class_name FrontCheck
extends Node
## A scripted run of the screens before the game, by touch (`-- --front --check`, add `--shots` to save
## screens/front_*.png). Prints `FRONT OK` / `FRONT FAIL` for each check and quits. A test aid, not game UI.

const SAVES_DIR := "user://saves_front_check"   # Front empties it, so the title is a first launch

var front: Front
var failed := 0
var shots_on := "--shots" in OS.get_cmdline_user_args()


func _ready() -> void:
	TestNotes.dir = "user://test_notes_check"
	DirAccess.make_dir_recursive_absolute(TestNotes.dir)
	_run.call_deferred()


func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


## Injected events are in window pixels; everything here works in the layout's units (as TouchTest).
func _touch(pos: Vector2, pressed: bool) -> void:
	var e := InputEventScreenTouch.new()
	e.index = 0
	e.position = pos * Vector2(DisplayServer.window_get_size()) / get_viewport().get_visible_rect().size
	e.pressed = pressed
	Input.parse_input_event(e)
	await get_tree().process_frame


func tap(pos: Vector2) -> void:
	await _touch(pos, true)
	await _wait(0.08)
	await _touch(pos, false)
	await _wait(0.15)


## The centre of the first visible control whose accessibility name is `what`.
func control(what: String, root: Node = null) -> Control:
	for c in (root if root else get_tree().root).get_children():
		if c is Control and c.is_visible_in_tree() and (c as Control).accessibility_name == what:
			return c
		var found := control(what, c)
		if found:
			return found
	return null


func tap_on(what: String) -> bool:
	var c := control(what)
	if c == null:
		check(false, "found %s" % what)
		return false
	await tap(c.get_global_rect().get_center())
	return true


func check(ok: bool, what: String) -> void:
	print("FRONT %s %s" % ["OK  " if ok else "FAIL", what])
	if not ok:
		failed += 1


func shot(name: String) -> void:
	if not shots_on:
		return
	await RenderingServer.frame_post_draw
	var dir := ProjectSettings.globalize_path("res://screens")
	get_viewport().get_texture().get_image().save_png(dir.path_join("front_%s.png" % name))


## Every visible label at 11 pt or more (DOCS: Minimum text size on phones).
func text_sizes(where: String, root: Node) -> void:
	var small: Array[String] = []
	var walk := func(n: Node, self_fn: Callable) -> void:
		if n is Label and n.is_visible_in_tree() and (n as Label).text != "":
			if n.get_theme_font_size("font_size") < 11:
				small.append((n as Label).text)
		for c in n.get_children():
			self_fn.call(c, self_fn)
	walk.call(root, walk)
	check(small.is_empty(), "%s: no text under 11 pt %s" % [where, small if not small.is_empty() else ""])


func _run() -> void:
	await _wait(1.6)
	_kit_report()
	if "--steadycheck" in OS.get_cmdline_user_args():   # test aid: nothing on a creator step moves as its text changes
		await tap_on("New campaign")
		await _wait(0.3)
		await _steady(front.creator)
		print("FRONT DONE: %d failed" % failed)
		get_tree().quit(1 if failed > 0 else 0)
		return
	await _title()
	await _note("title")
	await _creator()
	await _game_run()
	print("FRONT DONE: %d failed" % failed)
	get_tree().quit(1 if failed > 0 else 0)


func _title() -> void:
	check(control("New campaign") != null, "title: New campaign shows")
	check(control("Continue") == null, "title: no Continue without a save")
	check(control("Load") == null, "title: no Load without a save")
	var fps_from := Engine.get_frames_drawn()
	var t0 := Time.get_ticks_msec()
	await _wait(1.0)
	print("FRONT title: %.0f fps" % ((Engine.get_frames_drawn() - fps_from) * 1000.0 / (Time.get_ticks_msec() - t0)))
	await shot("title")
	await tap_on("Settings")
	await _wait(0.2)
	check(front.title._toast != null, "title: Settings says it isn't in yet")
	await shot("title_toast")
	await _cost("title")
	await _wait(1.5)
	text_sizes("title", front.title)


func _creator() -> void:
	await tap_on("New campaign")
	await _wait(0.3)
	var c: Creator = front.creator
	check(c != null, "New campaign opens the creator")
	check(control("Back") != null and (control("Back") as TagButton).disabled, "class: Back is off on the first step")
	await shot("class_none")
	text_sizes("class", c)
	await _cost("creator class")
	# The Ranger (06 -> Start, Nov 5, 2026): playable, its kit shows Hunter's Mark (Snare comes at level 3, Nov 9), and gear offers only its own
	# weapons and Clothes or Armoured (04 -> Armour; the class list is a PLACEHOLDER in Gear), unless the hero is Human (Versatile).
	await tap_on("Ranger")
	await _wait(0.6)
	check(c.cls == "Ranger" and c.done("class"), "class: the Ranger is playable")
	check(control("Hunter's Mark") != null and control("Snare") == null, "class: the Ranger's kit shows Hunter's Mark, not Snare")
	await shot("class_ranger")
	var ranger_w: Array = c.allowed_weapons().map(func(w): return w.id)
	check(ranger_w == ["longsword", "shortsword", "scimitar", "dagger", "spear", "glaive", "shortbow", "longbow", "crossbow", "gauntlets", "knuckles", "wraps"], "gear: a Ranger gets only Ranger weapons: %s" % [ranger_w])
	check(c.armour_options().map(func(a): return a.id) == ["none", "armoured"], "gear: a Ranger wears Clothes or Armoured")
	c.race = "Human"
	check(c.allowed_weapons().size() == Gear.WEAPONS.size(), "gear: a Human Ranger gets every weapon (Versatile)")
	c.race = ""
	# The Rogue (06 -> Start, Nov 6, 2026): playable, its kit shows Sneak Attack (Poison Blade comes at level 3, Nov 9), and gear offers only its own
	# weapons and no armour (Clothes only, 04).
	await tap_on("Rogue")
	await _wait(0.6)
	check(c.cls == "Rogue" and c.done("class"), "class: the Rogue is playable")
	check(control("Sneak Attack") != null and control("Poison Blade") == null, "class: the Rogue's kit shows Sneak Attack, not Poison Blade")
	await shot("class_rogue")
	var rogue_w: Array = c.allowed_weapons().map(func(w): return w.id)
	check(rogue_w == ["shortsword", "rapier", "scimitar", "dagger", "shortbow", "crossbow", "gauntlets", "knuckles", "wraps"], "gear: a Rogue gets only Rogue weapons: %s" % [rogue_w])
	check(c.armour_options().map(func(a): return a.id) == ["none"], "gear: a Rogue wears Clothes only")
	# The Wizard (06 -> Start, Nov 6, 2026): playable, its kit shows two spell slots, Clothes only, and a Spells step after
	# Gear: 2 picks from the 9 level-1 spells, a third swapping out the first, a tap on a filled slot clearing it.
	await tap_on("Wizard")
	await _wait(0.6)
	check(c.cls == "Wizard" and c.done("class"), "class: the Wizard is playable")
	check(c.allowed_weapons().map(func(w): return w.id) == ["dagger", "staff", "wand"] and c.armour_options().map(func(a): return a.id) == ["none"], "gear: a Wizard gets daggers, staves and wands, and wears Clothes only")
	check(c.steps().map(func(x): return x[0]) == ["class", "race", "bg", "scores", "skills", "gear", "spells", "look", "name"], "class: a Wizard's steps add Spells after Gear")
	await shot("class_wizard")
	c.race = "Human"
	c.bg = "Sage"
	c.go("spells")
	await _wait(0.6)
	check(control("Spell 1") != null and control("Spell 2") != null and not c.done("spells"), "spells: two empty slots, and Next waits")
	await shot("spells_none")
	text_sizes("spells", c)
	await tap_on("Firebolt")
	await _wait(0.2)
	check(control("Choose") != null, "spells: tapping a spell opens its pop-up with Choose")
	await shot("spells_popup")
	await tap_on("Choose")
	await _wait(0.1)
	await tap_on("Wisp")
	await _wait(0.1)
	await tap_on("Choose")
	await _wait(0.2)
	check(c.spells == ["firebolt", "wisp"] and c.done("spells"), "spells: two picks fill the slots and turn Next on")
	await shot("spells_picked")
	await tap_on("Mirror Image")
	await _wait(0.2)
	await shot("spells_replace")
	await tap_on("Choose")
	await _wait(0.1)
	check(c.spells == ["wisp", "mirror_image"], "spells: a third pick swaps out the first: %s" % [c.spells])
	await tap_on("Wisp")
	await _wait(0.1)
	check(c.spells == ["mirror_image"] and not c.done("spells"), "spells: tapping a filled slot clears it")
	c.race = ""
	c.bg = ""
	c.go("class")
	await _wait(0.4)
	# The Cleric (06 -> Start, Nov 12, 2026): playable, a God step right after Class (07), the god's free spell and +2
	# cards on its banner, and a Spells step with the four orders' 8 spells.
	await tap_on("Cleric")
	await _wait(0.6)
	check(c.cls == "Cleric" and c.done("class"), "class: the Cleric is playable")
	check(control("God") != null, "class: the Cleric's kit shows two spell slots and the god's slot")
	check(c.steps().map(func(x): return x[0]) == ["class", "god", "race", "bg", "scores", "skills", "gear", "spells", "look", "name"], "class: a Cleric's steps add God after Class and Spells after Gear")
	await shot("class_cleric")
	await tap_on("Next")
	await _wait(0.6)
	check(c.step == "god" and not c.done("god"), "god: the God step, and Next waits")
	await shot("god_none")
	for g: String in Progression.GODS:
		await tap_on(g)
		await _wait(0.5)
		check(c.god == g and c.done("god") and control(Cards.ALL[Progression.GODS[g]].n) != null, "god: %s shows its free spell, %s" % [g, Cards.ALL[Progression.GODS[g]].n])
		await shot("god_%s" % g.to_lower())
	await tap_on(Cards.ALL[Progression.GODS[c.god]].n)
	await _wait(0.15)
	await shot("god_card_popup")
	c.race = "Human"
	c.bg = "Acolyte"
	c.go("spells")
	await _wait(0.6)
	for id: String in ["sacred_flame", "shadow_bolt", "bless", "hex"]:
		check(control(Cards.ALL[id].n) != null, "spells: the Cleric's list has %s" % Cards.ALL[id].n)
	await shot("spells_cleric")
	await tap_on("Dread")
	await _wait(0.2)
	await shot("spells_cleric_popup")
	await tap_on("Choose")
	await _wait(0.1)
	check(c.spells == ["dread"] and c.hero().god == c.god, "spells: a Cleric's pick, and the hero keeps the god")
	# The Bard: playable, the College's four skills (Nov 12, 2026), the four schools' 8 spells.
	c.go("class")
	await _wait(0.4)
	await tap_on("Bard")
	await _wait(0.6)
	check(c.cls == "Bard" and c.done("class") and c.god == "" and c.cls_data().pr == ["Persuade", "Deceive", "Intimidate", "Lore"], "class: the Bard is playable, with the College's skills")
	await shot("class_bard")
	c.go("spells")
	await _wait(0.6)
	for id: String in ["mockery", "rousing_tune", "dazzle", "war_cry"]:
		check(control(Cards.ALL[id].n) != null, "spells: the Bard's list has %s" % Cards.ALL[id].n)
	await shot("spells_bard")
	await tap_on("Blade Twirl")
	await _wait(0.2)
	await shot("spells_bard_popup")
	c.go("skills")
	await _wait(0.5)
	await shot("skills_bard")
	c.race = ""
	c.bg = ""
	c.spells = []
	c.go("class")
	await _wait(0.4)
	await tap_on("Fighter")
	await _wait(0.6)
	check(c.done("class"), "class: the Fighter is playable")
	await shot("class_fighter")
	await tap_on("Second Wind")
	await _wait(0.15)
	await shot("class_card_popup")
	await tap_on("Next")
	await _wait(0.3)
	await shot("race_none")
	await _every_sub_type(c)
	# The longest race for the row of sub-types and a card, then the race the run goes on with.
	await tap_on("Dragonborn")
	await _wait(0.6)
	await tap_on("Blue")
	await _wait(0.5)
	await shot("race_dragonborn")
	text_sizes("race", c)
	await tap_on("Elf")
	await _wait(0.6)
	await tap_on("High elf")
	await _wait(0.5)
	check(not c.done("race"), "race: a high elf needs a spell")
	await tap_on("Lull")
	await _wait(0.4)
	check(c.done("race"), "race: picking the spell finishes it")
	await shot("race_high_elf")
	await tap_on("Dwarf")
	await _wait(0.6)
	await tap_on("Shield dwarf")
	await _wait(0.5)
	await shot("race_dwarf")
	await tap_on("Next")
	await _wait(0.3)
	await shot("background_none")
	await tap_on("Sage")
	await _wait(0.6)
	await shot("background_sage")
	text_sizes("background", c)
	await tap_on("Folk Hero")
	await _wait(0.6)
	await shot("background_folk_hero")
	await tap_on("Next")
	await _wait(0.4)
	# Scores: a third race +1 pushes the oldest off.
	for what in ["Race +1 CON", "Race +1 STR", "Race +1 WIS", "Class +1 DEX"]:
		await tap_on(what)
		await _wait(0.05)
	check(c.rb == ["STR", "WIS"], "scores: a third race pick swaps out the oldest")
	check(c.scores()["DEX"] == 2 and c.scores()["STR"] == 2 and c.done("scores"), "scores: the picks add coins")
	await _wait(0.35)
	await shot("scores")
	text_sizes("scores", c)
	await tap_on("Next")
	await _wait(0.4)
	await tap_on("Choose Animal")
	await _wait(0.05)
	await tap_on("cls:Athletics")
	await _wait(0.05)
	await tap_on("Choose Athletics")
	await _wait(0.35)
	check(c.done("skills"), "skills: one pick from each list")
	await shot("skills")
	text_sizes("skills", c)
	await tap_on("Next")
	await _wait(0.3)
	check(control("Greatsword") != null, "gear: the Fighter gets every weapon")
	await shot("gear_main")
	text_sizes("gear", c)
	await tap_on("Greatsword")
	await _wait(0.05)
	await tap_on("Choose Greatsword")
	await _wait(0.2)
	await shot("gear_flying")
	await _wait(0.6)
	check(c.off_options().is_empty(), "gear: a two-handed weapon crosses out the offhand")
	await shot("gear_two_handed")
	await tap_on("Longsword")
	await _wait(0.05)
	await tap_on("Choose Longsword")
	await _wait(0.6)
	await tap_on("Next: Offhand")
	await _wait(0.1)
	await tap_on("Shield")
	await _wait(0.05)
	await tap_on("Choose Shield")
	await _wait(0.6)
	await shot("gear_offhand")
	await tap_on("Next: Armour")
	await _wait(0.1)
	await tap_on("Armoured")
	await _wait(0.05)
	await tap_on("Choose Armoured")
	await _wait(0.6)
	check(c.done("gear"), "gear: all three slots filled")
	await tap_on("Next")
	await _wait(1.1)
	check((control("Next") as TagButton).disabled, "look: Next waits for pronouns")
	await shot("look")
	text_sizes("look", c)
	await tap_on("They")
	await _wait(0.05)
	await tap_on("Broad")
	await _wait(0.05)
	await tap_on("Hairstyle 3")
	await _wait(0.05)
	await tap_on("Hair 4")
	await _wait(0.05)
	await tap_on("Cloth 2")
	await _wait(0.05)
	await tap_on("Turn right")
	await _wait(0.5)
	var spun: float = (c.find_children("*", "HeroView", true, false)[0] as HeroView).yaw
	check(is_equal_approx(snappedf(spun, 0.001), snappedf(PI * 0.25, 0.001)), "look: Turn right turns the mini 45° (%.0f°)" % rad_to_deg(spun))
	check(control("Front") == null and not c.find_children("*", "Label", true, false).any(func(l): return (l as Label).text in ["Front", "Right side", "Back", "Left side"]), "look: no view name under the mini")
	await shot("look_picked")
	if "--lookshots" in OS.get_cmdline_user_args():   # test aid: the hero kit's poses on the Look step, one hero a shot
		await _look_shots()
		get_tree().quit()
		return
	await tap_on("Next")
	await _wait(0.9)
	check((control("Begin") as TagButton).disabled, "name: Begin waits for a name")
	var edit := front.creator.find_children("*", "LineEdit", true, false)[0] as LineEdit
	edit.text = "Hilde Oakshield"
	edit.text_changed.emit(edit.text)
	await _wait(0.1)
	check(not (control("Begin") as TagButton).disabled, "name: a typed name lets Begin on")
	await shot("name")
	await _note("creator")
	text_sizes("name", front.creator)
	await tap_on("Begin")
	await _wait(0.6)
	await shot("send_off_rising")
	await _wait(1.0)
	check(Hero.current.name == "Hilde Oakshield", "Begin hands the description to the game")
	check(Hero.current.race_name == "Shield dwarf" and Hero.current.background == "folk_hero", "the description names race and background")
	await _wait(1.6)
	await shot("send_off_banner")


## On into the game: the run from the creator, a town, then a Social event, all by touch.
## Every race at this width: nothing is preselected, Next stays off until a sub-type is picked, each selector is on screen and a finger's tap on it counts (design/07 -> Character creator).
func _every_sub_type(c: Creator) -> void:
	var screen := get_viewport().get_visible_rect()
	for r: Dictionary in CreatorData.RACES:
		await tap_on(r.id)
		await _wait(0.6)
		var subs: Array = r.get("subs", [])
		check(c.race == r.id and c.sub == "", "race %s: picked, with no sub-type preselected" % r.id)
		check(c.done("race") == subs.is_empty(), "race %s: Next is %s" % [r.id, "on" if subs.is_empty() else "off until a sub-type"])
		await shot("race_%s_open" % str(r.id).to_lower())
		for x: Dictionary in subs:
			var t := control(str(x.id))
			check(t != null and screen.encloses(t.get_global_rect()), "race %s: %s is on screen %s" % [r.id, x.id, t.get_global_rect() if t else ""])
			await tap_on(str(x.id))
			await _wait(0.5)
			check(c.sub == x.id, "race %s: tapping %s picks it" % [r.id, x.id])
			check(c.done("race") == (x.id != "High elf"), "race %s: Next after %s" % [r.id, x.id])
			check((control("Next") as TagButton).disabled != c.done("race"), "race %s: the Next button follows it after %s" % [r.id, x.id])
			await shot("race_pick_%s" % str(x.id).to_lower().replace(" ", "_"))
		if subs.any(func(x): return x.id == "High elf"):
			await tap_on("High elf")
			await _wait(0.4)
			for spell: String in ["Glimmerstep", "Faerie Fire", "Lull"]:
				await tap_on(spell)
				await _wait(0.3)
				check(c.elf_spell == spell and c.done("race"), "race Elf: picking %s turns Next on" % spell)


func _game_run() -> void:
	await _wait(5.0)   # the banner drops in and rises away
	var g := get_tree().current_scene as Game
	check(g != null, "the game scene is running")
	await _note("map")
	check(g.party[0].name == "Hilde Oakshield", "the game has the hero's name")
	check(g.party.size() == 2 and g.party[1].name == "Fluffy", "the party is the hero and Fluffy")
	check(g.run.background == "folk_hero", "the run starts from the background")
	check(g.can_enter_town(), "town: a Folk Hero's start tile, the inn, can be entered")
	# Each place opens its own scene (07 -> Town screen; Places): the start tile, each town variant and its landmark, and a
	# plain village, which is the market town; every kit the list names exists.
	check(Places.id_at(g, Rules.START_TILE) == "start_folk_hero", "places: the Folk Hero's start tile is its own place")
	for v: String in Variants.TIER2.village + ["market_town"]:
		check(Places.PLACES.has(v), "places: %s is a place" % v)
	for lm: String in ["tradinghouse", "keep", "blackmarket", "college"]:
		check(Places.PLACES.has(Variants.LANDMARKS[lm]), "places: the %s is part of its town's square" % lm)
	for id: String in Places.PLACES:
		var pl: Dictionary = Places.PLACES[id]
		check(Places.KITS.has(pl.kit) and Places.KITS.has(pl.inn), "places: %s's kits exist" % id)
	var next: Vector2i = Rules.START_TILE + Hex.NEIGHBOURS[0]
	g.map.retile({next: "village"})
	g.order[next] = 1
	g.gold = 40
	g.party[0].hp = maxi(g.party[0].hp - 4, 1)
	g.walk_to(next)
	while g.busy or g.party_tile != next:
		await get_tree().process_frame
	await _wait(0.4)
	g._refresh()
	await _wait(0.1)
	check(control("Enter") != null, "town: standing on one shows Enter")
	await shot("town_enter_card")
	await tap_on("Enter")
	await _wait(1.3)
	check(control("Shop") != null and control("Inn") != null and control("Leave") != null, "town: Shop, Inn and Leave")
	check(Places.id_at(g, next) == "market_town", "places: a plain village opens the market town")
	check(control("Enter") == null, "town: the map's cards are gone")
	var town := g.safe.get_children().filter(func(n): return n is TownScene)[0] as TownScene
	check(not g.map.visible, "town: the scene stands alone, the map hidden")
	check(town.stage._minis.size() == g.party.size(), "town: the party stands in the square")
	check(town.stage._keeper != null and town.stage._keeper.name == "shopkeeper", "town: the shopkeeper is at the stall")
	check(g.clock.environment.background_color != Color(Places.KITS.inn.backdrop), "town: the square has the map's backdrop")
	await _wait(0.2)
	print("FRONT square: %d triangles, %d draw calls" % [RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME), RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)])
	await shot("town_square")
	g.rig.yaw_deg = 60.0
	await _wait(0.2)
	await shot("town_square_turned")
	g.rig.yaw_deg = 0.0
	var day_minute := g.minute
	g.minute = 25.0
	town.stage.set_night(true)
	if shots_on:   # the light eases after the clock; only a picture needs it settled
		await _wait(3.5)
	await shot("town_square_night")
	town.stage.set_night(false)
	g.minute = day_minute
	if shots_on:
		await _wait(3.5)
	text_sizes("town", g.safe)
	await tap_on("Shop")
	await _wait(0.3)
	check(town.stage._minis[0].position.is_equal_approx(town.stage.spot("square", "shop", 0)), "shop: the party gathers by the stall")
	await shot("town_shop")
	await tap_on("Health potion")
	await _wait(0.2)
	await shot("town_shop_item")
	await tap_on("Buy Health potion")
	await _wait(0.3)
	check(g.gold == 35 and g.potions == 1, "shop: a potion spends gold and goes to the count Use item reads")
	await shot("town_shop_bought")
	await _wait(2.2)
	await tap_on("Back")
	await _wait(0.3)
	await tap_on("Inn")
	await _wait(0.6)
	check(town.stage.scene_name == "inn" and town.stage._keeper.name == "innkeeper", "inn: the interior, with the innkeeper")
	var behind_bar: Vector3 = town.stage._keeper.position
	check(behind_bar.z < town.stage._hex(1, -2).z, "inn: the innkeeper stands behind the bar")
	check(g.clock.environment.background_color == Color(Places.KITS.inn.backdrop), "inn: the flat dark backdrop")
	print("FRONT inn: %d triangles, %d draw calls" % [RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME), RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)])
	await shot("town_inn")
	g.rig.yaw_deg = -50.0
	await _wait(0.2)
	await shot("town_inn_turned")
	g.rig.yaw_deg = 0.0
	g.minute = 25.0
	town.stage.set_night(true)
	if shots_on:
		await _wait(3.5)
	await shot("town_inn_night_light")
	town.stage.set_night(false)
	g.minute = day_minute
	if shots_on:
		await _wait(3.5)
	text_sizes("inn", g.safe)
	await tap_on("Rest the night")
	await _wait(0.3)
	check(g.gold == 30, "inn: the rest charges gold")
	await shot("town_inn_bar")
	var scene := town
	while scene._phase == "revel":
		await tap(Vector2(420, 180))
		await _wait(0.2)
	await _wait(0.9)
	await shot("town_inn_night")
	await _wait(2.6)
	await _wait(1.6)
	check(g.party[0].hp == g.party[0].max_hp, "inn: resting heals")
	await shot("town_inn_rested")
	await tap_on("Carry on")
	await _wait(0.2)
	await tap_on("Rest the night")
	await _wait(0.2)
	check(g.gold == 30, "inn: one rest a visit")
	await tap_on("Back")
	await _wait(0.2)
	await tap_on("Leave")
	await _wait(0.3)
	await _wait(0.5)
	check(not g.busy, "town: Leave hands the map back")
	check(g.map.visible and g.party_node.visible, "town: the map and party are back")
	check(g.clock.environment.background_color != Color(Places.KITS.inn.backdrop), "town: the backdrop follows the clock again")
	await _social(g)


## Taps the scene's text (to finish or turn the page) until `what` shows, so a slow page can't make the check miss it.
func _tap_until(what: String) -> void:
	for i in 10:
		if control(what) != null:
			return
		await tap(Vector2(420, 180))
		await _wait(0.4)


## Waits up to secs for `what` to show (the flip's coins land before Continue).
func _wait_for(what: String, secs: float) -> void:
	var t := 0.0
	while control(what) == null and t < secs:
		await _wait(0.1)
		t += 0.1


func _social(g: Game) -> void:
	var t: Vector2i = Rules.START_TILE
	g.add_encounter(t, true, [], {"kind": "social", "scene": "enc_social_trader", "name": "[Trader]", "roams": false})
	g.debug_near_miss = 1
	g.walk_to(t)
	while g.party_tile != t or g.party_node.walking:
		await get_tree().process_frame
	await _wait(1.2)
	var scene := g.safe.get_children().filter(func(n): return n is SocialScreen)
	check(not scene.is_empty(), "social: walking onto the event opens the scene")
	await shot("social_line")
	text_sizes("social", g.safe)
	await _tap_until("Swear you are true")
	check(control("Swear you are true") != null and control("Leave") != null, "social: the cards deal on the last page")
	await shot("social_cards")
	await tap_on("Swear you are true")
	await _wait(0.3)
	await shot("social_check")
	await tap_on("Back")
	await _wait(0.2)
	await tap_on("Swear you are true")
	await _wait(0.2)
	await tap_on("Flip coins")
	await _wait_for("Continue", 8.0)
	await shot("social_chime")
	await tap_on("Continue")
	await _wait(0.6)
	await shot("social_blessing")
	await _wait(1.8)
	await _tap_until("Leave")
	await tap_on("Leave")
	await _wait(0.4)
	check(not g.busy and not g.encounters.has(t), "social: Leave hands the map back and the event is gone")
	await shot("social_done")
	# A failed Draw your weapon: her line, then the fight.
	var t2: Vector2i = Rules.START_TILE + Hex.NEIGHBOURS[0]
	g.add_encounter(t2, true, [], {"kind": "social", "scene": "enc_social_trader", "name": "[Trader]", "roams": false})
	g.walk_to(t2)
	while g.party_tile != t2 or g.party_node.walking:
		await get_tree().process_frame
	await _wait(1.2)
	await _tap_until("Draw your weapon")
	await tap_on("Draw your weapon")
	await _wait(0.2)
	await tap_on("Flip coins")
	await _wait_for("Continue", 8.0)
	await tap_on("Continue")
	await _wait(0.5)
	await shot("social_fight_line")
	await tap(Vector2(420, 180))
	for i in 60:   # up to 6 s for the zoom into the fight
		if g.fight.active:
			break
		await _wait(0.1)
	check(g.fight.active, "social: a failed threat starts the fight")
	await _note("fight")
	await shot("social_fight")


## The test note's flag on this screen: opens, pauses, keeps the words, saves one note, and comes back as it was.
func _note(where: String) -> void:
	var before := DirAccess.get_files_at(TestNotes.dir).size()
	check(control("Test note") != null, "note: the flag shows on %s" % where)
	await tap_on("Test note")
	await _wait(0.15)
	check(get_tree().paused, "note: the game holds while the box is open (%s)" % where)
	var edit := control("Note text") as TextEdit
	edit.text = "[check] on %s" % where
	edit.text_changed.emit()
	await _wait(0.1)
	if where == "map":
		await shot("note_box")
	await tap_on("Save")
	await _wait(0.2)
	check(not get_tree().paused, "note: Save lets the game go on (%s)" % where)
	var names := DirAccess.get_files_at(TestNotes.dir)
	check(names.size() >= before + 2, "note: a JSON and a screenshot saved (%s)" % where)
	var newest := ""
	for n in names:
		if n.ends_with(".json") and n > newest:
			newest = n
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(TestNotes.dir.path_join(newest)))
	print("FRONT note %s: %s" % [where, JSON.stringify(data).left(400)])
	check(data.get("text", "") == "[check] on %s" % where, "note: the text is kept (%s)" % where)


## The hero kit (art/handoff/hero_kit.md): the colours as Godot imported them, every shape the Fighter can pick assembles,
## triangles, and what a rebuild costs.
func _kit_report() -> void:
	print("FRONT kit decode: ", HeroMini.decode_report())
	var t := HeroMini.table()
	var tris := []
	var times := []
	var built := 0
	var missing := {}
	var kit := Kit.meshes(HeroMini.GLB)
	# Each race, a golem once per sub-type (kit v14; golem_metal is the metal golem's own entry, read through its sub-type).
	var shapes := []
	for race: String in t.races:
		if race == "golem":
			for sub: String in t.golem_subtypes:
				shapes.append([race, sub])
		elif not race.begins_with("golem_"):
			shapes.append([race, ""])
	for shape: Array in shapes:
		var race: String = shape[0]
		for build: String in t.builds:
			for main: String in t.races[race].builds[build].poses:
				for hold: String in t.races[race].builds[build].poses[main]:
					var off: String = {"shield": "shield", "second": "dagger"}.get(hold, "")
					for armour: String in ["none", "heavy"]:
						var d := {"race": race, "build": build, "head": "a", "hair": "long", "armour": armour, "main": main, "offhand": off,
							"two": hold == "two", "caster": hold == "cast",
							"colours": {"skin": "#C68E64", "hair": "#2B211C", "eyes": "#4F7A33", "cloth": "#3E6F8C"}}
						if shape[1] != "":
							d.subtype = shape[1]
						for part: Array in HeroMini.parts(d):
							if not kit.has(part[0]):
								missing[part[0]] = true
						if not missing.is_empty():
							continue
						var t0 := Time.get_ticks_usec()
						var m := HeroMini.build(d)
						times.append((Time.get_ticks_usec() - t0) / 1000.0)
						tris.append(m.surface_get_array_index_len(0) / 3)
						built += 1
	# Golems -> The metal golem's own arm placements: its arms and weapon sit elsewhere, its body where the stone golem's does.
	var g := {"race": "golem", "build": "average", "head": "a", "hair": "", "armour": "none", "main": "greatsword", "offhand": "",
		"colours": {"skin": "#9AA3AB", "hair": "#2B211C", "eyes": "#4F7A33", "cloth": "#3E6F8C"}}
	var metal := HeroMini.parts(g.merged({"subtype": "metal"}))
	var stone := HeroMini.parts(g.merged({"subtype": "stone"}))
	check(metal[1][1] == stone[1][1] and metal[-1][1] != stone[-1][1] and metal[-1][0] == "hero_greatsword",
			"kit: the metal golem reads its own entry (its greatsword moves, its body doesn't)")
	check(missing.is_empty(), "kit: every piece the table asks for exists %s" % [missing.keys() if not missing.is_empty() else ""])
	times.sort()
	print("FRONT kit: %d heroes, %d to %d triangles; rebuild median %.1f ms, worst %.1f ms" % [built, tris.min(), tris.max(), times[times.size() / 2], times[-1]])
	check(tris.max() <= 1360, "kit: a hero stays within the hand-off's 1,360 triangles (kit v14)")


## The Look step's mini for a few heroes, one per pose family (art/handoff/hero_kit.md, kit v10): [name, class, race, sub,
## main, off, armour].
func _look_shots() -> void:
	var c := front.creator
	var look := c.find_children("*", "CreatorLook", true, false)[0] as CreatorLook
	await tap_on("Turn left")   # back to the front after the walk's turn
	for h: Array in [["bow", "Ranger", "Elf", "Wood elf", "shortbow", "", "armoured"], ["glaive", "Fighter", "Dragonborn", "Blue", "glaive", "", "armoured"],
			["longsword_two", "Fighter", "Human", "", "longsword", "", "armoured"], ["staff_cast", "Wizard", "Halfling", "", "staff", "", ""],
			["wraps", "Fighter", "Dwarf", "Forge dwarf", "wraps", "", "armoured"], ["rogue_daggers", "Rogue", "Halfling", "", "dagger", "dagger", ""],
			["rogue_rapier", "Rogue", "Tiefling", "", "rapier", "", ""], ["rogue_rapier_dagger", "Rogue", "Elf", "High elf", "rapier", "dagger", ""],
			["rogue_scimitars", "Rogue", "Human", "", "scimitar", "scimitar", ""], ["rogue_shortbow", "Rogue", "Elf", "Wood elf", "shortbow", "", ""],
			# kit v14: each golem sub-type its own shape; the metal golem's long arms on a two-handed grip and a shield
			["golem_metal", "Fighter", "Golem", "Metal", "greatsword", "", "armoured"], ["golem_metal_shield", "Cleric", "Golem", "Metal", "mace", "shield", ""],
			["golem_stone", "Fighter", "Golem", "Stone", "warhammer", "", ""], ["golem_wood", "Ranger", "Golem", "Wood", "longbow", "", ""]]:
		c.cls = h[1]
		c.race = h[2]
		c.sub = h[3]
		c.main = h[4]
		c.off = h[5]
		c.arm = h[6]
		var d := HeroMini.description(c.hero())
		look._mini.show_hero(d)
		if h[2] == "Golem":
			var sub := str(h[3]).to_lower()
			var names := HeroMini.parts(d).map(func(p): return p[0])
			check(d.get("subtype") == sub and names.any(func(n): return n.begins_with("hero_body_golem_%s_" % sub)) and "hero_hand_golem_" + sub in names,
					"Look: a %s golem wears its own shape (%s)" % [sub, names.filter(func(n): return "golem" in n)])
		await _wait(0.4)
		await shot("look_kit_" + h[0])


## What a screen costs to draw.
func _cost(where: String) -> void:
	for _k in 10:
		await get_tree().process_frame
	print("FRONT cost %s: %d draw calls, %d nodes" % [where, Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.OBJECT_NODE_COUNT)])


# --- Steady layout (--steadycheck) --------------------------------------------------------

## Where things sit, top to bottom: every visible node under `root` that `pick` accepts, by its global y.
func _marks(root: Node, pick: Callable) -> Array:
	var out := []
	for n in root.find_children("*", "Control", true, false):
		if (n as Control).is_visible_in_tree() and pick.call(n):
			out.append(roundi((n as Control).get_global_rect().position.y))
	out.sort()
	return out


## Every pick in a group should leave the marks where the first one left them. Picks with a different number of marks
## (a race without passives, a weapon without a note) are laid out differently by design, so each count is its own group.
func _same(what: String, seen: Dictionary) -> void:
	var first := {}
	var off := []
	for k in seen:
		var n: int = seen[k].size()
		if not first.has(n):
			first[n] = seen[k]
		elif seen[k] != first[n]:
			off.append("%s %s" % [k, seen[k]])
	check(off.is_empty(), "%s: nothing moves from one pick to the next %s" % [what, ("(first %s; moved: %s)" % [first, ", ".join(off)]) if not off.is_empty() else ""])


## Ethan's phone note (Nov 8, 2026): text that wraps to a second line must not push what's below it. Each step's picks in
## turn, comparing where the dividers, headings and buttons under the text sit.
func _steady(c: Creator) -> void:
	var banner_marks := func(n: Node) -> bool:
		return n is CreatorBanners.Stitch or (n is Label and (n as Label).text in ["WEAPONS", "ARMOUR", "BOOSTS", "STARTING PLACE"]) \
			or str((n as Control).accessibility_name).ends_with("(racial passive)")
	var seen := {}
	for k: Dictionary in CreatorData.CLS:
		await tap_on(k.id)
		await _wait(0.6)
		seen[k.id] = _marks(c, banner_marks)
		await shot("steady_class_%s" % str(k.id).to_lower())
	_same("class", seen)
	await tap_on("Fighter")
	await _wait(0.6)
	await tap_on("Next")
	await _wait(0.3)
	var plain := {}
	var subs := {}
	for r: Dictionary in CreatorData.RACES:
		await tap_on(r.id)
		await _wait(0.6)
		if r.get("subs", []).is_empty():
			plain[r.id] = _marks(c, banner_marks)
		else:
			subs[r.id] = _marks(c, banner_marks)
			for x: Dictionary in r.subs:
				await tap_on(str(x.id))
				await _wait(0.5)
				subs[x.id] = _marks(c, banner_marks)
		await shot("steady_race_%s" % str(r.id).to_lower())
	_same("race without sub-types", plain)
	_same("race with sub-types", subs)
	await tap_on("Dwarf")
	await _wait(0.6)
	await tap_on("Shield dwarf")
	await _wait(0.5)
	await tap_on("Next")
	await _wait(0.3)
	seen = {}
	for b: Dictionary in CreatorData.BGS:
		await tap_on(b.id)
		await _wait(0.6)
		seen[b.id] = _marks(c, banner_marks)
		await shot("steady_background_%s" % str(b.id).to_lower().replace(" ", "_"))
	_same("background", seen)
	# Skills: the details pane's base line, signature and Choose.
	c.go("skills")
	await _wait(0.4)
	seen = {}
	var keys := []
	for n in c.find_children("*", "Control", true, false):
		var key := str((n as Control).accessibility_name)
		if (key.begins_with("bg:") or key.begins_with("cls:")) and not key in keys:
			keys.append(key)
	for key: String in keys:
		await tap_on(key)
		await _wait(0.1)
		seen[key] = _marks(c, func(n: Node) -> bool: return n is Label and ((n as Label).text == "SIGNATURE" or (n as Label).text.begins_with("Base: ")))
		await shot("steady_skills_%s" % key.replace(":", "_").to_lower().replace(" ", "_"))
	_same("skills", seen)
	# Gear: weapons with the same cards and modifier keep their text where it was.
	c.go("gear")
	await _wait(0.4)
	var groups := {}
	for w: Dictionary in c.allowed_weapons():
		await tap_on(str(w.n))
		await _wait(0.1)
		var key := "%d card(s)%s" % [CreatorData.WC.get(w.id, []).size(), ", a modifier" if CreatorData.WM.has(w.id) else ""]
		if not groups.has(key):
			groups[key] = {}
		groups[key][w.id] = _marks(c, func(n: Node) -> bool:
			return n is Label and n.get_theme_font_size("font_size") == 11 and (n as Label).autowrap_mode != TextServer.AUTOWRAP_OFF and (n as Label).custom_minimum_size.x > 120.0)
		await shot("steady_gear_%s" % str(w.id))
	for key: String in groups:
		_same("gear, weapons with %s" % key, groups[key])
	# Spells: the pop-up's foot, with AP and Choose.
	seen = {}
	for klass: String in ["Wizard", "Cleric", "Bard"]:
		c.cls = klass
		c.spells = []
		c.go("spells")
		await _wait(0.5)
		var lists: Dictionary = Weapons.SPELLS_1[klass.to_lower()]
		for s: String in lists:
			for id: String in lists[s]:
				var nm := str(Cards.get_card(id).n)
				await tap_on(nm)
				await _wait(0.15)
				var choose := control("Choose")
				seen[id] = [roundi(choose.get_global_rect().position.y)] if choose else []
				await shot("steady_spells_%s" % id)
				await tap_on(nm)
				await _wait(0.1)
	_same("spells", seen)
	# Name: the hero's banner keeps its hexes where they were as the name grows.
	c.cls = "Fighter"
	c.go("name")
	await _wait(0.9)
	var edit := c.find_children("*", "LineEdit", true, false)[0] as LineEdit
	seen = {}
	for nm: String in ["", "Al", "Hilde Oakshield", "Bartholomew Ashgrove"]:
		edit.text = nm
		edit.text_changed.emit(nm)
		await _wait(0.2)
		seen["'%s'" % nm] = _marks(c, func(n: Node) -> bool: return n is CreatorBanners.Stitch)
		await shot("steady_name_%d" % nm.length())
	_same("name", seen)
