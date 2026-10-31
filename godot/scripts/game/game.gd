class_name Game
extends Node3D
## The playable loop: place map cards from the hand, walk the party, fight encounters on the tile's
## combat board, and come back to the map with the hand refilled.
## Rules: design/02 Map & exploration.md, 03 Classes & combat.md, 05 Cards & progression.md; the numbers and
## every placeholder are in rules.gd. Screens: design/07 Presentation.md, built from the mockups
## (exploration v8b, combat v14, after combat v7).
##
## Map controls: click a card to hold it, click a lit slot to place it (Cancel or Esc lets go);
## click a placed tile to walk there. Camera: drag, wheel, right-drag, Q/E, F, or the nav button.

const COMBAT_AT := Vector2(1000, 0)   # the combat board lives away from the map
## DOCS: the backdrop per time of day (from Explore v8b; chosen Oct 30, 2026, revisit in playtesting):
## design/07 Presentation.md -> Art direction -> Time of day -> The light.
const SKY := {"night": "#A9AECB", "dawn": "#F4DCCB", "midday": "#D9E7EC", "dusk": "#EDCFD7"}

var rng := RandomNumberGenerator.new()
var deck: Deck
var map := MapBoard.new()
var rig := CameraRig.new()
var clock: TimeOfDay
var party_node: PartyWalker
var party_tile := Rules.START_TILE
var party: Array[Dictionary] = []     # per member: name, initial, color, mini, ability, score, hp, max_hp, cards
var held := -1                        # index into the hand, or -1
var busy := false                     # walking, in a pop-up or in a fight
var minute := Rules.START_MINUTE      # minutes into the 30-minute day
var day := 1
var encounters := {}                  # tile -> {expires, persistent, dropped}
var finished := {}                    # tile -> region index
var regions: Array[Dictionary] = []   # {terrain, tiles, name, landmark, landmark_tile, tier}
var order := {}                       # tile -> placement number (for "newest tile of a cluster")
var fight: Fight
var real_time := 0.0
var fights_won := 0

var ui := CanvasLayer.new()
var safe := SafeArea.new()            # the HUD's root: kept out of the Dynamic Island's strip
var hud: ExploreHud
var after: AfterCombat

var _encounter_tile := Vector2i.ZERO
var _open_pin = null
var _reveal_pin = null
var _reveal_until := 0.0
var _slot_mats := {}
var _shown_minute := -1.0             # the time the light shows (day * DAY_MINUTES + minute), easing after the clock
var _slot_marks: Array[Node3D] = []
var popup := BoardPopup.new()         # long-press / hover details
var picked = null                     # the hex a first tap picked to walk to (Vector2i), or null
var _path_marks: Array[Node3D] = []


func _ready() -> void:
	var seed_arg := "1"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--seed="):
			seed_arg = a.split("=")[1]
	rng.seed = hash(seed_arg)
	clock = Stage.create(self)
	clock.running = false
	clock.keys = sky_keys()
	clock.sun_step_hours = Rules.SUN_STEP_HOURS
	clock.sun_blend_seconds = Rules.SUN_BLEND_SECONDS

	map.time_of_day = clock
	add_child(map)
	map.place(Rules.START_TILE, Rules.START_TERRAIN)
	order[Rules.START_TILE] = 0

	for m in Rules.PARTY:
		var member: Dictionary = m.duplicate(true)
		member.max_hp = m.hp
		party.append(member)
	party_node = PartyWalker.new()
	party_node.name = "party"
	add_child(party_node)
	party_node.setup(map, party_tile)

	deck = Deck.new(Rules.STARTING_DECK, rng)
	deck.draw(Rules.STARTING_HAND)

	fight = Fight.new()
	fight.name = "fight"
	fight.position = Hex.to3(COMBAT_AT)
	fight.visible = false
	add_child(fight)

	add_child(rig)
	rig.min_distance = 8.0
	rig.max_distance = Rules.DAY_MAX_ZOOM
	rig.focus = Vector2(378, 200)       # Explore v8b: the open area left of the hand column
	rig.frame(party_node.centre(), 58.0, 50.0)
	_make_slot_materials()
	_warm_up.call_deferred()

	add_child(ui)
	ui.add_child(safe)
	hud = ExploreHud.new(self)
	safe.add_child(hud)
	after = AfterCombat.new()
	after.visible = false
	safe.add_child(after)
	safe.add_child(popup)
	_connect_gestures()
	_refresh()
	if PhoneCheck.wanted():
		add_child(PhoneCheck.new())
	if "--touchtest" in OS.get_cmdline_user_args():
		var tt := TouchTest.new()
		tt.game = self
		add_child(tt)
	elif Array(OS.get_cmdline_user_args()).any(func(x): return x.begins_with("--demo")):
		var demo := Demo.new()
		demo.game = self
		add_child(demo)


## TimeOfDay keys with the mockup's backdrop colours (lighting stays as in the look tests).
static func sky_keys() -> Array:
	var keys := []
	for k in TimeOfDay.KEYS:
		var row: Array = k.duplicate()
		var h: float = row[0]
		row[1] = SKY.night if (h <= 4.5 or h >= 20.0) else (SKY.dawn if h < 8.0 else (SKY.dusk if h >= 17.0 else SKY.midday))
		keys.append(row)
	return keys


func _refresh() -> void:
	hud.refresh()
	_light_slots()


func toast(text: String, good := true) -> void:
	hud.show_toast(text, good)


func held_terrain() -> String:
	return deck.hand[held] if held >= 0 and held < deck.hand.size() else ""


func _process(delta: float) -> void:
	real_time += delta
	if not fight.active:
		_advance(delta / 60.0)    # the day clock runs in real minutes; combat pauses it
	# The backdrop and light follow the clock, blending smoothly between the hours (DOCS: Art direction ->
	# Time of day -> The light; sky_keys() gives each phase's backdrop). The clock jumps when a card is placed,
	# a hex walked or the party rests, so the light glides after it rather than jumping (seen on the phone).
	var now := day * Rules.DAY_MINUTES + minute
	_shown_minute = now if _shown_minute < 0.0 else lerpf(_shown_minute, now, minf(1.0, delta / Rules.LIGHT_EASE_SECONDS))
	clock.hour = Rules.light_hour(fposmod(_shown_minute, Rules.DAY_MINUTES))
	# The camera follows the walking party, unless the player has moved it (DOCS: the player's camera wins).
	if party_node.walking and not rig.player_moved:
		rig.target = rig.target.lerp(party_node.centre(), minf(1.0, delta * 4.0))
	# At night the camera can't zoom all the way out (DOCS: Exploration screen -> Placing). The limit eases in
	# and out, so a zoomed-out camera glides in at nightfall instead of jumping on the next pinch.
	var most := Rules.NIGHT_MAX_ZOOM if Rules.is_night(minute) else Rules.DAY_MAX_ZOOM
	rig.max_distance = move_toward(rig.max_distance, most,
			delta * (Rules.DAY_MAX_ZOOM - Rules.NIGHT_MAX_ZOOM) / Rules.ZOOM_LIMIT_SECONDS)
	if rig.distance > rig.max_distance:
		rig.distance = rig.max_distance
	# Spawned encounters disappear after about 15 minutes unless a wipe made them stay (DOCS).
	for t in encounters.keys():
		var e: Dictionary = encounters[t]
		if not e.persistent and real_time > e.expires and t != party_tile:
			encounters.erase(t)
	if _reveal_pin != null and real_time > _reveal_until:
		_reveal_pin = null
	_pulse_slots()


func _advance(minutes: float) -> void:
	var was_night := Rules.is_night(minute)
	minute += minutes
	while minute >= Rules.DAY_MINUTES:
		minute -= Rules.DAY_MINUTES
		day += 1
	var night := Rules.is_night(minute)
	if night != was_night:
		if night:
			toast("Night falls. Build only within sight of the party, and find somewhere to rest.", false)
		_light_slots()


# --- Placing -----------------------------------------------------------------

func hold(i: int) -> void:
	if busy:
		return
	held = -1 if (held == i or i < 0) else i
	pick(null)
	_refresh()


## Holds card i as a drag out of the hand starts, but rebuilds the HUD and relights the slots on the next frame,
## so the drag's first frame stays light (Ethan: an unheld card didn't drag smoothly on the phone).
func hold_for_drag(i: int) -> void:
	if busy or held == i:
		return
	held = i
	pick(null)
	if not get_tree().process_frame.is_connected(_refresh):
		get_tree().process_frame.connect(_refresh, CONNECT_ONE_SHOT)


## Why a held card can't go on slot t, or "" if it can (DOCS: Placement).
func why_not(t: Vector2i, terrain: String) -> String:
	if map.terrains.has(t):
		return "That hex is already placed."
	if not map.slot_nodes.has(t):
		return "A card must go next to placed land."
	if absi(t.x) > Rules.MAP_LIMIT or absi(t.y) > Rules.MAP_LIMIT:
		return "Edge of the prototype map."
	if Rules.is_night(minute) and Rules.hex_distance(t, party_tile) > Rules.SIGHT_RANGE:
		return "Night: you can only build within sight of the party (%d hexes)." % Rules.SIGHT_RANGE
	for n in Hex.NEIGHBOURS:
		var other := land(t + n)
		if other != "" and Rules.banned(terrain, other):
			return "%s can't go next to %s." % [Rules.NAMES[terrain], Rules.NAMES.get(other, other)]
	return ""


func _make_slot_materials() -> void:
	var lit := StandardMaterial3D.new()
	lit.albedo_color = Color("#FCF7EE")
	lit.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	var banned := StandardMaterial3D.new()
	banned.albedo_color = Color("#E9C2B0")
	var dark := StandardMaterial3D.new()
	dark.albedo_color = Color(1, 1, 1, 0.3)
	dark.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_slot_mats = {lit = lit, banned = banned, dark = dark}


## Draws each slot material and slot icon once while loading, hidden under the board, so the renderer builds
## their pipelines now rather than in the middle of play (the Mobile renderer stalled for over a second the
## first time night darkened the far slots).
func _warm_up() -> void:
	var under := Node3D.new()
	under.name = "warm_up"
	add_child(under)
	var at := Hex.tile_position(party_tile.x, party_tile.y)
	for m: Material in _slot_mats.values():
		var mi := MeshInstance3D.new()
		mi.mesh = (map.slot_nodes.values()[0] as MeshInstance3D).mesh
		mi.material_override = m
		mi.position = Hex.to3(at, -1.0)   # under the tile: drawn (in view) but hidden by it
		under.add_child(mi)
	for icon in [["close", Color("#8E3B2E"), 0.8], ["t_plains", UI.terrain_ink("plains"), 0.55]]:
		var s := _slot_icon(party_tile, icon[0], icon[1], icon[2])
		s.reparent(under)
		s.position.y = -1.0
	for _f in 3:
		await get_tree().process_frame
	under.queue_free()


## Slots the held card can take light up (cream, pulsing, with the terrain's icon); slots it can't take
## next to a banned terrain turn red with a cross; at night, slots out of sight fade (Explore v8b).
func _light_slots() -> void:
	for m in _slot_marks:
		m.queue_free()
	_slot_marks.clear()
	var terrain := held_terrain()
	var night := Rules.is_night(minute)
	for t: Vector2i in map.slot_nodes:
		var mi: MeshInstance3D = map.slot_nodes[t]
		mi.material_override = null
		var far := night and Rules.hex_distance(t, party_tile) > Rules.SIGHT_RANGE
		if terrain == "":
			if far:
				mi.material_override = _slot_mats.dark
			continue
		var why := why_not(t, terrain)
		if why == "":
			mi.material_override = _slot_mats.lit
			_slot_marks.append(_slot_icon(t, "t_" + terrain, UI.terrain_ink(terrain), 0.55))
		elif why.contains("can't go next to"):
			mi.material_override = _slot_mats.banned
			_slot_marks.append(_slot_icon(t, "close", Color("#8E3B2E"), 0.8))
		elif far:
			mi.material_override = _slot_mats.dark


func _slot_icon(t: Vector2i, icon: String, col: Color, alpha: float) -> Sprite3D:
	var s := Sprite3D.new()
	s.texture = UI.icon(icon, col, 64, 2.2)
	s.axis = Vector3.AXIS_Y
	s.pixel_size = 3.4 / 128.0
	s.modulate.a = alpha
	s.shaded = false
	s.position = Hex.to3(Hex.tile_position(t.x, t.y), -0.26)
	add_child(s)
	return s


func _pulse_slots() -> void:
	# CSS litpulse: opacity 0.75 -> 1 -> 0.75 over 1.6 s
	_slot_mats.lit.albedo_color.a = 0.875 + 0.125 * sin(real_time * TAU / 1.6)


func try_place(t: Vector2i) -> bool:
	var terrain := held_terrain()
	if terrain == "" or busy:
		return false
	var why := why_not(t, terrain)
	if why != "":
		toast(why, false)
		return false
	deck.hand.remove_at(held)      # DOCS: placing never draws a new card
	held = -1
	map.place(t, terrain)
	order[t] = order.size()
	_advance(Rules.PLACE_MINUTES)
	hud.hide_toast()
	_check_region(t, terrain)
	_maybe_spawn(t)
	_refresh()
	return true


## The terrain of tile t ("" if empty). A finished region's tiles show its variant, but count as the terrain.
func land(t: Vector2i) -> String:
	return Variants.terrain_of(map.terrains.get(t))


## Connected tiles of one terrain (the starting hex is a Story card and joins none).
func cluster(t: Vector2i) -> Array[Vector2i]:
	var terrain := land(t)
	var seen := {t: true}
	var todo: Array[Vector2i] = [t]
	var out: Array[Vector2i] = []
	while not todo.is_empty():
		var c: Vector2i = todo.pop_back()
		out.append(c)
		for n in Hex.NEIGHBOURS:
			var m: Vector2i = c + n
			if not seen.has(m) and m != Rules.START_TILE and land(m) == terrain:
				seen[m] = true
				todo.append(m)
	return out


func _goal_for(terrain: String) -> int:
	return Rules.REGION_TIER2 if regions.any(func(g): return g.terrain == terrain) else Rules.REGION_TIER1


## Cluster goals and finished regions (DOCS: Clustered regions; draws: Core loop and hand refill).
func _check_region(t: Vector2i, terrain: String) -> void:
	var tiles := cluster(t)
	var joined := -1
	for c in tiles:
		if finished.has(c):
			joined = maxi(joined, finished[c])
	if joined >= 0:
		# A tile added to a finished region just expands it (the newer region if it touches two).
		for c in tiles:
			finished[c] = joined
		regions[joined].tiles = tiles
		_transform(tiles, regions[joined], t)
		toast("%s added to %s." % [Rules.NAMES[terrain], regions[joined].name])
		return
	var goal := _goal_for(terrain)
	if tiles.size() < goal:
		return
	var first := not regions.any(func(g): return g.terrain == terrain)
	var names: Array = Rules.REGION_NAMES.get(terrain, ["[Region]", "[landmark]"])
	var region := {terrain = terrain, tiles = tiles, tier = 1 if first else 2,
			name = names[0] if first else "[Tier 2 %s variant]" % Rules.NAMES[terrain].to_lower(),
			landmark = names[1] if first else "[landmark]",
			landmark_tile = tiles[rng.randi_range(0, tiles.size() - 1)]}
	regions.append(region)
	for c in tiles:
		finished[c] = regions.size() - 1
	_transform(tiles, region, t)
	var draw := Rules.DRAW_EASY_FIGHT if first else Rules.DRAW_TIER2_REGION
	var got := deck.draw(draw)
	var lost := draw - got.size()
	var over := deck.hand.size() - Rules.HAND_LIMIT
	_reveal_pin = region.landmark_tile
	_reveal_until = real_time + 3.5
	toast("%s! Region finished: draw %d%s. Landmark: %s.%s" % [region.name, draw,
			" (%d lost: deck empty, rest to reshuffle)" % lost if lost > 0 else "", region.landmark,
			" Hand %d/7: keep building; you discard down to 7 when you rest." % deck.hand.size() if over > 0 else ""])


## A finished region's tiles change to its variant's look (DOCS: Exploration screen -> Cluster goals; no rim).
## Only tier 1 has art: a tier 2 region keeps its terrain's look for now.
## PLACEHOLDER transition: a wave spreading from the tile that finished it; each tile sinks flat into the
## ground (0.22 s), swaps to the variant's pieces, then springs back up with a small overshoot (0.45 s).
func _transform(tiles: Array[Vector2i], region: Dictionary, from: Vector2i) -> void:
	if region.tier != 1:
		return
	var variant: String = Variants.TIER1[region.terrain]
	var todo := tiles.filter(func(c): return map.terrains[c] != variant)
	if todo.is_empty():
		return
	todo.sort_custom(func(a, b): return Rules.hex_distance(a, from) < Rules.hex_distance(b, from))
	busy = true
	const SINK := 0.22
	const STEP := 0.09
	for k in todo.size():
		var node := map.tile_node(todo[k])
		var tw := node.create_tween()
		tw.tween_interval(k * STEP)
		tw.tween_property(node, "scale:y", 0.04, SINK).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await get_tree().create_timer((todo.size() - 1) * STEP + SINK).timeout
	var changes := {}
	for c in todo:
		changes[c] = variant
	map.retile(changes)
	for k in todo.size():
		var node := map.tile_node(todo[k])
		node.scale.y = 0.04
		var tw := node.create_tween()
		tw.tween_interval(k * STEP * 0.6)
		tw.tween_property(node, "scale:y", 1.0, 0.45).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	await get_tree().create_timer((todo.size() - 1) * STEP * 0.6 + 0.45).timeout
	busy = false
	_refresh()


func toggle_pin(tile: Vector2i) -> void:
	_open_pin = null if _open_pin == tile else tile
	_reveal_pin = null


## Markers that stand over the board: cluster goals, the encounter, landmark pins.
func markers() -> Array:
	var out := []
	var seen := {}
	for t: Vector2i in map.terrains:
		if seen.has(t) or finished.has(t) or t == Rules.START_TILE:
			continue
		var cl := cluster(t)
		for c in cl:
			seen[c] = true
		if cl.size() < Rules.GOAL_SHOWS_AT:
			continue
		var newest: Vector2i = cl[0]
		for c in cl:
			if order.get(c, 0) > order.get(newest, 0):
				newest = c
		var goal := _goal_for(land(t))
		out.append({key = "goal%s" % newest, kind = "goal", text = str(goal - cl.size()), world = _tile_top(newest),
				aria = "Cluster goal: grow this %s to %d+ hexes" % [Rules.NAMES[land(t)].to_lower(), goal]})
	for t: Vector2i in encounters:
		out.append({key = "enc%s" % t, kind = "encounter", text = "", world = _tile_top(t)})
	if picked != null:
		# The first tap's walk: how far and how long (DOCS: Walking; the time is on the day clock).
		var n := path_to(picked).size()
		out.append({key = "walk%s" % picked, kind = "walk", world = _tile_top(picked), lift = 40,
				text = "%d hex%s · %d min" % [n, "" if n == 1 else "es", roundi(n * Rules.STEP_MINUTES)]})
	for g in regions:
		var lt: Vector2i = g.landmark_tile
		var open: bool = _open_pin == lt or _reveal_pin == lt
		out.append({key = "pin%s%s" % [lt, open], kind = "pin", text = "%s%s" % [g.landmark, open], world = _tile_top(lt),
				name = g.landmark, region = g.name, open = open, tile = lt, lift = 6})
	return out


func _tile_top(t: Vector2i) -> Vector3:
	return Hex.to3(Hex.tile_position(t.x, t.y), 1.2)


# --- Encounters --------------------------------------------------------------

## PLACEHOLDER spawn rule: a placement may spawn one encounter in its region (its cluster), on a random tile.
func _maybe_spawn(t: Vector2i) -> void:
	var tiles := cluster(t)
	var active := 0
	for c in tiles:
		if encounters.has(c):
			active += 1
	if active >= Rules.ENCOUNTERS_PER_REGION or rng.randf() >= Rules.ENCOUNTER_CHANCE:
		return
	var free := tiles.filter(func(c): return c != party_tile)
	if free.is_empty():
		return
	add_encounter(free[rng.randi_range(0, free.size() - 1)], false)


func add_encounter(t: Vector2i, persistent: bool, dropped: Array = []) -> void:
	if encounters.has(t):
		encounters[t].persistent = encounters[t].persistent or persistent
		encounters[t].dropped.append_array(dropped)
		return
	encounters[t] = {expires = real_time + Rules.ENCOUNTER_LIFETIME, persistent = persistent, dropped = dropped}


# --- Walking -----------------------------------------------------------------

func path_to(goal: Vector2i) -> Array[Vector2i]:
	var came := {party_tile: party_tile}
	var todo: Array[Vector2i] = [party_tile]
	while not todo.is_empty():
		var c: Vector2i = todo.pop_front()
		if c == goal:
			break
		for n in Hex.NEIGHBOURS:
			var m: Vector2i = c + n
			if map.terrains.has(m) and not came.has(m):
				came[m] = c
				todo.append(m)
	var path: Array[Vector2i] = []
	if not came.has(goal):
		return path
	var c := goal
	while c != party_tile:
		path.push_front(c)
		c = came[c]
	return path


## Walks the party along placed hexes one step at a time; the camera follows; the minis face the way
## they walk (DOCS: Exploration screen -> Walking). Stops on a hex with an encounter.
func walk_to(goal: Vector2i) -> void:
	if busy or goal == party_tile:
		return
	var path := path_to(goal)
	if path.is_empty():
		return
	busy = true
	held = -1
	pick(null)
	rig.player_moved = false   # PLACEHOLDER (what "the next action" is isn't decided): a new walk follows again
	_refresh()
	# The walk stops on the first hex with an encounter.
	for i in path.size():
		if encounters.has(path[i]):
			path = path.slice(0, i + 1)
			break
	# The day clock moves on as the hero steps onto each hex (PartyWalker: How the party moves).
	var on_step := func(t: Vector2i):
		party_tile = t
		_advance(Rules.STEP_MINUTES)
	party_node.entered.connect(on_step)
	await party_node.walk(path)
	party_node.entered.disconnect(on_step)
	party_tile = path[-1]
	if encounters.has(party_tile):
		_encounter_tile = party_tile
		hud.show_encounter(Rules.NAMES[land(party_tile)], "ask", [])
		return
	busy = false
	_refresh()


## Stealth group check (DOCS: a group check; on a pass the encounter stays on the map).
## PLACEHOLDER (Explore v8b's text): everyone flips one coin; 1 heads passes. A fail starts the fight.
func choose_sneak() -> void:
	var coins: Array[bool] = []
	for m in party:
		coins.append_array(Coins.flip(rng, Rules.SNEAK_COINS_EACH))
	var ok := Coins.heads(coins) >= 1
	hud.show_encounter(Rules.NAMES[land(_encounter_tile)], "passed" if ok else "spotted", coins)


func choose_carry_on() -> void:
	hud.hide_encounter()
	busy = false
	_refresh()


func choose_fight() -> void:
	hud.hide_encounter()
	start_fight(_encounter_tile)


# --- Fights ------------------------------------------------------------------

func start_fight(t: Vector2i) -> void:
	busy = true
	pick(null)
	popup.visible = false
	_encounter_tile = t
	map.visible = false
	party_node.visible = false
	for m in _slot_marks:
		m.visible = false
	hud.visible = false
	fight.visible = true
	var distance := Rules.hex_distance(t, Rules.START_TILE)
	var foes := mini(Rules.ENEMIES_BASE + distance / Rules.ENEMIES_PER_DISTANCE, Rules.ENEMIES_MAX)
	var won: bool = await fight.run(self, land(t), t, foes)
	var downed := {}
	for m in party:
		downed[m.name] = m.hp <= 0
	var drawn: Array[String] = []
	var dropped: Array = []
	if won:
		fights_won += 1
		var back: Array = encounters[t].dropped
		encounters.erase(t)
		for m in party:
			m.hp = maxi(m.hp, Rules.REVIVE_HP)
		drawn = deck.draw(Rules.DRAW_EASY_FIGHT)
		for card in back:
			deck.hand.append(card)
		dropped = back
	else:
		# DOCS: on a wipe the party retreats to its most recent camp and the hand is dropped; the
		# encounter stays until cleared, and clearing it recollects the cards.
		dropped = deck.hand.duplicate()
		deck.hand.clear()
		add_encounter(t, true, dropped)
		for m in party:
			m.hp = Rules.REVIVE_HP
	held = -1
	after.show_result(self, won, downed, drawn, dropped)
	await after.done
	after.visible = false
	fight.visible = false
	map.visible = true
	if not won:
		party_tile = Rules.START_TILE
	party_node.place_at(party_tile)
	party_node.visible = true
	hud.visible = true
	rig.frame(party_node.centre(), 58.0, 50.0)
	busy = false
	if not won:
		toast("The party fell back to camp. %d card%s dropped where they fell: win that fight to get them back." % [
				dropped.size(), "" if dropped.size() == 1 else "s"], false)
	_refresh()


# --- Rest --------------------------------------------------------------------

## Resting at camp (DOCS: Camps and rest): heal, +8 hours, discard down to 7, reshuffle the discard
## pile into the deck. Draws nothing. DOCS (Resting): the Rest action card along the bottom, shown while the
## party stands on a camp. PLACEHOLDER: the camp is the start hex.
func rest() -> void:
	if busy or party_tile != Rules.START_TILE:
		return
	for m in party:
		m.hp = m.max_hp
	var dropped := deck.rest()
	_advance(Rules.REST_MINUTES)
	held = -1
	toast("Rested at camp: HP restored, 8 hours passed%s, discard pile reshuffled." % [", discarded down to 7" if dropped else ""])
	_refresh()


# --- Camera buttons (nav) ------------------------------------------------------

func camera_button(which: String) -> void:
	if which != "center":
		rig._player()   # the player's camera wins (DOCS: Camera and controls)
	match which:
		"zoom_in":
			rig._zoom(0.8)
		"zoom_out":
			rig._zoom(1.25)
		"rot_l":
			rig.ease_to(rig.target, rig.distance, rig.yaw_deg + Rules.ROTATE_STEP)
		"rot_r":
			rig.ease_to(rig.target, rig.distance, rig.yaw_deg - Rules.ROTATE_STEP)
		"center":
			rig.player_moved = false   # the centre button gives the camera back to the game
			rig.ease_to(party_node.centre(), rig.distance, rig.yaw_deg)


# --- Input -------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if fight.active or after.visible:
		return
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_ESCAPE:
		hold(-1)


## Board gestures (Gestures, on the camera rig): a tap picks, a long-press or a resting mouse shows details,
## any pan, pinch or twist closes the pop-up.
func _connect_gestures() -> void:
	var g := rig.gestures
	g.tap.connect(func(pos: Vector2):
		popup.visible = false
		if not fight.active and not after.visible:
			tap(ground_tile(pos)))
	g.long_press.connect(func(pos: Vector2):
		if not fight.active and not after.visible:
			_details(pos))
	g.hover.connect(func(pos: Vector2):
		if not fight.active and not after.visible and not hud.encounter_open():
			_details(pos))
	g.hover_end.connect(func(): popup.visible = false)
	g.drag.connect(func(_r): popup.visible = false)
	g.pinch.connect(func(_f): popup.visible = false)
	g.gui_long_press.connect(func(c: Control, pos: Vector2):
		# A HUD control's details: what hover shows on PC (its tooltip text), first part as the title.
		var parts := Array(c.tooltip_text.split(","))
		popup.show_at(pos, parts[0], parts.slice(1).map(func(x): return str(x).strip_edges())))


## The map hex pop-up (DOCS: Camera and controls -> Long-press on the board): its terrain, its region and
## progress toward the cluster goal, the region's variant once finished; an encounter on it, if any.
func _details(pos: Vector2) -> void:
	var t := ground_tile(pos)
	if not map.terrains.has(t):
		popup.visible = false
		return
	var lines := []
	var title: String
	if t == Rules.START_TILE:
		title = "Starting hex"
		lines.append("Camp (stand-in): rest here")
	elif finished.has(t):
		var g: Dictionary = regions[finished[t]]
		title = Rules.NAMES[g.terrain]
		lines.append("Region: %s, finished (%d hexes)" % [g.name, g.tiles.size()])
		lines.append("Variant: %s" % (Rules.REGION_NAMES[g.terrain][0] if g.tier == 1 else "[tier 2 variant]"))
		lines.append("Landmark: %s" % g.landmark)
	else:
		var terrain := land(t)
		title = Rules.NAMES[terrain]
		var goal := _goal_for(terrain)
		lines.append("Cluster: %d / %d hexes to a region" % [cluster(t).size(), goal])
	if encounters.has(t):
		lines.append("Encounter: [Enemy group], %d foes" % _foes_at(t))
	popup.show_at(pos, title, lines)


func _foes_at(t: Vector2i) -> int:
	var distance := Rules.hex_distance(t, Rules.START_TILE)
	return mini(Rules.ENEMIES_BASE + distance / Rules.ENEMIES_PER_DISTANCE, Rules.ENEMIES_MAX)


## Walking is two taps (DOCS: Exploration screen -> Walking): the first shows the path and how long the
## walk takes, the same hex again walks, another hex picks that one instead. null clears the pick.
func pick(t) -> void:
	for m in _path_marks:
		m.queue_free()
	_path_marks.clear()
	picked = t
	if t == null:
		return
	var path := path_to(t)
	if path.is_empty():
		picked = null
		return
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.no_depth_test = true          # drawn over trees and houses, so the whole path shows
	mat.albedo_color = Color("#FCF7EE")
	var dot := SphereMesh.new()
	dot.radius = 0.2   # PLACEHOLDER look: no mockup shows the path yet
	dot.height = 0.08
	dot.material = mat
	var prev := Hex.tile_position(party_tile.x, party_tile.y)
	for step in path:
		var at := Hex.tile_position(step.x, step.y)
		for k in 3:   # three dots per step, from the last hex to this one
			var mi := MeshInstance3D.new()
			mi.mesh = dot
			mi.position = Hex.to3(prev.lerp(at, (k + 1) / 3.0), 0.3)
			mi.scale = Vector3.ONE * (1.6 if k == 2 and step == path[-1] else 1.0)
			add_child(mi)
			_path_marks.append(mi)
		prev = at


func ground_point(screen: Vector2) -> Vector2:
	var cam := rig.camera
	var o := cam.project_ray_origin(screen)
	var d := cam.project_ray_normal(screen)
	if absf(d.y) < 1e-4:
		return Vector2(INF, INF)
	var p := o + d * (-o.y / d.y)
	return Vector2(p.x, -p.z)


func ground_tile(screen: Vector2) -> Vector2i:
	return GroundCover.tile_at(ground_point(screen))


func tap(t: Vector2i) -> void:
	if busy or hud.encounter_open():
		return
	if held >= 0:
		if map.terrains.has(t):
			toast("That hex is already placed.", false)
		elif map.slot_nodes.has(t):
			try_place(t)
	elif map.terrains.has(t):
		if t == party_tile:
			pick(null)
		elif picked == t:
			walk_to(t)
		else:
			pick(t)
			_refresh()
	else:
		pick(null)
		_refresh()
