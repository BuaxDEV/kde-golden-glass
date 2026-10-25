/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <KQuickConfigModule>

#include <QVariantList>

class QProcess;

//* Módulo de Ajustes «Vidrio»: aplica el nivel de vidrio en vivo con
//* goldenglass-glass (Plasma Style, decoración y estilo de apps).
class GlassKcm : public KQuickConfigModule
{
    Q_OBJECT
    Q_PROPERTY(double level READ level NOTIFY levelChanged)
    Q_PROPERTY(double defaultLevel READ defaultLevel CONSTANT)
    Q_PROPERTY(QVariantList notches READ notches CONSTANT)
    //* imán de las muescas y pausa antes de aplicar con el teclado (tokens [glass])
    Q_PROPERTY(double snapDistance READ snapDistance CONSTANT)
    Q_PROPERTY(int keyboardApplyDelay READ keyboardApplyDelay CONSTANT)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QString errorText READ errorText NOTIFY errorTextChanged)
    //* refracción de Liquid Glass (efecto de KWin goldenglass_glass)
    Q_PROPERTY(bool refraction READ refraction WRITE setRefraction NOTIFY refractionChanged)
    //* KWin tiene el efecto (si no: goldenglass-kstyle no compilado para esta versión de KWin)
    Q_PROPERTY(bool refractionAvailable READ refractionAvailable NOTIFY refractionChanged)
    //* franja de vidrio translúcido tras la barra de menús (de fábrica sin fondo, como macOS)
    Q_PROPERTY(bool menubarBackground READ menubarBackground WRITE setMenubarBackground NOTIFY menubarBackgroundChanged)

public:
    GlassKcm(QObject *parent, const KPluginMetaData &data);

    double level() const;
    double defaultLevel() const;
    QVariantList notches() const;
    double snapDistance() const;
    int keyboardApplyDelay() const;
    bool busy() const;
    QString errorText() const;
    bool refraction() const;
    void setRefraction(bool value);
    bool refractionAvailable() const;
    bool menubarBackground() const;
    void setMenubarBackground(bool value);

    //* aplica un nivel (0 = más transparente, 1 = más opaco); si ya hay uno
    //* aplicándose, se aplica el último pedido al terminar
    Q_INVOKABLE void applyLevel(double level);

    void load() override;
    void defaults() override;

Q_SIGNALS:
    void levelChanged();
    void busyChanged();
    void errorTextChanged();
    void refractionChanged();
    void menubarBackgroundChanged();

private:
    void startProcess(double level);
    void loadRefraction();
    void setLevel(double level);
    void updateRepresentsDefaults();
    void setErrorText(const QString &text);

    QProcess *m_process = nullptr;
    double m_level;
    double m_pending = -1;
    QString m_errorText;
    QProcess *m_refractionProcess = nullptr;
    bool m_refraction = false;
    bool m_refractionAvailable = false;
    int m_refractionQuery = 0;
    bool m_menubarBackground;
};
