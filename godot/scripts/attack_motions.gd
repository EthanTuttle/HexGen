class_name AttackMotions
extends RefCounted
## The attack motions Ethan picked on Nov 7, 2026 (art/handoff/attack_motions.md; curves from
## art/scripts/render_attack_motions.py, each kind's picked branch): only the whole mini moves (it moves, leans on its base's
## edge, spins, scales and hops), plus flat unlit effects that fade and cast no shadows. Each motion is worked out per frame
## from the time since it started, as the script does, so the numbers carry over as they are.
##
## The script's frame is Z up with the attacker at the origin facing +X and the camera on the -Y side. Here a point in that
## frame is P(x, y, z) = Vector3(x, z, -y), which is also how plan points become 3D (Hex.to3); "forward" is the flat way to
## the target, "left" is UP x forward, and effects nudged toward the camera use the real camera.

const UP := Vector3.UP
const EDGE := 0.42          # a leaning mini rocks on its base's edge this far out
const FRONT := 0.22         # bursts and sparks sit this much toward the camera


# --- Curves -----------------------------------------------------------------

static func seg(s: float, a: float, b: float) -> float:
	return 0.0 if s <= a else 1.0 if s >= b else (s - a) / (b - a)


static func out(u: float) -> float:
	return 1.0 - (1.0 - u) * (1.0 - u)


static func inn(u: float) -> float:
	return u * u


static func smooth(u: float) -> float:
	return u * u * (3.0 - 2.0 * u)


static func bump(u: float) -> float:
	return sin(PI * clampf(u, 0.0, 1.0))


static func settle(v: float) -> float:
	v = clampf(v, 0.0, 1.0)
	return (1.0 - v) * (1.0 - v) * cos(1.5 * PI * v)


## The u at which smooth(u) = y (when the spin's blade reaches a foe).
static func smooth_inv(y: float) -> float:
	var lo := 0.0
	var hi := 1.0
	for _i in 30:
		var mid := (lo + hi) / 2.0
		if smooth(mid) < y:
			lo = mid
		else:
			hi = mid
	return lo


## A point given in the script's frame (Z up) as a 3D offset.
static func P(x: float, y: float, z: float) -> Vector3:
	return Vector3(x, z, -y)


## The flat direction at the script's angle (degrees from +X, anticlockwise from above).
static func dir_at(deg: float) -> Vector3:
	return Vector3(cos(deg_to_rad(deg)), 0.0, -sin(deg_to_rad(deg)))


## The script's angle of a flat direction.
static func angle_of(d: Vector3) -> float:
	return rad_to_deg(atan2(-d.z, d.x))


## A rotation taking +X to d, keeping up up (the script's aim()).
static func aim(d: Vector3) -> Basis:
	var x := d.normalized()
	var z := x.cross(UP)
	if z.length() < 1e-4:
		z = Vector3(0, 0, 1)
	z = z.normalized()
	return Basis(x, z.cross(x), z)


## A rotation of `deg` about an axis given in the script's frame.
static func rot(ax: float, ay: float, az: float, deg: float) -> Basis:
	return Basis(P(ax, ay, az).normalized(), deg_to_rad(deg))


static func flat(v: Vector3) -> Vector3:
	v.y = 0.0
	return v.normalized() if v.length() > 1e-4 else Vector3(1, 0, 0)


# --- Actors -----------------------------------------------------------------

## A whole mini: it can move, lean on a base edge, spin and scale, and nothing else. Set again every frame from rest.
class Actor:
	var mini: Node3D
	var body: Node3D
	var off := Vector3.ZERO
	var lean_v := Vector2.ZERO   # degrees toward a flat direction: (x, -z)
	var edge := 0.0
	var spin := 0.0
	var scale := 1.0

	func _init(m: Node3D) -> void:
		mini = m
		body = m.get_node("body")

	func home() -> Vector3:
		return mini.global_position

	func reset() -> void:
		off = Vector3.ZERO
		lean_v = Vector2.ZERO
		edge = 0.0
		spin = 0.0
		scale = 1.0

	func move(d: Vector3) -> void:
		off += d

	## Tip the top toward a flat direction, rocking on the base's edge on that side (edge 0: on its middle).
	func lean(deg: float, toward: Vector3, e := EDGE) -> void:
		lean_v += Vector2(toward.x, -toward.z).normalized() * deg
		if absf(deg) > 1e-4:
			edge = e if deg > 0 else -e

	func apply() -> void:
		var deg := lean_v.length()
		var d := lean_v.normalized() if deg > 1e-6 else Vector2(1, 0)
		var dd := Vector3(d.x, 0, -d.y)
		var pv := dd * edge * minf(1.0, deg / 4.0)   # rock on the edge once it really leans
		var w := Transform3D(Basis.IDENTITY, off + pv) * Transform3D(Basis(UP.cross(dd).normalized(), deg_to_rad(deg)), Vector3.ZERO) \
				* Transform3D(Basis.IDENTITY, -pv) * Transform3D(Basis(UP, deg_to_rad(spin)).scaled(Vector3.ONE * maxf(scale, 1e-4)), Vector3.ZERO)
		var face := Transform3D(mini.global_basis.orthonormalized(), Vector3.ZERO)
		body.transform = face.affine_inverse() * w * face   # the world move, in the mini's own frame
		body.visible = scale >= 1e-3


# --- Effects ----------------------------------------------------------------

## An effect: placed, scaled and faded per frame; hidden when not shown.
class Fx:
	var node: MeshInstance3D
	var mat: StandardMaterial3D
	var colour: Color

	func _init(parent: Node, mesh: Mesh, col: Color, lit := false) -> void:
		node = MeshInstance3D.new()
		node.mesh = mesh
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mat = StandardMaterial3D.new()
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		mat.vertex_color_use_as_albedo = true
		if lit:
			mat.roughness = 0.9
		else:
			mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		colour = col
		mat.albedo_color = col
		node.material_override = mat
		node.visible = false
		parent.add_child(node)

	## scale: a number, or a Vector3 in the script's axes (x along, y across, z up).
	func show(at: Vector3, scale = 1.0, b := Basis.IDENTITY, alpha := 1.0) -> void:
		var s: Vector3 = Vector3.ONE * scale if scale is float or scale is int else Vector3(scale.x, scale.z, scale.y)
		node.visible = minf(minf(s.x, s.y), s.z) > 1e-4 and alpha > 0.003
		node.global_transform = Transform3D(b * Basis.from_scale(s), at)
		mat.albedo_color = Color(colour, clampf(alpha, 0.0, 1.0))

	func hide() -> void:
		node.visible = false


# --- Meshes (built in the script's frame) ------------------------------------

static func _mesh(tris: Array, cols := []) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in tris.size():
		st.set_color(cols[i] if not cols.is_empty() else Color.WHITE)
		st.add_vertex(tris[i])
	st.generate_normals()
	return st.commit()


static func _quad(out_tris: Array, a: Vector3, b: Vector3, c: Vector3, d: Vector3) -> void:
	out_tris.append_array([a, b, c, a, c, d])


## A star of flat-shaded spikes from the origin, mostly outward and a bit up (each a four-sided pyramid).
static func spikes(n: int, length: float, width: float, up := 0.0, sd := 0) -> ArrayMesh:
	var tris := []
	for k in n:
		var a := TAU * (k + 0.37 * ((k * 7 + sd) % 3)) / n
		var d := Vector3(cos(a), sin(a), up + 0.25 * ((k + sd) % 2)).normalized()
		var side := d.cross(Vector3(0, 0, 1))
		side = side.normalized() * width if side.length() > 1e-6 else Vector3(width, 0, 0)
		var lift := d.cross(side).normalized() * width
		var tip := d * length * (0.75 + 0.25 * ((k + sd) % 3) / 2.0)
		var vs := [side, lift, -side, -lift]
		for i in 4:
			tris.append_array([_p(vs[i]), _p(vs[(i + 1) % 4]), _p(tip)])
	return _mesh(tris)


static func _p(v: Vector3) -> Vector3:
	return P(v.x, v.y, v.z)


## A flat crescent from angle a0 to a1 (degrees), thickest at a1 (the leading end) when tapered.
static func arc(r0: float, r1: float, a0: float, a1: float, segs := 14, taper := true) -> ArrayMesh:
	var tris := []
	var inner := []
	var outer := []
	for k in segs + 1:
		var u := float(k) / segs
		var a := deg_to_rad(a0 + (a1 - a0) * u)
		var w := (r1 - r0) * (pow(u, 0.8) if taper else 1.0)
		var rr := (r0 + r1) / 2.0
		inner.append(P(cos(a) * (rr - w / 2), sin(a) * (rr - w / 2), 0))
		outer.append(P(cos(a) * (rr + w / 2), sin(a) * (rr + w / 2), 0))
	for k in segs:
		_quad(tris, inner[k], inner[k + 1], outer[k + 1], outer[k])
	return _mesh(tris)


static func ring(r: float, width: float, segs := 24) -> ArrayMesh:
	return arc(r - width / 2, r + width / 2, 0, 360, segs, false)


## An open upright tube, base at the origin.
static func band(r: float, h: float, segs := 16) -> ArrayMesh:
	var tris := []
	for k in segs:
		var a := TAU * k / segs
		var b := TAU * (k + 1) / segs
		_quad(tris, P(cos(a) * r, sin(a) * r, 0), P(cos(b) * r, sin(b) * r, 0), P(cos(b) * r, sin(b) * r, h), P(cos(a) * r, sin(a) * r, h))
	return _mesh(tris)


## A 6-sided prism of radius 1 from x = 0 to x = 1: scaled per frame.
static func beam() -> ArrayMesh:
	var tris := []
	var a := []
	var b := []
	for k in 6:
		a.append(P(0, cos(k * PI / 3), sin(k * PI / 3)))
		b.append(P(1, cos(k * PI / 3), sin(k * PI / 3)))
	for k in 6:
		_quad(tris, a[k], a[(k + 1) % 6], b[(k + 1) % 6], b[k])
	for k in range(1, 5):
		tris.append_array([a[0], a[k + 1], a[k], b[0], b[k], b[k + 1]])
	return _mesh(tris)


## A jagged lightning stroke along +X, 5 segments.
static func zigzag(length: float, sd: int) -> ArrayMesh:
	var pts := [Vector3.ZERO]
	for k in range(1, 5):
		var j := ((k * 37 + sd * 11) % 7 - 3) / 3.0
		pts.append(Vector3(length * k / 5.0, 0.06 * j, 0.05 * ((k + sd) % 3 - 1)))
	pts.append(Vector3(length, 0, 0))
	var tris := []
	for i in pts.size() - 1:
		var p: Vector3 = pts[i]
		var q: Vector3 = pts[i + 1]
		var side := (q - p).cross(Vector3(0, 0, 1)).normalized() * 0.022
		var up := Vector3(0, 0, 0.022)
		var v := [p + side, p + up, p - side, q - side, q + up, q + side].map(func(x): return _p(x))
		_quad(tris, v[0], v[1], v[4], v[5])
		_quad(tris, v[1], v[2], v[3], v[4])
		_quad(tris, v[2], v[0], v[5], v[3])
	return _mesh(tris)


## A low-poly ball: an icosahedron, split once for sub 1.
static func ico(r: float, sub := 1) -> ArrayMesh:
	var t := (1.0 + sqrt(5.0)) / 2.0
	var v := [Vector3(-1, t, 0), Vector3(1, t, 0), Vector3(-1, -t, 0), Vector3(1, -t, 0), Vector3(0, -1, t), Vector3(0, 1, t),
		Vector3(0, -1, -t), Vector3(0, 1, -t), Vector3(t, 0, -1), Vector3(t, 0, 1), Vector3(-t, 0, -1), Vector3(-t, 0, 1)]
	var f := [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
		[3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
	var faces := []
	for fc in f:
		faces.append([v[fc[0]].normalized(), v[fc[1]].normalized(), v[fc[2]].normalized()])
	for _s in sub:
		var finer := []
		for fc in faces:
			var ab: Vector3 = (fc[0] + fc[1]).normalized()
			var bc: Vector3 = (fc[1] + fc[2]).normalized()
			var ca: Vector3 = (fc[2] + fc[0]).normalized()
			finer.append_array([[fc[0], ab, ca], [ab, fc[1], bc], [ca, bc, fc[2]], [ab, bc, ca]])
		faces = finer
	var tris := []
	for fc in faces:
		tris.append_array([fc[0] * r, fc[2] * r, fc[1] * r])
	return _mesh(tris)


## A flat hex on a combat cell (flat-top, as the boards are), radius 0.55.
static func hex_plate() -> ArrayMesh:
	var tris := []
	for k in 6:
		var a := deg_to_rad(60.0 * k)
		var b := deg_to_rad(60.0 * (k + 1))
		tris.append_array([Vector3.ZERO, Vector3(cos(a), 0, -sin(a)) * 0.55, Vector3(cos(b), 0, -sin(b)) * 0.55])
	return _mesh(tris)


static func _box(tris: Array, cols: Array, lo: Vector3, hi: Vector3, col: Color) -> void:
	var c := []
	for i in 8:
		c.append(_p(Vector3(hi.x if i & 1 else lo.x, hi.y if i & 2 else lo.y, hi.z if i & 4 else lo.z)))
	for q in [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]:
		_quad(tris, c[q[0]], c[q[1]], c[q[2]], c[q[3]])
	for _i in 36:
		cols.append(col)


## The arrow: along +X, tip at x = 0.42, nock at 0 (wood shaft, iron head, pale fletching).
static func arrow() -> ArrayMesh:
	var tris := []
	var cols := []
	_box(tris, cols, Vector3(0, -0.007, -0.007), Vector3(0.4, 0.007, 0.007), Color("#8A6440"))
	var base := [Vector3(0.385, 0.03, 0), Vector3(0.385, 0, 0.03), Vector3(0.385, -0.03, 0), Vector3(0.385, 0, -0.03)]
	for i in 4:
		tris.append_array([_p(base[i]), _p(base[(i + 1) % 4]), _p(Vector3(0.455, 0, 0))])
		tris.append_array([_p(base[(i + 1) % 4]), _p(base[i]), _p(Vector3(0.385, 0, 0))])
		for _j in 6:
			cols.append(Color("#6F7A82"))
	for z in [1.0, -1.0]:
		tris.append_array([_p(Vector3(0, 0, 0)), _p(Vector3(0.09, 0, 0)), _p(Vector3(0.02, 0, z * 0.04))])
		for _j in 3:
			cols.append(Color("#E8E2D4"))
	return _mesh(tris, cols)


## The thrown dagger: along +X, point at x = 0.26, moved back by `back` so it turns about its middle.
static func dagger(back := 0.0) -> ArrayMesh:
	var tris := []
	var cols := []
	var o := Vector3(back, 0, 0)
	var bl := [Vector3(0.06, 0.03, 0), Vector3(0.26, 0, 0), Vector3(0.06, -0.03, 0), Vector3(0.06, 0, 0.01), Vector3(0.06, 0, -0.01)]
	for f in [[0, 3, 1], [3, 2, 1], [2, 4, 1], [4, 0, 1]]:
		tris.append_array([_p(bl[f[0]] + o), _p(bl[f[1]] + o), _p(bl[f[2]] + o)])
		for _j in 3:
			cols.append(Color("#C9CED2"))
	_box(tris, cols, Vector3(-0.01, -0.008, -0.008) + o, Vector3(0.06, 0.008, 0.008) + o, Color("#4A3426"))
	return _mesh(tris, cols)


# --- The player -------------------------------------------------------------

var board: Node3D
var camera: Camera3D
var _actors: Array[Actor] = []
var _fx: Array[Fx] = []


func _init(b: Node3D) -> void:
	board = b
	camera = b.get_viewport().get_camera_3d()


func actor(m: Node3D) -> Actor:
	for a in _actors:
		if a.mini == m:
			return a
	var a := Actor.new(m)
	_actors.append(a)
	return a


func fx(mesh: Mesh, col: String, lit := false) -> Fx:
	var f := Fx.new(board, mesh, Color(col), lit)
	_fx.append(f)
	return f


## Plays update(s) every frame for `dur` seconds, from rest each frame; then puts the minis back and clears the effects.
func run(dur: float, update: Callable) -> void:
	var s := 0.0
	while s < dur:
		for a in _actors:
			a.reset()
		update.call(s)
		for a in _actors:
			if is_instance_valid(a.mini):
				a.apply()
		await board.get_tree().process_frame
		s += board.get_process_delta_time()   # frame time, so a fixed-rate capture plays at real speed
	for a in _actors:
		if is_instance_valid(a.mini):
			a.reset()
			a.apply()
	for f in _fx:
		f.node.queue_free()
	_actors.clear()
	_fx.clear()


## The flat way from p toward the camera, FRONT long.
func front(p: Vector3) -> Vector3:
	return flat(camera.global_position - p) * FRONT if camera else Vector3.ZERO


# --- Shared moves -----------------------------------------------------------

func hop(a: Actor, s: float, t0: float, toward: Vector3, dur := 0.32, h := 0.35, reach := 0.3, lean_deg := 10.0) -> void:
	var u := seg(s, t0, t0 + dur)
	if u > 0.0 and u < 1.0:
		var b := bump(u)
		a.move(toward * reach * b + UP * h * b)
		a.lean(lean_deg * b, toward, 0.0)


func recoil(a: Actor, s: float, t0: float, toward: Vector3, tilt := 16.0, push := 0.12, rec := 0.07, settle_t := 0.35) -> void:
	if s < t0:
		return
	var u := s - t0
	var k := out(u / rec) if u < rec else settle((u - rec) / settle_t)
	a.move(toward * push * k)
	a.lean(tilt * k, toward)


## A ring of puffs pushing out to a spread, rising a little, shrinking to 40% and fading.
func puff(list: Array, s: float, t0: float, at: Vector3, dur := 0.3, spread := 0.22, size := 0.07, up := 0.12) -> void:
	var u := seg(s, t0, t0 + dur)
	for k in list.size():
		var f: Fx = list[k]
		if u > 0.0 and u < 1.0:
			var p := at + dir_at(rad_to_deg(TAU * k / list.size() + 0.4)) * spread * out(u) + UP * up * out(u) * (0.5 + 0.5 * (k % 2))
			f.show(p, size * (1.0 - 0.6 * u) * (0.8 + 0.4 * (k % 2)), Basis.IDENTITY, 1.0 - u * u)
		else:
			f.hide()


func dust(n: int, col := "#D8CBB0") -> Array:
	var out_list := []
	var m := ico(1.0, 0)
	for _i in n:
		out_list.append(fx(m, col, true))
	return out_list


## A burst that grows from 40% to full size and fades.
func flash(f: Fx, s: float, t0: float, at: Vector3, dur := 0.18, size := 0.3, b := Basis.IDENTITY) -> void:
	var u := seg(s, t0, t0 + dur)
	if u > 0.0 and u < 1.0:
		f.show(at + front(at), size * (0.4 + 0.6 * out(u)), b, 1.0 - pow(u, 1.5))
	else:
		f.hide()


## A caster's wind-up: the mini lifts a little and a ring of light tightens round its base.
func charge(a: Actor, s: float, ringfx: Fx, base: Vector3, t0 := 0.0, dur := 0.14) -> void:
	var u := seg(s, t0, t0 + dur)
	var k := out(u) if s < t0 + dur + 0.1 else 1.0 - smooth(seg(s, t0 + dur + 0.1, t0 + dur + 0.35))
	a.move(UP * 0.1 * k)
	if (u > 0.0 and u < 1.0) or (s < t0 + dur + 0.12 and s >= t0):
		ringfx.show(base + UP * 0.02, 0.75 - 0.25 * u, Basis.IDENTITY, minf(1.0, 3.0 * u) * (1.0 - seg(s, t0 + dur, t0 + dur + 0.12)))
	else:
		ringfx.hide()


## The miss (A, sidestep), started `t0` before its hit time would be: the target slides across the attack toward the
## camera's side, a whiff crescent sweeps through where it stood, and a little dust where it lands.
func miss(t: Actor, s: float, hit: float, toward: Vector3, whiff: Fx, puffs: Array) -> void:
	var t0 := hit - 0.08
	var left := UP.cross(toward).normalized()
	var side := -left if (-left).dot(flat(camera.global_position - t.home()) if camera else -left) >= 0.0 else left
	var k := out(seg(s, t0 + 0.08, t0 + 0.18)) if s < t0 + 0.32 else 1.0 - smooth(seg(s, t0 + 0.32, t0 + 0.55))
	t.move(toward * 0.04 * k + side * 0.3 * k)
	t.lean(6.0 * k, side, 0.0)
	var v := seg(s, t0 + 0.14, t0 + 0.30)
	if v > 0.0 and v < 1.0:
		whiff.show(t.home() - toward * 0.05 + UP * 0.6, 1.4, aim(toward) * rot(0, 1, 0, 70) * rot(0, 0, 1, -90 + 150 * out(v)), 0.7 * (1.0 - v))
	else:
		whiff.hide()
	puff(puffs, s, t0 + 0.2, t.home() + side * 0.3 + UP * 0.02, 0.25, 0.18, 0.03, 0.04)


# --- The picked motions -----------------------------------------------------

## One attack of `kind` from a onto t: melee, sweep, thrust, heavy, shot, thrown, orb, ray, darts, touch, or a save
## spell's ("save": the old hop, PLACEHOLDER until a motion is picked for it). hit = false plays the miss.
func attack(kind: String, am: Node3D, tm: Node3D, hit := true) -> void:
	var a := actor(am)
	var t := actor(tm)
	var a0 := am.global_position
	var t0 := tm.global_position
	var d := flat(t0 - a0)
	var whiff := fx(arc(0.16, 0.22, -60, 60), "#FFFFFF")
	var miss_dust := dust(5, "#E8E0CC")
	var hit_at := 0.16
	var dur := 0.95
	var upd: Callable
	match kind:
		"sweep":   # A, spin (sweep below)
			await sweep(am, [tm], [hit])
			return
		"thrust":   # B, pivot jab
			var streak := fx(beam(), "#FFFFFF")
			var star := fx(spikes(7, 0.26, 0.035, 0.1), "#FFF4C8")
			var far := (t0 - a0).length()
			hit_at = 0.08
			upd = func(s: float) -> void:
				var k := out(seg(s, 0, 0.08)) if s < 0.13 else 1.0 - smooth(seg(s, 0.13, 0.33))
				a.lean(26.0 * k, d)
				var v := seg(s, hit_at - 0.04, hit_at + 0.12)
				if v > 0.0 and v < 1.0:
					var x0 := (0.25 + 0.9 * out(v)) * far / 2.0
					streak.show(a0 + d * (x0 - 0.5 * (1.0 - v)) + front(a0) * 0.55 + UP * 0.6, Vector3(0.5 + 0.5 * (1.0 - v), 0.028, 0.028), aim(d), 1.0 - v)
				else:
					streak.hide()
				if hit:
					recoil(t, s, hit_at, d, 15.0)
					flash(star, s, hit_at, t0 - d * 0.3 + UP * 0.55, 0.18, 1.0)
		"heavy":   # A, big hop slam
			var shock := fx(ring(1.0, 0.1), "#F4E6C0")
			var star := fx(spikes(9, 0.28, 0.035, 0.25), "#FFE9A8")
			var puffs := dust(8)
			hit_at = 0.38
			dur = 1.0
			upd = func(s: float) -> void:
				var rise := seg(s, 0, 0.26)
				var fall := seg(s, 0.3, 0.38)
				var back := seg(s, 0.42, 0.58)
				var z := 0.6 * out(rise) if s < 0.3 else (0.6 * (1.0 - inn(fall)) if s < 0.38 else 0.0)
				var x := 0.32 * rise if s < 0.38 else 0.32 * (1.0 - smooth(back))
				a.move(d * x + UP * z)
				var l := -10.0 * out(rise) if s < 0.3 else (-10.0 + 32.0 * fall if s < 0.38 else 22.0 * (1.0 - smooth(back)))
				a.lean(l, d, 0.0 if s < 0.38 else EDGE)
				if hit:
					recoil(t, s, hit_at, d, 26.0, 0.2, 0.07, 0.45)
					var near := t0 - d * 0.4 + UP * 0.02
					var u := seg(s, hit_at, hit_at + 0.3)
					if u > 0.0 and u < 1.0:
						shock.show(near, 0.25 + 0.6 * out(u), Basis.IDENTITY, 1.0 - u)
					else:
						shock.hide()
					puff(puffs, s, hit_at, near, 0.35, 0.35, 0.06)
					flash(star, s, hit_at, t0 - d * 0.25 + UP * 0.55, 0.2, 1.0)
		"shot":   # A, straight
			var arw := fx(arrow(), "#FFFFFF", true)
			var trl := fx(beam(), "#FFFFFF")
			var puffs := dust(5, "#E8E0CC")
			var from := a0 + d * 0.3 + UP * 0.55
			var to := t0 - d * 0.25 + UP * 0.42
			var dv := (to - from).normalized()
			hit_at = 0.26
			upd = func(s: float) -> void:
				a.lean(-7.0 * bump(seg(s, 0.08, 0.28)), d)
				var u := seg(s, 0.08, 0.26)
				if u > 0.0 and u < 1.0:
					var pos := from.lerp(to, u)
					arw.show(pos - dv * 0.6, 1.5, aim(dv))
					trl.show(pos - dv * (0.4 + 0.5 * minf(1.0, u * 3.0)), Vector3(0.5 * minf(1.0, u * 3.0), 0.016, 0.016), aim(dv), 0.8)
				else:
					arw.hide()
					trl.hide()
				if hit:
					recoil(t, s, hit_at, d, 14.0)
					puff(puffs, s, hit_at, to, 0.25, 0.12, 0.035, 0.05)
		"thrown":   # A, snap throw, turning end over end
			var dg := fx(dagger(-0.13 / 1.6), "#FFFFFF", true)
			var star := fx(spikes(7, 0.24, 0.03, 0.1), "#FFF4C8")
			var from := a0 + d * 0.35 + UP * 0.62
			var to := t0 - d * 0.22 + UP * 0.5
			hit_at = 0.34
			upd = func(s: float) -> void:
				var k := out(seg(s, 0, 0.08)) if s < 0.1 else 1.0 - smooth(seg(s, 0.1, 0.3))
				a.lean(12.0 * k, d)
				var u := seg(s, 0.08, 0.34)
				if u > 0.0 and u < 1.0:
					dg.show(from.lerp(to, u) + UP * 0.18 * bump(u), 1.6, aim(d) * rot(0, 1, 0, -900.0 * u))
				else:
					dg.hide()
				if hit:
					recoil(t, s, hit_at, d, 14.0)
					flash(star, s, hit_at, t0 - d * 0.25 + UP * 0.5, 0.18, 1.0)
		"orb", "ray", "darts":   # Firebolt, Frost Ray, Magic Bolt
			var c1: String = {"orb": "#FF8A2A", "ray": "#8FD8FF", "darts": "#B07CFF"}[kind]
			var c2: String = {"orb": "#FFD24A", "ray": "#E6F7FF", "darts": "#EBDDFF"}[kind]
			var rg := fx(ring(1.0, 0.07), c1)
			var from := a0 + d * 0.32 + UP * 0.75
			var to := t0 - d * 0.25 + UP * 0.5
			var left := UP.cross(d).normalized()
			var burst := fx(spikes(9, 0.34, 0.05, 0.3), c2)
			var burst2 := fx(spikes(7, 0.44, 0.045, 0.2, 3), c1)
			var core := fx(ico(0.13), c2)
			var tails := []
			for k in 5:
				tails.append(fx(ico(0.1), c1))
			var bm := fx(beam(), c2)
			var bm2 := fx(beam(), c1)
			var darts := []
			for k in 3:
				darts.append(fx(ico(0.1), c2))
			hit_at = {"orb": 0.36, "ray": 0.19, "darts": 0.36}[kind]
			upd = func(s: float) -> void:
				charge(a, s, rg, a0)
				if kind == "orb":
					var u := seg(s, 0.14, 0.36)
					if u > 0.0 and u < 1.0:
						core.show(from.lerp(to, u), 1.0)
						for k in 5:
							var uu := u - 0.05 * (k + 1)
							(tails[k] as Fx).show(from.lerp(to, maxf(uu, 0.0)), 0.9 - 0.15 * k, Basis.IDENTITY, 0.9 if uu > 0.0 else 0.0)
					else:
						core.hide()
						for tl in tails:
							(tl as Fx).hide()
					if hit:
						recoil(t, s, 0.36, d)
						flash(burst, s, 0.36, to, 0.2, 1.0)
						flash(burst2, s, 0.38, to, 0.25, 1.0)
				elif kind == "ray":
					var u := seg(s, 0.14, 0.19)
					if s >= 0.14 and s < 0.46:
						var w := 0.03 * (1.0 + 0.25 * sin(s * 90.0)) * (1.0 - seg(s, 0.36, 0.46))
						var l := (to - from).length() * out(u)
						bm.show(from, Vector3(l, w, w), aim(to - from))
						bm2.show(from, Vector3(l, w * 2.2, w * 2.2), aim(to - from), 0.45)
					else:
						bm.hide()
						bm2.hide()
					if hit:
						recoil(t, s, 0.19, d)
						flash(burst, s, 0.19, to, 0.3, 0.9)
				else:
					var hits := []
					for k in 3:
						var st := 0.14 + 0.06 * k
						var u := seg(s, st, st + 0.22)
						if u > 0.0 and u < 1.0:
							(darts[k] as Fx).show(from.lerp(to, u) + left * (k - 1) * 0.55 * bump(u) + UP * 0.15 * bump(u) * (1 - absi(k - 1)), 1.0)
						else:
							(darts[k] as Fx).hide()
						hits.append(st + 0.22)
					if hit:
						var last := -1
						for k in 3:
							if s >= hits[k]:
								last = k
						if last >= 0:   # a recoil restarts on each new hit
							recoil(t, s, hits[last], d, [8.0, 8.0, 10.0][last])
						flash(burst, s, hits[0], to, 0.15, 0.6)
						flash(burst2, s, hits[2], to, 0.18, 0.6)
		"touch":   # B, charge then tap (Shocking Grasp)
			var orbit := []
			for j in 4:
				orbit.append(fx(zigzag(0.16, j + 5), "#9FE3FF"))
			var zaps := []
			for j in 5:
				zaps.append(fx(zigzag(0.4, j), "#BFEFFF"))
			var core := fx(ico(0.06), "#FFFFFF")
			var c := t0 - d * 0.38 + UP * 0.5
			var left := UP.cross(d).normalized()
			hit_at = 0.34
			upd = func(s: float) -> void:
				var cu := seg(s, 0, 0.22)
				for j in 4:
					if s < 0.3:
						var ang := 720.0 * cu + j * 90.0
						(orbit[j] as Fx).show(a.home() + a.off + UP * (0.3 + 0.12 * j) + dir_at(ang) * 0.26, 1.0,
								Basis(UP, deg_to_rad(ang + 90.0 + 40.0 * fmod(s * 60.0, 2.0))), 0.9 * (1.0 - seg(s, 0.24, 0.3)))
					else:
						(orbit[j] as Fx).hide()
				hop(a, s, 0.22, d, 0.24, 0.16, 0.3, 12.0)
				if not hit:
					return
				var v := seg(s, hit_at, hit_at + 0.2)
				for j in 5:
					if v > 0.0 and v < 1.0:
						var ang := j * 72.0 + 25.0 * sin(s * 70.0 + j)
						var flick := 1.0 if (int(s * 60.0) + j) % 3 else 0.6
						(zaps[j] as Fx).show(c, (0.6 + 0.6 * out(v)) * flick, aim(d) * rot(0, 0, 1, ang) * rot(0, 1, 0, 20.0 * (j % 3 - 1)), 1.0 - v)
					else:
						(zaps[j] as Fx).hide()
				flash(core, s, hit_at, c, 0.12, 1.6)
				if s >= hit_at:
					recoil(t, s, hit_at, d, 12.0)
					var u := s - hit_at
					if u < 0.25:   # a buzz: the hit mini shivers side to side
						t.move(left * 0.025 * sin(u * 140.0) * (1.0 - u / 0.25))
		_:   # melee (A, hop), and save spells until they get their own
			upd = func(s: float) -> void:
				hop(a, s, 0, d)
				if hit:
					recoil(t, s, 0.16, d)
	if not hit:
		var main := upd
		upd = func(s: float) -> void:
			main.call(s)
			miss(t, s, hit_at, d, whiff, miss_dust)
	await run(dur, upd)


## The spin sweep (A, spin): one full turn clockwise, the blade starting on the mini's left; each foe in `targets` reacts as
## the trail passes it, recoiling when its `hits` entry is true and sidestepping when false. Sweeping Arc plays it once for
## all its foes (Ethan, Nov 8).
func sweep(am: Node3D, targets: Array, hits: Array) -> void:
	var a := actor(am)
	var a0 := am.global_position
	var d := flat(targets[0].global_position - a0) if not targets.is_empty() else flat(am.global_transform.basis.z)
	var trail := fx(arc(0.5, 0.78, 150, 0, 18), "#FFFFFF")
	var start := angle_of(d) + 90.0
	var foes := []   # [actor, way to it, hit time, hit, whiff, dust]
	for i in targets.size():
		var dt := flat((targets[i] as Node3D).global_position - a0)
		var at := 0.45 * smooth_inv(fmod(fmod(start - angle_of(dt), 360.0) + 360.0, 360.0) / 360.0)
		foes.append([actor(targets[i]), dt, at, hits[i], fx(arc(0.16, 0.22, -60, 60), "#FFFFFF"), dust(5, "#E8E0CC")])
	await run(0.95, func(s: float) -> void:
		var u := seg(s, 0, 0.45)
		a.spin = -360.0 * smooth(u)
		a.move(UP * 0.08 * bump(u))
		if u > 0.0 and u < 1.0:
			trail.show(a0 + UP * 0.45, 1.0, Basis(UP, deg_to_rad(start - 360.0 * smooth(u))), minf(1.0, 4.0 * u) * (1.0 - u * u * u))
		else:
			trail.hide()
		for f: Array in foes:
			if f[3]:
				recoil(f[0], s, f[2], f[1])
			else:
				miss(f[0], s, f[2], f[1], f[4], f[5]))


## Bless and heals (A, rising ring): the caster bobs, a gold tube rises round the ally with motes, and the ally hops.
func buff(am: Node3D, tm: Node3D) -> void:
	var a := actor(am)
	var t := actor(tm)
	var c := tm.global_position
	var bnd := fx(band(0.38, 0.13), "#FFD45A")
	var motes := []
	for j in 12:
		motes.append(fx(ico(0.055, 0), "#FFF3B8" if j % 2 else "#FFD45A"))
	await run(0.8, func(s: float) -> void:
		a.move(UP * 0.08 * bump(seg(s, 0, 0.24)))
		var u := seg(s, 0.12, 0.5)
		if u > 0.0 and u < 1.0:
			bnd.show(c + UP * (0.02 + 0.85 * smooth(u)), Vector3(1.0 - 0.3 * u, 1.0 - 0.3 * u, 1.0), Basis.IDENTITY, 1.0 - u * u * u)
		else:
			bnd.hide()
		t.move(UP * 0.1 * bump(seg(s, 0.3, 0.55)))
		for j in 12:
			var v := seg(s, 0.2 + 0.02 * j, 0.55 + 0.02 * j)
			if v > 0.0 and v < 1.0:
				(motes[j] as Fx).show(c + dir_at(j * 30.0) * 0.3 + UP * (0.2 + 0.8 * v), 1.0, Basis.IDENTITY, 1.0 - v)
			else:
				(motes[j] as Fx).hide())


## A summon (B, drops in): the caster charges, the summon falls from high onto its lit cell and bounces, with dust.
func summon(am: Node3D, wm: Node3D) -> void:
	var a := actor(am)
	var w := actor(wm)
	var a0 := am.global_position
	var c := wm.global_position
	var rg := fx(ring(1.0, 0.06), "#B07CFF")
	var plate := fx(hex_plate(), "#C9A6FF")
	var puffs := dust(10)
	await run(0.8, func(s: float) -> void:
		charge(a, s, rg, a0)
		var u := seg(s, 0.12, 0.34)
		if s < 0.12:
			w.scale = 0.0
		elif s < 0.34:
			w.move(UP * 1.4 * (1.0 - inn(u)))
		else:
			w.move(UP * 0.12 * bump(seg(s, 0.34, 0.46)))
		puff(puffs, s, 0.34, c + UP * 0.02, 0.35, 0.45, 0.06, 0.08)
		if s > 0.05 and s < 0.45:
			plate.show(c + UP * 0.012, 1.0, Basis.IDENTITY, 0.8 * bump(seg(s, 0.05, 0.45)))
		else:
			plate.hide())


## Breath Weapon (cone v2 B, together): the breather leans in, fourteen puffs roll out across ±30°, and each cell lights as the
## first puffs reach it. cells: the line's cell points; hit: the minis that take damage (each recoils as the puffs reach it).
func cone(am: Node3D, toward: Vector3, cells: Array, hit: Array) -> void:
	var a := actor(am)
	var a0 := am.global_position
	var d := flat(toward)
	var puffs := []
	var pm := ico(1.0)
	for j in 14:
		puffs.append(fx(pm, "#FF9A3C" if j % 3 else "#FFD27A"))
	var plates := []
	var pl := hex_plate()
	for c: Vector3 in cells:
		plates.append([fx(pl, "#FF9A3C"), c, clampf(((c - a0) * Vector3(1, 0, 1)).length() - 0.45, 0.0, 2.6) / 2.6])
	var hit_actors := []
	for m: Node3D in hit:
		hit_actors.append([actor(m), clampf(((m.global_position - a0) * Vector3(1, 0, 1)).length() - 0.45, 0.0, 2.6) / 2.6])
	await run(1.0, func(s: float) -> void:
		var k := out(seg(s, 0, 0.1)) if s < 0.45 else 1.0 - smooth(seg(s, 0.45, 0.6))
		a.lean(8.0 * k, d)
		a.move(UP * 0.06 * k)
		for j in 14:
			var u := seg(s, 0.06 + 0.025 * j, 0.06 + 0.025 * j + 0.32)
			if u > 0.0 and u < 1.0:
				var ang := ((j * 37) % 11 - 5) * 5.5
				var dist := 0.45 + 2.6 * out(u)
				(puffs[j] as Fx).show(a0 + d.rotated(UP, deg_to_rad(ang)) * dist + UP * (0.55 - 0.25 * u), 0.08 + 0.22 * u, Basis.IDENTITY, 0.9 * (1.0 - u * u))
			else:
				(puffs[j] as Fx).hide()
		for p: Array in plates:
			var on: float = 0.06 + 0.32 * (1.0 - sqrt(1.0 - p[2]))
			var w := seg(s, on, on + 0.5)
			if w > 0.0 and w < 1.0:
				(p[0] as Fx).show(p[1] + UP * 0.012, 1.0, Basis.IDENTITY, 0.85 * out(seg(s, on, on + 0.06)) * (1.0 - seg(s, on + 0.3, on + 0.5)))
			else:
				(p[0] as Fx).hide()
		for h: Array in hit_actors:
			recoil(h[0], s, 0.06 + 0.32 * (1.0 - sqrt(1.0 - h[1])), d, 14.0))
