/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Reloj de la barra de menús, como el de macOS: «Vie 16 de oct  1:09 p.m.».
    El reloj digital de Plasma no sirve para esto: escribe el día en minúscula,
    convierte «p.m.» en «P.M.» y no separa la fecha de la hora. Al pulsarlo
    abre un calendario.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.clock as PlasmaClock
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasmoid
import org.kde.plasma.workspace.calendar as PlasmaCalendar
import "tokens.js" as T

PlasmoidItem {
    id: root

    // El reloj de Plasma avisa en cada cambio de minuto, alineado, y también
    // al cambiar la zona horaria o la hora del sistema y al volver de la
    // suspensión (un Timer se queda atrás en esos casos)
    PlasmaClock.Clock {
        id: clock
        trackSeconds: false
    }
    readonly property date now: clock.dateTime

    // Orden de día, fecha y mes de la barra de menús de macOS en cada idioma
    // (el formato corto de Qt no lo trae): «Vie 16 de oct», «Fri Oct 16»,
    // «Fr. 16. Okt.». Sin entrada: «ddd d MMM».
    readonly property var dateFormats: ({
        "en_US": "ddd MMM d",
        "es": "ddd d 'de' MMM",
        "pt": "ddd d 'de' MMM",
        "de": "ddd d. MMM",
    })
    readonly property string dateFormat: {
        const name = Qt.locale().name;
        return dateFormats[name] ?? dateFormats[name.split("_")[0]] ?? "ddd d MMM";
    }

    function capitalized(text) {
        return text.length > 0 ? text.charAt(0).toLocaleUpperCase() + text.slice(1) : text;
    }

    // Dos espacios entre fecha y hora, como macOS. La hora sigue el formato
    // corto del idioma: «1:09 p.m.» en es_MX, «13:09» en es_ES.
    readonly property string label: capitalized(Qt.locale().toString(now, dateFormat))
        + "  " + Qt.locale().toString(now, Qt.locale().timeFormat(Locale.ShortFormat))

    preferredRepresentation: compactRepresentation
    toolTipMainText: capitalized(Qt.locale().toString(now, "dddd"))
    toolTipSubText: Qt.locale().toString(now, Qt.locale().dateFormat(Locale.LongFormat))

    compactRepresentation: MouseArea {
        Layout.minimumWidth: clockLabel.implicitWidth
        Layout.preferredWidth: clockLabel.implicitWidth
        onClicked: root.expanded = !root.expanded

        PlasmaComponents3.Label {
            id: clockLabel
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            textFormat: Text.PlainText
            wrapMode: Text.NoWrap
            text: root.label
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.minimumWidth: Kirigami.Units.gridUnit * 18
        Layout.minimumHeight: Kirigami.Units.gridUnit * 18
        spacing: Kirigami.Units.smallSpacing

        PlasmaCalendar.MonthView {
            id: monthView
            Layout.fillWidth: true
            Layout.fillHeight: true
            borderOpacity: T.tokens.clock.calendar_border_alpha
            today: root.now
            firstDayOfWeek: Qt.locale().firstDayOfWeek
        }

        Connections {
            target: root
            // Al abrir, el calendario vuelve al mes de hoy.
            function onExpandedChanged() {
                if (root.expanded) {
                    monthView.resetToToday();
                }
            }
        }
    }
}
