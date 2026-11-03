class_name Sand
extends RefCounted
## Port of art/scripts/sand.py (tiles v60): the ground of desert tiles, shaped in world space so dunes carry on across
## joined desert tiles and every crest lines up with one wind direction. Flat near edges facing other
## sand or terrain; cacti, rocks and dry bushes (or, on the wasteland, buried ruins, bones and dead trees) scattered
## from a world-space hash, off the party's routes. Plan coordinates as in the art scripts (x east, y north).

const WIND := deg_to_rad(25.0)   # the wind blows along this direction; crests run across it
const FADE := Vector2(0.3, 2.8)  # flat within 0.3 m of an edge facing other sand or terrain, full height from 2.8 m
const ND := 14                   # grid samples across one sixth of a tile: depth
const NV := 16                   # side to side (swells are 6.5 m long)
const PROP_CELL := 1.4
const LOOKS := {"desert": "desert", "wasteland": "wasteland", "sandstonesphinx": "wasteland"}  # the desert terrain, its variants and landmarks -> whose sand
const DUNE_H := 2.2              # the Sphinx's dune, at its crest
const SPHINX_STOP := Vector2(3.1, 0.0)  # where the party stops, facing the altar, on the piece's +X
const PROP_R := {"cactus": 0.35, "rock": 0.3, "bush": 0.25, "cracked": 0.0, "column": 1.1, "wall": 1.15, "statue": 1.2, "bones": 0.7, "deadtree": 0.45}  # how far a prop reaches from its point

static var _route_lines := []


## One crest per unit of phase: a long gentle rise (windward share), then a short steep drop.
static func profile(phase: float, windward: float) -> float:
	var f := fposmod(phase, 1.0)
	if f < windward:
		return 0.5 - 0.5 * cos(PI * f / windward)
	return 0.5 + 0.5 * cos(PI * (f - windward) / (1 - windward))


## Wasteland only: 0 on flat patches of cracked earth, 1 where the swells rise.
static func flats(x: float, y: float) -> float:
	var t := 0.5 + 0.5 * sin(x / 4.3 + 0.7) * sin(y / 3.9 - 0.3)
	t = clampf((t - 0.25) / 0.35, 0.0, 1.0)
	return t * t * (3 - 2 * t)


static func height(x: float, y: float, look := "desert") -> float:
	var u := x * cos(WIND) + y * sin(WIND)     # along the wind
	var w := -x * sin(WIND) + y * cos(WIND)    # across it
	var phase := u / 6.5 + 0.25 * sin(w / 7.0 + 0.5) + 0.15 * sin(w / 3.1)
	var swell := 0.55 * (0.75 + 0.25 * sin(w / 5.3)) * profile(phase, 0.66)   # the steepest lee face stays under a mini base's tilt limit
	return swell * 0.55 * flats(x, y) if look == "wasteland" else swell


static func _seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var t := clampf((p - a).dot(ab) / ab.dot(ab), 0.0, 1.0)
	return (p - (a + ab * t)).length()


## 0 near any edge of tile t facing a tile with other sand or none, 1 deep in the sand. (x, y) is world plan space.
static func fade(terrains: Dictionary, t: Vector2i, x: float, y: float) -> float:
	var p := Vector2(x, y) - Hex.tile_position(t.x, t.y)
	var near := 99.0
	var look: String = LOOKS[terrains[t]]
	for i in 6:
		if LOOKS.get(terrains.get(t + Hex.NEIGHBOURS[i])) != look:
			near = minf(near, _seg_dist(p, Water.corner(i - 1), Water.corner(i)))
	var s := clampf((near - FADE.x) / (FADE.y - FADE.x), 0.0, 1.0)
	return s * s * (3 - 2 * s)


static func _smooth(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return t * t * (3 - 2 * t)


## 1 in the middle of a tile, 0 at its edges: how much of a landmark's dune stands here. p is tile-local.
static func rim(p: Vector2) -> float:
	return _smooth((3.85 - p.length()) / 2.4)   # round, so the dune has no creases


## The Sphinx's dune at p, in the piece's frame (+X its front): over its haunches and back flanks, gone before its
## shoulders so its forelegs lie clear.
static func dune(p: Vector2) -> float:
	return DUNE_H * rim(p) * _smooth((-0.2 - p.x) / 2.2) * _smooth((3.1 - absf(p.y)) / 1.6)


## The sand's height at world (x, y). turn: a landmark's 60 degree steps.
static func surface_z(terrains: Dictionary, t: Vector2i, x: float, y: float, turn := 0) -> float:
	var name: String = terrains[t]
	var swell := height(x, y, LOOKS[name]) * fade(terrains, t, x, y)
	if name != "sandstonesphinx":
		return swell
	var p := Vector2(x, y) - Hex.tile_position(t.x, t.y)
	return swell * (1.0 - rim(p)) + dune(Water.turned(p, -turn))


## How many 60 degree steps to turn the Sphinx (and the Echo Cave): it faces a tile of its region, the one nearest the
## default map camera, so its face shows.
static func sphinx_turn(tile: Vector2i, region: Array) -> int:
	for k in [5, 4, 0, 3, 1, 2]:
		if region.has(tile + Hex.NEIGHBOURS[k]):
			return k
	return 5


## routes[i] for all six edges, in the tile's frame, for the Sphinx turned t steps: from the edge's midpoint round the
## dune to SPHINX_STOP.
static func sphinx_routes(t: int) -> Dictionary:
	var ways := {0: [], 1: [Vector2(3.4, 1.1)], 2: [Vector2(0.7, 3.05), Vector2(2.6, 2.35), Vector2(3.4, 1.1)],
		3: [Vector2(-3.6, 1.7), Vector2(-2.1, 3.1), Vector2(0.7, 3.05), Vector2(2.6, 2.35), Vector2(3.4, 1.1)]}
	var out := {}
	for k in 6:
		var sd := 1.0 if k <= 3 else -1.0
		var line := PackedVector2Array([Water.turned(Water.normal(k) * Water.A, t)])
		for p: Vector2 in ways[k if k <= 3 else 6 - k]:
			line.append(Water.turned(Vector2(p.x, p.y * sd), t))
		line.append(Water.turned(SPHINX_STOP, t))
		out[(k + t) % 6] = line
	return out


## The curves the party can walk through a tile (sand.route_lines): between any two edges, and each edge to the middle.
static func _routes() -> Array:
	if _route_lines.is_empty():
		for i in 6:
			var a := Water.normal(i) * Water.A
			_route_lines.append([a, Vector2.ZERO])
			for j in range(i + 1, 6):
				var b := Water.normal(j) * Water.A
				var line := []
				for k in 9:
					line.append(a * pow(1.0 - k / 8.0, 2.0) + b * pow(k / 8.0, 2.0))
				_route_lines.append(line)
	return _route_lines


static func clear_of_routes(p: Vector2, r: float) -> bool:
	for line in _routes():
		for k in range(1, line.size()):
			if _seg_dist(p, line[k - 1], line[k]) < r:
				return false
	return true


## The sand's normal at world point (x, y), from the slope of the surface (plan coordinates).
static func _normal(terrains: Dictionary, t: Vector2i, x: float, y: float, turn: int) -> Vector3:
	const E := 0.08
	var dx := surface_z(terrains, t, x + E, y, turn) - surface_z(terrains, t, x - E, y, turn)
	var dy := surface_z(terrains, t, x, y + E, turn) - surface_z(terrains, t, x, y - E, turn)
	return Vector3(-dx, -dy, 2 * E).normalized()


## The sand surface of desert tile t, tile-local, into piece p.
## Engine change: smooth normals. tiles v9's coarser grid (14 x 16) showed as stair-steps along the
## crests with flat shading; normals from the height function keep the swells soft at any grid size. Each sixth of the tile is a grid between
## the centre and one edge; edge samples sit where the neighbour's do, so joined tiles share their border.
static func add_surface(p: Piece, terrains: Dictionary, t: Vector2i, col: Color, turn := 0) -> void:
	var c := Hex.tile_position(t.x, t.y)
	var centre := Vector3(0, 0, surface_z(terrains, t, c.x, c.y, turn) + 0.01)
	var centre_n := _normal(terrains, t, c.x, c.y, turn)
	for i in 6:
		var n := Water.normal(i)
		var tn := Vector2(-n.y, n.x)
		var rows := []
		var normals := []
		for a in ND + 1:
			var row := []
			var nrow := []
			for b in NV + 1:
				if a == 0:
					row.append(centre)
					nrow.append(centre_n)
					continue
				var d := Water.A * a / ND
				var v := -1.0 + 2.0 * b / NV
				var q := n * d + tn * (v * d * tan(deg_to_rad(30.0)))
				row.append(Vector3(q.x, q.y, surface_z(terrains, t, c.x + q.x, c.y + q.y, turn) + 0.01))
				nrow.append(_normal(terrains, t, c.x + q.x, c.y + q.y, turn))
			rows.append(row)
			normals.append(nrow)
		for a in ND:
			for b in NV:
				p.tri_smooth(rows[a][b], rows[a + 1][b], rows[a + 1][b + 1],
						normals[a][b], normals[a + 1][b], normals[a + 1][b + 1], col)
				if a > 0:
					p.tri_smooth(rows[a][b], rows[a + 1][b + 1], rows[a][b + 1],
							normals[a][b], normals[a + 1][b + 1], normals[a][b + 1], col)


## A wasteland tile's buried ruins, tile-local: [kind, x, y], at most one in each of the six corners of the tile, the only
## room clear of every route. More of them, and more that stand tall, toward the Sphinx (near: steps from it).
static func ruins(t: Vector2i, near) -> Array:
	var out := []
	var keep: float = {1: 0.9, 2: 0.5}.get(near, 0.18)
	for k in 6:
		if GroundCover.hash01(t.x * 6 + k, t.y, 17) > keep:
			continue
		var a := Water.corner(k)   # between edges k and k + 1
		var u := 2.9 + 0.2 * GroundCover.hash01(t.x * 6 + k, t.y, 18)
		var side := 0.14 * (GroundCover.hash01(t.x * 6 + k, t.y, 19) - 0.5)
		var w := GroundCover.hash01(t.x * 6 + k, t.y, 20)
		out.append(["column" if w < 0.45 else "wall" if w < 0.75 else "statue", a.x / Water.R * u - a.y / Water.R * side, a.y / Water.R * u + a.x / Water.R * side])
	return out


## [kind, local x, local y, z, cell] of the props on desert tile t, from a world hash. They keep off the party's routes and
## stay in the tile. near: on a wasteland tile, its steps from the landmark. The Sphinx's tile has none: its piece holds its own.
static func props(terrains: Dictionary, t: Vector2i, near = null) -> Array:
	var c := Hex.tile_position(t.x, t.y)
	var out := []
	if terrains[t] == "sandstonesphinx":
		return out
	var waste: bool = terrains[t] == "wasteland"
	var cell := 1.8 if waste else PROP_CELL
	var keep := 0.6 if waste else 0.5
	for ix in range(int(floor((c.x - Water.A) / cell)), int(ceil((c.x + Water.A) / cell))):
		for iy in range(int(floor((c.y - Water.R) / cell)), int(ceil((c.y + Water.R) / cell))):
			var x := (ix + GroundCover.hash01(ix, iy, 10)) * cell
			var y := (iy + GroundCover.hash01(ix, iy, 11)) * cell
			if GroundCover.tile_at(Vector2(x, y)) != t or GroundCover.hash01(ix, iy, 12) > keep:
				continue
			if fade(terrains, t, x, y) < 0.8:
				continue
			var k := GroundCover.hash01(ix, iy, 13)
			var kind: String
			if waste:
				kind = "cracked" if flats(x, y) < 0.05 and k < 0.3 else "bones" if k < 0.6 else "deadtree"
			else:
				kind = "cactus" if k < 0.55 else "rock" if k < 0.8 else "bush"
			var p := Vector2(x, y) - c
			if clear_of_routes(p, PROP_R[kind]) and Water.inside_tile(p, PROP_R[kind]):
				out.append([kind, p.x, p.y, surface_z(terrains, t, x, y), Vector2i(ix, iy)])
	if waste:
		var ruin := ruins(t, near)
		for j in ruin.size():
			var r: Array = ruin[j]
			var p := Vector2(r[1], r[2])
			if clear_of_routes(p, PROP_R[r[0]]) and Water.inside_tile(p, PROP_R[r[0]]):
				out.append([r[0], p.x, p.y, surface_z(terrains, t, c.x + p.x, c.y + p.y), Vector2i(t.x * 6 + j, t.y)])
	return out


## Desert tile t's sand and props as one mesh, placed at the tile's centre. near and turn: see props and surface_z.
static func build_tile(terrains: Dictionary, t: Vector2i, near = null, turn := 0) -> MeshInstance3D:
	var p := Piece.new()
	var look: String = LOOKS[terrains[t]]
	add_surface(p, terrains, t, Hex.colour(look), turn)
	for item in props(terrains, t, near):
		var cell: Vector2i = item[4]
		var rng := PyRandom.new(GroundCover.hash01(cell.x, cell.y, 14))
		var at := Vector3(item[1], item[2], item[3] - 0.03)
		if look == "wasteland":
			_wasteland_prop(p, rng, item[0], at, near)
		elif item[0] == "cactus":
			_cactus(p, rng, at)
		elif item[0] == "rock":
			p.blob(at, rng.uniform(0.18, 0.3), Hex.colour("rock_light"), 0.0, 0.6)
		else:
			p.blob(at, rng.uniform(0.15, 0.22), Hex.colour("scrub"), 0.0, 0.7)
	var mi := p.instance("sand")
	mi.position = Hex.to3(Hex.tile_position(t.x, t.y))
	return mi


## build_tiles.cactus
static func _cactus(p: Piece, rng: PyRandom, at: Vector3) -> void:
	var col := Hex.colour("cactus")
	var h := rng.uniform(0.8, 1.25)
	p.cylinder(at, 0.12, h, col, 6)
	p.blob(at, 0.12, col, h, 0.8)
	for side in [-1, 1]:
		if rng.random() < 0.7:
			var z0 := rng.uniform(0.3, 0.55) * h
			p.box(at + Vector3(side * 0.17, 0, 0), Vector3(0.2, 0.12, 0.11), col, z0)
			p.cylinder(at + Vector3(side * 0.27, 0, 0), 0.075, rng.uniform(0.3, 0.45), col, 6, z0)


## Buried ruins, bones, dead trees and cracked earth for the wasteland, sunk a little into the sand. Ruins stand taller
## toward the Sphinx (near).
static func _wasteland_prop(p: Piece, rng: PyRandom, kind: String, at: Vector3, near = null) -> void:
	var stone := Hex.colour("sandstone"); var bone := Hex.colour("bone"); var wood := Hex.colour("deadwood")
	var spin := rng.uniform(0, TAU)
	var along := Vector3(cos(spin), sin(spin), 0)
	match kind:
		"cracked":
			# lifted with the sand under it, so the patch shows
			p.prism(Water.circle(Vector2(at.x, at.y), rng.uniform(0.7, 1.1), rng, 0.25), at.z, at.z + 0.045,
					Hex.colour("cracked"))
		"column":  # a sandstone column with its capital, standing or broken off, often a fallen drum
			var heights: Array = {1: [1.3, 1.7, 2.1], 2: [0.9, 1.4]}.get(near, [0.6, 0.95])
			var h: float = heights[rng.randbelow(heights.size())]
			p.cylinder(at, 0.26, h, stone, 8, -0.3)
			if h > 1.5 and rng.random() < 0.6:  # the rest have lost their capitals
				p.cylinder(at, 0.34, 0.1, Hex.colour("sphinx_light"), 8, h - 0.34)
				p.box(at, Vector3(0.62, 0.62, 0.14), stone, h - 0.24, spin)
			if rng.random() < 0.3:
				p.log(at + along * 0.75, 0.24, 0.55, stone, spin, 0.08)
		"wall":  # the top of a buried wall, stepped where it has crumbled
			var top := rng.uniform(0.6, 1.0)
			for k in 4:
				top = maxf(0.25, top + rng.uniform(-0.25, 0.2))
				p.box(at + along * ((k - 1.5) * 0.5), Vector3(0.48, 0.38, top), stone, -0.25, spin + rng.uniform(-0.05, 0.05))
		"statue":  # a toppled statue: a body on its side, a plinth and a head beside it
			p.box(at - along * 0.9, Vector3(0.6, 0.6, 0.45), stone, -0.15, spin)
			p.box_rot(at + Vector3(0, 0, 0.18), Vector3(1.3, 0.52, 0.45), stone,
					Basis(Vector3(0, 0, 1), spin) * Basis(Vector3(1, 0, 0), 0.25))
			p.blob(at + along * 1.0, 0.3, stone, 0.12)
		"bones":  # a spine with ribs and a skull
			p.log(at, 0.035, 1.0, bone, spin, 0.04)
			var side := Vector3(-along.y, along.x, 0)
			for k in 4:
				for s in [-1, 1]:
					p.log(at + along * (k * 0.18 - 0.3) + side * (s * 0.2), 0.025, 0.35, bone, spin + PI / 2, 0.06)
			p.blob(at + along * 0.62, 0.12, bone, 0.06, 0.8)
		_:  # a dead tree
			var h := rng.uniform(1.1, 1.6)
			p.cone(at, 0.11, h, wood, 5)
			for z in [0.5, 0.75]:
				var ang := rng.uniform(0, TAU)
				p.log(at + Vector3(cos(ang), sin(ang), 0) * 0.18, 0.03, 0.4, wood, ang, z * h, 4)
