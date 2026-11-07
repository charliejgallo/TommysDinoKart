class_name CoinPickup
extends Area3D
## A spinning coin over the road: +1 coin (spent in the garage). Grows back.

const RESPAWN := 8.0
var _vis: MeshInstance3D
var _dead := 0.0
var _t := randf() * TAU

func _ready() -> void:
	collision_layer = 4
	collision_mask = 2
	var cs := CollisionShape3D.new()
	var sp := SphereShape3D.new()
	sp.radius = 0.8
	cs.shape = sp
	add_child(cs)
	_vis = MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.42
	cm.bottom_radius = 0.42
	cm.height = 0.1
	cm.radial_segments = 20
	_vis.mesh = cm
	_vis.rotation.x = PI / 2
	_vis.material_override = Themes.toon(Color("#ffd35a"), 0.25)
	_vis.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_vis)
	body_entered.connect(_hit)

func _process(dt: float) -> void:
	if _dead > 0.0:
		_dead -= dt
		if _dead <= 0.0:
			_vis.visible = true
			set_deferred("monitoring", true)
		return
	_t += dt
	rotation.y = _t * 3.0
	_vis.position.y = sin(_t * 2.5) * 0.08

func _hit(b: Node) -> void:
	if _dead > 0.0 or not (b is Kart) or not Settings.coins_on:
		return
	(b as Kart).coins += 1
	_dead = RESPAWN
	_vis.visible = false
	set_deferred("monitoring", false)
	if (b as Kart).player >= 0:
		Sfx.play_at("coin", global_position, -4.0)
