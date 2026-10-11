# GoldenGlass — Arquitectura

Tema completo para KDE Plasma en CachyOS inspirado en macOS 27 "Golden Gate"
(refinamiento de Liquid Glass presentado en WWDC 2026, publicado el 14/09/2026).

## 1. Objetivos

- Fidelidad **alta** a macOS: barra de menús superior con menú global, dock
  centrado, semáforos a la izquierda, Spotlight, Launchpad, Centro de control.
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
| `gtk/*.css` | GTK3 / GTK4 | F6 |

**Regla:** los archivos generados no se editan a mano ni se versionan. Se cambia
el token y se regenera (`install.sh` y el PKGBUILD lo hacen solos).

## 4. Componentes

```
goldenglass/
├── tokens/              # goldenglass.toml
├── tools/               # gen_tokens.py (+ plasma_theme.py, lookandfeel.py, wallpaper.py,
│                        # cursors.py…), install.sh,
│                        # preview_plasma.py (vista previa), sandbox.sh (sesión aislada)
├── assets/logo/         # logo GoldenGlass (símbolo monocromo y versión a color)
├── kstyle/              # QStyle C++ (fork de Darkly) → goldenglass6.so
├── kdecoration/         # Plugin KDecoration3
├── kcm/                 # Módulo de Ajustes "GoldenGlass"
├── plasma/
│   ├── look-and-feel/   # plantilla común de los Global Themes (layout, splash)
│   ├── shell/           # shell org.goldenglass.desktop (pantalla de bloqueo)
│   └── plasmoids/       # Centro de control, Launchpad, menú de sistema
├── gtk/                 # (generado en parte)
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
- **Semáforos** (`goldenglasstrafficlight.cpp`): cerrar, minimizar y maximizar
  como círculos de vidrio de 12 px separados 8 px (tokens `traffic_lights`).
  Al pasar el ratón por cualquiera aparecen los símbolos en los tres; en ventanas
  inactivas son grises y se colorean al pasar el ratón. El zoom apunta hacia
  dentro con la ventana maximizada. `build/cmake/bin/trafficlight_preview
  salida.png` dibuja todos los estados para revisarlos sin KWin.
- Radio de esquina y sombras desde los tokens.
- **Toolbar unificada:** con `decoration.glass_titlebar` la barra de título usa
  el mismo color (Header) y la misma opacidad de vidrio que la toolbar, y KWin
  difumina detrás de ambas: se ven como una sola barra. Límite: los semáforos no
  pueden compartir fila con los botones de la toolbar, porque la toolbar la
  dibuja cada aplicación.

### 4.3 Efecto de vidrio
- **Blur nativo de KWin + superficies semitransparentes.** Sin efecto KWin propio
  ni dependencias de terceros. Sin refracción.
- La opacidad de cada superficie sale del nivel de vidrio activo.

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
    iconos (sin magnificación).
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
  - `org.goldenglass.launchpad` ✅ — primer elemento del dock; ventana
    `DashboardWindow` de Plasma (pantalla completa, blur) con buscador
    (`krunner_services`), páginas de hasta 7×5 apps de «Todas las aplicaciones»
    (`RootModel`) y puntos de página. Se declara `org.kde.plasma.launchermenu`:
    la tecla Meta lo abre.
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
  - **Pendiente:** ~50 apps (`feature/icons-apps`, squircle con capas).
  - La papelera de Plasma pide `user-trash-symbolic` dentro de un panel: en el
    dock sale el símbolo, no la papelera a color.
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

### 4.8 GTK — `gtk/`
- GTK3: tema completo generado desde tokens.
- GTK4/libadwaita: **solo colores** vía `~/.config/gtk-4.0/gtk.css` (libadwaita no
  admite temas oficialmente). Limitación aceptada.

## 5. Distribución

- Ya existe `packaging/goldenglass-kstyle/PKGBUILD` (estilo + decoración + KCMs,
  compila desde el repo local). El resto (Plasma, iconos…) se instala de momento
  con `tools/install.sh`.
- **PKGBUILD dividido** (`packaging/`) para AUR/CachyOS:
  `goldenglass-kstyle` (estilo + decoración + KCM, compilado),
  `goldenglass-plasma`, `goldenglass-icons`, `goldenglass-cursors`,
  `goldenglass-wallpapers`, `goldenglass-gtk` y el metapaquete `goldenglass`.
  Las partes C++ deben recompilarse con cada actualización de Qt/KDE.
- **`tools/install.sh`** para desarrollo: instala en `~/.local` sin empaquetar.
  `--dev` crea symlinks para iterar sin reinstalar.
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
| F5 | Iconos, cursores, wallpapers | en curso (wallpapers ✅, cursores ✅, iconos base y tipos de archivo ✅) |
| F6 | GTK, PKGBUILD, CI en GitHub | pendiente |

## 8. Fuera de alcance

SDDM, Plymouth, sonidos del sistema, dock con magnificación, efecto KWin propio
con refracción, X11 y Plasma < 6.7.

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
