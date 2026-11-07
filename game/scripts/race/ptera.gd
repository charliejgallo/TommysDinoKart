class_name Ptera
## The pterosaur that rescues karts that fall (and carries them on the
## "Aventón de Ptera" item): the Dino Zoo adult ptera, flapping.

static func make() -> Node3D:
	var root := Node3D.new()
	var m: Node3D = (load("res://assets/props/ptera_adult.glb") as PackedScene).instantiate()
	Look.apply(m)
	m.rotation.y = PI
	m.scale = Vector3.ONE * 1.6
	root.add_child(m)
	var ap: AnimationPlayer = m.find_child("AnimationPlayer", true, false)
	if ap and ap.has_animation("fly"):
		ap.get_animation("fly").loop_mode = Animation.LOOP_LINEAR
		ap.play("fly")
	# a rope / harness down to the kart
	var rope := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.03
	cm.bottom_radius = 0.03
	cm.height = 1.6
	rope.mesh = cm
	rope.material_override = Themes.toon(Color("#c9a46a"))
	rope.position = Vector3(0, -0.8, 0)
	root.add_child(rope)
	return root
