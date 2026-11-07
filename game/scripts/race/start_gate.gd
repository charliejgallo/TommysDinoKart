class_name StartGate
extends Node3D
## Start / finish line: checkered strip on the road and an arch with a
## banner, made of two big bones and a fern garland.

func setup(t: Track) -> void:
	var xf := t.frame_at(0.0, 0.0, 0.0)
	transform = xf
	var w := t.width[0] + 2.0 * Track.CURB
	# checkered strip
	var strip := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(w, 1.6)
	strip.mesh = pm
	var sm := ShaderMaterial.new()
	var sh := Shader.new()
	sh.code = """shader_type spatial;
uniform vec2 cells = vec2(16.0, 2.0);
void fragment() {
	vec2 c = floor(UV * cells);
	float k = mod(c.x + c.y, 2.0);
	ALBEDO = mix(vec3(0.1, 0.1, 0.12), vec3(0.97, 0.96, 0.92), k);
	ROUGHNESS = 0.8;
}"""
	sm.shader = sh
	sm.set_shader_parameter("cells", Vector2(round(w / 0.8), 2.0))
	strip.material_override = sm
	strip.position.y = 0.04
	add_child(strip)
	var col: Color = t.theme.get("gate", Color("#fff3df"))
	var acc: Color = t.theme.get("gate_acc", Color("#ef5b4c"))
	for s: float in [-1.0, 1.0]:
		var post := MeshInstance3D.new()
		var cm := CylinderMesh.new()
		cm.top_radius = 0.45
		cm.bottom_radius = 0.55
		cm.height = 7.0
		post.mesh = cm
		post.material_override = Themes.toon(col)
		post.position = Vector3(s * (w * 0.5 + 0.8), 3.5, 0)
		add_child(post)
		for yy in [0.2, 7.0]:
			var knob := MeshInstance3D.new()
			var sp := SphereMesh.new()
			sp.radius = 0.75
			sp.height = 1.3
			knob.mesh = sp
			knob.material_override = Themes.toon(col)
			knob.position = Vector3(s * (w * 0.5 + 0.8), yy, 0)
			add_child(knob)
	var banner := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(w + 1.0, 1.5, 0.3)
	banner.mesh = bm
	banner.material_override = Themes.toon(acc)
	banner.position = Vector3(0, 6.6, 0)
	add_child(banner)
	for z in [-0.17, 0.17]:
		var lab := Label3D.new()
		lab.text = tr("TOMMY'S DINO KART")
		lab.font_size = 96
		lab.outline_size = 18
		lab.modulate = Color("#fff7e6")
		lab.outline_modulate = Color("#3a3346")
		lab.pixel_size = 0.0105
		lab.position = Vector3(0, 6.6, z)
		if z < 0:
			lab.rotation.y = PI
		add_child(lab)
