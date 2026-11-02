class_name Cliffs
extends RefCounted
## Port of art/scripts/cliffs.py: raised hills regions stand on a cliff, with ledges climbing it (design/06 -> Tile
## build; art/handoff/hills_kit.md -> Raised regions). Worked out when a region finishes, and again whenever land near
## it changes.

## Only these stand on cliffs (DOCS: design/06 -> Tile build, Nov 2, 2026); cliffs.py's list still has four, and
## highlands and monastery heights have the pieces if that changes.
const RAISED := ["snowy_peaks", "volcanic_peaks"]
const UNWALKABLE := ["river"]                        # as in FenceGates
const NOT_CLEAR := ["forest", "farmland", "village"] # trees or a fence between the foot and the land beyond it


static func beside(t: Vector2i, i: int) -> Vector2i:
	return t + Hex.NEIGHBOURS[posmod(i, 6)]


## region: the tiles of a raised region, as a dictionary or array. raised: all raised tiles. The [tile, edge] pairs
## with a cliff: those facing a tile that's neither in the region nor raised.
static func outer_edges(region: Array, raised: Dictionary) -> Array:
	var inside := {}
	for t in region:
		inside[t] = true
	var out := []
	for t: Vector2i in region:
		for i in 6:
			var n := beside(t, i)
			if not inside.has(n) and not raised.has(n):
				out.append([t, i])
	return out


## The [tile, corner] pairs where the region's edge turns outward; corner i lies between edges i and i + 1.
static func outer_corners(region: Array, raised: Dictionary) -> Array:
	var outer := {}
	for e in outer_edges(region, raised):
		outer[e] = true
	var out := []
	for e in outer:
		if outer.has([e[0], (e[1] + 1) % 6]):
			out.append(e)
	return out


## A foot opens onto the tile on edge i - 1 only if that tile and the three tiles beyond it, in front of the foot,
## aren't raised.
static func foot_is_open(t: Vector2i, i: int, raised: Dictionary) -> bool:
	var ahead := beside(t, i - 1)
	return not raised.has(ahead) and not raised.has(beside(ahead, i - 2)) and not raised.has(beside(ahead, i - 1)) \
			and not raised.has(beside(ahead, i))


## Which ledges show: [t, i] runs round edges i - 1, i and i + 1 of tile t, all outer, with its foot on edge i - 1.
## terrains: tile -> terrain (variants and landmarks already turned into their terrain).
static func climbs(region: Array, terrains: Dictionary, raised_tiles: Dictionary) -> Array:
	var raised := raised_tiles.duplicate()
	for t in region:
		raised[t] = true
	var outer := {}
	for e in outer_edges(region, raised):
		outer[e] = true
	var ranked := []
	for e in outer:
		if outer.has([e[0], posmod(e[1] - 1, 6)]) and outer.has([e[0], (e[1] + 1) % 6]) and foot_is_open(e[0], e[1], raised):
			ranked.append(e)
	ranked.sort_custom(func(a, b): return _rank(a) < _rank(b))
	var taken := []
	for e in ranked:
		if taken.size() >= maxi(2, outer.size() / 6):
			break
		var t: Vector2i = e[0]
		if taken.all(func(o): return o[0] != t and not Hex.NEIGHBOURS.has(o[0] - t)):
			taken.append(e)
	var shown := taken.filter(func(e): return _clear(e, terrains))
	if shown.is_empty():
		shown = ranked.filter(func(e): return _clear(e, terrains)).slice(0, 1)
	if shown.is_empty():
		shown = ranked.filter(func(e): return _walkable(e, terrains)).slice(0, 1)
	return shown


static func _rank(e: Array) -> float:
	return GroundCover.hash01(e[0].x * 6 + e[1], e[0].y, 15)


static func _walkable(e: Array, terrains: Dictionary) -> bool:
	return not terrains.get(beside(e[0], e[1] - 1), "river") in UNWALKABLE


static func _clear(e: Array, terrains: Dictionary) -> bool:
	return _walkable(e, terrains) and not terrains[beside(e[0], e[1] - 1)] in NOT_CLEAR
