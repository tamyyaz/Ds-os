class_name GameCard
extends Control
## One card: art, title, selection frame and a floor reflection. The carousel moves and scales it.

signal pressed(card: GameCard)

var entry: GameEntry
var index := 0

var _art: TextureRect
var _art_mat: ShaderMaterial
var _refl: ColorRect
var _refl_mat: ShaderMaterial
var _frame: Panel
var _title: Label


func setup(e: GameEntry, i: int) -> void:
	entry = e
	index = i
	size = Vector2(DS.CARD_W, DS.CARD_H)
	custom_minimum_size = size
	pivot_offset = Vector2(DS.CARD_W * 0.5, DS.CARD_H)  # scale from the bottom centre so cards share a floor
	mouse_filter = Control.MOUSE_FILTER_STOP

	_art = TextureRect.new()
	_art.texture = e.cover
	_art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_art.stretch_mode = TextureRect.STRETCH_SCALE
	_art.size = size
	_art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_art_mat = ShaderMaterial.new()
	_art_mat.shader = load("res://shaders/card.gdshader")
	_art.material = _art_mat
	add_child(_art)

	_title = Label.new()
	_title.text = e.title
	_title.position = Vector2(22, DS.CARD_H - 96)
	_title.size = Vector2(DS.CARD_W - 44, 72)
	_title.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	DS.style_label(_title, 30, Color.WHITE, 700)
	add_child(_title)

	_frame = Panel.new()
	_frame.size = size
	_frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sb := StyleBoxFlat.new()
	sb.draw_center = false
	sb.set_border_width_all(4)
	sb.set_corner_radius_all(18)
	sb.border_color = DS.ACCENT
	sb.shadow_color = Color(DS.ACCENT, 0.45)
	sb.shadow_size = 26
	_frame.add_theme_stylebox_override("panel", sb)
	add_child(_frame)

	_refl = ColorRect.new()
	_refl.position = Vector2(0, DS.CARD_H + 8)
	_refl.size = Vector2(DS.CARD_W, DS.CARD_H * 0.38)
	_refl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_refl_mat = ShaderMaterial.new()
	_refl_mat.shader = load("res://shaders/reflection.gdshader")
	_refl_mat.set_shader_parameter("cover", e.cover)
	_refl.material = _refl_mat
	add_child(_refl)

	set_focus_amount(0.0)


## 0 = a side card (dim, no frame), 1 = the selected card (bright, framed).
func set_focus_amount(f: float) -> void:
	_frame.modulate.a = f
	_art_mat.set_shader_parameter("dim", (1.0 - f) * 0.45)
	_refl_mat.set_shader_parameter("dim", (1.0 - f) * 0.45)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		pressed.emit(self)
