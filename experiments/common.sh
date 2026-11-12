#!/usr/bin/env bash
# Shared setup. Source it, do not execute it. Everything runs in containers on one private,
# internal-only docker network (no published ports, no route out). Scratch files live under $SCR.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCR="${EXP_SCRATCH:?set EXP_SCRATCH to an empty scratch directory}"
mkdir -p "$SCR"
export EXP_LOG="${EXP_LOG:-$SCR/records.jsonl}"
PY="$(command -v python3)"
# Pinned by digest. The image tags are python:3.12-alpine, mvance/unbound:1.22.0, internetsystemsconsortium/bind9:9.20.
IMG_PY="${IMG_PY:-python@sha256:e064671ca452259bab50e8e2c7bd896e39e9a343bb06ca25234adf6fe18d0fc7}"
IMG_UNBOUND="${IMG_UNBOUND:-mvance/unbound@sha256:76906da36d1806f3387338f15dcf8b357c51ce6897fb6450d6ce010460927e90}"
IMG_BIND="${IMG_BIND:-internetsystemsconsortium/bind9@sha256:66092edb53c081fa11b1fa8219e99065b0f497cb38f568ba789702a4c10e2590}"
# Client runtime images (E6, E7), also pinned by digest: golang:1.23-bookworm (Go, curl 7.88, python3), python:3.12-slim-bookworm, eclipse-temurin:21-jdk.
IMG_GO="${IMG_GO:-golang@sha256:167053a2bb901972bf2c1611f8f52c44d5fe7e762e5cab213708d82c421614db}"
IMG_PYGLIBC="${IMG_PYGLIBC:-python@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df}"
IMG_JAVA="${IMG_JAVA:-eclipse-temurin@sha256:ebfbb18d11ff163ee83b21258acf12248af48d22a0fdfdc68fa1a1516c05976a}"
RUN="dnslab$$"
NET="$RUN-net"; SUBNET="${LAB_SUBNET:-172.29.77.0/24}"
A_IP=172.29.77.10; U_IP=172.29.77.11; B_IP=172.29.77.12; P_IP=172.29.77.13
SUBNET6="${LAB_SUBNET6:-2001:db8:77:1::/64}"; P6="${SUBNET6%::/64}::"
BE1_IP=172.29.77.21; BE2_IP=172.29.77.22; REF_IP=172.29.77.23; HOLE_IP=172.29.77.24
C_BE1="$RUN-be1"; C_BE2="$RUN-be2"; C_REF="$RUN-refuse"; C_HOLE="$RUN-hole"; C_GO="$RUN-go"; C_PYC="$RUN-pyc"; C_JAVA="$RUN-java"
export BE1_IP BE2_IP REF_IP HOLE_IP P6 C_PYC C_GO C_JAVA C_PROBE
ROOT_IP=172.29.77.31; TLD_IP=172.29.77.32; S1_IP=172.29.77.33; S2_IP=172.29.77.34
C_ROOT="$RUN-root"; C_TLD="$RUN-tld"; C_S1="$RUN-s1"; C_S2="$RUN-s2"
C_AUTH="$RUN-auth"; C_UNBOUND="$RUN-unbound"; C_BIND="$RUN-bind"; C_PROBE="$RUN-probe"
export AUTH_IP=$A_IP UNBOUND_IP=$U_IP BIND_IP=$B_IP

lab_down() { docker rm -f "$C_AUTH" "$C_UNBOUND" "$C_BIND" "$C_PROBE" "$C_BE1" "$C_BE2" "$C_REF" "$C_HOLE" "$C_GO" "$C_PYC" "$C_JAVA" "$C_ROOT" "$C_TLD" "$C_S1" "$C_S2" >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; true; }

lab_up() {
  trap lab_down EXIT
  docker network create --internal --ipv6 --subnet "$SUBNET" --subnet "$SUBNET6" "$NET" >/dev/null || { echo "cannot create lab network (subnet clash? set LAB_SUBNET and edit the IPs)" >&2; exit 1; }
  docker create --name "$C_AUTH" --network "$NET" --ip $A_IP "$IMG_PY" python -u /dnslab.py auth >/dev/null
  docker create --name "$C_PROBE" --network "$NET" --ip $P_IP -e AUTH_IP -e UNBOUND_IP -e BIND_IP "$IMG_PY" sleep 86400 >/dev/null
  docker create --name "$C_UNBOUND" --network "$NET" --ip $U_IP --entrypoint /opt/unbound/sbin/unbound "$IMG_UNBOUND" -d -c /tmp/unbound.conf >/dev/null
  docker create --name "$C_BIND" --network "$NET" --ip $B_IP --entrypoint /usr/sbin/named "$IMG_BIND" -g -c /tmp/named.conf >/dev/null
  for c in "$C_AUTH" "$C_PROBE"; do docker cp "$HERE/dnslab.py" "$c:/dnslab.py" >/dev/null; done
  docker start "$C_AUTH" "$C_PROBE" >/dev/null
}

# lab CMD ARGS...: run a lab routine in the probe container; JSON records go to stdout and the log.
lab() { docker exec "$C_PROBE" python -I -u /dnslab.py "$@" | tee -a "$EXP_LOG"; }
labq() { docker exec "$C_PROBE" python -I -u /dnslab.py "$@" >/dev/null; }

# Extra resolver settings per named config. Same intent in both resolvers.
unbound_extra() { case "$1" in
  default) ;;
  min15) echo "  cache-min-ttl: 15";;
  max8) echo "  cache-max-ttl: 8";;
  maxneg3) echo "  cache-max-negative-ttl: 3";;
  stale) printf '  serve-expired: yes\n  serve-expired-ttl: 15\n';;
  fixed) echo "  rrset-roundrobin: no";;
  *) echo "unknown config $1" >&2; return 1;; esac; }
bind_extra() { case "$1" in
  default) ;;
  min15) echo "  min-cache-ttl 15;";;
  max8) echo "  max-cache-ttl 8;";;
  maxneg3) echo "  max-ncache-ttl 3;";;
  stale) printf '  stale-answer-enable yes;\n  stale-cache-enable yes;\n  max-stale-ttl 15;\n';;
  *) echo "unknown config $1" >&2; return 1;; esac; }

# set_resolver RESOLVER CONFIG: write the config, restart the container (empty cache), wait until it answers.
set_resolver() {
  local r=$1 cfg=$2 f="$SCR/$1.conf"
  if [ "$r" = unbound ]; then
    { printf 'server:\n  interface: 0.0.0.0\n  access-control: 0.0.0.0/0 allow\n  username: ""\n  chroot: ""\n  directory: "/tmp"\n  pidfile: ""\n  use-syslog: no\n  verbosity: 0\n  do-ip6: no\n  qname-minimisation: no\n  prefetch: no\n  module-config: "iterator"\n  domain-insecure: "lab.test."\n  local-zone: "test." transparent\n'
      unbound_extra "$cfg"
      printf 'stub-zone:\n  name: "lab.test."\n  stub-addr: %s\n' "$A_IP"; } > "$f"
    docker cp "$f" "$C_UNBOUND:/tmp/unbound.conf" >/dev/null
    docker restart "$C_UNBOUND" >/dev/null
  else
    { printf 'options {\n  directory "/tmp";\n  listen-on { any; };\n  listen-on-v6 { none; };\n  allow-query { any; };\n  recursion yes;\n  allow-recursion { any; };\n  dnssec-validation no;\n  qname-minimization disabled;\n  prefetch 0;\n'
      bind_extra "$cfg"
      printf '};\nzone "lab.test" { type static-stub; server-addresses { %s; }; };\n' "$A_IP"; } > "$f"
    docker cp "$f" "$C_BIND:/tmp/named.conf" >/dev/null
    docker restart "$C_BIND" >/dev/null
  fi
  labq wait "$r" 40 || { echo "resolver $r failed to start with config $cfg" >&2; docker logs "$C_UNBOUND" 2>&1 | tail -5 >&2; docker logs "$C_BIND" 2>&1 | tail -5 >&2; exit 1; }
}

# clients_up: backends (answer with their label, one refuses, one drops SYNs) and one container per client runtime.
# Each client container resolves through the lab unbound only (resolv.conf rewritten at start).
clients_up() {
  local C
  for spec in "$C_BE1:$BE1_IP:21:ok old" "$C_BE2:$BE2_IP:22:ok new" "$C_HOLE:$HOLE_IP:24:blackhole"; do
    IFS=: read -r C ip n args <<<"$spec"
    docker create --name "$C" --network "$NET" --ip "$ip" --ip6 "${P6}$n" "$IMG_PY" python -u /backend.py $args >/dev/null
    docker cp "$HERE/clients/backend.py" "$C:/backend.py" >/dev/null; docker start "$C" >/dev/null
  done
  docker run -d --name "$C_REF" --network "$NET" --ip "$REF_IP" --ip6 "${P6}23" "$IMG_PY" sleep 86400 >/dev/null
  local rc="echo nameserver $U_IP > /etc/resolv.conf; exec sleep 86400"
  docker run -d --name "$C_GO" --network "$NET" --entrypoint sh "$IMG_GO" -c "$rc" >/dev/null
  docker run -d --name "$C_PYC" --network "$NET" --entrypoint sh "$IMG_PYGLIBC" -c "$rc" >/dev/null
  docker run -d --name "$C_JAVA" --network "$NET" --entrypoint sh "$IMG_JAVA" -c "$rc" >/dev/null
  docker cp "$HERE/clients/client.go" "$C_GO:/tmp/client.go" >/dev/null
  docker cp "$HERE/clients/client_curl.py" "$C_GO:/tmp/client_curl.py" >/dev/null
  docker cp "$HERE/clients/client.py" "$C_PYC:/tmp/client.py" >/dev/null
  docker cp "$HERE/clients/Client.java" "$C_JAVA:/tmp/Client.java" >/dev/null
  docker exec -e CGO_ENABLED=1 -e GOCACHE=/tmp/gocache -e GOFLAGS=-mod=mod -w /tmp "$C_GO" sh -c 'go mod init lab >/dev/null 2>&1; go build -o /tmp/client-go client.go' || { echo "go build failed" >&2; exit 1; }
  docker exec -w /tmp "$C_JAVA" javac Client.java || { echo "javac failed" >&2; exit 1; }
}

# deleg_up: root, parent (TLD) and two child servers for E8. Resolvers are then started from root hints (set_resolver_root).
deleg_up() {
  local spec C ip args
  for spec in "$C_ROOT:$ROOT_IP:root $TLD_IP" "$C_TLD:$TLD_IP:tld ns1.lab.test. $S1_IP 6" "$C_S1:$S1_IP:child ns1.lab.test. 192.0.2.1 $S1_IP 6" "$C_S2:$S2_IP:child ns2.lab.test. 192.0.2.2 $S2_IP 6"; do
    IFS=: read -r C ip args <<<"$spec"
    docker create --name "$C" --network "$NET" --ip "$ip" "$IMG_PY" python -u /dnslab.py dauth $args >/dev/null
    docker cp "$HERE/dnslab.py" "$C:/dnslab.py" >/dev/null; docker start "$C" >/dev/null
  done
}

# set_resolver_root RESOLVER: iterate from a root hint that points at the lab root, no stub zones. Fresh cache.
set_resolver_root() {
  local r=$1 f="$SCR/$1-root.conf"
  printf '. 3600000 NS a.root-lab.\na.root-lab. 3600000 A %s\n' "$ROOT_IP" > "$SCR/root.hints"
  if [ "$r" = unbound ]; then
    printf 'server:\n  interface: 0.0.0.0\n  access-control: 0.0.0.0/0 allow\n  username: ""\n  chroot: ""\n  directory: "/tmp"\n  pidfile: ""\n  use-syslog: no\n  verbosity: 0\n  do-ip6: no\n  qname-minimisation: no\n  prefetch: no\n  module-config: "iterator"\n  root-hints: "/tmp/root.hints"\n  local-zone: "test." transparent\n' > "$f"
    docker cp "$f" "$C_UNBOUND:/tmp/unbound.conf" >/dev/null; docker cp "$SCR/root.hints" "$C_UNBOUND:/tmp/root.hints" >/dev/null
    docker restart "$C_UNBOUND" >/dev/null
  else
    printf 'options {\n  directory "/tmp";\n  listen-on { any; };\n  listen-on-v6 { none; };\n  allow-query { any; };\n  recursion yes;\n  allow-recursion { any; };\n  dnssec-validation no;\n  qname-minimization disabled;\n  prefetch 0;\n};\nzone "." { type hint; file "/tmp/root.hints"; };\n' > "$f"
    docker cp "$f" "$C_BIND:/tmp/named.conf" >/dev/null; docker cp "$SCR/root.hints" "$C_BIND:/tmp/root.hints" >/dev/null
    docker restart "$C_BIND" >/dev/null
  fi
  labq wait "$r" 40 || { echo "resolver $r failed to start from root hints" >&2; exit 1; }
}
