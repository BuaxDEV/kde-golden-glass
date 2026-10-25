/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// parseUnitName() with the unit names seen on a real Plasma 6.8 session and in
// the SP-08 sandbox (docs/ARCHITECTURE.md, «Apps en segundo plano»).

#include "unitname.h"

#include "testbus.h"

using GoldenGlass::UnitName;

Q_DECLARE_METATYPE(UnitName::Origin)

class UnitNameTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void parses_data()
    {
        QTest::addColumn<QString>("unit");
        QTest::addColumn<UnitName::Origin>("origin");
        QTest::addColumn<QString>("appId");
        QTest::addColumn<QString>("launcher");
        QTest::addColumn<QString>("instance");

        const auto service = UnitName::Origin::Service;
        const auto scope = UnitName::Origin::Scope;
        const auto dbus = UnitName::Origin::DBusActivation;

        // KIO (dock, Apps, Kickoff, KRunner, Dolphin)
        QTest::newRow("kio service") << QStringLiteral("app-brave\\x2dbrowser@411abb663e7a4f3987533771d8c613d0.service") << service
                                     << QStringLiteral("brave-browser") << QString() << QStringLiteral("411abb663e7a4f3987533771d8c613d0");
        QTest::newRow("kio reverse-dns") << QStringLiteral("app-org.kde.kwrite@b0902d1d072145bfbf1313e30de97e13.service") << service
                                         << QStringLiteral("org.kde.kwrite") << QString() << QStringLiteral("b0902d1d072145bfbf1313e30de97e13");
        QTest::newRow("kio flatpak") << QStringLiteral("app-net.pcsx2.PCSX2@d4cb53dcf89b4bff8da93c52eac2ab17.service") << service
                                     << QStringLiteral("net.pcsx2.PCSX2") << QString() << QStringLiteral("d4cb53dcf89b4bff8da93c52eac2ab17");
        QTest::newRow("kio scope") << QStringLiteral("app-org.kde.dolphin-4242.scope") << scope << QStringLiteral("org.kde.dolphin") << QString()
                                   << QStringLiteral("4242");
        // systemd-xdg-autostart-generator
        QTest::newRow("autostart") << QStringLiteral("app-arch\\x2dupdate\\x2dtray@autostart.service") << service << QStringLiteral("arch-update-tray")
                                   << QString() << QStringLiteral("autostart");
        QTest::newRow("autostart dashes") << QStringLiteral("app-org.kde.plasma\\x2dfallback\\x2dsession\\x2drestore@autostart.service") << service
                                          << QStringLiteral("org.kde.plasma-fallback-session-restore") << QString() << QStringLiteral("autostart");
        // a static unit named in the desktop file's SystemdService
        QTest::newRow("static") << QStringLiteral("app-com.mitchellh.ghostty.service") << service << QStringLiteral("com.mitchellh.ghostty") << QString()
                                << QString();
        // dbus-broker's D-Bus activation
        QTest::newRow("dbus") << QStringLiteral("dbus-:1.2-org.kde.kdeconnect@0.service") << dbus << QStringLiteral("org.kde.kdeconnect") << QString()
                              << QStringLiteral("0");
        QTest::newRow("dbus other broker") << QStringLiteral("dbus-:1.23-org.a11y.atspi.Registry@0.service") << dbus
                                           << QStringLiteral("org.a11y.atspi.Registry") << QString() << QStringLiteral("0");
        // launchers that create their own scope
        QTest::newRow("chromium") << QStringLiteral("app-org.chromium.Chromium-25363.scope") << scope << QStringLiteral("org.chromium.Chromium") << QString()
                                  << QStringLiteral("25363");
        QTest::newRow("flatpak run") << QStringLiteral("app-flatpak-net.pcsx2.PCSX2-12345.scope") << scope << QStringLiteral("net.pcsx2.PCSX2")
                                     << QStringLiteral("flatpak") << QStringLiteral("12345");
        QTest::newRow("gnome") << QStringLiteral("app-gnome-org.gnome.Nautilus-3051.scope") << scope << QStringLiteral("org.gnome.Nautilus")
                               << QStringLiteral("gnome") << QStringLiteral("3051");
        QTest::newRow("launcher service") << QStringLiteral("app-kde-org.kde.kate@1.service") << service << QStringLiteral("org.kde.kate")
                                          << QStringLiteral("kde") << QStringLiteral("1");
        QTest::newRow("utf-8 escape") << QStringLiteral("app-caf\\xc3\\xa9@1.service") << service << QStringLiteral("café") << QString() << QStringLiteral("1");
    }

    void parses()
    {
        QFETCH(QString, unit);
        QFETCH(UnitName::Origin, origin);
        QFETCH(QString, appId);
        QFETCH(QString, launcher);
        QFETCH(QString, instance);

        const UnitName name = GoldenGlass::parseUnitName(unit);
        QVERIFY(name.isValid());
        QCOMPARE(name.origin, origin);
        QCOMPARE(name.appId, appId);
        QCOMPARE(name.launcher, launcher);
        QCOMPARE(name.instance, instance);
    }

    void rejects_data()
    {
        QTest::addColumn<QString>("unit");
        QTest::newRow("empty") << QString();
        QTest::newRow("slice") << QStringLiteral("app-dbus\\x2d:1.2\\x2dorg.kde.kdeconnect.slice");
        QTest::newRow("not an app") << QStringLiteral("plasma-plasmashell.service");
        QTest::newRow("dbus-broker itself") << QStringLiteral("dbus-broker.service");
        QTest::newRow("dbus scope") << QStringLiteral("dbus-:1.2-org.kde.kdeconnect-12.scope");
        QTest::newRow("ghostty surface") << QStringLiteral("app-ghostty-surface-transient-1920.scope");
        QTest::newRow("scope without instance") << QStringLiteral("app-org.kde.dolphin.scope");
        QTest::newRow("empty id") << QStringLiteral("app-@1.service");
        QTest::newRow("bad escape") << QStringLiteral("app-foo\\x2@1.service");
        QTest::newRow("not hex") << QStringLiteral("app-foo\\xzz@1.service");
        QTest::newRow("dbus without unique name") << QStringLiteral("dbus-org.kde.kdeconnect@0.service");
    }

    void rejects()
    {
        QFETCH(QString, unit);
        QVERIFY(!GoldenGlass::parseUnitName(unit).isValid());
    }

    void autostartOnlyForServices()
    {
        QVERIFY(GoldenGlass::parseUnitName(QStringLiteral("app-org.kde.kdeconnect.daemon@autostart.service")).isAutostart());
        QVERIFY(!GoldenGlass::parseUnitName(QStringLiteral("app-org.kde.kwrite@b0902d1d.service")).isAutostart());
        QVERIFY(!GoldenGlass::parseUnitName(QStringLiteral("dbus-:1.2-autostart@autostart.service")).isAutostart());
    }

    void scopePid()
    {
        QCOMPARE(GoldenGlass::parseUnitName(QStringLiteral("app-org.chromium.Chromium-25363.scope")).scopePid(), 25363);
        QCOMPARE(GoldenGlass::parseUnitName(QStringLiteral("app-foo-transient.scope")).scopePid(), 0);
        QCOMPARE(GoldenGlass::parseUnitName(QStringLiteral("app-foo@25363.service")).scopePid(), 0);
    }
};

GOLDENGLASS_TEST_MAIN(UnitNameTest)
#include "unitname_test.moc"
