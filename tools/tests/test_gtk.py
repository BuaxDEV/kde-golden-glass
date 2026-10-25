# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""gtk: semáforos CSD grises sin foco que se colorean al pasar el ratón."""

from __future__ import annotations

import gtk


def test_gtk4_backdrop_gray_with_group_hover(tokens):
    tl = tokens["traffic_lights"]
    assert tl["inactive_colored"] is False
    css = gtk._shape(tokens, gtk4=True)
    assert "windowcontrols > button:backdrop {" in css
    for cls, key in (("close", "close"), ("minimize", "minimize"), ("maximize", "zoom")):
        rule = next(line for line in css.splitlines()
                    if line.startswith(f"windowcontrols:backdrop:hover > button.{cls} {{"))
        assert f"background-color: {tl[key]}" in rule
        assert tl[key + "_border"] in rule
    assert "windowcontrols:hover > button image { opacity: 1; }" in css


def test_gtk3_backdrop_hover_per_button_fallback(tokens):
    tl = tokens["traffic_lights"]
    css = gtk._shape(tokens, gtk4=False)
    for cls, key in (("close", "close"), ("minimize", "minimize"), ("maximize", "zoom")):
        rule = next(line for line in css.splitlines()
                    if line.startswith(f"headerbar button.titlebutton.{cls}:backdrop:hover"))
        assert f"background-color: {tl[key]}" in rule
    assert "windowcontrols" not in css


def test_inactive_colored_true_has_no_gray_rules(tokens):
    tokens["traffic_lights"]["inactive_colored"] = True
    for gtk4 in (True, False):
        css = gtk._shape(tokens, gtk4=gtk4)
        assert ":backdrop" not in css
