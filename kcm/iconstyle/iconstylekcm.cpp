/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "iconstylekcm.h"

#include "../processquery.h"

#include <KLocalizedString>
#include <KPluginFactory>

#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QStandardPaths>

K_PLUGIN_CLASS_WITH_JSON(IconStyleKcm, "kcm_goldenglass_iconstyle.json")

namespace
{
const QString kTool = QStringLiteral("goldenglass-icon-style");
// what goldenglass-icon-style ships with, until its --get says otherwise
const QString kFactoryStyle = QStringLiteral("default");
const QString kFactoryAppearance = QStringLiteral("auto");
}

IconStyleKcm::IconStyleKcm(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
    , m_process(new QProcess(this))
    , m_style(kFactoryStyle)
    , m_appearance(kFactoryAppearance)
    , m_defaultStyle(kFactoryStyle)
    , m_defaultAppearance(kFactoryAppearance)
{
    // applied live, like the other GoldenGlass modules: no «Apply»
    setButtons(KAbstractConfigModule::Default);

    m_process->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_process, &QProcess::finished, this, [this](int exitCode, QProcess::ExitStatus status) {
        if (status != QProcess::NormalExit || exitCode != 0) {
            setErrorText(i18nc("@info:status", "The icon style could not be applied: %1", QString::fromLocal8Bit(m_process->readAll()).trimmed()));
        }
        if (!m_pending.empty()) {
            auto next = m_pending.extract(m_pending.begin());
            start(next.mapped());
            return;
        }
        Q_EMIT busyChanged();
        load();
    });
    connect(m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error != QProcess::FailedToStart) {
            return; // finished follows
        }
        setErrorText(i18nc("@info:status", "goldenglass-icon-style could not be started: %1", m_process->errorString()));
        m_pending.clear();
        Q_EMIT busyChanged();
        load();
    });
}

QString IconStyleKcm::style() const
{
    return m_style;
}

void IconStyleKcm::setStyle(const QString &value)
{
    if (m_style == value) {
        return;
    }
    m_style = value;
    Q_EMIT styleChanged();
    updateRepresentsDefaults();
    setErrorText(QString());
    request(Request::Style, {QStringLiteral("--style"), value});
}

QString IconStyleKcm::appearance() const
{
    return m_appearance;
}

void IconStyleKcm::setAppearance(const QString &value)
{
    if (m_appearance == value) {
        return;
    }
    m_appearance = value;
    Q_EMIT appearanceChanged();
    updateRepresentsDefaults();
    setErrorText(QString());
    request(Request::Appearance, {QStringLiteral("--appearance"), value});
}

QVariantMap IconStyleKcm::previews() const
{
    return m_previews;
}

bool IconStyleKcm::inFamily() const
{
    return m_inFamily;
}

bool IconStyleKcm::available() const
{
    return m_available;
}

bool IconStyleKcm::busy() const
{
    return m_process->state() != QProcess::NotRunning;
}

QString IconStyleKcm::errorText() const
{
    return m_errorText;
}

QString IconStyleKcm::program()
{
    const QString path = QStandardPaths::findExecutable(kTool);
    if (path.isEmpty()) {
        setErrorText(i18nc("@info:status", "goldenglass-icon-style was not found. Is the goldenglass-icons package installed?"));
    }
    return path;
}

void IconStyleKcm::load()
{
    const QString path = program();
    if (path.isEmpty()) {
        return;
    }
    // asynchronous: waiting here would freeze the module; only the last query counts
    const int query = ++m_getQuery;
    GoldenGlass::runQuery(this, path, {QStringLiteral("--get")}, [this, query](bool ok, const QByteArray &output, const QString &error) {
        if (query != m_getQuery) {
            return;
        }
        if (!ok) {
            setErrorText(i18nc("@info:status", "The icon style could not be read: %1", error));
        }
        m_available = ok;
        if (ok) {
            applyState(QJsonDocument::fromJson(output).object());
        }
        Q_EMIT stateChanged();
    });
}

void IconStyleKcm::applyState(const QJsonObject &state)
{
    m_defaultStyle = state.value(QStringLiteral("defaultStyle")).toString(kFactoryStyle);
    m_defaultAppearance = state.value(QStringLiteral("defaultAppearance")).toString(kFactoryAppearance);
    m_previews = state.value(QStringLiteral("previews")).toObject().toVariantMap();
    m_inFamily = state.value(QStringLiteral("inFamily")).toBool();
    // a choice still waiting for its turn keeps what the user picked
    if (!busy()) {
        const QString style = state.value(QStringLiteral("style")).toString(m_defaultStyle);
        if (m_style != style) {
            m_style = style;
            Q_EMIT styleChanged();
        }
        const QString appearance = state.value(QStringLiteral("appearance")).toString(m_defaultAppearance);
        if (m_appearance != appearance) {
            m_appearance = appearance;
            Q_EMIT appearanceChanged();
        }
    }
    updateRepresentsDefaults();
}

void IconStyleKcm::defaults()
{
    setStyle(m_defaultStyle);
    setAppearance(m_defaultAppearance);
}

void IconStyleKcm::request(Request kind, const QStringList &arguments)
{
    if (busy()) {
        m_pending[kind] = arguments;
        return;
    }
    start(arguments);
}

void IconStyleKcm::start(const QStringList &arguments)
{
    const QString path = program();
    if (path.isEmpty()) {
        m_pending.clear();
        Q_EMIT busyChanged();
        return;
    }
    m_process->start(path, arguments);
    Q_EMIT busyChanged();
}

void IconStyleKcm::updateRepresentsDefaults()
{
    setRepresentsDefaults(m_style == m_defaultStyle && m_appearance == m_defaultAppearance);
}

void IconStyleKcm::setErrorText(const QString &text)
{
    if (m_errorText != text) {
        m_errorText = text;
        Q_EMIT errorTextChanged();
    }
}

#include "iconstylekcm.moc"
