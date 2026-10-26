# Darksham logo intro: text wipes in left->right, sword drops, metal shine.
# Run: python3 tools/branding/logo_intro.py system_files/usr/share/darksham/branding/logo.png frames 1920 1080
#      ffmpeg -framerate 30 -i frames/f%04d.png -c:v libx264 -pix_fmt yuv420p intro.mp4
import sys, os, numpy as np
from PIL import Image
from scipy import ndimage as nd
# usage: python3 logo_intro.py LOGO.png OUT_DIR WIDTH HEIGHT
LOGO, OUT, W, H, FPS = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), 30
a = np.array(Image.open(LOGO))[...,3].astype(np.float32)/255
lh, lw = a.shape
B0, B1 = 352, 505                      # text band rows
solid = a > 0.5
thick = nd.binary_opening(solid, structure=np.ones((9,9))); thick[:B0]=False; thick[B1:]=False
text_m = nd.binary_dilation(thick, iterations=3)
sword = a*(~text_m); sword[B0:B1] = 0
lab,n = nd.label(sword>0.1); sz = nd.sum(np.ones_like(lab), lab, range(1,n+1))
keep = np.r_[False, sz>40]; sword = sword*keep[lab]
# blade through the band: continue the blade rows just above it
ref = sword[B0-24:B0].max(0)
cols = np.where(ref>0.2)[0]; c0, c1 = cols.min()-2, cols.max()+3
sword[B0:B1, c0:c1] = ref[c0:c1]
text = a.copy(); text[:B0]=0; text[B1:]=0; text[B0:B1, c0:c1] *= text_m[B0:B1, c0:c1]
full = a
# scale layers to canvas
S = (H*0.55)/lh; nw, nh = int(lw*S), int(lh*S)
def rs(m): return np.array(Image.fromarray((m*255).astype(np.uint8)).resize((nw,nh), Image.LANCZOS)).astype(np.float32)/255
text, sword, full = rs(text), rs(sword), rs(full)
ox, oy = (W-nw)//2, (H-nh)//2
bg = np.zeros((H,W,3),np.float32); bg[:] = np.array([8,8,10])/255
yy, xx = np.mgrid[0:H,0:W]
glow = np.exp(-(((xx-W/2)/(W*0.35))**2+((yy-H*0.5)/(H*0.45))**2))
bg += glow[...,None]*np.array([30,30,36])/255
def ease_out(t): return 1-(1-t)**3
def ease_in(t): return t*t*t
def put(canvas, m, dx=0, dy=0, color=(1,1,1)):
    x0, y0 = ox+dx, oy+dy
    sx0, sy0 = max(0,-x0), max(0,-y0); x0c, y0c = max(0,x0), max(0,y0)
    x1c, y1c = min(W, x0+nw), min(H, y0+nh)
    if x1c<=x0c or y1c<=y0c: return
    sub = m[sy0:sy0+(y1c-y0c), sx0:sx0+(x1c-x0c)][...,None]
    reg = canvas[y0c:y1c, x0c:x1c]
    canvas[y0c:y1c, x0c:x1c] = reg*(1-sub) + np.array(color)*sub
T = 6.5; N = int(T*FPS)
t_text0, t_text1, t_drop1, t_shine0, t_shine1 = 0.4, 2.1, 2.85, 3.2, 4.8
os.makedirs(OUT, exist_ok=True)
lx = np.arange(nw)[None,:]
for f in range(N):
    t = f/FPS; c = bg.copy(); shake = 0
    # 1) text wipe left->right with soft edge
    if t >= t_text0:
        p = ease_out(min(1,(t-t_text0)/(t_text1-t_text0)))
        edge = p*(nw+120)-60
        wipe = np.clip((edge - lx)/60, 0, 1)
        if t < t_drop1: put(c, text*wipe)
    # 2) sword drop (accelerating), smeared while moving
    if t_text1 <= t < t_drop1:
        p = ease_in((t-t_text1)/(t_drop1-t_text1))
        dy = int(-(oy+nh)*(1-p))
        smear = nd.uniform_filter1d(sword, size=max(1,int(40*p)), axis=0) if p>0.15 else sword
        put(c, smear, dy=dy)
    # 3) landing: full logo, small shake, flash
    if t >= t_drop1:
        k = (t-t_drop1)*FPS
        shake = int(6*np.exp(-k/2.5)*np.sin(k*2.2)) if k<10 else 0
        put(c, full, dy=shake)
        flash = max(0, 1-(t-t_drop1)/0.18)
        if flash>0: put(c, sword*flash*0.9, dy=shake, color=(1,1,1))
        # 4) metal shine: diagonal light band sliding down the sword
        if t_shine0 <= t < t_shine1:
            p = (t-t_shine0)/(t_shine1-t_shine0)
            ys, xs = np.mgrid[0:nh,0:nw]
            pos = p*(nh*1.4) - nh*0.2
            d = (ys + (xs-nw/2)*0.6) - pos
            band = np.exp(-(d/(nh*0.08))**2)
            shine = np.clip(sword*1.6,0,1)*band
            glint = np.exp(-(d/(nh*0.018))**2)*np.clip(sword*2,0,1)
            y0 = oy+shake
            reg = c[y0:y0+nh, ox:ox+nw]
            reg += (shine*1.1)[...,None]*np.array([0.75,0.82,1.0]) + (glint*1.4)[...,None]
            # soft bloom around the band
            bloom = nd.gaussian_filter(shine, 9)*2.2
            reg += bloom[...,None]*np.array([0.6,0.7,0.9])
            c[y0:y0+nh, ox:ox+nw] = np.clip(reg,0,1)
    Image.fromarray((np.clip(c,0,1)*255).astype(np.uint8)).save(f"{OUT}/f{f:04d}.png")
print("frames", N)
