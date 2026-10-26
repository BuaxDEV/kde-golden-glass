#! /usr/bin/env bash
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
$XGETTEXT $(find . -name \*.cpp -o -name \*.qml) -o $podir/kcm_goldenglass_iconstyle.pot
