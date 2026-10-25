# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cabecera C++ con los tokens que usan el estilo y la decoración.

Los .kcfg la incluyen y la usan como valores por defecto
(`<default code="true">GoldenGlass::Tokens::…</default>`): el usuario puede
cambiarlos desde los módulos de configuración, pero de fábrica salen de
tokens/goldenglass.toml. CMake la genera al configurar (ver CMakeLists.txt).
"""

from __future__ import annotations

import json
from pathlib import Path

import plasma_theme
from ggcommon import Color

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


def _shadow_size(tokens: dict, option: str) -> list[tuple]:
    """Constantes de una opción de ShadowSize: ShadowSmallRadius, … (px, 0..1)."""
    name = option.removeprefix("Shadow")
    key = "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")
    s = tokens["shadow"]["sizes"][key]
    return [
        (f"Shadow{name}Offset", int(s["offset"]), f"shadow.sizes.{key}: desplazamiento vertical del conjunto"),
        (f"Shadow{name}Radius", int(s["radius"]), "sombra principal: radio"),
        (f"Shadow{name}Alpha", float(s["alpha"]), "sombra principal: opacidad"),
        (f"Shadow{name}AmbientOffset", int(s["ambient_offset"]), "segunda sombra: desplazamiento vertical"),
        (f"Shadow{name}AmbientRadius", int(s["ambient_radius"]), "segunda sombra: radio"),
        (f"Shadow{name}AmbientAlpha", float(s["ambient_alpha"]), "segunda sombra: opacidad"),
    ]


def _camel(key: str) -> str:
    """search_handle_end → SearchHandleEnd."""
    return "".join(word.title() for word in key.split("_"))


def _alpha8(alpha: float) -> int:
    """Opacidad 0..1 → 0..255 (canal alfa de QColor)."""
    return round(alpha * 255)


def _argb(value: str) -> str:
    """#RRGGBB[AA] → literal 0xAARRGGBB (formato de QColor::fromRgba)."""
    c = Color.parse(value)
    return f"0x{c.alpha8:02X}{c.r:02X}{c.g:02X}{c.b:02X}u"


def header(tokens: dict) -> str:
    rad = tokens["radius"]
    tl = tokens["traffic_lights"]
    shadow = tokens["shadow"]["active"]
    inactive = tokens["shadow"]["inactive"]
    glass = round(plasma_theme.glass_alpha(tokens) * 100)
    finder = tokens["finder"]
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
        ("GlassSnapDistance", float(tokens["glass"]["snap_distance"]), "imán de las muescas del slider"),
        ("GlassKeyboardApplyMs", int(tokens["glass"]["keyboard_apply_ms"]), "pausa antes de aplicar con el teclado"),
        ("Barra de menús", None, None),
        ("MenubarBackground", bool(tokens["plasma"]["menubar_background"]), "franja de vidrio tras la barra de menús"),
        ("MenubarInactiveOpacity", float(tokens["plasma"]["menubar_inactive_opacity"]), "opacidad en las pantallas sin la ventana activa"),
        ("Sombras de ventana", None, None),
        ("ShadowSize", _shadow_size_index(shadow["size"]),
         f"{SHADOW_SIZES[_shadow_size_index(shadow['size'])]} ({shadow['size']} px)"),
        ("ShadowStrength", _shadow_strength(shadow["strength"]), f"{shadow['strength']} de opacidad"),
        ("InactiveShadowSize", _shadow_size_index(inactive["size"]),
         f"sin foco: {SHADOW_SIZES[_shadow_size_index(inactive['size'])]} ({inactive['size']} px)"),
        ("InactiveShadowStrength", _shadow_strength(inactive["strength"]), f"sin foco: {inactive['strength']} de opacidad"),
        ("ShadowOutlineAlpha", float(tokens["shadow"]["outline_alpha"]), "contorno de la ventana (× la fuerza)"),
        *(item for size in SHADOW_SIZES[1:] for item in _shadow_size(tokens, size)),
        ("Animaciones (estilo y decoración)", None, None),
        ("AnimationsDuration", int(tokens["animation"]["controls_ms"]), "controles de las apps y botones de la ventana (ms)"),
        ("Decoración", None, None),
        ("TitleAlignment", TITLE_ALIGNMENTS.index(align), align),
        ("GlassTitleBar", bool(tokens["decoration"]["glass_titlebar"]), "barra de título translúcida como la toolbar"),
        ("FloatingTitlebar", bool(tokens["decoration"]["floating_titlebar"]), "barra de título flotante (decoración y blur del estilo)"),
        ("DecorationTitleGradientLighter", int(tokens["decoration"]["title_gradient_lighter"]),
         "degradado de la barra de título (QColor::lighter)"),
        ("DecorationHighlightThreshold", int(tokens["decoration"]["highlight_threshold"]), "filo claro bajo este qGray"),
        ("DecorationHighlightAlpha", _alpha8(tokens["decoration"]["highlight_alpha"]), "opacidad del filo claro (0..255)"),
        ("Estilo de aplicaciones", None, None),
        ("StyleProgressBarBusyStepDuration", int(tokens["style"]["progress_busy_step_ms"]), "progreso indeterminado (ms)"),
        ("DolphinViewOpacity", round(tokens["style"]["dolphin_view_alpha"] * 100), "% de opacidad de la vista de Dolphin"),
        ("ListHoverAlpha", float(tokens["plasma"]["item_hover_alpha"]), "resaltado de listas (color de texto, como Plasma)"),
        ("ListSelectedHoverLighter", int(tokens["style"]["list_selected_hover_lighter"]), "selección bajo el cursor (QColor::lighter)"),
        ("Refracción (efecto de KWin goldenglass_glass, px lógicos)", None, None),
        ("RefractionEdge", float(tokens["glass"]["refraction"]["edge"]), "ancho de la zona curvada"),
        ("RefractionStrength", float(tokens["glass"]["refraction"]["strength"]), "desplazamiento en el borde"),
        ("RefractionOpaqueFactor", float(tokens["glass"]["refraction"]["opaque_factor"]), "fracción con el vidrio más opaco"),
        ("RefractionDispersion", float(tokens["glass"]["refraction"]["dispersion"]), "separación de colores"),
        ("RefractionSpecular", float(tokens["glass"]["refraction"]["specular"]), "brillo del filo"),
        ("RefractionClarity", float(tokens["glass"]["refraction"]["clarity"]), "fondo nítido en el borde"),
        ("RefractionTint", float(tokens["glass"]["refraction"]["tint"]), "tinte adaptativo"),
        ("RefractionEdgeMaxFraction", float(tokens["glass"]["refraction"]["edge_max_fraction"]),
         "tope de la zona curvada (fracción del lado menor)"),
        ("RefractionRimWidth", float(tokens["glass"]["refraction"]["rim_width"]), "ancho del filo (fracción de edge)"),
        ("RefractionRimBottom", float(tokens["glass"]["refraction"]["rim_bottom"]), "brillo del filo abajo"),
        ("Dock (valores de fábrica del módulo «Dock»)", None, None),
        ("DockIconSize", int(tokens["plasma"]["dock_icon_size"]), "tamaño de los iconos (px)"),
        ("DockMagnification", bool(tokens["dock"]["magnification"]), "ampliación bajo el cursor"),
        ("DockMagnificationSize", int(tokens["dock"]["magnification_size"]), "tamaño del icono ampliado (px)"),
        ("DockShowRecent", bool(tokens["dock"]["show_recent"]), "apps recientes en el dock"),
        ("DockIconSizeMin", int(tokens["dock"]["icon_size_min"]), "tamaño de los iconos: mínimo (px)"),
        ("DockIconSizeMax", int(tokens["dock"]["icon_size_max"]), "tamaño de los iconos: máximo (px)"),
        ("DockMagnificationSizeMax", int(tokens["dock"]["magnification_size_max"]),
         "ampliación: máximo (px; el mínimo es el tamaño del icono)"),
        ("Menús", None, None),
        ("MenuIcons", bool(tokens["menu"]["show_icons"]), "iconos junto a los comandos de los menús"),
        ("Accesibilidad (valores de fábrica de goldenglassrc [Accessibility])", None, None),
        ("AccessibilityShowBorders", bool(tokens["accessibility"]["show_borders"]), "ShowBorders: «Mostrar bordes»"),
        ("AccessibilityReduceTransparency", bool(tokens["accessibility"]["reduce_transparency"]),
         "ReduceTransparency: «Reducir transparencia»"),
        ("AccessibilityReduceMotion", bool(tokens["accessibility"]["reduce_motion"]), "ReduceMotion: «Reducir movimiento»"),
        ("AccessibilityReduceTransparencyAlpha", float(tokens["accessibility"]["reduce_transparency_alpha"]),
         "opacidad del vidrio con «Reducir transparencia» (0..1)"),
        ("Finder (Dolphin con la barra de título integrada; px lógicos, ms)", None, None),
        ("IntegratedTitleBarApps", ",".join(finder["apps"]), "app_id separados por comas"),
        ("FinderToolBarHeight", int(finder["toolbar_height"]), "primera fila: semáforos + toolbar"),
        ("FinderCapsuleHeight", int(finder["capsule_height"]), "alto de las cápsulas"),
        ("FinderCapsuleGap", int(finder["capsule_gap"]), "entre cápsulas"),
        ("FinderButtonWidth", int(finder["button_width"]), "cada botón de una cápsula"),
        ("FinderIconSize", int(finder["icon_size"]), "glifos de la toolbar"),
        ("FinderMenuArrow", int(finder["menu_arrow"]), "chevron de los botones con menú"),
        ("FinderTitleScale", float(finder["title_scale"]), "título respecto al texto normal"),
        ("FinderSelectedInset", int(finder["selected_inset"]), "píldora del control segmentado"),
        ("FinderPressScale", float(finder["press_scale"]), "escala al pulsar"),
        ("FinderPressMs", int(finder["press_ms"]), "pulsación"),
        ("FinderReleaseMs", int(finder["release_ms"]), "rebote al soltar"),
        ("FinderReleaseOvershoot", float(finder["release_overshoot"]), "rebote (Easing.OutBack)"),
        ("FinderSlideMs", int(finder["slide_ms"]), "píldora del control segmentado"),
        ("FinderSlideOvershoot", float(finder["slide_overshoot"]), "resorte de esa píldora"),
        ("FinderDividerHeight", int(finder["divider_height"]), "líneas dentro de las cápsulas"),
        ("FinderHeaderPadding", int(finder["header_padding"]), "margen del texto de la cabecera"),
        ("FinderHeaderArrowWidth", int(finder["header_arrow_width"]), "hueco del chevron de la cabecera"),
        ("FinderHoverMs", int(finder["hover_ms"]), "resaltado al pasar el ratón"),
        ("FinderSidebarMargin", int(finder["sidebar_margin"]), "borde de la barra lateral → selección"),
        ("FinderSidebarIconPadding", int(finder["sidebar_icon_padding"]), "selección → icono"),
        ("FinderSidebarRowHeight", int(finder["sidebar_row_height"]), "paso entre filas de la barra lateral"),
        ("FinderSidebarSelectionRadius", int(finder["sidebar_selection_radius"]), "esquinas de esa selección"),
        ("FinderSidebarSlideMs", int(finder["sidebar_slide_ms"]), "deslizamiento de esa selección"),
        ("FinderRowInset", int(finder["row_inset"]), "franjas y selección de la lista"),
        ("FinderRowRadius", int(finder["row_radius"]), "esquinas de franjas y selección"),
        ("FinderListIconSize", int(finder["list_icon_size"]), "iconos de la lista"),
        ("FinderSearchWidth", int(finder["search_width"]), "campo de búsqueda en la toolbar"),
        *((f"FinderGlyph{_camel(key)}", value, f"finder.glyphs.{key}")
          for key, value in finder["glyphs"].items()),
        ("Semáforos y colores fijos (px, 0xAARRGGBB)", None, None),
        ("TrafficLightDiameter", tl["diameter"], "diámetro"),
        ("TrafficLightGap", tl["gap"], "separación entre bordes"),
        ("TrafficLightInactiveColored", bool(tl["inactive_colored"]), "en color también sin foco"),
        ("TrafficLightPressScale", float(tl["press_scale"]), "tamaño al pulsar"),
        ("TrafficLightInactiveShine", float(tl["inactive_shine"]), "brillos sin foco (fracción)"),
        ("TrafficLightHighlightTopAlpha", _alpha8(tl["gem_highlight_top"]), "brillo de arriba, al empezar (0..255)"),
        ("TrafficLightHighlightTopEndAlpha", _alpha8(tl["gem_highlight_top_end"]), "brillo de arriba, al acabar (0..255)"),
        ("TrafficLightHighlightBottomAlpha", _alpha8(tl["gem_highlight_bottom"]), "brillo de abajo (0..255)"),
        ("TrafficLightShadowAlpha", _alpha8(tl["gem_shadow_alpha"]), "sombra (0..255)"),
        ("TrafficLightShadowInactiveAlpha", _alpha8(tl["gem_shadow_inactive_alpha"]), "sombra sin foco (0..255)"),
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
        ("ShadowColor", tokens["shadow"]["color"]),
        ("BootDarkBackground", tokens["boot"]["dark"]["background"]),
        ("BootLightBackground", tokens["boot"]["light"]["background"]),
        ("SidebarLight", tokens["light"]["sidebar"]),
        ("SidebarDark", tokens["dark"]["sidebar"]),
        ("SeparatorLight", tokens["light"]["separator"]),
        ("SeparatorDark", tokens["dark"]["separator"]),
        *((f"Finder{key.title().replace('_', '')}{variant.title()}", tokens[variant][f"finder_{key}"])
          for key in ("capsule", "capsule_border", "hover", "selected", "stripe", "sidebar_selected")
          for variant in ("light", "dark")),
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
            elif isinstance(value, str):
                out.append(f"inline constexpr char {name}[] = {json.dumps(value)}; // {comment}")
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
