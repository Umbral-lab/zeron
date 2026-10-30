import json, re, urllib.request, pathlib, time
toml = pathlib.Path("/opt/data/home/zeron/Cargo.toml").read_text()
block = toml.split("[workspace.dependencies]")[1]
block = block.split("\n[")[0]
names = re.findall(r'^([A-Za-z0-9_-]+)\s*=', block, re.M)
lock = pathlib.Path("/opt/data/home/zeron/Cargo.lock").read_text()
lockver = dict(re.findall(r'name = "([^"]+)"\nversion = "([^"]+)"', lock))
print("direct workspace deps:", len(names))
print("locked packages:", len(lockver))
out = {}
for n in names:
    v = lockver.get(n)
    url = "https://crates.io/api/v1/crates/" + n + ("/" + v if v else "")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "worker-a-baseline-scan"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
        info = d.get("version") or d.get("crate", {})
        out[n] = {"license": info.get("license"), "version": info.get("num_version") or info.get("newest_version")}
    except Exception as e:
        out[n] = {"license": None, "error": str(e)[:60]}
    time.sleep(0.25)
lic = {}
for n, v in out.items():
    l = v.get("license") or "UNKNOWN"
    lic.setdefault(l, []).append(n)
print("total queried:", len(out))
for l, deps in sorted(lic.items(), key=lambda kv: -len(kv[1])):
    print("%-40s %3d  %s" % (l, len(deps), ", ".join(sorted(deps)[:8]) + (" ..." if len(deps) > 8 else "")))
pathlib.Path("/opt/data/cache/scratch/direct-dep-licenses.json").write_text(json.dumps(out, indent=1))
