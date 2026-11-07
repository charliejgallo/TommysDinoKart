extends Node
## Title screen and every menu page, over a little 3D showroom where karts
## drive in circles. Pages are built in code (UI helpers in ui.gd):
##   main -> mode -> join -> pilot -> cup | track | arena -> race
##   garage, settings, parents (behind the grown-up gate), after_race,
##   podium (end of a cup), rest (the grown-ups' session limit ran out).

const CUP_NAMES := {"fern": "cup.fern", "amber": "cup.amber", "volcano": "cup.volcano"}
const ARENAS := ["arena_patio", "arena_isla", "arena_crater", "arena_templo"]

var ui: Control
var layer: CanvasLayer
var show3d: Node3D
var cam: Camera3D
var _karts := []
var _t := 0.0
var page := ""
var _back := Callable()
var _picker := 0          # which player is choosing a pilot
var _cursor := []         # per player grid index
var _chosen := []         # per player driver id
var _join := []           # join slots
var _grid_cells := []
var _pilot_preview: TextureRect
var _pilot_name: Label
var _pilot_info: Label
var _pilot_hint: Label
var _logo: Control

func _ready() -> void:
	_build_showroom()
	layer = CanvasLayer.new()
	add_child(layer)
	ui = Control.new()
	ui.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(ui)
	Music.play_track("title")
	var start: String = Flow.get_meta("menu_page", "") if Flow.has_meta("menu_page") else ""
	if Flow.has_meta("menu_page"):
		Flow.remove_meta("menu_page")
	if Dev.arg("menu") != "":
		start = Dev.arg("menu")
	match start:
		"after_race":
			_page_after_race()
		"podium":
			_page_podium()
		"rest":
			_page_rest()
		"":
			_page_main()
		_:
			call("_page_" + start)

# ------------------------------------------------------------ showroom
func _build_showroom() -> void:
	show3d = Node3D.new()
	add_child(show3d)
	var env := Environment.new()
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sky_top_color = Color("#5fa8ec")
	sm.sky_horizon_color = Color("#d8efff")
	sm.ground_horizon_color = Color("#d8efff")
	sm.ground_bottom_color = Color("#7fb069")
	sky.sky_material = sm
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.9
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssao_enabled = true
	env.glow_enabled = true
	env.fog_enabled = true
	env.fog_light_color = Color("#d9efff")
	env.fog_density = 0.0016
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.12
	var we := WorldEnvironment.new()
	we.environment = env
	show3d.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 60.0
	show3d.add_child(sun)
	var g := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 90.0
	cm.bottom_radius = 90.0
	cm.height = 0.2
	g.mesh = cm
	g.position.y = -0.1
	g.material_override = Themes.toon(Color("#78c25a"))
	show3d.add_child(g)
	var road := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = 7.5
	tm.outer_radius = 11.5
	tm.rings = 64
	road.mesh = tm
	road.scale = Vector3(1, 0.02, 1)
	road.material_override = Themes.toon(Color("#7c746e"))
	show3d.add_child(road)
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	for i in 14:
		var a := TAU * i / 14.0 + rng.randf() * 0.2
		var d := rng.randf_range(15.0, 24.0)
		var m: String = ["prop_tree_round", "prop_tree_tall", "prop_bush", "prop_tree_fruit", "prop_flowers"][i % 5]
		var p: Node3D = (load("res://assets/props/%s.glb" % m) as PackedScene).instantiate()
		Look.apply(p)
		p.position = Vector3(cos(a) * d, 0, sin(a) * d)
		p.scale = Vector3.ONE * rng.randf_range(1.4, 2.2)
		show3d.add_child(p)
	var ids: Array = ["tommy", "trike", "trex", "raptor", "stego", "parasaur"]
	for i in ids.size():
		var k := Kart.new()
		k.setup(null, ids[i], Garage.kart_for(ids[i]))
		show3d.add_child(k)
		if k.engine:
			k.engine.queue_free()
			k.engine = null
		_karts.append({"k": k, "a": TAU * i / ids.size(), "r": 9.5 + (i % 2) * 1.0})
	cam = Camera3D.new()
	cam.fov = 50
	show3d.add_child(cam)
	cam.current = true

func _process(dt: float) -> void:
	_t += dt
	for e in _karts:
		e.a += dt * 0.32
		var k: Kart = e.k
		var p := Vector3(cos(e.a) * e.r, 0.0, sin(e.a) * e.r)
		k.position = p
		var tang := Vector3(-sin(e.a), 0, cos(e.a))
		k.yaw = atan2(-tang.x, -tang.z)
		k.rotation.y = k.yaw
		k.speed = 9.0
		k.inp.steer = -0.25
		k._visuals(dt)
	var ca := _t * 0.06
	cam.position = Vector3(cos(ca) * 19.0, 5.5, sin(ca) * 19.0)
	cam.look_at(Vector3(0, 0.6, 0), Vector3.UP)

# ------------------------------------------------------------ page helpers
func _clear() -> void:
	for c in ui.get_children():
		c.queue_free()
	_grid_cells.clear()
	_back = Callable()

func _logo_label(small := false) -> void:
	var box := VBoxContainer.new()
	box.set_anchors_preset(Control.PRESET_TOP_LEFT)
	box.position = Vector2(60, 36)
	ui.add_child(box)
	var l := UI.outlined("Tommy's", 54 if not small else 34, Color("#ffd35a"))
	box.add_child(l)
	var l2 := UI.outlined("Dino Kart", 104 if not small else 60, Color("#fff7e6"))
	l2.add_theme_color_override("font_outline_color", Color("#e2577a"))
	box.add_child(l2)
	_logo = box

func _panel(title: String, width := 640) -> VBoxContainer:
	var p := UI.panel()
	p.custom_minimum_size = Vector2(width, 0)
	ui.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 14)
	p.add_child(v)
	if title != "":
		v.add_child(UI.title(title))
	p.set_anchors_preset(Control.PRESET_CENTER)
	(func():
		p.reset_size()
		p.position = (ui.size - p.size) * Vector2(0.5, 0.55)).call_deferred()
	return v

func _place_right(v: Control) -> void:
	var p := v.get_parent() as Control
	(func():
		p.reset_size()
		p.position = Vector2(ui.size.x - p.size.x - 80, (ui.size.y - p.size.y) * 0.6)).call_deferred()

func _btn(v: Container, text: String, cb: Callable, size := 34) -> Button:
	var b := UI.button(text, size)
	b.pressed.connect(cb)
	v.add_child(b)
	return b

func _focus_first(v: Node) -> void:
	for c in v.find_children("*", "Button", true, false):
		if not (c as Button).disabled:
			(c as Button).grab_focus.call_deferred()
			return

func _unhandled_input(e: InputEvent) -> void:
	if page == "pilot" or page == "join":
		return
	if e.is_action_pressed("ui_cancel") and _back.is_valid():
		Sfx.ui("back")
		_back.call()
		get_viewport().set_input_as_handled()

# ------------------------------------------------------------ main
func _page_main() -> void:
	_clear()
	page = "main"
	_logo_label()
	var v := _panel("", 470)
	_btn(v, tr("¡A correr!"), _page_mode, 44)
	_btn(v, tr("Garaje"), _page_garage)
	_btn(v, tr("Ajustes"), _page_settings)
	_btn(v, tr("Para grandes"), func(): _gate(_page_parents))
	_btn(v, tr("Salir"), func(): get_tree().quit())
	var coins := UI.outlined("● %d" % Garage.coins, 40, Color("#ffd35a"))
	coins.position = Vector2(64, 260)
	ui.add_child(coins)
	_place_right(v)
	_focus_first(v)

func _page_mode() -> void:
	_clear()
	page = "mode"
	_logo_label(true)
	var v := _panel(tr("¿Qué jugamos?"), 560)
	_btn(v, tr("Gran Premio"), func(): _start_mode("gp"))
	_btn(v, tr("Carrera libre"), func(): _start_mode("free"))
	_btn(v, tr("Contrarreloj"), func(): _start_mode("time"))
	if Settings.battle_on:
		_btn(v, tr("Batalla de globos"), func(): _start_mode("battle"))
	_btn(v, tr("Volver"), _page_main, 28)
	_back = _page_main
	_place_right(v)
	_focus_first(v)

func _start_mode(m: String) -> void:
	Session.mode = m
	# who pressed A becomes player 1
	_join = [{"kb": "both" if Controls.last_joy < 0 else "", "joy": Controls.last_joy if Controls.last_joy >= 0 else -2}]
	if m == "time":
		_finish_join()
	else:
		_page_join()

# ------------------------------------------------------------ join
var _join_box: HBoxContainer
var _join_wait := 0.0

func _page_join() -> void:
	_clear()
	page = "join"
	_join_wait = 0.4
	var v := _panel(tr("¿Quiénes juegan?"), 1200)
	var hint := UI.label(tr("Cada jugador aprieta A en su joystick para sumarse (o E / Enter en el teclado).\nJugador 1: A para empezar · B para volver"), 26)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(hint)
	_join_box = HBoxContainer.new()
	_join_box.add_theme_constant_override("separation", 20)
	_join_box.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(_join_box)
	_refresh_join()

func _refresh_join() -> void:
	for c in _join_box.get_children():
		c.queue_free()
	var cols := [Color("#e2577a"), Color("#3f8fe8"), Color("#2fae6a"), Color("#f4a640")]
	for i in 4:
		var p := PanelContainer.new()
		var sb := UI.panel_style(cols[i].lightened(0.75) if i < _join.size() else Color("#efe6d6"), 22)
		sb.border_color = cols[i] if i < _join.size() else Color("#c8b8a0")
		p.add_theme_stylebox_override("panel", sb)
		p.custom_minimum_size = Vector2(250, 190)
		var vb := VBoxContainer.new()
		vb.alignment = BoxContainer.ALIGNMENT_CENTER
		p.add_child(vb)
		var t := UI.label(tr("Jugador %d") % (i + 1), 34, cols[i] if i < _join.size() else Color("#a89a8a"))
		t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		vb.add_child(t)
		var d := tr("Apretá A") if i >= _join.size() else _dev_name(_join[i])
		var dl := UI.label(d, 24)
		dl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		vb.add_child(dl)
		_join_box.add_child(p)

func _dev_name(s: Dictionary) -> String:
	if s.get("joy", -2) >= 0:
		return tr("Joystick %d") % (int(s.joy) + 1)
	return {"both": tr("Teclado"), "left": tr("Teclado (WASD)"), "right": tr("Teclado (flechas)")}.get(s.get("kb", ""), "")

func _join_poll() -> void:
	_join_wait -= get_physics_process_delta_time()
	if _join_wait > 0.0:
		return
	# new joypads
	var taken := []
	for s in _join:
		if s.get("joy", -2) >= 0:
			taken.append(s.joy)
	if _join.size() < 4:
		for d in Input.get_connected_joypads():
			if d in taken:
				continue
			if Input.is_joy_button_pressed(d, JOY_BUTTON_A):
				_join.append({"kb": "", "joy": d})
				Sfx.ui("ok")
				_join_wait = 0.3
				_refresh_join()
				return
		# a second keyboard player: split the keyboard in halves
		var kb_players := _join.filter(func(s): return s.get("kb", "") != "")
		if kb_players.size() == 1 and kb_players[0].kb == "both":
			var other := ""
			if Input.is_physical_key_pressed(KEY_E):
				other = "left"
			elif Input.is_physical_key_pressed(KEY_ENTER) and Controls.last_joy < 0 and _join_wait < -0.3:
				other = "right"
			if other != "":
				kb_players[0].kb = "right" if other == "left" else "left"
				_join.append({"kb": other, "joy": -2})
				Sfx.ui("ok")
				_join_wait = 0.3
				_refresh_join()
				return
		elif kb_players.is_empty() and (Input.is_physical_key_pressed(KEY_SPACE) or Input.is_physical_key_pressed(KEY_Z)):
			_join.append({"kb": "both", "joy": -2})
			_join_wait = 0.3
			_refresh_join()
			return
	# player 1 starts / goes back
	var p1: Dictionary = Controls.peek(_join[0])
	if p1.get("cancel", false):
		Sfx.ui("back")
		_page_mode()
	elif p1.get("ok", false) and _join_wait < -0.25:
		_finish_join()

func _finish_join() -> void:
	var slots := _join.duplicate(true)
	if slots.size() == 1:
		slots = [{"kb": "both", "joy": -1}]
	Controls.set_players(slots)
	_chosen = []
	_cursor = []
	for i in slots.size():
		_chosen.append("")
		_cursor.append(i)
	_picker = 0
	_page_pilot()

# ------------------------------------------------------------ pilot select
func _page_pilot() -> void:
	_clear()
	page = "pilot"
	_join_wait = 0.35
	var root := HBoxContainer.new()
	root.add_theme_constant_override("separation", 30)
	var p := UI.panel()
	ui.add_child(p)
	p.add_child(root)
	var left := VBoxContainer.new()
	root.add_child(left)
	var title := UI.title(tr("Jugador %d: elegí tu piloto") % (_picker + 1), 40)
	left.add_child(title)
	var grid := GridContainer.new()
	grid.columns = 7
	grid.add_theme_constant_override("h_separation", 8)
	grid.add_theme_constant_override("v_separation", 8)
	left.add_child(grid)
	for id in Roster.ids():
		var cell := PanelContainer.new()
		cell.custom_minimum_size = Vector2(128, 128)
		var tr_ := TextureRect.new()
		tr_.texture = load("res://assets/ui/portraits/%s.png" % id)
		tr_.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr_.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		cell.add_child(tr_)
		grid.add_child(cell)
		_grid_cells.append({"cell": cell, "id": id})
	_pilot_hint = UI.label(tr("◀ ▶ ▲ ▼ elegir · A confirmar · B volver"), 24)
	left.add_child(_pilot_hint)
	var right := VBoxContainer.new()
	right.custom_minimum_size = Vector2(380, 0)
	root.add_child(right)
	_pilot_preview = TextureRect.new()
	_pilot_preview.custom_minimum_size = Vector2(380, 380)
	_pilot_preview.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_pilot_preview.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	right.add_child(_pilot_preview)
	_pilot_name = UI.title("", 52)
	right.add_child(_pilot_name)
	_pilot_info = UI.label("", 28)
	_pilot_info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	right.add_child(_pilot_info)
	(func():
		p.reset_size()
		p.position = (ui.size - p.size) * 0.5).call_deferred()
	_refresh_pilot()

const PCOLS := [Color("#e2577a"), Color("#3f8fe8"), Color("#2fae6a"), Color("#f4a640")]

func _refresh_pilot() -> void:
	for i in _grid_cells.size():
		var c: PanelContainer = _grid_cells[i].cell
		var id: String = _grid_cells[i].id
		var taken := _chosen.find(id)
		var sb := UI.panel_style(Color("#fffaf0"), 18)
		sb.content_margin_left = 4
		sb.content_margin_right = 4
		sb.content_margin_top = 4
		sb.content_margin_bottom = 4
		sb.shadow_size = 0
		sb.set_border_width_all(3)
		if i == _cursor[_picker]:
			sb.border_color = PCOLS[_picker]
			sb.set_border_width_all(8)
			sb.bg_color = PCOLS[_picker].lightened(0.8)
		elif taken >= 0:
			sb.border_color = PCOLS[taken]
			sb.bg_color = Color("#e6dccb")
		c.add_theme_stylebox_override("panel", sb)
		c.modulate = Color(1, 1, 1, 0.55) if taken >= 0 and taken != _picker else Color.WHITE
	var id2: String = _grid_cells[_cursor[_picker]].id
	_pilot_preview.texture = load("res://assets/ui/portraits/%s.png" % id2)
	_pilot_name.text = Roster.display_name(id2)
	var w: int = Roster.driver(id2).weight
	_pilot_info.text = [tr("Liviano: arranca rapidísimo"), tr("Mediano: equilibrado"), tr("Pesado: empuja a los demás")][w]

func _pilot_poll() -> void:
	_join_wait -= get_physics_process_delta_time()
	if _join_wait > 0.0:
		return
	var p := _picker
	var n := _grid_cells.size()
	var moved := false
	var c: int = _cursor[p]
	if Controls.just(p, "left"):
		c = (c - 1 + n) % n; moved = true
	elif Controls.just(p, "right"):
		c = (c + 1) % n; moved = true
	elif Controls.just(p, "up"):
		c = (c - 7 + n) % n; moved = true
	elif Controls.just(p, "down"):
		c = (c + 7) % n; moved = true
	if moved:
		_cursor[p] = c
		Sfx.ui("tick")
		_refresh_pilot()
		return
	if Controls.just(p, "ok"):
		var id: String = _grid_cells[c].id
		if _chosen.find(id) >= 0 and _chosen.find(id) != p:
			Sfx.ui("back")
			return
		_chosen[p] = id
		Sfx.ui("ok")
		if p + 1 < _chosen.size():
			_picker += 1
			if _cursor[_picker] == c:
				_cursor[_picker] = (c + 1) % n
			_join_wait = 0.25
			_page_pilot()
		else:
			_after_pilots()
	elif Controls.just(p, "cancel"):
		Sfx.ui("back")
		if p > 0:
			_chosen[p] = ""
			_picker -= 1
			_chosen[_picker] = ""
			_page_pilot()
		elif Session.mode == "time":
			Controls.solo()
			_page_mode()
		else:
			Controls.solo()
			_page_join()

func _after_pilots() -> void:
	Session.players = []
	for id in _chosen:
		Session.players.append({"driver": id, "kart": Garage.kart_for(id)})
	Controls.set_players(Controls.slots)
	match Session.mode:
		"gp":
			_page_cup()
		"battle":
			_page_arena()
		_:
			_page_track()

func _physics_process(_dt: float) -> void:
	if page == "join":
		_join_poll()
	elif page == "pilot":
		_pilot_poll()

func _page_devpilot() -> void:
	Session.mode = "free"
	_join = [{"kb": "both", "joy": -1}, {"kb": "", "joy": 0}]
	_finish_join()
	_chosen[0] = "trike"

# ------------------------------------------------------------ cups / tracks
func _page_cup() -> void:
	_clear()
	page = "cup"
	Controls.set_players(Controls.slots)
	var v := _panel(tr("Elegí una copa"), 1300)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 22)
	v.add_child(h)
	for c in Cups.CUPS:
		var col := VBoxContainer.new()
		h.add_child(col)
		var b := UI.button(tr(CUP_NAMES[c.id]), 36)
		b.custom_minimum_size = Vector2(400, 0)
		var cup_id: String = c.id
		b.pressed.connect(func():
			Session.start_cup(cup_id)
			Flow.to_race())
		col.add_child(b)
		var g := GridContainer.new()
		g.columns = 2
		col.add_child(g)
		for t in c.tracks:
			var tex := TextureRect.new()
			tex.texture = load("res://assets/ui/tracks/%s.jpg" % t)
			tex.custom_minimum_size = Vector2(196, 110)
			tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
			g.add_child(tex)
			g.add_child(Control.new()) if false else null
		var names := UI.label("\n".join(c.tracks.map(func(x): return "· " + tr("track." + x))), 22)
		col.add_child(names)
	_btn(v, tr("Volver"), _page_pilot_again, 28)
	_back = _page_pilot_again
	_focus_first(v)

func _page_pilot_again() -> void:
	_picker = 0
	for i in _chosen.size():
		_chosen[i] = ""
	_page_pilot()

func _page_track() -> void:
	_clear()
	page = "track"
	var v := _panel(tr("Elegí una pista"), 1500)
	var g := GridContainer.new()
	g.columns = 4
	g.add_theme_constant_override("h_separation", 14)
	g.add_theme_constant_override("v_separation", 14)
	v.add_child(g)
	for t in Cups.all_tracks():
		var b := UI.button(tr("track." + t), 24)
		b.icon = load("res://assets/ui/tracks/%s.jpg" % t)
		b.expand_icon = true
		b.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
		b.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
		b.custom_minimum_size = Vector2(330, 230)
		var tid: String = t
		b.pressed.connect(func():
			Session.track = tid
			Flow.to_race())
		g.add_child(b)
	var bk := _btn(v, tr("Volver"), _page_pilot_again, 28)
	bk.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_back = _page_pilot_again
	_focus_first(g)

func _page_arena() -> void:
	_clear()
	page = "arena"
	var v := _panel(tr("Elegí una arena"), 1200)
	var g := GridContainer.new()
	g.columns = 4
	g.add_theme_constant_override("h_separation", 14)
	v.add_child(g)
	for a in ARENAS:
		var b := UI.button(tr("track." + a), 24)
		var pth := "res://assets/ui/tracks/%s.jpg" % a
		if ResourceLoader.exists(pth):
			b.icon = load(pth)
			b.expand_icon = true
			b.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
		b.custom_minimum_size = Vector2(270, 210)
		var aid: String = a
		b.pressed.connect(func():
			Session.track = aid
			Flow.to_race())
		g.add_child(b)
	_btn(v, tr("Volver"), _page_pilot_again, 28)
	_back = _page_pilot_again
	_focus_first(g)

# ------------------------------------------------------------ after a race
func _page_after_race() -> void:
	_clear()
	page = "after_race"
	_logo_label(true)
	var v := _panel(tr("¿Y ahora?"), 520)
	_btn(v, tr("¡Revancha!"), func(): Flow.to_race(), 38)
	_btn(v, tr("Otra pista"), func():
		_chosen = Session.players.map(func(p): return p.driver)
		if Session.mode == "battle":
			_page_arena()
		else:
			_page_track())
	_btn(v, tr("Otro piloto"), func():
		_chosen = []
		_cursor = []
		for i in Controls.count():
			_chosen.append("")
			_cursor.append(i)
		_picker = 0
		_page_pilot())
	_btn(v, tr("Menú principal"), _page_main)
	_back = _page_main
	_place_right(v)
	_focus_first(v)

func _page_podium() -> void:
	_clear()
	page = "podium"
	Music.play_jingle("podium")
	Sfx.play("cheer")
	var rows := []
	for d in Session.standings:
		rows.append({"driver": d, "points": Session.standings[d]})
	rows.sort_custom(func(a, b): return a.points > b.points)
	var v := _panel(tr(CUP_NAMES.get(Session.cup, "cup.fern")) + " · " + tr("¡Podio!"), 1100)
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 20)
	v.add_child(h)
	var order := [1, 0, 2]
	var heights := [150, 220, 110]
	var medal := [Color("#dfe6f2"), Color("#ffd35a"), Color("#f0a46a")]
	for k in 3:
		var i: int = order[k]
		if i >= rows.size():
			continue
		var col := VBoxContainer.new()
		col.alignment = BoxContainer.ALIGNMENT_END
		h.add_child(col)
		var tex := TextureRect.new()
		tex.texture = load("res://assets/ui/portraits/%s.png" % rows[i].driver)
		tex.custom_minimum_size = Vector2(230, 230)
		tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		col.add_child(tex)
		var blk := PanelContainer.new()
		var sb := UI.panel_style(medal[k], 14)
		blk.add_theme_stylebox_override("panel", sb)
		blk.custom_minimum_size = Vector2(230, heights[k])
		var l := UI.label("%s\n%s · %d" % [Lang.ordinal(i + 1), Roster.display_name(rows[i].driver), rows[i].points], 28)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		blk.add_child(l)
		col.add_child(blk)
	var rest := []
	for i in range(3, rows.size()):
		rest.append("%s %s %d" % [Lang.ordinal(i + 1), Roster.display_name(rows[i].driver), rows[i].points])
	var rl := UI.label("   ".join(rest), 22)
	rl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	rl.autowrap_mode = TextServer.AUTOWRAP_WORD
	rl.custom_minimum_size.x = 1000
	v.add_child(rl)
	var hb := HBoxContainer.new()
	hb.alignment = BoxContainer.ALIGNMENT_CENTER
	hb.add_theme_constant_override("separation", 20)
	v.add_child(hb)
	_btn(hb, tr("Otra copa"), func(): _page_cup())
	_btn(hb, tr("Menú principal"), _page_main)
	_back = _page_main
	_focus_first(hb)

func _page_rest() -> void:
	_clear()
	page = "rest"
	Music.play_jingle("rest")
	var v := _panel(tr("¡Hora de descansar!"), 760)
	var t := UI.label(tr("Jugaste %d minutos. ¡Muy bien!\nLos dinos se van a dormir la siesta. Mañana seguimos.") % int(Settings.session_minutes_played()), 32)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.autowrap_mode = TextServer.AUTOWRAP_WORD
	t.custom_minimum_size.x = 680
	v.add_child(t)
	var tex := TextureRect.new()
	tex.texture = load("res://assets/ui/portraits/tommy.png")
	tex.custom_minimum_size = Vector2(260, 260)
	tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	v.add_child(tex)
	_btn(v, tr("Salir del juego"), func(): get_tree().quit())
	_btn(v, tr("Seguir jugando (para grandes)"), func(): _gate(func():
		Settings.new_session()
		_page_main()), 26)
	_focus_first(v)

# ------------------------------------------------------------ grown-up gate
var _gate_entry := ""
var _gate_answer := ""
var _gate_ok := Callable()
var _gate_lbl: Label

func _gate(ok: Callable) -> void:
	_clear()
	page = "gate"
	_gate_ok = ok
	_gate_entry = ""
	var v := _panel(tr("Sólo para grandes"), 620)
	var q: String
	if Settings.pin != "":
		q = tr("Escribí el PIN")
		_gate_answer = Settings.pin
	else:
		var a := randi_range(6, 9)
		var b := randi_range(6, 9)
		q = tr("¿Cuánto es %d × %d?") % [a, b]
		_gate_answer = str(a * b)
	var ql := UI.label(q, 34)
	ql.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(ql)
	_gate_lbl = UI.title("_", 54)
	v.add_child(_gate_lbl)
	var g := GridContainer.new()
	g.columns = 3
	g.add_theme_constant_override("h_separation", 10)
	g.add_theme_constant_override("v_separation", 10)
	v.add_child(g)
	for d in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"]:
		var b := UI.button(d, 36)
		b.custom_minimum_size = Vector2(150, 70)
		var dd: String = d
		b.pressed.connect(func(): _gate_key(dd))
		g.add_child(b)
	_btn(v, tr("Volver"), _page_main, 26)
	_back = _page_main
	_focus_first(g)

func _gate_key(d: String) -> void:
	if d == "⌫":
		_gate_entry = _gate_entry.substr(0, maxi(_gate_entry.length() - 1, 0))
	elif d == "OK":
		if _gate_entry == _gate_answer:
			_gate_ok.call()
			return
		_gate_entry = ""
		Sfx.ui("back")
	elif _gate_entry.length() < 4:
		_gate_entry += d
	_gate_lbl.text = _gate_entry if _gate_entry != "" else "_"

# ------------------------------------------------------------ settings
func _row(v: Container, label: String, ctl: Control) -> void:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 20)
	var l := UI.label(label, 28)
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(l)
	ctl.custom_minimum_size.x = 360
	h.add_child(ctl)
	v.add_child(h)

func _cycle(options: Array, get_i: Callable, set_i: Callable) -> Button:
	## a button showing "◀ value ▶": A / right goes forward, left goes back
	var b := UI.button("", 26)
	var upd := func(): b.text = "◀  %s  ▶" % options[clampi(get_i.call(), 0, options.size() - 1)]
	upd.call()
	b.pressed.connect(func():
		set_i.call((get_i.call() + 1) % options.size())
		upd.call()
		Settings.save())
	b.gui_input.connect(func(e: InputEvent):
		if e.is_action_pressed("ui_right"):
			set_i.call((get_i.call() + 1) % options.size())
			upd.call()
			Settings.save()
			b.accept_event()
		elif e.is_action_pressed("ui_left"):
			set_i.call((get_i.call() - 1 + options.size()) % options.size())
			upd.call()
			Settings.save()
			b.accept_event())
	return b

func _toggle(key: String) -> Button:
	return _cycle([tr("No"), tr("Sí")], func(): return 1 if Settings.get(key) else 0,
		func(i): Settings.set(key, i == 1); Settings.apply())

func _slider(key: String) -> HSlider:
	var s := HSlider.new()
	s.min_value = 0.0
	s.max_value = 1.0
	s.step = 0.05
	s.value = Settings.get(key)
	s.focus_mode = Control.FOCUS_ALL
	s.value_changed.connect(func(x): Settings.set(key, x); Settings.apply(); Settings.save())
	return s

func _scroll_panel(title: String, width := 1100) -> VBoxContainer:
	var v := _panel(title, width)
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(width - 80, 640)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	v.add_child(sc)
	var inner := VBoxContainer.new()
	inner.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner.add_theme_constant_override("separation", 10)
	sc.add_child(inner)
	return inner

func _page_settings() -> void:
	if Settings.protect_all and page != "gate":
		_gate(_page_settings_open)
		return
	_page_settings_open()

func _page_settings_open() -> void:
	_clear()
	page = "settings"
	var v := _scroll_panel(tr("Ajustes"))
	var langs: Array = Lang.languages.keys()
	langs.sort()
	_row(v, tr("Idioma"), _cycle(langs.map(func(l): return Lang.languages[l]),
		func(): return maxi(langs.find(TranslationServer.get_locale().substr(0, 2)), 0),
		func(i):
			Settings.language = langs[i]
			Settings.apply()
			_page_settings_open.call_deferred()))
	_row(v, tr("Música"), _slider("music_vol"))
	_row(v, tr("Sonidos"), _slider("sfx_vol"))
	_row(v, tr("Pantalla completa"), _toggle("fullscreen"))
	_row(v, tr("Calidad de imagen"), _cycle([tr("Liviana"), tr("Media"), tr("Alta")],
		func(): return Settings.quality, func(i): Settings.quality = i))
	_row(v, tr("2 jugadores: pantalla"), _cycle([tr("Arriba y abajo"), tr("Lado a lado")],
		func(): return 1 if Settings.split_vertical else 0, func(i): Settings.split_vertical = i == 1))
	_row(v, tr("Nombres sobre los karts"), _toggle("show_names"))
	_row(v, tr("Cámara más lejos"), _toggle("camera_far"))
	_row(v, tr("Vibración del joystick"), _toggle("rumble"))
	_btn(v.get_parent().get_parent(), tr("Volver"), _page_main, 28)
	_back = _page_main
	_focus_first(v)

func _page_parents() -> void:
	_clear()
	page = "parents"
	var v := _scroll_panel(tr("Para grandes"), 1300)
	var note := UI.label(tr("Estas opciones cambian cómo se juega. Los chicos no pueden entrar acá sin el PIN o la cuenta."), 24)
	note.autowrap_mode = TextServer.AUTOWRAP_WORD
	note.custom_minimum_size.x = 1180
	v.add_child(note)
	var mins := [0, 15, 20, 30, 45, 60, 90, 120]
	_row(v, tr("Tiempo máximo por sesión"), _cycle(mins.map(func(m): return tr("Sin límite") if m == 0 else tr("%d minutos") % m),
		func(): return maxi(mins.find(Settings.session_minutes), 0), func(i): Settings.session_minutes = mins[i]))
	_row(v, tr("Ítems"), _cycle([tr("Sólo carreras (sin ítems)"), tr("Sólo ítems amables"), tr("Todos (con ataques)")],
		func(): return Settings.items_mode, func(i): Settings.items_mode = i))
	_row(v, tr("Golpes suaves (sólo frenan)"), _toggle("gentle_hits"))
	_row(v, tr("Velocidad"), _cycle([tr("Tortuga"), tr("Normal"), tr("Rápida"), tr("Turbo")],
		func(): return Settings.speed, func(i): Settings.speed = i))
	_row(v, tr("Dificultad de los rivales"), _cycle([tr("Fácil"), tr("Normal"), tr("Difícil")],
		func(): return Settings.ai_level, func(i): Settings.ai_level = i))
	_row(v, tr("Rivales que esperan al jugador"), _toggle("catch_up"))
	_row(v, tr("Vueltas por carrera"), _cycle(["1", "2", "3", "4", "5"],
		func(): return Settings.laps - 1, func(i): Settings.laps = i + 1))
	_row(v, tr("Los karts se empujan"), _toggle("bumping_on"))
	_row(v, tr("Modo batalla"), _toggle("battle_on"))
	_row(v, tr("Ganar monedas"), _toggle("coins_on"))
	v.add_child(UI.title(tr("Ayudas por jugador"), 32))
	for p in 4:
		var pp := p
		_row(v, tr("J%d · acelerar solo") % (p + 1), _cycle([tr("No"), tr("Sí")],
			func(): return 1 if Settings.assists[pp].auto_accel else 0, func(i): Settings.assists[pp].auto_accel = i == 1))
		_row(v, tr("J%d · volante asistido") % (p + 1), _cycle([tr("No"), tr("Sí")],
			func(): return 1 if Settings.assists[pp].steer_help else 0, func(i): Settings.assists[pp].steer_help = i == 1))
	v.add_child(UI.title(tr("Protección"), 32))
	_row(v, tr("Pedir el PIN también para Ajustes"), _toggle("protect_all"))
	var pin_b := UI.button(tr("Cambiar PIN") if Settings.pin != "" else tr("Poner un PIN"), 26)
	pin_b.pressed.connect(_page_pin)
	_row(v, tr("PIN (si no hay, se pregunta una cuenta)"), pin_b)
	var hours := UI.label(tr("Tiempo jugado hoy: %d minutos") % int(Settings.played_today / 60.0), 26)
	v.add_child(hours)
	_btn(v.get_parent().get_parent(), tr("Volver"), _page_main, 28)
	_back = _page_main
	_focus_first(v)

func _page_pin() -> void:
	_clear()
	page = "pin"
	_gate_entry = ""
	var v := _panel(tr("Nuevo PIN (4 números, vacío = sin PIN)"), 620)
	_gate_lbl = UI.title("_", 54)
	v.add_child(_gate_lbl)
	var g := GridContainer.new()
	g.columns = 3
	v.add_child(g)
	for d in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"]:
		var b := UI.button(d, 36)
		b.custom_minimum_size = Vector2(150, 70)
		var dd: String = d
		b.pressed.connect(func():
			if dd == "OK":
				Settings.pin = _gate_entry
				Settings.save()
				_page_parents()
			elif dd == "⌫":
				_gate_entry = _gate_entry.substr(0, maxi(_gate_entry.length() - 1, 0))
			elif _gate_entry.length() < 4:
				_gate_entry += dd
			if is_instance_valid(_gate_lbl):
				_gate_lbl.text = _gate_entry if _gate_entry != "" else "_")
		g.add_child(b)
	_back = _page_parents
	_focus_first(g)

# ------------------------------------------------------------ garage
var _gar_id := "tommy"
var _gar_vp: SubViewport
var _gar_kart: Kart
var _gar_info: Label

func _page_garage() -> void:
	_clear()
	page = "garage"
	var v := _panel(tr("Garaje · elegí qué kart arreglar"), 1180)
	var g := GridContainer.new()
	g.columns = 7
	g.add_theme_constant_override("h_separation", 8)
	g.add_theme_constant_override("v_separation", 8)
	v.add_child(g)
	for id in Roster.ids():
		var b := Button.new()
		b.icon = load("res://assets/ui/portraits/%s.png" % id)
		b.expand_icon = true
		b.custom_minimum_size = Vector2(140, 140)
		var st := UI.button("").get_theme_stylebox("normal")
		for s in ["normal", "hover", "pressed", "focus"]:
			b.add_theme_stylebox_override(s, UI.button("").get_theme_stylebox(s))
		var iid: String = id
		b.pressed.connect(func():
			_gar_id = iid
			_page_garage_kart())
		g.add_child(b)
	var coins := UI.label(tr("Monedas: %d") % Garage.coins, 30, Color("#c8901a"))
	v.add_child(coins)
	_btn(v, tr("Volver"), _page_main, 28)
	_back = _page_main
	_focus_first(g)

func _page_garage_kart() -> void:
	_clear()
	page = "garage_kart"
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 30)
	var p := UI.panel()
	ui.add_child(p)
	p.add_child(h)
	# 3D preview
	var svc := SubViewportContainer.new()
	svc.custom_minimum_size = Vector2(620, 560)
	svc.stretch = true
	h.add_child(svc)
	_gar_vp = SubViewport.new()
	_gar_vp.own_world_3d = true
	_gar_vp.transparent_bg = true
	_gar_vp.msaa_3d = Viewport.MSAA_4X
	svc.add_child(_gar_vp)
	var root := Node3D.new()
	_gar_vp.add_child(root)
	var we := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_CLEAR_COLOR
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.85, 0.88, 1.0)
	e.ambient_light_energy = 0.7
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	we.environment = e
	root.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, 35, 0)
	root.add_child(sun)
	var c3 := Camera3D.new()
	c3.fov = 30
	c3.position = Vector3(0, 1.8, 4.6)
	root.add_child(c3)
	c3.look_at(Vector3(0, 0.5, 0), Vector3.UP)
	_gar_rebuild(root)
	# options
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	v.custom_minimum_size = Vector2(600, 0)
	h.add_child(v)
	v.add_child(UI.title(Roster.display_name(_gar_id), 48))
	_gar_info = UI.label("", 28, Color("#c8901a"))
	v.add_child(_gar_info)
	var cfg: Dictionary = Garage.karts.get(_gar_id, {})
	_gar_opt(v, tr("Chasis"), "chassis", Garage.CHASSIS, root)
	_gar_opt(v, tr("Ruedas"), "wheels", Garage.WHEELS, root)
	_gar_color(v, tr("Color"), "paint", root)
	_gar_color(v, tr("Detalles"), "paint2", root)
	_gar_color(v, tr("Asiento"), "seat", root)
	_btn(v, tr("Listo"), _page_garage, 30)
	_back = _page_garage
	_gar_update_info()
	(func():
		p.reset_size()
		p.position = (ui.size - p.size) * 0.5).call_deferred()
	_focus_first(v)

func _gar_rebuild(root: Node3D) -> void:
	if _gar_kart:
		_gar_kart.queue_free()
	_gar_kart = Kart.new()
	_gar_kart.setup(null, _gar_id, Garage.kart_for(_gar_id))
	root.add_child(_gar_kart)
	if _gar_kart.engine:
		_gar_kart.engine.queue_free()
		_gar_kart.engine = null
	var tw := _gar_kart.create_tween().set_loops()
	tw.tween_property(_gar_kart, "rotation:y", TAU, 8.0).from(0.0)

func _gar_update_info() -> void:
	_gar_info.text = tr("Monedas: %d") % Garage.coins

func _gar_opt(v: Container, label: String, key: String, items: Array, root: Node3D) -> void:
	var b := _cycle(items.map(func(it): return tr(it.name) + ("" if Garage.owns(key, it.id) else "  (● %d)" % it.price)),
		func(): return maxi(items.map(func(it): return it.id).find(Garage.kart_for(_gar_id)[key]), 0),
		func(i):
			var it: Dictionary = items[i]
			if Garage.try_set(_gar_id, key, it.id, it.price):
				_gar_rebuild(root)
			else:
				Sfx.ui("back")
			_gar_update_info())
	_row(v, label, b)

func _gar_color(v: Container, label: String, key: String, root: Node3D) -> void:
	var pal: Array = Garage.PALETTE
	var b := _cycle(pal.map(func(c): return ("■ " + tr(c.name)) + ("" if Garage.owns("color", c.hex) else "  (● %d)" % c.price)),
		func(): return maxi(pal.map(func(c): return c.hex).find((Garage.kart_for(_gar_id)[key] as Color).to_html(false)), 0),
		func(i):
			var c: Dictionary = pal[i]
			if Garage.try_set(_gar_id, key, c.hex, c.price):
				_gar_rebuild(root)
			else:
				Sfx.ui("back")
			_gar_update_info())
	_row(v, label, b)
