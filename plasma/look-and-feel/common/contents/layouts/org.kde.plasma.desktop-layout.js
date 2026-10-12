// SPDX-FileCopyrightText: 2026 GoldenGlass contributors
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Layout de GoldenGlass: barra de menús superior en cada pantalla y dock
// flotante centrado en la pantalla principal.
//
// Plantilla: tools/gen_tokens.py sustituye los marcadores entre arrobas desde los tokens.

const MENUBAR_HEIGHT = @MENUBAR_HEIGHT@;
const DOCK_HEIGHT = @DOCK_HEIGHT@;

// --- Barra de menús (todas las pantallas) -----------------------------------
for (let screen = 0; screen < screenCount; ++screen) {
    const menubar = new Panel;
    menubar.screen = screen;
    menubar.location = "top";
    menubar.floating = false;
    menubar.lengthMode = "fill";
    menubar.hiding = "none";
    menubar.opacity = "translucent";
    // La altura va al final: Plasma la limita al tamaño de las esquinas del
    // fondo con los bordes activos, y un panel flotante los activa todos.
    menubar.height = MENUBAR_HEIGHT;

    // Menú del logo (como el menú Apple), con Alt+F1 como Kickoff.
    const systemMenu = menubar.addWidget("org.goldenglass.systemmenu");
    if (screen === 0) {
        systemMenu.globalShortcut = "Alt+F1";
    }

    // Menú global de la aplicación activa.
    menubar.addWidget("org.kde.plasma.appmenu");

    menubar.addWidget("org.kde.plasma.panelspacer");

    menubar.addWidget("org.kde.plasma.systemtray");

    // Centro de control (Wi‑Fi, Bluetooth, modo oscuro, No molestar, brillo,
    // sonido, vidrio, multimedia), junto al reloj como en macOS.
    menubar.addWidget("org.goldenglass.controlcenter");

    // Reloj estilo macOS: "sáb 10 oct 13:04".
    const clock = menubar.addWidget("org.kde.plasma.digitalclock");
    clock.currentConfigGroup = ["Appearance"];
    clock.writeConfig("showDate", true);
    clock.writeConfig("dateFormat", "custom");
    clock.writeConfig("customDateFormat", "ddd d MMM");
    clock.writeConfig("dateDisplayFormat", 1); // BesideTime
    clock.writeConfig("showSeconds", 0);       // Never
}

// --- Dock (pantalla principal) ----------------------------------------------
const dock = new Panel;
dock.screen = 0;
dock.location = "bottom";
dock.floating = true;
dock.lengthMode = "fit";
dock.alignment = "center";
dock.hiding = "@DOCK_HIDING@";

// Deslizamiento del dock al aparecer/ocultarse (efecto Sliding Popups de KWin,
// también el de los popups de Plasma): KLookAndFeelManager ignora esta clave en
// contents/defaults, así que se escribe aquí.
const slide = ConfigFile("kwinrc", "Effect-slidingpopups");
slide.writeEntry("SlideInTime", @SLIDE_IN_MS@);
slide.writeEntry("SlideOutTime", @SLIDE_OUT_MS@);
dock.opacity = "translucent";
dock.height = DOCK_HEIGHT;

// Un solo plasmoid: Apps (la tecla Meta lo abre), apps fijadas y abiertas con
// ampliación, recientes y Papelera. El panel es más alto que la placa de
// vidrio (hueco para los iconos ampliados); la placa la dibuja el Panel.qml
// del shell GoldenGlass y el dock ajusta el grosor si cambian sus ajustes.
const dockWidget = dock.addWidget("org.goldenglass.dock");
dockWidget.currentConfigGroup = ["General"];
dockWidget.writeConfig("launchers", [
    "preferred://filemanager",
    "preferred://browser",
    "applications:org.kde.konsole.desktop",
    "applications:systemsettings.desktop",
]);

// --- Modo oscuro: el interruptor del Centro de control (DarkModeControl de
// Plasma) y el cambio automático día/noche alternan entre estos dos temas.
const lookAndFeel = ConfigFile("kdeglobals", "KDE");
lookAndFeel.writeEntry("DefaultLightLookAndFeel", "org.goldenglass.light.desktop");
lookAndFeel.writeEntry("DefaultDarkLookAndFeel", "org.goldenglass.dark.desktop");

// --- Spotlight: KRunner flotante y centrado ---------------------------------
const krunner = ConfigFile("krunnerrc", "General");
krunner.writeEntry("FreeFloating", true);

// --- Atajos de macOS (script de KWin org.goldenglass.shortcuts) -------------
// Ctrl+↑ Mission Control, Ctrl+↓ App Exposé.
ConfigFile("kwinrc", "Plugins").writeEntry("org.goldenglass.shortcutsEnabled", true);

// --- Escritorios por pantalla (Plasma ≥ 6.7) --------------------------------
// Como macOS: cada pantalla cambia de escritorio por su cuenta (Meta+Ctrl+←/→
// actúa en la pantalla con el foco). El script «Virtual Desktops Only on
// Primary» de kdeplasma-addons fija las ventanas de las demás pantallas y
// choca con esto: se desactiva.
ConfigFile("kwinrc", "Windows").writeEntry("PerOutputVirtualDesktops", @PER_SCREEN_DESKTOPS@);
if (@PER_SCREEN_DESKTOPS@) {
    ConfigFile("kwinrc", "Plugins").writeEntry("virtualdesktopsonlyonprimaryEnabled", false);
}
