/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// Comprueba que GOLDENGLASS_TEST_MAIN aísla de verdad el entorno.

#include "testbus.h"

#include <QStandardPaths>

class SandboxTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void pathsAreInsideTheSandbox()
    {
        QVERIFY(QStandardPaths::isTestModeEnabled());
        const QString tmp = QDir::tempPath();
        const QString home = qEnvironmentVariable("HOME");
        const QString configHome = qEnvironmentVariable("XDG_CONFIG_HOME");
        QVERIFY2(home.startsWith(tmp), qPrintable(home));
        QVERIFY2(configHome.startsWith(tmp), qPrintable(configHome));
        const QString config = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
        QVERIFY2(config.startsWith(tmp), qPrintable(config));
    }

    void noSessionBusWithoutTheMarker()
    {
        // Esta prueba no es DBUS: nunca tiene un bus propio
        QCOMPARE(qgetenv("GOLDENGLASS_TEST_BUS"), QByteArray("0"));
        QVERIFY(!GoldenGlassTest::sessionBusAvailable());
        QVERIFY(!QDBusConnection::sessionBus().isConnected());
    }
};

GOLDENGLASS_TEST_MAIN(SandboxTest)
#include "sandbox_test.moc"
