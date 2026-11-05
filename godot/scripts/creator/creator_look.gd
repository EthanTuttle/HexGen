class_name CreatorLook
extends Control
## The Look step (Creator v21a): the mini large in the middle with the starting place's tile faint behind it, body options
## on the left and colours on the right. The mini is the real one (HeroView), rebuilt on each pick.

const D = preload("res://scripts/creator/creator_data.gd")
const VIEWS: Array[String] = ["Front", "Right side", "Back", "Left side"]

var c: Creator
var turn := 0
var _risen := false
var _mini: HeroView


func _init(creator: Creator) -> void:
	c = creator
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func refresh() -> void:
	for ch in get_children():
		if ch != _mini:
			remove_child(ch)
			ch.queue_free()
	var side := 238.0 if size.x >= 760.0 else 228.0
	var left := _left()
	left.position = Vector2.ZERO
	left.size = Vector2(side, size.y)
	add_child(left)
	var right := _right()
	right.position = Vector2(size.x - side, 0)
	right.size = Vector2(side, size.y)
	add_child(right)
	_middle(side + 12.0, size.x - side * 2.0 - 24.0)
	_risen = true


func _left() -> Control:
	var p := CUI.panel(Vector4(14, 12, 14, 12))
	var v := CUI.vbox(7)
	v.add_child(_group("Build", false, _pills(["Slim", "Average", "Broad"], c.build, func(o):
		c.build = o
		c.render())))
	v.add_child(_group("Pronouns", true, _pills(["He", "She", "They"], c.pronouns, func(o):
		c.pronouns = o
		c.render())))
	v.add_child(_group("Head", false, _numbers(4, c.head, "Head", func(i):
		c.head = i
		c.render())))
	var r := c.race_data()
	if r.hair:
		v.add_child(_group("Hairstyle", false, _numbers(6, c.hair, "Hairstyle", func(i):
			c.hair = i
			c.render())))
	v.add_child(CUI.spring())
	var row := CUI.hbox(0)
	var back := CUI.big("Back", false)
	back.pressed.connect(c.go_back)
	row.add_child(back)
	v.add_child(row)
	p.add_child(v)
	return p


func _group(title: String, dot: bool, body: Control) -> Control:
	var v := CUI.vbox(4)
	var head := CUI.hbox(5)
	head.add_child(CUI.cap(title))
	if dot:
		var d := CUI.Dot.make(8, Color("#3E8E4E") if c.pronouns != "" else Color("#E07A2E"), "", 0)
		head.add_child(d)
	v.add_child(head)
	v.add_child(body)
	return v


func _pills(options: Array, cur: String, act: Callable) -> Control:
	var h := CUI.hbox(4)
	for o: String in options:
		var b := CUI.pill(o, cur == o)
		b.pressed.connect(act.bind(o))
		h.add_child(b)
	return h


func _numbers(n: int, cur: int, what: String, act: Callable) -> Control:
	var h := CUI.hbox(4)
	for i in n:
		var sel := cur == i
		var hx := CUI.hex(30, 35, CUI.SEL_RIM if sel else UI.RIM, 4 if sel else 3, "", UI.INK, 0).with_text(str(i + 1), 13, Color("#7E3519") if sel else Color("#33403B")).with_shadow(UI.HEX_SHADOW, 3)
		hx.clickable = true
		hx.accessibility_name = "%s %d" % [what, i + 1]
		hx.pressed.connect(act.bind(i))
		h.add_child(hx)
	return h


func _right() -> Control:
	var p := CUI.panel(Vector4(14, 12, 14, 12))
	var v := CUI.vbox(5)
	v.add_child(UI.label("Colours", "lilita", 16))
	for part: Dictionary in c.colour_parts():
		var g := CUI.vbox(3)
		g.add_child(CUI.cap(part.n))
		var row := CUI.hbox(6)
		var cur := c.colour_of(part.k)
		for i in part.pal.size():
			row.add_child(_swatch(part, i, cur))
		g.add_child(row)
		v.add_child(g)
	v.add_child(CUI.spring())
	var nav := CUI.hbox(0)
	nav.add_child(CUI.spring())
	nav.add_child(c.next_button())
	v.add_child(nav)
	p.add_child(v)
	return p


func _swatch(part: Dictionary, i: int, cur: String) -> Control:
	var hexcol: String = part.pal[i]
	var t := Swatch.new()
	t.col = Color(hexcol)
	t.on = hexcol == cur
	t.accessibility_name = "%s %d" % [part.n, i + 1]
	t.custom_minimum_size = Vector2(26, 26)
	t.pressed.connect(func():
		c.col[part.k] = hexcol
		c.render())
	return t


func _middle(x: float, w: float) -> void:
	var b := c.bg_data()
	var cx := x + w * 0.5
	var tile := HexShape.make(250, 289, CUI.shade(Color(D.TER[b.t][1]), 0.85), Color(0, 0, 0, 0), 0)
	tile.modulate.a = 0.38
	UI.at(tile, cx - 125.0, 4)
	add_child(tile)
	if _mini == null:
		_mini = HeroView.new(240, 256)
		add_child(_mini)
	UI.at(_mini, cx - 120.0, size.y - 44 - 256)
	move_child(_mini, tile.get_index() + 1)
	_mini.show_hero(HeroMini.description(c.hero()))
	if not _risen:   # CSS minirise: up from small with a glow
		_mini.pivot_offset = Vector2(120, 220)
		_mini.scale = Vector2(0.6, 0.6)
		_mini.modulate.a = 0.0
		var tw := _mini.create_tween().set_parallel()
		tw.tween_property(_mini, "scale", Vector2.ONE, 0.9).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		tw.tween_property(_mini, "modulate:a", 1.0, 0.5)
	var row := CUI.hbox(8)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(_turn_button("Turn left", "M4 12a8 8 0 1 0 2.5-5.8 M4 4v4h4", -1))
	var words := CUI.vbox(0)
	words.custom_minimum_size.x = 110
	words.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var view := UI.label(VIEWS[posmod(turn, 4)], "n900", 11, Color("#33403B"), 0, 1.2)
	view.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	words.add_child(view)
	var place := UI.label(b.hex, "n700", 11, CUI.SOFT_INK, 0, 1.2)
	place.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	words.add_child(place)
	row.add_child(words)
	row.add_child(_turn_button("Turn right", "M20 12a8 8 0 1 1-2.5-5.8 M20 4v4h-4", 1))
	row.position = Vector2(x, size.y - 44)
	row.size = Vector2(w, 44)
	add_child(row)


func _turn_button(what: String, icon: String, by: int) -> Control:
	var t := Swatch.new()
	t.accessibility_name = what
	t.col = UI.CREAM_LIGHT
	t.ring = false
	t.icon = UI.icon(icon, Color("#33403B"), 16, 2.6)
	t.custom_minimum_size = Vector2(44, 44)
	t.pressed.connect(func():
		turn += by
		_mini.turn_to(turn)
		c.render())
	return t


## A round swatch, or a round button with an icon.
class Swatch extends Control:
	signal pressed
	var col := Color.WHITE
	var on := false
	var ring := true
	var icon: Texture2D

	func _init() -> void:
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		mouse_filter = Control.MOUSE_FILTER_STOP

	func _gui_input(event: InputEvent) -> void:
		if UI.is_tap(self, event):
			pressed.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)

	func _draw() -> void:
		var m := size * 0.5
		if ring:
			draw_circle(m + Vector2(0, 2), 13, UI.CREAM_EDGE)
			if on:
				draw_circle(m, 15, UI.INK)
				draw_circle(m, 13.5, UI.CREAM)
			draw_circle(m, 13, UI.CREAM_LIGHT)
			draw_circle(m, 11, col)
		else:
			draw_circle(m + Vector2(0, 3), 16, UI.HEX_SHADOW)
			draw_circle(m, 16, col)
			draw_texture_rect(icon, Rect2(m - Vector2(8, 8), Vector2(16, 16)), false)
