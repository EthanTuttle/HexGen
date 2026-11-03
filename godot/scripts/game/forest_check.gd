class_name ForestCheck
extends Node
## Checks the forest kit (tiles v23) in the game (`-- --forestcheck`, add `--shots` to save screenshots to
## screens/forest_*.png): spawns a finished 7-tile region of each forest variant (Game.spawn_forest_regions),
## checks the pieces each tile picked against the trail rule, the landmark turn and edge_same_b, walks the party
## along each region's trails into its landmark and checks the route follows them, and prints the frame cost of
## the busiest view. Prints FOREST OK / FOREST FAIL lines, then FOREST DONE. A test aid only.

var game: Game
var shots := false
var failed := 0


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("FOREST %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _shot(name: String) -> void:
	for _f in 3:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	if shots:
		var dir := ProjectSettings.globalize_path("res://screens")
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("forest_%s.png" % name))
		print("SAVED forest_%s" % name)


func _region(variant: String) -> Dictionary:
	for g in game.regions:
		if g.variant == variant:
			return g
	return {}


## The pieces a tile's node holds, by name, with their turn in 60 degree steps.
func _pieces(t: Vector2i) -> Dictionary:
	var out := {}
	for c in game.map.tile_node(t).get_children():
		if c is MeshInstance3D and c.has_meta("piece"):
			var steps := posmod(roundi(rad_to_deg(c.rotation.y) / 60.0), 6)
			out[[String(c.get_meta("piece")), steps]] = true
	return out


func _has(t: Vector2i, piece: String, steps: int) -> bool:
	return _pieces(t).has([piece, steps])


func _run() -> void:
	game.spawn_forest_regions()
	await _wait(1.0)
	var map := game.map
	# 1. Pieces: trail wedges on both sides of every trail edge, near centres, the landmark turned to a trail.
	for v: String in Game.DEBUG_FOREST:
		var g := _region(v)
		var lm: Vector2i = g.landmark_tile
		var name: String = map.terrains[lm]
		var kit := Variants.wedges_of(name)
		var turn: int = map.landmark_turns.get(lm, 0)
		print("FOREST %s: landmark %s at %s, turn %d, dist %s" % [v, name, lm, turn,
				g.tiles.map(func(t): return map.flow_dist.get(t))])
		_check(_has(lm, name + "_centre", turn), "%s centre turned %d" % [name, turn])
		var trails := LandmarkFlow.trail_edges(lm, map.flow_toward)
		_check(g.tiles.size() == 1 or turn in trails, "%s entrance edge %d is a trail edge %s" % [name, turn, trails])
		var ok := true
		for t: Vector2i in g.tiles:
			var tn: String = map.terrains[t]
			for i in LandmarkFlow.trail_edges(t, map.flow_toward):
				var want := tn + "_edge_trail" if map._kit.has(tn + "_edge_trail") else Variants.wedges_of(tn) + "_edge_trail"
				if Variants.LANDMARKS.get(map.terrains.get(t + Hex.NEIGHBOURS[i])) == tn and map._kit.has(tn + "_edge_landmark"):
					want = tn + "_edge_landmark"
				if not _has(t, want, i):
					ok = false
					print("  missing %s on %s edge %d" % [want, t, i])
			if map.flow_dist.get(t) == 1 and map._kit.has(tn + "_centre_near") and not _has(t, tn + "_centre_near", 0):
				ok = false
				print("  missing %s_centre_near on %s" % [tn, t])
		_check(ok, "%s trail wedges on both sides of every trail edge, near centres next to the landmark" % v)
	# 2. edge_same_b: heartwood's joined edges alternate by the hash.
	var g := _region("heartwood")
	var a := 0
	var b := 0
	var right := true
	for t: Vector2i in g.tiles:
		if map.terrains[t] != "heartwood":
			continue
		var trails := LandmarkFlow.trail_edges(t, map.flow_toward)
		for i in 6:
			var near = map.terrains.get(t + Hex.NEIGHBOURS[i])
			if i in trails or not MapBoard.linked("heartwood", near) or Variants.LANDMARKS.get(near) == "heartwood":
				continue
			var want_b := GroundCover.hash01(t.x * 6 + i, t.y, 8) < 0.5
			if _has(t, "heartwood_edge_same_b", i):
				b += 1
				right = right and want_b
			elif _has(t, "heartwood_edge_same", i):
				a += 1
				right = right and not want_b
	print("FOREST heartwood joined edges: %d edge_same, %d edge_same_b" % [a, b])
	_check(right and a + b > 0, "heartwood edge_same_b picked by hash01(q * 6 + i, r, 8)")
	# 3. Materials: the web blends at 0.3 from both sides; the glows are on.
	var web: BaseMaterial3D = map._web
	_check(web.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA and is_equal_approx(web.albedo_color.a, 0.3)
			and web.cull_mode == BaseMaterial3D.CULL_DISABLED, "web material: blended, alpha 0.3, double-sided")

	# 4. Screenshots by day: the four regions, each region, each landmark facing its entrance.
	game.ui.visible = true
	game.rig.frame(Hex.to3(Vector2(0, 0)), Rules.DAY_MAX_ZOOM, 50.0)
	await _wait(1.5)
	await _shot("01_overview")
	await _perf("game camera zoomed all the way out over the four regions, HUD on")
	var hw: Vector2i = Game.DEBUG_FOREST.heartwood
	game.rig.frame(Hex.to3(Hex.tile_position(hw.x, hw.y)), 58.0, 50.0)
	await _perf("game camera at its opening zoom over heartwood and the Tree of Life, HUD on")
	game.ui.visible = false
	var focus := game.rig.focus
	game.rig.focus = Vector2(422, 195)   # the middle of the screen while the HUD is hidden
	var n := 2
	for v: String in Game.DEBUG_FOREST:
		var c: Vector2i = Game.DEBUG_FOREST[v]
		game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y)), 40.0, 50.0)
		await _wait(0.6)
		await _shot("%02d_region_%s" % [n, v])
		n += 1
	for v: String in Game.DEBUG_FOREST:
		var lm: Vector2i = _region(v).landmark_tile
		var e := map.entrance_angle(lm)
		var close := 26.0 if v == "heartwood" else 18.0   # the Tree of Life is about as tall as a hill peak
		game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y), 1.5 if v == "heartwood" else 0.8), close, 32.0,
				-90.0 - rad_to_deg(e))
		await _wait(0.6)
		await _shot("%02d_landmark_%s" % [n, map.terrains[lm]])
		n += 1
	var dark: Vector2i = Game.DEBUG_FOREST.dark_wood
	game.rig.frame(Hex.to3(Hex.tile_position(dark.x, dark.y), 1.0), 11.0, 30.0, 20.0)
	await _wait(0.6)
	await _shot("%02d_webs_closeup" % n)
	n += 1

	# 5. Walking the trails: from each region's farthest tile, along its trail steps into the landmark.
	game.ui.visible = true
	game.rig.focus = focus
	for v: String in Game.DEBUG_FOREST:
		await _walk_trail(v, n)
		n += 1
	# 6. Night: the glows and the fey motes.
	game.ui.visible = false
	game.rig.focus = Vector2(422, 195)
	game.minute = Rules.NIGHT_AT + 4.0
	await _wait(2.5)
	for v in ["fey_wood", "heartwood", "dark_wood"]:
		var lm: Vector2i = _region(v).landmark_tile
		var e := map.entrance_angle(lm)
		game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y), 1.2), 24.0, 42.0, -90.0 - rad_to_deg(e))
		await _wait(0.6)
		await _shot("%02d_night_%s" % [n, map.terrains[lm]])
		n += 1
	game.minute = 10.0   # midday again, for an overview wider than the game camera allows (screenshot only)
	await _wait(2.5)
	game.set_process(false)   # its zoom limit
	game.rig.max_distance = 140.0
	game.rig.frame(Hex.to3(Vector2(0, 0)), 135.0, 50.0)
	await _wait(0.6)
	await _shot("%02d_overview_wide" % n)
	print("FOREST DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## Walks the party to the region's farthest tile, then along its toward steps into the landmark, and checks the
## hero's route passes along each crossed trail (through the trail's inner end and the edge's middle) and ends at
## the landmark's entrance.
func _walk_trail(v: String, n: int) -> void:
	var map := game.map
	var g := _region(v)
	var lm: Vector2i = g.landmark_tile
	var far: Vector2i = lm
	for t: Vector2i in g.tiles:
		if map.flow_dist.get(t, 0) > map.flow_dist.get(far, 0):
			far = t
	if far != lm:
		game.walk_to(far)
		while game.busy:
			await get_tree().process_frame
	var steps: Array[Vector2i] = []
	var t := far
	while t != lm:
		t = map.flow_toward[t]
		steps.append(t)
	if steps.is_empty():
		_check(true, "%s: region is the landmark alone, no trail to walk" % v)
		return
	var walker := game.party_node
	game.busy = true
	walker.walk(steps)
	await get_tree().process_frame
	# The route's own points (PartyWalker keeps them while walking).
	var route: PackedVector2Array = walker._path
	var ok := true
	var prev := far
	for s in steps:
		var c0 := Hex.tile_position(prev.x, prev.y)
		var c1 := Hex.tile_position(s.x, s.y)
		var dir := (c1 - c0).normalized()
		var marks := [c0 + dir * Rules.TRAIL_INNER, (c0 + c1) * 0.5]
		if s != lm:
			marks.append(c1 - dir * Rules.TRAIL_INNER)
		for m: Vector2 in marks:
			if _nearest(route, m) > 0.3:
				ok = false
				print("  %s: route misses the trail at %s by %.2f m" % [v, m, _nearest(route, m)])
		prev = s
	var e := map.entrance_angle(lm)
	var door := Hex.tile_position(lm.x, lm.y) + Vector2.from_angle(e) * Rules.ENTRANCE_RING
	ok = ok and route[-1].distance_to(door) < 0.3
	_check(ok, "%s: the route follows the trail over %d step(s) to the landmark's entrance" % [v, steps.size()])
	await _wait(1.2)
	if v == "heartwood" or v == "fey_wood":
		game.rig.frame(walker.centre(), 26.0, 50.0)
		await _shot("%02d_walk_%s" % [n, v])
	while walker.walking:
		await get_tree().process_frame
	await _wait(Rules.SETTLE_SECONDS + 0.2)
	game.busy = false
	game.party_tile = lm
	if v == "heartwood":
		var c := Hex.tile_position(lm.x, lm.y)
		game.rig.frame(Hex.to3(c, 1.0), 18.0, 40.0, -90.0 - rad_to_deg(e))
		await _wait(0.4)
		await _shot("%02d_walk_arrived_treeoflife" % n)


static func _nearest(route: PackedVector2Array, p: Vector2) -> float:
	var best := INF
	for q in route:
		best = minf(best, q.distance_to(p))
	return best


## Prints the frame cost of the current view after it settles (like the look tests' `--perf`).
func _perf(what: String) -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	for _f in 60:
		await get_tree().process_frame
	var rs := RenderingServer
	var info := [rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
		rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)]
	var t0 := Time.get_ticks_usec()
	for _f in 120:
		await get_tree().process_frame
	var ms := (Time.get_ticks_usec() - t0) / 120000.0
	print("FOREST PERF %s: draw calls %d, triangles %d, objects %d; %.1f ms a frame on this Mac (vsync off)" % [
		what, info[0], info[1], info[2], ms])
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)
