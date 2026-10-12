/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <KQuickConfigModule>

#include <QStringList>

class QProcess;

//* Módulo de Ajustes «Efectos de sonido»: activa el tema de sonidos y el chime
//* de GoldenGlass en vivo con goldenglass-system.
class SoundsKcm : public KQuickConfigModule
{
    Q_OBJECT
    Q_PROPERTY(bool soundsEnabled READ soundsEnabled NOTIFY stateChanged)
    Q_PROPERTY(bool chimeEnabled READ chimeEnabled NOTIFY stateChanged)
    Q_PROPERTY(bool themeInstalled READ themeInstalled CONSTANT)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QString errorText READ errorText NOTIFY errorTextChanged)

public:
    SoundsKcm(QObject *parent, const KPluginMetaData &data);

    bool soundsEnabled() const;
    bool chimeEnabled() const;
    bool themeInstalled() const;
    bool busy() const;
    QString errorText() const;

    //* activa o desactiva una parte de goldenglass-system («sounds», «chime»);
    //* las peticiones seguidas se aplican en orden
    Q_INVOKABLE void setPart(const QString &part, bool enabled);
    //* reproduce un sonido del tema GoldenGlass (nombre freedesktop)
    Q_INVOKABLE void preview(const QString &name);

    void load() override;

Q_SIGNALS:
    void stateChanged();
    void busyChanged();
    void errorTextChanged();

private:
    QString program();
    void startNext();
    void setErrorText(const QString &text);

    QProcess *m_process = nullptr;
    QStringList m_queue; // «enable sounds», «disable chime»…
    bool m_sounds = false;
    bool m_chime = false;
    QString m_errorText;
};
