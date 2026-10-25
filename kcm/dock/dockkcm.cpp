/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "dockkcm.h"

#include "goldenglass_tokens.h"
#include "../processquery.h"

#include <KLocalizedString>
#include <KPluginFactory>

#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QStandardPaths>
#include <QTimer>

K_PLUGIN_CLASS_WITH_JSON(DockKcm, "kcm_goldenglass_dock.json")

namespace
{
// mientras se arrastra un deslizador, se aplica tras esta pausa
constexpr int kApplyDelayMs = 250;

QString onOff(bool value)
{
    return value ? QStringLiteral("on") : QStringLiteral("off");
}
}

DockKcm::DockKcm(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
    , m_process(new QProcess(this))
    , m_applyTimer(new QTimer(this))
    , m_iconSize(GoldenGlass::Tokens::DockIconSize)
    , m_magnification(GoldenGlass::Tokens::DockMagnification)
    , m_magnificationSize(GoldenGlass::Tokens::DockMagnificationSize)
    , m_showRecent(GoldenGlass::Tokens::DockShowRecent)
{
    // Como en macOS, los cambios se aplican al momento: no hay «Aplicar».
    setButtons(KAbstractConfigModule::Default);

    m_applyTimer->setSingleShot(true);
    m_applyTimer->setInterval(kApplyDelayMs);
    connect(m_applyTimer, &QTimer::timeout, this, &DockKcm::apply);

    m_process->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_process, &QProcess::finished, this, [this](int exitCode, QProcess::ExitStatus status) {
        if (status != QProcess::NormalExit || exitCode != 0) {
            setErrorText(i18nc("@info:status", "The dock settings could not be applied: %1", QString::fromLocal8Bit(m_process->readAll()).trimmed()));
        }
        if (m_pending) {
            m_pending = false;
            apply();
            return;
        }
        Q_EMIT busyChanged();
    });
    connect(m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
        setErrorText(i18nc("@info:status", "goldenglass-dock could not be started: %1", m_process->errorString()));
        Q_EMIT busyChanged();
    });
}

int DockKcm::iconSize() const
{
    return m_iconSize;
}

void DockKcm::setIconSize(int value)
{
    if (m_iconSize != value) {
        m_iconSize = value;
        // la ampliación nunca es menor que el icono
        m_magnificationSize = qMax(m_magnificationSize, m_iconSize);
        changed();
    }
}

bool DockKcm::magnification() const
{
    return m_magnification;
}

void DockKcm::setMagnification(bool value)
{
    if (m_magnification != value) {
        m_magnification = value;
        changed();
    }
}

int DockKcm::magnificationSize() const
{
    return m_magnificationSize;
}

void DockKcm::setMagnificationSize(int value)
{
    value = qMax(value, m_iconSize);
    if (m_magnificationSize != value) {
        m_magnificationSize = value;
        changed();
    }
}

bool DockKcm::showRecent() const
{
    return m_showRecent;
}

void DockKcm::setShowRecent(bool value)
{
    if (m_showRecent != value) {
        m_showRecent = value;
        changed();
    }
}

bool DockKcm::available() const
{
    return m_available;
}

bool DockKcm::busy() const
{
    return m_process->state() != QProcess::NotRunning;
}

QString DockKcm::errorText() const
{
    return m_errorText;
}

int DockKcm::iconSizeMin() const
{
    return GoldenGlass::Tokens::DockSettingsIconSizeMin;
}

int DockKcm::iconSizeMax() const
{
    return GoldenGlass::Tokens::DockSettingsIconSizeMax;
}

int DockKcm::magnificationSizeMin() const
{
    return GoldenGlass::Tokens::DockSettingsMagnificationSizeMin;
}

int DockKcm::magnificationSizeMax() const
{
    return GoldenGlass::Tokens::DockSettingsMagnificationSizeMax;
}

QString DockKcm::program()
{
    const QString path = QStandardPaths::findExecutable(QStringLiteral("goldenglass-dock"));
    if (path.isEmpty()) {
        setErrorText(i18nc("@info:status", "goldenglass-dock was not found. Is the goldenglass-plasma package installed?"));
    }
    return path;
}

void DockKcm::load()
{
    const QString path = program();
    if (path.isEmpty()) {
        return;
    }
    // asíncrono: esperar aquí congelaría la interfaz; solo cuenta la última consulta
    const int query = ++m_getQuery;
    GoldenGlass::runQuery(this, path, {QStringLiteral("--get")}, [this, query](bool ok, const QByteArray &output, const QString &) {
        if (query != m_getQuery) {
            return;
        }
        if (m_available != ok) {
            m_available = ok;
            Q_EMIT availableChanged();
        }
        if (ok) {
            applySettings(QJsonDocument::fromJson(output).object());
        }
        // sin dock: el módulo lo explica
    });
}

void DockKcm::applySettings(const QJsonObject &s)
{
    // null = valor de fábrica (los tokens)
    m_iconSize = s.value(QStringLiteral("iconSize")).toInt(GoldenGlass::Tokens::DockIconSize);
    m_magnification = s.value(QStringLiteral("magnification")).toBool(GoldenGlass::Tokens::DockMagnification);
    m_magnificationSize = s.value(QStringLiteral("magnificationSize")).toInt(GoldenGlass::Tokens::DockMagnificationSize);
    m_showRecent = s.value(QStringLiteral("showRecent")).toBool(GoldenGlass::Tokens::DockShowRecent);
    Q_EMIT settingsChanged();
    setRepresentsDefaults(m_iconSize == GoldenGlass::Tokens::DockIconSize && m_magnification == GoldenGlass::Tokens::DockMagnification
                          && m_magnificationSize == GoldenGlass::Tokens::DockMagnificationSize && m_showRecent == GoldenGlass::Tokens::DockShowRecent);
}

void DockKcm::defaults()
{
    m_iconSize = GoldenGlass::Tokens::DockIconSize;
    m_magnification = GoldenGlass::Tokens::DockMagnification;
    m_magnificationSize = GoldenGlass::Tokens::DockMagnificationSize;
    m_showRecent = GoldenGlass::Tokens::DockShowRecent;
    changed();
}

void DockKcm::changed()
{
    Q_EMIT settingsChanged();
    setErrorText(QString());
    setRepresentsDefaults(m_iconSize == GoldenGlass::Tokens::DockIconSize && m_magnification == GoldenGlass::Tokens::DockMagnification
                          && m_magnificationSize == GoldenGlass::Tokens::DockMagnificationSize && m_showRecent == GoldenGlass::Tokens::DockShowRecent);
    m_applyTimer->start();
}

void DockKcm::apply()
{
    if (!m_available) {
        return;
    }
    if (busy()) {
        m_pending = true; // se aplica lo último al terminar
        return;
    }
    const QString path = program();
    if (path.isEmpty()) {
        return;
    }
    m_process->start(path,
                     {QStringLiteral("--icon-size"),
                      QString::number(m_iconSize),
                      QStringLiteral("--magnification"),
                      onOff(m_magnification),
                      QStringLiteral("--magnification-size"),
                      QString::number(qMax(m_magnificationSize, m_iconSize)),
                      QStringLiteral("--recent"),
                      onOff(m_showRecent)});
    Q_EMIT busyChanged();
}

void DockKcm::setErrorText(const QString &text)
{
    if (m_errorText != text) {
        m_errorText = text;
        Q_EMIT errorTextChanged();
    }
}

#include "dockkcm.moc"
