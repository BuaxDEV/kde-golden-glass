# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Update scripts of the GoldenGlass shell (contents/updates/), which
plasmashell runs once per user. They run here in a QJSEngine against a fake
panels() of the Plasma scripting API."""

from __future__ import annotations

import json

import pytest
from conftest import ROOT
from ggcommon import fill_template

QtGui = pytest.importorskip("PyQt6.QtGui")
QtQml = pytest.importorskip("PyQt6.QtQml")

UPDATES = ROOT / "plasma" / "shell" / "org.goldenglass.desktop" / "contents" / "updates"
MENUBAR_SCRIPT = UPDATES / "goldenglass_menubar_height.js.in"
OLD_MENUBAR_HEIGHT = 28

FAKE_SCRIPTING_API = """
var fakePanels = %s.map(p => ({
    location: p.location,
    height: p.height,
    widgets: type => p.widgets.filter(w => w === type),
}));
function panels() { return fakePanels; }
"""


@pytest.fixture(scope="module", autouse=True)
def _application():
    """QJSEngine aborts without a Qt application. A GUI one, offscreen, as the
    icon generators expect if they run later in the same session."""
    return QtGui.QGuiApplication.instance() or QtGui.QGuiApplication(["goldenglass-tests", "-platform", "offscreen"])


def run_update(tokens: dict, panels: list[dict]) -> list[int]:
    """Heights of `panels` after the menu bar script ran over them."""
    engine = QtQml.QJSEngine()
    script = fill_template(MENUBAR_SCRIPT.read_text(encoding="utf-8"), tokens, MENUBAR_SCRIPT)
    for code in (FAKE_SCRIPTING_API % json.dumps(panels), script):
        result = engine.evaluate(code)
        assert not result.isError(), result.toString()
    return [engine.evaluate(f"fakePanels[{i}].height").toInt() for i in range(len(panels))]


def menubar(height: int, location: str = "top") -> dict:
    return {"location": location, "height": height,
            "widgets": ["org.goldenglass.systemmenu", "org.kde.plasma.appmenu", "org.kde.plasma.systemtray"]}


def test_a_menubar_at_the_old_height_takes_the_new_one(tokens: dict) -> None:
    new_height = tokens["plasma"]["menubar_height"]
    assert run_update(tokens, [menubar(OLD_MENUBAR_HEIGHT), menubar(OLD_MENUBAR_HEIGHT)]) == [new_height] * 2


@pytest.mark.parametrize("panel", [
    menubar(30),
    menubar(OLD_MENUBAR_HEIGHT, location="bottom"),
    {"location": "top", "height": OLD_MENUBAR_HEIGHT, "widgets": ["org.kde.plasma.kickoff"]},
], ids=["height chosen by the user", "not at the top", "without the logo menu"])
def test_other_panels_keep_their_height(tokens: dict, panel: dict) -> None:
    assert run_update(tokens, [panel]) == [panel["height"]]
