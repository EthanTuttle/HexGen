class_name Gestures
extends Node
## Turns board input into gestures (design/07 Presentation.md -> Camera and controls): a tap (barely moves,
## lets go quickly) picks, moving further makes a drag (pans), holding still is a long-press (details),
## two fingers pinch to zoom and twist to rotate. Touch is read straight from InputEventScreenTouch /
## InputEventScreenDrag. The left mouse button is the same single pointer, so mouse play is unchanged.
##
## Godot also turns each touch into an emulated mouse event (device -1). That emulation stays on because the
## HUD's controls need it, but the board ignores the emulated copies, so nothing fires twice. Touches over the
## HUD never get here: its controls take them first.
##
## It also gives HUD controls long-press details on touch: a still hold on a control with tooltip text opens
## that text in a pop-up (what hover shows on PC), and the release doesn't press the control.

signal tap(pos: Vector2)
signal long_press(pos: Vector2)
signal hover(pos: Vector2)              # mouse only: the pointer rests here (PC's long-press)
signal hover_end
signal drag(relative: Vector2)          # one pointer moving, past the tap distance
signal pinch(factor: float)             # two fingers: < 1 closer (zoom in), > 1 apart
signal twist(radians: float)            # two fingers: change in angle, anticlockwise on screen positive
signal twist_end                        # two-finger gesture over: snap the rotation
signal gui_long_press(control: Control, pos: Vector2)

const MOUSE := -100                     # pointer id of the left mouse button

var touch_from_mouse := false           # `--touch`: the mouse plays as a finger (Godot's touch emulation)

var _points := {}                       # pointer id -> position
var _start := Vector2.ZERO
var _start_ms := 0
var _state := ""                        # "", "pending", "drag", "held", "multi"
var _pair_dist := 0.0
var _pair_angle := 0.0
var _hover_pos := Vector2.INF
var _hover_ms := 0
var _hover_fired := false
var _gui_press := {}                    # a still press on a HUD control: {control, pos, ms, fired}


func _ready() -> void:
	touch_from_mouse = "--touch" in OS.get_cmdline_user_args()
	if touch_from_mouse:
		Input.emulate_touch_from_mouse = true


func _real_mouse(e: InputEvent) -> bool:
	return e.device != InputEvent.DEVICE_ID_EMULATION and not touch_from_mouse


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventScreenTouch:
		var t := e as InputEventScreenTouch
		if t.pressed:
			_down(t.index, t.position)
		else:
			_up(t.index, t.position)
	elif e is InputEventScreenDrag:
		var d := e as InputEventScreenDrag
		_move(d.index, d.position, d.relative)
	elif e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT and _real_mouse(e):
		if e.pressed:
			_down(MOUSE, e.position)
		else:
			_up(MOUSE, e.position)
	elif e is InputEventMouseMotion and _real_mouse(e):
		var m := e as InputEventMouseMotion
		if _points.has(MOUSE):
			_move(MOUSE, m.position, m.relative)
		elif m.button_mask == 0:
			_rest(m.position)


func _down(id: int, pos: Vector2) -> void:
	_points[id] = pos
	_end_hover()
	if _points.size() == 1:
		_state = "pending"
		_start = pos
		_start_ms = Time.get_ticks_msec()
	elif _points.size() == 2:
		# A second finger cancels any tap, hold or pan: from here it's a pinch and twist.
		_state = "multi"
		_pair_dist = _pair()[0]
		_pair_angle = _pair()[1]


func _up(id: int, pos: Vector2) -> void:
	if not _points.has(id):
		return
	_points.erase(id)
	if _state == "multi":
		if _points.size() < 2:
			twist_end.emit()
		if _points.is_empty():
			_state = ""
		else:
			_state = "spent"   # the finger left behind neither taps nor pans until all are up
		return
	if _points.is_empty():
		if _state == "pending" and Time.get_ticks_msec() - _start_ms < Rules.TAP_MS and pos.distance_to(_start) < Rules.TAP_PIXELS:
			tap.emit(pos)
		_state = ""


func _move(id: int, pos: Vector2, relative: Vector2) -> void:
	if not _points.has(id):
		return
	_points[id] = pos
	match _state:
		"pending", "held":
			if pos.distance_to(_start) >= Rules.TAP_PIXELS:
				_state = "drag"
				drag.emit(pos - _start)   # catch up with the distance moved before it became a drag
		"drag":
			drag.emit(relative)
		"multi":
			if _points.size() >= 2:
				var p := _pair()
				if _pair_dist > 1.0 and p[0] > 1.0:
					pinch.emit(p[0] / _pair_dist)
				twist.emit(wrapf(p[1] - _pair_angle, -PI, PI))
				_pair_dist = p[0]
				_pair_angle = p[1]


## [distance, angle] between the first two pointers.
func _pair() -> Array:
	var ps: Array = _points.values()
	var a: Vector2 = ps[0]
	var b: Vector2 = ps[1]
	return [a.distance_to(b), (b - a).angle()]


func _rest(pos: Vector2) -> void:
	if _hover_pos.distance_to(pos) >= Rules.TAP_PIXELS:
		if _hover_fired:
			hover_end.emit()
		_hover_pos = pos
		_hover_ms = Time.get_ticks_msec()
		_hover_fired = false


func _end_hover() -> void:
	if _hover_fired:
		hover_end.emit()
	_hover_fired = false
	_hover_pos = Vector2.INF


func _process(_delta: float) -> void:
	var now := Time.get_ticks_msec()
	# A still press past the tap time is a long-press (the docs give one time, 350 ms: a press held still
	# past it can no longer be a tap, so it opens details right then).
	if _state == "pending" and now - _start_ms >= Rules.TAP_MS:
		_state = "held"
		long_press.emit(_start)
	if _hover_pos != Vector2.INF and not _hover_fired and now - _hover_ms >= Rules.TAP_MS:
		_hover_fired = true
		hover.emit(_hover_pos)
	if not _gui_press.is_empty() and not _gui_press.fired and now - _gui_press.ms >= Rules.TAP_MS:
		_gui_press.fired = true
		gui_long_press.emit(_gui_press.control, _gui_press.pos)


# --- Long-press on HUD controls (touch) --------------------------------------------

func _input(e: InputEvent) -> void:
	# Godot sends each touch's emulated mouse event first, then the touch itself.
	if e is InputEventScreenTouch:
		var t := e as InputEventScreenTouch
		if t.pressed and t.index == 0:
			var c := _control_at(t.position)
			_gui_press = {} if c == null else {control = c, pos = t.position, ms = Time.get_ticks_msec(), fired = false}
		elif not t.pressed:
			if not _gui_press.is_empty() and _gui_press.fired:
				get_viewport().set_input_as_handled()
			_gui_press = {}
	elif e is InputEventScreenDrag and not _gui_press.is_empty():
		if (e as InputEventScreenDrag).position.distance_to(_gui_press.pos) >= Rules.TAP_PIXELS:
			_gui_press = {}
	elif e is InputEventMouseButton and e.device == InputEvent.DEVICE_ID_EMULATION and not e.pressed:
		if not _gui_press.is_empty() and _gui_press.fired:
			get_viewport().set_input_as_handled()   # the hold opened details: the release presses nothing


## The HUD control under a point that has details to show (its tooltip text), if any; the last drawn wins.
func _control_at(pos: Vector2) -> Control:
	var best: Control = null
	for n in get_tree().root.find_children("*", "Control", true, false):
		var c := n as Control
		if c.tooltip_text != "" and c.mouse_filter != Control.MOUSE_FILTER_IGNORE and c.is_visible_in_tree() \
				and c.get_global_rect().has_point(pos):
			best = c
	return best
