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
