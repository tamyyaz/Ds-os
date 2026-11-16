class_name MockProvider
extends LibraryProvider
## Demo library so the screens can be built and looked at before any real store is connected.
## The names are the Darksham test games; the art is generated placeholder art, not real art.

const DATA := [
	{"id": "ashfall", "title": "Ashfall", "c1": "ff8a4c", "c2": "2b0f1f", "hours": 12.5, "last": "today"},
	{"id": "apex_circuit", "title": "Apex Circuit", "c1": "4fd1ff", "c2": "0b1b3a", "hours": 31.0, "last": "yesterday"},
	{"id": "neon_drift", "title": "Neon Drift", "c1": "d36bff", "c2": "1a0b2e", "hours": 8.0, "last": "today"},
	{"id": "smoke_racing", "title": "Smoke Racing", "c1": "aab6c8", "c2": "15181f", "hours": 3.5, "last": "never"},
	{"id": "phone_arena", "title": "Phone Arena", "c1": "5eead4", "c2": "062a2b", "hours": 20.0, "last": "yesterday"},
	{"id": "traffic_dodge", "title": "Traffic Dodge", "c1": "ffd166", "c2": "2a1d05", "hours": 1.5, "last": "never"},
]


func provider_name() -> String:
	return "mock"


func list_games() -> Array[GameEntry]:
	var out: Array[GameEntry] = []
	var n := 0
	for d in DATA:
		var g := GameEntry.new()
		g.id = d.id
		g.title = d.title
		g.hours = d.hours
		g.last_played = d.last
		g.accent = Color(d.c1)
		g.dark = Color(d.c2)
		g.art_seed = 1.7 + n * 2.3
		out.append(g)
		n += 1
	return out


func launch(game: GameEntry) -> String:
	return L10n.t("demo_launch") % game.title
