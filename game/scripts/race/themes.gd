class_name Themes
## Looks of the worlds: sky, light, ground colours, road kind and what grows
## around the road. A track names its theme and may override any key with
## "theme_over". Props come from assets/props (Dino Zoo) and assets/scenery.

const TOON := preload("res://shaders/toon.gdshader")
const ROAD := preload("res://shaders/road.gdshader")
const GROUND := preload("res://shaders/ground.gdshader")
const WATER := preload("res://shaders/water.gdshader")
const LAVA := preload("res://shaders/lava.gdshader")

static var _noise: NoiseTexture2D
static var _toon_cache := {}

static func C(h: String) -> Color:
	return Color(h)

static var THEMES := {
	"meadow": {
		"sky_top": C("#5fa8ec"), "sky_horizon": C("#cfe9ff"), "ground_far": C("#7fb069"),
		"fog": C("#d9efff"), "sun": C("#fff4dc"), "sun_energy": 1.3,
		"grass": C("#69bd52"), "grass2": C("#8fcf5a"), "shoulder": C("#c9a46a"),
		"road": "asphalt", "road_col": C("#7c746e"), "line_col": C("#fff6dc"),
		"curb_a": C("#ef5b4c"), "curb_b": C("#fff6ea"),
		"hills": 9.0, "hill_freq": 0.007,
		"scatter": [
			{"m": "prop_tree_round", "d": 0.0009, "min": 7.0, "s": [1.2, 2.0], "solid": 0.6},
			{"m": "prop_tree_tall", "d": 0.0005, "min": 9.0, "s": [1.3, 2.2], "solid": 0.5},
			{"m": "prop_tree_fruit", "d": 0.0003, "min": 8.0, "s": [1.2, 1.8], "solid": 0.6},
			{"m": "prop_bush", "d": 0.0016, "min": 3.0, "s": [1.0, 1.8]},
			{"m": "prop_flowers", "d": 0.004, "min": 1.5, "max": 40.0, "s": [1.0, 1.6]},
			{"m": "prop_grass_tuft", "d": 0.01, "min": 1.2, "max": 30.0, "s": [1.0, 1.7]},
			{"m": "prop_rock", "d": 0.0005, "min": 5.0, "s": [1.0, 2.2], "solid": 0.7},
			{"m": "hay_bale", "d": 0.0002, "min": 2.5, "max": 8.0, "s": [1.0, 1.2], "solid": 0.7},
			{"m": "tire_stack", "d": 0.0002, "min": 2.0, "max": 6.0, "s": [1.0, 1.1], "solid": 0.6},
		],
		"music": "race_meadow",
	},
	"forest": {
		"sky_top": C("#4f9fe0"), "sky_horizon": C("#c8ecd8"), "ground_far": C("#4f8f4a"),
		"fog": C("#cfe8d6"), "fog_density": 0.004, "sun": C("#fff0c8"), "sun_energy": 1.15, "sun_pitch": -60.0,
		"grass": C("#3f9a48"), "grass2": C("#5fb556"), "shoulder": C("#8a6a48"),
		"road": "dirt", "road_col": C("#a8805a"), "curb_a": C("#7a5a3a"), "curb_b": C("#c8a070"),
		"hills": 14.0, "hill_freq": 0.008, "music": "race_forest",
		"gate": C("#d9b88a"), "gate_acc": C("#4f9a48"),
		"scatter": [
			{"m": "prop_tree_tall", "d": 0.0028, "min": 5.0, "s": [1.4, 2.4], "solid": 0.6},
			{"m": "prop_tree_round", "d": 0.0012, "min": 5.0, "s": [1.4, 2.2], "solid": 0.6},
			{"m": "prop_giant_fern", "d": 0.0018, "min": 2.5, "s": [1.2, 2.2]},
			{"m": "prop_fern", "d": 0.006, "min": 1.5, "max": 40.0, "s": [1.2, 2.0]},
			{"m": "prop_mushroom", "d": 0.001, "min": 2.0, "max": 30.0, "s": [1.2, 2.0]},
			{"m": "prop_stump", "d": 0.0006, "min": 3.0, "s": [1.0, 1.6], "solid": 0.6},
			{"m": "prop_moss_rock", "d": 0.0006, "min": 3.0, "s": [1.0, 2.0], "solid": 0.8},
		],
	},
	"lagoon": {
		"sky_top": C("#3fa6f0"), "sky_horizon": C("#d6f6ff"), "ground_far": C("#e8d6a0"),
		"fog": C("#d8f2ff"), "fog_density": 0.0018, "sun": C("#fff6e0"), "sun_energy": 1.35,
		"grass": C("#7cc85e"), "grass2": C("#e6d39a"), "shoulder": C("#ecd9a6"),
		"road": "wood", "road_col": C("#c7955c"), "curb_a": C("#3fb6c8"), "curb_b": C("#fff6ea"),
		"hills": 3.0, "base_h": -4.0, "rim_h": -5.0, "rim_d": 7.0, "rim_w": 10.0, "edge_rise": 0.0,
		"water_deep": Color(0.1, 0.62, 0.72, 0.9), "water_shallow": Color(0.45, 0.92, 0.88, 0.8),
		"music": "race_lagoon", "pillar": C("#9a7048"), "rail": C("#e9c690"),
		"scatter": [
			{"m": "prop_palm", "d": 0.0012, "min": 3.0, "max": 30.0, "s": [1.2, 1.8], "solid": 0.4},
			{"m": "prop_palm_big", "d": 0.0006, "min": 4.0, "max": 40.0, "s": [1.2, 1.6], "solid": 0.5},
			{"m": "prop_lilypads", "d": 0.002, "min": 3.0, "s": [1.2, 2.2], "in_water": true},
			{"m": "prop_reeds", "d": 0.0015, "min": 2.0, "max": 25.0, "s": [1.0, 1.6], "in_water": true},
			{"m": "prop_beach_rock", "d": 0.0006, "min": 4.0, "s": [1.2, 2.4], "in_water": true},
			{"m": "shell_big", "d": 0.0002, "min": 3.0, "max": 20.0, "s": [0.8, 1.2]},
		],
	},
	"beach": {
		"sky_top": C("#5a7fd8"), "sky_horizon": C("#ffc79a"), "ground_far": C("#e6c890"),
		"fog": C("#ffd8b8"), "fog_density": 0.002, "sun": C("#ffc890"), "sun_energy": 1.25,
		"sun_pitch": -18.0, "sun_yaw": -150.0, "cloud_bottom": C("#ffb5a0"),
		"grass": C("#ecd6a0"), "grass2": C("#f2e2b8"), "shoulder": C("#d8b880"), "ground_pattern": 1,
		"road": "sand", "road_col": C("#d9b67e"), "curb_a": C("#ff7f6a"), "curb_b": C("#fff6ea"),
		"hills": 5.0, "base_h": -1.0, "hill_freq": 0.01, "music": "race_beach",
		"scatter": [
			{"m": "prop_palm", "d": 0.0014, "min": 3.0, "s": [1.2, 2.0], "solid": 0.4},
			{"m": "prop_palm_big", "d": 0.0008, "min": 4.0, "s": [1.2, 1.8], "solid": 0.5},
			{"m": "prop_driftwood", "d": 0.0008, "min": 2.0, "max": 30.0, "s": [1.2, 2.0]},
			{"m": "prop_beach_rock", "d": 0.0006, "min": 3.0, "s": [1.2, 2.4], "solid": 0.8},
			{"m": "beach_umbrella", "d": 0.0002, "min": 3.0, "max": 15.0, "s": [1.0, 1.2]},
			{"m": "cactus_round", "d": 0.0003, "min": 3.0, "s": [1.0, 1.5]},
		],
	},
	"canyon": {
		"sky_top": C("#4c8fe0"), "sky_horizon": C("#ffe0b8"), "ground_far": C("#c97a4a"),
		"fog": C("#ffdcb8"), "fog_density": 0.0022, "sun": C("#fff0d0"), "sun_energy": 1.4, "sun_pitch": -40.0,
		"grass": C("#d08a54"), "grass2": C("#e0a468"), "shoulder": C("#c98a58"), "rock": C("#b0563a"),
		"ground_pattern": 3,
		"road": "dirt", "road_col": C("#c27a4e"), "curb_a": C("#7a3a2a"), "curb_b": C("#f2d0a0"),
		"hills": 6.0, "rim_h": 22.0, "rim_d": 9.0, "rim_w": 7.0, "music": "race_canyon",
		"gate": C("#e8c8a0"), "gate_acc": C("#b0563a"),
		"scatter": [
			{"m": "cactus_tall", "d": 0.0006, "min": 3.0, "max": 10.0, "s": [0.9, 1.3], "solid": 0.4},
			{"m": "cactus_round", "d": 0.0008, "min": 2.0, "max": 9.0, "s": [1.0, 1.5]},
			{"m": "prop_desert_shrub", "d": 0.0014, "min": 2.0, "max": 9.0, "s": [1.0, 1.6]},
			{"m": "prop_boulder_red", "d": 0.0006, "min": 3.0, "max": 9.0, "s": [1.0, 2.0], "solid": 0.8},
			{"m": "mesa_rock", "d": 0.00006, "min": 40.0, "max": 200.0, "s": [1.5, 2.5], "far": 600.0},
		],
	},
	"swamp": {
		"sky_top": C("#6a8f8a"), "sky_horizon": C("#c8dcc0"), "ground_far": C("#4a6a44"),
		"fog": C("#b8d0b0"), "fog_density": 0.009, "sun": C("#e8f0c8"), "sun_energy": 0.95, "sun_pitch": -55.0,
		"ambient": 1.0, "saturation": 1.05,
		"grass": C("#5a7a3e"), "grass2": C("#6e8f48"), "shoulder": C("#6a5238"),
		"road": "dirt", "road_col": C("#7a6448"), "curb_a": C("#4a6a3a"), "curb_b": C("#c8c090"),
		"hills": 2.0, "base_h": -1.2, "rim_h": -2.0, "rim_d": 5.0, "rim_w": 12.0, "edge_rise": 4.0,
		"water_deep": Color(0.22, 0.36, 0.26, 0.92), "water_shallow": Color(0.42, 0.55, 0.36, 0.85),
		"music": "race_swamp", "cloud_top": C("#e0ece0"), "cloud_bottom": C("#a8b8a8"),
		"scatter": [
			{"m": "swamp_tree", "d": 0.0012, "min": 4.0, "s": [1.0, 1.6], "solid": 0.6, "in_water": true},
			{"m": "dead_tree", "d": 0.0004, "min": 4.0, "s": [1.0, 1.5], "solid": 0.4},
			{"m": "prop_reeds", "d": 0.004, "min": 1.5, "max": 30.0, "s": [1.0, 1.8], "in_water": true},
			{"m": "reeds_tall", "d": 0.0016, "min": 2.0, "max": 30.0, "s": [1.0, 1.5], "in_water": true},
			{"m": "prop_lilypads", "d": 0.003, "min": 2.0, "s": [1.0, 2.0], "in_water": true},
			{"m": "prop_mushroom", "d": 0.001, "min": 2.0, "max": 20.0, "s": [1.2, 2.0]},
		],
	},
	"snow": {
		"sky_top": C("#6aa8ec"), "sky_horizon": C("#eef6ff"), "ground_far": C("#e8f0f8"),
		"fog": C("#eef4ff"), "fog_density": 0.003, "sun": C("#fffaf0"), "sun_energy": 1.2, "sun_pitch": -35.0,
		"grass": C("#f2f6fc"), "grass2": C("#dde8f6"), "shoulder": C("#c8d4e4"), "rock": C("#8a90a0"),
		"ground_pattern": 2,
		"road": "ice", "road_col": C("#7fa6d4"), "line_col": C("#ffffff"), "curb_a": C("#3f7fd0"), "curb_b": C("#ffffff"),
		"hills": 18.0, "hill_freq": 0.006, "music": "race_snow", "gate": C("#ffffff"), "gate_acc": C("#3f7fd0"),
		"scatter": [
			{"m": "pine_snow", "d": 0.0022, "min": 5.0, "s": [1.0, 1.8], "solid": 0.6},
			{"m": "pine_snow_small", "d": 0.002, "min": 3.0, "s": [1.0, 1.5], "solid": 0.4},
			{"m": "snow_rock", "d": 0.0008, "min": 3.0, "s": [1.0, 2.0], "solid": 0.8},
			{"m": "ice_spike", "d": 0.0003, "min": 4.0, "s": [1.0, 1.6], "solid": 0.6},
			{"m": "snowman", "d": 0.0001, "min": 3.0, "max": 12.0, "s": [1.0, 1.3]},
		],
	},
	"night_jungle": {
		"sky_top": C("#0e1440"), "sky_horizon": C("#2a3a78"), "ground_far": C("#162a28"),
		"fog": C("#1e2c50"), "fog_density": 0.006, "sun": C("#a8c0ff"), "sun_energy": 0.55, "sun_pitch": -50.0,
		"ambient": 1.6, "exposure": 1.15, "sky_energy": 0.8, "cloud_count": 10,
		"cloud_top": C("#4a5a90"), "cloud_bottom": C("#2a3060"),
		"grass": C("#2f6a48"), "grass2": C("#3f7a50"), "shoulder": C("#5a4a3a"),
		"road": "stone", "road_col": C("#7a7a8a"), "curb_a": C("#ffd35a"), "curb_b": C("#3a3346"),
		"hills": 10.0, "rim_h": 6.0, "rim_d": 12.0, "rim_w": 14.0, "music": "race_night",
		"night": true, "gate": C("#c8b890"), "gate_acc": C("#5a3d8a"),
		"scatter": [
			{"m": "jungle_tree", "d": 0.002, "min": 5.0, "s": [0.9, 1.4], "solid": 0.7},
			{"m": "giant_leaf_plant", "d": 0.003, "min": 2.0, "max": 40.0, "s": [1.0, 1.6]},
			{"m": "glow_mushroom", "d": 0.0016, "min": 2.0, "max": 25.0, "s": [1.0, 1.6]},
			{"m": "glow_mushroom_big", "d": 0.0003, "min": 4.0, "max": 30.0, "s": [1.0, 1.4], "solid": 0.6},
			{"m": "firefly_lamp", "d": 0.0006, "min": 1.5, "max": 5.0, "s": [1.0, 1.2]},
			{"m": "flower_giant", "d": 0.0008, "min": 2.0, "max": 30.0, "s": [1.0, 1.4]},
		],
	},
	"caves": {
		"sky_top": C("#1a1030"), "sky_horizon": C("#4a3070"), "ground_far": C("#2a2040"),
		"fog": C("#3a2a5a"), "fog_density": 0.008, "sun": C("#c8b0ff"), "sun_energy": 0.6, "sun_pitch": -70.0,
		"ambient": 1.7, "exposure": 1.1, "sky_energy": 0.7, "clouds": false,
		"grass": C("#4a3a6a"), "grass2": C("#5a4a7a"), "shoulder": C("#6a5a80"), "rock": C("#3a2f58"),
		"ground_pattern": 3,
		"road": "crystal", "road_col": C("#7a6ab0"), "curb_a": C("#4ae0e0"), "curb_b": C("#c86aff"),
		"hills": 4.0, "rim_h": 30.0, "rim_d": 8.0, "rim_w": 6.0, "music": "race_caves",
		"night": true, "gate": C("#b8a8e8"), "gate_acc": C("#4ae0e0"),
		"scatter": [
			{"m": "crystal_cluster", "d": 0.0024, "min": 2.5, "max": 14.0, "s": [0.8, 1.5], "solid": 0.6},
			{"m": "stalagmite", "d": 0.0016, "min": 3.0, "max": 16.0, "s": [0.8, 1.5], "solid": 0.6},
			{"m": "glow_mushroom", "d": 0.0016, "min": 2.0, "max": 12.0, "s": [1.0, 1.6]},
			{"m": "crystal_big", "d": 0.0003, "min": 8.0, "s": [1.0, 1.6]},
		],
	},
	"volcano": {
		"sky_top": C("#3a1a2a"), "sky_horizon": C("#c8583a"), "ground_far": C("#2a1a1a"),
		"fog": C("#8a3a2a"), "fog_density": 0.004, "sun": C("#ffb070"), "sun_energy": 1.0, "sun_pitch": -35.0,
		"ambient": 1.2, "cloud_top": C("#6a4a4a"), "cloud_bottom": C("#3a2a2a"),
		"grass": C("#3a2a2c"), "grass2": C("#4a3434"), "shoulder": C("#5a3a30"), "rock": C("#2a2024"),
		"ground_pattern": 3,
		"road": "stone", "road_col": C("#5a4a48"), "curb_a": C("#ff6a2a"), "curb_b": C("#ffd35a"),
		"hills": 8.0, "base_h": -6.0, "hill_freq": 0.009, "lava": true, "music": "race_volcano",
		"pillar": C("#3a2a2a"), "rail": C("#ff8a3a"), "gate": C("#4a3434"), "gate_acc": C("#ff6a2a"),
		"scatter": [
			{"m": "lava_rock", "d": 0.0016, "min": 3.0, "s": [0.8, 1.6], "solid": 0.8},
			{"m": "basalt_column", "d": 0.0005, "min": 5.0, "s": [0.8, 1.4], "solid": 1.2},
			{"m": "smoke_vent", "d": 0.0004, "min": 4.0, "s": [1.0, 1.4], "solid": 0.6},
			{"m": "dead_tree", "d": 0.0004, "min": 4.0, "s": [1.0, 1.4]},
		],
	},
	"cliffs": {
		"sky_top": C("#3f8fe8"), "sky_horizon": C("#d8f0ff"), "ground_far": C("#5a9a5a"),
		"fog": C("#d8eeff"), "fog_density": 0.0016, "sun": C("#fff4e0"), "sun_energy": 1.3,
		"grass": C("#6ab858"), "grass2": C("#8ac868"), "shoulder": C("#c8b090"), "rock": C("#b8a890"),
		"road": "stone", "road_col": C("#9a8e80"), "curb_a": C("#e2577a"), "curb_b": C("#fff6ea"),
		"hills": 4.0, "base_h": 28.0, "rim_h": -36.0, "rim_d": 14.0, "rim_w": 8.0, "edge_rise": 0.0,
		"water_deep": Color(0.12, 0.42, 0.75, 0.95), "water_shallow": Color(0.35, 0.75, 0.9, 0.9),
		"music": "race_cliffs", "pillar": C("#b8a890"), "rail": C("#e8dcc8"), "margin": 220.0,
		"scatter": [
			{"m": "prop_tree_round", "d": 0.0006, "min": 4.0, "max": 13.0, "s": [1.2, 1.8], "solid": 0.6},
			{"m": "prop_flowers", "d": 0.003, "min": 1.5, "max": 12.0, "s": [1.0, 1.6]},
			{"m": "prop_grass_tuft", "d": 0.006, "min": 1.2, "max": 12.0, "s": [1.0, 1.6]},
			{"m": "stone_column", "d": 0.0003, "min": 4.0, "max": 12.0, "s": [0.7, 1.1], "solid": 0.8},
			{"m": "prop_nest_pillar", "d": 0.0001, "min": 6.0, "max": 13.0, "s": [1.0, 1.5]},
		],
	},
	"rex_valley": {
		"sky_top": C("#4a9ae8"), "sky_horizon": C("#ffe6c0"), "ground_far": C("#7a9a4a"),
		"fog": C("#ffe8d0"), "fog_density": 0.0018, "sun": C("#fff0d0"), "sun_energy": 1.35, "sun_pitch": -32.0,
		"grass": C("#7ab04a"), "grass2": C("#a8c060"), "shoulder": C("#c8a070"),
		"road": "asphalt", "road_col": C("#7a7068"), "curb_a": C("#2fae6a"), "curb_b": C("#ffe07a"),
		"hills": 16.0, "hill_freq": 0.005, "music": "race_finale",
		"gate": C("#fff3df"), "gate_acc": C("#2fae6a"),
		"scatter": [
			{"m": "prop_cycad", "d": 0.0012, "min": 4.0, "s": [1.2, 2.0], "solid": 0.4},
			{"m": "prop_palm_big", "d": 0.0006, "min": 5.0, "s": [1.2, 1.8], "solid": 0.5},
			{"m": "prop_tree_giant", "d": 0.0003, "min": 8.0, "s": [1.0, 1.6], "solid": 1.5},
			{"m": "prop_fossil", "d": 0.0003, "min": 3.0, "max": 30.0, "s": [1.2, 2.0]},
			{"m": "prop_giant_fern", "d": 0.0016, "min": 3.0, "s": [1.2, 2.0]},
			{"m": "prop_big_boulder", "d": 0.0004, "min": 5.0, "s": [1.0, 2.0], "solid": 1.2},
			{"m": "flag_pole", "d": 0.0001, "min": 3.0, "max": 6.0, "s": [1.0, 1.0]},
		],
	},
}

static func get_theme(id: String) -> Dictionary:
	if THEMES.has(id):
		return THEMES[id]
	var path := "res://data/themes/%s.json" % id
	if FileAccess.file_exists(path):
		var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
		return _colors(d)
	return THEMES["meadow"]

static func _colors(d: Dictionary) -> Dictionary:
	## JSON themes write colours as "#rrggbb" strings
	for k in d.keys():
		if d[k] is String and (d[k] as String).begins_with("#"):
			d[k] = Color(d[k])
	return d

static func noise_tex() -> NoiseTexture2D:
	if _noise == null:
		_noise = NoiseTexture2D.new()
		var fn := FastNoiseLite.new()
		fn.frequency = 0.02
		fn.fractal_octaves = 4
		_noise.noise = fn
		_noise.seamless = true
		_noise.width = 256
		_noise.height = 256
		_noise.generate_mipmaps = true
	return _noise

static func toon(c: Color, emit := 0.0) -> ShaderMaterial:
	var key := "%s|%s" % [c.to_html(), emit]
	if _toon_cache.has(key):
		return _toon_cache[key]
	var m := ShaderMaterial.new()
	m.shader = TOON
	m.set_shader_parameter("albedo", c)
	m.set_shader_parameter("emit", emit)
	_toon_cache[key] = m
	return m

static func road_material(t: Dictionary) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = ROAD
	m.set_shader_parameter("kind", {"asphalt": 0, "dirt": 1, "sand": 2, "ice": 3, "stone": 4, "wood": 5,
		"crystal": 6, "rainbow": 7}.get(t.get("road", "asphalt"), 0))
	m.set_shader_parameter("base", t.get("road_col", Color("#5b5f6e")))
	m.set_shader_parameter("line", t.get("line_col", Color("#fff6dc")))
	m.set_shader_parameter("noise_tex", noise_tex())
	return m

static func curb_material(t: Dictionary) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = ROAD
	m.set_shader_parameter("kind", 10)
	m.set_shader_parameter("base", t.get("curb_a", Color("#ef5b4c")))
	m.set_shader_parameter("line", t.get("curb_b", Color("#fff6ea")))
	m.set_shader_parameter("noise_tex", noise_tex())
	return m

static func skirt_material(t: Dictionary) -> ShaderMaterial:
	return toon(t.get("skirt", (t.shoulder as Color).darkened(0.15)))

static func ground_material(t: Dictionary) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = GROUND
	m.set_shader_parameter("noise_tex", noise_tex())
	m.set_shader_parameter("pattern", t.get("ground_pattern", 0))
	return m

static func water_material(t: Dictionary) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	if t.get("lava", false):
		m.shader = LAVA
		m.set_shader_parameter("noise_tex", noise_tex())
		return m
	m.shader = WATER
	m.set_shader_parameter("noise_tex", noise_tex())
	if t.has("water_deep"):
		m.set_shader_parameter("deep", t.water_deep)
		m.set_shader_parameter("shallow", t.water_shallow)
	return m
