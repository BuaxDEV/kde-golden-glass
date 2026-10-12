# Módulo de Ajustes «Dock»: tamaño, ampliación y recientes (llama a goldenglass-dock).
kcmutils_add_qml_kcm(kcm_goldenglass_dock SOURCES dockkcm.cpp)
target_compile_definitions(kcm_goldenglass_dock PRIVATE TRANSLATION_DOMAIN="kcm_goldenglass_dock")
target_link_libraries(kcm_goldenglass_dock PRIVATE
    Qt6::Core
    KF6::KCMUtilsQuick
    KF6::CoreAddons
    KF6::I18n
)
