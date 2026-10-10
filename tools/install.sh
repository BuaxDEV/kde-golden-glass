#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Instalación de desarrollo de GoldenGlass en ~/.local (sin empaquetar).
# Para instalar en el sistema usar el PKGBUILD de packaging/.
#
#   tools/install.sh            genera e instala (copia)
#   tools/install.sh --dev      genera e instala con symlinks (iterar sin reinstalar)
#   tools/install.sh --uninstall

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

# origen (relativo a ROOT) → destino
declare -A TARGETS=(
  [build/color-schemes/GoldenGlassLight.colors]="$DATA/color-schemes/GoldenGlassLight.colors"
  [build/color-schemes/GoldenGlassDark.colors]="$DATA/color-schemes/GoldenGlassDark.colors"
  [fontconfig/60-goldenglass.conf]="$CONF/fontconfig/conf.d/60-goldenglass.conf"
)

mode=copy
case "${1:-}" in
  --dev) mode=link ;;
  --uninstall) mode=uninstall ;;
  "") ;;
  *) echo "uso: $0 [--dev|--uninstall]" >&2; exit 2 ;;
esac

if [[ $mode == uninstall ]]; then
  for dst in "${TARGETS[@]}"; do
    [[ -e $dst || -L $dst ]] && rm -v -- "$dst"
  done
  fc-cache -f >/dev/null
  exit 0
fi

echo "Generando desde tokens…"
python3 "$ROOT/tools/gen_tokens.py"

echo "Instalando ($mode)…"
for src in "${!TARGETS[@]}"; do
  dst="${TARGETS[$src]}"
  mkdir -p -- "$(dirname -- "$dst")"
  if [[ $mode == link ]]; then
    ln -sfnv -- "$ROOT/$src" "$dst"
  else
    install -Dm644 -v -- "$ROOT/$src" "$dst"
  fi
done

fc-cache -f >/dev/null
echo "Listo. Aplicar colores: plasma-apply-colorscheme GoldenGlassLight | GoldenGlassDark"
