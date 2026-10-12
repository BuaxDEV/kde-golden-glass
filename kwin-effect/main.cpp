/*
    SPDX-FileCopyrightText: 2021 Vlad Zahorodnii <vlad.zahorodnii@kde.org>

    SPDX-License-Identifier: GPL-2.0-or-later
*/

#include "glass.h"

namespace GoldenGlass
{
using namespace KWin;

KWIN_EFFECT_FACTORY_SUPPORTED_ENABLED(GlassEffect,
                                      "metadata.json",
                                      return GlassEffect::supported();
                                      ,
                                      return GlassEffect::enabledByDefault();)

} // namespace GoldenGlass

#include "main.moc"
