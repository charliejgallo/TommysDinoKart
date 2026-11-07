class_name RaceCam
extends Camera3D
## Chase camera for one player: behind and above the kart, swings out on
## drifts, widens the view with speed and boosts, looks back on request,
## orbits the kart after the finish line.

var kart: Kart
var split := 1
var orbit := false
var _pos := Vector3.ZERO
var _look := Vector3.ZERO
var _kick := 0.0
var _orbit_a := 0.0
var _yaw := 0.0
var mode := "chase"

func _ready() -> void:
	fov = 72.0 if split != 2 or Settings.split_vertical else 62.0
	near = 0.1
	far = 900.0
	mode = Dev.arg("cam", "chase")
	current = true

func kick(s: float) -> void:
	_kick = maxf(_kick, s)

func snap() -> void:
	if kart == null:
		return
	_yaw = kart.yaw
	_pos = _want_pos()
	_look = kart.global_position + Vector3.UP * 1.05 + Vector3(-sin(kart.yaw), 0, -cos(kart.yaw)) * 2.0
	global_position = _pos
	look_at(_look, Vector3.UP)

func _want_pos() -> Vector3:
	var far_k := 1.18 if Settings.camera_far else 1.0
	var back := Vector3(sin(_yaw), 0, cos(_yaw))
	var spd := clampf(absf(kart.speed) / maxf(kart.top_speed, 1.0), 0.0, 1.4)
	var d := (3.3 + spd * 0.7) * far_k
	var h := 1.38 * far_k + spd * 0.1
	if kart.inp.back and kart.player >= 0:
		back = -back
	return kart.global_position + back * d + Vector3.UP * h

func _physics_process(dt: float) -> void:
	if kart == null:
		return
	_kick = maxf(_kick - dt * 1.5, 0.0)
	if mode == "side":
		var r := Vector3(cos(kart.yaw), 0, -sin(kart.yaw))
		global_position = kart.global_position + r * 4.0 + Vector3.UP * 1.2 + Vector3(-sin(kart.yaw), 0, -cos(kart.yaw)) * 1.0
		look_at(kart.global_position + Vector3.UP * 0.7, Vector3.UP)
		return
	if mode == "front":
		var f := Vector3(-sin(kart.yaw), 0, -cos(kart.yaw))
		global_position = kart.global_position + f * 4.6 + Vector3.UP * 1.5 + Vector3(cos(kart.yaw), 0, -sin(kart.yaw)) * 1.4
		look_at(kart.global_position + Vector3.UP * 0.8, Vector3.UP)
		return
	if mode == "grid":
		var t := kart.track
		var f := t.frame_at(5.0, -3.0, 2.6)
		global_position = f.origin
		look_at(t.point_at(t.length - 16.0, 0.0) + Vector3.UP * 0.2, Vector3.UP)
		fov = 50.0
		return
	if mode == "top":
		global_position = kart.global_position + Vector3(0, 60, 0.01)
		look_at(kart.global_position, Vector3.UP)
		return
	if orbit or mode == "orbit":
		_orbit_a += dt * 0.5
		var o := Vector3(sin(_orbit_a), 0, cos(_orbit_a)) * 5.0 + Vector3.UP * 2.0
		_pos = _pos.lerp(kart.global_position + o, clampf(dt * 3.0, 0.0, 1.0))
		global_position = _pos
		look_at(kart.global_position + Vector3.UP * 0.8, Vector3.UP)
		return
	# follow the heading with a lag; drifting makes the camera swing wider
	var target_yaw := kart.yaw
	if kart.drifting:
		target_yaw += kart.drift_dir * 0.18
	_yaw = lerp_angle(_yaw, target_yaw, clampf(dt * (5.0 if not kart.drifting else 3.0), 0.0, 1.0))
	if kart.rescue_t > 0.0:
		_yaw = lerp_angle(_yaw, kart.yaw, clampf(dt * 2.0, 0.0, 1.0))
	var want := _want_pos()
	# keep above the ground
	var gh := kart.track.ground_h(want.x, want.z) + 0.8
	want.y = maxf(want.y, gh)
	_pos = _pos.lerp(want, clampf(dt * 10.0, 0.0, 1.0))
	if kart.inp.back and kart.player >= 0:
		_pos = want
	global_position = _pos
	_look = _look.lerp(kart.global_position + Vector3.UP * 1.05 + Vector3(-sin(kart.yaw), 0, -cos(kart.yaw)) * 2.0, clampf(dt * 14.0, 0.0, 1.0))
	look_at(_look, Vector3.UP)
	var spd := clampf(absf(kart.speed) / maxf(kart.top_speed, 1.0), 0.0, 1.5)
	var base := 72.0 if split != 2 or Settings.split_vertical else 62.0
	fov = lerpf(fov, base + spd * 8.0 + (6.0 if kart.boost_t > 0.0 else 0.0) + _kick * 4.0, dt * 4.0)
