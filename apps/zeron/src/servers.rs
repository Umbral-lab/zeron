//! Explicit owned-server enrollment and live session access. Normal local app
//! startup never reads this registry or connects to an enrolled machine.

use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use anyhow::{Context, bail, ensure};
use clap::Subcommand;
use serde_json::{Value, json};
use zeron_rpc::ssh::{SshConnection, SshEndpoint, connect_ssh};

const RPC_TIMEOUT: Duration = Duration::from_secs(5);
const RECORD_LIMIT: u64 = 32 * 1024;

#[derive(Subcommand)]
pub enum ServerCommand {
    /// Verify an engine over SSH, then save a named enrollment (never its token).
    Add {
        name: String,
        /// An existing SSH host alias or USER@HOST. Host keys must already be trusted.
        host: String,
        /// Local owner-only file containing the REMOTE engine's current IPC bearer.
        #[arg(long, value_name = "REMOTE_IPC_TOKEN_FILE")]
        remote_ipc_token_file: PathBuf,
        #[arg(long, default_value_t = 22)]
        ssh_port: u16,
        #[arg(long, default_value_t = 27654)]
        ipc_port: u16,
        #[arg(long)]
        known_hosts: Option<PathBuf>,
        #[arg(long)]
        identity: Option<PathBuf>,
    },
    /// List saved servers without making any network connection.
    List,
    /// Verify a saved server is reachable and still has the enrolled identity.
    Status { name: String },
    /// Read a saved server's current agent sessions, then disconnect.
    Sessions { name: String },
    /// Maintain a live session monitor. Ctrl-C or removing the enrollment disconnects.
    Connect { name: String },
    /// Disconnect live monitors without forgetting the server or deleting keys.
    Disconnect { name: String },
    /// Remove local enrollment and disconnect live monitors; does not delete SSH keys.
    Remove { name: String },
}

struct Registry {
    root: PathBuf,
}

impl Registry {
    fn new(data_dir: &Path) -> Self {
        Self {
            root: data_dir.join("servers"),
        }
    }

    fn path(&self, name: &str) -> anyhow::Result<PathBuf> {
        ensure!(
            !name.is_empty()
                && name.len() <= 64
                && name.as_bytes()[0].is_ascii_alphanumeric()
                && name
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b)),
            "server name must be 1–64 ASCII letters/digits/dots/dashes/underscores and start with a letter or digit"
        );
        let base = name.split('.').next().unwrap().to_ascii_lowercase();
        ensure!(
            !["con", "prn", "aux", "nul"].contains(&base.as_str())
                && !(base.len() == 4
                    && (base.starts_with("com") || base.starts_with("lpt"))
                    && matches!(base.as_bytes()[3], b'1'..=b'9')),
            "reserved server name"
        );
        Ok(self.root.join(format!("{name}.json")))
    }

    fn ensure_dir(&self) -> anyhow::Result<()> {
        let mut builder = fs::DirBuilder::new();
        builder.recursive(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::DirBuilderExt;
            builder.mode(0o700);
        }
        builder.create(&self.root)?;
        let meta = fs::symlink_metadata(&self.root)?;
        ensure!(
            meta.is_dir() && !meta.file_type().is_symlink(),
            "server registry must be a real directory"
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            ensure!(
                meta.permissions().mode() & 0o077 == 0,
                "server registry must be owner-only"
            );
        }
        Ok(())
    }

    fn load(&self, name: &str) -> anyhow::Result<Value> {
        self.ensure_dir()?;
        let path = self.path(name)?;
        let meta = fs::symlink_metadata(&path)
            .with_context(|| format!("server {name:?} is not enrolled"))?;
        ensure!(
            meta.is_file() && !meta.file_type().is_symlink(),
            "server enrollment must be a regular file"
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            ensure!(
                meta.permissions().mode() & 0o077 == 0,
                "server enrollment must be owner-only"
            );
        }
        let mut data = Vec::new();
        fs::File::open(&path)?
            .take(RECORD_LIMIT + 1)
            .read_to_end(&mut data)?;
        ensure!(
            data.len() as u64 <= RECORD_LIMIT,
            "server enrollment is too large"
        );
        let value: Value =
            serde_json::from_slice(&data).context("invalid server enrollment JSON")?;
        ensure!(
            value["formatVersion"] == 1 && value["name"] == name,
            "unsupported or mismatched server enrollment"
        );
        text(&value, "enrollmentId")?;
        Ok(value)
    }

    fn save_new(&self, name: &str, value: &Value) -> anyhow::Result<()> {
        let _lock = self.lock()?;
        self.write_record(name, value, false)
    }

    fn lock(&self) -> anyhow::Result<fs::File> {
        self.ensure_dir()?;
        let mut options = fs::OpenOptions::new();
        options.read(true).write(true).create(true).truncate(false);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600).custom_flags(libc::O_NOFOLLOW);
        }
        let lock = options.open(self.root.join(".registry.lock"))?;
        lock.lock()?;
        Ok(lock)
    }

    // Every writer holds the same OS lock: disconnect cannot resurrect a
    // removed enrollment or overwrite a concurrently re-enrolled identity.
    fn write_record(&self, name: &str, value: &Value, replace: bool) -> anyhow::Result<()> {
        let mut file = tempfile::NamedTempFile::new_in(&self.root)?;
        serde_json::to_writer_pretty(&mut file, value)?;
        file.write_all(b"\n")?;
        file.as_file().sync_all()?;
        let target = self.path(name)?;
        let saved = if replace {
            file.persist(target)
        } else {
            file.persist_noclobber(target)
        };
        saved.map_err(|e| anyhow::anyhow!("server {name:?} cannot be saved: {}", e.error))?;
        self.sync_dir()
    }

    fn disconnect(&self, name: &str) -> anyhow::Result<()> {
        let _lock = self.lock()?;
        let mut record = self.load(name)?;
        record["enrollmentId"] = json!(zeron_rpc::ipc_auth::generate_token()?);
        self.write_record(name, &record, true)
    }

    fn remove(&self, name: &str) -> anyhow::Result<()> {
        let path = self.path(name)?;
        let _lock = self.lock()?;
        fs::remove_file(path).with_context(|| format!("cannot remove server {name:?}"))?;
        self.sync_dir()
    }

    fn sync_dir(&self) -> anyhow::Result<()> {
        #[cfg(unix)]
        fs::File::open(&self.root)?.sync_all()?;
        Ok(())
    }

    fn list(&self) -> anyhow::Result<Vec<Value>> {
        if !self.root.exists() {
            return Ok(Vec::new());
        }
        self.ensure_dir()?;
        let mut entries = Vec::new();
        for entry in fs::read_dir(&self.root)? {
            let path = entry?.path();
            if path.extension().and_then(|x| x.to_str()) != Some("json") {
                continue;
            }
            let name = path
                .file_stem()
                .and_then(|x| x.to_str())
                .context("invalid enrollment filename")?;
            let record = self.load(name)?;
            entries.push(
                json!({"name": name, "host": record["host"], "sshPort": record["sshPort"],
                "ipcPort": record["ipcPort"], "identity": record["engineIdentity"],
                "enrolledAtMs": record["enrolledAtMs"]}),
            );
        }
        entries.sort_by(|a, b| a["name"].as_str().cmp(&b["name"].as_str()));
        Ok(entries)
    }
}

fn text<'a>(value: &'a Value, field: &str) -> anyhow::Result<&'a str> {
    value[field]
        .as_str()
        .filter(|s| !s.is_empty())
        .with_context(|| format!("missing enrollment field {field}"))
}

fn port(value: &Value, field: &str) -> anyhow::Result<u16> {
    value[field]
        .as_u64()
        .filter(|n| (1..=u16::MAX as u64).contains(n))
        .map(|n| n as u16)
        .with_context(|| format!("invalid enrollment port {field}"))
}

fn path_string(path: &Path) -> anyhow::Result<&str> {
    path.to_str()
        .context("server credential/trust paths must be valid UTF-8")
}

fn canonical_file(path: &Path) -> anyhow::Result<PathBuf> {
    let canonical =
        fs::canonicalize(path).with_context(|| format!("cannot resolve {}", path.display()))?;
    ensure!(canonical.is_file(), "{} is not a file", canonical.display());
    path_string(&canonical)?;
    Ok(canonical)
}

fn token(path: &Path) -> anyhow::Result<String> {
    let meta = fs::metadata(path)?;
    ensure!(
        meta.is_file() && meta.len() <= 4096,
        "invalid remote IPC token file"
    );
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        ensure!(
            meta.permissions().mode() & 0o077 == 0,
            "remote IPC token file must be owner-only (chmod 600)"
        );
    }
    let token = zeron_rpc::ipc_auth::read_token(path)?.context("remote IPC token file is empty")?;
    ensure!(
        token.len() == 64 && token.bytes().all(|b| b.is_ascii_hexdigit()),
        "expected the remote engine's 64-character IPC bearer, not a provider API key"
    );
    Ok(token)
}

fn endpoint(record: &Value) -> anyhow::Result<SshEndpoint> {
    let mut endpoint = SshEndpoint::new(text(record, "host")?, port(record, "ipcPort")?);
    endpoint.ssh_port = port(record, "sshPort")?;
    endpoint.known_hosts_file = optional_path(record, "knownHostsFile")?;
    endpoint.identity_file = optional_path(record, "identityFile")?;
    Ok(endpoint)
}

fn optional_path(record: &Value, field: &str) -> anyhow::Result<Option<PathBuf>> {
    match &record[field] {
        Value::Null => Ok(None),
        Value::String(path) if !path.is_empty() && Path::new(path).is_absolute() => {
            Ok(Some(PathBuf::from(path)))
        }
        _ => bail!("invalid enrollment path {field}"),
    }
}

fn identity(info: &Value) -> anyhow::Result<Value> {
    let device = text(info, "deviceId")?;
    let scope = text(info, "workspaceScope")?;
    ensure!(
        matches!(scope, "local" | "synced" | "development"),
        "unknown remote workspace scope"
    );
    Ok(json!({"deviceId": device, "workspaceScope": scope}))
}

fn now_ms() -> anyhow::Result<u64> {
    Ok(SystemTime::now()
        .duration_since(UNIX_EPOCH)?
        .as_millis()
        .try_into()?)
}

fn print(value: &Value) -> anyhow::Result<()> {
    println!("{}", terminal_safe(&serde_json::to_string(value)?));
    std::io::stdout().flush()?;
    Ok(())
}

fn terminal_safe(text: &str) -> String {
    let mut result = String::with_capacity(text.len());
    for c in text.chars() {
        if c.is_control()
            || matches!(c, '\u{061c}' | '\u{200e}' | '\u{200f}' | '\u{2028}'..='\u{202e}' | '\u{2066}'..='\u{2069}')
        {
            result.push_str(&format!("\\u{:04x}", c as u32));
        } else {
            result.push(c);
        }
    }
    result
}

async fn remote_info(connection: &SshConnection) -> anyhow::Result<Value> {
    Ok(tokio::time::timeout(
        RPC_TIMEOUT,
        connection
            .client()
            .call(zeron_rpc::methods::ENGINE_INFO, Value::Null),
    )
    .await
    .context("remote engine identity request timed out")??)
}

async fn verified(record: &Value) -> anyhow::Result<(SshConnection, Value)> {
    let token_path = Path::new(text(record, "remoteIpcTokenFile")?);
    ensure!(
        token_path.is_absolute(),
        "remote IPC token path must be absolute"
    );
    let connection = connect_ssh(&endpoint(record)?, &token(token_path)?).await?;
    let checked = async {
        let info = remote_info(&connection).await?;
        ensure!(
            identity(&info)? == record["engineIdentity"],
            "remote engine identity changed; remove and explicitly re-enroll the server"
        );
        Ok::<_, anyhow::Error>(info)
    }
    .await;
    match checked {
        Ok(info) => Ok((connection, info)),
        Err(error) => {
            connection.close().await;
            Err(error)
        }
    }
}

pub async fn run(command: ServerCommand, data_dir: &Path) -> anyhow::Result<()> {
    run_inner(command, data_dir)
        .await
        .map_err(|error| anyhow::anyhow!(terminal_safe(&format!("{error:#}"))))
}

async fn run_inner(command: ServerCommand, data_dir: &Path) -> anyhow::Result<()> {
    let registry = Registry::new(data_dir);
    match command {
        ServerCommand::Add {
            name,
            host,
            remote_ipc_token_file,
            ssh_port,
            ipc_port,
            known_hosts,
            identity: key,
        } => {
            let path = registry.path(&name)?;
            ensure!(
                fs::symlink_metadata(path).is_err_and(|e| e.kind() == std::io::ErrorKind::NotFound),
                "server already enrolled; remove it explicitly before changing its identity"
            );
            let token_file = canonical_file(&remote_ipc_token_file)?;
            let known_hosts = known_hosts.as_deref().map(canonical_file).transpose()?;
            let key = key.as_deref().map(canonical_file).transpose()?;
            let mut target = SshEndpoint::new(&host, ipc_port);
            target.ssh_port = ssh_port;
            target.known_hosts_file = known_hosts.clone();
            target.identity_file = key.clone();
            let connection = connect_ssh(&target, &token(&token_file)?).await?;
            let info = remote_info(&connection).await;
            connection.close().await;
            let info = info?;
            let record = json!({"formatVersion": 1, "name": name, "host": host,
                "sshPort": ssh_port, "ipcPort": ipc_port,
                "remoteIpcTokenFile": path_string(&token_file)?,
                "knownHostsFile": known_hosts.as_deref().map(path_string).transpose()?,
                "identityFile": key.as_deref().map(path_string).transpose()?,
                "engineIdentity": identity(&info)?, "enrollmentId": zeron_rpc::ipc_auth::generate_token()?,
                "enrolledAtMs": now_ms()?});
            registry.save_new(&name, &record)?;
            print(&json!({"status":"enrolled", "name":name, "engine":info}))
        }
        ServerCommand::List => print(&json!(registry.list()?)),
        ServerCommand::Remove { name } => {
            registry.remove(&name)?;
            print(&json!({"status":"removed", "name":name}))
        }
        ServerCommand::Disconnect { name } => {
            registry.disconnect(&name)?;
            print(&json!({"status":"disconnectRequested", "name":name}))
        }
        ServerCommand::Status { name } => {
            let (connection, info) = verified(&registry.load(&name)?).await?;
            connection.close().await;
            print(
                &json!({"status":"reachable", "name":name, "engine":info, "observedAtMs":now_ms()?}),
            )
        }
        ServerCommand::Sessions { name } => {
            let (connection, _) = verified(&registry.load(&name)?).await?;
            let result = async {
                let mut sessions = connection
                    .client()
                    .subscribe_scoped(zeron_rpc::methods::WATCH_SESSIONS, Value::Null)
                    .await?;
                tokio::time::timeout(RPC_TIMEOUT, sessions.recv())
                    .await
                    .context("remote session snapshot timed out")?
                    .context("remote session stream closed")
            }
            .await;
            connection.close().await;
            print(&json!({"name":name, "sessions":result?, "observedAtMs":now_ms()?}))
        }
        ServerCommand::Connect { name } => monitor(&registry, &name).await,
    }
}

async fn monitor(registry: &Registry, name: &str) -> anyhow::Result<()> {
    #[cfg(unix)]
    let mut interrupts = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::interrupt())?;
    #[cfg(unix)]
    let stop = async move {
        interrupts.recv().await;
        Ok::<_, std::io::Error>(())
    };
    #[cfg(not(unix))]
    let stop = tokio::signal::ctrl_c();
    tokio::pin!(stop);
    let record = registry.load(name)?;
    let (connection, info) = tokio::select! {
        biased;
        result = &mut stop => { result?; return print(&json!({"status":"cancelled", "name":name})); }
        result = verified(&record) => result?,
    };
    let result = async {
        let mut sessions = connection.client().subscribe_scoped(zeron_rpc::methods::WATCH_SESSIONS, Value::Null).await?;
        print(&json!({"status":"connected", "name":name, "engine":info}))?;
        let mut revoke = tokio::time::interval(Duration::from_millis(250));
        loop {
            tokio::select! {
                biased;
                signal = &mut stop => { signal?; return Ok(()); }
                _ = connection.client().closed() => bail!("remote server disconnected; reconnect explicitly (no requests were replayed)"),
                _ = revoke.tick() => {
                    if registry.load(name).ok().is_none_or(|current| current["enrollmentId"] != record["enrollmentId"]) {
                        return Ok(());
                    }
                }
                update = sessions.recv() => {
                    let update = update.context("remote session stream closed; reconnect explicitly")?;
                    print(&json!({"name":name, "sessions":update, "observedAtMs":now_ms()?}))?;
                }
            }
        }
    }.await;
    connection.close().await;
    print(&json!({"status":"disconnected", "name":name}))?;
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn remote_terminal_controls_are_escaped_without_changing_json_values() {
        let data = json!({"remote":"\u{009b}31m\u{202e}file\u{001b}]52;c;payload"});
        let output = terminal_safe(&serde_json::to_string(&data).unwrap());
        assert!(!output.contains(['\u{009b}', '\u{202e}', '\u{001b}']));
        assert_eq!(serde_json::from_str::<Value>(&output).unwrap(), data);
        assert!(!terminal_safe("SSH banner: \u{001b}]52;c;payload").contains('\u{001b}'));
    }

    fn record(name: &str) -> Value {
        json!({"formatVersion":1,"name":name,"enrollmentId":"fixture-enrollment",
            "host":"user@owned", "sshPort":22,"ipcPort":27654,
            "engineIdentity":{"deviceId":"fixture","workspaceScope":"local"}})
    }

    #[test]
    fn enrollment_is_atomic_private_and_never_overwrites() {
        let dir = tempfile::tempdir().unwrap();
        let registry = Registry::new(dir.path());
        let original = record("prod");
        registry.save_new("prod", &original).unwrap();
        assert!(registry.save_new("prod", &record("other")).is_err());
        assert_eq!(registry.load("prod").unwrap(), original);
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                fs::metadata(registry.path("prod").unwrap())
                    .unwrap()
                    .permissions()
                    .mode()
                    & 0o777,
                0o600
            );
            assert_eq!(
                fs::metadata(&registry.root).unwrap().permissions().mode() & 0o777,
                0o700
            );
        }
    }

    #[test]
    fn names_cannot_escape_or_use_reserved_device_files() {
        let registry = Registry::new(Path::new("unused"));
        for name in [
            "", ".", "..", "../other", "a/b", "a\\b", "-x", "a\n", "con", "COM1",
        ] {
            assert!(registry.path(name).is_err(), "{name:?}");
        }
        for name in ["prod", "build-1", "server.eu", "my_server"] {
            assert!(registry.path(name).is_ok());
        }
    }

    #[test]
    fn disconnect_preserves_trust_and_credentials_and_cannot_resurrect_removal() {
        let dir = tempfile::tempdir().unwrap();
        let registry = Registry::new(dir.path());
        let original = record("prod");
        registry.save_new("prod", &original).unwrap();
        registry.disconnect("prod").unwrap();
        let mut disconnected = registry.load("prod").unwrap();
        assert_ne!(disconnected["enrollmentId"], original["enrollmentId"]);
        disconnected["enrollmentId"] = original["enrollmentId"].clone();
        assert_eq!(disconnected, original);
        registry.remove("prod").unwrap();
        assert!(registry.disconnect("prod").is_err());
        assert!(registry.list().unwrap().is_empty());
    }

    #[test]
    fn concurrent_disconnect_cannot_restore_an_old_engine_identity() {
        use std::sync::{Arc, Barrier};
        let dir = tempfile::tempdir().unwrap();
        let registry = Registry::new(dir.path());
        for _ in 0..20 {
            registry.save_new("prod", &record("prod")).unwrap();
            let barrier = Arc::new(Barrier::new(2));
            let start = barrier.clone();
            let root = dir.path().to_owned();
            let disconnect = std::thread::spawn(move || {
                start.wait();
                let _ = Registry::new(&root).disconnect("prod");
            });
            barrier.wait();
            registry.remove("prod").unwrap();
            let mut replacement = record("prod");
            replacement["engineIdentity"]["deviceId"] = json!("new-engine");
            registry.save_new("prod", &replacement).unwrap();
            disconnect.join().unwrap();
            assert_eq!(
                registry.load("prod").unwrap()["engineIdentity"]["deviceId"],
                "new-engine"
            );
            registry.remove("prod").unwrap();
        }
    }

    #[test]
    fn list_and_remove_are_offline_and_preserve_credentials() {
        let dir = tempfile::tempdir().unwrap();
        let registry = Registry::new(dir.path());
        assert!(registry.list().unwrap().is_empty());
        let credential = dir.path().join("remote-token");
        fs::write(&credential, "synthetic-secret").unwrap();
        let mut value = record("prod");
        value["remoteIpcTokenFile"] = json!(credential.to_str().unwrap());
        registry.save_new("prod", &value).unwrap();
        let listed = registry.list().unwrap();
        assert_eq!(listed[0]["name"], "prod");
        assert!(
            !serde_json::to_string(&listed)
                .unwrap()
                .contains("synthetic-secret")
        );
        fs::remove_file(registry.path("prod").unwrap()).unwrap();
        assert!(registry.list().unwrap().is_empty());
        assert_eq!(fs::read_to_string(credential).unwrap(), "synthetic-secret");
    }

    #[test]
    fn corrupt_records_and_unrecognized_identity_fail_closed() {
        let dir = tempfile::tempdir().unwrap();
        let registry = Registry::new(dir.path());
        registry.save_new("prod", &record("other")).unwrap();
        assert!(registry.load("prod").is_err());
        assert!(identity(&json!({"deviceId":"a","workspaceScope":"unknown"})).is_err());
        assert!(identity(&json!({"deviceId":"","workspaceScope":"local"})).is_err());
        assert!(port(&json!({"port":65536}), "port").is_err());
        assert!(port(&json!({"port":0}), "port").is_err());
    }

    #[test]
    fn malformed_trust_paths_cannot_fall_back_to_different_ssh_credentials() {
        let mut value = record("prod");
        value["knownHostsFile"] = json!(42);
        assert!(endpoint(&value).is_err());
        value["knownHostsFile"] = json!("relative-known-hosts");
        assert!(endpoint(&value).is_err());
        value["knownHostsFile"] = Value::Null;
        value["identityFile"] = json!(false);
        assert!(endpoint(&value).is_err());
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn a_symlinked_registry_cannot_delete_an_outside_record() {
        use std::os::unix::fs::symlink;
        let dir = tempfile::tempdir().unwrap();
        let outside = tempfile::tempdir().unwrap();
        let record = outside.path().join("prod.json");
        fs::write(&record, "outside file").unwrap();
        symlink(outside.path(), dir.path().join("servers")).unwrap();
        assert!(Registry::new(dir.path()).load("prod").is_err());
        assert!(
            run(
                ServerCommand::Remove {
                    name: "prod".into()
                },
                dir.path()
            )
            .await
            .is_err()
        );
        assert_eq!(fs::read_to_string(&record).unwrap(), "outside file");
    }

    #[cfg(unix)]
    #[test]
    fn symlink_records_and_public_token_files_are_rejected() {
        use std::os::unix::fs::{PermissionsExt, symlink};
        let dir = tempfile::tempdir().unwrap();
        let registry = Registry::new(dir.path());
        registry.ensure_dir().unwrap();
        let target = dir.path().join("not-an-enrollment");
        fs::write(&target, "0".repeat(64)).unwrap();
        symlink(&target, registry.path("prod").unwrap()).unwrap();
        assert!(registry.load("prod").is_err());
        fs::set_permissions(&target, fs::Permissions::from_mode(0o644)).unwrap();
        assert!(token(&target).is_err());
        fs::set_permissions(&target, fs::Permissions::from_mode(0o600)).unwrap();
        assert_eq!(token(&target).unwrap(), "0".repeat(64));
        fs::write(&target, "sk-provider-shaped-fixture").unwrap();
        let error = token(&target).unwrap_err().to_string();
        assert!(!error.contains("sk-provider-shaped-fixture"));
    }
}
