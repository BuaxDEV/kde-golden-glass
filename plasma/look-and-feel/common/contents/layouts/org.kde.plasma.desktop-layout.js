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

// Launchpad primero (como en macOS); la tecla Meta también lo abre.
dock.addWidget("org.goldenglass.launchpad");

const tasks = dock.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "preferred://filemanager",
    "preferred://browser",
    "applications:org.kde.konsole.desktop",
    "applications:systemsettings.desktop",
]);
tasks.writeConfig("showOnlyCurrentDesktop", false);
tasks.writeConfig("taskHoverEffect", false);
tasks.writeConfig("iconSpacing", 1);

dock.addWidget("org.kde.plasma.marginsseparator");
dock.addWidget("org.kde.plasma.trash");

// --- Modo oscuro: el interruptor del Centro de control (DarkModeControl de
// Plasma) y el cambio automático día/noche alternan entre estos dos temas.
const lookAndFeel = ConfigFile("kdeglobals", "KDE");
lookAndFeel.writeEntry("DefaultLightLookAndFeel", "org.goldenglass.light.desktop");
lookAndFeel.writeEntry("DefaultDarkLookAndFeel", "org.goldenglass.dark.desktop");

// --- Spotlight: KRunner flotante y centrado ---------------------------------
const krunner = ConfigFile("krunnerrc", "General");
krunner.writeEntry("FreeFloating", true);
