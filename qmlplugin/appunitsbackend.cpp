/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "appunitsbackend.h"

#include <KConfigGroup>
#include <KDesktopFile>

#include <QDBusArgument>
#include <QDBusPendingCallWatcher>
#include <QDBusServiceWatcher>
#include <QDBusVariant>
#include <QLoggingCategory>
#include <QStandardPaths>

Q_LOGGING_CATEGORY(lcAppUnits, "org.goldenglass.appunits", QtWarningMsg)

namespace
{
const QString connectionName = QStringLiteral("goldenglass-units");
const QString systemdService = QStringLiteral("org.freedesktop.systemd1");
const QString systemdPath = QStringLiteral("/org/freedesktop/systemd1");
const QString managerInterface = QStringLiteral("org.freedesktop.systemd1.Manager");
const QString unitInterface = QStringLiteral("org.freedesktop.systemd1.Unit");
const QString serviceInterface = QStringLiteral("org.freedesktop.systemd1.Service");
const QString propertiesInterface = QStringLiteral("org.freedesktop.DBus.Properties");
const QStringList unitPatterns = {QStringLiteral("app-*.service"), QStringLiteral("app-*.scope"), QStringLiteral("dbus-*.service")};
const QStringList liveStates = {QStringLiteral("active"), QStringLiteral("activating"), QStringLiteral("reloading")};

// a burst of unit and job signals (an app starting) becomes one listing
constexpr int refreshDelayMs = 250;
constexpr int callTimeoutMs = 5000;

struct DesktopEntry {
    bool exists = false;
    bool shown = false;
    QString name;
    QString icon;
};

DesktopEntry readDesktopEntry(const QString &appId)
{
    const QString path = QStandardPaths::locate(QStandardPaths::ApplicationsLocation, appId + QLatin1String(".desktop"));
    if (path.isEmpty()) {
        return {};
    }
    const KDesktopFile file(path);
    const KConfigGroup group = file.desktopGroup();
    // the terminal's unit holds whatever was started from it
    const bool terminal = group.readXdgListEntry("Categories").contains(QLatin1String("TerminalEmulator"));
    DesktopEntry entry;
    entry.exists = true;
    entry.shown = file.hasApplicationType() && !file.noDisplay() && !group.readEntry("Hidden", false) && !terminal;
    entry.name = file.readName();
    entry.icon = file.readIcon();
    return entry;
}

QString desktopIdOf(const QString &sourcePath)
{
    const QString suffix = QStringLiteral(".desktop");
    if (!sourcePath.endsWith(suffix)) {
        return {};
    }
    return sourcePath.section(QLatin1Char('/'), -1).chopped(suffix.size());
}
} // namespace

QSharedPointer<AppUnitsBackend> AppUnitsBackend::shared()
{
    static QWeakPointer<AppUnitsBackend> instance;
    QSharedPointer<AppUnitsBackend> backend = instance.toStrongRef();
    if (!backend) {
        backend.reset(new AppUnitsBackend);
        instance = backend;
    }
    return backend;
}

AppUnitsBackend::AppUnitsBackend()
    : m_bus(QDBusConnection::connectToBus(QDBusConnection::SessionBus, connectionName))
{
    m_refreshTimer.setSingleShot(true);
    m_refreshTimer.setInterval(refreshDelayMs);
    connect(&m_refreshTimer, &QTimer::timeout, this, &AppUnitsBackend::refresh);

    if (!m_bus.isConnected()) {
        qCDebug(lcAppUnits) << "no session bus:" << m_bus.lastError().message();
        return;
    }
    watchSystemd();
    start();
}

AppUnitsBackend::~AppUnitsBackend()
{
    m_bus = QDBusConnection(QString());
    QDBusConnection::disconnectFromBus(connectionName);
}

bool AppUnitsBackend::available() const
{
    return m_available;
}

const QList<RunningApp> &AppUnitsBackend::apps() const
{
    return m_apps;
}

void AppUnitsBackend::stop(const QStringList &units)
{
    for (const QString &unit : units) {
        QDBusMessage message = managerCall(QStringLiteral("StopUnit"));
        message << unit << QStringLiteral("replace");
        auto *watcher = new QDBusPendingCallWatcher(m_bus.asyncCall(message, callTimeoutMs), this);
        connect(watcher, &QDBusPendingCallWatcher::finished, this, [unit](QDBusPendingCallWatcher *call) {
            call->deleteLater();
            if (call->isError()) {
                qCWarning(lcAppUnits) << "StopUnit" << unit << "failed:" << call->error().message();
            }
        });
    }
}

void AppUnitsBackend::watchSystemd()
{
    m_watcher = new QDBusServiceWatcher(systemdService, m_bus, QDBusServiceWatcher::WatchForOwnerChange, this);
    connect(m_watcher, &QDBusServiceWatcher::serviceOwnerChanged, this, [this](const QString &, const QString &, const QString &newOwner) {
        if (newOwner.isEmpty()) {
            setAvailable(false);
            m_knownPaths.clear();
            publish({});
        } else {
            start();
        }
    });

    for (const QString &signal : {QStringLiteral("UnitNew"), QStringLiteral("UnitRemoved"), QStringLiteral("JobRemoved")}) {
        m_bus.connect(systemdService, systemdPath, managerInterface, signal, this, SLOT(scheduleRefresh()));
    }
    // An app that exits on its own sends no job signal, and an autostart unit
    // stays loaded once dead (no UnitRemoved either): its state change is the
    // only sign. Any path, filtered to the listed units in the slot.
    m_bus.connect(systemdService, QString(), propertiesInterface, QStringLiteral("PropertiesChanged"), this, SLOT(onUnitPropertiesChanged(QDBusMessage)));
}

void AppUnitsBackend::start()
{
    auto *watcher = new QDBusPendingCallWatcher(m_bus.asyncCall(managerCall(QStringLiteral("Subscribe")), callTimeoutMs), this);
    connect(watcher, &QDBusPendingCallWatcher::finished, this, [this](QDBusPendingCallWatcher *call) {
        call->deleteLater();
        if (call->isError()) {
            qCDebug(lcAppUnits) << "Subscribe failed:" << call->error().message();
        }
        refresh();
    });
}

void AppUnitsBackend::scheduleRefresh()
{
    m_refreshTimer.start();
}

void AppUnitsBackend::onUnitPropertiesChanged(const QDBusMessage &message)
{
    if (message.arguments().value(0).toString() == unitInterface && m_knownPaths.contains(message.path())) {
        scheduleRefresh();
    }
}

void AppUnitsBackend::refresh()
{
    if (m_refreshing) {
        m_refreshAgain = true;
        return;
    }
    m_refreshing = true;
    QDBusMessage message = managerCall(QStringLiteral("ListUnitsByPatterns"));
    message << QStringList() << unitPatterns;
    auto *watcher = new QDBusPendingCallWatcher(m_bus.asyncCall(message, callTimeoutMs), this);
    connect(watcher, &QDBusPendingCallWatcher::finished, this, [this](QDBusPendingCallWatcher *call) {
        call->deleteLater();
        onUnitsListed(call->reply());
    });
}

void AppUnitsBackend::onUnitsListed(const QDBusMessage &reply)
{
    if (reply.type() != QDBusMessage::ReplyMessage) {
        qCDebug(lcAppUnits) << "ListUnitsByPatterns failed:" << reply.errorMessage();
        m_knownPaths.clear();
        finishRefresh({}, false);
        return;
    }

    auto units = std::make_shared<QList<LiveUnit>>();
    QSet<QString> listedPaths;
    QSet<QString> liveNames;
    const QDBusArgument list = reply.arguments().value(0).value<QDBusArgument>();
    list.beginArray();
    while (!list.atEnd()) {
        QString unit, description, loadState, activeState, subState, following, jobType;
        QDBusObjectPath path, jobPath;
        uint jobId = 0;
        list.beginStructure();
        list >> unit >> description >> loadState >> activeState >> subState >> following >> path >> jobId >> jobType >> jobPath;
        list.endStructure();
        listedPaths.insert(path.path());
        if (liveStates.contains(activeState)) {
            const GoldenGlass::UnitName name = GoldenGlass::parseUnitName(unit);
            const bool named = name.isValid() && readDesktopEntry(name.appId).exists;
            units->append({unit, path, name, named ? name.appId : QString()});
            liveNames.insert(unit);
        }
    }
    list.endArray();

    m_knownPaths = listedPaths;
    m_sourcePaths.removeIf([&liveNames](const auto &it) {
        return !liveNames.contains(it.key());
    });
    m_mainPids.removeIf([&liveNames](const auto &it) {
        return !liveNames.contains(it.key());
    });
    resolveBySourcePath(units);
}

void AppUnitsBackend::resolveBySourcePath(const Units &units)
{
    QList<PropertyRequest> requests;
    for (const LiveUnit &live : std::as_const(*units)) {
        if (live.key.isEmpty() && !m_sourcePaths.contains(live.unit)) {
            requests.append({live.path, unitInterface, QStringLiteral("SourcePath"), [this, unit = live.unit](const QVariant &value) {
                                 m_sourcePaths.insert(unit, value.toString());
                             }});
        }
    }
    fetchProperties(requests, [this, units] {
        for (LiveUnit &live : *units) {
            const QString id = desktopIdOf(m_sourcePaths.value(live.unit));
            if (live.key.isEmpty() && !id.isEmpty() && readDesktopEntry(id).exists) {
                live.key = id;
            }
        }
        resolveByMainPid(units);
    });
}

// Chromium moves its main process out of the unit it was launched in into its
// own app-org.chromium.Chromium-<pid>.scope, whatever the browser is called:
// the service it left still has that pid as MainPID.
void AppUnitsBackend::resolveByMainPid(const Units &units)
{
    const bool orphanScopes = std::any_of(units->cbegin(), units->cend(), [](const LiveUnit &live) {
        return live.key.isEmpty() && live.name.scopePid() > 0;
    });
    QList<PropertyRequest> requests;
    for (const LiveUnit &live : std::as_const(*units)) {
        if (orphanScopes && !live.key.isEmpty() && live.name.origin == GoldenGlass::UnitName::Origin::Service && !m_mainPids.contains(live.unit)) {
            requests.append({live.path, serviceInterface, QStringLiteral("MainPID"), [this, unit = live.unit](const QVariant &value) {
                                 m_mainPids.insert(unit, value.toUInt());
                             }});
        }
    }
    fetchProperties(requests, [this, units] {
        for (LiveUnit &scope : *units) {
            const qint64 pid = scope.name.scopePid();
            if (!scope.key.isEmpty() || pid <= 0) {
                continue;
            }
            for (const LiveUnit &service : std::as_const(*units)) {
                if (!service.key.isEmpty() && m_mainPids.value(service.unit) == pid) {
                    scope.key = service.key;
                    break;
                }
            }
        }
        finishRefresh(*units, true);
    });
}

void AppUnitsBackend::finishRefresh(const QList<LiveUnit> &units, bool listed)
{
    publish(units);
    setAvailable(listed);
    m_refreshing = false;
    if (m_refreshAgain) {
        m_refreshAgain = false;
        scheduleRefresh();
    }
}

void AppUnitsBackend::publish(const QList<LiveUnit> &units)
{
    QList<RunningApp> apps;
    QHash<QString, qsizetype> indexOfKey;
    for (const LiveUnit &live : units) {
        if (live.key.isEmpty()) {
            continue;
        }
        auto found = indexOfKey.constFind(live.key);
        if (found == indexOfKey.cend()) {
            const DesktopEntry entry = readDesktopEntry(live.key);
            if (!entry.shown) {
                continue;
            }
            found = indexOfKey.insert(live.key, apps.size());
            apps.append({live.key, entry.name, entry.icon, {}, true});
        }
        RunningApp &app = apps[*found];
        app.units.append(live.unit);
        app.agent = app.agent && live.name.isAutostart();
    }
    if (apps != m_apps) {
        m_apps = apps;
        Q_EMIT appsChanged();
    }
}

void AppUnitsBackend::setAvailable(bool available)
{
    if (m_available != available) {
        m_available = available;
        Q_EMIT availableChanged();
    }
}

void AppUnitsBackend::fetchProperties(const QList<PropertyRequest> &requests, const std::function<void()> &then)
{
    if (requests.isEmpty()) {
        then();
        return;
    }
    auto remaining = std::make_shared<qsizetype>(requests.size());
    for (const PropertyRequest &request : requests) {
        QDBusMessage message = QDBusMessage::createMethodCall(systemdService, request.path.path(), propertiesInterface, QStringLiteral("Get"));
        message << request.interface << request.property;
        message.setAutoStartService(false);
        auto *watcher = new QDBusPendingCallWatcher(m_bus.asyncCall(message, callTimeoutMs), this);
        connect(watcher, &QDBusPendingCallWatcher::finished, this, [request, remaining, then](QDBusPendingCallWatcher *call) {
            call->deleteLater();
            const QDBusMessage reply = call->reply();
            if (reply.type() == QDBusMessage::ReplyMessage) {
                request.store(reply.arguments().value(0).value<QDBusVariant>().variant());
            }
            if (--*remaining == 0) {
                then();
            }
        });
    }
}

QDBusMessage AppUnitsBackend::managerCall(const QString &method) const
{
    QDBusMessage message = QDBusMessage::createMethodCall(systemdService, systemdPath, managerInterface, method);
    // never start systemd through D-Bus activation: without it the feature is off
    message.setAutoStartService(false);
    return message;
}
