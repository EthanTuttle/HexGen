class_name StatusChip
extends Control
## One status chip on a unit's marker, drawn as sharp UI (07 -> Combat; Ethan, Nov 7, 2026: the icons floating on the
## minis looked fuzzy). The glyph is rasterised at the screen's real pixel size, so it isn't stretched. A round cream chip
## in a row beside the letter hex (CombatHud.fill_status). PLACEHOLDER glyphs and chip colours.

var glyph: Texture2D
var glyph_size := 9.0
var more := ""      # "+N" in place of a glyph
var ring := UI.DARK  # a modifier's chip: green for a buff, red for a penalty (07 -> Modifier coins)


## A chip `d` across showing `icon` (a status_icons name) in `ink`, or "+extra" when extra > 0.
static func make(d: float, icon: String, ink: Color, extra := 0, ring_col := UI.DARK) -> StatusChip:
	var c := StatusChip.new()
	c.ring = ring_col
	c.custom_minimum_size = Vector2(d, d)
	c.size = Vector2(d, d)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.glyph_size = roundf(d * 0.72)
	if extra > 0:
		c.more = "+%d" % extra
	else:
		c.glyph = UI.icon(CombatHud.status_path(icon), ink, c.glyph_size * _screen_scale() * 0.5, 2.6)
	return c


## Physical pixels per UI unit (the phone draws the 844 x 390 layout about 3x).
static func _screen_scale() -> float:
	var root := Engine.get_main_loop() as SceneTree
	if root == null:
		return 1.0
	return maxf(root.root.get_final_transform().get_scale().x, 1.0)


func _draw() -> void:
	draw_circle(size * 0.5, size.x * 0.5, ring, true, -1.0, true)
	draw_circle(size * 0.5, size.x * 0.5 - (1.0 if ring == UI.DARK else 1.6), UI.CREAM, true, -1.0, true)   # a modifier's coloured ring a touch wider
	if more != "":
		var f := UI.font("n900")
		var fs := int(size.x * 0.62)
		var ts := f.get_string_size(more, HORIZONTAL_ALIGNMENT_LEFT, -1, fs)
		var asc := f.get_ascent(fs)
		draw_string(f, Vector2((size.x - ts.x) * 0.5, (size.y - (asc + f.get_descent(fs))) * 0.5 + asc), more,
				HORIZONTAL_ALIGNMENT_LEFT, -1, fs, UI.INK)
	elif glyph:
		var s := Vector2(glyph_size, glyph_size)
		draw_texture_rect(glyph, Rect2((size - s) * 0.5, s), false)
