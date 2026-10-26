/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    «Icon style» module, like macOS 27 Appearance › «Icon & widget style»:
    Default, Clear or Tinted app icons, light, dark or following the colour
    scheme. Each card previews its style with icons of the installed theme,
    painted by the KDE icon engine, so the Tinted ones show the system accent.
    Everything applies at once.
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    id: root

    component StyleCard: QQC2.AbstractButton {
        id: card
        property string styleId
        property string label
        readonly property var icons: kcm.previews[styleId] || []

        checkable: true
        checked: kcm.style === styleId
        enabled: kcm.available
        onClicked: kcm.style = styleId
        Accessible.name: label
        Layout.alignment: Qt.AlignTop
        implicitWidth: Kirigami.Units.gridUnit * 8
        implicitHeight: column.implicitHeight

        contentItem: ColumnLayout {
            id: column
            spacing: Kirigami.Units.smallSpacing

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: width
                radius: Kirigami.Units.cornerRadius
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: card.checked ? 2 : 1
                border.color: card.checked ? Kirigami.Theme.highlightColor : Kirigami.Theme.disabledTextColor

                Grid {
                    anchors.centerIn: parent
                    columns: 2
                    spacing: Kirigami.Units.largeSpacing
                    Repeater {
                        model: card.icons
                        Kirigami.Icon {
                            width: Kirigami.Units.iconSizes.large
                            height: width
                            // an absolute path still goes through the KDE icon engine, which paints the accent
                            source: modelData
                        }
                    }
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: card.label
                font.bold: card.checked
                elide: Text.ElideRight
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
            visible: kcm.available && !kcm.inFamily
            text: i18nc("@info", "The icon theme in use is not a GoldenGlass one. Choosing a style here switches to the GoldenGlass icons.")
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            RowLayout {
                Kirigami.FormData.label: i18nc("@label", "Style:")
                Kirigami.FormData.buddyFor: defaultCard
                spacing: Kirigami.Units.largeSpacing

                StyleCard {
                    id: defaultCard
                    styleId: "default"
                    label: i18nc("@option:radio icon style", "Default")
                }
                StyleCard {
                    styleId: "clear"
                    label: i18nc("@option:radio icon style", "Clear")
                }
                StyleCard {
                    styleId: "tinted"
                    label: i18nc("@option:radio icon style", "Tinted")
                }
            }

            QQC2.Label {
                Layout.maximumWidth: Kirigami.Units.gridUnit * 26
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: i18nc("@info", "Clear icons are glass with a white symbol. Tinted icons take the accent color of the system (Colors). Apps installed later get their style the next time you log in.")
            }

            Item {
                Kirigami.FormData.isSection: true
            }

            RowLayout {
                id: appearanceRow
                Kirigami.FormData.label: i18nc("@label", "Appearance:")
                Kirigami.FormData.buddyFor: lightButton
                enabled: kcm.available
                spacing: Kirigami.Units.largeSpacing

                QQC2.ButtonGroup {
                    id: appearanceGroup
                }
                QQC2.RadioButton {
                    id: lightButton
                    QQC2.ButtonGroup.group: appearanceGroup
                    text: i18nc("@option:radio icon appearance", "Light")
                    checked: kcm.appearance === "light"
                    onToggled: kcm.appearance = "light"
                }
                QQC2.RadioButton {
                    QQC2.ButtonGroup.group: appearanceGroup
                    text: i18nc("@option:radio icon appearance", "Dark")
                    checked: kcm.appearance === "dark"
                    onToggled: kcm.appearance = "dark"
                }
                QQC2.RadioButton {
                    QQC2.ButtonGroup.group: appearanceGroup
                    text: i18nc("@option:radio icon appearance", "Auto")
                    checked: kcm.appearance === "auto"
                    onToggled: kcm.appearance = "auto"
                }
            }

            QQC2.Label {
                Layout.maximumWidth: Kirigami.Units.gridUnit * 26
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: i18nc("@info", "Auto follows the color scheme: light icons with a light scheme, dark icons with a dark one.")
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
    }
}
