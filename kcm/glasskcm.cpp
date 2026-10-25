/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "glasskcm.h"

#include "goldenglass_tokens.h"
#include "processquery.h"

#include <KConfig>
#include <KConfigGroup>
#include <KLocalizedString>
#include <KPluginFactory>
#include <KSharedConfig>

#include <QProcess>
#include <QStandardPaths>

K_PLUGIN_CLASS_WITH_JSON(GlassKcm, "kcm_goldenglass.json")

namespace
{
constexpr double kSameLevel = 0.005;

QString onOff(bool value)
{
    return value ? QStringLiteral("on") : QStringLiteral("off");
}
}

GlassKcm::GlassKcm(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
    , m_process(new QProcess(this))
    , m_level(GoldenGlass::Tokens::GlassDefaultLevel)
    , m_menubarBackground(GoldenGlass::Tokens::MenubarBackground)
    , m_reduceMotionProcess(new QProcess(this))
    , m_reduceMotion(GoldenGlass::Tokens::AccessibilityReduceMotion)
    , m_reduceTransparency(GoldenGlass::Tokens::AccessibilityReduceTransparency)
{
    // Los cambios se aplican en vivo al soltar el control: no hay «Aplicar».
    setButtons(KAbstractConfigModule::Default);

    m_process->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_process, &QProcess::finished, this, [this](int exitCode, QProcess::ExitStatus status) {
        if (status != QProcess::NormalExit || exitCode != 0) {
            glassRequestFailed(m_runningGlass, QString::fromLocal8Bit(m_process->readAll()).trimmed());
        } else if (m_runningGlass == GlassRequest::ReduceTransparency && !m_pendingGlass.contains(GlassRequest::ReduceTransparency)) {
            loadReduceTransparency();
        }
        if (!m_pendingGlass.empty()) {
            auto next = m_pendingGlass.extract(m_pendingGlass.begin());
            startGlass(next.key(), next.mapped());
            return;
        }
        Q_EMIT busyChanged();
    });
    m_refractionProcess = new QProcess(this);
    m_refractionProcess->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_refractionProcess, &QProcess::finished, this, [this](int exitCode, QProcess::ExitStatus status) {
        if (status != QProcess::NormalExit || exitCode != 0) {
            setErrorText(i18nc("@info:status", "Refraction could not be changed: %1", QString::fromLocal8Bit(m_refractionProcess->readAll()).trimmed()));
        }
        loadRefraction();
    });
    // sin arrancar no llega finished: el interruptor vuelve al estado real
    connect(m_refractionProcess, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart) {
            setErrorText(i18nc("@info:status", "goldenglass-glass could not be started: %1", m_refractionProcess->errorString()));
            loadRefraction();
        }
    });

    connect(m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error != QProcess::FailedToStart) {
            return; // finished follows
        }
        setErrorText(i18nc("@info:status", "goldenglass-glass could not be started: %1", m_process->errorString()));
        m_pendingGlass.clear();
        loadReduceTransparency();
        Q_EMIT busyChanged();
    });

    // One goldenglass-windows at a time; a switch flipped meanwhile runs next with its last value.
    m_reduceMotionProcess->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_reduceMotionProcess, &QProcess::finished, this, [this](int exitCode, QProcess::ExitStatus status) {
        if (status != QProcess::NormalExit || exitCode != 0) {
            setErrorText(i18nc("@info:status",
                               "Reduce motion could not be changed: %1",
                               QString::fromLocal8Bit(m_reduceMotionProcess->readAll()).trimmed()));
        }
        if (m_pendingReduceMotion) {
            const bool next = *m_pendingReduceMotion;
            m_pendingReduceMotion.reset();
            startReduceMotion(next);
            return;
        }
        loadReduceMotion();
    });
    connect(m_reduceMotionProcess, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart) {
            setErrorText(i18nc("@info:status", "goldenglass-windows could not be started: %1", m_reduceMotionProcess->errorString()));
            m_pendingReduceMotion.reset();
            loadReduceMotion();
        }
    });
}

double GlassKcm::level() const
{
    return m_level;
}

double GlassKcm::defaultLevel() const
{
    return GoldenGlass::Tokens::GlassDefaultLevel;
}

QVariantList GlassKcm::notches() const
{
    return {GoldenGlass::Tokens::GlassNotchClear, GoldenGlass::Tokens::GlassNotchMedium, GoldenGlass::Tokens::GlassNotchOpaque};
}

double GlassKcm::snapDistance() const
{
    return GoldenGlass::Tokens::GlassSnapDistance;
}

int GlassKcm::keyboardApplyDelay() const
{
    return GoldenGlass::Tokens::GlassKeyboardApplyMs;
}

bool GlassKcm::busy() const
{
    return m_process->state() != QProcess::NotRunning;
}

QString GlassKcm::errorText() const
{
    return m_errorText;
}

bool GlassKcm::refraction() const
{
    return m_refraction;
}

bool GlassKcm::refractionAvailable() const
{
    return m_refractionAvailable;
}

void GlassKcm::setRefraction(bool value)
{
    const QString program = QStandardPaths::findExecutable(QStringLiteral("goldenglass-glass"));
    if (program.isEmpty() || m_refractionProcess->state() != QProcess::NotRunning) {
        // rechazado: el interruptor ya se movió y debe volver al valor real
        Q_EMIT refractionChanged();
        return;
    }
    m_refraction = value;
    Q_EMIT refractionChanged();
    setErrorText(QString());
    m_refractionProcess->start(program, {QStringLiteral("--refraction"), value ? QStringLiteral("on") : QStringLiteral("off")});
}

bool GlassKcm::menubarBackground() const
{
    return m_menubarBackground;
}

void GlassKcm::setMenubarBackground(bool value)
{
    if (m_menubarBackground == value) {
        return;
    }
    m_menubarBackground = value;
    // Con aviso: el Panel.qml del shell lo relee al momento (MenuBarSettings).
    KConfigGroup group(KSharedConfig::openConfig(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig), QStringLiteral("Plasma"));
    group.writeEntry("MenubarBackground", value, KConfig::Notify);
    group.sync();
    Q_EMIT menubarBackgroundChanged();
    updateRepresentsDefaults();
}

bool GlassKcm::reduceMotion() const
{
    return m_reduceMotion;
}

void GlassKcm::setReduceMotion(bool value)
{
    if (m_reduceMotion == value) {
        return;
    }
    m_reduceMotion = value;
    Q_EMIT reduceMotionChanged();
    updateRepresentsDefaults();
    setErrorText(QString());
    if (m_reduceMotionProcess->state() != QProcess::NotRunning) {
        m_pendingReduceMotion = value;
        return;
    }
    startReduceMotion(value);
}

void GlassKcm::startReduceMotion(bool value)
{
    const QString program = QStandardPaths::findExecutable(QStringLiteral("goldenglass-windows"));
    if (program.isEmpty()) {
        setErrorText(i18nc("@info:status", "goldenglass-windows was not found. Is the goldenglass-plasma package installed?"));
        loadReduceMotion();
        return;
    }
    m_reduceMotionProcess->start(program, {QStringLiteral("--reduce-motion"), onOff(value)});
}

bool GlassKcm::reduceTransparency() const
{
    return m_reduceTransparency;
}

void GlassKcm::setReduceTransparency(bool value)
{
    if (m_reduceTransparency == value) {
        return;
    }
    m_reduceTransparency = value;
    Q_EMIT reduceTransparencyChanged();
    updateRepresentsDefaults();
    setErrorText(QString());
    requestGlass(GlassRequest::ReduceTransparency, {QStringLiteral("--reduce-transparency"), onOff(value)});
}

void GlassKcm::loadReduceTransparency()
{
    // a fresh KConfig: goldenglass-glass has just written the file
    const KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
    const bool value =
        config.group(QStringLiteral("Accessibility")).readEntry("ReduceTransparency", GoldenGlass::Tokens::AccessibilityReduceTransparency);
    if (m_reduceTransparency != value) {
        m_reduceTransparency = value;
        Q_EMIT reduceTransparencyChanged();
    }
    updateRepresentsDefaults();
}

void GlassKcm::loadReduceMotion()
{
    // a fresh KConfig: goldenglass-windows has just written the file
    const KConfig config(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
    const bool value = config.group(QStringLiteral("Accessibility")).readEntry("ReduceMotion", GoldenGlass::Tokens::AccessibilityReduceMotion);
    if (m_reduceMotion != value) {
        m_reduceMotion = value;
        Q_EMIT reduceMotionChanged();
    }
    updateRepresentsDefaults();
}

void GlassKcm::loadRefraction()
{
    const QString program = QStandardPaths::findExecutable(QStringLiteral("goldenglass-glass"));
    if (program.isEmpty()) {
        return;
    }
    // asíncrono: esperar aquí congelaría la interfaz; solo cuenta la última consulta
    const int query = ++m_refractionQuery;
    GoldenGlass::runQuery(this, program, {QStringLiteral("--get-refraction")}, [this, query](bool ok, const QByteArray &output, const QString &) {
        if (query != m_refractionQuery) {
            return;
        }
        const QString state = ok ? QString::fromLocal8Bit(output).trimmed() : QString();
        m_refractionAvailable = state != QLatin1String("unavailable") && !state.isEmpty();
        m_refraction = state == QLatin1String("on");
        Q_EMIT refractionChanged();
    });
}

void GlassKcm::load()
{
    loadRefraction();
    const KSharedConfig::Ptr config = KSharedConfig::openConfig(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig);
    const bool menubar = config->group(QStringLiteral("Plasma")).readEntry("MenubarBackground", GoldenGlass::Tokens::MenubarBackground);
    if (m_menubarBackground != menubar) {
        m_menubarBackground = menubar;
        Q_EMIT menubarBackgroundChanged();
    }
    setLevel(config->group(QStringLiteral("Glass")).readEntry("Level", GoldenGlass::Tokens::GlassDefaultLevel));
    loadReduceMotion();
    loadReduceTransparency();
}

void GlassKcm::defaults()
{
    applyLevel(GoldenGlass::Tokens::GlassDefaultLevel);
    setMenubarBackground(GoldenGlass::Tokens::MenubarBackground);
    setReduceMotion(GoldenGlass::Tokens::AccessibilityReduceMotion);
    setReduceTransparency(GoldenGlass::Tokens::AccessibilityReduceTransparency);
}

void GlassKcm::applyLevel(double level)
{
    level = qBound(0.0, level, 1.0);
    setLevel(level);
    setErrorText(QString());
    requestGlass(GlassRequest::Level, {QStringLiteral("--level"), QString::number(level, 'f', 3)});
}

void GlassKcm::requestGlass(GlassRequest kind, const QStringList &arguments)
{
    if (busy()) {
        m_pendingGlass[kind] = arguments;
        return;
    }
    startGlass(kind, arguments);
}

void GlassKcm::startGlass(GlassRequest kind, const QStringList &arguments)
{
    const QString program = QStandardPaths::findExecutable(QStringLiteral("goldenglass-glass"));
    if (program.isEmpty()) {
        setErrorText(i18nc("@info:status", "goldenglass-glass was not found. Is the goldenglass-kstyle package installed?"));
        m_pendingGlass.clear();
        loadReduceTransparency();
        Q_EMIT busyChanged();
        return;
    }
    m_runningGlass = kind;
    m_process->start(program, arguments);
    Q_EMIT busyChanged();
}

void GlassKcm::glassRequestFailed(GlassRequest kind, const QString &output)
{
    switch (kind) {
    case GlassRequest::Level:
        setErrorText(i18nc("@info:status", "The glass level could not be applied: %1", output));
        break;
    case GlassRequest::ReduceTransparency:
        setErrorText(i18nc("@info:status", "Reduce transparency could not be changed: %1", output));
        if (!m_pendingGlass.contains(GlassRequest::ReduceTransparency)) {
            loadReduceTransparency();
        }
        break;
    }
}

void GlassKcm::setLevel(double level)
{
    if (qAbs(m_level - level) > kSameLevel / 10) {
        m_level = level;
        Q_EMIT levelChanged();
    }
    updateRepresentsDefaults();
}

void GlassKcm::updateRepresentsDefaults()
{
    setRepresentsDefaults(qAbs(m_level - GoldenGlass::Tokens::GlassDefaultLevel) < kSameLevel
                          && m_menubarBackground == GoldenGlass::Tokens::MenubarBackground
                          && m_reduceMotion == GoldenGlass::Tokens::AccessibilityReduceMotion
                          && m_reduceTransparency == GoldenGlass::Tokens::AccessibilityReduceTransparency);
}

void GlassKcm::setErrorText(const QString &text)
{
    if (m_errorText != text) {
        m_errorText = text;
        Q_EMIT errorTextChanged();
    }
}

#include "glasskcm.moc"
