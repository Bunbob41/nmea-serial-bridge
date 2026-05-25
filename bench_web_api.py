#!/usr/bin/env python3
"""Bench: Web API start/stop loop (requires bridge GUI running with Web enabled)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8765"


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=5) as resp:
        return json.loads(resp.read().decode())


def _post(path: str) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=b"",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    try:
        health = _get("/health")
    except urllib.error.URLError as exc:
        print(f"[bench_web_api] Cannot reach {BASE}: {exc}")
        print("Enable Web API in Tools → Phone and restart the app.")
        return 1
    print(f"[bench_web_api] health: {health}")
    ok = 0
    for i in range(10):
        st = _post("/bridge/start")
        if not st.get("ok"):
            print(f"  cycle {i + 1} start failed: {st}")
            continue
        status = _get("/status")
        _post("/bridge/stop")
        if status.get("running") or st.get("ok"):
            ok += 1
    print(f"[bench_web_api] completed {ok}/10 cycles")
    return 0 if ok >= 8 else 1


if __name__ == "__main__":
    sys.exit(main())
