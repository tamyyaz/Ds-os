class_name LibraryProvider
extends RefCounted
## A source of games. The launcher shows whatever providers return; Steam, Lutris and
## Heroic are separate providers, so the screens never know where a game came from.


func provider_name() -> String:
	return "base"


func list_games() -> Array[GameEntry]:
	return []


## Starts the game. Returns "" when it started, otherwise a message to show the player.
func launch(_game: GameEntry) -> String:
	return "not supported"
