// Camera-facing (Y-locked) additive flame with a rising heat wobble.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;

uniform sampler2D flame_tex : source_color, filter_linear, repeat_disable;
uniform sampler2D noise_tex : filter_linear_mipmap, repeat_enable;
uniform float intensity = 1.6;
uniform float seed = 0.0;
global uniform vec4 fog_color;
global uniform float fog_far;

void vertex() {
	vec3 cam = normalize((INV_VIEW_MATRIX[3].xyz - MODEL_MATRIX[3].xyz) * vec3(1.0, 0.0, 1.0));
	vec3 up = vec3(0.0, 1.0, 0.0);
	vec3 right = normalize(cross(up, cam));
	float sx = length(MODEL_MATRIX[0].xyz);
	float sy = length(MODEL_MATRIX[1].xyz);
	vec3 world = MODEL_MATRIX[3].xyz + right * VERTEX.x * sx + up * VERTEX.y * sy;
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(world, 1.0);
}

void fragment() {
	float t = TIME * 1.6 + seed * 13.0;
	float n = texture(noise_tex, vec2(UV.x * 0.6 + seed, UV.y * 0.5 + t * 0.35)).r;
	float n2 = texture(noise_tex, vec2(UV.x * 1.3 - seed, UV.y * 1.1 + t * 0.6)).g;
	vec2 uv = UV;
	uv.x += (n - 0.5) * 0.28 * (1.0 - UV.y);
	uv.y += (n2 - 0.5) * 0.12;
	vec4 f = texture(flame_tex, uv);
	float flick = 0.85 + 0.15 * sin(t * 7.0 + n * 6.0);
	float dist = length(VERTEX);
	float fade = 1.0 - smoothstep(fog_far * 0.6, fog_far * 1.1, dist);
	ALBEDO = f.rgb * intensity * flick * fade;
	ALPHA = f.a;
}
