#!/usr/bin/env bash
# E8 method A: delegation change. Three tiers (root, parent, child) in containers; the resolver starts from root hints.
# The parent delegation moves from server 1 to server 2 one second after a warm lookup; fresh names are polled
# until server 2 answers. Case 1: parent NS TTL 6 s, child NS TTL 30 s. Case 2: the reverse.
source "$(dirname "$0")/common.sh"
lab_up; deleg_up
for r in unbound bind; do
  for pc in "6 30" "30 6"; do
    set -- $pc
    # reset all three tiers to the starting state before the resolver starts, its readiness probe already walks the delegation
    labq ctlto $TLD_IP cmd=deleg ns=ns1.lab.test. ip=$S1_IP ttl=$1
    labq ctlto $S1_IP cmd=ns ns=ns1.lab.test. ip=$S1_IP ttl=$2
    labq ctlto $S2_IP cmd=ns ns=ns2.lab.test. ip=$S2_IP ttl=$2
    set_resolver_root $r
    lab e8 $r $1 $2 $S1_IP $S2_IP $TLD_IP 70
  done
done
