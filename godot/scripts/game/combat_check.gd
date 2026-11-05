class_name CombatCheck
extends Node
## Checks the combat maps (art/handoff/combat_*_kit.md) in the game (`-- --combatcheck`, add `--shots` for screens/combat/): every map's data
## and starts, which maps a tile rolls, heights and ways up, giants, a whole fight from the zoom in and back, and for every map its
## build time, triangles and how much of it the default camera shows. `--zoomclip` plays only the zoom; `--opening=<id>` shoots only how that map's fight opens; `--lavaclip` films Fissures' cone and fall (with --write-movie); `--hillsonly` skips to the hillside checks. Prints COMBAT OK / COMBAT FAIL lines,
## then COMBAT DONE. A test aid only.

const HEAVIEST := ["scholars_town_lawns", "village_gardens", "village_lanes", "fortified_town_breach", "market_town_street"]

var game: Game
var shots := false
var failed := 0
var fight: Fight
var map_tris_of := {}


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
	if "--lavaclip" in OS.get_cmdline_user_args():
		await _lava_clip()
		get_tree().quit()
		return
	if "--lavatile" in OS.get_cmdline_user_args():   # the volcanic map tiles' lava, to set beside a fight's
		game.spawn_forest_regions()
		await _wait(1.0)
		game.hud.visible = false
		game.rig.focus = Vector2(422, 195)
		for g: Dictionary in game.regions:
			if g.variant == "volcanic_peaks":
				var at := Hex.tile_position(g.landmark_tile.x, g.landmark_tile.y)
				game.rig.frame(Hex.to3(at, 5.0), 20.0, 48.0)
				await _wait(0.5)
				await _shot("volcanic_tile")
		get_tree().quit()
		return
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--opening="):
			await _wait(1.0)
			game.debug_fight(arg.trim_prefix("--opening="))
			await _wait(Rules.ZOOM_SECONDS * 2.0 + 1.5)
			await _shot("opening_%s" % arg.trim_prefix("--opening="))
			get_tree().quit()
			return
	await _wait(0.5)
	var t0 := Time.get_ticks_msec()
	Kit.meshes("res://art/combat_village.glb")
	Kit.meshes("res://art/combat_maps_village.glb")
	print("COMBAT first load of the village kit's two glbs: %d ms" % (Time.get_ticks_msec() - t0))
	_check_data()
	_check_choices()
	if not "--hillsonly" in OS.get_cmdline_user_args():
		await _whole_fight()
	game.hud.visible = false
	game.map.visible = false
	game.party_node.visible = false
	fight.visible = true
	fight.game = game
	fight.rng = game.rng
	fight.active = false
	if "--hillsonly" in OS.get_cmdline_user_args():
		fight.hud = CombatHud.new(fight)
		game.safe.add_child(fight.hud)
		await _check_hills()
		print("COMBAT DONE: %d failed" % failed)
		get_tree().quit()
		return
	await _check_heights()
	await _check_giants()
	await _check_hills()
	await _check_facing()
	await _every_map()
	await _perf_heaviest()
	print("COMBAT DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _check_data() -> void:
	var maps := CombatMap.all()
	_check(maps.size() == 90, "%d maps: 19 forest, 20 farmland, 15 plains, 20 village, 16 hills" % maps.size())
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
	for name in ["forest", "plains"]:
		_check(CombatMap.choices(name, true).size() == 3, "tier 0 %s: its 3 maps" % name)
	_check(CombatMap.choices("farmland", false).size() == 3 and CombatMap.choices("farmland", true).size() == 4, "tier 0 farmland: 3 terrain maps, and its path map on a tile with paths")
	for name in ["river", "desert", "swamp"]:
		_check(CombatMap.choices(name, true).is_empty(), "%s: no maps yet, so the old board" % name)
	_check(CombatMap.choices("deep_forest", false).size() == 3 and CombatMap.choices("deep_forest", true).size() == 4, "deep forest: 3 terrain maps, and its path map on a tile with paths")
	_check(CombatMap.choices("village", true).size() == 4, "a tier 0 village has its own maps")
	_check(CombatMap.choices("meadows", true).size() == 3, "plains variants have no path maps")
	for name in ["hills", "highlands", "snowy_peaks", "volcanic_peaks"]:
		_check(CombatMap.choices(name, true).size() == 3, "%s: 3 maps" % name)
	_check(CombatMap.choices("monastery_heights", false).size() == 3 and CombatMap.choices("monastery_heights", true).size() == 4, "monastery heights: 3 terrain maps, and its path map on a tile with paths")
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
	var opens := fight.opening()
	_check(game.rig.distance == opens.distance and game.rig.target.distance_to(opens.target) < 0.5, "the fight opens close, %.1f m back, on the party and %d foes" % [opens.distance, opens.framed])
	_check(_on_screen(fight.current), "whoever acts first is in the opening")
	await _shot("groves_default")
	var held := game.rig.target
	game.rig._pan(Vector2(-200000, 90000))
	var lim := game.rig.limits
	_check(lim.has_area() and lim.grow(0.01).has_point(Vector2(game.rig.target.x, game.rig.target.z)), "a pan stops a little past the map's cells")
	game.rig._pan(Vector2(200000, -90000))
	_check(lim.grow(0.01).has_point(Vector2(game.rig.target.x, game.rig.target.z)), "and on its other side")
	game.rig.target = held
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
	_check(not game.rig.limits.has_area(), "the world map's camera has no fight limits")


func _load(id: String) -> void:
	fight.units.clear()
	fight.map_id = id
	fight._clear_overlays()
	fight._setup_map(id)
	fight.open_distance = _whole_map_distance()
	game.rig.focus = fight.open_area().get_center()
	var c: Array = CombatMap.all()[id].centre
	game.rig.frame(fight.position + Hex.to3(Vector2(c[0], c[1])), fight.open_distance, 52.0)


## How far back the whole map fits, for counting what tall pieces hide (no longer how a fight opens: DOCS, starts close, then pans).
func _whole_map_distance() -> float:
	var box := fight._cells_box()
	var open := fight.open_area()
	var wide := (box.size.x + 1.2) / (fight._per_unit() * open.size.x)
	var deep := (box.size.y + 2.4) * sin(deg_to_rad(52.0)) / (fight._per_unit() * open.size.y)
	return clampf(maxf(wide, deep), 14.0, 34.0)


## The hillsides (art/handoff/combat_hills_kit.md): the height rule on all 16, the lifts' costs, Climb and its walls, lava's burns and flow.
func _check_hills() -> void:
	var ids := CombatMap.all().keys().filter(func(id): return CombatMap.all()[id].set == "combat_maps_hills")
	var bad_gaps := []
	var bad_steps := []
	var cut_off := []
	var walker := {foot = [Vector2i.ZERO]}
	for id: String in ids:
		_load(id)
		var g := fight.grid
		var people := fight.units
		fight.units = []
		for c: Vector2i in g:
			if g[c].kind == "blocked":
				continue
			for n: Vector2i in Hex.NEIGHBOURS:
				var m: Vector2i = c + n
				if not g.has(m) or g[m].kind == "blocked":
					continue
				var rise: float = g[m].z - g[c].z
				var gap := absf(rise)
				if gap > 0.46 and gap < 0.89:
					bad_gaps.append("%s %s" % [id, c])
				var want := -1 if gap >= 0.89 else (2 if rise >= 0.29 else 1)
				if fight.step_cost(walker, c, m) != want:
					bad_steps.append("%s %s to %s" % [id, c, m])
		var first: Dictionary = people[0]
		var at: Vector2i = first.cell
		walker.cell = at
		var reach := fight._spread(walker, 1 << 19, Callable())
		for c: Vector2i in g:
			if g[c].kind != "blocked" and not reach.has(c):
				cut_off.append("%s %s" % [id, c])
		fight.units = people
	_check(bad_gaps.is_empty(), "on all 16 hills maps walkable neighbours are up to 0.45 apart or 0.9 and more %s" % [bad_gaps])
	_check(bad_steps.is_empty(), "every step costs 1, 2 going up 0.3 or more, and a gap of 0.9 or more can't be crossed either way %s" % [bad_steps.slice(0, 6)])
	_check(cut_off.is_empty(), "every walkable cell can be walked to from the party %s" % [cut_off.slice(0, 6)])
	for row: Array in [["snowy_peaks_shelf", [3, 4, 4]], ["volcanic_peaks_crater", [2, 3]], ["volcanic_peaks_ledge", [3, 3]]]:
		var found := _lifts(row[0], walker)
		_check(found == row[1], "%s: its lifts are %s moves, 2 each up and 1 each down, from lift_steps (found %s)" % [row[0], row[1], found])
	await _check_terraces(walker)
	await _check_lava(walker)
	await _check_flow()
	await _hills_shots()


## How many moves each of a map's lifts takes, from the art's long steps, checking the climb and the way down.
func _lifts(id: String, walker: Dictionary) -> Array:
	_load(id)
	var g := fight.grid
	var people := fight.units
	fight.units = []
	var ups := {}
	for c: Vector2i in fight.treads:
		for i in 6:
			var m: Vector2i = c + Hex.NEIGHBOURS[i]
			if fight.treads[c][0] & (1 << i) and g.has(m) and absf(g[m].z - g[c].z - 0.45) < 0.01:
				ups[[c, m]] = true
	# Each cell may be entered from several sides, so a lift's length is the longest climb from where its long steps start.
	var longest := func(self_call: Callable, c: Vector2i) -> int:
		var best := 0
		for up: Array in ups:
			if up[0] == c:
				if fight.step_cost(walker, up[0], up[1]) != 2 or fight.step_cost(walker, up[1], up[0]) != 1:
					return -100
				best = maxi(best, 1 + self_call.call(self_call, up[1]))
		return best
	var feet := []
	for up: Array in ups:
		if not ups.keys().any(func(o): return o[1] == up[0]):
			feet.append(up[0])
	var out := []
	var seen := {}
	for c: Vector2i in feet:
		var path := [c]
		var k := c
		while true:
			var next = null
			for up: Array in ups:
				if up[0] == k:
					next = up[1]
					break
			if next == null:
				break
			path.append(next)
			k = next
		if not seen.has(path[-2]):
			seen[path[-2]] = longest.call(longest, c)
	fight.units = people
	out = seen.values()
	out.sort()
	return out


## Monastery: herb cells walk, terrace walls of 0.9 only by a stair cell, and Climb from foot to head.
func _check_terraces(walker: Dictionary) -> void:
	for id: String in ["monastery_heights_climb", "monastery_heights_gardens", "monastery_heights_ridge", "monastery_heights_walled"]:
		_load(id)
		var g := fight.grid
		var people := fight.units
		fight.units = []
		var walls := 0
		var stairs := 0
		var herbs := 0
		for c: Vector2i in g:
			if g[c].kind == "brush":
				for n: Vector2i in Hex.NEIGHBOURS:
					if g.has(c + n) and g[c + n].kind != "blocked" and fight.step_cost(walker, c + n, c) > 0:
						herbs += 1
						break
			if g[c].kind == "blocked":
				continue
			var up := false
			var down := false
			for n: Vector2i in Hex.NEIGHBOURS:
				if not g.has(c + n) or g[c + n].kind == "blocked":
					continue
				var rise: float = g[c + n].z - g[c].z
				walls += 1 if rise >= 0.89 else 0
				up = up or absf(rise - 0.45) < 0.01
				down = down or absf(rise + 0.45) < 0.01
			stairs += 1 if up and down else 0
		var lows: Array = g.keys().filter(func(c): return g[c].kind != "blocked")
		lows.sort_custom(func(a, b): return g[a].z < g[b].z)
		walker.cell = lows[0]
		var came := fight._spread(walker, 1 << 19, Callable())
		var top: Vector2i = lows[-1]
		var moves := fight._path_to(walker, came, top).size()
		print("COMBAT TERRACES %s: %d herb cells walked onto, %d sides of 0.9 or more, %d cells 0.45 both ways; lowest cell to highest %d moves" % [id, herbs, walls, stairs, moves])
		_check(herbs == g.keys().filter(func(c): return g[c].kind == "brush").size(), "%s: herb rows can be walked onto" % id)
		fight.units = people
	await get_tree().process_frame


func _check_lava(walker: Dictionary) -> void:
	var id := "volcanic_peaks_fissures"
	_load(id)
	var g := fight.grid
	var lava: Array = g.keys().filter(func(c): return g[c].kind == "lava")
	_check(lava.size() == 14, "Fissures has 14 lava cells")
	var u: Dictionary = fight.units[0]
	var people := fight.units
	fight.units = []
	walker.cell = lava[0]
	var walks := 0
	for n: Vector2i in Hex.NEIGHBOURS:
		if g.has(lava[0] + n) and fight.step_cost(walker, lava[0] + n, lava[0]) > 0:
			walks += 1
	_check(walks > 0, "lava can be walked onto")
	# Of two ways that cost the same, the one without lava.
	var tried := 0
	var wrong := 0
	for l: Vector2i in lava:
		for a: Vector2i in Hex.NEIGHBOURS:
			var s: Vector2i = l + a
			if not g.has(s) or g[s].kind in ["blocked", "lava"]:
				continue
			for b: Vector2i in Hex.NEIGHBOURS:
				var t: Vector2i = l + b
				if t == s or Rules.hex_distance(s, t) != 2 or not g.has(t) or g[t].kind in ["blocked", "lava"]:
					continue
				for c: Vector2i in Hex.NEIGHBOURS:
					var m: Vector2i = s + c
					if m == l or Rules.hex_distance(m, t) != 1 or not g.has(m) or g[m].kind in ["blocked", "lava"]:
						continue
					if fight.step_cost(walker, s, m) + fight.step_cost(walker, m, t) == fight.step_cost(walker, s, l) + fight.step_cost(walker, l, t) and fight.step_cost(walker, s, m) > 0 and fight.step_cost(walker, m, t) > 0 and fight.step_cost(walker, s, l) > 0 and fight.step_cost(walker, l, t) > 0:
						walker.cell = s
						var path := fight._path_to(walker, fight._spread(walker, 4, Callable()), t)
						tried += 1
						wrong += 1 if path.any(func(k): return g[k].kind == "lava") else 0
	_check(tried > 0 and wrong == 0, "a path goes round lava when that costs no more (%d cases, %d through it)" % [tried, wrong])
	fight.units = people
	# Burns: each cell entered, stopping if it downs you, and the end of a turn.
	var beside := Vector2i.ZERO
	var strip: Array = []
	for l: Vector2i in lava:
		for k: Vector2i in lava:
			if Rules.hex_distance(l, k) == 1:
				strip = [l, k]
				break
		if not strip.is_empty():
			break
	for n: Vector2i in Hex.NEIGHBOURS:
		var s: Vector2i = strip[0] + n
		if g.has(s) and g[s].kind != "blocked" and g[s].kind != "lava":
			beside = s
			break
	for o in fight.units:
		o.cell = Vector2i(99, 99) if o != u else o.cell
	u.cell = beside
	u.hp = 20
	u.max_hp = 20
	fight.current = u
	await fight._walk(u, strip)
	_check(u.hp == 20 - 2 * Rules.LAVA_DAMAGE and u.cell == strip[1], "walking through two lava cells burns twice")
	u.hp = Rules.LAVA_DAMAGE
	u.cell = beside
	await fight._walk(u, strip)
	_check(u.down and u.cell == strip[0], "a burn that downs a walker stops them on that cell")
	u.down = false
	u.mini.get_node("body").quaternion = Quaternion.IDENTITY
	u.hp = 20
	u.cell = strip[1]
	var was_active := fight.active
	fight.active = false   # stops the phase after the party's turn ends
	await fight._enemy_phase()
	_check(u.hp == 20 - Rules.LAVA_DAMAGE, "ending the party's turn in lava burns")
	var e: Dictionary = fight.units.filter(func(o): return not o.ally)[0]
	for o in fight.units:
		if o != e and o != u:
			o.down = true
	u.cell = strip[1]
	u.hp = 99
	e.cell = strip[0]
	e.hp = 20
	fight.active = true
	await fight._enemy_phase()
	_check(e.hp == 20 - Rules.LAVA_DAMAGE, "a foe ending its turn in lava burns")
	fight.active = was_active
	fight.phase = "allies"
	fight.busy = false
	var giant := {foot = [Vector2i.ZERO, Vector2i(1, 0), Vector2i(0, 1)], cell = strip[0]}
	var refused := true
	fight.units = []
	for l: Vector2i in lava:
		for n: Vector2i in Hex.NEIGHBOURS:
			if g.has(l + n):
				refused = refused and fight.step_cost(giant, l + n, l) == -1
	fight.units = people
	_check(refused, "a giant won't step onto lava (PLACEHOLDER)")


## The moving surface: the art's UVs as handed off, and the field the bands run on, which grows going downhill and has no jumps where pieces meet.
func _check_flow() -> void:
	for row: Array in [["volcanic_peaks_fissures", -17.59], ["volcanic_peaks_crater", -9.82]]:
		var id: String = row[0]
		var key := "map_%s_lava_flow" % id
		var kit := Kit.meshes("res://art/combat_maps_hills.glb")
		var art: Mesh = kit[key]
		for k in art.get_surface_count():
			if art.surface_get_material(k).resource_name == "lava_flow":
				var v: PackedVector2Array = art.surface_get_arrays(k)[Mesh.ARRAY_TEX_UV]
				var lowest := INF
				for q: Vector2 in v:
					lowest = minf(lowest, q.y)
				if not CombatMap._flowed.has(key):
					_check(absf(lowest - row[1]) < 0.05, "%s: lava_flow's UVs are as handed off" % id)
		_load(id)
		await get_tree().process_frame
		var mesh: Mesh = kit[key]
		var surfaces := {}
		for k in mesh.get_surface_count():
			var m := mesh.surface_get_material(k)
			surfaces[m.resource_name] = m is ShaderMaterial
			if m.resource_name != "lava_flow":
				continue
			var data := mesh.surface_get_arrays(k)
			var verts: PackedVector3Array = data[Mesh.ARRAY_VERTEX]
			var field := PackedFloat32Array()
			for i in verts.size():
				field.append(CombatMap.flow_field(data, i))
			var start := 0
			var end := 0
			var jump := 0.0
			for i in verts.size():
				start = i if field[i] < field[start] else start
				end = i if field[i] > field[end] else end
				for j in i:
					if verts[i].distance_squared_to(verts[j]) < 0.04 * 0.04:
						jump = maxf(jump, absf(field[i] - field[j]))
			print("COMBAT FLOW %s: %.2f to %.2f m along; height %.2f at the crater, %.2f at the far end; the biggest jump where pieces meet %.3f m" % [id, field[start], field[end], verts[start].y, verts[end].y, jump])
			_check(verts[end].y < verts[start].y, "%s: metres along grow going downhill, so the bands run downstream" % id)
			_check(jump < 0.5, "%s: where pieces meet, the bands' field jumps at most a chevron's width, not the art's 3 to 5 m (biggest %.3f m)" % [id, jump])
		_check(surfaces.get("lava_flow", false), "%s: lava_flow has the moving material" % id)
		_check(surfaces.keys().any(func(n): return n != "lava_flow" and not surfaces[n]), "%s: its banks don't move" % id)


func _hills_shots() -> void:
	game.rig.focus = fight.open_area().get_center()
	await _wait(1.5)   # the burns' floating numbers
	for id: String in ["snowy_peaks_shelf", "monastery_heights_ridge", "monastery_heights_climb", "volcanic_peaks_fissures", "volcanic_peaks_crater"]:
		_load(id)
		var view := fight.opening()
		game.rig.frame(view.target, view.distance, 52.0)
		await _shot("hills_%s" % id)
	# The necks between lava cells, close, and each flow's cells together.
	if fight.hud:
		fight.hud.visible = false
	for row: Array in [["volcanic_peaks_crater", 11.0], ["volcanic_peaks_fissures", 15.0]]:
		_load(row[0])
		for u in fight.units:
			u.mini.visible = false
		var lava: Array = fight.grid.keys().filter(func(c): return fight.grid[c].kind == "lava")
		var middle := Vector3.ZERO
		for c: Vector2i in lava:
			middle += fight.cell_point(c) / lava.size()
		game.rig.focus = Vector2(422, 195)
		game.rig.frame(fight.global_position + middle, row[1], 58.0)
		await _shot("necks_%s" % row[0])
		game.rig.frame(fight.global_position + fight.cell_point(lava[lava.size() / 2]), 5.5, 58.0)
		await _shot("necks_%s_close" % row[0])
	game.rig.focus = fight.open_area().get_center()
	if fight.hud:
		fight.hud.visible = true
	# Move's highlights over a lift's treads, from both sides of the camera.
	_load("snowy_peaks_shelf")
	var u: Dictionary = fight.units[0]
	var low: Vector2i = fight.treads.keys()[0]
	u.cell = low
	u.mini.position = fight.cell_point(low)
	u.ap = Rules.AP
	fight.current = u
	fight.sel = "move"
	fight.phase = "allies"
	fight.visible = true
	fight._show_overlays()
	game.rig.frame(fight.global_position + fight.cell_point(low), 12.0, 52.0)
	await _shot("hills_lift_move")
	game.rig.yaw_deg = 180.0
	await _shot("hills_lift_move_turned")
	game.rig.yaw_deg = 0.0
	fight._clear_overlays()


## Fissures' cone, river and fall, without the panels.
func _lava_clip() -> void:
	await _wait(0.5)
	game.debug_fight("volcanic_peaks_fissures")
	await _wait(Rules.ZOOM_SECONDS * 2.0 + 0.5)
	game.fight.hud.visible = false
	game.rig.focus = Vector2(422, 195)
	var mesh: Mesh = Kit.meshes("res://art/combat_maps_hills.glb")["map_volcanic_peaks_fissures_lava_flow"]
	var f := game.fight
	for view: Array in [[2.6, 8.5, 40.0, 0.0], [10.0, 9.0, 48.0, 0.0], [17.2, 7.5, 26.0, 60.0]]:
		var at := Vector3.ZERO
		var best := INF
		for k in mesh.get_surface_count():
			if mesh.surface_get_material(k).resource_name == "lava_flow":
				var data := mesh.surface_get_arrays(k)
				var uv: PackedVector2Array = data[Mesh.ARRAY_TEX_UV]
				for i in uv.size():
					var off := absf(CombatMap.flow_field(data, i) - view[0])
					if off < best:
						best = off
						at = data[Mesh.ARRAY_VERTEX][i]
		game.rig.frame(f.global_position + at, view[1], view[2], view[3])
		await _wait(5.0)


## Is this unit's foot between the panels?
func _on_screen(u: Dictionary) -> bool:
	var at := game.rig.camera.unproject_position(fight.global_position + u.mini.position) * Vector2(844, 390) / game.get_viewport().get_visible_rect().size
	return fight.open_area().has_point(at)


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
	var lost_party := 0
	var lost_foes := 0
	var maps_with_foe := 0
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
		map_tris_of[id] = with_minis
		print("COMBAT MAP %s: %d cells, %d walkable; %d tris, %d with minis; build %.0f ms; camera %.1f m%s; hidden with the whole map in view %d, off screen %d" % [id,
			fight.grid.size(), cells.size(), fight.map_tris, with_minis, fight.map_build_ms, fight.open_distance,
			" (at the limit)" if fight.open_distance >= 34.0 else "", hidden, off])
		var view := fight.opening()
		game.rig.frame(view.target, view.distance, 52.0)
		var allies_in := fight.units.filter(func(u): return u.ally and _on_screen(u)).size()
		var foes_in := fight.units.filter(func(u): return not u.ally and _on_screen(u)).size()
		var foes := fight.units.size() - fight.units.filter(func(u): return u.ally).size()
		print("COMBAT OPENING %s: %.1f m; framed foes %d of %d; on screen %d allies, %d foes" % [id, view.distance, view.framed, foes, allies_in, foes_in])
		lost_party += 0 if allies_in == fight.units.size() - foes else 1
		lost_foes += 0 if foes_in >= view.framed else 1
		maps_with_foe += 1 if view.framed > 0 else 0
	print("COMBAT worst map with minis: %d triangles" % worst_tris)
	_check(lost_party == 0, "every map opens with the whole party between the panels (%d don't)" % lost_party)
	_check(lost_foes == 0, "every foe an opening frames is between the panels (%d maps lose one)" % lost_foes)
	print("COMBAT openings with a foe framed: %d of %d" % [maps_with_foe, ids.size()])


## Back faces are culled on the map kits, with webs shown from both sides.
func _check_facing() -> void:
	_load("dark_wood_thorns")
	var cells := Kit.meshes("res://art/combat_cells.glb")
	var webs := 0
	var culled := 0
	for mesh: Mesh in cells.values():
		for k in mesh.get_surface_count():
			var m := mesh.surface_get_material(k) as BaseMaterial3D
			if m and m.resource_name == "web":
				webs += 1 if m.cull_mode == BaseMaterial3D.CULL_DISABLED else 0
				culled += 1 if m.cull_mode != BaseMaterial3D.CULL_DISABLED else 0
			elif m:
				culled += 0 if m.cull_mode == BaseMaterial3D.CULL_BACK else 1
	_check(webs > 0 and culled == 0, "webs show from both sides (%d surfaces), and everything else in the kit culls back faces" % webs)
	await get_tree().process_frame


func _perf_heaviest() -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	var hills := CombatMap.all().keys().filter(func(id): return CombatMap.all()[id].set == "combat_maps_hills")
	hills.sort_custom(func(a, b): return map_tris_of.get(a, 0) > map_tris_of.get(b, 0))
	var list := HEAVIEST + hills.slice(0, 3)
	for id: String in ["volcanic_peaks_fissures", "volcanic_peaks_crater"]:
		if not id in list:
			list.append(id)
	for id: String in list:
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
