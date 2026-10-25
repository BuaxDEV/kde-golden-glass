/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "appunits.h"

#include "appunitsbackend.h"

#include <QVariantMap>

namespace
{
const RunningApp *findApp(const QList<RunningApp> &apps, const QString &key)
{
    const auto it = std::find_if(apps.cbegin(), apps.cend(), [&key](const RunningApp &app) {
        return app.key == key;
    });
    return it == apps.cend() ? nullptr : &*it;
}
} // namespace

AppUnits::AppUnits(QObject *parent)
    : QObject(parent)
    , m_backend(AppUnitsBackend::shared())
{
    connect(m_backend.data(), &AppUnitsBackend::availableChanged, this, &AppUnits::availableChanged);
    connect(m_backend.data(), &AppUnitsBackend::appsChanged, this, &AppUnits::updateApps);
    updateApps();
}

AppUnits::~AppUnits() = default;

bool AppUnits::available() const
{
    return m_backend->available();
}

QVariantList AppUnits::apps() const
{
    return m_apps;
}

QStringList AppUnits::ignored() const
{
    return m_ignored;
}

void AppUnits::setIgnored(const QStringList &ignored)
{
    if (m_ignored != ignored) {
        m_ignored = ignored;
        Q_EMIT ignoredChanged();
        updateApps();
    }
}

QStringList AppUnits::units(const QString &key) const
{
    const RunningApp *app = findApp(m_backend->apps(), key);
    return app ? app->units : QStringList();
}

void AppUnits::stop(const QString &key)
{
    m_backend->stop(units(key));
}

bool AppUnits::isAgent(const QString &key) const
{
    const RunningApp *app = findApp(m_backend->apps(), key);
    return app && app->agent;
}

void AppUnits::updateApps()
{
    QVariantList apps;
    for (const RunningApp &app : m_backend->apps()) {
        if (!m_ignored.contains(app.key)) {
            apps.append(QVariantMap{
                {QStringLiteral("key"), app.key},
                {QStringLiteral("name"), app.name},
                {QStringLiteral("icon"), app.icon},
                {QStringLiteral("agent"), app.agent},
            });
        }
    }
    if (apps != m_apps) {
        m_apps = apps;
        Q_EMIT appsChanged();
    }
}
