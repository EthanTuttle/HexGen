class_name HeroView
extends TextureRect
## The real mini on the creator's Look and Name steps: its own small 3D world, drawn at the screen's pixels. It redraws only
## when the mini changes or turns. Light: PLACEHOLDER, a midday sun near the map's.

const TURN_SECONDS := 0.35
const VIEW_YAW: Array[float] = [0.0, PI * 0.5, PI, -PI * 0.5]   # Front, Right side, Back, Left side

var _vp := SubViewport.new()
var _body := MeshInstance3D.new()
var _key := ""
var _anim_left := 0.0
var _dragging := false
var yaw: float:                         # how far the mini is turned (the creator check reads it)
	get: return _body.rotation.y

## A drag across the mini spins it; on letting go it settles on the nearest of the four views (Ethan's phone note, Nov 5,
## 2026: spin by touch too, not only by the arrows). Only where the step sets spinnable.
signal turned(view: int)
var spinnable := false:
	set(v):
		spinnable = v
		mouse_filter = Control.MOUSE_FILTER_STOP if v else Control.MOUSE_FILTER_IGNORE


func _init(w: float, h: float) -> void:
	custom_minimum_size = Vector2(w, h)
	size = Vector2(w, h)
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	accessibility_name = "Your hero"


func _ready() -> void:
	_vp.own_world_3d = true
	_vp.transparent_bg = true
	_vp.msaa_3d = Viewport.MSAA_4X
	var k: float = float(get_window().size.y) / get_viewport_rect().size.y
	_vp.size = Vector2i(custom_minimum_size * k)
	_vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	add_child(_vp)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("#E8EEF2")
	env.ambient_light_energy = 0.75
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var we := WorldEnvironment.new()
	we.environment = env
	_vp.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	sun.light_energy = 0.9
	sun.shadow_enabled = true
	_vp.add_child(sun)
	var cam := Camera3D.new()
	cam.fov = 26.0
	cam.position = Vector3(0, 1.28, 4.1)
	cam.rotation_degrees = Vector3(-8, 0, 0)
	cam.current = true
	_vp.add_child(cam)
	_vp.add_child(_body)
	texture = _vp.get_texture()


func _process(delta: float) -> void:
	if _anim_left > 0.0:
		_anim_left -= delta
		if _anim_left <= 0.0:
			_vp.render_target_update_mode = SubViewport.UPDATE_ONCE


func _redraw_for(seconds: float) -> void:
	_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_anim_left = maxf(_anim_left, seconds)


## Rebuilds only when the description changed. Returns the rebuild's milliseconds, or 0.
func show_hero(d: Dictionary) -> float:
	var key := JSON.stringify(d)
	if key == _key:
		return 0.0
	_key = key
	var t0 := Time.get_ticks_usec()
	_body.mesh = HeroMini.build(d)
	var ms := (Time.get_ticks_usec() - t0) / 1000.0
	_redraw_for(0.1)
	return ms


func _gui_input(e: InputEvent) -> void:
	if not spinnable:
		return
	if e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		if not e.pressed and _dragging:
			_dragging = false
			var view := posmod(roundi(_body.rotation.y / (PI * 0.5)), 4)   # VIEW_YAW's order: front, right, back, left
			turned.emit(view)
			turn_to(view)
		accept_event()
	elif e is InputEventMouseMotion and (e as InputEventMouseMotion).button_mask & MOUSE_BUTTON_MASK_LEFT:
		_dragging = true
		_body.rotation.y += (e as InputEventMouseMotion).relative.x * 0.012
		_redraw_for(0.1)
		accept_event()


func turn_to(view: int) -> void:
	var tw := create_tween()
	var from := _body.rotation.y
	var to: float = from + wrapf(VIEW_YAW[posmod(view, 4)] - from, -PI, PI)
	tw.tween_property(_body, "rotation:y", to, TURN_SECONDS).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	_redraw_for(TURN_SECONDS + 0.1)
