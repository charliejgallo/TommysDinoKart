extends Node
## The pilots: Tommy and the 20 dinos of Tommy's Dino Zoo, all free from the
## start. weight: 0 light (quick to speed up, pushed around), 1 medium,
## 2 heavy (slow to start, pushes others). scale / seat_y / seat_z fit the
## seated model into the kart. paint / paint2 are the kart's default colours.

var DRIVERS := [
	{"id": "tommy", "weight": 1, "fit": 1.0, "paint": "#ef5b4c", "paint2": "#ffd35a", "seat": "#2f6fb8"},
	{"id": "trike", "weight": 1, "fit": 1.2, "paint": "#9b7fe0", "paint2": "#ff9c4a", "seat": "#3fb6a8"},
	{"id": "trex", "weight": 2, "fit": 1.0, "paint": "#2fae6a", "paint2": "#ffe07a", "seat": "#e2577a"},
	{"id": "raptor", "weight": 0, "fit": 1.12, "paint": "#f4a640", "paint2": "#5a3d8a", "seat": "#fff1d6"},
	{"id": "brachio", "weight": 2, "fit": 1.0, "paint": "#4fb6d8", "paint2": "#ffc6dc", "seat": "#2c5aa0"},
	{"id": "ptera", "weight": 0, "fit": 1.0, "paint": "#ff8fa3", "paint2": "#4ad0e0", "seat": "#ffe9b0"},
	{"id": "plesio", "weight": 2, "fit": 1.0, "paint": "#3e8ee8", "paint2": "#a8f0ff", "seat": "#ffd35a"},
	{"id": "archaeo", "weight": 0, "fit": 1.0, "paint": "#e8635a", "paint2": "#4fc3f7", "seat": "#fff1d6"},
	{"id": "microraptor", "weight": 0, "fit": 1.0, "paint": "#3fc0a0", "paint2": "#8c5ae8", "seat": "#ffe07a"},
	{"id": "iguanodon", "weight": 1, "fit": 1.0, "paint": "#8bcf4a", "paint2": "#f08a3c", "seat": "#2f6fb8"},
	{"id": "parasaur", "weight": 1, "fit": 1.0, "paint": "#f2c14e", "paint2": "#e24a5e", "seat": "#4b8f5a"},
	{"id": "therizino", "weight": 2, "fit": 1.0, "paint": "#b07ad8", "paint2": "#ffd9a0", "seat": "#3a3346"},
	{"id": "galli", "weight": 0, "fit": 1.0, "paint": "#f7e07a", "paint2": "#ff7f50", "seat": "#4a90d9"},
	{"id": "spino", "weight": 2, "fit": 1.0, "paint": "#2b9fb3", "paint2": "#ff6f61", "seat": "#fff1d6"},
	{"id": "dilo", "weight": 1, "fit": 1.0, "paint": "#58c27d", "paint2": "#ffcf4a", "seat": "#e2577a"},
	{"id": "carno", "weight": 1, "fit": 1.0, "paint": "#d9483b", "paint2": "#262333", "seat": "#ffd35a"},
	{"id": "compy", "weight": 0, "fit": 1.0, "paint": "#a3d65c", "paint2": "#ff9ecb", "seat": "#2f6fb8"},
	{"id": "stego", "weight": 2, "fit": 1.0, "paint": "#e8a33c", "paint2": "#4fb07c", "seat": "#5a3d8a"},
	{"id": "ankylo", "weight": 2, "fit": 1.0, "paint": "#c0846a", "paint2": "#f2e2c0", "seat": "#2f6fb8"},
	{"id": "proto", "weight": 1, "fit": 1.0, "paint": "#e0b26c", "paint2": "#7cc6e8", "seat": "#d9483b"},
	{"id": "pachy", "weight": 1, "fit": 1.0, "paint": "#6aa6ff", "paint2": "#ffb3c6", "seat": "#fff1d6"},
]
var _by_id := {}

func _ready() -> void:
	if Dev.arg("drvdir") != "":
		drivers_dir = "res://assets/" + Dev.arg("drvdir")
	_reindex()
	var f := "res://data/drivers.json"
	if FileAccess.file_exists(f):
		var over: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(f))
		for d in DRIVERS:
			if over.has(d.id):
				d.merge(over[d.id], true)

func _reindex() -> void:
	for d in DRIVERS:
		_by_id[d.id] = d

## Size in the kart: drivers.py measures every pilot sitting in its drive
## pose (heights.json: top "h" and front-to-back "len", metres). The game
## scales it to a seated height for its weight class, unless it is so long
## (tails!) that it would not fit the kart; "fit" is a per-species touch.
var _heights := {}
var drivers_dir := "res://assets/drivers"
const SEAT_H := [0.84, 0.96, 1.08]    # light, medium, heavy
const MAX_LEN := 2.3

func scale_of(id: String) -> float:
	if id == "tommy":
		return 1.0
	if _heights.is_empty():
		var f := drivers_dir + "/heights.json"
		if FileAccess.file_exists(f):
			_heights = JSON.parse_string(FileAccess.get_file_as_string(f))
	var d := driver(id)
	var m: Dictionary = _heights.get(id, {"h": 1.0, "len": 1.0})
	var tgt: float = SEAT_H[d.weight] * (1.5 if id == "brachio" else 1.0)
	return minf(tgt / float(m.h), MAX_LEN / float(m.len)) * float(d.get("fit", 1.0))

func driver(id: String) -> Dictionary:
	return _by_id.get(id, DRIVERS[0])

func ids() -> Array:
	return DRIVERS.map(func(d): return d.id)

func display_name(id: String) -> String:
	return tr("driver." + id)

func kart_colors(id: String) -> Dictionary:
	var d := driver(id)
	return {"paint": Color(d.paint), "paint2": Color(d.paint2), "seat": Color(d.seat)}
