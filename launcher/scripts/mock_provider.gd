class_name MockProvider
extends LibraryProvider
## Demo library so the screens can be built and looked at before any real store is connected.
## The names are the Darksham test games; the cover art is a generated gradient, not real art.

const DATA := [
	{"id": "ashfall", "title": "Ashfall", "c1": "ff7a45", "c2": "2b0f1f", "hours": 12.5, "last": "today"},
	{"id": "apex_circuit", "title": "Apex Circuit", "c1": "4fd1ff", "c2": "0b1b3a", "hours": 31.0, "last": "yesterday"},
	{"id": "neon_drift", "title": "Neon Drift", "c1": "d36bff", "c2": "1a0b2e", "hours": 8.0, "last": "today"},
	{"id": "smoke_racing", "title": "Smoke Racing", "c1": "9aa7b8", "c2": "15181f", "hours": 3.5, "last": "never"},
	{"id": "phone_arena", "title": "Phone Arena", "c1": "5eead4", "c2": "062a2b", "hours": 20.0, "last": "yesterday"},
	{"id": "traffic_dodge", "title": "Traffic Dodge", "c1": "ffd166", "c2": "2a1d05", "hours": 1.5, "last": "never"},
]


func provider_name() -> String:
	return "mock"


func list_games() -> Array[GameEntry]:
	var out: Array[GameEntry] = []
	for d in DATA:
		var g := GameEntry.new()
		g.id = d.id
		g.title = d.title
		g.hours = d.hours
		g.last_played = d.last
		g.accent = Color(d.c1)
		g.cover = _cover(Color(d.c1), Color(d.c2))
		out.append(g)
	return out


func launch(game: GameEntry) -> String:
	return L10n.t("demo_launch") % game.title


func _cover(c1: Color, c2: Color) -> Texture2D:
	var grad := Gradient.new()
	grad.set_color(0, c1)
	grad.set_color(1, c2)
	var tex := GradientTexture2D.new()
	tex.gradient = grad
	tex.width = 360
	tex.height = 520
	tex.fill_from = Vector2(0.1, 0.0)
	tex.fill_to = Vector2(0.9, 1.0)
	return tex
