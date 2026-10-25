/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// MenuBarSettings lee goldenglassrc [Plasma] MenubarBackground (sin bus).

#include "menubarsettings.h"

#include "goldenglass_tokens.h"
#include "testbus.h"

#include <KConfig>
#include <KConfigGroup>
#include <KSharedConfig>

class MenuBarSettingsTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void defaultsFromTokens()
    {
        MenuBarSettings settings;
        QCOMPARE(settings.background(), GoldenGlass::Tokens::MenubarBackground);
        QCOMPARE(settings.inactiveOpacity(), GoldenGlass::Tokens::MenubarInactiveOpacity);
    }

    void readsGoldenglassrc()
    {
        const bool flipped = !GoldenGlass::Tokens::MenubarBackground;
        {
            KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
            config.group(QStringLiteral("Plasma")).writeEntry("MenubarBackground", flipped);
            QVERIFY(config.sync());
        }
        // el objeto compartido ya leyó el archivo (vacío) en la prueba anterior
        KSharedConfig::openConfig(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig)->reparseConfiguration();

        MenuBarSettings settings;
        QCOMPARE(settings.background(), flipped);
    }
};

GOLDENGLASS_TEST_MAIN(MenuBarSettingsTest)
#include "menubarsettings_test.moc"
