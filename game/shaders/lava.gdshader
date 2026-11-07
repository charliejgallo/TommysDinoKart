// Cartoon lava: slow glowing currents with dark crust plates.
shader_type spatial;
render_mode cull_back;
uniform sampler2D noise_tex : repeat_enable, filter_linear_mipmap;
uniform vec4 hot : source_color = vec4(1.0, 0.55, 0.12, 1.0);
uniform vec4 crust : source_color = vec4(0.28, 0.1, 0.08, 1.0);
varying vec3 wpos;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}
void fragment() {
	float t = TIME * 0.03;
	float n = texture(noise_tex, wpos.xz * 0.03 + vec2(t, t * 0.7)).r;
	float n2 = texture(noise_tex, wpos.xz * 0.11 - vec2(t * 1.3, t * 0.4)).r;
	float k = smoothstep(0.42, 0.62, n * 0.7 + n2 * 0.5);
	vec3 c = mix(hot.rgb * 1.2, crust.rgb, k);
	ALBEDO = c;
	EMISSION = hot.rgb * (1.0 - k) * (1.6 + 0.4 * sin(TIME * 1.7 + n * 8.0));
	ROUGHNESS = 0.9;
}
