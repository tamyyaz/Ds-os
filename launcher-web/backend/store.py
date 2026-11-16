"""Store data for the launcher: Steam's public store API, cached on disk, and a small image proxy.

Only public store data is used (no login, no account data is sent). Requests carry a generic user agent.
Purchases never happen here: "open" hands the store page to the Steam client, where the user buys.
Responses are cached (home 1 h, app details 24 h, images 7 days) and served stale if the network is down.
"""
import hashlib
import html as htmllib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "DarkshamLauncher/0.1"
CC = os.environ.get("DARKSHAM_CC", "us")          # price region
LANGS = {"ar": "arabic", "en": "english"}
CDN = "https://cdn.akamai.steamstatic.com/steam/apps/%s/%s"
IMG_HOSTS = {"cdn.akamai.steamstatic.com", "shared.akamai.steamstatic.com", "cdn.cloudflare.steamstatic.com", "shared.cloudflare.steamstatic.com"}
ART = {  # kind -> files to try on the CDN, best first
    "cover": ["library_600x900.jpg", "header.jpg"],
    "hero": ["library_hero.jpg", "header.jpg"],
    "logo": ["logo.png"],
    "header": ["header.jpg"],
}
NOT_GAMES = ("Steam Deck", "Steam Frame", "Steam Machine", "Steam Controller", "Steam Link", "Valve Index",
             " Pack", "DLC", "Soundtrack", "Season Pass", "Upgrade", "Expansion", "Bundle")
MAX_IMG = 8 * 1024 * 1024

ROOT = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".cache")) / "darksham" / "store"
(ROOT / "img").mkdir(parents=True, exist_ok=True)
(ROOT / "json").mkdir(parents=True, exist_ok=True)


def _fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(MAX_IMG + 1), r.headers.get("Content-Type", "application/octet-stream")


def _cached_json(name, url, ttl):
    """JSON from disk if fresh, else from the network; stale disk copy if the network fails."""
    path = ROOT / "json" / (hashlib.sha1(name.encode()).hexdigest() + ".json")
    if path.exists() and time.time() - path.stat().st_mtime < ttl:
        return json.loads(path.read_text(encoding="utf-8")), False
    try:
        data, _ = _fetch(url, 20)
        obj = json.loads(data.decode("utf-8"))
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return obj, False
    except (urllib.error.URLError, OSError, ValueError):
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8")), True
        raise


def _item(x):
    return {
        "appid": int(x["id"]), "name": htmllib.unescape(x.get("name", "")),
        "discount": int(x.get("discount_percent") or 0),
        "original": x.get("original_price"), "final": x.get("final_price"), "currency": x.get("currency") or "USD",
        "windows": bool(x.get("windows_available")), "linux": bool(x.get("linux_available")),
        # new releases often have no library_* art on the CDN, so keep the store's own images as fallbacks
        "header": x.get("header_image") or "", "capsule": x.get("large_capsule_image") or "",
    }


def home(lang="en"):
    """Shelves of games: featured, top sellers, specials, new releases, coming soon. Returns {shelves, stale}."""
    l = LANGS.get(lang, "english")
    raw, stale = _cached_json("home-%s-%s" % (CC, l), "https://store.steampowered.com/api/featuredcategories?cc=%s&l=%s" % (CC, l), 3600)
    lists = {"top_sellers": (raw.get("top_sellers") or {}).get("items", []),
             "specials": (raw.get("specials") or {}).get("items", []),
             "new_releases": (raw.get("new_releases") or {}).get("items", []),
             "coming_soon": (raw.get("coming_soon") or {}).get("items", [])}
    try:  # the "featured" list is a second, separate call; the shelves still work without it
        feat, stale2 = _cached_json("featured-%s-%s" % (CC, l), "https://store.steampowered.com/api/featured/?cc=%s&l=%s" % (CC, l), 3600)
        lists["featured"] = feat.get("featured_win", [])
        stale = stale or stale2
    except (urllib.error.URLError, OSError, ValueError):
        lists["featured"] = []
    shelves = []
    for key in ("featured", "top_sellers", "specials", "new_releases", "coming_soon"):
        items = []
        for x in lists[key]:
            if x.get("type") not in (0, None) or not x.get("id") or any(b in x.get("name", "") for b in NOT_GAMES):
                continue
            if any(i["appid"] == x["id"] for i in items):
                continue
            items.append(_item(x))
        if items:
            shelves.append({"id": key, "items": items})
    return {"shelves": shelves, "stale": stale}


def _strip(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", htmllib.unescape(html or ""))).strip()


def app(appid, lang="en"):
    """Details for one app. Returns a dict, or None if the store has nothing for it."""
    l = LANGS.get(lang, "english")
    raw, stale = _cached_json("app-%s-%s-%s" % (appid, CC, l), "https://store.steampowered.com/api/appdetails?appids=%d&cc=%s&l=%s" % (appid, CC, l), 86400)
    entry = raw.get(str(appid)) or {}
    d = entry.get("data")
    if not entry.get("success") or not d:
        return None
    langs_text = _strip(d.get("supported_languages"))
    price = d.get("price_overview") or {}
    return {
        "appid": appid, "name": htmllib.unescape(d.get("name", "")), "type": d.get("type"),
        "description": _strip(d.get("short_description", "")),
        "genres": [g["description"] for g in d.get("genres", [])][:4],
        "developers": d.get("developers", [])[:2], "publishers": d.get("publishers", [])[:2],
        "release": (d.get("release_date") or {}).get("date", ""), "coming_soon": bool((d.get("release_date") or {}).get("coming_soon")),
        "free": bool(d.get("is_free")),
        "price": {"final": price.get("final"), "original": price.get("initial"), "discount": price.get("discount_percent", 0),
                  "currency": price.get("currency", "USD"), "text": price.get("final_formatted", "")} if price else None,
        "arabic": bool(re.search(r"(Arabic|العربية)", langs_text)),
        "windows": bool((d.get("platforms") or {}).get("windows")), "linux": bool((d.get("platforms") or {}).get("linux")),
        "metacritic": (d.get("metacritic") or {}).get("score"),
        "screenshots": [s.get("path_full") or s.get("path_thumbnail") for s in d.get("screenshots", [])[:6] if s],
        "thumbs": [s.get("path_thumbnail") or s.get("path_full") for s in d.get("screenshots", [])[:6] if s],
        "stale": stale,
    }


def image(url):
    """(bytes, content-type) of an allowed Steam image, cached on disk for 7 days. None if not allowed or missing."""
    u = urllib.parse.urlparse(url)
    if u.scheme != "https" or u.hostname not in IMG_HOSTS:
        return None
    path = ROOT / "img" / hashlib.sha1(url.encode()).hexdigest()
    meta = path.with_suffix(".type")
    if path.exists() and time.time() - path.stat().st_mtime < 7 * 86400:
        return path.read_bytes(), meta.read_text() if meta.exists() else "image/jpeg"
    try:
        data, ctype = _fetch(url)
    except (urllib.error.URLError, OSError):
        if path.exists():
            return path.read_bytes(), meta.read_text() if meta.exists() else "image/jpeg"
        return None
    if len(data) > MAX_IMG or not ctype.startswith("image/"):
        return None
    path.write_bytes(data)
    meta.write_text(ctype)
    return data, ctype


def art(appid, kind):
    """Cover / hero / logo / header for an app id, trying the fallbacks in ART."""
    for name in ART.get(kind, []):
        got = image(CDN % (appid, name))
        if got:
            return got
    return None
