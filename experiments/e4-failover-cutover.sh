#!/usr/bin/env bash
# E4: failover cutover time as a function of TTL. The cache is filled, the record is flipped to the standby
# at 10, 50 and 90 percent of the TTL, and clients poll every 0.1 s. Expect cutover close to TTL * (1 - phase).
source "$(dirname "$0")/common.sh"
lab_up
for r in unbound bind; do
  set_resolver $r default
  lab e4 $r 0 0.0
  for t in 3 6 12; do for p in 0.1 0.5 0.9; do lab e4 $r $t $p; done; done
done
