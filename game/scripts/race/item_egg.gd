class_name ItemEgg
extends Area3D
## A surprise egg floating over the road: a kart that touches it cracks it
## and gets an item. It grows back after RESPAWN seconds.

const RESPAWN := 2.5
const EGGS := ["egg_trike", "egg_trex", "egg_stego", "egg_raptor", "egg_brachio", "egg_ptera"]
static var _meshes := {}
var _vis: Node3D
var _t := 0.0
var _dead := 0.0
var _phase := 0.0

func _ready() -> void:
	collision_layer = 4
	collision_mask = 2
	monitoring = true
	var cs := CollisionShape3D.new()
	var sp := SphereShape3D.new()
	sp.radius = 0.9
	cs.shape = sp
	add_child(cs)
	_phase = randf() * TAU
	var id: String = EGGS[randi() % EGGS.size()]
	_vis = (load("res://assets/props/%s.glb" % id) as PackedScene).instantiate()
	Look.apply(_vis)
	_vis.scale = Vector3.ONE * 4.2
	_vis.position.y = -0.55
	add_child(_vis)
	var q := Label3D.new()
	q.text = "?"
	q.font_size = 120
	q.outline_size = 28
	q.modulate = Color("#fff7e6")
	q.outline_modulate = Color("#e2577a")
	q.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	q.position = Vector3(0, 0.15, 0)
	q.no_depth_test = false
	q.pixel_size = 0.006
	_vis.add_child(q)
	q.scale = Vector3.ONE / 4.2
	body_entered.connect(_hit)

func _process(dt: float) -> void:
	_t += dt
	if _dead > 0.0:
		_dead -= dt
		if _dead <= 0.0:
			_vis.visible = true
			_vis.scale = Vector3.ONE * 0.5
			set_deferred("monitoring", true)
		return
	_vis.rotation.y = _t * 1.4 + _phase
	_vis.position.y = -0.55 + sin(_t * 2.2 + _phase) * 0.12
	_vis.scale = _vis.scale.lerp(Vector3.ONE * 4.2, dt * 6.0)

func _hit(b: Node) -> void:
	if _dead > 0.0 or not b.has_method("give_item"):
		return
	b.give_item()
	_dead = RESPAWN
	_vis.visible = false
	set_deferred("monitoring", false)
	Fx.burst(get_parent(), global_position, Color("#ffe27a"), 18)
	Sfx.play_at("egg_crack", global_position)

func visible_egg() -> bool:
	return _dead <= 0.0
