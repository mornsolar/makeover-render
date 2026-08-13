"""Colour temperature conversion, kept out of the Blender scripts.

``LightingSpec.color_temperature_k`` is the physically meaningful value a
caller sets; Blender lights want linear RGB. Doing the conversion here means
it is unit-testable without Blender, and the same function could drive a
non-Blender preview renderer later without duplication.
"""

from __future__ import annotations

import math

RGB = tuple[float, float, float]

MIN_KELVIN = 1000
MAX_KELVIN = 40_000


def kelvin_to_rgb(kelvin: int) -> RGB:
    """Approximate blackbody colour for ``kelvin``, as linear 0..1 RGB.

    Tanner Helland's widely-used polynomial fit. Not physically exact - no
    closed form is - but stable, fast, and accurate enough that a 5500K key
    light reads as neutral white and a 2000K one reads as candle-warm, which
    is all a lighting *rig* needs.
    """
    if not MIN_KELVIN <= kelvin <= MAX_KELVIN:
        raise ValueError(f"colour temperature must be between {MIN_KELVIN} and {MAX_KELVIN}K")

    temp = kelvin / 100

    red = 255.0 if temp <= 66 else 329.698_727_446 * (temp - 60) ** -0.133_204_759_2
    green = (
        99.470_802_586_1 * _ln(temp) - 161.119_568_166_1
        if temp <= 66
        else 288.122_169_528_3 * (temp - 60) ** -0.075_514_849_2
    )
    if temp >= 66:
        blue = 255.0
    elif temp <= 19:
        blue = 0.0
    else:
        blue = 138.517_731_223_1 * _ln(temp - 10) - 305.044_792_730_7

    return (_clamp_255(red) / 255.0, _clamp_255(green) / 255.0, _clamp_255(blue) / 255.0)


def _clamp_255(value: float) -> float:
    return max(0.0, min(255.0, value))


def _ln(value: float) -> float:
    return math.log(value)


def hex_to_linear_rgb(hex_color: str) -> RGB:
    """Convert an sRGB hex colour (``#RRGGBB``, as every ``HexColor`` field in
    the contract is) to linear RGB, which is what a Principled BSDF expects.

    Assigning the sRGB byte values straight to ``base_color`` is a common
    mistake that washes out mid-tones - Blender's shader nodes work in linear
    light, and the display transform re-applies gamma on the way to screen.
    """
    if len(hex_color) != 7 or hex_color[0] != "#":
        raise ValueError(f"expected a '#RRGGBB' hex colour, got {hex_color!r}")
    red, green, blue = (int(hex_color[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
    return (_srgb_to_linear(red), _srgb_to_linear(green), _srgb_to_linear(blue))


def _srgb_to_linear(channel: float) -> float:
    if channel <= 0.040_45:
        return channel / 12.92
    # float.__pow__ is typed to allow a complex result (a negative base with a
    # fractional exponent), so mypy sees Any here without the explicit cast -
    # channel is already clamped to [0, 1] by construction, so it never is.
    return float(((channel + 0.055) / 1.055) ** 2.4)
