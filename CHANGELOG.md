# Cambios

## [Unreleased]

### Cambios

- **Semáforos grises en ventanas inactivas**, como macOS: sin color ni glifo
  hasta que el ratón pasa por el grupo, que los colorea y muestra los glifos
  aunque la ventana siga sin foco (`traffic_lights.inactive_colored = false`).
  En las ventanas CSD de GTK4/libadwaita el grupo entero reacciona; en GTK3
  solo el botón bajo el ratón.
- **Sombra de las ventanas sin foco:** más corta y suave que la de la ventana
  activa, como en macOS 27 (tokens `[shadow.inactive]`, por calibrar). Se
  ajusta sin interfaz con `InactiveShadowSize` e `InactiveShadowStrength` en
  `goldenglassrc [Common]` y nunca supera a la activa. Las dos sombras se
  preparan de antemano: cambiar el foco no dibuja nada. La opacidad del
  contorno de la ventana sale del token `shadow.outline_alpha`.
- **Atajos de ventana** (script `org.goldenglass.shortcuts`), como Fn+Ctrl+F/C
  de macOS Sequoia con Meta en lugar de Fn: `Meta+Ctrl+F` llena la pantalla y
  `Meta+Ctrl+C` centra la ventana. Para volver al tamaño anterior (maximizada,
  en mosaico o a pantalla completa) sirve el atajo nativo de KWin
  `Meta+Retroceso`. Las mitades siguen siendo las nativas `Meta+flechas`, y los
  cuartos se alcanzan encadenándolas. Las instalaciones existentes reciben los
  atajos nuevos al recargar KWin o iniciar sesión, sin cambiar los que ya
  hubieras reasignado.
- **Los plasmoids siguen la velocidad de animación global:** el Centro de
  control, Apps y el dock (paneles, tarjetas, desplazamiento, rebote y
  ampliación) usan la «Velocidad de animación» de Ajustes del sistema, como el
  resto de Plasma, y la cambian en vivo; al mínimo no animan y los paneles se
  abren y cierran al momento. Con la velocidad normal todo dura lo mismo que
  antes. Las esperas (antes de mostrar el nombre de la app o de ocultar las
  miniaturas y la barra de desplazamiento) no cambian.
- **Efectos de ventana como en macOS** (`goldenglass-windows`, al iniciar
  sesión con un Global Theme GoldenGlass): las ventanas se minimizan con el
  genio hasta su icono del dock, se abren creciendo desde el 92 % y se cierran
  hacia el 95 % (tokens `[kwin]`, por calibrar), y la esquina superior
  izquierda ya no abre la vista general. Solo se escribe lo que no hubieras
  cambiado, una sola vez, y se aplica sin reiniciar la sesión; las
  instalaciones existentes lo reciben al iniciar sesión.
- **Reducir movimiento** en Ajustes del sistema › Vidrio › Accesibilidad: las
  ventanas aparecen y desaparecen con un fundido en vez de escalar, el cambio
  de escritorio se funde en vez de deslizarse y minimizar no anima; en el
  Centro de control, Apps y el dock los paneles solo se funden, los iconos no
  rebotan y las listas se detienen en los extremos sin estirarse. Al
  desactivarlo vuelven tus efectos anteriores, salvo los que hayas cambiado
  mientras tanto. También desde la terminal: `goldenglass-windows
  --reduce-motion on|off`.
- **Dock:** una app con todas sus ventanas minimizadas conserva su icono, como
  en macOS (antes desaparecía y el genio acababa en un hueco).
- **`goldenglass-glass`:** el módulo de Ajustes y el slider del Centro de
  control ya no se pisan si lanzan la herramienta a la vez: toda operación que
  escribe (`--level`, `--refraction`, `--menubar-background`, `--check`) toma
  un `flock` exclusivo en `$XDG_RUNTIME_DIR/goldenglass-glass.lock` y la
  segunda espera a la primera; `--get*` no esperan. El tema
  `GoldenGlassTuned` se genera en un directorio hermano y se cambia de golpe,
  así que Plasma nunca lo ve a medias.
- **Borde del vidrio como en macOS 27:** una línea oscura fina por fuera y el
  filo de luz justo dentro, ahora dibujados por encima del contenido del dock,
  la barra y los popups (antes el relleno del Plasma Style tapaba casi todo el
  filo). El efecto de refracción lo pinta en un pase aparte solo sobre la
  banda del borde (≈ 0,04 ms por fotograma en 4K), y el Plasma Style lleva
  además una línea negra y otra blanca que se ven también sin el efecto. Con
  el vidrio más opaco el borde conserva más contraste (tokens
  `[glass.refraction]` y `[glass.border]`, por calibrar).
- **Reducir transparencia** en Ajustes del sistema › Vidrio › Accesibilidad:
  la barra de menús, el dock, los popups, el panel de Apps, el Centro de
  control, las barras de título, las toolbars, las barras laterales y los
  menús se vuelven opacos, sin difuminado ni refracción. Tu nivel de vidrio se
  conserva para cuando lo desactives; mientras tanto el slider y «Refracción»
  quedan deshabilitados. También desde la terminal: `goldenglass-glass
  --reduce-transparency on|off`.
- **Mostrar bordes** en Ajustes del sistema › Vidrio › Accesibilidad, como en
  macOS 27: un borde fino del color del texto en los botones, los campos de
  texto, los botones de las toolbars (que muestran su forma sin pasar el
  ratón), las cápsulas de Dolphin, las ventanas (contorno y sombra) y el vidrio
  de la barra de menús, el dock, los popups y Spotlight. Funciona con cualquier
  nivel de vidrio y junto a «Reducir transparencia». También desde la
  terminal: `goldenglass-glass --show-borders on|off`. Las apps GTK llegarán
  más adelante (tokens `[accessibility.borders]`, por calibrar).
- **La refracción sigue de verdad al nivel de vidrio:** el efecto de KWin no
  se enteraba de los cambios de nivel hasta reiniciar la sesión;
  `goldenglass-glass` ahora se lo pide directamente.
- **El vidrio de Plasma ya no se vuelve opaco al activar la refracción:**
  activarla en vivo (también el primer inicio de sesión tras instalar)
  dejaba a Plasma sin blur hasta reiniciar KWin.

### Proyecto

- Los colores, opacidades y sombras del squircle de los iconos de apps pasan a
  la sección `[icon_tile]` de los tokens, sin cambio visual (los SVG generados
  son idénticos byte a byte). `goldenglass-icons` instala
  `/usr/share/goldenglass/icon-tile.json` con esos valores para que
  `goldenglass-wrap-icons` siga sin depender de los tokens ni de otros paquetes.
- `goldenglass-plasma` instala `goldenglass-windows`, su autostart y
  `/usr/share/goldenglass/windows.json` (tokens `[kwin]`); `tools/install.sh`
  añade el lanzador y el autostart. `tools/sandbox.sh` usa el módulo QML
  `org.goldenglass.glass` del árbol compilado en vez del instalado.
- `tools/sandbox.sh`: cierra al salir el KWin virtual que lanza (antes quedaba
  vivo: sus capacidades impiden leer su entorno) y admite
  `GG_SANDBOX_WIDTH`, `GG_SANDBOX_HEIGHT` y `GG_SANDBOX_SCALE` para probar en
  4K y con escalas fraccionarias.
- `tools/preview_style.py --show-borders` muestra el estilo de apps con
  «Mostrar bordes», y la vista previa incluye una toolbar.
- Los plasmoids leen la accesibilidad con un único singleton,
  `Accessibility.qml` (`MotionReduce.qml` pasa a ser
  `AccessibilityReader.qml`); `goldenglass-glass` aplica todo con `apply()`,
  que ya prevé «Mostrar bordes».

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
