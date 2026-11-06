class_name Saves
extends RefCounted
## Save files (design/06 -> Saving): per hero, the last 10 autosaves in a ring and 3 save slots, under user://saves/<hero id>/,
## with an index of every hero so the title and Load read one small file. Saves are JSON (JSON.from_native, so tiles and
## numbers come back exactly), written to a .tmp file and renamed, so an app closed mid-write never leaves a broken save.
## Autosaves: every hex move, after every fight and after every rest (watch). Only a campaign with a hero autosaves, so the
## checks and direct starts never touch real saves; checks point `dir` elsewhere.

const AUTOS := 10
const SLOTS := 3
const GAME_SCENE := "res://scenes/main.tscn"

static var dir := _first_dir()
static var pending := {}          # a save to apply as the game scene opens (Screens)
static var last_ms := {}          # the last save's timings: capture, encode, write (the save check and --savetime print them)
static var last_bytes := 0
static var _queue := []           # captured saves waiting for the writer
static var _lock := Mutex.new()
static var _task := -1


## user://saves, or a checks' folder for a test run (`-- --savesdir=saves_check`: the title over the save check's saves).
static func _first_dir() -> String:
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--savesdir=") and "check" in a:
			return "user://" + a.get_slice("=", 1)
	return "user://saves"


## Hooks a running Game's autosaves: each step onto a hex, and each fight's end (after its results and any level pick or
## member joining). The rest's comes from Game.rest_here.
static func watch(g: Game) -> void:
	g.party_node.entered.connect(func(_t): autosave(g), CONNECT_DEFERRED)
	g.after.done.connect(func(): autosave(g), CONNECT_DEFERRED)


static func autosave(g: Game) -> void:
	if Hero.current == null or g.fight.active:
		return
	_write(g, "auto")


## Saves to slot i (0-2); the pause menu asks first when it's used (design/06).
static func save_slot(g: Game, i: int) -> void:
	if Hero.current != null:
		_write(g, "slot_%d" % (i + 1))


static func _write(g: Game, kind: String) -> void:
	var hero := Hero.current
	if hero.id == "":
		hero.id = "%x%x" % [Time.get_unix_time_from_system(), randi()]
	var t0 := Time.get_ticks_usec()
	var job := {data = SaveGame.capture(g), kind = kind, id = hero.id, dir = dir, tiles = g.map.terrains.size()}
	job.main_ms = (Time.get_ticks_usec() - t0) / 1000.0
	_lock.lock()
	_queue.append(job)
	var start := _task < 0 or WorkerThreadPool.is_task_completed(_task)
	_lock.unlock()
	if start:
		if _task >= 0:
			WorkerThreadPool.wait_for_task_completion(_task)
		_task = WorkerThreadPool.add_task(_drain)


## Off the main thread: encodes and writes each queued save in turn (measured: 10 ms for a 900-tile map on the Mac, most of it
## encoding, which would be a dropped frame on every step), so a step only pays for the capture.
static func _drain() -> void:
	while true:
		_lock.lock()
		var job = _queue.pop_front() if not _queue.is_empty() else null
		_lock.unlock()
		if job == null:
			return
		_encode_and_store(job)


static func _encode_and_store(job: Dictionary) -> void:
	var t1 := Time.get_ticks_usec()
	var data: Dictionary = job.data
	var text := JSON.stringify(JSON.from_native(data), "", true, true)   # full precision: the clock and timers come back exactly
	var t2 := Time.get_ticks_usec()
	var index := _read_index(job.dir)
	var h: Dictionary = index.heroes.get(job.id, {autos = [], slots = [{}, {}, {}]})
	var kind: String = job.kind
	var file := kind
	if kind == "auto":
		var used: Array = h.autos.map(func(a): return a.file)
		file = h.autos[-1].file if h.autos.size() >= AUTOS else "auto_%d" % range(AUTOS).filter(func(k): return not "auto_%d" % k in used)[0]
	_store("%s/%s/%s.json" % [job.dir, job.id, file], text)
	var row := {file = file, at = data.saved_at, place = data.meta.place, level = data.meta.level}
	if kind == "auto":
		h.autos = h.autos.filter(func(a): return a.file != file)
		h.autos.push_front(row)
	else:
		h.slots[int(kind.get_slice("_", 1)) - 1] = row
	h.merge({name = data.meta.name, subtitle = data.meta.subtitle, color = data.meta.color, initial = data.meta.initial,
			last = data.saved_at}, true)
	index.heroes[job.id] = h
	_store("%s/index.json" % job.dir, JSON.stringify(index, "\t"))
	var t3 := Time.get_ticks_usec()
	last_ms = {main = job.main_ms, encode = (t2 - t1) / 1000.0, write = (t3 - t2) / 1000.0}
	last_bytes = text.length()
	if "--savetime" in OS.get_cmdline_user_args():
		print("SAVE %s %d tiles: on the frame %.2f ms; off it: encode %.1f ms, write %.1f ms; %d KB" % [kind, job.tiles,
				job.main_ms, last_ms.encode, last_ms.write, last_bytes / 1024])


## Waits for queued saves to be on disk (before reading the index or a save, and the checks).
static func flush() -> void:
	if _task >= 0:
		WorkerThreadPool.wait_for_task_completion(_task)
		_task = -1


static func _store(path: String, text: String) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var f := FileAccess.open(path + ".tmp", FileAccess.WRITE)
	if f == null:
		push_error("SAVE can't write %s" % path)
		return
	f.store_string(text)
	f.close()
	DirAccess.rename_absolute(path + ".tmp", path)


static func read_index() -> Dictionary:
	flush()
	return _read_index(dir)


static func _read_index(folder: String) -> Dictionary:
	var f := FileAccess.open("%s/index.json" % folder, FileAccess.READ)
	var d = JSON.parse_string(f.get_as_text()) if f else null
	if not d is Dictionary or not d.get("heroes") is Dictionary:
		return {version = 1, heroes = {}}
	for id: String in d.heroes:
		var h: Dictionary = d.heroes[id]
		for a: Dictionary in h.autos:
			a.at = int(a.at)
		for s: Dictionary in h.slots:
			if not s.is_empty():
				s.at = int(s.at)
	return d


## A save's data, or {} if it won't read or is from a newer build (Load dims it).
static func read(hero_id: String, file: String) -> Dictionary:
	flush()
	var f := FileAccess.open("%s/%s/%s.json" % [dir, hero_id, file], FileAccess.READ)
	if f == null:
		return {}
	var parsed = JSON.parse_string(f.get_as_text())
	if parsed == null:
		return {}
	var d = JSON.to_native(parsed)
	if not d is Dictionary or int(d.get("version", 0)) > SaveGame.VERSION:
		return {}
	return SaveUpgrade.upgrade(d)


## Heroes for Load and Continue, most recently played first: index rows with their id and time strings.
static func heroes() -> Array:
	var index := read_index()
	var out := []
	for id: String in index.heroes:
		var h: Dictionary = index.heroes[id].duplicate(true)
		h.id = id
		h.time = when(int(h.last))
		h.autos = h.autos.map(func(a): return {file = a.file, place = a.place, time = when(a.at), level = a.level})
		h.slots = h.slots.map(func(s): return {} if s.is_empty() else {file = s.file, place = s.place, time = when(s.at), level = s.level})
		out.append(h)
	out.sort_custom(func(a, b): return a.last > b.last)
	return out


static func delete_hero(id: String) -> void:
	flush()
	var folder := "%s/%s" % [dir, id]
	for n in DirAccess.get_files_at(folder):
		DirAccess.remove_absolute("%s/%s" % [folder, n])
	DirAccess.remove_absolute(folder)
	var index := read_index()
	index.heroes.erase(id)
	_store("%s/index.json" % dir, JSON.stringify(index, "\t"))


## Empties a checks' save folder (only a folder named for checks: real saves are never wiped this way).
static func wipe_check_dir(path: String) -> void:
	flush()
	if not "check" in path.get_file() or not DirAccess.dir_exists_absolute(path):
		return
	for d in DirAccess.get_directories_at(path):
		for f in DirAccess.get_files_at("%s/%s" % [path, d]):
			DirAccess.remove_absolute("%s/%s/%s" % [path, d, f])
		DirAccess.remove_absolute("%s/%s" % [path, d])
	for f in DirAccess.get_files_at(path):
		DirAccess.remove_absolute("%s/%s" % [path, f])


## Opens the game scene on a save (Continue, Load).
static func play(tree: SceneTree, data: Dictionary) -> void:
	Hero.current = SaveGame.hero_of(data)
	RunSetup.next = null
	pending = data
	tree.change_scene_to_file(GAME_SCENE)


## A save's time as its row shows it (design/07 -> What a save shows: "Today 9:40 pm"). PLACEHOLDER past today (approved
## for the plan): "Yesterday 9:40 pm", then "Nov 3, 9:40 pm".
static func when(unix: int) -> String:
	var bias := int(Time.get_time_zone_from_system().bias) * 60
	var t := Time.get_datetime_dict_from_unix_time(unix + bias)
	var now := Time.get_datetime_dict_from_unix_time(int(Time.get_unix_time_from_system()) + bias)
	var clock := "%d:%02d %s" % [(t.hour + 11) % 12 + 1, t.minute, "am" if t.hour < 12 else "pm"]
	var days := (int(Time.get_unix_time_from_system()) + bias) / 86400 - (unix + bias) / 86400
	if days == 0:
		return "Today " + clock
	if days == 1:
		return "Yesterday " + clock
	const MONTHS := ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	var date := "%s %d" % [MONTHS[t.month - 1], t.day]
	if t.year != now.year:
		date += " %d" % t.year
	return "%s, %s" % [date, clock]
