class_name FarmFx
extends RefCounted
## The kits' effect points as engine effects (art/handoff/farmland_kit.md, plains_kit.md): fire and smoke on the
## raided farms and the Nomad Camp, crows over the haunted scarecrows and the Abandoned Barn, faint crackling in the
## Thunderbird Nest's charred logs. All PLACEHOLDER looks, kept
## light for the phone: one particle node per kind per piece (its points share it), one mesh for each flock of
## crows, no lights and no shadows.

const CROW_RADIUS := 0.9
const CROW_SPEED := 0.7     # radians a second

static var _process_mats := {}
static var _fire_mesh: QuadMesh
static var _smoke_mesh: SphereMesh
static var _ember_mesh: QuadMesh
static var _crow_mesh: ArrayMesh


## The effects of a piece placed at `at`, turned `turn` steps, or null. They turn with the piece.
static func for_piece(piece: String, at: Vector2, turn: int) -> Node3D:
	var fx: Array = Kit.path_data(piece).get("effects", [])
	if fx.is_empty():
		return null
	var holder := Node3D.new()
	holder.name = "farm_fx"
	holder.position = Hex.to3(at)
	holder.rotation.y = deg_to_rad(60.0 * turn)
	var fires := []
	var smokes := []
	var crackles := []
	for e in fx:
		var p := Vector3(e.at[0], e.at[1], e.at[2])
		match e.kind:
			"fire": fires.append(p)
			"smoke": smokes.append(p)
			"crows": holder.add_child(_crows(p))
			"crackle": crackles.append(p)
	if not fires.is_empty():
		holder.add_child(_particles(piece + "|fire", fires, 6, 0.6, _fire(), Vector3(0, 0.9, 0), 0.25))
	if not smokes.is_empty():
		holder.add_child(_particles(piece + "|smoke", smokes, 4, 2.6, _smoke(), Vector3(0.06, 0.3, 0), 0.12))
	if not crackles.is_empty():
		holder.add_child(_particles(piece + "|crackle", crackles, 4, 0.5, _ember(), Vector3(0, 0.5, 0), 0.35))
	return holder


static func _particles(key: String, points: Array, each: int, life: float, mesh: Mesh, gravity: Vector3, speed: float) -> GPUParticles3D:
	if not _process_mats.has(key):
		var img := Image.create(points.size(), 1, false, Image.FORMAT_RGBF)
		for k in points.size():
			var v: Vector3 = points[k]
			img.set_pixel(k, 0, Color(v.x, v.y, v.z))
		var pm := ParticleProcessMaterial.new()
		pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_POINTS
		pm.emission_point_texture = ImageTexture.create_from_image(img)
		pm.emission_point_count = points.size()
		pm.direction = Vector3.UP
		pm.spread = 25.0
		pm.initial_velocity_min = speed * 0.5
		pm.initial_velocity_max = speed
		pm.gravity = gravity
		pm.scale_min = 0.6
		pm.scale_max = 1.2
		var curve := Curve.new()
		curve.add_point(Vector2(0.0, 0.5))
		curve.add_point(Vector2(1.0, 1.0 if "smoke" in key else 0.1))
		var tex := CurveTexture.new()
		tex.curve = curve
		pm.scale_curve = tex
		_process_mats[key] = pm
	var p := GPUParticles3D.new()
	p.amount = points.size() * each
	p.lifetime = life
	p.preprocess = life
	p.randomness = 0.4
	p.process_material = _process_mats[key]
	p.draw_pass_1 = mesh
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	p.visibility_aabb = AABB(Vector3(-5, -1, -5), Vector3(10, 7, 10))
	return p


## One crater's smoke, at a volcano's shared point (MapBoard keeps one per crater).
static func crater_smoke() -> GPUParticles3D:
	return _particles("crater|smoke", [Vector3.ZERO], 4, 2.6, _smoke(), Vector3(0.06, 0.3, 0), 0.12)


## A town's chimneys on one tile: a thin wisp at each point (village kit -> Materials and effects), one node for them all.
static func town_smoke(points: Array) -> GPUParticles3D:
	var img := Image.create(points.size(), 1, false, Image.FORMAT_RGBF)
	for k in points.size():
		var v: Vector3 = points[k]
		img.set_pixel(k, 0, Color(v.x, v.y, v.z))
	var pm: ParticleProcessMaterial = _particles("town|smoke", [Vector3.ZERO], 1, 2.0, _smoke(), Vector3(0.04, 0.25, 0), 0.08).process_material.duplicate()
	pm.emission_point_texture = ImageTexture.create_from_image(img)
	pm.emission_point_count = points.size()
	pm.scale_min = 0.25
	pm.scale_max = 0.5
	var p := GPUParticles3D.new()
	p.amount = points.size() * 2
	p.lifetime = 2.0
	p.preprocess = 2.0
	p.randomness = 0.4
	p.process_material = pm
	p.draw_pass_1 = _smoke()
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	p.visibility_aabb = AABB(Vector3(-5, -1, -5), Vector3(10, 7, 10))
	return p


## Spray where rapids fall (river kit -> Engine effects). PLACEHOLDER: a little pale smoke, thrown up and falling back.
static func spray(at: Vector3) -> GPUParticles3D:
	var p := _particles("rapids|spray", [Vector3.ZERO], 8, 0.9, _smoke(), Vector3(0, -1.2, 0), 0.7)
	p.position = at
	p.scale = Vector3.ONE * 0.5
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return p


## A low flame: an orange billboard, bright and additive.
static func _fire() -> Mesh:
	if _fire_mesh == null:
		var m := StandardMaterial3D.new()
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
		m.albedo_color = Color(1.0, 0.55, 0.15)
		_fire_mesh = QuadMesh.new()
		_fire_mesh.size = Vector2(0.22, 0.32)
		_fire_mesh.material = m
	return _fire_mesh


## A spark in the charred logs: a tiny orange billboard.
static func _ember() -> Mesh:
	if _ember_mesh == null:
		_ember_mesh = QuadMesh.new()
		_ember_mesh.size = Vector2(0.09, 0.09)
		_ember_mesh.material = _fire().material
	return _ember_mesh


## A puff of smoke: a small low-poly grey ball, see-through.
static func _smoke() -> Mesh:
	if _smoke_mesh == null:
		var m := StandardMaterial3D.new()
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.albedo_color = Color(0.3, 0.29, 0.28, 0.35)
		_smoke_mesh = SphereMesh.new()
		_smoke_mesh.radius = 0.2
		_smoke_mesh.height = 0.4
		_smoke_mesh.radial_segments = 6
		_smoke_mesh.rings = 3
		_smoke_mesh.material = m
	return _smoke_mesh


## Three crows in one mesh, circling the point.
static func _crows(at: Vector3) -> Spinner:
	if _crow_mesh == null:
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		for k in 3:
			var a := TAU * k / 3.0 + 0.3 * k
			var c := Vector3(cos(a), 0.15 * k, sin(a)) * Vector3(CROW_RADIUS, 1.0, CROW_RADIUS)
			var along := Vector3(-sin(a), 0, cos(a)) * 0.12    # the way it flies
			var out := Vector3(cos(a), 0.35, sin(a)) * 0.2     # a raised wing
			var other := Vector3(-cos(a), 0.35, -sin(a)) * 0.2
			for tri in [[c + along, c - along, c + out], [c + along, c - along, c + other]]:
				for v in tri:
					st.add_vertex(v)
		var m := StandardMaterial3D.new()
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		m.albedo_color = Color("#1E1C1A")
		st.set_material(m)
		_crow_mesh = st.commit()
	var s := Spinner.new()
	s.name = "crows"
	s.speed = CROW_SPEED
	s.position = at
	var mi := MeshInstance3D.new()
	mi.mesh = _crow_mesh
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	s.add_child(mi)
	return s
