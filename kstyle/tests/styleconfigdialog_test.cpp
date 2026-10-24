// SPDX-FileCopyrightText: 2026 GoldenGlass contributors
// SPDX-License-Identifier: GPL-3.0-or-later
//
// El diálogo del estilo (StyleConfig) con su .ui real: qué marca como cambiado,
// qué restaura «Predeterminados» y que recargar no duplica opciones.

#include <QCheckBox>
#include <QComboBox>
#include <QSignalSpy>
#include <QSpinBox>
#include <QStandardPaths>
#include <QTest>

#include "config/goldenglassstyleconfig.h"
#include "goldenglassstyleconfigdata.h"

using GoldenGlass::StyleConfig;
using GoldenGlass::StyleConfigData;

class StyleConfigDialogTest : public QObject
{
    Q_OBJECT

private Q_SLOTS:
    void initTestCase()
    {
        QStandardPaths::setTestModeEnabled(true);
    }

    void init()
    {
        StyleConfigData::self()->setDefaults();
        StyleConfigData::self()->save();
    }

    void reloadKeepsShadowSizes()
    {
        StyleConfig config(nullptr);
        auto *sizes = config.findChild<QComboBox *>(QStringLiteral("_shadowSize"));
        QVERIFY(sizes);
        const int count = sizes->count();
        QCOMPARE(count, 5);
        config.load();
        config.reset();
        QCOMPARE(sizes->count(), count);
    }

    void shadowStrengthMarksChanged()
    {
        StyleConfig config(nullptr);
        auto *strength = config.findChild<QSpinBox *>(QStringLiteral("_shadowStrength"));
        QVERIFY(strength);
        strength->setEnabled(true);
        QSignalSpy changed(&config, &StyleConfig::changed);
        strength->setValue(strength->value() == strength->minimum() ? strength->maximum() : strength->minimum());
        QVERIFY(!changed.isEmpty());
        QCOMPARE(changed.last().at(0).toBool(), true);
    }

    void roundedRubberBandMarksChanged()
    {
        StyleConfig config(nullptr);
        auto *box = config.findChild<QCheckBox *>(QStringLiteral("_roundedRubberBandFrame"));
        QVERIFY(box);
        QSignalSpy changed(&config, &StyleConfig::changed);
        box->toggle();
        QCOMPARE(changed.last().at(0).toBool(), true);
        box->toggle();
        QCOMPARE(changed.last().at(0).toBool(), false);
    }

    void defaultsRestoreFactoryValues()
    {
        // un valor guardado distinto del de fábrica y dentro del rango del control
        const int factory = StyleConfigData::self()->shadowStrength();
        const int saved = factory == 255 ? 254 : factory + 1;
        StyleConfigData::self()->setShadowStrength(saved);
        StyleConfigData::self()->save();

        StyleConfig config(nullptr);
        auto *strength = config.findChild<QSpinBox *>(QStringLiteral("_shadowStrength"));
        QVERIFY(strength);
        QCOMPARE(strength->value(), saved);

        QSignalSpy changed(&config, &StyleConfig::changed);
        config.defaults();
        QCOMPARE(strength->value(), factory);
        // lo guardado sigue siendo la referencia: hay cambios por aplicar
        QCOMPARE(changed.last().at(0).toBool(), true);
        QCOMPARE(StyleConfigData::self()->shadowStrength(), saved);
    }
};

QTEST_MAIN(StyleConfigDialogTest)

#include "styleconfigdialog_test.moc"
