/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <KQuickConfigModule>

#include <QStringList>

class QProcess;
class QTimer;

//* Módulo de Ajustes «Dock»: tamaño, ampliación y apps recientes del dock de
//* GoldenGlass, en vivo con goldenglass-dock (escribe la configuración del
//* plasmoid; el dock la aplica y ajusta el grosor de su panel).
class DockKcm : public KQuickConfigModule
{
    Q_OBJECT
    Q_PROPERTY(int iconSize READ iconSize WRITE setIconSize NOTIFY settingsChanged)
    Q_PROPERTY(bool magnification READ magnification WRITE setMagnification NOTIFY settingsChanged)
    Q_PROPERTY(int magnificationSize READ magnificationSize WRITE setMagnificationSize NOTIFY settingsChanged)
    Q_PROPERTY(bool showRecent READ showRecent WRITE setShowRecent NOTIFY settingsChanged)
    //* hay un dock de GoldenGlass en algún panel
    Q_PROPERTY(bool available READ available NOTIFY availableChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QString errorText READ errorText NOTIFY errorTextChanged)

public:
    DockKcm(QObject *parent, const KPluginMetaData &data);

    int iconSize() const;
    void setIconSize(int value);
    bool magnification() const;
    void setMagnification(bool value);
    int magnificationSize() const;
    void setMagnificationSize(int value);
    bool showRecent() const;
    void setShowRecent(bool value);
    bool available() const;
    bool busy() const;
    QString errorText() const;

    void load() override;
    void defaults() override;

Q_SIGNALS:
    void settingsChanged();
    void availableChanged();
    void busyChanged();
    void errorTextChanged();

private:
    QString program();
    void changed();
    void apply();
    void setErrorText(const QString &text);

    QProcess *m_process = nullptr;
    QTimer *m_applyTimer = nullptr;
    bool m_pending = false;

    int m_iconSize;
    bool m_magnification;
    int m_magnificationSize;
    bool m_showRecent;
    bool m_available = false;
    QString m_errorText;
};
