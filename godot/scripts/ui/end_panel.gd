class_name EndPanel
extends Control
## The prototype's end (design/06 -> First playable): after the goal's regions, what the run came to. Keep exploring, or a new campaign.

var game: Game


static func attach(g: Game) -> EndPanel:
	var p := EndPanel.new()
	p.game = g
	p.name = "end_panel"
	p.visible = false
	p.set_anchors_preset(Control.PRESET_FULL_RECT)
	g.safe.add_child(p)
	return p


func open() -> void:
	for c in get_children():
		remove_child(c)
		c.queue_free()
	var dim := Scrim.make(Color(0.141, 0.188, 0.172, 0.45))
	dim.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(dim)
	var box := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(24, 18, 24, 18))
	box.custom_minimum_size = Vector2(320, 200)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	box.add_child(v)
	v.add_child(UI.label("%d regions" % game.regions.size(), "lilita", 30, Color("#2E6B3A")))
	for row: Array in game.run_summary():
		var h := HBoxContainer.new()
		var name_ := UI.label(row[0], "n800", 14, UI.INK_SOFT)
		name_.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		h.add_child(name_)
		h.add_child(UI.label(str(row[1]), "lilita", 18))
		v.add_child(h)
	var again := TagButton.make("New campaign", 0, 40)
	again.pressed.connect(func(): game.restart_run())
	v.add_child(again)
	var on := TagButton.make("Keep exploring", 0, 40)
	on.pressed.connect(func():
		visible = false
		game.busy = false)
	v.add_child(on)
	add_child(Scrim.centre(box))
	visible = true
	move_to_front()
