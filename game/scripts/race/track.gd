class_name Track
extends Node3D
## A race track built at load time from data/tracks/<id>.json.
##
## The JSON gives a closed loop of control points [x, z, y, width, bank?]
## (metres, bank in degrees, + = right edge up), and the builder makes:
##   * the centre line: a Catmull-Rom curve sampled every STEP metres into
##     packed arrays (pos, fwd, right, up, width, dist) used by everything
##     else (progress, AI, respawn, item placement);
##   * the road surface + curbs + a skirt that hides the terrain seam, with
##     one trimesh collider (group "road");
##   * the terrain: a height grid that hugs the road and blends into the
##     theme's landscape (hills, canyon walls, islands), HeightMapShape3D
##     collider (group "offroad": slows karts);
##   * water plane, sky, light, fog from the theme;
##   * decoration: scattered props (MultiMesh) away from the road, set pieces;
##   * start gate, item eggs, boost pads and ramps at fractions of the lap.
##
## Coordinates: Godot (Y up). The lap runs in the order of the points; the
## start line is at distance 0 (the first point).

const STEP := 2.0
const TERRAIN_CELL := 2.5
const BLEND := 34.0           # metres over which terrain leaves the road height
const CURB := 0.9
const LOOK := preload("res://scripts/core/look.gd")

var data := {}
var theme := {}
var pos := PackedVector3Array()
var fwd := PackedVector3Array()
var right := PackedVector3Array()
var up := PackedVector3Array()
var width := PackedFloat32Array()
var dist := PackedFloat32Array()
var bridge := PackedByteArray()
var length := 0.0
var n := 0
var _hash := {}
var water_y := -1000.0
var kill_y := -1000.0
var grid := {}                 # terrain grid info for height queries
var item_spots := []           # [Vector3] centres of item egg rows
var spawn := []                # [Transform3D] grid slots, pole first

static func load_data(id: String) -> Dictionary:
	var f := FileAccess.open("res://data/tracks/%s.json" % id, FileAccess.READ)
	if f == null:
		push_error("track %s missing" % id)
		return {}
	return JSON.parse_string(f.get_as_text())

func build(d: Dictionary) -> void:
	data = d
	theme = Themes.get_theme(d.get("theme", "meadow")).duplicate(true)
	for k in d.get("theme_over", {}):
		theme[k] = d["theme_over"][k]
	_centre_line()
	_build_env()
	_build_road()
	_build_terrain()
	_build_water()
	_build_decor()
	_build_furniture()
	_build_spawn()

# ------------------------------------------------------------ centre line
func _centre_line() -> void:
	var cp: Array = data["pts"]
	var m := cp.size()
	var P := []
	for c in cp:
		P.append(Vector3(c[0], c[2], c[1]))
	# dense Catmull-Rom polyline, then resample by arc length
	var dense := []
	var dw := []
	var db := []
	var dbr := []
	var br_set := {}
	for span in data.get("bridges", []):
		var i0: int = span[0]
		var i1: int = span[1]
		var i := i0
		while true:
			br_set[i % m] = true
			if i % m == i1 % m:
				break
			i += 1
	for i in m:
		var p0: Vector3 = P[(i - 1 + m) % m]
		var p1: Vector3 = P[i]
		var p2: Vector3 = P[(i + 1) % m]
		var p3: Vector3 = P[(i + 2) % m]
		var w1: float = cp[i][3]
		var w2: float = cp[(i + 1) % m][3]
		var b1: float = cp[i][4] if cp[i].size() > 4 else 0.0
		var b2: float = cp[(i + 1) % m][4] if cp[(i + 1) % m].size() > 4 else 0.0
		var segs := int(ceil(p1.distance_to(p2) / 0.5)) + 1
		for s in segs:
			var t := float(s) / segs
			dense.append(_cr(p0, p1, p2, p3, t))
			var e := t * t * (3.0 - 2.0 * t)
			dw.append(lerpf(w1, w2, e))
			db.append(lerpf(b1, b2, e))
			dbr.append(1 if (br_set.has(i) and br_set.has((i + 1) % m)) else 0)
	# cumulative length
	var cum := PackedFloat32Array()
	cum.resize(dense.size() + 1)
	cum[0] = 0.0
	for i in dense.size():
		cum[i + 1] = cum[i] + (dense[i] as Vector3).distance_to(dense[(i + 1) % dense.size()])
	length = cum[dense.size()]
	n = int(round(length / STEP))
	var step := length / n
	pos.resize(n); fwd.resize(n); right.resize(n); up.resize(n)
	width.resize(n); dist.resize(n); bridge.resize(n)
	var bank := PackedFloat32Array()
	bank.resize(n)
	var j := 0
	for k in n:
		var s := k * step
		while j < dense.size() - 1 and cum[j + 1] < s:
			j += 1
		var seg := maxf(cum[j + 1] - cum[j], 0.0001)
		var t := (s - cum[j]) / seg
		var a: Vector3 = dense[j]
		var b: Vector3 = dense[(j + 1) % dense.size()]
		pos[k] = a.lerp(b, t)
		width[k] = lerpf(dw[j], dw[(j + 1) % dense.size()], t)
		bank[k] = lerpf(db[j], db[(j + 1) % dense.size()], t)
		bridge[k] = dbr[j]
		dist[k] = s
	for k in n:
		var f := (pos[(k + 1) % n] - pos[(k - 1 + n) % n]).normalized()
		fwd[k] = f
		var r := f.cross(Vector3.UP).normalized()
		var u := r.cross(f).normalized()
		var bq := Basis(f, deg_to_rad(bank[k]))
		right[k] = bq * r
		up[k] = bq * u
	# spatial hash (cells of 12 m) for nearest-sample queries
	for k in n:
		var key := _cell(pos[k])
		if not _hash.has(key):
			_hash[key] = PackedInt32Array()
		_hash[key].append(k)

static func _cr(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: float) -> Vector3:
	var t2 := t * t
	var t3 := t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 +
		(-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)

func _cell(p: Vector3) -> Vector2i:
	return Vector2i(int(floor(p.x / 12.0)), int(floor(p.z / 12.0)))

## Index of the centre-line sample nearest to p. With a hint (last known
## index) only a window around it is searched, so crossings and parallel
## stretches never make a kart jump ahead.
func nearest(p: Vector3, hint := -1) -> int:
	var best := -1
	var bd := INF
	if hint >= 0:
		for o in range(-12, 25):
			var k := (hint + o + n) % n
			var d := pos[k].distance_squared_to(p)
			if d < bd:
				bd = d
				best = k
		if bd < 30.0 * 30.0:
			return best
	var c := _cell(p)
	for r in range(0, 6):
		for dx in range(-r, r + 1):
			for dz in range(-r, r + 1):
				if maxi(absi(dx), absi(dz)) != r:
					continue
				var key := Vector2i(c.x + dx, c.y + dz)
				if not _hash.has(key):
					continue
				for k in _hash[key]:
					var d := pos[k].distance_squared_to(p)
					if d < bd:
						bd = d
						best = k
		if best >= 0 and r >= 1:
			break
	return maxi(best, 0)

## Distance along the lap (0..length) of p, refined between samples.
func progress_at(p: Vector3, k: int) -> float:
	var t := (p - pos[k]).dot(fwd[k])
	return fposmod(dist[k] + t, length)

func lateral_at(p: Vector3, k: int) -> float:
	return (p - pos[k]).dot(right[k])

func index_at_dist(s: float) -> int:
	return int(round(fposmod(s, length) / length * n)) % n

func point_at(s: float, lat := 0.0) -> Vector3:
	var k := index_at_dist(s)
	return pos[k] + right[k] * lat

func frame_at(s: float, lat := 0.0, lift := 0.0) -> Transform3D:
	var k := index_at_dist(s)
	var b := Basis(right[k], up[k], -fwd[k])
	return Transform3D(b, pos[k] + right[k] * lat + up[k] * lift)

func curvature_at(k: int, ahead := 6) -> float:
	## heading change (radians) over the next `ahead` samples
	var a := fwd[k]
	var b := fwd[(k + ahead) % n]
	return Vector2(a.x, a.z).angle_to(Vector2(b.x, b.z))

# ------------------------------------------------------------ environment
func _build_env() -> void:
	var env := Environment.new()
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sky_top_color = theme.sky_top
	sm.sky_horizon_color = theme.sky_horizon
	sm.ground_horizon_color = theme.sky_horizon
	sm.ground_bottom_color = theme.ground_far
	sm.sun_angle_max = 30.0
	sm.sky_curve = 0.12
	sm.sky_energy_multiplier = theme.get("sky_energy", 1.0)
	sky.sky_material = sm
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = theme.get("ambient", 0.9)
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = theme.get("exposure", 1.0)
	env.ssao_enabled = Settings.quality >= 1
	env.ssao_radius = 1.2
	env.ssao_intensity = 1.4
	env.glow_enabled = true
	env.glow_intensity = 0.5
	env.glow_bloom = 0.04
	env.glow_hdr_threshold = 1.1
	env.fog_enabled = true
	env.fog_light_color = theme.fog
	env.fog_density = theme.get("fog_density", 0.0022)
	env.fog_sky_affect = 0.25
	env.fog_aerial_perspective = 0.4
	env.adjustment_enabled = true
	env.adjustment_saturation = theme.get("saturation", 1.12)
	env.adjustment_contrast = 1.04
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.light_color = theme.sun
	sun.light_energy = theme.get("sun_energy", 1.25)
	sun.rotation_degrees = Vector3(theme.get("sun_pitch", -52.0), theme.get("sun_yaw", 35.0), 0)
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = 140.0
	sun.shadow_blur = 1.2
	add_child(sun)
	if theme.get("clouds", true):
		_clouds()

func _clouds() -> void:
	var puff := ArrayMesh.new()
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in 6:
		var sm := SphereMesh.new()
		sm.radial_segments = 16
		sm.rings = 8
		var r := rng.randf_range(0.6, 1.0)
		sm.radius = r
		sm.height = r * 1.6
		var off := Vector3((i - 2.5) * 0.75, rng.randf_range(-0.1, 0.35) + (0.3 if i in [2, 3] else 0.0), rng.randf_range(-0.3, 0.3))
		st.append_from(sm, 0, Transform3D(Basis(), off))
	st.commit(puff)
	var mat := ShaderMaterial.new()
	mat.shader = preload("res://shaders/cloud.gdshader")
	mat.set_shader_parameter("top", theme.get("cloud_top", Color(1, 1, 1)))
	mat.set_shader_parameter("bottom", theme.get("cloud_bottom", Color(0.8, 0.85, 0.98)))
	puff.surface_set_material(0, mat)
	var xf := []
	var c := Vector3.ZERO
	for p in pos:
		c += p
	c /= maxf(n, 1)
	for i in int(theme.get("cloud_count", 26)):
		var a := rng.randf() * TAU
		var d := rng.randf_range(420.0, 640.0)
		var s := rng.randf_range(16.0, 30.0)
		var p := c + Vector3(cos(a) * d, rng.randf_range(70.0, 150.0), sin(a) * d)
		xf.append(Transform3D(Basis(Vector3.UP, -a + PI * 0.5).scaled(Vector3(s, s * 0.8, s)), p))
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = puff
	mm.instance_count = xf.size()
	for i in xf.size():
		mm.set_instance_transform(i, xf[i])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)

# ------------------------------------------------------------ road
func _build_road() -> void:
	var road := SurfaceTool.new()
	var curb := SurfaceTool.new()
	var skirt := SurfaceTool.new()
	road.begin(Mesh.PRIMITIVE_TRIANGLES)
	curb.begin(Mesh.PRIMITIVE_TRIANGLES)
	skirt.begin(Mesh.PRIMITIVE_TRIANGLES)
	var cols := PackedVector3Array()
	const NX := 6
	var curbs: bool = theme.get("curbs", true)
	for k in n + 1:
		var i := k % n
		var v := dist[i] if k < n else length
		var hw := width[i] * 0.5
		var p := pos[i]
		var r := right[i]
		var u := up[i]
		var j := (k + 1) % n
		if k == n:
			continue
		var i2 := (k + 1) % n
		var v2 := dist[i2] if k + 1 < n else length
		var hw2 := width[i2] * 0.5
		var p2 := pos[i2]
		var r2 := right[i2]
		var u2 := up[i2]
		# road strip across in NX quads
		for x in NX:
			var a0 := -1.0 + 2.0 * x / NX
			var a1 := -1.0 + 2.0 * (x + 1) / NX
			var A := p + r * hw * a0
			var B := p + r * hw * a1
			var Cc := p2 + r2 * hw2 * a1
			var D := p2 + r2 * hw2 * a0
			_quad(road, A, B, Cc, D, u, u2, Vector2(x / float(NX), v / 4.0), Vector2((x + 1) / float(NX), v2 / 4.0))
			cols.append_array([A, B, Cc, A, Cc, D])
		# curbs / shoulders, then skirt down to the terrain
		for side: float in [-1.0, 1.0]:
			var e0 := p + r * hw * side
			var e1 := p2 + r2 * hw2 * side
			var lift := 0.06 if curbs else 0.0
			var o0 := p + r * (hw + CURB) * side + u * lift
			var o1 := p2 + r2 * (hw2 + CURB) * side + u2 * lift
			var m0 := p + r * (hw + CURB * 0.5) * side + u * (lift * 1.6)
			var m1 := p2 + r2 * (hw2 + CURB * 0.5) * side + u2 * (lift * 1.6)
			if side < 0:
				_quad(curb, o0, m0, m1, o1, u, u2, Vector2(0, v / 3.0), Vector2(0.5, v2 / 3.0))
				_quad(curb, m0, e0, e1, m1, u, u2, Vector2(0.5, v / 3.0), Vector2(1, v2 / 3.0))
				cols.append_array([o0, m0, m1, o0, m1, o1, m0, e0, e1, m0, e1, m1])
			else:
				_quad(curb, e0, m0, m1, e1, u, u2, Vector2(1, v / 3.0), Vector2(0.5, v2 / 3.0))
				_quad(curb, m0, o0, o1, m1, u, u2, Vector2(0.5, v / 3.0), Vector2(0, v2 / 3.0))
				cols.append_array([e0, m0, m1, e0, m1, e1, m0, o0, o1, m0, o1, m1])
			# shoulder: a gentle ramp down from the curb (with collision) so a
			# kart that runs wide can always drive back up; bridges just drop
			var isb := bridge[i] == 1
			var out := 0.6 if isb else 3.2
			var drop := 0.7 if isb else 1.1
			var d0 := o0 + r * out * side - Vector3.UP * drop
			var d1 := o1 + r2 * out * side - Vector3.UP * drop
			var n0 := (r * side * (0.9 if isb else 0.33) + u).normalized()
			if side < 0:
				_quad(skirt, d0, o0, o1, d1, n0, n0, Vector2(0, v), Vector2(1, v2))
				if not isb:
					cols.append_array([d0, o0, o1, d0, o1, d1])
			else:
				_quad(skirt, o0, d0, d1, o1, n0, n0, Vector2(0, v), Vector2(1, v2))
				if not isb:
					cols.append_array([o0, d0, d1, o0, d1, o1])
	var mi := MeshInstance3D.new()
	var mesh := ArrayMesh.new()
	road.generate_tangents()
	road.commit(mesh)
	curb.commit(mesh)
	skirt.commit(mesh)
	mesh.surface_set_material(0, Themes.road_material(theme))
	mesh.surface_set_material(1, Themes.curb_material(theme))
	mesh.surface_set_material(2, Themes.skirt_material(theme))
	mi.mesh = mesh
	mi.name = "Road"
	add_child(mi)
	var body := StaticBody3D.new()
	body.name = "RoadBody"
	body.add_to_group("road")
	body.collision_layer = 1
	var cs := CollisionShape3D.new()
	var sh := ConcavePolygonShape3D.new()
	sh.set_faces(cols)
	sh.backface_collision = true
	cs.shape = sh
	body.add_child(cs)
	add_child(body)
	_build_bridges()

func _quad(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3, n0: Vector3, n1: Vector3,
		uv0: Vector2, uv1: Vector2) -> void:
	# a,b on the near row; d,c on the far row (counter-clockwise seen from above
	# when a->b runs left to right and the strip goes forward)
	st.set_normal(n0); st.set_uv(Vector2(uv0.x, uv0.y)); st.add_vertex(a)
	st.set_normal(n1); st.set_uv(Vector2(uv1.x, uv1.y)); st.add_vertex(c)
	st.set_normal(n0); st.set_uv(Vector2(uv1.x, uv0.y)); st.add_vertex(b)
	st.set_normal(n0); st.set_uv(Vector2(uv0.x, uv0.y)); st.add_vertex(a)
	st.set_normal(n1); st.set_uv(Vector2(uv0.x, uv1.y)); st.add_vertex(d)
	st.set_normal(n1); st.set_uv(Vector2(uv1.x, uv1.y)); st.add_vertex(c)

func _build_bridges() -> void:
	## railings and pillars on bridge stretches
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var walls := PackedVector3Array()
	var any := false
	for k in n:
		if bridge[k] == 0 or bridge[(k + 1) % n] == 0:
			continue
		any = true
		var i2 := (k + 1) % n
		for side: float in [-1.0, 1.0]:
			var a := pos[k] + right[k] * (width[k] * 0.5 + CURB) * side
			var b := pos[i2] + right[i2] * (width[i2] * 0.5 + CURB) * side
			var h := Vector3.UP * 0.9
			var nn := right[k] * -side
			if side > 0:
				_quad(st, a, b, b + h, a + h, nn, nn, Vector2(0, 0), Vector2(1, 1))
			else:
				_quad(st, b, a, a + h, b + h, nn, nn, Vector2(0, 0), Vector2(1, 1))
			walls.append_array([a, b, b + h * 1.5, a, b + h * 1.5, a + h * 1.5])
		if k % 8 == 0:
			var pil := MeshInstance3D.new()
			var cm := CylinderMesh.new()
			var hgt := pos[k].y - water_level_guess() + 2.0
			cm.top_radius = 0.9
			cm.bottom_radius = 1.1
			cm.height = maxf(hgt, 2.0)
			pil.mesh = cm
			pil.material_override = Themes.toon(theme.get("pillar", Color(0.75, 0.66, 0.55)))
			pil.position = pos[k] - Vector3.UP * (cm.height * 0.5 + 0.6)
			add_child(pil)
	if not any:
		return
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	mi.material_override = Themes.toon(theme.get("rail", Color(0.95, 0.85, 0.6)))
	add_child(mi)
	var body := StaticBody3D.new()
	body.add_to_group("wall")
	var cs := CollisionShape3D.new()
	var sh := ConcavePolygonShape3D.new()
	sh.set_faces(walls)
	sh.backface_collision = true
	cs.shape = sh
	body.add_child(cs)
	add_child(body)

func water_level_guess() -> float:
	return data.get("water", theme.get("base_h", 0.0) - 4.0)

# ------------------------------------------------------------ terrain
func _build_terrain() -> void:
	var lo := Vector2(INF, INF)
	var hi := Vector2(-INF, -INF)
	for p in pos:
		lo = Vector2(minf(lo.x, p.x), minf(lo.y, p.z))
		hi = Vector2(maxf(hi.x, p.x), maxf(hi.y, p.z))
	var margin: float = theme.get("margin", 170.0)
	lo -= Vector2(margin, margin)
	hi += Vector2(margin, margin)
	var c := TERRAIN_CELL
	var nx := int(ceil((hi.x - lo.x) / c)) + 1
	var nz := int(ceil((hi.y - lo.y) / c)) + 1
	var cnt := nx * nz
	var dbest := PackedFloat32Array()
	dbest.resize(cnt)
	dbest.fill(1e9)
	var hroad := PackedFloat32Array()
	hroad.resize(cnt)
	var wroad := PackedFloat32Array()
	wroad.resize(cnt)
	var rad := BLEND + 12.0
	var cr := int(ceil(rad / c))
	var bcell := PackedByteArray()
	bcell.resize(cnt)
	var base_h0: float = theme.get("base_h", 0.0) - 2.0
	for k in n:
		var p := pos[k]
		var gx := int(round((p.x - lo.x) / c))
		var gz := int(round((p.z - lo.y) / c))
		var drop := 0.12 + absf(right[k].y) * width[k] * 0.5
		var isb := bridge[k] == 1
		for dz in range(-cr, cr + 1):
			var z := gz + dz
			if z < 0 or z >= nz:
				continue
			for dx in range(-cr, cr + 1):
				var x := gx + dx
				if x < 0 or x >= nx:
					continue
				var q := Vector2(lo.x + x * c - p.x, lo.y + z * c - p.z)
				var d := q.length()
				var id := z * nx + x
				if isb:
					d += 6.0        # a real road nearby wins over the bridge above it
				if d < dbest[id]:
					dbest[id] = d
					# under bridges the ground dips well below the deck
					hroad[id] = p.y - drop if not isb else minf(p.y - 9.0, base_h0)
					wroad[id] = width[k] * 0.5
					bcell[id] = 1 if isb else 0
	var noise := FastNoiseLite.new()
	noise.seed = hash(data.get("id", "x"))
	noise.frequency = theme.get("hill_freq", 0.006)
	noise.fractal_octaves = 4
	var noise2 := FastNoiseLite.new()
	noise2.seed = noise.seed + 7
	noise2.frequency = 0.03
	var base_h: float = theme.get("base_h", 0.0)
	var hills: float = theme.get("hills", 10.0)
	var rim_h: float = theme.get("rim_h", 0.0)
	var rim_d: float = theme.get("rim_d", 20.0)
	var rim_w: float = theme.get("rim_w", 10.0)
	var heights := PackedFloat32Array()
	heights.resize(cnt)
	var colors := PackedColorArray()
	colors.resize(cnt)
	var g1: Color = theme.grass
	var g2: Color = theme.grass2
	var sh_c: Color = theme.shoulder
	var rock_c: Color = theme.get("rock", Color(0.6, 0.55, 0.5))
	var edge_fade := 40.0
	for z in nz:
		for x in nx:
			var id := z * nx + x
			var wx := lo.x + x * c
			var wz := lo.y + z * c
			var nv := noise.get_noise_2d(wx, wz)
			var far := base_h + nv * hills + noise2.get_noise_2d(wx, wz) * 0.6
			var d := dbest[id]
			var h := far
			var edge_d := d - wroad[id]
			if d < 900.0:
				var t := clampf((edge_d - CURB - 0.5) / BLEND, 0.0, 1.0)
				t = t * t * (3.0 - 2.0 * t)
				var rim := 0.0
				if rim_h != 0.0 and bcell[id] == 0:
					rim = rim_h * clampf((edge_d - rim_d) / rim_w, 0.0, 1.0)
				h = lerpf(hroad[id], far + rim, t)
				if rim_h != 0.0 and edge_d > rim_d and bcell[id] == 0:
					h = maxf(h, hroad[id] + rim) if rim_h > 0 else minf(h, hroad[id] + rim)
			elif rim_h != 0.0:
				h = far + rim_h + (hroad[id] if hroad[id] != 0.0 else base_h) * 0.0
			# raise the far border into a soft bowl so the edge never shows
			var bx := minf(x, nx - 1 - x) * c
			var bz := minf(z, nz - 1 - z) * c
			var bd := minf(bx, bz)
			if bd < edge_fade:
				h += (1.0 - bd / edge_fade) * theme.get("edge_rise", 14.0)
			heights[id] = h
			var gcol := g1.lerp(g2, clampf(nv * 1.6 + 0.5, 0.0, 1.0))
			if d < 900.0 and edge_d < CURB + 2.6:
				gcol = sh_c.lerp(gcol, clampf((edge_d - CURB - 0.6) / 2.0, 0.0, 1.0))
			colors[id] = gcol
	# steep slopes look like rock
	for z in range(1, nz - 1):
		for x in range(1, nx - 1):
			var id := z * nx + x
			var sx := heights[id + 1] - heights[id - 1]
			var sz := heights[id + nx] - heights[id - nx]
			var slope := sqrt(sx * sx + sz * sz) / (2.0 * c)
			if slope > 0.7:
				colors[id] = colors[id].lerp(rock_c, clampf((slope - 0.7) * 2.0, 0.0, 1.0))
	grid = {"lo": lo, "nx": nx, "nz": nz, "c": c, "h": heights}
	# mesh
	var verts := PackedVector3Array()
	verts.resize(cnt)
	var norms := PackedVector3Array()
	norms.resize(cnt)
	for z in nz:
		for x in nx:
			var id := z * nx + x
			verts[id] = Vector3(lo.x + x * c, heights[id], lo.y + z * c)
			var hl := heights[id - 1] if x > 0 else heights[id]
			var hr := heights[id + 1] if x < nx - 1 else heights[id]
			var hd := heights[id - nx] if z > 0 else heights[id]
			var hu := heights[id + nx] if z < nz - 1 else heights[id]
			norms[id] = Vector3(hl - hr, 2.0 * c, hd - hu).normalized()
	var idx := PackedInt32Array()
	idx.resize((nx - 1) * (nz - 1) * 6)
	var w := 0
	for z in nz - 1:
		for x in nx - 1:
			var a := z * nx + x
			idx[w] = a; idx[w + 1] = a + 1; idx[w + 2] = a + nx
			idx[w + 3] = a + 1; idx[w + 4] = a + nx + 1; idx[w + 5] = a + nx
			w += 6
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_COLOR] = colors
	arr[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	mesh.surface_set_material(0, Themes.ground_material(theme))
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.name = "Terrain"
	add_child(mi)
	var body := StaticBody3D.new()
	body.name = "TerrainBody"
	body.add_to_group("offroad")
	var cs := CollisionShape3D.new()
	var hm := HeightMapShape3D.new()
	hm.map_width = nx
	hm.map_depth = nz
	hm.map_data = heights
	cs.shape = hm
	cs.scale = Vector3(c, 1.0, c)
	cs.position = Vector3(lo.x + (nx - 1) * c * 0.5, 0.0, lo.y + (nz - 1) * c * 0.5)
	body.add_child(cs)
	add_child(body)
	# a huge flat floor far below catches anything that leaves the grid
	kill_y = data.get("kill_y", minf(water_level_guess(), base_h - hills) - 6.0)

func ground_h(x: float, z: float) -> float:
	var lo: Vector2 = grid.lo
	var c: float = grid.c
	var fx := clampf((x - lo.x) / c, 0.0, grid.nx - 1.001)
	var fz := clampf((z - lo.y) / c, 0.0, grid.nz - 1.001)
	var ix := int(fx)
	var iz := int(fz)
	var tx := fx - ix
	var tz := fz - iz
	var H: PackedFloat32Array = grid.h
	var nx: int = grid.nx
	var a := lerpf(H[iz * nx + ix], H[iz * nx + ix + 1], tx)
	var b := lerpf(H[(iz + 1) * nx + ix], H[(iz + 1) * nx + ix + 1], tx)
	return lerpf(a, b, tz)

func _build_water() -> void:
	if not data.has("water") and not theme.has("water"):
		return
	water_y = data.get("water", theme.get("water", 0.0))
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(2400, 2400)
	mi.mesh = pm
	mi.position = Vector3(0, water_y, 0)
	mi.material_override = Themes.water_material(theme)
	mi.name = "Water"
	add_child(mi)
	kill_y = maxf(kill_y, water_y - 0.6)

# ------------------------------------------------------------ decoration
func _road_clear(p: Vector3, extra: float) -> bool:
	## true when p is at least `extra` metres outside every road edge
	var c := _cell(p)
	for dx in range(-2, 3):
		for dz in range(-2, 3):
			var key := Vector2i(c.x + dx, c.y + dz)
			if not _hash.has(key):
				continue
			for k in _hash[key]:
				var d := Vector2(p.x - pos[k].x, p.z - pos[k].z).length()
				if d < width[k] * 0.5 + CURB + extra:
					return false
	return true

func _build_decor() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(data.get("id", "x")) + 99
	var lo: Vector2 = grid.lo
	var span := Vector2(grid.nx * grid.c, grid.nz * grid.c)
	var solid := []
	for rule in theme.get("scatter", []) + data.get("scatter", []):
		var mesh := _prop_mesh(rule.m)
		if mesh == null:
			continue
		# the scatter area is the band around the road, not the whole map
		var band: float = minf(float(rule.get("max", 110.0)), 110.0) * 2.0 + 14.0
		var area := minf(span.x * span.y, band * length)
		var count := int(area * float(rule.get("d", 0.001)) * Settings.decor_density())
		var xforms := []
		var tries := count * 3
		while xforms.size() < count and tries > 0:
			tries -= 1
			var p := Vector3(lo.x + rng.randf() * span.x, 0, lo.y + rng.randf() * span.y)
			var mind: float = rule.get("min", 6.0)
			if not _road_clear(p, mind):
				continue
			if _road_clear(p, float(rule.get("max", 110.0))):
				continue
			p.y = ground_h(p.x, p.z)
			if water_y > -999.0 and p.y < water_y + float(rule.get("above_water", 0.3)):
				if not rule.get("in_water", false):
					continue
			var sc: Array = rule.get("s", [0.8, 1.3])
			var s := rng.randf_range(sc[0], sc[1])
			var b := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s, s))
			xforms.append(Transform3D(b, p - Vector3.UP * 0.05))
			if rule.get("solid", 0.0) > 0.0 and not _road_clear(p, 30.0) == true:
				solid.append([p, float(rule.solid) * s])
		_multimesh(mesh, xforms, float(rule.get("far", 0.0)))
	for sp in data.get("set", []):
		var node := _prop_scene(sp.m)
		if node == null:
			continue
		var p := Vector3(sp.p[0], 0, sp.p[1])
		p.y = sp.get("y", ground_h(p.x, p.z))
		node.position = p
		node.rotation.y = deg_to_rad(sp.get("r", 0.0))
		var s: float = sp.get("s", 1.0)
		node.scale = Vector3(s, s, s)
		add_child(node)
		if sp.has("solid"):
			solid.append([p, float(sp.solid) * s])
	# trunks / rocks near the road block karts (cylinders)
	if not solid.is_empty():
		var body := StaticBody3D.new()
		body.add_to_group("wall")
		for so in solid:
			var cs := CollisionShape3D.new()
			var cy := CylinderShape3D.new()
			cy.radius = so[1]
			cy.height = 8.0
			cs.shape = cy
			cs.position = so[0] + Vector3.UP * 3.0
			body.add_child(cs)
		add_child(body)

var _mesh_cache := {}

func _prop_mesh(m: String) -> Mesh:
	if _mesh_cache.has(m):
		return _mesh_cache[m]
	var node := _prop_scene(m)
	if node == null:
		_mesh_cache[m] = null
		return null
	# merge every MeshInstance (already toon-shaded) into one mesh
	var merged := ArrayMesh.new()
	for mi in node.find_children("*", "MeshInstance3D", true, false):
		var xf: Transform3D = (mi as MeshInstance3D).transform
		var par: Node = mi.get_parent()
		while par != node and par is Node3D:
			xf = (par as Node3D).transform * xf
			par = par.get_parent()
		var src: Mesh = mi.mesh
		for s in src.get_surface_count():
			var st := SurfaceTool.new()
			st.create_from(src, s)
			var arrs := st.commit_to_arrays()
			var vv: PackedVector3Array = arrs[Mesh.ARRAY_VERTEX]
			var nn: PackedVector3Array = arrs[Mesh.ARRAY_NORMAL]
			for i in vv.size():
				vv[i] = xf * vv[i]
				if nn.size() > i:
					nn[i] = (xf.basis * nn[i]).normalized()
			arrs[Mesh.ARRAY_VERTEX] = vv
			arrs[Mesh.ARRAY_NORMAL] = nn
			arrs[Mesh.ARRAY_TANGENT] = null
			merged.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrs)
			merged.surface_set_material(merged.get_surface_count() - 1, mi.get_active_material(s))
	node.free()
	_mesh_cache[m] = merged
	return merged

func _prop_scene(m: String) -> Node3D:
	var path := "res://assets/props/%s.glb" % m
	if not ResourceLoader.exists(path):
		path = "res://assets/scenery/%s.glb" % m
		if not ResourceLoader.exists(path):
			push_warning("prop %s missing" % m)
			return null
	var node: Node3D = (load(path) as PackedScene).instantiate()
	LOOK.apply(node)
	return node

const CHUNK := 72.0

func _multimesh(mesh: Mesh, xforms: Array, far := 0.0) -> void:
	## Instances are split into square chunks, each its own MultiMesh with a
	## visibility range, so the far ones are skipped and the frustum culls the
	## rest. Small things (below ~2.2 m) cast no shadow.
	if xforms.is_empty():
		return
	var h := mesh.get_aabb().size.y
	var chunks := {}
	for xf in xforms:
		var o: Vector3 = (xf as Transform3D).origin
		var key := Vector2i(int(floor(o.x / CHUNK)), int(floor(o.z / CHUNK)))
		if not chunks.has(key):
			chunks[key] = []
		chunks[key].append(xf)
	var vis_end: float = far if far > 0.0 else [150.0, 210.0, 270.0][clampi(Settings.quality, 0, 2)]
	for key in chunks:
		var list: Array = chunks[key]
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = mesh
		mm.instance_count = list.size()
		var sc_avg := 0.0
		for i in list.size():
			mm.set_instance_transform(i, list[i])
			sc_avg += (list[i] as Transform3D).basis.get_scale().y
		sc_avg /= list.size()
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.visibility_range_end = vis_end
		mmi.visibility_range_end_margin = 20.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
		if h * sc_avg < 2.2 or Settings.quality == 0:
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mmi)

# ------------------------------------------------------------ furniture
func _build_furniture() -> void:
	# start gate
	var gate := StartGate.new()
	gate.setup(self)
	add_child(gate)
	# item egg rows
	for f in data.get("items", [0.2, 0.5, 0.8]):
		var s: float = float(f) * length
		var k := index_at_dist(s)
		var rows := 4 if width[k] > 13.0 else 3
		for i in rows:
			var lat := (i - (rows - 1) * 0.5) * (width[k] - 3.0) / rows
			var egg := ItemEgg.new()
			egg.transform = frame_at(s, lat, 1.0)
			add_child(egg)
			item_spots.append(egg.position)
	if not data.get("arena", false):
		var cf: Array = data.get("coins", [])
		if cf.is_empty():
			for f in data.get("items", [0.2, 0.5, 0.8]):
				cf.append(fposmod(float(f) + 0.09, 1.0))
		var side := 1.0
		for f in cf:
			var s0: float = float(f) * length
			side = -side
			for i in 5:
				var c := CoinPickup.new()
				var kk := index_at_dist(s0 + i * 3.0)
				c.transform = frame_at(s0 + i * 3.0, side * width[kk] * 0.22, 0.9)
				add_child(c)
	for f in data.get("boosts", []):
		var bp := BoostPad.new()
		var lat := 0.0
		var ff := 0.0
		if f is Array:
			ff = f[0]
			lat = f[1]
		else:
			ff = f
		bp.transform = frame_at(ff * length, lat, 0.03)
		add_child(bp)
	for f in data.get("ramps", []):
		var rp := Ramp.new()
		var ff := 0.0
		var lat := 0.0
		var wr := 0.0
		if not f is Array:
			ff = f
		else:
			ff = f[0]
			lat = f[1]
			wr = f[2] if f.size() > 2 else 0.0
		var k := index_at_dist(ff * length)
		rp.width = wr if wr > 0.0 else width[k] - 2.0
		rp.transform = frame_at(ff * length, lat, 0.0)
		add_child(rp)

func _build_spawn() -> void:
	spawn.clear()
	if data.get("arena", false):
		for i in 8:
			var sd := length * i / 8.0
			spawn.append(frame_at(sd, (1.0 if i % 2 == 0 else -1.0) * width[0] * 0.2, 0.4))
		return
	var hw := width[0] * 0.5
	for i in 8:
		var row := i / 2
		var col := i % 2
		var s := length - 6.0 - row * 5.0
		var lat := (-1.0 if col == 0 else 1.0) * hw * 0.4 + (0.6 if col == 1 else 0.0)
		spawn.append(frame_at(s, lat, 0.4))
