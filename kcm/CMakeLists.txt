# Módulo de Ajustes «Vidrio»: nivel de vidrio en vivo (llama a goldenglass-glass).
kcmutils_add_qml_kcm(kcm_goldenglass SOURCES glasskcm.cpp)
target_compile_definitions(kcm_goldenglass PRIVATE TRANSLATION_DOMAIN="kcm_goldenglass")
target_link_libraries(kcm_goldenglass PRIVATE
    Qt6::Core
    KF6::KCMUtilsQuick
    KF6::ConfigCore
    KF6::CoreAddons
    KF6::I18n
)

add_subdirectory(sounds)
add_subdirectory(boot)
add_subdirectory(dock)

# Prueba del módulo «Vidrio»: tres niveles seguidos, se aplica el último. No se
# instala. En ctest usa un goldenglass-glass de prueba (tests/bin) y una
# configuración temporal; contra una sesión Plasma real, ver el archivo.
if(BUILD_TESTING)
    add_executable(kcm_apply_test tests/kcm_apply_test.cpp)
    target_link_libraries(kcm_apply_test Qt6::Gui KF6::KCMUtilsQuick KF6::ConfigCore KF6::CoreAddons)

    # Consultas de estado sin bloquear (processquery.h)
    find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS Test)
    include(ECMAddTests)
    ecm_add_test(tests/processquery_test.cpp LINK_LIBRARIES Qt6::Core Qt6::Test TEST_NAME processquery_test)

    set(KCM_APPLY_TEST_CONFIG "${CMAKE_CURRENT_BINARY_DIR}/kcm_apply_test-config")
    file(MAKE_DIRECTORY "${KCM_APPLY_TEST_CONFIG}")
    # sin el nivel de la ejecución anterior
    add_test(NAME kcm_apply_test_clean
             COMMAND ${CMAKE_COMMAND} -E rm -f "${KCM_APPLY_TEST_CONFIG}/goldenglassrc")
    set_tests_properties(kcm_apply_test_clean PROPERTIES FIXTURES_SETUP kcm_apply_config)
    add_test(NAME kcm_apply_test COMMAND kcm_apply_test $<TARGET_FILE:kcm_goldenglass>)
    set_tests_properties(kcm_apply_test PROPERTIES
        FIXTURES_REQUIRED kcm_apply_config
        ENVIRONMENT_MODIFICATION
            "PATH=path_list_prepend:${CMAKE_CURRENT_SOURCE_DIR}/tests/bin;XDG_CONFIG_HOME=set:${KCM_APPLY_TEST_CONFIG};QT_QPA_PLATFORM=set:offscreen"
        TIMEOUT 60)

    # Ese goldenglass-glass de prueba solo cambia su clave: no borra
    # [Accessibility] ni otros grupos de goldenglassrc
    add_test(NAME goldenglass_glass_stub_test
             COMMAND sh "${CMAKE_CURRENT_SOURCE_DIR}/tests/goldenglass_glass_stub_test.sh"
                     "${CMAKE_CURRENT_SOURCE_DIR}/tests/bin/goldenglass-glass")
    set_tests_properties(goldenglass_glass_stub_test PROPERTIES TIMEOUT 60)
endif()
