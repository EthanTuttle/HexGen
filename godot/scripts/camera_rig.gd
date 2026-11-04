class_name CameraRig
extends Node3D
## The tilted, rotatable camera of the map and combat screens (design/07 Presentation.md ->
## Camera and controls): one finger or a mouse drag pans, two fingers pinch to zoom and twist to rotate, the
## wheel zooms, a right-drag rotates. Rotation is free, with no snapping (DOCS, Oct 30, 2026).
## Keys: Q / E rotate by Rules.ROTATE_STEP, + / - zoom, F frames.
## Any pan, zoom or rotate by the player sets `player_moved` (the player's camera wins: following the
## party or centring on whoever acts stops until the game clears it).

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
var floor_at := Callable()                # plan point -> how high the camera must stay there (raised regions)
var shake := 0.0                          # metres: a region rising (PLACEHOLDER look)
var _floor_lift := 0.0

signal player_moved_camera

var camera := Camera3D.new()
var gestures := Gestures.new()
var player_moved := false
var _rotating := false
var _tween: Tween


func _ready() -> void:
	camera.keep_aspect = Camera3D.KEEP_WIDTH
	camera.fov = rad_to_deg(2.0 * atan(18.0 / lens_mm))
	camera.near = 0.1
	camera.far = 600.0
	add_child(camera)
	add_child(gestures)
	gestures.drag.connect(_pan)
	gestures.pinch.connect(func(f: float): _zoom(1.0 / f); _player())
	gestures.twist.connect(func(a: float):
		yaw_deg -= rad_to_deg(a)   # the board turns with the fingers (screen angles run clockwise; a higher yaw turns the board anticlockwise)
		_player())
	_apply()


func _player() -> void:
	if _tween and _tween.is_running():
		_tween.kill()   # the player's move wins over any easing in progress
	if not player_moved:
		player_moved = true
		player_moved_camera.emit()


## A drag on the board pans it, so the ground under the pointer follows it.
func _pan(relative: Vector2) -> void:
	var k := 2.0 * distance * tan(deg_to_rad(camera.fov) * 0.5) / 844.0   # metres per layout unit at the target
	var yaw := deg_to_rad(yaw_deg)
	var right := Vector3(cos(yaw), 0, sin(yaw))
	var forward := Vector3(sin(yaw), 0, -cos(yaw))
	target -= right * relative.x * k - forward * relative.y * k / sin(deg_to_rad(pitch_deg))
	_player()


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


## A timed move, to wait on (a fight's zoom into its hex).
func fly_to(at: Vector3, dist: float, seconds: float) -> void:
	if _tween:
		_tween.kill()
	_tween = create_tween().set_parallel().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	_tween.tween_property(self, "target", at, seconds)
	_tween.tween_property(self, "distance", dist, seconds)
	await _tween.finished


func _process(delta: float) -> void:
	_lift_over_floor(delta)
	_apply()


func _apply() -> void:
	var el := deg_to_rad(pitch_deg)
	var yaw := deg_to_rad(yaw_deg)
	var flat := distance * cos(el)
	camera.position = target + Vector3(-sin(yaw) * flat, distance * sin(el) + _floor_lift, cos(yaw) * flat)
	camera.look_at(target, Vector3.UP)
	# Shift the view so the target lands on `focus` (pixels of the 844-wide layout -> metres at the target).
	var k := 2.0 * distance * tan(deg_to_rad(camera.fov) * 0.5) / 844.0
	camera.h_offset = (422.0 - focus.x) * k
	camera.v_offset = -(195.0 - focus.y) * k
	if shake > 0.0:
		camera.h_offset += randf_range(-shake, shake)
		camera.v_offset += randf_range(-shake, shake)


## Close in over raised ground, the camera glides up rather than going through a mountain.
func _lift_over_floor(delta: float) -> void:
	if not floor_at.is_valid():
		return
	var el := deg_to_rad(pitch_deg)
	var yaw := deg_to_rad(yaw_deg)
	var flat := distance * cos(el)
	var at := Vector2(target.x - sin(yaw) * flat, -(target.z + cos(yaw) * flat))
	var least: float = floor_at.call(at) + Rules.CAMERA_CLEAR
	var want := 0.0 if least <= Rules.CAMERA_CLEAR else maxf(0.0, least - (target.y + distance * sin(el)))
	_floor_lift = move_toward(_floor_lift, want, delta * 12.0)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_RIGHT:
			_rotating = mb.pressed
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			_zoom(0.9)
			_player()
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_zoom(1.0 / 0.9)
			_player()
	elif event is InputEventMouseMotion:
		var mm := event as InputEventMouseMotion
		if _rotating:
			yaw_deg -= mm.relative.x * 0.3
			_player()
	elif event is InputEventMagnifyGesture:
		_zoom(1.0 / (event as InputEventMagnifyGesture).factor)
		_player()
	elif event is InputEventPanGesture:
		_zoom(1.0 + (event as InputEventPanGesture).delta.y * 0.05)
		_player()
	elif event is InputEventKey and event.pressed and not event.echo:
		match (event as InputEventKey).keycode:
			KEY_Q:
				_player()
				ease_to(target, distance, yaw_deg + Rules.ROTATE_STEP)
			KEY_E:
				_player()
				ease_to(target, distance, yaw_deg - Rules.ROTATE_STEP)
			KEY_EQUAL, KEY_KP_ADD:
				_zoom(0.8)
				_player()
			KEY_MINUS, KEY_KP_SUBTRACT:
				_zoom(1.25)
				_player()
			KEY_F:
				if not home.is_empty():
					ease_to(home.target, home.distance, yaw_deg)


func _zoom(f: float) -> void:
	distance = clampf(distance * f, min_distance, max_distance)
