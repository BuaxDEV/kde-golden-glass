#! /usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
$XGETTEXT $(find . -name \*.cpp -o -name \*.qml) -o $podir/kcm_goldenglass.pot
