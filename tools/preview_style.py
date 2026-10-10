#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Vista previa del estilo de aplicaciones compilado (build/cmake), sin instalarlo.

Renderiza un menú abierto (elemento seleccionado, casillas, separador,
submenú) y algunos controles con el estilo GoldenGlass y la paleta del esquema
de color, a través del tema de plataforma de KDE, en un entorno temporal.

  python3 tools/preview_style.py [--variant light|dark] [--out build/style-preview-light.png]

Requiere PyQt6 y haber compilado build/cmake.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "cmake"


def prepare_environment(variant: str, workdir: Path) -> dict[str, str]:
    """Instala los plugins en workdir con DESTDIR y prepara un kdeglobals."""
    stage = workdir / "stage"
    subprocess.run(["cmake", "--install", str(BUILD)], check=True, stdout=subprocess.DEVNULL,
                   env={**os.environ, "DESTDIR": str(stage)})
    scheme = "GoldenGlassLight" if variant == "light" else "GoldenGlassDark"
    colors = ROOT / "build" / "color-schemes" / f"{scheme}.colors"
    if not colors.exists():
        subprocess.run([sys.executable, str(ROOT / "tools" / "gen_tokens.py")], check=True, stdout=subprocess.DEVNULL)

    config = workdir / "config"
    config.mkdir(parents=True)
    kdeglobals = colors.read_text(encoding="utf-8")
    kdeglobals += "\n[KDE]\nwidgetStyle=GoldenGlass\n"
    kdeglobals += "\n[General]\nfont=GoldenGlass Sans,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1,,0,0\n"
    (config / "kdeglobals").write_text(kdeglobals, encoding="utf-8")

    env = dict(os.environ)
    env.update({
        "GG_PREVIEW_CHILD": "1",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QPA_PLATFORMTHEME": "kde",
        "QT_PLUGIN_PATH": f"{stage}/usr/lib/qt6/plugins",
        "XDG_CONFIG_HOME": str(config),
        "XDG_CONFIG_DIRS": "/etc/xdg",
        "XDG_DATA_DIRS": f"{stage}/usr/share:/usr/share",
    })
    return env


def render(out: Path) -> int:
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtGui import QAction, QColor, QIcon, QImage, QPainter
    from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QLineEdit, QMenu, QPushButton,
                                 QSlider, QVBoxLayout, QWidget)

    app = QApplication(sys.argv[:1])
    if app.style().name().lower() != "goldenglass":
        print(f"estilo cargado: {app.style().name()} (se esperaba goldenglass)", file=sys.stderr)
        return 1

    menu = QMenu()
    menu.addAction(QIcon.fromTheme("document-new"), "Nueva ventana")
    selected = menu.addAction(QIcon.fromTheme("document-open"), "Abrir…")
    menu.addAction(QIcon.fromTheme("document-save"), "Guardar")
    menu.addSeparator()
    check = menu.addAction("Mostrar barra lateral")
    check.setCheckable(True)
    check.setChecked(True)
    menu.addAction("Mostrar barra de estado").setCheckable(True)
    menu.addSeparator()
    sub = menu.addMenu("Ordenar por")
    sub.addAction("Nombre")
    disabled = menu.addAction("Deshacer cierre")
    disabled.setEnabled(False)
    menu.addAction(QIcon.fromTheme("application-exit"), "Salir")

    panel = QWidget()
    panel.resize(300, 280)
    lay = QVBoxLayout(panel)
    b = QPushButton("Aceptar"); b.setDefault(True); lay.addWidget(b)
    lay.addWidget(QPushButton("Cancelar"))
    lay.addWidget(QLineEdit("Texto"))
    c = QCheckBox("Opción"); c.setChecked(True); lay.addWidget(c)
    cb = QComboBox(); cb.addItems(["Uno", "Dos"]); lay.addWidget(cb)
    s = QSlider(Qt.Orientation.Horizontal); s.setValue(60); lay.addWidget(s)
    lay.addStretch()
    panel.show()
    app.processEvents()
    panel_img = panel.grab().toImage()

    # El menú se abre al final: si otra ventana se muestra después, el menú
    # pierde el foco, se cierra y Qt olvida el elemento activo.
    menu.popup(QPoint(0, 0))
    app.processEvents()
    menu.setActiveAction(selected)
    app.processEvents()
    menu_img = menu.grab().toImage()
    width = menu_img.width() + panel_img.width() + 48
    height = max(menu_img.height(), panel_img.height()) + 32
    sheet = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    sheet.fill(QColor(app.palette().window().color()).darker(110))
    p = QPainter(sheet)
    p.drawImage(16, 16, menu_img)
    p.drawImage(menu_img.width() + 32, 16, panel_img)
    p.end()
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out))
    print(out)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("light", "dark"), default="light")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    out = args.out or ROOT / "build" / f"style-preview-{args.variant}.png"

    if os.environ.get("GG_PREVIEW_CHILD"):
        return render(out)

    workdir = Path(tempfile.mkdtemp(prefix="gg-style-preview."))
    try:
        env = prepare_environment(args.variant, workdir)
        return subprocess.run([sys.executable, __file__, "--variant", args.variant, "--out", str(out)], env=env).returncode
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
