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


## A party portrait's details (DOCS: Touch controls -> Long-press on HUD controls): the character's effects
## (injuries, buffs, conditions) with what each does, one per line under their name; "" when they have none,
## so nothing opens. `fx` holds [name, what it does] pairs.
static func effects_tip(who: String, fx: Array) -> String:
	if fx.is_empty():
		return ""
	return who + "\n" + "\n".join(fx.map(func(e): return "%s: %s" % [e[0], e[1]]))


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
	var inside: bool = c._has_point(mb.position) if c.has_method("_has_point") else Rect2(Vector2.ZERO, c.size).has_point(mb.position)
	if mb.position.distance_to(p[0]) >= Rules.TAP_PIXELS or not inside:
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


## The same, for a panel on the right of the mockup: it keeps its distance from the right edge, so it moves in
## with the safe area (SafeArea) and with screens wider than 844.
static func at_right(c: Control, x: float, y: float) -> Control:
	var w := maxf(c.size.x, c.custom_minimum_size.x)
	c.anchor_left = 1.0
	c.anchor_right = 1.0
	c.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	c.offset_left = x - 844.0
	c.offset_right = x - 844.0 + w
	c.offset_top = y
	return c


## The same, for a piece along the bottom of the mockup: it keeps its distance from the bottom edge, so on a taller
## screen it stays at the bottom and the board gets the extra height (design/07 -> UI -> Screen sizes).
static func at_bottom(c: Control, x: float, y: float) -> Control:
	var h := maxf(c.size.y, c.custom_minimum_size.y)
	c.anchor_top = 1.0
	c.anchor_bottom = 1.0
	c.grow_vertical = Control.GROW_DIRECTION_BEGIN
	c.offset_left = x
	c.offset_top = y - 390.0
	c.offset_bottom = y - 390.0 + h
	return c


## DOCS (design/07 -> UI -> Screen sizes; the number is a placeholder there): a full-screen menu grows with the extra
## room up to this many times the mockup's 844 x 390 each way, then stops and sits centred.
const MENU_CAP := 1.25


## Where a full-screen menu goes in an area of this size: the whole area up to the cap, centred past it.
static func menu_frame(area: Vector2) -> Rect2:
	var s := area.min(Vector2(844.0, 390.0) * MENU_CAP)
	return Rect2(((area - s) * 0.5).floor(), s)


## Window pixels per layout unit: 2 on the phone, about 3.6 full screen on the Mac.
static func screen_scale() -> float:
	var tree := Engine.get_main_loop() as SceneTree
	if tree == null:
		return 1.0
	return maxf(tree.root.get_final_transform().get_scale().x, 1.0)


## An icon drawn into a fixed rect (draw_texture_rect), made at the screen's own density so it stays sharp on a
## bigger screen. Not for a Button's icon, which shows at the texture's own size.
static func sharp_icon(name: String, col: Color, size: float, stroke := 2.2, fill := false) -> Texture2D:
	return icon(name, col, size * screen_scale() * 0.5, stroke, fill)


## The action card's face (Combat v14 hotbar card; also the action cards screen, the map's Rest and Enter cards and
## level-up's card tiles): a cream card with a rim and its source's colour band across the top. The band follows the
## card's rounded top corners, so it sits right at any screen size (a plain rectangle shows its square corners
## inside the curve once the UI is drawn bigger than 2x, as on the Mac). band_bottom: where the band ends, from the
## card's top edge; a clear band draws none.
static func card_face(ci: CanvasItem, r: Rect2, rim: Color, rim_w: int, band: Color, band_bottom := 8.5, radius := 10, bg := CREAM_LIGHT) -> void:
	ci.draw_style_box(box(bg, radius), r)
	if band.a > 0.0:
		ci.draw_colored_polygon(_top_band(r.grow(-1.0), radius - 1.0, band_bottom - 1.0), band)
	var edge := box(bg, radius)
	edge.draw_center = false
	edge.set_border_width_all(rim_w)
	edge.border_color = rim
	ci.draw_style_box(edge, r)


## The top strip of a rounded rect, h tall, with its two top corners rounded by rad (drawn under the rim, which
## covers its outer edge).
static func _top_band(r: Rect2, rad: float, h: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	var rr := minf(rad, r.size.x * 0.5)
	var steps := 8
	for i in steps + 1:   # top left corner, from the left side round to the top
		var a := PI + PI * 0.5 * i / steps
		pts.append(r.position + Vector2(rr, rr) + Vector2(cos(a), sin(a)) * rr)
	for i in steps + 1:   # top right corner
		var a := PI * 1.5 + PI * 0.5 * i / steps
		pts.append(Vector2(r.end.x - rr, r.position.y + rr) + Vector2(cos(a), sin(a)) * rr)
	var bottom := r.position.y + h
	if bottom < r.position.y + rr:   # a band shallower than the corner: cut the arcs at its bottom
		pts = Geometry2D.intersect_polygons(pts + PackedVector2Array([r.end, Vector2(r.position.x, r.end.y)]),
			PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), Vector2(r.end.x, bottom), Vector2(r.position.x, bottom)]))[0]
		return pts
	pts.append(Vector2(r.end.x, bottom))
	pts.append(Vector2(r.position.x, bottom))
	return pts
