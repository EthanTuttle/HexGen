class_name LayoutMock
extends Node
## Shots of three ways to space the map's right-hand panels (`-- --layoutmock`), into screens/layout/: each rebuilds the
## clock and hand panels live, on a fresh run each time (`--option=a|b|c`). A test aid only; nothing here is the HUD.

var game: Game


func _ready() -> void:
	_run.call_deferred()


func _shot(name: String) -> void:
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	var dir := ProjectSettings.globalize_path("res://screens/layout")
	DirAccess.make_dir_recursive_absolute(dir)
	game.get_viewport().get_texture().get_image().save_png(dir.path_join("%s.png" % name))
	print("LAYOUT shot %s" % name)


func _run() -> void:
	await get_tree().create_timer(2.5).timeout
	var h := game.hud
	var w := get_viewport().get_visible_rect().size.x
	var tag := "%s_%d" % ["phone" if "--safe=both" in OS.get_cmdline_user_args() else "full", int(w)]
	await _shot("0_now_" + tag)
	var opt := "a"
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--option="):
			opt = a.get_slice("=", 1)
	match opt:
		"a":   # one line each, a shorter clock; the hand starts below it with a gap
			h._clock_title.autowrap_mode = TextServer.AUTOWRAP_OFF
			h._clock_sub.autowrap_mode = TextServer.AUTOWRAP_OFF
			h._clock_title.add_theme_font_size_override("font_size", 13)
			h._clock_sub.add_theme_font_size_override("font_size", 10)
			h._clock_title.custom_minimum_size.x = 0
			h._clock_sub.custom_minimum_size.x = 0
			h._clock_panel.custom_minimum_size.y = 58
			h._clock_panel.size.y = 58
			h._hand_panel.position.y = 12 + 58 + 10
			h._hand_panel.custom_minimum_size.y = 390 - 12 - 80
			h._hand_panel.size.y = 390 - 12 - 80
			await get_tree().process_frame
			var right := h._hand_panel.position.x + h._hand_panel.size.x   # both panels the clock's width, right edges lined up
			h._clock_panel.position.x = right - h._clock_panel.size.x
			h._hand_panel.position.x = right - h._clock_panel.size.x
			h._hand_panel.size.x = h._clock_panel.size.x
		"b":   # one column: the clock heads the hand panel, which runs the full height
			var p := h._clock_panel
			var box: HBoxContainer = p.get_child(0)
			p.remove_child(box)
			p.visible = false
			h._clock_title.autowrap_mode = TextServer.AUTOWRAP_OFF
			h._clock_sub.autowrap_mode = TextServer.AUTOWRAP_OFF
			h._clock_title.add_theme_font_size_override("font_size", 14)
			h._clock_sub.add_theme_font_size_override("font_size", 10)
			h._clock_title.custom_minimum_size.x = 0
			h._clock_sub.custom_minimum_size.x = 0
			var col: VBoxContainer = h._hand_panel.get_child(0)
			col.add_child(box)
			col.move_child(box, 0)
			var line := ColorRect.new()
			line.color = UI.CREAM_EDGE
			line.custom_minimum_size.y = 1.5
			col.add_child(line)
			col.move_child(line, 1)
			h._hand_panel.position.y = 12
			h._hand_panel.custom_minimum_size.y = 366
			h._hand_panel.size.y = 366
		"c":   # the clock as a pill at the top of the map, the hand panel the full height
			var p := h._clock_panel
			var box: HBoxContainer = p.get_child(0)
			var v: VBoxContainer = box.get_child(1)
			v.remove_child(h._clock_title)
			v.remove_child(h._clock_sub)
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 8)
			row.alignment = BoxContainer.ALIGNMENT_CENTER
			h._clock_title.autowrap_mode = TextServer.AUTOWRAP_OFF
			h._clock_sub.autowrap_mode = TextServer.AUTOWRAP_OFF
			h._clock_title.custom_minimum_size.x = 0
			h._clock_sub.custom_minimum_size.x = 0
			h._clock_title.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			h._clock_sub.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			row.add_child(h._clock_title)
			row.add_child(h._clock_sub)
			v.add_child(row)
			p.custom_minimum_size = Vector2(0, 0)
			p.size = Vector2.ZERO
			p.reset_size()
			await get_tree().process_frame
			p.position = Vector2((h._hand_panel.position.x - p.size.x) * 0.5 + 60, 12)
			h._hand_panel.position.y = 12
			h._hand_panel.custom_minimum_size.y = 366
			h._hand_panel.size.y = 366
	await _shot("%s_%s" % [opt, tag])
	get_tree().quit()
