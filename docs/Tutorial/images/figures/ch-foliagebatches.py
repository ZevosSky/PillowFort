"""Foliage batches (support lesson): authored figures.

@author Gary Yang
@brief Figures for FoliageBatches.md (two-sizes-in-one-flower-batch replaces make-foliage-batches.py's foliage-batches.svg)
@copyright (C) Gary 2026
"""
from figure_kit import *

SPACE = 0.348 * 15 + 1.5   # DejaVu Sans Bold's space at 15 px, and a little for the mono side bearings


def mixed_title(f, centre, y, parts):
    """One bold line of sans and mono pieces, (text, font), centred on centre; a space between pieces."""
    sizes = [14 if font.startswith("mono") else 15 for _, font in parts]
    widths = [measure(text, size, font)[0] for (text, font), size in zip(parts, sizes)]
    x = centre - (sum(widths) + SPACE * (len(parts) - 1)) / 2
    for (text, font), size, w in zip(parts, sizes, widths):
        f.text(x, y, text, size, font)
        x += w + SPACE


def a_plant_from_cell_to_draw():
    f = Figure("a-plant-from-cell-to-draw", 860, 452,
               "One plant's route, from a stable world cell through its candidate, the habitat, reach, culling and LOD "
               "tests, and its (kind, LOD) instance region and counts, to the indirect command's firstInstance with "
               "instance-rate attributes and the shared local mesh transformed for each plant. The compute pass does the "
               "first four steps, the draw the last two.",
               source="FoliageBatches.md, section 2 (Trace two sizes through one batch)")
    steps = [  # title (plain, or sans and mono pieces), kind
        ("stable world cell", "input"),
        ("candidate root, kind, yaw and nominal size", "pass"),
        ("habitat/reach tests, scaled bound, camera culling and LOD", "pass"),
        ("one (kind, LOD) instance region + each part’s count", "data"),
        ([("indirect command’s", "bold"), ("firstInstance", "mono-bold"), ("+ instance-rate vertex attributes", "bold")], "data"),
        ("shared local mesh transformed separately for each plant", "shader"),
    ]
    x, w, h, pitch, top = 24, 604, 40, 62, 40
    ys = [top + i * pitch for i in range(len(steps))]
    for y, (title, kind) in zip(ys, steps):
        if isinstance(title, str):
            node(f, x, y, w, h, title, kind=kind)
        else:
            node(f, x, y, w, h, "", kind=kind)
            mixed_title(f, x + w / 2, y, title)
    for a, b in zip(ys, ys[1:]):
        f.arrow([(x + w / 2, a + h / 2), (x + w / 2, b - h / 2)])

    rail = x + w + 18
    for first, last, name, notes in [(0, 3, "the compute pass", ["writes the records through", "set 2, binding 1, and the", "counts through binding 2"]),
                                     (4, 5, "the draw", ["binds the same buffer", "as vertex binding 1"])]:
        upper, lower = ys[first] - h / 2, ys[last] + h / 2
        f.line([(rail - 6, upper), (rail, upper), (rail, lower), (rail - 6, lower)], TEAL, 1.6)
        middle = (upper + lower) / 2
        block = 22 + 19 * len(notes)
        f.text(rail + 14, middle - block / 2 + 8, name, 15, "bold", TEAL)
        f.lines(rail + 14, middle - block / 2 + 8 + 24, notes, 13.5, "italic", GRAY, spacing=19)
    f.height = round(ys[-1] + h / 2 + 24)
    return f


def flower(f, x, ground, size, label):
    """One schematic flower standing on the ground line at x, uniformly scaled about its root: the same local shape
    for every size, as the vertex shader places it."""
    top = ground - 120 * size
    f.line([(x, ground), (x, top)], GREEN, 3.2 * size)
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        f.circle(x + 13 * size * dx, top + 13 * size * dy, 10 * size, GOLD_SOFT, GOLD, 1.1)
    f.circle(x, top, 7.5 * size, GOLD, GOLD, 1)
    f.circle(x, ground, 3.2, INK)
    f.text(x, ground + 20, label, 15, "bold", anchor="middle")
    f.text(x, ground + 39, f"size {size:g}", 13.5, fill=GRAY, anchor="middle")


def two_sizes_in_one_flower_batch():
    f = Figure("two-sizes-in-one-flower-batch", 880, 404,
               "Two flowers, of sizes 0.8 and 1.2, drawn from one Flower LOD0 mesh stored once: its stem submesh "
               "(FlowerBark) and head submesh (FlowerHead) each have their own indirect command of two instances, both "
               "starting at firstInstance 12800, and both commands select the same two 32-byte records, which the "
               "generate pass wrote from world cells. The draw runs each command once per record: two stems and two "
               "heads make two flowers, the same local shape at two sizes.",
               source="FoliageBatches.md, section 3 (Keep identity when the buffer is rebuilt)",
               parameters={"instanceCount": 2, "firstInstance": 12800, "sizes": [0.8, 1.2], "recordBytes": 32})
    stem_y, head_y, records_y = 110, 168, 318

    # The mesh, stored once, and its two parts.
    f.rect(24, 28, 250, 172, FILL, LINE, 1.4, 12)
    f.text(149, 50, "Flower LOD0: one mesh", 15, "bold", anchor="middle")
    f.text(149, 70, "stored once in the renderer", 13, "italic", GRAY, anchor="middle")
    for y, part, material in [(stem_y, "stem submesh", "FlowerBark"), (head_y, "head submesh", "FlowerHead")]:
        f.rect(40, y - 23, 218, 46, WHITE, LINE, 1.3, 9)
        f.text(149, y - 9, part, 15, "bold", anchor="middle")
        f.text(149, y + 12, material, 13, "mono", GRAY, anchor="middle")

    # The two commands, one per part.
    cx, cw = 330, 272
    for y, name in [(stem_y, "stem command"), (head_y, "head command")]:
        node(f, cx, y, cw, 46, name, "draws 2 instances", kind="data")
        f.arrow([(258, y), (cx, y)])
    f.text(cx + cw / 2, 216, "firstInstance = 12800", 13.5, "mono", GOLD_TEXT, anchor="middle")
    f.text(cx + cw / 2, 235, "for both: Flower LOD0's region, 2 × 6400", 13, "italic", GRAY, anchor="middle")
    f.arrow([(cx + cw / 2, 248), (cx + cw / 2, records_y - 48)])
    f.text(cx + cw / 2 + 12, 259, "both select", 13, "italic", GRAY)

    # The records both commands read, and the pass that wrote them.
    f.rect(cx, records_y - 46, cw, 92, TEAL_FILL, TEAL, 1.4, 10)
    f.text(cx + cw / 2, records_y - 24, "the same two 32-byte records", 15, "bold", anchor="middle")
    f.text(cx + cw / 2, records_y + 2, "A: root A, size 0.8", 13.5, "mono", anchor="middle")
    f.text(cx + cw / 2, records_y + 24, "B: root B, size 1.2", 13.5, "mono", anchor="middle")
    node(f, 24, records_y, 250, 58, "the generate pass", "a world cell seeds root, size, yaw", kind="pass")
    f.arrow([(274, records_y), (cx, records_y)])

    # The draw: each command once per record.
    px, pw, top, bottom = 630, 226, 28, 380
    f.rect(px, top, pw, bottom - top, WHITE, LINE, 1.3, 12)
    f.text(px + pw / 2, 50, "the draw", 15, "bold", anchor="middle")
    f.text(px + pw / 2, 70, "each command, once per record", 13, "italic", GRAY, anchor="middle")
    for y in (stem_y, head_y, records_y):
        f.arrow([(cx + cw, y), (px, y)])
    ground = 300
    f.line([(px + 18, ground), (px + pw - 18, ground)], LINE, 1.2)
    flower(f, 690, ground, 0.8, "A")
    flower(f, 796, ground, 1.2, "B")
    f.text(px + pw / 2, 362, "2 stems + 2 heads = 2 flowers", 13, "italic", GRAY, anchor="middle")
    return f


FIGURES = [a_plant_from_cell_to_draw, two_sizes_in_one_flower_batch]
