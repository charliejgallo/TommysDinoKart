class_name Cups
## The Grand Prix cups: four races each. All open from the start.

const CUPS := [
	{"id": "fern", "tracks": ["pradera", "bosque", "laguna", "playa"]},
	{"id": "amber", "tracks": ["canon", "pantano", "nevado", "selva"]},
	{"id": "volcano", "tracks": ["cuevas", "volcan", "acantilado", "valle_rex"]},
]

static func tracks(id: String) -> Array:
	for c in CUPS:
		if c.id == id:
			return c.tracks
	return CUPS[0].tracks

static func all_tracks() -> Array:
	var a := []
	for c in CUPS:
		a += c.tracks
	return a
