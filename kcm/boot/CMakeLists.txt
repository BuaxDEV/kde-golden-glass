# Módulo de Ajustes «Arranque e inicio de sesión»: Plymouth (llama a goldenglass-system).
kcmutils_add_qml_kcm(kcm_goldenglass_boot SOURCES bootkcm.cpp)
target_compile_definitions(kcm_goldenglass_boot PRIVATE TRANSLATION_DOMAIN="kcm_goldenglass_boot")
target_link_libraries(kcm_goldenglass_boot PRIVATE
    Qt6::Core
    KF6::KCMUtilsQuick
    KF6::CoreAddons
    KF6::I18n
)
