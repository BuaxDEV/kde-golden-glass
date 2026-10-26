/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Test of the «Icon style» module, run by ctest with the goldenglass-icon-style
 * stand-in of tests/bin and a temporary XDG_CONFIG_HOME (see kcm/CMakeLists.txt):
 *   kcm_iconstyle_test /path/to/kcm_goldenglass_iconstyle.so
 * It picks three styles and three appearances in a row: the last of each ends
 * stored. Then «Defaults» goes back to Default and Auto.
 */

#include <KConfig>
#include <KConfigGroup>
#include <KPluginFactory>
#include <KPluginMetaData>
#include <KQuickConfigModule>

#include <QElapsedTimer>
#include <QGuiApplication>
#include <QTextStream>
#include <QThread>

#include <functional>

namespace
{
constexpr int kTimeoutMs = 30000;

void waitFor(QGuiApplication &app, const std::function<bool()> &done)
{
    QElapsedTimer timer;
    timer.start();
    while (!done() && timer.elapsed() < kTimeoutMs) {
        app.processEvents(QEventLoop::AllEvents, 100);
        QThread::msleep(20);
    }
}

QString stored(const char *key)
{
    const KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
    return config.group(QStringLiteral("Icons")).readEntry(key, QString());
}
}

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    QTextStream out(stdout);
    if (argc < 2) {
        out << "usage: kcm_iconstyle_test kcm_goldenglass_iconstyle.so\n";
        return 2;
    }

    const KPluginMetaData metaData(QString::fromLocal8Bit(argv[1]));
    auto result = KPluginFactory::instantiatePlugin<KQuickConfigModule>(metaData, &app);
    if (!result) {
        out << "FAIL: the module did not load: " << result.errorText << "\n";
        return 1;
    }
    KQuickConfigModule *kcm = result.plugin;
    kcm->load();
    waitFor(app, [kcm] {
        return kcm->property("available").toBool();
    });
    const bool loadOk = kcm->property("available").toBool() && kcm->property("style").toString() == QLatin1String("default")
        && kcm->property("appearance").toString() == QLatin1String("auto") && kcm->representsDefaults();
    out << "available=" << kcm->property("available").toBool() << " style=" << kcm->property("style").toString()
        << " appearance=" << kcm->property("appearance").toString() << "\n";

    for (const char *style : {"tinted", "clear", "tinted"}) {
        kcm->setProperty("style", QString::fromLatin1(style));
    }
    for (const char *appearance : {"dark", "light", "dark"}) {
        kcm->setProperty("appearance", QString::fromLatin1(appearance));
    }
    // the queue empties, then the module reads the state back
    waitFor(app, [kcm] {
        return !kcm->property("busy").toBool() && stored("Appearance") == QLatin1String("dark");
    });
    QThread::msleep(500);
    app.processEvents(QEventLoop::AllEvents, 100);
    const QString error = kcm->property("errorText").toString();
    out << "style_stored=" << stored("Style") << " appearance_stored=" << stored("Appearance") << " style_kcm=" << kcm->property("style").toString()
        << " appearance_kcm=" << kcm->property("appearance").toString() << " error=\"" << error << "\"\n";
    const bool queueOk = stored("Style") == QLatin1String("tinted") && stored("Appearance") == QLatin1String("dark")
        && kcm->property("style").toString() == QLatin1String("tinted") && kcm->property("appearance").toString() == QLatin1String("dark")
        && !kcm->representsDefaults() && error.isEmpty();

    kcm->defaults();
    waitFor(app, [kcm] {
        return !kcm->property("busy").toBool() && stored("Appearance") == QLatin1String("auto");
    });
    out << "after_defaults style_stored=" << stored("Style") << " appearance_stored=" << stored("Appearance") << "\n";
    const bool defaultsOk = stored("Style") == QLatin1String("default") && stored("Appearance") == QLatin1String("auto") && kcm->representsDefaults();

    const bool ok = loadOk && queueOk && defaultsOk;
    out << (ok ? "OK" : "FAIL") << "\n";
    return ok ? 0 : 1;
}
