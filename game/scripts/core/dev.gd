extends Node
## Developer hooks from command-line user args (after `--`). Any of them
## makes the game keep its settings, garage and ghosts in user://dev/ so a
## family's real data is never touched. See docs/DEVELOPMENT.md.
##   --race=<track>      jump straight into a race on that track (or arena)
##   --mode=<m>          gp | free | time | battle (default free)
##   --drivers=a,b,..    pilots for --race (first = player 1)
##   --players=<n>       local players for --race (split screen)
##   --ai-player         player karts are driven by the AI (demos, tests)
##   --autotest[=<x>]    run the whole race headless at x times speed, print
##                       places, lap times, rescues and stuck karts, quit
##   --limit=<s>         autotest: give up after this race time (default 400)
##   --trace=<i>         print kart i's progress / speed / steering every 0.5 s
##   --t=<s>             run the race clock fast until it reaches s
##   --cam=<mode>        race camera for shots: chase, side, front, top, orbit, grid
##   --nohud             hide the HUD (track preview pictures)
##   --shot=<png>        save a screenshot of the window and quit
##   --shot-after=<s>    seconds before the shot (default 2.0)
##   --lang=<code>       language for this run (es, en, ...)
##   --menu=<page>       open the menus on a page (main, mode, track, cup,
##                       parents, garage, garage_kart, settings_open, rest, ...)
##   --keys=k,wait:s,..  type keys (enter, space, up, down, left, right, z, x,
##                       e, esc; key:hold seconds) to drive the menus
##   --scene=<name>      run scripts/dev/<name>.gd: lineup (all karts on a
##                       lawn: --only, --cols, --zoom, --drvdir) or portraits
##                       (renders assets/ui/portraits/*.png)
##   --fps               print fps / draw calls every second

var _shot := ""
var _after := 2.0
var _t := 0.0
var _fps_t := 0.0
var hold_shot := false
var _keys := []
var _key_t := 1.5
var _held := -1

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_shot = arg("shot")
	if arg("keys") != "":
		_keys = Array(arg("keys").split(","))
	if arg("shot-after") != "":
		_after = float(arg("shot-after"))

func is_dev() -> bool:
	for a in OS.get_cmdline_user_args():
		for k in ["--shot", "--race", "--scene", "--keys", "--ai-player", "--lineup", "--menu", "--keys"]:
			if a.begins_with(k):
				return true
	return false

func arg(name: String, def := "") -> String:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--" + name + "="):
			return a.substr(name.length() + 3)
		if a == "--" + name:
			return "1"
	return def

const KEYNAMES := {"enter": KEY_ENTER, "space": KEY_SPACE, "up": KEY_UP, "down": KEY_DOWN, "left": KEY_LEFT,
	"right": KEY_RIGHT, "z": KEY_Z, "x": KEY_X, "e": KEY_E, "esc": KEY_ESCAPE}

func _key(code: int, down: bool) -> void:
	var e := InputEventKey.new()
	e.physical_keycode = code
	e.keycode = code
	e.pressed = down
	Input.parse_input_event(e)

func _run_keys(dt: float) -> void:
	## --keys=enter,wait:1.5,right,space:0.6 (a key, or key:hold seconds)
	_key_t -= dt
	if _key_t > 0.0:
		return
	if _held >= 0:
		_key(_held, false)
		_held = -1
		_key_t = 0.25
		return
	if _keys.is_empty():
		return
	var st: String = _keys.pop_front()
	var parts := st.split(":")
	if parts[0] == "wait":
		_key_t = float(parts[1])
		return
	_held = KEYNAMES.get(parts[0], KEY_ENTER)
	_key(_held, true)
	_key_t = float(parts[1]) if parts.size() > 1 else 0.12

func _process(dt: float) -> void:
	_run_keys(dt)
	if not hold_shot:
		_t += dt / maxf(Engine.time_scale, 0.001)
	if arg("fps") != "":
		_fps_t += dt
		if _fps_t > 1.0:
			_fps_t = 0.0
			print("[fps] %d draws=%d prims=%d" % [Engine.get_frames_per_second(),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)])
	if _shot != "" and _t >= _after:
		var img := get_viewport().get_texture().get_image()
		img.save_png(_shot)
		print("[shot] ", _shot)
		_shot = ""
		get_tree().quit()
