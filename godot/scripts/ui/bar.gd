class_name Bar
extends Control
## A thin HP or XP bar: a track and a fill, with rounded ends.

var track := Color("#E6DCC8")
var fill := UI.GREEN
var value := 1.0:
	set(v):
		value = clampf(v, 0.0, 1.0)
		queue_redraw()
var outline := Color(0, 0, 0, 0)


static func make(w: float, h: float, tr: Color, fl: Color, v := 1.0, ol := Color(0, 0, 0, 0)) -> Bar:
	var b := Bar.new()
	b.custom_minimum_size = Vector2(w, h)
	b.size = Vector2(w, h)
	b.track = tr
	b.fill = fl
	b.value = v
	b.outline = ol
	b.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return b


func _draw() -> void:
	var rad := int(size.y * 0.5)
	draw_style_box(_rounded(track, rad), Rect2(Vector2.ZERO, size))
	if value > 0:
		draw_style_box(_rounded(fill, rad), Rect2(Vector2.ZERO, Vector2(maxf(size.x * value, size.y), size.y)))
	if outline.a > 0:
		var sb := _rounded(Color(0, 0, 0, 0), rad)
		sb.border_color = outline
		sb.set_border_width_all(1)
		draw_style_box(sb, Rect2(Vector2.ZERO, size))


static func _rounded(c: Color, r: int) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = c
	sb.set_corner_radius_all(r)
	return sb
