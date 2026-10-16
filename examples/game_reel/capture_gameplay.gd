extends Node
## Recording driver for the game reel (reels/claude-game). Not part of the game: copy the game's Godot project to a
## scratch folder, put this file at its root, register it as an autoload (Capture="*res://capture.gd"), then per clip:
##   xvfb-run -a godot --path . --rendering-driver opengl3 --resolution 1080x1920 \
##       --write-movie out/NAME.avi --fixed-fps 30 -- --clip=NAME
## Movie Maker mode steps time at exactly 30 fps, so every recording is deterministic and real-time-independent.
## Inert unless --clip is given. Use a fresh XDG_DATA_HOME per clip so each starts from a clean save.
## Plays the real game through its real input handlers (board _gui_input, button pressed
## signals) and draws a translucent touch indicator where each tap lands.

var clip := ""
var main: Node
var touch: TouchDots


class TouchDots extends Control:
	var dots: Array = []  # [pos, age]
	func _init() -> void:
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		set_anchors_preset(Control.PRESET_FULL_RECT)
		z_index = 100
	func add(p: Vector2) -> void:
		dots.append([p, 0.0])
	func _process(d: float) -> void:
		for x in dots:
			x[1] += d
		dots = dots.filter(func(x): return x[1] < 0.45)
		queue_redraw()
	func _draw() -> void:
		for x in dots:
			var t: float = x[1] / 0.45
			var a: float = 0.55 * (1.0 - t)
			draw_circle(x[0], 34.0 + 22.0 * t, Color(1, 1, 1, a * 0.55))
			draw_arc(x[0], 34.0 + 22.0 * t, 0, TAU, 48, Color(0.1, 0.1, 0.15, a), 3.0, true)


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--clip="):
			clip = a.substr(7)
	if clip == "":
		set_process(false)
		return
	_run.call_deferred()


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _tap_cell(i: int, hold := 0.11) -> void:
	var b = main.current.board
	var p: Vector2 = b.cell_center(i)
	touch.add(b.global_position + p)
	var ev := InputEventMouseButton.new()
	ev.button_index = MOUSE_BUTTON_LEFT
	ev.pressed = true
	ev.position = p
	b._gui_input(ev)
	await _wait(hold)
	var up := InputEventMouseButton.new()
	up.button_index = MOUSE_BUTTON_LEFT
	up.pressed = false
	up.position = p
	b._gui_input(up)


func _tap_button(btn: BaseButton) -> void:
	touch.add(btn.get_global_rect().get_center())
	await _wait(0.08)
	btn.pressed.emit()


func _tap_at(p: Vector2) -> void:
	touch.add(p)
	await _wait(0.08)


## Rotations needed per tile to reach the stored solution from the current state.
func _taps_to_solve() -> Array:
	var play = main.current
	var out: Array = []
	for mv in play.level["solution"]["moves"]:
		out.append([int(mv[0]), int(mv[1])])
	# Clockwise taps last, so the on-screen taps are plain taps (counter-clockwise ones are pre-applied).
	out.sort_custom(func(a, b): return a[1] < b[1])
	return out


func _apply_silently(moves: Array) -> void:
	var play = main.current
	for m in moves:
		play._on_rotate(int(m[0]), int(m[1]))
	await _wait(0.5)


func _open(id: String) -> void:
	main.goto("play", {"kind": "campaign", "index": Game.state.campaign_index[id]})
	await _wait(0.05)


func _unlock_progress(n: int) -> void:
	for i in n:
		var lvl: Dictionary = Game.state.campaign[i]
		if not Game.state.data["progress"].has(lvl["id"]):
			Game.state.data["progress"][lvl["id"]] = {"completed": true, "best": lvl["par"], "par": lvl["par"], "stars": 3, "completedAt": 1, "kind": "campaign"}
	Game.state.data["stats"]["perfect"] = n
	LFCrew.evaluate_unlocks(Game.state.data, Game.state.campaign, LFGameState.now_ms())  # latest build only


func _solve_and_run(id: String, pre: int, gap := 0.32) -> void:
	await _open(id)
	var moves := _taps_to_solve()
	var ccw := moves.filter(func(m): return m[1] < 0).size()
	pre = maxi(pre, ccw)
	await _apply_silently(moves.slice(0, pre))
	await _wait(0.25)
	for m in moves.slice(pre):
		await _tap_cell(m[0])
		await _wait(gap)
	await _wait(0.15)
	await _tap_button(main.current.run_btn)
	await _until_done()


func _until_done() -> void:
	var t := 0.0
	while not main.current.board.celebrating and not main.has_overlay() and t < 15.0:
		await get_tree().process_frame
		t += get_process_delta_time()
	if t >= 15.0:
		push_error("CAPTURE: run did not complete")


func _run() -> void:
	main = get_tree().root.get_node("Main")
	touch = TouchDots.new()
	get_tree().root.add_child(touch)
	Game.set_setting("analyticsAsked", true)
	await _wait(1.4)
	match clip:
		"hook":
			# Space Logistics, three colours: last taps, Run, the crew celebrates.
			_unlock_progress(30)
			await _solve_and_run("c31", 4, 0.28)
			await _wait(3.2)
		"solve":
			# Parcel Station from a fresh board: every tap shown.
			_unlock_progress(19)
			await _solve_and_run("c20", 0, 0.3)
			await _wait(4.0)
		"fail_fix":
			# Run too early -> the failure is explained; a hint; fix it; deliver.
			_unlock_progress(7)
			await _open("c08")
			await _wait(0.6)
			await _tap_button(main.current.run_btn)
			await _wait(2.6)
			await _tap_button(main.current.hint_btn)
			await _wait(1.4)
			var moves := _taps_to_solve()
			await _apply_silently(moves.filter(func(m): return m[1] < 0))
			for m in moves.filter(func(m): return m[1] > 0):
				await _tap_cell(m[0])
				await _wait(0.3)
			await _tap_button(main.current.run_btn)
			await _until_done()
			await _wait(3.0)
		"neon":
			_unlock_progress(25)
			await _solve_and_run("x26", 0, 0.32)
			await _wait(2.6)
		"big":
			_unlock_progress(33)
			await _solve_and_run("c34", 13, 0.26)
			await _wait(3.0)
		"menus":
			_unlock_progress(12)
			LFCrew.equip(Game.state.data, "bloop", "bloop_crown")
			LFCrew.equip(Game.state.data, "glitch", "glitch_shades")
			LFCrew.equip(Game.state.data, "naps", "naps_detective")
			main.home()
			await _wait(2.2)
			main.goto("crew")
			await _wait(2.0)
			main.goto("crew", {"id": "bloop"})
			await _wait(2.4)
			main.goto("levels")
			await _wait(0.8)
			# Scroll through all five worlds, like a finger drag would.
			var sc: ScrollContainer = main.current.find_children("*", "ScrollContainer", true, false)[0]
			var maxv: float = sc.get_v_scroll_bar().max_value - sc.size.y
			var t := 0.0
			while t < 3.6:
				t += get_process_delta_time()
				var k: float = clampf(t / 3.6, 0.0, 1.0)
				sc.scroll_vertical = int(maxv * (k * k * (3.0 - 2.0 * k)))
				await get_tree().process_frame
			await _wait(0.6)
		"c06":
			_unlock_progress(5)
			await _open("c06")
			await _wait(0.8)
			for m in _taps_to_solve():
				await _tap_cell(m[0])
				await _wait(0.3)
			await _wait(0.15)
			await _tap_button(main.current.run_btn)
			await _wait(6.0)
		"first":
			# Level 1 with the onboarding coach.
			await _open("c01")
			await _wait(1.6)
			await _tap_cell(_taps_to_solve()[0][0])
			await _wait(0.4)
			await _tap_button(main.current.run_btn)
			await _wait(4.0)
		_:
			push_error("unknown clip " + clip)
	get_tree().quit()
