// Alpha-tested leaf and plant cards with gentle wind sway and soft back lighting.
shader_type spatial;
render_mode cull_disabled, diffuse_lambert, specular_disabled, alpha_to_coverage_and_one;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform float alpha_cut = 0.42;
uniform float sway = 1.0;
uniform vec3 tint : source_color = vec3(1.0);
uniform vec3 translucency : source_color = vec3(0.18, 0.2, 0.08);
global uniform float wind_strength;

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec3 origin = MODEL_MATRIX[3].xyz;
	float h = max(wp.y - origin.y, 0.0);
	float phase = TIME * (1.3 + wind_strength * 1.6) + wp.x * 0.31 + wp.z * 0.23;
	float s = sin(phase) + 0.45 * sin(phase * 2.3 + wp.y * 0.7);
	float amp = (0.012 + wind_strength * 0.05) * h * sway;
	vec3 push = vec3(s * amp, 0.0, cos(phase * 0.8) * amp * 0.6);
	VERTEX += (inverse(mat3(MODEL_MATRIX)) * push);
}

void fragment() {
	vec4 c = texture(albedo_tex, UV);
	ALBEDO = c.rgb * COLOR.rgb * tint;
	ALPHA = c.a;
	ALPHA_SCISSOR_THRESHOLD = alpha_cut;
	ALPHA_ANTIALIASING_EDGE = 0.25;
	ALPHA_TEXTURE_COORDINATE = UV * vec2(textureSize(albedo_tex, 0));
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
	BACKLIGHT = translucency;
	ROUGHNESS = 1.0;
}
