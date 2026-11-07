class_name Results
extends Control
## End of race table: places, pilots, times, points; then continue.

var race: Race
var rows := []
var _t := 0.0
var _list: VBoxContainer

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var dim := ColorRect.new()
	dim.color = Color(0.12, 0.08, 0.18, 0.45)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var panel := UI.panel()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.custom_minimum_size = Vector2(820, 0)
	add_child(panel)
	_list = VBoxContainer.new()
	_list.add_theme_constant_override("separation", 6)
	panel.add_child(_list)
	var title := UI.title(tr("Resultados") if race.mode != "gp" else tr("Resultados · carrera %d de 4") % (Session.cup_race + 1))
	_list.add_child(title)
	for r in rows:
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 18)
		var pl := UI.label(Lang.ordinal(r.place), 34)
		pl.custom_minimum_size.x = 80
		h.add_child(pl)
		var nm := UI.label(Roster.display_name(r.driver) + ("  (%s)" % tr("J%d") % (r.player + 1) if r.player >= 0 else ""), 30)
		nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if r.player >= 0:
			nm.add_theme_color_override("font_color", Color("#e2577a"))
		h.add_child(nm)
		var tm := UI.label(_fmt(r.time) if r.time > 0 else "--:--.--", 28)
		h.add_child(tm)
		if race.mode == "gp":
			var pts := UI.label("+%d" % r.points, 28)
			pts.custom_minimum_size.x = 70
			h.add_child(pts)
		_list.add_child(h)
	var hint := UI.label(tr("Apretá A para seguir"), 26)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_list.add_child(hint)
	panel.reset_size()
	panel.position = (get_viewport_rect().size - panel.size) * 0.5

func _fmt(t: float) -> String:
	return "%d:%02d.%02d" % [int(t) / 60, int(t) % 60, int((t - floorf(t)) * 100.0)]

func _process(dt: float) -> void:
	_t += dt
	if _t > 1.0 and (Input.is_action_just_pressed("ui_accept")):
		Flow.after_race()
