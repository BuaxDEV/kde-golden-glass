/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Fila con interruptor circular (acento cuando está activo), título y
    subtítulo. El círculo conmuta; el texto abre los ajustes (si hay).
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

RowLayout {
    id: row

    property string iconName
    property string title
    property string subtitle
    property bool checked: false
    property bool available: true
    property bool hasSettings: false

    signal toggled()
    signal settingsRequested()

    spacing: Kirigami.Units.smallSpacing * 2

    QQC2.AbstractButton {
        id: toggle
        enabled: row.available
        implicitWidth: Kirigami.Units.iconSizes.medium + Kirigami.Units.smallSpacing * 2
        implicitHeight: implicitWidth
        Accessible.name: row.title
        Accessible.role: Accessible.CheckBox
        Accessible.checked: row.checked
        onClicked: row.toggled()

        background: Rectangle {
            radius: width / 2
            color: row.checked ? Kirigami.Theme.highlightColor
                               : Qt.alpha(Kirigami.Theme.textColor, toggle.hovered ? 0.18 : 0.12)
            opacity: row.available ? 1 : 0.5
            Behavior on color { ColorAnimation { duration: Kirigami.Units.shortDuration } }
        }
        contentItem: Kirigami.Icon {
            source: row.iconName
            isMask: true
            color: row.checked ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
            implicitWidth: Kirigami.Units.iconSizes.small
            implicitHeight: implicitWidth
        }
    }

    MouseArea {
        Layout.fillWidth: true
        implicitHeight: labels.implicitHeight
        cursorShape: row.hasSettings ? Qt.PointingHandCursor : Qt.ArrowCursor
        enabled: row.hasSettings
        onClicked: row.settingsRequested()

        ColumnLayout {
            id: labels
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: 0
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                text: row.title
                font.weight: Font.DemiBold
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
    }
}
