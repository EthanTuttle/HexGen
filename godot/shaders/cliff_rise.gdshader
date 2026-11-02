// A cliff piece while its region rises: the same look, cut off below the board's soil so it doesn't stick out beside an
// empty slot (art/handoff/hills_kit.md -> The rise). Only on while rising.
shader_type spatial;

uniform vec3 tint : source_color = vec3(1.0);
uniform float cut = -0.6;

varying float height;

void vertex() {
	height = (MODEL_MATRIX * vec4(VERTEX, 1.0)).y;
}

void fragment() {
	if (height < cut) {
		discard;
	}
	ALBEDO = tint * COLOR.rgb;
	ROUGHNESS = 0.9;
}
