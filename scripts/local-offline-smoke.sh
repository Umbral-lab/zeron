#!/usr/bin/env bash
# Local-core acceptance smoke with egress blocked (A01-A04, headless half).
#
# One engine, default configuration, mock harness, no account and no network:
#   1. start, create a space (a Git checkout with a hosted origin) + chat, run
#      the mock harness to completion;
#   2. idle for ZERON_SMOKE_IDLE seconds (default 75: past the engine's 20 s
#      release-check delay and the harness worker's startup pass);
#   3. stop and restart the engine, verify the records survived and the run
#      was not executed twice.
# The whole sequence runs under scripts/egress-probe/probe.sh, so the smoke
# fails on any outbound attempt by the engine or a child process.
#
# A second pass with ZERON_UPDATE_CHECKS=1 is the positive control: it must
# record the release-feed lookup, which proves the probe observes this engine.
#
# Usage: scripts/local-offline-smoke.sh [--no-build] [--no-control]
# Env:   CARGO_TARGET_DIR, ZERON_SMOKE_IDLE, ZERON_SMOKE_KEEP=1 (keep the work dir)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v cargo >/dev/null 2>&1 || PATH="$HOME/.cargo/bin:$PATH"
build=1; control=1
for arg in "$@"; do
  case "$arg" in
    --no-build) build=0 ;;
    --no-control) control=0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done
TARGET="${CARGO_TARGET_DIR:-$ROOT/target}"
if [[ "$build" -eq 1 ]]; then
  (cd "$ROOT" && cargo build --locked -q -p zeron --no-default-features --bin zeron-engine)
  (cd "$ROOT" && cargo build --locked -q -p zeron-rpc --example local_smoke)
fi
ENGINE="$TARGET/debug/zeron-engine"
DRIVER="$TARGET/debug/examples/local_smoke"
[[ -x "$ENGINE" && -x "$DRIVER" ]] || { echo "FAIL: missing $ENGINE or $DRIVER" >&2; exit 1; }

WORK="$(mktemp -d /tmp/zeron-local-smoke.XXXXXX)"
cleanup() { [[ "${ZERON_SMOKE_KEEP:-0}" == "1" ]] && echo "work dir kept: $WORK" || rm -rf "$WORK"; }
trap cleanup EXIT
IDLE="${ZERON_SMOKE_IDLE:-75}"

# The sequence that runs inside the isolated namespace. The environment is
# rebuilt from scratch so the engine sees a default install: no ZERON_*
# overrides beyond the isolation knobs, no proxy variables, an empty HOME.
cat > "$WORK/sequence.sh" <<'SEQ'
#!/usr/bin/env bash
set -euo pipefail
engine=$1; driver=$2; work=$3; idle=$4; port=$5; shift 5
start_engine() {
  env -i PATH="$PATH" HOME="$work/home" LANG=C.UTF-8 RUST_LOG=info \
    ZERON_DATA_DIR="$work/data" ZERON_IPC_PORT="$port" ZERON_HARNESS=mock "$@" \
    "$engine" >>"$work/engine.log" 2>&1 &
  engine_pid=$!
  for _ in $(seq 60); do
    (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null && return 0
    kill -0 "$engine_pid" 2>/dev/null || { echo "FAIL: engine exited during startup" >&2; return 1; }
    sleep 1
  done
  echo "FAIL: engine IPC :$port did not come up" >&2; return 1
}
stop_engine() {
  kill -TERM "$engine_pid" 2>/dev/null || true
  for _ in $(seq 30); do kill -0 "$engine_pid" 2>/dev/null || return 0; sleep 1; done
  echo "FAIL: engine ignored SIGTERM" >&2; kill -9 "$engine_pid" 2>/dev/null; return 1
}
mkdir -p "$work/home" "$work/workspace"
# A realistic project: a Git checkout whose origin is a hosted remote, so any
# automatic fetch, pull-request poll or avatar lookup would show up as egress.
if command -v git >/dev/null 2>&1; then
  git -C "$work/workspace" init -q
  git -C "$work/workspace" remote add origin https://github.com/example-owner/example-repo.git
  echo "smoke" > "$work/workspace/README"
  git -C "$work/workspace" add README
  git -C "$work/workspace" -c user.name=smoke -c user.email=smoke@localhost \
    -c commit.gpgsign=false commit -q -m "initial"
fi
start_engine "$@"
trap 'kill -9 "$engine_pid" 2>/dev/null || true' EXIT
"$driver" run "$port" "$work/data" "$work/workspace" "$work/state.json"
echo "idle ${idle}s"; sleep "$idle"
stop_engine
start_engine "$@"
"$driver" verify "$port" "$work/data" "$work/state.json"
stop_engine
trap - EXIT
SEQ
chmod +x "$WORK/sequence.sh"

PROBE="$ROOT/scripts/egress-probe/probe.sh"
BUDGET=$((IDLE + 300))

echo "=== pass 1: default configuration, egress blocked"
set +e
"$PROBE" "$WORK/probe-default" "$BUDGET" -- "$WORK/sequence.sh" "$ENGINE" "$DRIVER" "$WORK/default" "$IDLE" 27821
probe_status=$?
set -e
sequence_status=$(cat "$WORK/probe-default/command.status" 2>/dev/null || echo unknown)
[[ "$probe_status" -ne 4 ]] || { echo "SKIP: network isolation unavailable; the smoke did not run"; exit 4; }
[[ "$sequence_status" == "0" ]] || { echo "FAIL: local sequence exited $sequence_status"; tail -n 30 "$WORK/default/engine.log" 2>/dev/null || true; exit 1; }
[[ "$probe_status" -eq 0 ]] || { echo "FAIL: the default configuration attempted egress (see above)"; exit 1; }
echo "PASS: local core works with zero egress attempts"

if [[ "$control" -eq 1 ]]; then
  echo "=== pass 2: positive control (ZERON_UPDATE_CHECKS=1 must be observed)"
  set +e
  "$PROBE" "$WORK/probe-control" "$BUDGET" -- "$WORK/sequence.sh" "$ENGINE" "$DRIVER" "$WORK/control" 30 27822 ZERON_UPDATE_CHECKS=1 >"$WORK/control.out" 2>&1
  control_status=$?
  set -e
  if [[ "$control_status" -eq 3 ]] && grep -q ' DNS ' "$WORK/probe-control/sink.log"; then
    echo "PASS: control run recorded egress: $(grep ' DNS ' "$WORK/probe-control/sink.log" | awk '{print $3}' | sort -u | tr '\n' ' ')"
  else
    echo "FAIL: the control run recorded no egress (status $control_status); the probe is not observing the engine"
    cat "$WORK/control.out"; exit 1
  fi
fi
echo "PASS: local offline smoke complete"
