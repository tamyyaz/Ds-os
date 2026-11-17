"""Heroic Games Launcher access for the launcher: installed Epic, GOG and Amazon games (read-only), started through Heroic.

File formats, checked against the source of Ludusavi (which reads the same files) and Heroic's protocol handler:
  Epic (legendary)  <legendary dir>/installed.json  : an object app_name -> {title, install_path, is_dlc, ...}
                    legendary dir is one of <root>/legendaryConfig/legendary, <root>/../legendary (Flatpak), ~/.config/legendary
  GOG               <root>/gog_store/installed.json : {"installed": [{"appName", "platform", "install_path"}]}
                    titles from <root>/store_cache/gog_library.json (older: gog_store/library.json): {"games": [{"app_name", "title"}]}
  Amazon (nile)     <root>/store_cache/nile_library.json : {"library": [{"app_name", "title", "install": {"install_path"}}]}
  start a game      heroic://launch/<runner>/<appName>   (runner: legendary, gog or nile)
<root> is ~/.config/heroic, or ~/.var/app/com.heroicgameslauncher.hgl/config/heroic for the Flatpak.
Not read (not verified): play time and last played, sideloaded games, and the remote cover art URLs (cards get a generated look).
Nothing is copied or sent anywhere.
"""
import colorsys
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

RUNNERS = {"legendary": "Epic", "gog": "GOG", "nile": "Amazon"}
APP_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")


def roots():
    """(heroic config root, is_flatpak) for every Heroic folder that exists."""
    home = Path.home()
    xdg = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    cands = []
    if os.environ.get("DARKSHAM_HEROIC"):  # an unusual location, and a fixed folder for tests
        cands.append((Path(os.environ["DARKSHAM_HEROIC"]), False))
    cands += [(xdg / "heroic", False), (home / ".var/app/com.heroicgameslauncher.hgl/config/heroic", True)]
    out, seen = [], set()
    for r, flat in cands:
        if r.is_dir() and str(r) not in seen:
            seen.add(str(r))
            out.append((r, flat))
    return out


def _load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _look(title):
    """A stable colour pair per title, so cards without art still look different from each other."""
    h = int(hashlib.sha1(title.encode("utf-8")).hexdigest()[:6], 16) % 360 / 360
    acc = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.55, 0.9))
    drk = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.65, 0.16))
    return "#%02x%02x%02x" % acc, "#%02x%02x%02x" % drk


def _game(runner, app, title, flat):
    acc, drk = _look(title)
    return {
        "id": "heroic:%s:%s" % (runner, app), "appid": "%s:%s" % (runner, app), "key": "heroic-%s-%s" % (runner, app),
        "title": title, "source": "heroic", "runner": runner, "store": RUNNERS[runner],
        "hours": 0.0, "last_played": 0, "accent": acc, "dark": drk, "files": {}, "flatpak": flat,
    }


def _epic(root, flat):
    dirs = [root / "legendaryConfig" / "legendary", root.parent / "legendary"]
    if not flat:
        dirs.append(Path.home() / ".config" / "legendary")
    for d in dirs:
        data = _load(d / "installed.json")
        if isinstance(data, dict) and data:
            return [(app, g) for app, g in data.items() if isinstance(g, dict) and not g.get("is_dlc") and APP_RE.match(str(app))]
    return []


def scan():
    """Installed Heroic games (alphabetical: Heroic has no play-time data we read)."""
    games, seen = [], set()

    def add(runner, app, title, flat):
        k = (runner, app)
        if k not in seen and APP_RE.match(app) and title:
            seen.add(k)
            games.append(_game(runner, app, title, flat))

    for root, flat in roots():
        for app, g in _epic(root, flat):
            add("legendary", str(app), str(g.get("title") or app), flat)

        installed = _load(root / "gog_store" / "installed.json")
        titles = {}
        for lib in (root / "store_cache" / "gog_library.json", root / "gog_store" / "library.json"):
            data = _load(lib)
            if isinstance(data, dict):
                titles.update({str(x.get("app_name")): x.get("title") for x in data.get("games", []) if isinstance(x, dict)})
        if isinstance(installed, dict):
            for x in installed.get("installed", []):
                if isinstance(x, dict) and x.get("appName") and titles.get(str(x["appName"])):
                    add("gog", str(x["appName"]), str(titles[str(x["appName"])]), flat)

        nile = _load(root / "store_cache" / "nile_library.json")
        if isinstance(nile, dict):
            for x in nile.get("library", []):
                inst = x.get("install") if isinstance(x, dict) else None
                if isinstance(inst, dict) and inst.get("install_path") and x.get("app_name") and x.get("title"):
                    add("nile", str(x["app_name"]), str(x["title"]), flat)
    games.sort(key=lambda g: g["title"].lower())
    return games


def launch(runner, app, flatpak=False):
    """Ask Heroic to start an installed game. Returns (ok, message). Runner and app name are validated."""
    if runner not in RUNNERS or not APP_RE.match(str(app)):
        return False, "bad id"
    url = "heroic://launch/%s/%s" % (runner, app)
    if flatpak and shutil.which("flatpak"):
        cmd = ["flatpak", "run", "com.heroicgameslauncher.hgl", url]
    elif shutil.which("heroic"):
        cmd = ["heroic", url]
    elif shutil.which("flatpak"):
        cmd = ["flatpak", "run", "com.heroicgameslauncher.hgl", url]
    elif shutil.which("xdg-open"):
        cmd = ["xdg-open", url]
    else:
        return False, "Heroic is not installed"
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True, "started"
    except OSError as e:
        return False, str(e)
