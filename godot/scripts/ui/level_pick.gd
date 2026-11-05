class_name LevelPick
extends Control
## A level's terrain pick (design/06: simple, the full Level-up screen comes later): three terrain cards, one goes into the hand.

var game: Game


static func attach(g: Game) -> LevelPick:
	var p := LevelPick.new()
	p.game = g
	p.name = "level_pick"
	p.visible = false
	p.set_anchors_preset(Control.PRESET_FULL_RECT)
	g.safe.add_child(p)
	return p


func open(level: int, options: Array) -> void:
	for c in get_children():
		remove_child(c)
		c.queue_free()
	var dim := ColorRect.new()
	dim.color = Color(0.141, 0.188, 0.172, 0.45)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var box := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(24, 16, 24, 16))
	UI.at(box, 262, 110)
	box.custom_minimum_size = Vector2(320, 150)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	box.add_child(v)
	v.add_child(UI.label("Level %d" % level, "lilita", 26, Color("#2E6B3A")))
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 14)
	v.add_child(row)
	for t: String in options:
		var hx := HexShape.make(66, 76, UI.CREAM_LIGHT, UI.terrain_bg(t), 4).with_icon("t_" + t, UI.terrain_ink(t), 32)
		hx.clickable = true
		hx.accessibility_name = Rules.NAMES[t]
		hx.pressed.connect(func(): game.level_picked(t))
		row.add_child(hx)
	add_child(box)
	visible = true
	move_to_front()
