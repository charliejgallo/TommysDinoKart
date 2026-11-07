# Audio tools

All the sound effects and music of Tommy's Dino Kart are synthesised from
scratch in Python (numpy + ffmpeg). No samples, no downloads. The synthesiser
is a copy of Tommy's Dino Zoo's `synth.py` with a racing kit added (drums,
steel drum, synth lead, brass, organ, twang/banjo, synth bass, choir, sleigh
bells and a look-ahead limiter).

Requirements: Python 3 with numpy, and `ffmpeg` (with libvorbis) on the PATH.

## Regenerate

From the repo root:

    python3 tools/audio/gen_sfx.py          # game/assets/sfx/*.ogg   (~5 s)
    python3 tools/audio/gen_music.py        # game/assets/music/*.ogg (~2 min)
    python3 tools/audio/check_audio.py      # numeric check of everything

Pass names to regenerate only some files, for example
`python3 tools/audio/gen_music.py race_snow battle` or
`python3 tools/audio/gen_sfx.py boost coin`. With `WAV=1` the scripts also
write WAV copies to `$AUDIO_SCRATCH` (default: a `tdk_audio` folder in the
system temp dir) for listening in an editor.

Output is deterministic (fixed random seeds per file), so a rerun gives the
same audio.

## Files

- `synth.py` oscillators, envelopes, filters, reverb, instruments, `Song`
  (beat-based mixing; loops fold their reverb tail back onto the start),
  loudness (BS.1770) and OGG writing.
- `gen_sfx.py` one function per sound effect, mono, peaks at -3 dBFS
  (UI ticks lower).
- `gen_music.py` one function per track. Race loops are seamless and sit at
  about -16.5 LUFS (menu -18), with a limiter at -1.5 dBFS. `win`, `finish`,
  `podium` and `rest` are one-shot jingles. The "Dino Kart hook"
  (`HOOK_OPEN`/`HOOK_CLOSE`) appears in title, menu, race_finale and podium.
- `check_audio.py` decodes every OGG and prints duration, size, peak, RMS,
  loudness, clipping and, for loops, how cleanly the end flows into the start
  (jump/click/level at the wrap). Warnings are listed at the end.

The game sets `loop = true` on music streams when it plays a track
(`scripts/core/music.gd`), so the OGG import settings can stay at defaults.
