# Developing Tommy's Dino Kart

Everything in this repository is text or is generated from text: the 3D
models are Python scripts for Blender, the tracks are Python that writes
JSON, the music and sounds are synthesised in Python, and the game is
Godot 4 scenes and GDScript. This page explains how the pieces fit together
and how to change or add things.

- [Requirements](#requirements)
- [Repository layout](#repository-layout)
- [How the game is put together](#how-the-game-is-put-together)
- [Art pipeline](#art-pipeline)
- [Tracks](#tracks) (format reference in [TRACKS.md](TRACKS.md))
- [Adding things](#adding-things)
- [Testing](#testing)
- [Building and releasing](#building-and-releasing)
- [Traps we fell into](#traps-we-fell-into)

## Requirements

| what | version | for |
|---|---|---|
| Godot | 4.7.2 (standard, not .NET) | playing, testing, exporting |
| Blender | 3.3 | rebuilding models (`art/blender/`) |
| Python 3 | with Pillow | tracks (`tools/tracks.py`), picture boards |
| numpy + ffmpeg (libvorbis) | | rebuilding audio (`tools/audio/`) |

The generated files (`.glb`, `.ogg`, `.png`, `.jpg`, track `.json`) are
committed, so only Godot is needed to play or to export.

```
godot --path game                 # play
godot --editor --path game        # open the editor
```

## Repository layout

```
art/blender/           model scripts (run with Blender -b -P <script>.py)
  tdz_common.py          shared primitives / materials / export (from Tommy's Dino Zoo)
  dino_lib.py, dinos.py, species_*.py, tommy.py   the Dino Zoo characters, unchanged
  drivers.py             the 21 pilots seated in a kart, with kart animations
  kart.py                kart bodies and wheels
  scenery.py, scenery_lib.py, scenery_sheet.py    track scenery + contact sheet
game/                  the Godot project
  assets/drivers/        drv_<id>.glb + heights.json (seated size of each pilot)
  assets/karts/          kart_<body>.glb, wheel_<style>.glb
  assets/props/          props shared with Tommy's Dino Zoo (trees, rocks, eggs, ptera...)
  assets/scenery/        props made for this game
  assets/sfx, music      synthesised audio (OGG)
  assets/ui/             pilot portraits and track pictures for the menus
  data/tracks/*.json     the tracks and arenas (written by tools/tracks.py)
  lang/*.po              language packs
  scenes/                title.tscn (menus), race.tscn
  scripts/core/          autoloads (settings, controls, roster, garage, session...)
  scripts/race/          everything that happens during a race
  scripts/ui/            menus and UI style
  scripts/dev/           developer scenes (lineup, portraits)
  shaders/               toon, road, ground, water, lava, clouds, boost
tools/
  tracks.py              track designer: shapes -> JSON, checks, pictures
  sample_board.py        builds the picture boards in docs/img
  audio/                 synthesiser and generators (see tools/audio/README.md)
docs/                  this documentation and its pictures
.github/workflows/     CI: exports macOS and Windows, publishes releases on tags
```

## How the game is put together

### Autoloads (`game/scripts/core/`)

| name | job |
|---|---|
| `Dev` | developer command-line switches (see [Testing](#testing)) and screenshots |
| `Lang` | reads `lang/*.po` (and `user://lang/`) into Godot translations |
| `Controls` | up to 4 players, each owning a joypad or half of the keyboard; read straight from the devices |
| `Settings` | general settings and the grown-ups' options; saved in `user://settings.cfg` |
| `Roster` | the 21 pilots: weight class, kart colours, seated scale |
| `Sfx`, `Music` | sounds and music (missing files are silent); the engine hum is made in code |
| `Garage` | coins, bought parts and each pilot's kart; `user://garage.json` |
| `Session` | what is being played now: mode, track or cup, players, standings |
| `Flow` | changes screens (menus <-> race) |

Developer runs (any `--race`, `--shot`, `--menu`... switch) keep their data
in `user://dev/` so tests never touch a family's settings, coins or ghosts.

### A race (`game/scripts/race/`)

`race.gd` (scene `race.tscn`) builds everything in `_ready`:

1. **`Track`** (`track.gd`) builds the world from `data/tracks/<id>.json`:
   - the **centre line**: a Catmull-Rom curve through the control points,
     resampled every 2 m into packed arrays (`pos`, `fwd`, `right`, `up`,
     `width`, `dist`). Everything else uses them: progress along the lap,
     the AI, respawn points, item and coin placement, the minimap.
   - the **road**: a strip of quads, curbs, and a gentle shoulder ramp on
     each side (collision included, so a kart that runs wide can drive back
     up); one trimesh collider in group `road`.
   - the **terrain**: a 2.5 m height grid that hugs the road and blends into
     the theme's landscape (hills, canyon walls, cliffs, islands);
     `HeightMapShape3D` in group `offroad` (slower driving). Under bridge
     spans the ground dips instead.
   - water or lava, sky, sun, fog, clouds from the **theme** (`themes.gd`).
   - **decoration**: props scattered in a band around the road, in 72 m
     chunks of `MultiMeshInstance3D` with a visibility range (this is what
     keeps 4-player split screen at 60 fps); trees and rocks near the road
     get cylinder colliders; set pieces placed by hand.
   - the start gate, item eggs, coins, boost pads and ramps.
2. **8 karts** (`kart.gd`, 6 in battle). Players start at the back of the
   grid. Tommy always races: as a rival when nobody picked him.
3. One **pane** per local player: `SubViewportContainer` + `SubViewport`
   sharing the world, a `RaceCam` and a `Hud`.

States: `countdown` (holding accelerate at the right moment gives a start
boost) -> `race` -> `done` (results 3.5 s after the last player finishes).

### Karts (`kart.gd`)

A `CharacterBody3D` with a sphere collider and hand-written arcade
handling. A **brain** fills `kart.inp` (throttle, brake, steer, drift, item,
back) every physics frame: `Brains.PlayerBrain` (from `Controls`),
`Brains.AIBrain` (races) or `Brains.BattleBrain` (arenas).

- Speed along the heading; yaw rate from the stick, scaled down at low speed.
- **Drift**: pressing drift while steering hops and slides; the drift time
  sets the spark level (blue, orange, pink) and the turbo on release.
- **Air**: leaving a ramp; tapping drift in the air is a trick (turbo on landing).
- Grass and sand slow you down unless boosting; walls take speed by how
  square the hit is; heavier karts push lighter ones.
- **Ptera rescue**: below the world, far off the road, or not getting
  anywhere for a while (6 s AI, 10 s players) -> the Dino Zoo pterosaur
  carries the kart back to the road.
- Progress: nearest centre-line sample (searched near the last one, so
  crossings never confuse it), lap counting with a half-lap arm so cutting
  across never counts.

### AI (`brains.gd`)

`AIBrain` aims at a point ahead on the centre line (look-ahead grows with
speed) with its own lane, cuts the inside of bends a little more with
skill, avoids karts just ahead, eases off for sharp bends, drifts only *into*
long bends and lets go when the road turns the other way, backs out when
stuck, and uses items with a small delay. `Race._catch_up` slows rivals that
are far ahead of the best player and speeds up those far behind (grown-ups
can turn it off).

### Items (`items.gd`, `egg_shot.gd`, `mud.gd`)

Surprise eggs give an item by place: leaders get defensive items, the back
of the pack gets catch-up ones. Friendly items (feather turbo, three
feathers, bubble shield, golden fern, ptera ride) are the only ones in
"friendly items" mode; attack items (bouncing egg, triple egg, seeker egg,
mud puddle, roar) need "all items". "Gentle hits" turns every spin-out into
a slow-down. Thrown eggs ride the centre line and bounce between the curbs.

### Modes

- **Grand Prix**: `Cups.CUPS` (3 cups x 4 tracks); points 15-12-10-8-6-4-2-1;
  podium page at the end.
- **Free race**: any track, then rematch / another track / another pilot.
- **Time trial**: alone with three feathers; the run is recorded at 20 Hz and
  the best one per track is saved in `user://ghosts/<track>.json` and
  replayed as a see-through kart.
- **Balloon battle**: arenas (`arena_*`), 3 balloons each, every landed hit
  pops one; 3 minutes or until one kart is left (or every player is out).
  Needs "all items" and the battle switch on.

### Menus (`scripts/ui/menus.gd`)

One scene over a small 3D showroom. Pages are built in code:
`main -> mode -> join -> pilot -> cup | track | arena -> race`, plus garage,
settings, the grown-ups' page (behind a PIN or a multiplication), after_race,
podium and rest (the session limit card). Lists use Godot focus (any
joypad or the keyboard); the join and pilot pages read each player's own
device through `Controls`.

## Art pipeline

All models: `/Applications/Blender.app/Contents/MacOS/Blender -b -P <script> -- [args]`
from `art/blender/`. Conventions (from Tommy's Dino Zoo): metres, Blender +Z
up, models face -Y (Godot +Z), origin on the ground, flat colours with
materials named by role; Godot gives everything the toon shader
(`look.gd`) and recolours roles (`paint`, `paint2`, `seat`, `hub`).

| script | makes | notes |
|---|---|---|
| `drivers.py [--only a,b] [--age sport3]` | `assets/drivers/drv_<id>.glb`, `drv_tommy_cap.glb`, `heights.json` | dinos use the `sport3` proportions (smaller head and eyes, longer snout, bigger horns, slimmer torso, no blush, focused eyelids); actions `drive`, `cheer`, `hit`, `sad`; measures each pilot's seated height and length |
| `kart.py [--only tina,wheel_basic]` | `assets/karts/kart_<body>.glb`, `wheel_<style>.glb` | bodies `tina`, `bone`, `egg`; wheels `wheel_basic`, `wheel_stone` |
| `scenery.py [--only ...] [--list]` | `assets/scenery/<name>.glb` | 41 props; glowing materials are named `glow_*` |
| `scenery_sheet.py` | `docs/img/scenery-sheet.png` | contact sheet of every prop |

The game scales every pilot from `heights.json` (`Roster.scale_of`): a
seated height per weight class, unless the pilot is so long that it would
not fit the kart; `fit` in `roster.gd` is a per-species touch.

Menu pictures are rendered by the game itself:

```
godot --path game -- --scene=portraits                      # assets/ui/portraits/*.png
godot --path game -- --race=<id> --ai-player --nohud --t=9 --shot=x.png   # track pictures
```

Audio: see `tools/audio/README.md`.

## Tracks

`tools/tracks.py` holds every track and arena as a Python function (arcs,
lines and formulas are easier there than raw numbers). Running it writes
`game/data/tracks/<id>.json`, draws `docs/img/tracks/<id>.png` (top view
coloured by height, bridges dark, plus the height profile) and checks:

- lap length and the tightest bend radius (with where it is);
- every place where the road passes near itself must be a bridge with at
  least 5.5 m between the two levels.

```
python3 tools/tracks.py          # all
python3 tools/tracks.py volcan   # one
```

The JSON format and every theme key are in [TRACKS.md](TRACKS.md).

## Adding things

**A track**: add a function with `@track` in `tools/tracks.py`, run it, add
`"track.<id>"` to `game/lang/*.po`, put it in a cup in
`scripts/core/cups.gd`, render its picture into `assets/ui/tracks/<id>.jpg`,
then run the autotest on it (below) until it reports no rescues or stuck
karts.

**A world (theme)**: add an entry in `THEMES` in `scripts/race/themes.gd`
(or a JSON file in `game/data/themes/<id>.json` with colours as `"#rrggbb"`),
see [TRACKS.md](TRACKS.md) for the keys. Music: a `music` key naming a file in
`assets/music/`.

**A pilot**: build the model with `drivers.py` (a Dino Zoo species dict, or a
new one in `species_*.py`), add it to `DRIVERS` in `scripts/core/roster.gd`
with a weight class and kart colours, add `"driver.<id>"` to the `.po`
files, re-render the portraits.

**A kart body or wheels**: a function in `kart.py` (keep the material roles),
then an entry in `Garage.CHASSIS` / `Garage.WHEELS` with a price.

**An item**: roll weights in `Items.TABLE`, behaviour in `Items.use`, a
picture in `Hud.ItemIcon._draw`, and an entry in `FRIENDLY` if it never
hurts anyone.

**A language**: copy `game/lang/en.po` to `game/lang/<code>.po`, set
`X-Language-Name` in the header and translate the `msgstr` lines. The source
language is Spanish (`msgid`s are the Spanish text, or keys like
`driver.trike`, `track.bosque`, `cup.fern`). Players can also drop `.po`
files into `user://lang/`. The settings page lists whatever exists.

## Testing

The game has its own test drivers on the command line (all listed at the
top of `scripts/core/dev.gd`):

```
# 8 AI karts race a whole race at 8x speed; prints places, lap times,
# every ptera rescue and every stuck kart, then quits
godot --headless --path game -- --race=bosque --ai-player --autotest=8

# battle and time trial
godot --headless --path game -- --race=arena_isla --mode=battle --ai-player --autotest=8
godot --headless --path game -- --race=pradera --mode=time --ai-player --autotest=8

# follow one kart (index in the grid) every half second
godot --headless --path game -- --race=laguna --ai-player --autotest=8 --trace=0

# screenshots: race (4 players), menus, and the menu flow driven by keys
godot --path game -- --race=selva --ai-player --players=4 --t=8 --shot=/tmp/a.png --fps
godot --path game -- --menu=parents --lang=es --shot=/tmp/b.png
godot --path game -- --keys=enter,wait:1,enter,wait:1.5,space,wait:1,right,enter,wait:1.2,enter --shot-after=22 --shot=/tmp/c.png
```

Before a release: the autotest on every track should show no rescues, no
stuck karts and no DNF. On an Apple M2 the game holds 60 fps with one player
and with four (`--fps` prints frames, draw calls and primitives).

Don't use `--t` to skip time by stepping physics by hand: raycasts and
floors only update when the physics server steps. `--t` and `--autotest`
raise `Engine.time_scale` instead.

## Building and releasing

`game/export_presets.cfg` has two presets, `macOS` (universal, ad-hoc
signed zip) and `Windows` (one `.exe` with the game embedded). Export
templates for 4.7.2 must be installed; the macOS export needs
`textures/vram_compression/import_etc2_astc=true` (already set).

```
godot --headless --path game --import
godot --headless --path game --export-release "macOS" "../dist/TommysDinoKart-macOS.zip"
godot --headless --path game --export-release "Windows" "../dist/windows/TommysDinoKart.exe"
```

CI (`.github/workflows/build.yml`) does the same on every push to `main`
and uploads both zips as artifacts; pushing a tag `v*` also publishes a
GitHub release with them.

## Traps we fell into

- Godot's fallback locale is English. Spanish is the source language here,
  so `locale/fallback="es"` is set in `project.godot`; without it Spanish
  players saw English for every string missing from `es.po`.
- The AI used to start drifts in the correction of an S-bend and slide into
  the lagoon: it now drifts only into the bend and releases when the road
  turns the other way.
- A small step between the road edge and the terrain trapped karts that ran
  wide: the shoulder is now a gentle ramp with collision.
- Before the first crossing of the start line, distance along the lap must
  be negative (the grid is behind the line), or the ranking and the stuck
  detector think every kart is a lap ahead.
- Scattering every tree of the map in one `MultiMesh` drew 32 million
  triangles per frame: decoration is chunked with a visibility range, and
  small props cast no shadow.
- Blender 3.3's glTF exporter drops constant rotation channels with the
  size optimisation: `tommy.quaternion_actions()` keeps held poses.
