//! Direct access to an owned engine using OpenSSH's stdio forwarding.
//! No local listener, remote shell command, vendor relay, or credential forwarding.

use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::time::Duration;

use tokio::io::AsyncReadExt;
use tokio::sync::{mpsc, oneshot};
use tokio_tungstenite::tungstenite::client::IntoClientRequest;
use tokio_tungstenite::tungstenite::http::{HeaderValue, StatusCode, header};

use crate::{RpcClient, RpcError};

const CONNECT_TIMEOUT: Duration = Duration::from_secs(15);
const STDERR_LIMIT: usize = 8192;

/// An explicitly selected SSH host/alias and its loopback engine IPC port.
/// Host keys must already be trusted in OpenSSH's known_hosts (or the supplied
/// enrollment-specific file). Private keys stay with OpenSSH/the system agent.
#[derive(Clone, Debug)]
pub struct SshEndpoint {
    pub destination: String,
    pub ssh_port: u16,
    pub ipc_port: u16,
    pub known_hosts_file: Option<PathBuf>,
    pub identity_file: Option<PathBuf>,
}

impl SshEndpoint {
    pub fn new(destination: impl Into<String>, ipc_port: u16) -> Self {
        Self {
            destination: destination.into(),
            ssh_port: 22,
            ipc_port,
            known_hosts_file: None,
            identity_file: None,
        }
    }

    fn command(&self, program: &Path) -> Result<tokio::process::Command, RpcError> {
        let destination = &self.destination;
        if destination.is_empty()
            || destination.starts_with('-')
            || destination.matches('@').count() > 1
            || destination
                .split('@')
                .any(|part| part.is_empty() || part.starts_with('-'))
            || !destination
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"._-:@[]".contains(&c))
            || self.ssh_port == 0
            || self.ipc_port == 0
        {
            return Err(RpcError::Transport("invalid SSH endpoint".into()));
        }
        let mut cmd = tokio::process::Command::new(program);
        cmd.args([
            "-T",
            "-oBatchMode=yes",
            "-oStrictHostKeyChecking=yes",
            "-oVerifyHostKeyDNS=no",
            "-oKnownHostsCommand=none",
            "-oUpdateHostKeys=no",
            "-oPreferredAuthentications=publickey",
            "-oPasswordAuthentication=no",
            "-oKbdInteractiveAuthentication=no",
            "-oGSSAPIAuthentication=no",
            "-oProxyCommand=none",
            "-oProxyJump=none",
            "-oForwardAgent=no",
            "-oForwardX11=no",
            "-oPermitLocalCommand=no",
            "-oClearAllForwardings=yes",
            "-oControlMaster=no",
            "-oControlPath=none",
            "-oConnectTimeout=10",
            "-oConnectionAttempts=1",
            "-oServerAliveInterval=15",
            "-oServerAliveCountMax=2",
            "-oExitOnForwardFailure=yes",
        ]);
        if let Some(path) = &self.known_hosts_file {
            let path = path
                .to_str()
                .filter(|p| !p.contains(['\n', '\r', '\0']))
                .ok_or_else(|| RpcError::Transport("invalid known-hosts path".into()))?;
            // OpenSSH parses this value as a list, even though it is one argv.
            let quoted = path.replace('\\', "\\\\").replace('"', "\\\"");
            cmd.arg("-o")
                .arg(format!("UserKnownHostsFile=\"{quoted}\""));
            // Explicit enrollment must not fall back to a different global trust file.
            cmd.arg("-oGlobalKnownHostsFile=none");
        }
        if let Some(path) = &self.identity_file {
            cmd.arg("-oIdentitiesOnly=yes").arg("-i").arg(path);
        }
        cmd.arg("-p")
            .arg(self.ssh_port.to_string())
            .arg("-W")
            .arg(format!("127.0.0.1:{}", self.ipc_port))
            .arg("--")
            .arg(destination)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true);
        Ok(cmd)
    }
}

/// Owns the remote RPC client AND its SSH process. Drop disconnects, including
/// when subscriptions outlive the owner. `close` also waits for child reaping.
/// A dropped connection never retries requests: an interrupted remote mutation
/// has an uncertain outcome and must be reconciled before a caller retries it.
pub struct SshConnection {
    client: RpcClient,
    stop: Option<oneshot::Sender<()>>,
    task: Option<tokio::task::JoinHandle<()>>,
}

impl SshConnection {
    pub fn client(&self) -> &RpcClient {
        &self.client
    }

    pub async fn close(mut self) {
        if let Some(stop) = self.stop.take() {
            let _ = stop.send(());
        }
        if let Some(task) = self.task.take() {
            let _ = task.await;
        }
    }
}

impl Drop for SshConnection {
    fn drop(&mut self) {
        if let Some(stop) = self.stop.take() {
            let _ = stop.send(());
        }
    }
}

/// Connect on explicit user request. `ipc_token` is the REMOTE engine's current
/// bearer, not a local-engine token or provider credential. It is sent only
/// inside the encrypted SSH stream, never in argv, logs, or a listening URL.
/// This grants that SSH account's engine access; it does not create per-project
/// authorization. Callers must not claim narrower permissions than the server.
pub async fn connect_ssh(
    endpoint: &SshEndpoint,
    ipc_token: &str,
) -> Result<SshConnection, RpcError> {
    connect_with_program(endpoint, ipc_token, Path::new("ssh")).await
}

async fn connect_with_program(
    endpoint: &SshEndpoint,
    ipc_token: &str,
    program: &Path,
) -> Result<SshConnection, RpcError> {
    if ipc_token.trim().is_empty() {
        return Err(RpcError::Transport("remote IPC token is required".into()));
    }
    let bearer = HeaderValue::from_str(&format!("Bearer {ipc_token}"))
        .map_err(|_| RpcError::Transport("invalid remote IPC token".into()))?;
    let url = format!("ws://127.0.0.1:{}", endpoint.ipc_port);
    let mut request = url
        .into_client_request()
        .map_err(|_| RpcError::Transport("invalid remote IPC endpoint".into()))?;
    request.headers_mut().insert(header::AUTHORIZATION, bearer);
    let mut child = endpoint
        .command(program)?
        .spawn()
        .map_err(|e| RpcError::Transport(format!("could not start OpenSSH: {e}")))?;
    let io = tokio::io::join(child.stdout.take().unwrap(), child.stdin.take().unwrap());
    let mut stderr = child.stderr.take().unwrap();
    let diagnostics = tokio::spawn(async move {
        let mut retained = Vec::new();
        let mut buffer = [0; 1024];
        while let Ok(n) = stderr.read(&mut buffer).await {
            if n == 0 {
                break;
            }
            let keep = n.min(STDERR_LIMIT.saturating_sub(retained.len()));
            retained.extend_from_slice(&buffer[..keep]);
        }
        String::from_utf8_lossy(&retained).into_owned()
    });
    let handshake = tokio::time::timeout(
        CONNECT_TIMEOUT,
        tokio_tungstenite::client_async_with_config(request, io, Some(crate::ws::config())),
    )
    .await;
    let ws = match handshake {
        Ok(Ok((ws, _))) => ws,
        error => {
            let _ = child.kill().await;
            let detail = diagnostics.await.unwrap_or_default();
            let reason = match error {
                Err(_) => "SSH/remote IPC handshake timed out",
                Ok(Err(tokio_tungstenite::tungstenite::Error::Http(response)))
                    if response.status() == StatusCode::UNAUTHORIZED =>
                {
                    "remote engine rejected the IPC token (401)"
                }
                _ => "SSH/remote IPC handshake failed",
            };
            let detail = detail.replace(ipc_token, "[redacted]");
            return Err(RpcError::Transport(format!("{reason}: {}", detail.trim())));
        }
    };
    let (out_tx, out_rx) = mpsc::channel(256);
    let (in_tx, in_rx) = mpsc::channel(256);
    let client = RpcClient::new(out_tx, in_rx);
    let (stop, stopped) = oneshot::channel();
    let task = tokio::spawn(async move {
        tokio::select! {
            _ = stopped => {}
            _ = crate::ws::pump(ws, out_rx, in_tx) => {}
        }
        let _ = child.kill().await;
        let _ = diagnostics.await;
    });
    Ok(SshConnection {
        client,
        stop: Some(stop),
        task: Some(task),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn endpoints_cannot_inject_options_commands_or_extra_destinations() {
        for host in [
            "",
            "-oProxyCommand=bad",
            "user@",
            "@host",
            "user@-host",
            "a@b@c",
            "host\nother",
            "host;touch /tmp/bad",
            "user host",
            "$(id)",
        ] {
            assert!(
                SshEndpoint::new(host, 27654)
                    .command(Path::new("ssh"))
                    .is_err(),
                "{host:?}"
            );
        }
        for host in ["host", "user@host-alias", "127.0.0.1", "user@[::1]"] {
            assert!(
                SshEndpoint::new(host, 27654)
                    .command(Path::new("ssh"))
                    .is_ok()
            );
        }
        assert!(
            SshEndpoint::new("host", 0)
                .command(Path::new("ssh"))
                .is_err()
        );
    }

    #[test]
    fn ssh_uses_pinned_hosts_and_loopback_without_forwarding_credentials() {
        let mut endpoint = SshEndpoint::new("worker@machine", 27654);
        endpoint.known_hosts_file = Some(PathBuf::from("/home/test/known hosts"));
        let command = endpoint.command(Path::new("ssh")).unwrap();
        let args: Vec<_> = command
            .as_std()
            .get_args()
            .map(|a| a.to_string_lossy().into_owned())
            .collect();
        for required in [
            "-oStrictHostKeyChecking=yes",
            "-oBatchMode=yes",
            "-oForwardAgent=no",
            "-oForwardX11=no",
            "-oControlPath=none",
            "-oClearAllForwardings=yes",
            "-oGlobalKnownHostsFile=none",
            "UserKnownHostsFile=\"/home/test/known hosts\"",
            "127.0.0.1:27654",
        ] {
            assert!(args.iter().any(|a| a == required), "missing {required}");
        }
        assert_eq!(&args[args.len() - 2..], ["--", "worker@machine"]);
    }

    #[cfg(unix)]
    #[tokio::test(start_paused = true)]
    async fn a_stalled_ssh_handshake_has_a_bounded_deadline() {
        use std::os::unix::fs::PermissionsExt;
        let dir = tempfile::tempdir().unwrap();
        let program = dir.path().join("stalled-ssh");
        std::fs::write(&program, "#!/bin/sh\nexec sleep 30\n").unwrap();
        std::fs::set_permissions(&program, std::fs::Permissions::from_mode(0o700)).unwrap();
        let result =
            connect_with_program(&SshEndpoint::new("host", 27654), "fixture-token", &program).await;
        let Err(error) = result else {
            panic!("stalled handshake was accepted");
        };
        assert!(error.to_string().contains("timed out"), "{error}");
        assert!(!error.to_string().contains("fixture-token"));
    }

    #[tokio::test]
    async fn missing_or_malformed_tokens_fail_before_starting_ssh() {
        let endpoint = SshEndpoint::new("host", 27654);
        for token in ["", "  ", "bad\r\ntoken"] {
            let result = connect_with_program(&endpoint, token, Path::new("/does/not/exist")).await;
            let Err(error) = result else {
                panic!("accepted invalid token");
            };
            assert!(!error.to_string().contains("could not start OpenSSH"));
            assert!(!error.to_string().contains("bad\r\ntoken"));
        }
    }
}
