// A fight map's lava (art/handoff/combat_hills_kit.md -> Moving lava). flow: the moving surface, glow scrolling down UV's metres. Otherwise
// the shared `lava` of craters, streaks and vents, which pulses and has no usable UV. Numbers from render_lava_movie.py, PLACEHOLDER until seen on the phone.
shader_type spatial;
render_mode cull_back;

uniform bool flow = true;
uniform float speed = 0.45;   // metres a second downstream
uniform vec3 deep = vec3(0.62, 0.11, 0.015);   // linear, as in the movie's script
uniform vec3 hot = vec3(1.0, 0.62, 0.12);
uniform sampler2D noise : hint_default_black, repeat_enable, filter_linear_mipmap;

void fragment() {
	float heat;
	if (flow) {
		float along = 1.0 - UV.y;   // glTF flips V
		vec2 at = vec2(UV.x * 0.42, (along - TIME * speed) * 0.62);   // soft and stretched across, which hides the jumps at necks
		float n = texture(noise, at).r * 0.8 + texture(noise, at * 1.9 + vec2(0.37, 0.19)).r * 0.2;
		heat = smoothstep(0.26, 0.72, n);
	} else {
		heat = 0.5 + 0.25 * sin(TAU * TIME / 4.0);
	}
	vec3 c = mix(deep, hot, heat);
	ALBEDO = c * 0.45;
	EMISSION = c * 0.55;
	ROUGHNESS = 0.6;
}
