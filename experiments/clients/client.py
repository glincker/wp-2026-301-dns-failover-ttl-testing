#!/usr/bin/env python3
"""Python client (glibc getaddrinfo via urllib). Usage: client.py HOST PORT MODE DURATION_S INTERVAL_MS CONNECT_TIMEOUT|none CAP_S
Prints one JSON line per request: start time in epoch ms, duration, body or error."""
import json, signal, socket, sys, time, urllib.request
host, port, mode, dur, interval, cto, cap = sys.argv[1:8]
dur, interval, cap = float(dur), float(interval) / 1000, float(cap)
cto = None if cto == "none" else float(cto)
def out(**k): print(json.dumps(k), flush=True)
signal.signal(signal.SIGALRM, lambda *a: (out(t=int(time.time() * 1000), err="cap"), sys.exit(0)))
try:
    out(order=[a[4][0] for a in socket.getaddrinfo(host, int(port), type=socket.SOCK_STREAM)])
except Exception as e:
    out(order=[], err=str(e))
end = time.time() + dur
while True:
    t = time.time()
    signal.alarm(int(cap) + 1)
    try:
        body = urllib.request.urlopen("http://%s:%s/" % (host, port), timeout=cto).read().decode().strip()
        out(t=int(t * 1000), ms=int((time.time() - t) * 1000), body=body)
    except Exception as e:
        out(t=int(t * 1000), ms=int((time.time() - t) * 1000), err=type(e).__name__)
    signal.alarm(0)
    if mode == "once" or time.time() >= end:
        break
    time.sleep(max(0, interval - (time.time() - t)))
