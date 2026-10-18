/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Pantalla en detalle, como en macOS 26: brillo de cada pantalla, modo
    oscuro, luz nocturna (Night Shift) y duplicar pantalla.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.private.brightnesscontrolplugin as Brightness

DetailView {
    id: view

    required property var brightnessControl
    required property bool nightLightAvailable
    required property bool nightLightOn

    signal nightLightToggled()
    signal mirroringRequested()
    signal settingsRequested()

    title: i18n("Display")
    footerText: i18n("Display Settings…")
    onFooterClicked: settingsRequested()

    Repeater {
        id: displays
        model: view.brightnessControl.isBrightnessAvailable ? view.brightnessControl.displays : null
        delegate: ColumnLayout {
            id: display
            required property string displayName
            required property string label
            required property int brightness
            required property int maxBrightness

            Layout.fillWidth: true
            Layout.leftMargin: Kirigami.Units.smallSpacing
            Layout.rightMargin: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: displays.count > 1
                text: display.label
                opacity: 0.7
                font: Kirigami.Theme.smallFont
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            SliderRow {
                id: brightnessRow
                Layout.fillWidth: true
                iconFrom: "brightness-low-symbolic"
                iconTo: "brightness-high-symbolic"
                from: 0
                to: display.maxBrightness
                onMoved: view.brightnessControl.setBrightness(display.displayName, Math.round(value))

                Binding on value {
                    value: display.brightness
                    when: !brightnessRow.pressed
                }
            }
        }
    }

    SectionLabel {
        text: i18n("Appearance")
    }
    DetailRow {
        text: i18n("Dark Mode")
        iconName: Qt.resolvedUrl("../images/dark-mode-symbolic.svg")
        active: Brightness.DarkModeControl.darkMode
        onClicked: Brightness.DarkModeControl.darkMode = !Brightness.DarkModeControl.darkMode
    }
    DetailRow {
        visible: view.nightLightAvailable
        text: i18n("Night Light")
        iconName: "redshift-status-on"
        active: view.nightLightOn
        onClicked: view.nightLightToggled()
    }
    DetailRow {
        text: i18n("Screen Mirroring")
        iconName: Qt.resolvedUrl("../images/screen-mirroring-symbolic.svg")
        onClicked: view.mirroringRequested()
    }
}
