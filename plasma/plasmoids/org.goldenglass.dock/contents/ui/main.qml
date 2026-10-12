/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Dock de GoldenGlass, como el de macOS: Apps, apps fijadas y abiertas,
    apps recientes y la Papelera en una sola fila, con ampliación bajo el
    cursor. Va en un panel de Plasma más alto que la placa de vidrio: la placa
    la dibuja el Panel.qml del shell GoldenGlass (DockView le pasa su
    geometría) y el resto del panel queda transparente para los iconos
    ampliados y el rebote.

    AppsLauncher.qml, AppsPanel.qml y categories.js vienen del plasmoid Apps y
    TrashButton.qml del de la Papelera (tools/plasmoids.py los copia).
*/

import QtQuick

import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Plasmoid.constraintHints: Plasmoid.CanFillArea

    AppsLauncher {
        id: appsLauncher
        plasmoidItem: root
    }

    // Meta abre Apps (X-Plasma-Provides: org.kde.plasma.launchermenu)
    Connections {
        target: Plasmoid
        function onActivated(): void {
            appsLauncher.toggle();
        }
    }

    fullRepresentation: DockView {
        plasmoidItem: root
        apps: appsLauncher
    }
}
