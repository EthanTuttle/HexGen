// Ground colour of the map tiles' base slabs (look test 1: hex edge blending).
// Works in world space: finds the tile under the pixel, then mixes in each placed neighbour's ground
// colour with a weight that falls from 1 at the shared edge to 0 at blend_width away from it
// (the own tile always weighs 1). At an edge both tiles weigh 1, so they meet at the average.
// Distances are to each neighbour's whole hexagon, so the blend stays continuous at corners where
// three terrains meet (ground_cover.py's edge-by-edge fade jumps there, which shows in colour).
shader_type spatial;

uniform sampler2D terrain_map : filter_nearest;  // texel (q + 32, r + 32): sRGB ground colour, alpha 1 = placed
uniform float blend_width = 1.6;

#include "res://shaders/ground_blend.gdshaderinc"

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	ALBEDO = ground_colour(world_pos);
	ROUGHNESS = 0.9;
}
