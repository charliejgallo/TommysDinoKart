class_name Items
## What comes out of the surprise eggs, and what each item does.
##
## Friendly items (allowed in "friendly items only" mode):
##   feather   Pluma turbo: one turbo
##   feather3  Tres plumas: three turbos
##   bubble    Burbuja: blocks the next hit (12 s)
##   fern      Helecho dorado: 6 s faster and untouchable, bumps others aside
##   ptera     Aventón de Ptera: a ptera flies you ahead for 3 s
## Attack items (only when the grown-ups allow them):
##   egg       Huevo rebotón: thrown ahead (or behind holding brake), bounces off
##             the road edges, spins out the kart it touches
##   egg3      Tres huevos: three rebotones in a row
##   seeker    Huevo buscador: chases the kart just ahead
##   mud       Charco de barro: dropped behind, slows / spins who drives in
##   roar      Rugido: a big roar spins out karts close by
## The roll depends on the place: leaders get defensive items, the back of
## the pack gets the catch-up ones.

const FRIENDLY := ["feather", "feather3", "bubble", "fern", "ptera"]
const ICON_COLORS := {"feather": "#7fd6ff", "feather3": "#7fd6ff", "bubble": "#bff3ff", "fern": "#ffd35a",
	"ptera": "#ff8fa3", "egg": "#a6e36b", "egg3": "#a6e36b", "seeker": "#ff6b6b", "mud": "#a0714f",
	"roar": "#ff9c4a"}
const ICON_GLYPH := {"feather": "🪶", "feather3": "🪶×3", "bubble": "🫧", "fern": "🌿", "ptera": "🦅",
	"egg": "🥚", "egg3": "🥚×3", "seeker": "🎯", "mud": "💩", "roar": "🗯"}

# weights per band: front (1st-2nd), middle, back
const TABLE := {
	"front": {"egg": 30, "mud": 30, "bubble": 25, "feather": 15},
	"middle": {"egg": 18, "egg3": 10, "seeker": 14, "mud": 14, "feather": 18, "bubble": 10, "roar": 8,
		"feather3": 8},
	"back": {"feather3": 26, "fern": 18, "ptera": 14, "seeker": 16, "roar": 10, "egg3": 8, "feather": 8},
}

static func roll(k: Kart) -> void:
	var n: int = k.race.karts.size()
	var r := float(k.place - 1) / maxf(n - 1, 1)
	var band := "front" if k.place <= 2 else ("back" if r > 0.65 else "middle")
	var t: Dictionary = TABLE[band].duplicate()
	if Settings.friendly_only():
		for key in t.keys():
			if not key in FRIENDLY:
				t.erase(key)
		if t.is_empty():
			t = {"feather": 40, "bubble": 40, "feather3": 20}
	if k.race.mode == "battle":
		t.erase("ptera")
		t.erase("feather3")
	var total := 0
	for key in t:
		total += t[key]
	var pick := randi() % maxi(total, 1)
	for key in t:
		pick -= t[key]
		if pick < 0:
			k.item = key
			break
	k.item_count = {"feather3": 3, "egg3": 3}.get(k.item, 1)
	k.item_changed.emit(k)
	Sfx.play_at("item_get", k.global_position, -6.0 if k.player >= 0 else -18.0)

static func use(k: Kart) -> void:
	var it := k.item
	match it:
		"feather", "feather3":
			k.boost(1.2, false)
		"bubble":
			k.shield_t = 12.0
			Sfx.play_at("bubble", k.global_position)
		"fern":
			k.star_t = 6.0
			k.boost(1.0, false)
			Sfx.play_at("fern", k.global_position)
		"ptera":
			k.start_ride(3.0)
		"egg", "egg3":
			var back := k.inp.brake > 0.5 or k.inp.back
			EggShot.throw(k, back, false)
		"seeker":
			EggShot.throw(k, false, true)
		"mud":
			MudPuddle.drop(k)
		"roar":
			_roar(k)
	k.item_count -= 1
	if k.item_count <= 0:
		k.item = ""
		k.item_count = 0
	k.item_changed.emit(k)

static func _roar(k: Kart) -> void:
	Sfx.play_at("roar", k.global_position)
	Fx.burst(k.get_parent(), k.global_position + Vector3.UP, Color("#ff9c4a"), 30)
	for o in k.race.karts:
		if o == k:
			continue
		if o.global_position.distance_to(k.global_position) < 14.0:
			o.hit("slow" if Settings.gentle_hits else "spin", k)

static func hit_kind() -> String:
	return "slow" if Settings.gentle_hits else "spin"
