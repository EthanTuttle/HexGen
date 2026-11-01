class_name Lightning
extends Node3D
## Stormy plains' lightning (design/07 -> Region variant looks): now and then a bolt strikes a random stormy tile with
## a brief flash. PLACEHOLDER look and timing: one bright zigzag mesh, moved to each strike, drawn only while it
## shows; no light, no shadow. Nothing in the game depends on it.

const EVERY := Vector2(4.0, 9.0)     # seconds between strikes
const SHOW := 0.16                   # how long a bolt shows
const HEIGHT := 16.0

var tiles: Array[Vector2i] = []      # the stormy tiles (MapBoard keeps this current)
var strikes := 0
var _next := 3.0
var _left := 0.0
var _bolt := MeshInstance3D.new()


func _ready() -> void:
	_bolt.mesh = _make_bolt()
	_bolt.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_bolt.visible = false
	add_child(_bolt)


func _process(delta: float) -> void:
	if _left > 0.0:
		_left -= delta
		_bolt.visible = _left > 0.0 and fmod(_left, 0.08) > 0.025   # it flickers
		return
	if tiles.is_empty():
		return
	_next -= delta
	if _next <= 0.0:
		_next = randf_range(EVERY.x, EVERY.y)
		strike()


func strike() -> void:
	if tiles.is_empty():
		return
	var t: Vector2i = tiles[randi() % tiles.size()]
	var at := Hex.tile_position(t.x, t.y) + Vector2.from_angle(randf() * TAU) * randf() * 2.5
	_bolt.position = Hex.to3(at)
	_bolt.rotation.y = randf() * TAU
	_bolt.visible = true
	_left = SHOW
	strikes += 1


## A jagged ribbon from the sky to the ground, two-sided and unshaded.
static func _make_bolt() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var p := Vector3(0, 0, 0)
	var steps := 9
	for k in steps:
		var w0 := 0.05 + 0.1 * k / steps
		var w1 := 0.05 + 0.1 * (k + 1) / steps
		var q := Vector3(rng.randf_range(-0.9, 0.9), HEIGHT * (k + 1) / steps, rng.randf_range(-0.9, 0.9))
		for v in [p + Vector3(-w0, 0, 0), p + Vector3(w0, 0, 0), q + Vector3(w1, 0, 0),
				p + Vector3(-w0, 0, 0), q + Vector3(w1, 0, 0), q + Vector3(-w1, 0, 0)]:
			st.add_vertex(v)
		p = q
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	m.albedo_color = Color(1.0, 1.0, 0.85)
	st.set_material(m)
	return st.commit()
