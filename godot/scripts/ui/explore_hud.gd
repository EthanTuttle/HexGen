class_name ExploreHud
extends Control
## The exploration screen's HUD, built from Explore v8b (mockups/exploration/Explore-v8b-Sleeve.dc.html),
## in its 844 x 390 layout: party tray, Quests / equipment / nav buttons, prompt banner, toast, day clock,
## the hand in a side column, the encounter pop-up, and markers standing over the board.

var game: Game

var _tray := VBoxContainer.new()
var _nav_row := HBoxContainer.new()
var _cam_buttons := HBoxContainer.new()
var _nav: HexShape
var _banner: PanelContainer
var _banner_text: Label
var _banner_cancel: Button
var _toast: PanelContainer
var _toast_text: Label
var _clock_dial := ClockDial.new()
var _clock_title: Label
var _clock_sub: Label
var _hand_count: Label
var _hand_grid := Control.new()
var _hand_note: Label
var _deck_n: HexShape
var _discard_n: HexShape
var _enc_layer: ColorRect
var _enc_where: Label
var _enc_text: Label
var _enc_coins := HBoxContainer.new()
var _enc_buttons := HBoxContainer.new()
var _marks := Control.new()
var _toast_until := 0.0


func _init(g: Game) -> void:
	game = g
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	_marks.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_marks.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_marks)
	_build_tray()
	_build_buttons()
	_build_banner()
	_build_toast()
	_build_clock()
	_build_hand()
	_build_rest()
	_build_encounter()


# --- Party tray (left 12, top 12, width 60) ------------------------------------

func _build_tray() -> void:
	var p := UI.panel(UI.TRAY, 18, UI.TRAY_EDGE, 4, Vector4(6, 8, 6, 8))
	p.custom_minimum_size.x = 72       # CSS width 60 + padding (content-box)
	UI.at(p, 12, 12)
	_tray.add_theme_constant_override("separation", 5)
	_tray.alignment = BoxContainer.ALIGNMENT_CENTER
	p.add_child(_tray)
	add_child(p)


func _refresh_tray() -> void:
	for c in _tray.get_children():
		_tray.remove_child(c)
		c.queue_free()
	for m in game.party:
		var v := VBoxContainer.new()
		v.add_theme_constant_override("separation", 3)
		v.alignment = BoxContainer.ALIGNMENT_CENTER
		var h := HexShape.make(38, 44, UI.RIM, Color(m.color)).with_text(m.initial, 16).with_shadow(UI.HEX_SHADOW)
		h.tooltip_text = "%s: opens the character and gear screen (not in this prototype)" % m.name
		h.clickable = true
		var cc := CenterContainer.new()
		cc.add_child(h)
		v.add_child(cc)
		v.add_child(Bar.make(40, 5, Color("#E6DCC8"), UI.GREEN, float(m.hp) / m.max_hp, UI.HEX_SHADOW))
		_tray.add_child(v)


# --- Quests, equipment and the nav button (left 22, top 260) -------------------

func _build_buttons() -> void:
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 6)
	UI.at(col, 22, 260)
	var quests := HexShape.make(40, 46, UI.CREAM, UI.CREAM, 0).with_icon("quests", UI.INK, 18, 2.4).with_shadow(UI.HEX_SHADOW)
	quests.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	quests.clickable = true
	quests.tooltip_text = "Quests (not in this prototype)"
	quests.pressed.connect(func(): game.toast("The quest log isn't in this prototype yet.", false))
	col.add_child(quests)
	_nav_row.add_theme_constant_override("separation", 6)
	var gear := HexShape.make(40, 46, UI.CREAM, UI.CREAM, 0).with_icon("gear", UI.INK, 18, 2.4).with_shadow(UI.HEX_SHADOW)
	gear.clickable = true
	gear.tooltip_text = "Character and gear (not in this prototype)"
	gear.pressed.connect(func(): game.toast("The character and gear screen isn't in this prototype yet.", false))
	_nav_row.add_child(gear)
	_nav = HexShape.make(40, 46, UI.CREAM, UI.CREAM, 0).with_icon("nav", UI.INK, 18, 2.4).with_shadow(UI.HEX_SHADOW)
	_nav.clickable = true
	_nav.tooltip_text = "Camera controls"
	_nav.pressed.connect(_toggle_nav)
	_nav_row.add_child(_nav)
	_cam_buttons.add_theme_constant_override("separation", 4)
	_cam_buttons.visible = false
	var spacer := Control.new()
	spacer.custom_minimum_size.x = 0
	_cam_buttons.add_child(spacer)
	for b in [["zoom_in", "Zoom in"], ["zoom_out", "Zoom out"], ["rot_l", "Rotate left"], ["rot_r", "Rotate right"], ["center", "Center on the party"]]:
		var h := HexShape.make(40, 46, UI.CREAM, UI.CREAM, 0).with_icon(b[0], UI.INK, 18, 2.4).with_shadow(UI.HEX_SHADOW)
		h.clickable = true
		h.tooltip_text = b[1]
		h.pressed.connect(game.camera_button.bind(b[0]))
		_cam_buttons.add_child(h)
	_nav_row.add_child(_cam_buttons)
	col.add_child(_nav_row)
	add_child(col)


func _toggle_nav() -> void:
	_cam_buttons.visible = not _cam_buttons.visible
	_nav.rim = UI.DARK if _cam_buttons.visible else UI.CREAM
	_nav.with_icon("nav", UI.CREAM if _cam_buttons.visible else UI.INK, 18, 2.4)


# --- Banner (centred on x 378, top 14) and toast (bottom 16) -------------------

func _build_banner() -> void:
	_banner = UI.panel(UI.CREAM, 20, UI.CREAM_EDGE, 4, Vector4(16, 0, 6, 0))
	_banner.custom_minimum_size.y = 40
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	_banner_text = UI.label("", "n800", 13)
	_banner_text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(_banner_text)
	_banner_cancel = UI.FingerButton.new()
	_banner_cancel.text = "Cancel"
	_banner_cancel.custom_minimum_size = Vector2(0, 30)
	_banner_cancel.add_theme_font_override("font", UI.font("n900"))
	_banner_cancel.add_theme_font_size_override("font_size", 12)
	for s in ["normal", "hover", "pressed", "focus"]:
		_banner_cancel.add_theme_stylebox_override(s, UI.box(UI.SAND if s != "hover" else UI.SAND.darkened(0.05), 15, Color(0, 0, 0, 0), 0, Vector4(12, 0, 12, 0)))
	for s in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		_banner_cancel.add_theme_color_override(s, Color("#4A4034"))
	_banner_cancel.pressed.connect(func(): game.hold(-1))
	var cc := CenterContainer.new()
	cc.add_child(_banner_cancel)
	h.add_child(cc)
	_banner.add_child(h)
	add_child(_banner)


func _build_toast() -> void:
	_toast = UI.panel(UI.DARK, 16, UI.DARK_EDGE, 4, Vector4(16, 9, 16, 9))
	_toast_text = UI.label("", "n800", 13, UI.CREAM, 0, 1.3)
	_toast_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_toast.add_child(_toast_text)
	_toast.visible = false
	_toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_toast)


func show_toast(text: String, good: bool, seconds := 4.5) -> void:
	_toast_text.text = text
	_toast.add_theme_stylebox_override("panel", UI.box(UI.DARK if good else UI.RED, 16, UI.DARK_EDGE if good else UI.RED_EDGE, 4, Vector4(16, 9, 16, 9)))
	# Short toasts sit on one line; long ones wrap at the mockup's max width (420 incl. padding).
	var one_line := UI.font("n800").get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 13).x
	if one_line <= 388:
		_toast_text.autowrap_mode = TextServer.AUTOWRAP_OFF
		_toast_text.custom_minimum_size.x = 0
	else:
		_toast_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_toast_text.custom_minimum_size.x = 388
		_toast_text.size.x = 388
	_toast.visible = true
	_toast.size = Vector2.ZERO
	_toast_until = game.real_time + seconds
	await get_tree().process_frame
	_toast.size = Vector2.ZERO


func hide_toast() -> void:
	_toast.visible = false


# --- Day clock (left 680, top 12, width 152) ------------------------------------

func _build_clock() -> void:
	var p := UI.panel(UI.CREAM, 16, UI.CREAM_EDGE, 4, Vector4(8, 6, 8, 6))
	p.custom_minimum_size.x = 152
	UI.at_right(p, 680, 12)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	h.add_child(_clock_dial)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	_clock_title = UI.label("", "lilita", 15, UI.INK, 0, 1.1)
	_clock_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_clock_title.custom_minimum_size.x = 82
	_clock_sub = UI.label("", "n800", 11, UI.INK_SOFT, 0, 1.25)
	_clock_sub.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_clock_sub.custom_minimum_size.x = 82
	v.add_child(_clock_title)
	v.add_child(_clock_sub)
	h.add_child(v)
	p.add_child(h)
	add_child(p)


# --- Hand, in a side column (left 680, top 84, 152 x 294) ----------------------

func _build_hand() -> void:
	var p := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(10, 10, 10, 10))
	p.custom_minimum_size = Vector2(152, 294)
	p.size = Vector2(152, 294)
	p.clip_contents = true
	UI.at_right(p, 680, 84)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	var head := HBoxContainer.new()
	head.add_child(UI.label("Hand", "lilita", 16))
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(sp)
	_hand_count = UI.label("", "n900", 11, UI.INK_SOFT)
	head.add_child(_hand_count)
	v.add_child(head)
	_hand_grid.custom_minimum_size = Vector2(132, 104)
	_hand_grid.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(_hand_grid)
	_hand_note = UI.label("", "n800", 12, UI.INK_SOFT, 0, 1.3)
	_hand_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_hand_note.custom_minimum_size = Vector2(132, 32)
	v.add_child(_hand_note)
	var fill := Control.new()
	fill.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(fill)
	var piles := HBoxContainer.new()
	_deck_n = _pile(piles, "Deck", Color("#6B4C35"), Color("#8A6446"))
	var sp2 := Control.new()
	sp2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	piles.add_child(sp2)
	_discard_n = _pile(piles, "Discard", Color("#8F7E6A"), Color("#B3A38C"))
	v.add_child(piles)
	p.add_child(v)
	add_child(p)


func _pile(parent: Control, name: String, bg: Color, face: Color) -> HexShape:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 5)
	var hx := HexShape.make(26, 30, bg, face).with_text("0", 12, UI.CREAM).with_shadow(Color("#7E5F44"), 2)
	h.add_child(hx)
	var l := UI.label(name, "n900", 11, UI.INK_SOFT)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.size_flags_vertical = Control.SIZE_FILL
	h.add_child(l)
	parent.add_child(h)
	return hx


func _refresh_hand() -> void:
	for c in _hand_grid.get_children():
		_hand_grid.remove_child(c)
		c.queue_free()
	var hand: Array[String] = game.deck.hand
	var rows := ceili(hand.size() / 3.0)
	_hand_grid.custom_minimum_size.y = maxi(rows, 2) * 52
	for i in hand.size():
		var t := hand[i]
		var on := i == game.held
		var h := HexShape.make(40, 46, UI.ORANGE if on else UI.CREAM_LIGHT, UI.terrain_bg(t)).with_icon("t_" + t, UI.terrain_ink(t), 20)
		h.with_shadow(UI.ORANGE_EDGE if on else UI.HEX_SHADOW)
		h.position = Vector2((i % 3) * 46, (i / 3) * 52 + (0 if on else 6))
		h.clickable = true
		h.tooltip_text = Rules.NAMES[t] + (", held: tap a lit hex to place" if on else ", tap to hold")
		h.pressed.connect(game.hold.bind(i))
		h.gui_input.connect(_card_press.bind(i))
		_hand_grid.add_child(h)
	var over := hand.size() > Rules.HAND_LIMIT
	_hand_count.text = "%d / %d" % [hand.size(), Rules.HAND_LIMIT]
	_hand_count.add_theme_color_override("font_color", UI.RED if over else UI.INK_SOFT)
	var held := game.held_terrain()
	_hand_note.text = ("%s held. Lit hexes can take it; red ones clash with a neighbour." % Rules.NAMES[held] if held != "" else "Tap a card to hold it.") \
			+ (" Over the limit: discard down to 7 at your next rest." if over else "")
	_deck_n.with_text(str(game.deck.draw_pile.size()), 12, UI.CREAM)
	_discard_n.with_text(str(game.deck.discard.size()), 12, UI.CREAM)


# --- Rest action card (DOCS: Exploration screen -> Resting) ------------------------
# Along the bottom, like the combat hotbar's cards and the scenes' option cards; centred under the open board.

var _rest: Control


func _build_rest() -> void:
	_rest = _RestCard.new()
	_rest.tooltip_text = "Rest, heal, 8 hours pass, discard down to 7, reshuffle"
	_rest.pressed.connect(game.rest)
	UI.at(_rest, 378 - 37, 390 - 92 - 6)
	add_child(_rest)


class _RestCard extends Control:
	signal pressed

	func _init() -> void:
		custom_minimum_size = Vector2(74, 92)
		size = custom_minimum_size
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

	func _draw() -> void:
		# The combat hotbar card's look (Combat v14), with no AP hex: the map has no AP.
		var r := Rect2(Vector2(0, 8), Vector2(74, 84))
		var band := Color("#8A6446")   # PLACEHOLDER band colour (the camp's brown)
		draw_style_box(UI.box(UI.HEX_SHADOW, 10), Rect2(r.position + Vector2(0, 4), r.size))
		var face := UI.box(UI.CREAM_LIGHT, 10)
		face.border_color = band
		face.set_border_width_all(2)
		draw_style_box(face, r)
		draw_rect(Rect2(r.position + Vector2(2.5, 2.5), Vector2(69, 6)), band)
		draw_texture_rect(UI.icon("camp", Color("#5E4C30"), 26, 2), Rect2(r.position + Vector2(24, 20), Vector2(26, 26)), false)
		var f := UI.font("n900")
		draw_string(f, r.position + Vector2(37 - f.get_string_size("Rest", 0, -1, 11).x * 0.5, 60), "Rest",
				HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()


# --- Dragging a card onto the board (DOCS: Exploration screen -> Placing) ----------
# A card dragged from the hand follows the finger (drawn a little above it, so the finger doesn't hide it) and
# drops onto the slot under it when let go over a lit one; anywhere else it goes back to the hand.

## PLACEHOLDER (where a dragged card drops isn't decided): it rides this far above the finger and drops on
## the slot under the card, not under the finger.
const DRAG_LIFT := Vector2(0, -34)
var _drag := {}


func _card_press(e: InputEvent, i: int) -> void:
	if e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT and e.pressed:
		_drag = {i = i, start = (e as InputEventMouseButton).global_position, ghost = null}


func _input(e: InputEvent) -> void:
	if _drag.is_empty():
		return
	if e is InputEventMouseMotion:
		var p := (e as InputEventMouseMotion).position
		if _drag.ghost == null and p.distance_to(_drag.start) >= Rules.TAP_PIXELS and _drag.i < game.deck.hand.size():
			game.hold_for_drag(_drag.i)
			var t: String = game.deck.hand[_drag.i]
			var g := HexShape.make(40, 46, UI.ORANGE, UI.terrain_bg(t)).with_icon("t_" + t, UI.terrain_ink(t), 20)
			g.with_shadow(UI.ORANGE_EDGE, 6)
			g.mouse_filter = Control.MOUSE_FILTER_IGNORE
			add_child(g)
			_drag.ghost = g
		if _drag.ghost:
			var g: Control = _drag.ghost
			g.global_position = p + DRAG_LIFT - g.size * 0.5
	elif e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT and not e.pressed:
		var g = _drag.ghost
		_drag = {}
		if g == null:
			return   # a tap: the card's own press handles it
		var at: Vector2 = (g as Control).global_position + (g as Control).size * 0.5
		g.queue_free()
		var t := game.ground_tile(at)
		if game.held >= 0 and not _over_panel(at) and game.why_not(t, game.held_terrain()) == "":
			game.try_place(t)
		else:
			game.hold(-1)   # back to the hand
		get_viewport().set_input_as_handled()


## True if p is over one of the HUD's panels (the hand, the tray, the clock...), not the open board.
func _over_panel(p: Vector2) -> bool:
	for n in find_children("*", "Control", true, false):
		var c := n as Control
		if c.mouse_filter == Control.MOUSE_FILTER_STOP and c.is_visible_in_tree() and c.get_global_rect().has_point(p) \
				and c.size.x < get_viewport_rect().size.x * 0.9:
			return true
	for n in find_children("*", "PanelContainer", true, false):
		var c := n as Control
		if c.is_visible_in_tree() and c.get_global_rect().has_point(p) and c.size.x < get_viewport_rect().size.x * 0.9:
			return true
	return false


func dragging() -> bool:
	return not _drag.is_empty() and _drag.ghost != null


# --- Encounter pop-up ------------------------------------------------------------

func _build_encounter() -> void:
	_enc_layer = ColorRect.new()
	_enc_layer.color = Color(0.141, 0.188, 0.172, 0.45)
	_enc_layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	_enc_layer.mouse_filter = Control.MOUSE_FILTER_STOP
	var cc := CenterContainer.new()
	cc.set_anchors_preset(Control.PRESET_FULL_RECT)
	_enc_layer.add_child(cc)
	var p := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(16, 16, 16, 16))
	p.custom_minimum_size.x = 300
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	_enc_where = UI.label("", "n900", 11, UI.RED, 1)
	v.add_child(_enc_where)
	v.add_child(UI.label("[Enemy group]", "lilita", 20))
	_enc_text = UI.label("", "n700", 12, UI.INK_SOFT, 0, 1.35)
	_enc_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_enc_text.custom_minimum_size.x = 268
	v.add_child(_enc_text)
	_enc_coins.add_theme_constant_override("separation", 6)
	v.add_child(_enc_coins)
	_enc_buttons.add_theme_constant_override("separation", 8)
	var gap := Control.new()
	gap.custom_minimum_size.y = 0
	v.add_child(gap)
	v.add_child(_enc_buttons)
	p.add_child(v)
	cc.add_child(p)
	_enc_layer.visible = false
	add_child(_enc_layer)


## stage: "ask", "passed" or "spotted"
func show_encounter(where: String, stage: String, coins: Array) -> void:
	_enc_where.text = ("Encounter · " + where).to_upper()
	_enc_text.text = {
		"ask": "Foes block the way. Fight them, or try to slip past with a Stealth group check (everyone flips; needs 1 heads).",
		"passed": "You slipped past. The encounter stays on the map until it despawns.",
		"spotted": "Spotted! The fight is on."}[stage]
	for c in _enc_coins.get_children():
		_enc_coins.remove_child(c)
		c.queue_free()
	for h in coins:
		_enc_coins.add_child(CoinView.make(h, 30))
	_enc_coins.visible = not coins.is_empty()
	for c in _enc_buttons.get_children():
		_enc_buttons.remove_child(c)
		c.queue_free()
	if stage != "passed":
		var fight := TagButton.make("Fight", 0, 40)
		fight.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		fight.pressed.connect(game.choose_fight)
		_enc_buttons.add_child(fight)
	if stage == "ask":
		var sneak := _pill_button("Sneak past", "Stealth, group", UI.SAND, UI.INK)
		sneak.pressed.connect(game.choose_sneak)
		_enc_buttons.add_child(sneak)
	if stage == "passed":
		var on := _pill_button("Carry on", "", UI.DARK, UI.CREAM)
		on.pressed.connect(game.choose_carry_on)
		_enc_buttons.add_child(on)
	_enc_layer.visible = true


func hide_encounter() -> void:
	_enc_layer.visible = false


func encounter_open() -> bool:
	return _enc_layer.visible


func _pill_button(t: String, sub: String, bg: Color, ink: Color) -> Button:
	var b := UI.FingerButton.new()
	b.text = t + ("\n" + sub if sub != "" else "")
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.custom_minimum_size.y = 40
	b.add_theme_font_override("font", UI.font("n900"))
	b.add_theme_font_size_override("font_size", 12 if sub != "" else 13)
	b.add_theme_constant_override("line_spacing", -3)
	for s in ["normal", "hover", "pressed", "focus"]:
		b.add_theme_stylebox_override(s, UI.box(bg if s != "hover" else bg.darkened(0.05), 20, Color(0, 0, 0, 0), 0, Vector4(6, 2, 6, 2)))
	for s in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(s, ink)
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	return b


# --- Refresh ---------------------------------------------------------------------

func refresh() -> void:
	_refresh_tray()
	_refresh_hand()
	# The Rest card shows while the party stands on a camp (DOCS: Exploration screen -> Resting).
	_rest.visible = game.party_tile == Rules.START_TILE and not game.busy
	var held := game.held_terrain()
	if held != "":
		_banner_text.text = "Place %s · tap a lit hex" % Rules.NAMES[held]
		_banner_cancel.get_parent().visible = true
	elif not game.deck.hand.is_empty():
		_banner_text.text = "Pick a card to build, or tap a hex to walk"
		_banner_cancel.get_parent().visible = false
	else:
		_banner_text.text = "Hand empty: tap a hex to walk and find a fight"
		_banner_cancel.get_parent().visible = false
	_banner.reset_size()


func _process(_delta: float) -> void:
	# Clock (mockup: Day N · phase; "Nightfall in N min" / "Dawn in N min")
	var m: float = game.minute
	var night := m >= Rules.NIGHT_AT
	_clock_dial.minute = m
	_clock_dial.night = night
	_clock_dial.queue_redraw()
	var left := (Rules.DAY_MINUTES - m) if night else (Rules.NIGHT_AT - m)
	_clock_title.text = "Day %d · %s" % [game.day, Rules.phase_name(m)]
	_clock_sub.text = ("Dawn in " if night else "Nightfall in ") + ("under a minute" if left < 1 else "%d min" % ceili(left))
	_clock_sub.add_theme_color_override("font_color", UI.RED if night or left <= 5 else UI.INK_SOFT)
	# Banner and toast stay centred on x = 378 (the open area left of the hand column)
	_banner.position = Vector2(378 - _banner.size.x * 0.5, 14)
	if _toast.visible:
		_toast.position = Vector2(378 - _toast.size.x * 0.5, 390 - 16 - _toast.size.y)
		if game.real_time > _toast_until:
			_toast.visible = false
	_place_marks()


# --- Markers over the board (cluster goals, the encounter, landmark pins) --------

var _mark_nodes := {}


func _place_marks() -> void:
	var want := {}
	for m in game.markers():
		var key: String = m.key
		want[key] = true
		var node: Control = _mark_nodes.get(key)
		if node == null or node.get_meta("text", "") != m.text:
			if node:
				node.queue_free()
			node = _make_mark(m)
			node.set_meta("text", m.text)
			_marks.add_child(node)
			_mark_nodes[key] = node
		var cam := game.rig.camera
		var world: Vector3 = m.world
		node.visible = not cam.is_position_behind(world)
		var p := cam.unproject_position(world)
		node.global_position = p - Vector2(node.size.x * 0.5, node.size.y) - Vector2(0, m.get("lift", 26))  # on the board, so screen coordinates
	for key in _mark_nodes.keys():
		if not want.has(key):
			_mark_nodes[key].queue_free()
			_mark_nodes.erase(key)


func _make_mark(m: Dictionary) -> Control:
	match m.kind:
		"goal":
			var p := UI.panel(UI.DARK, 12, UI.DARK_EDGE, 3, Vector4(7, 0, 7, 0))
			p.custom_minimum_size = Vector2(22, 24)
			var l := UI.label(m.text, "lilita", 13, UI.CREAM)
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			p.add_child(l)
			p.mouse_filter = Control.MOUSE_FILTER_IGNORE
			p.tooltip_text = m.get("aria", "")
			return p
		"walk":
			var p := UI.panel(UI.DARK, 12, UI.DARK_EDGE, 3, Vector4(9, 0, 9, 0))
			p.custom_minimum_size = Vector2(0, 24)
			var l := UI.label(m.text, "n900", 11, UI.CREAM)
			l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			p.add_child(l)
			p.mouse_filter = Control.MOUSE_FILTER_IGNORE
			return p
		"encounter":
			var p := UI.panel(UI.RED, 12, UI.RED_EDGE, 3, Vector4(7, 0, 7, 0))
			p.custom_minimum_size = Vector2(28, 24)
			var cc := CenterContainer.new()
			cc.add_child(UI.icon_rect("swords", UI.WHITE_WARM, 14, 2.6))
			p.add_child(cc)
			p.mouse_filter = Control.MOUSE_FILTER_IGNORE
			return p
		_:   # landmark pin, with its name while open
			var v := VBoxContainer.new()
			v.alignment = BoxContainer.ALIGNMENT_END
			v.add_theme_constant_override("separation", 3)
			v.mouse_filter = Control.MOUSE_FILTER_IGNORE
			if m.get("open", false):
				var tag := UI.panel(UI.CREAM_LIGHT, 10, UI.CREAM_EDGE, 3, Vector4(10, 4, 10, 4))
				var tv := VBoxContainer.new()
				tv.add_theme_constant_override("separation", 0)
				var a := UI.label(m.name, "lilita", 12)
				a.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
				var b := UI.label(m.region, "n800", 9, INK_REGION)
				b.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
				tv.add_child(a)
				tv.add_child(b)
				tag.add_child(tv)
				tag.mouse_filter = Control.MOUSE_FILTER_IGNORE
				var cc := CenterContainer.new()
				cc.add_child(tag)
				v.add_child(cc)
			var pin := _Pin.new()
			pin.custom_minimum_size = Vector2(22, 24)
			pin.tooltip_text = m.name
			pin.clicked.connect(game.toggle_pin.bind(m.tile))
			var c2 := CenterContainer.new()
			c2.add_child(pin)
			v.add_child(c2)
			v.reset_size()
			return v


const INK_REGION := Color("#5A5040")


## The landmark pin: a cream disc with a brown ring and the landmark icon.
class _Pin extends Control:
	signal clicked

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

	func _draw() -> void:
		var c := Vector2(11, 11)
		draw_circle(c + Vector2(0, 2), 11, Color("#6B4C35"))
		draw_circle(c, 11, Color("#8A6446"))
		draw_circle(c, 9, UI.CREAM_LIGHT)
		draw_texture_rect(UI.icon("landmark", Color("#5E4C30"), 12, 2.6), Rect2(c - Vector2(6, 6), Vector2(12, 12)), false)

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			clicked.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)
