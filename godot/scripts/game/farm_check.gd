class_name FarmCheck
extends Node
## Checks the farmland kit (tiles v34) in the game (`-- --farmcheck`, add `--shots` to save screens/farm_*.png):
## spawns the debug regions (Game.spawn_forest_regions), checks gates, centre turn and centre_b, small mills and
## sails, then walks the party across and out of farm groups, watching every mini: no fence crossed except through
## a gate, and the route on the drawn paths. Prints FARM OK / FARM FAIL lines, then FARM DONE. A test aid only.

const LANE := 0.45           # half a lane's width: how far a route may stray from a drawn path
const GATE := 0.7            # how far from a gate's middle a mini may pass (the file of walking minis has some width)

var game: Game
var shots := false
var failed := 0
var _crossings := 0
var _bad_crossings := 0
var _widest := 0.0


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("FARM %s: %s" % ["OK" if ok else "FAIL", what])
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
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("farm_%s.png" % name))
		print("SAVED farm_%s" % name)


func _region(variant: String) -> Dictionary:
	for g in game.regions:
		if g.variant == variant:
			return g
	return {}


func _piece_nodes(t: Vector2i) -> Array:
	return game.map.tile_node(t).get_children().filter(func(c): return c is MeshInstance3D and c.has_meta("piece"))


func _steps(c: Node3D) -> int:
	return posmod(roundi(rad_to_deg(c.rotation.y) / 60.0), 6)


func _has(t: Vector2i, piece: String, steps: int) -> bool:
	return _piece_nodes(t).any(func(c): return c.get_meta("piece") == piece and _steps(c) == steps)


func _run() -> void:
	game.spawn_forest_regions()
	await _wait(1.0)
	var map := game.map
	_check_gates(map)
	_check_centres(map)
	await _check_sails(map)
	_check_effects(map)
	_check_reach(map)
	await _pictures(map)
	await _walks(map)
	print("FARM DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## Every gate edge has its gate piece and walkable land beyond; no other fence edge has one; every group has a way
## out where it can.
func _check_gates(map: MapBoard) -> void:
	var ok := true
	var total := 0
	for t: Vector2i in map.gates:
		var kit := Variants.wedges_of(map.terrains[t])
		for i in 6:
			var near = map.terrains.get(t + Hex.NEIGHBOURS[i])
			var fence: bool = not MapBoard.linked(map.terrains[t], near)
			var gate: bool = i in map.gates[t]
			if gate:
				total += 1
			if gate and (not fence or near == null or Variants.is_water(near) or not _has(t, kit + "_edge_gate", i)):
				ok = false
				print("  bad gate on %s edge %d" % [t, i])
			if not gate and fence and _has(t, kit + "_edge_gate", i):   # a wall's gatehouse on a joined edge isn't a fence gate
				ok = false
				print("  stray gate piece on %s edge %d" % [t, i])
	_check(ok and total > 0, "%d gates: each has its gate piece and walkable land beyond, and no stray gates" % total)
	var tier0: Vector2i = Game.DEBUG_FARMS
	var town: Vector2i = Game.DEBUG_TOWN
	var village_gates := 0
	var town_gates := 0
	for t: Vector2i in map.gates:
		if map.terrains[t] == "village":
			village_gates += map.gates[t].size()
		if map.terrains[t] == "market_town":
			town_gates += map.gates[t].size()
	_check(village_gates > 0 and town_gates > 0, "gates on villages (%d) and the market town (%d) too" % [village_gates, town_gates])


## Farm centres: centre_b and the turn by hash, near centres and small mills as the hand-off orders them; only the
## centre turns; the small mill stands in the turned yard but isn't turned itself.
func _check_centres(map: MapBoard) -> void:
	var ok := true
	var looks := {}
	var mills := 0
	var mills_ok := true
	for t: Vector2i in map.terrains:
		var name: String = map.terrains[t]
		if not map._kit.has(name + "_centre_b") or Variants.terrain_of(name) != "farmland":
			continue
		var turn := int(GroundCover.hash01(t.x * 31 + 7, t.y * 17 + 3, 14) * 6)
		var centre := "_centre"
		if map.flow_dist.get(t) == 1 and map._kit.has(name + "_centre_near"):
			centre = "_centre_near"
		elif GroundCover.hash01(t.x, t.y, 13) < 0.5:
			centre = "_centre_b"
		if map._kit.has(name + "_centre_mill") and GroundCover.hash01(t.x, t.y, 7) < 0.5:
			centre = "_centre_mill"
		if not _has(t, name + centre, turn):
			ok = false
			print("  %s: wants %s%s turned %d" % [t, name, centre, turn])
		looks["%s%s%d" % [name, centre, turn]] = true
		for c in _piece_nodes(t):
			if c.get_meta("piece") == "windmill_small":
				mills += 1
				var want := Hex.to3(Hex.tile_position(t.x, t.y) + Variants.SMALL_MILL_SPOT.rotated(deg_to_rad(60.0 * turn)))
				mills_ok = mills_ok and c.position.is_equal_approx(want) and is_zero_approx(c.rotation.y)
				mills_ok = mills_ok and centre == "_centre_mill"
	_check(ok, "centre, centre_b, near and mill centres at their hashed turn (%d different looks in the test regions)" % looks.size())
	_check(mills > 0 and mills_ok, "%d small mills in their turned yards, none turned themselves" % mills)
	# Landmarks turn by the flow, not the hash.
	var lm_ok := true
	for v: String in Game.DEBUG_FARM:
		var lm: Vector2i = _region(v).landmark_tile
		lm_ok = lm_ok and _has(lm, map.terrains[lm] + "_centre", map.landmark_turns.get(lm, 0))
		if map.terrains[lm] != Variants.LANDMARK_OF[v]:
			lm_ok = false
	_check(lm_ok, "each farm landmark's centre turned to its longest trail, on its variant's wedges")


func _check_sails(map: MapBoard) -> void:
	var lm: Vector2i = _region("windmill_country").landmark_tile
	var sails := map.tile_node(lm).find_child("sails", true, false) as Node3D
	if sails == null:
		_check(false, "the Great Windmill has its sails")
		return
	var b0 := sails.basis
	var spot := sails.position
	await _wait(0.5)
	var hub := Hex.tile_position(lm.x, lm.y) + Vector2(Variants.MILL_HUB.x, Variants.MILL_HUB.y).rotated(deg_to_rad(60.0 * map.landmark_turns.get(lm, 0)))
	var turning := not sails.basis.is_equal_approx(b0)
	var axis_still := sails.basis.x.is_equal_approx(b0.x)     # about its own X
	_check(turning and axis_still and sails.position == spot and spot.is_equal_approx(Hex.to3(hub, Variants.MILL_HUB.z)),
			"the Great Windmill's sails turn about their own X axis at the hub")


func _check_effects(map: MapBoard) -> void:
	var fires := 0
	var crows := 0
	for t: Vector2i in map.terrains:
		var fx := map.tile_node(t).find_child("farm_fx", false, false)
		if fx:
			fires += fx.get_children().filter(func(c): return c is GPUParticles3D).size()
			crows += fx.get_children().filter(func(c): return c is Spinner).size()
	_check(fires > 0 and crows > 0, "effect points: %d fire and smoke nodes, %d flocks of crows" % [fires, crows])
	_check(map._faint.emission_enabled, "window_faint has a night glow")


## Every placed land tile can be reached, and every step of every route goes through an open edge.
func _check_reach(map: MapBoard) -> void:
	var ok := true
	var count := 0
	for t: Vector2i in map.terrains:
		if t == game.party_tile:
			continue
		var path := game.path_to(t)
		if path.is_empty():
			ok = false
			print("  no way to %s" % t)
			continue
		count += 1
		var prev := game.party_tile
		for s in path:
			ok = ok and map.edge_open(prev, s)
			prev = s
	_check(ok, "%d tiles reachable from the start, every step through an open edge" % count)


func _pictures(map: MapBoard) -> void:
	var focus := game.rig.focus
	game.ui.visible = false
	game.rig.focus = Vector2(422, 195)
	var n := 1
	var names := Game.DEBUG_FARM.duplicate()
	names["village_farm_group"] = Game.DEBUG_FARMS
	names["market_town"] = Game.DEBUG_TOWN
	for v: String in names:
		var c: Vector2i = names[v]
		game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y)), 42.0, 50.0)
		await _wait(0.6)
		await _shot("%02d_region_%s" % [n, v])
		n += 1
	for v: String in Game.DEBUG_FARM:
		var lm: Vector2i = _region(v).landmark_tile
		var e := map.entrance_angle(lm)
		game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y), 0.8), 17.0, 34.0, -90.0 - rad_to_deg(e))
		await _wait(0.6)
		await _shot("%02d_landmark_%s" % [n, map.terrains[lm]])
		n += 1
	# A gate close up, on the tier 0 farm and village group.
	for t: Vector2i in map.gates:
		if not map.gates[t].is_empty() and Rules.hex_distance(t, Game.DEBUG_FARMS) <= 1:
			var i: int = map.gates[t][0]
			var at := Hex.tile_position(t.x, t.y) + Vector2.from_angle(deg_to_rad(60.0 * i)) * Hex.A
			game.rig.frame(Hex.to3(at), 15.0, 40.0, -90.0 - 60.0 * i)
			await _wait(0.6)
			await _shot("%02d_gate" % n)
			n += 1
			break
	game.minute = Rules.NIGHT_AT + 4.0
	await _wait(2.5)
	var barn: Vector2i = _region("haunted_homesteads").landmark_tile
	game.rig.frame(Hex.to3(Hex.tile_position(barn.x, barn.y), 0.8), 20.0, 36.0, -90.0 - rad_to_deg(map.entrance_angle(barn)))
	await _wait(0.6)
	await _shot("%02d_night_abandonedbarn" % n)
	n += 1
	game.minute = 10.0
	await _wait(2.5)
	game.rig.focus = focus
	game.ui.visible = true


func _walks(map: MapBoard) -> void:
	# 1. Across and out of each farm group: from plains on one side to plains on the far side.
	for v: String in Game.DEBUG_FARM:
		await _across(map, Game.DEBUG_FARM[v], v)
	await _across(map, Game.DEBUG_FARMS, "tier 0 farm and village group")
	await _across(map, Game.DEBUG_TOWN, "market town")
	# 2. Round to the gate: standing outside a closed fence, walk to the tile just over it.
	await _round_to_gate(map)
	# 3. Along the trails into each farm landmark, to its entrance.
	for v: String in Game.DEBUG_FARM:
		await _to_landmark(map, v)
	_check(_bad_crossings == 0, "%d crossings of fence edges by minis, all through gates (widest %.2f m from the gate's middle)" % [_crossings, _widest])


## The plains tiles on opposite sides of a 7-tile flower centred on c.
func _across(map: MapBoard, c: Vector2i, what: String) -> void:
	var from := c + Hex.NEIGHBOURS[3] * 2
	var to := c + Hex.NEIGHBOURS[0] * 2
	await _walk_to(from)
	game.pick(to)
	if what == "tier 0 farm and village group":
		game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y)), 42.0, 50.0)
		await _wait(0.4)
		await _shot("20_route_preview")
	game.pick(null)
	var tiles := game.path_to(to)
	var inside := tiles.filter(func(t): return map.gates.has(t)).size()
	await _walk_watching(tiles, "%s: across (%d steps, %d on fenced tiles)" % [what, tiles.size(), inside])
	game.party_tile = to


func _round_to_gate(map: MapBoard) -> void:
	for t: Vector2i in map.gates:
		if Rules.hex_distance(t, Game.DEBUG_FARMS) > 1:
			continue
		for i in 6:
			var o: Vector2i = t + Hex.NEIGHBOURS[i]
			if map.terrains.get(o) == "plains" and not map.edge_open(t, o):
				await _walk_to(o)
				var tiles := game.path_to(t)
				_check(tiles.size() > 1, "from outside a closed fence the way in goes round by a gate (%d steps, not 1)" % tiles.size())
				await _walk_watching(tiles, "round to the gate")
				game.party_tile = t
				return
	_check(false, "found a closed fence to test the way round")


func _to_landmark(map: MapBoard, v: String) -> void:
	var g := _region(v)
	var lm: Vector2i = g.landmark_tile
	var far := lm
	for t: Vector2i in g.tiles:
		if map.flow_dist.get(t, 0) > map.flow_dist.get(far, 0):
			far = t
	await _walk_to(far)
	var steps: Array[Vector2i] = []
	var t := far
	while t != lm:
		t = map.flow_toward[t]
		steps.append(t)
	if steps.is_empty():
		_check(true, "%s: the region's landmark is its only farthest tile, no trail to walk" % v)
		return
	await _walk_watching(steps, "%s: along the trail" % v)
	game.party_tile = lm
	var spot := game.party_node.centre()
	var graph := map.path_graph(lm)
	var entrance: Vector2 = graph.nodes[graph.stand]
	_check(Vector2(spot.x, -spot.z).distance_to(entrance) < 0.5, "%s: the party stops at the landmark's entrance" % v)
	if v == "windmill_country":
		game.rig.frame(Hex.to3(entrance), 16.0, 40.0, -90.0 - rad_to_deg(map.entrance_angle(lm)))
		await _wait(0.5)
		await _shot("21_party_at_greatwindmill")
	var watch := LeaveWatch.new(game.party_node)
	game.walk_to(far)
	var off_lane := 0.0
	while game.busy:
		await get_tree().process_frame
		watch.frame()
		for m in game.party_node.members:
			var at := Vector2(m.node.position.x, -m.node.position.z)
			var tile := GroundCover.tile_at(at)
			if tile == lm:
				off_lane = maxf(off_lane, map.path_graph(lm).distance_to_paths(at))
	_check(watch.passed(), "%s: leaving, %s" % [v, watch.report()])
	_check(off_lane <= LANE, "%s: leaving, everyone stays on the landmark's paths (at most %.2f m off)" % [v, off_lane])


## An ordinary walk through the game, while nothing is being checked.
func _walk_to(goal: Vector2i) -> void:
	if goal == game.party_tile:
		return
	game.walk_to(goal)
	while game.busy:
		await get_tree().process_frame


## Walks these tiles, checking the route against the drawn paths and every mini's every crossing of a fence edge.
func _walk_watching(tiles: Array[Vector2i], what: String) -> void:
	var map := game.map
	var walker := game.party_node
	game.busy = true
	walker.walk(tiles)
	await get_tree().process_frame
	var route: PackedVector2Array = walker._path
	var worst := 0.0
	var at := Vector2.ZERO
	for p in route:
		var t := GroundCover.tile_at(p)
		var kit := Variants.wedges_of(map.terrains.get(t, ""))
		if map.gates.has(t):
			var d := map.path_graph(t).distance_to_paths(p)
			if d > worst:
				worst = d
				at = p
	_check(worst <= LANE, "%s: the route keeps to the drawn paths (at most %.2f m off%s)" % [what, worst,
			"" if worst <= LANE else " at %s" % at])
	var off_path := 0.0
	var last := {}
	var start_tile := walker.members.map(func(m): return GroundCover.tile_at(Vector2(m.node.position.x, -m.node.position.z)))
	for k in walker.members.size():
		last[k] = start_tile[k]
	while walker.walking:
		await get_tree().process_frame
		for k in walker.members.size():
			var pos: Vector3 = walker.members[k].node.position
			var p := Vector2(pos.x, -pos.z)
			var t := GroundCover.tile_at(p)
			if t != last[k]:
				_crossing(map, last[k], t, p)
				last[k] = t
			if map.gates.has(t):
				off_path = maxf(off_path, map.path_graph(t).distance_to_paths(p))
	_check(off_path <= LANE, "%s: every mini stays on the lanes on farm tiles (at most %.2f m off)" % [what, off_path])
	await _wait(Rules.SETTLE_SECONDS + 0.2)
	_check_stop(map, tiles[-1], what)
	game.busy = false


## Stopped on a narrow path: every base on the path, in a file, none on top of another.
func _check_stop(map: MapBoard, t: Vector2i, what: String) -> void:
	var graph := map.path_graph(t)
	if graph.stand == null or graph.edge_node.is_empty():
		return
	var ms := game.party_node.members
	var worst := 0.0
	var closest := INF
	for k in ms.size():
		var a := Vector2(ms[k].node.position.x, -ms[k].node.position.z)
		var tile := GroundCover.tile_at(a)
		if map.terrains.has(tile):
			worst = maxf(worst, map.path_graph(tile).distance_to_paths(a) if not map.path_graph(tile).nodes.is_empty() else 0.0)
		for j in k:
			var b := Vector2(ms[j].node.position.x, -ms[j].node.position.z)
			closest = minf(closest, a.distance_to(b))
	_check(worst <= 0.1 and closest >= Rules.FILE_GAP - 0.1, "%s: stopped in a file on the path (centres at most %.2f m off, %.2f m apart; bases %.2f m wide, lanes 0.9)" % [
			what, worst, closest, ms[0].radius * 2.0])


func _crossing(map: MapBoard, a: Vector2i, b: Vector2i, p: Vector2) -> void:
	if map.gates.has(a) == map.gates.has(b):
		return   # not a fence edge
	_crossings += 1
	var mid := (Hex.tile_position(a.x, a.y) + Hex.tile_position(b.x, b.y)) * 0.5
	_widest = maxf(_widest, p.distance_to(mid))
	if Hex.NEIGHBOURS.find(b - a) < 0 or not map.edge_open(a, b) or p.distance_to(mid) > GATE:
		_bad_crossings += 1
		print("  a mini crossed the fence between %s and %s at %s, %.2f m from the middle" % [a, b, p, p.distance_to(mid)])
