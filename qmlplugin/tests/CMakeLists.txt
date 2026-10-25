# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Infraestructura común de las pruebas de qmlplugin/ (ctest, solo con
# BUILD_TESTING). Las usan los módulos org.goldenglass.glass y
# org.goldenglass.spotlight.
#
#   goldenglass_add_qmlplugin_test(<nombre>
#       [SOURCES <archivo>...]   # por defecto <nombre>.cpp
#       [LIBS <destino>...]      # además de Qt6::Test, Qt6::DBus y la biblioteca del módulo
#       [DBUS])                  # la prueba necesita un bus de sesión (servicios falsos)
#
# Crea el ejecutable QTest <nombre> y lo registra en ctest con
# QT_QPA_PLATFORM=offscreen. El código del módulo (GOLDENGLASS_QMLPLUGIN_SOURCES)
# se compila una vez en la biblioteca estática goldenglass_qmlplugin_core, que
# enlazan todas las pruebas; las que prueben otro módulo pasan sus fuentes en
# SOURCES y sus bibliotecas en LIBS.
#
# Aislamiento: la prueba usa GOLDENGLASS_TEST_MAIN(Clase) de testbus.h en lugar
# de QTEST_MAIN, que manda HOME y XDG_* a un directorio temporal y activa
# QStandardPaths::setTestModeEnabled. Es obligatorio: nunca se toca la
# configuración real de quien ejecuta ctest.
#
# Bus de sesión, nunca el real:
#   - con DBUS y dbus-run-session instalado, ctest ejecuta
#     «dbus-run-session -- <prueba>» con GOLDENGLASS_TEST_BUS=1 (un bus nuevo por
#     prueba);
#   - sin DBUS, o con DBUS pero sin dbus-run-session, la prueba corre con
#     DBUS_SESSION_BUS_ADDRESS=disabled: y sin GOLDENGLASS_TEST_BUS; las pruebas
#     D-Bus lo detectan con GG_REQUIRE_SESSION_BUS() (QSKIP con el motivo) y
#     ctest las marca como «Skipped».
# Por eso una prueba con DBUS no debe mezclarse con casos que no necesiten el
# bus: un QSKIP deja todo el ejecutable como omitido.

find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS Test Gui DBus)

find_program(GOLDENGLASS_DBUS_RUN_SESSION dbus-run-session)
if(NOT GOLDENGLASS_DBUS_RUN_SESSION)
    message(WARNING "dbus-run-session no encontrado: las pruebas D-Bus de qmlplugin se omitirán (paquete dbus)")
endif()

# El módulo sin QML: lo mismo que compila el plugin, para enlazarlo en las pruebas.
set(core_sources ${GOLDENGLASS_QMLPLUGIN_SOURCES})
list(TRANSFORM core_sources PREPEND "${CMAKE_CURRENT_SOURCE_DIR}/../")
add_library(goldenglass_qmlplugin_core STATIC ${core_sources})
set_target_properties(goldenglass_qmlplugin_core PROPERTIES
    AUTOMOC ON
    POSITION_INDEPENDENT_CODE ON
)
target_include_directories(goldenglass_qmlplugin_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/..
    ${CMAKE_SOURCE_DIR}/libgoldenglasscommon
)
target_link_libraries(goldenglass_qmlplugin_core PUBLIC ${GOLDENGLASS_QMLPLUGIN_LIBS} Qt6::Gui Qt6::DBus)

function(goldenglass_add_qmlplugin_test name)
    cmake_parse_arguments(PARSE_ARGV 1 ARG "DBUS" "" "SOURCES;LIBS")
    if(NOT ARG_SOURCES)
        set(ARG_SOURCES ${name}.cpp)
    endif()

    add_executable(${name} ${ARG_SOURCES})
    set_target_properties(${name} PROPERTIES AUTOMOC ON)
    target_include_directories(${name} PRIVATE ${CMAKE_CURRENT_FUNCTION_LIST_DIR})
    target_link_libraries(${name} PRIVATE goldenglass_qmlplugin_core Qt6::Test Qt6::DBus ${ARG_LIBS})

    set(env "QT_QPA_PLATFORM=offscreen")
    if(ARG_DBUS AND GOLDENGLASS_DBUS_RUN_SESSION)
        add_test(NAME ${name} COMMAND ${GOLDENGLASS_DBUS_RUN_SESSION} -- $<TARGET_FILE:${name}>)
        list(APPEND env "GOLDENGLASS_TEST_BUS=1")
    else()
        add_test(NAME ${name} COMMAND ${name})
        # sin bus: que ni siquiera se pueda llegar al de la sesión del usuario
        list(APPEND env "DBUS_SESSION_BUS_ADDRESS=disabled:" "GOLDENGLASS_TEST_BUS=0")
    endif()
    set_tests_properties(${name} PROPERTIES
        ENVIRONMENT "${env}"
        # QSKIP de QTest imprime «SKIP   : Clase::función() motivo»
        SKIP_REGULAR_EXPRESSION "SKIP +:"
        TIMEOUT 60
    )
endfunction()

goldenglass_add_qmlplugin_test(sandbox_test)
goldenglass_add_qmlplugin_test(menubarsettings_test)
goldenglass_add_qmlplugin_test(menubarsettings_watch_test DBUS)
goldenglass_add_qmlplugin_test(fakeservice_test DBUS)
goldenglass_add_qmlplugin_test(accessibilitysettings_test)
goldenglass_add_qmlplugin_test(accessibilitysettings_watch_test DBUS)
goldenglass_add_qmlplugin_test(glassregion_test)
goldenglass_add_qmlplugin_test(unitname_test)
goldenglass_add_qmlplugin_test(appunits_test DBUS)
goldenglass_add_qmlplugin_test(osdinterceptor_test DBUS)
