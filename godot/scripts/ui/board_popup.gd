class_name BoardPopup
extends PanelContainer
## The small details pop-up: long-press on touch, hover with a mouse (design/07 Presentation.md -> Camera and
## controls -> Long-press on the board; items and cards: their tooltip text). A cream card like the mockups'
## pin tags: a title, then short lines. It sits beside the point it describes and stays on screen.

var _title: Label
var _lines: VBoxContainer


func _init() -> void:
	add_theme_stylebox_override("panel", UI.box(UI.CREAM_LIGHT, 10, UI.CREAM_EDGE, 3, Vector4(10, 6, 10, 7)))
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 1)
	_title = UI.label("", "lilita", 13)
	v.add_child(_title)
	_lines = VBoxContainer.new()
	_lines.add_theme_constant_override("separation", 0)
	v.add_child(_lines)
	add_child(v)
	visible = false


## Shows title and lines next to `at` (layout units), above it if there's room.
func show_at(at: Vector2, title: String, lines: Array) -> void:
	_title.text = title
	for c in _lines.get_children():
		c.queue_free()
	for l in lines:
		var lab := UI.label(str(l), "n700", 10, UI.INK_SOFT)
		lab.autowrap_mode = TextServer.AUTOWRAP_OFF
		_lines.add_child(lab)
	visible = true
	reset_size()
	await get_tree().process_frame
	reset_size()
	var screen := get_viewport().get_visible_rect().size
	var p := at + Vector2(14, -size.y - 14)   # up and right of the finger, so the finger doesn't cover it
	if p.y < 6:
		p.y = at.y + 18
	p.x = clampf(p.x, 6, screen.x - size.x - 6)
	p.y = clampf(p.y, 6, screen.y - size.y - 6)
	position = p
