#!/usr/bin/env python3
"""Host side driver for E6 (client DNS caching) and E7 (multi-address fallback). Run through the shell wrappers.

  clients.py e6 RUNTIME VARIANT RUN_S EXPECTED_CACHE_S|none
  clients.py e7 RUNTIME FAMILY DEADMODE CONNECT_TIMEOUT|none CAP_S

Clients print raw JSON lines inside their containers; this script turns client epoch milliseconds into times relative to
the record change (taken from the authoritative server's own clock, same kernel clock), prints one JSON record per case.
Container names and addresses come from the environment set by common.sh."""
import json, os, subprocess, sys, threading, time, random

E = os.environ
LAB = "ZONE"
ZONE = "lab.test."
LABEL = {E["BE1_IP"]: "old", E["BE2_IP"]: "new", E["REF_IP"]: "refusing", E["HOLE_IP"]: "blackhole",
         E["P6"] + "23": "refusing", E["P6"] + "24": "blackhole", E["P6"] + "22": "new"}
JAVA_TTL = {"default": None, "ttl0": "0", "ttl5": "5", "ttlinf": "-1"}

def ctl(**kw):
    out = subprocess.run(["docker", "exec", E["C_PROBE"], "python", "-I", "-u", "/dnslab.py", "ctl"] + ["%s=%s" % kv for kv in kw.items()],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)

def command(runtime, variant, host, mode, dur, interval, cto, cap):
    args = [host, "8080", mode, str(dur), str(interval), str(cto), str(cap)]
    if runtime == "python":
        return E["C_PYC"], [], ["python", "/tmp/client.py"] + args
    if runtime in ("go-pure", "go-cgo"):
        return E["C_GO"], ["-e", "GODEBUG=netdns=" + runtime.split("-")[1]], ["/tmp/client-go"] + args
    if runtime == "curl":
        extra = {"fresh": [], "long": ["long"]}[variant]
        return E["C_GO"], [], ["python3", "/tmp/client_curl.py"] + args + extra
    if runtime == "java":
        ttl = JAVA_TTL[variant]
        pre = []
        if ttl is not None:
            subprocess.run(["docker", "exec", E["C_JAVA"], "sh", "-c", "echo networkaddress.cache.ttl=%s > /tmp/sec.props" % ttl], check=True)
            pre = ["-e", "JAVA_TOOL_OPTIONS=-Djava.security.properties=/tmp/sec.props"]
        return E["C_JAVA"], pre, ["java", "-cp", "/tmp", "Client"] + args
    sys.exit("unknown runtime " + runtime)

def run_client(cont, envargs, cmd, on_first=None):
    """Start the client, return its parsed lines. on_first runs in the main thread once the first request line arrived."""
    p = subprocess.Popen(["docker", "exec"] + envargs + [cont] + cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    lines, first = [], threading.Event()
    def rd():
        for ln in p.stdout:
            ln = ln.strip()
            if ln.startswith("{"):
                d = json.loads(ln)
                lines.append(d)
                if "t" in d and "attempt" not in d: first.set()
    th = threading.Thread(target=rd, daemon=True); th.start()
    if on_first:
        first.wait(120)
        on_first(lines)
    p.wait(); th.join(5)
    return lines

def label(d):
    b = d.get("body")
    return LABEL.get(b, b) if b else "error:" + str(d.get("err"))

def e6(runtime, variant, run_s, expected):
    name = "e6-%06d.%s" % (random.randrange(10**6), ZONE)
    ctl(cmd="set", name=name, addr=E["BE1_IP"], ttl=2)
    cont, env, cmd = command(runtime, variant, name.rstrip("."), "poll", run_s, 500, "none", 10)
    st = {}
    def flip(lines):
        t_first = min([d["t"] for d in lines if "t" in d and "attempt" not in d] or [0])
        time.sleep(3.5)
        st["t_flip"] = ctl(cmd="set", name=name, addr=E["BE2_IP"], ttl=2)["t_ms"]
        st["t_first"] = t_first
    lines = run_client(cont, env, cmd, flip)
    if "t_flip" not in st: sys.exit("e6: client produced no output")
    reqs = [d for d in lines if "t" in d and "attempt" not in d]
    tf = st["t_flip"]
    rel = [((d["t"] - tf) / 1000.0, label(d)) for d in reqs]
    after = [(t, l) for t, l in rel if t >= 0]
    olds = [t for t, l in after if l == "old"]; news = [t for t, l in after if l == "new"]
    trans, prev = [], None
    for t, l in rel:
        if l != prev: trans.append([round(t, 2), l]); prev = l
    print(json.dumps({"exp": "e6", "runtime": runtime, "variant": variant, "record_ttl_s": 2, "flip_after_first_s": round((tf - st["t_first"]) / 1000.0, 2),
                      "runtime_cache_s": expected if expected in ("none", "forever") else float(expected), "requests": len(reqs),
                      "last_old_after_flip_s": round(max(olds), 2) if olds else None, "first_new_after_flip_s": round(min(news), 2) if news else None,
                      "transitions": trans, "errors": sum(1 for _, l in rel if l.startswith("error"))}, sort_keys=True), flush=True)

def e7(runtime, family, deadmode, cto, cap):
    name = "e7-%06d.%s" % (random.randrange(10**6), ZONE)
    dead = {"refused": (E["REF_IP"], E["P6"] + "23"), "blackhole": (E["HOLE_IP"], E["P6"] + "24")}[deadmode]
    if family == "v4":
        ctl(cmd="set", name=name, addr="%s,%s" % (dead[0], E["BE2_IP"]), ttl=60)   # dead address listed first
    else:
        ctl(cmd="set", name=name, addr="%s,%s" % (dead[1], E["BE2_IP"]), ttl=60)   # AAAA dead, A alive
    variant = "fresh" if runtime == "curl" else "default"
    cont, env, cmd = command(runtime, variant, name.rstrip("."), "once", 0, 500, cto, cap)
    t0 = time.time()
    lines = run_client(cont, env, cmd)
    order = next((d["order"] for d in lines if "order" in d), None)
    req = next((d for d in lines if "t" in d and "attempt" not in d), {})
    att = [d["attempt"] for d in lines if "attempt" in d] or req.get("attempts")
    t_req = req.get("t")
    att_rel = None
    if any("attempt" in d for d in lines) and t_req:
        att_rel = [[round((d["t"] - t_req) / 1000.0, 2), LABEL.get(d["attempt"].rsplit(":", 1)[0].strip("[]"), "?")] for d in lines if "attempt" in d]
    outcome = label(req) if req else "error:none"
    print(json.dumps({"exp": "e7", "runtime": runtime, "family": family, "dead_mode": deadmode, "connect_timeout_s": None if cto == "none" else float(cto),
                      "cap_s": float(cap), "address_order": None if order is None else [LABEL.get(a, a) for a in order],
                      "outcome": outcome, "elapsed_s": round(req["ms"] / 1000.0, 2) if "ms" in req else None,
                      "attempts": (att_rel if att_rel is not None else [LABEL.get(a.rsplit(":", 1)[0].strip("[]"), "?") for a in att] if att else None)}, sort_keys=True), flush=True)

if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"e6": e6, "e7": e7}[c](*a)
