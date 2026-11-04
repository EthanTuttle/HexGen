// What falls on a Feywild tile (art/handoff/feywild_kit.md): flat cards with hard edges, looping down, swaying and turning. Snow is round; leaves and petals are diamonds that
// narrow as they tumble. CUSTOM0: x, y, phase, falls a second. CUSTOM1: size, sway, turn speed, 1 for a diamond. PLACEHOLDER numbers.
shader_type spatial;
render_mode depth_draw_opaque, cull_disabled, unshaded, shadows_disabled;

const float HEIGHT = 3.2;

varying float diamond;

void vertex() {
	float t = TIME * CUSTOM0.w + CUSTOM0.z;
	float f = fract(t);
	float phase = CUSTOM0.z * 40.0;
	vec3 at = vec3(CUSTOM0.x + CUSTOM1.y * sin(t * 6.0 + phase), HEIGHT * (1.0 - f) + 0.02, -CUSTOM0.y - CUSTOM1.y * cos(t * 4.0 + phase));
	vec4 view = MODELVIEW_MATRIX * vec4(at, 1.0);
	float narrow = CUSTOM1.w > 0.5 ? 0.35 + 0.65 * abs(cos(TIME * CUSTOM1.z + phase)) : 1.0;
	float spin = CUSTOM1.w > 0.5 ? TIME * CUSTOM1.z * 0.5 + phase : 0.0;
	vec2 corner = (UV - 0.5) * CUSTOM1.x * vec2(narrow, 1.0);
	view.xy += vec2(corner.x * cos(spin) - corner.y * sin(spin), corner.x * sin(spin) + corner.y * cos(spin));
	diamond = CUSTOM1.w;
	VERTEX = view.xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
	POSITION = PROJECTION_MATRIX * view;
}

void fragment() {
	vec2 p = abs(UV - 0.5) * 2.0;
	float d = diamond > 0.5 ? p.x + p.y : length(p);
	if (d > 1.0) {
		discard;
	}
	ALBEDO = COLOR.rgb;
}
