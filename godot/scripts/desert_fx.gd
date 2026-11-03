class_name DesertFx
extends RefCounted
## The desert kit's engine effects (art/handoff/desert_kit.md; looks: design/07 -> Region variant looks): heat shimmer over
## open oasis and badlands ground, and glints on the pool and well with a faint glow at night. All PLACEHOLDER looks, kept
## light for the phone: one node (one draw call) each, no lights, no shadows. Fire and smoke are FarmFx's, as elsewhere.

const SHIMMER_SIZE := Vector2(8.6, 2.6)

static var _shimmer_mat: ShaderMaterial
static var _glow_mat: ShaderMaterial
static var _spark_mat: StandardMaterial3D
static var _spark_process: ParticleProcessMaterial
static var _shimmer_mesh: QuadMesh


## Heat waves rising from the effect point (`at`, in the piece's frame).
static func shimmer(at: Vector3) -> MeshInstance3D:
	if _shimmer_mesh == null:
		_shimmer_mat = ShaderMaterial.new()
		_shimmer_mat.shader = load("res://shaders/heat_shimmer.gdshader")
		_shimmer_mesh = QuadMesh.new()
		_shimmer_mesh.size = SHIMMER_SIZE
		_shimmer_mesh.material = _shimmer_mat
	var mi := MeshInstance3D.new()
	mi.name = "shimmer"
	mi.mesh = _shimmer_mesh
	mi.position = at + Vector3(0, SHIMMER_SIZE.y * 0.5 - 0.25, 0)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.custom_aabb = AABB(Vector3(-5, -2, -5), Vector3(10, 4, 10))   # it turns to the camera, in the shader
	return mi


## Blue-white glints over water of this radius, with a faint glow at night (set_night).
static func glint(at: Vector3, radius: float) -> Node3D:
	if _glow_mat == null:
		_glow_mat = ShaderMaterial.new()
		_glow_mat.shader = load("res://shaders/oasis_glow.gdshader")
		_spark_mat = StandardMaterial3D.new()
		_spark_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_spark_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		_spark_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		_spark_mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
		_spark_mat.vertex_color_use_as_albedo = true
		_spark_process = ParticleProcessMaterial.new()
		_spark_process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_RING
		_spark_process.emission_ring_axis = Vector3.UP
		_spark_process.emission_ring_height = 0.0
		_spark_process.gravity = Vector3.ZERO
		_spark_process.scale_min = 0.6
		_spark_process.scale_max = 1.3
		var col := Color(0.86, 0.98, 1.0)
		var ramp := Gradient.new()   # a quick flash, then gone
		ramp.offsets = PackedFloat32Array([0.0, 0.35, 0.6, 1.0])
		ramp.colors = PackedColorArray([Color(col, 0), col, Color(col, 0), Color(col, 0)])
		var tex := GradientTexture1D.new()
		tex.gradient = ramp
		_spark_process.color_ramp = tex
	var node := Node3D.new()
	node.name = "glint"
	node.position = at
	var disc := MeshInstance3D.new()
	disc.name = "glow"
	var plane := PlaneMesh.new()
	plane.size = Vector2.ONE * radius * 2.4
	disc.mesh = plane
	disc.material_override = _glow_mat
	disc.position.y = 0.02
	disc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	node.add_child(disc)
	var p := GPUParticles3D.new()
	p.name = "sparks"
	p.amount = maxi(4, roundi(radius * 9.0))
	p.lifetime = 1.6
	p.preprocess = 1.6
	p.randomness = 0.6
	var pm := _spark_process.duplicate() as ParticleProcessMaterial   # each its own radius
	pm.emission_ring_radius = radius
	pm.emission_ring_inner_radius = 0.0
	p.process_material = pm
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE * 0.1
	quad.material = _spark_mat
	p.draw_pass_1 = quad
	p.position.y = 0.05
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	p.visibility_aabb = AABB(Vector3(-radius, -0.5, -radius), Vector3(radius * 2.0, 1.0, radius * 2.0))
	node.add_child(p)
	return node


## 0 by day, 1 at night: heat waves fade out, and the water's glow fades in.
static func set_night(night: float) -> void:
	if _shimmer_mat:
		_shimmer_mat.set_shader_parameter("strength", 1.0 - night)
	if _glow_mat:
		_glow_mat.set_shader_parameter("strength", night)
