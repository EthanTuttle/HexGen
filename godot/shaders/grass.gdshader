// Ground cover (tufts, flowers, pebbles) that bends away from the walking minis (DOCS: How the party moves ->
// the grass parts). Each vertex is pushed away from the nearest minis by how high it stands above the ground,
// so the tips lean and the roots stay put. Colours come from the vertex colours (Piece, sRGB).
shader_type spatial;
render_mode cull_disabled;

uniform vec3 minis[4];
uniform float radius = 0.75;

vec3 to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 push = vec2(0.0);
	for (int i = 0; i < 4; i++) {
		vec2 d = w.xz - minis[i].xz;
		float l = length(d);
		if (l > 0.001 && l < radius) {
			push += d / l * (1.0 - l / radius);
		}
	}
	float h = clamp(w.y, 0.0, 0.5);
	w.xz += push * h * 1.4;
	w.y -= length(push) * h * 0.45;
	VERTEX = (inverse(MODEL_MATRIX) * vec4(w, 1.0)).xyz;
}

void fragment() {
	ALBEDO = to_linear(COLOR.rgb);
	ROUGHNESS = 0.9;
}
