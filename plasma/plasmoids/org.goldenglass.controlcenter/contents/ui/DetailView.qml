/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Vista de detalle de un módulo (Wi‑Fi, Bluetooth, Enfoque, Pantalla, Sonido,
    Reproducción), como en macOS 26: una sola tarjeta de vidrio con el título
    (y su interruptor), el contenido y, abajo, «Ajustes de…». Sustituye a la
    cuadrícula hasta que se cierra el Centro de control o se pulsa Esc.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

import "tokens.js" as T

Tile {
    id: view

    property string title
    property bool hasSwitch: false
    property bool checked: false
    property bool switchEnabled: true
    property string footerText
    default property alias body: bodyColumn.data

    signal toggled()
    signal footerClicked()

    readonly property var cc: T.tokens.control_center
    readonly property real padding: (cc.cell - cc.icon_circle) / 2

    implicitWidth: 4 * cc.cell + 3 * cc.gap
    implicitHeight: column.implicitHeight + 2 * padding

    ColumnLayout {
        id: column
        anchors.fill: parent
        anchors.margins: view.padding
        spacing: Kirigami.Units.smallSpacing * 2

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing * 2

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                text: view.title
                font.weight: Font.Bold
                font.pointSize: Kirigami.Theme.defaultFont.pointSize * view.cc.detail_title_scale
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            MacSwitch {
                visible: view.hasSwitch
                enabled: view.switchEnabled
                checked: view.checked
                Accessible.name: view.title
                onToggled: view.toggled()
            }
        }

        // el contenido se desplaza si no cabe (listas de redes largas)
        PlasmaComponents3.ScrollView {
            id: scroll
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(bodyColumn.implicitHeight, view.cc.detail_max_height)
            contentWidth: availableWidth
            PlasmaComponents3.ScrollBar.horizontal.policy: PlasmaComponents3.ScrollBar.AlwaysOff

            ColumnLayout {
                id: bodyColumn
                width: scroll.availableWidth
                spacing: Kirigami.Units.smallSpacing / 2
            }
        }

        Rectangle {
            visible: view.footerText.length > 0
            Layout.fillWidth: true
            implicitHeight: 1
            color: Qt.alpha(Kirigami.Theme.textColor, view.cc.separator_alpha)
        }
        DetailRow {
            visible: view.footerText.length > 0
            text: view.footerText
            onClicked: view.footerClicked()
        }
    }
}
