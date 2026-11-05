class_name EncounterView
extends Node3D
## One map encounter's figures, true scale on its tile (design/07 -> Encounters; art/handoff/encounters_kit.md), shown only within sight. Its badge is a HUD marker (ExploreHud).

const STEP_SECONDS := 0.7     # a roamer's move

var figures: MeshInstance3D
var shown := false


static func make(scene: String, seed_: int) -> EncounterView:
	var kit := Kit.meshes("res://art/encounters.glb")
	Kit.combat_materials(kit)
	var v := EncounterView.new()
	v.name = "encounter_%d" % seed_
	v.figures = MeshInstance3D.new()
	v.figures.mesh = kit[scene]
	v.figures.rotation.y = GroundCover.hash01(seed_, 3, 98) * TAU
	v.add_child(v.figures)
	v.visible = false
	return v


## Moves it to a world point: walks there if it shows.
func place(to: Vector3, walk: bool) -> void:
	if not walk:
		position = to
		return
	var tw := create_tween()
	tw.tween_property(self, "position", to, STEP_SECONDS).set_trans(Tween.TRANS_SINE)


func height() -> float:
	return figures.mesh.get_aabb().end.y
