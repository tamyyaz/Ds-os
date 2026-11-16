shader_type canvas_item;
// Dark background with a soft glow in the colour of the selected game.

uniform vec4 tint : source_color = vec4(0.54, 0.72, 1.0, 1.0);
uniform vec4 base : source_color = vec4(0.04, 0.043, 0.06, 1.0);

void fragment() {
	vec2 uv = UV;
	float t = TIME * 0.2;
	float g1 = exp(-pow(length((uv - vec2(0.5 + 0.04 * sin(t), 0.45)) * vec2(1.0, 1.5)), 2.0) * 3.2);
	float g2 = exp(-pow(length((uv - vec2(0.12, 0.95)) * vec2(1.0, 1.2)), 2.0) * 6.0);
	vec3 col = base.rgb + tint.rgb * (g1 * 0.30 + g2 * 0.12);
	float vig = smoothstep(1.1, 0.3, length((uv - 0.5) * vec2(1.0, 0.9)));
	col *= mix(0.55, 1.0, vig);
	COLOR = vec4(col, 1.0);
}
