/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// Camino dbus-run-session: un servicio falso registrado en una conexión
// aparte, al que la prueba llama como lo haría el código real.

#include "testbus.h"

class FakeObject : public QObject
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.goldenglass.Test")

public:
    int calls = 0;

public Q_SLOTS:
    QString Ping(const QString &text)
    {
        ++calls;
        return QStringLiteral("pong:") + text;
    }
};

// Receptor de una señal D-Bus del servicio falso
class Listener : public QObject
{
    Q_OBJECT
public:
    QStringList received;

public Q_SLOTS:
    void onChanged(const QString &value)
    {
        received << value;
        Q_EMIT changed();
    }

Q_SIGNALS:
    void changed();
};

class FakeServiceTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void initTestCase()
    {
        GG_REQUIRE_SESSION_BUS();
    }

    void callsTheFakeService()
    {
        GoldenGlassTest::FakeService fake;
        QVERIFY(fake.isConnected());
        FakeObject object;
        QVERIFY(fake.registerService(QStringLiteral("org.goldenglass.Test")));
        QVERIFY(fake.registerObject(QStringLiteral("/Test"), &object));

        QDBusMessage message = QDBusMessage::createMethodCall(QStringLiteral("org.goldenglass.Test"),
                                                              QStringLiteral("/Test"),
                                                              QStringLiteral("org.goldenglass.Test"),
                                                              QStringLiteral("Ping"));
        message << QStringLiteral("hi");
        const QDBusMessage reply = GoldenGlassTest::call(message);
        QCOMPARE(reply.type(), QDBusMessage::ReplyMessage);
        QCOMPARE(reply.arguments().value(0).toString(), QStringLiteral("pong:hi"));
        QCOMPARE(object.calls, 1);
    }

    void receivesFakeSignals()
    {
        GoldenGlassTest::FakeService fake;
        QVERIFY(fake.registerService(QStringLiteral("org.goldenglass.Test2")));

        Listener listener;
        QVERIFY(QDBusConnection::sessionBus().connect(QStringLiteral("org.goldenglass.Test2"),
                                                      QStringLiteral("/Test"),
                                                      QStringLiteral("org.goldenglass.Test"),
                                                      QStringLiteral("Changed"),
                                                      &listener,
                                                      SLOT(onChanged(QString))));

        QSignalSpy spy(&listener, &Listener::changed);
        QVERIFY(fake.emitSignal(QStringLiteral("/Test"), QStringLiteral("org.goldenglass.Test"), QStringLiteral("Changed"), {QStringLiteral("x")}));
        QVERIFY(spy.wait(5000));
        QCOMPARE(listener.received, QStringList{QStringLiteral("x")});
    }

    void unknownServiceFails()
    {
        QDBusMessage message = QDBusMessage::createMethodCall(QStringLiteral("org.goldenglass.NoSuchService"),
                                                              QStringLiteral("/"),
                                                              QStringLiteral("org.goldenglass.Test"),
                                                              QStringLiteral("Ping"));
        QCOMPARE(GoldenGlassTest::call(message, 2000).type(), QDBusMessage::ErrorMessage);
    }
};

GOLDENGLASS_TEST_MAIN(FakeServiceTest)
#include "fakeservice_test.moc"
