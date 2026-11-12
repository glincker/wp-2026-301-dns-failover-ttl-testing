#!/usr/bin/env bash
# E6: how long a client runtime keeps using the old address after the record changed. Record TTL 2 s, the change comes
# 3.5 s after the first lookup (so the resolver's own entry has expired), requests every 0.5 s on a new connection.
source "$(dirname "$0")/common.sh"
lab_up; clients_up
set_resolver unbound fixed
c() { "$PY" -I "$HERE/clients.py" e6 "$@" | tee -a "$EXP_LOG"; }
c python fresh 15 none
c go-pure fresh 15 none
c go-cgo fresh 15 none
c curl fresh 15 none
c curl long 75 60
c java default 45 30
c java ttl0 15 none
c java ttl5 20 5
c java ttlinf 45 forever
