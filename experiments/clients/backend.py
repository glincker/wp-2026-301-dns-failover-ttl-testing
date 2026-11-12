#!/usr/bin/env python3
"""Tiny backends on port 8080 (dual stack). Usage: backend.py ok BODY | blackhole
ok: answers 200 with BODY and closes the connection. blackhole: accept queue is full, so new SYNs are dropped and clients see a timeout."""
import socket, sys, threading
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
s.bind(("::", 8080))
if sys.argv[1] == "blackhole":
    s.listen(0)
    held = []
    for _ in range(4):                                  # fill the queue, never accept
        try: held.append(socket.create_connection(("127.0.0.1", 8080), timeout=1))
        except OSError: pass
    threading.Event().wait()
s.listen(64)
body = sys.argv[2].encode()
while True:
    c, _ = s.accept()
    try:
        c.settimeout(2); c.recv(4096)
        c.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % (len(body) + 1) + body + b"\n")
    except OSError: pass
    c.close()
