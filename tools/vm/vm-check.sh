#!/bin/bash
# Darksham OS check: run it INSIDE the machine (VM or real PC) after `bootc switch` and a reboot.
#   curl -fsSL https://raw.githubusercontent.com/tamyyaz/Ds-os/main/tools/vm/vm-check.sh | bash
# It only reads and tests; it changes nothing outside /tmp. The report is printed and saved to ~/darksham-vm-report.txt.
#   --files-only   skip the tests that need a running system (used on a fake root)
# For tests of this script itself: DARKSHAM_CHECK_ROOT=/some/dir checks the files under that dir.

ROOT="${DARKSHAM_CHECK_ROOT:-}"
REPORT="${DARKSHAM_REPORT:-$HOME/darksham-vm-report.txt}"
FILES_ONLY=0
[ "${1:-}" = "--files-only" ] && FILES_ONLY=1
[ -n "$ROOT" ] && FILES_ONLY=1

exec > >(tee "$REPORT") 2>&1

PASS=0; WARN=0; FAIL=0
ok()   { echo "PASS  $*"; PASS=$((PASS + 1)); }
warn() { echo "WARN  $*"; WARN=$((WARN + 1)); }
bad()  { echo "FAIL  $*"; FAIL=$((FAIL + 1)); }
info() { echo "INFO  $*"; }
head_() { echo; echo "== $*"; }

has_file()  { [ -f "$ROOT$1" ] && ok "$2" || bad "$2 (missing: $1)"; }
has_dir()   { [ -d "$ROOT$1" ] && ok "$2" || bad "$2 (missing: $1)"; }
has_exec()  { [ -x "$ROOT$1" ] && ok "$2" || bad "$2 (not executable or missing: $1)"; }
opt_file()  { [ -e "$ROOT$1" ] && ok "$2" || warn "$2 (not found: $1)"; }

echo "Darksham OS check - $(date '+%F %T')"

head_ "System"
if [ -n "$ROOT" ]; then
    info "fake root: $ROOT (running file checks only)"
else
    info "kernel: $(uname -r)"
    info "session: ${XDG_SESSION_TYPE:-unknown} / desktop: ${XDG_CURRENT_DESKTOP:-unknown}"
    info "gpu: $(lspci 2>/dev/null | grep -iE 'vga|3d|display' | head -1 | cut -d: -f3- | sed 's/^ //' || echo unknown)"
    info "ram: $(free -h 2>/dev/null | awk '/Mem:/ {print $2}')  disk free on /: $(df -h / 2>/dev/null | awk 'NR==2 {print $4}')"
    if command -v bootc >/dev/null; then
        img="$(bootc status 2>/dev/null | grep -m1 -iE 'image:|booted' || true)"
        info "bootc: ${img:-no status}"
        if bootc status 2>/dev/null | grep -qi 'tamyyaz/ds-os'; then ok "booted from a ds-os image (ghcr.io/tamyyaz)"; else bad "NOT booted from ghcr.io/tamyyaz/ds-os (run: sudo bootc switch ghcr.io/tamyyaz/ds-os:latest, then reboot)"; fi
    else
        warn "bootc command not found"
    fi
fi
if grep -q 'PRETTY_NAME="Darksham OS"' "$ROOT/usr/lib/os-release" 2>/dev/null; then ok "os-release says Darksham OS"; else bad "os-release does not say Darksham OS"; fi
grep -q '^LANG=ar' "$ROOT/etc/locale.conf" 2>/dev/null && ok "default language is Arabic" || warn "default language is not Arabic (etc/locale.conf)"

head_ "Look and feel"
has_dir  /usr/share/plasma/look-and-feel/org.darksham.desktop "Plasma look-and-feel org.darksham.desktop"
has_file /usr/share/plasma/look-and-feel/org.darksham.desktop/contents/splash/Splash.qml "login splash (Splash.qml)"
has_file /usr/share/wallpapers/Darksham/contents/images/1920x1080.png "Darksham wallpaper"
has_file /usr/share/darksham/branding/logo.png "logo"
has_file /usr/share/darksham/branding/intro.mp4 "logo intro video"
if compgen -G "$ROOT/usr/share/icons/*[Ff]luent*" >/dev/null; then ok "Fluent icon theme installed"; else bad "Fluent icon theme missing"; fi
conf="$(ls "$ROOT"/usr/share/sddm/themes/*breeze*/theme.conf.user 2>/dev/null | head -1)"
if [ -n "$conf" ] && grep -q Darksham "$conf"; then ok "login screen uses the Darksham wallpaper"; else bad "login screen (SDDM) is not set to the Darksham wallpaper"; fi
if [ "$FILES_ONLY" = 0 ]; then
    fc-list 2>/dev/null | grep -qi 'Noto Kufi Arabic' && ok "font Noto Kufi Arabic available" || bad "Noto Kufi Arabic font missing"
    lf="$(kreadconfig6 --group KDE --key LookAndFeelPackage 2>/dev/null || true)"
    info "current look-and-feel in this user: ${lf:-unknown}"
fi

head_ "Darksham Launcher (files)"
L=/usr/share/darksham/launcher
has_file $L/index.html "launcher UI"
has_file $L/backend/server.py "launcher backend"
has_file $L/backend/steam.py "Steam module"
has_file $L/backend/store.py "store module"
has_file $L/js/app.js "launcher script"
has_file $L/fonts/Sora.ttf "font Sora"
has_file $L/fonts/NotoKufiArabic.ttf "font Noto Kufi Arabic (bundled)"
[ ! -e "$ROOT$L/library.js" ] && ok "no personal library data inside the image" || bad "library.js is inside the image"
[ ! -e "$ROOT$L/tools" ] && ok "dev tools were left out of the image" || warn "tools/ is inside the image"
has_exec /usr/bin/darksham-launcher "command darksham-launcher"
has_exec /usr/bin/darksham-session "command darksham-session"
has_file /usr/share/applications/darksham-launcher.desktop "app menu entry"
has_file /usr/share/gamescope-session-plus/sessions.d/darksham "Gaming Mode session definition"
has_file /usr/share/wayland-sessions/gamescope-session-darksham.desktop "Gaming Mode login entry"

if [ "$FILES_ONLY" = 0 ]; then
    head_ "Darksham Launcher (what it needs)"
    PY="$(command -v python3 || true)"
    [ -n "$PY" ] && ok "python3: $($PY --version 2>&1)" || bad "python3 missing"
    CH="$(command -v chromium-browser || command -v chromium || true)"
    [ -n "$CH" ] && ok "Chromium: $CH" || bad "Chromium missing (the image build could not install it): the launcher cannot open"
    "$PY" -c 'import PIL' 2>/dev/null && ok "python3-pillow (game colours)" || warn "python3-pillow missing (the launcher still works, with one accent colour)"
    command -v xdotool >/dev/null && command -v xprop >/dev/null && ok "xdotool + xprop (Gaming Mode window flag)" || warn "xdotool/xprop missing (Gaming Mode only)"
    command -v steam >/dev/null && ok "steam: $(command -v steam)" || warn "steam not found (the launcher cannot start games without it)"
    command -v gamescope-session-plus >/dev/null && ok "gamescope-session-plus present (Gaming Mode can work)" || warn "gamescope-session-plus missing: the Gaming Mode login entry will not work in this image"
    command -v gamescope >/dev/null && ok "gamescope present" || warn "gamescope missing"

    head_ "Darksham Launcher (does it run?)"
    TMP="$(mktemp -d)"
    if [ -n "$PY" ] && [ -f "$L/backend/server.py" ]; then
        PORT="$("$PY" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
        "$PY" "$L/backend/server.py" --port "$PORT" >"$TMP/backend.log" 2>&1 &
        BPID=$!
        up=0; for _ in $(seq 1 50); do curl -sf "http://127.0.0.1:$PORT/api/library" >/dev/null 2>&1 && { up=1; break; }; sleep 0.2; done
        if [ "$up" = 1 ]; then
            ok "backend starts and answers on 127.0.0.1:$PORT"
            n="$(curl -s "http://127.0.0.1:$PORT/api/library" | "$PY" -c 'import sys,json; print(len(json.load(sys.stdin)["games"]))' 2>/dev/null)"
            info "Steam games found by the backend: ${n:-?} (0 is normal in a fresh VM)"
            [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/")" = 200 ] && ok "UI page is served" || bad "UI page is not served"
            [ "$(curl -s -o /dev/null -w '%{http_code}' -X POST -d '{}' "http://127.0.0.1:$PORT/api/launch")" = 403 ] && ok "launch endpoint refuses requests without the token" || bad "launch endpoint did not refuse a tokenless request"
            if [ -n "$CH" ]; then
                shot=/tmp/darksham-launcher-check.png; rm -f "$shot"
                timeout 90 "$CH" --headless=new --disable-gpu --hide-scrollbars --window-size=1920,1080 --virtual-time-budget=8000 \
                    --user-data-dir="$TMP/chromium" --screenshot="$shot" "http://127.0.0.1:$PORT/?static=1" >"$TMP/chromium.log" 2>&1
                if [ -s "$shot" ] && [ "$(stat -c %s "$shot")" -gt 20000 ]; then ok "Chromium rendered the launcher: $shot (open it to look at it)"; else bad "Chromium did not produce a screenshot (see $TMP/chromium.log)"; fi
            fi
        else
            bad "backend did not start (log: $TMP/backend.log)"; tail -5 "$TMP/backend.log"
        fi
        kill "$BPID" 2>/dev/null
    fi
fi

head_ "Summary"
echo "PASS: $PASS   WARN: $WARN   FAIL: $FAIL"
echo "Report saved to $REPORT. Send it back (and a screenshot of the desktop, the login screen and the launcher)."
[ "$FAIL" = 0 ]
