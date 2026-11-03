class_name RiverCheck
extends Node
## Checks the river kit (tiles v53) in the game (`-- --rivercheck`, add `--shots` for screens/river_*.png): water styles,
## props and landmarks, routes, and a party crossing by check and by raft. Prints RIVER OK / RIVER FAIL lines, then
## RIVER DONE. A test aid only.

const KITS := ["delta", "great_lake", "rapids", "still_waters"]

var game: Game
var shots := false
var failed := 0
var checks := 0


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("RIVER %s: %s" % ["OK" if ok else "FAIL", what])
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
		game.get_viewport().get_texture().get_image().save_png(dir.path_join("river_%s.png" % name))
		print("SAVED river_%s" % name)


func _region(variant: String) -> Dictionary:
	for g in game.regions:
		if g.variant == variant:
			return g
	return {}


func _pieces(t: Vector2i) -> Array:
	return game.map.tile_node(t).get_children().filter(func(c): return c is MeshInstance3D and c.has_meta("piece")).map(func(c): return c.get_meta("piece"))


func _run() -> void:
	game.spawn_forest_regions()
	await _wait(1.0)
	var map := game.map
	if "--nobridge" in OS.get_cmdline_user_args():
		await _no_bridge(map)
		get_tree().quit()
		return
	_check_regions(map)
	_check_graphs(map)
	_check_fences(map)
	await _pictures(map)
	await _crossings(map)
	await _popups(map)
	await _perf(map)
	await _ledge_on_water(map)
	print("RIVER DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _check_regions(map: MapBoard) -> void:
	for v in KITS:
		var g := _region(v)
		_check(not g.is_empty(), "%s: spawned" % v)
		if g.is_empty():
			continue
		var lm: Vector2i = g.landmark_tile
		var w: Dictionary = map.water_shapes[lm]
		_check(map.terrains[lm] == Variants.LANDMARK_OF[v], "%s: its landmark stands on %s" % [v, lm])
		if v in ["delta", "still_waters"]:
			_check(w.mask.has(false), "%s: the landmark has a land neighbour" % v)
		if v == "rapids":
			_check(not w.get("bridge", {}).is_empty(), "rapids: the Troll Bridge has a spot")
			_check("trollbridge_centre" in _pieces(lm), "rapids: the Troll Bridge piece is placed")
		_check(Variants.LANDMARK_OF[v] + "_centre" in _pieces(lm), "%s: landmark piece placed" % v)
		var props := 0
		for t: Vector2i in g.tiles:
			props += map.water_shapes[t].props.size()
		_check(v == "delta" or props > 0, "%s: %d props from water.py" % [v, props])
		_check(map.get_node("water").get_node_or_null("water_surface_" + v) != null or v == "delta", "%s: its own water material" % v)
	var port: Vector2i = _region("delta").landmark_tile
	var pw: Dictionary = map.water_shapes[port]
	var turn: int = map.landmark_turns[port]
	var behind := Hex.tile_position(port.x, port.y) + Water.turned(Vector2(-1.5, 0), turn)
	_check(not map.wet_at(behind), "port: no water behind the quay")
	_check(not pw.walls.is_empty(), "port: %d stone walls" % pw.walls.size())
	_check(map.tile_node(port).get_children().any(func(c): return c.name == "town_smoke"), "port: smoke at the tavern")
	_check(map.get_node("water").get_child_count() > 0, "water drawn")
	var lairless: Array = _region("rapids").tiles.filter(func(t): return map.terrains[t] == "rapids")
	_check(lairless.all(func(t): return not Water.raft_can_enter(map.terrains[t])), "rapids: no raft can enter")


func _check_graphs(map: MapBoard) -> void:
	var edges := 0
	var missing := 0
	for t: Vector2i in map.water_shapes:
		var g := map.path_graph(t)
		for i in 6:
			edges += 1
			if not g.edge_node.has(i) or g.route(g.edge_node[i], g.stand).is_empty():
				missing += 1
				print("  no way in from edge %d of %s (%s)" % [i, t, map.terrains[t]])
	_check(missing == 0, "water tiles: all %d edges have a way to the stopping point" % edges)
	# What's free and what isn't.
	for spec in [["riverport", false], ["meditationrock", false], ["serpentlair", true]]:
		var t := _named(map, spec[0])
		var w: Dictionary = map.water_shapes[t]
		for i in 6:
			if not w.mask[i] and map.wet_between(t, i, -1) != spec[1]:
				_check(false, "%s: from land edge %d, wet is %s" % [spec[0], i, not spec[1]])
		_check(true, "%s: from land %s" % [spec[0], "needs a check or raft" if spec[1] else "is free"])
	var lm := _named(map, "trollbridge")
	var bridge: Dictionary = map.water_shapes[lm].bridge
	_check(bridge.routes.keys().all(func(e): return not map.wet_between(lm, e, -1)), "Troll Bridge: walked with no check from its land edges")
	var a: int = bridge.routes.keys()[0]
	var b: int = bridge.routes.keys()[-1]
	_check(not map.wet_between(lm, a, b), "Troll Bridge: over it, edge %d to %d, stays dry" % [a, b])


func _named(map: MapBoard, name: String) -> Vector2i:
	for t: Vector2i in map.terrains:
		if map.terrains[t] == name:
			return t
	return Vector2i(99, 99)


func _check_fences(map: MapBoard) -> void:
	var bad := 0
	for t: Vector2i in map.gates:
		for i: int in map.gates[t]:
			if Variants.is_water(map.terrains.get(t + Hex.NEIGHBOURS[i])):
				bad += 1
	_check(bad == 0, "no fence gate faces water")


func _pictures(map: MapBoard) -> void:
	for v in KITS:
		var lm: Vector2i = _region(v).landmark_tile
		var at := Hex.to3(Hex.tile_position(lm.x, lm.y))
		game.rig.frame(at, 34.0, 50.0)
		await _wait(0.5)
		await _shot("1%d_%s_map" % [KITS.find(v), v])
		game.rig.frame(at, 15.0, 40.0)
		await _wait(0.3)
		await _shot("2%d_%s_landmark" % [KITS.find(v), v])
	var t0: Vector2i = Game.DEBUG_RIVER_T0[3]
	game.rig.frame(Hex.to3(Hex.tile_position(t0.x, t0.y)), 34.0, 50.0)
	await _wait(0.4)
	await _shot("30_tier0")


## The land tile beside t and the edge of t it comes in by.
func _land_beside(map: MapBoard, t: Vector2i) -> Array:
	for i in 6:
		var n: Vector2i = t + Hex.NEIGHBOURS[i]
		var name = map.terrains.get(n)
		if name != null and not Variants.is_water(name) and map.edge_open(n, t) and not map.gates.has(n):
			return [n, i]
	return []


func _set_party(t: Vector2i) -> void:
	game.party_tile = t
	game.party_node.place_at(t)
	game.rig.frame(game.party_node.centre(), 18.0, 45.0)
	await _wait(0.2)


## Walks a route and watches: checks fired, lowest mini, raft showing, whether anyone rode on its seats.
func _walk(goal: Vector2i) -> Dictionary:
	var w := game.party_node
	var out := {checks = 0, low = 0.0, raft = false, shot = false}
	var count := func(): out.checks += 1
	w.waded.connect(count)
	game.walk_to(goal)
	while game.busy:
		await get_tree().process_frame
		for m in w.members:
			out.low = minf(out.low, m.node.position.y)
		if w._raft and w._raft.visible:
			out.raft = true
	w.waded.disconnect(count)
	await _wait(Rules.SETTLE_SECONDS)
	return out


func _hp() -> Array:
	return game.party.map(func(m): return m.hp)


## Across a tile with land each side, or onto the tile.
func _crossings(map: MapBoard) -> void:
	var w := game.party_node
	var river: Vector2i = Game.DEBUG_RIVER_T0[3]
	var side := _land_beside(map, river)
	_check(not side.is_empty(), "tier 0 river has land beside it")
	if side.is_empty():
		return
	game.debug_fail_crossing = false
	var hp := _hp()
	await _set_party(side[0])
	var r := await _walk(river)
	_check(r.checks == 1, "by check: the check fires once (%d)" % r.checks)
	_check(r.low < -Rules.WADE_DEPTH * 0.6, "by check: minis wade at waist height (lowest %.2f)" % r.low)
	game.rig.frame(w.centre(), 14.0, 40.0)
	await _wait(0.3)
	await _shot("40_wading")
	_check(w.centre().y < 0.0, "by check: stopped on the water, the hero stays in it")
	# A failed one.
	game.debug_fail_crossing = true
	await _set_party(side[0])
	hp = _hp()
	r = await _walk(river)
	var after := _hp()
	var lost := true
	for k in hp.size():
		lost = lost and after[k] == maxi(mini(hp[k], 1), hp[k] - Rules.CROSS_FAIL_HP)
	_check(lost, "a fail: everyone loses %d HP (%s to %s), and it still crosses" % [Rules.CROSS_FAIL_HP, hp, after])
	_check(game.party_tile == river, "a fail: the party got there")
	for m in game.party:
		m.hp = 1
	await _set_party(side[0])
	r = await _walk(river)
	_check(game.party.all(func(m): return m.hp >= 1), "a fail never downs anyone")
	for m in game.party:
		m.hp = m.max_hp
	game.debug_fail_crossing = false
	# Free ways.
	for name in ["riverport", "meditationrock"]:
		var t := _named(map, name)
		var s := _land_beside(map, t)
		_check(not s.is_empty(), "%s has land beside it" % name)
		if s.is_empty():
			continue
		await _set_party(s[0])
		r = await _walk(t)
		_check(r.checks == 0, "%s: reached on foot with no check" % name)
		var hero := Vector2(w.centre().x, -w.centre().z)
		_check(hero.distance_to(map.path_graph(t).nodes[map.path_graph(t).stand]) < 0.3, "%s: stops at its stopping point" % name)
		_check(r.low > -0.1, "%s: nobody got wet (lowest %.2f)" % [name, r.low])
		game.rig.frame(w.centre(), 14.0, 40.0)
		await _wait(0.3)
		await _shot("5%s" % name)
	w.has_raft = true
	# The Troll Bridge.
	var troll := _named(map, "trollbridge")
	var ts := []
	for e in map.water_shapes[troll].bridge.routes:
		if map.terrains.has(troll + Hex.NEIGHBOURS[e]) and map.edge_open(troll + Hex.NEIGHBOURS[e], troll):
			ts.append(e)
	if not ts.is_empty():
		await _set_party(troll + Hex.NEIGHBOURS[ts[0]])
		var was := w.has_raft
		w.has_raft = false
		r = await _walk(troll)
		w.has_raft = was
		_check(r.checks == 0, "Troll Bridge: reached over the bridge with no check")
		game.rig.frame(w.centre(), 14.0, 40.0)
		await _wait(0.3)
		await _shot("60_on_the_troll_bridge")
		_check(w.centre().y > 1.0, "Troll Bridge: the party stands up on the hump (%.2f)" % w.centre().y)
	# The Lair: only by check or raft.
	var lair := _named(map, "serpentlair")
	await _set_party(_lake_land(map, lair))
	w.has_raft = false
	r = await _walk(lair)
	_check(r.checks == 1, "the Lair: by check, one check")
	# On the raft.
	w.has_raft = true
	await _set_party(side[0])
	hp = _hp()
	game.debug_fail_crossing = true
	var seated := await _raft_walk(river)
	_check(seated.raft, "by raft: the raft shows")
	_check(seated.seated, "by raft: everyone rides on its seats")
	_check(seated.checks == 0, "by raft: no check")
	_check(_hp() == hp, "by raft: no HP lost")
	_check(w._on_raft and w._raft.visible, "by raft: stopped on the water, still on it")
	var off := await _walk(side[0])
	_check(not w._raft.visible, "by raft: hidden at the far landing")
	_check(off.checks == 0, "by raft: no check off it")
	# Rapids: no raft on them, the check still allowed.
	var rapid: Vector2i = Vector2i(99, 99)
	for t: Vector2i in _region("rapids").tiles:
		if map.terrains[t] == "rapids" and not map.water_shapes[t].has("bridge") and not _land_beside(map, t).is_empty():
			rapid = t
	if rapid != Vector2i(99, 99):
		await _set_party(_land_beside(map, rapid)[0])
		r = await _walk(rapid)
		_check(r.checks == 1 and not r.raft, "rapids with no bridge: no raft, one check (%d)" % r.checks)
	game.debug_fail_crossing = false
	w.has_raft = false


func _lake_land(map: MapBoard, lair: Vector2i) -> Vector2i:
	var s := _land_beside(map, lair)
	if not s.is_empty():
		return s[0]
	var best := Vector2i(99, 99)
	for t: Vector2i in _region("great_lake").tiles:
		var b := _land_beside(map, t)
		if not b.is_empty() and Rules.hex_distance(t, lair) < Rules.hex_distance(best, lair):
			best = b[0]
	return best


func _raft_walk(goal: Vector2i) -> Dictionary:
	var w := game.party_node
	var out := {raft = false, seated = false, checks = 0}
	var count := func(): out.checks += 1
	w.waded.connect(count)
	game.walk_to(goal)
	var shot := false
	while game.busy:
		await get_tree().process_frame
		if w._raft and w._raft.visible:
			out.raft = true
		if w._riding and w._ride_t > Rules.RAFT_SETTLE:
			var seats: Array = Kit.path_data("raft").effects
			var ok := true
			for i in w.members.size():
				var seat: Array = seats[i].at
				var want := Vector2(seat[0], -seat[2]).rotated(w._raft.rotation.y) + Vector2(w._raft.position.x, -w._raft.position.z)
				var at := Vector2(w.members[i].node.position.x, -w.members[i].node.position.z)
				ok = ok and at.distance_to(want) < 0.25
			out.seated = out.seated or ok
			if not shot:
				shot = true
				game.rig.frame(w.centre(), 14.0, 40.0)
				await _shot("70_on_the_raft")
	w.waded.disconnect(count)
	await _wait(Rules.SETTLE_SECONDS)
	return out


## What a rapids region looks like when no tile fits a Troll Bridge (a question for Ethan): `-- --rivercheck --nobridge --shots`.
func _no_bridge(map: MapBoard) -> void:
	var g := _region("rapids")
	var fits: Array = g.tiles.filter(func(c): return game.region_look(g, c) == "trollbridge")
	print("RIVER NOBRIDGE: %d tiles, %d show a Troll Bridge, region %s, landmark %s" % [g.tiles.size(), fits.size(), g.name, g.landmark])
	var at := Hex.to3(Hex.tile_position(g.landmark_tile.x, g.landmark_tile.y))
	game.rig.frame(at, 34.0, 50.0)
	await _wait(0.6)
	await _shot("no_bridge_map")
	game.rig.frame(at, 15.0, 40.0)
	await _wait(0.4)
	await _shot("no_bridge_tile")


## The pop-ups themselves, as a player meets them: the prompt, the flip with a chime-in, and the River Port's counter.
func _popups(map: MapBoard) -> void:
	var w := game.party_node
	var check := game.hud.check
	var river: Vector2i = Game.DEBUG_RIVER_T0[3]
	var side := _land_beside(map, river)
	game.debug_auto_cross = false
	w.has_raft = false
	for m in game.party:
		m.hp = m.max_hp
	# Onto the water there's no way round: Cross or Back.
	await _set_party(side[0])
	game.walk_to(river)
	await _wait(0.2)
	_check(check.visible and game.busy, "a route needing a check asks first")
	_check(game.party_tile == side[0], "nothing is committed: the party hasn't moved")
	await _shot("80_prompt")
	var labels := _buttons(check)
	_check(labels.has("Back") and labels.has("Cross"), "onto water, no way round: Back and Cross (%s)" % str(labels))
	_press(check, "Back")
	await _wait(0.1)
	_check(not check.visible and not game.busy and game.party_tile == side[0], "Back: stays put, free to act")
	# A near miss, saved.
	game.debug_near_miss = 1
	game.walk_to(river)
	await _wait(0.1)
	_press(check, "Cross")
	while not w.holding:
		await get_tree().process_frame
	var y := w.centre()
	await _wait(CheckPopup.COIN_STEP * game._cross_view().coins + CheckPopup.CHIME_WAIT + 0.2)
	await _shot("81_chime_in")
	await _wait(CheckPopup.CHIME_FLIP + 0.1)
	await _shot("82_chime_saved")
	_check(w.centre().is_equal_approx(y), "the party holds at the water's edge while the coins flip")
	var hp := _hp()
	_press(check, "Continue")
	while game.busy:
		await get_tree().process_frame
	_check(_hp() == hp and game.party_tile == river, "saved by the chime-in: no HP lost, and across")
	# A fail: no helper's coin at 0 heads; HP goes, and they still cross.
	game.debug_near_miss = 0
	game.debug_fail_crossing = true
	await _set_party(side[0])
	game.walk_to(river)
	await _wait(0.1)
	_press(check, "Cross")
	while not w.holding:
		await get_tree().process_frame
	await _wait(CheckPopup.COIN_STEP * game._cross_view().coins + CheckPopup.CHIME_WAIT + 0.2)
	await _shot("83_failed")
	_press(check, "Continue")
	while game.busy:
		await get_tree().process_frame
	_check(_hp() != hp and game.party_tile == river, "failed: HP lost, and across")
	game.debug_fail_crossing = false
	for m in game.party:
		m.hp = m.max_hp
	# A near miss with no one to help: with Chelmsford gone from the party there's no chime-in.
	var c: Dictionary = game.party.pop_at(2)
	_check(game._chime_helper("Athletics").is_empty(), "no one proficient in the party: no helper")
	game.party.insert(2, c)
	_check(game._chime_helper("Athletics").name == "Chelmsford", "Chelmsford is the party's Athletics helper")
	# Round the water: a tier 0 river tile with land beside it and a dry way past.
	var way := await _way_round(map)
	_check(not way.is_empty(), "there's a crossing with a dry way round")
	if not way.is_empty():
		var over: Array[Vector2i] = [way[1], way[2]]
		game._ask_crossing(way[2], over)
		await _wait(0.1)
		_check(check.visible and _buttons(check).has("Walk round"), "with a dry way: Walk round is offered")
		await _shot("84_walk_round")
		var low := 0.0
		_press(check, "Walk round")
		while game.busy:
			await get_tree().process_frame
			low = minf(low, w.members[0].node.position.y)
		_check(game.party_tile == way[2] and low > -0.1, "walking round: there, and dry (lowest %.2f)" % low)
	# Stopped in water: the nearest bank is free, a farther one isn't (design/02 -> Crossing water).
	await _set_party(side[0])
	game.debug_auto_cross = true
	await _walk(river)
	game.debug_auto_cross = false
	var near_bank := _nearest_bank(map, river)
	var hurt := _hp()
	var wades := {n = 0}
	var tally := func(): wades.n += 1
	w.waded.connect(tally)
	game.walk_to(near_bank)
	await _wait(0.1)
	_check(not check.visible and game.busy, "stopped in water: no prompt to the nearest bank")
	while game.busy:
		await get_tree().process_frame
	await _wait(Rules.SETTLE_SECONDS)
	w.waded.disconnect(tally)
	_check(wades.n == 0 and _hp() == hurt and game.party_tile == near_bank, "stopped in water: to the nearest bank, no check (%d)" % wades.n)
	var lake := Vector2i(99, 99)
	for t: Vector2i in _region("great_lake").tiles:
		if map.terrains[t] == "great_lake":
			await _set_party(t)
			if game._bank_limit() > 0.0:
				lake = t
				break
	await _set_party(lake)
	var limit := game._bank_limit()
	var far := _farthest_bank(map, lake)
	var far_wet: float = w.wet_start(w.route_preview(game.path_to(far))) if far != Vector2i(99, 99) else -1.0
	_check(limit > 0.0, "mid-lake: the nearest bank is %.1f m away" % limit)
	if far_wet > limit and far_wet < INF:
		game.walk_to(far)
		await _wait(0.1)
		_check(check.visible, "mid-lake: a farther bank (%.1f m) still asks" % far_wet)
		await _shot("88_far_bank")
		_press(check, "Walk round" if _buttons(check).has("Walk round") else "Back")
		while game.busy:
			await get_tree().process_frame
		await _wait(Rules.SETTLE_SECONDS)
	else:
		_check(false, "mid-lake: no farther bank to test (%.1f against %.1f)" % [far_wet, limit])
	# The raft: bought at the counter, then no prompt; rapids still ask.
	var port := _named(map, "riverport")
	await _set_party(_land_beside(map, port)[0])
	game.walk_to(port)
	var waited := 0.0
	while not game.hud.shop.visible and waited < 60.0:
		await get_tree().process_frame
		waited += get_process_delta_time()
	_check(game.hud.shop.visible, "reaching the River Port opens its counter (busy %s, at %s, port %s, prompt %s, encounter %s)" % [game.busy, game.party_tile, port, check.visible, game.hud.encounter_open()])
	await _wait(0.3)
	await _shot("85_counter")
	game.hud.shop._toggle_pop()
	await _wait(0.1)
	await _shot("86_counter_raft")
	_check(not w.has_raft, "looking doesn't buy")
	game.hud.shop._buy()
	_check(w.has_raft, "Buy: the party has the raft")
	await _wait(0.4)
	await _shot("87_bought")
	await _wait(0.9)
	game.hud.shop.close()
	await _wait(0.1)
	_check(not game.busy and not game.hud.shop.visible, "Back: the map again")
	game.tap(game.party_tile)
	_check(not game.hud.shop.visible, "sold out: the counter doesn't open again")
	await _set_party(side[0])
	game.walk_to(river)
	await _wait(0.1)
	_check(not check.visible and game.busy, "with a raft: no prompt")
	while game.busy:
		await get_tree().process_frame
	await _wait(Rules.SETTLE_SECONDS)
	var rapid := Vector2i(99, 99)
	for t: Vector2i in _region("rapids").tiles:
		if map.terrains[t] == "rapids" and not map.water_shapes[t].has("bridge") and not _land_beside(map, t).is_empty():
			rapid = t
	if rapid != Vector2i(99, 99):
		await _set_party(_land_beside(map, rapid)[0])
		game.walk_to(rapid)
		await _wait(0.1)
		_check(check.visible, "rapids ask even with a raft")
		_press(check, "Back")
		await _wait(0.1)
	w.has_raft = false
	game.debug_auto_cross = true


func _buttons(c: Control) -> Array:
	var out := []
	for n in c.find_children("*", "Control", true, false):
		if n is Button or n is TagButton:
			out.append(n.text)
	return out


func _press(c: Control, label: String) -> void:
	for n in c.find_children("*", "Control", true, false):
		if (n is Button or n is TagButton) and n.text == label:
			n.pressed.emit()
			return
	_check(false, "no %s button" % label)


## The land beside this water tile that its party reaches with the shortest wade.
func _nearest_bank(map: MapBoard, t: Vector2i) -> Vector2i:
	var best := Vector2i(99, 99)
	var least := INF
	for n in Hex.NEIGHBOURS:
		var c: Vector2i = t + n
		if map.terrains.has(c) and not Variants.is_water(map.terrains[c]):
			var path := game.path_to(c)
			var wet := game.party_node.wet_start(game.party_node.route_preview(path)) if not path.is_empty() else INF
			if wet >= 0.0 and wet < least:
				least = wet
				best = c
	return best


## The lake shore land that takes the longest wade from here and does reach land.
func _farthest_bank(map: MapBoard, t: Vector2i) -> Vector2i:
	var best := Vector2i(99, 99)
	var most := -1.0
	for w_tile: Vector2i in _region("great_lake").tiles:
		for n in Hex.NEIGHBOURS:
			var c: Vector2i = w_tile + n
			if map.terrains.has(c) and not Variants.is_water(map.terrains[c]):
				var path := game.path_to(c)
				var wet := game.party_node.wet_start(game.party_node.route_preview(path)) if not path.is_empty() else -1.0
				if wet > most and wet < INF:
					most = wet
					best = c
	return best


## A way over a tier 0 river tile between two land tiles, with a dry way between them too: [from, river, to].
func _way_round(map: MapBoard) -> Array:
	for r: Vector2i in Game.DEBUG_RIVER_T0:
		for x in Hex.NEIGHBOURS:
			for y in Hex.NEIGHBOURS:
				var a: Vector2i = r + x
				var b: Vector2i = r + y
				if a == b or not map.terrains.has(a) or not map.terrains.has(b) or Variants.is_water(map.terrains[a]) or Variants.is_water(map.terrains[b]):
					continue
				if not map.edge_open(a, r) or not map.edge_open(r, b):
					continue
				await _set_party(a)
				var over: Array[Vector2i] = [r, b]
				var dry := game.path_to(b, true)
				if game._needs_check(over) and not dry.is_empty() and not game._needs_check(dry):
					return [a, r, b]
	return []


## Design/02 -> Raised hills regions and water: a region ringed by water has a ledge whose foot opens onto it.
func _ledge_on_water(map: MapBoard) -> void:
	var g := _region("snowy_peaks")
	var changes := {}
	for t: Vector2i in g.tiles:
		for n in Hex.NEIGHBOURS:
			if not g.tiles.has(t + n) and map.terrains.has(t + n):
				changes[t + n] = "river"
	map.retile(changes)
	await _wait(0.3)
	var foot = null
	var top = null
	for c in map.climbs:
		if g.tiles.has(c[0]):
			var f: Vector2i = Cliffs.beside(c[0], c[1] - 1)
			if Variants.is_water(map.terrains.get(f)):
				foot = f
				top = c[0]
	_check(foot != null, "a raised region ringed by water has a ledge with its foot on the water")
	if foot == null:
		return
	_check(not Cliffs.ledge_tops(map.climbs).is_empty() and not map.ridge_wall(top, 0, 3), "no ridges where a ledge comes out")
	_check(not _pieces(top).any(func(n): return "_ridge_" in n), "no ridge pieces on the ledge's tile")
	game.party_tile = foot
	game.party_node.place_at(foot)
	await _wait(0.2)
	var r := await _walk(top)
	_check(game.party_tile == top and game.party_node.centre().y > Variants.RAISE - 0.5, "up the ledge from the water (height %.2f)" % game.party_node.centre().y)
	r = await _walk(foot)
	_check(game.party_tile == foot and r.checks >= 1, "down it into the water: %d check" % r.checks)


func _perf(map: MapBoard) -> void:
	for v in KITS:
		var lm: Vector2i = _region(v).landmark_tile
		game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y)), 26.0, 50.0)
		await _wait(0.8)
		print("RIVER PERF %s, opening zoom: draw calls %d, triangles %d" % [v, Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
				Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)])
