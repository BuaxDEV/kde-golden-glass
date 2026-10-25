#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the GoldenGlass shell's update scripts for a development install.

plasmashell runs each contents/updates/ script of a shell once, but only for
shells in the system data dirs: under XDG_DATA_HOME (tools/install.sh) they
never run. tools/install.sh starts this at login; it runs the pending scripts
through evaluateScript and records them in plasmashellrc [Updates] performed,
the list plasmashell keeps, so a later package install skips them too.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import dock

SHELL_ID = "org.goldenglass.desktop"
PLASMASHELL_WAIT_S = 60
PANEL_ATTEMPTS = 10
PANEL_RETRY_S = 2
# plasmashell may answer before it has loaded the panels: an update run then
# would change nothing and still be recorded as performed
COUNT_PANELS = "\nprint(panels().length);"


def user_updates_dir() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(data_home) / "plasma" / "shells" / SHELL_ID / "contents" / "updates"


def performed() -> list[str]:
    out = subprocess.run(["kreadconfig6", "--file", "plasmashellrc", "--group", "Updates", "--key", "performed"],
                         capture_output=True, text=True, check=True).stdout.strip()
    return [entry for entry in out.split(",") if entry]


def record(done: list[str]) -> None:
    subprocess.run(["kwriteconfig6", "--file", "plasmashellrc", "--group", "Updates", "--key", "performed",
                    ",".join(done)], check=True)


def pending(scripts: list[Path], done: list[str]) -> list[Path]:
    """Scripts not performed yet, by name: the system package's copy has another path."""
    done_names = {Path(entry).name for entry in done}
    return [script for script in scripts if script.name not in done_names]


def wait_for_plasmashell() -> bool:
    try:
        return subprocess.run(["gdbus", "wait", "--session", "--timeout", str(PLASMASHELL_WAIT_S),
                               "org.kde.plasmashell"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def run(script: Path) -> bool:
    """Run `script` once panels exist; whether it ran over any."""
    code = script.read_text(encoding="utf-8") + COUNT_PANELS
    for attempt in range(PANEL_ATTEMPTS):
        if attempt:
            time.sleep(PANEL_RETRY_S)
        panels = dock.evaluate(code).strip()
        if panels.isdigit() and int(panels) > 0:
            return True
    return False


def main() -> int:
    todo = pending(sorted(user_updates_dir().glob("*.js")), performed())
    if not todo or not wait_for_plasmashell():
        return 0
    done = performed()
    for script in todo:
        if run(script):
            done.append(str(script))
            record(done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
