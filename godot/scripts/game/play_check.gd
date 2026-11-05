class_name PlayCheck
extends Node
## Plays the first playable by itself from a real start (`-- --playcheck [--seed=<any>]`, design/06 -> First playable): places what it holds, grows clusters, walks to fights and wins them
## by the debug way, rests when it can, until the goal's end panel, or says where it stuck. Prints PLAY OK / PLAY FAIL lines, then PLAY DONE. A test aid only.

const MAX_STEPS := 400

var game: Game
var failed := 0
var fights := 0
var empties := 0
var rests := 0


func _ready() -> void:
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	StallWatch.beat(what)
	print("PLAY %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _run() -> void:
	Engine.time_scale = 4.0
	game.debug_auto_cross = true
	await _wait(0.5)
	_check(game.party.size() == 2 and game.party[1].name == "Fluffy", "the party is the hero and Fluffy")
	var total: int = game.deck.draw_pile.size() + game.deck.hand.size()
	_check(total == 15, "the deck is 15 cards: %s" % [game.run.deck_cards()])
	_check(game.deck.hand.size() + game.deck.draw_pile.size() == 15 and game.run.seed_text != "", "seed %s" % game.run.seed_text)
	var steps := 0
	while not game._ended and steps < MAX_STEPS:
		steps += 1
		StallWatch.beat("step %d: %d regions, %d in hand" % [steps, game.regions.size(), game.deck.hand.size()])
		if steps % 25 == 0:
			print("PLAY step %d: %d regions, hand %s, deck %d, %d encounters, day %d minute %.0f" % [steps, game.regions.size(), game.deck.hand, game.deck.draw_pile.size(), game.encounters.size(), game.day, game.minute])
		while game.busy and not game.hud.encounter_open():
			await get_tree().process_frame
		if game.hud.encounter_open():
			await _answer()
			continue
		if await _place_one():
			continue
		await _go_to_a_fight()
	print("PLAY %d steps; %d regions, %d fights, %d rests, %d times out of cards, day %d" % [steps, game.regions.size(), fights, rests, empties, game.day])
	_check(game._ended, "the goal's 3 regions brought up the end panel")
	_check(game.end_panel.visible, "the end panel shows")
	print("PLAY DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## Places a card, growing the biggest cluster it can. False if it can't place anything.
func _place_one() -> bool:
	var best := -1
	var best_t := Vector2i.ZERO
	var score := -1
	for i in game.deck.hand.size():
		var card: String = game.deck.hand[i]
		for t: Vector2i in game.map.slot_nodes:
			if game.why_not(t, card) != "":
				continue
			var near := 0
			for n: Vector2i in Hex.NEIGHBOURS:
				if game.land(t + n) == card and not game.finished.has(t + n):
					near = maxi(near, game.cluster(t + n).size())
			var s := near * 10 + (1 if near > 0 else 0)
			if s > score:
				score = s
				best = i
				best_t = t
	if best < 0:
		return false
	game.hold(best)
	game.try_place(best_t)
	await _wait(0.05)
	return true


func _go_to_a_fight() -> void:
	if game.deck.hand.is_empty():
		empties += 1
	var goal = null
	var near := 1 << 20
	for t: Vector2i in game.encounters:
		var d := Rules.hex_distance(t, game.party_tile)
		if d < near:
			near = d
			goal = t
	if goal == null:
		if game.deck.hand.is_empty():
			await get_tree().process_frame
			return
		# Holding cards with nowhere to put them, and nothing to fight: walk, so the clock rolls.
		game._advance(Rules.ROLL_EVERY)
		await get_tree().process_frame
		return
	game.walk_to(goal)
	await _wait(0.1)


func _answer() -> void:
	if game.encounters.has(game.party_tile) and game.encounters[game.party_tile].entry.kind != "fight":
		game.choose_event_done()
		await get_tree().process_frame
		return
	if not game.encounters.has(game.party_tile):
		game.choose_carry_on()
		return
	fights += 1
	game.choose_fight()
	while not game.fight.active:
		await get_tree().process_frame
	await _wait(0.5)
	game.fight.finished.emit(true)
	while not game.after.visible:
		await get_tree().process_frame
	await _wait(0.1)
	game.after.done.emit()
	while game.busy:
		await get_tree().process_frame
