class_name Demo
extends Node
## Plays one full loop by itself, through the same calls a player's clicks make, for recordings and
## screenshots: place cards (finishing a region), walk to an encounter, fight it, return with the hand
## refilled. Run with `-- --demo` (add `--shots` to save screens/loop_*.png).
## It's a test driver, not game AI: it plays simply and never cheats the rules, except that if no
## encounter has spawned once the hand is empty it adds one so the loop can go on (said on screen).

var game: Game
var shots := false
var _n := 0


func _ready() -> void:
	shots = "--shots" in OS.get_cmdline_user_args()
	_run.call_deferred()


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _shot(name: String) -> void:
	_n += 1
	if not shots:
		return
	await RenderingServer.frame_post_draw
	var dir := ProjectSettings.globalize_path("res://screens")
	game.get_viewport().get_texture().get_image().save_png(dir.path_join("loop_%d_%s.png" % [_n, name]))
	print("SAVED loop_%d_%s" % [_n, name])


func _run() -> void:
	await _wait(1.5)
	await _shot("start")
	# 1. Place cards, growing same-terrain clusters, until the hand is empty or an encounter is up.
	var first := true
	while not game.deck.hand.is_empty():
		var i := _pick_card()
		game.hold(i)
		await _wait(0.5)
		if first:
			await _shot("holding_card")
			first = false
		var slot := _best_slot(game.deck.hand[i])
		game.try_place(slot)
		await _wait(0.6)
		if game.prompt.text.contains("region finished"):
			await _wait(0.4)
			await _shot("region_finished_first")
		if not game.encounters.is_empty() and game.deck.hand.size() <= 3:
			break
	if game.encounters.is_empty():
		var tiles: Array = game.map.terrains.keys().filter(func(t): return t != game.party_tile)
		game._add_encounter(tiles[-1], false)
		game.message("(demo) no encounter spawned, so the demo added one", 3.0)
	await _wait(1.0)
	await _shot("map_built")
	# 2. Walk to the encounter.
	var target: Vector2i = game.encounters.keys()[0]
	game.walk_to(target)
	while not game.popup.visible:
		await _wait(0.1)
	await _wait(0.6)
	await _shot("encounter")
	# 3. Fight.
	game.start_fight(target)
	await _wait(1.5)
	await _shot("fight_start")
	var fight := game.fight
	var shot_flip := true
	while fight.active:
		if fight.phase != "Allies" or fight._busy:
			await _wait(0.2)
			continue
		for u in fight.units.duplicate():
			if not fight.active or fight.phase != "Allies":
				break
			if not u.ally or u.down:
				continue
			fight.select(u)
			await _wait(0.4)
			while u.ap > 0 and fight.active and fight.phase == "Allies":
				var foes := fight.foes_of(u)
				if foes.is_empty():
					break
				foes.sort_custom(func(a, b): return Rules.hex_distance(a.cell, u.cell) < Rules.hex_distance(b.cell, u.cell))
				var foe: Dictionary = foes[0]
				if "hunters_mark" in u.cards and fight._can_use(u, "hunters_mark") and u.mark != foe:
					fight.choose("hunters_mark")
					await _wait(0.4)
					await fight.click_cell(foe.cell)
				elif Rules.hex_distance(foe.cell, u.cell) == 1:
					fight.choose("attack")
					await _wait(0.35)
					await fight.click_cell(foe.cell)
					if shot_flip:
						shot_flip = false
						await _shot("attack_coins")
				else:
					var options: Dictionary = fight.reachable(u)
					if options.is_empty():
						break
					var best: Vector2i = options.keys()[0]
					for c in options:
						if Rules.hex_distance(c, foe.cell) < Rules.hex_distance(best, foe.cell):
							best = c
					if Rules.hex_distance(best, foe.cell) >= Rules.hex_distance(u.cell, foe.cell):
						break
					fight.choose("move")
					await _wait(0.35)
					await fight.click_cell(best)
				await _wait(0.3)
		if fight.active and fight.phase == "Allies":
			fight.end_phase()
			if fight.confirm.visible:      # allies with AP left: answer the confirmation with End phase
				await _wait(0.6)
				fight.confirm.visible = false
				fight._enemy_phase()
			await _wait(0.5)
	# 4. Back on the map.
	while not game.popup.visible:
		await _wait(0.1)
	await _wait(0.5)
	await _shot("fight_result")
	for b in game.popup_buttons.get_children():
		(b as Button).pressed.emit()
		break
	await _wait(1.5)
	await _shot("back_on_map")
	# 5. Build again with the refilled hand, until a region finishes or the hand runs out.
	var done := false
	while not game.deck.hand.is_empty() and not done:
		var i := _pick_card()
		game.hold(i)
		await _wait(0.5)
		game.try_place(_best_slot(game.deck.hand[i]))
		await _wait(0.6)
		if game.prompt.text.contains("region finished"):
			done = true
			await _wait(0.4)
			await _shot("region_finished")
	await _wait(2.0)
	print("DEMO DONE")
	if shots or "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## The card whose terrain already has the most tiles on the map (to finish a region), else the first.
func _pick_card() -> int:
	var best := 0
	var best_count := -1
	for i in game.deck.hand.size():
		var t := game.deck.hand[i]
		var count := game.map.terrains.values().count(t)
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
			if game.map.terrains.get(s + n) == terrain and s + n != Rules.START_TILE:
				same += 1
		var v := same * 10.0 - Rules.hex_distance(s, Rules.START_TILE)
		if v > score:
			score = v
			best = s
	return best
