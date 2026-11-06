class_name TitleScreen
extends Control
## The title screen, from Title v11 (mockups/title-and-icon/Title-v11-CopyCode.dc.html; design/07 -> Title screen).
## New campaign is the main button on a first launch; Continue and Load stay hidden until a save exists (Saves). Behind it
## stands the latest save's map, or a generic world on a first launch (Front). PLACEHOLDER: Multiplayer and Settings say "Not
## in the prototype yet".

const SETTINGS_ICON := "M9 12a3 3 0 1 0 6 0a3 3 0 1 0-6 0 M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
const LEFT := 36.0                     # the mockup's 30 + 6, from the screen's edge
const LEFT_IN_SAFE := 8.0              # the least room left inside the safe area, on a phone

signal new_campaign

var front: Front
var _left: Control
var _toast: PanelContainer
var _toast_run := 0
var _buttons: Array[TagButton] = []
var _pops: SavePopups


func _init(f: Front) -> void:
	front = f
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	_left = Control.new()
	_left.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_left.anchor_bottom = 1.0
	add_child(_left)
	var logo := Logo.new()
	logo.position = Vector2(0, 22)
	_left.add_child(logo)
	_rise(logo, 0.6, 0.0)

	_build_buttons(true)

	var gear := HexShape.make(46, 52, UI.CREAM_LIGHT, UI.CREAM_LIGHT, 0).with_icon(SETTINGS_ICON, Color("#33403B"), 22).with_shadow(UI.HEX_SHADOW)
	gear.clickable = true
	gear.accessibility_name = "Settings"
	gear.pressed.connect(_not_yet)
	UI.at_right(gear, 844 - 22 - 46, 18)
	add_child(gear)
	resized.connect(_place_left)   # the safe area moved
	_place_left()


## Title v11's buttons: Continue (the latest autosave, with its hero, level, place and time under it), New campaign, then Load
## and Multiplayer in a row. With no save, New campaign is the main button and Continue and Load stay hidden (DOCS: first
## launch). Built again when Load deletes a hero's saves.
func _build_buttons(rise := false) -> void:
	for b in _buttons:
		b.queue_free()
	_buttons.clear()
	var heroes := Saves.heroes().filter(func(h): return not h.autos.is_empty() or h.slots.any(func(s): return not s.is_empty()))
	var latest: Dictionary = heroes[0] if not heroes.is_empty() else {}
	var last := 390.0 - 22.0 - 38.0
	if latest.is_empty():
		_add(_button("New campaign", 62, true), last - 10 - 62, func(): new_campaign.emit(), rise, 0.25)
		_add(_button("Multiplayer", 38, false), last, _not_yet, rise, 0.35)
		return
	if not latest.autos.is_empty():
		var cont := _button("Continue", 62, true)
		cont.text = ""
		var lines := VBoxContainer.new()
		lines.add_theme_constant_override("separation", -2)
		lines.alignment = BoxContainer.ALIGNMENT_CENTER
		lines.set_anchors_preset(Control.PRESET_FULL_RECT)
		lines.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var a: Dictionary = latest.autos[0]
		for l in [["Continue", "lilita", 20], ["%s · Lv %d" % [latest.name, a.level], "n800", 11], ["%s · %s" % [a.place, a.time], "n800", 11]]:
			var lab := UI.label(l[0], l[1], l[2], UI.CREAM_LIGHT, 0, 1.1)
			lab.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			if l[1] != "lilita":
				lab.modulate.a = 0.9
			lines.add_child(lab)
		cont.add_child(lines)
		_add(cont, last - 10 - 38 - 10 - 62, func(): _continue(latest), rise, 0.15)
	_add(_button("New campaign", 38, false), last - 10 - 38, func(): new_campaign.emit(), rise, 0.25)
	var load := _button("Load", 38, false)
	load.custom_minimum_size.x = 230 - 10 - 142
	load.size.x = load.custom_minimum_size.x
	_add(load, last, _open_load, rise, 0.35)
	var mp := _button("Multiplayer", 38, false)
	mp.custom_minimum_size.x = 142
	mp.size.x = 142
	_add(mp, last, _not_yet, rise, 0.35)
	mp.position.x = 230 - 142


func _add(b: TagButton, y: float, on_press: Callable, rise: bool, delay: float) -> void:
	UI.at(b, 0, y)
	b.accessibility_name = b.text if b.text != "" else "Continue"
	b.pressed.connect(on_press)
	_left.add_child(b)
	_buttons.append(b)
	if rise:
		_rise(b, 0.5, delay)


## The hero's latest autosave; if it won't read, the newest one that does.
func _continue(hero: Dictionary) -> void:
	for a: Dictionary in hero.autos:
		var data := Saves.read(hero.id, a.file)
		if not data.is_empty():
			Saves.play(get_tree(), data)
			return


func _open_load() -> void:
	if _pops == null:
		_pops = SavePopups.new()
		front.ui.add_child(_pops)
		_pops.deleted.connect(_build_buttons)
	_pops.show_load()


## The mockup's left edge, or further in where the phone's safe area needs it: this control already starts at the inset.
func _place_left() -> void:
	var inset: float = front.safe.inset.x
	_left.position.x = maxf(LEFT - inset, LEFT_IN_SAFE)


func _button(text: String, h: float, primary: bool) -> TagButton:
	var b := TagButton.make(text, 230, h, 20 if primary else 16)
	b.cut = 16.0 if primary else 13.0
	if primary:
		b.ink = UI.CREAM_LIGHT
		b.drop = 4.0
	else:
		b.bg = UI.CREAM_LIGHT
		b.ink = Color("#33403B")
		b.shadow = UI.HEX_SHADOW
		b.drop = 3.0
	b.soft_shadow = true
	return b


## CSS rise: up 14 px and fading in, after a delay.
func _rise(c: Control, seconds: float, delay: float) -> void:
	var y := c.position.y
	c.position.y = y + 14.0
	c.modulate.a = 0.0
	var tw := c.create_tween().set_parallel().set_ease(Tween.EASE_OUT)
	tw.tween_property(c, "position:y", y, seconds).set_delay(delay)
	tw.tween_property(c, "modulate:a", 1.0, seconds).set_delay(delay)


func _not_yet() -> void:
	_toast_run += 1
	var run := _toast_run
	if _toast:
		_toast.queue_free()
	_toast = UI.panel(UI.DARK, 14, Color(0, 0, 0, 0), 0, Vector4(14, 6, 14, 6))
	_toast.add_child(UI.label("Not in the prototype yet", "n800", 12, UI.CREAM_LIGHT))
	_toast.anchor_left = 0.5
	_toast.anchor_right = 0.5
	_toast.anchor_top = 1.0
	_toast.anchor_bottom = 1.0
	_toast.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_toast.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_toast.offset_bottom = -18
	_toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_toast)
	await get_tree().create_timer(1.4).timeout
	if run == _toast_run and _toast:
		_toast.queue_free()
		_toast = null


## The logo (Title v4 on): the wordmark in Lilita One, clay orange with a cream outline, a wooden edge and a soft shadow,
## "or" on a gold coin and a small hex tile before "Hexes". Copies the mockup's stacked text-shadows.
class Logo extends Control:
	const OUTLINE: Array[Vector2] = [Vector2(-3, 0), Vector2(3, 0), Vector2(0, -3), Vector2(0, 3), Vector2(-2, -2), Vector2(2, -2),
		Vector2(-2, 2), Vector2(2, 2), Vector2(-3, 2), Vector2(3, 2), Vector2(-3, 4), Vector2(3, 4), Vector2(0, 5), Vector2(-2, 6),
		Vector2(2, 6), Vector2(0, 8)]
	const SIZE := 41

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		accessibility_name = "Heads or Hexes"
		size = Vector2(240, 90)

	func _word(at: Vector2, text: String) -> void:
		var f := UI.font("lilita")
		var base := at + Vector2(0, f.get_ascent(SIZE))
		for k in 6:   # the mockup's 14 px blur
			var s := 4.0 + k * 2.0
			for d: Vector2 in [Vector2(-s, 0), Vector2(s, 0), Vector2(0, -s), Vector2(0, s)]:
				draw_string(f, base + d + Vector2(0, 12), text, HORIZONTAL_ALIGNMENT_LEFT, -1, SIZE, Color(0.141, 0.188, 0.172, 0.018))
		draw_string(f, base + Vector2(0, 10), text, HORIZONTAL_ALIGNMENT_LEFT, -1, SIZE, UI.ORANGE_EDGE)
		for d in OUTLINE:
			draw_string(f, base + d, text, HORIZONTAL_ALIGNMENT_LEFT, -1, SIZE, UI.CREAM_LIGHT)
		draw_string(f, base, text, HORIZONTAL_ALIGNMENT_LEFT, -1, SIZE, UI.ORANGE)

	func _draw() -> void:
		var f := UI.font("lilita")
		var line := f.get_ascent(SIZE) + f.get_descent(SIZE)
		line = maxf(line, SIZE)
		_word(Vector2.ZERO, "Heads")
		var w := f.get_string_size("Heads", HORIZONTAL_ALIGNMENT_LEFT, -1, SIZE).x
		var c := Vector2(w + 8 + 17, line * 0.5)
		draw_circle(c + Vector2(0, 5), 17, Color("#9A6A12"))
		draw_circle(c, 17, Color("#C9A24A"))
		draw_circle(c, 14, UI.GOLD)
		var or_w := f.get_string_size("or", HORIZONTAL_ALIGNMENT_LEFT, -1, 14).x
		draw_string(f, c + Vector2(-or_w * 0.5, 5), "or", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, UI.ORANGE_EDGE)
		var y := line + 2.0
		var hex := Rect2(Vector2(20, y + (line - 32) * 0.5), Vector2(28, 32))
		draw_colored_polygon(UI.hex_points(Rect2(hex.position + Vector2(0, 4), hex.size)), UI.ORANGE_EDGE)
		draw_colored_polygon(UI.hex_points(hex), UI.CREAM_LIGHT)
		draw_colored_polygon(UI.hex_points(hex.grow(-4)), Color("#6E9E5F"))
		var k := hex.grow(-4).size.x * 0.6 / 24.0
		var o := hex.get_center() - Vector2(12, 12) * k
		var at := func(x: float, py: float) -> Vector2: return o + Vector2(x, py) * k
		draw_colored_polygon(PackedVector2Array([at.call(5, 17), at.call(12, 3), at.call(19, 17)]), Color("#4C7D47"))
		draw_colored_polygon(PackedVector2Array([at.call(12, 3), at.call(19, 17), at.call(12, 17)]), Color("#3F6A3E"))
		draw_rect(Rect2(at.call(10.8, 17), Vector2(2.4, 4) * k), Color("#7E5A3A"))
		_word(Vector2(20 + 28 + 6, y), "Hexes")
