/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "bootkcm.h"

#include <KLocalizedString>
#include <KPluginFactory>

#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QStandardPaths>
#include <QUrl>

K_PLUGIN_CLASS_WITH_JSON(BootKcm, "kcm_goldenglass_boot.json")

namespace
{
const QString kSystem = QStringLiteral("system");

QString themeId(const QString &variant)
{
    return variant == QLatin1String("light") ? QStringLiteral("goldenglass-light") : QStringLiteral("goldenglass");
}
}

BootKcm::BootKcm(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
    , m_process(new QProcess(this))
{
    setButtons(KAbstractConfigModule::Apply | KAbstractConfigModule::Default);

    m_process->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_process, &QProcess::finished, this, [this](int exitCode, QProcess::ExitStatus status) {
        // 126/127: autenticación cancelada o denegada en pkexec
        if (status != QProcess::NormalExit || exitCode != 0) {
            const QString output = QString::fromLocal8Bit(m_process->readAll()).trimmed();
            if (exitCode == 126 || exitCode == 127) {
                setErrorText(i18nc("@info:status", "The boot screen was not changed: authentication was canceled or denied."));
            } else {
                setErrorText(i18nc("@info:status", "The boot screen could not be changed: %1", output));
            }
        }
        load();
        Q_EMIT busyChanged();
    });
    connect(m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
        setErrorText(i18nc("@info:status", "goldenglass-system could not be started: %1", m_process->errorString()));
        Q_EMIT busyChanged();
    });
}

QString BootKcm::plymouth() const
{
    return m_plymouth;
}

void BootKcm::setPlymouth(const QString &value)
{
    if (m_plymouth == value) {
        return;
    }
    m_plymouth = value;
    Q_EMIT plymouthChanged();
    updateState();
}

QString BootKcm::systemTheme() const
{
    return m_systemTheme;
}

bool BootKcm::installed() const
{
    return m_installed;
}

QStringList BootKcm::warnings() const
{
    return m_warnings;
}

bool BootKcm::busy() const
{
    return m_process->state() != QProcess::NotRunning;
}

QString BootKcm::errorText() const
{
    return m_errorText;
}

QString BootKcm::themeImage(const QString &variant, const QString &piece) const
{
    const QString id = themeId(variant);
    const QString path = QStringLiteral("/usr/share/plymouth/themes/%1/%2@2x.png").arg(id, piece);
    return QFileInfo::exists(path) ? QUrl::fromLocalFile(path).toString() : QString();
}

QString BootKcm::program()
{
    const QString path = QStandardPaths::findExecutable(QStringLiteral("goldenglass-system"));
    if (path.isEmpty()) {
        setErrorText(i18nc("@info:status", "goldenglass-system was not found. Is the goldenglass-plasma package installed?"));
    }
    return path;
}

void BootKcm::load()
{
    const QString path = program();
    if (path.isEmpty()) {
        return;
    }
    QProcess status;
    status.start(path, {QStringLiteral("status"), QStringLiteral("--json"), QStringLiteral("plymouth")});
    if (!status.waitForFinished(5000) || status.exitCode() != 0) {
        setErrorText(i18nc("@info:status", "The current state could not be read: %1", QString::fromLocal8Bit(status.readAllStandardError()).trimmed()));
        return;
    }
    const QJsonObject plymouth = QJsonDocument::fromJson(status.readAllStandardOutput()).object().value(QStringLiteral("plymouth")).toObject();
    m_loaded = plymouth.value(QStringLiteral("enabled")).toBool() ? plymouth.value(QStringLiteral("variant")).toString() : kSystem;
    m_systemTheme = plymouth.value(QStringLiteral("system_theme")).toString();
    m_installed = plymouth.value(QStringLiteral("installed")).toBool();
    m_warnings.clear();
    for (const QJsonValue &code : plymouth.value(QStringLiteral("warnings")).toArray()) {
        m_warnings.append(code.toString());
    }
    Q_EMIT stateChanged();

    m_plymouth = m_loaded;
    Q_EMIT plymouthChanged();
    updateState();
}

void BootKcm::save()
{
    if (m_plymouth == m_loaded || busy()) {
        return;
    }
    const QString path = program();
    if (path.isEmpty()) {
        return;
    }
    setErrorText(QString());
    // goldenglass-system pide la contraseña con pkexec y regenera el initramfs
    if (m_plymouth == kSystem) {
        m_process->start(path, {QStringLiteral("disable"), QStringLiteral("plymouth")});
    } else {
        m_process->start(path, {QStringLiteral("enable"), QStringLiteral("plymouth"), QStringLiteral("--variant"), m_plymouth});
    }
    Q_EMIT busyChanged();
}

void BootKcm::defaults()
{
    setPlymouth(QStringLiteral("dark"));
}

void BootKcm::updateState()
{
    setNeedsSave(m_plymouth != m_loaded);
    setRepresentsDefaults(m_plymouth == QLatin1String("dark"));
}

void BootKcm::setErrorText(const QString &text)
{
    if (m_errorText != text) {
        m_errorText = text;
        Q_EMIT errorTextChanged();
    }
}

#include "bootkcm.moc"
