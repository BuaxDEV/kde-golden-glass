#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Genera los artefactos de GoldenGlass a partir de tokens/goldenglass.toml.

Salidas (en build/, no versionado):
  build/color-schemes/GoldenGlassLight.colors
  build/color-schemes/GoldenGlassDark.colors
  build/tokens.json
  build/plasma/desktoptheme/GoldenGlass/   (Plasma Style)
  build/plasma/look-and-feel/org.goldenglass.{light,dark}.desktop/
  build/plasma/plasmoids/<id>/            (plasmoids con sus traducciones)
  build/plasma/shells/org.goldenglass.desktop/  (shell: pantalla de bloqueo y panel)
  build/wallpapers/GoldenGlass/           (fondo día/noche; se cachea)
  build/cursors/GoldenGlass-cursors/      (tema de cursores; se cachea)
  build/icons/GoldenGlass{,-Dark}/        (tema de iconos)
  build/gtk/GoldenGlass/ y libadwaita.css (GTK3/GTK4 sobre adw-gtk3)
  build/sounds/GoldenGlass/               (tema de sonidos; se cachea)
  build/plymouth/goldenglass{,-light}/    (temas de Plymouth; se cachea)
  build/login/sddm/GoldenGlass/           (tema de SDDM)
  build/kwin/windows.json                 (factory values for goldenglass-windows)

Uso:
  python3 tools/gen_tokens.py [--tokens RUTA] [--out DIR]
  python3 tools/gen_tokens.py --cxx-header RUTA   # solo la cabecera C++ (CMake)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cursors  # noqa: E402
import cxx_tokens  # noqa: E402
import gtk  # noqa: E402
import icons  # noqa: E402
import login  # noqa: E402
import lookandfeel  # noqa: E402
import plasma_theme  # noqa: E402
import plasmoids  # noqa: E402
import plymouth  # noqa: E402
import shell  # noqa: E402
import sounds  # noqa: E402
import wallpaper  # noqa: E402
import windows  # noqa: E402
from ggcommon import Color, load_tokens  # noqa: E402

VARIANTS = {
    "light": ("GoldenGlassLight", "GoldenGlass Light"),
    "dark": ("GoldenGlassDark", "GoldenGlass Dark"),
}


# --- .colors ----------------------------------------------------------------

def color_set(p: dict[str, Color], bg: Color, bg_alt: Color) -> dict[str, str]:
    """Bloque [Colors:*] estándar para un fondo dado."""
    return {
        "BackgroundAlternate": bg_alt.kde(),
        "BackgroundNormal": bg.kde(),
        "DecorationFocus": p["accent"].kde(),
        "DecorationHover": p["accent"].kde(),
        "ForegroundActive": p["accent"].kde(),
        "ForegroundInactive": p["label_secondary"].over(bg).kde(),
        "ForegroundLink": p["link"].kde(),
        "ForegroundNegative": p["negative"].kde(),
        "ForegroundNeutral": p["neutral"].kde(),
        "ForegroundNormal": p["label"].over(bg).kde(),
        "ForegroundPositive": p["positive"].kde(),
        "ForegroundVisited": p["visited"].kde(),
    }


def build_colors(tokens: dict, variant: str) -> str:
    p = {k: Color.parse(v) for k, v in tokens[variant].items()}
    dark = {k: Color.parse(v) for k, v in tokens["dark"].items()}
    scheme_id, scheme_name = VARIANTS[variant]

    # Selección: texto y semánticos sobre el acento.
    on_accent = p["accent_fg"]
    selection = {
        "BackgroundAlternate": p["accent"].mix(p["view"], 0.5).kde(),
        "BackgroundNormal": p["accent"].kde(),
        "DecorationFocus": p["accent"].kde(),
        "DecorationHover": p["accent"].kde(),
        "ForegroundActive": on_accent.kde(),
        "ForegroundInactive": on_accent.mix(p["accent"], 0.3).kde(),
        "ForegroundLink": on_accent.kde(),
        "ForegroundNegative": p["negative"].mix(on_accent, 0.5).kde(),
        "ForegroundNeutral": p["neutral"].mix(on_accent, 0.5).kde(),
        "ForegroundNormal": on_accent.kde(),
        "ForegroundPositive": p["positive"].mix(on_accent, 0.5).kde(),
        "ForegroundVisited": on_accent.kde(),
    }

    # Complementary es oscuro en ambas variantes (OSD, bloqueo): texto de la
    # paleta oscura.
    complementary = color_set(dark, p["complementary"], p["complementary"].mix(dark["window"], 0.3))
    for key in ("DecorationFocus", "DecorationHover", "ForegroundActive"):
        complementary[key] = p["accent"].kde()

    sections: dict[str, dict[str, str]] = {
        "ColorEffects:Disabled": {
            "Color": "56,56,56", "ColorAmount": "0", "ColorEffect": "0",
            "ContrastAmount": "0.65", "ContrastEffect": "1",
            "IntensityAmount": "0.1", "IntensityEffect": "2",
        },
        "ColorEffects:Inactive": {
            "ChangeSelectionColor": "true", "Color": "112,111,110",
            "ColorAmount": "0.025", "ColorEffect": "2", "ContrastAmount": "0.1",
            "ContrastEffect": "2", "Enable": "false",
            "IntensityAmount": "0", "IntensityEffect": "0",
        },
        "Colors:Button": color_set(p, p["button"], p["button_alt"]),
        "Colors:Complementary": complementary,
        "Colors:Header": color_set(p, p["header"], p["window_alt"]),
        "Colors:Header][Inactive": color_set(p, p["header_inactive"], p["window_alt"]),
        "Colors:Selection": selection,
        "Colors:Tooltip": color_set(p, p["tooltip"], p["window"]),
        "Colors:View": color_set(p, p["view"], p["view_alt"]),
        "Colors:Window": color_set(p, p["window"], p["window_alt"]),
        "General": {
            "ColorScheme": scheme_id,
            "Name": scheme_name,
            "shadeSortColumn": "true",
        },
        "KDE": {"contrast": "4"},
        "WM": {
            "activeBackground": p["header"].kde(),
            "activeBlend": p["header"].kde(),
            "activeForeground": p["label"].over(p["header"]).kde(),
            "inactiveBackground": p["header_inactive"].kde(),
            "inactiveBlend": p["header_inactive"].kde(),
            "inactiveForeground": p["label_secondary"].over(p["header_inactive"]).kde(),
        },
    }

    out = [
        "# Generado por tools/gen_tokens.py desde tokens/goldenglass.toml — NO EDITAR",
        # REUSE-IgnoreStart
        "# SPDX-License-Identifier: GPL-3.0-or-later",
        # REUSE-IgnoreEnd
        "",
    ]
    for name, entries in sections.items():
        out.append(f"[{name}]")
        out.extend(f"{k}={v}" for k, v in entries.items())
        out.append("")
    return "\n".join(out)


# --- main -------------------------------------------------------------------

# Secciones que leen los generadores: deben existir y ser tablas
REQUIRED_SECTIONS = (
    "meta", "radius", "focus_ring", "glass", "plasma", "shadow", "decoration", "menu", "finder",
    "font", "apps", "icon_tile", "scroll", "traffic_lights", "dock", "control_center", "motion", "boot", "login",
    "sounds", "accessibility", "kwin", "light", "dark",
)

# [accessibility]: valores de fábrica de goldenglassrc [Accessibility] y la
# opacidad con «Reducir transparencia» (docs/ARCHITECTURE.md, «Accesibilidad»)
ACCESSIBILITY_FLAGS = ("show_borders", "reduce_transparency", "reduce_motion")

# [motion]: clave → si admite 0 (Motion.qml divide por kirigami_long_ms)
MOTION_KEYS = {"kirigami_long_ms": False, "reduced_fade_ms": True}


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def validate_motion(motion: dict) -> None:
    for key, zero_ok in MOTION_KEYS.items():
        value = motion.get(key)
        if not _is_number(value) or value < 0 or (value == 0 and not zero_ok):
            limit = "≥ 0" if zero_ok else "> 0"
            raise SystemExit(f"[motion].{key} debe ser un número {limit} (ms), no {value!r}")


def validate_kwin(kwin: dict) -> None:
    for key in ("open_scale", "close_scale"):
        value = kwin.get(key)
        if not _is_number(value) or not 0 < value <= 1:
            raise SystemExit(f"[kwin].{key} must be a number in (0, 1], not {value!r}")
    duration = kwin.get("window_anim_ms")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise SystemExit(f"[kwin].window_anim_ms must be a whole number of ms > 0, not {duration!r}")
    minimize = kwin.get("reduce_motion_minimize")
    if minimize not in windows.REDUCE_MOTION_MINIMIZE:
        raise SystemExit(f"[kwin].reduce_motion_minimize must be one of {', '.join(windows.REDUCE_MOTION_MINIMIZE)}, "
                         f"not {minimize!r}")


ICON_TILE_PAIRS = ("white", "graphite", "paper", "wrap_paper")
ICON_TILE_COLORS = ("highlight", "shadow_color")
ICON_TILE_ALPHAS = ("shadow_alpha", "glyph_shadow_alpha", "sheen_light", "sheen_dark", "rim_top_light",
                    "rim_top_dark", "rim_mid", "rim_bottom_light", "rim_bottom_dark", "edge_alpha")
ICON_TILE_LENGTHS = ("shadow_blur", "shadow_dy", "glyph_shadow_blur", "glyph_shadow_dy", "rim_width", "edge_width")


def validate_icon_tile(tile: dict) -> None:
    """[icon_tile]: colores válidos, opacidades en 0..1 y medidas del lienzo de 64 en 0..8."""
    expected = {*ICON_TILE_PAIRS, *ICON_TILE_COLORS, *ICON_TILE_ALPHAS, *ICON_TILE_LENGTHS}
    if set(tile) != expected:
        raise SystemExit(f"[icon_tile]: faltan {sorted(expected - set(tile))} o sobran {sorted(set(tile) - expected)}")

    def number(key: str) -> float:
        value = tile[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SystemExit(f"[icon_tile].{key}: debe ser un número")
        return float(value)

    def color(key: str, value: object) -> None:
        if not isinstance(value, str):
            raise SystemExit(f"[icon_tile].{key}: debe ser un color #RRGGBB")
        try:
            parsed = Color.parse(value)
        except ValueError as e:
            raise SystemExit(f"[icon_tile].{key}: {e}") from None
        if parsed.a != 1.0 or len(value.lstrip("#")) != 6:
            raise SystemExit(f"[icon_tile].{key}: debe ser #RRGGBB, sin alfa (la opacidad va en su propia clave)")

    for key in ICON_TILE_PAIRS:
        pair = tile[key]
        if not isinstance(pair, list) or len(pair) != 2:
            raise SystemExit(f"[icon_tile].{key}: debe ser [arriba, abajo]")
        for value in pair:
            color(key, value)
    for key in ICON_TILE_COLORS:
        color(key, tile[key])
    for key in ICON_TILE_ALPHAS:
        if not 0 <= number(key) <= 1:
            raise SystemExit(f"[icon_tile].{key}: la opacidad debe estar entre 0 y 1")
    for key in ICON_TILE_LENGTHS:
        if not 0 <= number(key) <= 8:
            raise SystemExit(f"[icon_tile].{key}: la medida debe estar entre 0 y 8 (lienzo de 64)")


def validate(tokens: dict) -> None:
    missing = [name for name in REQUIRED_SECTIONS if name not in tokens]
    if missing:
        raise SystemExit(f"faltan secciones en los tokens: {', '.join(f'[{name}]' for name in missing)}")
    not_tables = [name for name in REQUIRED_SECTIONS if not isinstance(tokens[name], dict)]
    if not_tables:
        raise SystemExit(f"estas claves de los tokens deben ser secciones: {', '.join(not_tables)}")
    validate_motion(tokens["motion"])
    validate_kwin(tokens["kwin"])

    validate_icon_tile(tokens["icon_tile"])

    light, dark = set(tokens["light"]), set(tokens["dark"])
    if light != dark:
        raise SystemExit(
            "las paletas claro/oscuro no tienen las mismas claves:\n"
            f"  solo en light: {sorted(light - dark)}\n"
            f"  solo en dark:  {sorted(dark - light)}")
    for variant in ("light", "dark"):
        for key, value in tokens[variant].items():
            try:
                Color.parse(value)
            except ValueError as e:
                raise SystemExit(f"[{variant}].{key}: {e}") from None
    validate_shadow(tokens["shadow"])
    _validate_accessibility(tokens["accessibility"])


def validate_shadow(shadow: dict) -> None:
    """Sombras de ventana: la inactiva no puede ser mayor que la activa."""
    for state in ("active", "inactive"):
        if not isinstance(shadow.get(state), dict):
            raise SystemExit(f"falta la sección [shadow.{state}] en los tokens")
        for key in ("size", "strength"):
            value = shadow[state].get(key)
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise SystemExit(f"[shadow.{state}].{key} debe ser un número (es {value!r})")
        if not 0 <= shadow[state]["strength"] <= 1:
            raise SystemExit(f"[shadow.{state}].strength fuera de 0..1: {shadow[state]['strength']}")
    active, inactive = shadow["active"], shadow["inactive"]
    for key in ("size", "strength"):
        if inactive[key] > active[key]:
            raise SystemExit(
                f"[shadow.inactive].{key} = {inactive[key]} es mayor que [shadow.active].{key} = {active[key]}: "
                "la sombra de las ventanas sin foco no puede superar a la de la activa")
    alpha = shadow.get("outline_alpha")
    if isinstance(alpha, bool) or not isinstance(alpha, int | float) or not 0 <= alpha <= 1:
        raise SystemExit(f"[shadow].outline_alpha debe estar en 0..1 (es {alpha!r})")


def _validate_accessibility(section: dict) -> None:
    for key in ACCESSIBILITY_FLAGS:
        if key not in section:
            raise SystemExit(f"falta [accessibility].{key} en los tokens")
        if not isinstance(section[key], bool):
            raise SystemExit(f"[accessibility].{key} debe ser true o false, no {section[key]!r}")
    alpha = section.get("reduce_transparency_alpha")
    # bool es subclase de int: true/false no valen como opacidad
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0.0 <= alpha <= 1.0:
        raise SystemExit(f"[accessibility].reduce_transparency_alpha debe ser un número entre 0 y 1, no {alpha!r}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tokens", type=Path, default=ROOT / "tokens" / "goldenglass.toml")
    ap.add_argument("--out", type=Path, default=ROOT / "build")
    ap.add_argument("--cxx-header", type=Path, metavar="RUTA",
                    help="solo escribe la cabecera C++ de tokens en RUTA")
    ap.add_argument("--glass-level", type=float, metavar="0..1",
                    help="nivel del slider de vidrio para el Plasma Style (por defecto, glass.default_level)")
    args = ap.parse_args(argv)

    tokens = load_tokens(args.tokens)
    validate(tokens)

    if args.cxx_header:
        cxx_tokens.write(tokens, args.cxx_header)
        return 0

    schemes = args.out / "color-schemes"
    schemes.mkdir(parents=True, exist_ok=True)
    written = []
    for variant, (scheme_id, _) in VARIANTS.items():
        path = schemes / f"{scheme_id}.colors"
        path.write_text(build_colors(tokens, variant), encoding="utf-8")
        written.append(path)

    path = args.out / "tokens.json"
    path.write_text(json.dumps(tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written.append(path)

    written += plasma_theme.build(tokens, args.out, args.glass_level)
    written += lookandfeel.build(tokens, args.out)
    written += plasmoids.build(args.out, tokens)
    written += shell.build(tokens, args.out)
    written += wallpaper.build(args.out)
    written += cursors.build(tokens, args.out)
    written += icons.build(tokens, args.out)
    written += gtk.build(tokens, args.out)
    written += sounds.build(tokens, args.out)
    written += plymouth.build(tokens, args.out)
    written += login.build(tokens, args.out)
    written.append(windows.write_json(tokens, args.out / "kwin" / windows.TOKENS_JSON))

    for p in written:
        print(f"  {p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyError as exc:
        # una clave que falta en los tokens: se dice cuál y qué generador la leía
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        raise SystemExit(f"falta la clave {exc} en los tokens (leída en {Path(frame.filename).name}:{frame.lineno})") from None
