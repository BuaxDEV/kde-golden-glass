# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Módulo QML org.goldenglass.glass: le pasa a KWin la región de blur de las
# piezas de vidrio de una ventana (p. ej. las tarjetas sueltas del Centro de
# control), que Plasma no deja hacer desde QML, y da al shell los ajustes de
# la barra de menús (MenuBarSettings).
include(ECMQmlModule)

ecm_add_qml_module(goldenglassglassplugin
    URI org.goldenglass.glass
    GENERATE_PLUGIN_SOURCE
)

target_sources(goldenglassglassplugin PRIVATE glassregion.cpp glassregion.h menubarsettings.cpp menubarsettings.h)
# goldenglassroundedregion.h (solo cabecera, compartida con el estilo)
target_include_directories(goldenglassglassplugin PRIVATE ${CMAKE_SOURCE_DIR}/libgoldenglasscommon)

target_link_libraries(goldenglassglassplugin PRIVATE
    Qt6::Quick
    KF6::WindowSystem
    KF6::ConfigCore
)

ecm_finalize_qml_module(goldenglassglassplugin DESTINATION ${KDE_INSTALL_QMLDIR})
