/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Módulo «Vidrio»: control de transparencia como el de macOS 27. Tres
    muescas (más claro, medio, más opaco) y cualquier valor intermedio; se
    aplica en vivo al soltar el control.
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    id: root

    // Imán: al soltar cerca de una muesca, el valor queda exactamente en ella.
    function snapped(value) {
        for (const notch of kcm.notches) {
            if (Math.abs(value - notch) < kcm.snapDistance) {
                return notch;
            }
        }
        return value;
    }

    function apply() {
        const value = root.snapped(slider.value);
        slider.value = value;
        kcm.applyLevel(value);
    }

    Connections {
        target: kcm
        function onLevelChanged() {
            if (!slider.pressed) {
                slider.value = kcm.level;
            }
        }
    }

    // Con el teclado no hay «soltar»: se aplica tras una pausa.
    Timer {
        id: keyboardDelay
        interval: kcm.keyboardApplyDelay
        onTriggered: root.apply()
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            type: Kirigami.MessageType.Error
            visible: kcm.errorText.length > 0
            text: kcm.errorText
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            ColumnLayout {
                Kirigami.FormData.label: i18nc("@label:slider", "Glass:")
                spacing: Kirigami.Units.smallSpacing

                Item {
                    implicitWidth: Kirigami.Units.gridUnit * 20
                    implicitHeight: slider.implicitHeight + notchRow.height

                    QQC2.Slider {
                        id: slider
                        width: parent.width
                        from: 0
                        to: 1
                        value: kcm.level
                        Accessible.name: i18nc("@label:slider", "Glass")
                        onPressedChanged: {
                            if (!pressed) {
                                root.apply();
                            }
                        }
                        onMoved: {
                            if (!pressed) {
                                keyboardDelay.restart();
                            }
                        }
                    }

                    // Marcas de las muescas bajo la pista.
                    Item {
                        id: notchRow
                        anchors.top: slider.bottom
                        x: slider.leftPadding
                        width: slider.availableWidth
                        height: Kirigami.Units.smallSpacing * 2

                        Repeater {
                            model: kcm.notches
                            Rectangle {
                                required property real modelData
                                x: modelData * notchRow.width - width / 2
                                width: 2
                                height: notchRow.height
                                radius: 1
                                color: Kirigami.Theme.disabledTextColor
                            }
                        }
                    }
                }

                // Extremos a los lados y «Por defecto» bajo el nivel de fábrica
                // (token glass.default_level), sin salirse de la fila.
                Item {
                    id: labelRow
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 20
                    implicitHeight: defaultLabel.implicitHeight

                    QQC2.Label {
                        anchors.left: parent.left
                        text: i18nc("@item:inrange glass level", "Clearer")
                    }
                    QQC2.Label {
                        id: defaultLabel
                        x: Math.max(0, Math.min(labelRow.width - width,
                            slider.leftPadding + kcm.defaultLevel * slider.availableWidth - width / 2))
                        text: i18nc("@item:inrange glass level", "Default")
                    }
                    QQC2.Label {
                        anchors.right: parent.right
                        text: i18nc("@item:inrange glass level", "More opaque")
                    }
                }
            }

            RowLayout {
                spacing: Kirigami.Units.smallSpacing
                opacity: kcm.busy ? 1 : 0
                Behavior on opacity {
                    NumberAnimation {
                        duration: Kirigami.Units.shortDuration
                    }
                }
                QQC2.BusyIndicator {
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: implicitWidth
                    running: kcm.busy
                }
                QQC2.Label {
                    text: i18nc("@info:status", "Applying…")
                }
            }

            Item {
                Kirigami.FormData.isSection: true
            }

            QQC2.Switch {
                Kirigami.FormData.label: i18nc("@label", "Refraction:")
                text: i18nc("@option:check", "Bend the background at the edges of the glass")
                enabled: kcm.refractionAvailable
                checked: kcm.refraction
                onToggled: kcm.refraction = checked
            }
            QQC2.Label {
                Layout.maximumWidth: Kirigami.Units.gridUnit * 20
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: kcm.refractionAvailable
                    ? i18nc("@info", "Like Liquid Glass: the dock, menu bar and popups bend what is behind them, more with clearer glass. Turn it off if the graphics card struggles.")
                    : i18nc("@info", "Not available: KWin did not load the GoldenGlass effect. Rebuild goldenglass-kstyle after updating KWin.")
            }

            Item {
                Kirigami.FormData.isSection: true
            }

            QQC2.Switch {
                Kirigami.FormData.label: i18nc("@label", "Menu bar:")
                text: i18nc("@option:check", "Show menu bar background")
                checked: kcm.menubarBackground
                onToggled: kcm.menubarBackground = checked
            }
            QQC2.Label {
                Layout.maximumWidth: Kirigami.Units.gridUnit * 20
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: i18nc("@info", "Off, like macOS: the menu bar is drawn straight over the wallpaper. On: a strip of glass behind it.")
            }

            Item {
                Kirigami.FormData.isSection: true
            }

            QQC2.Switch {
                Kirigami.FormData.label: i18nc("@label", "Accessibility:")
                text: i18nc("@option:check", "Reduce motion")
                checked: kcm.reduceMotion
                onToggled: kcm.reduceMotion = checked
            }
            QQC2.Label {
                Layout.maximumWidth: Kirigami.Units.gridUnit * 20
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: i18nc("@info", "Windows, the dock and panels fade in and out instead of zooming, sliding or bouncing.")
            }
        }

        QQC2.Label {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 30
            Layout.alignment: Qt.AlignHCenter
            wrapMode: Text.WordWrap
            color: Kirigami.Theme.disabledTextColor
            text: i18nc("@info", "Changes the glass of the menu bar, the dock, popups, window title bars, toolbars, sidebars and menus. A clearer glass shows more of what is behind; a more opaque glass is easier to read.")
        }
    }
}
