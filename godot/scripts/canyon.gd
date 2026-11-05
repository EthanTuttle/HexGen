class_name Canyon
extends RefCounted
## Port of art/scripts/canyon.py (tiles v60): the canyon the party walks, a maze of banded rock sunk below the land,
## generated once for a whole region when it finishes. No scene calls, so generate() can run off the main thread; the
## meshes come out one to a tile, so the tiles' transition and their culling work as for any other tile.
## Plan coordinates, as in the art scripts. Compare with tools/canyon_cases.py and tools/canyon_check.gd.

const FLOOR := -1.9
const LAYER := 0.95          # one band of rock
const TOP_LEVEL := 2         # the band whose top is level with the land outside, z = 0
const MAX_LEVEL := 3.6       # the tallest rock, in bands
const HALF_WIDTH := 0.82     # a corridor's half width
const STEP_OUT := 0.2        # how far each band stands back from the one below
const ND := 10               # grid over a sixth of a tile: depth, side to side
const NV := 12
const CELL := 0.2            # the field's grid
const MINI_HALF := 0.56      # a mini's base, with a little room
const RAMP_STEEP := 27.5     # the minis' limit is 28
const PATH_HALF := 0.62      # the walked path, within the lane
const KERB := 0.07           # the rock shoulder stands this much above the path
const LANE_REACH := 2.8      # how far a lane looks for a wall to run up to
const LANE_OPEN := 0.92      # its half width on a side with no wall, where the rock stands lower than it
const MESA_HALF := 0.68      # the rock above the land: no part of it is narrower than twice this
const MESA_BACK := 0.8       # and it stands this far back from the region's edge
const MESA_RIM := 0.57       # and this far back from the canyon's rim, so it has a real ledge
const MESA_GAP := 1.05       # and two mesas are at least this far apart, or join
const MESA_LEAST := 3.5      # and no mesa is smaller than this, in square metres
const MESA_TRUE := 0.15      # how far an outline may stray from the rock it was traced from
const MESA_SIDE := 0.5       # its shortest side, so no wall is a thin strip
const MESA_CORNER := 70.0    # its sharpest corner, in degrees
const RIDGE_HALF := 0.25     # the bottom band: no part of it is narrower than twice this
const LAND_HALF := 0.4       # the band level with the land: no part of its top is narrower than twice this
const LEDGE := 0.12          # each band stands at least this far back from the one below
const STOP := Vector2(0.1, 0.0)  # the Echo Cave's stop, in its frame: +X toward the edge it faces
const SOIL_TOP := -0.15      # hexkit: tile sides, light band, then dark band
const SOIL_BOTTOM := -0.6
static var CAP_SLOPE := tan(deg_to_rad(50.0)) / LAYER  # bands per metre north of a corridor, under the camera's line of sight
static var TAN30 := tan(deg_to_rad(30.0))

const BAND := {1: "canyon_rust", 2: "canyon_orange", 3: "canyon_cream", 4: "canyon_cream"}
const LANE := ["canyon_floor", "canyon_lane_a", "canyon_lane_b", "canyon_lane_c", "canyon_top"]   # from the floor's colour at its foot to the land's at its top
const FLAT := {0: "canyon_floor", 1: "canyon_rust_top", 2: "canyon_top", 3: "canyon_cream", 4: "canyon_cream"}
const ROCK := ["canyon_side", "canyon_rust", "canyon_orange"]


static func neighbours(t: Vector2i) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for n: Vector2i in Hex.NEIGHBOURS:
		out.append(t + n)
	return out


## The same for both tiles on an edge: (q, r, i).
static func edge_key(t: Vector2i, i: int) -> Vector3i:
	var n: Vector2i = t + Hex.NEIGHBOURS[i]
	return Vector3i(t.x, t.y, i) if t < n else Vector3i(n.x, n.y, (i + 3) % 6)


static func _h(t: Vector2i, i: int, salt: int) -> float:
	return GroundCover.hash01(t.x * 13 + i * 3, t.y * 7 + i, salt)


## {openset: edge key -> true, entrances: [Vector3i(q, r, edge)...]}. facing: the edge the Echo Cave's mouth faces, into
## its region. Every tile can be reached from every other.
static func open_edges(region: Array, landmark: Vector2i, facing: int) -> Dictionary:
	var inside := {}
	for t: Vector2i in region:
		inside[t] = true
	var openset := {edge_key(landmark, facing): true}
	var start: Vector2i = landmark + Hex.NEIGHBOURS[facing]
	var seen := {landmark: true, start: true}
	var todo: Array[Vector2i] = [start]
	while not todo.is_empty():   # a winding tree: from the last tile reached, on to a neighbour picked by hash, backing up at dead ends
		var t: Vector2i = todo[-1]
		var best := -1
		var best_h := INF
		for i in 6:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if inside.has(n) and not seen.has(n):
				var h := GroundCover.hash01(t.x * 5 + n.x, t.y * 5 + n.y, 71)
				if h < best_h:
					best_h = h
					best = i
		if best < 0:
			todo.pop_back()
			continue
		var next: Vector2i = t + Hex.NEIGHBOURS[best]
		openset[edge_key(t, best)] = true
		seen[next] = true
		todo.append(next)
	var ordered: Array = region.duplicate()
	ordered.sort()
	for t: Vector2i in ordered:   # a few loops, so not every way is a dead end
		if t == landmark:
			continue
		for i in 6:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if inside.has(n) and n != landmark and t < n and _h(t, i, 72) < 0.22:
				openset[Vector3i(t.x, t.y, i)] = true
	var outer: Array = []
	for t: Vector2i in ordered:
		if t == landmark:
			continue
		for i in 6:
			if not inside.has(t + Hex.NEIGHBOURS[i]):
				outer.append(Vector3i(t.x, t.y, i))
	outer.sort_custom(func(a: Vector3i, b: Vector3i): return _h(Vector2i(a.x, a.y), a.z, 73) < _h(Vector2i(b.x, b.y), b.z, 73))
	var entrances: Array = []
	var used := {}
	for e: Vector3i in outer:   # one to a tile, so lanes don't pile up
		var t := Vector2i(e.x, e.y)
		if not used.has(t) and entrances.size() < maxi(2, outer.size() / 5):
			entrances.append(e)
			used[t] = true
	# Tiles the Echo Cave cuts off from the rest, since it has only one way in: each such group gets its own tree and
	# way in from outside.
	var left := {}
	for t: Vector2i in ordered:
		if not seen.has(t):
			left[t] = true
	while not left.is_empty():
		var keys: Array = left.keys()
		keys.sort()
		var first: Vector2i = keys[0]
		var group := {first: true}
		var stack: Array[Vector2i] = [first]
		while not stack.is_empty():
			var t: Vector2i = stack.pop_back()
			for i in 6:
				var n: Vector2i = t + Hex.NEIGHBOURS[i]
				if left.has(n) and not group.has(n):
					group[n] = true
					stack.append(n)
					openset[edge_key(t, i)] = true
		for t: Vector2i in group:
			left.erase(t)
		if not entrances.any(func(e: Vector3i): return group.has(Vector2i(e.x, e.y))):
			for e: Vector3i in outer:
				if group.has(Vector2i(e.x, e.y)):
					entrances.append(e)
					break
	return {openset = openset, entrances = entrances}


## A finished canyon growing (DOCS: design/02 -> Canyon walls): the maze stays fixed. Each new tile opens onto one old
## neighbour, never the Echo Cave, and gets its own entrance on an edge facing outside; an old entrance facing it becomes an
## ordinary opening, and then that is its way in. land: edges facing placed land are preferred for an entrance.
## Returns {openset, entrances, rebuild: the new tiles and the old ones touching them}.
static func grow(openset: Dictionary, entrances: Array, region: Array, new_tiles: Array, landmark: Vector2i, land: Dictionary) -> Dictionary:
	var open := openset.duplicate()
	var doors := entrances.duplicate()
	var inside := {}
	for t: Vector2i in region:
		inside[t] = true
	var rebuild := {}
	var todo := new_tiles.duplicate()
	while not todo.is_empty():
		var k := 0   # one that touches the canyon so far, if any does
		for j in todo.size():
			if neighbours(todo[j]).any(func(n): return inside.has(n)):
				k = j
				break
		var x: Vector2i = todo.pop_at(k)
		rebuild[x] = true
		var old_door := false
		for i in 6:
			var n: Vector2i = x + Hex.NEIGHBOURS[i]
			if inside.has(n):
				rebuild[n] = true
				var e := Vector3i(n.x, n.y, (i + 3) % 6)
				if e in doors:
					doors.erase(e)
					open[edge_key(n, e.z)] = true
					old_door = true
		if not old_door:
			var best := -1
			for i in 6:
				var n: Vector2i = x + Hex.NEIGHBOURS[i]
				if inside.has(n) and n != landmark and (best < 0 or _h(x, i, 76) < _h(x, best, 76)):
					best = i
			if best >= 0:
				open[edge_key(x, best)] = true
		inside[x] = true
		var door := _door(x, inside, land)
		if door >= 0:
			doors.append(Vector3i(x.x, x.y, door))
	_repair(open, doors, inside, new_tiles, rebuild, landmark, land)
	return {openset = open, entrances = doors, rebuild = rebuild.keys()}


## Tile t's best edge for an entrance: facing outside, placed land first, then by hash; -1 if it has none.
static func _door(t: Vector2i, inside: Dictionary, land: Dictionary) -> int:
	var best := -1
	var best_at := INF
	for i in 6:
		var n: Vector2i = t + Hex.NEIGHBOURS[i]
		if not inside.has(n):
			var at := _h(t, i, 73) + (0.0 if land.has(n) and not Variants.is_canyon(land[n]) else 2.0)
			if at < best_at:
				best_at = at
				best = i
	return best


## Holes (DOCS: nothing gets cut off): a new tile with no outer edge has no entrance, and old entrances that faced it have
## gone, so a part of the maze, or all of it, can lose its way in. Tiles that can't be reached from an entrance are opened
## onto a new tile they touch; failing that, a tile touching a new one takes an entrance, or at the very last any other.
static func _repair(open: Dictionary, doors: Array, inside: Dictionary, new_tiles: Array, rebuild: Dictionary, landmark: Vector2i, land: Dictionary) -> void:
	for _pass in inside.size() + 1:
		var seen := reached(open, doors, inside)
		if seen.size() == inside.size():
			return
		var opened := false
		if not seen.is_empty():
			for x: Vector2i in new_tiles:
				for i in 6:
					var n: Vector2i = x + Hex.NEIGHBOURS[i]
					if inside.has(n) and n != landmark and seen.has(x) != seen.has(n) and not open.has(edge_key(x, i)):
						open[edge_key(x, i)] = true
						opened = true
						break
				if opened:
					break
		if opened:
			continue
		var keys := rebuild.keys()
		keys.sort()
		var rest := inside.keys()
		rest.sort()
		keys.append_array(rest)
		for t: Vector2i in keys:
			if t != landmark and not seen.has(t):
				var door := _door(t, inside, land)
				if door >= 0:
					doors.append(Vector3i(t.x, t.y, door))
					rebuild[t] = true
					break


## The tiles that can be walked to from the entrances.
static func reached(open: Dictionary, doors: Array, inside: Dictionary) -> Dictionary:
	var seen := {}
	var todo: Array[Vector2i] = []
	for e: Vector3i in doors:
		var t := Vector2i(e.x, e.y)
		if not seen.has(t):
			seen[t] = true
			todo.append(t)
	while not todo.is_empty():
		var t: Vector2i = todo.pop_back()
		for i in 6:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if inside.has(n) and not seen.has(n) and open.has(edge_key(t, i)):
				seen[n] = true
				todo.append(n)
	return seen


static func is_open(openset: Dictionary, entrances: Array, t: Vector2i, i: int) -> bool:
	return openset.has(edge_key(t, i)) or Vector3i(t.x, t.y, i) in entrances


## Where a tile's corridors meet, in its frame. The Echo Cave's is its stop.
static func junction(t: Vector2i, landmark: Vector2i, turn: int) -> Vector2:
	if t == landmark:
		return Water.turned(STOP, turn)
	return Vector2((GroundCover.hash01(t.x, t.y, 74) - 0.5) * 0.7, (GroundCover.hash01(t.x, t.y, 75) - 0.5) * 0.7)


## A corridor from edge i's midpoint, by way of a bend, to the junction, in the tile's frame.
static func line_to_junction(t: Vector2i, i: int, landmark: Vector2i, turn: int) -> PackedVector2Array:
	var n := Water.normal(i)
	var side := Vector2(-n.y, n.x)
	var start := n * Water.A
	var end := junction(t, landmark, turn)
	var off := (_h(t, i, 76) - 0.5) * 1.7
	var need := -FLOOR / tan(deg_to_rad(RAMP_STEEP))
	var bend := n * 2.1 + side * off
	while start.distance_to(bend) + bend.distance_to(end) < need:   # too short to reach the floor within the minis' limit: bend it wider until it's long enough
		off += 0.02 if off >= 0.0 else -0.02
		bend = n * 2.1 + side * off
	return PackedVector2Array([start, bend, end])


## edge -> its corridor, for tile t's open edges.
static func tile_lines(t: Vector2i, openset: Dictionary, entrances: Array, landmark: Vector2i, turn: int) -> Dictionary:
	var out := {}
	for i in 6:
		if is_open(openset, entrances, t, i):
			out[i] = line_to_junction(t, i, landmark, turn)
	return out


## An entrance's lane line, tile-frame (x, y, z): from z = 0 at the edge's midpoint down its corridor to the floor.
static func ramp_line(t: Vector2i, i: int, landmark: Vector2i, turn: int) -> PackedVector3Array:
	var line := line_to_junction(t, i, landmark, turn)
	var run := 0.0
	for k in range(1, line.size()):
		run += line[k - 1].distance_to(line[k])
	var climb := minf(run, -FLOOR / tan(deg_to_rad(RAMP_STEEP)))   # it reaches the floor as soon as it can, so its foot stays clear of the junction
	var out := PackedVector3Array()
	var walked := 0.0
	for k in line.size():
		var q := line[k]
		var step := line[k - 1].distance_to(q) if k > 0 else 0.0
		if walked < climb and climb < walked + step:
			var a := line[k - 1]
			var p := a.lerp(q, (climb - walked) / step)
			out.append(Vector3(p.x, p.y, FLOOR))
		walked += step
		out.append(Vector3(q.x, q.y, FLOOR * minf(walked, climb) / climb))
	return out


static func seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var d := ab.dot(ab)
	var f := 0.0 if d == 0.0 else clampf((p - a).dot(ab) / d, 0.0, 1.0)
	return (p - (a + ab * f)).length()


## Rough rock: pushes the walls in and out a little, the same from any tile.
static func wobble(x: float, y: float) -> float:
	return 0.11 * sin(x * 2.1 + 1.3 * sin(y * 1.1)) + 0.07 * sin(y * 3.3 + 0.7) * sin(x * 1.7)


static func level_z(level: int) -> float:
	return FLOOR + LAYER * level


## The region's rock, in bands above the floor, on a world grid. value(x, y) is the height in bands: 0 on the floor.
class Field:
	var region := {}
	var landmark: Vector2i
	var turn: int
	var openset: Dictionary
	var entrances: Array
	var segs: Array = []       # corridors, each [a, b] in world plan coordinates
	var x0: float
	var y0: float
	var nx: int
	var ny: int
	var dist: PackedFloat64Array
	var north: PackedFloat64Array
	var ridge: PackedFloat64Array   # distance from the bottom band's line: positive inside
	var land: PackedFloat64Array    # and from the band level with the land
	var mesas: Array = []      # each one's outline, anticlockwise (PackedVector2Array)
	var lane_segs: Array = []
	var dropped: Array = []    # old mesas a new corridor reached
	var before: Field = null   # a canyon that has grown: the field its unrebuilt tiles were made from
	var kept := {}             # those tiles

	## anchored: the grid sits on the world's, so a tile that grows the region west or south can't shift it (canyon.py starts
	## it at the region's corner, which is what the compare tool checks). maze: the saved maze, in place of working one out.
	## old: a canyon that has grown: its field, whose mesas stay unless a new corridor reaches them; rebuilt: the tiles that get new
	## ones. given: mesas already worked out, for a field only there to be compared with.
	func _init(tiles: Array, lm: Vector2i, t: int, anchored := false, maze := {}, old: Field = null, rebuilt: Array = [], given = null) -> void:
		for c: Vector2i in tiles:
			region[c] = true
		landmark = lm
		turn = t
		var o := maze if not maze.is_empty() else Canyon.open_edges(tiles, lm, t)
		openset = o.openset
		entrances = o.entrances
		var lo := Vector2(INF, INF)
		var hi := Vector2(-INF, -INF)
		for c: Vector2i in tiles:
			var at := Hex.tile_position(c.x, c.y)
			lo = lo.min(at)
			hi = hi.max(at)
			for line: PackedVector2Array in Canyon.tile_lines(c, openset, entrances, lm, t).values():
				for k in range(1, line.size()):
					segs.append([at + line[k - 1], at + line[k]])
		var c_lm := Hex.tile_position(lm.x, lm.y)   # the court before the Echo Cave
		segs.append([c_lm + Water.turned(Vector2(-0.2, 1.05), t), c_lm + Water.turned(Vector2(-0.2, -1.05), t)])
		# and back behind the cave's mouth and its carvings, so no rock stands in front of them
		segs.append([c_lm + Water.turned(Vector2(-1.0, 1.1), t), c_lm + Water.turned(Vector2(-1.0, -1.1), t)])
		x0 = lo.x - 5.0
		y0 = lo.y - 5.0
		if anchored:
			x0 = floorf(x0 / Canyon.CELL) * Canyon.CELL
			y0 = floorf(y0 / Canyon.CELL) * Canyon.CELL
		nx = int((hi.x + 5.0 - x0) / Canyon.CELL) + 2
		ny = int((hi.y + 5.0 - y0) / Canyon.CELL) + 2
		var near := {}
		for s in segs:   # only look at corridors near a grid point: buckets a few metres wide
			var a: Vector2 = s[0]
			var b: Vector2 = s[1]
			for bx in range(int((minf(a.x, b.x) - x0) / 3.0) - 1, int((maxf(a.x, b.x) - x0) / 3.0) + 2):
				for by in range(int((minf(a.y, b.y) - y0) / 3.0) - 1, int((maxf(a.y, b.y) - y0) / 3.0) + 2):
					near.get_or_add(Vector2i(bx, by), []).append(s)
		dist = PackedFloat64Array()
		dist.resize(nx * ny)
		for ix in nx:
			var x := x0 + ix * Canyon.CELL
			var bx := int((x - x0) / 3.0)
			for iy in ny:
				var y := y0 + iy * Canyon.CELL
				var best := 3.0
				var bucket: Array = near.get(Vector2i(bx, int((y - y0) / 3.0)), [])
				for s in bucket:
					var d := Canyon.seg_dist(Vector2(x, y), s[0], s[1])
					if d < best:
						best = d
				dist[ix * ny + iy] = best
		# How far north to the next corridor: down each column from the north.
		var raw := PackedFloat64Array()
		raw.resize(nx * ny)
		for ix in nx:
			var run := 9.0
			for iy in range(ny - 1, -1, -1):
				run = 0.0 if dist[ix * ny + iy] < Canyon.HALF_WIDTH else minf(9.0, run + Canyon.CELL)
				raw[ix * ny + iy] = run
		# Eased across columns, so a corridor's bends don't leave thin fins of rock.
		const SPREAD := 4
		north = PackedFloat64Array()
		north.resize(nx * ny)
		for ix in nx:
			for iy in ny:
				var least := INF
				for j in range(maxi(0, ix - SPREAD), mini(nx, ix + SPREAD + 1)):
					least = minf(least, raw[j * ny + iy])
				north[ix * ny + iy] = least * 0.5 + raw[ix * ny + iy] * 0.5
		_rock_bodies()
		if given != null:
			mesas = given
			return
		mesas = _mesa_outlines()
		if old != null:   # a mesa is its own solid on top of the land, so one going leaves nothing to rejoin
			var stay := []
			for m: PackedVector2Array in old.mesas:
				var holds := true
				for q in m:
					if _bilinear(land, q.x, q.y) < Canyon.MESA_RIM - Canyon.MESA_TRUE:
						holds = false
						break
				if holds:
					stay.append(m)
				else:
					dropped.append(m)
			var fresh := stay.duplicate()
			for m: PackedVector2Array in mesas:
				var fits := true
				for q in m:
					if not GroundCover.tile_at(q) in rebuilt:
						fits = false
						break
				if fits:
					for other: PackedVector2Array in stay:
						if Canyon.outline_gap(m, other) < Canyon.MESA_GAP - 2.0 * Canyon.MESA_TRUE:
							fits = false
							break
				if fits:
					fresh.append(m)
			mesas = fresh

	## How far each grid point is from the nearest set cell, in metres: two sweeps, near enough to a true distance.
	func _reach(cells: PackedByteArray) -> PackedFloat64Array:
		const FAR := 99.0
		var side := Canyon.CELL
		var slant := Canyon.CELL * sqrt(2.0)
		var s := ny + 2   # a border of far cells, so no sweep needs a bounds check
		var out := PackedFloat64Array()
		out.resize((nx + 2) * s)
		out.fill(FAR)
		for ix in nx:
			var at := (ix + 1) * s + 1
			var from := ix * ny
			for iy in ny:
				if cells[from + iy] != 0:
					out[at + iy] = 0.0
		for at in range(s + 1, (nx + 1) * s - 1):
			var v := out[at]
			if v != 0.0:
				v = minf(v, minf(out[at - 1] + side, minf(out[at - s] + side, minf(out[at - s - 1] + slant, out[at - s + 1] + slant))))
				out[at] = v if v < FAR else FAR
		for at in range((nx + 1) * s - 2, s, -1):
			var v := out[at]
			if v != 0.0:
				v = minf(v, minf(out[at + 1] + side, minf(out[at + s] + side, minf(out[at + s + 1] + slant, out[at + s - 1] + slant))))
				out[at] = v if v < FAR else FAR
		var res := PackedFloat64Array()
		res.resize(nx * ny)
		for ix in nx:
			var at := (ix + 1) * s + 1
			var to := ix * ny
			for iy in ny:
				res[to + iy] = out[at + iy]
		return res

	static func _inverted(cells: PackedByteArray) -> PackedByteArray:
		var out := PackedByteArray()
		out.resize(cells.size())
		for k in cells.size():
			out[k] = 0 if cells[k] != 0 else 1
		return out

	## Keeps what a disc of radius half can reach while staying inside high. The distance from its outline: positive inside.
	func _body(high: PackedByteArray, half: float) -> PackedFloat64Array:
		var worn := _reach(_inverted(high))
		var core := PackedByteArray()
		core.resize(high.size())
		for k in high.size():
			core[k] = 1 if worn[k] > half else 0
		var far := _reach(core)
		var kept_cells := PackedByteArray()
		kept_cells.resize(high.size())
		for k in high.size():
			kept_cells[k] = 1 if far[k] <= half and high[k] != 0 else 0
		var inside := _reach(_inverted(kept_cells))
		var outside := _reach(kept_cells)
		var out := PackedFloat64Array()
		out.resize(high.size())
		for k in high.size():
			out[k] = inside[k] - outside[k]
		return out

	## The two lower bands, as distances from their lines. Outside the region the rock runs on by its corridors, so the rim isn't
	## worn away from that side and a way in stays open.
	func _rock_bodies() -> void:
		var r := PackedByteArray()
		var l := PackedByteArray()
		r.resize(nx * ny)
		l.resize(nx * ny)
		for ix in nx:
			var x := x0 + ix * Canyon.CELL
			for iy in ny:
				var v := slope(x, y0 + iy * Canyon.CELL)
				r[ix * ny + iy] = 1 if v >= 1.0 else 0
				l[ix * ny + iy] = 1 if v >= Canyon.TOP_LEVEL else 0
		ridge = _body(r, Canyon.RIDGE_HALF)
		land = _body(l, Canyon.LAND_HALF)

	func _grown(cells: PackedByteArray, by: float) -> PackedByteArray:
		var far := _reach(cells)
		var out := PackedByteArray()
		out.resize(cells.size())
		for k in cells.size():
			out[k] = 1 if far[k] <= by else 0
		return out

	func _opened(cells: PackedByteArray, half: float) -> PackedByteArray:
		var worn := _reach(_inverted(cells))
		var core := PackedByteArray()
		core.resize(cells.size())
		for k in cells.size():
			core[k] = 1 if worn[k] > half else 0
		return _grown(core, half)

	## The connected parts of a grid, each a list of its cells' indices.
	func _parts(cells: PackedByteArray) -> Array:
		var seen := PackedByteArray()
		seen.resize(cells.size())
		var out := []
		for start in cells.size():
			if cells[start] == 0 or seen[start] != 0:
				continue
			var part := PackedInt32Array()
			var stack := PackedInt32Array([start])
			seen[start] = 1
			while not stack.is_empty():
				var k: int = stack[-1]
				stack.resize(stack.size() - 1)
				part.append(k)
				var iy := k % ny
				for n in [k + ny, k - ny, k + 1 if iy < ny - 1 else -1, k - 1 if iy > 0 else -1]:
					if n >= 0 and n < cells.size() and cells[n] != 0 and seen[n] == 0:
						seen[n] = 1
						stack.append(n)
			out.append(part)
		return out

	## Could a mesa stand here: on the land, back from the rim and the region's edge, off the lanes and clear of the Echo Cave's
	## cliff. Lumpy, so its sides aren't parallel to any of those.
	func _mesa_room(x: float, y: float) -> bool:
		if not region.has(GroundCover.tile_at(Vector2(x, y))):
			return false
		var lump := 0.15 + 0.1 * sin(x * 1.4 + 1.7 * sin(y * 0.9)) * sin(y * 1.2 + 0.5) + 0.25 * Canyon.wobble(x, y)   # 0 to 0.3: they only ever stand further back
		if edge_margin(x, y) - lump < Canyon.MESA_BACK or _bilinear(land, x, y) - lump < Canyon.MESA_RIM:
			return false
		var at := Vector2(x, y)
		for s in lane_segs:
			if Canyon.seg_dist(at, s[0], s[1]) < 1.75:
				return false
		var q := Water.turned(at - Hex.tile_position(landmark.x, landmark.y), -turn)
		return not (q.x > -3.3 and q.x < 0.2 and absf(q.y) < 2.6)

	## Each mesa's outline, a few straight sides, anticlockwise. The disc comes after the lumps, so nothing narrows it afterwards.
	func _mesa_outlines() -> Array:
		for e: Vector3i in entrances:
			var c := Hex.tile_position(e.x, e.y)
			var line := Canyon.line_to_junction(Vector2i(e.x, e.y), e.z, landmark, turn)
			for k in range(1, line.size()):
				lane_segs.append([line[k - 1] + c, line[k] + c])
		var size := nx * ny
		var room := PackedByteArray()
		var high := PackedByteArray()
		room.resize(size)
		high.resize(size)
		for ix in nx:
			var x := x0 + ix * Canyon.CELL
			for iy in ny:
				var y := y0 + iy * Canyon.CELL
				if _bilinear(land, x, y) > 0.0 and _mesa_room(x, y):
					room[ix * ny + iy] = 1
					high[ix * ny + iy] = 1 if rock(x, y) >= Canyon.TOP_LEVEL + 1 else 0
		var kept_cells := _opened(high, Canyon.MESA_HALF)
		# a gap too narrow to read as a gap closes up, where there's room
		var wide := _grown(kept_cells, Canyon.MESA_GAP / 2.0 + Canyon.CELL)
		var shut := _reach(_inverted(wide))
		var closed := PackedByteArray()
		closed.resize(size)
		for k in size:
			closed[k] = 1 if (kept_cells[k] != 0 or (shut[k] > Canyon.MESA_GAP / 2.0 + Canyon.CELL and room[k] != 0)) and room[k] != 0 else 0
		kept_cells = _opened(closed, Canyon.MESA_HALF)
		# any that are still too close (no room to join): the smaller gives way
		var parts := _parts(kept_cells)
		var order := range(parts.size())
		order.sort_custom(func(a, b): return parts[a].size() > parts[b].size() or (parts[a].size() == parts[b].size() and a < b))
		var taken := PackedByteArray()
		taken.resize(size)
		var least_cells: float = Canyon.MESA_LEAST / (Canyon.CELL * Canyon.CELL)
		for n in order.size():
			var part: PackedInt32Array = parts[order[n]]
			var left := PackedByteArray()
			left.resize(size)
			var clear := 0
			if n > 0:
				var near := _reach(taken)
				for k in part:
					if near[k] >= Canyon.MESA_GAP + 2.0 * Canyon.MESA_TRUE:
						left[k] = 1
						clear += 1
			else:
				for k in part:
					left[k] = 1
				clear = part.size()
			var subs: Array = _parts(_opened(left, Canyon.MESA_HALF)) if clear < part.size() else [part]
			for sub: PackedInt32Array in subs:
				if sub.size() >= least_cells:
					for k in sub:
						if left[k] != 0:
							taken[k] = 1
		var out := []
		for part: PackedInt32Array in _parts(taken):
			out.append(Canyon.straighten(_trace(part)))
		return out

	## The outer outline of one part of the grid: points midway between its cells and the rest, anticlockwise.
	func _trace(part: PackedInt32Array) -> PackedVector2Array:
		var cells := {}
		for k in part:
			cells[k] = true
		var follow := {}   # corners, in half cells
		for k in part:
			var a := k / ny
			var b := k % ny
			var c := 2 * a
			var d := 2 * b
			if not (b >= 0 and cells.has(k + ny)):
				follow.get_or_add(Vector2i(c + 1, d - 1), []).append(Vector2i(c + 1, d + 1))
			if not (b < ny - 1 and cells.has(k + 1)):
				follow.get_or_add(Vector2i(c + 1, d + 1), []).append(Vector2i(c - 1, d + 1))
			if not cells.has(k - ny):
				follow.get_or_add(Vector2i(c - 1, d + 1), []).append(Vector2i(c - 1, d - 1))
			if not (b > 0 and cells.has(k - 1)):
				follow.get_or_add(Vector2i(c - 1, d - 1), []).append(Vector2i(c + 1, d - 1))
		var best: Array = []
		while not follow.is_empty():
			var start: Vector2i = follow.keys().min()
			var ring := [start]
			var q: Vector2i = follow[start].pop_back()
			if follow[start].is_empty():
				follow.erase(start)
			while q != start:
				ring.append(q)
				var nxt: Vector2i = follow[q].pop_back()
				if follow[q].is_empty():
					follow.erase(q)
				q = nxt
			if ring.size() > best.size():
				best = ring
		var out := PackedVector2Array()
		for q: Vector2i in best:
			out.append(Vector2(x0 + q.x * 0.5 * Canyon.CELL, y0 + q.y * 0.5 * Canyon.CELL))
		return out

	## How far (x, y) is inside a mesa, or 0.
	func mesa_depth(x: float, y: float) -> float:
		var p := Vector2(x, y)
		for m: PackedVector2Array in mesas:
			if Water.point_in(m, p):
				var best := INF
				for k in m.size():
					best = minf(best, Canyon.seg_dist(p, m[k - 1], m[k]))
				return best
		return 0.0

	func _bilinear(grid: PackedFloat64Array, x: float, y: float) -> float:
		var fx := minf(maxf((x - x0) / Canyon.CELL, 0.0), nx - 1.001)
		var fy := minf(maxf((y - y0) / Canyon.CELL, 0.0), ny - 1.001)
		var ix := int(fx)
		var iy := int(fy)
		var ax := fx - ix
		var ay := fy - iy
		var i00 := ix * ny + iy
		var i10 := i00 + ny
		return ((grid[i00] * (1.0 - ax) + grid[i10] * ax) * (1.0 - ay)
				+ (grid[i00 + 1] * (1.0 - ax) + grid[i10 + 1] * ax) * ay)

	## How far (x, y) is from the region's outer edge, inside it.
	func edge_margin(x: float, y: float) -> float:
		var t := GroundCover.tile_at(Vector2(x, y))
		var p := Vector2(x, y) - Hex.tile_position(t.x, t.y)
		var best := 9.0
		for i in 6:
			if not region.has(t + Hex.NEIGHBOURS[i]):
				best = minf(best, Water.A - p.dot(Water.normal(i)))
		return best

	## The rock's height in bands before its top is worked out.
	func rock(x: float, y: float, tall := true) -> float:
		var d := _bilinear(dist, x, y)
		var v := (d - Canyon.HALF_WIDTH + Canyon.wobble(x, y)) / Canyon.STEP_OUT
		v = minf(v, _bilinear(north, x, y) * Canyon.CAP_SLOPE + 0.6)
		if not tall:
			return v
		return minf(v, Canyon.TOP_LEVEL + 0.7 + (Canyon.MAX_LEVEL - Canyon.TOP_LEVEL - 0.7) * (0.5 + 0.5 * sin(x * 0.61 + 0.8) * sin(y * 0.73 - 0.4)))

	## The rock before its bands are worked out, not clamped at the floor or above the land. Negative in a corridor.
	func slope(x: float, y: float) -> float:
		var plain := (_bilinear(dist, x, y) - Canyon.HALF_WIDTH + Canyon.wobble(x, y)) / Canyon.STEP_OUT
		if not region.has(GroundCover.tile_at(Vector2(x, y))):
			return plain
		var v := rock(x, y, false)
		var margin := edge_margin(x, y)
		if margin < 0.6:   # easing to a plain slope with no cap along the region's edge, so a wall meets it with no jump
			v = v + (plain - v) * (1.0 - margin / 0.6)
		return v

	func ridge_at(x: float, y: float) -> float:
		return _bilinear(ridge, x, y)

	## Positive where the rock reaches the land. It always stands back from the band below, so every ledge is real.
	func land_at(x: float, y: float) -> float:
		return minf(_bilinear(land, x, y), ridge_at(x, y) - Canyon.LEDGE)

	## The land line at a point of a tile being rebuilt: along an edge shared with a tile that isn't, the line that tile was built with.
	func seam_land(x: float, y: float) -> float:
		if before != null:
			var t := GroundCover.tile_at(Vector2(x, y))
			var p := Vector2(x, y) - Hex.tile_position(t.x, t.y)
			for i in 6:
				if absf(p.dot(Water.normal(i)) - Water.A) < 0.002 and (kept.has(t) or kept.has(t + Hex.NEIGHBOURS[i])):
					return before._bilinear(before.land, x, y)
		return _bilinear(land, x, y)

	## The rock's height in bands, as the mesh has it: 0 on the floor, 1 and 2 on its ledges, 3 up on a mesa.
	func value(x: float, y: float) -> float:
		var a := ridge_at(x, y)
		if a <= 0.0:
			return maxf(0.0, 1.0 + a * 5.0)
		var b := land_at(x, y)
		if b <= 0.0:
			return 1.0 + minf(0.999, a * 5.0)
		var d := mesa_depth(x, y)
		return Canyon.TOP_LEVEL + 1.0 + minf(0.9, d * 1.5) if d > 0.0 else Canyon.TOP_LEVEL + minf(0.9, b * 5.0)


## The least distance between two outlines' corners and sides.
static func outline_gap(m: PackedVector2Array, o: PackedVector2Array) -> float:
	var best := INF
	for p in m:
		for k in o.size():
			best = minf(best, seg_dist(p, o[k - 1], o[k]))
	for p in o:
		for k in m.size():
			best = minf(best, seg_dist(p, m[k - 1], m[k]))
	return best


## The farthest any corner of m is from outline o, and the other way (for the compare tool).
static func outline_gap_most(m: PackedVector2Array, o: PackedVector2Array) -> float:
	var most := 0.0
	for pair in [[m, o], [o, m]]:
		for p: Vector2 in pair[0]:
			var best := INF
			for k in pair[1].size():
				best = minf(best, seg_dist(p, pair[1][k - 1], pair[1][k]))
			most = maxf(most, best)
	return most


static func _split(a: Vector2, run: Array, b: Vector2) -> Array:
	var worst := 0.0
	var at := 0
	for k in run.size():
		var d := seg_dist(run[k], a, b)
		if d >= worst:
			worst = d
			at = k
	if worst <= MESA_TRUE:
		return []
	return _split(a, run.slice(0, at), run[at]) + [run[at]] + _split(run[at], run.slice(at + 1), b)


static func _corner(pts: Array, k: int) -> float:
	var a: Vector2 = pts[k - 1]
	var b: Vector2 = pts[k]
	var c: Vector2 = pts[(k + 1) % pts.size()]
	var u := a - b
	var v := c - b
	var l := u.length() * v.length()
	return rad_to_deg(acos(clampf(u.dot(v) / (l if l != 0.0 else 1.0), -1.0, 1.0)))


static func _corner_area(pts: Array, k: int) -> float:
	var a: Vector2 = pts[k - 1]
	var b: Vector2 = pts[k]
	var c: Vector2 = pts[(k + 1) % pts.size()]
	return absf((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x))


## A traced outline as a few straight sides: within MESA_TRUE of the trace, with no side under MESA_SIDE and no corner sharper than MESA_CORNER.
static func straighten(ring_in: PackedVector2Array) -> PackedVector2Array:
	var ring := Array(ring_in)
	var far := 0
	var most := -1.0
	for k in ring.size():
		var d: float = ring[0].distance_to(ring[k])
		if d > most:
			most = d
			far = k
	var pts: Array = [ring[0]] + _split(ring[0], ring.slice(1, far), ring[far]) + [ring[far]] + _split(ring[far], ring.slice(far + 1), ring[0])
	while pts.size() > 5:
		var sharp := -1
		var least := MESA_CORNER
		for k in pts.size():
			var c := _corner(pts, k)
			if c < least:
				least = c
				sharp = k
		if sharp >= 0:
			pts.remove_at(sharp)
			continue
		var drop := -1
		var small := INF
		for k in pts.size():
			if pts[k].distance_to(pts[(k + 1) % pts.size()]) < MESA_SIDE:
				for j in [k, (k + 1) % pts.size()]:
					var area := _corner_area(pts, j)
					if area < small:
						small = area
						drop = j
		if drop < 0:
			break
		pts.remove_at(drop)
	return PackedVector2Array(pts)


## The part of a polygon of (x, y, v) at or above level, and the contour edge, if it crosses: [part, edge or []].
static func _clip(poly: Array, level: float) -> Array:
	var out := []
	var edge := []
	var n := poly.size()
	for k in n:
		var a: Vector3 = poly[k]
		var b: Vector3 = poly[(k + 1) % n]
		if a.z >= level:
			out.append(a)
		if (a.z >= level) != (b.z >= level):
			var q := a.lerp(b, (level - a.z) / (b.z - a.z))
			q.z = level
			out.append(q)
			edge.append(q)
	return [out, edge if edge.size() == 2 else []]


## One band's cut of a polygon whose values are that band's distance from its line: adds the flat it leaves at level - 1 and
## the wall, and returns the part above.
static func _band_cut(poly_in: Array, level: int, flats: Array, walls: Array) -> Array:
	var poly := []
	var flipped := []
	for q: Vector3 in poly_in:
		var z := q.z if q.z != 0.0 else 1e-6   # exactly on the line would count as both sides
		poly.append(Vector3(q.x, q.y, z))
		flipped.append(Vector3(q.x, q.y, -z))
	var low: Array = _clip(flipped, 0.0)[0]
	var cut := _clip(poly, 0.0)
	var high: Array = cut[0]
	if low.size() >= 3:
		flats.append([level - 1, low])
	if not cut[1].is_empty() and high.size() >= 3:
		var a: Vector3 = cut[1][0]
		var b: Vector3 = cut[1][1]
		var mid := Vector2.ZERO
		for q: Vector3 in high:
			mid += Vector2(q.x, q.y)
		mid /= high.size()
		var left := (b.x - a.x) * (mid.y - a.y) - (b.y - a.y) * (mid.x - a.x) > 0
		walls.append([level, a, b] if left else [level, b, a])
	return high


## Cut one triangle of (x, y, ridge) by the two lower bands: [flats, walls]. flats: [level, poly] to lie at that level's height.
## walls: [level, a, b], upright from level - 1 to level, with the higher rock on the left going from a to b. Each band is cut
## only from the one below, so its walls always stand on a ledge.
static func _terrace(tri: Array, field: Field) -> Array:
	var flats := []
	var walls := []
	var above := _band_cut(tri, 1, flats, walls)
	if above.size() >= 3:
		var ring := []   # its own value for the ridge, so its wall below always has a ledge on top
		for q: Vector3 in above:
			ring.append(Vector3(q.x, q.y, minf(field.seam_land(q.x, q.y), q.z - LEDGE)))
		var crossings := 0
		for k in ring.size():
			if (ring[k].z >= 0.0) != (ring[k - 1].z >= 0.0):
				crossings += 1
		# a line that crosses more than once in here is cut a triangle at a time, so every piece of it gets its wall
		var pieces := [ring]
		if crossings > 2:
			pieces = []
			for k in range(1, ring.size() - 1):
				pieces.append([ring[0], ring[k], ring[k + 1]])
		for piece in pieces:
			var top := _band_cut(piece, TOP_LEVEL, flats, walls)
			if top.size() >= 3:
				flats.append([TOP_LEVEL, top])
	return [flats, walls]


## One mesa, as one solid: its sides running down onto the land and a flat top.
static func _mesa(p: Piece, m: PackedVector2Array, cols: Dictionary) -> void:
	var z1 := level_z(TOP_LEVEL + 1)
	var z0 := level_z(TOP_LEVEL) - 0.02
	var side: Color = cols[BAND[TOP_LEVEL + 1]]
	for k in m.size():
		var a := m[k - 1]
		var b := m[k]
		p.poly([Vector3(a.x, a.y, z0), Vector3(b.x, b.y, z0), Vector3(b.x, b.y, z1), Vector3(a.x, a.y, z1)], side)
	var top: Color = cols[FLAT[TOP_LEVEL + 1]]
	for t in Gorge._ear_clip(m):
		p.tri(Vector3(m[t[0]].x, m[t[0]].y, z1), Vector3(m[t[1]].x, m[t[1]].y, z1), Vector3(m[t[2]].x, m[t[2]].y, z1), top)


## The tile whose mesh holds a mesa: the one under its middle, or under its first corner if its middle is off the region.
static func _mesa_owner(m: PackedVector2Array, field: Field) -> Vector2i:
	var mid := Vector2.ZERO
	for q in m:
		mid += q
	var t := GroundCover.tile_at(mid / m.size())
	return t if field.region.has(t) else GroundCover.tile_at(m[0])


## The tile's triangles of (x, y, ridge), world space, anticlockwise: each sixth is a grid between the middle and an edge,
## on points its neighbours share. Returned flat: three Vector3 to a triangle.
static func tile_grid(t: Vector2i, field: Field) -> Array:
	var c := Hex.tile_position(t.x, t.y)
	var tris := []
	var memo := {}
	for i in 6:
		var n := Water.normal(i)
		var tv := Vector2(-n.y, n.x)
		var pts := []   # (a, b) -> its point
		for a in ND + 1:
			var d := Water.A * a / ND
			var row := []
			for b in NV + 1:
				var p := n * d + tv * ((-1.0 + 2.0 * b / NV) * d * TAN30)
				var key := Vector2i(roundi(p.x * 1000.0), roundi(p.y * 1000.0))
				if not memo.has(key):
					memo[key] = Vector3(c.x + p.x, c.y + p.y, _seam_value(t, p, field))
				row.append(memo[key])
			pts.append(row)
		for a in ND:
			for b in NV:
				var q00: Vector3 = pts[a][b]
				var q10: Vector3 = pts[a + 1][b]
				var q11: Vector3 = pts[a + 1][b + 1]
				var q01: Vector3 = pts[a][b + 1]
				if a == 0:
					tris.append([q10, q11, q00])
				else:
					tris.append([q00, q10, q11])
					tris.append([q00, q11, q01])
	return tris


## The rock's height at p in tile t, tile-frame. Along an edge shared with a tile that isn't being rebuilt, it's the height
## that tile was built with, so the two still join if a new corridor's reach has changed the rock there.
static func _seam_value(t: Vector2i, p: Vector2, field: Field) -> float:
	var c := Hex.tile_position(t.x, t.y)
	if field.before != null:
		for i in 6:
			if field.kept.has(t + Hex.NEIGHBOURS[i]) and absf(p.dot(Water.normal(i)) - Water.A) < 0.001:
				return field.before.ridge_at(c.x + p.x, c.y + p.y)
	return field.ridge_at(c.x + p.x, c.y + p.y)


## Cross-sections of an entrance's lane, top to foot, world space: [x, y, z, nx, ny, left, right], with (nx, ny) pointing
## left. Its middle line is ramp_line, so the route walks on it.
static func ramp_sections(t: Vector2i, i: int, field: Field, landmark: Vector2i, turn: int, spacing := 0.35) -> Array:
	var c := Hex.tile_position(t.x, t.y)
	var line := []
	for q in ramp_line(t, i, landmark, turn):
		line.append(Vector3(q.x + c.x, q.y + c.y, q.z))
	while line.size() > 2 and line[-2].z <= FLOOR + 1e-4:
		line.pop_back()   # the rest of the way to the junction is floor
	var lens := PackedFloat32Array()
	var total := 0.0
	for k in range(1, line.size()):
		var a: Vector3 = line[k - 1]
		var b: Vector3 = line[k]
		lens.append(Vector2(a.x, a.y).distance_to(Vector2(b.x, b.y)))
		total += lens[-1]
	var own := {}
	for q in line_to_junction(t, i, landmark, turn):
		own[c + q] = true
	var others := []
	for s in field.segs:
		if not (own.has(s[0]) and own.has(s[1])):
			others.append(s)
	var count := maxi(1, roundi(total / spacing))
	var at_set := {}
	for k in count + 1:
		at_set[snappedf(total * k / count, 0.0001)] = true
	at_set[snappedf(lens[0], 0.0001)] = true
	# Where the lane passes a band's height it's level with that band's ledge: two sections there, the one above reaching
	# the wall behind the ledge, the one below only as far as the ledge's own wall.
	var ledges := {}
	for level in range(1, TOP_LEVEL):
		ledges[snappedf(total * (1.0 - level * LAYER / -FLOOR), 0.0001)] = true
	var stations: Array = at_set.keys()
	for s: float in ledges:
		stations.append(s)
		if not at_set.has(s):
			stations.append(s)
	stations.sort()
	var seen_ledge := {}
	var dirs := []
	for k in lens.size():
		var a: Vector3 = line[k]
		var b: Vector3 = line[k + 1]
		dirs.append((Vector2(b.x, b.y) - Vector2(a.x, a.y)) * (1.0 / maxf(lens[k], 1e-6)))
	var raw := []
	var into := -Water.normal(i)   # square to the tile's edge where it starts, so it meets the land along the edge
	for s: float in stations:
		var k := 0
		var walked := 0.0
		while k < lens.size() - 1 and walked + lens[k] < s:
			walked += lens[k]
			k += 1
		var f := (s - walked) / maxf(lens[k], 1e-6)
		var a: Vector3 = line[k]
		var b: Vector3 = line[k + 1]
		var d: Vector2 = dirs[k]
		if dirs.size() > 1:
			var blend := smoothstep(0.0, 1.0, clampf((s - lens[0] + 1.0) / 2.0, 0.0, 1.0))
			d = dirs[0] * (1.0 - blend) + dirs[1] * blend
			d = d * (1.0 / maxf(d.length(), 1e-6))
		var start := smoothstep(0.0, 1.0, clampf(s / 1.2, 0.0, 1.0))
		d = into * (1.0 - start) + d * start
		d = d * (1.0 / maxf(d.length(), 1e-6))
		var n := Vector2(-d.y, d.x)
		var p := a.lerp(b, f)
		var level := (p.z - FLOOR) / LAYER
		if ledges.has(s):
			level = round(level) + (0.001 if not seen_ledge.has(s) else -0.001)
			seen_ledge[s] = true
		var clear := MINI_HALF + (HALF_WIDTH + 0.06 - MINI_HALF) * minf(1.0, (p.z - FLOOR) / 0.6)   # low down, just far enough for a mini on that corridor to miss it
		raw.append([p.x, p.y, p.z, n.x, n.y, _reach(field, others, p, n, 1.0, s, level, clear), _reach(field, others, p, n, -1.0, s, level, clear)])
	# Near the land, each section is at least as wide as the next: under the rock kept level with the land, the lane
	# still covers any pit behind it. Not the very first, which is level with that rock.
	for k in range(raw.size() - 2, 0, -1):
		if stations[k] < 1.4:
			for side in [5, 6]:
				if raw[k][side] > 0.0 and raw[k + 1][side] > raw[k][side]:
					raw[k][side] = raw[k + 1][side]
	for q in raw:
		q[5] = absf(q[5])
		q[6] = absf(q[6])
	return raw


## Out to the wall and just into it, stopping short of any other corridor; negative where another corridor stopped it.
static func _reach(field: Field, others: Array, p: Vector3, n: Vector2, sign: float, s: float, level: float, clear: float) -> float:
	var w := 0.1
	var kept := 0.1
	var at := Vector2(p.x, p.y)
	var out := n * sign
	while w < LANE_REACH:
		w = minf(LANE_REACH, w + 0.06)
		var q := at + out * w
		for sg in others:
			if seg_dist(q, sg[0], sg[1]) < clear:
				return -kept
		kept = w
		# A real wall, not just a tooth of rock with a pit behind it, which the lane would leave showing.
		if float(int(field.value(q.x, q.y))) >= level:
			var solid := s > 1.4
			if not solid:
				solid = true
				for look in [0.2, 0.4, 0.6, 0.8]:
					var r: Vector2 = at + out * (w + look)
					if float(int(field.value(r.x, r.y))) < level:
						solid = false
						break
			if solid:
				return w + 0.06
	var mouth := maxf(0.0, 1.0 - s / 1.4)   # near the land it runs wide to the rock kept level with it, so no slit opens along the edge
	return minf(LANE_REACH, LANE_OPEN + (LANE_REACH - LANE_OPEN) * mouth)


# --- Meshes ----------------------------------------------------------------------------------

## The generated region: {openset, entrances, landmark, turn, pieces: tile -> Piece, triangles, field_ms, mesh_ms}. Safe
## off the main thread; turn the pieces into meshes on the main thread. grown: a finished canyon growing, {tiles, openset,
## entrances} as they were, and the result of grow(): only its rebuild tiles get pieces.
static func generate(tiles: Array, landmark: Vector2i, turn: int, seed_value: float, grown := {}) -> Dictionary:
	var t0 := Time.get_ticks_usec()
	var field: Field
	var rebuilt: Array = [] if grown.is_empty() else grown.grow.rebuild.duplicate()
	if grown.is_empty():
		field = Field.new(tiles, landmark, turn, true)
	else:
		var old := Field.new(grown.tiles, landmark, turn, true, {openset = grown.openset, entrances = grown.entrances}, null, [], grown.mesas)
		field = Field.new(tiles, landmark, turn, true, {openset = grown.grow.openset, entrances = grown.grow.entrances}, old, grown.grow.rebuild)
		field.before = old
		for m: PackedVector2Array in field.dropped:   # the tile holding a mesa that's gone has to be rebuilt without it
			var owner := _mesa_owner(m, old)
			if not owner in rebuilt:
				rebuilt.append(owner)
		for t: Vector2i in tiles:
			if not t in rebuilt:
				field.kept[t] = true
	var t1 := Time.get_ticks_usec()
	var rng := PyRandom.new(seed_value)
	var cols := {}
	for key: String in Hex.PALETTE:
		cols[key] = Color.html(Hex.PALETTE[key])
	var ordered: Array = tiles.duplicate() if grown.is_empty() else rebuilt.duplicate()
	ordered.sort()
	var pieces := {}
	for t: Vector2i in ordered:
		var p := Piece.new()
		var at := Hex.tile_position(t.x, t.y)
		p.offset = Vector3(-at.x, -at.y, 0)
		pieces[t] = p
	var mouths := PackedVector2Array()
	for e: Vector3i in field.entrances:
		mouths.append(Hex.tile_position(e.x, e.y) + Water.normal(e.z) * Water.A)
	for t: Vector2i in ordered:
		_rock(pieces[t], t, field, mouths, cols)
		_skirts(pieces[t], t, field, cols)
	for m: PackedVector2Array in field.mesas:   # each one solid, in one tile's mesh. A kept tile's mesh still has its own
		var owner := _mesa_owner(m, field)
		if pieces.has(owner):
			_mesa(pieces[owner], m, cols)
	var ramp_segs := []
	for e: Vector3i in field.entrances:
		var t := Vector2i(e.x, e.y)
		var c := Hex.tile_position(t.x, t.y)
		var line := ramp_line(t, e.z, landmark, turn)
		for k in range(1, line.size()):
			ramp_segs.append([c + Vector2(line[k - 1].x, line[k - 1].y), c + Vector2(line[k].x, line[k].y)])
		if pieces.has(t):
			_lane(pieces[t], rng, t, e.z, field, cols)
	_dwellings(pieces, rng, field, ramp_segs, cols)
	if pieces.has(landmark):
		_echo_cave(pieces[landmark], rng, landmark, turn, cols)
	for t: Vector2i in ordered:   # craggy rock on the highest ground
		var c := Hex.tile_position(t.x, t.y)
		for k in 6:
			var w := c + Water.corner(k) * 0.72
			if GroundCover.hash01(int(w.x * 3), int(w.y * 3), 79) < 0.35 and field.value(w.x, w.y) >= TOP_LEVEL + 1.7:   # well inside a mesa
				_crag(pieces[t], rng, Vector3(w.x, w.y, level_z(int(field.value(w.x, w.y)))), 0.32, 0.55, cols)
	var triangles := 0
	var per_tile := {}
	for t: Vector2i in pieces:
		per_tile[t] = pieces[t].triangles
		triangles += pieces[t].triangles
	return {openset = field.openset, entrances = field.entrances, landmark = landmark, turn = turn, tiles = tiles.duplicate(), pieces = pieces, mesas = field.mesas,
		triangles = triangles, per_tile = per_tile, field_ms = (t1 - t0) / 1000.0, mesh_ms = (Time.get_ticks_usec() - t1) / 1000.0}


static func _rock(p: Piece, t: Vector2i, field: Field, mouths: PackedVector2Array, cols: Dictionary) -> void:
	for tri in tile_grid(t, field):
		var cut := _terrace(tri, field)
		for fl in cut[0]:
			var poly: Array = fl[1]
			if poly.size() < 3:
				continue
			var area := 0.0
			for k in poly.size():
				var a: Vector3 = poly[k]
				var b: Vector3 = poly[(k + 1) % poly.size()]
				area += a.x * b.y - b.x * a.y
			if absf(area) < 1e-6:
				continue
			var z := level_z(fl[0])
			var col: Color = cols[FLAT[fl[0]]]
			var pts := []
			for q: Vector3 in poly:
				pts.append(Vector3(q.x, q.y, z))
			if area < 0.0:
				pts.reverse()
			p.poly(pts, col)
		for wall in cut[1]:
			var level: int = wall[0]
			var a: Vector3 = wall[1]
			var b: Vector3 = wall[2]
			var z1 := level_z(level)
			var z0 := level_z(level - 1)
			var m := Vector2((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)
			# Where a lane meets the land, the short walls beside it are in the land's colour, so they don't stand out against it.
			var by_mouth := false
			if level == TOP_LEVEL:
				for q in mouths:
					if m.distance_to(q) < 2.4:
						by_mouth = true
						break
			var mat: String = "canyon_top" if by_mouth else BAND[mini(level, 4)]
			p.poly([Vector3(a.x, a.y, z0), Vector3(b.x, b.y, z0), Vector3(b.x, b.y, z1), Vector3(a.x, a.y, z1)], cols[mat])


## The sides of the board on every edge facing outside the region, so nothing's open from the side.
static func _skirts(p: Piece, t: Vector2i, field: Field, cols: Dictionary) -> void:
	var c := Hex.tile_position(t.x, t.y)
	for i in 6:
		if field.region.has(t + Hex.NEIGHBOURS[i]):
			continue
		var a := c + Water.corner(i - 1)
		var b := c + Water.corner(i)
		for band in [[0.0, SOIL_TOP, "soil_light"], [SOIL_TOP, SOIL_BOTTOM, "soil_dark"], [SOIL_BOTTOM, FLOOR - 0.2, "canyon_side"]]:
			p.poly([Vector3(a.x, a.y, band[1]), Vector3(b.x, b.y, band[1]), Vector3(b.x, b.y, band[0]), Vector3(a.x, a.y, band[0])], cols[band[2]])
			# Engine change: both sides, as the render shows them. Where a corridor runs close by the edge, the skirt is seen from
			# inside, and with only its outer side the sky would show under the neighbour.
			p.poly([Vector3(b.x, b.y, band[1]), Vector3(a.x, a.y, band[1]), Vector3(a.x, a.y, band[0]), Vector3(b.x, b.y, band[0])], cols[band[2]])


static func _up(pts: Array) -> Array:
	var n := 0.0
	for k in pts.size():
		var a: Vector3 = pts[k]
		var b: Vector3 = pts[(k + 1) % pts.size()]
		n += a.x * b.y - b.x * a.y
	if n <= 0.0:
		pts.reverse()
	return pts


## One face, looking away from a point inside its part (there's no culling off in the engine).
static func _away(p: Piece, pts: Array, away: Vector3, col: Color) -> void:
	if pts.size() < 3:
		return
	var n := Vector3.ZERO
	var mid := Vector3.ZERO
	for k in pts.size():
		var a: Vector3 = pts[k]
		n += a.cross(pts[(k + 1) % pts.size()])
		mid += a
	if n.dot(mid / pts.size() - away) < 0.0:
		pts.reverse()
	p.poly(pts, col)


## ramp_parts.Run.chunk: a broken stone, a leaning, uneven frustum with no bottom.
static func _chunk(p: Piece, rng: PyRandom, s: float, d: float, z: float, r: float, h: float, col: Color, sides := 5) -> void:
	var a0 := rng.uniform(0.0, 6.28)
	var lean := Vector2(rng.uniform(-0.25, 0.25) * r, rng.uniform(-0.25, 0.25) * r)
	var rad := []
	for _k in sides:
		rad.append(r * rng.uniform(0.7, 1.15))
	var low := []
	var up := []
	for k in sides:
		var u := Vector2(cos(a0 + 6.283 * k / sides), sin(a0 + 6.283 * k / sides))
		low.append(Vector3(s + rad[k] * u.x, d + rad[k] * u.y, z - 0.04))
	for k in sides:
		var u := Vector2(cos(a0 + 6.283 * k / sides), sin(a0 + 6.283 * k / sides))
		up.append(Vector3(s + lean.x + 0.62 * rad[k] * u.x, d + lean.y + 0.62 * rad[k] * u.y, z + h * rng.uniform(0.8, 1.15)))
	var mid := Vector3(s, d, z + h / 2.0)
	for k in sides:
		var j := (k + 1) % sides
		_away(p, [low[k], low[j], up[j], up[k]], mid, col)
	p.poly(_up(up), col)


## One entrance's cut lane: rock shoulder, a low broken kerb down to the worn path, the path, kerb and shoulder again.
static func _lane(p: Piece, rng: PyRandom, t: Vector2i, i: int, field: Field, cols: Dictionary) -> void:
	var secs := ramp_sections(t, i, field, field.landmark, field.turn)
	var rows := []
	for k in secs.size():
		var s: Array = secs[k]
		var x: float = s[0]; var y: float = s[1]; var z: float = s[2]; var nx: float = s[3]; var ny: float = s[4]
		var lw: float = s[5]; var rw: float = s[6]
		var jit := 0.0 if k == 0 or k == secs.size() - 1 else 0.05
		# The kerb sinks away at both ends.
		var kerb := KERB * minf(1.0, minf(k / 3.0, (secs.size() - 1 - k) / 3.0)) * rng.uniform(0.35, 1.0)
		var pl := minf(lw, PATH_HALF + rng.uniform(-jit, jit))
		var pr := minf(rw, PATH_HALF + rng.uniform(-jit, jit))
		var cuts := [[maxf(pl + 0.04, lw), z], [pl + 0.03, z + kerb], [pl, z], [-pr, z], [-pr - 0.03, z + kerb], [minf(-pr - 0.04, -rw), z]]   # the shoulder's outer edge is at the lane's height, so it lies flush with a ledge
		var row := []
		for cut in cuts:
			row.append(Vector3(x + nx * cut[0], y + ny * cut[0], cut[1]))
		rows.append(row)
	for j in rows.size() - 1:
		if secs[j][0] == secs[j + 1][0] and secs[j][1] == secs[j + 1][1]:
			continue
		var sink: float = (secs[j][2] + secs[j + 1][2]) / 2.0 / FLOOR   # 0 at the top, 1 at the foot
		for k in 5:
			var tone := (1.0 - sink) * 4.0 + rng.uniform(-0.45, 0.45)
			tone += -0.6 if k == 2 else 1.2   # the walked middle a shade nearer the floor's, the shoulders nearer the land's
			var mat: String = LANE[clampi(roundi(tone), 0, 4)] if k in [0, 2, 4] else "canyon_top"
			p.poly_one_normal(_up([rows[j][k], rows[j + 1][k], rows[j + 1][k + 1], rows[j][k + 1]]), cols[mat])
	# Beside it: where the rock stands lower than the lane, the bands carry on up to its edge, with a broken lip; where
	# it's higher, a stone or two fallen from the cut.
	for pair in [[0, 1.0], [5, -1.0]]:
		var side: int = pair[0]
		var sign: float = pair[1]
		for k in rows.size() - 1:
			if secs[k][0] == secs[k + 1][0] and secs[k][1] == secs[k + 1][1]:
				continue
			var p0: Vector3 = rows[k][side]
			var p1: Vector3 = rows[k + 1][side]
			var x: float = secs[k][0]; var y: float = secs[k][1]; var z: float = secs[k][2]; var nx: float = secs[k][3]; var ny: float = secs[k][4]
			var out0 := Vector2(p0.x + nx * sign * 0.1, p0.y + ny * sign * 0.1)
			var out1 := Vector2(p1.x + nx * sign * 0.1, p1.y + ny * sign * 0.1)
			var l0 := (p0.z - FLOOR) / LAYER
			if float(int(field.value(out0.x, out0.y))) >= l0 and float(int(field.value(out1.x, out1.y))) >= l0:
				if rng.random() < 0.14 and z > FLOOR + 0.3 and k > 2:
					_chunk(p, rng, p0.x - nx * sign * 0.25, p0.y - ny * sign * 0.25, p0.z, rng.uniform(0.08, 0.13), rng.uniform(0.08, 0.15), cols[ROCK[k % 3]])
				continue
			var za := p0.z
			var zb := p1.z
			for level in [1, 2]:
				var lo := level_z(level - 1)
				var hi := level_z(level)
				var poly := []
				if za > lo or zb > lo:
					var ta := minf(za, hi)
					var tb := minf(zb, hi)
					if za < lo:
						var q := p0.lerp(p1, (lo - za) / (zb - za))
						poly = [Vector3(q.x, q.y, lo), Vector3(p1.x, p1.y, lo), Vector3(p1.x, p1.y, tb)]
					elif zb < lo:
						var q := p1.lerp(p0, (lo - zb) / (za - zb))
						poly = [Vector3(p0.x, p0.y, lo), Vector3(q.x, q.y, lo), Vector3(p0.x, p0.y, ta)]
					else:
						poly = [Vector3(p0.x, p0.y, lo), Vector3(p1.x, p1.y, lo), Vector3(p1.x, p1.y, tb), Vector3(p0.x, p0.y, ta)]
				_away(p, poly, Vector3(x, y, (lo + hi) / 2.0), cols[BAND[level]])
			if rng.random() < 0.55 and k > 2:
				var r: float = rng.uniform(0.08, 0.14)
				_chunk(p, rng, p0.x + nx * sign * r * 0.3, p0.y + ny * sign * r * 0.3, p0.z, r, rng.uniform(0.09, 0.2), cols[ROCK[rng.randbelow(3)]])
	# Stones along both kerbs, here and there.
	for k in range(3, rows.size() - 1):
		for q: Vector3 in [rows[k][1], rows[k][4]]:
			if rng.random() < 0.3 and field.edge_margin(q.x, q.y) > 0.3:
				_chunk(p, rng, q.x, q.y, q.z, rng.uniform(0.06, 0.1), rng.uniform(0.05, 0.11), cols[ROCK[rng.randbelow(3)]], 4)


## Cliff dwellings set into the walls, here and there along the corridors, facing into them.
static func _dwellings(pieces: Dictionary, rng: PyRandom, field: Field, ramp_segs: Array, cols: Dictionary) -> void:
	var spots := PackedVector2Array()
	var segs := field.segs.duplicate()
	segs.sort_custom(func(s, u):
		if s[0] != u[0]:
			return s[0].x < u[0].x or (s[0].x == u[0].x and s[0].y < u[0].y)
		return s[1].x < u[1].x or (s[1].x == u[1].x and s[1].y < u[1].y))
	for sg in segs:
		var a: Vector2 = sg[0]
		var b: Vector2 = sg[1]
		var ln := a.distance_to(b)
		var count := int(ln / 1.6)
		for j in count:
			var f := (j + 0.5) / maxf(count, 1)
			var m := a.lerp(b, f)
			if GroundCover.hash01(int(m.x * 3), int(m.y * 3), 77) > 0.6:
				continue
			var nrm := Vector2(-(b.y - a.y) / ln, (b.x - a.x) / ln)
			if GroundCover.hash01(int(m.x * 3), int(m.y * 3), 78) < 0.5:
				nrm = -nrm
			var skip := false
			for q in spots:
				if m.distance_to(q) < 1.3:
					skip = true
					break
			if not skip:
				for rs in ramp_segs:   # not where a lane would bury it
					if seg_dist(m, rs[0], rs[1]) < 1.7:
						skip = true
						break
			if skip:
				continue
			var hit := Vector2.INF
			for s in range(4, 14):
				var q := m + nrm * (s * 0.15)
				if field.region.has(GroundCover.tile_at(q)) and field.value(q.x, q.y) >= 1.0:   # the wall's foot
					if field.value(q.x + nrm.x * 0.5, q.y + nrm.y * 0.5) >= 1.5:   # with rock behind it, tall enough to be set into
						hit = q
					break
			if hit == Vector2.INF or GroundCover.tile_at(hit) == field.landmark:
				continue
			spots.append(m)
			if pieces.has(GroundCover.tile_at(hit)):
				_dwelling(pieces[GroundCover.tile_at(hit)], Vector3(hit.x - nrm.x * 0.02, hit.y - nrm.y * 0.02, FLOOR), atan2(-nrm.y, -nrm.x), cols)


## canyon_takes.dwelling: adobe rooms against the rock, doors facing along spin, with a ladder down.
static func _dwelling(p: Piece, at: Vector3, spin: float, cols: Dictionary) -> void:
	var by := func(x: float, y: float) -> Vector3:
		var v := Vector2(x, y).rotated(spin)
		return at + Vector3(v.x, v.y, 0)
	for r in [[-0.1, 0.0, 0.62, 0.72], [-0.05, 0.52, 0.5, 0.5], [-0.14, -0.06, 0.44, 1.25]]:
		p.box(by.call(r[0], r[1]), Vector3(0.5, r[2], r[3]), cols["adobe"], 0.0, spin)
	for d in [[-0.1, 0.16, 0.05], [0.52, 0.21, 0.05], [-0.06, 0.12, 0.8]]:
		p.box(by.call(d[1], d[0]) + Vector3(0, 0, d[2]), Vector3(0.02, 0.17, 0.3), cols["cave_dark"], 0.0, spin)
	for sd in [-1.0, 1.0]:   # a ladder up to the top room
		p.box(by.call(0.26, -0.3 + sd * 0.09), Vector3(0.03, 0.03, 1.15), cols["deadwood"], 0.0, spin)
	for k in 4:
		p.box(by.call(0.26, -0.3) + Vector3(0, 0, 0.2 + 0.27 * k), Vector3(0.03, 0.2, 0.03), cols["deadwood"], 0.0, spin)


## The Echo Cave: a mouth in a banded cliff at the back of its court, facing the edge the tile faces. Drawn in its frame.
static func _echo_cave(p: Piece, rng: PyRandom, landmark: Vector2i, turn: int, cols: Dictionary) -> void:
	var keep := p.offset
	p.offset = Vector3.ZERO
	p.spin = deg_to_rad(60.0 * turn)
	const X := -1.35
	_echo_mouth(p, X, FLOOR, cols)
	for b in 4:
		var z0 := FLOOR - 0.1 + LAYER * b
		var z1 := FLOOR + LAYER * (b + 1)
		var q := PackedVector2Array([Vector2(X - 0.04, -1.8 + 0.12 * b), Vector2(X - 1.2 + 0.1 * b, -1.7 + 0.12 * b), Vector2(X - 1.35 + 0.1 * b, 0.0),
				Vector2(X - 1.2 + 0.1 * b, 1.7 - 0.12 * b), Vector2(X - 0.04, 1.8 - 0.12 * b)])
		# The outline runs clockwise here (hexkit makes its faces either way, and the render shows both sides).
		q.reverse()
		p.prism(q, z0, z1, cols[["canyon_rust", "canyon_orange", "canyon_cream", "canyon_cream"][b]])
	_crag(p, rng, Vector3(X - 0.75, 0.3, FLOOR + LAYER * 4), 0.5, 0.8, cols)
	_spiral_ground(p, Vector3(-0.2, 0.0, FLOOR), 0.42, cols)
	p.spin = 0.0
	p.offset = keep


## canyon_takes.echo_mouth: a massive dark arch, a stone frame, carved spirals beside it, facing +X.
static func _echo_mouth(p: Piece, x: float, floor_z: float, cols: Dictionary) -> void:
	var arch := []
	for q in [[-0.95, 0.0], [0.95, 0.0], [0.95, 1.65], [0.72, 2.05], [0.3, 2.28], [-0.3, 2.28], [-0.72, 2.05], [-0.95, 1.65]]:
		arch.append(Vector3(x, q[0], floor_z + q[1]))
	p.poly(arch, cols["cave_dark"])
	for sd in [-1.0, 1.0]:
		p.box(Vector3(x + 0.14, sd * 1.12, 0), Vector3(0.3, 0.34, 2.3), cols["sandstone"], floor_z)
	var rings := []
	for q in [[-1.28, 2.28], [-0.7, 2.45], [0.0, 2.58], [0.7, 2.45], [1.28, 2.28]]:
		var z: float = floor_z + q[1]
		rings.append([Vector3(x, q[0], z), Vector3(x + 0.32, q[0], z), Vector3(x + 0.32, q[0], z + 0.34), Vector3(x, q[0], z + 0.34)])
	_loft(p, rings, [cols["sandstone"], cols["sphinx_light"], cols["sphinx_light"], cols["sandstone"]], true, true, false)
	p.box(Vector3(x + 0.3, 0, 0), Vector3(0.12, 0.36, 0.46), cols["sphinx_light"], floor_z + 2.58)
	for s in [[1.5, 1.6, 0.26], [-1.5, 1.5, 0.28], [1.5, 0.75, 0.2]]:   # canyon.build's marks, on the cliff's face
		var at := Vector3(x + 0.03, s[0], floor_z + s[1])
		var r: float = s[2]
		for k in 13:
			var u0 := Vector2(cos(k * 0.75), sin(k * 0.75)) * (r * k / 13.0)
			var u1 := Vector2(cos((k + 1) * 0.75), sin((k + 1) * 0.75)) * (r * (k + 1) / 13.0)
			var mid := (u0 + u1) * 0.5
			p.box_rot(at + Vector3(0, mid.x, mid.y), Vector3(0.02, u0.distance_to(u1) + 0.03, 0.05), cols["cave_dark"],
					Basis(Vector3(1, 0, 0), (u1 - u0).angle()))


## variants.spiral_mark, up on the ground.
static func _spiral_ground(p: Piece, at: Vector3, r: float, cols: Dictionary) -> void:
	for k in 13:
		var u0 := Vector2(cos(k * 0.75), sin(k * 0.75)) * (r * k / 13.0)
		var u1 := Vector2(cos((k + 1) * 0.75), sin((k + 1) * 0.75)) * (r * (k + 1) / 13.0)
		var mid := (u0 + u1) * 0.5
		p.box(at + Vector3(mid.x, mid.y, 0), Vector3(u0.distance_to(u1) + 0.03, 0.045, 0.012), cols["canyon_rust"], 0.02, (u1 - u0).angle())


## variants.rough_crag: a few leaning, broken blocks of uneven facets.
static func _crag(p: Piece, rng: PyRandom, at: Vector3, r: float, h: float, cols: Dictionary) -> void:
	var mats := [cols["canyon_rust"], cols["canyon_orange"], cols["canyon_cream"]]
	for _j in (3 if r > 0.45 else 2):
		var c := at + Vector3(rng.uniform(-0.6, 0.6) * r, rng.uniform(-0.6, 0.6) * r, 0)
		var hh := h * rng.uniform(0.55, 1.0)
		var lean := Vector3(rng.uniform(-0.22, 0.22) * r, rng.uniform(-0.22, 0.22) * r, 0)
		const N := 6
		var ang := rng.uniform(0.0, 6.28)
		var rad := []
		for _k in N:
			var a := rng.uniform(0.6, 1.1)
			rad.append(a * r * rng.uniform(0.6, 0.9))
		var rings := []
		for row in [[-0.1, 1.05], [0.45, 0.85], [0.8, 0.6], [1.0, 0.28]]:
			var ring := []
			for k in N:
				var sx := rng.uniform(0.85, 1.1)
				var sy := rng.uniform(0.85, 1.1)
				var sz := rng.uniform(0.93, 1.05)
				ring.append(c + lean * row[0] + Vector3(rad[k] * row[1] * sx * cos(ang + 6.283 * k / N), rad[k] * row[1] * sy * sin(ang + 6.283 * k / N), row[0] * hh * sz))
			rings.append(ring)
		_loft(p, rings, mats, false, true, true)


## variants.loft: a hull through rings of points, painted course by course. anticlockwise: which way the rings run seen
## from above (in the engine a hull's faces must look out, which the render doesn't need).
static func _loft(p: Piece, rings: Array, mats: Array, cap_start: bool, cap_end: bool, anticlockwise: bool) -> void:
	var n: int = rings[0].size()
	for k in rings.size() - 1:
		for j in n:
			var q := [rings[k][j], rings[k][(j + 1) % n], rings[k + 1][(j + 1) % n], rings[k + 1][j]]
			if not anticlockwise:
				q.reverse()
			p.poly(q, mats[k % mats.size()])
	if cap_start:
		var ring: Array = rings[0].duplicate()
		if anticlockwise:
			ring.reverse()
		p.poly(ring, mats[0])
	if cap_end:
		var ring: Array = rings[-1].duplicate()
		if not anticlockwise:
			ring.reverse()
		p.poly(ring, mats[-1])
