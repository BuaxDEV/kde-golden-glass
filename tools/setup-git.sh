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

# Los filtros se ejecutan desde la raíz del árbol de trabajo. VERSION viene del
# árbol (un PR puede cambiarlo) y acaba dentro del programa de sed: solo se
# acepta si son caracteres válidos de pkgver, o sed podría ejecutar comandos
# (GNU sed tiene «e»). El filtro va entero aquí y no en un script versionado,
# que un PR también podría cambiar.
git config filter.pkgver.clean 'v=$(cat VERSION) && case $v in ""|*[!0-9A-Za-z._]*) echo "filtro pkgver: VERSION no válido" >&2; exit 1;; esac && sed "s/^pkgver=.*/pkgver=$v/"'
git config filter.pkgver.smudge cat
git config filter.pkgver.required false
echo "Filtro pkgver configurado."
