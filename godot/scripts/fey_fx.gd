class_name FeyFx
extends RefCounted
## The Feywild crossing's engine effects (art/handoff/feywild_kit.md): the Fey Gate's portal and wisps, and falling snow, leaves and petals. Flat and hard-edged, as the art is
## (Ethan: no smooth noise, stay stylized). All PLACEHOLDER looks, kept light for the phone: one mesh a tile, one a gate, no lights, no shadows, the work in the vertex shader.

const WISPS := 16
const FALLS := {"snow": 18, "leaves": 10, "petals": 12}   # PLACEHOLDER: how many at once on a tile
const FALL_COLOURS := {"snow": ["#F2F5FA", "#E6EBF1"], "leaves": ["#DB7A2E", "#C9502B", "#E5A92F"], "petals": ["#F7E8EE", "#F3D5E2", "#F7F2D8"]}
const FALL_SIZE := {"snow": 0.07, "leaves": 0.15, "petals": 0.11}
const FALL_SPEED := {"snow": 0.13, "leaves": 0.11, "petals": 0.09}
const PORTAL := {"fey_portal_a": [Color("#8E78D2"), 0.62], "fey_portal_b": [Color("#A995E2"), 0.8], "fey_portal_c": [Color("#C6B6F0"), 0.92], "fey_portal_d": [Color("#DFD5F9"), 1.0]}

static var _portal: ShaderMaterial
static var _wisp: ShaderMaterial
static var _fall: ShaderMaterial


## Takes the gate piece's portal bands out into a mesh of their own, one material with the colours in the vertices: a blended material still casts a solid shadow,
## and shadows are set per mesh. Returns [the piece without them, the portal].
static func split_gate(gate: Mesh) -> Array:
	var body := ArrayMesh.new()
	var verts := PackedVector3Array()
	var colours := PackedColorArray()
	var normals := PackedVector3Array()
	var order := {}
	for k in gate.get_surface_count():
		order[Kit.material_name(gate, k)] = k
	for k in gate.get_surface_count():
		if not PORTAL.has(Kit.material_name(gate, k)):
			var arrays := gate.surface_get_arrays(k)
			body.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
			body.surface_set_material(body.get_surface_count() - 1, gate.surface_get_material(k))
	for name: String in ["fey_portal_a", "fey_portal_b", "fey_portal_c", "fey_portal_d"]:   # rim to core, so each draws over the last
		var arrays := gate.surface_get_arrays(order[name])
		var c: Color = PORTAL[name][0].srgb_to_linear()
		c.a = PORTAL[name][1]
		var at: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var ns: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		for i: int in arrays[Mesh.ARRAY_INDEX]:
			verts.append(at[i])
			normals.append(ns[i])
			colours.append(c)
	var data := []
	data.resize(Mesh.ARRAY_MAX)
	data[Mesh.ARRAY_VERTEX] = verts
	data[Mesh.ARRAY_NORMAL] = normals
	data[Mesh.ARRAY_COLOR] = colours
	var portal := ArrayMesh.new()
	portal.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, data)
	if _portal == null:
		_portal = ShaderMaterial.new()
		_portal.shader = load("res://shaders/fey_portal.gdshader")
	portal.surface_set_material(0, _portal)
	return [body, portal]


static func set_night(n: float) -> void:
	if _portal:
		_portal.set_shader_parameter("night", n)


## A gate's wisps, in the gate's frame.
static func wisps() -> MeshInstance3D:
	var cards := []
	for k in WISPS:
		var a0 := GroundCover.hash01(k, 3, 81) * TAU
		var r0 := 1.8 + 1.6 * GroundCover.hash01(k, 3, 82)
		var z0 := 0.5 + 1.9 * GroundCover.hash01(k, 3, 83)
		var life := 4.0 + 2.0 * GroundCover.hash01(k, 3, 85)
		var phase := GroundCover.hash01(k, 3, 84)
		for j in 4:   # the head and three smaller behind it
			cards.append([Color(a0, r0, z0, life), Color(phase, 0.035 * j, 0.11 * (1.0 - 0.24 * j), 0.0), Color.WHITE])
	if _wisp == null:
		_wisp = ShaderMaterial.new()
		_wisp.shader = load("res://shaders/fey_wisp.gdshader")
	var mi := _cards(cards, _wisp, AABB(Vector3(-4, -1, -4), Vector3(8, 6, 8)))
	mi.name = "fey_wisps"
	return mi


## What falls on a tile: effects are the kinds fey_tile says. Tile-local.
static func falls(t: Vector2i, effects: Array) -> MeshInstance3D:
	var cards := []
	for kind: String in effects:
		var colours: Array = FALL_COLOURS[kind]
		for k in FALLS[kind]:
			var ang := GroundCover.hash01(t.x * 7 + k, t.y, 91) * TAU
			var far := sqrt(GroundCover.hash01(t.x * 7 + k, t.y, 92)) * Water.A
			var speed: float = FALL_SPEED[kind] * (0.8 + 0.4 * GroundCover.hash01(t.x * 7 + k, t.y, 93))
			var size: float = FALL_SIZE[kind] * (0.8 + 0.4 * GroundCover.hash01(t.x * 7 + k, t.y, 94))
			var c := Color(colours[k % colours.size()])
			cards.append([Color(far * cos(ang), far * sin(ang), GroundCover.hash01(t.x * 7 + k, t.y, 95), speed),
					Color(size, 0.05 if kind == "snow" else 0.16, 2.0 + 2.0 * GroundCover.hash01(k, t.y, 96), 0.0 if kind == "snow" else 1.0), c.srgb_to_linear()])
	if cards.is_empty():
		return null
	if _fall == null:
		_fall = ShaderMaterial.new()
		_fall.shader = load("res://shaders/fey_fall.gdshader")
	var mi := _cards(cards, _fall, AABB(Vector3(-5, -1, -5), Vector3(10, 6, 10)))
	mi.name = "fey_falls"
	return mi


## Cards the vertex shader places: each entry is [CUSTOM0, CUSTOM1, colour].
static func _cards(cards: Array, mat: Material, box: AABB) -> MeshInstance3D:
	var verts := PackedVector3Array()
	var uv := PackedVector2Array()
	var colours := PackedColorArray()
	var one := PackedFloat32Array()
	var two := PackedFloat32Array()
	var idx := PackedInt32Array()
	for card: Array in cards:
		var n := verts.size()
		for c: Vector2 in [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]:
			verts.append(Vector3.ZERO)
			uv.append(c)
			colours.append(card[2])
			one.append_array(PackedFloat32Array([card[0].r, card[0].g, card[0].b, card[0].a]))
			two.append_array(PackedFloat32Array([card[1].r, card[1].g, card[1].b, card[1].a]))
		idx.append_array(PackedInt32Array([n, n + 1, n + 2, n, n + 2, n + 3]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_TEX_UV] = uv
	arrays[Mesh.ARRAY_COLOR] = colours
	arrays[Mesh.ARRAY_CUSTOM0] = one
	arrays[Mesh.ARRAY_CUSTOM1] = two
	arrays[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) | (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT))
	mesh.custom_aabb = box
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi
