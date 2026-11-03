class_name DesertLands
extends RefCounted
## Port of art/scripts/desert_lands.py (tiles v60): badlands and oasis, whose flat ground is in tile pieces, not in
## world-space sand, and the routes of the Raider Stronghold, the Oasis Bazaar and the oasis pool. Routes are tile-frame
## (x, y, z), from an edge's midpoint to the landmark's stop, for a piece turned t steps.

const MESA_H := 2.3            # the Raider Stronghold's mesa
const BAZAAR_RING := 1.45      # the open ground round the well-house
const POOL_RING := 3.0         # routes round the pool, on the pool tile
const STRONGHOLD_TURN := 3     # on the map its ramp side always faces the default camera (design/07)
const RAMP_FOOT := Vector2(-2.85, 1.96)
const RAMP_TOP := Vector2(1.9, 1.96)   # it reaches the top's height here, then runs on flat as a landing
const FORT_SIDE := 1.45
const FORT_GATE := Vector2(2.0, 0.95)  # the stop: in the gate, on the top
const RIPPLE_DEG := 25.0       # the wind's one way across any oasis region
## desert_lands.py sets this from the map; fixed here, so a tile placed later doesn't move every ripple on the map.
const RIPPLE_REACH := 150.0


static func _polar(r: float, deg: float) -> Vector2:
	return Vector2(r, 0).rotated(deg_to_rad(deg))


## The walk on the ramp, from its foot to the gate.
static func ramp_walk() -> PackedVector3Array:
	var out := PackedVector3Array()
	const STEPS := 8
	for k in STEPS + 1:
		out.append(Vector3(RAMP_FOOT.x + (RAMP_TOP.x - RAMP_FOOT.x) * k / STEPS, RAMP_FOOT.y, MESA_H * k / STEPS))
	out.append(Vector3(2.0, RAMP_TOP.y, MESA_H))
	out.append(Vector3(2.0, FORT_SIDE, MESA_H))
	out.append(Vector3(FORT_GATE.x, FORT_GATE.y, MESA_H))
	return out


static func _turned(line: PackedVector3Array, t: int) -> PackedVector3Array:
	var out := PackedVector3Array()
	for p in line:
		var q := Water.turned(Vector2(p.x, p.y), t)
		out.append(Vector3(q.x, q.y, p.z))
	return out


## From each edge round the mesa to the ramp's foot, up it, and sideways onto the top to the gate. edge -> line.
static func stronghold_routes(t := 0) -> Dictionary:
	var back := [Vector2(-3.5, 0.9), Vector2(-3.45, RAMP_FOOT.y)]
	var low := [Vector2(2.4, -2.6), Vector2(0.0, -2.7), Vector2(-2.3, -2.4), Vector2(-3.3, -1.4)]
	var north := [Vector2(-3.25, 2.62), Vector2(-3.45, RAMP_FOOT.y)]
	var ways := {0: [Vector2(3.4, -1.2)] + low + back, 1: [Vector2(-0.5, 3.12), Vector2(-2.0, 3.2)] + north, 2: north, 3: back,
		4: [Vector2(-3.3, -1.4)] + back, 5: low.slice(1) + back}
	var out := {}
	for k in 6:
		var line := PackedVector3Array()
		var start := Water.normal(k) * Water.A
		line.append(Vector3(start.x, start.y, 0.0))
		for p: Vector2 in ways[k]:
			line.append(Vector3(p.x, p.y, 0.0))
		line.append_array(ramp_walk())
		out[(k + t) % 6] = _turned(line, t)
	return out


## Along a lane or between lanes to the open ground round the well-house, then round it to the one stop, on its +X side.
static func bazaar_routes(t := 0) -> Dictionary:
	var out := {}
	for k in 6:
		var a := 60 * k if k <= 3 else 60 * k - 360
		var start := Water.normal(k) * Water.A
		var line := PackedVector3Array([Vector3(start.x, start.y, 0.0)])
		var steps := absi(a) / 20
		if steps > 0:
			for s in steps + 1:
				var q := _polar(BAZAAR_RING, a * (1.0 - float(s) / steps))
				line.append(Vector3(q.x, q.y, 0.0))
		else:
			line.append(Vector3(BAZAAR_RING, 0.0, 0.0))
		out[(k + t) % 6] = _turned(line, t)
	return out


## The pool tile's ring points and spokes: edge i in to the ring at its angle, then round it (desert_lands.pool_route).
static func pool_ring() -> PackedVector2Array:
	var out := PackedVector2Array()
	for k in 18:
		out.append(_polar(POOL_RING, 20.0 * k))
	return out


## What stands at each tile corner of a badlands region: [owner tile, piece, x, y, degrees], world space. A corner with
## three badlands tiles round it may hold a wide mesa across all three; any other corner of a badlands tile may hold a
## wide mesa in that tile's corner alone. Some stretches stay open, from a slow pattern over the world. Nearest the
## Stronghold, camps and wagons take a share of the corners. Each corner's tiles are sorted, so it's the same every time.
static func badlands_features(terrains: Dictionary, dist: Dictionary) -> Array:
	var out := []
	var seen := {}
	var tiles: Array = terrains.keys()
	tiles.sort()
	for tile: Vector2i in tiles:
		var name: String = terrains[tile]
		if name != "badlands" and name != "raiderstronghold":
			continue
		var at := Hex.tile_position(tile.x, tile.y)
		for k in 6:
			var w := at + Water.corner(k)
			var kx := snappedf(w.x, 0.01)
			var ky := snappedf(w.y, 0.01)
			var key := Vector2i(roundi(kx * 100.0), roundi(ky * 100.0))
			if seen.has(key):
				continue
			seen[key] = true
			var ix := int(kx * 10.0)
			var iy := int(ky * 10.0)
			var round_it: Array = []
			for c: Vector2i in [tile, tile + Hex.NEIGHBOURS[k], tile + Hex.NEIGHBOURS[(k + 1) % 6]]:
				if terrains.get(c) == "badlands":
					round_it.append(c)
			if round_it.is_empty():
				continue
			round_it.sort()
			var near := 99
			for c: Vector2i in round_it:
				near = mini(near, dist.get(c, 3))
			var h := GroundCover.hash01(ix, iy, 31)
			var pick := GroundCover.hash01(ix, iy, 32)
			var open_land := 0.5 + 0.5 * sin(w.x / 7.3 + 1.1) * sin(w.y / 6.1 - 0.4)
			var kind: String
			if near == 1 and h < 0.3:
				kind = "camp" if h < 0.2 else "wagon"
			elif near == 2 and h < 0.15:
				kind = "post" if h < 0.07 else "wagon"
			elif h > 0.5 + 0.5 * open_land:
				continue   # open ground
			else:
				kind = ["big", "big", "big", "mid", "mid", "low", "low", "butte"][int(pick * 8.0)] if pick < 0.97 else "butte"
			var wide := kind in ["big", "mid", "low"]
			if wide and round_it.size() == 3:
				var corner_k := _corner_of(round_it[0], w)
				out.append([round_it[0], "badlands_mesa_" + kind, w.x, w.y, fposmod(60.0 * corner_k + 30.0 + 180.0 + 120.0 * int(GroundCover.hash01(ix, iy, 33) * 3.0), 360.0)])
				continue
			if kind == "butte" and round_it.size() == 3:
				out.append([round_it[0], "badlands_butte", w.x, w.y, 360.0 * GroundCover.hash01(ix, iy, 34)])
				continue
			for t: Vector2i in (round_it if wide else round_it.slice(0, 1)):
				var c := Hex.tile_position(t.x, t.y)
				var deg := fposmod(60.0 * _corner_of(t, w) + 30.0 + 180.0, 360.0)
				if wide:
					out.append([t, "badlands_kite_" + kind, w.x, w.y, deg])
				else:
					var q := c + (w - c) * (3.2 / Water.R)   # set back inside this tile
					out.append([t, "badlands_" + kind, q.x, q.y, deg])
	return out


static func _corner_of(t: Vector2i, w: Vector2) -> int:
	var c := Hex.tile_position(t.x, t.y)
	var best := 0
	var d := INF
	for k in 6:
		var e := (c + Water.corner(k)).distance_to(w)
		if e < d:
			d = e
			best = k
	return best


## The oasis's wind ripples on tile t, world space, all one way across the region: [x, y, length]. In uneven rows; none
## on the pool's or the Bazaar's tile, nor crossing out of open oasis sand.
static func oasis_ripples(terrains: Dictionary, t: Vector2i) -> Array:
	var out := []
	var deg := deg_to_rad(RIPPLE_DEG)
	var u := Vector2(cos(deg), sin(deg))
	var v := Vector2(-sin(deg), cos(deg))
	var c := Hex.tile_position(t.x, t.y)
	var mid_row := c.dot(v) / 1.05
	for r in range(int(floor(mid_row - (Water.R + 1.0) / 1.05)), int(ceil(mid_row + (Water.R + 1.0) / 1.05)) + 1):
		var s := -RIPPLE_REACH + 1.6 * GroundCover.hash01(r, 7, 43)
		var k := 0
		while s < RIPPLE_REACH:
			k += 1
			var long_ := GroundCover.hash01(r, k, 44) > 0.55
			var ln := 1.7 if long_ else 1.0
			if absf(s + ln / 2.0 - c.dot(u)) < Water.R + 2.0:
				var off := (GroundCover.hash01(r, k, 45) - 0.5) * 0.35
				var mid := u * (s + ln / 2.0) + v * (r * 1.05 + off)
				if GroundCover.tile_at(mid) == t and GroundCover.hash01(r, k, 46) < 0.72 \
						and terrains.get(GroundCover.tile_at(mid + u * ln * 0.5)) == "oasis" \
						and terrains.get(GroundCover.tile_at(mid - u * ln * 0.5)) == "oasis" \
						and terrains.get(t) == "oasis":
					out.append([mid.x, mid.y, ln])
			s += ln + 0.5 + 1.3 * GroundCover.hash01(r, k, 47)
	return out


## [bazaar tile, pool tile] for a finished oasis region. The Bazaar is any tile with a free neighbour in the region, picked
## by hash; the pool is that neighbour with most region neighbours of its own, so it sits away from the region's edge when
## it can. Ties go by hash, so it's the same every time for a tile set. Empty for a region with no two tiles side by side.
static func oasis_tiles(region: Array, seed_value := 0, taken := []) -> Array:
	var free := {}
	for t: Vector2i in region:
		if not t in taken:
			free[t] = true
	var near := func(t: Vector2i) -> Array:
		var a := []
		for n: Vector2i in Hex.NEIGHBOURS:
			if free.has(t + n):
				a.append(t + n)
		return a
	var bazaar = null
	var best := -INF
	for t: Vector2i in free:
		if not near.call(t).is_empty():
			var h := GroundCover.hash01(t.x + seed_value, t.y, 41)
			if h > best:
				best = h
				bazaar = t
	if bazaar == null:
		return []
	var pool = null
	var most := Vector2(-1, -INF)
	for t: Vector2i in near.call(bazaar):
		var score := Vector2(near.call(t).size(), GroundCover.hash01(t.x + seed_value, t.y, 42))
		if score > most:
			most = score
			pool = t
	return [bazaar, pool]
