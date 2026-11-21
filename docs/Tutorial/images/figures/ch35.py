"""Chapter 35, Seeing Far: authored figures.

@author Gary Yang
@brief Figures for 35-Seeing-Far.md
@copyright (C) Gary 2026
"""
from pathlib import Path
import re

from figure_kit import *

CHAPTER = Path(__file__).resolve().parents[2] / "35-Seeing-Far.md"


def constant(text, name):
    return float(re.search(rf"constexpr float\s+{name}\s*=\s*([\d.]+)f;", text).group(1))


def camera(f, x, y, color=BLUE):
    """A camera from above: a body and its lens, looking toward +x on the page."""
    f.rect(x - 22, y - 13, 30, 26, BLUE_FILL, color, 1.8, 4)
    f.polygon([(x + 8, y - 6), (x + 22, y - 12), (x + 22, y + 12), (x + 8, y + 6)], WHITE, color, 1.8)


def a_plate_pair_from_above():
    text = CHAPTER.read_text(encoding="utf-8")
    gap, front, back = constant(text, "PLATE_GAP"), constant(text, "FRONT_SIZE"), constant(text, "BACK_SIZE")
    assert (gap, front, back) == (1.0, 0.10, 0.12), (gap, front, back)

    f = Figure("a-plate-pair-from-above", 744, 244,
               "One pair of plates along its line from the camera, seen from above and not to scale: the coloured front "
               "plate, then 1 m behind it the white back plate, a little wider.",
               source="35-Seeing-Far.md, section 2 (What the plates test)",
               parameters={"plateGapMetres": gap, "frontSize": front, "backSize": back})
    y = 128
    cam_x = 58
    front_x, back_x = 466, 642
    half = 50   # the front plate's half width on the page; the back plate's is BACK_SIZE / FRONT_SIZE of it
    back_half = half * back / front

    camera(f, cam_x, y)
    f.text(cam_x - 2, y + 34, "camera", 15, "bold", BLUE, "middle")
    f.text(24, 28, "seen from above, not to scale", 13.5, "italic", GRAY)

    # The line from the camera, broken to say its length is not drawn.
    brk = 262
    f.line([(cam_x + 28, y), (brk - 7, y)], LINE, 1.6)
    f.line([(brk + 7, y), (back_x, y)], LINE, 1.6)
    for dx in (-7, 7):
        f.line([(brk + dx - 5, y + 9), (brk + dx + 5, y - 9)], LINE, 1.6)

    f.rect(front_x - 4, y - half, 8, 2 * half, RED, RED, 1.6, 2)   # red, as the 1 km pair's front plate is
    f.rect(back_x - 4, y - back_half, 8, 2 * back_half, WHITE, LINE, 1.6, 2)

    # The 1 m between them, as a dimension above the line.
    dim = y - back_half - 18
    for x in (front_x, back_x):
        f.line([(x, dim - 7), (x, dim + 7)], INK, 1.3)
    f.arrow([(front_x + 2, dim), (back_x - 2, dim)], INK, 1.3, 9, both=True)
    f.text((front_x + back_x) / 2, dim - 15, f"{gap:g} m", 15, "bold", anchor="middle")

    label_y = y + back_half + 14
    for x, name, note in [(front_x, "front", "(coloured)"), (back_x, "back", "(white, a little wider)")]:
        f.text(x, label_y, name, 15, "bold", anchor="middle")
        f.text(x, label_y + 20, note, 14, fill=GRAY, anchor="middle")
    return f


FIGURES = [a_plate_pair_from_above]
