# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generador de los Global Themes (Look-and-Feel) claro y oscuro.

Ambos paquetes salen de `plasma/look-and-feel/common/` (layout, splash) con los
marcadores entre arrobas sustituidos desde los tokens, más un `defaults` y un `metadata.json`
propios de cada variante.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMON = ROOT / "plasma" / "look-and-feel" / "common"
LOGO = ROOT / "assets" / "logo" / "goldenglass.svg"
SHELL_PACKAGE = "org.goldenglass.desktop"
PLASMA_THEME = "GoldenGlass"
# Plugins C++ del paquete goldenglass-kstyle. Si no está instalado, Plasma usa
# Breeze para ambos.
WIDGET_STYLE = "GoldenGlass"
DECORATION = "org.goldenglass.decoration"
CURSOR_THEME = "GoldenGlass-cursors"  # tools/cursors.py
ICON_THEMES = {"light": "GoldenGlass", "dark": "GoldenGlass-Dark"}  # tools/icons.py

VARIANTS = {
    "light": ("org.goldenglass.light.desktop", "GoldenGlass Light", "GoldenGlassLight"),
    "dark": ("org.goldenglass.dark.desktop", "GoldenGlass Dark", "GoldenGlassDark"),
}

TEMPLATED = {".js", ".qml"}


def _font(family: str, size: int, weight: int = 400) -> str:
    """Serialización QFont::toString() de Qt 6."""
    return f"{family},{size},-1,5,{weight},0,0,0,0,0,0,0,0,0,0,1,,0,0"


def _flatten(fg: str, bg: str) -> str:
    f, b = fg.lstrip("#"), bg.lstrip("#")
    a = int(f[6:8], 16) / 255 if len(f) == 8 else 1.0
    return "#" + "".join(f"{round(int(f[i:i + 2], 16) * a + int(b[i:i + 2], 16) * (1 - a)):02X}"
                         for i in (0, 2, 4))


def _dock_height(tokens: dict) -> int:
    """Grosor inicial del panel del dock: la placa (icono + relleno; el punto de
    app abierta va en el relleno) y encima el hueco para el icono más ampliado
    rebotando (al hacer clic está ampliado y salta desde ese tamaño). Después
    lo mantiene el propio dock (DockView.panelThickness)."""
    p, d = tokens["plasma"], tokens["dock"]
    icon = p["dock_icon_size"]
    biggest = d["magnification_size"] if d["magnification"] else icon
    headroom = math.ceil(biggest * (1 + d["bounce"])) - icon
    h = icon + 2 * p["dock_padding"] + headroom
    return h + h % 2                          # Plasma solo muestra alturas pares


def values(tokens: dict, variant: str) -> dict[str, str]:
    pal = tokens[variant]
    label = _flatten(pal["label"], pal["window"])
    if variant == "light":
        splash_bg, splash_fg = pal["window"], label
    else:
        splash_bg, splash_fg = pal["complementary"], _flatten(pal["label"], pal["complementary"])
    track_alpha = "26" if variant == "light" else "40"
    return {
        "MENUBAR_HEIGHT": str(tokens["plasma"]["menubar_height"]),
        "DOCK_HEIGHT": str(_dock_height(tokens)),
        "DOCK_HIDING": tokens["plasma"]["dock_hiding"],
        "SLIDE_IN_MS": str(tokens["plasma"]["slide_in_ms"]),
        "SLIDE_OUT_MS": str(tokens["plasma"]["slide_out_ms"]),
        "PER_SCREEN_DESKTOPS": "true" if tokens["plasma"]["per_screen_desktops"] else "false",
        "SPLASH_BACKGROUND": splash_bg,
        "SPLASH_TRACK": _with_alpha(splash_fg, track_alpha),
        "SPLASH_FILL": splash_fg,
    }


def _with_alpha(rgb: str, alpha_hex: str) -> str:
    """#RRGGBB + AA → #AARRGGBB (formato de color con alfa de QML)."""
    return "#" + alpha_hex + rgb.lstrip("#")


def defaults(tokens: dict, variant: str) -> str:
    pkg_id, _, scheme = VARIANTS[variant]
    f = tokens["font"]
    weight = {"Normal": 400, "Medium": 500, "DemiBold": 600, "Bold": 700}[f["window_title_weight"]]
    sans, mono = f["sans"], f["mono"]
    fonts = {
        "font": _font(sans, f["size_general"]),
        "fixed": _font(mono, f["size_general"]),
        "smallestReadableFont": _font(sans, f["size_small"]),
        "toolBarFont": _font(sans, f["size_toolbar"]),
        "menuFont": _font(sans, f["size_menu"]),
    }
    title_font = _font(sans, f["size_window_title"], weight)
    lines = [
        "# Generado por tools/gen_tokens.py — NO EDITAR",
        "",
        "[kdeglobals][General]",
        f"ColorScheme={scheme}",
        *(f"{k}={v}" for k, v in fonts.items()),
        # KLookAndFeelManager detecta las fuentes en [WM] pero las aplica desde
        # [General] (y al revés para activeFont): se escriben en ambos grupos.
        f"activeFont={title_font}",
        "",
        "[kdeglobals][WM]",
        f"activeFont={title_font}",
        *(f"{k}={v}" for k, v in fonts.items()),
        "",
        "[kdeglobals][KDE]",
        f"widgetStyle={WIDGET_STYLE}",
        "",
        "[kdeglobals][Icons]",
        f"Theme={ICON_THEMES[variant]}",
        "",
        "[plasmarc][Theme]",
        f"name={PLASMA_THEME}",
        "",
        "[Wallpaper]",
        "Image=GoldenGlass",
        "",
        "[kcminputrc][Mouse]",
        f"cursorTheme={CURSOR_THEME}",
        "",
        "[kwinrc][org.kde.kdecoration2]",
        f"library={DECORATION}",
        "theme=GoldenGlass",
        "",
        "[ksplashrc][KSplash]",
        f"Theme={pkg_id}",
        "",
        "[plasmashellrc][Shell]",
        f"ShellPackage={SHELL_PACKAGE}",
        "",
    ]
    return "\n".join(lines)


def layout_defaults() -> str:
    """contents/layouts/defaults: ajustes de "disposición" que KLookAndFeelManager
    solo lee de este archivo (no de contents/defaults)."""
    return "\n".join([
        "# Generado por tools/gen_tokens.py — NO EDITAR",
        "",
        "# Semáforos a la izquierda: cerrar, minimizar, maximizar.",
        "[kwinrc][org.kde.kdecoration2]",
        "ButtonsOnLeft=XIA",
        "ButtonsOnRight=",
        "",
    ])


def metadata(tokens: dict, variant: str) -> str:
    pkg_id, name, _ = VARIANTS[variant]
    return json.dumps({
        "KPackageStructure": "Plasma/LookAndFeel",
        "KPlugin": {
            "Authors": [{"Name": "GoldenGlass contributors"}],
            "Category": "",
            "Description": f"{name}: glass desktop inspired by macOS 27",
            "Id": pkg_id,
            "License": "GPL-3.0-or-later",
            "Name": name,
            "Version": tokens["meta"]["version"],
            "Website": "https://github.com/brayanAP/buapdev-cachyos-kde-macos",
        },
        "X-Plasma-APIVersion": "2",
    }, indent=4) + "\n"


def build(tokens: dict, out: Path) -> list[Path]:
    written: list[Path] = []
    for variant, (pkg_id, _, _) in VARIANTS.items():
        root = out / "plasma" / "look-and-feel" / pkg_id
        if root.exists():
            shutil.rmtree(root)
        vals = values(tokens, variant)

        for src in sorted(COMMON.rglob("*")):
            if src.is_dir():
                continue
            dst = root / src.relative_to(COMMON)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.suffix in TEMPLATED:
                text = src.read_text(encoding="utf-8")
                text = re.sub(r"@([A-Z_]+)@", lambda m: vals[m.group(1)], text)
                dst.write_text(text, encoding="utf-8")
            else:
                shutil.copy2(src, dst)
            written.append(dst)

        # Plasma busca layouts/<shell>-layout.js: el mismo layout sirve con el
        # shell estándar y con el de GoldenGlass (que trae la pantalla de bloqueo).
        layouts = root / "contents" / "layouts"
        shell_layout = layouts / f"{SHELL_PACKAGE}-layout.js"
        shutil.copy2(layouts / "org.kde.plasma.desktop-layout.js", shell_layout)
        written.append(shell_layout)

        logo = root / "contents" / "splash" / "images" / "goldenglass.svg"
        logo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LOGO, logo)
        written.append(logo)

        for rel, content in (("metadata.json", metadata(tokens, variant)),
                             ("contents/defaults", defaults(tokens, variant)),
                             ("contents/layouts/defaults", layout_defaults())):
            path = root / rel
            path.write_text(content, encoding="utf-8")
            written.append(path)
    return written
