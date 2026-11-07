#!/usr/bin/env python3
"""Generate every sound effect of Tommy's Dino Kart into game/assets/sfx/*.ogg.

All procedural (see synth.py), no samples. Friendly cartoon tone for kids:
round thumps, boings and bells, nothing harsh or violent. Mono (most are
played positionally), short tails, peaks at -3 dBFS (UI ticks lower).

    python3 tools/audio/gen_sfx.py               # all
    python3 tools/audio/gen_sfx.py boost coin    # only these
    WAV=1 ...                                    # also dump WAVs to the scratch dir
"""
import os
import tempfile
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth import *  # noqa: E402,F401,F403
import synth as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'game', 'assets', 'sfx')
SCRATCH = os.environ.get('AUDIO_SCRATCH', os.path.join(tempfile.gettempdir(), 'tdk_audio'))
PEAK = -3.0

# ---------------------------------------------------------------- helpers
# (same toolbox as Tommy's Dino Zoo's gen_sfx.py)


class Mix:
    """Mono timeline: place signals at times (seconds)."""

    def __init__(self, length):
        self.x = np.zeros(ns(length))

    def at(self, t, sig, gain=1.0):
        s = ns(t)
        sig = np.asarray(sig, float)
        if sig.ndim == 2:
            sig = sig.mean(0)
        if s + len(sig) > len(self.x):
            self.x = np.concatenate([self.x, np.zeros(s + len(sig) - len(self.x))])
        self.x[s:s + len(sig)] += sig * gain
        return self

    def out(self):
        return self.x


def room(x, wet=0.15, size=0.5, damp=0.45, tail=0.6):
    x = np.concatenate([x, np.zeros(ns(tail))])
    r = reverb(x, room=size, damp=damp, predelay=0.012).mean(0)
    return x + r * wet * 6


def glide(f0, f1, dur, curve=3.0):
    """Exponential-ish pitch glide array from f0 to f1."""
    n = ns(dur)
    u = np.linspace(0, 1, n)
    k = (1 - np.exp(-curve * u)) / (1 - np.exp(-curve)) if curve else u
    return f0 * (f1 / f0) ** k


def blip(f0, f1, dur, tau=None, a=0.003, harm=0.15, curve=3.0):
    f = glide(f0, f1, dur, curve)
    n = len(f)
    c = 2 * np.pi * cycles(f, n)
    x = np.sin(c) + harm * np.sin(2 * c) + harm * 0.3 * np.sin(3 * c)
    env = perc(n, a, tau if tau else dur / 3)
    return fade(x * env, 0, 0.004)


def tone(f, n, harm=(1.0, 0.0, 0.0)):
    """Few-harmonic tone for a per-sample frequency array or a constant."""
    c = 2 * np.pi * cycles(f, n)
    return sum(a * np.sin((k + 1) * c) for k, a in enumerate(harm) if a)


def thump(f=110, dur=0.25, tau=0.06, drop=1.6, nz=0.5, nzf=500):
    n = ns(dur)
    t = tvec(n)
    f_ = f * (1 + (drop - 1) * np.exp(-t / 0.02))
    x = np.sin(2 * np.pi * cycles(f_, n)) * perc(n, 0.002, tau)
    x += lowpass(noise(n) * perc(n, 0.001, tau * 0.5), nzf) * nz * 2
    return fade(x, 0, 0.01)


def wood(f, dur=0.25, taus=(0.06, 0.025, 0.012), amps=(1, 0.45, 0.18), ratios=(1, 2.32, 4.1)):
    return modal(f, dur, ratios, amps, taus, attack=0.0006)


SPARK_PC = [0, 2, 4, 7, 9]  # pentatonic


def sparkle(count=4, lo=84, hi=100, spread=0.25, vel=0.5, up=False, inst=glock):
    """A few high pentatonic pings. lo/hi are MIDI notes."""
    pool = [m for m in range(lo, hi + 1) if m % 12 in SPARK_PC]
    picks = sorted(S.rng().choice(pool, count)) if up else S.rng().choice(pool, count)
    mx = Mix(spread + 2.5)
    for i, m in enumerate(picks):
        t = (i / max(count - 1, 1)) * spread if up else S.rng().uniform(0, spread)
        mx.at(t, inst(hz(int(m)), vel * S.rng().uniform(0.6, 1.0)))
    return mx.out()


def grains(dur, count, flo, fhi, glen=(0.003, 0.009), env=None, q=2.0):
    """Granular texture: short band-passed noise bursts at random times."""
    mx = Mix(dur + 0.05)
    for _ in range(count):
        t = S.rng().uniform(0, dur) if env is None else env()
        n = ns(S.rng().uniform(*glen))
        g = bandpass(noise(n + 64), S.rng().uniform(flo, fhi), q)[:n] * np.hanning(n)
        mx.at(t, g, S.rng().uniform(0.4, 1.0))
    return mx.out()


def swish(dur, f0, f1, q=1.2, shape=1.0):
    n = ns(dur)
    u = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** u
    x = bandpass(noise(n), f, q)
    env = np.sin(np.pi * u ** shape) ** 2
    return x * env


def finish(x, peak_db=PEAK, trim_db=-42, fout=None, maxlen=2.0, squash=0.0):
    """Damp/trim the tail, fade, normalise. squash (dB) pushes short
    transient sounds into the look-ahead limiter so they read louder."""
    x = np.asarray(x, float)
    if squash:
        x = S.limit(normalize(x, 0.0) * undb(squash), 0.0, attack=0.002, release=0.06)
    if len(x) > ns(maxlen):
        # damp long ringing tails naturally instead of chopping them
        t = tvec(len(x))
        t0 = 0.45 * maxlen
        x = x * np.exp(-np.maximum(t - t0, 0) * 6.9 / (maxlen - t0))
        x = x[:ns(maxlen)]
    x = highpass(x, 40)
    a = np.abs(x)
    thr = a.max() * undb(trim_db)
    idx = np.nonzero(a > thr)[0]
    if len(idx):
        x = x[:min(len(x), idx[-1] + ns(0.02))]
    if fout is None:
        fout = min(0.45, 0.3 * len(x) / SR)
    x = fade(x, 0.0008, fout)
    return normalize(x, peak_db)


def crack(f, g=1.0):
    n = ns(0.05)
    b = bandpass(noise(n), f, 3.0) * perc(n, 0.0004, 0.005)
    tick = modal(f * 0.7, 0.05, [1, 1.7, 2.9], [1, 0.5, 0.25], [0.012, 0.007, 0.004], attack=0.0004)
    return (b * 1.2 + tick * 0.6) * g


def coin_ping(f, vel=0.7, dur=0.5):
    return modal(f, dur, [1, 2.37, 4.09, 5.9], [1, 0.45, 0.2, 0.08], [0.16, 0.08, 0.045, 0.03],
                 attack=0.0005) * vel


def boing(f=260, dur=0.32, wob=13, depth=0.07, tau=0.09):
    """Rubbery boing: pitch drops onto f and wobbles."""
    n = ns(dur)
    t = tvec(n)
    ff = f * (1 + 0.3 * np.exp(-t / 0.04) + depth * np.sin(2 * np.pi * wob * t) * np.exp(-t / 0.12))
    c = 2 * np.pi * cycles(ff, n)
    return np.sin(c) * perc(n, 0.003, tau) + 0.25 * np.sin(2 * c) * perc(n, 0.002, tau * 0.45)


def beep(f, dur, vel=1.0):
    """Clean countdown beep: sine + a little soft square."""
    n = ns(dur)
    x = wt(tbl('square', f, f * 3), f, n) * 0.5 + sine(f, n) * 0.7
    return x * adsr(n, 0.004, 0.06, 0.85, 0.07) * vel


# ---------------------------------------------------------------- items

def egg_crack():
    mx = Mix(1.2)
    for t, f, g in [(0, 2700, 0.6), (0.07, 2300, 0.8), (0.12, 3000, 0.9)]:
        mx.at(t, crack(f, g))
        mx.at(t + 0.01, crack(f * 1.25, g * 0.5))
    mx.at(0.16, blip(380, 900, 0.09, tau=0.035, harm=0.25), 0.8)
    mx.at(0.16, thump(150, 0.12, tau=0.03, nz=0.2), 0.35)
    mx.at(0.22, sparkle(3, 88, 100, 0.15, 0.4, up=True))
    return finish(room(lowpass(mx.out(), 9000), 0.1, tail=0.4), maxlen=1.0)


def item_get():
    """Roulette slowing down (ticks) and stopping on a bright ding."""
    mx = Mix(1.2)
    for i, t in enumerate([0, 0.05, 0.11, 0.18]):
        mx.at(t, wood(1700 + i * 60, 0.06, taus=(0.012, 0.006, 0.003)), 0.35)
    for i, m in enumerate(['E6', 'G6', 'C7']):
        mx.at(0.24 + i * 0.045, glock(hz(m), 0.6))
    mx.at(0.33, fm_bell(hz('C6'), 0.6, ratio=2.0, index=0.9, tau=0.55), 0.6)
    mx.at(0.33, fm_bell(hz('G6'), 0.4, ratio=2.0, index=0.7, tau=0.45), 0.4)
    mx.at(0.36, sparkle(3, 96, 103, 0.2, 0.25))
    return finish(room(lowpass(mx.out(), 10000), 0.12, tail=0.5), maxlen=1.0)


def spark():
    mx = Mix(0.3)
    mx.at(0, blip(1800, 2600, 0.06, tau=0.025, harm=0.1), 0.8)
    mx.at(0.035, blip(2600, 3400, 0.06, tau=0.025, harm=0.1), 0.6)
    mx.at(0, grains(0.12, 30, 4000, 8000, (0.001, 0.003)), 0.35)
    return finish(room(lowpass(mx.out(), 10000), 0.05, tail=0.15), -4)


def boost():
    dur = 0.8
    n = ns(dur)
    u = np.linspace(0, 1, n)
    env = np.clip(u / 0.05, 0, 1) * np.clip((1 - u) / 0.65, 0, 1) ** 1.5
    air = bandpass(noise(n), 500 * 7.0 ** (u ** 0.6), 1.0) * env
    ft = 140 * 3.2 ** (u ** 0.5) * (1 + 0.02 * np.sin(2 * np.pi * 28 * tvec(n)))
    jet = lowpass(tone(ft, n, (1, 0.5, 0.25)), 2500) * env
    mx = Mix(1.1)
    mx.at(0, thump(70, 0.3, tau=0.08, drop=2.0, nz=0.4, nzf=300), 0.8)
    mx.at(0, air, 1.6)
    mx.at(0, jet, 0.35)
    return finish(room(lowpass(mx.out(), 8000), 0.06, tail=0.25), maxlen=1.0)


def land():
    mx = Mix(0.5)
    mx.at(0, thump(85, 0.3, tau=0.07, drop=1.8, nz=0.7, nzf=450))
    n = ns(0.25)
    t = tvec(n)
    f = 230 * (1 + 0.08 * np.sin(2 * np.pi * 18 * t) * np.exp(-t / 0.08))
    mx.at(0.01, sine(f, n) * perc(n, 0.003, 0.06), 0.25)
    mx.at(0, grains(0.12, 18, 1200, 3200, (0.002, 0.005)), 0.2)
    return finish(room(lowpass(mx.out(), 6000), 0.04, tail=0.25), squash=5)


def bump():
    """Wall: a cartoon wooden 'bonk' with a little falling boing."""
    mx = Mix(0.6)
    mx.at(0, wood(420, 0.3, ratios=(1, 2.7, 4.4), taus=(0.06, 0.03, 0.012)), 0.9)
    mx.at(0, thump(110, 0.25, tau=0.07, drop=1.6, nz=0.5), 0.9)
    n = ns(0.24)
    t = tvec(n)
    f = 520 * 0.55 ** (t / 0.24) * (1 + 0.05 * np.sin(2 * np.pi * 24 * t))
    mx.at(0.02, tone(f, n, (1, 0.2)) * perc(n, 0.003, 0.08), 0.6)
    return finish(room(lowpass(mx.out(), 7000), 0.05, tail=0.25), squash=8)


def bump_kart():
    mx = Mix(0.4)
    mx.at(0, boing(260), 1.0)
    mx.at(0, thump(120, 0.12, tau=0.025, nz=0.3), 0.45)
    return finish(room(lowpass(mx.out(), 6000), 0.04, tail=0.2), -4, squash=5)


def flap():
    n = ns(0.17)
    u = np.linspace(0, 1, n)
    x = bandpass(noise(n), 650 + 500 * u, 0.8) * np.sin(np.pi * u ** 0.7) ** 2
    return x * 1.6 + thump(70, 0.17, tau=0.05, drop=1.2, nz=0) * 0.35


def ptera():
    """Pterosaur swoops in: flap flap flap, then a friendly 'kee-yaa!'."""
    mx = Mix(1.6)
    for i, t in enumerate([0, 0.19, 0.38]):
        mx.at(t, flap(), 0.9 - 0.12 * i)
    n = ns(0.12)
    f0 = glide(1250, 1450, 0.12, 1.5)
    mx.at(0.52, voice(f0, [(0, 'i'), (1, 'i')], scale=1.7) * adsr(n, 0.01, 0.05, 0.8, 0.04), 0.6)
    n = ns(0.5)
    t = tvec(n)
    u = t / 0.5
    f0 = (1100 + 450 * np.sin(np.pi * np.clip(u * 1.3, 0, 1) ** 0.7) - 250 * u) * \
        (1 + 0.025 * np.sin(2 * np.pi * 21 * t))
    x = voice(f0, [(0, 'e'), (0.3, 'a'), (1, 'o')], scale=1.7, tilt=0.9) * adsr(n, 0.02, 0.15, 0.8, 0.14)
    mx.at(0.66, x, 0.8)
    return finish(room(lowpass(mx.out(), 8000), 0.12, tail=0.5), maxlen=1.5)


def pop():
    """Shield bubble popping: tight pop + droplets."""
    mx = Mix(0.5)
    n = ns(0.05)
    mx.at(0, sine(glide(500, 1600, 0.05, 2.0), n) * perc(n, 0.0008, 0.015))
    nn = ns(0.03)
    mx.at(0, highpass(noise(nn), 1500) * perc(nn, 0.0003, 0.006) * 2.0, 0.8)
    for _ in range(5):
        f = S.rng().uniform(1200, 2800)
        mx.at(S.rng().uniform(0.03, 0.22), blip(f, f * 1.7, 0.03, tau=0.01, harm=0, curve=1.0),
              S.rng().uniform(0.2, 0.4))
    return finish(room(mx.out(), 0.08, tail=0.3), squash=8)


def hit():
    """Spun out: soft bonk, a wobbly slide-whistle spin down and two birdie tweets."""
    mx = Mix(1.4)
    mx.at(0, boing(300, tau=0.07), 0.6)
    mx.at(0, thump(110, 0.15, tau=0.03, nz=0.3), 0.4)
    n = ns(0.85)
    t = tvec(n)
    u = t / 0.85
    f = 1300 * 0.28 ** (u ** 0.8) * (1 + 0.06 * np.sin(2 * np.pi * 9 * t))
    mx.at(0.05, tone(f, n, (1, 0.08)) * adsr(n, 0.02, 0.3, 0.8, 0.2), 0.45)
    for t0 in (0.75, 0.92):
        mx.at(t0, blip(2300, 3100, 0.06, tau=0.025, harm=0.05, curve=1.5), 0.18)
        mx.at(t0 + 0.06, blip(2500, 3300, 0.05, tau=0.02, harm=0.05, curve=1.5), 0.14)
    return finish(room(lowpass(mx.out(), 8000), 0.1, tail=0.4), maxlen=1.4)


def bubble():
    """Shield on: a rising chorused bloop wrapped in little bubbles."""
    mx = Mix(1.0)
    n = ns(0.45)
    t = tvec(n)
    f = glide(250, 800, 0.45, 2.0) * (1 + 0.02 * np.sin(2 * np.pi * 7 * t))
    x = (sine(f, n) + sine(f * 1.006, n) + 0.2 * sine(f * 2, n)) * adsr(n, 0.03, 0.2, 0.8, 0.15)
    mx.at(0, x, 0.45)
    for _ in range(9):
        fb = S.rng().uniform(600, 1800)
        mx.at(S.rng().uniform(0, 0.4), blip(fb, fb * 1.8, 0.03, tau=0.012, harm=0, curve=1.0),
              S.rng().uniform(0.15, 0.35))
    mx.at(0.3, fm_bell(hz('E6'), 0.4, ratio=2.0, index=0.6, tau=0.5), 0.35)
    return finish(room(lowpass(mx.out(), 9000), 0.15, tail=0.5), maxlen=1.2)


def fern():
    """Golden fern: sparkling pentatonic run up into a bell chord + shimmer."""
    mx = Mix(2.2)
    pool = [m for m in range(72, 104) if m % 12 in SPARK_PC]
    for i, m in enumerate(pool[:14]):
        mx.at(i * 0.04, glock(hz(m), 0.35 + 0.02 * i))
    for m in ['C6', 'E6', 'G6', 'C7']:
        mx.at(0.6, fm_bell(hz(m), 0.45, ratio=2.0, index=0.8, tau=0.9), 0.5)
    dur = 1.3
    n = ns(dur)
    t = tvec(n)
    u = t / dur
    sh = np.zeros(n)
    for _ in range(8):
        f0 = S.rng().uniform(700, 1400)
        trem = 0.6 + 0.4 * np.sin(2 * np.pi * S.rng().uniform(9, 14) * t + S.rng().uniform(0, 6))
        sh += sine(f0 * 2 ** (1.2 * u ** 1.3), n) * trem / 8
    mx.at(0.1, sh * np.sin(np.pi * u ** 0.6) ** 2, 0.4)
    return finish(room(lowpass(mx.out(), 10000), 0.25, size=0.7, tail=0.8), maxlen=1.8)


def throw():
    n = ns(0.32)
    u = np.linspace(0, 1, n)
    f = 450 + 1600 * np.sin(np.pi * np.clip(u * 0.9, 0, 1)) ** 2
    x = bandpass(noise(n), f, 1.4) * np.sin(np.pi * u ** 0.8) ** 2
    mx = Mix(0.4)
    mx.at(0, lowpass(x, 5000))
    mx.at(0.02, blip(300, 520, 0.08, tau=0.03, harm=0.2), 0.25)
    return finish(room(mx.out(), 0.05, tail=0.2), -4)


def egg_bounce():
    mx = Mix(0.2)
    mx.at(0, wood(900, 0.1, taus=(0.025, 0.012, 0.006)), 0.8)
    n = ns(0.1)
    mx.at(0, sine(glide(500, 800, 0.1), n) * perc(n, 0.002, 0.03), 0.4)
    return finish(room(mx.out(), 0.04, tail=0.12), -4, squash=5)


def roar():
    """Cute dino roar + a soft round shockwave whoomp."""
    mx = Mix(1.6)
    dur = 0.9
    n = ns(dur)
    t = tvec(n)
    u = t / dur
    f0 = 190 + 70 * np.sin(np.pi * u ** 0.7) - 45 * u
    x = voice(f0, [(0, 'r'), (0.2, 'a'), (0.7, 'o'), (1, 'u')], scale=1.05, tilt=0.9, breath=0.03)
    roll = np.where(u < 0.4, 0.6 + 0.4 * np.sin(2 * np.pi * 28 * t) ** 2, 1.0)
    x = S._norm1(x) * roll * adsr(n, 0.04, 0.3, 0.85, 0.25)
    mx.at(0.05, x, 0.9)
    nn = ns(0.9)
    tt = tvec(nn)
    mx.at(0, sine(35 + 90 * np.exp(-tt / 0.4), nn) * perc(nn, 0.01, 0.25), 0.6)
    w = lowpass(noise(nn), 300 + 1700 * np.exp(-tt / 0.2)) * perc(nn, 0.02, 0.2)
    mx.at(0, w, 0.7)
    return finish(room(lowpass(mx.out(), 6000), 0.12, size=0.6, tail=0.5), maxlen=1.4)


def splat():
    mx = Mix(0.8)
    n = ns(0.35)
    u = np.linspace(0, 1, n)
    mx.at(0, lowpass(noise(n), 2500 * 0.15 ** u) * perc(n, 0.003, 0.08), 1.3)
    mx.at(0, thump(70, 0.25, tau=0.05, nz=0.6, nzf=300), 0.7)
    m = ns(0.2)
    um = np.linspace(0, 1, m)
    mx.at(0.05, bandpass(noise(m), 1400 * (300 / 1400) ** um, 4.0) * np.sin(np.pi * um) ** 1.5, 1.0)
    for _ in range(5):
        f = S.rng().uniform(300, 700)
        mx.at(S.rng().uniform(0.1, 0.35), blip(f, f * 0.6, 0.05, tau=0.02, harm=0.2), 0.3)
    return finish(room(lowpass(mx.out(), 5000), 0.06, tail=0.3), squash=5)


# ---------------------------------------------------------------- race flow

def count():
    mx = Mix(0.5)
    mx.at(0, beep(hz('A5'), 0.26))
    mx.at(0, marimba(hz('A5'), 0.7, hard=0.6), 0.4)
    return finish(room(mx.out(), 0.08, tail=0.3))


def go():
    mx = Mix(1.0)
    mx.at(0, beep(hz('A6'), 0.55))
    mx.at(0, beep(hz('E6'), 0.55), 0.45)
    mx.at(0, beep(hz('A5'), 0.55), 0.35)
    mx.at(0, glock(hz('A7'), 0.4), 0.4)
    mx.at(0.08, sparkle(3, 93, 105, 0.25, 0.25, up=True))
    return finish(room(lowpass(mx.out(), 10000), 0.1, tail=0.4), maxlen=1.1)


def finish_line():
    """Finish-line fanfare sting (~1.5 s)."""
    mx = Mix(2.2)
    step = 0.11
    for i, m in enumerate(['G4', 'C5', 'E5']):
        mx.at(i * step, brass(hz(m), 0.09, 0.8))
        mx.at(i * step, marimba(hz(m) * 2, 0.6, hard=0.6), 0.4)
    t = 3 * step
    for m in ['C5', 'E5', 'G5', 'C6']:
        mx.at(t, brass(hz(m), 0.75, 0.75), 0.5)
    mx.at(t, glock(hz('C7'), 0.5), 0.6)
    mx.at(t, crash(0.35, 1.2), 0.35)
    mx.at(t, timpani(hz('C3'), 0.7), 0.5)
    mx.at(t + 0.1, sparkle(4, 96, 105, 0.4, 0.25, up=True))
    return finish(room(lowpass(mx.out(), 10000), 0.15, tail=0.8), maxlen=1.8)


def last_lap():
    """Final lap alert: da-da-da-DAAA + ding ding."""
    mx = Mix(1.8)
    for t, m, d in [(0, 'G4', 0.08), (0.11, 'G4', 0.08), (0.22, 'C5', 0.08), (0.33, 'E5', 0.5)]:
        for k, tr in enumerate([0, 7, 12]):
            if d < 0.2 and k:
                continue
            mx.at(t, brass(hz(m) * 2 ** (tr / 12), d, 0.75), 0.5 if k == 0 else 0.3)
    for t in (0.33, 0.55):
        mx.at(t, fm_bell(hz('E6'), 0.6, ratio=3.5, index=1.0, tau=0.35), 0.5)
    mx.at(0.33, timpani(hz('C3'), 0.6), 0.35)
    return finish(room(lowpass(mx.out(), 9000), 0.12, tail=0.6), maxlen=1.4)


# ---------------------------------------------------------------- UI and rewards

def tick():
    x = marimba(hz('C6'), 0.6, hard=0.15)[:ns(0.1)]
    return finish(fade(x, 0, 0.05), -10)


def ok():
    mx = Mix(0.6)
    mx.at(0, marimba(hz('G5'), 0.75, hard=0.4))
    mx.at(0.07, marimba(hz('D6'), 0.85, hard=0.45))
    mx.at(0.07, glock(hz('D7'), 0.2))
    x = mx.out()[:ns(0.45)]
    return finish(room(fade(x, 0, 0.15), 0.06, tail=0.25), -6)


def back():
    mx = Mix(0.6)
    mx.at(0, marimba(hz('D6'), 0.65, hard=0.3))
    mx.at(0.08, marimba(hz('A5'), 0.6, hard=0.25))
    x = mx.out()[:ns(0.42)]
    return finish(room(fade(x, 0, 0.15), 0.05, tail=0.2), -8)


def coin():
    mx = Mix(0.7)
    mx.at(0, coin_ping(1980, 0.7, 0.35))
    mx.at(0.055, coin_ping(2495, 0.8, 0.45))
    mx.at(0.08, sparkle(2, 98, 105, 0.08, 0.2, up=True))
    return finish(room(lowpass(mx.out(), 10000), 0.08, tail=0.3), maxlen=0.7)


def cheer():
    """Crowd of little dinos cheering 'yaaay!' + clapping (~2 s)."""
    mx = Mix(2.6)
    paths = [[(0, 'i'), (0.25, 'e'), (1, 'a')], [(0, 'e'), (0.3, 'a'), (1, 'a')],
             [(0, 'u'), (0.4, 'o'), (1, 'o')], [(0, 'a'), (1, 'e')]]
    for k in range(26):
        t0 = S.rng().uniform(0, 0.35)
        d = S.rng().uniform(1.0, 1.75)
        n = ns(d)
        t = tvec(n)
        u = t / d
        base = S.rng().uniform(230, 650)
        f0 = base * (1 + 0.28 * np.sin(np.pi * np.clip(u * 1.3, 0, 1))) * \
            (1 + 0.035 * np.sin(2 * np.pi * S.rng().uniform(5, 9) * t))
        x = voice(f0, paths[k % 4], scale=S.rng().uniform(1.0, 1.6), kmax=40, breath=0.02)
        x = S._norm1(x) * adsr(n, 0.05, 0.3, 0.8, 0.3)
        mx.at(t0, x, S.rng().uniform(0.15, 0.3))
    for _ in range(70):
        t0 = S.rng().uniform(0.05, 2.1)
        n = ns(0.03)
        cl = bandpass(noise(n), S.rng().uniform(1100, 1900), 1.2) * perc(n, 0.0005, 0.007)
        mx.at(t0, cl, S.rng().uniform(0.5, 1.2) * (1 - t0 / 2.6))
    for t0 in (0.2, 0.5, 0.9):
        f = S.rng().uniform(1500, 2000)
        mx.at(t0, blip(f, f * 1.5, 0.08, tau=0.04, harm=0.1, curve=1.5), 0.15)
    x = mx.out()
    tt = tvec(len(x))
    x *= np.clip((2.35 - tt) / 0.9, 0, 1)
    return finish(room(lowpass(x, 8000), 0.25, size=0.7, tail=0.5), maxlen=2.8)


SOUNDS = {
    'egg_crack': egg_crack, 'item_get': item_get, 'spark': spark, 'boost': boost, 'land': land,
    'bump': bump, 'bump_kart': bump_kart, 'ptera': ptera, 'pop': pop, 'hit': hit,
    'bubble': bubble, 'fern': fern, 'throw': throw, 'egg_bounce': egg_bounce, 'roar': roar,
    'splat': splat, 'count': count, 'go': go, 'finish': finish_line, 'last_lap': last_lap,
    'tick': tick, 'ok': ok, 'back': back, 'coin': coin, 'cheer': cheer,
}


def main(names):
    os.makedirs(OUT, exist_ok=True)
    dump = os.environ.get('WAV')
    if dump:
        os.makedirs(SCRATCH, exist_ok=True)
    for i, name in enumerate(sorted(SOUNDS)):
        if names and name not in names:
            continue
        S.seed(2000 + i * 7919)
        x = SOUNDS[name]()
        write_ogg(os.path.join(OUT, name + '.ogg'), x, q=4)
        if dump:
            write_wav(os.path.join(SCRATCH, name + '.wav'), x)
        print('%-12s %5.2f s  peak %6.1f dBFS' % (name, len(x) / SR, db(peak(x))))


if __name__ == '__main__':
    main(set(sys.argv[1:]))
