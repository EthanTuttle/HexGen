class_name HexShape
extends Control
## A pointy-top hex as the mockups draw them: an optional drop shadow, a rim, a face inset inside it,
## and a centred letter or icon. Emits pressed when clicked (if clickable).

signal pressed

@export var rim := UI.RIM
@export var face := UI.CREAM
@export var inset := 3.0
@export var shadow := Color(0, 0, 0, 0)
@export var shadow_y := 3.0
@export var text := ""
@export var text_size := 16
@export var text_color := Color("#22262E")
@export var text_font := "lilita"
var icon: Texture2D
var icon_size := 18.0
var icon_alpha := 1.0
var clickable := false:
	set(v):
		clickable = v
		mouse_filter = Control.MOUSE_FILTER_STOP if v else Control.MOUSE_FILTER_IGNORE
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND if v else Control.CURSOR_ARROW


static func make(w: float, h: float, rim_c: Color, face_c: Color, ins := 3.0) -> HexShape:
	var s := HexShape.new()
	s.custom_minimum_size = Vector2(w, h)
	s.size = Vector2(w, h)
	s.rim = rim_c
	s.face = face_c
	s.inset = ins
	s.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return s


func with_text(t: String, sz: int, col := Color("#22262E"), f := "lilita") -> HexShape:
	text = t
	text_size = sz
	text_color = col
	text_font = f
	queue_redraw()
	return self


func with_icon(name: String, col: Color, sz: float, stroke := 2.2, fill := false) -> HexShape:
	icon = UI.icon(name, Color(col, 1.0), sz, stroke, fill)
	icon_size = sz
	icon_alpha = col.a
	queue_redraw()
	return self


func with_shadow(col: Color, y := 3.0) -> HexShape:
	shadow = col
	shadow_y = y
	queue_redraw()
	return self


func _draw() -> void:
	var r := Rect2(Vector2.ZERO, size)
	if shadow.a > 0:
		draw_colored_polygon(UI.hex_points(Rect2(Vector2(0, shadow_y), size)), shadow)
	draw_colored_polygon(UI.hex_points(r), rim)
	if inset > 0:
		draw_colored_polygon(UI.hex_points(r.grow(-inset)), face)
	if icon:
		var s := Vector2(icon_size, icon_size)
		draw_texture_rect(icon, Rect2((size - s) * 0.5, s), false, Color(1, 1, 1, icon_alpha))
	if text != "":
		var f := UI.font(text_font)
		var ts := f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, text_size)
		var asc := f.get_ascent(text_size)
		var desc := f.get_descent(text_size)
		draw_string(f, Vector2((size.x - ts.x) * 0.5, (size.y - (asc + desc)) * 0.5 + asc), text,
				HORIZONTAL_ALIGNMENT_LEFT, -1, text_size, text_color)


func _gui_input(event: InputEvent) -> void:
	if clickable and UI.is_tap(self, event):
		pressed.emit()
		accept_event()


func _has_point(point: Vector2) -> bool:
	return UI.finger_rect(size).has_point(point) if clickable else Rect2(Vector2.ZERO, size).has_point(point)
