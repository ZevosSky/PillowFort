"""Chapter 27, Grass: The Look: authored figures.

@author Gary Yang
@brief Figures for 27-Grass-Look.md
@copyright (C) Gary 2026
"""
from figure_kit import *


def fade(t):
    """Noise.glsl's quintic, 6t^5 - 15t^4 + 10t^3: flat at both ends."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def noise_1d(x, g0, g1):
    """Section 2's worked example: gradient noise in one dimension on the cell from 0 to 1."""
    a, b = g0 * (x - 0.0), g1 * (x - 1.0)     # each gradient's ramp, zero at its own point
    return a + (b - a) * fade(x)


def gradient_noise_in_one_dimension():
    cases = [(+1, -1, "gradients +1 and −1"), (+1, +1, "gradients +1 and +1")]
    for g0, g1, _ in cases:
        assert noise_1d(0.0, g0, g1) == 0 and noise_1d(1.0, g0, g1) == 0      # 0 at every grid point
    assert noise_1d(0.5, +1, -1) == 0.5 and noise_1d(0.5, +1, +1) == 0      # the hump, and the zero crossing
    assert (+1 * (0.5 - 0), -1 * (0.5 - 1)) == (0.5, 0.5) and (+1 * (0.5 - 1)) == -0.5

    f = Figure("gradient-noise-in-one-dimension", 880, 344,
               "Gradient noise on one cell, from x = 0 to 1. With gradients +1 and -1 the two ramps, +1 × (x - 0) and "
               "-1 × (x - 1), are both 0.5 at x = 0.5, and the noise is a hump of 0.5 between the points. With +1 and +1 "
               "the ramps give +0.5 and -0.5 there and cancel, so the noise crosses zero: a hump, then a dip.",
               kind="computed plot",
               source="27-Grass-Look.md, section 2 (Wind)",
               parameters={"fade": "6t^5 - 15t^4 + 10t^3", "cases": [[g0, g1] for g0, g1, _ in cases],
                           "atHalf": [noise_1d(0.5, g0, g1) for g0, g1, _ in cases]})
    limit, scale, axis_y = 0.6, 150, 176
    width = 300

    for index, (g0, g1, title) in enumerate(cases):
        left = 76 + index * 430

        def px(x):
            return left + x * width

        def py(y):
            return axis_y - y * scale

        f.text(px(0.5), 30, title, 15, "bold", anchor="middle")
        f.line([(px(-0.08), axis_y), (px(1.08), axis_y)], INK, 1.6)
        f.line([(px(0.5), py(limit)), (px(0.5), py(-limit))], GRID, 1.2)
        for y in (-0.5, 0.5):
            f.line([(px(0) - 5, py(y)), (px(0), py(y))], LINE, 1.2)
            f.text(px(0) - 10, py(y), f"{y:+g}".replace("-", "−"), 13.5, fill=GRAY, anchor="end")

        # Each gradient's ramp, through its own grid point, drawn while it stays inside the plot.
        for g, x0, colour in [(g0, 0.0, GOLD), (g1, 1.0, TEAL)]:
            xs = [x for x in (i / 100 for i in range(101)) if abs(g * (x - x0)) <= limit + 1e-9]
            f.line([(px(xs[0]), py(g * (xs[0] - x0))), (px(xs[-1]), py(g * (xs[-1] - x0)))], colour, 1.8, "7 5")
        curve = [(px(i / 200), py(noise_1d(i / 200, g0, g1))) for i in range(201)]
        f.line(curve, BLUE, 3)

        # What each ramp and the noise give at x = 0.5.
        ramp_a, ramp_b, value = g0 * 0.5, g1 * (0.5 - 1.0), noise_1d(0.5, g0, g1)
        if ramp_a == ramp_b:
            # Both ramps and the noise meet here; the hump below the point is clear for the label.
            f.circle(px(0.5), py(value), 5.5, BLUE, WHITE, 1.6)
            f.text(px(0.5), py(value) + 22, f"{value:g}", 15, "bold", BLUE, "middle")
        else:
            # Each label sits on the side its ramp leaves empty: above left of +0.5, below right of -0.5.
            for ramp, colour in [(ramp_a, GOLD), (ramp_b, TEAL)]:
                f.circle(px(0.5), py(ramp), 4.5, colour, WHITE, 1.4)
                above = ramp > 0
                f.text(px(0.5) + (-10 if above else 10), py(ramp) + (-12 if above else 13),
                       f"{ramp:+g}".replace("-", "−"), 14, fill=GOLD_TEXT if colour == GOLD else TEAL,
                       anchor="end" if above else "start")
            f.circle(px(0.5), py(value), 5.5, BLUE, WHITE, 1.6)
            f.text(px(0.5) + 12, py(value) - 14, f"{value:g}", 15, "bold", BLUE)

        for x in (0.0, 1.0):
            f.circle(px(x), axis_y, 5, INK, WHITE, 1.4)
        for x, label in [(0.0, "x = 0"), (0.5, "0.5"), (1.0, "1")]:
            f.text(px(x), axis_y + limit * scale + 22, label, 14, fill=GRAY, anchor="middle")

    # One key for both panels.
    key_y = 320
    for x, colour, dash, label in [(76, GOLD, "7 5", "the ramp of the gradient at 0"),
                                   (346, TEAL, "7 5", "the ramp of the gradient at 1"), (616, BLUE, None, "the noise")]:
        f.line([(x, key_y), (x + 30, key_y)], colour, 3 if dash is None else 1.8, dash)
        f.text(x + 40, key_y, label, 14)
    return f


FIGURES = [gradient_noise_in_one_dimension]
