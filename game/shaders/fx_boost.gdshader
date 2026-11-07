// Boost pad: scrolling chevrons, emissive.
shader_type spatial;
render_mode unshaded, cull_disabled;
uniform vec4 c1 : source_color = vec4(1.0, 0.78, 0.2, 1.0);
uniform vec4 c2 : source_color = vec4(1.0, 0.42, 0.25, 1.0);
void fragment() {
	vec2 uv = UV;
	float v = uv.y * 3.0 + abs(uv.x - 0.5) * 2.0 + TIME * 2.5;
	float s = step(0.5, fract(v));
	float edge = smoothstep(0.0, 0.06, min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y)));
	vec3 c = mix(c1.rgb, c2.rgb, s);
	ALBEDO = mix(vec3(1.0), c, edge) * 1.6;
}
