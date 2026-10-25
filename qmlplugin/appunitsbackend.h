/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include "unitname.h"

#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusObjectPath>
#include <QHash>
#include <QList>
#include <QObject>
#include <QSet>
#include <QSharedPointer>
#include <QStringList>
#include <QTimer>

#include <functional>
#include <memory>

class QDBusServiceWatcher;

// An app with at least one live unit, keyed by its desktop file id
struct RunningApp {
    QString key;
    QString name;
    QString icon;
    QStringList units;
    bool agent = true;

    bool operator==(const RunningApp &other) const = default;
};

/*
    The systemd side of AppUnits, shared by every AppUnits of the process (one
    per Dock): one private connection, one subscription, one listing.

    The connection is private ("goldenglass-units") because Subscribe() makes
    systemd send every unit and job signal to the subscriber: on plasmashell's
    own connection all its other clients would pay for them. The listing is
    refreshed only on systemd's signals, never polled.
*/
class AppUnitsBackend : public QObject
{
    Q_OBJECT

public:
    static QSharedPointer<AppUnitsBackend> shared();
    ~AppUnitsBackend() override;

    bool available() const;
    const QList<RunningApp> &apps() const;
    void stop(const QStringList &units);

Q_SIGNALS:
    void availableChanged();
    void appsChanged();

private Q_SLOTS:
    void scheduleRefresh();
    void onUnitPropertiesChanged(const QDBusMessage &message);

private:
    struct LiveUnit {
        QString unit;
        QDBusObjectPath path;
        GoldenGlass::UnitName name;
        QString key;
    };
    using Units = std::shared_ptr<QList<LiveUnit>>;

    struct PropertyRequest {
        QDBusObjectPath path;
        QString interface;
        QString property;
        std::function<void(const QVariant &)> store;
    };

    AppUnitsBackend();

    void watchSystemd();
    void start();
    void refresh();
    void onUnitsListed(const QDBusMessage &reply);
    void resolveBySourcePath(const Units &units);
    void resolveByMainPid(const Units &units);
    void finishRefresh(const QList<LiveUnit> &units, bool listed);
    void publish(const QList<LiveUnit> &units);
    void setAvailable(bool available);
    void fetchProperties(const QList<PropertyRequest> &requests, const std::function<void()> &then);
    QDBusMessage managerCall(const QString &method) const;

    QDBusConnection m_bus;
    QDBusServiceWatcher *m_watcher = nullptr;
    QTimer m_refreshTimer;
    bool m_refreshing = false;
    bool m_refreshAgain = false;
    bool m_available = false;
    QList<RunningApp> m_apps;
    QSet<QString> m_knownPaths;
    // immutable for the life of a unit: fetched once, kept while it is listed
    QHash<QString, QString> m_sourcePaths;
    QHash<QString, uint> m_mainPids;
};
