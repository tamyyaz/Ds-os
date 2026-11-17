#!/bin/bash
# Stand-in for Chromium in tests: checks what darksham-launcher gave it, then exits like a closed window.
# Writes the URL it was given to $FAKE_URL_OUT and exits 1 if anything is wrong.
url=""
for a in "$@"; do case "$a" in --app=*) url="${a#--app=}" ;; esac; done
echo "fake browser args: $*"
[ -n "$url" ] || { echo "no --app= URL given"; exit 1; }
code="$(curl -s -o /dev/null -w '%{http_code}' "$url")"
echo "index status: $code"
[ "$code" = 200 ] || exit 1
n="$(curl -s "${url}api/library" | "${PYTHON:-python3}" -c 'import sys,json; print(len(json.load(sys.stdin)["games"]))')"
echo "games from the API: $n"
[ "$n" = 5 ] || exit 1
echo "$url" > "${FAKE_URL_OUT:?}"
