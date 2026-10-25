# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Entradas dañadas o inesperadas en las herramientas de tools/: tokens y
plantillas mal escritos, estado corrupto, niveles no finitos y D-Bus sin
respuesta. Se ejecuta con:

  python3 -m unittest discover -s tools/tests
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

import gen_tokens  # noqa: E402
import glass  # noqa: E402
import gtk_sync  # noqa: E402
import lookandfeel  # noqa: E402
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

    def test_unknown_lookandfeel_marker_names_template(self) -> None:
        src = lookandfeel.COMMON / "contents" / "x.qml"
        with self.assertRaises(SystemExit) as raised:
            lookandfeel._fill("a @KNOWN@ b @MISPELLED@", {"KNOWN": "1"}, src)
        self.assertIn("@MISPELLED@", str(raised.exception))
        self.assertIn("x.qml", str(raised.exception))
        self.assertEqual(lookandfeel._fill("a @KNOWN@", {"KNOWN": "1"}, src), "a 1")

    def test_unknown_plasmoid_marker_names_template(self) -> None:
        tokens = {"dock": {"icon_size": 48}}
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "main.qml.in"
            template.write_text("size: @dock.icon_size@\n", encoding="utf-8")
            plasmoids._fill_templates(Path(tmp), tokens)
            self.assertEqual((Path(tmp) / "main.qml").read_text(encoding="utf-8"), "size: 48\n")

            bad = Path(tmp) / "bad.qml.in"
            bad.write_text("size: @dock.icon_szie@ @dock.icon_size.x@\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                plasmoids._fill_templates(Path(tmp), tokens)
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
            with self.assertRaises(Exception, msg=text):
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
