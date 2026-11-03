class_name PlainsCheck
extends Node
## Checks the plains kit (tiles v38) in the game (`-- --plainscheck`, add `--shots` for screens/plains_*.png): density
## bands turned toward the landmark, ordinary centres by hash, no trail pieces, the battlefield's alternate wedge and
## the tourney bunting, each landmark's turn, no_cover, BENT tufts, lightning, and the party's curved route to each
## entrance. Prints PLAINS OK / PLAINS FAIL lines, then PLAINS DONE. A test aid only.

var game: Game
var shots := false
var failed := 0


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("PLAINS %s: %s" % ["OK" if ok else "FAIL", what])
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
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("plains_%s.png" % name))
		print("SAVED plains_%s" % name)


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
	for v: String in Game.DEBUG_PLAINS:
		_check_region(map, v)
	_check_edges(map)
	_check_tier0(map)
	_check_cover(map)
	await _check_lightning(map)
	await _pictures(map)
	var names: Array = Game.DEBUG_PLAINS.keys()
	for k in names.size():
		var v: String = names[k]
		await _walk_in(map, v)
		if k < names.size() - 1:
			await _leave(_far(map, v), v, "40_leaving_camp" if k == 0 else "")
	await _walk_out(map)
	print("PLAINS DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _check_region(map: MapBoard, v: String) -> void:
	var g := _region(v)
	var lm: Vector2i = g.landmark_tile
	var name: String = map.terrains[lm]
	var bands := {0: 0, 1: 0, 2: 0, 3: 0}
	var ok := true
	for t: Vector2i in g.tiles:
		var d: int = map.flow_dist[t]
		bands[mini(d, 3)] += 1
		if d == 0:
			continue
		var piece := v + "_centre"
		var turn := int(GroundCover.hash01(t.x * 31 + 7, t.y * 17 + 3, 14) * 6)
		if d <= 2:
			piece = v + ("_centre_near" if d == 1 else "_centre_mid")
			turn = LandmarkFlow.toward_edge(t, map.flow_toward)
			# The piece's +X side faces the landmark's side: the neighbour one step closer.
			if map.flow_toward[t] != t + Hex.NEIGHBOURS[turn]:
				ok = false
		elif GroundCover.hash01(t.x, t.y, 13) < 0.5:
			piece = v + "_centre_b"
		if not _has(t, piece, turn):
			ok = false
			print("  %s: wants %s turned %d" % [t, piece, turn])
	_check(ok, "%s: near, mid and ordinary centres, turned toward the landmark or by hash (%d near, %d mid, %d far)" % [v, bands[1], bands[2], bands[3]])
	_check(_has(lm, name + "_centre", map.landmark_turns.get(lm, 0)), "%s: centre turned %d, toward the farthest tile" % [name, map.landmark_turns.get(lm, 0)])
	var trail_pieces := 0
	for t: Vector2i in g.tiles:
		trail_pieces += _pieces(t).filter(func(c): return "_edge_trail" in c.get_meta("piece") or "_edge_landmark" in c.get_meta("piece")).size()
	_check(trail_pieces == 0 and not map.trail_edge(g.tiles[1], map.flow_toward[g.tiles[1]]), "%s: no trail pieces and no trail edges" % v)


func _check_edges(map: MapBoard) -> void:
	var g := _region("battlefield")
	var alt := 0
	var ok := true
	for t: Vector2i in g.tiles:
		for i in 6:
			var joined := MapBoard.linked(map.terrains[t], map.terrains.get(t + Hex.NEIGHBOURS[i]))
			var want := joined and GroundCover.hash01(t.x * 6 + i, t.y, 8) < 0.5
			var kit := Variants.wedges_of(map.terrains[t])
			var got := _has(t, kit + "_edge_same_b", i)
			ok = ok and want == got
			if got:
				alt += 1
	_check(ok and alt > 0, "battlefield: %d broken spears, on joined edges by hash" % alt)
	var bunting := 0
	var tg := _region("tourney_fields")
	var good := true
	for t: Vector2i in tg.tiles:
		for i in 6:
			var joined := MapBoard.linked(map.terrains[t], map.terrains.get(t + Hex.NEIGHBOURS[i]))
			var has := _has(t, "tourney_fields_edge_other", i)
			good = good and has == (not joined)
			if has:
				bunting += 1
	_check(good, "tourney fields: bunting on all %d outer edges only (plains count as joined)" % bunting)


func _check_tier0(map: MapBoard) -> void:
	var ok := true
	var n := 0
	for t: Vector2i in map.terrains:
		if map.terrains[t] != "plains":
			continue
		n += 1
		var piece := "plains_centre_b" if GroundCover.hash01(t.x, t.y, 13) < 0.5 else "plains_centre"
		ok = ok and _has(t, piece, int(GroundCover.hash01(t.x * 31 + 7, t.y * 17 + 3, 14) * 6))
	_check(ok and n > 0, "tier 0 plains: %d tiles with their lone trees turned by hash" % n)


## The tufts of a tile: its ground cover's triangles, by height above the ground.
func _check_cover(map: MapBoard) -> void:
	# no_cover: the Nomad Camp's whole yard (r 2.5) stays clear, measured on the mesh; its ground has density 0 anyway,
	# so measure on the stormy tiles, whose burns sit in dense grass.
	var checked := 0
	var ok := true
	var near_points := 0
	for t: Vector2i in _region("stormy_plains").tiles:
		var node := map.tile_node(t)
		for mi in node.get_children():
			if not (mi is MeshInstance3D and mi.has_meta("piece")):
				continue
			for c in Kit.path_data(mi.get_meta("piece")).get("no_cover", []):
				var at := Hex.tile_position(t.x, t.y) + Vector2(c.at[0], -c.at[2]).rotated(mi.rotation.y)
				checked += 1
				for cov in node.get_children():
					if cov.name == "ground_cover":
						var v: PackedVector3Array = cov.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
						for p in v:
							if p.y < 0.01 and Vector2(p.x, -p.z).distance_to(at) < c.r - 0.25:
								near_points += 1
								ok = false
	_check(ok and checked > 0, "no_cover: %d circles on stormy tiles kept clear (%d tuft roots inside)" % [checked, near_points])
	# BENT: every stormy tuft leans +X, alpha 0 for the ripple; other tiles' tufts don't.
	var bent := 0
	for cov in map.tile_node(_region("stormy_plains").tiles[-1]).get_children():
		if cov.name == "ground_cover":
			var a: Array = cov.mesh.surface_get_arrays(0)
			var cols: PackedColorArray = a[Mesh.ARRAY_COLOR]
			bent = Array(cols).filter(func(c): return c.a < 0.5).size()
	var straight := 0
	for cov in map.tile_node(_region("meadows").tiles[-1]).get_children():
		if cov.name == "ground_cover":
			straight = Array(cov.mesh.surface_get_arrays(0)[Mesh.ARRAY_COLOR]).filter(func(c): return c.a < 0.5).size()
	_check(bent > 0 and straight == 0, "BENT: stormy tufts marked to ripple (%d vertices on one tile), meadows' not" % bent)


func _check_lightning(map: MapBoard) -> void:
	var l := map.lightning
	if l == null:
		_check(false, "lightning exists")
		return
	var stormy := _region("stormy_plains")
	var c: Vector2i = Game.DEBUG_PLAINS.stormy_plains
	game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y)), 58.0, 50.0)
	await _wait(0.4)
	var before := l.strikes
	l.strike()
	await _wait(0.03)
	_check(l.strikes == before + 1 and l.tiles.size() == stormy.tiles.size(), "lightning strikes among the %d stormy tiles" % l.tiles.size())
	await _wait(0.4)
	_check(not l._bolt.visible, "a bolt is brief")
	# Hold one on screen for the picture.
	l.strike()
	l.set_process(false)
	l._bolt.visible = true
	var b := l._bolt.position
	game.rig.frame(Vector3(b.x, 0, b.z), 58.0, 50.0)
	await _shot("20_lightning")
	l.set_process(true)


func _pictures(map: MapBoard) -> void:
	# How each region reads at the game camera: its opening zoom and tilt, HUD on.
	var n := 1
	for v: String in Game.DEBUG_PLAINS:
		var g := _region(v)
		var at := Vector2.ZERO
		for t: Vector2i in g.tiles:
			at += Hex.tile_position(t.x, t.y)
		game.rig.frame(Hex.to3(at / g.tiles.size()), 58.0, 50.0)
		await _wait(0.8)
		await _shot("%02d_game_camera_%s" % [n, v])
		n += 1
	var focus := game.rig.focus
	game.ui.visible = false
	game.rig.focus = Vector2(422, 195)
	for v: String in Game.DEBUG_PLAINS:
		var lm: Vector2i = _region(v).landmark_tile
		var e := map.entrance_angle(lm)
		game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y), 0.8), 18.0, 36.0, -90.0 - rad_to_deg(e))
		await _wait(0.6)
		await _shot("%02d_landmark_%s" % [n, map.terrains[lm]])
		n += 1
	var tier0: Vector2i = Rules.START_TILE
	game.rig.frame(Hex.to3(Hex.tile_position(tier0.x, tier0.y)), 34.0, 50.0)
	await _wait(0.5)
	await _shot("%02d_tier0_plains" % n)
	game.rig.focus = focus
	game.ui.visible = true


func _walk_to(goal: Vector2i) -> void:
	if goal == game.party_tile:
		return
	game.walk_to(goal)
	while game.busy:
		await get_tree().process_frame
	await _wait(Rules.SETTLE_SECONDS)


func _far(map: MapBoard, v: String) -> Vector2i:
	var g := _region(v)
	var far: Vector2i = g.landmark_tile
	for t: Vector2i in g.tiles:
		if map.flow_dist.get(t, 0) > map.flow_dist.get(far, 0):
			far = t
	return far


func _walk_in(map: MapBoard, v: String) -> void:
	var g := _region(v)
	var lm: Vector2i = g.landmark_tile
	await _walk_to(_far(map, v))
	var route := game.party_node.route_preview(game.path_to(lm))
	var c := Hex.tile_position(lm.x, lm.y)
	# Curved, not along the middle lines, where the route leaves far's tile; and never inside the landmark's yard
	# except along the way in from the entrance.
	var e := map.entrance_angle(lm)
	var graph := map.path_graph(lm)
	var door: Vector2 = graph.nodes[graph.stand]
	var ok := true
	for p in route:
		var r := p.distance_to(c)
		if r < Rules.ROUND_LANDMARK - 0.05:
			var along := (p - c).dot(Vector2.from_angle(e))
			var off := absf((p - c).cross(Vector2.from_angle(e)))
			if along < 0.0 or off > 0.1:
				ok = false
	_check(ok, "%s: the route stays outside the landmark except on the way in through its entrance" % v)
	await _walk_to(lm)
	var ms := game.party_node.members
	var hero: Vector3 = ms[0].node.position
	_check(Vector2(hero.x, -hero.z).distance_to(door) < 0.3, "%s: the party stops at the entrance" % v)
	game.rig.frame(Hex.to3(door), 18.0, 40.0, -90.0 - rad_to_deg(e))
	await _wait(0.5)
	await _shot("3%d_party_at_%s" % [Game.DEBUG_PLAINS.keys().find(v), map.terrains[lm]])


## Out of the last landmark: back out through its entrance to a plain tile.
func _walk_out(map: MapBoard) -> void:
	var lm := game.party_tile
	var other: Vector2i = Game.DEBUG_FOREST.heartwood
	var route := game.party_node.route_preview(game.path_to(other))
	var e := map.entrance_angle(lm)
	var c := Hex.tile_position(lm.x, lm.y)
	var ok := true
	for p in route:
		if p.distance_to(c) < Rules.ROUND_LANDMARK - 0.05 and (absf((p - c).cross(Vector2.from_angle(e))) > 0.1 or (p - c).dot(Vector2.from_angle(e)) < 0.0):
			ok = false
	_check(ok, "leaving a landmark goes out through its entrance")
	await _leave(other, "last plains landmark")
	_check(game.party_tile == other, "the party walked out and away")


## Out of a landmark, watching the followers peel off behind the hero.
func _leave(goal: Vector2i, what: String, shots_as := "") -> void:
	var watch := LeaveWatch.new(game.party_node)
	game.walk_to(goal)
	var t := 0.0
	var next_shot := 0
	const TIMES := [0.5, 1.1, 1.7]
	while game.busy:
		await get_tree().process_frame
		watch.frame()
		t += get_process_delta_time()
		if shots_as != "" and next_shot < TIMES.size() and t >= TIMES[next_shot]:
			next_shot += 1
			await _shot("%s_%d" % [shots_as, next_shot])
	_check(game.party_node.peeled and watch.passed(), "%s: leaving, %s" % [what, watch.report()])
