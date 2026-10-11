/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Tarjeta del Centro de control: rectángulo redondeado sobre el vidrio del
    popup, ligeramente más claro/oscuro que el fondo (como en macOS).
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami

Rectangle {
    id: tile

    default property alias content: inner.data
    property real padding: Kirigami.Units.largeSpacing

    implicitWidth: inner.implicitWidth + 2 * padding
    implicitHeight: inner.implicitHeight + 2 * padding
    radius: Kirigami.Units.cornerRadius * 2.5
    color: Qt.alpha(Kirigami.Theme.textColor, 0.07)
    border.width: 1
    border.color: Qt.alpha(Kirigami.Theme.textColor, 0.08)

    ColumnLayout {
        id: inner
        anchors.fill: parent
        anchors.margins: tile.padding
        spacing: Kirigami.Units.largeSpacing
    }
}
