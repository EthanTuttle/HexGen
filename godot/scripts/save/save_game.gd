class_name SaveGame
extends RefCounted
## A campaign as data, and back (design/06 -> Saving). capture() reads a running Game into a plain dictionary; apply() writes
## one over a freshly opened Game. What is kept and what is rebuilt: the notes' saving plan, and SAVED / REBUILT below,
## which the save check holds Game's, MapBoard's and PartyWalker's variables against, so a new field gets noticed.
## A fight isn't saved mid-way (design/06): the last save before it stands on the fight's hex, and loading shows its pop-up.

const VERSION := 1

## Each class's variables, saved (in capture) or rebuilt from those on load (or not campaign state at all).
const SAVED := {
	"Game": ["rng", "deck", "party_tile", "party", "minute", "day", "encounters", "_encounter_count", "run", "gold", "potions", "xp",
		"level", "_picks", "_pick_options", "_spent_minutes", "_next_roll", "_ended", "finished", "regions", "order", "fights_won"],
	"MapBoard": ["terrains", "flow_dist", "flow_toward", "landmark_turns", "water_gates", "_troll_water", "raised_regions", "lift", "canyons"],
	"PartyWalker": ["has_raft", "facing"],
}
const REBUILT := {
	"Game": ["map", "rig", "clock", "party_node", "debug_fail_crossing", "debug_near_miss", "debug_auto_cross", "held", "busy",
		"_encounter_views", "walk_limited", "level_pick", "end_panel", "enter_town_screen", "event_screen", "fight", "real_time",
		"ui", "safe", "hud", "after", "_encounter_tile", "_open_pin", "_reveal_pin", "_reveal_until", "_slot_mats", "_shown_minute",
		"_slot_marks", "popup", "picked", "_path_marks", "_debug_fill", "force_map", "_fade", "_debug_map", "ambush"],
	"MapBoard": ["water_shapes", "boats", "slot_nodes", "_kit", "_ground", "_ground_img", "_ground_tex", "_tile_nodes", "_water_node",
		"_water_cache", "_water_mats", "_port_boats", "_still_mists", "_slots_node", "_slot_mesh", "_slot_mat", "_still_water", "_glow",
		"_lamp", "_st_glow", "_mist_mat", "_fey", "_window", "_web", "gates", "party_walks", "lightning", "_faint", "_graphs", "raised",
		"tiles_built", "streets", "party_at", "climbs", "_outer", "_corners", "_ledges", "_links", "_shape", "_lava", "_lantern_red",
		"canyon_stats", "_canyon_meshes", "_canyon_dirty", "_canyon_mat", "_gorge_rock", "_gorge_ground", "_fall_mat",
		"_gorge_foam_mat", "_dressing_cache", "_surface_cache", "gorge_build_us", "marsh_job_ms", "marsh_data_us", "marsh_build_us",
		"marsh_cover_us", "gorge_job_ms", "_feywild", "fey_job_ms", "fey_build_us", "_fey_material", "_fey_portal", "_marsh",
		"_marsh_water", "_prop_arrays", "_marsh_glow", "_features", "_clip_mats", "time_of_day", "_time", "cover_queue", "cover_view_first"],
	"PartyWalker": ["map", "members", "walking", "peeled", "_path", "_len", "_heights", "_s", "_trail", "_s0", "_file_start",
		"_file_end", "_tail", "speed_factor", "_raft", "_spans", "_span", "_landed", "_ride_t", "_riding", "free_out", "holding",
		"_on_raft", "_raft_at", "_gaps", "_start_gaps", "_t", "_start_facing", "_end_facing", "_tile", "_idle_in", "_footprints",
		"_entered", "_rock_at", "_rock_version", "_silhouette_on", "_silhouette", "_ledge_tops"],
}


## Variables of a class's script that are in neither list (the save check fails on any).
static func unlisted(script: Script, cls: String) -> Array:
	var out := []
	for p: Dictionary in script.get_script_property_list():
		if p.usage & PROPERTY_USAGE_SCRIPT_VARIABLE and not p.name in SAVED[cls] and not p.name in REBUILT[cls]:
			out.append(p.name)
	return out


static func _fields(obj: Object) -> Dictionary:
	var out := {}
	for p: Dictionary in obj.get_script().get_script_property_list():
		if p.usage & PROPERTY_USAGE_SCRIPT_VARIABLE:
			out[p.name] = obj.get(p.name)
	return out


static func _set_fields(obj: Object, d: Dictionary) -> void:
	for p: Dictionary in obj.get_script().get_script_property_list():
		if p.usage & PROPERTY_USAGE_SCRIPT_VARIABLE and d.has(p.name):
			var v = d[p.name]
			if obj.get(p.name) is Array and v is Array:
				(obj.get(p.name) as Array).assign(v)
			else:
				obj.set(p.name, v)


## Where the party stands, as a save's row says it (design/07 -> What a save shows). PLACEHOLDER (06 plan, approved): the
## finished region's name, the background's place on the starting tile, else the terrain's name.
static func place_of(g: Game) -> String:
	if g.finished.has(g.party_tile):
		return g.regions[g.finished[g.party_tile]].name
	if g.party_tile == Rules.START_TILE:
		return RunSetup.BACKGROUNDS.get(g.run.background, {}).get("place", "")
	return Rules.NAMES.get(g.land(g.party_tile), "")


static func capture(g: Game) -> Dictionary:
	var hero: Hero = Hero.current
	var encounters := []
	for t: Vector2i in g.encounters:
		var e: Dictionary = g.encounters[t].duplicate(true)
		e.erase("spot")
		e.expires_in = e.expires - g.real_time
		e.erase("expires")
		e.tile = t
		encounters.append(e)
	var canyons := {}   # one entry per canyon region (every tile of one shares the same info)
	for t: Vector2i in g.map.canyons:
		var c: Dictionary = g.map.canyons[t]
		if not canyons.has(c.landmark):
			canyons[c.landmark] = c.duplicate(true)
	var m := g.map
	return {
		version = VERSION,
		saved_at = int(Time.get_unix_time_from_system()),
		meta = {hero_id = hero.id if hero else "", name = g.party[0].name, level = g.level, place = place_of(g),
			subtitle = hero.subtitle(g.level) if hero else "", color = g.party[0].color, initial = g.party[0].initial},
		hero = _fields(hero) if hero else {},
		run = _fields(g.run),
		rng = {seed = g.rng.seed, state = g.rng.state},
		game = {party_tile = g.party_tile, day = g.day, minute = g.minute, gold = g.gold, potions = g.potions, xp = g.xp,
			level = g.level, picks = g._picks, pick_options = g._pick_options.duplicate(), spent_minutes = g._spent_minutes,
			next_roll = g._next_roll, ended = g._ended, fights_won = g.fights_won, encounter_count = g._encounter_count},
		party = g.party.duplicate(true),
		deck = {draw = g.deck.draw_pile.duplicate(), hand = g.deck.hand.duplicate(), discard = g.deck.discard.duplicate()},
		encounters = encounters,
		map = {terrains = m.terrains.duplicate(), order = g.order.duplicate(), finished = g.finished.duplicate(),
			regions = g.regions.duplicate(true), flow_dist = m.flow_dist.duplicate(), flow_toward = m.flow_toward.duplicate(),
			landmark_turns = m.landmark_turns.duplicate(), water_gates = m.water_gates.duplicate(true),
			troll_water = m._troll_water.duplicate(true), raised_regions = m.raised_regions.duplicate(true), canyons = canyons},
		walker = {has_raft = g.party_node.has_raft, facing = g.party_node.facing},
	}


## A Hero from a save's hero fields (Hero.current is set from it before the game scene opens).
static func hero_of(data: Dictionary) -> Hero:
	if data.hero.is_empty():
		return null
	var h := Hero.new()
	_set_fields(h, data.hero)
	return h


static func _tiles(a: Array) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	out.assign(a)
	return out


## Writes a save over a Game that has just opened (its _ready done): the party, deck, clock, encounters and the whole map.
static func apply(g: Game, data: Dictionary) -> void:
	var t0 := Time.get_ticks_msec()
	_set_fields(g.run, data.run)
	g.walk_limited = not g.run.wide_deck
	g.rng.seed = data.rng.seed
	g.rng.state = data.rng.state
	var s: Dictionary = data.game
	g.party_tile = s.party_tile
	g.day = s.day
	g.minute = s.minute
	g.gold = s.gold
	g.potions = s.potions
	g.xp = s.xp
	g.level = s.level
	g._picks = s.picks
	g._pick_options = s.pick_options
	g._spent_minutes = s.spent_minutes
	g._next_roll = s.next_roll
	g._ended = false            # the end panel opens again by itself if the goal was reached (design/06 -> Saving)
	g.fights_won = s.fights_won
	g._encounter_count = s.encounter_count
	g.party.assign(data.party)
	Hero.live = g.party[0].scores
	while g.party_node.members.size() < g.party.size():
		g.party_node.add_member(g.party[g.party_node.members.size()].mini)
	g.deck.draw_pile.assign(data.deck.draw)
	g.deck.hand.assign(data.deck.hand)
	g.deck.discard.assign(data.deck.discard)
	g.held = -1
	g.encounters.clear()
	for e: Dictionary in data.encounters:
		var d := e.duplicate(true)
		var t: Vector2i = d.tile
		d.erase("tile")
		d.expires = g.real_time + d.expires_in
		d.erase("expires_in")
		g.encounters[t] = d
	_apply_map(g, data.map)
	g.party_node.has_raft = data.walker.has_raft
	g.party_node.place_at(g.party_tile, data.walker.facing)
	g.party_node.speed_factor = Rules.WOOD_ELF_WALK if Races.wood_elf_in(g.party) else 1.0
	g.rig.frame(g.party_node.centre(), 58.0, 50.0)
	print("LOAD %d tiles in %d ms" % [g.map.terrains.size(), Time.get_ticks_msec() - t0])
	if LoadProfile.instance != null:
		LoadProfile.profile.apply_total = float(Time.get_ticks_msec() - t0)


static func _apply_map(g: Game, d: Dictionary) -> void:
	g.regions.clear()
	for r: Dictionary in d.regions:
		var region := r.duplicate(true)
		region.tiles = _tiles(region.tiles)
		if region.has("canyon_tiles"):
			region.canyon_tiles = _tiles(region.canyon_tiles)
		g.regions.append(region)
	g.finished = d.finished.duplicate()
	g.order = d.order.duplicate()
	restore_map(g.map, d, g.party_tile)


## A save's map on a MapBoard: the game's on load, the title's backdrop (design/07 -> Title screen: v1b, your last save).
## What depends on the map's history goes in first (trails, water gates, Troll Bridge water, raised regions, canyon mazes),
## then every tile in one retile, which works out the rest.
static func restore_map(m: MapBoard, d: Dictionary, party_tile: Vector2i) -> void:
	m.flow_dist = d.flow_dist.duplicate()
	m.flow_toward = d.flow_toward.duplicate()
	m.landmark_turns = d.landmark_turns.duplicate()
	m.water_gates = d.water_gates.duplicate(true)
	m._troll_water = d.troll_water.duplicate(true)
	var t0 := Time.get_ticks_usec()
	for key in d.raised_regions:
		m.set_raised(key, d.raised_regions[key])
	for lm: Vector2i in d.canyons:   # from its saved maze: a canyon that grew can't be worked out again from its tiles
		var region: Dictionary = d.regions[d.finished[lm]]
		var c: Dictionary = d.canyons[lm]
		m._keep_canyon(Canyon.generate(region.get("canyon_tiles", region.tiles), lm, c.turn, GroundCover.hash01(lm.x, lm.y, 80), {}, c))
	m.party_at = party_tile
	var all := {}
	for t: Vector2i in d.terrains:
		all[t] = d.terrains[t]
	if LoadProfile.instance != null:   # the load profile's timed copy of retile
		LoadProfile.profile.canyons_raised = (Time.get_ticks_usec() - t0) / 1000.0
		LoadProfile.restore_profiled(m, all)
	else:
		m.retile(all)


## The latest save of all heroes, or {} (the title's backdrop and Continue).
static func latest() -> Dictionary:
	var heroes := Saves.heroes()
	if heroes.is_empty() or heroes[0].autos.is_empty():
		return {}
	return Saves.read(heroes[0].id, heroes[0].autos[0].file)


## After apply, once the scene runs: what the party was in the middle of comes back (design/06 -> Saving): a fight's or an
## event's pop-up on its hex, owed level picks.
static func resume(g: Game) -> void:
	g._refresh()
	if g.encounters.has(g.party_tile):
		g.busy = true
		g._encounter_tile = g.party_tile
		if g.encounters[g.party_tile].entry.kind == "fight":
			g.hud.show_encounter(Rules.NAMES[g.land(g.party_tile)], "ask", [])
		else:
			g.open_event(g.party_tile)
	elif g._picks > 0 and not g._pick_options.is_empty():   # the same three, not rolled again
		g.busy = true
		g.level_pick.open(g.level - g._picks + 1, g._pick_options)
