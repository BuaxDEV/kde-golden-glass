# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/sandbox.sh no debe escribir en el HOME real: los lanzadores de
install.sh van a GOLDENGLASS_BIN_DIR, dentro del sandbox."""

from __future__ import annotations

import getpass
import re
import subprocess
import sys
import uuid

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


def _reap_script(sandbox_id: str) -> str:
    text = (ROOT / "tools" / "sandbox.sh").read_text()
    functions = text[text.index("sandbox_socket() {"):text.index("# --- Proceso externo")]
    return f'{functions}\nreap "{sandbox_id}"\n'


def test_reap_closes_processes_known_only_by_their_kwin_socket() -> None:
    """kwin_wayland has file capabilities, so its environ cannot be read: the
    socket name on its command line identifies it instead."""
    sandbox_id = f"goldenglass-test-{uuid.uuid4().hex}"
    socket = f"gg-sandbox-{sandbox_id}"
    env = {"PATH": "/usr/bin:/bin", "USER": getpass.getuser()}
    sleeper = [sys.executable, "-c", "import time; time.sleep(300)", "--socket"]
    ours = subprocess.Popen([*sleeper, socket], env=env)
    other = subprocess.Popen([*sleeper, f"{socket}-other"], env=env)
    try:
        subprocess.run(["bash", "-c", _reap_script(sandbox_id)], env=env, check=True, timeout=30)
        assert ours.wait(timeout=5) is not None
        assert other.poll() is None, "a process of another sandbox was closed"
    finally:
        for process in (ours, other):
            process.kill()
            process.wait()
