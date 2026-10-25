/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// Ajustes de la decoración (InternalSettings): goldenglassrc [Accessibility],
// con los tokens de fábrica. Aislada con GOLDENGLASS_TEST_MAIN de
// qmlplugin/tests/testbus.h: nunca lee ni escribe la configuración real.

#include "goldenglass_tokens.h"
#include "goldenglasssettings.h"
#include "testbus.h"

#include <KConfig>
#include <KConfigGroup>

using GoldenGlass::InternalSettings;

class InternalSettingsTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void accessibilityDefaults()
    {
        InternalSettings settings;
        settings.load();
        QCOMPARE(settings.showBorders(), GoldenGlass::Tokens::AccessibilityShowBorders);
        QCOMPARE(settings.reduceTransparency(), GoldenGlass::Tokens::AccessibilityReduceTransparency);
        QCOMPARE(settings.reduceMotion(), GoldenGlass::Tokens::AccessibilityReduceMotion);
    }

    void readsAccessibilityGroup()
    {
        {
            KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
            KConfigGroup group = config.group(QStringLiteral("Accessibility"));
            group.writeEntry("ShowBorders", !GoldenGlass::Tokens::AccessibilityShowBorders);
            group.writeEntry("ReduceTransparency", !GoldenGlass::Tokens::AccessibilityReduceTransparency);
            group.writeEntry("ReduceMotion", !GoldenGlass::Tokens::AccessibilityReduceMotion);
            QVERIFY(config.sync());
        }

        InternalSettings settings;
        settings.load(); // relee el archivo
        QCOMPARE(settings.showBorders(), !GoldenGlass::Tokens::AccessibilityShowBorders);
        QCOMPARE(settings.reduceTransparency(), !GoldenGlass::Tokens::AccessibilityReduceTransparency);
        QCOMPARE(settings.reduceMotion(), !GoldenGlass::Tokens::AccessibilityReduceMotion);
    }

    // Guardar otros ajustes de la decoración no escribe las claves de
    // accesibilidad que nadie tocó (las de goldenglass-glass quedan intactas).
    void saveKeepsAccessibility()
    {
        InternalSettings settings;
        settings.load();
        {
            // otra herramienta cambia una clave después de cargar
            KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
            config.group(QStringLiteral("Accessibility")).writeEntry("ShowBorders", GoldenGlass::Tokens::AccessibilityShowBorders);
            QVERIFY(config.sync());
        }
        settings.setDrawTitleBarSeparator(!settings.drawTitleBarSeparator());
        QVERIFY(settings.save());

        const KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
        const KConfigGroup group = config.group(QStringLiteral("Accessibility"));
        QCOMPARE(group.readEntry("ShowBorders", !GoldenGlass::Tokens::AccessibilityShowBorders), GoldenGlass::Tokens::AccessibilityShowBorders);
        QCOMPARE(group.readEntry("ReduceMotion", GoldenGlass::Tokens::AccessibilityReduceMotion), !GoldenGlass::Tokens::AccessibilityReduceMotion);
    }
};

GOLDENGLASS_TEST_MAIN(InternalSettingsTest)
#include "internalsettings_test.moc"
