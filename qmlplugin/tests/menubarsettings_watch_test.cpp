/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// MenuBarSettings sigue en vivo los cambios de goldenglassrc con KConfigWatcher,
// que usa el bus de sesión (prueba DBUS: corre bajo dbus-run-session).

#include "menubarsettings.h"

#include "goldenglass_tokens.h"
#include "testbus.h"

#include <KConfig>
#include <KConfigGroup>

class MenuBarSettingsWatchTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void initTestCase()
    {
        GG_REQUIRE_SESSION_BUS();
    }

    void reactsToConfigChange()
    {
        MenuBarSettings settings;
        QCOMPARE(settings.background(), GoldenGlass::Tokens::MenubarBackground);

        const bool flipped = !GoldenGlass::Tokens::MenubarBackground;
        QSignalSpy spy(&settings, &MenuBarSettings::backgroundChanged);

        // KConfig::Notify avisa por D-Bus, como hacen el módulo «Vidrio» y goldenglass-glass
        KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
        config.group(QStringLiteral("Plasma")).writeEntry("MenubarBackground", flipped, KConfig::Notify);
        QVERIFY(config.sync());

        QVERIFY(spy.wait(5000));
        QCOMPARE(settings.background(), flipped);
    }
};

GOLDENGLASS_TEST_MAIN(MenuBarSettingsWatchTest)
#include "menubarsettings_watch_test.moc"
