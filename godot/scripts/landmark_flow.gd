class_name LandmarkFlow
extends RefCounted
## Port of art/scripts/landmark_flow.py: which way each tile of a finished region leads to its landmark
## (design/06 -> Tile build -> Trails to the landmark). Worked out once when the region finishes, from the game's
## own region tiles, and never changed as the map grows.


## region: the region's tiles (its landmark included). Returns {dist = tile -> steps to the landmark,
## toward = tile -> the region neighbour one step closer}, ties broken by hash01(q, r, 9).
static func flow(region: Array, landmark: Vector2i) -> Dictionary:
	var inside := {}
	for t in region:
		inside[t] = true
	var dist := {landmark: 0}
	var frontier: Array[Vector2i] = [landmark]
	while not frontier.is_empty():
		var nxt: Array[Vector2i] = []
		for t in frontier:
			for n in Hex.NEIGHBOURS:
				var c: Vector2i = t + n
				if inside.has(c) and not dist.has(c):
					dist[c] = dist[t] + 1
					nxt.append(c)
		frontier = nxt
	var toward := {}
	for t: Vector2i in dist:
		var d: int = dist[t]
		if d == 0:
			continue
		var closer := []
		for n in Hex.NEIGHBOURS:
			if dist.get(t + n, -1) == d - 1:
				closer.append(t + n)
		toward[t] = closer[int(GroundCover.hash01(t.x, t.y, 9) * closer.size())]
	return {dist = dist, toward = toward}


## A tile added to a finished raised region: the old tiles keep their distances, trails and the landmark's turn, and
## only the new tile gets a distance and toward step, into its nearest neighbour, ties by the same hash. Changes dist
## and toward in place. Does nothing if no neighbour is in the region.
static func extend(tile: Vector2i, dist: Dictionary, toward: Dictionary) -> void:
	var near := []
	for n in Hex.NEIGHBOURS:
		if dist.has(tile + n):
			near.append(tile + n)
	if near.is_empty():
		return
	var d: int = near.map(func(n): return dist[n]).min()
	var closer := near.filter(func(n): return dist[n] == d)
	dist[tile] = d + 1
	toward[tile] = closer[int(GroundCover.hash01(tile.x, tile.y, 9) * closer.size())]


## The edges i of `tile` that are trail edges: its own toward step, and any neighbour's step into it.
static func trail_edges(tile: Vector2i, toward: Dictionary) -> Array:
	var out := []
	for i in 6:
		var n: Vector2i = tile + Hex.NEIGHBOURS[i]
		if toward.get(tile) == n or toward.get(n) == tile:
			out.append(i)
	return out


## True where `tile` is the closer of the two tiles on its trail edge i, so the way to the landmark runs in from
## the edge toward this tile's middle (it uses <variant>_edge_trail_in where that exists).
static func heads_in(tile: Vector2i, i: int, dist: Dictionary) -> bool:
	return dist.get(tile, 0) < dist.get(tile + Hex.NEIGHBOURS[i], 0)


## The edge of `tile` its toward step crosses: how many 60 degree steps to turn a density band piece.
static func toward_edge(tile: Vector2i, toward: Dictionary) -> int:
	return Hex.NEIGHBOURS.find(toward[tile] - tile)


## How many 60 degree steps (anticlockwise, the way edge numbers go) the landmark's centre piece turns, so its
## entrance on edge 0 faces the edge where the trail from the farthest tile arrives. 0 for the landmark alone.
static func turn(landmark: Vector2i, dist: Dictionary, toward: Dictionary) -> int:
	var far = null
	for t: Vector2i in dist:
		if dist[t] == 0:
			continue
		if far == null or dist[t] > dist[far] or (dist[t] == dist[far]
				and GroundCover.hash01(t.x, t.y, 10) > GroundCover.hash01(far.x, far.y, 10)):
			far = t
	if far == null:
		return 0
	var t: Vector2i = far
	while toward[t] != landmark:
		t = toward[t]
	return Hex.NEIGHBOURS.find(t - landmark)
