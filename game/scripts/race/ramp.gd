class_name Ramp
extends StaticBody3D
## A jump ramp across the road (or part of it): a wedge that lifts karts;
## the lip gives a trick window (see Kart.trick).

var width := 8.0
var length := 5.0
var height := 1.1

func _ready() -> void:
	add_to_group("road")
	add_to_group("ramp")
	var hw := width * 0.5
	# wedge: low edge at z=+length/2 (behind), lip at z=-length/2 (ahead)
	var b := length * 0.5
	var pts := PackedVector3Array([
		Vector3(-hw, 0, b), Vector3(hw, 0, b), Vector3(hw, 0, -b), Vector3(-hw, 0, -b),
		Vector3(-hw, height, -b), Vector3(hw, height, -b)])
	var cs := CollisionShape3D.new()
	var sh := ConvexPolygonShape3D.new()
	sh.points = pts
	cs.shape = sh
	add_child(cs)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var slope_n := Vector3(0, length, height).normalized()
	_tri(st, pts[0], pts[1], pts[5], slope_n, [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1)])
	_tri(st, pts[0], pts[5], pts[4], slope_n, [Vector2(0, 0), Vector2(1, 1), Vector2(0, 1)])
	_tri(st, pts[3], pts[4], pts[5], Vector3(0, 0, -1), [Vector2(0, 0), Vector2(0, 1), Vector2(1, 1)])
	_tri(st, pts[3], pts[5], pts[2], Vector3(0, 0, -1), [Vector2(0, 0), Vector2(1, 1), Vector2(1, 0)])
	_tri(st, pts[1], pts[2], pts[5], Vector3(1, 0, 0), [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1)])
	_tri(st, pts[0], pts[4], pts[3], Vector3(-1, 0, 0), [Vector2(0, 0), Vector2(1, 1), Vector2(1, 0)])
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	var m := ShaderMaterial.new()
	m.shader = preload("res://shaders/fx_boost.gdshader")
	m.set_shader_parameter("c1", Color("#ffd35a"))
	m.set_shader_parameter("c2", Color("#3a3346"))
	mi.material_override = m
	add_child(mi)

func _tri(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, nn: Vector3, uv: Array) -> void:
	for i in 3:
		st.set_normal(nn)
		st.set_uv(uv[i])
		st.add_vertex([a, b, c][i])
