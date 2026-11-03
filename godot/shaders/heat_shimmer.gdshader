// Heat waves over open ground (oasis and badlands: design/07 -> Region variant looks; desert kit -> shimmer). An upright
// quad turned to the camera bends what's behind it, in waves running upward; it fades out at its edges so no shape
// shows, and out at night. PLACEHOLDER strength and speed. It reads the screen, so it's on the phone check's list.
shader_type spatial;
render_mode unshaded, depth_draw_never, cull_disabled, shadows_disabled;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear, repeat_disable;
uniform float strength = 1.0;

void vertex() {
	vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), INV_VIEW_MATRIX[2].xyz));
	vec3 back = normalize(cross(right, vec3(0.0, 1.0, 0.0)));
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(vec4(right, 0.0), vec4(0.0, 1.0, 0.0, 0.0), vec4(back, 0.0), MODEL_MATRIX[3]);
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	float edge = smoothstep(0.0, 0.22, UV.x) * smoothstep(1.0, 0.78, UV.x) * smoothstep(0.0, 0.5, UV.y) * smoothstep(1.0, 0.92, UV.y);
	float wave = sin(UV.y * 42.0 + TIME * 3.3 + UV.x * 6.0) * 0.6 + sin(UV.y * 83.0 + TIME * 5.2 - UV.x * 9.0) * 0.4;
	ALBEDO = textureLod(screen_tex, SCREEN_UV + vec2(wave * 0.0028 * edge * strength, 0.0), 0.0).rgb;
	ALPHA = edge;
}
