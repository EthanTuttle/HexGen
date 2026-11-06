class_name CreatorTapCheck
extends Node
## Ethan's creator notes from the phone (Nov 5, 2026), by emulated touch (`-- --front --creatortaps --safe=both`): a tap on a
## banner's card (its pop-up) or on a Skills row mustn't fade anything in again (the flash), a Skills tap keeps the list
## where it was, the step pips sit evenly, and a drag on the Look step spins the mini. Prints CTAP OK / CTAP FAIL lines,
## then CTAP DONE, and saves screens/creator_taps/*.png. A test aid only.

var front: Front
var failed := 0


func _ready() -> void:
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	print("CTAP %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _frames(n: int) -> void:
	for _k in n:
		await get_tree().process_frame


func _shot(name: String) -> void:
	await _frames(3)
	var dir := ProjectSettings.globalize_path("res://screens/creator_taps")
	DirAccess.make_dir_recursive_absolute(dir)
	get_viewport().get_texture().get_image().save_png(dir.path_join("%s.png" % name))


## A finger, as the emulated mouse events a touch makes: press, optional moves, release.
func _touch(at: Vector2, to := Vector2.INF) -> void:
	var k := get_viewport().get_final_transform()
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
		for i in range(1, 16):
			var mm := InputEventMouseMotion.new()
			mm.device = InputEvent.DEVICE_ID_EMULATION
			mm.button_mask = MOUSE_BUTTON_MASK_LEFT
			mm.position = k * at.lerp(to, i / 15.0)
			mm.global_position = mm.position
			mm.relative = k.basis_xform((to - at) / 15.0)
			Input.parse_input_event(mm)
			await get_tree().process_frame
		end = to
	var r := b.duplicate() as InputEventMouseButton
	r.pressed = false
	r.position = k * end
	r.global_position = r.position
	Input.parse_input_event(r)
	await get_tree().process_frame


## Controls in the creator whose transparency changes from one frame to the next, over n frames: what a flash is.
func _fading(n: int) -> int:
	var seen := {}
	var moving := 0
	for _k in n:
		await get_tree().process_frame
		for x in front.creator.find_children("*", "CanvasItem", true, false):
			var a: float = (x as CanvasItem).modulate.a
			var id := x.get_instance_id()
			if seen.has(id) and not is_equal_approx(seen[id], a):
				moving += 1
			seen[id] = a
	return moving


func _named(prefix: String) -> Control:
	for x in front.creator.find_children("*", "Control", true, false):
		var c := x as Control
		if c.is_visible_in_tree() and c.accessibility_name.begins_with(prefix):
			return c
	return null


func _run() -> void:
	await get_tree().create_timer(1.0).timeout
	front.open_creator()
	var c := front.creator
	await _frames(10)
	# 3. Even pips: the same distance between every pip's centre.
	var pips: Array = []
	for name: String in ["Class", "Race", "Background", "Scores", "Skills", "Gear", "Look", "Name"]:
		var p := _named(name)
		if p:
			pips.append(p.get_global_rect().get_center().x)
	var gaps: Array = range(1, pips.size()).map(func(i): return pips[i] - pips[i - 1])
	_check(pips.size() == 8 and gaps.max() - gaps.min() < 1.0, "the step pips sit evenly: gaps %s" % [gaps.map(func(g): return snappedf(g, 0.1))])
	await _shot("pips")
	# 1. A tap on a banner's card opens its pop-up without fading anything in again.
	c.cls = "Fighter"
	c.go("race")
	await get_tree().create_timer(1.0).timeout
	c.race = "Halfling"
	c.render()
	await get_tree().create_timer(1.2).timeout
	var card := _named("Lucky")
	_check(card != null, "the halfling's Lucky card shows on its banner")
	if card:
		await _touch(card.get_global_rect().get_center())
		var moving := await _fading(20)
		_check(moving == 0, "tapping a banner's card opens its pop-up with nothing fading in again (%d changes)" % moving)
		await _shot("card_popup")
	# 5. A race with sub-types, none picked yet: the to-do dot shows what's missing, and Next waits (phone note 071055).
	c.race = "Elf"
	c.sub = ""
	c.render()
	await get_tree().create_timer(1.2).timeout
	_check(not c.done("race"), "an elf with no sub-type picked isn't done yet")
	await _shot("race_elf_no_sub")
	c.sub = "Wood elf"
	c.render()
	await get_tree().create_timer(0.8).timeout
	await _shot("race_elf_sub_picked")
	# 2. A tap on a Skills row keeps the list where it was and fades nothing.
	c.bg = "Soldier"
	c.go("skills")
	await get_tree().create_timer(1.0).timeout
	var scroll: ScrollContainer = c.find_children("*", "ScrollContainer", true, false)[0]
	scroll.scroll_vertical = 120
	await _frames(3)
	var before := scroll.scroll_vertical
	var rows := c.find_children("*", "Control", true, false).filter(func(t): return t is CUI.Tap and ":" in (t as Control).accessibility_name and (t as Control).is_visible_in_tree())
	var target: Control = rows[-1] if not rows.is_empty() else null
	for r: Control in rows:   # the lowest row that's fully in view
		if scroll.get_global_rect().encloses(r.get_global_rect()):
			target = r
	if target:
		await _touch(target.get_global_rect().get_center())
		var moving := await _fading(20)
		var now: ScrollContainer = c.find_children("*", "ScrollContainer", true, false)[0]
		_check(before > 0 and now.scroll_vertical == before, "a Skills tap keeps the list's place (%d, then %d)" % [before, now.scroll_vertical])
		_check(moving == 0, "a Skills tap fades nothing in again (%d changes)" % moving)
		await _shot("skills_after_tap")
	# 4. A drag across the Look step's mini spins it.
	c.go("look")
	await get_tree().create_timer(1.5).timeout
	var mini: Control = c.find_children("*", "HeroView", true, false)[0]
	var yaw0: float = mini.yaw
	var mid := mini.get_global_rect().get_center()
	await _touch(mid - Vector2(40, 0), mid + Vector2(60, 0))
	await _frames(5)
	_check(absf(mini.yaw - yaw0) > 0.3, "a drag across the mini spins it (%.2f to %.2f rad)" % [yaw0, mini.yaw])
	await _shot("look_spun")
	print("CTAP DONE: %d failed" % failed)
	get_tree().quit()
