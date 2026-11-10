class_name SaveCheck
extends Node
## Checks saving (`-- --savecheck`, design/06 -> Saving), in user://saves_check so real saves are never touched. A real
## first-playable run (a creator hero, 2 in the party) is played by PlayCheck's moves; at several points it's saved to a slot,
## read back from disk, loaded into a fresh game scene and saved again, and the two must match field by field. The rebuilt map
## (gates, streets, cliffs, water, canyon mazes, slots) must match too, which catches state wrongly counted as rebuildable.
## Then the debug map with every variant, a grown canyon and raised region, the autosave ring, slots, a broken and a too-new file, two heroes of one name, delete,
## and every variable of Game, MapBoard and PartyWalker sorted into SaveGame's lists. Prints SAVE OK / SAVE FAIL lines and save
## timings, then SAVE DONE. Lives on the root, so it outlives each load. A test aid only.

const CHECK_DIR := "user://saves_check"
const POINTS := [6, 18, 40, 80]   # PlayCheck moves before each round trip

static var instance: SaveCheck

var game: Game
var failed := 0
var driver: Driver
var timings := []


## PlayCheck's moves without its own run, so this check decides when to stop and save.
class Driver extends PlayCheck:
	func _ready() -> void:
		game.debug_auto_cross = true
		game.event_screen = Callable()


## A hero as the creator makes one (its defaults, a Human Fighter with a longsword and shield), so the mini builds.
static func test_hero(hero_name: String) -> Hero:
	var c := Creator.new()
	c.race = "Human"
	c.cls = "Fighter"
	c.bg = "Soldier"
	c.hero_name = hero_name
	c.main = "longsword"
	c.off = "shield"
	c.arm = "armoured"
	var h := c.hero()
	h.scores = {"STR": 3, "CON": 2, "DEX": 1}
	c.free()
	return h


static func attach(g: Game) -> void:
	if instance != null:
		return
	instance = SaveCheck.new()
	instance.game = g
	g.get_tree().root.add_child.call_deferred(instance)


func _ready() -> void:
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("SAVE %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _frames(n: int) -> void:
	for _k in n:
		await get_tree().process_frame


## Waits for the game scene that's opening, its _ready and the deferred load done.
func _new_game() -> void:
	var old := game
	while not (get_tree().current_scene is Game and get_tree().current_scene != old):
		await get_tree().process_frame
	game = get_tree().current_scene
	await _frames(4)


func _run() -> void:
	Saves.dir = CHECK_DIR
	Saves.wipe_check_dir(CHECK_DIR)
	_check_lists()
	Hero.current = test_hero("Check")
	get_tree().change_scene_to_file(Saves.GAME_SCENE)
	await _new_game()
	_check(game.party.size() == 2 and not game.run.wide_deck, "a real first-playable run: the hero and Fluffy, seed %s" % game.run.seed_text)
	await _time("start", game)
	await _save_from_menu()
	var moves := 0
	for target: int in POINTS:
		await _play(target - moves)
		moves = target
		await _round_trip("after %d moves (%d tiles, %d regions, party %d, level %d)" % [moves, game.map.terrains.size(), game.regions.size(), game.party.size(), game.level])
	await _time("mid", game)
	await _ring_and_slots()
	await _debug_map()
	_files()
	print("SAVE timings: %s" % [timings])
	print("SAVE DONE: %d failed" % failed)
	get_tree().quit()


## The pause menu's Save on a new hero, whose 3 slots are all empty: tapping Slot 1 writes it (the phone playtest, Nov 8:
## empty slots were pale and took no taps, so nothing could be saved by hand).
func _save_from_menu() -> void:
	var pops := PauseMenu.open(game)
	await _frames(2)
	var save_button: Control = pops.find_children("*", "TagButton", true, false).filter(func(b): return b.accessibility_name == "Save")[0]
	save_button.pressed.emit()
	await _frames(2)
	var rows := pops.find_children("*", "PanelContainer", true, false).filter(func(r): return r.has_signal("tapped") \
			and r.find_children("*", "Label", true, false).any(func(l): return l.text == "Slot 1"))
	_check(rows.size() == 1, "the Save pop-up lists Slot 1")
	if rows.size() == 1:
		var row: Control = rows[0]
		for down in [true, false]:
			var e := InputEventMouseButton.new()
			e.button_index = MOUSE_BUTTON_LEFT
			e.pressed = down
			e.position = row.size / 2.0
			row._gui_input(e)
		await _frames(2)
		var h: Dictionary = Saves.read_index().heroes.get(Hero.current.id, {slots = [{}]})
		_check(not h.slots[0].is_empty(), "tapping an empty Slot 1 in the pause menu saves to it")
	pops.close()
	await _frames(2)


## n of PlayCheck's moves (place, fight, rest, answer pop-ups), from whatever state the game is in.
func _play(n: int) -> void:
	Engine.time_scale = 4.0
	driver = Driver.new()
	driver.game = game
	game.add_child(driver)
	for _k in n:
		await driver._settle()
		if game._ended:
			break
		if game.hud.encounter_open():
			await driver._answer()
			continue
		if await driver._rest_if_hurt():
			continue
		if not await driver._place_one():
			await driver._go_to_a_fight()
	await driver._settle()
	driver.queue_free()


## Saves to slot 1, reads it back from disk, loads it, and compares a second capture and the rebuilt map with the first.
func _round_trip(what: String) -> void:
	var m := game.map
	print("SAVE %s holds: %d water gates, %d Troll Bridges, %d raised regions, %d canyon tiles, %d encounters (%d left by a wipe), %d trails" % [what,
			m.water_gates.size(), m._troll_water.size(), m.raised_regions.size(), m.canyons.size(), game.encounters.size(),
			game.encounters.values().filter(func(e): return e.persistent).size(), m.flow_dist.size()])
	Saves.save_slot(game, 0)
	Saves.flush()
	timings.append([what.get_slice(" (", 0), game.map.terrains.size(), Saves.last_ms, Saves.last_bytes])
	var a := SaveGame.capture(game)
	var da := _rebuilt(game)
	var data := Saves.read(Hero.current.id, "slot_1")
	_check(not data.is_empty(), "%s: slot 1 reads back" % what)
	_check(_same(_strip(SaveGame.capture(game)), _strip(data)), "%s: the file holds what the game holds" % what)
	Engine.time_scale = 0.0   # no clock, spawn rolls or roaming between the load and the second capture
	Saves.play(get_tree(), data)
	await _new_game()
	var b := SaveGame.capture(game)
	var db := _rebuilt(game)
	_compare(_strip(a), _strip(b), what)
	for k: String in da:
		_check(_same(da[k], db[k]), "%s: rebuilt %s match" % [what, k])
	var ea: Array = a.encounters.map(func(e): return e.expires_in)
	var eb: Array = b.encounters.map(func(e): return e.expires_in)
	_check(ea.size() == eb.size() and range(ea.size()).all(func(i): return absf(ea[i] - eb[i]) < 5.0), "%s: encounters keep their time left" % what)
	_check(game.hud.encounter_open() == game.encounters.has(game.party_tile), "%s: an encounter's pop-up shows again on its hex" % what)
	_check(game.level_pick.visible == (game._picks > 0), "%s: owed level picks open again" % what)
	var done: bool = game.run.goal_regions > 0 and game.regions.size() >= game.run.goal_regions
	_check(game.end_panel.visible == done, "%s: a finished run opens on its end panel%s" % [what, "" if done else " (not finished)"])
	Engine.time_scale = 4.0
	await _frames(3)


## What a save can't hold exactly: when it was made, and the encounters' seconds left (checked with a margin).
func _strip(d: Dictionary) -> Dictionary:
	var c := d.duplicate(true)
	c.erase("saved_at")
	for e: Dictionary in c.encounters:
		e.erase("expires_in")
	c.game.erase("ended")   # the end panel opens again by itself
	return c


func _compare(a: Dictionary, b: Dictionary, what: String) -> void:
	for k: String in a:
		if k == "map":
			for mk: String in a.map:
				_check(_same(a.map[mk], b.map[mk]), "%s: map %s match" % [what, mk])
		else:
			_check(_same(a[k], b[k]), "%s: %s match" % [what, k])
			if not _same(a[k], b[k]):
				print("SAVE   was %s\nSAVE   now %s" % [var_to_str(_norm(a[k])).left(600), var_to_str(_norm(b[k])).left(600)])


## The map's rebuilt parts, to hold against a loaded game's.
func _rebuilt(g: Game) -> Dictionary:
	var m := g.map
	var mazes := {}
	for t: Vector2i in m.canyons:
		mazes[t] = [m.canyons[t].openset, m.canyons[t].entrances]
	return {gates = m.gates, streets = m.streets, climbs = m.climbs, raised = m.raised, water = m.water_shapes.keys(),
		slots = m.slot_nodes.keys(), canyon_mazes = mazes, visit = m.terrains.keys().filter(func(t): return m.can_visit(t)),
		reach = m._reach().keys()}


func _same(a, b) -> bool:
	return var_to_str(_norm(a)) == var_to_str(_norm(b))


## Order-free and type-free: dictionaries as key-sorted pairs, arrays of any type as plain arrays, numbers to 6 places.
func _norm(v):
	if v is Dictionary:
		var keys: Array = v.keys()
		keys.sort_custom(func(x, y): return var_to_str(x) < var_to_str(y))
		return keys.map(func(k): return [_norm(k), _norm(v[k])])
	if v is Array:
		var out := []
		for x in v:
			out.append(_norm(x))
		return out
	if v is float:   # JSON.from_native writes 15 digits, so the last one or two of a double can differ
		return int(v) if is_equal_approx(v, roundf(v)) and absf(v) < 1e15 else snappedf(v, 1e-6)
	return v


## Every variable of Game, MapBoard and PartyWalker is in SaveGame's SAVED or REBUILT, so one Builder adds gets noticed.
func _check_lists() -> void:
	for pair in [[Game, "Game"], [MapBoard, "MapBoard"], [PartyWalker, "PartyWalker"]]:
		var left := SaveGame.unlisted(pair[0], pair[1])
		_check(left.is_empty(), "every %s variable is saved or rebuilt%s" % [pair[1], "" if left.is_empty() else ": not listed %s" % [left]])


## Times a save of the map as it stands: capture, encode and write, the file's size, and the frame it takes.
func _time(label: String, g: Game) -> void:
	var worst := 0.0
	for _k in 3:
		Saves.save_slot(g, 2)
		Saves.flush()
		worst = maxf(worst, Saves.last_ms.main)
	print("SAVE time %s, %d tiles: %s ms, %d KB; slowest on the frame of 3: %.2f ms" % [label, g.map.terrains.size(), Saves.last_ms, Saves.last_bytes / 1024, worst])
	timings.append([label, g.map.terrains.size(), Saves.last_ms, Saves.last_bytes])
	await _frames(1)


## 12 autosaves keep the newest 10; slots fill and overwrite.
func _ring_and_slots() -> void:
	for k in 12:
		game.minute = float(k)   # tells them apart
		Saves.autosave(game)
	var h: Dictionary = Saves.read_index().heroes[Hero.current.id]
	_check(h.autos.size() == Saves.AUTOS, "12 autosaves keep the last %d (%d)" % [Saves.AUTOS, h.autos.size()])
	var files := Array(DirAccess.get_files_at("%s/%s" % [Saves.dir, Hero.current.id])).filter(func(n): return n.begins_with("auto_"))
	_check(files.size() == Saves.AUTOS, "and %d autosave files on disk (%s)" % [Saves.AUTOS, files])
	var newest := Saves.read(Hero.current.id, h.autos[0].file)
	_check(not newest.is_empty() and is_equal_approx(newest.game.minute, 11.0), "the newest autosave is first in the list")
	var oldest := Saves.read(Hero.current.id, h.autos[-1].file)
	_check(not oldest.is_empty() and is_equal_approx(oldest.game.minute, 2.0), "the oldest kept is the 3rd made")
	Saves.save_slot(game, 1)
	h = Saves.read_index().heroes[Hero.current.id]
	_check(h.slots.all(func(s): return not s.is_empty()), "the 3 slots fill")
	var row: Dictionary = Saves.heroes()[0]
	_check(row.time.begins_with("Today ") and row.autos[0].time.begins_with("Today "), "rows say \"Today 9:40 pm\": %s" % row.time)
	_check(Saves.when(int(Time.get_unix_time_from_system()) - 86400).begins_with("Yesterday "), "and \"Yesterday ...\" for the day before")
	_check(Saves.when(int(Time.get_unix_time_from_system()) - 86400 * 5).contains(", "), "and \"Nov 3, 9:40 pm\" before that: %s" % Saves.when(int(Time.get_unix_time_from_system()) - 86400 * 5))
	await _frames(1)


## The debug map: every finished variant, raised hills, a canyon, rivers and towns, round-tripped and timed.
func _debug_map() -> void:
	game.run.goal_regions = 0   # past the prototype's goal: the end panel would stop placing
	game.end_panel.visible = false
	game.hud.hide_encounter()
	game.level_pick.visible = false
	game._picks = 0
	game.busy = false
	game.spawn_forest_regions()
	await _frames(10)
	await _time("big (debug map)", game)
	await _round_trip("debug map (%d tiles, %d regions)" % [game.map.terrains.size(), game.regions.size()])
	game.minute = 10.0   # by day: night's sight would stop placing far out
	var grew := []
	for pair in [["canyon", "desert"], ["snowy_peaks", "hills"]]:   # a finished region that grows keeps its old maze and trails
		var region := _region_on_free_land(pair[0], pair[1])
		var before: int = region.tiles.size()
		var at: Vector2i = region.tiles[1] + Hex.NEIGHBOURS[0]
		for t: Vector2i in region.tiles:
			for n: Vector2i in Hex.NEIGHBOURS:
				if game.why_not(t + n, pair[1]) == "":
					at = t + n
		game.deck.hand.append(pair[1])
		game.hold(game.deck.hand.size() - 1)
		_check(game.try_place(at), "a %s tile placed beside the %s region (%s)" % [pair[1], pair[0], game.why_not(at, pair[1])])
		await _frames(2)
		var waited := 0
		while game.busy and waited < 1200:
			await get_tree().process_frame
			waited += 1
		_check(region.tiles.size() > before, "the %s region grew from %d to %d tiles" % [pair[0], before, region.tiles.size()])
		grew.append(pair[0])
	await _frames(5)
	await _round_trip("grown %s" % " and ".join(grew))


## A finished 7-tile region on empty land, made as the debug spawn makes them, with free slots round it so it can grow.
func _region_on_free_land(variant: String, terrain: String) -> Dictionary:
	var shape: Array = [Vector2i.ZERO]
	shape.append_array(Hex.NEIGHBOURS)
	var anchor := game._free_spot(shape, {})
	var tiles: Array[Vector2i] = []
	for x: Vector2i in shape:
		tiles.append(anchor + x)
	var region := game.new_region(terrain, tiles, variant, tiles[0])
	game._set_flow(region)
	if variant == "canyon":
		region.canyon_tiles = tiles.duplicate()
		game.map.generate_canyon(tiles, region.landmark_tile)
	if variant in Cliffs.RAISED:
		game.map.set_raised(game.regions.size() - 1, tiles)
	var changes := {}
	for x in tiles:
		changes[x] = game.region_look(region, x)
		game.order[x] = game.order.size()
	game.map.retile(changes)
	return region


## Bad files, two heroes of one name, delete.
func _files() -> void:
	var id: String = Hero.current.id
	var path := ProjectSettings.globalize_path("%s/%s/slot_2.json" % [Saves.dir, id])
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string("{ not json")
	f.close()
	_check(Saves.read(id, "slot_2").is_empty(), "a broken save reads as nothing (Load dims it)")
	var newer := Saves.read(id, "slot_1")
	newer.version = SaveGame.VERSION + 1
	f = FileAccess.open(path, FileAccess.WRITE)
	f.store_string(JSON.stringify(JSON.from_native(newer), "", true, true))
	f.close()
	_check(Saves.read(id, "slot_2").is_empty(), "a save from a newer build reads as nothing")
	var other := Hero.new()
	other.name = Hero.current.name
	var keep := Hero.current
	Hero.current = other
	Saves.autosave(game)
	Hero.current = keep
	var heroes := Saves.heroes()
	_check(heroes.size() == 2 and heroes[0].id != heroes[1].id and heroes[0].name == heroes[1].name, "two heroes of one name keep their own saves")
	Saves.delete_hero(other.id)
	_check(Saves.heroes().size() == 1 and not DirAccess.dir_exists_absolute("%s/%s" % [Saves.dir, other.id]), "delete removes a hero's saves and folder")
