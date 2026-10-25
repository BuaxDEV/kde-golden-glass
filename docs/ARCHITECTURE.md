# GoldenGlass — Arquitectura

Tema completo para KDE Plasma en CachyOS inspirado en macOS 27 "Golden Gate"
(refinamiento de Liquid Glass presentado en WWDC 2026, publicado el 14/09/2026).

## 1. Objetivos

- Fidelidad **alta** a macOS: barra de menús superior con menú global, dock
  centrado, semáforos a la izquierda, Spotlight, Apps, Centro de control.
- Variantes **clara, oscura y automática** (día/noche).
- Replicar el **slider de transparencia** de macOS 27 como módulo de Ajustes.
- Distribuible en CachyOS/Arch mediante PKGBUILD.

### Referencia visual (macOS 27 Golden Gate)

| Rasgo | Detalle | Dónde se implementa |
|---|---|---|
| Slider de vidrio | 3 muescas (más claro / medio por defecto / más opaco) + valores intermedios; afecta dock, widgets, sidebars, toolbars y sus botones | `kcm/` + todos los consumidores de tokens |
| Menos transparencia por defecto | Más contraste y legibilidad que Tahoe | `tokens/` (nivel medio) |
| Esquinas de ventana | Radio más cerrado que Tahoe y uniforme en todas las apps | `kdecoration/`, `kstyle/` |
| Semáforos | Sombreado tipo vidrio ("candy-like", eco de Aqua) | `kdecoration/` |
| Sidebars | Pegadas al borde izquierdo (no flotantes), fondo más oscuro, iconos a color | `kstyle/` |
| Toolbars | Barras reales y uniformes, no botones flotantes | `kstyle/` + `kdecoration/` |
| Finder | Sin barra de título: semáforos sobre la barra lateral, toolbar en la misma fila con botones en cápsulas de vidrio, la carpeta como título, lista con franjas | `kstyle/goldenglassfinder.cpp` + `kdecoration/` (Dolphin) |
| Menús | Sin iconos junto a cada comando | `kstyle/` |
| Barra de menús | Sin fondo (texto sobre el fondo de pantalla) y fondo translúcido opcional; nombre de la app en negrita; reloj «Vie 16 de oct  1:09 p.m.»; atenuada en la pantalla sin foco; desbordamiento de iconos tras un chevron «» | `plasma/shell` (`Panel.qml`), `plasma/desktoptheme`, layout, plasmoids `appname` y `clock` |
| Iconos de app | Squircle con capas y más detalle | `icons/` |
| Liquid Glass | El fondo se curva como una lente en los bordes del vidrio, con dispersión, filo de luz y tinte que se adapta al fondo | `kwin-effect/` (F11) |
| Dock | Ampliación de los iconos bajo el cursor, rebote al abrir, apps recientes | `plasma/plasmoids/org.goldenglass.dock` (F10) |
| Arranque y sesión | Logo con barra de progreso, pantalla de inicio de sesión como la de bloqueo, sonidos del sistema | `plymouth/`, `login/`, `tools/sounds.py` (F7–F9) |

Fuentes: Six Colors (review), 9to5Mac (slider de Liquid Glass), Digital Trends,
Wccftech. Los valores numéricos exactos (radios, opacidades) no están publicados:
los tokens parten de valores iniciales que se calibran contra capturas.

## 2. Plataforma soportada

- **Plasma ≥ 6.8, solo Wayland.** Qt 6. Sin soporte X11.
- Desarrollo sobre CachyOS (Plasma 6.8.1, Qt 6.12, KWin 6.8.1).

## 3. Principio rector: tokens de diseño como única fuente de verdad

Todos los valores visuales (paleta clara/oscura, radios, niveles de vidrio, blur,
sombras, tipografía, semáforos) viven en **`tokens/goldenglass.toml`**.
`tools/gen_tokens.py` genera a partir de ahí, en **`build/`** (no versionado):

| Salida | Consumidor | Estado |
|---|---|---|
| `build/color-schemes/*.colors` | Plasma / KColorScheme (todas las apps KDE) | ✅ F0 |
| `build/tokens.json` | KCM y plasmoids QML | ✅ F0 |
| `build/cmake/generated/goldenglass_tokens.h` (lo genera CMake al configurar) | Valores por defecto de los `.kcfg` del estilo y la decoración | ✅ F1 |
| `build/plasma/desktoptheme/GoldenGlass/` (SVG dibujados por código) | Plasma Style | ✅ F2 |
| `build/plasma/look-and-feel/org.goldenglass.{light,dark}.desktop/` | Global Themes (desde `plasma/look-and-feel/common/`) | ✅ F2 |
| `build/plasma/shells/org.goldenglass.desktop/` (desde `plasma/shell/`, con `tokens.js`; `tools/shell.py`) | Shell: pantalla de bloqueo y panel | ✅ |
| `build/wallpapers/GoldenGlass/` (numpy, se cachea) | Fondo de pantalla día/noche | ✅ F5 |
| `build/cursors/GoldenGlass-cursors/` (QtSvg, se cachea) | Tema de cursores (SVG + Xcursor) | ✅ F5 |
| `build/icons/GoldenGlass{,-Dark}/` (SVG dibujados por código) | Tema de iconos claro/oscuro | F5 (base ✅) |
| `build/gtk/GoldenGlass{,-Dark}/`, `build/gtk/libadwaita.css` | GTK3 / GTK4 / libadwaita | ✅ F6 |
| `build/sounds/GoldenGlass/` (numpy + python-soundfile, se cachea) | Tema de sonidos freedesktop | ✅ F7 |
| `build/plymouth/goldenglass{,-light}/` (piezas dibujadas con QtSvg/QPainter, se cachea) | Temas de Plymouth negro y gris | ✅ F8 |
| `build/login/sddm/GoldenGlass/` (desde `login/sddm/`, `theme.conf` y `.qm` generados) | Tema de SDDM | ✅ F9 |
| `contents/ui/tokens.js` y `contents/config/main.xml` (plantilla `.in`) del dock | Plasmoid `org.goldenglass.dock` | ✅ F10 |
| `goldenglass_tokens.h` (secciones `[dock]` y `[glass.refraction]`) | Valores de fábrica del dock y del efecto de KWin | ✅ F10, F11 |

**Regla:** los archivos generados no se editan a mano ni se versionan. Se cambia
el token y se regenera (`install.sh` y el PKGBUILD lo hacen solos).

## 4. Componentes

```
goldenglass/
├── tokens/              # goldenglass.toml
├── tools/               # gen_tokens.py (+ plasma_theme.py, lookandfeel.py, wallpaper.py,
│                        # cursors.py, sounds.py, plymouth.py…; utilidades comunes
│                        # en ggcommon.py), install.sh,
│                        # system.py (goldenglass-system), windows.py (goldenglass-windows),
│                        # preview_plasma.py (vista previa), sandbox.sh (sesión aislada)
├── assets/logo/         # logo GoldenGlass (símbolo monocromo y versión a color)
├── kstyle/              # QStyle C++ (fork de Darkly) → goldenglass6.so
├── kdecoration/         # Plugin KDecoration3
├── kwin-effect/         # efecto de KWin goldenglass_glass (F11)
├── kcm/                 # Módulo de Ajustes "GoldenGlass"
├── plasma/
│   ├── look-and-feel/   # plantilla común de los Global Themes (layout, splash)
│   ├── shell/           # shell org.goldenglass.desktop (pantalla de bloqueo)
│   └── plasmoids/       # Centro de control, Apps, menú de sistema, papelera, dock
├── login/sddm/          # tema QML de SDDM (F9)
├── plymouth/            # plantilla del tema de Plymouth (script) (F8)
├── fontconfig/          # alias de familias tipográficas
├── packaging/           # PKGBUILD dividido
├── docs/
└── build/               # salidas generadas (no versionado)
```

### 4.1 Estilo de aplicaciones — `kstyle/` (C++)
- **Fork de [Darkly](https://github.com/Bali10050/darkly)** v0.5.40 (GPL-2.0-or-later →
  publicado como GPL-3.0-or-later). Renombrado completo; tabla de equivalencias
  en `UPSTREAM.md`. Identificadores: estilo `GoldenGlass` (`goldenglass6.so`),
  decoración `org.goldenglass.decoration`, config `goldenglassrc`, app
  `goldenglass-settings`, señal D-Bus `org.goldenglass.Style`. No choca con un
  Darkly instalado: ambos pueden convivir.
- Darkly ya aporta transparencia y blur por ventana. Se añade: sidebars de borde
  a borde con fondo más oscuro, toolbar unificada con la barra de título, menús
  sin iconos, controles con radios de los tokens.
- Lee `~/.config/goldenglassrc` y reacciona en vivo (KConfigWatcher) a los
  cambios del slider.
- **Valores de fábrica desde los tokens:** los `.kcfg` usan
  `<default code="true">GoldenGlass::Tokens::…</default>`. Los módulos de
  configuración heredados siguen sirviendo para ajustar; sin `goldenglassrc`
  rige `goldenglass.toml`.
- **Barras laterales** (`_kde_side_panel_view` y el dock de Dolphin): color
  `sidebar` de los tokens, de borde a borde, con una línea fina (`separator`)
  hacia el contenido y sin sombras. Los iconos a color de las barras laterales
  llegan en F5: los iconos simbólicos de lugares usarán `ColorScheme-Highlight`
  (el delegado de Dolphin pinta sus iconos y el estilo no puede teñirlos).
- **Menús** de solo texto (token `menu.show_icons`, opción `MenuItemIcons`) con
  ✓ en el margen para las opciones activas y selección en color de acento.
  Afecta a las apps QtWidgets; los menús QML de Kirigami siguen la preferencia
  global de KDE `ShowIconsInMenuItems`.
- **Radios por función, en px** (compartidos por estilo y decoración en
  `[Common]`): `CornerRadius` (controles), `MenuCornerRadius` (menús, popups y
  sus sombras), `WindowCornerRadius` (decoración y región de blur de la ventana,
  para que coincidan).
- Las apps Kirigami/QML lo heredan vía `qqc2-desktop-style`.

#### Dolphin como Finder — `goldenglassfinder.cpp`

Dolphin imita el Finder de macOS 27 (tokens `[finder]` y los colores
`finder_*` de `[light]`/`[dark]`). Solo para las apps de
`[Common] IntegratedTitleBarApps` (de fábrica `org.kde.dolphin`, token
`finder.apps`).

- **Sin barra de título.** La decoración la quita en las ventanas de esas apps
  que exportan su menú (`hasApplicationMenu`: la ventana principal, no los
  diálogos), conserva sombra, esquinas redondeadas arriba
  (`setBorderRadius`) y el borde superior para redimensionar. El estilo
  comprueba lo mismo (`QMenuBar::isNativeMenuBar` y `kwinrc` con
  `org.goldenglass.decoration`) y entonces la toolbar pinta los semáforos
  (`libgoldenglasscommon/goldenglasstrafficlight.cpp`, los de la decoración)
  con la regla de Apple, símbolos al pasar el ratón y las mismas acciones.
  Doble clic en la toolbar vacía maximiza; arrastrar mueve la ventana.
- **Barra lateral hasta arriba.** La toolbar y la cabecera de columnas tienen
  el color y el vidrio de la barra lateral; un separador invisible al
  principio de la toolbar (`goldenglass_finder_lead`) la hace tan ancha como la
  barra lateral, o como los semáforos si está oculta. `QToolBarLayout` solo
  admite márgenes iguales (intercambia izquierda y arriba): por eso el
  separador, y el estilo recoloca los márgenes tras cada cambio de estilo.
  Sin línea entre barra lateral y contenido; el separador del dock y el
  hueco de la barra de desplazamiento se pintan, y la vista va sin marco. Con
  otro estilo, `unpolish` devuelve márgenes, marco y paleta.
- **Cápsulas.** Los botones entre separadores forman una cápsula
  (`capsule_height`); uno solo es un círculo (búsqueda). Los checables (vistas)
  son un control segmentado cuya píldora se desliza (`slide_ms`, resorte); ‹ ›
  llevan una línea entre ellos. Al pasar el ratón el segmento se ilumina y al
  pulsar cede y vuelve con rebote (`press_scale`, `release_overshoot`). ⌄ solo
  en menús de clic (Agrupar), no en los de pulsación larga (historial de ‹ ›).
  Glifos propios para ⋯, búsqueda y agrupar.
- **Título.** La ruta (`KUrlNavigator`) solo enseña la carpeta actual, en
  negrita y mayor (`title_scale`); Ctrl+L la edita. KIO borra tarde los botones
  que sobran, así que se actualiza en diferido.
- **Barra lateral** (el dock `placesDock`): selección en píldora gris (`finder_sidebar_selected`) que
  ocupa la fila y se desliza (`sidebar_slide_ms`), sin resaltado al pasar el
  ratón, texto sin cambiar de color. KIO dibuja el icono a 4 px del borde del
  elemento (y el texto relativo a la vista, no al elemento): el margen del dock
  (`sidebar_margin`) y un margen interior de la vista (`sidebar_icon_padding`)
  los dejan dentro de la píldora, que se pinta en la vista, bajo su viewport.
  Cada lugar mide `sidebar_row_height`.
- **Búsqueda como en Finder:** al buscar, la lupa de la toolbar se convierte
  en un campo en cápsula con lupa y el anillo de foco de `[focus_ring]`, de
  ancho fijo `search_width` (si compartiera el espacio libre con el título, se
  redimensionarían en bucle). Ese campo es del estilo (si XMLGUI reconstruye la
  toolbar se crea otro) y refleja el de la barra de búsqueda de Dolphin
  (`Search::Bar`), que se queda en su barra reducido a 0×0: texto, Intro y
  foco pasan de uno a otro (mover el de Dolphin dejaría a la barra con un
  puntero colgante al reconstruirse la toolbar). La barra queda en una fila del
  color de la toolbar con Aquí / En todas partes y Filtrar; sin ✕: Esc borra y
  luego cierra (el estilo reenvía Esc y ↓ a la barra). Al cerrar vuelve la lupa.
- **Lista:** franjas alternas redondeadas y separadas de los bordes
  (`row_inset`, `row_radius`), también bajo las filas vacías; Dolphin pinta las
  suyas de borde a borde con `AlternateBase`, que el estilo deja transparente
  (también en los diálogos de Dolphin). Qué filas llevan franja lo dice el
  propio Dolphin (`KItemListWidget::alternateBackground`, exportada por
  `libdolphinprivate`, resuelta con `dlsym`), así que con «Mostrar en grupos»
  la alternancia vuelve a empezar en cada grupo.
  Selección de fila completa con las mismas medidas; sin rectángulo de foco ni
  líneas de árbol. Cabecera de Finder: separadores cortos, columna ordenada en
  negrita con su chevron. La región de blur incluye la cabecera.
- **Valores de fábrica** (`goldenglassrc [Finder] DolphinDefaults`): la
  primera vez que Dolphin abre con GoldenGlass el estilo escribe, si el usuario
  no los tiene: la toolbar de Finder en `kxmlgui5/dolphin/dolphinui.rc` (el
  `dolphinui.rc` de Dolphin con otra `mainToolBar`; al actualizarse Dolphin,
  XMLGUI conserva esa toolbar), botones solo con icono, sin barra de estado,
  iconos de 16 px en la lista (`list_icon_size`) y la vista en lista con
  Nombre, Tamaño, Tipo y Modificado (`view_properties/global/.directory`, que
  Dolphin migra a sus atributos extendidos al guardar).
- Límites: Dolphin no tiene vista de galería ni Compartir/Etiquetas en la
  toolbar (van Dividir y ⋯); las barras de capacidad de los discos de la barra
  lateral las pinta su delegado y no se pueden quitar.

### 4.2 Decoración de ventanas — `kdecoration/` (C++, KDecoration3)
- En el mismo árbol CMake que `kstyle/` (como Breeze/Darkly), config compartida.
- **Semáforos** (`libgoldenglasscommon/goldenglasstrafficlight.cpp`, compartido con el estilo), como los de macOS 27 Golden
  Gate (Liquid Glass): gemas de vidrio de 14 px separadas 8 px con sombra suave
  que las separa de la ventana, relleno con volumen, borde fino, **brillo arriba
  y brillo abajo** y glifo tintado por botón (×, −, triángulos de pantalla
  completa; tokens `traffic_lights`). Al pulsar se encogen un poco. Al pasar el
  ratón por cualquiera aparecen los símbolos en los tres. En ventanas sin foco son
  vidrio gris sin glifo, con los brillos atenuados (`inactive_shine`), como
  macOS; al pasar el ratón por el **grupo** se colorean y muestran los glifos
  aunque la ventana siga inactiva (`traffic_lights.inactive_colored`; con `true`
  van siempre en color). El
  zoom apunta hacia dentro con la ventana maximizada. **Posición** con la regla
  de Apple: el primer círculo está tan lejos del borde izquierdo como del
  superior (`Decoration::leftButtonsPadding`). Los semáforos CSD de GTK usan
  los mismos colores, glifos y brillos. `build/cmake/bin/trafficlight_preview
  salida.png` dibuja todos los estados para revisarlos sin KWin.
- Radio de esquina y sombras desde los tokens.
- **Sombra activa e inactiva**, como macOS 27: la ventana sin foco lleva una
  sombra más corta y suave (`[shadow.inactive]`, de fábrica ShadowMedium al
  25 %, frente a `[shadow.active]`, ShadowVeryLarge al 45 %; calibrar). En
  `goldenglassrc [Common]`, `InactiveShadowSize` e `InactiveShadowStrength`,
  sin interfaz en el diálogo de la decoración; los valores efectivos son
  `min(inactiva, activa)` y, sin sombra activa, tampoco hay inactiva
  (`gen_tokens` rechaza unos tokens con la inactiva mayor). La resolución y la
  clave de la caché están en `kdecoration/goldenglassshadowparams.h`, una
  cabecera pura con su prueba (`shadowparams_test`). Cada decoración guarda las
  dos sombras (`updateShadows()`, al configurar, cambiar de escala o
  maximizar); las texturas se comparten entre ventanas por estilo resuelto
  (tamaño, fuerza, color, radio, inicio del contorno y su opacidad,
  `shadow.outline_alpha`). Cambiar el foco solo elige una de las dos
  (`applyShadow()`): no renderiza nada, y el cambio es instantáneo porque
  KDecoration3 no funde sombras. Con
  `QT_LOGGING_RULES="goldenglass.decoration.shadow.debug=true"` KWin anota cada
  textura creada. Como el `padding` de la sombra cambia con el foco, también
  cambia la geometría expandida de la ventana (la del marco no).
- **Toolbar unificada:** con `decoration.glass_titlebar` la barra de título usa
  el mismo color (Header) y la misma opacidad de vidrio que la toolbar, y KWin
  difumina detrás de ambas: se ven como una sola barra. Los semáforos no pueden
  compartir fila con los botones de la toolbar, porque la toolbar la dibuja
  cada aplicación; la excepción son las apps de `IntegratedTitleBarApps`
  (Dolphin), que van sin barra de título y cuyo estilo pinta los semáforos
  (ver «Dolphin como Finder» en 4.1).

### 4.3 Efecto de vidrio
- **Base: blur nativo de KWin + superficies semitransparentes.** Es lo que se
  ve sin el efecto propio (o si no carga) y lo que siguen usando las ventanas
  de las apps.
- La opacidad de cada superficie sale del nivel de vidrio activo.
- **Refracción (F11):** efecto propio `goldenglass_glass` (activado de fábrica
  si KWin lo carga), ver 4.14.

### 4.4 Nivel de vidrio — `goldenglass-glass` y módulo de Ajustes (`kcm/`)

**`goldenglass-glass --level N`** (`tools/glass.py`, instalado con sus archivos
en `share/goldenglass`) aplica un nivel en vivo a las tres capas. Por dentro,
`--level`, `--reduce-transparency` y `--show-borders` llaman a `apply(tokens, *,
level=None, reduce_transparency=None, borders=None, reload_plasma=True)`: lo que
se pasa se guarda en `goldenglassrc` (con aviso de cambio) y lo que no se lee de
ahí, así que cada llamada deja las capas de acuerdo con todos los ajustes:

| Capa | Cómo |
|---|---|
| Estilo de apps | `goldenglassrc [Style]` (`MenuOpacity`, `ToolBarOpacity`, `DolphinSidebarOpacity`: menús, toolbars, barra lateral; el diálogo del estilo no tiene controles para ellas) + señal D-Bus `org.goldenglass.Style` → repinta las ventanas abiertas |
| Decoración | misma opacidad (`ToolBarOpacity`) + `KWin.reconfigure` → relee `goldenglassrc` |
| Plasma Style | nivel por defecto (y sin «Reducir transparencia» ni «Mostrar bordes») → tema del paquete `GoldenGlass`; si no → genera `GoldenGlassTuned` en `~/.local/share` y cambia a él (con rebote por `GoldenGlass` si ya estaba activo). El tema del paquete nunca se sobrescribe |
| Efecto de KWin | `org.kde.kwin.Effects.reconfigureEffect goldenglass_glass`: `KWin.reconfigure` no llega a los efectos, y el efecto vuelve a leer (`reparseConfiguration`) `goldenglassrc`, que la decoración tiene abierto en KWin |

El cambio de tema se hace dentro de plasmashell (`evaluateScript`,
`theme = …`), de forma síncrona; si plasmashell no corre, se escribe `plasmarc`.
Para cambios rápidos seguidos: al regenerar `GoldenGlassTuned` se borra su caché
de KSvg (caduca por segundos) y el rebote espera 0,35 s (libplasma agrupa los
avisos de cambio de tema cada 100 ms).
Verificado en el sandbox midiendo la barra de menús, el título y la toolbar de
Dolphin en 0 → 1 → 0,5 → 0 → 0 → 1.

**`goldenglass-glass --menubar-background on|off`** solo guarda `goldenglassrc
[Plasma] MenubarBackground` con aviso de cambio (de fábrica, token
`plasma.menubar_background = false`); no toca el Plasma Style. El `Panel.qml`
del shell lo lee en vivo (ver «Barra de menús» en 4.5).

#### Módulo de Ajustes

`kcm/` (`kcm_goldenglass`, C++ + QML): Preferencias del Sistema › Colores y
temas › **Vidrio**. Control con las tres muescas de los tokens (imán al soltar
cerca) y valores intermedios; se aplica en vivo al soltar ejecutando
`goldenglass-glass`; si se suelta varias veces, solo se encola el último nivel.
El interruptor «Mostrar fondo de la barra de menús» escribe `goldenglassrc`
directamente (con aviso de cambio, sin procesos). "Predeterminados" vuelve al
nivel y al fondo de fábrica; no hay "Aplicar". Traducción al
español en `po/es`. `kcm_apply_test` pide 1,0 → 0,0 → 0,25 seguidos y
comprueba que queda 0,25: en ctest con un `goldenglass-glass` de prueba
(`kcm/tests/bin`) y configuración temporal; a mano, dentro de una sesión Plasma.
Ese `goldenglass-glass` de prueba solo cambia `[Glass] Level`, como
`kwriteconfig6`, sin borrar otros grupos de `goldenglassrc`
(`goldenglass_glass_stub_test`).

#### Accesibilidad (F12/F13)

Contrato común de «Mostrar bordes», «Reducir transparencia» y «Reducir
movimiento» (detalle en [MACOS27-PLAN.md](MACOS27-PLAN.md) §3.1, §4.4, §4.5 y
§4.7). **«Reducir movimiento»** (interruptor en el módulo «Vidrio»,
`goldenglass-windows` y `Motion.qml`) y **«Reducir transparencia»** (ver abajo)
y **«Mostrar bordes»** (ver abajo) ya funcionan; de «Mostrar bordes» falta la
fase 2 en GTK.

| Clave en `goldenglassrc [Accessibility]` (bool) | Token de fábrica | La escribe |
|---|---|---|
| `ShowBorders` | `accessibility.show_borders = false` | `goldenglass-glass --show-borders on\|off` ✅ (F12; GTK pendiente de SP-02) |
| `ReduceTransparency` | `accessibility.reduce_transparency = false` | `goldenglass-glass --reduce-transparency on\|off` ✅ (F12) |
| `ReduceMotion` | `accessibility.reduce_motion = false` | `goldenglass-windows --reduce-motion on\|off` ✅ (efectos de KWin: «Efectos de ventana» en 4.5; plasmoids: «Movimiento») |

- **Escritura:** siempre con aviso de cambio (`KConfig::Notify`, `kwriteconfig6
  --notify`) y solo la clave propia, sin reescribir el archivo. El módulo
  «Vidrio» llamará a cada herramienta según la clave.
- **Tokens:** `[accessibility]` también trae `reduce_transparency_alpha = 1.0`,
  la opacidad del vidrio con «Reducir transparencia», y `[accessibility.borders]`
  los valores de «Mostrar bordes» (`surface_alpha`, `field_alpha`,
  `edge_shade`, `window_outline_contrast`, `window_shadow_outline_alpha`,
  `control_alpha`, `toolbar_button_alpha` y `gtk_alpha`, este para la fase 2).
  `gen_tokens.py` exige los tres interruptores booleanos y los alfas y mezclas
  en [0, 1].
- **C++:** `goldenglass_tokens.h` exporta `AccessibilityShowBorders`,
  `AccessibilityReduceTransparency`, `AccessibilityReduceMotion`,
  `AccessibilityReduceTransparencyAlpha` y los `AccessibilityBorders*` que leen
  el efecto, la decoración y el estilo. `kstyle/goldenglass.kcfg` y
  `kdecoration/goldenglasssettingsdata.kcfg` (los dos sobre `goldenglassrc`)
  tienen el grupo `Accessibility` con esos valores de fábrica:
  `StyleConfigData::showBorders()` y `InternalSettings::showBorders()`, etc.
  Guardar sus diálogos no escribe estas claves si no cambian.
- **QML:** un solo tipo, `AccessibilitySettings` (módulo
  `org.goldenglass.glass`, `qmlplugin/`), con `showBorders`,
  `reduceTransparency` y `reduceMotion` (solo lectura, con NOTIFY). Como
  `MenuBarSettings`, sigue el archivo con `KConfigWatcher` filtrado por el
  grupo `Accessibility`. Pruebas: `accessibilitysettings_test` y
  `accessibilitysettings_watch_test` (D-Bus).
- **QML de los plasmoids:** el singleton `Accessibility.qml` (compartido con
  `Motion.qml` por `SHARED`) es el único lector por plasmoide: carga con un
  `Loader` `AccessibilityReader.qml` (un `AccessibilitySettings`; sin el
  módulo, todo queda en `false`) y expone `reduceMotion`, `reduceTransparency`
  y `showBorders`. `Motion.reduced` sale de ahí.
- **«Reducir transparencia»:** conserva `[Glass] Level` y aplica un nivel
  efectivo opaco:
  - `goldenglass-glass`: `STYLE_KEYS` a `reduce_transparency_alpha` (100 %:
    estilo y decoración opacos sin cambiar su código) y `GoldenGlassTuned`
    con `translucent/` a ese alfa y, en su `plasmarc`, `[BlurBehindEffect]` y
    `[ContrastEffect]` con `enabled=false`;
  - efecto `goldenglass_glass`: lee la clave en `reconfigure` y pone a 0 la
    lente, la claridad, el filo y el oscurecido, y no difumina ninguna
    superficie de Plasma (spike SP-03, abajo); no toca `kwinrc [Plugins]`;
  - plasmoids: las tarjetas del Centro de control (`Tile.qml`) y el panel de
    Apps usan `reduce_transparency_alpha`, y el slider de vidrio del Centro
    de control queda deshabilitado; todo en vivo.
- **«Mostrar bordes»:** un borde fino de color de texto que separa el vidrio,
  las ventanas y los controles de lo que hay detrás. Todas las capas leen
  `ShowBorders`:

  | Capa | Cambio | Cómo se entera |
  |---|---|---|
  | Plasma Style | `build(..., borders=True)`: la línea exterior del filo del vidrio pasa de negra a `ColorScheme-Text` con `surface_alpha` (la interior blanca se queda) y el filo de los campos (`lineedit.svg`) usa `field_alpha`. Se combina con cualquier nivel y con «Reducir transparencia», que solo cambian el relleno; el tema del paquete solo sirve sin bordes | `goldenglass-glass` regenera `GoldenGlassTuned` |
  | Efecto `goldenglass_glass` | oscurecido de la banda exterior `edge_shade` y filo sin atenuar por el nivel (`rimFactor = 1`). Con «Reducir transparencia» el efecto sigue sin dibujar nada sobre Plasma: casi ninguna superficie pide ya blur y el contorno lo pone el Plasma Style sobre el vidrio opaco | `reconfigureEffect goldenglass_glass` |
  | Decoración | contorno de la ventana con `OutlineEnabled` **o** `ShowBorders`; color `mix(Frame, Text, window_outline_contrast)` y contorno de la sombra con `window_shadow_outline_alpha`. `ShowBorders` forma parte de la clave de la caché de sombras | `KWin.reconfigure` |
  | Estilo de apps | filo de 1 px de color de texto con `control_alpha` en `renderButtonFrame` y `renderLineEdit`; los botones planos de las toolbars (también los de Qt Quick, sin widget) muestran su forma sin el ratón encima con `toolbar_button_alpha`; las cápsulas y el buscador del Finder usan el color de texto con `control_alpha` | señal D-Bus `reparseConfiguration` → `StyleConfigData::load()` |
  | GTK (fase 2) | bloque CSS de usuario con `gtk_alpha` vía `gtk_sync` | **pendiente** del spike SP-02 |

  Las ventanas QML ya abiertas (p. ej. Preferencias del sistema) solo se
  repintan con el estilo nuevo cuando algo las invalida: el estilo repinta los
  widgets, no los elementos de qqc2-desktop-style. Los plasmoids no cambian:
  sus tarjetas ya llevan filo y macOS no documenta un cambio en ellas.
  Pruebas: matriz nivel × «Reducir transparencia» × «Mostrar bordes» de
  `apply()` y el cerrojo (pytest), el SVG con bordes (`test_plasma_theme.py`),
  `shadowparams_test` (clave de la sombra), `styleconfig_test` (relectura) y
  `kcm_apply_test`. `tools/preview_style.py --show-borders` muestra el estilo
  con bordes. Comprobado en el sandbox, en claro y en oscuro, con y sin
  «Reducir transparencia»: Spotlight lleva el filo de color de texto en los
  niveles 0, 0,5 y 1 y con el vidrio opaco; Dolphin (cápsulas y contorno) y
  Preferencias del sistema (botones y toolbar QML) lo muestran al abrirse.
- **Spike SP-03** (libplasma 6.8.1, sandbox con el efecto instrumentado para
  listar qué ventanas piden blur): con `[BlurBehindEffect] enabled=false` en
  el `plasmarc` del tema, el dock y la barra (PanelView) dejan de pedir blur
  al momento, y KRunner tampoco lo pide; libplasma 6.8.1 lo respeta. Lo que
  pide el blur por su cuenta (`GlassRegion`, `KWindowEffects` directo: panel de
  Apps y Centro de control) lo sigue pidiendo. **No-go parcial → plan B:** el
  efecto descarta él mismo las superficies de Plasma con RT. Comprobado: con
  RT, 0 superficies difuminadas por fotograma (antes 2) y el panel de Apps, el
  dock y KRunner opacos; al quitarlo, todo vuelve. Los popups de plasmoids con
  fondo estándar (Dialog) no se pudieron abrir en el sandbox sin simular
  entrada; usan el mismo `Theme::blurBehindEnabled()` de libplasma.
- **Módulo «Vidrio»:** bloque «Accesibilidad» bajo «Barra de menús», con los
  interruptores «Reducir transparencia» (propiedad `reduceTransparency`),
  «Mostrar bordes» (`showBorders`) y «Reducir movimiento» (propiedad
  `reduceMotion` de `GlassKcm`). Con
  «Reducir transparencia», el slider y «Refracción» quedan deshabilitados con
  la nota «Desactivado por Reducir transparencia». El nivel y «Reducir
  transparencia» y «Mostrar bordes» van por el mismo `goldenglass-glass`: las
  peticiones se encolan por tipo (`GlassRequest` `Level`, `ReduceTransparency`
  y `Borders`), un proceso a la vez y la última de cada tipo después; si
  falla, el interruptor vuelve a lo que diga el archivo. `kcm_apply_test`
  pulsa «Reducir transparencia» tres veces con un nivel encima, y luego
  «Mostrar bordes» tres veces junto a «Reducir transparencia», y comprueba que
  quedan todos.
  Lee la clave y la cambia con `goldenglass-windows --reduce-motion` por
  `QProcess`: un proceso a la vez y, si se pulsa mientras tanto, el último
  valor después; si falla, el interruptor vuelve a lo que diga el archivo.
  Cuenta para «Predeterminados». `kcm_apply_test` lo pulsa tres veces (sí,
  no, sí) con un `goldenglass-windows` de prueba (`kcm/tests/bin`, que como el
  de `goldenglass-glass` solo cambia su clave: `kcm/tests/set_entry.sh`) y
  comprueba que acaba activado sin perder el nivel de vidrio.

#### Otros módulos de Ajustes

Como en macOS, cada ajuste vive donde el usuario lo busca: **módulos aparte**
(cada uno en `kcm/<nombre>/`, con su dominio de traducción) en vez de páginas
dentro de «Vidrio».

| Módulo | Dónde | Contenido | Fase |
|---|---|---|---|
| Vidrio (`kcm_goldenglass`) | Colores y temas | slider + interruptor **Refracción** (`goldenglass-glass --refraction`; apagado y explicado si KWin no cargó el efecto) + interruptor **Mostrar fondo de la barra de menús** + bloque **Accesibilidad** con «Reducir transparencia» y «Mostrar bordes» (`goldenglass-glass --reduce-transparency` / `--show-borders`) y «Reducir movimiento» (`goldenglass-windows --reduce-motion`) | ✅ |
| Efectos de sonido (`kcm_goldenglass_sounds`) | Multimedia | sonidos de GoldenGlass y sonido al iniciar sesión, con botón para escucharlos (`pw-play`); llama a `goldenglass-system` (4.9) | ✅ F7 |
| Arranque e inicio de sesión (`kcm_goldenglass_boot`) | Colores y temas, junto a «Pantalla de bienvenida» | Pantalla de arranque: del sistema, GoldenGlass o GoldenGlass gris, con miniaturas dibujadas con las piezas del tema y los avisos de `goldenglass-system`. Pantalla de inicio de sesión: interruptor según el gestor activo (con SDDM, el tema; con Plasma Login Manager, fondo y ajustes, con la explicación). Se aplica con «Aplicar»: pide la contraseña (una vez para los dos cambios) y, si cambia Plymouth, regenera el initramfs | ✅ F8 / F9 |
| Dock (`kcm_goldenglass_dock`) | Espacio de trabajo (como «Escritorio y Dock») | Tamaño, **ampliación** (activada de fábrica) y su tamaño, apps recientes. En vivo con `goldenglass-dock` | ✅ F10 |

### 4.5 Escritorio Plasma — `plasma/`
- **Plasma Style** `GoldenGlass`: lo genera `tools/plasma_theme.py` dibujando
  cada pieza de FrameSvg por código (esquinas, bordes, máscara de blur, sombra).
  Usa clases `ColorScheme-*`, así que **un solo Plasma Style sirve para claro y
  oscuro**; solo la opacidad queda fija en el SVG. Genera diálogos, panel (barra
  de menús y dock), tooltips, fondo de widgets, tareas del dock (punto bajo las
  apps abiertas), resaltado de listas, campos de texto, cabeceras de popups y
  menús de la app en la barra (`menubaritem`: margen de macOS entre títulos,
  `plasma.menubar_item_padding`, y acento al pasar o abrir uno). Lo
  que no genera se hereda de Breeze. `plasmarc` pide saturación extra detrás del
  blur ("vibrancy").
- **Global Themes** (`look-and-feel/`): `org.goldenglass.light.desktop` y
  `org.goldenglass.dark.desktop`. Incluyen:
  - Script de layout: **barra de menús** en cada pantalla (logo, nombre de la
    app, menú global, bandeja, Centro de control y reloj) + **dock** = panel nativo flotante centrado con el plasmoid
    `org.goldenglass.dock` (ver 4.13), **autoocultable** como en
    macOS («Ocultar y mostrar automáticamente», token `plasma.dock_hiding`): aparece al llevar el
    cursor al borde inferior y las ventanas maximizadas usan toda la pantalla.
    Plasma lo anima con el efecto *Sliding Popups* de KWin (entra decelerando y
    sale acelerando); el script fija sus tiempos en `kwinrc`
    (`plasma.slide_in_ms`/`slide_out_ms`, que también usan los popups de
    Plasma) porque KLookAndFeelManager ignora esa clave en `contents/defaults`.
    Límite: Plasma espera 500 ms fijos tras salir el cursor antes de ocultarlo.
  - Atajos de macOS (script de KWin `org.goldenglass.shortcuts`, en
    `plasma/kwin/scripts/`, que el layout activa en `kwinrc`): Ctrl+↑ Mission
    Control (vista general de KWin con los escritorios) y Ctrl+↓ App Exposé
    (ventanas de la app actual). Lanzan las acciones de KWin por kglobalaccel y
    se pueden cambiar en Preferencias › Atajos. Cambiar de escritorio sigue en
    Meta+Ctrl+←/→: Ctrl+←/→ es saltar palabra en Linux. KWin carga el script
    al reconfigurarse o en el siguiente inicio de sesión.
  - Organizar ventanas, como Fn+Ctrl+F/C de macOS Sequoia (mismo script):
    Meta+Ctrl+F llena la pantalla (`setMaximize(true, true)`: no alterna y deja
    la ventana si no es maximizable) y Meta+Ctrl+C la centra (acción nativa
    `Window Move Center`). Volver al tamaño anterior es el nativo
    `Window Restore` en Meta+Retroceso, sin atajo propio: en KWin 6.8.1
    deshace maximizada, mosaico (mitades y cuartos) y pantalla completa. No se
    usa Meta+Ctrl+R (el equivalente de macOS) porque Spectacle 6.8.1 la trae
    por defecto para `RecordWindow`. Las mitades son las nativas Meta+←/→/↑/↓ y
    los cuartos se alcanzan encadenándolas (Meta+← y luego Meta+↑).
    Meta+Ctrl+F y Meta+Ctrl+C no tienen otro dueño por defecto. Un atajo que el
    usuario ya reasignó no se pisa: kglobalaccel conserva lo guardado en
    `kglobalshortcutsrc` y usa la tecla del script solo si el atajo no existe
    todavía.
  - Escritorios independientes por pantalla, como «Las pantallas tienen
    espacios independientes» de macOS (`plasma.per_screen_desktops`): el layout
    activa `[Windows] PerOutputVirtualDesktops` de KWin (Plasma ≥ 6.7) y
    desactiva el script «Virtual Desktops Only on Primary», que choca con ello.
  - Splash de inicio (logo + barra de progreso).
  - Fuentes, esquema de color, Plasma Style, estilo de apps `GoldenGlass` y
    decoración `org.goldenglass.decoration` (requieren el paquete
    `goldenglass-kstyle`; sin él Plasma usa Breeze).
  - Botones de ventana a la izquierda (`ButtonsOnLeft=XIA`) en
    `contents/layouts/defaults`: KLookAndFeelManager solo lee de ahí los ajustes
    de disposición de KWin, no de `contents/defaults`.
  - `ShellPackage=org.goldenglass.desktop` (ver pantalla de bloqueo).
  - Iconos, cursores y wallpaper se añaden en F5.
- **Barra de menús** como la de macOS 27. El `Panel.qml` del shell la reconoce
  como el panel superior que lleva el menú del logo
  (`org.goldenglass.systemmenu`); los demás paneles no cambian.
  - Sin fondo ni blur (`NoBackground`): el texto va sobre el fondo de pantalla.
    Fondo de vidrio translúcido opcional (4.4). El ajuste y los tokens llegan
    por `MenuBarSettings` del módulo QML `org.goldenglass.glass`
    (`qmlplugin/`): lee `goldenglassrc [Plasma] MenubarBackground` y lo sigue
    con `KConfigWatcher`, sin depender del Plasma Style activo. El módulo viene
    con `goldenglass-kstyle`: `Panel.qml` lo carga con un `Loader`
    (`GoldenGlassMenuBarSettings.qml`) y, si falta, la barra queda sin fondo y
    sin atenuar.
  - Con varias pantallas, la barra de las que no tienen la ventana activa se
    atenúa (`plasma.menubar_inactive_opacity` sobre la contención); sin ventana
    activa no se atenúa ninguna. Los dos `TasksModel` que lo deciden solo
    existen en la barra de menús y con más de una pantalla.
  - El nombre de la app es el de la última ventana visible de esa pantalla; el
    menú global (`allScreens=false`) solo enseña los menús de la ventana activa
    en su pantalla: en las demás queda el nombre, atenuado, sin menús.
  - Bandeja con los iconos separados como en macOS (`iconSpacing` a partir de
    `plasma.menubar_tray_spacing`).
  - Límites: el applet de menú global de Plasma añade al final un menú
    «Buscar» que no se puede quitar desde su configuración; la bandeja muestra
    su flecha de iconos ocultos (`arrow-down-symbolic`) cuando hay alguno.
- **Pantalla de bloqueo** estilo macOS (reloj grande arriba, avatar y contraseña
  abajo). Desde Plasma 6 vive en el **paquete de shell**, no en el Global Theme:
  - `plasma/shell/org.goldenglass.desktop` solo trae `lockscreen/` y hereda el
    resto de `org.kde.plasma.desktop` (`X-Plasma-FallbackPackage`).
  - `lockscreen/` es la de plasma-desktop 6.8.1 con cambios mínimos (ver
    `UPSTREAM.md`).
  - Efecto: plasmashell guarda el layout en
    `plasma-org.goldenglass.desktop-appletsrc`. El layout previo del usuario no se
    toca y vuelve si regresa a Breeze. Por eso el Global Theme trae el layout con
    los dos nombres (`org.kde.plasma.desktop-layout.js` y
    `org.goldenglass.desktop-layout.js`).
  - El shell y los botones solo se aplican con "Disposición del escritorio y
    ventanas" (`plasma-apply-lookandfeel --resetLayout`).
- **Spotlight:** KRunner flotante y centrado (`krunnerrc FreeFloating=true`,
  escrito por el script de layout), estilizado por el Plasma Style.
- **Plasmoids propios** (`plasmoids/`):
  - `org.goldenglass.controlcenter` ✅ — en la barra, junto al reloj. Cuadrícula
    de 4 columnas como la de macOS 26 (medidas en `[control_center]`), cada
    control en su tarjeta de vidrio:
    - Píldoras (círculo que conmuta; el texto abre sus ajustes): Wi‑Fi (con el
      nombre de la red), Bluetooth, KDE Connect en el hueco de AirDrop (se carga
      aparte: sin `kdeconnect` no aparece y Enfoque ocupa su sitio) y Enfoque
      (No molestar).
    - Reproducción (MPRIS) de 2 × 2, siempre visible («Sin reproducción»).
    - Botones redondos: Duplicar pantalla (selector de pantallas de KScreen, el
      de Meta+P), Captura (Spectacle), Modo oscuro (`DarkModeControl` de Plasma;
      el layout fija `DefaultLight/DarkLookAndFeel` a los temas GoldenGlass) y
      Luz nocturna, que la enciende o apaga de verdad (`kwinrc [NightColor]
      Active`) como Night Shift, no solo la suspende.
    - **Tarjetas sueltas de vidrio, como macOS 26** (único modo): el popup
      de Plasma (`AppletPopup`) no deja quitar su fondo, así que el icono de la
      barra es la representación «completa» (como Apps: Plasma no abre popup)
      y abre su propia ventana (`FloatingPanel.qml`): un `PlasmaCore.Dialog`
      sin fondo que cubre la pantalla, transparente, con las tarjetas pegadas
      al borde derecho bajo la barra y el icono resaltado mientras está
      abierta. Un clic fuera de las tarjetas la cierra, también en la barra de
      menús (que no toma el foco: perderlo no bastaría); y también Esc, el
      atajo del plasmoide o el foco en otra pantalla. Sin fondo, Dialog no pide
      blur: lo pide `GlassRegion`, del módulo QML `org.goldenglass.glass`
      (`qmlplugin/`, C++, en `goldenglass-kstyle`), con la forma de cada
      tarjeta (`goldenGlassTile`), y el efecto `goldenglass_glass` dibuja cada
      una como un vidrio (4.14). Las tarjetas son más claras que los popups
      (`tile_alpha`, sin seguir el nivel de vidrio). Sin el módulo
      (`GlassBlur.qml`, el de Apps copiado por `SHARED`, va en un Loader) se ven
      sin difuminar.
    - **Animaciones de Liquid Glass** (tiempos y escalas en
      `[control_center]`): al abrir, el vidrio brota del icono de la barra con
      un resorte (`Easing.OutBack`), más deprisa a lo alto que a lo ancho; al
      cerrar (también al perder el foco) se encoge hacia el icono y se
      desvanece, y el blur se quita a mitad (KWin no difumina a medias). Al
      pulsar una tarjeta cede, se ilumina desde el punto de contacto (degradado
      radial recortado a su forma) y vuelve con un rebote; la vista de detalle
      y la cuadrícula entran con el mismo resorte. GlassRegion sigue las
      escalas (esquinas elípticas si lo ancho y lo alto escalan distinto), así
      que el vidrio de KWin se mueve con las tarjetas; durante una animación
      manda a KWin como mucho una región cada `glass_update_ms`, y `active:
      false` quita el blur. Mientras se cierra, la ventana deja pasar los
      clics (`Qt.WindowTransparentForInput`); reabrirla a medio cierre sigue
      desde donde iba, con la cuadrícula. Necesita Qt 6.8 (`PathRectangle`).
    - **Vistas de detalle**, como en macOS 26: el texto de Wi‑Fi, Bluetooth y
      Enfoque, la tarjeta de Reproducción y las de Pantalla y Sonido (fuera de
      los sliders; también el botón de salida) cambian la cuadrícula por una
      tarjeta con título (e interruptor), lista y «Ajustes de…»: redes
      conocidas y otras (conectar, desconectar, contraseña en la fila; la
      lógica del applet de redes de Plasma), dispositivos Bluetooth
      emparejados, No molestar durante 1 hora o hasta mañana, brillo de cada
      pantalla con modo oscuro, luz nocturna y duplicar pantalla, volumen y
      salidas de sonido, y el reproductor con progreso. Esc vuelve a la
      cuadrícula; al cerrar y abrir, vuelve también.
    - A lo ancho, sliders sin tirador: Pantalla (un slider por pantalla con
      control, p. ej. DDC/CI, en la misma tarjeta), sonido con silencio y
      salida, y vidrio (`goldenglass-glass`).
    - Encendido: círculo blanco con el glifo en acento (en tema claro, círculo
      de acento con glifo blanco).
    Usa los módulos QML de Plasma (privados: se revisan en cada actualización de
    Plasma) y D‑Bus (`org.kde.plasma.workspace.dbus`) para KWin y KScreen.
  - `org.goldenglass.launchpad` ✅ **Apps** — primer elemento del dock, como
    Apps de macOS 27 (que sustituyó a Launchpad y vive en Spotlight): una pieza
    de vidrio centrada en la pantalla del dock, con esquinas amplias y sombra
    propia (`RectangularShadow`). Es un `PlasmaCore.Dialog` sin fondo: el vidrio
    lo dibuja el panel con la opacidad del nivel de vidrio (`goldenglassrc`) y
    `GlassRegion` pide a KWin el blur solo detrás de él, como el Centro de
    control. Cabecera de buscador sin caja («Búsqueda en Spotlight», glifo de
    Apps y «⋯» con cuadrícula o lista, que se recuerda en la configuración del
    plasmoid), etiquetas de categoría como rectángulos redondeados que llegan
    hasta el borde (filtran; otra pulsación quita el filtro), una fila de
    recientes (`RecentUsageModel`), una línea fina y todas las apps de la A a la
    Z, sin títulos de sección. Desplazamiento como el de macOS
    (`GlassScrollView.qml`, tokens `[scroll]`): barra superpuesta que solo
    aparece al desplazarse, rueda del ratón animada, touchpad con inercia
    (`Flickable.flick`; el ratón no arrastra el contenido para poder arrastrar
    apps), rebote elástico con la fórmula de UIScrollView y las apps
    difuminándose al pasar bajo las etiquetas (máscara de alfa con
    `MultiEffect`). Al abrir crece desde el centro con un resorte suave y
    aparece; al cerrar se encoge y se desvanece. Las categorías del
    menú de KDE (`RootModel`, identificadas por su icono) se agrupan en las 8
    de macOS (`categories.js`).
    Teclado: flechas y Return (la selección solo se ve al usar el teclado o al
    buscar), Tab entre etiquetas, Escape borra y luego cierra; si lo escrito
    no es una app, «Buscar en Spotlight» pasa la consulta a KRunner. Medidas en `[apps]` de los tokens (`contents/ui/tokens.js`, que
    `tools/plasmoids.py` genera en cada plasmoid). Las acciones de Kicker
    (`actionList`) se leen solo al abrir el menú contextual: leerlas al cargar
    tumba plasmashell. Las apps se arrastran como en Kickoff (`DragHandler` +
    `Drag.Automatic` en un elemento aparte, con el `.desktop` en
    `text/uri-list`, solo Copy/Link): al dock, al escritorio o a Dolphin.
    Los menús (contextual y «⋯») son QMenu
    (`PlasmaExtras.Menu`), como los de Kickoff: un `Menu` de Qt Quick quedaba
    recortado dentro del panel y, como ventana propia (`Popup.Window`), sin
    blur de KWin detrás; el QMenu lo dibuja el kstyle, que sí lo pide. Lo
    mismo en los menús de la papelera y del dock. El icono del dock es `goldenglass-apps` del tema de iconos (claro u oscuro),
    con `view-app-grid` de respaldo. Se declara `org.kde.plasma.launchermenu`: Meta lo abre.
  - `org.goldenglass.trash` ✅ — papelera del dock como la de macOS: icono a
    color del tema (`user-trash`/`user-trash-full` según haya archivos en
    `~/.local/share/Trash/files`, que crea si falta: `FolderListModel` lista el
    directorio actual si la carpeta no existe), clic abre `trash:/`, soltar
    archivos los tira con `gio trash` y el menú «Vaciar papelera…» pide
    confirmación (`kdialog`) antes de `ktrash6 --empty`.
  - `org.goldenglass.appname` ✅ — nombre de la app en negrita entre el logo y
    el menú global: la última ventana activada en esa pantalla, escritorio y
    actividad, sin las minimizadas (`TasksModel` con `SortLastActivated`; tras
    «Ocultar» pasa a la de delante), sin coletillas del `.desktop`
    («Spotify (Launcher)» → «Spotify»). Al pulsarlo: Ocultar <app>, Ocultar
    otros, Mostrar todo y Salir de <app> (minimiza, restaura o cierra sus
    ventanas). Mismo margen lateral que los menús (`plasma.menubar_item_padding`).
  - `org.goldenglass.clock` ✅ — reloj de la barra de menús: «Vie 16 de oct
    1:09 p.m.» (día con mayúscula, orden de fecha de macOS por idioma, dos
    espacios y la hora corta del idioma, que en es_MX trae «p.m.»). El reloj
    digital de Plasma no puede: escribe el día en minúscula y convierte «p.m.»
    en «P.M.». Se actualiza al cambiar el minuto; al pulsarlo, un calendario
    (`MonthView` de Plasma).
  - `org.goldenglass.systemmenu` ✅ — menú del logo como el menú Apple: Acerca de
    este equipo (kinfocenter), Preferencias del Sistema, Tienda (solo si está
    Discover), Forzar salida (KWin `killWindow`), Reposo, Reiniciar…, Apagar…,
    Bloquear pantalla, Cerrar sesión de <usuario>… (las tres con "…" piden
    confirmación). Atajo Alt+F1.
  - Los plasmoids viven en `plasma/plasmoids/<id>/` con sus traducciones en
    `po/<idioma>.po`; `tools/plasmoids.py` los copia a `build/` y compila las
    traducciones dentro del paquete (`contents/locale`).
- **Modo automático:** se apoya en el cambio día/noche nativo de Plasma entre los
  dos Global Themes. Los wallpapers usan `images_dark/` para cambiar solos.

#### Pruebas del módulo QML — `qmlplugin/tests/`

Infraestructura común de las pruebas C++ de `qmlplugin/` (ctest, con
`BUILD_TESTING`). `GOLDENGLASS_QMLPLUGIN_SOURCES` se compila una vez como
biblioteca estática (`goldenglass_qmlplugin_core`) que enlazan todas las
pruebas, sin cambiar lo que instala el plugin.
`goldenglass_add_qmlplugin_test(nombre [SOURCES ...] [LIBS ...] [DBUS])` crea
el ejecutable, lo registra con `QT_QPA_PLATFORM=offscreen` y, con `DBUS`, lo
ejecuta bajo `dbus-run-session` (un bus de sesión propio y descartable, con
`GOLDENGLASS_TEST_BUS=1`). `testbus.h` aporta:

- `GOLDENGLASS_TEST_MAIN(Clase)`, que sustituye a `QTEST_MAIN` y es
  obligatorio: manda HOME y los XDG_* a un directorio temporal y activa
  `QStandardPaths::setTestModeEnabled`, así que ninguna prueba toca la
  configuración real;
- `GG_REQUIRE_SESSION_BUS()`: `QSKIP` si no hay bus propio (sin
  `dbus-run-session`, o ejecutando el binario a mano); ctest lo marca como
  «Skipped». Nunca se usa el bus de la sesión del usuario: sin bus propio las
  pruebas corren con `DBUS_SESSION_BUS_ADDRESS=disabled:`;
- `FakeService` (servicio y objetos falsos en una conexión separada, para
  systemd1, osdService, krunner…), `call()` (llamada D-Bus que no bloquea el
  bucle de eventos) y `waitForSignal()`.

`check()` del PKGBUILD y la CI (`tools/ci.sh`) instalan `dbus` como
`checkdepends`; `ctest` no necesita envoltorio.

#### Movimiento — `Motion.qml`

Las animaciones de los plasmoids siguen la «Velocidad de animación» de
Ajustes del sistema (`kdeglobals [KDE] AnimationDurationFactor`). Los `*_ms` de
animación de `[apps]`, `[scroll]`, `[dock]` y `[control_center]` son duraciones
a factor 1 y pasan por el singleton `Motion` (`org.goldenglass.launchpad/
contents/ui/Motion.qml` y su `qmldir`, que `tools/plasmoids.py` copia por
`SHARED` al dock y al Centro de control, uniéndolo al `qmldir` que ya tengan):

- `factor` = `Kirigami.Units.longDuration ÷ motion.kirigami_long_ms` (200);
  `animated` = `longDuration > 1`.
- `ms(base)`: fundidos, colores, rueda, barra de desplazamiento y ampliación
  del dock (`base × factor`, 0 sin animaciones).
- `moveMs(base)`: escalas, desplazamientos y resortes (paneles, tarjetas,
  rebote elástico, rebote del dock, hueco al arrastrar).
- `fadeMs(base)`: el fundido de una transición que también se mueve (abrir y
  cerrar paneles).
- `overshoot(v)`: el rebote de `Easing.OutBack`.
- `reduced` («Reducir movimiento»): la clave `ReduceMotion`, en vivo, del
  singleton `Accessibility.qml`, que carga `AccessibilityReader.qml` (un
  `AccessibilitySettings` del módulo `org.goldenglass.glass`) con un
  `Loader`: sin `goldenglass-kstyle` falla solo ese archivo y `reduced` vale
  `false`. `SHARED` los copia junto a `Motion.qml`. Con `reduced`, `moveMs` y
  `overshoot` dan 0 y `fadeMs` da `ms(motion.reduced_fade_ms)`: los paneles
  solo se funden, los iconos del dock no rebotan (el rebote no arranca con
  tramos de menos de 1 ms) y `GlassScrollView` se detiene en los extremos
  (`StopAtBounds`, y la rueda del touchpad no estira) en vez del rebote
  elástico.

No se escalan las esperas que no son animaciones (`label_delay_ms`,
`preview_hide_ms`, `bar_hide_ms`, `glass_update_ms`, `interval:` de los
Timer). Con factor 1 las duraciones son las de los tokens, sin cambios. El
rebote del dock no arranca si un tramo dura menos de 1 ms. `tools/tests/
test_motion.py` falla si un `duration:` o un `easing.overshoot` de los
plasmoids usa un token sin pasar por `Motion`, y comprueba en ejecución
(offscreen, `kdeglobals` temporal; se salta sin `qml6` o sin el plugin de
plataforma de Kirigami) `Motion.ms(100)` con factor 0, 0,25, 1 y 2; con un
`AccessibilityReader.qml` que da `reduceMotion: true`, `moveMs` 0, `fadeMs` 150 y
sin rebote; sin el módulo, `reduced` false; y, si `build/cmake` tiene el
módulo compilado, que `reduced` sigue a un `goldenglassrc` temporal.

**Spike SP-04** (Plasma 6.8.1, Qt 6.12, Kirigami 6.31; `qml6` offscreen con
`QT_QUICK_CONTROLS_STYLE=Plasma`, que carga `KirigamiPlasmaStyle`, el mismo
plugin de plataforma que plasmashell):

| `AnimationDurationFactor` | `longDuration` | `shortDuration` | `veryLongDuration` | `Motion.factor` |
|---|---|---|---|---|
| sin clave / 1 | 200 | 100 | 400 | 1 |
| 0 (y negativos) | 1 | 0 | 2 | 0,005 (`animated` false) |
| 0,25 | 50 | 25 | 100 | 0,25 |
| 0,333 | 67 | 33 | 134 | 0,335 |
| 2 | 400 | 200 | 800 | 2 |

- `longDuration` = `max(1, round(200 × factor))`; `shortDuration` es la mitad
  sin el mínimo de 1 y `veryLongDuration` el doble. Una clave no numérica se
  ignora (200). Sin plugin de plataforma (estilo `Basic` o sin estilo), 200 fijo.
- **En vivo:** cambia al instante (señal `longDurationChanged` y los bindings
  que llaman a `Motion` se recalculan) cuando se reescribe `kdeglobals` con
  aviso (`kwriteconfig6 --notify`, como hace Ajustes del sistema; probado en un
  bus de D-Bus privado). Reescribir el archivo sin aviso no cambia nada.
- **Duración 0:** `NumberAnimation`, `ParallelAnimation` y
  `SequentialAnimation` (con `PauseAnimation` y `ScriptAction`) terminan dentro
  de `start()`/`restart()`: dejan los valores finales, ejecutan los
  `ScriptAction` y emiten `finished` antes de volver, así que el cierre de
  `FloatingPanel` y `AppsPanel` acaba igual. Un `Behavior` de 0 ms pone el
  valor final al momento. Reiniciar en `onFinished` una animación de 0 ms es
  una recursión síncrona (en la prueba, `RangeError: Maximum call stack size
  exceeded` tras ~1650 vueltas), no un bucle por fotograma: de ahí la guarda
  del rebote del dock. Con 1 ms la animación termina en el fotograma
  siguiente. No hizo falta el plan B (leer el factor en C++ ni forzar
  `visible = false`).
- **plasmashell resuelve el singleton por el `qmldir` de `contents/ui`:** en
  una sesión aislada (KWin virtual, plasmashell 6.8.1, bus D-Bus y HOME
  propios, el layout de `org.goldenglass.light.desktop`, factor 0,5) el dock y
  el Centro de control cargan y se ven, cada uno crea su `Motion`
  (`factor=0.5`, `longDuration=100`, `ms(100)=50`) y, al cambiar el factor a 2
  con aviso, los dos pasan en vivo a `ms(100)=200`. El registro no tiene
  errores de QML de los plasmoids GoldenGlass, igual que sin `Motion`.

#### Efectos de ventana — `goldenglass-windows`

`tools/windows.py` (`goldenglass-windows`, en `goldenglass-plasma`, con
autostart de fase 1) da a KWin los efectos de ventana de macOS y aplica
«Reducir movimiento» (plan de macOS 27 §4.6 y §4.7).

**`--check`** (al iniciar sesión): solo con un Global Theme
`org.goldenglass.*` y una vez por versión de la tabla (`goldenglassrc
[Windows] DefaultsVersion=1`). Escribe en `kwinrc` solo lo que el usuario dejó
vacío:

| Grupo | Clave | Valor | Condición |
|---|---|---|---|
| `Plugins` | `magiclampEnabled` / `squashEnabled` | `true` / `false` (genio al minimizar) | Las dos vacías |
| `Plugins` | `scaleEnabled` / `fadeEnabled` | `true` / `false` | Las dos vacías |
| `Effect-scale` | `InScale` / `OutScale` / `Duration` | `kwin.open_scale` 0,92 / `kwin.close_scale` 0,95 / `kwin.window_anim_ms` 220 (calibrar; KWin trae 0,8 y 200) | Cada una, si está vacía |
| `Effect-overview` | `BorderActivate` | `9` (sin esquina activa) | Vacía o `7` (arriba a la izquierda) |
| `Effect-windowview` | `BorderActivate`, `BorderActivateAll`, `BorderActivateClass` | `9` | Vacías o `7` |
| `ElectricBorders` | `TopLeft` | `None` | Vacía |
| `Plugins` | `org.goldenglass.shortcutsEnabled` | `true` | Vacía |

Lo escrito se aplica en vivo: `unloadEffect` de los efectos apagados y luego
`loadEffect` de los encendidos (dos efectos de una categoría exclusiva nunca a
la vez), `reconfigureEffect` de los grupos `Effect-*` y `/KWin reconfigure`
(que carga el script de atajos). El script de layout no cambia: sigue
aplicándose solo con `--resetLayout`.

**`--reduce-motion on|off`** escribe `goldenglassrc [Accessibility]
ReduceMotion` con aviso (los plasmoids lo siguen por `Motion`) y cambia los
efectos: `scale` → `fade`, `slide` → `fadedesktop` y, al minimizar, ninguno
(token `kwin.reduce_motion_minimize`: `none`, `squash` o `magiclamp`; se
apagan los demás efectos de minimizar). Lo que había antes (o que la clave no
existía) queda en `goldenglassrc [Windows] ReduceMotionSaved` (JSON, con lo
que se escribió); `off` lo devuelve salvo en las claves que el usuario cambió
mientras tanto, y un segundo `on` conserva el estado del primero. Para cargar
o descargar en vivo una clave borrada usa el `EnabledByDefault` de KWin 6.8.1
(`scale`, `slide` y `squash` sí; `fade`, `fadedesktop` y `magiclamp` no).
`--get-reduce-motion` imprime `on` u `off`.

- **Autónoma:** solo biblioteca estándar y sin `ggcommon` (que va en
  `goldenglass-kstyle`: compartirlo crearía un conflicto de archivos o una
  dependencia nueva entre paquetes), así que tiene su propio `kread`,
  `kwrite` y `effects_call`, como las herramientas de iconos. Los tokens salen
  del TOML del repositorio o, instalada, de `/usr/share/goldenglass/windows.json`
  (`[kwin]` y `accessibility.reduce_motion`), que escribe `gen_tokens.py` en
  `build/kwin/`. `gen_tokens.py` valida `[kwin]`.
- **Pruebas** (`tools/tests/test_windows.py`, configuración en memoria y
  llamadas de D-Bus solo registradas): instalación limpia, claves tocadas que
  no se pisan, 7 → 9, segunda ejecución sin cambios, otro Global Theme sin
  cambios, Reducir movimiento (activar, restaurar, cambios del usuario
  mientras tanto, dos `on`) y una actualización sobre un `kwinrc` previo con
  `kreadconfig6`/`kwriteconfig6` reales en un `XDG_CONFIG_HOME` temporal y
  D-Bus desactivado.

**Spikes SP-05 y SP-06** (sandbox: KWin 6.8.1 virtual 1600×1000, plasmashell
6.8.1, layout de `org.goldenglass.light.desktop`, `AnimationDurationFactor=10`
para capturar fotogramas a mitad de animación; minimizado con
`invokeShortcut "Window Minimize"` y geometrías leídas con un script de KWin):

- **El autostart llega a tiempo — go.** Tras arrancar KWin, `--check` cargó
  `magiclamp` y descargó `squash` en vivo (`isEffectLoaded`), escribió la
  tabla y cargó el script `org.goldenglass.shortcuts` (antes, no cargado); una
  segunda ejecución no cambió `kwinrc`. `--reduce-motion on` dejó cargados
  `fade` y `fadedesktop` y descargó `scale`, `slide` y `magiclamp`; `off`
  devolvió `kwinrc` byte a byte y los mismos efectos cargados. Sin reiniciar
  sesión.
- **El genio acaba en el icono — go, con un arreglo en el dock.** KWin apunta
  a la geometría que publica el dock (`iconGeometry` 875,938 48×48, el icono
  de la app). Con el dock visible, el `TasksModel` del dock tenía
  `filterHidden: true` y quitaba la app al minimizarse su única ventana: el
  dock se encogía y el genio acababa en un hueco. Ahora `filterHidden: false`
  (como el Dock, la app minimizada conserva su icono) y el genio termina sobre
  él. Con el dock autoocultado el genio baja al borde inferior, a la x del
  icono, como en macOS; no hizo falta republicar la geometría al mostrarse
  (plan B). Con el dock ampliado no se probó (el sandbox no mueve el cursor).
- **`scale` con `goldenglass_glass` — go.** Con la refracción cargada (y el
  Blur no), abrir y cerrar con `scale` (0,92/0,95) no deja artefactos ni
  cambios en el vidrio del dock en los fotogramas capturados (unos 3 por
  segundo a velocidad ×10); un parpadeo de un solo fotograma a velocidad
  normal no se puede descartar con este método.

### 4.6 Tipografía — `fontconfig/`
- SF Pro **no se redistribuye** (licencia de Apple).
- Alias de fontconfig `GoldenGlass Sans` → SF Pro → SF Pro Text → Inter, y
  `GoldenGlass Mono` → SF Mono → JetBrains Mono → Hack.
- KDE se configura siempre con el alias. Si el usuario instala SF Pro por su
  cuenta se usa; si no, Inter.
- **⚠ A verificar en F0:** que Qt resuelva un alias sin familia real en el
  selector de fuentes de KDE. Plan B: el Global Theme escribe la familia concreta
  detectada al aplicarse.

### 4.7 Iconos, cursores y wallpapers
- **Iconos** (`tools/icons.py`), por bloques:
  - **Base ✅:** carpetas, lugares y dispositivos. Desde 32 px, carpetas de
    macOS 27 en el color de acento con el símbolo grabado; papelera y unidades a
    color. A 16/22/24 px solo el símbolo en acento (barra lateral estilo Finder,
    también en las listas de Dolphin); `*-symbolic` en el color del texto.
    Todo usa las clases `ColorScheme-Accent`/`-Text` con
    `FollowsColorScheme=true`, así que sigue al acento y al modo claro/oscuro.
    Dos temas: `GoldenGlass` (hereda WhiteSur → breeze) y `GoldenGlass-Dark`
    (mismas carpetas por enlace; hereda WhiteSur-dark → breeze-dark).
    WhiteSur (AUR) es dependencia opcional.
    Incluye las carpetas de color de Dolphin («Asignar color a carpeta») y
    `folder-new`.
  - **Tipos de archivo ✅** (`tools/icons_mime.py`): hoja blanca con esquina
    doblada, símbolo del tipo en su color y la extensión en gris (texto a
    trazos con la fuente del tema al generar). Categorías de shared-mime-info
    y ~80 tipos concretos; lo demás sale de WhiteSur.
  - **Ojo con los temas parciales:** dentro de cada tema KIconLoader recorta
    los nombres que no encuentra (`audio-volume-muted` → `audio`) y prueba
    `<tipo>-x-generic` antes de mirar los heredados. Por eso no se publican
    `text|image|audio|video|application-x-generic`, y las acciones `folder-*`
    importantes se dibujan (si no, acabarían en `folder`).
  - **Apps ✅** (`tools/icons_apps.py`): 35 apps de KDE, CachyOS, terminales
    y utilidades, en squircle de superelipse con sombra, brillo y filo de
    vidrio. Claro: fondo del color de la app y símbolo blanco; oscuro (tema
    `GoldenGlass-Dark`, carpeta `apps` propia): fondo grafito y símbolo en el
    color. No se dibujan marcas de terceros.
    Los colores, opacidades y sombras del squircle (fondos grafito y papel,
    brillo, filo, sombras del tile y del símbolo) están en `[icon_tile]` de los
    tokens, validada por `gen_tokens.py`. Las herramientas de iconos son
    autónomas (no importan `ggcommon`): `icons_apps.tile_tokens()` toma los
    tokens explícitos, si no el TOML del repositorio (desarrollo), si no el
    `icon-tile.json` que genera `icons.build()` y instala `goldenglass-icons` en
    `/usr/share/goldenglass/` (se busca en `XDG_DATA_DIRS/goldenglass/` y junto a
    `tools/`), y si no, falla con un mensaje claro. `tile()` y `App.svg()` reciben un `Style`
    (`tools/icons_style.py`, hoy solo `DEFAULT`) para los estilos Tintado y
    Transparente. `tools/tests/test_icon_tile.py` guarda el SHA-256 de cada SVG
    (`icon_tile_golden.py`, se regenera con `--update` cuando el cambio visual es
    a propósito) y comprueba que cada token cambia el dibujo.
  - **Protección de nombres:** al generar se crean en `<tema>/inherited/`
    enlaces al icono real (en WhiteSur, Breeze o hicolor) de cada nombre que
    el recorte llevaría a una de nuestras apps (`preferences-system-bluetooth`
    → `preferences-system`, `kdeconnect-tray` → `kdeconnect`…). Dependen de
    los temas instalados en la máquina que genera; si uno desaparece, el
    enlace roto no molesta.
  - **Apps de terceros ✅** (`tools/wrap_icons.py`, lo ejecuta `install.sh`):
    en el equipo del usuario, cada app visible sin icono propio se encierra
    en el squircle claro/oscuro a partir de su icono original (hicolor o
    pixmaps, no la versión de otro tema), como hace macOS 26/27. Si el
    original ya es un cuadrado lleno se recorta al squircle; si no, va al
    68 %. Sale a `~/.local/share/icons/GoldenGlass{,-Dark}/wrapped/`, carpeta
    que los temas declaran siempre (vale también con el tema en `/usr`).
    Volver a ejecutarlo al instalar apps; las apps con `Icon=` como ruta
    absoluta no se pueden sustituir desde un tema.
  - La papelera de Plasma pide `user-trash-symbolic` dentro de un panel; por
    eso el dock usa `org.goldenglass.trash` (ver plasmoids), con el icono a color.
- **Cursores** ✅ (`tools/cursors.py`, tema `GoldenGlass-cursors`): dibujados
  por código como los de macOS (flecha e I negras con borde blanco, manos
  blancas con borde negro, sombra suave, rueda de colores animada para
  «ocupado»/«trabajando»). Cada cursor se describe una vez en un lienzo 32×32
  (tamaño nominal 24) y de ahí salen los SVG de `cursors_scalable/` que usa
  KWin y los Xcursor de `cursors/` (XWayland), escritos en Python y
  rasterizados con QtSvg en 18–72. Los nombres CSS/X11/hash son enlaces;
  `Inherits=breeze_cursors` cubre lo que falte. El Global Theme lo activa
  (`[kcminputrc][Mouse] cursorTheme`). Requiere `python-pyqt6` al generar.
- **Wallpapers** ✅ (`tools/wallpaper.py`): cintas de vidrio sobre la bahía al
  atardecer (día) y de noche, generadas con numpy (sin imágenes en el repo) en
  5120×2880 y 3840×2400, con `images/` e `images_dark/` para que Plasma las
  cambie con el tema claro/oscuro. El Global Theme las pone de fondo y el Plasma
  Style las declara fondo por defecto (también para la pantalla de bloqueo).
  Requiere `python-numpy` y `python-pillow` al generar.
- **Acento:** azul macOS por defecto (`#007AFF` claro / `#0A84FF` oscuro),
  sobreescribible por el acento del sistema.

### 4.8 GTK ✅ — `tools/gtk.py`, `tools/gtk_sync.py`
- **Temas `GoldenGlass` y `GoldenGlass-Dark`** (GTK3 y GTK4 sin libadwaita):
  importan **adw-gtk3** (dependencia: `adw-gtk-theme`) y encima redefinen la
  paleta con la de los tokens, los radios de macOS y los semáforos de las
  ventanas con decoración propia (CSD).
- **libadwaita** no admite temas: `build/gtk/libadwaita.css` (variables CSS de
  libadwaita, claro y oscuro por `prefers-color-scheme`, el acento lo da el
  portal) se copia a `~/.config/gtk-4.0/gtk.css` solo si no existe o ya es
  nuestro (marca en la primera línea); si es de otra herramienta no se toca.
- **Semáforos sin foco.** En `:backdrop` son grises (`traffic_light_inactive`).
  GTK4/libadwaita: `windowcontrols:backdrop:hover > button.close|minimize|maximize`
  devuelve el color de cada uno y `windowcontrols:hover > button image` muestra
  los glifos de los tres al pasar por el grupo. GTK3 no tiene un nodo de grupo
  con hover propio (`headerbar:hover` abarcaría toda la barra), así que la
  reserva es `button.titlebutton.<clase>:backdrop:hover` por botón: límite
  documentado, solo el botón bajo el ratón se colorea.
- **`goldenglass-gtk-sync`** (autostart de la sesión): el Global Theme no puede
  fijar GTK, así que mientras sea GoldenGlass pone `GoldenGlass` o
  `GoldenGlass-Dark` según el esquema de KDE con la API de kde-gtk-config
  (`org.kde.GtkConfig.setGtkTheme`), y escucha la señal de KConfig de
  `kdeglobals` para cambiar en vivo. GTK3 en Wayland no sigue
  `gtk-application-prefer-dark-theme`, por eso hay dos temas. Al cambiar a
  otro Global Theme restaura el tema GTK anterior.

### 4.9 Integración con el sistema — `goldenglass-system` (F7–F9)
- Los paquetes de sonidos, Plymouth y login **solo instalan**: nada se activa
  al instalar ni con hooks de pacman. Se activa con
  `goldenglass-system enable|disable|status [--json] <parte…>`
  (`tools/system.py`, en `goldenglass-plasma`) o desde los módulos de Ajustes,
  que lo llaman. Partes: `sounds`, `chime`, `plymouth` y `login` ✅. `status --json` es lo que leen los módulos.
- Lo que es del usuario (sonidos, chime) se escribe en su `~/.config` sin root,
  con `kwriteconfig6 --notify`.
  Lo del sistema (Plymouth, login) necesita root: con `sudo` se hace en el
  sitio; sin él, el comando se vuelve a lanzar con **pkexec** sobre un ayudante
  fijo (`/usr/lib/goldenglass/system-helper`, que ejecuta `system.py` con
  `python3 -I`) y la acción de polkit `org.goldenglass.system`
  (`auth_admin`, solo para ese ayudante; polkit no recuerda la contraseña).
  Solo entonces se pide la contraseña. El módulo de Ajustes manda todos los
  cambios en una sola llamada (`goldenglass-system apply --plymouth … --login …`)
  para pedirla una vez. Como root, `umask 022` y escrituras atómicas sin seguir
  enlaces (`pkexec` conserva el umask de quien llama). Con root se rechazan las partes del usuario, para no escribir en
  la configuración de root. En desarrollo (sin el paquete) no hay ayudante: el
  comando pide `sudo`.
- **Reversible:** antes de cambiar algo se guarda el valor anterior
  (`/var/lib/goldenglass/` para el sistema, `~/.local/state/goldenglass/system.json`
  para el usuario; si la clave no existía se guarda como tal) y `disable` lo
  restaura. Un segundo `enable` no pisa lo guardado, y `disable` no toca una
  clave que el usuario haya cambiado después. `tools/install.sh --uninstall`
  desactiva las partes del usuario antes de borrar.
- No cambia de gestor de inicio de sesión, ni la línea de comandos del kernel,
  ni los `HOOKS` de mkinitcpio: si falta algo (p. ej. `splash` o el hook
  `plymouth`) lo avisa y no lo toca.

### 4.10 Sonidos — `tools/sounds.py` (F7)
- **Sintetizados por código** con numpy, como los fondos: sin binarios en el
  repo. Cada evento de `[sounds.events]` en los tokens es una lista de capas:
  notas de cristal (parciales casi armónicos con caída exponencial, glissando
  opcional) y ráfagas de ruido filtrado (sueltas, para el papel). Se mezclan,
  pasan por una cola de sala corta, distinta en cada canal, y se normalizan
  (`volume` × `gain`). Ogg Vorbis (`.oga`) con `python-soundfile` (solo al
  generar). Se cachea con el hash del generador y de `[sounds]`.
- Iterar el diseño: `python3 tools/sounds.py --play notification alert` (con
  `pw-play`) o `--preview DIR` (un `.wav` por evento).
- Tema freedesktop `GoldenGlass` (`build/sounds/GoldenGlass/`,
  `index.theme` + `stereo/`). El nombre principal de cada evento es un archivo y
  los demás son enlaces. Los eventos de macOS y los de Plasma que no deben
  perderse (temporizador, cargador, avisos, contraseña):

  | Evento | Nombres freedesktop |
  |---|---|
  | Alerta (también avisos de diálogos KDE) | `bell`, `bell-window-system`, `dialog-warning`, `dialog-error`, `dialog-error-critical`, `dialog-error-serious` |
  | Notificación | `message-new-instant`, `message-new-email` |
  | Vaciar papelera | `trash-empty` |
  | Captura de pantalla | `screen-capture`, `camera-shutter` |
  | Respuesta del volumen | `audio-volume-change` |
  | Conectar / desconectar | `device-added`, `device-removed` |
  | Batería baja | `battery-low`, `battery-caution` |
  | Enchufar el cargador | `power-plug` |
  | Alarma del temporizador | `alarm-clock-elapsed` |
  | Contraseña de administrador | `dialog-warning-auth` |
  | Chime | `desktop-login` |

- **El resto, en silencio**, como macOS (sin heredar Ocean): información y
  pregunta de los diálogos, desenchufar, cerrar sesión, completado, mensajes,
  llamadas… La especificación siempre recurre al tema `freedesktop` cuando a
  un tema le falta un sonido; un archivo vacío `<nombre>.disabled` corta esa
  búsqueda (verificado con libcanberra: «Sound disabled»). Se dejan sin tocar
  los de la prueba de altavoces (`audio-channel-*`, `audio-test-signal`).
- Activación (`goldenglass-system enable sounds`): `kdeglobals [Sounds]
  Theme=GoldenGlass` (lo leen KNotifications y plasma-pa) y, como Spectacle no
  suena al capturar, `spectacle.notifyrc [Event/newScreenshotSaved]
  Action=Popup|Sound`, `Sound=screen-capture`. El **chime** es aparte
  (`enable chime`): Plasma trae el evento de inicio de sesión
  (`plasma_workspace.notifyrc [Event/startkde]`, `desktop-login`) sin acción;
  se le pone `Action=Sound`.
- Paquete `goldenglass-sounds`.

### 4.11 Arranque — Plymouth (F8) ✅
- Dos temas: **`goldenglass`** (negro, logo blanco; el de fábrica) y
  **`goldenglass-light`** (gris claro, logo oscuro), como las dos variantes del
  arranque de Mac. Se elige con `goldenglass-system enable plymouth
  [--variant dark|light]` o en el módulo «Arranque e inicio de sesión».
- **Plugin `script`** de Plymouth (`plymouth/goldenglass.script.in`, plantilla
  que rellena `tools/plymouth.py` con `[boot]` de los tokens; colores y
  opacidades por variante en `[boot.dark]` y `[boot.light]`).
- Piezas dibujadas al generar, a 1x, 2x y 3x: logo
  (`assets/logo/goldenglass-symbolic.svg` recoloreado, con QtSvg), pista y
  relleno de la barra, campo de contraseña, punto e icono de Bloq Mayús (con
  QPainter). Las medidas de los tokens son para una pantalla de 1080 líneas:
  el script escala con la altura de la pantalla, elige el juego de piezas más
  cercano por encima y lo ajusta a la medida exacta.
- **Mismas proporciones y colores que el splash de Plasma** (logo de 126 px,
  barra de 216×6 a 54 px, desplazados 36 px hacia arriba; fondo, barra y pista
  de `[boot.dark]` o `[boot.light]` según el Global Theme), para que arranque →
  login → escritorio se vea continuo.
- **Barra de progreso fina** que sigue el progreso de arranque de Plymouth (lo
  estima con la duración de arranques anteriores) y se mueve con suavidad. El
  relleno es un recorte de la barra llena más su extremo redondeado aparte, así
  el extremo no se deforma al crecer (`Image.Crop`).
- **Contraseña de disco (LUKS)** estilo FileVault: campo de vidrio con un punto
  por carácter, el texto de la petición debajo e icono de Bloq Mayús. Las
  preguntas (`ask-question`) muestran lo escrito en el mismo campo. Los
  mensajes (fsck…) van abajo, centrados.
- **Apagar y reiniciar: solo el logo**, sin barra (Plymouth no sabe cuánto
  falta).
- **Fuente:** el hook `plymouth` de mkinitcpio mete en el initramfs el archivo
  que resuelve fontconfig para `Font=`. Se usa **Inter Variable** (0,9 MB): el
  alias `GoldenGlass Sans` da `Inter.ttc`, de 13 MB, que acabaría en cada
  initramfs (y en sus copias de la ESP y de los snapshots).
- Activación (root): `plymouth-set-default-theme -R <tema>`, que llama al
  `plymouth-update-initrd` de la distribución (en CachyOS con Limine,
  `limine-mkinitcpio`). El tema anterior se guarda una vez (cambiar de variante
  no lo pisa) y `disable` lo restaura (si no hay ninguno guardado, `--reset`).
  Si regenerar el initramfs falla, se vuelve a fijar el tema anterior sin
  regenerar: el initramfs sigue siendo el de antes. Avisa (no corrige) si
  falta `splash` en la línea de comandos del kernel o el hook `plymouth`.
- **Vista previa sin reiniciar ni root:** `tools/preview_plymouth.sh [tema]
  [ANCHOxALTO]` ejecuta Plymouth de verdad (renderer x11) en un contenedor
  podman sobre un Xvfb y deja capturas de arranque, contraseña, pregunta,
  mensaje y apagado en `build/plymouth-preview/`.
- **Límite:** con varias pantallas de distinto tamaño, Plymouth da al script
  la medida de la más pequeña: en las otras el conjunto no queda centrado.
- Paquete `goldenglass-plymouth`.

### 4.12 Inicio de sesión — SDDM y Plasma Login Manager (F9) ✅
- **Plasma Login Manager** (PLM, el sucesor de SDDM de KDE, el que usa CachyOS
  con Plasma 6.7) **no admite temas**: su interfaz va compilada en el binario
  (`qrc:/qt/qml/org/kde/plasma/login/Main.qml`). Por eso hay dos caminos.
- **SDDM: tema propio `GoldenGlass`** (`login/sddm/Main.qml`, QML Qt 6,
  `QtVersion=6`), con el **diseño de nuestra pantalla de bloqueo**: fecha y
  hora grandes arriba, fondo difuminado (`MultiEffect`) y un poco oscurecido,
  avatar redondo, nombre y contraseña abajo. Con varios usuarios, primero una
  fila de avatares (como macOS); al elegir uno, su contraseña y un botón para
  volver (también Escape). Reposo / Reiniciar / Apagar como botones de vidrio
  redondos con texto; sesión (abajo a la izquierda) y teclado (abajo a la
  derecha) solo si hay más de una. Contraseña en un campo de vidrio con la
  flecha para entrar dentro; aviso de Bloq Mayús; si falla, el campo tiembla y
  sale «Error de inicio de sesión».
  - Solo Qt Quick (sin módulos de Plasma ni temas de iconos: corre como el
    usuario `sddm`); iconos SVG propios en `login/sddm/icons/`.
  - Valores en `theme.conf`, que genera `tools/login.py` desde `[login]` de los
    tokens (medidas a 1080 líneas, escaladas con la altura), con la fuente
    `GoldenGlass Sans` y el fondo de GoldenGlass instalado (`images/` o
    `images_dark/`, 16:9 o 16:10 según la pantalla).
  - Textos de `SddmComponents` (`TextConstants`), que SDDM ya trae traducidos
    a todos sus idiomas. `login/sddm/translations/<idioma>.po` (compilado con
    `msgfmt --qt`) solo corrige lo que SDDM no traduce o cambia por el término
    de macOS (en español, «Suspend» → «Reposo»).
  - El avatar es el que da SDDM (`~/.face.icon`, `FacesDir`, AccountsService);
    su silueta genérica se sustituye por la nuestra de vidrio.
  - Con varias pantallas, la interfaz solo en la principal; las demás, fondo y
    reloj.
- **Claro/oscuro según la hora:** fondo de día o de noche (`day_start`,
  `night_start` en `[login]`); los controles son siempre vidrio oscuro con
  texto claro, como el login de macOS.
- **PLM: fondo y ajustes**, lo mismo que hace su módulo de KDE:
  - `/etc/plasmalogin.conf`: `[Greeter] WallpaperPluginId=org.kde.image` e
    `Image=file:///usr/share/wallpapers/GoldenGlass/` en
    `[Greeter][Wallpaper][org.kde.image][General]` (el greeter lo lee de
    `/usr`, no hace falta copiarlo).
  - «Aplicar ajustes de Plasma»: `kdeglobals`, `plasmarc`, `kcminputrc`,
    `kxkbrc` y `fontconfig/fonts.conf` del usuario que lo pide (`PKEXEC_UID` o
    `SUDO_UID`) a `/var/lib/plasmalogin/.config/`, y se vacía su `.cache`.
    Se lee **como ese usuario** y se escribe **como `plasmalogin`** (procesos
    hijo sin privilegios, `_as_user`): root no sigue enlaces del usuario ni
    escribe con privilegios en un home ajeno. Un archivo que el usuario no
    puede leer, que no es regular (FIFO, dispositivo) o que pasa de 1 MiB se
    omite con un aviso y el del greeter no se toca; las operaciones como otro
    usuario tienen un límite de tiempo.
  - El greeter lo ve todo el mundo: del `fonts.conf` se quitan los `<dir>`,
    `<include>` y `<cachedir>` que salgan del sistema (`/usr/share/fonts`,
    `/usr/local/share/fonts`, `/etc/fonts`) o del home del greeter (`~`,
    `prefix="xdg"`/`"relative"`), y si no es XML válido no se copia. La
    distribución de teclado (`kxkbrc`) sí pasa a todos, como en el módulo de KDE.
  - Se guardan una vez los valores y archivos previos; `disable` los
    restaura (si el administrador cambió el fondo después, el fondo no se toca).
- `goldenglass-system enable login` detecta el gestor activo
  (`/etc/systemd/system/display-manager.service`): con SDDM escribe
  `/etc/sddm.conf.d/99-goldenglass.conf` (tema y, si está instalado, el
  cursor de GoldenGlass; `99-` para ir después de `kde_settings.conf`), que
  `disable` borra. Avisa si `/etc/sddm.conf` fija el tema, porque manda sobre
  `sddm.conf.d`. Otro gestor: error claro. **Nunca cambia de gestor.**
- **Vista previa sin cerrar sesión ni root:** `tools/preview_login.sh
  [ANCHOxALTO]` ejecuta el greeter real (`sddm-greeter-qt6 --test-mode`) en un
  contenedor podman sobre un Xvfb, con usuarios de prueba (uno con foto) y la
  hora fijada con `TZ`. Deja en `build/login-preview/` día, noche, contraseña
  escrita, fila de usuarios y usuario elegido. En modo prueba SDDM dice que no
  se puede apagar: la copia de la vista previa muestra los botones igualmente.
- Paquete `goldenglass-login` (SDDM como dependencia opcional).

### 4.13 Dock con ampliación — `org.goldenglass.dock` (F10) ✅
- Antes el dock eran cuatro plasmoids en un panel (Apps, `icontasks`,
  separador, Papelera): un panel recorta su contenido a su grosor y cada
  plasmoid es independiente, así que la ampliación no podía cruzar de uno a
  otro. Ahora es **un solo plasmoid**, todo QML (sin C++):
  - Apps · apps fijadas y abiertas · [| recientes] · | · Papelera.
  - **Apps** usa `AppsLauncher.qml` (modelos de Kicker + panel) y la
    **Papelera** `TrashButton.qml`: salen de los plasmoids Apps y Papelera, y
    `tools/plasmoids.py` los copia al dock (`SHARED`) y une sus traducciones a
    las del dock. Los plasmoids sueltos siguen disponibles para otros paneles.
    El dock declara `org.kde.plasma.launchermenu`: Meta abre Apps.
  - Apps fijadas y abiertas: `TasksModel` de libtaskmanager (el de
    `icontasks`), agrupado por app, orden manual, todas las apps de todos los
    escritorios; las fijadas en la configuración del plasmoid (`launchers`).
- **Ampliación** (`DockView.qml`): cada icono crece según su distancia al
  cursor medida sobre la fila *sin ampliar* (así la posición del cursor no
  depende de la ampliación y no hay realimentación), con una curva de coseno
  que llega a 0 a `dock.spread` iconos; la fila se ensancha alrededor de su
  centro y entra y sale suavizada (`magnification_ms`). El plasmoid reserva el
  ancho máximo, así el panel no cambia de tamaño al ampliar.
- **Placa de vidrio y panel** (resultado del spike):
  - El fondo del panel lo dibuja `views/Panel.qml` del paquete de shell, y
    PanelView usa su `panelMask` como región de blur. El shell GoldenGlass
    trae su copia (ver `UPSTREAM.md`) con `goldenglassDockSlab`: el dock le
    pasa la geometría de la placa y el fondo, la máscara de blur y la sombra la
    siguen; el resto del panel queda transparente. La contención se queda en su
    sitio normal (si siguiera al fondo, el dock movería su placa en bucle).
  - El dock fija el grosor del panel (`goldenglassSetThickness`): placa (icono
    + `dock_padding`, con el punto de app abierta dentro del relleno) más el
    hueco para el icono más ampliado rebotando (al hacer clic está ampliado y
    salta desde ese tamaño: `máx × (1 + bounce)`). El layout pone el mismo valor
    al inicio (`_dock_height`).
  - **Límite aceptado (región de entrada):** PanelView toma como entrada todo
    el ancho de la ventana desde el borde superior de la placa. La parte de un
    icono ampliado por encima de la placa no recibe el ratón (al subir el
    cursor la ampliación se recoge y un clic ahí va a la ventana de detrás), y
    los márgenes reservados a los lados sí capturan clics a la altura de la
    placa mientras el dock está visible.
  - Con «Evitar ventanas» o siempre visible, el hueco de la ampliación también
    se reserva (las ventanas maximizadas quedan por encima); con la
    autoocultación de fábrica no se reserva nada.
- **Cada icono** (`DockIcon.qml`): punto debajo si la app está abierta;
  **rebote** al arrancar (sin parar mientras dura el aviso de arranque,
  `IsStartup`) y al pedir atención (`attention_bounces` veces); más oscuro al
  pulsar; nombre encima al pasar el ratón y, si tiene ventanas, **vistas
  previas** en vivo (`WindowPreviews.qml`: `ScreencastingRequest` +
  `PipeWireSourceItem`, como el gestor de tareas de Plasma; clic activa esa
  ventana). El contenido del tooltip solo existe mientras se ve: cada
  miniatura es un stream de PipeWire y KWin renderiza la ventana mientras dure.
  - El tooltip es un `PlasmaCore.Dialog` de tipo `Tooltip` y no
    `ToolTipArea`: en un panel, libplasma (`PopupPlasmaWindow`) coloca los
    tooltips sobre el borde de la *máscara* de la ventana, que en el dock es la
    placa, y taparían los iconos ampliados. `Dialog` (`popupPosition`) usa el
    rectángulo del elemento: se ancla a uno invisible cuyo borde superior es el
    del icono más ampliado (más un pequeño margen), con `location: Floating`
    para que el globo tenga los cuatro bordes. Se recoloca cuando la ampliación
    mueve el icono; con miniaturas espera un momento al salir para poder pasar
    el ratón al tooltip.
- **Clics:** izquierdo abre la app o trae su ventana más reciente (si ya está
  delante, la siguiente); central, nueva instancia; derecho, menú
  (`TaskMenu.qml`): acciones de la app (las del `.desktop`, de Kicker
  `SimpleFavoritesModel`, leídas al abrir el menú; solo
  `_kicker_jumpListAction`, sin recientes ni Editar/Desinstalar), Nueva ventana / Abrir,
  Mantener en el Dock, Salir. Arrastrar una app fijada la reordena; soltar
  archivos sobre una app los abre con ella. Publica la geometría de cada icono
  para la animación de minimizar de KWin.
- **Añadir apps:** arrastrar una app desde Apps (o un `.desktop` desde Dolphin)
  y soltarla en el dock. Mientras se arrastra, las apps se separan donde caerá
  (el icono anterior crece por la derecha, `trailingSpace`); el punto de corte
  se mide en la fila sin el hueco, como la ampliación. Al soltar se fija
  (`requestAddLauncher`, que pasa `file:///…/x.desktop` a `applications:`) y
  se mueve a ese sitio; si ya estaba (fijada o abierta) solo se fija y se
  mueve. Un `DropArea` de todo el dock, por debajo de los iconos: el de cada
  app deja pasar las apps (solo abre archivos) y la Papelera rechaza las que
  vienen de Apps (`application/x-goldenglass-app`), así no tira el `.desktop`.
  Cubre también los huecos: si llegara al panel, Plasma crearía un widget de
  icono. El plasmoid reserva el ancho del hueco aunque la ampliación esté
  apagada. En el menú de Apps, «Mantener en el Dock» (`pinApp`/`unpinApp`).
  Mientras Apps está abierto, el plasmoid está en `NeedsAttentionStatus`: el
  dock autoocultable aparece (también si Apps se abrió con Meta) y no se
  esconde, para poder soltar en él.
- **Recientes:** `RecentUsageModel` de Kicker, las `recent_count` más
  recientes que no están ya en el dock, tras un separador (como macOS).
- **Ajustes:** `goldenglass-dock` (`tools/dock.py`) escribe la configuración
  del plasmoid con el script de plasmashell (`iconSize`, `magnification`,
  `magnificationSize`, `showRecent`); el dock la aplica al momento y ajusta el
  grosor. Valores de fábrica en `[dock]` y `[plasma]` de los tokens (el
  `main.xml` del plasmoid es una plantilla). El módulo «Dock» lo llama. Un solo
  rango de tamaños (`[dock] icon_size_min/max`, `magnification_size_max`; la
  ampliación nunca por debajo del icono) en los deslizadores del módulo, en el
  `<min>`/`<max>` del `main.xml` y en `goldenglass-dock`, que lo lee del
  `main.xml` instalado.
- **Pruebas:** en el sandbox, el dock real con una app abierta y el panel de
  Apps abierto desde el dock (también que el dock oculto aparece al abrir Apps
  con `activateLauncherMenu` y se oculta al cerrarlo); `goldenglass-dock` y el
  ajuste de grosor. El
  KWin virtual no tiene entrada: la ampliación con el ratón, el menú, las
  vistas previas, el arrastre y el rebote se prueban en una sesión real.
- **Pendiente de revisar en sesión real:** la sombra de la placa se reenvía a
  KWin en cada fotograma de la ampliación; en el sandbox dejó un rastro. Si se
  nota, el dock dibujará su propia sombra.

### 4.14 Refracción — efecto de KWin `goldenglass_glass` (F11) ✅
- **Fork del efecto Blur de KWin 6.7.5** (`kwin-effect/`, C++, GPL-2.0-or-later
  como el original; ver `UPSTREAM.md`), compilado fuera del árbol de KWin con
  sus cabeceras instaladas (`find_package(KWin)`, `KWin::kwin`) y cargado como
  plugin externo (`kwin/effects/plugins/goldenglass_glass.so`). Va en el árbol
  CMake de `kstyle/` (opción `WITH_KWIN_EFFECT`) y en `goldenglass-kstyle`.
  Mismo difuminado (dual Kawase, mismos ajustes `Effect-blur`) y, en el paso
  final en pantalla, la refracción.
- **Sustituye a Blur:** en KWin 6.7 la región de blur la guarda el núcleo
  (`surface->blurRegion()`), no el efecto; los dos a la vez difuminarían dos
  veces, así que activar uno descarga y desactiva el otro (en vivo, D-Bus
  `/Effects`, y en `kwinrc [Plugins]`).
- **Solo las superficies de Plasma** (clase de ventana `plasmashell` o
  `krunner`: dock, barra de menús, popups, Centro de control, Apps,
  tooltips, Spotlight). Las ventanas de las apps reciben el blur normal, como
  en macOS.
- **Forma:** la región de blur se separa en piezas (rectángulos que se tocan)
  y cada una es un vidrio con su borde y su refracción: casi siempre hay una
  sola (popup, dock), pero el Centro de control con tarjetas sueltas manda
  una por tarjeta. De cada pieza, el rectángulo que la envuelve y el radio de
  cada esquina medido en la propia región (Plasma la manda con la forma
  redondeada de su SVG, en franjas: una esquina mide lo que tardan en tocar el
  lateral). Así sirve para cualquier superficie sin saber de qué tipo es.
  Distancia con signo `sdfRoundedBox` (la de KWin, incluida en el shader); una
  pasada por pieza, y fuera de su forma el shader deja los píxeles
  transparentes.
- **Shader** (`shaders/glass.frag`):
  - **Lente en el borde:** en una banda de `edge` px (como mucho el 30 % del
    lado corto, para el dock), el fondo se toma de más adentro a lo largo de
    la normal, más cuanto más cerca del borde (`strength`), y se mezcla con el
    fondo **sin difuminar** (`clarity`): con solo el difuminado la curvatura no
    se vería. El centro queda esmerilado, como Liquid Glass.
  - **Dispersión:** rojo y azul se desplazan algo más y algo menos que el verde.
  - **Borde** (`shaders/edge.frag`, pase aparte): ver abajo.
  - **Tinte adaptativo:** la luminancia del fondo se acerca a la media (`tint`).
- **Borde oscurecido y filo de luz** (macOS 27, «improved contrast»): un
  segundo pase **después** de dibujar la ventana (`drawEdge()`), solo sobre la
  banda del borde de cada pieza (hasta cuatro rectángulos por pieza,
  `edgeBand()` en `glassgeometry.h`, con la curva de las esquinas): una banda
  exterior multiplicativa de `edge_shade_width` px (× escala) que oscurece
  por `edge_shade`, y justo después el filo de luz (`specular`, más fuerte
  arriba, ancho `rim_width` × `edge`). Premultiplicado: el alfa multiplica lo
  de debajo y el color suma. El Plasma Style dibuja además dos líneas fijas,
  negra (`[glass.border] shade_alpha`) y blanca por dentro
  (`highlight_alpha`), que se ven también con el Blur de reserva.
- **Spike SP-01** (go): antes el filo se pintaba debajo del relleno del SVG y
  solo asomaba (1 − α) × aporte (0,026 en el nivel medio). Medido en el
  sandbox con temporizadores de GPU (`GL_TIMESTAMP`, efecto instrumentado
  aparte; Radeon RX 9070, no una iGPU): en una salida 4K al 150 % con el dock
  y un popup, el pase cuesta ≈ 0,04 ms por fotograma (0,147 ms medidos con el
  pase frente a 0,107 ms de la propia medida sin él); el fotograma completo
  de GPU, 0,94 ms frente a 0,93–0,95 ms sin el pase (dentro del ruido, < 2 %).
  Sin artefactos a escala 1, 1,25 y 1,5, en claro y oscuro; el texto de los
  popups queda fuera de la banda (margen del popup). En un corte
  perpendicular al borde del dock (claro, escala 1), de fuera a dentro:
  línea oscura de 1 px (76 / 89 / 101 en los niveles 0 / 0,5 / 1), pico de
  luz (179 / 207 / 237) y cuerpo (136 / 177 / 219). Con el pase, `specular`
  baja a 0,10.
- **Sigue al slider de vidrio:** con el nivel más claro, la refracción entera;
  con el más opaco, por `opaque_factor` (desplazamiento y nitidez); el borde
  por su propio `rim_opaque_factor` (filo y oscurecido), para conservar más
  contraste con el vidrio opaco. Con «Reducir transparencia», nada (4.4).
  `goldenglass-glass` pide a KWin `reconfigureEffect goldenglass_glass`, y el
  efecto relee `goldenglassrc`. Valores en `[glass.refraction]` de los tokens
  (`goldenglass_tokens.h`), calibrados con el nivel por defecto para que sea
  sutil.
- **Activación:** `goldenglass-glass --refraction on|off` (y
  `--get-refraction`: on, off o unavailable), que usa el interruptor del
  módulo Vidrio. El cambio en vivo descarga el efecto anterior, carga el
  nuevo y solo después escribe `kwinrc [Plugins]`: escrito antes, KWin
  recargaba los dos desde el aviso en el orden contrario y retiraba la
  capacidad de blur (ext-background-effect), con lo que Plasma pasaba a su
  tema opaco hasta reiniciar KWin (visto en el sandbox en el primer
  `--check` de la sesión).
- **Red de seguridad** (`goldenglass-glass --check`, autostart de
  `goldenglass-kstyle`): la primera vez lo activa (es el valor de fábrica); si
  está pedido pero KWin no lo cargó (el plugin solo carga con la versión de
  KWin con la que se compiló: KWin actualizado sin recompilar) vuelve a cargar
  el Blur; si sí lo cargó, se asegura de que el Blur no esté cargado. Nunca
  quedan los dos ni ninguno.
- **Pruebas:** en el sandbox (KWin virtual con OpenGL real): el fork sin
  cambios idéntico al Blur; con valores exagerados sobre un fondo de rayas, la
  lente, la dispersión y el centro esmerilado; calibrado con el nivel por
  defecto; y todos los casos de `--check` y del interruptor.

## 5. Distribución

- **PKGBUILD dividido ✅** (`packaging/goldenglass/`, compila la rama `main` del
  repo local; sin publicar en AUR mientras el repo sea privado):

  | Paquete | Contenido |
  |---|---|
  | `goldenglass-kstyle` (x86_64) | estilo, decoración, KCM, `goldenglass-glass` (C++: recompilar tras actualizar Qt/KDE) |
  | `goldenglass-plasma` | Plasma Style, Global Themes, shell (pantalla de bloqueo y `Panel.qml` del dock), plasmoids (dock incluido), esquemas de color, fontconfig (activado en `/etc/fonts/conf.d`), `goldenglass-system`, `goldenglass-dock` y `goldenglass-windows` (autostart con `--check`; lee `/usr/share/goldenglass/windows.json`) |
  | `goldenglass-icons` | temas de iconos claro/oscuro y `goldenglass-wrap-icons` (autostart con `--if-changed`: cada usuario encierra sus apps de terceros al iniciar sesión si cambiaron) |
  | `goldenglass-cursors` | tema de cursores |
  | `goldenglass-wallpapers` | fondo día/noche |
  | `goldenglass-gtk` | temas GTK, CSS de libadwaita y `goldenglass-gtk-sync` (autostart) |
  | `goldenglass-sounds` ✅ | tema de sonidos (se activa con `goldenglass-system` o en Efectos de sonido) |
  | `goldenglass-plymouth` ✅ | temas de Plymouth negro y gris (se activan con `goldenglass-system` o en Arranque e inicio de sesión) |
  | `goldenglass-login` ✅ | tema de SDDM (se activa con `goldenglass-system` o en Arranque e inicio de sesión; en Plasma Login Manager bastan el fondo y `goldenglass-plasma`) |
  | `goldenglass` | metapaquete (sonidos, Plymouth y login como dependencias opcionales) |

  `goldenglass-system` y su acción de polkit van en `goldenglass-plasma`, del
  que dependen los tres paquetes de sistema. El dock (F10) es solo QML: va en
  `goldenglass-plasma` con `goldenglass-dock`; su módulo de Ajustes, en
  `goldenglass-kstyle` con los demás. El efecto `goldenglass_glass` (F11) va
  en `goldenglass-kstyle`, que ya se recompila con cada actualización de KDE
  (depende de `kwin`: el plugin solo carga con esa versión).

  Se genera con `GOLDENGLASS_SYSTEM=1`: los enlaces de protección de los
  iconos y el import de adw-gtk3 solo apuntan a `/usr`, nunca al `/home` de
  quien compila.
- **`tools/install.sh`** para desarrollo: instala en `~/.local` sin empaquetar.
  `--dev` crea symlinks para iterar sin reinstalar.
- **CI ✅** (`.github/workflows/ci.yml` → `tools/ci.sh`): en cada PR y push a
  `main`, en un contenedor `archlinux:latest`, instala las dependencias de
  compilación del PKGBUILD (con caché de pacman) y comprueba:
  - Python con ruff (reglas en `pyproject.toml`: errores, no estilo) y las
    pruebas de `tools/tests` con pytest (colores y cabecera C++ de los tokens,
    `goldenglass-system` con sustitutos de kreadconfig6/kwriteconfig6/Plymouth
    en directorios temporales);
  - los scripts de `tools/` con shellcheck;
  - las traducciones: `msgfmt --check` y `tools/check_i18n.sh`, que extrae los
    textos con los `Messages.sh` (como los scripts de KDE) y exige que el
    catálogo en español los tenga todos;
  - los módulos QML y la versión del shell contra el Plasma de Arch
    (`tools/check_plasma_compat.py`);
  - el QML generado, el shell y los módulos de Ajustes con qmllint (solo las
    categorías que son errores; la lista está en `tools/ci.sh`).

  Al final hace `makepkg` del commit, que compila el C++ y pasa ctest
  (`check()`, con las pruebas D-Bus de `qmlplugin/tests` bajo
  `dbus-run-session`) una sola vez; los paquetes quedan como artefacto.

  El mismo script se ejecuta en local con `podman run --rm -v
  "$PWD":/src:Z -w /src docker.io/library/archlinux:latest tools/ci.sh`.
- **Plasma next** (`.github/workflows/plasma-next.yml`): cada lunes, la misma CI
  sobre `main` contra el Arch actual y contra `[kde-unstable]`
  (`GOLDENGLASS_CI_REPOS=kde-unstable`), que Arch llena con las betas de Plasma
  unas semanas antes de cada versión: avisa de lo que se va a romper antes de
  que llegue a stable.
- KDE Store: opcional y posterior, solo para partes no compiladas.

## 6. Repositorio y licencias

- Monorepo en GitHub.
- Código: **GPL-3.0-or-later**. Assets gráficos (iconos, cursores, wallpapers,
  SVG): **CC-BY-SA-4.0**.
- Las partes de upstream conservan su licencia (GPL-2.0-or-later, MIT y la
  cláusula de KDE e.V. en `kstyle/`, `kdecoration/`, `libgoldenglasscommon/`,
  `kwin-effect/` y la pantalla de bloqueo). Sus cabeceras no se tocan;
  `REUSE.toml` declara la licencia de todo archivo sin etiquetas SPDX y la CI
  comprueba el cumplimiento REUSE (`reuse lint`) y que los archivos nuevos de
  cada PR traigan su cabecera SPDX (`tools/check_spdx.sh`: con la licencia por
  defecto de `REUSE.toml`, `reuse lint` no lo detecta).
- Comunidad: `CONTRIBUTING.md` (DCO), `CODE_OF_CONDUCT.md`, `SECURITY.md`
  (reporte privado de GitHub), plantillas en `.github/`.
- No se incluye ningún asset, fuente ni marca de Apple. El nombre del proyecto
  evita "macOS"/"Apple".

## 7. Fases

| Fase | Contenido | Estado |
|---|---|---|
| F0 | Repo, tokens, generador, color schemes, fontconfig, `install.sh` | ✅ |
| F1 | Fork de Darkly renombrado: QStyle + decoración (semáforos, radios, sidebar, toolbar unificada) | ✅ |
| F2 | Plasma Style, Global Themes, layout (barra superior + dock), Spotlight, pantalla de bloqueo | ✅ |
| F3 | Spike de opacidad del Plasma Style → KCM completo | ✅ |
| F4 | Plasmoids: Centro de control, Launchpad, menú de sistema | ✅ |
| F5 | Iconos, cursores, wallpapers | ✅ |
| F6 | GTK, PKGBUILD, CI en GitHub | ✅ |
| F7 | Sonidos sintetizados, chime, `goldenglass-system`, módulo Efectos de sonido | ✅ |
| F8 | Plymouth negro y gris con contraseña LUKS, módulo Arranque e inicio de sesión | ✅ |
| F9 | Tema de SDDM + fondo y sincronización en Plasma Login Manager | ✅ |
| F10 | Dock unificado: ampliación, rebote, vistas previas, recientes; módulo Dock | ✅ |
| F11 | Efecto de KWin `goldenglass_glass` (fork de Blur) con refracción; interruptor en Vidrio | ✅ |
| F12 | Material y accesibilidad: filo del vidrio, sombra inactiva, semáforos grises, Reducir transparencia, Mostrar bordes | 🚧 |
| F13 | Ventanas y movimiento: efectos de KWin, atajos de tiling, velocidad de animación global, Reducir movimiento | 🚧 |
| F14 | Barra de menús y Dock: barra a 24 px, HUD de volumen y brillo, apps en segundo plano | 📋 |
| F15 | Estilos de icono Tintado y Transparente; módulo Estilo de iconos | 📋 |
| F16 | Spotlight propio (sustituye a KRunner) con vistas, portapapeles y teclas rápidas | 📋 |
| F17 | Centro de notificaciones y avisos de vidrio | 📋 |

F12–F17 se planifican en [MACOS27-PLAN.md](MACOS27-PLAN.md).

Orden de menor a mayor riesgo: lo independiente primero; lo que depende de la
API interna de KWin y de Plasma, al final.

## 8. Fuera de alcance

X11 y Plasma < 6.8. Gestores de inicio de sesión distintos de SDDM y Plasma
Login Manager (GDM, LightDM…). Un fork del greeter de Plasma Login Manager.
Refracción en las ventanas de las apps.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| Opacidad del Plasma Style no ajustable en vivo | Resuelto en el spike de F3: regenerar + alternar id (o rebote por Breeze); plan B: 3 sub-temas fijos |
| Divergencia del fork de Darkly respecto a upstream | Renombrado limpio y registro de cambios propios para poder hacer rebase |
| Roturas por actualizaciones de Qt/KDE (rolling) | PKGBUILD con rebuild; CI contra la versión actual de Arch y, cada semana, contra `[kde-unstable]` (betas de Plasma) |
| Alias de fuente no resuelto por Qt | Plan B descrito en 4.6 |
| libadwaita ignora temas | Solo colores; documentado |
| Los plasmoids usan módulos QML privados de Plasma (sin API estable) | Mínimo Plasma 6.8; `tools/plasma_api.toml` lista los tipos, propiedades, métodos, señales, enums y roles privados que usa el QML y `tools/check_plasma_compat.py` los comprueba contra los `.qmltypes` instalados (los roles, contra las cadenas del plugin) en la CI y en la semanal con `[kde-unstable]`, indicando el archivo QML afectado; un módulo privado sin listar falla; probar en el sandbox tras cada actualización de Plasma |
| Plasma limita la altura de cada panel a la suma de las esquinas de `panel-background` (barra y dock comparten SVG) | `radius.dock ≤ menubar_height / 2` (14 px); el generador lo valida |
| Plasma Login Manager no admite temas: el diseño propio solo se ve con SDDM | En PLM se aplica fondo y sincronización (el módulo lo explica); si KDE añade temas, se porta el QML de SDDM |
| Copiar ajustes de un usuario al home de `plasmalogin` como root | Lectura como el usuario y escritura como `plasmalogin` en procesos hijo sin privilegios; probado con un enlace a `/etc/shadow` |
| La especificación de sonidos recurre a `freedesktop` para lo que falta | Los nombres no cubiertos llevan un `<nombre>.disabled` |
| Activar Plymouth regenera el initramfs con root | Comando explícito o «Aplicar» con pkexec; avisos de `splash` y del hook; si falla el initramfs se mantiene el tema anterior |
| La fuente del tema entra en cada initramfs | Inter Variable (0,9 MB) en vez de `Inter.ttc` (13 MB) |
| El dock depende de `views/Panel.qml` copiado de Plasma; si no carga, plasmashell se cae (pasó con Plasma 6.8) | Cambio mínimo y documentado en `UPSTREAM.md` (merge a tres vías por versión); `X-GoldenGlass-PlasmaVersion` + hook de pacman que quita `views/` y `lockscreen/` con otro Plasma; la CI comprueba módulos QML y versión (`tools/check_plasma_compat.py`) |
| PanelView fija la región de entrada desde el borde superior de la placa | Aceptado: la ampliación se recoge al salir de la placa (4.13) |
| El dock unificado pierde funciones de `icontasks` | Mismo `TasksModel`; menú, vistas previas, arrastre y soltar archivos reimplementados (4.13) |
| La API de efectos de KWin no es estable: el efecto se rompe con cada KWin | Recompilar `goldenglass-kstyle` (un hook de pacman lo avisa al actualizar KWin); `goldenglass-glass --check` al iniciar sesión reactiva Blur si el efecto no carga; fork documentado en `UPSTREAM.md` |
| Valores de fábrica de KWin que pisan los del usuario | `goldenglass-windows` solo escribe claves vacías, una vez por `DefaultsVersion` y solo con un Global Theme GoldenGlass; «Reducir movimiento» guarda y devuelve lo anterior sin pisar lo que el usuario cambió; pruebas de actualización con un `kwinrc` previo |
| Coste de GPU de la refracción | Solo superficies de Plasma; dos muestras más por píxel solo en la banda del borde; interruptor en el módulo Vidrio |
