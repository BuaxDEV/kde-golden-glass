/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "unitname.h"

#include <QStringList>

namespace GoldenGlass
{

namespace
{
const QString serviceSuffix = QStringLiteral(".service");
const QString scopeSuffix = QStringLiteral(".scope");
const QString appPrefix = QStringLiteral("app-");
const QString dbusPrefix = QStringLiteral("dbus-");
const QString autostartInstance = QStringLiteral("autostart");
constexpr int escapeLength = 4; // "\xNN"

UnitName invalid()
{
    return {};
}

// dbus-:1.2-org.kde.kdeconnect@0 (without ".service")
UnitName parseDBusActivation(const QString &base)
{
    const QString rest = base.mid(dbusPrefix.size());
    const qsizetype nameStart = rest.indexOf(QLatin1Char('-'));
    const qsizetype instanceStart = rest.lastIndexOf(QLatin1Char('@'));
    if (!rest.startsWith(QLatin1Char(':')) || nameStart < 0 || instanceStart < nameStart) {
        return invalid();
    }
    UnitName name;
    name.origin = UnitName::Origin::DBusActivation;
    name.appId = unescapeUnitName(rest.mid(nameStart + 1, instanceStart - nameStart - 1));
    name.instance = rest.mid(instanceStart + 1);
    return name.appId.isEmpty() ? invalid() : name;
}

UnitName parseApp(QString rest, UnitName::Origin origin)
{
    UnitName name;
    name.origin = origin;
    if (origin == UnitName::Origin::Service) {
        const qsizetype instanceStart = rest.indexOf(QLatin1Char('@'));
        if (instanceStart >= 0) {
            name.instance = rest.mid(instanceStart + 1);
            rest.truncate(instanceStart);
        }
    } else {
        const qsizetype instanceStart = rest.lastIndexOf(QLatin1Char('-'));
        if (instanceStart < 0) {
            return invalid();
        }
        name.instance = rest.mid(instanceStart + 1);
        rest.truncate(instanceStart);
        if (name.instance.isEmpty()) {
            return invalid();
        }
    }

    // Dashes inside the id are escaped, so a raw '-' only separates the
    // launcher. Anything with more parts (Ghostty's
    // app-ghostty-surface-transient-<n>.scope) does not follow the spec.
    const QStringList parts = rest.split(QLatin1Char('-'));
    if (parts.size() > 2) {
        return invalid();
    }
    if (parts.size() == 2) {
        name.launcher = unescapeUnitName(parts.first());
    }
    name.appId = unescapeUnitName(parts.last());
    return name.appId.isEmpty() ? invalid() : name;
}

int hexValue(char c)
{
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    return -1;
}
} // namespace

bool UnitName::isValid() const
{
    return origin != Origin::Invalid;
}

bool UnitName::isAutostart() const
{
    return origin == Origin::Service && instance == autostartInstance;
}

qint64 UnitName::scopePid() const
{
    if (origin != Origin::Scope) {
        return 0;
    }
    bool ok = false;
    const qint64 pid = instance.toLongLong(&ok);
    return ok && pid > 0 ? pid : 0;
}

QString unescapeUnitName(const QString &escaped)
{
    const QByteArray in = escaped.toUtf8();
    QByteArray out;
    out.reserve(in.size());
    for (qsizetype i = 0; i < in.size(); ++i) {
        if (in.at(i) != '\\') {
            out += in.at(i);
            continue;
        }
        if (i + escapeLength > in.size() || in.at(i + 1) != 'x') {
            return {};
        }
        const int high = hexValue(in.at(i + 2));
        const int low = hexValue(in.at(i + 3));
        if (high < 0 || low < 0) {
            return {};
        }
        out += char(high * 16 + low);
        i += escapeLength - 1;
    }
    return QString::fromUtf8(out);
}

UnitName parseUnitName(const QString &unit)
{
    UnitName::Origin origin;
    QString base;
    if (unit.endsWith(serviceSuffix)) {
        origin = UnitName::Origin::Service;
        base = unit.chopped(serviceSuffix.size());
    } else if (unit.endsWith(scopeSuffix)) {
        origin = UnitName::Origin::Scope;
        base = unit.chopped(scopeSuffix.size());
    } else {
        return invalid();
    }

    if (origin == UnitName::Origin::Service && base.startsWith(dbusPrefix)) {
        return parseDBusActivation(base);
    }
    if (!base.startsWith(appPrefix)) {
        return invalid();
    }
    return parseApp(base.mid(appPrefix.size()), origin);
}

} // namespace GoldenGlass
