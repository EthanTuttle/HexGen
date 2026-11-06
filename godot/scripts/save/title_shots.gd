class_name TitleShots
extends Node
## Shots of the title with saves (`-- --front --titleshots --savesdir=saves_check`, after a --savecheck run), into
## screens/saving/: Continue and the last save's map, Load, and Delete's confirm. A test aid only.

var front: Front


func _ready() -> void:
	_run.call_deferred()


func _shot(name: String) -> void:
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	var dir := ProjectSettings.globalize_path("res://screens/saving")
	DirAccess.make_dir_recursive_absolute(dir)
	get_viewport().get_texture().get_image().save_png(dir.path_join("%s.png" % name))
	print("TITLE shot %s" % name)


func _run() -> void:
	await get_tree().create_timer(2.0).timeout
	await _shot("title_continue")
	front.title._open_load()
	await _shot("title_load")
	front.title._pops.open_confirm("Delete %s's saves?" % Saves.heroes()[0].name, "Delete", func(): pass, true)
	await _shot("title_delete")
	get_tree().quit()
