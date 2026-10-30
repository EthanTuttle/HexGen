class_name UI
extends RefCounted
## Shared look of the screens, taken from the mockups (mockups/exploration/Explore-v8b-Sleeve.dc.html,
## mockups/combat/Combat-v14-AllyTargets.dc.html, mockups/final-screens/AfterCombat.dc.html).
## The UI is laid out in the mockups' own 844 x 390 units (project stretch: canvas_items, base 844 x 390),
## so positions and sizes copy straight from their CSS.

# Colours (mockup CSS)
const INK := Color("#24302C")
const INK_SOFT := Color("#43524D")
const INK_MUTED := Color("#5A5040")
const CREAM := Color("#F6EEDF")
const CREAM_LIGHT := Color("#FCF7EE")
const CREAM_EDGE := Color("#CDB894")
const SAND := Color("#E6DCC8")
const TRAY := Color("#B89C7E")
const TRAY_EDGE := Color("#8F7458")
const RIM := Color("#BFAE8E")
const HEX_SHADOW := Color("#A48A62")
const ORANGE := Color("#B5532F")
const ORANGE_EDGE := Color("#7E3519")
const RED := Color("#8E3B2E")
const RED_EDGE := Color("#5A2A22")
const DARK := Color("#24302C")
const DARK_EDGE := Color("#11181A")
const GREEN := Color("#4E9A5B")
const GOLD := Color("#E4B54C")
const GOLD_EDGE := Color("#A67A1F")
const WHITE_WARM := Color("#FFF8EE")

## Mockup terrain colours, ink and icons (Explore v8b, T). Placeholders in the mockups too.
const TERRAIN := {
	"plains": {"bg": "#A8CF7E", "ink": "#4F7A33"},
	"forest": {"bg": "#5E8F5A", "ink": "#203E1E"},
	"farmland": {"bg": "#DCC562", "ink": "#6E5410"},
	"village": {"bg": "#E6C590", "ink": "#7A4A22"},
	"river": {"bg": "#86BEDB", "ink": "#245A7E"},
	"hills": {"bg": "#BFAE8E", "ink": "#5E4C30"},
	"swamp": {"bg": "#7F9A6E", "ink": "#2E4626"},
	"desert": {"bg": "#EDD49A", "ink": "#8A6A2A"},
	"ruins": {"bg": "#B3ADA4", "ink": "#4E4840"},
	"start": {"bg": "#F3E6C8", "ink": "#9A4A12"},
}

static var _fonts := {}
static var _icons := {}


## "lilita", or "n600" / "n700" / "n800" / "n900" for Nunito at that weight; spacing in px between letters.
static func font(kind: String, spacing := 0) -> Font:
	var key := "%s/%d" % [kind, spacing]
	if _fonts.has(key):
		return _fonts[key]
	var f := FontVariation.new()
	if kind == "lilita":
		f.base_font = load("res://fonts/LilitaOne-Regular.ttf")
	else:
		f.base_font = load("res://fonts/Nunito-Variable.ttf")
		f.variation_opentype = {0x77676874: int(kind.substr(1))}   # "wght"
	f.spacing_glyph = spacing
	_fonts[key] = f
	return f


## A label in the mockup's type; lh is the CSS line-height (Godot's default spacing is much looser).
static func label(text: String, kind: String, size: int, col := INK, spacing := 0, lh := 1.3) -> Label:
	var l := Label.new()
	l.text = text
	var f := font(kind, spacing)
	l.add_theme_font_override("font", f)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	l.add_theme_constant_override("line_spacing", int(roundf(lh * size - f.get_height(size))))
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


## A flat box with rounded corners and a hard bottom edge (the mockups' "box-shadow: 0 Npx 0 colour").
static func box(bg: Color, radius: int, edge := Color(0, 0, 0, 0), edge_px := 0, pad := Vector4(0, 0, 0, 0)) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(radius)
	sb.corner_detail = 8
	sb.anti_aliasing_size = 0.6
	if edge_px > 0:
		sb.shadow_color = edge
		sb.shadow_size = 1
		sb.shadow_offset = Vector2(0, edge_px - 1)
	sb.content_margin_left = pad.x
	sb.content_margin_top = pad.y
	sb.content_margin_right = pad.z
	sb.content_margin_bottom = pad.w
	return sb


static func panel(bg: Color, radius: int, edge: Color, edge_px: int, pad: Vector4) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", box(bg, radius, edge, edge_px, pad))
	p.mouse_filter = Control.MOUSE_FILTER_STOP
	return p


## A stroked 24 x 24 icon from the mockups, as a texture at twice the UI size (the UI is drawn at 2x).
static func icon(name: String, col: Color, size: float, stroke := 2.2, fill := false) -> Texture2D:
	var key := "%s/%s/%s/%s/%s" % [name, col.to_html(), size, stroke, fill]
	if _icons.has(key):
		return _icons[key]
	var d: String = Icons.PATHS.get(name, name)
	var hex := "#" + col.to_html(false)
	var attrs := 'fill="%s"' % hex if fill else 'fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"' % [hex, stroke]
	var svg := '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" %s><path d="%s"/></svg>' % [attrs, d]
	var img := Image.new()
	img.load_svg_from_string(svg, size / 24.0 * 2.0)
	var tex := ImageTexture.create_from_image(img)
	if col.a < 1.0:
		pass
	_icons[key] = tex
	return tex


static func icon_rect(name: String, col: Color, size: float, stroke := 2.2, fill := false) -> TextureRect:
	var t := TextureRect.new()
	t.texture = icon(name, col, size, stroke, fill)
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	t.custom_minimum_size = Vector2(size, size)
	t.size = Vector2(size, size)
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if col.a < 1.0:
		t.modulate.a = col.a
	return t


## Pointy-top hexagon points in a w x h box (CSS: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%)).
## A Button whose hit area is at least a finger (its look stays as drawn).
class FingerButton extends Button:
	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)


## The hit area of a control drawn at `size`: grown to at least a finger (Rules.FINGER) each way, centred, so
## small mockup controls keep their look but are easy to tap (design: everything tappable at least 44 pt).
static func finger_rect(size: Vector2) -> Rect2:
	var s := size.max(Vector2(Rules.FINGER, Rules.FINGER))
	return Rect2((size - s) * 0.5, s)


## Tap check for the HUD's own controls: call with each left-button event; true on a release that is a tap.
## A press that moved past the tap distance is a drag and never presses. On touch (emulated mouse events)
## a press held past the tap time is a long-press, which opens details instead (Gestures).
static func is_tap(c: Control, e: InputEvent) -> bool:
	if not (e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT):
		return false
	var mb := e as InputEventMouseButton
	if mb.pressed:
		c.set_meta("press", [mb.position, Time.get_ticks_msec()])
		return false
	if not c.has_meta("press"):
		return false
	var p: Array = c.get_meta("press")
	c.remove_meta("press")
	if mb.position.distance_to(p[0]) >= Rules.TAP_PIXELS or not c._has_point(mb.position):
		return false
	return mb.device != InputEvent.DEVICE_ID_EMULATION or Time.get_ticks_msec() - int(p[1]) < Rules.TAP_MS


static func hex_points(r: Rect2) -> PackedVector2Array:
	var p := r.position
	var w := r.size.x
	var h := r.size.y
	return PackedVector2Array([p + Vector2(w * 0.5, 0), p + Vector2(w, h * 0.25), p + Vector2(w, h * 0.75),
		p + Vector2(w * 0.5, h), p + Vector2(0, h * 0.75), p + Vector2(0, h * 0.25)])


## A shape with pointed ends (CSS: polygon(12px 0, calc(100% - 12px) 0, 100% 50%, ...)).
static func tag_points(r: Rect2, cut: float) -> PackedVector2Array:
	var p := r.position
	var w := r.size.x
	var h := r.size.y
	return PackedVector2Array([p + Vector2(cut, 0), p + Vector2(w - cut, 0), p + Vector2(w, h * 0.5),
		p + Vector2(w - cut, h), p + Vector2(cut, h), p + Vector2(0, h * 0.5)])


static func terrain_bg(t: String) -> Color:
	return Color(TERRAIN.get(t, TERRAIN.plains).bg)


static func terrain_ink(t: String) -> Color:
	return Color(TERRAIN.get(t, TERRAIN.plains).ink)


## Places a control at a fixed spot in the 844 x 390 layout.
static func at(c: Control, x: float, y: float) -> Control:
	c.position = Vector2(x, y)
	return c
