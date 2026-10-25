# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Entradas dañadas o inesperadas en las herramientas de tools/: tokens y
plantillas mal escritos, estado corrupto, niveles no finitos y D-Bus sin
respuesta. Se ejecuta con:

  python3 -m unittest discover -s tools/tests
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import time
import tomllib
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

import gen_tokens  # noqa: E402
import ggcommon  # noqa: E402
import glass  # noqa: E402
import gtk_sync  # noqa: E402
import plasmoids  # noqa: E402
import system  # noqa: E402


def _tokens() -> dict:
    with (TOOLS.parent / "tokens" / "goldenglass.toml").open("rb") as f:
        return tomllib.load(f)


class TokensTest(unittest.TestCase):
    def test_valid_tokens_pass(self) -> None:
        gen_tokens.validate(_tokens())

    def test_missing_section_is_named(self) -> None:
        tokens = _tokens()
        del tokens["dock"]
        with self.assertRaises(SystemExit) as raised:
            gen_tokens.validate(tokens)
        self.assertIn("[dock]", str(raised.exception))

    def test_section_must_be_a_table(self) -> None:
        tokens = _tokens()
        tokens["radius"] = 12
        with self.assertRaises(SystemExit) as raised:
            gen_tokens.validate(tokens)
        self.assertIn("radius", str(raised.exception))

    def test_accessibility_flags_must_be_booleans(self) -> None:
        for key in ("show_borders", "reduce_transparency", "reduce_motion"):
            for bad in (1, "false", None):
                tokens = _tokens()
                if bad is None:
                    del tokens["accessibility"][key]
                else:
                    tokens["accessibility"][key] = bad
                with self.assertRaises(SystemExit) as raised:
                    gen_tokens.validate(tokens)
                self.assertIn(f"[accessibility].{key}", str(raised.exception))

    def test_reduce_transparency_alpha_in_range(self) -> None:
        for good in (0, 0.0, 0.5, 1, 1.0):
            tokens = _tokens()
            tokens["accessibility"]["reduce_transparency_alpha"] = good
            gen_tokens.validate(tokens)
        for bad in (-0.1, 1.01, float("nan"), True, "1.0", None):
            tokens = _tokens()
            if bad is None:
                del tokens["accessibility"]["reduce_transparency_alpha"]
            else:
                tokens["accessibility"]["reduce_transparency_alpha"] = bad
            with self.assertRaises(SystemExit) as raised:
                gen_tokens.validate(tokens)
            self.assertIn("reduce_transparency_alpha", str(raised.exception))

    def test_unknown_template_marker_names_template(self) -> None:
        tokens = {"dock": {"icon_size": 48}}
        self.assertEqual(ggcommon.fill_template("size: @dock.icon_size@", tokens, "x.qml"), "size: 48")
        for marker in ("@dock.icon_szie@", "@dock.icon_size.x@", "@dock.nope.x@"):
            with self.assertRaises(SystemExit) as raised:
                ggcommon.fill_template(f"size: {marker}", tokens, "x.qml")
            self.assertIn("x.qml", str(raised.exception))
            self.assertIn(marker, str(raised.exception))

    def test_unknown_plasmoid_marker_names_template(self) -> None:
        tokens = {"dock": {"icon_size": 48}}
        src = plasmoids.ROOT / "plasma" / "plasmoids" / "org.example"
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "main.qml.in"
            template.write_text("size: @dock.icon_size@\n", encoding="utf-8")
            plasmoids.fill_templates(src, Path(tmp), tokens)
            self.assertEqual((Path(tmp) / "main.qml").read_text(encoding="utf-8"), "size: 48\n")

            bad = Path(tmp) / "bad.qml.in"
            bad.write_text("size: @dock.icon_szie@\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                plasmoids.fill_templates(src, Path(tmp), tokens)
            self.assertIn("bad.qml.in", str(raised.exception))
            self.assertIn("@dock.icon_szie@", str(raised.exception))


class SystemStateTest(unittest.TestCase):
    def _load(self, text: str) -> tuple[dict, str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "system.json"
            path.write_text(text, encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                state = system.load_state(path)
            return state, stderr.getvalue()

    def test_missing_file_is_empty(self) -> None:
        self.assertEqual(system.load_state(Path("/nonexistent/goldenglass/system.json")), {})

    def test_valid_state(self) -> None:
        state = {"sounds": {"kdeglobals/Sounds/Theme": None}}
        self.assertEqual(self._load(json.dumps(state)), (state, ""))

    def test_corrupt_json_is_ignored_with_a_warning(self) -> None:
        state, warning = self._load('{"sounds": {')
        self.assertEqual(state, {})
        self.assertIn("system.json", warning)

    def test_wrong_shape_is_ignored(self) -> None:
        for text in ("[]", '{"sounds": 3}', '"x"'):
            state, warning = self._load(text)
            self.assertEqual(state, {}, text)
            self.assertTrue(warning, text)


class GlassLevelTest(unittest.TestCase):
    def setUp(self) -> None:
        # nada sale de la prueba: ni configuración, ni temas en el HOME, ni D-Bus
        self.kwrite = self._patch("kwrite")
        self._patch("kread", return_value="")
        self.tuned = self._patch("write_tuned_theme")
        self._patch("set_plasma_theme")
        self._patch("dbus")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._patch("data_home", return_value=Path(tmp.name))
        self._patch("cache_home", return_value=Path(tmp.name))

    def _patch(self, name: str, **kwargs) -> mock.Mock:
        patcher = mock.patch.object(glass, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_level_argument_must_be_finite(self) -> None:
        self.assertEqual(glass._level_arg("0.25"), 0.25)
        for text in ("nan", "inf", "-inf", "abc"):
            with self.assertRaises(argparse.ArgumentTypeError, msg=text):
                glass._level_arg(text)

    def test_set_level_rejects_nan(self) -> None:
        with self.assertRaises(ValueError):
            glass.set_level(float("nan"), reload_plasma=False)
        self.kwrite.assert_not_called()
        self.tuned.assert_not_called()

    def test_unreadable_level_is_the_default(self) -> None:
        default = float(_tokens()["glass"]["default_level"])
        for stored in ("garbage", "nan", "inf", ""):
            with mock.patch.object(glass, "kread", return_value=stored):
                self.assertEqual(glass.get_level(), default, stored)
        with mock.patch.object(glass, "kread", return_value="0.4"):
            self.assertEqual(glass.get_level(), 0.4)


class GlassConcurrencyTest(unittest.TestCase):
    """Dos goldenglass-glass a la vez (KCM y slider del Centro de control)."""

    def setUp(self) -> None:
        # HOME, XDG_* y cerrojo temporales; kread/kwrite/D-Bus sustituidos
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        for sub in ("home", "data", "cache", "run"):
            (self.tmp / sub).mkdir()
        env = mock.patch.dict(os.environ, {"HOME": str(self.tmp / "home"), "XDG_DATA_HOME": str(self.tmp / "data"),
                                           "XDG_CACHE_HOME": str(self.tmp / "cache"),
                                           "XDG_RUNTIME_DIR": str(self.tmp / "run")})
        env.start()
        self.addCleanup(env.stop)
        self.writes: list[tuple] = []
        self._patch("kwrite", side_effect=lambda *a: self.writes.append(a))
        self._patch("kread", return_value="")
        self._patch("set_plasma_theme")
        self._patch("dbus")
        self.theme_dir = self.tmp / "data" / "plasma" / "desktoptheme"

    def _patch(self, name: str, **kwargs) -> mock.Mock:
        patcher = mock.patch.object(glass, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def _in_thread(self, argv: list[str]) -> threading.Thread:
        thread = threading.Thread(target=glass.main, args=(argv,))
        thread.start()
        self.addCleanup(thread.join, 10)
        return thread

    def test_lock_path_follows_xdg_runtime_dir_with_a_fallback(self) -> None:
        self.assertEqual(glass.lock_path(), self.tmp / "run" / "goldenglass-glass.lock")
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.tmp / "missing")}):
            self.assertEqual(glass.lock_path(), Path(tempfile.gettempdir()) / f"goldenglass-glass-{os.getuid()}.lock")
        with mock.patch.dict(os.environ):
            del os.environ["XDG_RUNTIME_DIR"]
            self.assertEqual(glass.lock_path().name, f"goldenglass-glass-{os.getuid()}.lock")

    def test_reads_do_not_wait_for_the_lock(self) -> None:
        with glass.session_lock(), mock.patch.object(glass, "effect_available", return_value=True), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            start = time.monotonic()
            for flag in ("--get", "--get-refraction", "--get-menubar-background"):
                self.assertEqual(glass.main([flag]), 0, flag)
            self.assertLess(time.monotonic() - start, 2)
        self.assertEqual(len(out.getvalue().split()), 3)

    def test_writes_wait_for_the_lock(self) -> None:
        for argv in (["--menubar-background", "on"], ["--level", "0.8", "--no-plasma-reload"],
                     ["--refraction", "off"], ["--check"]):
            with self.subTest(argv=argv), mock.patch.object(glass, "effect_available", return_value=True), \
                    mock.patch.object(glass, "effects_call", return_value=""), \
                    mock.patch.object(glass, "write_tuned_theme"):
                self.writes.clear()
                with glass.session_lock():
                    thread = self._in_thread(argv)
                    thread.join(0.3)
                    self.assertTrue(thread.is_alive())
                    self.assertEqual(self.writes, [])
                thread.join(10)
                self.assertFalse(thread.is_alive())
                self.assertTrue(self.writes)

    def test_concurrent_levels_are_serialized_and_the_final_state_is_coherent(self) -> None:
        inside = 0
        overlaps: list[int] = []
        guard = threading.Lock()
        real_write = glass.write_tuned_theme

        def slow_write(tokens: dict, level: float) -> None:
            nonlocal inside
            with guard:
                inside += 1
                overlaps.append(inside)
            time.sleep(0.15)
            real_write(tokens, level)
            with guard:
                inside -= 1

        self._patch("write_tuned_theme", side_effect=slow_write)
        threads = [threading.Thread(target=glass.main, args=(["--level", level, "--no-plasma-reload"],))
                   for level in ("0.1", "0.9", "0.2", "0.8")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(60)
            self.assertFalse(thread.is_alive())
        self.assertEqual(max(overlaps), 1)
        # lo último escrito en goldenglassrc y el tema Tuned son del mismo nivel
        last = [w for w in self.writes if w[1:3] == ("Glass", "Level")][-1][3]
        meta = json.loads((self.theme_dir / glass.TUNED_ID / "metadata.json").read_text(encoding="utf-8"))
        self.assertIn(f"level {float(last):.2f} ", meta["KPlugin"]["Description"])
        self.assertTrue((self.theme_dir / glass.TUNED_ID / "metadata.json").is_file())

    def test_lock_leaves_only_its_own_file(self) -> None:
        for _ in range(2):
            with glass.session_lock():
                pass
        self.assertEqual([p.name for p in (self.tmp / "run").iterdir()], ["goldenglass-glass.lock"])
        # el archivo sigue ahí: borrarlo dejaría que dos procesos tuvieran cerrojos distintos
        self.assertEqual((self.tmp / "run" / "goldenglass-glass.lock").stat().st_mode & 0o777, 0o600)

    def test_lock_that_cannot_be_opened_does_not_block_the_tool(self) -> None:
        lock = self.tmp / "run" / "goldenglass-glass.lock"
        lock.symlink_to(self.tmp / "elsewhere")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), glass.session_lock():
            pass
        self.assertIn("sin cerrojo", stderr.getvalue())

    def _build(self, level: float) -> None:
        glass.write_tuned_theme(ggcommon.load_tokens(), level)

    def _description(self) -> str:
        meta = json.loads((self.theme_dir / glass.TUNED_ID / "metadata.json").read_text(encoding="utf-8"))
        return meta["KPlugin"]["Description"]

    def test_tuned_theme_is_replaced_whole_and_leaves_no_staging_dirs(self) -> None:
        cache = self.tmp / "cache" / f"plasma_theme_{glass.TUNED_ID}.kcache"
        self._build(0.2)
        self.assertIn("level 0.20", self._description())
        cache.write_text("stale")
        stale = self.theme_dir / glass.TUNED_ID / "stale-file"
        stale.write_text("x")
        self._build(0.8)
        self.assertIn("level 0.80", self._description())
        self.assertFalse(stale.exists(), "el tema nuevo reemplaza al anterior entero")
        self.assertFalse(cache.exists())
        self.assertEqual([p.name for p in self.theme_dir.iterdir()], [glass.TUNED_ID])

    def test_tuned_theme_replacement_without_renameat2(self) -> None:
        self._build(0.2)
        with mock.patch.object(glass, "_exchange", return_value=False):
            self._build(0.8)
        self.assertIn("level 0.80", self._description())
        self.assertEqual([p.name for p in self.theme_dir.iterdir()], [glass.TUNED_ID])

    def test_failed_generation_keeps_the_previous_tuned_theme(self) -> None:
        self._build(0.2)
        with mock.patch.object(glass.shutil, "copytree", side_effect=OSError("disco lleno")), \
                self.assertRaises(OSError):
            self._build(0.8)
        self.assertIn("level 0.20", self._description())
        self.assertEqual([p.name for p in self.theme_dir.iterdir()], [glass.TUNED_ID])


class GtkSyncTest(unittest.TestCase):
    def test_failed_dbus_call_gives_no_theme(self) -> None:
        try:
            from PyQt6.QtDBus import QDBusMessage
        except ImportError:
            self.skipTest("sin PyQt6")
        reply = mock.Mock()
        reply.type.return_value = QDBusMessage.MessageType.ErrorMessage
        reply.arguments.return_value = []
        gtk = mock.Mock()
        gtk.call.return_value = reply
        self.assertIsNone(gtk_sync._gtk_theme(gtk))

        reply.type.return_value = QDBusMessage.MessageType.ReplyMessage
        reply.arguments.return_value = ["Breeze"]
        self.assertEqual(gtk_sync._gtk_theme(gtk), "Breeze")

    def test_sync_errors_do_not_escape(self) -> None:
        stderr = io.StringIO()
        with mock.patch.object(gtk_sync, "sync", side_effect=IndexError("kded")), contextlib.redirect_stderr(stderr):
            self.assertFalse(gtk_sync._safe_sync())
        self.assertIn("kded", stderr.getvalue())


class WrapIconsTest(unittest.TestCase):
    def test_fingerprint_covers_the_drawing_modules(self) -> None:
        import wrap_icons

        names = {path.name for path in wrap_icons._generator_files()}
        self.assertTrue({"wrap_icons.py", "icons.py", "icons_apps.py"} <= names, names)


if __name__ == "__main__":
    unittest.main()
