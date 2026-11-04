// A fight map's lava (art/handoff/combat_hills_kit.md -> Moving lava), in flat colours with crisp edges. style 0 is the shared `lava` of craters, streaks and
// vents, one flat colour; 1 to 4 are the flow's looks on trial, from UV's metres. All PLACEHOLDER: Ethan picks one, the rest go.
shader_type spatial;
render_mode cull_back, unshaded;

uniform int style = 1;
uniform float flow_end = 18.6;   // metres along where this map's fall ends
uniform vec3 deep : source_color = vec3(0.757, 0.204, 0.063);   // #C1340F
uniform vec3 mid : source_color = vec3(0.957, 0.475, 0.165);    // #F4792A, the tiles' lava
uniform vec3 hot : source_color = vec3(1.0, 0.769, 0.302);      // #FFC44D
uniform vec3 crust : source_color = vec3(0.2, 0.17, 0.19);
uniform vec3 crust2 : source_color = vec3(0.3, 0.2, 0.18);

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

// A slow triangle wave, for shapes with straight sides.
float wave(float x) {
	return abs(fract(x) - 0.5) * 2.0;
}

// 1 past edge, with a one-pixel step so a moving edge stays crisp without shimmering.
float past(float value, float edge) {
	float w = fwidth(value);
	return clamp((value - edge) / max(w, 0.0001) + 0.5, 0.0, 1.0);
}

void vertex() {
	float along = 1.0 - UV.y;
	if (style == 4) {
		float lobe = wave((along - TIME * 0.22) / 1.7);
		VERTEX.y += 0.07 * lobe * (1.0 - pow(abs(UV.x) / 0.41, 2.0));
	}
}

vec3 bands(float across, float along) {
	float v = along * 0.95 - TIME * 0.16 - abs(across) * 0.8 + 0.07 * wave(along * 1.3 + across);
	float f = fract(v);
	vec3 c = mix(hot, mid, past(f, 0.5));
	return mix(c, deep, past(f, 0.8));
}

// Triangles laid out in the flow's own metres, as the mesh's own are too few and big on the pools. Each is one flat colour.
vec3 faceted(float across, float along) {
	vec2 p = vec2(across / 0.3, along / 0.36);
	vec2 cell = floor(p);
	vec2 in_cell = p - cell;
	float half_cell = step(in_cell.x + in_cell.y, 1.0);
	float seed = hash(cell + half_cell * 7.0);
	float s = sin((cell.y + half_cell * 0.5) * 0.36 * 2.3 - TIME * 1.1 + seed * 2.4);
	if (s > 0.4) return hot;
	if (s > -0.3) return mid;
	return deep;
}

vec3 plates(float across, float along) {
	vec2 p = vec2(across * 3.1, (along - TIME * 0.09) * 1.7);
	vec2 cell = floor(p);
	float f1 = 8.0;
	float f2 = 8.0;
	vec2 id = cell;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 c = cell + vec2(float(x), float(y));
			vec2 at = c + vec2(hash(c), hash(c + 17.0)) * 0.8 + 0.1;
			float d = distance(p, at);
			if (d < f1) {
				f2 = f1;
				f1 = d;
				id = c;
			} else if (d < f2) {
				f2 = d;
			}
		}
	}
	float gap = f2 - f1;
	float kind = hash(id + 3.0);
	if (kind > 0.74) return hot;   // open lava
	vec3 plate = kind > 0.37 ? crust : crust2;
	vec3 c = mix(hot, mid, past(gap, 0.055));
	return mix(c, plate, past(gap, 0.12));
}

vec3 creeping(float across, float along) {
	float rim = 0.39 - 0.03 - 0.11 * wave((along - TIME * 0.15) / 0.9 + (across > 0.0 ? 0.31 : 0.0));
	return mix(hot, deep, past(abs(across), rim));
}

void fragment() {
	float along = 1.0 - UV.y;
	vec3 c = hot;
	if (style == 1) {
		c = bands(UV.x, along);
	} else if (style == 2) {
		c = faceted(UV.x, along);
	} else if (style == 3) {
		c = plates(UV.x, along);
	} else if (style == 4) {
		float front = flow_end - 0.1 - 0.4 * wave(TIME * 0.05);   // the fall's foot slowly creeps out and back
		if (along > front) {
			discard;
		}
		c = creeping(UV.x, along);
		vec3 face = normalize(cross(dFdx(VERTEX), dFdy(VERTEX)));
		c *= 0.94 + 0.1 * abs(face.y);   // the swelling's facets, in view space
	}
	ALBEDO = c;
}
