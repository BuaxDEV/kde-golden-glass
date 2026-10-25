# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Temas de Plymouth «goldenglass» (negro) y «goldenglass-light» (gris claro).

Plugin `script`: plymouth/goldenglass.script.in con los valores de [boot] de
los tokens. Las piezas (logo, barra, campo de contraseña, puntos, Bloq Mayús)
se dibujan con QtSvg/QPainter a 1x, 2x y 3x; el script elige el juego según
la altura de la pantalla y lo escala a la medida exacta.

Salida:
  build/plymouth/goldenglass/goldenglass.{plymouth,script} + *@{1,2,3}x.png
  build/plymouth/goldenglass-light/…

Vista previa sin reiniciar ni root: tools/preview_plymouth.sh.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ggcommon import Color, fill_template, stamp

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "plymouth" / "goldenglass.script.in"
LOGO = ROOT / "assets" / "logo" / "goldenglass-symbolic.svg"
LOGO_COLOR = "#232629"  # color de ColorScheme-Text en el SVG, se sustituye
THEMES_DIR = "/usr/share/plymouth/themes"
SCALES = (1, 2, 3)  # el script elige entre estas (ver asset() en la plantilla)

VARIANTS = {
    "dark": ("goldenglass", "GoldenGlass", "Logo and thin progress bar on black, like a Mac booting"),
    "light": ("goldenglass-light", "GoldenGlass Light", "Logo and thin progress bar on light gray, like a Mac booting"),
}


def _script_color(hex_color: str) -> str:
    """#RRGGBB → «r, g, b» en 0..1 (formato de color de Plymouth)."""
    return ", ".join(f"{c / 255:.3f}" for c in Color.parse(hex_color).rgb())


# --- piezas -----------------------------------------------------------------

def _image(width: int, height: int):
    from PyQt6.QtGui import QImage

    img = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    return img


def _painter(img):
    from PyQt6.QtGui import QPainter

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return p


def _color(hex_color: str, alpha: float):
    from PyQt6.QtGui import QColor

    c = QColor(hex_color)
    c.setAlphaF(alpha)
    return c


def _logo(fg: str, px: int):
    from PyQt6.QtCore import QByteArray, QRectF
    from PyQt6.QtSvg import QSvgRenderer

    svg = LOGO.read_text(encoding="utf-8").replace(LOGO_COLOR, fg)
    img = _image(px, px)
    p = _painter(img)
    QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(0, 0, px, px))
    p.end()
    return img


def _pill(width: int, height: int, fill, border=None, border_width: float = 0):
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QPen

    img = _image(width, height)
    p = _painter(img)
    inset = border_width / 2
    rect = QRectF(inset, inset, width - border_width, height - border_width)
    radius = rect.height() / 2
    p.setPen(QPen(border, border_width) if border is not None else Qt.PenStyle.NoPen)
    p.setBrush(fill)
    p.drawRoundedRect(rect, radius, radius)
    p.end()
    return img


def _capslock(color, px: int):
    """Flecha hueca hacia arriba con una barra debajo (⇪), en un lienzo de 14."""
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import QPainterPath, QPen

    img = _image(px, px)
    p = _painter(img)
    p.scale(px / 14, px / 14)
    path = QPainterPath(QPointF(7, 1.2))
    for x, y in ((12.6, 7), (9.6, 7), (9.6, 9.8), (4.4, 9.8), (4.4, 7), (1.4, 7)):
        path.lineTo(x, y)
    path.closeSubpath()
    p.setPen(QPen(color, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(QRectF(4.4, 11.3, 5.2, 1.6), 0.6, 0.6)
    p.end()
    return img


def _pieces(boot: dict, pal: dict, scale: int) -> dict:
    fg = pal["foreground"]
    s = scale
    bar_w, bar_h = boot["bar_width"] * s, boot["bar_height"] * s
    field_w, field_h = boot["field_width"] * s, boot["field_height"] * s
    return {
        "logo": _logo(fg, boot["logo_size"] * s),
        "track": _pill(bar_w, bar_h, _color(fg, pal["track_alpha"])),
        "fill": _pill(bar_w, bar_h, _color(fg, 1.0)),
        "field": _pill(field_w, field_h, _color(fg, pal["field_alpha"]),
                       _color(fg, pal["field_border_alpha"]), 1.0 * s),
        "dot": _pill(boot["dot_size"] * s, boot["dot_size"] * s, _color(fg, 1.0)),
        "capslock": _capslock(_color(fg, pal["text_alpha"]), 14 * s),
    }


# --- tema -------------------------------------------------------------------

def script(boot: dict, pal: dict) -> str:
    # [boot] tal cual y, en «plymouth», los colores de la variante en el
    # formato del script
    values = {"boot": boot, "plymouth": {
        "background": _script_color(pal["background"]),
        "foreground": _script_color(pal["foreground"]),
        "text_alpha": f"{pal['text_alpha']:.3f}",
    }}
    text = fill_template(TEMPLATE.read_text(encoding="utf-8"), values, TEMPLATE.relative_to(ROOT))
    header = "// Generado por tools/plymouth.py desde tokens/goldenglass.toml — NO EDITAR\n"
    return header + text


def plymouth_file(theme_id: str, name: str, description: str, boot: dict) -> str:
    folder = f"{THEMES_DIR}/{theme_id}"
    return (
        "# Generado por tools/plymouth.py desde tokens/goldenglass.toml — NO EDITAR\n"
        "[Plymouth Theme]\n"
        f"Name={name}\n"
        f"Description={description}\n"
        "ModuleName=script\n"
        "\n"
        "[script]\n"
        f"ImageDir={folder}\n"
        f"ScriptFile={folder}/{theme_id}.script\n"
        # el hook plymouth de mkinitcpio mete esta fuente en el initramfs
        f"Font={boot['font']} {boot['font_size']}\n"
    )


def _stamp(tokens: dict) -> str:
    return stamp(Path(__file__), TEMPLATE, LOGO, data=tokens["boot"])


def build(tokens: dict, out: Path) -> list[Path]:
    """Genera los dos temas; se salta si nada de lo que usan cambió."""
    base = out / "plymouth"
    stamp_file = base / ".stamp"
    if stamp_file.exists() and stamp_file.read_text() == _stamp(tokens):
        return []
    if base.exists():
        shutil.rmtree(base)

    boot = tokens["boot"]
    written: list[Path] = []
    for variant, (theme_id, name, description) in VARIANTS.items():
        pal = boot[variant]
        root = base / theme_id
        root.mkdir(parents=True)
        for scale in SCALES:
            for piece, img in _pieces(boot, pal, scale).items():
                path = root / f"{piece}@{scale}x.png"
                if not img.save(str(path)):
                    raise RuntimeError(f"no se pudo escribir {path}")
                written.append(path)
        for path, content in ((root / f"{theme_id}.script", script(boot, pal)),
                              (root / f"{theme_id}.plymouth", plymouth_file(theme_id, name, description, boot))):
            path.write_text(content, encoding="utf-8")
            written.append(path)
    stamp_file.write_text(_stamp(tokens))
    return written
