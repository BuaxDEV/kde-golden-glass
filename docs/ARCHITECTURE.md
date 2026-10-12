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
| Menús | Sin iconos junto a cada comando | `kstyle/` |
| Barra de menús | Desbordamiento de iconos tras un chevron «»; fondo translúcido opcional | `plasma/desktoptheme`, layout |
| Iconos de app | Squircle con capas y más detalle | `icons/` |
| Liquid Glass | El fondo se curva como una lente en los bordes del vidrio, con dispersión, filo de luz y tinte que se adapta al fondo | `kwin-effect/` (F11) |
| Dock | Ampliación de los iconos bajo el cursor | `plasma/plasmoids/org.goldenglass.dock` (F10) |
| Arranque y sesión | Logo con barra de progreso, pantalla de inicio de sesión como la de bloqueo, sonidos del sistema | `plymouth/`, `login/`, `tools/sounds.py` (F7–F9) |

Fuentes: Six Colors (review), 9to5Mac (slider de Liquid Glass), Digital Trends,
Wccftech. Los valores numéricos exactos (radios, opacidades) no están publicados:
los tokens parten de valores iniciales que se calibran contra capturas.

## 2. Plataforma soportada

- **Plasma ≥ 6.7, solo Wayland.** Qt 6. Sin soporte X11.
- Desarrollo sobre CachyOS (Plasma 6.7.5, Qt 6.12, KWin 6.7.5).

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
| `build/wallpapers/GoldenGlass/` (numpy, se cachea) | Fondo de pantalla día/noche | ✅ F5 |
| `build/cursors/GoldenGlass-cursors/` (QtSvg, se cachea) | Tema de cursores (SVG + Xcursor) | ✅ F5 |
| `build/icons/GoldenGlass{,-Dark}/` (SVG dibujados por código) | Tema de iconos claro/oscuro | F5 (base ✅) |
| `build/gtk/GoldenGlass{,-Dark}/`, `build/gtk/libadwaita.css` | GTK3 / GTK4 / libadwaita | ✅ F6 |
| `build/sounds/GoldenGlass/` (numpy + python-soundfile, se cachea) | Tema de sonidos freedesktop | ✅ F7 |
| `build/plymouth/goldenglass{,-light}/` (logo rasterizado con QtSvg) | Temas de Plymouth negro y gris | F8 |
| `build/login/sddm/GoldenGlass/` (desde `login/sddm/`) | Tema de SDDM | F9 |
| `contents/ui/tokens.js` del dock (lo genera `tools/plasmoids.py`) | Plasmoid `org.goldenglass.dock` | F10 |
| `goldenglass_tokens.h` (secciones `[dock]` y `[glass.refraction]`) | Valores de fábrica del dock y del efecto de KWin | F10, F11 |

**Regla:** los archivos generados no se editan a mano ni se versionan. Se cambia
el token y se regenera (`install.sh` y el PKGBUILD lo hacen solos).

## 4. Componentes

```
goldenglass/
├── tokens/              # goldenglass.toml
├── tools/               # gen_tokens.py (+ plasma_theme.py, lookandfeel.py, wallpaper.py,
│                        # cursors.py, sounds.py, plymouth.py…), install.sh,
│                        # system.py (goldenglass-system),
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

### 4.2 Decoración de ventanas — `kdecoration/` (C++, KDecoration3)
- En el mismo árbol CMake que `kstyle/` (como Breeze/Darkly), config compartida.
- **Semáforos** (`goldenglasstrafficlight.cpp`), como los de macOS 27 Golden
  Gate (Liquid Glass): gemas de vidrio de 14 px separadas 8 px con sombra suave
  que las separa de la ventana, relleno con volumen, borde fino, **brillo arriba
  y brillo abajo** y glifo tintado por botón (×, −, triángulos de pantalla
  completa; tokens `traffic_lights`). Al pulsar se encogen un poco. Al pasar el
  ratón por cualquiera aparecen los símbolos en los tres. Siempre en color, también
  en ventanas sin foco (`traffic_lights.inactive_colored`; con `false`, como
  macOS: vidrio gris con los brillos atenuados que se colorea al pasar el ratón). El
  zoom apunta hacia dentro con la ventana maximizada. **Posición** con la regla
  de Apple: el primer círculo está tan lejos del borde izquierdo como del
  superior (`Decoration::leftButtonsPadding`). Los semáforos CSD de GTK usan
  los mismos colores, glifos y brillos. `build/cmake/bin/trafficlight_preview
  salida.png` dibuja todos los estados para revisarlos sin KWin.
- Radio de esquina y sombras desde los tokens.
- **Toolbar unificada:** con `decoration.glass_titlebar` la barra de título usa
  el mismo color (Header) y la misma opacidad de vidrio que la toolbar, y KWin
  difumina detrás de ambas: se ven como una sola barra. Límite: los semáforos no
  pueden compartir fila con los botones de la toolbar, porque la toolbar la
  dibuja cada aplicación.

### 4.3 Efecto de vidrio
- **Base: blur nativo de KWin + superficies semitransparentes.** Es lo que se
  ve sin el efecto propio (o si no carga) y lo que siguen usando las ventanas
  de las apps.
- La opacidad de cada superficie sale del nivel de vidrio activo.
- **Refracción (F11):** efecto propio `goldenglass_glass`, ver 4.14.

### 4.4 Nivel de vidrio — `goldenglass-glass` y módulo de Ajustes (`kcm/`)

**`goldenglass-glass --level N`** (`tools/glass.py`, instalado con sus archivos
en `share/goldenglass`) aplica un nivel en vivo a las tres capas:

| Capa | Cómo |
|---|---|
| Estilo de apps | `goldenglassrc [Style]` (menús, toolbars, barra lateral) + señal D-Bus `org.goldenglass.Style` → repinta las ventanas abiertas |
| Decoración | misma opacidad (`ToolBarOpacity`) + `KWin.reconfigure` → relee `goldenglassrc` |
| Plasma Style | nivel por defecto → tema del paquete `GoldenGlass`; otro nivel → genera `GoldenGlassTuned` en `~/.local/share` y cambia a él (con rebote por `GoldenGlass` si ya estaba activo). El tema del paquete nunca se sobrescribe |

El cambio de tema se hace dentro de plasmashell (`evaluateScript`,
`theme = …`), de forma síncrona; si plasmashell no corre, se escribe `plasmarc`.
Para cambios rápidos seguidos: al regenerar `GoldenGlassTuned` se borra su caché
de KSvg (caduca por segundos) y el rebote espera 0,35 s (libplasma agrupa los
avisos de cambio de tema cada 100 ms).
Verificado en el sandbox midiendo la barra de menús, el título y la toolbar de
Dolphin en 0 → 1 → 0,5 → 0 → 0 → 1.

#### Módulo de Ajustes

`kcm/` (`kcm_goldenglass`, C++ + QML): Preferencias del Sistema › Colores y
temas › **Vidrio**. Control con las tres muescas de los tokens (imán al soltar
cerca) y valores intermedios; se aplica en vivo al soltar ejecutando
`goldenglass-glass`; si se suelta varias veces, solo se encola el último nivel.
"Predeterminados" vuelve al nivel de fábrica; no hay "Aplicar". Traducción al
español en `po/es`. `kcm_apply_test` (prueba de integración, dentro de una
sesión Plasma) pide 1,0 → 0,0 → 0,25 seguidos y comprueba que queda 0,25.

#### Otros módulos de Ajustes

Como en macOS, cada ajuste vive donde el usuario lo busca: **módulos aparte**
(cada uno en `kcm/<nombre>/`, con su dominio de traducción) en vez de páginas
dentro de «Vidrio».

| Módulo | Dónde | Contenido | Fase |
|---|---|---|---|
| Vidrio (`kcm_goldenglass`) | Colores y temas | slider actual + interruptor **Refracción** (efecto `goldenglass_glass`) | ✅ / F11 |
| Efectos de sonido (`kcm_goldenglass_sounds`) | Multimedia | sonidos de GoldenGlass y sonido al iniciar sesión, con botón para escucharlos (`pw-play`); llama a `goldenglass-system` (4.9) | ✅ F7 |
| Arranque e inicio de sesión | Sesión (a confirmar en F8) | Plymouth (negro / gris) y pantalla de inicio de sesión | F8–F9 |
| Dock | Escritorio y ventanas (a confirmar en F10) | **Ampliación** (interruptor, activada de fábrica) y su tamaño máximo, tamaño del dock | F10 |

### 4.5 Escritorio Plasma — `plasma/`
- **Plasma Style** `GoldenGlass`: lo genera `tools/plasma_theme.py` dibujando
  cada pieza de FrameSvg por código (esquinas, bordes, máscara de blur, sombra).
  Usa clases `ColorScheme-*`, así que **un solo Plasma Style sirve para claro y
  oscuro**; solo la opacidad queda fija en el SVG. Genera diálogos, panel (barra
  de menús y dock), tooltips, fondo de widgets, tareas del dock (punto bajo las
  apps abiertas), resaltado de listas, campos de texto y cabeceras de popups. Lo
  que no genera se hereda de Breeze. `plasmarc` pide saturación extra detrás del
  blur ("vibrancy").
- **Global Themes** (`look-and-feel/`): `org.goldenglass.light.desktop` y
  `org.goldenglass.dark.desktop`. Incluyen:
  - Script de layout: panel superior (menú de sistema, menú global, bandeja,
    reloj) + **dock** = panel nativo flotante centrado con gestor de tareas solo
    iconos (sin magnificación hasta F10, ver 4.13), **autoocultable** como en
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
- **Pantalla de bloqueo** estilo macOS (reloj grande arriba, avatar y contraseña
  abajo). Desde Plasma 6 vive en el **paquete de shell**, no en el Global Theme:
  - `plasma/shell/org.goldenglass.desktop` solo trae `lockscreen/` y hereda el
    resto de `org.kde.plasma.desktop` (`X-Plasma-FallbackPackage`).
  - `lockscreen/` es la de plasma-desktop 6.7.5 con cambios mínimos (ver
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
  - `org.goldenglass.controlcenter` ✅ — en la barra, junto al reloj. Tarjetas de
    Wi‑Fi y Bluetooth (el texto abre sus ajustes), Modo oscuro (`DarkModeControl`
    de Plasma; el layout fija `DefaultLight/DarkLookAndFeel` a los temas
    GoldenGlass), No molestar, brillo por pantalla (si hay control, p. ej.
    DDC/CI), sonido con silencio, vidrio (`goldenglass-glass`) y lo que se
    reproduce (MPRIS). Usa los módulos QML de Plasma (privados: se revisan en
    cada actualización de Plasma).
  - `org.goldenglass.launchpad` ✅ **Apps** — primer elemento del dock, como
    Apps de macOS 26/27 (que sustituyó a Launchpad y vive en Spotlight): un
    `PlasmaCore.Dialog` flotante centrado en la pantalla del dock (vidrio, blur
    y sombra del Plasma Style) con buscador, etiquetas de categoría, «Sugeridas»
    (`RecentUsageModel`) y secciones por categoría con «Mostrar más», en
    cuadrícula o lista y por categoría o por nombre (se recuerda en la
    configuración del plasmoid). Las categorías del menú de KDE (`RootModel`,
    identificadas por su icono) se agrupan en las 7 de macOS (`categories.js`).
    Teclado: flechas y Return, Tab entre etiquetas, Escape borra y luego
    cierra; si lo escrito no es una app, «Buscar en Spotlight» pasa la consulta
    a KRunner. Medidas en `[apps]` de los tokens (`contents/ui/tokens.js`, que
    `tools/plasmoids.py` genera en cada plasmoid). Las acciones de Kicker
    (`actionList`) se leen solo al abrir el menú contextual: leerlas al cargar
    tumba plasmashell. Los menús (contextual y ordenar) son ventanas emergentes
    propias (`popupType: Popup.Window`): dentro del panel quedaban recortados
    y sin blur. El icono del dock es `goldenglass-apps` del tema de iconos (claro u oscuro),
    con `view-app-grid` de respaldo. Se declara `org.kde.plasma.launchermenu`: Meta lo abre.
  - `org.goldenglass.trash` ✅ — papelera del dock como la de macOS: icono a
    color del tema (`user-trash`/`user-trash-full` según haya archivos en
    `~/.local/share/Trash/files`, que crea si falta: `FolderListModel` lista el
    directorio actual si la carpeta no existe), clic abre `trash:/`, soltar
    archivos los tira con `gio trash` y el menú «Vaciar papelera…» pide
    confirmación (`kdialog`) antes de `ktrash6 --empty`.
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
  que lo llaman. Partes: `sounds` y `chime` ✅; `plymouth` y `login` llegan en
  F8–F9.
- Lo que es del usuario (sonidos, chime) se escribe en su `~/.config` sin root,
  con `kwriteconfig6 --notify`.
  Lo del sistema (Plymouth, login) se ejecuta con **pkexec** y una acción de
  polkit propia (`org.goldenglass.system`); solo entonces se pide la contraseña.
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

### 4.11 Arranque — Plymouth (F8)
- Dos temas: **`goldenglass`** (negro, logo blanco; el de fábrica) y
  **`goldenglass-light`** (gris claro, logo oscuro), como las dos variantes del
  arranque de Mac. Se elige con `goldenglass-system enable plymouth
  [--variant dark|light]`.
- Logo GoldenGlass (`assets/logo/goldenglass-symbolic.svg`) rasterizado con
  QtSvg a varias escalas (se elige según la resolución) y **barra de progreso
  fina** redondeada bajo el logo, que avanza con el progreso de arranque.
  Mismas proporciones que el splash de Plasma, para que la secuencia arranque →
  login → escritorio se vea continua.
- **Plugin `script`** de Plymouth (`plymouth/goldenglass.script.in`, plantilla
  que rellena `tools/plymouth.py` con los tokens `[boot]`): da control total
  sobre la petición de contraseña.
- **Contraseña de disco (LUKS)** estilo FileVault: campo de vidrio con puntos
  y el texto de la petición. También mensajes (fsck) y el modo de apagado.
- Activación: `plymouth-set-default-theme` + `mkinitcpio -P` (en CachyOS con
  Limine los hooks de limine-mkinitcpio actualizan las entradas). Si
  `mkinitcpio` falla se restaura el tema anterior.
- Paquete `goldenglass-plymouth`.

### 4.12 Inicio de sesión — SDDM y Plasma Login Manager (F9)
- **Plasma Login Manager** (PLM, el sucesor de SDDM de KDE, el que usa CachyOS
  con Plasma 6.7) **no admite temas**: su interfaz va compilada en el binario
  (`qrc:/qt/qml/org/kde/plasma/login/Main.qml`). Por eso hay dos caminos:
- **SDDM: tema propio `GoldenGlass`** (`login/sddm/`, QML Qt 6,
  `QtVersion=6`), con el **diseño de nuestra pantalla de bloqueo**: reloj
  grande arriba, fondo difuminado, avatar y contraseña abajo; con varios
  usuarios, fila de avatares. Reposo / Reiniciar / Apagar, sesión y teclado,
  discretos. Solo Qt Quick (sin módulos de Plasma: corre como el usuario
  `sddm`); blur con `MultiEffect`. Colores, radios y fuentes en un
  `theme.conf` generado desde los tokens; traducciones `.qm` desde `po/`.
- **Claro/oscuro según la hora:** fondo de día o de noche (franja horaria en
  `[login]` de los tokens); los controles son siempre vidrio oscuro con texto
  claro, como el login de macOS.
- **PLM:** lo que permite: el fondo GoldenGlass y la sincronización de los
  ajustes de Plasma del usuario (colores, Plasma Style, fuentes, cursor,
  iconos) al usuario `plasmalogin`. La disposición sigue siendo la de KDE.
- `goldenglass-system enable login` detecta el gestor activo
  (`display-manager.service`): con SDDM escribe
  `/etc/sddm.conf.d/goldenglass.conf`; con PLM aplica lo anterior. **Nunca
  cambia de gestor.**
- Vista previa sin cerrar sesión: `sddm-greeter-qt6 --test-mode --theme
  build/login/sddm/GoldenGlass`.
- Paquete `goldenglass-login` (SDDM como dependencia opcional).

### 4.13 Dock con ampliación — `org.goldenglass.dock` (F10)
- Hoy el dock son cuatro plasmoids en un panel (Apps, `icontasks`,
  separador, Papelera). Un panel recorta su contenido a su grosor y cada
  plasmoid es independiente, así que la ampliación no puede cruzar de uno a
  otro. Se sustituyen por **un plasmoid de dock unificado**:
  - Apps (el diálogo actual de `org.goldenglass.launchpad`, que hereda la
    declaración `org.kde.plasma.launchermenu`: Meta lo abre), apps fijadas y
    abiertas (`TasksModel` de libtaskmanager, el mismo modelo que usa
    `icontasks`), separador y Papelera. El código de Apps y Papelera se
    comparte en tiempo de generación (`tools/plasmoids.py`); los plasmoids
    sueltos siguen disponibles para otros paneles.
  - **Ampliación como macOS:** el icono bajo el cursor crece hasta el tamaño
    máximo y los vecinos con una caída suave; los iconos crecen hacia arriba y
    la placa de vidrio se ensancha sin crecer en altura. Activada de fábrica.
    Tokens `[dock]`: `magnification`, `magnification_size`, `spread`,
    duraciones.
  - El panel se hace más alto (margen transparente para los iconos ampliados)
    y **sin fondo propio**: el plasmoid dibuja la placa de vidrio. Un módulo
    QML en C++ (`org.goldenglass.private.dock`) fija en la ventana del panel la
    **región de blur** (`KWindowEffects`) y la **región de entrada** (solo la
    placa y los iconos: el margen transparente deja pasar los clics).
  - Configuración en `goldenglassrc [Dock]` (sección Dock del módulo de
    Ajustes); el plasmoid la sigue en vivo con KConfigWatcher desde el módulo
    C++.
  - Va en `goldenglass-kstyle` (necesita la parte compilada). El script de
    layout usa el dock nuevo si está instalado (`knownWidgetTypes`); si no,
    monta el dock actual.
- **Spike al empezar la fase:** quitar el fondo del panel sin tocar el de la
  barra de menús (comparten SVG), y comprobar que PanelView no pisa la región
  de blur ni la de entrada, también con autoocultación. Si no es viable, el
  plan B es un dock como app propia con layer-shell (lo que hacía Latte Dock).
- Paridad con el dock actual: clic, menú contextual (fijar, salir, acciones de
  la app), arrastrar para reordenar, soltar archivos sobre una app, punto de app
  abierta y autoocultación. Las vistas previas de ventanas en el tooltip se
  deciden en la fase.

### 4.14 Refracción — efecto de KWin `goldenglass_glass` (F11)
- **Fork del efecto Blur de KWin 6.7** (`kwin-effect/`, C++, en el mismo
  árbol CMake que `kstyle/`; GPL-2.0-or-later como el original). Mismo
  difuminado y, en el mismo shader, la refracción. **Sustituye a Blur:** solo
  uno de los dos puede atender el protocolo de blur de Wayland, así que al
  activarlo se desactiva Blur en `kwinrc` y al desactivarlo vuelve.
- **Solo las superficies de Plasma** llevan refracción: dock, barra de menús,
  popups, Centro de control, Apps, tooltips y Spotlight (se reconocen por app
  id y tipo de ventana: plasmashell, krunner). Las ventanas de las apps
  reciben el blur normal, como en macOS.
- **Rasgos:**
  - **Refracción en los bordes:** el fondo se curva como una lente cerca del
    borde redondeado; el centro queda plano.
  - **Dispersión cromática** leve en la zona refractada.
  - **Brillo especular** fijo en el borde superior (como los semáforos).
  - **Tinte adaptativo:** aclara u oscurece el fondo según su luminancia media
    para mantener la legibilidad.
- **Sigue al slider de vidrio:** más claro = más refracción, más opaco = casi
  ninguna (`[glass.refraction]` de los tokens da los extremos). Interruptor
  «Refracción» en el módulo de Ajustes para apagarlo. `goldenglass-glass` ya
  llama a `KWin.reconfigure`, que relee `goldenglassrc`.
- **Forma:** el protocolo de blur solo da una región (rectángulos). La lente
  necesita la forma redondeada: se toma el rectángulo de cada componente de la
  región y el radio del tipo de superficie desde los tokens (dock, popup…).
  Se valida en el spike.
- **Red de seguridad:** al iniciar sesión, si el efecto está activado pero
  KWin no lo ha cargado (p. ej. tras actualizar KWin sin recompilar), se
  reactiva Blur para no quedarse sin difuminado.
- **Spike al empezar la fase:** compilar el fork fuera del árbol de KWin con
  las cabeceras de `/usr/include/kwin`, sustituir a Blur en caliente y
  obtener la forma de las superficies.

## 5. Distribución

- **PKGBUILD dividido ✅** (`packaging/goldenglass/`, compila la rama `main` del
  repo local; sin publicar en AUR mientras el repo sea privado):

  | Paquete | Contenido |
  |---|---|
  | `goldenglass-kstyle` (x86_64) | estilo, decoración, KCM, `goldenglass-glass` (C++: recompilar tras actualizar Qt/KDE) |
  | `goldenglass-plasma` | Plasma Style, Global Themes, shell y pantalla de bloqueo, plasmoids, esquemas de color, fontconfig (activado en `/etc/fonts/conf.d`) |
  | `goldenglass-icons` | temas de iconos claro/oscuro y `goldenglass-wrap-icons` (autostart con `--if-changed`: cada usuario encierra sus apps de terceros al iniciar sesión si cambiaron) |
  | `goldenglass-cursors` | tema de cursores |
  | `goldenglass-wallpapers` | fondo día/noche |
  | `goldenglass-gtk` | temas GTK, CSS de libadwaita y `goldenglass-gtk-sync` (autostart) |
  | `goldenglass-sounds` ✅ | tema de sonidos (se activa con `goldenglass-system` o en Efectos de sonido) |
  | `goldenglass-plymouth` (F8) | temas de Plymouth negro y gris |
  | `goldenglass-login` (F9) | tema de SDDM y fondo para Plasma Login Manager |
  | `goldenglass` | metapaquete (sonidos, Plymouth y login como dependencias opcionales) |

  `goldenglass-system` y su acción de polkit van en `goldenglass-plasma`, del
  que dependen los tres paquetes de sistema. Lo compilado de F10 y F11 (dock
  con su módulo QML y el efecto `goldenglass_glass`) va en
  `goldenglass-kstyle`, que ya se recompila con cada actualización de KDE.

  Se genera con `GOLDENGLASS_SYSTEM=1`: los enlaces de protección de los
  iconos y el import de adw-gtk3 solo apuntan a `/usr`, nunca al `/home` de
  quien compila.
- **`tools/install.sh`** para desarrollo: instala en `~/.local` sin empaquetar.
  `--dev` crea symlinks para iterar sin reinstalar.
- **CI ✅** (`.github/workflows/ci.yml` → `tools/ci.sh`): en cada PR y push a
  `main`, en un contenedor `archlinux:latest`, instala las dependencias de
  compilación del PKGBUILD (con caché de pacman), comprueba Python, bash y las
  traducciones, ejecuta los generadores, compila el C++ y pasa ctest, y hace
  `makepkg` del commit; los paquetes quedan como artefacto. El mismo script se
  ejecuta en local con `podman run --rm -v "$PWD":/src:Z -w /src
  docker.io/library/archlinux:latest tools/ci.sh`.
- KDE Store: opcional y posterior, solo para partes no compiladas.

## 6. Repositorio y licencias

- Monorepo en GitHub.
- Código: **GPL-3.0-or-later**. Assets gráficos (iconos, cursores, wallpapers,
  SVG): **CC-BY-SA-4.0**.
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
| F8 | Plymouth negro y gris con contraseña LUKS | |
| F9 | Tema de SDDM + fondo y sincronización en Plasma Login Manager | |
| F10 | Spike del panel → dock unificado con ampliación → sección Dock | |
| F11 | Spike del fork de Blur → efecto `goldenglass_glass` con refracción → interruptor en Vidrio | |

Orden de menor a mayor riesgo: lo independiente primero; lo que depende de la
API interna de KWin y de Plasma, al final.

## 8. Fuera de alcance

X11 y Plasma < 6.7. Gestores de inicio de sesión distintos de SDDM y Plasma
Login Manager (GDM, LightDM…). Un fork del greeter de Plasma Login Manager.
Refracción en las ventanas de las apps.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| Opacidad del Plasma Style no ajustable en vivo | Resuelto en el spike de F3: regenerar + alternar id (o rebote por Breeze); plan B: 3 sub-temas fijos |
| Divergencia del fork de Darkly respecto a upstream | Renombrado limpio y registro de cambios propios para poder hacer rebase |
| Roturas por actualizaciones de Qt/KDE (rolling) | PKGBUILD con rebuild; CI contra la versión actual de Arch |
| Alias de fuente no resuelto por Qt | Plan B descrito en 4.6 |
| libadwaita ignora temas | Solo colores; documentado |
| Los plasmoids usan módulos QML privados de Plasma (sin API estable) | Mínimo Plasma 6.7; probar en el sandbox tras cada actualización de Plasma |
| Plasma limita la altura de cada panel a la suma de las esquinas de `panel-background` (barra y dock comparten SVG) | `radius.dock ≤ menubar_height / 2` (14 px); el generador lo valida |
| Plasma Login Manager no admite temas: el diseño propio solo se ve con SDDM | En PLM se aplica fondo y sincronización; si KDE añade temas, se porta el QML de SDDM |
| La especificación de sonidos recurre a `freedesktop` para lo que falta | Los nombres no cubiertos llevan un `<nombre>.disabled` |
| Activar Plymouth regenera el initramfs con root | Comando explícito, aviso previo, restauración del tema anterior si `mkinitcpio` falla |
| Quitar el fondo del panel y fijar sus regiones de blur y entrada no tiene API en Plasma | Spike al inicio de F10; plan B: dock como app con layer-shell; si no está el dock nuevo, el layout monta el actual |
| El dock unificado pierde funciones de `icontasks` | Lista de paridad en 4.13; mismo `TasksModel` |
| La API de efectos de KWin no es estable: el efecto se rompe con cada KWin | Recompilar `goldenglass-kstyle`; comprobación al iniciar sesión que reactiva Blur si el efecto no carga |
| Coste de GPU de la refracción | Solo superficies de Plasma; interruptor en el módulo de Ajustes |
