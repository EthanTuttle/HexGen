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
var debug_fail_crossing := false      # a test aid: every crossing check fails
var debug_near_miss := 0              # a test aid: the hero lands 1 heads short; the helper's coin saves it (1) or not (-1)
var debug_auto_cross := false         # a test aid: no pop-ups for crossings or the shop (the checks' walks), flips still count
var party: Array[Dictionary] = []     # per member: name, initial, color, mini, ability, score, hp, max_hp, cards
var held := -1                        # index into the hand, or -1
var busy := false                     # walking, in a pop-up or in a fight
var minute := Rules.START_MINUTE      # minutes into the 30-minute day
var day := 1
var encounters := {}                  # tile -> {expires, persistent, dropped}
var finished := {}                    # tile -> region index
var regions: Array[Dictionary] = []   # {terrain, tiles, name, landmark, landmark_tile, tier, variant}
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
var _debug_fill := {}                 # spawn_forest_regions' plains (no cluster goal)


func _ready() -> void:
	var seed_arg := "1"
	debug_auto_cross = Array(OS.get_cmdline_user_args()).any(func(a): return a.ends_with("check") or a.begins_with("--demo") or a == "--touchtest")
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
	rig.floor_at = map.camera_floor
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
	if "--forest" in OS.get_cmdline_user_args():
		spawn_forest_regions()
	elif "--farmcheck" in OS.get_cmdline_user_args():
		var fm := FarmCheck.new()
		fm.game = self
		add_child(fm)
	elif "--rivercheck" in OS.get_cmdline_user_args():
		var rc := RiverCheck.new()
		rc.game = self
		add_child(rc)
	elif "--towncheck" in OS.get_cmdline_user_args():
		var tc := TownCheck.new()
		tc.game = self
		add_child(tc)
	elif "--hillscheck" in OS.get_cmdline_user_args():
		var hc := HillsCheck.new()
		hc.game = self
		add_child(hc)
	elif "--plainscheck" in OS.get_cmdline_user_args():
		var pc := PlainsCheck.new()
		pc.game = self
		add_child(pc)
	elif "--gorgecheck" in OS.get_cmdline_user_args():
		var gc := GorgeCheck.new()
		gc.game = self
		add_child(gc)
	elif "--desertcheck" in OS.get_cmdline_user_args():
		var dc := DesertCheck.new()
		dc.game = self
		add_child(dc)
	elif "--forestcheck" in OS.get_cmdline_user_args():
		var fc := ForestCheck.new()
		fc.game = self
		add_child(fc)
	if PhoneCheck.wanted():
		add_child(PhoneCheck.new())
	if debug_auto_cross:
		var sw := StallWatch.new()
		sw.game = self
		add_child(sw)
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
		_light_slots()   # the dial and the faded slots show night: no toast (DOCS: UI -> Screen text)


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
		return "Already placed"
	if not map.slot_nodes.has(t):
		return "Must touch placed land"
	if absi(t.x) > Rules.MAP_LIMIT or absi(t.y) > Rules.MAP_LIMIT:
		return "Edge of the map"
	if Rules.is_night(minute) and Rules.hex_distance(t, party_tile) > Rules.SIGHT_RANGE:
		return "Out of sight at night"
	for n in Hex.NEIGHBOURS:
		var other := land(t + n)
		if other != "" and Rules.banned(terrain, other):
			return "Clashes with %s" % Rules.NAMES.get(other, other)
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
	# The desert's: canyon rock, the minis' silhouette, heat shimmer.
	var rock := MeshInstance3D.new()
	rock.mesh = (map.slot_nodes.values()[0] as MeshInstance3D).mesh
	rock.material_override = map._canyon_material()
	rock.material_overlay = _silhouette_material()
	rock.position = Hex.to3(at, -1.0)
	under.add_child(rock)
	var heat := DesertFx.shimmer(Hex.to3(at, -3.0))
	under.add_child(heat)
	for _f in 3:
		await get_tree().process_frame
	under.queue_free()


func _silhouette_material() -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/mini_silhouette.gdshader")
	return m


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
		elif why.begins_with("Clashes"):
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
	# A hills tile touching a raised region always joins it and rises, so low hills don't stand beside one (DOCS:
	# design/06 -> Tile build); the newer one if it touches two.
	var up := -1
	for c in tiles:
		if not finished.has(c):
			for n in Hex.NEIGHBOURS:
				var g: int = finished.get(c + n, -1)
				if g >= 0 and regions[g].variant in Cliffs.RAISED:
					up = maxi(up, g)
	if up >= 0:
		joined = up
	if joined >= 0:
		# A tile added to a finished region just expands it (the newer region if it touches two). Finished
		# regions that touch stay separate (DOCS: Merging finished regions), so only unfinished tiles join.
		for c in tiles:
			if not finished.has(c):
				finished[c] = joined
				regions[joined].tiles.append(c)
		_transform(regions[joined].tiles, regions[joined], t)   # no toast: the region visibly grows
		return
	var goal := _goal_for(terrain)
	if tiles.size() < goal:
		return
	var first := not regions.any(func(g): return g.terrain == terrain)
	var variant: String = Variants.TIER1[terrain] if first else _roll_tier2(terrain)
	var region := new_region(terrain, tiles, variant, _landmark_tile(variant, tiles))
	_transform(tiles, region, t)
	var draw := Rules.DRAW_EASY_FIGHT if first else Rules.DRAW_TIER2_REGION
	deck.draw(draw)
	_reveal_pin = region.landmark_tile
	_reveal_until = real_time + 3.5
	# No draw amounts or hand-limit notes (DOCS: UI -> Screen text); the hand and its count show them.
	toast("%s! Landmark: %s" % [region.name, region.landmark])


## Which of a finished region's tiles gets its landmark: at random, from the tiles where it fits (DOCS: design/02 ->
## Crossing water, Bridges on rapids). If none fits, a random tile keeps the plain look (region_look); no 7- or 12-tile
## rapids region tested by the art session came to that.
func _landmark_tile(variant: String, tiles: Array[Vector2i], placed := {}) -> Vector2i:
	var lm: String = Variants.LANDMARK_OF.get(variant, "")
	var fits := tiles.filter(func(c): return _landmark_fits(lm, variant, c, tiles, placed))
	var from: Array = fits if not fits.is_empty() else tiles
	return from[rng.randi_range(0, from.size() - 1)]


func _landmark_fits(lm: String, variant: String, c: Vector2i, tiles: Array[Vector2i], placed: Dictionary) -> bool:
	if not Water.FAMILY.has(lm):
		return true
	var mask := []
	var near := []
	for n in Hex.NEIGHBOURS:
		var x = variant if tiles.has(c + n) else placed.get(c + n, map.terrains.get(c + n))
		near.append(x)
		mask.append(Variants.is_water(x))
	var widths := Water.edge_widths(variant, near)
	if Water.FAMILY.get(variant) == "rapids":
		widths = Water.with_falls(widths, mask, c.x, c.y)
	return Water.landmark_fits(lm, mask, "%d,%d" % [c.x, c.y], widths)


## Records a finished region. variant "" means a tier 2 region with no art yet (it keeps its terrain's look).
func new_region(terrain: String, tiles: Array[Vector2i], variant: String, landmark_tile: Vector2i) -> Dictionary:
	var tier := 1 if variant == Variants.TIER1[terrain] else 2
	var names: Array = Rules.REGION_NAMES.get(terrain, ["[Region]", "[landmark]"]) if tier == 1 \
			else Variants.TIER2_NAMES.get(variant, ["[Tier 2 %s variant]" % Rules.NAMES[terrain].to_lower(), "[landmark]"])
	var region := {terrain = terrain, tiles = tiles, tier = tier, variant = variant, name = names[0],
			landmark = names[1], landmark_tile = landmark_tile}
	if variant == "oasis":   # DOCS (design/02 -> Landmarks): an oasis converts two, the pool tile and the Bazaar beside it
		var two := DesertLands.oasis_tiles(tiles)
		if not two.is_empty():
			region.landmark_tile = two[0]
			region.pool_tile = two[1]
	regions.append(region)
	for c in tiles:
		finished[c] = regions.size() - 1
	return region


## A later region's tier 2 variant (DOCS: rolled at random with a slight lean from neighbouring terrain).
## PLACEHOLDER: an even roll with no lean (the lean isn't set). Terrains with no tier 2 art yet give "".
func _roll_tier2(terrain: String) -> String:
	var pool: Array = Variants.TIER2.get(terrain, [])
	return pool[rng.randi_range(0, pool.size() - 1)] if not pool.is_empty() else ""


## The look a finished region's tile takes: its landmark's on the landmark tile (where the variant has landmark
## art), else the variant's.
func region_look(region: Dictionary, c: Vector2i) -> String:
	if c == region.get("pool_tile"):
		return "oasispool"
	var lm: String = Variants.LANDMARK_OF.get(region.variant, "")
	if lm == "" or c != region.landmark_tile or not _landmark_fits(lm, region.variant, c, region.tiles, {}):
		return region.variant
	return lm


## Sets a region's landmark trails (DOCS: Tile build -> Trails to the landmark), once, when it finishes.
func _set_flow(region: Dictionary) -> void:
	if region.get("flowed", false) or not Variants.LANDMARK_OF.has(region.variant):
		return
	region.flowed = true
	map.set_flow(region.tiles, region.landmark_tile, region.variant, region.get("pool_tile"))


## A raised region comes up over a few seconds with dust and shaking, carrying the party, and nobody walks until it's
## done (DOCS: design/06 -> Raised hills regions; hills kit -> The rise). Also when a later hills tile joins it.
func _rise(region: Dictionary) -> void:
	map.party_at = party_tile
	var r := map.begin_rise(regions.find(region), region.tiles)
	if r.rising.is_empty():
		map.finish_rise(r)
		return
	party_node.gather()
	var carried: bool = r.rising.has(party_tile)
	var dust := PackedVector2Array()
	for t: Vector2i in r.rising:
		var c := Hex.tile_position(t.x, t.y)
		for i: int in map._outer.get(t, []):
			var along := Water.normal(i).orthogonal()
			for u in [-1.5, 0.0, 1.5]:
				dust.append(c + Water.normal(i) * Hex.A + along * u)
	RiseDust.start(map, dust, Rules.RISE_SECONDS)
	var t := 0.0
	var y := 0.0
	while t < Rules.RISE_SECONDS:
		await get_tree().process_frame
		t += get_process_delta_time()
		var u := clampf(t / Rules.RISE_SECONDS, 0.0, 1.0)
		var now := Variants.RAISE * smoothstep(0.0, 1.0, u)
		map.set_lift(r.rising, now)
		if carried:
			party_node.lift_by(now - y)
		y = now
		rig.shake = Rules.RISE_SHAKE * minf(1.0, (1.0 - u) * 4.0)
	rig.shake = 0.0
	map.finish_rise(r)
	party_node.settle_up()


## Debug (`-- --forest`, or F9 on PC): a finished 7-tile region of each forest and farmland variant, each with its
## landmark on a random tile, plus a market town and a tier 0 farm and village group, around the start with plains
## between, made at once by the same rules as a region finishing.
const DEBUG_FOREST := {"deep_forest": Vector2i(3, -3), "fey_wood": Vector2i(3, 0), "dark_wood": Vector2i(0, 3),
	"heartwood": Vector2i(-3, 3)}
const DEBUG_FARM := {"windmill_country": Vector2i(-3, 0), "haunted_homesteads": Vector2i(0, -3),
	"raided_farms": Vector2i(6, -3), "cider_orchards": Vector2i(-6, 3)}
const DEBUG_PLAINS := {"meadows": Vector2i(0, 6), "battlefield": Vector2i(0, -7), "stormy_plains": Vector2i(-5, -2),
	"tourney_fields": Vector2i(-5, 6)}   # 12 tiles each (DEBUG_PLAINS_SHAPE), so the density bands show
const DEBUG_PLAINS_SHAPE := [Vector2i(1, -1), Vector2i(0, 0), Vector2i(1, 0), Vector2i(0, 1), Vector2i(-1, 1), Vector2i(-1, 0),
	Vector2i(0, -1), Vector2i(1, 1), Vector2i(0, 2), Vector2i(-1, 2), Vector2i(-2, 2), Vector2i(-2, 1)]   # its landmark first
const DEBUG_HILLS := {"highlands": Vector2i(10, -6), "snowy_peaks": Vector2i(11, -13), "volcanic_peaks": Vector2i(-12, 2),
	"monastery_heights": Vector2i(-10, 12)}   # 12 tiles each, raised, with plains laid to them
const DEBUG_TOWNS := {"fortified_town": Vector2i(5, -12), "slums": Vector2i(4, 11), "scholars_town": Vector2i(-7, -11)}   # 12 tiles each, like plains
const DEBUG_RIVERS := {"delta": Vector2i(16, -2), "great_lake": Vector2i(15, 7), "rapids": Vector2i(-17, 8), "still_waters": Vector2i(-16, -4)}   # with plains laid to them
const DEBUG_RIVER_SHAPES := {   # channels for the delta and rapids, so islands and bridges fit; pools for the others
	"delta": [Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0), Vector2i(3, -1), Vector2i(4, -2), Vector2i(-1, 0), Vector2i(-2, 1)],
	"great_lake": DEBUG_PLAINS_SHAPE,
	"rapids": [Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, -1), Vector2i(3, -1), Vector2i(4, -2), Vector2i(-1, 0), Vector2i(-2, 1)],
	"still_waters": DEBUG_PLAINS_SHAPE}
const DEBUG_RIVER_T0 := [Vector2i(13, 3), Vector2i(14, 3), Vector2i(15, 2), Vector2i(16, 2), Vector2i(17, 1), Vector2i(17, 2), Vector2i(18, 1)]   # tier 0: a river into a small lake
const DEBUG_DESERTS := ["wasteland", "badlands", "oasis", "canyon"]   # 12 tiles each, like plains; where's found at the spawn
const DEBUG_HILLS_T0 := Vector2i(9, 2)    # tier 0: a hills group, and one lone tile beside it
const DEBUG_TOWN := Vector2i(6, 0)       # a market town region
const DEBUG_FARMS := Vector2i(3, 3)      # tier 0: farmland in the middle and half the ring, village the other half

func spawn_forest_regions() -> void:
	var changes := {}
	var wanted := DEBUG_FOREST.duplicate()
	wanted.merge(DEBUG_FARM)
	wanted["market_town"] = DEBUG_TOWN
	for v: String in DEBUG_PLAINS:
		var tiles: Array[Vector2i] = []
		for s: Vector2i in DEBUG_PLAINS_SHAPE:
			tiles.append(DEBUG_PLAINS[v] + s)
		if tiles.any(func(x): return map.terrains.has(x)):
			continue
		var region := new_region("plains", tiles, v, tiles[0])
		_set_flow(region)
		for x in tiles:
			changes[x] = region_look(region, x)
			order[x] = order.size()
	for v: String in wanted:
		var c: Vector2i = wanted[v]
		var tiles: Array[Vector2i] = [c]
		for n in Hex.NEIGHBOURS:
			tiles.append(c + n)
		if tiles.any(func(x): return map.terrains.has(x)):
			continue
		var region := new_region(Variants.terrain_of(v), tiles, v, tiles[rng.randi_range(0, tiles.size() - 1)])
		_set_flow(region)
		for x in tiles:
			changes[x] = region_look(region, x)
			order[x] = order.size()
	for v: String in DEBUG_HILLS:
		var tiles: Array[Vector2i] = []
		for s: Vector2i in DEBUG_PLAINS_SHAPE:
			tiles.append(DEBUG_HILLS[v] + s)
		if tiles.any(func(x): return map.terrains.has(x) or changes.has(x)):
			continue
		var region := new_region("hills", tiles, v, tiles[0])
		_set_flow(region)
		if v in Cliffs.RAISED:
			map.set_raised(regions.size() - 1, tiles)
		for x in tiles:
			changes[x] = region_look(region, x)
			order[x] = order.size()
		_debug_road(DEBUG_HILLS[v] + Vector2i(-3, 3), changes)
	for v: String in DEBUG_RIVERS:
		var tiles: Array[Vector2i] = []
		var river_shape: Array = DEBUG_RIVER_SHAPES[v]
		for s: Vector2i in river_shape:
			tiles.append(DEBUG_RIVERS[v] + s)
		if tiles.any(func(x): return map.terrains.has(x) or changes.has(x)):
			continue
		var placed := changes.duplicate()
		var region := new_region("river", tiles, v, _landmark_tile(v, tiles, placed))
		_set_flow(region)
		for x in tiles:
			changes[x] = v if x != region.landmark_tile or not _landmark_fits(Variants.LANDMARK_OF[v], v, x, tiles, placed) else Variants.LANDMARK_OF[v]
			order[x] = order.size()
		_debug_road(DEBUG_RIVERS[v] + Vector2i(-3, 3), changes)
	for k in DEBUG_RIVER_T0.size():
		var x: Vector2i = DEBUG_RIVER_T0[k]
		if not map.terrains.has(x) and not changes.has(x):
			changes[x] = "river"
			order[x] = order.size()
			_debug_fill[x] = true
	_debug_road(DEBUG_RIVER_T0[0] + Vector2i(-1, 2), changes)
	for v: String in DEBUG_TOWNS:
		var tiles: Array[Vector2i] = []
		for s: Vector2i in DEBUG_PLAINS_SHAPE:
			tiles.append(DEBUG_TOWNS[v] + s)
		if tiles.any(func(x): return map.terrains.has(x) or changes.has(x)):
			continue
		var region := new_region("village", tiles, v, tiles[0])
		_set_flow(region)
		for x in tiles:
			changes[x] = region_look(region, x)
			order[x] = order.size()
		_debug_road(DEBUG_TOWNS[v] + Vector2i(-3, 3), changes)
		if v == "fortified_town":   # a plain village and a farm against its walls
			for x: Vector2i in [DEBUG_TOWNS[v] + Vector2i(2, -1), DEBUG_TOWNS[v] + Vector2i(2, 0), DEBUG_TOWNS[v] + Vector2i(1, 2)]:
				if not changes.has(x) and not map.terrains.has(x):
					changes[x] = "farmland" if x == DEBUG_TOWNS[v] + Vector2i(1, 2) else "village"
					order[x] = order.size()
					_debug_fill[x] = true
	for k in 7:
		var x: Vector2i = DEBUG_HILLS_T0 + (Vector2i.ZERO if k == 6 else Hex.NEIGHBOURS[k])
		if not map.terrains.has(x) and not changes.has(x):
			changes[x] = "hills"
			order[x] = order.size()
			_debug_fill[x] = true
	changes[DEBUG_HILLS_T0 + Vector2i(3, 0)] = "hills"
	_debug_fill[DEBUG_HILLS_T0 + Vector2i(3, 0)] = true
	_debug_road(DEBUG_HILLS_T0 + Vector2i(-2, 0), changes)
	for k in 7:
		var x: Vector2i = DEBUG_FARMS + (Vector2i.ZERO if k == 6 else Hex.NEIGHBOURS[k])
		if not map.terrains.has(x):
			changes[x] = "village" if k < 3 else "farmland"
			order[x] = order.size()
			_debug_fill[x] = true
	_spawn_deserts(changes)
	# Plains between them, so the party can walk there (they show no cluster goal).
	var land_now := changes.keys()
	land_now.append(Rules.START_TILE)
	for t: Vector2i in land_now:
		for n in Hex.NEIGHBOURS:
			var x: Vector2i = t + n
			if not changes.has(x) and not map.terrains.has(x):
				changes[x] = "plains"
				order[x] = order.size()
				_debug_fill[x] = true
	map.retile(changes)
	_refresh()


## Debug: a 12-tile region of each desert variant and a tier 0 group, on free land out past the rest, with plains laid to them.
func _spawn_deserts(changes: Dictionary) -> void:
	for v: String in DEBUG_DESERTS:
		var anchor := _free_spot(DEBUG_PLAINS_SHAPE, changes)
		var tiles: Array[Vector2i] = []
		for s: Vector2i in DEBUG_PLAINS_SHAPE:
			tiles.append(anchor + s)
		var region := new_region("desert", tiles, v, tiles[0])
		_set_flow(region)
		if v == "canyon":
			region.canyon_tiles = tiles.duplicate()
			map.generate_canyon(tiles, region.landmark_tile)
		for x in tiles:
			changes[x] = region_look(region, x)
			order[x] = order.size()
		_debug_road(anchor + Vector2i(-3, 3), changes)
	var t0: Array = [Vector2i.ZERO]
	t0.append_array(Hex.NEIGHBOURS)
	var at := _free_spot(t0, changes)
	for s: Vector2i in t0:
		changes[at + s] = "desert"
		order[at + s] = order.size()
		_debug_fill[at + s] = true
	_debug_road(at + Vector2i(-2, 2), changes)


## Debug: the nearest place to the start where a shape, and a tile's margin round it, is empty.
func _free_spot(shape: Array, changes: Dictionary) -> Vector2i:
	for r in range(8, Rules.MAP_LIMIT):
		for q in range(-r, r + 1):
			for s in range(-r, r + 1):
				var c := Vector2i(q, s)
				if Rules.hex_distance(c, Rules.START_TILE) != r:
					continue
				var free := true
				for x: Vector2i in shape:
					for n in [Vector2i.ZERO, Vector2i(1, 0), Vector2i(1, -1), Vector2i(0, -1), Vector2i(-1, 0), Vector2i(-1, 1), Vector2i(0, 1)]:
						if map.terrains.has(c + x + n) or changes.has(c + x + n):
							free = false
				if free:
					return c
	return Vector2i(Rules.MAP_LIMIT, 0)


## Debug: plains from this tile back toward the start until they meet land, so the party can walk there.
func _debug_road(from: Vector2i, changes: Dictionary) -> void:
	var t := from
	while not map.terrains.has(t) and not changes.has(t):
		changes[t] = "plains"
		order[t] = order.size()
		_debug_fill[t] = true
		var best: Vector2i = t + Hex.NEIGHBOURS[0]
		for n in Hex.NEIGHBOURS:
			if Rules.hex_distance(t + n, Rules.START_TILE) < Rules.hex_distance(best, Rules.START_TILE):
				best = t + n
		t = best


## A finished region's tiles change to its variant's look (DOCS: Exploration screen -> Cluster goals; no rim),
## and its landmark tile to the landmark's. Tier 2 regions without art keep their terrain's look for now.
## PLACEHOLDER transition: a wave spreading from the tile that finished it; each tile sinks flat into the
## ground (0.22 s), swaps to the variant's pieces, then springs back up with a small overshoot (0.45 s).
func _transform(tiles: Array[Vector2i], region: Dictionary, from: Vector2i) -> void:
	if region.variant == "":
		return
	_set_flow(region)
	var job := {}
	var grew := []
	if region.variant == "canyon" and not region.has("canyon_tiles"):
		region.canyon_tiles = tiles.duplicate()
		job = map.start_canyon(tiles, region.landmark_tile)
	elif region.has("canyon_tiles") and tiles.size() > region.canyon_tiles.size():
		var added := tiles.filter(func(c): return not c in region.canyon_tiles)
		job = map.start_canyon_growth(region.canyon_tiles, added, region.landmark_tile)
		grew = added
		region.canyon_tiles = tiles.duplicate()
	var todo := tiles.filter(func(c): return map.terrains[c] != region_look(region, c))
	if todo.is_empty():
		return
	if region.variant in Cliffs.RAISED:   # old tiles keep their trails and turn; only a new tile gets its own
		var dist := {}   # this region's only: a trail never runs into a region it touches
		var toward := {}
		for c in tiles:
			if map.flow_dist.has(c):
				dist[c] = map.flow_dist[c]
				if map.flow_toward.has(c):
					toward[c] = map.flow_toward[c]
		for _k in todo.size():
			for c in todo:
				if not dist.has(c):
					LandmarkFlow.extend(c, dist, toward)
		map.flow_dist.merge(dist, true)
		map.flow_toward.merge(toward, true)
	todo.sort_custom(func(a, b): return Rules.hex_distance(a, from) < Rules.hex_distance(b, from))
	busy = true
	var changes := {}
	for c in todo:
		changes[c] = region_look(region, c)
	var gorges := map.start_gorges(changes)
	const SINK := 0.22
	const STEP := 0.09
	for k in todo.size():
		var node := map.tile_node(todo[k])
		var tw := node.create_tween()
		tw.tween_interval(k * STEP)
		tw.tween_property(node, "scale:y", 0.04, SINK).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await get_tree().create_timer((todo.size() - 1) * STEP + SINK).timeout
	if not job.is_empty():   # the tiles wait flat if the rock isn't ready
		while not map.canyon_done(job):
			await get_tree().process_frame
		map.finish_canyon(job)
	while not map.gorges_done(gorges):
		await get_tree().process_frame
	map.retile(changes)
	if not grew.is_empty():
		map.canyon_dust(grew)
	if not job.is_empty() and map.canyons.has(party_tile):
		if grew.is_empty() or party_tile in grew:
			party_node.place_at(party_tile)   # down on the floor, while the tile's flat
		else:
			party_node.reseat()               # a lane it stood on may have gone
	for k in todo.size():
		var node := map.tile_node(todo[k])
		node.scale.y = 0.04
		var tw := node.create_tween()
		tw.tween_interval(k * STEP * 0.6)
		tw.tween_property(node, "scale:y", 1.0, 0.45).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	await get_tree().create_timer((todo.size() - 1) * STEP * 0.6 + 0.45).timeout
	if region.variant in Cliffs.RAISED:
		await _rise(region)
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
		if seen.has(t) or finished.has(t) or t == Rules.START_TILE or _debug_fill.has(t):
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
	return Hex.to3(Hex.tile_position(t.x, t.y), 1.2 + map.lift.get(t, 0.0))


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

func path_to(goal: Vector2i, dry := false) -> Array[Vector2i]:
	# Each tile is reached by a particular edge, because ridges can wall one way across a tile off from another.
	var start := Vector3i(party_tile.x, party_tile.y, -1)
	var came := {}
	var cost := {start: 0}
	var todo: Array[Vector3i] = [start]
	var end = null
	while not todo.is_empty():
		var best := 0
		for k in todo.size():
			if cost[todo[k]] < cost[todo[best]]:
				best = k
		var at: Vector3i = todo.pop_at(best)
		var c := Vector2i(at.x, at.y)
		if c == goal:
			end = at
			break
		for i in 6:
			var m: Vector2i = c + Hex.NEIGHBOURS[i]
			if not map.terrains.has(m) or not map.edge_open(c, m):   # fences only through a gate
				continue
			# A shared mountain stands on the edge, or ridges across the tile: the party goes round where it can.
			var step: int = Rules.MOUNTAIN_EDGE_COST if map._ranges(c, i) else 1
			if at.z >= 0 and map.ridge_wall(c, at.z, i):
				step += Rules.RIDGE_WALL_COST
			if at.z >= 0 and map.water_shapes.has(c) and map.wet_between(c, at.z, i):
				if dry:
					continue
				step += _cross_cost(c)
			if m == goal and map.water_shapes.has(m) and map.wet_between(m, (i + 3) % 6, -1):
				if dry:
					continue
				step += _cross_cost(m)
			var next := Vector3i(m.x, m.y, (i + 3) % 6)
			if cost[at] + step < cost.get(next, 1 << 30):
				cost[next] = cost[at] + step
				came[next] = at
				if not next in todo:
					todo.append(next)
	var path: Array[Vector2i] = []
	if end == null or end == start:
		return path
	var c: Vector3i = end
	while c != start:
		path.push_front(Vector2i(c.x, c.y))
		c = came[c]
	return path


## What crossing water tile t adds to a route: little on a raft, which can't run rapids; else a check to pass or pay for.
func _cross_cost(t: Vector2i) -> int:
	return 1 if party_node.has_raft and Water.raft_can_enter(map.terrains[t]) else Rules.CROSS_STEP_COST


## Whether this route steps into water with no way over but the check: no raft, or rapids, which a raft can't run.
func _needs_check(path: Array[Vector2i]) -> bool:
	var points := party_node.route_preview(path)
	var out := _bank_limit()
	var wet := party_node.wet_start(points)
	var free := out >= 0.0 and wet >= 0.0 and wet <= out
	var left := not free
	for p in points:
		left = left or not map.wet_at(p)
		if left and map.wet_at(p) and not (party_node.has_raft and Water.raft_can_enter(map.terrains.get(GroundCover.tile_at(p)))):
			return true
	return false


## For a party stopped in water: how far it can wade and still be going to the nearest bank, which takes no check
## (DOCS: design/02 -> Crossing water). -1 on land. Spreads over the water tile by tile to the first land it meets, and
## measures the party's own routes there.
func _bank_limit() -> float:
	var hero: Vector3 = party_node.members[0].node.position
	if not map.wet_at(Vector2(hero.x, -hero.z)):
		return -1.0
	var seen := {party_tile: true}
	var ring: Array[Vector2i] = [party_tile]
	while not ring.is_empty():
		var banks: Array[Vector2i] = []
		var next: Array[Vector2i] = []
		for t in ring:
			for n in Hex.NEIGHBOURS:
				var c: Vector2i = t + n
				if seen.has(c) or not map.terrains.has(c):
					continue
				seen[c] = true
				if Variants.is_water(map.terrains[c]):
					next.append(c)
				else:
					banks.append(c)
		var best := INF
		for c in banks:
			var path := path_to(c)
			if not path.is_empty():
				var wet := party_node.wet_start(party_node.route_preview(path))
				if wet >= 0.0:
					best = minf(best, wet)
		if best < INF:
			return best + Rules.BANK_MARGIN
		ring = next
	return -1.0


## The check pop-up's top half, for the hero's Athletics check (DOCS: design/02 -> Crossing water; 07 -> Social
## encounter screen). Coins: the base ability's plus the proficiency's (DOCS: 03 -> Proficiency rules).
func _cross_view() -> Dictionary:
	var hero := party[0]
	var n: int = hero.score + (1 if "Athletics" in Rules.PROFICIENCIES.get(hero.name, []) else 0)
	return {tag = "Athletics · STR", tag_bg = Color("#8A6420"), text = "Cross the water?", initial = hero.initial, face = hero.color,
			coins = n, line = "%s · %d coin%s · STR · needs %d heads" % [hero.name, n, "" if n == 1 else "s", Rules.CROSS_HEADS]}


## Who chimes in on a miss by exactly 1 (DOCS: 03 -> Companion chime-in): a proficient companion with the highest
## score, ties by party order. {} if none. PLACEHOLDER: the prototype's members have one score each.
func _chime_helper(proficiency: String) -> Dictionary:
	var best := {}
	for k in range(1, party.size()):
		var m := party[k]
		if proficiency in Rules.PROFICIENCIES.get(m.name, []) and (best.is_empty() or m.score > best.score):
			best = m
	return best


## The prompt when a route needs a check: cross, or walk round where there's a way (DOCS: design/02 -> Crossing water).
func _ask_crossing(goal: Vector2i, path: Array[Vector2i]) -> void:
	busy = true
	var way := _up_to_encounter(path_to(goal, true))
	var has_way := not way.is_empty() and not _needs_check(way)
	var stay := func():
		hud.check.visible = false
		if has_way:
			_walk(way)
		else:
			busy = false
			_refresh()
	var go := func():
		hud.check.visible = false
		_walk(path)
	hud.check.ask(_cross_view(), "Walk round" if has_way else "Back", stay, go)


## The Athletics check as the hero steps into water: the party holds at the edge while it flips on the pop-up. A fail
## still crosses, and the whole party loses some HP, with a splash.
func _cross_check() -> void:
	var view := _cross_view()
	view.text = "Cross the water"
	var flips: Array[bool] = Coins.flip(rng, view.coins)
	if debug_fail_crossing or debug_near_miss != 0:
		var heads_up: int = 0 if debug_fail_crossing else Rules.CROSS_HEADS - 1
		for k in flips.size():
			flips[k] = k < heads_up
	var heads := Coins.heads(flips)
	var helper := {}
	var helper_heads := false
	if heads == Rules.CROSS_HEADS - 1:
		var m := _chime_helper("Athletics")
		if not m.is_empty():
			var say: Array = Rules.CHIME_LINES[m.name]["Athletics"]
			helper = {initial = m.initial, face = m.color, name = m.name, note = say[0], line = say[1]}
			helper_heads = debug_near_miss > 0 or (debug_near_miss == 0 and rng.randf() < 0.5)
	var passed: bool = heads + (1 if helper_heads else 0) >= Rules.CROSS_HEADS
	if not debug_auto_cross:
		hud.check.play(view, flips, helper, helper_heads, passed)
		await hud.check.continued
	party_node.go_on()
	if passed:
		return
	for m in party:
		m.hp = maxi(mini(m.hp, 1), m.hp - Rules.CROSS_FAIL_HP)
	party_node.splash()
	_refresh()


## The walk stops on the first hex with an encounter.
func _up_to_encounter(path: Array[Vector2i]) -> Array[Vector2i]:
	for i in path.size():
		if encounters.has(path[i]):
			return path.slice(0, i + 1)
	return path


## Walks the party along placed hexes one step at a time; the camera follows; the minis face the way
## they walk (DOCS: Exploration screen -> Walking). Stops on a hex with an encounter.
func walk_to(goal: Vector2i) -> void:
	if busy or goal == party_tile:
		return
	var path := _up_to_encounter(path_to(goal))
	if path.is_empty():
		return
	if not debug_auto_cross and _needs_check(path):
		_ask_crossing(goal, path)
		return
	_walk(path)


func _walk(path: Array[Vector2i]) -> void:
	busy = true
	held = -1
	pick(null)
	rig.player_moved = false   # PLACEHOLDER (what "the next action" is isn't decided): a new walk follows again
	_refresh()
	# The day clock moves on as the hero steps onto each hex (PartyWalker: How the party moves).
	var on_step := func(t: Vector2i):
		party_tile = t
		_advance(Rules.STEP_MINUTES)
	party_node.free_out = _bank_limit()
	party_node.entered.connect(on_step)
	party_node.waded.connect(_cross_check)
	await party_node.walk(path)
	party_node.entered.disconnect(on_step)
	party_node.waded.disconnect(_cross_check)
	party_tile = path[-1]
	map.party_moved(party_tile)
	if encounters.has(party_tile):
		_encounter_tile = party_tile
		hud.show_encounter(Rules.NAMES[land(party_tile)], "ask", [])
		return
	if _open_port_shop():
		return
	busy = false
	_refresh()


## The River Port's shop counter, while it still has the raft (DOCS: design/02 -> Crossing water; 07 -> Town screen).
func _open_port_shop() -> bool:
	if map.terrains.get(party_tile) != "riverport" or party_node.has_raft or debug_auto_cross:
		return false
	busy = true
	hud.open_shop("River Port", func(): party_node.has_raft = true, func():
		busy = false
		_refresh())
	return true


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
	map.party_moved(party_tile)
	party_node.place_at(party_tile)
	party_node.visible = true
	hud.visible = true
	rig.frame(party_node.centre(), 58.0, 50.0)
	busy = false   # no defeat toast: the results screen already showed the dropped cards (DOCS: UI -> Screen text)
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
	deck.rest()
	_advance(Rules.REST_MINUTES)
	held = -1
	_refresh()   # no summary toast: the HP bars, the clock and the deck count show it (DOCS: UI -> Screen text)


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
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F9 and not busy:
		spawn_forest_regions()   # debug, PC only


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
		# A HUD control's details: what hover shows on PC (its tooltip text), first line (or part) as the title.
		var parts := Array(c.tooltip_text.split("\n" if "\n" in c.tooltip_text else ","))
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
		lines.append("Variant: %s" % g.name)
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
	# Three dots per step, along the route the party will walk.
	var route := party_node.route_preview(path)
	var dots := path.size() * 3
	var length := 0.0
	for k in range(1, route.size()):
		length += route[k].distance_to(route[k - 1])
	var d := 0.0
	var n := 1
	for k in range(1, route.size()):
		var seg := route[k].distance_to(route[k - 1])
		while n <= dots and d + seg >= length * n / dots:
			var mi := MeshInstance3D.new()
			mi.mesh = dot
			var at := route[k - 1].lerp(route[k], (length * n / dots - d) / maxf(seg, 1e-4))
			mi.position = Hex.to3(at, party_node.height_on_route(k) + 0.3)
			mi.scale = Vector3.ONE * (1.6 if n == dots else 1.0)
			add_child(mi)
			_path_marks.append(mi)
			n += 1
		d += seg


func ground_point(screen: Vector2) -> Vector2:
	var cam := rig.camera
	var o := cam.project_ray_origin(screen)
	var d := cam.project_ray_normal(screen)
	if absf(d.y) < 1e-4:
		return Vector2(INF, INF)
	# Raised ground stands in the way of what's behind it, so try its height first.
	if not map.raised.is_empty():
		var high := o + d * ((Variants.RAISE + 1.0 - o.y) / d.y)
		if map.raised.has(GroundCover.tile_at(Vector2(high.x, -high.z))):
			return Vector2(high.x, -high.z)
	var p := o + d * (-o.y / d.y)
	# Past the land's level over a canyon, the ray goes on down to its floor.
	if map.canyons.has(GroundCover.tile_at(Vector2(p.x, -p.z))):
		var low := o + d * ((Canyon.FLOOR - o.y) / d.y)
		if map.canyons.has(GroundCover.tile_at(Vector2(low.x, -low.z))):
			return Vector2(low.x, -low.z)
	return Vector2(p.x, -p.z)


func ground_tile(screen: Vector2) -> Vector2i:
	return GroundCover.tile_at(ground_point(screen))


func tap(t: Vector2i) -> void:
	if busy or hud.encounter_open():
		return
	if held >= 0:
		if map.terrains.has(t):
			toast("Already placed", false)
		elif map.slot_nodes.has(t):
			try_place(t)
	elif map.terrains.has(t):
		if t == party_tile:
			pick(null)
			_open_port_shop()
		elif picked == t:
			walk_to(t)
		else:
			pick(t)
			_refresh()
	else:
		pick(null)
		_refresh()
