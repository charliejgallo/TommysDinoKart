# Tracks and worlds: format reference

Tracks are written by `tools/tracks.py` into `game/data/tracks/<id>.json`
and built when a race starts by `game/scripts/race/track.gd`. Coordinates
are Godot's: metres, x to the right, z towards the viewer, y up.

## Track JSON

| key | type | meaning |
|---|---|---|
| `id` | string | file name and translation key `track.<id>` |
| `theme` | string | a world from `themes.gd` (or `data/themes/<id>.json`) |
| `theme_over` | object | overrides any theme key for this track only |
| `pts` | list | closed loop of control points `[x, z, y, width, bank]`; `bank` (degrees, + = right edge up) is optional. The lap runs in point order and the start line is at the first point |
| `bridges` | list | `[[i0, i1], ...]` spans of control points built as bridges: railings, pillars, the ground dips under them and the shoulders are not drivable |
| `items` | list | fractions of the lap with a row of surprise eggs (3 or 4 across) |
| `coins` | list | fractions with a line of 5 coins; by default 0.09 after each item row |
| `boosts` | list | boost pads: a fraction, or `[fraction, lateral offset m]` |
| `ramps` | list | jump ramps: a fraction, or `[fraction, lateral, width m]` |
| `water` | number | water (or lava, if the theme says so) level |
| `kill_y` | number | below this height a kart is rescued (default: under the water / lowest ground) |
| `set` | list | set pieces `{"m": model, "p": [x, z], "s": scale, "r": yaw°, "y": height, "solid": collider radius}` |
| `scatter` | list | extra scatter rules, added to the theme's |
| `arena` | bool | a battle arena: karts spawn around the ring, no coins |

Models are looked up in `assets/props/` and then `assets/scenery/` by name.
Don't give arches a `solid` radius: the collider would block the road.

## Theme keys

Colours are `Color`s in `themes.gd`, `"#rrggbb"` strings in JSON.

| key | default | meaning |
|---|---|---|
| `sky_top`, `sky_horizon`, `ground_far` | | procedural sky colours |
| `sky_energy` | 1.0 | sky brightness |
| `fog`, `fog_density` | , 0.0022 | fog colour and density |
| `sun`, `sun_energy`, `sun_pitch`, `sun_yaw` | , 1.25, -52, 35 | the sun (or moon) |
| `ambient`, `exposure`, `saturation` | 0.9, 1.0, 1.12 | light and colour grading |
| `clouds`, `cloud_count`, `cloud_top`, `cloud_bottom` | true, 26 | far cartoon clouds |
| `grass`, `grass2`, `shoulder`, `rock` | | terrain colours (mixed by noise; near the road; steep slopes) |
| `ground_pattern` | 0 | 0 grass, 1 sand ripples, 2 snow sparkle, 3 rock strata |
| `road` | `asphalt` | `asphalt`, `dirt`, `sand`, `ice`, `stone`, `wood`, `crystal`, `rainbow` |
| `road_col`, `line_col` | | road and painted line colours |
| `curb_a`, `curb_b`, `curbs` | , , true | curb stripes; `curbs: false` for flat edges |
| `hills`, `hill_freq`, `base_h` | 10, 0.006, 0 | the landscape away from the road |
| `rim_h`, `rim_d`, `rim_w` | 0, 20, 10 | a rise (canyon walls, +) or drop (cliffs, islands, -) of `rim_h` metres starting `rim_d` metres past the road edge, over `rim_w` metres |
| `edge_rise`, `margin` | 14, 170 | the bowl that hides the edge of the world; how far the terrain reaches |
| `water`, `water_deep`, `water_shallow`, `lava` | | water level and colours; `lava: true` uses the lava shader |
| `music` | `race_meadow` | file in `assets/music/` |
| `gate`, `gate_acc` | | start gate posts and banner colours |
| `pillar`, `rail` | | bridge pillars and railings |
| `night` | false | a night world (glowing props carry it) |
| `scatter` | | list of scatter rules, below |

### Scatter rules

`{"m": "prop_tree_round", "d": 0.0009, "min": 7.0, "max": 110.0, "s": [1.2, 2.0], "solid": 0.6}`

| key | meaning |
|---|---|
| `m` | model name |
| `d` | instances per square metre of the band around the road |
| `min`, `max` | distance from the road edge (max defaults to 110 m) |
| `s` | random scale range |
| `solid` | trunk collider radius (times the scale) for instances near the road |
| `in_water` | allowed below the water level (reeds, lily pads, swamp trees) |
| `far` | visibility distance for big landmarks (default 150-270 m by quality) |

## The tracks

| id | world | lap | notes |
|---|---|---|---|
| `pradera` | meadow | 859 m | the zoo, a hill, a jump on the last straight |
| `bosque` | forest | 995 m | figure of eight; the high lobe crosses on a log bridge |
| `laguna` | lagoon | 1133 m | wooden boardwalks and bridges over the water |
| `playa` | beach | 997 m | sunset, sand road, two jumps |
| `canon` | canyon | 1171 m | high red walls on both sides |
| `pantano` | swamp | 1233 m | misty causeways between pools |
| `nevado` | snow | 1118 m | switchbacks up 30 m, overpass, icy descent |
| `selva` | night jungle | 1253 m | glowing mushrooms, stone road |
| `cuevas` | caves | 979 m | crystal gorge spiralling down |
| `volcan` | volcano | 1225 m | bridge over the lava lake, up around the crater |
| `acantilado` | cliffs | 991 m | 30 m over the sea, stone arch, two cliff bridges |
| `valle_rex` | Rex valley | 1338 m | the finale: bone arch, T-Rex statue, three boosts |
| `arena_patio`, `arena_isla`, `arena_crater`, `arena_templo` | | ~230 m rings | balloon battle |
