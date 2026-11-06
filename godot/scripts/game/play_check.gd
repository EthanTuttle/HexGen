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
var bot: FightBot
var to_far := "--tofar" in OS.get_cmdline_user_args()   # test aid: play on past the goal until the first far fight, for level pacing
var first_far := {}
var _shut := {}
var _locked := false
var _water_gates := {}


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
	game.event_screen = Callable()   # events as a pop-up it can answer; Screens' own checks play the Social screen
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
	while (to_far or not game._ended) and steps < (MAX_STEPS * 3 if to_far else MAX_STEPS) and first_far.is_empty():
		steps += 1
		if to_far and game.end_panel.visible:   # Keep exploring
			game.end_panel.visible = false
			game.busy = false
		StallWatch.beat("step %d: %d regions, %d in hand" % [steps, game.regions.size(), game.deck.hand.size()])
		if steps % 25 == 0:
			print("PLAY step %d: %d regions, hand %s, deck %d, %d encounters, day %d minute %.0f" % [steps, game.regions.size(), game.deck.hand, game.deck.draw_pile.size(), game.encounters.size(), game.day, game.minute])
		await _settle()
		if game.hud.encounter_open():
			await _answer()
			continue
		_watch_start()
		if await _rest_if_hurt():
			continue
		if "--outward" in OS.get_cmdline_user_args() and steps % 3 == 0:
			await _walk_outward()
			await _settle()
		if await _place_one():
			continue
		await _go_to_a_fight()
	if to_far:
		print("PLAY FIRST FAR: %s" % (JSON.stringify(first_far) if not first_far.is_empty() else "none in %d steps (%d fights, level %d, party %d)" % [steps, fights, game.level, game.party.size()]))
		print("PLAY DONE: %d failed" % failed)
		get_tree().quit()
		return
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


## Says so if a tile beside the start can't be stepped to, or the party has no cards and nothing left to walk to (design/06: a run can't stick that way).
func _watch_start() -> void:
	var seed_is := "seed %s, background %s" % [game.run.seed_text, game.run.background]
	for n: Vector2i in Hex.NEIGHBOURS:
		var t: Vector2i = Rules.START_TILE + n
		if game.map.terrains.has(t) and not _shut.has(t) and not game.map.edge_open(Rules.START_TILE, t):
			_shut[t] = true
			print("PLAY START SHUT: %s, %s %s" % [seed_is, game.map.terrains[t], t])
	if game.map.terrains[Rules.START_TILE] == StartTiles.MONTO:
		for i in 6:
			if not i in StartTiles.MOUTHS and Variants.is_water(game.map.terrains.get(Rules.START_TILE + Hex.NEIGHBOURS[i])) and not _shut.has(i):
				_shut[i] = true
				print("PLAY FAIL: water beside Monto Town on side %d, %s" % [i, seed_is])
				failed += 1
	for t: Vector2i in game.map.water_gates:
		if not _water_gates.has(t):
			_water_gates[t] = true
			print("PLAY WATER GATE: %s, %s %s edge %s, %d tiles, monto %s" % [seed_is, game.map.terrains[t], t, game.map.water_gates[t],
					game.map.terrains.size(), game.map.terrains[Rules.START_TILE] == StartTiles.MONTO])
	if _locked or game.busy or not game.deck.hand.is_empty():
		return
	for t: Vector2i in game.map.terrains:
		if t != game.party_tile and t != Rules.START_TILE and not game.path_to(t).is_empty():
			return
	if game.map.terrains.size() == 1:
		return
	_locked = true
	print("PLAY LOCKED: %s, at %s, %d tiles, %d in the deck" % [seed_is, game.party_tile, game.map.terrains.size(), game.deck.draw_pile.size()])


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
## Foes' numbers to compare: --tune=hp:1,1.5,2;damage:1,1,2;coins:0,1,2;heads:0,0,1;elite:1;count:2-3,3-3,3-4;attacks:1;
## level:elite=0,0,1,1,2
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
				"elite": Foes.elite_heads = vals[0].to_int()
				"farfrom": Foes.far_from_level = vals[0].to_int()
				"level":
					var rv := kv[1].split("=")
					Foes.level_heads[rv[0]] = Array(rv[1].split(",")).map(func(v): return v.to_int())


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


## The fight bot (FightBot) plays it out; notes how each fight went, for the balance report.
func _play_fight() -> void:
	var f := game.fight
	var band := Foes.band(game.party_tile)
	var roles: Array = f.units.filter(func(u): return not u.ally).map(func(u): return u.role)
	if bot == null:
		bot = FightBot.new(get_tree())
	if band == 3 and first_far.is_empty():
		first_far = {fights_before = fights - 1, won_before = game.fights_won, level = game.level, party = f.allies().size(), day = game.day, regions = game.regions.size()}
	var r := await bot.play(f)
	drunk = bot.drunk
	print("PLAY FIGHT party %d band %d, %s: %d rounds, party HP %d to %d, %d down%s" % [f.allies().size(), band, roles, r.rounds, r.hp0, r.hp1, r.downs, ", WIPED" if r.wiped else ""])
	wipes += 1 if r.wiped else 0


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
