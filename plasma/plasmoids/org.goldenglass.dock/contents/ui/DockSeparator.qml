/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Línea vertical fina entre secciones del dock (como la de macOS antes de
    las recientes y de la Papelera).
*/

import QtQuick

import org.kde.kirigami as Kirigami
import "tokens.js" as T

Item {
    Rectangle {
        anchors.centerIn: parent
        width: 1
        height: parent.height * T.tokens.dock.separator_height
        color: Kirigami.Theme.textColor
        opacity: T.tokens.dock.separator_alpha
    }
}
