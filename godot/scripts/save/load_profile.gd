class_name LoadProfile
extends Node
## Where a load's time goes (`-- --loadprofile`), for the planner's timing report. Builds the debug map, saves it, cuts it
## down to smaller maps round the start (every tile within a distance), then loads each size 3 times into a fresh game scene.
## Each load is timed step by step: reading the file, parsing the JSON, turning it back into Godot values, the game's own
## setup, the map's history-dependent parts, and MapBoard.retile's steps (rerun here from outside with timers between them,
## in the same order; the slowest terrains of _build_tile too). Prints LOADPROF lines and quits. A test aid only.

const DIR := "user://saves_loadprofile_check"
const RUNS := 3
const RADII := [3, 7, 10, 99]   # tiles within this distance of the start: about 25, 120, 250 and the whole map

static var instance: LoadProfile
static var profile := {}         # the current load's steps, filled by restore_profiled

var game: Game
var results := {}               # tiles -> [ {step: ms} per run ]


static func attach(g: Game) -> void:
	if instance != null:
		return
	instance = LoadProfile.new()
	instance.game = g
	g.get_tree().root.add_child.call_deferred(instance)


func _ready() -> void:
	_run.call_deferred()


func _new_game() -> void:
	var old := game
	while not (get_tree().current_scene is Game and get_tree().current_scene != old):
		await get_tree().process_frame
	game = get_tree().current_scene
	for _k in 3:
		await get_tree().process_frame


func _run() -> void:
	Saves.dir = DIR
	Saves.wipe_check_dir(DIR)
	Hero.current = SaveCheck.test_hero("Profile")
	game.spawn_forest_regions()
	for _k in 10:
		await get_tree().process_frame
	var full := SaveGame.capture(game)
	for r: int in RADII:
		var data := _cut(full, r)
		var tiles: int = data.map.terrains.size()
		results[tiles] = []
		var path := ProjectSettings.globalize_path("%s/profile_%d.json" % [DIR, r])
		DirAccess.make_dir_recursive_absolute(path.get_base_dir())
		var f := FileAccess.open(path, FileAccess.WRITE)
		f.store_string(JSON.stringify(JSON.from_native(data), "", true, true))
		f.close()
		for k in RUNS:
			var steps := {}
			var t := Time.get_ticks_usec()
			var text := FileAccess.get_file_as_string(path)
			steps.read = _ms(t)
			t = Time.get_ticks_usec()
			var parsed = JSON.parse_string(text)
			steps.parse = _ms(t)
			t = Time.get_ticks_usec()
			var back: Dictionary = JSON.to_native(parsed)
			steps.to_native = _ms(t)
			steps.kb = text.length() / 1024
			profile = {}
			var scene_t := Time.get_ticks_usec()
			Saves.play(get_tree(), back)
			await _new_game()
			steps.merge(profile)
			steps.scene_open_and_apply = _ms(scene_t)
			var worst := 0.0
			for _f in 30:   # the first frames after: shaders and the first draw of every new mesh
				var f0 := Time.get_ticks_usec()
				await get_tree().process_frame
				worst = maxf(worst, _ms(f0))
			steps.worst_first_frame = worst
			results[tiles].append(steps)
			print("LOADPROF %d tiles, run %d: %s" % [tiles, k + 1, steps])
	_report()
	get_tree().quit()


func _ms(t0: int) -> float:
	return snappedf((Time.get_ticks_usec() - t0) / 1000.0, 0.1)


## The save with only the tiles within r of the start, and what belongs to them.
func _cut(full: Dictionary, r: int) -> Dictionary:
	var d := full.duplicate(true)
	var m: Dictionary = d.map
	var keep := func(t: Vector2i): return Rules.hex_distance(t, Rules.START_TILE) <= r
	for key in ["terrains", "order", "finished", "flow_dist", "flow_toward", "landmark_turns", "water_gates", "troll_water"]:
		for t: Vector2i in m[key].keys():
			if not keep.call(t):
				m[key].erase(t)
	for key in m.raised_regions.keys():
		if not m.raised_regions[key].all(keep):
			m.raised_regions.erase(key)
	for lm: Vector2i in m.canyons.keys():
		var region: Dictionary = m.regions[full.map.finished[lm]]
		if not region.get("canyon_tiles", region.tiles).all(keep):
			m.canyons.erase(lm)
	d.encounters = d.encounters.filter(func(e): return keep.call(e.tile))
	return d


func _report() -> void:
	print("LOADPROF ---- medians of %d runs (ms) ----" % RUNS)
	for tiles: int in results:
		var runs: Array = results[tiles]
		var med := {}
		for key in runs[0]:
			if runs[0][key] is float or runs[0][key] is int:
				var vals: Array = runs.map(func(x): return float(x.get(key, 0.0)))
				vals.sort()
				med[key] = vals[vals.size() / 2]
		var keys: Array = med.keys()
		keys.sort_custom(func(a, b): return med[a] > med[b])
		print("LOADPROF %d tiles: %s" % [tiles, ", ".join(keys.map(func(k): return "%s %s" % [k, med[k]]))])
		var slow: Dictionary = runs[runs.size() / 2].get("build_by_terrain", {})
		var names: Array = slow.keys()
		names.sort_custom(func(a, b): return slow[a][0] > slow[b][0])
		print("LOADPROF %d tiles, _build_tile by terrain (ms, tiles): %s" % [tiles, ", ".join(names.slice(0, 8).map(func(n): return "%s %.0f/%d" % [n, slow[n][0], slow[n][1]]))])


## SaveGame.restore_map's retile, step by step (MapBoard.retile's own steps in its order, with timers). Fills `profile`.
static func restore_profiled(m: MapBoard, changes: Dictionary) -> void:
	var clock := {t = Time.get_ticks_usec()}   # a dictionary: a lambda copies plain locals
	var lap := func(name: String):
		profile[name] = profile.get(name, 0.0) + snappedf((Time.get_ticks_usec() - clock.t) / 1000.0, 0.1)
		clock.t = Time.get_ticks_usec()
	if m._kit.is_empty():
		m._setup()
	lap.call("kit_setup")
	var water_changed := false
	var touched := {}
	for c: Vector2i in changes:
		m.terrains[c] = changes[c]
		m._set_ground(c)
		touched[c] = true
		if Variants.is_water(changes[c]):
			water_changed = true
		for n in Hex.NEIGHBOURS:
			if m.terrains.has(c + n):
				touched[c + n] = true
				if Variants.is_water(m.terrains[c + n]):
					water_changed = true
	lap.call("ground")
	if water_changed:
		m._update_water()
	lap.call("water")
	touched.merge(m._update_raised())
	lap.call("raised_cliffs")
	touched.merge(m._update_gates())
	lap.call("gates")
	touched.merge(m._update_streets())
	lap.call("streets")
	touched.merge(m._open_cut_off())
	lap.call("cut_off")
	touched.merge(m._canyon_dirty)
	m._canyon_dirty.clear()
	if changes.values().any(func(n): return n in ["badlands", "raiderstronghold"]):
		m._update_badlands()
	lap.call("badlands")
	var by := {}
	for c: Vector2i in touched:
		var t0 := Time.get_ticks_usec()
		m._build_tile(c)
		var name: String = m.terrains[c]
		var e: Array = by.get(name, [0.0, 0])
		by[name] = [e[0] + (Time.get_ticks_usec() - t0) / 1000.0, e[1] + 1]
	lap.call("build_tiles")
	profile.build_by_terrain = by
	for c: Vector2i in touched:
		m._add_cover(c)
	lap.call("ground_cover")
	m._update_smoke()
	m._update_lightning()
	lap.call("smoke_lightning")
	m._build_slots()
	lap.call("slots")
