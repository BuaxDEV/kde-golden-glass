/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Parámetros de la sombra de la decoración, sin KDecoration: tamaños de los
 * tokens [shadow.sizes.*], sombra de la ventana activa e inactiva (la inactiva
 * nunca mayor) y la clave con la que se comparten las texturas. Funciones
 * puras para probarlas sin KWin (tests/shadowparams_test.cpp).
 */
#pragma once

#include "goldenglass_tokens.h"

#include <QPoint>
#include <QRgb>

#include <algorithm>
#include <tuple>
#include <utility>

namespace GoldenGlass
{

// Opciones de ShadowSize en el orden de los <choice> del .kcfg (el índice es el
// valor del enum; ver tools/cxx_tokens.py SHADOW_SIZES)
enum ShadowSizeIndex {
    ShadowSizeNone = 0,
    ShadowSizeSmall,
    ShadowSizeMedium,
    ShadowSizeLarge,
    ShadowSizeVeryLarge,
};

struct ShadowParams {
    ShadowParams() = default;
    ShadowParams(const QPoint &offset, int radius, qreal opacity)
        : offset(offset)
        , radius(radius)
        , opacity(opacity)
    {
    }

    QPoint offset;
    int radius = 0;
    qreal opacity = 0;
};

struct CompositeShadowParams {
    CompositeShadowParams() = default;
    CompositeShadowParams(const QPoint &offset, const ShadowParams &shadow1, const ShadowParams &shadow2)
        : offset(offset)
        , shadow1(shadow1)
        , shadow2(shadow2)
    {
    }

    bool isNone() const
    {
        return std::max(shadow1.radius, shadow2.radius) == 0;
    }

    QPoint offset;
    ShadowParams shadow1;
    ShadowParams shadow2;
};

//* un tamaño fuera de rango cuenta como Large (lo que hacía Breeze)
inline int normalizedShadowSize(int size)
{
    return (size >= ShadowSizeNone && size <= ShadowSizeVeryLarge) ? size : int(ShadowSizeLarge);
}

//* tamaños de sombra: tokens [shadow.sizes.*]
inline CompositeShadowParams lookupShadowParams(int size)
{
    namespace T = GoldenGlass::Tokens;
    switch (normalizedShadowSize(size)) {
    case ShadowSizeNone:
        return CompositeShadowParams();
    case ShadowSizeSmall:
        return CompositeShadowParams(QPoint(0, T::ShadowSmallOffset),
                                     ShadowParams(QPoint(0, 0), T::ShadowSmallRadius, T::ShadowSmallAlpha),
                                     ShadowParams(QPoint(0, T::ShadowSmallAmbientOffset), T::ShadowSmallAmbientRadius, T::ShadowSmallAmbientAlpha));
    case ShadowSizeMedium:
        return CompositeShadowParams(QPoint(0, T::ShadowMediumOffset),
                                     ShadowParams(QPoint(0, 0), T::ShadowMediumRadius, T::ShadowMediumAlpha),
                                     ShadowParams(QPoint(0, T::ShadowMediumAmbientOffset), T::ShadowMediumAmbientRadius, T::ShadowMediumAmbientAlpha));
    case ShadowSizeLarge:
    default:
        return CompositeShadowParams(QPoint(0, T::ShadowLargeOffset),
                                     ShadowParams(QPoint(0, 0), T::ShadowLargeRadius, T::ShadowLargeAlpha),
                                     ShadowParams(QPoint(0, T::ShadowLargeAmbientOffset), T::ShadowLargeAmbientRadius, T::ShadowLargeAmbientAlpha));
    case ShadowSizeVeryLarge:
        return CompositeShadowParams(QPoint(0, T::ShadowVeryLargeOffset),
                                     ShadowParams(QPoint(0, 0), T::ShadowVeryLargeRadius, T::ShadowVeryLargeAlpha),
                                     ShadowParams(QPoint(0, T::ShadowVeryLargeAmbientOffset),
                                                  T::ShadowVeryLargeAmbientRadius,
                                                  T::ShadowVeryLargeAmbientAlpha));
    }
}

//* tamaño (opción de ShadowSize) y fuerza (0..255) de la sombra de un estado
struct ShadowSetting {
    int size = ShadowSizeNone;
    int strength = 0;

    bool operator==(const ShadowSetting &) const = default;
};

struct ShadowSettings {
    ShadowSetting active;
    ShadowSetting inactive;
};

//* Valores efectivos a partir de goldenglassrc [Common]: la sombra inactiva es
//* min(inactiva, activa) en tamaño y fuerza, y sin sombra activa no hay
//* inactiva.
inline ShadowSettings resolveShadowSettings(const ShadowSetting &active, const ShadowSetting &inactive)
{
    ShadowSettings result;
    result.active = {normalizedShadowSize(active.size), active.strength};
    if (result.active.size == ShadowSizeNone) {
        result.inactive = result.active;
        return result;
    }
    result.inactive = {std::min(normalizedShadowSize(inactive.size), result.active.size), std::min(inactive.strength, result.active.strength)};
    return result;
}

//* Todo lo que cambia la textura de una sombra. Dos ventanas (o los dos estados
//* de una) con el mismo estilo comparten la textura.
struct ShadowStyle {
    CompositeShadowParams params;
    int strength = 0; //* 0..255
    QRgb color = 0;
    qreal cornerRadius = 0; //* escalado a la rejilla de la pantalla
    int outlineTop = 0; //* el contorno empieza debajo de la barra flotante
    qreal outlineAlpha = 0; //* contorno de la ventana, × strength

    bool isNone() const
    {
        return params.isNone();
    }

    auto key() const
    {
        const auto layer = [](const ShadowParams &s) {
            return std::make_tuple(s.offset.x(), s.offset.y(), s.radius, s.opacity);
        };
        return std::tuple_cat(std::make_tuple(params.offset.x(), params.offset.y()),
                              layer(params.shadow1),
                              layer(params.shadow2),
                              std::make_tuple(strength, color, cornerRadius, outlineTop, outlineAlpha));
    }
};

using ShadowKey = decltype(std::declval<ShadowStyle>().key());

inline ShadowStyle makeShadowStyle(const ShadowSetting &setting, QRgb color, qreal cornerRadius, int outlineTop, qreal outlineAlpha)
{
    return ShadowStyle{lookupShadowParams(setting.size), setting.strength, color, cornerRadius, outlineTop, outlineAlpha};
}

} // namespace GoldenGlass
