#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-dock: ajustes del dock de GoldenGlass en vivo.

  goldenglass-dock --get                      # JSON con los ajustes (null = de fábrica)
  goldenglass-dock --magnification on|off
  goldenglass-dock --magnification-size 96 --icon-size 48 --recent on|off

Escribe la configuración del plasmoid org.goldenglass.dock en todos los
paneles con el script de plasmashell (como el módulo de Ajustes «Dock», que
lo usa); el dock la aplica al momento y ajusta el grosor de su panel. Los
valores de fábrica y los límites de los tamaños son los de los tokens: se
leen del main.xml del plasmoid instalado (esta herramienta no tiene los tokens).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

KEYS = {"iconSize": int, "magnification": bool, "magnificationSize": int, "showRecent": bool}
PLASMOID = "org.goldenglass.dock"
KCFG = "{http://www.kde.org/standards/kcfg/1.0}"


def main_xml() -> Path | None:
    """main.xml del plasmoid instalado, con el orden de búsqueda de XDG."""
    home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    dirs = [home, *(os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")]
    for d in dirs:
        path = Path(d) / "plasma" / "plasmoids" / PLASMOID / "contents" / "config" / "main.xml"
        if d and path.is_file():
            return path
    return None


def limits(path: Path | None = None) -> dict[str, tuple[int, int]]:
    """<min>/<max> de las opciones enteras del main.xml (vacío si no está)."""
    path = path or main_xml()
    if path is None:
        return {}
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError):
        return {}
    result = {}
    for entry in tree.iter(f"{KCFG}entry"):
        low, high = entry.findtext(f"{KCFG}min"), entry.findtext(f"{KCFG}max")
        if entry.get("name") in KEYS and low is not None and high is not None:
            result[entry.get("name")] = (int(low), int(high))
    return result


def evaluate(script: str) -> str:
    """Ejecuta un script de Plasma y devuelve lo que imprime."""
    r = subprocess.run(["dbus-send", "--session", "--print-reply", "--dest=org.kde.plasmashell", "/PlasmaShell",
                        "org.kde.PlasmaShell.evaluateScript", f"string:{script}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"goldenglass-dock: plasmashell no responde: {r.stderr.strip()}")
    out = r.stdout.split("\n", 1)[1] if "\n" in r.stdout else ""
    start, end = out.find('"'), out.rfind('"')
    return out[start + 1:end] if 0 <= start < end else ""


def docks_script(body: str) -> str:
    return ("var docks = [];"
            "panels().forEach(function (p) { p.widgets('org.goldenglass.dock').forEach(function (w) {"
            " w.currentConfigGroup = ['General']; docks.push(w); }); });"
            + body)


def get() -> dict:
    out = evaluate(docks_script(
        "var r = null;"
        "if (docks.length > 0) { r = {};"
        # con null como valor por defecto readConfig no devuelve lo guardado
        + "".join(f"var v_{k} = String(docks[0].readConfig('{k}', '')); r['{k}'] = v_{k} === '' ? null : v_{k};"
                  for k in KEYS)
        + "} print(JSON.stringify(r));"))
    data = json.loads(out or "null")
    if data is None:
        raise SystemExit("goldenglass-dock: no hay ningún dock de GoldenGlass en los paneles")
    result = {}
    for key, kind in KEYS.items():
        value = data.get(key)
        if value is None:
            result[key] = None
        elif kind is bool:
            result[key] = value.lower() == "true"
        else:
            result[key] = int(float(value))
    return result


def set_values(values: dict) -> None:
    assignments = "".join(f"w.writeConfig('{k}', {json.dumps(v)});" for k, v in values.items())
    out = evaluate(docks_script(f"docks.forEach(function (w) {{ {assignments} }}); print(docks.length);"))
    if out.strip() in ("", "0"):
        raise SystemExit("goldenglass-dock: no hay ningún dock de GoldenGlass en los paneles")


def on_off(text: str) -> bool:
    if text not in ("on", "off"):
        raise argparse.ArgumentTypeError("on u off")
    return text == "on"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="goldenglass-dock", description=__doc__.splitlines()[0])
    ap.add_argument("--get", action="store_true", help="muestra los ajustes en JSON")
    ap.add_argument("--magnification", type=on_off, metavar="on|off")
    ap.add_argument("--magnification-size", type=int, metavar="PX")
    ap.add_argument("--icon-size", type=int, metavar="PX")
    ap.add_argument("--recent", type=on_off, metavar="on|off", help="apps recientes en el dock")
    args = ap.parse_args(argv)

    if args.get:
        print(json.dumps(get()))
        return 0
    values = {
        "magnification": args.magnification,
        "magnificationSize": args.magnification_size,
        "iconSize": args.icon_size,
        "showRecent": args.recent,
    }
    values = {k: v for k, v in values.items() if v is not None}
    if not values:
        ap.error("nada que cambiar (o --get)")
    for key, (low, high) in limits().items():
        if key in values and not low <= values[key] <= high:
            ap.error(f"{key} fuera de rango ({low}–{high})")
    if values.get("magnificationSize", sys.maxsize) < values.get("iconSize", 0):
        ap.error("magnificationSize no puede ser menor que iconSize")
    set_values(values)
    return 0


if __name__ == "__main__":
    sys.exit(main())
