/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <KQuickConfigModule>

#include <QStringList>
#include <QVariantList>

#include <map>
#include <optional>

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
    //* «Reduce motion»: written by goldenglass-windows, which also swaps KWin's effects for fades
    Q_PROPERTY(bool reduceMotion READ reduceMotion WRITE setReduceMotion NOTIFY reduceMotionChanged)
    //* «Reduce transparency»: opaque glass without blur or refraction, through goldenglass-glass
    Q_PROPERTY(bool reduceTransparency READ reduceTransparency WRITE setReduceTransparency NOTIFY reduceTransparencyChanged)

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
    bool reduceMotion() const;
    void setReduceMotion(bool value);
    bool reduceTransparency() const;
    void setReduceTransparency(bool value);

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
    void reduceMotionChanged();
    void reduceTransparencyChanged();

private:
    // What goldenglass-glass is asked to change. One process runs at a time;
    // meanwhile the last request of each kind waits for its turn.
    enum class GlassRequest {
        Level,
        ReduceTransparency,
    };
    void requestGlass(GlassRequest kind, const QStringList &arguments);
    void startGlass(GlassRequest kind, const QStringList &arguments);
    void glassRequestFailed(GlassRequest kind, const QString &output);
    void loadReduceTransparency();
    void loadRefraction();
    void startReduceMotion(bool value);
    void loadReduceMotion();
    void setLevel(double level);
    void updateRepresentsDefaults();
    void setErrorText(const QString &text);

    QProcess *m_process = nullptr;
    GlassRequest m_runningGlass = GlassRequest::Level;
    std::map<GlassRequest, QStringList> m_pendingGlass;
    double m_level;
    QString m_errorText;
    QProcess *m_refractionProcess = nullptr;
    bool m_refraction = false;
    bool m_refractionAvailable = false;
    int m_refractionQuery = 0;
    bool m_menubarBackground;
    QProcess *m_reduceMotionProcess = nullptr;
    bool m_reduceMotion;
    std::optional<bool> m_pendingReduceMotion;
    bool m_reduceTransparency;
};
