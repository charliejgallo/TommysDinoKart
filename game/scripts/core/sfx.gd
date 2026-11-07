extends Node
## Sound effects (assets/sfx/<name>.wav, made by tools/audio/gen_sfx.py) and
## the kart engine loop. Missing files are silent, never an error.

var _cache := {}
var _engine: AudioStreamWAV
var _ui: AudioStreamPlayer

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_ui = AudioStreamPlayer.new()
	_ui.bus = "SFX"
	add_child(_ui)

func stream(name: String) -> AudioStream:
	if _cache.has(name):
		return _cache[name]
	var s: AudioStream = null
	for ext in ["wav", "ogg"]:
		var p := "res://assets/sfx/%s.%s" % [name, ext]
		if ResourceLoader.exists(p):
			s = load(p)
			break
	_cache[name] = s
	return s

func play(name: String, vol := 0.0, pitch := 1.0) -> void:
	var s := stream(name)
	if s == null:
		return
	var p := AudioStreamPlayer.new()
	p.stream = s
	p.volume_db = vol
	p.pitch_scale = pitch
	p.bus = "SFX"
	add_child(p)
	p.play()
	p.finished.connect(p.queue_free)

func play_at(name: String, at: Vector3, vol := 0.0) -> void:
	var s := stream(name)
	if s == null:
		return
	var tree := get_tree()
	if tree == null or tree.current_scene == null:
		return
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.volume_db = vol
	p.unit_size = 8.0
	p.max_distance = 90.0
	p.pitch_scale = randf_range(0.95, 1.05)
	p.bus = "SFX"
	tree.current_scene.add_child(p)
	p.global_position = at
	p.play()
	p.finished.connect(p.queue_free)

func ui(name: String) -> void:
	var s := stream(name)
	if s:
		_ui.stream = s
		_ui.play()

## A small two-stroke "putt-putt" loop, made once in code (22 kHz, 0.5 s);
## the kart changes its pitch with speed.
func engine_stream() -> AudioStreamWAV:
	if _engine:
		return _engine
	var rate := 22050
	var n := rate / 2
	var data := PackedByteArray()
	data.resize(n * 2)
	var f0 := 48.0
	var ph := 0.0
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in n:
		var t := float(i) / rate
		ph += f0 / rate
		var pulse := pow(maxf(sin(TAU * ph), 0.0), 6.0)
		var buzz := sin(TAU * ph * 2.0) * 0.35 + sin(TAU * ph * 3.0) * 0.18
		var v := (pulse * 0.7 + buzz * 0.4) * 0.5 + rng.randf_range(-0.04, 0.04) * pulse
		var s := int(clampf(v, -1.0, 1.0) * 26000.0)
		data.encode_s16(i * 2, s)
	_engine = AudioStreamWAV.new()
	_engine.format = AudioStreamWAV.FORMAT_16_BITS
	_engine.mix_rate = rate
	_engine.data = data
	_engine.loop_mode = AudioStreamWAV.LOOP_FORWARD
	_engine.loop_begin = 0
	_engine.loop_end = n
	return _engine
