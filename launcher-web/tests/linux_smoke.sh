#!/bin/bash
# End-to-end smoke test of the launcher on a fake Steam, with a real Chrome/Chromium:
#   1. darksham-launcher (the real wrapper) with a stand-in browser: free port, backend up, flags, cleanup
#   2. the backend + real Chrome rendering the UI to screenshots (Arabic games, English games, profile)
# Usage: bash launcher-web/tests/linux_smoke.sh [output-dir]
# Overrides for other machines: PYTHON, CHROME_BIN, CHROME_EXTRA (extra Chrome flags).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$APP/.." && pwd)"
PYTHON="${PYTHON:-python3}"
OUT="${1:-$PWD/launcher-smoke}"
mkdir -p "$OUT"
CHROME="${CHROME_BIN:-$(command -v google-chrome || command -v google-chrome-stable || command -v chromium-browser || command -v chromium || true)}"
[ -n "$CHROME" ] || { echo "no Chrome/Chromium found"; exit 1; }
echo "python: $($PYTHON --version 2>&1)   chrome: $CHROME"

# a fresh HOME with a fake Steam where the backend looks for it on Linux
HOME="$(mktemp -d)"
export HOME
mkdir -p "$HOME/.local/share"
"$PYTHON" "$HERE/fixture.py" "$HOME/.local/share" >/dev/null
test -d "$HOME/.local/share/Steam/steamapps"
# On Linux the backend must find it at its default place (~/.local/share/Steam); elsewhere point it there
case "$(uname -s)" in Linux) ;; *) export DARKSHAM_STEAM="$HOME/.local/share/Steam" ;; esac

echo "== 1. the wrapper script"
export FAKE_URL_OUT="$OUT/wrapper_url.txt"
rm -f "$FAKE_URL_OUT"
DARKSHAM_LAUNCHER_DIR="$APP" DARKSHAM_PYTHON="$PYTHON" DARKSHAM_BROWSER="$HERE/fake_browser.sh" \
    bash "$REPO/system_files/usr/bin/darksham-launcher" | grep -vE '^\[launcher\]'
test -s "$FAKE_URL_OUT" || { echo "FAIL: the stand-in browser did not get a working page"; exit 1; }
URL="$(cat "$FAKE_URL_OUT")"
sleep 1
if curl -s -m 2 -o /dev/null "$URL"; then echo "FAIL: the backend is still running after the browser exited"; exit 1; fi
echo "OK: wrapper started the backend on $URL, the page and API worked, and the backend stopped with the browser"

echo "== 1b. kiosk flags"
KIOSK_ARGS="$(DARKSHAM_LAUNCHER_DIR="$APP" DARKSHAM_PYTHON="$PYTHON" DARKSHAM_BROWSER="$HERE/fake_browser.sh" bash "$REPO/system_files/usr/bin/darksham-launcher" --kiosk | grep 'fake browser args')"
case "$KIOSK_ARGS" in *--kiosk*) echo "OK: --kiosk reaches the browser" ;; *) echo "FAIL: --kiosk missing"; exit 1 ;; esac

echo "== 2. real Chrome renders the UI"
PORT="$("$PYTHON" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
"$PYTHON" "$APP/backend/server.py" --port "$PORT" >"$OUT/backend.log" 2>&1 &
BACKEND=$!
trap 'kill "$BACKEND" 2>/dev/null || true' EXIT
for _ in $(seq 1 50); do curl -sf "http://127.0.0.1:$PORT/api/library" >/dev/null && break; sleep 0.2; done
shot() {  # name, query
    # shellcheck disable=SC2086
    timeout 120 "$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1920,1080 --virtual-time-budget=9000 \
        --user-data-dir="$HOME/chrome-$1" ${CHROME_EXTRA:-} --screenshot="$OUT/$1.png" "http://127.0.0.1:$PORT/?static=1&$2" >"$OUT/$1.log" 2>&1 || true
    test -s "$OUT/$1.png" || { echo "FAIL: no screenshot for $1 (see $OUT/$1.log)"; tail -5 "$OUT/$1.log"; exit 1; }
}
shot games-ar "lang=ar&select=0"
shot games-en "lang=en&select=1"
shot profile  "lang=ar&tab=profile"
"$PYTHON" "$HERE/check_png.py" "$OUT/games-ar.png" "$OUT/games-en.png" "$OUT/profile.png"
echo "ALL OK"
