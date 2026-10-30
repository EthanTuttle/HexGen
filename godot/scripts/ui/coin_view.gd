class_name CoinView
extends Control
## A flipped coin as in the mockups: gold with "H" for heads, grey with "T" for tails.

var heads := true
var diameter := 34.0


static func make(h: bool, d := 34.0) -> CoinView:
	var c := CoinView.new()
	c.heads = h
	c.diameter = d
	c.custom_minimum_size = Vector2(d, d)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c


func _draw() -> void:
	var r := diameter * 0.5
	var ctr := Vector2(r, r)
	var bg := UI.GOLD if heads else Color("#CFC2A8")
	var edge := UI.GOLD_EDGE if heads else Color("#8A7D66")
	var ink := Color("#5A3A05") if heads else Color("#4A4034")
	draw_circle(ctr, r, edge)
	draw_circle(ctr - Vector2(0, 1.5), r - 1.5, bg)
	var f := UI.font("lilita")
	var sz := int(diameter * 0.44)
	var t := "H" if heads else "T"
	var ts := f.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, sz)
	var asc := f.get_ascent(sz)
	draw_string(f, Vector2(r - ts.x * 0.5, r - (asc + f.get_descent(sz)) * 0.5 + asc - 1), t, HORIZONTAL_ALIGNMENT_LEFT, -1, sz, ink)
