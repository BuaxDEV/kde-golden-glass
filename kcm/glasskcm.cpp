/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "glasskcm.h"

#include "goldenglass_tokens.h"

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
}

GlassKcm::GlassKcm(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
    , m_process(new QProcess(this))
    , m_level(GoldenGlass::Tokens::GlassDefaultLevel)
{
    // Los cambios se aplican en vivo al soltar el control: no hay «Aplicar».
    setButtons(KAbstractConfigModule::Default);

    m_process->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_process, &QProcess::finished, this, [this](int exitCode, QProcess::ExitStatus status) {
        if (status != QProcess::NormalExit || exitCode != 0) {
            const QString output = QString::fromLocal8Bit(m_process->readAll()).trimmed();
            setErrorText(i18nc("@info:status", "The glass level could not be applied: %1", output));
        }
        if (m_pending >= 0) {
            const double next = m_pending;
            m_pending = -1;
            startProcess(next);
            return;
        }
        Q_EMIT busyChanged();
    });
    connect(m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
        setErrorText(i18nc("@info:status", "goldenglass-glass could not be started: %1", m_process->errorString()));
        Q_EMIT busyChanged();
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

bool GlassKcm::busy() const
{
    return m_process->state() != QProcess::NotRunning;
}

QString GlassKcm::errorText() const
{
    return m_errorText;
}

void GlassKcm::load()
{
    const KConfigGroup group(KSharedConfig::openConfig(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig), QStringLiteral("Glass"));
    setLevel(group.readEntry("Level", GoldenGlass::Tokens::GlassDefaultLevel));
}

void GlassKcm::defaults()
{
    applyLevel(GoldenGlass::Tokens::GlassDefaultLevel);
}

void GlassKcm::applyLevel(double level)
{
    level = qBound(0.0, level, 1.0);
    setLevel(level);
    setErrorText(QString());

    if (busy()) {
        m_pending = level; // se aplica al terminar el actual
        return;
    }
    startProcess(level);
}

void GlassKcm::startProcess(double level)
{
    const QString program = QStandardPaths::findExecutable(QStringLiteral("goldenglass-glass"));
    if (program.isEmpty()) {
        setErrorText(i18nc("@info:status", "goldenglass-glass was not found. Is the goldenglass-kstyle package installed?"));
        return;
    }
    m_process->start(program, {QStringLiteral("--level"), QString::number(level, 'f', 3)});
    Q_EMIT busyChanged();
}

void GlassKcm::setLevel(double level)
{
    if (qAbs(m_level - level) > kSameLevel / 10) {
        m_level = level;
        Q_EMIT levelChanged();
    }
    setRepresentsDefaults(qAbs(m_level - GoldenGlass::Tokens::GlassDefaultLevel) < kSameLevel);
}

void GlassKcm::setErrorText(const QString &text)
{
    if (m_errorText != text) {
        m_errorText = text;
        Q_EMIT errorTextChanged();
    }
}

#include "glasskcm.moc"
