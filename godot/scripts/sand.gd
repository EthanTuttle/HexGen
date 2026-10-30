class_name Sand
extends RefCounted
## Port of art/scripts/sand.py: the ground of desert tiles, shaped in world space so dunes carry on across
## joined desert tiles and every crest lines up with one wind direction. Flat near edges facing other
## terrain; cacti, rocks and dry bushes (or, on the wasteland, buried ruins, bones and dead trees) scattered
## from a world-space hash. Plan coordinates as in the art scripts (x east, y north).

const WIND := deg_to_rad(25.0)   # the wind blows along this direction; crests run across it
const FADE := Vector2(0.3, 2.2)  # flat within 0.3 m of a non-desert edge, full height from 2.2 m
const ND := 28                   # grid samples across one sixth of a tile: depth
const NV := 32                   # side to side
const PROP_CELL := 2.4
const DESERTS := ["desert", "wasteland"]  # the desert terrain and its variants


static func is_desert(name) -> bool:
	return name in DESERTS


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
	var swell := 0.55 * (0.75 + 0.25 * sin(w / 5.3)) * profile(phase, 0.7)
	return swell * 0.55 * flats(x, y) if look == "wasteland" else swell


static func _seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var t := clampf((p - a).dot(ab) / ab.dot(ab), 0.0, 1.0)
	return (p - (a + ab * t)).length()


## 0 near any edge of tile t facing a non-desert tile, 1 deep in the sand. (x, y) is world plan space.
static func fade(terrains: Dictionary, t: Vector2i, x: float, y: float) -> float:
	var p := Vector2(x, y) - Hex.tile_position(t.x, t.y)
	var near := 99.0
	for i in 6:
		if not is_desert(terrains.get(t + Hex.NEIGHBOURS[i])):
			near = minf(near, _seg_dist(p, Water.corner(i - 1), Water.corner(i)))
	var s := clampf((near - FADE.x) / (FADE.y - FADE.x), 0.0, 1.0)
	return s * s * (3 - 2 * s)


static func surface_z(terrains: Dictionary, t: Vector2i, x: float, y: float) -> float:
	return height(x, y, terrains[t]) * fade(terrains, t, x, y)


## The sand surface of desert tile t, tile-local, into piece p. Each sixth of the tile is a grid between
## the centre and one edge; edge samples sit where the neighbour's do, so joined tiles share their border.
static func add_surface(p: Piece, terrains: Dictionary, t: Vector2i, col: Color) -> void:
	var c := Hex.tile_position(t.x, t.y)
	var centre := Vector3(0, 0, surface_z(terrains, t, c.x, c.y) + 0.01)
	for i in 6:
		var n := Water.normal(i)
		var tn := Vector2(-n.y, n.x)
		var rows := []
		for a in ND + 1:
			var row := []
			for b in NV + 1:
				if a == 0:
					row.append(centre)
					continue
				var d := Water.A * a / ND
				var v := -1.0 + 2.0 * b / NV
				var q := n * d + tn * (v * d * tan(deg_to_rad(30.0)))
				row.append(Vector3(q.x, q.y, surface_z(terrains, t, c.x + q.x, c.y + q.y) + 0.01))
			rows.append(row)
		for a in ND:
			for b in NV:
				if a > 0:
					p.tri(rows[a][b], rows[a + 1][b], rows[a + 1][b + 1], col)
				p.tri(rows[a][b], rows[a + 1][b + 1], rows[a][b + 1], col)


## [kind, local x, local y, z, cell] of the props on desert tile t, from a world hash.
static func props(terrains: Dictionary, t: Vector2i) -> Array:
	var c := Hex.tile_position(t.x, t.y)
	var out := []
	for ix in range(int(floor((c.x - Water.A) / PROP_CELL)), int(ceil((c.x + Water.A) / PROP_CELL))):
		for iy in range(int(floor((c.y - Water.R) / PROP_CELL)), int(ceil((c.y + Water.R) / PROP_CELL))):
			var x := (ix + GroundCover.hash01(ix, iy, 10)) * PROP_CELL
			var y := (iy + GroundCover.hash01(ix, iy, 11)) * PROP_CELL
			if GroundCover.tile_at(Vector2(x, y)) != t or GroundCover.hash01(ix, iy, 12) > 0.45:
				continue
			if fade(terrains, t, x, y) < 0.8:
				continue
			var k := GroundCover.hash01(ix, iy, 13)
			var kind: String
			if terrains[t] == "wasteland":
				kind = ("cracked" if flats(x, y) < 0.05 and k < 0.45 else "column" if k < 0.3 else
						"wall" if k < 0.45 else "statue" if k < 0.55 else "bones" if k < 0.75 else "deadtree")
			else:
				kind = "cactus" if k < 0.5 else "rock" if k < 0.8 else "bush"
			out.append([kind, x - c.x, y - c.y, surface_z(terrains, t, x, y), Vector2i(ix, iy)])
	return out


## Desert tile t's sand and props as one mesh, placed at the tile's centre.
static func build_tile(terrains: Dictionary, t: Vector2i) -> MeshInstance3D:
	var p := Piece.new()
	var look: String = terrains[t]
	add_surface(p, terrains, t, Hex.colour(look))
	for item in props(terrains, t):
		var cell: Vector2i = item[4]
		var rng := PyRandom.new(GroundCover.hash01(cell.x, cell.y, 14))
		var at := Vector3(item[1], item[2], item[3] - 0.03)
		if look == "wasteland":
			_wasteland_prop(p, rng, item[0], at)
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


## Buried ruins, bones, dead trees and cracked earth for the wasteland, sunk a little into the sand.
static func _wasteland_prop(p: Piece, rng: PyRandom, kind: String, at: Vector3) -> void:
	var stone := Hex.colour("sandstone"); var bone := Hex.colour("bone"); var wood := Hex.colour("deadwood")
	var spin := rng.uniform(0, TAU)
	var along := Vector3(cos(spin), sin(spin), 0)
	match kind:
		"cracked":
			var ring := Water.circle(Vector2(at.x, at.y), rng.uniform(0.7, 1.1), rng, 0.25)
			var top := []
			for q in ring:
				top.append(Vector3(q.x, q.y, at.z + 0.045))  # just above the sand (drawn 0.01 up)
			p.poly(top, Hex.colour("cracked"))
		"column":  # a sandstone column, standing or broken off
			p.cylinder(at, 0.2, [0.5, 0.9, 1.4][rng.randbelow(3)], stone, 8, -0.25)
			if rng.random() < 0.5:
				p.log(at + along * 0.7, 0.18, 0.9, stone, spin, 0.05)
		"wall":  # the top of a buried wall
			for k in 3:
				var hgt := rng.uniform(0.3, 0.55)
				p.box(at + along * ((k - 1) * 0.42), Vector3(0.4, 0.3, hgt), stone, -0.2, spin + rng.uniform(-0.05, 0.05))
		"statue":  # a toppled statue: a body on its side and a head beside it
			p.box_rot(at + Vector3(0, 0, 0.12), Vector3(0.9, 0.38, 0.32), stone,
					Basis(Vector3(0, 0, 1), spin) * Basis(Vector3(1, 0, 0), 0.25))
			p.blob(at + along * 0.75, 0.2, stone, 0.05)
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
