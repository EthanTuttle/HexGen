class_name Gorge
extends RefCounted
## Port of art/scripts/gorge.py (rapids, tiles v64): a river gorge cut below the land, worked out per tile from the same
## inputs as Water.tile_water. In one tile's plan frame. There's no slab under a rapids tile with a water neighbour: this is its
## ground. Line by line; PyRandom keeps the walls' jitter the same as the Blender reference.

const DEPTH := 1.2           # the water's level below the land
const WATER_TOP := 0.03      # ordinary water's level
const NORTH_RUN := 0.5       # how far a full-height wall leans back, on the side away from the default camera
const SOUTH_RUN := 1.05      # and on the side toward it
const LANE_WIDTH := 1.32     # the cut's width at a lane: a low broken lip, then the path
const LANE_START := 0.2      # where the path starts, out from the shore
const LANE_MID := 0.76       # the walked line, out from the shore; a mini's base is 1.04 across
const LANE_TILT := 26.5      # the minis' limit is 28
const LANE_BLEND := 3        # columns over which the lip eases back to the plain wall, each side of a lane
const WALL_SHARES := [0.0, 0.14, 0.4, 0.68, 0.88, 1.0]  # across a wall, shares of its run
const WALL_RISE := [0.0, 0.2, 0.5, 0.74, 0.92, 1.0]     # and of its height
const WALL_MATS := [["rock_wet_dark"], ["rock_wet_dark", "rock_wet"], ["rock_wet"], ["rock_wet", "rock_wet", "rock_wet_moss"], ["rock_wet", "rock_wet_moss"]]
const FALL_ROWS := [[0.0, WATER_TOP], [0.1, -0.05], [0.4, -0.38], [0.55, -0.52], [0.85, -0.86], [1.0, -1.0], [1.2, -DEPTH + 0.01]]  # a waterfall: in from the edge, and height
const FALL_WHITE := [false, false, true, false, true, true]  # which steps of it are all foam
const LANE_TONES := ["gorge_lane_a", "gorge_lane_b", "gorge_lane_c", "gorge_lane_d"]  # from wet stone at its foot to nearly the ground's colour at its top
const FALL_MATS := ["foam", "fall_light", "water_fast"]
const SOIL_BANDS := [[-0.15, 0.0, "soil_light"], [-0.6, -0.15, "soil_dark"]]   # a slab's soil (hexkit_soil.py)

static var _shores_cache := {}
static var _build_cache := {}


static func shared(water: Array, widths: Array, i: int) -> bool:
	return water[i] and not widths.is_empty() and widths[i] in [Water.RAPIDS_WIDTH, Water.FALL_WIDTH]


## The water's height at p. Exact at each water edge, DEPTH down at the tile's middle, and between them by inverse distance.
static func water_z(water: Array, widths: Array, p: Vector2) -> float:
	var total := 0.0
	var weight := 0.0
	for i in 6:
		if water[i]:
			var d := maxf(Water.A - p.dot(Water.normal(i)), 0.0)
			var z := -DEPTH if shared(water, widths, i) else WATER_TOP
			if d < 1e-4:   # Python's 1e-6, for 32-bit points
				return z
			total += z / d
			weight += 1.0 / d
	var d := maxf(p.length(), 0.05)
	return (total - DEPTH / d) / (weight + 1.0 / d)


static func _crossing(a: Vector2, b: Vector2, c: Vector2, d: Vector2):
	var r := b - a
	var s := d - c
	var den := r.x * s.y - r.y * s.x
	if absf(den) < 1e-9:
		return null
	var t := ((c.x - a.x) * s.y - (c.y - a.y) * s.x) / den
	var u := ((c.x - a.x) * r.y - (c.y - a.y) * r.x) / den
	return a + r * t if t > 0 and t < 1 and u > 0 and u < 1 else null


## A wall's lip folds over itself on the inside of a tight bend: collapse each loop to the point where it crosses.
static func _untangle(row: PackedVector2Array) -> PackedVector2Array:
	var n := row.size() - 1
	for i in n - 2:
		for j in range(n - 1, i + 1, -1):
			var x = _crossing(row[i], row[i + 1], row[j], row[j + 1])
			if x != null:
				for k in range(i + 1, j + 1):
					row[k] = x
				break
	return row


## Triangles (index triples) for a simple polygon, anticlockwise.
static func _ear_clip(poly: PackedVector2Array) -> Array:
	var idx: Array[int] = []
	for k in poly.size():
		idx.append(k)
	var out := []
	var guard := 0
	while idx.size() > 3 and guard < 4000:
		guard += 1
		var cut := false
		for k in idx.size():
			var i0: int = idx[k - 1]
			var i1: int = idx[k]
			var i2: int = idx[(k + 1) % idx.size()]
			var a := poly[i0]
			var b := poly[i1]
			var c := poly[i2]
			if (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x) <= 1e-10:
				continue
			var blocked := false
			for j: int in idx:
				if j != i0 and j != i1 and j != i2 and _in_tri(poly[j], a, b, c):
					blocked = true
					break
			if blocked:
				continue
			out.append([i0, i1, i2])
			idx.remove_at(k)
			cut = true
			break
		if not cut:   # only degenerate corners left: drop the flattest
			var best := 0
			var least := INF
			for m in idx.size():
				var a := poly[idx[m - 1]]
				var b := poly[idx[m]]
				var c := poly[idx[(m + 1) % idx.size()]]
				var area := absf((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x))
				if area < least:
					least = area
					best = m
			idx.remove_at(best)
	if idx.size() == 3:
		out.append([idx[0], idx[1], idx[2]])
	return out


static func _in_tri(p: Vector2, a: Vector2, b: Vector2, c: Vector2) -> bool:
	return (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x) >= -1e-9 \
			and (c.x - b.x) * (p.y - b.y) - (c.y - b.y) * (p.x - b.x) >= -1e-9 \
			and (a.x - c.x) * (p.y - c.y) - (a.y - c.y) * (p.x - c.x) >= -1e-9


static func _anticlockwise(poly: PackedVector2Array) -> PackedVector2Array:
	var keep := PackedVector2Array()
	for k in poly.size():
		if (poly[k] - poly[k - 1]).length() > 1e-6:
			keep.append(poly[k])
	var area := 0.0
	for k in keep.size():
		var a := keep[k]
		var b := keep[(k + 1) % keep.size()]
		area += a.x * b.y - b.x * a.y
	if area <= 0:
		keep.reverse()
	return keep


## One shore's columns: curve, outward direction, water height, plain wall run, and jitter drawn once so a lane doesn't move the rest.
class Shore:
	var curve: PackedVector2Array
	var ends: Array
	var n: int
	var out := PackedVector2Array()
	var zw := PackedFloat64Array()
	var run := PackedFloat64Array()
	var jig := []
	var mats := []

	func _init(s: int, curve_in: PackedVector2Array, ends_in: Array, outlines: Array, water: Array, seed: String, widths: Array) -> void:
		curve = curve_in.duplicate()
		ends = ends_in
		n = curve.size() - 1
		for pair in [[0, ends[0]], [n, ends[1]]]:
			var e: int = pair[1]
			if e >= 0:   # exactly on the line, so no slit shows between the two tiles' walls
				curve[pair[0]] -= Water.normal(e) * (curve[pair[0]].dot(Water.normal(e)) - Water.A)
		var rng := PyRandom.new("%s-gorge%d" % [seed, s])
		for k in n + 1:
			var t := curve[mini(n, k + 1)] - curve[maxi(0, k - 1)]
			var l := t.length()
			var o := Vector2(-t.y, t.x) * (1.0 / (l if l != 0.0 else 1.0))
			if Water.in_water(outlines, curve[k] + o * 0.06):
				o = -o
			var edge: int = ends[0] if k == 0 else ends[1] if k == n else -1
			if edge >= 0:   # along the edge, away from the channel
				var ne := Water.normal(edge)
				var along := Vector2(-ne.y, ne.x)
				o = along if along.dot(curve[k] - ne * Water.A) > 0 else -along
			out.append(o)
		for p in curve:
			zw.append(Gorge.water_z(water, widths, p))
		for pair in [[0, ends[0]], [n, ends[1]]]:
			var e: int = pair[1]
			if e >= 0:
				zw[pair[0]] = -Gorge.DEPTH if Gorge.shared(water, widths, e) else Gorge.WATER_TOP
		for k in n + 1:
			var row := []
			for _j in 8:
				row.append(rng.uniform(-1, 1))
			jig.append(row)
		for k in n:
			var row := []
			for _j in Gorge.WALL_MATS.size():
				row.append(rng.random())
			mats.append(row)
		for k in n + 1:
			var r := lean(k) * (Gorge.WATER_TOP - zw[k]) / Gorge.DEPTH
			if k > 0 and k < n:
				r *= 1.0 + 0.16 * jig[k][0]
			run.append(maxf(r, 0.0))
		# beside a fall the wall stands straight at the edge, since the land across it isn't cut, and leans back further in
		for spec in [[0, 1, ends[0]], [n, -1, ends[1]]]:
			var e: int = spec[2]
			if e >= 0 and Water.falling(widths, e):
				var shares := [0.02, 0.3, 0.65]
				for m in 3:
					var k: int = spec[0] + spec[1] * m
					if k >= 0 and k <= n:
						run[k] *= shares[m]

	func lean(k: int) -> float:
		return (Gorge.NORTH_RUN + Gorge.SOUTH_RUN) / 2.0 + (Gorge.NORTH_RUN - Gorge.SOUTH_RUN) / 2.0 * out[k].y

	## The land edges on this shore's side, between the edges it starts and ends on.
	func land_edges() -> Array:
		var res := []
		if ends[0] < 0:
			return res
		var steps: int = posmod(ends[1] - ends[0], 6)
		if steps == 0:
			steps = 6
		for j in range(1, steps):
			res.append((ends[0] + j) % 6)
		return res

	func lip_point(k: int, d: float) -> Vector2:
		var p := curve[k] + out[k] * d
		if (k == 0 and ends[0] >= 0) or (k == n and ends[1] >= 0):
			return p
		return p if Water.inside_tile(p, 0.05) else pull_in(k, d)

	func pull_in(k: int, d: float) -> Vector2:
		var lo := 0.0
		var hi := d
		for _j in 12:
			var mid := (lo + hi) / 2.0
			if Water.inside_tile(curve[k] + out[k] * mid, 0.05):
				lo = mid
			else:
				hi = mid
		return curve[k] + out[k] * lo


## [{column: lane height}, top column], or []: from foot, along the shore by step, as far as it takes to climb to z = 0 at LANE_TILT along the walked line.
static func _lane_cols(sh: Shore, foot: int, step: int) -> Array:
	var climb := WATER_TOP - sh.zw[foot] - 0.05 + WATER_TOP - 0.03
	if climb < 0.05:
		return []
	var need := climb / tan(deg_to_rad(LANE_TILT))
	var arc := 0.0
	var cols := [[foot, 0.0]]
	var k := foot
	while arc < need:
		var j := k + step
		if j < 1 or j > sh.n - 1:
			return []
		arc += ((sh.curve[j] + sh.out[j] * LANE_MID) - (sh.curve[k] + sh.out[k] * LANE_MID)).length()
		cols.append([j, arc])
		k = j
	var foot_z := sh.zw[foot] + 0.05
	var heights := {}
	for c in cols:
		heights[c[0]] = foot_z * (1.0 - c[1] / arc)
	var before := foot - step
	if before < 1 or before > sh.n - 1:
		return []
	heights[before] = foot_z   # a landing at the water, so a mini at the foot stands clear of the wall beyond it
	return [heights, k]


static func _lane_ends(lane: Dictionary) -> Vector2i:
	var lo := 1 << 30
	var hi := -1
	for c: int in lane:
		lo = mini(lo, c)
		hi = maxi(hi, c)
	return Vector2i(lo, hi)


## The lip, widening smoothly round a lane, so it blends into the wall rather than standing out as a box.
static func _lip_row(sh: Shore, lane: Dictionary) -> PackedVector2Array:
	var ds := PackedFloat64Array()
	for k in sh.n + 1:
		if lane.has(k):
			ds.append(LANE_WIDTH + 0.03 + sh.lean(k) * -float(lane[k]) / DEPTH)
		else:
			ds.append(sh.run[k])
	if not lane.is_empty():
		var e := _lane_ends(lane)
		for pair in [[e.x, -1], [e.y, 1]]:
			var c: int = pair[0]
			for m in range(1, LANE_BLEND + 1):
				var k: int = c + pair[1] * m
				if k > 0 and k < sh.n:
					ds[k] = maxf(ds[k], sh.run[k] + (ds[c] - sh.run[k]) * (1.0 - float(m) / (LANE_BLEND + 1)))
	var row := PackedVector2Array()
	for k in sh.n + 1:
		row.append(sh.lip_point(k, ds[k]))
	return _untangle(row)


## The cut's outline: every lip in turn, anticlockwise. lanes: shore -> [lane, top column].
static func _cut_of(shs: Array, lanes: Dictionary) -> PackedVector2Array:
	var poly := PackedVector2Array()
	for s in shs.size():
		poly.append_array(_lip_row(shs[s], lanes[s][0] if lanes.has(s) else {}))
	return poly


## [outlines, shores as Shore objects].
static func _shores(water: Array, seed: String, widths: Array) -> Array:
	var key := [water, seed, widths]
	if _shores_cache.has(key):
		return _shores_cache[key]
	var w := Water.tile_water(water, seed, widths, "rapids")
	var shs := []
	for s in w.shores.size():
		shs.append(Shore.new(s, w.shores[s], w.ends[s], w.outlines, water, seed, widths))
	var res := [w.outlines, shs]
	if _shores_cache.size() > 512:
		_shores_cache.clear()
	_shores_cache[key] = res
	return res


## The cut with no lanes, as a list of outlines, for bridges to clear.
static func cut_outlines(water: Array, seed: String, widths: Array = []) -> Array:
	var shs: Array = _shores(water, seed, widths)[1]
	return [_cut_of(shs, {})] if not shs.is_empty() else []


## [lane, top column, {edge: walk}] for this shore, or []. The foot is as near the tile's middle as it can be, clear of the bridge.
static func _pick_lane(sh: Shore, s: int, shs: Array, lanes: Dictionary, ways_off: Array, water: Array, widths: Array) -> Array:
	var edges := sh.land_edges()
	if edges.is_empty():
		return []
	var feet := []
	for k in range(1, sh.n):
		feet.append(k)
	# Python's sort keeps ties in order, and Godot's doesn't: the index breaks them.
	feet.sort_custom(func(a, b): return sh.curve[a].length() < sh.curve[b].length() or (sh.curve[a].length() == sh.curve[b].length() and a < b))
	var has_fall := false
	for i in 6:
		has_fall = has_fall or Water.falling(widths, i)
	for foot: int in feet:
		for step in [1, -1]:
			var got := _lane_cols(sh, foot, step)
			if got.is_empty():
				continue
			var lane: Dictionary = got[0]
			var top: int = got[1]
			var order: Array = lane.keys()
			order.sort()
			var bent := false
			for j in order.size() - 1:
				if sh.out[order[j]].dot(sh.out[order[j] + 1]) < 0.93:
					bent = true
			if bent or sh.out[order[0]].dot(sh.out[order[-1]]) < (-0.1 if has_fall else 0.55):
				continue   # on a tight bend the wall would crowd the path, though round a pool's outside it has room
			var near_way := false
			for c: int in order:
				var q := sh.curve[c] + sh.out[c] * LANE_MID
				for way in ways_off:
					if Water.seg_dist(q, way[0], way[1]) < 1.25:
						near_way = true
			if near_way:
				continue
			var row := _lip_row(sh, lane)
			var thin := false
			for c: int in order:
				if (row[c] - sh.curve[c]).length() < LANE_WIDTH:
					thin = true
			if thin:
				continue
			var folds := false
			for c in range(maxi(0, order[0] - 1), mini(sh.n, order[-1] + 1)):
				if (row[c] - row[c + 1]).length() < 0.02:
					folds = true   # its lip folds here
			if folds:
				continue
			var with_it := lanes.duplicate()
			with_it[s] = [lane, top]
			var cut := _cut_of(shs, with_it)
			var t := sh.curve[top] + sh.out[top] * LANE_MID
			var q2 := sh.curve[top] + sh.out[top] * (LANE_WIDTH + 0.25)
			if not Water.inside_tile(q2, 0.1):
				continue
			var walks := {}
			var ok := true
			for e: int in edges:
				var mid := Water.normal(e) * Water.A
				var via := []
				if not _dry(cut, mid, q2):   # round the cut, by way of the land edges nearer the lane
					var hops := []
					for h: int in edges:
						if h != e:
							hops.append(Water.normal(h) * (Water.A - 0.3))
					via = _route_round(cut, mid, q2, hops)
					if via.is_empty():
						ok = false
						break
				var line := PackedVector3Array([Vector3(mid.x, mid.y, 0.0)])
				for h: Vector2 in via:
					line.append(Vector3(h.x, h.y, 0.0))
				line.append(Vector3(q2.x, q2.y, 0.0))
				line.append(Vector3(t.x, t.y, 0.0))
				var c: int = top - step
				while c != foot - step:
					var p := sh.curve[c] + sh.out[c] * LANE_MID
					line.append(Vector3(p.x, p.y, lane[c]))
					c -= step
				var w := sh.curve[foot] - sh.out[foot] * 0.4
				line.append(Vector3(w.x, w.y, water_z(water, widths, w)))
				walks[e] = line
			if ok:
				return [lane, top, walks]
	return []


static func _dry(cut: PackedVector2Array, a: Vector2, b: Vector2) -> bool:
	for f in 17:
		if Water.point_in(cut, a + (b - a) * (f / 16.0)):
			return false
	return true


static func _route_round(cut: PackedVector2Array, mid: Vector2, q: Vector2, hops: Array) -> Array:
	for h: Vector2 in hops:
		if _dry(cut, mid, h) and _dry(cut, h, q):
			return [h]
	for h: Vector2 in hops:
		for i: Vector2 in hops:
			if _dry(cut, mid, h) and _dry(cut, h, i) and _dry(cut, i, q):
				return [h, i]
	return []


## The waterfall on edge i: from the river's level at the edge down into the pool, as a stepped cascade, fanning out as it
## drops. Adds to tris; returns {top, foot, top_half, half}.
static func _fall_sheet(i: int, water: Array, widths: Array, seed: String, tris: Array) -> Dictionary:
	var iv := Water.edge_interval(water, i, widths)
	var a := Water.edge_point(i, iv[0])
	var b := Water.edge_point(i, iv[1])
	var mid := (a + b) * 0.5
	var along := (b - a) / (b - a).length()
	var top_half := (b - a).length() / 2.0
	var into := -Water.normal(i)
	var rng := PyRandom.new("%s-fall%d" % [seed, i])
	const ACROSS := 8
	var rows := []
	for r in FALL_ROWS.size():
		var d: float = FALL_ROWS[r][0]
		var z: float = FALL_ROWS[r][1]
		var back := absf(d - Water.POOL_BACK)
		var half := maxf(top_half, sqrt(maxf(Water.POOL_RADIUS * Water.POOL_RADIUS - back * back, 0.0)) + 0.12) if r != 0 else top_half
		var row := PackedVector3Array()
		for k in ACROSS + 1:
			var jog := 0.0 if k == 0 or k == ACROSS or r == 0 else rng.uniform(-0.05, 0.05)
			var q := mid + along * (half * (2.0 * k / ACROSS - 1.0)) + into * (d + jog)
			var c: Vector2 = q if Water.inside_tile(q, -0.01) else Water.clamp_inside(q, 0.0)
			row.append(Vector3(c.x, c.y, z))
		rows.append(row)
	var streak := []
	for _k in ACROSS:
		streak.append(rng.random() < 0.4)
	for r in rows.size() - 1:
		for k in ACROSS:
			var mat := "foam"
			if not (FALL_WHITE[r] or (streak[k] and r % 2 == 1)):
				mat = "fall_light" if rng.random() < 0.45 else "water_fast"
			var p: Vector3 = rows[r][k]
			var q: Vector3 = rows[r][k + 1]
			var s: Vector3 = rows[r + 1][k + 1]
			var t: Vector3 = rows[r + 1][k]
			_add(tris, p, q, s, mat)
			_add(tris, p, s, t, mat)
	var foot: PackedVector3Array = rows[-1]
	return {top = mid, foot = mid + into * float(FALL_ROWS[-1][0]), top_half = top_half,
			half = Vector2(foot[0].x, foot[0].y).distance_to(Vector2(foot[-1].x, foot[-1].y)) / 2.0}


static func _add(tris: Array, a: Vector3, b: Vector3, c: Vector3, mat: String) -> void:
	var area := (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
	if absf(area) > 1e-7:
		tris.append([a, b, c, mat] if area > 0 else [c, b, a, mat])


## {tris = [a, b, c, material], all facing up: walls, lanes, ground ("ground") and falls; water = [a, b, c]; sides = [four
## points, material], soil on land edges; lanes = shore -> [{column: height}, top column]; walks = land edge -> its walk,
## (x, y, z) from the edge's midpoint down the lane and into the water; cut = outline of the cut, lanes included, as a list;
## spot = its bridge, as Water.bridge_spot gives it; falls}.
static func build(water: Array, seed: String, widths: Array = [], landmark := false) -> Dictionary:
	var key := [water, seed, widths, landmark]
	if _build_cache.has(key):
		return _build_cache[key]
	var got: Array = _shores(water, seed, widths)
	var outlines: Array = got[0]
	var shs: Array = got[1]
	var spot := Water.rapids_spot(water, seed, widths, landmark)
	var ways_off := []
	if not spot.is_empty():
		var half := Water.TROLL_HALF if landmark else Water.BRIDGE_HALF
		var d := Vector2.from_angle(spot.angle) * half
		ways_off.append([spot.middle - d, spot.middle + d])
	var lanes := {}
	var walks := {}
	for s in shs.size():
		var sh: Shore = shs[s]
		if not spot.is_empty() and sh.land_edges().all(func(e): return spot.routes.has(e)):
			continue   # a bridge here crosses with no check, so no one needs a way down to the water on this side
		var picked := _pick_lane(sh, s, shs, lanes, ways_off, water, widths)
		if not picked.is_empty():
			lanes[s] = [picked[0], picked[1]]
			walks.merge(picked[2], true)
	var tris := []
	for s in shs.size():
		_wall(shs[s], lanes[s][0] if lanes.has(s) else {}, tris)
	var sides := []
	for i in 6:
		if not water[i]:
			var a := Water.edge_point(i, 0.0)
			var b := Water.edge_point(i, 1.0)
			for band in SOIL_BANDS:
				# Facing out: gorge.py's order faces in, which the preview draws from both sides and Godot culls.
				sides.append([[Vector3(b.x, b.y, band[1]), Vector3(a.x, a.y, band[1]), Vector3(a.x, a.y, band[0]), Vector3(b.x, b.y, band[0])], band[2]])
	var water_tris := []
	for o: PackedVector2Array in outlines:
		var poly := _anticlockwise(o)
		for t in _ear_clip(poly):
			var tri := []
			for j: int in t:
				tri.append(Vector3(poly[j].x, poly[j].y, water_z(water, widths, poly[j])))
			water_tris.append(tri)
	var falls := []
	for i in 6:
		if water[i] and Water.falling(widths, i):
			falls.append(_fall_sheet(i, water, widths, seed, tris))
	var out := {tris = tris, water = water_tris, sides = sides, lanes = lanes, walks = walks, cut = [_cut_of(shs, lanes)] if not shs.is_empty() else [], spot = spot, falls = falls}
	if _build_cache.size() > 256:
		_build_cache.clear()
	_build_cache[key] = out
	return out


## One shore's wall, its lane if it has one, and the ground beyond it.
static func _wall(sh: Shore, lane: Dictionary, tris: Array) -> void:
	var lip := _lip_row(sh, lane)
	var grid := []
	var ends := _lane_ends(lane) if not lane.is_empty() else Vector2i(-1, -1)
	for k in sh.n + 1:
		var p0 := sh.curve[k]
		var zw: float = sh.zw[k]
		var full := (lip[k] - p0).length()
		var o := sh.out[k]
		var edge_col := k == 0 or k == sh.n
		var col := PackedVector3Array()
		if lane.has(k):
			var zl: float = lane[k]
			var wall := maxf(full - LANE_WIDTH, 0.01)
			var kerb: float = 0.0 if mini(absi(k - ends.x), absi(k - ends.y)) == 0 else 0.03 + 0.05 * (sh.jig[k][1] + 1.0)
			var span := minf(full, LANE_WIDTH)
			for dz in [[-0.03, zw - 0.03], [0.07, zl + kerb], [LANE_START, zl], [span, zl], [span + wall * 0.5, zl * 0.45], [full, 0.0]]:
				var q := p0 + o * float(dz[0])
				col.append(Vector3(q.x, q.y, dz[1]))
		else:
			var h := -zw if zw < 0 else 0.0
			for r in 6:
				var d: float = full * WALL_SHARES[r]
				var z: float = zw - 0.03 + (h + 0.03) * WALL_RISE[r]
				if r == 0:
					d = -0.03
				elif r == 5:
					z = 0.0 if zw < WATER_TOP - 1e-6 else minf(zw, 0.0)
				elif not edge_col:
					d += 0.09 * sh.jig[k][r + 1] * minf(1.0, full)
					z += 0.09 * sh.jig[k][r + 2] * minf(1.0, h)
				var q := p0 + o * (minf(d, full * 0.97) if r != 0 else d)
				col.append(Vector3(q.x, q.y, z))
		if not edge_col:
			for j in col.size():
				var q := Vector2(col[j].x, col[j].y)
				if not Water.inside_tile(q, 0.01):
					q = Water.clamp_inside(q, 0.01)
				col[j] = Vector3(q.x, q.y, col[j].z)
		col[-1] = Vector3(lip[k].x, lip[k].y, 0.0)
		grid.append(col)
	var lowest := 0.0
	for c: int in lane:
		lowest = minf(lowest, lane[c])
	for k in sh.n:
		var on_lane := lane.has(k) and lane.has(k + 1)
		var share := 0.0
		if on_lane:
			share = 1.0 - (float(lane[k]) + float(lane[k + 1])) / 2.0 / lowest
		for r in 5:
			var mat: String
			if on_lane and r == 2:
				mat = LANE_TONES[clampi(int(share * LANE_TONES.size() + 0.6 * (sh.mats[k][r] - 0.5)), 0, LANE_TONES.size() - 1)]
			elif on_lane and r == 1:
				mat = "rock_wet"
			else:
				var opts: Array = WALL_MATS[r]
				mat = opts[int(sh.mats[k][r] * opts.size())]
			var a: Vector3 = grid[k][r]
			var b: Vector3 = grid[k + 1][r]
			var c: Vector3 = grid[k + 1][r + 1]
			var d: Vector3 = grid[k][r + 1]
			_add(tris, a, b, c, mat)
			_add(tris, a, c, d, mat)
	# the ground beyond this wall: from the lip's far end, round the tile's edge, to its near end
	if sh.ends[0] >= 0:
		var steps: int = posmod(sh.ends[1] - sh.ends[0], 6)
		if steps == 0:
			steps = 6
		var ring := PackedVector2Array([lip[0]])
		for j in steps:
			ring.append(Water.edge_point((sh.ends[0] + j) % 6, 1.0))
		ring.append(lip[sh.n])
		for k in range(sh.n - 1, 0, -1):
			ring.append(lip[k])
		var poly := _anticlockwise(ring)
		for t in _ear_clip(poly):
			_add(tris, Vector3(poly[t[0]].x, poly[t[0]].y, 0.0), Vector3(poly[t[1]].x, poly[t[1]].y, 0.0), Vector3(poly[t[2]].x, poly[t[2]].y, 0.0), "ground")
