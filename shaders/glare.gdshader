// Screen-space sun glare, drawn additively over the 3D view when the sun is in sight.
shader_type canvas_item;
render_mode blend_add, unshaded;

uniform vec2 sun_screen = vec2(0.5);
uniform float intensity = 0.0;
uniform vec3 glare_color : source_color = vec3(1.0, 0.95, 0.88);
uniform float aspect = 1.777;

void fragment() {
	vec2 d = (UV - sun_screen) * vec2(aspect, 1.0);
	float r = length(d);
	float core = exp(-r * r / 0.012);
	float bloom = exp(-r * r / 0.09) * 0.55;
	float wash = exp(-r * 2.2) * 0.25;
	float rays = (0.5 + 0.5 * sin(atan(d.y, d.x) * 9.0)) * exp(-r * 6.0) * 0.12;
	COLOR = vec4(glare_color * (core + bloom + wash + rays) * intensity, 1.0);
}
