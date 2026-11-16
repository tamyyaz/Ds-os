shader_type canvas_item;
// Floor reflection: the bottom of the card art, mirrored, fading out downwards.

uniform sampler2D cover : filter_linear;
uniform float strength : hint_range(0.0, 1.0) = 0.4;
uniform float dim : hint_range(0.0, 1.0) = 0.0;
uniform float part = 0.38; // how much of the card height is mirrored

void fragment() {
	vec4 c = texture(cover, vec2(UV.x, 1.0 - UV.y * part));
	c.rgb *= mix(1.0, 0.35, smoothstep(0.0, 0.2, 1.0 - UV.y * part));
	c.rgb = mix(c.rgb, vec3(0.03, 0.03, 0.05), dim);
	float fade = pow(1.0 - UV.y, 1.6);
	COLOR = vec4(c.rgb, c.a * fade * strength);
}
