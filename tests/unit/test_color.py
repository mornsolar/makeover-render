"""Colour temperature and sRGB conversion."""

from __future__ import annotations

import pytest

from makeover_render.domain.model.color import hex_to_linear_rgb, kelvin_to_rgb


def test_a_neutral_temperature_is_close_to_white():
    # ~6600K is the daylight-white point of the Helland fit; this pins that
    # the polynomial coefficients above weren't transcribed wrong.
    red, green, blue = kelvin_to_rgb(6600)

    assert red == pytest.approx(1.0, abs=0.02)
    assert green == pytest.approx(1.0, abs=0.02)
    assert blue == pytest.approx(1.0, abs=0.02)


def test_a_warm_temperature_is_reddish():
    red, _, blue = kelvin_to_rgb(2000)

    assert red > blue


def test_a_cool_temperature_is_bluish():
    red, _, blue = kelvin_to_rgb(12_000)

    assert blue > red


def test_every_channel_stays_in_unit_range():
    for kelvin in (1000, 2000, 6600, 20_000, 40_000):
        for channel in kelvin_to_rgb(kelvin):
            assert 0.0 <= channel <= 1.0


def test_rejects_a_temperature_outside_the_supported_range():
    with pytest.raises(ValueError, match="between"):
        kelvin_to_rgb(500)


def test_black_hex_is_black_in_linear_space():
    assert hex_to_linear_rgb("#000000") == (0.0, 0.0, 0.0)


def test_white_hex_is_white_in_linear_space():
    assert hex_to_linear_rgb("#FFFFFF") == pytest.approx((1.0, 1.0, 1.0))


def test_mid_grey_srgb_is_darker_in_linear_space():
    # This is the whole point of the conversion: a naive assignment of sRGB
    # bytes to a linear shader input reads far too bright in the mid-tones.
    red, _, _ = hex_to_linear_rgb("#808080")

    assert red < 0.5


def test_rejects_a_malformed_hex_string():
    with pytest.raises(ValueError, match="RRGGBB"):
        hex_to_linear_rgb("not-a-colour")
