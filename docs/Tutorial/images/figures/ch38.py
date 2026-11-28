"""Chapter 38, Ground Materials: authored figures.

@author Gary Yang
@brief Figures for 38-Ground-Materials.md
@copyright (C) Gary 2026
"""
from pathlib import Path
import math
import re

from figure_kit import *

CHAPTER = Path(__file__).resolve().parents[2] / "38-Ground-Materials.md"
ROCK_INK, ROCK_FILL = GRAY, "#a3adb8"   # rock, in the plot and in the strips
SAND_INK, SAND_FILL = GOLD, GOLD_SOFT


def height_depth():
    """HEIGHT_DEPTH, read from the chapter's own constant."""
    text = CHAPTER.read_text(encoding="utf-8")
    return float(re.search(r"const float HEIGHT_DEPTH = ([\d.]+);", text).group(1))


def shares(heights, weights, d):
    """Section 8's heightBlend for one pixel: keys, the line d below the highest, and each layer's share."""
    keys = [(h - 0.5) + w for h, w in zip(heights, weights)]
    line = max(keys) - d
    b = [max(k - line, 0.0) for k in keys]
    return keys, line, [v / sum(b) for v in b]


def rock_height(x):
    """A schematic rock photograph along the cross-section: stones standing up from low gaps."""
    stones = [(0.06, 0.85), (0.15, 0.95), (0.25, 0.80), (0.34, 0.92), (0.45, 0.86), (0.55, 0.97),
              (0.64, 0.84), (0.74, 0.93), (0.85, 0.88), (0.94, 0.96)]
    return max([0.12] + [0.12 + (top - 0.12) * math.exp(-((x - c) / 0.022) ** 2) for c, top in stones])


def sand_height(x):
    """A schematic sand photograph: gentle ripples about the middle."""
    return 0.5 + 0.13 * math.sin(2 * math.pi * 9 * x) + 0.05 * math.sin(2 * math.pi * 23 * x + 1.0)


def mix(a, b, t):
    """Two #rrggbb colours mixed, t of the second."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(p + (q - p) * t):02x}" for p, q in zip(ca, cb))


def height_blend_across_a_border():
    d = height_depth()
    assert d == 0.2, d
    # The chapter's worked pixels: rock alone, then half and half.
    assert shares([0.2, 0.8], [0.5, 0.5], d)[2] == [0.0, 1.0]
    half = shares([0.2, 0.8], [0.8, 0.2], d)[2]
    assert abs(half[0] - 0.5) < 1e-9 and abs(half[1] - 0.5) < 1e-9

    f = Figure("height-blend-across-a-border", 880, 452,
               "A cross-section across a border where the sand's weight rises from 0 to 1 and the rock's falls from 1 "
               "to 0. Each layer's key is its photograph's height, centred on 0, plus its weight; the layers whose keys "
               "stand within HEIGHT_DEPTH, 0.2, of the highest share the pixel. Below, what the pixels show: the rock's "
               "stones stand out of the sand past the middle, and the sand fills the gaps between them before it, "
               "where section 6's cross-fade prints one over the other at a fraction of each.",
               kind="computed plot", source="38-Ground-Materials.md, section 8 (Blending by height)",
               parameters={"HEIGHT_DEPTH": d, "samples": 373})

    x0, x1 = 64, 856
    top, bottom = 72, 262
    k_low, k_high = -0.45, 1.55

    def px(x):
        return x0 + (x1 - x0) * x

    def py(k):
        return bottom - (bottom - top) * (k - k_low) / (k_high - k_low)

    columns = 373
    xs = [i / (columns - 1) for i in range(columns)]
    data = []
    for x in xs:
        keys, line, (s_sand, s_rock) = shares([sand_height(x), rock_height(x)], [x, 1.0 - x], d)
        data.append((x, keys, line, s_sand))

    # The legend, above the plot.
    legend_y = 36
    f.line([(x0, legend_y), (x0 + 28, legend_y)], ROCK_INK, 2.2)
    f.text(x0 + 38, legend_y, "rock's key", 13.5, fill=GRAY)
    f.line([(x0 + 150, legend_y), (x0 + 178, legend_y)], SAND_INK, 2.2)
    f.text(x0 + 188, legend_y, "sand's key", 13.5, fill=GRAY)
    f.rect(x0 + 300, legend_y - 8, 28, 16, TEAL_FILL, TEAL, 1, 3)
    f.text(x0 + 338, legend_y, "from the highest key down d = 0.2: a layer whose key is in it shows",
           13.5, fill=GRAY)

    # The plot: a frame, the zero line, the band between the highest key and the line, then the two keys.
    f.rect(x0, top, x1 - x0, bottom - top, WHITE, HAIR, 1)
    f.line([(x0, py(0.0)), (x1, py(0.0))], GRID, 1)
    f.text(x0 - 8, py(0.0), "0", 13, fill=GRAY, anchor="end")
    f.text(x0 - 8, py(1.0), "1", 13, fill=GRAY, anchor="end")
    f.line([(x0, py(1.0)), (x1, py(1.0))], GRID, 1)
    band = [(px(x), py(line + d)) for x, _, line, _ in data] + [(px(x), py(line)) for x, _, line, _ in reversed(data)]
    f.polygon(band, TEAL_FILL, opacity=0.85)
    f.line([(px(x), py(line)) for x, _, line, _ in data], TEAL, 1.2, dash="5 4")
    f.line([(px(x), py(keys[1])) for x, keys, _, _ in data], ROCK_INK, 1.9)
    f.line([(px(x), py(keys[0])) for x, keys, _, _ in data], SAND_INK, 1.9)
    f.text(x0 - 8, (top + bottom) / 2 - 10, "key", 13.5, "italic", GRAY, anchor="end")

    # What the pixels show, by height; and section 6's cross-fade by the weights alone.
    strip_h = 30
    shown_y, fade_y = 300, 368
    step = (x1 - x0) / columns
    for strip_y, label, fraction in [(shown_y, "what the pixels show, by height", lambda e: e[3]),
                                     (fade_y, "section 6's cross-fade, by the weights alone", lambda e: e[0])]:
        f.text(x0, strip_y - 16, label, 13.5, "bold", INK)
        for i, entry in enumerate(data):
            f.rect(x0 + i * step, strip_y, step + 0.6, strip_h, mix(ROCK_FILL, SAND_FILL, fraction(entry)))
        f.rect(x0, strip_y, x1 - x0, strip_h, "none", LINE, 1)

    # The axis, under both strips.
    axis_y = fade_y + strip_h + 22
    f.text(x0, axis_y, "rock's weight 1", 13.5, fill=GRAY)
    f.text((x0 + x1) / 2, axis_y, "both 0.5", 13.5, fill=GRAY, anchor="middle")
    f.text(x1, axis_y, "sand's weight 1", 13.5, fill=GRAY, anchor="end")
    f.arrow([(x0 + 130, axis_y), ((x0 + x1) / 2 - 50, axis_y)], LINE, 1.2, 8)
    f.arrow([((x0 + x1) / 2 + 50, axis_y), (x1 - 130, axis_y)], LINE, 1.2, 8)
    f.height = round(axis_y + 22)
    return f


FIGURES = [height_blend_across_a_border]
