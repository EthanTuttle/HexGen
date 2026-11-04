// A fight map's lava (art/handoff/combat_hills_kit.md -> Moving lava), in flat colours with crisp edges (Ethan, Nov 4, 2026: hard flat bands). flow: the moving
// surface, bands drifting down the metres from the crater (CombatMap.flow_mesh says how each triangle gets them). Otherwise the shared `lava` of craters, streaks and vents, one flat colour.
// Speed, spacing and colours are PLACEHOLDER until seen on the phone.
shader_type spatial;
render_mode cull_back, unshaded;

uniform bool flow = true;
uniform vec3 deep : source_color = vec3(0.757, 0.204, 0.063);   // #C1340F
uniform vec3 mid : source_color = vec3(0.957, 0.475, 0.165);    // #F4792A, the tiles' lava
uniform vec3 hot : source_color = vec3(1.0, 0.769, 0.302);      // #FFC44D

varying vec2 plan;
varying vec4 way;
varying vec4 metres;

void vertex() {
	plan = vec2(VERTEX.x, -VERTEX.z);
	way = CUSTOM0;
	metres = CUSTOM1;
}

// 1 past edge, with a one-pixel step so a moving edge stays crisp without shimmering.
float past(float value, float edge) {
	float w = fwidth(value);
	return clamp((value - edge) / max(w, 0.0001) + 0.5, 0.0, 1.0);
}

void fragment() {
	vec3 c = hot;
	if (flow) {
		float along = UV.y;
		if (metres.z >= 0.0) {
			vec2 axis = way.zw - way.xy;
			vec2 off = plan - way.xy;
			float size = dot(axis, axis);
			along = mix(metres.x, metres.y, clamp(dot(off, axis) / size, 0.0, 1.0)) - metres.w * abs(off.x * axis.y - off.y * axis.x) / sqrt(size);
		}
		float f = fract(along * 1.3 - TIME * 0.22);
		c = mix(c, mid, past(f, 0.5));
		c = mix(c, deep, past(f, 0.8));
	}
	ALBEDO = c;
}
