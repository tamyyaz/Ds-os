extends SceneTree
## Headless check of the carousel input: run with
##   ENGINE --headless --path . --script res://tests/nav_test.gd
## Prints PASS/FAIL lines and exits with code 1 on any failure.

var failures := 0


func _check(name: String, cond: bool) -> void:
	print(("PASS " if cond else "FAIL ") + name)
	if not cond:
		failures += 1


func _press(action: String, frames: int = 3) -> void:
	Input.action_press(action)
	for i in frames:
		await process_frame
	Input.action_release(action)
	await process_frame
	await process_frame


func _initialize() -> void:
	var main: Control = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	await process_frame

	_check("starts on the first game", main.idx == 0)

	# Arabic (RTL): the first game is on the right, so "left" goes forward.
	L10n.lang = "ar"
	await _press("ui_left")
	_check("RTL: left moves to the next game", main.idx == 1)
	await _press("ui_right")
	_check("RTL: right goes back", main.idx == 0)
	await _press("ui_right")
	_check("RTL: cannot go before the first game", main.idx == 0)

	# English (LTR): "right" goes forward.
	L10n.lang = "en"
	main._apply_language()
	await _press("ui_right")
	_check("LTR: right moves to the next game", main.idx == 1)

	# Tabs and language keys.
	var ev := InputEventAction.new()
	ev.action = "tab_next"
	ev.pressed = true
	Input.parse_input_event(ev)
	await process_frame
	await process_frame
	_check("tab_next goes to Profile", main.tab == 1)
	await _press("ui_left")
	_check("arrows do nothing outside Games", main.idx == 1)

	# Launch returns a message (demo provider), it must not crash.
	main._set_tab(0)
	var msg: String = main.provider.launch(main.games[main.idx])
	_check("demo launch returns a message", msg != "")

	# Reaches the last game and stops there.
	for i in 10:
		main._move(1)
	_check("stops on the last game", main.idx == main.games.size() - 1)

	print("failures: ", failures)
	quit(1 if failures > 0 else 0)
