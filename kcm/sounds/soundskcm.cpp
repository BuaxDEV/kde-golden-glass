/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "soundskcm.h"

#include "../processquery.h"

#include <KLocalizedString>
#include <KPluginFactory>

#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QStandardPaths>

K_PLUGIN_CLASS_WITH_JSON(SoundsKcm, "kcm_goldenglass_sounds.json")

namespace
{
QString themeFile(const QString &name)
{
    return QStandardPaths::locate(QStandardPaths::GenericDataLocation, QStringLiteral("sounds/GoldenGlass/stereo/%1.oga").arg(name));
}
}

SoundsKcm::SoundsKcm(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
    , m_process(new QProcess(this))
{
    // Como en macOS, los cambios se aplican al momento: no hay «Aplicar».
    setButtons(KAbstractConfigModule::NoAdditionalButton);

    m_process->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_process, &QProcess::finished, this, [this](int exitCode, QProcess::ExitStatus status) {
        if (status != QProcess::NormalExit || exitCode != 0) {
            const QString output = QString::fromLocal8Bit(m_process->readAll()).trimmed();
            setErrorText(i18nc("@info:status", "The change could not be applied: %1", output));
        }
        if (!m_queue.isEmpty()) {
            startNext();
            return;
        }
        load();
        Q_EMIT busyChanged();
    });
    connect(m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
        setErrorText(i18nc("@info:status", "goldenglass-system could not be started: %1", m_process->errorString()));
        m_queue.clear();
        Q_EMIT busyChanged();
    });
}

bool SoundsKcm::soundsEnabled() const
{
    return m_sounds;
}

bool SoundsKcm::chimeEnabled() const
{
    return m_chime;
}

bool SoundsKcm::themeInstalled() const
{
    return !QStandardPaths::locate(QStandardPaths::GenericDataLocation, QStringLiteral("sounds/GoldenGlass/index.theme")).isEmpty();
}

bool SoundsKcm::busy() const
{
    return m_process->state() != QProcess::NotRunning;
}

QString SoundsKcm::errorText() const
{
    return m_errorText;
}

QString SoundsKcm::program()
{
    const QString path = QStandardPaths::findExecutable(QStringLiteral("goldenglass-system"));
    if (path.isEmpty()) {
        setErrorText(i18nc("@info:status", "goldenglass-system was not found. Is the goldenglass-plasma package installed?"));
    }
    return path;
}

void SoundsKcm::load()
{
    const QString path = program();
    if (path.isEmpty()) {
        return;
    }
    // asíncrono: esperar aquí congelaría la interfaz; solo cuenta la última consulta
    const int query = ++m_statusQuery;
    GoldenGlass::runQuery(this, path, {QStringLiteral("status"), QStringLiteral("--json")}, [this, query](bool ok, const QByteArray &output, const QString &error) {
        if (query != m_statusQuery) {
            return;
        }
        if (!ok) {
            setErrorText(i18nc("@info:status", "The current state could not be read: %1", error));
            return;
        }
        const QJsonObject state = QJsonDocument::fromJson(output).object();
        m_sounds = state.value(QStringLiteral("sounds")).toBool();
        m_chime = state.value(QStringLiteral("chime")).toBool();
        Q_EMIT stateChanged();
    });
}

void SoundsKcm::setPart(const QString &part, bool enabled)
{
    setErrorText(QString());
    m_queue.append({enabled ? QStringLiteral("enable") : QStringLiteral("disable"), part});
    if (!busy()) {
        startNext();
    }
}

void SoundsKcm::startNext()
{
    const QString path = program();
    if (path.isEmpty()) {
        m_queue.clear();
        return;
    }
    m_process->start(path, m_queue.takeFirst());
    Q_EMIT busyChanged();
}

void SoundsKcm::preview(const QString &name)
{
    const QString file = themeFile(name);
    if (!file.isEmpty()) {
        QProcess::startDetached(QStringLiteral("pw-play"), {file});
    }
}

void SoundsKcm::setErrorText(const QString &text)
{
    if (m_errorText != text) {
        m_errorText = text;
        Q_EMIT errorTextChanged();
    }
}

#include "soundskcm.moc"
