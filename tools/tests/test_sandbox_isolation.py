# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/sandbox.sh no debe escribir en el HOME real: los lanzadores de
install.sh van a GOLDENGLASS_BIN_DIR, dentro del sandbox."""

from __future__ import annotations

import re
import subprocess

from conftest import ROOT


def test_sandbox_exports_bin_dir_before_install() -> None:
    text = (ROOT / "tools" / "sandbox.sh").read_text()
    export = re.search(r'^\s*export GOLDENGLASS_BIN_DIR="\$HOME_DIR/', text, re.M)
    assert export, "sandbox.sh debe fijar GOLDENGLASS_BIN_DIR dentro de HOME_DIR"
    assert export.start() < text.index('"$ROOT/tools/install.sh"')
    assert 'PATH="$GOLDENGLASS_BIN_DIR:$PATH"' in text


def test_install_uses_bin_dir_variable() -> None:
    text = (ROOT / "tools" / "install.sh").read_text()
    assert 'BIN_DIR="${GOLDENGLASS_BIN_DIR:-$HOME/.local/bin}"' in text
    assert "$HOME/.local/bin/goldenglass" not in text


def test_uninstall_touches_only_bin_dir(tmp_path) -> None:
    home, bin_dir = tmp_path / "home", tmp_path / "bin"
    real_bin = home / ".local" / "bin"
    real_bin.mkdir(parents=True)
    bin_dir.mkdir()
    for d in (real_bin, bin_dir):
        (d / "goldenglass-system").write_text("x")
    env = {
        "PATH": "/usr/bin:/bin", "HOME": str(home), "USER": "nobody-gg",
        "XDG_CONFIG_HOME": str(tmp_path / "c"), "XDG_DATA_HOME": str(tmp_path / "d"),
        "XDG_STATE_HOME": str(tmp_path / "s"), "XDG_CACHE_HOME": str(tmp_path / "k"),
        "GOLDENGLASS_BIN_DIR": str(bin_dir),
    }
    subprocess.run(["bash", str(ROOT / "tools" / "install.sh"), "--uninstall"],
                   env=env, check=False, capture_output=True, timeout=120)
    assert not (bin_dir / "goldenglass-system").exists()
    assert (real_bin / "goldenglass-system").exists()
