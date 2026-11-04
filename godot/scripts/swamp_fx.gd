class_name SwampFx
extends RefCounted
## The swamp kit's engine effects (art/handoff/swamp_kit.md): wisps, glows and bubbles at the kit's effect points, mist and haze at
## the wetland's, smoke at a landmark's. All PLACEHOLDER looks until seen, kept light for the phone: one mesh per tile for what
## floats and one for what lies flat, with no lights and no shadows; smoke is one particle node per landmark.

const WISP_SIZE := 0.26     # PLACEHOLDER sizes and colours
const GLOW_SIZE := 0.7
const BUBBLE_SIZE := 0.1
const MIST_SIZE := 4.2
const COLOURS := {"wisp": Color("#D8FFF2"), "glow_pale": Color("#CFF7E8"), "glow_green": Color("#A8F56A"), "glow_ooze": Color("#D8EE5A"), "bubbles": Color("#D8E48A")}

static var _spark: ShaderMaterial
static var _rising: ShaderMaterial
static var _mist: ShaderMaterial
static var _haze: ShaderMaterial
static var _smoke_green: StandardMaterial3D
static var night := 0.0


## The effects node for tile t's marsh, or null. pieces: [piece, x, y, spin] of what stands on it, its landmark's centre too.
static func for_tile(tile: Dictionary, at: Vector2, pieces: Array) -> Node3D:
	var floats := []
	var rises := []
	var smokes := []
	var greens := []
	for item: Array in pieces:
		for e in Kit.path_data(item[0]).get("effects", []):
			var q := Vector2(e.at[0], -e.at[2]).rotated(item[3]) + Vector2(item[1], item[2])
			var p := Vector3(q.x, e.at[1], -q.y)
			match e.kind:
				"wisp":
					floats.append([p, WISP_SIZE, COLOURS.wisp])
				"glow_pale", "glow_green", "glow_ooze":
					floats.append([p, GLOW_SIZE, COLOURS[e.kind]])
				"bubbles":
					for k in 3:
						rises.append([p + Vector3(0.1 * (k - 1), 0, 0.07 * (k % 2)), BUBBLE_SIZE, COLOURS.bubbles])
				"smoke":
					smokes.append(p)
				"smoke_green":
					greens.append(p)
				"mist":
					tile.effects.append(["mist", p.x, -p.z, p.y])
				"haze":
					tile.effects.append(["haze", p.x, -p.z, p.y])
	var holder := Node3D.new()
	holder.name = "swamp_fx"
	holder.position = Hex.to3(at)
	if not floats.is_empty():
		holder.add_child(_cards(floats, _spark_material(false), "wisps"))
	if not rises.is_empty():
		holder.add_child(_cards(rises, _spark_material(true), "bubbles"))
	var mist := []
	var haze := []
	for e: Array in tile.effects:
		(mist if e[0] == "mist" else haze).append(e)
	if not mist.is_empty():
		holder.add_child(_flats(mist, MIST_SIZE, _mist_material(false), "mist"))
	if not haze.is_empty():
		holder.add_child(_flats(haze, Water.A * 2.0, _mist_material(true), "haze"))
	if not smokes.is_empty():
		holder.add_child(FarmFx.town_smoke(smokes))
	if not greens.is_empty():
		var s := FarmFx.town_smoke(greens)
		s.material_override = _green()
		holder.add_child(s)
	if holder.get_child_count() == 0:
		holder.free()
		return null
	return holder


## Lights up the wisps and glows at night (0 day, 1 night).
static func set_night(n: float) -> void:
	night = n
	if _spark:
		_spark.set_shader_parameter("strength", 0.65 + 1.6 * n)


## Cards that face the camera, all in one mesh: each vertex holds its card's middle, and the shader spreads them.
static func _cards(items: Array, mat: Material, node_name: String) -> MeshInstance3D:
	var verts := PackedVector3Array()
	var uv := PackedVector2Array()
	var uv2 := PackedVector2Array()
	var cols := PackedColorArray()
	var idx := PackedInt32Array()
	for j in items.size():
		var item: Array = items[j]
		var n := verts.size()
		for c: Vector2 in [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]:
			verts.append(item[0])
			uv.append(c)
			uv2.append(Vector2(item[1], float(j) * 1.37))
			cols.append(item[2])
		idx.append_array(PackedInt32Array([n, n + 1, n + 2, n, n + 2, n + 3]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_TEX_UV] = uv
	arrays[Mesh.ARRAY_TEX_UV2] = uv2
	arrays[Mesh.ARRAY_COLOR] = cols
	arrays[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.custom_aabb = AABB(Vector3(-5, -2, -5), Vector3(10, 5, 10))
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new()
	mi.name = node_name
	mi.mesh = mesh
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


## Flat squares of drifting haze, all in one mesh. items: [kind, x, y, z].
static func _flats(items: Array, size: float, mat: Material, node_name: String) -> MeshInstance3D:
	var verts := PackedVector3Array()
	var uv := PackedVector2Array()
	var normals := PackedVector3Array()
	var idx := PackedInt32Array()
	for item: Array in items:
		var n := verts.size()
		for c: Vector2 in [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]:
			var q := Vector2(item[1], item[2]) + (c - Vector2(0.5, 0.5)) * size
			verts.append(Vector3(q.x, item[3], -q.y))
			uv.append(c)
			normals.append(Vector3.UP)
		idx.append_array(PackedInt32Array([n, n + 2, n + 1, n, n + 3, n + 2]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_TEX_UV] = uv
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new()
	mi.name = node_name
	mi.mesh = mesh
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


static func _spark_material(rising: bool) -> ShaderMaterial:
	if _spark == null:
		var shader: Shader = load("res://shaders/swamp_spark.gdshader")
		_spark = ShaderMaterial.new()
		_spark.shader = shader
		_spark.set_shader_parameter("strength", 0.65)
		_rising = ShaderMaterial.new()
		_rising.shader = shader
		_rising.set_shader_parameter("rising", true)
		_rising.set_shader_parameter("strength", 0.8)
	return _rising if rising else _spark


static func _mist_material(rot: bool) -> ShaderMaterial:
	if _mist == null:
		var shader: Shader = load("res://shaders/mist.gdshader")
		_mist = ShaderMaterial.new()
		_mist.shader = shader
		_mist.set_shader_parameter("strength", 0.3)
		_haze = ShaderMaterial.new()
		_haze.shader = shader
		_haze.set_shader_parameter("tint", Color("#B7BC62"))
		_haze.set_shader_parameter("strength", 0.2)
		_haze.set_shader_parameter("layer", 1.0)
	return _haze if rot else _mist


static func _green() -> StandardMaterial3D:
	if _smoke_green == null:
		_smoke_green = StandardMaterial3D.new()
		_smoke_green.albedo_color = Color(0.62, 0.86, 0.5, 0.55)
		_smoke_green.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		_smoke_green.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return _smoke_green
