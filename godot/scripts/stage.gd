class_name Stage
extends RefCounted
## The backdrop, sun and day clock shared by the look tests and the game.


static func create(parent: Node) -> TimeOfDay:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.reflected_light_source = Environment.REFLECTION_SOURCE_BG
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var we := WorldEnvironment.new()
	we.environment = env
	parent.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.name = "sun"
	sun.shadow_enabled = true
	sun.light_angular_distance = 0.0      # see README: soft (PCSS) shadows gave grain here
	sun.directional_shadow_max_distance = 140.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.shadow_blur = 1.5
	parent.add_child(sun)
	var clock := TimeOfDay.new()
	clock.environment = env
	clock.sun = sun
	parent.add_child(clock)
	clock.apply()
	return clock
