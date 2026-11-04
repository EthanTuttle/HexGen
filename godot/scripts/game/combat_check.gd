class_name CombatCheck
extends Node
## Checks the combat maps (art/handoff/combat_*_kit.md) in the game (`-- --combatcheck`, add `--shots` for screens/combat/): every map's data
## and starts, which maps a tile rolls, heights and ways up, giants, a whole fight from the zoom in and back, and for every map its
## build time, triangles and how much of it the default camera shows. `--zoomclip` plays only the zoom. Prints COMBAT OK / COMBAT FAIL lines,
## then COMBAT DONE. A test aid only.

const HEAVIEST := ["scholars_town_lawns", "village_gardens", "village_lanes", "fortified_town_breach", "market_town_street"]

var game: Game
var shots := false
var failed := 0
var fight: Fight


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	print("COMBAT %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _shot(name: String) -> void:
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	if shots:
		var dir := ProjectSettings.globalize_path("res://screens/combat")
		DirAccess.make_dir_recursive_absolute(dir)
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("%s.png" % name))


func _run() -> void:
	fight = game.fight
	if "--zoomclip" in OS.get_cmdline_user_args():
		await _wait(1.0)
		game.debug_fight("scholars_town_court")
		await _wait(4.0)
		get_tree().quit()
		return
	await _wait(0.5)
	var t0 := Time.get_ticks_msec()
	Kit.meshes("res://art/combat_village.glb")
	Kit.meshes("res://art/combat_maps_village.glb")
	print("COMBAT first load of the village kit's two glbs: %d ms" % (Time.get_ticks_msec() - t0))
	_check_data()
	_check_choices()
	await _whole_fight()
	game.hud.visible = false
	game.map.visible = false
	game.party_node.visible = false
	fight.visible = true
	fight.game = game
	fight.rng = game.rng
	fight.active = false
	await _check_heights()
	await _check_giants()
	await _every_map()
	await _perf_heaviest()
	print("COMBAT DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _check_data() -> void:
	var maps := CombatMap.all()
	_check(maps.size() == 64, "%d maps: 16 forest, 16 farmland, 12 plains, 20 village" % maps.size())
	var missing := 0
	var empty := 0
	var bad_starts := []
	var giants := 0
	for id: String in maps:
		var data: Dictionary = maps[id]
		var cells := Kit.meshes("res://art/%s.glb" % CombatMap.SETS[data.set])
		var pieces := Kit.meshes("res://art/%s.glb" % data.set)
		for p: Dictionary in data.placements:
			if CombatMap.piece_mesh(p.piece, cells, pieces) == null:
				if String(p.piece).ends_with("_gates") or String(p.piece).ends_with("_wall_to_towers"):
					empty += 1   # in the glb with no mesh
				else:
					missing += 1
		var grid := CombatMap.grid_of(id)
		for st: Dictionary in data.starts:
			var c := Vector2i(int(st.q), int(st.r))
			if not grid.has(c) or grid[c].kind == "blocked" or st.get("z", 0.0) != grid[c].z:
				bad_starts.append("%s %s" % [id, st.mini])
			if String(st.mini).begins_with("giant_"):
				giants += 1
				for off: Vector2i in Minis.footprint(st.mini):
					var k: Vector2i = c + CombatMap.turned(off, int(st.get("turn", 0)) / 60)
					if not grid.has(k) or grid[k].kind == "blocked" or grid[k].z != grid[c].z or grid[k].way_up:
						bad_starts.append("%s %s body at %s" % [id, st.mini, k])
	_check(missing == 0, "every placement's piece is in its kit (%d missing, %d empty gates or tower joins)" % [missing, empty])
	_check(bad_starts.is_empty(), "every start stands on a free cell at its height, giants on level ground (%d giants) %s" % [giants, bad_starts])


func _check_choices() -> void:
	for name in ["forest", "plains", "farmland", "hills", "river", "desert", "swamp"]:
		_check(CombatMap.choices(name, true).is_empty(), "%s: no maps yet, so the old board" % name)
	_check(CombatMap.choices("deep_forest", false).size() == 3 and CombatMap.choices("deep_forest", true).size() == 4, "deep forest: 3 terrain maps, and its path map on a tile with paths")
	_check(CombatMap.choices("village", true).size() == 4, "a tier 0 village has its own maps")
	_check(CombatMap.choices("meadows", true).size() == 3, "plains variants have no path maps")
	_check(CombatMap.choices("college", true) == CombatMap.choices("scholars_town", true), "a landmark's tile takes its variant's maps (PLACEHOLDER)")


## Debug jump to a map with ways up and a giant, the zoom in, a Move, the enemies' phase, a win, and back to the map.
func _whole_fight() -> void:
	game.debug_fight("deep_forest_groves")
	await _wait(Rules.ZOOM_SECONDS * 0.5)
	await _shot("zoom_going_in")
	await _wait(Rules.ZOOM_SECONDS * 1.0)
	await _shot("zoom_coming_up")
	await _wait(Rules.ZOOM_SECONDS + 0.8)
	_check(fight.active and fight.map_id == "deep_forest_groves", "the debug jump opens the map by id")
	_check(not game.map.visible, "a fight is a separate map: the world map is hidden")
	_check(not fight.current.is_empty() and absf(game.rig.target.distance_to(fight.global_position + fight.current.mini.position)) < 0.5, "the camera has panned to whoever acts")
	await _shot("groves_default")
	var yaw := game.rig.yaw_deg
	game.rig.yaw_deg = yaw + 120.0
	var d := game.rig.distance
	game.rig._zoom(0.7)
	_check(game.rig.distance < d, "the fight's camera zooms")
	await _shot("groves_turned")
	game.rig.yaw_deg = yaw
	game.rig.distance = d
	fight.pick_card("move")
	await _wait(0.2)
	await _shot("groves_move")
	var u := fight.current
	var options := fight.reachable(u)
	_check(not options.is_empty(), "Move lights cells")
	var was: Vector2i = u.cell
	await fight.click_cell(options.keys()[-1])
	_check(u.cell != was, "a Move walks there")
	fight.end_phase()
	await _wait(0.2)
	if fight.phase == "allies":
		fight.confirm_end()
	var t0 := Time.get_ticks_msec()
	while fight.active and fight.phase != "allies" and Time.get_ticks_msec() - t0 < 40000:
		await get_tree().process_frame
	_check(fight.phase == "allies" or not fight.active, "the enemies' phase ends, with a giant among them")
	if fight.active:
		for e in fight.units:
			if not e.ally:
				e.hp = 0
				e.down = true
		fight._check_end()
		await fight.finished
	await _wait(0.2)
	game.after.done.emit()
	await _wait(0.4)
	_check(game.map.visible and not game.busy, "back on the world map")


func _load(id: String) -> void:
	fight.units.clear()
	fight.map_id = id
	fight._clear_overlays()
	fight._setup_map(id)
	fight.fit_distance = fight._fit()
	game.rig.focus = Vector2(368, 150)
	game.rig.frame(fight._middle(), fight.fit_distance, 52.0)


func _check_heights() -> void:
	var id := "deep_forest_groves"
	await get_tree().process_frame
	_load(id)
	var g := fight.grid
	var way := Vector2i.ZERO
	var low = null
	var high = null
	for c: Vector2i in g:
		if not g[c].way_up:
			continue
		for n: Vector2i in Hex.NEIGHBOURS:
			var m: Vector2i = c + n
			if g.has(m) and g[m].kind != "blocked" and fight.unit_at(m).is_empty():
				if g[m].z == 0.0 and low == null:
					low = m
				if g[m].z == 0.9 and high == null:
					high = m
		if low != null and high != null:
			way = c
			break
		low = null
		high = null
	_check(low != null and high != null, "a way up with low ground and high ground beside it")
	var u: Dictionary = fight.units[0]
	var keep: Vector2i = u.cell
	var mini_at: Vector3 = u.mini.position
	_check(fight.step_cost(u, low, way) == 2, "onto a landing from low ground: an ordinary move, +1 going up")
	_check(fight.step_cost(u, way, low) == 1, "down off a landing: no extra")
	_check(fight.step_cost(u, way, high) == 2, "from a landing up to high ground: +1")
	_check(fight.step_cost(u, high, way) == 1, "from high ground down to a landing: no extra")
	var sheer := 0
	for c: Vector2i in g:
		if g[c].z == 0.9:
			for n: Vector2i in Hex.NEIGHBOURS:
				if g.has(c + n) and g[c + n].z == 0.0 and g[c + n].kind != "blocked" and fight.unit_at(c + n).is_empty():
					sheer += 1
					_check(fight.step_cost(u, c, c + n) == -1 and fight.step_cost(u, c + n, c) == -1, "a 0.9 rise can't be crossed either way")
					break
		if sheer > 0:
			break
	var blocked := g.keys().filter(func(c): return g[c].kind == "blocked")
	u.cell = low
	var reach := fight.reachable(u)
	_check(not blocked.any(func(c): return reach.has(c)), "Move doesn't reach blocked cells")
	_check(reach.has(way) and not reach.has(high), "one Move reaches the landing; high ground takes another")
	# Highlights over treads, arrows, a mini's height, and a tap on each height.
	fight.current = u
	fight.sel = "move"
	u.ap = Rules.AP
	fight.phase = "allies"
	u.cell = keep
	var lifted: Mesh = fight._lifted_mesh(low)
	_check(lifted != fight._hex_mesh and lifted.get_aabb().size.y > 0.3 and fight._lifted_mesh(high) == fight._hex_mesh, "a highlight beside a way up climbs its treads; on high ground it stays flat")
	game.rig.frame(fight.global_position + fight.cell_point(way), 9.0, 52.0)
	await get_tree().process_frame
	await get_tree().process_frame
	u.cell = low
	u.mini.position = fight.cell_point(low)
	fight._show_overlays()
	await _wait(0.1)
	await _shot("way_up_highlight")
	for c: Vector2i in [low, way, high]:
		var p := game.rig.camera.unproject_position(fight.global_position + fight.cell_point(c))
		_check(fight._cell_under(p) == c, "a tap on %s at height %.2f picks it" % [c, g[c].z])
	await fight.board.step_along(u.mini, [way])
	_check(is_equal_approx(u.mini.position.y, 0.45), "a mini stands on the landing's height")
	var turns: float = fposmod(rad_to_deg(u.mini.rotation.y), 60.0)
	_check(turns < 0.5 or turns > 59.5, "its base stays lined up with its cell")
	await _shot("way_up_mini_on_landing")
	await fight.board.step_along(u.mini, [high])
	_check(is_equal_approx(u.mini.position.y, 0.9), "a mini stands on high ground")
	fight._clear_overlays()
	u.cell = keep
	u.mini.position = mini_at
	fight.current = {}


func _check_giants() -> void:
	_load("deep_forest_groves")
	var giant: Dictionary = fight.units.filter(func(x): return String(x.mini.name).begins_with("giant_"))[0]
	_check(giant.foot.size() == 3, "a 3-cell giant stands on 3 cells")
	var ok := true
	for c in fight.cells_of(giant):
		ok = ok and fight.unit_at(c) == giant
	_check(ok, "each of its cells finds it, so any can be attacked or aimed at")
	var middle := Vector2.ZERO
	for c in fight.cells_of(giant):
		middle += Hex.cell_position(c.x, c.y)
	middle /= 3.0
	_check(Vector2(giant.mini.position.x, -giant.mini.position.z).distance_to(middle) < 0.01, "its mini stands at the middle of its cells")
	# The far cell: a mini beside it is next to the giant, though far from its anchor.
	var ally: Dictionary = fight.units[0]
	var keep: Vector2i = ally.cell
	var far: Vector2i = fight.cells_of(giant)[-1]
	var spot = null
	for n: Vector2i in Hex.NEIGHBOURS:
		var m: Vector2i = far + n
		if Rules.hex_distance(m, giant.cell) == 2 and fight.grid.has(m) and fight.unit_at(m).is_empty():
			spot = m
	if spot != null:
		ally.cell = spot
		_check(fight.dist(ally, giant) == 1 and fight.dist(giant, ally) == 1, "it melees anyone next to any of its cells, and they it")
		var attack := Cards.get_card("attack", "spear")
		_check(fight.in_reach(ally, giant, attack), "an attack reaches it by any of its cells")
		ally.cell = keep
	# A lane one cell wide keeps it out, not a one-cell mini.
	var saved := fight.grid
	var lane := {}
	for q in range(-6, 7):
		lane[Vector2i(q, 0)] = {kind = "open", z = 0.0, way_up = false}
	fight.grid = lane
	var body := {foot = giant.foot, cell = Vector2i(0, 0), ally = false, down = false}
	var small := {foot = [Vector2i.ZERO] as Array[Vector2i], cell = Vector2i(0, 0), ally = false, down = false}
	var keep_units := fight.units
	fight.units = []
	_check(fight.step_cost(body, Vector2i(0, 0), Vector2i(1, 0)) == -1, "narrow lanes keep giants out")
	_check(fight.step_cost(small, Vector2i(0, 0), Vector2i(1, 0)) == 1, "a one-cell mini goes down the same lane")
	# On open ground it moves whole, and a landing or a rise under any of its cells stops it (PLACEHOLDER: level ground only).
	var open := {}
	for q in range(-5, 6):
		for r in range(-5, 6):
			open[Vector2i(q, r)] = {kind = "open", z = 0.0, way_up = false}
	fight.grid = open
	_check(fight.step_cost(body, Vector2i(0, 0), Vector2i(1, 0)) == 1, "on open ground it moves")
	var one: Vector2i = Vector2i(1, 0) + giant.foot[-1]
	open[one] = {kind = "open", z = 0.45, way_up = true}
	_check(fight.step_cost(body, Vector2i(0, 0), Vector2i(1, 0)) == -1, "it stays on level ground")
	fight.units = keep_units
	fight.grid = saved
	var turn: float = giant.mini.rotation.y
	await fight.board.step_along(giant.mini, [giant.cell])
	_check(is_equal_approx(giant.mini.rotation.y, turn), "its facing stays fixed")
	_check(not fight.has_method("push") and not fight.has_method("pull"), "nothing in the fight moves a unit but its own Move, so nothing moves a giant")


## Every map at the default camera: its numbers and how many of its walkable cells show, by drawing each with a marker and looking for it.
func _every_map() -> void:
	var ids := CombatMap.all().keys()
	ids.sort()
	var markers := StandardMaterial3D.new()
	markers.albedo_color = Color(1, 0, 1)
	markers.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	var worst_tris := 0
	for id: String in ids:
		_load(id)
		await get_tree().process_frame
		await _shot("map_%s" % id)
		for u in fight.units:
			u.mini.visible = false
		var cells: Array = fight.grid.keys().filter(func(c): return fight.grid[c].kind != "blocked")
		var marks := []
		for c: Vector2i in cells:
			var mi := MeshInstance3D.new()
			mi.mesh = fight._hex_mesh
			mi.material_override = markers
			mi.scale = Vector3(0.45, 1.0, 0.45)
			mi.position = fight.cell_point(c) + Vector3(0, Rules.CELL_TOP + 0.03, 0)
			fight.board.add_child(mi)
			marks.append(mi)
		for _f in 3:
			await get_tree().process_frame
		await StallWatch.drawn(get_tree())
		var img := game.get_viewport().get_texture().get_image()
		var hidden := 0
		var off := 0
		var size := Vector2(img.get_width(), img.get_height())
		var cam := game.rig.camera
		for c: Vector2i in cells:
			var at := cam.unproject_position(fight.global_position + fight.cell_point(c) + Vector3(0, Rules.CELL_TOP + 0.03, 0)) * size / game.get_viewport().get_visible_rect().size
			var sees := false
			if at.x >= 0 and at.y >= 0 and at.x < size.x and at.y < size.y:
				for d: Vector2 in [Vector2.ZERO, Vector2(3, 0), Vector2(-3, 0), Vector2(0, 2), Vector2(0, -2)]:
					var q := (at + d).clamp(Vector2.ZERO, size - Vector2.ONE)
					var col := img.get_pixelv(q)
					sees = sees or (col.r > 0.8 and col.g < 0.3 and col.b > 0.8)
				hidden += 0 if sees else 1
			else:
				off += 1
		for mi in marks:
			mi.queue_free()
		var with_minis := fight.map_tris
		for u in fight.units:
			var mesh: Mesh = u.mini.get_node("body").mesh
			for s in mesh.get_surface_count():
				with_minis += mesh.surface_get_array_index_len(s) / 3
		worst_tris = maxi(worst_tris, with_minis)
		print("COMBAT MAP %s: %d cells, %d walkable; %d tris, %d with minis; build %.0f ms; camera %.1f m%s; hidden from the default view %d, off screen %d" % [id,
			fight.grid.size(), cells.size(), fight.map_tris, with_minis, fight.map_build_ms, fight.fit_distance,
			" (at the limit)" if fight.fit_distance >= Rules.FIGHT_DISTANCE_MAX else "", hidden, off])
	print("COMBAT worst map with minis: %d triangles" % worst_tris)


func _perf_heaviest() -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	for id: String in HEAVIEST:
		_load(id)
		for _f in 60:
			await get_tree().process_frame
		var rs := RenderingServer
		var draws := rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)
		var tris := rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)
		var t0 := Time.get_ticks_usec()
		var worst := 0
		var last := t0
		for _f in 180:
			await get_tree().process_frame
			var now := Time.get_ticks_usec()
			worst = maxi(worst, now - last)
			last = now
		print("COMBAT PERF %s: %d tris in frame, %d draw calls; %.1f ms a frame, worst %.1f (Mac, phone settings, vsync off); build %.0f ms" % [id, tris, draws, (Time.get_ticks_usec() - t0) / 180000.0, worst / 1000.0, fight.map_build_ms])
		await _shot("perf_%s" % id)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)
