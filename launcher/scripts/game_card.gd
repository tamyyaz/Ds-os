class_name GameCard
extends Control
## One card (2:3): art, selection ring, glass edge and a floor reflection.
## The row moves and scales it; `intro` (0..1) is the entrance animation.

signal pressed(card: GameCard)

var entry: GameEntry
var index := 0
var intro := 1.0

var _art_mat: ShaderMaterial
var _refl_mat: ShaderMaterial
var _frame: Panel
var _ring_sb: StyleBoxFlat


func setup(e: GameEntry, i: int) -> void:
	entry = e
	index = i
	size = Vector2(DS.CARD_W, DS.CARD_H)
	custom_minimum_size = size
	pivot_offset = Vector2(DS.CARD_W * 0.5, DS.CARD_H)  # scale from the bottom centre so cards share a floor
	mouse_filter = Control.MOUSE_FILTER_STOP

	var art := ColorRect.new()
	art.size = size
	art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_art_mat = _make_material(e.cover, 18.0, size)
	art.material = _art_mat
	add_child(art)

	# Placeholder art has no title in it, so the card carries one; real covers already do.
	if e.cover == null:
		var t := Label.new()
		t.text = e.title
		t.position = Vector2(18, DS.CARD_H - 88)
		t.size = Vector2(DS.CARD_W - 36, 66)
		t.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
		t.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		t.mouse_filter = Control.MOUSE_FILTER_IGNORE
		DS.style_label(t, 26, Color.WHITE, 700)
		add_child(t)

	# glass edge: a faint 1px light outline that makes the card read as an object
	var edge := Panel.new()
	edge.size = size
	edge.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var esb := StyleBoxFlat.new()
	esb.draw_center = false
	esb.set_border_width_all(1)
	esb.border_color = Color(1, 1, 1, 0.16)
	esb.set_corner_radius_all(18)
	edge.add_theme_stylebox_override("panel", esb)
	add_child(edge)

	# selection ring + glow (thick and high contrast: it has to read from a sofa)
	_frame = Panel.new()
	_frame.size = size
	_frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ring_sb = StyleBoxFlat.new()
	_ring_sb.draw_center = false
	_ring_sb.set_border_width_all(4)
	_ring_sb.set_corner_radius_all(18)
	_ring_sb.border_color = Color.WHITE
	_ring_sb.shadow_color = Color(e.accent, 0.55)
	_ring_sb.shadow_size = 34
	_frame.add_theme_stylebox_override("panel", _ring_sb)
	add_child(_frame)

	var refl := ColorRect.new()
	refl.position = Vector2(0, DS.CARD_H + 6)
	refl.size = Vector2(DS.CARD_W, DS.CARD_H * 0.34)
	refl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_refl_mat = _make_material(e.cover, 0.0, refl.size)
	_refl_mat.set_shader_parameter("reflection", true)
	refl.material = _refl_mat
	add_child(refl)

	set_focus_amount(0.0)


func _make_material(tex: Texture2D, radius: float, rect_size: Vector2) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/art.gdshader")
	m.set_shader_parameter("c1", entry.accent)
	m.set_shader_parameter("c2", entry.dark)
	m.set_shader_parameter("seed", entry.art_seed)
	m.set_shader_parameter("aspect", DS.CARD_W / DS.CARD_H)
	m.set_shader_parameter("radius", radius)
	m.set_shader_parameter("rect_size", rect_size)
	m.set_shader_parameter("bottom_dark", 1.0)
	if tex != null:
		m.set_shader_parameter("has_tex", true)
		m.set_shader_parameter("tex", tex)
	return m


## 0 = a side card (dim, no ring), 1 = the selected card (bright, ringed).
func set_focus_amount(f: float) -> void:
	_frame.modulate.a = f
	var dim := (1.0 - f) * 0.42
	_art_mat.set_shader_parameter("dim", dim)
	_refl_mat.set_shader_parameter("dim", dim)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		pressed.emit(self)
