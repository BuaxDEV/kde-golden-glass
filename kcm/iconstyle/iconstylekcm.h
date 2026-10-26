/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <KQuickConfigModule>

#include <QStringList>
#include <QVariantMap>

#include <map>

class QJsonObject;
class QProcess;

//* Settings module «Icon style» (macOS 27 Appearance › «Icon & widget style»):
//* Default, Clear or Tinted app icons, light, dark or following the colour
//* scheme. goldenglass-icon-style stores the choice in goldenglassrc [Icons]
//* and applies the icon theme live; the accent is the system's.
class IconStyleKcm : public KQuickConfigModule
{
    Q_OBJECT
    //* "default", "clear" or "tinted"
    Q_PROPERTY(QString style READ style WRITE setStyle NOTIFY styleChanged)
    //* "light", "dark" or "auto"
    Q_PROPERTY(QString appearance READ appearance WRITE setAppearance NOTIFY appearanceChanged)
    //* style → paths of a few app icons of its theme, in the appearance in use
    Q_PROPERTY(QVariantMap previews READ previews NOTIFY stateChanged)
    //* the icon theme in use is a GoldenGlass one (otherwise choosing a style switches to it)
    Q_PROPERTY(bool inFamily READ inFamily NOTIFY stateChanged)
    //* goldenglass-icon-style answered
    Q_PROPERTY(bool available READ available NOTIFY stateChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QString errorText READ errorText NOTIFY errorTextChanged)

public:
    IconStyleKcm(QObject *parent, const KPluginMetaData &data);

    QString style() const;
    void setStyle(const QString &value);
    QString appearance() const;
    void setAppearance(const QString &value);
    QVariantMap previews() const;
    bool inFamily() const;
    bool available() const;
    bool busy() const;
    QString errorText() const;

    void load() override;
    void defaults() override;

Q_SIGNALS:
    void styleChanged();
    void appearanceChanged();
    void stateChanged();
    void busyChanged();
    void errorTextChanged();

private:
    // What goldenglass-icon-style is asked to change. One process runs at a
    // time; meanwhile the last request of each kind waits for its turn.
    enum class Request {
        Style,
        Appearance,
    };
    void request(Request kind, const QStringList &arguments);
    void start(const QStringList &arguments);
    QString program();
    void applyState(const QJsonObject &state);
    void updateRepresentsDefaults();
    void setErrorText(const QString &text);

    QProcess *m_process = nullptr;
    std::map<Request, QStringList> m_pending;
    int m_getQuery = 0;

    QString m_style;
    QString m_appearance;
    QString m_defaultStyle;
    QString m_defaultAppearance;
    QVariantMap m_previews;
    bool m_inFamily = false;
    bool m_available = false;
    QString m_errorText;
};
