#!/usr/bin/env python3
"""DNS + TCP sink for blocked-egress probes.

Answers every A query with 127.0.0.2 and logs the queried name; accepts TCP on
127.0.0.2:80/443 and logs each connection (with TLS SNI when present). Run it
inside an isolated network namespace so nothing can leave the host.
"""
import socket, struct, sys, threading, time

LOG = open(sys.argv[1], "a", buffering=1)
T0 = time.time()

def log(kind, detail):
    LOG.write(f"{time.time() - T0:8.2f} {kind} {detail}\n")

def qname(data):
    labels, i = [], 12
    while i < len(data) and data[i]:
        n = data[i]
        labels.append(data[i + 1:i + 1 + n].decode("ascii", "replace"))
        i += n + 1
    return ".".join(labels), i + 1

def dns():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 53))
    while True:
        data, addr = s.recvfrom(2048)
        try:
            name, end = qname(data)
            qtype = struct.unpack(">H", data[end:end + 2])[0]
            log("DNS", f"{name} type={qtype}")
            question = data[12:end + 4]
            if qtype == 1:
                answer = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x05\x00\x04\x7f\x00\x00\x02"
                head = data[:2] + b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"
                s.sendto(head + question + answer, addr)
            else:
                head = data[:2] + b"\x81\x80\x00\x01\x00\x00\x00\x00\x00\x00"
                s.sendto(head + question, addr)
        except Exception as e:  # malformed packet: log and keep serving
            log("DNS_ERR", repr(e))

def sni(hello):
    try:
        i = 43
        i += 1 + hello[i]
        i += 2 + struct.unpack(">H", hello[i:i + 2])[0]
        i += 1 + hello[i]
        end = i + 2 + struct.unpack(">H", hello[i:i + 2])[0]
        i += 2
        while i + 4 <= end:
            etype, elen = struct.unpack(">HH", hello[i:i + 4])
            if etype == 0:
                n = struct.unpack(">H", hello[i + 7:i + 9])[0]
                return hello[i + 9:i + 9 + n].decode("ascii", "replace")
            i += 4 + elen
    except Exception:
        pass
    return None

def tcp(port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.2", port))
    s.listen(64)
    while True:
        c, addr = s.accept()
        c.settimeout(2)
        try:
            first = c.recv(4096)
        except Exception:
            first = b""
        if first[:1] == b"\x16":
            detail = f"tls sni={sni(first)}"
        else:
            detail = "plain " + first.split(b"\r\n")[0][:120].decode("ascii", "replace")
        log(f"TCP:{port}", detail)
        c.close()

threading.Thread(target=dns, daemon=True).start()
for p in (80, 443):
    threading.Thread(target=tcp, args=(p,), daemon=True).start()
log("SINK", "ready")
while True:
    time.sleep(3600)
