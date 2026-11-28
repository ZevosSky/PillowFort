"""Chapter 30, A Rougher Sea: authored figures.

@author Gary Yang
@brief Figures for 30-A-Rougher-Sea.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *

# Section 2's bands: cascade 0 takes waves from its 250 m patch down to 37 / 6 m, cascade 1 down to 7 / 6 m,
# cascade 2 everything shorter.
PATCHES = (250.0, 37.0, 7.0)
BOUNDS = (PATCHES[0], PATCHES[1] / 6, PATCHES[2] / 6, 0.0)


def note(f, x, y, parts, size=14):
    """One line of (text, font, colour) runs, a space between them."""
    for text, font, colour in parts:
        box = f.text(x, y, text, size, font, colour)
        x = box[2] + size * 0.32
    return x


def three_cascades_added_up():
    # One stretch of sea, the same width in every strip, so the bottom strip is exactly the sum of the three above.
    stretch = 50.0  # metres across a strip
    waves = [[(33.0, 1.0, 0.0), (21.0, 0.32, 1.3)],     # wavelength (m), height, phase: two waves in each band
             [(4.9, 0.20, 0.4), (3.2, 0.10, 2.1)],
             [(0.93, 0.085, 0.9), (0.62, 0.04, 2.6)]]
    for cascade, members in enumerate(waves):
        for wavelength, _, _ in members:
            assert BOUNDS[cascade + 1] < wavelength <= BOUNDS[cascade], (cascade, wavelength)
    assert round(BOUNDS[1], 1) == 6.2 and round(BOUNDS[2], 1) == 1.2   # the chapter's 6.2 m and 1.2 m

    f = Figure("three-cascades-added-up", 880, 380,
               "Three cascades added up: cascade 0, 250 m, holds waves from 250 m to 6.2 m, the swell and the sea; "
               "cascade 1, 37 m, holds 6.2 m to 1.2 m, the chop on it; cascade 2, 7 m, holds 1.2 m and shorter, the "
               "ripples on that. Their sum is the sea.",
               kind="computed plot", source="30-A-Rougher-Sea.md, Where this is going",
               parameters={"stretchMetres": stretch, "wavesPerCascade": waves, "bandBoundsMetres": [round(b, 2) for b in BOUNDS[:3]]})
    left, right, half = 316, 856, 30
    scale = (right - left) / stretch
    unit_height = 20.0  # px per unit of the heights above: heights are not to scale between cascades

    def height(members, x):
        return sum(h * math.cos(2 * math.pi * x / w + p) for w, h, p in members)

    labels = [("cascade 0, 250 m", "waves 250 m to 6.2 m", "the swell and the sea"),
              ("cascade 1, 37 m", "waves 6.2 m to 1.2 m", "the chop on it"),
              ("cascade 2, 7 m", "waves 1.2 m and shorter", "the ripples on that"),
              ("the sea", "", "")]
    rows = [50, 132, 214, 304]
    for i, y in enumerate(rows):
        members = waves[i] if i < 3 else [w for c in waves for w in c]
        xs = [stretch * k / 1400 for k in range(1401)]
        curve = [(left + x * scale, y - height(members, x) * unit_height) for x in xs]
        assert max(abs(py - y) for _, py in curve) + 1.3 + 2 <= half + 4, i   # the curve and its stroke stay inside the strip
        f.rect(left, y - half - 4, right - left, 2 * half + 8, FILL if i < 3 else BLUE_FILL, radius=6)
        f.line([(left, y), (right, y)], LINE if i < 3 else BLUE, 1, "4 4")
        f.line(curve, BLUE, 2.2 if i < 3 else 2.6)
        name, band, role = labels[i]
        if band:
            f.text(24, y - 21, name, 15, "bold")
            f.text(24, y, band, 14)
            f.text(24, y + 21, role, 14, "italic", GRAY)
        else:
            f.text(24, y, name, 15, "bold")
        operator = "+" if 0 < i < 3 else ("=" if i == 3 else "")
        if operator:
            f.text(left - 26, (y + rows[i - 1]) / 2 + (6 if i == 3 else 0), operator, 22, "bold", GRAY, "middle")
    f.line([(left, (rows[2] + rows[3]) / 2 + 6), (right, (rows[2] + rows[3]) / 2 + 6)], LINE, 1.4)
    f.text(right, rows[3] + half + 24, "the same stretch of sea in every strip; heights not to scale", 13.5, "italic", GRAY, "end")
    return f


def one_frame_of_the_rougher_sea():
    f = Figure("one-frame-of-the-rougher-sea", 880, 612,
               "One frame of the rougher sea: settings feed the spectrum pass, which makes each cascade's h0, its "
               "band only, when a setting changes; animate, FFT and assemble are Chapter 29's passes, unchanged, run "
               "three times. New are the foam pass, which keeps the larger of the Jacobian's new foam and what is "
               "left of last frame's, and the surface, which adds up every cascade's displacement, slopes and foam.",
               source="30-A-Rougher-Sea.md, Where this is going")
    rows = [56, 160, 254, 348, 442, 552]
    spine_x, spine_w, h = 160, 240, 64
    spine_end, centre = spine_x + spine_w, spine_x + spine_w / 2
    notes_x = spine_end + 26

    node(f, 24, rows[0], 104, 52, "settings", kind="input")
    node(f, 24, rows[1], 104, 52, "time", kind="input")
    spine = [("spectrum x3", "sections 3, 5-7", "pass"),
             ("animate x3", "Chapter 29 section 8", "pass"),
             ("FFT x3", "Chapter 29 section 5", "pass"),
             ("assemble x3", "Chapter 29 section 9", "pass"),
             ("foam x3", "section 8", "pass"),
             ("surface", "section 4", "shader")]
    for y, (title, sub, kind) in zip(rows, spine):
        node(f, spine_x, y, spine_w, h, title, sub, kind)
    node(f, 444, rows[0], 196, h, "h0 per cascade", "its band only", "data")
    f.text(656, rows[0] - 10, "when a setting", 13.5, "italic", GRAY)
    f.text(656, rows[0] + 10, "changes", 13.5, "italic", GRAY)

    f.arrow([(128, rows[0]), (spine_x, rows[0])])
    f.arrow([(128, rows[1]), (spine_x, rows[1])])
    f.arrow([(spine_end, rows[0]), (444, rows[0])])
    f.arrow([(542, rows[0] + h / 2), (542, rows[1] - 12), (spine_end, rows[1] - 12)])
    for a, b in zip(rows[1:-1], rows[2:]):
        f.arrow([(centre, a + h / 2), (centre, b - h / 2)])

    # animate's row also carries the h0 arrow: the arrow takes the row's upper half, "unchanged" its lower half,
    # in the same column as FFT's and assemble's.
    f.text(notes_x, rows[1] + 12, "unchanged", 14, fill=GRAY)
    unchanged = [("unchanged:", "regular", GRAY)]
    note(f, notes_x, rows[2], unchanged + [("16 stages, three dispatches each", "regular", INK)])
    note(f, notes_x, rows[3], unchanged + [("displacement, normal, Jacobian", "regular", INK)])
    new = ("new:", "bold", TEAL)
    note(f, notes_x, rows[4] - 10, [new, ("the larger (max) of the Jacobian's foam", "regular", INK)])
    f.text(notes_x, rows[4] + 10, "and what is left of last frame's", 14)
    note(f, notes_x, rows[5] - 20, [new, ("every cascade's displacement, slopes,", "regular", INK)])
    f.text(notes_x, rows[5], "and foam, added up", 14)
    note(f, notes_x, rows[5] + 24, [("Part 4:", "bold", GRAY), ("the engine's sky and clouds, reflected", "regular", GRAY)])

    for y, kind, label in [(232 - 30, "pass", "compute pass"), (232, "data", "image data"), (232 + 30, "shader", "graphics shader")]:
        swatch(f, 700, y - 60, kind, label)
    return f


FIGURES = [three_cascades_added_up, one_frame_of_the_rougher_sea]
