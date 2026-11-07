class_name Race
extends Node
## One race (or battle): builds the track and the 8 karts, one screen pane
## per local player (split screen), runs countdown -> race -> finish, keeps
## the places, and hands the result to Session.

const N_KARTS := 8
const POINTS := [15, 12, 10, 8, 6, 4, 2, 1]

var cfg := {}
var mode := "gp"                 # gp, free, time, battle
var track: Track
var karts: Array[Kart] = []
var players: Array[Kart] = []
var panes := []                  # [{container, viewport, cam, hud}]
var state := "pre"               # pre, countdown, race, done
var clock := 0.0
var countdown_left := 3.6
var laps := 3
var rev := {}
var ai_mul := {}
var finish_order: Array[Kart] = []
var _done_t := 0.0
var _world: Node3D
var _paused := false
var _pause_menu: Control
var _results_shown := false

func _ready() -> void:
	cfg = Session.race_cfg()
	mode = cfg.get("mode", "free")
	laps = cfg.get("laps", Settings.laps)
	if mode == "time":
		laps = 3
	if mode == "battle":
		laps = 999
	_world = Node3D.new()
	_world.name = "World"
	_world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(_world)
	track = Track.new()
	track.name = "Track"
	_world.add_child(track)
	track.build(Track.load_data(cfg.get("track", "pradera")))
	_spawn_karts()
	if mode == "time":
		_ghost_setup()
	_build_panes()
	Music.play_track(track.theme.get("music", "race_meadow") if mode != "battle" else "battle")
	state = "countdown"
	if Dev.arg("t") != "":
		_fast_forward(float(Dev.arg("t")))
	if Dev.arg("autotest") != "":
		countdown_left = 0.05
		Engine.time_scale = float(Dev.arg("autotest")) if Dev.arg("autotest").is_valid_float() else 6.0
		Engine.max_physics_steps_per_frame = 16

func _spawn_karts() -> void:
	var chosen: Array = cfg.get("players", [{"driver": "tommy"}])
	var used := {}
	for c in chosen:
		used[c.driver] = true
	var rivals := []
	if mode != "time":
		# Tommy always races: as a rival when no player picked him
		if not used.has("tommy"):
			rivals.append("tommy")
			used["tommy"] = true
		var pool := Roster.ids().filter(func(i): return not used.has(i))
		pool.shuffle()
		var want := (N_KARTS if mode != "battle" else 6) - chosen.size() - rivals.size()
		for i in want:
			rivals.append(pool[i])
	var order := []
	for i in chosen.size():
		order.append({"driver": chosen[i].driver, "player": i, "kart": chosen[i].get("kart", {})})
	for r in rivals:
		order.append({"driver": r, "player": -1, "kart": {}})
	# players start at the back of the grid in GP / free (like the classic
	# fairness rule), rivals ahead
	var slots := track.spawn.duplicate()
	var grid_order := []
	for o in order:
		if o.player < 0:
			grid_order.append(o)
	for o in order:
		if o.player >= 0:
			grid_order.append(o)
	if mode == "time":
		grid_order = order
	var skill_base: float = [0.25, 0.55, 0.85][Settings.ai_level]
	for i in grid_order.size():
		var o: Dictionary = grid_order[i]
		var k := Kart.new()
		k.name = "Kart_%s" % o.driver
		k.player = o.player
		k.race = self
		var kc: Dictionary = Roster.kart_colors(o.driver)
		kc.merge(o.kart, true)
		if o.player < 0:
			kc["top_mul"] = 0.94 + skill_base * 0.08 + randf_range(-0.015, 0.015)
		k.setup(track, o.driver, kc)
		_world.add_child(k)
		k.place_at(slots[i])
		k.idx = i
		if o.player >= 0 and Dev.arg("ai-player") == "":
			k.brain = Brains.PlayerBrain.new(o.player)
		elif mode == "battle":
			k.brain = Brains.BattleBrain.new(clampf(skill_base + randf_range(-0.12, 0.12), 0.05, 1.0), i * 7919 + 13)
		else:
			k.brain = Brains.AIBrain.new(clampf(skill_base + randf_range(-0.12, 0.12), 0.05, 1.0), i * 7919 + 13)
		if mode == "battle":
			k.add_balloons()
		k.finished.connect(_on_finished)
		k.lap_done.connect(_on_lap)
		karts.append(k)
		if o.player >= 0:
			players.append(k)
	players.sort_custom(func(a, b): return a.player < b.player)
	if Settings.show_names:
		for k in karts:
			if k.player < 0:
				k.set_name_tag(Roster.display_name(k.driver_id), Color("#fff7e6"))

func _build_panes() -> void:
	var n := players.size()
	if n >= 2:
		# every pane renders the world again: lighter shadows / no SSAO
		for c in track.get_children():
			if c is WorldEnvironment and n >= 3:
				(c as WorldEnvironment).environment.ssao_enabled = false
			if c is DirectionalLight3D:
				(c as DirectionalLight3D).directional_shadow_max_distance = 100.0 if n == 2 else 60.0
				if n >= 3:
					(c as DirectionalLight3D).directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	var rects := _pane_rects(n)
	for i in n:
		var r: Rect2 = rects[i]
		var svc := SubViewportContainer.new()
		svc.stretch = true
		svc.anchor_left = r.position.x
		svc.anchor_top = r.position.y
		svc.anchor_right = r.end.x
		svc.anchor_bottom = r.end.y
		svc.offset_left = 2 if r.position.x > 0 else 0
		svc.offset_top = 2 if r.position.y > 0 else 0
		root.add_child(svc)
		var vp := SubViewport.new()
		vp.msaa_3d = Viewport.MSAA_2X if Settings.quality >= 1 else Viewport.MSAA_DISABLED
		vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA if n > 1 else Viewport.SCREEN_SPACE_AA_DISABLED
		vp.positional_shadow_atlas_size = 1024
		vp.audio_listener_enable_3d = i == 0
		svc.add_child(vp)
		var cam := RaceCam.new()
		cam.kart = players[i]
		cam.split = n
		vp.add_child(cam)
		cam.snap()
		var hud := Hud.new()
		hud.race = self
		hud.kart = players[i]
		hud.split = n
		hud.visible = Dev.arg("nohud") == ""
		hud.anchor_left = r.position.x
		hud.anchor_top = r.position.y
		hud.anchor_right = r.end.x
		hud.anchor_bottom = r.end.y
		hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(hud)
		panes.append({"svc": svc, "vp": vp, "cam": cam, "hud": hud})
	if n > 1:
		var lines := ColorRect.new()
		lines.color = Color("#2b2440")
		lines.set_anchors_preset(Control.PRESET_FULL_RECT)
		lines.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(lines)
		root.move_child(lines, 0)

func _pane_rects(n: int) -> Array:
	match n:
		1:
			return [Rect2(0, 0, 1, 1)]
		2:
			if Settings.split_vertical:
				return [Rect2(0, 0, 0.5, 1), Rect2(0.5, 0, 0.5, 1)]
			return [Rect2(0, 0, 1, 0.5), Rect2(0, 0.5, 1, 0.5)]
		3:
			return [Rect2(0, 0, 0.5, 0.5), Rect2(0.5, 0, 0.5, 0.5), Rect2(0, 0.5, 0.5, 0.5)]
		_:
			return [Rect2(0, 0, 0.5, 0.5), Rect2(0.5, 0, 0.5, 0.5), Rect2(0, 0.5, 0.5, 0.5), Rect2(0.5, 0.5, 0.5, 0.5)]

func _fast_forward(t: float) -> void:
	## developer: run the clock fast until the race clock reaches t
	_ff_until = t
	countdown_left = 0.05
	Engine.time_scale = 4.0
	Dev.hold_shot = true

var _ff_until := -1.0

# ------------------------------------------------------------ loop
func _physics_process(dt: float) -> void:
	if _paused:
		return
	match state:
		"countdown":
			var before := countdown_left
			countdown_left -= dt
			for i in 3:
				var th := 3.0 - i
				if before > th and countdown_left <= th:
					Sfx.play("count", -2.0)
			if countdown_left <= 0.0:
				state = "race"
				Sfx.play("go", 0.0)
				if mode == "time":
					for p in players:
						p.item = "feather3"
						p.item_count = 3
						p.item_changed.emit(p)
				for k in karts:
					var r: float = rev.get(k.idx, 0.0)
					if r > 0.15 and r < 1.0:
						k.boost(1.0, false)
					elif r >= 2.4:
						k.spin_t = 0.7
		"race", "done":
			clock += dt
			if _ff_until > 0.0 and clock >= _ff_until:
				_ff_until = -1.0
				Engine.time_scale = 1.0
				Dev.hold_shot = false
			_rank()
			_catch_up()
			if mode == "battle" and state == "race":
				_battle_check()
			elif state == "race" and _all_players_done():
				state = "done"
				_done_t = 0.0
			if mode == "time":
				_ghost_step(dt)
			if Dev.arg("autotest") != "":
				_autotest_step()
			if state == "done":
				_done_t += dt
				if _done_t > 3.5 and not _results_shown:
					_show_results()
			if Settings.session_over() and not _results_shown and state == "race":
				pass
	if Controls.any_pause() and state != "pre":
		toggle_pause()

var _trace_t := 0.0
func _process(dt: float) -> void:
	if Dev.arg("trace") != "":
		_trace_t += dt
		if _trace_t > 0.5:
			_trace_t = 0.0
			var k: Kart = karts[int(Dev.arg("trace"))] if Dev.arg("trace").is_valid_int() else karts[0]
			print("[trace] t=%.1f %s seg=%d prog=%.0f lat=%.1f/%.1f spd=%.1f st=%.2f thr=%.1f surf=%s y=%.1f ground=%s drift=%s air=%.2f resc=%.1f" % [clock, k.driver_id, k.seg, k.prog,
				track.lateral_at(k.global_position, k.seg), track.width[k.seg] * 0.5, k.speed, k.inp.steer, k.inp.throttle,
				k.surface, k.global_position.y, k.on_ground, k.drifting, k.air_t, k.rescue_t])

func _rank() -> void:
	var order: Array[Kart] = karts.duplicate()
	order.sort_custom(_before)
	for i in order.size():
		order[i].place = i + 1

const BATTLE_TIME := 180.0

func battle_left() -> float:
	return maxf(BATTLE_TIME - clock, 0.0)

func _battle_check() -> void:
	var alive := karts.filter(func(k): return not k.out)
	var players_alive := players.filter(func(k): return not k.out)
	if alive.size() <= 1 or players_alive.is_empty() or clock >= BATTLE_TIME:
		state = "done"
		_done_t = 0.0
		for k in alive:
			k.done = true
			k.finish_time = clock + 1000.0 + k.balloons
		Sfx.play("finish")
		for p in players:
			panes[p.player].cam.orbit = true

func _before(a: Kart, b: Kart) -> bool:
	if mode == "battle":
		if a.out != b.out:
			return not a.out
		if a.balloons != b.balloons:
			return a.balloons > b.balloons
		return a.finish_time > b.finish_time
	if a.done and b.done:
		return a.finish_time < b.finish_time
	if a.done != b.done:
		return a.done
	return a.race_dist > b.race_dist

func _catch_up() -> void:
	## rivals keep the race lively: the ones far ahead of the best player ease
	## off, the ones far behind push a little (grown-ups can turn it off)
	if not Settings.catch_up or players.is_empty():
		ai_mul.clear()
		return
	var best := -INF
	for p in players:
		best = maxf(best, p.race_dist)
	for k in karts:
		if k.player >= 0:
			continue
		var gap := k.race_dist - best
		var m := 1.0
		if gap > 30.0:
			m = 1.0 - clampf((gap - 30.0) / 300.0, 0.0, 0.14)
		elif gap < -40.0:
			m = 1.0 + clampf((-gap - 40.0) / 300.0, 0.0, 0.1)
		ai_mul[k.idx] = m

var _stuck := {}
func _autotest_step() -> void:
	for k in karts:
		if absf(k.speed) < 2.0 and not k.done and k.rescue_t <= 0.0:
			_stuck[k] = _stuck.get(k, 0.0) + get_physics_process_delta_time()
			if _stuck[k] > 4.0:
				_stuck[k] = -30.0
				print("[stuck] %s seg=%d prog=%.0f pos=%s lat=%.1f y=%.1f road_y=%.1f on_ground=%s" % [k.driver_id, k.seg, k.prog,
					k.global_position, track.lateral_at(k.global_position, k.seg), k.global_position.y, track.pos[k.seg].y, k.on_ground])
		elif _stuck.get(k, 0.0) > 0.0:
			_stuck[k] = 0.0
	var all_done := true
	for k in karts:
		if not k.done:
			all_done = false
	if all_done or clock > float(Dev.arg("limit", "400")):
		var order: Array[Kart] = karts.duplicate()
		order.sort_custom(_before)
		print("[autotest] %s lap=%.0fm clock=%.1f" % [track.data.get("id", "?"), track.length, clock])
		for k in order:
			print("[autotest]   %d %-12s %s laps=%s rescues=%d" % [k.place, k.driver_id,
				("%.1f" % k.finish_time) if k.done else "DNF lap %d prog %.0f" % [k.lap, k.prog],
				", ".join(k.lap_times.map(func(x): return "%.1f" % x)), k.rescues])
		get_tree().quit()

func _all_players_done() -> bool:
	for p in players:
		if not p.done:
			return false
	return true

var new_record := false

func _on_finished(k: Kart) -> void:
	finish_order.append(k)
	if mode == "time" and k.player == 0:
		new_record = _ghost_save(k)
	if k.player >= 0:
		Sfx.play("finish", 0.0)
		Music.play_jingle("win" if k.place <= 3 else "finish")
		panes[k.player].cam.orbit = true
		k.brain = Brains.AIBrain.new(0.4, 1)

func _on_lap(k: Kart, lap: int) -> void:
	if k.player >= 0:
		panes[k.player].hud.on_lap(lap)
		if lap == laps - 1:
			Music.set_fast(true)

func kart_ahead(k: Kart) -> Kart:
	for o in karts:
		if o.place == k.place - 1:
			return o
	return null

func kart_behind(k: Kart) -> Kart:
	for o in karts:
		if o.place == k.place + 1:
			return o
	return null

func on_hit(victim: Kart, _from: Kart) -> void:
	if mode == "battle":
		victim.pop_balloon()

# ------------------------------------------------------------ time trial ghost
var _rec := PackedFloat32Array()
var _rec_t := 0.0
var _ghost: Kart
var _ghost_data := {}
const GHOST_HZ := 20.0

func ghost_path() -> String:
	var d := ("user://dev/" if Dev.is_dev() else "user://") + "ghosts/"
	DirAccess.make_dir_recursive_absolute(d)
	return d + "%s.json" % track.data.get("id", "x")

func best_time() -> float:
	return float(_ghost_data.get("time", -1.0))

func _ghost_setup() -> void:
	if FileAccess.file_exists(ghost_path()):
		var d = JSON.parse_string(FileAccess.get_file_as_string(ghost_path()))
		if d is Dictionary:
			_ghost_data = d
	if _ghost_data.is_empty():
		return
	_ghost = Kart.new()
	_ghost.setup(track, _ghost_data.get("driver", "tommy"), Roster.kart_colors(_ghost_data.get("driver", "tommy")))
	_ghost.collision_layer = 0
	_ghost.collision_mask = 0
	_world.add_child(_ghost)
	_ghost.set_physics_process(false)
	if _ghost.engine:
		_ghost.engine.queue_free()
		_ghost.engine = null
	for mi in _ghost.find_children("*", "MeshInstance3D", true, false):
		for si in mi.mesh.get_surface_count():
			var m: Material = mi.get_active_material(si)
			if m is ShaderMaterial:
				var m2: ShaderMaterial = m.duplicate()
				m2.set_shader_parameter("fade", 0.5)
				mi.set_surface_override_material(si, m2)
	var tag := Label3D.new()
	tag.text = tr("Fantasma")
	tag.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	tag.position.y = 2.0
	tag.pixel_size = 0.008
	tag.font_size = 32
	tag.modulate = Color(1, 1, 1, 0.7)
	_ghost.add_child(tag)

func _ghost_step(dt: float) -> void:
	if state != "race" or players.is_empty():
		return
	var p: Kart = players[0]
	_rec_t += dt
	if _rec_t >= 1.0 / GHOST_HZ and not p.done:
		_rec_t = 0.0
		_rec.append_array([p.global_position.x, p.global_position.y, p.global_position.z, p.yaw])
	if _ghost and _ghost_data.has("frames"):
		var fr: Array = _ghost_data.frames
		var f := clock * GHOST_HZ
		var i := int(f) * 4
		if i + 7 < fr.size():
			var t := f - floorf(f)
			var a := Vector3(fr[i], fr[i + 1], fr[i + 2])
			var b := Vector3(fr[i + 4], fr[i + 5], fr[i + 6])
			_ghost.global_position = a.lerp(b, t)
			_ghost.yaw = lerp_angle(fr[i + 3], fr[i + 7], t)
			_ghost.rotation.y = _ghost.yaw
			_ghost.speed = a.distance_to(b) * GHOST_HZ
			_ghost._visuals(dt)
		else:
			_ghost.visible = false

func _ghost_save(p: Kart) -> bool:
	## keeps the best run of this track; true when it is a new record
	var bt := best_time()
	if bt > 0.0 and p.finish_time >= bt:
		return false
	var f := FileAccess.open(ghost_path(), FileAccess.WRITE)
	f.store_string(JSON.stringify({"time": p.finish_time, "driver": p.driver_id, "laps": p.lap_times,
		"frames": Array(_rec).map(func(x): return snappedf(x, 0.01))}))
	return true

func rumble(p: int, s: float) -> void:
	if not Settings.rumble:
		return
	var slot: Dictionary = Controls.slots[p] if p < Controls.slots.size() else {}
	var j: int = slot.get("joy", -2)
	if j >= 0:
		Input.start_joy_vibration(j, s * 0.5, s, 0.18)
	elif j == -1:
		for d in Input.get_connected_joypads():
			Input.start_joy_vibration(d, s * 0.5, s, 0.18)

func cam_kick(p: int, s: float) -> void:
	if p < panes.size():
		panes[p].cam.kick(s)

# ------------------------------------------------------------ end of race
func _show_results() -> void:
	_results_shown = true
	# AI karts that are still racing get a finish time estimated from their gap
	var order: Array[Kart] = karts.duplicate()
	order.sort_custom(_before)
	var res := []
	for i in order.size():
		var k: Kart = order[i]
		res.append({"driver": k.driver_id, "player": k.player, "place": i + 1,
			"time": k.finish_time if k.done else -1.0, "coins": k.coins,
			"points": POINTS[i] if i < POINTS.size() else 0, "best_lap": _best(k.lap_times)})
	Session.race_finished(res, self)
	var rs := Results.new()
	rs.race = self
	rs.rows = res
	add_child(rs)

func _best(a: Array) -> float:
	var b := INF
	for t in a:
		b = minf(b, t)
	return b if b < INF else -1.0

func toggle_pause() -> void:
	_paused = not _paused
	get_tree().paused = _paused
	if _paused:
		_pause_menu = PauseMenu.new()
		_pause_menu.race = self
		add_child(_pause_menu)
	elif _pause_menu:
		_pause_menu.queue_free()
		_pause_menu = null
