class_name BoostPad
extends Area3D
## A dash panel on the road: karts that cross it get a turbo.

func _ready() -> void:
	collision_layer = 4
	collision_mask = 2
	var cs := CollisionShape3D.new()
	var bx := BoxShape3D.new()
	bx.size = Vector3(3.0, 1.2, 3.6)
	cs.shape = bx
	cs.position.y = 0.5
	add_child(cs)
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(3.0, 3.6)
	mi.mesh = pm
	var m := ShaderMaterial.new()
	m.shader = preload("res://shaders/fx_boost.gdshader")
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# chevrons point along -Z (forward) : flip the plane's V
	mi.rotation.y = PI
	add_child(mi)
	body_entered.connect(func(b): if b.has_method("boost"): b.boost(1.1, true))
