class_name GroundCover
extends RefCounted
## Port of art/scripts/ground_cover.py: tufts, flowers and pebbles scattered from one world-space
## pattern, with density per terrain fading toward the neighbour's within BLEND metres of an edge.

const CELL := 0.55
const BLEND := 1.6
## Share of cells that get a prop, per terrain (placeholders from ground_cover.py).
const DENSITY := {"plains": 0.5, "river": 0.3, "forest": 0.18, "farmland": 0.0, "village": 0.0}

const R := Water.R
const A := Water.A


static func hash01(ix: int, iy: int, k: int) -> float:
	var h := (ix * 374761393 + iy * 668265263 + k * 1442695041) & 0xFFFFFFFF
	h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
	h ^= h >> 16
	return h / 4294967296.0


## Axial (q, r) of the pointy-top tile holding plan point p (hexkit.tile_position, inverted).
static func tile_at(p: Vector2) -> Vector2i:
	var r := -p.y / (1.5 * R)
	var q := p.x / (2 * A) - r / 2
	var s := -q - r
	var rq := roundf(q); var rr := roundf(r); var rs := roundf(s)
	var dq := absf(rq - q); var dr := absf(rr - r); var ds := absf(rs - s)
	if dq > dr and dq > ds:
		rq = -rr - rs
	elif dr > ds:
		rr = -rq - rs
	return Vector2i(int(rq), int(rr))


static func density(terrains: Dictionary, p: Vector2) -> float:
	var t := tile_at(p)
	if not terrains.has(t):
		return 0.0
	var local := p - Hex.tile_position(t.x, t.y)
	var d_own: float = DENSITY[terrains[t]]
	var dens := d_own
	for i in 6:
		var to_edge := A - local.dot(Water.normal(i))
		if to_edge < BLEND:
			var other = terrains.get(t + Hex.NEIGHBOURS[i])
			var d_other: float = DENSITY[other] if other != null else d_own
			dens += 0.5 * (1 - to_edge / BLEND) * (d_other - d_own)
	return maxf(0.0, dens)


## [kind, plan point, cell] for the whole map. water_shapes maps (q, r) -> tile_water() result.
static func scatter(terrains: Dictionary, water_shapes: Dictionary) -> Array:
	var x0 := INF; var x1 := -INF; var y0 := INF; var y1 := -INF
	for t: Vector2i in terrains:
		var c := Hex.tile_position(t.x, t.y)
		x0 = minf(x0, c.x); x1 = maxf(x1, c.x); y0 = minf(y0, c.y); y1 = maxf(y1, c.y)
	var out := []
	for ix in range(int(floor((x0 - A) / CELL)), int(ceil((x1 + A) / CELL))):
		for iy in range(int(floor((y0 - R) / CELL)), int(ceil((y1 + R) / CELL))):
			var p := Vector2((ix + hash01(ix, iy, 0)) * CELL, (iy + hash01(ix, iy, 1)) * CELL)
			var item := _keep(terrains, water_shapes, ix, iy, p)
			if not item.is_empty():
				out.append(item)
	return out


## [kind, point, cell] if cell (ix, iy) gets a prop, else [].
static func _keep(terrains: Dictionary, water_shapes: Dictionary, ix: int, iy: int, p: Vector2) -> Array:
	var dens := density(terrains, p)
	if hash01(ix, iy, 3) >= dens:
		return []
	var t := tile_at(p)
	if water_shapes.has(t):
		var local := p - Hex.tile_position(t.x, t.y)
		var w: Dictionary = water_shapes[t]
		if w.outlines.any(func(o): return Water.point_in(o, local)):
			return []
		if _near_shore(local, w.shores, 0.45):
			return []
	var k := hash01(ix, iy, 2)
	return ["tuft" if k < 0.7 else "flower" if k < 0.93 else "pebble", p, Vector2i(ix, iy)]


static func _near_shore(p: Vector2, shores: Array, d: float) -> bool:
	for c: PackedVector2Array in shores:
		for s in c:
			if (p - s).length() < d:
				return true
	return false


## The ground cover of one tile: the cells of the world-space pattern whose point lands in it.
## Gives the same props as the whole-map scatter, so tiles can be rebuilt one at a time.
static func build_tile(terrains: Dictionary, water_shapes: Dictionary, t: Vector2i) -> MeshInstance3D:
	var c := Hex.tile_position(t.x, t.y)
	var items := []
	for ix in range(int(floor((c.x - A) / CELL)), int(ceil((c.x + A) / CELL))):
		for iy in range(int(floor((c.y - R) / CELL)), int(ceil((c.y + R) / CELL))):
			var p := Vector2((ix + hash01(ix, iy, 0)) * CELL, (iy + hash01(ix, iy, 1)) * CELL)
			if tile_at(p) != t:
				continue
			var item := _keep(terrains, water_shapes, ix, iy, p)
			if not item.is_empty():
				items.append(item)
	return _build(items)


static func build(terrains: Dictionary, water_shapes: Dictionary) -> MeshInstance3D:
	return _build(scatter(terrains, water_shapes))


static func _build(items: Array) -> MeshInstance3D:
	var piece := Piece.new()
	var ink := Hex.colour("grass_ink"); var flower := Hex.colour("flower"); var rock := Hex.colour("rock")
	for item in items:
		var cell: Vector2i = item[2]
		var rng := PyRandom.new(hash01(cell.x, cell.y, 4))
		var at := Vector3(item[1].x, item[1].y, 0)
		match item[0]:
			"tuft":
				var radius := rng.uniform(0.12, 0.2)
				var height := rng.uniform(0.2, 0.35)
				piece.cone(at, radius, height, ink, 4, 0.0, rng.uniform(0, 1))
			"flower":
				piece.box(at, Vector3(0.08, 0.08, 0.12), flower, 0.0, rng.uniform(0, 1))
			_:
				piece.blob(at, rng.uniform(0.07, 0.12), rock, 0.0, 0.6)
	return piece.instance("ground_cover")
