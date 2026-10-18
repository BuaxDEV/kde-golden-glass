/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Enfoque en detalle, como en macOS 26: No molestar y por cuánto tiempo.
*/

import QtQuick

DetailView {
    id: view

    required property bool doNotDisturb

    // fin del modo (Date) o null para desactivarlo
    signal untilRequested(var until)
    signal settingsRequested()

    title: i18n("Focus")
    footerText: i18n("Notification Settings…")
    onFooterClicked: settingsRequested()

    function hoursFromNow(hours) {
        const until = new Date();
        until.setTime(until.getTime() + hours * 3600 * 1000);
        return until;
    }
    function tomorrowMorning() {
        const until = new Date();
        until.setDate(until.getDate() + 1);
        until.setHours(8, 0, 0, 0);
        return until;
    }
    function forever() {
        const until = new Date();
        until.setFullYear(until.getFullYear() + 1);
        return until;
    }

    DetailRow {
        text: i18n("Do Not Disturb")
        iconName: "weather-clear-night-symbolic"
        active: view.doNotDisturb
        onClicked: view.untilRequested(view.doNotDisturb ? null : view.forever())
    }
    DetailRow {
        text: i18n("For 1 hour")
        indented: true
        onClicked: view.untilRequested(view.hoursFromNow(1))
    }
    DetailRow {
        text: i18n("Until tomorrow morning")
        indented: true
        onClicked: view.untilRequested(view.tomorrowMorning())
    }
}
