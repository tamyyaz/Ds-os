class_name GameEntry
extends RefCounted
## One game in the library, whatever store it comes from.

var id := ""
var title := ""
var source := "darksham"      # "darksham", "steam", later "lutris", "heroic"
var hours := 0.0
var last_played := "never"     # "today", "yesterday", "never" (a key of L10n)
var accent := DS.ACCENT         # light colour of the art; tints the background while selected
var dark := Color("0b1020")     # dark colour of the art
var art_seed := 1.0             # varies the generated placeholder art
var cover: Texture2D            # portrait card art (2:3); null = generated placeholder
var hero: Texture2D             # wide background art; null = generated placeholder
var launch_id := ""             # what the provider needs to start it (Steam app id, ...)
