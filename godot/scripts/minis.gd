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
	if name.begins_with("standin_"):
		return Kit.meshes("res://art/standin_minis.glb")[name]
	for glb in ["enemy_minis", "humanoid_minis", "giant_minis"]:
		if (name.begins_with("giant_")) != (glb == "giant_minis"):
			continue
		var kit := Kit.meshes("res://art/%s.glb" % glb)
		if kit.has(name):
			Kit.combat_materials(kit, true)   # PLACEHOLDER: the winding fix covers the map kits; some minis still lose faces when culled
			return kit[name]
	push_error("no mini %s" % name)
	return null


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
