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
	return PackedVector2Array([n * Water.A, n * 2.1 + side * ((_h(t, i, 76) - 0.5) * 1.7), junction(t, landmark, turn)])


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
	var dist: PackedFloat32Array
	var north: PackedFloat32Array

	func _init(tiles: Array, lm: Vector2i, t: int) -> void:
		for c: Vector2i in tiles:
			region[c] = true
		landmark = lm
		turn = t
		var o := Canyon.open_edges(tiles, lm, t)
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
		x0 = lo.x - 5.0
		y0 = lo.y - 5.0
		nx = int((hi.x + 5.0 - x0) / Canyon.CELL) + 2
		ny = int((hi.y + 5.0 - y0) / Canyon.CELL) + 2
		var near := {}
		for s in segs:   # only look at corridors near a grid point: buckets a few metres wide
			var a: Vector2 = s[0]
			var b: Vector2 = s[1]
			for bx in range(int((minf(a.x, b.x) - x0) / 3.0) - 1, int((maxf(a.x, b.x) - x0) / 3.0) + 2):
				for by in range(int((minf(a.y, b.y) - y0) / 3.0) - 1, int((maxf(a.y, b.y) - y0) / 3.0) + 2):
					near.get_or_add(Vector2i(bx, by), []).append(s)
		dist = PackedFloat32Array()
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
		var raw := PackedFloat32Array()
		raw.resize(nx * ny)
		for ix in nx:
			var run := 9.0
			for iy in range(ny - 1, -1, -1):
				run = 0.0 if dist[ix * ny + iy] < Canyon.HALF_WIDTH else minf(9.0, run + Canyon.CELL)
				raw[ix * ny + iy] = run
		# Eased across columns, so a corridor's bends don't leave thin fins of rock.
		const SPREAD := 4
		north = PackedFloat32Array()
		north.resize(nx * ny)
		for ix in nx:
			for iy in ny:
				var least := INF
				for j in range(maxi(0, ix - SPREAD), mini(nx, ix + SPREAD + 1)):
					least = minf(least, raw[j * ny + iy])
				north[ix * ny + iy] = least * 0.5 + raw[ix * ny + iy] * 0.5

	func _bilinear(grid: PackedFloat32Array, x: float, y: float) -> float:
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

	func value(x: float, y: float) -> float:
		var d := _bilinear(dist, x, y)
		var v := (d - Canyon.HALF_WIDTH + Canyon.wobble(x, y)) / Canyon.STEP_OUT
		var cap := _bilinear(north, x, y) * Canyon.CAP_SLOPE + 0.6
		var tall: float = Canyon.TOP_LEVEL + 0.4 + (Canyon.MAX_LEVEL - Canyon.TOP_LEVEL - 0.4) * (0.5 + 0.5 * sin(x * 0.61 + 0.8) * sin(y * 0.73 - 0.4))
		v = minf(v, minf(cap, tall))
		var margin := edge_margin(x, y)
		if margin < 0.6:   # level with the land outside, along the region's edge
			v = minf(v, Canyon.TOP_LEVEL + 0.001 + maxf(0.0, margin - 0.25))
			if v > Canyon.TOP_LEVEL - 0.001 or d > Canyon.HALF_WIDTH + Canyon.STEP_OUT * Canyon.TOP_LEVEL:
				v = maxf(v, Canyon.TOP_LEVEL + 0.001)
		return maxf(0.0, v)


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


## Cut one triangle of (x, y, v) by the bands: [flats, walls]. flats: [level, poly]. walls: [level, a, b].
static func _terrace(tri: Array) -> Array:
	var v0: float = tri[0].z
	var v1: float = tri[1].z
	var v2: float = tri[2].z
	var lo := int(minf(v0, minf(v1, v2)))
	var hi := int(maxf(v0, maxf(v1, v2)))
	if lo == hi:
		return [[[lo, tri]], []]
	var flats := []
	var walls := []
	var above: Array = tri
	for level in range(lo + 1, hi + 1):
		var flipped := []
		for q: Vector3 in above:
			flipped.append(Vector3(q.x, q.y, -q.z))
		var keep: Array = _clip(flipped, -level)[0]   # the part below this level
		if keep.size() >= 3:
			flats.append([level - 1, keep])
		var cut := _clip(above, level)
		if not cut[1].is_empty():
			walls.append([level, cut[1][0], cut[1][1]])
		above = cut[0]
	if above.size() >= 3:
		flats.append([hi, above])
	return [flats, walls]


## The tile's triangles of (x, y, v), world space, anticlockwise: each sixth is a grid between the middle and an edge,
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
					memo[key] = Vector3(c.x + p.x, c.y + p.y, field.value(c.x + p.x, c.y + p.y))
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
## off the main thread; turn the pieces into meshes on the main thread.
static func generate(tiles: Array, landmark: Vector2i, turn: int, seed_value: float) -> Dictionary:
	var t0 := Time.get_ticks_usec()
	var field := Field.new(tiles, landmark, turn)
	var t1 := Time.get_ticks_usec()
	var rng := PyRandom.new(seed_value)
	var cols := {}
	for key: String in Hex.PALETTE:
		cols[key] = Color.html(Hex.PALETTE[key])
	var ordered: Array = tiles.duplicate()
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
	var ramp_segs := []
	for e: Vector3i in field.entrances:
		var t := Vector2i(e.x, e.y)
		var c := Hex.tile_position(t.x, t.y)
		var line := ramp_line(t, e.z, landmark, turn)
		for k in range(1, line.size()):
			ramp_segs.append([c + Vector2(line[k - 1].x, line[k - 1].y), c + Vector2(line[k].x, line[k].y)])
		_lane(pieces[t], rng, t, e.z, field, cols)
	_dwellings(pieces, rng, field, ramp_segs, cols)
	_echo_cave(pieces[landmark], rng, landmark, turn, cols)
	for t: Vector2i in ordered:   # craggy rock on the highest ground
		var c := Hex.tile_position(t.x, t.y)
		for k in 6:
			var w := c + Water.corner(k) * 0.72
			if GroundCover.hash01(int(w.x * 3), int(w.y * 3), 79) < 0.35 and field.value(w.x, w.y) >= TOP_LEVEL + 1:
				_crag(pieces[t], rng, Vector3(w.x, w.y, level_z(int(field.value(w.x, w.y)))), 0.32, 0.55, cols)
	var triangles := 0
	var per_tile := {}
	for t: Vector2i in pieces:
		per_tile[t] = pieces[t].triangles
		triangles += pieces[t].triangles
	return {openset = field.openset, entrances = field.entrances, landmark = landmark, turn = turn, tiles = tiles.duplicate(), pieces = pieces,
		triangles = triangles, per_tile = per_tile, field_ms = (t1 - t0) / 1000.0, mesh_ms = (Time.get_ticks_usec() - t1) / 1000.0}


static func _rock(p: Piece, t: Vector2i, field: Field, mouths: PackedVector2Array, cols: Dictionary) -> void:
	for tri in tile_grid(t, field):
		var cut := _terrace(tri)
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
			# The wall looks toward the lower side. Engine change: canyon.py tests the field beside the wall's middle, and the
			# render shows both sides of a face. Here a face seen from behind is culled, and that test can be wrong along the
			# triangle's own straight contour, so the triangle's highest corner says which side the rock is.
			var m := Vector2((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)
			var top: Vector3 = tri[0]
			for q: Vector3 in tri:
				if q.z > top.z:
					top = q
			if (b.x - a.x) * (top.y - a.y) - (b.y - a.y) * (top.x - a.x) < 0.0:   # (b - a) x z looks right: rock on the left
				var keep := a
				a = b
				b = keep
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
			p.poly(_up([rows[j][k], rows[j + 1][k], rows[j + 1][k + 1], rows[j][k + 1]]), cols[mat])
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
