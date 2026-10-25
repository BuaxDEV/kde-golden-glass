#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Comprueba GoldenGlass contra el Plasma instalado (lo usa tools/ci.sh):

  - Cada módulo QML que importa el repositorio (salvo org.goldenglass.*, que
    se compilan aquí) está instalado. Plasma mueve y quita módulos entre
    versiones: con 6.8 desapareció org.kde.plasma.shell.panel y plasmashell se
    caía al cargar views/Panel.qml.
  - El shell está portado al plasma-desktop instalado
    (X-GoldenGlass-PlasmaVersion de su metadata.json; ver UPSTREAM.md).
  - La API privada de Plasma que usa el QML (tools/plasma_api.toml): tipos,
    propiedades, métodos, señales, valores de enum y roles de modelo, contra los
    .qmltypes instalados (los roles, contra las cadenas del plugin; ver el
    manifiesto). Un módulo privado (org.kde.*private*) que el QML importa y el
    manifiesto no lista también es un error.
  - Los contratos del sistema que esperan Spotlight y Notificaciones (sección
    [system] del manifiesto): interfaz D-Bus y .desktop de KRunner, etc.

Con --qmldirs solo lista las rutas (qmldir de esos módulos y archivos del
sistema del manifiesto) para pacman -F, que dice qué paquetes instalar antes
de comprobar.
"""

from __future__ import annotations

import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHELL = ROOT / "plasma/shell/org.goldenglass.desktop"
OWN = "org.goldenglass."
IMPORT = re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)", re.M)
MANIFEST = ROOT / "tools/plasma_api.toml"
# módulos privados de Plasma: sin API estable, deben estar en el manifiesto
PRIVATE = re.compile(r"^org\.kde\..*private")


def _qml_dir() -> Path:
    for tool in ("qtpaths6", "qtpaths"):
        if shutil.which(tool):
            out = subprocess.run([tool, "--query", "QT_INSTALL_QML"], capture_output=True, text=True,
                                 check=False).stdout.strip()
            if out:
                return Path(out)
    return Path("/usr/lib/qt6/qml")


def _imports(root: Path = ROOT) -> dict[str, list[str]]:
    """Módulo -> archivos que lo importan."""
    files = subprocess.run(["git", "-C", str(root), "ls-files", "*.qml"], capture_output=True, text=True,
                           check=True).stdout.split()
    found: dict[str, list[str]] = {}
    for name in files:
        for module in IMPORT.findall((root / name).read_text(encoding="utf-8")):
            if not module.startswith(OWN):
                found.setdefault(module, []).append(name)
    return found


def _plasma_version() -> str | None:
    """plasma-desktop instalado como mayor.menor (1:6.8.1-1.1 -> 6.8)."""
    if not shutil.which("pacman"):
        return None
    out = subprocess.run(["pacman", "-Q", "plasma-desktop"], capture_output=True, text=True, check=False)
    if out.returncode != 0:
        return None
    version = out.stdout.split()[1].split(":")[-1]
    return ".".join(version.split(".")[:2])


# --- .qmltypes -----------------------------------------------------------------------
# Los .qmltypes son sintaxis QML: «Module { Component { name: "X"; Property { … } } }».
# Hace falta un analizador propio (sin dependencias nuevas): un tokenizador y un
# descenso recursivo que sirve para cualquier archivo de qmltyperegistrar.

_TOKEN = re.compile(
    r"""
    (?P<skip>\s+|//[^\n]*|/\*.*?\*/)
  | (?P<str>"(?:[^"\\]|\\.)*")
  | (?P<num>-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)
  | (?P<id>[A-Za-z_][\w.]*)
  | (?P<punct>[{}\[\]:;,])
    """,
    re.X | re.S,
)


@dataclass
class Node:
    """Un objeto QML (Component, Property, Enum…) con sus atributos y objetos hijos."""

    kind: str
    attrs: dict = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)


def _tokens(text: str) -> list[tuple[str, str]]:
    out = []
    pos = 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"carácter inesperado {text[pos]!r} (posición {pos})")
        pos = m.end()
        if m.lastgroup != "skip":
            out.append((m.lastgroup, m.group()))
    return out


class _Parser:
    def __init__(self, text: str):
        self.toks = _tokens(text)
        self.pos = 0

    def peek(self) -> tuple[str, str]:
        return self.toks[self.pos] if self.pos < len(self.toks) else ("eof", "")

    def take(self, want: str | None = None) -> tuple[str, str]:
        tok = self.peek()
        if tok[0] == "eof" or (want is not None and tok[1] != want):
            raise ValueError(f"se esperaba {want or 'más texto'!r} y hay {tok[1]!r}")
        self.pos += 1
        return tok

    def obj(self, kind: str) -> Node:
        node = Node(kind)
        self.take("{")
        while True:
            tok_kind, text = self.peek()
            if text in (";", ","):
                self.pos += 1
            elif text == "}":
                self.pos += 1
                return node
            elif tok_kind == "id":
                self.pos += 1
                if self.peek()[1] == ":":
                    self.pos += 1
                    node.attrs[text] = self.value()
                elif self.peek()[1] == "{":
                    node.children.append(self.obj(text))
                else:
                    raise ValueError(f"tras {text!r} se esperaba ':' o '{{'")
            else:
                raise ValueError(f"token inesperado {text!r}")

    def value(self):
        tok_kind, text = self.peek()
        if tok_kind == "str":
            self.pos += 1
            try:
                return json.loads(text)
            except ValueError:
                return text[1:-1]
        if tok_kind == "num":
            self.pos += 1
            return float(text) if re.search(r"[.eE]", text) else int(text)
        if text == "[":
            self.pos += 1
            items = []
            while self.peek()[1] != "]":
                if self.peek()[1] == ",":
                    self.pos += 1
                else:
                    items.append(self.value())
            self.pos += 1
            return items
        if tok_kind == "id":
            self.pos += 1
            if self.peek()[1] == "{":
                return self.obj(text)
            return text  # true, false, identificadores
        raise ValueError(f"valor inesperado {text!r}")


def parse_qmltypes(text: str) -> Node:
    """El árbol de un .qmltypes (raíz: Module). ValueError si no es sintaxis válida."""
    text = re.sub(r"^[ \t]*import[ \t][^\n]*", "", text, flags=re.M)
    parser = _Parser(text)
    root = parser.obj(parser.take()[1])
    if parser.peek()[0] != "eof":
        raise ValueError(f"texto tras el objeto raíz: {parser.peek()[1]!r}")
    return root


@dataclass
class QmlType:
    """Un Component de un .qmltypes: lo que se puede comprobar de un tipo."""

    name: str
    prototype: str | None = None
    extension: str | None = None
    exports: list[tuple[str, str]] = field(default_factory=list)  # (módulo, nombre en QML)
    properties: set[str] = field(default_factory=set)
    methods: set[str] = field(default_factory=set)
    signals: set[str] = field(default_factory=set)
    enums: dict[str, set[str]] = field(default_factory=dict)  # nombre y alias -> valores


def _as_list(value) -> list:
    return value if isinstance(value, list) else [] if value is None else [value]


def _qml_type(node: Node) -> QmlType | None:
    name = node.attrs.get("name")
    if node.kind != "Component" or not isinstance(name, str):
        return None
    t = QmlType(name, node.attrs.get("prototype"), node.attrs.get("extension"))
    for export in _as_list(node.attrs.get("exports")):
        if isinstance(export, str) and "/" in export:
            uri, _, rest = export.partition("/")
            t.exports.append((uri, rest.split()[0]))
    for child in node.children:
        cname = child.attrs.get("name")
        if not isinstance(cname, str):
            continue
        if child.kind == "Property":
            t.properties.add(cname)
        elif child.kind == "Method":
            t.methods.add(cname)
        elif child.kind == "Signal":
            t.signals.add(cname)
        elif child.kind == "Enum":
            values = {v for v in _as_list(child.attrs.get("values")) if isinstance(v, str)}
            for key in (cname, child.attrs.get("alias")):
                if isinstance(key, str):
                    t.enums.setdefault(key, set()).update(values)
    return t


@dataclass
class ModuleInfo:
    module: str
    directory: Path
    types: dict[str, QmlType] = field(default_factory=dict)  # nombre de C++ -> tipo
    exported: dict[str, QmlType] = field(default_factory=dict)  # nombre en QML -> tipo
    libs: list[Path] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _qmldir_lines(path: Path) -> dict[str, list[list[str]]]:
    out: dict[str, list[list[str]]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        words = line.split("#")[0].split()
        if words[:1] == ["optional"]:
            words = words[1:]  # «optional plugin x»
        if words:
            out.setdefault(words[0], []).append(words[1:])
    return out


@cache
def load_module(qml_dir: Path, module: str, _seen: tuple[str, ...] = ()) -> ModuleInfo | None:
    """El módulo QML instalado en qml_dir (None si no tiene qmldir).

    Reúne los tipos de su .qmltypes y los de los módulos de los que depende (los
    prototipos: QAbstractItemModel, etc.) y localiza las bibliotecas de su plugin.
    """
    directory = qml_dir / module.replace(".", "/")
    qmldir = directory / "qmldir"
    if not qmldir.is_file():
        return None
    info = ModuleInfo(module, directory)
    lines = _qmldir_lines(qmldir)
    typeinfos = [directory / w[0] for w in lines.get("typeinfo", []) if w]
    if not typeinfos:
        info.problems.append(f"{qmldir} no declara typeinfo (.qmltypes)")
    for path in typeinfos:
        try:
            root = parse_qmltypes(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            info.problems.append(f"no se pudo leer {path}: {e}")
            continue
        for t in filter(None, map(_qml_type, root.children)):
            info.types.setdefault(t.name, t)
            for uri, qml_name in t.exports:
                if uri == module:
                    info.exported[qml_name] = t
    for words in lines.get("depends", []):
        dep = words[0] if words else ""
        if dep and dep != module and dep not in _seen:
            found = load_module(qml_dir, dep, (*_seen, module))
            for name, t in (found.types if found else {}).items():
                info.types.setdefault(name, t)
    # «plugin [optional] nombre» y «linktarget nombre» -> libnombre.so
    names = [w[-1] for key in ("plugin", "linktarget") for w in lines.get(key, []) if w]
    info.libs = [directory / f"lib{n}.so" for n in dict.fromkeys(names) if (directory / f"lib{n}.so").is_file()]
    return info


def _chain(info: ModuleInfo, t: QmlType):
    """El tipo y sus prototipos y extensiones (donde viven los miembros heredados)."""
    seen: set[str] = set()
    queue = [t]
    while queue:
        cur = queue.pop(0)
        if cur.name in seen:
            continue
        seen.add(cur.name)
        yield cur
        queue += [info.types[n] for n in (cur.prototype, cur.extension) if n and n in info.types]


def has_member(info: ModuleInfo, t: QmlType, kind: str, name: str) -> bool:
    """kind: properties, methods, signals o enums («Valor» o «Enum.Valor»)."""
    for cur in _chain(info, t):
        if kind == "enums":
            enum, dot, value = name.rpartition(".")
            if dot:
                if value in cur.enums.get(enum, ()):
                    return True
            elif any(value in values for values in cur.enums.values()):
                return True
        elif name in getattr(cur, kind):
            return True
    return False


@cache
def _lib_bytes(paths: tuple[Path, ...]) -> bytes:
    return b"\0".join(p.read_bytes() for p in paths)


def has_string(libs: list[Path], text: str) -> bool:
    """Si un nombre aparece como cadena entera (Latin-1 o UTF-16, la de QStringLiteral) en las bibliotecas.

    Los roles de un modelo C++ (roleNames()) y las constantes de los singletons
    registrados a mano no están en el .qmltypes: viven como literales en el
    binario del plugin. Se busca la cadena entera, sin caracteres imprimibles
    pegados. No prueba que el nombre sea de ese modelo, pero uno quitado o
    renombrado en Plasma deja de estar en el plugin.
    """
    data = _lib_bytes(tuple(libs))
    ascii_ = rb"(?<![\x20-\x7e])" + re.escape(text.encode()) + rb"(?![\x20-\x7e])"
    utf16 = rb"(?<![\x20-\x7e]\x00)" + re.escape(text.encode("utf-16-le")) + rb"(?![\x20-\x7e]\x00)"
    return re.search(ascii_, data) is not None or re.search(utf16, data) is not None


# --- manifiesto ------------------------------------------------------------------------

MODULE_KEYS = {"files", "types", "plugin_strings", "unverified"}
TYPE_KEYS = {"files", "properties", "methods", "signals", "enums", "roles", "unverified_roles"}
MEMBER_KINDS = (("properties", "propiedad"), ("methods", "método"), ("signals", "señal"), ("enums", "valor de enum"))


def load_manifest(path: Path = MANIFEST) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def _users(files: list[str]) -> str:
    return "; lo usan: " + ", ".join(sorted(set(files))) if files else ""


def check_manifest_shape(manifest: dict) -> list[str]:
    """Claves desconocidas: un error tipográfico no debe pasar en silencio."""
    errors = [f"{MANIFEST.name}: clave desconocida «{key}»" for key in set(manifest) - {"modules", "system"}]
    for module, mdata in manifest.get("modules", {}).items():
        errors += [f"{MANIFEST.name}: [{module}] clave desconocida «{key}»" for key in set(mdata) - MODULE_KEYS]
        for tname, tdata in mdata.get("types", {}).items():
            errors += [f"{MANIFEST.name}: [{module}.{tname}] clave desconocida «{key}»"
                       for key in set(tdata) - TYPE_KEYS]
    return errors


def check_api(manifest: dict, qml_dir: Path) -> tuple[list[str], int, int]:
    """Verifica los módulos del manifiesto contra los instalados.

    Devuelve (errores, comprobaciones hechas, nombres no verificables). Un módulo
    sin instalar no se repite aquí: ya lo marca la comprobación de importaciones.
    """
    errors: list[str] = []
    checked = unverified = 0
    for module, mdata in sorted(manifest.get("modules", {}).items()):
        info = load_module(qml_dir, module)
        if info is None:
            continue
        errors += [f"API privada {module}: {problem}" for problem in info.problems]
        for tname, tdata in sorted(mdata.get("types", {}).items()):
            files = tdata.get("files") or mdata.get("files", [])
            t = info.exported.get(tname) or info.types.get(tname)
            checked += 1
            if t is None:
                errors.append(f"API privada {module}: el tipo {tname} ya no existe" + _users(files))
                continue
            for key, label in MEMBER_KINDS:
                for name in tdata.get(key, []):
                    checked += 1
                    if not has_member(info, t, key, name):
                        errors.append(f"API privada {module}: {label} {tname}.{name} ya no existe" + _users(files))
            unverified += len(tdata.get("unverified_roles", []))
            for role in tdata.get("roles", []):
                checked += 1
                if not info.libs:
                    errors.append(f"API privada {module}: no hay biblioteca del plugin donde buscar el rol "
                                  f"{tname}.{role}" + _users(files))
                elif not has_string(info.libs, role):
                    errors.append(f"API privada {module}: el rol {tname}.{role} ya no está en "
                                  + ", ".join(p.name for p in info.libs) + _users(files))
        mfiles = mdata.get("files", [])
        unverified += len(mdata.get("unverified", []))
        for name in mdata.get("plugin_strings", []):
            checked += 1
            if not info.libs:
                errors.append(f"API privada {module}: no hay biblioteca del plugin donde buscar {name}" + _users(mfiles))
            elif not has_string(info.libs, name):
                errors.append(f"API privada {module}: {name} ya no está en "
                              + ", ".join(p.name for p in info.libs) + _users(mfiles))
    return errors, checked, unverified


def unlisted_private(manifest: dict, imports: dict[str, list[str]]) -> list[str]:
    """Módulos privados que el QML importa y el manifiesto no lista."""
    listed = manifest.get("modules", {})
    return [f"módulo privado {module} sin listar en {MANIFEST.name}; lo usan: " + ", ".join(sorted(set(files)))
            for module, files in sorted(imports.items()) if PRIVATE.match(module) and module not in listed]


def _data_dirs() -> list[Path]:
    dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    return [Path(d) for d in dirs.split(":") if d]


def _find(data_dirs: list[Path], search: list[str], name: str) -> Path | None:
    for base in data_dirs:
        for sub in search:
            if (base / sub / name).is_file():
                return base / sub / name
    return None


def system_paths(manifest: dict, data_dirs: list[Path]) -> list[Path]:
    """Todas las rutas donde el manifiesto espera sus archivos del sistema."""
    system = manifest.get("system", {})
    return [base / sub / entry["file"] for kind in ("dbus_interface", "desktop_file") for entry in system.get(kind, [])
            for base in data_dirs for sub in entry.get("search", [])]


def _desktop_entry(path: Path) -> dict[str, str]:
    parser = configparser.ConfigParser(strict=False, interpolation=None, delimiters=("=",), comment_prefixes=("#",))
    parser.optionxform = str  # type: ignore[assignment]  # las claves distinguen mayúsculas
    parser.read_string(path.read_text(encoding="utf-8", errors="replace"))
    return dict(parser["Desktop Entry"]) if parser.has_section("Desktop Entry") else {}


def check_system(manifest: dict, data_dirs: list[Path]) -> tuple[list[str], int]:
    """Contratos del sistema: interfaces D-Bus y .desktop que esperan Spotlight y Notificaciones."""
    system = manifest.get("system", {})
    errors: list[str] = []
    checked = 0
    for entry in system.get("dbus_interface", []):
        checked += 1
        used = f"; lo usa: {entry['used_by']}" if entry.get("used_by") else ""
        path = _find(data_dirs, entry.get("search", []), entry["file"])
        if path is None:
            errors.append(f"sistema: no se encuentra la interfaz D-Bus {entry['interface']} ({entry['file']}){used}")
            continue
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as e:
            errors.append(f"sistema: {path} no es un XML válido: {e}{used}")
            continue
        iface = next((i for i in root.iter("interface") if i.get("name") == entry["interface"]), None)
        if iface is None:
            errors.append(f"sistema: {path} no declara la interfaz {entry['interface']}{used}")
            continue
        have = {m.get("name") for m in iface.iter("method")}
        errors += [f"sistema: {entry['interface']} ya no tiene el método {method} ({path}){used}"
                   for method in entry.get("methods", []) if method not in have]
    for entry in system.get("desktop_file", []):
        checked += 1
        used = f"; lo usa: {entry['used_by']}" if entry.get("used_by") else ""
        path = _find(data_dirs, entry.get("search", []), entry["file"])
        if path is None:
            errors.append(f"sistema: no se encuentra {entry['file']} (en {', '.join(entry.get('search', []))}){used}")
            continue
        try:
            found = _desktop_entry(path)
        except (configparser.Error, OSError) as e:
            errors.append(f"sistema: {path} no se puede leer: {e}{used}")
            continue
        for key, want in entry.get("keys", {}).items():
            got = found.get(key)
            if got is None or got.strip().lower() != str(want).lower():
                errors.append(f"sistema: {path}: {key} debe ser {want!r} y es {got!r}{used}")
    return errors, checked


def main() -> int:
    qml = _qml_dir()
    imports = _imports()
    manifest = load_manifest()
    qmldirs = {m: qml / m.replace(".", "/") / "qmldir" for m in imports}
    if "--qmldirs" in sys.argv[1:]:
        # pacman -F solo conoce /usr: los archivos del sistema, en /usr/share
        for path in sorted(set(qmldirs.values()) | set(system_paths(manifest, [Path("/usr/share")]))):
            print(str(path).lstrip("/"))
        return 0

    errors = []
    for module, path in sorted(qmldirs.items()):
        if not path.is_file():
            errors.append(f"módulo QML {module} no instalado ({path}); lo importan: "
                          + ", ".join(sorted(set(imports[module]))))

    errors += check_manifest_shape(manifest)
    errors += unlisted_private(manifest, imports)
    api_errors, api_checked, unverified = check_api(manifest, qml)
    errors += api_errors
    system_errors, system_checked = check_system(manifest, _data_dirs())
    errors += system_errors

    ported = json.loads((SHELL / "metadata.json").read_text(encoding="utf-8")).get("X-GoldenGlass-PlasmaVersion")
    plasma = _plasma_version()
    if plasma is None:
        print("plasma-desktop no instalado: no se comprueba la versión del shell", file=sys.stderr)
    elif ported != plasma:
        errors.append(f"el shell está portado a Plasma {ported} y está instalado Plasma {plasma}: "
                      "portar views/ y lockscreen/ (UPSTREAM.md)")

    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if not errors:
        print(f"{len(imports)} módulos QML instalados; {api_checked} elementos de API privada y "
              f"{system_checked} contratos del sistema comprobados ({unverified} nombres no verificables); "
              f"shell portado a Plasma {ported}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
