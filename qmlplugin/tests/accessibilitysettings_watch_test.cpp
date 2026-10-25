/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// AccessibilitySettings sigue en vivo goldenglassrc [Accessibility] con
// KConfigWatcher, que usa el bus de sesión (prueba DBUS: corre bajo
// dbus-run-session).

#include "accessibilitysettings.h"

#include "goldenglass_tokens.h"
#include "testbus.h"

#include <KConfig>
#include <KConfigGroup>

class AccessibilitySettingsWatchTest : public QObject
{
    Q_OBJECT

    // Escribe una clave con KConfig::Notify, como goldenglass-glass y
    // goldenglass-windows (aviso por D-Bus).
    static bool writeNotify(const QString &group, const char *key, bool value)
    {
        KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
        config.group(group).writeEntry(key, value, KConfig::Notify);
        return config.sync();
    }

private Q_SLOTS:
    void initTestCase()
    {
        GG_REQUIRE_SESSION_BUS();
    }

    // Cada clave cambia su propiedad y solo avisa de esa.
    void reactsToEachKey_data()
    {
        QTest::addColumn<QByteArray>("key");
        QTest::addColumn<bool>("factory");
        QTest::newRow("ShowBorders") << QByteArray("ShowBorders") << GoldenGlass::Tokens::AccessibilityShowBorders;
        QTest::newRow("ReduceTransparency") << QByteArray("ReduceTransparency") << GoldenGlass::Tokens::AccessibilityReduceTransparency;
        QTest::newRow("ReduceMotion") << QByteArray("ReduceMotion") << GoldenGlass::Tokens::AccessibilityReduceMotion;
    }

    void reactsToEachKey()
    {
        QFETCH(QByteArray, key);
        QFETCH(bool, factory);

        AccessibilitySettings settings;
        const auto value = [&settings, &key] {
            return key == "ShowBorders" ? settings.showBorders() : key == "ReduceTransparency" ? settings.reduceTransparency() : settings.reduceMotion();
        };
        QCOMPARE(value(), factory);

        QSignalSpy borders(&settings, &AccessibilitySettings::showBordersChanged);
        QSignalSpy transparency(&settings, &AccessibilitySettings::reduceTransparencyChanged);
        QSignalSpy motion(&settings, &AccessibilitySettings::reduceMotionChanged);
        QSignalSpy &own = key == "ShowBorders" ? borders : key == "ReduceTransparency" ? transparency : motion;

        QVERIFY(writeNotify(QStringLiteral("Accessibility"), key.constData(), !factory));
        QVERIFY(own.wait(5000));
        QCOMPARE(value(), !factory);
        QCOMPARE(borders.count() + transparency.count() + motion.count(), 1);

        // vuelta a fábrica para la fila siguiente (y aviso de vuelta)
        QVERIFY(writeNotify(QStringLiteral("Accessibility"), key.constData(), factory));
        QVERIFY(own.wait(5000));
        QCOMPARE(value(), factory);
    }

    // Un aviso de otro grupo de goldenglassrc no relee [Accessibility].
    void ignoresOtherGroups()
    {
        AccessibilitySettings settings;
        QSignalSpy borders(&settings, &AccessibilitySettings::showBordersChanged);

        // la clave cambia en el archivo sin aviso propio...
        {
            KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
            config.group(QStringLiteral("Accessibility")).writeEntry("ShowBorders", !GoldenGlass::Tokens::AccessibilityShowBorders);
            QVERIFY(config.sync());
        }
        // ...y llega un aviso de [Glass]: no se relee
        QVERIFY(writeNotify(QStringLiteral("Glass"), "Unrelated", true));
        QVERIFY(!borders.wait(1000));
        QCOMPARE(settings.showBorders(), GoldenGlass::Tokens::AccessibilityShowBorders);
    }
};

GOLDENGLASS_TEST_MAIN(AccessibilitySettingsWatchTest)
#include "accessibilitysettings_watch_test.moc"
