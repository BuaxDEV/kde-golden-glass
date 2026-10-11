# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepara los plasmoids de plasma/plasmoids/ en build/plasma/plasmoids/.

Copia cada paquete, compila sus traducciones (po/<idioma>.po) dentro del
propio paquete, en contents/locale/<idioma>/LC_MESSAGES/plasma_applet_<id>.mo,
donde Plasma las busca para los plasmoids instalados como paquete, y escribe
contents/ui/tokens.js con los tokens (en QML: import "tokens.js" as T).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "plasma" / "plasmoids"


def build(out: Path, tokens: dict | None = None) -> list[Path]:
    written: list[Path] = []
    if not SOURCES.exists():
        return written
    for src in sorted(p for p in SOURCES.iterdir() if p.is_dir()):
        plugin_id = json.loads((src / "metadata.json").read_text(encoding="utf-8"))["KPlugin"]["Id"]
        dst = out / "plasma" / "plasmoids" / plugin_id
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("po"))
        written.append(dst)
        if tokens is not None:
            js = dst / "contents" / "ui" / "tokens.js"
            js.write_text("// Generado por tools/gen_tokens.py desde tokens/goldenglass.toml — NO EDITAR\n"
                          ".pragma library\n\nvar tokens = " + json.dumps(tokens, ensure_ascii=False) + ";\n",
                          encoding="utf-8")

        for po in sorted((src / "po").glob("*.po")) if (src / "po").exists() else []:
            mo = dst / "contents" / "locale" / po.stem / "LC_MESSAGES" / f"plasma_applet_{plugin_id}.mo"
            mo.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["msgfmt", "--check", "-o", str(mo), str(po)], check=True)
            written.append(mo)
    return written
