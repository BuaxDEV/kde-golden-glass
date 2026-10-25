#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Comprueba que la traducción al español cubre todos los textos de la interfaz.
# Como los scripts de traducción de KDE: ejecuta cada Messages.sh (con XGETTEXT,
# EXTRACTRC y podir) para sacar los .pot y compara cada uno con su catálogo
# (msgcmp: falla si falta un texto, está sin traducir o es «fuzzy»):
#
#   plasma_applet_<id>.pot   → plasma/plasmoids/<id>/po/es.po
#   <dominio>.pot            → po/es/<dominio>.po
#
# El shell no tiene catálogo propio: sus textos (copias de plasma-desktop) usan
# i18nd*() con el dominio de plasma-desktop, que ya los traduce. Aquí se exige
# que no haya ninguno sin dominio.
#
#   tools/check_i18n.sh
#
# Usa el extractrc de KDE si está instalado; si no, tools/extractrc.py.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LANG_CODE=es

# las palabras clave de ki18n sin dominio (-k quita las de --kde, que incluyen
# i18nd*: esos textos son de otro catálogo)
export XGETTEXT="xgettext --from-code=UTF-8 -C --kde -ci18n -k -ki18n:1 -ki18nc:1c,2 -ki18np:1,2 -ki18ncp:1c,2,3
  -kki18n:1 -kki18nc:1c,2 -kki18np:1,2 -kki18ncp:1c,2,3 -kxi18n:1 -kxi18nc:1c,2 -kxi18np:1,2 -kxi18ncp:1c,2,3
  -kkxi18n:1 -kkxi18nc:1c,2 -kkxi18np:1,2 -kkxi18ncp:1c,2,3 -kkli18n:1 -kkli18nc:1c,2 -kkli18np:1,2 -kkli18ncp:1c,2,3
  -kklxi18n:1 -kklxi18nc:1c,2 -kklxi18np:1,2 -kklxi18ncp:1c,2,3 -kI18N_NOOP:1 -kI18NC_NOOP:1c,2
  -ktr2i18n:1,2c -ktr2xi18n:1,2c --no-location"
if command -v extractrc >/dev/null; then
  EXTRACTRC=extractrc
else
  EXTRACTRC="python3 $ROOT/tools/extractrc.py"
fi
export EXTRACTRC
podir="$(mktemp -d)"
export podir
trap 'rm -rf "$podir"' EXIT

cd "$ROOT"
mapfile -t scripts < <(git ls-files --cached --others --exclude-standard '*Messages.sh')
for script in "${scripts[@]}"; do
  (cd "$(dirname "$script")" && bash Messages.sh)
done

fail=0
for pot in "$podir"/*.pot; do
  [[ -e $pot ]] || continue
  name=$(basename "$pot" .pot)
  if [[ $name == plasma_applet_* ]]; then
    po=plasma/plasmoids/${name#plasma_applet_}/po/$LANG_CODE.po
  else
    po=po/$LANG_CODE/$name.po
  fi
  count=$(grep -c '^msgid ' "$pot")
  if [[ ! -f $po ]]; then
    echo "::error file=$po::falta el catálogo de $name ($((count - 1)) textos)"
    fail=1
  elif msgcmp "$po" "$pot" 2>/dev/null; then
    echo "$name: $((count - 1)) textos, todos traducidos ($po)"
  else
    echo "::error file=$po::$name: faltan textos por traducir:"
    msgmerge --quiet --no-fuzzy-matching "$po" "$pot" -o - | msgattrib --untranslated --no-obsolete
    fail=1
  fi
done

# shell: sin textos en su propio dominio (no tiene catálogo)
mapfile -t shell < <(git ls-files 'plasma/shell/*.qml' 'plasma/shell/*.js')
# shellcheck disable=SC2086 # XGETTEXT son varias palabras, como en Messages.sh
$XGETTEXT "${shell[@]}" -o "$podir/shell.pot"
if [[ -e $podir/shell.pot ]]; then
  echo "::error::el shell usa textos sin dominio; usar i18nd*(\"plasma_shell_org.kde.plasma.desktop\", …):"
  grep '^msgid ' "$podir/shell.pot" | tail -n +2
  fail=1
fi

exit "$fail"
