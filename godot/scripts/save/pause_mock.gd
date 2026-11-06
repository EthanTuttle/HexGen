class_name PauseMock
extends Node
## Shots of the pause menu mockup (`-- --pausemock`), into screens/pause/, with stand-in save rows. A test aid only.

var game: Game
var pops := SavePopups.new()

const SLOTS := [{place = "Dunfaire Tower", time = "Today 9:40 pm"}, {place = "Ashen Fields", time = "Yesterday 8:12 pm"}, {}]
const HEROES := [
	{name = "[Hero name 1]", subtitle = "Human Fighter · Lv 3", time = "Today 9:52 pm", initial = "1", color = "#E9C46A"},
	{name = "[Hero name 2]", subtitle = "Wood Elf Ranger · Lv 2", time = "Nov 3, 7:05 pm", initial = "2", color = "#5E8F5A"},
	{name = "[Hero name 3]", subtitle = "Dwarf Fighter · Lv 1", time = "Nov 1, 6:30 pm", initial = "3", color = "#3E6F8C"},
]


func _ready() -> void:
	_run.call_deferred()


func _shot(name: String) -> void:
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	var dir := ProjectSettings.globalize_path("res://screens/pause")
	DirAccess.make_dir_recursive_absolute(dir)
	game.get_viewport().get_texture().get_image().save_png(dir.path_join("%s.png" % name))
	print("PAUSE shot %s" % name)


func _away_and_back(where: String, entry: Control) -> void:
	game.rig._player()
	game.rig.target += Vector3(6, 0, -4)
	await get_tree().create_timer(0.8).timeout
	await _shot("9_%s_panned_away" % where)
	var hex: HexShape = entry.find_children("*", "HexShape", true, false)[0]
	hex.pressed.emit()
	await get_tree().create_timer(1.0).timeout
	await _shot("10_%s_portrait_tapped" % where)


func _button(x: float, y: float) -> HexShape:
	var b := HexShape.make(40, 46, UI.CREAM, UI.CREAM, 0).with_icon(SavePopups.MENU_ICON, UI.INK, 18, 2.4).with_shadow(UI.HEX_SHADOW)
	UI.at(b, x, y)
	game.hud.add_child(b)
	return b


func _run() -> void:
	await get_tree().create_timer(2.5).timeout
	if "--recentre" in OS.get_cmdline_user_args():   # a portrait tap brings the camera back, on the map and in a fight
		await _away_and_back("map", game.hud._tray.get_child(0))
		game.debug_fight("plains_stones")
		while not (game.fight.active and game.fight.hud != null and game.fight.hud.visible):
			await get_tree().process_frame
		await get_tree().create_timer(2.0).timeout
		await _shot("11_combat_no_camera_column")
		await _away_and_back("combat", game.fight.hud._portraits.get_child(0))
		get_tree().quit()
		return
	if "--built" in OS.get_cmdline_user_args():   # the HUD's own button, and the menu it opens
		await _shot("7_built_cluster")
		game.hud._menu.pressed.emit()
		await _shot("8_built_menu")
		get_tree().quit()
		return
	var a := _button(22, 214)      # a: on top of the left column, over Quests
	await _shot("1a_button_left_column")
	a.queue_free()
	var b := _button(96, 12)       # b: beside the party tray
	await _shot("1b_button_by_tray")
	b.queue_free()
	_button(22, 214)
	game.ui.add_child(pops)
	var noop := func(): pass
	pops.open_menu([["Save", noop], ["Load", noop], ["Settings", noop], ["Quit to title", noop]])
	await _shot("2_menu")
	pops.open_save(SLOTS, func(_i): pass)
	await _shot("3_save")
	pops.open_confirm("Overwrite Slot 1?", "Overwrite", noop)
	await _shot("4_overwrite")
	var heroes := []
	for h: Dictionary in HEROES:
		var d := h.duplicate()
		d.autos = []
		for i in 10:
			d.autos.append({place = ["Dunfaire Tower", "Ashen Fields", "Plains"][i % 3], time = "Today %d:%02d pm" % [9 - i / 4, 52 - i * 4]})
		d.slots = SLOTS
		heroes.append(d)
	pops.open_load(heroes, 0, func(_h, _k, _i): pass, func(_h): pass)
	await _shot("5_load")
	pops.open_confirm("Delete [Hero name 1]'s saves?", "Delete", noop, true)
	await _shot("6_delete")
	get_tree().quit()
