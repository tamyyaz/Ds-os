extends Control
## Darksham Launcher: Games / Profile / Apps. Only Games is built; Profile shows real counts,
## Apps is a "coming soon" page. Keys: arrows or D-pad/stick move, Enter or A plays,
## Q/E or shoulder buttons switch tab, F2 or Y switches Arabic/English.

const TABS := ["games", "profile", "apps"]

var provider: LibraryProvider = MockProvider.new()
var games: Array[GameEntry] = []
var cards: Array[GameCard] = []
var idx := 0
var pos := 0.0            # smoothed position of the carousel (float index)
var tab := 0

var _bg_mat: ShaderMaterial
var _tab_labels: Array[Label] = []
var _tabs_box: HBoxContainer
var _logo: TextureRect
var _clock: Label
var _carousel: Control
var _title: Label
var _meta: Label
var _hint: Label
var _toast: Label
var _page: Label            # text of the Profile / Apps pages
var _nav_prev := 0
var _nav_timer := 0.0
var _clock_timer := 1.0
var _title_tween: Tween
var _toast_tween: Tween


func _ready() -> void:
	_add_action("tab_prev", [KEY_Q], [JOY_BUTTON_LEFT_SHOULDER])
	_add_action("tab_next", [KEY_E], [JOY_BUTTON_RIGHT_SHOULDER])
	_add_action("toggle_lang", [KEY_F2], [JOY_BUTTON_Y])

	_build_background()
	_build_top_bar()
	_build_carousel()
	_build_info()
	_build_overlay()

	games = provider.list_games()
	for i in games.size():
		var c := GameCard.new()
		c.setup(games[i], i)
		c.pressed.connect(_on_card_pressed)
		_carousel.add_child(c)
		cards.append(c)

	# Dev/test options after "--": --lang=en  --select=2  --tab=1  (used for screenshots)
	var start_idx := 0
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--lang="):
			L10n.lang = a.substr(7)
		elif a.begins_with("--select="):
			start_idx = clampi(int(a.substr(9)), 0, maxi(games.size() - 1, 0))
		elif a.begins_with("--tab="):
			tab = clampi(int(a.substr(6)), 0, TABS.size() - 1)

	resized.connect(_layout)
	_apply_language()
	_select(start_idx, true)


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

func _build_background() -> void:
	var bg := ColorRect.new()
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bg_mat = ShaderMaterial.new()
	_bg_mat.shader = load("res://shaders/bg.gdshader")
	bg.material = _bg_mat
	add_child(bg)


func _build_top_bar() -> void:
	_tabs_box = HBoxContainer.new()
	_tabs_box.add_theme_constant_override("separation", 40)
	_tabs_box.alignment = BoxContainer.ALIGNMENT_CENTER
	_tabs_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_tabs_box)
	for i in TABS.size():
		var l := Label.new()
		l.mouse_filter = Control.MOUSE_FILTER_STOP
		l.gui_input.connect(_on_tab_input.bind(i))
		DS.style_label(l, 30, DS.MUTED, 600)
		_tabs_box.add_child(l)
		_tab_labels.append(l)

	_logo = TextureRect.new()
	_logo.texture = load("res://assets/logo.png")
	_logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_logo.stretch_mode = TextureRect.STRETCH_SCALE
	_logo.size = Vector2(200, 200.0 * 137.0 / 850.0)
	_logo.modulate = Color(1, 1, 1, 0.9)
	_logo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_logo)

	_clock = Label.new()
	DS.style_label(_clock, 28, DS.TEXT, 600)
	_clock.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_clock)


func _build_carousel() -> void:
	_carousel = Control.new()
	_carousel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_carousel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_carousel)


func _build_info() -> void:
	_title = Label.new()
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	DS.style_label(_title, 64, Color.WHITE, 700)
	add_child(_title)

	_meta = Label.new()
	_meta.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_meta.mouse_filter = Control.MOUSE_FILTER_IGNORE
	DS.style_label(_meta, 26, DS.MUTED, 400)
	add_child(_meta)


func _build_overlay() -> void:
	_hint = Label.new()
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	DS.style_label(_hint, 22, DS.MUTED, 400)
	add_child(_hint)

	_page = Label.new()
	_page.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_page.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_page.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_page.visible = false
	DS.style_label(_page, 40, DS.TEXT, 600)
	add_child(_page)

	_toast = Label.new()
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_toast.modulate.a = 0.0
	DS.style_label(_toast, 28, Color.WHITE, 600)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.08, 0.09, 0.13, 0.92)
	sb.set_corner_radius_all(14)
	sb.set_content_margin_all(18)
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
	_tabs_box.reset_size()
	var tabs_w := _tabs_box.get_combined_minimum_size().x
	_tabs_box.position = Vector2((w - tabs_w) * 0.5, 40)
	var rtl := L10n.is_rtl()
	_logo.position = Vector2(w - 60 - _logo.size.x if rtl else 60, 52)
	_clock.position = Vector2(60 if rtl else w - 60 - 120, 44)
	_clock.size = Vector2(120, 40)
	_clock.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT if rtl else HORIZONTAL_ALIGNMENT_RIGHT
	_title.position = Vector2(0, 150)
	_title.size = Vector2(w, 90)
	_meta.position = Vector2(0, 245)
	_meta.size = Vector2(w, 40)
	_hint.position = Vector2(0, h - 64)
	_hint.size = Vector2(w, 32)
	_page.position = Vector2(0, 0)
	_page.size = Vector2(w, h)
	_toast.size = Vector2(minf(1100.0, w - 120.0), 0)
	_toast.position = Vector2((w - _toast.size.x) * 0.5, h * 0.5 + 10)


func _apply_language() -> void:
	layout_direction = Control.LAYOUT_DIRECTION_RTL if L10n.is_rtl() else Control.LAYOUT_DIRECTION_LTR
	var td := Control.TEXT_DIRECTION_RTL if L10n.is_rtl() else Control.TEXT_DIRECTION_LTR
	for l in [_title, _meta, _hint, _page, _toast]:
		l.text_direction = td
	for i in TABS.size():
		_tab_labels[i].text = L10n.t(TABS[i])
	_style_tabs()
	_hint.text = "◀ ▶  %s      Enter / A  %s      Q / E  %s      F2  %s" % [
		L10n.t("move"), L10n.t("play"), L10n.t("switch_tab"), L10n.t("lang")]
	_layout()
	_refresh_info()
	_refresh_page()


func _style_tabs() -> void:
	for i in _tab_labels.size():
		var on := i == tab
		var l := _tab_labels[i]
		l.add_theme_color_override("font_color", Color.WHITE if on else DS.MUTED)
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0, 0, 0, 0)
		sb.border_width_bottom = 3
		sb.border_color = DS.ACCENT if on else Color(0, 0, 0, 0)
		sb.content_margin_left = 14
		sb.content_margin_right = 14
		sb.content_margin_bottom = 8
		l.add_theme_stylebox_override("normal", sb)


func _refresh_info() -> void:
	if games.is_empty():
		_title.text = ""
		_meta.text = ""
		return
	var g := games[idx]
	_title.text = g.title
	var hours := "%s %s" % [("%.1f" % g.hours).trim_suffix(".0"), L10n.t("hours")]
	# Each piece is an isolate (U+2068..U+2069) so numbers and Latin names do not reorder the Arabic around them.
	var parts := [L10n.t("src_" + g.source), hours, "%s: %s" % [L10n.t("last"), L10n.t(g.last_played)]]
	var iso: Array[String] = []
	for p in parts:
		iso.append("\u2068" + p + "\u2069")
	_meta.text = "  •  ".join(iso)


func _refresh_page() -> void:
	var on_games := tab == 0
	_carousel.visible = on_games
	_title.visible = on_games
	_meta.visible = on_games
	_page.visible = not on_games
	if tab == 1:
		var total := 0.0
		for g in games:
			total += g.hours
		_page.text = "%s\n\n%s: %d\n%s: %s" % [
			L10n.t("player"), L10n.t("stat_games"), games.size(),
			L10n.t("stat_hours"), ("%.1f" % total).trim_suffix(".0")]
	elif tab == 2:
		_page.text = "%s\n\n%s" % [L10n.t("soon"), L10n.t("apps_soon")]


# ---------------------------------------------------------------- behaviour

func _move(screen_dir: int) -> void:
	if tab != 0 or games.is_empty():
		return
	# In RTL the first game is on the right, so "right" goes back.
	var step := -screen_dir if L10n.is_rtl() else screen_dir
	_select(clampi(idx + step, 0, games.size() - 1))


func _select(i: int, instant: bool = false) -> void:
	if games.is_empty():
		return
	var changed := i != idx
	idx = i
	if instant:
		pos = float(idx)
		_bg_mat.set_shader_parameter("tint", games[idx].accent)
		_refresh_info()
		return
	if not changed:
		return
	var from: Color = _bg_mat.get_shader_parameter("tint")
	var tw := create_tween()
	tw.tween_method(func(c: Color) -> void: _bg_mat.set_shader_parameter("tint", c), from, games[idx].accent, 0.45)
	_refresh_info()
	if _title_tween:
		_title_tween.kill()
	_title.modulate.a = 0.0
	_meta.modulate.a = 0.0
	_title_tween = create_tween().set_parallel(true)
	_title_tween.tween_property(_title, "modulate:a", 1.0, 0.25)
	_title_tween.tween_property(_meta, "modulate:a", 1.0, 0.25)


func _set_tab(t: int) -> void:
	tab = posmod(t, TABS.size())
	_style_tabs()
	_refresh_page()


func _on_tab_input(event: InputEvent, i: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_set_tab(i)


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
	_toast_tween.tween_interval(2.2)
	_toast_tween.tween_property(_toast, "modulate:a", 0.0, 0.4)


## Places every card from its distance to the (smoothed) selection: the selected one is big and
## framed, the neighbours smaller and dim, the far ones fade out.
func _update_cards(delta: float) -> void:
	pos = lerpf(pos, float(idx), 1.0 - exp(-10.0 * delta))
	var dirn := -1.0 if L10n.is_rtl() else 1.0
	var cx := size.x * 0.5
	var floor_y := size.y - 220.0
	for c in cards:
		var d := (float(c.index) - pos) * dirn
		var ad := absf(d)
		var s := lerpf(1.0, 0.7, clampf(ad, 0.0, 1.0))
		if ad > 1.0:
			s = lerpf(0.7, 0.55, clampf(ad - 1.0, 0.0, 1.0))
		var off := ad * 400.0 if ad <= 1.0 else 400.0 + (ad - 1.0) * 270.0
		var focus := clampf(1.0 - ad, 0.0, 1.0)
		c.position = Vector2(cx + signf(d) * off - DS.CARD_W * 0.5, floor_y - DS.CARD_H - 14.0 * focus)
		c.scale = Vector2(s, s)
		c.z_index = int(10.0 - ad * 2.0)
		c.modulate.a = clampf(1.0 - (ad - 2.6) * 1.5, 0.0, 1.0)
		c.visible = c.modulate.a > 0.01
		c.set_focus_amount(focus)
