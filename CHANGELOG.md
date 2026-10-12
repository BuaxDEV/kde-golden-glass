# Cambios

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
