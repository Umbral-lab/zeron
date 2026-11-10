//! Per-project workspace grants — narrowing a presented bearer to a set of
//! workspace spaces.
//!
//! The engine's `{data_dir}/ipc-token` bearer is all-or-nothing: whoever
//! presents it may call every RPC method ([`crate::ipc_auth`]). An enrolled
//! owned-server session (REMOTE-001 transport) therefore gets the whole remote
//! engine, and the client is not a security boundary — a localhost listener
//! still needs server-side authorization.
//!
//! This module adds an optional, owner-only grants file
//! (`{data_dir}/ipc-grants.json`, same write discipline as the ipc-token):
//! each grant carries its own secret bearer plus an allow-set of workspace
//! space ids. A handshake presenting a grant bearer is served with a
//! [`ScopedRpcService`] that refuses workspace-targeted calls outside the
//! allow-set before the engine ever runs them. Presenting the main ipc-token
//! is byte-compatible with pre-grant behavior (full access), so an engine
//! without a grants file — or a client that never heard of grants — is
//! unaffected.
//!
//! Identity model: the space id already addresses the (device, folder) pair
//! from the workspace doc (see the Spaces registry in [`crate`]); the grant
//! allow-set is exactly a set of those ids as this engine knows them.

use std::collections::HashSet;
use std::io::{self, Write};
use std::path::{Path, PathBuf};

use async_trait::async_trait;

use crate::{RpcError, RpcReply, RpcService, methods};

/// File name of the grants record inside the engine's data dir.
pub const GRANTS_FILE_NAME: &str = "ipc-grants.json";

/// Format version this build understands.
pub const GRANTS_FORMAT_VERSION: u32 = 1;

const NAME_MAX: usize = 64;
const SPACE_MAX: usize = 128;
const SPACES_MAX: usize = 256;
const GRANTS_MAX: usize = 64;
const FILE_LIMIT: u64 = 64 * 1024;

fn name_ok(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= NAME_MAX
        && name.as_bytes()[0].is_ascii_alphanumeric()
        && name
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b))
}

fn space_ok(space_id: &str) -> bool {
    !space_id.is_empty() && space_id.len() <= SPACE_MAX && space_id.bytes().all(|b| !b.is_ascii_control())
}

/// One entry of the grants file: a secret bearer plus the spaces it may touch.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GrantRecord {
    pub name: String,
    pub token: String,
    pub space_ids: Vec<String>,
}

/// The whole grants file.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GrantsFile {
    pub format_version: u32,
    pub grants: Vec<GrantRecord>,
}

impl GrantsFile {
    /// Structural validation: names unique and safe, tokens 64-hex (a bearer is
    /// as unguessable as the ipc-token), spaces within bounds, no duplicates.
    pub fn validate(&self) -> io::Result<()> {
        if self.format_version != GRANTS_FORMAT_VERSION {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, 
                "unsupported ipc-grants format version",
            ));
        }
        if self.grants.len() > GRANTS_MAX {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "too many grants"));
        }
        let mut names = HashSet::new();
        let mut tokens = HashSet::new();
        for grant in &self.grants {
            if !name_ok(&grant.name) {
                return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid grant name"));
            }
            if !names.insert(grant.name.as_str()) {
                return Err(io::Error::new(io::ErrorKind::InvalidInput, "duplicate grant name"));
            }
            if grant.token.len() != 64 || !grant.token.bytes().all(|b| b.is_ascii_hexdigit()) {
                return Err(io::Error::new(io::ErrorKind::InvalidInput, "grant token must be 64 hex chars"));
            }
            if !tokens.insert(grant.token.as_str()) {
                return Err(io::Error::new(io::ErrorKind::InvalidInput, "duplicate grant token"));
            }
            if grant.space_ids.len() > SPACES_MAX {
                return Err(io::Error::new(io::ErrorKind::InvalidInput, "too many granted spaces"));
            }
            let mut spaces = HashSet::new();
            for space_id in &grant.space_ids {
                if !space_ok(space_id) {
                    return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid granted space id"));
                }
                if !spaces.insert(space_id.as_str()) {
                    return Err(io::Error::new(io::ErrorKind::InvalidInput, "duplicate granted space id"));
                }
            }
        }
        Ok(())
    }
}

/// `{data_dir}/ipc-grants.json`.
pub fn grants_path(data_dir: &Path) -> PathBuf {
    data_dir.join(GRANTS_FILE_NAME)
}

/// Read the grants file. `None` means "no grants configured" — every bearer
/// keeps today's full-access semantics. A file that exists but does not parse
/// or validate fails closed (an error), never a silent grant.
pub fn read_grants(path: &Path) -> io::Result<Option<GrantsFile>> {
    let raw = match std::fs::read(path) {
        Ok(raw) => raw,
        Err(err) if err.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(err) => return Err(err),
    };
    if raw.len() as u64 > FILE_LIMIT {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "ipc-grants file is too large"));
    }
    let file: GrantsFile = serde_json::from_slice(&raw)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidInput, format!("invalid ipc-grants JSON: {e}")))?;
    file.validate()?;
    Ok(Some(file))
}

/// Atomically replace the grants file owner-only, reusing the ipc-token's
/// exclusive-create + rename discipline (never follows a planted symlink).
pub fn write_grants(path: &Path, file: &GrantsFile) -> io::Result<()> {
    file.validate()?;
    let dir = path
        .parent()
        .filter(|dir| !dir.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    std::fs::create_dir_all(dir)?;
    let suffix = crate::ipc_auth::generate_token()?;
    let tmp = dir.join(format!(".{}.{}.tmp", GRANTS_FILE_NAME, &suffix[..16]));
    let json = serde_json::to_vec_pretty(file)?;
    let written = write_exclusive(&tmp, &json).and_then(|()| std::fs::rename(&tmp, path));
    if written.is_err() {
        let _ = std::fs::remove_file(&tmp);
    }
    written
}

fn write_exclusive(path: &Path, bytes: &[u8]) -> io::Result<()> {
    let mut options = std::fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(path)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        file.set_permissions(std::fs::Permissions::from_mode(0o600))?;
    }
    file.write_all(bytes)?;
    file.write_all(b"\n")?;
    file.sync_all()
}

/// Which spaces a presented bearer may reach.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkspaceScope {
    pub grant_name: String,
    pub space_ids: HashSet<String>,
}

/// Resolve a handshake bearer to a session scope, consulting the main
/// ipc-token first (unchanged full access), then grant tokens (constant-time).
/// `Ok(None)` = serve with full access; `Err(None)` = 401; `Err(Some(scope))`
/// = the bearer matched a grant but its record is broken (503, fail closed).
pub fn resolve_bearer(
    grants: Option<&GrantsFile>,
    token: &str,
    presented: &[u8],
) -> Result<Option<WorkspaceScope>, Option<WorkspaceScope>> {
    if crate::ipc_auth::bearer_matches(token, Some(presented)) {
        return Ok(None);
    }
    if let Some(grants) = grants {
        for grant in &grants.grants {
            if crate::ipc_auth::bearer_matches(&grant.token, Some(presented)) {
                if !grant.space_ids.iter().all(|s| space_ok(s)) {
                    return Err(Some(WorkspaceScope {
                        grant_name: grant.name.clone(),
                        space_ids: HashSet::new(),
                    }));
                }
                return Ok(Some(WorkspaceScope {
                    grant_name: grant.name.clone(),
                    space_ids: grant.space_ids.iter().cloned().collect(),
                }));
            }
        }
    }
    Err(None)
}

/// Workspace-targeted methods whose params carry a [`zeron_proto::WorkspaceTarget`]
/// (chatId / spaceId / checkoutPath). Server-side grants understand space ids;
/// a scoped session calling one of these with any other target form is refused.
fn workspace_targeted(method: &str) -> bool {
    matches!(
        method,
        methods::LIST_WORKSPACE_DIRECTORY
            | methods::SEARCH_WORKSPACE_FILES
            | methods::WARM_WORKSPACE_SEARCH
            | methods::SEARCH_WORKSPACE_CONTENT
            | methods::READ_WORKSPACE_IMAGE
            | methods::READ_WORKSPACE_FILE
            | methods::MOVE_WORKSPACE_ENTRY
            | methods::DELETE_WORKSPACE_ENTRY
            | methods::WRITE_WORKSPACE_FILE
            | methods::WATCH_WORKSPACE_FILES
    )
}

/// A per-connection service wrapper enforcing a [`WorkspaceScope`]. Non-workspace
/// methods pass through untouched (the grant narrows project workspaces, not the
/// engine's session/chat surface); workspace calls are admitted only for
/// space ids in the allow-set.
pub struct ScopedRpcService {
    inner: std::sync::Arc<dyn RpcService>,
    scope: WorkspaceScope,
}

impl ScopedRpcService {
    pub fn new(inner: std::sync::Arc<dyn RpcService>, scope: WorkspaceScope) -> Self {
        Self { inner, scope }
    }
}

#[async_trait]
impl RpcService for ScopedRpcService {
    async fn handle(&self, method: &str, params: serde_json::Value) -> Result<RpcReply, RpcError> {
        if workspace_targeted(method) {
            let space_id = params.get("spaceId").and_then(|v| v.as_str());
            match space_id {
                Some(space_id) if self.scope.space_ids.contains(space_id) => {}
                Some(space_id) => {
                    tracing::warn!(
                        grant = %self.scope.grant_name,
                        method,
                        space_id,
                        "rpc: refusing a workspace call outside the grant's spaces"
                    );
                    return Err(RpcError::Capability(format!(
                        "grant {:?} is not authorized for this workspace",
                        self.scope.grant_name
                    )));
                }
                None => {
                    tracing::warn!(
                        grant = %self.scope.grant_name,
                        method,
                        "rpc: refusing a workspace call the grant cannot identify"
                    );
                    return Err(RpcError::Capability(format!(
                        "grant {:?} only addresses workspace calls by space id",
                        self.scope.grant_name
                    )));
                }
            }
        }
        self.inner.handle(method, params).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn grant(name: &str, token: &str, spaces: &[&str]) -> GrantRecord {
        GrantRecord {
            name: name.to_string(),
            token: token.to_string(),
            space_ids: spaces.iter().map(|s| s.to_string()).collect(),
        }
    }

    #[test]
    fn validate_rejects_malformed_files() {
        let token = "ab".repeat(32);
        let mut file = GrantsFile {
            format_version: GRANTS_FORMAT_VERSION,
            grants: vec![grant("work", &token, &["space-1"])],
        };
        assert!(file.validate().is_ok());

        file.grants.push(grant("work", &"cd".repeat(32), &[]));
        assert!(file.validate().is_err(), "duplicate names must fail");

        file.grants.pop();
        file.grants.push(grant("other", &token, &[]));
        assert!(file.validate().is_err(), "duplicate tokens must fail");

        file.grants.clear();
        file.grants.push(grant("bad name", &token, &[]));
        assert!(file.validate().is_err(), "unsafe names must fail");

        file.grants[0].name = "ok".into();
        file.grants[0].token = "short".into();
        assert!(file.validate().is_err(), "a weak token must fail");
    }

    #[test]
    fn read_write_round_trip_and_missing_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = grants_path(dir.path());
        assert_eq!(read_grants(&path).unwrap(), None);

        let token = "ab".repeat(32);
        let file = GrantsFile {
            format_version: GRANTS_FORMAT_VERSION,
            grants: vec![grant("work", &token, &["space-1", "space-2"])],
        };
        write_grants(&path, &file).unwrap();
        assert_eq!(read_grants(&path).unwrap(), Some(file.clone()));
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                std::fs::metadata(&path).unwrap().permissions().mode() & 0o777,
                0o600,
                "grants file must be owner-only"
            );
        }

        std::fs::write(&path, "{\"formatVersion\":99,\"grants\":[]}").unwrap();
        assert!(read_grants(&path).unwrap_err().kind() == io::ErrorKind::InvalidInput);
    }

    #[test]
    fn resolve_prefers_the_main_token_and_binds_grants() {
        let main = "ab".repeat(32);
        let grant_token = "cd".repeat(32);
        let grants = GrantsFile {
            format_version: GRANTS_FORMAT_VERSION,
            grants: vec![grant("work", &grant_token, &["space-1"])],
        };
        let bearer = |token: &str| format!("Bearer {token}");

        // Main bearer: full access, exactly as before grants existed.
        assert_eq!(resolve_bearer(Some(&grants), &main, bearer(&main).as_bytes()), Ok(None));
        assert_eq!(resolve_bearer(None, &main, bearer(&main).as_bytes()), Ok(None));

        // Grant bearer: scoped to its spaces.
        let scoped = resolve_bearer(Some(&grants), &main, bearer(&grant_token).as_bytes())
            .unwrap()
            .unwrap();
        assert_eq!(scoped.grant_name, "work");
        assert!(scoped.space_ids.contains("space-1"));

        // Unknown bearer: no session at all.
        assert_eq!(
            resolve_bearer(Some(&grants), &main, bearer(&"ef".repeat(32)).as_bytes()),
            Err(None)
        );
        assert_eq!(resolve_bearer(None, &main, b"nonsense"), Err(None));
    }

    fn value_of(result: Result<RpcReply, RpcError>) -> serde_json::Value {
        match result.expect("a unary reply") {
            RpcReply::Value(value) => value,
            RpcReply::Stream(_) => panic!("expected a unary reply"),
        }
    }

    #[tokio::test]
    async fn scoped_service_admits_only_granted_space_calls() {
        struct Echo;
        #[async_trait]
        impl RpcService for Echo {
            async fn handle(
                &self,
                method: &str,
                params: serde_json::Value,
            ) -> Result<RpcReply, RpcError> {
                // A value-returning stand-in for the engine's workspace
                // dispatch: a granted call reaches here and echoes its target.
                RpcReply::value(&serde_json::json!({"method": method, "space": params.get("spaceId")}))
            }
        }
        let scope = WorkspaceScope {
            grant_name: "work".into(),
            space_ids: ["space-1".to_string()].into_iter().collect(),
        };
        let scoped = ScopedRpcService::new(std::sync::Arc::new(Echo), scope);

        let ok = scoped
            .handle(
                methods::LIST_WORKSPACE_DIRECTORY,
                serde_json::json!({"spaceId": "space-1"}),
            )
            .await;
        assert_eq!(
            value_of(ok),
            serde_json::json!({"method": "ListWorkspaceDirectory", "space": "space-1"})
        );

        let refused = scoped
            .handle(
                methods::READ_WORKSPACE_FILE,
                serde_json::json!({"spaceId": "space-other"}),
            )
            .await;
        match refused {
            Err(RpcError::Capability(message)) => assert!(message.contains("not authorized"), "{message}"),
            Ok(_) => panic!("a non-granted space must be refused server-side"),
            Err(error) => panic!("expected a capability refusal, got {error}"),
        }

        let refused = scoped
            .handle(methods::WRITE_WORKSPACE_FILE, serde_json::json!({"chatId": "c"}))
            .await;
        match refused {
            Err(RpcError::Capability(_)) => {}
            Ok(_) => panic!("an unidentifiable target must be refused"),
            Err(error) => panic!("expected a capability refusal, got {error}"),
        }

        // Non-workspace methods are untouched by the scope.
        let ok = scoped
            .handle("Echo", serde_json::json!("anything"))
            .await;
        assert_eq!(
            value_of(ok),
            serde_json::json!({"method": "Echo", "space": null})
        );
    }
}
