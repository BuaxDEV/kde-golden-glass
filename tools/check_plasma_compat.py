#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Comprueba GoldenGlass contra el Plasma instalado (lo usa tools/ci.sh):

  - Cada módulo QML que importa el repositorio (salvo org.goldenglass.*, que
    se compilan aquí) está instalado. Plasma mueve y quita módulos entre
    versiones: con 6.8 desapareció org.kde.plasma.shell.panel y plasmashell se
    caía al cargar views/Panel.qml.
  - El shell está portado al plasma-desktop instalado
    (X-GoldenGlass-PlasmaVersion de su metadata.json; ver UPSTREAM.md).

Con --qmldirs solo lista los qmldir de esos módulos (rutas para pacman -F, que
dice qué paquetes instalar antes de comprobar).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHELL = ROOT / "plasma/shell/org.goldenglass.desktop"
OWN = "org.goldenglass."
IMPORT = re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)", re.M)


def _qml_dir() -> Path:
    for tool in ("qtpaths6", "qtpaths"):
        if shutil.which(tool):
            out = subprocess.run([tool, "--query", "QT_INSTALL_QML"], capture_output=True, text=True,
                                 check=False).stdout.strip()
            if out:
                return Path(out)
    return Path("/usr/lib/qt6/qml")


def _imports() -> dict[str, list[str]]:
    """Módulo -> archivos que lo importan."""
    files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "*.qml"], capture_output=True, text=True,
                           check=True).stdout.split()
    found: dict[str, list[str]] = {}
    for name in files:
        for module in IMPORT.findall((ROOT / name).read_text(encoding="utf-8")):
            if not module.startswith(OWN):
                found.setdefault(module, []).append(name)
    return found


def _plasma_version() -> str | None:
    """plasma-desktop instalado como mayor.menor (1:6.8.1-1.1 -> 6.8)."""
    if not shutil.which("pacman"):
        return None
    out = subprocess.run(["pacman", "-Q", "plasma-desktop"], capture_output=True, text=True, check=False)
    if out.returncode != 0:
        return None
    version = out.stdout.split()[1].split(":")[-1]
    return ".".join(version.split(".")[:2])


def main() -> int:
    qml = _qml_dir()
    imports = _imports()
    qmldirs = {m: qml / m.replace(".", "/") / "qmldir" for m in imports}
    if "--qmldirs" in sys.argv[1:]:
        for path in sorted(qmldirs.values()):
            print(str(path).lstrip("/"))
        return 0

    errors = []
    for module, path in sorted(qmldirs.items()):
        if not path.is_file():
            errors.append(f"módulo QML {module} no instalado ({path}); lo importan: "
                          + ", ".join(sorted(set(imports[module]))))

    ported = json.loads((SHELL / "metadata.json").read_text(encoding="utf-8")).get("X-GoldenGlass-PlasmaVersion")
    plasma = _plasma_version()
    if plasma is None:
        print("plasma-desktop no instalado: no se comprueba la versión del shell", file=sys.stderr)
    elif ported != plasma:
        errors.append(f"el shell está portado a Plasma {ported} y está instalado Plasma {plasma}: "
                      "portar views/ y lockscreen/ (UPSTREAM.md)")

    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if not errors:
        print(f"{len(imports)} módulos QML instalados; shell portado a Plasma {ported}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
