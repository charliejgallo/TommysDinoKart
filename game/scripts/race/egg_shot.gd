class_name EggShot
extends Node3D
## A thrown egg. Rebotón: rolls along the track at a fixed offset from the
## centre line and bounces between the road edges. Buscador: follows the
## centre line to the kart ahead, then homes in. Both ride the road height,
## live a few seconds, and spin out the first kart they touch (the thrower
## is safe for a moment).

var race
var track: Track
var owner_kart: Kart
var seg := 0
var lat := 0.0
var lat_v := 0.0
var dir := 1.0
var speed := 32.0
var life := 6.0
var homing := false
var target: Kart
var safe := 0.4
var _vis: Node3D

static func throw(k: Kart, back: bool, seek: bool) -> void:
	var e := EggShot.new()
	e.race = k.race
	e.track = k.track
	e.owner_kart = k
	e.seg = k.seg
	e.lat = k.track.lateral_at(k.global_position, k.seg)
	e.dir = -1.0 if back else 1.0
	e.speed = maxf(k.top_speed * 1.6, 28.0) if not back else 16.0
	e.lat_v = (randf() - 0.5) * 6.0
	e.homing = seek
	if seek:
		e.target = k.race.kart_ahead(k)
		e.speed = k.top_speed * 1.45
		e.life = 9.0
	k.get_parent().add_child(e)
	e.global_position = k.global_position + Vector3.UP * 0.5
	Sfx.play_at("throw", k.global_position, -4.0)

func _ready() -> void:
	var id := "egg_raptor" if homing else "egg_trike"
	_vis = (load("res://assets/props/%s.glb" % id) as PackedScene).instantiate()
	Look.apply(_vis)
	_vis.scale = Vector3.ONE * 2.6
	add_child(_vis)
	if homing:
		var l := OmniLight3D.new()
		l.light_color = Color("#ff6b6b")
		l.light_energy = 1.5
		l.omni_range = 3.0
		add_child(l)

func _physics_process(dt: float) -> void:
	life -= dt
	safe -= dt
	if life <= 0.0 or race == null:
		_pop()
		return
	var p := global_position
	if homing and target and is_instance_valid(target):
		var to := target.global_position - p
		var gap := race_gap(target)
		if gap < 18.0 or to.length() < 18.0:
			# close: straight at it
			global_position = p + to.normalized() * minf(speed * dt, to.length())
			global_position.y = lerpf(global_position.y, target.global_position.y + 0.5, dt * 8.0)
		else:
			_follow(dt, lerpf(lat, track.lateral_at(target.global_position, target.seg), dt * 1.5))
	else:
		lat += lat_v * dt
		var edge := track.width[seg] * 0.5 + Track.CURB - 0.4
		if absf(lat) > edge:
			lat = clampf(lat, -edge, edge)
			lat_v = -lat_v
			Sfx.play_at("egg_bounce", global_position, -12.0)
		_follow(dt, lat)
	_vis.rotation.x -= dt * 14.0 * dir
	_vis.position.y = absf(sin(life * 9.0)) * 0.25 - 0.4
	for k in race.karts:
		if k == owner_kart and safe > 0.0:
			continue
		if k.global_position.distance_to(global_position) < 1.5:
			k.hit(Items.hit_kind(), owner_kart)
			_pop()
			return

func _follow(dt: float, want_lat: float) -> void:
	var s := track.dist[seg] + speed * dt * dir
	var k := track.index_at_dist(s)
	# advance seg by distance
	var adv := speed * dt * dir
	var cur := track.dist[seg] + adv
	seg = track.index_at_dist(cur)
	lat = want_lat
	var q := track.pos[seg] + track.right[seg] * lat + track.up[seg] * 0.6
	global_position = q
	look_at(q + track.fwd[k] * dir, Vector3.UP)

func race_gap(t: Kart) -> float:
	var d := t.prog - track.dist[seg]
	return fposmod(d, track.length)

func _pop() -> void:
	Fx.burst(get_parent(), global_position, Color("#fff3df"), 14)
	queue_free()

