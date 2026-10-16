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

QStringList strings(const QJsonValue &array)
{
    QStringList out;
    for (const QJsonValue &value : array.toArray()) {
        out.append(value.toString());
    }
    return out;
}
}

BootKcm::BootKcm(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
    , m_process(new QProcess(this))
{
    setButtons(KAbstractConfigModule::Apply | KAbstractConfigModule::Default);

    m_process->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_process, &QProcess::finished, this, [this](int exitCode, QProcess::ExitStatus status) {
        if (status != QProcess::NormalExit || exitCode != 0) {
            const QString output = QString::fromLocal8Bit(m_process->readAll()).trimmed();
            // 126/127: autenticación cancelada o denegada en pkexec
            if (exitCode == 126 || exitCode == 127) {
                setErrorText(i18nc("@info:status", "Nothing was changed: authentication was canceled or denied."));
            } else {
                setErrorText(i18nc("@info:status", "The change could not be applied: %1", output));
            }
            m_queue.clear();
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

bool BootKcm::login() const
{
    return m_login;
}

void BootKcm::setLogin(bool value)
{
    if (m_login == value) {
        return;
    }
    m_login = value;
    Q_EMIT loginChanged();
    updateState();
}

QString BootKcm::loginManager() const
{
    return m_loginManager;
}

bool BootKcm::loginInstalled() const
{
    return m_loginInstalled;
}

QStringList BootKcm::loginWarnings() const
{
    return m_loginWarnings;
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
    status.start(path, {QStringLiteral("status"), QStringLiteral("--json"), QStringLiteral("plymouth"), QStringLiteral("login")});
    if (!status.waitForFinished(5000) || status.exitCode() != 0) {
        setErrorText(i18nc("@info:status", "The current state could not be read: %1", QString::fromLocal8Bit(status.readAllStandardError()).trimmed()));
        return;
    }
    const QJsonObject state = QJsonDocument::fromJson(status.readAllStandardOutput()).object();

    const QJsonObject plymouth = state.value(QStringLiteral("plymouth")).toObject();
    m_loadedPlymouth = plymouth.value(QStringLiteral("enabled")).toBool() ? plymouth.value(QStringLiteral("variant")).toString() : kSystem;
    m_systemTheme = plymouth.value(QStringLiteral("system_theme")).toString();
    m_installed = plymouth.value(QStringLiteral("installed")).toBool();
    m_warnings = strings(plymouth.value(QStringLiteral("warnings")));

    const QJsonObject login = state.value(QStringLiteral("login")).toObject();
    m_loadedLogin = login.value(QStringLiteral("enabled")).toBool();
    m_loginManager = login.value(QStringLiteral("manager")).toString();
    m_loginInstalled = login.value(QStringLiteral("installed")).toBool();
    m_loginWarnings = strings(login.value(QStringLiteral("warnings")));
    Q_EMIT stateChanged();

    m_plymouth = m_loadedPlymouth;
    m_login = m_loadedLogin;
    Q_EMIT plymouthChanged();
    Q_EMIT loginChanged();
    updateState();
}

void BootKcm::save()
{
    if (busy()) {
        return;
    }
    // una sola llamada: goldenglass-system pide la contraseña con pkexec una vez
    // para todos los cambios (polkit no la recuerda: auth_admin)
    QStringList args{QStringLiteral("apply")};
    if (m_plymouth != m_loadedPlymouth) {
        args << QStringLiteral("--plymouth") << m_plymouth;
    }
    if (m_login != m_loadedLogin) {
        args << QStringLiteral("--login") << (m_login ? QStringLiteral("on") : QStringLiteral("off"));
    }
    if (args.size() > 1) {
        m_queue.append(args);
    }
    if (!m_queue.isEmpty()) {
        setErrorText(QString());
        startNext();
    }
}

void BootKcm::startNext()
{
    const QString path = program();
    if (path.isEmpty()) {
        m_queue.clear();
        return;
    }
    m_process->start(path, m_queue.takeFirst());
    Q_EMIT busyChanged();
}

void BootKcm::defaults()
{
    setPlymouth(QStringLiteral("dark"));
    setLogin(m_loginInstalled);
}

void BootKcm::updateState()
{
    setNeedsSave(m_plymouth != m_loadedPlymouth || m_login != m_loadedLogin);
    setRepresentsDefaults(m_plymouth == QLatin1String("dark") && m_login == m_loginInstalled);
}

void BootKcm::setErrorText(const QString &text)
{
    if (m_errorText != text) {
        m_errorText = text;
        Q_EMIT errorTextChanged();
    }
}

#include "bootkcm.moc"
