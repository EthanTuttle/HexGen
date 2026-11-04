class_name Kit
extends RefCounted
## Meshes from an exported .glb kit (art/export, linked into godot/art), by node name.

static var _cache := {}
static var _paths := {}   # piece -> {paths, hub, spokes, effects}, from the glb's node extras


static func meshes(path: String) -> Dictionary:
	if _cache.has(path):
		return _cache[path]
	var root: Node = (load(path) as PackedScene).instantiate()
	var out := {}
	for child in root.find_children("*", "Node3D", true, false):   # a piece with no mesh can still have effect points (the oasis's open sand)
		if child is MeshInstance3D:
			out[String(child.name)] = (child as MeshInstance3D).mesh
		if child.has_meta("extras"):
			_paths[String(child.name)] = _path_extras(child.get_meta("extras"))
	root.free()
	_cache[path] = out
	return out


## A piece's path data and effect points (art/handoff/farmland_kit.md), or {} if it has none. Load the kit first.
static func path_data(piece: String) -> Dictionary:
	return _paths.get(piece, {})


static func _path_extras(extras: Dictionary) -> Dictionary:
	var read := func(key: String, empty):
		return JSON.parse_string(extras[key]) if extras.has(key) else empty
	return {paths = read.call("paths", []), hub = read.call("path_hub", null), spokes = read.call("path_spokes", {}),
		effects = read.call("effects", []), no_cover = read.call("no_cover", []), footprint = read.call("footprint", [])}


## Combat kits' materials: colours in the vertex colours, and drawn from both sides. PLACEHOLDER until the art turns its door and window
## plates round: some face into their walls (godot/README.md -> Combat kit).
static func combat_materials(kit: Dictionary) -> void:
	for mesh: Mesh in kit.values():
		for k in mesh.get_surface_count():
			var m := mesh.surface_get_material(k) as BaseMaterial3D
			if m:
				m.vertex_color_use_as_albedo = true
				m.cull_mode = BaseMaterial3D.CULL_DISABLED if m.resource_name == "web" else BaseMaterial3D.CULL_BACK   # webs show from both sides (combat_forest_kit.md -> Facing)


static func place(parent: Node3D, kit: Dictionary, name: String, at: Vector2, angle := 0.0) -> MeshInstance3D:
	if not kit.has(name):
		return null   # some edge pieces are empty (e.g. plains wedges) and export no mesh
	var mi := MeshInstance3D.new()
	mi.name = name
	mi.set_meta("piece", name)   # the node's own name gets a suffix when a tile holds the same piece twice
	mi.mesh = kit[name]
	mi.position = Hex.to3(at)
	mi.rotation.y = angle
	parent.add_child(mi)
	return mi


static func material_name(mesh: Mesh, surface: int) -> String:
	var m := mesh.surface_get_material(surface)
	return m.resource_name if m else ""
