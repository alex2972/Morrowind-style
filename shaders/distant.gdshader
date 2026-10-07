// Far landmarks (island fortress, mountain ring): triplanar texture with a haze curve that
// keeps silhouettes visible far beyond the land fog, like Morrowind's distant land.
shader_type spatial;
render_mode diffuse_lambert, specular_disabled, cull_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D roof_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float uv_scale = 0.12;
uniform vec3 tint : source_color = vec3(1.0);
uniform float haze_reach = 3.4;
uniform float min_haze = 0.25;
uniform float max_haze = 0.93;
global uniform vec4 fog_color;
global uniform float fog_far;

varying vec3 wpos;
varying vec3 wnorm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 b = pow(abs(wnorm), vec3(3.0));
	b /= (b.x + b.y + b.z);
	vec3 c = texture(albedo_tex, wpos.zy * uv_scale).rgb * b.x + texture(albedo_tex, wpos.xz * uv_scale).rgb * b.y
			+ texture(albedo_tex, wpos.xy * uv_scale).rgb * b.z;
	ALBEDO = c * COLOR.rgb * tint;
	ROUGHNESS = 1.0;
	float d = length(wpos - CAMERA_POSITION_WORLD);
	float h = clamp(d / max(fog_far * haze_reach, 1.0), 0.0, 1.0);
	FOG = vec4(fog_color.rgb, clamp(mix(min_haze, max_haze, sqrt(h)) * smoothstep(0.0, 1.0, d / max(fog_far, 1.0)) , 0.0, 0.995));
}
