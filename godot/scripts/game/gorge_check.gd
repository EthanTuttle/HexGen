class_name GorgeCheck
extends Node
## Checks rapids as a dug gorge (tiles v64, art/handoff/river_kit.md) in the game (`-- --gorgecheck`, add `--shots` for
## screens/gorge_*.png): no slab, walls and ground, water heights, lanes, bridges, falls and flow, the frozen Troll tile, the
## silhouette, and a region turning into rapids. `--gorgemovie` stands the camera on the moving water for a recording.
## Prints GORGE OK / GORGE FAIL lines, then GORGE DONE. A test aid only.

var game: Game
var shots := false
var failed := 0
var map: MapBoard


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("GORGE %s: %s" % ["OK" if ok else "FAIL", what])
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
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("gorge_%s.png" % name))
		print("SAVED gorge_%s" % name)


func _region(variant: String) -> Dictionary:
	for g in game.regions:
		if g.variant == variant:
			return g
	return {}


func _look(t: Vector2i, dist: float, tilt: float, name: String, off := Vector2.ZERO) -> void:
	game.rig.frame(Hex.to3(Hex.tile_position(t.x, t.y) + off), dist, tilt)
	await _wait(0.5)
	await _shot(name)


func _run() -> void:
	game.spawn_forest_regions()
	await _wait(1.0)
	map = game.map
	game.debug_auto_cross = true
	var g := _region("rapids")
	_check(not g.is_empty(), "the rapids region spawned")
	var tiles: Array = g.tiles
	if "--gorgemovie" in OS.get_cmdline_user_args():
		await _movie(tiles, g.landmark_tile)
		get_tree().quit()
		return
	_check_tiles(tiles)
	await _look(g.landmark_tile, 34.0, 50.0, "01_region")
	await _look(g.landmark_tile, 16.0, 45.0, "02_troll")
	await _falls(tiles)
	await _walks(tiles)
	await _hop(g.landmark_tile)
	await _frozen(g.landmark_tile)
	await _region_turning()
	_perf()
	print("GORGE DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _names(t: Vector2i) -> Array:
	return map.tile_node(t).get_children().map(func(c): return String(c.name))


func _check_tiles(tiles: Array) -> void:
	var worst := 0
	var slabs := 0
	var marked := 0
	var sides_ok := true
	for t: Vector2i in tiles:
		var w: Dictionary = map.water_shapes[t]
		if not w.has("gorge"):
			continue
		var names := _names(t)
		if names.any(func(n): return n.begins_with("base_")):
			slabs += 1
		var rock := map.tile_node(t).get_node_or_null("gorge_rock") as MeshInstance3D
		if rock and (rock.material_override as BaseMaterial3D).stencil_reference == 1:
			marked += 1
		worst = maxi(worst, w.gorge_triangles)
		sides_ok = sides_ok and w.gorge.sides.size() == 2 * w.mask.count(false)
		for i in 6:
			if w.mask[i]:
				var z := Gorge.water_z(w.mask, w.widths, Water.normal(i) * Water.A)
				var want := -Gorge.DEPTH if w.widths[i] in [Water.RAPIDS_WIDTH, Water.FALL_WIDTH] else Gorge.WATER_TOP
				_check(absf(z - want) < 0.01, "%s edge %d: the water is at %.2f" % [t, i, z]) if absf(z - want) >= 0.01 else null
	_check(slabs == 0, "no slab on a rapids tile with a water neighbour")
	_check(marked == tiles.size(), "gorge rock marks the stencil on all %d tiles" % tiles.size())
	_check(sides_ok, "soil sides on every land edge")
	print("GORGE PERF worst tile %d triangles of rock, ground and falls" % worst)
	_check(map.get_node("water").get_node_or_null("water_surface_rapids") != null, "the water has its own material")
	var surface := map.get_node("water").get_node("water_surface_rapids") as MeshInstance3D
	var lowest := INF
	for v: Vector3 in surface.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]:
		lowest = minf(lowest, v.y)
	_check(absf(lowest + Gorge.DEPTH) < 0.05, "the water runs down in the gorge (%.2f)" % lowest)


## The neighbour of t on edge i, with nothing there yet.
func _free_edge(t: Vector2i, wants_up: bool) -> int:
	var here := Water.downhill(t.x, t.y)
	for i in 6:
		var n: Vector2i = t + Hex.NEIGHBOURS[i]
		if not Variants.is_water(map.terrains.get(n)) and (Water.downhill(n.x, n.y) > here) == wants_up:
			return i
	return -1


func _falls(tiles: Array) -> void:
	# Downstream: the tile the water flows out of, with free ground on its low side.
	var down := -1
	var from: Vector2i
	var order := tiles.duplicate()
	order.sort_custom(func(a, b): return Water.downhill(a.x, a.y) > Water.downhill(b.x, b.y))
	for t: Vector2i in order:
		if map.terrains[t] == "rapids":
			down = _free_edge(t, true)
			if down >= 0:
				from = t
				break
	_check(down >= 0, "a free slot downstream")
	if down < 0:
		return
	var river: Vector2i = from + Hex.NEIGHBOURS[down]
	map.retile({river: "river"})
	var r2: Vector2i = river + Hex.NEIGHBOURS[down]
	if not Variants.is_water(map.terrains.get(r2)):
		map.retile({r2: "river"})
	var w: Dictionary = map.water_shapes[from]
	_check(Water.falling(w.widths, down), "%s: a fall on edge %d, where it flows out into a plain river" % [from, down])
	_check(w.gorge.falls.size() >= 1, "it has a waterfall")
	_check(map.tile_node(from).get_node_or_null("gorge_fall") != null, "the waterfall's mesh is on its tile, unlit")
	_check(not map.edge_open(from, river) and not map.edge_open(river, from), "no route over the fall, either way")
	_check(not Water.water_routes(w.mask, w.seed, w.widths, w.style).lines.has(down), "no line up or down it")
	var rw: Dictionary = map.water_shapes[river]
	var flow := Water.flow_in(river.x, river.y, rw.mask, Hex.NEIGHBOURS.map(func(n): return Water.FAMILY.get(map.terrains.get(river + n)) == "rapids"), "river")
	var back: int = (down + 3) % 6
	_check(not flow[back], "the last river tile flows toward its fall")
	_check(Water.flow_signs(rw.ends, flow).any(func(s): return s != 0), "and it does flow (%s)" % [Water.flow_signs(rw.ends, flow)])
	var at := Hex.tile_position(from.x, from.y) + Water.normal(down) * 2.0
	game.rig.frame(Hex.to3(at), 14.0, 45.0)
	await _wait(0.5)
	await _shot("10_fall_default")
	# Upstream: a river flowing in slopes down into the gorge.
	var up := -1
	var top: Vector2i
	for k in range(order.size() - 1, -1, -1):
		var t: Vector2i = order[k]
		if map.terrains[t] == "rapids":
			up = _free_edge(t, false)
			if up >= 0:
				top = t
				break
	_check(up >= 0, "a free slot upstream")
	if up >= 0:
		var inr: Vector2i = top + Hex.NEIGHBOURS[up]
		map.retile({inr: "river"})
		var u: Dictionary = map.water_shapes[top]
		_check(not Water.falling(u.widths, up), "%s: no fall where a river flows in" % top)
		_check(absf(Gorge.water_z(u.mask, u.widths, Water.normal(up) * Water.A) - Gorge.WATER_TOP) < 0.01, "the water joins the river's level at that edge")
		_check(map.edge_open(top, inr), "that edge can be crossed")
		var at2 := Hex.tile_position(top.x, top.y) + Water.normal(up) * 2.0
		game.rig.frame(Hex.to3(at2), 14.0, 45.0)
		await _wait(0.5)
		await _shot("11_inflow")


func _land_slot(t: Vector2i, e: int) -> Vector2i:
	var n: Vector2i = t + Hex.NEIGHBOURS[e]
	if not map.terrains.has(n):
		map.retile({n: "plains"})
	return n


func _walks(tiles: Array) -> void:
	# A lane: from land, down it and into the water.
	var lane_tile = null
	var edge := -1
	for t: Vector2i in tiles:
		var w: Dictionary = map.water_shapes[t]
		if w.has("gorge") and map.terrains[t] == "rapids" and not w.has("bridge"):
			for e: int in w.gorge.walks:
				var n: Vector2i = t + Hex.NEIGHBOURS[e]
				if not map.terrains.has(n) or not Variants.is_water(map.terrains[n]):
					lane_tile = t
					edge = e
					break
		if lane_tile != null:
			break
	_check(lane_tile != null, "a tile with a lane and no bridge")
	if lane_tile == null:
		return
	var from := _land_slot(lane_tile, edge)
	var pw := game.party_node
	pw.has_raft = false
	game.party_tile = from
	pw.place_at(from)
	game.rig.frame(pw.centre(), 16.0, 45.0)
	await _wait(0.3)
	game.walk_to(lane_tile)
	var lowest := 0.0
	var steep := 0.0
	var last := pw.centre()
	var was_on := false
	var shot := false
	while game.busy:
		await get_tree().process_frame
		var h: Vector3 = pw.members[0].node.position
		lowest = minf(lowest, h.y)
		var run := Vector2(h.x - last.x, h.z - last.z).length()
		if run > 0.05:
			if last.y > -1.05 and h.y > -1.05:   # on the lane: the wade's sink at its foot is on purpose
				steep = maxf(steep, rad_to_deg(atan2(absf(h.y - last.y), run)))
			last = h
		was_on = was_on or pw._silhouette_on
		if not shot and h.y < -0.5:
			shot = true
			game.rig.frame(h, 12.0, 45.0)
			await _shot("20_on_the_lane")
	await _wait(Rules.SETTLE_SECONDS)
	_check(game.party_tile == lane_tile, "the party reached %s by its lane" % lane_tile)
	_check(lowest < -1.3, "and waded down in the gorge, at %.2f (0.4 below the water)" % lowest)
	print("GORGE steepest walk on the way, by the hero: %.1f degrees" % steep)
	_check(was_on, "the silhouette is on in a gorge")
	game.rig.frame(pw.centre(), 12.0, 45.0)
	await _wait(0.3)
	await _shot("21_wading")
	await _wait(0.3)
	# From across the channel the near wall hides a wader: at the game's camera angle, and lower, to see the silhouette whole.
	var hero: Vector3 = pw.members[0].node.position
	var along := Water.normal(edge)
	var yaw := rad_to_deg(atan2(along.x, along.y))
	for k in 2:
		var turn: float = yaw + 180.0 * k
		game.rig.frame(hero, 12.0, 45.0, turn)
		await _wait(0.3)
		await _shot("22_silhouette_%d_game_angle" % k)
		if k == 1:
			game.rig.frame(hero, 9.0, 18.0, turn)
			await _wait(0.3)
			await _shot("23_silhouette_low")
	game.rig.frame(hero, 12.0, 45.0, 0.0)
	# A plain bridge or the Troll Bridge: over it with no check.
	var troll: Vector2i = _region("rapids").landmark_tile
	var br: Dictionary = map.water_shapes[troll].get("bridge", {})
	_check(not br.is_empty(), "the Troll Bridge stands")
	if br.is_empty():
		return
	for e: int in br.routes:
		var n: Vector2i = troll + Hex.NEIGHBOURS[e]
		if not Variants.is_water(map.terrains.get(n)):
			var land := _land_slot(troll, e)
			game.party_tile = land
			pw.place_at(land)
			await _wait(0.2)
			var cross := {n = 0}
			var count := func(): cross.n += 1
			pw.waded.connect(count)
			game.walk_to(troll)
			var high := 0.0
			while game.busy:
				await get_tree().process_frame
				high = maxf(high, pw.members[0].node.position.y)
			pw.waded.disconnect(count)
			_check(cross.n == 0, "the Troll Bridge is walked with no check")
			_check(high > 0.7 and high < 1.3, "up on its hump at %.2f" % high)
			game.rig.frame(pw.centre(), 12.0, 40.0)
			await _wait(0.4)
			await _shot("30_on_the_troll_bridge")
			break


## What the player sees when a wader reaches a bridged tile, and how many routes on this region do it.
func _hop(troll: Vector2i) -> void:
	var pw := game.party_node
	var from = null
	for i in 6:
		var n: Vector2i = troll + Hex.NEIGHBOURS[i]
		if map.water_shapes.has(n) and map.water_shapes[n].has("gorge") and map.water_shapes[troll].mask[i] and map.edge_open(n, troll):
			from = n
			break
	_check(from != null, "a gorge tile joining the Troll tile by water")
	if from == null:
		return
	game.party_tile = from
	pw.place_at(from)
	await _wait(0.4)
	game.rig.frame(Hex.to3(Hex.tile_position(troll.x, troll.y)), 15.0, 45.0)
	await _wait(0.3)
	await _shot("35_hop_before")
	var low := pw.members[0].node.position.y as float
	# Straight over the shared edge, as a route does when there's no dry way round (on this map there is one).
	var straight: Array[Vector2i] = [troll]
	game._walk(straight)
	var t0 := -1.0
	var took := 0.0
	var last := low
	var worst_step := 0.0
	var mid_shot := false
	var at_shot := false
	while game.busy:
		await get_tree().process_frame
		var y: float = pw.members[0].node.position.y
		var rise := y - last
		worst_step = maxf(worst_step, rise)
		last = y
		if y > low + 0.3 and t0 < 0.0:
			t0 = Time.get_ticks_msec()
		if t0 >= 0.0 and took == 0.0 and y > -0.05:
			took = Time.get_ticks_msec() - t0
		if t0 >= 0.0 and not mid_shot and y > -0.9:
			mid_shot = true
			game.rig.frame(pw.members[0].node.position, 12.0, 45.0)
			await _shot("36_hop_rising")
		if took > 0.0 and not at_shot:
			at_shot = true
			game.rig.frame(pw.members[0].node.position, 12.0, 45.0)
			await _shot("37_hop_on_deck")
	print("GORGE HOP from the water at %.2f up to the deck: %d ms, the most in one frame %.2f m" % [low, took, worst_step])
	# How often: every land or water start next to the region, to every tile of it and across it.
	var region: Array = _region("rapids").tiles
	var around := {}
	for t: Vector2i in region:
		for n in Hex.NEIGHBOURS:
			if map.terrains.has(t + n) and not (t + n) in region:
				around[t + n] = true
	var starts := {"from the land round it": around.keys(), "from inside the gorge": region}
	for label: String in starts:
		_count_hops(label, starts[label], region + around.keys())


func _count_hops(label: String, from_tiles: Array, goals: Array) -> void:
	var routes := 0
	var hops := 0
	var was_at := game.party_tile
	for a: Vector2i in from_tiles:
		for goal: Vector2i in goals:
			if a == goal:
				continue
			game.party_tile = a
			var path := game.path_to(goal)
			if path.is_empty():
				continue
			routes += 1
			var was: Vector2i = a
			var hop := false
			for t: Vector2i in path:
				var edge := Hex.NEIGHBOURS.find(t - was)
				if edge >= 0 and map.water_shapes.has(t):
					var w: Dictionary = map.water_shapes[t]
					if w.has("gorge") and w.mask[(edge + 3) % 6] and w.has("bridge"):
						hop = true
				was = t
			hops += 1 if hop else 0
	game.party_tile = was_at
	print("GORGE HOP %s: %d routes, %d step into a bridged tile by water" % [label, routes, hops])


## design/02: once it stands, a later water neighbour's channel ends in a gorge head beside it.
func _frozen(troll: Vector2i) -> void:
	var w: Dictionary = map.water_shapes[troll]
	var mask: Array = w.mask.duplicate()
	var spot: Dictionary = w.bridge
	var e := -1
	for i in 6:
		var n: Vector2i = troll + Hex.NEIGHBOURS[i]
		if Variants.is_water(map.terrains.get(n)) or map.gates.has(n):
			continue
		var alone := true   # beside the Troll tile and nothing else, so what it joins is only the tile placed beyond it
		for m in Hex.NEIGHBOURS:
			if n + m != troll and Variants.is_water(map.terrains.get(n + m)):
				alone = false
		if alone and not Variants.is_water(map.terrains.get(n + Hex.NEIGHBOURS[i])):
			e = i
			break
	_check(e >= 0, "a slot beside the Troll Bridge")
	if e < 0:
		return
	var n: Vector2i = troll + Hex.NEIGHBOURS[e]
	var beyond: Vector2i = n + Hex.NEIGHBOURS[e]
	var changes := {n: "rapids"}
	changes[beyond] = "rapids"
	map.retile(changes)
	var now: Dictionary = map.water_shapes[troll]
	_check(now.mask == mask and now.bridge.middle == spot.middle and now.bridge.angle == spot.angle, "the Troll tile's water and bridge didn't move")
	var nw: Dictionary = map.water_shapes[n]
	_check(not nw.mask[(e + 3) % 6], "the new tile doesn't list the shared edge")
	_check(nw.has("gorge") and nw.kind == "spring", "its channel ends in a gorge head")
	_check(not Water.falling(nw.widths, (e + 3) % 6), "and no fall there")
	var at := Hex.tile_position(n.x, n.y)
	game.rig.frame(Hex.to3(at), 16.0, 45.0)
	await _wait(0.5)
	await _shot("40_gorge_head_beside_troll")


## A plain river region really finishing into rapids, with the frame times of the change.
func _region_turning() -> void:
	var c := Vector2i(-24, 0)
	var shape: Array = Game.DEBUG_RIVER_SHAPES["rapids"]
	var tiles: Array[Vector2i] = []
	var changes := {}
	for s: Vector2i in shape:
		if map.terrains.has(c + s):
			_check(false, "the staged region's ground is free")
			return
		tiles.append(c + s)
		changes[c + s] = "river"
	map.retile(changes)
	await _wait(0.3)
	var region := game.new_region("river", tiles, "rapids", game._landmark_tile("rapids", tiles))
	game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y)), 30.0, 50.0)
	await _wait(0.5)
	var worst := 0
	game._transform(tiles, region, c)
	await get_tree().process_frame
	var t0 := Time.get_ticks_usec()
	while game.busy:
		await get_tree().process_frame
		var t1 := Time.get_ticks_usec()
		worst = maxi(worst, t1 - t0)
		t0 = t1
	print("GORGE PERF a %d-tile region turning into rapids: %d ms off the main thread, worst frame %.1f ms" % [tiles.size(), map.gorge_job_ms, worst / 1000.0])
	_check(tiles.all(func(t): return map.water_shapes[t].has("gorge")), "the region turned into gorges")
	await _shot("50_region_turned")
	var ends: Array = tiles.duplicate()
	ends.sort_custom(func(a, b): return Hex.tile_position(a.x, a.y).x > Hex.tile_position(b.x, b.y).x)
	game.rig.frame(Hex.to3(Hex.tile_position(ends[0].x, ends[0].y)), 16.0, 45.0)
	await _wait(0.3)
	await _shot("51_region_end")
	_count_hops("in a region with no land placed round it", tiles, tiles)


func _perf() -> void:
	print("GORGE PERF slowest Gorge.build on the main thread %.1f ms" % (map.gorge_build_us / 1000.0))
	print("GORGE PERF view: draw calls %d, triangles %d" % [Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)])


## The water moving: a long look at a fall and its pool, then the gorge, then a river flowing in.
func _movie(tiles: Array, _troll: Vector2i) -> void:
	var order := tiles.duplicate()
	order.sort_custom(func(a, b): return Water.downhill(a.x, a.y) > Water.downhill(b.x, b.y))
	var from: Vector2i = order[0]
	var down := _free_edge(from, true)
	var up_tile: Vector2i = order[-1]
	var up := _free_edge(up_tile, false)
	if down >= 0:
		map.retile({from + Hex.NEIGHBOURS[down]: "river"})
		map.retile({from + Hex.NEIGHBOURS[down] * 2: "river"})
		game.rig.frame(Hex.to3(Hex.tile_position(from.x, from.y) + Water.normal(down) * 2.0), 13.0, 45.0)
		await _wait(5.0)
	var mid: Vector2i = order[order.size() / 2]
	game.rig.frame(Hex.to3(Hex.tile_position(mid.x, mid.y)), 15.0, 45.0)
	await _wait(4.0)
	if up >= 0:
		map.retile({up_tile + Hex.NEIGHBOURS[up]: "river"})
		game.rig.frame(Hex.to3(Hex.tile_position(up_tile.x, up_tile.y) + Water.normal(up) * 2.0), 13.0, 45.0)
		await _wait(4.0)
