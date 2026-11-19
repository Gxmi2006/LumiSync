"""Screen images and synthesized sound effects / music bed for the 3D reel.

    python make_assets.py

Writes public/scenes/*.png and public/sfx/*.wav. Everything is generated here,
so there are no licensing questions about the audio.
"""

import os
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))  # marketing/, for make_reel's scene painters
import make_reel  # noqa: E402

SR = 44100
rng = np.random.default_rng(1)


def save_wav(name, x):
    x = np.clip(x, -1, 1)
    st = np.stack([x, x], 1) if x.ndim == 1 else x
    path = os.path.join(ROOT, "public", "sfx", name)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def t_(sec):
    return np.arange(int(SR * sec)) / SR


def lowpass(x, a):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def sweep_filter(x, a0, a1):
    a = np.linspace(a0, a1, len(x))
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def whoosh(sec=0.7):
    t = t_(sec)
    n = rng.standard_normal(len(t))
    env = np.sin(np.pi * np.clip(t / sec, 0, 1)) ** 2
    y = sweep_filter(n, 0.02, 0.35) * env
    return y / np.abs(y).max() * 0.7


def impact(sec=1.4):
    t = t_(sec)
    f = 30 + 90 * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    crack = lowpass(rng.standard_normal(len(t)), 0.25) * np.exp(-t * 22)
    y = body * 0.9 + crack * 0.6
    return y / np.abs(y).max() * 0.9


def riser(sec=1.3):
    t = t_(sec)
    n = sweep_filter(rng.standard_normal(len(t)), 0.01, 0.5)
    f = 200 + 900 * (t / sec) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    env = (t / sec) ** 2
    y = (n * 0.8 + tone) * env
    return y / np.abs(y).max() * 0.6


def pop(sec=0.12):
    t = t_(sec)
    y = np.sin(2 * np.pi * (900 + 600 * np.exp(-t * 60)) * t) * np.exp(-t * 45)
    return y * 0.5


def shimmer(sec=1.6):
    t = t_(sec)
    y = np.zeros_like(t)
    for k, f in enumerate([1318.5, 1567.98, 1975.5, 2637.0]):
        d = 0.06 * k
        y += np.sin(2 * np.pi * f * t) * np.exp(-np.clip(t - d, 0, None) * 4) * (t > d)
    return y / np.abs(y).max() * 0.35


def music(sec, bpm=104):
    """Dark synth pad + soft four-on-the-floor kick, ducked a little on each beat."""
    t = t_(sec)
    beat = 60 / bpm
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 196.0, 261.63), (196.0, 246.94, 293.66)]
    pad = np.zeros_like(t)
    bar = beat * 4
    for i, ch in enumerate(chords * 8):
        s = i * bar
        if s >= sec:
            break
        m = (t >= s) & (t < s + bar + 0.3)
        tt = t[m] - s
        env = np.minimum(1, tt / 0.4) * np.minimum(1, np.clip(bar + 0.3 - tt, 0, None) / 0.4)
        for f in ch:
            for det in (-0.6, 0.6):
                pad[m] += np.sign(np.sin(2 * np.pi * (f + det) * tt)) * env * 0.05
    pad = lowpass(pad, 0.06)
    kick = np.zeros_like(t)
    kt = t_(0.35)
    k1 = np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-kt * 30)) / SR) * np.exp(-kt * 9)
    duck = np.ones_like(t)
    for b in np.arange(0, sec, beat):
        i = int(b * SR)
        j = min(len(t), i + len(k1))
        kick[i:j] += k1[: j - i]
        dj = min(len(t), i + int(0.25 * SR))
        duck[i:dj] = np.minimum(duck[i:dj], 0.45 + 0.55 * np.linspace(0, 1, dj - i))
    hat = np.zeros_like(t)
    ht = t_(0.05)
    h1 = rng.standard_normal(len(ht)) * np.exp(-ht * 90)
    h1 = h1 - lowpass(h1, 0.3)
    for b in np.arange(beat / 2, sec, beat):
        i = int(b * SR)
        j = min(len(t), i + len(h1))
        hat[i:j] += h1[: j - i] * 0.25
    y = pad * duck + kick * 0.55 + hat
    fade = np.minimum(1, t / 1.0) * np.minimum(1, (sec - t) / 1.5)
    return y / np.abs(y).max() * 0.8 * fade


def main():
    os.makedirs(os.path.join(ROOT, "public", "scenes"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "public", "sfx"), exist_ok=True)
    names = ["ring", "sunset", "night", "city", "fire"]
    for name, (_, fn, _) in zip(names, make_reel.SCENES):
        fn().save(os.path.join(ROOT, "public", "scenes", name + ".png"))
    # Sound effects and music now come from ElevenLabs (tools/sfx.mjs). The synth versions
    # below are kept as an offline fallback: pass --synth-audio to write them.
    if "--synth-audio" in sys.argv:
        for name, fn in [("whoosh", whoosh), ("impact", impact), ("riser", riser), ("pop", pop), ("shimmer", shimmer)]:
            save_wav(name + ".wav", fn())
        save_wav("music.wav", music(40))
    print("assets written")


if __name__ == "__main__":
    main()
