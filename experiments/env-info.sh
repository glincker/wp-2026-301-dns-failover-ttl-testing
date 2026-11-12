#!/usr/bin/env bash
# Record tool versions and the platform class. No hostnames, paths or dates.
source "$(dirname "$0")/common.sh"
true
j() { "$PY" -I -c 'import json,sys;print(json.dumps(sys.stdin.read().strip()))'; }
ub=$(docker run --rm --entrypoint /opt/unbound/sbin/unbound "$IMG_UNBOUND" -V 2>/dev/null | head -1)
bd=$(docker run --rm --entrypoint /usr/sbin/named "$IMG_BIND" -V 2>/dev/null | head -1)
py=$(docker run --rm "$IMG_PY" python -V)
gov=$(docker run --rm "$IMG_GO" go version | sed "s/ linux.*//"); cv=$(docker run --rm "$IMG_GO" curl -V | head -1 | cut -d" " -f1-2); jv=$(docker run --rm "$IMG_JAVA" java -version 2>&1 | head -1); gl=$(docker run --rm "$IMG_PYGLIBC" sh -c "ldd --version | head -1")
echo "{\"exp\":\"env\",\"go\":$(echo "$gov" | j),\"curl\":$(echo "$cv" | j),\"java\":$(echo "$jv" | j),\"glibc_python_image\":$(echo "$gl" | j),\"unbound\":$(echo "$ub" | j),\"bind\":$(echo "$bd" | j),\"python\":$(echo "$py" | j),\"docker_server\":$(docker version --format '{{.Server.Version}}' | j),\"host_arch\":$(uname -m | j),\"image_arch\":\"linux/amd64 (emulated on arm64 hosts)\",\"cores\":$(docker info --format '{{.NCPU}}')}" | tee -a "$EXP_LOG"
