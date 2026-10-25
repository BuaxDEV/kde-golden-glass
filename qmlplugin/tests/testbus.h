/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

/*
    Ayudas para las pruebas de qmlplugin/ (ver qmlplugin/tests/CMakeLists.txt).

    1. Aislamiento (OBLIGATORIO en toda prueba): GOLDENGLASS_TEST_MAIN(Clase)
       sustituye a QTEST_MAIN. Antes de crear la aplicación apunta HOME y los
       XDG_* a un directorio temporal y activa
       QStandardPaths::setTestModeEnabled(true), de modo que ninguna prueba
       lee ni escribe la configuración real (~/.config/goldenglassrc, etc.).
       Una prueba con su propio main() debe crear un GoldenGlassTest::Sandbox
       antes de su QCoreApplication.

    2. Bus de sesión: nunca se usa el de la sesión real. Las pruebas con la
       opción DBUS de goldenglass_add_qmlplugin_test() corren bajo
       dbus-run-session, que crea un bus propio, y el entorno lleva
       GOLDENGLASS_TEST_BUS=1. GG_REQUIRE_SESSION_BUS() hace QSKIP si esa marca
       falta (sin dbus-run-session, o al ejecutar el binario a mano) o si el bus
       no conecta: así una prueba D-Bus nunca registra nombres falsos en el bus
       del usuario.

    3. FakeService: servicio falso en una conexión SEPARADA de la del código bajo
       prueba. Una llamada bloqueante de la prueba a un objeto suyo, desde el
       mismo hilo, se bloquearía (nadie atiende el bucle de eventos): usar
       GoldenGlassTest::call() o llamadas asíncronas.

    4. waitForSignal(): espera una señal de Qt con tiempo límite.

    Solo cabecera, sin dependencias fuera de Qt Core, Gui, Test y DBus.
*/

#include <QByteArray>
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusError>
#include <QDBusMessage>
#include <QDBusPendingCall>
#include <QDBusPendingCallWatcher>
#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QGuiApplication>
#include <QSignalSpy>
#include <QStandardPaths>
#include <QString>
#include <QTemporaryDir>
#include <QTimer>
#include <QUuid>
#include <QtTest>

namespace GoldenGlassTest
{

/*
    HOME, XDG_* y modo de prueba de QStandardPaths en un directorio temporal
    que se borra al destruirse. Crear antes de la QCoreApplication.
*/
class Sandbox
{
public:
    Sandbox()
    {
        const QString root = m_dir.path();
        const auto set = [&root](const char *variable, const QString &sub) {
            const QString path = root + QLatin1Char('/') + sub;
            QDir().mkpath(path);
            qputenv(variable, QFile::encodeName(path));
        };
        set("HOME", QStringLiteral("home"));
        set("XDG_CONFIG_HOME", QStringLiteral("config"));
        set("XDG_DATA_HOME", QStringLiteral("data"));
        set("XDG_CACHE_HOME", QStringLiteral("cache"));
        set("XDG_STATE_HOME", QStringLiteral("state"));
        set("XDG_RUNTIME_DIR", QStringLiteral("runtime")); // 0700 por QTemporaryDir
        // Sin configuración ni datos del sistema (/etc/xdg, /usr/share)
        set("XDG_CONFIG_DIRS", QStringLiteral("config-dirs"));
        set("XDG_DATA_DIRS", QStringLiteral("data-dirs"));
        QStandardPaths::setTestModeEnabled(true);
    }

    QString path() const
    {
        return m_dir.path();
    }

private:
    QTemporaryDir m_dir;
};

/*
    Verdadero si hay un bus de sesión propio de la prueba (ver arriba). Si no,
    deja en *why el motivo para el QSKIP.
*/
inline bool sessionBusAvailable(QString *why = nullptr)
{
    if (qgetenv("GOLDENGLASS_TEST_BUS") != "1") {
        if (why) {
            *why = QStringLiteral("no isolated session bus: run this test through ctest with dbus-run-session installed (GOLDENGLASS_TEST_BUS is not set)");
        }
        return false;
    }
    if (!QDBusConnection::sessionBus().isConnected()) {
        if (why) {
            *why = QStringLiteral("the isolated session bus does not accept connections");
        }
        return false;
    }
    return true;
}

/*
    Espera, con bucle de eventos, a que sender emita la señal. Devuelve false si
    pasa el tiempo. Para varias señales o argumentos, usar QSignalSpy.
*/
template<typename Sender, typename Signal>
bool waitForSignal(const Sender *sender, Signal signal, int timeoutMs = 5000)
{
    QSignalSpy spy(sender, signal);
    return spy.wait(timeoutMs);
}

/*
    Servicio D-Bus falso en su propia conexión al bus de sesión.

        FakeService fake;
        QVERIFY(fake.registerService(QStringLiteral("org.freedesktop.systemd1")));
        QVERIFY(fake.registerObject(QStringLiteral("/org/freedesktop/systemd1"), &miObjeto));

    El objeto exporta sus slots, señales y propiedades (QDBusConnection::
    ExportAll*) con la interfaz de Q_CLASSINFO("D-Bus Interface", "..."). Los
    nombres de método D-Bus son los de los slots.
*/
class FakeService
{
public:
    explicit FakeService(QDBusConnection::BusType type = QDBusConnection::SessionBus)
        : m_name(QStringLiteral("goldenglass-fake-") + QUuid::createUuid().toString(QUuid::WithoutBraces))
        , m_connection(QDBusConnection::connectToBus(type, m_name))
    {
    }

    ~FakeService()
    {
        m_connection = QDBusConnection(QString()); // suelta la referencia antes de cerrar
        QDBusConnection::disconnectFromBus(m_name);
    }

    FakeService(const FakeService &) = delete;
    FakeService &operator=(const FakeService &) = delete;

    bool isConnected() const
    {
        return m_connection.isConnected();
    }

    QDBusConnection &connection()
    {
        return m_connection;
    }

    bool registerService(const QString &serviceName)
    {
        return m_connection.registerService(serviceName);
    }

    bool registerObject(const QString &path,
                        QObject *object,
                        QDBusConnection::RegisterOptions options = QDBusConnection::ExportAllSlots | QDBusConnection::ExportAllSignals
                            | QDBusConnection::ExportAllProperties)
    {
        return m_connection.registerObject(path, object, options);
    }

    void unregisterObject(const QString &path)
    {
        m_connection.unregisterObject(path);
    }

    // Emite una señal D-Bus desde el servicio falso (sin necesidad de un slot).
    bool emitSignal(const QString &path, const QString &interface, const QString &name, const QVariantList &args = {})
    {
        QDBusMessage message = QDBusMessage::createSignal(path, interface, name);
        message.setArguments(args);
        return m_connection.send(message);
    }

private:
    QString m_name;
    QDBusConnection m_connection;
};

/*
    Llamada a un método D-Bus desde la prueba sin bloquear el bucle de eventos,
    para que atienda a un FakeService del mismo proceso. Devuelve la respuesta
    (o el error); si no llega a tiempo, un mensaje de error NoReply.
*/
inline QDBusMessage call(const QDBusMessage &message, int timeoutMs = 5000, const QDBusConnection &bus = QDBusConnection::sessionBus())
{
    QDBusPendingCall pending = bus.asyncCall(message, timeoutMs);
    QDBusPendingCallWatcher watcher(pending);
    QEventLoop loop;
    QObject::connect(&watcher, &QDBusPendingCallWatcher::finished, &loop, &QEventLoop::quit);
    if (!pending.isFinished()) {
        QTimer::singleShot(timeoutMs + 500, &loop, &QEventLoop::quit);
        loop.exec();
    }
    return pending.isFinished() ? pending.reply() : QDBusMessage::createError(QDBusError::NoReply, QStringLiteral("timeout waiting for the D-Bus reply"));
}

} // namespace GoldenGlassTest

// QSKIP de la función de prueba (o de todo initTestCase) si no hay bus propio.
#define GG_REQUIRE_SESSION_BUS()                                                                                                                               \
    do {                                                                                                                                                       \
        QString ggWhy;                                                                                                                                         \
        if (!GoldenGlassTest::sessionBusAvailable(&ggWhy)) {                                                                                                   \
            QSKIP(qPrintable(ggWhy));                                                                                                                          \
        }                                                                                                                                                      \
    } while (false)

// Sustituye a QTEST_MAIN: aislamiento obligatorio y QGuiApplication.
#define GOLDENGLASS_TEST_MAIN(TestObject)                                                                                                                      \
    int main(int argc, char *argv[])                                                                                                                           \
    {                                                                                                                                                          \
        GoldenGlassTest::Sandbox ggSandbox;                                                                                                                    \
        QGuiApplication app(argc, argv);                                                                                                                       \
        app.setAttribute(Qt::AA_Use96Dpi, true);                                                                                                               \
        TestObject tc;                                                                                                                                         \
        QTEST_SET_MAIN_SOURCE_PATH                                                                                                                             \
        return QTest::qExec(&tc, argc, argv);                                                                                                                  \
    }
