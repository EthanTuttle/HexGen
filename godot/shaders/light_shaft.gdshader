// A soft shaft of light through the canopy (heartwood, the Tree of Life, the Hidden Shrine; an engine effect,
// art/handoff/forest_kit.md). PLACEHOLDER look: a warm additive glow, strongest near the ground, fading out at
// the top and toward the cone's silhouette so it has no hard edge; it breathes slowly. Faded out at night.
shader_type spatial;
render_mode blend_add, depth_draw_never, cull_back, shadows_disabled, unshaded;

uniform vec4 tint : source_color = vec4(1.0, 0.93, 0.7, 1.0);
uniform float strength = 1.0;
uniform float peak = 0.16;

void fragment() {
	float up = UV.y;   // 0 at the top, 1 at the bottom
	float along = smoothstep(0.0, 0.7, up) * smoothstep(1.0, 0.85, up);
	float edge = pow(clamp(abs(dot(NORMAL, VIEW)), 0.0, 1.0), 1.5);
	float breathe = 0.85 + 0.15 * sin(TIME * 0.6 + NODE_POSITION_WORLD.x);
	ALBEDO = tint.rgb;
	ALPHA = peak * along * edge * breathe * strength;
}
