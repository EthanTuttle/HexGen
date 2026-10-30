class_name Minis
extends RefCounted
## Stand-in minis from art/export/standin_minis.glb. Each is a Node3D at the base centre (ground level)
## with a "body" child holding the mesh, so tweens can hop and tilt the body without losing the spot.


static func make(name: String, at_plan: Vector2, facing_plan: Vector2) -> Node3D:
	var kit := Kit.meshes("res://art/standin_minis.glb")
	var root := Node3D.new()
	root.name = name
	root.position = Hex.to3(at_plan)
	var dir := Hex.to3(facing_plan)
	root.rotation.y = atan2(dir.x, dir.z)   # the minis face +Z (glTF front)
	var body := MeshInstance3D.new()
	body.name = "body"
	body.mesh = kit[name]
	root.add_child(body)
	return root


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
