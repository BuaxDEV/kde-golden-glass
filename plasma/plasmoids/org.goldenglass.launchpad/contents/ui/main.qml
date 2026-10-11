/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Launchpad: icono en el dock que abre una cuadrícula de apps a pantalla
    completa (ventana DashboardWindow de Plasma, con blur detrás). Se declara
    como lanzador (org.kde.plasma.launchermenu): la tecla Meta lo abre.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid
import org.kde.plasma.private.kicker as Kicker

PlasmoidItem {
    id: root

    // El icono es la representación «completa»: no hay popup, sino ventana.
    preferredRepresentation: fullRepresentation
    toolTipMainText: Plasmoid.title
    toolTipSubText: ""

    // Como el lanzador a pantalla completa de Plasma: RootModel con solo
    // «Todas las aplicaciones», que es la lista plana y ordenada (un AppsModel
    // sin ruta mostraría las categorías del menú).
    Kicker.RootModel {
        id: rootModel
        autoPopulate: false
        appletInterface: root
        appNameFormat: 0 // solo el nombre de la app
        flat: true
        sorted: true
        showSeparators: false
        showTopLevelItems: false
        showAllApps: true
        showAllAppsCategorized: false
        showRecentApps: false
        showRecentDocs: false
        showRecentFolders: false
        showPowerSession: false
        showFavoritesPlaceholder: false
        onRefreshed: root.appsModel = rowCount() > 0 ? modelForRow(0) : null
        Component.onCompleted: refresh()
    }
    property var appsModel: null

    Kicker.RunnerModel {
        id: runnerModel
        appletInterface: root
        runners: ["krunner_services"]
        mergeResults: true
    }

    property LaunchpadWindow window: null

    function toggle() {
        if (!window) {
            window = windowComponent.createObject(root, {
                visualParent: fullRepresentationItem,
                appsModel: Qt.binding(() => root.appsModel),
                runnerModel: runnerModel,
            });
        }
        window.toggle();
    }

    Component {
        id: windowComponent
        LaunchpadWindow {}
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

        Kirigami.Icon {
            anchors.fill: parent
            source: Qt.resolvedUrl("../images/launchpad.svg")
            active: icon.containsMouse
        }
    }
}
