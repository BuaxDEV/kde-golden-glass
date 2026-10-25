/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Icon theme switches seen by the plasmoid, for ThemedIcon.qml: revision
    grows once the new theme is loaded. One reader per plasmoid; without the
    org.goldenglass.glass module it stays at 0 and the icons keep the theme they
    painted until they are created again.

    The qmldir of the directory declares it a singleton; tools/plasmoids.py
    (SHARED) copies it with Motion.qml.
*/

pragma Singleton

import QtQuick

QtObject {
    readonly property Loader reader: Loader {
        source: "IconThemeReader.qml"
    }
    readonly property int revision: reader.item ? reader.item.revision : 0
}
