"""A fake Steam installation for tests: manifests, play time and generated placeholder art.

Nothing here is real game data or real art. `build(root)` returns the fake Steam folder, laid out
the way Steam does it on Linux (steamapps/, userdata/<id>/config/localconfig.vdf, appcache/librarycache/<appid>/).
"""
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


if __name__ == "__main__":
    import sys
    print(build(sys.argv[1]))
