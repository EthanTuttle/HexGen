// The Fey Gate's portal (art/handoff/feywild_kit.md -> Portal): flat nested bands, each showing from the side it faces, one flat colour and alpha in COLOR.
// A slow pulse of brightness, dimmer at night so it doesn't take over the night map. PLACEHOLDER numbers.
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_back, unshaded, shadows_disabled;

uniform float night = 0.0;

void fragment() {
	ALBEDO = COLOR.rgb * (1.0 + 0.1 * sin(TAU * TIME / 5.0)) * mix(1.0, 0.82, night);
	ALPHA = COLOR.a;
}
