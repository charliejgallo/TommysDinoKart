extends Node3D
## Developer: renders the menu pictures.
##   --scene=portraits  -> assets/ui/portraits/<driver>.png (kart + pilot, 3/4 front,
##                         transparent background, 512x512)

func _ready() -> void:
	get_viewport().transparent_bg = true
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_CLEAR_COLOR
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.85, 0.88, 1.0)
	e.ambient_light_energy = 0.7
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.environment = e
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, 35, 0)
	add_child(sun)
	var cam := Camera3D.new()
	cam.fov = 26
	add_child(cam)
	cam.position = Vector3(2.4, 1.7, -3.6)
	cam.look_at(Vector3(0, 0.62, 0), Vector3.UP)
	cam.current = true
	DirAccess.make_dir_recursive_absolute("res://assets/ui/portraits")
	for id in Roster.ids():
		var k := Kart.new()
		k.setup(null, id, Garage.kart_for(id))
		add_child(k)
		await get_tree().process_frame
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var sz := mini(img.get_width(), img.get_height())
		img = img.get_region(Rect2i((img.get_width() - sz) / 2, (img.get_height() - sz) / 2, sz, sz))
		img.resize(512, 512, Image.INTERPOLATE_LANCZOS)
		img.save_png("res://assets/ui/portraits/%s.png" % id)
		print("[portrait] ", id)
		k.free()
	get_tree().quit()
