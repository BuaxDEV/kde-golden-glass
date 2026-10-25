/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <KQuickConfigModule>

#include <QColor>
#include <QStringList>

class QJsonObject;
class QProcess;

//* Módulo de Ajustes «Arranque e inicio de sesión»: tema de Plymouth de
//* GoldenGlass (negro o gris) y pantalla de inicio de sesión (tema de SDDM, o
//* fondo y ajustes en Plasma Login Manager), con goldenglass-system. Pide la
//* contraseña de administrador (pkexec): se aplica con «Aplicar».
class BootKcm : public KQuickConfigModule
{
    Q_OBJECT
    //* «system» (tema de la distribución), «dark» o «light»
    Q_PROPERTY(QString plymouth READ plymouth WRITE setPlymouth NOTIFY plymouthChanged)
    //* tema de Plymouth de la distribución (el que vuelve con «system»)
    Q_PROPERTY(QString systemTheme READ systemTheme NOTIFY stateChanged)
    Q_PROPERTY(bool installed READ installed NOTIFY stateChanged)
    //* avisos de Plymouth de goldenglass-system: «no-splash», «no-hook»
    Q_PROPERTY(QStringList warnings READ warnings NOTIFY stateChanged)

    //* pantalla de inicio de sesión de GoldenGlass activada (pendiente de aplicar)
    Q_PROPERTY(bool login READ login WRITE setLogin NOTIFY loginChanged)
    //* gestor activo: «sddm», «plasmalogin», otro o vacío
    Q_PROPERTY(QString loginManager READ loginManager NOTIFY stateChanged)
    Q_PROPERTY(bool loginInstalled READ loginInstalled NOTIFY stateChanged)
    //* avisos del login: «sddm-overridden», «unsupported-manager»
    Q_PROPERTY(QStringList loginWarnings READ loginWarnings NOTIFY stateChanged)

    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QString errorText READ errorText NOTIFY errorTextChanged)

    //* fondo de los temas de Plymouth negro y gris (tokens [boot]), para las miniaturas
    Q_PROPERTY(QColor darkBackground READ darkBackground CONSTANT)
    Q_PROPERTY(QColor lightBackground READ lightBackground CONSTANT)

public:
    BootKcm(QObject *parent, const KPluginMetaData &data);

    QString plymouth() const;
    void setPlymouth(const QString &value);
    QString systemTheme() const;
    bool installed() const;
    QStringList warnings() const;

    bool login() const;
    void setLogin(bool value);
    QString loginManager() const;
    bool loginInstalled() const;
    QStringList loginWarnings() const;

    bool busy() const;
    QString errorText() const;
    QColor darkBackground() const;
    QColor lightBackground() const;

    //* ruta de una imagen del tema de Plymouth (para las miniaturas)
    Q_INVOKABLE QString themeImage(const QString &variant, const QString &piece) const;

    void load() override;
    void save() override;
    void defaults() override;

Q_SIGNALS:
    void plymouthChanged();
    void loginChanged();
    void stateChanged();
    void busyChanged();
    void errorTextChanged();

private:
    QString program();
    void startNext();
    void applyStatus(const QJsonObject &state);
    void setErrorText(const QString &text);
    void updateState();

    QProcess *m_process = nullptr;
    QList<QStringList> m_queue; // argumentos de goldenglass-system pendientes
    int m_statusQuery = 0;

    QString m_plymouth = QStringLiteral("system");
    QString m_loadedPlymouth = QStringLiteral("system");
    QString m_systemTheme;
    bool m_installed = false;
    QStringList m_warnings;

    bool m_login = false;
    bool m_loadedLogin = false;
    QString m_loginManager;
    bool m_loginInstalled = false;
    QStringList m_loginWarnings;

    QString m_errorText;
};
