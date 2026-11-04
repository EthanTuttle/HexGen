class_name FeyCheck
extends Node
## Checks the Feywild crossing (tiles v84, art/handoff/feywild_kit.md) in the game (`-- --feycheck`, add `--shots` for screens/fey_*.png, `--feyclip` to film the gate and a walk over
## a seam with --write-movie): the region, its seasons and sharp edges, the gate's parts, walking, placement time and draw calls. Prints FEY OK / FEY FAIL lines, then FEY DONE. A test aid only.

const BUDGET := 4816 - 412   # the kit's budget, less the slab

var game: Game
var map: MapBoard
var shots := false
var failed := 0
var region: Dictionary


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("FEY %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _shot(name: String) -> void:
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	if shots:
		game.get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path("res://screens").path_join("fey_%s.png" % name))


func _look(at: Vector3, dist: float, pitch: float, name: String, yaw := 0.0) -> void:
	game.rig.frame(at, dist, pitch, yaw)
	await _wait(0.3)
	await _shot(name)


func _run() -> void:
	map = game.map
	var t0 := Time.get_ticks_msec()
	game.spawn_forest_regions()
	print("FEY spawn of every debug region took %d ms" % (Time.get_ticks_msec() - t0))
	await _wait(1.0)
	game.debug_auto_cross = true
	for g: Dictionary in game.regions:
		if g.variant == "feywild_crossing":
			region = g
	if "--feyclip" in OS.get_cmdline_user_args():
		await _clip()
		get_tree().quit()
		return
	_check(not region.is_empty(), "the 12-tile region is on the map")
	await _tiles()
	await _walking()
	await _perf()
	await _views()
	print("FEY DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _tiles() -> void:
	var gate: Vector2i = region.landmark_tile
	_check(map.terrains[gate] == "feygate", "the Fey Gate stands on its tile")
	var seasons := {}
	var clash := 0
	var worst := 0
	var culled := 0
	var fell := 0
	for t: Vector2i in region.tiles:
		var tile: Dictionary = map.fey_of(t).tile
		seasons[tile.season] = true
		worst = maxi(worst, FeyLands.face_tris(tile.ground) + FeyLands.face_tris(tile.trail) + FeyLands.face_tris(tile.stand))
		for n: Vector2i in Hex.NEIGHBOURS:
			if region.tiles.has(t + n) and FeyLands.season_of(t.x, t.y) == FeyLands.season_of(t.x + n.x, t.y + n.y):
				clash += 1
		for name: String in ["fey_ground", "fey_stand"]:
			var mi := map.tile_node(t).get_node(name) as MeshInstance3D
			if (mi.mesh.surface_get_material(0) as BaseMaterial3D).cull_mode != BaseMaterial3D.CULL_DISABLED:
				culled += 1
		var falls := map.tile_node(t).get_node_or_null("fey_falls")
		if (falls != null) == tile.effects.is_empty():
			_check(false, "%s (%s): what falls doesn't match its season" % [t, tile.season])
		fell += 1 if falls != null else 0
	_check(clash == 0, "neighbours never share a season (%s)" % [seasons.keys()])
	_check(worst <= BUDGET, "the worst tile is %d triangles, within the kit's %d" % [worst, BUDGET])
	_check(culled == 0, "the Feywild mesh draws double-sided")
	_check(fell > 0, "%d tiles have snow, leaves or petals falling" % fell)
	# Sharp edges: both sides of an outer edge marked; a neighbour's slab ignores it.
	_check(absf(map._ground_img.get_pixel(gate.x + 32, gate.y + 32).a - 0.75) < 0.01, "its tiles are marked so the ground shader leaves their outer edges sharp")
	var node := map.tile_node(gate)
	var portal := node.get_node("fey_portal") as MeshInstance3D
	_check(portal.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_OFF and portal.mesh.surface_get_material(0) is ShaderMaterial, "the portal has its own material, with no shadow")
	var body: Mesh = null
	for c in node.get_children():
		if c is MeshInstance3D and c.has_meta("piece") and c.get_meta("piece") == "feygate_centre":
			body = c.mesh
	var names := []
	if body:
		for k in body.get_surface_count():
			names.append(Kit.material_name(body, k))
	_check(body != null and not names.any(func(n): return n.begins_with("fey_portal")), "the gate's piece no longer holds the portal, which would cast a solid shadow")
	_check(node.get_node_or_null("fey_wisps") != null, "the gate has its wisps")
	_check(GroundCover.DENSITY["feywild_crossing"] == 0.0, "no ground cover on it: it holds its own tufts")
	await get_tree().process_frame


func _walking() -> void:
	var gate: Vector2i = region.landmark_tile
	var g := map.path_graph(gate)
	var stop: Vector2 = Hex.tile_position(gate.x, gate.y) + Water.turned(FeyLands.GATE_STOP, map.landmark_turns.get(gate, 0))
	_check(g.nodes[g.stand].distance_to(stop) < 0.05, "a party stops on the gate's entrance side")
	var plain: Vector2i = region.tiles.filter(func(t): return t != gate)[0]
	var pg := map.path_graph(plain)
	_check(pg.edge_node.size() == 6, "any tile can be crossed from every edge")
	var reg: FeyLands.Region = map.fey_of(plain).region
	var trail_tile = null
	for t: Vector2i in region.tiles:
		if t != gate and reg.edges[t].size() >= 2:
			trail_tile = t
			break
	if trail_tile != null:
		var tg := map.path_graph(trail_tile)
		var e: Array = reg.edges[trail_tile]
		var line := tg.route(tg.edge_node[e[0]], tg.edge_node[e[1]])
		var want := SwampLands.trail_line(trail_tile.x, trail_tile.y, e[0], e[1])
		var at := Hex.tile_position(trail_tile.x, trail_tile.y)
		_check(SwampLands.line_dist(line[line.size() / 2] - at, [want]) < 0.1, "between trail edges a party walks the trail")
	await get_tree().process_frame


func _perf() -> void:
	var names := {}
	for t: Vector2i in region.tiles:
		names[t] = map.terrains[t]
	var t2 := Time.get_ticks_usec()
	map._new_fey(names, map._fey_key(names))
	print("FEY PERF working out the region's forest (off the main thread in play): %.0f ms for %d tiles (Mac)" % [(Time.get_ticks_usec() - t2) / 1000.0, region.tiles.size()])
	var around: Vector2i = region.tiles[3]
	var open := Vector2i.ZERO
	for t: Vector2i in region.tiles:
		for n: Vector2i in Hex.NEIGHBOURS:
			if not map.terrains.has(t + n):
				open = t + n
				around = t
				break
		if open != Vector2i.ZERO:
			break
	map.fey_build_us = 0
	var t0 := Time.get_ticks_usec()
	map.retile({around: map.terrains[around]})
	print("FEY PERF rebuilding one tile (a card placed beside it): %.0f ms in all, %.0f ms of it building its meshes (Mac)" % [(Time.get_ticks_usec() - t0) / 1000.0, map.fey_build_us / 1000.0])
	await _wait(0.5)
	var at := Vector3.ZERO
	for t: Vector2i in region.tiles:
		at += Hex.to3(Hex.tile_position(t.x, t.y)) / region.tiles.size()
	game.rig.frame(at, 34.0, 50.0)
	await _wait(0.5)
	var rs := RenderingServer
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	for _f in 30:
		await get_tree().process_frame
	var t1 := Time.get_ticks_usec()
	for _f in 120:
		await get_tree().process_frame
	print("FEY PERF the whole region in view: %d draw calls, %d triangles in a frame, %.1f ms a frame (Mac, vsync off)" % [rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME), rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME), (Time.get_ticks_usec() - t1) / 120000.0])
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)


func _views() -> void:
	game.hud.visible = false
	game.rig.focus = Vector2(422, 195)
	var gate: Vector2i = region.landmark_tile
	var at := Vector3.ZERO
	for t: Vector2i in region.tiles:
		at += Hex.to3(Hex.tile_position(t.x, t.y)) / region.tiles.size()
	await _look(at, 40.0, 50.0, "region")
	await _look(Hex.to3(Hex.tile_position(gate.x, gate.y), 1.9), 11.0, 18.0, "gate", -70.0 - 60.0 * map.landmark_turns.get(gate, 0))
	await _look(Hex.to3(Hex.tile_position(gate.x, gate.y)), 14.0, 42.0, "gate_tile")
	var seam: Vector2i = region.tiles[3]
	for n: Vector2i in Hex.NEIGHBOURS:
		if region.tiles.has(seam + n):
			var mid := (Hex.tile_position(seam.x, seam.y) + Hex.tile_position(seam.x + n.x, seam.y + n.y)) * 0.5
			await _look(Hex.to3(mid), 12.0, 40.0, "seam")
			break
	# An outer edge against plains: sharp on both sides.
	for t: Vector2i in region.tiles:
		for i in 6:
			if not region.tiles.has(t + Hex.NEIGHBOURS[i]) and map.terrains.has(t + Hex.NEIGHBOURS[i]):
				await _look(Hex.to3(Hex.tile_position(t.x, t.y) + Water.normal(i) * Water.A), 11.0, 45.0, "outer_edge")
				return


## The gate with its wisps, then a walk over a seam, without the panels.
func _clip() -> void:
	game.hud.visible = false
	game.rig.focus = Vector2(422, 195)
	var gate: Vector2i = region.landmark_tile
	var turn: int = map.landmark_turns.get(gate, 0)
	game.rig.frame(Hex.to3(Hex.tile_position(gate.x, gate.y), 1.8), 11.0, 16.0, -75.0 - 60.0 * turn)
	await _wait(6.0)
	game.rig.frame(Hex.to3(Hex.tile_position(gate.x, gate.y), 0.8), 15.0, 40.0, -110.0 - 60.0 * turn)
	await _wait(4.0)
	var from: Vector2i = region.tiles.filter(func(t): return t != gate)[0]
	var to := from
	for n: Vector2i in Hex.NEIGHBOURS:
		if region.tiles.has(from + n) and from + n != gate:
			to = from + n
			break
	game.party_node.place_at(from)
	game.party_tile = from
	game.rig.frame(Hex.to3((Hex.tile_position(from.x, from.y) + Hex.tile_position(to.x, to.y)) * 0.5), 12.0, 42.0)
	await _wait(0.5)
	game.walk_to(to)
	while game.busy:
		await get_tree().process_frame
	await _wait(1.0)
