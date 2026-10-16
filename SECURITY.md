<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Seguridad

## Versiones con soporte

Solo la última versión publicada y la rama `main` reciben correcciones de
seguridad.

## Reportar una vulnerabilidad

**No abras un issue público.** Usa el reporte privado de GitHub:
[Report a vulnerability](https://github.com/BuaxDEV/kde-golden-glass/security/advisories/new)
(pestaña *Security* del repositorio).

Incluye, si puedes: versión o commit, pasos para reproducirlo, impacto y una
posible corrección. Recibirás respuesta en un plazo de 7 días; una vez
confirmada la vulnerabilidad, la corrección y el aviso se publican juntos y se
te da crédito si lo deseas.

## Superficie sensible

Estas partes se ejecutan con privilegios o modifican el arranque del sistema, y
son las que más interesa revisar:

- `tools/goldenglass-system-helper` y `tools/system.py`: se ejecutan como root
  mediante `pkexec` (acción de polkit `org.goldenglass.system`).
- `tools/org.goldenglass.system.policy`: política de polkit.
- Plymouth, SDDM / Plasma Login Manager e initramfs (`goldenglass-plymouth`,
  `goldenglass-login`).
- `packaging/goldenglass/PKGBUILD` y `tools/install.sh`.
- El efecto de KWin `kwin-effect/` (se carga dentro del compositor).
