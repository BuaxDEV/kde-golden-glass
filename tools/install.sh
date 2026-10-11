#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Instalación de desarrollo de GoldenGlass en ~/.local (sin empaquetar).
# Para instalar en el sistema usar el PKGBUILD de packaging/.
#
#   tools/install.sh            genera e instala (copia)
#   tools/install.sh --dev      genera e instala con symlinks (iterar sin reinstalar)
#   tools/install.sh --uninstall
#
# No aplica nada: para usar el tema, elegir el Global Theme en Preferencias del
# Sistema › Colores y temas, o `plasma-apply-lookandfeel -a org.goldenglass.light.desktop`.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

# origen (relativo a ROOT; archivo o carpeta) → destino
declare -A TARGETS=(
  [build/color-schemes/GoldenGlassLight.colors]="$DATA/color-schemes/GoldenGlassLight.colors"
  [build/color-schemes/GoldenGlassDark.colors]="$DATA/color-schemes/GoldenGlassDark.colors"
  [fontconfig/60-goldenglass.conf]="$CONF/fontconfig/conf.d/60-goldenglass.conf"
  [build/plasma/desktoptheme/GoldenGlass]="$DATA/plasma/desktoptheme/GoldenGlass"
  [build/plasma/look-and-feel/org.goldenglass.light.desktop]="$DATA/plasma/look-and-feel/org.goldenglass.light.desktop"
  [build/plasma/look-and-feel/org.goldenglass.dark.desktop]="$DATA/plasma/look-and-feel/org.goldenglass.dark.desktop"
  [plasma/shell/org.goldenglass.desktop]="$DATA/plasma/shells/org.goldenglass.desktop"
  [build/plasma/plasmoids/org.goldenglass.systemmenu]="$DATA/plasma/plasmoids/org.goldenglass.systemmenu"
  [build/plasma/plasmoids/org.goldenglass.controlcenter]="$DATA/plasma/plasmoids/org.goldenglass.controlcenter"
  [assets/logo/goldenglass.svg]="$DATA/icons/hicolor/scalable/apps/goldenglass.svg"
  [assets/logo/goldenglass-symbolic.svg]="$DATA/icons/hicolor/scalable/apps/goldenglass-symbolic.svg"
)

mode=copy
case "${1:-}" in
  --dev) mode=link ;;
  --uninstall) mode=uninstall ;;
  "") ;;
  *) echo "uso: $0 [--dev|--uninstall]" >&2; exit 2 ;;
esac

refresh_caches() {
  fc-cache -f >/dev/null
  command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true
}

if [[ $mode == uninstall ]]; then
  for dst in "${TARGETS[@]}"; do
    [[ -e $dst || -L $dst ]] && rm -rfv -- "$dst"
  done
  refresh_caches
  exit 0
fi

echo "Generando desde tokens…"
python3 "$ROOT/tools/gen_tokens.py" >/dev/null

echo "Instalando ($mode)…"
for src in "${!TARGETS[@]}"; do
  dst="${TARGETS[$src]}"
  mkdir -p -- "$(dirname -- "$dst")"
  [[ -e $dst || -L $dst ]] && rm -rf -- "$dst"
  if [[ $mode == link ]]; then
    ln -sfnv -- "$ROOT/$src" "$dst"
  elif [[ -d $ROOT/$src ]]; then
    cp -rv -- "$ROOT/$src" "$dst" | tail -1
  else
    install -Dm644 -v -- "$ROOT/$src" "$dst"
  fi
done

refresh_caches
echo "Listo. Aplicar: plasma-apply-lookandfeel -a org.goldenglass.light.desktop (o .dark.desktop)"
