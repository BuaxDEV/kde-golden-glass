#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Exige la cabecera SPDX en los archivos nuevos de un PR. REUSE.toml da una
# licencia por defecto a todo (path = "**"), así que `reuse lint` no avisa de un
# archivo nuevo sin cabecera, y uno nuevo en kstyle/, kdecoration/ o
# libgoldenglasscommon/ quedaría como GPL-2.0-or-later (la de Darkly).
#
#   tools/check_spdx.sh BASE [HEAD]     archivos añadidos desde merge-base(BASE, HEAD)
#
# Un archivo nuevo pasa si contiene SPDX-License-Identifier, si tiene al lado un
# <archivo>.license o si REUSE.toml lo nombra tal cual (sin comodines). Quedan
# fuera los formatos sin comentarios (JSON, imágenes, sonidos, fuentes), los
# textos de LICENSES/ y las copias de upstream (sus cabeceras no se tocan).

set -euo pipefail

base=${1:?uso: $0 BASE [HEAD]}
tip=${2:-HEAD}
cd "$(git rev-parse --show-toplevel)"
for rev in "$base" "$tip"; do
  git rev-parse --verify --quiet "$rev^{commit}" >/dev/null || { echo "$0: commit no válido: $rev" >&2; exit 2; }
done

# sin comentarios donde poner la cabecera (REUSE.toml los cubre)
exempt_ext='json|png|jpg|jpeg|gif|webp|ico|svgz|ogg|oga|wav|flac|ttf|otf|woff|woff2|license'
# textos de licencia, capturas y copias de upstream (ver REUSE.toml y UPSTREAM.md)
exempt_paths=(
  LICENSES/
  docs/screenshots/
  plasma/shell/org.goldenglass.desktop/contents/lockscreen/
)

fail=0
while IFS= read -r -d '' file; do
  [[ $file =~ \.($exempt_ext)$ ]] && continue
  for prefix in "${exempt_paths[@]}"; do
    [[ $file == "$prefix"* ]] && continue 2
  done
  [[ -e "$file.license" ]] && continue
  grep -qF "\"$file\"" REUSE.toml && continue
  # la cabecera va al principio: basta con mirar las primeras líneas
  # REUSE-IgnoreStart
  head -n 20 -- "$file" | grep -q 'SPDX-License-Identifier:' && continue
  # REUSE-IgnoreEnd
  echo "::error file=$file::archivo nuevo sin cabecera SPDX (SPDX-License-Identifier, ver CONTRIBUTING.md)"
  fail=1
done < <(git diff -z --name-only --diff-filter=A "$base...$tip")

if ((fail == 0)); then
  echo "Cabeceras SPDX: bien"
fi
exit "$fail"
