class_name Water
extends RefCounted
## Port of art/scripts/water.py (rules: design/07 Presentation.md -> Art direction -> Water flows freely).
## Line by line, in one tile's own plan coordinates (pointy-top, centre at the origin, edge 0 facing +X).
## PyRandom makes the seeded curves and dressing identical to the Blender reference.

const RIPPLE_TILE := 8.9         # metres the water shader's baked ripples cover (shaders/water.gdshader: TILE)
const RIPPLE_SLOPE := 4.0        # the slopes they can hold (SLOPE_RANGE)
const R := 4.5
const A := R * sqrt(3.0) / 2.0
const RIVER_WIDTH := 1.5
const DELTA_WIDTH := 3.0        # river delta (tier 1 river variant): wider, with sandy islands
const LAKE_MARGIN := 0.25
const MEANDER := 0.9
const WOBBLE := 0.18
const SAMPLES := 18
const SWERVE := 1.12             # how far a delta's route swings round each island
const LAKE_WIDTH := 3.4          # great lake: tiles join into one body, nearly a whole edge wide
const STILL_WIDTH := 2.8         # still waters: broad, calm pools
const FALL_WIDTH := 1.501        # a plain river's width, on a rapids tile's edge where the rapids flow out into it: the gorge ends in a pool there, with a waterfall (Gorge)
const POOL_BACK := 1.75          # that pool: its middle's distance from the edge
const POOL_RADIUS := 1.45        # and its size
const RAPIDS_WIDTH := 1.4        # rapids: a narrow gorge, always a channel, even round a triangle of tiles
const RAPIDS_POOL := 0.85        # where a gorge starts: no wide pools
const BROAD := {"great_lake": 0.7, "still_waters": 1.05}   # styles drawn as one body, and how far their shore stands in
## Water tile names and landmarks -> their style. Both tiles on an edge must share a style for its width to apply.
const FAMILY := {"delta": "delta", "riverport": "delta", "great_lake": "great_lake", "serpentlair": "great_lake",
	"rapids": "rapids", "trollbridge": "rapids", "still_waters": "still_waters", "meditationrock": "still_waters"}
const WIDTH := {"delta": DELTA_WIDTH, "great_lake": LAKE_WIDTH, "rapids": RAPIDS_WIDTH, "still_waters": STILL_WIDTH}
const WATER_MAT := {"great_lake": "water_deep", "rapids": "water_fast", "still_waters": "water_still"}


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


static func inside_tile(p: Vector2, margin := 0.0) -> bool:
	for i in 6:
		if p.dot(normal(i)) > A - margin:
			return false
	return true


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
	var width: float = widths[i] if not widths.is_empty() else RIVER_WIDTH
	if width == FALL_WIDTH:
		width = RIVER_WIDTH
	if width == RAPIDS_WIDTH or not (start_tri or end_tri):
		var half: float = width / R / 2.0
		return [0.5 - half, 0.5 + half]
	var margin: float = (1.0 - width / R) / 2.0 if width in [LAKE_WIDTH, STILL_WIDTH] else LAKE_MARGIN
	return [0.0 if start_tri else margin, 1.0 if end_tri else 1.0 - margin]


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


static func _wobbled(pts: PackedVector2Array, rng: PyRandom, wobble: float) -> PackedVector2Array:
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
	return out


## A shore that keeps inset in from the tile's land edges, anticlockwise from p to q, so the water fills the tile. It
## leaves each edge square-on, then rounds each corner it passes (three rounds of corner cutting).
static func broad_shore(p: Vector2, edge_p: int, q: Vector2, edge_q: int, inset: float, rng: PyRandom, wobble: float) -> PackedVector2Array:
	var last := edge_q if edge_q > edge_p else edge_q + 6
	var ctrl := PackedVector2Array([p, p - normal(edge_p) * inset])
	for e in range(edge_p, last):
		ctrl.append(corner(e % 6) * (1.0 - inset * 1.15 / R))
	ctrl.append(q - normal(edge_q) * inset)
	ctrl.append(q)
	for _r in 3:
		var fine := PackedVector2Array([ctrl[0]])
		for k in ctrl.size() - 1:
			fine.append(ctrl[k] * 0.75 + ctrl[k + 1] * 0.25)
			fine.append(ctrl[k] * 0.25 + ctrl[k + 1] * 0.75)
		fine.append(ctrl[-1])
		ctrl = fine
	var out := _wobbled(ctrl, rng, wobble)
	for m in out.size():
		out[m] = clamp_inside(out[m])
	return out


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
## River width at each edge: a variant's width only where both tiles are that variant, so the two always agree.
## own and neighbours[i] are terrain or variant names (or null).
static func edge_widths(own: String, neighbours: Array) -> Array:
	var style = FAMILY.get(own)
	var out := []
	for n in neighbours:
		out.append(WIDTH[style] if style != null and FAMILY.get(n) == style else RIVER_WIDTH)
	return out


static func falling(widths: Array, i: int) -> bool:
	return not widths.is_empty() and widths[i] == FALL_WIDTH


## A rapids tile's widths, marking the plain river or lake edges its water flows out through (downhill): water can't climb
## out of a gorge, so those get a pool and a waterfall.
static func with_falls(widths: Array, water: Array, q: int, r: int) -> Array:
	var here := downhill(q, r)
	var out := []
	for i in 6:
		var n: Vector2i = Hex.NEIGHBOURS[i]
		out.append(FALL_WIDTH if water[i] and widths[i] != RAPIDS_WIDTH and downhill(q + n.x, r + n.y) > here else widths[i])
	return out


## A rapids shore, pushed out round each fall's pool.
static func pooled(curve: PackedVector2Array, widths: Array) -> PackedVector2Array:
	var out := curve
	for i in 6:
		if falling(widths, i):
			var c := normal(i) * (A - POOL_BACK)
			var pushed := PackedVector2Array()
			for k in out.size():
				var d := out[k] - c
				var ln := d.length()
				pushed.append(c + d * (POOL_RADIUS / ln) if k > 0 and k < out.size() - 1 and ln > 1e-6 and ln < POOL_RADIUS else out[k])
			out = pushed
	return out


static func tile_water(water: Array, seed: String, widths: Array = [], style := "") -> Dictionary:
	var rng := PyRandom.new(seed)
	var sway_angle := rng.uniform(0, TAU)
	var sway := Vector2(cos(sway_angle), sin(sway_angle)) * (rng.uniform(0.4, 1.0) * MEANDER)

	var inset: float = BROAD.get(style, 0.0)
	if not water.has(true):
		var ring := circle(Vector2.ZERO, A - inset if inset != 0.0 else (RAPIDS_POOL if style == "rapids" else 1.7), rng, 0.06 if inset != 0.0 else 0.12)
		return {outlines = [ring], shores = [_closed(ring)], kind = "pond", ends = [[-1, -1]]}

	var spans := []
	for i in 6:
		var iv := edge_interval(water, i, widths)
		if not iv.is_empty():
			spans.append([i, iv])
	var lake := (is_lake(water) or inset != 0.0) and style != "rapids"

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
		if style == "rapids":   # no pool: the gorge just ends, in a rounded head
			var side := Vector2(-n.y, n.x)
			var half := (t1 - t0) * R / 2.0
			var a_ := pond_at + side * (half if (p - q).dot(side) > 0 else -half)   # on p's side
			var b_ := pond_at + (pond_at - a_)
			bank_a = bezier(p, p - n * 1.3, a_ + n * 1.3, a_, 14)   # running straight in to the head, so no overshoot where they meet
			bank_b = bezier(b_, b_ + n * 1.3, q - n * 1.3, q, 14)
			var start := (a_ - pond_at).angle()
			var way := 1.0 if Vector2(cos(start + 1.57), sin(start + 1.57)).dot(n) < 0 else -1.0
			var curve := bank_a.duplicate()
			for k in range(1, 6):
				curve.append(pond_at + Vector2.from_angle(start + way * PI * k / 6.0) * half)
			curve.append_array(bank_b)
			curve = pooled(curve, widths)
			var outline := PackedVector2Array([edge_point(i, t0), edge_point(i, t1)])
			outline.append_array(curve.slice(1, curve.size() - 1))
			return {outlines = [outline], shores = [curve], kind = "spring", ends = [[i, i]]}
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
		var curve: PackedVector2Array
		if inset != 0.0:
			curve = broad_shore(run.pts[-1], run.end_edge, nxt.pts[0], nxt.start_edge, inset, rng, WOBBLE)
		else:
			curve = shore(run.pts[-1], run.end_edge, nxt.pts[0], nxt.start_edge,
					sway if not lake else sway * 0.4, rng, WOBBLE if lake else 0.0)
		if style == "rapids":
			curve = pooled(curve, widths)
		outline.append_array(curve.slice(1, curve.size() - 1))
		shores.append(curve)
		ends.append([run.end_edge, nxt.start_edge])
	return {outlines = [outline], shores = shores, kind = "lake" if lake else "river", ends = ends}


# --- 3. Flow -------------------------------------------------------------------

## Placeholder flow rule from water.py: water flows toward higher values (down the screen).
static func downhill(q: int, r: int) -> float:
	return r - 0.3 * q


## Which water edges water comes in through, for flow_signs. downhill decides, but a waterfall needs a source: the last river
## tile above one flows toward it, from all its plain river edges, so the far edge is where it parts from the next river
## tile. A lake only turns at the fall's edge. rapids[i]: the tile across edge i is rapids. own: "river", "lake" or "rapids".
static func flow_in(q: int, r: int, water: Array, rapids: Array, own := "river") -> Array:
	var here := downhill(q, r)
	var inflow := []
	var falls := []
	for i in 6:
		var n: Vector2i = Hex.NEIGHBOURS[i]
		var lower := downhill(q + n.x, r + n.y) < here
		inflow.append(lower)
		if water[i] and rapids[i] and lower:
			falls.append(i)
	if own == "rapids":
		for i in 6:
			inflow[i] = inflow[i] or (water[i] and not rapids[i])
		return inflow
	if not falls.is_empty():
		for i in 6:
			inflow[i] = false if i in falls else inflow[i] if rapids[i] or own == "lake" else true
	return inflow


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


static func _middle(shores: Array) -> PackedVector2Array:
	var a: PackedVector2Array = shores[0]
	var b: PackedVector2Array = shores[1]
	var mid := PackedVector2Array()
	for k in mini(a.size(), b.size()):
		mid.append((a[k] + b[b.size() - 1 - k]) * 0.5)
	return mid


## A delta channel's route: its middle line, swinging to one side of the first island and the other side of the second.
static func swung(mid: PackedVector2Array) -> PackedVector2Array:
	var n := mid.size() - 1
	var out := PackedVector2Array()
	for k in mid.size():
		var tan := mid[mini(k + 1, n)] - mid[maxi(k - 1, 0)]
		var l := tan.length()
		out.append(mid[k] + Vector2(-tan.y, tan.x) * (SWERVE * sin(TAU * k / n) / (l if l != 0.0 else 1.0)))
	return out


## River delta extras: sandy islands splitting the channel, and a busier waterway (more boats, a jetty with
## cargo crates). near: 1 one step from the River Port, 2 two steps, else 0.
## Returns {islands = outlines, boats = [point, angle], jetties = [point, angle]}.
static func delta_dressing(outlines: Array, shores: Array, kind: String, seed: String, near := 0) -> Dictionary:
	var rng := PyRandom.new(seed + "-delta")
	var islands := []; var boats := []; var jetties := []
	if kind == "river" and shores.size() == 2:
		var a: PackedVector2Array = shores[0]
		var b: PackedVector2Array = shores[1].duplicate()
		b.reverse()
		var mid := _middle(shores)
		var n := mid.size() - 1
		for k in [py_round(n * 0.3), py_round(n * 0.7)]:
			var tan := mid[k + 1] - mid[k - 1]
			var ang := atan2(tan.y, tan.x)
			var long_ := rng.uniform(1.1, 1.5)
			var wide := rng.uniform(0.42, 0.58)
			var island := PackedVector2Array()
			for j in 14:
				var t := TAU * j / 14
				island.append(mid[k] + Vector2(cos(ang) * long_ * cos(t) - sin(ang) * wide * sin(t),
						sin(ang) * long_ * cos(t) + cos(ang) * wide * sin(t)))
			islands.append(island)
		var route := swung(mid)
		islands = islands.filter(func(isl):   # on a tight bend, the route comes first
			for p in route:
				if point_in(isl, p):
					return false
			return true)
		var spots := [[py_round(n * 0.5), 1.0], [py_round(n * 0.12), -0.85]]
		if near != 0:
			spots.append([py_round(n * 0.88), 0.85])
		if near == 1:
			spots.append([py_round(n * 0.5), -1.0])
		for spot in spots:
			var k: int = spot[0]
			var tan := mid[k + 1] - mid[k - 1]
			var l := tan.length()
			boats.append([mid[k] + Vector2(-tan.y, tan.x) * (spot[1] / (l if l != 0.0 else 1.0)), atan2(tan.y, tan.x)])
		var k := n / 2
		for sgn in ([1, -1] if near == 1 else [1]):
			var curve := a if sgn == 1 else b
			var tan := curve[k + 1] - curve[k - 1]
			var l := tan.length()
			var inward := Vector2(-tan.y * sgn, tan.x * sgn) * (1.0 / (l if l != 0.0 else 1.0))
			jetties.append([curve[k], atan2(inward.y, inward.x)])
	elif kind == "lake" and not outlines.is_empty():
		var poly: PackedVector2Array = outlines[0]
		for _t in 80:
			if islands.size() >= 2:
				break
			var p := Vector2(rng.uniform(-A, A), rng.uniform(-R, R))
			if not point_in(poly, p) or not inside_tile(p, 0.9):
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


# --- 5. Routes on water and landings ----------------------------------------------
# Water is an obstacle (design/02 -> Obstacles): a party crosses it on a raft, or by an Athletics check, or walks round.

static func _mean(pts: Array) -> Vector2:
	var sum := Vector2.ZERO
	for p: Vector2 in pts:
		sum += p
	return sum / pts.size()


## {hub, lines}: lines[i] is the route on the water from edge i's midpoint to the hub, for each water edge i. No line up or
## down a rapids waterfall: nothing can walk or float over one.
static func water_routes(water: Array, seed: String, widths: Array = [], style := "") -> Dictionary:
	var r := _water_routes(water, seed, widths, style)
	for i in r.lines.keys():
		if falling(widths, i):
			r.lines.erase(i)
	return r


static func _water_routes(water: Array, seed: String, widths: Array = [], style := "") -> Dictionary:
	var w := tile_water(water, seed, widths, style)
	var mids := {}
	for i in 6:
		if water[i]:
			mids[i] = normal(i) * A
	if w.kind == "river" and w.shores.size() == 2:
		var whole := _middle(w.shores)
		var n := whole.size() - 1
		if style == "delta":
			whole = swung(whole)
		var mid := PackedVector2Array()
		if n % 3 == 0 and style != "rapids":   # rapids: a narrow channel, so its line keeps every bend
			for k in range(0, whole.size(), 3):
				mid.append(whole[k])
		else:
			mid = whole
		var h := mid.size() / 2
		var e0: int = w.ends[0][0]
		var e1: int = w.ends[1][0]
		var first := PackedVector2Array([mids[e0]])
		first.append_array(mid.slice(1, h + 1))
		var second := PackedVector2Array([mids[e1]])
		for k in range(mid.size() - 2, h - 1, -1):
			second.append(mid[k])
		return {hub = mid[h], lines = {e0: first, e1: second}}
	var hub := Vector2.ZERO
	if w.kind == "pond" or w.kind == "spring":
		var ring: PackedVector2Array = w.shores[-1]
		hub = _mean(Array(ring.slice(0, ring.size() - 1)))
	elif not in_water(w.outlines, Vector2.ZERO):
		hub = _mean(mids.values())
	var lines := {}
	for i in mids:
		lines[i] = PackedVector2Array([mids[i], hub])
	return {hub = hub, lines = lines}


static func in_water(outlines: Array, p: Vector2) -> bool:
	for o: PackedVector2Array in outlines:
		if point_in(o, p):
			return true
	return false


## lands[i] for each edge i with no water neighbour: [edge midpoint, shore point, point in the water]. A party on the land
## beyond edge i walks from the midpoint to the shore, steps in there, and floats to the hub.
static func landings(water: Array, seed: String, widths: Array = [], style := "") -> Dictionary:
	var outlines: Array = tile_water(water, seed, widths, style).outlines
	var hub: Vector2 = water_routes(water, seed, widths, style).hub
	var lands := {}
	for i in 6:
		if water[i]:
			continue
		var p := normal(i) * A
		var d := hub - p
		var s := hub
		for k in 81:
			if in_water(outlines, p + d * (k / 80.0)):
				s = p + d * (k / 80.0)
				break
		var l := d.length()
		lands[i] = [p, s, s + d * minf(0.35 / (l if l != 0.0 else 1.0), 1.0)]
	return lands


static func clear_of_landings(points: Array, lands: Dictionary, r := 0.5) -> Array:
	return points.filter(func(p):
		for i in lands:
			if (p - lands[i][1]).length() <= r:
				return false
		return true)


static func seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var d := b - a
	var dd := d.dot(d)
	var t := clampf((p - a).dot(d) / (dd if dd != 0.0 else 1.0), 0.0, 1.0)
	return (p - (a + d * t)).length()


static func _line_dist(p: Vector2, lines: Dictionary) -> float:
	var best := INF
	for i in lines:
		var l: PackedVector2Array = lines[i]
		for k in l.size() - 1:
			best = minf(best, seg_dist(p, l[k], l[k + 1]))
	return best


static func clear_of_routes(spots: Array, lines: Dictionary, r := 0.75) -> Array:
	return spots.filter(func(s): return _line_dist(s[0], lines) > r)


# --- 6. The River Port -------------------------------------------------------------

const QUAY_X := 0.9
const HARBOUR := Vector2(2.2, 2.85)       # how far the harbour reaches out from the quay's middle, and along it
const PORT_STOP := Vector2(0.62, 0)       # on the quay, where the party stops; the land routes all end here
const PORT_FLOAT := Vector2(2.3, 0)       # in the harbour, where the water routes all end
const GATE_STEPS := 0.6                   # how far along a back edge a water gate's steps are from the edge's midpoint
const GATE_WALL := Vector2(1.33, 1.25)    # how far a water gate's own wall runs each way along the edge


## How many 60 degree steps to turn the port: the harbour faces as much water as it can, and the town's back as much
## land, so a party on foot can reach it. Ties by the tile's seed.
static func port_turn(water: Array, seed: String) -> int:
	var rng := PyRandom.new(seed + "-port")
	var best := [-1, -1.0]
	var turn := 0
	for t in 6:
		var front := 0
		for k in [-1, 0, 1]:
			front += 1 if water[posmod(t + k, 6)] else 0
		var back := 0
		for k in [2, 3, 4]:
			back += 0 if water[(t + k) % 6] else 1
		var score := [2 * front + 3 * mini(back, 1) + back, rng.random()]
		if score > best:
			best = score
			turn = t
	return turn


static func turned(p: Vector2, t: int) -> Vector2:
	var a := deg_to_rad(60.0 * t)
	return Vector2(p.x * cos(a) - p.y * sin(a), p.x * sin(a) + p.y * cos(a))


## [the harbour's outline, its shore], in the tile's frame, for the port turned t steps.
static func port_water(t: int) -> Array:
	var arc := PackedVector2Array()
	for k in 25:
		var a := deg_to_rad(-90.0 + 180.0 * k / 24)
		arc.append(turned(Vector2(QUAY_X + HARBOUR.x * cos(a), HARBOUR.y * sin(a)), t))
	var outline := PackedVector2Array([turned(Vector2(QUAY_X - 0.3, -HARBOUR.y), t)])
	outline.append_array(arc)
	outline.append(turned(Vector2(QUAY_X - 0.3, HARBOUR.y), t))
	return [outline, arc]


## The part of a polygon in front of the quay's line, for the port turned t steps.
static func clip_to_quay(poly: PackedVector2Array, t: int) -> PackedVector2Array:
	var out := PackedVector2Array()
	var n := poly.size()
	for k in n:
		var b := poly[k]
		var a := poly[posmod(k - 1, n)]
		var da := turned(a, -t).x - QUAY_X
		var db := turned(b, -t).x - QUAY_X
		if (da < 0) != (db < 0):
			out.append(a + (b - a) * (da / (da - db)))
		if db >= 0:
			out.append(b)
	return out


## The port's water: {outlines, quads}, with what lies behind the quay's line taken away and the harbour added.
static func port_shape(water: Array, seed: String, widths: Array, t: int) -> Dictionary:
	var w := tile_water(water, seed, widths)
	var harbour := port_water(t)
	var outs := []
	for o: PackedVector2Array in w.outlines:
		var c := clip_to_quay(o, t)
		if c.size() > 2:
			outs.append(c)
	outs.append(clip_to_quay(harbour[0], t))
	var quads := []
	for c: PackedVector2Array in w.shores:
		quads.append_array(bank_strip(c, 0.22))
	var arc: PackedVector2Array = harbour[1].duplicate()
	arc.reverse()
	quads.append_array(bank_strip(arc, 0.22))
	var kept := []
	for q: PackedVector2Array in quads:
		var c := clip_to_quay(q, t)
		if c.size() > 2:
			kept.append(c)
	return {outlines = outs, quads = kept}


## The stone walls where the port's land meets water, as [a, b] segments in the tile's frame.
static func port_walls(water: Array, seed: String, widths: Array, t: int) -> Array:
	var outs: Array = port_shape(water, seed, widths, t).outlines
	var runs := []
	var on = null
	var n := 80
	var half := R - QUAY_X * tan(deg_to_rad(30.0))
	for k in n + 1:
		var y := -half + 2 * half * k / n
		var wet := in_water(outs, turned(Vector2(QUAY_X + 0.05, y), t))
		if wet and on == null:
			on = y
		if on != null and (not wet or k == n):
			runs.append([on, y])
			on = null
	var walls := []
	for r in runs:
		walls.append([turned(Vector2(QUAY_X - 0.04, r[0]), t), turned(Vector2(QUAY_X - 0.04, r[1]), t)])
	for k in 6:
		var iv := edge_interval(water, (k + t) % 6, widths)
		if iv.is_empty():
			continue
		var nk := normal(k)
		var at := func(y: float) -> Vector2: return nk * (A - 0.12) + Vector2(-nk.y, nk.x) * y
		var low := PackedFloat32Array()
		var high := PackedFloat32Array()
		for ix in 41:
			var y: float = (iv[0] + (iv[1] - iv[0]) * ix / 40.0 - 0.5) * R
			if at.call(y).x < QUAY_X and (not k in [2, 3, 4] or not (-GATE_WALL.x < y and y < GATE_WALL.y)):
				(low if y < 0 else high).append(y)
		for side in [low, high]:
			if side.size() > 1 and side[-1] - side[0] > 0.05:
				walls.append([turned(at.call(side[0]), t), turned(at.call(side[-1]), t)])
	return walls


## The port's routes, in the tile's frame: {land, floats}. land[i] walks from a land edge i's midpoint to PORT_STOP, or for
## a back edge with water, from the water gate. floats[i] floats from a front water edge i's midpoint to PORT_FLOAT.
static func port_routes(water: Array, t: int) -> Dictionary:
	var land := {}
	var floats := {}
	var alley := [Vector2(-1.55, 0), PORT_STOP]
	for k in 6:
		var i := (k + t) % 6
		var mid := normal(k) * A
		var line := []
		if k in [2, 3, 4]:
			line = [mid] + alley
			if water[i]:
				var along := Vector2(-normal(k).y, normal(k).x)
				var step := normal(k) * (A - 0.6) + along * GATE_STEPS
				line = [mid, step, Vector2(alley[0].x, step.y * 0.9)] + alley
		elif water[i]:
			line = [mid, PORT_FLOAT] if k == 0 else [mid, Vector2(2.8, 1.7 if k == 1 else -1.7), PORT_FLOAT]
			floats[i] = _turned_line(line, t)
			continue
		elif k == 0:
			line = [mid, Vector2(3.3, 1.9), Vector2(2.2, 3.1), Vector2(0.62, 3.05), PORT_STOP]
		else:
			var sd := 1.0 if k == 1 else -1.0
			line = [mid, Vector2(2.2, 3.1 * sd), Vector2(0.62, 3.05 * sd), PORT_STOP]
		land[i] = _turned_line(line, t)
	return {land = land, floats = floats}


static func _turned_line(line: Array, t: int) -> PackedVector2Array:
	var out := PackedVector2Array()
	for p: Vector2 in line:
		out.append(turned(p, t))
	return out


# --- 7. Rapids: white water and bridges ---------------------------------------------

const BRIDGE_HALF := 2.35    # half the length of a rapids_bridge, from ground to ground over the gorge
const TROLL_HALF := 3.1      # half the length of the Troll Bridge
const BRIDGE_OPEN := 0.85    # half the width of its arch
const TROLL_OPEN := 1.42     # and the Troll Bridge's
const BRIDGE_CHANCE := 0.35  # the share of rapids tiles that have a bridge, where one fits


## The land edges either side of water edge i, going each way round to the next water edge.
static func land_sides(water: Array, i: int) -> Array:
	if water.count(true) == 1:
		return [[(i + 1) % 6, (i + 2) % 6, (i + 3) % 6], [posmod(i - 1, 6), posmod(i - 2, 6)]]
	var sides := []
	for s_ in [1, -1]:
		var side := []
		for d in range(1, 6):
			var e := posmod(i + s_ * d, 6)
			if water[e]:
				break
			side.append(e)
		sides.append(side)
	return sides


## {middle, angle, routes}, or {} if no bridge fits. routes[e] walks from land edge e's midpoint to the nearer end.
static func bridge_spot(water: Array, seed: String, widths: Array = [], half := BRIDGE_HALF) -> Dictionary:
	var w := tile_water(water, seed, widths, "rapids")
	var outlines := Gorge.cut_outlines(water, seed, widths)   # both ends on the land beyond the cut
	if outlines.is_empty():
		return {}
	var wet := []
	for i in 6:
		if water[i]:
			wet.append(i)
	var tries := []
	if w.kind == "river" and wet.size() == 2 and w.shores.size() == 2:
		var mid := _middle(w.shores)
		var n := mid.size() - 1
		var ks := range(py_round(n * 0.25), py_round(n * 0.75) + 1)
		# Python's sort keeps ties in order, and Godot's doesn't: the index breaks them.
		ks.sort_custom(func(a, b): return mid[a].length() < mid[b].length() or (mid[a].length() == mid[b].length() and a < b))
		for k in ks:
			var tan := mid[k + 1] - mid[k - 1]
			var l := tan.length()
			tries.append([wet[0], mid[k], Vector2(-tan.y, tan.x) * (1.0 / (l if l != 0.0 else 1.0))])
	else:
		var keys := {}
		for e in wet:
			keys[e] = PyRandom.new("%s-arm%d" % [seed, e]).random()
		var order := wet.duplicate()
		order.sort_custom(func(a, b): return keys[a] < keys[b])
		for i: int in order:
			for d in [1.6, 1.3, 1.9, 2.2]:
				var n := normal(i)
				tries.append([i, n * (A - d), Vector2(-n.y, n.x)])
	for attempt in tries:
		var i: int = attempt[0]
		var c: Vector2 = attempt[1]
		var axis: Vector2 = attempt[2]
		var sides := land_sides(water, i)
		var after: Array = sides[0]
		var before: Array = sides[1]
		if after.is_empty() or before.is_empty():
			continue
		var sum := Vector2.ZERO
		for e in after:
			sum += normal(e)
		if axis.dot(sum) < 0:
			axis = -axis
		var end_a := c + axis * half
		var end_b := c - axis * half
		if in_water(outlines, c + axis * (half - 0.35)) or in_water(outlines, c - axis * (half - 0.35)):
			continue
		if not inside_tile(end_a, 0.1) or not inside_tile(end_b, 0.1) or in_water(outlines, end_a) or in_water(outlines, end_b):
			continue
		var routes := {}
		for e in after:
			routes[e] = PackedVector2Array([normal(e) * A, end_a])
		for e in before:
			routes[e] = PackedVector2Array([normal(e) * A, end_b])
		var clear := true
		for e in routes:
			for k in 13:
				if in_water(outlines, routes[e][0] + (routes[e][1] - routes[e][0]) * (k / 12.0)):
					clear = false
		if not clear:
			continue
		return {middle = c, angle = atan2(axis.y, axis.x), routes = routes}
	return _bridge_search(water, w.outlines, outlines, half)


## Where the channel's shape leaves bridge_spot's usual tries no room: any line over one channel, near the tile's middle, whose
## water fits under the arch, with each land edge a dry walk from one end. A plain bridge must join land on both sides; the
## Troll's may end on a spit, since it's a place in itself.
static func _bridge_search(water: Array, wet_outlines: Array, outlines: Array, half: float) -> Dictionary:
	var land := []
	for e in 6:
		if not water[e]:
			land.append(e)
	if land.is_empty():
		return {}
	var arch := (BRIDGE_OPEN if half <= BRIDGE_HALF else TROLL_OPEN) * 2.0 - 0.05
	var spots := []
	for x in range(-10, 11):
		for y in range(-10, 11):
			spots.append(Vector2(x * 0.4, y * 0.4))
	# Python's sort keeps ties in order (x, then y), and Godot's doesn't: they break ties the same way here.
	spots.sort_custom(func(a, b): return snappedf(a.length_squared(), 0.0001) < snappedf(b.length_squared(), 0.0001) \
			or (snappedf(a.length_squared(), 0.0001) == snappedf(b.length_squared(), 0.0001) and (a.x < b.x or (a.x == b.x and a.y < b.y))))
	var firm_by := half - 0.35
	var dry := func(a: Vector2, b: Vector2) -> bool:
		for k in 13:
			if in_water(outlines, a + (b - a) * (k / 12.0)):
				return false
		return true
	for c: Vector2 in spots:
		if not inside_tile(c, 0.5) or not in_water(wet_outlines, c):
			continue
		for k in 12:
			var axis := Vector2.from_angle(PI * k / 12.0)
			var ends := [c + axis * half, c - axis * half]
			if in_water(outlines, c + axis * firm_by) or in_water(outlines, c - axis * firm_by) or in_water(outlines, ends[0]) or in_water(outlines, ends[1]):
				continue
			if not inside_tile(ends[0], 0.1) or not inside_tile(ends[1], 0.1):
				continue
			var wet_n := 0
			for j in 41:
				if in_water(wet_outlines, c + axis * (-half + 2.0 * half * j / 40.0)):
					wet_n += 1
			if wet_n * 2.0 * half / 40.0 > arch:
				continue
			var routes := {}
			var used := {}
			var ok := true
			for e: int in land:
				var mid := normal(e) * A
				var near: Array = ends if (ends[0] - mid).length() <= (ends[1] - mid).length() else [ends[1], ends[0]]
				var way = null
				for q: Vector2 in near:
					if dry.call(mid, q):
						way = q
						break
				if way == null:
					ok = false
					break
				routes[e] = PackedVector2Array([mid, way])
				used[way] = true
			if ok and (half > BRIDGE_HALF or used.size() == 2):
				return {middle = c, angle = atan2(axis.y, axis.x), routes = routes}
	return {}


## This tile's bridge, as bridge_spot gives it, or {}. Landmark: the Troll Bridge. Otherwise some tiles have one (design/02).
static func rapids_spot(water: Array, seed: String, widths: Array = [], landmark := false) -> Dictionary:
	if landmark:
		return bridge_spot(water, seed, widths, TROLL_HALF)
	if PyRandom.new(seed + "-bridge").random() < BRIDGE_CHANCE:
		return bridge_spot(water, seed, widths)
	return {}


## {foam = [point, angle, long, wide, held by a boulder], boulders = [point, radius]} in the channel. near: closer to the Troll Bridge, more.
static func rapids_marks(water: Array, seed: String, widths: Array = [], near := 0) -> Dictionary:
	var w := tile_water(water, seed, widths, "rapids")
	var lines: Dictionary = water_routes(water, seed, widths, "rapids").lines
	var rng := PyRandom.new(seed + "-rapids")
	var foam := []
	var boulders := []
	var step := 2 if near != 0 else 3
	for curve: PackedVector2Array in w.shores.slice(0, 6):
		for k in range(2, curve.size() - 2, step):
			var tan := curve[k + 1] - curve[k - 1]
			if tan.length() < 1e-6:
				continue
			var into := Vector2(-tan.y, tan.x) / tan.length()
			var ang := atan2(tan.y, tan.x)
			var p := curve[k] + into * rng.uniform(0.2, 0.34)
			if rng.random() < (0.45 if near != 0 else 0.3) and in_water(w.outlines, p) and inside_tile(p, 0.25) and _line_dist(p, lines) > 0.32:
				var r := rng.uniform(0.12, 0.22)
				boulders.append([p, r])
				var off := Vector2(cos(ang), sin(ang)) * rng.uniform(-0.1, 0.1)
				var long_ := r + rng.uniform(0.2, 0.42)
				foam.append([p + off, ang, long_, r * 0.72, true])
			var q := curve[k] + into * rng.uniform(0.15, 0.6)
			if in_water(w.outlines, q) and inside_tile(q, 0.4):
				var a2 := ang + rng.uniform(-0.2, 0.2)
				var l2 := rng.uniform(0.28, 0.55)
				foam.append([q, a2, l2, rng.uniform(0.04, 0.08), false])
	for i in lines:
		var l: PackedVector2Array = lines[i]
		for k in l.size() - 1:
			var d := l[k + 1] - l[k]
			if d.length() > 0.5 and rng.random() < 0.8:
				var c := l[k] + d * rng.uniform(0.25, 0.75)
				if in_water(w.outlines, c):
					var l2 := rng.uniform(0.3, 0.6)
					foam.append([c, atan2(d.y, d.x), l2, rng.uniform(0.04, 0.09), false])
	return {foam = foam, boulders = boulders}


# --- 8. Lake Serpent's Lair and Meditation Rock: routes --------------------------------

const LAIR_LAND := Vector2(2.75, 0)  # where a raft or a wader reaches the shelf in front of the cave
const LAIR_STOP := Vector2(1.5, 0)   # on the shelf, at the cave's mouth


## routes[i] for all six edges, in the tile's frame, for the Lair turned t steps: from the edge's midpoint to LAIR_LAND.
static func lair_routes(t: int) -> Dictionary:
	var near := Vector2(2.75, 1.05)
	var far := Vector2(1.0, 2.7)
	var back := Vector2(-2.3, 1.9)
	var ways := {0: [], 1: [], 2: [far, near], 3: [back, far, near]}
	var out := {}
	for k in 6:
		var sd := 1.0 if k <= 3 else -1.0
		var line := [normal(k) * A]
		for p: Vector2 in ways[k if k <= 3 else 6 - k]:
			line.append(Vector2(p.x, p.y * sd))
		line.append(LAIR_LAND)
		out[(k + t) % 6] = _turned_line(line, t)
	return out


const ROCK_R := 1.45     # Meditation Rock's radius at the waterline
const STONE_GAP := 0.52  # between stepping stones


## Meditation Rock's routes, in the tile's frame: {land, floats, stones = [point, radius], turn}. turn is -1 with no land neighbour.
static func rock_routes(water: Array, seed: String, widths: Array = []) -> Dictionary:
	var outlines: Array = tile_water(water, seed, widths, "still_waters").outlines
	var rng := PyRandom.new(seed + "-rock")
	var land := {}
	var stones := []
	var floats := {}
	for i in 6:
		if water[i]:
			floats[i] = PackedVector2Array([normal(i) * A, normal(i) * ROCK_R])
	if not water.has(false):
		return {land = land, floats = floats, stones = stones, turn = -1}
	var start := 0
	for i in 6:
		if not water[i] and water[posmod(i - 1, 6)]:
			start = i
			break
	var runs := []
	for d in 6:
		var e := (start + d) % 6
		if water[e]:
			continue
		if not runs.is_empty() and (runs[-1][-1] + 1) % 6 == e:
			runs[-1].append(e)
		else:
			runs.append([e])
	var mains := []
	for run in runs:
		mains.append(run[run.size() / 2])
	for r in runs.size():
		var run: Array = runs[r]
		var main: int = mains[r]
		var n_main := normal(main)
		var mid := n_main * A
		var shore_at := ROCK_R / A
		for k in 81:
			if in_water(outlines, mid * (1.0 - k / 80.0)):
				shore_at = 1.0 - k / 80.0
				break
		var far := A * shore_at + 0.1
		var n := maxi(2, py_round((far - ROCK_R) / STONE_GAP))
		var line := PackedVector2Array()
		for k in n:
			var at := far - (far - ROCK_R) * (k + 0.5) / n
			var side := rng.uniform(-0.1, 0.1)
			var pt := n_main * at + Vector2(-n_main.y, n_main.x) * side
			stones.append([pt, rng.uniform(0.2, 0.27)])
			line.append(pt)
		line.append(Vector2.ZERO)
		var pos := run.find(main)
		var way_main := PackedVector2Array([mid])
		way_main.append_array(line)
		land[main] = way_main
		for j in run.size():
			var e: int = run[j]
			if e == main:
				continue
			var way := PackedVector2Array([normal(e) * A, normal(e) * (A - 0.4)])
			for m in (range(j, pos) if j < pos else range(j - 1, pos - 1, -1)):
				way.append(corner(run[m]) * (1.0 - 0.5 / R))
			way.append(n_main * (A - 0.4))
			way.append_array(line)
			land[e] = way
	return {land = land, floats = floats, stones = stones, turn = mains[0]}


# --- 9. Props on water tiles ---------------------------------------------------------

static func _clear_of(p: Vector2, shores: Array, clear: float) -> bool:
	for c: PackedVector2Array in shores:
		for k in range(0, c.size(), 2):
			if (p - c[k]).length() <= clear:
				return false
	return true


## A random point in the water, away from the shores, the routes, what's placed there and the tile's middle; null if none.
static func open_spot(outlines: Array, shores: Array, lines: Dictionary, rng: PyRandom, clear := 1.0, route := 0.75, taken: Array = [], apart := 1.4, hub := 0.0):
	for _t in 60:
		var p := Vector2(rng.uniform(-A, A), rng.uniform(-R, R))
		if p.length() >= hub and inside_tile(p, 0.8) and in_water(outlines, p) and _clear_of(p, shores, clear) \
				and _line_dist(p, lines) > route and taken.all(func(q): return (p - q).length() > apart):
			return p
	return null


## [a point on a shore curve, the angle pointing out over the water].
static func at_shore(curve: PackedVector2Array, u: float) -> Array:
	var k := clampi(int((curve.size() - 1) * u), 1, curve.size() - 2)
	var tan := curve[k + 1] - curve[k - 1]
	return [curve[k], atan2(tan.x, -tan.y)]


## Whether this water tile can become the landmark (design/02).
static func landmark_fits(name: String, water: Array, seed: String, widths: Array = []) -> bool:
	if name == "riverport" or name == "meditationrock":
		return water.has(false)
	if name == "trollbridge":
		return not bridge_spot(water, seed, widths, TROLL_HALF).is_empty()
	return true


## A raft can't run rapids (design/02): a party can still cross them on foot, by bridge or Athletics check.
static func raft_can_enter(name) -> bool:
	return FAMILY.get(name) != "rapids"


## [prop piece, point, angle] for a great lake, rapids or still waters tile. near: 1 or 2 steps from the region's landmark.
static func tile_props(water: Array, seed: String, widths: Array = [], style := "", near := 0, landmark := false) -> Array:
	if not style in ["great_lake", "rapids", "still_waters"]:
		return []
	var w := tile_water(water, seed, widths, style)
	var lines: Dictionary = water_routes(water, seed, widths, style).lines
	var rng := PyRandom.new("%s-%s-props" % [seed, style])
	var out := []
	var long_shores: Array = w.shores.filter(func(c): return c.size() > 8)
	var taken := []
	var afloat := func(name: String, clear := 1.0, route := 0.75) -> void:
		var p = open_spot(w.outlines, w.shores, lines, rng, clear, route, taken, 1.4, 3.0 if landmark else 0.0)
		if p != null and p != Vector2.ZERO:
			taken.append(p)
			out.append([name, p, rng.uniform(0, TAU)])
	var on_route := func(p: Vector2, ang: float, reach: float) -> bool:
		return _line_dist(p + Vector2(cos(ang), sin(ang)) * reach, lines) < 0.45
	if style == "great_lake":
		if not landmark:
			for c: PackedVector2Array in long_shores:
				var u := rng.uniform(0.35, 0.65)
				var sh := at_shore(c, u)
				if rng.random() < 0.75 and inside_tile(sh[0], 0.3) and not on_route.call(sh[0], sh[1], 1.5):
					out.append(["lake_hut", sh[0], sh[1]])
					taken.append(sh[0] + Vector2(cos(sh[1]), sin(sh[1])))
					var sh2 := at_shore(c, u + 0.22)
					if rng.random() < 0.7 and inside_tile(sh2[0], 0.4):
						out.append(["lake_net", sh2[0] + Vector2(cos(sh2[1]), sin(sh2[1])) * -0.42, sh2[1]])
			if rng.random() < 0.7:
				afloat.call("lake_boat")
			if w.shores.is_empty() and rng.random() < 0.4:
				afloat.call("lake_islet", 1.6)
		if near == 1 and rng.random() < 0.5:
			afloat.call("lake_wreck", 1.0, 0.7)
		var sign_ := rng.random()   # now and then, far out: more often toward the Lair
		if sign_ < (0.3 if near == 1 else 0.12):
			afloat.call("lake_coil", 1.3, 0.9)
		elif sign_ < (0.5 if near != 0 else 0.25):
			afloat.call("lake_fin", 1.3, 0.6)
	elif style == "rapids":
		for i in 3:   # a shared edge's fall is placed by one of its two tiles
			if water[i] and not widths.is_empty() and widths[i] == RAPIDS_WIDTH:
				out.append(["rapids_fall", normal(i) * A, deg_to_rad(60.0 * i)])
		var spot := {} if landmark else rapids_spot(water, seed, widths)
		if not spot.is_empty():
			out.append(["rapids_bridge", spot.middle, spot.angle])
	else:
		for c: PackedVector2Array in long_shores:
			var sh := at_shore(c, rng.uniform(0.3, 0.7))
			if not landmark and rng.random() < (0.8 if near != 0 else 0.5) and inside_tile(sh[0], 0.4) and not on_route.call(sh[0], sh[1], 1.0):
				out.append(["still_willow", sh[0], sh[1]])
			if rng.random() < (0.8 if near != 0 else 0.45):
				var sh2 := at_shore(c, rng.uniform(0.15, 0.85))
				var p2: Vector2 = sh2[0] + Vector2(cos(sh2[1]), sin(sh2[1])) * -0.5
				if inside_tile(p2, 0.25):
					out.append(["still_stack", p2, sh2[1]])
		for c: PackedVector2Array in long_shores:
			if rng.random() < (0.7 if near != 0 else 0.4):
				var sh := at_shore(c, rng.uniform(0.1, 0.9))
				var p: Vector2 = sh[0] + Vector2(cos(sh[1]), sin(sh[1])) * rng.uniform(0.75, 1.05)
				if in_water(w.outlines, p) and inside_tile(p, 0.7) and not on_route.call(p, sh[1], 0.0) and (not landmark or p.length() > ROCK_R + 0.6):
					out.append(["still_stones", p, rng.uniform(0, TAU)])
	return out


## How high to place a prop from tile_props: a rapids fall stands on the gorge's water, at a shared edge.
static func prop_z(prop: String) -> float:
	return -Gorge.DEPTH if prop == "rapids_fall" else 0.0


## Short pale strokes on deep water, all lying the same way: [point, angle, long, wide].
static func lake_waves(outlines: Array, shores: Array, seed: String) -> Array:
	var rng := PyRandom.new(seed + "-waves")
	var out := []
	for _t in 26:
		var p := Vector2(rng.uniform(-A, A), rng.uniform(-R, R))
		if inside_tile(p, 0.5) and in_water(outlines, p) and _clear_of(p, shores, 0.55):
			var ang := 0.32 + rng.uniform(-0.08, 0.08)
			var l := rng.uniform(0.35, 0.7)
			out.append([p, ang, l, rng.uniform(0.035, 0.06)])
		if out.size() == 7:
			break
	return out


## Lily pads near still waters' shores: [point, radius, flower], flower "" or the colour of a lotus on the pad.
static func still_lilies(outlines: Array, shores: Array, seed: String, near := 0) -> Array:
	var rng := PyRandom.new(seed + "-lilies")
	var out := []
	for curve: PackedVector2Array in shores:
		for k in range(1, curve.size() - 1, 2):
			if rng.random() > (0.55 if near != 0 else 0.38):
				continue
			var tan := curve[k + 1] - curve[k - 1]
			var l := tan.length()
			var into := Vector2(-tan.y, tan.x) * (1.0 / (l if l != 0.0 else 1.0))
			var p := curve[k] + into * rng.uniform(0.3, 0.8)
			if in_water(outlines, p) and inside_tile(p, 0.25):
				var f := rng.random()
				var r := rng.uniform(0.13, 0.22)
				out.append([p, r, "flower_pink" if f < 0.3 else "flower_white" if f < 0.5 else ""])
	return out


## [outlines, shores] a water tile keeps the ground cover off.
static func cover_shape(own: String, neighbours: Array, seed: String) -> Array:
	var mask := neighbours.map(func(n): return FAMILY.has(n) or n == "river")
	var widths := edge_widths(own, neighbours)
	if own == "riverport":
		var t := port_turn(mask, seed)
		return [port_shape(mask, seed, widths, t).outlines, [port_water(t)[1]]]
	var w := tile_water(mask, seed, widths, FAMILY.get(own, ""))
	if FAMILY.get(own) == "rapids" and mask.has(true):   # off the cut too
		var cut: Array = Gorge.build(mask, seed, widths, own == "trollbridge").cut
		return [cut if not cut.is_empty() else w.outlines, w.shores]
	return [w.outlines, w.shores]


static var _ripples: ImageTexture


## The water shader's ripples, baked: height in R, its slope per metre along x and y in G and B. One tile, as the shader's old per-pixel noise took a phone under 60 fps on broad water.
static func ripple_texture() -> ImageTexture:
	if _ripples == null:
		const SIZE := 256
		var look := FastNoiseLite.new()
		look.noise_type = FastNoiseLite.TYPE_PERLIN
		look.frequency = 8.0 / SIZE
		look.fractal_type = FastNoiseLite.FRACTAL_FBM
		look.fractal_octaves = 4
		var src := look.get_seamless_image(SIZE, SIZE)
		var h := PackedFloat32Array()
		h.resize(SIZE * SIZE)
		for y in SIZE:
			for x in SIZE:
				h[y * SIZE + x] = 0.5 + (src.get_pixel(x, y).r - 0.5) * 0.55   # about the old noise's contrast
		var per_metre := SIZE / RIPPLE_TILE * 0.5
		var out := Image.create(SIZE, SIZE, false, Image.FORMAT_RGB8)
		for y in SIZE:
			for x in SIZE:
				var sx := (h[y * SIZE + (x + 1) % SIZE] - h[y * SIZE + (x + SIZE - 1) % SIZE]) * per_metre
				var sy := (h[(y + 1) % SIZE * SIZE + x] - h[(y + SIZE - 1) % SIZE * SIZE + x]) * per_metre
				out.set_pixel(x, y, Color(h[y * SIZE + x], clampf(0.5 + sx / RIPPLE_SLOPE, 0.0, 1.0), clampf(0.5 + sy / RIPPLE_SLOPE, 0.0, 1.0)))
		out.generate_mipmaps()
		_ripples = ImageTexture.create_from_image(out)
	return _ripples
