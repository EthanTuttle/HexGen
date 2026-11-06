class_name PauseMenu
extends RefCounted
## The pause menu (design/06 -> Saving: Save, Load, Settings, Quit to title), opened from a map button. Save shows the 3 slots
## and asks before writing over a used one; Load is the title's Load; Settings isn't in the prototype yet. Quit to title
## autosaves first, and the day clock keeps running while it's open (Ethan, Nov 5, 2026; design/07 -> Menu replaces the nav
## button). Nothing on the map can be tapped meanwhile: the pop-ups' scrim takes every touch.

static func open(g: Game) -> SavePopups:
	var pops := SavePopups.new()
	g.ui.add_child(pops)
	pops.closed.connect(pops.queue_free)
	_menu(g, pops)
	return pops


static func _menu(g: Game, pops: SavePopups) -> void:
	pops.open_menu([
		["Save", func(): _save(g, pops)],
		["Load", func(): pops.show_load()],
		["Settings", func(): g.toast("Not in the prototype yet", false)],
		["Quit to title", func():
			Saves.autosave(g)
			Saves.flush()
			g.restart_run()],
	])


static func _save(g: Game, pops: SavePopups) -> void:
	var h: Array = Saves.heroes().filter(func(x): return x.id == Hero.current.id) if Hero.current else []
	var slots: Array = h[0].slots if not h.is_empty() else [{}, {}, {}]
	pops.open_save(slots, func(i: int):
		var write := func():
			Saves.save_slot(g, i)
			_save(g, pops)   # the row shows its new place and time
		if slots[i].is_empty():
			write.call()
		else:
			pops.open_confirm("Overwrite Slot %d?" % (i + 1), "Overwrite", write, false, func(): _save(g, pops)))
