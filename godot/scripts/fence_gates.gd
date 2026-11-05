class_name FenceGates
extends RefCounted
## Port of art/scripts/fence_gates.py: which edges of a fenced farm and village group get a gate
## (design/06 -> Tile build), so the party always has a way in and out (design/07 -> Walking).

const FENCED := ["farmland", "village"]   # terrains inside the fence (their variants count as them)
const UNWALKABLE := ["river"]             # water: rivers and lakes


## terrains: tile -> terrain (variants and landmarks already turned into their terrain). raised: all raised tiles.
## climbs: every raised region's Cliffs.climbs(). Returns tile -> the edges of that fenced tile that show a gate.
static func gates(terrains: Dictionary, raised := {}, climbs := []) -> Dictionary:
	var out := {}
	var fence := {}
	for t: Vector2i in terrains:
		if not terrains[t] in FENCED:
			continue
		var edges := []
		for i in 6:
			if not terrains.get(t + Hex.NEIGHBOURS[i]) in FENCED:
				edges.append(i)
		fence[t] = edges
		var ranked := edges.duplicate()
		ranked.sort_custom(func(a, b): return _rank(t, a) < _rank(t, b))
		var take := ranked.slice(0, 2 if GroundCover.hash01(t.x, t.y, 12) < 0.35 else 1)
		out[t] = take.filter(func(i): return _walkable(terrains, raised, t + Hex.NEIGHBOURS[i]))
		if t == Rules.START_TILE:
			out[t] = edges   # a starting tile is open on every side (design/06 -> First playable)
	# Every group gets a way out.
	var seen := {}
	for start: Vector2i in fence:
		if seen.has(start):
			continue
		var group: Array[Vector2i] = [start]
		seen[start] = true
		var k := 0
		while k < group.size():
			for n in Hex.NEIGHBOURS:
				var c: Vector2i = group[k] + n
				if fence.has(c) and not seen.has(c):
					seen[c] = true
					group.append(c)
			k += 1
		if group.any(func(t): return out[t].any(func(i): return _walkable(terrains, raised, t + Hex.NEIGHBOURS[i]))):
			continue
		var best := INF
		var best_tile := Vector2i.ZERO
		var best_edge := -1
		for t in group:
			for i: int in fence[t]:
				if _walkable(terrains, raised, t + Hex.NEIGHBOURS[i]) and _rank(t, i) < best:
					best = _rank(t, i)
					best_tile = t
					best_edge = i
		if best_edge >= 0:
			out[best_tile] = [best_edge]
	# A fenced tile in front of a ledge's foot always gets a gate on the edge facing it.
	for c in climbs:
		var front: Vector2i = Cliffs.beside(c[0], c[1] - 1)
		var facing: int = (c[1] + 2) % 6
		if fence.has(front) and not facing in out[front]:
			out[front].append(facing)
	return out


static func _rank(t: Vector2i, i: int) -> float:
	return GroundCover.hash01(t.x * 6 + i, t.y, 11)


static func _walkable(terrains: Dictionary, raised: Dictionary, n: Vector2i) -> bool:
	return not raised.has(n) and terrains.get(n) != null and not terrains[n] in UNWALKABLE
