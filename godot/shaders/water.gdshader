// Water, ported from art/scripts/render_animation.py (water_material). Per vertex the mesh carries
// UV.x = depth (distance to the nearest shore) and UV2 = flow (world X, Z; metres per second).
// - ripples flow along rivers: a two-phase flow-map scroll, cross-faded so the restart never shows
// - sparkle: small random cells drifting with the flow, about 1 in 3 can glint, each on its own clock
// - a foam rim at the shore that breathes and frays with the ripples
// - darker water away from the shore
shader_type spatial;

uniform vec3 shallow = vec3(0.36, 0.70, 0.86);  // linear colours, as in the Blender nodes
uniform vec3 deep = vec3(0.13, 0.42, 0.66);
uniform vec3 foam_colour = vec3(0.94, 0.97, 1.0);
uniform float period = 2.0;
uniform float bump_strength = 2.0;  // Blender: 0.7; raised by eye, its Bump node reads stronger than this port
uniform float bump_distance = 0.08;
uniform float sparkle_strength = 2.5;

varying vec3 world_pos;
varying float depth;
varying vec2 flow;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	depth = UV.x;
	flow = UV2;
}

// --- Noise (stand-ins for Blender's Noise, Voronoi and White Noise textures) ---

vec3 hash33(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.xxy + p.yxx) * p.zyx);
}

float gradient_noise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	vec3 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
	float n = 0.0;
	float v[8];
	for (int k = 0; k < 8; k++) {
		vec3 o = vec3(float(k & 1), float((k >> 1) & 1), float((k >> 2) & 1));
		vec3 g = hash33(i + o) * 2.0 - 1.0;
		v[k] = dot(g, f - o);
	}
	return mix(mix(mix(v[0], v[1], u.x), mix(v[2], v[3], u.x), u.y),
			mix(mix(v[4], v[5], u.x), mix(v[6], v[7], u.x), u.y), u.z);
}

// fBm in [0, 1] around 0.5, like the Noise texture's Fac (detail = extra octaves, roughness 0.5).
float noise_fac(vec3 p, int detail) {
	float sum = 0.0, amp = 1.0, total = 0.0;
	for (int k = 0; k <= detail; k++) {
		sum += amp * gradient_noise(p);
		total += amp;
		amp *= 0.5;
		p *= 2.0;
	}
	return 0.5 + 0.5 * 1.4 * sum / total;
}

// --- The water ---------------------------------------------------------------

float ripples(vec2 p) {
	return noise_fac(vec3(p * 0.9, TIME * 0.12 * 0.9), 3);
}

float flowing(vec2 pos, float ph0, float ph1, float blend) {
	vec2 p0 = pos - flow * (ph0 * period);
	vec2 p1 = pos - flow * (ph1 * period) + vec2(3.7, 1.9);
	return mix(ripples(p0), ripples(p1), blend);
}

void fragment() {
	vec2 pos = world_pos.xz;
	float cycle = TIME / period + noise_fac(vec3(pos * 0.25, 0.0), 0) * 3.0;
	float ph0 = fract(cycle);
	float ph1 = fract(cycle + 0.5);
	float blend = abs((ph0 - 0.5) * 2.0);  // 1 when copy 0 restarts

	float wave = flowing(pos, ph0, ph1, blend);
	// Bump: the ripples' slope tilts the normal, so highlights move with them.
	const float e = 0.04;
	float wx = flowing(pos + vec2(e, 0.0), ph0, ph1, blend);
	float wz = flowing(pos + vec2(0.0, e), ph0, ph1, blend);
	vec3 n = normalize(vec3(-(wx - wave) / e * bump_distance * bump_strength, 1.0,
			-(wz - wave) / e * bump_distance * bump_strength));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);

	vec3 col = mix(shallow, deep, smoothstep(0.2, 2.2, depth));

	// Foam: a rim at the bank that breathes and frays with the ripples.
	float edge = 0.05 + sin(TIME * 1.6) * 0.03 + wave * 0.12;
	float foam = depth < edge ? 1.0 : 0.0;
	col = mix(col, foam_colour, foam * 0.75);

	// Sparkle: 3D Voronoi cells (scale 2.6) drifting with the flow, sliced at the water's height.
	vec3 drift = vec3(pos - flow * TIME, world_pos.y) * 2.6;
	vec3 cell_id = floor(drift);
	float best = 1e9;
	vec3 best_cell = vec3(0.0);
	for (int x = -1; x <= 1; x++) for (int y = -1; y <= 1; y++) for (int z = -1; z <= 1; z++) {
		vec3 c = cell_id + vec3(float(x), float(y), float(z));
		float d = length(c + hash33(c) - drift);
		if (d < best) {
			best = d;
			best_cell = c;
		}
	}
	vec3 rnd = hash33(best_cell + 17.0);
	float can = rnd.x > 0.65 ? 1.0 : 0.0;
	float pace = 6.283 / (3.5 + rnd.y * 2.5);
	float wave_t = sin(TIME * pace + rnd.z * 6.283);
	float blink = max((wave_t - 0.96) / 0.04, 0.0);
	float dot_ = best < 0.22 ? 1.0 : 0.0;
	float spark = can * blink * dot_ * (depth > 0.35 ? 1.0 : 0.0);

	ALBEDO = col;
	ROUGHNESS = 0.18;
	// Blender lights reflections with the backdrop at half strength (world strength 0.5 off camera);
	// Godot reflects the background at full strength, so the reflectance is halved to match.
	SPECULAR = 0.25;
	EMISSION = vec3(spark * sparkle_strength);
}
