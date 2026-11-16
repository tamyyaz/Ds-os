#!/usr/bin/env python3
"""Reads the local Steam library (read-only) and writes ../library.js for the launcher UI.

Names come from appmanifest_*.acf, play time and last played from localconfig.vdf, and the art
(portrait cover, hero, logo) from Steam's own appcache/librarycache. Nothing is copied or sent
anywhere; the art stays on this computer, so library.js and the images are not committed.

usage: python3 tools/steam_scan.py [--steam PATH] [--out library.js]
"""
import argparse, colorsys, json, os, re, sys, time
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # colours fall back to the default accent
    Image = None

SKIP = ("Steamworks Common Redistributables", "Proton", "Steam Linux Runtime", "Steam Deck")


def find_steam(hint):
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
    sys.exit("Steam folder not found (use --steam PATH)")


def libraries(steam):
    libs = [steam]
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(errors="ignore")):
            p = Path(m.group(1).replace("\\\\", "\\"))
            if p not in libs and (p / "steamapps").is_dir():
                libs.append(p)
    return libs


def acf_value(text, key):
    m = re.search(r'"%s"\s+"([^"]*)"' % key, text)
    return m.group(1) if m else ""


def play_stats(steam):
    """appid -> (minutes, last_played_unix) from the first localconfig.vdf found."""
    stats = {}
    for cfg in (steam / "userdata").glob("*/config/localconfig.vdf"):
        text = cfg.read_text(errors="ignore")
        for m in re.finditer(r'"(\d+)"\s*\{([^{}]*)\}', text):
            body = m.group(2)
            lp, pt = acf_value(body, "LastPlayed"), acf_value(body, "Playtime")
            if lp or pt:
                stats[m.group(1)] = (int(pt or 0), int(lp or 0))
        break
    return stats


def best(cache, names):
    """First existing file whose name is in `names` (searches the app's cache folder recursively)."""
    for name in names:
        hits = sorted(cache.rglob(name), key=lambda p: -p.stat().st_size)
        if hits:
            return hits[0]
    return None


def colours(path):
    """(accent, dark) hex from an image: the most vivid colour, and a deep shade of it."""
    if not (Image and path):
        return "#8ab8ff", "#0b1020"
    im = Image.open(path).convert("RGB")
    im.thumbnail((64, 64))
    best_score, best_rgb = -1.0, (138, 184, 255)
    for r, g, b in im.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        score = s * v * (1.0 if 0.25 < v < 0.95 else 0.4)
        if score > best_score:
            best_score, best_rgb = score, (r, g, b)
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in best_rgb))
    s = min(1.0, max(s, 0.55))
    v = min(1.0, max(v, 0.78))
    acc = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))
    drk = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, min(1.0, s + 0.1), 0.16))
    return "#%02x%02x%02x" % acc, "#%02x%02x%02x" % drk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steam")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "library.js"))
    a = ap.parse_args()
    steam = find_steam(a.steam)
    stats = play_stats(steam)
    cache_root = steam / "appcache" / "librarycache"
    games = []
    for lib in libraries(steam):
        for acf in sorted((lib / "steamapps").glob("appmanifest_*.acf")):
            text = acf.read_text(errors="ignore")
            appid, name = acf_value(text, "appid"), acf_value(text, "name")
            if not appid or not name or any(s in name for s in SKIP):
                continue
            cache = cache_root / appid
            hero = best(cache, ["library_hero.jpg"])
            cover = best(cache, ["library_600x900.jpg", "library_capsule.jpg"])
            logo = best(cache, ["logo.png"])
            blur = best(cache, ["library_hero_blur.jpg"])
            acc, drk = colours(hero or cover)
            minutes, last = stats.get(appid, (0, int(acf_value(text, "LastPlayed") or 0)))
            uri = lambda p: p.as_uri() if p else ""
            games.append({
                "id": "steam:" + appid, "appid": appid, "title": name, "source": "steam",
                "hours": round(minutes / 60, 1), "last_played": last,
                "accent": acc, "dark": drk,
                "cover": uri(cover), "hero": uri(hero), "logo": uri(logo), "blur": uri(blur),
            })
    games.sort(key=lambda g: -g["last_played"])
    out = Path(a.out)
    out.write_text("window.LIBRARY = " + json.dumps({"generated": int(time.time()), "games": games}, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"{len(games)} games -> {out}")
    for g in games:
        print(" ", g["title"], "| cover" if g["cover"] else "| NO cover", "| hero" if g["hero"] else "| NO hero", "| logo" if g["logo"] else "| NO logo", g["accent"], f'{g["hours"]}h')


main()
