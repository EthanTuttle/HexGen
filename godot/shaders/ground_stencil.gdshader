// A gorge's land: ground.gdshader, and it marks the stencil like the rock (Gorge; shaders/mini_silhouette.gdshader), so a
// mini wading below shows through the land as well as the wall.
shader_type spatial;
stencil_mode write, compare_always, 1;

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
