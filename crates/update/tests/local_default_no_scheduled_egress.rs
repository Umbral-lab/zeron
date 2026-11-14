//! Default local behavior of the desktop release checker (OPS-001B).
//!
//! Baseline main (eb1958ba) polled `{edge}/releases` from the desktop checker
//! after its 2 s initial delay with no consent switch in the environment. With
//! the consent gate in place, a default desktop spawn must stay local: no
//! scheduled egress at startup or on idle wakes, while the explicit
//! "Check for Updates…" path still works because the user asked for it.

use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

use tokio::io::{AsyncReadExt, AsyncWriteExt};
use zeron_update::Updater;

async fn counting_update_feed() -> (String, Arc<AtomicUsize>, tokio::task::JoinHandle<()>) {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    let requests = Arc::new(AtomicUsize::new(0));
    let seen = requests.clone();
    let server = tokio::spawn(async move {
        loop {
            let Ok((mut socket, _)) = listener.accept().await else {
                return;
            };
            let seen = seen.clone();
            tokio::spawn(async move {
                // Read the request before answering: replying first confuses
                // the client's connection reuse.
                let mut request = [0u8; 2048];
                let Ok(n) = socket.read(&mut request).await else {
                    return;
                };
                if n == 0 {
                    return;
                }
                seen.fetch_add(1, Ordering::SeqCst);
                let body = "{\"version\":\"999.0.0\",\"files\":{}}";
                let response = format!(
                    "HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{}",
                    body.len(),
                    body
                );
                let _ = socket.write_all(response.as_bytes()).await;
            });
        }
    });
    (format!("http://127.0.0.1:{port}"), requests, server)
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn default_desktop_checker_stays_local_until_the_user_asks() {
    let (edge_url, requests, server) = counting_update_feed().await;
    // Deterministic default: this integration binary holds one test, so the
    // process environment is its own to fix. Consent off = local.
    unsafe { std::env::set_var("ZERON_UPDATE_CHECKS", "0") };
    let updater = Updater::spawn_desktop(edge_url);

    // Past the 2 s desktop initial delay, plus wakes: nothing may be sent.
    tokio::time::sleep(std::time::Duration::from_millis(3_500)).await;
    for _ in 0..5 {
        updater.poke();
        tokio::time::sleep(std::time::Duration::from_millis(120)).await;
    }
    assert_eq!(
        requests.load(Ordering::SeqCst),
        0,
        "a default desktop spawn must not poll the release feed without check consent"
    );
    assert_eq!(updater.watch().borrow().latest_version, None);

    // The explicit user action is its own decision and still works.
    let status = updater.check().await.unwrap();
    assert!(status.update_available);
    assert_eq!(status.latest_version.as_deref(), Some("999.0.0"));
    assert!(requests.load(Ordering::SeqCst) >= 1);

    updater.shutdown().await;
    server.abort();
}
