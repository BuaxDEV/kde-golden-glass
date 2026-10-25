/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QString>

namespace GoldenGlass
{

/*
    What the name of a systemd user unit says about the app it runs.

    Launchers follow https://systemd.io/DESKTOP_ENVIRONMENTS/:

        app[-<launcher>]-<ApplicationID>[@<instance>].service
        app[-<launcher>]-<ApplicationID>-<instance>.scope

    where ApplicationID is the desktop file id without ".desktop", escaped the
    systemd way (a '-' inside it is "\x2d"). dbus-broker names the units it
    starts for D-Bus activation

        dbus-<broker unique name>-<bus name>@<serial>.service

    and the bus name of a DBusActivatable app is its desktop file id.
*/
struct UnitName {
    enum class Origin {
        Invalid,
        Service,
        Scope,
        DBusActivation,
    };

    Origin origin = Origin::Invalid;
    QString appId;
    QString launcher;
    QString instance;

    bool isValid() const;
    // started by systemd-xdg-autostart-generator, not by the user
    bool isAutostart() const;
    // the pid a launcher put in a scope name (Chromium, Flatpak), or 0
    qint64 scopePid() const;
};

UnitName parseUnitName(const QString &unit);

// "\xNN" escapes back to UTF-8 text; a null QString if an escape is malformed
QString unescapeUnitName(const QString &escaped);

} // namespace GoldenGlass
