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
	await _no_route_along(g.tiles)
	await _frozen(g.landmark_tile)
	await _region_turning()
	await _stranded()
	_walled_off()
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
		_check(not map.edge_open(top, inr) and not map.edge_open(inr, top), "and no route steps over it (design/02: crossing only)")
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
	# A crossing: from land, down one bank's lane, over the water, up the other bank's, and on to the land beyond it.
	var picked := Crossing.find(map, tiles)
	_check(not picked.is_empty(), "a tile with a lane on each bank and no bridge")
	if picked.is_empty():
		return
	var cross_tile: Vector2i = picked[0]
	var from: Vector2i = picked[1]
	var far: Vector2i = picked[2]
	var pw := game.party_node
	pw.has_raft = false
	game.party_tile = from
	pw.place_at(from)
	game.rig.frame(pw.centre(), 16.0, 45.0)
	await _wait(0.3)
	var waded := {n = 0}
	var on_wade := func(): waded.n += 1
	pw.waded.connect(on_wade)
	var route: Array[Vector2i] = [cross_tile, far]
	_check(game._needs_check(route), "that route needs the check")
	game._walk(route)
	var lowest := 0.0
	var steep := 0.0
	var last := pw.centre()
	var was_on := false
	var on_lane := false
	var in_water := false
	var at_water: Vector3
	while game.busy:
		await get_tree().process_frame
		var h: Vector3 = pw.members[0].node.position
		lowest = minf(lowest, h.y)
		var run := Vector2(h.x - last.x, h.z - last.z).length()
		if run > 0.05:
			if last.y > -1.05 and h.y > -1.05:   # on the lane: the wade's sink at its foot is on purpose
				if h.y < -0.1 and not in_water:   # going down the first lane, before the steps at its ends
					steep = maxf(steep, rad_to_deg(atan2(absf(h.y - last.y), run)))
			last = h
		was_on = was_on or pw._silhouette_on
		if not on_lane and h.y < -0.5:
			on_lane = true
			game.rig.frame(h, 12.0, 45.0)
			await _shot("20_on_the_lane")
		if not in_water and h.y < -1.4 and map.wet_at(Vector2(h.x, -h.z)):
			in_water = true
			at_water = h
			pw.process_mode = Node.PROCESS_MODE_DISABLED   # held mid-crossing for its pictures
			game.rig.frame(h, 12.0, 45.0)
			await _wait(0.3)
			await _shot("21_crossing")
			var yaw := rad_to_deg(atan2(Water.normal(picked[3]).x, Water.normal(picked[3]).y))
			for k in 2:
				game.rig.frame(h, 12.0, 45.0, yaw + 180.0 * k)
				await _wait(0.3)
				await _shot("22_silhouette_%d_game_angle" % k)
				if k == 1:
					game.rig.frame(h, 9.0, 18.0, yaw + 180.0)
					await _wait(0.3)
					await _shot("23_silhouette_low")
			game.rig.frame(h, 16.0, 45.0)
			pw.process_mode = Node.PROCESS_MODE_INHERIT
	pw.waded.disconnect(on_wade)
	await _wait(Rules.SETTLE_SECONDS)
	_check(game.party_tile == far, "the party crossed %s and reached %s" % [cross_tile, far])
	_check(lowest < -1.3, "wading in the gorge, at %.2f (0.4 below the water)" % lowest)
	_check(waded.n == 1, "one check for the crossing (%d)" % waded.n)
	print("GORGE steepest walk down the lane, by the hero: %.1f degrees" % steep)
	_check(was_on, "the silhouette is on in a gorge")
	# Walking onto the tile from a bank stops on that bank, with no check; leaving by the far side is a crossing.
	game.party_tile = from
	pw.place_at(from)
	await _wait(0.2)
	waded.n = 0
	pw.waded.connect(on_wade)
	game.walk_to(cross_tile)
	while game.busy:
		await get_tree().process_frame
	pw.waded.disconnect(on_wade)
	await _wait(Rules.SETTLE_SECONDS)
	var stood: Vector3 = pw.members[0].node.position
	_check(game.party_tile == cross_tile and waded.n == 0 and absf(stood.y) < 0.05 and not map.wet_at(Vector2(stood.x, -stood.z)), "stepping onto it stops on the near bank, dry, with no check (y %.2f, %d)" % [stood.y, waded.n])
	var out: Array[Vector2i] = [far]
	_check(game._needs_check(out), "and going on from there to the far side is the check")
	await _shot("24_stopped_on_a_bank")
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


## design/02 -> Bridges on rapids: crossing only. Every route on the region and round it, tile by tile and point by point.
func _no_route_along(region: Array) -> void:
	var around := {}
	for t: Vector2i in region:
		for n in Hex.NEIGHBOURS:
			if map.terrains.has(t + n) and not (t + n) in region:
				around[t + n] = true
	var was_at := game.party_tile
	var routes := 0
	var along := 0
	var spans_bad := 0
	var starts: Array = region + around.keys()
	for a: Vector2i in starts:
		if map.water_shapes.has(a) and map.path_graph(a).stand == null:
			continue
		game.party_tile = a
		game.party_node.place_at(a)
		for goal: Vector2i in starts:
			if a == goal:
				continue
			var path := game.path_to(goal)
			if path.is_empty():
				continue
			routes += 1
			var from: Vector2i = a
			for t: Vector2i in path:
				var e := Hex.NEIGHBOURS.find(t - from)
				if map._water_edge_shut(from, e) or map._water_edge_shut(t, (e + 3) % 6):
					along += 1
				from = t
			var points: PackedVector2Array = game.party_node.route_preview(path)
			var wet_tile = null
			for p in points:
				if map.wet_at(p):
					var here := GroundCover.tile_at(p)
					if map.water_shapes[here].style == "rapids":
						if wet_tile != null and wet_tile != here:
							spans_bad += 1
						wet_tile = here
				else:
					wet_tile = null
			if not points.is_empty() and map.wet_at(points[-1]) and map.water_shapes[GroundCover.tile_at(points[-1])].style == "rapids":
				spans_bad += 1
	game.party_tile = was_at
	game.party_node.place_at(was_at)
	_check(routes > 0 and along == 0, "no route steps along the gorge or over a fall, of %d" % routes)
	_check(spans_bad == 0, "no route wades from one rapids tile into the next, or ends in the water")
	var in_water := 0
	for t: Vector2i in region:
		var g := map.path_graph(t)
		for e in g.edge_stand:
			if map.wet_at(g.nodes[g.edge_stand[e]]):
				in_water += 1
		if map.water_shapes[t].has("gorge"):
			for i in 6:
				if map.water_shapes[t].mask[i] and g.edge_node.has(i):
					in_water += 1
	_check(in_water == 0, "no stop in the water, no line out by a water edge")


## A party on a plain river when it becomes rapids.
func _stranded() -> void:
	var c := Vector2i(-24, -8)
	var shape: Array = Game.DEBUG_RIVER_SHAPES["rapids"]
	var tiles: Array[Vector2i] = []
	var changes := {}
	for s: Vector2i in shape:
		if map.terrains.has(c + s):
			print("GORGE stranded test: ground taken, skipped")
			return
		tiles.append(c + s)
		changes[c + s] = "river"
	map.retile(changes)
	await _wait(0.2)
	var on: Vector2i = tiles[2]
	game.party_tile = on
	game.party_node.place_at(on)
	await _wait(0.2)
	var h: Vector3 = game.party_node.members[0].node.position
	var was_wet := map.wet_at(Vector2(h.x, -h.z))
	var region := game.new_region("river", tiles, "rapids", game._landmark_tile("rapids", tiles))
	game._transform(tiles, region, on)
	await get_tree().process_frame
	while game.busy:
		await get_tree().process_frame
	await _wait(0.3)
	var wet := 0
	for m in game.party_node.members:
		var p: Vector3 = m.node.position
		wet += 1 if map.wet_at(Vector2(p.x, -p.z)) else 0
	_check(wet == 0, "a party on a river that turns to rapids (in the water before: %s) ends on a bank, on %s, none in the water" % [was_wet, game.party_tile])
	await _shot("45_party_put_on_a_bank")
	# In the middle of a ring of rapids, with no land on its tile, there's no bank at all: the nearest tile that has a way on.
	var mid := Vector2i(-30, 6)
	var ring := {mid: "river"}
	for n in Hex.NEIGHBOURS:
		ring[mid + n] = "river"
	if ring.keys().any(func(q): return map.terrains.has(q)):
		print("GORGE stranded test: ground taken, skipped the ring")
		return
	map.retile(ring)
	await _wait(0.2)
	game.party_tile = mid
	game.party_node.place_at(mid)
	await _wait(0.2)
	for q: Vector2i in ring:
		ring[q] = "rapids"
	map.retile(ring)
	game._off_rapids()
	await _wait(0.3)
	var off := game.party_tile
	_check(off != mid and map.path_graph(mid).stand == null, "a party on a tile left with no land moves to %s, off it" % off)
	for m in game.party_node.members:
		var p: Vector3 = m.node.position
		wet += 1 if map.wet_at(Vector2(p.x, -p.z)) else 0
	print("GORGE stranded ring: moved %s to %s; in the water after: %d; can it walk anywhere: %d steps to the next land" % [mid, off, wet, game.path_to(Vector2i(-24, 0)).size()])
	await _shot("46_party_off_a_tile_with_no_land")


## What crossing-only leaves walled off: random rapids regions, each with two rings of land round it. A land tile's reach goes
## over land, bridges and crossings. Water.* and Gorge only: no map needed.
func _walled_off() -> void:
	var rnd := RandomNumberGenerator.new()
	rnd.seed = 31
	var regions := 200
	var cut_regions := 0
	var land_total := 0
	var land_cut := 0
	var tiles_total := 0
	var no_land := 0
	var no_stop := 0
	var one_lane := 0
	var side_shut := 0
	var edges_total := 0
	var under_deck := 0
	var two_sides := 0
	var two_bridge := 0
	var two_lanes := 0
	var two_neither := 0
	for _n in regions:
		var region: Array = [Vector2i(rnd.randi_range(-12, 12), rnd.randi_range(-12, 12))]
		var size := rnd.randi_range(3, 14)
		while region.size() < size:
			var c: Vector2i = region[rnd.randi_range(0, region.size() - 1)] + Hex.NEIGHBOURS[rnd.randi_range(0, 5)]
			if not c in region:
				region.append(c)
		var land := {}
		for t: Vector2i in region:
			for n in Hex.NEIGHBOURS:
				for m in Hex.NEIGHBOURS:
					for q: Vector2i in [t + n, t + n + m]:
						if not q in region:
							land[q] = true
		# Nodes: land tiles, and for each rapids tile its land edges; a union of what's joined.
		var parent := {}
		var find := func(x0):
			var x := str(x0)
			while parent.get(x, x) != x:
				x = parent[x]
			return x
		var join := func(a, b):
			parent[find.call(a)] = find.call(b)
		for t: Vector2i in land:
			for n in Hex.NEIGHBOURS:
				if land.has(t + n):
					join.call(t, t + n)
		for t: Vector2i in region:
			var mask := []
			var near := []
			for n in Hex.NEIGHBOURS:
				mask.append(t + n in region)
				near.append("rapids" if t + n in region else "plains")
			tiles_total += 1
			if not mask.has(true):
				continue
			var widths := Water.edge_widths("rapids", near)
			var g := Gorge.build(mask, "%d,%d" % [t.x, t.y], widths, false)
			if not mask.has(false):
				no_land += 1
				continue
			var lanes := {}
			var stops := 0
			for s: int in g.lanes:
				lanes[s] = true
			var banks := []
			for e in 6:
				if mask[e]:
					continue
				edges_total += 1
				var by_walk: bool = g.walks.has(e)
				var by_bridge: bool = not g.spot.is_empty() and g.spot.routes.has(e)
				if not by_walk and not by_bridge:
					side_shut += 1
					continue
				stops += 1
				var nb: Vector2i = t + Hex.NEIGHBOURS[e]
				var node := Vector3i(t.x, t.y, e)
				if land.has(nb):
					join.call(nb, node)
				banks.append([e, by_walk and not by_bridge, by_bridge])
			no_stop += 1 if stops == 0 else 0
			# edges of one bank are joined; bridges join theirs; crossings join every bank with a lane
			var shores := Water.tile_water(mask, "%d,%d" % [t.x, t.y], widths, "rapids")
			var laned := []
			for b in banks:
				if b[2]:
					join.call(Vector3i(t.x, t.y, b[0]), Vector3i(t.x, t.y, banks.filter(func(x): return x[2])[0][0]))
				if b[1]:
					laned.append(b[0])
			for k in range(1, laned.size()):
				join.call(Vector3i(t.x, t.y, laned[0]), Vector3i(t.x, t.y, laned[k]))
			one_lane += 1 if g.lanes.size() == 1 else 0
			var land_sides := 0
			for sh in Gorge._shores(mask, "%d,%d" % [t.x, t.y], widths)[1]:
				land_sides += 1 if not sh.land_edges().is_empty() else 0
			if land_sides >= 2:
				two_sides += 1
				if not g.spot.is_empty():
					two_bridge += 1
				elif laned.size() >= 2 and _lanes_apart(mask, g):
					two_lanes += 1
				else:
					two_neither += 1
			if not g.spot.is_empty() and g.lanes.size() >= 2:
				var hub: Vector2 = Water.water_routes(mask, "%d,%d" % [t.x, t.y], widths, "rapids").hub
				var axis := Vector2.from_angle(g.spot.angle) * Water.BRIDGE_HALF
				if Water.seg_dist(hub, g.spot.middle - axis, g.spot.middle + axis) < 0.75:
					under_deck += 1
		var roots := {}
		for t: Vector2i in land:
			var r = find.call(t)
			roots[r] = roots.get(r, 0) + 1
		var most := 0
		for r in roots:
			most = maxi(most, roots[r])
		land_total += land.size()
		land_cut += land.size() - most
		cut_regions += 1 if roots.size() > 1 else 0
	print("GORGE WALLED %d regions of 3 to 14 tiles, %d tiles, two rings of land round each" % [regions, tiles_total])
	print("GORGE WALLED regions where some land can't reach the rest even by crossing: %d; land tiles cut off: %d of %d" % [cut_regions, land_cut, land_total])
	print("GORGE WALLED tiles with no land at all, no way on or off: %d; tiles with land but no way onto it: %d; tiles with one lane, so no crossing on that tile unless by a bridge: %d" % [no_land, no_stop, one_lane])
	print("GORGE WALLED tiles with land on two or more sides: %d; a bridge %d, lanes to cross by %d, neither %d" % [two_sides, two_bridge, two_lanes, two_neither])
	_river_lines()
	print("GORGE WALLED land edges with no lane or bridge: %d of %d; tiles where a crossing's middle is under a bridge's deck: %d" % [side_shut, edges_total, under_deck])


static func _lanes_apart(_mask: Array, g: Dictionary) -> bool:
	return g.lanes.size() >= 2


## A river of rapids from one side of the land to the other, with nothing placed past its ends: can a party get across at all?
func _river_lines() -> void:
	var rnd := RandomNumberGenerator.new()
	rnd.seed = 47
	for size in [3, 5, 7, 12]:
		var none := 0
		var crossings := 0
		const RUNS := 150
		for _n in RUNS:
			var line: Array = [Vector2i.ZERO]
			var guard := 0
			while line.size() < size and guard < 200:
				guard += 1
				var c: Vector2i = line[-1] + Hex.NEIGHBOURS[rnd.randi_range(0, 5)]
				if not c in line and Hex.NEIGHBOURS.filter(func(n): return c + n in line).size() == 1:
					line.append(c)
			var ways := 0
			for t: Vector2i in line:
				var mask := []
				var near := []
				for n in Hex.NEIGHBOURS:
					mask.append(t + n in line)
					near.append("rapids" if t + n in line else "plains")
				var g := Gorge.build(mask, "%d,%d" % [t.x + _n * 40, t.y], Water.edge_widths("rapids", near), false)
				if not g.spot.is_empty() or g.lanes.size() >= 2:
					ways += 1
			crossings += ways
			none += 1 if ways == 0 else 0
		print("GORGE WALLED a %d-tile river: on average %.1f tiles to cross on, none at all in %d of %d" % [size, float(crossings) / RUNS, none, RUNS])


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
