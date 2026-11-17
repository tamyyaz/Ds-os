"""Desktop applications for the launcher's Apps screen: reads the standard .desktop files (read-only) and starts them.

Where: $XDG_DATA_HOME/applications, the XDG data dirs, and the Flatpak exports (system and user). The first file
with a given name wins, like the desktop does, so a user's copy overrides the system one.
Shown: Type=Application entries that are not hidden (NoDisplay / Hidden), do not need a terminal, are not games
(those are in the library), are not this launcher, and whose TryExec exists. Icons are looked up in the icons
folders next to those applications folders. An app is started with `gio launch <file>` (which handles the Exec
line the way the desktop does); if gio is missing the Exec line is split without a shell and its field codes
(%u, %F, ...) are dropped. Only ids that were scanned can be started, so no command comes from the page.
"""
import configparser
import hashlib
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,150}\.desktop$")
ICON_EXT = (".png", ".svg", ".xpm", ".jpg", ".webp")
ICON_SIZES = ("256x256", "512x512", "128x128", "192x192", "96x96", "64x64", "scalable", "48x48", "72x72", "32x32")
SELF_IDS = {"darksham-launcher.desktop"}


def app_dirs():
    home = Path.home()
    if os.environ.get("DARKSHAM_APPS_DIRS"):  # a fixed list for tests (separated like PATH)
        return [Path(p) for p in os.environ["DARKSHAM_APPS_DIRS"].split(os.pathsep) if p]
    xdg_home = Path(os.environ.get("XDG_DATA_HOME") or home / ".local/share")
    dirs = [xdg_home / "applications"]
    for d in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":"):
        if d:
            dirs.append(Path(d) / "applications")
    dirs += [Path("/var/lib/flatpak/exports/share/applications"), home / ".local/share/flatpak/exports/share/applications"]
    seen, out = set(), []
    for d in dirs:
        if str(d) not in seen:
            seen.add(str(d))
            out.append(d)
    return out


def _parse(path):
    cp = configparser.RawConfigParser(strict=False, interpolation=None)
    cp.optionxform = str  # keys are case-sensitive (Name[ar] vs name)
    try:
        cp.read_string(Path(path).read_text(encoding="utf-8", errors="replace"))
    except (OSError, configparser.Error):
        return None
    return dict(cp["Desktop Entry"]) if cp.has_section("Desktop Entry") else None


def _bool(v):
    return str(v).strip().lower() == "true"


def find_icon(name, roots):
    """A file for an Icon= value: an absolute path, or a name looked up in the icon folders."""
    if not name:
        return None
    if name.startswith("/"):
        p = Path(name)
        return p if p.is_file() and p.suffix.lower() in ICON_EXT else None
    for root in roots:
        for size in ICON_SIZES:
            for ext in ICON_EXT:
                p = root / "icons" / "hicolor" / size / "apps" / (name + ext)
                if p.is_file():
                    return p
        for ext in ICON_EXT:
            p = root / "pixmaps" / (name + ext)
            if p.is_file():
                return p
    return None


def scan():
    """Applications for the Apps screen, sorted by name. Each has a private 'path' and 'icon_file'."""
    dirs = app_dirs()
    roots = [d.parent for d in dirs]
    apps, seen = [], set()
    for d in dirs:
        try:
            files = sorted(d.glob("*.desktop"))
        except OSError:
            continue
        for f in files:
            if f.name in seen:
                continue
            seen.add(f.name)  # the first folder that has this name decides, even if it hides the app
            e = _parse(f)
            if not e or e.get("Type") != "Application" or not ID_RE.match(f.name) or f.name in SELF_IDS:
                continue
            if _bool(e.get("NoDisplay")) or _bool(e.get("Hidden")) or _bool(e.get("Terminal")):
                continue
            if "Game" in (e.get("Categories") or "").split(";"):
                continue
            if not e.get("Name") or not e.get("Exec"):
                continue
            if e.get("TryExec") and not (shutil.which(e["TryExec"]) or Path(e["TryExec"]).is_file()):
                continue
            icon = find_icon(e.get("Icon", ""), roots)
            apps.append({
                "id": f.name, "key": "app-" + hashlib.sha1(f.name.encode()).hexdigest()[:12],
                "name": e["Name"], "name_ar": e.get("Name[ar]", ""), "comment": e.get("Comment", ""),
                "path": f, "icon_file": icon,
            })
    apps.sort(key=lambda a: a["name"].lower())
    return apps


def _exec_argv(exec_line):
    """Split an Exec line without a shell and drop the field codes (%u, %F, ...); %% becomes %."""
    try:
        parts = shlex.split(exec_line)
    except ValueError:
        return []
    out = []
    for p in parts:
        p = p.replace("%%", "\0")
        p = re.sub(r"%[fFuUdDnNickvm]", "", p).replace("\0", "%")
        if p:
            out.append(p)
    return out


def launch(app):
    """Start a scanned app (a dict from scan()). Returns (ok, message)."""
    path = Path(app["path"])
    if shutil.which("gio"):
        cmd = ["gio", "launch", str(path)]
    else:
        e = _parse(path) or {}
        cmd = _exec_argv(e.get("Exec", ""))
        if not cmd:
            return False, "nothing to run"
    try:
        subprocess.Popen(cmd, cwd=str(Path.home()), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True, "started"
    except OSError as e:
        return False, str(e)
