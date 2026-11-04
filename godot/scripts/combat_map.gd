class_name CombatMap
extends RefCounted
## The approved combat maps (art/handoff/combat_*_kit.md; design/07 -> Combat maps): which map a fight takes, and drawing one.
## Coordinates are the art's: a piece at x, y stands at Hex.to3(Vector2(x, y), z), turned `turn` degrees about +Y.
## Each piece is one MultiMesh, so a map of hundreds of placements costs a few dozen draws.

const SETS := {"combat_maps": "combat_cells", "combat_maps_farmland": "combat_farmland", "combat_maps_plains": "combat_plains",
	"combat_maps_village": "combat_village"}

static var _maps := {}


## Every map's data by id, with `set` added: the glb of its map_ pieces.
static func all() -> Dictionary:
	if _maps.is_empty():
		for s: String in SETS:
			var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://art/%s.json" % s))
			for id: String in data:
				data[id].set = s
				_maps[id] = data[id]
	return _maps


## The maps a fight on this tile can take. PLACEHOLDER: a landmark's tile uses its variant's maps until landmark fights exist.
static func choices(tile_name: String, has_paths: bool) -> Array:
	var variant := Variants.wedges_of(tile_name)
	var out := []
	for id: String in all():
		if _maps[id].variant == variant and (has_paths or _maps[id].get("kind", "") != "path"):
			out.append(id)
	out.sort()
	return out


## The map's grid: cell -> {kind, z, way_up}.
static func grid_of(id: String) -> Dictionary:
	var out := {}
	for c: Dictionary in all()[id].cells:
		out[Vector2i(int(c.q), int(c.r))] = {kind = c.kind, z = c.get("z", 0.0), way_up = c.get("way_up", false)}
	return out


## Draws the map under parent. Returns how many triangles it has.
static func build(id: String, parent: Node3D) -> int:
	var data: Dictionary = all()[id]
	var cells := Kit.meshes("res://art/%s.glb" % SETS[data.set])
	var pieces := Kit.meshes("res://art/%s.glb" % data.set)
	Kit.combat_materials(cells)
	Kit.combat_materials(pieces)
	var by_piece := {}
	for p: Dictionary in data.placements:
		if not by_piece.has(p.piece):
			by_piece[p.piece] = []
		by_piece[p.piece].append(Transform3D(Basis(Vector3.UP, deg_to_rad(p.turn)), Hex.to3(Vector2(p.x, p.y), p.get("z", 0.0))))
	var tris := 0
	for name: String in by_piece:
		var mesh: Mesh = piece_mesh(name, cells, pieces)
		if mesh == null:
			continue   # some map_ pieces export empty (a map with no gates of its kind)
		var list: Array = by_piece[name]
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = mesh
		mm.instance_count = list.size()
		for k in list.size():
			mm.set_instance_transform(k, list[k])
		var node := MultiMeshInstance3D.new()
		node.name = name
		node.multimesh = mm
		parent.add_child(node)
		for s in mesh.get_surface_count():
			tris += list.size() * mesh.surface_get_array_index_len(s) / 3
	return tris


## A piece's mesh: Godot turns a "." in a node's name into "_" on import.
static func piece_mesh(name: String, cells: Dictionary, pieces: Dictionary) -> Mesh:
	return (pieces if name.begins_with("map_") else cells).get(name.validate_node_name())


## A cell's offset turned k steps of 60 degrees anticlockwise from above (render_forest_maps.turned).
static func turned(c: Vector2i, k: int) -> Vector2i:
	var p := Hex.cell_position(c.x, c.y).rotated(deg_to_rad(60.0 * k))
	var q := roundi(p.x / (1.5 * Hex.CELL_RADIUS))
	return Vector2i(q, roundi(-p.y / Hex.CELL_FLATS - q / 2.0))
