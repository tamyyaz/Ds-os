shader_type canvas_item;
// Game art for cards, hero background and reflections.
// With a texture (real cover/hero art) it shows that; without one it paints a layered
// "landscape" from two colours, so the launcher looks designed even with placeholder data.

uniform vec4 c1 : source_color = vec4(0.54, 0.72, 1.0, 1.0);   // light / accent colour
uniform vec4 c2 : source_color = vec4(0.04, 0.04, 0.08, 1.0);  // dark colour
uniform float seed = 1.0;
uniform float aspect = 0.667;          // width / height of the drawn rect
uniform float zoom = 1.0;
uniform bool has_tex = false;
uniform sampler2D tex : filter_linear_mipmap, repeat_disable;
uniform float radius = 0.0;            // corner radius in px (0 = square)
uniform vec2 rect_size = vec2(220.0, 330.0);
uniform float dim : hint_range(0.0, 1.0) = 0.0;
uniform float bottom_dark : hint_range(0.0, 1.0) = 0.0;
uniform bool reflection = false;
uniform float refl_part = 0.34;        // share of the card height that is mirrored
uniform float refl_strength = 0.30;

float hash(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}

float fbm(vec2 p) {
	float v = 0.0;
	float a = 0.5;
	for (int i = 0; i < 4; i++) {
		v += a * vnoise(p);
		p *= 2.0;
		a *= 0.5;
	}
	return v;
}

vec3 landscape(vec2 uv) {
	vec2 p = vec2(uv.x * aspect, uv.y);
	vec3 col = mix(c1.rgb * 0.50 + c2.rgb * 0.50, c2.rgb, smoothstep(0.0, 0.95, uv.y));
	// glow orb (sun / light source)
	vec2 o = vec2((0.25 + 0.5 * fract(seed * 0.37)) * aspect, 0.30);
	float g = exp(-pow(length((p - o) * vec2(1.0, 1.15)), 2.0) * 5.0);
	col += c1.rgb * g * 0.95;
	// haze
	col += c1.rgb * fbm(p * vec2(1.4, 3.0) + seed) * 0.10 * (1.0 - uv.y);
	// three ridge layers, far to near
	for (int i = 0; i < 3; i++) {
		float fi = float(i);
		float h = 0.52 + fi * 0.13 + (fbm(vec2(p.x * (2.2 + fi * 1.3) + seed * 3.1 + fi * 7.0, fi)) - 0.5) * (0.46 - fi * 0.08);
		float m = smoothstep(h, h + 0.005, uv.y);
		vec3 layer = mix(c2.rgb * 0.60, c2.rgb * 0.10, fi / 2.0) + c1.rgb * 0.07 * (1.0 - fi / 2.0);
		col = mix(col, layer, m);
	}
	return col;
}

void fragment() {
	vec2 base_uv = UV;
	float fade = 1.0;
	if (reflection) {
		base_uv = vec2(UV.x, 1.0 - UV.y * refl_part);
		fade = pow(1.0 - UV.y, 1.7) * refl_strength;
	}
	vec2 uv = (base_uv - 0.5) / zoom + 0.5;
	vec3 col = has_tex ? texture(tex, uv).rgb : landscape(uv);
	col *= mix(1.0, 0.30, smoothstep(0.60, 1.0, base_uv.y) * bottom_dark);
	col = mix(col, vec3(0.03, 0.03, 0.05), dim);
	float a = 1.0;
	if (radius > 0.0) {
		vec2 p = (UV - 0.5) * rect_size;
		vec2 q = abs(p) - (rect_size * 0.5 - vec2(radius));
		float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
		a = 1.0 - smoothstep(-1.0, 1.0, d);
	}
	COLOR = vec4(col, a * fade);
}
