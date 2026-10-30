// The hills' and highlands' pieces cover their whole tile, so the base slab's faded ground never shows and a
// hard hexagon of hill grass met the plains. Here the pieces' grass (the faces whose vertex colour is the
// hill grass) takes the same faded ground colour as the base slabs; everything else keeps its vertex colour.
// Engine side; it matches the grass by colour until the art marks ground faces (see README).
shader_type spatial;

uniform sampler2D terrain_map : filter_nearest;
uniform float blend_width = 1.6;
uniform vec3 grass_a;   // linear hill_grass
uniform vec3 grass_b;   // linear highland_grass

#include "res://shaders/ground_blend.gdshaderinc"

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 c = COLOR.rgb;
	bool grass = distance(c, grass_a) < 0.02 || distance(c, grass_b) < 0.02;
	ALBEDO = grass ? ground_colour(world_pos) : c;
	ROUGHNESS = 0.9;
}
