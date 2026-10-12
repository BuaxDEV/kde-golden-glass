/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <KQuickConfigModule>

#include <QStringList>

class QProcess;

//* Módulo de Ajustes «Arranque e inicio de sesión»: tema de Plymouth de
//* GoldenGlass (negro o gris) con goldenglass-system. Pide la contraseña de
//* administrador (pkexec) y regenera el initramfs: se aplica con «Aplicar».
class BootKcm : public KQuickConfigModule
{
    Q_OBJECT
    //* «system» (tema de la distribución), «dark» o «light»
    Q_PROPERTY(QString plymouth READ plymouth WRITE setPlymouth NOTIFY plymouthChanged)
    //* tema de Plymouth de la distribución (el que vuelve con «system»)
    Q_PROPERTY(QString systemTheme READ systemTheme NOTIFY stateChanged)
    Q_PROPERTY(bool installed READ installed NOTIFY stateChanged)
    //* avisos de goldenglass-system: «no-splash», «no-hook»
    Q_PROPERTY(QStringList warnings READ warnings NOTIFY stateChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QString errorText READ errorText NOTIFY errorTextChanged)

public:
    BootKcm(QObject *parent, const KPluginMetaData &data);

    QString plymouth() const;
    void setPlymouth(const QString &value);
    QString systemTheme() const;
    bool installed() const;
    QStringList warnings() const;
    bool busy() const;
    QString errorText() const;

    //* ruta de una imagen del tema de Plymouth (para las miniaturas)
    Q_INVOKABLE QString themeImage(const QString &variant, const QString &piece) const;

    void load() override;
    void save() override;
    void defaults() override;

Q_SIGNALS:
    void plymouthChanged();
    void stateChanged();
    void busyChanged();
    void errorTextChanged();

private:
    QString program();
    void setErrorText(const QString &text);
    void updateState();

    QProcess *m_process = nullptr;
    QString m_plymouth = QStringLiteral("system");
    QString m_loaded = QStringLiteral("system");
    QString m_systemTheme;
    bool m_installed = false;
    QStringList m_warnings;
    QString m_errorText;
};
