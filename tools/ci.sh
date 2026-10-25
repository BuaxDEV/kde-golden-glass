#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Integración continua de GoldenGlass, dentro de un contenedor Arch Linux:
#
#   1. dependencias de compilación del PKGBUILD (pacman)
#   2. comprobaciones rápidas: Python (ruff), bash, traducciones
#   3. compatibilidad con el Plasma actual de Arch (tools/check_plasma_compat.py)
#   4. generadores (tools/gen_tokens.py)
#   5. C++: compilación y pruebas (ctest)
#   6. makepkg del commit actual: los paquetes quedan en ci-artifacts/
#
# Trabaja sobre un clon en /tmp (makepkg no corre como root y así no se
# tocan los permisos del repositorio montado). Lo usa .github/workflows/ci.yml;
# en local:
#
#   podman run --rm -v "$PWD":/src:Z -w /src docker.io/library/archlinux:latest tools/ci.sh
#
# Con GOLDENGLASS_CI_REPOS=kde-unstable, contra la próxima versión de Plasma:
# activa [kde-unstable] y los repos de testing de los que depende (lo usa
# .github/workflows/plasma-next.yml). Arch solo lo llena durante las betas.
#
# Instala paquetes y crea un usuario: solo se ejecuta en CI o en un contenedor.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK=/tmp/goldenglass-ci
BUILDER=builder

if [[ -z ${CI:-} && ! -e /.dockerenv && ! -e /run/.containerenv ]]; then
  echo "tools/ci.sh instala paquetes y crea usuarios: solo en CI o en un contenedor" >&2
  exit 2
fi

step() { printf '\n==> %s\n' "$*"; }

if [[ ${GOLDENGLASS_CI_REPOS:-} == kde-unstable ]]; then
  step "Repos: kde-unstable, core-testing, extra-testing"
  # por encima de [core] y en este orden (wiki de Arch, «Official repositories»)
  sed -i '0,/^\[core\]/s//[kde-unstable]\nInclude = \/etc\/pacman.d\/mirrorlist\n\n[core-testing]\nInclude = \/etc\/pacman.d\/mirrorlist\n\n[extra-testing]\nInclude = \/etc\/pacman.d\/mirrorlist\n\n[core]/' /etc/pacman.conf
  grep -E '^\[' /etc/pacman.conf
fi

step "Dependencias de compilación"
mapfile -t makedeps < <(cd "$ROOT/packaging/goldenglass" && startdir=$PWD && source PKGBUILD && printf '%s\n' "${makedepends[@]}")
# herramientas que solo usa la CI (no son dependencias del paquete)
citools=(ruff)
pacman -Syu --noconfirm --needed base-devel "${makedeps[@]}" "${citools[@]}"

step "Clon de trabajo (commit $(git -C "$ROOT" rev-parse --short HEAD))"
id -u "$BUILDER" >/dev/null 2>&1 || useradd -m "$BUILDER"
rm -rf "$WORK"
git config --global --add safe.directory "$ROOT"
git clone --quiet --no-hardlinks "$ROOT" "$WORK/goldenglass"
# makepkg compila una rama del repo: la del commit actual (en un PR, HEAD suele
# estar desacoplado)
git -C "$WORK/goldenglass" checkout --quiet -B ci-build "$(git -C "$ROOT" rev-parse HEAD)"
chown -R "$BUILDER:$BUILDER" "$WORK"

as_builder() { runuser -u "$BUILDER" -- env HOME="/home/$BUILDER" QT_QPA_PLATFORM=offscreen "$@"; }

step "Comprobaciones rápidas"
# VERSION entra en el filtro pkgver de git (tools/setup-git.sh) y en el PKGBUILD
grep -Eqx '[0-9]+(\.[0-9]+)*' "$ROOT/VERSION" || { echo "VERSION no válido: $(head -c 80 "$ROOT/VERSION")" >&2; exit 1; }
as_builder bash -c "cd '$WORK/goldenglass' && python -m py_compile tools/*.py && for f in tools/*.sh; do bash -n \"\$f\"; done \
  && find plasma po login -name '*.po' -print0 | xargs -0 -n1 msgfmt --check -o /dev/null"
# ruff (reglas en pyproject.toml)
as_builder bash -c "cd '$WORK/goldenglass' && ruff check --no-cache"

step "Compatibilidad con Plasma (tools/check_plasma_compat.py)"
# los paquetes que traen los módulos QML que importamos (pacman -F): un módulo
# que ya no existe no sale aquí y la comprobación lo marca
pacman -Fy --noconfirm >/dev/null
mapfile -t qmlpkgs < <(as_builder python "$WORK/goldenglass/tools/check_plasma_compat.py" --qmldirs \
  | xargs pacman -Fq 2>/dev/null | sort -u)
pacman -S --noconfirm --needed plasma-desktop "${qmlpkgs[@]}"
as_builder python "$WORK/goldenglass/tools/check_plasma_compat.py"

step "Generadores (tools/gen_tokens.py)"
as_builder bash -c "cd '$WORK/goldenglass' && python tools/gen_tokens.py >/dev/null"

step "C++: compilación y pruebas"
as_builder bash -c "cd '$WORK/goldenglass' && cmake -S . -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON >/dev/null \
  && cmake --build build/cmake && ctest --test-dir build/cmake --output-on-failure"

step "makepkg"
as_builder bash -c "git config --global --add safe.directory '*' && cd '$WORK/goldenglass/packaging/goldenglass' \
  && GOLDENGLASS_BRANCH=ci-build makepkg -f --nodeps --noconfirm"

mkdir -p "$ROOT/ci-artifacts"
# sin el paquete de símbolos (-debug) que Arch genera por defecto
find "$WORK/goldenglass/packaging/goldenglass" -maxdepth 1 -name '*.pkg.tar.zst' ! -name '*-debug-*' \
  -exec cp -t "$ROOT/ci-artifacts/" {} +
step "Paquetes"
ls -1 "$ROOT/ci-artifacts"
