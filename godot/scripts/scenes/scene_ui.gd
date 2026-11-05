class_name SceneUI
extends RefCounted
## What the town and social scenes share (Town v9, Social v9): the speaker's panel on top, the option cards dealt along the
## bottom, Leave as a dark card, gold. Scenes show the party and the camera, not the map's hand and clock.

const ICONS := {
	"person": "M12 4a4 4 0 1 0 0 8a4 4 0 1 0 0-8 M4 21c1-4 4-6 8-6s7 2 8 6",
	"house": "M4 11l8-6 8 6v9H4z M10 20v-5h4v5",
	"shop": "M4 9l1.5-5h13L20 9 M4 9h16v2a3 3 0 0 1-5 2 3 3 0 0 1-6 0 3 3 0 0 1-5-2z M5 13v7h14v-7 M10 20v-4h4v4",
	"inn": "M3 18V8 M3 14h18v4 M21 14v-2a3 3 0 0 0-3-3h-7v5 M7 11a1.5 1.5 0 1 0 0.01 0",
	"back": "M15 6l-6 6 6 6",
	"next": "M9 6l6 6-6 6",
	"check": "M5 12l5 5 9-10",
	"heart": "M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z",
	"clock": "M12 4a8 8 0 1 0 0 16a8 8 0 1 0 0-16 M12 8v4l3 2",
	"cards": "M8 4h10v14H8z M5 7v13h10",
	"mug": "M5 8h10v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z M15 11h2a2 2 0 0 1 0 4h-2 M7 5c0-1 1-2 2-2s1 1 2 1 2-1 2-1",
	"moon": "M20 14A8 8 0 1 1 10 4a6.5 6.5 0 0 0 10 10z",
	"tent": "M3 20L12 4l9 16z M12 4v16 M9 20l3-5 3 5",
	"potion": "M10 3h4 M10 3v5l-4.5 6.5A4.5 4.5 0 0 0 9.5 21h5a4.5 4.5 0 0 0 4-6.5L14 8V3 M7 14h10",
	"bow": "M6 3c9 3 9 15 0 18 M6 3v18 M3 12h15 M15 9l3 3-3 3",
	"axe": "M5 19L15 9 M13 4c5 0 7 3 7 7-3 0-5-1-7-3z",
	"spear": "M4 20L17 7 M17 7l3-4-4 1z",
	"sword": "M20 4L9 15 M20 4h-5 M20 4v5 M6 12l6 6 M8 16l-4 4",
	"armor": "M8 3L4 6v6h3v9h10v-9h3V6l-4-3c-1 2-7 2-8 0z",
	"drop": "M12 3s7 7 7 12a7 7 0 0 1-14 0c0-5 7-12 7-12z",
}


## The speaker's panel: portrait hex, name, sub-line, the line itself.
class Head extends PanelContainer:
	var _hex: HexShape
	var _name := UI.label("", "lilita", 16, Color("#245A7E"))
	var _sub := UI.label("", "n800", 11, UI.INK_MUTED)
	var _note := UI.label("", "n700", 11, UI.INK_MUTED)
	var _line := UI.label("", "n800", 14, UI.INK, 0, 1.35)
	var _arrow: TextureRect

	func _init() -> void:
		add_theme_stylebox_override("panel", UI.box(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(10, 10, 52, 10)))
		custom_minimum_size = Vector2(560, 76)
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		UI.at(self, 160, 12)
		var h := CUI.hbox(12)
		_hex = HexShape.make(46, 53, UI.RIM, UI.CREAM, 3).with_shadow(UI.HEX_SHADOW)
		_hex.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
		h.add_child(_hex)
		var v := CUI.vbox(3)
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var top := CUI.hbox(8)
		top.add_child(_name)
		_sub.size_flags_vertical = Control.SIZE_SHRINK_END
		top.add_child(_sub)
		v.add_child(top)
		v.add_child(_note)
		_line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		v.add_child(_line)
		h.add_child(v)
		add_child(h)
		_arrow = UI.icon_rect(ICONS.next, UI.ORANGE, 20, 3.0)
		_arrow.visible = false
		_arrow.position = Vector2(26, 28)
		var holder := Control.new()
		holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
		holder.custom_minimum_size = Vector2.ZERO
		holder.add_child(_arrow)
		h.add_child(holder)

	## The panel's width: the mockup's 560, less on a phone where the gold pill needs its room beside it.
	func fit(room: float) -> void:
		var w := minf(560.0, room)
		custom_minimum_size.x = w
		size.x = w
		_line.custom_minimum_size.x = w - 10.0 - 52.0 - 46.0 - 12.0

	func say(who: String, sub: String, line: String, face: Color, ink: Color, icon: String, initial := "", note := "", more := false) -> void:
		_name.text = who
		_sub.text = sub
		_line.text = line
		_note.text = note
		_note.visible = note != ""
		_arrow.visible = more
		_hex.face = face
		_hex.icon = null
		_hex.text = ""
		if initial != "":
			_hex.with_text(initial, 20, UI.INK)
		elif icon != "":
			_hex.with_icon(icon, ink, 24)
		_hex.queue_redraw()
		_line.modulate.a = 0.0
		var tw := _line.create_tween()
		tw.tween_property(_line, "modulate:a", 1.0, 0.3).set_ease(Tween.EASE_OUT)


## A 108 pt option card: band, icon, words.
class OptionCard extends Control:
	signal pressed
	var band := UI.DARK
	var band_ink := UI.WHITE_WARM
	var band_text := ""
	var coin := false
	var dim := false
	var icon: Texture2D
	var words := ""
	var word_font := "lilita"
	var word_px := 14

	func _init() -> void:
		custom_minimum_size = Vector2(108, 108)
		size = custom_minimum_size
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size)
		var a := 0.6 if dim else 1.0
		draw_style_box(UI.box(Color(UI.HEX_SHADOW, a), 12), Rect2(Vector2(0, 4), size))
		var face := UI.box(Color(UI.CREAM_LIGHT, a), 12)
		draw_style_box(face, r)
		var top := StyleBoxFlat.new()
		top.bg_color = Color(band, a)
		top.corner_radius_top_left = 12
		top.corner_radius_top_right = 12
		draw_style_box(top, Rect2(0, 0, size.x, 22))
		var line := UI.box(Color(0, 0, 0, 0), 12)
		line.draw_center = false
		line.set_border_width_all(2)
		line.border_color = Color(CUI.PANEL_LINE, a)
		draw_style_box(line, r)
		var f := UI.font("n900", 1)
		var tw := f.get_string_size(band_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x + (15.0 if coin else 0.0)
		var x := (size.x - tw) * 0.5
		if coin:
			draw_circle(Vector2(x + 5.5, 11), 5.5, UI.GOLD)
			x += 15.0
		draw_string(f, Vector2(x, 15), band_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(band_ink, a))
		if icon:
			draw_texture_rect(icon, Rect2(Vector2(size.x * 0.5 - 13, 31), Vector2(26, 26)), false, Color(1, 1, 1, a))
		var fw := UI.font(word_font)
		var rows := _wrap(fw, words, size.x - 16.0, word_px)
		var y := 64.0 + fw.get_ascent(word_px)
		for row in rows:
			var w := fw.get_string_size(row, HORIZONTAL_ALIGNMENT_LEFT, -1, word_px).x
			draw_string(fw, Vector2((size.x - w) * 0.5, y), row, HORIZONTAL_ALIGNMENT_LEFT, -1, word_px, Color(UI.INK, a))
			y += word_px * 1.2

	func _wrap(f: Font, text: String, w: float, px: int) -> Array[String]:
		var rows: Array[String] = []
		var cur := ""
		for word in text.split(" "):
			var t := word if cur == "" else cur + " " + word
			if f.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, px).x > w and cur != "":
				rows.append(cur)
				cur = word
			else:
				cur = t
		rows.append(cur)
		return rows


static func card(band_text: String, band: Color, icon: String, ink: Color, words: String, what := "") -> OptionCard:
	var c := OptionCard.new()
	c.band_text = band_text
	c.band = band
	c.icon = UI.icon(icon, ink, 26, 2.2)
	c.words = words
	c.accessibility_name = what if what != "" else words
	return c


## Leave or Back, the dark card at the end of the row.
static func dark_card(words: String) -> Control:
	var t := DarkCard.new()
	t.words = words
	t.accessibility_name = words
	return t


class DarkCard extends Control:
	signal pressed
	var words := ""

	func _init() -> void:
		custom_minimum_size = Vector2(78, 108)
		size = custom_minimum_size
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _draw() -> void:
		draw_style_box(UI.box(UI.DARK_EDGE, 12), Rect2(Vector2(0, 4), size))
		draw_style_box(UI.box(UI.DARK, 12), Rect2(Vector2.ZERO, size))
		draw_texture_rect(UI.icon(ICONS.back, UI.CREAM, 22, 2.6), Rect2(size.x * 0.5 - 11, 34, 22, 22), false)
		var f := UI.font("n900")
		var w := f.get_string_size(words, HORIZONTAL_ALIGNMENT_LEFT, -1, 13).x
		draw_string(f, Vector2((size.x - w) * 0.5, 76), words, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, UI.CREAM)


## The row of cards along the bottom, centred in the room right of the nav button.
static func card_row() -> HBoxContainer:
	var h := CUI.hbox(8)
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.anchor_top = 1.0
	h.anchor_bottom = 1.0
	h.anchor_right = 1.0
	h.offset_left = 96
	h.offset_right = -12
	h.offset_top = -14 - 108
	h.offset_bottom = -14
	return h


## The gold pill (Town v9), top right.
static func gold_pill(amount: int) -> Control:
	var p := UI.panel(UI.DARK, 17, Color(0, 0, 0, 0), 0, Vector4(6, 0, 12, 0))
	p.custom_minimum_size.y = 34
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	UI.at_right(p, 745, 12)
	var h := CUI.hbox(6)
	h.add_child(CUI.Dot.make(22, UI.GOLD, "", 0))
	var l := UI.label(str(amount), "n900", 13, UI.CREAM)
	l.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(l)
	p.add_child(h)
	return p


## A reward pops big in the middle, then flies to its home (Social v3a). Status effects go by the party panel.
static func reveal_reward(parent: Control, type: String, reward_name: String, col: Color, icon: String, to: Vector2) -> void:
	var p := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(10, 10, 10, 10))
	p.custom_minimum_size = Vector2(200, 132)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := CUI.vbox(4)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	var hx := HexShape.make(52, 60, col, UI.CREAM_LIGHT, 4).with_icon(icon, col, 26).with_shadow(UI.HEX_SHADOW)
	hx.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(hx)
	var t := UI.label(type.to_upper(), "n900", 11, col, 1)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	var n := UI.label(reward_name, "lilita", 17, UI.INK, 0, 1.1)
	n.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(n)
	p.add_child(v)
	parent.add_child(p)
	p.position = parent.size * 0.5 - Vector2(100, 66)
	p.pivot_offset = Vector2(100, 66)
	p.scale = Vector2(0.3, 0.3)
	p.modulate.a = 0.0
	var tw := p.create_tween()
	tw.tween_property(p, "scale", Vector2(1.1, 1.1), 0.25).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(p, "modulate:a", 1.0, 0.25)
	tw.tween_property(p, "scale", Vector2.ONE, 0.18)
	tw.tween_interval(0.8)
	tw.tween_property(p, "position", to - Vector2(100, 66), 0.58).set_ease(Tween.EASE_IN_OUT).set_trans(Tween.TRANS_CUBIC)
	tw.parallel().tween_property(p, "scale", Vector2(0.12, 0.12), 0.58)
	tw.parallel().tween_property(p, "modulate:a", 0.0, 0.58)
	tw.tween_callback(p.queue_free)


## True for a quick tap anywhere the HUD didn't take: "tap anywhere to continue" (DOCS: Social encounter screen), leaving
## drags and holds to the camera. Call with each unhandled event; `press` is the caller's dictionary.
static func is_scene_tap(event: InputEvent, press: Dictionary) -> bool:
	if not (event is InputEventMouseButton and (event as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT):
		return false
	var mb := event as InputEventMouseButton
	if mb.pressed:
		press.at = mb.position
		press.t = Time.get_ticks_msec()
		return false
	if not press.has("at"):
		return false
	var ok: bool = mb.position.distance_to(press.at) < Rules.TAP_PIXELS and Time.get_ticks_msec() - int(press.t) < Rules.TAP_MS
	press.clear()
	return ok
