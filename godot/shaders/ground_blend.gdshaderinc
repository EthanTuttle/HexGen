// The ground colour fade shared by the base slabs (ground.gdshader) and the hills' grass (hill_ground.gdshader).
// Needs: uniform sampler2D terrain_map, uniform float blend_width.
const float R = 4.5;
const float A = 3.8971143;  // R * sqrt(3) / 2
const ivec2 NB[6] = ivec2[](ivec2(1, 0), ivec2(1, -1), ivec2(0, -1), ivec2(-1, 0), ivec2(-1, 1), ivec2(0, 1));

vec4 tile(ivec2 t) {
	return texelFetch(terrain_map, t + ivec2(32), 0);
}

vec3 to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

// The faded ground colour (linear) at a world position.
vec3 ground_colour(vec3 wp) {
	vec2 p = vec2(wp.x, -wp.z);  // plan coordinates, as in the art scripts
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
	return to_linear(sum / total);
}
