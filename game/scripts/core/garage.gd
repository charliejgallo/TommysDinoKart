extends Node
## Coins and the garage: chassis, wheels, colours, stickers and hats bought
## with coins (only looks; pilots and tracks are always free). Each pilot
## remembers its own kart. Saved in user://garage.json (dev: user://dev/).

const CHASSIS := [
	{"id": "tina", "name": "Clásico", "price": 0},
	{"id": "bone", "name": "Hueso", "price": 60},
	{"id": "egg", "name": "Cáscara", "price": 80},
]
const WHEELS := [
	{"id": "wheel_basic", "name": "Gomas", "price": 0},
	{"id": "wheel_stone", "name": "Piedra", "price": 40},
]
const PALETTE := [
	{"hex": "ef5b4c", "name": "Rojo", "price": 0}, {"hex": "ff9c4a", "name": "Naranja", "price": 0},
	{"hex": "ffd35a", "name": "Amarillo", "price": 0}, {"hex": "8bcf4a", "name": "Verde lima", "price": 0},
	{"hex": "2fae6a", "name": "Verde", "price": 0}, {"hex": "3fc0a0", "name": "Turquesa", "price": 0},
	{"hex": "4fb6d8", "name": "Celeste", "price": 0}, {"hex": "2f6fb8", "name": "Azul", "price": 0},
	{"hex": "9b7fe0", "name": "Lila", "price": 0}, {"hex": "ff8fa3", "name": "Rosa", "price": 0},
	{"hex": "fff1d6", "name": "Crema", "price": 0}, {"hex": "3a3346", "name": "Noche", "price": 0},
	{"hex": "e8c060", "name": "Dorado", "price": 30}, {"hex": "c9ccd6", "name": "Plateado", "price": 30},
	{"hex": "ff4fd0", "name": "Fucsia neón", "price": 25}, {"hex": "4affc0", "name": "Verde neón", "price": 25},
	{"hex": "7a3cff", "name": "Violeta eléctrico", "price": 25}, {"hex": "c27a4e", "name": "Ámbar", "price": 20},
]

var coins := 0
var owned := {"chassis:tina": true, "wheels:wheel_basic": true}
var karts := {}             # driver id -> {"chassis", "wheels", "paint", "paint2", "seat", "hat"}

func _ready() -> void:
	load_garage()

func path() -> String:
	return ("user://dev/" if Dev.is_dev() else "user://") + "garage.json"

func load_garage() -> void:
	if not FileAccess.file_exists(path()):
		return
	var d = JSON.parse_string(FileAccess.get_file_as_string(path()))
	if d is Dictionary:
		coins = int(d.get("coins", 0))
		owned = d.get("owned", owned)
		karts = d.get("karts", {})

func save() -> void:
	DirAccess.make_dir_recursive_absolute(path().get_base_dir())
	var f := FileAccess.open(path(), FileAccess.WRITE)
	f.store_string(JSON.stringify({"coins": coins, "owned": owned, "karts": karts}, "  "))

func add_coins(n: int) -> void:
	coins += n
	save()

func owns(kind: String, id: String) -> bool:
	if kind == "chassis" and id == "tina" or kind == "wheels" and id == "wheel_basic":
		return true
	if kind in ["paint", "paint2", "seat", "color"]:
		for c in PALETTE:
			if c.hex == id:
				return c.price == 0 or owned.has("color:" + id)
		return false
	return owned.has("%s:%s" % [kind, id])

## Put a part or colour on a pilot's kart, buying it first if needed.
## False when there are not enough coins.
func try_set(driver: String, key: String, id: String, price: int) -> bool:
	var kind := "color" if key in ["paint", "paint2", "seat"] else key
	if not owns(kind, id):
		if coins < price:
			return false
		coins -= price
		owned["%s:%s" % [kind, id]] = true
		Sfx.ui("coin")
	var k: Dictionary = karts.get(driver, {})
	k[key] = id
	karts[driver] = k
	save()
	return true

func kart_for(driver: String) -> Dictionary:
	var base := Roster.kart_colors(driver)
	var k: Dictionary = karts.get(driver, {})
	var out := {"chassis": k.get("chassis", "tina"), "wheels": k.get("wheels", "wheel_basic")}
	for c in ["paint", "paint2", "seat"]:
		out[c] = Color(k[c]) if k.has(c) else base[c]
	return out
