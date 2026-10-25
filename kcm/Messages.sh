#! /usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
$XGETTEXT $(find . \( -path ./sounds -o -path ./boot -o -path ./dock -o -path ./iconstyle \) -prune -o \( -name \*.cpp -o -name \*.qml \) -print) -o $podir/kcm_goldenglass.pot
