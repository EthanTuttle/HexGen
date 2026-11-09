class_name ActionCardsCheck
extends Node
## Checks the Action cards screen in a fight (`-- --cardscheck`, add `--shots` for screens/action_cards/): Edit hotbar opens it
## for whoever acts, taps and long-presses show details, drags place, move, swap and clear, the camera stays put, other
## members switch in, and Back hands the fight its new bar. Input goes in as touch does (emulated mouse events). Prints
## CARDS OK / CARDS FAIL lines, then CARDS DONE. A test aid only.

var game: Game
var shots := false
var failed := 0
var screen: ActionCards


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	print("CARDS %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _shot(name: String) -> void:
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	if shots:
		var dir := ProjectSettings.globalize_path("res://screens/action_cards")
		DirAccess.make_dir_recursive_absolute(dir)
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("%s.png" % name))


## A finger: press, optional moves, release, as the emulated mouse events a touch makes.
func _touch(at: Vector2, to := Vector2.INF, hold := 0.05) -> void:
	var vp := game.get_viewport()
	var k := vp.get_final_transform()   # layout units to window pixels
	var b := InputEventMouseButton.new()
	b.device = InputEvent.DEVICE_ID_EMULATION
	b.button_index = MOUSE_BUTTON_LEFT
	b.pressed = true
	b.position = k * at
	b.global_position = b.position
	Input.parse_input_event(b)
	await get_tree().process_frame
	var end := at
	if to != Vector2.INF:
		for i in range(1, 13):
			var mm := InputEventMouseMotion.new()
			mm.device = InputEvent.DEVICE_ID_EMULATION
			mm.button_mask = MOUSE_BUTTON_MASK_LEFT
			mm.position = k * at.lerp(to, i / 12.0)
			mm.global_position = mm.position
			Input.parse_input_event(mm)
			await get_tree().process_frame
		end = to
	await _wait(hold)
	var u := b.duplicate() as InputEventMouseButton
	u.pressed = false
	u.position = k * end
	u.global_position = u.position
	Input.parse_input_event(u)
	await get_tree().process_frame
	await get_tree().process_frame


func _centre(c: Control) -> Vector2:
	return c.get_global_rect().get_center()


func _tile(id: String) -> Control:
	for t in screen.find_children("*", "", true, false):
		if t.get("id") == id and t.has_method("_draw") and t.get("slot") != null:
			return t
	return null


func _details_text() -> String:
	var out := []
	for l in screen._details.find_children("*", "Label", true, false):
		out.append((l as Label).text)
	return " ".join(out)


func _run() -> void:
	await _wait(1.0)
	game.debug_fight("plains_stones")
	while not (game.fight.active and game.fight.phase == "allies" and not game.fight.busy):
		await get_tree().process_frame
	await _wait(0.5)
	var f := game.fight
	var hud := f.hud
	var hero: Dictionary = f.current
	var m: Dictionary = hero.member
	m.hot.erase("use_item")   # off the bar, as on a full one: a level-1 Fighter's bar has room since the level-3 cards moved (Nov 9, 2026)
	var before: Array = m.hot.duplicate()
	print("CARDS bar at the start: %s" % [before])

	# Edit hotbar, through All actions as a player gets there
	hud._all.visible = true
	hud._refresh_all()
	await get_tree().process_frame
	var edit: Control = hud._all.find_children("*", "TagButton", true, false).filter(func(b): return b.text == "Edit hotbar")[0]
	await _touch(_centre(edit))
	await _wait(0.2)
	var found := game.ui.get_children().filter(func(c): return c is ActionCards)
	_check(found.size() == 1, "Edit hotbar opens the Action cards screen")
	if found.is_empty():
		print("CARDS DONE: %d failed" % (failed + 1))
		return
	screen = found[0]
	_check(not hud._all.visible, "All actions closes behind it")
	_check(screen.member() == m, "it opens on whoever acts (%s)" % m.name)
	_check(screen._name.text == m.name and screen._sub.text != "", "top bar: %s, %s" % [screen._name.text, screen._sub.text])
	await _shot("from_combat")

	# Fits: nothing past the safe area, the tray's slots inside the tray, the details' contents inside the panel
	var safe := screen._root.get_global_rect()
	for c: Control in [screen._top, screen._list_panel, screen._tray, screen._details_panel]:
		_check(safe.encloses(c.get_global_rect()), "%s inside the safe area" % c.get_class())
	var tray := screen._tray.get_global_rect()
	_check(screen._slots.all(func(s): return tray.encloses(s.get_global_rect())), "%d slots inside the tray" % screen._slots.size())

	# Every card's details fit the 170 pt panel at 11 pt or more (design/07), Breath Weapon for every dragon type
	var panel := screen._details_panel
	var room := panel.size.y - 24.0
	var worst := ["", 0.0]
	var sub_was: String = m.get("sub", "")
	var subs: Array = [""] + CreatorData.DRI.keys()
	for id: String in Cards.ALL:
		for sub: String in (subs if id == "breath" else [""]):
			m.sub = sub
			screen.select(id)
			await get_tree().process_frame
			var need: float = screen._details.get_combined_minimum_size().y
			var wide: float = screen._details.get_combined_minimum_size().x
			if need > worst[1]:
				worst = [id + (" " + sub if sub != "" else ""), need]
			var small := screen._details.find_children("*", "Label", true, false).filter(func(l): return l.get_theme_font_size("font_size") < 11)
			if need > room or wide > panel.size.x - 24.0 or not small.is_empty():
				_check(false, "%s %s fits: %.0f of %.0f tall, %.0f wide" % [id, sub, need, room, wide])
	m.sub = sub_was
	_check(worst[1] <= room, "every card's details fit the %.0f pt panel (tallest: %s, %.0f of %.0f)" % [panel.size.x, worst[0], worst[1], room])
	var tallest: PackedStringArray = String(worst[0]).split(" ")
	m.sub = tallest[1] if tallest.size() > 1 else sub_was
	screen.select(tallest[0])   # shown even if this member doesn't have it
	await _shot("details_longest")
	m.sub = sub_was
	screen.select("attack")
	for _f in 2:
		await get_tree().process_frame

	var rig := game.rig
	var cam_at: Vector3 = rig.target

	# Shield users: Block with the Weapon cards and no Defend in Basic (04 -> Shields; from the member's cards, Rules.PARTY)
	var guard := "block" if "block" in m.cards else "defend"
	_check(screen.section_of("block") == "weapon" and (guard == "defend" or not "defend" in m.cards), "%s: %s%s" % [m.name, "Block in Weapon, no Defend" if guard == "block" else "Defend in Basic", ""])

	# Tap: details
	await _touch(_centre(_tile(guard)))
	_check(screen.sel == guard, "a tap shows the card's details")
	_check("Once per turn" in _details_text() and not "Attack Flip" in _details_text(), "%s: once per turn, no flip line (%s)" % [guard, _details_text()])
	await _touch(_centre(_tile("attack")))
	_check("Repeatable" in _details_text() and "Attack Flip: " + String(m.ability) in _details_text(), "Attack: repeatable, attack flip on %s" % m.ability)
	await _shot("details_attack")

	# Long-press: details while still held, and the release does nothing more
	# A swipe up in the list scrolls it (PLACEHOLDER rule), and picks nothing
	var t := _tile("second_wind")
	var sel_was := screen.sel
	var bar_was: Array = screen.slots().duplicate()
	var sc := screen._scroll
	var hidden := not sc.get_global_rect().has_point(_centre(t))
	for _i in 3:   # swipes that stay inside the list, from a card near its foot
		var r := sc.get_global_rect()
		var from_card: Control = null
		for c in screen._list.find_children("*", "", true, false):
			if c.get("slot") != null and c.get("id") != null and r.has_point(_centre(c)) and _centre(c).y > r.position.y + r.size.y * 0.5:
				from_card = c
		if from_card:
			var p := _centre(from_card)
			await _touch(p, Vector2(p.x, maxf(r.position.y + 4, p.y - 80)))
	_check(sc.scroll_vertical > 0 and screen.sel == sel_was and screen.slots() == bar_was, "a swipe up scrolls the list (to %d) and picks nothing" % sc.scroll_vertical)
	_check(sc.get_global_rect().has_point(_centre(_tile("second_wind"))) or not hidden, "Second Wind comes into view")
	t = _tile("second_wind")
	await _touch(_centre(t), Vector2.INF, 0.6)
	_check(screen.sel == "second_wind", "a long-press shows the card's details")
	_check("Once per fight" in _details_text(), "Second Wind: once per fight")
	await _shot("scrolled_longpress")
	sc.scroll_vertical = 0
	await get_tree().process_frame

	# Drag a card from the list onto a slot that holds another
	# (Use item: off the starting bar for everyone, as slots fill before it)
	var s3 := screen.slots()[2] as String
	await _touch(_centre(_tile("use_item")), _centre(screen._slots[2]))
	_check(screen.slots()[2] == "use_item", "a dragged card lands in its slot")
	_check(not s3 in m.hot or s3 == "use_item", "the card it replaced leaves the bar (%s)" % s3)
	_check(f.current.hot == m.hot and f.current.hot.has("use_item"), "the fight's unit sees the new bar")
	await _shot("after_drag")

	# A card already on the bar dragged from the list to another slot moves (swapping with what was there)
	var at0 := screen.slots().find("use_item")
	var s5 := screen.slots()[4] as String
	await _touch(_centre(_tile("use_item")), _centre(screen._slots[4]))
	_check(screen.slots()[4] == "use_item" and screen.slots()[at0] == s5, "a card on the bar moves, swapping (%s to slot %d)" % [s5, at0 + 1])

	# Slot to slot swaps
	var a := screen.slots()[0] as String
	var b := screen.slots()[1] as String
	await _touch(_centre(screen._slots[0]), _centre(screen._slots[1]))
	_check(screen.slots()[0] == b and screen.slots()[1] == a, "slot to slot swaps")

	# Off the tray clears
	var last := screen.slots()[6] as String
	await _touch(_centre(screen._slots[6]), _centre(screen._list_panel))
	_check(screen.slots()[6] == "" and not last in m.hot, "dragged off the tray clears the slot (%s)" % last)
	_check(m.hot.size() == screen.slots().filter(func(x): return x != "").size(), "combat's bar is the slots without the gaps")
	await _shot("cleared")

	# From the list, dropped outside any slot: nothing changes
	var was: Array = screen.slots().duplicate()
	await _touch(_centre(_tile("move")), _centre(screen._details_panel))
	_check(screen.slots() == was, "a list card dropped off the tray changes nothing")

	_check(rig.target.distance_to(cam_at) < 0.01, "the camera stays put under the screen")

	# The tabs: Set 1 picked, Set 2 dimmed with "No weapon", and a tap on it does nothing (Ethan, Nov 5, 2026)
	var tab2: Control = screen._tabs.get_child(1)
	_check(screen._tabs.get_child_count() == 2 and tab2.dim and tab2.gear == "No weapon", "Set 2's tab is dimmed, \"No weapon\"")
	var bar_before: Array = screen.slots().duplicate()
	await _touch(_centre(tab2))
	_check(screen.slots() == bar_before and tab2.dim, "a tap on Set 2 does nothing")
	_check(screen._slots.all(func(sl): return sl.get_child_count() == 1), "no number badges on the slots")

	# Another member
	if game.party.size() > 1:
		var other: Control = screen._party.get_child(1)
		await _touch(_centre(other))
		_check(screen.ci == 1 and screen._name.text == game.party[1].name, "the party switches to %s (%s)" % [game.party[1].name, screen._sub.text])
		await _shot("other_member")
		await _touch(_centre(screen._party.get_child(0)))

	# A middle slot cleared, so the fight's bar should keep the gap
	await _touch(_centre(screen._slots[2]), _centre(screen._list_panel))
	_check(screen.slots()[2] == "", "slot 3 cleared")
	var expect: Array = screen.slots().duplicate()

	# Back: the fight draws the new bar, gaps where the slots are empty (combat reads `hot_slots`)
	var back: Control = screen._top.get_child(0)
	await _touch(_centre(back))
	await _wait(0.2)
	_check(not is_instance_valid(screen) or not screen.is_inside_tree(), "Back closes the screen")
	var drawn := hud._hotbar.get_children()
	var shown := drawn.map(func(c): return "" if not c.has_method("setup") else String(c.k.id))
	_check(drawn.size() == Rules.HOTBAR_SLOTS, "back in the fight, the bar has %d places" % drawn.size())
	_check(shown == expect, "each card in its slot, gaps kept (%s)" % [shown])
	await _shot("back_in_fight")
	print("CARDS bar at the end: %s" % [m.hot])
	print("CARDS DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()
