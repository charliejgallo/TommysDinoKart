// Road surfaces and curbs. UV.x runs across the road (0 left edge .. 1
// right edge), UV.y along it (metres / 4 on the road, / 3 on curbs).
// kind: 0 asphalt, 1 dirt, 2 sand, 3 ice, 4 stone, 5 wood planks,
//       6 crystal, 7 rainbow, 10 curb (stripes base/line)
shader_type spatial;

uniform int kind = 0;
uniform vec4 base : source_color = vec4(0.36, 0.37, 0.43, 1.0);
uniform vec4 line : source_color = vec4(1.0, 0.96, 0.86, 1.0);
uniform sampler2D noise_tex : repeat_enable, filter_linear_mipmap;
uniform float band_soft = 0.22;
uniform float shade = 0.5;
uniform vec3 shade_tint : source_color = vec3(0.78, 0.82, 1.0);

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float band(float x, float a, float b, float aa) {
	return smoothstep(a - aa, a + aa, x) * (1.0 - smoothstep(b - aa, b + aa, x));
}

void fragment() {
	vec2 uv = UV;
	float n = texture(noise_tex, wpos.xz * 0.11).r;
	float n2 = texture(noise_tex, wpos.xz * 0.9).r;
	vec3 c = base.rgb;
	float rough = 0.9;
	float aa = fwidth(uv.x) * 1.2;
	if (kind == 10) {
		float s = step(0.5, fract(uv.y * 1.0));
		c = mix(base.rgb, line.rgb, s);
		c *= 0.94 + 0.12 * n;
		rough = 0.7;
	} else if (kind == 0) {
		float n3 = texture(noise_tex, wpos.xz * 3.1).r;
		c *= 0.9 + 0.16 * n + 0.08 * (n3 - 0.5);
		// fine grit
		c += vec3(0.05) * smoothstep(0.66, 0.72, n3) - vec3(0.03) * smoothstep(0.62, 0.7, 1.0 - n3);
		float edge = band(uv.x, 0.025, 0.045, aa) + band(uv.x, 0.955, 0.975, aa);
		float dash = band(uv.x, 0.493, 0.507, aa) * step(0.55, fract(uv.y * 0.5));
		c = mix(c, line.rgb, clamp(edge + dash * 0.85, 0.0, 1.0));
		rough = 0.75;
	} else if (kind == 1 || kind == 2) {
		c *= 0.82 + 0.3 * n + 0.12 * (n2 - 0.5);
		// wheel ruts
		float rut = band(uv.x, 0.28, 0.36, aa * 2.0) + band(uv.x, 0.64, 0.72, aa * 2.0);
		c *= 1.0 - 0.10 * rut;
		c = mix(c, c * 0.8, smoothstep(0.0, 0.06, 0.06 - min(uv.x, 1.0 - uv.x)));
	} else if (kind == 3) {
		c *= 0.92 + 0.14 * n;
		c += vec3(0.2) * smoothstep(0.6, 0.9, n2) * 0.5;
		float edge = band(uv.x, 0.03, 0.05, aa) + band(uv.x, 0.95, 0.97, aa);
		c = mix(c, line.rgb, edge * 0.6);
		rough = 0.2;
	} else if (kind == 4) {
		vec2 cell = vec2(uv.x * 8.0, uv.y * 4.0 + floor(uv.x * 8.0) * 0.5);
		vec2 f = fract(cell);
		float grout = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y));
		float id = fract(sin(dot(floor(cell), vec2(12.9898, 78.233))) * 43758.5453);
		c *= 0.85 + 0.25 * id + 0.1 * n;
		c = mix(c * 0.55, c, smoothstep(0.02, 0.07, grout));
	} else if (kind == 5) {
		float plank = fract(uv.y * 6.0);
		float id = fract(sin(floor(uv.y * 6.0) * 91.7) * 4375.5);
		c *= 0.82 + 0.25 * id + 0.15 * (texture(noise_tex, vec2(uv.x * 0.3, uv.y * 0.2)).r - 0.5);
		c = mix(c * 0.5, c, smoothstep(0.0, 0.06, min(plank, 1.0 - plank)));
	} else if (kind == 6) {
		c *= 0.9 + 0.2 * n;
		c += vec3(0.25, 0.3, 0.45) * smoothstep(0.55, 0.95, n2);
		EMISSION = c * 0.25;
		rough = 0.25;
	} else if (kind == 7) {
		vec3 rb = 0.5 + 0.5 * cos(6.2831 * (uv.x * 1.0 + vec3(0.0, 0.33, 0.67)));
		c = mix(rb, vec3(1.0), 0.25);
		c *= 0.9 + 0.15 * n;
		EMISSION = c * 0.35;
		rough = 0.4;
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	SPECULAR = (kind == 3 || kind == 6) ? 0.6 : 0.2;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float b = smoothstep(0.0, band_soft, ndl) * ATTENUATION;
	vec3 l = mix(shade_tint * shade, vec3(1.0), b);
	if (!LIGHT_IS_DIRECTIONAL) {
		l = vec3(smoothstep(-0.2, 0.4, ndl)) * ATTENUATION;
	}
	DIFFUSE_LIGHT += l * LIGHT_COLOR * ALBEDO / PI;
	if (kind == 3 || kind == 6) {
		vec3 h = normalize(VIEW + LIGHT);
		float s = pow(clamp(dot(NORMAL, h), 0.0, 1.0), 60.0);
		SPECULAR_LIGHT += s * 0.6 * LIGHT_COLOR * ATTENUATION;
	}
}
