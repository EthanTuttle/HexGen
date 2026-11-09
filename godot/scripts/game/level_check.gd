class_name LevelCheck
extends RaceCheck
## Checks levels 2 to 5 (`-- --levelcheck`, with `--class=` and gear for the hero; design/06 -> First playable -> Levels; picks:
## Progression): the test-only Level up now grants each level, every member makes that level's picks on the pick screen as
## the bots make them, and each level's gains land (mastery at 2, the class card or 2 spells at 3, a feat at 4, the
## subclass and its card at 5). Then every new card that's built is played once in a fight with set coins, a few passives
## and feats are read off the fight's numbers, and the fight bot plays a fight out. `--shots` saves each new pick screen and
## one pop-up to screens/levels/. Prints LEVEL OK / LEVEL FAIL lines, then LEVEL DONE. A test aid only.

const SMOKE := ["sweep", "overhand_cut", "sidestep", "rend", "rage", "wide_chop", "smite", "ground_pound", "vault", "heavy_bolt",
	"bolas_bolt", "shield_charge", "flame_burst", "chain_spark", "blood_ward", "hemorrhage", "holy_brand", "dawn_pulse",
	"curse_of_frailty", "bring_it", "divine_smite", "reposition", "arcane_shield", "fake_surrender", "vanish", "raise_the_stakes",
	"mage_hand", "fireball", "chain_lightning", "psychic_spike", "soul_siphon", "life_tap", "mass_heal", "miracle_of_plenty",
	"purify", "siphon_strength", "curse_of_ruin", "stone_skin", "toll_the_dead", "stone_sentinel", "soul_swap", "unbind",
	"killing_shot"]
var _shot_seen := {}


func _ready() -> void:
	_levels.call_deferred()


func _check(ok: bool, what: String) -> void:
	print("LEVEL %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


## `--shots`: the screen to screens/levels/<name>.png.
func _snap(name: String) -> void:
	if not "--shots" in OS.get_cmdline_user_args():
		return
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	var dir := ProjectSettings.globalize_path("res://screens/levels")
	DirAccess.make_dir_recursive_absolute(dir)
	game.get_viewport().get_texture().get_image().save_png(dir.path_join("%s.png" % name))


func _levels() -> void:
	await _wait(1.0)
	var lp := game.level_pick
	var names := game.party.map(func(m): return "%s (%s)" % [m.name, Progression.klass(m)])
	print("LEVEL party: %s" % [names])
	for level in range(2, 6):
		var cards_before := game.party.map(func(m): return m.cards.duplicate())
		game.level_up_now()
		await _wait(0.3)
		_check(game.level == level and lp.visible, "Level up now: level %d, its picks open" % level)
		var guard := 0
		while lp.visible and guard < 60:
			guard += 1
			var sec := _lp_section(lp)
			if sec == "terrain":
				game.level_picked(game._pick_options[0], lp.placed, lp.picks)
				break
			var who: Dictionary = game.party[lp._who()]
			var shot := "level%d_%s_%s" % [level, sec, Progression.klass(who)]
			if not _shot_seen.has(shot):
				_shot_seen[shot] = true
				await _snap(shot)
			if sec == "points":
				lp.place(String(who.ability) if Races.score(who, who.ability) < LevelPick.CAP else "CON")
			else:
				if not _shot_seen.has(shot + "_pop"):   # one pop-up per kind of step, before the pick so Choose shows
					_shot_seen[shot + "_pop"] = true
					var rows := lp.find_children("*", "Control", true, false).filter(func(n): return n.has_meta("key"))
					if not rows.is_empty():
						lp._focus = rows[0].get_meta("key")
						lp._build()
						await _snap(shot + "_pop")
						lp._focus = ""
						lp._build()
				_lp_auto(lp)
				if sec in ["spells", "feat", "subclass", "gain"]:
					await _snap(shot + "_picked")
			lp.next()
		await _wait(0.2)
		_check(not lp.visible, "level %d: the picks close after the terrain card" % level)
		for i in game.party.size():
			var m: Dictionary = game.party[i]
			var gained: Array = m.cards.filter(func(id): return not id in cards_before[i])
			_check(int(m.get("levelled", 1)) == level, "%s: level %d's picks made" % [m.name, level])
			match level:
				2:
					var want := Progression.martial(m)
					_check(m.get("mastery", []).size() == (1 if want else 0), "%s: %s mastery node at level 2 (%s)" % [m.name, "one" if want else "no", m.get("mastery", [])])
				3:
					if Progression.klass(m) in Progression.CASTERS:
						_check(gained.size() == Progression.SPELL_PICKS_3, "%s: 2 level-3 spells (%s)" % [m.name, gained])
					else:
						_check(Progression.LEVEL3_CARD[Progression.klass(m)] in m.cards, "%s: has its level-3 class card" % m.name)
				4:
					var feat := Progression.feat_of(Progression.feat(m))
					_check(not feat.is_empty() and Progression.missing(m, feat, game.run.background) == "", "%s: a feat it qualifies for (%s)" % [m.name, Progression.feat(m)])
				5:
					var sub := Progression.sub(m)
					_check(Progression.SUBCLASSES[Progression.klass(m)].has(sub), "%s: subclass %s" % [m.name, sub])
					if Progression.DEFAULT_SUBCLASS.has(m.name):
						_check(sub == Progression.DEFAULT_SUBCLASS[m.name], "%s: the bots keep the default subclass" % m.name)
					var s: Dictionary = Progression.SUBCLASSES[Progression.klass(m)][sub]
					if s.has("card"):
						_check(s.card in m.cards, "%s: gains %s" % [m.name, Cards.ALL[s.card].n])
					else:
						_check(gained.size() == 1 and gained[0] in (Progression.WIZARD_T1 if Progression.klass(m) == "wizard" else Progression.CLERIC_T1)[sub],
								"%s: a tier-1 spell of %s (%s)" % [m.name, sub, gained])
	var mel := game.party.filter(func(m): return m.name == "Mel")
	if not mel.is_empty():
		_check(Progression.card_for(mel[0], Cards.get_card("poison_blade")).n == "Sleeping Draught", "Mel's Poison Blade shows as Sleeping Draught")
	var ch := game.party.filter(func(m): return m.name == "Chelmsford")
	if not ch.is_empty():
		_check(Progression.sub(ch[0]) == "Order of Good", "Chelmsford stays Order of Good")
	_late_joiner_check()
	await _smoke()
	await _feat_numbers()
	await _bot_fight()
	print("LEVEL DONE: %d failed" % failed)
	get_tree().quit()


## A companion joining at level 5 has levels 2-5 picked for it, as the bots pick.
func _late_joiner_check() -> void:
	var late: Dictionary = Rules.PARTY[3].duplicate(true)
	Races.join(late, 5)
	Progression.catch_up(late, 5, "")
	_check(late.get("mastery", []).size() == 1 and Progression.feat(late) != "" and Progression.sub(late) == "Con Artist" and "fake_surrender" in late.cards,
			"Mel joining at level 5: mastery, feat and Con Artist made for her")


## Every new built card played once by the hero, set coins: attacks hit, saves fail.
func _smoke() -> void:
	await _fight("plains_stones")
	var hero: Dictionary = f.units[0]
	var line := _free_line(4)
	var s: Vector2i = line[0]
	var dv: Vector2i = Hex.NEIGHBOURS[line[1]]
	var foes := f.units.filter(func(u): return not u.ally)
	var foe: Dictionary = foes[0]
	var fluffy := _who("Fluffy")
	for id: String in SMOKE:
		_clear_round(s, [hero, foe, fluffy])
		for u in [hero, foe, fluffy]:
			_fresh(u)
		_place(hero, s)
		_place(foe, s + dv)
		_place(fluffy, s - dv)
		hero.off = "" if id in ["overhand_cut"] else hero.off
		hero.conc = {} if id != "unbind" and id != "soul_swap" else hero.conc
		if not id in hero.cards:
			hero.cards.append(id)
		if not id in hero.hot:
			hero.hot.append(id)
		var k: Dictionary = Progression.card_for(hero.member, Cards.get_card(id, hero.weapon))
		if id == "killing_shot":
			hero.mark = foe
			foe.hp = 1
		var at = null
		var coins: Array = []
		match k.kind:
			"attack":
				at = foe.cell
				coins.resize(12)
				coins.fill(true)
			"save":
				at = foe.cell
				coins.resize(12)
				coins.fill(false)
			"ally":
				at = fluffy.cell if id != "soul_swap" else f.summon_of(hero).get("cell", fluffy.cell)
			"arc":
				at = foe.cell
				coins.resize(12)
				coins.fill(true)
			"cell":
				var spots := f.cell_options(hero, k)
				at = spots[0] if not spots.is_empty() else null
			"self":
				coins.resize(12)
				coins.fill(false)
		_turn(hero)
		hero.ap = Rules.AP_CAP
		var why: String = f.cant_use(hero, k)
		_check(why == "" or why.begins_with("_"), "%s: usable (%s)" % [k.n, why])
		var foe_hp: int = foe.hp
		await _play(hero, id, at, coins)
		match id:
			"rage":
				_check(f.on(hero, "rage"), "Rage: raging until the hero's next turn")
			"sidestep":
				_check(f.heads_needed(hero) == Weapons.defence_heads(hero.member) + Rules.SIDESTEP_HEADS, "Sidestep: foes need 1 more heads")
			"bring_it":
				_check(foe.taunt == hero, "Bring It: the adjacent foe is taunted")
			"hemorrhage":
				_check(foe.bleed_turns > 0, "Hemorrhage: a failed save bleeds")
			"holy_brand":
				_check(foe.branded, "Holy Brand: a failed save brands")
			"fake_surrender":
				_check(hero.name in foe.unaware, "Fake Surrender: the foe is unaware of the hero")
			"stone_sentinel":
				_check(not f.summon_of(hero).is_empty() and f.summon_of(hero).taunts, "Stone Sentinel: a taunting summon")
			"raise_the_stakes":
				_check(hero.stakes and f.heads_needed(foe, hero) == foe.heads + 1, "Raise the Stakes: the next attack needs 1 more heads")
			"sweep", "smite", "divine_smite", "heavy_bolt", "overhand_cut", "killing_shot", "flame_burst", "fireball", "toll_the_dead", "psychic_spike":
				_check(foe.hp < foe_hp or foe.down, "%s: the foe takes damage (%d -> %d)" % [k.n, foe_hp, foe.hp])


## A few numbers read off the fight: Opening Strike's coin, Heavy Blade, Tough's HP.
func _feat_numbers() -> void:
	var hero: Dictionary = f.units[0]
	var foe: Dictionary = f.units.filter(func(u): return not u.ally)[0]
	var keep: String = hero.member.get("feat", "")
	hero.member.feat = "opening_strike"
	hero.opened = false
	var atk := Cards.get_card("attack", hero.weapon)
	_check(f.attack_mods(hero, foe, atk).any(func(m): return m.why == "opening"), "Opening Strike: +1 coin on the first attack")
	hero.opened = true
	_check(not f.attack_mods(hero, foe, atk).any(func(m): return m.why == "opening"), "Opening Strike: only the first")
	var m := {"klass": "fighter", "scores": {"CON": 2}, "hp": 12, "max_hp": 12, "feat": "tough"}
	Races.refresh_hp(m, 4)
	_check(m.max_hp == 24 + Rules.TOUGH_HP * 4, "Tough: +%d max HP a level (%d)" % [Rules.TOUGH_HP, m.max_hp])
	hero.member.feat = keep
	var unbuilt := Cards.get_card("ice_wall")
	_check(f.cant_use(hero, unbuilt) == "Not built yet", "a card that isn't built shows and can't be used")
	await _wait(0.1)


func _bot_fight() -> void:
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
	var bot := FightBot.new(get_tree())
	var r := await bot.play(f)
	print("LEVEL BOT: %d rounds, party HP %d to %d, %d down%s; played %s" % [r.rounds, r.hp0, r.hp1, r.downs, ", WIPED" if r.wiped else "", bot.used])
	_check(true, "a level-5 party plays a fight out")
