/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Módulo «Dock», como «Escritorio y Dock» de macOS: tamaño, ampliación (con
    su tamaño) y apps recientes. Todo se aplica al momento.
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    id: root

    // Deslizador con etiquetas en los extremos, como los de macOS.
    component LabeledSlider: ColumnLayout {
        id: labeled
        property alias from: slider.from
        property alias to: slider.to
        property alias value: slider.value
        property alias enabledSlider: slider.enabled
        property string minLabel
        property string maxLabel
        property string accessibleName
        signal moved(int value)
        spacing: 0

        QQC2.Slider {
            id: slider
            Layout.preferredWidth: Kirigami.Units.gridUnit * 18
            stepSize: 1
            Accessible.name: labeled.accessibleName
            onMoved: labeled.moved(Math.round(value))
        }
        RowLayout {
            Layout.preferredWidth: Kirigami.Units.gridUnit * 18
            QQC2.Label {
                Layout.fillWidth: true
                text: labeled.minLabel
                font: Kirigami.Theme.smallFont
                opacity: slider.enabled ? 0.8 : 0.4
            }
            QQC2.Label {
                text: labeled.maxLabel
                font: Kirigami.Theme.smallFont
                opacity: slider.enabled ? 0.8 : 0.4
            }
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            type: Kirigami.MessageType.Error
            visible: kcm.errorText.length > 0
            text: kcm.errorText
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            type: Kirigami.MessageType.Information
            visible: !kcm.available
            text: i18nc("@info", "There is no GoldenGlass dock in the panels. Apply a GoldenGlass global theme with “Desktop and window layout” checked to add it.")
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true
            enabled: kcm.available

            LabeledSlider {
                Kirigami.FormData.label: i18nc("@label:slider", "Size:")
                accessibleName: i18nc("@label:slider", "Size")
                from: 32
                to: 80
                value: kcm.iconSize
                minLabel: i18nc("@item:inrange dock size", "Small")
                maxLabel: i18nc("@item:inrange dock size", "Large")
                onMoved: value => kcm.iconSize = value
            }

            Item {
                Kirigami.FormData.isSection: true
            }

            QQC2.Switch {
                id: magnification
                Kirigami.FormData.label: i18nc("@label", "Magnification:")
                text: i18nc("@option:check", "Enlarge icons under the pointer")
                checked: kcm.magnification
                onToggled: kcm.magnification = checked
            }

            LabeledSlider {
                accessibleName: i18nc("@label:slider", "Magnification size")
                from: Math.max(kcm.iconSize, 48)
                to: 128
                value: kcm.magnificationSize
                enabledSlider: kcm.magnification
                minLabel: i18nc("@item:inrange magnification", "Small")
                maxLabel: i18nc("@item:inrange magnification", "Large")
                onMoved: value => kcm.magnificationSize = value
            }

            Item {
                Kirigami.FormData.isSection: true
            }

            QQC2.CheckBox {
                text: i18nc("@option:check", "Show recent apps in the Dock")
                checked: kcm.showRecent
                onToggled: kcm.showRecent = checked
            }
        }
    }
}
