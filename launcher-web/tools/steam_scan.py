#!/usr/bin/env python3
"""Writes library.js (file:// URLs) for opening index.html straight from disk, without the backend.

usage: python3 tools/steam_scan.py [--steam PATH] [--out library.js]
The backend (backend/server.py) does not need this: it reads Steam itself and serves the art.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import steam  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steam")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "library.js"))
    a = ap.parse_args()
    root = steam.find_steam(a.steam)
    if not root:
        sys.exit("Steam folder not found (use --steam PATH)")
    games = []
    for g in steam.scan(root):
        out = {k: v for k, v in g.items() if k != "files"}
        for kind in ("cover", "hero", "logo", "blur"):
            out[kind] = g["files"][kind].as_uri() if kind in g["files"] else ""
        games.append(out)
    Path(a.out).write_text("window.LIBRARY = " + json.dumps({"generated": int(time.time()), "games": games}, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print("%d games -> %s" % (len(games), a.out))


main()
