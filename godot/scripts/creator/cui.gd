class_name CUI
extends RefCounted
## Small pieces the creator's steps share, in Creator v22b's CSS. The mockup's 9.5-10.5 px text is 11 here (DOCS: 11 pt
## is the smallest text on phones).

const SEL_RIM := Color("#B5532F")
const FOCUS_RIM := Color("#4A86C8")
const SOFT_INK := Color("#43524D")
const CAP_INK := Color("#5A6862")
const PANEL_LINE := Color("#E2D5BC")
const TICK := "M5 12l5 5 9-10"


## .big: Back, Next, Begin.
static func big(text: String, primary: bool, pad := 24.0) -> TagButton:
	var f := UI.font("lilita")
	var b := TagButton.make(text, f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 16).x + pad * 2.0, 40, 16)
	b.cut = 13.0
	b.accessibility_name = text
	if primary:
		b.ink = UI.WHITE_WARM
	else:
		b.bg = UI.CREAM_LIGHT
		b.ink = Color("#33403B")
		b.shadow = UI.HEX_SHADOW
	return b


## .pill: Build and Pronouns.
static func pill(text: String, sel: bool) -> TagButton:
	var f := UI.font("n800")
	var b := TagButton.make(text, f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x + 22.0, 28, 12)
	b.font_kind = "n800"
	b.cut = 9.0
	b.drop = 3.0
	b.accessibility_name = text
	b.bg = SEL_RIM if sel else UI.CREAM_LIGHT
	b.ink = UI.WHITE_WARM if sel else Color("#33403B")
	b.shadow = UI.ORANGE_EDGE if sel else UI.RIM
	return b


static func choose_button(text: String, w: float) -> TagButton:
	var b := TagButton.make(text, w, 34, 15)
	b.cut = 10.0
	b.drop = 3.0
	b.ink = UI.WHITE_WARM
	b.accessibility_name = text
	return b


static func cap(text: String, col := CAP_INK) -> Label:
	return UI.label(text.to_upper(), "n900", 11, col, 1)


static func hbox(sep := 8) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", sep)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return h


static func vbox(sep := 6) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", sep)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return v


static func wrap(l: Label, w: float) -> Label:
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = w
	return l


static func spring() -> Control:
	var c := Control.new()
	c.size_flags_vertical = Control.SIZE_EXPAND_FILL
	c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c


## The orange to-do dot, or the green tick when done (from level-up).
static func mark(done: bool) -> Control:
	return Dot.make(16, Color("#3E8E4E") if done else Color("#E07A2E"), TICK if done else "", 10)


## A hex a player taps, with the drop shadow and the gold glow on the picked one.
static func hex(w: float, h: float, rim: Color, inset: float, icon: String, ink: Color, icon_size: float, face := UI.CREAM_LIGHT, glow := false, stroke := 2.2) -> HexGlow:
	var s := HexGlow.new()
	s.custom_minimum_size = Vector2(w, h)
	s.size = Vector2(w, h)
	s.rim = rim
	s.face = face
	s.inset = inset
	s.mouse_filter = Control.MOUSE_FILTER_IGNORE
	s.glowing = glow
	if icon != "":
		s.with_icon(icon, ink, icon_size, stroke)
	return s


## A hex with CSS's "drop-shadow(0 0 10px #FFE9A8)" when picked.
class HexGlow extends HexShape:
	var glowing := false
	func _draw() -> void:
		if glowing:
			for i in 5:
				var g := 2.0 + i * 2.0
				draw_colored_polygon(UI.hex_points(Rect2(Vector2.ZERO, size).grow(g)), Color(1.0, 0.91, 0.66, 0.14))
		super()


## A small round badge with an icon.
class Dot extends Control:
	var col := Color.WHITE
	var icon: Texture2D
	var icon_px := 10.0

	static func make(px: float, c: Color, path: String, ipx: float) -> Dot:
		var d := Dot.new()
		d.custom_minimum_size = Vector2(px, px)
		d.size = Vector2(px, px)
		d.col = c
		d.icon_px = ipx
		d.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		d.mouse_filter = Control.MOUSE_FILTER_IGNORE
		if path != "":
			d.icon = UI.icon(path, UI.WHITE_WARM, ipx, 4.0)
		return d

	func _draw() -> void:
		draw_circle(size * 0.5, size.x * 0.5, col)
		if icon:
			draw_texture_rect(icon, Rect2((size - Vector2(icon_px, icon_px)) * 0.5, Vector2(icon_px, icon_px)), false)


## An invisible tap area over whatever sits under it, with a finger-sized hit area and an optional drawn look.
class Tap extends Control:
	signal pressed
	func _init(what := "") -> void:
		accessibility_name = what
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		mouse_filter = Control.MOUSE_FILTER_PASS

	func _gui_input(event: InputEvent) -> void:
		if UI.is_tap(self, event):
			pressed.emit()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)


## A column: tappable, sized by what's in it (the mockups' `.hb` hex with a label under it).
static func tap_column(what: String, children: Array, sep := 3) -> Tap:
	var t := Tap.new(what)
	var v := vbox(sep)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	for c: Control in children:
		c.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		v.add_child(c)
	t.add_child(v)
	v.resized.connect(func(): t.custom_minimum_size = v.size)
	t.custom_minimum_size = v.get_combined_minimum_size()
	return t


## Cream panel with the hard edge.
static func panel(pad: Vector4) -> PanelContainer:
	return UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, pad)


## #FCF7EE with CSS's "inset 0 0 0 2.5px" line, or a heavier coloured border.
static func tile_box(border: Color, px := 2.5, radius := 12, pad := Vector4(10, 7, 10, 7), bg := UI.CREAM_LIGHT) -> StyleBoxFlat:
	var sb := UI.box(bg, radius, Color(0, 0, 0, 0), 0, pad)
	sb.set_border_width_all(int(ceilf(px)))
	sb.border_color = border
	return sb


static func shade(c: Color, f: float) -> Color:
	return Color(minf(c.r * f, 1.0), minf(c.g * f, 1.0), minf(c.b * f, 1.0), c.a)


## Fades and rises a step's parts in (CSS: reveal).
## How far a view's list is scrolled (its first ScrollContainer), to keep across a rebuild.
static func scroll_of(view: Node) -> int:
	var found := view.find_children("*", "ScrollContainer", true, false)
	return (found[0] as ScrollContainer).scroll_vertical if not found.is_empty() else 0


## Puts a rebuilt view's list back where it was, once its new rows are laid out (they are by the end of this frame).
static func keep_scroll(view: Node, y: int) -> void:
	if y <= 0:
		return
	var found := view.find_children("*", "ScrollContainer", true, false)
	if found.is_empty():
		return
	var s: ScrollContainer = found[0]
	s.set_deferred("scroll_vertical", y)


static func reveal(c: Control, seconds := 0.3) -> void:
	c.modulate.a = 0.0
	var tw := c.create_tween()
	tw.tween_property(c, "modulate:a", 1.0, seconds).set_ease(Tween.EASE_OUT)
