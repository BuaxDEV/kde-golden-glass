/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Lo que se está reproduciendo (MPRIS): carátula, título, artista y controles.
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.private.mpris as Mpris

Tile {
    id: tile

    required property var player
    readonly property bool playing: player && player.playbackStatus === Mpris.PlaybackStatus.Playing

    RowLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.largeSpacing

        Item {
            implicitWidth: Kirigami.Units.iconSizes.large
            implicitHeight: implicitWidth
            Image {
                id: cover
                anchors.fill: parent
                source: tile.player ? tile.player.artUrl : ""
                sourceSize.width: width * 2
                sourceSize.height: height * 2
                fillMode: Image.PreserveAspectCrop
                visible: status === Image.Ready
                asynchronous: true
            }
            Kirigami.Icon {
                anchors.fill: parent
                visible: cover.status !== Image.Ready
                source: "media-album-cover"
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                text: tile.player && tile.player.track.length > 0 ? tile.player.track : (tile.player ? tile.player.identity : "")
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: text.length > 0
                text: tile.player ? tile.player.artist : ""
                opacity: 0.7
                font: Kirigami.Theme.smallFont
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
        }

        PlasmaComponents3.ToolButton {
            icon.name: "media-skip-backward"
            display: QQC2.AbstractButton.IconOnly
            text: i18n("Previous")
            enabled: tile.player && tile.player.canGoPrevious
            onClicked: tile.player.Previous()
        }
        PlasmaComponents3.ToolButton {
            icon.name: tile.playing ? "media-playback-pause" : "media-playback-start"
            display: QQC2.AbstractButton.IconOnly
            text: tile.playing ? i18n("Pause") : i18n("Play")
            enabled: tile.player && (tile.playing ? tile.player.canPause : tile.player.canPlay)
            onClicked: tile.player.PlayPause()
        }
        PlasmaComponents3.ToolButton {
            icon.name: "media-skip-forward"
            display: QQC2.AbstractButton.IconOnly
            text: i18n("Next")
            enabled: tile.player && tile.player.canGoNext
            onClicked: tile.player.Next()
        }
    }
}
