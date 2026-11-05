// Water, ported from art/scripts/render_animation.py (water_material). Per vertex the mesh carries
// UV.x = depth (distance to the nearest shore) and UV2 = flow (world X, Z; metres per second).
// - ripples flow along rivers: a two-phase flow-map scroll, cross-faded so the restart never shows
// - sparkle: small random cells drifting with the flow, about 1 in 3 can glint, each on its own clock
// - a foam rim at the shore that breathes and frays with the ripples
// - darker water away from the shore
shader_type spatial;

uniform vec3 shallow = vec3(0.27, 0.56, 0.76);  // linear; Blender: (0.36, 0.70, 0.86), which read icy on narrow rivers
uniform vec3 deep = vec3(0.13, 0.42, 0.66);
uniform vec3 foam_colour = vec3(0.94, 0.97, 1.0);
uniform float period = 2.0;
uniform float bump_strength = 2.0;  // Blender: 0.7; raised by eye, its Bump node reads stronger than this port
uniform float bump_distance = 0.08;
uniform float sparkle_strength = 2.5;
uniform sampler2D ripple_map : repeat_enable, filter_linear_mipmap;
const float TILE = 8.9;          // metres the baked tile covers (Water.RIPPLE_TILE)
const float SLOPE_RANGE = 4.0;   // the slopes it can hold (Water.RIPPLE_SLOPE)
uniform float night = 0.0;  // 0 by day, 1 at night: set by the map so the water doesn't outshine the land

varying vec3 world_pos;
varying float depth;
varying vec2 flow;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	depth = UV.x;
	flow = UV2;
}

// --- Noise -------------------------------------------------------------------
// Ripples come from one baked tile (Water.ripple_texture: height in R, slopes in G and B), as working out 3D noise per pixel took a phone under 60 fps on broad water.

vec3 hash33(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.xxy + p.yxx) * p.zyx);
}

// Height in x, its slope per metre in y and z. Two layers drifting apart stand in for the noise evolving.
vec3 ripples(vec2 p) {
	vec2 slow = vec2(TIME * 0.05, -TIME * 0.03);
	vec3 a = texture(ripple_map, (p + slow) / TILE).rgb;
	vec3 b = texture(ripple_map, (p * 0.77 - slow + vec2(2.3, 5.1)) / TILE).rgb;
	vec3 c = mix(a, b, 0.5);
	return vec3(c.r, (c.gb - 0.5) * SLOPE_RANGE);
}

vec3 flowing(vec2 pos, float ph0, float ph1, float blend) {
	vec2 p0 = pos - flow * (ph0 * period);
	vec2 p1 = pos - flow * (ph1 * period) + vec2(3.7, 1.9);
	return mix(ripples(p0), ripples(p1), blend);
}

void fragment() {
	vec2 pos = world_pos.xz;
	float cycle = TIME / period + texture(ripple_map, pos * 0.25 / TILE).r * 3.0;
	float ph0 = fract(cycle);
	float ph1 = fract(cycle + 0.5);
	float blend = abs((ph0 - 0.5) * 2.0);  // 1 when copy 0 restarts

	vec3 ripple = flowing(pos, ph0, ph1, blend);
	float wave = ripple.x;
	// Bump: the ripples' slope tilts the normal, so highlights move with them.
	vec3 n = normalize(vec3(-ripple.y * bump_distance * bump_strength, 1.0, -ripple.z * bump_distance * bump_strength));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);

	vec3 col = mix(shallow, deep, smoothstep(0.2, 2.2, depth));

	// Foam: a rim at the bank that breathes and frays with the ripples.
	float edge = 0.05 + sin(TIME * 1.6) * 0.03 + wave * 0.06;  // fray 0.06 (Blender 0.12): a thinner rim
	float foam = depth < edge ? 1.0 : 0.0;
	col = mix(col, foam_colour, foam * 0.55);  // 0.55 (Blender 0.75): the rim read as ice at game distance

	// Sparkle: Voronoi cells (scale 2.6) drifting with the flow.
	vec2 drift = (pos - flow * TIME) * 2.6;
	vec2 cell_id = floor(drift);
	float best = 1e9;
	vec3 best_cell = vec3(0.0);
	for (int x = -1; x <= 1; x++) for (int y = -1; y <= 1; y++) {
		vec3 c = vec3(cell_id + vec2(float(x), float(y)), 0.0);
		float d = length(c.xy + hash33(c).xy - drift);
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

	ALBEDO = col * mix(1.0, 0.7, night);
	ROUGHNESS = 0.18;
	// Blender lights reflections with the backdrop at half strength (world strength 0.5 off camera);
	// Godot reflects the background at full strength, so the reflectance is halved to match.
	SPECULAR = 0.25 * mix(1.0, 0.4, night);
	EMISSION = vec3(spark * sparkle_strength);
}
