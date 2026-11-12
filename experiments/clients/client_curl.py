#!/usr/bin/env python3
"""curl client. Usage: client_curl.py HOST PORT MODE DURATION_S INTERVAL_MS CONNECT_TIMEOUT|none CAP_S [long]
Default: a new curl process per request. 'long': one curl process, globbed URLs paced with --rate, so its in-process DNS cache applies."""
import json, subprocess, sys, time
host, port, mode, dur, interval, cto, cap = sys.argv[1:8]
long_mode = len(sys.argv) > 8 and sys.argv[8] == "long"
dur, interval = float(dur), float(interval) / 1000
def out(**k): print(json.dumps(k), flush=True)
base = ["curl", "-sS", "-o", "/dev/null", "--max-time", cap, "-w", "%{remote_ip} %{time_total}\n"]
if cto != "none": base += ["--connect-timeout", cto]
url = "http://%s:%s/" % (host, port)
if long_mode:
    n = int(dur / interval) + 1
    p = subprocess.Popen(["stdbuf", "-oL"] + base + ["--rate", "%d/s" % round(1 / interval), "%s?[1-%d]" % (url, n)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    for line in p.stdout:
        f = line.split()
        ip, tt = (f[0], f[1]) if len(f) == 2 else ("", f[0] if f else "0")
        out(t=int(time.time() * 1000 - float(tt) * 1000), ms=int(float(tt) * 1000), body=ip if ip else None, **({} if ip else {"err": "curl"}))
    sys.exit(0)
end = time.time() + dur
while True:
    t = time.time()
    p = subprocess.run(base[:1] + ["-v"] + base[1:] + [url], capture_output=True, text=True)
    att = [l.split("Trying ")[1].split("...")[0] for l in p.stderr.splitlines() if "Trying " in l]
    f = p.stdout.split()
    ip = f[0] if f and p.returncode == 0 else ""
    out(t=int(t * 1000), ms=int((time.time() - t) * 1000), attempts=att, **({"body": ip} if ip else {"err": "curl%d" % p.returncode}))
    if mode == "once" or time.time() >= end: break
    time.sleep(max(0, interval - (time.time() - t)))
