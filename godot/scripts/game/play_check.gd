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
var drunk := 0


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
	Engine.time_scale = 1.0 if "--slow" in OS.get_cmdline_user_args() else 16.0 if "--fast" in OS.get_cmdline_user_args() else 4.0
	game.debug_auto_cross = true
	await _wait(0.5)
	if "--bands" in OS.get_cmdline_user_args():
		_tune()
		await _bands()
		get_tree().quit()
		return
	_check(game.party.size() == 2 and game.party[1].name == "Fluffy", "the party is the hero and Fluffy")
	var total: int = game.deck.draw_pile.size() + game.deck.hand.size()
	_check(total == 24, "the deck is 05's 15 cards plus one of every terrain: %s" % [game.run.deck_cards()])
	_check(game.run.seed_text != "", "seed %s" % game.run.seed_text)
	game.potions = 2
	_check_sneak()
	var steps := 0
	while not game._ended and steps < MAX_STEPS:
		steps += 1
		StallWatch.beat("step %d: %d regions, %d in hand" % [steps, game.regions.size(), game.deck.hand.size()])
		if steps % 25 == 0:
			print("PLAY step %d: %d regions, hand %s, deck %d, %d encounters, day %d minute %.0f" % [steps, game.regions.size(), game.deck.hand, game.deck.draw_pile.size(), game.encounters.size(), game.day, game.minute])
		await _settle()
		if game.hud.encounter_open():
			await _answer()
			continue
		if await _rest_if_hurt():
			continue
		if "--outward" in OS.get_cmdline_user_args() and steps % 3 == 0:
			await _walk_outward()
			await _settle()
		if await _place_one():
			continue
		await _go_to_a_fight()
	for t: Vector2i in game.encounters:
		print("PLAY left on the map: %s %s at %s, %d steps away, party at %s" % [game.encounters[t].entry.kind, game.encounters[t].entry.scene, t, game.path_to(t).size(), game.party_tile])
	if failed > 0 or not game._ended:
		print("PLAY the map: %s" % [game.map.terrains])
		for t: Vector2i in game.map.terrains:
			print("PLAY tile %s %s: visit %s, path %d" % [t, game.map.terrains[t], game.map.can_visit(t), game.path_to(t).size()])
	print("PLAY party %d at the end, %d rests" % [game.party.size(), rests])
	print("PLAY %d steps; %d regions, %d fights, %d wipes, %d levels (level %d, %d gold), %d times out of cards, day %d" % [steps, game.regions.size(), fights, wipes, levels, game.level, game.gold, empties, game.day])
	_check(game.fights_won == 0 or game.gold > 0, "wins pay gold")
	print("PLAY party HP at the end: %s; %d potions drunk, %d left" % [game.party.map(func(m): return m.hp), drunk, game.potions])
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
			if "--outward" in OS.get_cmdline_user_args():   # a player who builds away from the start
				s = near * 10 + Rules.hex_distance(t, Rules.START_TILE)
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


## Sneak past goes by the hero, not the party; a helper's coin comes only on a miss by exactly 1 (design/03).
func _check_sneak() -> void:
	var hero := Hero.new()
	hero.scores = {"DEX": 2}
	hero.proficiencies = ["Stealth"]
	var before := Hero.current
	Hero.current = hero
	_check(Hero.coins_for("DEX", "Stealth") == 3, "Sneak past's coins are the hero's DEX and Stealth")
	hero.proficiencies = []
	_check(Hero.coins_for("DEX", "Stealth") == 2, "an unskilled hero has DEX alone")
	var kept := game.rng.state   # so a seed still means the same run
	var bad := 0
	for k in 200:
		var coins: Array[bool] = game.sneak_flip("Persuade")   # Fluffy stands in for a proficient helper
		var first := coins.slice(0, 2)
		var near_miss: bool = Coins.heads(first) == game.sneak_heads() - 1
		bad += 0 if coins.size() == (3 if near_miss else 2) else 1
	game.rng.state = kept
	_check(bad == 0, "the helper's one coin comes only on a miss by exactly 1")
	Hero.current = before


## Until the game's free or an encounter asks something; takes the first terrain at a level's pick.
func _settle() -> void:
	while game.busy and not game.hud.encounter_open() and not game._ended:
		if game.level_pick.visible:
			game.level_picked(game._pick_options[0])
		await get_tree().process_frame


## Under half the party's HP: back to the free rest at the start, as a player would (design/06).
func _rest_if_hurt() -> bool:
	var hp: int = game.party.reduce(func(n, m): return n + m.hp, 0)
	var most: int = game.party.reduce(func(n, m): return n + m.max_hp, 0)
	if hp * 2 >= most or not "--realfights" in OS.get_cmdline_user_args():
		return false
	if game.party_tile != Rules.START_TILE:
		game.walk_to(Rules.START_TILE)
		await _wait(0.1)
		await _settle()
		if game.party_tile != Rules.START_TILE:
			return false   # met something on the way, or can't get there: carry on
	game.rest_here()
	rests += 1
	return true


## An outward player stands at the far end of what's built, so the next cards can go further.
func _walk_outward() -> void:
	var far := game.party_tile
	for t: Vector2i in game.map.terrains:
		if Rules.hex_distance(t, Rules.START_TILE) > Rules.hex_distance(far, Rules.START_TILE):
			far = t
	if far != game.party_tile and not game.encounters.has(far):
		game.walk_to(far)
		await _wait(0.1)


func _go_to_a_fight() -> void:
	if game.deck.hand.is_empty():
		empties += 1
	var goal = null
	var near := 1 << 20
	for t: Vector2i in game.encounters:
		var d := Rules.hex_distance(t, game.party_tile)
		if d < near and not game.path_to(t).is_empty():
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


## How fights go at each band for a fresh party at a given level's HP (design/06's numbers), for the balance report.
## Foes' numbers to compare: --tune=hp:1,1.5,2;damage:1,1,2;coins:0,1,2;heads:0,0,1;count:2-3,3-3,3-4;attacks:1
func _tune() -> void:
	for a: String in OS.get_cmdline_user_args():
		if not a.begins_with("--tune="):
			continue
		for part: String in a.trim_prefix("--tune=").split(";"):
			var kv := part.split(":")
			var vals := kv[1].split(",")
			match kv[0]:
				"hp": Foes.band_hp = Array(vals).map(func(v): return v.to_float())
				"damage": Foes.band_damage = Array(vals).map(func(v): return v.to_float())
				"coins": Foes.band_coins = Array(vals).map(func(v): return v.to_int())
				"heads": Foes.band_heads = Array(vals).map(func(v): return v.to_int())
				"count": Foes.band_count = Array(vals).map(func(v): return [v.split("-")[0].to_int(), v.split("-")[1].to_int()])
				"attacks": Foes.attacks_per_turn = vals[0].to_int()


func _bands() -> void:
	game.run.joins_after = []
	var sizes := [2, 3, 4]
	var each := 8
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--each="):
			each = a.split("=")[1].to_int()
	for size in sizes:
		while game.party.size() < size:
			game._add_member(game.party.size())
			game.party_node.add_member(game.party[-1].mini)
		await _band_fights(each)
	print("PLAY DONE: %d failed" % failed)


func _band_fights(each: int) -> void:
	for band in [1, 2, 3]:
		Foes.debug_band = band
		for k in each:
			for m in game.party:
				m.hp = m.max_hp
			game.encounters.clear()
			game.busy = false
			var map_id: String = ["plains_stones", "forest_knoll", "plains_trees", "forest_glade", "plains_long_grass"][k % 5]
			game.force_map = map_id
			game.add_encounter(game.party_tile, false, [], Rules.ENCOUNTER_TABLE[k % 2])
			game.start_fight(game.party_tile)
			while not game.fight.active:
				await get_tree().process_frame
			await _wait(0.5)
			await _play_fight()
			while not game.after.visible:
				await get_tree().process_frame
			await _wait(0.1)
			game.after.done.emit()
			while game.busy:
				if game.level_pick.visible:
					game.level_picked(game._pick_options[0])
				await get_tree().process_frame
			game.level = 1
			game.xp = 0


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
	print("PLAY FIGHT party %d band %d, %s: %d rounds, party HP %d to %d, %d down%s" % [f.allies().size(), band, roles, rounds, hp0, hp1, downs, ", WIPED" if wiped else ""])
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
		var hurt: Array = f.allies().filter(func(a): return not a.down and a.hp * 2 < a.max_hp and f.dist(a, u) <= 5)
		if "healing_word" in u.cards and not hurt.is_empty() and f.cant_use(u, Cards.get_card("healing_word")) == "":
			f.pick_card("healing_word")
			await _wait(0.05)
			await f.click_cell(hurt[0].cell)
			await _wait(0.05)
			await f.press_button()
			await _wait(0.2)
			while f.busy:
				await _wait(0.05)
			continue
		if u.hp * 2 < u.max_hp and f.cant_use(u, Cards.get_card("second_wind")) == "" and "second_wind" in u.cards:
			picked = "second_wind"
		elif u.hp * 2 < u.max_hp and f.cant_use(u, Cards.get_card("use_item")) == "":
			picked = "use_item"
			drunk += 1
		else:
			for id: String in ["firebolt", "frost_ray", "sacred_flame", "backstab", "sneak_attack", "throw", "shield_bash", "attack"]:
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
		if Cards.get_card(picked).kind in ["attack", "save"]:
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
