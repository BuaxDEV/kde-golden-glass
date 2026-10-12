/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Línea vertical fina entre secciones del dock (como la de macOS antes de
    las recientes y de la Papelera).
*/

import QtQuick

import org.kde.kirigami as Kirigami

Item {
    Rectangle {
        anchors.centerIn: parent
        width: 1
        height: parent.height * 0.78
        color: Kirigami.Theme.textColor
        opacity: 0.22
    }
}
