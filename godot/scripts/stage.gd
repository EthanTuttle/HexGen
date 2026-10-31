class_name Stage
extends RefCounted
## The backdrop, sun and day clock shared by the look tests and the game.


static func create(parent: Node) -> TimeOfDay:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.reflected_light_source = Environment.REFLECTION_SOURCE_BG
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	# Contact shade where pieces meet the ground, so props don't look pasted on (engine choice, tuned by eye).
	env.ssao_enabled = true
	env.ssao_radius = 0.6
	env.ssao_intensity = 1.6
	env.ssao_light_affect = 0.15
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
	_test_settings(sun)
	var clock := TimeOfDay.new()
	clock.environment = env
	clock.sun = sun
	parent.add_child(clock)
	clock.apply()
	return clock


## Test aids for checking phone settings on the Mac (README -> iOS). `--phone` applies the project's `.mobile`
## shadow settings (they only apply by themselves on a phone; run it with `--rendering-method mobile` too).
## `--shadow-size=N`, `--shadow-filter=N`, `--splits=2|4` and `--shadow-distance=M` try other values.
static func _test_settings(sun: DirectionalLight3D) -> void:
	var size := -1
	var filter := -1
	var key := "rendering/lights_and_shadows/directional_shadow/"
	for a in OS.get_cmdline_user_args():
		if a == "--phone":
			size = ProjectSettings.get_setting(key + "size.mobile", 2048)
			filter = ProjectSettings.get_setting(key + "soft_shadow_filter_quality.mobile", 0)
	for a in OS.get_cmdline_user_args():
		var v := a.split("=")[-1]
		if a.begins_with("--shadow-size="):
			size = int(v)
		elif a.begins_with("--shadow-filter="):
			filter = int(v)
		elif a.begins_with("--splits="):
			sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS if v == "2" \
					else DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
		elif a.begins_with("--shadow-distance="):
			sun.directional_shadow_max_distance = float(v)
	if size > 0:
		RenderingServer.directional_shadow_atlas_set_size(size, ProjectSettings.get_setting(key + "16_bits", true))
	if filter >= 0:
		RenderingServer.directional_soft_shadow_filter_set_quality(filter)
	if size > 0 or filter >= 0:
		print("STAGE shadows: size %d, filter %d, %s, %.0f m" % [size, filter,
				"2 splits" if sun.directional_shadow_mode == DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS else "4 splits",
				sun.directional_shadow_max_distance])
