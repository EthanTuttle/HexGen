class_name Piece
extends RefCounted
## Builds low-poly, flat-shaded meshes out of flat-coloured parts, like hexkit.Piece in the art scripts.
## Points are plan coordinates (x east, y north) plus a height z; the mesh comes out in Godot's Y-up space.

var _st := SurfaceTool.new()
var _empty := true
var offset := Vector3.ZERO        # plan offset (x, y, z) added to every point

static var _material: StandardMaterial3D


func _init() -> void:
	_st.begin(Mesh.PRIMITIVE_TRIANGLES)


static func material() -> StandardMaterial3D:
	if _material == null:
		_material = StandardMaterial3D.new()
		_material.vertex_color_use_as_albedo = true
		_material.vertex_color_is_srgb = true
		_material.roughness = 0.9
	return _material


func _v(p: Vector3) -> Vector3:
	p += offset
	return Vector3(p.x, p.z, -p.y)


## One triangle, anticlockwise seen from its front (outside).
func tri(a: Vector3, b: Vector3, c: Vector3, col: Color) -> void:
	var va := _v(a); var vb := _v(b); var vc := _v(c)
	var n := (vb - va).cross(vc - va)
	if n.length_squared() < 1e-14:
		return
	n = n.normalized()
	_st.set_color(col)
	_st.set_normal(n)
	# Godot draws clockwise triangles as front faces.
	_st.add_vertex(va); _st.add_vertex(vc); _st.add_vertex(vb)
	_empty = false


func poly(pts: Array, col: Color) -> void:
	for k in range(1, pts.size() - 1):
		tri(pts[0], pts[k], pts[k + 1], col)


## Extrude a convex outline (plan points, anticlockwise) from z0 up to z1.
func prism(outline: PackedVector2Array, z0: float, z1: float, col: Color, side_col := Color(0, 0, 0, 0)) -> void:
	var sc := col if side_col.a == 0 else side_col
	var bottom := []; var top := []
	for p in outline:
		bottom.append(Vector3(p.x, p.y, z0))
		top.append(Vector3(p.x, p.y, z1))
	poly(top, col)
	var rb := bottom.duplicate()
	rb.reverse()
	poly(rb, sc)
	var n := outline.size()
	for i in n:
		var j := (i + 1) % n
		poly([bottom[i], bottom[j], top[j], top[i]], sc)


func flat(outline: PackedVector2Array, z: float, col: Color) -> void:
	prism(outline, 0.0, z, col)


func _ring(at: Vector3, radius: float, segments: int, spin: float, z: float) -> Array:
	var out := []
	for k in segments:
		var a := TAU * k / segments + spin
		out.append(at + Vector3(radius * cos(a), radius * sin(a), z))
	return out


func cone(at: Vector3, radius: float, height: float, col: Color, segments := 6, z := 0.0, spin := 0.0) -> void:
	var ring := _ring(at, radius, segments, spin, z)
	var tip := at + Vector3(0, 0, z + height)
	for k in segments:
		var a: Vector3 = ring[k]
		var b: Vector3 = ring[(k + 1) % segments]
		tri(a, b, tip, col)
		tri(b, a, at + Vector3(0, 0, z), col)


func cylinder(at: Vector3, radius: float, height: float, col: Color, segments := 6, z := 0.0) -> void:
	var lo := _ring(at, radius, segments, 0.0, z)
	var hi := _ring(at, radius, segments, 0.0, z + height)
	var rl := lo.duplicate()
	rl.reverse()
	poly(hi, col)
	poly(rl, col)
	for k in segments:
		var j := (k + 1) % segments
		poly([lo[k], lo[j], hi[j], hi[k]], col)


const _ICO_F := [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4],
	[11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
	[4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]


## An icosahedron (Blender's icosphere at subdivisions=1), squashed in height.
func blob(at: Vector3, radius: float, col: Color, z := 0.0, squash := 1.0) -> void:
	var t := (1.0 + sqrt(5.0)) / 2.0
	var raw := [Vector3(-1, t, 0), Vector3(1, t, 0), Vector3(-1, -t, 0), Vector3(1, -t, 0),
		Vector3(0, -1, t), Vector3(0, 1, t), Vector3(0, -1, -t), Vector3(0, 1, -t),
		Vector3(t, 0, -1), Vector3(t, 0, 1), Vector3(-t, 0, -1), Vector3(-t, 0, 1)]
	var v := []
	for p: Vector3 in raw:
		var s := p.normalized() * radius
		v.append(at + Vector3(s.x, s.y, s.z * squash + z))
	for f in _ICO_F:
		tri(v[f[0]], v[f[1]], v[f[2]], col)


func box(at: Vector3, size: Vector3, col: Color, z := 0.0, spin := 0.0) -> void:
	var c := cos(spin); var s := sin(spin)
	var pts := []
	for k in 8:
		var lx := (0.5 if k & 1 else -0.5) * size.x
		var ly := (0.5 if k & 2 else -0.5) * size.y
		var lz := (1.0 if k & 4 else 0.0) * size.z
		pts.append(at + Vector3(lx * c - ly * s, lx * s + ly * c, z + lz))
	for f in [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]:
		poly([pts[f[0]], pts[f[1]], pts[f[2]], pts[f[3]]], col)


func is_empty() -> bool:
	return _empty


func mesh() -> ArrayMesh:
	var m := _st.commit()
	if m.get_surface_count() > 0:
		m.surface_set_material(0, material())
	return m


func instance(name: String) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = name
	mi.mesh = mesh()
	return mi
