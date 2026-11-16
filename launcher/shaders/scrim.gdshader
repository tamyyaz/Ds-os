shader_type canvas_item;
// Darkens the hero art where text sits: the start side (right in Arabic), the bottom row, a little at the top.

uniform bool rtl = true;

void fragment() {
	float sx = rtl ? 1.0 - UV.x : UV.x;
	float side = pow(1.0 - smoothstep(0.0, 0.80, sx), 1.3) * 0.90;
	float bottom = smoothstep(0.42, 0.92, UV.y) * 0.96;
	float top = (1.0 - smoothstep(0.0, 0.26, UV.y)) * 0.68;
	float a = clamp(max(side, bottom) + top, 0.0, 1.0);
	COLOR = vec4(0.039, 0.043, 0.059, a);
}
