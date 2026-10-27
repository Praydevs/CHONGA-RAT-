#!/usr/bin/env python3
"""Check that the panel answers on this machine's LAN address.

Run it on the panel host after starting with LAN mode:

    python tools/lan-probe.py
    python tools/lan-probe.py --port 8787

It reports the URLs a second PC should use, then requests /api/config with the
LAN IP as the Host header. A 200 means the bind, the Host allow-list and the
route are all correct; a 403 means the Host guard rejected the address.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import urllib.error
import urllib.request


def local_ips() -> list[str]:
    found: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in found:
                found.append(ip)
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            ip = probe.getsockname()[0]
        finally:
            probe.close()
        if ip not in found:
            found.append(ip)
    except OSError:
        pass
    return [ip for ip in found if not ip.startswith("127.")]


def probe(ip: str, port: int, timeout: float) -> tuple[bool, str]:
    url = f"http://{ip}:{port}/api/config"
    req = urllib.request.Request(url, headers={"Host": f"{ip}:{port}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cfg = json.loads(r.read())
            return True, json.dumps({k: cfg.get(k) for k in
                                     ("httpPort", "agentPort", "bind", "agentBind",
                                      "lanIp", "lan")})
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} {e.read()[:200].decode('utf-8', 'replace')}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--agent-port", type=int, default=8790)
    ap.add_argument("--timeout", type=float, default=5.0)
    args = ap.parse_args()

    ips = local_ips()
    if not ips:
        print("no non-loopback IPv4 address found — this machine is offline")
        return 1

    print("panel host addresses:")
    for ip in ips:
        print(f"  http://{ip}:{args.port}/   agents dial {ip}:{args.agent_port}")
    print()

    ok_any = False
    for ip in ips:
        ok, detail = probe(ip, args.port, args.timeout)
        print(f"{'PASS' if ok else 'FAIL'}  {ip}  {detail}")
        ok_any = ok_any or ok
    if not ok_any:
        print()
        print("The panel is not answering on the LAN address.")
        print("Start it with:  start-panel.bat lan")
        print("or set PANEL_BIND=0.0.0.0 and AGENT_BIND=0.0.0.0 before launching.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
