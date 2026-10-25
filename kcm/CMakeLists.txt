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

# Prueba de integración (necesita una sesión Plasma; ver el comentario del
# archivo). No se instala ni se registra en ctest.
if(BUILD_TESTING)
    add_executable(kcm_apply_test tests/kcm_apply_test.cpp)
    target_link_libraries(kcm_apply_test Qt6::Gui KF6::KCMUtilsQuick KF6::ConfigCore KF6::CoreAddons)

    # Consultas de estado sin bloquear (processquery.h)
    find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS Test)
    include(ECMAddTests)
    ecm_add_test(tests/processquery_test.cpp LINK_LIBRARIES Qt6::Core Qt6::Test TEST_NAME processquery_test)
endif()
