class_name RuinsCheck
extends Node
## Checks the ruins kit (tiles v92 corner halls, v96 outpost stockade, v97 graveyard city, v98 colonnade field,
## art/handoff/ruins_kit.md) in the game (`-- --ruinscheck`, add `--shots` for screens/ruins_*.png): each tile's halls and their
## join flags, the stockade and its burrows, the Warren and its routes, the graveyard plots, wisps and mist, the Crypt and its
## routes, the column grids and their parties, the Nest and its routes, plain halls left part-open beside the variants, a rebuilt
## neighbour re-picking its halls, the glows at night, and ground cover.
## Prints RUINS OK / RUINS FAIL lines, then RUINS DONE. A test aid only.

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
	var haunted := {}
	var basilisk := {}
	for g in game.regions:
		if g.variant == "overrun_outpost":
			outpost = g
		if g.variant == "haunted_ruins":
			haunted = g
		if g.variant == "basilisk_ruins":
			basilisk = g
	_check(not outpost.is_empty(), "the 12-tile Overrun outpost is on the map")
	_check(not haunted.is_empty(), "the 12-tile Haunted ruins is on the map")
	_check(not basilisk.is_empty(), "the 12-tile Basilisk ruins is on the map")
	var beside := func(t: Vector2i, g: Dictionary) -> bool:
		return Hex.NEIGHBOURS.any(func(n): return t + n in g.tiles)
	var all_plain := map.terrains.keys().filter(func(t): return map.terrains[t] == "ruins")
	var edge := all_plain.filter(func(t): return beside.call(t, haunted))
	var edge_b := all_plain.filter(func(t): return beside.call(t, basilisk))
	var plain := all_plain.filter(func(t): return not beside.call(t, haunted) and not beside.call(t, basilisk))
	_check(plain.size() == 7, "the tier 0 ruins group is on the map (%d tiles)" % plain.size())
	_check_plain(plain)
	_check_outpost(outpost)
	_check_warren(outpost)
	_check_haunted(haunted, edge)
	_check_crypt(haunted)
	_check_basilisk(basilisk, edge_b)
	_check_nest(basilisk)
	_check_cover()
	await _pictures(plain, outpost, haunted, basilisk)
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
		var halls := ps.filter(func(p): return p.begins_with("stockade_"))
		var want := RuinHalls.outpost(map.terrains, t).map(func(h): return h[0])
		var have := ps.filter(func(p): return p.begins_with("stockade_") or p.begins_with("outpost_burrow_"))
		want.sort()
		have.sort()
		if have != want or ps.any(func(p): return p.begins_with("outpost_hall_")):
			bad += 1
		var dug := halls.filter(func(p): return p.ends_with("_burrow")).size()
		var holes := ps.filter(func(p): return p.begins_with("outpost_burrow_")).size()
		counts[dug] = counts.get(dug, 0) + 1
		burrows += holes
		if halls.size() != 6 or dug != holes or not dug in [1, 2] or ps.any(func(p): return p.begins_with("ruin_hall_")):
			bad += 1
		if not "overrun_outpost_centre" in ps:
			bad += 1
	_check(bad == 0, "outpost: a stretch of stockade at each corner, one or two breached with a burrow outside (tiles by burrows: %s)" % [counts])
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


## The graveyard city: a walled plot at each corner, wisps over two or three plots, one or two mists; no halls. Plain ruins beside
## it reach out to it, left part-open.
func _check_haunted(g: Dictionary, edge: Array) -> void:
	var lm: Vector2i = g.landmark_tile
	var bad := 0
	var wisps := {}
	for t: Vector2i in g.tiles:
		if t == lm:
			continue
		var ps := _pieces(t)
		var want := RuinHalls.haunted(map.terrains, t).map(func(h): return h[0])
		var have := ps.filter(func(p): return p.begins_with("graveyard_") or p.begins_with("haunt_"))
		want.sort()
		have.sort()
		var w := ps.filter(func(p): return p == "haunt_wisps").size()
		var m := ps.filter(func(p): return p == "haunt_mist").size()
		wisps[w] = wisps.get(w, 0) + 1
		if have != want or not w in [2, 3] or not m in [1, 2] or not "haunted_ruins_centre" in ps:
			bad += 1
		if ps.any(func(p): return p.begins_with("ruin_hall_") or p.begins_with("haunted_block_") or p.begins_with("haunted_ghost_")):
			bad += 1
		if ps.filter(func(p): return p.begins_with("graveyard_")).size() != 6:
			bad += 1
	_check(bad == 0, "graveyard city: six plots a tile, wisps and mist, no halls or ghost town (tiles by wisps: %s)" % [wisps])
	# A wisp stands over its plot, 3.2 m out toward a corner.
	var t: Vector2i = g.tiles.filter(func(x): return x != lm)[0]
	var at := Hex.tile_position(t.x, t.y)
	var on_plot := true
	for c in map.tile_node(t).get_children():
		if c is MeshInstance3D and c.get_meta("piece", "") == "haunt_wisps":
			var p := Vector2(c.position.x, -c.position.z) - at
			var corner := fposmod(rad_to_deg(p.angle()) - 30.0, 60.0)
			on_plot = on_plot and absf(p.length() - RuinHalls.WISP_AT.x) < 0.01 and (corner < 0.01 or corner > 59.99)
	_check(on_plot, "each wisp stands over a plot, %.1f m out toward a corner" % RuinHalls.WISP_AT.x)
	_check(map._haunt.has("haunt_glow") and not map._haunt.has("ghost_house"), "the mausolea's doors and open graves glow; no ghost materials")
	_check(map._haunt_wisp is ShaderMaterial and map._haunt_wisp.shader.resource_path.ends_with("haunt_wisp.gdshader"), "the wisps drift up (their own shader)")
	# Plain halls beside the graveyard city reach its edge.
	var open := 0
	for e: Vector2i in edge:
		var halls := RuinHalls.halls(map.terrains, e)
		for c in 6:
			if e + Hex.NEIGHBOURS[c] in g.tiles and halls[c][0].substr(halls[c][0].length() - 2, 1) == "1":
				open += 1
		var have := _pieces(e).filter(func(p): return p.begins_with("ruin_hall_"))
		var want := halls.map(func(h): return h[0])
		have.sort()
		want.sort()
		if have != want:
			open = -99
	_check(edge.size() == 2 and open > 0, "plain halls beside the graveyard city reach out to it, left part-open (%d halls on %d tiles)" % [open, edge.size()])


## The Crypt: a centre-only landmark on the graveyard city's wedges, no plots, its routes the ring and the approach to its doors.
func _check_crypt(g: Dictionary) -> void:
	var lm: Vector2i = g.landmark_tile
	var ps := _pieces(lm)
	_check(map.terrains[lm] == "crypt" and "crypt_centre" in ps and not ps.any(func(p): return p.begins_with("graveyard_") or p.begins_with("ruin_hall_")),
			"the Crypt stands on its landmark tile, with no plots")
	_check(ps.any(func(p): return p.begins_with("haunted_ruins_edge")), "and the graveyard city's wedges")
	var turn: int = map.landmark_turns.get(lm, 0)
	var at := Hex.tile_position(lm.x, lm.y)
	var graph := map.path_graph(lm)
	var doors := at + Vector2(1.95, 0).rotated(deg_to_rad(60.0 * turn))
	var ring := at + Vector2(3.0, 0).rotated(deg_to_rad(60.0 * turn + 30.0)) * cos(deg_to_rad(30.0))
	_check(graph.distance_to_paths(doors) < 0.05 and graph.distance_to_paths(ring) < 0.05 and graph.distance_to_paths(at) > 1.0,
			"its routes: the ring 3 m out and the approach to its doors, not the tile's middle")
	_check("haunted_ruins" in Variants.TIER2.ruins and Variants.TIER2_NAMES.haunted_ruins == ["Haunted ruins", "Crypt"],
			"a later ruins region can roll Haunted ruins, with the Crypt")


## Basilisk ruins: a column grid at each corner, a party of stone explorers in at most two of them; plain halls beside it reach out
## to it, left part-open.
func _check_basilisk(g: Dictionary, edge: Array) -> void:
	var lm: Vector2i = g.landmark_tile
	var bad := 0
	var parties := {}
	for t: Vector2i in g.tiles:
		if t == lm:
			continue
		var ps := _pieces(t)
		var want := RuinHalls.basilisk(map.terrains, t).map(func(h): return h[0])
		var have := ps.filter(func(p): return p.begins_with("colonnade_"))
		want.sort()
		have.sort()
		var n := have.filter(func(p): return p.begins_with("colonnade_party_")).size()
		parties[n] = parties.get(n, 0) + 1
		if have != want or have.size() != 6 or n > RuinHalls.PARTY_MOST or not "basilisk_ruins_centre" in ps or ps.any(func(p): return p.begins_with("ruin_hall_")):
			bad += 1
	_check(bad == 0, "basilisk ruins: a column grid at each corner, at most two with a stone party (tiles by parties: %s)" % [parties])
	# Over many tiles the parties come as the hand-off counts them (400 tiles: 161 none, 157 one, 82 two).
	var counts := [0, 0, 0]
	for i in 400:
		var t := Vector2i(i % 20 - 10, i / 20 - 10)
		counts[RuinHalls.basilisk({}, t).filter(func(h): return h[0].begins_with("colonnade_party_")).size()] += 1
	_check(counts == [161, 157, 82], "parties over 400 tiles (the hand-off's): %d none, %d one, %d two" % counts)
	var open := 0
	for e: Vector2i in edge:
		var halls := RuinHalls.halls(map.terrains, e)
		for c in 6:
			if e + Hex.NEIGHBOURS[c] in g.tiles and halls[c][0].substr(halls[c][0].length() - 2, 1) == "1":
				open += 1
		var have := _pieces(e).filter(func(p): return p.begins_with("ruin_hall_"))
		var want := halls.map(func(h): return h[0])
		have.sort()
		want.sort()
		if have != want:
			open = -99
	_check(edge.size() == 2 and open > 0, "plain halls beside the basilisk ruins reach out to it, left part-open (%d halls on %d tiles)" % [open, edge.size()])


## The Basilisk Nest: a centre-only landmark on the basilisk ruins' wedges, no halls, its routes the ring and the approach to its
## door's step; its eyes are their own material.
func _check_nest(g: Dictionary) -> void:
	var lm: Vector2i = g.landmark_tile
	var ps := _pieces(lm)
	_check(map.terrains[lm] == "basilisknest" and "basilisknest_centre" in ps and not ps.any(func(p): return p.contains("_hall_") or p.contains("_party_")),
			"the Basilisk Nest stands on its landmark tile, with no halls")
	_check(ps.any(func(p): return p.begins_with("basilisk_ruins_edge")), "and the basilisk ruins' wedges")
	var turn: int = map.landmark_turns.get(lm, 0)
	var at := Hex.tile_position(lm.x, lm.y)
	var graph := map.path_graph(lm)
	var step := at + Vector2(1.7, 0).rotated(deg_to_rad(60.0 * turn))
	var ring := at + Vector2(3.0, 0).rotated(deg_to_rad(60.0 * turn + 30.0)) * cos(deg_to_rad(30.0))
	_check(graph.distance_to_paths(step) < 0.05 and graph.distance_to_paths(ring) < 0.05 and graph.distance_to_paths(at) > 1.0,
			"its routes: the ring 3 m out and the approach to its door's step, not the tile's middle")
	_check("basilisk_ruins" in Variants.TIER2.ruins and Variants.TIER2_NAMES.basilisk_ruins == ["Basilisk ruins", "Basilisk Nest"],
			"a later ruins region can roll Basilisk ruins, with the Nest")
	_check(map._basilisk_eye != null and map._basilisk_eye.resource_name == "basilisk_eye", "the Nest's eyes have their own material")


func _check_cover() -> void:
	_check(GroundCover.DENSITY.ruins == 0.1 and GroundCover.DENSITY.overrun_outpost == 0.1 and GroundCover.DENSITY.warren == 0.1
			and GroundCover.DENSITY.haunted_ruins == 0.1 and GroundCover.DENSITY.crypt == 0.1
			and GroundCover.DENSITY.basilisk_ruins == 0.1 and GroundCover.DENSITY.basilisknest == 0.1,
			"ground cover 0.1 on ruins, the outpost, the Warren, the graveyard city, the Crypt, the basilisk ruins and the Nest")
	_check(GroundCover.TUFT.basilisk_ruins == "tuft_stone" and GroundCover.TUFT.basilisknest == "tuft_stone"
			and "basilisk_ruins" in GroundCover.NO_FLOWERS and "basilisknest" in GroundCover.NO_FLOWERS, "stone tufts and no flowers on the basilisk ruins and the Nest")


## Day and night, plain ruins, the outpost, the graveyard city and the basilisk ruins; the eyes and the graveyard glow at night.
func _pictures(plain: Array, g: Dictionary, haunted: Dictionary, basilisk: Dictionary) -> void:
	for when: Array in [[Rules.START_MINUTE, "day"], [Rules.NIGHT_AT + 4.0, "night"]]:
		game.minute = when[0]
		game._shown_minute = -1.0   # straight there, not eased
		await _wait(Rules.SUN_BLEND_SECONDS + 1.0)
		if when[1] == "day":
			_check(map._goblin_eye != null and map._goblin_eye.emission_energy_multiplier < 0.5, "by day the goblin eyes don't glow (%.1f)" % map._goblin_eye.emission_energy_multiplier)
			_check(map._basilisk_eye.emission_energy_multiplier < 0.6, "by day the basilisk's eyes glint faintly (%.1f)" % map._basilisk_eye.emission_energy_multiplier)
		else:
			_check(map._goblin_eye.emission_energy_multiplier > 3.0, "at night they glow (%.1f)" % map._goblin_eye.emission_energy_multiplier)
			_check(map._basilisk_eye.emission_energy_multiplier > 1.4, "at night the basilisk's eyes glow (%.1f)" % map._basilisk_eye.emission_energy_multiplier)
		var glow: float = map._haunt.haunt_glow.emission_energy_multiplier
		_check(glow < 0.5 if when[1] == "day" else glow > 1.3, "the graveyard's glows at %s (%.1f)" % [when[1], glow])
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
		game.rig.frame(_middle(haunted.tiles), 42.0, 45.0)
		await _wait(0.6)
		await _shot("haunted_%s" % when[1])
		var cr: Vector2i = haunted.landmark_tile
		game.rig.frame(Hex.to3(Hex.tile_position(cr.x, cr.y)), 16.0, 40.0)
		await _wait(0.6)
		await _shot("crypt_%s" % when[1])
		var near: Vector2i = haunted.tiles.filter(func(x): return x != cr)[0]
		game.rig.frame(Hex.to3(Hex.tile_position(near.x, near.y)), 14.0, 40.0)
		await _wait(0.6)
		await _shot("haunted_close_%s" % when[1])
		game.rig.frame(_middle(basilisk.tiles), 42.0, 45.0)
		await _wait(0.6)
		await _shot("basilisk_%s" % when[1])
		var bn: Vector2i = basilisk.landmark_tile
		game.rig.frame(Hex.to3(Hex.tile_position(bn.x, bn.y)), 16.0, 40.0)
		await _wait(0.6)
		await _shot("nest_%s" % when[1])
		var party: Array = basilisk.tiles.filter(func(x): return x != bn and _pieces(x).any(func(p): return p.begins_with("colonnade_party_")))
		var close: Vector2i = party[0] if not party.is_empty() else basilisk.tiles.filter(func(x): return x != bn)[0]
		game.rig.frame(Hex.to3(Hex.tile_position(close.x, close.y)), 14.0, 40.0)
		await _wait(0.6)
		await _shot("basilisk_close_%s" % when[1])
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
