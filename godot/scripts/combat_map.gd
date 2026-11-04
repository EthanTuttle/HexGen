class_name CombatMap
extends RefCounted
## The approved combat maps (art/handoff/combat_*_kit.md; design/07 -> Combat maps): which map a fight takes, and drawing one.
## Coordinates are the art's: a piece at x, y stands at Hex.to3(Vector2(x, y), z), turned `turn` degrees about +Y.
## Each piece is one MultiMesh, so a map of hundreds of placements costs a few dozen draws.

const SETS := {"combat_maps": "combat_cells", "combat_maps_farmland": "combat_farmland", "combat_maps_plains": "combat_plains",
	"combat_maps_village": "combat_village", "combat_maps_hills": "combat_hills"}

static var _maps := {}
const BOW := 0.6                         # PLACEHOLDER: how far a band's middle leads its edges, per metre from the middle
static var _flowed := {}
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
	flow_mesh(id)
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
		_flow = ShaderMaterial.new()
		_flow.shader = load("res://shaders/combat_lava.gdshader")
		_flow.resource_name = "lava_flow"
		_pulse = _flow.duplicate() as ShaderMaterial
		_pulse.resource_name = "lava"
		_pulse.set_shader_parameter("flow", false)
	for mesh: Mesh in kit.values():
		for k in mesh.get_surface_count():
			match Kit.material_name(mesh, k):
				"lava_flow": mesh.surface_set_material(k, _flow)
				"lava": mesh.surface_set_material(k, _pulse)


## A map's lava_flow with what its bands run on. The art's V comes from the nearest point on a zigzag centre line, so it jumps at the necks between cells
## (combat_hills_kit.md -> Pattern jumps), each cell is three pieces, and a pool has too few vertices to carry bands. So a triangle on a cell gets that cell's way in
## and way out, with their metres along, in CUSTOM0 and CUSTOM1, and the shader works out each pixel from them: straight chevrons across the line from in to out, which
## meet the next cell's at the neck and turn there. The channel and the fall keep V in UV.y, bowed the same way, with the bow gone where they meet the cells.
static func flow_mesh(id: String) -> Mesh:
	var pieces := Kit.meshes("res://art/%s.glb" % all()[id].set)
	var key := "map_%s_lava_flow" % id
	if not pieces.has(key) or _flowed.has(key):
		return pieces.get(key)
	_flowed[key] = true
	var old: Mesh = pieces[key]
	var heights := {}
	var next := {}
	for c: Dictionary in all()[id].cells:
		if c.kind == "lava":
			var at := Vector2i(int(c.q), int(c.r))
			heights[at] = c.get("z", 0.0)
			if c.has("flow_to"):
				next[at] = Vector2i(int(c.flow_to[0]), int(c.flow_to[1]))
	var first: Vector2i = heights.keys().filter(func(c): return not next.values().has(c))[0]
	var chain: Array[Vector2i] = [first]
	while next.has(chain[-1]):
		chain.append(next[chain[-1]])
	var mesh := ArrayMesh.new()
	for k in old.get_surface_count():
		var arrays := old.surface_get_arrays(k)
		var flags := 0
		if old.surface_get_material(k).resource_name == "lava_flow":
			arrays = _flow_arrays(arrays, chain, heights)
			flags = (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) | (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT)
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, flags)
		mesh.surface_set_material(k, old.surface_get_material(k))
	pieces[key] = mesh
	return mesh


## The flow's surface with its own corners per triangle. CUSTOM0: way in x, y, way out x, y. CUSTOM1: their metres along, 1 for a cell or -1 to use UV.y, and the bow.
static func _flow_arrays(arrays: Array, chain: Array[Vector2i], heights: Dictionary) -> Array:
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var uv: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
	var tris: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var index := {}
	for i in chain.size():
		index[chain[i]] = i
	var on_cell := func(p: Vector3) -> int:
		var c := Fight.cell_at(Vector2(p.x, -p.z))
		return index[c] if index.has(c) and absf(p.y - heights[c]) < 0.2 else -1
	# The way points: the middle of each neck with its metres along in the art, then where the channel comes in and the fall leaves.
	var ways := []
	var metres := []
	ways.resize(chain.size() + 1)
	metres.resize(chain.size() + 1)
	for n in range(1, chain.size()):
		var a := Hex.cell_position(chain[n - 1].x, chain[n - 1].y)
		var b := Hex.cell_position(chain[n].x, chain[n].y)
		var total := Vector2.ZERO
		var sum := 0.0
		var count := 0
		for i in verts.size():
			var p := Vector2(verts[i].x, -verts[i].z)
			if on_cell.call(verts[i]) >= 0 and p.distance_to((a + b) * 0.5) < 0.3:
				total += p
				sum += _along(verts, uv, i)
				count += 1
		ways[n] = total / count if count > 0 else (a + b) * 0.5
		metres[n] = sum / maxi(count, 1)
	var cone := -INF
	var fall := INF
	for i in verts.size():
		if on_cell.call(verts[i]) < 0:
			var along := _along(verts, uv, i)
			if along < metres[1] - 0.5:
				cone = maxf(cone, along)
			elif along > metres[chain.size() - 1] + 0.5:
				fall = minf(fall, along)
	metres[0] = cone
	metres[chain.size()] = fall
	# Each end's way point is the middle of the flow there.
	for end: Array in [[0, cone], [chain.size(), fall]]:
		var total := Vector2.ZERO
		var count := 0
		for i in verts.size():
			if on_cell.call(verts[i]) < 0 and absf(_along(verts, uv, i) - end[1]) < 0.06:
				total += Vector2(verts[i].x, -verts[i].z)
				count += 1
		ways[end[0]] = total / maxi(count, 1)
	var out_verts := PackedVector3Array()
	var out_normals := PackedVector3Array()
	var out_uv := PackedVector2Array()
	var way := PackedFloat32Array()
	var meta := PackedFloat32Array()
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	for t in range(0, tris.size(), 3):
		var middle := (verts[tris[t]] + verts[tris[t + 1]] + verts[tris[t + 2]]) / 3.0
		var n: int = on_cell.call(middle)
		if n == 0 or n == chain.size() - 1:   # the channel's foot and the fall's lip stand over a cell, off its level
			for s in 3:
				var off: float = verts[tris[t + s]].y - heights[chain[n]]
				n = -1 if off > 0.06 or off < -0.04 else n
		for s in 3:
			var i := tris[t + s]
			var along := _along(verts, uv, i)
			var to_cells := minf(cone - along if along <= cone else INF, along - fall if along >= fall else INF)
			out_verts.append(verts[i])
			out_normals.append(normals[i])
			out_uv.append(Vector2(uv[i].x, along - absf(uv[i].x) * BOW * minf(to_cells / 0.6, 1.0)))
			if n >= 0:
				way.append_array(PackedFloat32Array([ways[n].x, ways[n].y, ways[n + 1].x, ways[n + 1].y]))
				meta.append_array(PackedFloat32Array([metres[n], metres[n + 1], 1, BOW]))
			else:
				way.append_array(PackedFloat32Array([0, 0, 0, 0]))
				meta.append_array(PackedFloat32Array([0, 0, -1, 0]))
	var out := []
	out.resize(Mesh.ARRAY_MAX)
	out[Mesh.ARRAY_VERTEX] = out_verts
	out[Mesh.ARRAY_NORMAL] = out_normals
	out[Mesh.ARRAY_TEX_UV] = out_uv
	out[Mesh.ARRAY_CUSTOM0] = way
	out[Mesh.ARRAY_CUSTOM1] = meta
	return out


## What the shader's bands run on at corner i of the flow's surface.
static func flow_field(arrays: Array, i: int) -> float:
	var way: PackedFloat32Array = arrays[Mesh.ARRAY_CUSTOM0]
	var meta: PackedFloat32Array = arrays[Mesh.ARRAY_CUSTOM1]
	if meta[i * 4 + 2] < 0.0:
		return arrays[Mesh.ARRAY_TEX_UV][i].y
	var p: Vector3 = arrays[Mesh.ARRAY_VERTEX][i]
	var from := Vector2(way[i * 4], way[i * 4 + 1])
	var axis := Vector2(way[i * 4 + 2], way[i * 4 + 3]) - from
	var off := Vector2(p.x, -p.z) - from
	return lerpf(meta[i * 4], meta[i * 4 + 1], clampf(off.dot(axis) / axis.length_squared(), 0.0, 1.0)) - meta[i * 4 + 3] * absf(off.cross(axis)) / axis.length()


## The art's metres along at vertex i. The channel's side faces carry 0 down their length: those take the value of the surface they share a corner with.
static func _along(verts: PackedVector3Array, uv: PackedVector2Array, i: int) -> float:
	var along := 1.0 - uv[i].y
	if along > 0.01:
		return along
	for j in verts.size():
		if 1.0 - uv[j].y > 0.01 and verts[j].distance_squared_to(verts[i]) < 0.03 * 0.03:
			return 1.0 - uv[j].y
	return along


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
