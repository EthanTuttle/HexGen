class_name SwampLands
extends RefCounted
## Port of art/scripts/swamp_lands.py's plain section (tiles v68, art/handoff/swamp_kit.md): the wetland, worked out per tile
## from world position as desert sand is, so it runs on across edges and no two tiles match. marsh_tile is the entry point.
## Everything is tile-local plan coordinates (x east, y north). tools/swamp_cases.py and swamp_check.gd compare it with the art's.

const X1 := Water.A
const STILT_Z := 0.5        # a stilt house's deck
const RAMP_START := 1.72    # where its gangway meets the ground, on +X: inside the centre piece
const RAMP_END := 0.62      # and the deck
const HUT_STOP := Vector3(0.62, 0.0, STILT_Z)
const HOLLOW_STOP := Vector3(1.02, 0.0, 0.0)
const GUILD_STOP := Vector3(0.62, 0.0, STILT_Z)
const RING := 2.25          # the circle a landmark's routes walk round
const PIT_RING := 3.25
const PIT_LANE_R := 2.38    # its walked line
const PIT_FOOT_Z := -1.16   # its foot, a little above the ooze
const PIT_TILT := 25.5
const PIT_TOP := 82.0 * PI / 180.0   # where the lane leaves the ground
const LEAD := 0.86          # a walk leaves its edge straight, to meet the next tile's going the same way

const VIEW := {
	"swamp": {water = "bog_water", rim = "swamp_bank", style = "broad", level = 0.47, bank = 0.05},
	"bog": {water = "bog_dark", rim = "bog_bank", style = "broad", track = "track_bog", level = 0.46, bank = 0.045},
	"wisp_marsh": {water = "wisp_water", rim = "wisp_bank", style = "narrow", track = "track_wisp", level = 0.062, bank = 0.03},
	"rot_swamp": {water = "rot_water", rim = "rot_mud", style = "broad", track = "track_rot", level = 0.47, bank = 0.05},
	"smugglers_bayou": {water = "bayou_water", rim = "bayou_bank", style = "narrow", level = 0.105, bank = 0.03},
	"plaguepit": {water = "rot_water", rim = "rot_mud", style = "broad", track = "track_rot", level = 9.0, bank = 0.0},
}

const CELLS := 12           # rows of the triangle grid in each sixth of a tile: edge samples sit where the neighbour's do
const WATER_DRY := 0.54     # water keeps this far from every route's line
const WATER_TRAIL := 0.62   # and from a drawn trail
const CLOSE := 0.34         # water stops this far short of an edge it can't cross
const K := 0.2              # how fast distance counts against the field's value
const TRAIL_HALF := 0.3
const WALK_HALF := 0.52     # the bayou's boardwalk
const END_R := 3.0          # where a trail's finish stands, out toward a tile's corner
const POND_R := 3.25        # the bayou's landing stage: its pool
const POND_SIZE := 0.85
const END_START := 2.45     # and where the trail itself starts
const LOOKS := {"swamp": "swamp", "bog": "bog", "witchhut": "bog", "wisp_marsh": "wisp_marsh", "wisphollow": "wisp_marsh", "rot_swamp": "rot_swamp",
	"plaguepit": "plaguepit", "smugglers_bayou": "smugglers_bayou", "thievesguild": "smugglers_bayou"}
const LANDMARK_KEEP := {"witchhut": 1.95, "wisphollow": 2.05, "thievesguild": 2.05, "plaguepit": 3.35}  # a landmark's own piece holds what's inside this

## What stands in the wetland. name: [reach from its point, room it takes from others, triangles].
const PROP := {
	"marsh_tree_a": [0.72, 0.42, 96], "marsh_tree_b": [0.72, 0.42, 96], "marsh_tree_c": [0.62, 0.38, 96],
	"marsh_snag_a": [0.2, 0.2, 40], "marsh_snag_b": [0.2, 0.2, 40],
	"marsh_log_a": [0.78, 0.5, 60], "marsh_log_b": [0.62, 0.42, 60],
	"marsh_stump": [0.2, 0.16, 30],
	"marsh_reeds_a": [0.3, 0.14, 42], "marsh_reeds_b": [0.3, 0.14, 42], "marsh_reeds_small": [0.14, 0.08, 18],
	"marsh_cattails_a": [0.3, 0.14, 66], "marsh_cattails_b": [0.3, 0.14, 66],
	"marsh_mound_a": [0.45, 0.3, 90], "marsh_mound_b": [0.32, 0.22, 90],
	"marsh_lily": [0.34, 0.2, 60],
	"marsh_mist_a": [0.0, 0.0, 36], "marsh_mist_b": [0.0, 0.0, 36],
	"bog_toadstools": [0.3, 0.18, 144], "bog_flowers": [0.34, 0.2, 118], "bog_charm": [0.26, 0.2, 92], "bog_toadstools_small": [0.14, 0.1, 110], "bog_flowers_small": [0.14, 0.1, 110],
	"wisp_light_a": [0.3, 0.05, 40], "wisp_light_b": [0.3, 0.05, 40], "wisp_stake": [0.16, 0.08, 40],
	"rot_log": [0.78, 0.5, 204], "rot_rock": [0.34, 0.24, 70], "rot_puddle": [0.34, 0.24, 28], "rot_scum": [0.3, 0.2, 60], "rot_fungus": [0.14, 0.1, 90],
	"bog_trail_end": [0.6, 0.6, 464], "wisp_trail_end": [0.6, 0.6, 300], "rot_trail_end": [0.72, 0.6, 300], "bayou_landing": [1.2, 1.0, 300],
	"bayou_shack": [1.04, 0.8, 250], "bayou_boat": [0.72, 0.5, 56], "bayou_goods": [0.5, 0.4, 60], "bayou_lantern": [0.2, 0.16, 48], "bayou_crate": [0.14, 0.12, 12],
	"mudbank_swamp": [0.55, 0.3, 40], "mudbank_bog": [0.55, 0.3, 40], "mudbank_wisp_marsh": [0.55, 0.3, 40], "mudbank_rot_swamp": [0.55, 0.3, 40],
	"mudbank_smugglers_bayou": [0.55, 0.3, 40], "mudbank_plaguepit": [0.55, 0.3, 40],
}
## What each look scatters: in water, on its banks, on dry ground, in the small gaps in a tile's middle, and along its trails. Repeats are weights.
const SCATTER := {
	"swamp": {wet = ["marsh_lily", "marsh_lily", "marsh_tree_c", "marsh_tree_b", "marsh_reeds_a"], rim = ["marsh_reeds_a", "marsh_reeds_b", "marsh_cattails_a", "marsh_log_b", "marsh_mound_b", "marsh_cattails_b"], dry = ["marsh_tree_a", "marsh_tree_b", "marsh_log_a", "marsh_mound_a", "marsh_reeds_b", "mudbank_swamp", "marsh_tree_c", "marsh_reeds_a"], gap = ["marsh_reeds_small", "marsh_stump"], trail = [], keep = 0.9, mist = 0.3},
	"bog": {wet = ["marsh_tree_c", "marsh_tree_a", "marsh_tree_b", "marsh_reeds_a"], rim = ["marsh_reeds_a", "marsh_reeds_b", "bog_flowers", "marsh_log_b", "marsh_tree_c", "bog_toadstools"], dry = ["marsh_tree_a", "marsh_tree_b", "marsh_tree_c", "bog_toadstools", "bog_flowers", "marsh_log_a", "mudbank_bog", "marsh_reeds_b"], gap = ["bog_toadstools_small", "bog_flowers_small", "marsh_reeds_small"], trail = ["bog_charm"], keep = 0.9, mist = 0.45},
	"wisp_marsh": {wet = ["marsh_reeds_a", "marsh_cattails_a", "wisp_light_a", "marsh_cattails_b"], rim = ["marsh_cattails_a", "marsh_cattails_b", "marsh_reeds_a", "marsh_reeds_b", "wisp_light_b", "marsh_reeds_b"], dry = ["marsh_cattails_b", "marsh_reeds_b", "marsh_cattails_a", "marsh_reeds_a", "wisp_light_a", "marsh_tree_c", "marsh_log_b"], gap = ["marsh_reeds_small", "marsh_reeds_small"], trail = ["wisp_stake", "wisp_light_a", "wisp_light_b"], keep = 0.95, mist = 0.2},
	"rot_swamp": {wet = ["rot_scum", "rot_scum", "marsh_tree_c", "rot_rock"], rim = ["rot_rock", "rot_puddle", "marsh_log_b", "marsh_reeds_b", "marsh_reeds_a"], dry = ["rot_log", "marsh_tree_b", "rot_log", "mudbank_rot_swamp", "marsh_tree_c", "rot_rock", "marsh_reeds_b"], gap = ["rot_fungus", "marsh_reeds_small", "marsh_reeds_small"], trail = ["rot_puddle"], keep = 0.7, mist = 0.2},
	"plaguepit": {wet = [], rim = [], dry = ["rot_rock", "rot_puddle", "marsh_tree_c", "rot_fungus", "mudbank_plaguepit", "marsh_stump"], gap = [], trail = [], keep = 0.6, mist = 0.0},
	"smugglers_bayou": {wet = ["bayou_boat", "bayou_boat", "marsh_tree_c", "marsh_reeds_a"], rim = ["marsh_reeds_a", "marsh_reeds_b", "marsh_tree_b", "marsh_cattails_b", "marsh_log_b"], dry = ["marsh_tree_a", "marsh_tree_b", "bayou_goods", "marsh_log_a", "marsh_reeds_b", "marsh_tree_c", "marsh_reeds_a"], gap = ["bayou_crate", "marsh_reeds_small", "marsh_reeds_small"], trail = ["bayou_lantern"], keep = 0.85, mist = 0.15},
}
const PROP_CLEAR := 0.42
const COVER_CLEAR := 0.2    # ground cover keeps this far off planks and tracks
const FINISH := {"bog": "bog_trail_end", "wisp_marsh": "wisp_trail_end", "rot_swamp": "rot_trail_end", "smugglers_bayou": "bayou_landing"}
const SPUR_MAX := 2.6       # how far a shack may stand from the walkway its spur joins
const SHACK_FOOT := 0.62    # where its rope walkway meets the ground, ahead of its point
const MIST_POINTS := {"swamp": 2, "bog": 4, "wisp_marsh": 2}  # the engine's mist effect, per tile
const PROP_BUDGET := 3900   # everything on a tile but its slab (412)
const LANDMARK_TRIS := {"witchhut": 1098, "wisphollow": 641, "thievesguild": 1050, "plaguepit": 1167}

static var _grid := {}
static var _centre_gaps := []
static var _usual := {}       # local point -> its distance from the usual routes: every tile has the same grid points


static func pit_angle() -> float:
	return (-PIT_FOOT_Z / tan(deg_to_rad(PIT_TILT))) / PIT_LANE_R


static func pit_foot() -> float:
	return PIT_TOP - pit_angle()


static func _ring_point(k: int, radius: float) -> Vector2:
	var a := deg_to_rad(30.0 * k)
	return Vector2(radius * cos(a), radius * sin(a))


## From edge i's middle round the ring to edge gate's, the shorter way, curving in rather than turning at the ring.
static func _ring_walk(i: int, radius: float, gate := 0) -> Array:
	if i == gate:
		return [Water.turned(Vector2(2.9, 0.16), gate), Water.turned(Vector2(radius, 0.0), gate)]
	var steps := posmod(gate - i, 6)
	var way := 1 if steps <= 3 else -1
	var count := 2 * (steps if way > 0 else 6 - steps)
	var out := []
	for k in count:
		out.append(_ring_point(2 * i + way * (k + 1), radius))
	return out


## The Plague Pit's walked line, from z = 0 where it leaves the ground to its foot.
static func pit_lane(n := 10) -> Array:
	var out := []
	for k in n + 1:
		var a := PIT_TOP - pit_angle() * k / n
		out.append(Vector3(PIT_LANE_R * cos(a), PIT_LANE_R * sin(a), PIT_FOOT_Z * k / n))
	return out


static func pit_stop() -> Vector3:
	var a := pit_foot() - 0.2   # on the flat beyond the lane's foot, out on the spit, with the hole overhead
	return Vector3(1.6 * cos(a), 1.6 * sin(a), PIT_FOOT_Z)


## Where the walk leaves the lane's line, on the flat past its foot.
static func pit_turn() -> Vector3:
	var a := pit_foot() - 0.2
	return Vector3(PIT_LANE_R * cos(a), PIT_LANE_R * sin(a), PIT_FOOT_Z)


## {edge: walk (x, y, z)}, from each edge's middle to the landmark's stop, for the piece turned by turn.
static func landmark_routes(name: String, turn := 0) -> Dictionary:
	var routes := {}
	for i in 6:
		var start := Water.normal(i) * X1
		var out := []
		if name == "plaguepit":
			var a := PIT_TOP + 0.42   # on the land, lined up with the lane's first stretch
			var ground := Vector2(cos(a), sin(a)) * PIT_LANE_R
			var knots: Array = [start, start * LEAD]
			knots.append_array(_ring_walk(i, PIT_RING, 2))
			knots.append(ground)
			for q: Vector2 in curve(knots, 4):
				out.append(Vector3(q.x, q.y, 0.0))
			out.append_array(pit_lane())
			out.append(pit_turn())
			out.append(pit_stop())
		else:
			var stop: Vector3 = {"witchhut": HUT_STOP, "wisphollow": HOLLOW_STOP, "thievesguild": GUILD_STOP}[name]
			var knots: Array = [start, start * LEAD]
			knots.append_array(_ring_walk(i, RING, 0))
			for q: Vector2 in curve(knots, 4):
				out.append(Vector3(q.x, q.y, 0.0))
			if name == "wisphollow":
				out.append(stop)
			else:
				out.append(Vector3(RAMP_START, 0.0, 0.0))
				out.append(Vector3(RAMP_END, 0.0, stop.z))
		var turned := []
		for q: Vector3 in out:
			var p := Water.turned(Vector2(q.x, q.y), turn)
			turned.append(Vector3(p.x, p.y, q.z))
		routes[(i + turn) % 6] = turned
	return routes


## Smooth value noise in world space, 0 to 1.
static func noise(x: float, y: float, cell: float, salt: int) -> float:
	var u := x / cell
	var w := y / cell
	var ix := int(floor(u))
	var iy := int(floor(w))
	var fx := u - ix
	var fy := w - iy
	fx = fx * fx * (3 - 2 * fx)
	fy = fy * fy * (3 - 2 * fy)
	var a := GroundCover.hash01(ix, iy, salt)
	var b := GroundCover.hash01(ix + 1, iy, salt)
	var c := GroundCover.hash01(ix, iy + 1, salt)
	var d := GroundCover.hash01(ix + 1, iy + 1, salt)
	return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy


## Above 0 the land wants to be water here, before routes have their say.
static func wetness(look: String, x: float, y: float) -> float:
	var w: Dictionary = VIEW[look]
	if w.style == "broad":
		return 0.56 * noise(x, y, 4.8, 30) + 0.34 * noise(x, y, 2.1, 31) + 0.1 * noise(x, y, 0.9, 34) - w.level
	return w.level - absf(0.68 * noise(x, y, 4.4, 32) + 0.26 * noise(x, y, 1.9, 33) + 0.06 * noise(x, y, 0.9, 35) - 0.5)   # along a contour: long winding channels


## A line pushed sideways, most in its middle, level with its ends so it still meets the next tile's going the same way.
static func _bent_line(pts: Array, h1: float, h2: float) -> PackedVector2Array:
	var out := PackedVector2Array()
	var n := pts.size() - 1
	for k in pts.size():
		var t: Vector2 = pts[mini(n, k + 1)] - pts[maxi(0, k - 1)]
		var o := Vector2(-t.y, t.x) / t.length()
		var f := float(k) / n
		var s := sin(PI * f)
		out.append(pts[k] + o * (h1 * s * s + h2 * sin(TAU * f) * s))
	return out


## How a trail bends on this tile: always some, each its own way, within 0.3.
static func _wander(q: int, r: int, a: int, b: int) -> Vector2:
	var h := GroundCover.hash01(q * 36 + a * 6 + b, r, 40)
	var h1 := (0.15 + 0.11 * GroundCover.hash01(q * 36 + a * 6 + b, r, 41)) * (1.0 if h < 0.5 else -1.0)
	return Vector2(h1, 0.22 * (GroundCover.hash01(q * 36 + a * 6 + b, r, 42) - 0.5))


## The way a party walks on tile (q, r) from edge i to edge j along a trail: the usual curve between them, bent. The same line either way.
static func trail_line(q: int, r: int, i: int, j: int) -> PackedVector2Array:
	var a := mini(i, j)
	var b := maxi(i, j)
	var pa := Water.normal(a) * X1
	var pb := Water.normal(b) * X1
	var base := []
	for k in 25:
		base.append(pa * pow(1.0 - k / 24.0, 2.0) + pb * pow(k / 24.0, 2.0))
	var w := _wander(q, r, a, b)
	var line := _bent_line(base, w.x, w.y)
	if i != a:
		line.reverse()
	return line


## Which corner of the tile a trail starting here comes from, two or three corners round from edge i.
static func _end_corner(q: int, r: int, i: int) -> int:
	return posmod(i + [1, -2, 2, -3][int(GroundCover.hash01(q * 6 + i, r, 82) * 4)], 6)


## A trail that starts on this tile, the far end of a region's trail: from its finish, out in a corner, curving to edge i.
static func _trail_end(q: int, r: int, i: int) -> PackedVector2Array:
	var pa := Water.normal(i) * X1
	var c := Water.corner(_end_corner(q, r, i))
	var start := c * (END_START / Water.R)
	var ctrl := pa * 0.32
	var base := []
	for k in 25:
		var f := k / 24.0
		base.append(start * pow(1.0 - f, 2.0) + ctrl * (2.0 * f * (1.0 - f)) + pa * (f * f))
	var w := _wander(q, r, i, i)
	return _bent_line(base, w.x, w.y)


## A smooth line through points, by Catmull-Rom.
static func curve(pts: Array, each := 5) -> PackedVector2Array:
	var out := PackedVector2Array()
	var n := pts.size()
	for k in n - 1:
		var a: Vector2 = pts[maxi(0, k - 1)]
		var b: Vector2 = pts[k]
		var c: Vector2 = pts[k + 1]
		var d: Vector2 = pts[mini(n - 1, k + 2)]
		for j in each:
			var t := float(j) / each
			out.append((b * 2.0 + (c - a) * t + (a * 2.0 - b * 5.0 + c * 4.0 - d) * t * t + (b * 3.0 - a - c * 3.0 + d) * t * t * t) * 0.5)
	out.append(pts[-1])
	return out


## The nearest any of these lines comes to p. Called hundreds of times a tile, so seg_dist is written out and works on squares.
static func line_dist(p: Vector2, lines: Array) -> float:
	var best := INF
	for line in lines:
		var a: Vector2 = line[0]
		for k in range(1, line.size()):
			var b: Vector2 = line[k]
			var abx := b.x - a.x
			var aby := b.y - a.y
			var apx := p.x - a.x
			var apy := p.y - a.y
			var t := (apx * abx + apy * aby) / (abx * abx + aby * aby)
			t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
			var dx := apx - abx * t
			var dy := apy - aby * t
			var d := dx * dx + dy * dy
			if d < best:
				best = d
			a = b
	return sqrt(best)


## [[line, drawn]] for a tile's trail edges. Trails join the way out smoothly instead of meeting in the middle.
static func _tile_trails(terrains: Dictionary, q: int, r: int, edges: Array, out, turn := 0) -> Array:
	var name: String = terrains[Vector2i(q, r)]
	if edges.is_empty():
		return []
	var lines := []
	if LANDMARK_KEEP.has(name):
		var routes := landmark_routes(name, turn)
		var gate := (turn + (2 if name == "plaguepit" else 0)) % 6
		var sorted_edges := edges.duplicate()
		var rank := func(e: int) -> int:
			return (0 if e == gate else 100) + mini(posmod(e - gate, 6), posmod(gate - e, 6)) * 10 + edges.find(e)
		sorted_edges.sort_custom(func(a, b): return rank.call(a) < rank.call(b))
		for i: int in sorted_edges:
			var route: Array = routes[i]
			var end: Vector3 = route[-1]
			var line := PackedVector2Array()
			for s: Vector3 in route:
				if s.z == 0.0 and not (name == "wisphollow" and s.x == end.x and s.y == end.y):
					line.append(Vector2(s.x, s.y))
			lines.append(line)
	elif out == null:
		return []
	else:
		var ins := []
		for e: int in edges:
			if e != out:
				ins.append(e)
		ins.sort_custom(func(a, b): return GroundCover.hash01(q * 6 + a, r, 43) < GroundCover.hash01(q * 6 + b, r, 43))
		for e: int in ins:
			lines.append(trail_line(q, r, e, out))
		if lines.is_empty():
			lines.append(_trail_end(q, r, out))
	var done := []
	for line: PackedVector2Array in lines:
		var cut := line.size()
		if not done.is_empty():
			var drawn := []
			for d in done:
				drawn.append(d[1])
			for k in line.size():
				if line_dist(line[k], drawn) < 0.1:
					cut = k + 1
					break
		done.append([line, line.slice(0, cut)])
	return done


## A region's far tile: [corner k, x, y, spin] of what its trail ends at, or null.
static func _trail_finish(tile: Dictionary):
	if tile.edges.size() != 1 or LANDMARK_KEEP.has(tile.name) or tile.out == null:
		return null
	var k := _end_corner(tile.q, tile.r, tile.out)
	var p := Water.corner(k) * (END_R / Water.R)
	return [k, p.x, p.y, atan2(p.y, p.x)]


## World-space segments water can't cross near this tile: wherever marsh of one look meets anything else.
static func _closed_edges(terrains: Dictionary, q: int, r: int) -> Array:
	var out := []
	var c0 := Vector2i(q, r)
	var ts: Array = [c0]
	for n in Hex.NEIGHBOURS:
		ts.append(c0 + n)
	for t: Vector2i in ts:
		var seam = LOOKS.get(terrains.get(t))
		if seam == null:
			continue
		var c := Hex.tile_position(t.x, t.y)
		for i in 6:
			if LOOKS.get(terrains.get(t + Hex.NEIGHBOURS[i])) != seam:
				out.append([c + Water.corner(posmod(i - 1, 6)), c + Water.corner(i)])
	return out


## Each sixth of the tile as rows of points from its middle to edge i.
static func _grid_points() -> Dictionary:
	if _grid.is_empty():
		for i in 6:
			var ca := Water.corner(posmod(i - 1, 6))
			var cb := Water.corner(i)
			var rows := []
			for a in CELLS + 1:
				var row := PackedVector2Array()
				for b in a + 1:
					var f := float(b) / a if a > 0 else 0.0
					row.append(ca * (float(a) / CELLS * (1.0 - f)) + cb * (float(a) / CELLS * f))
				rows.append(row)
			_grid[i] = rows
	return _grid


## f(p) for local p: Vector2(W, B), water where W > 0, mud bank where B > 0.
static func _field_at(tile: Dictionary, p: Vector2) -> Vector2:
	var c: Vector2 = tile.centre
	var x: float = c.x + p.x
	var y: float = c.y + p.y
	var look: String = tile.look
	var n := wetness(look, x, y)
	var i := 0
	var top := -INF
	for e in 6:
		var v := p.dot(Water.normal(e))
		if v > top:
			top = v
			i = e
	var on_edge := top > X1 - 1e-5   # the art's 1e-6 is too fine for Vector2's float32: it missed points on an edge, and both tiles must agree there
	var d: float
	if on_edge:   # a route meets an edge only at its middle, on any tile, so both tiles agree here
		d = absf(p.dot(Vector2(-Water.normal(i).y, Water.normal(i).x)))
	elif tile.usual:
		var key := Vector2i(roundi(p.x * 10000.0), roundi(p.y * 10000.0))
		if _usual.has(key):
			d = _usual[key]
		else:
			d = line_dist(p, tile.lines)
			if _usual.size() < 4000:   # the grid's points; a scattered prop's aren't worth keeping
				_usual[key] = d
	else:
		d = line_dist(p, tile.lines)
	var nn := noise(x, y, 1.5, 36)
	var w := (d - WATER_DRY - 0.6 * nn * nn) * K   # never nearer than WATER_DRY, but not along a ruled line either
	if not tile.trail_lines.is_empty() and not on_edge:
		var near: float = WATER_TRAIL + (0.12 if look == "smugglers_bayou" else 0.0)
		w = minf(w, (line_dist(p, tile.trail_lines) - near) * K)
	var e := 9.0
	var world := Vector2(x, y)
	for s: Array in tile.closed:
		e = minf(e, Water.seg_dist(world, s[0], s[1]))
	var inner: float = (p.length() - tile.keep) * K
	var water: float = minf(minf(n, w), minf((e - CLOSE) * K, inner))
	if tile.pond != null:
		water = maxf(water, minf((POND_SIZE - p.distance_to(tile.pond)) * K, (d - WATER_DRY) * K))
	var bank: float = VIEW[look].bank
	var mud := maxf(minf(minf(n + bank, (e - 0.12) * K), inner), water + 0.035)
	return Vector2(water, mud)


## What _field_at says of p, to the signs a prop's choice reads (water above 0.015, mud above 0), skipping the routes' distance where
## the noise alone rules out water: it's most of the work.
static func _field_sign(tile: Dictionary, p: Vector2) -> Vector2:
	var c: Vector2 = tile.centre
	var look: String = tile.look
	var n := wetness(look, c.x + p.x, c.y + p.y)
	if n >= -0.035 or tile.pond != null:
		return _field_at(tile, p)
	var e := 9.0
	var world: Vector2 = c + p
	for s: Array in tile.closed:
		e = minf(e, Water.seg_dist(world, s[0], s[1]))
	var bank: float = VIEW[look].bank
	return Vector2(-1.0, minf(minf(n + bank, (e - 0.12) * K), (p.length() - tile.keep) * K))


## The part of a polygon of [x, y, W, B] where value k, times sign, is above 0.
static func _clip_poly(poly: Array, k: int, sign_: float) -> Array:
	var out := []
	for j in poly.size():
		var b: Array = poly[j]
		var a: Array = poly[j - 1]
		var va: float = a[k] * sign_
		var vb: float = b[k] * sign_
		if (va > 0) != (vb > 0):
			var f := va / (va - vb)
			out.append([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f])
		if vb > 0:
			out.append(b)
	return out


## {water: [[p, p, p]], bank: [...]}: flat triangles, anticlockwise, tile-local (x, y).
static func _water_mesh(tile: Dictionary) -> Dictionary:
	var seen := {}
	var out := {water = [], bank = []}
	var g_all := _grid_points()
	var at := func(p: Vector2) -> Array:
		var key := Vector2i(roundi(p.x * 100000.0), roundi(p.y * 100000.0))
		if not seen.has(key):
			var f := _field_at(tile, p)
			seen[key] = [p.x, p.y, f.x, f.y]
		return seen[key]
	var cut := func(t: Array) -> void:
		var v := [at.call(t[0]), at.call(t[1]), at.call(t[2])]
		var wet := _clip_poly(v, 2, 1.0)
		for m in range(1, wet.size() - 1):
			out.water.append([Vector2(wet[0][0], wet[0][1]), Vector2(wet[m][0], wet[m][1]), Vector2(wet[m + 1][0], wet[m + 1][1])])
		var mud := _clip_poly(_clip_poly(v, 3, 1.0), 2, -1.0)
		for m in range(1, mud.size() - 1):
			out.bank.append([Vector2(mud[0][0], mud[0][1]), Vector2(mud[m][0], mud[m][1]), Vector2(mud[m + 1][0], mud[m + 1][1])])
	# One big triangle where all of it is one thing, which saves three, else its four small ones.
	var block := func(big: Array, small: Array) -> void:
		var all_wet := true
		var all_mud := true
		var all_dry := true
		for t: Array in small:
			for q: Vector2 in t:
				var v: Array = at.call(q)
				all_wet = all_wet and v[2] > 0
				all_mud = all_mud and v[2] < 0 and v[3] > 0
				all_dry = all_dry and v[3] < 0
		if all_wet:
			out.water.append(big)
		elif all_mud:
			out.bank.append(big)
		elif not all_dry:
			for t: Array in small:
				cut.call(t)
	for i in 6:
		var g: Array = g_all[i]
		for a in range(0, CELLS, 2):
			for b in range(0, a + 1, 2):
				block.call([g[a][b], g[a + 2][b], g[a + 2][b + 2]], [[g[a][b], g[a + 1][b], g[a + 1][b + 1]], [g[a + 1][b], g[a + 2][b], g[a + 2][b + 1]], [g[a + 1][b], g[a + 2][b + 1], g[a + 1][b + 1]], [g[a + 1][b + 1], g[a + 2][b + 1], g[a + 2][b + 2]]])
				if b < a:
					block.call([g[a][b], g[a + 2][b + 2], g[a][b + 2]], [[g[a][b], g[a + 1][b + 1], g[a][b + 1]], [g[a][b + 1], g[a + 1][b + 1], g[a + 1][b + 2]], [g[a][b + 1], g[a + 1][b + 2], g[a][b + 2]], [g[a + 1][b + 1], g[a + 2][b + 2], g[a + 1][b + 2]]])
	return out


## Pairs [left, right] along a line. fade: the share of its length, from its start, over which it narrows to almost nothing.
static func ribbon(line: PackedVector2Array, half: float, fade := 0.0) -> Array:
	var out := []
	var n := line.size() - 1
	for k in line.size():
		var t: Vector2 = line[mini(n, k + 1)] - line[maxi(0, k - 1)]
		var o := Vector2(-t.y, t.x) / t.length()
		var w := half
		if fade > 0.0:
			w *= maxf(0.1, minf(1.0, (float(k) / n) / fade))
		out.append([line[k] + o * w, line[k] - o * w])
	return out


## The point s along a line, and its direction.
static func along(line: PackedVector2Array, s: float) -> Array:
	for k in range(1, line.size()):
		var a := line[k - 1]
		var b := line[k]
		var d := a.distance_to(b)
		if s <= d and d > 0:
			return [a + (b - a) * (s / d), (b - a) / d]
		s -= d
	var last := line[-1] - line[-2]
	return [line[-1], last / maxf(last.length(), 1e-6)]


static func line_length(line: PackedVector2Array) -> float:
	var total := 0.0
	for k in range(1, line.size()):
		total += line[k - 1].distance_to(line[k])
	return total


## The bayou's boardwalk: planks as trapezoids that follow the bend. [material, a-left, a-right, b-right, b-left].
static func planks(line: PackedVector2Array, half: float, seed_: int, each := 0.21) -> Array:
	var total := line_length(line)
	var n := maxi(1, int(total / each))
	var out := []
	for k in n:
		var s0 := total * k / n + 0.012
		var s1 := total * (k + 1) / n - 0.012
		var at0 := along(line, s0)
		var at1 := along(line, s1)
		var wa := half + 0.05 * (GroundCover.hash01(seed_, k, 44) - 0.5)
		var wb := half + 0.05 * (GroundCover.hash01(seed_, k, 45) - 0.5)
		var oa := Vector2(-at0[1].y, at0[1].x)
		var ob := Vector2(-at1[1].y, at1[1].x)
		out.append(["plank_dark" if GroundCover.hash01(seed_, k, 46) < 0.34 else "plank", at0[0] + oa * wa, at0[0] - oa * wa, at1[0] - ob * wb, at1[0] + ob * wb])
	return out


static func _gaps() -> Array:
	if _centre_gaps.is_empty():
		for k in 6:
			for ra: Vector2 in [Vector2(0.74, 29.5), Vector2(1.25, 11.0), Vector2(1.25, 49.5), Vector2(1.46, 30.5)]:
				var a := deg_to_rad(k * 60 + ra.y)
				_centre_gaps.append(Vector2(ra.x * cos(a), ra.x * sin(a)))
	return _centre_gaps


static func _crowded(p: Vector2, room: float, placed: Array) -> bool:
	for o: Array in placed:
		if p.distance_to(Vector2(o[1], o[2])) < room + PROP[o[0]][1]:
			return true
	return false


## [name, x, y, spin] on one tile, from a world hash. Each keeps its reach off the tile's walked lines, stays in the tile and doesn't crowd another.
static func _marsh_props(tile: Dictionary, spent: int) -> Array:
	var q: int = tile.q
	var r: int = tile.r
	var name: String = tile.name
	var look: String = tile.look
	var table: Dictionary = SCATTER[look]
	var c: Vector2 = tile.centre
	var budget: int = PROP_BUDGET - spent - LANDMARK_TRIS.get(name, 0)
	var lines: Array = tile.lines
	var trail_lines: Array = tile.trail_lines
	var placed: Array = tile.shack.duplicate()
	if tile.finish != null:
		placed.append([FINISH[look], tile.finish[1], tile.finish[2], tile.finish[3]])
	var spent_props := 0
	for o: Array in placed:
		spent_props += PROP[o[0]][2]
	var spurs: Array = tile.spurs
	var tile_half: float = WALK_HALF if look == "smugglers_bayou" else TRAIL_HALF
	var keep: float = tile.keep
	# along the trails first: what marks the way
	if not table.trail.is_empty():
		var half := tile_half
		for t in tile.trails.size():
			var drawn: PackedVector2Array = tile.trails[t][1]
			var total := line_length(drawn)
			var s := 0.5 + 0.8 * GroundCover.hash01(q * 6 + t, r, 47)
			var k := 0
			while s < total - 0.2:
				var a := along(drawn, s)
				var side := 1.0 if GroundCover.hash01(q * 6 + t, r + k, 48) < 0.5 else -1.0
				var prop: String = table.trail[int(GroundCover.hash01(q * 6 + t, r + k, 49) * table.trail.size())]
				var p: Vector2 = a[0] + Vector2(-a[1].y, a[1].x) * (side * (half + 0.24))
				if Water.inside_tile(p, PROP[prop][0]) and line_dist(p, lines) >= 0.16 and line_dist(p, trail_lines) >= half + 0.12 \
						and _off_spurs(p, 0.12, spurs) and p.length() >= keep and not _crowded(p, PROP[prop][1], placed):
					placed.append([prop, p.x, p.y, GroundCover.hash01(q * 6 + t, r + k, 50) * 6.283])
					spent_props += PROP[prop][2]
				s += (2.0 if tile.near <= 2 else 3.2) * (0.6 if look != "smugglers_bayou" else 1.0) + 0.9 * GroundCover.hash01(q * 6 + t, r + k, 51)   # thicker toward the landmark
				k += 1
	# the middle's gaps
	if not table.gap.is_empty() and not LANDMARK_KEEP.has(name):
		var gaps := _gaps()
		for k in gaps.size():
			if GroundCover.hash01(q * 6 + k, r, 52) < 0.7:
				var prop: String = table.gap[int(GroundCover.hash01(q * 6 + k, r, 53) * table.gap.size())]
				var p2: Vector2 = gaps[k] + Vector2(0.05 * (GroundCover.hash01(q * 6 + k, r, 54) - 0.5), 0.05 * (GroundCover.hash01(q * 6 + k, r, 55) - 0.5))
				if (trail_lines.is_empty() or line_dist(p2, trail_lines) >= tile_half + 0.12) and _off_spurs(p2, 0.1, spurs) and not _crowded(p2, PROP[prop][1], placed):
					placed.append([prop, p2.x, p2.y, GroundCover.hash01(q * 6 + k, r, 56) * 6.283])
					spent_props += PROP[prop][2]
	# a little mist that stays when the engine's effect is off, and only some tiles have it
	if GroundCover.hash01(q, r, 57) < table.mist:
		var a := GroundCover.hash01(q, r, 58) * 6.283
		var rad := 0.5 + 2.6 * GroundCover.hash01(q, r, 59)
		var p := Vector2(rad * cos(a), rad * sin(a))
		if p.length() >= keep and Water.inside_tile(p, 1.2):
			var prop := "marsh_mist_a" if GroundCover.hash01(q, r, 60) < 0.5 else "marsh_mist_b"
			placed.append([prop, p.x, p.y, a])
			spent_props += PROP[prop][2]
	# the scatter, by world cell, in a fixed order, so the budget thins it evenly
	var cell := 0.62
	var cands := []
	for ix in range(int(floor((c.x - Water.A) / cell)), int(ceil((c.x + Water.A) / cell))):
		for iy in range(int(floor((c.y - Water.R) / cell)), int(ceil((c.y + Water.R) / cell))):
			var x := (ix + GroundCover.hash01(ix, iy, 61)) * cell
			var y := (iy + GroundCover.hash01(ix, iy, 62)) * cell
			if GroundCover.tile_at(Vector2(x, y)) == Vector2i(q, r) and GroundCover.hash01(ix, iy, 63) < table.keep:
				cands.append([GroundCover.hash01(ix, iy, 64), ix, iy, x - c.x, y - c.y])
	cands.sort_custom(func(a, b): return a[0] < b[0])
	var signs := {}
	for big in [true, false]:   # what needs room first, or the small things would take it all
		for cand: Array in cands:
			var ix: int = cand[1]
			var iy: int = cand[2]
			var p := Vector2(cand[3], cand[4])
			var f: Vector2 = signs.get(ix * 100000 + iy, Vector2.INF)
			if f == Vector2.INF:
				f = _field_sign(tile, p)
				signs[ix * 100000 + iy] = f
			var pool: Array = table.wet if f.x > 0.015 else table.rim if f.y > 0 else table.dry
			var names := []
			for n: String in pool:
				if (PROP[n][0] >= 0.5) == big:
					names.append(n)
			if names.is_empty() or (big and GroundCover.hash01(ix, iy, 67) > 0.6):
				continue
			var start := int(GroundCover.hash01(ix, iy, 65) * names.size())
			var spin := GroundCover.hash01(ix, iy, 66) * 6.283
			for j in names.size():
				var prop: String = names[(start + j) % names.size()]
				if spent_props + PROP[prop][2] > budget:
					continue
				if _fits(tile, prop, p, spin, 0.22 if big else 0.0, placed, tile_half):
					placed.append([prop, cand[3], cand[4], spin])
					spent_props += PROP[prop][2]
					break
	return placed


static func _off_spurs(p: Vector2, r_: float, spurs: Array) -> bool:
	return spurs.is_empty() or line_dist(p, spurs) >= WALK_HALF + r_


static func _fits(tile: Dictionary, prop: String, p: Vector2, spin: float, trail_extra: float, placed: Array, tile_half: float) -> bool:
	var own: float = PROP[prop][0]
	var reach := maxf(own, PROP_CLEAR)   # a mini's base is about 0.52 either side of its line; only marks and the middle's small things stand closer
	var need := maxf(reach + trail_extra, tile_half + minf(own, 0.3) + 0.04)   # clear of the planks or track, not just the line
	if not Water.inside_tile(p, maxf(own, 0.08)) or p.length() < tile.keep + reach or _crowded(p, PROP[prop][1], placed):
		return false
	if not tile.trail_lines.is_empty() and line_dist(p, tile.trail_lines) < need:
		return false
	if not _off_spurs(p, minf(reach, 0.3), tile.spurs):
		return false
	if line_dist(p, tile.lines) < reach:
		return false
	if prop == "bayou_boat":
		var d := Vector2(cos(spin), sin(spin))
		return _field_at(tile, p - d * 0.5).x > 0.0 and _field_at(tile, p + d * 0.5).x > 0.0
	return true


## The bayou's shack on this tile and the plank spur joining it to a walkway: [shack list, spur list]. Out in a corner, facing the nearest walkway.
static func _shack_spot(tile: Dictionary) -> Array:
	var q: int = tile.q
	var r: int = tile.r
	var drawn := []
	for d in tile.trails:
		if d[1].size() > 1:
			drawn.append(d[1])
	if tile.look != "smugglers_bayou" or LANDMARK_KEEP.has(tile.name) or drawn.is_empty() or GroundCover.hash01(q, r, 68) >= 0.7:
		return [[], []]
	var ranks := {}
	for k in 6:
		var p := Water.corner(k) * (3.0 / Water.R)
		ranks[k] = [line_dist(p, drawn) > SPUR_MAX, _field_at(tile, p).x <= 0, GroundCover.hash01(q * 6 + k, r, 69)]
	var order := [0, 1, 2, 3, 4, 5]
	order.sort_custom(func(a, b):
		var x: Array = ranks[a]
		var y: Array = ranks[b]
		if x[0] != y[0]:
			return not x[0]
		if x[1] != y[1]:
			return not x[1]
		return x[2] < y[2])
	var reach: float = PROP.bayou_shack[0]
	for k: int in order:
		var p := Water.corner(k) * (3.0 / Water.R)
		var far := line_dist(p, drawn)
		if line_dist(p, tile.lines) < reach or far < reach or far > SPUR_MAX or (tile.finish != null and tile.finish[0] == k):
			continue
		var near_: Vector2 = drawn[0][0]
		var best := INF
		for line: PackedVector2Array in drawn:
			for m in range(1, line.size()):
				for f in 7:
					var c := line[m - 1] + (line[m] - line[m - 1]) * (f / 6.0)
					var dd := c.distance_to(p)
					if dd < best:
						best = dd
						near_ = c
		var d := (near_ - p) / p.distance_to(near_)
		var spin := atan2(d.y, d.x)
		var foot := p + d * SHACK_FOOT
		if line_dist(foot, drawn) <= WALK_HALF - 0.04:
			return [[["bayou_shack", p.x, p.y, spin]], []]   # its rope walkway lands on the boardwalk itself
		var ahead := foot.distance_to(near_) - 0.04   # well under the walkway, so its last plank can't leave a sliver
		var spur := PackedVector2Array()
		for f in 9:
			spur.append(p + d * (SHACK_FOOT - 0.16 + (ahead + 0.16) * f / 8.0))
		return [[["bayou_shack", p.x, p.y, spin]], [spur]]
	return [[], []]


static func _blob_outline(c: Vector2, long_: float, wide: float, spin: float, key: int, r: int) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for j in 7:
		var a := TAU * j / 7.0
		var m := 0.8 + 0.4 * GroundCover.hash01(key, j + r * 7, 77)
		var x_ := long_ * m * cos(a)
		var y_ := wide * m * sin(a)
		pts.append(c + Vector2(x_ * cos(spin) - y_ * sin(spin), x_ * sin(spin) + y_ * cos(spin)))
	return pts


## Where a track fades out at its finish: a few worn patches, thinning, so it doesn't stop on a line.
static func _track_flecks(tile: Dictionary) -> Array:
	if tile.finish == null or tile.look == "smugglers_bayou":
		return []
	var line: PackedVector2Array = tile.trails[0][0]
	var q: int = tile.q
	var r: int = tile.r
	var out := []
	for k in 6:
		var a := along(line, 0.15 + 0.32 * k)
		var side := TRAIL_HALF * 0.75 * (2 * GroundCover.hash01(q * 6 + k, r, 83) - 1) * (k / 5.0)
		var c: Vector2 = a[0] + Vector2(-a[1].y, a[1].x) * (side + (0.32 if k % 2 == 1 else -0.32))
		var pts := _blob_outline(c, 0.07 + 0.05 * GroundCover.hash01(q * 6 + k, r, 84), 0.04 + 0.03 * GroundCover.hash01(q * 6 + k, r, 85), atan2(a[1].y, a[1].x), q * 6 + k, r)
		var inside := true
		for p in pts:
			inside = inside and Water.inside_tile(p)
		if inside:
			out.append(pts)
	return out


## Rot swamp: patchy drips and small puddles of ooze near a trail's edge, never a line. [material, outline].
static func _ooze_patches(tile: Dictionary) -> Array:
	var out := []
	if tile.look != "rot_swamp":
		return out
	var q: int = tile.q
	var r: int = tile.r
	for t in tile.trails.size():
		var drawn: PackedVector2Array = tile.trails[t][1]
		var total := line_length(drawn)
		var s := 0.3 + 1.2 * GroundCover.hash01(q * 6 + t, r, 71)
		var k := 0
		while s < total - 0.3:
			var a := along(drawn, s)
			var key: int = q * 36 + t * 6 + k
			var side := 1.0 if GroundCover.hash01(key, r, 72) < 0.5 else -1.0
			var off := TRAIL_HALF - 0.08 + 0.42 * GroundCover.hash01(key, r, 73)
			var c: Vector2 = a[0] + Vector2(-a[1].y, a[1].x) * (side * off)
			var spin: float = atan2(a[1].y, a[1].x) + 1.4 * (GroundCover.hash01(key, r, 74) - 0.5)
			var pts := _blob_outline(c, 0.1 + 0.2 * GroundCover.hash01(key, r, 75), 0.05 + 0.08 * GroundCover.hash01(key, r, 76), spin, key, r)
			var inside := true
			for p in pts:
				inside = inside and Water.inside_tile(p, 0.04)
			if inside:
				out.append(["ooze" if GroundCover.hash01(key, r, 78) < 0.45 else "scum", pts])
			var h := GroundCover.hash01(key, r, 79)
			s += 0.55 + 1.7 * h * h
			k += 1
	return out


## Where the engine adds its effects on this tile: [kind, x, y, z].
static func _marsh_effects(tile: Dictionary) -> Array:
	var q: int = tile.q
	var r: int = tile.r
	var out := []
	for k in MIST_POINTS.get(tile.look, 0):
		var a := GroundCover.hash01(q * 6 + k, r, 80) * 6.283
		var rad := 0.4 + 2.8 * GroundCover.hash01(q * 6 + k, r, 81)
		if rad >= tile.keep:
			out.append(["mist", rad * cos(a), rad * sin(a), 0.12])
	if tile.look == "rot_swamp" and not LANDMARK_KEEP.has(tile.name):
		out.append(["haze", 0.0, 0.0, 0.5])
	return out


## Everything the wetland puts on tile (q, r). edges and out: its trail edges and the edge it heads out by; turn: a landmark's; near: steps
## from it. Rebuilt when a neighbour lands or the region finishes.
static func marsh_tile(terrains: Dictionary, q: int, r: int, edges := [], out = null, turn := 0, near := 9) -> Dictionary:
	var name: String = terrains[Vector2i(q, r)]
	var look: String = LOOKS[name]
	var tile := {q = q, r = r, name = name, look = look, keep = LANDMARK_KEEP.get(name, 0.0), near = near, edges = edges, out = out, centre = Hex.tile_position(q, r)}
	tile.finish = _trail_finish(tile)
	tile.usual = not LANDMARK_KEEP.has(name)
	if tile.usual:
		tile.lines = Sand._routes()
	else:
		var lines := []
		for line: Array in landmark_routes(name, turn).values():
			var flat := PackedVector2Array()
			for s: Vector3 in line:
				flat.append(Vector2(s.x, s.y))
			lines.append(flat)
		tile.lines = lines
	tile.trails = _tile_trails(terrains, q, r, edges, out, turn)
	var trail_lines := []
	for t in tile.trails:
		trail_lines.append(t[0])
	tile.trail_lines = trail_lines
	tile.closed = _closed_edges(terrains, q, r)
	tile.pond = null
	if look == "smugglers_bayou" and tile.finish != null:   # the landing stage's own pool, for its boat
		tile.pond = Water.corner(tile.finish[0]) * (POND_R / Water.R)
	tile.merge(_water_mesh(tile))
	tile.half = WALK_HALF if look == "smugglers_bayou" else TRAIL_HALF
	var shack := _shack_spot(tile)
	tile.shack = shack[0]
	tile.spurs = shack[1]
	tile.ooze = _ooze_patches(tile)
	tile.flecks = _track_flecks(tile)
	tile.effects = _marsh_effects(tile)
	var spent: int = 5 * (tile.ooze.size() + tile.flecks.size()) + tile.water.size() + tile.bank.size()
	for d: PackedVector2Array in tile.spurs:
		spent += int(line_length(d) / 0.21) * 10
	for t in tile.trails:
		var d: PackedVector2Array = t[1]
		spent += int(line_length(d) / 0.21) * 10 if look == "smugglers_bayou" else (d.size() - 1) * 2
	tile.props = _marsh_props(tile, spent)
	return tile


## Triangles on a tile: water, banks, trails and props, before its slab and a landmark's piece.
static func tile_tris(tile: Dictionary) -> int:
	var per := 10 if tile.look == "smugglers_bayou" else 2
	var total: int = tile.water.size() + tile.bank.size() + 5 * (tile.ooze.size() + tile.flecks.size())
	for o: Array in tile.props:
		total += PROP[o[0]][2]
	for d: PackedVector2Array in tile.spurs:
		total += int(line_length(d) / 0.21) * 10
	for t in tile.trails:
		var drawn: PackedVector2Array = t[1]
		total += (int(line_length(drawn) / 0.21) if per == 10 else drawn.size() - 1) * per
	return total


## For the ground cover: true where the wetland's mud or water lies, or on a tile's planks, tracks or trail finish. tiles: {tile: marsh_tile's dict}.
static func cover_wet(terrains: Dictionary, tiles: Dictionary, x: float, y: float, t: Vector2i) -> bool:
	var look = LOOKS.get(terrains.get(t))
	if look == null:
		return false
	var tile: Dictionary = tiles.get(t, {})
	if not tile.is_empty():
		var p: Vector2 = Vector2(x, y) - tile.centre
		var drawn: Array = tile.spurs.duplicate()
		for d in tile.trails:
			if d[1].size() > 1:
				drawn.append(d[1])
		if not drawn.is_empty() and line_dist(p, drawn) < tile.half + COVER_CLEAR:
			return true
		if tile.finish != null and p.distance_to(Vector2(tile.finish[1], tile.finish[2])) < PROP[FINISH[look]][0] + COVER_CLEAR:
			return true
	return look != "plaguepit" and wetness(look, x, y) + VIEW[look].bank > 0
