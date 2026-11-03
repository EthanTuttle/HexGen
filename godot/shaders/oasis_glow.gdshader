// The faint glow on the pool and the well at night (design/07 -> Oasis): a soft round wash of blue-white light on the water.
// Nothing by day. PLACEHOLDER strength.
shader_type spatial;
render_mode blend_add, depth_draw_never, unshaded, shadows_disabled;

uniform vec4 tint : source_color = vec4(0.62, 0.95, 0.98, 1.0);
uniform float strength = 0.0;

void fragment() {
	float r = length(UV - vec2(0.5)) * 2.0;
	ALBEDO = tint.rgb;
	ALPHA = 0.32 * strength * smoothstep(1.0, 0.25, r);
}
