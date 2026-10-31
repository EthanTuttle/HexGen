class_name TouchTest
extends Node
## Plays one loop by touch alone, for testing the touch controls without a phone and for the recording:
## every action is an injected InputEventScreenTouch / InputEventScreenDrag (one or two fingers), the same
## events an iPhone sends. It checks what each gesture did and prints TOUCH OK / TOUCH FAIL lines.
## Run with `-- --touchtest` in a phone-sized window (iPhone 15 Pro landscape is 852 x 393 pt):
##   godot --path godot --resolution 1704x786 -- --touchtest [--shots] [--quit]
## Fingers show as circles with a caption saying the gesture (the test's own overlay, not game UI).
## Like the demo it never cheats the rules, except that it adds an encounter next to the party if none has
## spawned when it's time to fight (said on screen).

var game: Game
var shots := false
var prefix := "touch"       # `--shotname=x` names the stills x_NN_….png
var fails := 0
var _n := 0
var _fingers := {}          # finger index -> position, for the overlay
var _caption := ""
var _overlay := _Overlay.new()
var _times = null          # frame times (ms) while measuring a gesture, or null when not
var _last_us := 0


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shotname="):
			prefix = a.split("=")[1]
	var layer := CanvasLayer.new()
	layer.layer = 100
	add_child(layer)
	_overlay.test = self
	_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_overlay)
	_run.call_deferred()


func _process(_delta: float) -> void:
	var now := Time.get_ticks_usec()
	if _times != null and _last_us > 0:
		_times.append((now - _last_us) / 1000.0)
	_last_us = now


## Prints the frame times recorded since `_times = []` (Ethan: dragging an unheld card out of the hand wasn't
## smooth on the phone).
func frame_report(what: String) -> void:
	var t: Array = _times.duplicate()
	_times = null
	t.sort()
	print("FRAMES %s: %d frames, median %.2f ms, worst %.2f ms" % [what, t.size(), t[t.size() / 2], t[-1]])


# --- Injected touches -----------------------------------------------------------------

func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _frame() -> void:
	await get_tree().process_frame


## Injected events are in window pixels; everything here works in the layout's units, so scale.
func _win() -> Vector2:
	return Vector2(DisplayServer.window_get_size()) / get_viewport().get_visible_rect().size


func _touch(i: int, pos: Vector2, pressed: bool) -> void:
	var t := InputEventScreenTouch.new()
	t.index = i
	t.position = pos * _win()
	t.pressed = pressed
	if pressed:
		_fingers[i] = pos
	else:
		_fingers.erase(i)
	Input.parse_input_event(t)
	await _frame()


func _move(i: int, pos: Vector2) -> void:
	var d := InputEventScreenDrag.new()
	d.index = i
	d.relative = (pos - _fingers.get(i, pos)) * _win()
	d.position = pos * _win()
	_fingers[i] = pos
	Input.parse_input_event(d)
	await _frame()


func tap(pos: Vector2) -> void:
	await _touch(0, pos, true)
	await _wait(0.08)
	await _touch(0, pos, false)
	await _wait(0.25)


func hold(pos: Vector2, seconds := 0.7) -> void:
	await _touch(0, pos, true)
	await _wait(seconds)
	await _touch(0, pos, false)


func drag(from: Vector2, to: Vector2, seconds := 0.6) -> void:
	await _touch(0, from, true)
	var steps := maxi(6, int(seconds * 40))
	for k in range(1, steps + 1):
		await _move(0, from.lerp(to, float(k) / steps))
	await _wait(0.1)
	await _touch(0, to, false)


## Two fingers around `centre`: from `r0` apart to `r1` apart, turning by `turn` radians.
func two_finger(centre: Vector2, r0: float, r1: float, turn: float, seconds := 0.8) -> void:
	await _touch(0, centre + Vector2(-r0, 0), true)
	await _touch(1, centre + Vector2(r0, 0), true)
	var steps := maxi(8, int(seconds * 40))
	for k in range(1, steps + 1):
		var f := float(k) / steps
		var r := lerpf(r0, r1, f)
		var a := turn * f
		var off := Vector2(r * cos(a), -r * sin(a))   # screen y is down: a positive turn is anticlockwise
		await _move(0, centre - off)
		await _move(1, centre + off)
	await _wait(0.1)
	await _touch(1, _fingers[1], false)
	await _touch(0, _fingers[0], false)


# --- Finding things on screen ---------------------------------------------------------

func screen_of(world: Vector3) -> Vector2:
	return game.rig.camera.unproject_position(world)


func tile_screen(t: Vector2i) -> Vector2:
	return screen_of(Hex.to3(Hex.tile_position(t.x, t.y)))


## The centre of the first visible control whose text or tooltip starts with `prefix`.
func control(prefix: String) -> Vector2:
	for n in get_tree().root.find_children("*", "Control", true, false):
		var c := n as Control
		if not c.is_visible_in_tree() or c.mouse_filter == Control.MOUSE_FILTER_IGNORE:
			continue
		var t: String = str(c.get("text")) if c.get("text") != null else ""
		if t.begins_with(prefix) or c.tooltip_text.begins_with(prefix):
			return c.get_global_rect().get_center()
	return Vector2.INF


## Pans with one-finger drags until screen point p (where it is now) sits near the middle of the open board.
func pan_to(p: Vector2) -> void:
	var want := Vector2(380, 220)
	for k in 4:
		var off := want - p
		if off.length() < 40:
			return
		var step := off.limit_length(220)
		var from := want - step * 0.5
		await drag(from, from + step, 0.5)
		await _wait(0.2)
		p += step


## Every tappable HUD control drawn smaller than a finger (their hit areas are grown to Rules.FINGER).
func audit(where: String) -> void:
	for n in get_tree().root.find_children("*", "Control", true, false):
		var c := n as Control
		if c.mouse_filter != Control.MOUSE_FILTER_STOP or not c.is_visible_in_tree() or c is Container:
			continue
		if c.size.x < Rules.FINGER or c.size.y < Rules.FINGER:
			var label: String = c.tooltip_text if c.tooltip_text != "" else str(c.get("text")) if c.get("text") != null else c.get_class()
			print("AUDIT %s | %s | %s | %.0f x %.0f | hit %s" % [where, label, c.get_script().get_global_name() if c.get_script() else c.get_class(),
					c.size.x, c.size.y, "grown" if c.has_method("_has_point") and c.get_script() != null else "NOT grown"])


func check(ok: bool, what: String) -> void:
	print("TOUCH %s %s" % ["OK  " if ok else "FAIL", what])
	if not ok:
		fails += 1


func shot(name: String) -> void:
	_n += 1
	if not shots:
		return
	await RenderingServer.frame_post_draw
	var dir := ProjectSettings.globalize_path("res://screens")
	game.get_viewport().get_texture().get_image().save_png(dir.path_join("%s_%02d_%s.png" % [prefix, _n, name]))


func say(text: String) -> void:
	_caption = text
	_overlay.queue_redraw()


# --- The run ------------------------------------------------------------------------

func _run() -> void:
	await _wait(1.2)
	audit("map")
	var demo := Demo.new()   # its slot picker, so the cards grow clusters the way the demo plays
	demo.game = game

	# 1. Drag cards from the hand onto lit slots.
	for k in 3:
		var i := demo._pick_card()
		var terrain: String = game.deck.hand[i]
		var slot := demo._best_slot(terrain)
		var card: Control = game.hud._hand_grid.get_child(i)
		say("Drag a card onto a lit slot")
		var before := game.map.terrains.size()
		var target0 := game.rig.target
		var to := tile_screen(slot) - game.hud.DRAG_LIFT
		if k == 0:
			# Timed (Ethan: an unheld card didn't drag smoothly): the press and the slide, then the drop.
			check(game.held == -1, "the first dragged card isn't held beforehand")
			var from := card.get_global_rect().get_center()
			_times = []
			await _touch(0, from, true)
			for s in range(1, 33):
				await _move(0, from.lerp(to, s / 32.0))
			frame_report("pressing and sliding a card that wasn't held")
			await _wait(0.1)
			_times = []
			await _touch(0, to, false)
			for _f in 3:
				await _frame()
			frame_report("dropping it (the tile is built)")
		else:
			await drag(card.get_global_rect().get_center(), to, 0.8)
		check(game.rig.target.distance_to(target0) < 0.01, "dragging a card doesn't pan the board")
		await _wait(0.5)
		check(game.map.terrains.get(slot) != null and game.map.terrains.size() == before + 1,
				"drag %s from the hand onto slot %s places it" % [terrain, slot])
		if k == 0:
			await shot("drag_place")
		await _wait(0.4)

	# 2. A card dropped off the lit slots goes back to the hand.
	say("Let go off the slots: back to the hand")
	var hand_before := game.deck.hand.size()
	var card0: Control = game.hud._hand_grid.get_child(0)
	var hand_panel: Control = game.hud._hand_grid.get_parent()
	await drag(card0.get_global_rect().get_center(), hand_panel.get_global_rect().get_center() + Vector2(0, 60), 0.6)
	await _wait(0.3)
	check(game.deck.hand.size() == hand_before and game.held == -1, "a card let go over no lit slot goes back to the hand")

	# 3. Tap a card, then tap a lit slot.
	say("Tap a card, then tap a lit slot")
	var j := demo._pick_card()
	var slot2 := demo._best_slot(game.deck.hand[j])
	await tap((game.hud._hand_grid.get_child(j) as Control).get_global_rect().get_center())
	check(game.held == j, "tapping a card holds it")
	await _wait(0.3)
	await tap(tile_screen(slot2))
	await _wait(0.4)
	check(game.map.terrains.has(slot2), "tapping a lit slot places the held card")

	# 4. Long-press a hex: its details.
	say("Long-press a hex: its details")
	await _touch(0, tile_screen(slot2), true)
	await _wait(0.6)
	check(game.popup.visible, "a long-press on a map hex opens its pop-up")
	await shot("long_press_hex")
	await _wait(0.8)
	await _touch(0, tile_screen(slot2), false)
	await _wait(0.2)
	check(game.map.terrains.size() > 0 and game.picked == null, "the long-press didn't pick a walk")

	# 5. Long-press a card in the hand: what hover shows on PC.
	if not game.deck.hand.is_empty():
		say("Long-press a card: its details")
		var c: Control = game.hud._hand_grid.get_child(0)
		var held_before := game.held
		await _touch(0, c.get_global_rect().get_center(), true)
		await _wait(0.6)
		check(game.popup.visible, "a long-press on a hand card shows its details")
		await shot("long_press_card")
		await _wait(0.6)
		await _touch(0, c.get_global_rect().get_center(), false)
		await _wait(0.2)
		check(game.held == held_before, "letting go after a long-press doesn't hold the card")

	# 6. Pinch to zoom: neither places nor walks.
	game.hold(-1)
	say("Pinch to zoom")
	var d0: float = game.rig.distance
	var tiles_before := game.map.terrains.size()
	var party_before := game.party_tile
	await two_finger(Vector2(380, 200), 40, 120, 0.0)
	await _wait(0.4)
	check(game.rig.distance < d0 * 0.8, "pinching out zooms in (%.0f m -> %.0f m)" % [d0, game.rig.distance])
	check(game.map.terrains.size() == tiles_before and game.party_tile == party_before and game.picked == null,
			"the pinch neither placed, picked nor walked")
	check(game.rig.player_moved, "the pinch counts as the player's camera")
	await two_finger(Vector2(380, 200), 110, 50, 0.0)

	# 7. Twist to rotate: free, nothing snaps when the fingers lift (DOCS).
	say("Twist to rotate")
	var y0: float = game.rig.yaw_deg
	await two_finger(Vector2(380, 200), 70, 70, deg_to_rad(40))
	await _wait(0.7)
	check(absf(game.rig.yaw_deg - y0 - 40.0) < 2.0, "a 40° anticlockwise twist turns the board 40° anticlockwise, no snap (%.0f° -> %.0f°)" % [y0, game.rig.yaw_deg])
	await shot("twist")

	# 8. One finger pans; it never taps.
	say("Drag to pan")
	var target0: Vector3 = game.rig.target
	await drag(Vector2(420, 220), Vector2(300, 180), 0.6)
	await _wait(0.3)
	check(game.rig.target.distance_to(target0) > 2.0 and game.picked == null, "a one-finger drag pans and doesn't tap")

	# 9. The nav button's centre gives the camera back.
	say("Nav: centre")
	await tap(control("Camera"))
	await _wait(0.3)
	await tap(control("Center"))
	await _wait(0.6)
	check(not game.rig.player_moved, "the nav button's centre gives the camera back to the game")
	await tap(control("Camera"))

	# 10. The Rest card shows while the party stands on the camp; tapping it rests.
	say("Tap Rest")
	var minute0: float = game.minute
	await tap(control("Rest"))
	await _wait(0.5)
	check(game.minute > minute0 + 5.0, "the Rest card rests (minute %.1f -> %.1f)" % [minute0, game.minute])
	await shot("rest")

	# 11. Two-tap walk to an encounter, then fight it by touch.
	if game.encounters.is_empty():
		var tiles: Array = game.map.terrains.keys().filter(func(t): return t != game.party_tile and t != Rules.START_TILE)
		game.add_encounter(tiles[-1], false)
		game.toast("(touch test) No encounter spawned, so the test added one.", false)
	var goal: Vector2i = game.encounters.keys()[0]
	say("Drag the encounter into view")
	await pan_to(tile_screen(goal))
	say("Tap once: the path and time")
	await tap(tile_screen(goal))
	await _wait(0.3)
	check(game.picked == goal and game.party_tile == Rules.START_TILE, "the first tap shows the path and doesn't walk")
	await shot("walk_preview")
	await _wait(0.6)
	say("Tap again: walk")
	await tap(tile_screen(goal))
	await _wait(0.2)
	check(game.busy, "tapping the same hex again walks")
	await _wait(0.3)
	check(not game.hud._rest.visible, "the Rest card hides once the party leaves the camp")
	while not game.hud.encounter_open():
		await _wait(0.1)
	await _wait(0.5)
	say("Tap Fight")
	await tap(control("Fight"))
	await _wait(1.6)
	check(game.fight.active, "tapping Fight starts the fight")
	await _fight()
	while not game.after.visible:
		await _wait(0.1)
	await _wait(4.5)
	say("Tap Back to map")
	await tap(control("Back to"))
	await _wait(1.2)
	check(not game.fight.active and not game.after.visible, "the after-combat button goes back to the map")
	say("")
	print("TOUCH DONE: %d failed" % fails)
	if shots or "--quit" in OS.get_cmdline_user_args():
		get_tree().quit(1 if fails > 0 else 0)


## The fight, by taps on tokens, hotbar cards and buttons.
func _fight() -> void:
	var f := game.fight
	var long_pressed := false
	audit("combat")
	var guard := 0
	while f.active and guard < 30:   # allies' turns played (the foes' turns don't count)
		if f.phase != "allies" or f.busy:
			await _wait(0.2)
			continue
		guard += 1
		for u in f.allies():
			if not f.active or f.phase != "allies":
				break
			if u.down or f.ap_left(u) <= 0:
				continue
			say("Tap an ally's token")
			await tap(screen_of(f.global_position + u.mini.position))
			await _wait(0.3)
			if not long_pressed and not f.foes_of(u).is_empty():
				long_pressed = true
				var e: Dictionary = f.foes_of(u)[0]
				say("Long-press a foe: its details")
				await _touch(0, screen_of(f.global_position + e.mini.position), true)
				await _wait(0.6)
				check(game.popup.visible, "a long-press on a foe's token shows its details")
				await shot("long_press_foe")
				await _wait(0.6)
				await _touch(0, _fingers[0], false)
			var tries := 0
			while f.active and f.phase == "allies" and f.ap_left(u) > 0 and tries < 5:
				tries += 1
				var foes := f.foes_of(u)
				if foes.is_empty():
					break
				foes.sort_custom(func(a, b): return Rules.hex_distance(a.cell, u.cell) < Rules.hex_distance(b.cell, u.cell))
				var foe: Dictionary = foes[0]
				if Rules.hex_distance(foe.cell, u.cell) == 1:
					say("Attack: card, target, Flip coins")
					await tap(control("Attack"))
					await tap(screen_of(f.global_position + foe.mini.position))
					await tap(control("Flip"))
					await _wait(1.0)
					continue
				var options: Dictionary = f.reachable(u)
				var best := u.cell as Vector2i
				for c in options:
					if Rules.hex_distance(c, foe.cell) < Rules.hex_distance(best, foe.cell):
						best = c
				if best == u.cell:
					break
				say("Move: card, then a lit hex")
				await tap(control("Move"))
				await tap(screen_of(f.global_position + Hex.to3(Hex.cell_position(best.x, best.y))))
				await _wait(0.8)
		if f.active and f.phase == "allies":
			say("End the allies' phase")
			await tap(control("End allies"))
			await _wait(0.4)
			if f.hud.confirm_open():
				await tap(control("End phase"))
			await _wait(0.5)


class _Overlay extends Control:
	var test: TouchTest

	func _process(_d: float) -> void:
		queue_redraw()

	func _draw() -> void:
		for p: Vector2 in test._fingers.values():
			draw_circle(p, 13, Color(1, 1, 1, 0.45))
			draw_arc(p, 13, 0, TAU, 32, Color(0.14, 0.19, 0.17, 0.9), 2.0)
		if test._caption != "":
			var f := UI.font("lilita")
			var w := f.get_string_size(test._caption, HORIZONTAL_ALIGNMENT_LEFT, -1, 13).x
			var r := Rect2(Vector2((size.x - w) * 0.5 - 12, 62), Vector2(w + 24, 24))
			draw_style_box(UI.box(Color(0.14, 0.19, 0.17, 0.85), 12), r)
			draw_string(f, r.position + Vector2(12, 17), test._caption, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, UI.CREAM)
