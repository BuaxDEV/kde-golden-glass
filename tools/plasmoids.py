# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepara los plasmoids de plasma/plasmoids/ en build/plasma/plasmoids/.

Copia cada paquete, compila sus traducciones (po/<idioma>.po) dentro del
propio paquete, en contents/locale/<idioma>/LC_MESSAGES/plasma_applet_<id>.mo,
donde Plasma las busca para los plasmoids instalados como paquete, y escribe
contents/ui/tokens.js con los tokens (en QML: import "tokens.js" as T).

Además:
  - SHARED: archivos de un plasmoid que otro usa tal cual (el dock lleva el
    panel de Apps y la Papelera); se copian y sus traducciones se unen a las
    del que los usa.
  - Plantillas *.in: @sección.clave@ se sustituye por el token y se quita .in
    (p. ej. los valores de fábrica de contents/config/main.xml).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "plasma" / "plasmoids"

# plasmoid que usa → {plasmoid de origen: [archivos de contents/ui/]}
SHARED = {
    "org.goldenglass.dock": {
        "org.goldenglass.launchpad": ["AppsLauncher.qml", "AppsPanel.qml", "GlassBlur.qml", "GlassScrollView.qml", "categories.js"],
        "org.goldenglass.trash": ["TrashButton.qml"],
    },
}


def _token(tokens: dict, path: str) -> str:
    value = tokens
    for key in path.split("."):
        value = value[key]
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _fill_templates(dst: Path, tokens: dict) -> list[Path]:
    written = []
    for template in sorted(dst.rglob("*.in")):
        text = re.sub(r"@([a-z_]+(?:\.[a-z_]+)+)@", lambda m: _token(tokens, m.group(1)),
                      template.read_text(encoding="utf-8"))
        target = template.with_suffix("")
        target.write_text(text, encoding="utf-8")
        template.unlink()
        written.append(target)
    return written


def _catalogs(src: Path, plugin_id: str) -> dict[str, list[Path]]:
    """idioma → .po del plasmoid y de los plasmoids de los que comparte archivos."""
    found: dict[str, list[Path]] = {}
    for folder in [src, *(SOURCES / origin for origin in SHARED.get(plugin_id, {}))]:
        for po in sorted((folder / "po").glob("*.po")) if (folder / "po").exists() else []:
            found.setdefault(po.stem, []).append(po)
    return found


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
        for origin, files in SHARED.get(plugin_id, {}).items():
            for name in files:
                shutil.copy2(SOURCES / origin / "contents" / "ui" / name, dst / "contents" / "ui" / name)
        if tokens is not None:
            written += _fill_templates(dst, tokens)
            js = dst / "contents" / "ui" / "tokens.js"
            js.write_text("// Generado por tools/gen_tokens.py desde tokens/goldenglass.toml — NO EDITAR\n"
                          ".pragma library\n\nvar tokens = " + json.dumps(tokens, ensure_ascii=False) + ";\n",
                          encoding="utf-8")

        for lang, pos in _catalogs(src, plugin_id).items():
            mo = dst / "contents" / "locale" / lang / "LC_MESSAGES" / f"plasma_applet_{plugin_id}.mo"
            mo.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory() as tmp:
                merged = Path(tmp) / f"{lang}.po"
                # el catálogo propio manda si un texto está en varios
                subprocess.run(["msgcat", "--use-first", "-o", str(merged), *map(str, pos)], check=True)
                subprocess.run(["msgfmt", "--check", "-o", str(mo), str(merged)], check=True)
            written.append(mo)
    return written
