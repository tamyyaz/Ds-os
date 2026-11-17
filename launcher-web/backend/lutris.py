"""Lutris access for the launcher: reads Lutris's own game database (read-only) and starts games through Lutris.

Formats are from the Lutris source (lutris/settings.py and database/schema.py): the database is
<data dir>/pga.db with a `games` table (id, name, slug, runner, platform, installed, lastplayed, playtime in
hours, ...), cover art in <data dir>/coverart/<slug>.*, banners in <data dir>/banners/<slug>.* and icons in
<xdg data>/icons/hicolor/128x128/apps/lutris_<slug>.png. A game is started with `lutris lutris:rungameid/<id>`.
Nothing is copied or sent anywhere, and the database is opened read-only.
"""
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import steam  # for the shared colour picker

ART_EXT = (".jpg", ".png", ".jpeg", ".webp")


def data_dirs():
    """(data dir, is_flatpak) for every Lutris data folder that has a database."""
    home = Path.home()
    xdg = Path(os.environ.get("XDG_DATA_HOME") or home / ".local/share")
    cands = []
    if os.environ.get("DARKSHAM_LUTRIS"):  # an unusual location, and a fixed folder for tests
        cands.append((Path(os.environ["DARKSHAM_LUTRIS"]), False))
    cands += [(xdg / "lutris", False), (home / ".var/app/net.lutris.Lutris/data/lutris", True)]
    out, seen = [], set()
    for d, flat in cands:
        if (d / "pga.db").is_file() and str(d) not in seen:
            seen.add(str(d))
            out.append((d, flat))
    return out


def _art(folder, slug):
    for ext in ART_EXT:
        p = folder / (slug + ext)
        if slug and p.is_file():
            return p
    return None


def scan():
    """Installed Lutris games (most recently played first)."""
    games = []
    for d, flat in data_dirs():
        try:
            con = sqlite3.connect("file:%s?mode=ro" % (d / "pga.db").as_posix(), uri=True, timeout=2)
        except sqlite3.Error:
            continue
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(games)")}
            if not {"id", "name"} <= cols:
                continue
            want = [c for c in ("id", "name", "slug", "runner", "platform", "installed", "lastplayed", "playtime") if c in cols]
            for row in con.execute("SELECT %s FROM games" % ", ".join(want)):
                r = dict(zip(want, row))
                if "installed" in r and not r["installed"]:
                    continue
                if not r.get("name"):
                    continue
                slug = r.get("slug") or ""
                icon_dir = d.parent.parent / "icons/hicolor/128x128/apps" if not flat else d.parent / "icons/hicolor/128x128/apps"
                files = {}
                cover = _art(d / "coverart", slug) or _art(d / "banners", slug) or _art(icon_dir, "lutris_" + slug)
                if cover:
                    files["cover"] = cover
                acc, drk = steam.colours(cover)
                games.append({
                    "id": "lutris:%d" % r["id"], "appid": str(r["id"]), "title": r["name"], "source": "lutris",
                    "runner": r.get("runner") or "", "platform": r.get("platform") or "",
                    "hours": round(float(r.get("playtime") or 0), 1), "last_played": int(r.get("lastplayed") or 0),
                    "accent": acc, "dark": drk, "files": files, "flatpak": flat,
                })
        except sqlite3.Error:
            continue
        finally:
            con.close()
    games.sort(key=lambda g: -g["last_played"])
    return games


def launch(game_id, flatpak=False):
    """Ask Lutris to start a game by its numeric id. Returns (ok, message)."""
    if not str(game_id).isdigit():
        return False, "bad id"
    uri = "lutris:rungameid/%s" % game_id
    if flatpak and shutil.which("flatpak"):
        cmd = ["flatpak", "run", "net.lutris.Lutris", uri]
    elif shutil.which("lutris"):
        cmd = ["lutris", uri]
    elif shutil.which("flatpak"):
        cmd = ["flatpak", "run", "net.lutris.Lutris", uri]
    else:
        return False, "Lutris is not installed"
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True, "started"
    except OSError as e:
        return False, str(e)
