# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tema de SDDM «GoldenGlass» (pantalla de inicio de sesión).

Copia login/sddm/ (QML e iconos), rellena metadata.desktop (versión) y escribe
theme.conf con los valores de [login] de los tokens, la fuente de la interfaz y
el fondo de GoldenGlass instalado en el sistema (día y noche, 16:9 y 16:10).

Salida:
  build/login/sddm/GoldenGlass/{Main.qml,metadata.desktop,theme.conf,icons/}

Vista previa sin cerrar sesión ni root: tools/preview_login.sh.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import wallpaper
from ggcommon import fill_template

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "login" / "sddm"
THEME_ID = "GoldenGlass"
WALLPAPER_DIR = f"/usr/share/wallpapers/{wallpaper.THEME_ID}/contents"

# clave de [login] → clave de theme.conf (la que lee Main.qml)
KEYS = {
    "day_start": "dayStart",
    "night_start": "nightStart",
    "blur": "blur",
    "dim": "dim",
    "clock_size": "clockSize",
    "date_size": "dateSize",
    "clock_top": "clockTop",
    "avatar_size": "avatarSize",
    "avatar_small": "avatarSmall",
    "name_size": "nameSize",
    "field_width": "fieldWidth",
    "field_height": "fieldHeight",
    "action_size": "actionSize",
    "bottom_margin": "bottomMargin",
    "text": "text",
    "text_alpha": "textAlpha",
    "glass": "glass",
    "glass_alpha": "glassAlpha",
    "glass_border_alpha": "glassBorderAlpha",
    "error": "error",
}


def _size(width_height: tuple[int, int]) -> str:
    return f"{width_height[0]}x{width_height[1]}.jpg"


def theme_conf(tokens: dict) -> str:
    login = tokens["login"]
    missing = set(KEYS) - set(login)
    if missing:
        raise ValueError(f"[login]: faltan {sorted(missing)}")
    wide = max(wallpaper.SIZES, key=lambda s: s[0] / s[1])
    tall = min(wallpaper.SIZES, key=lambda s: s[0] / s[1])
    lines = [
        "# Generado por tools/login.py desde tokens/goldenglass.toml — NO EDITAR",
        "[General]",
        f"font={tokens['font']['sans']}",
        f"wallpaperDir={WALLPAPER_DIR}",
        f"wallpaperWide={_size(wide)}",
        f"wallpaperTall={_size(tall)}",
    ]
    # entre comillas: QSettings no debe tomar «#» de los colores por un comentario
    lines += [f'{conf}="{login[key]}"' if isinstance(login[key], str) else f"{conf}={login[key]}"
              for key, conf in KEYS.items()]
    return "\n".join(lines) + "\n"


def build(tokens: dict, out: Path) -> list[Path]:
    root = out / "login" / "sddm" / THEME_ID
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(SOURCE, root, ignore=shutil.ignore_patterns("*.po"))
    meta = root / "metadata.desktop"
    meta.write_text(fill_template((SOURCE / meta.name).read_text(encoding="utf-8"), tokens,
                                  (SOURCE / meta.name).relative_to(ROOT)), encoding="utf-8")
    conf = root / "theme.conf"
    conf.write_text(theme_conf(tokens), encoding="utf-8")
    # SDDM carga <idioma>.qm de TranslationsDirectory; msgfmt --qt los compila
    for po in sorted((SOURCE / "translations").glob("*.po")):
        subprocess.run(["msgfmt", "--qt", "-o", str(root / "translations" / f"{po.stem}.qm"), str(po)],
                       check=True)
    return [root]
