# Cambios

## 0.2.1 — 2026-10-15

Correcciones de seguridad, compatibilidad con KWin 6.8 y publicación como
proyecto open source. **Actualizar** si tienes instalado `goldenglass-plasma`
0.2.0 o anterior: el ayudante de `goldenglass-system` que se ejecuta como root
tenía una escalada de privilegios local.

### Seguridad

- **Escalada a root en `goldenglass-system`:** pkexec conserva el umask de
  quien llama, así que con `umask 000` el ayudante creaba
  `/etc/sddm.conf.d/99-goldenglass.conf` y `/var/lib/goldenglass` escribibles
  por cualquiera (SDDM ejecuta como root los comandos de su configuración).
  Ahora fija `umask 022`, escribe como root de forma atómica, con permisos
  fijos y sin seguir enlaces, y cierra a 0755 un `/var/lib/goldenglass` que
  haya quedado abierto.
- La acción de polkit pide la contraseña cada vez (`auth_admin`, antes
  `auth_admin_keep`, que dejaba a otros procesos de la sesión reutilizarla unos
  minutos). El módulo «Arranque e inicio de sesión» aplica todos los cambios en
  una sola llamada (`goldenglass-system apply`) y la pide una vez.
- Lo que se copia al Plasma Login Manager: solo archivos regulares de hasta
  1 MiB (un FIFO o un archivo enorme ya no bloquean al ayudante), con límite de
  tiempo, y el `fonts.conf` del greeter no carga fuentes ni configuración de
  un home. El archivo de estado se valida antes de usarlo.

### Cambios

- **KWin 6.8:** el efecto de vidrio compila con la nueva API (sigue
  compilando con 6.7) y trae el arreglo de upstream de la región de desenfoque
  en ventanas con decoración propia (GTK, Electron).
- **Dock:** arrastrar apps desde Apps para fijarlas (también un `.desktop`
  desde Dolphin), «Mantener en el Dock» en el menú de Apps, y el dock oculto
  aparece mientras Apps está abierto. El menú contextual del dock funciona y
  los menús de los plasmoids son de vidrio con desenfoque. Konsole y
  Preferencias del Sistema solo se fijan si están instalados. El rebote de un
  icono ampliado ya no se recorta. Las vistas previas de ventanas ya no
  mantienen un flujo de PipeWire por ventana.
- **Campos de texto:** anillo de foco ceñido al borde, como en macOS (tokens
  `[focus_ring]`).

### Proyecto

- Repositorio público en <https://github.com/BuaxDEV/kde-golden-glass>.
- Cumple [REUSE](https://reuse.software): la licencia de cada archivo, incluidas
  las partes de Darkly/Breeze (GPL-2.0-or-later, MIT), KWin y Plasma, está en
  su cabecera o en `REUSE.toml`.
- `CONTRIBUTING.md` (commits firmados con DCO), código de conducta,
  `SECURITY.md` (reporte privado de vulnerabilidades) y plantillas.
- CI: token de solo lectura, acciones fijadas por commit con Dependabot, y
  comprobaciones de REUSE, gitleaks y DCO en cada PR.

## 0.2.0 — 2026-10-12

Arranque, inicio de sesión, sonidos, dock con ampliación y refracción
(fases F7–F11 de [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

- **Sonidos** (`goldenglass-sounds`): tema de sonidos de cristal sintetizado
  desde los tokens; solo los eventos de macOS (y los avisos de Plasma que no
  deben perderse), el resto en silencio. Sonido al iniciar sesión opcional.
  Módulo «Efectos de sonido» en Multimedia.
- **Arranque** (`goldenglass-plymouth`): Plymouth negro o gris claro con el
  logo y una barra fina, contraseña de disco (LUKS) en un campo de vidrio y
  solo el logo al apagar. Vista previa sin reiniciar: `tools/preview_plymouth.sh`.
- **Inicio de sesión** (`goldenglass-login`): tema de SDDM como la pantalla de
  bloqueo (fondo de día o de noche, reloj grande, avatar y contraseña, fila
  de usuarios). En Plasma Login Manager, que no admite temas, el fondo de
  GoldenGlass y los ajustes de Plasma del usuario. Vista previa:
  `tools/preview_login.sh`.
- **`goldenglass-system`**: activa y desactiva sonidos, chime, Plymouth y
  login, guarda lo anterior y lo restaura; las partes del sistema con pkexec.
  Módulo «Arranque e inicio de sesión» en Colores y temas.
- **Dock** (`org.goldenglass.dock`): un solo plasmoid con Apps, apps fijadas y
  abiertas, recientes y Papelera; **ampliación** bajo el cursor, rebote al
  abrir, vistas previas de ventanas, menú con las acciones de la app,
  arrastrar para reordenar. Módulo «Dock» en Espacio de trabajo y
  `goldenglass-dock`.
- **Refracción** (efecto de KWin `goldenglass_glass`, en `goldenglass-kstyle`):
  el vidrio de Plasma curva el fondo en sus bordes, como Liquid Glass, con
  dispersión, filo de luz y tinte adaptativo; sigue al slider de vidrio.
  Interruptor en el módulo Vidrio; si KWin no carga el efecto, vuelve el Blur.
- CI: `vulkan-headers` entre las dependencias de compilación.

## 0.1.0

Tema completo (fases F0–F6): tokens de diseño, estilo de aplicaciones y
decoración (fork de Darkly) con semáforos, Plasma Style y Global Themes claro
y oscuro, barra de menús y dock, Spotlight, pantalla de bloqueo, módulo de
Ajustes «Vidrio», Centro de control, Apps, menú de sistema, Papelera, iconos,
cursores, fondo de pantalla, GTK y libadwaita, PKGBUILD dividido y CI.
