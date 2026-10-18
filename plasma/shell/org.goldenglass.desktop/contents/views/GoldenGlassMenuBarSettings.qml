/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Ajustes de la barra de menús para Panel.qml. Aparte porque el módulo
    org.goldenglass.glass viene con goldenglass-kstyle: si no está, falla solo
    este archivo (Panel.qml lo carga con un Loader).
*/

import QtQuick
import org.goldenglass.glass

Item {
    readonly property alias background: settings.background
    readonly property alias inactiveOpacity: settings.inactiveOpacity

    MenuBarSettings {
        id: settings
    }
}
