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

Uso:
  python3 tools/gen_tokens.py [--tokens RUTA] [--out DIR]
  python3 tools/gen_tokens.py --cxx-header RUTA   # solo la cabecera C++ (CMake)
"""

from __future__ import annotations

import argparse
import json
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
    "font", "apps", "scroll", "traffic_lights", "dock", "control_center", "boot", "login",
    "sounds", "light", "dark",
)


def validate(tokens: dict) -> None:
    missing = [name for name in REQUIRED_SECTIONS if name not in tokens]
    if missing:
        raise SystemExit(f"faltan secciones en los tokens: {', '.join(f'[{name}]' for name in missing)}")
    not_tables = [name for name in REQUIRED_SECTIONS if not isinstance(tokens[name], dict)]
    if not_tables:
        raise SystemExit(f"estas claves de los tokens deben ser secciones: {', '.join(not_tables)}")

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
                raise SystemExit(f"[{variant}].{key}: {e}")


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
