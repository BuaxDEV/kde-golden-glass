#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Configuración local del clon (una vez): filtro «pkgver» para
# packaging/goldenglass/PKGBUILD. makepkg reescribe la línea pkgver= con la
# versión de git en cada compilación; con el filtro, git la compara normalizada
# a la de VERSION y el archivo no aparece como modificado.
#
#   tools/setup-git.sh

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Los filtros se ejecutan desde la raíz del árbol de trabajo.
git config filter.pkgver.clean 'sed "s/^pkgver=.*/pkgver=$(cat VERSION)/"'
git config filter.pkgver.smudge cat
git config filter.pkgver.required false
echo "Filtro pkgver configurado."
