class_name MudPuddle
extends Node3D
## Charco de barro: dropped behind a kart, sits on the road for a while;
## the first kart that drives in skids (spins, or only slows in gentle mode).

var race
var owner_kart: Kart
var life := 25.0
var safe := 0.8

static func drop(k: Kart) -> void:
	var m := MudPuddle.new()
	m.race = k.race
	m.owner_kart = k
	k.get_parent().add_child(m)
	var back := k.global_transform.basis.z * 2.2
	m.global_position = k.global_position + back + Vector3.UP * 0.05
	m.rotation.y = randf() * TAU
	Sfx.play_at("splat", k.global_position, -4.0)

func _ready() -> void:
	var mi := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 1.25
	cm.bottom_radius = 1.35
	cm.height = 0.08
	cm.radial_segments = 20
	mi.mesh = cm
	mi.material_override = Themes.toon(Color("#7a5236"))
	add_child(mi)
	for i in 5:
		var b := MeshInstance3D.new()
		var sm := SphereMesh.new()
		sm.radius = randf_range(0.12, 0.25)
		sm.height = sm.radius * 1.2
		b.mesh = sm
		b.material_override = Themes.toon(Color("#94673f"))
		var a := randf() * TAU
		b.position = Vector3(cos(a), 0.06, sin(a)) * randf_range(0.2, 0.9)
		add_child(b)
	# ride the ground
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 2.0, global_position + Vector3.DOWN * 4.0, 1)
	var hit := space.intersect_ray(q)
	if hit:
		global_position = hit.position + Vector3.UP * 0.03

func _physics_process(dt: float) -> void:
	life -= dt
	safe -= dt
	if life <= 0.0:
		queue_free()
		return
	for k in race.karts:
		if k == owner_kart and safe > 0.0:
			continue
		if k.global_position.distance_to(global_position) < 1.6:
			k.hit(Items.hit_kind(), owner_kart)
			Fx.puff(get_parent(), global_position, Color(0.48, 0.32, 0.21, 0.8))
			queue_free()
			return
