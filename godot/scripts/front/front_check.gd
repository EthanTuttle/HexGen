class_name FrontCheck
extends Node
## A scripted run of the screens before the game, by touch (`-- --front --check`, add `--shots` to save
## screens/front_*.png). Prints `FRONT OK` / `FRONT FAIL` for each check and quits. A test aid, not game UI.

var front: Front
var failed := 0


func _ready() -> void:
	_run.call_deferred()


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


## Injected events are in window pixels; everything here works in the layout's units (as TouchTest).
func _touch(pos: Vector2, pressed: bool) -> void:
	var e := InputEventScreenTouch.new()
	e.index = 0
	e.position = pos * Vector2(DisplayServer.window_get_size()) / get_viewport().get_visible_rect().size
	e.pressed = pressed
	Input.parse_input_event(e)
	await get_tree().process_frame


func tap(pos: Vector2) -> void:
	await _touch(pos, true)
	await _wait(0.08)
	await _touch(pos, false)
	await _wait(0.15)


## The centre of the first visible control whose accessibility name is `what`.
func control(what: String, root: Node = null) -> Control:
	for c in (root if root else get_tree().root).get_children():
		if c is Control and c.is_visible_in_tree() and (c as Control).accessibility_name == what:
			return c
		var found := control(what, c)
		if found:
			return found
	return null


func tap_on(what: String) -> bool:
	var c := control(what)
	if c == null:
		check(false, "found %s" % what)
		return false
	await tap(c.get_global_rect().get_center())
	return true


func check(ok: bool, what: String) -> void:
	print("FRONT %s %s" % ["OK  " if ok else "FAIL", what])
	if not ok:
		failed += 1


func shot(name: String) -> void:
	if not "--shots" in OS.get_cmdline_user_args():
		return
	await RenderingServer.frame_post_draw
	var dir := ProjectSettings.globalize_path("res://screens")
	get_viewport().get_texture().get_image().save_png(dir.path_join("front_%s.png" % name))


## Every visible label at 11 pt or more (DOCS: Minimum text size on phones).
func text_sizes(where: String, root: Node) -> void:
	var small: Array[String] = []
	var walk := func(n: Node, self_fn: Callable) -> void:
		if n is Label and n.is_visible_in_tree() and (n as Label).text != "":
			if n.get_theme_font_size("font_size") < 11:
				small.append((n as Label).text)
		for c in n.get_children():
			self_fn.call(c, self_fn)
	walk.call(root, walk)
	check(small.is_empty(), "%s: no text under 11 pt %s" % [where, small if not small.is_empty() else ""])


func _run() -> void:
	await _wait(1.6)
	await _title()
	await _creator()
	print("FRONT DONE: %d failed" % failed)
	get_tree().quit(1 if failed > 0 else 0)


func _title() -> void:
	check(control("New campaign") != null, "title: New campaign shows")
	check(control("Continue") == null, "title: no Continue without a save")
	check(control("Load") == null, "title: no Load without a save")
	var fps_from := Engine.get_frames_drawn()
	var t0 := Time.get_ticks_msec()
	await _wait(1.0)
	print("FRONT title frames: %.0f fps" % ((Engine.get_frames_drawn() - fps_from) * 1000.0 / (Time.get_ticks_msec() - t0)))
	await shot("title")
	await tap_on("Settings")
	await _wait(0.2)
	check(front.title._toast != null, "title: Settings says it isn't in yet")
	await shot("title_toast")
	await _wait(1.5)
	text_sizes("title", front.title)


func _creator() -> void:
	await tap_on("New campaign")
	await _wait(0.3)
	var c: Creator = front.creator
	check(c != null, "New campaign opens the creator")
	check(control("Back") != null and (control("Back") as TagButton).disabled, "class: Back is off on the first step")
	await shot("class_none")
	text_sizes("class", c)
	# Every class can be read; only the Fighter goes on.
	await tap_on("Wizard")
	await _wait(0.6)
	check(c.cls == "Wizard" and not c.done("class"), "class: Wizard opens to read and stays locked")
	await shot("class_locked")
	await tap_on("Fighter")
	await _wait(0.6)
	check(c.done("class"), "class: the Fighter is playable")
	await shot("class_fighter")
	await tap_on("Second Wind")
	await _wait(0.15)
	await shot("class_card_popup")
	await tap_on("Next")
	await _wait(0.3)
	await shot("race_none")
	# The longest race for the row of sub-types and a card, then the race the run goes on with.
	await tap_on("Dragonborn")
	await _wait(0.6)
	await tap_on("Blue")
	await _wait(0.5)
	await shot("race_dragonborn")
	text_sizes("race", c)
	await tap_on("Elf")
	await _wait(0.6)
	await tap_on("High elf")
	await _wait(0.5)
	check(not c.done("race"), "race: a high elf needs a spell")
	await tap_on("Lull")
	await _wait(0.4)
	check(c.done("race"), "race: picking the spell finishes it")
	await shot("race_high_elf")
	await tap_on("Dwarf")
	await _wait(0.6)
	await tap_on("Shield dwarf")
	await _wait(0.5)
	await shot("race_dwarf")
	await tap_on("Next")
	await _wait(0.3)
	await shot("background_none")
	await tap_on("Sage")
	await _wait(0.6)
	await shot("background_sage")
	text_sizes("background", c)
	await tap_on("Folk Hero")
	await _wait(0.6)
	await shot("background_folk_hero")
	await tap_on("Next")
	await _wait(0.4)
	# Scores: a third race +1 pushes the oldest off.
	for what in ["Race +1 CON", "Race +1 STR", "Race +1 WIS", "Class +1 DEX"]:
		await tap_on(what)
		await _wait(0.05)
	check(c.rb == ["STR", "WIS"], "scores: a third race pick swaps out the oldest")
	check(c.scores()["DEX"] == 2 and c.scores()["STR"] == 2 and c.done("scores"), "scores: the picks add coins")
	await _wait(0.35)
	await shot("scores")
	text_sizes("scores", c)
	await tap_on("Next")
	await _wait(0.4)
	await tap_on("Choose Animal")
	await _wait(0.05)
	await tap_on("cls:Athletics")
	await _wait(0.05)
	await tap_on("Choose Athletics")
	await _wait(0.35)
	check(c.done("skills"), "skills: one pick from each list")
	await shot("skills")
	text_sizes("skills", c)
	await tap_on("Next")
	await _wait(0.3)
	check(control("Greatsword") != null, "gear: the Fighter gets every weapon")
	await shot("gear_main")
	text_sizes("gear", c)
	await tap_on("Greatsword")
	await _wait(0.05)
	await tap_on("Choose Greatsword")
	await _wait(0.2)
	await shot("gear_flying")
	await _wait(0.6)
	check(c.off_options().is_empty(), "gear: a two-handed weapon crosses out the offhand")
	await shot("gear_two_handed")
	await tap_on("Longsword")
	await _wait(0.05)
	await tap_on("Choose Longsword")
	await _wait(0.6)
	await tap_on("Next: Offhand")
	await _wait(0.1)
	await tap_on("Shield")
	await _wait(0.05)
	await tap_on("Choose Shield")
	await _wait(0.6)
	await shot("gear_offhand")
	await tap_on("Next: Armour")
	await _wait(0.1)
	await tap_on("Medium armour")
	await _wait(0.05)
	await tap_on("Choose Medium armour")
	await _wait(0.6)
	check(c.done("gear"), "gear: all three slots filled")
	await tap_on("Next")
	await _wait(1.1)
	check((control("Next") as TagButton).disabled, "look: Next waits for pronouns")
	await shot("look")
	text_sizes("look", c)
	await tap_on("They")
	await _wait(0.05)
	await tap_on("Broad")
	await _wait(0.05)
	await tap_on("Hairstyle 3")
	await _wait(0.05)
	await tap_on("Hair 4")
	await _wait(0.05)
	await tap_on("Cloth 2")
	await _wait(0.05)
	await tap_on("Turn right")
	await _wait(0.1)
	await shot("look_picked")
	await tap_on("Next")
	await _wait(0.9)
	check((control("Begin") as TagButton).disabled, "name: Begin waits for a name")
	var edit := front.creator.find_children("*", "LineEdit", true, false)[0] as LineEdit
	edit.text = "Hilde Oakshield"
	edit.text_changed.emit(edit.text)
	await _wait(0.1)
	check(not (control("Begin") as TagButton).disabled, "name: a typed name lets Begin on")
	await shot("name")
	text_sizes("name", front.creator)
	await tap_on("Begin")
	await _wait(0.6)
	await shot("send_off_rising")
	await _wait(1.0)
	check(Hero.current.get("name") == "Hilde Oakshield", "Begin hands the description to the game")
	check(Hero.current.get("race_name") == "Shield dwarf" and Hero.current.get("start_place") == "The Oak & Lantern", "the description names race and place")
	print("FRONT hero: ", Hero.current)
	await _wait(1.6)
	await shot("send_off_banner")
