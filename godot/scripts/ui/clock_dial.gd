class_name ClockDial
extends Control
## The day clock's sun/moon dial (Explore v8b): a day disc with a dark night slice and a marker on a hand.

var minute := 14.0        # minutes into the 30-minute day
var day_minutes := 30.0
var night_at := 20.0
var night := false


func _ready() -> void:
	custom_minimum_size = Vector2(46, 46)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _draw() -> void:
	var c := Vector2(23, 23)
	draw_circle(c, 22, Color("#F2D88A"))
	var a0 := night_at / day_minutes * TAU
	var pts := PackedVector2Array([c])
	for k in 33:
		var a := lerpf(a0, TAU, k / 32.0)
		pts.append(c + Vector2(sin(a), -cos(a)) * 22)
	draw_colored_polygon(pts, Color("#3E4A78"))
	draw_arc(c, 21, 0, TAU, 48, Color("#A48A62"), 2, true)
	var deg := minute / day_minutes * TAU
	var dir := Vector2(sin(deg), -cos(deg))
	draw_line(c, c + dir * 13, UI.INK, 2.4, true)
	var m := c + dir * 15
	draw_circle(m, 6.8, UI.INK)
	draw_circle(m, 5.2, Color("#DDE3F2") if night else Color("#F7C948"))
	draw_circle(c, 2.6, UI.INK)
