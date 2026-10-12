#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-system: activa o desactiva las partes de GoldenGlass que no
aplica el Global Theme (sonidos, chime; más adelante Plymouth y login).

Los paquetes solo instalan; esto es lo que las activa. Antes de cambiar un
valor se guarda el anterior y `disable` lo restaura (si no existía, se borra).

  goldenglass-system status [PARTE…] [--json]
  goldenglass-system enable PARTE…
  goldenglass-system disable PARTE…

Partes:
  sounds   tema de sonidos GoldenGlass (kdeglobals) y sonido de Spectacle al
           guardar una captura
  chime    sonido al iniciar sesión en Plasma

Estado guardado: ~/.local/state/goldenglass/system.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "goldenglass" / "system.json"
UNSET = "__goldenglass_unset__"  # kreadconfig6 lo devuelve si la clave no existe


@dataclass(frozen=True)
class Entry:
    """Una clave de configuración de KDE (archivo en ~/.config, grupo, clave)."""
    file: str
    group: str
    key: str
    value: str

    @property
    def id(self) -> str:
        return f"{self.file}/{self.group}/{self.key}"


PARTS: dict[str, tuple[Entry, ...]] = {
    "sounds": (
        Entry("kdeglobals", "Sounds", "Theme", "GoldenGlass"),
        # Spectacle no suena al capturar: como macOS, con el sonido del obturador
        Entry("spectacle.notifyrc", "Event/newScreenshotSaved", "Action", "Popup|Sound"),
        Entry("spectacle.notifyrc", "Event/newScreenshotSaved", "Sound", "screen-capture"),
    ),
    "chime": (
        # Plasma trae el evento de inicio de sesión sin acción
        Entry("plasma_workspace.notifyrc", "Event/startkde", "Action", "Sound"),
    ),
}


def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"goldenglass-system: falta {name} (paquete kconfig)")
    return path


def read(entry: Entry) -> str | None:
    out = subprocess.run(
        [_tool("kreadconfig6"), "--file", entry.file, "--group", entry.group,
         "--key", entry.key, "--default", UNSET],
        check=True, capture_output=True, text=True,
    ).stdout.rstrip("\n")
    return None if out == UNSET else out


def write(entry: Entry, value: str | None) -> None:
    args = [_tool("kwriteconfig6"), "--notify", "--file", entry.file,
            "--group", entry.group, "--key", entry.key]
    args += ["--delete"] if value is None else [value]
    subprocess.run(args, check=True)


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(STATE)


def is_enabled(part: str) -> bool:
    return all(read(e) == e.value for e in PARTS[part])


def enable(part: str, state: dict) -> None:
    saved = state.setdefault(part, {})
    for entry in PARTS[part]:
        current = read(entry)
        if current == entry.value:
            continue
        # el valor previo se guarda una sola vez: un segundo enable no lo pisa
        saved.setdefault(entry.id, current)
        write(entry, entry.value)


def disable(part: str, state: dict) -> None:
    saved = state.pop(part, {})
    for entry in PARTS[part]:
        if read(entry) != entry.value:
            continue  # lo cambió el usuario después: se respeta
        write(entry, saved.get(entry.id))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="goldenglass-system", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    st = sub.add_parser("status", help="muestra qué partes están activas")
    st.add_argument("parts", nargs="*", metavar="PARTE")
    st.add_argument("--json", action="store_true", help="salida JSON (la usa el módulo de Ajustes)")
    for name in ("enable", "disable"):
        p = sub.add_parser(name, help=f"{name} de las partes indicadas")
        p.add_argument("parts", nargs="+", metavar="PARTE")
    args = ap.parse_args(argv)

    unknown = [p for p in args.parts if p not in PARTS]
    if unknown:
        ap.error(f"partes desconocidas: {', '.join(unknown)} (hay: {', '.join(PARTS)})")

    if args.command == "status":
        status = {part: is_enabled(part) for part in (args.parts or PARTS)}
        if args.json:
            print(json.dumps(status))
        else:
            for part, on in status.items():
                print(f"{part}: {'enabled' if on else 'disabled'}")
        return 0

    state = load_state()
    try:
        for part in args.parts:
            (enable if args.command == "enable" else disable)(part, state)
    finally:
        save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
