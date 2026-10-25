/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Pruebas de goldenglassshadowparams.h, sin KWin: sombra efectiva de la
 * ventana activa e inactiva y clave con la que se comparten las texturas.
 */

#include "goldenglassshadowparams.h"

#include <QTest>

using namespace GoldenGlass;

namespace
{
ShadowStyle style(const ShadowSetting &setting, int outlineTop = 0)
{
    return makeShadowStyle(setting, 0xFF000000u, 12.0, outlineTop, Tokens::ShadowOutlineAlpha);
}
}

class ShadowParamsTest : public QObject
{
    Q_OBJECT

private Q_SLOTS:
    void factoryDefaults()
    {
        // los tokens ya cumplen la regla: la inactiva no supera a la activa
        const ShadowSettings s = resolveShadowSettings({Tokens::ShadowSize, Tokens::ShadowStrength},
                                                       {Tokens::InactiveShadowSize, Tokens::InactiveShadowStrength});
        QCOMPARE(s.active, (ShadowSetting{Tokens::ShadowSize, Tokens::ShadowStrength}));
        QCOMPARE(s.inactive, (ShadowSetting{Tokens::InactiveShadowSize, Tokens::InactiveShadowStrength}));
        QVERIFY(s.inactive.size <= s.active.size);
        QVERIFY(s.inactive.strength <= s.active.strength);
    }

    void inactiveIsSmallerOrEqual_data()
    {
        QTest::addColumn<int>("activeSize");
        QTest::addColumn<int>("activeStrength");
        QTest::addColumn<int>("inactiveSize");
        QTest::addColumn<int>("inactiveStrength");
        QTest::addColumn<int>("expectedSize");
        QTest::addColumn<int>("expectedStrength");

        QTest::newRow("smaller") << int(ShadowSizeVeryLarge) << 115 << int(ShadowSizeMedium) << 64 << int(ShadowSizeMedium) << 64;
        QTest::newRow("larger size") << int(ShadowSizeSmall) << 115 << int(ShadowSizeLarge) << 64 << int(ShadowSizeSmall) << 64;
        QTest::newRow("stronger") << int(ShadowSizeLarge) << 60 << int(ShadowSizeMedium) << 200 << int(ShadowSizeMedium) << 60;
        QTest::newRow("both larger") << int(ShadowSizeMedium) << 60 << int(ShadowSizeVeryLarge) << 255 << int(ShadowSizeMedium) << 60;
        QTest::newRow("inactive none") << int(ShadowSizeLarge) << 115 << int(ShadowSizeNone) << 64 << int(ShadowSizeNone) << 64;
        // fuera de rango cuenta como Large, también para el mínimo
        QTest::newRow("invalid active") << 42 << 115 << int(ShadowSizeVeryLarge) << 64 << int(ShadowSizeLarge) << 64;
        QTest::newRow("invalid inactive") << int(ShadowSizeVeryLarge) << 115 << -1 << 64 << int(ShadowSizeLarge) << 64;
    }

    void inactiveIsSmallerOrEqual()
    {
        QFETCH(int, activeSize);
        QFETCH(int, activeStrength);
        QFETCH(int, inactiveSize);
        QFETCH(int, inactiveStrength);
        QFETCH(int, expectedSize);
        QFETCH(int, expectedStrength);

        const ShadowSettings s = resolveShadowSettings({activeSize, activeStrength}, {inactiveSize, inactiveStrength});
        QCOMPARE(s.active, (ShadowSetting{normalizedShadowSize(activeSize), activeStrength}));
        QCOMPARE(s.inactive, (ShadowSetting{expectedSize, expectedStrength}));
    }

    void noActiveShadowMeansNoInactiveShadow()
    {
        const ShadowSettings s = resolveShadowSettings({ShadowSizeNone, 115}, {ShadowSizeMedium, 64});
        QCOMPARE(s.active.size, int(ShadowSizeNone));
        QCOMPARE(s.inactive.size, int(ShadowSizeNone));
        QVERIFY(style(s.active).isNone());
        QVERIFY(style(s.inactive).isNone());
    }

    void sizesFollowTheTokens()
    {
        QVERIFY(lookupShadowParams(ShadowSizeNone).isNone());
        QCOMPARE(lookupShadowParams(ShadowSizeMedium).shadow1.radius, Tokens::ShadowMediumRadius);
        QCOMPARE(lookupShadowParams(ShadowSizeMedium).offset.y(), Tokens::ShadowMediumOffset);
        QCOMPARE(lookupShadowParams(ShadowSizeVeryLarge).shadow2.radius, Tokens::ShadowVeryLargeAmbientRadius);
        QCOMPARE(lookupShadowParams(99).shadow1.radius, Tokens::ShadowLargeRadius);
    }

    void equalSettingsShareTheKey()
    {
        // inactiva configurada mayor que la activa: queda igual y comparte textura
        const ShadowSettings s = resolveShadowSettings({ShadowSizeMedium, 100}, {ShadowSizeVeryLarge, 200});
        QCOMPARE(s.active, s.inactive);
        QVERIFY(style(s.active).key() == style(s.inactive).key());
    }

    void differentSettingsHaveDifferentKeys()
    {
        const ShadowSettings s = resolveShadowSettings({ShadowSizeVeryLarge, 115}, {ShadowSizeMedium, 64});
        QVERIFY(style(s.active).key() != style(s.inactive).key());

        // solo cambia la fuerza
        QVERIFY(style({ShadowSizeMedium, 64}).key() != style({ShadowSizeMedium, 65}).key());
        // solo cambia el contorno (barra flotante)
        QVERIFY(style({ShadowSizeMedium, 64}, 0).key() != style({ShadowSizeMedium, 64}, 30).key());
        // solo cambia la opacidad del contorno, el color o el radio
        const ShadowStyle base = style({ShadowSizeMedium, 64});
        ShadowStyle other = base;
        other.outlineAlpha = 0.2;
        QVERIFY(base.key() != other.key());
        other = base;
        other.color = 0xFF202020u;
        QVERIFY(base.key() != other.key());
        other = base;
        other.cornerRadius = 13.5;
        QVERIFY(base.key() != other.key());
    }
};

QTEST_GUILESS_MAIN(ShadowParamsTest)
#include "shadowparams_test.moc"
