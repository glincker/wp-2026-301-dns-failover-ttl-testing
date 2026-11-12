#!/usr/bin/env bash
# Usage: EXP_SCRATCH=/path/to/empty/dir ./run-all.sh   (needs docker, python3; images are pulled once by digest)
# Runs every experiment in order, never in parallel, then builds results.json and results.md. Takes about 40 minutes.
source "$(dirname "$0")/common.sh"
[ -z "$(ls -A "$SCR" 2>/dev/null)" ] || { echo "refusing to run: $SCR is not empty" >&2; exit 1; }
for i in "$IMG_PY" "$IMG_UNBOUND" "$IMG_BIND" "$IMG_GO" "$IMG_PYGLIBC" "$IMG_JAVA"; do docker image inspect "$i" >/dev/null 2>&1 || docker pull -q "$i" >/dev/null; done
"$HERE/env-info.sh"
for s in e1-ttl-clamp e2-negative-cache e3-serve-stale e4-failover-cutover e5-stale-window e6-client-cache e7-multi-address e8-delegation; do
  echo "== $s" >&2
  "$HERE/$s.sh" 2>&1 | grep -v 'platform (linux/amd64)' >&2
done
"$PY" -I "$HERE/build-results.py"
[ -n "${KEEP_SCRATCH:-}" ] || rm -rf "$SCR"
echo done >&2
