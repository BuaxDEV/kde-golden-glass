#version 140
// SPDX-FileCopyrightText: 2026 GoldenGlass contributors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Paso final del vidrio de GoldenGlass: el fondo ya difuminado (dual Kawase,
// como el Blur de KWin) con la refracción de Liquid Glass. Todo en píxeles
// del dispositivo, relativos al rectángulo de fondo.
//   - lente: cerca del borde redondeado, el fondo se toma de más adentro a lo
//     largo de la normal (más fuerte cuanto más cerca del borde) y deja ver el
//     fondo nítido: el difuminado lo borraría (el centro sigue esmerilado)
//   - dispersión: rojo y azul se desplazan algo más y algo menos que el verde
//   - filo de luz: brillo en el borde, más arriba que abajo
//   - tinte adaptativo: la luminancia del fondo se acerca a la media

uniform sampler2D texUnit;       // fondo difuminado (media resolución)
uniform sampler2D sharpTexture;  // fondo sin difuminar
uniform mat4 colorMatrix;
uniform float offset;
uniform vec2 halfpixel;
uniform vec4 box;          // centro y semiextensiones de la forma
uniform vec4 cornerRadius; // arriba-izq., arriba-der., abajo-izq., abajo-der.
uniform float opacity;
uniform vec2 backgroundSize;
uniform float edge;
uniform float strength;
uniform float dispersion;
uniform float specular;
uniform float tint;
uniform float clarity;

in vec2 uv;
in vec2 vertex;

out vec4 fragColor;

// sdfRoundedBox de KWin (src/opengl/sdf.glsl, :/opengl/ en libkwin; KWin
// resuelve el #include): negativa dentro de la forma
#include "sdf.glsl"

float shape(vec2 p)
{
    return sdfRoundedBox(p, box.xy, box.zw, cornerRadius);
}

// último paso del dual Kawase (el del pase en pantalla del Blur)
vec4 blurred(vec2 tc)
{
    vec4 sum = texture(texUnit, tc + vec2(-halfpixel.x * 2.0, 0.0) * offset);
    sum += texture(texUnit, tc + vec2(-halfpixel.x, halfpixel.y) * offset) * 2.0;
    sum += texture(texUnit, tc + vec2(0.0, halfpixel.y * 2.0) * offset);
    sum += texture(texUnit, tc + vec2(halfpixel.x, halfpixel.y) * offset) * 2.0;
    sum += texture(texUnit, tc + vec2(halfpixel.x * 2.0, 0.0) * offset);
    sum += texture(texUnit, tc + vec2(halfpixel.x, -halfpixel.y) * offset) * 2.0;
    sum += texture(texUnit, tc + vec2(0.0, -halfpixel.y * 2.0) * offset);
    sum += texture(texUnit, tc + vec2(-halfpixel.x, -halfpixel.y) * offset) * 2.0;
    return sum / 12.0;
}

void main(void)
{
    float d = shape(vertex);

    // normal hacia fuera (gradiente de la distancia)
    vec2 grad = vec2(shape(vertex + vec2(0.5, 0.0)) - shape(vertex - vec2(0.5, 0.0)),
                     shape(vertex + vec2(0.0, 0.5)) - shape(vertex - vec2(0.0, 0.5)));
    vec2 n = dot(grad, grad) > 0.0 ? normalize(grad) : vec2(0.0);

    // lente: 1 en el borde, 0 a «edge» píxeles hacia dentro
    float bend = edge > 0.0 ? 1.0 - clamp(-d / edge, 0.0, 1.0) : 0.0;
    bend *= bend;
    vec2 shift = -n * strength * bend;              // píxeles: hacia dentro
    vec2 toUv = vec2(1.0 / backgroundSize.x, -1.0 / backgroundSize.y); // v crece hacia arriba

    vec4 color = blurred(uv + shift * toUv);
    if (bend > 0.0 && clarity > 0.0) {
        vec4 sharp = texture(sharpTexture, uv + shift * toUv);
        if (dispersion > 0.0) {
            sharp.r = texture(sharpTexture, uv + shift * (1.0 + dispersion) * toUv).r;
            sharp.b = texture(sharpTexture, uv + shift * (1.0 - dispersion) * toUv).b;
        }
        color = mix(color, sharp, clarity * bend);
    }
    color *= colorMatrix;

    float luminance = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));
    color.rgb = clamp(color.rgb + (0.5 - luminance) * tint, 0.0, 1.0);

    // filo de luz: estrecho, y más fuerte donde la normal mira hacia arriba
    float rim = edge > 0.0 ? 1.0 - smoothstep(0.0, edge * 0.3, -d) : 0.0;
    float top = clamp(-n.y, 0.0, 1.0);
    color.rgb = min(color.rgb + specular * rim * (0.35 + 0.65 * top), 1.0);

    color *= opacity;

    // borde suave de la forma redondeada
    float df = fwidth(d);
    color *= 1.0 - clamp(0.5 + d / max(df, 1e-4), 0.0, 1.0);
    fragColor = color;
}
