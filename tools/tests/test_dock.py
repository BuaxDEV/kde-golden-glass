# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""dock (goldenglass-dock): los límites de los tamaños salen del main.xml del
plasmoid instalado, el mismo que genera tools/plasmoids.py desde los tokens.

Nada llega a plasmashell: evaluate() se sustituye y XDG_DATA_HOME/XDG_DATA_DIRS
apuntan a un directorio temporal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import dock
from ggcommon import fill_template

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE = ROOT / "plasma" / "plasmoids" / dock.PLASMOID / "contents" / "config" / "main.xml.in"


@pytest.fixture
def installed(tokens, tmp_path, monkeypatch):
    """main.xml generado desde los tokens, instalado en un XDG_DATA_HOME temporal."""
    config = tmp_path / "data" / "plasma" / "plasmoids" / dock.PLASMOID / "contents" / "config"
    config.mkdir(parents=True)
    path = config / "main.xml"
    path.write_text(fill_template(TEMPLATE.read_text(encoding="utf-8"), tokens, TEMPLATE.name), encoding="utf-8")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "none"))
    calls = []
    monkeypatch.setattr(dock, "evaluate", lambda script: calls.append(script) or "1")
    return calls


def test_limits_match_tokens(tokens, installed):
    d = tokens["dock"]
    assert dock.limits() == {
        "iconSize": (d["icon_size_min"], d["icon_size_max"]),
        "magnificationSize": (d["icon_size_min"], d["magnification_size_max"]),
    }


def test_out_of_range_is_rejected(tokens, installed):
    with pytest.raises(SystemExit):
        dock.main(["--icon-size", str(tokens["dock"]["icon_size_max"] + 1)])
    with pytest.raises(SystemExit):
        dock.main(["--icon-size", "64", "--magnification-size", "48"])
    assert installed == []
    assert dock.main(["--icon-size", str(tokens["dock"]["icon_size_max"])]) == 0
    assert len(installed) == 1


def test_without_plasmoid_no_limits(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "a"))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "b"))
    assert dock.limits() == {}
