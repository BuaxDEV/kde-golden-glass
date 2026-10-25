#version 140
// SPDX-FileCopyrightText: 2026 GoldenGlass contributors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Edge of the glass, drawn over the window once it is painted (spike SP-01):
// under it, the Plasma Style fill would hide most of it. Along the rounded
// outline a thin band darkens what is below (macOS 27's improved contrast)
// and the light rim peaks right after it, brighter where the normal points
// up. Device pixels relative to the background rectangle, like glass.frag.

uniform vec4 box;          // centre and half extents of the shape
uniform vec4 cornerRadius; // top left, top right, bottom left, bottom right
uniform float opacity;
uniform float shade;       // darkening of the outer band (0..1)
uniform float shadeWidth;
uniform float specular;
uniform float rimWidth;    // fall-off of the rim after the band
uniform float rimBottom;   // rim where the normal points down
uniform float rimTopGain;  // added where it points up (1 - rimBottom)

in vec2 vertex;

out vec4 fragColor;

// KWin's sdfRoundedBox (src/opengl/sdf.glsl): negative inside the shape
#include "sdf.glsl"

float shape(vec2 p)
{
    return sdfRoundedBox(p, box.xy, box.zw, cornerRadius);
}

void main(void)
{
    float d = shape(vertex);
    float depth = -d;

    vec2 grad = vec2(shape(vertex + vec2(0.5, 0.0)) - shape(vertex - vec2(0.5, 0.0)),
                     shape(vertex + vec2(0.0, 0.5)) - shape(vertex - vec2(0.0, 0.5)));
    vec2 n = dot(grad, grad) > 0.0 ? normalize(grad) : vec2(0.0);
    float up = clamp(-n.y, 0.0, 1.0);

    float pastShade = smoothstep(shadeWidth - 0.5, shadeWidth + 0.5, depth);
    float darkening = shade * (1.0 - pastShade);
    float rim = pastShade * (1.0 - smoothstep(shadeWidth, shadeWidth + rimWidth, depth));
    float light = specular * rim * (rimBottom + rimTopGain * up);

    float coverage = 1.0 - clamp(0.5 + d / max(fwidth(d), 1e-4), 0.0, 1.0);
    // premultiplied over: alpha multiplies what is below, the colour adds to it
    fragColor = vec4(vec3(light), darkening) * opacity * coverage;
}
