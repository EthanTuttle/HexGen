class_name Demo
extends Node
## Plays one full loop by itself, through the same calls a player's clicks make, for recordings and
## screenshots: place cards (finishing a region), walk to an encounter, fight it, see the result, return
## with the hand refilled. Run with `-- --demo` (add `--shots` to save screens/loop_*.png).
## `-- --demo=variants` instead records regions finishing and turning into their tier 1 variants: it stages
## the hand (5 forest, then 5 hills, then 5 plains) and says so on screen; placement still follows the rules.
## It's a test driver, not game AI: it plays simply and never cheats the rules, except that if no
## encounter has spawned once the hand runs low it adds one so the loop can go on (said on screen).

var game: Game
var shots := false
var _n := 0
var _taken := {}
var _prefix := "loop"


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	if "--demo=variants" in OS.get_cmdline_user_args():
		_variants.call_deferred()
	elif "--demo=walk" in OS.get_cmdline_user_args():
		_walk.call_deferred()
	elif "--demo=round" in OS.get_cmdline_user_args():
		_round.call_deferred()
	elif "--demo=hill" in OS.get_cmdline_user_args():
		_hill.call_deferred()
	elif "--demo=day" in OS.get_cmdline_user_args():
		_day.call_deferred()
	else:
		_run.call_deferred()


## Places one card from the hand (the best slot for it), waiting out any region transition first.
func _place(i: int, pause: float) -> void:
	while game.busy:
		await _wait(0.1)
	game.hold(i)
	await _wait(pause)
	game.try_place(_best_slot(game.deck.hand[i]))
	await _wait(pause)
	while game.busy:
		await _wait(0.1)


## The walk recording (How the party moves): a staged strip of land from the camp eastward, plains, a hill,
## plains, a river crossing (a ford), then sand; the party walks it in one go with the camera close behind,
## then stands a while (settling, looking around, an idle look). The map is staged and says so on screen.
func _walk() -> void:
	_prefix = "walk"
	var strip := {Vector2i(1, 0): "plains", Vector2i(1, -1): "plains", Vector2i(0, 1): "plains",
		Vector2i(2, 0): "hills", Vector2i(3, 0): "plains", Vector2i(3, -1): "plains", Vector2i(2, 1): "plains",
		Vector2i(4, -1): "river", Vector2i(4, 0): "river", Vector2i(3, 1): "river",
		Vector2i(5, 0): "desert", Vector2i(5, -1): "desert", Vector2i(6, 0): "desert", Vector2i(4, 1): "plains"}
	game.map.retile(strip)
	for t in strip:
		game.order[t] = game.order.size()
	game.toast("(demo) Staged map: plains, a hill, a ford and sand.", true)
	game.rig.frame(game.party_node.centre(), 30.0, 50.0)
	await _wait(2.5)
	await _shot("start")
	var goal := Vector2i(6, 0)
	game.walk_to(goal)
	var k := 0
	while game.busy:
		await _wait(0.1)
		k += 1
		if k % 15 == 0:
			await _shot("step%02d" % (k / 15))
	await _wait(7.0)
	await _shot("arrived")
	print("DEMO DONE")
	if shots or "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## Walking round the mountains (How the party moves: round peaks and mountains, not over them): a staged
## strip with a lone hill, then a group of four hills tiles (mountains on their shared edges and corners).
## The party walks onto the lone hill and stands there, then on across the group. Prints how much of each
## route still touches a mountain (should be none).
func _round() -> void:
	_prefix = "round"
	var strip := {Vector2i(1, 0): "plains", Vector2i(2, 0): "hills", Vector2i(3, 0): "plains",
		Vector2i(4, 0): "hills", Vector2i(5, 0): "hills", Vector2i(4, 1): "hills", Vector2i(3, 1): "hills",
		Vector2i(6, 0): "plains", Vector2i(1, -1): "plains", Vector2i(2, -1): "plains", Vector2i(0, 1): "plains",
		Vector2i(5, -1): "plains", Vector2i(6, -1): "plains"}
	game.map.retile(strip)
	for t in strip:
		game.order[t] = game.order.size()
	game.toast("(demo) Staged map: a lone hill, then joined hills.", true)
	await _wait(1.0)
	var k := 0
	for goal in [Vector2i(2, 0), Vector2i(6, 0)]:
		game.rig.frame(game.party_node.centre(), 30.0, 50.0)
		await _wait(1.5)
		await _shot("before_%d_%d" % [goal.x, goal.y])
		game.walk_to(goal)
		await _wait(0.2)
		var walker := game.party_node
		var touching := 0
		for p in walker._path:
			if walker._on_mountain(p):
				touching += 1
		var near := 0
		for p in walker._path:
			if walker.blocked(p):
				near += 1
		print("ROUTE to %s: %d points, %d on a mountain, %d within clearance, %.1f m" % [goal, walker._path.size(), touching, near, walker._len[-1]])
		if shots:
			_trace(walker._path)
		var probe := _probe()
		while game.busy:
			await _wait(0.1)
			k += 1
			if k % 12 == 0:
				await _shot("step%02d" % (k / 12))
		await _wait(3.0)
		probe.call(false)
		await _shot("arrived_%d_%d" % [goal.x, goal.y])
	# From above, with both routes traced (red dots, stills only: a test aid, not a look).
	game.rig.frame(Hex.to3(Hex.tile_position(3, 0)), 75.0, 89.0)
	await _wait(1.0)
	await _shot("routes_from_above")
	print("DEMO DONE")
	if shots or "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## Measures, every frame until called with false, how far any mini's base rim (tilted and waddling) dips below
## the ground and how often a mini's own spot is on a mountain; prints both when stopped.
func _probe() -> Callable:
	var walker := game.party_node
	var worst := [0.0, 0, 0]   # deepest dip (m), frames with a mini on a mountain, frames
	var tick := func() -> void:
		worst[2] += 1
		for m in walker.members:
			var body: Node3D = m.body
			var on := false
			for k in 12:   # the hex base's corners and the middles of its sides
				var r: float = m.radius if k % 2 == 0 else m.radius * 0.866
				var rim: Vector3 = body.global_transform * (Vector3.RIGHT.rotated(Vector3.UP, k * TAU / 12.0) * r)
				var plan := Vector2(rim.x, -rim.z)
				if not walker.in_water(plan):
					worst[0] = maxf(worst[0], walker.ground(plan) - rim.y)
				on = on or walker._on_mountain(plan)
			if on:
				worst[1] += 1
	get_tree().process_frame.connect(tick)
	return func(_go: bool) -> void:
		get_tree().process_frame.disconnect(tick)
		print("BASES: deepest rim below ground %.3f m; a base on a mountain in %d of %d frames"
				% [worst[0], worst[1], worst[2]])


## The close-up of the party crossing a hill (each base tilted flat on the slope): the walk demo's staged strip,
## from the camp over the lone hill to the plains beyond, with the camera low and close.
func _hill() -> void:
	_prefix = "hill"
	var strip := {Vector2i(1, 0): "plains", Vector2i(1, -1): "plains", Vector2i(0, 1): "plains",
		Vector2i(2, 0): "hills", Vector2i(3, 0): "plains", Vector2i(3, -1): "plains", Vector2i(2, 1): "plains",
		Vector2i(2, -1): "plains", Vector2i(4, 0): "plains"}
	game.map.retile(strip)
	for t in strip:
		game.order[t] = game.order.size()
	game.toast("(demo) Staged map: a lone hill.", true)
	game.rig.frame(game.party_node.centre(), 13.0, 30.0, -60.0)
	await _wait(1.5)
	await _shot("start")
	var probe := _probe()
	game.walk_to(Vector2i(3, 0))
	var k := 0
	while game.busy:
		await _wait(0.1)
		k += 1
		if k % 10 == 0:
			await _shot("step%02d" % (k / 10))
	await _wait(4.0)
	probe.call(false)
	await _shot("arrived")
	print("DEMO DONE")
	if shots or "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## The day passing over a swamp (Ethan's phone test: shadows dancing, a hitch at nightfall, the backdrop jumping):
## a staged swamp and forest round the camp, the camera close, and the clock run fast (`--speed=N`, clock
## minutes per real second; default 20) from `--from=M` to `--to=M` (clock minutes; past 30 is the next day).
## `--jumps=S` also moves the clock on by one card placement's time every S real seconds, as placing cards does.
## Prints frame times (all frames, around nightfall and around dawn), GPU render time, how often the sun moved
## and how fast the backdrop changed. Run it with --rendering-method mobile -- --phone for the phone's settings.
func _day() -> void:
	_prefix = "day"
	var args := OS.get_cmdline_user_args()
	var speed := 20.0
	var from := 12.0
	var to := 32.0
	var jumps := 0.0
	for a in args:
		var v := float(a.split("=")[-1])
		if a.begins_with("--speed="):
			speed = v
		elif a.begins_with("--from="):
			from = v
		elif a.begins_with("--to="):
			to = v
		elif a.begins_with("--jumps="):
			jumps = v
	var next_jump := jumps
	var kinds := ["swamp", "bog", "forest", "swamp", "deep_forest", "swamp"]
	var strip := {}
	var k := 0
	for q in range(-2, 3):
		for r in range(-2, 3):
			var t: Vector2i = game.party_tile + Vector2i(q, r)
			if t != game.party_tile and Rules.hex_distance(t, game.party_tile) <= 2 and not game.map.terrains.has(t):
				strip[t] = kinds[k % kinds.size()]
				k += 1
	game.map.retile(strip)
	for t in strip:
		game.order[t] = game.order.size()
	game.toast("(demo) Staged map: swamp and forest round the camp; the clock runs fast.", true)
	game.minute = from
	game.rig.frame(Hex.to3(Hex.tile_position(game.party_tile.x, game.party_tile.y) + Vector2(4.0, 2.0)), 26.0, 50.0)
	await _wait(2.0)
	var vp := get_viewport().get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(vp, true)
	var frames := []          # [clock minute (unwrapped), frame ms, gpu ms]
	var sun_moves := 0        # quarter seconds in which the sun's angle changed
	var quarters := 0
	var quarter_at := 0.0
	var sky_jump := 0.0       # the most the backdrop changed in one frame (0-255 per channel)
	var sky_rate := 0.0       # the most it changed over any half second
	var skies := []           # [real s, backdrop]
	var clock_min := from
	var last := Time.get_ticks_usec()
	var real := 0.0
	var sun_z: Vector3 = game.clock.sun.basis.z
	var sky: Color = game.clock.environment.background_color
	var shot_every := 2.0     # clock minutes between stills
	var next_shot := from
	while clock_min < to:
		var dt := get_process_delta_time()
		game._advance(dt * (speed - 1.0) / 60.0)
		clock_min += dt * speed / 60.0
		if jumps > 0.0 and real >= next_jump:
			next_jump += jumps
			game._advance(Rules.PLACE_MINUTES)
			clock_min += Rules.PLACE_MINUTES
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		var ms := (now - last) / 1000.0
		last = now
		real += ms / 1000.0
		frames.append([clock_min, ms, RenderingServer.viewport_get_measured_render_time_gpu(vp)])
		if real - quarter_at >= 0.25:
			quarter_at = real
			quarters += 1
			var z: Vector3 = game.clock.sun.basis.z
			if z.distance_to(sun_z) > 1e-5:   # about 0.0006 degrees
				sun_moves += 1
			sun_z = z
		var c: Color = game.clock.environment.background_color
		sky_jump = maxf(sky_jump, _col_diff(c, sky))
		sky = c
		skies.append([real, c])
		while skies.size() > 2 and real - skies[0][0] > 0.5:
			skies.pop_front()
		sky_rate = maxf(sky_rate, _col_diff(c, skies[0][1]))
		if shots and clock_min >= next_shot:
			next_shot += shot_every
			await _shot("min%04.1f" % fmod(clock_min, Rules.DAY_MINUTES))
	_report("all", frames, func(m): return true)
	_report("nightfall", frames, func(m): return absf(m - Rules.NIGHT_AT) < speed / 60.0 * 1.0)
	_report("dawn", frames, func(m): return absf(m - Rules.DAY_MINUTES) < speed / 60.0 * 1.0)
	print("SUN moved in %d of %d quarter seconds" % [sun_moves, quarters])
	print("BACKDROP most change: %.1f in one frame, %.1f over half a second (0-255 per channel)" % [sky_jump, sky_rate])
	print("DEMO DONE")
	if shots or "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


static func _col_diff(a: Color, b: Color) -> float:
	return maxf(absf(a.r - b.r), maxf(absf(a.g - b.g), absf(a.b - b.b))) * 255.0


## Prints frame time and GPU time for the frames whose clock minute passes `keep`.
static func _report(name: String, frames: Array, keep: Callable) -> void:
	var ms := []
	var gpu := []
	for f in frames:
		if keep.call(f[0]):
			ms.append(f[1])
			gpu.append(f[2])
	if ms.is_empty():
		print("FRAMES %s: none" % name)
		return
	ms.sort()
	gpu.sort()
	print("FRAMES %s: %d frames, median %.2f ms, 99th %.2f ms, worst %.2f ms; GPU median %.2f ms, worst %.2f ms" % [
		name, ms.size(), ms[ms.size() / 2], ms[mini(ms.size() - 1, int(ms.size() * 0.99))], ms[-1],
		gpu[gpu.size() / 2], gpu[-1]])


func _trace(path: PackedVector2Array) -> void:
	var dot := SphereMesh.new()
	dot.radius = 0.06
	dot.height = 0.12
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color.RED
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.no_depth_test = true
	dot.material = mat
	for k in range(0, path.size(), 2):
		var mi := MeshInstance3D.new()
		mi.mesh = dot
		mi.position = Hex.to3(path[k], game.party_node.ground(path[k]) + 0.1)
		game.map.add_child(mi)


## The variants recording: three regions finish one after another, the camera on each.
func _variants() -> void:
	_prefix = "variants"
	game.toast("(demo) Staged hand: 5 forest, then 5 hills, then 5 plains.", true)
	await _wait(1.0)
	for terrain in ["forest", "hills", "plains"]:
		game.deck.hand.clear()
		for k in 5:
			game.deck.hand.append(terrain)
		game._refresh()
		var placed: Array[Vector2i] = []
		while game.deck.hand.has(terrain):
			var before: Dictionary = game.map.terrains.duplicate()
			if placed.size() == 1:
				# frame where this cluster grows
				game.rig.ease_to(Hex.to3(Hex.tile_position(placed[0].x, placed[0].y)), 48.0, game.rig.yaw_deg)
			await _place(game.deck.hand.find(terrain), 0.35)
			for t: Vector2i in game.map.terrains:
				if not before.has(t):
					placed.append(t)
		await _wait(0.4)
		while game.busy:
			await _wait(0.1)
		await _wait(1.6)
		await _shot(Variants.TIER1[terrain])
	game.rig.ease_to(Hex.to3(Vector2.ZERO), 84.0, game.rig.yaw_deg)
	await _wait(2.5)
	await _shot("all")
	print("DEMO DONE")
	if shots or "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


## Saves one screenshot per name (the first time that state comes up).
func _shot(name: String) -> void:
	if _taken.has(name):
		return
	_taken[name] = true
	_n += 1
	if not shots:
		return
	await RenderingServer.frame_post_draw
	var dir := ProjectSettings.globalize_path("res://screens")
	game.get_viewport().get_texture().get_image().save_png(dir.path_join("%s_%02d_%s.png" % [_prefix, _n, name]))
	print("SAVED %s_%02d_%s" % [_prefix, _n, name])


func _run() -> void:
	await _wait(1.5)
	await _shot("explore_start")
	# 1. Place cards, growing same-terrain clusters, until an encounter is up and the hand runs low.
	var first := true
	while not game.deck.hand.is_empty():
		var i := _pick_card()
		while game.busy:
			await _wait(0.1)
		game.hold(i)
		await _wait(0.6)
		if first:
			await _shot("explore_holding")
			first = false
		game.try_place(_best_slot(game.deck.hand[i]))
		await _wait(0.7)
		while game.busy:
			await _wait(0.1)
		if not game.regions.is_empty() and not _taken.has("explore_region"):
			await _wait(0.5)
			await _shot("explore_region")
		if not game.encounters.is_empty() and game.deck.hand.size() <= 2:
			break
	if game.encounters.is_empty():
		var tiles: Array = game.map.terrains.keys().filter(func(t): return t != game.party_tile and t != Rules.START_TILE)
		game.add_encounter(tiles[-1], false)
		game.toast("(demo) No encounter spawned, so the demo added one.", false)
	await _wait(1.2)
	# 2. Walk to the encounter.
	var target: Vector2i = game.encounters.keys()[0]
	game.walk_to(target)
	while not game.hud.encounter_open():
		await _wait(0.1)
	await _wait(0.6)
	await _shot("explore_encounter")
	game.choose_fight()
	await _wait(1.6)
	await _fight()
	# 3. After combat.
	while not game.after.visible:
		await _wait(0.1)
	await _wait(5.5)
	await _shot("after_combat")
	game.after.done.emit()
	await _wait(1.5)
	await _shot("back_on_map")
	# 4. Build again with the refilled hand, until a region finishes or the hand runs out.
	var regions := game.regions.size()
	while not game.deck.hand.is_empty() and game.regions.size() == regions:
		await _place(_pick_card(), 0.5)
	# Frame the newest region so its variant tiles and landmark pin are in view.
	if game.regions.size() > 0:
		var g: Dictionary = game.regions[-1]
		var c := Vector2.ZERO
		for t in g.tiles:
			c += Hex.tile_position(t.x, t.y)
		game.rig.ease_to(Hex.to3(c / g.tiles.size()), 62.0, game.rig.yaw_deg)
	await _wait(1.0)
	await _shot("region_after_fight")
	await _wait(2.0)
	print("DEMO DONE")
	if shots or "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


# --- The fight ---------------------------------------------------------------------

func _fight() -> void:
	var f := game.fight
	await _shot("combat_start")
	# Show the screens the mockups show before the fight gets going: All actions, an ally target, and
	# the End phase confirmation (answered with Keep playing).
	var h := f.hud
	h._all.visible = true
	h._refresh_all()
	await _wait(0.8)
	await _shot("combat_all_actions")
	h._all.visible = false
	var chel: Dictionary = f.allies()[2]
	f.select(chel)
	await _wait(0.5)
	f.pick_card("bless")
	await _wait(0.4)
	await f.click_cell(f.allies()[0].cell)
	await _wait(0.6)
	await _shot("combat_ally_target")
	await f.press_button()
	await _wait(0.6)
	await _shot("combat_ally_cast")
	f.end_phase()
	await _wait(0.6)
	await _shot("combat_confirm_end")
	h.hide_confirm()
	await _wait(0.4)
	var first_round := true
	while f.active:
		if f.phase != "allies" or f.busy:
			await _wait(0.2)
			continue
		for u in f.allies():
			if not f.active or f.phase != "allies":
				break
			if u.down:
				continue
			f.select(u)
			await _wait(0.5)
			await _act(f, u)
		if f.active and f.phase == "allies":
			f.end_phase()
			await _wait(0.6)
			if f.hud.confirm_open():
				await _shot("combat_confirm_end")
				await _wait(0.4)
				f.confirm_end()
			first_round = false
		await _wait(0.4)


## One ally's turn: a class card when it fits, otherwise move toward the nearest foe and attack.
func _act(f: Fight, u: Dictionary) -> void:
	var tries := 0
	while f.active and f.phase == "allies" and f.ap_left(u) > 0 and tries < 8:
		tries += 1
		var foes := f.foes_of(u)
		if foes.is_empty():
			return
		foes.sort_custom(func(a, b): return Rules.hex_distance(a.cell, u.cell) < Rules.hex_distance(b.cell, u.cell))
		var foe: Dictionary = foes[0]
		# Chelmsford blesses the hero once (shows ally targeting), then casts Sacred Flame.
		if u.name == "Chelmsford" and f.cant_use(u, Cards.get_card("bless")) == "":
			f.pick_card("bless")
			await _wait(0.5)
			var hero: Dictionary = f.allies()[0]
			if f.ally_in_reach(u, hero, f.card()):
				await f.click_cell(hero.cell)
				await _wait(0.5)
				await _shot("combat_ally_target")
				await f.press_button()
				await _wait(0.7)
				continue
		var spell := ""
		for id in ["firebolt", "sacred_flame", "frost_ray"]:
			if id in u.cards and f.cant_use(u, Cards.get_card(id)) == "" and f.in_reach(u, foe, Cards.get_card(id)):
				spell = id
				break
		if spell != "":
			await _hit(f, foe, spell)
			continue
		if u.name == "[Hero name]" and f.cant_use(u, Cards.get_card("action_surge")) == "" and Rules.hex_distance(foe.cell, u.cell) == 1:
			f.pick_card("action_surge")
			await _wait(0.5)
			await f.press_button()
			await _wait(0.8)
			await _shot("combat_bonus_ap")
			continue
		if Rules.hex_distance(foe.cell, u.cell) == 1:
			var id := "sneak_attack" if u.name == "Mel" and f.cant_use(u, Cards.get_card("sneak_attack")) == "" else "attack"
			await _hit(f, foe, id)
			continue
		var options: Dictionary = f.reachable(u)
		if options.is_empty():
			return
		var best: Vector2i = options.keys()[0]
		for c in options:
			if Rules.hex_distance(c, foe.cell) < Rules.hex_distance(best, foe.cell):
				best = c
		if Rules.hex_distance(best, foe.cell) >= Rules.hex_distance(u.cell, foe.cell):
			return
		f.pick_card("move")
		await _wait(0.5)
		await _shot("combat_move")
		await f.click_cell(best)
		await _wait(0.4)


func _hit(f: Fight, foe: Dictionary, id: String) -> void:
	f.pick_card(id)
	await _wait(0.4)
	await f.click_cell(foe.cell)
	await _wait(0.5)
	await _shot("combat_target")
	await f.press_button()
	await _wait(0.3)
	await _shot("combat_coins")
	await _wait(0.6)


# --- Building ---------------------------------------------------------------------

## The card whose terrain already has the most tiles on the map (to finish a region), else the first.
func _pick_card() -> int:
	var best := 0
	var best_count := -1
	for i in game.deck.hand.size():
		var t := game.deck.hand[i]
		var count := game.map.terrains.keys().filter(func(c): return game.land(c) == t).size()
		if count > best_count:
			best = i
			best_count = count
	return best


## A legal slot touching the most tiles of the same terrain, then closest to the start.
func _best_slot(terrain: String) -> Vector2i:
	var best := Vector2i(999, 999)
	var score := -INF
	for s: Vector2i in game.map.slot_nodes:
		if game.why_not(s, terrain) != "":
			continue
		var same := 0
		for n in Hex.NEIGHBOURS:
			if game.land(s + n) == terrain and s + n != Rules.START_TILE:
				same += 1
		var v := same * 10.0 - Rules.hex_distance(s, Rules.START_TILE)
		if v > score:
			score = v
			best = s
	return best
