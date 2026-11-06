class_name Minis
extends RefCounted
## Minis from art/export: the stand-ins, enemies and giants. Each is a Node3D at the base centre (ground level)
## with a "body" child holding the mesh, so tweens can hop and tilt the body without losing the spot.


static func make(name: String, at_plan: Vector2, facing_plan: Vector2) -> Node3D:
	var root := Node3D.new()
	root.name = name
	root.position = Hex.to3(at_plan)
	var dir := Hex.to3(facing_plan)
	root.rotation.y = atan2(dir.x, dir.z)   # the minis face +Z (glTF front)
	var body := MeshInstance3D.new()
	body.name = "body"
	body.mesh = _mesh(name)
	root.add_child(body)
	return root


static func _mesh(name: String) -> Mesh:
	if name == "standin_hero" and Hero.current != null:   # the hero made in the creator
		return HeroMini.mesh_for(Hero.current)
	if name.begins_with("summon_"):
		return _summon_mesh(name)
	if name.begins_with("standin_"):
		var standins := Kit.meshes("res://art/standin_minis.glb")
		Kit.combat_materials(standins)   # their colours are in the vertices too, since the art's facing fix
		return standins[name]
	for glb in ["enemy_minis", "humanoid_minis", "giant_minis"]:
		if (name.begins_with("giant_")) != (glb == "giant_minis"):
			continue
		var kit := Kit.meshes("res://art/%s.glb" % glb)
		if kit.has(name):
			Kit.combat_materials(kit)
			return kit[name]
	push_error("no mini %s" % name)
	return null


## The Wizard's summons (03 -> Summoner), built here until there's art: PLACEHOLDER looks. The Animated Blade floats point
## down; the Wisp is a glowing orb with a small one trailing.
static var _summons := {}


static func _summon_mesh(name: String) -> Mesh:
	if _summons.has(name):
		return _summons[name]
	var am := ArrayMesh.new()
	if name == "summon_blade":
		_part(am, _box(Vector3(0.09, 0.78, 0.025)), Vector3(0, 0.78, 0), Color("#D3D8DF"))   # the blade
		_part(am, _box(Vector3(0.34, 0.05, 0.07)), Vector3(0, 1.19, 0), Color("#C8A24A"))    # crossguard
		_part(am, _box(Vector3(0.05, 0.2, 0.05)), Vector3(0, 1.31, 0), Color("#5A3A26"))     # grip
		_part(am, _ball(0.045), Vector3(0, 1.43, 0), Color("#C8A24A"))                         # pommel
	else:
		_part(am, _ball(0.2), Vector3(0, 0.95, 0), Color("#BFE6FF"), true)
		_part(am, _ball(0.08), Vector3(0.12, 0.66, -0.16), Color("#BFE6FF"), true)
	_summons[name] = am
	return am


static func _box(s: Vector3) -> PrimitiveMesh:
	var b := BoxMesh.new()
	b.size = s
	return b


static func _ball(r: float) -> PrimitiveMesh:
	var b := SphereMesh.new()
	b.radius = r
	b.height = r * 2.0
	b.radial_segments = 12
	b.rings = 6
	return b


static func _part(am: ArrayMesh, shape: PrimitiveMesh, at: Vector3, col: Color, glow := false) -> void:
	var arrays := shape.get_mesh_arrays()
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	for i in verts.size():
		verts[i] += at
	arrays[Mesh.ARRAY_VERTEX] = verts
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	if glow:
		mat.emission_enabled = true
		mat.emission = col
		mat.emission_energy_multiplier = 1.2
	am.surface_set_material(am.get_surface_count() - 1, mat)


## The cells a giant stands on, as offsets from its anchor at turn 0 (art/handoff/combat_forest_kit.md); one cell for anyone else.
static func footprint(name: String) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	if name.begins_with("giant_"):
		_mesh(name)
		for c: Array in Kit.path_data(name).footprint:
			out.append(Vector2i(int(c[0]), int(c[1])))
	if out.is_empty():
		out.append(Vector2i.ZERO)
	return out


## The party on a map tile as a loose cluster at true scale, hero in front: the same spots as
## art/scripts/render_standin_minis.py (map_tile). Built facing south (toward the default camera);
## turn the group node to face the way it walks.
const PARTY := [["standin_hero", Vector2i(0, 1)], ["standin_chelmsford", Vector2i(-1, 1)],
	["standin_small", Vector2i(1, 0)], ["standin_fluffy", Vector2i(0, 0)]]
## Where the cluster stands on its tile (render_standin_minis.py moves it off the centre piece).
const PARTY_OFFSET := Vector2(0.6, -0.4)


static func party(centre: Vector2) -> Node3D:
	var group := Node3D.new()
	group.name = "party"
	group.position = Hex.to3(centre + PARTY_OFFSET)
	for m in PARTY:
		var c: Vector2i = m[1]
		group.add_child(make(m[0], Hex.cell_position(c.x, c.y), Vector2(0, -1)))
	return group
