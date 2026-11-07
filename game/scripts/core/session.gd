extends Node
## What is being played right now: the mode, the cup and its standings, the
## players with their pilots and karts. Menus fill it, Race reads it.

var mode := "free"            # gp, free, time, battle
var track := "pradera"
var cup := ""                 # cup id in GP
var cup_race := 0             # index of the race in the cup
var players := [{"driver": "tommy", "kart": {}}]
var standings := {}           # driver -> points (GP)
var last_results := []

func _ready() -> void:
	if Dev.arg("race") != "":
		track = Dev.arg("race")
		mode = Dev.arg("mode", "free")
		var ds := Dev.arg("drivers", "tommy").split(",")
		var np := int(Dev.arg("players", "1"))
		players = []
		for i in np:
			players.append({"driver": ds[i] if i < ds.size() else Roster.ids()[i + 1], "kart": {}})
		var cs := []
		for i in np:
			cs.append({"kb": "both" if np == 1 else ["left", "right", "", ""][i], "joy": -1 if np == 1 else i})
		Controls.set_players(cs)

func race_cfg() -> Dictionary:
	return {"mode": mode, "track": track, "players": players, "laps": Settings.laps}

func race_finished(rows: Array, _race) -> void:
	last_results = rows
	if mode == "gp":
		for r in rows:
			standings[r.driver] = standings.get(r.driver, 0) + r.points
	var earned := 0
	for r in rows:
		if r.player >= 0:
			earned += r.coins + [10, 8, 6, 5, 4, 3, 2, 1][r.place - 1]
	if Settings.coins_on:
		Garage.add_coins(earned)

func start_cup(id: String) -> void:
	mode = "gp"
	cup = id
	cup_race = 0
	standings = {}
	track = Cups.tracks(id)[0]

func next_race() -> bool:
	if mode != "gp":
		return false
	cup_race += 1
	var t: Array = Cups.tracks(cup)
	if cup_race >= t.size():
		return false
	track = t[cup_race]
	return true
