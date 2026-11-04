class_name FeyLands
extends RefCounted
## Port of art/scripts/fey_lands.py's plain section (tiles v84, art/handoff/feywild_kit.md): the Feywild crossing, each tile locked in a season
## with sharp seams and one forest carrying across, worked out from world position. Region once per finished region, then fey_tile per tile.
## Everything is plan coordinates (x east, y north, z up). tools/fey_cases.py and FeyCheck compare it with the art's.

const A := Water.A
const R := Water.R
const VARIANT := "feywild_crossing"
const GATES := ["feygate"]
const LOOKS := {"feywild_crossing": "feywild_crossing", "feygate": "feywild_crossing"}

const RINGS := 7            # ground grid: rings from a tile's middle to its edge. Edge samples sit where the neighbour's do
const GROUND_Z := 0.012
const TRAIL_Z := 0.02
const TRAIL_HALF := 0.26
const CELL := 0.5           # candidate trees: one per cell, jittered
const GAP := 0.45           # no two trees closer than this
const TRAIL_CLEAR := 0.9    # a trunk from a trail's line: a mini's half width and a crown's reach
const SPOKE_CLEAR := 0.38   # a trunk from a spoke: a mini's half width and a trunk's
const HUB_CLEAR := 0.75     # and from a tile's middle
const OUTER_GAP := 0.22     # and from an outer edge. The crown may hang over
const ITEM_CLEAR := 0.62    # logs and boulders from any walked line
const GREAT_RATE := 0.18    # share of three-way corners with a great tree
const GREAT_H := 3.0
const SECOND_TRAIL := 10    # a region this big gets a second route to the gate
const GATE_KEEP := 2.9      # trees stay out of this circle on a gate's tile
const RING_R := 2.45        # the circle a gate's routes walk round
const GATE_STOP := Vector2(1.25, 0.0)
const GLADE_R := 3.0        # a far tile's glade: out toward a corner
const GLADE_CLEAR := 0.95
const PORTAL_MID := Vector3(0.0, 0.0, 1.2)   # the wisps drift to this point, gate-local

const GROUND := {           # floor, darker patch, what shows through: the patches lie in the same world spots in every season
	"spring": ["#8FB765", "#7FA75C", "#6F8F52"],
	"summer": ["#6E9158", "#62854F", "#566F46"],
	"autumn": ["#9A9150", "#8C8247", "#75693D"],
	"winter": ["#E6EBF1", "#D6DEE6", "#99A08C"],
}
const TRAIL := {"spring": "#8B7550", "summer": "#7D6C4A", "autumn": "#7B5A33", "winter": "#8E99A6"}
const CROWN := {
	"spring": ["#B7D86A", "#C9E07E", "#A5CF60", "#B7D86A", "#C9E07E", "blossom"],
	"summer": ["#4E8049", "#3F7440", "#5B8F4E", "#47793F", "#4E8049"],
	"autumn": ["#DB7A2E", "#C9502B", "#E5A92F", "#B8432E", "#DA8E2A"],
}
const PINE := {"spring": ["#3B6A3A", "#79A955"], "summer": ["#3B6A3A", "#3F7040"], "autumn": ["#35603A", "#4A6B38"], "winter": ["#2F5236", "#EEF3F8"]}
const ROCK_TOP := {"spring": "#7FA25E", "summer": "#8E8F8A", "autumn": "#B5812F", "winter": "#F0F4F8"}
const TUFT := {"spring": ["#F7F2D8", "#F4D45C", "#8DBB5C"], "summer": ["#7FA95A", "#6C9A52", "#7FA95A"], "autumn": ["#B8622B", "#8C7A3A", "#C98A2E"], "winter": ["#B7A584", "#A08F72", "#B7A584"]}
const EFFECT := {"spring": "petals", "autumn": "leaves", "winter": "snow"}


## Two parities, four seasons: every neighbour differs in at least one parity, so neighbours never match, and no tile needs its neighbours to know its own.
static func season_of(q: int, r: int) -> String:
	return [["autumn", "spring"], ["winter", "summer"]][posmod(q, 2)][posmod(r, 2)]


static func world_noise(x: float, y: float, seed_: int) -> float:
	var i := int(floor(x))
	var j := int(floor(y))
	var fx := x - i
	var fy := y - j
	fx = fx * fx * (3.0 - 2.0 * fx)
	fy = fy * fy * (3.0 - 2.0 * fy)
	var a := GroundCover.hash01(i, j, seed_)
	var b := GroundCover.hash01(i + 1, j, seed_)
	var c := GroundCover.hash01(i, j + 1, seed_)
	var d := GroundCover.hash01(i + 1, j + 1, seed_)
	return (a * (1.0 - fx) + b * fx) * (1.0 - fy) + (c * (1.0 - fx) + d * fx) * fy


static func fine_hash(x: float, y: float, k: int) -> float:
	return GroundCover.hash01(int(floor(x * 97.0)), int(floor(y * 97.0)), k)


## A squashed icosahedron's triangles, wound outward.
static func ico_faces(centre: Vector3, r: float, squash: float, spin: float) -> Array:
	var t := (1.0 + sqrt(5.0)) / 2.0
	var v := [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]]
	var f := [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
	var c := cos(spin)
	var s := sin(spin)
	var scale := r / sqrt(1.0 + t * t)
	var pts := []
	for q: Array in v:
		pts.append(Vector3(centre.x + (q[0] * c - q[1] * s) * scale, centre.y + (q[0] * s + q[1] * c) * scale, centre.z + q[2] * scale * squash))
	var out := []
	for k: Array in f:
		out.append([pts[k[0]], pts[k[1]], pts[k[2]]])
	return out


static func seg_d(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var f := clampf((p - a).dot(ab) / maxf(1e-9, ab.length_squared()), 0.0, 1.0)
	return p.distance_to(a + ab * f)


static func line_d(p: Vector2, lines: Array) -> float:
	var best := 99.0
	for line in lines:
		for k in range(1, line.size()):
			best = minf(best, seg_d(p, line[k - 1], line[k]))
	return best


static func spoke(i: int) -> PackedVector2Array:
	return PackedVector2Array([Water.normal(i) * A, Vector2.ZERO])


## {edge: walk}, from each edge's middle round the ring to the gate's stop.
static func gate_routes(turn := 0) -> Dictionary:
	var routes := {}
	for i in 6:
		var start := Water.normal(i) * A
		var pts := [start, start * SwampLands.LEAD]
		pts.append_array(SwampLands._ring_walk(i, RING_R, 0))
		pts.append(Vector2(1.9, 0.0))
		pts.append(GATE_STOP)
		var line := SwampLands.curve(pts, 4)
		var turned_line := PackedVector2Array()
		for q: Vector2 in line:
			turned_line.append(Water.turned(q, turn))
		routes[posmod(i + turn, 6)] = turned_line
	return routes


## The steps that get trails: {tile: its toward neighbour}, for the path from the region's farthest tile (the one LandmarkFlow.turn faces the gate toward) and,
## on a bigger region, the far tile with the longest way before it joins that path.
static func gate_paths(toward: Dictionary, gate: Vector2i) -> Dictionary:
	if toward.is_empty():
		return {}
	var dist := {gate: 0}
	for t: Vector2i in toward:
		var n := 0
		var u := t
		while u != gate:
			u = toward[u]
			n += 1
		dist[t] = n
	var rank := func(t: Vector2i) -> Array:
		return [dist[t], GroundCover.hash01(t.x, t.y, 10)]
	var first := _most(toward.keys(), rank)
	var kept := {}
	var u: Vector2i = first
	while u != gate:
		kept[u] = toward[u]
		u = toward[u]
	if toward.size() + 1 >= SECOND_TRAIL:
		var fresh := func(t: Vector2i) -> int:
			var n := 0
			while not kept.has(t) and t != gate:
				t = toward[t]
				n += 1
			return n
		var second := _most(toward.keys(), func(t: Vector2i): return [fresh.call(t), dist[t], GroundCover.hash01(t.x, t.y, 10)])
		if fresh.call(second) >= 2:
			u = second
			while not kept.has(u) and u != gate:
				kept[u] = toward[u]
				u = toward[u]
	return kept


static func _most(items: Array, rank: Callable) -> Vector2i:
	var best: Vector2i = items[0]
	var top: Array = rank.call(best)
	for t: Vector2i in items:
		var r: Array = rank.call(t)
		if _above(r, top):
			best = t
			top = r
	return best


static func _above(a: Array, b: Array) -> bool:
	for k in a.size():
		if a[k] != b[k]:
			return a[k] > b[k]
	return false


## How a party walks across tile t from edge i to edge j, tile-local. Past a gate it goes round the ring and back out.
static func walk_line(region: Region, t: Vector2i, i: int, j: int) -> PackedVector2Array:
	if region.names[t] in GATES:
		var out: PackedVector2Array = region.routes[t][i].duplicate()
		var back: PackedVector2Array = region.routes[t][j].duplicate()
		back.reverse()
		out.append_array(back)
		return out
	if i in region.edges[t] and j in region.edges[t]:
		return SwampLands.trail_line(t.x, t.y, i, j)
	var out := spoke(i)
	var back := spoke(j)
	back.reverse()
	back.remove_at(0)
	out.append_array(back)
	return out


## One finished Feywild region: its names, flow, walked lines and everything standing in it, worked out once when the region finishes.
class Region:
	var names := {}
	var toward := {}
	var turns := {}
	var edges := {}
	var out := {}
	var trails := {}
	var routes := {}
	var glades := {}
	var trail_world := {}
	var spoke_world := {}
	var ring_world := {}
	var seam_list := []
	var items := []
	var tris := []       # [a, b, c, part, id, tier] in world space
	var things := {}     # id -> its tris, so a tile looks at what's near without going through every face
	var owner := {}      # id -> the tile it stands on
	var number := 0
	var placed_trees := 0
	var taken := []
	var memo := {}

	func _init(terrains: Dictionary, flow := {}, turns_ := {}) -> void:
		for t: Vector2i in terrains:
			if FeyLands.LOOKS.has(terrains[t]):
				names[t] = terrains[t]
		turns = turns_
		var gates := names.keys().filter(func(t): return names[t] in FeyLands.GATES)
		if not gates.is_empty() and not flow.is_empty():
			var inside := {}
			for t: Vector2i in flow:
				if names.has(t):
					inside[t] = flow[t]
			toward = FeyLands.gate_paths(inside, gates[0])
		for t: Vector2i in names:
			edges[t] = LandmarkFlow.trail_edges(t, toward) if not toward.is_empty() else []
			out[t] = LandmarkFlow.toward_edge(t, toward) if toward.has(t) else null
			if names[t] in FeyLands.GATES:
				routes[t] = FeyLands.gate_routes(turns.get(t, 0))
				trails[t] = _gate_trails(t)
			else:
				trails[t] = SwampLands._tile_trails(names, t.x, t.y, edges[t], out[t])
			if edges[t].size() == 1 and not names[t] in FeyLands.GATES and out[t] != null:
				var k := SwampLands._end_corner(t.x, t.y, out[t])
				glades[t] = Hex.tile_position(t.x, t.y) + Water.corner(k) * (FeyLands.GLADE_R / FeyLands.R)
		for t: Vector2i in names:
			var c := Hex.tile_position(t.x, t.y)
			var worn := []
			for pair: Array in trails[t]:
				worn.append(_moved(pair[0], c))
			trail_world[t] = worn
			var spokes := []
			if not names[t] in FeyLands.GATES:
				for i in 6:
					spokes.append(_moved(FeyLands.spoke(i), c))
			spoke_world[t] = spokes
			if routes.has(t):
				var ring := []
				for line in routes[t].values():
					ring.append(_moved(line, c))
				ring_world[t] = ring
		seam_list = _find_seams()
		_place_things()

	static func _moved(line: PackedVector2Array, c: Vector2) -> PackedVector2Array:
		var moved := PackedVector2Array()
		for q: Vector2 in line:
			moved.append(c + q)
		return moved

	func _gate_trails(t: Vector2i) -> Array:
		var turn: int = turns.get(t, 0)
		var done := []
		var order: Array = edges[t].duplicate()
		order.sort_custom(func(a, b): return mini(posmod(a - turn, 6), posmod(turn - a, 6)) < mini(posmod(b - turn, 6), posmod(turn - b, 6)))
		for i: int in order:
			var line: PackedVector2Array = routes[t][i]
			var cut := line.size()
			if not done.is_empty():
				var drawn := done.map(func(d): return d[1])
				for k in line.size():
					if SwampLands.line_dist(line[k], drawn) < 0.1:
						cut = k + 1
						break
			done.append([line, line.slice(0, cut)])
		return done

	func sorted_tiles() -> Array:
		var list := names.keys()
		list.sort_custom(func(a, b): return a.x < b.x or (a.x == b.x and a.y < b.y))
		return list

	## Each edge between two of the region's tiles once: [tile, tile, world end, world end].
	func _find_seams() -> Array:
		var seams := []
		for t: Vector2i in sorted_tiles():
			var c := Hex.tile_position(t.x, t.y)
			for i in 6:
				var n: Vector2i = t + Hex.NEIGHBOURS[i]
				if names.has(n) and (t.x < n.x or (t.x == n.x and t.y < n.y)):
					seams.append([t, n, c + Water.corner(posmod(i - 1, 6)), c + Water.corner(i)])
		return seams

	## The region's tiles whose walked lines count at a world point: the one under it and those touching it.
	func around(p: Vector2) -> Array:
		var t := GroundCover.tile_at(p)
		var near := []
		if names.has(t):
			near.append(t)
		for d: Vector2i in Hex.NEIGHBOURS:
			if names.has(t + d):
				near.append(t + d)
		return near

	func clear_for_trunk(p: Vector2, trail := FeyLands.TRAIL_CLEAR, spokes := FeyLands.SPOKE_CLEAR) -> bool:
		for u: Vector2i in around(p):
			if FeyLands.line_d(p, trail_world[u]) < trail or FeyLands.line_d(p, spoke_world[u]) < spokes or FeyLands.line_d(p, ring_world.get(u, [])) < trail:
				return false
			if names[u] in FeyLands.GATES and p.distance_to(Hex.tile_position(u.x, u.y)) < FeyLands.GATE_KEEP:
				return false
			if glades.has(u) and p.distance_to(glades[u]) < FeyLands.GLADE_CLEAR:
				return false
		var t := GroundCover.tile_at(p)
		return p.distance_to(Hex.tile_position(t.x, t.y)) >= FeyLands.HUB_CLEAR

	## How far a point is from an outer edge of the tile under it.
	func outer_gap(p: Vector2) -> float:
		var t := GroundCover.tile_at(p)
		var c := Hex.tile_position(t.x, t.y)
		var best := 99.0
		for i in 6:
			if not names.has(t + Hex.NEIGHBOURS[i]):
				best = minf(best, FeyLands.A - (p - c).dot(Water.normal(i)))
		return best

	func _free(p: Vector2, gap: float) -> bool:
		for u: Vector3 in taken:
			if p.distance_to(Vector2(u.x, u.y)) < gap + u.z:
				return false
		return true

	func _place_things() -> void:
		for t: Vector2i in glades:   # a far tile's trail ends among boulders round a stump
			var g: Vector2 = glades[t]
			var ang := GroundCover.hash01(t.x, t.y, 76) * 6.28
			number += 1
			_stump(g, 0.2)
			for k in 3:
				var a := ang + k * 2.2
				number += 1
				_rock(g + Vector2(0.62 * cos(a), 0.62 * sin(a)), 0.2 + 0.08 * k)
			taken.append(Vector3(g.x, g.y, 0.5))
		var corners := {}
		for s: Array in seam_list:
			corners[Vector2(snappedf(s[2].x, 0.0001), snappedf(s[2].y, 0.0001))] = true
			corners[Vector2(snappedf(s[3].x, 0.0001), snappedf(s[3].y, 0.0001))] = true
		var corner_list := corners.keys()
		corner_list.sort_custom(func(a, b): return a.x < b.x or (a.x == b.x and a.y < b.y))
		for p: Vector2 in corner_list:   # now and then a great tree where three tiles meet
			if _around_corner(p) == 3 and GroundCover.hash01(int(p.x * 10), int(p.y * 10), 71) < FeyLands.GREAT_RATE and clear_for_trunk(p, 1.5, 0.9):
				number += 1
				_broadleaf(p, FeyLands.GREAT_H, true)
				items.append(["great", p])
				taken.append(Vector3(p.x, p.y, 0.6))
		for k in seam_list.size():   # trunks and boulders lying across seams, away from the edge's middle, where the walked lines cross it
			var a: Vector2i = seam_list[k][0]
			var b: Vector2i = seam_list[k][1]
			var p: Vector2 = seam_list[k][2]
			var q: Vector2 = seam_list[k][3]
			var h := GroundCover.hash01(a.x * 5 + b.x, a.y * 5 + b.y, 72)
			var s := GroundCover.hash01(a.x * 5 + b.x, a.y * 5 + b.y, 73)
			s = 0.14 + 0.22 * s if h < 0.4 or (0.6 < h and h < 0.8) else 0.64 + 0.22 * s
			var m := p + (q - p) * s
			var e := (q - p) / FeyLands.R
			var side := Vector2(-e.y, e.x)
			if h < 0.5:
				var tilt := (GroundCover.hash01(k, 7, 74) - 0.5) * 0.9
				var u := (side + e * tilt).normalized()
				for half: float in [1.5, 1.1]:
					var e0 := m - u * half
					var e1 := m + u * half
					if _item_clear(e0, e1) and outer_gap(e0) > 0.2 and outer_gap(e1) > 0.2 and _free(e0, 0.4) and _free(e1, 0.4):
						number += 1
						_log(e0, e1, 0.13)
						items.append(["log", e0, e1])
						for j in 5:
							var f := j / 4.0
							var at := e0 + (e1 - e0) * f
							taken.append(Vector3(at.x, at.y, 0.3))
						break
			elif h < 0.88 and _item_clear(m, m, 0.45) and _free(m, 0.4):
				number += 1
				var r := 0.3 + 0.2 * (h - 0.5)
				_rock(m, r)
				items.append(["rock", m, r])
				taken.append(Vector3(m.x, m.y, 0.3))
		var low := Vector2(INF, INF)
		var high := Vector2(-INF, -INF)
		for t: Vector2i in names:
			var c := Hex.tile_position(t.x, t.y)
			low = Vector2(minf(low.x, c.x), minf(low.y, c.y))
			high = Vector2(maxf(high.x, c.x), maxf(high.y, c.y))
		for ix in range(int((low.x - FeyLands.A - 1.0) / FeyLands.CELL), int((high.x + FeyLands.A + 1.0) / FeyLands.CELL)):
			for iy in range(int((low.y - FeyLands.R - 1.0) / FeyLands.CELL), int((high.y + FeyLands.R + 1.0) / FeyLands.CELL)):
				if not _stands(ix, iy):
					continue
				var p := _candidate(ix, iy)
				var h := 1.7 + 0.8 * GroundCover.hash01(ix, iy, 14)
				number += 1
				placed_trees += 1
				if GroundCover.hash01(ix, iy, 15) < 0.5:
					_pine(p, h)
				else:
					_broadleaf(p, h)
		var step := 0.95
		for ix in range(int((low.x - FeyLands.A - 1.0) / step), int((high.x + FeyLands.A + 1.0) / step)):
			for iy in range(int((low.y - FeyLands.R - 1.0) / step), int((high.y + FeyLands.R + 1.0) / step)):
				var p := Vector2(ix * step + (GroundCover.hash01(ix, iy, 21) - 0.5) * step, iy * step + (GroundCover.hash01(ix, iy, 22) - 0.5) * step)
				if names.has(GroundCover.tile_at(p)) and GroundCover.hash01(ix, iy, 23) < 0.35 and outer_gap(p) > 0.15 and _free(p, 0.2):
					var dry := true
					for u: Vector2i in around(p):
						if FeyLands.line_d(p, trail_world[u]) <= 0.45:
							dry = false
							break
					if dry:
						number += 1
						_tuft(p)

	func _around_corner(p: Vector2) -> int:
		var seen := {}
		for ang: float in [30.0, 90.0, 150.0, 210.0, 270.0, 330.0]:
			var t := GroundCover.tile_at(p + Vector2(0.3 * cos(deg_to_rad(ang)), 0.3 * sin(deg_to_rad(ang))))
			if names.has(t):
				seen[t] = true
		return seen.size()

	func _item_clear(a: Vector2, b: Vector2, need := FeyLands.ITEM_CLEAR) -> bool:
		for f: float in [0.0, 0.25, 0.5, 0.75, 1.0]:
			var p := a + (b - a) * f
			if not names.has(GroundCover.tile_at(p)):
				return false
			for u: Vector2i in around(p):
				if FeyLands.line_d(p, trail_world[u]) < need or FeyLands.line_d(p, spoke_world[u]) < need or FeyLands.line_d(p, ring_world.get(u, [])) < need:
					return false
				if names[u] in FeyLands.GATES and p.distance_to(Hex.tile_position(u.x, u.y)) < FeyLands.GATE_KEEP:
					return false
				if glades.has(u) and p.distance_to(glades[u]) < FeyLands.GLADE_CLEAR:
					return false
		return true

	static func _candidate(ix: int, iy: int) -> Vector2:
		return Vector2(ix * FeyLands.CELL + (GroundCover.hash01(ix, iy, 11) - 0.5) * FeyLands.CELL, iy * FeyLands.CELL + (GroundCover.hash01(ix, iy, 12) - 0.5) * FeyLands.CELL)

	## A candidate stands if it has room and no standing candidate within GAP has a higher hash, so trees fill up to the walked lines. Tiles either side of a seam work out the same answer.
	func _stands(ix: int, iy: int) -> bool:
		var key := Vector2i(ix, iy)
		if memo.has(key):
			return memo[key]
		var p := _candidate(ix, iy)
		var ok := names.has(GroundCover.tile_at(p)) and outer_gap(p) >= FeyLands.OUTER_GAP and _free(p, 0.55) and clear_for_trunk(p)
		if ok:
			var mine := GroundCover.hash01(ix, iy, 10)
			for u in range(ix - 2, ix + 3):
				for v in range(iy - 2, iy + 3):
					if (u != ix or v != iy) and GroundCover.hash01(u, v, 10) > mine and _candidate(u, v).distance_to(p) < FeyLands.GAP and _stands(u, v):
						ok = false
						break
				if not ok:
					break
		memo[key] = ok
		return ok

	# Shapes ---------------------------------------------------------------------------------------------

	func _add(a: Vector3, b: Vector3, c: Vector3, part: String, tier := 0) -> void:
		var tri := [a, b, c, part, number, tier]
		tris.append(tri)
		if not things.has(number):
			things[number] = []
		things[number].append(tri)
		if not owner.has(number) and part in ["trunk", "log", "rock", "tuft"]:
			owner[number] = GroundCover.tile_at(Vector2(a.x, a.y))

	static func _ring(at: Vector2, r: float, z: float, segs: int, spin: float) -> Array:
		var pts := []
		for k in segs:
			pts.append(Vector3(at.x + r * cos(spin + TAU * k / segs), at.y + r * sin(spin + TAU * k / segs), z))
		return pts

	func _wall(low: Array, high: Array, part: String, tier := 0) -> void:
		var n := low.size()
		for k in n:
			_add(low[k], low[(k + 1) % n], high[(k + 1) % n], part, tier)
			_add(low[k], high[(k + 1) % n], high[k], part, tier)

	func _cone(at: Vector2, r: float, z: float, h: float, part: String, spin: float) -> void:
		var low := _ring(at, r, z, 6, spin)
		var mid := _ring(at, r * 0.45, z + h * 0.55, 6, spin)
		var tip := Vector3(at.x, at.y, z + h)
		_wall(low, mid, part, 0)
		for k in 6:
			_add(mid[k], mid[(k + 1) % 6], tip, part, 1)

	func _ico(centre: Vector3, r: float, squash: float, part: String, spin: float) -> void:
		for f: Array in FeyLands.ico_faces(centre, r, squash, spin):
			_add(f[0], f[1], f[2], part)

	## A three-sided limb, no end cap.
	func _spar(a: Vector3, b: Vector3, r0: float, r1: float, part: String) -> void:
		var d := (b - a).normalized()
		var s := Vector3(d.y, -d.x, 0.0)
		var sl := Vector2(s.x, s.y).length()
		if sl <= 0.0:
			sl = 1.0
		s = Vector3(s.x / sl, s.y / sl, 0.0) if sl > 1e-3 else Vector3(1, 0, 0)
		var u := s.cross(d)
		var around_ := func(p: Vector3, r: float) -> Array:
			var pts := []
			for c: float in [PI / 2.0, PI / 2.0 + 2.094, PI / 2.0 + 4.188]:
				pts.append(p + (u * cos(c) + s * sin(c)) * r)
			return pts
		_wall(around_.call(a, r0), around_.call(b, r1), part)

	## Winter's tree: what stands inside every crown. Fewer twigs than limbs, for the budget.
	func _limbs(at: Vector2, h: float, spin: float, big: bool) -> void:
		var base := Vector3(at.x, at.y, FeyLands.GROUND_Z + h * 0.4)
		var reach := h * (0.36 if big else 0.28)
		var spread := 5 if big else 3
		for k in spread:
			var ang := spin + k * 6.28 / spread + 0.5 * GroundCover.hash01(number, k, 61)
			var lift := h * (0.2 + 0.2 * GroundCover.hash01(number, k, 62))
			var tip := Vector3(at.x + reach * cos(ang), at.y + reach * sin(ang), base.z + lift)
			_spar(base, tip, 0.055 if big else 0.045, 0.02, "limb")
			if big or k == 0:
				var j := 0.7 if GroundCover.hash01(number, k, 63) < 0.5 else -0.7
				_spar(tip, Vector3(tip.x + reach * 0.5 * cos(ang + j), tip.y + reach * 0.5 * sin(ang + j), tip.z + h * 0.13), 0.02, 0.006, "twig")
		_spar(base, Vector3(at.x, at.y, base.z + h * 0.42), 0.06, 0.012, "twig")

	func _broadleaf(at: Vector2, h: float, big := false) -> void:
		var spin := GroundCover.hash01(int(at.x * 97), int(at.y * 97), 1) * 6.28
		_wall(_ring(at, 0.11 if big else 0.09, 0.0, 6, spin), _ring(at, 0.09 if big else 0.07, FeyLands.GROUND_Z + h * 0.42, 6, spin), "trunk")
		_limbs(at, h, spin, big)
		if big:
			_ico(Vector3(at.x, at.y, FeyLands.GROUND_Z + h * 0.62), h * 0.36, 1.0, "crown", spin)
			for k: float in [0.0, 2.1, 4.2]:
				_ico(Vector3(at.x + h * 0.2 * cos(spin + k), at.y + h * 0.2 * sin(spin + k), FeyLands.GROUND_Z + h * 0.47), h * 0.24, 0.9, "crown", spin + k)
		else:
			_ico(Vector3(at.x, at.y, FeyLands.GROUND_Z + h * 0.55), h * 0.3, 1.15, "crown", spin)

	func _pine(at: Vector2, h: float) -> void:
		var spin := GroundCover.hash01(int(at.x * 97), int(at.y * 97), 2) * 6.28
		_wall(_ring(at, 0.09, 0.0, 6, spin), _ring(at, 0.07, FeyLands.GROUND_Z + h * 0.25, 6, spin), "trunk")
		_cone(at, h * 0.3, FeyLands.GROUND_Z + h * 0.2, h * 0.55, "pine", spin)
		_cone(at, h * 0.22, FeyLands.GROUND_Z + h * 0.5, h * 0.45, "pine", spin + 0.5)

	func _rock(at: Vector2, r: float) -> void:
		_ico(Vector3(at.x, at.y, FeyLands.GROUND_Z + r * 0.15), r, 0.6, "rock", GroundCover.hash01(int(at.x * 97), int(at.y * 97), 3) * 6.28)

	func _stump(at: Vector2, r: float) -> void:
		var spin := GroundCover.hash01(int(at.x * 97), int(at.y * 97), 5) * 6.28
		var low := _ring(at, r, 0.0, 6, spin)
		var high := _ring(at, r * 0.85, 0.26, 6, spin)
		_wall(low, high, "log")
		var top := Vector3(at.x, at.y, 0.28)
		for k in 6:
			_add(high[k], high[(k + 1) % 6], top, "log_end")

	func _log(a: Vector2, b: Vector2, r: float) -> void:
		var d := b - a
		var side := Vector2(-d.y, d.x) / d.length()
		var steps := 4
		var rings := []
		for s in steps + 1:
			var p := a + d * (float(s) / steps)
			var g := FeyLands.GROUND_Z + r * 0.75
			var one := []
			for k in 6:
				one.append(Vector3(p.x + side.x * r * cos(k * PI / 3.0), p.y + side.y * r * cos(k * PI / 3.0), g + r * sin(k * PI / 3.0)))
			rings.append(one)
		for s in steps:
			_wall(rings[s + 1], rings[s], "log")   # around the way that faces out
		for row: Array in [[rings[0], true], [rings[-1], false]]:
			var rr: Array = row[0]
			var c := Vector3.ZERO
			for q: Vector3 in rr:
				c += q / 6.0
			for k in 6:
				if row[1]:
					_add(rr[k], rr[(k + 1) % 6], c, "log_end")
				else:
					_add(rr[(k + 1) % 6], rr[k], c, "log_end")

	func _tuft(at: Vector2) -> void:
		var h := 0.14 + 0.14 * FeyLands.fine_hash(at.x, at.y, 4)
		var low := _ring(at, 0.09, 0.0, 4, FeyLands.fine_hash(at.x, at.y, 5) * 6.28)
		for k in 4:
			_add(low[k], low[(k + 1) % 4], Vector3(at.x, at.y, FeyLands.GROUND_Z + h), "tuft")

	## Once every tile has its faces: what walking needs stays.
	func free_shapes() -> void:
		tris = []
		things = {}
		memo = {}
		taken = []

	# Cutting and colouring ------------------------------------------------------------------------------

	## The half planes bounding tile t: [centre, normal]. Outer edges don't cut, unless whole: over them, crowns hang on.
	func planes(t: Vector2i, whole := false) -> Array:
		var c := Hex.tile_position(t.x, t.y)
		var list := []
		for i in 6:
			if whole or names.has(t + Hex.NEIGHBOURS[i]):
				list.append([c, Water.normal(i)])
		return list

	## [[colour, [points], part]] world-space, for everything standing on tile t.
	func forest_faces(t: Vector2i) -> Array:
		var c := Hex.tile_position(t.x, t.y)
		var reach := FeyLands.R + 2.2
		var faces := []
		var season := FeyLands.season_of(t.x, t.y)
		var base := planes(t)
		var whole := planes(t, true)
		var winter := season == "winter"
		for id: int in things:
			var list: Array = things[id]
			var first: Vector3 = list[0][0]
			if Vector2(first.x - c.x, first.y - c.y).length() > reach + 4.0 or not _may_draw(t, id):
				continue
			for tri: Array in list:
				var a: Vector3 = tri[0]
				var b: Vector3 = tri[1]
				var d: Vector3 = tri[2]
				var mid := (a + b + d) / 3.0
				if Vector2(mid.x - c.x, mid.y - c.y).length_squared() > reach * reach:
					continue
				var part: String = tri[3]
				var bare: bool = part == "limb" or part == "twig"
				if winter != bare and (bare or part == "crown"):
					continue
				var poly := FeyLands.clip([a, b, d], whole if part == "tuft" else base)
				if poly.size() >= 3:
					faces.append([FeyLands.part_colour(part, id, tri[5], season, FeyLands.face_normal(a, b, d), mid.x, mid.y), poly, part])
		return faces

	## A tile draws a thing that stands on it or on a neighbour: its open outer sides mustn't pick up a tree from across a fold in the outline.
	func _may_draw(t: Vector2i, id: int) -> bool:
		if not owner.has(id):
			return true
		var o: Vector2i = owner[id]
		return o == t or (o - t) in Hex.NEIGHBOURS or not names.has(o)


## Cuts a polygon by half planes ([a point, an outward normal], A out from the point).
static func clip(poly: Array, planes_: Array) -> Array:
	for plane: Array in planes_:
		var c: Vector2 = plane[0]
		var n: Vector2 = plane[1]
		var kept := []
		for k in poly.size():
			var a: Vector3 = poly[k - 1]
			var b: Vector3 = poly[k]
			var da := (a.x - c.x) * n.x + (a.y - c.y) * n.y - A
			var db := (b.x - c.x) * n.x + (b.y - c.y) * n.y - A
			if (da <= 0.0) != (db <= 0.0):
				kept.append(a.lerp(b, da / (da - db)))
			if db <= 0.0:
				kept.append(b)
		poly = kept
		if poly.is_empty():
			return []
	return poly


static func face_normal(a: Vector3, b: Vector3, c: Vector3) -> Vector3:
	return (b - a).cross(c - a).normalized()


## A face's colour in a season. The mesh never changes between seasons, except that winter swaps a crown for its limbs.
static func part_colour(part: String, id: int, tier: int, season: String, n: Vector3, cx: float, cy: float) -> String:
	match part:
		"trunk":
			return "#6E5240" if season == "winter" else "#7A5236"
		"log":
			if season == "winter" and n.z > 0.7:
				return "#E8EDF3" if fine_hash(snappedf(cx, 0.1), snappedf(cy, 0.1), 16) < 0.6 else "#6E4E36"
			return "#6F7A3C" if season == "spring" and n.z > 0.7 else "#6E4E36"
		"log_end":
			return "#B99C70"
		"rock":
			return ROCK_TOP[season] if n.z > 0.25 else "#8E8F8A" if n.z > -0.3 else "#77787A"
		"tuft":
			return TUFT[season][id % 3]
		"pine":
			if season == "winter" and tier == 0:   # snow caught on every other face of the skirt
				return "#D6E2EC" if fine_hash(cx, cy, 6) < 0.45 else PINE[season][0]
			return PINE[season][tier]
		"limb":
			return "#B9C0C6" if n.z > 0.6 else "#5F5048"
		"twig":
			return "#5F5048"
	var pal: Array = CROWN[season]
	var k := int(GroundCover.hash01(id, 3, 41) * pal.size())
	var col: String = pal[k]
	if col == "blossom":   # never a whole white ball: a little cream among the leaves
		return "#EDEDC4" if fine_hash(cx, cy, 17) < 0.55 else "#B7D86A"
	if season == "autumn" and fine_hash(cx, cy, 8) < 0.2:
		return pal[(k + 2) % pal.size()]
	return col


static func ground_faces(t: Vector2i) -> Array:
	var c := Hex.tile_position(t.x, t.y)
	var out := []
	var season := season_of(t.x, t.y)
	var at := func(ring: int, side: int, s: int) -> Vector3:
		if ring == 0:
			return Vector3(c.x, c.y, GROUND_Z)
		if s == ring:
			side = (side + 1) % 6
			s = 0
		var a := Water.corner(posmod(side - 1, 6))
		var b := Water.corner(side)
		var f := float(ring) / RINGS
		var p := c + a * f + (b - a) * f * s / ring
		return Vector3(p.x, p.y, GROUND_Z)
	var tri := func(a: Vector3, b: Vector3, d: Vector3) -> void:
		var cx := (a.x + b.x + d.x) / 3.0
		var cy := (a.y + b.y + d.y) / 3.0
		var pick := world_noise(cx / 1.7, cy / 1.7, 33) * 0.65 + world_noise(cx / 0.8, cy / 0.8, 34) * 0.35   # the same patches in every season
		var k := 0 if pick < 0.5 else 1 if pick < 0.6 else 2
		out.append([GROUND[season][k], [a, b, d]])
	for ring in range(1, RINGS + 1):
		for side in 6:
			for s in ring:
				tri.call(at.call(ring, side, s), at.call(ring, side, s + 1), at.call(ring - 1, side, s))
				if s < ring - 1:
					tri.call(at.call(ring - 1, side, s), at.call(ring, side, s + 1), at.call(ring - 1, side, s + 1))
	return out


## Ribbons along a tile's drawn trails, in its season. Edge ends sit on an edge's middle, so they meet the next tile's.
static func trail_faces(region: Region, t: Vector2i) -> Array:
	var c := Hex.tile_position(t.x, t.y)
	var season := season_of(t.x, t.y)
	var whole := region.planes(t, true)
	var out := []
	for pair: Array in region.trails[t]:
		var drawn: PackedVector2Array = pair[1]
		var n := drawn.size()
		var side := func(i: int) -> Vector2:
			var d := drawn[mini(i + 1, n - 1)] - drawn[maxi(i - 1, 0)]
			var ln := d.length()
			if ln <= 0.0:
				ln = 1.0
			return Vector2(-d.y / ln * TRAIL_HALF, d.x / ln * TRAIL_HALF)
		for k in n - 1:
			var a := c + drawn[k]
			var b := c + drawn[k + 1]
			var sa: Vector2 = side.call(k)
			var sb: Vector2 = side.call(k + 1)
			var quad := [Vector3(a.x + sa.x, a.y + sa.y, TRAIL_Z), Vector3(a.x - sa.x, a.y - sa.y, TRAIL_Z), Vector3(b.x - sb.x, b.y - sb.y, TRAIL_Z), Vector3(b.x + sb.x, b.y + sb.y, TRAIL_Z)]
			if face_normal(quad[0], quad[1], quad[2]).z < 0.0:
				quad.reverse()
			var poly := clip(quad, whole)
			if poly.size() >= 3:
				out.append([TRAIL[season], poly])
	return out


## Everything the Feywild crossing puts on tile t, tile-local: ground, trail and stand as [colour, points anticlockwise], trails [[walked, drawn]], effects [kind], season.
static func fey_tile(region: Region, t: Vector2i) -> Dictionary:
	var c := Hex.tile_position(t.x, t.y)
	var local := func(faces: Array) -> Array:
		for f: Array in faces:
			var moved := []
			for q: Vector3 in f[1]:
				moved.append(Vector3(q.x - c.x, q.y - c.y, q.z))
			f[1] = moved
		return faces
	var season := season_of(t.x, t.y)
	return {season = season, ground = local.call(ground_faces(t)), trail = local.call(trail_faces(region, t)), stand = local.call(region.forest_faces(t)),
			trails = region.trails[t], effects = [EFFECT[season]] if EFFECT.has(season) else []}


static func face_tris(faces: Array) -> int:
	var n := 0
	for f: Array in faces:
		n += f[1].size() - 2
	return n
