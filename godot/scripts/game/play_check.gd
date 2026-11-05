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
var levels := 0
var wipes := 0


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
	_check(total == 24, "the deck is 05's 15 cards plus one of every terrain: %s" % [game.run.deck_cards()])
	_check(game.run.seed_text != "", "seed %s" % game.run.seed_text)
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
	print("PLAY %d steps; %d regions, %d fights, %d wipes, %d levels (level %d, %d gold), %d times out of cards, day %d" % [steps, game.regions.size(), fights, wipes, levels, game.level, game.gold, empties, game.day])
	_check(game.fights_won == 0 or game.gold > 0, "wins pay gold")
	print("PLAY party HP at the end: %s" % [game.party.map(func(m): return m.hp)])
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


## A plain player: Fluffy's bolts and frost when in reach, the hero's Shield Bash then attacks, Second Wind when hurt. Notes how each fight went, for the balance report.
func _play_fight() -> void:
	var f := game.fight
	var band := Foes.band(game.party_tile)
	var roles: Array = f.units.filter(func(u): return not u.ally).map(func(u): return u.role)
	var hp0: int = f.allies().reduce(func(n, u): return n + u.hp, 0)
	var rounds := 0
	while f.active and f.phase != "over":
		if f.phase != "allies" or f.busy:
			await _wait(0.1)
			continue
		rounds += 1
		for u: Dictionary in f.allies():
			if not f.active or f.phase != "allies" or u.down:
				continue
			f.select(u)
			await _wait(0.1)
			await _take_turn(f, u)
		if f.active and f.phase == "allies":
			f.end_phase()
			await _wait(0.2)
			if f.hud.confirm_open():
				f.confirm_end()
		await _wait(0.1)
		if rounds > 30:
			break
	var hp1: int = f.allies().reduce(func(n, u): return n + maxi(u.hp, 0), 0)
	var downs: int = f.allies().filter(func(u): return u.down).size()
	var wiped: bool = f.allies().all(func(u): return u.down)
	print("PLAY FIGHT band %d, %s: %d rounds, party HP %d to %d, %d down%s" % [band, roles, rounds, hp0, hp1, downs, ", WIPED" if wiped else ""])
	wipes += 1 if wiped else 0


func _take_turn(f: Fight, u: Dictionary) -> void:
	var tries := 0
	while f.active and f.phase == "allies" and f.ap_left(u) > 0 and tries < 8:
		tries += 1
		var foes := f.foes_of(u)
		if foes.is_empty():
			return
		foes.sort_custom(func(a, b): return f.dist(a, u) < f.dist(b, u))
		var foe: Dictionary = foes[0]
		var picked := ""
		if u.hp * 2 < u.max_hp and f.cant_use(u, Cards.get_card("second_wind")) == "" and "second_wind" in u.cards:
			picked = "second_wind"
		else:
			for id: String in ["firebolt", "frost_ray", "shield_bash", "attack"]:
				if id in u.cards:
					var c := Cards.get_card(id, u.weapon)
					if f.cant_use(u, c) == "" and f.dist(foe, u) <= c.get("range", 1):
						picked = id
						break
		if picked == "":
			var options: Dictionary = f.reachable(u)
			var best := u.cell as Vector2i
			for c in options:
				if Rules.hex_distance(c, foe.cell) < Rules.hex_distance(best, foe.cell):
					best = c
			if best == u.cell:
				return
			f.pick_card("move")
			await _wait(0.05)
			await f.click_cell(best)
			await _wait(0.1)
			continue
		f.pick_card(picked)
		await _wait(0.05)
		if Cards.get_card(picked).kind == "attack":
			await f.click_cell(foe.cell)
			await _wait(0.05)
		await f.press_button()
		await _wait(0.2)
		while f.busy:
			await _wait(0.05)


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
	if "--realfights" in OS.get_cmdline_user_args():
		await _play_fight()
	else:
		game.fight.finished.emit(true)
	while not game.after.visible:
		await get_tree().process_frame
	await _wait(0.1)
	game.after.done.emit()
	while game.busy:
		if game.level_pick.visible:
			levels += 1
			game.level_picked(game._pick_options[0])
		await get_tree().process_frame
