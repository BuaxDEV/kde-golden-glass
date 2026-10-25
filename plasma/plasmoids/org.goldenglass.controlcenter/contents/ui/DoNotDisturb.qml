/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Do Not Disturb, as the Focus pill and its detail view drive it: Plasma's
    notification inhibition (notificationmanager), the same one its
    notifications applet uses. A component of its own so that the
    notifications plasmoid can share it (tools/plasmoids.py, SHARED).
*/

import QtQuick

import org.kde.notificationmanager as NotificationManager

QtObject {
    readonly property NotificationManager.Settings settings: NotificationManager.Settings {}

    // inhibited until a later date, or by an application (a video, a talk)
    readonly property bool active: {
        const until = settings.notificationsInhibitedUntil;
        return (until !== undefined && !isNaN(until.getTime()) && until.getTime() > Date.now())
            || settings.notificationsInhibitedByApplication;
    }

    // on without an end: a year ahead, as Plasma's notifications applet does
    function setActive(on) {
        if (on) {
            const until = new Date();
            until.setFullYear(until.getFullYear() + 1);
            setActiveUntil(until);
        } else {
            setActiveUntil(null);
        }
    }

    // until a date (Date) or, with null, off
    function setActiveUntil(until) {
        if (until) {
            settings.notificationsInhibitedUntil = until;
        } else {
            settings.notificationsInhibitedUntil = undefined;
            settings.revokeApplicationInhibitions();
        }
        settings.save();
    }
}
