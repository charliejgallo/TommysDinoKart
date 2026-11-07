extends Node
## Background music (assets/music/<name>.ogg, made by tools/audio/gen_music.py).
## Missing files are silent.

var _p: AudioStreamPlayer
var _cur := ""

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_p = AudioStreamPlayer.new()
	_p.bus = "Music"
	add_child(_p)

func play_track(name: String) -> void:
	if name == _cur and _p.playing:
		return
	_cur = name
	var path := "res://assets/music/%s.ogg" % name
	if not ResourceLoader.exists(path):
		_p.stop()
		return
	var s: AudioStream = load(path)
	if s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = true
	_p.stream = s
	_p.pitch_scale = 1.0
	_p.play()

func set_fast(on: bool) -> void:
	_p.pitch_scale = 1.08 if on else 1.0

func play_jingle(name: String) -> void:
	var path := "res://assets/music/%s.ogg" % name
	if not ResourceLoader.exists(path):
		return
	_cur = name
	var s: AudioStream = load(path)
	if s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = false
	_p.stream = s
	_p.pitch_scale = 1.0
	_p.play()

func stop() -> void:
	_p.stop()
	_cur = ""
