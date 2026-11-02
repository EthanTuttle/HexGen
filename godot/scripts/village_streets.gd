class_name VillageStreets
extends RefCounted
## Port of art/scripts/village_streets.py: which edges of a village tile have a street (design/06 -> Tile build), so
## tiles joined at any angle connect, and there's no spoke to nowhere.

const VILLAGE := "village"
const FARM := "farmland"
const BLOCK := 3   # tiles along each side of a block that shares an axis


## Which pair of opposite edges (0: edges 0 and 3, 1: 1 and 4, 2: 2 and 5) the tile's main street runs between.
static func axis(t: Vector2i) -> int:
	return int(GroundCover.hash01(floori(t.x / float(BLOCK)), floori(t.y / float(BLOCK)), 15) * 3)


## terrains: tile -> terrain (variants and landmarks already turned into their terrain). trails: trail edges, as
## {[tile, edge]: true}. Returns tile -> {edge: "main" or "side"} for every village tile, both sides agreeing.
static func streets(terrains: Dictionary, trails := {}) -> Dictionary:
	var out := {}
	var parent := {}
	for t: Vector2i in terrains:
		if terrains[t] == VILLAGE:
			out[t] = {}
		if terrains[t] == VILLAGE or terrains[t] == FARM:
			parent[t] = t
	var find := func(t: Vector2i) -> Vector2i:
		while parent[t] != t:
			parent[t] = parent[parent[t]]
			t = parent[t]
		return t
	for t: Vector2i in parent:
		for i in 6:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if not parent.has(n):
				continue
			if terrains[t] == FARM and terrains[n] == FARM:   # a farm has a track to every joined neighbour
				parent[find.call(t)] = find.call(n)
			elif terrains[t] == VILLAGE and terrains[n] == FARM:
				out[t][i] = "side"
				parent[find.call(t)] = find.call(n)
			elif terrains[t] == VILLAGE and terrains[n] == VILLAGE:
				var back := (i + 3) % 6
				if axis(t) == i % 3 or axis(n) == i % 3 or trails.has([t, i]) or trails.has([n, back]):
					out[t][i] = "main"
					out[n][back] = "main"
					parent[find.call(t)] = find.call(n)
	var spare := []
	for t: Vector2i in out:
		for i in 6:
			var n: Vector2i = t + Hex.NEIGHBOURS[i]
			if not out[t].has(i) and out.has(n):
				var low: Vector2i = t if [t.x, t.y] < [n.x, n.y] else n
				spare.append([GroundCover.hash01(low.x * 6 + mini(i, (i + 3) % 6), low.y, 16), t.x, t.y, i])
	spare.sort()
	for e in spare:
		var t := Vector2i(e[1], e[2])
		var i: int = e[3]
		var n: Vector2i = t + Hex.NEIGHBOURS[i]
		if find.call(t) != find.call(n):
			out[t][i] = "side"
			out[n][(i + 3) % 6] = "side"
			parent[find.call(t)] = find.call(n)
	return out
