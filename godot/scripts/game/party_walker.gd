class_name PartyWalker
extends Node3D
## The party on the map, each mini moving on its own (DOCS: Exploration screen -> Walking -> How the party
## moves). Minis have no walk cycle, so each one *waddles*: it rocks side to side as it slides, like a piece
## wiggled along the table. The hero leads along a curved route that bends through each hex (through the
## middle of each edge it crosses) and eases in and out; the companions follow the hero's trail a beat behind
## each, so the group stretches when the hero speeds up and bunches when it slows. Everyone faces a little way
## ahead on the route, so they turn before a corner. They follow the ground's height (hills, mountains, sand),
## slow in swamp and forest, sink a little and splash in fords, kick up dust and leave footprints in sand, and
## the grass bends away from them. On stopping they settle with a wobble, spread back into their loose cluster
## and look around; while they stand, one now and then looks somewhere else. Numbers: Rules (all placeholders).
## Plan coordinates as everywhere: x east, y north; Hex.to3 turns them into Godot's world.

signal entered(tile: Vector2i)          # the hero stepped onto a new hex

var map: MapBoard
var members: Array[Dictionary] = []     # {node, body, offset, phase, side, yaw}
var walking := false
var facing := -PI / 2                   # the cluster's facing (plan angle) while standing; south to start

var _path := PackedVector2Array()       # the route, densely sampled
var _len := PackedFloat32Array()        # distance along it at each sample
var _s := 0.0                           # how far along the hero is
var _trail: Array[Vector2] = []         # (time, s) of the hero, for the companions to follow
var _t := 0.0
var _start_facing := 0.0
var _end_facing := 0.0
var _tile := Vector2i.ZERO
var _idle_in := 6.0
var _footprints: Array[MeshInstance3D] = []

## The hero's spot relative to the cluster's centre, and the cluster's spot on its tile (Minis.PARTY_OFFSET).
static var HERO_CELL := Vector2.ZERO


func setup(board: MapBoard, tile: Vector2i) -> void:
	map = board
	var hero_cell: Vector2i = Minis.PARTY[0][1]
	HERO_CELL = Hex.cell_position(hero_cell.x, hero_cell.y)
	for m in Minis.PARTY:
		var c: Vector2i = m[1]
		var node := Minis.make(m[0], Vector2.ZERO, Vector2(0, -1))
		add_child(node)
		# The standing cluster faces south; offsets are relative to the hero, in that frame.
		members.append({node = node, body = node.get_node("body"),
				offset = (Hex.cell_position(c.x, c.y) - HERO_CELL) * Rules.STAND_SPREAD,
				phase = 0.0, side = 1.0, yaw = 0.0})
	place_at(tile)


## Where the hero stands on a tile.
static func anchor(tile: Vector2i) -> Vector2:
	return Hex.tile_position(tile.x, tile.y) + Minis.PARTY_OFFSET + HERO_CELL


## The hero's position (the camera follows and centres on it).
func centre() -> Vector3:
	return members[0].node.position if not members.is_empty() else Vector3.ZERO


## Stands the cluster on a tile at once (start of play, back at camp after a wipe).
func place_at(tile: Vector2i, angle := -PI / 2) -> void:
	_tile = tile
	facing = angle
	walking = false
	for m in members:
		var p := anchor(tile) + _turned(m.offset, angle)
		m.node.position = Hex.to3(p, ground(p))
		m.node.rotation.y = yaw_of(angle)
		m.yaw = m.node.rotation.y
		m.body.rotation = Vector3.ZERO
		m.body.position = Vector3.ZERO


## Walks the route through these tiles (each a neighbour of the last; the first a neighbour of where the party
## stands). Returns when everyone has arrived and settled into place.
func walk(tiles: Array[Vector2i]) -> void:
	_build_path(tiles)
	_s = 0.0
	_t = 0.0
	_trail = [Vector2(0, 0)]
	_start_facing = facing
	_end_facing = _angle_at(_len[-1])
	walking = true
	while walking:
		await get_tree().process_frame
	facing = _end_facing
	_tile = tiles[-1]
	_arrive()
	await get_tree().create_timer(Rules.SETTLE_SECONDS).timeout


# --- The route ----------------------------------------------------------------------

func _build_path(tiles: Array[Vector2i]) -> void:
	var hero: Vector3 = members[0].node.position
	var pts := PackedVector2Array([Vector2(hero.x, -hero.z)])
	var here := Hex.tile_position(_tile.x, _tile.y)
	for t in tiles:
		var next := Hex.tile_position(t.x, t.y)
		var mid := (here + next) * 0.5          # the middle of the edge it crosses
		_quad(pts, here, mid)                   # bends through the hex it's in
		here = next
	var goal := anchor(tiles[-1])
	_quad(pts, here, goal)
	_path = pts
	_len = PackedFloat32Array([0.0])
	for k in range(1, pts.size()):
		_len.append(_len[-1] + pts[k].distance_to(pts[k - 1]))


## Adds a quadratic curve from the route's last point to `to`, pulled toward `control`.
static func _quad(pts: PackedVector2Array, control: Vector2, to: Vector2) -> void:
	var from := pts[-1]
	for k in range(1, 17):
		var u := k / 16.0
		pts.append(from.lerp(control, u).lerp(control.lerp(to, u), u))


func _point_at(s: float) -> Vector2:
	s = clampf(s, 0.0, _len[-1])
	var i := _len.bsearch(s)
	if i <= 0:
		return _path[0]
	if i >= _len.size():
		return _path[-1]
	var a := _len[i - 1]
	var b := _len[i]
	return _path[i - 1].lerp(_path[i], (s - a) / maxf(b - a, 1e-5))


func _angle_at(s: float) -> float:
	var a := _point_at(minf(s, _len[-1] - 0.2))
	var b := _point_at(minf(s + 0.2, _len[-1]))
	return (b - a).angle() if a.distance_to(b) > 1e-4 else facing


## The hero's distance along the route `time` seconds into the walk (the trail the companions follow).
func _trail_s(time: float) -> float:
	if time <= 0.0:
		return 0.0
	for k in range(_trail.size() - 1, 0, -1):
		if _trail[k - 1].x <= time:
			var a := _trail[k - 1]
			var b := _trail[k]
			return lerpf(a.y, b.y, (time - a.x) / maxf(b.x - a.x, 1e-5))
	return 0.0


# --- Every frame ----------------------------------------------------------------------

func _process(delta: float) -> void:
	if walking:
		_step(delta)
	else:
		_idle(delta)
	_grass()


func _step(delta: float) -> void:
	var total := _len[-1]
	_t += delta
	if _s < total:
		var p := _point_at(_s)
		var terrain: String = map.terrains.get(GroundCover.tile_at(p), "")
		var ease_in := minf(1.0, 0.3 + 0.7 * _s / Rules.WALK_EASE_IN)
		var ease_out := clampf((total - _s) / Rules.WALK_EASE_OUT, 0.15, 1.0)
		_s = minf(total, _s + Rules.WALK_SPEED * Rules.TERRAIN_SPEED.get(terrain, 1.0) * ease_in * ease_out * delta)
		var t := GroundCover.tile_at(_point_at(_s))
		if t != _tile and map.terrains.has(t):
			_tile = t
			entered.emit(t)
	_trail.append(Vector2(_t, _s))
	var done := true
	for i in members.size():
		var m: Dictionary = members[i]
		var s := _trail_s(_t - i * Rules.FOLLOW_DELAY)
		if s < total - 1e-3:
			done = false
		_place_member(m, s, total, delta)
	if done:
		walking = false


func _place_member(m: Dictionary, s: float, total: float, delta: float) -> void:
	# Its spot: the route, plus its place in the cluster, which narrows to a loose file while walking.
	var w_start := smoothstep(0.0, 1.2, s)
	var w_end := smoothstep(0.0, 1.2, total - s)
	var tangent := _angle_at(s)
	var frame := lerp_angle(lerp_angle(_start_facing, tangent, w_start), _end_facing, 1.0 - w_end)
	var off := _turned(m.offset, frame)
	var across := Vector2.from_angle(tangent + PI / 2)
	var walking_off := across * off.dot(across) * Rules.WALK_SPREAD
	var p := _point_at(s) + off.lerp(walking_off, w_start * w_end)
	var old: Vector3 = m.node.position
	var y := ground(p)
	var wet := in_water(p)
	if wet:
		y -= Rules.WADE_DEPTH
	m.node.position = Hex.to3(p, lerpf(old.y, y, minf(1.0, delta * 14.0)))
	# Facing: a little way ahead on the route, so it turns before a corner.
	var want := yaw_of(lerp_angle(_angle_at(minf(s + Rules.LOOK_AHEAD, total)), _end_facing, 1.0 - w_end))
	m.node.rotation.y = lerp_angle(m.node.rotation.y, want, minf(1.0, delta * Rules.TURN_RATE))
	# The waddle: rock side to side with the distance slid; each rock is a footstep.
	var moved := Vector2(old.x, old.z).distance_to(Vector2(m.node.position.x, m.node.position.z))
	var speed := clampf(moved / maxf(delta, 1e-4) / Rules.WALK_SPEED, 0.0, 1.0)
	m.phase += moved / Rules.WADDLE_STRIDE * PI
	var rock := sin(m.phase)
	m.body.rotation.z = deg_to_rad(Rules.WADDLE_DEG) * rock * speed
	m.body.position.y = Rules.WADDLE_BOB * absf(rock) * speed
	if signf(rock) != m.side and moved > 0.0:
		m.side = signf(rock)
		_footstep(m, p, wet)


# --- Ground ----------------------------------------------------------------------------

## The ground's height at a plan point: the hills' and mountains' surfaces and the desert sand (they have
## collision, MapBoard), otherwise the flat tile top at 0.
func ground(p: Vector2) -> float:
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(Hex.to3(p, 40.0), Hex.to3(p, -2.0))
	var hit := space.intersect_ray(q)
	return maxf(0.0, (hit.position as Vector3).y) if not hit.is_empty() else 0.0


func in_water(p: Vector2) -> bool:
	var t := GroundCover.tile_at(p)
	if not map.water_shapes.has(t):
		return false
	var local := p - Hex.tile_position(t.x, t.y)
	for o: PackedVector2Array in map.water_shapes[t].outlines:
		if Water.point_in(o, local):
			return true
	return false


static func yaw_of(angle: float) -> float:
	return atan2(cos(angle), -sin(angle))   # Minis face +Z: a plan direction to rotation.y


## An offset from the south-facing frame turned to face `angle`.
static func _turned(offset: Vector2, angle: float) -> Vector2:
	return offset.rotated(angle + PI / 2)


# --- Arrival and standing ----------------------------------------------------------------

func _arrive() -> void:
	for i in members.size():
		var m: Dictionary = members[i]
		var body: Node3D = m.body
		var s := deg_to_rad(Rules.SETTLE_DEG)
		var k := Rules.SETTLE_SECONDS / 4.0
		var tw := create_tween()
		tw.tween_property(body, "rotation:z", s * m.side, k)
		tw.tween_property(body, "rotation:z", -s * 0.55 * m.side, k)
		tw.tween_property(body, "rotation:z", s * 0.25 * m.side, k)
		tw.tween_property(body, "rotation:z", 0.0, k)
		tw.parallel().tween_property(body, "position:y", 0.0, k)
		# Then a look around: aside, the other way, back.
		var node: Node3D = m.node
		m.yaw = node.rotation.y
		var look := deg_to_rad(Rules.LOOK_AROUND_DEG) * (1.0 if i % 2 == 0 else -1.0)
		var lt := create_tween()
		lt.tween_interval(Rules.SETTLE_SECONDS * 0.6 + i * 0.15)
		lt.tween_property(node, "rotation:y", m.yaw + look, 0.35).set_trans(Tween.TRANS_SINE)
		lt.tween_interval(0.35)
		lt.tween_property(node, "rotation:y", m.yaw - look * 0.6, 0.45).set_trans(Tween.TRANS_SINE)
		lt.tween_property(node, "rotation:y", m.yaw, 0.35).set_trans(Tween.TRANS_SINE)
	_idle_in = randf_range(Rules.IDLE_LOOK_EVERY.x, Rules.IDLE_LOOK_EVERY.y) + 2.0


func _idle(delta: float) -> void:
	if members.is_empty() or not visible:
		return
	_idle_in -= delta
	if _idle_in > 0.0:
		return
	_idle_in = randf_range(Rules.IDLE_LOOK_EVERY.x, Rules.IDLE_LOOK_EVERY.y)
	var m: Dictionary = members[randi() % members.size()]
	var node: Node3D = m.node
	var look := deg_to_rad(Rules.IDLE_LOOK_DEG) * (1.0 if randf() < 0.5 else -1.0)
	var tw := create_tween()
	tw.tween_property(node, "rotation:y", m.yaw + look, 0.4).set_trans(Tween.TRANS_SINE)
	tw.tween_interval(randf_range(1.0, 2.2))
	tw.tween_property(node, "rotation:y", m.yaw, 0.5).set_trans(Tween.TRANS_SINE)


# --- Terrain effects ------------------------------------------------------------------

func _footstep(m: Dictionary, p: Vector2, wet: bool) -> void:
	var terrain: String = map.terrains.get(GroundCover.tile_at(p), "")
	var node: Node3D = m.node
	if wet:
		_burst(node.position + Vector3(0, 0.05, 0), Color("#E8F4FA"), 10, 0.45, 1.8, -9.8, 0.035)
	elif terrain in Sand.DESERTS:
		_burst(node.position + Vector3(0, 0.05, 0), Color(Hex.colour(terrain), 0.7), 5, 0.9, 0.5, 0.15, 0.09)
		_footprint(node, m.side)


## A one-shot puff of small particles (splash droplets or dust).
func _burst(at: Vector3, col: Color, amount: int, life: float, speed: float, gravity: float, size: float) -> void:
	var fx := CPUParticles3D.new()
	fx.one_shot = true
	fx.amount = amount
	fx.lifetime = life
	fx.explosiveness = 0.9
	fx.direction = Vector3.UP
	fx.spread = 65.0
	fx.initial_velocity_min = speed * 0.5
	fx.initial_velocity_max = speed
	fx.gravity = Vector3(0, gravity, 0)
	fx.scale_amount_min = 0.6
	fx.scale_amount_max = 1.2
	var mesh := SphereMesh.new()
	mesh.radius = size
	mesh.height = size * 2.0
	mesh.radial_segments = 6
	mesh.rings = 3
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = col
	if col.a < 1.0:
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mesh.material = mat
	fx.mesh = mesh
	var fade := Gradient.new()
	fade.set_color(0, Color(1, 1, 1, 1))
	fade.set_color(1, Color(1, 1, 1, 0))
	fx.color_ramp = fade
	mat.vertex_color_use_as_albedo = false
	fx.position = at
	map.add_child(fx)
	fx.emitting = true
	get_tree().create_timer(life + 0.3).timeout.connect(fx.queue_free)


## A footprint pressed into the sand, fading away.
func _footprint(node: Node3D, side: float) -> void:
	var mi := MeshInstance3D.new()
	var quad := PlaneMesh.new()
	quad.size = Vector2(0.11, 0.17)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.45, 0.33, 0.2, 0.32)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	quad.material = mat
	mi.mesh = quad
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var right := node.global_transform.basis.x.normalized()
	mi.position = node.position + right * (0.08 * side) + Vector3(0, 0.03, 0)
	mi.rotation.y = node.rotation.y
	map.add_child(mi)
	_footprints.append(mi)
	var tw := mi.create_tween()
	tw.tween_property(mat, "albedo_color:a", 0.0, Rules.FOOTPRINT_SECONDS).set_ease(Tween.EASE_IN)
	tw.tween_callback(mi.queue_free)


## The grass bends away from the minis (GroundCover's material reads their positions).
func _grass() -> void:
	var at := PackedVector3Array()
	for m in members:
		at.append(m.node.position if visible else Vector3(1e5, 0, 1e5))
	while at.size() < 4:
		at.append(Vector3(1e5, 0, 1e5))
	GroundCover.grass_material().set_shader_parameter("minis", at)
