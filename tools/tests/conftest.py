# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Configuración común de las pruebas de tools/ (pytest desde la raíz del repo)."""

from __future__ import annotations

import copy
import sys
import tomllib
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))


@pytest.fixture(scope="session")
def _tokens() -> dict:
    with (ROOT / "tokens" / "goldenglass.toml").open("rb") as f:
        return tomllib.load(f)


@pytest.fixture
def tokens(_tokens: dict) -> dict:
    """Los tokens reales; cada prueba recibe una copia que puede modificar."""
    return copy.deepcopy(_tokens)
