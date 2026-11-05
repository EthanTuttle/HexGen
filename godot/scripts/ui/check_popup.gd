class_name CheckPopup
extends ColorRect
## The check pop-up from the social encounter mockup (mockups/social-encounter/Social-v9-Camera.dc.html; design/07 ->
## Social encounter screen): the approach tag, the coin line, the coins spinning before they land one after another,
## and a companion's chime-in after a short pause. Crossing water uses it twice: ask() is the small prompt that shows
## the coins before anything is committed, play() flips them. Silver Tongue and the picker aren't here: water's check
## is the hero's (design/02 -> Who crosses), and Silver Tongue is for social checks.

signal continued                        # the player closed the result

const COIN_STEP := 0.38                 # s per coin landing (Social v9)
const CHIME_WAIT := 0.35                # s after the last coin before the chime-in
const CHIME_FLIP := 1.3                 # s the companion's coin spins

var _box := VBoxContainer.new()
var _spinning: Array[CoinView] = []
var _run := 0


func _init() -> void:
	color = Color(0.141, 0.188, 0.172, 0.45)
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	visible = false
	var cc := CenterContainer.new()
	cc.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(cc)
	var p := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(16, 14, 16, 16))
	p.custom_minimum_size.x = 360
	_box.add_theme_constant_override("separation", 7)
	p.add_child(_box)
	cc.add_child(p)


func _process(_delta: float) -> void:
	# rotateY(720deg) in the mockup's coinspin, seen edge on as the coin narrows.
	var turn := absf(cos(Time.get_ticks_msec() / 1000.0 * TAU / 0.19))
	for c in _spinning:
		if is_instance_valid(c):
			c.pivot_offset = c.size * 0.5
			c.scale.x = turn


## The prompt, before the party sets off. view: tag, tag_bg, text, initial, face, line, coins. `on_stay` and `on_go`
## are the two buttons; stay_label names the first: "Walk round" where there's a way round, else "Back".
func ask(view: Dictionary, stay_label: String, on_stay: Callable, on_go: Callable, go_label := "Cross") -> void:
	_run += 1
	_clear()
	_head(view)
	var row := _coin_row()
	for _k in view.coins:
		row.add_child(CoinView.blank(34))
	var buttons := _buttons()
	var stay := _pill(stay_label, UI.SAND, UI.INK)
	stay.accessibility_name = stay_label
	stay.pressed.connect(on_stay)
	buttons.add_child(stay)
	var go := TagButton.make(go_label, 0, 40)
	go.accessibility_name = go_label
	go.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	go.pressed.connect(on_go)
	buttons.add_child(go)
	visible = true


## Flips: the same head, the coins landing in turn, then the helper (if any) and the result. flips: the hero's coins;
## helper: {} or initial, face, name, note, line; helper_heads: their coin; passed: the result. Emits continued.
## lucky: Lucky's reflip (design/03 -> Races -> Halfling), {at, heads}: that coin spins again under the clover, before any chime-in.
func play(view: Dictionary, flips: Array[bool], helper: Dictionary, helper_heads: bool, passed: bool, lucky := {}) -> void:
	_run += 1
	var run := _run
	_clear()
	_head(view)
	var row := _coin_row()
	var coins: Array[CoinView] = []
	for _k in flips:
		var c := CoinView.blank(34)
		row.add_child(c)
		coins.append(c)
		_spinning.append(c)
	visible = true
	for k in flips.size():
		await get_tree().create_timer(COIN_STEP).timeout
		if run != _run:
			return
		_land(coins[k], flips[k])
	if not lucky.is_empty():
		await get_tree().create_timer(CHIME_WAIT).timeout
		if run != _run:
			return
		var clover := TextureRect.new()   # PLACEHOLDER icon
		clover.texture = UI.icon(CreatorData.PI.clover, UI.GREEN, 20, 2.4)
		clover.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.add_child(clover)
		row.move_child(clover, lucky.at)
		coins[lucky.at].is_blank = true
		_spinning.append(coins[lucky.at])
		await get_tree().create_timer(CHIME_FLIP).timeout
		if run != _run:
			return
		_land(coins[lucky.at], lucky.heads)
	await get_tree().create_timer(CHIME_WAIT).timeout
	if run != _run:
		return
	if not helper.is_empty():
		var theirs := CoinView.blank(34)
		theirs.ring = UI.GREEN
		var cut := ColorRect.new()   # PLACEHOLDER look: the mockup's dashed divider, plain
		cut.color = UI.CREAM_EDGE
		cut.custom_minimum_size = Vector2(2, 34)
		cut.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.add_child(cut)
		row.add_child(theirs)
		_spinning.append(theirs)
		_box.add_child(_chime(helper))
		await get_tree().create_timer(CHIME_FLIP).timeout
		if run != _run:
			return
		_land(theirs, helper_heads)
	_box.add_child(UI.label("Passed!" if passed else "Failed", "lilita", 20, Color("#2E6B3A") if passed else UI.RED))
	var on := _pill("Continue", UI.DARK, UI.CREAM)
	on.accessibility_name = "Continue"
	on.pressed.connect(func():
		visible = false
		continued.emit())
	_buttons().add_child(on)


func _land(c: CoinView, heads: bool) -> void:
	_spinning.erase(c)
	c.scale.x = 1.0
	c.is_blank = false
	c.heads = heads
	c.queue_redraw()


func _clear() -> void:
	_spinning.clear()
	for c in _box.get_children():
		_box.remove_child(c)
		c.queue_free()


func _head(view: Dictionary) -> void:
	var tag := _Tag.new()
	tag.text = view.tag
	tag.bg = view.tag_bg
	tag.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_box.add_child(tag)
	_box.add_child(UI.label(view.text, "lilita", 18, UI.INK, 0, 1.15))
	var who := HBoxContainer.new()
	who.add_theme_constant_override("separation", 8)
	who.add_child(HexShape.make(28, 32, UI.RIM, Color(view.face), 2).with_text(view.initial, 12))
	var line := UI.label(view.line, "n900", 12, UI.INK_SOFT)
	line.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	who.add_child(line)
	_box.add_child(who)


func _coin_row() -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	row.custom_minimum_size.y = 40
	row.alignment = BoxContainer.ALIGNMENT_BEGIN
	_box.add_child(row)
	return row


func _buttons() -> HBoxContainer:
	var b := HBoxContainer.new()
	b.add_theme_constant_override("separation", 8)
	_box.add_child(b)
	return b


func _pill(t: String, bg: Color, ink: Color) -> Button:
	var b := UI.FingerButton.new()
	b.text = t
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.custom_minimum_size.y = 40
	b.add_theme_font_override("font", UI.font("n900"))
	b.add_theme_font_size_override("font_size", 13)
	for s in ["normal", "hover", "pressed", "focus"]:
		b.add_theme_stylebox_override(s, UI.box(bg if s != "hover" else bg.darkened(0.05), 20))
	for s in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(s, ink)
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	return b


## The companion's portrait and line, with "+1 coin" and a stage note (DOCS: 07 -> Companion chime-in, Chime-in lines).
func _chime(helper: Dictionary) -> Control:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	var portrait := HexShape.make(38, 44, UI.RIM, Color(helper.face), 3).with_text(helper.initial, 16).with_shadow(UI.HEX_SHADOW)
	portrait.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(portrait)
	var p := UI.panel(UI.CREAM_LIGHT, 12, Color(0, 0, 0, 0), 0, Vector4(12, 7, 12, 7))
	(p.get_theme_stylebox("panel") as StyleBoxFlat).set_border_width_all(2)
	(p.get_theme_stylebox("panel") as StyleBoxFlat).border_color = Color("#CFE3D2")
	p.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.add_child(UI.label("%s · +1 coin" % helper.name, "n900", 11, Color("#2E6B3A")))
	if helper.note != "":
		v.add_child(UI.label(helper.note, "n700", 11, UI.INK_MUTED))
	var line := UI.label(helper.line, "n800", 12)
	line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	line.custom_minimum_size.x = 250
	v.add_child(line)
	p.add_child(v)
	h.add_child(p)
	return h


## The check's approach tag: a small bar with pointed ends (Social v9).
class _Tag extends Control:
	var text := ""
	var bg := UI.DARK

	func _ready() -> void:
		var f := UI.font("n900", 1)
		custom_minimum_size = Vector2(f.get_string_size(text.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x + 24, 24)
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		draw_colored_polygon(UI.tag_points(Rect2(Vector2.ZERO, size), 8), bg)
		var f := UI.font("n900", 1)
		var asc := f.get_ascent(11)
		draw_string(f, Vector2(12, (size.y - (asc + f.get_descent(11))) * 0.5 + asc), text.to_upper(),
				HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.WHITE_WARM)
