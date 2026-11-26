class_name RangerCheck
extends RaceCheck
## Checks the subclass cards built on Nov 22, 2026 (`-- --rangercheck --class=<class> --subclass=<name>`, and `--beast=` for a
## Companion; design/03 -> Martial class cards): levels the hero to 5 the bots' way with that subclass, then plays its cards with
## set coins. Elementalist: Infuse's pop-up (closing it cancels), each element's rider, Primal Snare's element when set and sprung.
## Arcane Trickster (`--class=rogue`): Magical Blade's damage at once. Companion: the beast on the board, its attack, Command
## Beast's signature move and Pack Mark. Shifter (`--form=`): Shift's swap of the hotbar, Rending Claws, the form's card,
## shifting back and Pounce. `--shots` saves the pop-ups and boards to screens/ranger/. Prints RANGER OK /
## RANGER FAIL lines, then RANGER DONE. A test aid only.


## The Shifter's test hero per form: hair (the fur) and cloth, from the kit's swatches.
const SHIFTER_LOOKS := {"Werewolf": ["#5A3A26", "#5E8F5A"], "Werebear": ["#9A6A3A", "#3E6F8C"], "Werecat": ["#D9B26A", "#B5532F"]}


func _check(ok: bool, what: String) -> void:
	print("RANGER %s: %s" % ["OK" if ok else "FAIL", what])
	if not ok:
		failed += 1


func _shot(name: String) -> void:
	if not "--shots" in OS.get_cmdline_user_args():
		return
	for _f in 3:
		await get_tree().process_frame
	await StallWatch.drawn(get_tree())
	var dir := ProjectSettings.globalize_path("res://screens/ranger")
	DirAccess.make_dir_recursive_absolute(dir)
	game.get_viewport().get_texture().get_image().save_png(dir.path_join("%s.png" % name))


func _run() -> void:
	await _wait(1.0)
	while game.level < 5:
		game.level_up_now()
		await _wait(0.2)
		while game.busy:
			if game.level_pick.visible:
				game.level_pick.bot_pick()
			await get_tree().process_frame
	var hero_m: Dictionary = game.party[0]
	var sub := Progression.sub(hero_m)
	print("RANGER hero: %s %s, level %d" % [Progression.klass(hero_m), sub, game.level])
	if sub == "Shifter":   # a hero from the creator, so the forms wear the hero kit's colours; each form a different one
		var h := Hero.new()
		h.race = game.run.race if game.run.race != "" else "Human"
		h.klass = game.run.klass
		h.sub = game.run.sub
		h.gear = {"main": hero_m.weapon, "off": hero_m.off, "armour": hero_m.armour}
		var look: Array = SHIFTER_LOOKS.get(hero_m.get("form", ""), SHIFTER_LOOKS.Werewolf)
		h.appearance = {"race": h.race, "sub": h.sub, "build": "Average", "head": 0, "hair": 0, "hair_colour": look[0], "cloth": look[1]}
		Hero.current = h
	await _fight("plains_stones")
	var hero: Dictionary = f.units[0]
	var line := _free_line(4)
	var s: Vector2i = line[0]
	var dv: Vector2i = Hex.NEIGHBOURS[line[1]]
	var foes := f.units.filter(func(u): return not u.ally)
	var foe: Dictionary = foes[0]
	var foe2: Dictionary = foes[1]
	match sub:
		"Elementalist":
			await _elementalist(hero, foe, foe2, s, dv)
		"Arcane Trickster":
			await _trickster(hero, foe, s, dv)
		"Companion":
			await _companion(hero, foe, foe2, s, dv)
		"Shifter":
			await _shifter(hero, foe, foe2, s, dv)
		_:
			_check(false, "a subclass this check covers (got %s)" % sub)
	print("RANGER DONE: %d failed" % failed)
	get_tree().quit()


## The hero beside the foe, a second foe 2 hexes behind it, everyone else out of the way, all fresh.
func _stage(hero: Dictionary, foe: Dictionary, foe2: Dictionary, s: Vector2i, dv: Vector2i) -> void:
	_clear_round(s, [hero, foe, foe2] + f.units.filter(func(u): return u.get("beast_of", "") != ""))
	for u in [hero, foe, foe2]:
		_fresh(u)
		u.mark = {}
		u.taunt = {}
		u.fear = -1
	_place(hero, s)
	_place(foe, s + dv)
	_place(foe2, s + dv * 3)
	f.target = {}


## Heads on every coin, then a hit with card id; how much HP the foe lost.
func _hit(u: Dictionary, foe: Dictionary, id := "attack") -> int:
	var before: int = foe.hp
	var heads: Array = []
	heads.resize(12)
	heads.fill(true)
	await _play(u, id, foe.cell, heads)
	return before - foe.hp


func _elementalist(hero: Dictionary, foe: Dictionary, foe2: Dictionary, s: Vector2i, dv: Vector2i) -> void:
	_check("infuse" in hero.cards, "Elementalist: gains Infuse")
	_check(f.cant_use(hero, Cards.get_card("infuse")) == "", "Infuse: usable")
	_check(Progression.card_for(hero.member, Cards.get_card("snare")).n == "Primal Snare", "Snare shows as Primal Snare")
	# The pop-up: Back cancels and costs nothing; a pick sets the element and pays.
	_stage(hero, foe, foe2, s, dv)
	f.auto_pick = ""
	_turn(hero)
	f.pick_card("infuse")
	f.press_button.call_deferred()
	await _wait(0.4)
	_check(f.hud.element_open(), "Infuse: the element pop-up opens")
	await _shot("infuse_popup")
	f.hud.element_picked.emit("")
	await _wait(0.2)
	_check(not f.hud.element_open() and hero.infuse == "" and f.ap_left(hero) == Rules.AP and not hero.used.has("infuse"), "Infuse: closing it leaves no element and spends no AP")
	f.pick_card("infuse")
	f.press_button.call_deferred()
	await _wait(0.4)
	f.hud.element_picked.emit("ice")
	await _wait(0.3)
	_check(hero.infuse == "ice" and f.ap_left(hero) == Rules.AP - 1, "Infuse: picking Ice sets it and spends 1 AP")
	await _shot("infuse_status")
	# Each element's rider on a hit.
	hero.infuse = ""
	_stage(hero, foe, foe2, s, dv)
	var plain := await _hit(hero, foe)
	hero.infuse = "fire"
	_stage(hero, foe, foe2, s, dv)
	var fire := await _hit(hero, foe)
	_check(fire == plain + Rules.INFUSE_FIRE, "Infuse fire: a hit deals %d more (%d vs %d)" % [Rules.INFUSE_FIRE, fire, plain])
	hero.infuse = "ice"
	_stage(hero, foe, foe2, s, dv)
	await _hit(hero, foe)
	_check(f.on(foe, "slowed"), "Infuse ice: the foe is slowed")
	hero.infuse = "lightning"
	_stage(hero, foe, foe2, s, dv)
	var before2: int = foe2.hp
	await _hit(hero, foe)
	_check(foe2.hp == before2 - Rules.INFUSE_JUMP, "Infuse lightning: %d jumps to the foe behind (%d -> %d)" % [Rules.INFUSE_JUMP, before2, foe2.hp])
	await _shot("infuse_lightning")
	hero.infuse = ""
	# Primal Snare: the pop-up when it's set, then each element when a foe walks in.
	_stage(hero, foe, foe2, s, dv)
	f.auto_pick = ""
	_turn(hero)
	f.pick_card("snare")
	var spots := f.cell_options(hero, Cards.get_card("snare"))
	var spot: Vector2i = spots[0]
	await f.click_cell(spot)
	f.press_button.call_deferred()
	await _wait(0.4)
	_check(f.hud.element_open(), "Primal Snare: the element pop-up opens when it's set")
	await _shot("primal_snare_popup")
	f.hud.element_picked.emit("fire")
	await _wait(0.3)
	_check(f.snares.get(hero.name, null) == spot and f.snare_elements.get(hero.name, "") == "fire", "Primal Snare: set with fire")
	await _shot("primal_snare_set")
	for el in ["fire", "ice", "lightning"]:
		_stage(hero, foe, foe2, s, dv)
		_place(hero, s + dv * 4)
		var trap: Vector2i = s
		f._set_snare(hero, trap, el)
		_place(foe, s + dv)
		_place(foe2, s + dv * 2)   # 2 from the trap once the foe walks in, for ice's slow and lightning's jump
		var hp1: int = foe.hp
		var hp2: int = foe2.hp
		await f._walk(foe, [trap])
		_check(f.on(foe, "snared"), "Primal Snare %s: the foe is rooted" % el)
		match el:
			"fire":
				_check(hp1 - foe.hp == Rules.SNARE_DAMAGE + Rules.INFUSE_FIRE, "Primal Snare fire: burns for %d more (%d)" % [Rules.INFUSE_FIRE, hp1 - foe.hp])
			"ice":
				_check(f.on(foe2, "slowed"), "Primal Snare ice: the foe beside it is slowed")
			"lightning":
				_check(foe2.hp == hp2 - Rules.INFUSE_JUMP, "Primal Snare lightning: %d jumps to the foe beside it" % Rules.INFUSE_JUMP)
	f.auto_pick = "fire"
	await _bot_fight_here()


func _trickster(hero: Dictionary, foe: Dictionary, s: Vector2i, dv: Vector2i) -> void:
	var foe2: Dictionary = f.units.filter(func(u): return not u.ally and u != foe)[0]
	_check(Progression.card_for(hero.member, Cards.get_card("poison_blade")).n == "Magical Blade", "Poison Blade shows as Magical Blade")
	_stage(hero, foe, foe2, s, dv)
	var plain := await _hit(hero, foe)
	_stage(hero, foe, foe2, s, dv)
	await _play(hero, "poison_blade", null, [])
	var heads: Array = []
	heads.resize(12)
	heads.fill(true)
	var before: int = foe.hp
	Coins.forced.assign(heads)
	f.pick_card("attack")
	await f.click_cell(foe.cell)
	await f.press_button()
	Coins.forced.clear()
	var blade: int = before - foe.hp
	_check(blade == plain + Rules.MAGIC_BLADE and foe.poison.is_empty(), "Magical Blade: %d more at once, no poison (%d vs %d)" % [Rules.MAGIC_BLADE, blade, plain])
	await _shot("magical_blade")


func _companion(hero: Dictionary, foe: Dictionary, foe2: Dictionary, s: Vector2i, dv: Vector2i) -> void:
	var kind := Progression.bot_follow_sub(hero.member, "Companion")
	_check(hero.member.get("beast", "") == kind, "Companion: picked the %s" % kind)
	_check(Progression.card_for(hero.member, Cards.get_card("hunters_mark")).n == "Pack Mark", "Hunter's Mark shows as Pack Mark")
	var b := f.beast_for(hero)
	_check(not b.is_empty() and b.beast == kind and b.mini.get_node("body").mesh != null, "the %s is on the board with its mini" % kind)
	if b.is_empty():
		return
	var st: Dictionary = Rules.BEAST_STATS[kind]
	_check(b.max_hp == st.hp + Rules.BEAST_HP_PER_LEVEL * (game.level - 5) and b.ap == Rules.SUMMON_AP, "the %s: %d HP, %d AP" % [kind, b.max_hp, b.ap])
	_check(not f.units.any(func(u): return u.ally and u.name == kind and u != b), "it doesn't take a companion's place")
	game.rig.ease_to(f.global_position + b.mini.position, 9.0, game.rig.yaw_deg)
	await _wait(0.8)
	await _shot("companion_%s_board" % kind.to_lower())
	# Its own attack, and Pack Mark.
	_stage(hero, foe, foe2, s, dv)
	_fresh(b)
	_place(hero, s + dv * 4)
	_place(b, s)
	foe.facing = f._dir_toward(foe.cell, b.cell)   # facing the beast, so the panther's from-behind bonus is off
	var plain := await _hit(b, foe)
	_check(plain > 0, "the %s's attack hits (%d)" % [kind, plain])
	if kind == "Wolf":
		_check(foe.lost_ap >= Rules.PRONE_AP, "the wolf knocks the foe down")
	_stage(hero, foe, foe2, s, dv)
	_fresh(b)
	_place(hero, s + dv * 4)
	_place(b, s)
	foe.facing = f._dir_toward(foe.cell, b.cell)
	hero.mark = foe
	var marked := await _hit(b, foe)
	_check(marked == plain + Rules.MARK_DAMAGE, "Pack Mark: the beast deals %d more to the marked foe (%d vs %d)" % [Rules.MARK_DAMAGE, marked, plain])
	# Command Beast.
	var cmd := Progression.card_for(hero.member, Cards.get_card("command_beast"))
	_stage(hero, foe, foe2, s, dv)
	_fresh(b)
	_place(hero, s + dv * 4)
	_place(b, s)
	var tails: Array = []
	tails.resize(12)
	tails.fill(false)
	match kind:
		"Wolf":
			await _play(hero, "command_beast", null, tails)
			_check(f.on(foe, "fear") and not f.on(foe2, "fear"), "Howl: the foe near the wolf is frightened, not the one %d away" % f.dist(b, foe2))
		"Bear":
			await _play(hero, "command_beast", null, [])
			_check(f._taunter(foe) == b, "Roar: foes near the bear must attack it")
		"Panther":
			await _play(hero, "command_beast", null, [])
			_check(b.lurking and b.name in foe.unaware, "Ambush: the panther hides")
			foe.facing = f._dir_toward(foe.cell, b.cell)
			var big := await _hit(b, foe)
			_check(big == plain * Rules.AMBUSH_TIMES + st.behind and not b.lurking, "Ambush: its next strike, %dx and from behind (%d)" % [Rules.AMBUSH_TIMES, big])
		"Hawk":
			_place(foe, s + dv * 3)
			_place(hero, s + dv * 4 + dv)   # out past the line: Dive's reach is the hawk's, not the ranger's
			_check(cmd.kind == "attack" and cmd.range == Weapons.of("beast_talons").range and f.in_reach(hero, foe, cmd), "Dive: aimed from the hawk, %d hexes away" % f.dist(b, foe))
			var before: int = foe.hp
			var heads: Array = []
			heads.resize(12)
			heads.fill(true)
			await _play(hero, "command_beast", foe.cell, heads)
			_check(before - foe.hp == st.damage * Rules.DIVE_TIMES, "Dive: a %dx hit from the hawk (%d)" % [Rules.DIVE_TIMES, before - foe.hp])
	await _shot("companion_%s_command" % kind.to_lower())
	# Downed: the card dims, the fight goes on, and the party alone decides it.
	b.hp = 0
	b.down = true
	_turn(hero)
	_check(f.cant_use(hero, cmd) == "_no_beast", "Command Beast dims while the beast is down")
	_fresh(b)
	await _bot_fight_here()


## `--shots`: the camera close on u, then the screen.
func _close(u: Dictionary, name: String) -> void:
	if not "--shots" in OS.get_cmdline_user_args():
		return
	game.rig.player_moved = true
	game.rig.ease_to(f.global_position + u.mini.position, 11.0, game.rig.yaw_deg)
	await _wait(0.9)
	await _shot(name)


## The Shifter's shots by day and then at night (the light only: the fight's own night rule stays as it started).
func _close_day_night(u: Dictionary, name: String) -> void:
	await _close(u, name + "_day")
	if not "--shots" in OS.get_cmdline_user_args():
		return
	for when: Array in [[Rules.NIGHT_AT + 4.0, "_night"], [Rules.START_MINUTE, ""]]:
		game.minute = when[0]
		game._shown_minute = -1.0   # straight there, not eased
		await _wait(0.4)
		if when[1] != "":
			await _shot(name + when[1])


## The hero's mini: the form's werebeast in form, taller than the hero, on one cell; the hero again out of it (07).
func _check_mini(hero: Dictionary, form: String, shifted: bool) -> void:
	var body := hero.mini.get_node("body") as MeshInstance3D
	var own := HeroMini.mesh_for(Hero.current)
	var beast := HeroMini.form_mesh(HeroMini.description(Hero.current), form)
	if not shifted:
		_check(body.mesh == own, "out of form: the hero's own mini")
		return
	var tall: float = beast.get_aabb().end.y
	var tris := beast.surface_get_array_index_len(0) / 3
	print("RANGER %s mini: %d triangles (the hero %d), %.2f tall (the hero %.2f)" % [form, tris, own.surface_get_array_index_len(0) / 3, tall, HeroMini.race_tall(HeroMini.description(Hero.current).race)])
	_check(body.mesh == beast and tall > HeroMini.race_tall(HeroMini.description(Hero.current).race), "in form: the %s mini, taller than the hero (%.2f)" % [form, tall])
	_check(absf(tall - HeroMini.FORM_TALL[form.to_lower()] * HeroMini.race_tall(HeroMini.description(Hero.current).race) / HeroMini.race_tall("human")) < 0.01, "the %s stands its size for the race" % form)
	var box := beast.get_aabb()
	_check(maxf(absf(box.position.x), box.end.x) <= 0.6 and maxf(absf(box.position.z), box.end.z) <= 0.6, "the %s keeps to its cell (%.2f x %.2f)" % [form, box.size.x, box.size.z])


func _shifter(hero: Dictionary, foe: Dictionary, foe2: Dictionary, s: Vector2i, dv: Vector2i) -> void:
	var form: String = hero.member.get("form", "")
	_check(form == Progression.bot_follow_sub(hero.member, "Shifter"), "Shifter: picked the %s" % form)
	if not Progression.FORMS.has(form):
		return
	var fc: String = Progression.FORMS[form].card
	_check("shift" in hero.cards and "rending_claws" in hero.cards and fc in hero.cards, "Shifter: gains Shift, Rending Claws and %s" % fc)
	_check(Progression.card_for(hero.member, Cards.get_card("snare")).n == "Pounce", "Snare shows as Pounce")
	# Out of form: the claws and the form's card dim and stay off the hotbar.
	_stage(hero, foe, foe2, s, dv)
	_turn(hero)
	_check(f.cant_use(hero, Cards.get_card("rending_claws")) == "_not_shifted" and f.cant_use(hero, Cards.get_card(fc)) == "_not_shifted", "out of form: Rending Claws and %s dim" % fc)
	_check(not "rending_claws" in f.hot_slots(hero) and f.sel == "attack", "out of form: the weapon's attack, no claws on the hotbar")
	_check_mini(hero, form, false)
	await _close_day_night(hero, "shifter_%s_1_out" % form.to_lower())
	# Shift: 1 AP; the weapon cards go, the claws and the form's card come.
	_turn(hero)
	f.pick_card("shift")
	await f.press_button()
	_check(hero.shifted and f.ap_left(hero) == Rules.AP - 1, "Shift: in form for 1 AP")
	var slots := f.hot_slots(hero)
	_check("rending_claws" in slots and fc in slots and not slots.any(func(id): return id != "" and Fight.weapon_attack(Cards.get_card(id))), "in form: Rending Claws and %s on the hotbar, no weapon cards" % fc)
	_check(f.cant_use(hero, Cards.get_card("attack", hero.weapon)) == "_shifted" and not "attack" in f.cards_of(hero) and fc in f.cards_of(hero), "in form: the basic attack is off, All actions swaps too")
	_turn(hero)
	_check(f.sel == "rending_claws", "in form: Rending Claws is the picked card")
	_check_mini(hero, form, true)
	await _close_day_night(hero, "shifter_%s_2_in" % form.to_lower())
	_stage(hero, foe, foe2, s, dv)
	var claws := await _hit(hero, foe, "rending_claws")
	_check(claws > 0 and f.cant_use(hero, Cards.get_card("rending_claws")) == "", "Rending Claws: hits (%d) and can go again" % claws)
	# The form's card.
	_stage(hero, foe, foe2, s, dv)
	var tails: Array = []
	tails.resize(12)
	tails.fill(false)
	match form:
		"Werewolf":
			_place(foe, s + dv * 3)
			foe.hp = maxi(foe.hp, claws * Rules.HUNT_DOWN_TIMES + 1)   # still standing for the save
			var hp: int = foe.hp
			var coins: Array = []   # heads for the claw hit, then tails for the foe's save
			for i in 12:
				coins.append(i < f.attack_coins(hero, foe, Cards.get_card("rending_claws")))
			await _play(hero, "hunt_down", foe.cell, coins)
			_check(f.dist(hero, foe) == 1 and hp - foe.hp == claws * Rules.HUNT_DOWN_TIMES and foe.lost_ap >= Rules.PRONE_AP, "Hunt Down: dashes to the foe, claws it for %d (%dx) and knocks it down" % [hp - foe.hp, Rules.HUNT_DOWN_TIMES])
		"Werebear":
			await _play(hero, "thick_hide", null, [])
			_check(hero.thick_hide and f._level_reduction(foe, hero) >= Rules.THICK_HIDE_LESS, "Thick Hide: takes %d less" % Rules.THICK_HIDE_LESS)
			f._turn_starts(hero)
			_check(not hero.thick_hide, "Thick Hide: ends at its next turn")
		"Werecat":
			var heads: Array = []
			heads.resize(12)
			heads.fill(true)
			await _play(hero, "shred", foe.cell, heads)
			var hp: int = foe.hp
			await f._turn_starts(foe)
			_check(hp - foe.hp == Rules.SHRED_BLEED, "Shred: the foe bleeds %d a turn (%d)" % [Rules.SHRED_BLEED, hp - foe.hp])
	await _close(hero, "shifter_%s_3_card" % form.to_lower())
	# Shift back: 1 AP, weapons again.
	_turn(hero)
	f.pick_card("shift")
	await f.press_button()
	await _wait(0.4)
	_check(not hero.shifted and f.cant_use(hero, Cards.get_card("attack", hero.weapon)) == "", "Shift again: back to the weapon")
	_check_mini(hero, form, false)
	# Pounce: the Snare springs, the Shifter leaps beside the foe and attacks it for double damage.
	_stage(hero, foe, foe2, s, dv)
	var plain := await _hit(hero, foe)
	_stage(hero, foe, foe2, s, dv)
	_place(hero, s + dv * 4)
	f._set_snare(hero, s, "")
	_place(foe, s + dv)
	_place(foe2, s + dv * 3)
	var hp0: int = foe.hp
	var all_heads: Array = []
	all_heads.resize(12)
	all_heads.fill(true)
	Coins.forced.assign(all_heads)
	await f._walk(foe, [s])
	Coins.forced.clear()
	_check(f.on(foe, "snared") and f.dist(hero, foe) == 1 and hp0 - foe.hp == Rules.SNARE_DAMAGE + plain * Rules.POUNCE_TIMES, "Pounce: the Snare springs, the Shifter leaps to the foe and hits for %d (Snare %d + %d x%d)" % [hp0 - foe.hp, Rules.SNARE_DAMAGE, plain, Rules.POUNCE_TIMES])
	await _close(hero, "shifter_%s_4_pounce" % form.to_lower())
	await _bot_fight_here()


## The fight bot plays the rest of this fight out.
func _bot_fight_here() -> void:
	for u in f.units:
		_fresh(u)
	var bot := FightBot.new(get_tree())
	var r := await bot.play(f)
	print("RANGER BOT: %d rounds, party HP %d to %d, %d down%s; played %s" % [r.rounds, r.hp0, r.hp1, r.downs, ", WIPED" if r.wiped else "", bot.used])
	_check(true, "a level-5 party plays a fight out")
