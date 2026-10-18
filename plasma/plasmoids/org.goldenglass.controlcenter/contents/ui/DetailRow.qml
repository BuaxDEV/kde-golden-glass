/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Fila de una vista de detalle, como las listas de macOS 26 (redes,
    dispositivos, salidas de sonido): círculo con el glifo (de acento si está
    activo), nombre, subtítulo opcional y un icono o indicador al final.
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

import "tokens.js" as T

QQC2.AbstractButton {
    id: row

    property string iconName
    property bool active: false
    property string subtitle
    property string trailingIcon
    property bool busy: false
    // sin icono, alineada con el texto de las filas que sí lo llevan
    property bool indented: false

    readonly property var cc: T.tokens.control_center

    Layout.fillWidth: true
    implicitHeight: cc.row_height
    hoverEnabled: true
    Accessible.name: text

    background: Rectangle {
        radius: row.cc.row_radius
        color: row.hovered ? Qt.alpha(Kirigami.Theme.textColor, row.cc.row_hover_alpha) : "transparent"
    }

    leftPadding: indented ? cc.row_circle + Kirigami.Units.smallSpacing * 2 : 0

    contentItem: RowLayout {
        spacing: Kirigami.Units.smallSpacing * 2

        Rectangle {
            visible: row.iconName.length > 0
            implicitWidth: row.cc.row_circle
            implicitHeight: implicitWidth
            radius: width / 2
            color: row.active ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor, row.cc.off_alpha)

            Kirigami.Icon {
                anchors.centerIn: parent
                width: row.cc.row_icon
                height: width
                roundToIconSize: false
                source: row.iconName
                isMask: true
                color: row.active ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                text: row.text
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: text.length > 0
                text: row.subtitle
                opacity: 0.7
                font: Kirigami.Theme.smallFont
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
        }

        PlasmaComponents3.BusyIndicator {
            visible: row.busy
            running: visible
            implicitWidth: Kirigami.Units.iconSizes.small
            implicitHeight: implicitWidth
        }

        Kirigami.Icon {
            visible: row.trailingIcon.length > 0 && !row.busy
            implicitWidth: Kirigami.Units.iconSizes.small
            implicitHeight: implicitWidth
            source: row.trailingIcon
            isMask: true
            color: Kirigami.Theme.textColor
            opacity: 0.6
        }
    }
}
