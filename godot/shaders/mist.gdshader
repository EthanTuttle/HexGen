// The bog's low mist (an engine effect; the art leaves it to us). PLACEHOLDER look: soft drifting
// banks of pale haze in a few flat layers just above the ground, fading out toward the tile's edge.
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

uniform vec4 tint : source_color = vec4(0.93, 0.95, 0.92, 1.0);
uniform float strength = 0.2;
uniform float layer = 0.0;

varying vec3 world;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}

void vertex() {
	world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = world.xz * 0.33 + vec2(TIME * 0.05, TIME * 0.02) * (1.0 + layer);
	float n = noise(p) * 0.6 + noise(p * 2.3 + 7.0 + layer) * 0.4;
	float edge = 1.0 - smoothstep(0.55, 1.0, length(UV - 0.5) * 2.0);
	ALBEDO = tint.rgb;
	ALPHA = clamp((n - 0.35) * 1.6, 0.0, 1.0) * edge * strength;
}
