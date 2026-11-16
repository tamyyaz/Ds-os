class_name GameEntry
extends RefCounted
## One game in the library, whatever store it comes from.

var id := ""
var title := ""
var source := "darksham"      # "darksham", "steam", later "lutris", "heroic"
var hours := 0.0
var last_played := "never"     # "today", "yesterday", "never" (a key of L10n)
var accent := DS.ACCENT         # tints the background while the card is selected
var cover: Texture2D            # card art
var launch_id := ""             # what the provider needs to start it (Steam app id, ...)
