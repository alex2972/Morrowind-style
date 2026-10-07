// Eight-layer splat terrain with height-aware blending, macro variation, baked AO tint,
// underwater darkening and clipping for the planar-reflection camera.
shader_type spatial;
render_mode diffuse_lambert, specular_disabled;

uniform sampler2D splat_a : filter_linear, repeat_disable;
uniform sampler2D splat_b : filter_linear, repeat_disable;
uniform sampler2D tint_map : filter_linear, repeat_disable;
uniform sampler2D macro_tex : filter_linear_mipmap, repeat_enable;
uniform sampler2D tex_grass : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_dirt : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_rock : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_mud : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_ash : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_sand : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_cobble : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_road : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float map_half = 256.0;
// texture repeats per metre
uniform vec4 scale_a = vec4(0.25, 0.25, 0.2, 0.25);
uniform vec4 scale_b = vec4(0.22, 0.25, 0.42, 0.25);
uniform float blend_depth = 0.22;
global uniform float water_level;
global uniform float wetness;

varying vec3 wpos;
varying vec3 wnorm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

vec3 triplanar(sampler2D t, vec3 p, vec3 n, float s) {
	vec3 b = pow(abs(n), vec3(4.0));
	b /= (b.x + b.y + b.z);
	return texture(t, p.zy * s).rgb * b.x + texture(t, p.xz * s).rgb * b.y + texture(t, p.xy * s).rgb * b.z;
}

float lum(vec3 c) {
	return dot(c, vec3(0.3, 0.45, 0.25));
}

void fragment() {
	if ((CAMERA_VISIBLE_LAYERS & (1u << 19u)) != 0u && wpos.y < water_level - 0.05) {
		discard;
	}
	vec2 muv = (wpos.xz + map_half) / (2.0 * map_half);
	vec3 macro = texture(macro_tex, wpos.xz * 0.006).rgb;
	vec2 jitter = (texture(macro_tex, wpos.xz * 0.045).gb - 0.5) * 0.007;
	vec4 wa = texture(splat_a, muv + jitter);
	vec4 wb = texture(splat_b, muv + jitter);
	vec2 p = wpos.xz;
	vec3 c0 = texture(tex_grass, p * scale_a.x).rgb;
	vec3 c1 = texture(tex_dirt, p * scale_a.y).rgb;
	vec3 c2 = triplanar(tex_rock, wpos, wnorm, scale_a.z);
	vec3 c3 = texture(tex_mud, p * scale_a.w).rgb;
	vec3 c4 = texture(tex_ash, p * scale_b.x).rgb;
	vec3 c5 = texture(tex_sand, p * scale_b.y).rgb;
	vec3 c6 = texture(tex_cobble, p * scale_b.z).rgb;
	vec3 c7 = texture(tex_road, p * scale_b.w).rgb;
	vec4 wa2 = wa * (0.55 + vec4(lum(c0), lum(c1), lum(c2) * 1.2, lum(c3)));
	vec4 wb2 = wb * (0.55 + vec4(lum(c4), lum(c5), lum(c6) * 1.3, lum(c7)));
	float mx = max(max(max(wa2.x, wa2.y), max(wa2.z, wa2.w)), max(max(wb2.x, wb2.y), max(wb2.z, wb2.w)));
	wa2 = max(wa2 - mx + blend_depth, 0.0);
	wb2 = max(wb2 - mx + blend_depth, 0.0);
	float sum = dot(wa2, vec4(1.0)) + dot(wb2, vec4(1.0)) + 1e-4;
	vec3 col = (c0 * wa2.x + c1 * wa2.y + c2 * wa2.z + c3 * wa2.w + c4 * wb2.x + c5 * wb2.y + c6 * wb2.z + c7 * wb2.w) / sum;
	col *= mix(0.84, 1.12, macro.r);
	col *= texture(tint_map, muv).rgb * 1.2;
	float under = clamp((water_level - wpos.y) / 2.5, 0.0, 1.0);
	col = mix(col, col * vec3(0.36, 0.48, 0.46), under);
	float wet = max(wetness, 1.0 - smoothstep(water_level, water_level + 0.6, wpos.y));
	col *= 1.0 - wet * 0.22;
	ALBEDO = col;
	ROUGHNESS = 1.0 - wet * 0.45;
}
