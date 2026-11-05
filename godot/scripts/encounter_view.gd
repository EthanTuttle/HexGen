class_name EncounterView
extends Node3D
## One map encounter as the map shows it (design/07 -> Encounters; art/handoff/encounters_kit.md): true-scale figures on its tile and a badge for its kind, both shown only within
## sight. The badge is unlit, draws over trees, faces the camera and keeps about 32 pt at map zoom, shrinking gently as the camera comes in. PLACEHOLDER numbers; the badges are being iterated.

const POINTS := 32.0
const AT_DISTANCE := 58.0     # the map's opening zoom
const SHRINK := 0.35
const SMALLEST := 0.6
const STEP_SECONDS := 0.7     # a roamer's move

static var _badge_material: StandardMaterial3D

var figures: MeshInstance3D
var badge: MeshInstance3D
var shown := false


static func make(scene: String, kind: String, seed_: int) -> EncounterView:
	var kit := Kit.meshes("res://art/encounters.glb")
	Kit.combat_materials(kit)
	var v := EncounterView.new()
	v.name = "encounter_%d" % seed_
	v.figures = MeshInstance3D.new()
	v.figures.mesh = kit[scene]
	v.figures.rotation.y = GroundCover.hash01(seed_, 3, 98) * TAU
	v.add_child(v.figures)
	if _badge_material == null:
		_badge_material = StandardMaterial3D.new()
		_badge_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_badge_material.vertex_color_use_as_albedo = true
		_badge_material.no_depth_test = true
		_badge_material.cull_mode = BaseMaterial3D.CULL_DISABLED
		_badge_material.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
		_badge_material.billboard_keep_scale = true
		_badge_material.render_priority = 2
	v.badge = MeshInstance3D.new()
	v.badge.mesh = kit["enc_badge_" + kind]
	v.badge.material_override = _badge_material
	v.badge.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	v.add_child(v.badge)
	v.visible = false
	return v


## Puts it on tile t, off the middle where a party stands: walks there if it shows.
func place(game: Game, t: Vector2i, walk: bool) -> void:
	var ang := GroundCover.hash01(t.x, t.y, 99) * TAU
	var to := Hex.to3(Hex.tile_position(t.x, t.y) + Vector2(cos(ang), sin(ang)) * 1.5, game.map.lift.get(t, 0.0))
	if not walk:
		position = to
		return
	var tw := create_tween()
	tw.tween_property(self, "position", to, STEP_SECONDS).set_trans(Tween.TRANS_SINE)


func show_for(in_sight: bool, rig: CameraRig) -> void:
	shown = in_sight
	visible = in_sight
	if not in_sight:
		return
	var k := 2.0 * tan(deg_to_rad(rig.camera.fov) * 0.5) / 844.0   # metres per layout point, per metre of distance
	var points := POINTS * clampf(pow(rig.distance / AT_DISTANCE, SHRINK), SMALLEST, 1.0)
	badge.scale = Vector3.ONE * points * k * rig.distance
	badge.position.y = figures.mesh.get_aabb().end.y + 0.25
