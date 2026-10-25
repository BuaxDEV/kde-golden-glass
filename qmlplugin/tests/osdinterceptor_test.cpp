/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// OsdInterceptor and OsdHost against a fake of plasmashell's Osd on the test bus
// (DBUS test: runs under dbus-run-session). The fake lives where Plasma's does,
// on this process's session connection; plasma-pa, powerdevil and the lock
// screen are played by a FakeService, a connection of their own.

#include "osdhost.h"
#include "osdinterceptor.h"

#include "testbus.h"

#include <KConfigGroup>
#include <KLocalizedString>
#include <KSharedConfig>

#include <QDBusConnection>
#include <QDBusMessage>
#include <QFile>
#include <QGuiApplication>
#include <QRect>

#include <memory>

namespace
{
const QString plasmaService = QStringLiteral("org.kde.plasmashell");
const QString osdPath = QStringLiteral("/org/kde/osdService");
const QString osdInterface = QStringLiteral("org.kde.osdService");
constexpr QDBusConnection::RegisterOptions osdExport = QDBusConnection::ExportAllSlots | QDBusConnection::ExportAllSignals;
const QRect leftScreen(0, 0, 1600, 1000);
const QRect rightScreen(1600, 0, 1600, 1000);

// Two named screens side by side, like two outputs of KWin: Qt's offscreen
// platform makes them from a configuration file
const char *const twoScreens = R"({"screens": [
    {"name": "DP-1", "x": 0, "y": 0, "width": 1600, "height": 1000, "logicalDpi": 96},
    {"name": "DP-2", "x": 1600, "y": 0, "width": 1600, "height": 1000, "logicalDpi": 96}
]})";
} // namespace

/*
    Plasma's Osd as plasmashell 6.8 exports it (shell/osd.h): same slots and
    signals. It records what reaches it and, like Plasma, answers a text OSD
    with osdText.
*/
class FakePlasmaOsd : public QObject
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.kde.osdService")

public:
    QStringList calls;

public Q_SLOTS:
    void brightnessChanged(int percent)
    {
        record(QStringLiteral("brightnessChanged %1").arg(percent));
    }
    void screenBrightnessChanged(int percent, const QString &displayId, const QString &displayLabel, int priority, const QRect &screenRect)
    {
        Q_UNUSED(displayLabel)
        Q_UNUSED(priority)
        Q_UNUSED(screenRect)
        record(QStringLiteral("screenBrightnessChanged %1 %2").arg(percent).arg(displayId));
    }
    void keyboardBrightnessChanged(int percent)
    {
        record(QStringLiteral("keyboardBrightnessChanged %1").arg(percent));
    }
    void volumeChanged(int percent)
    {
        record(QStringLiteral("volumeChanged %1").arg(percent));
    }
    void volumeChanged(int percent, int maximumPercent)
    {
        record(QStringLiteral("volumeChanged %1 %2").arg(percent).arg(maximumPercent));
    }
    void microphoneVolumeChanged(int percent)
    {
        record(QStringLiteral("microphoneVolumeChanged %1").arg(percent));
    }
    void mediaPlayerVolumeChanged(int percent, const QString &playerName, const QString &playerIconName)
    {
        Q_UNUSED(playerIconName)
        record(QStringLiteral("mediaPlayerVolumeChanged %1 %2").arg(percent).arg(playerName));
    }
    void kbdLayoutChanged(const QString &layoutName)
    {
        record(QStringLiteral("kbdLayoutChanged ") + layoutName);
        Q_EMIT osdText(QStringLiteral("keyboard-layout"), layoutName);
    }
    void virtualDesktopChanged(const QString &currentVirtualDesktopName)
    {
        record(QStringLiteral("virtualDesktopChanged ") + currentVirtualDesktopName);
    }
    void touchpadEnabledChanged(bool touchpadEnabled)
    {
        record(QStringLiteral("touchpadEnabledChanged %1").arg(touchpadEnabled));
    }
    void wifiEnabledChanged(bool wifiEnabled)
    {
        record(QStringLiteral("wifiEnabledChanged %1").arg(wifiEnabled));
    }
    void bluetoothEnabledChanged(bool bluetoothEnabled)
    {
        record(QStringLiteral("bluetoothEnabledChanged %1").arg(bluetoothEnabled));
    }
    void wwanEnabledChanged(bool wwanEnabled)
    {
        record(QStringLiteral("wwanEnabledChanged %1").arg(wwanEnabled));
    }
    void virtualKeyboardEnabledChanged(bool virtualKeyboardEnabled)
    {
        record(QStringLiteral("virtualKeyboardEnabledChanged %1").arg(virtualKeyboardEnabled));
    }
    void powerManagementInhibitedChanged(bool inhibited)
    {
        record(QStringLiteral("powerManagementInhibitedChanged %1").arg(inhibited));
    }
    void powerProfileChanged(const QString &profile)
    {
        record(QStringLiteral("powerProfileChanged ") + profile);
    }
    void showText(const QString &icon, const QString &text)
    {
        record(QStringLiteral("showText %1 %2").arg(icon, text));
        Q_EMIT osdText(icon, text);
    }
    void hide()
    {
        record(QStringLiteral("hide"));
    }

Q_SIGNALS:
    void osdProgress(const QString &icon, const int percent, const int maximumPercent, const QString &additionalText);
    void osdText(const QString &icon, const QString &text);

private:
    void record(const QString &call)
    {
        calls << call;
    }
};

// An Osd of another Plasma: volumeChanged takes one more argument
class FakeChangedOsd : public QObject
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.kde.osdService")

public:
    QStringList calls;

public Q_SLOTS:
    void volumeChanged(int percent, int maximumPercent, const QString &deviceName)
    {
        calls << QStringLiteral("volumeChanged %1 %2 %3").arg(percent).arg(maximumPercent).arg(deviceName);
    }
    void showText(const QString &icon, const QString &text)
    {
        calls << QStringLiteral("showText %1 %2").arg(icon, text);
    }

Q_SIGNALS:
    void osdProgress(const QString &icon, const int percent, const int maximumPercent, const QString &additionalText);
    void osdText(const QString &icon, const QString &text);
};

// What kscreenlocker_greet hears on the bus
class FakeLockScreen : public QObject
{
    Q_OBJECT

public:
    QStringList heard;

public Q_SLOTS:
    void osdProgress(const QString &icon, int percent, int maximumPercent, const QString &additionalText)
    {
        heard << QStringLiteral("progress %1 %2/%3 %4").arg(icon).arg(percent).arg(maximumPercent).arg(additionalText).trimmed();
    }
    void osdText(const QString &icon, const QString &text)
    {
        heard << QStringLiteral("text %1 %2").arg(icon, text);
    }
};

class OsdInterceptorTest : public QObject
{
    Q_OBJECT

private Q_SLOTS:
    void initTestCase();
    void init();
    void cleanup();

    void takesOverAndGivesBackWithTheSameInterface();
    void leavesAnotherPlasmaAlone();
    void volumeGoesToTheHudAndTheLockScreen();
    void eachOsdGetsPlasmasIcon_data();
    void eachOsdGetsPlasmasIcon();
    void aMuteShowsAnEmptyBarAndPlasmasText();
    void textOsdsGoOnToPlasma();
    void choosesTheHostOfTheScreen();
    void anOpenControlCenterShowsNothing();
    void honoursPlasmasOsdSwitch();

private:
    std::unique_ptr<OsdHost> makeHost(const QRect &screenRect, bool activeScreen = false);
    QDBusMessage callOsd(const QString &method, const QVariantList &arguments = {});
    QString introspect();

    std::unique_ptr<GoldenGlassTest::FakeService> m_clients;
    std::unique_ptr<FakeLockScreen> m_lockScreen;
    std::unique_ptr<FakePlasmaOsd> m_plasma;
};

void OsdInterceptorTest::initTestCase()
{
    GG_REQUIRE_SESSION_BUS();
    // the lock screen texts come in Plasma's language: English here
    KLocalizedString::setLanguages({QStringLiteral("en_US")});
    QVERIFY(QDBusConnection::sessionBus().registerService(plasmaService));
}

void OsdInterceptorTest::init()
{
    m_plasma = std::make_unique<FakePlasmaOsd>();
    QVERIFY(QDBusConnection::sessionBus().registerObject(osdPath, m_plasma.get(), osdExport));

    m_clients = std::make_unique<GoldenGlassTest::FakeService>();
    QVERIFY(m_clients->isConnected());
    m_lockScreen = std::make_unique<FakeLockScreen>();
    QDBusConnection &bus = m_clients->connection();
    QVERIFY(
        bus.connect(plasmaService, osdPath, osdInterface, QStringLiteral("osdProgress"), m_lockScreen.get(), SLOT(osdProgress(QString, int, int, QString))));
    QVERIFY(bus.connect(plasmaService, osdPath, osdInterface, QStringLiteral("osdText"), m_lockScreen.get(), SLOT(osdText(QString, QString))));
}

void OsdInterceptorTest::cleanup()
{
    QDBusConnection::sessionBus().unregisterObject(osdPath);
    m_lockScreen.reset();
    m_clients.reset();
    m_plasma.reset();
}

std::unique_ptr<OsdHost> OsdInterceptorTest::makeHost(const QRect &screenRect, bool activeScreen)
{
    auto host = std::make_unique<OsdHost>();
    host->setScreenRect(screenRect);
    host->setActiveScreen(activeScreen);
    return host;
}

QDBusMessage OsdInterceptorTest::callOsd(const QString &method, const QVariantList &arguments)
{
    QDBusMessage message = QDBusMessage::createMethodCall(plasmaService, osdPath, osdInterface, method);
    message.setArguments(arguments);
    return GoldenGlassTest::call(message, 5000, m_clients->connection());
}

QString OsdInterceptorTest::introspect()
{
    const QDBusMessage message =
        QDBusMessage::createMethodCall(plasmaService, osdPath, QStringLiteral("org.freedesktop.DBus.Introspectable"), QStringLiteral("Introspect"));
    const QDBusMessage reply = GoldenGlassTest::call(message, 5000, m_clients->connection());
    return reply.type() == QDBusMessage::ReplyMessage ? reply.arguments().value(0).toString() : QString();
}

void OsdInterceptorTest::takesOverAndGivesBackWithTheSameInterface()
{
    const QString plasmaInterface = introspect();
    QVERIFY(plasmaInterface.contains(QLatin1String("screenBrightnessChanged")));

    auto first = makeHost(leftScreen, true);
    auto second = makeHost(rightScreen);
    QVERIFY(first->isIntercepting());
    QVERIFY(second->isIntercepting());
    QVERIFY(QDBusConnection::sessionBus().objectRegisteredAt(osdPath) != m_plasma.get());
    QCOMPARE(introspect(), plasmaInterface);

    first.reset();
    QVERIFY(QDBusConnection::sessionBus().objectRegisteredAt(osdPath) != m_plasma.get());

    second.reset();
    QCOMPARE(QDBusConnection::sessionBus().objectRegisteredAt(osdPath), m_plasma.get());
    QCOMPARE(introspect(), plasmaInterface);
    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {40}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(m_plasma->calls, QStringList{QStringLiteral("volumeChanged 40")});
}

void OsdInterceptorTest::leavesAnotherPlasmaAlone()
{
    QDBusConnection::sessionBus().unregisterObject(osdPath);
    FakeChangedOsd changed;
    QVERIFY(QDBusConnection::sessionBus().registerObject(osdPath, &changed, osdExport));

    auto host = makeHost(leftScreen, true);
    QSignalSpy shown(host.get(), &OsdHost::progressRequested);
    QVERIFY(!host->isIntercepting());
    QCOMPARE(QDBusConnection::sessionBus().objectRegisteredAt(osdPath), &changed);

    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {40, 100, QStringLiteral("Speakers")}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(changed.calls, QStringList{QStringLiteral("volumeChanged 40 100 Speakers")});
    QCOMPARE(shown.count(), 0);

    host.reset();
    QCOMPARE(QDBusConnection::sessionBus().objectRegisteredAt(osdPath), &changed);
    QVERIFY(!OsdInterceptor::exportsOsdServiceInterface(changed.metaObject()));
    QVERIFY(OsdInterceptor::exportsOsdServiceInterface(m_plasma->metaObject()));
}

void OsdInterceptorTest::volumeGoesToTheHudAndTheLockScreen()
{
    auto host = makeHost(leftScreen, true);
    QSignalSpy shown(host.get(), &OsdHost::progressRequested);

    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {40}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(shown.count(), 1);
    QCOMPARE(shown.first(), (QVariantList{QStringLiteral("audio-volume-medium"), 40, 100}));
    QTRY_COMPARE(m_lockScreen->heard, QStringList{QStringLiteral("progress audio-volume-medium 40/100")});

    // a raised maximum (150 %) and a value past it, which Plasma bounds
    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {170, 150}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(shown.last(), (QVariantList{QStringLiteral("audio-volume-high-danger"), 150, 150}));
    QTRY_COMPARE(m_lockScreen->heard.size(), 2);
    QCOMPARE(m_lockScreen->heard.last(), QStringLiteral("progress audio-volume-high-danger 150/150"));

    QVERIFY(m_plasma->calls.isEmpty());
}

void OsdInterceptorTest::eachOsdGetsPlasmasIcon_data()
{
    QTest::addColumn<QString>("method");
    QTest::addColumn<QVariantList>("arguments");
    QTest::addColumn<QVariantList>("hud");
    QTest::addColumn<QString>("lockScreen");

    QTest::newRow("low volume") << QStringLiteral("volumeChanged") << QVariantList{20} << QVariantList{QStringLiteral("audio-volume-low"), 20, 100}
                                << QStringLiteral("progress audio-volume-low 20/100");
    QTest::newRow("high volume") << QStringLiteral("volumeChanged") << QVariantList{90, 100} << QVariantList{QStringLiteral("audio-volume-high"), 90, 100}
                                 << QStringLiteral("progress audio-volume-high 90/100");
    QTest::newRow("microphone") << QStringLiteral("microphoneVolumeChanged") << QVariantList{60}
                                << QVariantList{QStringLiteral("microphone-sensitivity-medium"), 60, 100}
                                << QStringLiteral("progress microphone-sensitivity-medium 60/100");
    QTest::newRow("media player") << QStringLiteral("mediaPlayerVolumeChanged") << QVariantList{30, QStringLiteral("Elisa"), QStringLiteral("elisa")}
                                  << QVariantList{QStringLiteral("elisa"), 30, 100} << QStringLiteral("progress elisa 30/100 Elisa");
    QTest::newRow("brightness") << QStringLiteral("brightnessChanged") << QVariantList{70} << QVariantList{QStringLiteral("video-display-brightness"), 70, 100}
                                << QStringLiteral("progress video-display-brightness 70/100");
    QTest::newRow("screen brightness") << QStringLiteral("screenBrightnessChanged")
                                       << QVariantList{55, QStringLiteral("eDP-1"), QStringLiteral("Built-in Screen"), 0, QRect()}
                                       << QVariantList{QStringLiteral("video-display-brightness"), 55, 100}
                                       << QStringLiteral("progress video-display-brightness 55/100 Built-in Screen");
    QTest::newRow("keyboard brightness") << QStringLiteral("keyboardBrightnessChanged") << QVariantList{110}
                                         << QVariantList{QStringLiteral("input-keyboard-brightness"), 100, 100}
                                         << QStringLiteral("progress input-keyboard-brightness 100/100");
}

void OsdInterceptorTest::eachOsdGetsPlasmasIcon()
{
    QFETCH(QString, method);
    QFETCH(QVariantList, arguments);
    QFETCH(QVariantList, hud);
    QFETCH(QString, lockScreen);

    auto host = makeHost(leftScreen, true);
    QSignalSpy shown(host.get(), &OsdHost::progressRequested);
    QCOMPARE(callOsd(method, arguments).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(shown.count(), 1);
    QCOMPARE(shown.first(), hud);
    QTRY_COMPARE(m_lockScreen->heard, QStringList{lockScreen});
    QVERIFY(m_plasma->calls.isEmpty());
}

void OsdInterceptorTest::aMuteShowsAnEmptyBarAndPlasmasText()
{
    auto host = makeHost(leftScreen, true);
    QSignalSpy shown(host.get(), &OsdHost::progressRequested);

    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {0, 150}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(callOsd(QStringLiteral("microphoneVolumeChanged"), {0}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(callOsd(QStringLiteral("mediaPlayerVolumeChanged"), {0, QStringLiteral("Elisa"), QStringLiteral("elisa")}).type(), QDBusMessage::ReplyMessage);

    QCOMPARE(shown.count(), 3);
    QCOMPARE(shown.at(0), (QVariantList{QStringLiteral("audio-volume-muted"), 0, 150}));
    QCOMPARE(shown.at(1), (QVariantList{QStringLiteral("microphone-sensitivity-muted"), 0, 100}));
    QCOMPARE(shown.at(2), (QVariantList{QStringLiteral("elisa"), 0, 100}));
    QTRY_COMPARE(m_lockScreen->heard.size(), 3);
    QCOMPARE(m_lockScreen->heard,
             (QStringList{QStringLiteral("text audio-volume-muted Audio Muted"),
                          QStringLiteral("text microphone-sensitivity-muted Microphone Muted"),
                          QStringLiteral("text elisa Elisa Muted")}));
}

void OsdInterceptorTest::textOsdsGoOnToPlasma()
{
    auto host = makeHost(leftScreen, true);
    QSignalSpy shown(host.get(), &OsdHost::progressRequested);

    QCOMPARE(callOsd(QStringLiteral("kbdLayoutChanged"), {QStringLiteral("Spanish")}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(callOsd(QStringLiteral("showText"), {QStringLiteral("irc-voice"), QStringLiteral("Speak…")}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(callOsd(QStringLiteral("touchpadEnabledChanged"), {false}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(callOsd(QStringLiteral("powerProfileChanged"), {QStringLiteral("balanced")}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(callOsd(QStringLiteral("hide")).type(), QDBusMessage::ReplyMessage);

    QCOMPARE(m_plasma->calls,
             (QStringList{QStringLiteral("kbdLayoutChanged Spanish"),
                          QStringLiteral("showText irc-voice Speak…"),
                          QStringLiteral("touchpadEnabledChanged 0"),
                          QStringLiteral("powerProfileChanged balanced"),
                          QStringLiteral("hide")}));
    QCOMPARE(shown.count(), 0);
    // Plasma's own signals still reach the lock screen
    QTRY_COMPARE(m_lockScreen->heard.size(), 2);
    QCOMPARE(m_lockScreen->heard, (QStringList{QStringLiteral("text keyboard-layout Spanish"), QStringLiteral("text irc-voice Speak…")}));
}

void OsdInterceptorTest::choosesTheHostOfTheScreen()
{
    auto left = makeHost(leftScreen);
    auto right = makeHost(rightScreen, true);
    QSignalSpy onLeft(left.get(), &OsdHost::progressRequested);
    QSignalSpy onRight(right.get(), &OsdHost::progressRequested);

    // the screen with the active window
    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {40}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(onLeft.count(), 0);
    QCOMPARE(onRight.count(), 1);

    // the brightness of a screen, on that screen
    QCOMPARE(callOsd(QStringLiteral("screenBrightnessChanged"), {50, QStringLiteral("DP-1"), QStringLiteral("Left"), 1, leftScreen}).type(),
             QDBusMessage::ReplyMessage);
    QCOMPARE(onLeft.count(), 1);
    QCOMPARE(onRight.count(), 1);

    // powerdevil sends no rectangle: a display id that names a screen
    QCOMPARE(QGuiApplication::screens().size(), 2);
    QCOMPARE(callOsd(QStringLiteral("screenBrightnessChanged"), {60, QStringLiteral("DP-1"), QStringLiteral("Left"), 0, QRect()}).type(),
             QDBusMessage::ReplyMessage);
    QCOMPARE(onLeft.count(), 2);
    QCOMPARE(onRight.count(), 1);

    // an unknown display: the active screen again
    QCOMPARE(callOsd(QStringLiteral("screenBrightnessChanged"), {70, QStringLiteral("HDMI-9"), QStringLiteral("Other"), 2, QRect()}).type(),
             QDBusMessage::ReplyMessage);
    QCOMPARE(onLeft.count(), 2);
    QCOMPARE(onRight.count(), 2);

    // no active window anywhere: the primary screen
    right->setActiveScreen(false);
    QCOMPARE(QGuiApplication::primaryScreen()->geometry(), leftScreen);
    QCOMPARE(callOsd(QStringLiteral("keyboardBrightnessChanged"), {30}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(onLeft.count(), 3);
    QCOMPARE(onRight.count(), 2);

    // with several screens the lock screen, which shows one OSD, gets the display's name
    QTRY_COMPARE(m_lockScreen->heard.size(), 5);
    QCOMPARE(m_lockScreen->heard.at(1), QStringLiteral("progress video-display-brightness 50/100 Left"));
}

void OsdInterceptorTest::anOpenControlCenterShowsNothing()
{
    auto left = makeHost(leftScreen, true);
    auto right = makeHost(rightScreen);
    QSignalSpy onLeft(left.get(), &OsdHost::progressRequested);
    QSignalSpy onRight(right.get(), &OsdHost::progressRequested);
    left->setSuppressed(true);

    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {40}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(onLeft.count(), 0);
    QCOMPARE(onRight.count(), 0);
    // the lock screen still hears it
    QTRY_COMPARE(m_lockScreen->heard, QStringList{QStringLiteral("progress audio-volume-medium 40/100")});
    QVERIFY(m_plasma->calls.isEmpty());

    left->setSuppressed(false);
    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {50}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(onLeft.count(), 1);
}

void OsdInterceptorTest::honoursPlasmasOsdSwitch()
{
    KSharedConfig::Ptr plasmarc = KSharedConfig::openConfig(QStringLiteral("plasmarc"));
    KConfigGroup osd = plasmarc->group(QStringLiteral("OSD"));
    osd.writeEntry("Enabled", false);

    auto host = makeHost(leftScreen, true);
    QSignalSpy shown(host.get(), &OsdHost::progressRequested);
    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {40}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {0}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(shown.count(), 0);

    osd.writeEntry("Enabled", true);
    QCOMPARE(callOsd(QStringLiteral("volumeChanged"), {40}).type(), QDBusMessage::ReplyMessage);
    QCOMPARE(shown.count(), 1);
    // only the last call was shown, also to the lock screen
    QTRY_COMPARE(m_lockScreen->heard, QStringList{QStringLiteral("progress audio-volume-medium 40/100")});
}

// GOLDENGLASS_TEST_MAIN with two screens
int main(int argc, char *argv[])
{
    GoldenGlassTest::Sandbox sandbox;
    QFile screens(sandbox.path() + QStringLiteral("/screens.json"));
    if (!screens.open(QIODevice::WriteOnly) || screens.write(twoScreens) < 0) {
        qFatal("could not write the offscreen screens");
    }
    screens.close();
    qputenv("QT_QPA_PLATFORM", "offscreen:configfile=" + QFile::encodeName(screens.fileName()));
    QGuiApplication app(argc, argv);
    app.setAttribute(Qt::AA_Use96Dpi, true);
    OsdInterceptorTest test;
    QTEST_SET_MAIN_SOURCE_PATH
    return QTest::qExec(&test, argc, argv);
}

#include "osdinterceptor_test.moc"
