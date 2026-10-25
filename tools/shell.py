# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepara el shell de Plasma org.goldenglass.desktop (pantalla de bloqueo y
vista del panel) en build/plasma/shells/.

Como los plasmoids (tools/plasmoids.py): copia el paquete, rellena las
plantillas *.in (@sección.clave@ → token, sin .in) y escribe tokens.js con los
tokens en las carpetas de QML que lo usan (en QML: import "tokens.js" as T).
Los QML de upstream siguen siendo .qml normales: solo cambian sus valores de
GoldenGlass, que se leen de tokens.js.

Salida:
  build/plasma/shells/org.goldenglass.desktop/
"""

from __future__ import annotations

import shutil
from pathlib import Path

import plasmoids

ROOT = Path(__file__).resolve().parent.parent
SHELL_ID = "org.goldenglass.desktop"
SOURCE = ROOT / "plasma" / "shell" / SHELL_ID
# carpetas del paquete cuyos QML importan tokens.js
TOKENS_JS = ("contents/lockscreen",)


def build(tokens: dict, out: Path) -> list[Path]:
    dst = out / "plasma" / "shells" / SHELL_ID
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(SOURCE, dst)
    written = [dst, *plasmoids.fill_templates(SOURCE, dst, tokens)]
    written += [plasmoids.write_tokens_js(dst / folder / "tokens.js", tokens) for folder in TOKENS_JS]
    return written
