"""Chapter 49, Bloom and Color Grading: authored figures.

@author Gary Yang
@brief Figures for 49-Bloom-And-Color-Grading.md
@copyright (C) Gary 2026
"""
from figure_kit import *


def frame_order_from_hdr_to_display():
    f = Figure("frame-order-from-hdr-to-display", 656, 498,
               "The frame order, from demo lighting and atmosphere through the resolved linear HDR scene, the bloom "
               "pyramid, scene + strength * bloom, manual exposure with RGB gain and saturation, one tone curve and one "
               "sRGB encode, to the UI. The scene also feeds the sum directly, and the composite holds the four steps "
               "from the sum to the encode.",
               source="49-Bloom-And-Color-Grading.md, section 1 (HDR Is The Input, Display Color Is The Output)")
    steps = [("demo lighting and atmosphere", "pass", "bold"),
             ("resolved linear HDR scene", "data", "bold"),
             ("bloom pyramid", "data", "bold"),
             ("scene + strength * bloom", "pass", "mono-bold"),
             ("manual exposure, RGB gain, saturation", "pass", "bold"),
             ("one tone curve", "pass", "bold"),
             ("one sRGB encode", "pass", "bold"),
             ("UI", "plain", "bold")]
    x, w, h, pitch, top = 72, 364, 38, 60, 42
    ys = [top + i * pitch for i in range(len(steps))]
    for y, (title, kind, font) in zip(ys, steps):
        node(f, x, y, w, h, title, kind=kind, title_font=font, size=14 if font.startswith("mono") else 15)
    for a, b in zip(ys, ys[1:]):
        f.arrow([(x + w / 2, a + h / 2), (x + w / 2, b - h / 2)])

    # The sum's other input: the scene itself, past the pyramid.
    side = x - 30
    f.arrow([(x, ys[1]), (side, ys[1]), (side, ys[3]), (x, ys[3])], GOLD, 1.7)

    # The four steps the composite holds.
    rail = x + w + 18
    f.line([(rail - 6, ys[3] - h / 2), (rail, ys[3] - h / 2), (rail, ys[6] + h / 2), (rail - 6, ys[6] + h / 2)], TEAL, 1.6)
    middle = (ys[3] + ys[6]) / 2
    f.text(rail + 14, middle - 10, "the composite", 15, "bold", TEAL)
    f.text(rail + 14, middle + 12, "Composite.frag.glsl", 13, "mono", GRAY)
    return f


FIGURES = [frame_order_from_hdr_to_display]
