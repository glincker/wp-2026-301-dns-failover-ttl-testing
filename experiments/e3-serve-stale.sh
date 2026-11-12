#!/usr/bin/env bash
# E3: authoritative outage after a cached answer with TTL 5. Default resolvers versus serve-stale enabled
# (stale window of 15 s). The authoritative drops every query (silent outage) for the whole 26 s window.
source "$(dirname "$0")/common.sh"
lab_up
for r in unbound bind; do
  for c in default stale; do set_resolver $r $c; lab e3 $r $c 26; done
done
