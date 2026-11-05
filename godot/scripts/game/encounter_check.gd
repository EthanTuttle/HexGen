class_name EncounterCheck
extends Node
## Checks map encounters and the walking limit (design/02, design/07) in the game (`-- --enccheck`, add `--shots` for screens/enc_*.png, `--encclip` to film walking and spotting by day and
## night with --write-movie). Prints ENC OK / ENC FAIL lines, then ENC DONE. A test aid only.

var game: Game
var failed := 0
var shots := false


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("ENC %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _shot(name: String) -> void:
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	if shots:
		game.get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path("res://screens").path_join("enc_%s.png" % name))


func _run() -> void:
	game.spawn_forest_regions()
	await _wait(1.0)
	game.debug_auto_cross = true
	game.walk_limited = true
	game.rig.player_moved = false
	if "--encclip" in OS.get_cmdline_user_args():
		await _clip()
		get_tree().quit()
		return
	await _limit()
	await _sight()
	await _roam()
	await _kinds()
	print("ENC DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


func _day() -> void:
	game.minute = Rules.START_MINUTE


func _night() -> void:
	while not Rules.is_night(game.minute):
		game.minute = fposmod(game.minute + 0.5, Rules.DAY_MINUTES)


## A placed tile a walk of exactly n steps away at least, and the path.
func _far(n: int) -> Vector2i:
	for t: Vector2i in game.map.terrains:
		var away := Rules.hex_distance(t, game.party_tile)
		if away >= n and away <= n + 2 and game.map.can_visit(t) and game.path_to(t).size() >= n:
			return t
	return game.party_tile


func _limit() -> void:
	_day()
	var goal := _far(7)
	var whole := game.path_to(goal)
	_check(whole.size() >= 7, "a goal %d steps away" % whole.size())
	var from := game.party_tile
	game.walk_to(goal)
	while game.busy:
		await get_tree().process_frame
	var by_day := game.party_tile
	_check(by_day == whole[Rules.SIGHT_RANGE * Rules.SIGHT_DAY_TIMES - 1], "by day one tap walks at most %d, the day's sight" % (Rules.SIGHT_RANGE * Rules.SIGHT_DAY_TIMES))
	_night()
	var goal2 := _far(5)
	var whole2 := game.path_to(goal2)
	game.walk_to(goal2)
	while game.busy:
		await get_tree().process_frame
	_check(game.party_tile == whole2[Rules.SIGHT_RANGE - 1], "at night one tap walks at most %d" % Rules.SIGHT_RANGE)
	_day()
	await get_tree().process_frame


func _ring_tile(n: int) -> Vector2i:
	for t: Vector2i in game.map.terrains:
		if Rules.hex_distance(t, game.party_tile) == n and game.map.can_visit(t) and not game.encounters.has(t):
			return t
	return Vector2i(999, 999)


func _sight() -> void:
	_day()
	var near := _ring_tile(3)
	var far := _ring_tile(6)
	game.add_encounter(near, false, [], Rules.ENCOUNTER_TABLE[3])   # one that stays put, as the clock jumps here
	game.add_encounter(far, false, [], Rules.ENCOUNTER_TABLE[4])
	await get_tree().process_frame
	var vn: EncounterView = game._encounter_views[game.encounters[near].id]
	var vf: EncounterView = game._encounter_views[game.encounters[far].id]
	_check(vn.visible and not vf.visible, "by day figures and badge show within 4 and not at 6")
	_check(is_equal_approx(vn.figures.scale.x, 1.0), "figures stand at scale 1")
	_night()
	await get_tree().process_frame
	_check(not vn.visible and game.sees(game.party_tile), "at night the same one at 3 has gone")
	_day()
	await get_tree().process_frame
	game.rig.frame(Hex.to3(Hex.tile_position(near.x, near.y)), 58.0, 50.0)
	await _wait(0.2)
	await _shot("day_map_zoom")
	game.rig.frame(Hex.to3(Hex.tile_position(near.x, near.y)), 16.0, 45.0)
	await _wait(0.2)
	await _shot("close")
	var pts := vn.badge.scale.x * 844.0 / (2.0 * tan(deg_to_rad(game.rig.camera.fov) * 0.5) * game.rig.distance)
	_check(pts < EncounterView.POINTS and pts >= EncounterView.POINTS * EncounterView.SMALLEST, "the badge shrinks gently zoomed in: %.0f pt at %.0f m" % [pts, game.rig.distance])
	var gone: int = game.encounters[near].id
	game.encounters.erase(near)
	game.encounters.erase(far)
	await get_tree().process_frame
	await get_tree().process_frame
	_check(not game._encounter_views.has(gone), "gone encounters take their views with them")


func _roam() -> void:
	var at := _ring_tile(3)
	game.add_encounter(at, false, [], Rules.ENCOUNTER_TABLE[2])
	var e: Dictionary = game.encounters[at]
	var moves := 0
	var region := game.cluster(at)
	for k in 5:
		game.minute = fposmod(game.minute + Rules.ROAM_MINUTES + 1.0, Rules.DAY_MINUTES)
		game.day += 1
		await get_tree().process_frame
	var now = null
	for t: Vector2i in game.encounters:
		if game.encounters[t].id == e.id:
			now = t
	_check(now != null and region.has(now), "a roamer stays in its region")
	_check(now != at or region.size() < 2, "a roamer moves a tile at a time on the clock")
	game.encounters.erase(now)
	var still := _ring_tile(3)
	game.add_encounter(still, false, [], Rules.ENCOUNTER_TABLE[3])
	game.day += 2
	await get_tree().process_frame
	_check(game.encounters.has(still), "the rest stay put")
	game.encounters.erase(still)
	await get_tree().process_frame


func _kinds() -> void:
	for row: Dictionary in Rules.ENCOUNTER_TABLE:
		var kit := Kit.meshes("res://art/encounters.glb")
		_check(kit.has(row.scene) and kit.has("enc_badge_" + row.kind), "%s: figures and a %s badge are in the kit" % [row.scene, row.kind])
	_day()
	var at := _ring_tile(1)
	game.add_encounter(at, false, [], Rules.ENCOUNTER_TABLE[4])
	game.walk_to(at)
	while not game.hud.encounter_open():
		await get_tree().process_frame
	_check(game.party_tile == at, "walking onto a Discovery stops there and opens its pop-up")
	await _shot("discovery_popup")
	game.choose_event_done()
	_check(not game.encounters.has(at) and not game.busy, "Carry on closes it, and it's gone (PLACEHOLDER)")


## Walking and spotting, by day and at night.
func _clip() -> void:
	_day()
	game.rig.frame(game.party_node.centre(), 30.0, 50.0)
	game.rig.player_moved = false
	var rows := Rules.ENCOUNTER_TABLE
	var spots := [[3, 3], [4, 0], [5, 2], [6, 1], [7, 4], [8, 3]]
	for s: Array in spots:
		var t := _ring_tile(s[0])
		if t != Vector2i(999, 999):
			game.add_encounter(t, false, [], rows[s[1]])
	await _wait(1.0)
	for pass_ in 2:
		if pass_ == 1:
			_night()
			await _wait(1.5)
		for step in 2:
			var goal := _far(8)
			game.pick(goal)
			await _wait(1.2)
			game.walk_to(goal)
			await _wait(0.1)
			while game.busy and not game.hud.encounter_open():
				await get_tree().process_frame
			if game.hud.encounter_open():
				await _wait(0.8)
				if game.encounters.has(game.party_tile) and game.encounters[game.party_tile].entry.kind != "fight":
					game.choose_event_done()
				else:
					game.choose_carry_on()
			await _wait(0.8)
