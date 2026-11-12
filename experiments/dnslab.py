#!/usr/bin/env python3
"""DNS lab tool. Runs inside python containers on a private docker network.

  dnslab.py auth                 a scriptable authoritative server (UDP 53, control on UDP 5353)
  dnslab.py e1|e2|e3|e4|e5 ...   measurement routines, run from the probe container

Every measurement prints one JSON record per line on stdout. No wall-clock dates are printed.
"""
import json, os, random, socket, struct, sys, threading, time

AUTH_IP = os.environ.get("AUTH_IP", "172.29.77.10")
RESOLVERS = {"unbound": os.environ.get("UNBOUND_IP", "172.29.77.11"),
             "bind": os.environ.get("BIND_IP", "172.29.77.12")}
ZONE = "lab.test."

# ---------------------------------------------------------------- wire format
def enc_name(n):
    out = b""
    for lab in n.rstrip(".").split("."):
        if lab:
            out += bytes([len(lab)]) + lab.encode()
    return out + b"\0"

def read_name(buf, off):
    labels, jumped, end = [], False, off
    while True:
        ln = buf[off]
        if ln == 0:
            off += 1
            break
        if ln & 0xC0 == 0xC0:
            ptr = ((ln & 0x3F) << 8) | buf[off + 1]
            if not jumped:
                end = off + 2
            jumped, off = True, ptr
            continue
        labels.append(buf[off + 1:off + 1 + ln].decode())
        off += 1 + ln
    if not jumped:
        end = off
    return ".".join(labels).lower() + ".", end

def build_query(name, qtype=1, rd=True):
    qid = random.randrange(65536)
    return qid, struct.pack(">HHHHHH", qid, 0x0100 if rd else 0, 1, 0, 0, 0) + enc_name(name) + struct.pack(">HH", qtype, 1)

def parse_response(buf):
    qid, flags, qd, an, ns, ar = struct.unpack(">HHHHHH", buf[:12])
    off = 12
    for _ in range(qd):
        _, off = read_name(buf, off)
        off += 4
    res = {"id": qid, "rcode": flags & 15, "aa": bool(flags & 0x400), "answers": [], "soa_ttl": None, "soa_min": None}
    for sect, cnt in (("an", an), ("ns", ns), ("ar", ar)):
        for _ in range(cnt):
            _, off = read_name(buf, off)
            rtype, _, ttl, rdlen = struct.unpack(">HHIH", buf[off:off + 10])
            off += 10
            if sect == "an" and rtype == 1:
                res["answers"].append({"addr": socket.inet_ntoa(buf[off:off + 4]), "ttl": ttl})
            if sect == "ns" and rtype == 6:
                res["soa_ttl"] = ttl
                _, o2 = read_name(buf, off)
                _, o2 = read_name(buf, o2)
                res["soa_min"] = struct.unpack(">I", buf[o2 + 16:o2 + 20])[0]
            off += rdlen
    return res

def ask(server, name, qtype=1, timeout=4.0, rd=True):
    qid, pkt = build_query(name, qtype, rd)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    t0 = time.monotonic()
    try:
        s.sendto(pkt, (server, 53))
        while True:
            data, _ = s.recvfrom(4096)
            r = parse_response(data)
            if r["id"] == qid:
                r["rtt_ms"] = round((time.monotonic() - t0) * 1000)
                return r
    except socket.timeout:
        return {"rcode": -1, "answers": [], "rtt_ms": round((time.monotonic() - t0) * 1000), "soa_ttl": None, "soa_min": None}
    finally:
        s.close()

# ---------------------------------------------------------------- authoritative server
class Zone:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()
    def reset(self):
        self.records, self.counts = {}, {}
        self.down, self.soa_ttl, self.soa_min, self.soa_mode = False, 60, 60, "capped"

def serve_auth():
    z = Zone()
    def handle(data):
        qid, flags, qd = struct.unpack(">HHH", data[:6])
        name, off = read_name(data, 12)
        qtype = struct.unpack(">H", data[off:off + 2])[0]
        question = data[12:off + 4]
        with z.lock:
            z.counts[name] = z.counts.get(name, 0) + 1
            if z.down:
                return None
            rec = z.records.get(name)
            soa_ttl, soa_min = z.soa_ttl, z.soa_min
            if z.soa_mode == "capped":
                soa_ttl = min(soa_ttl, soa_min)   # RFC 2308 section 5: the SOA in a negative answer carries min(TTL, MINIMUM)
        soa_rdata = enc_name("ns." + ZONE) + enc_name("hostmaster." + ZONE) + struct.pack(">IIIII", 1, 3600, 600, 86400, soa_min)
        soa = enc_name(ZONE) + struct.pack(">HHIH", 6, 1, soa_ttl, len(soa_rdata)) + soa_rdata
        rd = flags & 0x0100
        if rec is None:
            hdr = struct.pack(">HHHHHH", qid, 0x8400 | rd | 3, 1, 0, 1, 0)
            return hdr + question + soa
        if qtype in (1, 28):
            v6 = qtype == 28
            addrs = [a for a in rec["addrs"] if (":" in a) == v6]
            if addrs:
                ans = b"".join(b"\xc0\x0c" + struct.pack(">HHIH", qtype, 1, rec["ttl"], 16 if v6 else 4) +
                               (socket.inet_pton(socket.AF_INET6, a) if v6 else socket.inet_aton(a)) for a in addrs)
                return struct.pack(">HHHHHH", qid, 0x8400 | rd, 1, len(addrs), 0, 0) + question + ans
        return struct.pack(">HHHHHH", qid, 0x8400 | rd, 1, 0, 1, 0) + question + soa
    def dns_loop():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", 53))
        while True:
            data, addr = s.recvfrom(4096)
            try:
                out = handle(data)
            except Exception:
                out = None
            if out:
                s.sendto(out, addr)
    def ctl_loop():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", 5353))
        while True:
            data, addr = s.recvfrom(4096)
            c, rep = json.loads(data), {"ok": True, "t_ms": int(time.time() * 1000)}
            with z.lock:
                cmd = c["cmd"]
                if cmd == "set":
                    z.records[c["name"]] = {"addrs": c["addr"].split(","), "ttl": int(c["ttl"])}
                elif cmd == "down":
                    z.down = True
                elif cmd == "up":
                    z.down = False
                elif cmd == "soa":
                    z.soa_ttl, z.soa_min = int(c["ttl"]), int(c["min"])
                    z.soa_mode = c.get("mode", "capped")
                elif cmd == "unset":
                    z.records.pop(c["name"], None)
                elif cmd == "count":
                    rep["count"] = z.counts.get(c["name"], 0)
                elif cmd == "reset":
                    z.reset()
            s.sendto(json.dumps(rep).encode(), addr)
    threading.Thread(target=ctl_loop, daemon=True).start()
    dns_loop()

def ctl(**c):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    s.sendto(json.dumps(c).encode(), (AUTH_IP, 5353))
    r = json.loads(s.recvfrom(4096)[0])
    s.close()
    return r

# ---------------------------------------------------------------- measurement helpers
def emit(**kw):
    print(json.dumps(kw, sort_keys=True), flush=True)

def uniq(tag):
    return "%s-%06d.%s" % (tag, random.randrange(10**6), ZONE)

def first_addr(r):
    return r["answers"][0]["addr"] if r["answers"] else None

def poll_until(srv, name, want, interval, maxwait, t_ref):
    """Poll the resolver until it returns address `want` (or NOERROR for want=True). Returns seconds since t_ref, or None."""
    while time.monotonic() - t_ref < maxwait:
        r = ask(srv, name)
        ok = (r["rcode"] == 0 and bool(r["answers"])) if want is True else first_addr(r) == want
        if ok:
            return round(time.monotonic() - t_ref, 3), r
        time.sleep(interval)
    return None, None


# ---------------------------------------------------------------- delegation lab (E8): root, parent (TLD) and child servers
def rr(name, rtype, ttl, rdata):
    return enc_name(name) + struct.pack(">HHIH", rtype, 1, ttl, len(rdata)) + rdata

def under(q, zone):
    return q == zone or q.endswith("." + zone)

def serve_deleg(role, *a):
    """root TEST_NS_IP | tld NS_NAME NS_IP NS_TTL | child NS_NAME ANSWER_ADDR OWN_IP NS_TTL. Control (UDP 5353): tld 'deleg', child 'ns'."""
    st = {"lock": threading.Lock()}
    if role == "tld":
        st.update(ns=a[0], ip=a[1], ttl=int(a[2]))
    elif role == "child":
        st.update(ns=a[0], addr=a[1], ip=a[2], ttl=int(a[3]))
    def handle(data):
        qid, flags = struct.unpack(">HH", data[:4])
        qname, off = read_name(data, 12)
        qtype = struct.unpack(">H", data[off:off + 2])[0]
        question = data[12:off + 4]
        rd = flags & 0x0100
        with st["lock"]:
            cur = dict(st)
        if role == "root":
            if qname == "." and qtype == 2:      # priming query
                return struct.pack(">HHHHHH", qid, 0x8400 | rd, 1, 1, 0, 1) + question + rr(".", 2, 3600000, enc_name("a.root-lab.")) + rr("a.root-lab.", 1, 3600000, socket.inet_aton(a[0]))
            if under(qname, "test."):
                return struct.pack(">HHHHHH", qid, 0x8000 | rd, 1, 0, 1, 1) + question + rr("test.", 2, 3600, enc_name("ns.test.")) + rr("ns.test.", 1, 3600, socket.inet_aton(a[0]))
        elif role == "tld":
            if under(qname, "lab.test."):
                return struct.pack(">HHHHHH", qid, 0x8000 | rd, 1, 0, 1, 1) + question + rr("lab.test.", 2, cur["ttl"], enc_name(cur["ns"])) + rr(cur["ns"], 1, cur["ttl"], socket.inet_aton(cur["ip"]))
        elif role == "child" and under(qname, "lab.test."):
            nsrr, glue = rr("lab.test.", 2, cur["ttl"], enc_name(cur["ns"])), rr(cur["ns"], 1, cur["ttl"], socket.inet_aton(cur["ip"]))
            if qtype == 1 and qname == cur["ns"]:
                return struct.pack(">HHHHHH", qid, 0x8400 | rd, 1, 1, 1, 0) + question + glue + nsrr
            if qtype == 1:
                return struct.pack(">HHHHHH", qid, 0x8400 | rd, 1, 1, 1, 1) + question + rr(qname, 1, 1, socket.inet_aton(cur["addr"])) + nsrr + glue
            if qtype == 2 and qname == "lab.test.":
                return struct.pack(">HHHHHH", qid, 0x8400 | rd, 1, 1, 0, 1) + question + nsrr + glue
            soa = rr("lab.test.", 6, 60, enc_name("ns.lab.test.") + enc_name("hostmaster.lab.test.") + struct.pack(">IIIII", 1, 3600, 600, 86400, 60))
            return struct.pack(">HHHHHH", qid, 0x8400 | rd, 1, 0, 1, 0) + question + soa
        return struct.pack(">HHHHHH", qid, 0x8400 | rd | 5, 1, 0, 0, 0) + question
    def ctl_loop():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("0.0.0.0", 5353))
        while True:
            data, addr = s.recvfrom(4096)
            c = json.loads(data)
            with st["lock"]:
                if c["cmd"] == "deleg": st.update(ns=c["ns"], ip=c["ip"], ttl=int(c["ttl"]))
                elif c["cmd"] == "ns": st.update(ns=c["ns"], ip=c["ip"], ttl=int(c["ttl"]))
            s.sendto(json.dumps({"ok": True, "t_ms": int(time.time() * 1000)}).encode(), addr)
    threading.Thread(target=ctl_loop, daemon=True).start()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("0.0.0.0", 53))
    while True:
        data, addr = s.recvfrom(4096)
        try: out = handle(data)
        except Exception: out = None
        if out: s.sendto(out, addr)

def ctl_to(server, **c):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(3)
    s.sendto(json.dumps(c).encode(), (server, 5353))
    r = json.loads(s.recvfrom(4096)[0]); s.close()
    return r

def e8(resolver, parent_ttl, child_ttl, s1, s2, tld, maxwait="60"):
    """Delegation change: parent delegates lab.test to server 1 (NS TTL = parent_ttl), the child zone on server 1 says NS TTL = child_ttl.
    After one warm lookup the parent delegation moves to server 2. Fresh names are polled; which server answers tells which TTL the resolver followed."""
    srv, parent_ttl, child_ttl = RESOLVERS[resolver], int(parent_ttl), int(child_ttl)
    ctl_to(tld, cmd="deleg", ns="ns1.lab.test.", ip=s1, ttl=parent_ttl)
    ctl_to(s1, cmd="ns", ns="ns1.lab.test.", ip=s1, ttl=child_ttl)
    ctl_to(s2, cmd="ns", ns="ns2.lab.test.", ip=s2, ttl=child_ttl)
    t_warm = time.monotonic()
    warm = ask(srv, uniq("w"))
    time.sleep(1.0)
    ctl_to(tld, cmd="deleg", ns="ns2.lab.test.", ip=s2, ttl=parent_ttl)
    t_flip = time.monotonic()
    seen, n = None, 0
    while time.monotonic() - t_flip < float(maxwait):
        r = ask(srv, uniq("p"))
        n += 1
        if first_addr(r) == "192.0.2.2":
            seen = round(time.monotonic() - t_flip, 3); break
        time.sleep(1.0)
    emit(exp="e8", resolver=resolver, parent_ns_ttl=parent_ttl, child_ns_ttl=child_ttl, warm_addr=first_addr(warm), flip_after_warm_s=round(t_flip - t_warm, 2), switch_s=seen, polls=n)

# ---------------------------------------------------------------- experiments
def e1(resolver, config, ttl):
    """Cache lifetime of a positive answer: record changes right after the first lookup; time until the new value shows."""
    srv, ttl = RESOLVERS[resolver], int(ttl)
    name = uniq("e1")
    ctl(cmd="set", name=name, addr="192.0.2.1", ttl=ttl)
    t0 = time.monotonic()
    r1 = ask(srv, name)
    ctl(cmd="set", name=name, addr="192.0.2.2", ttl=ttl)
    series, seen, last_ttl = [], None, None
    next_sample = 1.0
    while time.monotonic() - t0 < ttl + 40:
        el = time.monotonic() - t0
        r = ask(srv, name)
        if el >= next_sample and r["answers"]:
            series.append([round(el, 1), r["answers"][0]["ttl"]])
            next_sample += 1.0
        if first_addr(r) == "192.0.2.2":
            seen = round(time.monotonic() - t0, 3)
            break
        time.sleep(0.2)
    emit(exp="e1", resolver=resolver, config=config, record_ttl=ttl, first_reply_ttl=r1["answers"][0]["ttl"] if r1["answers"] else None,
         ttl_series_sample=series[:3], new_value_seen_s=seen, auth_queries=ctl(cmd="count", name=name)["count"])

def e2(resolver, config, soa_ttl, soa_min, soa_mode="capped"):
    """Negative caching: NXDOMAIN, then the name is created; time until the resolver stops answering NXDOMAIN."""
    srv = RESOLVERS[resolver]
    name = uniq("e2")
    ctl(cmd="soa", ttl=soa_ttl, min=soa_min, mode=soa_mode)
    t0 = time.monotonic()
    r1 = ask(srv, name)
    ctl(cmd="set", name=name, addr="192.0.2.9", ttl=1)
    seen, r = poll_until(srv, name, True, 0.2, int(soa_ttl) + 40, t0)
    emit(exp="e2", resolver=resolver, config=config, soa_mode=soa_mode, soa_ttl=int(soa_ttl), soa_minimum=int(soa_min), first_rcode=r1["rcode"],
         first_reply_soa_ttl=r1["soa_ttl"], nxdomain_cached_s=seen, auth_queries=ctl(cmd="count", name=name)["count"])
    ctl(cmd="soa", ttl=60, min=60, mode="capped")

def e3(resolver, config, window="26"):
    """Authoritative outage after a cached answer with TTL 5: poll once a second, record every reply."""
    srv, window = RESOLVERS[resolver], float(window)
    name = uniq("e3")
    ctl(cmd="set", name=name, addr="192.0.2.3", ttl=5)
    warm = ask(srv, name)
    t0 = time.monotonic()
    ctl(cmd="down")
    polls = []
    while time.monotonic() - t0 < window:
        el = time.monotonic() - t0
        r = ask(srv, name, timeout=6)
        polls.append({"t": round(el, 2), "rcode": r["rcode"], "addr": first_addr(r), "ttl": r["answers"][0]["ttl"] if r["answers"] else None, "rtt_ms": r["rtt_ms"]})
        time.sleep(max(0, 1.0 - (time.monotonic() - t0 - el)))
    ok = [p for p in polls if p["rcode"] == 0 and p["addr"]]
    bad = [p for p in polls if not (p["rcode"] == 0 and p["addr"])]
    ctl(cmd="up")
    time.sleep(1)
    rec = ask(srv, name)
    emit(exp="e3", resolver=resolver, config=config, warm_ttl=warm["answers"][0]["ttl"] if warm["answers"] else None,
         last_success_s=ok[-1]["t"] if ok else None, first_failure_s=bad[0]["t"] if bad else None,
         failure_rcodes=sorted({p["rcode"] for p in bad}), stale_reply_ttls=sorted({p["ttl"] for p in ok if p["t"] > 6}),
         max_failure_rtt_ms=max([p["rtt_ms"] for p in bad], default=0), polls_ok=len(ok), polls_failed=len(bad),
         after_recovery_rcode=rec["rcode"], after_recovery_ttl=rec["answers"][0]["ttl"] if rec["answers"] else None)

def e4(resolver, ttl, phase):
    """Failover cutover: the cache is filled, the operator flips the record `phase` of the way through the TTL; time until clients see the new address."""
    srv, ttl, phase = RESOLVERS[resolver], int(ttl), float(phase)
    name = uniq("e4")
    ctl(cmd="set", name=name, addr="192.0.2.10", ttl=ttl)
    t_fill = time.monotonic()
    ask(srv, name)
    time.sleep(max(0, phase * ttl - (time.monotonic() - t_fill)))
    t_flip = time.monotonic()
    ctl(cmd="set", name=name, addr="192.0.2.20", ttl=ttl)
    seen, _ = poll_until(srv, name, "192.0.2.20", 0.1, ttl + 40, t_flip)
    emit(exp="e4", resolver=resolver, record_ttl=ttl, flip_phase=phase, flip_after_fill_s=round(t_flip - t_fill, 2), cutover_s=seen)

def e5(resolver, mode):
    """Stale-record window after a change, with and without lowering the TTL ahead of time. Old TTL 20, new TTL 2."""
    srv = RESOLVERS[resolver]
    name = uniq("e5")
    ctl(cmd="set", name=name, addr="192.0.2.30", ttl=20)
    ask(srv, name)
    if mode == "lower_late":
        time.sleep(1)
        ctl(cmd="set", name=name, addr="192.0.2.30", ttl=2)
        time.sleep(1)
    elif mode == "lower_ahead":
        ctl(cmd="set", name=name, addr="192.0.2.30", ttl=2)
        time.sleep(21.5)          # outlast the old 20 s entry
        ask(srv, name)            # the cache now holds the 2 s entry
        time.sleep(0.5)
    elif mode == "baseline":
        time.sleep(1)
    t_change = time.monotonic()
    ctl(cmd="set", name=name, addr="192.0.2.31", ttl=2 if mode != "baseline" else 20)
    seen, _ = poll_until(srv, name, "192.0.2.31", 0.1, 60, t_change)
    emit(exp="e5", resolver=resolver, mode=mode, stale_window_s=seen)

def wait(resolver, secs="30"):
    """Block until the resolver answers anything (NXDOMAIN counts)."""
    end = time.monotonic() + float(secs)
    while time.monotonic() < end:
        if ask(RESOLVERS[resolver], uniq("ready"), timeout=2)["rcode"] != -1:
            return
        time.sleep(0.3)
    sys.exit("resolver %s did not come up" % resolver)

if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "auth":
        serve_auth()
    elif cmd == "dauth":
        serve_deleg(*args)
    elif cmd == "ctlto":
        print(json.dumps(ctl_to(args[0], **dict(a.split("=", 1) for a in args[1:]))))
    elif cmd == "ctl":
        print(json.dumps(ctl(**dict(a.split("=", 1) for a in args))))
    else:
        globals()[cmd](*args)
