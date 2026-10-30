class_name CombatHud
extends Control
## The combat screen's HUD, built from Combat v14 (mockups/combat/Combat-v14-AllyTargets.dc.html) in its
## 844 x 390 layout: the party tray with phase, End and AP pips; camera buttons; the details panel with
## the card, target, coins and the action button; the hotbar and All actions; the End confirmation;
## HP bars standing over the minis.

var fight: Fight

var _phase_label: Label
var _portraits := VBoxContainer.new()
var _hotbar := HBoxContainer.new()
var _details := VBoxContainer.new()
var _button_box := VBoxContainer.new()
var _all: PanelContainer
var _all_grid := GridContainer.new()
var _all_title: Label
var _confirm: ColorRect
var _confirm_rows := VBoxContainer.new()
var _enemy_pill: PanelContainer
var _bars := Control.new()
var _bar_nodes := {}


func _init(f: Fight) -> void:
	fight = f
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	_bars.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bars.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_bars)
	_build_tray()
	_build_cam()
	_build_details()
	_build_hotbar()
	_build_all()
	_build_confirm()
	_build_enemy_pill()


# --- Party tray (left 12, top 12) -----------------------------------------------

func _build_tray() -> void:
	var p := UI.panel(UI.TRAY, 18, UI.TRAY_EDGE, 4, Vector4(6, 8, 6, 8))
	p.custom_minimum_size.x = 72       # CSS width 60 + padding (content-box)
	UI.at(p, 12, 12)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	_phase_label = UI.label("Allies", "lilita", 12)
	_phase_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(_phase_label)
	var end := _EndHex.new()
	end.custom_minimum_size = Vector2(38, 47)
	end.pressed.connect(fight.end_phase)
	end.tooltip_text = "End allies' phase"
	var cc := CenterContainer.new()
	cc.add_child(end)
	v.add_child(cc)
	var gap := Control.new()
	gap.custom_minimum_size.y = 0
	v.add_child(gap)
	_portraits.add_theme_constant_override("separation", 4)
	v.add_child(_portraits)
	p.add_child(v)
	add_child(p)


func _refresh_tray() -> void:
	for c in _portraits.get_children():
		_portraits.remove_child(c)
		c.queue_free()
	for u in fight.allies():
		var on: bool = u == fight.current
		var v := VBoxContainer.new()
		v.add_theme_constant_override("separation", 3)
		var h := HexShape.make(38, 44, UI.ORANGE if on else UI.RIM, Color(u.color), 4 if on else 3).with_text(u.initial, 16).with_shadow(UI.HEX_SHADOW)
		h.clickable = true
		h.tooltip_text = "%s, %d AP left%s" % [u.name, fight.ap_left(u), ", acting now" if on else ""]
		h.pressed.connect(fight.select.bind(u))
		if u.down:
			h.modulate.a = 0.5
		var cc := CenterContainer.new()
		cc.add_child(h)
		v.add_child(cc)
		v.add_child(Bar.make(40, 5, Color("#E6DCC8"), UI.GREEN, float(maxi(u.hp, 0)) / u.max_hp, UI.HEX_SHADOW))
		var pips := HBoxContainer.new()
		pips.add_theme_constant_override("separation", 2)
		pips.alignment = BoxContainer.ALIGNMENT_CENTER
		# Bonus AP display (DOCS, combat v4d): always 3 pips; a blue lightning pip is worth 2, shown first.
		var t: int = u.ap + u.bonus
		var bolts := mini(3, maxi(0, t - 3))
		var golds := mini(3, t) - bolts
		for i in 3:
			var col := Color("#3F8FC4") if i < bolts else (UI.GOLD if i < bolts + golds else Color("#6F5A41"))
			var pip := HexShape.make(10, 11.5, col, col, 0)
			if i < bolts:
				pip.with_icon("bolt_fill", Color.WHITE, 8, 2, true)
			pips.add_child(pip)
		v.add_child(pips)
		_portraits.add_child(v)


class _EndHex extends Control:
	signal pressed

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, Vector2(38, 44))
		draw_colored_polygon(UI.hex_points(Rect2(Vector2(0, 3), r.size)), UI.ORANGE_EDGE)
		draw_colored_polygon(UI.hex_points(r), UI.ORANGE)
		draw_texture_rect(UI.icon("chevron", UI.WHITE_WARM, 12, 3), Rect2(Vector2(13, 9), Vector2(12, 12)), false)
		var f := UI.font("lilita")
		var w := f.get_string_size("End", HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
		draw_string(f, Vector2(19 - w * 0.5, 32), "End", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.WHITE_WARM)

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)


# --- Camera buttons (left 96, top 14) --------------------------------------------

func _build_cam() -> void:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	UI.at(v, 96, 14)
	for b in [["zoom_in", "Zoom in"], ["zoom_out", "Zoom out"], ["rot_l", "Rotate left"], ["rot_r", "Rotate right"], ["center", "Center on the acting character"]]:
		var h := HexShape.make(40, 46, UI.RIM, UI.CREAM_LIGHT).with_icon(b[0], Color("#33403B"), 18, 2.4).with_shadow(UI.HEX_SHADOW)
		h.clickable = true
		h.tooltip_text = b[1]
		h.pressed.connect(_cam.bind(b[0]))
		v.add_child(h)
	add_child(v)


func _cam(which: String) -> void:
	var rig := fight.game.rig
	if which == "center":
		rig.player_moved = false   # the centre button gives the camera back to the game
	else:
		rig._player()
	match which:
		"zoom_in":
			rig._zoom(0.75)
		"zoom_out":
			rig._zoom(1.33)
		"rot_l":
			rig.ease_to(rig.target, rig.distance, roundf(rig.yaw_deg / 60.0) * 60.0 + 60.0)
		"rot_r":
			rig.ease_to(rig.target, rig.distance, roundf(rig.yaw_deg / 60.0) * 60.0 - 60.0)
		"center":
			if not fight.current.is_empty():
				rig.ease_to(fight.global_position + fight.current.mini.position, rig.distance, rig.yaw_deg)


# --- Details panel (left 656, top 12, 170 x 366) ------------------------------------

func _build_details() -> void:
	var p := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(12, 12, 12, 12))
	p.custom_minimum_size = Vector2(170, 366)
	p.size = Vector2(170, 366)
	p.clip_contents = true
	UI.at(p, 656, 12)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	_details.add_theme_constant_override("separation", 6)
	_details.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(_details)
	_button_box.add_theme_constant_override("separation", 4)
	v.add_child(_button_box)
	p.add_child(v)
	add_child(p)


func _wrap(l: Label) -> Label:
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = 146
	return l


func _refresh_details() -> void:
	for c in _details.get_children() + _button_box.get_children():
		c.get_parent().remove_child(c)
		c.queue_free()
	if fight.phase == "enemies":
		_details.add_child(_wrap(UI.label("Enemies' phase", "lilita", 20)))
		_details.add_child(_wrap(UI.label("The foes act on the board.", "n700", 12, UI.INK_SOFT)))
		return
	if fight.phase == "over" or fight.current.is_empty():
		return
	var u := fight.current
	var k := fight.card()
	var src: Dictionary = Cards.SRC[k.src]
	var lim: String = {"turn": " · once per turn", "fight": " · once per fight"}.get(k.limit, "")
	var head_text := ("%s · %s%s" % [src.label, "AP not set" if k.ap < 0 else "%d AP" % k.ap, lim]).to_upper()
	if k.limit == "":
		var head := HBoxContainer.new()
		head.add_theme_constant_override("separation", 4)
		head.add_child(UI.label(head_text, "n900", 11, Color(src.ink), 1))
		head.add_child(UI.icon_rect("repeat", Color(src.ink), 12, 2.8))
		_details.add_child(head)
	else:
		_details.add_child(_wrap(UI.label(head_text, "n900", 11, Color(src.ink), 1)))
	var name := _wrap(UI.label(k.n, "lilita", 20))
	_details.add_child(name)
	_details.add_child(_wrap(UI.label(k.desc, "n700", 12, UI.INK_SOFT)))
	if k.limit == "fight":
		_details.add_child(_wrap(UI.label("Once per fight: stays used until the next fight.", "n800", 12, Color("#9A4A12"))))
	var div := ColorRect.new()
	div.color = Color(UI.HEX_SHADOW, 0.5)
	div.custom_minimum_size = Vector2(146, 2)
	_details.add_child(div)

	var targeting: bool = k.kind in ["attack", "save", "ally"]
	var has_target: bool = not (fight.ally_target if k.kind == "ally" else fight.target).is_empty()
	if k.kind == "move":
		var line := "No AP left to move." if fight.ap_left(u) < 1 else ("Moved %d %s. Tap a lit hex to move again." % [fight.moved, "hex" if fight.moved == 1 else "hexes"] if fight.moved > 0 else "Tap a lit hex to move there.")
		_details.add_child(_wrap(UI.label(line, "n800", 13)))
		_details.add_child(_wrap(UI.label("Each Move costs 1 AP and can be repeated. Rocks and other tokens block; trees don't. Distance shown: 2 hexes [placeholder, not set yet].", "n700", 12, UI.INK_SOFT)))
	elif targeting and not fight.result.is_empty():
		var coins := HBoxContainer.new()
		coins.add_theme_constant_override("separation", 6)
		for h in fight.result.coins:
			coins.add_child(CoinView.make(h, 34))
		if not fight.result.coins.is_empty():
			_details.add_child(coins)
		_details.add_child(_wrap(UI.label(fight.result.title, "lilita", 22, Color("#2E7A3E") if fight.result.good else UI.RED)))
		_details.add_child(_wrap(UI.label(fight.result.sub, "n700", 12, UI.INK_SOFT)))
	elif targeting and has_target:
		var t: Dictionary = fight.ally_target if k.kind == "ally" else fight.target
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		row.add_child(UI.label(t.name, "lilita", 16))
		var bar := Bar.make(40, 6, UI.DARK, UI.GREEN if t.ally else Color("#C4542A"), float(maxi(t.hp, 0)) / t.max_hp)
		bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		row.add_child(bar)
		_details.add_child(row)
		if k.kind == "ally":
			_details.add_child(_wrap(UI.label("No roll", "n800", 13)))
			_details.add_child(_wrap(UI.label("Spells that help an ally always work.", "n700", 12, UI.INK_SOFT)))
		elif k.kind == "attack":
			var n: int = u.score + (1 if u.blessed else 0)
			_details.add_child(_wrap(UI.label("Flip %d coins (%s)%s" % [n, u.ability, " +1 Bless" if u.blessed else ""], "n800", 13)))
			_details.add_child(_wrap(UI.label("Needs 1 heads to hit.", "n700", 12, UI.INK_SOFT)))
		else:
			_details.add_child(_wrap(UI.label("%s flips %d coins (%s save)" % [t.name, Rules.ENEMY_SAVE_COINS, k.save], "n800", 13)))
			_details.add_child(_wrap(UI.label("Needs 1 heads to save. A save halves the damage.", "n700", 12, UI.INK_SOFT)))
	elif targeting:
		_details.add_child(_wrap(UI.label("Pick an ally. Allies in reach have a green circle." if k.kind == "ally" else "Pick a target. Foes in reach glow gold.", "n800", 13)))
	elif k.kind == "self" and fight.self_done == k.id:
		_details.add_child(UI.label("Used", "lilita", 18, Color("#2E7A3E")))
		_details.add_child(_wrap(UI.label(fight.self_message(k.id), "n700", 12, UI.INK_SOFT)))

	# The button (and the note under it when the card can't be used)
	var label := ""
	if targeting and (has_target or not fight.result.is_empty()):
		if k.kind == "ally":
			label = "Cast again" if not fight.result.is_empty() else "Cast"
		elif k.kind == "save":
			label = "Cast"
		else:
			label = "Flip again" if not fight.result.is_empty() else "Flip coins"
	elif k.kind == "self":
		label = "Use"
	if label != "":
		var note := fight.cant_use(u, k)
		if (k.kind in ["attack", "save"] and fight.target.is_empty()) or (k.kind == "ally" and fight.ally_target.is_empty()):
			note = note if note != "" else "Pick a target again"
		var b := TagButton.make(label, 146, 44, 15, true)
		b.disabled = note != "" or fight.busy
		b.pressed.connect(fight.press_button)
		_button_box.add_child(b)
		if note != "":
			var nl := _wrap(UI.label(note, "n800", 11, UI.INK_MUTED))
			nl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			_button_box.add_child(nl)


# --- Hotbar (left 100, top 286) ----------------------------------------------------

func _build_hotbar() -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	UI.at(row, 100, 286)
	row.custom_minimum_size = Vector2(546, 92)
	_hotbar.add_theme_constant_override("separation", 6)
	_hotbar.alignment = BoxContainer.ALIGNMENT_END
	row.add_child(_hotbar)
	var all := UI.FingerButton.new()
	all.text = "All actions"
	all.icon = UI.icon("grid", UI.CREAM, 22, 2)
	all.expand_icon = false
	all.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
	all.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
	all.custom_minimum_size = Vector2(56, 84)
	all.add_theme_constant_override("icon_max_width", 22)
	all.size_flags_vertical = Control.SIZE_SHRINK_END
	all.add_theme_font_override("font", UI.font("n900"))
	all.add_theme_font_size_override("font_size", 11)
	all.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	all.add_theme_constant_override("h_separation", 4)
	for s in ["normal", "hover", "pressed", "focus"]:
		all.add_theme_stylebox_override(s, UI.box(UI.DARK, 10, UI.DARK_EDGE, 4, Vector4(4, 14, 4, 10)))
	for s in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		all.add_theme_color_override(s, UI.CREAM)
	all.pressed.connect(func(): _all.visible = true; _refresh_all())
	row.add_child(all)
	add_child(row)


func _card_button(id: String, big: bool) -> Control:
	var u := fight.current
	var k := Cards.get_card(id, u.weapon)
	var src: Dictionary = Cards.SRC[k.src]
	var on: bool = id == fight.sel
	var dim := fight.spent(u, k)
	if big:
		var c := _HotCard.new()
		c.setup(k, src, on, dim)
		c.pressed.connect(fight.pick_card.bind(id))
		c.tooltip_text = "%s, %s card, %s" % [k.n, src.label, "AP cost not set" if k.ap < 0 else "%d AP" % k.ap]
		return c
	var b := _AllCard.new()
	b.setup(k, src, on, dim, " · on hotbar" if id in u.hot else "")
	b.pressed.connect(func():
		_all.visible = false
		fight.pick_card(id))
	return b


func _refresh_hotbar() -> void:
	for c in _hotbar.get_children():
		_hotbar.remove_child(c)
		c.queue_free()
	if fight.current.is_empty():
		return
	for id in fight.current.hot:
		_hotbar.add_child(_card_button(id, true))


## A hotbar card (74 x 84): colour band, AP hex, repeat icon or once-per-fight tag, icon and name.
class _HotCard extends Control:
	signal pressed
	var k: Dictionary
	var src: Dictionary
	var on := false
	var dim := false

	func setup(card: Dictionary, s: Dictionary, selected: bool, spent: bool) -> void:
		k = card
		src = s
		on = selected
		dim = spent
		custom_minimum_size = Vector2(74, 92)
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		modulate.a = 0.45 if dim else 1.0

	func _draw() -> void:
		var y := 0.0 if on else 8.0           # the picked card lifts 8 px
		var r := Rect2(Vector2(0, y), Vector2(74, 84))
		draw_style_box(UI.box(UI.HEX_SHADOW, 10), Rect2(r.position + Vector2(0, 4), r.size))
		var face := UI.box(UI.CREAM_LIGHT, 10)
		face.border_color = UI.ORANGE if on else Color(src.band)
		face.set_border_width_all(3 if on else 2)
		draw_style_box(face, r)
		draw_rect(Rect2(r.position + Vector2(2.5, 2.5), Vector2(69, 6)), Color(src.band))
		draw_colored_polygon(UI.hex_points(Rect2(r.position + Vector2(4, 9), Vector2(20, 23))), UI.DARK)
		var f := UI.font("n900")
		var ap := Cards.ap_text(k)
		draw_string(f, r.position + Vector2(14 - f.get_string_size(ap, 0, -1, 11).x * 0.5, 25), ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
		if k.limit == "":
			draw_texture_rect(UI.icon("repeat", Color("#2E6B3A"), 16, 2.6), Rect2(r.position + Vector2(54, 10), Vector2(16, 16)), false)
		elif k.limit == "fight":
			draw_style_box(UI.box(Color("#9A4A12"), 8), Rect2(r.position + Vector2(44, 9), Vector2(27, 16)))
			draw_string(f, r.position + Vector2(49, 21), "1", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, UI.WHITE_WARM)
			draw_texture_rect(UI.icon("fight_once", UI.WHITE_WARM, 10, 2.6), Rect2(r.position + Vector2(57, 12), Vector2(10, 10)), false)
		draw_texture_rect(UI.icon(k.icon, Color(src.icon_ink), 26, 2), Rect2(r.position + Vector2(24, 20), Vector2(26, 26)), false)
		var lines := String(k.n).split(" ")
		var text_y := 60.0 if lines.size() == 1 or f.get_string_size(k.n, 0, -1, 11).x < 64 else 56.0
		var parts: Array = [k.n] if f.get_string_size(k.n, 0, -1, 11).x < 64 else lines
		for i in parts.size():
			var w := f.get_string_size(parts[i], 0, -1, 11).x
			draw_string(f, r.position + Vector2(37 - w * 0.5, text_y + i * 12), parts[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)


## A card in the All actions list (48 tall): AP hex, icon, name and source.
class _AllCard extends Control:
	signal pressed
	var k: Dictionary
	var src: Dictionary
	var on := false
	var note := ""

	func setup(card: Dictionary, s: Dictionary, selected: bool, spent: bool, hot_note: String) -> void:
		k = card
		src = s
		on = selected
		note = hot_note
		custom_minimum_size = Vector2(160, 48)
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		modulate.a = 0.45 if spent else 1.0

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size)
		var face := UI.box(UI.CREAM_LIGHT, 10)
		face.border_color = UI.ORANGE if on else Color(src.band)
		face.set_border_width_all(2)
		draw_style_box(face, r)
		draw_colored_polygon(UI.hex_points(Rect2(Vector2(8, 12.5), Vector2(20, 23))), UI.DARK)
		var f := UI.font("n900")
		var ap := Cards.ap_text(k)
		draw_string(f, Vector2(18 - f.get_string_size(ap, 0, -1, 11).x * 0.5, 28), ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
		draw_texture_rect(UI.icon(k.icon, Color(src.icon_ink), 20, 2), Rect2(Vector2(36, 14), Vector2(20, 20)), false)
		draw_string(f, Vector2(64, 22), k.n, HORIZONTAL_ALIGNMENT_LEFT, size.x - 70, 12, UI.INK)
		draw_string(UI.font("n700"), Vector2(64, 37), src.label + note, HORIZONTAL_ALIGNMENT_LEFT, size.x - 70, 11, UI.INK_SOFT)

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)


# --- All actions (left 90, top 12, 524 x 262) ---------------------------------------

func _build_all() -> void:
	_all = UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(12, 12, 12, 12))
	_all.custom_minimum_size = Vector2(524, 262)
	UI.at(_all, 90, 12)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	var head := HBoxContainer.new()
	_all_title = UI.label("All actions", "lilita", 18)
	head.add_child(_all_title)
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(sp)
	var edit := TagButton.make("Edit hotbar", 120, 36, 14)
	edit.cut = 10
	edit.icon = UI.icon("M4 20h4L19 9l-4-4L4 16z M13 7l4 4", UI.WHITE_WARM, 16, 2.4)
	edit.tooltip_text = "The Action cards screen isn't in this prototype"
	edit.pressed.connect(func(): fight.game.toast("The Action cards screen isn't in this prototype yet.", false))
	head.add_child(edit)
	var close := HexShape.make(30, 30, Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0).with_icon("close", UI.INK_SOFT, 16, 2.6)
	close.clickable = true
	close.pressed.connect(func(): _all.visible = false)
	head.add_child(close)
	v.add_child(head)
	_all_grid.columns = 3
	_all_grid.add_theme_constant_override("h_separation", 6)
	_all_grid.add_theme_constant_override("v_separation", 6)
	v.add_child(_all_grid)
	_all.add_child(v)
	_all.visible = false
	add_child(_all)


func _refresh_all() -> void:
	for c in _all_grid.get_children():
		_all_grid.remove_child(c)
		c.queue_free()
	if fight.current.is_empty():
		return
	_all_title.text = "All actions · " + fight.current.name
	for id in fight.current.cards:
		_all_grid.add_child(_card_button(id, false))


# --- End confirmation and the enemies' phase ---------------------------------------

func _build_confirm() -> void:
	_confirm = ColorRect.new()
	_confirm.color = Color(0.141, 0.188, 0.172, 0.55)
	_confirm.set_anchors_preset(Control.PRESET_FULL_RECT)
	_confirm.mouse_filter = Control.MOUSE_FILTER_STOP
	var cc := CenterContainer.new()
	cc.set_anchors_preset(Control.PRESET_FULL_RECT)
	_confirm.add_child(cc)
	var p := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(16, 16, 16, 16))
	p.custom_minimum_size.x = 300
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	v.add_child(UI.label("End allies' phase?", "lilita", 20))
	var t := UI.label("These allies still have AP left. Unspent AP is lost when the phase ends.", "n700", 13, UI.INK_SOFT)
	t.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	t.custom_minimum_size.x = 268
	v.add_child(t)
	_confirm_rows.add_theme_constant_override("separation", 6)
	v.add_child(_confirm_rows)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var keep := UI.FingerButton.new()
	keep.text = "Keep playing"
	keep.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	keep.custom_minimum_size.y = 44
	keep.add_theme_font_override("font", UI.font("lilita"))
	keep.add_theme_font_size_override("font_size", 14)
	var ks := UI.box(UI.CREAM_LIGHT, 12)
	ks.border_color = UI.RIM
	ks.set_border_width_all(2)
	for s in ["normal", "hover", "pressed", "focus"]:
		keep.add_theme_stylebox_override(s, ks)
	for s in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		keep.add_theme_color_override(s, UI.INK)
	keep.pressed.connect(hide_confirm)
	row.add_child(keep)
	var end := TagButton.make("End phase", 130, 44, 14)
	end.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	end.pressed.connect(fight.confirm_end)
	row.add_child(end)
	var gap := Control.new()
	gap.custom_minimum_size.y = 0
	v.add_child(gap)
	v.add_child(row)
	p.add_child(v)
	cc.add_child(p)
	_confirm.visible = false
	add_child(_confirm)


func show_confirm(left: Array) -> void:
	for c in _confirm_rows.get_children():
		_confirm_rows.remove_child(c)
		c.queue_free()
	for u in left:
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 8)
		h.add_child(HexShape.make(26, 30, Color(u.color), Color(u.color), 0).with_text(u.initial, 13))
		var n := UI.label(u.name, "n800", 13)
		n.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		n.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		n.size_flags_vertical = Control.SIZE_FILL
		h.add_child(n)
		var a := UI.label("%d AP%s" % [fight.ap_left(u), " (%d bonus)" % u.bonus if u.bonus > 0 else ""], "n900", 12, Color("#5A3A05"))
		a.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		a.size_flags_vertical = Control.SIZE_FILL
		h.add_child(a)
		_confirm_rows.add_child(h)
	_confirm.visible = true


func hide_confirm() -> void:
	_confirm.visible = false


func confirm_open() -> bool:
	return _confirm.visible


## While the foes act, a pill at the top says so (the mockup shows a modal "Enemies' phase" card with
## "[Enemy actions play out on the board]"; here they really do, so the board stays visible).
func _build_enemy_pill() -> void:
	_enemy_pill = UI.panel(UI.CREAM, 20, UI.CREAM_EDGE, 4, Vector4(18, 0, 18, 0))
	_enemy_pill.custom_minimum_size.y = 40
	var l := UI.label("Enemies' phase", "lilita", 17)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_enemy_pill.add_child(l)
	_enemy_pill.visible = false
	add_child(_enemy_pill)


# --- HP bars and floating numbers over the minis -----------------------------------

func _process(_delta: float) -> void:
	if not visible:
		return
	_enemy_pill.position = Vector2(368 - _enemy_pill.size.x * 0.5, 14)
	var cam := fight.game.rig.camera
	for u in fight.units:
		var key: int = u.mini.get_instance_id()
		var node: Control = _bar_nodes.get(key)
		if node == null:
			node = _make_bar(u)
			_bars.add_child(node)
			_bar_nodes[key] = node
		var world: Vector3 = u.mini.global_position + Vector3(0, 1.75, 0)
		node.visible = not (u.down and not u.ally) and not cam.is_position_behind(world)
		node.position = cam.unproject_position(world) - Vector2(node.size.x * 0.5, node.size.y)
		var bar: Bar = node.get_meta("bar")
		bar.value = float(maxi(u.hp, 0)) / u.max_hp
	for key in _bar_nodes.keys():
		if not fight.units.any(func(u): return u.mini.get_instance_id() == key):
			_bar_nodes[key].queue_free()
			_bar_nodes.erase(key)


## Above each mini: its letter (as on the mockup's tokens) and a 24 x 4 HP bar (Combat v14).
func _make_bar(u: Dictionary) -> Control:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 2)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var plate := HexShape.make(14, 16, UI.RED if not u.ally else Color("#C9A97A"), UI.RED if not u.ally else Color(u.color), 0 if not u.ally else 1.5)
	plate.with_text(u.initial, 9, UI.WHITE_WARM if not u.ally else UI.INK)
	var cc := CenterContainer.new()
	cc.add_child(plate)
	v.add_child(cc)
	var bar := Bar.make(24, 4, UI.DARK, UI.GREEN if u.ally else Color("#C4542A"))
	v.add_child(bar)
	v.set_meta("bar", bar)
	v.reset_size()
	return v


func float_text(u: Dictionary, text: String, hurt: bool, heal := false) -> void:
	var l := UI.label(text, "lilita", 18, Color("#2E7A3E") if heal else (UI.RED if hurt else UI.INK_SOFT))
	l.add_theme_constant_override("outline_size", 6)
	l.add_theme_color_override("font_outline_color", UI.CREAM_LIGHT)
	add_child(l)
	var cam := fight.game.rig.camera
	var p := cam.unproject_position(u.mini.global_position + Vector3(0, 2.2, 0))
	l.position = p - Vector2(20, 10)
	var tw := create_tween().set_parallel()
	tw.tween_property(l, "position:y", l.position.y - 24, 1.0)
	tw.tween_property(l, "modulate:a", 0.0, 0.6).set_delay(0.5)
	tw.chain().tween_callback(l.queue_free)


func refresh() -> void:
	_phase_label.text = {"allies": "Allies", "enemies": "Enemies", "over": "Done"}.get(fight.phase, "Allies")
	_enemy_pill.visible = fight.phase == "enemies"
	_refresh_tray()
	_refresh_details()
	_refresh_hotbar()
	if _all.visible:
		_refresh_all()
