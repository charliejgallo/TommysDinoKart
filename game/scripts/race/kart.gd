class_name Kart
extends CharacterBody3D
## One kart with its driver: arcade handling, items, visuals.
##
## Driven by a "brain" (PlayerBrain for people, AIBrain for rivals) that
## fills `inp` every physics frame:
##   inp.throttle 0..1, inp.brake 0..1, inp.steer -1..1, inp.drift (held),
##   inp.item (pressed this frame), inp.back (look behind, held)
##
## Handling: speed along the heading, yaw rate from the stick (less at low
## speed, reversed when backing up). Hop + drift: holding drift while
## steering hops and slides; the longer the drift the bigger the spark
## level (blue, orange, pink) and the turbo on release. Leaving a ramp lip
## with drift tapped in the air = trick = small turbo on landing.
## Grass and sand slow you unless boosting. Falling off the world or
## straying far from the road calls the Ptera rescue.

signal lap_done(kart, lap)
signal finished(kart)
signal item_changed(kart)

const GRAVITY := 26.0
const RADIUS := 0.55

class Input_:
	var throttle := 0.0
	var brake := 0.0
	var steer := 0.0
	var drift := false
	var item := false
	var back := false

var inp := Input_.new()
var brain = null
var track: Track
var race = null
var idx := 0                 # index in race.karts
var player := -1             # local player number (0..3) or -1 for AI
var driver_id := "tommy"
var weight := 1              # 0 light, 1 medium, 2 heavy
var kart_cfg := {}

# race progress
var seg := 0                 # nearest centre-line sample
var lap := 0                 # laps completed
var prog := 0.0              # distance along the lap
var race_dist := -1000.0     # lap * length + prog (for ranking)
var place := 1
var done := false
var finish_time := 0.0
var _last_prog := 0.0
var lap_times := []
var _lap_start := 0.0
var lap_armed := false       # passed the half of the lap since the last line
var _started := false        # crossed the start line once (grid is behind it)

# motion
var yaw := 0.0
var speed := 0.0
var vy := 0.0
var ground_n := Vector3.UP
var on_ground := true
var surface := "road"
var air_t := 0.0
var top_speed := 19.0
var accel := 11.0
var turn := 1.9

# drift / boosts
var drifting := false
var drift_dir := 0.0
var drift_t := 0.0
var drift_level := 0
var hop_t := 0.0
var boost_t := 0.0
var boost_k := 1.0
var trick_ok := false
var tricked := false
var spin_t := 0.0
var spin_kind := ""
var shield_t := 0.0
var star_t := 0.0
var ride_t := 0.0
var rescue_t := 0.0
var squash_t := 0.0
var coins := 0
var rescues := 0
var balloons := 3
var out := false
var _balloon_nodes := []
var item := ""
var item_count := 0
var _was_drift := false
var _bump_cd := 0.0

# visuals
var vis: Node3D
var body_pivot: Node3D
var wheels := []
var driver: Node3D
var driver_anim: AnimationPlayer
var _anim_now := ""
var sparks_l: GPUParticles3D
var sparks_r: GPUParticles3D
var dust: GPUParticles3D
var flame: GPUParticles3D
var shield_vis: MeshInstance3D
var name_tag: Label3D
var engine: AudioStreamPlayer3D

func setup(p_track: Track, p_driver: String, cfg: Dictionary) -> void:
	track = p_track
	driver_id = p_driver
	kart_cfg = cfg
	var d: Dictionary = Roster.driver(p_driver)
	weight = d.get("weight", 1)
	var cls: Dictionary = Settings.speed_class()
	top_speed = cls.top * [1.0, 1.0, 1.02][weight] * cfg.get("top_mul", 1.0)
	accel = cls.accel * [1.12, 1.0, 0.9][weight] * cfg.get("acc_mul", 1.0)
	turn = 1.95 * [1.06, 1.0, 0.94][weight]
	collision_layer = 2
	collision_mask = 1 | 2
	floor_max_angle = deg_to_rad(50)
	floor_snap_length = 0.7
	floor_stop_on_slope = true
	floor_block_on_wall = false
	wall_min_slide_angle = deg_to_rad(20)
	safe_margin = 0.02
	var cs := CollisionShape3D.new()
	var sp := SphereShape3D.new()
	sp.radius = RADIUS
	cs.shape = sp
	cs.position.y = RADIUS
	add_child(cs)
	_build_visual(d)

func place_at(xf: Transform3D) -> void:
	global_position = xf.origin
	var f := -xf.basis.z
	yaw = atan2(-f.x, -f.z)
	rotation = Vector3(0, yaw, 0)
	seg = track.nearest(global_position)
	prog = track.progress_at(global_position, seg)
	_last_prog = prog
	lap = 0
	_started = false
	race_dist = prog - track.length if prog > track.length * 0.5 else prog

# ------------------------------------------------------------ visuals
func _build_visual(d: Dictionary) -> void:
	vis = Node3D.new()
	vis.name = "Vis"
	add_child(vis)
	body_pivot = Node3D.new()
	vis.add_child(body_pivot)
	var model := Node3D.new()        # Blender models face +Z in Godot; karts drive to -Z
	model.rotation.y = PI
	body_pivot.add_child(model)
	var chassis: String = kart_cfg.get("chassis", "tina")
	var ch: Node3D = (load("res://assets/karts/kart_%s.glb" % chassis) as PackedScene).instantiate()
	Look.apply(ch)
	_paint(ch, kart_cfg)
	model.add_child(ch)
	var wstyle: String = kart_cfg.get("wheels", "wheel_basic")
	var wscene: PackedScene = load("res://assets/karts/%s.glb" % wstyle)
	for w in [[0.50, -0.50, 0.19, 0.19, true], [-0.50, -0.50, 0.19, 0.19, true],
			[0.52, 0.52, 0.22, 0.22, false], [-0.52, 0.52, 0.22, 0.22, false]]:
		var steer_piv := Node3D.new()
		steer_piv.position = Vector3(w[0], w[2], -w[1])     # Blender (x,y,z) -> Godot (x,z,-y)
		model.add_child(steer_piv)
		var spin := Node3D.new()
		steer_piv.add_child(spin)
		var wm: Node3D = wscene.instantiate()
		Look.apply(wm)
		_paint(wm, kart_cfg)
		wm.scale = Vector3.ONE * float(w[3])
		if w[0] < 0:
			wm.rotation.y = PI
		spin.add_child(wm)
		wheels.append({"steer": steer_piv, "spin": spin, "front": w[4], "r": w[3]})
	# driver on the seat
	var seat := Vector3(0.0, 0.24, -0.16)
	driver = (load(Roster.drivers_dir + "/drv_%s.glb" % driver_id) as PackedScene).instantiate()
	Look.apply(driver)
	driver.position = seat + Vector3(0, d.get("seat_y", 0.0), d.get("seat_z", 0.0))
	driver.scale = Vector3.ONE * Roster.scale_of(driver_id)
	model.add_child(driver)
	if driver_id == "tommy":
		_attach_cap()
	driver_anim = driver.find_child("AnimationPlayer", true, false)
	for a in ["drive", "cheer", "sad"]:
		if driver_anim and driver_anim.has_animation(a):
			driver_anim.get_animation(a).loop_mode = Animation.LOOP_LINEAR
	_anim("drive")
	# effects
	sparks_l = Fx.drift_sparks()
	sparks_r = Fx.drift_sparks()
	sparks_l.position = Vector3(0.55, 0.08, 0.55)
	sparks_r.position = Vector3(-0.55, 0.08, 0.55)
	body_pivot.add_child(sparks_l)
	body_pivot.add_child(sparks_r)
	dust = Fx.dust()
	dust.position = Vector3(0, 0.1, 0.7)
	body_pivot.add_child(dust)
	flame = Fx.exhaust_flame()
	flame.position = Vector3(0, 0.36, 0.75)
	body_pivot.add_child(flame)
	shield_vis = MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 1.25
	sm.height = 2.2
	shield_vis.mesh = sm
	shield_vis.material_override = Fx.bubble_material()
	shield_vis.position.y = 0.7
	shield_vis.visible = false
	shield_vis.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	vis.add_child(shield_vis)
	engine = AudioStreamPlayer3D.new()
	engine.stream = Sfx.engine_stream()
	engine.unit_size = 6.0
	engine.max_distance = 60.0
	engine.volume_db = -14.0
	engine.bus = "SFX"
	add_child(engine)

func _attach_cap() -> void:
	var sk: Skeleton3D = driver.find_child("Skeleton3D", true, false)
	if sk == null:
		return
	var ba := BoneAttachment3D.new()
	ba.bone_name = "head"
	sk.add_child(ba)
	var cap: Node3D = (load("res://assets/drivers/drv_tommy_cap.glb") as PackedScene).instantiate()
	Look.apply(cap)
	ba.add_child(cap)

func _paint(root: Node, cfg: Dictionary) -> void:
	var cols := {"paint": cfg.get("paint", Color("#ef5b4c")), "paint2": cfg.get("paint2", Color("#ffd35a")),
		"seat": cfg.get("seat", Color("#2f6fb8")), "hub": cfg.get("hub", cfg.get("paint2", Color("#ffd35a")))}
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		for s in mi.mesh.get_surface_count():
			var m: Material = mi.get_active_material(s)
			if m == null:
				continue
			var role := m.resource_name
			if cols.has(role):
				mi.set_surface_override_material(s, Themes.toon(cols[role]))

func _anim(a: String, restart := false) -> void:
	if driver_anim == null or (a == _anim_now and not restart):
		return
	if driver_anim.has_animation(a):
		driver_anim.play(a, 0.2)
		_anim_now = a

func add_balloons() -> void:
	var sc: PackedScene = load("res://assets/scenery/balloon.glb")
	for i in 3:
		var b: Node3D = sc.instantiate()
		Look.apply(b)
		for mi in b.find_children("*", "MeshInstance3D", true, false):
			for si in mi.mesh.get_surface_count():
				var m: Material = mi.get_active_material(si)
				if m and m.resource_name == "paint":
					mi.set_surface_override_material(si, Themes.toon(kart_cfg.get("paint", Color("#ef5b4c")).lightened(0.15)))
		b.scale = Vector3.ONE * 0.6
		b.position = Vector3((i - 1) * 0.32, 0.45, 0.8)
		b.rotation.z = (i - 1) * 0.25
		vis.add_child(b)
		_balloon_nodes.append(b)

func pop_balloon() -> void:
	if balloons <= 0:
		return
	balloons -= 1
	var b: Node3D = _balloon_nodes.pop_back()
	if b:
		Fx.burst(get_parent(), b.global_position + Vector3.UP * 1.2, Color("#ffd35a"), 16)
		b.queue_free()
	Sfx.play_at("pop", global_position)
	if balloons <= 0:
		out = true
		done = true
		finish_time = race.clock
		collision_layer = 0
		speed = 0.0
		_anim("sad")

func set_name_tag(text: String, col: Color) -> void:
	name_tag = Label3D.new()
	name_tag.text = text
	name_tag.font_size = 30
	name_tag.outline_size = 9
	name_tag.visibility_range_end = 28.0
	name_tag.visibility_range_begin = 5.0
	name_tag.outline_modulate = Color("#4a3426")
	name_tag.modulate = col
	name_tag.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	name_tag.position = Vector3(0, 2.1, 0)
	name_tag.pixel_size = 0.008
	name_tag.no_depth_test = false
	vis.add_child(name_tag)

# ------------------------------------------------------------ physics
func _physics_process(dt: float) -> void:
	if race == null or track == null:
		return
	if brain and race.state != "pre":
		brain.think(self, dt)
	if race.state == "countdown" or race.state == "pre":
		_engine_rev(dt)
		_track_progress()
		return
	if done and brain:
		# after the finish line the AI takes over, gently
		pass
	if out:
		speed = move_toward(speed, 0.0, 20.0 * dt)
		inp.throttle = 0.0
		inp.steer = 0.0
		inp.item = false
	_timers(dt)
	if rescue_t > 0.0:
		_rescue_step(dt)
		return
	if ride_t > 0.0:
		_ride_step(dt)
		return
	_drive(dt)
	_track_progress()
	_check_bounds()
	_unstick(dt)
	_visuals(dt)

func _engine_rev(dt: float) -> void:
	# revving on the grid: hold throttle at the right moment for a start boost
	if inp.throttle > 0.5:
		race.rev[idx] = race.rev.get(idx, 0.0) + dt
	_visuals(dt)

func _timers(dt: float) -> void:
	boost_t = maxf(boost_t - dt, 0.0)
	spin_t = maxf(spin_t - dt, 0.0)
	shield_t = maxf(shield_t - dt, 0.0) if shield_t < 900.0 else shield_t
	star_t = maxf(star_t - dt, 0.0)
	squash_t = maxf(squash_t - dt, 0.0)
	_bump_cd = maxf(_bump_cd - dt, 0.0)
	if inp.item and item != "" and spin_t <= 0.0 and not done:
		Items.use(self)

func _drive(dt: float) -> void:
	var assist: Dictionary = Settings.assists_for(player)
	var throttle := inp.throttle
	if assist.get("auto_accel", false) and player >= 0 and inp.brake < 0.1:
		throttle = 1.0
	var steer := inp.steer
	if spin_t > 0.0:
		throttle = 0.0
		steer = 0.0
	# ---- ground probe
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 1.0,
		global_position + Vector3.DOWN * 1.2, 1)
	q.exclude = [get_rid()]
	var hit := space.intersect_ray(q)
	var near_ground := false
	if hit:
		near_ground = true
		var col: Object = hit.collider
		surface = "offroad" if (col is Node and (col as Node).is_in_group("offroad")) else "road"
		if col is Node and (col as Node).is_in_group("ramp"):
			surface = "ramp"
		ground_n = ground_n.slerp(hit.normal, clampf(dt * 10.0, 0.0, 1.0)).normalized()
	on_ground = is_on_floor()
	# ---- speed
	var top := top_speed
	if surface == "offroad" and boost_t <= 0.0 and star_t <= 0.0:
		top *= Settings.offroad_mul()
	if boost_t > 0.0:
		top *= 1.32 * boost_k
	if star_t > 0.0:
		top *= 1.2
	if squash_t > 0.0:
		top *= 0.6
	if race.ai_mul.has(idx):
		top *= race.ai_mul[idx]
	if on_ground or air_t < 0.15:
		if throttle > 0.05:
			if speed < top:
				var k := 1.0 - clampf(speed / top, 0.0, 1.0) * 0.55
				speed = minf(speed + accel * throttle * k * dt, top)
			else:
				speed = move_toward(speed, top, 14.0 * dt)
		elif inp.brake > 0.05:
			if speed > 0.5:
				speed = move_toward(speed, 0.0, 26.0 * inp.brake * dt)
			else:
				speed = move_toward(speed, -top * 0.35, 9.0 * inp.brake * dt)
		else:
			speed = move_toward(speed, 0.0, 5.0 * dt)
		if boost_t > 0.0:
			speed = maxf(speed, top * 0.92)
	# ---- drift: hop on press while steering
	var want_drift := inp.drift and not done and spin_t <= 0.0
	if want_drift and not _was_drift and (on_ground or air_t < 0.1):
		vy = 3.6
		hop_t = 0.25
		if air_t > 0.0 or surface == "ramp":
			trick_ok = true
	if want_drift and not drifting and absf(steer) > 0.3 and speed > top_speed * 0.4 and (on_ground or hop_t > 0.0):
		drifting = true
		drift_dir = signf(steer)
		drift_t = 0.0
		drift_level = 0
	if drifting and (not want_drift or speed < top_speed * 0.3):
		_end_drift()
	if assist.get("auto_drift", false) and player >= 0:
		pass
	_was_drift = want_drift
	hop_t = maxf(hop_t - dt, 0.0)
	# ---- steering
	var sp_k := clampf(absf(speed) / 6.0, 0.0, 1.0) * (1.0 - clampf((absf(speed) - top_speed) / 20.0, 0.0, 0.35))
	var yaw_rate := 0.0
	if drifting:
		var s := clampf(steer * drift_dir, -1.0, 1.0)
		yaw_rate = -drift_dir * turn * (0.75 + 0.55 * s) * sp_k
		drift_t += dt * (1.0 + 0.6 * maxf(s, 0.0))
		var lv := 0
		if drift_t > 0.75: lv = 1
		if drift_t > 1.7: lv = 2
		if drift_t > 2.8: lv = 3
		if lv != drift_level:
			drift_level = lv
			Sfx.play_at("spark", global_position, -6.0)
	else:
		var st := steer
		if assist.get("steer_help", false) and player >= 0:
			st = _steer_help(st)
		yaw_rate = -st * turn * sp_k * (1.0 if speed >= 0.0 else -1.0)
		if not on_ground:
			yaw_rate *= 0.5
	if spin_t > 0.0:
		yaw_rate = 10.0 * (1.0 if spin_kind != "spin_l" else -1.0) * clampf(spin_t, 0.0, 1.0)
	yaw += yaw_rate * dt if spin_t <= 0.0 else 0.0
	# ---- velocity
	var fwd := Vector3(-sin(yaw), 0.0, -cos(yaw))
	var n := ground_n if near_ground else Vector3.UP
	var f_on := (fwd - n * fwd.dot(n)).normalized()
	var lat := Vector3.ZERO
	if drifting:
		var r := f_on.cross(n).normalized()
		lat = r * drift_dir * absf(speed) * 0.22
	var hv := f_on * speed + lat
	if on_ground and hop_t <= 0.0:
		vy = minf(vy, 0.0)
		velocity = hv + n * vy - n * 0.5
		vy = 0.0
		if air_t > 0.35:
			_land()
		air_t = 0.0
	else:
		air_t += dt
		vy -= GRAVITY * dt
		var keep := Vector3(velocity.x, 0.0, velocity.z)
		var fh := Vector3(f_on.x, 0.0, f_on.z).normalized() * Vector3(hv.x, 0, hv.z).length()
		velocity = keep.lerp(fh, clampf(dt * 3.0, 0.0, 1.0))
		if air_t < 0.05 and hop_t <= 0.0:
			# just left the ground over a lip: keep the climb we had
			vy = maxf(vy, hv.y)
		velocity.y = vy
		if inp.drift and not _was_drift and air_t > 0.15 and not tricked:
			trick_ok = true
	var before := velocity
	move_and_slide()
	if is_on_floor():
		if not on_ground and air_t > 0.0:
			pass
	else:
		if on_ground:
			# leaving the ground this frame: take the vertical speed with us
			vy = before.y
	_collisions(before)
	rotation = Vector3(0, yaw, 0)

func _steer_help(st: float) -> float:
	## nudges the stick towards the road ahead when the kid lets go or
	## heads off the road (assist "volante asistido")
	var k := (seg + 8) % track.n
	var to := track.pos[k] - global_position
	var fwd := Vector3(-sin(yaw), 0, -cos(yaw))
	var ang := Vector2(fwd.x, fwd.z).angle_to(Vector2(to.x, to.z))
	var want := clampf(ang * 1.6, -1.0, 1.0)
	var off := absf(track.lateral_at(global_position, seg)) / (track.width[seg] * 0.5)
	var w := 0.35 + 0.5 * clampf(off - 0.6, 0.0, 1.0)
	if absf(st) < 0.15:
		w = 0.8
	return lerpf(st, want, w)

func _end_drift() -> void:
	if drifting and drift_level > 0 and spin_t <= 0.0:
		boost([0.0, 0.7, 1.25, 1.9][drift_level], false)
	drifting = false
	drift_level = 0
	drift_t = 0.0

func _land() -> void:
	squash_t = 0.0
	if trick_ok and not tricked:
		boost(0.8, false)
		tricked = true
		Fx.burst(get_parent(), global_position + Vector3.UP, Color("#8ee8ff"), 12)
	trick_ok = false
	tricked = false
	Sfx.play_at("land", global_position, -10.0)
	Fx.puff(get_parent(), global_position, Color(0.9, 0.85, 0.75, 0.7))

func _collisions(before: Vector3) -> void:
	for i in get_slide_collision_count():
		var c := get_slide_collision(i)
		var other := c.get_collider()
		var nn := c.get_normal()
		if other is Kart:
			_bump_kart(other, nn)
			continue
		if absf(nn.y) < 0.55:
			# wall: lose speed by how square the hit was, bounce a little
			var fwd := Vector3(-sin(yaw), 0, -cos(yaw))
			var hit_k := absf(fwd.dot(Vector3(nn.x, 0, nn.z).normalized()))
			if hit_k > 0.35 and absf(speed) > 6.0 and _bump_cd <= 0.0:
				speed *= 1.0 - 0.6 * hit_k
				speed = -signf(speed) * minf(absf(speed), 4.0) if hit_k > 0.85 else speed
				_bump_cd = 0.3
				Sfx.play_at("bump", global_position, -4.0)
				Game_rumble(0.3)
				if drifting:
					drifting = false
			# turn the heading along the wall
			var tang := fwd - Vector3(nn.x, 0, nn.z).normalized() * fwd.dot(Vector3(nn.x, 0, nn.z).normalized())
			if tang.length() > 0.2 and hit_k < 0.9:
				var ny := atan2(-tang.x, -tang.z)
				yaw = lerp_angle(yaw, ny, 0.3)

func _bump_kart(o: Kart, nn: Vector3) -> void:
	if _bump_cd > 0.0:
		return
	_bump_cd = 0.25
	var wd := float(o.weight - weight)
	var push := 3.0 + 1.6 * wd
	if star_t > 0.0 and o.star_t <= 0.0:
		o.hit("spin", self)
		return
	if o.star_t > 0.0 and star_t <= 0.0:
		hit("spin", o)
		return
	if not Settings.bumping():
		push *= 0.4
	var away := Vector3(nn.x, 0, nn.z).normalized()
	global_position += away * 0.12
	speed *= 0.93
	velocity += away * push
	# a little sideways shove on the heading
	yaw += 0.04 * signf(away.dot(Vector3(cos(yaw), 0, -sin(yaw)))) * (1.0 + wd * 0.3)
	Sfx.play_at("bump_kart", global_position, -6.0)

func _track_progress() -> void:
	seg = track.nearest(global_position, seg)
	var p := track.progress_at(global_position, seg)
	var L := track.length
	if p > L * 0.45 and p < L * 0.55:
		lap_armed = true
	if _last_prog > L * 0.8 and p < L * 0.2:
		if lap_armed or not _started:
			_cross_line()
	elif _last_prog < L * 0.2 and p > L * 0.8 and _started:
		# went back over the line
		lap -= 1
		lap_armed = true
	_last_prog = p
	prog = p
	if not _started:
		# on the grid, behind the line: negative distance until the first crossing
		race_dist = p - L if p > L * 0.5 else p
	else:
		race_dist = lap * L + p

func _cross_line() -> void:
	if not _started:
		# grid starts behind the line: the first crossing starts lap 1
		_started = true
		lap = 0
		lap_armed = false
		_lap_start = race.clock
		return
	lap += 1
	lap_armed = false
	lap_times.append(race.clock - _lap_start)
	_lap_start = race.clock
	lap_done.emit(self, lap)
	if lap >= race.laps and not done:
		done = true
		finish_time = race.clock
		finished.emit(self)

func _check_bounds() -> void:
	if global_position.y < track.kill_y or (global_position.y < track.water_y - 0.2):
		start_rescue()
		return
	var lat := absf(track.lateral_at(global_position, seg))
	var edge := track.width[seg] * 0.5
	if lat > edge + Settings.stray_limit() or global_position.y < track.pos[seg].y - 12.0:
		start_rescue()
	if Settings.no_fall() and lat > edge + 2.5 and player >= 0:
		start_rescue()

var _slow_t := 0.0
var _best_dist := -INF
func _unstick(dt: float) -> void:
	## not getting anywhere (stuck on a rock, circling, lost): the ptera helps
	if race.state != "race" or done or spin_t > 0.0 or race.mode == "battle":
		_slow_t = 0.0
		_best_dist = race_dist
		return
	if race_dist > _best_dist + 4.0:
		_best_dist = race_dist
		_slow_t = 0.0
		return
	_slow_t += dt
	if _slow_t > (6.0 if player < 0 else 10.0):
		if Dev.arg("autotest") != "":
			print("[stuck] %s seg=%d pos=%s spd=%.1f lat=%.1f y=%.1f road_y=%.1f" % [driver_id, seg, global_position,
				speed, track.lateral_at(global_position, seg), global_position.y, track.pos[seg].y])
		_slow_t = 0.0
		_best_dist = race_dist
		start_rescue()

# ------------------------------------------------------------ rescue (Ptera)
var _rescue_from := Vector3.ZERO
var _rescue_to := Transform3D()
var _ptera: Node3D

func start_rescue() -> void:
	if rescue_t > 0.0:
		return
	rescues += 1
	if Dev.arg("autotest") != "":
		print("[rescue] %s seg=%d lat=%.1f y=%.1f (road y %.1f) t=%.1f" % [driver_id, seg, track.lateral_at(global_position, seg), global_position.y, track.pos[seg].y, race.clock])
	rescue_t = 2.2
	speed = 0.0
	vy = 0.0
	drifting = false
	boost_t = 0.0
	_rescue_from = global_position
	var s := track.dist[seg] + 2.0
	_rescue_to = track.frame_at(s, clampf(track.lateral_at(global_position, seg), -2.0, 2.0), 0.6)
	_ptera = Ptera.make()
	get_parent().add_child(_ptera)
	_ptera.global_position = _rescue_from + Vector3(0, 8, 0)
	Sfx.play_at("ptera", global_position)
	if item != "" and Settings.lose_item_on_fall():
		pass

func _rescue_step(dt: float) -> void:
	rescue_t -= dt
	var T := 2.2 - rescue_t
	var a := _rescue_from + Vector3.UP * 2.5
	var b := _rescue_to.origin + Vector3.UP * 4.0
	if T < 0.5:
		_ptera.global_position = _ptera.global_position.lerp(global_position + Vector3.UP * 2.4, clampf(dt * 8.0, 0.0, 1.0))
	elif T < 1.7:
		var t := (T - 0.5) / 1.2
		t = t * t * (3.0 - 2.0 * t)
		global_position = a.lerp(b, t) + Vector3.UP * sin(t * PI) * 5.0
		var f := (b - a)
		if Vector2(f.x, f.z).length() > 0.5:
			yaw = lerp_angle(yaw, atan2(-f.x, -f.z), dt * 4.0)
		_ptera.global_position = global_position + Vector3.UP * 2.4
	else:
		var t := (T - 1.7) / 0.5
		global_position = b.lerp(_rescue_to.origin, clampf(t, 0.0, 1.0))
		var f := -_rescue_to.basis.z
		yaw = lerp_angle(yaw, atan2(-f.x, -f.z), clampf(dt * 10.0, 0.0, 1.0))
		_ptera.global_position += Vector3(0, dt * 9.0, 0)
	_ptera.rotation.y = yaw
	rotation = Vector3(0, yaw, 0)
	velocity = Vector3.ZERO
	if rescue_t <= 0.0:
		global_position = _rescue_to.origin
		_ptera.queue_free()
		_ptera = null
		seg = track.nearest(global_position, seg)
	_track_progress()
	_visuals(dt)

# ------------------------------------------------------------ ptera ride item
var _ride_lat := 0.0

func start_ride(seconds: float) -> void:
	ride_t = seconds
	_ride_lat = track.lateral_at(global_position, seg)
	_ptera = Ptera.make()
	get_parent().add_child(_ptera)
	shield_t = maxf(shield_t, seconds)
	Sfx.play_at("ptera", global_position)

func _ride_step(dt: float) -> void:
	ride_t -= dt
	var v := top_speed * 1.55
	var s := track.dist[seg] + v * dt * 3.0
	_ride_lat = lerpf(_ride_lat, 0.0, dt)
	var tgt := track.point_at(s, _ride_lat) + track.up[seg] * 2.2
	var to := tgt - global_position
	global_position += to.limit_length(v * dt)
	var f := track.fwd[track.index_at_dist(s)]
	yaw = lerp_angle(yaw, atan2(-f.x, -f.z), clampf(dt * 6.0, 0.0, 1.0))
	rotation = Vector3(0, yaw, 0)
	speed = v * 0.7
	_ptera.global_position = global_position + Vector3.UP * 2.4
	_ptera.rotation.y = yaw
	if ride_t <= 0.0:
		_ptera.queue_free()
		_ptera = null
		shield_t = 0.0
		vy = 0.0
		boost(0.6, false)
	_track_progress()
	_visuals(dt)

# ------------------------------------------------------------ effects api
func boost(seconds: float, pad: bool) -> void:
	if seconds <= 0.0:
		return
	boost_t = maxf(boost_t, seconds)
	boost_k = 1.0 if not pad else 1.05
	speed = maxf(speed, top_speed * 1.15)
	Sfx.play_at("boost", global_position, -4.0 if player >= 0 else -10.0)
	if player >= 0:
		race.cam_kick(player, 0.6)

func give_item() -> void:
	if race and race.mode == "time":
		return
	if item != "" or (not Settings.items_on() and race.mode != "battle"):
		coins += 1
		return
	Items.roll(self)

func hit(kind: String, from = null) -> bool:
	## returns true when it landed (not blocked by a shield/star/ride)
	if rescue_t > 0.0 or ride_t > 0.0 or star_t > 0.0:
		return false
	if shield_t > 0.0:
		shield_t = 0.0
		Fx.burst(get_parent(), global_position + Vector3.UP, Color("#bff3ff"), 20)
		Sfx.play_at("pop", global_position)
		return false
	if kind == "squash":
		squash_t = 1.6
		speed *= 0.6
	elif kind == "slow":
		speed *= 0.45
	else:
		spin_t = 1.0 if kind != "tumble" else 1.4
		spin_kind = "spin_l" if randf() < 0.5 else "spin_r"
		speed *= 0.3
		if kind == "tumble":
			vy = 6.0
			on_ground = false
	drifting = false
	boost_t = 0.0
	coins = maxi(coins - 1, 0)
	_anim("hit", true)
	Sfx.play_at("hit", global_position)
	Game_rumble(0.7)
	if race and from is Kart:
		race.on_hit(self, from)
	return true

func Game_rumble(s: float) -> void:
	if player >= 0 and race:
		race.rumble(player, s)

# ------------------------------------------------------------ visuals per frame
var _wheel_spin := 0.0
var _lean := 0.0
var _tilt_basis := Basis()

func _visuals(dt: float) -> void:
	# align the body to the ground normal, lean into turns, squash on boosts
	var target_up := ground_n if (on_ground or air_t < 0.3) else Vector3.UP
	var fwd := Vector3(-sin(yaw), 0, -cos(yaw))
	var local_up := global_transform.basis.inverse() * target_up
	var b := Basis.looking_at(Vector3(0, 0, -1).slide(local_up).normalized(), local_up) if local_up.length() > 0.1 else Basis()
	_tilt_basis = _tilt_basis.slerp(b, clampf(dt * 10.0, 0.0, 1.0))
	vis.basis = _tilt_basis
	var steer_vis := inp.steer if spin_t <= 0.0 else 0.0
	var lean_t := -steer_vis * 0.08 * clampf(speed / 10.0, 0.0, 1.0)
	if drifting:
		lean_t = drift_dir * 0.12
	_lean = lerpf(_lean, lean_t, dt * 6.0)
	body_pivot.rotation = Vector3(0, 0, _lean)
	if drifting:
		body_pivot.rotation.y = lerpf(body_pivot.rotation.y, -drift_dir * 0.38, dt * 8.0)
	else:
		body_pivot.rotation.y = lerpf(body_pivot.rotation.y, 0.0, dt * 8.0)
	if spin_t > 0.0:
		body_pivot.rotation.y += spin_t * 14.0 * (1.0 if spin_kind == "spin_l" else -1.0)
	var sq := 1.0
	if squash_t > 0.0:
		sq = 0.5
	body_pivot.scale = body_pivot.scale.lerp(Vector3(1.0 + (1.0 - sq) * 0.5, sq, 1.0), dt * 10.0)
	if hop_t > 0.0:
		body_pivot.position.y = lerpf(body_pivot.position.y, 0.15, dt * 20.0)
	else:
		body_pivot.position.y = lerpf(body_pivot.position.y, 0.0, dt * 12.0)
	_wheel_spin += speed * dt / 0.2
	for w in wheels:
		(w.spin as Node3D).rotation.x = -_wheel_spin
		if w.front:
			(w.steer as Node3D).rotation.y = -steer_vis * 0.45
	var lvl_col: Color = [Color(0, 0, 0, 0), Color("#5ec8ff"), Color("#ffad3b"), Color("#ff6ad5")][drift_level]
	var on_sparks := drifting and drift_level > 0 and on_ground
	sparks_l.emitting = on_sparks
	sparks_r.emitting = on_sparks
	if on_sparks:
		Fx.tint(sparks_l, lvl_col)
		Fx.tint(sparks_r, lvl_col)
	dust.emitting = on_ground and absf(speed) > 6.0 and (surface == "offroad" or drifting)
	flame.emitting = boost_t > 0.0 or star_t > 0.0
	shield_vis.visible = shield_t > 0.0
	if star_t > 0.0:
		_star_flash()
	# driver animation
	if done:
		_anim("cheer" if place <= 3 else "sad")
	elif spin_t > 0.0:
		pass
	elif rescue_t > 0.0:
		_anim("hit")
	else:
		if driver_anim and _anim_now == "hit" and driver_anim.is_playing() and spin_t > 0.0:
			pass
		elif _anim_now == "hit" and (driver_anim == null or not driver_anim.is_playing() or driver_anim.current_animation_position > 0.95):
			_anim("drive")
		elif _anim_now != "hit":
			_anim("drive")
	if engine and not engine.playing and is_inside_tree():
		engine.play()
	if engine:
		engine.pitch_scale = 0.7 + clampf(absf(speed) / top_speed, 0.0, 1.4) * 0.9 + (0.15 if boost_t > 0.0 else 0.0)

var _star_k := 0.0
func _star_flash() -> void:
	_star_k += 0.2
	vis.scale = Vector3.ONE * (1.0 + 0.05 * sin(_star_k * 3.0))
	if star_t <= 0.05:
		vis.scale = Vector3.ONE
