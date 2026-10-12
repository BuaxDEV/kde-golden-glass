/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Módulo «Efectos de sonido», como el apartado de Sonido de macOS: sonidos
    de cristal de GoldenGlass y sonido al iniciar sesión. Cada interruptor se
    aplica al momento con goldenglass-system.
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    id: root

    component PreviewButton: QQC2.ToolButton {
        property string sound
        icon.name: "media-playback-start"
        enabled: kcm.themeInstalled
        display: QQC2.AbstractButton.IconOnly
        text: i18nc("@action:button", "Listen")
        QQC2.ToolTip.text: text
        QQC2.ToolTip.visible: hovered
        QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
        onClicked: kcm.preview(sound)
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
            visible: !kcm.themeInstalled
            text: i18nc("@info", "The GoldenGlass sound theme is not installed (goldenglass-sounds package).")
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            RowLayout {
                Kirigami.FormData.label: i18nc("@label", "Sound effects:")
                QQC2.Switch {
                    text: i18nc("@option:check", "Use GoldenGlass sounds")
                    checked: kcm.soundsEnabled
                    enabled: kcm.themeInstalled
                    onToggled: kcm.setPart("sounds", checked)
                }
                PreviewButton {
                    sound: "bell"
                }
            }

            RowLayout {
                QQC2.Switch {
                    text: i18nc("@option:check", "Play sound on login")
                    checked: kcm.chimeEnabled
                    onToggled: kcm.setPart("chime", checked)
                }
                PreviewButton {
                    sound: "desktop-login"
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
        }

        QQC2.Label {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 30
            Layout.alignment: Qt.AlignHCenter
            wrapMode: Text.WordWrap
            color: Kirigami.Theme.disabledTextColor
            text: i18nc("@info", "Glass sounds for alerts, notifications, emptying the trash, screenshots, volume changes, devices, battery and charger, and the timer alarm. Everything else stays silent, like on macOS.")
        }
    }
}
