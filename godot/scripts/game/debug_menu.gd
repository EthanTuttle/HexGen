class_name DebugMenu
extends PanelContainer
## A test aid for the phone: three fingers on the screen (F8 on a Mac) open it, in debug builds only. It jumps to what's being tried: Feywild, hills and lava fights, encounters. No part of
## the game: its text isn't under the Screen text rules, and it never ships.

var game: Game
var _list: VBoxContainer
var _spawned := false


static func attach(g: Game) -> void:
	if not OS.is_debug_build():
		return
	var m := DebugMenu.new()
	m.game = g
	m.visible = false
	g.safe.add_child(m)


func _ready() -> void:
	set_anchors_preset(Control.PRESET_CENTER)
	custom_minimum_size = Vector2(320, 340)
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(300, 330)
	add_child(scroll)
	_list = VBoxContainer.new()
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_list)
	var close := func(): visible = false
	for row: Array in [
			["Close", close],
			["Spawn all regions (a long pause)", _spawn],
			["Feywild: go to the Fey Gate", _go_to.bind("feywild_crossing", true)],
			["Feywild: go in the forest", _go_to.bind("feywild_crossing", false)],
			["Volcanic tile: go there", _go_to.bind("volcanic_peaks", true)],
			["Lava fight: Fissures", _fight.bind("volcanic_peaks_fissures")],
			["Lava fight: Crater", _fight.bind("volcanic_peaks_crater")],
			["Hills fight: Shelf (lifts)", _fight.bind("snowy_peaks_shelf")],
			["Hills fight: Climb", _fight.bind("monastery_heights_climb")],
			["Big fight: Plains Stones", _fight.bind("plains_stones")],
			["Big fight: Farmland Paddocks", _fight.bind("farmland_paddocks")],
			["Encounters round the party", _encounters],
			["Day", _time.bind(false)],
			["Night", _time.bind(true)],
			["End this fight (a win)", _end_fight]]:
		var b := Button.new()
		b.text = row[0]
		b.custom_minimum_size = Vector2(0, 44)
		b.pressed.connect(row[1])
		_list.add_child(b)


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F8:
		visible = not visible
		move_to_front()
	elif event is InputEventScreenTouch and event.pressed and event.index == 2:
		visible = not visible
		move_to_front()


func _spawn() -> void:
	visible = false
	_ensure()


func _ensure() -> void:
	if not _spawned:
		_spawned = true
		game.spawn_forest_regions()


func _go_to(variant: String, landmark: bool) -> void:
	visible = false
	_ensure()
	await get_tree().create_timer(0.3).timeout
	for g: Dictionary in game.regions:
		if g.variant == variant:
			var t: Vector2i = g.landmark_tile if landmark else g.tiles.filter(func(x): return x != g.landmark_tile)[0]
			game.party_tile = t
			game.party_node.place_at(t)
			game.map.party_moved(t)
			game.rig.player_moved = false
			game.rig.frame(game.party_node.centre(), 30.0, 50.0)
			return


func _fight(id: String) -> void:
	visible = false
	game.debug_fight(id)


func _end_fight() -> void:
	visible = false
	if game.fight.active:
		game.fight.finished.emit(true)


func _time(night: bool) -> void:
	visible = false
	if night:
		game.minute = Rules.NIGHT_AT + 1.0
	else:
		game.minute = Rules.START_MINUTE


## One of each kind near and far, so sight shows by walking and by the clock.
func _encounters() -> void:
	visible = false
	var rows := Rules.ENCOUNTER_TABLE.size()
	var k := 0
	for t: Vector2i in game.map.terrains:
		var away := Rules.hex_distance(t, game.party_tile)
		if away >= 1 and away <= 6 and game.map.can_visit(t) and not game.encounters.has(t) and not Variants.LANDMARKS.has(game.map.terrains[t]) and GroundCover.hash01(t.x, t.y, 90) < 0.3:
			game.add_encounter(t, false, [], Rules.ENCOUNTER_TABLE[k % rows])
			k += 1
			if k >= 8:
				break
