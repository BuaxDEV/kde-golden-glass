#! /usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
$XGETTEXT $(find . -name \*.qml -o -name \*.js) -o $podir/plasma_applet_org.goldenglass.trash.pot
