"""A fake Steam installation for tests: manifests, play time and generated placeholder art.

Nothing here is real game data or real art. `build(root)` returns the fake Steam folder, laid out
the way Steam does it on Linux (steamapps/, userdata/<id>/config/localconfig.vdf, appcache/librarycache/<appid>/).
"""
import sqlite3
from pathlib import Path

from PIL import Image, ImageDraw

GAMES = [
    # appid, name, last played (unix), minutes, art kinds present
    ("1001", "Test Game One", 1760000000, 600, ("cover", "hero", "logo", "blur")),
    ("1002", "Another Game", 1750000000, 90, ("hero",)),
    ("1003", "Third Game", 0, 0, ()),
]


def _gradient(path, size, c1, c2, mode="RGB", fmt=None):
    img = Image.new(mode, size)
    d = ImageDraw.Draw(img)
    w, h = size
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, fmt)


def _acf(appid, name, last):
    return '"AppState"\n{\n\t"appid"\t\t"%s"\n\t"name"\t\t"%s"\n\t"LastPlayed"\t\t"%d"\n}\n' % (appid, name, last)


def build(root):
    root = Path(root)
    steam = root / "Steam"
    lib2 = root / "SteamLibrary"
    (steam / "steamapps").mkdir(parents=True)
    (lib2 / "steamapps").mkdir(parents=True)

    # a second library folder, written the way Steam does (backslashes doubled on Windows paths)
    p2 = str(lib2).replace("\\", "\\\\")
    (steam / "steamapps" / "libraryfolders.vdf").write_text(
        '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n\t"1"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n'
        % (str(steam).replace("\\", "\\\\"), p2), encoding="utf-8")

    # games 1001 and 1002 live in the first library, 1003 in the second; plus a tool Steam installs that is not a game
    (steam / "steamapps" / "appmanifest_1001.acf").write_text(_acf("1001", GAMES[0][1], 0), encoding="utf-8")
    (steam / "steamapps" / "appmanifest_1002.acf").write_text(_acf("1002", GAMES[1][1], 0), encoding="utf-8")
    (lib2 / "steamapps" / "appmanifest_1003.acf").write_text(_acf("1003", GAMES[2][1], 0), encoding="utf-8")
    (steam / "steamapps" / "appmanifest_228980.acf").write_text(_acf("228980", "Steamworks Common Redistributables", 0), encoding="utf-8")

    apps = "".join('\t\t\t\t\t"%s"\n\t\t\t\t\t{\n\t\t\t\t\t\t"LastPlayed"\t\t"%d"\n\t\t\t\t\t\t"Playtime"\t\t"%d"\n\t\t\t\t\t}\n' % (a, last, mins)
                   for a, _, last, mins, _ in GAMES if last or mins)
    cfg = steam / "userdata" / "42" / "config"
    cfg.mkdir(parents=True)
    (cfg / "localconfig.vdf").write_text(
        '"UserLocalConfigStore"\n{\n\t"Software"\n\t{\n\t\t"Valve"\n\t\t{\n\t\t\t"Steam"\n\t\t\t{\n\t\t\t\t"apps"\n\t\t\t\t{\n%s\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n' % apps,
        encoding="utf-8")

    palette = {"1001": ((240, 130, 40), (40, 15, 30)), "1002": ((60, 170, 230), (10, 25, 60)), "1003": ((150, 150, 160), (20, 20, 25))}
    for appid, _, _, _, kinds in GAMES:
        c1, c2 = palette[appid]
        cache = steam / "appcache" / "librarycache" / appid
        # Steam keeps newer art in hash-named subfolders; the scanner searches recursively
        sub = cache / "0123456789abcdef0123456789abcdef01234567"
        if "cover" in kinds:
            _gradient(sub / "library_600x900.jpg", (600, 900), c1, c2)
        if "hero" in kinds:
            _gradient(sub / "library_hero.jpg", (1920, 620), c2, c1)
        if "blur" in kinds:
            _gradient(sub / "library_hero_blur.jpg", (192, 62), c2, c1)
        if "logo" in kinds:
            img = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
            ImageDraw.Draw(img).rectangle([40, 60, 560, 140], fill=(255, 255, 255, 255))
            (cache).mkdir(parents=True, exist_ok=True)
            img.save(cache / "logo.png")
    return steam


def build_lutris(root):
    """A fake Lutris data folder (<root>/lutris) with pga.db, cover art and a banner. Returns the folder."""
    d = Path(root) / "lutris"
    d.mkdir(parents=True)
    con = sqlite3.connect(d / "pga.db")
    con.execute("CREATE TABLE games (id INTEGER PRIMARY KEY, name TEXT, slug TEXT, runner TEXT, platform TEXT, "
                "installed INTEGER, lastplayed INTEGER, playtime REAL, directory TEXT, service TEXT, service_id TEXT, configpath TEXT)")
    con.executemany("INSERT INTO games (id, name, slug, runner, platform, installed, lastplayed, playtime) VALUES (?,?,?,?,?,?,?,?)", [
        (5, "Lutris Game A", "lutris-game-a", "wine", "Windows", 1, 1755000000, 3.5),
        (6, "Lutris Game B", "lutris-game-b", "linux", "Linux", 1, 0, 0),
        (7, "Not Installed", "not-installed", "wine", "Windows", 0, 1700000000, 9.0),
    ])
    con.commit()
    con.close()
    _gradient(d / "coverart" / "lutris-game-a.jpg", (264, 352), (90, 200, 120), (10, 40, 30))
    _gradient(d / "banners" / "lutris-game-b.png", (184, 69), (200, 90, 90), (40, 10, 10), fmt="PNG")
    return d


def build_heroic(root):
    """A fake Heroic config folder (<root>/heroic): Epic (legendary), GOG and Amazon (nile) files. Returns it."""
    import json
    h = Path(root) / "heroic"
    (h / "legendaryConfig" / "legendary").mkdir(parents=True)
    (h / "gog_store").mkdir(parents=True)
    (h / "store_cache").mkdir(parents=True)
    (h / "legendaryConfig" / "legendary" / "installed.json").write_text(json.dumps({
        "EpicApp1": {"app_name": "EpicApp1", "title": "Epic Game", "install_path": "/games/epic", "platform": "Windows", "is_dlc": False},
        "EpicDlc1": {"app_name": "EpicDlc1", "title": "Epic Game DLC", "install_path": "/games/epic", "is_dlc": True},
        "bad name": {"app_name": "bad name", "title": "Bad Name", "install_path": "/x"},
    }), encoding="utf-8")
    (h / "gog_store" / "installed.json").write_text(json.dumps({"installed": [
        {"appName": "1207658930", "platform": "windows", "install_path": "/games/gog"},
        {"appName": "999", "platform": "windows", "install_path": "/games/unknown-title"},
    ]}), encoding="utf-8")
    (h / "store_cache" / "gog_library.json").write_text(json.dumps({"games": [
        {"app_name": "1207658930", "title": "GOG Game", "art_square": "https://images.gog-statics.com/abc_tall.jpg",
         "art_cover": "https://images.gog-statics.com/abc_wide.jpg", "art_background": "https://images.gog.com/abc_bg.jpg"},
        {"app_name": "555", "title": "GOG Not Installed"}]}), encoding="utf-8")
    (h / "store_cache" / "legendary_library.json").write_text(json.dumps({"library": [
        {"app_name": "EpicApp1", "title": "Epic Game", "art_square": "https://cdn1.epicgames.com/x/tall.jpg",
         "art_cover": "https://cdn1.epicgames.com/x/wide.jpg"}]}), encoding="utf-8")
    (h / "store_cache" / "nile_library.json").write_text(json.dumps({"library": [
        {"app_name": "amzn1.adg.abc", "title": "Amazon Game", "art_square": "fallback", "art_cover": "http://insecure.example/x.jpg",
         "install": {"install_path": "/games/amazon", "platform": "Windows"}},
        {"app_name": "amzn1.adg.def", "title": "Amazon Not Installed", "install": {}},
    ]}), encoding="utf-8")
    return h


def build_apps(root):
    """Fake .desktop files in two applications folders (user first, like the desktop). Returns the folders joined like PATH."""
    import os
    base = Path(root) / "apps"
    user, system = base / "user" / "applications", base / "system" / "applications"
    user.mkdir(parents=True)
    system.mkdir(parents=True)

    def entry(folder, name, body):
        (folder / name).write_text("[Desktop Entry]\nType=Application\n" + body, encoding="utf-8")

    entry(system, "firefox.desktop", "Name=Firefox\nName[ar]=\u0641\u0627\u064a\u0631\u0641\u0648\u0643\u0633\nComment=Web browser\nExec=firefox %u\nIcon=firefox\nCategories=Network;WebBrowser;\n")
    entry(system, "konsole.desktop", "Name=Konsole\nExec=konsole\nIcon=utilities-terminal\nTerminal=false\nCategories=System;TerminalEmulator;\n")
    entry(system, "htop.desktop", "Name=Htop\nExec=htop\nTerminal=true\n")                     # needs a terminal
    entry(system, "hidden.desktop", "Name=Hidden\nExec=hidden\nNoDisplay=true\n")               # not for menus
    entry(system, "steam.desktop", "Name=Steam\nExec=steam\nCategories=Network;Game;\n")        # games live in the library
    entry(system, "darksham-launcher.desktop", "Name=Darksham Launcher\nExec=darksham-launcher\n")  # this app
    entry(system, "notinstalled.desktop", "Name=Gone\nExec=gone\nTryExec=definitely-not-installed-xyz\n")
    (system / "broken.desktop").write_text("this is not a desktop file", encoding="utf-8")
    (system / "bad name.desktop").write_text("[Desktop Entry]\nType=Application\nName=Bad\nExec=bad\n", encoding="utf-8")
    entry(system, "dup.desktop", "Name=Dup System\nExec=dup-system\n")
    entry(user, "dup.desktop", "Name=Dup User\nExec=dup-user\n")                               # the user's copy wins
    _gradient(base / "system" / "icons" / "hicolor" / "128x128" / "apps" / "firefox.png", (128, 128), (255, 120, 40), (60, 20, 10), fmt="PNG")
    return str(user) + os.pathsep + str(system)


if __name__ == "__main__":
    import sys
    print(build(sys.argv[1]))
    print(build_lutris(sys.argv[1]))
    print(build_heroic(sys.argv[1]))
    print(build_apps(sys.argv[1]))   # last line: the applications folders, for DARKSHAM_APPS_DIRS
