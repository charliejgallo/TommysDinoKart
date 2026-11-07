extends Node
## Settings, including the grown-ups' area (protected by a PIN or a
## grown-up question). Saved in user://settings.cfg (developer runs:
## user://dev/settings.cfg, so tests never touch the family's settings).

signal changed

const SPEEDS := [
	{"id": "turtle", "top": 13.0, "accel": 8.5},
	{"id": "normal", "top": 18.5, "accel": 11.0},
	{"id": "fast", "top": 23.5, "accel": 13.5},
	{"id": "turbo", "top": 28.5, "accel": 16.0},
]

# --- general (anyone)
var language := ""
var music_vol := 0.7
var sfx_vol := 0.85
var fullscreen := false
var quality := 2               # 0 low, 1 medium, 2 high
var split_vertical := false    # 2 players: side by side instead of top/bottom
var show_names := true
var camera_far := false
var rumble := true

# --- grown-ups' area
var pin := ""                  # "" = grown-up question instead of a PIN
var session_minutes := 0       # 0 = no limit
var items_mode := 2            # 0 racing only, 1 friendly items only, 2 all items
var speed := 1                 # index in SPEEDS
var ai_level := 1              # 0 easy, 1 normal, 2 hard
var catch_up := true           # rivals wait for / chase the players
var laps := 3
var bumping_on := true         # karts push each other
var battle_on := true          # battle mode visible
var protect_all := false       # every setting behind the grown-up gate
var assists := [               # per player: auto_accel, steer_help, no_fall
	{"auto_accel": false, "steer_help": false, "no_fall": false},
	{"auto_accel": false, "steer_help": false, "no_fall": false},
	{"auto_accel": false, "steer_help": false, "no_fall": false},
	{"auto_accel": false, "steer_help": false, "no_fall": false},
]
var gentle_hits := false       # items only slow you down, never spin
var coins_on := true

# --- play time (real time, for the session limit)
var played_today := 0.0
var played_day := ""
var session_start := 0.0

func _ready() -> void:
	Lang.load_dirs(["res://lang", "user://lang"])
	load_settings()
	if Dev.arg("lang") != "":
		language = Dev.arg("lang")
		apply()
	elif language == "":
		TranslationServer.set_locale(Lang.best_default())
	session_start = Time.get_unix_time_from_system()

func path() -> String:
	var d := "user://dev/" if Dev.is_dev() else "user://"
	DirAccess.make_dir_recursive_absolute(d)
	return d + "settings.cfg"

const KEYS := ["language", "music_vol", "sfx_vol", "fullscreen", "quality", "split_vertical", "show_names",
	"camera_far", "rumble", "pin", "session_minutes", "items_mode", "speed", "ai_level", "catch_up", "laps",
	"bumping_on", "battle_on", "protect_all", "assists", "gentle_hits", "coins_on", "played_today", "played_day"]

func load_settings() -> void:
	var cf := ConfigFile.new()
	if cf.load(path()) == OK:
		for k in KEYS:
			if cf.has_section_key("s", k):
				set(k, cf.get_value("s", k))
	var today := Time.get_date_string_from_system()
	if played_day != today:
		played_day = today
		played_today = 0.0
	apply()

func save() -> void:
	var cf := ConfigFile.new()
	for k in KEYS:
		cf.set_value("s", k, get(k))
	cf.save(path())
	changed.emit()

func apply() -> void:
	if language != "":
		TranslationServer.set_locale(language)
	_bus("Music", music_vol)
	_bus("SFX", sfx_vol)
	if not Dev.is_dev():
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED)

func _bus(name: String, v: float) -> void:
	var i := AudioServer.get_bus_index(name)
	if i < 0:
		AudioServer.add_bus()
		i = AudioServer.bus_count - 1
		AudioServer.set_bus_name(i, name)
		AudioServer.set_bus_send(i, "Master")
	AudioServer.set_bus_volume_db(i, linear_to_db(maxf(v, 0.0001)))

# ---- queries used by the race
func speed_class() -> Dictionary:
	return SPEEDS[clampi(speed, 0, SPEEDS.size() - 1)]

func items_on() -> bool:
	return items_mode > 0

func friendly_only() -> bool:
	return items_mode == 1

func assists_for(p: int) -> Dictionary:
	if p < 0 or p >= assists.size():
		return {}
	return assists[p]

func no_fall() -> bool:
	return false

func offroad_mul() -> float:
	return 0.55

func stray_limit() -> float:
	return 40.0

func bumping() -> bool:
	return bumping_on

func lose_item_on_fall() -> bool:
	return false

func decor_density() -> float:
	return [0.45, 0.75, 1.0][clampi(quality, 0, 2)]

# ---- session time
func _process(dt: float) -> void:
	played_today += dt

func session_minutes_played() -> float:
	return (Time.get_unix_time_from_system() - session_start) / 60.0

func session_over() -> bool:
	return session_minutes > 0 and session_minutes_played() >= session_minutes

func new_session() -> void:
	session_start = Time.get_unix_time_from_system()
