/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// AccessibilitySettings lee goldenglassrc [Accessibility] (sin bus).

#include "accessibilitysettings.h"

#include "goldenglass_tokens.h"
#include "testbus.h"

#include <KConfig>
#include <KConfigGroup>
#include <KSharedConfig>

class AccessibilitySettingsTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void defaultsFromTokens()
    {
        AccessibilitySettings settings;
        QCOMPARE(settings.showBorders(), GoldenGlass::Tokens::AccessibilityShowBorders);
        QCOMPARE(settings.reduceTransparency(), GoldenGlass::Tokens::AccessibilityReduceTransparency);
        QCOMPARE(settings.reduceMotion(), GoldenGlass::Tokens::AccessibilityReduceMotion);
    }

    void otherGroupsDoNotCount()
    {
        // las mismas claves en otro grupo no son las de accesibilidad
        {
            KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
            KConfigGroup glass = config.group(QStringLiteral("Glass"));
            glass.writeEntry("ShowBorders", !GoldenGlass::Tokens::AccessibilityShowBorders);
            glass.writeEntry("ReduceTransparency", !GoldenGlass::Tokens::AccessibilityReduceTransparency);
            glass.writeEntry("ReduceMotion", !GoldenGlass::Tokens::AccessibilityReduceMotion);
            QVERIFY(config.sync());
        }
        KSharedConfig::openConfig(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig)->reparseConfiguration();

        AccessibilitySettings settings;
        QCOMPARE(settings.showBorders(), GoldenGlass::Tokens::AccessibilityShowBorders);
        QCOMPARE(settings.reduceTransparency(), GoldenGlass::Tokens::AccessibilityReduceTransparency);
        QCOMPARE(settings.reduceMotion(), GoldenGlass::Tokens::AccessibilityReduceMotion);
    }

    void readsGoldenglassrc()
    {
        {
            KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
            KConfigGroup group = config.group(QStringLiteral("Accessibility"));
            group.writeEntry("ShowBorders", !GoldenGlass::Tokens::AccessibilityShowBorders);
            group.writeEntry("ReduceTransparency", !GoldenGlass::Tokens::AccessibilityReduceTransparency);
            group.writeEntry("ReduceMotion", !GoldenGlass::Tokens::AccessibilityReduceMotion);
            QVERIFY(config.sync());
        }
        // el objeto compartido ya leyó el archivo en las pruebas anteriores
        KSharedConfig::openConfig(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig)->reparseConfiguration();

        AccessibilitySettings settings;
        QCOMPARE(settings.showBorders(), !GoldenGlass::Tokens::AccessibilityShowBorders);
        QCOMPARE(settings.reduceTransparency(), !GoldenGlass::Tokens::AccessibilityReduceTransparency);
        QCOMPARE(settings.reduceMotion(), !GoldenGlass::Tokens::AccessibilityReduceMotion);
    }
};

GOLDENGLASS_TEST_MAIN(AccessibilitySettingsTest)
#include "accessibilitysettings_test.moc"
