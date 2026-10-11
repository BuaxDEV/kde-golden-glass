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
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QString errorText READ errorText NOTIFY errorTextChanged)

public:
    GlassKcm(QObject *parent, const KPluginMetaData &data);

    double level() const;
    double defaultLevel() const;
    QVariantList notches() const;
    bool busy() const;
    QString errorText() const;

    //* aplica un nivel (0 = más transparente, 1 = más opaco); si ya hay uno
    //* aplicándose, se aplica el último pedido al terminar
    Q_INVOKABLE void applyLevel(double level);

    void load() override;
    void defaults() override;

Q_SIGNALS:
    void levelChanged();
    void busyChanged();
    void errorTextChanged();

private:
    void startProcess(double level);
    void setLevel(double level);
    void setErrorText(const QString &text);

    QProcess *m_process = nullptr;
    double m_level;
    double m_pending = -1;
    QString m_errorText;
};
