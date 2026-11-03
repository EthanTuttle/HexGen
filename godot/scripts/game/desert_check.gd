class_name DesertCheck
extends Node
## Checks the desert kit (tiles v60) in the game (`-- --desertcheck`, add `--shots` for screens/desert_*.png): each variant's
## pieces, turns and effects, the canyon's rock, routes, closed walls and lanes, the Stronghold's ramp, the Sphinx's dune, the
## Bazaar and pool, the ripples, the silhouette through rock, generating off the main thread, and a tile added to a finished
## canyon. Prints DESERT OK / DESERT FAIL lines, then DESERT DONE. A test aid only.

var game: Game
var shots := false
var failed := 0


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("DESERT %s: %s" % ["OK" if ok else "FAIL", what])
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
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("desert_%s.png" % name))
		print("SAVED desert_%s" % name)


func _region(variant: String) -> Dictionary:
	for g in game.regions:
		if g.variant == variant:
			return g
	return {}


func _pieces(t: Vector2i) -> Array:
	return game.map.tile_node(t).get_children().filter(func(c): return c is MeshInstance3D and c.has_meta("piece"))


func _piece_names(t: Vector2i) -> Array:
	return _pieces(t).map(func(c): return String(c.get_meta("piece")))


func _middle(g: Dictionary) -> Vector3:
	var at := Vector2.ZERO
	for t: Vector2i in g.tiles:
		at += Hex.tile_position(t.x, t.y)
	return Hex.to3(at / g.tiles.size())


func _run() -> void:
	var map := game.map
	var t0 := Time.get_ticks_msec()
	game.spawn_forest_regions()
	print("DESERT spawn of every debug region took %d ms" % (Time.get_ticks_msec() - t0))
	await _wait(1.0)
	if "--shimmeronly" in OS.get_cmdline_user_args():
		await _shimmer_shows(map)
		get_tree().quit()
		return
	_check_variants(map)
	_check_ripples(map)
	_check_effects(map)
	_check_maze(map)
	_check_rock(map)
	_check_mesas()
	_report_reference()
	await _pictures(map)
	await _perf(map)
	await _shimmer_shows(map)
	await _walk_stronghold(map)
	await _walk_sphinx(map)
	await _walk_oasis(map)
	await _walk_canyon(map)
	await _silhouette(map)
	await _runtime_canyon(map)
	await _wait(1.0)   # the last ray test's frames
	print("DESERT DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _check_variants(map: MapBoard) -> void:
	for v: String in Game.DEBUG_DESERTS:
		_check(not _region(v).is_empty(), "%s: the 12-tile region is on the map" % v)
	var waste := _region("wasteland")
	var sphinx: Vector2i = waste.landmark_tile
	_check(map.terrains[sphinx] == "sandstonesphinx" and "sandstonesphinx_centre" in _piece_names(sphinx), "the Sphinx stands on its tile")
	_check(map.landmark_turns[sphinx] == Sand.sphinx_turn(sphinx, waste.tiles), "the Sphinx turns by sphinx_turn")
	_check(sphinx + Hex.NEIGHBOURS[map.landmark_turns[sphinx]] in waste.tiles, "the Sphinx faces a tile of its region")
	var bad := bad_sand(map, waste)
	_check(bad == 0, "wasteland and Sphinx tiles have sand over a recoloured slab, and no trail pieces (%d bad)" % bad)
	var bad_t := Vector2i.MAX
	for g: Vector2i in map.terrains:
		if map.terrains[g] == "desert" and _piece_names(g).any(func(n): return "trail" in n):
			bad_t = g
	_check(bad_t == Vector2i.MAX, "tier 0 desert has no drawn paths")
	var bad_lands := _region("badlands")
	var fort: Vector2i = bad_lands.landmark_tile
	_check(map.landmark_turns[fort] == DesertLands.STRONGHOLD_TURN, "the Stronghold always turns STRONGHOLD_TURN (3), so its ramp faces the default camera")
	var fort_piece: Array = _pieces(fort).filter(func(c): return c.get_meta("piece") == "raiderstronghold_centre")
	_check(fort_piece.size() == 1 and posmod(roundi(rad_to_deg(fort_piece[0].rotation.y) / 60.0), 6) == 3, "its centre piece is turned 3 steps")
	var feats := 0
	var wide := 0
	for t: Vector2i in bad_lands.tiles:
		for n: String in _piece_names(t):
			if n.begins_with("badlands_mesa_") or n.begins_with("badlands_kite_") or n in ["badlands_butte", "badlands_camp", "badlands_wagon", "badlands_post"]:
				feats += 1
				if n.begins_with("badlands_mesa_") or n.begins_with("badlands_kite_"):
					wide += 1
	_check(feats > 4 and wide > 2, "badlands: %d corner features stand on the region, %d of them wide mesas" % [feats, wide])
	var oasis := _region("oasis")
	var bazaar: Vector2i = oasis.landmark_tile
	var pool: Vector2i = oasis.pool_tile
	_check(map.terrains[bazaar] == "oasisbazaar" and map.terrains[pool] == "oasispool", "the oasis converts two tiles: the Bazaar and the pool")
	_check(Rules.hex_distance(bazaar, pool) == 1, "the pool is next to the Bazaar")
	_check(oasis.tiles.all(func(t): return mini(Rules.hex_distance(t, bazaar), Rules.hex_distance(t, pool)) == map.flow_dist[t]), "oasis tiles thicken toward both")
	var near: Array = oasis.tiles.filter(func(t): return map.flow_dist[t] == 1)
	_check(near.all(func(t): return "oasis_centre_near" in _piece_names(t)), "camels only on the tiles next to the pool and Bazaar (%d)" % near.size())
	_check(oasis.tiles.filter(func(t): return map.flow_dist[t] > 1).all(func(t): return not "oasis_centre_near" in _piece_names(t)), "open sand elsewhere")
	var canyon := _region("canyon")
	_check(map.landmark_turns[canyon.landmark_tile] == Sand.sphinx_turn(canyon.landmark_tile, canyon.tiles), "the Echo Cave turns by sphinx_turn")
	var pieces := 0
	for t: Vector2i in canyon.tiles:
		pieces += _pieces(t).size()
	_check(pieces == 0, "a canyon tile has no kit pieces and no slab: its rock is the ground")
	_check(canyon.tiles.all(func(t): return map.tile_node(t).get_node_or_null("canyon") != null), "every canyon tile has its piece of the generated rock")


func bad_sand(map: MapBoard, g: Dictionary) -> int:
	var bad := 0
	for t: Vector2i in g.tiles:
		var names := _piece_names(t)
		if map.tile_node(t).get_node_or_null("sand") == null or not "base_desert" in names or names.any(func(n): return "trail" in n):
			bad += 1
	return bad


func _check_ripples(map: MapBoard) -> void:
	var g := _region("oasis")
	var total := 0
	var ok := true
	for t: Vector2i in g.tiles:
		var node := map.tile_node(t).get_node_or_null("ripples")
		var name: String = map.terrains[t]
		if name != "oasis":
			ok = ok and node == null
		else:
			for r in DesertLands.oasis_ripples(map.terrains, t):
				total += 1
				ok = ok and GroundCover.tile_at(Vector2(r[0], r[1])) == t
	_check(ok and total > 30, "oasis ripples: %d, in world space, none on the pool's or Bazaar's tile" % total)
	var a := DesertLands.oasis_ripples(map.terrains, g.tiles[0] if map.terrains[g.tiles[0]] == "oasis" else g.tiles[1])
	var extra := map.terrains.duplicate()
	extra[Vector2i(Rules.MAP_LIMIT, Rules.MAP_LIMIT)] = "oasis"
	var b := DesertLands.oasis_ripples(extra, g.tiles[0] if map.terrains[g.tiles[0]] == "oasis" else g.tiles[1])
	_check(a == b, "a tile placed far away doesn't move any ripple")


func _check_effects(map: MapBoard) -> void:
	for v: String in ["badlands", "oasis"]:
		var g := _region(v)
		var count := 0
		var plain := 0
		for t: Vector2i in g.tiles:
			if map.terrains[t] == v:
				plain += 1
				if map.tile_node(t).find_children("shimmer", "MeshInstance3D", true, false).size() == 1:
					count += 1
		_check(count == plain and plain > 0, "%s: shimmer on all %d open tiles" % [v, plain])
	var o := _region("oasis")
	for t: Vector2i in [o.landmark_tile, o.pool_tile]:
		_check(map.tile_node(t).find_children("glint", "Node3D", true, false).size() == 1, "%s: a glint" % map.terrains[t])
	var fx: Array = map.tile_node(_region("badlands").landmark_tile).find_children("*", "GPUParticles3D", true, false)
	_check(fx.size() == 2, "the Stronghold has its fire and smoke")
	DesertFx.set_night(1.0)
	_check(is_equal_approx(DesertFx._glow_mat.get_shader_parameter("strength"), 1.0) and is_zero_approx(DesertFx._shimmer_mat.get_shader_parameter("strength")), "at night the water glows and the heat waves stop")
	DesertFx.set_night(0.0)


func _check_maze(map: MapBoard) -> void:
	var g := _region("canyon")
	var lm: Vector2i = g.landmark_tile
	var c: Dictionary = map.canyons[lm]
	var ways := 0
	for i in 6:
		if map.canyon_open(lm, i):
			ways += 1
	_check(ways == 1 and map.canyon_open(lm, c.turn), "the Echo Cave has one way in, the edge it faces")
	var closed := 0
	var shared := 0
	for t: Vector2i in g.tiles:
		for i in 6:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if map.canyons.has(n):
				shared += 1
				_check_edge_same(map, t, n, i)
				if not map.edge_open(t, n):
					closed += 1
	_check(closed > 0, "%d of %d shared edge sides are rock, and can't be crossed" % [closed, shared])
	var ring := 0
	var open_out := 0
	for t: Vector2i in g.tiles:
		for i in 6:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if not map.canyons.has(n) and map.terrains.has(n):
				ring += 1
				if map.edge_open(n, t):
					open_out += 1
	_check(open_out == c.entrances.size(), "only the %d entrances open onto the land round it (%d edges face out)" % [open_out, ring])
	# Every tile can be reached from the land outside, by walking through open edges only.
	var outside: Vector2i = g.tiles[0]
	for e: Vector3i in c.entrances:
		outside = Vector2i(e.x, e.y) + Hex.NEIGHBOURS[e.z]
		break
	var seen := {outside: true}
	var todo: Array[Vector2i] = [outside]
	while not todo.is_empty():
		var t: Vector2i = todo.pop_back()
		for n in Hex.NEIGHBOURS:
			var m: Vector2i = t + n
			if map.terrains.has(m) and not seen.has(m) and map.edge_open(t, m):
				seen[m] = true
				todo.append(m)
	_check(g.tiles.all(func(t): return seen.has(t)), "every canyon tile can be walked to from outside")
	var dead: Array = g.tiles.filter(func(t): return range(6).filter(func(i): return map.canyon_open(t, i)).size() == 1)
	print("DESERT canyon: %d tiles, %d entrances, %d dead ends" % [g.tiles.size(), c.entrances.size(), dead.size()])
	# Each tile's graph has its open edges and meets at the junction, with no way out by a closed edge.
	var ok := true
	for t: Vector2i in g.tiles:
		var graph := map.path_graph(t)
		for i in 6:
			ok = ok and graph.edge_node.has(i) == map.canyon_open(t, i)
			if graph.edge_node.has(i):
				ok = ok and not graph.route(graph.edge_node[i], graph.stand).is_empty()
	_check(ok, "each tile's corridors run from its open edges to its junction, and none from a closed one")


func _check_edge_same(map: MapBoard, t: Vector2i, n: Vector2i, i: int) -> void:
	if map.canyon_open(t, i) != map.canyon_open(n, (i + 3) % 6):
		_check(false, "edge %s %d: both tiles must agree" % [t, i])


## Rays against the rock's triangles (a temporary shape, not kept): no holes, a floor under every corridor, lanes that
## meet the land at the top and the floor at the foot.
func _check_rock(map: MapBoard) -> void:
	var g := _region("canyon")
	var body := StaticBody3D.new()
	body.collision_layer = 1 << 9
	var faces := PackedVector3Array()
	for t: Vector2i in g.tiles:
		var mi: MeshInstance3D = map.tile_node(t).get_node("canyon")
		var at: Vector3 = mi.global_position
		var v: PackedVector3Array = mi.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		for q in v:
			faces.append(q + at)
	var cs := CollisionShape3D.new()
	var shape := ConcavePolygonShape3D.new()
	shape.set_faces(faces)
	cs.shape = shape
	body.add_child(cs)
	add_child(body)
	# Colliders in the physics server only take effect next step, so the rest is deferred a frame.
	_rock_rays.call_deferred(map, g, body)


func _rock_rays(map: MapBoard, g: Dictionary, body: StaticBody3D) -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	var space := body.get_world_3d().direct_space_state
	var ray := func(p: Vector2) -> float:
		var q := PhysicsRayQueryParameters3D.create(Hex.to3(p, 20.0), Hex.to3(p, -5.0), 1 << 9)
		var hit := space.intersect_ray(q)
		return (hit.position as Vector3).y if not hit.is_empty() else NAN
	var holes := 0
	var rays := 0
	var low := INF
	var high := -INF
	for t: Vector2i in g.tiles:
		var c := Hex.tile_position(t.x, t.y)
		for ix in range(-20, 21):
			for iy in range(-22, 23):
				var q := c + Vector2(ix * 0.2 + 0.013, iy * 0.2 + 0.017)
				if GroundCover.tile_at(q) != t:
					continue
				rays += 1
				var y: float = ray.call(q)
				if is_nan(y):
					holes += 1
				else:
					low = minf(low, y)
					high = maxf(high, y)
	_check(holes == 0, "no holes: %d rays straight down, %d miss; heights %.2f to %.2f" % [rays, holes, low, high])
	_check(absf(low - Canyon.FLOOR) < 0.01, "the floor is at %.2f" % Canyon.FLOOR)
	var c: Dictionary = map.canyons[g.landmark_tile]
	var unjoined := 0
	var off_lane := 0.0
	var steep := 0.0
	for e: Vector3i in c.entrances:
		var t := Vector2i(e.x, e.y)
		var at := Hex.tile_position(t.x, t.y)
		var line := Canyon.ramp_line(t, e.z, c.landmark, c.turn)
		var top := at + Vector2(line[0].x, line[0].y) - Water.normal(e.z) * 0.1
		var foot := at + Vector2(line[-1].x, line[-1].y)
		if absf(ray.call(top) - map.walk_z(top)) > 0.12 or absf(ray.call(foot) - Canyon.FLOOR) > 0.05:
			unjoined += 1
		for k in range(1, line.size()):
			var d := Vector2(line[k].x, line[k].y).distance_to(Vector2(line[k - 1].x, line[k - 1].y))
			if d > 1e-4:
				steep = maxf(steep, rad_to_deg(atan2(absf(line[k].z - line[k - 1].z), d)))
			for u in 8:
				var q := Vector3(line[k - 1]).lerp(line[k], u / 8.0)
				off_lane = maxf(off_lane, absf(ray.call(at + Vector2(q.x, q.y)) - q.z))
	_check(unjoined == 0, "every lane meets the land at its top and the floor at its foot (%d of %d don't)" % [unjoined, c.entrances.size()])
	_check(off_lane < 0.12, "the route walks on the lane's path, within %.3f m" % off_lane)
	_check(steep < 28.0, "the steepest lane is %.1f degrees; the minis' limit is 28" % steep)
	var over := 0
	var samples := 0
	var worst := 0.0
	for t: Vector2i in g.tiles:
		var graph := map.path_graph(t)
		for a in graph.links:
			for b in graph.links[a]:
				if a < b:
					for u in 8:
						var q := graph.nodes[a].lerp(graph.nodes[b], u / 7.0)
						var y: float = ray.call(q)
						var want := map.walk_z(q)
						samples += 1
						if absf(y - want) > 0.1:
							over += 1
							worst = maxf(worst, y - want)
	_check(over == 0, "the ground under every corridor is what the party walks at: %d of %d samples differ, by up to %.2f" % [over, samples, worst])
	body.queue_free()


## The art's 12-tile preview region, so its count can be set against the hand-off's 41,439.
func _report_reference() -> void:
	var region: Array = [Vector2i(0, 0)]
	region.append_array(Hex.NEIGHBOURS)
	region.append_array([Vector2i(1, 1), Vector2i(2, -1), Vector2i(1, -2), Vector2i(-1, 2), Vector2i(-2, 1)])
	var lm := Vector2i(1, 0)
	var turn := Sand.sphinx_turn(lm, region)
	var times := []
	var r := {}
	for _k in 3:
		var t0 := Time.get_ticks_usec()
		r = Canyon.generate(region, lm, turn, 7.0)
		times.append((Time.get_ticks_usec() - t0) / 1000.0)
	var worst := 0
	for t: Vector2i in r.per_tile:
		worst = maxi(worst, r.per_tile[t])
	print("DESERT PERF the art's 12-tile region: %d triangles, %d a tile, worst tile %d (hand-off: 41,439, about 3,450 a tile, worst 3,984 before the lanes' last change, budget 4,816)" % [r.triangles, r.triangles / region.size(), worst])
	print("DESERT PERF generating it in GDScript on this Mac: field %d ms, mesh %d ms; three runs %s ms (plain Python: about 450 ms)" % [r.field_ms, r.mesh_ms, str(times.map(func(x): return int(x)))])
	_check(worst <= 4816, "the worst canyon tile (%d) is inside deep forest's 4,816" % worst)
	var budget := []
	for t: Vector2i in game.map.terrains:
		if game.map.terrains[t] in ["wasteland", "sandstonesphinx", "desert", "badlands", "raiderstronghold", "oasis", "oasisbazaar", "oasispool"]:
			var n := 0
			for mi in game.map.tile_node(t).find_children("*", "MeshInstance3D", true, false):
				if mi.mesh is ArrayMesh or mi.mesh is PrimitiveMesh:
					n += _tris(mi.mesh)
			budget.append([n, game.map.terrains[t]])
	budget.sort()
	if not budget.is_empty():
		print("DESERT PERF worst other desert tile on these maps: %d triangles (%s)" % budget[-1])


static func _tris(m: Mesh) -> int:
	var n := 0
	for k in m.get_surface_count():
		var a := m.surface_get_arrays(k)
		var idx = a[Mesh.ARRAY_INDEX]
		n += (idx.size() if idx is PackedInt32Array and idx.size() > 0 else (a[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()) / 3
	return n


func _pictures(_map: MapBoard) -> void:
	var n := 1
	for v: String in ["wasteland", "badlands", "oasis", "canyon"]:
		game.rig.frame(_middle(_region(v)), 58.0, 50.0)
		await _wait(0.8)
		await _shot("%02d_game_camera_%s" % [n, v])
		n += 1
	var focus := game.rig.focus
	game.ui.visible = false
	game.rig.focus = Vector2(422, 195)
	var canyon := _region("canyon")
	game.rig.frame(_middle(canyon), 62.0, 50.0)
	await _wait(0.5)
	await _shot("%02d_canyon_map" % n); n += 1
	game.rig.frame(_middle(canyon), 62.0, 50.0, 90.0)
	await _wait(0.5)
	await _shot("%02d_canyon_turned" % n); n += 1
	game.rig.frame(_middle(canyon), 24.0, 28.0, 30.0)
	await _wait(0.5)
	await _shot("%02d_canyon_low" % n); n += 1
	var lm: Vector2i = canyon.landmark_tile
	var turn: int = game.map.landmark_turns[lm]
	game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y), -1.2), 14.0, 30.0, -90.0 - 60.0 * turn)
	await _wait(0.5)
	await _shot("%02d_echo_cave" % n); n += 1
	var c: Dictionary = game.map.canyons[lm]
	for k in mini(2, c.entrances.size()):
		var e: Vector3i = c.entrances[k]
		var at := Hex.tile_position(e.x, e.y) + Water.normal(e.z) * 2.6
		game.rig.frame(Hex.to3(at, -0.8), 13.0, 34.0, -90.0)
		await _wait(0.5)
		await _shot("%02d_lane_%d" % [n, k]); n += 1
	var fort: Vector2i = _region("badlands").landmark_tile
	game.rig.frame(Hex.to3(Hex.tile_position(fort.x, fort.y), 1.0), 17.0, 30.0, 0.0)
	await _wait(0.5)
	await _shot("%02d_stronghold" % n); n += 1
	var sphinx: Vector2i = _region("wasteland").landmark_tile
	game.rig.frame(Hex.to3(Hex.tile_position(sphinx.x, sphinx.y), 1.5), 18.0, 32.0, -90.0 - 60.0 * game.map.landmark_turns[sphinx])
	await _wait(0.5)
	await _shot("%02d_sphinx" % n); n += 1
	var oasis := _region("oasis")
	game.rig.frame(Hex.to3(Hex.tile_position(oasis.pool_tile.x, oasis.pool_tile.y)), 22.0, 42.0)
	await _wait(1.0)
	await _shot("%02d_oasis_pool" % n); n += 1
	game.rig.frame(Hex.to3(Hex.tile_position(oasis.landmark_tile.x, oasis.landmark_tile.y), 0.8), 18.0, 38.0)
	await _wait(0.5)
	await _shot("%02d_oasis_bazaar" % n); n += 1
	game.rig.frame(_middle(_region("badlands")), 40.0, 50.0)
	await _wait(0.5)
	await _shot("%02d_badlands_map" % n); n += 1
	var t0_tile := Vector2i.MAX
	for t: Vector2i in game.map.terrains:
		if game.map.terrains[t] == "desert":
			t0_tile = t
			break
	game.rig.frame(Hex.to3(Hex.tile_position(t0_tile.x, t0_tile.y)), 30.0, 50.0)
	await _wait(0.5)
	await _shot("%02d_tier0_desert" % n); n += 1
	game.ui.visible = true
	game.rig.focus = focus


func _perf(_map: MapBoard) -> void:
	var vsync := DisplayServer.window_get_vsync_mode()
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	for view in [["canyon", 58.0], ["badlands", 58.0], ["oasis", 58.0], ["wasteland", 58.0], ["canyon", 100.0]]:
		game.rig.frame(_middle(_region(view[0])), view[1], 50.0)
		await _wait(0.6)
		var t0 := Time.get_ticks_usec()
		for _f in 120:
			await get_tree().process_frame
		print("DESERT PERF %s at distance %d, HUD on: draw calls %d, triangles %d, objects %d; %.1f ms a frame on this Mac (vsync off)" % [
				view[0], int(view[1]),
				Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
				Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
				Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
				(Time.get_ticks_usec() - t0) / 120000.0])
	DisplayServer.window_set_vsync_mode(vsync)


## Heat waves bend what's behind them by day, and leave no shape of their own when they're at rest.
func _shimmer_shows(map: MapBoard) -> void:
	var g := _region("badlands")
	game.ui.visible = false
	game.rig.frame(_middle(g), 34.0, 40.0)
	await _wait(0.3)
	var nodes := []
	for t: Vector2i in g.tiles:
		nodes.append_array(map.tile_node(t).find_children("shimmer", "MeshInstance3D", true, false))
	var by_day := await _grab()
	for n in nodes:
		n.visible = false
	var without := await _grab()
	for n in nodes:
		n.visible = true
	DesertFx.set_night(1.0)
	DesertFx.test_hold = true   # the map sets these from the clock every frame
	var resting := await _grab()
	DesertFx.test_hold = false
	DesertFx.set_night(0.0)
	for n in nodes:
		n.visible = false
	var without_b := await _grab()
	for n in nodes:
		n.visible = true
	if shots:
		var dir := ProjectSettings.globalize_path("res://screens")
		by_day.save_png(dir.path_join("desert_33_shimmer_on.png"))
		without.save_png(dir.path_join("desert_34_shimmer_off.png"))
		resting.save_png(dir.path_join("desert_35_shimmer_at_rest.png"))
	var noise := _differs(without, without_b)   # fire and smoke move between frames whatever the heat does
	var bent := _differs(by_day, without)
	var shape := _differs(resting, without_b)
	_check(bent > noise + 200, "by day the heat waves bend the view: %d pixels change, against %d from fire and smoke" % [bent, noise])
	_check(shape <= noise * 2 + 50, "and leave no shape of their own at rest: %d pixels change" % shape)
	game.ui.visible = true


## Walks to `goal` and watches every mini: `each` is called with the map height the route says, per mini per frame.
func _walk_to(goal: Vector2i) -> void:
	if goal == game.party_tile:
		return
	game.walk_to(goal)
	while game.busy:
		await get_tree().process_frame
	await _wait(Rules.SETTLE_SECONDS)


## The party hops to tile t for a walk's start (the check's roads are long).
func _start_at(t: Vector2i) -> void:
	game.party_tile = t
	game.party_node.place_at(t)
	game.rig.player_moved = false
	game.rig.frame(game.party_node.centre(), 24.0, 45.0)
	await _wait(0.3)


## Plains next to a region, on the side of `edge_tile`.
func _outside(map: MapBoard, g: Dictionary) -> Vector2i:
	for t: Vector2i in g.tiles:
		for n in Hex.NEIGHBOURS:
			var m: Vector2i = t + n
			if not m in g.tiles and map.terrains.get(m) == "plains":
				return m
	return g.tiles[0]


## Follows every mini through a walk: worst gap between its height and the ground's, its worst tilt, and how many frames it was
## at all. ground: the height a mini at plan point p should stand at.
func _follow(goal: Vector2i, ground: Callable, shot := "") -> Dictionary:
	var out := {gap = 0.0, tilt = 0.0, frames = 0, highest = -INF, lowest = INF, shot_done = false}
	game.walk_to(goal)
	while game.busy:
		await get_tree().process_frame
		for m in game.party_node.members:
			var node: Node3D = m.node
			var p := Vector2(node.position.x, -node.position.z)
			var want: float = ground.call(p)
			out.gap = maxf(out.gap, absf(node.position.y - want))
			out.tilt = maxf(out.tilt, rad_to_deg((m.up as Vector3).angle_to(Vector3.UP)))
			out.highest = maxf(out.highest, node.position.y)
			out.lowest = minf(out.lowest, node.position.y)
			out.frames += 1
		if shot != "" and not out.shot_done and game.party_node.members[0].node.position.y > 1.2:
			out.shot_done = true
			await _shot(shot)
	await _wait(Rules.SETTLE_SECONDS)
	return out


func _walk_stronghold(map: MapBoard) -> void:
	var g := _region("badlands")
	var fort: Vector2i = g.landmark_tile
	var outside := _outside(map, g)
	await _start_at(outside)
	var r := await _follow(fort, func(p): return map.walk_z(p) if not is_nan(map.walk_z(p)) else 0.0, "20_on_the_ramp")
	var hero: Node3D = game.party_node.members[0].node
	var at := Hex.tile_position(fort.x, fort.y)
	var stop := Water.turned(DesertLands.FORT_GATE, DesertLands.STRONGHOLD_TURN) + at
	_check(game.party_tile == fort, "the party reached the Raider Stronghold")
	_check(Vector2(hero.position.x, -hero.position.z).distance_to(stop) < 0.3, "the hero stops in the gate")
	_check(absf(hero.position.y - DesertLands.MESA_H) < 0.1, "on the mesa's top, at %.2f" % hero.position.y)
	_check(r.gap < 0.2, "every mini follows the route's height on the ramp, within %.3f m" % r.gap)
	_check(r.tilt < 28.0, "the steepest a base tilts on the ramp is %.1f degrees (the ramp's 25.8)" % r.tilt)
	game.ui.visible = false
	game.rig.frame(Hex.to3(stop, DesertLands.MESA_H), 12.0, 32.0, 0.0)
	await _wait(0.5)
	await _shot("21_at_the_gate")
	game.ui.visible = true
	var away := await _follow(outside, func(p): return map.walk_z(p) if not is_nan(map.walk_z(p)) else 0.0)
	_check(away.gap < 0.2 and absf(hero.position.y) < 0.05, "and walks back down and out (gap %.3f, height %.3f)" % [away.gap, hero.position.y])
	# Through the tile without stopping: round the mesa at ground level.
	var ok := true
	var graph := map.path_graph(fort)
	for a in 6:
		for b in 6:
			if a != b:
				var way := graph.route(graph.edge_node[a], graph.edge_node[b])
				for q in way:
					if map.walk_z(q) >= 0.2:
						ok = false
						print("DESERT up the ramp: edge %d to %d at %s, height %.2f" % [a, b, Water.turned(q - Hex.tile_position(fort.x, fort.y), -DesertLands.STRONGHOLD_TURN), map.walk_z(q)])
						break
	_check(ok, "walking through the tile keeps to the ground round the mesa")


func _walk_sphinx(map: MapBoard) -> void:
	var g := _region("wasteland")
	var lm: Vector2i = g.landmark_tile
	var turn: int = map.landmark_turns[lm]
	await _start_at(_outside(map, g))
	var sand_at := func(p: Vector2) -> float:
		var t := GroundCover.tile_at(p)
		return Sand.surface_z(map.terrains, t, p.x, p.y, map.landmark_turns.get(t, 0)) if map.terrains.get(t) in Sand.LOOKS else 0.0
	var r := await _follow(lm, sand_at)
	var at := Hex.tile_position(lm.x, lm.y)
	var hero: Node3D = game.party_node.members[0].node
	_check(game.party_tile == lm, "the party reached the Sphinx")
	_check(Vector2(hero.position.x, -hero.position.z).distance_to(at + Water.turned(Sand.SPHINX_STOP, turn)) < 0.3, "the hero stops before the altar")
	_check(r.gap < 0.45, "minis follow the sand, within %.3f m (a base sits on the highest ground under it)" % r.gap)
	_check(r.tilt <= Rules.MAX_TILT_DEG + 0.1, "the steepest a base tilts on the way is %.1f degrees" % r.tilt)
	game.ui.visible = false
	game.rig.frame(Hex.to3(at + Water.turned(Sand.SPHINX_STOP, turn), 1.0), 13.0, 25.0, -90.0 - 60.0 * turn)
	await _wait(0.5)
	await _shot("22_at_the_sphinx")
	game.ui.visible = true


func _walk_oasis(map: MapBoard) -> void:
	var g := _region("oasis")
	await _start_at(_outside(map, g))
	var pool: Vector2i = g.pool_tile
	var at := Hex.tile_position(pool.x, pool.y)
	var route := game.party_node.route_preview(game.path_to(pool))
	var nearest := INF
	for p in route:
		nearest = minf(nearest, p.distance_to(at))
	_check(nearest > DesertLands.POOL_RING - 0.25, "the way to the pool keeps round it, %.2f m from its middle" % nearest)
	await _walk_to(pool)
	_check(game.party_tile == pool, "the party reached the pool's tile")
	var dry := true
	for m in game.party_node.members:
		var p := Vector2(m.node.position.x, -m.node.position.z)
		dry = dry and p.distance_to(at) > DesertLands.POOL_RING - 0.3
	_check(dry, "the party stands on the ring, out of the water")
	game.ui.visible = false
	game.rig.frame(game.party_node.centre(), 14.0, 36.0)
	await _wait(0.5)
	await _shot("23_at_the_pool")
	game.ui.visible = true
	var bazaar: Vector2i = g.landmark_tile
	await _walk_to(bazaar)
	var b_at := Hex.tile_position(bazaar.x, bazaar.y)
	var hero: Node3D = game.party_node.members[0].node
	_check(game.party_tile == bazaar and Vector2(hero.position.x, -hero.position.z).distance_to(b_at + Water.turned(Vector2(DesertLands.BAZAAR_RING, 0), map.landmark_turns[bazaar])) < 0.3, "the hero stops at the well-house")
	var clear := true
	for m in game.party_node.members:
		var p := Vector2(m.node.position.x, -m.node.position.z)
		clear = clear and (GroundCover.tile_at(p) != bazaar or p.distance_to(b_at) > DesertLands.BAZAAR_RING - 0.25)
	_check(clear, "nobody stands in the well-house")
	game.ui.visible = false
	game.rig.frame(game.party_node.centre(), 12.0, 40.0)
	await _wait(0.5)
	await _shot("24_at_the_bazaar")
	game.ui.visible = true


func _walk_canyon(map: MapBoard) -> void:
	var g := _region("canyon")
	var lm: Vector2i = g.landmark_tile
	var c: Dictionary = map.canyons[lm]
	var e: Vector3i = c.entrances[0]
	var mouth := Vector2i(e.x, e.y)
	var outside: Vector2i = mouth + Hex.NEIGHBOURS[e.z]
	await _start_at(outside)
	var path := game.path_to(lm)
	var ok := true
	var from := outside
	for t in path:
		ok = ok and map.edge_open(from, t)
		from = t
	_check(ok and path[-1] == lm, "the walk to the Echo Cave (%d tiles) crosses only open edges" % path.size())
	var height := func(p: Vector2) -> float:
		return map.walk_z(p) if not is_nan(map.walk_z(p)) else 0.0
	var r := await _follow(lm, height)
	var at := Hex.tile_position(lm.x, lm.y)
	var hero: Node3D = game.party_node.members[0].node
	_check(game.party_tile == lm, "the party reached the Echo Cave")
	_check(Vector2(hero.position.x, -hero.position.z).distance_to(at + Water.turned(Canyon.STOP, c.turn)) < 0.3, "the hero stops at the cave's stop")
	_check(absf(hero.position.y - Canyon.FLOOR) < 0.05, "on the floor, at %.2f" % hero.position.y)
	_check(r.gap < 0.15, "every mini stays on the lane or floor all the way, within %.3f m" % r.gap)
	_check(r.tilt < 28.5, "the steepest a base tilts on a lane is %.1f degrees" % r.tilt)
	var inside := true
	for m in game.party_node.members:
		var p := Vector2(m.node.position.x, -m.node.position.z)
		inside = inside and map.path_graph(GroundCover.tile_at(p)).distance_to_paths(p) < 0.15 if map.canyons.has(GroundCover.tile_at(p)) else inside
	_check(inside, "the stopped party stands on its corridors")
	game.rig.player_moved = false
	game.ui.visible = false
	game.rig.frame(game.party_node.centre(), 14.0, 40.0)
	await _wait(0.5)
	await _shot("25_at_the_echo_cave")
	game.ui.visible = true
	# A fight there brings it back to the floor, not to height 0.
	game.party_node.place_at(lm)
	_check(absf(game.party_node.members[0].node.position.y - Canyon.FLOOR) < 0.05 and game.party_node.members.all(func(m): return m.node.position.y < -1.5), "placed back on its tile (after a fight), it's on the floor")
	# All the way round: to every tile and out again.
	var bad_gap := 0.0
	var visited := 0
	var tilted := 0.0
	var tour: Array = g.tiles.duplicate()
	tour.sort_custom(func(a, b): return Rules.hex_distance(a, lm) < Rules.hex_distance(b, lm))
	for t: Vector2i in tour:
		if t == game.party_tile:
			continue
		var w := await _follow(t, height)
		bad_gap = maxf(bad_gap, w.gap)
		tilted = maxf(tilted, w.tilt)
		visited += 1 if game.party_tile == t else 0
	_check(visited == tour.size() - 1, "the party walked to all %d other tiles of the maze" % (tour.size() - 1))
	_check(bad_gap < 0.15 and tilted < 28.5, "on every tile, within %.3f m of the ground and %.1f degrees" % [bad_gap, tilted])
	var w := await _follow(outside, height)
	_check(game.party_tile == outside and absf(game.party_node.members[0].node.position.y) < 0.2, "and out by an entrance, back at ground level (gap %.3f)" % w.gap)


## The silhouette through rock: on in a canyon, off outside; changes pixels in a turned view, none in a view with nothing in front.
func _silhouette(map: MapBoard) -> void:
	var g := _region("canyon")
	var body: MeshInstance3D = game.party_node.members[0].body
	await _wait(0.2)
	_check(body.material_overlay == null, "no silhouette pass outside a canyon")
	game.party_tile = g.landmark_tile
	game.party_node.place_at(g.landmark_tile)
	await _wait(0.1)
	_check(body.material_overlay != null, "the silhouette pass is on in a canyon")
	game.ui.visible = false
	var hero := game.party_node.centre()
	# From behind the wall behind the party: a camera that sees rock in front of the minis.
	var best := -1
	var angle_best := 0.0
	var plain_best: Image = null
	var drawn_best: Image = null
	for k in 12:
		var yaw := k * 30.0
		game.rig.frame(hero, 11.0, 32.0, yaw)
		await _wait(0.1)
		var drawn := await _grab()
		for m in game.party_node.members:
			(m.body as MeshInstance3D).material_overlay = null
		var plain := await _grab()
		for m in game.party_node.members:
			(m.body as MeshInstance3D).material_overlay = game.party_node._silhouette
		var n := _differs(drawn, plain)
		if n > best:
			best = n
			angle_best = yaw
			plain_best = plain
			drawn_best = drawn
	_check(best > 30, "turned so rock hides the party, the silhouette shows: %d pixels change (yaw %d)" % [best, int(angle_best)])
	var flat := _flat_share(drawn_best, plain_best)
	_check(flat > 0.95, "the silhouette is one flat colour: %.1f%% of its pixels" % (flat * 100.0))
	# A view where the party's in plain sight: nothing shows through itself.
	var clear_view := -1
	game.rig.frame(hero, 11.0, 75.0)
	await _wait(0.2)
	var drawn_top := await _grab()
	for m in game.party_node.members:
		(m.body as MeshInstance3D).material_overlay = null
	var plain_top := await _grab()
	for m in game.party_node.members:
		(m.body as MeshInstance3D).material_overlay = game.party_node._silhouette
	clear_view = _differs(drawn_top, plain_top)
	_check(clear_view < 20, "from above, with nothing in front, no inner parts show: %d pixels change" % clear_view)
	game.rig.frame(hero, 11.0, 32.0, angle_best)
	await _wait(0.2)
	await _shot("30_silhouette_on")
	if shots and plain_best:
		plain_best.save_png(ProjectSettings.globalize_path("res://screens").path_join("desert_31_silhouette_off.png"))
	# Default camera on a corridor: the rock is held low, so little's hidden.
	game.rig.frame(hero, 16.0, 50.0)
	await _wait(0.2)
	await _shot("32_default_camera_in_the_canyon")
	game.ui.visible = true


## Of the pixels that differ between two pictures, the share in the first that are the commonest colour among them.
static func _flat_share(a: Image, b: Image) -> float:
	var counts := {}
	var total := 0
	for y in range(0, a.get_height(), 2):
		for x in range(0, a.get_width(), 2):
			var p := a.get_pixel(x, y)
			var q := b.get_pixel(x, y)
			if absf(p.r - q.r) + absf(p.g - q.g) + absf(p.b - q.b) > 0.1:
				total += 1
				var key := Vector3i(roundi(p.r * 64.0), roundi(p.g * 64.0), roundi(p.b * 64.0))
				counts[key] = counts.get(key, 0) + 1
	var most := 0
	for k in counts:
		most = maxi(most, counts[k])
	return float(most) / maxi(total, 1)


func _grab() -> Image:
	for _f in 2:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	return game.get_viewport().get_texture().get_image()


static func _differs(a: Image, b: Image) -> int:
	var n := 0
	for y in range(0, a.get_height(), 2):
		for x in range(0, a.get_width(), 2):
			var p := a.get_pixel(x, y)
			var q := b.get_pixel(x, y)
			if absf(p.r - q.r) + absf(p.g - q.g) + absf(p.b - q.b) > 0.1:
				n += 1
	return n


## A canyon generated off the main thread while the game runs, the party standing on one of its tiles, then tiles added.
func _runtime_canyon(map: MapBoard) -> void:
	var anchor := game._free_spot(Game.DEBUG_PLAINS_SHAPE, {})
	var tiles: Array[Vector2i] = []
	for s: Vector2i in Game.DEBUG_PLAINS_SHAPE:
		tiles.append(anchor + s)
	var old := tiles.duplicate()   # the region's own list grows when a tile joins
	var changes := {}
	for t: Vector2i in tiles:
		changes[t] = "desert"
		game.order[t] = game.order.size()
	map.retile(changes)
	game.party_tile = tiles[3]
	game.party_node.place_at(tiles[3])
	var region := game.new_region("desert", tiles, "canyon", tiles[0])
	var worst := 0.0
	var worst_after := 0.0
	var frames := 0
	var before := map.canyon_stats.size()
	var t0 := Time.get_ticks_msec()
	game.rig.frame(Hex.to3(Hex.tile_position(anchor.x, anchor.y)), 58.0, 50.0)
	game._transform(tiles, region, tiles[0])
	var last := Time.get_ticks_usec()
	var generating := true
	var gen_ms := 0.0
	while game.busy:
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		var d := (now - last) / 1000.0
		last = now
		frames += 1
		if generating and map.canyon_stats.size() > before:
			generating = false
			gen_ms = Time.get_ticks_msec() - t0
			worst_after = maxf(worst_after, d)
		elif generating:
			worst = maxf(worst, d)
		else:
			worst_after = maxf(worst_after, d)
	var st: Dictionary = map.canyon_stats[-1]
	print("DESERT PERF a canyon finishing in play on this Mac: %d triangles; field %d ms and mesh %d ms off the main thread, commit %d ms on it; worst frame while generating %.1f ms; worst frame at the swap, with the retile, %.1f ms; %d frames in all, %d ms" % [
			st.triangles, st.field_ms, st.mesh_ms, st.commit_ms, worst, worst_after, frames, Time.get_ticks_msec() - t0])
	_check(worst < 40.0, "generating off the main thread keeps frames short: worst %.1f ms" % worst)
	_check(tiles.all(func(t): return Variants.is_canyon(map.terrains[t])), "the tiles turned to canyon")
	await _wait(0.2)
	var y: float = game.party_node.members[0].node.position.y
	_check(absf(y - Canyon.FLOOR) < 0.2, "a party standing on the region goes down to the floor (%.2f)" % y)
	await _grow_in_play(map, region, old)
	_grow_cases()


## A tile added to the finished canyon in play (DOCS: design/02 -> Canyon walls): the maze stays fixed, only touching tiles rebuild.
func _grow_in_play(map: MapBoard, region: Dictionary, old: Array) -> void:
	game.minute = Rules.START_MINUTE   # by day, for the shots
	game._shown_minute = -1.0
	var lm: Vector2i = region.landmark_tile
	var maze_before: Dictionary = map.canyons[lm].openset.duplicate()
	var doors_before: Array = map.canyons[lm].entrances.duplicate()
	var meshes := {}
	for t: Vector2i in old:
		meshes[t] = map._canyon_meshes[t]
	# West or south of the region, to test the anchored grid, on a tile that touches an old entrance if it can.
	var slots := []
	for t: Vector2i in old:
		for n in Hex.NEIGHBOURS:
			if not map.terrains.has(t + n) and not (t + n) in slots:
				slots.append(t + n)
	slots.sort_custom(func(a, b): return Hex.tile_position(a.x, a.y).x < Hex.tile_position(b.x, b.y).x)
	var add: Vector2i = slots[0]
	var party_on: Vector2i = game.party_tile
	var party_y: float = game.party_node.members[0].node.position.y
	var worst := await _place_and_time(map, add, region)
	var info: Dictionary = map.canyons[lm]
	_check(add in region.tiles and Variants.is_canyon(map.terrains[add]), "a tile added to a finished canyon joins it and turns to canyon, %s, west of the rest" % add)
	var kept := true
	for key in maze_before:
		kept = kept and info.openset.has(key)
	_check(kept, "no opening closes: the maze only gains")
	var added := 0
	var added_old := 0
	for key: Vector3i in info.openset:
		if not maze_before.has(key):
			added += 1
			var a := Vector2i(key.x, key.y)
			var b: Vector2i = a + Hex.NEIGHBOURS[key.z]
			if a != add and b != add:
				added_old += 1
	_check(added_old == 0, "the only new openings are the new tile's (%d)" % added)
	for i in 6:
		if add + Hex.NEIGHBOURS[i] == lm:
			_check(not map.canyon_open(lm, (i + 3) % 6), "it stays closed to the Echo Cave")
	var door_count: int = info.entrances.filter(func(e: Vector3i): return Vector2i(e.x, e.y) == add).size()
	_check(door_count == 1, "it has its own entrance")
	var rebuilt := []
	var same := true
	for t: Vector2i in old:
		if map._canyon_meshes[t] != meshes[t]:
			rebuilt.append(t)
			same = same and Rules.hex_distance(t, add) == 1
	_check(same, "only touching tiles rebuilt (%d of %d)" % [rebuilt.size(), old.size()])
	print("DESERT PERF growing a canyon in play on this Mac: %d tiles rebuilt, %d triangles; field %d ms and mesh %d ms off the main thread; worst frame %.1f ms" % [
			map.canyon_stats[-1].rebuilt, map.canyon_stats[-1].triangles, map.canyon_stats[-1].field_ms, map.canyon_stats[-1].mesh_ms, worst])
	_check(absf(game.party_node.members[0].node.position.y - party_y) < 0.3 and game.party_tile == party_on, "a party on the canyon stays put, on the ground")
	# In by the new entrance, on to every tile.
	var e: Vector3i = info.entrances.filter(func(q: Vector3i): return Vector2i(q.x, q.y) == add)[0]
	var through: Vector2i = add + Hex.NEIGHBOURS[e.z]
	map.place(through, "plains")
	game.order[through] = game.order.size()
	game._debug_fill[through] = true
	await _wait(0.1)
	var seen := Canyon.reached(info.openset, info.entrances, _set_of(region.tiles))
	_check(seen.size() == region.tiles.size(), "every tile can still be walked to from an entrance")
	game.party_tile = through
	game.party_node.place_at(through)
	var height := func(p: Vector2) -> float:
		return map.walk_z(p) if not is_nan(map.walk_z(p)) else 0.0
	var r := await _follow(add, height)
	_check(game.party_tile == add and r.gap < 0.15 and absf(game.party_node.members[0].node.position.y - Canyon.FLOOR) < 0.05, "the party walks down the new lane to the new tile's floor (gap %.3f)" % r.gap)
	var far := await _follow(lm, height)
	_check(game.party_tile == lm and far.gap < 0.15, "and from there on to the Echo Cave (gap %.3f)" % far.gap)
	game.ui.visible = false
	game.rig.frame(Hex.to3(Hex.tile_position(add.x, add.y)), 44.0, 50.0)
	await _wait(1.0)
	await _shot("40_canyon_grown")
	game.ui.visible = true
	_check_rock_of(map, region)
	await _wait(0.5)
	# Filling a hole: place tiles round a gap so one has no outer edge at all.
	await _fill_hole(map, region)


static func _set_of(tiles: Array) -> Dictionary:
	var out := {}
	for t in tiles:
		out[t] = true
	return out


## test_mesas.py's limits, on the anchored grid the game uses: the rebuilt mesas (art/handoff/desert_kit.md).
func _check_mesas() -> void:
	var rnd := RandomNumberGenerator.new()
	rnd.seed = 24
	var count := 0
	var tiles := 0
	var side := INF
	var corner := 180.0
	var gap := INF
	var rim := INF
	var edge := INF
	var slowest := 0.0
	var crossing := 0
	for _n in 24:
		var region: Array = [Vector2i(rnd.randi_range(-12, 12), rnd.randi_range(-12, 12))]
		var size := rnd.randi_range(8, 14)
		while region.size() < size:
			var c: Vector2i = region[rnd.randi_range(0, region.size() - 1)] + Hex.NEIGHBOURS[rnd.randi_range(0, 5)]
			if not c in region:
				region.append(c)
		var lm: Vector2i = region[rnd.randi_range(0, region.size() - 1)]
		var t0 := Time.get_ticks_usec()
		var f := Canyon.Field.new(region, lm, Sand.sphinx_turn(lm, region), true)
		slowest = maxf(slowest, (Time.get_ticks_usec() - t0) / 1000.0)
		count += f.mesas.size()
		tiles += region.size()
		for i in f.mesas.size():
			var m: PackedVector2Array = f.mesas[i]
			var pts := Array(m)
			for k in m.size():
				side = minf(side, m[k].distance_to(m[(k + 1) % m.size()]))
				corner = minf(corner, Canyon._corner(pts, k))
				rim = minf(rim, f._bilinear(f.land, m[k].x, m[k].y))
				edge = minf(edge, f.edge_margin(m[k].x, m[k].y))
				for j in range(k + 2, m.size()):
					if (j + 1) % m.size() != k and Geometry2D.segment_intersects_segment(m[k], m[(k + 1) % m.size()], m[j], m[(j + 1) % m.size()]) != null:
						crossing += 1
			for j in range(i + 1, f.mesas.size()):
				gap = minf(gap, Canyon.outline_gap(m, f.mesas[j]))
	_check(side >= 0.45, "mesas: shortest side %.2f (at least 0.45)" % side)
	_check(corner >= 60.0, "mesas: sharpest corner %.1f degrees (at least 60)" % corner)
	_check(gap >= 0.9, "mesas: smallest gap %.2f (at least 0.9)" % gap)
	_check(rim >= 0.42, "mesas: nearest the rim %.2f (at least 0.42)" % rim)
	_check(edge >= 0.6, "mesas: nearest the region's edge %.2f (at least 0.6)" % edge)
	_check(crossing == 0, "mesas: no outline crosses itself")
	print("DESERT PERF mesas: %d on %d tiles (hand-off: 90 on 276); slowest Field %d ms in GDScript (plain Python, 12 tiles: 1.14 s)" % [count, tiles, slowest])


func _place_and_time(map: MapBoard, add: Vector2i, _region_d: Dictionary) -> float:
	map.place(add, "desert")
	game.order[add] = game.order.size()
	game._check_region(add, "desert")
	var worst := 0.0
	var last := Time.get_ticks_usec()
	var shot_taken := false
	while game.busy:
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		worst = maxf(worst, (now - last) / 1000.0)
		last = now
	return worst


## The rock of a grown region against rays, by the same test as the first.
func _check_rock_of(map: MapBoard, g: Dictionary) -> void:
	var holes := 0
	var body := StaticBody3D.new()
	body.collision_layer = 1 << 9
	var faces := PackedVector3Array()
	for t: Vector2i in g.tiles:
		var mi: MeshInstance3D = map.tile_node(t).get_node("canyon")
		var v: PackedVector3Array = mi.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		for q in v:
			faces.append(q + mi.global_position)
	var cs := CollisionShape3D.new()
	var shape := ConcavePolygonShape3D.new()
	shape.set_faces(faces)
	cs.shape = shape
	body.add_child(cs)
	add_child(body)
	_rock_rays.call_deferred(map, g, body)


## A tile with no outer edge, in play: nothing's cut off, and the party can walk onto it.
func _fill_hole(map: MapBoard, region: Dictionary) -> void:
	var info: Dictionary = map.canyons[region.landmark_tile]
	# A slot of the region's with the most old neighbours; the rest of its ring are placed as new canyon tiles first.
	var best := Vector2i.MAX
	var most := 0
	for t: Vector2i in region.tiles:
		for n in Hex.NEIGHBOURS:
			var s: Vector2i = t + n
			if not map.terrains.has(s):
				var c := 0
				for m in Hex.NEIGHBOURS:
					c += 1 if region.tiles.has(s + m) else 0
				if c > most:
					most = c
					best = s
	for m in Hex.NEIGHBOURS:
		var ring: Vector2i = best + m
		if not map.terrains.has(ring):
			await _place_and_time(map, ring, region)
	await _wait(0.2)
	info = map.canyons[region.landmark_tile]
	var doors_near: int = info.entrances.filter(func(e: Vector3i): return Vector2i(e.x, e.y) + Hex.NEIGHBOURS[e.z] == best).size()
	await _place_and_time(map, best, region)
	info = map.canyons[region.landmark_tile]
	var inside := _set_of(region.tiles)
	_check(Variants.is_canyon(map.terrains[best]) and Canyon.reached(info.openset, info.entrances, inside).size() == region.tiles.size(), "a tile filling a hole cuts nothing off (%d old entrances faced it, %d entrances left)" % [doors_near, info.entrances.size()])
	_check(info.entrances.filter(func(e: Vector3i): return Vector2i(e.x, e.y) == best).is_empty(), "and has no entrance of its own, with no edge facing out")
	_check(range(6).any(func(i): return map.canyon_open(best, i)), "it opens onto the maze")
	var height := func(p: Vector2) -> float:
		return map.walk_z(p) if not is_nan(map.walk_z(p)) else 0.0
	var r := await _follow(best, height)
	_check(game.party_tile == best and r.gap < 0.15, "the party can walk onto it (gap %.3f)" % r.gap)
	game.ui.visible = false
	game.rig.frame(Hex.to3(Hex.tile_position(best.x, best.y)), 40.0, 50.0)
	await _wait(0.8)
	await _shot("41_canyon_hole_filled")
	game.ui.visible = true


## Random regions and tiles, off the map: every side of a region (the anchored grid), holes among them. Compares rock before and after.
func _grow_cases() -> void:
	var rnd := RandomNumberGenerator.new()
	rnd.seed = 5
	var cases := 0
	var west_south := 0
	var holes := 0
	var far_cells := 0
	var far_worst := 0.0
	var near_cells := 0
	var floor_lost := 0
	var cut_off := 0
	var echo_opened := 0
	var closed := 0
	var no_door := 0
	var seam_bad := 0
	for _n in 40:
		var region: Array = [Vector2i.ZERO]
		var size := rnd.randi_range(8, 14)
		while region.size() < size:
			var c: Vector2i = region[rnd.randi_range(0, region.size() - 1)] + Hex.NEIGHBOURS[rnd.randi_range(0, 5)]
			if not c in region:
				region.append(c)
		var lm: Vector2i = region[rnd.randi_range(0, region.size() - 1)]
		var turn := Sand.sphinx_turn(lm, region)
		var old := Canyon.open_edges(region, lm, turn)
		var a := Canyon.Field.new(region, lm, turn, true, old)
		var slots := {}
		for t: Vector2i in region:
			for k in Hex.NEIGHBOURS:
				if not region.has(t + k):
					slots[t + k] = true
		# Each slot in turn is too slow: the westmost, the southmost, a random one, and any that's a hole.
		var picks := {}
		var keys := slots.keys()
		keys.sort_custom(func(p, q): return Hex.tile_position(p.x, p.y).x < Hex.tile_position(q.x, q.y).x)
		picks[keys[0]] = true
		keys.sort_custom(func(p, q): return Hex.tile_position(p.x, p.y).y < Hex.tile_position(q.x, q.y).y)
		picks[keys[0]] = true
		picks[keys[rnd.randi_range(0, keys.size() - 1)]] = true
		for s: Vector2i in slots:
			if Hex.NEIGHBOURS.all(func(k): return region.has(s + k)):
				picks[s] = true
		for x: Vector2i in picks:
			var g := Canyon.grow(old.openset, old.entrances, region, [x], lm, {})
			var tiles := region + [x]
			var b := Canyon.Field.new(tiles, lm, turn, true, g)
			cases += 1
			var at_x := Hex.tile_position(x.x, x.y)
			var west := region.all(func(t): return Hex.tile_position(t.x, t.y).x > at_x.x) or region.all(func(t): return Hex.tile_position(t.x, t.y).y > at_x.y)
			west_south += 1 if west else 0
			var hole: bool = Hex.NEIGHBOURS.all(func(k): return region.has(x + k))
			holes += 1 if hole else 0
			var inside := _set_of(tiles)
			if Canyon.reached(g.openset, g.entrances, inside).size() != tiles.size():
				cut_off += 1
			if g.entrances.is_empty():
				no_door += 1
			for k in 6:
				var n: Vector2i = x + Hex.NEIGHBOURS[k]
				if n == lm and g.openset.has(Canyon.edge_key(x, k)):
					echo_opened += 1
			for key in old.openset:
				if not g.openset.has(key):
					closed += 1
			for ix in range(0, a.nx, 2):
				for iy in range(0, a.ny, 2):
					var px := a.x0 + ix * Canyon.CELL + 0.03
					var py := a.y0 + iy * Canyon.CELL + 0.03
					var t := GroundCover.tile_at(Vector2(px, py))
					if not region.has(t):
						continue
					var va := a.value(px, py)
					var vb := b.value(px, py)
					if va < 0.01 and vb > va + 0.05:
						floor_lost += 1
					if absf(va - vb) > 0.02:
						if t in g.rebuild:
							near_cells += 1
						else:
							far_cells += 1
							far_worst = maxf(far_worst, absf(va - vb))
	# Holes: rings and rings of rings round a gap. All the entrances facing the gap is the worst case: the gap's tile has no
	# outer edge, so the maze must find a new way in.
	for radius in [1, 2]:
		for shift in [Vector2i.ZERO, Vector2i(3, -2), Vector2i(-4, 1), Vector2i(2, 5)]:
			var x: Vector2i = shift
			var region: Array = []
			for q in range(-radius, radius + 1):
				for r in range(-radius, radius + 1):
					if Rules.hex_distance(Vector2i(q, r), Vector2i.ZERO) <= radius and Vector2i(q, r) != Vector2i.ZERO:
						region.append(x + Vector2i(q, r))
			for lm_k in [0, 3]:
				var lm: Vector2i = x + Hex.NEIGHBOURS[lm_k]
				var turn := Sand.sphinx_turn(lm, region)
				var made := Canyon.open_edges(region, lm, turn)
				var doors_at_gap := []
				for e in 6:
					var n: Vector2i = x + Hex.NEIGHBOURS[e]
					if n != lm:
						doors_at_gap.append(Vector3i(n.x, n.y, (e + 3) % 6))
				for maze in [made, {openset = made.openset, entrances = doors_at_gap}]:
					var g := Canyon.grow(maze.openset, maze.entrances, region, [x], lm, {})
					cases += 1
					holes += 1
					if Canyon.reached(g.openset, g.entrances, _set_of(region + [x])).size() != region.size() + 1 or g.entrances.is_empty():
						cut_off += 1
					if g.openset.has(Canyon.edge_key(x, lm_k)):
						echo_opened += 1
	print("DESERT grow cases: %d tiles added, %d west or south of all, %d holes; rock changed at %d cells on touching tiles and %d further off (worst %.2f bands; pinned at the seam)" % [cases, west_south, holes, near_cells, far_cells, far_worst])
	_check(west_south > 10, "the cases include tiles west and south of the region (%d)" % west_south)
	_check(holes > 0, "and holes (%d)" % holes)
	_check(cut_off == 0, "no added tile cuts anything off")
	_check(no_door == 0, "every grown canyon keeps an entrance")
	_check(echo_opened == 0, "none opens onto the Echo Cave")
	_check(closed == 0, "none closes an opening")
	_check(floor_lost == 0, "no old floor becomes rock")
