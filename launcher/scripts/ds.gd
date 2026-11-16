class_name DS
extends RefCounted
## Darksham look: colours, sizes and fonts in one place.

const BG := Color("0a0b0f")
const ACCENT := Color("8ab8ff")
const TEXT := Color("e8ecf4")
const MUTED := Color("8c93a3")
const CARD_W := 360.0
const CARD_H := 520.0

static var _fonts: Dictionary = {}


## Sora and Noto Kufi Arabic when the system has them (the OS image installs Noto Kufi);
## otherwise the next one in the list, so Arabic always has a font.
static func font(weight: int = 400) -> Font:
	if _fonts.has(weight):
		return _fonts[weight]
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Sora", "Noto Kufi Arabic", "Segoe UI", "Noto Sans Arabic", "sans-serif"])
	f.font_weight = weight
	f.antialiasing = TextServer.FONT_ANTIALIASING_GRAY
	_fonts[weight] = f
	return f


static func style_label(l: Label, size: int, color: Color, weight: int = 400) -> void:
	l.add_theme_font_override("font", font(weight))
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
