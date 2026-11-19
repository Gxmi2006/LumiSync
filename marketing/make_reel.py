"""Render a 30 second vertical promo reel for LumiSync (1080x1920, 30 fps).

Usage:
    python make_reel.py                 # full render -> lumisync-reel.mp4
    python make_reel.py --preview 2 5 9 # save PNG stills at those seconds

Needs: numpy, pillow, imageio-ffmpeg.
"""

import argparse
import colorsys
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DURATION = 30.0
HERE = os.path.dirname(os.path.abspath(__file__))

FONT_DIR = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


F_BLACK = lambda s: font("seguibl.ttf", s)
F_BOLD = lambda s: font("segoeuib.ttf", s)
F_SEMI = lambda s: font("seguisb.ttf", s)
F_REG = lambda s: font("segoeui.ttf", s)
F_MONO = lambda s: font("consolab.ttf", s)

BG = (7, 8, 12)
WHITE = (240, 242, 247)
MUTED = (150, 156, 170)

# ---------------------------------------------------------------- layout
SCR_X0, SCR_Y0, SCR_X1, SCR_Y1 = 90, 560, 990, 1100  # outer bezel
BEZ = 16
SX0, SY0, SX1, SY1 = SCR_X0 + BEZ, SCR_Y0 + BEZ, SCR_X1 - BEZ, SCR_Y1 - BEZ
SW, SH = SX1 - SX0, SY1 - SY0
DECK = (50, 1112, 1030, 1470)
KEYS = (92, 1146, 988, 1436)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def window(t, a, b, fade=0.35):
    """1 inside [a,b], easing in/out over `fade` seconds."""
    if t < a or t > b:
        return 0.0
    return min(ease((t - a) / fade), ease((b - t) / fade))


# ---------------------------------------------------------------- scenes
def grid():
    y, x = np.mgrid[0:SH, 0:SW].astype(np.float32)
    return x / SW, y / SH, x, y


def lerp3(c0, c1, t):
    c0, c1 = np.array(c0, np.float32), np.array(c1, np.float32)
    return c0 + (c1 - c0) * t[..., None]


def finish(img):
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def scene_ring():
    u, v, x, y = grid()
    img = lerp3((6, 10, 28), (14, 8, 30), v)
    cx, cy = SW * 0.5, SH * 0.5
    d = np.hypot(x - cx, y - cy)
    r0 = 165
    core = np.exp(-((d - r0) / 7.0) ** 2)
    glow = np.exp(-((d - r0) / 45.0) ** 2) * 0.55
    halo = np.exp(-((d - r0) / 120.0) ** 2) * 0.18
    green = np.array((60, 255, 150), np.float32)
    img += (core[..., None] * 255 * np.array((0.75, 1, 0.85))) + (glow + halo)[..., None] * green
    rng = np.random.default_rng(3)
    for _ in range(70):
        px, py = rng.uniform(0, SW), rng.uniform(0, SH)
        s = np.exp(-(((x - px) ** 2 + (y - py) ** 2) / 6.0))
        img += s[..., None] * np.array((120, 90, 255)) * rng.uniform(0.3, 0.9)
    return finish(img)


def scene_sunset():
    u, v, x, y = grid()
    top = lerp3((40, 18, 90), (230, 90, 70), np.clip(v / 0.55, 0, 1))
    img = np.where((v < 0.55)[..., None], top, lerp3((230, 90, 70), (255, 180, 90), np.clip((v - 0.55) / 0.12, 0, 1)))
    sx, sy = SW * 0.5, SH * 0.6
    d = np.hypot(x - sx, y - sy)
    img += (np.exp(-(d / 260.0) ** 2) * 0.6)[..., None] * np.array((255, 150, 70))
    sun = d < 95
    img[sun] = img[sun] * 0.15 + np.array((255, 215, 140)) * 0.85
    hills = SH * (0.68 + 0.05 * np.sin(u * 7.0) + 0.03 * np.sin(u * 17.0 + 1))
    land = y > hills
    img[land] = lerp3((40, 14, 30), (16, 6, 16), np.clip((v[land] - 0.68) / 0.32, 0, 1))
    return finish(img)


def scene_night():
    u, v, x, y = grid()
    img = lerp3((12, 6, 40), (110, 36, 130), v)
    mx, my = SW * 0.68, SH * 0.36
    d = np.hypot(x - mx, y - my)
    img += (np.exp(-(d / 200.0) ** 2) * 0.7)[..., None] * np.array((255, 110, 200))
    moon = d < 92
    img[moon] = np.array((255, 190, 225))
    rng = np.random.default_rng(7)
    for _ in range(90):
        px, py = int(rng.uniform(0, SW)), int(rng.uniform(0, SH * 0.6))
        img[max(py - 1, 0):py + 2, max(px - 1, 0):px + 2] = (255, 240, 255)
    # rooftops silhouette
    roof = np.full(SW, SH * 0.8, np.float32)
    for bx in range(0, SW, 70):
        h = rng.uniform(0.62, 0.85) * SH
        roof[bx:bx + 70] = h
    img[y > roof[None, :].repeat(SH, 0)] = (14, 6, 22)
    return finish(img)


def scene_city():
    u, v, x, y = grid()
    img = lerp3((4, 12, 24), (6, 30, 46), v)
    rng = np.random.default_rng(11)
    pil = finish(img)
    d = ImageDraw.Draw(pil)
    bx = 0
    while bx < SW:
        bw = int(rng.uniform(60, 130))
        top = int(rng.uniform(0.25, 0.6) * SH)
        d.rectangle((bx, top, bx + bw - 6, SH), fill=(8, 16, 26))
        for wy in range(top + 14, SH - 10, 22):
            for wx in range(bx + 10, bx + bw - 16, 18):
                if rng.random() < 0.55:
                    c = (40, 220, 255) if rng.random() < 0.8 else (255, 80, 200)
                    d.rectangle((wx, wy, wx + 8, wy + 10), fill=c)
        bx += bw
    d.rounded_rectangle((SW * 0.28, SH * 0.18, SW * 0.72, SH * 0.3), 14, outline=(60, 230, 255), width=6)
    f = F_BLACK(46)
    tw = d.textlength("NIGHT  LIVE", font=f)
    d.text(((SW - tw) / 2, SH * 0.24 - 30), "NIGHT  LIVE", font=f, fill=(90, 235, 255))
    glow = pil.filter(ImageFilter.GaussianBlur(14))
    return ImageChops.add(pil, glow)


def scene_fire():
    u, v, x, y = grid()
    img = lerp3((10, 4, 4), (30, 6, 4), v)
    rng = np.random.default_rng(5)
    for _ in range(26):
        px, py = rng.uniform(0.1, 0.9) * SW, rng.uniform(0.45, 1.05) * SH
        r = rng.uniform(40, 120)
        s = np.exp(-(((x - px) ** 2 + ((y - py) * 0.6) ** 2) / (r * r)))
        img += s[..., None] * np.array((255, 70 + rng.uniform(0, 60), 30)) * 0.9
    return finish(img)


# label, picked colour, hex shown
SCENES = [
    ("GAME", scene_ring, (60, 255, 150)),
    ("MOVIE", scene_sunset, (255, 128, 48)),
    ("ANIME", scene_night, (230, 90, 200)),
    ("YOUTUBE", scene_city, (34, 204, 255)),
    ("GAME", scene_fire, (255, 64, 40)),
]

# when each scene is on screen: (start_time, scene_index)
SCHEDULE = [
    (0.0, 0), (6.4, 1), (8.8, 2), (11.2, 3), (13.6, 4),
    (16.0, 0), (18.2, 2), (20.4, 1), (22.6, 3), (24.6, 0),
]
XFADE = 0.45


def scene_at(t):
    """(index_a, index_b, mix) for crossfading."""
    for i in range(len(SCHEDULE) - 1, -1, -1):
        st, idx = SCHEDULE[i]
        if t >= st:
            if i > 0 and t - st < XFADE:
                return SCHEDULE[i - 1][1], idx, ease((t - st) / XFADE), st
            return idx, idx, 1.0, st
    return 0, 0, 1.0, 0.0


def target_color(t):
    if t < 3.4:
        return (225, 230, 240), 0.55  # plain static white backlight
    a, b, m, st = scene_at(t - 0.25)  # colour lags the picture a little, like real capture
    return SCENES[b][2], 1.0


# ---------------------------------------------------------------- static layers
def rr_mask(box, r, size=(W, H)):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, r, fill=255)
    return m


def build_static():
    s = {}
    base = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(base)
    # laptop deck + hinge
    d.rounded_rectangle(DECK, 38, fill=(20, 22, 28))
    d.rounded_rectangle((DECK[0], DECK[1], DECK[2], DECK[1] + 8), 4, fill=(32, 35, 44))
    # trackpad hint
    d.rounded_rectangle((430, 1442, 650, 1462), 8, fill=(26, 28, 35))
    # screen bezel
    d.rounded_rectangle((SCR_X0, SCR_Y0, SCR_X1, SCR_Y1), 30, fill=(14, 15, 19), outline=(40, 43, 52), width=2)
    s["base"] = base
    s["screen_mask"] = rr_mask((0, 0, SW - 1, SH - 1), 18, (SW, SH))

    keys = Image.new("L", (W, H), 0)
    kd = ImageDraw.Draw(keys)
    kx0, ky0, kx1, ky1 = KEYS
    rows, gap = 6, 9
    kh = (ky1 - ky0 - gap * (rows - 1)) / rows
    layouts = [
        [1] * 15,
        [1] * 14 + [1],
        [1.5] + [1] * 12 + [1.5],
        [1.8] + [1] * 11 + [2.2],
        [2.3] + [1] * 10 + [2.7],
        [1.2, 1, 1.2, 6.4, 1.2, 1, 1, 1],
    ]
    for r, lay in enumerate(layouts):
        units = sum(lay)
        unit = (kx1 - kx0 - gap * (len(lay) - 1)) / units
        x = kx0
        y = ky0 + r * (kh + gap)
        for w in lay:
            kd.rounded_rectangle((x, y, x + w * unit, y + kh), 9, fill=255)
            x += w * unit + gap
    s["keys"] = keys
    s["key_glow"] = keys.filter(ImageFilter.GaussianBlur(16))
    s["key_rim"] = ImageChops.subtract(keys, keys.filter(ImageFilter.MinFilter(5)))

    # ambient light spilling around the laptop
    amb = Image.new("L", (W, H), 0)
    ImageDraw.Draw(amb).ellipse((-120, 1000, W + 120, 1640), fill=200)
    s["ambient"] = amb.filter(ImageFilter.GaussianBlur(140))

    print("building scenes...", flush=True)
    s["scenes"] = [fn() for _, fn, _ in SCENES]
    return s


# ---------------------------------------------------------------- drawing helpers
def solid(c):
    return Image.new("RGB", (W, H), tuple(int(v) for v in c))


def add_light(canvas, mask, color, strength):
    if strength <= 0.003:
        return canvas
    m = mask.point(lambda p: int(p * min(strength, 1.0)))
    return Image.composite(solid(color), canvas, m)


def screen_light(canvas, mask, color, strength):
    """Additive glow."""
    if strength <= 0.003:
        return canvas
    layer = Image.composite(solid(color), Image.new("RGB", (W, H), 0), mask.point(lambda p: int(p * min(strength, 1.0))))
    return ImageChops.add(canvas, layer)


def text_layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def draw_center(layer, text, y, fnt, color, alpha, rise=0.0, spacing=10):
    if alpha <= 0.01:
        return
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    box = d.multiline_textbbox((0, 0), text, font=fnt, align="center", spacing=spacing)
    tw = box[2] - box[0]
    d.multiline_text(((W - tw) / 2 - box[0], y + rise * 26), text, font=fnt, fill=color + (int(255 * alpha),),
                     align="center", spacing=spacing)
    layer.alpha_composite(tmp)


def gradient_text(layer, text, y, fnt, c0, c1, alpha, glow_color=None):
    if alpha <= 0.01:
        return
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    box = d.textbbox((0, 0), text, font=fnt)
    tw = box[2] - box[0]
    x0 = (W - tw) / 2 - box[0]
    d.text((x0, y), text, font=fnt, fill=255)
    grad = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
    g = (np.array(c0, np.float32) * (1 - grad) + np.array(c1, np.float32) * grad)
    g = np.repeat(g, H, 0)
    rgba = np.dstack([g, np.array(m, np.float32) * alpha]).astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    if glow_color:
        gm = m.filter(ImageFilter.GaussianBlur(28)).point(lambda p: int(p * 0.8 * alpha))
        glow = Image.new("RGBA", (W, H), glow_color + (0,))
        glow.putalpha(gm)
        layer.alpha_composite(glow)
    layer.alpha_composite(img)


def lighten(c, k):
    return tuple(int(v + (255 - v) * k) for v in c)


def star(d, cx, cy, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


# ---------------------------------------------------------------- text script
HOOK = [
    (0.15, 3.3, "Your screen is putting on a show.", 30),
    (1.35, 3.3, "Your RGB keyboard is just\nsitting there in plain white.", 140),
]
DEMO_HEAD = [
    (6.4, 10.4, "Games, movies, anime, YouTube.\nYour lights follow all of it."),
    (10.6, 15.7, "It picks the best colour on screen\ninstead of a muddy average."),
]
FEATURES = [
    (15.9, 18.1, "Works with OpenRGB", "Keyboards, mice, RAM, LED strips and laptops"),
    (18.1, 20.3, "Light on your PC", "Low overhead, lives quietly in the tray"),
    (20.3, 22.5, "Smooth, never flashy", "One calm cinematic colour, no flicker"),
    (22.5, 24.6, "Free and open source", "MIT licensed and written in Python"),
]


def render(t, st, state):
    # ----- smoothed keyboard colour (mimics LumiSync's smoothing)
    # smoothed in HSV so transitions sweep through hues instead of going grey
    tc, ti = target_color(t)
    k = 0.22
    th, ts, tv = colorsys.rgb_to_hsv(*(c / 255 for c in tc))
    h, s, v = state["hsv"]
    if ts < 0.15:
        th = h  # white has no real hue; keep the current one
    if s < 0.15 and ts >= 0.15:
        h = th  # leaving white: start from the target hue
    dh = (th - h + 0.5) % 1.0 - 0.5
    state["hsv"] = ((h + dh * k) % 1.0, s + (ts - s) * k, v + (tv - v) * k)
    state["i"] += (ti - state["i"]) * k
    col = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(*state["hsv"]))
    inten = state["i"]

    cta = ease((t - 24.8) / 0.8)  # 0..1 into the call to action
    dim = 1.0 - 0.72 * cta

    canvas = st["base"].copy()
    canvas = screen_light(canvas, st["ambient"], col, 0.42 * inten * dim)

    # ----- screen content
    a, b, m, sched_t = scene_at(t)
    zoom = 1.0 + 0.03 * ((t - sched_t) / 2.4)
    def frame_of(idx):
        img = st["scenes"][idx]
        zw, zh = int(SW * zoom), int(SH * zoom)
        img = img.resize((zw, zh), Image.BILINEAR)
        ox, oy = (zw - SW) // 2, (zh - SH) // 2
        return img.crop((ox, oy, ox + SW, oy + SH))
    scr = frame_of(b)
    if m < 1.0 and a != b:
        scr = Image.blend(frame_of(a), scr, m)
    if dim < 1:
        scr = Image.blend(Image.new("RGB", (SW, SH), 0), scr, dim)
    canvas.paste(scr, (SX0, SY0), st["screen_mask"])

    sd = ImageDraw.Draw(canvas)
    # debug-overlay style focal box on the neon ring
    fb = window(t, 4.0, 6.25, 0.3) * (1 if b == 0 else 0)
    if fb > 0:
        c = tuple(int(v * fb + 30 * (1 - fb)) for v in (60, 255, 150))
        cx, cy = SX0 + SW // 2, SY0 + SH // 2
        sd.rectangle((cx - 205, cy - 205, cx + 205, cy + 205), outline=c, width=3)
        sd.rectangle((cx - 205, cy - 245, cx + 60, cy - 207), fill=(10, 30, 20))
        sd.text((cx - 196, cy - 243), "focal: ring  0.91", font=F_MONO(26), fill=c)

    # scene label chip in the screen corner
    lab_a = (1 - cta) * (1.0 if t > 6.3 else 0.0)
    if lab_a > 0:
        label = SCENES[b if m > 0.5 else a][0]
        f = F_SEMI(26)
        tw = sd.textlength(label, font=f)
        sd.rounded_rectangle((SX0 + 22, SY0 + 22, SX0 + 22 + tw + 36, SY0 + 66), 20, fill=(0, 0, 0))
        sd.text((SX0 + 40, SY0 + 26), label, font=f, fill=(225, 228, 236))

    # ----- keyboard
    canvas = screen_light(canvas, st["key_glow"], col, 0.95 * inten * dim)
    cap = tuple(int(18 + v * 0.10 * inten * dim) for v in col)
    canvas = Image.composite(solid(cap), canvas, st["keys"])
    canvas = screen_light(canvas, st["key_rim"], lighten(col, 0.25), 1.0 * inten * dim)

    # the laptop fades away for the call to action, leaving only the coloured ambient light
    if cta > 0:
        bg = screen_light(Image.new("RGB", (W, H), BG), st["ambient"], col, 0.5 * inten)
        canvas = Image.blend(canvas, bg, cta * 0.92)

    # ----- text
    tl = text_layer()
    for a0, a1, txt, y_off in HOOK:
        al = window(t, a0, a1, 0.35)
        rise = 1 - ease((t - a0) / 0.4)
        draw_center(tl, txt, 210 + y_off, F_BOLD(58), WHITE, al, rise)

    # "LumiSync makes it follow along."
    al = window(t, 3.5, 6.25, 0.35)
    if al > 0:
        gradient_text(tl, "LumiSync", 190, F_BLACK(150), lighten(col, 0.55), col, al, glow_color=col)
        draw_center(tl, "makes it follow along.", 400, F_SEMI(54), WHITE, al, 1 - ease((t - 3.7) / 0.4))

    for a0, a1, txt in DEMO_HEAD:
        al = window(t, a0, a1, 0.35)
        draw_center(tl, txt, 270, F_BOLD(56), WHITE, al, 1 - ease((t - a0) / 0.4))

    for a0, a1, head, sub in FEATURES:
        al = window(t, a0, a1, 0.3)
        rise = 1 - ease((t - a0) / 0.35)
        draw_center(tl, head, 250, F_BLACK(76), WHITE, al, rise)
        draw_center(tl, sub, 370, F_SEMI(40), MUTED, al, rise)

    # colour swatch under the laptop: what gets sent to OpenRGB
    sw_a = window(t, 3.7, 24.7, 0.4)
    if sw_a > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        hexs = "#%02X%02X%02X" % col
        pill = (300, 1512, 780, 1586)
        d.rounded_rectangle(pill, 37, fill=(20, 22, 28, 235), outline=(46, 50, 60, 255), width=2)
        d.ellipse((318, 1527, 362, 1571), fill=col + (255,))
        d.text((380, 1527), hexs, font=F_MONO(34), fill=WHITE + (255,))
        d.text((548, 1532), "to OpenRGB", font=F_SEMI(30), fill=MUTED + (255,))
        lay.putalpha(lay.getchannel("A").point(lambda p: int(p * sw_a)))
        tl.alpha_composite(lay)

    # ----- call to action
    if cta > 0:
        rise = 1 - cta
        gradient_text(tl, "LumiSync", 600 + rise * 30, F_BLACK(190), lighten(col, 0.6), col, cta, glow_color=col)
        draw_center(tl, "Ambient RGB sync, without the bloat.", 860, F_SEMI(50), WHITE, cta, rise)
        a2 = ease((t - 25.6) / 0.7)
        if a2 > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            d.rounded_rectangle((110, 1020, 970, 1130), 55, fill=(255, 255, 255, 255))
            url = "github.com/Gxmi2006/LumiSync"
            f = F_MONO(44)
            tw = d.textlength(url, font=f)
            d.text(((W - tw) / 2, 1048), url, font=f, fill=(10, 12, 18, 255))
            lay.putalpha(lay.getchannel("A").point(lambda p: int(p * a2)))
            tl.alpha_composite(lay)
        a3 = ease((t - 26.4) / 0.7)
        if a3 > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            msg = "Free download. Give it a star"
            f = F_BOLD(50)
            tw = d.textlength(msg, font=f)
            x0 = (W - tw - 60) / 2
            d.text((x0, 1185), msg, font=f, fill=WHITE + (255,))
            star(d, x0 + tw + 38, 1219, 26, (255, 205, 60, 255))
            f2 = F_SEMI(42)
            m2 = "Link in bio"
            d.text(((W - d.textlength(m2, font=f2)) / 2, 1280), m2, font=f2, fill=MUTED + (255,))
            lay.putalpha(lay.getchannel("A").point(lambda p: int(p * a3)))
            tl.alpha_composite(lay)

    # fade from black at the very start and to black at the very end
    out = Image.alpha_composite(canvas.convert("RGBA"), tl).convert("RGB")
    edge = min(ease(t / 0.3), ease((DURATION - t) / 0.5))
    if edge < 1:
        out = Image.blend(Image.new("RGB", (W, H), BG), out, edge)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", nargs="*", type=float)
    ap.add_argument("--out", default=os.path.join(HERE, "lumisync-reel.mp4"))
    args = ap.parse_args()

    st = build_static()
    state = {"hsv": colorsys.rgb_to_hsv(225 / 255, 230 / 255, 240 / 255), "i": 0.55}
    n = int(DURATION * FPS)

    if args.preview is not None:
        wanted = {int(s * FPS) for s in args.preview}
        last = max(wanted)
        for f in range(last + 1):
            img = render(f / FPS, st, state)
            if f in wanted:
                p = os.path.join(HERE, "preview_%05.2fs.png" % (f / FPS))
                img.resize((540, 960), Image.LANCZOS).save(p)
                print("saved", p, flush=True)
        return

    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-map", "0:v", "-map", "1:a", "-shortest",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(n):
        proc.stdin.write(render(f / FPS, st, state).tobytes())
        if f % 60 == 0:
            print(f"frame {f}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("done:", args.out)


if __name__ == "__main__":
    main()
