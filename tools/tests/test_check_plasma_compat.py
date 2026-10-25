# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""check_plasma_compat: el manifiesto de la API privada de Plasma.

Las pruebas de comportamiento montan un árbol falso en tmp_path (qmldir,
.qmltypes, plugin, XML y .desktop) y comprueban qué errores salen cuando falta
algo. Las de «guarda» recorren el QML y el manifiesto reales (sin necesitar
Plasma instalado) para que el manifiesto no se quede viejo.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

import check_plasma_compat as cpc

ROOT = Path(__file__).resolve().parent.parent.parent
MODULE = "org.kde.fake"
USER = "plasma/plasmoids/org.fake/contents/ui/main.qml"

QMLTYPES = """\
import QtQuick.tooling 1.2

// generado
Module {
    Component {
        file: "qabstractitemmodel.h"
        name: "QAbstractItemModel"
        accessSemantics: "reference"
        prototype: "QObject"
        Method { name: "rowCount"; lineNumber: 3 }
        Signal {
            name: "dataChanged"
            Parameter { name: "topLeft"; type: "QModelIndex" }
        }
    }
    Component {
        file: "base.h"
        name: "Fake::BaseModel"
        accessSemantics: "reference"
        prototype: "QAbstractItemModel"
        Property { name: "inherited"; type: "int"; read: "inherited"; index: 0 }
    }
    Component {
        file: "fakemodel.h"
        name: "Fake::FakeModel"
        accessSemantics: "reference"
        prototype: "Fake::BaseModel"
        exports: ["org.kde.fake/FakeModel 1.0", "org.kde.fake/FakeModel 2.0"]
        exportMetaObjectRevisions: [256, 512]
        Enum {
            name: "Mode"
            isScoped: true
            values: ["Alpha", "Beta", "Gamma"]
        }
        Enum {
            name: "Flags"
            alias: "Flag"
            values: [
                "FlagOne",
                "FlagTwo" // comentario
            ]
        }
        Property {
            name: "count"
            type: "int"
            read: "count"
            notify: "countChanged"
            index: 0
            isReadonly: true
        }
        Property { name: "label"; type: "QString"; read: "label"; index: 1 }
        Signal { name: "countChanged"; lineNumber: 9 }
        Method {
            name: "refresh"
            Parameter { name: "force"; type: "bool" }
        }
    }
    Component {
        file: "other.h"
        name: "Fake::Other"
        accessSemantics: "reference"
        prototype: "QObject"
        exports: ["org.kde.fake/Other 1.0"]
        Property { name: "value"; type: "int"; index: 0 }
    }
}
"""

QMLDIR = """\
module org.kde.fake
linktarget fakeplugin
optional plugin fakeplugin
classname org_kde_fakePlugin
typeinfo fake.qmltypes
depends QtQuick
prefer :/qt/qml/org/kde/fake/
"""

KRUNNER_XML = """\
<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.kde.krunner.App">
    <method name="display"/>
    <method name="toggleDisplay"/>
    <method name="query"><arg name="term" type="s" direction="in"/></method>
    <method name="querySingleRunner"><arg name="runnerName" type="s" direction="in"/></method>
    <method name="displaySingleRunner"><arg name="runnerName" type="s" direction="in"/></method>
    <method name="displayWithClipboardContents"/>
  </interface>
</node>
"""

KRUNNER_DESKTOP = """\
[Desktop Entry]
Exec=/usr/bin/krunner
Name=KRunner
Name[es]=KRunner
Type=Application
DBusActivatable=True
X-DBUS-StartupType=Unique
X-DBUS-ServiceName=org.kde.krunner

[Desktop Action Clipboard]
Exec=krunner -c
Name=Clipboard
Name=Clipboard
"""

MANIFEST = f"""\
[modules."{MODULE}"]
files = ["{USER}"]
plugin_strings = ["FakeSingleton"]

[modules."{MODULE}".types.FakeModel]
properties = ["count", "label", "inherited"]
methods = ["refresh", "rowCount"]
signals = ["countChanged", "dataChanged"]
enums = ["Alpha", "Mode.Gamma", "Flag.FlagTwo"]
roles = ["roleOne", "roleWide"]
unverified_roles = ["roleElsewhere"]

[modules."{MODULE}".types.Other]
files = ["plasma/plasmoids/org.fake/contents/ui/Other.qml"]
properties = ["value"]

[[system.dbus_interface]]
file = "org.kde.krunner.App.xml"
search = ["dbus-1/interfaces"]
interface = "org.kde.krunner.App"
methods = ["display", "toggleDisplay", "query", "querySingleRunner", "displaySingleRunner",
           "displayWithClipboardContents"]
used_by = "Spotlight"

[[system.desktop_file]]
file = "org.kde.krunner.desktop"
search = ["kglobalaccel", "applications"]
keys = {{ DBusActivatable = "true", X-DBUS-ServiceName = "org.kde.krunner" }}
used_by = "Spotlight"

[[system.desktop_file]]
file = "plasma-runner-baloosearch.desktop"
search = ["krunner/dbusplugins"]
used_by = "Spotlight"
"""


class Tree:
    """Árbol falso: qml/ (módulos QML) y share/ (XDG_DATA_DIRS)."""

    def __init__(self, base: Path):
        self.qml = base / "qml"
        self.share = base / "share"
        mod = self.qml / "org/kde/fake"
        mod.mkdir(parents=True)
        (mod / "qmldir").write_text(QMLDIR)
        (mod / "fake.qmltypes").write_text(QMLTYPES)
        # roleOne en Latin-1; roleWide como QStringLiteral (UTF-16); roleOnlyPart solo como
        # parte de otra cadena: no debe contar
        (mod / "libfakeplugin.so").write_bytes(
            b"\x7fELF\0\0roleOne\0\x01" + "roleWide".encode("utf-16-le") + b"\0\0"
            + b"FakeSingleton\0xx_roleMissing_yy\0")
        self.write("dbus-1/interfaces/org.kde.krunner.App.xml", KRUNNER_XML)
        self.write("kglobalaccel/org.kde.krunner.desktop", KRUNNER_DESKTOP)
        self.write("krunner/dbusplugins/plasma-runner-baloosearch.desktop", "[Desktop Entry]\nName=File Search\n")

    def write(self, rel: str, text: str) -> Path:
        path = self.share / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def qmltypes(self, old: str, new: str) -> None:
        path = self.qml / "org/kde/fake/fake.qmltypes"
        text = path.read_text()
        assert old in text
        path.write_text(text.replace(old, new))
        cpc.load_module.cache_clear()


@pytest.fixture
def tree(tmp_path: Path) -> Tree:
    cpc.load_module.cache_clear()
    cpc._lib_bytes.cache_clear()
    return Tree(tmp_path)


@pytest.fixture
def manifest() -> dict:
    return tomllib.loads(MANIFEST)


def api(tree: Tree, manifest: dict) -> list[str]:
    return cpc.check_api(manifest, tree.qml)[0]


def system(tree: Tree, manifest: dict) -> list[str]:
    return cpc.check_system(manifest, [tree.share])[0]


# --- analizador de .qmltypes ----------------------------------------------------------------


def test_parser_reads_components_members_and_enums(tree: Tree):
    root = cpc.parse_qmltypes(QMLTYPES)
    assert root.kind == "Module"
    names = [c.attrs["name"] for c in root.children]
    assert names == ["QAbstractItemModel", "Fake::BaseModel", "Fake::FakeModel", "Fake::Other"]
    fake = root.children[2]
    assert fake.attrs["exports"] == ["org.kde.fake/FakeModel 1.0", "org.kde.fake/FakeModel 2.0"]
    flags = next(c for c in fake.children if c.attrs.get("name") == "Flags")
    assert flags.attrs["values"] == ["FlagOne", "FlagTwo"]
    assert flags.attrs["alias"] == "Flag"


def test_parser_value_types_and_separators():
    root = cpc.parse_qmltypes('Module { Component { a: 1; b: -2.5; c: true; d: "x\\"y"; e: [1, 2,] ; f: [] } }')
    attrs = root.children[0].attrs
    assert attrs == {"a": 1, "b": -2.5, "c": "true", "d": 'x"y', "e": [1, 2], "f": []}


@pytest.mark.parametrize("text", ["Module {", "Module { a }", "Module { a: }", 'Module { a: "x }', "Module { } }", ""])
def test_parser_rejects_broken_syntax(text: str):
    with pytest.raises(ValueError):
        cpc.parse_qmltypes(text)


def test_a_broken_qmltypes_is_reported_not_raised(tree: Tree, manifest: dict):
    (tree.qml / "org/kde/fake/fake.qmltypes").write_text("Module { Component {")
    errors = api(tree, manifest)
    assert any("no se pudo leer" in e and "fake.qmltypes" in e for e in errors)


# --- API privada ------------------------------------------------------------------------------


def test_everything_present_passes(tree: Tree, manifest: dict):
    errors, checked, unverified = cpc.check_api(manifest, tree.qml)
    assert errors == []
    assert checked > 10
    assert unverified == 1  # roleElsewhere


def test_missing_property_names_the_qml_file(tree: Tree, manifest: dict):
    tree.qmltypes('Property { name: "label"; type: "QString"; read: "label"; index: 1 }', "")
    assert api(tree, manifest) == [f"API privada {MODULE}: propiedad FakeModel.label ya no existe; lo usan: {USER}"]


def test_missing_enum_value_names_the_qml_file(tree: Tree, manifest: dict):
    tree.qmltypes('values: ["Alpha", "Beta", "Gamma"]', 'values: ["Alpha", "Beta"]')
    assert api(tree, manifest) == [f"API privada {MODULE}: valor de enum FakeModel.Mode.Gamma ya no existe; lo usan: {USER}"]


def test_missing_type_names_the_qml_file(tree: Tree, manifest: dict):
    tree.qmltypes('exports: ["org.kde.fake/FakeModel 1.0", "org.kde.fake/FakeModel 2.0"]', "")
    errors = api(tree, manifest)
    assert errors == [f"API privada {MODULE}: el tipo FakeModel ya no existe; lo usan: {USER}"]


def test_type_level_files_replace_the_module_ones(tree: Tree, manifest: dict):
    tree.qmltypes('Property { name: "value"; type: "int"; index: 0 }', "")
    assert api(tree, manifest) == [
        f"API privada {MODULE}: propiedad Other.value ya no existe; lo usan: plasma/plasmoids/org.fake/contents/ui/Other.qml"
    ]


def test_missing_method_and_signal(tree: Tree, manifest: dict):
    tree.qmltypes('Method {\n            name: "refresh"', 'Method {\n            name: "renamed"')
    tree.qmltypes('Signal { name: "countChanged"; lineNumber: 9 }', "")
    errors = api(tree, manifest)
    assert any("método FakeModel.refresh" in e for e in errors)
    assert any("señal FakeModel.countChanged" in e for e in errors)
    assert len(errors) == 2


def test_inherited_members_come_through_the_prototype_chain(tree: Tree, manifest: dict):
    # inherited (BaseModel), rowCount y dataChanged (QAbstractItemModel): ya en el manifiesto base
    assert api(tree, manifest) == []
    tree.qmltypes('prototype: "Fake::BaseModel"', 'prototype: "Nothing"')
    errors = api(tree, manifest)
    assert any("FakeModel.inherited" in e for e in errors)
    assert any("FakeModel.rowCount" in e for e in errors)


def test_enum_by_name_or_alias(tree: Tree, manifest: dict):
    manifest["modules"][MODULE]["types"]["FakeModel"]["enums"] = ["FlagOne", "Flags.FlagTwo", "Flag.FlagOne", "Mode.FlagOne"]
    errors = api(tree, manifest)
    assert len(errors) == 1 and "Mode.FlagOne" in errors[0]


def test_roles_are_checked_against_the_plugin_strings(tree: Tree, manifest: dict):
    manifest["modules"][MODULE]["types"]["FakeModel"]["roles"] = ["roleOne", "roleWide", "roleMissing", "role"]
    errors = api(tree, manifest)
    assert len(errors) == 2
    assert any("rol FakeModel.roleMissing ya no está en libfakeplugin.so" in e for e in errors)
    assert any("rol FakeModel.role ya no está" in e for e in errors)  # solo es parte de otra cadena


def test_plugin_strings_and_unverified(tree: Tree, manifest: dict):
    manifest["modules"][MODULE]["plugin_strings"] = ["FakeSingleton", "Gone"]
    manifest["modules"][MODULE]["unverified"] = ["Whatever.Name"]
    errors, _, unverified = cpc.check_api(manifest, tree.qml)
    assert len(errors) == 1 and "Gone ya no está" in errors[0]
    assert unverified == 2


def test_roles_without_plugin_library_are_an_error(tree: Tree, manifest: dict):
    (tree.qml / "org/kde/fake/libfakeplugin.so").unlink()
    errors = api(tree, manifest)
    assert any("no hay biblioteca del plugin" in e for e in errors)


def test_types_not_exported_are_found_by_their_cpp_name(tree: Tree, manifest: dict):
    manifest["modules"][MODULE]["types"]["Fake::BaseModel"] = {"properties": ["inherited", "nope"]}
    errors = api(tree, manifest)
    assert len(errors) == 1 and "Fake::BaseModel.nope" in errors[0]


def test_uninstalled_module_is_left_to_the_import_check(tree: Tree, manifest: dict):
    manifest["modules"]["org.kde.absent"] = {"files": [USER], "types": {"X": {"properties": ["y"]}}}
    assert api(tree, manifest) == []


def test_unknown_manifest_keys_are_errors(manifest: dict):
    assert cpc.check_manifest_shape(manifest) == []
    manifest["modules"][MODULE]["types"]["FakeModel"]["propertes"] = ["x"]
    manifest["modules"][MODULE]["tipos"] = {}
    manifest["extra"] = 1
    errors = cpc.check_manifest_shape(manifest)
    assert len(errors) == 3
    assert any("propertes" in e for e in errors) and any("tipos" in e for e in errors) and any("extra" in e for e in errors)


def test_private_module_missing_from_the_manifest(manifest: dict):
    imports = {
        MODULE: [USER],
        "org.kde.plasma.private.newthing": ["b.qml", "a.qml", "a.qml"],
        "org.kde.kirigami": ["c.qml"],  # público: no hace falta
    }
    assert cpc.unlisted_private(manifest, imports) == [
        "módulo privado org.kde.plasma.private.newthing sin listar en plasma_api.toml; lo usan: a.qml, b.qml"
    ]
    manifest["modules"]["org.kde.plasma.private.newthing"] = {}
    assert cpc.unlisted_private(manifest, imports) == []


# --- contratos del sistema ----------------------------------------------------------------------


def test_system_contracts_pass(tree: Tree, manifest: dict):
    errors, checked = cpc.check_system(manifest, [tree.share])
    assert errors == []
    assert checked == 3


def test_xml_without_a_method(tree: Tree, manifest: dict):
    tree.write("dbus-1/interfaces/org.kde.krunner.App.xml", KRUNNER_XML.replace('<method name="displayWithClipboardContents"/>', ""))
    errors = system(tree, manifest)
    assert len(errors) == 1
    assert "org.kde.krunner.App ya no tiene el método displayWithClipboardContents" in errors[0]
    assert "lo usa: Spotlight" in errors[0]


def test_xml_without_the_interface_or_missing_or_broken(tree: Tree, manifest: dict):
    xml = tree.share / "dbus-1/interfaces/org.kde.krunner.App.xml"
    xml.write_text(KRUNNER_XML.replace("org.kde.krunner.App", "org.kde.other"))
    assert "no declara la interfaz org.kde.krunner.App" in system(tree, manifest)[0]
    xml.write_text("<node>")
    assert "no es un XML válido" in system(tree, manifest)[0]
    xml.unlink()
    assert "no se encuentra la interfaz D-Bus org.kde.krunner.App" in system(tree, manifest)[0]


def test_desktop_without_dbus_activatable(tree: Tree, manifest: dict):
    tree.write("kglobalaccel/org.kde.krunner.desktop", KRUNNER_DESKTOP.replace("DBusActivatable=True\n", ""))
    errors = system(tree, manifest)
    assert len(errors) == 1
    assert "DBusActivatable debe ser 'true' y es None" in errors[0]
    assert "org.kde.krunner.desktop" in errors[0]


def test_desktop_with_wrong_values(tree: Tree, manifest: dict):
    tree.write("kglobalaccel/org.kde.krunner.desktop",
               KRUNNER_DESKTOP.replace("DBusActivatable=True", "DBusActivatable=false")
               .replace("X-DBUS-ServiceName=org.kde.krunner", "X-DBUS-ServiceName=org.kde.other"))
    assert len(system(tree, manifest)) == 2


def test_dbus_activatable_in_another_section_does_not_count(tree: Tree, manifest: dict):
    tree.write("kglobalaccel/org.kde.krunner.desktop",
               KRUNNER_DESKTOP.replace("DBusActivatable=True\n", "").replace("Name=Clipboard", "DBusActivatable=true", 1))
    assert len(system(tree, manifest)) == 1


def test_missing_baloo_runner_desktop(tree: Tree, manifest: dict):
    (tree.share / "krunner/dbusplugins/plasma-runner-baloosearch.desktop").unlink()
    errors = system(tree, manifest)
    assert len(errors) == 1
    assert "plasma-runner-baloosearch.desktop" in errors[0] and "krunner/dbusplugins" in errors[0]


def test_data_dirs_are_searched_in_order(tree: Tree, manifest: dict, tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cpc.check_system(manifest, [empty, tree.share])[0] == []
    assert len(cpc.check_system(manifest, [empty])[0]) == 3  # la interfaz D-Bus y los dos .desktop
    paths = cpc.system_paths(manifest, [tree.share])
    assert tree.share / "dbus-1/interfaces/org.kde.krunner.App.xml" in paths


# --- objetos D-Bus de plasmashell -------------------------------------------------------------------

OSD_OBJECT = {
    "binary": "plasmashell",
    "interface": "org.kde.osdService",
    "path": "/org/kde/osdService",
    "methods": ["volumeChanged", "hide"],
    "signals": ["osdProgress"],
    "used_by": "HUD",
}


def fake_plasmashell(directory: Path, *, without: str = "") -> Path:
    """A binary with the names as moc and u""_s leave them: NUL-separated Latin-1, the path in UTF-16."""
    names = [n for n in ("org.kde.osdService", "volumeChanged", "hide", "osdProgress") if n != without]
    data = b"\x7fELF\0" + b"\0".join(n.encode() for n in names) + b"\0\0"
    if without != "/org/kde/osdService":
        data += "/org/kde/osdService".encode("utf-16-le") + b"\0\0"
    directory.mkdir(parents=True, exist_ok=True)
    binary = directory / "plasmashell"
    binary.write_bytes(data)
    cpc._lib_bytes.cache_clear()
    return binary


def test_dbus_object_names_are_found_in_the_binary(tmp_path: Path):
    manifest = {"system": {"dbus_object": [OSD_OBJECT]}}
    fake_plasmashell(tmp_path / "bin")
    assert cpc.check_dbus_objects(manifest, [tmp_path / "empty", tmp_path / "bin"]) == ([], 1)


@pytest.mark.parametrize("missing", ["hide", "osdProgress", "/org/kde/osdService", "org.kde.osdService"])
def test_a_renamed_member_of_the_dbus_object_is_an_error(tmp_path: Path, missing: str):
    manifest = {"system": {"dbus_object": [OSD_OBJECT]}}
    binary = fake_plasmashell(tmp_path / "bin", without=missing)
    errors, _ = cpc.check_dbus_objects(manifest, [tmp_path / "bin"])
    assert errors == [f"system: {binary} no longer has {missing} (org.kde.osdService at /org/kde/osdService); used by: HUD"]


def test_a_missing_binary_is_an_error(tmp_path: Path):
    manifest = {"system": {"dbus_object": [OSD_OBJECT]}}
    errors, checked = cpc.check_dbus_objects(manifest, [tmp_path])
    assert checked == 1
    assert errors == ["system: plasmashell not found in PATH; used by: HUD"]
    assert cpc.binary_paths(manifest) == [Path("/usr/bin/plasmashell")]


def test_real_manifest_guards_the_whole_osd_service(real_manifest: dict):
    """The same slots and signals that qmlplugin/osdservice.h copies from Plasma."""
    header = (ROOT / "qmlplugin/osdservice.h").read_text()
    exported = set(re.findall(r"^\s+void (\w+)\(", header, re.M))
    (osd,) = real_manifest["system"]["dbus_object"]
    assert (osd["interface"], osd["path"]) == ("org.kde.osdService", "/org/kde/osdService")
    assert set(osd["methods"]) | set(osd["signals"]) == exported


# --- main() ---------------------------------------------------------------------------------------


@pytest.fixture
def run_main(tree: Tree, manifest: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, tmp_path: Path):
    imports = {MODULE: [USER]}
    monkeypatch.setattr(cpc, "_qml_dir", lambda: tree.qml)
    monkeypatch.setattr(cpc, "_imports", lambda *a: imports)
    monkeypatch.setattr(cpc, "load_manifest", lambda *a: manifest)
    monkeypatch.setattr(cpc, "_data_dirs", lambda: [tree.share])
    monkeypatch.setattr(cpc, "_bin_dirs", lambda: [tmp_path / "bin"])
    monkeypatch.setattr(cpc, "_plasma_version", lambda: None)
    monkeypatch.setattr(cpc.sys, "argv", ["check_plasma_compat.py"])

    def run() -> tuple[int, str, str]:
        code = cpc.main()
        out = capsys.readouterr()
        return code, out.out, out.err

    run.imports = imports
    return run


def test_main_exit_codes_and_messages(run_main, tree: Tree):
    code, out, err = run_main()
    assert code == 0 and "nombres no verificables" in out and err.count("error:") == 0
    tree.qmltypes('Property { name: "label"; type: "QString"; read: "label"; index: 1 }', "")
    code, out, err = run_main()
    assert code == 1 and out == ""
    assert f"error: API privada {MODULE}: propiedad FakeModel.label ya no existe; lo usan: {USER}" in err


def test_main_reports_unlisted_private_modules(run_main):
    run_main.imports["org.kde.plasma.private.nope"] = ["x.qml"]
    code, _, err = run_main()
    assert code == 1
    assert "error: módulo QML org.kde.plasma.private.nope no instalado" in err
    assert "error: módulo privado org.kde.plasma.private.nope sin listar en plasma_api.toml; lo usan: x.qml" in err


# --- guardas sobre el repositorio real ------------------------------------------------------------


@pytest.fixture(scope="module")
def real_manifest() -> dict:
    return cpc.load_manifest()


@pytest.fixture(scope="module")
def real_imports() -> dict[str, list[str]]:
    return cpc._imports()


def test_every_private_module_the_qml_imports_is_in_the_manifest(real_manifest: dict, real_imports: dict):
    """Si falla: al usar una API privada nueva hay que añadirla a tools/plasma_api.toml."""
    assert cpc.unlisted_private(real_manifest, real_imports) == []


def test_real_manifest_has_the_expected_shape(real_manifest: dict):
    assert cpc.check_manifest_shape(real_manifest) == []
    assert real_manifest["modules"], "manifiesto vacío"
    assert len(real_manifest["system"]["dbus_interface"][0]["methods"]) == 6


def test_manifest_files_exist_and_modules_are_imported_there(real_manifest: dict, real_imports: dict):
    for module, mdata in real_manifest["modules"].items():
        assert mdata.get("files"), f"{module}: sin files"
        for name in mdata["files"]:
            assert (ROOT / name).is_file(), f"{module}: {name} ya no existe"
            assert name in real_imports.get(module, []), f"{module}: {name} ya no importa el módulo"
        for tname, tdata in mdata.get("types", {}).items():
            for name in tdata.get("files", []):
                assert (ROOT / name).is_file(), f"{module}.{tname}: {name} ya no existe"


def test_every_manifest_name_still_appears_in_its_qml_files(real_manifest: dict):
    """Un nombre que el QML ya no usa es una comprobación inútil (y un posible falso error)."""
    missing = []

    def present(name: str, files: list[str], signal: bool = False) -> bool:
        words = [name.rpartition(".")[2]]
        if signal:
            words.append("on" + words[0][:1].upper() + words[0][1:])
        texts = [(ROOT / f).read_text(encoding="utf-8") for f in files]
        return any(re.search(rf"\b{re.escape(w)}\b", t, re.I) for w in words for t in texts)

    for module, mdata in real_manifest["modules"].items():
        for name in mdata.get("plugin_strings", []) + mdata.get("unverified", []):
            if not present(name, mdata["files"]):
                missing.append(f"{module}: {name}")
        for tname, tdata in mdata.get("types", {}).items():
            files = tdata.get("files") or mdata["files"]
            # el nombre del tipo no se exige: algunos llegan solo como valor (PlayerContainer, Sink)
            for key in ("properties", "methods", "signals", "enums", "roles", "unverified_roles"):
                for name in tdata.get(key, []):
                    if not present(name, files, signal=key == "signals"):
                        missing.append(f"{module}.{tname}: {key} {name}")
    assert missing == [], "ya no aparecen en el QML que se les atribuye:\n" + "\n".join(missing)
