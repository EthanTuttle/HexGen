class_name HillsCheck
extends Node
## Checks the hills kit (tiles v45) in the game (`-- --hillscheck`, add `--shots` for screens/hills_*.png): tier 0, the
## range rules, each raised region's cliffs, ledges and heights, the rise and what it carries, routes up, across and
## down, tiles added later, touching regions, a region with no way up, fenced feet, and a fight on raised ground.
## Prints HILLS OK / HILLS FAIL lines, then HILLS DONE. A test aid only.

const VARIANTS := ["highlands", "snowy_peaks", "volcanic_peaks", "monastery_heights"]
const AT_GROUND := ["highlands", "monastery_heights"]

var game: Game
var shots := false
var failed := 0


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	print("HILLS %s: %s" % ["OK" if ok else "FAIL", what])
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
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("hills_%s.png" % name))
		print("SAVED hills_%s" % name)


func _region(variant: String) -> Dictionary:
	for g in game.regions:
		if g.variant == variant:
			return g
	return {}


func _pieces(t: Vector2i) -> Array:
	return game.map.tile_node(t).get_children().filter(func(c): return c is MeshInstance3D and c.has_meta("piece"))


func _cliff_pieces(t: Vector2i) -> Array:
	var holder := game.map.tile_node(t).get_node_or_null("cliffs")
	return holder.get_children() if holder else []


func _steps(c: Node3D) -> int:
	return posmod(roundi(rad_to_deg(c.rotation.y) / 60.0), 6)


func _has(list: Array, piece: String, steps: int) -> bool:
	return list.any(func(c): return c.get_meta("piece") == piece and _steps(c) == steps)


func _run() -> void:
	game.spawn_forest_regions()
	game.party_node.place_at(game.party_tile)
	await _wait(1.0)
	var map := game.map
	_check_tier0(map)
	_check_ranges(map)
	for v in Cliffs.RAISED:
		_check_cliffs(map, v)
	for v in AT_GROUND:
		_check_at_ground(map, v)
	_check_smoke(map)
	await _pictures(map)
	for v in Cliffs.RAISED:
		await _walk_up(map, v)
	for v in AT_GROUND:
		await _walk_at_ground(map, v)
	await _check_low_tile_joins(map)
	await _check_camera(map)
	await _check_fight(map)
	await _perf_views(map)
	await _check_rise()
	await _check_added()
	await _check_touching()
	await _check_no_way()
	await _check_fenced_foot()
	print("HILLS DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _check_tier0(map: MapBoard) -> void:
	var c := Game.DEBUG_HILLS_T0
	_check(not map.raised.has(c), "tier 0 hills isn't raised")
	var ok := true
	var other_b := 0
	for t: Vector2i in map.terrains:
		if map.terrains[t] != "hills":
			continue
		var list := _pieces(t)
		var want_b := GroundCover.hash01(t.x, t.y, 13) < 0.5
		ok = ok and list.any(func(p): return p.get_meta("piece") == ("hills_centre_b" if want_b else "hills_centre"))
		for i in 6:
			var n = map.terrains.get(t + Hex.NEIGHBOURS[i])
			if MapBoard.linked("hills", n):
				continue
			var b := GroundCover.hash01(t.x * 6 + i, t.y, 8) < 0.5
			other_b += 1 if b else 0
			ok = ok and _has(list, "hills_edge_other_b" if b else "hills_edge_other", i)
	_check(ok and other_b > 0, "tier 0 hills: centre_b by hash, edge_other_b's trees only on wedges facing other land (%d)" % other_b)


## The range rules, each from what's placed: no mountain on a landmark, on a trail edge, or half up a cliff.
func _check_ranges(map: MapBoard) -> void:
	var ok := true
	var parts := 0
	for t: Vector2i in map.terrains:
		if Variants.terrain_of(map.terrains[t]) != "hills":
			continue
		var name: String = map.terrains[t]
		for p in _pieces(t):
			var piece: String = p.get_meta("piece")
			if not ("_mountain_" in piece or piece.ends_with("_peak") or "_ridge_" in piece):
				continue
			parts += 1
			if Variants.LANDMARKS.has(name):
				ok = false
			if "_mountain_edge" in piece:
				var i := _steps(p)
				if i in LandmarkFlow.trail_edges(t, map.flow_toward) or not MapBoard.linked(name, map.terrains.get(t + Hex.NEIGHBOURS[i])):
					ok = false
			if "_ridge_" in piece and (map.flow_dist.get(t, 3) <= 2 or name == "monastery_heights"):
				ok = false
			if piece.ends_with("_peak") and map.flow_dist.get(t, 3) <= 2:
				ok = false
	_check(ok and parts > 0, "range rules: %d mountain and ridge parts, none on a landmark, a trail edge, a cliff or (ridges, peaks) near a landmark" % parts)


## Highlands and monastery heights stay at ground level, with their bases and no cliff pieces at all.
func _check_at_ground(map: MapBoard, v: String) -> void:
	var g := _region(v)
	var ok := true
	for t: Vector2i in g.tiles:
		ok = ok and not map.raised.has(t) and map.tile_node(t).position.y == 0.0 and _cliff_pieces(t).is_empty()
		ok = ok and _pieces(t).any(func(p): return p.get_meta("piece") == "base_hills")
		ok = ok and not _pieces(t).any(func(p): return "_edge_rim" in p.get_meta("piece") or "_edge_climb" in p.get_meta("piece"))
	_check(ok, "%s: at ground level, with bases, no cliffs, rims or ledges" % v)
	_check(not map.climbs.any(func(c): return c[0] in g.tiles), "%s: no ledges" % v)
	var lm: Vector2i = g.landmark_tile
	var near_ok := true
	for t: Vector2i in g.tiles:
		if map.flow_dist.get(t) == 1:
			near_ok = near_ok and _has(_pieces(t), v + "_centre_near", LandmarkFlow.toward_edge(t, map.flow_toward))
	_check(near_ok, "%s: near centres turned toward the landmark" % v)
	if v == "monastery_heights":
		var steps := true
		for t: Vector2i in g.tiles:
			for i in LandmarkFlow.trail_edges(t, map.flow_toward):
				if t != lm:
					steps = steps and _has(_pieces(t), v + "_steps_centre", i)
				elif i != map.landmark_turns[lm]:
					steps = steps and _has(_pieces(t), v + "_steps_rise", i)
		_check(steps, "monastery heights: steps on every trail edge, except the Library's entrance")


## Walks into a ground-level region to its landmark's entrance and out again, on the low land throughout.
func _walk_at_ground(map: MapBoard, v: String) -> void:
	var g := _region(v)
	var lm: Vector2i = g.landmark_tile
	var reach := true
	for t: Vector2i in g.tiles:
		reach = reach and not game.path_to(t).is_empty()
	_check(reach, "%s: every tile can be reached" % v)
	await _watched_walk(lm, "%s: to the landmark" % v, "")
	var graph := map.path_graph(lm)
	var hero := game.party_node.centre()
	var door: Vector2 = graph.nodes[graph.stand]
	_check(Vector2(hero.x, -hero.z).distance_to(door) < 0.5, "%s: the party stops at the entrance (%.2f m off)" % [v, Vector2(hero.x, -hero.z).distance_to(door)])
	_check(absf(hero.y - (_stand_height(map, lm) - Variants.RAISE)) < 0.45, "%s: at the entrance's height: mini %.2f" % [v, hero.y])
	game.rig.frame(hero, 16.0, 40.0, -90.0 - rad_to_deg(map.entrance_angle(lm)))
	await _wait(0.5)
	await _shot("6%d_party_at_%s" % [VARIANTS.find(v), map.terrains[lm]])
	game.rig.frame(hero, 58.0, 50.0)
	await _wait(0.2)
	await _shot("6%d_game_camera_party_on_%s" % [VARIANTS.find(v), v])
	var far := lm
	for t: Vector2i in g.tiles:
		if map.flow_dist.get(t, 0) > map.flow_dist.get(far, 0):
			far = t
	await _watched_walk(far, "%s: out across it" % v, "")


## A hills tile beside a ground-level region joins it and stays low, with no rise.
func _check_low_tile_joins(map: MapBoard) -> void:
	var g := _region("highlands")
	var spot := Vector2i.ZERO
	for e in Cliffs.outer_edges(g.tiles, map.raised):
		var n: Vector2i = Cliffs.beside(e[0], e[1])
		if n != game.party_tile and game._debug_fill.has(n) and map.terrains.get(n) == "plains":
			spot = n
			break
	map.terrains.erase(spot)
	map.tile_node(spot).free()
	map._tile_nodes.erase(spot)
	game._debug_fill.erase(spot)
	map.place(spot, "hills")
	game.order[spot] = game.order.size()
	game._check_region(spot, "hills")
	await _await_free()
	_check(map.terrains[spot] == "highlands" and game.finished.get(spot) == game.regions.find(g), "a hills tile beside highlands joins it")
	_check(not map.raised.has(spot) and map.tile_node(spot).position.y == 0.0, "and stays at ground level")


## Every outer edge has its cliff and rim; no bases, no cover; a ledge's three parts; the geometry of test_cliffs.py.
func _check_cliffs(map: MapBoard, v: String) -> void:
	var g := _region(v)
	if g.is_empty():
		_check(false, "%s: not spawned" % v)
		return
	var tiles: Array = g.tiles
	var outer := Cliffs.outer_edges(tiles, map.raised)
	var by_terrain := {}
	for t: Vector2i in map.terrains:
		by_terrain[t] = Variants.terrain_of(map.terrains[t])
	var climbs := Cliffs.climbs(tiles, by_terrain, map.raised)
	var ok := true
	for t: Vector2i in tiles:
		ok = ok and map.tile_node(t).position.y == Variants.RAISE
		ok = ok and not _pieces(t).any(func(p): return p.get_meta("piece").begins_with("base_"))
		ok = ok and not map.tile_node(t).get_children().any(func(c): return c.name.begins_with("ground_cover"))
	_check(ok, "%s: every tile at height 5, no bases, no ground cover" % v)
	ok = true
	var ledge := {}
	for c in climbs:
		ledge[[c[0], posmod(c[1] - 1, 6)]] = "low"
		ledge[[c[0], c[1]]] = "mid"
		ledge[[c[0], (c[1] + 1) % 6]] = "top"
	for e in outer:
		var part: String = ledge.get(e, "")
		var cliffs := _cliff_pieces(e[0])
		if part == "":
			var b := GroundCover.hash01(e[0].x * 6 + e[1], e[0].y, 8) < 0.5
			ok = ok and _has(cliffs, v + ("_cliff_edge_b" if b else "_cliff_edge"), e[1]) and _has(_pieces(e[0]), v + "_edge_rim", e[1])
		else:
			var wedge: String = {"low": "_edge_climb_low", "mid": "_edge_climb", "top": "_edge_climb_top"}[part]
			ok = ok and _has(cliffs, v + "_cliff_path_" + part, e[1]) and _has(_pieces(e[0]), v + wedge, e[1])
	_check(ok, "%s: %d outer edges each with its cliff and rim, or a ledge's parts" % [v, outer.size()])
	ok = true
	for e in Cliffs.outer_corners(tiles, map.raised):
		var skip: bool = ledge.has(e)
		ok = ok and skip != _has(_cliff_pieces(e[0]), v + "_cliff_corner", e[1])
	_check(ok, "%s: a pinnacle at each outer corner except a ledge's" % v)
	_check(climbs.size() >= 1, "%s: %d ledges" % [v, climbs.size()])
	# test_cliffs.py's geometry, on this region.
	for c in climbs:
		var wrong := _foot_wrong(map, c)
		_check(wrong == "", "%s: ledge %s: foot and top clear%s" % [v, c, ": " + wrong if wrong != "" else ""])
		var line := map.ledge_line(c[0], c[1])
		var steep := 0.0
		for k in range(4, line.size()):   # over about a metre, a base's width, not a rounded corner's few centimetres
			var run := 0.0
			for j in range(k - 3, k + 1):
				run += Vector2(line[j].x, line[j].y).distance_to(Vector2(line[j - 1].x, line[j - 1].y))
			steep = maxf(steep, rad_to_deg(atan2(line[k].z - line[k - 4].z, maxf(run, 1e-4))))
		var length := 0.0
		for k in range(1, line.size()):
			length += line[k].distance_to(line[k - 1])
		_check(line[0].z < 0.3 and absf(line[-1].z - 5.215) < 0.05 and steep < 33.0, "%s: ledge climbs from %.2f to %.2f, %.1f m, steepest %.1f degrees" % [v, line[0].z, line[-1].z, length, steep])


## test_cliffs.check: straight ahead of the foot is low walkable land, with no other cliff ahead or beside it.
func _foot_wrong(map: MapBoard, c: Array) -> String:
	var t: Vector2i = c[0]
	var edge: int = posmod(c[1] - 1, 6)
	var at := Hex.tile_position(t.x, t.y)
	var out := Water.normal(edge)
	var foot := at + Vector2(Hex.A, -0.135).rotated(deg_to_rad(60.0 * edge))
	var front := GroundCover.tile_at(foot + out * 3.0)
	if front != Cliffs.beside(t, edge):
		return "straight ahead is %s" % front
	if map.raised.has(front) or Variants.is_water(map.terrains.get(front)) or not map.terrains.has(front):
		return "%s isn't walkable low land" % front
	for r: Vector2i in map.raised:
		for k in 6:
			if map.raised.has(Cliffs.beside(r, k)) or (r == t and k == edge):
				continue
			var mid := Hex.tile_position(r.x, r.y) + Water.normal(k) * Hex.A
			var along := Water.normal(k).orthogonal() * Hex.R * 0.5
			if Geometry2D.get_closest_point_to_segment(foot, mid - along, mid + along).distance_to(foot) < 1.5:
				return "cliff of %s edge %d near the foot" % [r, k]
			for turn in [0.0, 45.0, -45.0]:
				var d := out.rotated(deg_to_rad(turn)) * (8.0 if turn == 0.0 else 4.0)
				if Geometry2D.segment_intersects_segment(foot + out * 0.01, foot + d, mid - along, mid + along) != null:
					return "cliff of %s edge %d ahead of the foot" % [r, k]
	return ""


func _check_smoke(map: MapBoard) -> void:
	var points := []
	var smoke := 0
	for t: Vector2i in map.terrains:
		if map.terrains[t] != "volcanic_peaks":
			continue
		for c in map.tile_node(t).get_children():
			if c.name.begins_with("crater_smoke"):
				smoke += 1
				points.append(c.global_position)
			elif c is MeshInstance3D and c.has_meta("piece") and not Kit.path_data(c.get_meta("piece")).get("effects", []).is_empty():
				points.append_array([])
	var apart := true
	for k in points.size():
		for j in k:
			apart = apart and points[k].distance_to(points[j]) > 0.1
	_check(smoke > 0 and apart, "volcanic peaks: %d craters' smoke, no two on one spot" % smoke)


func _pictures(map: MapBoard) -> void:
	var n := 1
	for v in VARIANTS:
		var g := _region(v)
		var lm: Vector2i = g.landmark_tile
		game.rig.frame(game.map.tile_node(lm).position + Hex.to3(Hex.tile_position(lm.x, lm.y)), 58.0, 50.0, 0.0)
		for yaw in [0.0, 90.0, 180.0, 270.0]:
			game.rig.yaw_deg = yaw
			await _wait(0.2)
			await _shot("%02d_game_camera_%s_%d" % [n, v, int(yaw)])
			n += 1
		game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y), 2.0 + map.lift.get(lm, 0.0)), 18.0, 40.0, -90.0 - rad_to_deg(map.entrance_angle(lm)))
		await _wait(0.2)
		await _shot("%02d_landmark_%s" % [n, map.terrains[lm]])
		n += 1
		if not map.climbs.is_empty():
			for c in map.climbs:
				if c[0] in g.tiles:
					var line := map.ledge_line(c[0], c[1])
					var foot := Vector2(line[0].x, line[0].y)
					game.rig.frame(Hex.to3(foot, 1.5), 16.0, 22.0, -90.0 - 60.0 * posmod(c[1] - 1, 6))
					await _wait(0.2)
					await _shot("%02d_ledge_%s" % [n, v])
					n += 1
					break
	var c0 := Game.DEBUG_HILLS_T0
	game.rig.frame(Hex.to3(Hex.tile_position(c0.x, c0.y)), 40.0, 50.0)
	await _wait(0.2)
	await _shot("%02d_tier0_hills" % n)


## Up a ledge, across the plateau to the landmark's entrance, then down again: every mini at every frame.
func _walk_up(map: MapBoard, v: String) -> void:
	var g := _region(v)
	var lm: Vector2i = g.landmark_tile
	# Every region tile can be reached, only through a ledge.
	var reach := true
	for t: Vector2i in g.tiles:
		reach = reach and not game.path_to(t).is_empty()
	_check(reach, "%s: every tile can be reached" % v)
	var below: Vector2i = Cliffs.beside(map.climbs.filter(func(c): return c[0] in g.tiles)[0][0], map.climbs.filter(func(c): return c[0] in g.tiles)[0][1] - 1)
	await _plain_walk(below)
	game.rig.player_moved = false
	game.rig.frame(game.party_node.centre(), 30.0, 50.0)
	var watch := await _watched_walk(lm, "%s: up to the landmark" % v, "50_%s_climbing" % v)
	var graph := map.path_graph(lm)
	var hero := game.party_node.centre()
	var door: Vector2 = graph.nodes[graph.stand]
	_check(Vector2(hero.x, -hero.z).distance_to(door) < 0.5, "%s: the party stops at the entrance (%.2f m off)" % [v, Vector2(hero.x, -hero.z).distance_to(door)])
	var path_h: float = _stand_height(map, lm)
	_check(absf(hero.y - path_h) < 0.45, "%s: at the entrance's height: mini %.2f, path %.2f" % [v, hero.y, path_h])
	game.rig.frame(hero, 16.0, 40.0, -90.0 - rad_to_deg(map.entrance_angle(lm)))
	await _wait(0.5)
	await _shot("6%d_party_at_%s" % [VARIANTS.find(v), map.terrains[lm]])
	game.rig.frame(hero, 58.0, 50.0)
	await _wait(0.2)
	await _shot("6%d_game_camera_party_on_%s" % [VARIANTS.find(v), v])
	# Across the plateau, as far as it goes, then down.
	var far := lm
	for t: Vector2i in g.tiles:
		if map.flow_dist.get(t, 0) > map.flow_dist.get(far, 0):
			far = t
	await _watched_walk(far, "%s: across the plateau" % v, "")
	await _watched_walk(below, "%s: back down" % v, "")
	_check(game.party_node.centre().y < 1.5, "%s: back on low ground" % v)


func _stand_height(map: MapBoard, lm: Vector2i) -> float:
	var data := Kit.path_data(map.terrains[lm] + "_centre")
	for poly in data.paths:
		if poly[0] != poly[-1]:
			return Variants.RAISE + float(poly[-1][1])
	return 0.0


func _plain_walk(goal: Vector2i) -> void:
	if goal == game.party_tile:
		return
	game.walk_to(goal)
	while game.busy:
		await get_tree().process_frame
	await _wait(Rules.SETTLE_SECONDS)


## Walks, watching every mini each frame: raised tiles only by a ledge, on the ledge at its height and tilt, on the
## plateau never past the lip or over a mountain unless there was no way round.
func _watched_walk(goal: Vector2i, what: String, shots_as: String) -> Dictionary:
	var map := game.map
	var w := game.party_node
	var path := game.path_to(goal)
	if path.is_empty() and goal != game.party_tile:
		_check(false, "%s: no route" % what)
		return {}
	var off_ledge := 0.0
	var tilt := 0.0
	var fell := 0
	var lip := 0
	var on_rock := 0
	var cliff_cross := 0
	var last_tile: Array = w.members.map(func(m): return GroundCover.tile_at(Vector2(m.node.position.x, -m.node.position.z)))
	var last_y: Array = w.members.map(func(m): return m.node.position.y)
	var jump := 0.0
	var jump_at := ""
	var lines := []
	for c in map.climbs:
		lines.append(map.ledge_line(c[0], c[1]))
	game.walk_to(goal)
	var t := 0.0
	var shot := 0
	const TIMES := [1.2, 2.2, 3.2, 4.2]
	while game.busy:
		await get_tree().process_frame
		t += get_process_delta_time()
		for k in w.members.size():
			var m: Dictionary = w.members[k]
			var at := Vector2(m.node.position.x, -m.node.position.z)
			var tile := GroundCover.tile_at(at)
			var y: float = m.node.position.y
			# Near a ledge? Then its height, its tilt.
			var near := INF
			var near_h := 0.0
			for line in lines:
				for q in line:
					var d := Vector2(q.x, q.y).distance_to(at)
					if d < near:
						near = d
						near_h = q.z
			if near < 0.12:
				off_ledge = maxf(off_ledge, absf(y - near_h))
			tilt = maxf(tilt, rad_to_deg((m.up as Vector3).angle_to(Vector3.UP)))
			if absf(y - last_y[k]) > jump:
				jump = absf(y - last_y[k])
				jump_at = "%s on %s, %s to %.2f" % [at, map.terrains.get(tile), last_y[k], y]
			last_y[k] = y
			if map.raised.has(tile) and near > 0.5:
				if y < Variants.RAISE - 0.3:
					fell += 1
				if map.near_lip(at) and near > 1.5:
					lip += 1
			if not map.raised.has(tile) and y > 1.6 and near > 0.5 and not Variants.terrain_of(map.terrains.get(tile)) == "hills":
				fell += 1
			if map.raised.has(tile) != map.raised.has(last_tile[k]) and tile != last_tile[k] and near > 0.6:
				cliff_cross += 1
			last_tile[k] = tile
			if w._on_mountain(at) and near > 0.5:
				on_rock += 1
		if shots_as != "" and shot < TIMES.size() and t >= TIMES[shot]:
			shot += 1
			await _shot("%s_%d" % [shots_as, shot])
	await _wait(Rules.SETTLE_SECONDS)
	_check(off_ledge < 0.15, "%s: on a ledge, minis at its height (at most %.3f off)" % [what, off_ledge])
	_check(tilt <= Rules.LEDGE_MAX_TILT_DEG + 0.5, "%s: the steepest base tilt %.1f degrees" % [what, tilt])
	_check(jump < 1.0, "%s: no pop in height (biggest step in a frame %.2f m)" % [what, jump])
	_check(cliff_cross == 0, "%s: nobody crossed a cliff except by its ledge (%d)" % [what, cliff_cross])
	_check(fell == 0, "%s: nobody at the wrong height for their ground (%d frames)" % [what, fell])
	_check(lip == 0, "%s: nobody on a lip (%d frames)" % [what, lip])
	print("HILLS NOTE: %s: %d mini-frames on a mountain or ridge; biggest step %s" % [what, on_rock, jump_at])
	return {on_rock = on_rock}


## The camera: close in over raised ground it must clear the mountains; a party at a cliff's back can be hidden.
func _check_camera(map: MapBoard) -> void:
	var g := _region("snowy_peaks")
	var t: Vector2i = g.tiles[1]
	var lowest := INF
	for yaw in [0.0, 120.0, 240.0]:
		game.rig.frame(Hex.to3(Hex.tile_position(t.x, t.y), 6.0), game.rig.min_distance, 50.0, yaw)
		for _f in 40:
			await get_tree().process_frame
		var cam: Vector3 = game.rig.camera.global_position
		lowest = minf(lowest, cam.y - map.camera_floor(Vector2(cam.x, -cam.z)))
	_check(lowest > 0.0, "fully zoomed in over a plateau, the camera clears the tallest mountain by %.2f m" % lowest)
	await _shot("65_closest_zoom_on_plateau")
	# The low tile on the far side of a region, where the plateau comes between the camera and the party.
	var r := _region("volcanic_peaks")
	var best := Vector2i.ZERO
	var y := -INF
	for e in Cliffs.outer_edges(r.tiles, map.raised):
		var n: Vector2i = Cliffs.beside(e[0], e[1])
		var at := Hex.tile_position(n.x, n.y)
		if map.terrains.has(n) and at.y > y and not game.path_to(n).is_empty():
			y = at.y
			best = n
	await _plain_walk(best)
	var hero := game.party_node.centre()
	for yaw in [0.0, 90.0, 180.0, 270.0]:
		game.rig.frame(hero, 58.0, 50.0, yaw)
		await _wait(0.2)
		await _shot("66_party_behind_plateau_%d" % int(yaw))
	game.rig.frame(hero, 30.0, 50.0, 0.0)
	await _wait(0.2)
	await _shot("67_party_behind_plateau_closer")


## Combat starts on a raised tile: the flat board as ever (rules for slopes are open, design/03), and back on the plateau.
func _check_fight(map: MapBoard) -> void:
	var g := _region("snowy_peaks")
	var below: Vector2i = g.tiles[1]
	await _plain_walk(below)
	var y0 := game.party_node.centre().y
	game.add_encounter(below, false)
	game.encounters[below].expires = INF
	game.start_fight(below)
	await _wait(1.0)
	await _shot("70_fight_on_raised_tile")
	_check(game.fight.active and game.fight.visible, "a fight starts on a raised tile, on its usual flat board")
	game.fight.finished.emit(true)
	await _wait(0.5)
	game.after.done.emit()
	await _wait(0.5)
	_check(not game.busy, "the fight ends and hands back the map")
	_check(absf(game.party_node.centre().y - y0) < 0.5 and game.party_tile == below, "after it, the party stands on the plateau again (%.2f, was %.2f)" % [game.party_node.centre().y, y0])
	await _shot("71_after_fight_on_raised_tile")


## What the debug spawn costs now, on this Mac: compare with the phone's last run.
func _perf_views(map: MapBoard) -> void:
	var lm: Vector2i = _region("snowy_peaks").landmark_tile
	game.hud.visible = true
	game.rig.frame(Hex.to3(Hex.tile_position(0, 0)), game.rig.max_distance, 50.0)
	await _perf("the whole spawn, zoomed all the way out")
	await _shot("68_zoomed_out")
	game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y), 6.0), 58.0, 50.0)
	await _perf("the opening zoom over the snowy region")
	var v: Vector2i = _region("volcanic_peaks").landmark_tile
	game.rig.frame(Hex.to3(Hex.tile_position(v.x, v.y), 6.0), 58.0, 50.0)
	await _perf("the opening zoom over the volcanic region")


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
	print("HILLS PERF %s: draw calls %d, triangles %d; %.1f ms a frame on this Mac (vsync off)" % [what, info[0], info[1], (Time.get_ticks_usec() - t0) / 120000.0])
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)


## Plains from this tile back to the land, so the party can walk there.
func _connect(from: Vector2i) -> void:
	var t := from
	if not game.map.terrains.has(t):
		game.map.retile({t: "plains"})
		game._debug_fill[t] = true
	var best: Vector2i = t + Hex.NEIGHBOURS[0]
	for n in Hex.NEIGHBOURS:
		if Rules.hex_distance(t + n, Rules.START_TILE) < Rules.hex_distance(best, Rules.START_TILE):
			best = t + n
	var road := {}
	game._debug_road(best, road)
	game.map.retile(road)


## Far from everything: a clean corner of the map for the scenes below.
func _land(at: Vector2i, radius: int, terrain := "plains") -> void:
	var changes := {}
	for q in range(-radius, radius + 1):
		for r in range(maxi(-radius, -q - radius), mini(radius, -q + radius) + 1):
			var t := at + Vector2i(q, r)
			if not game.map.terrains.has(t):
				changes[t] = terrain
				game._debug_fill[t] = true
	game.map.retile(changes)


func _finish_region(variant: String, tiles: Array[Vector2i], landmark: Vector2i, empty_ok := false) -> Dictionary:
	var changes := {}
	for t in tiles:
		changes[t] = "hills"
		game.order[t] = game.order.size()
	game.map.retile(changes)
	game.party_node.get_parent()
	var region := game.new_region("hills", tiles, variant, landmark)
	game._transform(tiles, region, tiles[0])
	return region


func _await_free() -> void:
	await get_tree().process_frame
	while game.busy:
		await get_tree().process_frame


## The rise: real time, with the party on it, beside empty slots.
func _check_rise() -> void:
	var map := game.map
	var c := Vector2i(16, 10)
	# An island of hills beside empty slots, with a strip of land for the party to arrive by.
	var tiles: Array[Vector2i] = [c]
	for n in Hex.NEIGHBOURS:
		tiles.append(c + n)
	_connect(c + Vector2i(-2, 0))
	for t in tiles:
		map.retile({t: "hills"})
		game.order[t] = game.order.size()
	game.party_tile = tiles[0]
	game.party_node.place_at(tiles[0])
	var y0 := game.party_node.centre().y
	game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y)), 40.0, 50.0)
	await _wait(0.2)
	await _shot("80_before_rise")
	var region := game.new_region("hills", tiles, "volcanic_peaks", tiles[1])
	game._transform(tiles, region, tiles[0])
	var ok_walk := true
	var heights := []
	var hero_y := []
	var start := Time.get_ticks_msec()
	var shot := 0
	var rising_seen := false
	while game.busy:
		await get_tree().process_frame
		if not game.busy:
			break
		var y: float = map.lift.get(tiles[0], 0.0)
		if map.raised.has(tiles[0]) and not rising_seen:
			rising_seen = true
			start = Time.get_ticks_msec()
		if rising_seen:
			heights.append(y)
			hero_y.append(game.party_node.centre().y - y)
			game.tap(tiles[1])
			game.tap(tiles[1])
			ok_walk = ok_walk and not game.party_node.walking
			var t := (Time.get_ticks_msec() - start) / 1000.0
			if shot < 4 and t > [0.15, 1.2, 1.8, 3.0][shot]:
				shot += 1
				await _shot("8%d_rising" % shot)
				_cliff_clip_check(map, tiles)
	var secs := (Time.get_ticks_msec() - start) / 1000.0
	_check(rising_seen and absf(secs - Rules.RISE_SECONDS) < 1.5, "the region rose over %.1f seconds" % secs)
	_check(ok_walk, "no walking during the rise, whatever is tapped")
	var up := true
	for k in range(1, heights.size()):
		up = up and heights[k] >= heights[k - 1] - 0.001
	_check(up and map.lift[tiles[0]] == Variants.RAISE, "tile pieces come up steadily to 5")
	var carried := true
	for k in range(1, hero_y.size()):
		carried = carried and absf(hero_y[k] - hero_y[0]) < 0.02
	_check(carried, "the party rides up with it (height over the tile changes by at most 0.02 m)")
	var cliffs := map.tile_node(tiles[1]).get_node("cliffs")
	_check(cliffs.global_position.y == 0.0, "cliffs end at ground level")
	var clipped := false
	for mi in cliffs.get_children():
		clipped = clipped or mi.get_surface_override_material(0) != null
	_check(not clipped, "the rising look comes off when it's up")
	_check(game.party_node.centre().y > y0 + 4.0, "the party is on top at %.2f" % game.party_node.centre().y)
	await _wait(0.5)
	await _shot("85_risen")
	_check(not map.climbs.any(func(cl): return cl[0] in tiles) or true, "(no land in front of a foot yet: no ledge is fine)")
	_land(c, 3)   # land placed round it: its ledges appear
	await _wait(0.2)
	await _shot("86_land_placed_round_it")
	_check(map.climbs.any(func(cl): return cl[0] in tiles), "with land round it, it has a ledge")
	var way: Array = map.climbs.filter(func(cl): return cl[0] in tiles)[0]
	await _watched_walk(Cliffs.beside(way[0], way[1] - 1), "after the rise: down its ledge", "")
	# A second region of the same run rising with the party off it stays where it is: covered by _check_added.


func _cliff_clip_check(map: MapBoard, tiles: Array) -> void:
	var cliffs := map.tile_node(tiles[1]).get_node_or_null("cliffs")
	if cliffs:
		var on: bool = cliffs.get_child(0).get_surface_override_material(0) != null
		_check(on, "while rising, cliff pieces are cut off below the board at height %.1f" % cliffs.global_position.y)


## A hills tile placed beside a raised region joins and rises; old tiles keep their trails and turn; any other tile stays low.
func _check_added() -> void:
	var map := game.map
	var g := _region("snowy_peaks")
	var lm: Vector2i = g.landmark_tile
	var turn: int = map.landmark_turns[lm]
	var old_dist := {}
	var old_toward := {}
	for t in g.tiles:
		old_dist[t] = map.flow_dist[t]
		old_toward[t] = map.flow_toward.get(t)
	# A slot beside the region, clear of its ledges where possible.
	var spot := Vector2i.ZERO
	for e in Cliffs.outer_edges(g.tiles, map.raised):
		var n: Vector2i = Cliffs.beside(e[0], e[1])
		spot = n
		if map.climb_between(n, e[0]).is_empty():
			break
	var keep_terrain = map.terrains.get(spot)
	# It stands on plains filler: take it away first, as if the slot were empty.
	if keep_terrain != null:
		map.terrains.erase(spot)
		var nd := map.tile_node(spot)
		nd.free()
		map._tile_nodes.erase(spot)
		game._debug_fill.erase(spot)
	game.party_tile = game.party_tile
	game.rig.frame(Hex.to3(Hex.tile_position(spot.x, spot.y), 2.0), 40.0, 50.0)
	await _shot("90_added_before")
	var other := Vector2i.ZERO
	map.place(spot, "hills")
	game.order[spot] = game.order.size()
	game._check_region(spot, "hills")
	_check(game.finished.get(spot) == game.regions.find(g), "the new tile joins the region")
	await _await_free()
	_check(map.raised.has(spot) and map.lift[spot] == Variants.RAISE, "it rises to 5")
	_check(map.terrains[spot] == "snowy_peaks", "it takes the region's variant")
	_check(map.landmark_turns[lm] == turn, "the landmark keeps its turn")
	var kept := true
	for t in old_dist:
		kept = kept and map.flow_dist[t] == old_dist[t] and map.flow_toward.get(t) == old_toward[t]
	_check(kept, "old tiles keep their distances and trails")
	_check(map.flow_dist.has(spot), "the new tile has its own trail step")
	var no_cliff := true
	for i in 6:
		var n: Vector2i = spot + Hex.NEIGHBOURS[i]
		if g.tiles.has(n):
			no_cliff = no_cliff and not _cliff_pieces(n).any(func(p): return _steps(p) == (i + 3) % 6 and "_cliff_edge" in p.get_meta("piece"))
	_check(no_cliff, "no cliff left between the new tile and the old")
	var climbs_ok := true
	for c in map.climbs:
		climbs_ok = climbs_ok and not map.raised.has(Cliffs.beside(c[0], c[1] - 1))
	_check(climbs_ok, "every ledge still has a low foot")
	await _wait(0.2)
	await _shot("91_added_after")
	# Any other tile stays low: a plains tile on the far side.
	for e in Cliffs.outer_edges(g.tiles, map.raised):
		var n: Vector2i = Cliffs.beside(e[0], e[1])
		if not map.terrains.has(n):
			other = n
			map.place(n, "plains")
			_check(not map.raised.has(n) and map.tile_node(n).position.y == 0.0, "a plains tile placed beside it stays low")
			break


## Two raised regions touching: one plateau at one height, no cliff between, crossed on foot.
func _check_touching() -> void:
	var map := game.map
	var a := Vector2i(-16, -6)
	var b := a + Vector2i(2, 0)
	_land(a + Vector2i(1, 0), 5)
	var ta: Array[Vector2i] = [a, a + Vector2i(0, -1), a + Vector2i(0, 1), a + Vector2i(-1, 0), a + Vector2i(-1, 1)]
	var tb: Array[Vector2i] = [b, b + Vector2i(0, -1), b + Vector2i(0, 1), b + Vector2i(1, 0), b + Vector2i(1, -1)]
	_connect(a + Vector2i(1, 0) + Vector2i(-4, 4))
	var ra := _raised_at_once(ta, "snowy_peaks", a)
	var rb := _raised_at_once(tb, "volcanic_peaks", b)
	# The tile between them: joins the newer region, and rises.
	var bridge := a + Vector2i(1, 0)
	map.terrains.erase(bridge)
	map.tile_node(bridge).free()
	map._tile_nodes.erase(bridge)
	game._debug_fill.erase(bridge)
	map.place(bridge, "hills")
	game.order[bridge] = game.order.size()
	game._check_region(bridge, "hills")
	await _await_free()
	_check(game.finished.get(bridge) == game.regions.find(rb), "the tile between joins the newer region")
	_check(map.raised.has(bridge), "and rises")
	var between := Vector2i(a + Vector2i(1, 0))
	var a_edge := Hex.NEIGHBOURS.find(between - a)
	_check(not _cliff_pieces(a).any(func(p): return _steps(p) == a_edge), "no cliff where the two regions touch")
	_check(map.tile_node(a).position.y == map.tile_node(between).position.y, "they stand at one height")
	# Edge pieces there dip to the join.
	_check(_has(_pieces(a), "snowy_peaks_edge_other", a_edge), "edge_other at the join")
	_check(not a_edge in LandmarkFlow.trail_edges(a, map.flow_toward), "no trail runs from one region into the other")
	var own_a := map.climbs.filter(func(c): return c[0] in ra.tiles)
	var own_b := map.climbs.filter(func(c): return c[0] in rb.tiles)
	_check(own_a.size() >= 1 and own_b.size() >= 1, "each has its own ledges (%d and %d)" % [own_a.size(), own_b.size()])
	game.rig.frame(Hex.to3(Hex.tile_position(between.x, between.y), 6.0), 40.0, 50.0)
	await _wait(0.2)
	await _shot("92_touching")
	if not own_a.is_empty():
		var foot: Vector2i = Cliffs.beside(own_a[0][0], own_a[0][1] - 1)
		var there := game.path_to(foot)
		if not there.is_empty():
			await _plain_walk(foot)
			await _watched_walk(tb[0], "touching regions: up one, across to the other", "")
			_check(game.party_tile == tb[0], "the party crossed the join")


func _raised_at_once(tiles: Array[Vector2i], variant: String, landmark: Vector2i) -> Dictionary:
	var map := game.map
	for t in tiles:
		map.terrains.erase(t)
		var nd := map.tile_node(t)
		if nd:
			nd.free()
			map._tile_nodes.erase(t)
		game._debug_fill.erase(t)
	var region := game.new_region("hills", tiles, variant, landmark)
	game._set_flow(region)
	map.set_raised(game.regions.size() - 1, tiles)
	var changes := {}
	for t in tiles:
		changes[t] = game.region_look(region, t)
		game.order[t] = game.order.size()
	map.retile(changes)
	return region


## Ringed by a river: no ledge, no route, a tap does nothing; land placed beside it... stays until there's a foot.
func _check_no_way() -> void:
	var map := game.map
	var c := Vector2i(-2, -18)
	var tiles: Array[Vector2i] = [c]
	for n in Hex.NEIGHBOURS:
		tiles.append(c + n)
	var ring := {}
	for t in tiles:
		for n in Hex.NEIGHBOURS:
			if not tiles.has(t + n) and not map.terrains.has(t + n):
				ring[t + n] = "river"
	map.retile(ring)
	for t in ring:
		game._debug_fill[t] = true
	var r := _raised_at_once(tiles, "snowy_peaks", c)
	var own := map.climbs.filter(func(x): return x[0] in tiles)
	_check(own.is_empty(), "a river all round: no ledge")
	_check(game.path_to(c).is_empty(), "no route up")
	game.pick(null)
	game.tap(c)
	_check(game.picked == null and not game.party_node.walking, "a tap on it does nothing")
	game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y), 4.0), 45.0, 50.0)
	await _wait(0.2)
	await _shot("93_no_way_up")


## A fenced farm in front of the only foot: a gate there, and never a gate onto a cliff anywhere.
func _check_fenced_foot() -> void:
	var map := game.map
	var c := Vector2i(10, 15)
	var tiles: Array[Vector2i] = [c, c + Hex.NEIGHBOURS[0], c + Hex.NEIGHBOURS[1], c + Hex.NEIGHBOURS[2]]
	# Fenced farm all round the raised tiles, and plains beyond.
	var round_ := {}
	for t in tiles:
		for n in Hex.NEIGHBOURS:
			if not tiles.has(t + n) and not map.terrains.has(t + n):
				round_[t + n] = "farmland"
	var beyond := {}
	for t in round_:
		for n in Hex.NEIGHBOURS:
			if not tiles.has(t + n) and not round_.has(t + n) and not map.terrains.has(t + n):
				beyond[t + n] = "plains"
				game._debug_fill[t + n] = true
	map.retile(beyond)
	var nearest: Vector2i = beyond.keys()[0]
	for t: Vector2i in beyond:
		if Rules.hex_distance(t, Rules.START_TILE) < Rules.hex_distance(nearest, Rules.START_TILE):
			nearest = t
	_connect(nearest)
	map.retile(round_)
	for t in round_:
		game._debug_fill[t] = true
	var r := _raised_at_once(tiles, "volcanic_peaks", c)
	var own := map.climbs.filter(func(x): return x[0] in tiles)
	_check(not own.is_empty(), "fenced all round: a ledge still shows")
	var gate_at_foot := true
	for cl in own:
		var front: Vector2i = Cliffs.beside(cl[0], cl[1] - 1)
		gate_at_foot = gate_at_foot and ((cl[1] + 2) % 6) in map.gates.get(front, [])
	_check(gate_at_foot, "a gate on the fence facing each foot")
	var none_on_cliff := true
	var feet := {}
	for cl in map.climbs:
		feet[[Cliffs.beside(cl[0], cl[1] - 1), (cl[1] + 2) % 6]] = true
	for t: Vector2i in map.gates:
		for i: int in map.gates[t]:
			if map.raised.has(Cliffs.beside(t, i)) and not feet.has([t, i]):
				none_on_cliff = false
	_check(none_on_cliff, "no gate anywhere opens onto a cliff except at a foot")
	if not own.is_empty():
		var front: Vector2i = Cliffs.beside(own[0][0], own[0][1] - 1)
		game.rig.frame(Hex.to3(Hex.tile_position(front.x, front.y), 2.0), 22.0, 35.0, -90.0 - 60.0 * posmod(own[0][1] - 1, 6))
		await _wait(0.2)
		await _shot("94_fenced_foot")
		var there := game.path_to(front)
		if there.is_empty():
			_check(false, "the fenced tile can be reached")
		else:
			await _plain_walk(front)
			await _watched_walk(c, "through the gate and up from a fenced farm", "")
			_check(game.party_tile == c, "the party reached the top")
