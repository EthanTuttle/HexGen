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
	for child in root.find_children("*", "MeshInstance3D", true, false):
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
		effects = read.call("effects", [])}


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
