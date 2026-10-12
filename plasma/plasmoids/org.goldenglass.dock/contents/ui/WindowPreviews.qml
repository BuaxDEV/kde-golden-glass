/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Contenido del tooltip de una app con ventanas: su nombre y una miniatura
    en vivo por ventana (captura de KWin por PipeWire, como el gestor de
    tareas de Plasma) con el título debajo. Clic en una miniatura: activa esa
    ventana. Sin captura (o mientras llega), el icono de la app.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.pipewire as PipeWire
import org.kde.plasma.components as PlasmaComponents3
import org.kde.taskmanager as TaskManager

import "tokens.js" as T

ColumnLayout {
    id: previews

    required property var tasks             // TasksModel (ver TaskMenu.qml)
    required property string appName
    required property var appIcon
    // [{ index (QModelIndex persistente), title, winId, active }]
    required property var windows
    signal activated

    readonly property real thumbWidth: T.tokens.dock.preview_width
    spacing: Kirigami.Units.smallSpacing

    PlasmaComponents3.Label {
        Layout.alignment: Qt.AlignHCenter
        text: previews.appName
        font.weight: Font.DemiBold
    }

    RowLayout {
        spacing: Kirigami.Units.largeSpacing

        Repeater {
            model: previews.windows
            delegate: ColumnLayout {
                id: entry
                required property var modelData
                spacing: Kirigami.Units.smallSpacing

                Rectangle {
                    Layout.preferredWidth: previews.thumbWidth
                    Layout.preferredHeight: previews.thumbWidth * 10 / 16
                    radius: Kirigami.Units.cornerRadius
                    color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b,
                                   hover.hovered ? 0.16 : 0.06)
                    border.width: entry.modelData.active ? 2 : 0
                    border.color: Kirigami.Theme.highlightColor

                    TaskManager.ScreencastingRequest {
                        id: cast
                        uuid: entry.modelData.winId
                    }
                    PipeWire.PipeWireSourceItem {
                        id: thumbnail
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.smallSpacing
                        nodeId: cast.nodeId
                        visible: nodeId > 0
                    }
                    Kirigami.Icon {
                        anchors.centerIn: parent
                        width: Kirigami.Units.iconSizes.large
                        height: width
                        visible: !thumbnail.visible
                        source: previews.appIcon
                    }

                    HoverHandler {
                        id: hover
                    }
                    TapHandler {
                        onTapped: {
                            previews.tasks.requestActivate(entry.modelData.index);
                            previews.activated();
                        }
                    }
                }

                PlasmaComponents3.Label {
                    Layout.preferredWidth: previews.thumbWidth
                    horizontalAlignment: Text.AlignHCenter
                    text: entry.modelData.title
                    elide: Text.ElideRight
                    font: Kirigami.Theme.smallFont
                }
            }
        }
    }
}
