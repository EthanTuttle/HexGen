class_name Crossing
extends RefCounted
## A test aid: a rapids tile a party can cross, for the checks.


## [tile, the land tile on one bank, the land tile on the other, the first's edge], or []. Lays plains where a bank has no tile yet.
static func find(map: MapBoard, tiles: Array) -> Array:
	for t: Vector2i in tiles:
		var w: Dictionary = map.water_shapes[t]
		if not w.has("gorge") or w.has("bridge") or map.terrains[t] != "rapids":
			continue
		for a: int in w.gorge.walks:
			for b: int in w.gorge.walks:
				if a != b and map.wet_between(t, a, b):
					var near: Vector2i = t + Hex.NEIGHBOURS[a]
					var far: Vector2i = t + Hex.NEIGHBOURS[b]
					if Variants.is_water(map.terrains.get(near)) or Variants.is_water(map.terrains.get(far)):
						continue
					for n: Vector2i in [near, far]:
						if not map.terrains.has(n):
							map.place(n, "plains")
					if map.edge_open(near, t) and map.edge_open(far, t):
						return [t, near, far, a]
	return []
