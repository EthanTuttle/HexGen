class_name CameraRig
extends Node3D
## The tilted, rotatable camera of the map and combat screens (design/07 Presentation.md ->
## Camera and controls): mouse drag pans, the wheel zooms, a right-drag rotates and snaps to the
## nearest 60 degree step on release. Keys: Q / E rotate 60 degrees, + / - zoom, F frames.

@export var pitch_deg := 50.0             # tilt; the mockups' camera is about 50 degrees
@export var distance := 60.0
@export var min_distance := 6.0
@export var max_distance := 120.0
@export var lens_mm := 50.0               # Blender's preview camera: 50 mm lens on a 36 mm sensor

var target := Vector3.ZERO
## Where the target sits on screen, in the 844 x 390 UI layout (the mockups centre the action in the open
## area between the panels, not in the middle of the screen).
var focus := Vector2(422, 195)
var yaw_deg := 0.0                        # 0 = looking north, from the south
var home := {}

var camera := Camera3D.new()
var _dragging := false
var _rotating := false
var _tween: Tween


func _ready() -> void:
	camera.keep_aspect = Camera3D.KEEP_WIDTH
	camera.fov = rad_to_deg(2.0 * atan(18.0 / lens_mm))
	camera.near = 0.1
	camera.far = 600.0
	add_child(camera)
	_apply()


func frame(at: Vector3, dist: float, pitch: float, yaw := 0.0) -> void:
	home = {target = at, distance = dist, pitch = pitch, yaw = yaw}
	target = at
	distance = dist
	pitch_deg = pitch
	yaw_deg = yaw
	_apply()


func ease_to(at: Vector3, dist: float, yaw: float) -> void:
	if _tween:
		_tween.kill()
	_tween = create_tween().set_parallel().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_tween.tween_property(self, "target", at, 0.45)
	_tween.tween_property(self, "distance", dist, 0.45)
	_tween.tween_property(self, "yaw_deg", yaw, 0.45)


func _process(_delta: float) -> void:
	_apply()


func _apply() -> void:
	var el := deg_to_rad(pitch_deg)
	var yaw := deg_to_rad(yaw_deg)
	var flat := distance * cos(el)
	camera.position = target + Vector3(-sin(yaw) * flat, distance * sin(el), cos(yaw) * flat)
	camera.look_at(target, Vector3.UP)
	# Shift the view so the target lands on `focus` (pixels of the 844-wide layout -> metres at the target).
	var k := 2.0 * distance * tan(deg_to_rad(camera.fov) * 0.5) / 844.0
	camera.h_offset = (422.0 - focus.x) * k
	camera.v_offset = -(195.0 - focus.y) * k


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			_dragging = mb.pressed
		elif mb.button_index == MOUSE_BUTTON_RIGHT:
			_rotating = mb.pressed
			if not mb.pressed:
				ease_to(target, distance, roundf(yaw_deg / 60.0) * 60.0)
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			_zoom(0.9)
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_zoom(1.0 / 0.9)
	elif event is InputEventMouseMotion:
		var mm := event as InputEventMouseMotion
		if _dragging:
			var scale := distance * 0.0012
			var yaw := deg_to_rad(yaw_deg)
			var right := Vector3(cos(yaw), 0, sin(yaw))
			var forward := Vector3(sin(yaw), 0, -cos(yaw))
			target -= right * mm.relative.x * scale - forward * mm.relative.y * scale
		elif _rotating:
			yaw_deg -= mm.relative.x * 0.3
	elif event is InputEventMagnifyGesture:
		_zoom(1.0 / (event as InputEventMagnifyGesture).factor)
	elif event is InputEventPanGesture:
		_zoom(1.0 + (event as InputEventPanGesture).delta.y * 0.05)
	elif event is InputEventKey and event.pressed and not event.echo:
		match (event as InputEventKey).keycode:
			KEY_Q:
				ease_to(target, distance, roundf(yaw_deg / 60.0) * 60.0 + 60.0)
			KEY_E:
				ease_to(target, distance, roundf(yaw_deg / 60.0) * 60.0 - 60.0)
			KEY_EQUAL, KEY_KP_ADD:
				_zoom(0.8)
			KEY_MINUS, KEY_KP_SUBTRACT:
				_zoom(1.25)
			KEY_F:
				if not home.is_empty():
					ease_to(home.target, home.distance, roundf(yaw_deg / 60.0) * 60.0)


func _zoom(f: float) -> void:
	distance = clampf(distance * f, min_distance, max_distance)
