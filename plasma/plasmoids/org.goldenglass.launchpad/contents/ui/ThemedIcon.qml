/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Kirigami.Icon that follows an icon theme switch (an icon style chosen in
    «Estilo de iconos», a global theme): give it themedSource instead of source.
    Kirigami.Icon keeps the icon it painted until its palette or its source
    changes, so after each switch the source is set again and the icon of the
    new theme fades in. tools/plasmoids.py (SHARED) copies it with Motion.qml.
*/

import QtQuick
import org.kde.kirigami as Kirigami

Kirigami.Icon {
    id: icon

    property var themedSource

    source: themedSource

    Connections {
        target: IconTheme
        function onRevisionChanged() {
            icon.source = "";
            icon.source = Qt.binding(() => icon.themedSource);
        }
    }
}
