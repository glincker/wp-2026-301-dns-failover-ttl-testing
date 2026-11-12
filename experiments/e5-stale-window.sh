#!/usr/bin/env bash
# E5: stale-record window after a change. Old TTL 20, new TTL 2. Lowering the TTL only helps when it is done
# before the old TTL has had time to expire in caches: baseline, lowered 1 s before the change, lowered 21.5 s before.
source "$(dirname "$0")/common.sh"
lab_up
for r in unbound bind; do
  set_resolver $r default
  for m in baseline lower_late lower_ahead; do lab e5 $r $m; done
done
