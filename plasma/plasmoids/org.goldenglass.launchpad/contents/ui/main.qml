/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Apps: icono en el dock que abre un panel centrado con todas las
    aplicaciones (buscador, categorías, sugeridas, cuadrícula o lista), como
    Apps de macOS 26/27. Se declara como lanzador
    (org.kde.plasma.launchermenu): la tecla Meta lo abre.

    Los datos y el panel están en AppsLauncher.qml, que comparte con el dock.
*/

import QtQuick
import QtQml

import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    // El icono es la representación «completa»: no hay popup, sino panel.
    preferredRepresentation: fullRepresentation
    toolTipMainText: Plasmoid.title
    toolTipSubText: ""

    AppsLauncher {
        id: apps
        plasmoidItem: root
    }

    function toggle() {
        apps.toggle();
    }

    Connections {
        target: Plasmoid
        function onActivated(): void {
            root.toggle();
        }
    }

    fullRepresentation: MouseArea {
        id: icon
        hoverEnabled: true
        onClicked: root.toggle()

        // Icono del tema GoldenGlass (claro u oscuro según el tema de iconos)
        Kirigami.Icon {
            anchors.fill: parent
            source: "goldenglass-apps"
            fallback: "view-app-grid"
            active: icon.containsMouse
        }
    }
}
