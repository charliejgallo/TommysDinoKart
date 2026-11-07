class_name Hud
extends Control
## One player's race HUD: place, lap, time, item slot, coins, minimap,
## countdown and banners. Sized for its pane (split screen shrinks it).

var race: Race
var kart: Kart
var split := 1
var _k := 1.0
var place_lbl: Label
var place_sub: Label
var lap_lbl: Label
var time_lbl: Label
var coin_lbl: Label
var item_box: Panel
var item_lbl: Label
var item_icon: ItemIcon
var count_lbl: Label
var banner: Label
var _banner_t := 0.0
var _item_spin := 0.0
var _last_item := ""
var _map_pts := PackedVector2Array()
var _map_xf := Transform2D()
var _place_pop := 0.0
var _last_place := 0

const CREAM := Color("#fff7e6")
const INK := Color("#4a3426")

func _ready() -> void:
	_k = 1.0 if split == 1 else (0.72 if split == 2 else 0.6)
	lap_lbl = _label(48, HORIZONTAL_ALIGNMENT_LEFT)
	time_lbl = _label(36, HORIZONTAL_ALIGNMENT_LEFT)
	coin_lbl = _label(38, HORIZONTAL_ALIGNMENT_LEFT)
	place_lbl = _label(130, HORIZONTAL_ALIGNMENT_RIGHT)
	place_sub = _label(36, HORIZONTAL_ALIGNMENT_RIGHT)
	count_lbl = _label(170, HORIZONTAL_ALIGNMENT_CENTER)
	banner = _label(64, HORIZONTAL_ALIGNMENT_CENTER)
	banner.visible = false
	item_box = Panel.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(1, 0.97, 0.9, 0.92)
	sb.border_color = Color("#6b4a3a")
	sb.set_border_width_all(int(5 * _k))
	sb.set_corner_radius_all(int(26 * _k))
	sb.shadow_color = Color(0, 0, 0, 0.25)
	sb.shadow_size = int(6 * _k)
	item_box.add_theme_stylebox_override("panel", sb)
	add_child(item_box)
	item_icon = ItemIcon.new()
	item_box.add_child(item_icon)
	item_lbl = _label(30, HORIZONTAL_ALIGNMENT_CENTER)
	item_lbl.reparent(item_box)
	_build_map()
	resized.connect(_layout)
	_layout()

func _label(size: int, align: int) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", int(size * _k))
	l.add_theme_color_override("font_color", CREAM)
	l.add_theme_color_override("font_outline_color", INK)
	l.add_theme_constant_override("outline_size", int(maxf(size * 0.3, 10) * _k))
	l.horizontal_alignment = align
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(l)
	return l

func _layout() -> void:
	var s := size
	var m := 24.0 * _k
	lap_lbl.position = Vector2(m, m * 0.6)
	lap_lbl.size = Vector2(500 * _k, 64 * _k)
	time_lbl.position = Vector2(m, m * 0.6 + 62 * _k)
	time_lbl.size = Vector2(500 * _k, 50 * _k)
	coin_lbl.position = Vector2(m, m * 0.6 + 112 * _k)
	coin_lbl.size = Vector2(300 * _k, 50 * _k)
	var ib := 150.0 * _k
	item_box.position = Vector2(s.x * 0.5 - ib * 0.5, m * 0.8)
	item_box.size = Vector2(ib, ib)
	item_icon.position = Vector2(ib * 0.1, ib * 0.06)
	item_icon.size = Vector2(ib * 0.8, ib * 0.8)
	item_lbl.position = Vector2(0, ib * 0.66)
	item_lbl.size = Vector2(ib, ib * 0.3)
	place_lbl.position = Vector2(s.x - 400 * _k - m, s.y - 210 * _k - m)
	place_lbl.size = Vector2(400 * _k, 170 * _k)
	place_sub.position = Vector2(s.x - 400 * _k - m, s.y - 56 * _k - m)
	place_sub.size = Vector2(400 * _k, 50 * _k)
	count_lbl.position = Vector2(0, s.y * 0.28)
	count_lbl.size = Vector2(s.x, 220 * _k)
	banner.position = Vector2(0, s.y * 0.3)
	banner.size = Vector2(s.x, 90 * _k)
	pivot_offset = s * 0.5
	_fit_map()

func _build_map() -> void:
	var t := race.track
	_map_pts.resize(0)
	for i in range(0, t.n, 2):
		_map_pts.append(Vector2(t.pos[i].x, t.pos[i].z))

func _fit_map() -> void:
	if _map_pts.is_empty():
		return
	var r := Rect2(_map_pts[0], Vector2.ZERO)
	for p in _map_pts:
		r = r.expand(p)
	var box := Vector2(300, 300) * _k * (1.0 if split == 1 else 0.85)
	var sc := minf(box.x / maxf(r.size.x, 1.0), box.y / maxf(r.size.y, 1.0))
	var origin := Vector2(24 * _k + 10, size.y - 24 * _k - box.y - 10)
	_map_xf = Transform2D(0.0, Vector2(sc, sc), 0.0, origin + (box - r.size * sc) * 0.5 - r.position * sc)

func _process(dt: float) -> void:
	if kart == null:
		return
	var L: int = race.laps
	var lap_now := clampi(kart.lap + 1, 1, L)
	if race.mode == "battle":
		var left := race.battle_left()
		lap_lbl.text = "%d:%02d" % [int(left) / 60, int(left) % 60]
		time_lbl.text = tr("Globos: %d") % kart.balloons
	else:
		lap_lbl.text = tr("Vuelta %d/%d") % [lap_now, L]
	if race.mode != "battle":
		time_lbl.text = _fmt(race.clock if not kart.done else kart.finish_time)
	if race.mode == "time" and race.best_time() > 0.0:
		coin_lbl.text = tr("Récord: %s") % _fmt(race.best_time())
	if race.mode != "time":
		coin_lbl.text = "● %d" % kart.coins if Settings.coins_on else ""
	coin_lbl.add_theme_color_override("font_color", Color("#ffd35a"))
	# place
	if kart.place != _last_place:
		_place_pop = 1.0
		_last_place = kart.place
	_place_pop = maxf(_place_pop - dt * 3.0, 0.0)
	place_lbl.text = Lang.ordinal(kart.place)
	place_lbl.scale = Vector2.ONE * (1.0 + 0.2 * _place_pop)
	place_lbl.pivot_offset = place_lbl.size * Vector2(1.0, 0.5)
	var pc: Color = [Color("#ffd35a"), Color("#dfe6f2"), Color("#f0a46a")][kart.place - 1] if kart.place <= 3 else CREAM
	place_lbl.add_theme_color_override("font_color", pc)
	place_sub.text = tr("de %d") % race.karts.size()
	place_lbl.visible = race.mode != "time"
	place_sub.visible = race.mode != "time"
	# item
	item_box.visible = Settings.items_on() or race.mode == "battle"
	if kart.item != _last_item:
		_item_spin = 0.6 if kart.item != "" else 0.0
		_last_item = kart.item
	_item_spin = maxf(_item_spin - dt, 0.0)
	if _item_spin > 0.0:
		var keys := Items.ICON_COLORS.keys()
		item_icon.item = keys[int(_item_spin * 20.0) % keys.size()]
	else:
		item_icon.item = kart.item
	item_icon.queue_redraw()
	item_lbl.text = ("×%d" % kart.item_count) if kart.item_count > 1 and _item_spin <= 0.0 else ""
	# countdown
	if race.state == "countdown":
		var c := ceili(race.countdown_left)
		count_lbl.text = str(c) if c <= 3 and c >= 1 else ""
		var f := race.countdown_left - floorf(race.countdown_left)
		count_lbl.scale = Vector2.ONE * (1.0 + f * 0.4)
		count_lbl.pivot_offset = count_lbl.size * 0.5
		count_lbl.add_theme_color_override("font_color", [Color("#ff6b6b"), Color("#ffb347"), Color("#ffd35a")][clampi(c - 1, 0, 2)])
	elif race.clock < 1.0:
		count_lbl.text = tr("¡YA!")
		count_lbl.add_theme_color_override("font_color", Color("#7fe07a"))
		count_lbl.scale = Vector2.ONE * (1.0 + race.clock * 0.3)
		count_lbl.modulate.a = 1.0 - race.clock
	else:
		count_lbl.text = ""
	if race.mode == "battle":
		if kart.out:
			_show(tr("¡Te quedaste sin globos!"), 999.0)
		elif race.state == "done":
			_show(tr("¡GANASTE!") if kart.place == 1 else tr("¡LLEGASTE!"), 999.0)
	elif race.mode == "time" and kart.done:
		_show(tr("¡Nuevo récord!") if race.new_record else _fmt(kart.finish_time), 999.0)
	elif kart.done:
		_show(tr("¡LLEGASTE!") if kart.place > 3 else tr("¡GENIAL!"), 999.0)
	if _banner_t > 0.0:
		_banner_t -= dt
		banner.visible = true
		banner.modulate.a = clampf(_banner_t * 2.0, 0.0, 1.0)
	else:
		banner.visible = false
	queue_redraw()

func on_lap(lap: int) -> void:
	if lap == race.laps - 1:
		_show(tr("¡Última vuelta!"), 2.5)
		Sfx.play("last_lap", 0.0)
	elif lap < race.laps:
		_show(tr("Vuelta %d") % (lap + 1), 1.6)

func _show(text: String, t: float) -> void:
	banner.text = text
	_banner_t = t

func _fmt(t: float) -> String:
	var m := int(t) / 60
	var s := int(t) % 60
	var c := int((t - floorf(t)) * 100.0)
	return "%d:%02d.%02d" % [m, s, c]

func _draw() -> void:
	if _map_pts.size() < 2 or race.mode == "time" and false:
		return
	var pts := _map_xf * _map_pts
	pts.append(pts[0])
	draw_polyline(pts, Color(0.29, 0.2, 0.15, 0.85), 16.0 * _k, true)
	draw_polyline(pts, Color(1, 0.97, 0.9, 0.95), 9.0 * _k, true)
	for k in race.karts:
		var p := _map_xf * Vector2(k.global_position.x, k.global_position.z)
		var col: Color = Roster.kart_colors(k.driver_id).paint
		var r := 7.0 * _k if k.player < 0 else 11.0 * _k
		draw_circle(p, r + 2.5 * _k, INK)
		draw_circle(p, r, col)
		if k == kart:
			draw_circle(p, r * 0.45, CREAM)


class ItemIcon extends Control:
	## Item pictures drawn with shapes (crisp at any size).
	var item := ""
	func _draw() -> void:
		var s := size
		var c := s * 0.5
		var r := minf(s.x, s.y) * 0.42
		match item:
			"":
				return
			"feather", "feather3":
				_feather(c, r, Color("#7fd6ff"))
				if item == "feather3":
					_feather(c + Vector2(-r * 0.35, r * 0.1), r * 0.7, Color("#5ec8ff"))
					_feather(c + Vector2(r * 0.35, r * 0.1), r * 0.7, Color("#a8e6ff"))
			"bubble":
				draw_circle(c, r, Color(0.75, 0.95, 1.0, 0.55))
				draw_arc(c, r, 0, TAU, 48, Color("#5ec8ff"), r * 0.12, true)
				draw_circle(c + Vector2(-r * 0.35, -r * 0.35), r * 0.18, Color(1, 1, 1, 0.9))
			"fern":
				_fern(c, r, Color("#ffd35a"), Color("#e8a33c"))
			"ptera":
				var w := PackedVector2Array([c + Vector2(-r, -r * 0.1), c + Vector2(-r * 0.2, r * 0.05),
					c + Vector2(0, -r * 0.35), c + Vector2(r * 0.2, r * 0.05), c + Vector2(r, -r * 0.1),
					c + Vector2(r * 0.2, r * 0.35), c + Vector2(0, r * 0.2), c + Vector2(-r * 0.2, r * 0.35)])
				draw_colored_polygon(w, Color("#ff8fa3"))
				draw_polyline(w + PackedVector2Array([w[0]]), Color("#4a3426"), r * 0.08, true)
				draw_circle(c + Vector2(0, -r * 0.3), r * 0.2, Color("#ff8fa3"))
			"egg", "egg3", "seeker":
				var col := Color("#a6e36b") if item != "seeker" else Color("#ff6b6b")
				var n := 3 if item == "egg3" else 1
				for i in n:
					var o := Vector2((i - (n - 1) * 0.5) * r * 0.6, (absf(i - 1.0) * 0.1) * r if n > 1 else 0.0)
					_egg(c + o, r * (0.62 if n > 1 else 0.85), col)
				if item == "seeker":
					draw_arc(c, r * 0.95, 0, TAU, 40, Color("#ff6b6b"), r * 0.08, true)
			"mud":
				draw_set_transform(c + Vector2(0, r * 0.25), 0, Vector2(1.0, 0.45))
				draw_circle(Vector2.ZERO, r, Color("#7a5236"))
				draw_set_transform(Vector2.ZERO)
				draw_circle(c + Vector2(-r * 0.3, r * 0.05), r * 0.22, Color("#94673f"))
				draw_circle(c + Vector2(r * 0.3, r * 0.2), r * 0.17, Color("#94673f"))
			"roar":
				for i in 3:
					draw_arc(c + Vector2(-r * 0.4, 0), r * (0.35 + i * 0.3), -0.8, 0.8, 16, Color("#ff9c4a"), r * 0.12, true)
				draw_circle(c + Vector2(-r * 0.55, 0), r * 0.25, Color("#ff6b6b"))
	func _egg(c: Vector2, r: float, col: Color) -> void:
		draw_set_transform(c, 0, Vector2(0.78, 1.0))
		draw_circle(Vector2.ZERO, r * 0.8, Color("#4a3426"))
		draw_circle(Vector2.ZERO, r * 0.72, col.lightened(0.55))
		draw_circle(Vector2(-r * 0.25, -r * 0.2), r * 0.16, col)
		draw_circle(Vector2(r * 0.3, r * 0.15), r * 0.2, col)
		draw_circle(Vector2(-r * 0.1, r * 0.4), r * 0.12, col)
		draw_set_transform(Vector2.ZERO)
	func _feather(c: Vector2, r: float, col: Color) -> void:
		var pts := PackedVector2Array()
		for i in 21:
			var t := float(i) / 20.0
			var y := lerpf(-r, r, t)
			var w := sin(t * PI) * r * 0.42
			pts.append(c + Vector2(w + y * 0.25, y).rotated(0.0))
		for i in range(20, -1, -1):
			var t := float(i) / 20.0
			var y := lerpf(-r, r, t)
			var w := sin(t * PI) * r * 0.42
			pts.append(c + Vector2(-w + y * 0.25, y))
		draw_colored_polygon(pts, col)
		draw_line(c + Vector2(-r * 0.25, -r), c + Vector2(r * 0.32, r * 1.1), Color("#4a3426"), r * 0.07, true)
	func _fern(c: Vector2, r: float, col: Color, col2: Color) -> void:
		draw_line(c + Vector2(0, r), c + Vector2(0, -r), col2, r * 0.1, true)
		for i in 6:
			var y := lerpf(r * 0.7, -r * 0.8, i / 5.0)
			var l := r * (0.75 - i * 0.1)
			for s: float in [-1.0, 1.0]:
				draw_set_transform(c + Vector2(s * l * 0.5, y), s * -0.5, Vector2(1.0, 0.4))
				draw_circle(Vector2.ZERO, l * 0.5, col)
				draw_set_transform(Vector2.ZERO)
