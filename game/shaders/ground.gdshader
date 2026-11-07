// Terrain: vertex colours from the track builder (grass, shoulder, rock on
// steep slopes) with noise so big fields don't look flat. pattern: 0 grass
// (tiny blades of shade), 1 sand ripples, 2 snow sparkle, 3 rock strata.
shader_type spatial;

uniform sampler2D noise_tex : repeat_enable, filter_linear_mipmap;
uniform int pattern = 0;
uniform float band_soft = 0.22;
uniform float shade = 0.5;
uniform vec3 shade_tint : source_color = vec3(0.78, 0.82, 1.0);

varying vec3 wpos;
varying vec3 wnrm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = NORMAL;
}

void fragment() {
	float n = texture(noise_tex, wpos.xz * 0.035).r;
	float n2 = texture(noise_tex, wpos.xz * 0.31).r;
	float n3 = texture(noise_tex, wpos.xz * 1.7).r;
	vec3 c = COLOR.rgb * (0.88 + 0.24 * n + 0.10 * (n2 - 0.5));
	if (pattern == 0) {
		c *= 0.95 + 0.1 * n3;
	} else if (pattern == 1) {
		float r = sin(wpos.x * 1.3 + wpos.z * 0.7 + n2 * 6.0);
		c *= 0.95 + 0.06 * r;
	} else if (pattern == 2) {
		c += vec3(0.25) * smoothstep(0.86, 0.9, n3);
	} else if (pattern == 3) {
		c *= 0.9 + 0.12 * sin(wpos.y * 2.2 + n2 * 3.0);
	}
	ALBEDO = c;
	ROUGHNESS = 0.95;
	SPECULAR = pattern == 2 ? 0.4 : 0.1;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float b = smoothstep(0.0, band_soft, ndl) * ATTENUATION;
	vec3 l = mix(shade_tint * shade, vec3(1.0), b);
	if (!LIGHT_IS_DIRECTIONAL) {
		l = vec3(smoothstep(-0.2, 0.4, ndl)) * ATTENUATION;
	}
	DIFFUSE_LIGHT += l * LIGHT_COLOR * ALBEDO / PI;
}
