class_name TilePaths
extends RefCounted
## One tile's drawn paths as a graph, from its placed pieces' path data (art/handoff/farmland_kit.md -> Path data;
## the glb's node extras): wedge paths, centre paths, the hub, and the spokes of edges whose wedge has a path. Ends
## that coincide are joined, and an end lying along another path splits it. Points are plan coordinates.

const JOIN := 0.03

var nodes := PackedVector2Array()
var links := {}          # node -> {node -> distance}
var edge_node := {}      # edge i -> the node at the edge's middle, where its wedge has a path
var edge_inner := {}     # edge i -> the wedge path's inner end
var stand = null         # the node a party stops on: the landmark's entrance, the hub, or the tile's middle


## pieces: [piece name, its turn in 60 degree steps] for each centre and wedge on the tile, at plan point `at`.
static func build(pieces: Array, at: Vector2) -> TilePaths:
	var g := TilePaths.new()
	var centres := []
	for p in pieces:
		var data := Kit.path_data(p[0])
		if data.is_empty():
			continue
		if "_edge_" in String(p[0]):
			for poly in data.paths:
				g._add(poly, p[1], at)
				if not poly.is_empty():
					g.edge_node[p[1]] = g._node(_plan(poly[-1], p[1], at))
					g.edge_inner[p[1]] = _plan(poly[0], p[1], at)
		else:
			centres.append(p)
	for p in centres:
		var data := Kit.path_data(p[0])
		for poly in data.paths:
			g._add(poly, p[1], at)
		for key in data.spokes:
			if g.edge_node.has(posmod(int(key) + p[1], 6)):   # spoke i lies on real edge i + the centre's turn
				g._add(data.spokes[key], p[1], at)
		if data.hub != null:
			var hub := g._node(_plan(data.hub, p[1], at))
			for i in g.edge_inner:
				g._link(hub, g._node(g.edge_inner[i]))
		var spot = stand_point(p[0], p[1], at)
		if spot != null:
			g.stand = g._node(spot)
	g._split()
	return g


## Where a party stops on a piece with path data: a landmark's entrance (its approach's inner end), else the
## hub, else the tile's middle where the spokes meet. null if the piece has none.
static func stand_point(piece: String, turn: int, at: Vector2):
	var data := Kit.path_data(piece)
	if data.is_empty() or "_edge_" in piece:
		return null
	if Variants.LANDMARKS.has(piece.trim_suffix("_centre")):
		for poly in data.paths:   # the approach: the first path that isn't a closed ring
			if poly[0] != poly[-1]:
				return _plan(poly[-1], turn, at)
	if data.hub != null:
		return _plan(data.hub, turn, at)
	for key in data.spokes:
		if _plan(data.spokes[key][-1], turn, Vector2.ZERO).length() < JOIN:
			return at
	return null


## Piece point (glTF Y-up, the piece's own frame) to plan coordinates, turned with the piece.
static func _plan(p: Array, turn: int, at: Vector2) -> Vector2:
	return at + Vector2(p[0], -p[2]).rotated(deg_to_rad(60.0 * turn))


func _node(p: Vector2) -> int:
	for k in nodes.size():
		if nodes[k].distance_to(p) < JOIN * 2.0:
			return k
	nodes.append(p)
	links[nodes.size() - 1] = {}
	return nodes.size() - 1


func _link(a: int, b: int) -> void:
	if a != b:
		var d := nodes[a].distance_to(nodes[b])
		links[a][b] = d
		links[b][a] = d


func _add(poly: Array, turn: int, at: Vector2) -> void:
	for k in range(1, poly.size()):
		_link(_node(_plan(poly[k - 1], turn, at)), _node(_plan(poly[k], turn, at)))


## Joins a node lying along another path's stretch into that stretch.
func _split() -> void:
	for n in nodes.size():
		for a in links.keys():
			for b in links[a].keys():
				if a < b and n != a and n != b:
					var on := Geometry2D.get_closest_point_to_segment(nodes[n], nodes[a], nodes[b])
					if on.distance_to(nodes[n]) < JOIN * 2.0:
						links[a].erase(b)
						links[b].erase(a)
						_link(a, n)
						_link(n, b)


func nearest(p: Vector2) -> int:
	var best := -1
	var d := INF
	for k in nodes.size():
		if nodes[k].distance_to(p) < d:
			d = nodes[k].distance_to(p)
			best = k
	return best


## The shortest way along the paths between two nodes, or empty if they don't connect.
func route(from: int, to: int) -> PackedVector2Array:
	var dist := {from: 0.0}
	var came := {}
	var todo := [from]
	while not todo.is_empty():
		todo.sort_custom(func(a, b): return dist[a] < dist[b])
		var c: int = todo.pop_front()
		if c == to:
			break
		for n: int in links[c]:
			var d: float = dist[c] + links[c][n]
			if d < dist.get(n, INF):
				dist[n] = d
				came[n] = c
				if not n in todo:
					todo.append(n)
	if not dist.has(to):
		return PackedVector2Array()
	var out := PackedVector2Array([nodes[to]])
	var c := to
	while c != from:
		c = came[c]
		out.insert(0, nodes[c])
	return out


## How far p is from the nearest path (for the check that routes keep to them).
func distance_to_paths(p: Vector2) -> float:
	var best := INF
	for a in links:
		for b in links[a]:
			best = minf(best, Geometry2D.get_closest_point_to_segment(p, nodes[a], nodes[b]).distance_to(p))
	return best
