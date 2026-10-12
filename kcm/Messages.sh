#! /usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
$XGETTEXT $(find . -path ./sounds -prune -o \( -name \*.cpp -o -name \*.qml \) -print) -o $podir/kcm_goldenglass.pot
