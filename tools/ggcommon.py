# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Utilidades comunes de los generadores de GoldenGlass.

  Color          color de los tokens ("#RRGGBB" o "#RRGGBBAA")
  load_tokens()  lee tokens/goldenglass.toml (con meta.version desde VERSION)
  fill_template  sustituye los marcadores @sección.clave@ por los tokens
  stamp()        huella de lo que usa un generador con caché

Se instala junto a glass.py y plasma_theme.py (CMakeLists.txt): goldenglass-glass
lo usa en el equipo del usuario, así que solo depende de la biblioteca estándar.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "tokens" / "goldenglass.toml"
VERSION = ROOT / "VERSION"


# --- color ------------------------------------------------------------------

class Color:
    __slots__ = ("r", "g", "b", "a")

    def __init__(self, r: int, g: int, b: int, a: float = 1.0):
        self.r, self.g, self.b, self.a = r, g, b, a

    @classmethod
    def parse(cls, value: str) -> "Color":
        h = value.lstrip("#")
        if len(h) not in (6, 8):
            raise ValueError(f"color inválido: {value!r}")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return cls(r, g, b, a)

    @property
    def alpha8(self) -> int:
        """Alfa en 0..255."""
        return round(self.a * 255)

    def over(self, bg: "Color") -> "Color":
        """Aplana este color (con alfa) sobre un fondo opaco."""
        a = self.a
        return Color(*(round(c * a + b * (1 - a))
                       for c, b in ((self.r, bg.r), (self.g, bg.g), (self.b, bg.b))))

    def mix(self, other: "Color", t: float) -> "Color":
        return Color(*(round(a + (b - a) * t)
                       for a, b in ((self.r, other.r), (self.g, other.g), (self.b, other.b))))

    def rgb(self) -> tuple[int, int, int]:
        return self.r, self.g, self.b

    def hex(self) -> str:
        """#RRGGBB (sin alfa)."""
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def kde(self) -> str:
        return f"{self.r},{self.g},{self.b}"


def flatten(fg: str, bg: str) -> str:
    """#RRGGBB[AA] sobre #RRGGBB → #RRGGBB."""
    return Color.parse(fg).over(Color.parse(bg)).hex()


# --- tokens -----------------------------------------------------------------

def load_tokens(path: Path | None = None) -> dict:
    """Tokens de `path` (por defecto tokens/goldenglass.toml).

    La versión sale de VERSION, la única fuente (CMake y el PKGBUILD también la
    leen de ahí): se añade como meta.version. Instalado, VERSION va junto a
    tokens/ (CMakeLists.txt).
    """
    with (path or TOKENS).open("rb") as f:
        tokens = tomllib.load(f)
    if "version" in tokens.get("meta", {}):
        raise SystemExit("meta.version no va en los tokens: la versión sale del archivo VERSION")
    tokens.setdefault("meta", {})["version"] = VERSION.read_text(encoding="utf-8").strip()
    return tokens


# --- plantillas -------------------------------------------------------------

# @sección.clave@ (al menos un punto): no confunde correos ni otras arrobas
MARKER = re.compile(r"@([a-z0-9_]+(?:\.[a-z0-9_]+)+)@")


def token_value(tokens: dict, path: str) -> str:
    """Valor del token `path` (sección.clave) como texto; KeyError si no existe."""
    value = tokens
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise KeyError(path)
        value = value[key]
    if isinstance(value, dict):
        raise KeyError(path)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def fill_template(text: str, tokens: dict, name: str | Path) -> str:
    """Sustituye cada @sección.clave@ de `text` por su token.

    `name` (la plantilla) solo sirve para el mensaje de error si falta uno.
    """
    def replace(match: re.Match) -> str:
        try:
            return token_value(tokens, match.group(1))
        except KeyError:
            raise SystemExit(f"{name}: el marcador @{match.group(1)}@ no es ningún token") from None
    return MARKER.sub(replace, text)


# --- caché ------------------------------------------------------------------

def stamp(*paths: Path, data: object = None) -> str:
    """Huella de los archivos `paths` y de `data` (JSON): si no cambia, un
    generador con caché puede saltarse el trabajo."""
    h = hashlib.sha256()
    for path in paths:
        h.update(Path(path).read_bytes())
    if data is not None:
        h.update(json.dumps(data, sort_keys=True).encode())
    return h.hexdigest()
