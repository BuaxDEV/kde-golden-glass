# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cabecera C++ con los tokens que usan el estilo y la decoración.

Los .kcfg la incluyen y la usan como valores por defecto
(`<default code="true">GoldenGlass::Tokens::…</default>`): el usuario puede
cambiarlos desde los módulos de configuración, pero de fábrica salen de
tokens/goldenglass.toml. CMake la genera al configurar (ver CMakeLists.txt).
"""

from __future__ import annotations

from pathlib import Path

import plasma_theme

# Orden de los <choice> en los .kcfg: el índice es el valor del enum.
SHADOW_SIZES = ("ShadowNone", "ShadowSmall", "ShadowMedium", "ShadowLarge", "ShadowVeryLarge")
TITLE_ALIGNMENTS = ("AlignLeft", "AlignCenter", "AlignCenterFullWidth", "AlignRight")


def _shadow_size_index(px: int) -> int:
    """Tamaño de sombra en px → opción de ShadowSize más cercana."""
    if px <= 0:
        return 0
    for index, limit in enumerate((24, 40, 56), start=1):
        if px <= limit:
            return index
    return 4


def _shadow_strength(alpha: float) -> int:
    """Opacidad 0..1 → ShadowStrength (rango del .kcfg: 25..255)."""
    return max(25, min(255, round(alpha * 255)))


def _argb(value: str) -> str:
    """#RRGGBB[AA] → literal 0xAARRGGBB (formato de QColor::fromRgba)."""
    h = value.lstrip("#")
    alpha = h[6:8] if len(h) == 8 else "FF"
    return "0x" + (alpha + h[:6]).upper() + "u"


def header(tokens: dict) -> str:
    rad = tokens["radius"]
    tl = tokens["traffic_lights"]
    shadow = tokens["shadow"]["active"]
    glass = round(plasma_theme.glass_alpha(tokens) * 100)
    align = tokens["decoration"]["title_alignment"]
    if align not in TITLE_ALIGNMENTS:
        raise SystemExit(f"decoration.title_alignment inválido: {align!r} (opciones: {', '.join(TITLE_ALIGNMENTS)})")

    values = [
        ("Radios (px)", None, None),
        ("ControlRadius", rad["control"], "botones, campos, pestañas, selección"),
        ("MenuRadius", rad["menu"], "menús y listas desplegables"),
        ("WindowRadius", rad["window"], "esquinas de ventana (decoración y blur)"),
        ("Anillo de foco de los campos de texto", None, None),
        ("FocusRingWidth", int(tokens["focus_ring"]["width"]), "ancho (px)"),
        ("FocusRingAlpha", float(tokens["focus_ring"]["alpha"]), "opacidad del acento"),
        ("Vidrio", None, None),
        ("GlassOpacity", glass, "% de opacidad en el nivel por defecto del slider"),
        ("GlassDefaultLevel", float(tokens["glass"]["default_level"]), "nivel del slider de fábrica (0..1)"),
        ("GlassNotchClear", float(tokens["glass"]["notch"]["clear"]["position"]), "muesca «más claro»"),
        ("GlassNotchMedium", float(tokens["glass"]["notch"]["medium"]["position"]), "muesca «medio»"),
        ("GlassNotchOpaque", float(tokens["glass"]["notch"]["opaque"]["position"]), "muesca «más opaco»"),
        ("Sombras de ventana", None, None),
        ("ShadowSize", _shadow_size_index(shadow["size"]),
         f"{SHADOW_SIZES[_shadow_size_index(shadow['size'])]} ({shadow['size']} px)"),
        ("ShadowStrength", _shadow_strength(shadow["strength"]), f"{shadow['strength']} de opacidad"),
        ("Decoración", None, None),
        ("TitleAlignment", TITLE_ALIGNMENTS.index(align), align),
        ("GlassTitleBar", bool(tokens["decoration"]["glass_titlebar"]), "barra de título translúcida como la toolbar"),
        ("Refracción (efecto de KWin goldenglass_glass, px lógicos)", None, None),
        ("RefractionEdge", float(tokens["glass"]["refraction"]["edge"]), "ancho de la zona curvada"),
        ("RefractionStrength", float(tokens["glass"]["refraction"]["strength"]), "desplazamiento en el borde"),
        ("RefractionOpaqueFactor", float(tokens["glass"]["refraction"]["opaque_factor"]), "fracción con el vidrio más opaco"),
        ("RefractionDispersion", float(tokens["glass"]["refraction"]["dispersion"]), "separación de colores"),
        ("RefractionSpecular", float(tokens["glass"]["refraction"]["specular"]), "brillo del filo"),
        ("RefractionClarity", float(tokens["glass"]["refraction"]["clarity"]), "fondo nítido en el borde"),
        ("RefractionTint", float(tokens["glass"]["refraction"]["tint"]), "tinte adaptativo"),
        ("Dock (valores de fábrica del módulo «Dock»)", None, None),
        ("DockIconSize", int(tokens["plasma"]["dock_icon_size"]), "tamaño de los iconos (px)"),
        ("DockMagnification", bool(tokens["dock"]["magnification"]), "ampliación bajo el cursor"),
        ("DockMagnificationSize", int(tokens["dock"]["magnification_size"]), "tamaño del icono ampliado (px)"),
        ("DockShowRecent", bool(tokens["dock"]["show_recent"]), "apps recientes en el dock"),
        ("Menús", None, None),
        ("MenuIcons", bool(tokens["menu"]["show_icons"]), "iconos junto a los comandos de los menús"),
        ("Semáforos y colores fijos (px, 0xAARRGGBB)", None, None),
        ("TrafficLightDiameter", tl["diameter"], "diámetro"),
        ("TrafficLightGap", tl["gap"], "separación entre bordes"),
        ("TrafficLightInactiveColored", bool(tl["inactive_colored"]), "en color también sin foco"),
    ]
    colors = [
        ("TrafficLightClose", tl["close"]),
        ("TrafficLightCloseBorder", tl["close_border"]),
        ("TrafficLightMinimize", tl["minimize"]),
        ("TrafficLightMinimizeBorder", tl["minimize_border"]),
        ("TrafficLightZoom", tl["zoom"]),
        ("TrafficLightZoomBorder", tl["zoom_border"]),
        ("TrafficLightCloseGlyph", tl["close_glyph"]),
        ("TrafficLightMinimizeGlyph", tl["minimize_glyph"]),
        ("TrafficLightZoomGlyph", tl["zoom_glyph"]),
        ("TrafficLightInactiveLight", tokens["light"]["traffic_light_inactive"]),
        ("TrafficLightInactiveDark", tokens["dark"]["traffic_light_inactive"]),
        ("SidebarLight", tokens["light"]["sidebar"]),
        ("SidebarDark", tokens["dark"]["sidebar"]),
        ("SeparatorLight", tokens["light"]["separator"]),
        ("SeparatorDark", tokens["dark"]["separator"]),
    ]

    out = [
        "// Generado por tools/gen_tokens.py desde tokens/goldenglass.toml — NO EDITAR",
        # REUSE-IgnoreStart
        "// SPDX-License-Identifier: GPL-3.0-or-later",
        # REUSE-IgnoreEnd
        "#pragma once",
        "",
        "namespace GoldenGlass::Tokens",
        "{",
    ]
    for name, value, comment in values:
        if value is None:
            out += ["", f"// {name}"]
        else:
            if isinstance(value, bool):
                out.append(f"inline constexpr bool {name} = {str(value).lower()}; // {comment}")
            elif isinstance(value, float):
                out.append(f"inline constexpr double {name} = {value!r}; // {comment}")
            else:
                out.append(f"inline constexpr int {name} = {value}; // {comment}")
    for name, value in colors:
        out.append(f"inline constexpr unsigned int {name} = {_argb(value)}; // {value}")
    out += ["}", ""]
    return "\n".join(out)


def write(tokens: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = header(tokens)
    # No reescribir si no cambia: evita recompilar todo en cada configure.
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")
    return path
