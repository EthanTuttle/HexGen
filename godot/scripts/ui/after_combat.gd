class_name AfterCombat
extends Control
## The step back to the map after a fight, built from After combat v7 (mockups/final-screens/AfterCombat.dc.html):
## "Victory!", the party's HP, the rewards revealed one by one in the middle and settling into place, the
## XP bar, then the button. The loop's rewards are the cards the win draws (and any dropped cards won
## back); gold, loot and XP aren't in the loop, so gold and XP show the mockup's placeholders.
## A wipe uses the same panel as "Defeat" (there's no defeat mockup).

signal done

var _main: PanelContainer
var _rewards: Control
var _reveal: Array[Control] = []


func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP


func show_result(game: Game, won: bool, downed: Dictionary, drawn: Array[String], dropped: Array) -> void:
	for c in get_children():
		remove_child(c)
		c.queue_free()
	_reveal.clear()
	var dim := ColorRect.new()
	dim.color = Color(0.141, 0.188, 0.172, 0.28)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(dim)

	_main = UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(18, 14, 18, 14))
	UI.at(_main, 90, 14)
	_main.custom_minimum_size = Vector2(664, 362)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	_main.add_child(v)

	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 12)
	head.alignment = BoxContainer.ALIGNMENT_BEGIN
	var title := UI.label("Victory!" if won else "Defeat", "lilita", 30, Color("#2E6B3A") if won else UI.RED)
	head.add_child(title)
	var sub := UI.label("[Enemy group] defeated" if won else "The party fell back to camp", "n800", 13, UI.INK_SOFT)
	sub.size_flags_vertical = Control.SIZE_SHRINK_END
	head.add_child(sub)
	v.add_child(head)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 14)
	row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(row)
	row.add_child(_party_panel(game, downed))
	row.add_child(_rewards_panel(won, drawn, dropped))

	var bottom := HBoxContainer.new()
	bottom.add_theme_constant_override("separation", 10)
	bottom.alignment = BoxContainer.ALIGNMENT_END
	if won:
		var xp := VBoxContainer.new()
		xp.add_theme_constant_override("separation", 5)
		xp.custom_minimum_size.x = 330
		var xr := HBoxContainer.new()
		xr.add_child(UI.label("+[XP] XP", "lilita", 18))
		var sp := Control.new()
		sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		xr.add_child(sp)
		var lv := UI.label("Party level [level]", "n800", 11, UI.INK_SOFT)
		lv.size_flags_vertical = Control.SIZE_SHRINK_END
		xr.add_child(lv)
		xp.add_child(xr)
		xp.add_child(Bar.make(330, 14, Color("#E6DCC8"), UI.GOLD, 0.62, UI.HEX_SHADOW))
		bottom.add_child(xp)
	var sp2 := Control.new()
	sp2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bottom.add_child(sp2)
	var b := TagButton.make("Back to map" if won else "Back to camp", 170, 44, 16)
	b.pressed.connect(func(): done.emit())
	bottom.add_child(b)
	v.add_child(bottom)
	add_child(_main)
	visible = true
	_play_reveal.call_deferred()


func _party_panel(game: Game, downed: Dictionary) -> Control:
	var p := UI.panel(UI.TRAY, 14, UI.TRAY_EDGE, 4, Vector4(12, 10, 12, 10))
	p.custom_minimum_size.x = 250
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	v.alignment = BoxContainer.ALIGNMENT_BEGIN
	v.add_child(UI.label("PARTY", "n900", 10, UI.WHITE_WARM, 1))
	for m in game.party:
		var was_down: bool = downed.get(m.name, false)
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 10)
		var hex := HexShape.make(40, 46, UI.RIM, Color(m.color)).with_text(m.initial, 17).with_shadow(Color("#7E5F44"), 2)
		hex.modulate.a = 0.6 if was_down else 1.0
		h.add_child(hex)
		var col := VBoxContainer.new()
		col.add_theme_constant_override("separation", 3)
		col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		col.alignment = BoxContainer.ALIGNMENT_CENTER
		var line := HBoxContainer.new()
		line.add_child(UI.label(m.name, "n900", 13, UI.WHITE_WARM))
		var sp := Control.new()
		sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		line.add_child(sp)
		var frac: float = float(m.hp) / m.max_hp
		line.add_child(UI.label("Was downed" if was_down else "%d%%" % roundi(frac * 100), "n900", 13, Color("#FFD7C2") if was_down else UI.WHITE_WARM))
		col.add_child(line)
		var bar := Bar.make(160, 8, Color("#6F5A41"), Color("#C4542A") if was_down else UI.GREEN, frac)
		bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		col.add_child(bar)
		h.add_child(col)
		v.add_child(h)
	p.add_child(v)
	return p


func _rewards_panel(won: bool, drawn: Array[String], dropped: Array) -> Control:
	var p := Panel.new()
	var sb := UI.box(UI.CREAM_LIGHT, 14)
	sb.border_color = Color("#E2D5BC")
	sb.set_border_width_all(2)
	p.add_theme_stylebox_override("panel", sb)
	p.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	p.clip_contents = true
	_rewards = p
	p.add_child(UI.at(UI.label("Rewards" if won else "Dropped cards", "lilita", 16), 14, 8))
	var cards: Array = drawn.duplicate()
	if won:
		cards.append_array(dropped)
	else:
		cards = dropped.duplicate()
	var x := 80.0
	for i in cards.size():
		var t: String = cards[i]
		var hx := HexShape.make(60, 69, UI.CREAM_LIGHT, UI.terrain_bg(t), 4).with_icon("t_" + t, UI.terrain_ink(t), 28).with_shadow(UI.HEX_SHADOW)
		hx.position = Vector2(x + (i % 4) * 72, 48 + (i / 4) * 80)
		hx.tooltip_text = Rules.NAMES[t] + (" (won back)" if won and i >= drawn.size() else "")
		if not won:
			hx.modulate.a = 0.55
		p.add_child(hx)
		_reveal.append(hx)
	if won:
		if cards.is_empty():
			p.add_child(UI.at(UI.label("The deck is empty: no cards drawn. Rest to reshuffle.", "n800", 12, UI.INK_SOFT), 14, 60))
		var gold := UI.panel(UI.DARK, 26, Color(0, 0, 0, 0), 0, Vector4(8, 0, 16, 0))
		gold.custom_minimum_size.y = 52
		var gh := HBoxContainer.new()
		gh.add_theme_constant_override("separation", 8)
		var dot := _GoldDot.new()
		dot.custom_minimum_size = Vector2(36, 36)
		var cc := CenterContainer.new()
		cc.add_child(dot)
		gh.add_child(cc)
		var gl := UI.label("+[gold]", "lilita", 20, UI.CREAM)
		gl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		gl.size_flags_vertical = Control.SIZE_FILL
		gh.add_child(gl)
		gold.add_child(gh)
		UI.at(gold, 10, 137 + (80 if cards.size() > 4 else 0))
		p.add_child(gold)
		_reveal.append(gold)
	else:
		var note := UI.label("Win this fight to get them back.", "n800", 12, UI.INK_SOFT)
		p.add_child(UI.at(note, 14, 130))
	return p


## Each reward pops up big in the middle of the panel, then settles into its place (After combat v7).
func _play_reveal() -> void:
	await get_tree().process_frame
	var centre := Vector2(182, 116)
	var t := 0.5
	for c in _reveal:
		var home := c.position
		c.pivot_offset = c.size * 0.5
		c.position = centre - c.size * 0.5
		c.scale = Vector2(0.3, 0.3)
		var a := c.modulate.a
		c.modulate.a = 0.0
		var tw := create_tween()
		tw.tween_interval(t)
		tw.tween_property(c, "modulate:a", a, 0.2)
		tw.parallel().tween_property(c, "scale", Vector2(1.9, 1.9), 0.2)
		tw.tween_interval(0.3)
		tw.tween_property(c, "position", home, 0.4).set_trans(Tween.TRANS_SINE)
		tw.parallel().tween_property(c, "scale", Vector2.ONE, 0.4).set_trans(Tween.TRANS_SINE)
		t += 0.55


class _GoldDot extends Control:
	func _draw() -> void:
		draw_circle(Vector2(18, 18), 18, UI.GOLD_EDGE)
		draw_circle(Vector2(18, 16.5), 16.5, UI.GOLD)
