// The Fey Gate's wisps (art/handoff/feywild_kit.md -> Wisps; fey_lands.gate_wisps' paths): flat round cards with a hard edge, spiralling in to the portal, each with three
// smaller behind as its trail. CUSTOM0: start angle, start radius, start height, seconds a trip. CUSTOM1: phase, how far behind its head, size at the start, 0. PLACEHOLDER numbers.
shader_type spatial;
render_mode blend_add, depth_draw_never, cull_disabled, unshaded, shadows_disabled;

uniform vec3 colour : source_color = vec3(0.886, 0.831, 1.0);   // #E2D4FF

varying float fade;

void vertex() {
	float f = max(0.0, fract(TIME / CUSTOM0.w + CUSTOM1.x) - CUSTOM1.y);
	float r = CUSTOM0.y * pow(1.0 - f, 1.3);
	float a = CUSTOM0.x + 1.75 * f;
	vec3 at = vec3(r * cos(a) * (1.0 - 0.25 * f), mix(CUSTOM0.z, 1.2, f), -r * sin(a));
	vec4 view = MODELVIEW_MATRIX * vec4(at, 1.0);
	view.xy += (UV - 0.5) * CUSTOM1.z * (1.0 - 0.55 * f);
	fade = clamp((1.0 - f) / 0.15, 0.0, 1.0);
	VERTEX = view.xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
	POSITION = PROJECTION_MATRIX * view;
}

void fragment() {
	float d = length(UV - 0.5) * 2.0;
	float w = fwidth(d);
	ALBEDO = colour;
	ALPHA = clamp((1.0 - d) / max(w, 0.001), 0.0, 1.0) * fade;
}
