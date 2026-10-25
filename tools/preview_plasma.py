#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Vista previa del Plasma Style generado, sin aplicarlo al escritorio.

Compone los marcos de build/plasma/desktoptheme/GoldenGlass como lo hace
FrameSvg (esquinas a tamaño natural, bordes y centro estirados) usando QtSvg,
sobre un fondo de colores para apreciar la translucidez. El blur de KWin no se
simula.

  python3 tools/preview_plasma.py [--variant light|dark] [--out build/preview-light.png]

Requiere PyQt6.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from PyQt6.QtCore import QByteArray, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QRadialGradient
from PyQt6.QtSvg import QSvgRenderer

from ggcommon import flatten

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "build" / "plasma" / "desktoptheme" / "GoldenGlass"
PARTS = ("topleft", "top", "topright", "left", "center", "right", "bottomleft", "bottom", "bottomright")


class Frame:
    def __init__(self, path: Path, colors: dict[str, str]):
        text = path.read_text(encoding="utf-8")
        style = "".join(f".ColorScheme-{k} {{ color:{v}; }}" for k, v in colors.items())
        text = re.sub(r'(<style[^>]*id="current-color-scheme"[^>]*>).*?(</style>)',
                      lambda m: m.group(1) + style + m.group(2), text, flags=re.S)
        self.r = QSvgRenderer(QByteArray(text.encode()))
        if not self.r.isValid():
            raise SystemExit(f"SVG inválido: {path}")

    def has(self, eid: str) -> bool:
        return self.r.elementExists(eid)

    def size(self, eid: str) -> tuple[float, float]:
        b = self.r.boundsOnElement(eid)
        return b.width(), b.height()

    def margins(self, prefix: str = "") -> tuple[float, float, float, float]:
        """(top, right, bottom, left) como FrameSvg: hint o tamaño del borde."""
        out = []
        for side, part in (("top", "top"), ("right", "right"), ("bottom", "bottom"), ("left", "left")):
            hint = f"{prefix}hint-{side}-margin"
            w, h = self.size(hint) if self.has(hint) else self.size(prefix + part)
            out.append(h if side in ("top", "bottom") else w)
        return tuple(out)

    def paint(self, p: QPainter, rect: QRectF, prefix: str = "", edges=("top", "right", "bottom", "left")):
        """Dibuja el marco; los bordes no incluidos en `edges` se omiten (panel pegado al borde)."""
        tl_w, tl_h = self.size(prefix + "topleft")
        br_w, br_h = self.size(prefix + "bottomright")
        lw = tl_w if "left" in edges else 0
        rw = br_w if "right" in edges else 0
        th = tl_h if "top" in edges else 0
        bh = br_h if "bottom" in edges else 0
        x0, y0, x1, y1 = rect.left(), rect.top(), rect.right() + 1, rect.bottom() + 1
        cols = ((x0, lw, "left"), (x0 + lw, x1 - x0 - lw - rw, ""), (x1 - rw, rw, "right"))
        rows = ((y0, th, "top"), (y0 + th, y1 - y0 - th - bh, ""), (y1 - bh, bh, "bottom"))
        for ry, rh, rname in rows:
            for cx, cw, cname in cols:
                if cw <= 0 or rh <= 0:
                    continue
                name = (rname + cname) or "center"
                self.r.render(p, prefix + name, QRectF(cx, ry, cw, rh))


def paint_shadow(frame: Frame, p: QPainter, rect: QRectF) -> None:
    """Coloca las teselas `shadow-*` como KWin (KWindowShadow): cada una a su
    tamaño natural alrededor de la ventana, con el relleno definido por los
    `shadow-hint-*-margin`."""
    pt = frame.size("shadow-hint-top-margin")[1]
    pb = frame.size("shadow-hint-bottom-margin")[1]
    pl = frame.size("shadow-hint-left-margin")[0]
    pr = frame.size("shadow-hint-right-margin")[0]
    x0, y0 = rect.left() - pl, rect.top() - pt
    x1, y1 = rect.right() + 1 + pr, rect.bottom() + 1 + pb
    tl, tr = frame.size("shadow-topleft"), frame.size("shadow-topright")
    bl, br = frame.size("shadow-bottomleft"), frame.size("shadow-bottomright")
    t, b = frame.size("shadow-top"), frame.size("shadow-bottom")
    l, r = frame.size("shadow-left"), frame.size("shadow-right")
    tiles = {
        "topleft": QRectF(x0, y0, *tl),
        "topright": QRectF(x1 - tr[0], y0, *tr),
        "bottomleft": QRectF(x0, y1 - bl[1], *bl),
        "bottomright": QRectF(x1 - br[0], y1 - br[1], *br),
        "top": QRectF(x0 + tl[0], y0, x1 - tr[0] - x0 - tl[0], t[1]),
        "bottom": QRectF(x0 + bl[0], y1 - b[1], x1 - br[0] - x0 - bl[0], b[1]),
        "left": QRectF(x0, y0 + tl[1], l[0], y1 - bl[1] - y0 - tl[1]),
        "right": QRectF(x1 - r[0], y0 + tr[1], r[0], y1 - br[1] - y0 - tr[1]),
    }
    for name, area in tiles.items():
        if area.width() > 0 and area.height() > 0:
            frame.r.render(p, "shadow-" + name, area)


def backdrop(p: QPainter, w: int, h: int) -> None:
    g = QLinearGradient(0, 0, w, h)
    for t, c in ((0, "#1d4e89"), (0.35, "#d95d39"), (0.65, "#f0a202"), (1, "#7fb069")):
        g.setColorAt(t, QColor(c))
    p.fillRect(0, 0, w, h, g)
    rg = QRadialGradient(QPointF(w * 0.7, h * 0.3), w * 0.4)
    rg.setColorAt(0, QColor(255, 255, 255, 120))
    rg.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(0, 0, w, h, rg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("light", "dark"), default="light")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    out = args.out or ROOT / "build" / f"preview-{args.variant}.png"

    tokens = json.loads((ROOT / "build" / "tokens.json").read_text())
    pal = tokens[args.variant]
    colors = {"Background": pal["window"], "Text": flatten(pal["label"], pal["window"]),
              "Highlight": pal["accent"], "NeutralText": pal["neutral"]}
    plasma = tokens["plasma"]

    app = QGuiApplication(sys.argv[:1])  # noqa: F841
    W, H = 1100, 640
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    backdrop(p, W, H)
    font = QFont("GoldenGlass Sans", 10)
    p.setFont(font)
    text = QColor(colors["Text"])

    def label(x, y, s):
        p.setPen(text)
        p.drawText(QPointF(x, y), s)

    # Barra de menús: pegada arriba, solo borde inferior.
    panel = Frame(THEME / "translucent/widgets/panel-background.svg", colors)
    mb = plasma["menubar_height"]
    panel.paint(p, QRectF(0, 0, W, mb), edges=("bottom",))
    label(14, mb - 9, "  Finder   Archivo   Edición   Ver   Ir   Ventana   Ayuda")
    label(W - 170, mb - 9, "sáb 10 oct  13:04")

    # Diálogo / popup con sombra.
    dlg = Frame(THEME / "translucent/dialogs/background.svg", colors)
    rect = QRectF(60, 80, 340, 220)
    paint_shadow(dlg, p, rect)
    dlg.paint(p, rect)
    m = dlg.margins()
    label(rect.left() + m[3], rect.top() + m[0] + 14, "Centro de control (popup)")
    vi = Frame(THEME / "widgets/viewitem.svg", colors)
    for i, state in enumerate(("hover-", "selected-", "normal-")):
        r = QRectF(rect.left() + m[3], rect.top() + 40 + i * 38, rect.width() - m[1] - m[3], 32)
        vi.paint(p, r, prefix=state)
        label(r.left() + 10, r.top() + 21, f"Elemento {state.rstrip('-')}")

    # Tooltip.
    tip = Frame(THEME / "translucent/widgets/tooltip.svg", colors)
    trect = QRectF(460, 90, 180, 34)
    paint_shadow(tip, p, trect)
    tip.paint(p, trect)
    label(trect.left() + 12, trect.top() + 22, "Tooltip de vidrio")

    # Dock flotante con tareas.
    tasks = Frame(THEME / "widgets/tasks.svg", colors)
    icon = plasma["dock_icon_size"]
    tm = tasks.margins("normal-")
    item_w = icon + tm[1] + tm[3]
    item_h = icon + tm[0] + tm[2]
    pad = plasma["dock_padding"]
    states = ("", "normal-", "focus-", "hover-", "minimized-", "attention-", "")
    dock_w = len(states) * item_w + 2 * pad
    dock_h = item_h + 2 * pad
    drect = QRectF((W - dock_w) / 2, H - dock_h - 14, dock_w, dock_h)
    paint_shadow(panel, p, drect)
    panel.paint(p, drect)
    for i, st in enumerate(states):
        ir = QRectF(drect.left() + pad + i * item_w, drect.top() + pad, item_w, item_h)
        if st:
            tasks.paint(p, ir, prefix=st)
        icon_r = QRectF(ir.left() + tm[3], ir.top() + tm[0], icon, icon)
        g = QLinearGradient(icon_r.topLeft(), icon_r.bottomLeft())
        g.setColorAt(0, QColor("#5ac8fa")); g.setColorAt(1, QColor("#007aff"))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(g)
        p.drawRoundedRect(icon_r.adjusted(3, 3, -3, -3), 10, 10)

    p.end()
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out))
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
