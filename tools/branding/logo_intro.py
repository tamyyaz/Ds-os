# Darksham logo intro: the DARKSHAM wordmark wipes in left->right, then settles with a soft pulse.
# Needs only numpy + Pillow. Writes PNG frames, then encode them:
# Run: python3 tools/branding/logo_intro.py system_files/usr/share/darksham/branding/logo.png frames 1920 1080
#      ffmpeg -framerate 30 -i frames/f%04d.png -c:v libx264 -pix_fmt yuv420p intro.mp4
import sys, os, numpy as np
from PIL import Image
# usage: python3 logo_intro.py LOGO.png OUT_DIR WIDTH HEIGHT
LOGO, OUT, W, H, FPS = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), 30
logo = Image.open(LOGO).convert("RGBA")
T, t_wipe0, t_wipe1, t_pulse = 4.0, 0.4, 1.9, 0.35
N = int(T * FPS)
bw = int(W * 0.34); bh = round(logo.height * bw / logo.width)

def ease_out(t): return 1 - (1 - t) ** 3

# background: near-black with a soft radial glow, same look as the wallpaper
yy, xx = np.mgrid[0:H, 0:W]
glow = np.exp(-(((xx - W / 2) / (W * 0.35)) ** 2 + ((yy - H * 0.5) / (H * 0.45)) ** 2))
bg = np.zeros((H, W, 3), np.float32); bg[:] = np.array([8, 8, 10]) / 255
bg += glow[..., None] * np.array([30, 30, 36]) / 255
bg = np.clip(bg, 0, 1)

os.makedirs(OUT, exist_ok=True)
for f in range(N):
    t = f / FPS
    p = ease_out(min(1, max(0, (t - t_wipe0) / (t_wipe1 - t_wipe0))))
    # soft pulse right after the wipe finishes
    k = t - t_wipe1
    s = 1 + (0.03 * np.sin(np.pi * k / t_pulse) if 0 <= k < t_pulse else 0)
    w, h = round(bw * s), round(bh * s)
    m = np.array(logo.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255
    a = m[..., 3]
    # left->right wipe with a soft edge
    lx = np.arange(w)[None, :]
    edge = p * (w + 80) - 40
    a = a * np.clip((edge - lx) / 40, 0, 1)
    c = (bg * 255).astype(np.uint8).astype(np.float32) / 255
    x0, y0 = (W - w) // 2, (H - h) // 2
    reg = c[y0:y0 + h, x0:x0 + w]
    c[y0:y0 + h, x0:x0 + w] = reg * (1 - a[..., None]) + a[..., None]
    Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).save(f"{OUT}/f{f:04d}.png")
print("frames", N)
