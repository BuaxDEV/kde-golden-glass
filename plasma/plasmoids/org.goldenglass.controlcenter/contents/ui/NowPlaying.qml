/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Reproducción (MPRIS), tarjeta de 2 × 2 celdas como en macOS 26: carátula,
    título y artista arriba y los controles abajo. Sin reproductor muestra
    «Sin reproducción» con los controles apagados. Un clic fuera de los
    controles abre su vista de detalle.
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.private.mpris as Mpris

import "tokens.js" as T

Tile {
    id: tile

    property var player: null
    readonly property bool hasPlayer: player !== null && player !== undefined
    readonly property bool playing: hasPlayer && player.playbackStatus === Mpris.PlaybackStatus.Playing

    signal detailRequested()

    readonly property var cc: T.tokens.control_center
    readonly property real padding: (cc.cell - cc.icon_circle) / 2

    implicitWidth: 2 * cc.cell + cc.gap
    implicitHeight: 2 * cc.cell + cc.gap

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: tile.padding
        spacing: Kirigami.Units.smallSpacing

        MouseArea {
            Layout.fillWidth: true
            Layout.fillHeight: true
            cursorShape: Qt.PointingHandCursor
            onClicked: tile.detailRequested()

            ColumnLayout {
                anchors.fill: parent
                spacing: Kirigami.Units.smallSpacing

                Rectangle {
                    implicitWidth: tile.cc.icon_circle + Kirigami.Units.smallSpacing * 2
                    implicitHeight: implicitWidth
                    radius: Kirigami.Units.cornerRadius * 2
                    color: Qt.alpha(Kirigami.Theme.textColor, tile.cc.off_alpha)

                    Kirigami.ShadowedImage {
                        id: cover
                        anchors.fill: parent
                        radius: parent.radius
                        source: tile.hasPlayer ? tile.player.artUrl : ""
                        sourceSize.width: width * 2
                        sourceSize.height: height * 2
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        visible: status === Image.Ready
                    }
                    Kirigami.Icon {
                        anchors.centerIn: parent
                        width: Kirigami.Units.iconSizes.small
                        height: width
                        visible: tile.hasPlayer && cover.status !== Image.Ready
                        source: tile.hasPlayer ? tile.player.iconName : ""
                    }
                }

                Item { Layout.fillHeight: true }

                PlasmaComponents3.Label {
                    Layout.fillWidth: true
                    text: !tile.hasPlayer ? i18n("Not Playing")
                        : tile.player.track.length > 0 ? tile.player.track : tile.player.identity
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                }
                PlasmaComponents3.Label {
                    Layout.fillWidth: true
                    visible: text.length > 0
                    text: tile.hasPlayer ? tile.player.artist : ""
                    opacity: 0.7
                    font: Kirigami.Theme.smallFont
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 0

            component MediaButton: QQC2.AbstractButton {
                id: mediaButton
                property string iconName
                Layout.fillWidth: true
                implicitHeight: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing
                display: QQC2.AbstractButton.IconOnly
                hoverEnabled: true
                Accessible.name: text
                contentItem: Kirigami.Icon {
                    source: mediaButton.iconName
                    implicitWidth: Kirigami.Units.iconSizes.smallMedium
                    implicitHeight: implicitWidth
                    isMask: true
                    color: Kirigami.Theme.textColor
                    opacity: !mediaButton.enabled ? 0.35 : mediaButton.pressed ? 0.6 : 1
                }
            }

            MediaButton {
                iconName: "media-skip-backward"
                text: i18n("Previous")
                enabled: tile.hasPlayer && tile.player.canGoPrevious
                onClicked: tile.player.Previous()
            }
            MediaButton {
                iconName: tile.playing ? "media-playback-pause" : "media-playback-start"
                text: tile.playing ? i18n("Pause") : i18n("Play")
                enabled: tile.hasPlayer && (tile.playing ? tile.player.canPause : tile.player.canPlay)
                onClicked: tile.player.PlayPause()
            }
            MediaButton {
                iconName: "media-skip-forward"
                text: i18n("Next")
                enabled: tile.hasPlayer && tile.player.canGoNext
                onClicked: tile.player.Next()
            }
        }
    }
}
