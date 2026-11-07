class_name PauseMenu
extends Control
## Pause: continue, restart, quit to the menu.

var race: Race

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var dim := ColorRect.new()
	dim.color = Color(0.12, 0.08, 0.18, 0.5)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var panel := UI.panel()
	add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	panel.add_child(v)
	v.add_child(UI.title(tr("Pausa")))
	var b1 := UI.button(tr("Seguir"))
	b1.pressed.connect(func(): race.toggle_pause())
	v.add_child(b1)
	var b2 := UI.button(tr("Empezar de nuevo"))
	b2.pressed.connect(func(): get_tree().paused = false; get_tree().reload_current_scene())
	v.add_child(b2)
	var b3 := UI.button(tr("Salir al menú"))
	b3.pressed.connect(func(): get_tree().paused = false; Flow.to_menu())
	v.add_child(b3)
	panel.reset_size()
	panel.position = (get_viewport_rect().size - panel.size) * 0.5
	b1.grab_focus()
