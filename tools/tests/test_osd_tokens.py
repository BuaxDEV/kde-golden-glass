# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""[osd]: the tokens of the volume and brightness HUD are validated by gen_tokens."""

from __future__ import annotations

import pytest

import gen_tokens


def with_osd(tokens: dict, **changes) -> dict:
    return {**tokens, "osd": {**tokens["osd"], **changes}}


def test_factory_osd_tokens_pass(tokens):
    gen_tokens.validate(tokens)
    assert tokens["osd"]["segments"] == 16 and tokens["osd"]["timeout_ms"] == 1500


@pytest.mark.parametrize(("key", "value"), [
    ("width", 0), ("height", 36.5), ("margin_top", -1), ("icon", True), ("segments", 0), ("segment_gap", -2),
    ("track_alpha", 1.2), ("fill_alpha", -0.1), ("alpha", float("nan")), ("alpha", "0.3"), ("timeout_ms", 0),
    ("open_ms", 260.5), ("close_ms", -1), ("open_scale", 1.1), ("open_scale", 0), ("open_overshoot", -1),
])
def test_bad_values_name_their_key(tokens, key, value):
    with pytest.raises(SystemExit, match=rf"\[osd\]\.{key}"):
        gen_tokens.validate(with_osd(tokens, **{key: value}))


def test_missing_or_unknown_keys(tokens):
    broken = with_osd(tokens)
    del broken["osd"]["segments"]
    with pytest.raises(SystemExit, match=r"\[osd\]: missing \['segments'\]"):
        gen_tokens.validate(broken)
    with pytest.raises(SystemExit, match=r"unknown \['radius'\]"):
        gen_tokens.validate(with_osd(tokens, radius=18))
    del tokens["osd"]
    with pytest.raises(SystemExit, match=r"\[osd\]"):
        gen_tokens.validate(tokens)


def test_the_pill_holds_its_icon_and_segments(tokens):
    with pytest.raises(SystemExit, match="must fit in height"):
        gen_tokens.validate(with_osd(tokens, icon=40))
    with pytest.raises(SystemExit, match="do not fit"):
        gen_tokens.validate(with_osd(tokens, segments=64, segment_gap=4))
