class_name Water
extends RefCounted
## Port of art/scripts/water.py (rules: design/07 Presentation.md -> Art direction -> Water flows freely).
## Line by line, in one tile's own plan coordinates (pointy-top, centre at the origin, edge 0 facing +X).
## PyRandom makes the seeded curves and dressing identical to the Blender reference.

const R := 4.5
const A := R * sqrt(3.0) / 2.0
const RIVER_WIDTH := 1.5
const DELTA_WIDTH := 2.6        # river delta (tier 1 river variant): wider, with sandy islands
const LAKE_MARGIN := 0.25
const MEANDER := 0.9
const WOBBLE := 0.18
const SAMPLES := 18


static func normal(i: int) -> Vector2:
	var a := deg_to_rad(60.0 * i)
	return Vector2(cos(a), sin(a))


static func corner(i: int) -> Vector2:
	var a := deg_to_rad(60.0 * i + 30.0)
	return Vector2(R * cos(a), R * sin(a))


static func edge_point(i: int, t: float) -> Vector2:
	var s := corner(i - 1)
	var e := corner(i)
	return s + (e - s) * t


static func clamp_inside(p: Vector2, inset := 0.01) -> Vector2:
	for i in 6:
		var over := p.dot(normal(i)) - (A - inset)
		if over > 0:
			p -= normal(i) * over
	return p


# --- 1. Water along each edge ------------------------------------------------

## [t0, t1] of edge i that is water, or an empty array.
## widths[i] is the river's width where it crosses edge i (both tiles on an edge pass the same width).
static func edge_interval(water: Array, i: int, widths: Array = []) -> Array:
	if not water[i]:
		return []
	var start_tri: bool = water[posmod(i - 1, 6)]
	var end_tri: bool = water[(i + 1) % 6]
	if not (start_tri or end_tri):
		var half: float = (widths[i] if not widths.is_empty() else RIVER_WIDTH) / R / 2.0
		return [0.5 - half, 0.5 + half]
	return [0.0 if start_tri else LAKE_MARGIN, 1.0 if end_tri else 1.0 - LAKE_MARGIN]


static func is_lake(water: Array) -> bool:
	for i in 6:
		if water[i] and water[(i + 1) % 6]:
			return true
	return false


# --- 2. Shores ---------------------------------------------------------------

static func bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, n := SAMPLES) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for k in n + 1:
		var t := float(k) / n
		var u := 1.0 - t
		pts.append(p0 * (u * u * u) + p1 * (3 * u * u * t) + p2 * (3 * u * t * t) + p3 * (t * t * t))
	return pts


static func shore(p: Vector2, edge_p: int, q: Vector2, edge_q: int, sway: Vector2, rng: PyRandom, wobble: float) -> PackedVector2Array:
	var k := minf(maxf(0.5 * (q - p).length(), 0.6), 3.0)
	var c1 := p - normal(edge_p) * k
	var c2 := q - normal(edge_q) * k
	var pts := PackedVector2Array()
	var bz := bezier(p, c1, c2, q)
	for j in bz.size():
		pts.append(bz[j] + sway * pow(sin(PI * j / SAMPLES), 2))
	if wobble != 0.0:
		var phase := rng.uniform(0, 6.28)
		var freq := rng.uniform(2.5, 4.0)
		var out := PackedVector2Array()
		var n := pts.size()
		for m in n:
			var t := float(m) / (n - 1)
			var tan := pts[mini(m + 1, n - 1)] - pts[maxi(m - 1, 0)]
			var l := tan.length()
			var side := Vector2(-tan.y, tan.x) * (1.0 / (l if l != 0.0 else 1.0))
			out.append(pts[m] + side * (wobble * sin(phase + freq * t * PI) * sin(t * PI)))
		pts = out
	for m in pts.size():
		pts[m] = clamp_inside(pts[m])
	return pts


static func circle(centre: Vector2, radius: float, rng: PyRandom, wobble: float, n := 20) -> PackedVector2Array:
	var phase := rng.uniform(0, 6.28)
	var out := PackedVector2Array()
	for k in n:
		var a := TAU * k / n
		out.append(centre + Vector2(cos(a), sin(a)) * (radius * (1 + wobble * sin(3 * a + phase))))
	return out


static func _closed(ring: PackedVector2Array) -> PackedVector2Array:
	var c := ring.duplicate()
	c.append(ring[0])
	return c


## Water outlines and shore curves for one tile, as a Dictionary:
## outlines (Array of PackedVector2Array), shores (same), kind ("pond", "spring", "river", "lake"),
## ends (Array of [start edge, end edge], -1 for a pond end).
## River width at each edge: a delta's width only where both tiles are delta, so the two always agree.
## own and neighbours[i] are terrain or variant names (or null).
static func edge_widths(own: String, neighbours: Array) -> Array:
	var out := []
	for n in neighbours:
		out.append(DELTA_WIDTH if own == "delta" and n == "delta" else RIVER_WIDTH)
	return out


static func tile_water(water: Array, seed: String, widths: Array = []) -> Dictionary:
	var rng := PyRandom.new(seed)
	var sway_angle := rng.uniform(0, TAU)
	var sway := Vector2(cos(sway_angle), sin(sway_angle)) * (rng.uniform(0.4, 1.0) * MEANDER)

	if not water.has(true):
		var ring := circle(Vector2.ZERO, 1.7, rng, 0.12)
		return {outlines = [ring], shores = [_closed(ring)], kind = "pond", ends = [[-1, -1]]}

	var spans := []
	for i in 6:
		var iv := edge_interval(water, i, widths)
		if not iv.is_empty():
			spans.append([i, iv])
	var lake := is_lake(water)

	if spans.size() == 1 and not lake:
		var i: int = spans[0][0]
		var t0: float = spans[0][1][0]
		var t1: float = spans[0][1][1]
		var n := normal(i)
		var pond_at := n * -0.6
		var p := edge_point(i, t1)
		var q := edge_point(i, t0)
		var bank_a := shore(p, i, pond_at + Vector2(-n.y, n.x) * 0.7, i, sway, rng, 0)
		var bank_b := shore(pond_at + Vector2(n.y, -n.x) * 0.7, i, q, i, sway, rng, 0)
		var channel := PackedVector2Array([edge_point(i, t0), edge_point(i, t1)])
		channel.append_array(bank_a.slice(1))
		channel.append_array(bank_b.slice(0, bank_b.size() - 1))
		var pond := circle(pond_at + sway, 1.3, rng, 0.12)
		return {outlines = [channel, pond], shores = [bank_a, bank_b, _closed(pond)], kind = "spring",
				ends = [[i, -1], [-1, i], [-1, -1]]}

	# Walk round the edge, merging stretches that meet at a water corner.
	var runs := []
	for span in spans:
		var i: int = span[0]
		var t0: float = span[1][0]
		var t1: float = span[1][1]
		var pts := PackedVector2Array([edge_point(i, t0), edge_point(i, t1)])
		if not runs.is_empty() and runs[-1].end_edge == i - 1 and runs[-1].end_t == 1.0 and t0 == 0.0:
			runs[-1].pts.append_array(pts.slice(1))
			runs[-1].end_edge = i
			runs[-1].end_t = t1
		else:
			runs.append({start_edge = i, start_t = t0, end_edge = i, end_t = t1, pts = pts})
	if runs.size() > 1 and runs[-1].end_edge == 5 and runs[-1].end_t == 1.0 \
			and runs[0].start_edge == 0 and runs[0].start_t == 0.0:
		var last: Dictionary = runs.pop_back()
		var merged: PackedVector2Array = last.pts.duplicate()
		merged.append_array(runs[0].pts.slice(1))
		runs[0].pts = merged
		runs[0].start_edge = last.start_edge
		runs[0].start_t = last.start_t
	if runs.size() == 1 and spans.size() == 6 and spans.all(func(s): return s[1][0] == 0.0 and s[1][1] == 1.0):
		var hexagon := PackedVector2Array()
		for i in 6:
			hexagon.append(corner(i))
		return {outlines = [hexagon], shores = [], kind = "lake", ends = []}

	var outline := PackedVector2Array()
	var shores := []
	var ends := []
	for k in runs.size():
		var run: Dictionary = runs[k]
		var nxt: Dictionary = runs[(k + 1) % runs.size()]
		outline.append_array(run.pts)
		var curve := shore(run.pts[-1], run.end_edge, nxt.pts[0], nxt.start_edge,
				sway if not lake else sway * 0.4, rng, WOBBLE if lake else 0.0)
		outline.append_array(curve.slice(1, curve.size() - 1))
		shores.append(curve)
		ends.append([run.end_edge, nxt.start_edge])
	return {outlines = [outline], shores = shores, kind = "lake" if lake else "river", ends = ends}


# --- 3. Flow -------------------------------------------------------------------

## Placeholder flow rule from water.py: water flows toward higher values (down the screen).
static func downhill(q: int, r: int) -> float:
	return r - 0.3 * q


static func flow_signs(ends: Array, inflow: Array) -> Array:
	var signs := []
	for e in ends:
		var a: int = e[0]
		var b: int = e[1]
		if a < 0 and b < 0:
			signs.append(0)
		elif b < 0:
			signs.append(1 if inflow[a] else -1)
		elif a < 0:
			signs.append(-1 if inflow[b] else 1)
		elif inflow[a] and not inflow[b]:
			signs.append(1)
		elif inflow[b] and not inflow[a]:
			signs.append(-1)
		else:
			signs.append(0)
	return signs


static func point_in(poly: PackedVector2Array, p: Vector2) -> bool:
	var inside := false
	var n := poly.size()
	for k in n:
		var a := poly[k]
		var b := poly[posmod(k - 1, n)]
		if (a.y > p.y) != (b.y > p.y) and p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x:
			inside = not inside
	return inside


static func bank_strip(curve: PackedVector2Array, d: float) -> Array:
	var n := curve.size()
	var outs := PackedVector2Array()
	for k in n:
		var tan := curve[mini(k + 1, n - 1)] - curve[maxi(k - 1, 0)]
		var l := tan.length()
		outs.append(curve[k] + Vector2(tan.y, -tan.x) * (d / (l if l != 0.0 else 1.0)))
	var quads := []
	for k in n - 1:
		quads.append(PackedVector2Array([curve[k], outs[k], outs[k + 1], curve[k + 1]]))
	return quads


# --- 4. Dressing -----------------------------------------------------------------

## Reeds, rocks, lilies, jetties ([point, angle]) and boats ([point, angle]).
static func dressing(outlines: Array, shores: Array, kind: String, seed: String) -> Dictionary:
	var rng := PyRandom.new(seed + "-dress")
	var reeds := []; var rocks := []; var lilies := []; var jetties := []; var boats := []
	for curve: PackedVector2Array in shores:
		for k in range(2, curve.size() - 2, 3):
			var tan := curve[k + 1] - curve[k - 1]
			if tan.length() < 1e-6:
				continue
			var out := Vector2(tan.y, -tan.x) / tan.length()
			var r := rng.random()
			if r < 0.4:
				reeds.append(clamp_inside(curve[k] + out * 0.2, 0.2))
			elif r < 0.5:
				rocks.append(clamp_inside(curve[k] + out * 0.25, 0.3))
			elif r < 0.7 and kind in ["lake", "pond"]:
				lilies.append(curve[k] - out * 0.6)
	if kind == "lake" and not shores.is_empty() and rng.random() < 0.5:
		var curve: PackedVector2Array = shores[0]
		for c: PackedVector2Array in shores:
			if c.size() > curve.size():
				curve = c
		var k := curve.size() / 2
		var tan := curve[k + 1] - curve[k - 1]
		var l := tan.length()
		var inward := Vector2(-tan.y, tan.x) / (l if l != 0.0 else 1.0)
		jetties.append([curve[k], atan2(inward.y, inward.x)])
	if kind in ["lake", "pond"] and rng.random() < 0.6:
		var poly: PackedVector2Array = outlines[0]
		for _t in 60:
			var p := Vector2(rng.uniform(-A, A), rng.uniform(-R, R))
			if point_in(poly, p) and _clear_of_shores(p, shores):
				boats.append([p, rng.uniform(0, TAU)])
				break
	return {reeds = reeds, rocks = rocks, lilies = lilies, jetties = jetties, boats = boats}


static func _clear_of_shores(p: Vector2, shores: Array) -> bool:
	for c: PackedVector2Array in shores:
		for k in range(0, c.size(), 2):
			if (p - c[k]).length() <= 1.0:
				return false
	return true


## Python's round(): halves go to the even neighbour.
static func py_round(x: float) -> int:
	var f := floorf(x)
	var d := x - f
	if d > 0.5 or (d == 0.5 and int(f) % 2 != 0):
		return int(f) + 1
	return int(f)


## River delta extras: sandy islands splitting the channel, and a busier waterway (more boats, a jetty with
## cargo crates). Returns {islands = outlines, boats = [point, angle], jetties = [point, angle]}.
static func delta_dressing(outlines: Array, shores: Array, kind: String, seed: String) -> Dictionary:
	var rng := PyRandom.new(seed + "-delta")
	var islands := []; var boats := []; var jetties := []
	if kind == "river" and shores.size() == 2:
		# The channel's middle line, halfway between its two banks.
		var a: PackedVector2Array = shores[0]
		var b: PackedVector2Array = shores[1].duplicate()
		b.reverse()
		var mid := PackedVector2Array()
		for k in mini(a.size(), b.size()):
			mid.append((a[k] + b[k]) * 0.5)
		var n := mid.size() - 1
		for k in [py_round(n * 0.3), py_round(n * 0.7)]:
			var tan := mid[k + 1] - mid[k - 1]
			var ang := atan2(tan.y, tan.x)
			var long_ := rng.uniform(1.1, 1.5)
			var wide := rng.uniform(0.32, 0.45)
			var island := PackedVector2Array()
			for j in 14:
				var t := TAU * j / 14
				island.append(mid[k] + Vector2(cos(ang) * long_ * cos(t) - sin(ang) * wide * sin(t),
						sin(ang) * long_ * cos(t) + cos(ang) * wide * sin(t)))
			islands.append(island)
		for k in [py_round(n * 0.12), py_round(n * 0.5)]:  # boats in the side channels and below the islands
			var tan := mid[k + 1] - mid[k - 1]
			var l := tan.length()
			var side := Vector2(-tan.y, tan.x) * (0.55 / (l if l != 0.0 else 1.0)) if k == py_round(n * 0.5) else Vector2.ZERO
			boats.append([mid[k] + side, atan2(tan.y, tan.x)])
		var k := n / 2
		var tan := a[k + 1] - a[k - 1]
		var l := tan.length()
		var inward := Vector2(-tan.y, tan.x) / (l if l != 0.0 else 1.0)
		jetties.append([a[k], atan2(inward.y, inward.x)])
	elif kind == "lake" and not outlines.is_empty():
		var poly: PackedVector2Array = outlines[0]
		for _t in 80:
			if islands.size() >= 2:
				break
			var p := Vector2(rng.uniform(-A, A), rng.uniform(-R, R))
			if not point_in(poly, p):
				continue
			var clear := true
			for c: PackedVector2Array in shores:
				for j in range(0, c.size(), 2):
					if (p - c[j]).length() <= 1.3:
						clear = false
			for isl: PackedVector2Array in islands:
				if (p - isl[0]).length() <= 2.0:
					clear = false
			if clear:
				islands.append(circle(p, rng.uniform(0.45, 0.7), rng, 0.2))
	return {islands = islands, boats = boats, jetties = jetties}
