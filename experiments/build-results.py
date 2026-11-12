#!/usr/bin/env python3
"""Build results.json and results.md from the raw records. Every number comes from the log; nothing is typed in.
Expected values are computed from the configuration of each case. Tolerances are stated in the output.
Env: EXP_LOG (raw records), PREV_RESULTS (optional earlier results.json to compare against)."""
import json, os, re, socket, getpass, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ["EXP_LOG"]
PREV = os.environ.get("PREV_RESULTS")
recs = []
for line in open(LOG):
    line = line.strip()
    if line.startswith("{"):
        recs.append(json.loads(line))
by = lambda e: [r for r in recs if r["exp"] == e]
env = (by("env") or [{}])[0]

def verdict(delta, lo, hi):
    return delta is not None and lo <= delta <= hi

E = {}
# a missing record means a case crashed; refuse to build partial results
WANT = {"e1": 8, "e2": 10, "e3": 4, "e4": 20, "e5": 6, "e6": 9, "e7": 30, "e8": 4}
for k, n in WANT.items():
    if len(by(k)) != n: sys.exit("expected %d %s records, found %d: a case failed, refusing to build results" % (n, k, len(by(k))))
# ---- E1
c = []
for r in by("e1"):
    exp = {"default": r["record_ttl"], "min15": max(r["record_ttl"], 15), "max8": min(r["record_ttl"], 8)}[r["config"]]
    m = r["new_value_seen_s"]; d = None if m is None else round(m - exp, 2)
    c.append({"resolver": r["resolver"], "config": r["config"], "record_ttl_s": r["record_ttl"], "first_reply_ttl_s": r["first_reply_ttl"],
              "expected_cache_s": exp, "measured_cache_s": m, "delta_s": d, "pass": verdict(d, -1.2, 1.5), "auth_queries": r["auth_queries"],
              "behaviour": "clamped up" if exp > r["record_ttl"] else "clamped down" if exp < r["record_ttl"] else "honored"})
E["e1"] = {"title": "TTL honored or clamped by the resolver", "tolerance": "measured minus expected within -1.2 s to +1.5 s (poll step 0.2 s, TTL counted in whole seconds so a cache may drop an entry up to one second early, emulated CPU)", "cases": c}
# ---- E2
c = []
for r in by("e2"):
    exp = min(r["soa_ttl"], r["soa_minimum"])
    if r["config"] == "maxneg3": exp = min(exp, 3)
    m = r["nxdomain_cached_s"]; d = None if m is None else round(m - exp, 2)
    ok = verdict(d, -1.2, 1.5)
    # "follows" says which input the resolver's measured value tracks: the MINIMUM field, the SOA record TTL on the wire, or neither.
    tr = lambda v: m is not None and abs(m - v) <= 2.5
    follows = "resolver cap" if r["config"] == "maxneg3" else "min(TTL, MINIMUM)" if tr(exp) else "wire SOA TTL" if tr(r["soa_ttl"]) else "other"
    c.append({"resolver": r["resolver"], "config": r["config"], "auth_soa_mode": r["soa_mode"], "soa_ttl_s": r["soa_ttl"], "soa_minimum_s": r["soa_minimum"], "ttl_on_first_nxdomain_s": r["first_reply_soa_ttl"],
              "expected_negative_s": exp, "measured_negative_s": m, "delta_s": d, "pass": ok, "follows": follows, "auth_queries": r["auth_queries"]})
E["e2"] = {"title": "Negative caching duration", "tolerance": "measured minus expected within -1.2 s to +1.5 s; expected is min(SOA TTL, SOA MINIMUM), then the resolver cap if configured", "cases": c}
# ---- E3
c = []
for r in by("e3"):
    ls = r["last_success_s"]
    stale = ls is not None and ls > 6.5
    if r["config"] == "default": ok = not stale
    else: ok = ls is not None and 17 <= ls <= 22.5
    c.append({"resolver": r["resolver"], "config": r["config"], "expected": "no stale answers after the 5 s TTL" if r["config"] == "default" else "stale answers until about 20 s (5 s TTL + 15 s stale window)",
              "last_success_s": ls, "first_failure_s": r["first_failure_s"], "served_stale": stale, "stale_reply_ttls_s": r["stale_reply_ttls"],
              "failure_rcodes": r["failure_rcodes"], "max_failure_latency_ms": r["max_failure_rtt_ms"], "polls_ok": r["polls_ok"], "polls_failed": r["polls_failed"],
              "after_recovery_rcode": r["after_recovery_rcode"], "pass": ok})
E["e3"] = {"title": "Serve-stale during an authoritative outage", "tolerance": "default: no success after 6.5 s; serve-stale: last success between 17 s and 22.5 s (client-side wait before a stale answer is up to 1.8 s)", "cases": c}
# ---- E4
c = []
for r in by("e4"):
    exp = round(r["record_ttl"] * (1 - r["flip_phase"]) - (r["flip_after_fill_s"] - r["record_ttl"] * r["flip_phase"]), 2) if r["record_ttl"] else 0.0
    m = r["cutover_s"]; d = None if m is None else round(m - exp, 2)
    c.append({"resolver": r["resolver"], "record_ttl_s": r["record_ttl"], "flip_at_fraction_of_ttl": r["flip_phase"], "flip_after_fill_s": r["flip_after_fill_s"],
              "expected_cutover_s": exp, "measured_cutover_s": m, "delta_s": d, "pass": verdict(d, -1.2, 1.5)})
E["e4"] = {"title": "Failover cutover time as a function of TTL", "tolerance": "measured minus expected within -1.2 s to +1.5 s; expected = TTL minus actual time since the cache fill", "cases": c}
# ---- E5
c = []
for r in by("e5"):
    exp = {"baseline": 19.0, "lower_late": 18.0, "lower_ahead": 1.5}[r["mode"]]
    m = r["stale_window_s"]; d = None if m is None else round(m - exp, 2)
    c.append({"resolver": r["resolver"], "mode": r["mode"], "expected_stale_window_s": exp, "measured_stale_window_s": m, "delta_s": d, "pass": verdict(d, -1.2, 1.5)})
E["e5"] = {"title": "Stale-record window after a change, with TTL lowered late or ahead", "tolerance": "measured minus expected within -1.2 s to +1.5 s; old TTL 20 s, new TTL 2 s", "cases": c}

# ---- E6
c = []
for r in by("e6"):
    L, fa, fn, la = r["runtime_cache_s"], r["flip_after_first_s"], r["first_new_after_flip_s"], r["last_old_after_flip_s"]
    if L == "none":
        # no client cache: the resolver entry (TTL 2 s, refreshed by the polling) can still be up to 2 s old, plus one 0.5 s poll step
        exp, ok = "switch within 3.5 s of the change (resolver TTL 2 s + poll step)", fn is not None and 0 <= fn <= 3.5
    elif L == "forever":
        exp, ok = "never switches during the run", fn is None
    else:
        e = round(L - fa, 2)
        exp, ok = "switch at about %s s (client cache %s s minus %s s already elapsed)" % (e, L, fa), fn is not None and -1.2 <= fn - e <= 1.5
    c.append({"runtime": r["runtime"], "variant": r["variant"], "client_cache_s": L, "change_after_first_lookup_s": fa, "expected": exp,
              "last_request_on_old_address_s": la, "first_request_on_new_address_s": fn, "requests": r["requests"], "errors": r["errors"], "pass": ok})
E["e6"] = {"title": "Client runtimes: how long the old address stays in use after the record changed", "tolerance": "times are seconds after the change; record TTL 2 s, requests every 0.5 s on a new connection each time; cached runtimes within -1.2 s to +1.5 s of cache lifetime minus time already elapsed", "cases": c}
# ---- E7
c = []
HE = ("go-pure", "go-cgo", "curl")
for r in by("e7"):
    cto, el, o = r["connect_timeout_s"], r["elapsed_s"], r["outcome"]
    if r["dead_mode"] == "refused" and r["family"] == "v4":
        exp, ok = "next address within 1.5 s", o == "new" and el is not None and el <= 1.5
    elif r["family"] == "v4" and cto is not None:
        exp, ok = "success within the connect timeout (%s s) plus 1 s" % cto, o == "new" and el is not None and el <= cto + 1
    elif r["family"] == "v4":
        exp, ok = "success within the %s s cap" % r["cap_s"], o == "new"
    elif r["runtime"] in HE:
        exp, ok = "Happy Eyeballs (RFC 8305): live family within 2 s (the largest delay the RFC allows)", o == "new" and el is not None and el <= 2.0
    else:
        exp, ok = "no Happy Eyeballs implementation expected; reported as found", None
    c.append({"runtime": r["runtime"], "family": r["family"], "dead_mode": r["dead_mode"], "connect_timeout_s": cto, "address_order_seen": r["address_order"],
              "expected": exp, "outcome": {"new": "connected to the live address"}.get(o, o), "elapsed_s": el, "attempts": r["attempts"], "pass": ok})
E["e7"] = {"title": "Two addresses, the first dead: client fallback", "tolerance": "v4 rows: the dead address is listed first; v6 rows: the AAAA is dead and the A is alive. Elapsed time includes client process start for curl. Runtimes without Happy Eyeballs have no pass or fail", "cases": c}

# ---- E8
c = []
for r in by("e8"):
    P, C, fl, m = r["parent_ns_ttl"], r["child_ns_ttl"], r["flip_after_warm_s"], r["switch_s"]
    ep, ec = round(P - fl, 2), round(C - fl, 2)
    near = lambda e: m is not None and -1.2 <= m - e <= 1.5
    follows = "child NS TTL" if near(ec) and not near(ep) else "parent NS TTL" if near(ep) and not near(ec) else "either (equal)" if near(ep) and near(ec) else "neither"
    c.append({"resolver": r["resolver"], "parent_ns_ttl_s": P, "child_ns_ttl_s": C, "expected_if_parent_centric_s": ep, "expected_if_child_centric_s": ec,
              "measured_switch_s": m, "follows": follows, "pass": follows != "neither"})
E["e8"] = {"title": "Delegation change: which NS TTL the resolver follows", "tolerance": "switch time measured from the parent change, polling once a second with fresh names; a case passes when the switch matches the parent or the child expectation within -1.2 s to +1.5 s, a row that matches neither is a finding", "cases": c}

allc = [x for e in E.values() for x in e["cases"] if x["pass"] is not None]
out = {"environment": {k: v for k, v in env.items() if k != "exp"}, "experiments": E,
       "summary": {"cases": len(allc), "within_tolerance": sum(1 for x in allc if x["pass"])}}

# ---- comparison with an earlier run
KEYS = ("measured_switch_s", "first_request_on_new_address_s", "elapsed_s", "measured_cache_s", "measured_negative_s", "last_success_s", "measured_cutover_s", "measured_stale_window_s")
IDS = ("parent_ns_ttl_s", "runtime", "variant", "family", "dead_mode", "connect_timeout_s", "resolver", "config", "auth_soa_mode", "record_ttl_s", "soa_ttl_s", "soa_minimum_s", "flip_at_fraction_of_ttl", "mode")
if PREV and os.path.exists(PREV):
    prev = json.load(open(PREV)); rows = []
    for en, e in E.items():
        if en not in prev["experiments"]: continue
        pc = prev["experiments"][en]["cases"]
        for a, b in zip(e["cases"], pc):
            k = next((k for k in KEYS if k in a), None)
            ident = ",".join("%s=%s" % (i, a[i]) for i in IDS if i in a)
            va, vb = a[k], b[k]
            rows.append({"exp": en, "case": ident, "run_1": vb, "run_2": va, "abs_diff": None if va is None or vb is None else round(abs(va - vb), 2),
                         "same_verdict": a["pass"] == b["pass"]})
    diffs = [r["abs_diff"] for r in rows if r["abs_diff"] is not None]
    out["repeat_comparison"] = {"rows": rows, "cases": len(rows), "same_verdict": sum(r["same_verdict"] for r in rows),
                                "max_abs_diff_s": max(diffs) if diffs else None, "median_abs_diff_s": sorted(diffs)[len(diffs) // 2] if diffs else None}

# ---- markdown
def tbl(rows):
    if not rows: return ""
    h = list(rows[0])
    f = lambda v: "yes" if v is True else "no" if v is False else "none" if v is None else ", ".join(map(str, v)) if isinstance(v, list) else str(v)
    return "\n".join(["| " + " | ".join(h) + " |", "|" + "---|" * len(h)] + ["| " + " | ".join(f(r[k]) for k in h) + " |" for r in rows]) + "\n"
md = ["# GLINR-WP-2026-301 experiment results", "",
      "Generated by build-results.py from the raw records of run-all.sh. Nothing here is edited by hand.", "",
      "Environment: " + ", ".join("%s: %s" % (k, v) for k, v in out["environment"].items()), "",
      "Lab: one internal docker network (no route out, no published ports), a scriptable authoritative server, unbound and BIND as caching resolvers delegating to it, and a probe container that does all timing. Image CPU is emulated on arm64 hosts, so allow a few hundred ms of overhead.", "",
      "Summary: %d of %d cases match the stated expectation within tolerance. A failing row is a finding, not a harness error: it means the resolver behaves differently from the expectation written in the tolerance line." % (out["summary"]["within_tolerance"], out["summary"]["cases"]), ""]
for en, e in E.items():
    md += ["## %s. %s" % (en.upper(), e["title"]), "", "Tolerance: " + e["tolerance"], "", tbl(e["cases"])]
if "repeat_comparison" in out:
    rc = out["repeat_comparison"]
    md += ["## Repeat comparison (run 1 against run 2)", "",
           "%d cases, %d with the same verdict, maximum absolute difference %s s, median %s s." % (rc["cases"], rc["same_verdict"], rc["max_abs_diff_s"], rc["median_abs_diff_s"]), "", tbl(rc["rows"])]
md += ["## Not run", "",
       "E8 method B (signed zone, DS TTL cache, validating resolver after a wrong re-sign) was not run: it needs a signed lab zone with key rollover tooling and a validating resolver configuration, which this round did not build. No DS claim is measured here.",
       "curl has no command line option for its DNS cache timeout (only libcurl does), so only the default 60 s was measured. The `networkaddress.cache.negative.ttl` Java setting, the Node.js and nginx runtimes, and requests-style Python libraries were not run.", ""]
arm = open(os.path.join(HERE, "arm-quote.txt")).read().strip()
md += ["## BIND 9.20 reference manual text for the negative cache caps", "", "\n\n".join("> " + l for l in arm.split("\n\n")), ""]
text_md, text_js = "\n".join(md), json.dumps(out, indent=1, sort_keys=True)

# ---- sanitizer: nothing local may leak into the published files
bad = [os.environ.get("EXP_SCRATCH", ""), os.path.expanduser("~"), getpass.getuser(), socket.gethostname().split(".")[0], "/Users", "/private", "/tmp", "/var/folders"]
for b in filter(lambda x: len(x) > 2, bad):
    for t in (text_md, text_js):
        if b in t: sys.exit("sanitizer: local identifier found in output: refusing to write")
if re.search(r"\b\d{4}-\d\d-\d\dT", text_js): sys.exit("sanitizer: timestamp found")
open(os.path.join(HERE, "results.json"), "w").write(text_js + "\n")
open(os.path.join(HERE, "results.md"), "w").write(text_md + "\n")
print("results written: %d/%d within tolerance" % (out["summary"]["within_tolerance"], out["summary"]["cases"]), file=sys.stderr)
