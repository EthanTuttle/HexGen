class_name RaceCheck
extends Node
## Checks the races in play (`-- --racecheck`, with `--race=`, `--sub=` and `--spell=` for the hero; design/03 -> Races and
## Racial spells, design/06 -> First playable -> Races): the party's scores, each racial passive and card with set coins
## (Coins.forced), cover and the long shot, then one fight played out by the fight bot. Prints RACE OK / RACE FAIL lines,
## RACE BOT (the fight and the cards it played), then RACE DONE. A test aid only.

var game: Game
var f: Fight
var failed := 0


func _ready() -> void:
	_run.call_deferred()


func _check(ok: bool, what: String) -> void:
	print("RACE %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _fight(map_id: String) -> void:
	game.debug_fight(map_id)
	while not (game.fight.active and game.fight.phase == "allies" and not game.fight.busy):
		await get_tree().process_frame
	await _wait(0.3)
	f = game.fight


func _who(name: String) -> Dictionary:
	for u in f.units:
		if u.ally and u.name == name:
			return u
	return {}


func _place(u: Dictionary, c: Vector2i) -> void:
	u.cell = c
	u.mini.position = f.cell_point(c)


## A start cell and direction with n open, level, empty cells after it and no cover, or [].
func _free_line(n: int) -> Array:
	for s: Vector2i in f.grid:
		for d in Hex.NEIGHBOURS.size():
			var ok: bool = f.grid[s].kind == "open" and not f.cover.has(s)
			for i in range(1, n + 1):
				var c: Vector2i = s + Hex.NEIGHBOURS[d] * i
				ok = ok and f.grid.has(c) and f.grid[c].kind == "open" and not f.cover.has(c) and f.grid[c].z == f.grid[s].z
			if ok:
				return [s, d]
	return []


## Moves everyone out of the way: to the free cells farthest from `from`.
func _clear_round(from: Vector2i, keep: Array) -> void:
	var free: Array = f.grid.keys().filter(func(c): return f.grid[c].kind == "open" and Rules.hex_distance(c, from) > 7)
	free.sort_custom(func(a, b): return Rules.hex_distance(a, from) > Rules.hex_distance(b, from))
	var k := 0
	for u in f.units:
		if not u in keep and k < free.size():
			_place(u, free[k])
			k += 2


## Clears riders left by an earlier case.
func _fresh(u: Dictionary) -> void:
	u.hp = u.max_hp
	u.down = false
	u.lost_ap = 0
	(u.mini.get_node("body") as Node3D).quaternion = Quaternion.IDENTITY
	u.glow = -1
	u.slowed = -1
	u.acid = -1
	u.poison = []
	u.slow_hexes = 0
	u.bleed_turns = 0
	u.lull = false
	u.lockdown = false


func _turn(u: Dictionary) -> void:
	f.phase = "allies"
	f.busy = false
	u.ap = Rules.AP
	u.bonus = 0
	u.used = {}
	f.select(u)


## `--shots`: the screen to screens/race/<name>.png.
func _shot(name: String) -> void:
	if not "--shots" in OS.get_cmdline_user_args():
		return
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	var dir := ProjectSettings.globalize_path("res://screens/race")
	DirAccess.make_dir_recursive_absolute(dir)
	game.get_viewport().get_texture().get_image().save_png(dir.path_join("%s.png" % name))


## Plays card id for u at a cell, with these coins next. With --shots: the aimed card before, the board after.
func _play(u: Dictionary, id: String, at, coins: Array) -> void:
	_turn(u)
	Coins.forced.assign(coins)
	f.pick_card(id)
	if at != null:
		await f.click_cell(at)
	if "--shots" in OS.get_cmdline_user_args():
		game.rig.ease_to(f.global_position + u.mini.position, game.rig.distance, game.rig.yaw_deg)
		await _wait(0.5)
		await _shot("%s_%s_aim" % [game.party[0].sub.replace(" ", "_").to_lower(), id])
	var shooting := "--shots" in OS.get_cmdline_user_args()
	if shooting and id in ["attack", "breath"]:
		f.press_button.call_deferred()
		await get_tree().process_frame
		await _wait(0.9)   # Lucky's clover and the reflip, mid-air
		await _shot("%s_%s_mid" % [game.party[0].sub.replace(" ", "_").to_lower(), id])
	else:
		await f.press_button()
	while f.busy:
		await get_tree().process_frame
	Coins.forced.clear()
	await _shot("%s_%s_after" % [game.party[0].sub.replace(" ", "_").to_lower(), id])


func _run() -> void:
	await _wait(1.0)
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--covermap="):
			await _fight(a.trim_prefix("--covermap="))
			_cover_data_checks()
			print("RACE DONE: %d failed" % failed)
			get_tree().quit()
			return
	await _fight("plains_stones")
	var hero: Dictionary = f.units[0]
	var fluffy := _who("Fluffy")
	var chelm := _who("Chelmsford")
	var mel := _who("Mel")
	var foe: Dictionary = f.units.filter(func(u): return not u.ally)[0]
	var level: int = game.level
	print("RACE hero: %s %s %s, scores %s" % [hero.member.race, hero.sub, hero.member.get("spell", ""), hero.member.scores])
	if "--panelfit" in OS.get_cmdline_user_args():
		await _panel_fit()
		get_tree().quit()
		return

	# Scores drive play (06): the hero's from the creator (or HERO_DEFAULT), companions' from 03.
	_check(f.attack_score(hero, Cards.get_card("attack")) == Races.score(hero.member, "STR"), "the hero's attack flips their own STR")
	_check(f.attack_score(fluffy, Cards.get_card("firebolt")) == 3 and f.save_coins(fluffy, {}, "DEX") == 2, "Fluffy: INT 3 on Firebolt, DEX 2 on saves")
	_check(f.attack_score(chelm, Cards.get_card("attack")) == 2 and f.save_coins(chelm, {}, "DEX") == 1, "Chelmsford: STR 2, DEX 1")
	_check(f.attack_score(mel, Cards.get_card("attack")) == 2 and f.save_coins(mel, {}, "WIS") == 2, "Mel: DEX 2, WIS 2")
	var f9 := UI.font("n900")
	var too_wide := []
	for id: String in Cards.ALL:
		for line in Cards.name_lines(Cards.ALL[id].n, f9, 11, 56):
			if f9.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x > 56:
				too_wide.append(line)
	_check(too_wide.is_empty(), "every card name's lines fit a creator card (56 pt) and a hotbar card: %s" % [too_wide])
	hero.member.hot_slots = ["move", "", "attack"]   # Edit hotbar cleared the middle slot
	f.select(hero)
	f.hud.refresh()
	var bar: Array = f.hud._hotbar.get_children()
	_check(bar.size() == Rules.HOTBAR_SLOTS and bar[1].get_class() == "Control" and bar[1].get_script() != bar[0].get_script() and bar[2].k.id == "attack", "a cleared slot stays empty and the cards keep their slots")
	hero.member.erase("hot_slots")
	var ls := f.flip_check(0, 1)
	var ls2 := f.flip_check(1, 2)
	_check(ls.coins.size() == 2 and ls.need == 2 and ls2.need == 3, "the long shot: 0 coins needing 1 is 2 heads in a row, 1 needing 2 is 3")

	# Wood elf: Mel's +1 hex per Move, and the party walks faster and spends less clock.
	_check(f.move_hexes(mel) == 4 and f.move_hexes(fluffy) == 3 and f.move_hexes(chelm) == 2, "a Move: 2, +1 a DEX point over 1, +1 wood elf: Mel (DEX 2, wood elf) %d, Fluffy (DEX 2) %d, Chelmsford (DEX 1) %d" % [f.move_hexes(mel), f.move_hexes(fluffy), f.move_hexes(chelm)])
	_check(is_equal_approx(game.step_minutes(), Rules.STEP_MINUTES * Rules.WOOD_ELF_CLOCK), "with Mel in the party a hex costs %.2f min" % game.step_minutes())

	# Claw Swipe (Fluffy): DEX attack, 2 damage, bleed 1 at the start of the foe's next 2 turns.
	var line := _free_line(5)
	_check(not line.is_empty(), "found a free line of 5 on the map")
	if line.is_empty():
		_done()
		return
	var s: Vector2i = line[0]
	var dv: Vector2i = Hex.NEIGHBOURS[line[1]]
	_clear_round(s, [])
	_place(fluffy, s)
	_place(foe, s + dv)
	foe.hp = foe.max_hp
	_check(f.attack_coins(fluffy, foe, Cards.get_card("claw_swipe")) == 2, "Claw Swipe flips Fluffy's DEX (2)")
	var hp: int = foe.hp
	await _play(fluffy, "claw_swipe", foe.cell, [true, true])
	_check(hp - foe.hp == Rules.CLAW_DAMAGE and foe.bleed_turns == Rules.DOT_TURNS, "Claw Swipe: %d damage, bleeding %d turns" % [hp - foe.hp, foe.bleed_turns])
	hp = foe.hp
	await f._turn_starts(foe)
	_check(hp - foe.hp == Rules.DOT_DAMAGE and foe.bleed_turns == 1, "bleed ticks 1 at the start of its turn")

	# Breath Weapon (Chelmsford, blue): a line of 4, allies included; DEX saves; half on a pass. Cat Reflexes for Fluffy.
	_clear_round(s, [])
	_place(chelm, s)
	_check(f.breath_line(chelm, line[1]).size() == 4, "blue breath reaches 4 hexes on open ground")
	_place(mel, s + dv * 2)
	_place(foe, s + dv * 4)
	foe.hp = foe.max_hp
	var mel_hp: int = mel.hp
	hp = foe.hp
	await _play(chelm, "breath", s + dv, [false, false, true, false])
	var dmg := Races.breath_damage(chelm.member, level)
	_check(mel_hp - mel.hp == dmg and hp - foe.hp == dmg / 2, "breath: Mel fails, takes %d; the foe saves, takes %d (half of %d)" % [mel_hp - mel.hp, hp - foe.hp, dmg])
	_check(chelm.ap == Rules.AP - 2 and chelm.used.has("breath"), "breath costs 2 AP, once per turn")
	_clear_round(s, [chelm, foe])
	_place(fluffy, s + dv * 2)
	var fl_hp: int = fluffy.hp
	await _play(chelm, "breath", s + dv, [false, false, true, true])
	_check(fl_hp - fluffy.hp == dmg / 2, "Cat Reflexes: Fluffy fails and takes half (%d)" % (fl_hp - fluffy.hp))
	fl_hp = fluffy.hp
	await _play(chelm, "breath", s + dv, [true, true, true])
	_check(fl_hp == fluffy.hp, "Cat Reflexes: Fluffy passes and takes none")
	mel.hp = mel.max_hp
	fluffy.hp = fluffy.max_hp

	await _card_checks(hero, fluffy, chelm, mel, foe, s, line[1])
	await _hero_checks(hero, fluffy, foe, s, line[1], level)
	await _cover_checks()
	_done()


## 03 and 04's card rules (Ethan, Nov 5, 2026): facing and Backstab, the slows, Shield Bash's push, stacking poison.
func _card_checks(hero: Dictionary, fluffy: Dictionary, chelm: Dictionary, mel: Dictionary, foe: Dictionary, s: Vector2i, d: int) -> void:
	var dv: Vector2i = Hex.NEIGHBOURS[d]
	# Facing: a foe faces whoever it last attacked or the way it last moved.
	_clear_round(s, [])
	_fresh(foe)
	_place(foe, s + dv)
	_place(mel, s)
	Coins.forced.assign([false, false, false, false, false, false])
	f.phase = "enemies"
	await f._attack(foe, mel, Cards.get_card("attack", "spear"))
	Coins.forced.clear()
	_check(foe.facing == (d + 3) % 6, "a foe faces whoever it last attacked")
	await f._walk(foe, [s + dv * 2])
	_check(foe.facing == d, "and the way it last moved")
	# Backstab: Mel in the hex behind it, +2 on the first dagger hit each turn.
	_place(mel, s + dv)   # foe at s + 2dv faces d: behind it is s + dv
	_check(f.behind(mel, foe), "Mel stands behind the foe")
	var hp: int = foe.hp
	await _play(mel, "attack", foe.cell, [true, true])
	_check(hp - foe.hp == Races.score(mel.member, "DEX") + Rules.BACKSTAB, "Backstab: %d damage from behind (DEX %d + %d)" % [hp - foe.hp, Races.score(mel.member, "DEX"), Rules.BACKSTAB])
	foe.facing = d   # Mel's hit doesn't turn it
	hp = foe.hp
	Coins.forced.assign([true, true])
	await f.press_button()
	Coins.forced.clear()
	_check(hp - foe.hp == Races.score(mel.member, "DEX"), "only the first dagger hit each turn (%d)" % (hp - foe.hp))
	# Poison Blade: every hit this turn poisons, and the poisons stack.
	_fresh(foe)
	await _play(mel, "poison_blade", null, [])
	mel.ap = Rules.AP
	f.pick_card("attack")
	await f.click_cell(foe.cell)
	for i in 2:
		Coins.forced.assign([true, true])
		await f.press_button()
	Coins.forced.clear()
	hp = foe.hp
	await f._turn_starts(foe)
	_check(foe.poison.size() == 2 and hp - foe.hp == 2 * Rules.DOT_DAMAGE, "Poison Blade: 2 hits stack, %d damage at the turn's start" % (hp - foe.hp))
	# Slows: Frost Ray -1, Bonebreaker -2, until the foe's next turn ends; no prone.
	_fresh(foe)
	_clear_round(s, [])
	_place(fluffy, s)
	_place(foe, s + dv * 2)
	await _play(fluffy, "frost_ray", foe.cell, [true, true, true])
	_check(f.move_hexes(foe) == Rules.MOVE_HEXES - Rules.FROST_SLOW and foe.lost_ap == 0, "Frost Ray slows the foe to %d hexes, and doesn't knock it prone" % f.move_hexes(foe))
	_place(chelm, s + dv)
	await _play(chelm, "bonebreaker", foe.cell, [true, true])
	_check(f.move_hexes(foe) == maxi(Rules.MOVE_HEXES - Rules.BONEBREAKER_SLOW, 0), "Bonebreaker slows it to %d hexes" % f.move_hexes(foe))
	f.phase_no += 2
	_check(f.move_hexes(foe) == Rules.MOVE_HEXES, "the slow ends after its next turn")
	# Shield Bash: push 1 hex away; blocked behind, it stays.
	_fresh(foe)
	_clear_round(s, [])
	_place(hero, s)
	_place(foe, s + dv)
	await _play(hero, "shield_bash", foe.cell, [true, true, true])
	_check(foe.cell == s + dv * 2 and foe.lost_ap == 0, "Shield Bash pushes the foe 1 hex, no stun")
	_place(foe, s + dv)
	_place(fluffy, s + dv * 2)
	await _play(hero, "shield_bash", foe.cell, [true, true, true])
	_check(foe.cell == s + dv, "with the hex behind taken, it stays put")
	_fresh(foe)
	_fresh(mel)
	_fresh(fluffy)


func _hero_checks(hero: Dictionary, fluffy: Dictionary, foe: Dictionary, s: Vector2i, d: int, level: int) -> void:
	var dv: Vector2i = Hex.NEIGHBOURS[d]
	var m: Dictionary = hero.member
	_clear_round(s, [])
	_place(hero, s)
	_place(foe, s + dv)
	_fresh(foe)
	match String(m.race):
		"Halfling":
			_check(m.lucky == Rules.LUCKY_CHARGES, "Lucky starts with %d charges" % m.lucky)
			var hp: int = foe.hp
			await _play(hero, "attack", foe.cell, [false, false, false, true])   # misses by 1; Lucky reflips a tail to heads
			_check(m.lucky == Rules.LUCKY_CHARGES - 1 and foe.hp < hp, "Lucky turns the hero's miss by 1 into a hit (charges %d)" % m.lucky)
			var hhp: int = hero.hp
			Coins.forced.assign([true, false, false])   # the foe hits with exactly 1 heads; Lucky reflips it to tails
			f.phase = "enemies"
			await f._attack(foe, hero, Cards.get_card("attack", "spear"))
			_check(hero.hp == hhp and m.lucky == Rules.LUCKY_CHARGES - 2, "Lucky turns a foe's exact hit into a miss (charges %d)" % m.lucky)
			Coins.forced.assign([true, true])   # 2 heads: one reflip can't change it, so no charge spent
			await f._attack(foe, hero, Cards.get_card("attack", "spear"))
			Coins.forced.clear()
			_check(m.lucky == Rules.LUCKY_CHARGES - 2, "Lucky doesn't fire when one reflip can't change the result")
			_place(fluffy, s - dv)
			await _play(hero, "duck_behind", fluffy.cell, [])
			_check(hero.cell == s - dv and fluffy.cell == s, "Duck Behind swaps the hero and Fluffy")
		"Elf":
			if m.sub == "Wood elf":
				_check(f.move_hexes(hero) == Rules.MOVE_HEXES + 1, "wood elf hero moves %d hexes" % f.move_hexes(hero))
			elif m.spell == "Glimmerstep":
				var spots := f.blink_cells(hero)
				_check(not spots.is_empty() and spots.all(func(c): return Rules.hex_distance(c, hero.cell) <= 3 and f.grid[c].kind != "lava"), "Glimmerstep lands up to 3 away, never on lava")
				var to: Vector2i = spots[0]
				await _play(hero, "glimmerstep", to, [])
				_check(hero.cell == to and hero.mini.visible, "Glimmerstep: the hero reappears %d hexes away" % Rules.hex_distance(to, s))
			elif m.spell == "Faerie Fire":
				var before := f.attack_coins(hero, foe, Cards.get_card("attack"))
				await _play(hero, "faerie_fire", foe.cell, [false, false])
				_check(f.on(foe, "glow") and f.attack_coins(hero, foe, Cards.get_card("attack")) == before + 1, "Faerie Fire: the foe glows, attacks on it flip 1 more")
				f.phase_no += 2
				_check(not f.on(foe, "glow"), "the glow ends by the caster's next turn")
			elif m.spell == "Lull":
				await _play(hero, "lull", foe.cell, [false, false])
				_check(foe.lull, "Lull: the foe dozes on a failed WIS save")
				await f._hurt(foe, 0)
				_check(foe.lull, "no damage, still dozing")
				var hhp: int = hero.hp
				f.end_phase()
				if f.hud.confirm_open():
					f.confirm_end()
				while not (f.phase == "allies" and not f.busy) and f.active:
					await get_tree().process_frame
				_check(not foe.lull and (hero.hp == hhp or f.dist(foe, hero) > 1), "the dozing foe loses its attack and wakes (hero HP %d to %d)" % [hhp, hero.hp])
				await _play(hero, "lull", foe.cell, [false, false])
				await f._hurt(foe, 1)
				_check(not foe.lull, "any damage wakes it")
		"Dwarf":
			if m.sub == "Forge dwarf":
				_check(f.attack_coins(hero, foe, Cards.get_card("attack")) == Races.score(m, "STR") + 1 and f.attack_coins(hero, foe, Cards.get_card("shield_bash")) == Races.score(m, "STR") + 1, "forge dwarf: +1 coin on Attack and weapon cards")
			else:
				_check(m.max_hp == Rules.PARTY[0].hp + Rules.SHIELD_DWARF_HP, "shield dwarf: %d max HP at level 1" % m.max_hp)
				var mhp: int = m.max_hp
				var chp: int = m.hp
				game._add_xp(game.xp_needed())
				_check(m.max_hp == mhp + 1 and m.hp == chp + 1, "shield dwarf: +1 max and current HP on a level-up")
		"Golem":
			match String(m.sub):
				"Metal":
					_check(f.reduction(hero) == Rules.METAL_REDUCTION, "metal golem: reduction %d" % f.reduction(hero))
					var hhp: int = hero.hp
					Coins.forced.assign([true, true, true, true, true])
					f.phase = "enemies"
					await f._attack(foe, hero, Cards.get_card("attack", "spear"))
					Coins.forced.clear()
					var hit: int = foe.damage if foe.damage >= 0 else foe.score
					_check(hhp - hero.hp == maxi(hit - Rules.METAL_REDUCTION, 0), "a hit of %d takes %d off" % [hit, hhp - hero.hp])
					await _play(hero, "lockdown", null, [])
					_check(f.reduction(hero) == 2 * Rules.METAL_REDUCTION and f.reachable(hero).is_empty(), "Lockdown doubles it and the hero can't move")
				"Wood":
					hero.hp = hero.max_hp - 3
					await f._turn_starts(hero)
					_check(hero.hp == hero.max_hp - 3 + Rules.REGROWTH, "Regrowth heals %d at the turn's start" % Rules.REGROWTH)
				"Stone":
					_place(foe, s + dv * 4)
					var hp: int = foe.hp
					_check(f.in_reach(hero, foe, Cards.get_card("stone_throw")), "Stone Throw reaches 4")
					await _play(hero, "stone_throw", foe.cell, [true, true, true])
					_check(hp - foe.hp == Rules.RACIAL_DAMAGE, "Stone Throw: %d damage" % (hp - foe.hp))
		"Dragonborn":
			_place(foe, s + dv * 2)
			var hp: int = foe.hp
			await _play(hero, "breath", s + dv, [false, false])
			var dmg := Races.breath_damage(m, level)
			_check(hp - foe.hp == dmg, "%s breath: %d damage on a fail" % [m.sub, hp - foe.hp])
			match String(m.sub):
				"Red":
					_check(dmg == Rules.BREATH_DAMAGE + Rules.BREATH_RED, "red hits harder: %d" % dmg)
				"White":
					_check(f.move_hexes(foe) == Rules.MOVE_HEXES - 1, "white slows: the foe moves %d" % f.move_hexes(foe))
					f.phase_no += 2
					_check(f.move_hexes(foe) == Rules.MOVE_HEXES, "the slow ends after the foe's next turn")
				"Black":
					_check(f.attack_coins(hero, foe, Cards.get_card("attack")) == Races.score(m, "STR") + 1, "black acid: attacks on it flip 1 more")
				"Green":
					hp = foe.hp
					await f._turn_starts(foe)
					await f._turn_starts(foe)
					await f._turn_starts(foe)
					_check(hp - foe.hp == Rules.DOT_DAMAGE * Rules.DOT_TURNS, "green poison: %d damage over its next 2 turns" % (hp - foe.hp))
		"Tiefling":
			match String(m.sub):
				"Hayes":
					_place(foe, s + dv * 4)
					var hp: int = foe.hp
					_check(f.attack_coins(hero, foe, Cards.get_card("scorch")) == Races.score(m, "CHA"), "Scorch flips CHA")
					await _play(hero, "scorch", foe.cell, [true, true, true])
					_check(hp - foe.hp == Rules.RACIAL_DAMAGE, "Scorch: %d damage at range 4" % (hp - foe.hp))
				"Conley":
					_place(fluffy, s + dv * 3)
					fluffy.hp = 2
					await _play(hero, "ember_mend", fluffy.cell, [])
					_check(fluffy.hp == 2 + Rules.EMBER_MEND_LOW, "Ember Mend heals %d below half HP" % (fluffy.hp - 2))
					await _play(hero, "ember_mend", fluffy.cell, [])
					_check(fluffy.hp == mini(fluffy.max_hp, 2 + Rules.EMBER_MEND_LOW + Rules.EMBER_MEND), "and %d above" % Rules.EMBER_MEND)
				"Keegan":
					await _play(hero, "guiding_ember", null, [])
					_check(hero.ap == Rules.AP - 1 and hero.used.has("guiding_ember"), "Guiding Ember plays (1 AP) and reveals nothing yet")
		"Human":
			_check(Races.cards(m).is_empty(), "Human: Versatile changes nothing for a Fighter, no card")
	_check(Races.cards(m).all(func(id): return id in hero.cards), "the hero's racial cards are in All actions: %s" % [Races.cards(m)])
	for u in f.allies():
		var want: Array = ["move", "attack"] + Races.cards(u.member)
		_check(u.hot.size() == mini(Rules.HOTBAR_SLOTS, u.cards.size()) and u.hot.slice(0, want.size()) == want, "%s's starting bar: %s" % [u.name, u.hot])


## Cover (design/03 -> Combat -> Cover) on a map with brush and blocked cells.
func _cover_checks() -> void:
	var shooter: Dictionary = _who("Fluffy")
	var foe: Dictionary = f.units.filter(func(u): return not u.ally)[0]
	_fresh(foe)
	_fresh(shooter)
	var found := {}
	for a: Vector2i in f.grid:
		if f.grid[a].kind != "open":
			continue
		for d in Hex.NEIGHBOURS:
			var b: Vector2i = a + d
			var c: Vector2i = a + d * 2
			if not (f.cover.has(b) and f.grid.has(c) and f.grid[c].kind == "open" and f.grid[c].z == f.grid[a].z and f.grid[b].z <= f.grid[a].z):
				continue
			var kind: String = f.cover[b]
			if found.has(kind):
				continue
			_clear_round(a, [])
			_place(shooter, a)
			_place(foe, c)
			var t := f.cover_between(shooter, foe)
			if kind == "partial":
				_check(t == "partial" and f.attack_coins(shooter, foe, Cards.get_card("firebolt")) == 2 and f.save_coins(foe, shooter, "DEX") == Rules.ENEMY_SAVE_COINS + 1, "partial cover (%s): Firebolt flips 2, the foe saves with 3" % f.grid[b].kind)
			else:
				_check(t == "full" and not f.in_reach(shooter, foe, Cards.get_card("firebolt")), "full cover: can't aim through")
			found[kind] = true
	print("RACE cover cases on %s: %s" % [f.map_id, found.keys()])


## The details panel at its short height (design/07 -> Combat screen: everything it can show must fit): every card of every
## member in its fullest states, with the longest foe name. Prints FIT lines (height needed of the panel's, widest line of
## its 146), worst first; with --shots, the worst ones to screens/race/fit_*.png.
func _panel_fit() -> void:
	var hud: CombatHud = f.hud
	print("FIT layout: screen %s, details %s, bar %s, cards %s, all actions %s" % [hud.get_viewport_rect().size, hud._details_panel.get_global_rect(), hud._hotbar_row.get_global_rect(), hud._hotbar.get_child_count(), hud._hotbar_row.get_child(1).get_global_rect()])
	var foe: Dictionary = f.units.filter(func(u): return not u.ally)[0]
	foe.name = "[Bandit archer A]"   # the longest foe name in Foes.MIX
	var rows := []
	for u in f.allies():
		for id: String in u.cards:
			for state in ["picked", "target", "used_note", "result"]:
				_turn(u)
				f.pick_card(id)
				var k := f.card()
				u.blessed = state != "picked"
				foe.glow = f.phase_no if state != "picked" else -1
				if state != "picked":
					match k.kind:
						"attack", "save":
							f.target = foe
						"ally":
							f.ally_target = _who("Chelmsford") if u.name != "Chelmsford" else _who("Fluffy")
						"breath":
							f.breath_dir = 0
						"cell":
							var spots := f.blink_cells(u)
							f.cell_target = spots[0] if not spots.is_empty() else null
						"self":
							f.self_done = id if state == "result" else ""
				if state in ["used_note", "result"]:   # a played card shows its result with the used note under the button
					u.used[id] = true
					u.used_fight[id] = true
				if state == "result":
					var n: int = f.attack_coins(u, foe, k) if k.kind == "attack" else (f.save_coins(foe, u, k.get("save", "DEX")) if k.kind == "save" else 0)
					var miss: Array[bool] = []
					for i in n:
						miss.append(false)
					match k.kind:
						"attack":
							f.result = {coins = miss, title = "Hit!", good = true, sub = "Damage: 12 [placeholder]"}
						"save":
							f.result = {coins = miss, title = "Saved: half damage", good = false, sub = "Damage: 12 [placeholder]"}
						"ally":
							f.result = {coins = [], title = "Blessed", good = true, sub = "%s flips an extra coin on their next check." % "Chelmsford"}
				hud.refresh()
				await get_tree().process_frame
				await get_tree().process_frame
				var box: Control = hud._details_panel.get_child(0)
				var need: float = box.get_combined_minimum_size().y + 24.0
				var wide := 0.0
				for c in hud._details.get_children() + hud._button_box.get_children():
					wide = maxf(wide, c.get_combined_minimum_size().x)
				rows.append([need, wide, u.name, id, state])
				if "--shots" in OS.get_cmdline_user_args() and (need > CombatHud.DETAILS_H - 16.0 or wide > 146.5):
					await _shot("fit_%s_%s_%s" % [u.name.replace("[", "").replace("]", "").replace(" ", "_"), id, state])
				u.blessed = false
				f.result = {}
	rows.sort_custom(func(a, b): return a[0] > b[0])
	var over := rows.filter(func(r): return r[0] > CombatHud.DETAILS_H or r[1] > 146.5)
	for r in rows.slice(0, 12) + over:
		print("FIT %.0f of %.0f, widest %.0f of 146: %s %s %s" % [r[0], CombatHud.DETAILS_H, r[1], r[2], r[3], r[4]])
	print("FIT %d states, %d over" % [rows.size(), over.size()])


## The art's cover data on line pieces (art/handoff/combat_cover_data.md), on one map: `-- --racecheck --covermap=<id>`.
## Counts what each piece gives and finds a shot through each kind.
func _cover_data_checks() -> void:
	var data: Dictionary = CombatMap.all()[f.map_id]
	var pieces: Array = data.placements.filter(func(p): return p.has("cover"))
	print("RACE cover data on %s: %d pieces (%s), %d partial and %d full cells, %d low edges" % [f.map_id, pieces.size(),
			", ".join(pieces.map(func(p): return p.cover)), f.cover.values().count("partial"), f.cover.values().count("full"), f.edge_cover.size()])
	var shooter := _who("Fluffy")
	var foe: Dictionary = f.units.filter(func(u): return not u.ally)[0]
	_fresh(foe)
	var found := {}
	for p in pieces:
		for c in p.get("cells", []):
			var b := Vector2i(int(c[0]), int(c[1]))
			for d in Hex.NEIGHBOURS:
				var a: Vector2i = b - d
				var t: Vector2i = b + d
				if found.has(p.cover) or not (f.grid.has(a) and f.grid.has(t) and f.grid[a].kind == "open" and f.grid[t].kind == "open" and f.unit_at(a).is_empty() and f.unit_at(t).is_empty() and absf(f.grid[a].z - f.grid[t].z) < 0.01):
					continue
				_place(shooter, a)
				_place(foe, t)
				var got: String = f.cover_between(shooter, foe)
				_check(got == ("full" if p.cover == "wall" else "partial"), "%s: a shot over its cell gets %s cover" % [p.cover, got])
				found[p.cover] = true
		for e in p.get("edges", []):
			var c1 := Vector2i(int(e[0][0]), int(e[0][1]))
			var c2 := Vector2i(int(e[1][0]), int(e[1][1]))
			var d: Vector2i = c2 - c1
			var a: Vector2i = c1 - d
			var t: Vector2i = c2 + d
			var key := "edge %s" % ("flat" if f.grid[c1].z == f.grid[c2].z else "curb")
			# A clean case: one step, each side level, no cover on the cells, no other edge on the line.
			if found.has(key) or not (f.grid.has(a) and f.grid.has(t) and f.grid[a].kind == "open" and f.grid[t].kind == "open" and f.unit_at(a).is_empty() and f.unit_at(t).is_empty()):
				continue
			if f.grid[a].z != f.grid[c1].z or f.grid[t].z != f.grid[c2].z or f.cover.has(c1) or f.cover.has(c2) or f.edge_cover.has([a, c1] if a < c1 else [c1, a]) or f.edge_cover.has([c2, t] if c2 < t else [t, c2]):
				continue
			var low: Vector2i = a if f.grid[c1].z <= f.grid[c2].z else t
			var high: Vector2i = t if low == a else a
			_place(shooter, low)
			_place(foe, high)
			var up: String = f.cover_between(shooter, foe)
			_place(shooter, high)
			_place(foe, low)
			var down: String = f.cover_between(shooter, foe)
			if key == "edge flat":
				_check(up == "partial" and down == "partial", "a flat low edge: partial both ways (%s, %s)" % [up, down])
			else:
				_check(up != "none" and down == "none", "a terrace curb: %s from below, %s from the top" % [up, down])
			found[key] = true
	print("RACE cover data cases: %s" % [found.keys()])


func _done() -> void:
	var bot := FightBot.new(get_tree())
	for u in f.units:
		if not u.ally:
			u.hp = 0
			u.down = true
	f._check_end()
	while not game.after.visible:
		await get_tree().process_frame
	game.after.done.emit()
	while game.busy:
		if game.level_pick.visible:
			game.level_picked(game._pick_options[0])
		await get_tree().process_frame
	for m in game.party:
		m.hp = m.max_hp
	await _wait(0.5)
	await _fight("plains_trees")
	var r := await bot.play(f)
	print("RACE BOT %s %s: %d rounds, party HP %d to %d, %d down%s; played %s" % [game.party[0].race, game.party[0].sub, r.rounds, r.hp0, r.hp1, r.downs, ", WIPED" if r.wiped else "", bot.used])
	if game.party[0].has("lucky"):
		game.rest_here()
		_check(game.party[0].lucky == Rules.LUCKY_CHARGES, "Lucky's charges come back on rest")
	print("RACE DONE: %d failed" % failed)
	get_tree().quit()
