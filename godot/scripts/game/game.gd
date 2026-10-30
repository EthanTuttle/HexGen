class_name Game
extends Node3D
## The playable loop: place map cards from the hand, walk the party, fight encounters on the tile's
## combat board, and come back to the map with the hand refilled.
## Rules: design/02 Map & exploration.md, 03 Classes & combat.md, 05 Cards & progression.md; the
## numbers and every placeholder are in rules.gd.
##
## Map controls: click a card to hold it, click a lit slot to place it (Esc or the card again lets go);
## click a placed tile to walk there. Camera as in the look tests (drag, wheel, right-drag, Q/E, F).

const COMBAT_AT := Vector2(1000, 0)   # the combat board lives away from the map
const TAP_PIXELS := 8.0               # PLACEHOLDER from the docs' mockups: a press that barely moves ...
const TAP_MS := 350                   # ... and lets go quickly is a tap, not a drag

var rng := RandomNumberGenerator.new()
var deck: Deck
var map := MapBoard.new()
var rig := CameraRig.new()
var clock: TimeOfDay
var party_node: Node3D
var party_tile := Rules.START_TILE
var party: Array[Dictionary] = []     # per member: name, mini, ability, score, hp, max_hp, cards
var held := -1                        # index into the hand, or -1
var busy := false                     # walking, in a pop-up or in a fight
var encounters := {}                  # tile -> {expires: float, persistent: bool, dropped: Array, badge: Node3D}
var finished := {}                    # tile -> region id, for tiles in finished regions
var regions_done := {}                # terrain -> how many regions of it are finished
var goal_badges := {}                 # tile -> Label3D cluster goal badge
var fight: Fight
var real_time := 0.0
var fights_won := 0

# UI
var ui := CanvasLayer.new()
var hand_box := HBoxContainer.new()
var party_label := Label.new()
var clock_label := Label.new()
var prompt := Label.new()
var counts := Label.new()
var rest_button := Button.new()
var popup := PanelContainer.new()
var popup_text := Label.new()
var popup_buttons := HBoxContainer.new()

var _press_pos := Vector2.ZERO
var _press_ms := 0
var _slot_lit: StandardMaterial3D
var _slot_banned_marks: Array[Node3D] = []
var _message_until := 0.0


func _ready() -> void:
	var seed_arg := "1"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--seed="):
			seed_arg = a.split("=")[1]
	rng.seed = hash(seed_arg)
	clock = Stage.create(self)
	clock.day_seconds = Rules.DAY_SECONDS
	clock.hour = 9.0                  # PLACEHOLDER: the campaign starts in the morning
	clock.running = true

	add_child(map)
	map.place(Rules.START_TILE, Rules.START_TERRAIN)
	_label3d(Hex.tile_position(0, 0), 1.6, "Estate (start · camp)", Color(0.25, 0.2, 0.15), 48)

	for m in Rules.PARTY:
		var member: Dictionary = m.duplicate(true)
		member.max_hp = m.hp
		party.append(member)
	party_node = Minis.party(Hex.tile_position(party_tile.x, party_tile.y))
	add_child(party_node)

	deck = Deck.new(Rules.STARTING_DECK, rng)
	deck.draw(Rules.STARTING_HAND)

	fight = Fight.new()
	fight.name = "fight"
	fight.position = Hex.to3(COMBAT_AT)
	fight.visible = false
	add_child(fight)

	add_child(rig)
	rig.min_distance = 8.0
	rig.max_distance = 110.0
	rig.frame(party_node.position, 52.0, 50.0)
	_slot_lit = StandardMaterial3D.new()
	_slot_lit.albedo_color = Color.html("#FFF3B8")     # PLACEHOLDER UI colour for a slot the held card can take
	_build_ui()
	_refresh()
	if "--demo" in OS.get_cmdline_user_args():
		var demo := Demo.new()
		demo.game = self
		add_child(demo)


# --- UI ----------------------------------------------------------------------

func _build_ui() -> void:
	add_child(ui)
	var theme := Theme.new()
	theme.default_font_size = 17
	theme.set_color("font_color", "Label", Color(0.2, 0.17, 0.13))
	var root := Control.new()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = theme
	ui.add_child(root)
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	var left := _panel(root, Vector2(16, 16))
	var lv := VBoxContainer.new()
	left.add_child(lv)
	party_label.add_theme_font_size_override("font_size", 16)
	lv.add_child(party_label)
	rest_button.text = "Rest at camp"
	rest_button.pressed.connect(rest)
	lv.add_child(rest_button)

	var top := _panel(root, Vector2.ZERO)
	top.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP, Control.PRESET_MODE_MINSIZE, 16)
	top.grow_horizontal = Control.GROW_DIRECTION_BOTH
	var tv := VBoxContainer.new()
	top.add_child(tv)
	clock_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tv.add_child(clock_label)
	prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	prompt.add_theme_color_override("font_color", Color(0.45, 0.25, 0.1))
	tv.add_child(prompt)

	var bottom := _panel(root, Vector2.ZERO)
	bottom.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM, Control.PRESET_MODE_MINSIZE, 16)
	bottom.grow_horizontal = Control.GROW_DIRECTION_BOTH
	bottom.grow_vertical = Control.GROW_DIRECTION_BEGIN
	var bv := VBoxContainer.new()
	bottom.add_child(bv)
	counts.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	bv.add_child(counts)
	hand_box.add_theme_constant_override("separation", 8)
	bv.add_child(hand_box)

	popup.set_anchors_preset(Control.PRESET_CENTER)
	popup.grow_horizontal = Control.GROW_DIRECTION_BOTH
	popup.grow_vertical = Control.GROW_DIRECTION_BOTH
	popup.add_theme_stylebox_override("panel", _box(Color(0.98, 0.95, 0.88, 0.97), 18))
	var pv := VBoxContainer.new()
	pv.add_theme_constant_override("separation", 12)
	popup.add_child(pv)
	popup_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	popup_text.add_theme_color_override("font_color", Color(0.2, 0.17, 0.13))
	pv.add_child(popup_text)
	popup_buttons.alignment = BoxContainer.ALIGNMENT_CENTER
	popup_buttons.add_theme_constant_override("separation", 12)
	pv.add_child(popup_buttons)
	popup.visible = false
	root.add_child(popup)
	popup.set_anchors_and_offsets_preset(Control.PRESET_CENTER, Control.PRESET_MODE_MINSIZE)


func _panel(root: Control, at: Vector2) -> PanelContainer:
	var p := PanelContainer.new()
	p.position = at
	p.add_theme_stylebox_override("panel", _box(Color(0.98, 0.95, 0.88, 0.9), 10))
	root.add_child(p)
	return p


static func _box(c: Color, pad: int) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = c
	sb.set_corner_radius_all(8)
	sb.set_content_margin_all(pad)
	return sb


func _refresh() -> void:
	var lines := PackedStringArray()
	for m in party:
		lines.append("%s   HP %d/%d" % [m.name, m.hp, m.max_hp])
	party_label.text = "\n".join(lines)
	rest_button.disabled = busy or party_tile != Rules.START_TILE
	for c in hand_box.get_children():
		hand_box.remove_child(c)
		c.queue_free()
	for i in deck.hand.size():
		var terrain := deck.hand[i]
		var b := Button.new()
		b.text = Rules.NAMES[terrain]
		b.custom_minimum_size = Vector2(108, 56)
		var col := Hex.colour(terrain if terrain != "river" else "water")
		b.add_theme_stylebox_override("normal", _box(col, 6))
		b.add_theme_stylebox_override("hover", _box(col.lightened(0.15), 6))
		var held_box := _box(col.lightened(0.1), 6)
		held_box.border_color = Color(0.85, 0.35, 0.1)
		held_box.set_border_width_all(4)
		b.add_theme_stylebox_override("pressed", held_box)
		if i == held:
			b.add_theme_stylebox_override("normal", held_box)
			b.add_theme_stylebox_override("hover", held_box)
		b.add_theme_color_override("font_color", Color(0.15, 0.13, 0.1))
		b.add_theme_color_override("font_hover_color", Color(0.15, 0.13, 0.1))
		b.add_theme_color_override("font_pressed_color", Color(0.15, 0.13, 0.1))
		b.pressed.connect(hold.bind(i))
		b.disabled = busy
		hand_box.add_child(b)
	var over := " · over the limit, discard down at the next rest" if deck.hand.size() > Rules.HAND_LIMIT else ""
	counts.text = "Hand %d/%d%s   ·   Deck %d   ·   Discard %d" % [deck.hand.size(), Rules.HAND_LIMIT, over, deck.draw_pile.size(), deck.discard.size()]
	if real_time > _message_until:
		if held >= 0:
			prompt.text = "Holding %s: click a lit slot to place it (Esc lets go)" % Rules.NAMES[deck.hand[held]]
		elif deck.hand.is_empty():
			prompt.text = "Hand empty: go exploring (click a tile to walk) to win more cards"
		else:
			prompt.text = "Pick a card to place, or click a tile to walk there"
	_light_slots()


func message(text: String, seconds := 4.0) -> void:
	prompt.text = text
	_message_until = real_time + seconds


func _process(delta: float) -> void:
	real_time += delta
	clock.running = not fight.active
	var night := Rules.is_night(clock.hour)
	var to_switch := fposmod((Rules.NIGHT_FROM if not night else Rules.NIGHT_TO) - clock.hour, 24.0)
	var real_min := to_switch / 24.0 * Rules.DAY_SECONDS / 60.0
	clock_label.text = "Day %d · %s · %s in %d min" % [_day + 1, clock.label(), "Dawn" if night else "Nightfall", ceili(real_min)]
	if night != _was_night:
		_was_night = night
		_light_slots()
	if clock.hour < _last_hour:
		_day += 1
	_last_hour = clock.hour
	# Spawned encounters disappear after about 15 minutes unless a wipe made them stay (DOCS).
	for t in encounters.keys():
		var e: Dictionary = encounters[t]
		if not e.persistent and real_time > e.expires and t != party_tile:
			_remove_encounter(t)
	if real_time > _message_until and _message_until > 0.0:
		_message_until = 0.0
		_refresh()

var _day := 0
var _last_hour := 0.0
var _was_night := false


# --- Placing -----------------------------------------------------------------

func hold(i: int) -> void:
	if busy:
		return
	held = -1 if held == i else i
	_refresh()


## Why a held card can't go on slot t, or "" if it can (DOCS: Placement).
func why_not(t: Vector2i, terrain: String) -> String:
	if map.terrains.has(t):
		return "That hex is already placed"
	if not map.slot_nodes.has(t):
		return "A card must go next to placed land"
	if absi(t.x) > Rules.MAP_LIMIT or absi(t.y) > Rules.MAP_LIMIT:
		return "Edge of the prototype map"
	for n in Hex.NEIGHBOURS:
		var other = map.terrains.get(t + n)
		if other != null and Rules.banned(terrain, other):
			return "%s can't go next to %s" % [Rules.NAMES[terrain], Rules.NAMES.get(other, other)]
	if Rules.is_night(clock.hour) and Rules.hex_distance(t, party_tile) > Rules.SIGHT_RANGE:
		return "At night you can only build within the party's sight (%d hexes)" % Rules.SIGHT_RANGE
	return ""


func _light_slots() -> void:
	for m in _slot_banned_marks:
		m.queue_free()
	_slot_banned_marks.clear()
	for t: Vector2i in map.slot_nodes:
		var mi: MeshInstance3D = map.slot_nodes[t]
		mi.material_override = null
		if held < 0:
			continue
		var why := why_not(t, deck.hand[held])
		if why == "":
			mi.material_override = _slot_lit
		elif why.contains("can't go next to"):
			_slot_banned_marks.append(_label3d(Hex.tile_position(t.x, t.y), 0.4, "×", Color(0.8, 0.15, 0.1), 160))


func try_place(t: Vector2i) -> bool:
	if held < 0 or busy:
		return false
	var terrain := deck.hand[held]
	var why := why_not(t, terrain)
	if why != "":
		message(why)
		return false
	deck.hand.remove_at(held)      # DOCS: placing never draws a new card
	held = -1
	map.place(t, terrain)
	clock.hour = fmod(clock.hour + Rules.PLACE_MINUTES / 60.0, 24.0)
	_check_region(t, terrain)
	_maybe_spawn(t)
	_refresh()
	return true


## Connected tiles of one terrain, counting only placed terrain cards (not the start hex).
func cluster(t: Vector2i) -> Array[Vector2i]:
	var terrain = map.terrains.get(t)
	var seen := {t: true}
	var todo: Array[Vector2i] = [t]
	var out: Array[Vector2i] = []
	while not todo.is_empty():
		var c: Vector2i = todo.pop_back()
		out.append(c)
		for n in Hex.NEIGHBOURS:
			var m: Vector2i = c + n
			if not seen.has(m) and m != Rules.START_TILE and map.terrains.get(m) == terrain:
				seen[m] = true
				todo.append(m)
	return out


## Cluster goals and finished regions (DOCS: Clustered regions; draws: Core loop and hand refill).
func _check_region(t: Vector2i, terrain: String) -> void:
	var tiles := cluster(t)
	for c in tiles:
		if goal_badges.has(c):
			goal_badges[c].queue_free()
			goal_badges.erase(c)
	var joined := -1
	for c in tiles:
		if finished.has(c):
			joined = maxi(joined, finished[c])
	if joined >= 0:
		# A tile added to a finished region just expands it (the newer region if it touches two).
		for c in tiles:
			if not finished.has(c):
				finished[c] = joined
		return
	var tier := 1 if regions_done.get(terrain, 0) == 0 else 2
	var goal := Rules.REGION_TIER1 if tier == 1 else Rules.REGION_TIER2
	if tiles.size() >= goal:
		var id := finished.size() + 1000 * regions_done.size()
		for c in tiles:
			finished[c] = id
		regions_done[terrain] = regions_done.get(terrain, 0) + 1
		var got := deck.draw(Rules.DRAW_EASY_FIGHT if tier == 1 else Rules.DRAW_TIER2_REGION)
		# PLACEHOLDER: no landmark (no art yet); the region gets a name label instead.
		var centre := Vector2.ZERO
		for c in tiles:
			centre += Hex.tile_position(c.x, c.y)
		_label3d(centre / tiles.size(), 3.0, "%s region · tier %d" % [Rules.NAMES[terrain], tier], Color(0.2, 0.16, 0.1), 64)
		message("%s region finished (tier %d): drew %d card%s%s" % [Rules.NAMES[terrain], tier, got.size(),
				"" if got.size() == 1 else "s", "" if got.size() > 0 else " (deck empty)"], 6.0)
	elif tiles.size() >= Rules.GOAL_SHOWS_AT:
		goal_badges[t] = _label3d(Hex.tile_position(t.x, t.y), 2.2, "%d+  (%d to go)" % [goal, goal - tiles.size()], Color(0.15, 0.15, 0.2), 72)


func _label3d(at: Vector2, height: float, text: String, col: Color, size := 64) -> Label3D:
	var l := Label3D.new()
	l.text = text
	l.font_size = size
	l.pixel_size = 0.012
	l.outline_size = 14
	l.outline_modulate = Color(1, 0.98, 0.92)
	l.modulate = col
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = true
	l.position = Hex.to3(at, height)
	add_child(l)
	return l


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
	_add_encounter(free[rng.randi_range(0, free.size() - 1)], false)


func _add_encounter(t: Vector2i, persistent: bool, dropped: Array = []) -> void:
	if encounters.has(t):
		encounters[t].persistent = encounters[t].persistent or persistent
		encounters[t].dropped.append_array(dropped)
		return
	var badge := _label3d(Hex.tile_position(t.x, t.y), 2.4, "⚔ Fight", Color(0.75, 0.12, 0.08), 72)
	badge.text = "Fight!"
	encounters[t] = {expires = real_time + Rules.ENCOUNTER_LIFETIME, persistent = persistent, dropped = dropped, badge = badge}


func _remove_encounter(t: Vector2i) -> void:
	encounters[t].badge.queue_free()
	encounters.erase(t)


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


## Walks the party along placed hexes one step at a time; the camera follows (DOCS: Walking).
## Stops on a hex with an encounter.
func walk_to(goal: Vector2i) -> void:
	if busy or goal == party_tile:
		return
	var path := path_to(goal)
	if path.is_empty():
		return
	busy = true
	held = -1
	_refresh()
	for step in path:
		var to := Hex.to3(Hex.tile_position(step.x, step.y) + Minis.PARTY_OFFSET)
		var d := to - party_node.position
		var tw := create_tween().set_parallel()
		tw.tween_property(party_node, "rotation:y", party_node.rotation.y + wrapf(atan2(d.x, d.z) - party_node.rotation.y, -PI, PI), 0.15)
		tw.tween_property(party_node, "position", to, Rules.STEP_SECONDS).set_trans(Tween.TRANS_SINE)
		tw.tween_property(rig, "target", to, Rules.STEP_SECONDS)
		# A small bob per step, so the minis read as walking pieces (PLACEHOLDER: how minis move is open in the docs).
		for mini in party_node.get_children():
			var body: Node3D = mini.get_node("body")
			var bob := create_tween()
			bob.tween_property(body, "position:y", 0.12, Rules.STEP_SECONDS * 0.5).set_trans(Tween.TRANS_SINE)
			bob.tween_property(body, "position:y", 0.0, Rules.STEP_SECONDS * 0.5).set_trans(Tween.TRANS_SINE)
		await tw.finished
		party_tile = step
		clock.hour = fmod(clock.hour + Rules.WALK_MINUTES.get(map.terrains[step], Rules.WALK_MINUTES_DEFAULT) / 60.0, 24.0)
		if encounters.has(step):
			_encounter_popup(step)
			return
	busy = false
	_refresh()


func _encounter_popup(t: Vector2i) -> void:
	var dropped: Array = encounters[t].dropped
	var extra := "\n(%d dropped card%s wait here)" % [dropped.size(), "" if dropped.size() == 1 else "s"] if not dropped.is_empty() else ""
	show_popup("Cultists block the way on this %s hex.%s" % [Rules.NAMES[map.terrains[t]].to_lower(), extra],
			[["Fight", start_fight.bind(t)], ["Sneak past (Stealth)", sneak_past.bind(t)]])


func show_popup(text: String, buttons: Array) -> void:
	popup_text.text = text
	for c in popup_buttons.get_children():
		popup_buttons.remove_child(c)
		c.queue_free()
	for b in buttons:
		var button := Button.new()
		button.text = b[0]
		button.custom_minimum_size = Vector2(150, 42)
		button.pressed.connect(func():
			popup.visible = false
			b[1].call())
		popup_buttons.add_child(button)
	popup.visible = true


## Stealth group check: everyone flips their DEX coins (DOCS: group check for sneaking past).
## On a pass the encounter stays on the map (DOCS). PLACEHOLDER: pass if half the party gets 1+ heads;
## a fail starts the fight.
func sneak_past(t: Vector2i) -> void:
	var passed := 0
	var lines := PackedStringArray()
	for m in party:
		var coins := Coins.flip(rng, m.score if m.ability == "DEX" else 1)
		if Coins.heads(coins) >= 1:
			passed += 1
		lines.append("%s %s" % [m.name, Coins.text(coins)])
	var ok := passed >= ceili(party.size() * Rules.SNEAK_PASS_SHARE)
	show_popup("Stealth (DEX, needs 1 heads each, half the party):\n%s\n%s" % ["\n".join(lines),
			"Passed: you slip by. The cultists stay." if ok else "Spotted! They attack."],
			[["Carry on", func(): _after_sneak()]] if ok else [["Fight", start_fight.bind(t)]])


func _after_sneak() -> void:
	busy = false
	_refresh()


# --- Fights ------------------------------------------------------------------

func start_fight(t: Vector2i) -> void:
	busy = true
	map.visible = false
	party_node.visible = false
	for e in encounters.values():
		e.badge.visible = false
	for l in get_children():
		if l is Label3D:
			l.visible = false
	ui.visible = false
	fight.visible = true
	var distance := Rules.hex_distance(t, Rules.START_TILE)
	var foes := mini(Rules.ENEMIES_BASE + distance / Rules.ENEMIES_PER_DISTANCE, Rules.ENEMIES_MAX)
	rig.frame(fight.position + Vector3(0, 0, 0.3), 21.0, 55.0)
	var won: bool = await fight.run(self, map.terrains[t], t, foes)
	fight.visible = false
	map.visible = true
	party_node.visible = true
	for l in get_children():
		if l is Label3D:
			l.visible = true
	ui.visible = true
	rig.frame(party_node.position, 52.0, 50.0)
	if won:
		fights_won += 1
		var dropped: Array = encounters[t].dropped
		_remove_encounter(t)
		for m in party:
			m.hp = maxi(m.hp, Rules.REVIVE_HP)
		var got := deck.draw(Rules.DRAW_EASY_FIGHT)
		for card in dropped:
			deck.hand.append(card)
		show_popup("Victory! Drew %d card%s%s%s." % [got.size(), "" if got.size() == 1 else "s",
				" (the deck ran out)" if got.size() < Rules.DRAW_EASY_FIGHT else "",
				", and picked up %d dropped" % dropped.size() if not dropped.is_empty() else ""],
				[["Back to the map", _after_sneak]])
	else:
		# DOCS: on a wipe the party retreats to its most recent camp and the hand is dropped; the
		# encounter stays until cleared, and clearing it recollects the cards.
		var dropped := deck.hand.duplicate()
		deck.hand.clear()
		_add_encounter(t, true, dropped)
		party_tile = Rules.START_TILE
		party_node.position = Hex.to3(Hex.tile_position(party_tile.x, party_tile.y) + Minis.PARTY_OFFSET)
		rig.frame(party_node.position, 52.0, 50.0)
		for m in party:
			m.hp = Rules.REVIVE_HP
		show_popup("The party was beaten and fell back to camp.\n%d card%s dropped where they fell; win that fight to get them back." % [
				dropped.size(), "" if dropped.size() == 1 else "s"], [["Back to the map", _after_sneak]])
	_refresh()


# --- Rest --------------------------------------------------------------------

## Resting at camp (DOCS: Camps and rest): heal, +8 hours, discard down to 7, reshuffle the discard
## pile into the deck. Draws nothing.
func rest() -> void:
	if busy or party_tile != Rules.START_TILE:
		return
	for m in party:
		m.hp = m.max_hp
	var dropped := deck.rest()
	clock.hour = fmod(clock.hour + Rules.REST_HOURS, 24.0)
	held = -1
	message("Rested: HP restored, 8 hours passed%s." % [", discarded %d down to %d" % [dropped, Rules.HAND_LIMIT] if dropped else ""])
	_refresh()


# --- Input -------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if fight.active:
		return
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_ESCAPE:
		held = -1
		_refresh()
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_press_pos = event.position
			_press_ms = Time.get_ticks_msec()
		elif event.position.distance_to(_press_pos) < TAP_PIXELS and Time.get_ticks_msec() - _press_ms < TAP_MS:
			tap(ground_tile(event.position))


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
	if busy:
		return
	if held >= 0:
		if map.terrains.has(t):
			message("That hex is already placed")
		else:
			try_place(t)
	elif map.terrains.has(t):
		walk_to(t)
