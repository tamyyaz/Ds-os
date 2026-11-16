shader_type canvas_item;
// Rounded card art, darker at the bottom (where the title sits) and dimmed when not selected.

uniform vec2 rect_size = vec2(360.0, 520.0);
uniform float radius = 18.0;
uniform float dim : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	vec2 p = (UV - 0.5) * rect_size;
	vec2 q = abs(p) - (rect_size * 0.5 - vec2(radius));
	float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
	float a = 1.0 - smoothstep(-1.0, 1.0, d);
	vec4 c = texture(TEXTURE, UV);
	c.rgb *= mix(1.0, 0.35, smoothstep(0.62, 1.0, UV.y));
	c.rgb = mix(c.rgb, vec3(0.03, 0.03, 0.05), dim);
	COLOR = vec4(c.rgb, c.a * a);
}
