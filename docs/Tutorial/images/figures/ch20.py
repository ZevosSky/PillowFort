"""Chapter 20, Compute Fundamentals: authored figures.

@author Gary Yang
@brief Figures for 20-Compute-Fundamentals.md
@copyright (C) Gary 2026
"""
from figure_kit import *


def a_tile_at_the_grids_corner():
    # The chapter's numbers: a 300 x 170 grid, 8 x 8 workgroups, a 10 x 10 tile with a one-cell border.
    width_cells, height_cells, group, tile = 300, 170, 8, 10
    groups = ((width_cells + group - 1) // group, (height_cells + group - 1) // group)
    assert groups == (38, 22) and (groups[0] * group, groups[1] * group) == (304, 176)   # section 3's dispatch
    last = (groups[0] - 1, groups[1] - 1)
    corner = (last[0] * group - 1, last[1] * group - 1)                     # gl_WorkGroupID.xy * GROUP - 1
    assert corner == (295, 167) and corner[0] + tile - 1 == 304             # "cell.x ranges from -1 to 304"
    storing = sum(1 for r in range(1, 9) for c in range(1, 9)
                  if corner[0] + c < width_cells and corner[1] + r < height_cells)
    second_pass = tile * tile - group * group
    assert storing == 8 and second_pass == 36                               # "invocations 0-35 load two entries"

    f = Figure("a-tile-at-the-grids-corner", 880, 498,
               "The 10 by 10 tile of the workgroup in the dispatch's bottom-right corner, workgroup (37, 21), whose tile "
               "starts at cell (295, 167). Its 8 by 8 cells run from x 296 to 303 and y 168 to 175, but the grid ends at "
               "x 299 and y 169, so only 8 of its 64 invocations store; the rest load and reach barrier() without storing. "
               "The one-cell border is the halo, read only as neighbours. Each entry is numbered by its index in tile[]: "
               "invocations 0 to 63 load entries 0 to 63, then invocations 0 to 35 load entries 64 to 99. Coordinates "
               "past the edge read the wrapped cell: x 300 to 304 read columns 0 to 4, and y 170 to 176 read rows 0 to 6.",
               source="20-Compute-Fundamentals.md, section 6 (Shared memory and barrier()), worked solution",
               parameters={"grid": [width_cells, height_cells], "workgroup": group, "tile": tile,
                           "workgroupId": list(last), "tileCorner": list(corner), "storingInvocations": storing,
                           "secondPassEntries": second_pass})

    c = 34
    x0, y0 = 150, 84

    def cell_box(col, row):
        return x0 + col * c, y0 + row * c

    for row in range(tile):
        for col in range(tile):
            x, y = corner[0] + col, corner[1] + row
            halo = row in (0, tile - 1) or col in (0, tile - 1)
            inside = x < width_cells and y < height_cells
            fill = GOLD_FILL if halo else (BLUE_FILL if inside else WHITE)
            bx, by = cell_box(col, row)
            f.rect(bx, by, c, c, fill, HAIR, 1)
            index = row * tile + col
            second = index >= group * group
            f.text(bx + c / 2, by + c / 2, str(index), 12.5, "bold" if second else "regular",
                   TEAL if second else GRAY, "middle")

    # The workgroup's own 8 x 8 cells, and the whole tile.
    f.rect(x0 + c, y0 + c, group * c, group * c, "none", BLUE, 2.2)
    f.rect(x0, y0, tile * c, tile * c, "none", GOLD, 1.6)

    # Where the grid ends: after column 299 and after row 169.
    edge_x = x0 + (width_cells - corner[0]) * c
    edge_y = y0 + (height_cells - corner[1]) * c
    f.line([(edge_x, y0 - 6), (edge_x, y0 + tile * c + 6)], INK, 2.6)
    f.line([(x0 - 6, edge_y), (x0 + tile * c + 6, edge_y)], INK, 2.6)

    # Column and row numbers; past the edge, the cell each one actually reads.
    for col in range(tile):
        x = corner[0] + col
        cx = x0 + col * c + c / 2
        f.text(cx, y0 - 38, str(x), 13, fill=GRAY, anchor="middle")
        if x >= width_cells:
            f.text(cx, y0 - 19, f"→{x % width_cells}", 13, "bold", TEAL, "middle")
    for row in range(tile):
        y = corner[1] + row
        cy = y0 + row * c + c / 2
        f.text(x0 - 44, cy, str(y), 13, fill=GRAY, anchor="end")
        if y >= height_cells:
            f.text(x0 - 10, cy, f"→{y % height_cells}", 13, "bold", TEAL, "end")

    below = y0 + tile * c + 30
    f.text(x0 + tile * c / 2, below, "workgroup (37, 21): its tile starts at cell (295, 167)", 13.5, "italic", GRAY,
           "middle")

    # The legend, beside the tile.
    lx, tx = 536, 576

    def key(y, fill, stroke, lines):
        f.rect(lx, y - 11, 28, 22, fill, stroke, 1.4, 4)
        f.lines(tx, y, lines, 13.5, fill=INK, spacing=19)

    key(104, BLUE_FILL, BLUE, ["the workgroup's cells inside the grid:", "8 of its 64 invocations store"])
    key(170, WHITE, LINE, ["invocations past the grid: they load", "and reach barrier(), but never store"])
    key(236, GOLD_FILL, GOLD, ["the halo, read only as neighbours"])
    f.text(lx + 14, 288, "64", 12.5, "bold", TEAL, "middle")
    f.lines(tx, 288, ["an entry's index i in tile[]: invocations", "0-63 load 0-63, then invocations 0-35",
                      "load 64-99 (teal)"], 13.5, spacing=19)
    f.line([(lx, 372), (lx + 28, 372)], INK, 2.6)
    f.lines(tx, 372, ["the grid's edges: 300 columns, 170 rows"], 13.5)
    f.text(lx + 14, 418, "→0", 13, "bold", TEAL, "middle")
    f.lines(tx, 418, ["the cell a coordinate past the edge reads:", "(x + 300) % 300, (y + 170) % 170"], 13.5, spacing=19)
    return f


FIGURES = [a_tile_at_the_grids_corner]
