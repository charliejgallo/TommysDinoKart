class_name UI
## The game's look for menus: cream rounded panels with a brown outline,
## Fredoka, big friendly buttons (focus = pink outline + a little grow).

const CREAM := Color("#fff7e6")
const INK := Color("#4a3426")
const LINE := Color("#6b4a3a")
const PINK := Color("#e2577a")

static func panel_style(bg := CREAM, r := 28) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = LINE
	sb.set_border_width_all(5)
	sb.set_corner_radius_all(r)
	sb.content_margin_left = 34
	sb.content_margin_right = 34
	sb.content_margin_top = 24
	sb.content_margin_bottom = 26
	sb.shadow_color = Color(0, 0, 0, 0.22)
	sb.shadow_size = 10
	sb.shadow_offset = Vector2(0, 5)
	return sb

static func panel() -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", panel_style())
	return p

static func label(text: String, size := 28, col := INK) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	return l

static func title(text: String, size := 44) -> Label:
	var l := label(text, size, PINK)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return l

static func outlined(text: String, size := 48, col := CREAM) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	l.add_theme_color_override("font_outline_color", INK)
	l.add_theme_constant_override("outline_size", maxi(int(size * 0.2), 6))
	return l

static func button(text: String, size := 32) -> Button:
	var b := Button.new()
	b.text = text
	b.add_theme_font_size_override("font_size", size)
	for st in ["normal", "hover", "pressed", "focus", "disabled"]:
		var sb := StyleBoxFlat.new()
		sb.bg_color = {"normal": Color("#ffffff"), "hover": Color("#fff0d0"), "pressed": Color("#ffe0a8"),
			"focus": Color("#ffe9f0"), "disabled": Color("#eee6da")}[st]
		sb.border_color = PINK if st == "focus" else LINE
		sb.set_border_width_all(6 if st == "focus" else 4)
		sb.set_corner_radius_all(22)
		sb.content_margin_left = 28
		sb.content_margin_right = 28
		sb.content_margin_top = 10
		sb.content_margin_bottom = 12
		if st == "focus":
			sb.draw_center = true
		b.add_theme_stylebox_override(st, sb)
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(c, INK)
	b.add_theme_color_override("font_disabled_color", Color("#a89a8a"))
	b.focus_entered.connect(func(): Sfx.ui("tick"))
	b.pressed.connect(func(): Sfx.ui("ok"))
	return b
