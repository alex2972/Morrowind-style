// Sea and marsh water: planar reflection (from WaterReflection), refraction with depth
// absorption, scrolling ripple normals and sun glints.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx, cull_back;

uniform sampler2D reflection_tex : source_color, filter_linear, repeat_disable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform vec3 shallow_color : source_color = vec3(0.13, 0.17, 0.14);
uniform vec3 deep_color : source_color = vec3(0.035, 0.06, 0.065);
uniform float has_reflection = 0.0;
uniform float distortion = 0.025;
global uniform vec4 fog_color;
global uniform float wind_strength;
global uniform float night_factor;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float speed = 0.6 + wind_strength;
	vec2 uv1 = wpos.xz * 0.045 + TIME * vec2(0.010, 0.006) * speed;
	vec2 uv2 = wpos.xz * 0.11 + TIME * vec2(-0.008, 0.012) * speed;
	vec2 uv3 = wpos.xz * 0.27 + TIME * vec2(0.02, -0.015) * speed;
	vec3 n1 = texture(normal_tex, uv1).rgb * 2.0 - 1.0;
	vec3 n2 = texture(normal_tex, uv2).rgb * 2.0 - 1.0;
	vec3 n3 = texture(normal_tex, uv3).rgb * 2.0 - 1.0;
	vec2 slope = (n1.xy * 0.5 + n2.xy * 0.35 + n3.xy * 0.25) * (0.75 + wind_strength * 0.9);
	vec3 nw = normalize(vec3(slope.x, 1.0, slope.y));
	NORMAL = normalize((VIEW_MATRIX * vec4(nw, 0.0)).xyz);

	float depth = texture(depth_tex, SCREEN_UV).r;
	vec4 ndc = vec4(SCREEN_UV * 2.0 - 1.0, depth, 1.0);
	vec4 vpos = INV_PROJECTION_MATRIX * ndc;
	vpos.xyz /= vpos.w;
	float thickness = max(0.0, -vpos.z + VERTEX.z);
	float absorb = clamp(thickness * 0.28, 0.0, 1.0);

	vec2 off = slope * distortion * clamp(thickness, 0.0, 1.0);
	vec3 refr = textureLod(screen_tex, SCREEN_UV + off, 0.0).rgb;
	vec3 body = mix(shallow_color, deep_color, clamp(thickness / 7.0, 0.0, 1.0));
	vec3 under = mix(refr * vec3(0.62, 0.78, 0.74), body, absorb);

	vec3 view = normalize(-VERTEX);
	float fres = 0.04 + 0.96 * pow(1.0 - clamp(dot(NORMAL, view), 0.0, 1.0), 4.0);
	fres = clamp(fres * 1.15 + 0.12, 0.0, 1.0);
	vec3 refl = fog_color.rgb;
	if (has_reflection > 0.5) {
		vec2 ruv = vec2(1.0 - SCREEN_UV.x, SCREEN_UV.y) + slope * 0.06;
		refl = texture(reflection_tex, clamp(ruv, vec2(0.001), vec2(0.999))).rgb;
	}
	vec3 col = mix(under, refl * 0.62 + body * 0.3, fres * 0.8);
	// soft foam line where the water meets the shore
	float foam = (1.0 - smoothstep(0.0, 0.35, thickness)) * (0.5 + 0.5 * n3.x);
	col += vec3(0.5, 0.52, 0.48) * foam * 0.25 * (1.0 - night_factor * 0.8);
	ALBEDO = vec3(0.0);
	EMISSION = col;
	ROUGHNESS = 0.12;
	SPECULAR = 0.55;
}
