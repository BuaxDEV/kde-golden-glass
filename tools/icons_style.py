# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Estilos de los iconos de apps de GoldenGlass (Apariencia › «Icon & widget style»).

Por ahora solo existe el estilo de fábrica. `tile()` y `App.svg()` de
icons_apps.py ya reciben el estilo para que Transparente y Tintado
(docs/MACOS27-PLAN.md §4.11) se añadan después sin cambiar sus firmas.
"""

from __future__ import annotations

from enum import Enum


class Style(Enum):
    DEFAULT = "default"
