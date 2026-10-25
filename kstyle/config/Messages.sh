#!/bin/sh
$EXTRACTRC `find . -name \*.rc -o -name \*.ui -o -name \*.kcfg` >> rc.cpp
# las etiquetas de las opciones del estilo están en el .kcfg de kstyle/
$EXTRACTRC ../goldenglass.kcfg >> rc.cpp
$XGETTEXT `find . -name \*.cc -o -name \*.cpp -o -name \*.h` -o $podir/goldenglass_style_config.pot
rm -f rc.cpp
