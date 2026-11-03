class_name TownCheck
extends Node
## Checks the village kit (tiles v50) in the game (`-- --towncheck`, add `--shots` for screens/town_*.png): streets and
## the pieces they pick, centres, the fortified town's walls and gatehouses, and a party walking through each town and
## out by its gates, with every mini on the streets and through a wall or fence only at a gate. Prints TOWN OK / TOWN FAIL
## lines, then TOWN DONE. A test aid only.

const KITS := ["market_town", "fortified_town", "slums", "scholars_town"]
const STREET := 0.6        # half a main street; a mini's middle stays within it (a route's within 0.1 of the line)
const GATE := 0.7          # how far from a gate's middle a mini may pass (the file of walking minis has some width)

var game: Game
var shots := false
var failed := 0


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("TOWN %s: %s" % ["OK" if ok else "FAIL", what])
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
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("town_%s.png" % name))
		print("SAVED town_%s" % name)


func _region(variant: String) -> Dictionary:
	for g in game.regions:
		if g.variant == variant:
			return g
	return {}


func _pieces(t: Vector2i) -> Array:
	return game.map.tile_node(t).get_children().filter(func(c): return c is MeshInstance3D and c.has_meta("piece"))


func _steps(c: Node3D) -> int:
	return posmod(roundi(rad_to_deg(c.rotation.y) / 60.0), 6)


func _has(t: Vector2i, piece: String, steps: int) -> bool:
	return _pieces(t).any(func(c): return c.get_meta("piece") == piece and _steps(c) == steps)


func _run() -> void:
	game.spawn_forest_regions()
	await _wait(1.0)
	var map := game.map
	if "--lines" in OS.get_cmdline_user_args():   # only the party's line at the hub
		await _after_fight(map)
		print("TOWN DONE: %d failed" % failed)
		get_tree().quit()
		return
	_check_streets(map)
	for v in KITS:
		_check(not _region(v).is_empty(), "%s: spawned" % v)
	_check_wedges(map)
	_check_centres(map)
	_check_walls(map)
	_check_effects(map)
	_check_routes(map)
	await _pictures(map)
	for v in KITS:
		await _walk_town(map, v)
	await _walk_through_wall(map)
	await _walk_tier0(map)
	await _after_fight(map)
	await _perf_views(map)
	print("TOWN DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## Both sides of every street agree, none leads nowhere, and each farm and village group is one network.
func _check_streets(map: MapBoard) -> void:
	var agree := true
	var nowhere := true
	var count := 0
	for t: Vector2i in map.streets:
		for i: int in map.streets[t]:
			count += 1
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if map.streets.has(n):
				agree = agree and map.streets[n].get((i + 3) % 6) == map.streets[t][i]
			else:
				nowhere = nowhere and Variants.terrain_of(map.terrains.get(n)) == "farmland"
	_check(agree, "streets: both sides of every edge agree (%d street ends)" % count)
	_check(nowhere, "streets: none leads nowhere")
	var seen := {}
	var one := true
	for start: Vector2i in map.streets:
		if seen.has(start):
			continue
		# The whole group by touching, then what the streets and farm tracks reach.
		var group := {start: true}
		var todo: Array[Vector2i] = [start]
		while not todo.is_empty():
			var c: Vector2i = todo.pop_back()
			for n in Hex.NEIGHBOURS:
				var m: Vector2i = c + n
				if not group.has(m) and Variants.terrain_of(map.terrains.get(m)) in ["village", "farmland"]:
					group[m] = true
					todo.append(m)
		var reached := {start: true}
		todo = [start]
		while not todo.is_empty():
			var c: Vector2i = todo.pop_back()
			for i in 6:
				var m: Vector2i = c + Hex.NEIGHBOURS[i]
				if group.has(m) and not reached.has(m) and map.edge_open(c, m):
					reached[m] = true
					todo.append(m)
		one = one and reached.size() == group.size()
		for c: Vector2i in group:
			seen[c] = true
	_check(one, "streets: each farm and village group is one network")


## The hand-off's table, edge by edge.
func _check_wedges(map: MapBoard) -> void:
	var by_kit := {}
	for t: Vector2i in map.streets:
		var name: String = map.terrains[t]
		var kit := Variants.wedges_of(name)
		var trails := LandmarkFlow.trail_edges(t, map.flow_toward)
		var ok := true
		for i in 6:
			var near = map.terrains.get(t + Hex.NEIGHBOURS[i])
			var joined := Variants.terrain_of(near) in ["village", "farmland"]
			var want := ""
			var lm := Variants.LANDMARKS.has(name)
			if joined and kit == "fortified_town" and Variants.wedges_of(near) != kit:
				want = "_edge_gate" if map.streets[t].has(i) else ("_edge_other_lm" if lm else "_edge_other")
			elif i in trails and kit != "village":
				want = "_edge_trail"
			elif joined:
				match map.streets[t].get(i, ""):
					"main": want = "_edge_same"
					"side": want = "_edge_side"
					_: want = "_edge_block_lm" if lm and kit != "village" else "_edge_block"
			elif i in map.gates.get(t, []):
				want = "_edge_gate"
			else:
				want = "_edge_other_lm" if lm and kit != "village" else "_edge_other"
			ok = ok and _has(t, kit + want, i)
		by_kit[kit] = by_kit.get(kit, true) and ok
	for kit in by_kit:
		_check(by_kit[kit], "%s: every edge's wedge as the hand-off's table says" % kit)


func _check_centres(map: MapBoard) -> void:
	for v in KITS:
		var g := _region(v)
		var lm: Vector2i = g.landmark_tile
		var ok := _has(lm, map.terrains[lm] + "_centre", map.landmark_turns[lm])
		var looks := {}
		for t: Vector2i in g.tiles:
			if t == lm:
				continue
			var d: int = map.flow_dist[t]
			var hash_turn := int(GroundCover.hash01(t.x * 31 + 7, t.y * 17 + 3, 14) * 6)
			var piece: String = v + ("_centre_b" if GroundCover.hash01(t.x, t.y, 13) < 0.5 else "_centre")
			var turn := hash_turn
			if d == 1:
				piece = v + "_centre_near"
			elif d == 2 and v == "fortified_town":
				piece = v + "_centre_mid"
			if v == "fortified_town" and d <= 2:
				turn = LandmarkFlow.toward_edge(t, map.flow_toward)
			ok = ok and _has(t, piece, turn)
			looks[piece] = true
		_check(ok, "%s: landmark turned to its longest trail; %d kinds of centre at their turns" % [v, looks.size()])


func _check_walls(map: MapBoard) -> void:
	var g := _region("fortified_town")
	var unbroken := true
	var facing_kin := 0
	var gatehouses := 0
	for t: Vector2i in g.tiles:
		var name: String = map.terrains[t]
		for i in 6:
			var near = map.terrains.get(t + Hex.NEIGHBOURS[i])
			var inside := Variants.wedges_of(near) == "fortified_town" if near != null else false
			if inside:
				continue
			var wall := _has(t, "fortified_town_edge_other", i) or _has(t, "fortified_town_edge_other_lm", i) or _has(t, "fortified_town_edge_gate", i)
			unbroken = unbroken and wall
			if Variants.terrain_of(near) in ["village", "farmland"]:
				facing_kin += 1
				var street: bool = map.streets[t].has(i)
				unbroken = unbroken and _has(t, "fortified_town_edge_gate", i) == street
				gatehouses += 1 if street else 0
	_check(unbroken, "fortified town: a wall on every edge out of the region, a gatehouse only where a gate or street goes")
	_check(facing_kin > 0 and gatehouses > 0, "fortified town: %d edges against a plain village or farm, %d with a gatehouse" % [facing_kin, gatehouses])
	var joins := true
	var count := 0
	for t: Vector2i in g.tiles:
		for i in 6:
			var inside := func(k: int) -> bool:
				var near = map.terrains.get(t + Hex.NEIGHBOURS[posmod(k, 6)])
				return near != null and Variants.wedges_of(near) == "fortified_town"
			if inside.call(i):
				var l: bool = not inside.call(i + 1)
				var r: bool = not inside.call(i - 1)
				joins = joins and l == _has(t, "fortified_town_border_join_l", i) and r == _has(t, "fortified_town_border_join_r", i)
				count += int(l) + int(r)
			else:
				joins = joins and not _has(t, "fortified_town_border_join_l", i) and not _has(t, "fortified_town_border_join_r", i)
		joins = joins and not _pieces(t).any(func(c): return c.get_meta("piece") in ["border_join_l", "border_join_r"])
	_check(joins and count > 0, "fortified town: its own border joins, %d of them, where the wall runs out to a shared edge" % count)
	# A neighbour's wedge is unchanged, with no fence of its own on that edge.
	var plain := true
	for t: Vector2i in g.tiles:
		for i in 6:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if map.terrains.get(n) == "village":
				plain = plain and not _has(n, "village_edge_other", (i + 3) % 6) and not _has(n, "village_edge_gate", (i + 3) % 6)
	_check(plain, "a plain village against the wall has no fence of its own there")
	var no_cliff := true
	for t: Vector2i in map.gates:
		for i: int in map.gates[t]:
			if Variants.terrain_of(map.terrains.get(t + Hex.NEIGHBOURS[i])) in ["village", "farmland"]:
				no_cliff = false
	_check(no_cliff, "fence gates only open onto land outside the group")


func _check_effects(map: MapBoard) -> void:
	_check(map._lantern_red != null and map._lantern_red.emission_enabled, "lantern_red has its own glowing material")
	for v in ["fortified_town", "slums"]:
		var g := _region(v)
		var points := 0
		var nodes := 0
		for t: Vector2i in g.tiles:
			for c in map.tile_node(t).get_children():
				if c.name.begins_with("town_smoke"):
					nodes += 1
					points += (c as GPUParticles3D).amount / 2
		_check(nodes > 0, "%s: %d chimneys' smoke, in %d particle nodes" % [v, points, nodes])
	var none := true
	for v in ["market_town", "scholars_town"]:
		for t: Vector2i in _region(v).tiles:
			for c in map.tile_node(t).get_children():
				none = none and not c.name.begins_with("town_smoke")
	_check(none, "no smoke on market towns or scholars' towns")


## Every tile of every town can be reached, on routes along the drawn streets, whichever way they come.
func _check_routes(map: MapBoard) -> void:
	for v in KITS:
		var g := _region(v)
		var reach := true
		var worst := 0.0
		for t: Vector2i in g.tiles:
			var path := game.path_to(t)
			reach = reach and not path.is_empty()
			if path.is_empty():
				continue
			var route := game.party_node.route_preview(path)
			for p in route:
				var c := GroundCover.tile_at(p)
				if g.tiles.has(c):
					worst = maxf(worst, map.path_graph(c).distance_to_paths(p))
		_check(reach, "%s: every tile can be reached" % v)
		_check(worst <= 0.45, "%s: every route to it keeps to the streets (at most %.2f m off a street's middle)" % [v, worst])


func _pictures(map: MapBoard) -> void:
	var n := 1
	for v in KITS:
		var g := _region(v)
		var lm: Vector2i = g.landmark_tile
		var c := Hex.tile_position(lm.x, lm.y)
		for yaw in [0.0, 180.0]:
			game.rig.frame(Hex.to3(c), 58.0, 50.0, yaw)
			await _wait(0.2)
			await _shot("%02d_game_camera_%s_%d" % [n, v, int(yaw)])
			n += 1
		game.rig.frame(Hex.to3(c), 16.0, 40.0, -90.0 - rad_to_deg(map.entrance_angle(lm)))
		await _wait(0.2)
		await _shot("%02d_landmark_%s" % [n, map.terrains[lm]])
		n += 1
		var far := lm
		for t: Vector2i in g.tiles:
			if map.flow_dist[t] > map.flow_dist[far]:
				far = t
		game.rig.frame(Hex.to3(Hex.tile_position(far.x, far.y)), 12.0, 35.0)
		await _wait(0.2)
		await _shot("%02d_street_%s" % [n, v])
		n += 1
	# A gatehouse from low down, and the walls against a plain village.
	var g := _region("fortified_town")
	for t: Vector2i in g.tiles:
		for i: int in map.streets[t]:
			if Variants.wedges_of(map.terrains.get(t + Hex.NEIGHBOURS[i])) != "fortified_town":
				var at := Hex.tile_position(t.x, t.y) + Water.normal(i) * Hex.A
				game.rig.frame(Hex.to3(at), 12.0, 30.0, 90.0 + 60.0 * i + 180.0)
				await _wait(0.2)
				await _shot("40_gatehouse_to_plain_village")
				game.rig.frame(Hex.to3(at), 34.0, 50.0)
				await _wait(0.2)
				await _shot("41_wall_meets_plain_village")
				_tier0_shot(map)
				await _wait(0.2)
				await _shot("42_tier0_streets")
				return


func _tier0_shot(map: MapBoard) -> void:
	var f := Game.DEBUG_FARMS
	game.rig.frame(Hex.to3(Hex.tile_position(f.x, f.y)), 30.0, 50.0)


## Walks, watching every mini each frame: on a town or farm tile its middle stays on the streets, and it crosses a wall,
## fence or from one town tile to the next only where a street or gate goes.
func _watched(goal: Vector2i, what: String) -> void:
	var map := game.map
	var w := game.party_node
	if goal == game.party_tile:
		return
	if game.path_to(goal).is_empty():
		_check(false, "%s: no route" % what)
		return
	var off := 0.0
	var off_at := ""
	var crossings := 0
	var bad := 0
	var last: Array = w.members.map(func(m): return GroundCover.tile_at(Vector2(m.node.position.x, -m.node.position.z)))
	var first := game.party_tile
	game.walk_to(goal)
	while game.busy:
		await get_tree().process_frame
		for k in w.members.size():
			var pos: Vector3 = w.members[k].node.position
			var p := Vector2(pos.x, -pos.z)
			var t := GroundCover.tile_at(p)
			if map.gates.has(t) and w.walking and t != first:   # a party can start off the streets, as at the camp
				var d := map.path_graph(t).distance_to_paths(p)
				if d > off:
					off = d
					off_at = "%s on %s" % [p, map.terrains[t]]
			if t != last[k]:
				var a: Vector2i = last[k]
				last[k] = t
				if map.gates.has(a) or map.gates.has(t):
					crossings += 1
					var mid := (Hex.tile_position(a.x, a.y) + Hex.tile_position(t.x, t.y)) * 0.5
					if not map.edge_open(a, t) or p.distance_to(mid) > GATE:
						bad += 1
						print("  a mini crossed from %s to %s at %s, %.2f m from the middle" % [a, t, p, p.distance_to(mid)])
	await _wait(Rules.SETTLE_SECONDS)
	_check(off <= STREET, "%s: every mini on the streets (at most %.2f m off%s)" % [what, off, "" if off <= STREET else " at " + off_at])
	_check(bad == 0, "%s: %d crossings of a tile edge, all at a street or gate" % [what, crossings])
	_stopped(map, goal, what)


## Stopped: in a file on the street, none on top of another.
func _stopped(map: MapBoard, t: Vector2i, what: String) -> void:
	if map.path_graph(t).stand == null:
		return
	var ms := game.party_node.members
	var worst := 0.0
	var closest := INF
	for k in ms.size():
		var a := Vector2(ms[k].node.position.x, -ms[k].node.position.z)
		var tile := GroundCover.tile_at(a)
		if map.gates.has(tile):
			worst = maxf(worst, map.path_graph(tile).distance_to_paths(a))
		for j in k:
			closest = minf(closest, a.distance_to(Vector2(ms[j].node.position.x, -ms[j].node.position.z)))
	_check(worst <= 0.15 and closest >= Rules.FILE_GAP - 0.25, "%s: stopped in a file on the street (centres at most %.2f m off, %.2f m apart)" % [what, worst, closest])


## In by a gate, to the landmark's door, across to the far side, and out by a gate.
func _walk_town(map: MapBoard, v: String) -> void:
	var g := _region(v)
	var lm: Vector2i = g.landmark_tile
	await _watched(lm, "%s: in to the landmark" % v)
	var graph := map.path_graph(lm)
	var hero := game.party_node.centre()
	_check(Vector2(hero.x, -hero.z).distance_to(graph.nodes[graph.stand]) < 0.3, "%s: the party stops at the entrance" % v)
	game.rig.frame(hero, 16.0, 40.0, -90.0 - rad_to_deg(map.entrance_angle(lm)))
	await _wait(0.4)
	await _shot("5%d_party_at_%s" % [KITS.find(v), map.terrains[lm]])
	var far := lm
	for t: Vector2i in g.tiles:
		if map.flow_dist[t] > map.flow_dist[far]:
			far = t
	await _watched(far, "%s: across the town" % v)
	# Out by a gate, to the land beyond it.
	var out = null
	for t: Vector2i in g.tiles:
		for i: int in map.gates.get(t, []):
			out = t + Hex.NEIGHBOURS[i]
	_check(out != null, "%s: has a gate" % v)
	if out != null:
		await _watched(out, "%s: out by a gate" % v)
		_check(not g.tiles.has(game.party_tile), "%s: the party is out" % v)


## Through a gatehouse in the wall, from a plain village, and to the farm by the other.
func _walk_through_wall(map: MapBoard) -> void:
	var g := _region("fortified_town")
	var plain := []
	for t: Vector2i in g.tiles:
		for i: int in map.streets[t]:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if map.terrains.get(n) in ["village", "farmland"]:
				plain.append([t, n])
	_check(not plain.is_empty(), "the fortified town has a street through its wall")
	for pair in plain.slice(0, 2):
		await _watched(pair[1], "out to %s by a gatehouse" % map.terrains[pair[1]])
		await _watched(pair[0], "back in from %s" % map.terrains[pair[1]])


## DOCS (Walking): after a fight the party is at the hub in the tight line. Back from a fight is place_at, as in
## Game.start_fight: a party in the line stays in it, one coming from elsewhere takes it, and it can walk on from there.
func _after_fight(map: MapBoard) -> void:
	var w := game.party_node
	var f := Game.DEBUG_FARMS
	var spots := [[f, "a farm"]]
	for n: Vector2i in Hex.NEIGHBOURS:
		if map.terrains.get(f + n) == "village":
			spots.append([f + n, "a tier 0 village"])
			break
	for v in KITS:
		spots.append([_region(v).landmark_tile, v + "'s landmark"])
		for t: Vector2i in _region(v).tiles:
			if t != _region(v).landmark_tile and map.path_graph(t).stand != null:
				spots.append([t, v + "'s hub"])
				break
	for v in ["windmill_country", "raided_farms"]:
		if not _region(v).is_empty():
			spots.append([_region(v).landmark_tile, v + "'s landmark"])
	for spot in spots:
		var t: Vector2i = spot[0]
		await _watched(t, "to %s" % spot[1])
		var was: Array = w.members.map(func(m): return m.node.position)
		w.place_at(t)
		_check(w.members.map(func(m): return m.node.position) == was, "%s: back from a fight, the line hasn't moved" % spot[1])
		_line_at_hub(map, t, spot[1] + ", back from a fight")
	# From another tile (a line that has gone stale, or a debug start): a new line on the streets, ready to walk on.
	for spot in spots:
		var t: Vector2i = spot[0]
		game.party_tile = t
		w.place_at(Rules.START_TILE)
		w.place_at(t)
		_line_at_hub(map, t, spot[1] + ", set down")
		w.members[0].node.position += Vector3(1.0, 0.0, 0.0)   # streets that have changed under the line
		w.place_at(t)
		_line_at_hub(map, t, spot[1] + ", streets changed")
	var from: Vector2i = spots[0][0]
	game.party_tile = from
	w.place_at(from)
	for t: Vector2i in Hex.NEIGHBOURS.map(func(n): return from + n):
		if map.edge_open(from, t) and map.path_graph(t).stand != null:
			await _watched(t, "on from a line set down")
			break


func _line_at_hub(map: MapBoard, t: Vector2i, what: String) -> void:
	var ms := game.party_node.members
	var graph := map.path_graph(t)
	var hero := Vector2(ms[0].node.position.x, -ms[0].node.position.z)
	_check(hero.distance_to(graph.nodes[graph.stand]) < 0.3, "%s: the hero is at the hub" % what)
	_stopped(map, t, what)


func _walk_tier0(map: MapBoard) -> void:
	var f := Game.DEBUG_FARMS
	var seen := 0
	for k in 7:
		var t: Vector2i = f + (Vector2i.ZERO if k == 6 else Hex.NEIGHBOURS[k])
		if map.terrains.get(t) == "village":
			seen += 1
			await _watched(t, "tier 0 village %s" % t)
	_check(seen > 0, "walked %d tier 0 village tiles" % seen)
	await _watched(f, "from a village to its farm")


func _perf_views(map: MapBoard) -> void:
	for v in KITS:
		var lm: Vector2i = _region(v).landmark_tile
		game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y)), 58.0, 50.0)
		await _perf("the opening zoom over the %s" % v)
	game.rig.frame(Hex.to3(Vector2.ZERO), game.rig.max_distance, 50.0)
	await _perf("the whole spawn, zoomed all the way out")


func _perf(what: String) -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	for _f in 60:
		await get_tree().process_frame
	var rs := RenderingServer
	var info := [rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)]
	var t0 := Time.get_ticks_usec()
	for _f in 120:
		await get_tree().process_frame
	print("TOWN PERF %s: draw calls %d, triangles %d; %.1f ms a frame on this Mac (vsync off)" % [what, info[0], info[1], (Time.get_ticks_usec() - t0) / 120000.0])
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)
