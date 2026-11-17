#!/usr/bin/env python3
"""Darksham Launcher backend: serves the UI, the game library, the store (Steam public data) and a launch endpoint on localhost.

  python3 backend/server.py [--port 8765] [--open]

Security: it listens on 127.0.0.1 only, rejects other Host headers (DNS rebinding), and launching needs a
random per-run token that only the page served by this server receives, plus a game id that is in the
scanned library. Nothing else can be executed.
"""
import argparse
import json
import mimetypes
import re
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import heroic  # noqa: E402
import lutris  # noqa: E402
import settings  # noqa: E402
import steam  # noqa: E402
import store  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOKEN = secrets.token_urlsafe(24)
VERSION = "0.1"
STATIC_DIRS = {"css", "js", "fonts", "assets"}
ID_RE = re.compile(r"^(?:(steam|lutris):(\d{1,12})|heroic:(legendary|gog|nile):([A-Za-z0-9_.\-]{1,64}))$")
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("text/javascript", ".js")

_lock = threading.Lock()
_games = []


def library():
    global _games
    with _lock:
        on = settings.load()["sources"]
        found = (steam.scan() if on["steam"] else []) + (lutris.scan() if on["lutris"] else []) + (heroic.scan() if on["heroic"] else [])
        for g in found:  # one key per game for art URLs: steam-730, lutris-5, heroic-legendary-<app>
            g.setdefault("key", "%s-%s" % (g["source"], g["appid"]))
        _games = sorted(found, key=lambda g: -g["last_played"])
        return _games


def settings_payload():
    s = settings.load()
    found = {"steam": len(steam.scan()), "lutris": len(lutris.scan()), "heroic": len(heroic.scan())}
    return {"region": s["region"], "regions": settings.REGIONS, "version": VERSION, "remote_art": s["remote_art"],
            "sources": {n: {"enabled": s["sources"][n], "found": found[n]} for n in settings.SOURCES}}


def public(g):
    out = {k: v for k, v in g.items() if k not in ("files", "remote")}
    kinds = set(g["files"]) | (set(g.get("remote", {})) if settings.load()["remote_art"] else set())
    for kind in kinds:
        out[kind] = "/art/%s/%s" % (g["key"], kind)
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "DarkshamLauncher"

    def log_message(self, fmt, *args):
        sys.stderr.write("[launcher] " + fmt % args + "\n")

    # -- helpers
    def _host_ok(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        return host in ("127.0.0.1", "localhost")

    def _send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, cache="no-cache"):
        try:
            data = path.read_bytes()
        except OSError:
            return self._send(404, {"error": "not found"})
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self._send(200, data, ctype, {"Cache-Control": cache})

    # -- routes
    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "bad host"})
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            html = (ROOT / "index.html").read_text(encoding="utf-8")
            html = html.replace("<!--DARKSHAM_TOKEN-->", '<script>window.DARKSHAM={token:"%s"};</script>' % TOKEN)
            return self._send(200, html, "text/html; charset=utf-8", {"Cache-Control": "no-store"})
        if path == "/api/settings":
            return self._send(200, settings_payload(), extra={"Cache-Control": "no-store"})
        if path == "/api/library":
            return self._send(200, {"games": [public(g) for g in library()]}, extra={"Cache-Control": "no-store"})
        q = parse_qs(urlparse(self.path).query)
        lang = (q.get("lang") or ["en"])[0]
        if path == "/api/store/home":
            try:
                return self._send(200, store.home(lang), extra={"Cache-Control": "no-store"})
            except Exception as e:  # network down and nothing cached
                return self._send(502, {"error": "store unavailable", "detail": type(e).__name__})
        m = re.fullmatch(r"/api/store/app/(\d{1,12})", path)
        if m:
            try:
                d = store.app(int(m.group(1)), lang)
            except Exception as e:
                return self._send(502, {"error": "store unavailable", "detail": type(e).__name__})
            return self._send(200, d, extra={"Cache-Control": "no-store"}) if d else self._send(404, {"error": "no such app"})
        m = re.fullmatch(r"/store-art/(\d{1,12})/(cover|hero|logo|header)", path)
        if m:
            got = store.art(int(m.group(1)), m.group(2))
            return self._send(200, got[0], got[1], {"Cache-Control": "max-age=86400"}) if got else self._send(404, {"error": "no art"})
        if path == "/store-img":
            got = store.image((q.get("u") or [""])[0])
            return self._send(200, got[0], got[1], {"Cache-Control": "max-age=86400"}) if got else self._send(404, {"error": "not allowed"})
        m = re.fullmatch(r"/art/([A-Za-z0-9_.\-]{1,100})/(cover|hero|logo|blur)", path)
        if m:
            g = next((x for x in (_games or library()) if x["key"] == m.group(1)), None)
            f = g and g["files"].get(m.group(2))
            if f:
                return self._file(f, "max-age=3600")
            url = g and settings.load()["remote_art"] and g.get("remote", {}).get(m.group(2))
            got = store.remote_art(url) if url else None
            return self._send(200, got[0], got[1], {"Cache-Control": "max-age=86400"}) if got else self._send(404, {"error": "no art"})
        top = path.lstrip("/").split("/", 1)[0]
        if top in STATIC_DIRS:
            target = (ROOT / path.lstrip("/")).resolve()
            # must stay inside the static folder itself, not just inside the project (/css/../backend/server.py)
            if (ROOT / top).resolve() in target.parents and target.is_file():
                return self._file(target)
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._host_ok():
            return self._send(403, {"error": "bad host"})
        route = urlparse(self.path).path
        if route not in ("/api/launch", "/api/store/open", "/api/settings", "/api/settings/clear-cache"):
            return self._send(404, {"error": "not found"})
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).hostname not in ("127.0.0.1", "localhost"):
            return self._send(403, {"error": "bad origin"})
        if not secrets.compare_digest(self.headers.get("X-Darksham-Token") or "", TOKEN):
            return self._send(403, {"error": "bad token"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(min(n, 4096)) or b"{}")
        except ValueError:
            return self._send(400, {"error": "bad json"})
        if route == "/api/settings":
            data, problems = settings.update(body)
            if problems:
                return self._send(400, {"ok": False, "problems": problems})
            store.CC = data["region"]
            return self._send(200, dict(settings_payload(), ok=True))
        if route == "/api/settings/clear-cache":
            return self._send(200, {"ok": True, "removed": store.clear_cache()})
        if route == "/api/store/open":
            appid = str(body.get("appid", ""))
            if not appid.isdigit() or len(appid) > 12:
                return self._send(400, {"ok": False, "message": "bad id"})
            ok, msg = steam.open_store(appid)
            sys.stderr.write("[launcher] open store page %s: %s\n" % (appid, msg))
            return self._send(200 if ok else 500, {"ok": ok, "message": msg})
        m = ID_RE.fullmatch(str(body.get("id", "")))
        if not m:
            return self._send(400, {"ok": False, "message": "bad id"})
        game = next((g for g in library() if g["id"] == m.group(0)), None)
        if not game:
            return self._send(404, {"ok": False, "message": "game is not installed"})
        if game["source"] == "lutris":
            ok, msg = lutris.launch(game["appid"], game.get("flatpak", False))
        elif game["source"] == "heroic":
            ok, msg = heroic.launch(game["runner"], game["appid"].split(":", 1)[1], game.get("flatpak", False))
        else:
            ok, msg = steam.launch(game["appid"])
        sys.stderr.write("[launcher] launch %s (%s): %s\n" % (game["title"], game["appid"], msg))
        self._send(200 if ok else 500, {"ok": ok, "message": msg, "title": game["title"]})


def main():
    store.CC = settings.load()["region"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--open", action="store_true", help="open the UI in the default browser")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = "http://127.0.0.1:%d/" % a.port
    print("Darksham Launcher backend on %s  (%d Steam games found)" % (url, len(library())), flush=True)
    if a.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
