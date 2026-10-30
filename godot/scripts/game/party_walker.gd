class_name PartyWalker
extends Node3D
## The party on the map, each mini moving on its own (DOCS: Exploration screen -> Walking -> How the party
## moves). Minis have no walk cycle, so each one *waddles*: it rocks side to side as it slides, like a piece
## wiggled along the table. The hero leads along a curved route that bends through each hex (through the
## middle of each edge it crosses) and eases in and out; the companions follow the hero's trail a beat behind
## each, so the group stretches when the hero speeds up and bunches when it slows. Everyone faces a little way
## ahead on the route, so they turn before a corner. The route goes round peaks, mountains and ridges, so on
## hills the party stays on the grass, and a companion walking beside the route is pushed in toward it rather
## than cut into a mountain's flank. They follow the ground's height (the hills' grass, sand), each base tilted
## to lie flat on the slope like a real mini on a sloped board, so no part of a base sinks into the ground,
## slow in swamp and forest, sink a little and splash in fords, kick up dust and leave footprints in sand, and
## the grass bends away from them. On stopping they settle with a wobble, spread back into their loose cluster
## and look around; while they stand, one now and then looks somewhere else. Numbers: Rules (all placeholders).
## Plan coordinates as everywhere: x east, y north; Hex.to3 turns them into Godot's world.

signal entered(tile: Vector2i)          # the hero stepped onto a new hex

var map: MapBoard
var members: Array[Dictionary] = []     # {node, tilt, body, radius, offset, phase, side, yaw, up, squeeze}
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
var _entered := {}                      # tiles the hero has stepped onto this walk (a detour can cross back)
var _blocked := {}                      # grid point -> on or too near a mountain (this walk's detours)
const JOIN := 5                         # route samples (about 1.2 m) either side of a blocked stretch

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
		# Between the mini's spot (which turns it) and its body (which waddles): the tilt onto the slope.
		var body: MeshInstance3D = node.get_node("body")
		var tilt := Node3D.new()
		tilt.name = "tilt"
		node.add_child(tilt)
		body.reparent(tilt, false)
		var box := body.mesh.get_aabb()
		# The standing cluster faces south; offsets are relative to the hero, in that frame.
		members.append({node = node, tilt = tilt, body = body,
				radius = maxf(box.size.x, box.size.z) * 0.5,   # the base's corners (it fills a combat cell)
				offset = (Hex.cell_position(c.x, c.y) - HERO_CELL) * Rules.STAND_SPREAD,
				phase = 0.0, side = 1.0, yaw = 0.0, up = Vector3.UP, squeeze = 1.0})
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
	_blocked.clear()
	var spot := _stand_spot(tile, angle)
	facing = spot[1]
	walking = false
	for m in members:
		var p: Vector2 = spot[0] + _turned(m.offset, facing)
		m.node.rotation.y = yaw_of(angle)
		m.yaw = m.node.rotation.y
		m.up = Vector3.UP
		m.squeeze = 1.0
		_stand_on(m, p, _feel(m, p), 1.0, true)
		_rock(m, 0.0, 0.0)


## Walks the route through these tiles (each a neighbour of the last; the first a neighbour of where the party
## stands). Returns when everyone has arrived and settled into place.
func walk(tiles: Array[Vector2i]) -> void:
	_build_path(tiles)
	_s = 0.0
	_t = 0.0
	_trail = [Vector2(0, 0)]
	_start_facing = facing
	_entered = {_tile: true}
	walking = true
	while walking:
		await get_tree().process_frame
	facing = _end_facing
	_tile = tiles[-1]
	_arrive()
	await get_tree().create_timer(Rules.SETTLE_SECONDS).timeout


# --- The route ----------------------------------------------------------------------

func _build_path(tiles: Array[Vector2i]) -> void:
	_blocked.clear()
	var hero: Vector3 = members[0].node.position
	var pts := PackedVector2Array([Vector2(hero.x, -hero.z)])
	var here := Hex.tile_position(_tile.x, _tile.y)
	for t in tiles:
		var next := Hex.tile_position(t.x, t.y)
		var mid := (here + next) * 0.5          # the middle of the edge it crosses
		_quad(pts, here, mid)                   # bends through the hex it's in
		here = next
	var spot := _stand_spot(tiles[-1], (anchor(tiles[-1]) - here).angle())
	_quad(pts, here, spot[0])
	_end_facing = spot[1]
	var allowed := {_tile: true}
	for t in tiles:
		allowed[t] = true
	_set_path(_round_mountains(pts, allowed))


func _set_path(pts: PackedVector2Array) -> void:
	_path = pts
	_len = PackedFloat32Array([0.0])
	for k in range(1, pts.size()):
		_len.append(_len[-1] + pts[k].distance_to(pts[k - 1]))


# --- Round the mountains ------------------------------------------------------------------
# DOCS: the party walks round peaks and mountains rather than over them; on hills it stays on the grass. The
# curved route above bends through each hex's middle and the middle of each edge, which is just where the hills
# put a lone tile's peak and the mountains between joined tiles. Wherever the curve runs onto one (or too near
# it), that stretch is searched again on a fine grid within the route's own tiles, and the way round it is
# straightened and smoothed. Where there's no way round, the curve is kept.

## Whether a plan point is on a peak, mountain or ridge, or within the clearance of one.
func blocked(p: Vector2) -> bool:
	if _on_mountain(p):
		return true
	for k in 12:
		if _on_mountain(p + Vector2.from_angle(k * TAU / 12.0) * Rules.MOUNTAIN_CLEARANCE):
			return true
	return false


func _on_mountain(p: Vector2) -> bool:
	var q := PhysicsRayQueryParameters3D.create(Hex.to3(p, 40.0), Hex.to3(p, -2.0))
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	return not hit.is_empty() and (hit.collider as Object).get_meta("mountain", false)


func _grid_blocked(c: Vector2i) -> bool:
	if not _blocked.has(c):
		_blocked[c] = blocked(Vector2(c) * Rules.ROUTE_GRID)
	return _blocked[c]


func _round_mountains(pts: PackedVector2Array, allowed: Dictionary) -> PackedVector2Array:
	# The blocked stretches, each widened a little either side so the way round joins the curve smoothly.
	var spans := []
	var k := 0
	while k < pts.size():
		if not blocked(pts[k]):
			k += 1
			continue
		var j := k
		while j < pts.size() and blocked(pts[j]):
			j += 1
		var a := maxi(0, k - JOIN)
		var b := mini(pts.size() - 1, j - 1 + JOIN)
		while b < pts.size() - 1 and blocked(pts[b]):
			b += 1
		if not spans.is_empty() and a <= spans[-1][1]:
			spans[-1][1] = b
		else:
			spans.append([a, b])
		k = b + 1
	if spans.is_empty():
		return pts
	var out := PackedVector2Array()
	var at := 0
	for span in spans:
		out.append_array(pts.slice(at, span[0] + 1))
		var way := PackedVector2Array()
		if not blocked(pts[span[0]]) and not blocked(pts[span[1]]):
			way = _search(pts[span[0]], pts[span[1]], allowed)
		# No way round (or the ends themselves are blocked): keep the curve.
		out.append_array(_smooth(way) if way.size() >= 2 else pts.slice(span[0] + 1, span[1] + 1))
		at = span[1] + 1
	out.append_array(pts.slice(at))
	return out


## The shortest way between two clear points on the grid, staying in the route's tiles and off the mountains.
func _search(from: Vector2, to: Vector2, allowed: Dictionary) -> PackedVector2Array:
	var g := Rules.ROUTE_GRID
	var a := Vector2i((from / g).round())
	var b := Vector2i((to / g).round())
	var open := {a: (Vector2(b - a)).length()}
	var cost := {a: 0.0}
	var came := {}
	var steps := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1),
		Vector2i(1, 1), Vector2i(1, -1), Vector2i(-1, 1), Vector2i(-1, -1)]
	var budget := 20000
	while not open.is_empty() and budget > 0:
		budget -= 1
		var c: Vector2i = open.keys()[0]
		for k in open:
			if open[k] < open[c]:
				c = k
		open.erase(c)
		if c == b:
			if not came.has(c):
				return PackedVector2Array([from, to])
			var way := PackedVector2Array([to])
			while came.has(c):
				c = came[c]
				way.append(Vector2(c) * g)
			way[-1] = from
			way.reverse()
			return way
		for d: Vector2i in steps:
			var n := c + d
			if n != b and (not allowed.has(GroundCover.tile_at(Vector2(n) * g)) or _grid_blocked(n)):
				continue
			var nc: float = cost[c] + Vector2(d).length()
			if nc < cost.get(n, INF):
				cost[n] = nc
				came[n] = c
				open[n] = nc + Vector2(b - n).length()
	return PackedVector2Array()


## Takes the grid's zig-zag out of a way round: keeps only the corners it needs (each straight run clear of the
## mountains), then rounds those corners off.
func _smooth(way: PackedVector2Array) -> PackedVector2Array:
	var keep := PackedVector2Array([way[0]])
	var i := 0
	while i < way.size() - 1:
		var j := way.size() - 1
		while j > i + 1 and not _clear(way[i], way[j]):
			j -= 1
		keep.append(way[j])
		i = j
	for pass_ in 3:   # Chaikin: cut each corner a quarter of the way in, keeping the ends
		var cut := PackedVector2Array([keep[0]])
		for k in keep.size() - 1:
			if k > 0:
				cut.append(keep[k].lerp(keep[k + 1], 0.25))
			if k < keep.size() - 2:
				cut.append(keep[k].lerp(keep[k + 1], 0.75))
		cut.append(keep[-1])
		keep = cut
	# Fill it in, so the route stays densely sampled like the curves.
	var dense := PackedVector2Array([keep[0]])
	for k in range(1, keep.size()):
		var n := maxi(1, ceili(keep[k - 1].distance_to(keep[k]) / 0.15))
		for u in range(1, n + 1):
			dense.append(keep[k - 1].lerp(keep[k], float(u) / n))
	return dense.slice(1)   # the first point is already on the route


func _clear(a: Vector2, b: Vector2) -> bool:
	var n := maxi(1, ceili(a.distance_to(b) / (Rules.ROUTE_GRID * 0.5)))
	for k in range(1, n):
		var p := a.lerp(b, float(k) / n)
		if _grid_blocked(Vector2i((p / Rules.ROUTE_GRID).round())):
			return false
	return true


## Where the cluster stands on a tile: the usual spot (anchor), facing `angle`, if everyone's place there is
## clear of the mountains; else the nearest spot on the tile that is, facing away from the tile's middle.
## Returns [hero's spot, facing].
func _stand_spot(tile: Vector2i, angle: float) -> Array:
	var centre := Hex.tile_position(tile.x, tile.y)
	var spot := anchor(tile)
	if _cluster_clear(tile, spot, angle):
		return [spot, angle]
	for ring in range(1, 8):
		for k in 12:
			var p := centre + Vector2.from_angle(k * TAU / 12.0 + ring * 0.4) * ring * 0.5
			var f := (p - centre).angle()
			if _cluster_clear(tile, p, f):
				return [p, f]
	return [spot, angle]


func _cluster_clear(tile: Vector2i, spot: Vector2, face: float) -> bool:
	for m in members:
		var p: Vector2 = spot + _turned(m.offset, face)
		if GroundCover.tile_at(p) != tile or blocked(p):
			return false
	return true


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
		for m in members:   # they turn to look around while standing
			_tilt(m)
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
			if not _entered.has(t):
				_entered[t] = true
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
	var side := off.lerp(walking_off, w_start * w_end)
	var old: Vector3 = m.node.position
	# Facing: a little way ahead on the route, so it turns before a corner.
	var want := yaw_of(lerp_angle(_angle_at(minf(s + Rules.LOOK_AHEAD, total)), _end_facing, 1.0 - w_end))
	m.node.rotation.y = lerp_angle(m.node.rotation.y, want, minf(1.0, delta * Rules.TURN_RATE))
	# Its own spot must be clear of the mountains (the route's clearance is measured from the route line, and a
	# companion walks beside it): pushed in toward the route as far as it takes, spreading back out slowly.
	var squeeze := minf(1.0, m.squeeze + delta * Rules.SQUEEZE_RATE)
	var p := _point_at(s) + side * squeeze
	var felt := _feel(m, p)
	if felt.mountain and squeeze > m.squeeze:
		squeeze = m.squeeze
		p = _point_at(s) + side * squeeze
		felt = _feel(m, p)
	while felt.mountain and squeeze > 0.0:
		squeeze = maxf(0.0, squeeze - 0.25)
		p = _point_at(s) + side * squeeze
		felt = _feel(m, p)
	m.squeeze = squeeze
	var wet := in_water(p)
	_stand_on(m, p, felt, delta, false, Rules.WADE_DEPTH if wet else 0.0)
	# The waddle: rock side to side with the distance slid; each rock is a footstep.
	var moved := Vector2(old.x, old.z).distance_to(Vector2(m.node.position.x, m.node.position.z))
	var speed := clampf(moved / maxf(delta, 1e-4) / Rules.WALK_SPEED, 0.0, 1.0)
	m.phase += moved / Rules.WADDLE_STRIDE * PI
	var rock := sin(m.phase)
	_rock(m, deg_to_rad(Rules.WADDLE_DEG) * rock * speed, Rules.WADDLE_BOB * absf(rock) * speed)
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


## Feels the ground under a mini's base at `p`, as it faces now: the height just past each corner of its hex
## and the middle of each side, and under its centre (as world offsets from the centre), and whether any of
## them is on a mountain.
func _feel(m: Dictionary, p: Vector2) -> Dictionary:
	var space := get_world_3d().direct_space_state
	var node: Node3D = m.node
	var turn := node.rotation.y   # the base's local x axis as a plan angle
	var at := PackedVector3Array()
	var on := false
	for k in 13:
		var r: float = (m.radius if k % 2 == 1 else m.radius * 0.866) + Rules.BASE_MARGIN
		var o := Vector2.ZERO if k == 0 else Vector2.from_angle(turn + (k - 1) * TAU / 12.0) * r
		var hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(Hex.to3(p + o, 40.0), Hex.to3(p + o, -2.0)))
		var y := 0.0
		if not hit.is_empty():
			y = maxf(0.0, (hit.position as Vector3).y)
			on = on or (hit.collider as Object).get_meta("mountain", false)
		at.append(Vector3(o.x, y, -o.y))
	return {at = at, mountain = on}


## Sets a mini on the ground it felt: its base tilts toward the slope through those points (eased by `k`, so it
## doesn't jitter on facet edges), then sits as low as it can with none of them above the tilted base. It sinks
## to lower ground eased, but never trails below the ground. `sink` lowers it on purpose (wading).
func _stand_on(m: Dictionary, p: Vector2, felt: Dictionary, k: float, snap := false, sink := 0.0) -> void:
	var at: PackedVector3Array = felt.at
	# The slope: a plane fitted through the points (least squares; they ring the centre symmetrically).
	var sxx := 0.0
	var szz := 0.0
	var sxz := 0.0
	var sxy := 0.0
	var szy := 0.0
	for q in at:
		sxx += q.x * q.x
		szz += q.z * q.z
		sxz += q.x * q.z
		sxy += q.x * q.y
		szy += q.z * q.y
	var det := sxx * szz - sxz * sxz
	var bx := (sxy * szz - szy * sxz) / det
	var bz := (szy * sxx - sxy * sxz) / det
	var want := Vector3(-bx, 1.0, -bz).normalized()
	var most := deg_to_rad(Rules.MAX_TILT_DEG)
	if want.angle_to(Vector3.UP) > most:
		want = Vector3.UP.slerp(want, most / want.angle_to(Vector3.UP))
	var up: Vector3 = want if snap else (m.up as Vector3).slerp(want, minf(1.0, k * Rules.TILT_RATE)).normalized()
	m.up = up
	var y := -INF
	for q in at:   # the tilted base's height over each point, so none of them is above it
		y = maxf(y, q.y + (up.x * q.x + up.z * q.z) / up.y)
	y -= sink
	var old: Vector3 = m.node.position
	if not snap:
		y = maxf(y, lerpf(old.y, y, minf(1.0, k * Rules.HEIGHT_RATE)))
	m.node.position = Hex.to3(p, y)
	_tilt(m)


## Keeps the base's tilt on the slope however the mini turns (the tilt sits inside its turn).
func _tilt(m: Dictionary) -> void:
	var node: Node3D = m.node
	var tilt: Node3D = m.tilt
	tilt.basis = node.basis.inverse() * Basis(Quaternion(Vector3.UP, m.up)) * node.basis


## Rocks a mini's body by `angle` onto one side, tipping on that side's edge of its base (like a piece
## wiggled on the table), so the low edge stays on the ground; `lift` raises it a little more.
func _rock(m: Dictionary, angle: float, lift: float) -> void:
	var body: Node3D = m.body
	var pivot := Vector3(-signf(angle) * m.radius, 0, 0)
	var turn := Basis(Vector3.BACK, angle)
	body.basis = turn
	body.position = pivot - turn * pivot + Vector3(0, lift, 0)


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
		var settle := func(a: float) -> void: _rock(m, a, 0.0)
		var tw := create_tween()
		tw.tween_method(settle, body.rotation.z, s * m.side, k)
		tw.tween_method(settle, s * m.side, -s * 0.55 * m.side, k)
		tw.tween_method(settle, -s * 0.55 * m.side, s * 0.25 * m.side, k)
		tw.tween_method(settle, s * 0.25 * m.side, 0.0, k)
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
