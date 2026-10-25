/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Accessibility settings of the plasmoids, live (goldenglassrc
    [Accessibility], written by goldenglass-glass and goldenglass-windows).
    One reader per plasmoid, shared by Motion.qml and the glass:

        color: Qt.alpha(base, Accessibility.reduceTransparency ? 1 : alpha)

    The qmldir of the directory declares it a singleton; tools/plasmoids.py
    (SHARED) copies it with Motion.qml.
*/

pragma Singleton

import QtQuick

QtObject {
    readonly property Loader reader: Loader {
        source: "AccessibilityReader.qml"
    }
    readonly property bool reduceMotion: reader.item ? reader.item.reduceMotion : false
    readonly property bool reduceTransparency: reader.item ? reader.item.reduceTransparency : false
    readonly property bool showBorders: reader.item ? reader.item.showBorders : false
}
