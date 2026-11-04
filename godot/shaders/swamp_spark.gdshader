// Wisps, glows and bubbles (SwampFx). PLACEHOLDER look: soft round cards that face the camera, one mesh a tile. Each vertex holds its
// card's middle; UV says which corner, UV2 its size and phase. A wisp bobs and pulses; a bubble rises and fades.
shader_type spatial;
render_mode blend_add, depth_draw_never, cull_disabled, shadows_disabled, unshaded;

uniform bool rising = false;
uniform float strength = 1.0;

varying float fade;

void vertex() {
	float t = TIME + UV2.y;
	vec3 at = VERTEX;
	fade = 1.0;
	if (rising) {
		float k = fract(t * 0.45);
		at.y += k * 0.3;
		fade = sin(k * PI);
	} else {
		at.y += 0.06 * sin(t * 1.3);
		at.x += 0.04 * sin(t * 0.9);
		fade = 0.75 + 0.25 * sin(t * 2.1);
	}
	vec4 view = MODELVIEW_MATRIX * vec4(at, 1.0);
	view.xy += (UV - 0.5) * UV2.x;
	VERTEX = view.xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
	POSITION = PROJECTION_MATRIX * view;
}

void fragment() {
	float d = length(UV - 0.5) * 2.0;
	ALBEDO = COLOR.rgb;
	ALPHA = pow(max(0.0, 1.0 - d), 2.0) * fade * strength;
}
