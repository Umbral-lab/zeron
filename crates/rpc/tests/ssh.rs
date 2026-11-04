//! Explicit real-OpenSSH verification. Uses only disposable loopback fixtures.
#![cfg(unix)]

use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};
use std::time::Duration;

use async_trait::async_trait;
use futures::{StreamExt, stream};
use serde_json::{Value, json};
use zeron_rpc::ssh::{SshEndpoint, connect_ssh};
use zeron_rpc::{RpcError, RpcReply, RpcService, serve_ws_listener};

struct Engine(Arc<AtomicUsize>);
struct Active(Arc<AtomicUsize>);
impl Drop for Active {
    fn drop(&mut self) {
        self.0.fetch_sub(1, Ordering::SeqCst);
    }
}
#[async_trait]
impl RpcService for Engine {
    async fn handle(&self, method: &str, params: Value) -> Result<RpcReply, RpcError> {
        match method {
            zeron_rpc::methods::ENGINE_INFO => Ok(RpcReply::Value(
                json!({"deviceId":"owned-fixture", "workspaceId":"scoped-fixture"}),
            )),
            "Echo" => Ok(RpcReply::Value(params)),
            "Watch" => {
                self.0.fetch_add(1, Ordering::SeqCst);
                let active = Active(self.0.clone());
                let tail = stream::unfold(active, |active| async move {
                    std::future::pending::<()>().await;
                    Some((json!(null), active))
                });
                Ok(RpcReply::Stream(
                    stream::once(async { json!("ready") }).chain(tail).boxed(),
                ))
            }
            _ => Err(RpcError::UnknownMethod(method.into())),
        }
    }
}

struct Sshd {
    child: Child,
    dir: tempfile::TempDir,
    endpoint: SshEndpoint,
}
impl Drop for Sshd {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
fn key(path: &Path) {
    let result = Command::new("ssh-keygen")
        .args(["-q", "-t", "ed25519", "-N", "", "-f"])
        .arg(path)
        .output()
        .expect("ssh-keygen is required for this explicit integration test");
    assert!(
        result.status.success(),
        "ssh-keygen failed: {}",
        String::from_utf8_lossy(&result.stderr)
    );
}
impl Sshd {
    async fn start(ipc_port: u16) -> Self {
        let dir = tempfile::tempdir().unwrap();
        key(&dir.path().join("host"));
        key(&dir.path().join("client"));
        let user =
            String::from_utf8(Command::new("id").arg("-un").output().unwrap().stdout).unwrap();
        let public = std::fs::read_to_string(dir.path().join("client.pub")).unwrap();
        std::fs::write(dir.path().join("authorized_keys"), format!(
            "restrict,port-forwarding,permitopen=\"127.0.0.1:{ipc_port}\",command=\"/bin/false\" {public}"
        )).unwrap();
        let reservation = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = reservation.local_addr().unwrap().port();
        let root = dir.path().display();
        let config = format!(
            "Port {port}\nListenAddress 127.0.0.1\nHostKey {root}/host\nPidFile {root}/pid\n\
             AuthorizedKeysFile {root}/authorized_keys\nAllowUsers {}\n\
             AuthenticationMethods publickey\nPubkeyAuthentication yes\nPasswordAuthentication no\n\
             KbdInteractiveAuthentication no\nUsePAM no\nStrictModes no\nAllowTcpForwarding local\n\
             GatewayPorts no\nPermitTTY no\nLogLevel ERROR\n",
            user.trim()
        );
        std::fs::write(dir.path().join("sshd_config"), config).unwrap();
        let public = std::fs::read_to_string(dir.path().join("host.pub")).unwrap();
        let known = dir.path().join("known hosts");
        std::fs::write(&known, format!("[127.0.0.1]:{port} {public}")).unwrap();
        let sshd = if Path::new("/usr/sbin/sshd").exists() {
            "/usr/sbin/sshd"
        } else {
            "sshd"
        };
        drop(reservation);
        let child = Command::new(sshd)
            .args(["-D", "-e", "-f"])
            .arg(dir.path().join("sshd_config"))
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(std::fs::File::create(dir.path().join("sshd.log")).unwrap())
            .spawn()
            .expect("sshd is required for this explicit integration test");
        let mut endpoint = SshEndpoint::new(format!("{}@127.0.0.1", user.trim()), ipc_port);
        endpoint.ssh_port = port;
        endpoint.known_hosts_file = Some(known);
        endpoint.identity_file = Some(dir.path().join("client"));
        let mut fixture = Self {
            child,
            dir,
            endpoint,
        };
        tokio::time::timeout(Duration::from_secs(3), async {
            loop {
                if let Some(status) = fixture.child.try_wait().unwrap() {
                    panic!(
                        "fixture sshd exited {status}: {}",
                        std::fs::read_to_string(fixture.dir.path().join("sshd.log")).unwrap()
                    );
                }
                if tokio::net::TcpStream::connect(("127.0.0.1", port))
                    .await
                    .is_ok()
                {
                    break;
                }
                tokio::time::sleep(Duration::from_millis(20)).await;
            }
        })
        .await
        .expect("fixture sshd must listen");
        fixture
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
#[ignore = "requires OpenSSH ssh, ssh-keygen and sshd; run explicitly on supported hosts"]
async fn real_openssh_authentication_rpc_disconnect_and_reconnect() {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    let active = Arc::new(AtomicUsize::new(0));
    let token = zeron_rpc::ipc_auth::generate_token().unwrap();
    let server = tokio::spawn(serve_ws_listener(
        listener,
        Arc::new(Engine(active.clone())),
        token.clone(),
    ));
    let mut sshd = Sshd::start(port).await;

    if let Some(example) = std::env::var_os("ZERON_SSH_STATUS_EXAMPLE") {
        let token_file = sshd.dir.path().join("local-token");
        zeron_rpc::ipc_auth::write_token(&token_file, &token).unwrap();
        let result = Command::new(example)
            .arg(&sshd.endpoint.destination)
            .arg(port.to_string())
            .arg(&token_file)
            .arg(sshd.endpoint.ssh_port.to_string())
            .arg(sshd.endpoint.known_hosts_file.as_ref().unwrap())
            .arg(sshd.endpoint.identity_file.as_ref().unwrap())
            .output()
            .unwrap();
        assert!(
            result.status.success(),
            "CLI failed: {}",
            String::from_utf8_lossy(&result.stderr)
        );
        let identity: Value = serde_json::from_slice(&result.stdout).unwrap();
        assert_eq!(identity["deviceId"], "owned-fixture");
        println!("ssh_status CLI returned the authenticated server identity");
    }

    // A legitimate SSH key does NOT bypass the engine's independent bearer.
    let denied = connect_ssh(&sshd.endpoint, "wrong-token").await;
    let Err(error) = denied else {
        panic!("accepted wrong IPC token");
    };
    assert!(error.to_string().contains("401"), "{error}");
    assert!(!error.to_string().contains("wrong-token"));

    // Pinning is mandatory: neither unknown nor changed keys are accepted.
    let mut untrusted = sshd.endpoint.clone();
    let unknown = sshd.dir.path().join("unknown_hosts");
    std::fs::write(&unknown, "").unwrap();
    untrusted.known_hosts_file = Some(unknown.clone());
    assert!(
        connect_ssh(&untrusted, &token).await.is_err(),
        "accepted unknown host key"
    );
    key(&sshd.dir.path().join("other_host"));
    let other = std::fs::read_to_string(sshd.dir.path().join("other_host.pub")).unwrap();
    std::fs::write(
        &unknown,
        format!("[127.0.0.1]:{} {other}", untrusted.ssh_port),
    )
    .unwrap();
    assert!(
        connect_ssh(&untrusted, &token).await.is_err(),
        "accepted changed host key"
    );

    for _ in 0..2 {
        let connection = connect_ssh(&sshd.endpoint, &token).await.unwrap();
        assert_eq!(
            connection
                .client()
                .call("Echo", json!({"machine":"owned", "workspace":"fixture"}))
                .await
                .unwrap(),
            json!({"machine":"owned", "workspace":"fixture"})
        );
        let mut subscription = connection
            .client()
            .subscribe_scoped("Watch", json!(null))
            .await
            .unwrap();
        assert_eq!(subscription.recv().await, Some(json!("ready")));
        assert_eq!(active.load(Ordering::SeqCst), 1);
        connection.close().await;
        assert!(
            tokio::time::timeout(Duration::from_secs(2), subscription.recv())
                .await
                .unwrap()
                .is_none()
        );
        tokio::time::timeout(Duration::from_secs(2), async {
            while active.load(Ordering::SeqCst) != 0 {
                tokio::time::sleep(Duration::from_millis(10)).await;
            }
        })
        .await
        .expect("disconnect must cancel server-side streams");
    }

    // Dropping the owner must also cancel streams retained by UI subscribers.
    let connection = connect_ssh(&sshd.endpoint, &token).await.unwrap();
    let mut subscription = connection
        .client()
        .subscribe_scoped("Watch", json!(null))
        .await
        .unwrap();
    assert_eq!(subscription.recv().await, Some(json!("ready")));
    drop(connection);
    assert!(
        tokio::time::timeout(Duration::from_secs(2), subscription.recv())
            .await
            .unwrap()
            .is_none()
    );
    tokio::time::timeout(Duration::from_secs(2), async {
        while active.load(Ordering::SeqCst) != 0 {
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .expect("dropped connections must cancel remote streams");

    // Revoking the SSH key denies fresh connections; explicit disconnect is
    // still required to terminate an already-authenticated SSH session.
    let authorized = std::fs::read(sshd.dir.path().join("authorized_keys")).unwrap();
    std::fs::write(sshd.dir.path().join("authorized_keys"), "").unwrap();
    assert!(
        connect_ssh(&sshd.endpoint, &token).await.is_err(),
        "accepted revoked SSH key"
    );
    std::fs::write(sshd.dir.path().join("authorized_keys"), authorized).unwrap();

    // Losing the listening sshd prevents a subsequent explicit reconnect.
    let connection = connect_ssh(&sshd.endpoint, &token).await.unwrap();
    sshd.child.kill().unwrap();
    sshd.child.wait().unwrap();
    // Killing the listening sshd need not kill established SSH sessions.
    connection.close().await;
    assert!(connect_ssh(&sshd.endpoint, &token).await.is_err());
    server.abort();
}

#[tokio::test]
async fn dropping_rpc_client_releases_retained_subscriptions() {
    let (out, mut peer) = tokio::sync::mpsc::channel(4);
    let (_keep_peer_open, inbound) = tokio::sync::mpsc::channel(4);
    let client = zeron_rpc::RpcClient::new(out, inbound);
    let mut subscription = client.subscribe_scoped("Watch", json!(null)).await.unwrap();
    assert!(peer.recv().await.is_some());
    drop(client);
    assert!(
        tokio::time::timeout(Duration::from_millis(200), subscription.recv())
            .await
            .expect("client drop must close subscriptions even while the peer stays open")
            .is_none()
    );
}
