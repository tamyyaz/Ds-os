class_name DS
extends RefCounted
## Darksham look: colours, sizes, fonts and shared styles in one place. Sizes are for a 1920x1080 canvas.

const BG := Color("0a0b0f")
const ACCENT := Color("8ab8ff")
const TEXT := Color("f1f4fa")
const MUTED := Color("aab2c2")        # 7:1 on the background, still readable over art with the scrim
const ON_ACCENT := Color("0a1220")    # text on accent fills (about 9:1)
const CARD_W := 220.0                 # 2:3 like Steam portrait art
const CARD_H := 330.0
const MARGIN_X := 96.0                # about 5% safe area for TVs
const MARGIN_Y := 48.0

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


## A label that looks like a pill (chip, button, tab): `fill` background, optional outline.
static func pill(l: Label, fill: Color, text_color: Color, size: int, weight: int, pad_x: int, pad_y: int, outline: Color = Color(0, 0, 0, 0)) -> void:
	style_label(l, size, text_color, weight)
	var sb := StyleBoxFlat.new()
	sb.bg_color = fill
	sb.set_corner_radius_all(999)
	sb.content_margin_left = pad_x
	sb.content_margin_right = pad_x
	sb.content_margin_top = pad_y
	sb.content_margin_bottom = pad_y
	if outline.a > 0.0:
		sb.set_border_width_all(2)
		sb.border_color = outline
	l.add_theme_stylebox_override("normal", sb)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
