/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <QProcess>
#include <QStringList>
#include <QTimer>

#include <functional>

namespace GoldenGlass
{
//* tiempo máximo de una consulta de estado; después se mata el proceso
constexpr int kQueryTimeoutMs = 5000;

//* Lanza una consulta de estado (`program args`) sin bloquear la interfaz y
//* llama a done al terminar: ok solo si salió con normalidad y código 0;
//* output es la salida estándar y error, el motivo del fallo. El proceso es
//* hijo de context: si context se destruye antes, done no se llama.
inline void runQuery(QObject *context,
                     const QString &program,
                     const QStringList &args,
                     std::function<void(bool ok, const QByteArray &output, const QString &error)> done)
{
    auto process = new QProcess(context);
    QObject::connect(process, &QProcess::finished, context, [process, done](int exitCode, QProcess::ExitStatus status) {
        const bool ok = status == QProcess::NormalExit && exitCode == 0;
        QString error;
        if (!ok) {
            error = QString::fromLocal8Bit(process->readAllStandardError()).trimmed();
            if (error.isEmpty()) {
                error = process->errorString();
            }
        }
        done(ok, ok ? process->readAllStandardOutput() : QByteArray(), error);
        process->deleteLater();
    });
    // sin arrancar no llega finished
    QObject::connect(process, &QProcess::errorOccurred, context, [process, done](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart) {
            done(false, QByteArray(), process->errorString());
            process->deleteLater();
        }
    });
    QTimer::singleShot(kQueryTimeoutMs, process, &QProcess::kill);
    process->start(program, args);
}
}
