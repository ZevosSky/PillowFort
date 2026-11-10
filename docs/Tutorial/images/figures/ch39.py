"""Chapter 39, Plants: authored figures.

@author Gary Yang
@brief Figures for 39-Plants.md
@copyright (C) Gary 2026
"""
from figure_kit import *

LEAF = GREEN
LEAF_FILL = "#cfe3d0"


def mix(a, b, t):
    """Two #rrggbb colours mixed, t of the second."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(p + (q - p) * t):02x}" for p, q in zip(ca, cb))


def grid_of(f, x, y, values, cell, numbers=False):
    """A square grid of alphas, leaf green at 1 and white at 0, with each alpha written in it if numbers."""
    n = len(values)
    for row in range(n):
        for col in range(n):
            a = values[row][col]
            f.rect(x + col * cell, y + row * cell, cell, cell, mix(WHITE, LEAF, a), LINE, 1)
            if numbers:
                f.text(x + (col + 0.5) * cell, y + (row + 0.5) * cell, f"{a:g}", 15, "bold",
                       WHITE if a > 0.6 else INK, "middle")
    f.rect(x, y, n * cell, n * cell, "none", INK, 1.4)


def averaging_loses_the_cut_share():
    cutoff = 0.5
    level = [[1, 1, 0, 0],
             [0, 0, 1, 0],
             [0, 1, 0, 0],
             [0, 0, 0, 1]]
    below = [[sum(level[2 * r + i][2 * c + j] for i in (0, 1) for j in (0, 1)) / 4 for c in (0, 1)] for r in (0, 1)]
    mean = lambda g: sum(map(sum, g)) / len(g) ** 2
    share = lambda g: sum(v >= cutoff for row in g for v in row) / len(g) ** 2
    # The section's own sentences: two leaf and two gap average to 0.5, which passes; one leaf and three gaps to
    # 0.25, which does not. Box mips keep the mean and lose the share at or above the cutoff.
    assert below == [[0.5, 0.25], [0.25, 0.25]], below
    assert mean(level) == mean(below) == 0.3125 and share(level) == 0.3125 and share(below) == 0.25

    f = Figure("averaging-loses-the-cut-share", 880, 372,
               "Five leaf texels in sixteen, and the next mip level down. Each of its texels is the average of four: "
               "two leaf and two gap make 0.5, which passes the cutoff, and one leaf and three gaps make 0.25, which "
               "does not. The mean alpha stays 0.3125 at both levels, while the share at or above 0.5 falls from "
               "0.3125 to 0.25, and that share is what the cutoff keeps.",
               kind="computed plot", source="39-Plants.md, section 6 (Measured)",
               parameters={"cutoff": cutoff, "texels": 16, "leafTexels": 5})
    top, size = 74, 176
    panels = [(40, "a level: leaf or gap", level, False),
              (352, "the next level: averages of 2 x 2", below, True),
              (664, "the next level, cut at 0.5", [[1 if v >= cutoff else 0 for v in row] for row in below], False)]
    for x, title, values, numbers in panels:
        f.text(x + size / 2, top - 26, title, 15, "bold", anchor="middle")
        grid_of(f, x, top, values, size / len(values), numbers)
    # The 2 x 2 blocks the averages come from, outlined on the first grid.
    for r in (0, 1):
        for c in (0, 1):
            f.rect(40 + c * size / 2 + 2, top + r * size / 2 + 2, size / 2 - 4, size / 2 - 4, "none", GOLD, 1.8, 4,
                   dash="5 3")
    f.arrow([(40 + size + 18, top + size / 2), (352 - 18, top + size / 2)])
    f.arrow([(352 + size + 18, top + size / 2), (664 - 18, top + size / 2)])

    rows = top + size + 34
    notes = [(40, ["mean alpha 0.3125", "at 0.5 or above: 5 of 16, 0.3125"]),
             (352, ["mean alpha 0.3125, kept", "at 0.5 or above: 1 of 4, 0.25"]),
             (664, ["what the test keeps:", "0.25 of the area, not 0.3125"])]
    for x, lines in notes:
        f.lines(x + size / 2, rows, lines, 13.5, fill=GRAY, anchor="middle", spacing=21)
    f.height = round(rows + 21 + 30)
    return f


FIGURES = [averaging_loses_the_cut_share]
