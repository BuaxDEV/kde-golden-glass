#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Integración continua de GoldenGlass, dentro de un contenedor Arch Linux:
#
#   1. dependencias de compilación del PKGBUILD (pacman)
#   2. comprobaciones rápidas: Python, bash, traducciones
#   3. generadores (tools/gen_tokens.py)
#   4. C++: compilación y pruebas (ctest)
#   5. makepkg del commit actual: los paquetes quedan en ci-artifacts/
#
# Trabaja sobre un clon en /tmp (makepkg no corre como root y así no se
# tocan los permisos del repositorio montado). Lo usa .github/workflows/ci.yml;
# en local:
#
#   podman run --rm -v "$PWD":/src:Z -w /src docker.io/library/archlinux:latest tools/ci.sh
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

step "Dependencias de compilación"
mapfile -t makedeps < <(cd "$ROOT/packaging/goldenglass" && startdir=$PWD && source PKGBUILD && printf '%s\n' "${makedepends[@]}")
pacman -Syu --noconfirm --needed base-devel "${makedeps[@]}"

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
as_builder bash -c "cd '$WORK/goldenglass' && python -m py_compile tools/*.py && for f in tools/*.sh; do bash -n \"\$f\"; done \
  && find plasma po login -name '*.po' -print0 | xargs -0 -n1 msgfmt --check -o /dev/null"

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
