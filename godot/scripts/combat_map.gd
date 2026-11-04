class_name CombatMap
extends RefCounted
## The approved combat maps (art/handoff/combat_*_kit.md; design/07 -> Combat maps): which map a fight takes, and drawing one.
## Coordinates are the art's: a piece at x, y stands at Hex.to3(Vector2(x, y), z), turned `turn` degrees about +Y.
## Each piece is one MultiMesh, so a map of hundreds of placements costs a few dozen draws.

const SETS := {"combat_maps": "combat_cells", "combat_maps_farmland": "combat_farmland", "combat_maps_plains": "combat_plains",
	"combat_maps_village": "combat_village", "combat_maps_hills": "combat_hills"}

static var _maps := {}
static var _flow: ShaderMaterial
static var _pulse: ShaderMaterial


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
	_lava_materials(cells)
	_lava_materials(pieces)
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


## The kit's `lava` and `lava_flow` surfaces get the moving material; banks and rims stay as they are.
static func _lava_materials(kit: Dictionary) -> void:
	if _flow == null:
		var look := FastNoiseLite.new()
		look.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
		look.frequency = 0.03
		look.fractal_type = FastNoiseLite.FRACTAL_NONE
		var img := look.get_seamless_image(128, 128)
		img.convert(Image.FORMAT_L8)
		img.generate_mipmaps()
		_flow = ShaderMaterial.new()
		_flow.shader = load("res://shaders/combat_lava.gdshader")
		_flow.resource_name = "lava_flow"
		_flow.set_shader_parameter("noise", ImageTexture.create_from_image(img))
		_pulse = _flow.duplicate() as ShaderMaterial
		_pulse.resource_name = "lava"
		_pulse.set_shader_parameter("flow", false)
	for mesh: Mesh in kit.values():
		for k in mesh.get_surface_count():
			match Kit.material_name(mesh, k):
				"lava_flow": mesh.surface_set_material(k, _flow)
				"lava": mesh.surface_set_material(k, _pulse)


## The long steps of a map's lifts, stairs and path, where each cell's edge has them, read from the art: cell -> [mask of neighbours, height].
## A cell's highlight climbs them, as the data doesn't say which cells are lifts.
static func treads_of(id: String, grid: Dictionary) -> Dictionary:
	var on_cell := {}
	var pieces := Kit.meshes("res://art/%s.glb" % all()[id].set)
	for name: String in ["map_%s_lift_steps" % id, "map_%s_path_steps" % id]:
		var mesh: Mesh = pieces.get(name.validate_node_name())
		if mesh == null:
			continue
		for k in mesh.get_surface_count():
			for v: Vector3 in mesh.surface_get_arrays(k)[Mesh.ARRAY_VERTEX]:
				var p := Vector2(v.x, -v.z)
				var c := Fight.cell_at(p)
				if grid.has(c) and v.y - grid[c].z >= 0.05:
					if not on_cell.has(c):
						on_cell[c] = []
					on_cell[c].append(Vector3(p.x - Hex.cell_position(c.x, c.y).x, p.y - Hex.cell_position(c.x, c.y).y, v.y - grid[c].z))
	var out := {}
	for c: Vector2i in on_cell:
		var mask := 0
		var high := 0.0
		for i in 6:   # a long step runs most of its edge; another's end only reaches the corner
			var side := Hex.cell_position(Hex.NEIGHBOURS[i].x, Hex.NEIGHBOURS[i].y).normalized()
			var low := INF
			var far := -INF
			for v: Vector3 in on_cell[c]:
				var q := Vector2(v.x, v.y)
				if q.dot(side) >= 0.2:
					low = minf(low, q.dot(side.orthogonal()))
					far = maxf(far, q.dot(side.orthogonal()))
					high = maxf(high, v.z)
			if far - low > 0.35:
				mask |= 1 << i
		out[c] = [mask, high]
	return out


## A piece's mesh: Godot turns a "." in a node's name into "_" on import.
static func piece_mesh(name: String, cells: Dictionary, pieces: Dictionary) -> Mesh:
	return (pieces if name.begins_with("map_") else cells).get(name.validate_node_name())


## A cell's offset turned k steps of 60 degrees anticlockwise from above (render_forest_maps.turned).
static func turned(c: Vector2i, k: int) -> Vector2i:
	var p := Hex.cell_position(c.x, c.y).rotated(deg_to_rad(60.0 * k))
	var q := roundi(p.x / (1.5 * Hex.CELL_RADIUS))
	return Vector2i(q, roundi(-p.y / Hex.CELL_FLATS - q / 2.0))
