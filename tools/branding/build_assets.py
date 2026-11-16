# Rebuilds every Darksham logo asset from the sword-free wordmark (tools/branding/darksham_wordmark.png).
# Run from the repo root: python3 tools/branding/build_assets.py
from PIL import Image
R = "system_files/usr/share"
B = f"{R}/darksham/branding"
SPL = f"{R}/plasma/look-and-feel/org.darksham.desktop/contents"
mark = Image.open("tools/branding/darksham_wordmark.png").convert("RGBA")

def sized(w):
    return mark.resize((w, round(mark.height * w / mark.width)), Image.LANCZOS)

# plain logos (transparent background)
sized(850).save(f"{B}/logo.png")
for s in (128, 256, 512):
    sized(s).save(f"{B}/logo-{s}.png")

# wallpaper / previews: wordmark centered on the Darksham dark gradient, same size as before (34% of width)
bg0 = Image.open(f"{SPL}/splash/images/background.png").convert("RGB")
def scene(w, h):
    bg = bg0.resize((w, h), Image.LANCZOS).convert("RGBA")
    m = sized(round(w * 0.34))
    bg.alpha_composite(m, ((w - m.width) // 2, (h - m.height) // 2))
    return bg.convert("RGB")
scene(1920, 1080).save(f"{R}/wallpapers/Darksham/contents/images/1920x1080.png")
scene(3840, 2160).save(f"{R}/wallpapers/Darksham/contents/images/3840x2160.png")
scene(400, 225).save(f"{R}/wallpapers/Darksham/contents/screenshot.png")
scene(640, 360).save(f"{SPL}/previews/preview.png")
scene(640, 360).save(f"{SPL}/previews/splash.png")
print("done")
