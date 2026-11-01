class_name ForestFx
extends RefCounted
## The forest kit's engine effects (art/handoff/forest_kit.md -> Engine effects; looks: design/07 -> Region variant
## looks and Landmark tiles). All PLACEHOLDER looks, kept light for the phone: each effect is one node (one draw
## call) per tile, with no lights and no shadows.
##   fey wood, Fey Court       drifting motes of light (GPU particles)
##   heartwood, Tree of Life   light shafts (additive cones) and floating seeds (GPU particles)
##   Hidden Shrine             a shaft of light on its clearing

const MOTES := 10                 # PLACEHOLDER counts and sizes
const SEEDS := 8
const SHAFT_HEIGHT := 7.0

static var _mote_mat: StandardMaterial3D
static var _seed_mat: StandardMaterial3D
static var _shaft_mat: ShaderMaterial
static var _mote_process: ParticleProcessMaterial
static var _seed_process: ParticleProcessMaterial


## The effects node for one tile, or null.
static func for_tile(name: String, at: Vector2, t: Vector2i, turn: int) -> Node3D:
	var out: Node3D = null
	match name:
		"fey_wood", "feycourt":
			out = _holder(at)
			out.add_child(_particles(_motes(), MOTES, 6.0, Vector3(3.2, 0.7, 3.2), Vector3(0, 1.0, 0)))
		"heartwood", "treeoflife":
			out = _holder(at)
			out.add_child(_particles(_seeds(), SEEDS, 9.0, Vector3(3.0, 1.2, 3.0), Vector3(0, 1.6, 0)))
			# Shafts fall between the crowns, set from the tile's hash so they stay put.
			var n := 2 if name == "treeoflife" else 1
			for k in n:
				var a := TAU * GroundCover.hash01(t.x, t.y, 20 + k)
				var r := 1.4 + 1.4 * GroundCover.hash01(t.x, t.y, 22 + k) if name == "heartwood" else 3.2
				out.add_child(_shaft(Vector2.from_angle(a) * r, 0.45, 0.9))
		"hiddenshrine":
			# The shrine stands a little back from the tile's middle, away from its entrance (variants.hidden_shrine:
			# centre (0, 0.25) built facing -Y, turned to face edge 0), then turned with the centre piece.
			out = _holder(at)
			out.add_child(_shaft(Vector2(-0.25, 0).rotated(deg_to_rad(60.0 * turn)), 0.55, 1.0))
	return out


## Fades the light shafts out at night (0 day, 1 night).
static func set_night(night: float) -> void:
	if _shaft_mat:
		_shaft_mat.set_shader_parameter("strength", 1.0 - night)


static func _holder(at: Vector2) -> Node3D:
	var n := Node3D.new()
	n.name = "forest_fx"
	n.position = Hex.to3(at)
	return n


static func _particles(mat: Array, amount: int, life: float, box: Vector3, centre: Vector3) -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.amount = amount
	p.lifetime = life
	p.preprocess = life
	p.randomness = 0.5
	p.process_material = mat[0]
	p.draw_pass_1 = mat[1]
	p.position = centre
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	p.visibility_aabb = AABB(-box - Vector3(1, 1, 1), (box + Vector3(1, 1, 1)) * 2.0)
	(mat[0] as ParticleProcessMaterial).emission_box_extents = box
	return p


## Fey motes: small lilac-white sparks that drift and bob, fading in and out.
static func _motes() -> Array:
	if _mote_mat == null:
		_mote_mat = _spark_material(Color(0.86, 0.78, 1.0))
		_mote_process = _drift(Vector3(0, 0.08, 0), 0.12, Color(0.86, 0.78, 1.0))
	return [_mote_process, _quad(0.09, _mote_mat)]


## Heartwood seeds: pale fluff floating slowly down and sideways.
static func _seeds() -> Array:
	if _seed_mat == null:
		_seed_mat = _spark_material(Color(1.0, 0.97, 0.86))
		_seed_mat.blend_mode = BaseMaterial3D.BLEND_MODE_MIX
		_seed_process = _drift(Vector3(0.05, -0.06, 0.03), 0.1, Color(1.0, 0.97, 0.86))
	return [_seed_process, _quad(0.07, _seed_mat)]


static func _spark_material(col: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.albedo_color = col
	return m


static func _drift(gravity: Vector3, speed: float, col: Color) -> ParticleProcessMaterial:
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.direction = Vector3(0, 1, 0)
	pm.spread = 180.0
	pm.initial_velocity_min = speed * 0.5
	pm.initial_velocity_max = speed
	pm.gravity = gravity
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 0.4
	pm.turbulence_noise_speed_random = 0.3
	pm.turbulence_influence_min = 0.05
	pm.turbulence_influence_max = 0.12
	var ramp := Gradient.new()   # fade in, hold, fade out
	ramp.offsets = PackedFloat32Array([0.0, 0.2, 0.8, 1.0])
	ramp.colors = PackedColorArray([Color(col, 0), col, col, Color(col, 0)])
	var tex := GradientTexture1D.new()
	tex.gradient = ramp
	pm.color_ramp = tex
	return pm


static func _quad(size: float, mat: Material) -> QuadMesh:
	var q := QuadMesh.new()
	q.size = Vector2(size, size)
	q.material = mat
	return q


## A soft shaft of light: an open cone, brightest low down, fading to nothing at its top and edges; leaning
## a little like low sun through the canopy.
static func _shaft(at: Vector2, r0: float, r1: float) -> MeshInstance3D:
	if _shaft_mat == null:
		_shaft_mat = ShaderMaterial.new()
		_shaft_mat.shader = load("res://shaders/light_shaft.gdshader")
	var c := CylinderMesh.new()
	c.bottom_radius = r0
	c.top_radius = r1
	c.height = SHAFT_HEIGHT
	c.radial_segments = 10
	c.rings = 1
	c.cap_top = false
	c.cap_bottom = false
	var mi := MeshInstance3D.new()
	mi.name = "light_shaft"
	mi.mesh = c
	mi.material_override = _shaft_mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.rotation = Vector3(deg_to_rad(14), deg_to_rad(35), 0)
	mi.position = Hex.to3(at, SHAFT_HEIGHT * 0.5 * cos(deg_to_rad(14)) - 0.1)
	return mi
