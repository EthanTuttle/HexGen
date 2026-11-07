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
	u.disarmed = false
	f.board.stand(u.mini)
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
	u.dance_ready = false
	u.quick_ready = false
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
	if "--minishot" in OS.get_cmdline_user_args():   # the hero kit's mini with the hero's gear, close up in a fight
		var h := Hero.new()
		h.race = game.run.race if game.run.race != "" else "Human"
		h.klass = game.run.klass
		h.gear = {"main": game.party[0].weapon, "off": game.party[0].off, "armour": game.party[0].armour}
		h.appearance = {"race": h.race, "build": "Average", "head": 0, "hair": 0}
		Hero.current = h
		await _fight("plains_stones")
		var me: Dictionary = f.units[0]
		f.select(me)
		game.rig.ease_to(f.global_position + me.mini.position + Vector3(0, 0.6, 0), 11.0, game.rig.yaw_deg + 150.0)
		await _wait(1.2)
		await _shot("mini_%s_%s" % [h.klass, h.gear.main])
		Hero.current = null
		get_tree().quit()
		return
	if "--covercompare" in OS.get_cmdline_user_args():   # test aid: threaded cover gives today's meshes, array for array
		if "--coverforest" in OS.get_cmdline_user_args():   # the debug map of every forest and farmland region
			game.spawn_forest_regions()
			await _wait(1.0)
		var map: MapBoard = game.map
		var jobs := []
		for t: Vector2i in map.terrains:
			var job := map._cover_job(t)
			if not job.is_empty():
				jobs.append(job)
		var t0 := Time.get_ticks_usec()
		var old := []
		for job: Array in jobs:   # today's path: one tile at a time, Piece.mesh()
			old.append(GroundCover._piece(GroundCover.tile_items(map.terrains, map.water_shapes, job[0], job[1], job[2]), map.terrains).mesh())
		var t1 := Time.get_ticks_usec()
		var made := GroundCover.build_tiles(map.terrains, map.water_shapes, jobs)
		var t2 := Time.get_ticks_usec()
		var same := 0
		var verts := 0
		for k in jobs.size():
			var a: Mesh = old[k]
			var b: Mesh = made[k].mesh
			var ok := a.get_surface_count() == b.get_surface_count()
			if ok and a.get_surface_count() > 0:
				var aa := a.surface_get_arrays(0)
				var bb := b.surface_get_arrays(0)
				for i in Mesh.ARRAY_MAX:
					ok = ok and aa[i] == bb[i]
				ok = ok and a.surface_get_format(0) == b.surface_get_format(0) and a.surface_get_material(0) == b.surface_get_material(0)
				verts += (aa[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
			same += 1 if ok else 0
		_check(same == jobs.size(), "cover: %d of %d tiles' threaded meshes match today's exactly (%d vertices)" % [same, jobs.size(), verts])
		print("RACE cover timing: %d tiles, one at a time %.0f ms, threaded %.0f ms" % [jobs.size(), (t1 - t0) / 1000.0, (t2 - t1) / 1000.0])
		print("RACE DONE: %d failed" % failed)
		get_tree().quit()
		return
	if "--fallshots" in OS.get_cmdline_user_args():   # test aid: a foe falls, then shrinks away, in frames
		await _fight("plains_stones")
		var foe: Dictionary = f.units.filter(func(u): return not u.ally)[0]
		game.rig.ease_to(f.global_position + foe.mini.position + Vector3(0, 0.4, 0), 7.0, game.rig.yaw_deg)
		await _wait(1.0)
		f._hurt.call_deferred(foe, foe.hp)
		for i in 16:
			await _shot("fall_%d" % i)
			await _wait(0.1)
		get_tree().quit()
		return
	if "--popupshots" in OS.get_cmdline_user_args():   # test aid: Victory, the end panel and the level pick, on the map
		var drawn: Array[String] = ["plains", "forest", "river", "hills"]
		game.after.show_result(game, true, {}, drawn, [], 8)
		await _wait(5.0)   # the rewards' reveal
		await _shot("popup_victory")
		game.after.visible = false
		game.end_panel.open()
		await _shot("popup_end")
		game.end_panel.visible = false
		game.level_pick.open(2, ["plains", "forest", "river"])
		await _shot("popup_level")
		game.level_pick.open(4, ["plains", "forest", "river"], game.party.duplicate())
		await _shot("popup_level4")
		game.level_pick.place(String(game.party[0].ability))
		await _shot("popup_level4_placed")
		game.level_pick.next()
		await _shot("popup_level4_fluffy")
		get_tree().quit()
		return
	if "--wizardshots" in OS.get_cmdline_user_args():   # test aid: a Wizard's fight with a summon, both decoys and the circle
		await _wizard_shots()
		get_tree().quit()
		return
	if "--statusshots" in OS.get_cmdline_user_args():   # test aid: the status chips on the markers
		await _status_shots()
		get_tree().quit()
		return
	if "--panelshots" in OS.get_cmdline_user_args():
		await _panel_shots()
		get_tree().quit()
		return
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
	_check(f.attack_score(hero, Cards.get_card("attack")) == Races.score(hero.member, Weapons.of(hero.weapon).ab), "the hero's attack flips their own %s (%s)" % [Weapons.of(hero.weapon).ab, hero.weapon])
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
	await _gear_checks(hero, fluffy, foe, s, line[1])
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


## Gear in play (06 -> Start; 04): armour, ranges and the ranged penalty, the hero's weapon's cards, the Ranger's class
## cards. Run with `--class=ranger --main=<weapon> --off=<...> --armour=<tier>` to check each weapon.
func _gear_checks(hero: Dictionary, fluffy: Dictionary, foe: Dictionary, s: Vector2i, d: int) -> void:
	var dv: Vector2i = Hex.NEIGHBOURS[d]
	var m: Dictionary = hero.member
	var w: Dictionary = Weapons.of(hero.weapon)
	print("RACE gear: %s %s / %s, armour %s, heads to hit %d, cards %s" % [m.klass, hero.weapon, hero.off, m.armour, hero.heads, hero.cards])
	var expect_heads: int = (1 + ceili(Races.score(m, "CON") / 2.0) + (1 if hero.off == "shield" else 0)) if Weapons.armoured(m.armour) else maxi(ceili(Races.score(m, "DEX") / 2.0), 1)
	_check(hero.heads == expect_heads, "armour: foes need %d heads to hit the hero (Armoured 1 + half CON up, +1 shield; Clothes half DEX up)" % expect_heads)
	var dh := func(armour: String, off: String, scores: Dictionary) -> int: return Weapons.defence_heads({"armour": armour, "off": off, "scores": scores})
	_check(dh.call("Light", "", {"CON": 1}) == 2 and dh.call("Light", "", {"CON": 2}) == 2 and dh.call("Medium", "", {"CON": 3}) == 3 and dh.call("Heavy", "", {"CON": 5}) == 4
		and dh.call("Medium", "shield", {"CON": 2}) == 3, "armour: Armoured CON 1-2 needs 2, CON 3 needs 3, CON 5 needs 4, a shield adds 1")
	_check(dh.call("none", "", {"DEX": 1}) == 1 and dh.call("none", "", {"DEX": 2}) == 1 and dh.call("none", "", {"DEX": 3}) == 2 and dh.call("none", "", {"DEX": 6}) == 3,
		"armour: Clothes DEX 1-2 needs 1, DEX 3 needs 2, DEX 6 needs 3")
	_check(_who("Fluffy").heads == 1 and _who("Chelmsford").heads == 3 and _who("Mel").heads == 1, "companions: Fluffy and Mel in Clothes (DEX 2: 1 heads), Chelmsford Armoured with a shield (CON 2: 3)")
	_check(hero.cards.filter(func(id): return not id in Races.cards(m) and not id in game.run.spells) == Weapons.cards_for(m.klass, hero.weapon, hero.off), "the hero's cards come from class and gear (plus the racial card and spell picks)")
	_check(f.card("attack").range == w.range or hero != f.current, "the basic attack reaches %d with a %s" % [w.range, hero.weapon])
	_check(hero.max_hp == Weapons.CLASS_HP[m.klass] + Races.extra_hp(m, 1), "%s HP %d" % [m.klass, hero.max_hp])
	_clear_round(s, [])
	_fresh(foe)
	_place(hero, s)
	_place(foe, s + dv)
	f.select(hero)
	var atk := f.card("attack")
	var expect: int = Races.score(m, w.ab) + Races.forge_coin(m, atk)
	_check(f.attack_coins(hero, foe, atk) == expect, "armour: foes wear none, so the hero flips all %d coins" % expect)
	_check(f.save_coins(hero, {}, "DEX") == Races.score(m, "DEX"), "armour costs no save coins")
	if w.get("ranged", false):
		_check(f.heads_needed(foe, hero, atk) == foe.heads + (0 if w.get("point_blank", false) else Rules.RANGED_ADJACENT), "a ranged shot with a foe next to you needs %d heads (%s)" % [f.heads_needed(foe, hero, atk), "Point Blank" if w.get("point_blank", false) else "+1"])
		_place(foe, s + dv * 3)
		_check(f.heads_needed(foe, hero, atk) == foe.heads and f.in_reach(hero, foe, atk), "and none from 3 away, in reach")
	if m.klass == "ranger":
		_check("hunters_mark" in hero.cards and "snare" in hero.cards and hero.hot.slice(2, 4) == ["hunters_mark", "snare"] if Races.cards(m).is_empty() else true, "the Ranger starts with Hunter's Mark and Snare on the bar: %s" % [hero.hot])
		var run := RunSetup.new()
		run.klass = "ranger"
		run.background = "noble"
		_check(run.deck_cards().get("forest", 0) == 6 and run.deck_cards().get("plains", 0) == 6 and run.deck_cards().get("farmland", 0) == 6, "the Ranger's deck: forest 5, plains 5, plus the background's (and one of each)")
		# Hunter's Mark: any foe in sight, no roll; +1 on every hit on it; moving it off a downed foe is free.
		_fresh(foe)
		_place(foe, s + dv * (3 if w.get("ranged", false) else 1))
		await _play(hero, "hunters_mark", foe.cell, [])
		_check(hero.mark == foe and hero.ap == Rules.AP - 1, "Hunter's Mark: marked, 1 AP")
		var hp: int = foe.hp
		var plain: int = Races.score(m, w.ab) + (Weapons.VERSATILE_TWO_HANDED if w.hands == "v" and hero.off in ["", "none"] else 0)
		await _play(hero, "attack", foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
		var off_marked: int = _offhand_damage(hero) + Rules.MARK_DAMAGE if Fight.dual_wields(hero) else 0   # the free offhand hit takes the Mark too
		_check(hp - foe.hp == plain + Rules.MARK_DAMAGE + off_marked, "a hit on the marked foe deals %d (%d + %d, offhand %d)" % [hp - foe.hp, plain, Rules.MARK_DAMAGE, off_marked])
		foe.down = true
		_turn(hero)
		hero.used["hunters_mark"] = true
		_check(f.ap_cost(hero, f.card("hunters_mark")) == 0 and f.cant_use(hero, f.card("hunters_mark")) == "", "moving the mark off a downed foe is free")
		_fresh(foe)
		# Snare: an empty walkable hex up to 3 away; a foe walks in, stops, takes 1 and is snared; allies don't set it off.
		_clear_round(s, [])
		_place(hero, s)
		var trap: Vector2i = s + dv * 2
		await _play(hero, "snare", trap, [])
		_check(f.snares.get(hero.name) == trap, "the Snare is set 2 hexes away")
		_place(fluffy, s + dv * 3)
		await f._walk(fluffy, [trap, s + dv])
		_check(f.snares.has(hero.name), "an ally walks over it without setting it off")
		_place(fluffy, s - dv * 3)
		_place(foe, s + dv * 4)
		hp = foe.hp
		await f._walk(foe, [s + dv * 3, trap, s + dv])
		_check(foe.cell == trap and hp - foe.hp == Rules.SNARE_DAMAGE and f.move_hexes(foe) == 0 and not f.snares.has(hero.name), "a foe walking through stops on it, takes %d and is snared" % (hp - foe.hp))
		f.phase_no += 2
		_check(f.move_hexes(foe) == Rules.MOVE_HEXES, "the snare ends after its next turn")
	if m.klass == "rogue":
		await _rogue_checks(hero, fluffy, foe, s, d)
	if m.klass == "wizard":
		await _wizard_checks(hero, fluffy, foe, s, d)
	if Fight.dual_wields(hero):
		await _dual_checks(hero, fluffy, foe, s, d)
	await _weapon_card_checks(hero, fluffy, foe, s, d)
	await _ambush_checks(hero, fluffy, foe, s, d)


## The Rogue (06 -> Start, Nov 6, 2026): Sneak Attack and Poison Blade on the bar, Clothes, the swamp and village deck, and
## Sneak Attack doubling the weapon's damage on a flanked foe, before Backstab's +2 (03).
func _rogue_checks(hero: Dictionary, fluffy: Dictionary, foe: Dictionary, s: Vector2i, d: int) -> void:
	var dv: Vector2i = Hex.NEIGHBOURS[d]
	var m: Dictionary = hero.member
	var w: Dictionary = Weapons.of(hero.weapon)
	_check(not Weapons.armoured(m.armour), "the Rogue wears Clothes")
	_check("sneak_attack" in hero.cards and "poison_blade" in hero.cards and hero.hot.slice(2, 4) == ["sneak_attack", "poison_blade"] if Races.cards(m).is_empty() else true, "the Rogue starts with Sneak Attack and Poison Blade on the bar: %s" % [hero.hot])
	var run := RunSetup.new()
	run.klass = "rogue"
	run.background = "noble"
	_check(run.deck_cards().get("swamp", 0) == 6 and run.deck_cards().get("village", 0) == 6 and run.deck_cards().get("farmland", 0) == 6, "the Rogue's deck: swamp 5, village 5, plus the background's (and one of each)")
	var plain: int = Races.score(m, w.ab)
	var far := 3 if w.get("ranged", false) else 1
	var tough: int = foe.max_hp
	_check(f.card("sneak_attack").range == w.range, "Sneak Attack reaches as far as the %s (%d)" % [hero.weapon, w.range])
	# Not flanked: the plain damage.
	hero.mark = {}
	_clear_round(s, [])
	_fresh(foe)
	foe.max_hp = 60
	foe.hp = 60
	_place(hero, s)
	_place(foe, s + dv * far)
	_place(fluffy, s - dv * 3)
	foe.facing = _facing_from(foe, s)   # facing the Rogue: no Backstab
	var hp: int = foe.hp
	await _play(hero, "sneak_attack", foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
	var off_hit: int = hp - foe.hp - plain
	_check(off_hit == _offhand_damage(hero), "Sneak Attack on a foe nobody flanks: %d (the weapon's %d)" % [hp - foe.hp, plain])
	# Flanked: doubled.
	_fresh(foe)
	foe.max_hp = 60
	foe.hp = 60
	foe.facing = _facing_from(foe, s)
	_place(fluffy, s + dv * (far + 1))
	hp = foe.hp
	await _play(hero, "sneak_attack", foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
	off_hit = hp - foe.hp - plain * Rules.SNEAK_TIMES
	_check(off_hit == _offhand_damage(hero), "Sneak Attack on a flanked foe: %d (the weapon's %d doubled)" % [hp - foe.hp, plain])
	if hero.weapon == "dagger":
		# From behind too: doubled, then Backstab's +2.
		_fresh(foe)
		foe.max_hp = 60
		foe.hp = 60
		foe.facing = (_facing_from(foe, s) + 3) % 6
		hero.backstabbed = false
		hp = foe.hp
		await _play(hero, "sneak_attack", foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
		off_hit = hp - foe.hp - (plain * Rules.SNEAK_TIMES + Rules.BACKSTAB)
		_check(f.behind(hero, foe) and off_hit == _offhand_damage(hero), "flanked and from behind with a dagger: %d (%d doubled, + %d Backstab)" % [hp - foe.hp, plain, Rules.BACKSTAB])
	foe.max_hp = tough
	_fresh(foe)
	_place(fluffy, s - dv * 3)


## The Wizard (06 -> Start; 03 -> Wizard spells and Wizard level-1 placeholders, Ethan, Nov 6, 2026): Clothes, 6 HP, the
## hills and ruins deck, the two picks on the bar; spell damage from INT; summons, concentration, Warding Circle and the
## decoys, the foes' side played by the real enemy phase.
func _wizard_checks(hero: Dictionary, fluffy: Dictionary, foe: Dictionary, s: Vector2i, d: int) -> void:
	var dv: Vector2i = Hex.NEIGHBOURS[d]
	var m: Dictionary = hero.member
	var smart: int = Races.score(m, "INT")
	var all := [true, true, true, true, true, true, true, true, true, true, true, true]
	_check(not Weapons.armoured(m.armour) and Weapons.CLASS_HP.wizard == 6, "the Wizard wears Clothes and starts on 6 HP")
	_check(game.run.spells.size() == 2 and game.run.spells.all(func(id): return id in hero.cards and id in hero.hot), "the Wizard's two picks are on the bar: %s" % [hero.hot])
	var run := RunSetup.new()
	run.klass = "wizard"
	run.background = "noble"
	_check(run.deck_cards().get("hills", 0) == 6 and run.deck_cards().get("ruins", 0) == 6 and run.deck_cards().get("farmland", 0) == 6, "the Wizard's deck: hills 5, ruins 5, plus the background's (and one of each)")
	var bolt := Cards.get_card("attack", "wand")
	_check(bolt.n == "Magic Bolt" and bolt.range == Rules.SPELL_RANGE and bolt.ranged and Weapons.of("wand").ab == "INT", "a wand's basic attack is Magic Bolt: ranged, %d hexes, INT" % bolt.range)
	var tough: int = foe.max_hp
	_clear_round(s, [])
	_fresh(foe)
	foe.max_hp = 60
	foe.hp = 60
	_place(hero, s)
	_place(foe, s + dv * 3)
	# Damage spells: INT plus the card's bonus (Firebolt +1, Blood Bolt +2); Blood Bolt costs 2 HP and can't take you to 0.
	for row: Array in [["firebolt", 1], ["frost_ray", 0], ["blood_bolt", 2]]:
		var hp: int = foe.hp
		var mine: int = hero.hp
		await _play(hero, row[0], foe.cell, all)
		_check(hp - foe.hp == smart + row[1], "%s deals INT %d + %d: %d" % [row[0], smart, row[1], hp - foe.hp])
		if row[0] == "blood_bolt":
			_check(mine - hero.hp == Rules.BLOOD_BOLT_HP, "Blood Bolt costs %d HP" % (mine - hero.hp))
		if row[0] == "frost_ray":
			_check(f.on(foe, "slowed"), "Frost Ray slows on a hit")
	hero.hp = Rules.BLOOD_BOLT_HP
	_turn(hero)
	_check(f.cant_use(hero, f.card("blood_bolt")) == "Not enough HP", "Blood Bolt can't be cast on %d HP" % hero.hp)
	_fresh(hero)
	_fresh(foe)
	foe.max_hp = 60
	foe.hp = 60
	_place(foe, s + dv)
	var hp0: int = foe.hp
	await _play(hero, "shocking_grasp", foe.cell, all)
	_check(hp0 - foe.hp == smart and foe.cell == s + dv * 2, "Shocking Grasp: INT %d damage, and the foe is pushed 1 hex" % (hp0 - foe.hp))
	# Summons: an empty hex beside you, the player's to act with from this turn, 2 AP; they hit with the caster's INT coins.
	_clear_round(s, [])
	_place(hero, s)
	_place(foe, s + dv * 4)
	await _play(hero, "animated_blade", s + dv, [])
	var blade := f.unit_at(s + dv)
	_check(not blade.is_empty() and Fight.is_summon(blade) and blade.hp == 4 and blade.ap == Rules.SUMMON_AP and hero.conc.get("unit", {}) == blade,
			"Animated Blade: beside you, 4 HP, 2 AP this turn, held by concentration")
	_check(f.allies().has(blade) and f.foes_of(foe).has(blade), "a summon is an ally, and foes can pick it as a target")
	_fresh(foe)
	_place(foe, s + dv * 2)
	_check(f.attack_coins(blade, foe, Cards.get_card("attack", blade.weapon)) == smart, "the Blade flips the caster's INT coins (%d)" % smart)
	hp0 = foe.hp
	await _play(blade, "attack", foe.cell, all)
	_check(hp0 - foe.hp == 2, "the Blade hits for 2: %d" % (hp0 - foe.hp))
	_place(fluffy, s + dv * 3)
	_check(f._flanked(fluffy, foe), "a summon next to the foe flanks it")
	_place(fluffy, s - dv * 4)
	_turn(hero)
	var spot: Vector2i = f.cell_options(hero, Cards.get_card("wisp"))[0]
	await _play(hero, "wisp", spot, [])
	var wisp := f.unit_at(spot)
	_check(not blade in f.units and not wisp.is_empty() and hero.conc.id == "wisp", "a new summon ends the old one: one at a time")
	_check(wisp.hp == 2 and wisp.member.flies and Cards.get_card("attack", wisp.weapon).range == 4, "Wisp: 2 HP, flies, zaps at 4 hexes")
	await f._hurt(hero, hero.hp)
	_check(hero.down and not wisp in f.units and hero.conc.is_empty(), "the caster going down ends the summon")
	_fresh(hero)
	await _play(hero, "animated_blade", s + dv, [])
	blade = f.unit_at(s + dv)
	await f._hurt(blade, blade.hp)
	_check(not blade in f.units and hero.conc.is_empty(), "a destroyed summon is gone, and so is the concentration")
	# Warding Circle: 7 hexes within 5; allies inside take 1 less a hit; another concentration spell ends it.
	_clear_round(s, [])
	_place(hero, s)
	_place(foe, s + dv)
	await _play(hero, "warding_circle", s, [])
	var ring: int = 1 + Hex.NEIGHBOURS.filter(func(n): return f.grid.has(s + n)).size()   # fewer at the map's edge
	_check(f.circles.has(hero.name) and f.circles[hero.name].cells.size() == ring and f.warded(hero), "Warding Circle: the hex and its neighbours on the map (%d)" % ring)
	var spear := Cards.get_card("attack", "spear")
	var mine: int = hero.hp
	Coins.forced.assign(all)
	await f._one_attack(foe, hero, spear)
	var inside: int = mine - hero.hp
	hero.hp = hero.max_hp
	_place(hero, s + dv * 3)
	_place(foe, s + dv * 4)
	mine = hero.hp
	Coins.forced.assign(all)
	await f._one_attack(foe, hero, spear)
	var outside: int = mine - hero.hp
	Coins.forced.clear()
	_check(outside - inside == Rules.WARDING_LESS, "inside the circle a foe's hit does %d less (%d, outside %d)" % [Rules.WARDING_LESS, inside, outside])
	hero.hp = hero.max_hp
	_place(hero, s)
	_turn(hero)
	await _play(hero, "animated_blade", f.cell_options(hero, Cards.get_card("animated_blade"))[0], [])
	_check(not f.circles.has(hero.name), "casting a summon ends the circle")
	f._end_conc(hero)
	# Decoys, against the real enemy phase with one foe left standing.
	var others := f.units.filter(func(u): return not u.ally and u != foe and not u.down)
	for u in others:
		u.down = true
	_clear_round(s, [])
	_place(hero, s)
	_place(foe, s + dv)
	_fresh(foe)
	var room: int = Hex.NEIGHBOURS.filter(func(n): return f.grid.has(s + n) and f.grid[s + n].kind in ["open", "brush"] and f.unit_at(s + n).is_empty()).size()
	await _play(hero, "mirror_image", null, [])
	var copies := f.units.filter(func(u): return u.decoy == "mirror")
	_check(copies.size() == mini(Rules.MIRROR_COPIES, room) and copies.size() > 0 and copies.all(func(c): return Rules.hex_distance(c.cell, s) == 1),
			"Mirror Image: %d copies on the free hexes next to you (%d free)" % [copies.size(), room])
	_check(not f.allies().any(func(u): return u.decoy != "") and not f.foes_of(foe).any(func(u): return u.decoy != ""), "decoys aren't allies: no flanking, and foes don't pick them by themselves")
	mine = hero.hp
	Coins.forced.assign([false, false])   # the foe's INT save fails
	await f._enemy_phase()
	Coins.forced.clear()
	_check(hero.hp == mine and f.units.filter(func(u): return u.decoy == "mirror").size() == copies.size() - 1, "a foe that fails its INT save hits a copy, which pops")
	_fresh(foe)
	Coins.forced.assign([true, true] + all)   # it sees through, and hits
	await f._enemy_phase()
	Coins.forced.clear()
	_check(hero.hp < mine, "a foe that passes it hits you")
	for u in f.units.duplicate():
		if u.decoy != "":
			f._vanish(u)
	hero.hp = hero.max_hp
	_fresh(foe)
	_place(foe, s + dv * 4)
	await _play(hero, "phantom_ally", s + dv * 2, [])
	var phantom := f.unit_at(s + dv * 2)
	_check(not phantom.is_empty() and phantom.decoy == "phantom", "Phantom Ally stands on an empty hex within 5")
	mine = hero.hp
	Coins.forced.assign([false, false] + all)   # fooled: it goes for the phantom
	await f._enemy_phase()
	Coins.forced.clear()
	_check(not phantom in f.units and hero.hp == mine, "a fooled foe goes for the phantom, and one hit pops it")
	await _play(hero, "phantom_ally", s + dv * 2, [])
	phantom = f.unit_at(s + dv * 2)
	await f._hurt(phantom, 0)
	_check(not phantom in f.units, "an area hit pops it too")
	for u in others:
		u.down = false
	foe.max_hp = tough
	_fresh(foe)
	_fresh(hero)
	_place(fluffy, s - dv * 3)


## Shots for Ethan (screens/race/wizard_*.png): Warding Circle under the party, the Animated Blade beside the Wizard with
## its small portrait, Mirror Image's copies and a Phantom Ally out front; then a foe's turn against them.
func _wizard_shots() -> void:
	await _fight("plains_stones")
	var hero: Dictionary = f.units[0]
	var open := func(c: Vector2i) -> bool: return f.grid.has(c) and f.grid[c].kind == "open" and not f.cover.has(c)
	var s := Vector2i.ZERO
	var d := 0
	for c: Vector2i in f.grid:   # a spot with all 6 neighbours open and a clear line of 6 ahead, so the whole circle shows
		for k in 6:
			if Hex.NEIGHBOURS.all(func(n): return open.call(c + n)) and range(1, 7).all(func(i): return open.call(c + Hex.NEIGHBOURS[k] * i)):
				s = c
				d = k
	var dv: Vector2i = Hex.NEIGHBOURS[d]
	var foes := f.units.filter(func(u): return not u.ally)
	_clear_round(s, [])
	_place(hero, s)
	_place(_who("Fluffy"), s - dv)
	for i in foes.size():
		_place(foes[i], s + dv * (5 + i % 2) + Hex.NEIGHBOURS[(d + 1) % 6] * (i / 2))
	var mid := f.global_position + f.cell_point(s + dv * 2)
	await _play(hero, "warding_circle", s, [])
	await _play(hero, "mirror_image", null, [])
	await _play(hero, "phantom_ally", s + dv * 3, [])
	_turn(hero)
	f.pick_card("move")
	game.rig.ease_to(mid, 19.0, game.rig.yaw_deg)
	await _wait(1.2)
	await _shot("wizard_circle_decoys")
	game.rig.ease_to(f.global_position + f.cell_point(s), 9.0, game.rig.yaw_deg)
	await _wait(1.0)
	await _shot("wizard_copies_close")
	var spots := f.cell_options(hero, Cards.get_card("animated_blade"))
	spots.sort_custom(func(a, b): return Rules.hex_distance(a, s + dv * 5) < Rules.hex_distance(b, s + dv * 5))
	await _play(hero, "animated_blade", spots[0], [])   # the summon ends the circle: one concentration at a time (03)
	_turn(hero)
	f.pick_card("move")
	game.rig.ease_to(mid, 19.0, game.rig.yaw_deg)
	await _wait(1.2)
	await _shot("wizard_summon_decoys")
	f.select(f.summon_of(hero))
	f.pick_card("attack")
	game.rig.ease_to(mid, 19.0, game.rig.yaw_deg)
	await _wait(1.0)
	await _shot("wizard_summon_turn")
	_turn(hero)
	f.pick_card("wisp")
	await _wait(0.4)
	await _shot("wizard_ends_prompt")
	hero.hot[2] = "blood_bolt"
	_turn(hero)
	f.pick_card("blood_bolt")
	await _wait(0.4)
	await _shot("wizard_blood_bolt")


## Ambush and unaware (03 -> Ambush, Unaware; Ethan, Nov 6, 2026): a pass leaves every foe unaware of the whole party, a
## fail lets the foes go first; a hostile action ends a foe's unawareness of that character only (Hunter's Mark is quiet);
## foes that started unaware lose 1 AP on their first turn, hit or not; Sneak Attack doubles on an unaware foe.
func _ambush_checks(hero: Dictionary, fluffy: Dictionary, foe: Dictionary, s: Vector2i, d: int) -> void:
	var dv: Vector2i = Hex.NEIGHBOURS[d]
	var m: Dictionary = hero.member
	var w: Dictionary = Weapons.of(hero.weapon)
	var far := 3 if w.get("ranged", false) else 1
	var tough: int = foe.max_hp
	var foes := f.units.filter(func(u): return not u.ally)
	var names := f.allies().map(func(a): return String(a.member.name))
	_check(Ambush.apply(f.units, false) and foes.all(func(u): return u.unaware.is_empty() and not u.ambushed), "a failed ambush: nobody unaware, and the foes go first")
	_check(not Ambush.apply(f.units, true) and foes.all(func(u): return u.ambushed and names.all(func(n): return n in u.unaware)), "a passed ambush: every foe unaware of every ally, and the party goes first")
	_check(Ambush.is_unaware(foe, hero) and not Ambush.is_unaware(hero, foe) and not Ambush.is_unaware(foe, foe), "only foes are unaware, and only of allies")
	hero.mark = {}
	_clear_round(s, [])
	_fresh(foe)
	foe.max_hp = 60
	foe.hp = 60
	_place(hero, s)
	_place(foe, s + dv * far)
	_place(fluffy, s - dv * 3)
	foe.facing = _facing_from(foe, s)   # facing the hero: no Backstab
	_turn(hero)
	var icon: Array = f.status_icons(foe).filter(func(i): return i[1] == "Unaware")
	_check(icon.size() == 1 and icon[0][2] == "Hasn't noticed %s" % hero.name, "the icon line on the hero's turn: %s" % [icon])
	if m.klass == "ranger":
		await _play(hero, "hunters_mark", foe.cell, [])
		_check(hero.mark == foe and Ambush.is_unaware(foe, hero), "Hunter's Mark is quiet: the foe stays unaware")
		hero.mark = {}
	var hp: int = foe.hp
	var plain: int = Races.score(m, w.ab) + (Weapons.VERSATILE_TWO_HANDED if w.hands == "v" and hero.off in ["", "none"] else 0)
	var id := "sneak_attack" if m.klass == "rogue" else "attack"
	await _play(hero, id, foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
	var off: int = hp - foe.hp - plain * (Rules.SNEAK_TIMES if m.klass == "rogue" else 1)
	if m.klass == "rogue":
		_check(off == _offhand_damage(hero), "Sneak Attack on an unaware foe nobody flanks: %d (the weapon's %d doubled)" % [hp - foe.hp, plain])
	_check(not Ambush.is_unaware(foe, hero) and Ambush.is_unaware(foe, fluffy), "a hit ends its unawareness of the hero only")
	_turn(fluffy)
	_check(f.status_icons(foe).any(func(i): return i[1] == "Unaware" and i[2] == "Hasn't noticed %s" % fluffy.name), "on Fluffy's turn it still hasn't noticed Fluffy")
	# A miss is a hostile action too.
	foe.unaware = [hero.name]
	await _play(hero, "attack", foe.cell, [false, false, false, false, false, false, false, false, false, false, false, false])
	_check(not Ambush.is_unaware(foe, hero), "a miss ends it too")
	# Its first turn: 1 AP less, though it was already hit; once only.
	_check(foe.ambushed and Ambush.first_turn_ap(foe) == Ambush.LOST_AP and Ambush.first_turn_ap(foe) == 0, "ambushed foes lose %d AP on their first turn only, hit or not" % Ambush.LOST_AP)
	if m.klass == "ranger":
		# The Snare's damage is the Ranger's: it notices the Ranger, not the others.
		foe.unaware = names.duplicate()
		_clear_round(s, [])
		_fresh(foe)
		_place(hero, s)
		var trap: Vector2i = s + dv * 2
		await _play(hero, "snare", trap, [])
		_place(foe, s + dv * 4)
		await f._walk(foe, [s + dv * 3, trap, s + dv])
		_check(not Ambush.is_unaware(foe, hero) and Ambush.is_unaware(foe, fluffy), "springing the Snare notices the Ranger only")
	for u in foes:
		u.unaware = []
		u.ambushed = false
	foe.max_hp = tough
	_fresh(foe)
	_place(fluffy, s - dv * 3)


## Dual-wielding (04; Ethan, Nov 6, 2026): once a turn, right after a main-hand hit, the offhand makes a free attack on the
## same foe at full strength; nothing after a miss.
func _dual_checks(hero: Dictionary, fluffy: Dictionary, foe: Dictionary, s: Vector2i, d: int) -> void:
	var dv: Vector2i = Hex.NEIGHBOURS[d]
	var m: Dictionary = hero.member
	var plain: int = Races.score(m, Weapons.of(hero.weapon).ab)
	var tough: int = foe.max_hp
	hero.mark = {}
	_clear_round(s, [])
	_fresh(foe)
	foe.max_hp = 60
	foe.hp = 60
	_place(hero, s)
	_place(foe, s + dv)
	foe.facing = _facing_from(foe, s)
	var hp: int = foe.hp
	await _play(hero, "attack", foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
	_check(hp - foe.hp == plain + _offhand_damage(hero) and hero.ap == Rules.AP - 1, "dual-wielding: a hit, then the offhand's free hit (%d + %d), for 1 AP" % [plain, _offhand_damage(hero)])
	hp = foe.hp
	Coins.forced.assign([true, true, true, true, true, true, true, true, true, true, true, true])
	f.pick_card("attack")
	await f.click_cell(foe.cell)
	await f.press_button()
	Coins.forced.clear()
	_check(hp - foe.hp == plain, "the free hit comes once a turn (%d)" % (hp - foe.hp))
	hp = foe.hp
	await _play(hero, "attack", foe.cell, [false, false, false, false, false, false, true, true, true, true, true, true])
	_check(hp - foe.hp == 0, "no free hit after a miss")
	foe.max_hp = tough
	_fresh(foe)


## The direction from u toward cell c (for setting a foe's facing).
func _facing_from(u: Dictionary, c: Vector2i) -> int:
	for k in Hex.NEIGHBOURS.size():
		if Rules.hex_distance(u.cell + Hex.NEIGHBOURS[k], c) < Rules.hex_distance(u.cell, c):
			return k
	return 0


## The free offhand hit's damage, if the hero dual-wields (04), else 0: its own weapon's score, with no doubling or Backstab.
func _offhand_damage(hero: Dictionary) -> int:
	return Races.score(hero.member, f.offhand_card(hero).ab) if Fight.dual_wields(hero) else 0


## The hero's weapon's own card (04 -> Weapon category cards, Ethan's placeholders).
func _weapon_card_checks(hero: Dictionary, fluffy: Dictionary, foe: Dictionary, s: Vector2i, d: int) -> void:
	var dv: Vector2i = Hex.NEIGHBOURS[d]
	var m: Dictionary = hero.member
	var w: Dictionary = Weapons.of(hero.weapon)
	var plain: int = Races.score(m, w.ab) + (Weapons.VERSATILE_TWO_HANDED if w.hands == "v" and hero.off in ["", "none"] else 0)
	hero.mark = {}
	_clear_round(s, [])
	_fresh(foe)
	var tough: int = foe.max_hp
	foe.max_hp = 60   # so big hits don't down it before their riders show
	foe.hp = 60
	_place(hero, s)
	_place(foe, s + dv)
	var hp: int = foe.hp
	match String(hero.weapon):
		"longsword", "spear":
			if hero.off in ["", "none"]:
				await _play(hero, "attack", foe.cell, [true, true, true, true, true])
				_check(hp - foe.hp == Races.score(m, w.ab) + Weapons.VERSATILE_TWO_HANDED, "two-handed %s: +%d damage (%d)" % [hero.weapon, Weapons.VERSATILE_TWO_HANDED, hp - foe.hp])
			if hero.weapon == "spear":
				_place(foe, s + dv * 2)
				_check(f.in_reach(hero, foe, f.card("attack")) and f.card("throw").range == Weapons.THROW_RANGE, "spear: Reach 2, Throw 4")
		"shortsword":
			await _play(hero, "attack", foe.cell, [true, true, true, true, true])
			hp = foe.hp
			hero.ap = 1
			f.pick_card("quick_slash")
			_check(f.ap_cost(hero, f.card()) == 0, "Quick Slash is free right after a shortsword hit")
			Coins.forced.assign([true, true, true, true, true])
			await f.press_button()
			Coins.forced.clear()
			_check(hp - foe.hp == plain - Rules.QUICK_SLASH_LESS and hero.ap == 1, "and deals %d (1 less), costing nothing" % (hp - foe.hp))
		"rapier":
			await _play(hero, "disarm", foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
			_check(hp - foe.hp == plain + _offhand_damage(hero) and foe.lost_ap == Rules.DISARM_AP and foe.disarmed, "Disarm: a normal hit (%d) and the foe loses %d AP next turn" % [hp - foe.hp, foe.lost_ap])
			_fresh(foe)
			foe.lost_ap = 2
			await _play(hero, "disarm", foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
			_check(foe.lost_ap == 2, "with a bigger AP loss already on it, the larger counts")
			_fresh(foe)
			foe.disarmed = false
			var look: String = foe.member.mini
			foe.member.mini = "enemy_wolf"
			await _play(hero, "disarm", foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
			_check(foe.lost_ap == 0 and not foe.disarmed, "a wolf holds no weapon: Disarm only hits")
			foe.member.mini = look
		"scimitar":
			_turn(hero)
			_check(f.cant_use(hero, f.card("dancing_step")) != "", "Dancing Step waits for a scimitar attack")
			await _play(hero, "attack", foe.cell, [false, false, false, false, false])
			hero.ap = 1
			f.pick_card("dancing_step")
			var spots := f.cell_options(hero, f.card())
			_check(f.cant_use(hero, f.card()) == "" and spots.all(func(c): return Rules.hex_distance(c, s) <= Rules.DANCE_HEXES), "after any scimitar attack (a miss here), a free move of up to 2")
			await f.click_cell(spots[0])
			await f.press_button()
			_check(hero.cell == spots[0] and hero.ap == 1, "Dancing Step moves for 0 AP")
		"glaive":
			var foes: Array = f.units.filter(func(u): return not u.ally)
			for cell: Vector2i in f.grid:   # a hex with open ground all round, away from the board's edge
				if Hex.NEIGHBOURS.all(func(n): return f.grid.has(cell + n) and f.grid[cell + n].kind == "open" and f.unit_at(cell + n).is_empty()) and f.grid[cell].kind == "open":
					_clear_round(cell, [])
					_place(hero, cell)
					break
			var c: Vector2i = hero.cell + Hex.NEIGHBOURS[0]
			var arc := f.arc_cells(hero, c)
			var placed := 0
			for i in mini(arc.size(), foes.size()):
				_fresh(foes[i])
				_place(foes[i], arc[i])
				placed += 1 if f.grid[arc[i]].kind != "blocked" else 0
			var before: Array = foes.map(func(u): return u.hp)
			_turn(hero)
			Coins.forced.assign([true, true, true, true, true, true, true, true, true, true, true, true])
			f.pick_card("sweeping_arc")
			await f.click_cell(c)
			await f.press_button()
			Coins.forced.clear()
			var hit := 0
			for i in foes.size():
				if foes[i].hp < before[i]:
					hit += 1
			_check(arc.size() == 3 and hit == placed, "Sweeping Arc: 3 hexes in front, one flip each (%d of %d foes standing in it hit; arc %d, foes %d)" % [hit, placed, arc.size(), foes.size()])
		"shortbow":
			_place(foe, s + dv * 3)
			await _play(hero, "double_shot", foe.cell, [true, true, true, true, true, true, true, true, true, true])
			_check(hp - foe.hp == 2 * plain, "Double Shot: two hits of %d" % plain)
		"longbow":
			_place(foe, s + dv * 4)
			_check(f.card("attack").range == 8 and f.card("aimed_shot").ap == 3, "longbow: range 8, Aimed Shot 3 AP")
			var n := f.attack_coins(hero, foe, f.card("aimed_shot"))
			_check(n == Races.score(m, w.ab), "Aimed Shot ignores armour (%d coins)" % n)
			await _play(hero, "aimed_shot", foe.cell, [true, true, true, true, true])
			_check(hp - foe.hp == mini(hp, Rules.AIMED_TIMES * plain), "Aimed Shot: %d damage (4x)" % (hp - foe.hp))
		"crossbow":
			_place(foe, s + dv * 3)
			await _play(hero, "pinning_bolt", foe.cell, [true, true, true, true, true])
			_check(hp - foe.hp == plain and f.move_hexes(foe) == 0, "Pinning Bolt: a hit and the foe is snared")
		"gauntlets":
			await _play(hero, "guard_up", null, [])
			var hhp: int = hero.hp
			var fhp: int = foe.hp
			Coins.forced.assign([true, true, true, true, true, true])
			f.phase = "enemies"
			await f._attack(foe, hero, Cards.get_card("attack", "spear"))
			Coins.forced.clear()
			var hit: int = foe.damage if foe.damage >= 0 else foe.score
			_check(hhp - hero.hp == maxi(hit - Rules.GUARD_UP_LESS - f.reduction(hero), 0) and fhp - foe.hp == Races.score(m, w.ab), "Guard Up: %d less taken, and a hit back of %d" % [Rules.GUARD_UP_LESS, fhp - foe.hp])
		"knuckles":
			var coins: Array = [true]
			for i in maxi(f.attack_coins(hero, foe, Cards.get_card("haymaker")) - 1, 0):
				coins.append(false)
			await _play(hero, "haymaker", foe.cell, coins + [false, false, false, false, false, false, false, false])   # the save, then the offhand misses
			_check(hp - foe.hp == mini(hp, 2 * plain) and foe.lost_ap == Rules.HAYMAKER_AP, "Haymaker: double damage, and a failed CON save loses 1 AP")
		"wraps":
			_place(foe, s + dv * 3)
			_check(f.in_reach(hero, foe, f.card("step_strike")), "Step and Strike reaches a foe 3 away")
			await _play(hero, "step_strike", foe.cell, [true, true, true, true, true, true, true, true, true, true, true, true])
			_check(f.dist(hero, foe) == 1 and hp - foe.hp == plain + _offhand_damage(hero), "it steps next to it and hits (and the pair's free hit)")
		"dagger":
			_check(f.card("throw").range == Weapons.THROW_RANGE, "a thrown dagger reaches 4")
	foe.max_hp = tough
	_fresh(foe)


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


## Option B's panel in its fullest new states (design/07): a 3-target Breath Weapon result, and a long shot through cover.
## `-- --racecheck --statusshots --shots` saves screens/race/status_scene.png and status_close.png: a foe
## with 4 statuses (Unaware, Slowed, Poisoned, Marked) and an ally with 1 (Bleeding), on the hero's turn (07 -> Combat -> Rethink).
func _status_shots() -> void:
	await _fight("plains_stones")
	var hero: Dictionary = f.allies()[0]
	var fluffy := _who("Fluffy")
	var foe: Dictionary = f.units.filter(func(u): return not u.ally)[0]
	var mid := Vector2.ZERO
	for c: Vector2i in f.grid:
		mid += Vector2(c) / f.grid.size()
	var line := []   # the free line nearest the board's middle
	for c: Vector2i in f.grid:
		if f.grid[c].kind == "open" and not f.cover.has(c) and (line.is_empty() or Vector2(c).distance_to(mid) < Vector2(line[0]).distance_to(mid)):
			for d in 6:
				var ok := true
				for i in range(1, 3):
					var n: Vector2i = c + Hex.NEIGHBOURS[d] * i
					ok = ok and f.grid.has(n) and f.grid[n].kind == "open" and not f.cover.has(n) and f.grid[n].z == f.grid[c].z
				if ok:
					line = [c, d]
					break
	var s: Vector2i = line[0]
	var dv: Vector2i = Hex.NEIGHBOURS[line[1]]
	_clear_round(s, [])
	_place(hero, s)
	_place(foe, s + dv * 2)
	_place(fluffy, s + Hex.NEIGHBOURS[(line[1] + 1) % 6])
	_fresh(foe)
	foe.unaware = [String(hero.member.name)]
	foe.slowed = f.phase_no + 2
	foe.poison = [2]
	hero.mark = foe
	fluffy.bleed_turns = 2
	_turn(hero)
	game.rig.ease_to(f.global_position + (hero.mini.position + foe.mini.position) * 0.5, game.rig.distance, game.rig.yaw_deg)
	await _wait(0.8)
	await _shot("status_scene")
	# The close-up: the markers' corner of that same frame, at 2x with no smoothing, so its pixels show as drawn.
	var cam := game.rig.camera
	var pts := [hero, foe, fluffy].map(func(u): return cam.unproject_position(u.mini.global_position + Vector3(0, 1.75, 0)))
	var box := Rect2(pts[0], Vector2.ZERO)
	for p: Vector2 in pts:
		box = box.expand(p)
	box = box.grow_individual(40, 40, 70, 20)   # room for the hex and chips above each point, and chips beside
	var img := game.get_viewport().get_texture().get_image()
	var k: float = img.get_width() / game.get_viewport().get_visible_rect().size.x
	var px := Rect2i(Vector2i(box.position * k), Vector2i(box.size * k)).intersection(Rect2i(Vector2i.ZERO, img.get_size()))
	var crop := img.get_region(px)
	crop.resize(px.size.x * 2, px.size.y * 2, Image.INTERPOLATE_NEAREST)
	if "--shots" in OS.get_cmdline_user_args():
		crop.save_png(ProjectSettings.globalize_path("res://screens/race/status_close.png"))
	print("RACE status chips: foe %s, ally %s, screen scale %.2f" % [f.status_icons(foe).map(func(e): return e[1]), f.status_icons(fluffy).map(func(e): return e[1]), StatusChip._screen_scale()])


## `-- --racecheck --panelshots --shots` saves screens/race/panel_*.png.
func _panel_shots() -> void:
	await _fight("plains_stones")
	var chelm := _who("Chelmsford")
	var mel := _who("Mel")
	var foes: Array = f.units.filter(func(u): return not u.ally)
	var line := _free_line(5)
	var s: Vector2i = line[0]
	var dv: Vector2i = Hex.NEIGHBOURS[line[1]]
	_clear_round(s, [])
	_place(chelm, s)
	for i in mini(3, foes.size()):
		_fresh(foes[i])
		_place(foes[i], s + dv * (i + 1))
	_turn(chelm)
	f.pick_card("breath")
	await f.click_cell(s + dv)
	game.rig.ease_to(f.global_position + chelm.mini.position, game.rig.distance, game.rig.yaw_deg)
	await _wait(0.6)
	await _shot("panel_breath_aimed")
	Coins.forced.assign([false, false, true, false, false, true])
	await f.press_button()
	Coins.forced.clear()
	await _wait(0.3)
	await _shot("panel_breath_result")
	_check(f.result.rows.size() == 3, "the breath result lists 3 targets")
	var box: Control = f.hud._details_panel.get_child(0)
	_check(box.get_combined_minimum_size().y + 24.0 <= CombatHud.DETAILS_H, "the 3-target breath result fits the panel (%.0f of %.0f)" % [box.get_combined_minimum_size().y + 24.0, CombatHud.DETAILS_H])
	# A long shot through cover: Mel's Throw at a foe behind brush that needs 2 heads.
	var foe: Dictionary = foes[0]
	_fresh(foe)
	for a: Vector2i in f.grid:
		for d in Hex.NEIGHBOURS:
			var b: Vector2i = a + d
			var c: Vector2i = a + d * 2
			if f.grid[a].kind == "open" and f.cover.get(b, "") == "partial" and f.grid.has(c) and f.grid[c].kind == "open" and f.grid[c].z == f.grid[a].z and f.unit_at(a).is_empty() and f.unit_at(c).is_empty():
				_clear_round(a, [])
				_place(mel, a)
				_place(foe, c)
				foe.heads = 2
				_turn(mel)
				f.pick_card("throw")
				await f.click_cell(c)
				game.rig.ease_to(f.global_position + mel.mini.position, game.rig.distance, game.rig.yaw_deg)
				await _wait(0.6)
				await _shot("panel_longshot_aimed")
				print("RACE coin line: %s" % f.hud.coin_line(mel, foe, f.card()))
				Coins.forced.assign([true, true, false])
				await f.press_button()
				Coins.forced.clear()
				await _wait(0.3)
				await _shot("panel_longshot_result")
				_check(box.get_combined_minimum_size().y + 24.0 <= CombatHud.DETAILS_H, "the long-shot result fits the panel")
				return


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
			game.level_pick.bot_pick()
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
	await _score_step_checks()
	print("RACE DONE: %d failed" % failed)
	get_tree().quit()


## Score increases (03 -> Ability scores, Ethan, Nov 6, 2026): level 4's pick has each member place a point, one at a time,
## hero first, none above 6; then the terrain.
func _score_step_checks() -> void:
	var hero: Dictionary = game.party[0]
	var fluffy: Dictionary = game.party[1]
	fluffy.scores.INT = LevelPick.CAP
	game.level = 3
	game.xp = 0
	for m in game.party:
		Races.refresh_hp(m, 3)
	var before := game.party.map(func(m): return [m.max_hp, m.hp])
	game._add_xp(game.xp_needed())
	var grew := range(game.party.size()).map(func(i): return game.party[i].max_hp - before[i][0])
	var want := game.party.map(func(m): return Races.level_hp(m) + Races.extra_hp(m, 4) - Races.extra_hp(m, 3))
	_check(grew == want and range(game.party.size()).all(func(i): return game.party[i].hp - before[i][1] == grew[i]),
			"level 4: max HP and HP grow by class plus half CON (%s)" % [grew])
	_check(Races.level_hp({"klass": "fighter", "scores": {"CON": 2}}) * 3 + 12 == 24, "a CON 2 Fighter: 12 at level 1, 24 at level 4")
	var fl_class := Races.level_hp({"name": "Fluffy", "scores": {"CON": 1}})
	_check(fl_class == 2, "Fluffy levels as a Wizard (+1, +1 for CON 1)")
	game._next_pick()
	await _wait(0.2)
	var lp := game.level_pick
	_check(lp.visible and lp.step == 0 and lp._members.size() == game.party.size(), "level 4: each member places a point, hero first (%d)" % lp._members.size())
	_check(lp.find_children("*", "HexShape", true, false).is_empty(), "level 4: the terrain cards come after the points")
	lp.next()
	_check(lp.step == 0, "level 4: Next waits for the point")
	var dex := Races.score(hero, "DEX")
	var con := Races.score(hero, "CON")
	lp.place("CON")
	lp.place("DEX")   # moved: only the last tile tapped gets it
	await _shot("level4_hero")
	lp.next()
	_check(lp.step == 1, "level 4: on to Fluffy")
	lp.back()
	_check(lp.step == 0 and lp.placed.get(0, "") == "DEX", "level 4: Back returns to the hero, the point still placed")
	lp.place("CON")
	lp.place("DEX")
	lp.next()
	lp.place("INT")
	_check(not lp.placed.has(1), "level 4: a score at 6 takes no point")
	var tiles := lp.find_children("*", "Button", true, false).filter(func(x): return x.accessibility_name == "INT")
	_check(tiles.size() == 1 and tiles[0].disabled, "level 4: Fluffy's INT tile at 6 is dimmed")
	await _shot("level4_fluffy_capped")
	var others := {}
	for i in range(1, game.party.size()):
		var k: String = "DEX" if i == 1 else String(game.party[i].ability)
		others[i] = [k, Races.score(game.party[i], k)]
		lp.place(k)
		lp.next()
	var hexes := lp.find_children("*", "HexShape", true, false)
	_check(hexes.size() == 3 and hexes.all(func(h): return h.clickable), "level 4: then the terrain cards")
	await _shot("level4_terrain")
	var hand := game.deck.hand.size()
	game.level_picked(game._pick_options[0], lp.placed)
	_check(Races.score(hero, "DEX") == dex + 1 and Races.score(hero, "CON") == con, "level 4: hero DEX %d -> %d, CON unchanged" % [dex, Races.score(hero, "DEX")])
	_check(others.keys().all(func(i): return Races.score(game.party[i], others[i][0]) == others[i][1] + 1), "level 4: each companion's point lands on its pick")
	_check(Races.score(fluffy, "INT") == LevelPick.CAP, "level 4: Fluffy's INT stays at 6")
	_check(game.deck.hand.size() == hand + 1, "level 4: the terrain card still goes into the hand")
	_check(Hero.live == hero.scores, "checks outside combat read the levelled scores")
	game._add_xp(game.xp_needed())
	game._next_pick()
	await _wait(0.2)
	_check(lp._members.is_empty(), "level 5: no ability point")
	var tough := {"klass": "fighter", "scores": {"CON": 2}, "hp": 12, "max_hp": 12}
	Races.refresh_hp(tough, 4)
	var at4: int = tough.max_hp
	tough.hp -= 5
	tough.scores.CON = 3
	Races.refresh_hp(tough, 4)
	_check(at4 == 24 and tough.max_hp == 27 and tough.hp == 22, "CON 2 -> 3 at level 4 recounts levels 2-4: max HP 24 -> %d, HP 19 -> %d" % [tough.max_hp, tough.hp])
	var late: Dictionary = Rules.PARTY[3].duplicate(true)
	Races.join(late, 8)
	_check(Races.score(late, "DEX") == 4 and late.max_hp == Rules.PARTY[3].hp + Races.level_hp(late) * 7,
			"Mel joining at level 8: DEX 2 -> 4 from the points passed, HP %d" % late.max_hp)
	lp.bot_pick()
