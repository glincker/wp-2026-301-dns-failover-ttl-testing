#!/usr/bin/env bash
# E2: negative caching. NXDOMAIN is cached for min(SOA TTL, SOA MINIMUM) unless the resolver caps it lower.
# The name is created right after the first NXDOMAIN; time until the resolver stops saying NXDOMAIN.
# Two authoritative modes: capped (RFC 2308 section 5, the SOA in the authority section carries min(TTL, MINIMUM))
# and uncapped (the SOA keeps its own TTL, which is what a non compliant server would send).
source "$(dirname "$0")/common.sh"
lab_up
for r in unbound bind; do
  set_resolver $r default
  lab e2 $r default 8 8 capped
  lab e2 $r default 30 6 capped      # SOA TTL above MINIMUM: the smaller one should win
  lab e2 $r default 30 6 uncapped    # same zone data, but the wire SOA TTL stays 30
  lab e2 $r default 60 6 uncapped
  set_resolver $r maxneg3
  lab e2 $r maxneg3 20 20 capped     # resolver cap of 3 s
done
