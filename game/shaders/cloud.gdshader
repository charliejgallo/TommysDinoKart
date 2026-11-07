// Far cartoon clouds: white tops, soft lilac-blue undersides, no fog.
shader_type spatial;
render_mode unshaded, fog_disabled, cull_back;
uniform vec4 top : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform vec4 bottom : source_color = vec4(0.8, 0.85, 0.98, 1.0);
varying float ny;
void vertex() {
	ny = (MODEL_MATRIX * vec4(NORMAL, 0.0)).y;
}
void fragment() {
	float k = smoothstep(-0.4, 0.5, ny);
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALBEDO = mix(bottom.rgb, top.rgb, k) + rim * 0.06;
}
