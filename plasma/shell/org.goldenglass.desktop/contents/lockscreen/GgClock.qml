/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Reloj de la pantalla de bloqueo estilo macOS: fecha encima y hora grande.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami

import "tokens.js" as T

ColumnLayout {
    id: clock

    // WallpaperFader ajusta la opacidad de la sombra al mostrar/ocultar la UI.
    property Item shadow
    property date now: new Date()

    spacing: 0

    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: clock.now = new Date()
    }

    PlasmaComponents3.Label {
        Layout.alignment: Qt.AlignHCenter
        text: Qt.locale().toString(clock.now, "dddd d MMMM")
        textFormat: Text.PlainText
        color: Kirigami.Theme.textColor
        opacity: T.tokens.lock_screen.clock_alpha
        font.pointSize: Kirigami.Theme.defaultFont.pointSize * T.tokens.lock_screen.date_scale
        font.weight: Font.DemiBold
        font.capitalization: Font.Capitalize
    }

    PlasmaComponents3.Label {
        Layout.alignment: Qt.AlignHCenter
        text: Qt.locale().toString(clock.now, Qt.locale().timeFormat(Locale.ShortFormat).replace(/\s*[aApP]+$/, ""))
        textFormat: Text.PlainText
        color: Kirigami.Theme.textColor
        opacity: T.tokens.lock_screen.clock_alpha
        font.pointSize: Kirigami.Theme.defaultFont.pointSize * T.tokens.lock_screen.clock_scale
        font.weight: Font.Bold
    }
}
