class_name TagButton
extends Control
## The mockups' main action button: a bar with pointed ends (Fight, Flip coins, End phase, Level up now),
## with an optional coin dot before the label.

signal pressed

var bg := UI.ORANGE
var ink := UI.WHITE_WARM
var shadow := UI.ORANGE_EDGE
var text := ""
var text_size := 15
var cut := 12.0
var coin := false
var icon: Texture2D             # optional icon before the label (e.g. the pencil on Edit hotbar)
var disabled := false:
	set(v):
		disabled = v
		queue_redraw()


static func make(t: String, w: float, h: float, sz := 15, with_coin := false) -> TagButton:
	var b := TagButton.new()
	b.text = t
	b.custom_minimum_size = Vector2(w, h)
	b.size = Vector2(w, h)
	b.text_size = sz
	b.coin = with_coin
	b.mouse_filter = Control.MOUSE_FILTER_STOP
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	return b


func _draw() -> void:
	var r := Rect2(Vector2.ZERO, size)
	var b := Color("#E6DCC8") if disabled else bg
	var k := Color("#6B6152") if disabled else ink
	if not disabled and shadow.a > 0:
		draw_colored_polygon(UI.tag_points(Rect2(Vector2(0, 4), size), cut), shadow)
	draw_colored_polygon(UI.tag_points(r, cut), b)
	var f := UI.font("lilita")
	var ts := f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, text_size)
	var w := ts.x + (26.0 if coin else 0.0) + (22.0 if icon else 0.0)
	var x := (size.x - w) * 0.5
	var asc := f.get_ascent(text_size)
	var y := (size.y - (asc + f.get_descent(text_size))) * 0.5 + asc
	if coin:
		var c := Vector2(x + 9, size.y * 0.5)
		draw_circle(c, 9, UI.GOLD_EDGE)
		draw_circle(c - Vector2(0, 1), 8, UI.GOLD)
		x += 26
	if icon:
		draw_texture_rect(icon, Rect2(Vector2(x, size.y * 0.5 - 8), Vector2(16, 16)), false)
		x += 22
	draw_string(f, Vector2(x, y), text, HORIZONTAL_ALIGNMENT_LEFT, -1, text_size, k)


func _gui_input(event: InputEvent) -> void:
	if UI.is_tap(self, event) and not disabled:
		pressed.emit()
		accept_event()


func _has_point(point: Vector2) -> bool:
	return UI.finger_rect(size).has_point(point)
