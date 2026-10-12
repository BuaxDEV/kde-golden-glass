# Módulo de Ajustes «Efectos de sonido»: sonidos y chime (llama a goldenglass-system).
kcmutils_add_qml_kcm(kcm_goldenglass_sounds SOURCES soundskcm.cpp)
target_compile_definitions(kcm_goldenglass_sounds PRIVATE TRANSLATION_DOMAIN="kcm_goldenglass_sounds")
target_link_libraries(kcm_goldenglass_sounds PRIVATE
    Qt6::Core
    KF6::KCMUtilsQuick
    KF6::CoreAddons
    KF6::I18n
)
