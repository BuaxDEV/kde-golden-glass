/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Ventana del Launchpad: pantalla completa con blur (DashboardWindow),
    buscador arriba, páginas de apps ordenadas por filas como en macOS y
    puntos de página. Clic en el vacío, Escape o lanzar una app la cierran.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.private.kicker as Kicker

Kicker.DashboardWindow {
    id: window

    property var appsModel
    property var runnerModel

    readonly property real iconSize: Kirigami.Units.iconSizes.huge * 1.25
    readonly property real cellWidth: iconSize + Kirigami.Units.gridUnit * 4
    readonly property real cellHeight: iconSize + Kirigami.Units.gridUnit * 3
    readonly property int columns: Math.max(4, Math.min(7, Math.floor((width - Kirigami.Units.gridUnit * 8) / cellWidth)))
    readonly property int rows: Math.max(3, Math.min(5, Math.floor((height - Kirigami.Units.gridUnit * 14) / cellHeight)))
    readonly property int perPage: columns * rows
    readonly property int appCount: appsModel ? appsModel.count : 0
    readonly property bool searching: searchField.text.length > 0
    readonly property var resultsModel: runnerModel && runnerModel.count > 0 ? runnerModel.modelForRow(0) : null

    backgroundColor: "transparent"
    keyEventProxy: searchField

    function launch(model, row) {
        model.trigger(row, "", null);
        window.toggle();
    }

    onVisibleChanged: {
        if (visible) {
            searchField.clear();
            pages.currentIndex = 0;
            searchField.forceActiveFocus();
        }
    }

    onKeyEscapePressed: {
        if (searching) {
            searchField.clear();
        } else {
            window.toggle();
        }
    }

    mainItem: MouseArea {
        anchors.fill: parent
        onClicked: window.toggle()

        // Velo sobre el fondo difuminado.
        Rectangle {
            anchors.fill: parent
            color: Qt.rgba(0, 0, 0, 0.25)
        }

        PlasmaExtras.SearchField {
            id: searchField
            anchors.top: parent.top
            anchors.topMargin: Kirigami.Units.gridUnit * 3
            anchors.horizontalCenter: parent.horizontalCenter
            width: Kirigami.Units.gridUnit * 16
            onTextChanged: {
                if (window.runnerModel) {
                    window.runnerModel.query = text;
                }
            }
            onAccepted: {
                if (window.resultsModel && window.resultsModel.count > 0) {
                    window.launch(window.resultsModel, 0);
                }
            }
        }

        // Páginas de apps
        ListView {
            id: pages
            visible: !window.searching
            anchors {
                top: searchField.bottom
                topMargin: Kirigami.Units.gridUnit * 2
                bottom: dots.top
                bottomMargin: Kirigami.Units.gridUnit
                left: parent.left
                right: parent.right
            }
            clip: true
            orientation: ListView.Horizontal
            snapMode: ListView.SnapOneItem
            highlightRangeMode: ListView.StrictlyEnforceRange
            highlightMoveDuration: Kirigami.Units.longDuration
            boundsBehavior: Flickable.StopAtBounds
            model: Math.ceil(window.appCount / window.perPage)

            delegate: Item {
                required property int index
                width: pages.width
                height: pages.height

                AppGrid {
                    anchors.centerIn: parent
                    launchpad: window
                    model: window.appsModel
                    first: parent.index * window.perPage
                    count: Math.min(window.perPage, window.appCount - first)
                }
            }

            WheelHandler {
                onWheel: event => {
                    const delta = event.angleDelta.y !== 0 ? event.angleDelta.y : event.angleDelta.x;
                    if (delta < 0) {
                        pages.incrementCurrentIndex();
                    } else if (delta > 0) {
                        pages.decrementCurrentIndex();
                    }
                }
            }
        }

        // Resultados de búsqueda
        AppGrid {
            launchpad: window
            visible: window.searching
            anchors.top: searchField.bottom
            anchors.topMargin: Kirigami.Units.gridUnit * 2
            anchors.horizontalCenter: parent.horizontalCenter
            model: window.resultsModel
            first: 0
            count: window.resultsModel ? Math.min(window.perPage, window.resultsModel.count) : 0
        }

        // Puntos de página
        Row {
            id: dots
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Kirigami.Units.gridUnit * 7 // por encima del dock
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Kirigami.Units.largeSpacing
            visible: !window.searching && pages.count > 1

            Repeater {
                model: pages.count
                delegate: Rectangle {
                    required property int index
                    width: Kirigami.Units.smallSpacing * 2
                    height: width
                    radius: width / 2
                    color: Qt.rgba(1, 1, 1, index === pages.currentIndex ? 0.9 : 0.35)
                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -Kirigami.Units.smallSpacing
                        onClicked: pages.currentIndex = parent.index
                    }
                }
            }
        }
    }

    // Cuadrícula de `count` apps del modelo a partir de la fila `first`.
    // Los componentes en línea no ven los id del documento: la ventana se
    // pasa como propiedad.
    component AppGrid: Grid {
        id: grid
        property var launchpad
        property var model
        property int first: 0
        property int count: 0
        columns: launchpad.columns

        Repeater {
            model: grid.model ? grid.count : 0
            delegate: AppTile {
                required property int index
                launchpad: grid.launchpad
                appModel: grid.model
                row: grid.first + index
            }
        }
    }

    component AppTile: MouseArea {
        id: tile
        property var launchpad
        property var appModel
        property int row
        readonly property var modelIndex: appModel ? appModel.index(row, 0) : null

        width: tile.launchpad.cellWidth
        height: tile.launchpad.cellHeight
        hoverEnabled: true
        onClicked: tile.launchpad.launch(appModel, row)

        Rectangle {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            radius: Kirigami.Units.cornerRadius * 3
            color: Qt.rgba(1, 1, 1, tile.containsMouse ? 0.14 : 0)
        }

        ColumnLayout {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.largeSpacing * 2
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Icon {
                Layout.alignment: Qt.AlignHCenter
                implicitWidth: tile.launchpad.iconSize
                implicitHeight: tile.launchpad.iconSize
                source: tile.modelIndex ? tile.appModel.data(tile.modelIndex, Qt.DecorationRole) : ""
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: tile.modelIndex ? tile.appModel.data(tile.modelIndex, Qt.DisplayRole) : ""
                color: "white"
                style: Text.Raised
                styleColor: Qt.rgba(0, 0, 0, 0.35)
                elide: Text.ElideRight
                maximumLineCount: 1
                textFormat: Text.PlainText
            }
        }
    }
}
