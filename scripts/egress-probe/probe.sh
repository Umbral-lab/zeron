#!/usr/bin/env bash
# Run a command with all egress blocked and every attempt recorded.
#
# Usage: probe.sh OUT_DIR SECONDS -- COMMAND...
#
# COMMAND (and every child process) runs in a fresh network + mount namespace
# that has loopback only. A DNS sink answers every name with 127.0.0.2 and logs
# it; a TCP sink on 127.0.0.2:80/443 logs each connection with its TLS SNI; and,
# when strace is installed, every connect() is traced with the calling process
# name, so targets that bypass DNS (IP literals, /etc/hosts entries) are caught too. Nothing reaches a real
# host. Exit status: 0 = no egress attempt, 3 = egress attempted, 4 = the
# namespace could not be created (the probe did not run).
set -euo pipefail
[[ $# -ge 4 && "$3" == "--" ]] || { echo "usage: $0 OUT_DIR SECONDS -- COMMAND..." >&2; exit 2; }
out=$1; secs=$2; shift 3
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$out"; out=$(cd "$out" && pwd)
: > "$out/sink.log"; : > "$out/strace.log"

ns=(unshare -n -m)
[[ $(id -u) -eq 0 ]] || ns=(unshare -r -n -m)
if ! "${ns[@]}" true 2>/dev/null; then
  echo "egress-probe: cannot create a network namespace here (needs root or unprivileged user namespaces)" >&2
  exit 4
fi

export PROBE_OUT="$out" PROBE_SECS="$secs" PROBE_HERE="$here"
"${ns[@]}" bash -c '
  set -e
  python3 -I "$PROBE_HERE/lo_up.py"
  echo "nameserver 127.0.0.1" > "$PROBE_OUT/resolv.conf"
  mount --bind "$PROBE_OUT/resolv.conf" /etc/resolv.conf
  python3 -I "$PROBE_HERE/sink.py" "$PROBE_OUT/sink.log" &
  sink=$!
  for _ in $(seq 50); do grep -q " SINK ready" "$PROBE_OUT/sink.log" && break; sleep 0.1; done
  set +e
  if command -v strace >/dev/null 2>&1; then
    timeout -s TERM "$PROBE_SECS" strace -f -qq -Y -e trace=connect -o "$PROBE_OUT/strace.log" "$@"
  else
    echo "egress-probe: strace not installed; IP-literal and /etc/hosts targets are not traced" >&2
    timeout -s TERM "$PROBE_SECS" "$@"
  fi
  echo "$?" > "$PROBE_OUT/command.status"
  kill "$sink" 2>/dev/null
' _ "$@"

dns=$(grep ' DNS ' "$out/sink.log" | awk '{print $3}' | sort | uniq -c || true)
tcp=$(grep ' TCP:' "$out/sink.log" || true)
direct=$(grep -E 'sa_family=AF_INET6?,' "$out/strace.log" \
  | grep -vE 'inet_addr\("127\.|inet_pton\(AF_INET6, "::1"|sin6?_port=htons\(0\)' \
  | sed -E 's/^[0-9]+(<[^>]*>)? +/\1 /; s/connect\([0-9]+, /connect(/' | sort | uniq -c || true)
echo "--- DNS names queried";            [[ -n "$dns" ]] && echo "$dns" || echo "(none)"
echo "--- TCP sink connections";         [[ -n "$tcp" ]] && echo "$tcp" || echo "(none)"
echo "--- non-loopback connect() calls"; [[ -n "$direct" ]] && echo "$direct" || echo "(none)"
echo "--- command status: $(cat "$out/command.status" 2>/dev/null || echo unknown)"
[[ -z "$dns" && -z "$tcp" && -z "$direct" ]] || exit 3
