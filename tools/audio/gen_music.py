#!/usr/bin/env python3
"""Generate the music of Tommy's Dino Kart into game/assets/music/*.ogg.

Original tunes, all synthesised (synth.py), no samples. The loops are
rendered with an extra tail and the tail is folded back onto the start, so
every file wraps around seamlessly (reverb and ringing notes included).
Race loops sit around -16.5 LUFS with a look-ahead limiter at -1.5 dBFS.

    python3 tools/audio/gen_music.py                     # all
    python3 tools/audio/gen_music.py race_snow battle    # only these
    WAV=1 ...                                            # also dump WAVs to scratch

The Dino Kart hook (5-1-3-5 up, stepping back down: G C E G F E D | E C D G
in C) opens the title, carries the finale's chorus and the podium jingle.

Each track has its own key, tempo and band:
    title         D    132  square lead, brass, uke, pop drums (the hook)
    menu          D    104  kalimba, electric piano, flute (title, relaxed)
    race_meadow   G    150  square lead, marimba riff, uke, claps, tambourine
    race_forest   Em   144  flute, horn calls, pizzicato, toms, woodblocks
    race_beach    F    140  steel drum, marimba, congas, four-on-the-floor
    race_lagoon   A    146  soft lead, bloops, kalimba, bouncy bass
    race_canyon   Am   138  twang guitar, banjo, whistle, gallop percussion
    race_swamp    Dm   128  funky synth bass, organ, plucks, croaks
    race_snow     E    152  bells, glockenspiel, sleigh bells, pizzicato
    race_night    Fm   142  half-time groove, flute, e-piano, fireflies
    race_caves    Bm   150  crystal arpeggios, saw lead, big reverb
    race_volcano  Cm   162  driving bass, brass, square lead, toms
    race_cliffs   Eb   140  strings, brass melody, timpani, harp
    race_finale   C    156  everything + choir: the hook as the chorus
    battle        Gm   120  punchy riff, claps, brass stabs
    win/finish/podium/rest  jingles, not looped
"""
import os
import tempfile
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth as S  # noqa: E402
from synth import (Chord, Song, banjo, bass, brass, choir, clap, conga, crash, ep, flute,  # noqa: E402
                   fm_bell, glock, hat, hz, jingle, kalimba, kick, lead, marimba, musicbox, ns,
                   organ, pad, parse, pluck, shaker, snare, steeldrum, synbass, timpani, tom,
                   twang, whistle, woodblock)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'game', 'assets', 'music')
SCRATCH = os.environ.get('AUDIO_SCRATCH', os.path.join(tempfile.gettempdir(), 'tdk_audio'))
OGG_Q = 3
_CUR = ['']


def bloop(f, vel=0.7):
    """Watery sine pluck: the pitch slides up onto the note."""
    n = ns(0.35)
    t = S.tvec(n)
    x = S.sine(f * (1 - 0.25 * np.exp(-t / 0.018)), n) * S.perc(n, 0.002, 0.09)
    return x * vel


_CHOIR = {}


def choir_c(f, d, v, vowel='a'):
    key = (round(f, 1), round(d, 2), vowel)
    if key not in _CHOIR:
        _CHOIR[key] = choir(f, d, 1.0, vowel)
    return _CHOIR[key] * v


INST = {
    'marimba': lambda f, d, v: marimba(f, v, hard=0.3),
    'xylo': lambda f, d, v: marimba(f, v, hard=0.75),
    'kalimba': lambda f, d, v: kalimba(f, v),
    'musicbox': lambda f, d, v: musicbox(f, v),
    'glock': lambda f, d, v: glock(f, v),
    'bell': lambda f, d, v: fm_bell(f, v, ratio=3.5, index=0.9, tau=1.1),
    'sweetbell': lambda f, d, v: fm_bell(f, v, ratio=2.0, index=0.8, tau=1.0),
    'crystal': lambda f, d, v: fm_bell(f, v, ratio=4.0, index=1.1, tau=0.32, dur=1.0),
    'ep': lambda f, d, v: ep(f, d, v),
    'flute': lambda f, d, v: flute(f, d, v),
    'pluck': lambda f, d, v: pluck(f, d, v, bright=0.45, t60=1.3),
    'harp': lambda f, d, v: pluck(f, max(d, 1.2), v, bright=0.3, t60=2.4, pick=0.3),
    'bass': lambda f, d, v: bass(f, d, v),
    'pizz': lambda f, d, v: pluck(f, min(d, 0.3), v, bright=0.25, t60=0.6, pick=0.4),
    'lead': lambda f, d, v: lead(f, d, v, 'square', bright=3.0),
    'softlead': lambda f, d, v: lead(f, d, v, 'tri', bright=6.0, vib=0.006),
    'sawlead': lambda f, d, v: lead(f, d, v, 'saw', bright=4.0, dark=2.0, tau=0.25, vib=0.006),
    'synpluck': lambda f, d, v: lead(f, min(d, 0.5), v, 'saw', bright=8.0, dark=1.3, tau=0.05,
                                     sus=0.25, release=0.15, vib=0),
    'steel': lambda f, d, v: steeldrum(f, v),
    'brass': lambda f, d, v: brass(f, d, v),
    'organ': lambda f, d, v: organ(f, d, v),
    'synbass': lambda f, d, v: synbass(f, d, v, 0.4),
    'sqbass': lambda f, d, v: synbass(f, d, v, 0.5, 'square', tau=0.05),
    'twang': lambda f, d, v: twang(f, d, v),
    'banjo': lambda f, d, v: banjo(f, d, v),
    'whistle': lambda f, d, v: whistle(f, d, v),
    'choir': lambda f, d, v: choir_c(f, d, v, 'a'),
    'choiro': lambda f, d, v: choir_c(f, d, v, 'o'),
    'bloop': lambda f, d, v: bloop(f, v),
}


def hv(v, spread=0.12):
    """Humanised velocity."""
    return v * S.rng().uniform(1 - spread, 1 + spread * 0.4)


# ---------------------------------------------------------------- notation helpers

NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def nname(m):
    return '%s%d' % (NAMES[m % 12], m // 12 - 1)


def transpose(seq, k):
    out = []
    for tok in seq.split():
        if tok == '|':
            out.append(tok)
            continue
        name, d = tok.split(':')
        if name not in ('r', '-'):
            name = '+'.join(nname(S.note(x) + k) for x in name.split('+'))
        out.append(name + ':' + d)
    return ' '.join(out)


def check_bars(seq, meter):
    for i, bar in enumerate(seq.split('|')):
        _, L = parse(bar)
        if abs(L - meter) > 1e-6:
            print('  ! %s: bar %d of a melody has %.3f beats' % (_CUR[0], i, L))


# The Dino Kart hook, in C (transpose for other keys). Open ends on the 2nd
# degree (a question), the answer starts on the 6th, closed lands home.
HOOK_OPEN = 'G4:.5 C5:.5 E5:.5 G5:1 F5:.5 E5:.5 D5:.5 | E5:1.5 C5:.5 D5:1 G4:1'
HOOK_ANS = 'A4:.5 C5:.5 E5:.5 A5:1 G5:.5 E5:.5 D5:.5 | E5:1 D5:1 C5:1 D5:1'
HOOK_CLOSE = 'G4:.5 C5:.5 E5:.5 G5:1 F5:.5 E5:.5 D5:.5 | E5:1.5 D5:.5 C5:2'
HOOK_CHORUS = ' | '.join([HOOK_OPEN, HOOK_ANS, HOOK_OPEN, HOOK_CLOSE])   # 8 bars


# ---------------------------------------------------------------- building blocks

def timeline(song, prog, bar0=0):
    """'F | Am | Bb C' -> [(beat, Chord, beats)] starting at bar0."""
    out = []
    for i, bar in enumerate(prog.split('|')):
        syms = bar.split()
        for j, sym in enumerate(syms):
            out.append(((bar0 + i) * song.meter + j * song.meter / len(syms), Chord(sym),
                        song.meter / len(syms)))
    return out


def song_prog(song, *sections):
    prog = ' | '.join(sections)
    nb = len(prog.split('|'))
    if abs(nb * song.meter - song.beats) > 1e-6:
        print('  ! %s: progression has %d bars, song has %g' % (_CUR[0], nb, song.beats / song.meter))
    return timeline(song, prog)


def _inbars(beat, bars, meter):
    return not bars or bars[0] * meter <= beat < bars[1] * meter


def melody(song, seq, bar, inst, gain=0.5, pan=0.0, rev=0.3, vel=0.8, octave=0, legato=0.95,
           accent=None):
    if '|' in seq:
        check_bars(seq, song.meter)
    notes, _ = parse(seq)
    b0 = bar * song.meter
    for b, ms, d in notes:
        v = vel
        if accent and (b % song.meter) == 0:
            v *= accent
        for m in ms:
            sig = INST[inst](hz(m + 12 * octave), song.dur(b0 + b, d) * legato, hv(v))
            song.add(b0 + b, sig, gain, pan, rev)


def arp(song, tl, pattern, inst, octave=4, gain=0.3, pan=0.0, rev=0.3, step=0.5, vels=None,
        dur=None, bars=None, pan_lfo=0.0):
    """Broken chords: pattern = chord-tone indices per step (None = rest)."""
    for beat, ch, beats in tl:
        if not _inbars(beat, bars, song.meter):
            continue
        k = 0
        t = 0.0
        while t < beats - 1e-6:
            i = pattern[k % len(pattern)]
            if i is not None:
                v = vels[k % len(vels)] if vels else 0.7
                f = S.mtof(ch.pc(i, octave))
                d = song.dur(beat + t, dur if dur else step)
                p = pan + pan_lfo * np.sin(2 * np.pi * (beat + t) / 8)
                song.add(beat + t, INST[inst](float(f), d, hv(v)), gain, p, rev)
            k += 1
            t += step


def bassline(song, tl, pattern, inst='bass', gain=0.5, lo=36, rev=0.1, bars=None):
    """pattern: [(beat, 'R'|'5'|'8'|'3', beats, vel)] relative to each chord."""
    for beat, ch, beats in tl:
        if not _inbars(beat, bars, song.meter):
            continue
        for ob, which, d, v in pattern:
            if ob >= beats - 1e-6:
                continue
            r = ch.bass_note(lo)
            m = {'R': r, '5': ch.fifth(lo), '8': r + 12, '3': ch.pc(1, (r // 12) - 1)}[which]
            if which == '3' and m < r:
                m += 12
            dd = min(d, beats - ob)
            song.add(beat + ob, INST[inst](hz(m), song.dur(beat + ob, dd), hv(v, 0.08)), gain, 0, rev)


def eighths(vels=(0.9, 0.6, 0.75, 0.6, 0.85, 0.6, 0.75, 0.6), which='R', d=0.42):
    return [(i * 0.5, which, d, v) for i, v in enumerate(vels)]


def pads(song, tl, center=60, count=4, gain=0.2, fc=1400, rev=0.4, bars=None, kind='saw',
         attack=0.8, inst=None):
    for beat, ch, beats in tl:
        if not _inbars(beat, bars, song.meter):
            continue
        d = song.dur(beat, beats) + 0.15
        for m in ch.voicing(center, count):
            sig = INST[inst](hz(m), d, 0.6) if inst else pad(hz(m), d, 0.6, fc=fc, attack=attack, kind=kind)
            song.add(beat, sig, gain, 0, rev, jitter=0)


def chords_on(song, tl, hits, inst, center=62, count=3, gain=0.25, rev=0.3, spread=0.012,
              bars=None, pan=0.0):
    """Block chords at hits = [(beat, beats, vel)] (slightly rolled)."""
    for beat, ch, beats in tl:
        if not _inbars(beat, bars, song.meter):
            continue
        for ob, d, v in hits:
            if ob >= beats - 1e-6:
                continue
            for j, m in enumerate(ch.voicing(center, count)):
                sig = INST[inst](hz(m), song.dur(beat + ob, d), hv(v))
                song.add(beat + ob + j * spread / song.spb, sig, gain, pan + 0.2 * (j - 1), rev,
                         jitter=0.004)


UKE_STRUM = [(0, 'D', 0.9), (1, 'D', 0.65), (1.5, 'U', 0.45), (2.5, 'U', 0.5), (3, 'D', 0.7),
             (3.5, 'U', 0.45)]


def uke(song, tl, pattern=UKE_STRUM, gain=0.25, center=67, rev=0.25, bars=None, mute=0.0, bright=0.35):
    """Strums: 4 KS strings, down = low->high, up = high->low."""
    for beat, ch, beats in tl:
        if not _inbars(beat, bars, song.meter):
            continue
        notes = ch.voicing(center, 4)
        for ob, dirn, v in pattern:
            if ob >= beats - 1e-6:
                continue
            order = notes if dirn == 'D' else notes[::-1]
            nxt = min([p[0] for p in pattern if p[0] > ob] + [beats])
            d = song.dur(beat + ob, nxt - ob) * (1 - mute) + 0.05
            for j, m in enumerate(order):
                sig = pluck(hz(m), d, hv(v) * (0.85 if dirn == 'U' else 1), bright=bright, t60=1.2,
                            pick=0.18)
                song.add(beat + ob + j * 0.012 / song.spb, sig, gain, -0.25 + 0.17 * j, rev,
                         jitter=0.003)


def sprinkle(song, tl, inst, per_bar=2, octave=6, gain=0.1, rev=0.6, bars=None, vel=0.5):
    """Random high chord tones (fireflies, glints, ice sparkles)."""
    for beat, ch, beats in tl:
        if not _inbars(beat, bars, song.meter):
            continue
        for _ in range(S.rng().poisson(per_bar * beats / song.meter)):
            b = beat + S.rng().integers(0, int(beats * 2)) * 0.5
            m = ch.pc(int(S.rng().integers(0, 3)), octave)
            song.add(b, INST[inst](hz(m), song.dur(b, 1), hv(vel, 0.3)), gain,
                     S.rng().uniform(-0.7, 0.7), rev)


# ---------------------------------------------------------------- drums

VEL = {'X': 1.0, 'x': 0.78, 'o': 0.55, '.': 0.32}


def make_kit(punch=0.5, ktau=0.12, stone=200, snap=0.5, toms=(210, 160, 115)):
    n1 = S._norm1
    return {
        'k': [kick(1.0, punch, tau=ktau, f_end=56)],
        's': [snare(1.0, stone, snap) for _ in range(3)],
        'c': [clap(1.0) for _ in range(2)],
        'h': [hat(1.3) for _ in range(4)],
        'o': [hat(1.3, True) for _ in range(2)],
        'cr': [crash(1.0)],
        't1': [tom(toms[0], 1.0)], 't2': [tom(toms[1], 1.0)], 't3': [tom(toms[2], 1.0)],
        'sh': [n1(shaker(1.0, 0.11, b)) for b in (0.9, 1.0, 1.1, 0.95)],
        'tb': [jingle(1.2, 3500, 7000, 7, 0.18) for _ in range(3)],
        'sl': [jingle(1.0) for _ in range(4)],
        'cgh': [conga(390, 1.0)], 'cgl': [conga(265, 1.0)], 'cgs': [conga(390, 1.0, slap=True)],
        'wb': [n1(woodblock(950, 1.0))], 'wb2': [n1(woodblock(700, 1.0))],
    }


def drums(song, kit, bar0, bar1, parts, swing=0.0, fills=()):
    """parts: {kit_name: (pattern, gain, pan[, rev])}. Patterns are 16 steps per
    bar ('X' 'x' 'o' '.' = hits, '-' rest; spaces ignored), 32 = two bars.
    In bars listed in `fills` only the first half of the pattern plays."""
    for name, spec in parts.items():
        pat, gain, pan_ = spec[:3]
        rev = spec[3] if len(spec) > 3 else 0.06
        pat = pat.replace(' ', '')
        bank = kit[name]
        nbp = max(1, len(pat) // 16)
        per = len(pat) // nbp
        step = song.meter / per
        for bar in range(bar0, bar1):
            off = ((bar - bar0) % nbp) * per
            for i in range(per):
                c = pat[off + i]
                if c not in VEL or (bar in fills and i >= per // 2):
                    continue
                b = bar * song.meter + i * step
                if swing and i % 2:
                    b += swing * step
                song.add(b, bank[(bar * 7 + i) % len(bank)] * hv(VEL[c], 0.08), gain, pan_, rev,
                         jitter=0.002)


def fill(song, kit, bar, kind='toms', gain=0.42, crash_next=0.0):
    b = bar * song.meter + 2
    if kind == 'toms':
        seq = ['t1', 't1', 't2', 't2', 't3', 't3', 't3', 'k']
    elif kind == 'snare':
        seq = ['s'] * 8
    else:
        seq = ['s', 's', 't1', 't1', 't2', 't2', 't3', 'k']
    for i, nm in enumerate(seq):
        v = 0.55 + 0.45 * i / 7
        song.add(b + i * 0.25, kit[nm][0] * hv(v, 0.06), gain * (1.1 if nm == 'k' else 1),
                 {'t1': 0.3, 't2': 0.0, 't3': -0.3}.get(nm, 0), 0.12, jitter=0.002)
    if crash_next:
        song.add((bar + 1) * song.meter, kit['cr'][0], crash_next, 0.25, 0.15, jitter=0)


def crashes(song, kit, bars, gain=0.2):
    for bar in bars:
        song.add(bar * song.meter, kit['cr'][0], gain, 0.25, 0.15, jitter=0)


# ---------------------------------------------------------------- mixing

def finish_song(song, target=-16.5, room=0.8, damp=0.35, wet=1.0, fade_out=None, length=None):
    x = song.render(room=room, damp=damp, wet=wet, hp=45)
    if not song.loop:
        a = np.abs(x).max(0)
        idx = np.nonzero(a > a.max() * S.undb(-60))[0]
        x = x[:, :idx[-1] + ns(0.05)]
        if length:
            x = x[:, :ns(length)]
        n = min(ns(fade_out or 0.6), x.shape[1])
        x[:, -n:] *= np.linspace(1, 0, n) ** 2
    for _ in range(2):
        x = x * S.undb(target - S.loudness(x))
        x = S.limit(x, -1.5, loop=song.loop)
    return x


# ================================================================ tracks

TITLE_A = ('F#5:1 A5:.5 F#5:.5 E5:1 D5:1 | B4:.5 D5:.5 F#5:1 F#5:.5 E5:.5 D5:1 | '
           'G5:1 B5:.5 G5:.5 D5:1 E5:1 | E5:1.5 F#5:.5 A5:2 | '
           'F#5:1 A5:.5 F#5:.5 E5:1 D5:1 | B4:.5 D5:.5 F#5:1 B5:1 A5:1 | '
           'G5:.5 F#5:.5 E5:.5 D5:.5 E5:1 G5:1 | F#5:1 E5:1 C#5:1 A4:1')
TITLE_B = ('D5:.5 G5:.5 B5:1 A5:.5 G5:.5 D5:1 | C#5:.5 E5:.5 A5:1 G5:.5 F#5:.5 E5:1 | '
           'F#5:1 C#5:1 A4:1 C#5:1 | D5:1.5 C#5:.5 B4:2 | '
           'D5:.5 G5:.5 B5:1 A5:.5 G5:.5 D5:1 | E5:.5 A5:.5 C#6:1 B5:.5 A5:.5 E5:1 | '
           'D6:1 B5:1 A5:1 E5:1 | B5:1 G5:1 A5:1 r:1')


def title():
    """D major, 132 bpm, 36 bars (65 s). The hook, then a verse, a lift,
    the hook as a chorus and a breakdown that builds back to the top."""
    s = Song(132, 36)
    k = make_kit(punch=0.55)
    tl = song_prog(s, 'D | Bm A | D | A D',
                   'D | Bm | G | A | D | Bm | Em | A',
                   'G | A | F#m | Bm | G | A | Bm A/C# | Em7 A7',
                   'D | Bm A | G | Bm G | D | Bm A | D | A D',
                   'G | A | F#m | Bm | G | A | Em7 | A7sus4 A7')
    hook_d = transpose(' | '.join([HOOK_OPEN, HOOK_CLOSE]), 2)
    chorus_d = transpose(HOOK_CHORUS, 2)
    pads(s, tl, center=62, gain=0.07, fc=1500, bars=(0, 36))
    # intro: the hook on lead + glock over brass stabs
    melody(s, hook_d, 0, 'lead', gain=0.30, pan=0.05, vel=0.8)
    melody(s, hook_d, 0, 'glock', gain=0.12, pan=0.3, vel=0.6, octave=1)
    chords_on(s, tl, [(0, 0.35, 0.75), (1.5, 0.3, 0.6), (3, 0.3, 0.65)], 'brass', center=57,
              count=3, gain=0.13, spread=0.0, bars=(0, 4))
    bassline(s, tl, eighths(), 'synbass', gain=0.34, lo=38, bars=(0, 4))
    drums(s, k, 0, 4, {'k': ('X---x---X---x---', 0.5, 0), 'h': ('x-o-x-o-x-o-x-o-', 0.1, 0.2)},
          fills={3})
    fill(s, k, 3, 'toms', crash_next=0.22)
    # verse: lead + uke strums + rock beat
    rock = {'k': ('X---o-x-X---o---', 0.5, 0), 's': ('----X-------X---', 0.36, 0, 0.12),
            'h': ('x-o-x-o-x-o-x-o-', 0.1, 0.2)}
    bassline(s, tl, [(0, 'R', 0.9, 0.9), (1, 'R', 0.4, 0.6), (1.5, '5', 0.4, 0.7), (2, 'R', 0.9, 0.8),
                     (3, '8', 0.4, 0.7), (3.5, '5', 0.4, 0.6)], 'synbass', gain=0.34, lo=38,
             bars=(4, 28))
    melody(s, TITLE_A, 4, 'lead', gain=0.30, pan=0.05, vel=0.8)
    uke(s, tl, gain=0.22, center=66, bars=(4, 12))
    drums(s, k, 4, 12, rock, fills={11})
    fill(s, k, 11, 'snare', gain=0.3, crash_next=0.2)
    # lift: brass sings, marimba doubles, tambourine
    melody(s, TITLE_B, 12, 'brass', gain=0.26, pan=-0.05, vel=0.75)
    melody(s, TITLE_B, 12, 'marimba', gain=0.2, pan=0.3, vel=0.7, octave=1)
    arp(s, tl, [0, 1, 2, 1], 'pluck', 4, gain=0.12, pan=-0.35, bars=(12, 20))
    drums(s, k, 12, 20, dict(rock, tb=('-x-x-x-x-x-x-x-x', 0.1, -0.3)), fills={19})
    fill(s, k, 19, 'toms', crash_next=0.24)
    # chorus: the hook, big
    melody(s, chorus_d, 20, 'lead', gain=0.30, pan=0.05, vel=0.85)
    melody(s, chorus_d, 20, 'brass', gain=0.16, pan=-0.2, vel=0.7, octave=-1)
    melody(s, chorus_d, 20, 'glock', gain=0.1, pan=0.35, vel=0.55, octave=1)
    uke(s, tl, gain=0.2, center=66, bars=(20, 28))
    pads(s, tl, center=66, gain=0.06, fc=2200, bars=(20, 28))
    drums(s, k, 20, 28, dict(rock, c=('----x-------x---', 0.2, 0.1)), fills={27})
    crashes(s, k, [24], 0.18)
    fill(s, k, 27, 'toms')
    # breakdown -> build
    arp(s, tl, [0, 1, 2, 3, 2, 1], 'glock', 5, gain=0.12, pan=0.3, step=0.5, bars=(28, 36))
    arp(s, tl, [0, 2, 1, 2], 'marimba', 4, gain=0.22, pan=-0.25, step=0.5, bars=(28, 36))
    melody(s, 'r:2 B4:.5 D5:.5 G5:1 | r:2 C#5:.5 E5:.5 A5:1 | r:4 | r:2 B4:.5 D5:.5 F#5:1 | '
              'r:2 B4:.5 D5:.5 G5:1 | r:2 C#5:.5 E5:.5 A5:1 | B5:1 G5:1 E5:1 G5:1 | A5:3 r:1',
           28, 'brass', gain=0.22, vel=0.7)
    bassline(s, tl, [(0, 'R', 1.8, 0.8), (2, '5', 1.8, 0.65)], 'synbass', gain=0.32, lo=38,
             bars=(28, 36))
    drums(s, k, 28, 32, {'k': ('X-------X-------', 0.45, 0), 'h': ('x---x---x---x---', 0.08, 0.2)})
    drums(s, k, 32, 36, {'k': ('X---X---X---X---', 0.48, 0), 'h': ('x-o-x-o-x-o-x-o-', 0.1, 0.2),
                         's': ('----x-------x---', 0.3, 0, 0.12)}, fills={35})
    drums(s, k, 34, 35, {'s': ('o-o-o-o-x-x-x-x-', 0.22, 0, 0.1)})
    fill(s, k, 35, 'toms', crash_next=0.22)
    return finish_song(s, -16.5, room=0.75)


def menu():
    """D major, 104 bpm, 28 bars (65 s). The title relaxed: kalimba verse,
    the hook on flute, marimba lift."""
    s = Song(104, 28)
    tl = song_prog(s, 'Dmaj7 | Bm7 | Gmaj7 | A7sus4 A | Dmaj7 | Bm7 | Em7 | A',
                   'Dmaj7 | Bm7 A | Gmaj7 | Bm7 Gmaj7 | Dmaj7 | Bm7 A | Dmaj7 | A D',
                   'Gmaj7 | A | F#m7 | Bm7 | Gmaj7 | A | Bm A/C# | Em7 A7',
                   'Gmaj7 | A | Bm7 | A7sus4')
    pads(s, tl, center=60, gain=0.1, fc=1100, attack=1.0)
    chords_on(s, tl, [(0, 1.4, 0.5), (1.5, 0.9, 0.38), (3, 0.9, 0.4)], 'ep', center=62, count=4,
              gain=0.16, spread=0.02)
    bassline(s, tl, [(0, 'R', 1.4, 0.8), (1.5, 'R', 0.4, 0.5), (2, '5', 1.4, 0.65)], gain=0.36)
    melody(s, TITLE_A, 0, 'kalimba', gain=0.36, pan=0.1, vel=0.75)
    melody(s, transpose(HOOK_CHORUS, 2), 8, 'flute', gain=0.32, pan=0.05, vel=0.7, rev=0.4)
    melody(s, transpose(HOOK_CHORUS, 2), 8, 'musicbox', gain=0.08, pan=0.35, vel=0.5, octave=1)
    melody(s, TITLE_B, 16, 'marimba', gain=0.34, pan=0.05, vel=0.7)
    arp(s, tl, [0, 2, 1, 2], 'kalimba', 4, gain=0.12, pan=-0.3, step=1.0, bars=(16, 24))
    melody(s, 'r:2 F#6:1 D6:1 | r:2 E6:1 C#6:1 | r:2 D6:1 B5:1 | D6:2 E6:2', 24, 'musicbox',
           gain=0.18, pan=0.3, vel=0.55)
    arp(s, tl, [0, 1, 2, 3], 'harp', 3, gain=0.3, pan=-0.2, step=1.0, bars=(24, 28))
    melody(s, 'D5:1 G5:1 B5:2 | C#5:1 E5:1 A5:2 | D5:1 F#5:1 B5:2 | A4:.5 D5:.5 E5:.5 A5:1 r:1.5', 24,
           'kalimba', gain=0.32, pan=-0.05, vel=0.7)
    k = make_kit(punch=0.2, ktau=0.1)
    drums(s, k, 0, 28, {'k': ('X-------x-------', 0.28, 0), 'sh': ('o-x-o-x-o-x-o-x-', 0.1, 0.35)},
          swing=0.12)
    return finish_song(s, -18.0, room=0.82)


def race_meadow():
    """G major, 150 bpm, 40 bars (64 s). Sunny pop: square lead, marimba riff,
    ukulele, claps and tambourine."""
    s = Song(150, 40)
    k = make_kit(punch=0.55)
    riff = ('G5:.5 D5:.5 B4:.5 D5:.5 G5:.5 A5:.5 B5:1 | C6:.5 B5:.5 A5:.5 G5:.5 A5:1 D5:1')
    A = ('B4:.5 D5:.5 G5:1 G5:.5 A5:.5 B5:1 | B5:.5 A5:.5 G5:.5 E5:.5 G5:2 | '
         'E5:.5 G5:.5 C6:1 E6:.5 D6:.5 C6:1 | A5:1.5 F#5:.5 D5:2 | '
         'B4:.5 D5:.5 G5:1 G5:.5 A5:.5 B5:1 | D6:.5 C6:.5 B5:.5 G5:.5 E5:2 | '
         'C6:1 A5:1 F#5:1 A5:1 | G5:3 r:1')
    B = ('r:.5 E5:.5 G5:.5 E5:.5 C6:1 G5:1 | r:.5 F#5:.5 A5:.5 F#5:.5 D6:1 A5:1 | '
         'B5:1 F#5:.5 D5:.5 B4:1 D5:1 | E5:1.5 G5:.5 B5:2 | '
         'r:.5 E5:.5 G5:.5 E5:.5 C6:1 E6:1 | D6:1 C6:.5 B5:.5 A5:1 F#5:1 | '
         'A5:.5 G5:.5 E5:.5 C5:.5 E5:1 A5:1 | F#5:1 A5:1 C6:1 D6:1')
    tl = song_prog(s, 'G | C D | G | C D',
                   'G | Em | C | D | G | Em | Am D | G',
                   'C | D | Bm | Em | C | D | Am7 | D7',
                   'G | Em | C | D | G | Em | Am D | G',
                   'Em | C | G | D | Em | C | Am | D',
                   'G | C D | G | C D')
    pop = {'k': ('X---o-x-X-x-o---', 0.5, 0), 's': ('----X-------X---', 0.34, 0, 0.1),
           'c': ('----x-------x---', 0.16, 0.15), 'h': ('x-o-x-o-x-o-x-o-', 0.09, 0.25),
           'tb': ('-o-x-o-x-o-x-o-x', 0.09, -0.3)}
    bass8 = eighths()
    # intro + outro: the riff
    for b0 in (0, 36):
        melody(s, riff + ' | ' + riff, b0, 'xylo', gain=0.34, pan=-0.1, vel=0.8, legato=0.6)
        drums(s, k, b0, b0 + 4, {'k': ('X---X---X---X---', 0.5, 0), 'h': ('--x---x---x---x-', 0.1, 0.25),
                                 'c': ('----x-------x---', 0.18, 0.15)}, fills={b0 + 3})
        fill(s, k, b0 + 3, 'toms', crash_next=0.2)
    melody(s, riff + ' | ' + riff, 36, 'glock', gain=0.1, pan=0.3, vel=0.55, octave=1)
    bassline(s, tl, bass8, 'synbass', gain=0.32, lo=40)
    uke(s, tl, gain=0.2, center=67, bars=(4, 28))
    # A, B, A'
    melody(s, A, 4, 'lead', gain=0.30, pan=0.05, vel=0.8)
    melody(s, B, 12, 'lead', gain=0.27, pan=0.05, vel=0.75)
    melody(s, B, 12, 'marimba', gain=0.18, pan=-0.3, vel=0.65, octave=-1)
    melody(s, A, 20, 'lead', gain=0.28, pan=0.05, vel=0.8)
    melody(s, A, 20, 'glock', gain=0.1, pan=0.35, vel=0.55, octave=1)
    arp(s, tl, [0, 1, 2, 1], 'marimba', 4, gain=0.14, pan=-0.35, bars=(20, 28))
    drums(s, k, 4, 28, pop, fills={11, 19, 27})
    for b in (11, 19, 27):
        fill(s, k, b, 'snare' if b == 11 else 'toms', gain=0.32, crash_next=0.2)
    # breakdown: kalimba calls, glock answers
    melody(s, 'E5:.5 G5:.5 B5:1 r:2 | C5:.5 E5:.5 G5:1 r:2 | B4:.5 D5:.5 G5:1 r:2 | '
              'A4:.5 D5:.5 F#5:1 r:2 | E5:.5 G5:.5 B5:1 r:2 | C5:.5 E5:.5 G5:1 r:2 | '
              'A4:.5 C5:.5 E5:1 r:2 | D5:.5 F#5:.5 A5:1 r:2', 28, 'kalimba', gain=0.36, pan=-0.15)
    melody(s, 'r:2 B5:.5 A5:.5 G5:1 | r:2 G5:.5 A5:.5 E5:1 | r:2 D6:.5 B5:.5 G5:1 | '
              'r:2 A5:.5 F#5:.5 D5:1 | r:2 B5:.5 C6:.5 D6:1 | r:2 E6:.5 D6:.5 C6:1 | '
              'r:2 C6:.5 B5:.5 A5:1 | r:2 F#5:.5 G5:.5 A5:1', 28, 'glock', gain=0.2, pan=0.3,
           vel=0.65)
    pads(s, tl, center=64, gain=0.07, fc=1600, bars=(28, 36))
    drums(s, k, 28, 36, {'k': ('X-------X-------', 0.42, 0), 'c': ('----x-------x---', 0.16, 0.15),
                         'h': ('--x---x---x---x-', 0.08, 0.25)}, fills={35})
    fill(s, k, 35, 'snare', gain=0.3, crash_next=0.2)
    return finish_song(s, -16.5, room=0.7)


def race_forest():
    """E minor (dorian), 144 bpm, 40 bars (67 s). Flute and horn calls over
    pizzicato, toms, woodblocks and congas."""
    s = Song(144, 40)
    k = make_kit(punch=0.4, toms=(230, 165, 110))
    A = ('E5:1 G5:.5 A5:.5 B5:2 | A5:.5 B5:.5 A5:.5 F#5:.5 D5:2 | '
         'E5:1 G5:.5 A5:.5 G5:1 E5:1 | F#5:1.5 E5:.5 D5:2 | '
         'E5:1 G5:.5 A5:.5 B5:1.5 D6:.5 | D6:1 B5:1 G5:1 B5:1 | '
         'C#6:1 A5:.5 E5:.5 A5:1 C#6:1 | B5:2 A5:1 F#5:1')
    B = ('G4:1 C5:1 E5:1.5 D5:.5 | D5:1 B4:1 G4:2 | A4:1 D5:1 F#5:1.5 E5:.5 | E5:3 r:1 | '
         'G5:1 E5:1 C5:1.5 E5:.5 | D5:1 G5:1 B5:2 | A5:1 E5:.5 C5:.5 A4:1 C5:1 | '
         'B4:1 D#5:1 F#5:1 A5:1')
    tl = song_prog(s, 'Em | D | C | D',
                   'Em | D | C | D | Em | G | A | B7',
                   'C | G | D | Em | C | G | Am | B7',
                   'Em | D | C | D | Em | G | A | B7',
                   'Em | Em | D | D | C | C | B7 | B7',
                   'Em | D | C | D')
    tribal = {'k': ('X-------X--x----', 0.45, 0), 't3': ('X-----x---X-----', 0.3, -0.3, 0.12),
              't2': ('---x------x--x--', 0.24, 0.0, 0.12), 't1': ('------x-------x-', 0.2, 0.3, 0.12),
              'sh': ('xoxoxoxoxoxoxoxo', 0.08, 0.35), 'wb': ('--x---x-x--x--x-', 0.1, -0.4)}
    groove = {'k': ('X-------X--x----', 0.45, 0), 's': ('----x-------x---', 0.26, 0, 0.15),
              'cgh': ('--x--x----x--x--', 0.16, 0.35), 'cgl': ('x-----x-x-----x-', 0.18, -0.3),
              'sh': ('xoxoxoxoxoxoxoxo', 0.08, 0.35), 'wb': ('--------------x-', 0.1, -0.4)}
    arp(s, tl, [0, 2, 3, 2, 1, 2, 3, 2], 'pizz', 3, gain=0.42, pan=-0.2,
        vels=[0.8, 0.5, 0.6, 0.5, 0.65, 0.5, 0.6, 0.5])
    bassline(s, tl, [(0, 'R', 1.4, 0.85), (1.5, 'R', 0.4, 0.55), (2.5, '5', 0.9, 0.7),
                     (3.5, 'R', 0.4, 0.55)], 'marimba', gain=0.5, lo=40)
    bassline(s, tl, [(0, 'R', 1.4, 0.7), (2.5, '5', 1.4, 0.6)], gain=0.28, lo=28)
    drums(s, k, 0, 4, tribal)
    melody(s, A, 4, 'flute', gain=0.40, pan=0.1, vel=0.8, rev=0.35)
    drums(s, k, 4, 12, groove, fills={11})
    fill(s, k, 11, 'toms', crash_next=0.15)
    melody(s, B, 12, 'brass', gain=0.28, pan=-0.05, vel=0.75, rev=0.35)
    pads(s, tl, center=60, gain=0.08, fc=1200, bars=(12, 20))
    drums(s, k, 12, 20, tribal, fills={19})
    fill(s, k, 19, 'toms', crash_next=0.15)
    melody(s, A, 20, 'flute', gain=0.36, pan=0.1, vel=0.8, rev=0.35)
    melody(s, A, 20, 'marimba', gain=0.22, pan=-0.3, vel=0.65, octave=-1)
    drums(s, k, 20, 28, groove, fills={27})
    fill(s, k, 27, 'toms')
    melody(s, 'E4:.5 E4:.5 G4:.5 E4:.5 B4:1 A4:1 | G4:.5 A4:.5 B4:.5 G4:.5 E4:2 | '
              'D4:.5 D4:.5 F#4:.5 D4:.5 A4:1 F#4:1 | F#4:.5 G4:.5 A4:.5 F#4:.5 D4:2 | '
              'C4:.5 C4:.5 E4:.5 C4:.5 G4:1 E4:1 | E4:.5 F#4:.5 G4:.5 E4:.5 C4:2 | '
              'B3:.5 D#4:.5 F#4:.5 A4:.5 B4:1 A4:1 | F#4:.5 A4:.5 B4:.5 D#5:.5 F#5:2',
           28, 'xylo', gain=0.36, pan=0.1, vel=0.8, octave=1, legato=0.5)
    drums(s, k, 28, 36, tribal, fills={35})
    fill(s, k, 35, 'toms', crash_next=0.15)
    melody(s, 'E5:1 B4:1 E5:1 G5:1 | F#5:2 D5:2 | E5:1 G5:1 C6:1.5 B5:.5 | A5:2 F#5:2', 36,
           'brass', gain=0.26, vel=0.75)
    drums(s, k, 36, 40, groove)
    return finish_song(s, -16.5, room=0.8, damp=0.45)


def race_beach():
    """F major, 140 bpm, 40 bars (69 s). Tropical: steel drum, marimba
    off-beats, congas, shaker and a four-on-the-floor kick."""
    s = Song(140, 40)
    k = make_kit(punch=0.45)
    riff = 'A5:.5 C6:.5 r:.5 A5:.5 F5:.5 G5:.5 A5:1 | Bb5:.5 A5:.5 G5:.5 F5:.5 G5:1 C5:1'
    A = ('C5:.5 F5:.5 A5:.5 F5:.5 C6:1 A5:1 | Bb5:.5 A5:.5 G5:.5 F5:.5 D5:2 | '
         'E5:.5 G5:.5 C6:.5 Bb5:.5 A5:.5 G5:.5 E5:1 | F5:1.5 A5:.5 C6:2 | '
         'C5:.5 F5:.5 A5:.5 F5:.5 C6:1 D6:1 | D6:.5 C6:.5 Bb5:.5 A5:.5 G5:1 F5:1 | '
         'G5:.5 A5:.5 Bb5:1 E5:.5 F5:.5 G5:1 | F5:3 r:1')
    B = ('D5:.75 F5:.75 Bb5:.5 r:.5 A5:.5 Bb5:1 | C6:.75 Bb5:.75 G5:.5 r:.5 E5:.5 C5:1 | '
         'E5:.75 A5:.75 C6:.5 r:.5 G5:.5 A5:1 | F5:1.5 E5:.5 D5:2 | '
         'D5:.75 F5:.75 Bb5:.5 r:.5 C6:.5 D6:1 | E6:.75 D6:.75 C6:.5 r:.5 Bb5:.5 G5:1 | '
         'Bb5:1 G5:.5 F5:.5 D5:1 F5:1 | E5:1 G5:1 Bb5:1 C6:1')
    tl = song_prog(s, 'F | Bb C | F | Bb C',
                   'F | Bb | C | F | F | Bb | Gm C | F',
                   'Bb | C | Am | Dm | Bb | C | Gm7 | C7',
                   'F | Bb | C | F | F | Bb | Gm C | F',
                   'Dm | Bb | F | C | Dm | Bb | Gm | C7',
                   'F | Bb C | F | Bb C')
    soca = {'k': ('X---X---X---X---', 0.46, 0), 'c': ('----x-------x---', 0.14, 0.1),
            'h': ('--x---x---x---x-', 0.08, 0.25), 'sh': ('oxoxoxoxoxoxoxox', 0.08, 0.35),
            'cgh': ('---x--x----x-x--', 0.16, 0.4), 'cgl': ('x-----x-x-------', 0.16, -0.35)}
    bassline(s, tl, [(0, 'R', 0.7, 0.9), (0.75, 'R', 0.2, 0.5), (1.5, '5', 0.4, 0.7),
                     (2, 'R', 0.7, 0.85), (2.75, '8', 0.2, 0.5), (3.5, '5', 0.4, 0.7)],
             'synbass', gain=0.34, lo=36)
    chords_on(s, tl, [(0.5, 0.3, 0.5), (1.5, 0.3, 0.45), (2.5, 0.3, 0.5), (3.5, 0.3, 0.45)],
              'marimba', center=65, count=3, gain=0.16, pan=-0.25)
    for b0 in (0, 36):
        melody(s, riff + ' | ' + riff, b0, 'steel', gain=0.4, pan=0.05, vel=0.8)
    drums(s, k, 0, 40, soca, fills={11, 19, 27, 35})
    for b in (11, 19, 27, 35):
        fill(s, k, b, 'toms', gain=0.32, crash_next=0.14)
    melody(s, A, 4, 'steel', gain=0.44, pan=0.05, vel=0.85)
    melody(s, B, 12, 'marimba', gain=0.36, pan=0.1, vel=0.8)
    melody(s, B, 12, 'steel', gain=0.16, pan=-0.3, vel=0.6, octave=-1)
    melody(s, A, 20, 'steel', gain=0.4, pan=0.05, vel=0.85)
    melody(s, A, 20, 'kalimba', gain=0.14, pan=0.35, vel=0.6, octave=1)
    uke(s, tl, pattern=[(0.5, 'D', 0.6), (1.5, 'U', 0.5), (2.5, 'D', 0.6), (3.5, 'U', 0.5)],
        gain=0.16, center=69, bars=(12, 28), mute=0.5)
    melody(s, 'r:2 A5:.5 F5:.5 D5:1 | r:2 F5:.5 D5:.5 Bb4:1 | r:2 C6:.5 A5:.5 F5:1 | '
              'r:2 G5:.5 E5:.5 C5:1 | r:2 D6:.5 A5:.5 F5:1 | r:2 D6:.5 Bb5:.5 F5:1 | '
              'r:2 Bb5:.5 G5:.5 D5:1 | r:1 E5:.5 G5:.5 Bb5:1 C6:1', 28, 'steel', gain=0.38, vel=0.8)
    arp(s, tl, [0, 1, 2, 1], 'marimba', 4, gain=0.16, pan=0.3, step=0.5, bars=(28, 36))
    return finish_song(s, -16.5, room=0.65)


def race_lagoon():
    """A major, 146 bpm, 40 bars (66 s). Bouncy and watery: soft lead,
    bloop plucks, kalimba, octave bass, swung hats and bubbles."""
    s = Song(146, 40)
    k = make_kit(punch=0.4, stone=230)
    riff = 'A5:.5 E5:.5 A5:.5 C#6:.5 r:.5 B5:.5 A5:1 | F#5:.5 A5:.5 B5:.5 G#5:.5 r:.5 E5:.5 B5:1'
    A = ('E5:.5 r:.5 A5:.5 r:.5 C#6:.5 B5:.5 A5:1 | F#5:.5 r:.5 A5:.5 r:.5 C#6:1 B5:1 | '
         'D6:.5 C#6:.5 B5:.5 A5:.5 F#5:1 A5:1 | G#5:1.5 F#5:.5 E5:2 | '
         'E5:.5 r:.5 A5:.5 r:.5 C#6:.5 D6:.5 E6:1 | C#6:.5 r:.5 A5:.5 r:.5 F#5:1 A5:1 | '
         'B5:.5 C#6:.5 D6:1 B5:.5 G#5:.5 E5:1 | A5:3 r:1')
    B = ('F#5:2 A5:1 D6:1 | C#6:1.5 B5:.5 G#5:2 | E5:2 G#5:1 C#6:1 | B5:1.5 A5:.5 F#5:2 | '
         'F#5:1 A5:1 D6:1 F#6:1 | E6:1.5 D6:.5 B5:2 | D6:1 B5:1 F#5:1 A5:1 | A5:2 G#5:2')
    tl = song_prog(s, 'A | D E | A | D E',
                   'A | F#m | D | E | A | F#m | Bm E | A',
                   'D | E | C#m | F#m | D | E | Bm7 | E7sus4 E7',
                   'A | F#m | D | E | A | F#m | Bm E | A',
                   'F#m | D | A | E | F#m | D | Bm | E',
                   'A | D E | A | D E')
    bounce = {'k': ('X-----x-X--x----', 0.46, 0), 's': ('----X-------X---', 0.3, 0, 0.15),
              'h': ('x.o.x.o.x.o.x.o.', 0.08, 0.25), 'sh': ('--x---x---x---x-', 0.08, -0.35)}
    bassline(s, tl, [(0, 'R', 0.35, 0.9), (0.5, '8', 0.3, 0.6), (1, 'R', 0.35, 0.75),
                     (1.5, '8', 0.3, 0.6), (2, '5', 0.35, 0.8), (2.5, '8', 0.3, 0.6),
                     (3, 'R', 0.35, 0.75), (3.5, '8', 0.3, 0.6)], 'sqbass', gain=0.3, lo=33)
    arp(s, tl, [0, 2, 1, 2, 3, 2, 1, 2], 'bloop', 5, gain=0.16, pan=0.0, pan_lfo=0.6,
        vels=[0.8, 0.5, 0.6, 0.5, 0.7, 0.5, 0.6, 0.5])
    chords_on(s, tl, [(0, 1.4, 0.5), (1.5, 0.4, 0.4), (2.5, 1.2, 0.45)], 'ep', center=64, count=3,
              gain=0.12, spread=0.02, bars=(4, 36))
    for b0 in (0, 36):
        melody(s, riff + ' | ' + riff, b0, 'kalimba', gain=0.4, pan=-0.1, vel=0.8)
    drums(s, k, 0, 40, bounce, swing=0.18, fills={11, 19, 27, 35})
    for b in (11, 19, 27, 35):
        fill(s, k, b, 'mix', gain=0.3, crash_next=0.12)
    melody(s, A, 4, 'softlead', gain=0.42, pan=0.05, vel=0.8, legato=0.8)
    melody(s, B, 12, 'sweetbell', gain=0.26, pan=0.1, vel=0.75)
    melody(s, B, 12, 'softlead', gain=0.2, pan=-0.1, vel=0.65, octave=-1)
    melody(s, A, 20, 'softlead', gain=0.38, pan=0.05, vel=0.8, legato=0.8)
    melody(s, A, 20, 'kalimba', gain=0.18, pan=0.35, vel=0.6, octave=0)
    melody(s, 'C#6:2 A5:2 | D6:2 F#5:2 | E6:2 C#6:2 | B5:4 | C#6:2 A5:2 | F#6:2 D6:2 | '
              'D6:2 B5:2 | G#5:2 B5:2', 28, 'sweetbell', gain=0.24, pan=0.2, vel=0.7)
    sprinkle(s, tl, 'bloop', per_bar=3, octave=6, gain=0.1, rev=0.5)
    return finish_song(s, -16.5, room=0.78)


def race_canyon():
    """A minor, 138 bpm, 40 bars (70 s). Desert western: twang guitar, banjo
    rolls, whistle, boom-chick bass and galloping woodblocks."""
    s = Song(138, 40)
    k = make_kit(punch=0.35, stone=180, snap=0.3)
    riff = ('E5:.5 E5:.5 A5:1 r:.5 G5:.5 E5:1 | D5:.5 D5:.5 G5:1 r:.5 F5:.5 D5:1 | '
            'C5:.5 C5:.5 F5:1 r:.5 E5:.5 C5:1 | B4:1 G#4:1 E4:1 r:1')
    A = ('A4:.5 C5:.5 E5:1 E5:.5 D5:.5 C5:1 | B4:.5 D5:.5 G5:1 G5:.5 F5:.5 D5:1 | '
         'A4:.5 C5:.5 F5:1 F5:.5 E5:.5 C5:1 | B4:1.5 G#4:.5 E4:2 | '
         'A4:.5 C5:.5 E5:1 A5:1 G5:1 | G5:.5 F5:.5 E5:.5 D5:.5 B4:1 G4:1 | '
         'A4:1 C5:1 B4:1 G#4:1 | A4:3 r:1')
    B = ('E5:1 G5:1 C6:1.5 B5:.5 | B5:1 G5:1 D5:2 | C6:1 A5:1 E5:1.5 G5:.5 | G#5:3 r:1 | '
         'A5:1 C6:1 F6:1.5 E6:.5 | E6:1 C6:1 G5:2 | F5:1 A5:1 B5:1 G#5:1 | A5:3 r:1')
    tl = song_prog(s, 'Am | G | F | E7',
                   'Am | G | F | E7 | Am | G | F E7 | Am',
                   'C | G | Am | E7 | F | C | Dm E7 | Am',
                   'Am | G | F | E7 | Am | G | F E7 | Am',
                   'Am | Am | Dm | Dm | Am | Am | E7 | E7',
                   'Am | G | F | E7')
    gallop = {'k': ('X-------X-------', 0.42, 0), 's': ('----o-------o---', 0.24, 0, 0.12),
              'wb': ('x-oox-oox-oox-oo', 0.12, 0.35), 'wb2': ('--------------x-', 0.1, -0.35),
              'tb': ('--x---x---x---x-', 0.08, -0.3)}
    bassline(s, tl, [(0, 'R', 0.9, 0.9), (2, '5', 0.9, 0.75)], 'bass', gain=0.46, lo=33)
    chords_on(s, tl, [(1, 0.4, 0.55), (3, 0.4, 0.5)], 'pluck', center=60, count=3, gain=0.18,
              pan=-0.2, spread=0.015)
    for b0 in (0, 36):
        melody(s, riff, b0, 'twang', gain=0.42, pan=0.05, vel=0.85)
    drums(s, k, 0, 40, gallop, fills={11, 19, 35})
    for b in (11, 19, 35):
        fill(s, k, b, 'toms', gain=0.3)
    melody(s, A, 4, 'twang', gain=0.42, pan=0.05, vel=0.85)
    arp(s, tl, [0, 1, 2, 3, 1, 2, 3, 2], 'banjo', 4, gain=0.14, pan=-0.35, step=0.5, bars=(4, 12))
    melody(s, B, 12, 'whistle', gain=0.24, pan=0.05, vel=0.7, rev=0.4)
    arp(s, tl, [0, 1, 2, 3, 1, 2, 3, 2], 'banjo', 4, gain=0.16, pan=-0.35, step=0.5, bars=(12, 20))
    melody(s, A, 20, 'twang', gain=0.38, pan=0.05, vel=0.85)
    melody(s, A, 20, 'whistle', gain=0.12, pan=0.3, vel=0.55, octave=1)
    melody(s, 'A3:.5 A3:.5 C4:.5 A3:.5 E4:1 D4:1 | C4:.5 A3:.5 G3:.5 A3:.5 A3:2 | '
              'D4:.5 D4:.5 F4:.5 D4:.5 A4:1 G4:1 | F4:.5 D4:.5 C4:.5 D4:.5 D4:2 | '
              'A3:.5 A3:.5 C4:.5 A3:.5 E4:1 D4:1 | C4:.5 A3:.5 G3:.5 A3:.5 A3:2 | '
              'E4:.5 E4:.5 G#4:.5 E4:.5 B4:1 G#4:1 | G#4:.5 E4:.5 D4:.5 B3:.5 E4:2', 28, 'twang',
           gain=0.42, vel=0.85, octave=1)
    arp(s, tl, [0, 1, 2, 3, 1, 2, 3, 2], 'banjo', 5, gain=0.13, pan=0.35, step=0.5, bars=(28, 36))
    return finish_song(s, -16.5, room=0.7)


def race_swamp():
    """D minor, 128 bpm, 36 bars (68 s). Mysterious but fun: funky synth bass,
    organ, sneaky plucks, claps and frog croaks."""
    s = Song(128, 36)
    k = make_kit(punch=0.5, stone=190)
    A = ('D5:.5 F5:.5 r:.5 A5:.5 G#5:.5 A5:.5 r:1 | C6:.5 A5:.5 r:.5 F5:.5 E5:.5 D5:.5 r:1 | '
         'B4:.5 D5:.5 r:.5 F5:.5 E5:.5 F5:.5 r:1 | G5:.5 F5:.5 D5:.5 B4:.5 G4:2 | '
         'D5:.5 F5:.5 r:.5 A5:.5 G#5:.5 A5:.5 r:.5 D6:.5 | C6:.5 A5:.5 F5:.5 D5:.5 F5:1 A5:1 | '
         'D5:.5 F5:.5 Ab5:1 C#5:.5 E5:.5 G5:1 | D5:2 r:2')
    B = ('F5:1.5 D5:.5 A5:2 | G5:1.5 E5:.5 C#5:2 | D5:1 F5:1 A5:1 C6:1 | A5:3 r:1 | '
         'F5:1.5 D5:.5 A5:1.5 Bb5:.5 | C#6:1.5 A5:.5 E5:2 | F5:1 D5:1 Bb4:1 G4:1 | '
         'A4:1 C#5:1 E5:1 G5:1')
    tl = song_prog(s, 'Dm7 | Dm7 | Bb7 | A7',
                   'Dm7 | Dm7 | G7 | G7 | Dm7 | Dm7 | Bb7 A7 | Dm7',
                   'Bbmaj7 | A7 | Dm7 | Dm7 | Bbmaj7 | A7 | Gm7 | A7',
                   'Dm7 | Dm7 | G7 | G7 | Dm7 | Dm7 | Bb7 A7 | Dm7',
                   'Dm7 | Dm7 | G7 | A7',
                   'Dm7 | Dm7 | Bb7 | A7')
    # funky bass riff in minor-pentatonic steps from each chord root
    RIFF = [(0, 0, .75), (0, .75, .25), (3, 1.5, .5), (5, 2.25, .25), (7, 2.5, .5), (10, 3, .5)]
    for beat, ch, beats in tl:
        r = ch.bass_note(38)
        for semi, ob, d in RIFF:
            if ob >= beats - 1e-6:
                continue
            m = r + semi if beats >= 4 or semi < 7 else r + semi - 12
            s.add(beat + ob, synbass(hz(m), s.dur(beat + ob, d) * 0.9, hv(0.85 if ob == 0 else 0.7),
                                     0.55, tau=0.06), 0.42, 0, 0.05)
    funk = {'k': ('X-----x-X-x-----', 0.48, 0), 's': ('----X--.-.--X--.', 0.3, 0, 0.12),
            'c': ('----x-------x---', 0.12, 0.15), 'h': ('xoxoxoxoxoxoxoxo', 0.07, 0.25)}
    drums(s, k, 0, 36, funk, fills={11, 19, 27})
    for b in (11, 19, 27):
        fill(s, k, b, 'mix', gain=0.3, crash_next=0.12)
    chords_on(s, tl, [(0.5, 0.25, 0.6), (2.5, 0.25, 0.55)], 'organ', center=62, count=3,
              gain=0.12, spread=0.0, pan=0.2, bars=(0, 12))
    melody(s, A, 4, 'synpluck', gain=0.32, pan=0.05, vel=0.8)
    melody(s, A, 4, 'marimba', gain=0.14, pan=-0.3, vel=0.6, octave=-1)
    melody(s, B, 12, 'organ', gain=0.24, pan=0.05, vel=0.7)
    pads(s, tl, center=57, gain=0.07, fc=900, bars=(12, 20))
    melody(s, A, 20, 'synpluck', gain=0.3, pan=0.05, vel=0.8)
    melody(s, A, 20, 'xylo', gain=0.14, pan=0.35, vel=0.6)
    chords_on(s, tl, [(0.5, 0.25, 0.6), (1.75, 0.25, 0.5), (2.5, 0.25, 0.55)], 'organ', center=62,
              count=3, gain=0.11, spread=0.0, pan=0.2, bars=(20, 28))
    arp(s, tl, [0, 1, 2, 3, 2, 1, 2, 3], 'marimba', 3, gain=0.26, pan=-0.2, bars=(28, 36))
    melody(s, 'r:3 A5:.5 G#5:.5 | A5:1 r:3 | r:3 B5:.5 A#5:.5 | B5:1 r:1 C#6:1 E6:1 | '
              'r:3 A5:.5 G#5:.5 | A5:1 r:3 | r:2 F5:.5 G5:.5 Ab5:1 | A5:1 C#6:1 E6:1 G6:1', 28,
           'synpluck', gain=0.24, pan=0.3, vel=0.7)
    # frog croaks: ribbit = two quick dropping boings
    for bar in range(36):
        if bar % 2 == 1:
            for j, ob in enumerate((3.25, 3.5)):
                n = ns(0.09)
                t = S.tvec(n)
                c = S.sine(hz('A3') * (1.25 - 0.3 * t / 0.09) * (1 + 0.15 * np.sin(2 * np.pi * 40 * t)), n)
                s.add(bar * 4 + ob, c * S.perc(n, 0.004, 0.035) * (0.9 - 0.2 * j), 0.18, -0.5, 0.2)
    return finish_song(s, -16.5, room=0.8, damp=0.5)


def race_snow():
    """E major, 152 bpm, 40 bars (63 s). Bright: bells and glockenspiel,
    sleigh bells, pizzicato, light drums."""
    s = Song(152, 40)
    k = make_kit(punch=0.4, stone=220)
    riff = 'E6:.5 B5:.5 G#5:.5 B5:.5 E6:.5 F#6:.5 G#6:1 | A6:.5 G#6:.5 F#6:.5 E6:.5 F#6:1 B5:1'
    A = ('G#5:.5 B5:.5 E6:1 F#6:.5 E6:.5 B5:1 | C#6:.5 E6:.5 G#6:1 F#6:.5 E6:.5 C#6:1 | '
         'A5:.5 C#6:.5 E6:1 C#6:.5 B5:.5 A5:1 | B5:1.5 A5:.5 F#5:2 | '
         'G#5:.5 B5:.5 E6:1 F#6:.5 E6:.5 B5:1 | G#5:.5 C#6:.5 E6:1 G#6:1 F#6:1 | '
         'F#6:.5 E6:.5 C#6:.5 A5:.5 D#6:1 B5:1 | E6:3 r:1')
    B = ('E5:.5 A5:.5 C#6:1.5 B5:.5 A5:1 | F#5:.5 B5:.5 D#6:1.5 C#6:.5 B5:1 | '
         'D#5:.5 G#5:.5 B5:1.5 F#5:.5 G#5:1 | E5:3 r:1 | '
         'E5:.5 A5:.5 C#6:1.5 B5:.5 C#6:1 | D#6:.5 F#6:.5 B6:1.5 A6:.5 F#6:1 | '
         'G#6:1 E6:1 F#6:1 C#6:1 | B5:1 D#6:1 F#6:1 A6:1')
    tl = song_prog(s, 'E | A B | E | A B',
                   'E | C#m | A | B | E | C#m | F#m B | E',
                   'A | B | G#m | C#m | A | B | C#m F#m | B7',
                   'E | C#m | A | B | E | C#m | F#m B | E',
                   'C#m | A | E | B | C#m | A | F#m | B',
                   'E | A B | E | A B')
    light = {'k': ('X-----x-X-------', 0.42, 0), 's': ('----X-------X---', 0.28, 0, 0.15),
             'sl': ('x-o-x-o-x-o-x-ox', 0.13, 0.3)}
    bassline(s, tl, [(0, 'R', 0.9, 0.85), (1, '5', 0.4, 0.6), (2, 'R', 0.9, 0.8), (3, '8', 0.4, 0.6)],
             'bass', gain=0.42, lo=40)
    arp(s, tl, [0, 2, 1, 2], 'pizz', 4, gain=0.34, pan=-0.25, vels=[0.75, 0.5, 0.6, 0.5])
    for b0 in (0, 36):
        melody(s, riff + ' | ' + riff, b0, 'glock', gain=0.32, pan=0.1, vel=0.75)
    drums(s, k, 0, 40, light, fills={11, 19, 27, 35})
    for b in (11, 19, 27, 35):
        fill(s, k, b, 'snare', gain=0.24, crash_next=0.12)
    melody(s, A, 4, 'sweetbell', gain=0.34, pan=0.05, vel=0.8)
    melody(s, A, 4, 'glock', gain=0.14, pan=0.3, vel=0.6)
    melody(s, B, 12, 'flute', gain=0.34, pan=0.05, vel=0.75, rev=0.4)
    melody(s, B, 12, 'musicbox', gain=0.1, pan=0.35, vel=0.5, octave=1)
    pads(s, tl, center=64, gain=0.08, fc=1500, bars=(12, 20))
    melody(s, A, 20, 'sweetbell', gain=0.3, pan=0.05, vel=0.8)
    melody(s, A, 20, 'xylo', gain=0.16, pan=-0.3, vel=0.65, octave=-1)
    arp(s, tl, [0, 1, 2, 3, 2, 1], 'musicbox', 5, gain=0.12, pan=0.3, step=0.5, bars=(28, 36))
    melody(s, 'r:2 G#6:1 E6:1 | r:2 C#6:1 A5:1 | r:2 B5:1 G#5:1 | F#5:2 D#6:2 | '
              'r:2 G#6:1 E6:1 | r:2 E6:1 C#6:1 | r:2 C#6:1 A5:1 | D#6:2 F#6:2', 28, 'bell',
           gain=0.26, vel=0.7)
    pads(s, tl, center=64, gain=0.08, fc=1300, bars=(28, 36))
    sprinkle(s, tl, 'glock', per_bar=1.5, octave=7, gain=0.06, rev=0.6)
    return finish_song(s, -16.5, room=0.82)


def race_night():
    """F minor, 142 bpm (half-time feel), 40 bars (68 s). Jungle at night:
    mellow groove, flute and e-piano, firefly music-box glints."""
    s = Song(142, 40)
    k = make_kit(punch=0.35, ktau=0.15, stone=180, snap=0.35)
    A = ('C5:1.5 Eb5:.5 G5:1 F5:1 | F5:2 Ab5:1 C6:1 | Db6:1.5 C6:.5 Bb5:1 F5:1 | F5:2 E5:2 | '
         'C5:1.5 Eb5:.5 G5:1 Ab5:1 | F5:1 C6:1 Ab5:2 | Db6:1 Bb5:1 G5:1 Eb5:1 | C5:3 r:1')
    B = ('r:.5 F5:.5 Ab5:.5 C6:1 Ab5:.5 F5:1 | r:.5 G5:.5 Bb5:.5 Eb6:1 Bb5:.5 G5:1 | '
         'r:.5 G5:.5 Bb5:.5 Eb6:1 C6:.5 G5:1 | Ab5:2 F5:2 | '
         'r:.5 F5:.5 Ab5:.5 C6:1 Db6:.5 C6:1 | r:.5 Bb5:.5 Eb6:.5 G6:1 F6:.5 Eb6:1 | '
         'Db6:1 Bb5:1 F5:1 Ab5:1 | G5:2 E5:2')
    tl = song_prog(s, 'Fm9 | Dbmaj7 | Bbm7 | C7sus4 C7',
                   'Fm9 | Dbmaj7 | Bbm7 | C7sus4 C7 | Fm9 | Dbmaj7 | Bbm7 Eb | Abmaj7',
                   'Dbmaj7 | Eb | Cm7 | Fm7 | Dbmaj7 | Eb | Bbm7 | C7sus4 C7',
                   'Fm9 | Dbmaj7 | Bbm7 | C7sus4 C7 | Fm9 | Dbmaj7 | Bbm7 Eb | Abmaj7',
                   'Fm9 | Dbmaj7 | Bbm7 | C7sus4 | Fm9 | Dbmaj7 | Bbm7 | C7',
                   'Fm9 | Dbmaj7 | Bbm7 | C7sus4 C7')
    half = {'k': ('X-------x-X-----', 0.46, 0), 's': ('--------X-------', 0.32, 0, 0.2),
            'h': ('x.o.x.o.x.o.x.o.', 0.07, 0.25), 'sh': ('--x---x---x---x-', 0.07, -0.35),
            'cgl': ('------x-------x-', 0.1, -0.4)}
    soft = {'k': ('X-------x-------', 0.4, 0), 'h': ('x.o.x.o.x.o.x.o.', 0.06, 0.25)}
    pads(s, tl, center=60, gain=0.08, fc=900, attack=1.0)
    chords_on(s, tl, [(0, 1.4, 0.5), (1.5, 0.4, 0.35), (2.5, 1.3, 0.45)], 'ep', center=63, count=4,
              gain=0.14, spread=0.02)
    bassline(s, tl, [(0, 'R', 1.4, 0.9), (1.5, 'R', 0.4, 0.55), (2.5, '5', 0.9, 0.75),
                     (3.5, '8', 0.4, 0.5)], 'bass', gain=0.48, lo=29)
    drums(s, k, 0, 28, half, fills={11, 19, 27})
    for b in (11, 19, 27):
        fill(s, k, b, 'toms', gain=0.24, crash_next=0.1)
    drums(s, k, 28, 36, soft)
    drums(s, k, 36, 40, half)
    melody(s, 'r:2 C6:1 Ab5:1 | F5:2 r:2 | r:2 Db6:1 Bb5:1 | G5:2 E5:2', 0, 'kalimba', gain=0.3,
           pan=-0.1, vel=0.7)
    melody(s, A, 4, 'flute', gain=0.42, pan=0.1, vel=0.8, rev=0.4)
    melody(s, B, 12, 'kalimba', gain=0.36, pan=0.05, vel=0.8)
    melody(s, B, 12, 'ep', gain=0.18, pan=-0.2, vel=0.6, octave=-1)
    melody(s, A, 20, 'flute', gain=0.4, pan=0.1, vel=0.8, rev=0.4)
    melody(s, A, 20, 'musicbox', gain=0.1, pan=-0.35, vel=0.5, octave=1)
    melody(s, 'C6:1 Ab5:1 r:2 | F5:1 Ab5:1 r:2 | Db6:1 Bb5:1 r:2 | G5:1 F5:1 r:2 | '
              'C6:1 Ab5:1 r:2 | F5:1 Ab5:1 r:2 | Db6:1 Bb5:1 r:2 | G5:1 Bb5:1 E5:2', 28, 'kalimba',
           gain=0.34, pan=-0.1, vel=0.75)
    melody(s, 'r:2 C6:1 Ab5:1 | F5:2 r:2 | r:2 Db6:1 Bb5:1 | G5:2 E5:2', 36, 'flute', gain=0.34,
           pan=0.1, vel=0.7)
    sprinkle(s, tl, 'musicbox', per_bar=3, octave=6, gain=0.08, rev=0.7)
    sprinkle(s, tl, 'glock', per_bar=1, octave=7, gain=0.04, rev=0.7)
    # crickets: soft high double ticks
    for bar in range(40):
        for ob in (0.75, 2.75):
            for j in range(3):
                n = ns(0.012)
                s.add(bar * 4 + ob + j * 0.06, S.sine(4600, n) * np.hanning(n), 0.025, 0.6, 0.3,
                      jitter=0)
    return finish_song(s, -16.5, room=0.88, damp=0.45)


def race_caves():
    """B minor, 150 bpm, 40 bars (64 s). Crystal shimmer: 16th-note bell
    arpeggios, saw lead, glockenspiel, big echoing drums."""
    s = Song(150, 40)
    k = make_kit(punch=0.5, ktau=0.14, stone=190)
    A = ('F#5:1 B5:1 D6:1.5 C#6:.5 | B5:1 G5:1 D5:2 | F#5:1 A5:1 D6:1.5 E6:.5 | C#6:3 r:1 | '
         'F#5:1 B5:1 D6:1.5 F#6:.5 | E6:1 D6:.5 B5:.5 G5:2 | G5:1 B5:1 E6:1 D6:1 | C#6:2 A#5:2')
    B = ('D6:.5 B5:.5 G5:.5 B5:.5 D6:1 E6:1 | E6:.5 C#6:.5 A5:.5 C#6:.5 E6:1 F#6:1 | '
         'F#6:.5 C#6:.5 A5:.5 C#6:.5 F#6:1 E6:1 | D6:2 B5:2 | '
         'D6:.5 B5:.5 G5:.5 B5:.5 D6:1 G6:1 | F#6:.5 E6:.5 C#6:.5 E6:.5 A6:1 G6:1 | '
         'G6:1 E6:1 D6:1 B5:1 | C#6:1 E6:1 A#5:2')
    tl = song_prog(s, 'Bm | G | D | A',
                   'Bm | G | D | A | Bm | G | Em | F#',
                   'G | A | F#m | Bm | G | A | Em7 | F#7',
                   'Bm | G | D | A | Bm | G | Em | F#',
                   'Bm | Bm | G | G | D | D | A | F#',
                   'Bm | G | D | A')
    big = {'k': ('X-------X-x-----', 0.48, 0), 's': ('----X-------X---', 0.3, 0, 0.35),
           'h': ('x.o.x.o.x.o.x.o.', 0.07, 0.3)}
    arp(s, tl, [0, 1, 2, 3, 2, 1, 2, 3], 'crystal', 5, gain=0.13, step=0.25, pan_lfo=0.6,
        vels=[0.8, 0.5, 0.6, 0.55, 0.7, 0.5, 0.6, 0.55])
    pads(s, tl, center=59, gain=0.09, fc=1000, attack=1.0)
    bassline(s, tl, eighths((0.9, 0.55, 0.7, 0.55, 0.85, 0.55, 0.7, 0.55)), 'synbass', gain=0.3, lo=35)
    drums(s, k, 0, 4, {'k': ('X-------X-------', 0.45, 0), 'h': ('x.o.x.o.x.o.x.o.', 0.07, 0.3)},
          fills={3})
    fill(s, k, 3, 'toms', gain=0.3, crash_next=0.14)
    drums(s, k, 4, 28, big, fills={11, 19, 27})
    for b in (11, 19, 27):
        fill(s, k, b, 'toms', gain=0.3, crash_next=0.14)
    melody(s, A, 4, 'sawlead', gain=0.24, pan=0.05, vel=0.8, rev=0.4)
    melody(s, B, 12, 'glock', gain=0.3, pan=0.1, vel=0.75)
    melody(s, B, 12, 'marimba', gain=0.2, pan=-0.25, vel=0.65, octave=-1)
    melody(s, A, 20, 'sawlead', gain=0.22, pan=0.05, vel=0.8, rev=0.4)
    melody(s, A, 20, 'bell', gain=0.12, pan=0.3, vel=0.55, octave=1)
    drums(s, k, 28, 36, {'k': ('X-------X-------', 0.38, 0), 't3': ('------x-------x-', 0.18, -0.3, 0.4),
                         'h': ('x---x---x---x---', 0.06, 0.3)})
    melody(s, 'r:2 F#6:1 D6:1 | B5:2 r:2 | r:2 G6:1 D6:1 | B5:2 r:2 | r:2 F#6:1 A6:1 | '
              'F#6:2 r:2 | r:2 E6:1 C#6:1 | A#5:2 C#6:2', 28, 'glock', gain=0.28, vel=0.7)
    drums(s, k, 36, 40, big, fills={39})
    fill(s, k, 39, 'toms', gain=0.3, crash_next=0.14)
    return finish_song(s, -16.5, room=0.92, damp=0.3)


def race_volcano():
    """C minor, 162 bpm, 44 bars (65 s). Driving: 8th-note synth bass, rock
    drums, brass and a square lead, bright major lifts."""
    s = Song(162, 44)
    k = make_kit(punch=0.6)
    A = ('G5:.5 G5:.5 C6:.5 G5:.5 Eb6:1 C6:1 | C6:.5 Ab5:.5 Eb5:.5 Ab5:.5 C6:2 | '
         'D6:.5 Bb5:.5 F5:.5 Bb5:.5 D6:1 F6:1 | Eb6:1.5 D6:.5 C6:2 | '
         'G5:.5 G5:.5 C6:.5 G5:.5 Eb6:1 F6:1 | Eb6:1 C6:.5 Ab5:.5 C6:2 | '
         'F6:.5 Eb6:.5 D6:.5 C6:.5 B5:1 D6:1 | C6:3 r:1')
    B = ('Bb4:1 Eb5:1 G5:1.5 F5:.5 | F5:1 D5:1 Bb4:2 | C5:1 Eb5:1 Ab5:1.5 G5:.5 | F5:3 r:1 | '
         'Bb4:1 Eb5:1 G5:1 Bb5:1 | D6:1.5 C6:.5 Bb5:2 | C6:1 Ab5:1 Eb5:1 C5:1 | D5:1 G5:1 B5:2')
    tl = song_prog(s, 'Cm | Ab | Bb | G',
                   'Cm | Ab | Bb | Cm | Cm | Ab | Fm G | Cm',
                   'Eb | Bb | Ab | Bb | Eb | Bb | Ab | G',
                   'Cm | Ab | Bb | Cm | Cm | Ab | Fm G | Cm',
                   'Cm | Cm | Ab | Ab | Fm | Fm | G | G',
                   'Eb | Bb | Ab | Bb | Eb | Bb | Ab | G')
    drive = {'k': ('X---X---X---X---', 0.5, 0), 's': ('----X-------X---', 0.34, 0, 0.1),
             'h': ('x-o-x-o-x-o-x-o-', 0.09, 0.25)}
    bassline(s, tl, eighths((0.9, 0.7, 0.8, 0.7, 0.85, 0.7, 0.8, 0.7)), 'synbass', gain=0.34, lo=36)
    chords_on(s, tl, [(0, 0.35, 0.8), (1.5, 0.3, 0.65), (3, 0.5, 0.7)], 'brass', center=60,
              count=3, gain=0.14, spread=0.0, bars=(0, 4))
    chords_on(s, tl, [(0, 1.8, 0.5), (2, 1.8, 0.45)], 'organ', center=60, count=3, gain=0.09,
              spread=0.0, bars=(0, 4))
    melody(s, 'G5:.5 G5:.5 C6:.5 G5:.5 Eb6:2 | C6:.5 Ab5:.5 Eb5:.5 Ab5:.5 C6:2 | '
              'D6:.5 Bb5:.5 F5:.5 Bb5:.5 D6:2 | B5:1 D6:1 G6:2', 0, 'lead', gain=0.2, vel=0.75)
    drums(s, k, 0, 4, drive, fills={3})
    fill(s, k, 3, 'toms', crash_next=0.2)
    melody(s, A, 4, 'lead', gain=0.30, pan=0.05, vel=0.8)
    chords_on(s, tl, [(0, 1.8, 0.5), (2, 1.8, 0.45)], 'organ', center=60, count=3, gain=0.09,
              spread=0.0, bars=(4, 12))
    drums(s, k, 4, 12, drive, fills={11})
    fill(s, k, 11, 'toms', crash_next=0.2)
    melody(s, B, 12, 'brass', gain=0.3, pan=0.0, vel=0.8)
    pads(s, tl, center=63, gain=0.07, fc=1800, bars=(12, 20))
    drums(s, k, 12, 20, dict(drive, c=('----x-------x---', 0.16, 0.1)), fills={19})
    fill(s, k, 19, 'toms', crash_next=0.2)
    melody(s, A, 20, 'lead', gain=0.28, pan=0.05, vel=0.8)
    melody(s, A, 20, 'xylo', gain=0.14, pan=0.3, vel=0.6)
    chords_on(s, tl, [(0, 0.35, 0.7), (1.5, 0.3, 0.6), (3, 0.3, 0.65)], 'brass', center=57,
              count=3, gain=0.1, spread=0.0, bars=(20, 28))
    drums(s, k, 20, 28, drive, fills={27})
    fill(s, k, 27, 'toms')
    # breakdown: toms + organ riff
    drums(s, k, 28, 36, {'k': ('X-------X-------', 0.46, 0), 't3': ('X--x--x---x--x--', 0.26, -0.3, 0.1),
                         't1': ('--x-----x-----x-', 0.18, 0.3, 0.1), 'h': ('x---x---x---x---', 0.08, 0.25)},
          fills={35})
    melody(s, 'G4:.5 C5:.5 Eb5:.5 G5:.5 F5:.5 Eb5:.5 D5:.5 Eb5:.5 | C5:2 G4:2 | '
              'Ab4:.5 C5:.5 Eb5:.5 Ab5:.5 G5:.5 F5:.5 Eb5:.5 F5:.5 | Eb5:2 C5:2 | '
              'F4:.5 Ab4:.5 C5:.5 F5:.5 Eb5:.5 D5:.5 C5:.5 D5:.5 | C5:2 Ab4:2 | '
              'G4:.5 B4:.5 D5:.5 G5:.5 F5:.5 D5:.5 B4:.5 D5:.5 | G5:4', 28, 'organ', gain=0.24,
           pan=0.05, vel=0.75)
    fill(s, k, 35, 'toms', crash_next=0.22)
    # climax: the lift tune on lead + brass
    melody(s, B, 36, 'lead', gain=0.26, pan=0.1, vel=0.8, octave=1)
    melody(s, B, 36, 'brass', gain=0.24, pan=-0.1, vel=0.8)
    drums(s, k, 36, 44, dict(drive, c=('----x-------x---', 0.16, 0.1)), fills={43})
    fill(s, k, 43, 'toms', crash_next=0.22)   # lands on bar 0 through the loop fold
    return finish_song(s, -16.5, room=0.7)


def race_cliffs():
    """Eb major, 140 bpm, 40 bars (69 s). Soaring and heroic: strings, brass
    melody, harp, timpani and big drums."""
    s = Song(140, 40)
    k = make_kit(punch=0.5, ktau=0.15, stone=185, snap=0.45, toms=(180, 130, 95))
    fan = 'Eb5:1 Bb4:.5 Eb5:.5 G5:2 | Ab5:1 G5:.5 F5:.5 Eb5:2 | G5:1 F5:.5 Eb5:.5 C5:2 | D5:1 F5:1 Bb5:2'
    A = ('Bb4:1 Eb5:1 G5:1.5 Bb5:.5 | Bb5:1.5 Ab5:.5 F5:2 | G5:1 C6:1 Bb5:1 G5:1 | Ab5:1.5 G5:.5 Eb5:2 | '
         'Bb4:1 Eb5:1 G5:1.5 Bb5:.5 | C6:1.5 Bb5:.5 Ab5:1 Eb5:1 | F5:1 Ab5:1 G5:1 F5:1 | Eb5:3 r:1')
    B = ('C6:2 Eb6:2 | D6:1.5 C6:.5 Bb5:2 | Bb5:2 D6:2 | C6:1 Bb5:1 G5:2 | '
         'Eb6:2 Ab6:2 | G6:1.5 F6:.5 D6:2 | Eb6:1 G6:1 F6:1 D6:1 | Eb6:3 r:1')
    tl = song_prog(s, 'Eb | Ab | Cm | Bb',
                   'Eb | Bb/D | Cm | Ab | Eb/Bb | Ab | Fm7 Bb | Eb',
                   'Ab | Bb | Gm | Cm | Ab | Bb | Cm Bb/D | Eb',
                   'Eb | Bb/D | Cm | Ab | Eb/Bb | Ab | Fm7 Bb | Eb',
                   'Cm | Ab | Eb | Bb | Cm | Ab | Fm | Bb',
                   'Eb | Ab | Cm | Bb')
    hero = {'k': ('X-----x-X-------', 0.48, 0), 's': ('----X-------X---', 0.34, 0, 0.25),
            'h': ('x-o-x-o-x-o-x-o-', 0.08, 0.25)}
    pads(s, tl, center=62, gain=0.13, fc=2000, attack=0.4)
    bassline(s, tl, [(0, 'R', 1.4, 0.9), (1.5, 'R', 0.4, 0.6), (2, '5', 0.9, 0.75), (3, 'R', 0.9, 0.7)],
             'synbass', gain=0.32, lo=34)
    arp(s, tl, [0, 1, 2, 3, 2, 1, 2, 3], 'harp', 4, gain=0.26, pan=-0.3, step=0.5,
        vels=[0.75, 0.5, 0.6, 0.55, 0.65, 0.5, 0.6, 0.55])
    for b0 in (0, 36):
        melody(s, fan, b0, 'brass', gain=0.3, vel=0.8)
        for b in range(b0, b0 + 4):
            s.add(b * 4, timpani(hz(tl_root(tl, b, 36)), 0.9), 0.32, 0, 0.2, jitter=0)
        drums(s, k, b0, b0 + 4, {'k': ('X-------X-------', 0.45, 0), 'h': ('x-o-x-o-x-o-x-o-', 0.07, 0.25)},
              fills={b0 + 3})
        fill(s, k, b0 + 3, 'toms', gain=0.34, crash_next=0.2)
    melody(s, A, 4, 'brass', gain=0.32, pan=0.0, vel=0.8)
    melody(s, A, 4, 'glock', gain=0.08, pan=0.35, vel=0.5, octave=1)
    drums(s, k, 4, 28, hero, fills={11, 19, 27})
    for b in (11, 19, 27):
        fill(s, k, b, 'mix', gain=0.34, crash_next=0.2)
    melody(s, B, 12, 'sawlead', gain=0.2, pan=0.05, vel=0.8)
    pads(s, tl, center=72, gain=0.07, fc=3000, bars=(12, 20), attack=0.3)
    melody(s, A, 20, 'brass', gain=0.3, pan=-0.1, vel=0.8)
    melody(s, A, 20, 'sawlead', gain=0.14, pan=0.15, vel=0.7, octave=1)
    melody(s, 'r:2 G5:1 Eb5:1 | C5:2 r:2 | r:2 Bb5:1 G5:1 | F5:2 D5:2 | r:2 Eb6:1 C6:1 | '
              'Ab5:2 r:2 | r:2 C6:1 Ab5:1 | F5:2 D5:2', 28, 'glock', gain=0.24, vel=0.7)
    drums(s, k, 28, 32, {'k': ('X-------X-------', 0.42, 0), 'h': ('x---x---x---x---', 0.06, 0.25)})
    drums(s, k, 32, 36, {'k': ('X-------X-x-----', 0.45, 0), 's': ('----x-------x---', 0.28, 0, 0.25),
                         'h': ('x-o-x-o-x-o-x-o-', 0.07, 0.25)}, fills={35})
    for b in range(32, 36):
        s.add(b * 4 + 3, timpani(hz(tl_root(tl, b, 36)), 0.7), 0.22, 0, 0.2, jitter=0)
    return finish_song(s, -16.5, room=0.85, damp=0.35)


def tl_root(tl, bar, lo, meter=4):
    for beat, ch, beats in tl:
        if beat <= bar * meter < beat + beats:
            return ch.bass_note(lo)
    return lo


FINALE_A = ('E5:.5 G5:.5 C6:.5 G5:.5 E5:.5 G5:.5 C6:1 | C6:.5 B5:.5 A5:.5 E5:.5 A5:2 | '
            'F5:.5 A5:.5 C6:.5 A5:.5 F5:.5 A5:.5 D6:1 | D6:.5 C6:.5 B5:.5 G5:.5 D5:2 | '
            'E5:.5 G5:.5 C6:.5 G5:.5 E6:1 D6:1 | C6:.5 B5:.5 A5:.5 G5:.5 E5:2 | '
            'F5:.5 A5:.5 D6:1 B5:.5 D6:.5 G6:1 | E6:3 r:1')
FINALE_B = ('C5:.5 F5:.5 A5:1 G5:.5 F5:.5 C5:1 | B4:.5 D5:.5 G5:1 F5:.5 D5:.5 B4:1 | '
            'B4:.5 E5:.5 G5:1 A5:.5 G5:.5 E5:1 | C5:1 E5:1 A5:2 | '
            'C5:.5 F5:.5 A5:1 C6:1 A5:1 | B5:.5 A5:.5 G5:.5 F5:.5 D5:2 | '
            'C5:1 E5:1 D5:1 G5:1 | C5:2 r:1 G4:1')
HOOK_CHORDS = 'C | Am G | F | Am F | C | Am G | C | G C'


def race_finale():
    """C major, 156 bpm, 44 bars (68 s). Valle Rex: the big one. Lead,
    brass, strings, choir, timpani; the Dino Kart hook as the chorus."""
    s = Song(156, 44)
    k = make_kit(punch=0.6, toms=(200, 150, 105))
    tl = song_prog(s, 'C | Am G | C | Am G',
                   'C | Am | F | G | C | Am | Dm G | C',
                   'F | G | Em | Am | F | G | Am G/B | C',
                   HOOK_CHORDS,
                   'Am | F | C | G | Am | F | Dm | G',
                   HOOK_CHORDS)
    rock = {'k': ('X---x-x-X---x---', 0.5, 0), 's': ('----X-------X--o', 0.34, 0, 0.15),
            'h': ('x-o-x-o-x-o-x-o-', 0.09, 0.25)}
    big = dict(rock, c=('----x-------x---', 0.16, 0.1))
    pads(s, tl, center=64, gain=0.1, fc=2200, attack=0.4)
    bassline(s, tl, eighths(), 'synbass', gain=0.32, lo=36)
    # intro: hook on brass + timpani
    melody(s, ' | '.join([HOOK_OPEN, HOOK_OPEN]), 0, 'brass', gain=0.3, vel=0.85)
    melody(s, ' | '.join([HOOK_OPEN, HOOK_OPEN]), 0, 'glock', gain=0.1, pan=0.3, vel=0.6, octave=1)
    for b in range(4):
        s.add(b * 4, timpani(hz(tl_root(tl, b, 36)), 0.9), 0.3, 0, 0.2, jitter=0)
    drums(s, k, 0, 4, {'k': ('X-------X-------', 0.48, 0), 'h': ('x-o-x-o-x-o-x-o-', 0.08, 0.25)},
          fills={3})
    fill(s, k, 3, 'mix', crash_next=0.22)
    # A: fast lead verse with brass stabs
    melody(s, FINALE_A, 4, 'lead', gain=0.28, pan=0.05, vel=0.8)
    chords_on(s, tl, [(0, 0.3, 0.75), (1.5, 0.3, 0.6), (3, 0.3, 0.65)], 'brass', center=58,
              count=3, gain=0.1, spread=0.0, bars=(4, 12))
    drums(s, k, 4, 12, rock, fills={11})
    fill(s, k, 11, 'snare', gain=0.32, crash_next=0.2)
    # B: brass + choir
    melody(s, FINALE_B, 12, 'brass', gain=0.3, vel=0.8)
    pads(s, tl, center=62, count=3, gain=0.22, bars=(12, 20), inst='choir')
    arp(s, tl, [0, 1, 2, 1], 'marimba', 4, gain=0.16, pan=-0.3, bars=(12, 20))
    drums(s, k, 12, 20, rock, fills={19})
    fill(s, k, 19, 'toms', crash_next=0.24)
    # chorus: the hook
    melody(s, HOOK_CHORUS, 20, 'lead', gain=0.3, pan=0.05, vel=0.85, octave=1)
    melody(s, HOOK_CHORUS, 20, 'brass', gain=0.24, pan=-0.15, vel=0.8)
    melody(s, HOOK_CHORUS, 20, 'glock', gain=0.08, pan=0.35, vel=0.5, octave=1)
    pads(s, tl, center=64, count=3, gain=0.18, bars=(20, 28), inst='choir')
    drums(s, k, 20, 28, big, fills={27})
    crashes(s, k, [24], 0.18)
    fill(s, k, 27, 'toms')
    # build: strings ostinato, toms, hook fragments
    arp(s, tl, [0, 1, 2, 1, 0, 1, 2, 3], 'pizz', 4, gain=0.4, pan=-0.2, step=0.5, bars=(28, 36))
    melody(s, 'r:2 E5:.5 A5:.5 C6:1 | r:2 F5:.5 A5:.5 C6:1 | r:2 G5:.5 C6:.5 E6:1 | '
              'r:2 G5:.5 B5:.5 D6:1 | r:2 E5:.5 A5:.5 C6:1 | r:2 F5:.5 A5:.5 C6:1 | '
              'D6:1 C6:1 A5:1 F5:1 | G5:1 B5:1 D6:1 G6:1', 28, 'glock', gain=0.24, vel=0.7)
    melody(s, 'r:4 | r:4 | r:4 | r:4 | G4:.5 C5:.5 E5:.5 G5:1 r:1.5 | r:4 | '
              'A4:.5 D5:.5 F5:.5 A5:1 G5:.5 F5:.5 E5:.5 | D5:4', 28, 'brass', gain=0.26, vel=0.8)
    drums(s, k, 28, 32, {'k': ('X-------X-------', 0.46, 0), 't3': ('X-----x---X-----', 0.24, -0.3, 0.12),
                         'h': ('x---x---x---x---', 0.07, 0.25)})
    drums(s, k, 32, 36, {'k': ('X---X---X---X---', 0.48, 0), 't2': ('--x---x---x---x-', 0.2, 0, 0.12),
                         's': ('----x-------x---', 0.28, 0, 0.15), 'h': ('x-o-x-o-x-o-x-o-', 0.08, 0.25)},
          fills={35})
    for b in range(28, 36, 2):
        s.add(b * 4, timpani(hz(tl_root(tl, b, 36)), 0.8), 0.26, 0, 0.2, jitter=0)
    fill(s, k, 35, 'mix', crash_next=0.24)
    # final chorus: everything
    melody(s, HOOK_CHORUS, 36, 'lead', gain=0.28, pan=0.05, vel=0.85, octave=1)
    melody(s, HOOK_CHORUS, 36, 'brass', gain=0.26, pan=-0.15, vel=0.85)
    melody(s, HOOK_CHORUS, 36, 'xylo', gain=0.12, pan=0.35, vel=0.6, octave=1)
    pads(s, tl, center=64, count=3, gain=0.2, bars=(36, 44), inst='choir')
    uke(s, tl, gain=0.16, center=67, bars=(36, 44))
    drums(s, k, 36, 44, big, fills={43})
    crashes(s, k, [40], 0.18)
    fill(s, k, 43, 'toms')
    return finish_song(s, -16.5, room=0.78)


def battle():
    """G minor, 120 bpm, 32 bars (64 s). Arena: punchy riff, claps, synth
    bass, brass stabs."""
    s = Song(120, 32)
    k = make_kit(punch=0.7, ktau=0.11)
    R1 = 'G5:.5 r:.25 G5:.25 Bb5:.5 G5:.5 C6:.5 Bb5:.5 G5:1 | F5:.5 r:.25 F5:.25 G5:.5 F5:.5 D5:1 r:1'
    R2 = 'Eb5:.5 r:.25 Eb5:.25 G5:.5 Eb5:.5 Bb5:.5 G5:.5 Eb5:1 | D5:.5 r:.25 D5:.25 F#5:.5 A5:.5 D6:1 r:1'
    B = ('C5:1 Eb5:1 G5:1.5 F5:.5 | F#5:1 A5:1 D6:2 | D6:1 Bb5:1 G5:1.5 A5:.5 | Bb5:3 r:1 | '
         'C6:1 Bb5:.5 G5:.5 Eb5:1 G5:1 | A5:1 F#5:.5 D5:.5 A4:1 D5:1 | Eb5:1 G5:1 Bb5:1 G5:1 | '
         'A5:2 F#5:2')
    tl = song_prog(s, 'Gm | F | Eb | D',
                   'Gm | F | Eb | D | Gm | F | Eb | D',
                   'Cm | D | Gm | Eb | Cm | D | Eb | D',
                   'Gm | F | Eb | D | Gm | F | Eb | D',
                   'Gm | F | Eb | D')
    punch = {'k': ('X--x--x-X--x----', 0.55, 0), 's': ('----X-------X---', 0.3, 0, 0.1),
             'c': ('----X-------X---', 0.22, 0.1), 'h': ('x-x-x-x-x-x-x-o-', 0.09, 0.25)}
    bassline(s, tl, [(0, 'R', 0.35, 0.95), (0.75, 'R', 0.2, 0.6), (1.5, 'R', 0.35, 0.8),
                     (2.5, '8', 0.35, 0.75), (3, 'R', 0.35, 0.8), (3.5, '5', 0.35, 0.7)],
             'sqbass', gain=0.34, lo=31)
    drums(s, k, 0, 4, {'k': ('X---X---X---X---', 0.55, 0), 'c': ('----X-------X---', 0.2, 0.1)},
          fills={3})
    fill(s, k, 3, 'mix', crash_next=0.2)
    chords_on(s, tl, [(0, 0.3, 0.8), (0.75, 0.25, 0.6), (2.5, 0.3, 0.7)], 'brass', center=58,
              count=3, gain=0.11, spread=0.0, bars=(0, 4))
    for b0 in (4, 20):
        melody(s, ' | '.join([R1, R2, R1, R2]), b0, 'lead', gain=0.28, pan=0.05, vel=0.85)
        drums(s, k, b0, b0 + 8, punch, fills={b0 + 7})
        fill(s, k, b0 + 7, 'toms', crash_next=0.2)
    melody(s, ' | '.join([R1, R2, R1, R2]), 20, 'brass', gain=0.16, pan=-0.2, vel=0.75, octave=-1)
    melody(s, B, 12, 'brass', gain=0.3, vel=0.85)
    chords_on(s, tl, [(0, 1.8, 0.5), (2, 1.8, 0.45)], 'organ', center=60, count=3, gain=0.08,
              spread=0.0, bars=(12, 20))
    drums(s, k, 12, 20, dict(punch, tb=('-x-x-x-x-x-x-x-x', 0.08, -0.3)), fills={19})
    fill(s, k, 19, 'toms', crash_next=0.2)
    drums(s, k, 28, 32, {'k': ('X-------X-x-----', 0.5, 0), 'c': ('----X-------X---', 0.22, 0.1),
                         't3': ('------x-------x-', 0.22, -0.3, 0.1)}, fills={31})
    melody(s, 'G4:.5 Bb4:.5 D5:.5 G5:.5 r:2 | F4:.5 A4:.5 C5:.5 F5:.5 r:2 | '
              'Eb4:.5 G4:.5 Bb4:.5 Eb5:.5 r:2 | D4:.5 F#4:.5 A4:.5 D5:.5 F#5:1 A5:1', 28, 'synpluck',
           gain=0.3, vel=0.8)
    fill(s, k, 31, 'snare', gain=0.3, crash_next=0.2)
    return finish_song(s, -16.5, room=0.65)


# ---------------------------------------------------------------- jingles (not looped)

def win():
    """1st-3rd place: bright brass fanfare, ~4 s."""
    s = Song(150, 2.5, tail=1.8, loop=False)
    k = make_kit(punch=0.5)
    tl = timeline(s, 'C | F G | C')
    mel = 'C5:.5 E5:.5 G5:.5 C6:.5 r:.5 G5:.5 C6:1 | A5:.5 B5:.5 C6:.5 D6:.5 E6:2'
    melody(s, mel, 0, 'brass', gain=0.34, vel=0.85)
    melody(s, mel, 0, 'lead', gain=0.14, pan=0.1, vel=0.7, octave=1)
    melody(s, mel, 0, 'glock', gain=0.1, pan=0.3, vel=0.6, octave=1)
    for j, m in enumerate(['C4', 'G4', 'C5', 'E5', 'G5']):
        s.add(8 + j * 0.02, brass(hz(m), s.dur(8, 2), 0.75), 0.18, -0.4 + 0.2 * j, 0.35, jitter=0)
    s.add(8, glock(hz('C7'), 0.5), 0.3, 0.3, 0.4, jitter=0)
    s.add(8, crash(1.0), 0.18, 0.2, 0.3, jitter=0)
    s.add(8, timpani(hz('C2'), 0.9), 0.35, 0, 0.2, jitter=0)
    bassline(s, tl, eighths(), 'synbass', gain=0.3, lo=36, bars=(0, 2))
    s.add(8, synbass(hz('C2'), 1.0, 0.9), 0.32, 0, 0.1, jitter=0)
    drums(s, k, 0, 2, {'k': ('X---X---X---X---', 0.5, 0), 's': ('----X-------X---', 0.3, 0, 0.1),
                       'h': ('x-x-x-x-x-x-x-x-', 0.08, 0.25)}, fills={1})
    fill(s, k, 1, 'snare', gain=0.3)
    pads(s, tl, center=64, gain=0.1, fc=2200, attack=0.3)
    return finish_song(s, -16.0, room=0.75, fade_out=0.8, length=4.4)


def finish_jingle():
    """Other places: gentle and warm, ~3 s."""
    s = Song(120, 1.5, tail=1.8, loop=False)
    tl = timeline(s, 'G D | G')
    melody(s, 'B4:.5 D5:.5 G5:1 F#5:.5 E5:.5 D5:1 G5:2', 0, 'marimba', gain=0.4, vel=0.8)
    melody(s, 'r:4 B5:2', 0, 'glock', gain=0.14, pan=0.3, vel=0.55)
    pads(s, tl, center=62, gain=0.12, fc=1200, attack=0.3)
    for j, m in enumerate(['G3', 'D4', 'G4', 'B4', 'D5']):
        s.add(4 + j * 0.04, kalimba(hz(m), 0.6), 0.22, -0.3 + 0.15 * j, 0.45, jitter=0)
    s.add(0, bass(hz('G2'), 1.0, 0.7), 0.35, 0, 0.1, jitter=0)
    s.add(2, bass(hz('D2'), 0.9, 0.6), 0.32, 0, 0.1, jitter=0)
    s.add(4, bass(hz('G2'), 1.4, 0.7), 0.35, 0, 0.1, jitter=0)
    return finish_song(s, -17.5, room=0.8, fade_out=0.9, length=3.4)


def podium():
    """Cup ceremony: the Dino Kart hook as a fanfare, ~8 s."""
    s = Song(140, 4.5, tail=1.8, loop=False)
    k = make_kit(punch=0.5, toms=(200, 150, 105))
    tl = timeline(s, 'C | Am G | C | G C | C')
    hook = ' | '.join([HOOK_OPEN, HOOK_CLOSE])
    melody(s, hook, 0, 'brass', gain=0.32, vel=0.85)
    melody(s, hook, 0, 'lead', gain=0.16, pan=0.1, vel=0.75, octave=1)
    melody(s, hook, 0, 'glock', gain=0.1, pan=0.3, vel=0.6, octave=1)
    pads(s, tl, center=64, count=3, gain=0.16, inst='choir')
    pads(s, tl, center=60, gain=0.08, fc=2000, attack=0.3)
    bassline(s, tl, [(0, 'R', 1.8, 0.85), (2, '5', 1.8, 0.7)], 'synbass', gain=0.32, lo=36, bars=(0, 4))
    arp(s, tl, [0, 1, 2, 3, 2, 1, 2, 3], 'harp', 4, gain=0.2, pan=-0.3, bars=(0, 4))
    s.add(0, timpani(hz('C2'), 0.9), 0.32, 0, 0.2, jitter=0)
    s.add(0, crash(1.0), 0.16, 0.2, 0.3, jitter=0)
    drums(s, k, 0, 4, {'k': ('X-------X-------', 0.45, 0), 's': ('----x-------x---', 0.26, 0, 0.15),
                       'h': ('x-o-x-o-x-o-x-o-', 0.07, 0.25)}, fills={3})
    fill(s, k, 3, 'snare', gain=0.3)
    for j, m in enumerate(['C4', 'G4', 'C5', 'E5', 'G5', 'C6']):
        s.add(16 + j * 0.02, brass(hz(m), s.dur(16, 2), 0.8), 0.16, -0.4 + 0.16 * j, 0.35, jitter=0)
    s.add(16, glock(hz('C7'), 0.5), 0.3, 0.3, 0.4, jitter=0)
    s.add(16, glock(hz('G7'), 0.4), 0.2, -0.3, 0.4, jitter=0)
    s.add(16, crash(1.0), 0.2, 0.2, 0.3, jitter=0)
    s.add(16, timpani(hz('C2'), 1.0), 0.38, 0, 0.2, jitter=0)
    s.add(16, synbass(hz('C2'), 1.2, 0.9), 0.32, 0, 0.1, jitter=0)
    return finish_song(s, -16.0, room=0.8, fade_out=1.0, length=8.4)


def rest():
    """'Time to rest': a tiny music-box lullaby, 3/4, ~6 s."""
    s = Song(92, 3, meter=3, tail=2.2, loop=False, rit=(4, 66))
    tl = timeline(s, 'C | G7 | C')
    melody(s, 'G5:1 E5:1 C5:1 | D5:1 F5:1 B4:1 | C5:3', 0, 'musicbox', gain=0.42, vel=0.7, rev=0.5)
    pads(s, tl, center=57, gain=0.12, fc=700, kind='tri', attack=0.8)
    for beat, ch, beats in tl:
        s.add(beat, kalimba(hz(ch.bass_note(48)), 0.5), 0.22, -0.2, 0.45, jitter=0)
    for j, m in enumerate(['E6', 'G6', 'C7']):
        s.add(6.5 + j * 0.6, glock(hz(m), 0.25), 0.08, 0.3, 0.6, jitter=0)
    return finish_song(s, -19.0, room=0.9, damp=0.5, fade_out=1.4, length=6.6)


TRACKS = {
    'title': title, 'menu': menu,
    'race_meadow': race_meadow, 'race_forest': race_forest, 'race_beach': race_beach,
    'race_lagoon': race_lagoon, 'race_canyon': race_canyon, 'race_swamp': race_swamp,
    'race_snow': race_snow, 'race_night': race_night, 'race_caves': race_caves,
    'race_volcano': race_volcano, 'race_cliffs': race_cliffs, 'race_finale': race_finale,
    'battle': battle,
    'win': win, 'finish': finish_jingle, 'podium': podium, 'rest': rest,
}


def main(names):
    os.makedirs(OUT, exist_ok=True)
    dump = os.environ.get('WAV')
    if dump:
        os.makedirs(SCRATCH, exist_ok=True)
    for i, (name, fn) in enumerate(TRACKS.items()):
        if names and name not in names:
            continue
        _CUR[0] = name
        S.seed(7300 + i)
        x = fn()
        write = os.path.join(OUT, name + '.ogg')
        S.write_ogg(write, x, q=OGG_Q)
        if dump:
            S.write_wav(os.path.join(SCRATCH, name + '.wav'), x)
        print('%-13s %6.2f s  %5.1f LUFS  peak %5.1f dBFS  %4d KB' % (
            name, x.shape[1] / S.SR, S.loudness(x), S.db(S.peak(x)), os.path.getsize(write) // 1024),
            flush=True)


if __name__ == '__main__':
    main(set(sys.argv[1:]))
