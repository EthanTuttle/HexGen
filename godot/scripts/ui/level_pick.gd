class_name LevelPick
extends Control
## A level's picks (design/06: simple, the full Level-up screen comes later). At levels 4, 8, 12 and 16 each member places
## 1 ability point first, one at a time, hero first (03 -> Ability scores; 07 -> Level-up: "one character at a time", v8d's
## six coin tiles in 2 rows of 3, the new coin ringed green, Next off until it's placed, Back to an earlier member). No score goes above 6: a tile at
## 6 is dimmed. Then three terrain cards, one goes into the hand.

const ABILITIES := ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
const CAP := 6

var game: Game
var _level := 0
var _options := []
var _members := []       # who places a point this level (the party), or none
var step := 0            # the member placing now; == _members.size() for the terrain cards
var placed := {}         # member index -> the ability its point went on


static func attach(g: Game) -> LevelPick:
	var p := LevelPick.new()
	p.game = g
	p.name = "level_pick"
	p.visible = false
	p.set_anchors_preset(Control.PRESET_FULL_RECT)
	g.safe.add_child(p)
	return p


func open(level: int, options: Array, members := []) -> void:
	_level = level
	_options = options
	_members = members
	step = 0
	placed = {}
	_build()


## The test bots' pick: each member's point on its main score (the weapon's), or its highest score under the cap, then
## the first terrain card.
func bot_pick() -> void:
	for i in _members.size():
		var m: Dictionary = _members[i]
		var open := ABILITIES.filter(func(k): return Races.score(m, k) < CAP)
		if open.is_empty():
			continue
		open.sort_custom(func(a, b): return Races.score(m, a) > Races.score(m, b))
		placed[i] = String(m.ability) if String(m.ability) in open else open[0]
	game.level_picked(_options[0], placed)


## Places this member's point (or moves it).
func place(ability: String) -> void:
	if Races.score(_members[step], ability) >= CAP:
		return
	placed[step] = ability
	_build()


## On to the next member, or the terrain cards.
func next() -> void:
	if placed.has(step) or _full(_members[step]):
		step += 1
		_build()


## Back to the previous member, whose point stays placed until moved.
func back() -> void:
	if step > 0:
		step -= 1
		_build()


func _full(m: Dictionary) -> bool:
	return ABILITIES.all(func(k): return Races.score(m, k) >= CAP)


func _build() -> void:
	for c in get_children():
		remove_child(c)
		c.queue_free()
	var dim := Scrim.make(Color(0.141, 0.188, 0.172, 0.45))
	dim.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(dim)
	var box := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(24, 16, 24, 16))
	box.custom_minimum_size = Vector2(320, 150)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	box.add_child(v)
	v.add_child(UI.label("Level %d" % _level, "lilita", 26, Color("#2E6B3A")))
	if step < _members.size():
		var m: Dictionary = _members[step]
		var head := HBoxContainer.new()
		head.add_theme_constant_override("separation", 12)
		head.add_child(UI.label(String(m.name), "lilita", 20))
		head.add_child(_section("Place 1 ability point", placed.has(step)))
		v.add_child(head)
		var grid := GridContainer.new()
		grid.columns = 3
		grid.add_theme_constant_override("h_separation", 8)
		grid.add_theme_constant_override("v_separation", 8)
		for k: String in ABILITIES:
			grid.add_child(_tile(m, k))
		v.add_child(grid)
		var nav := _nav()
		var go := CUI.big("Next", true)
		var on := placed.has(step) or _full(m)
		go.modulate.a = 1.0 if on else 0.4
		go.mouse_filter = Control.MOUSE_FILTER_STOP if on else Control.MOUSE_FILTER_IGNORE
		go.pressed.connect(next)
		nav.add_child(go)
		v.add_child(nav)
	else:
		var row := HBoxContainer.new()
		row.alignment = BoxContainer.ALIGNMENT_CENTER
		row.add_theme_constant_override("separation", 14)
		v.add_child(row)
		for t: String in _options:
			var hx := HexShape.make(66, 76, UI.CREAM_LIGHT, UI.terrain_bg(t), 4).with_icon("t_" + t, UI.terrain_ink(t), 32)
			hx.clickable = true
			hx.accessibility_name = Rules.NAMES[t]
			hx.pressed.connect(func(): game.level_picked(t, placed))
			row.add_child(hx)
		if not _members.is_empty():
			v.add_child(_nav())
	add_child(Scrim.centre(box))
	visible = true
	move_to_front()


## The row under a step: Back from the second step on, then a spring for Next.
func _nav() -> HBoxContainer:
	var nav := HBoxContainer.new()
	if step > 0:
		var b := CUI.big("Back", false)
		b.pressed.connect(back)
		nav.add_child(b)
	var spring := Control.new()
	spring.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nav.add_child(spring)
	return nav


## A section title with its dot: orange until done, then a green tick (07 -> Level-up, no to-do line).
func _section(title: String, done: bool) -> Control:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 7)
	h.add_child(UI.label(title, "lilita", 16))
	var mark := CUI.mark(done)
	mark.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(mark)
	return h


## One ability's tile: its name, score and a coin per point; the placed point's coin is ringed green. Dimmed at the cap.
func _tile(m: Dictionary, k: String) -> Control:
	var mine: bool = placed.get(step, "") == k
	var n: int = Races.score(m, k) + (1 if mine else 0)
	var capped := Races.score(m, k) >= CAP
	var b := Button.new()
	b.accessibility_name = k
	b.custom_minimum_size = Vector2(120, 58)
	b.add_theme_stylebox_override("normal", UI.box(UI.CREAM_LIGHT, 12, UI.GREEN if mine else UI.CREAM_EDGE, 3 if mine else 2))
	for s in ["hover", "pressed", "focus", "disabled"]:
		b.add_theme_stylebox_override(s, b.get_theme_stylebox("normal"))
	b.disabled = capped
	b.modulate.a = 0.45 if capped else 1.0
	b.pressed.connect(place.bind(k))
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 6)
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 8)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var names := VBoxContainer.new()
	names.add_theme_constant_override("separation", 0)
	names.mouse_filter = Control.MOUSE_FILTER_IGNORE
	names.add_child(UI.label(k, "n900", 11, UI.INK, 1))
	names.add_child(UI.label(str(n), "lilita", 24, UI.INK, 0, 1.0))
	h.add_child(names)
	var coins := HBoxContainer.new()
	coins.add_theme_constant_override("separation", -6)   # past what fits they overlap slightly (07 -> coins stay on one line)
	coins.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	coins.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for i in n:
		var c := CoinView.blank(18)
		if mine and i == n - 1:
			c.ring = UI.GREEN
		coins.add_child(c)
	h.add_child(coins)
	b.add_child(h)
	return b
