"""Checks that a screenshot is a real render: right size and not one flat colour."""
import sys

from PIL import Image


def main(path):
    img = Image.open(path).convert("RGB")
    ok = True
    if img.size != (1920, 1080):
        print("FAIL %s: size %s, expected 1920x1080" % (path, img.size))
        ok = False
    colours = img.resize((192, 108)).getcolors(maxcolors=200000) or []
    if len(colours) < 300:
        print("FAIL %s: only %d distinct colours, the page probably did not render" % (path, len(colours)))
        ok = False
    px = list(img.resize((64, 36)).getdata())
    bright = sum(sum(p) for p in px) / (3 * len(px))
    if bright < 6:
        print("FAIL %s: the picture is almost black (%.1f)" % (path, bright))
        ok = False
    if ok:
        print("OK   %s: %dx%d, %d colours, brightness %.0f" % (path, img.size[0], img.size[1], len(colours), bright))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(max(main(p) for p in sys.argv[1:]))
