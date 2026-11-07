extends Node3D
## Developer: every pilot in its kart on a lawn, for sizing (data in roster.gd).
##   godot --path . -- --scene=lineup --shot=/tmp/l.png

func _ready() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color("#cfe9ff")
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.8, 0.85, 1.0)
	e.ambient_light_energy = 0.6
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.environment = e
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	sun.shadow_enabled = true
	add_child(sun)
	var g := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(80, 80)
	g.mesh = pm
	g.material_override = Themes.toon(Color("#7cc45e"))
	add_child(g)
	var ids: Array = Roster.ids()
	var only := Dev.arg("only")
	if only != "":
		ids = Array(only.split(","))
	var cols := int(Dev.arg("cols", "7"))
	for i in ids.size():
		var k := Kart.new()
		k.setup(null, ids[i], Garage.kart_for(ids[i]))
		add_child(k)
		var row := i / cols
		var col := i % cols
		k.position = Vector3((col - (cols - 1) * 0.5) * 1.95 + (0.9 if row % 2 == 1 else 0.0), 0, row * 2.6)
		k.rotation.y = PI * 0.88
		var l := Label3D.new()
		l.text = Roster.display_name(ids[i])
		l.font_size = 40
		l.outline_size = 10
		l.position = Vector3(0, 0.05, 1.0)
		l.rotation = Vector3(-PI / 2, PI, 0)
		l.outline_modulate = Color("#4a3426")
		l.modulate = Color("#fff7e6")
		l.pixel_size = 0.008
		k.add_child(l)
	var cam := Camera3D.new()
	cam.fov = 30
	add_child(cam)
	var rows := (ids.size() + cols - 1) / cols
	var dist := cols * 1.95 / (2.0 * tan(deg_to_rad(15.0))) * float(Dev.arg("zoom", "0.62")) + rows * 1.3
	var look := Vector3(0.45 if rows > 1 else 0.0, 0.75, (rows - 1) * 1.3)
	cam.position = look + Vector3(0, dist * 0.42, dist)
	cam.look_at(look, Vector3.UP)
