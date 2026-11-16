shader_type canvas_item;
// Base layer under the hero art: dark with a soft glow in the colour of the selected game.

uniform vec4 tint : source_color = vec4(0.54, 0.72, 1.0, 1.0);
uniform vec4 base : source_color = vec4(0.04, 0.043, 0.06, 1.0);

void fragment() {
	vec2 uv = UV;
	float g1 = exp(-pow(length((uv - vec2(0.5, 0.45)) * vec2(1.0, 1.5)), 2.0) * 3.2);
	vec3 col = base.rgb + tint.rgb * g1 * 0.22;
	COLOR = vec4(col, 1.0);
}
