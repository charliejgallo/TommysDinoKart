class_name Fx
## Particle effects made in code: drift sparks, dust, exhaust flame,
## one-shot bursts and puffs, the shield bubble.

static func _mat(col: Color, size: float, spread: float, vel: Vector2, grav: Vector3, life_scale := 1.0) -> ParticleProcessMaterial:
	var m := ParticleProcessMaterial.new()
	m.direction = Vector3(0, 1, 0.6)
	m.spread = spread
	m.initial_velocity_min = vel.x
	m.initial_velocity_max = vel.y
	m.gravity = grav
	m.scale_min = size * 0.6
	m.scale_max = size
	m.color = col
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	var gt := GradientTexture1D.new()
	gt.gradient = g
	m.color_ramp = gt
	var c := Curve.new()
	c.add_point(Vector2(0, 1))
	c.add_point(Vector2(1, 0.3 * life_scale))
	var ct := CurveTexture.new()
	ct.curve = c
	m.scale_curve = ct
	return m

static func _quad(emissive: bool, size := 0.18) -> QuadMesh:
	var q := QuadMesh.new()
	q.size = Vector2(size, size)
	var sm := StandardMaterial3D.new()
	sm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sm.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	sm.vertex_color_use_as_albedo = true
	sm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	sm.albedo_texture = _dot()
	if emissive:
		sm.emission_enabled = true
		sm.emission = Color(1, 1, 1)
		sm.emission_energy_multiplier = 2.0
	q.material = sm
	return q

static var _dot_tex: GradientTexture2D
static func _dot() -> GradientTexture2D:
	if _dot_tex == null:
		_dot_tex = GradientTexture2D.new()
		var g := Gradient.new()
		g.set_color(0, Color(1, 1, 1, 1))
		g.add_point(0.55, Color(1, 1, 1, 0.9))
		g.set_color(g.get_point_count() - 1, Color(1, 1, 1, 0))
		_dot_tex.gradient = g
		_dot_tex.fill = GradientTexture2D.FILL_RADIAL
		_dot_tex.fill_from = Vector2(0.5, 0.5)
		_dot_tex.fill_to = Vector2(1.0, 0.5)
		_dot_tex.width = 64
		_dot_tex.height = 64
	return _dot_tex

static func drift_sparks() -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.amount = 40
	p.lifetime = 0.35
	p.process_material = _mat(Color("#5ec8ff"), 1.0, 35.0, Vector2(2.0, 5.0), Vector3(0, -12, 0))
	p.draw_pass_1 = _quad(true, 0.14)
	p.emitting = false
	p.local_coords = false
	return p

static func tint(p: GPUParticles3D, c: Color) -> void:
	(p.process_material as ParticleProcessMaterial).color = c

static func dust() -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.amount = 24
	p.lifetime = 0.8
	var m := _mat(Color(0.86, 0.78, 0.62, 0.55), 2.6, 50.0, Vector2(0.5, 1.6), Vector3(0, 0.6, 0))
	p.process_material = m
	p.draw_pass_1 = _quad(false, 0.6)
	p.emitting = false
	p.local_coords = false
	return p

static func exhaust_flame() -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.amount = 30
	p.lifetime = 0.25
	var m := _mat(Color("#ffb347"), 1.0, 12.0, Vector2(3.0, 5.0), Vector3.ZERO)
	m.direction = Vector3(0, 0.2, 1)
	p.lifetime = 0.16
	p.process_material = m
	p.draw_pass_1 = _quad(true, 0.22)
	p.emitting = false
	p.local_coords = false
	return p

static func burst(parent: Node, at: Vector3, col: Color, amount := 16) -> void:
	if parent == null:
		return
	var p := GPUParticles3D.new()
	p.amount = amount
	p.lifetime = 0.7
	p.one_shot = true
	p.explosiveness = 0.95
	var m := _mat(col, 2.0, 180.0, Vector2(3.0, 7.0), Vector3(0, -9, 0))
	m.direction = Vector3.UP
	p.process_material = m
	p.draw_pass_1 = _quad(true, 0.25)
	parent.add_child(p)
	p.global_position = at
	p.emitting = true
	p.finished.connect(p.queue_free)

static func puff(parent: Node, at: Vector3, col: Color) -> void:
	if parent == null:
		return
	var p := GPUParticles3D.new()
	p.amount = 10
	p.lifetime = 0.6
	p.one_shot = true
	p.explosiveness = 0.9
	var m := _mat(col, 3.0, 80.0, Vector2(1.0, 2.5), Vector3(0, 0.5, 0))
	m.direction = Vector3.UP
	p.process_material = m
	p.draw_pass_1 = _quad(false, 0.7)
	parent.add_child(p)
	p.global_position = at
	p.emitting = true
	p.finished.connect(p.queue_free)

static var _bubble: ShaderMaterial
static func bubble_material() -> ShaderMaterial:
	if _bubble == null:
		_bubble = ShaderMaterial.new()
		var sh := Shader.new()
		sh.code = """shader_type spatial;
render_mode blend_add, unshaded, cull_back, depth_draw_never;
void fragment() {
	float f = 1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	vec3 rb = 0.5 + 0.5 * cos(6.2831 * (f * 1.5 + TIME * 0.3 + vec3(0.0, 0.33, 0.67)));
	ALBEDO = mix(vec3(0.6, 0.9, 1.0), rb, 0.5) * (pow(f, 2.5) * 1.4 + 0.04);
}"""
		_bubble.shader = sh
	return _bubble
