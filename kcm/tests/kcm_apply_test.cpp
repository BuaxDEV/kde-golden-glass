/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Prueba de integración del módulo «Vidrio» (requiere una sesión Plasma, p. ej.
 * GG_SANDBOX_HOOK en tools/sandbox.sh, y goldenglass-glass en el PATH):
 *   kcm_apply_test /ruta/a/kcm_goldenglass.so
 * Pide tres niveles seguidos (1.0, 0.0, 0.25): el último debe quedar aplicado.
 * Then flips «Reduce motion» on, off and on: it must end on, through
 * goldenglass-windows, without losing the glass level. Then «Reduce
 * transparency» on, off and on with a level on top: both end applied. Then
 * «Show borders» on, off and on queued with «Reduce transparency» off: all
 * three kinds end applied.
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

    // «Reduce transparency» shares goldenglass-glass with the level: both
    // queue up and the last request of each kind wins
    for (const bool value : {true, false, true}) {
        kcm->setProperty("reduceTransparency", value);
    }
    QMetaObject::invokeMethod(kcm, "applyLevel", Q_ARG(double, 0.6));
    timer.restart();
    while (kcm->property("busy").toBool() && timer.elapsed() < 30000) {
        app.processEvents(QEventLoop::AllEvents, 100);
        QThread::msleep(20);
    }
    const KConfig afterTransparency(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
    const bool transparencyApplied = afterTransparency.group(QStringLiteral("Accessibility")).readEntry("ReduceTransparency", false);
    const double levelAfterTransparency = afterTransparency.group(QStringLiteral("Glass")).readEntry("Level", -1.0);
    const QString transparencyError = kcm->property("errorText").toString();
    out << "reduce_transparency_kcm=" << kcm->property("reduceTransparency").toBool() << " reduce_transparency_applied=" << transparencyApplied
        << " nivel_tras=" << levelAfterTransparency << " error=\"" << transparencyError << "\"\n";
    const bool transparencyOk = !kcm->property("busy").toBool() && transparencyApplied && kcm->property("reduceTransparency").toBool()
        && qAbs(levelAfterTransparency - 0.6) < 0.001 && transparencyError.isEmpty();

    // «Show borders» queues as a third kind next to the other two
    for (const bool value : {true, false, true}) {
        kcm->setProperty("showBorders", value);
    }
    kcm->setProperty("reduceTransparency", false);
    timer.restart();
    while (kcm->property("busy").toBool() && timer.elapsed() < 30000) {
        app.processEvents(QEventLoop::AllEvents, 100);
        QThread::msleep(20);
    }
    const KConfig afterBorders(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
    const KConfigGroup accessibility = afterBorders.group(QStringLiteral("Accessibility"));
    const bool bordersApplied = accessibility.readEntry("ShowBorders", false);
    const bool transparencyAfterBorders = accessibility.readEntry("ReduceTransparency", true);
    const double levelAfterBorders = afterBorders.group(QStringLiteral("Glass")).readEntry("Level", -1.0);
    const QString bordersError = kcm->property("errorText").toString();
    out << "show_borders_kcm=" << kcm->property("showBorders").toBool() << " show_borders_applied=" << bordersApplied
        << " reduce_transparency_applied=" << transparencyAfterBorders << " nivel_tras=" << levelAfterBorders << " error=\"" << bordersError
        << "\"\n";
    const bool bordersOk = !kcm->property("busy").toBool() && bordersApplied && kcm->property("showBorders").toBool() && !transparencyAfterBorders
        && !kcm->property("reduceTransparency").toBool() && qAbs(levelAfterBorders - 0.6) < 0.001 && bordersError.isEmpty();

    const bool ok = levelOk && reduceOk && transparencyOk && bordersOk;
    out << (ok ? "OK" : "FALLO") << "\n";
    return ok ? 0 : 1;
}
