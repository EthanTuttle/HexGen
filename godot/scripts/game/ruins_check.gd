class_name RuinsCheck
extends Node
## Checks the ruins kit (tiles v92 corner halls, v93 Overrun outpost, art/handoff/ruins_kit.md) in the game (`-- --ruinscheck`,
## add `--shots` for screens/ruins_*.png): each tile's halls and their join flags, the outpost's burrows, the Warren and its
## routes, a rebuilt neighbour re-picking its halls, the goblin eyes at night, and ground cover. Prints RUINS OK / RUINS FAIL
## lines, then RUINS DONE. A test aid only.

var game: Game
var shots := false
var failed := 0
var map: MapBoard


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("RUINS %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _shot(name: String) -> void:
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	if shots:
		var dir := ProjectSettings.globalize_path("res://screens")
		DirAccess.make_dir_recursive_absolute(dir)
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("ruins_%s.png" % name))
		print("SAVED ruins_%s" % name)


func _middle(tiles: Array) -> Vector3:
	var at := Vector2.ZERO
	for t: Vector2i in tiles:
		at += Hex.tile_position(t.x, t.y)
	return Hex.to3(at / tiles.size())


## The pieces placed on tile t, by name.
func _pieces(t: Vector2i) -> Array:
	var out := []
	for c in map.tile_node(t).get_children():
		if c is MeshInstance3D and c.has_meta("piece"):
			out.append(String(c.get_meta("piece")))
	return out


func _run() -> void:
	game.spawn_forest_regions()
	await _wait(1.0)
	map = game.map
	var outpost := {}
	for g in game.regions:
		if g.variant == "overrun_outpost":
			outpost = g
	_check(not outpost.is_empty(), "the 12-tile Overrun outpost is on the map")
	var plain := map.terrains.keys().filter(func(t): return map.terrains[t] == "ruins")
	_check(plain.size() == 7, "the tier 0 ruins group is on the map (%d tiles)" % plain.size())
	_check_plain(plain)
	_check_outpost(outpost)
	_check_warren(outpost)
	_check_cover()
	await _pictures(plain, outpost)
	_check_neighbour(plain)
	print("RUINS DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## Six halls a tile, each reaching out where its sides' neighbours are ruins, the variant from the tile's hash.
func _check_plain(plain: Array) -> void:
	var bad := 0
	var halls := 0
	var joined := 0
	for t: Vector2i in plain:
		var have := _pieces(t).filter(func(p): return p.begins_with("ruin_hall_"))
		halls += have.size()
		var want := RuinHalls.halls(map.terrains, t).map(func(h): return h[0])
		have.sort()
		want.sort()
		if have != want:
			bad += 1
		joined += want.filter(func(p): return p.ends_with("11")).size()
		for p: String in _pieces(t):
			if p.begins_with("ruin_") and not p.begins_with("ruin_hall_"):
				bad += 1   # tiles_v90's remains
	_check(bad == 0 and halls == plain.size() * 6, "plain ruins: six corner halls a tile, picked by the neighbours (%d halls, %d joined both ways)" % [halls, joined])
	_check(joined > 0, "where three ruins tiles meet, the halls reach the edge on both sides")


func _check_outpost(g: Dictionary) -> void:
	var lm: Vector2i = g.landmark_tile
	var bad := 0
	var burrows := 0
	var counts := {}
	for t: Vector2i in g.tiles:
		if t == lm:
			continue
		var ps := _pieces(t)
		var halls := ps.filter(func(p): return p.begins_with("outpost_hall_"))
		var dug := halls.filter(func(p): return p.ends_with("_burrow")).size()
		var holes := ps.filter(func(p): return p.begins_with("outpost_burrow_")).size()
		counts[dug] = counts.get(dug, 0) + 1
		burrows += holes
		if halls.size() != 6 or dug != holes or not dug in [1, 2] or ps.any(func(p): return p.begins_with("ruin_hall_")):
			bad += 1
		if not "overrun_outpost_centre" in ps:
			bad += 1
	_check(bad == 0, "outpost: six recoloured halls a tile, one or two dug with a burrow beside it (tiles by burrows: %s)" % [counts])
	var old := 0
	for t: Vector2i in g.tiles:
		for p: String in _pieces(t):
			if p.begins_with("outpost_") and p.get_slice("_", 1) in ["banner", "bones", "crates", "totem"]:
				old += 1
	_check(old == 0, "none of tiles_v90's goblin junk is placed")
	# A burrow stands on its hall's corner, its mouth to the tile's middle.
	var t: Vector2i = g.tiles.filter(func(x): return x != lm)[0]
	var at := Hex.tile_position(t.x, t.y)
	var far := true
	for c in map.tile_node(t).get_children():
		if c is MeshInstance3D and String(c.get_meta("piece", "")).begins_with("outpost_burrow_"):
			var p := Vector2(c.position.x, -c.position.z) - at
			far = far and absf(p.length() - RuinHalls.BURROW_AT.x) < 0.01 and absf(angle_difference(c.rotation.y, p.angle() + PI)) < 0.01
	_check(far, "each burrow stands %.1f m out toward its corner, its mouth facing the tile's middle" % RuinHalls.BURROW_AT.x)


## The Warren: a centre-only landmark on the outpost's wedges, no halls, its routes the ring and the approach to its mouth.
func _check_warren(g: Dictionary) -> void:
	var lm: Vector2i = g.landmark_tile
	var ps := _pieces(lm)
	_check(map.terrains[lm] == "warren" and "warren_centre" in ps and not ps.any(func(p): return p.contains("_hall_")),
			"the Warren stands on its landmark tile, with no halls")
	_check(ps.any(func(p): return p.begins_with("overrun_outpost_edge")), "and the outpost's wedges")
	var turn: int = map.landmark_turns.get(lm, 0)
	var at := Hex.tile_position(lm.x, lm.y)
	var graph := map.path_graph(lm)
	var mouth := at + Vector2(1.45, 0).rotated(deg_to_rad(60.0 * turn))
	var ring := at + Vector2(3.0, 0).rotated(deg_to_rad(60.0 * turn + 30.0)) * cos(deg_to_rad(30.0))
	_check(graph.distance_to_paths(mouth) < 0.05 and graph.distance_to_paths(ring) < 0.05 and graph.distance_to_paths(at) > 1.0,
			"its routes: the ring 3 m out and the approach to the mouth, not the tile's middle")
	var trails := LandmarkFlow.trail_edges(lm, map.flow_toward)
	_check(trails.is_empty() or turn in trails or map.flow_toward.values().has(lm), "it turns its mouth (edge %d) to the region's trails" % turn)


func _check_cover() -> void:
	_check(GroundCover.DENSITY.ruins == 0.1 and GroundCover.DENSITY.overrun_outpost == 0.1 and GroundCover.DENSITY.warren == 0.1,
			"ground cover 0.1 on ruins, the outpost and the Warren")


## Day and night, plain ruins and the outpost; the eyes glint only at night.
func _pictures(plain: Array, g: Dictionary) -> void:
	for when: Array in [[Rules.START_MINUTE, "day"], [Rules.NIGHT_AT + 4.0, "night"]]:
		game.minute = when[0]
		game._shown_minute = -1.0   # straight there, not eased
		await _wait(Rules.SUN_BLEND_SECONDS + 1.0)
		if when[1] == "day":
			_check(map._goblin_eye != null and map._goblin_eye.emission_energy_multiplier < 0.5, "by day the goblin eyes don't glow (%.1f)" % map._goblin_eye.emission_energy_multiplier)
		else:
			_check(map._goblin_eye.emission_energy_multiplier > 3.0, "at night they glow (%.1f)" % map._goblin_eye.emission_energy_multiplier)
		game.rig.player_moved = false
		game.rig.frame(_middle(plain), 34.0, 45.0)
		await _wait(0.6)
		await _shot("plain_%s" % when[1])
		game.rig.frame(_middle(g.tiles), 42.0, 45.0)
		await _wait(0.6)
		await _shot("outpost_%s" % when[1])
		var lm: Vector2i = g.landmark_tile
		game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y)), 16.0, 40.0)
		await _wait(0.6)
		await _shot("warren_%s" % when[1])
	game.minute = Rules.START_MINUTE
	game._shown_minute = -1.0


## A ruins tile placed beside the group: its neighbours rebuild, and the halls facing it reach out to it.
func _check_neighbour(plain: Array) -> void:
	for t: Vector2i in plain:
		for i in 6:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if map.terrains.get(n) in RuinHalls.LOOKS or n == Rules.START_TILE:
				continue
			var before := _pieces(t).filter(func(p): return p.begins_with("ruin_hall_"))
			map.place(n, "ruins")
			var after := _pieces(t).filter(func(p): return p.begins_with("ruin_hall_"))
			var want := RuinHalls.halls(map.terrains, t).map(func(h): return h[0])
			after.sort()
			want.sort()
			_check(after == want and after != before, "a ruins tile laid beside it: its neighbour re-picks the two halls facing it")
			return
	_check(false, "no spot beside the ruins group")
