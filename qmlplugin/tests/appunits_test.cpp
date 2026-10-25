/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// AppUnits against a fake org.freedesktop.systemd1 on the test bus (DBUS test:
// runs under dbus-run-session). The desktop files live in the test's own
// XDG_DATA_HOME.

#include "appunits.h"

#include "testbus.h"

#include <QDBusArgument>
#include <QDBusMetaType>
#include <QDBusObjectPath>
#include <QDBusVariant>
#include <QDBusVirtualObject>

namespace
{
const QString systemdService = QStringLiteral("org.freedesktop.systemd1");
const QString systemdPath = QStringLiteral("/org/freedesktop/systemd1");
const QString managerInterface = QStringLiteral("org.freedesktop.systemd1.Manager");
const QString unitInterface = QStringLiteral("org.freedesktop.systemd1.Unit");
const QString serviceInterface = QStringLiteral("org.freedesktop.systemd1.Service");
const QString propertiesInterface = QStringLiteral("org.freedesktop.DBus.Properties");
// AppUnits waits this long after a signal; the tests wait a few times more
constexpr int signalWaitMs = 3000;
} // namespace

// one row of ListUnitsByPatterns: a(ssssssouso)
struct ListedUnit {
    QString name;
    QString description;
    QString loadState = QStringLiteral("loaded");
    QString activeState = QStringLiteral("active");
    QString subState = QStringLiteral("running");
    QString following;
    QDBusObjectPath path;
    uint jobId = 0;
    QString jobType;
    QDBusObjectPath jobPath = QDBusObjectPath(QStringLiteral("/"));
};
Q_DECLARE_METATYPE(ListedUnit)

QDBusArgument &operator<<(QDBusArgument &argument, const ListedUnit &unit)
{
    argument.beginStructure();
    argument << unit.name << unit.description << unit.loadState << unit.activeState << unit.subState << unit.following << unit.path << unit.jobId
             << unit.jobType << unit.jobPath;
    argument.endStructure();
    return argument;
}

const QDBusArgument &operator>>(const QDBusArgument &argument, ListedUnit &unit)
{
    argument.beginStructure();
    argument >> unit.name >> unit.description >> unit.loadState >> unit.activeState >> unit.subState >> unit.following >> unit.path >> unit.jobId
        >> unit.jobType >> unit.jobPath;
    argument.endStructure();
    return argument;
}

struct FakeUnit {
    FakeUnit(const QString &activeState = QStringLiteral("active"), const QString &sourcePath = {}, uint mainPid = 0)
        : activeState(activeState)
        , sourcePath(sourcePath)
        , mainPid(mainPid)
    {
    }

    QString activeState;
    QString sourcePath;
    uint mainPid;
};

/*
    The parts of systemd's manager that AppUnits uses: Subscribe,
    ListUnitsByPatterns, StopUnit, the unit signals and the SourcePath and
    MainPID properties of each unit.
*/
class FakeSystemd : public QDBusVirtualObject
{
    Q_OBJECT

public:
    explicit FakeSystemd(GoldenGlassTest::FakeService &service)
        : m_service(service)
    {
    }

    QMap<QString, FakeUnit> units;
    QStringList stopped;
    int listings = 0;
    int subscriptions = 0;

    static QString pathOf(const QString &unit)
    {
        QString path = systemdPath + QStringLiteral("/unit/");
        for (const char c : unit.toUtf8()) {
            path += QChar::isLetterOrNumber(uchar(c)) ? QString(QLatin1Char(c)) : QStringLiteral("_%1").arg(uchar(c), 2, 16, QLatin1Char('0'));
        }
        return path;
    }

    void addUnit(const QString &unit, const FakeUnit &state = {})
    {
        units.insert(unit, state);
        m_service.emitSignal(systemdPath, managerInterface, QStringLiteral("UnitNew"), {unit, QVariant::fromValue(QDBusObjectPath(pathOf(unit)))});
    }

    void removeUnit(const QString &unit)
    {
        units.remove(unit);
        m_service.emitSignal(systemdPath, managerInterface, QStringLiteral("UnitRemoved"), {unit, QVariant::fromValue(QDBusObjectPath(pathOf(unit)))});
    }

    // the unit changes state without a job: an app that exits on its own
    void setActiveState(const QString &unit, const QString &state)
    {
        units[unit].activeState = state;
        m_service.emitSignal(pathOf(unit),
                             propertiesInterface,
                             QStringLiteral("PropertiesChanged"),
                             {unitInterface, QVariantMap{{QStringLiteral("ActiveState"), state}}, QStringList()});
    }

    QString introspect(const QString &) const override
    {
        return {};
    }

    bool handleMessage(const QDBusMessage &message, const QDBusConnection &connection) override
    {
        if (message.interface() == managerInterface) {
            return handleManager(message, connection);
        }
        if (message.interface() == propertiesInterface && message.member() == QLatin1String("Get")) {
            return handleGet(message, connection);
        }
        return false;
    }

private:
    bool handleManager(const QDBusMessage &message, const QDBusConnection &connection)
    {
        const QString member = message.member();
        if (member == QLatin1String("Subscribe")) {
            ++subscriptions;
            connection.send(message.createReply());
        } else if (member == QLatin1String("ListUnitsByPatterns")) {
            ++listings;
            QList<ListedUnit> rows;
            for (auto it = units.cbegin(); it != units.cend(); ++it) {
                ListedUnit row;
                row.name = it.key();
                row.activeState = it->activeState;
                row.path = QDBusObjectPath(pathOf(it.key()));
                rows.append(row);
            }
            connection.send(message.createReply(QVariant::fromValue(rows)));
        } else if (member == QLatin1String("StopUnit")) {
            const QString unit = message.arguments().value(0).toString();
            stopped.append(unit + QLatin1Char(':') + message.arguments().value(1).toString());
            const QDBusObjectPath job(systemdPath + QStringLiteral("/job/1"));
            connection.send(message.createReply(QVariant::fromValue(job)));
            units.remove(unit);
            m_service.emitSignal(systemdPath,
                                 managerInterface,
                                 QStringLiteral("JobRemoved"),
                                 {uint(1), QVariant::fromValue(job), unit, QStringLiteral("done")});
        } else {
            return false;
        }
        return true;
    }

    bool handleGet(const QDBusMessage &message, const QDBusConnection &connection)
    {
        const QString interface = message.arguments().value(0).toString();
        const QString property = message.arguments().value(1).toString();
        for (auto it = units.cbegin(); it != units.cend(); ++it) {
            if (pathOf(it.key()) != message.path()) {
                continue;
            }
            QVariant value;
            if (interface == unitInterface && property == QLatin1String("SourcePath")) {
                value = it->sourcePath;
            } else if (interface == serviceInterface && property == QLatin1String("MainPID")) {
                value = it->mainPid;
            } else {
                return false;
            }
            connection.send(message.createReply(QVariant::fromValue(QDBusVariant(value))));
            return true;
        }
        return false;
    }

    GoldenGlassTest::FakeService &m_service;
};

class AppUnitsTest : public QObject
{
    Q_OBJECT

    static void writeDesktopFile(const QString &id, const QString &extra = {})
    {
        const QString dir = QStandardPaths::writableLocation(QStandardPaths::ApplicationsLocation);
        QDir().mkpath(dir);
        QFile file(dir + QLatin1Char('/') + id + QStringLiteral(".desktop"));
        QVERIFY(file.open(QIODevice::WriteOnly));
        file.write(QStringLiteral("[Desktop Entry]\nType=Application\nName=%1 app\nIcon=%1-icon\nExec=true\n%2\n").arg(id, extra).toUtf8());
    }

    static QStringList keysOf(const AppUnits &appUnits)
    {
        QStringList keys;
        for (const QVariant &app : appUnits.apps()) {
            keys.append(app.toMap().value(QStringLiteral("key")).toString());
        }
        keys.sort();
        return keys;
    }

    // a fresh fake systemd per test, and the AppUnits listing it
    struct Session {
        GoldenGlassTest::FakeService service;
        FakeSystemd systemd{service};
        std::unique_ptr<AppUnits> appUnits;

        bool start()
        {
            if (!service.registerService(systemdService) || !service.connection().registerVirtualObject(systemdPath, &systemd, QDBusConnection::SubPath)) {
                return false;
            }
            appUnits = std::make_unique<AppUnits>();
            return appUnits->available() || QSignalSpy(appUnits.get(), &AppUnits::availableChanged).wait(signalWaitMs);
        }
    };

private Q_SLOTS:
    void initTestCase()
    {
        GG_REQUIRE_SESSION_BUS();
        qDBusRegisterMetaType<ListedUnit>();
        qDBusRegisterMetaType<QList<ListedUnit>>();

        writeDesktopFile(QStringLiteral("brave-browser"));
        writeDesktopFile(QStringLiteral("org.example.Tray"));
        writeDesktopFile(QStringLiteral("org.example.Hidden"), QStringLiteral("NoDisplay=true"));
        writeDesktopFile(QStringLiteral("org.example.Deleted"), QStringLiteral("Hidden=true"));
        writeDesktopFile(QStringLiteral("org.example.Terminal"), QStringLiteral("Categories=System;TerminalEmulator;"));
        writeDesktopFile(QStringLiteral("org.example.Link"), QStringLiteral("Type=Link\nURL=https://example.org"));
        writeDesktopFile(QStringLiteral("org.example.Ignored"));
        writeDesktopFile(QStringLiteral("org.example.Real"));
    }

    void listsShownApps()
    {
        Session session;
        session.systemd.units = {
            {QStringLiteral("app-brave\\x2dbrowser@411abb663e7a4f3987533771d8c613d0.service"), {}},
            {QStringLiteral("app-org.example.Tray@autostart.service"), {}},
            {QStringLiteral("app-org.example.Hidden@1.service"), {}},
            {QStringLiteral("app-org.example.Deleted@1.service"), {}},
            {QStringLiteral("app-org.example.Terminal@1.service"), {}},
            {QStringLiteral("app-org.example.Link@1.service"), {}},
            {QStringLiteral("app-org.example.Missing@1.service"), {}},
            {QStringLiteral("app-org.example.Real@dead.service"), {QStringLiteral("inactive")}},
            {QStringLiteral("dbus-:1.2-org.kde.kdeconnect@0.service"), {}},
        };
        QVERIFY(session.start());
        QVERIFY(session.appUnits->available());
        QCOMPARE(session.systemd.subscriptions, 1);
        QCOMPARE(keysOf(*session.appUnits), (QStringList{QStringLiteral("brave-browser"), QStringLiteral("org.example.Tray")}));

        const QVariantMap brave = session.appUnits->apps().constFirst().toMap();
        QCOMPARE(brave.value(QStringLiteral("name")).toString(), QStringLiteral("brave-browser app"));
        QCOMPARE(brave.value(QStringLiteral("icon")).toString(), QStringLiteral("brave-browser-icon"));
        QCOMPARE(brave.value(QStringLiteral("agent")).toBool(), false);
        QCOMPARE(session.appUnits->units(QStringLiteral("brave-browser")),
                 QStringList{QStringLiteral("app-brave\\x2dbrowser@411abb663e7a4f3987533771d8c613d0.service")});
    }

    void ignoresListedKeys()
    {
        Session session;
        session.systemd.units = {
            {QStringLiteral("app-org.example.Tray@1.service"), {}},
            {QStringLiteral("app-org.example.Ignored@1.service"), {}},
        };
        QVERIFY(session.start());
        QCOMPARE(keysOf(*session.appUnits), (QStringList{QStringLiteral("org.example.Ignored"), QStringLiteral("org.example.Tray")}));

        QSignalSpy changed(session.appUnits.get(), &AppUnits::appsChanged);
        session.appUnits->setIgnored({QStringLiteral("org.example.Ignored")});
        QCOMPARE(changed.count(), 1);
        QCOMPARE(keysOf(*session.appUnits), QStringList{QStringLiteral("org.example.Tray")});
    }

    // only XDG autostart units: an agent; once the user launches it, not
    void agentsComeFromAutostart()
    {
        Session session;
        session.systemd.units = {{QStringLiteral("app-org.example.Tray@autostart.service"), {}}};
        QVERIFY(session.start());
        QVERIFY(session.appUnits->isAgent(QStringLiteral("org.example.Tray")));
        QVERIFY(!session.appUnits->isAgent(QStringLiteral("org.example.Missing")));

        QSignalSpy changed(session.appUnits.get(), &AppUnits::appsChanged);
        session.systemd.addUnit(QStringLiteral("app-org.example.Tray@0f3a.service"));
        QVERIFY(changed.wait(signalWaitMs));
        QVERIFY(!session.appUnits->isAgent(QStringLiteral("org.example.Tray")));
        QCOMPARE(session.appUnits->units(QStringLiteral("org.example.Tray")).size(), 2);
    }

    // several signals in a row: one listing
    void signalsAreCoalesced()
    {
        Session session;
        QVERIFY(session.start());
        const int listings = session.systemd.listings;

        QSignalSpy changed(session.appUnits.get(), &AppUnits::appsChanged);
        session.systemd.addUnit(QStringLiteral("app-org.example.Tray@1.service"));
        session.systemd.addUnit(QStringLiteral("app-brave\\x2dbrowser@1.service"));
        session.systemd.addUnit(QStringLiteral("app-org.example.Real@1.service"));
        QVERIFY(changed.wait(signalWaitMs));
        QCOMPARE(session.systemd.listings, listings + 1);
        QCOMPARE(keysOf(*session.appUnits).size(), 3);

        session.systemd.removeUnit(QStringLiteral("app-org.example.Real@1.service"));
        QVERIFY(changed.wait(signalWaitMs));
        QCOMPARE(keysOf(*session.appUnits), (QStringList{QStringLiteral("brave-browser"), QStringLiteral("org.example.Tray")}));
    }

    // an autostart unit that dies stays loaded and sends no job signal
    void followsStateChanges()
    {
        Session session;
        session.systemd.units = {{QStringLiteral("app-org.example.Tray@autostart.service"), {}}};
        QVERIFY(session.start());
        QCOMPARE(keysOf(*session.appUnits), QStringList{QStringLiteral("org.example.Tray")});

        QSignalSpy changed(session.appUnits.get(), &AppUnits::appsChanged);
        session.systemd.setActiveState(QStringLiteral("app-org.example.Tray@autostart.service"), QStringLiteral("inactive"));
        QVERIFY(changed.wait(signalWaitMs));
        QVERIFY(keysOf(*session.appUnits).isEmpty());
    }

    void stopsEveryUnitOfTheApp()
    {
        Session session;
        session.systemd.units = {
            {QStringLiteral("app-org.example.Tray@autostart.service"), {}},
            {QStringLiteral("app-org.example.Tray@0f3a.service"), {}},
            {QStringLiteral("app-brave\\x2dbrowser@1.service"), {}},
        };
        QVERIFY(session.start());

        QSignalSpy changed(session.appUnits.get(), &AppUnits::appsChanged);
        session.appUnits->stop(QStringLiteral("org.example.Tray"));
        QVERIFY(changed.wait(signalWaitMs));
        session.systemd.stopped.sort();
        QCOMPARE(session.systemd.stopped,
                 (QStringList{QStringLiteral("app-org.example.Tray@0f3a.service:replace"), QStringLiteral("app-org.example.Tray@autostart.service:replace")}));
        QCOMPARE(keysOf(*session.appUnits), QStringList{QStringLiteral("brave-browser")});
    }

    // a unit whose name says nothing, but whose SourcePath is a desktop file
    void fallsBackToSourcePath()
    {
        Session session;
        const QString applications = QStandardPaths::writableLocation(QStandardPaths::ApplicationsLocation);
        session.systemd.units = {
            {QStringLiteral("app-renamed@1.service"), {QStringLiteral("active"), applications + QStringLiteral("/org.example.Real.desktop")}},
            {QStringLiteral("app-other@1.service"), {QStringLiteral("active"), QStringLiteral("/etc/xdg/autostart/other.desktop")}},
        };
        QVERIFY(session.start());
        QTRY_COMPARE_WITH_TIMEOUT(keysOf(*session.appUnits), QStringList{QStringLiteral("org.example.Real")}, signalWaitMs);
        QCOMPARE(session.appUnits->units(QStringLiteral("org.example.Real")), QStringList{QStringLiteral("app-renamed@1.service")});
    }

    // Brave moves its main process into app-org.chromium.Chromium-<pid>.scope
    void chromiumScopeJoinsItsService()
    {
        Session session;
        session.systemd.units = {
            {QStringLiteral("app-brave\\x2dbrowser@411a.service"), {QStringLiteral("active"), {}, 25363}},
            {QStringLiteral("app-org.chromium.Chromium-25363.scope"), {}},
            {QStringLiteral("app-org.chromium.Chromium-999.scope"), {}},
        };
        QVERIFY(session.start());
        QTRY_COMPARE_WITH_TIMEOUT(session.appUnits->units(QStringLiteral("brave-browser")),
                                  (QStringList{QStringLiteral("app-brave\\x2dbrowser@411a.service"), QStringLiteral("app-org.chromium.Chromium-25363.scope")}),
                                  signalWaitMs);
        QCOMPARE(keysOf(*session.appUnits), QStringList{QStringLiteral("brave-browser")});
    }

    // systemd leaves the bus: the feature switches off, and comes back with it
    void followsSystemdOnTheBus()
    {
        auto session = std::make_unique<Session>();
        session->systemd.units = {{QStringLiteral("app-org.example.Tray@1.service"), {}}};
        QVERIFY(session->start());
        std::unique_ptr<AppUnits> appUnits = std::move(session->appUnits);
        QCOMPARE(keysOf(*appUnits), QStringList{QStringLiteral("org.example.Tray")});

        QSignalSpy available(appUnits.get(), &AppUnits::availableChanged);
        session.reset();
        QVERIFY(available.wait(signalWaitMs));
        QVERIFY(!appUnits->available());
        QVERIFY(appUnits->apps().isEmpty());

        Session again;
        again.systemd.units = {{QStringLiteral("app-brave\\x2dbrowser@1.service"), {}}};
        QVERIFY(again.service.registerService(systemdService));
        QVERIFY(again.service.connection().registerVirtualObject(systemdPath, &again.systemd, QDBusConnection::SubPath));
        QVERIFY(available.wait(signalWaitMs));
        QVERIFY(appUnits->available());
        QCOMPARE(keysOf(*appUnits), QStringList{QStringLiteral("brave-browser")});
    }

    void offWithoutSystemd()
    {
        AppUnits appUnits;
        QSignalSpy available(&appUnits, &AppUnits::availableChanged);
        QVERIFY(!available.wait(1000));
        QVERIFY(!appUnits.available());
        QVERIFY(appUnits.apps().isEmpty());
        QVERIFY(appUnits.units(QStringLiteral("org.example.Tray")).isEmpty());
        appUnits.stop(QStringLiteral("org.example.Tray"));
    }
};

GOLDENGLASS_TEST_MAIN(AppUnitsTest)
#include "appunits_test.moc"
