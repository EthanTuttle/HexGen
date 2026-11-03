// A mini's silhouette where canyon rock hides it (design/07 -> Region variant looks): solid, in one flat colour (Ethan, Nov 3,
// 2026). An overlay on the mini, drawn only behind something (inverted depth test) and only over rock: the canyon's material
// marks the stencil, and a mini's own visible surfaces clear it, so its inner parts never show. PLACEHOLDER colour.
shader_type spatial;
render_mode unshaded, depth_draw_never, depth_test_inverted, cull_back, shadows_disabled;
stencil_mode read, compare_equal, 1;

uniform vec4 tint : source_color = vec4(0.16, 0.1, 0.08, 1.0);
instance uniform float water_y = -100.0;  // a mini wading in a gorge: what's under the water doesn't show

varying float world_y;

void vertex() {
	world_y = (MODEL_MATRIX * vec4(VERTEX, 1.0)).y;
}

void fragment() {
	if (world_y < water_y) {
		discard;
	}
	ALBEDO = tint.rgb;
	ALPHA = tint.a;
}
