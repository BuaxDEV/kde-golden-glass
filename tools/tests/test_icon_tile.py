# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""icons_apps: los tokens [icon_tile] dibujan el squircle y la salida no cambia sin querer.

Decisión: el refactor a tokens exigía salida idéntica byte a byte. A futuro no
se puede comparar con el código antiguo, así que:
  - icon_tile_golden.py guarda el SHA-256 del SVG de cada app (claro y oscuro) y
    de dos llamadas directas a tile() como las de wrap_icons.py. Si cambia un
    token o un dibujo a propósito, se regenera con
        python3 tools/tests/test_icon_tile.py --update
    y el diff del archivo documenta el cambio visual en el PR.
  - Cada token de [icon_tile] debe cambiar el SVG (si no, estaría muerto o
    seguiría escrito en el código).
La app de Fuentes se deja fuera de los hashes: su «Aa» sale de la fuente
instalada y de Qt, y no es determinista entre equipos.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # tools/, para ejecutarlo con --update

import icons_apps  # noqa: E402
from gen_tokens import validate_icon_tile  # noqa: E402
from icon_tile_golden import GOLDEN  # noqa: E402
from icons_style import Style  # noqa: E402

GOLDEN_FILE = Path(__file__).resolve().parent / "icon_tile_golden.py"


def render(tt: icons_apps.TileTokens) -> dict[str, str]:
    """Nombre → SVG de todo lo que depende de [icon_tile]."""
    out = {}
    for app in icons_apps.APPS:
        if app.glyph is icons_apps.fonts:
            continue
        for dark in (False, True):
            out[f"{app.names[0]}.{'dark' if dark else 'light'}"] = app.svg(dark, tt=tt)
    for dark in (False, True):  # como wrap_icons.wrap()
        bg = tt.graphite if dark else tt.wrap_paper
        out[f"wrap.{'dark' if dark else 'light'}"] = icons_apps.tile(bg, tt.white, "<g/>", dark, tt=tt)
    return out


def digest(svgs: dict[str, str]) -> dict[str, str]:
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in sorted(svgs.items())}


@pytest.fixture
def tile_tokens(tokens) -> icons_apps.TileTokens:
    return icons_apps.TileTokens.from_tokens(tokens)


def test_output_matches_golden_hashes(tile_tokens):
    assert digest(render(tile_tokens)) == GOLDEN, "el dibujo cambió: revísalo y, si es a propósito, --update"


def test_default_tokens_are_the_toml_ones(tile_tokens):
    assert icons_apps.tile_tokens() == tile_tokens


def test_files_uses_given_tokens(tokens):
    other = copy.deepcopy(tokens)
    other["icon_tile"]["shadow_alpha"] = 0.5
    assert icons_apps.files(other) != icons_apps.files(tokens)


def test_style_default_is_implicit(tile_tokens):
    app = icons_apps.APPS[0]
    for dark in (False, True):
        assert app.svg(dark, Style.DEFAULT, tile_tokens) == app.svg(dark, tt=tile_tokens)


def _changed(key: str, value):
    if isinstance(value, list):
        return ["#123456", "#654321"]
    if isinstance(value, str):
        return "#123456"
    return value / 2 if value else 0.5


@pytest.mark.parametrize("key", sorted(icons_apps.TileTokens.__dataclass_fields__))
def test_every_token_changes_the_svg(tokens, tile_tokens, key):
    other = copy.deepcopy(tokens)
    other["icon_tile"][key] = _changed(key, other["icon_tile"][key])
    assert render(icons_apps.TileTokens.from_tokens(other)) != render(tile_tokens), key


def test_toml_has_exactly_the_fields_of_tiletokens(tokens):
    assert set(tokens["icon_tile"]) == set(icons_apps.TileTokens.__dataclass_fields__)


def test_number_format_matches_the_old_literals():
    assert [icons_apps._alpha(v) for v in (0.30, 0.06, 0.55, 0.1, 1, 0)] == [".30", ".06", ".55", ".10", "1.00", ".00"]
    assert [icons_apps._length(v) for v in (1.3, 0.8, 0.4, 1, 10, 0)] == ["1.3", ".8", ".4", "1", "10", "0"]


# --- tokens instalados (icon-tile.json) ------------------------------------------

@pytest.fixture
def installed(tokens, tmp_path, monkeypatch):
    """Simula el paquete: sin TOML del repositorio y con icon-tile.json en XDG_DATA_DIRS."""
    data = tmp_path / "share"
    icons_apps.write_tile_json(tokens, data / "goldenglass" / icons_apps.TILE_JSON)
    monkeypatch.setattr(icons_apps, "REPO_TOKENS", tmp_path / "no-such.toml")
    monkeypatch.setattr(icons_apps, "HERE", tmp_path / "tools")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_DATA_DIRS", str(data))
    icons_apps._default_tile_tokens.cache_clear()
    yield data
    icons_apps._default_tile_tokens.cache_clear()


def test_generated_json_matches_the_toml_section(tokens, tmp_path):
    path = icons_apps.write_tile_json(tokens, tmp_path / "icon-tile.json")
    assert json.loads(path.read_text(encoding="utf-8")) == {"icon_tile": tokens["icon_tile"]}


def test_build_writes_the_json(tokens, tmp_path, monkeypatch):
    import icons
    import icons_mime

    # solo interesa el archivo de datos: sin fuentes del sistema ni iconos
    monkeypatch.setattr(icons, "_family", lambda tokens: "Inter")
    monkeypatch.setattr(icons, "ICONS", [])
    monkeypatch.setattr(icons, "_guards", lambda *args, **kwargs: None)
    monkeypatch.setattr(icons_apps, "files", lambda *args, **kwargs: [])
    monkeypatch.setattr(icons_mime, "files", lambda family: [])
    written = icons.build(tokens, tmp_path)
    path = tmp_path / "icons" / icons_apps.TILE_JSON
    assert path in written
    assert json.loads(path.read_text(encoding="utf-8")) == {"icon_tile": tokens["icon_tile"]}


def test_installed_json_gives_the_same_drawing(installed, tile_tokens):
    assert icons_apps.tile_tokens_source() == installed / "goldenglass" / icons_apps.TILE_JSON
    assert icons_apps.tile_tokens() == tile_tokens
    assert digest(render(icons_apps.tile_tokens())) == GOLDEN


def test_installed_json_next_to_tools(installed, tokens, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "empty"))
    icons_apps.write_tile_json(tokens, tmp_path / icons_apps.TILE_JSON)  # HERE.parent == tmp_path
    assert icons_apps.tile_tokens_source() == tmp_path / icons_apps.TILE_JSON


def test_missing_tokens_fail_clearly(installed, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "empty"))
    assert icons_apps.tile_tokens_source() is None
    with pytest.raises(SystemExit, match="icon-tile.json"):
        icons_apps.tile_tokens()


def test_icon_tools_do_not_import_ggcommon():
    code = ("import sys; sys.path.insert(0, 'tools'); import icons_apps, wrap_icons; "
            "icons_apps.tile_tokens(); assert 'ggcommon' not in sys.modules")
    root = Path(__file__).resolve().parent.parent.parent
    assert subprocess.run([sys.executable, "-c", code], cwd=root, check=False).returncode == 0


# --- validación de gen_tokens --------------------------------------------------

@pytest.mark.parametrize("key, value", [
    ("sheen_light", 1.5),
    ("rim_mid", -0.1),
    ("shadow_blur", 20),
    ("shadow_dy", -1),
    ("edge_alpha", "0.2"),
    ("graphite", ["#3A3A3E"]),
    ("white", ["#FFFFFF", "#GG0000"]),
    ("paper", ["#FFFFFF", "#E4E6EB80"]),
    ("highlight", "#FFF"),
])
def test_validate_rejects_bad_values(tokens, key, value):
    section = copy.deepcopy(tokens["icon_tile"])
    section[key] = value
    with pytest.raises(SystemExit, match=key):
        validate_icon_tile(section)


def test_validate_rejects_missing_and_unknown_keys(tokens):
    section = copy.deepcopy(tokens["icon_tile"])
    del section["edge_width"]
    with pytest.raises(SystemExit, match="edge_width"):
        validate_icon_tile(section)
    section = copy.deepcopy(tokens["icon_tile"])
    section["nope"] = 1
    with pytest.raises(SystemExit, match="nope"):
        validate_icon_tile(section)


def test_validate_accepts_the_real_tokens(tokens):
    validate_icon_tile(tokens["icon_tile"])


def _update() -> None:
    import ggcommon

    hashes = digest(render(icons_apps.TileTokens.from_tokens(ggcommon.load_tokens())))
    lines = [
        # REUSE-IgnoreStart
        "# SPDX-FileCopyrightText: 2026 GoldenGlass contributors",
        "# SPDX-License-Identifier: GPL-3.0-or-later",
        # REUSE-IgnoreEnd
        '"""SHA-256 del SVG de cada icono de app (generado: python3 tools/tests/test_icon_tile.py --update)."""',
        "",
        "GOLDEN = {",
        *(f'    "{k}":\n        "{v}",' for k, v in hashes.items()),
        "}",
        "",
    ]
    GOLDEN_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(hashes)} hashes en {GOLDEN_FILE}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--update"]:
        _update()
    else:
        raise SystemExit("uso: test_icon_tile.py --update")
