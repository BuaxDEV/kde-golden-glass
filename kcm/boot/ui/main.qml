/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Módulo «Arranque e inicio de sesión»: pantalla de arranque (Plymouth) de
    la distribución o de GoldenGlass, negra o gris, con miniaturas dibujadas
    con las piezas del propio tema. Se aplica con «Aplicar» (pide la contraseña
    de administrador y regenera el initramfs).
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    id: root

    // Miniatura de una opción: fondo, logo y barra como en el arranque.
    component ThemeCard: QQC2.AbstractButton {
        id: card
        property string variant
        property color screenColor
        property string label
        property string detail

        checkable: true
        checked: kcm.plymouth === variant
        enabled: !kcm.busy && (variant === "system" || kcm.installed)
        onClicked: kcm.plymouth = variant
        Accessible.name: label
        Layout.alignment: Qt.AlignTop
        implicitWidth: Kirigami.Units.gridUnit * 10
        implicitHeight: column.implicitHeight

        contentItem: ColumnLayout {
            id: column
            spacing: Kirigami.Units.smallSpacing

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: width * 9 / 16
                radius: Kirigami.Units.cornerRadius
                color: card.screenColor
                border.width: card.checked ? 2 : 1
                border.color: card.checked ? Kirigami.Theme.highlightColor : Kirigami.Theme.disabledTextColor

                Image {
                    id: logo
                    visible: card.variant !== "system"
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.verticalCenterOffset: -parent.height * 0.06
                    width: parent.height * 0.24
                    height: width
                    source: visible ? kcm.themeImage(card.variant, "logo") : ""
                    smooth: true
                    mipmap: true
                }
                Image {
                    id: track
                    visible: logo.visible
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: logo.bottom
                    anchors.topMargin: logo.height * 0.43
                    width: logo.width * 1.7
                    height: Math.max(2, logo.height * 0.05)
                    source: visible ? kcm.themeImage(card.variant, "track") : ""
                    smooth: true
                }
                // un tercio de barra ya recorrido
                Item {
                    visible: logo.visible
                    x: track.x
                    y: track.y
                    width: track.width / 3
                    height: track.height
                    clip: true
                    Image {
                        width: track.width
                        height: track.height
                        source: parent.visible ? kcm.themeImage(card.variant, "fill") : ""
                        smooth: true
                    }
                }
                Kirigami.Icon {
                    visible: card.variant === "system"
                    anchors.centerIn: parent
                    width: Kirigami.Units.iconSizes.large
                    height: width
                    source: "preferences-system-startup"
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: card.label
                font.bold: card.checked
                elide: Text.ElideRight
            }
            QQC2.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                visible: card.detail.length > 0
                text: card.detail
                color: Kirigami.Theme.disabledTextColor
                font: Kirigami.Theme.smallFont
                elide: Text.ElideMiddle
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
            visible: !kcm.installed
            text: i18nc("@info", "The GoldenGlass boot screens are not installed (goldenglass-plymouth package).")
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            type: Kirigami.MessageType.Warning
            visible: kcm.warnings.length > 0
            text: kcm.warnings.map(code => code === "no-splash"
                ? i18nc("@info", "The kernel command line has no “splash” option: no boot screen will be shown.")
                : i18nc("@info", "The “plymouth” hook is missing from the mkinitcpio HOOKS: no boot screen will be shown.")).join("\n")
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            type: Kirigami.MessageType.Warning
            visible: kcm.loginWarnings.indexOf("sddm-overridden") >= 0
            text: i18nc("@info", "/etc/sddm.conf sets its own theme and takes precedence: the GoldenGlass login screen will not be shown.")
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            RowLayout {
                Kirigami.FormData.label: i18nc("@label", "Boot screen:")
                Kirigami.FormData.buddyFor: systemCard
                spacing: Kirigami.Units.largeSpacing

                ThemeCard {
                    id: systemCard
                    variant: "system"
                    screenColor: Kirigami.Theme.alternateBackgroundColor
                    label: i18nc("@option:radio boot screen", "System")
                    detail: kcm.systemTheme
                }
                ThemeCard {
                    variant: "dark"
                    screenColor: kcm.darkBackground
                    label: i18nc("@option:radio boot screen", "GoldenGlass")
                }
                ThemeCard {
                    variant: "light"
                    screenColor: kcm.lightBackground
                    label: i18nc("@option:radio boot screen", "GoldenGlass Light")
                }
            }

            QQC2.Label {
                Layout.maximumWidth: Kirigami.Units.gridUnit * 31
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: i18nc("@info", "The logo and a thin progress bar while the computer starts, and the disk password, if it is encrypted, in a glass field. Applying rebuilds the initramfs, which takes a moment.")
            }

            Item {
                Kirigami.FormData.isSection: true
            }

            QQC2.Switch {
                id: loginSwitch
                Kirigami.FormData.label: i18nc("@label", "Login screen:")
                visible: kcm.loginManager === "sddm" || kcm.loginManager === "plasmalogin"
                enabled: !kcm.busy && kcm.loginInstalled
                text: kcm.loginManager === "sddm"
                    ? i18nc("@option:check", "Use the GoldenGlass login screen")
                    : i18nc("@option:check", "Use the GoldenGlass wallpaper and my Plasma settings")
                checked: kcm.login
                onToggled: kcm.login = checked
            }

            QQC2.Label {
                Layout.maximumWidth: Kirigami.Units.gridUnit * 31
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: {
                    if (kcm.loginManager === "sddm") {
                        return kcm.loginInstalled
                            ? i18nc("@info", "Like the lock screen: blurred day or night wallpaper, large clock, avatar and password.")
                            : i18nc("@info", "The GoldenGlass SDDM theme is not installed (goldenglass-login package).");
                    }
                    if (kcm.loginManager === "plasmalogin") {
                        return kcm.loginInstalled
                            ? i18nc("@info", "Plasma Login Manager does not support themes: it gets the GoldenGlass wallpaper and copies your colors, Plasma style, fonts, cursor and keyboard layout. For the full GoldenGlass login screen, use SDDM.")
                            : i18nc("@info", "The GoldenGlass wallpaper is not installed (goldenglass-wallpapers package).");
                    }
                    return i18nc("@info", "The login manager in use is not SDDM or Plasma Login Manager: GoldenGlass cannot change its screen.");
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
            text: i18nc("@info", "Applying asks for the administrator password.")
        }
    }
}
