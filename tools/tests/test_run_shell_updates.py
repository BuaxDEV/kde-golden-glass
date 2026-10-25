# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/run_shell_updates.py: the shell's update scripts for a development
install. Nothing reaches plasmashell or plasmashellrc: evaluate(), the config
access and the wait for plasmashell are replaced."""

from __future__ import annotations

from pathlib import Path

import pytest
import run_shell_updates as updates

SCRIPT = "goldenglass_menubar_height.js"
SYSTEM_COPY = f"/usr/share/plasma/shells/org.goldenglass.desktop/contents/updates/{SCRIPT}"
PLASMA_UPDATE = "/usr/share/plasma/shells/org.kde.plasma.desktop/contents/updates/containmentactions_middlebutton.js"


class Session:
    def __init__(self, performed: list[str], panels: str = "2") -> None:
        self.performed = performed
        self.panels = panels
        self.evaluated: list[str] = []
        self.waited = False

    def evaluate(self, code: str) -> str:
        self.evaluated.append(code)
        return self.panels

    def wait(self) -> bool:
        self.waited = True
        return True


@pytest.fixture
def scripts(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    folder = updates.user_updates_dir()
    folder.mkdir(parents=True)
    (folder / SCRIPT).write_text("panels();\n", encoding="utf-8")
    return folder


def start(monkeypatch, session: Session) -> None:
    monkeypatch.setattr(updates, "performed", lambda: list(session.performed))
    monkeypatch.setattr(updates, "record", lambda done: setattr(session, "performed", done))
    monkeypatch.setattr(updates.dock, "evaluate", session.evaluate)
    monkeypatch.setattr(updates, "wait_for_plasmashell", session.wait)
    monkeypatch.setattr(updates.time, "sleep", lambda seconds: None)


def test_a_pending_script_runs_once_and_is_recorded_with_plasma_ones(scripts, monkeypatch) -> None:
    session = Session([PLASMA_UPDATE])
    start(monkeypatch, session)

    updates.main()
    updates.main()

    assert len(session.evaluated) == 1
    assert session.evaluated[0].startswith("panels();")
    assert session.performed == [PLASMA_UPDATE, str(scripts / SCRIPT)]


def test_a_script_the_system_package_ran_is_skipped(scripts, monkeypatch) -> None:
    session = Session([SYSTEM_COPY])
    start(monkeypatch, session)

    updates.main()

    assert session.evaluated == []
    assert not session.waited


def test_without_panels_yet_it_retries_and_records_nothing(scripts, monkeypatch) -> None:
    session = Session([], panels="0")
    start(monkeypatch, session)

    updates.main()

    assert len(session.evaluated) == updates.PANEL_ATTEMPTS
    assert session.performed == []


def test_without_the_shell_installed_nothing_happens(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    session = Session([])
    start(monkeypatch, session)

    updates.main()

    assert session.evaluated == []
    assert not session.waited
