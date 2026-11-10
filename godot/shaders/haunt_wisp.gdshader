shader_type spatial;
// The Haunted ruins' wisps (art/handoff/ruins_kit.md -> Haunted ruins): the haunt_wisps piece drifts up, fading in at the bottom
// and out at the top, then starts again. Each piece keeps its own phase, from where it stands. PLACEHOLDER rise and speed.
render_mode blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

uniform vec4 colour : source_color = vec4(0.85, 1.0, 0.95, 1.0);
uniform float strength = 0.5;   // emission: 0.5 by day, 2.2 at night
uniform float rise = 0.7;
uniform float speed = 0.12;

varying float fade;

void vertex() {
	vec3 o = NODE_POSITION_WORLD;
	float t = fract(TIME * speed + fract(sin(dot(o.xz, vec2(12.9898, 78.233))) * 43758.5453));
	VERTEX.y += t * rise;
	fade = sin(t * PI);
}

void fragment() {
	ALBEDO = colour.rgb;
	EMISSION = colour.rgb * strength;
	ALPHA = clamp(fade * 1.6, 0.0, 1.0);
}
