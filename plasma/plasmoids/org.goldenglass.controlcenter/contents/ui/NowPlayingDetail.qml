/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Reproducción en detalle, como en macOS 26: carátula, título, artista y
    app, progreso con el tiempo (se puede mover si el reproductor lo permite) y
    controles grandes. La carátula trae el reproductor al frente.
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.private.mpris as Mpris

import "tokens.js" as T

DetailView {
    id: view

    property var player: null
    readonly property bool hasPlayer: player !== null && player !== undefined
    readonly property bool playing: hasPlayer && player.playbackStatus === Mpris.PlaybackStatus.Playing

    signal raised()

    title: hasPlayer ? player.identity : i18n("Now Playing")

    // la posición solo se actualiza sola mientras suena
    Timer {
        interval: 1000
        repeat: true
        running: view.playing
        onTriggered: if (view.hasPlayer) view.player.updatePosition()
    }

    function time(microseconds) {
        const seconds = Math.max(0, Math.floor(microseconds / 1e6));
        const minutes = Math.floor(seconds / 60);
        return minutes + ":" + String(seconds % 60).padStart(2, "0");
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin: Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.largeSpacing

        Rectangle {
            implicitWidth: T.tokens.control_center.cell
            implicitHeight: implicitWidth
            radius: Kirigami.Units.cornerRadius * 2
            color: Qt.alpha(Kirigami.Theme.textColor, T.tokens.control_center.off_alpha)

            Kirigami.ShadowedImage {
                id: cover
                anchors.fill: parent
                radius: parent.radius
                source: view.hasPlayer ? view.player.artUrl : ""
                sourceSize.width: width * 2
                sourceSize.height: height * 2
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                visible: status === Image.Ready
            }
            Kirigami.Icon {
                anchors.centerIn: parent
                width: Kirigami.Units.iconSizes.medium
                height: width
                visible: view.hasPlayer && cover.status !== Image.Ready
                source: view.hasPlayer ? view.player.iconName : ""
            }
            MouseArea {
                anchors.fill: parent
                enabled: view.hasPlayer && view.player.canRaise
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: {
                    view.player.Raise();
                    view.raised();
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                text: !view.hasPlayer ? i18n("Not Playing")
                    : view.player.track.length > 0 ? view.player.track : view.player.identity
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: text.length > 0
                text: view.hasPlayer ? view.player.artist : ""
                opacity: T.tokens.text.secondary_alpha
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: text.length > 0
                text: view.hasPlayer ? view.player.album : ""
                opacity: T.tokens.text.secondary_alpha
                font: Kirigami.Theme.smallFont
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
        }
    }

    ColumnLayout {
        visible: view.hasPlayer && view.player.length > 0
        Layout.fillWidth: true
        Layout.leftMargin: Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        spacing: 0

        GlassSlider {
            id: progress
            Layout.fillWidth: true
            enabled: view.hasPlayer && view.player.canSeek
            wheelEnabled: false
            from: 0
            to: view.hasPlayer ? view.player.length : 0
            // el reproductor puede cerrarse mientras se arrastra
            onPressedChanged: if (!pressed && view.hasPlayer) view.player.position = value

            Binding on value {
                value: view.hasPlayer ? view.player.position : 0
                when: !progress.pressed
            }
        }
        RowLayout {
            Layout.fillWidth: true
            PlasmaComponents3.Label {
                text: view.time(progress.value)
                opacity: T.tokens.text.secondary_alpha
                font: Kirigami.Theme.smallFont
            }
            Item { Layout.fillWidth: true }
            PlasmaComponents3.Label {
                text: "-" + view.time(progress.to - progress.value)
                opacity: T.tokens.text.secondary_alpha
                font: Kirigami.Theme.smallFont
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
            implicitHeight: Kirigami.Units.iconSizes.medium + Kirigami.Units.smallSpacing * 2
            display: QQC2.AbstractButton.IconOnly
            Accessible.name: text
            contentItem: Kirigami.Icon {
                source: mediaButton.iconName
                implicitWidth: Kirigami.Units.iconSizes.medium
                implicitHeight: implicitWidth
                isMask: true
                color: Kirigami.Theme.textColor
                opacity: !mediaButton.enabled ? T.tokens.control_center.media_disabled_alpha
                             : mediaButton.pressed ? T.tokens.control_center.media_pressed_alpha : 1
            }
        }

        MediaButton {
            iconName: "media-skip-backward"
            text: i18n("Previous")
            enabled: view.hasPlayer && view.player.canGoPrevious
            onClicked: view.player.Previous()
        }
        MediaButton {
            iconName: view.playing ? "media-playback-pause" : "media-playback-start"
            text: view.playing ? i18n("Pause") : i18n("Play")
            enabled: view.hasPlayer && (view.playing ? view.player.canPause : view.player.canPlay)
            onClicked: view.player.PlayPause()
        }
        MediaButton {
            iconName: "media-skip-forward"
            text: i18n("Next")
            enabled: view.hasPlayer && view.player.canGoNext
            onClicked: view.player.Next()
        }
    }
}
