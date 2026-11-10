"""Chapter 50, Screen-Space Ambient Occlusion: authored figures.

@author Gary Yang
@brief Figures for 50-Screen-Space-Ambient-Occlusion.md
@copyright (C) Gary 2026
"""
from figure_kit import *


def material_ao_in_scene_alpha():
    f = Figure("material-ao-in-scene-alpha", 800, 560,
               "The opt-in path, from the G-buffer output with emission in scene RGB and material AO in scene alpha, "
               "through preparing depth and the G-buffer once, raw then filtered AO, diffuse ambient with screen AO, "
               "emission and direct lights, haze applied once and scene alpha restored to one, to the sky, forward glows "
               "and post-processing. The four steps from diffuse ambient to the restore are one lighting dispatch, and "
               "material AO stays in scene alpha from the G-buffer output until that restore.",
               source="50-Screen-Space-Ambient-Occlusion.md, section 5 (Change The Ambient Evaluation Order)")
    x, w, top = 24, 504, 24
    centre = x + w / 2
    rows = [  # title, note, kind, height
        ("G-buffer output", "emission in scene RGB, material AO in scene alpha", "data", 56),
        ("prepare depth/G-buffer for sampling exactly once", "", "plain", 38),
        None,   # raw AO, then filtered AO, side by side
        ("compute diffuse ambient with screen AO", "preserve specular/material policy", "pass", 56),
        ("add emission and direct lights", "", "pass", 38),
        ("apply atmospheric/haze transport once", "", "pass", 38),
        ("restore scene alpha to one", "", "pass", 38),
        ("sky and forward glows, then renderer post-processing", "", "plain", 38),
    ]
    gap = 24
    ys, y = [], top
    for row in rows:
        h = 38 if row is None else row[3]
        ys.append((y + h / 2, h))
        y += h + gap
    f.height = round(y - gap + 24)

    ao_w = 150
    raw_x, filtered_x = centre - ao_w - 30, centre + 30
    for i, row in enumerate(rows):
        middle, h = ys[i]
        if row is None:
            node(f, raw_x, middle, ao_w, h, "raw AO", kind="data")
            node(f, filtered_x, middle, ao_w, h, "filtered AO", kind="data")
            f.arrow([(raw_x + ao_w, middle), (filtered_x, middle)])
            continue
        title, note, kind, _ = row
        node(f, x, middle, w, h, title, note, kind)

    for i in range(len(rows) - 1):
        (a, ha), (b, hb) = ys[i], ys[i + 1]
        # Into raw AO straight down from above it; out of filtered AO straight down from below it.
        column = raw_x + ao_w / 2 if rows[i + 1] is None else filtered_x + ao_w / 2 if rows[i] is None else centre
        f.arrow([(column, a + ha / 2), (column, b - hb / 2)])

    # The two private passes are the G-buffer variant, which writes the G-buffer output, and its lighting
    # dispatch: DeferredLighting.comp.glsl's one main() does the ambient, the emission and lights, the haze
    # and the alpha-one store, so its four steps get one bracket, as Chapter 49 marks its composite.
    rail, bracket = x + w + 16, x + w + 32
    label = bracket + 14
    first, restore = ys[0][0], ys[6][0]
    dispatch_top, dispatch_bottom = ys[3][0] - ys[3][1] / 2, ys[6][0] + ys[6][1] / 2
    f.line([(bracket - 6, dispatch_top), (bracket, dispatch_top),
            (bracket, dispatch_bottom), (bracket - 6, dispatch_bottom)], TEAL, 1.6)
    middle = (dispatch_top + dispatch_bottom) / 2
    f.text(label, middle - 10, "the lighting dispatch", 15, "bold", TEAL)
    f.text(label, middle + 12, "DeferredLighting.comp.glsl", 13, "mono", GRAY)

    # Material AO is data in scene alpha from the G-buffer output until the restore: a gold rail from the
    # one step to the other, inside the dispatch's bracket so the two never share a tick.
    f.line([(rail - 8, first), (rail, first), (rail, restore), (rail - 8, restore)], GOLD, 1.6)
    upper = (first + dispatch_top) / 2
    f.lines(label, upper - 26, ["material AO", "in scene alpha"], 15, "bold", GOLD_TEXT, spacing=21)
    f.lines(label, upper + 26, ["between the G-buffer variant", "and its lighting dispatch"], 13.5, "italic", GRAY,
            spacing=19)
    return f


FIGURES = [material_ao_in_scene_alpha]
