class_name RiseDust
extends RefCounted
## The dust while a raised region comes up (DOCS: design/06 -> Raised hills regions; PLACEHOLDER look): one particle
## node along all its new cliffs, no lights and no shadows, covering the trench where the ground stops short.


## points: plan points along the outer edges.
static func start(parent: Node3D, points: PackedVector2Array, seconds: float) -> CPUParticles3D:
	var fx := CPUParticles3D.new()
	fx.name = "rise_dust"
	var at := PackedVector3Array()
	for p in points:
		at.append(Hex.to3(p, 0.1))
	fx.emission_shape = CPUParticles3D.EMISSION_SHAPE_POINTS
	fx.emission_points = at
	fx.amount = mini(points.size() * 10, 240)
	fx.lifetime = 1.6
	fx.direction = Vector3.UP
	fx.spread = 70.0
	fx.initial_velocity_min = 0.6
	fx.initial_velocity_max = 2.2
	fx.gravity = Vector3(0, -0.35, 0)
	fx.scale_amount_min = 0.8
	fx.scale_amount_max = 2.4
	var mesh := SphereMesh.new()
	mesh.radius = 0.35
	mesh.height = 0.7
	mesh.radial_segments = 6
	mesh.rings = 3
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.vertex_color_use_as_albedo = true
	mat.albedo_color = Color(0.74, 0.68, 0.58, 0.55)
	mesh.material = mat
	fx.mesh = mesh
	var fade := Gradient.new()
	fade.set_color(0, Color(1, 1, 1, 1))
	fade.set_color(1, Color(1, 1, 1, 0))
	fx.color_ramp = fade
	fx.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(fx)
	fx.emitting = true
	var stop := fx.get_tree().create_timer(seconds)
	stop.timeout.connect(func(): if is_instance_valid(fx): fx.emitting = false)
	fx.get_tree().create_timer(seconds + fx.lifetime + 0.2).timeout.connect(func(): if is_instance_valid(fx): fx.queue_free())
	return fx
