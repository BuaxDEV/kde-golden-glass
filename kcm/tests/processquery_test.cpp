/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Consultas de estado de los módulos de Ajustes (processquery.h): no
 * bloquean y distinguen éxito, código de salida y fallo al arrancar.
 */

#include "../processquery.h"

#include <QTest>

class ProcessQueryTest : public QObject
{
    Q_OBJECT

private:
    bool m_called = false;
    bool m_ok = false;
    QByteArray m_output;
    QString m_error;

    void start(const QString &program, const QStringList &args)
    {
        m_called = false;
        GoldenGlass::runQuery(this, program, args, [this](bool ok, const QByteArray &output, const QString &error) {
            m_called = true;
            m_ok = ok;
            m_output = output;
            m_error = error;
        });
    }

private Q_SLOTS:
    void success()
    {
        start(QStringLiteral("/bin/sh"), {QStringLiteral("-c"), QStringLiteral("printf on")});
        // no bloquea: el resultado llega desde el bucle de eventos
        QVERIFY(!m_called);
        QTRY_VERIFY_WITH_TIMEOUT(m_called, 5000);
        QVERIFY(m_ok);
        QCOMPARE(m_output, QByteArray("on"));
    }

    void exitCode()
    {
        start(QStringLiteral("/bin/sh"), {QStringLiteral("-c"), QStringLiteral("printf on; echo broken >&2; exit 3")});
        QTRY_VERIFY_WITH_TIMEOUT(m_called, 5000);
        QVERIFY(!m_ok);
        QVERIFY(m_output.isEmpty());
        QCOMPARE(m_error, QStringLiteral("broken"));
    }

    void failedToStart()
    {
        start(QStringLiteral("/nonexistent/goldenglass-query"), {});
        QTRY_VERIFY_WITH_TIMEOUT(m_called, 5000);
        QVERIFY(!m_ok);
        QVERIFY(!m_error.isEmpty());
    }
};

QTEST_GUILESS_MAIN(ProcessQueryTest)
#include "processquery_test.moc"
