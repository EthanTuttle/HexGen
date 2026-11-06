class_name Scrim
extends ColorRect
## The dark wash behind a pop-up. Pop-ups live in SafeArea, which keeps out of the island's strip, but the wash covers the
## whole screen, edge to edge (Ethan's phone note, Nov 5, 2026: it stopped at the insets).


static func make(c: Color) -> Scrim:
	var s := Scrim.new()
	s.color = c
	s.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return s


func _process(_delta: float) -> void:
	global_position = Vector2.ZERO
	size = get_viewport_rect().size


## A full-rect centring box for a pop-up's panel, inside the safe area.
static func centre(child: Control) -> CenterContainer:
	var cc := CenterContainer.new()
	cc.set_anchors_preset(Control.PRESET_FULL_RECT)
	cc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cc.add_child(child)
	return cc
