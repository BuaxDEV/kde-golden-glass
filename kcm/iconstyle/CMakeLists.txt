# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Settings module «Icon style»: Default, Clear or Tinted app icons, light, dark
# or auto (calls goldenglass-icon-style).
kcmutils_add_qml_kcm(kcm_goldenglass_iconstyle SOURCES iconstylekcm.cpp)
target_compile_definitions(kcm_goldenglass_iconstyle PRIVATE TRANSLATION_DOMAIN="kcm_goldenglass_iconstyle")
target_link_libraries(kcm_goldenglass_iconstyle PRIVATE
    Qt6::Core
    KF6::KCMUtilsQuick
    KF6::CoreAddons
    KF6::I18n
)
