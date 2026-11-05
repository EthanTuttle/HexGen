class_name SwampCheck
extends Node
## Checks the swamp kit (tiles v68, art/handoff/swamp_kit.md) in the game (`-- --swampcheck`, add `--shots` for screens/swamp_*.png):
## the wetland per variant, old pieces gone, shared edges, cover off water and planks, walks on trails, landmark walks and heights,
## a rebuilt neighbour, a region turning off the main thread, triangles and times. Prints SWAMP OK / SWAMP FAIL lines, then SWAMP DONE.
## A test aid only.

var game: Game
var shots := false
var failed := 0
var map: MapBoard


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("SWAMP %s: %s" % ["OK" if ok else "FAIL", what])
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
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("swamp_%s.png" % name))
		print("SAVED swamp_%s" % name)


func _region(variant: String) -> Dictionary:
	for g in game.regions:
		if g.variant == variant:
			return g
	return {}


func _middle(tiles: Array) -> Vector3:
	var at := Vector2.ZERO
	for t: Vector2i in tiles:
		at += Hex.tile_position(t.x, t.y)
	return Hex.to3(at / tiles.size())


func _look(at: Vector3, dist: float, tilt: float, name: String) -> void:
	game.rig.player_moved = false
	game.rig.frame(at, dist, tilt)
	await _wait(0.6)
	await _shot(name)


func _run() -> void:
	var t0 := Time.get_ticks_msec()
	game.spawn_forest_regions()
	print("SWAMP spawn of every debug region took %d ms" % (Time.get_ticks_msec() - t0))
	await _wait(1.0)
	map = game.map
	game.debug_auto_cross = true
	_check_every_look()
	_check_tiles()
	_check_edges()
	_check_kit()
	_check_cover()
	await _pictures()
	await _walks()
	await _landmarks()
	await _neighbour()
	await _region_turning()
	await _perf()
	await _wait(0.5)
	print("SWAMP DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## Every look that can be a plain tile, at many spots, with a trail through it, starting on it and none: no spot should be able to break it.
func _check_every_look() -> void:
	var made := 0
	var bad := 0
	for look: String in ["swamp", "bog", "wisp_marsh", "rot_swamp", "smugglers_bayou"]:
		for q in range(-6, 7, 3):
			for r in range(-6, 7, 3):
				for row: Array in [[[], null], [[2], 2], [[1, 4], 4]]:
					var tile := SwampLands.marsh_tile({Vector2i(q, r): look}, q, r, row[0], row[1])
					made += 1
					if tile.finish != null and not SwampLands.FINISH.has(look):
						bad += 1
	_check(bad == 0, "%d plain tiles worked out with trail edges and without, on every look (a tier 0 swamp with a trail has no finish)" % made)


func _check_tiles() -> void:
	for v: String in Game.DEBUG_SWAMPS:
		var g := _region(v)
		_check(not g.is_empty(), "%s: the 12-tile region is on the map" % v)
		var lm: Vector2i = g.landmark_tile
		_check(map.terrains[lm] == Variants.LANDMARK_OF[v], "%s: its landmark %s stands on its tile" % [v, map.terrains[lm]])
		var worst := 0
		var props := 0
		var old := 0
		var meshed := 0
		var dry := INF
		var water := 0
		for t: Vector2i in g.tiles:
			var tile := map.marsh_of(t)
			worst = maxi(worst, SwampLands.tile_tris(tile) + SwampLands.LANDMARK_TRIS.get(tile.name, 0))
			props += tile.props.size()
			water += tile.water.size()
			var node := map.tile_node(t)
			for c in node.get_children():
				if c is MeshInstance3D and c.has_meta("piece"):
					var piece := String(c.get_meta("piece"))
					if piece.begins_with("base_") or piece == tile.name + "_centre":
						continue
					old += 1
			if node.get_node_or_null("marsh_props") != null:
				meshed += 1
			for tri: Array in tile.water:
				for q: Vector2 in tri:
					dry = minf(dry, SwampLands.line_dist(q, tile.lines))
					if not tile.trail_lines.is_empty() and tile.pond == null:   # a landing stage's pool lies at its own trail's end
						dry = minf(dry, SwampLands.line_dist(q, tile.trail_lines) + 0.08)
		_check(worst <= SwampLands.PROP_BUDGET, "%s: at most %d triangles a tile, before its slab, against the budget of %d" % [v, worst, SwampLands.PROP_BUDGET])
		_check(old == 0, "%s: no old wedge or centre pieces placed (%d)" % [v, old])
		_check(meshed == g.tiles.size(), "%s: each tile's %d props are merged into one mesh (%d in all)" % [v, props / g.tiles.size(), props])
		_check(water > 0 and dry >= SwampLands.WATER_DRY - 0.03, "%s: water stays off every route and trail, %.2f m at closest" % [v, dry])
	var t0_tiles := []
	for t: Vector2i in map.terrains:
		if map.terrains[t] == "swamp":
			t0_tiles.append(t)
	_check(t0_tiles.size() == 7, "tier 0: the swamp group is on the map (%d tiles)" % t0_tiles.size())
	_check(t0_tiles.all(func(t): return map.marsh_of(t).trails.is_empty()), "tier 0 has no trails")
	var bog := _region("bog")
	var far := 0
	for t: Vector2i in bog.tiles:
		if map.marsh_of(t).finish != null:
			far += 1
			_check(map.marsh_of(t).props.any(func(o): return o[0] == "bog_trail_end"), "a bog far tile %s has its finish" % t)
	_check(far > 0, "the bog region has %d far tiles with finishes" % far)
	var bayou := _region("smugglers_bayou")
	var shacks := 0
	var spurs := 0
	for t: Vector2i in bayou.tiles:
		for o: Array in map.marsh_of(t).props:
			shacks += 1 if o[0] == "bayou_shack" else 0
		spurs += map.marsh_of(t).spurs.size()
	_check(shacks > 0, "the bayou has %d shacks and %d spurs" % [shacks, spurs])


## Water reaching a shared edge from one side reaches it at the same places from the other.
func _check_edges() -> void:
	var worst := 0.0
	var pairs := 0
	for v: String in Game.DEBUG_SWAMPS:
		for t: Vector2i in _region(v).tiles:
			for i in 3:
				var o: Vector2i = t + Hex.NEIGHBOURS[i]
				if not SwampLands.LOOKS.has(map.terrains.get(o)) or SwampLands.LOOKS[map.terrains[o]] != SwampLands.LOOKS[map.terrains[t]]:
					continue
				var a := _edge_length(map.marsh_of(t).water, i)
				var b := _edge_length(map.marsh_of(o).water, (i + 3) % 6)
				worst = maxf(worst, absf(a - b))
				pairs += 1
	_check(pairs > 0 and worst < 0.01, "water meets across %d shared edges, worst difference %.4f m" % [pairs, worst])


static func _edge_length(tris: Array, i: int) -> float:
	var n := Water.normal(i)
	var total := 0.0
	for t: Array in tris:
		if t[0].dot(n) > Water.A - 1e-3 and t[1].dot(n) > Water.A - 1e-3 and t[2].dot(n) > Water.A - 1e-3:
			continue   # a sliver lying wholly on the edge, of no area
		for j in 3:
			var a: Vector2 = t[j]
			var b: Vector2 = t[(j + 1) % 3]
			if a.dot(n) > Water.A - 1e-3 and b.dot(n) > Water.A - 1e-3:
				total += a.distance_to(b)
	return total


func _check_kit() -> void:
	var kit: Dictionary = map._kit
	var missing := []
	var off := []
	for name: String in SwampLands.PROP:
		if not kit.has(name):
			missing.append(name)
			continue
		var tris := 0
		var mesh: Mesh = kit[name]
		for k in mesh.get_surface_count():
			tris += (mesh.surface_get_arrays(k)[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
		if absf(tris - SwampLands.PROP[name][2]) > maxf(8.0, SwampLands.PROP[name][2] * 0.25):
			off.append("%s %d against %d" % [name, tris, SwampLands.PROP[name][2]])
	_check(missing.is_empty(), "every prop is in the kit %s" % str(missing))
	print("SWAMP kit triangles different from the table: %s" % str(off))
	var empty := []
	for v in ["swamp_centre", "bog_centre", "wisp_marsh_edge_trail", "rot_swamp_centre", "smugglers_bayou_edge_same", "plaguepit_edge_same"]:
		if kit.has(v):
			empty.append(v)
	_check(empty.is_empty(), "the old wedges and centres are empty in the kit %s" % str(empty))
	var wisps: int = map.tile_node(_region("wisp_marsh").landmark_tile).find_children("wisps", "MeshInstance3D", true, false).size()
	_check(wisps == 1, "Wisp Hollow has its wisps")
	var pit: Vector2i = _region("rot_swamp").landmark_tile
	_check(map.tile_node(pit).find_children("bubbles", "MeshInstance3D", true, false).size() == 1 and map.tile_node(pit).find_children("haze", "MeshInstance3D", true, false).size() == 1, "the Plague Pit has its bubbles and haze")
	_check(not map.tile_node(pit).get_children().any(func(c): return c is MeshInstance3D and c.has_meta("piece") and String(c.get_meta("piece")).begins_with("base_")), "the Plague Pit has no slab")


## No tuft on water, mud, planks or a track.
func _check_cover() -> void:
	var bad := 0
	var count := 0
	for v: String in Game.DEBUG_SWAMPS:
		for t: Vector2i in _region(v).tiles:
			var tile := map.marsh_of(t)
			var c := Hex.tile_position(t.x, t.y)
			for ix in range(int(floor((c.x - GroundCover.A) / GroundCover.CELL)), int(ceil((c.x + GroundCover.A) / GroundCover.CELL))):
				for iy in range(int(floor((c.y - GroundCover.R) / GroundCover.CELL)), int(ceil((c.y + GroundCover.R) / GroundCover.CELL))):
					var p := Vector2((ix + GroundCover.hash01(ix, iy, 0)) * GroundCover.CELL, (iy + GroundCover.hash01(ix, iy, 1)) * GroundCover.CELL)
					if GroundCover.tile_at(p) != t:
						continue
					var item := GroundCover._keep(map.terrains, map.water_shapes, ix, iy, p, [], {t: tile})
					if item.is_empty():
						continue
					count += 1
					var local := p - c
					if SwampLands._field_at(tile, local).x > 0.0 or SwampLands.cover_wet(map.terrains, {t: tile}, p.x, p.y, t):
						bad += 1
	_check(count > 0 and bad == 0, "%d tufts on the regions, none on water, mud, planks or tracks (%d)" % [count, bad])


## The mist pieces on bayou and rot swamp (tiles v76: alpha in COLOR_0, white if it's not used), and the Plague Pit from any side with nothing beside it.
func _mist_and_pit() -> void:
	for v in ["smugglers_bayou", "rot_swamp"]:
		for t: Vector2i in _region(v).tiles:
			if map.marsh_of(t).props.any(func(p): return String(p[0]).begins_with("marsh_mist")):
				_check(true, "%s: mist pieces on %s" % [v, t])
				await _look(Hex.to3(Hex.tile_position(t.x, t.y)), 12.0, 32.0, "mist_%s" % v)
				break
	var pit: Vector2i = _region("rot_swamp").landmark_tile
	await _look(Hex.to3(Hex.tile_position(pit.x, pit.y)), 11.0, 45.0, "pit_top")
	# As on a map's edge: nothing beside it. Its tile's pieces don't depend on its neighbours, so hide those.
	var hidden: Array[Node3D] = []
	for t: Vector2i in map.terrains:
		var node := map.tile_node(t)
		if t != pit and Rules.hex_distance(t, pit) <= 2 and node and node.visible:
			node.visible = false
			hidden.append(node)
	for i in [0, 2, 4]:
		var out := Water.normal(i)
		game.rig.frame(Hex.to3(Hex.tile_position(pit.x, pit.y) + out * Hex.A), 11.0, 18.0, rad_to_deg(atan2(-out.x, -out.y)))
		await _wait(0.6)
		await _shot("pit_edge_%d" % i)
	for node in hidden:
		node.visible = true


func _pictures() -> void:
	game.ui.visible = false
	var n := 1
	await _mist_and_pit()
	for v: String in Game.DEBUG_SWAMPS:
		var g := _region(v)
		await _look(_middle(g.tiles), 34.0, 50.0, "%02d_%s_map" % [n, v]); n += 1
		var lm: Vector2i = g.landmark_tile
		await _look(Hex.to3(Hex.tile_position(lm.x, lm.y)), 15.0, 42.0, "%02d_%s_landmark" % [n, v]); n += 1
		await _look(_middle(g.tiles), 15.0, 22.0, "%02d_%s_low" % [n, v]); n += 1
		var far = null
		for t: Vector2i in g.tiles:
			if map.marsh_of(t).finish != null:
				far = t
				break
		if far != null:
			var f: Array = map.marsh_of(far).finish
			await _look(Hex.to3(Hex.tile_position(far.x, far.y) + Vector2(f[1], f[2])), 9.0, 38.0, "%02d_%s_end" % [n, v]); n += 1
	var tier0 := []
	for t: Vector2i in map.terrains:
		if map.terrains[t] == "swamp":
			tier0.append(t)
	await _look(_middle(tier0), 26.0, 50.0, "%02d_tier0" % n); n += 1
	# Night: wisps and glows show.
	SwampFx.set_night(1.0)
	await _look(_middle(_region("wisp_marsh").tiles), 20.0, 40.0, "%02d_wisp_marsh_night" % n); n += 1
	SwampFx.set_night(0.0)
	game.ui.visible = true


func _start_at(t: Vector2i) -> void:
	game.party_tile = t
	game.party_node.place_at(t)
	game.rig.player_moved = false
	game.rig.frame(game.party_node.centre(), 18.0, 45.0)
	await _wait(0.3)


## Follows every mini through a walk: the worst its middle comes to water, and its worst gap from the height the route says.
func _follow(goal: Vector2i) -> Dictionary:
	var out := {wet = INF, gap = 0.0, tilt = 0.0, lowest = INF, highest = -INF, frames = 0, off_trail = 0.0}
	game.walk_to(goal)
	while game.busy:
		await get_tree().process_frame
		for m in game.party_node.members:
			var node: Node3D = m.node
			var p := Vector2(node.position.x, -node.position.z)
			var t := GroundCover.tile_at(p)
			if SwampLands.LOOKS.has(map.terrains.get(t)):
				var tile := map.marsh_of(t)
				out.wet = minf(out.wet, -SwampLands._field_at(tile, p - tile.centre).x / SwampLands.K)
			var z := map.walk_z(p)
			if not is_nan(z):
				out.gap = maxf(out.gap, absf(node.position.y - z))
			out.tilt = maxf(out.tilt, rad_to_deg((m.up as Vector3).angle_to(Vector3.UP)))
			out.lowest = minf(out.lowest, node.position.y)
			out.highest = maxf(out.highest, node.position.y)
			out.frames += 1
	await _wait(Rules.SETTLE_SECONDS)
	return out


## A tile on the region with two trail edges, and the tiles on either side of it, for a walk along its trail.
func _trail_tile(g: Dictionary) -> Array:
	for t: Vector2i in g.tiles:
		var edges := LandmarkFlow.trail_edges(t, map.flow_toward)
		if edges.size() >= 2 and not Variants.LANDMARKS.has(map.terrains[t]):
			return [t, t + Hex.NEIGHBOURS[edges[0]], t + Hex.NEIGHBOURS[edges[1]], edges[0], edges[1]]
	return []


func _walks() -> void:
	for v: String in Game.DEBUG_SWAMPS:
		var g := _region(v)
		var way := _trail_tile(g)
		if way.is_empty():
			_check(false, "%s has a tile with two trail edges" % v)
			continue
		var mid: Vector2i = way[0]
		var line := map.marsh_way(mid, way[3], way[4])
		_check(line.size() == 25, "%s: a trail tile's way between its trail edges is its bent line" % v)
		await _start_at(way[1])
		var r := map.marsh_way(mid, way[4], way[3])
		_check(r.size() == 25 and r[0].distance_to(line[-1]) < 0.001, "%s: the same line either way" % v)
		var at_edge := Hex.tile_position(mid.x, mid.y) + Water.normal(way[3]) * Water.A
		_check(line[0].distance_to(at_edge) < 0.001, "%s: it starts at the edge's middle, so it meets the next tile's" % v)
		var preview: PackedVector2Array = game.party_node.route_preview([mid, way[2]] as Array[Vector2i])
		var off := 0.0
		var through := 0
		for p in preview:
			if GroundCover.tile_at(p) == mid:
				through += 1
				off = maxf(off, SwampLands.line_dist(p, [line]))
		_check(through > 0 and off < 0.12, "%s: the route across keeps within %.3f m of the trail's line" % [v, off])
		var w := await _follow(way[2])
		_check(game.party_tile == way[2], "%s: the party walked the trail" % v)
		_check(w.wet > 0.0, "%s: every mini's middle stays dry on it, %.2f m from water at closest" % [v, w.wet])
		if v == "smugglers_bayou":
			_check(absf(map.walk_z(line[12]) - 0.045) < 0.001, "on the boardwalk a mini stands at 0.045")
		# Off a trail: the usual curve between edges that aren't both trail edges.
		await _shot("%s_walked" % v)
	var t0 := []
	for t: Vector2i in map.terrains:
		if map.terrains[t] == "swamp":
			t0.append(t)
	await _start_at(t0[1])
	var w := await _follow(t0[0])
	_check(game.party_tile == t0[0] and w.wet > 0.0, "tier 0: a walk stays dry, %.2f m from water at closest" % w.wet)


func _landmarks() -> void:
	for v: String in Game.DEBUG_SWAMPS:
		var g := _region(v)
		var lm: Vector2i = g.landmark_tile
		var name: String = map.terrains[lm]
		var out := Vector2i.MAX
		for n in Hex.NEIGHBOURS:
			if g.tiles.has(lm + n):
				out = lm + n
				break
		await _start_at(out)
		var r := await _follow(lm)
		var hero: Node3D = game.party_node.members[0].node
		var line: Array = SwampLands.landmark_routes(name, map.landmark_turns[lm]).values()[0]
		var stop: Vector3 = line[-1]
		var at := Hex.tile_position(lm.x, lm.y)
		_check(game.party_tile == lm, "%s: the party reached it" % name)
		_check(Vector2(hero.position.x, -hero.position.z).distance_to(at + Vector2(stop.x, stop.y)) < 0.3, "%s: the hero stops at its stop" % name)
		_check(absf(hero.position.y - stop.z) < 0.08, "%s: at height %.2f, the stop's %.2f" % [name, hero.position.y, stop.z])
		_check(r.gap < 0.2, "%s: minis keep to the route's height within %.3f m" % [name, r.gap])
		_check(r.tilt < 28.5, "%s: the steepest a base tilts is %.1f degrees" % [name, r.tilt])
		_check(r.wet > 0.0 or name == "plaguepit", "%s: everyone stays dry, %.2f m from water at closest" % [name, r.wet])
		game.ui.visible = false
		await _look(game.party_node.centre(), 11.0, 38.0, "landmark_party_%s" % name)
		game.ui.visible = true
		var back := await _follow(out)
		_check(game.party_tile == out and back.gap < 0.2, "%s: and walks out again" % name)
		# Walking past, from one side of it to another.
		game.party_node.place_at(lm)


## A neighbour landing rebuilds a tile's wetland: water stops short of a different look.
func _neighbour() -> void:
	var at := Vector2i.ZERO
	for t: Vector2i in map.terrains:
		if map.terrains[t] == "swamp":
			var free := 0
			for n in Hex.NEIGHBOURS:
				free += 0 if map.terrains.has(t + n) else 1
			if free == 0:
				at = t
				break
	var before := map.marsh_of(at)
	var key: String = map._marsh[at].key
	map.retile({at + Hex.NEIGHBOURS[0]: "plains"})
	await _wait(0.2)
	var after := map.marsh_of(at)
	_check(map._marsh[at].key != key, "a neighbour changing look rebuilds a swamp tile")
	var reach := 0.0
	var n0 := Water.normal(0)
	for tri: Array in after.water:
		for q: Vector2 in tri:
			reach = maxf(reach, q.dot(n0))
	_check(reach <= Water.A - SwampLands.CLOSE + 0.06, "water stops short of an edge it can't cross (%.2f of %.2f)" % [reach, Water.A])
	var again := map.marsh_of(at)
	_check(again == after, "the same tile unchanged isn't rebuilt (was %d triangles, %d now)" % [before.water.size(), after.water.size()])


func _region_turning() -> void:
	var c := game._free_spot(Game.DEBUG_PLAINS_SHAPE, {})
	var tiles: Array[Vector2i] = []
	var changes := {}
	for s: Vector2i in Game.DEBUG_PLAINS_SHAPE:
		tiles.append(c + s)
		changes[c + s] = "swamp"
	var t0 := Time.get_ticks_usec()
	map.retile(changes)
	print("SWAMP PERF %d swamp tiles placed at once, on the main thread: %d ms" % [tiles.size(), (Time.get_ticks_usec() - t0) / 1000])
	await _wait(0.3)
	var t1 := Time.get_ticks_usec()
	map.retile({c + Vector2i(4, 0): "swamp"})
	print("SWAMP PERF one swamp card beside them: %d ms" % ((Time.get_ticks_usec() - t1) / 1000))
	await _wait(0.2)
	var region := game.new_region("swamp", tiles, "smugglers_bayou", game._landmark_tile("smugglers_bayou", tiles))
	game.rig.player_moved = false
	game.rig.frame(_middle(tiles), 34.0, 50.0)
	await _wait(0.5)
	var worst := 0
	map.marsh_data_us = 0
	map.marsh_build_us = 0
	map.marsh_cover_us = 0
	game._transform(tiles, region, c)
	await get_tree().process_frame
	var t2 := Time.get_ticks_usec()
	while game.busy:
		await get_tree().process_frame
		var t3 := Time.get_ticks_usec()
		worst = maxi(worst, t3 - t2)
		t2 = t3
	print("SWAMP PERF a %d-tile region turning into a bayou: wetland %d ms off the main thread, worst frame %.1f ms" % [tiles.size(), map.marsh_job_ms, worst / 1000.0])
	print("SWAMP PERF of that frame: %.1f ms building marsh tiles, %.1f of it their data, %.1f ms their ground cover" % [map.marsh_build_us / 1000.0, map.marsh_data_us / 1000.0, map.marsh_cover_us / 1000.0])
	_check(map.terrains[region.landmark_tile] == "thievesguild" and tiles.all(func(t): return SwampLands.LOOKS[map.terrains[t]] == "smugglers_bayou"), "a tier 0 swamp turns into a bayou region")
	_check(tiles.all(func(t): return map.tile_node(t).get_node_or_null("marsh") != null or map.marsh_of(t).bank.is_empty()), "with its wetland rebuilt")
	await _shot("region_turned")


func _perf() -> void:
	var vsync := DisplayServer.window_get_vsync_mode()
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	for v: String in Game.DEBUG_SWAMPS:
		for view: float in [58.0, 30.0]:
			game.rig.player_moved = false
			game.rig.frame(_middle(_region(v).tiles), view, 50.0)
			await _wait(0.6)
			var t0 := Time.get_ticks_usec()
			for _f in 120:
				await get_tree().process_frame
			print("SWAMP PERF %s at distance %d: draw calls %d, triangles %d, objects %d; %.1f ms a frame on this Mac" % [v, int(view),
					Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
					Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME), (Time.get_ticks_usec() - t0) / 120000.0])
	DisplayServer.window_set_vsync_mode(vsync)
	var worst := 0
	var most := ""
	var seen := 0
	for v: String in Game.DEBUG_SWAMPS:
		for t: Vector2i in _region(v).tiles:
			var total := 0
			for mi in map.tile_node(t).find_children("*", "MeshInstance3D", true, false):
				if mi.mesh is ArrayMesh or mi.mesh is Mesh:
					for k in mi.mesh.get_surface_count():
						var a: Array = mi.mesh.surface_get_arrays(k)
						total += (a[Mesh.ARRAY_INDEX].size() if a[Mesh.ARRAY_INDEX] != null else a[Mesh.ARRAY_VERTEX].size()) / 3
			seen += 1
			if total > worst:
				worst = total
				most = map.terrains[t]
	print("SWAMP PERF heaviest of %d tiles: %d triangles with its slab, cover and effects (%s), against 4,816" % [seen, worst, most])
	_check(worst <= 4816, "every tile fits the 4,816 budget (%d)" % worst)
