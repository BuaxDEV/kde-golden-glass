/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Píldora de dos celdas (Wi‑Fi, Bluetooth, KDE Connect, Enfoque): círculo que
    conmuta, título y subtítulo. El texto abre su vista de detalle (si hay).
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

import "tokens.js" as T

Tile {
    id: pill

    property string iconName
    property string title
    property string subtitle
    property bool checked: false
    property bool available: true
    property bool hasDetail: false

    signal toggled()
    signal detailRequested()

    readonly property var cc: T.tokens.control_center
    // margen del círculo: el mismo arriba, abajo y a la izquierda
    readonly property real inset: (cc.cell - cc.icon_circle) / 2

    implicitWidth: 2 * cc.cell + cc.gap
    implicitHeight: cc.cell
    radius: height / 2

    CircleButton {
        id: circle
        anchors.left: parent.left
        anchors.leftMargin: pill.inset
        anchors.verticalCenter: parent.verticalCenter
        iconName: pill.iconName
        text: pill.title
        active: pill.checked
        enabled: pill.available
        onClicked: pill.toggled()
    }

    MouseArea {
        anchors.left: circle.right
        anchors.leftMargin: Kirigami.Units.smallSpacing * 2
        anchors.right: parent.right
        anchors.rightMargin: pill.inset
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        enabled: pill.hasDetail
        cursorShape: pill.hasDetail ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: pill.detailRequested()

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                text: pill.title
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: text.length > 0
                text: pill.subtitle
                opacity: 0.7
                font: Kirigami.Theme.smallFont
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
        }
    }
}
