"""Steam access for the launcher: reads the local library (read-only) and starts games.

Names come from appmanifest_*.acf, play time and last played from localconfig.vdf, art and colours
from Steam's own appcache/librarycache. Nothing is copied or sent anywhere.
"""
import colorsys
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # colours fall back to the default accent
    Image = None

SKIP = ("Steamworks Common Redistributables", "Proton", "Steam Linux Runtime", "Steam Deck")
ART = {  # kind -> candidate file names, best first
    "cover": ["library_600x900.jpg", "library_capsule.jpg"],
    "hero": ["library_hero.jpg"],
    "logo": ["logo.png"],
    "blur": ["library_hero_blur.jpg"],
}


def find_steam(hint=None):
    home = Path.home()
    cands = [hint] if hint else []
    cands += [
        r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam",
        home / ".local/share/Steam", home / ".steam/steam",
        home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]
    for c in cands:
        if c and (Path(c) / "steamapps").is_dir():
            return Path(c)
    return None


def libraries(steam):
    libs = [steam]
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(errors="ignore")):
            p = Path(m.group(1).replace("\\\\", "\\"))
            if p not in libs and (p / "steamapps").is_dir():
                libs.append(p)
    return libs


def _value(text, key):
    m = re.search(r'"%s"\s+"([^"]*)"' % key, text)
    return m.group(1) if m else ""


def _play_stats(steam):
    """appid -> (minutes, last_played_unix) from the first localconfig.vdf found."""
    stats = {}
    for cfg in (steam / "userdata").glob("*/config/localconfig.vdf"):
        text = cfg.read_text(errors="ignore")
        for m in re.finditer(r'"(\d+)"\s*\{([^{}]*)\}', text):
            lp, pt = _value(m.group(2), "LastPlayed"), _value(m.group(2), "Playtime")
            if lp or pt:
                stats[m.group(1)] = (int(pt or 0), int(lp or 0))
        break
    return stats


def _best(cache, names):
    for name in names:
        hits = sorted(cache.rglob(name), key=lambda p: -p.stat().st_size)
        if hits:
            return hits[0]
    return None


_colour_cache = {}


def _colours(path):
    """(accent, dark) hex from an image: the most vivid colour, and a deep shade of it."""
    if not (Image and path):
        return "#8ab8ff", "#0b1020"
    key = (str(path), path.stat().st_mtime)
    if key in _colour_cache:
        return _colour_cache[key]
    im = Image.open(path).convert("RGB")
    im.thumbnail((64, 64))
    w, h = im.size
    pixels = [im.getpixel((x, y)) for y in range(h) for x in range(w)]
    best_score, best_rgb = -1.0, (138, 184, 255)
    for r, g, b in pixels:
        hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        score = s * v * (1.0 if 0.25 < v < 0.95 else 0.4)
        if score > best_score:
            best_score, best_rgb = score, (r, g, b)
    hh, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in best_rgb))
    s, v = min(1.0, max(s, 0.55)), min(1.0, max(v, 0.78))
    acc = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hh, s, v))
    drk = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hh, min(1.0, s + 0.1), 0.16))
    out = ("#%02x%02x%02x" % acc, "#%02x%02x%02x" % drk)
    _colour_cache[key] = out
    return out


def scan(steam=None):
    """Installed Steam games, most recently played first. Each has a private "files" dict of art paths."""
    steam = steam or find_steam()
    if not steam:
        return []
    stats = _play_stats(steam)
    games = []
    for lib in libraries(steam):
        for acf in sorted((lib / "steamapps").glob("appmanifest_*.acf")):
            text = acf.read_text(errors="ignore")
            appid, name = _value(text, "appid"), _value(text, "name")
            if not appid.isdigit() or not name or any(s in name for s in SKIP):
                continue
            cache = steam / "appcache" / "librarycache" / appid
            files = {kind: _best(cache, names) for kind, names in ART.items()}
            acc, drk = _colours(files["hero"] or files["cover"])
            minutes, last = stats.get(appid, (0, int(_value(text, "LastPlayed") or 0)))
            games.append({
                "id": "steam:" + appid, "appid": appid, "title": name, "source": "steam",
                "hours": round(minutes / 60, 1), "last_played": last, "accent": acc, "dark": drk,
                "files": {k: v for k, v in files.items() if v},
            })
    games.sort(key=lambda g: -g["last_played"])
    return games


def launch(appid):
    """Ask Steam to start an installed game. Returns (ok, message). The id must be digits only."""
    if not appid.isdigit():
        return False, "bad id"
    uri = "steam://rungameid/" + appid
    try:
        if sys.platform.startswith("win"):
            os.startfile(uri)  # fixed steam:// URI built from digits only
        else:
            steam = shutil.which("steam")
            if steam:
                cmd = [steam, uri]
            elif shutil.which("flatpak"):
                cmd = ["flatpak", "run", "com.valvesoftware.Steam", uri]
            else:
                cmd = ["xdg-open", uri]
            subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True, "started"
    except OSError as e:
        return False, str(e)
