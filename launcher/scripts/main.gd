extends Control
## Darksham Launcher: Games / Profile / Apps.
## Games: full-screen hero art of the selected game, its info and Play button on the start side
## (right in Arabic), and a row of 2:3 cards at the bottom that slides so the selection stays put.
## Keys: arrows or D-pad/stick move, Enter or A plays, Q/E or shoulder buttons switch tab,
## F2 or Y switches Arabic/English.

const TABS := ["games", "profile", "apps"]
const STEP := 248.0                      # card pitch: width 220 + gap 28
const FOCUS_SCALE := 1.18
const EXTRA := 39.6                      # extra width of the selected card (220 * 0.18)

var provider: LibraryProvider = MockProvider.new()
var games: Array[GameEntry] = []
var cards: Array[GameCard] = []
var idx := 0
var pos := 0.0            # smoothed position of the row (float index)
var tab := 0

var _static := false      # --static: no entrance animation (used for screenshots)
var _pad := false         # last input came from a gamepad (changes the key hints)

var _base_mat: ShaderMaterial
var _hero_back: ColorRect
var _hero_front: ColorRect
var _front_entry: GameEntry
var _scrim_mat: ShaderMaterial
var _tabs_box: HBoxContainer
var _tab_labels: Array[Label] = []
var _logo: TextureRect
var _clock: Label
var _avatar: Panel
var _carousel: Control
var _info: Control
var _info_base := Vector2.ZERO
var _title: Label
var _chips: HBoxContainer
var _chip_src: Label
var _chip_hours: Label
var _chip_last: Label
var _play: PanelContainer
var _play_label: Label
var _play_key: Label
var _hints: HBoxContainer
var _profile_box: VBoxContainer
var _profile_name: Label
var _stat_games_n: Label
var _stat_games_l: Label
var _stat_hours_n: Label
var _stat_hours_l: Label
var _apps_box: VBoxContainer
var _apps_title: Label
var _apps_sub: Label
var _toast: Label

var _nav_prev := 0
var _nav_timer := 0.0
var _clock_timer := 1.0
var _hero_tween: Tween
var _tint_tween: Tween
var _info_tween: Tween
var _toast_tween: Tween


func _ready() -> void:
	_add_action("tab_prev", [KEY_Q], [JOY_BUTTON_LEFT_SHOULDER])
	_add_action("tab_next", [KEY_E], [JOY_BUTTON_RIGHT_SHOULDER])
	_add_action("toggle_lang", [KEY_F2], [JOY_BUTTON_Y])

	_build_hero()
	_build_top_bar()
	_build_carousel()
	_build_info()
	_build_pages()
	_build_overlay()

	games = provider.list_games()
	for i in games.size():
		var c := GameCard.new()
		c.setup(games[i], i)
		c.pressed.connect(_on_card_pressed)
		_carousel.add_child(c)
		cards.append(c)

	# Dev/test options after "--": --lang=en  --select=2  --tab=1  --static  (used for screenshots)
	var start_idx := 0
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--lang="):
			L10n.lang = a.substr(7)
		elif a.begins_with("--select="):
			start_idx = clampi(int(a.substr(9)), 0, maxi(games.size() - 1, 0))
		elif a.begins_with("--tab="):
			tab = clampi(int(a.substr(6)), 0, TABS.size() - 1)
		elif a == "--static":
			_static = true

	resized.connect(_layout)
	_apply_language()
	_select(start_idx, true)
	if not _static:
		_play_entrance()


func _process(delta: float) -> void:
	_clock_timer += delta
	if _clock_timer >= 1.0:
		_clock_timer = 0.0
		var t := Time.get_time_dict_from_system()
		_clock.text = "%02d:%02d" % [t.hour, t.minute]

	# D-pad / stick / arrows: one step on press, then repeat while held.
	var nav := int(Input.is_action_pressed("ui_right")) - int(Input.is_action_pressed("ui_left"))
	if nav == 0:
		_nav_prev = 0
		_nav_timer = 0.0
	elif nav != _nav_prev:
		_nav_prev = nav
		_nav_timer = 0.0
		_move(nav)
	else:
		_nav_timer += delta
		if _nav_timer >= 0.4:
			_nav_timer -= 0.14
			_move(nav)

	_update_cards(delta)


func _input(event: InputEvent) -> void:
	var from_pad := event is InputEventJoypadButton or (event is InputEventJoypadMotion and absf(event.axis_value) > 0.5)
	var from_kb := event is InputEventKey or event is InputEventMouseButton
	if from_pad and not _pad:
		_pad = true
		_rebuild_hints()
	elif from_kb and _pad:
		_pad = false
		_rebuild_hints()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_accept") and not event.is_echo():
		_launch_selected()
	elif event.is_action_pressed("tab_next"):
		_set_tab(tab + 1)
	elif event.is_action_pressed("tab_prev"):
		_set_tab(tab - 1)
	elif event.is_action_pressed("toggle_lang"):
		L10n.toggle()
		_apply_language()


# ---------------------------------------------------------------- building

func _art_material() -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/art.gdshader")
	m.set_shader_parameter("aspect", 16.0 / 9.0)
	return m


func _build_hero() -> void:
	var base := ColorRect.new()
	base.set_anchors_preset(Control.PRESET_FULL_RECT)
	base.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_base_mat = ShaderMaterial.new()
	_base_mat.shader = load("res://shaders/bg.gdshader")
	base.material = _base_mat
	add_child(base)

	_hero_back = ColorRect.new()
	_hero_back.set_anchors_preset(Control.PRESET_FULL_RECT)
	_hero_back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hero_back.material = _art_material()
	_hero_back.modulate.a = 0.0
	add_child(_hero_back)

	_hero_front = ColorRect.new()
	_hero_front.set_anchors_preset(Control.PRESET_FULL_RECT)
	_hero_front.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hero_front.material = _art_material()
	add_child(_hero_front)

	var scrim := ColorRect.new()
	scrim.set_anchors_preset(Control.PRESET_FULL_RECT)
	scrim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_scrim_mat = ShaderMaterial.new()
	_scrim_mat.shader = load("res://shaders/scrim.gdshader")
	scrim.material = _scrim_mat
	add_child(scrim)


func _build_top_bar() -> void:
	_tabs_box = HBoxContainer.new()
	_tabs_box.add_theme_constant_override("separation", 10)
	_tabs_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_tabs_box)
	for i in TABS.size():
		var l := Label.new()
		l.mouse_filter = Control.MOUSE_FILTER_STOP
		l.gui_input.connect(_on_tab_input.bind(i))
		_tabs_box.add_child(l)
		_tab_labels.append(l)

	_logo = TextureRect.new()
	_logo.texture = load("res://assets/logo.png")
	_logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_logo.stretch_mode = TextureRect.STRETCH_SCALE
	_logo.size = Vector2(210, 210.0 * 137.0 / 850.0)
	_logo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_logo)

	_clock = Label.new()
	_clock.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_clock.mouse_filter = Control.MOUSE_FILTER_IGNORE
	DS.style_label(_clock, 30, DS.TEXT, 600)
	add_child(_clock)

	_avatar = Panel.new()
	_avatar.size = Vector2(56, 56)
	_avatar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(DS.ACCENT, 0.22)
	sb.set_corner_radius_all(28)
	sb.set_border_width_all(2)
	sb.border_color = Color(DS.ACCENT, 0.7)
	_avatar.add_theme_stylebox_override("panel", sb)
	var initial := Label.new()
	initial.text = "D"
	initial.set_anchors_preset(Control.PRESET_FULL_RECT)
	initial.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	initial.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	DS.style_label(initial, 28, DS.TEXT, 700)
	_avatar.add_child(initial)
	add_child(_avatar)


func _build_carousel() -> void:
	_carousel = Control.new()
	_carousel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_carousel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_carousel)


func _build_info() -> void:
	_info = Control.new()
	_info.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_info)

	_title = Label.new()
	_title.clip_text = true
	_title.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	DS.style_label(_title, 76, Color.WHITE, 700)
	_title.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.55))
	_title.add_theme_constant_override("shadow_offset_y", 3)
	_title.add_theme_constant_override("shadow_outline_size", 8)
	_info.add_child(_title)

	_chips = HBoxContainer.new()
	_chips.add_theme_constant_override("separation", 14)
	_chips.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_info.add_child(_chips)
	_chip_src = Label.new()
	_chip_hours = Label.new()
	_chip_last = Label.new()
	for c in [_chip_src, _chip_hours, _chip_last]:
		c.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_chips.add_child(c)

	_play = PanelContainer.new()
	_play.mouse_filter = Control.MOUSE_FILTER_STOP
	_play.gui_input.connect(_on_play_input)
	var psb := StyleBoxFlat.new()
	psb.bg_color = DS.ACCENT
	psb.set_corner_radius_all(999)
	psb.content_margin_left = 34
	psb.content_margin_right = 20
	psb.content_margin_top = 14
	psb.content_margin_bottom = 14
	psb.shadow_color = Color(DS.ACCENT, 0.35)
	psb.shadow_size = 22
	_play.add_theme_stylebox_override("panel", psb)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 18)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_play.add_child(row)
	_play_label = Label.new()
	_play_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	DS.style_label(_play_label, 32, DS.ON_ACCENT, 700)
	row.add_child(_play_label)
	_play_key = Label.new()
	_play_key.mouse_filter = Control.MOUSE_FILTER_IGNORE
	DS.pill(_play_key, Color(0.04, 0.07, 0.13, 0.18), DS.ON_ACCENT, 24, 700, 14, 3)
	row.add_child(_play_key)
	_info.add_child(_play)


func _build_pages() -> void:
	_profile_box = VBoxContainer.new()
	_profile_box.alignment = BoxContainer.ALIGNMENT_CENTER
	_profile_box.add_theme_constant_override("separation", 26)
	_profile_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_profile_box.visible = false
	add_child(_profile_box)
	var av := Panel.new()
	av.custom_minimum_size = Vector2(150, 150)
	av.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var asb := StyleBoxFlat.new()
	asb.bg_color = Color(DS.ACCENT, 0.22)
	asb.set_corner_radius_all(75)
	asb.set_border_width_all(3)
	asb.border_color = DS.ACCENT
	av.add_theme_stylebox_override("panel", asb)
	var ai := Label.new()
	ai.text = "D"
	ai.set_anchors_preset(Control.PRESET_FULL_RECT)
	ai.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	ai.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	DS.style_label(ai, 76, DS.TEXT, 700)
	av.add_child(ai)
	_profile_box.add_child(av)
	_profile_name = Label.new()
	_profile_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	DS.style_label(_profile_name, 56, Color.WHITE, 700)
	_profile_box.add_child(_profile_name)
	var tiles := HBoxContainer.new()
	tiles.alignment = BoxContainer.ALIGNMENT_CENTER
	tiles.add_theme_constant_override("separation", 28)
	_profile_box.add_child(tiles)
	var t1 := _stat_tile()
	_stat_games_n = t1[1]
	_stat_games_l = t1[2]
	tiles.add_child(t1[0])
	var t2 := _stat_tile()
	_stat_hours_n = t2[1]
	_stat_hours_l = t2[2]
	tiles.add_child(t2[0])

	_apps_box = VBoxContainer.new()
	_apps_box.alignment = BoxContainer.ALIGNMENT_CENTER
	_apps_box.add_theme_constant_override("separation", 14)
	_apps_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_apps_box.visible = false
	add_child(_apps_box)
	_apps_title = Label.new()
	_apps_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	DS.style_label(_apps_title, 80, Color.WHITE, 700)
	_apps_box.add_child(_apps_title)
	_apps_sub = Label.new()
	_apps_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	DS.style_label(_apps_sub, 32, DS.MUTED, 400)
	_apps_box.add_child(_apps_sub)


## A stat tile: returns [panel, number label, caption label].
func _stat_tile() -> Array:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(340, 150)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(1, 1, 1, 0.07)
	sb.set_corner_radius_all(24)
	sb.set_border_width_all(1)
	sb.border_color = Color(1, 1, 1, 0.14)
	sb.set_content_margin_all(24)
	p.add_theme_stylebox_override("panel", sb)
	var v := VBoxContainer.new()
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	p.add_child(v)
	var n := Label.new()
	n.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	DS.style_label(n, 64, DS.ACCENT, 700)
	v.add_child(n)
	var l := Label.new()
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	DS.style_label(l, 26, DS.MUTED, 400)
	v.add_child(l)
	return [p, n, l]


func _build_overlay() -> void:
	_hints = HBoxContainer.new()
	_hints.add_theme_constant_override("separation", 40)
	_hints.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_hints)

	_toast = Label.new()
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_toast.modulate.a = 0.0
	DS.style_label(_toast, 30, Color.WHITE, 600)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.08, 0.09, 0.13, 0.94)
	sb.set_corner_radius_all(20)
	sb.set_content_margin_all(22)
	sb.border_color = DS.ACCENT
	sb.set_border_width_all(2)
	_toast.add_theme_stylebox_override("normal", sb)
	add_child(_toast)


func _add_action(action: String, keys: Array, pad: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for k in keys:
		var e := InputEventKey.new()
		e.physical_keycode = k
		InputMap.action_add_event(action, e)
	for b in pad:
		var j := InputEventJoypadButton.new()
		j.button_index = b
		InputMap.action_add_event(action, j)


# ---------------------------------------------------------------- layout and language

func _layout() -> void:
	var w := size.x
	var h := size.y
	var rtl := L10n.is_rtl()
	var m := DS.MARGIN_X
	var my := DS.MARGIN_Y

	for hero in [_hero_back, _hero_front]:
		hero.material.set_shader_parameter("aspect", w / h)

	# top bar
	_tabs_box.reset_size()
	var tw := _tabs_box.get_combined_minimum_size().x
	_tabs_box.position = Vector2((w - tw) * 0.5, my)
	_logo.position = Vector2(w - m - _logo.size.x if rtl else m, my + 15)
	_avatar.position = Vector2(m if rtl else w - m - 56.0, my)
	# the clock text is set after this runs the first time, so give it a fixed width ("00:00") and let it
	# sit next to the avatar: Godot mirrors alignment in RTL, so RIGHT here means "toward the avatar" in Arabic
	var cw := 120.0
	_clock.size = Vector2(cw, 56)
	_clock.position = Vector2(m + 74.0 if rtl else w - m - 74.0 - cw, my)
	_clock.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT

	# info block on the start side
	var iw := minf(1100.0, w * 0.58)
	_info_base = Vector2(w - m - iw if rtl else m, 262.0)
	_info.size = Vector2(iw, 280)
	if _info_tween == null or not _info_tween.is_running():
		_info.position = _info_base
	# Godot mirrors alignment in RTL layouts: LEFT means "start" (right in Arabic), which is what we want.
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	_title.position = Vector2(0, 0)
	_title.size = Vector2(iw, 104)
	_chips.reset_size()
	_chips.position = Vector2(0, 116)
	_chips.size = Vector2(iw, 56)
	_play.reset_size()
	var pw := _play.get_combined_minimum_size().x
	_play.position = Vector2(iw - pw if rtl else 0.0, 196)

	# pages
	_profile_box.position = Vector2(0, 150)
	_profile_box.size = Vector2(w, h - 330)
	_apps_box.position = Vector2(0, 150)
	_apps_box.size = Vector2(w, h - 330)

	# hints and toast
	_hints.reset_size()
	var hw := _hints.get_combined_minimum_size().x
	_hints.position = Vector2((w - hw) * 0.5, h - my - 42)
	_toast.size = Vector2(minf(1100.0, w - 120.0), 0)
	_toast.position = Vector2((w - _toast.size.x) * 0.5, h * 0.5 + 10)


func _apply_language() -> void:
	var rtl := L10n.is_rtl()
	layout_direction = Control.LAYOUT_DIRECTION_RTL if rtl else Control.LAYOUT_DIRECTION_LTR
	var td := Control.TEXT_DIRECTION_RTL if rtl else Control.TEXT_DIRECTION_LTR
	for l in [_title, _chip_src, _chip_hours, _chip_last, _play_label, _profile_name, _apps_title, _apps_sub, _toast]:
		l.text_direction = td
	_scrim_mat.set_shader_parameter("rtl", rtl)
	for i in TABS.size():
		_tab_labels[i].text = L10n.t(TABS[i])
	_play_label.text = L10n.t("play")
	_style_tabs()
	_refresh_info()
	_refresh_pages()
	_rebuild_hints()
	_layout()


func _style_tabs() -> void:
	for i in _tab_labels.size():
		var on := i == tab
		var fill := Color(DS.ACCENT, 0.20) if on else Color(0, 0, 0, 0)
		var outline := Color(DS.ACCENT, 0.65) if on else Color(0, 0, 0, 0)
		DS.pill(_tab_labels[i], fill, Color.WHITE if on else DS.MUTED, 28, 600, 30, 10, outline)


func _refresh_info() -> void:
	if games.is_empty():
		_title.text = ""
		return
	var g := games[idx]
	_title.text = g.title
	DS.pill(_chip_src, Color(DS.ACCENT, 0.22), DS.ACCENT, 26, 600, 22, 8)
	DS.pill(_chip_hours, Color(1, 1, 1, 0.12), DS.TEXT, 26, 500, 22, 8)
	DS.pill(_chip_last, Color(1, 1, 1, 0.12), DS.TEXT, 26, 500, 22, 8)
	_chip_src.text = L10n.t("src_" + g.source)
	_chip_hours.text = "%s %s" % [("%.1f" % g.hours).trim_suffix(".0"), L10n.t("hours")]
	_chip_last.text = "%s: %s" % [L10n.t("last"), L10n.t(g.last_played)]


func _refresh_pages() -> void:
	var on_games := tab == 0
	_carousel.visible = on_games
	_info.visible = on_games
	_profile_box.visible = tab == 1
	_apps_box.visible = tab == 2
	var total := 0.0
	for g in games:
		total += g.hours
	_profile_name.text = L10n.t("player")
	_stat_games_n.text = str(games.size())
	_stat_games_l.text = L10n.t("stat_games")
	_stat_hours_n.text = ("%.1f" % total).trim_suffix(".0")
	_stat_hours_l.text = L10n.t("stat_hours")
	_apps_title.text = L10n.t("soon")
	_apps_sub.text = L10n.t("apps_soon")


func _key(what: String) -> String:
	match what:
		"accept":
			return "A" if _pad else "Enter"
		"tabs":
			return "LB / RB" if _pad else "Q / E"
		"lang":
			return "Y" if _pad else "F2"
		_:
			return "D-pad" if _pad else "← →"


func _rebuild_hints() -> void:
	for c in _hints.get_children():
		_hints.remove_child(c)
		c.queue_free()
	var items := [
		[_key("move"), L10n.t("move")],
		[_key("accept"), L10n.t("play")],
		[_key("tabs"), L10n.t("switch_tab")],
		[_key("lang"), L10n.t("lang")],
	]
	var td := Control.TEXT_DIRECTION_RTL if L10n.is_rtl() else Control.TEXT_DIRECTION_LTR
	for it in items:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		var k := Label.new()
		k.text = it[0]
		DS.pill(k, Color(1, 1, 1, 0.14), DS.TEXT, 22, 700, 14, 3)
		row.add_child(k)
		var d := Label.new()
		d.text = it[1]
		d.text_direction = td
		DS.style_label(d, 24, DS.MUTED, 500)
		row.add_child(d)
		_hints.add_child(row)
	if _play_key:
		_play_key.text = _key("accept")
	if is_inside_tree():
		_layout.call_deferred()


# ---------------------------------------------------------------- behaviour

func _move(screen_dir: int) -> void:
	if tab != 0 or games.is_empty():
		return
	# In RTL the first game is on the right, so "right" goes back.
	var step := -screen_dir if L10n.is_rtl() else screen_dir
	_select(clampi(idx + step, 0, games.size() - 1))


func _apply_art(mat: ShaderMaterial, g: GameEntry) -> void:
	mat.set_shader_parameter("c1", g.accent)
	mat.set_shader_parameter("c2", g.dark)
	mat.set_shader_parameter("seed", g.art_seed)
	mat.set_shader_parameter("has_tex", g.hero != null)
	if g.hero != null:
		mat.set_shader_parameter("tex", g.hero)


func _select(i: int, instant: bool = false) -> void:
	if games.is_empty():
		return
	var changed := i != idx
	idx = i
	var g := games[idx]
	if instant:
		pos = float(idx)
		_base_mat.set_shader_parameter("tint", g.accent)
		_apply_art(_hero_front.material, g)
		_front_entry = g
		_refresh_info()
		return
	if not changed:
		return

	# background tint + hero crossfade with a slow zoom
	if _tint_tween:
		_tint_tween.kill()
	var from: Color = _base_mat.get_shader_parameter("tint")
	_tint_tween = create_tween()
	_tint_tween.tween_method(func(c: Color) -> void: _base_mat.set_shader_parameter("tint", c), from, g.accent, 0.45)
	if _hero_tween:
		_hero_tween.kill()
	if _front_entry != null:
		_apply_art(_hero_back.material, _front_entry)
		_hero_back.modulate.a = 1.0
	_apply_art(_hero_front.material, g)
	_front_entry = g
	_hero_front.modulate.a = 0.0
	_hero_tween = create_tween().set_parallel(true)
	_hero_tween.tween_property(_hero_front, "modulate:a", 1.0, 0.45)
	_hero_tween.tween_property(_hero_back, "modulate:a", 0.0, 0.45)
	_hero_tween.tween_method(func(z: float) -> void: _hero_front.material.set_shader_parameter("zoom", z), 1.08, 1.0, 1.4).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)

	# info block: fade in and rise a little
	_refresh_info()
	_layout()
	if _info_tween:
		_info_tween.kill()
	_info.modulate.a = 0.0
	_info.position = _info_base + Vector2(0, 18)
	_info_tween = create_tween().set_parallel(true)
	_info_tween.tween_property(_info, "modulate:a", 1.0, 0.30)
	_info_tween.tween_property(_info, "position", _info_base, 0.30).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)


func _play_entrance() -> void:
	for c in cards:
		c.intro = 0.0
		var tw := create_tween()
		tw.tween_interval(0.35 + 0.07 * c.index)
		tw.tween_property(c, "intro", 1.0, 0.55).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_info.modulate.a = 0.0
	var it := create_tween()
	it.tween_interval(0.2)
	it.tween_property(_info, "modulate:a", 1.0, 0.5)


func _set_tab(t: int) -> void:
	tab = posmod(t, TABS.size())
	_style_tabs()
	_refresh_pages()
	_layout()


func _on_tab_input(event: InputEvent, i: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_set_tab(i)


func _on_play_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_launch_selected()


func _on_card_pressed(card: GameCard) -> void:
	if card.index == idx:
		_launch_selected()
	else:
		_select(card.index)


func _launch_selected() -> void:
	if tab != 0 or games.is_empty():
		return
	var msg := provider.launch(games[idx])
	if msg != "":
		_show_toast(msg)


func _show_toast(text: String) -> void:
	_toast.text = text
	_toast.reset_size()
	_toast.size.x = minf(1100.0, size.x - 120.0)
	_toast.position.x = (size.x - _toast.size.x) * 0.5
	if _toast_tween:
		_toast_tween.kill()
	_toast.modulate.a = 1.0
	_toast_tween = create_tween()
	_toast_tween.tween_interval(2.4)
	_toast_tween.tween_property(_toast, "modulate:a", 0.0, 0.4)


## The row slides so the selected card stays at the start margin: it is big and ringed, the next
## ones follow at normal size and dim, the previous ones slide out and fade.
func _update_cards(delta: float) -> void:
	pos = lerpf(pos, float(idx), 1.0 - exp(-11.0 * delta))
	var rtl := L10n.is_rtl()
	var w := size.x
	var floor_y := size.y - 130.0
	for c in cards:
		var d := float(c.index) - pos
		var ad := absf(d)
		var focus := clampf(1.0 - ad, 0.0, 1.0)
		var s := lerpf(1.0, FOCUS_SCALE, focus)
		var left := DS.MARGIN_X + d * STEP + EXTRA * clampf(d, 0.0, 1.0)
		var center := left + DS.CARD_W * s * 0.5
		var sx := w - center if rtl else center
		c.position = Vector2(sx - DS.CARD_W * 0.5, floor_y - DS.CARD_H - 12.0 * focus + (1.0 - c.intro) * 90.0)
		c.scale = Vector2(s, s)
		c.z_index = int(10.0 - ad * 2.0)
		var a := clampf(1.0 + d * 1.1, 0.0, 1.0) * c.intro
		c.modulate.a = a
		c.visible = a > 0.01 and sx > -300.0 and sx < w + 300.0
		c.set_focus_amount(focus)
