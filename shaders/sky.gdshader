// Morrowind-style sky dome: sky colour fading to the fog colour at the horizon, a scrolling
// cloud layer on a flattened dome, a glaring sun, two moons and a star field at night.
shader_type sky;

uniform vec3 sky_color : source_color = vec3(0.37, 0.53, 0.8);
uniform vec3 horizon_color : source_color = vec3(0.8, 0.86, 0.95);
uniform vec3 sun_color : source_color = vec3(1.0);
uniform vec3 sun_disc_color : source_color = vec3(1.0, 0.95, 0.85);
uniform vec3 sun_direction = vec3(0.0, 0.5, 0.8);
uniform float sun_visibility = 1.0;
uniform float sunset_glow = 0.0;
uniform sampler2D clouds_a : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D clouds_b : source_color, filter_linear_mipmap, repeat_enable;
uniform float cloud_blend = 0.0;
uniform vec2 cloud_offset = vec2(0.0);
uniform vec3 cloud_lit : source_color = vec3(1.0);
uniform vec3 cloud_shade : source_color = vec3(0.6);
uniform float cloud_opacity = 1.0;
uniform sampler2D stars_tex : source_color, filter_linear_mipmap;
uniform float stars_alpha = 0.0;
uniform sampler2D moon_large_tex : source_color, filter_linear_mipmap;
uniform sampler2D moon_small_tex : source_color, filter_linear_mipmap;
uniform vec3 moon_large_dir = vec3(0.3, 0.5, -0.8);
uniform vec3 moon_small_dir = vec3(-0.4, 0.6, -0.7);
uniform float moon_large_size = 0.1;
uniform float moon_small_size = 0.055;
uniform float moon_alpha = 0.0;
uniform float flash = 0.0;

vec4 moon(vec3 d, vec3 mdir, float size, sampler2D tex) {
	mdir = normalize(mdir);
	float c = dot(d, mdir);
	if (c < 0.95) {
		return vec4(0.0);
	}
	vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), mdir));
	vec3 up = cross(mdir, right);
	vec3 p = d / c - mdir;
	vec2 uv = vec2(dot(p, right), -dot(p, up)) / size * 0.5 + 0.5;
	if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) {
		return vec4(0.0);
	}
	return texture(tex, uv);
}

void sky() {
	vec3 d = EYEDIR;
	float up = d.y;
	float t = smoothstep(-0.04, 0.45, up);
	vec3 col = mix(horizon_color, sky_color, pow(t, 0.8));
	float above = smoothstep(-0.02, 0.14, up);

	if (stars_alpha > 0.001) {
		vec2 suv = vec2(atan(d.x, d.z) / TAU + 0.5, acos(clamp(d.y, -1.0, 1.0)) / PI);
		col += texture(stars_tex, suv).rgb * stars_alpha * above * 1.6;
	}
	if (moon_alpha > 0.001) {
		vec4 ml = moon(d, moon_large_dir, moon_large_size, moon_large_tex);
		col = mix(col, ml.rgb * 1.15, ml.a * moon_alpha * above);
		vec4 ms = moon(d, moon_small_dir, moon_small_size, moon_small_tex);
		col = mix(col, ms.rgb * 1.2, ms.a * moon_alpha * above);
	}

	vec3 sd = normalize(sun_direction);
	float cs = max(dot(d, sd), 0.0);
	float disc = smoothstep(0.99905, 0.9994, cs);
	float halo = pow(cs, 220.0) * 1.4 + pow(cs, 18.0) * 0.32 + pow(cs, 5.0) * 0.1;
	col += sun_color * halo * sun_visibility * above;
	col += sun_color * sunset_glow * pow(cs, 2.5) * (1.0 - t * 0.85) * 0.75;
	col = mix(col, sun_disc_color * 3.5, disc * sun_visibility * above);

	if (up > -0.03) {
		vec2 cuv = d.xz / (max(up, 0.0) + 0.085) * 0.17 + cloud_offset;
		vec4 c = mix(texture(clouds_a, cuv), texture(clouds_b, cuv), cloud_blend);
		float a = c.a * cloud_opacity * smoothstep(-0.03, 0.2, up);
		float sunlit = pow(cs, 5.0);
		vec3 cc = mix(cloud_shade, cloud_lit, c.r) + sun_color * sunlit * 0.5 * sun_visibility;
		col = mix(col, cc, a);
	}
	col += vec3(0.8, 0.85, 1.0) * flash;
	COLOR = col;
}
