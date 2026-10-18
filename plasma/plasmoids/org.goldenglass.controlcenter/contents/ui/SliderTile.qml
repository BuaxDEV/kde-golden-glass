/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Tarjeta a lo ancho con título y sus sliders (SliderRow, como hijos), como
    Pantalla y Sonido en macOS 26. Con hasDetail, un clic fuera de los
    sliders abre su vista de detalle.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

import "tokens.js" as T

Tile {
    id: tile

    property string title
    property bool hasDetail: false
    default property alias rows: column.data

    signal detailRequested()

    readonly property var cc: T.tokens.control_center
    readonly property real padding: (cc.cell - cc.icon_circle) / 2

    implicitWidth: 4 * cc.cell + 3 * cc.gap
    implicitHeight: column.implicitHeight + 2 * padding
    pressed: area.pressed
    pressPoint: Qt.point(area.mouseX, area.mouseY)

    MouseArea {
        id: area
        anchors.fill: parent
        enabled: tile.hasDetail
        cursorShape: Qt.PointingHandCursor
        onClicked: tile.detailRequested()
    }

    ColumnLayout {
        id: column
        anchors.fill: parent
        anchors.margins: tile.padding
        spacing: Kirigami.Units.smallSpacing * 2

        PlasmaComponents3.Label {
            Layout.fillWidth: true
            text: tile.title
            font.weight: Font.DemiBold
            elide: Text.ElideRight
            textFormat: Text.PlainText
        }
    }
}
