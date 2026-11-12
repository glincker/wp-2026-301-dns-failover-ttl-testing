#!/usr/bin/env bash
# E7: a record set of two addresses, the first one dead, the second alive. Dead modes: connection refused (RST) and
# blackhole (SYNs dropped, a real timeout). Dual stack: AAAA dead, A alive. One request per case; elapsed time to the first byte.
source "$(dirname "$0")/common.sh"
lab_up; clients_up
set_resolver unbound fixed
c() { "$PY" -I "$HERE/clients.py" e7 "$@" | tee -a "$EXP_LOG"; }
for fam in v4 v6; do
  for rt in python go-pure go-cgo curl java; do
    c $rt $fam refused none 20
    c $rt $fam blackhole 3 20       # explicit connect timeout of 3 s
    c $rt $fam blackhole none 20    # the runtime default, observed for 20 s at most
  done
done
