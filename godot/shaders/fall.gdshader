// A rapids waterfall (river kit: it faces away from the sun, and went grey in shade). Unlit, the kit's vertex colours, with
// pale bands running down it. A gorge's foam uses it too, with no bands. PLACEHOLDER: the bands' speed and strength, and how far
// it dims at night.
shader_type spatial;
render_mode unshaded, shadows_disabled;

uniform float night = 0.0;
uniform float bands_on = 0.55;
uniform vec3 foam_colour : source_color = vec3(0.957, 0.98, 0.973);

varying vec3 world_pos;
varying vec3 tint;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	tint = COLOR.rgb;
}

void fragment() {
	vec3 base = pow(tint, vec3(2.2));
	float wobble = sin(world_pos.x * 5.0 + world_pos.z * 3.0) * 0.12;
	float bands = smoothstep(0.55, 0.95, sin((world_pos.y + wobble) * 9.0 + TIME * 6.0));
	ALBEDO = mix(base, foam_colour, bands * bands_on) * mix(1.0, 0.45, night);
}
