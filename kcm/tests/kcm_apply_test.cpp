/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Prueba de integración del módulo «Vidrio» (requiere una sesión Plasma, p. ej.
 * GG_SANDBOX_HOOK en tools/sandbox.sh, y goldenglass-glass en el PATH):
 *   kcm_apply_test /ruta/a/kcm_goldenglass.so
 * Pide tres niveles seguidos (1.0, 0.0, 0.25): el último debe quedar aplicado.
 * Then flips «Reduce motion» on, off and on: it must end on, through
 * goldenglass-windows, without losing the glass level.
 * En ctest corre sin sesión, con el goldenglass-glass de prueba de tests/bin y
 * XDG_CONFIG_HOME temporal (ver kcm/CMakeLists.txt).
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

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    QTextStream out(stdout);
    if (argc < 2) {
        out << "uso: kcm_apply_test kcm_goldenglass.so\n";
        return 2;
    }

    const KPluginMetaData metaData(QString::fromLocal8Bit(argv[1]));
    auto result = KPluginFactory::instantiatePlugin<KQuickConfigModule>(metaData, &app);
    if (!result) {
        out << "FALLO: no se pudo cargar el módulo: " << result.errorText << "\n";
        return 1;
    }
    KQuickConfigModule *kcm = result.plugin;
    kcm->load();

    for (const double level : {1.0, 0.0, 0.25}) {
        QMetaObject::invokeMethod(kcm, "applyLevel", Q_ARG(double, level));
    }

    QElapsedTimer timer;
    timer.start();
    while (kcm->property("busy").toBool() && timer.elapsed() < 30000) {
        app.processEvents(QEventLoop::AllEvents, 100);
        QThread::msleep(20);
    }

    const KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
    const double applied = config.group(QStringLiteral("Glass")).readEntry("Level", -1.0);
    const QString error = kcm->property("errorText").toString();
    out << "busy=" << kcm->property("busy").toBool() << " nivel_kcm=" << kcm->property("level").toDouble()
        << " nivel_aplicado=" << applied << " error=\"" << error << "\"\n";

    const bool levelOk = !kcm->property("busy").toBool() && qAbs(applied - 0.25) < 0.001 && error.isEmpty();

    for (const bool value : {true, false, true}) {
        kcm->setProperty("reduceMotion", value);
    }
    const auto readReduceMotion = [] {
        const KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
        return config.group(QStringLiteral("Accessibility")).readEntry("ReduceMotion", false);
    };
    timer.restart();
    // the queued request runs after the first one: wait past both
    while ((!readReduceMotion() || timer.elapsed() < 1500) && timer.elapsed() < 30000) {
        app.processEvents(QEventLoop::AllEvents, 100);
        QThread::msleep(20);
    }
    const KConfig after(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
    const double levelAfter = after.group(QStringLiteral("Glass")).readEntry("Level", -1.0);
    const QString reduceError = kcm->property("errorText").toString();
    out << "reduce_motion_kcm=" << kcm->property("reduceMotion").toBool() << " reduce_motion_applied=" << readReduceMotion()
        << " nivel_tras=" << levelAfter << " error=\"" << reduceError << "\"\n";
    const bool reduceOk =
        readReduceMotion() && kcm->property("reduceMotion").toBool() && qAbs(levelAfter - 0.25) < 0.001 && reduceError.isEmpty();

    const bool ok = levelOk && reduceOk;
    out << (ok ? "OK" : "FALLO") << "\n";
    return ok ? 0 : 1;
}
