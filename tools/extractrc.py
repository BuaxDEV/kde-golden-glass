#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sustituto mínimo de extractrc (scripts de traducción de KDE) para los
Messages.sh: escribe en la salida estándar llamadas i18n()/i18nc() con los
textos de archivos .ui y .kcfg, para que xgettext los extraiga.

  python3 tools/extractrc.py archivo.ui archivo.kcfg… >> rc.cpp

.ui: cada <string> salvo notr="true"; su comment="…" es el contexto (el mismo
que usa tr2i18n al traducir). .kcfg: <label>, <tooltip> y <whatsthis>, con su
atributo context="…" como contexto. Lo usa tools/check_i18n.sh cuando no está
el extractrc de KDE.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

KCFG_TAGS = {"label", "tooltip", "whatsthis"}


def _c_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _call(text: str, context: str | None) -> str:
    if context:
        return f"i18nc({_c_string(context)}, {_c_string(text)});"
    return f"i18n({_c_string(text)});"


def extract(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    calls = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]  # .kcfg lleva espacio de nombres
        text = element.text or ""
        if not text.strip():
            continue
        if path.suffix == ".ui" and tag == "string" and element.get("notr") != "true":
            calls.append(f"// i18n: file: {path}\n" + _call(text, element.get("comment")))
        elif path.suffix == ".kcfg" and tag in KCFG_TAGS:
            calls.append(f"// i18n: file: {path}\n" + _call(text.strip(), element.get("context")))
    return calls


def main(argv: list[str]) -> int:
    for name in argv:
        path = Path(name)
        if path.suffix not in (".ui", ".kcfg"):
            continue  # .rc: no hay en el proyecto
        print("\n".join(extract(path)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
