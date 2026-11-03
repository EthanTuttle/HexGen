// A gorge's white water (Ethan, Nov 3, 2026: it moves, so the rapids read as fast). Unlit, so walls don't shade it grey. Each ring
// is its own: UV its drift (world X, Z, metres a second), UV2 its middle (world X, Z), COLOR.r its phase, COLOR.g how its water
// rises per metre, COLOR.b its pace. With a drift it swells, runs along the flow and shrinks away; with none (a boulder's or a
// fall's foam) it stays and churns. PLACEHOLDER: the times, sizes and how far it dims at night.
shader_type spatial;
render_mode unshaded, shadows_disabled;

uniform float night = 0.0;
uniform vec3 foam_colour : source_color = vec3(0.957, 0.98, 0.973);

void vertex() {
	float running = step(0.001, length(UV));
	float period = mix(mix(1.1, 1.8, COLOR.b), mix(0.55, 0.9, COLOR.b), running);
	float p = fract(TIME / period + COLOR.r);
	vec2 off = VERTEX.xz - UV2;
	float life = p * (1.0 - p) * 4.0;
	float size = mix(0.8 + 0.25 * sin(TAU * p), sqrt(life), running);
	float along = (p - 0.5) * period;
	VERTEX.xz = UV2 + off * size + UV * along;
	VERTEX.y += (COLOR.g * 4.0 - 2.0) * length(UV) * along * running + 0.01;
}

void fragment() {
	ALBEDO = foam_colour * mix(1.0, 0.45, night);
}
