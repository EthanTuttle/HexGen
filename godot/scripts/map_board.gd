class_name MapBoard
extends Node3D
## The test map from art/scripts/render_preview.py (MAP), assembled by the same rules: edge wedges
## same/other, farm-village linking, border joins; water drawn per tile; ground cover scattered.

## Pointy-top axial (q, r) -> terrain. Copied from render_preview.py.
const MAP := {
	Vector2i(0, 0): "forest", Vector2i(1, -1): "forest", Vector2i(1, 0): "forest",
	Vector2i(0, 1): "plains", Vector2i(-2, 0): "plains",
	Vector2i(-1, 0): "village", Vector2i(-1, -1): "village",
	Vector2i(2, -1): "farmland", Vector2i(2, -2): "farmland", Vector2i(1, -2): "farmland", Vector2i(0, -2): "farmland",
	Vector2i(-2, 1): "river", Vector2i(-2, 2): "river", Vector2i(-1, 1): "river", Vector2i(-1, 2): "river",
	Vector2i(0, 2): "river", Vector2i(1, 1): "river", Vector2i(2, 0): "river", Vector2i(3, 0): "river",
	Vector2i(0, -1): "river",
}
const BORDERED := ["farmland", "village"]
const BLEND_WIDTH := 1.6   # ground colour fade width; no doc value yet, matches ground cover's BLEND

# render_animation.py
const RIVER_SPEED := 0.6
const LAKE_SPEED := 0.15
const GRID := 0.35

var water_shapes := {}     # (q, r) -> Water.tile_water() result
var boats: Array[Node3D] = []


static func linked(a, b) -> bool:
	return a == b or (a in BORDERED and b in BORDERED)


func build() -> void:
	var kit := Kit.meshes("res://art/tiles.glb")
	var ground := _ground_material(kit)
	var tiles := Node3D.new()
	tiles.name = "tiles"
	add_child(tiles)
	for t: Vector2i in MAP:
		var terrain: String = MAP[t]
		var at := Hex.tile_position(t.x, t.y)
		var base := Kit.place(tiles, kit, "base_" + terrain, at)
		base.name = "base_%d_%d" % [t.x, t.y]
		base.set_surface_override_material(0, ground)
		if terrain == "river":
			var mask := []
			for n in Hex.NEIGHBOURS:
				mask.append(MAP.get(t + n) == "river")
			water_shapes[t] = Water.tile_water(mask, "%d,%d" % [t.x, t.y])
			continue
		Kit.place(tiles, kit, terrain + "_centre", at)
		var joined := []
		for n in Hex.NEIGHBOURS:
			joined.append(linked(terrain, MAP.get(t + n)))
		for i in 6:
			var angle := deg_to_rad(60.0 * i)
			Kit.place(tiles, kit, terrain + ("_edge_same" if joined[i] else "_edge_other"), at, angle)
			# Carry a neighbouring edge's border out to this joined edge, so borders run on between tiles.
			if terrain in BORDERED and joined[i]:
				if not joined[(i + 1) % 6]:
					Kit.place(tiles, kit, "border_join_l", at, angle)
				if not joined[posmod(i - 1, 6)]:
					Kit.place(tiles, kit, "border_join_r", at, angle)
	_build_water()
	add_child(GroundCover.build(MAP, water_shapes))
	_build_slots()


## Ground colour per tile in a small lookup texture; the shader fades it toward the neighbours.
## The colour of each terrain is the top material of its base slab in the kit.
func _ground_material(kit: Dictionary) -> ShaderMaterial:
	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for t: Vector2i in MAP:
		var top := (kit["base_" + MAP[t]] as Mesh).surface_get_material(0) as BaseMaterial3D
		var c := top.albedo_color
		img.set_pixel(t.x + 32, t.y + 32, Color(c.r, c.g, c.b, 1))
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/ground.gdshader")
	mat.set_shader_parameter("terrain_map", ImageTexture.create_from_image(img))
	mat.set_shader_parameter("blend_width", BLEND_WIDTH)
	return mat


# --- Water -------------------------------------------------------------------

func _build_water() -> void:
	var dressing := Piece.new()
	var shores := []        # [world plan points, flow sign, speed]
	var outlines := []      # world plan outlines
	var bank := Hex.colour("bank")
	for t: Vector2i in water_shapes:
		var w: Dictionary = water_shapes[t]
		var at := Hex.tile_position(t.x, t.y)
		var seed := "%d,%d" % [t.x, t.y]
		var h := Water.downhill(t.x, t.y)
		var inflow := []
		for n in Hex.NEIGHBOURS:
			inflow.append(Water.downhill(t.x + n.x, t.y + n.y) < h)
		var speed := RIVER_SPEED if w.kind in ["river", "spring"] else LAKE_SPEED
		var signs := Water.flow_signs(w.ends, inflow)
		for k in w.shores.size():
			var pts := PackedVector2Array()
			for p in w.shores[k]:
				pts.append(at + p)
			shores.append([pts, signs[k], speed])
		for poly: PackedVector2Array in w.outlines:
			var pts := PackedVector2Array()
			for p in poly:
				pts.append(at + p)
			outlines.append(pts)
		# Banks and dressing (water.add_water with plates=False, boats=False)
		dressing.offset = Vector3(at.x, at.y, 0)
		for curve: PackedVector2Array in w.shores:
			for quad in Water.bank_strip(curve, 0.22):
				dressing.flat(quad, 0.025, bank)
		_add_dressing(dressing, w, seed, at)
	add_child(dressing.instance("water_dressing"))
	var mi := MeshInstance3D.new()
	mi.name = "water"
	mi.mesh = _water_mesh(outlines, shores)
	mi.material_override = load("res://shaders/water.tres")
	add_child(mi)


func _add_dressing(p: Piece, w: Dictionary, seed: String, at: Vector2) -> void:
	var d := Water.dressing(w.outlines, w.shores, w.kind, seed)
	var rng := PyRandom.new(seed + "-props")
	for r: Vector2 in d.reeds:
		for _k in 3:
			var jx := rng.uniform(-0.12, 0.12)
			var jy := rng.uniform(-0.12, 0.12)
			p.cone(Vector3(r.x + jx, r.y + jy, 0), 0.05, rng.uniform(0.35, 0.6), Hex.colour("reed"), 4)
	for r: Vector2 in d.rocks:
		p.blob(Vector3(r.x, r.y, 0), rng.uniform(0.12, 0.2), Hex.colour("rock"), 0.0, 0.6)
	for r: Vector2 in d.lilies:
		p.cylinder(Vector3(r.x, r.y, 0), rng.uniform(0.14, 0.22), 0.02, Hex.colour("lily"), 7, 0.03)
	for j in d.jetties:
		var ang: float = j[1]
		var dir := Vector2(cos(ang), sin(ang))
		var tip: Vector2 = j[0] + dir * 0.7
		p.box(Vector3(tip.x, tip.y, 0), Vector3(1.6, 0.45, 0.06), Hex.colour("trunk"), 0.12, ang)
		for s in [-1, 1]:
			var post: Vector2 = tip + dir * (0.6 * s)
			p.cylinder(Vector3(post.x, post.y, 0), 0.05, 0.2, Hex.colour("trunk"))
	# Boats are their own nodes so they can bob (render_animation.bob_boats).
	for b in d.boats:
		var piece := Piece.new()
		var ang: float = b[1]
		piece.box(Vector3.ZERO, Vector3(0.9, 0.36, 0.14), Hex.colour("trunk"), 0.03, ang)
		piece.box(Vector3.ZERO, Vector3(0.5, 0.26, 0.06), Hex.colour("boat"), 0.17, ang)
		var boat := Node3D.new()
		boat.name = "boat"
		boat.position = Hex.to3(at + b[0])
		boat.add_child(piece.instance("hull"))
		add_child(boat)
		boats.append(boat)


var _time := 0.0


func _process(delta: float) -> void:
	_time += delta   # engine time, so movie recordings at a fixed frame rate stay in step
	var s := _time
	for k in boats.size():
		boats[k].position.y = 0.03 * sin(TAU * s / 2.0 + k)
		boats[k].rotation.x = 0.05 * sin(TAU * s / 3.0 + k)


static func _seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var l2 := ab.length_squared()
	var t := clampf((p - a).dot(ab) / (l2 if l2 != 0.0 else 1.0), 0.0, 1.0)
	return (p - (a + ab * t)).length()


## One mesh for all water, with depth (UV.x) and flow (UV2, world XZ) per vertex, like
## render_animation.water_mesh(): outline points, a staggered grid inside, Delaunay triangles.
func _water_mesh(outlines: Array, shores: Array) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for raw: PackedVector2Array in outlines:
		var poly := PackedVector2Array()
		for k in raw.size():
			var a := raw[k]
			var b := raw[(k + 1) % raw.size()]
			var steps := maxi(1, int((b - a).length() / GRID))
			for j in steps:
				poly.append(a.lerp(b, float(j) / steps))
		var pts := poly.duplicate()
		var lo := Vector2(INF, INF); var hi := Vector2(-INF, -INF)
		for p in poly:
			lo = lo.min(p); hi = hi.max(p)
		var y := lo.y + GRID / 2
		while y < hi.y:
			var x := lo.x + GRID / 2 + (GRID / 2 if int((y - lo.y) / GRID) % 2 else 0.0)
			while x < hi.x:
				var p := Vector2(x, y)
				if Water.point_in(poly, p) and _min_dist(p, poly) > GRID * 0.4:
					pts.append(p)
				x += GRID
			y += GRID
		# Godot has no constrained Delaunay: triangulate all points, keep triangles inside the outline.
		var tris := Geometry2D.triangulate_delaunay(pts)
		for k in range(0, tris.size(), 3):
			var a := pts[tris[k]]; var b := pts[tris[k + 1]]; var c := pts[tris[k + 2]]
			if not Water.point_in(poly, (a + b + c) / 3.0):
				continue
			if (b - a).cross(c - a) < 0:
				var tmp := b; b = c; c = tmp
			for p in [a, c, b]:   # clockwise for Godot's front face
				var df := _depth_flow(p, shores)
				st.set_uv(Vector2(df.x, 0))
				st.set_uv2(Vector2(df.y, df.z))
				st.set_normal(Vector3.UP)
				st.add_vertex(Hex.to3(p, 0.03))
	return st.commit()


static func _min_dist(p: Vector2, poly: PackedVector2Array) -> float:
	var best := INF
	for k in poly.size():
		best = minf(best, _seg_dist(p, poly[k - 1], poly[k]))
	return best


## Distance to the nearest shore, and the flow there (x, z in Godot world).
static func _depth_flow(p: Vector2, shores: Array) -> Vector3:
	var best := INF
	var tangent := Vector2.ZERO
	var sign := 0
	var speed := 0.0
	for s in shores:
		var pts: PackedVector2Array = s[0]
		for k in range(1, pts.size()):
			var d := _seg_dist(p, pts[k - 1], pts[k])
			if d < best:
				best = d
				tangent = (pts[k] - pts[k - 1]).normalized()
				sign = s[1]
				speed = s[2]
	var fade := 1.0 if speed == RIVER_SPEED else maxf(0.0, 1.0 - best / 2.5)
	var f := tangent * (sign * speed * fade)
	return Vector3(minf(best, 10.0), f.x, -f.y)


func _build_slots() -> void:
	var p := Piece.new()
	var hexagon := Hex.hex_corners(Hex.R * 0.94, true)
	hexagon.reverse()
	var slots := {}
	for t: Vector2i in MAP:
		for n in Hex.NEIGHBOURS:
			if not MAP.has(t + n):
				slots[t + n] = true
	for t: Vector2i in slots:
		var at := Hex.tile_position(t.x, t.y)
		p.offset = Vector3(at.x, at.y, -0.3)
		p.flat(hexagon, 0.02, Hex.colour("slot"))
	add_child(p.instance("slots"))
