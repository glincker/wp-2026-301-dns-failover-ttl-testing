#!/usr/bin/env bash
# E1: is the TTL honored, or clamped by the resolver? Positive answer cached, record changes right after,
# time until the new value is visible = effective cache lifetime. Two resolvers, three configs.
source "$(dirname "$0")/common.sh"
lab_up
for r in unbound bind; do
  set_resolver $r default; for t in 5 20; do lab e1 $r default $t; done
  set_resolver $r min15;   lab e1 $r min15 5       # floor of 15 s on a 5 s record
  set_resolver $r max8;    lab e1 $r max8 20       # ceiling of 8 s on a 20 s record
done
