// Ground colour of the map tiles' base slabs (look test 1: hex edge blending).
// Works in world space: finds the tile under the pixel, then mixes in each placed neighbour's ground
// colour with a weight that falls from 1 at the shared edge to 0 at blend_width away from it
// (the own tile always weighs 1). At an edge both tiles weigh 1, so they meet at the average.
// Distances are to each neighbour's whole hexagon, so the blend stays continuous at corners where
// three terrains meet (ground_cover.py's edge-by-edge fade jumps there, which shows in colour).
shader_type spatial;

uniform sampler2D terrain_map : filter_nearest;  // texel (q + 32, r + 32): sRGB ground colour, alpha 1 = placed
uniform float blend_width = 1.6;

const float R = 4.5;
const float A = 3.8971143;  // R * sqrt(3) / 2
const ivec2 NB[6] = ivec2[](ivec2(1, 0), ivec2(1, -1), ivec2(0, -1), ivec2(-1, 0), ivec2(-1, 1), ivec2(0, 1));

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

vec4 tile(ivec2 t) {
	return texelFetch(terrain_map, t + ivec2(32), 0);
}

vec3 to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

void fragment() {
	vec2 p = vec2(world_pos.x, -world_pos.z);  // plan coordinates, as in the art scripts
	float r = -p.y / (1.5 * R);
	float q = p.x / (2.0 * A) - r / 2.0;
	float s = -q - r;
	vec3 rd = round(vec3(q, r, s));
	vec3 d = abs(rd - vec3(q, r, s));
	if (d.x > d.y && d.x > d.z) {
		rd.x = -rd.y - rd.z;
	} else if (d.y > d.z) {
		rd.y = -rd.x - rd.z;
	}
	ivec2 t = ivec2(rd.xy);
	vec2 local = p - vec2(2.0 * A * (rd.x + rd.y / 2.0), -1.5 * R * rd.y);
	vec3 sum = tile(t).rgb;
	float total = 1.0;
	for (int i = 0; i < 6; i++) {
		vec4 o = tile(t + NB[i]);
		if (o.a < 0.5) {
			continue;  // the map's outer edge keeps its own colour
		}
		float a = radians(60.0 * float(i));
		vec2 rel = local - 2.0 * A * vec2(cos(a), sin(a));  // relative to the neighbour's centre
		float d = -1e9;
		for (int k = 0; k < 6; k++) {
			float b = radians(60.0 * float(k));
			d = max(d, dot(rel, vec2(cos(b), sin(b))));
		}
		float w = clamp(1.0 - (d - A) / blend_width, 0.0, 1.0);
		sum += w * o.rgb;
		total += w;
	}
	vec3 c = sum / total;
	ALBEDO = to_linear(c);
	ROUGHNESS = 0.9;
}
