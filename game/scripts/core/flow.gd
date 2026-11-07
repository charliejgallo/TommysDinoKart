extends Node
## Moves between screens: title -> menus -> race -> results -> ...

const RACE := "res://scenes/race.tscn"
const MENU := "res://scenes/title.tscn"

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	if Dev.arg("race") != "":
		get_tree().change_scene_to_file.call_deferred(RACE)
	elif Dev.arg("scene") != "":
		var path := "res://scripts/dev/%s.gd" % Dev.arg("scene")
		if ResourceLoader.exists(path):
			var sc := Node3D.new()
			sc.set_script(load(path))
			get_tree().root.add_child.call_deferred(sc)

func to_race() -> void:
	get_tree().paused = false
	get_tree().change_scene_to_file(RACE)

func to_menu(page := "") -> void:
	get_tree().paused = false
	Music.stop()
	if page != "":
		set_meta("menu_page", page)
	get_tree().change_scene_to_file(MENU)

func after_race() -> void:
	if Settings.session_over():
		to_menu("rest")
		return
	if Session.mode == "gp":
		if Session.next_race():
			to_race()
		else:
			to_menu("podium")
		return
	to_menu("after_race")
