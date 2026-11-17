"""Launcher settings, kept in a small JSON file (~/.config/darksham/settings.json, %APPDATA%\\darksham on Windows).

Only known keys with valid values are accepted; anything else is rejected, never stored.
  region   the store's price region, one of REGIONS (a Steam country code)
  sources  which game sources are shown: steam, lutris, heroic (true / false)
The language is kept by the page itself (it needs no server).
"""
import json
import os
import threading
from pathlib import Path

REGIONS = ["us", "gb", "de", "sa", "ae", "eg", "tr", "ca", "au", "br", "in"]
SOURCES = ("steam", "lutris", "heroic")
_lock = threading.Lock()


def path():
    if os.environ.get("DARKSHAM_SETTINGS"):
        return Path(os.environ["DARKSHAM_SETTINGS"])
    base = os.environ.get("APPDATA") if os.name == "nt" else None
    base = Path(base) if base else Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "darksham" / "settings.json"


def defaults():
    env = (os.environ.get("DARKSHAM_CC") or "us").lower()
    return {"region": env if env in REGIONS else "us", "sources": {s: True for s in SOURCES}}


def _valid(patch):
    """(clean patch, list of problems). Unknown keys are problems, not ignored."""
    clean, problems = {}, []
    if not isinstance(patch, dict):
        return {}, ["settings must be an object"]
    for key, value in patch.items():
        if key == "region":
            if isinstance(value, str) and value in REGIONS:
                clean["region"] = value
            else:
                problems.append("unknown region")
        elif key == "sources":
            if not isinstance(value, dict):
                problems.append("sources must be an object")
                continue
            srcs = {}
            for name, on in value.items():
                if name in SOURCES and isinstance(on, bool):
                    srcs[name] = on
                else:
                    problems.append("bad source setting: %s" % str(name)[:20])
            clean["sources"] = srcs
        else:
            problems.append("unknown setting: %s" % str(key)[:20])
    return clean, problems


def load():
    data = defaults()
    try:
        saved = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return data
    clean, _ = _valid(saved)  # a hand-edited file with bad values falls back to the defaults for those keys
    if "region" in clean:
        data["region"] = clean["region"]
    data["sources"].update(clean.get("sources", {}))
    return data


def update(patch):
    """Apply a patch. Returns (settings, problems); nothing is saved if there is any problem."""
    clean, problems = _valid(patch)
    if problems:
        return load(), problems
    with _lock:
        data = load()
        if "region" in clean:
            data["region"] = clean["region"]
        data["sources"].update(clean.get("sources", {}))
        p = path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        os.replace(tmp, p)
    return data, []
