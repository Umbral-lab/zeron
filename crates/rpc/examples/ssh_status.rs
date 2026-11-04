//! Read an owned server's engine identity without a vendor account or relay.
//! Usage: ssh_status HOST IPC_PORT LOCAL_TOKEN_FILE [SSH_PORT] [KNOWN_HOSTS] [IDENTITY]
//! LOCAL_TOKEN_FILE must contain the remote engine's current IPC bearer.

use std::path::{Path, PathBuf};
use std::time::Duration;
use zeron_rpc::ssh::{SshEndpoint, connect_ssh};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if !(3..=6).contains(&args.len()) {
        anyhow::bail!(
            "usage: ssh_status HOST IPC_PORT LOCAL_TOKEN_FILE [SSH_PORT] [KNOWN_HOSTS] [IDENTITY]"
        );
    }
    let mut endpoint = SshEndpoint::new(&args[0], args[1].parse()?);
    if let Some(port) = args.get(3) {
        endpoint.ssh_port = port.parse()?;
    }
    endpoint.known_hosts_file = args.get(4).map(PathBuf::from);
    endpoint.identity_file = args.get(5).map(PathBuf::from);
    let token = zeron_rpc::ipc_auth::read_token(Path::new(&args[2]))?
        .ok_or_else(|| anyhow::anyhow!("remote IPC token file is empty or missing"))?;
    let connection = connect_ssh(&endpoint, &token).await?;
    let result = tokio::time::timeout(
        Duration::from_secs(5),
        connection
            .client()
            .call(zeron_rpc::methods::ENGINE_INFO, serde_json::Value::Null),
    )
    .await;
    connection.close().await;
    println!("{}", serde_json::to_string_pretty(&result??)?);
    Ok(())
}
