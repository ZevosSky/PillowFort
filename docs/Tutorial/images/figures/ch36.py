"""Chapter 36, Terrain to the Horizon: authored figures.

@author Gary Yang
@brief Figures for 36-Terrain-To-The-Horizon.md
@copyright (C) Gary 2026
"""
from pathlib import Path
import re

from figure_kit import *

CHAPTER = Path(__file__).resolve().parents[2] / "36-Terrain-To-The-Horizon.md"
RED_FILL = "#f6dcd6"


def full_preset():
    """The Full preset's cells per side and finest cell, the ring count and the skirt's reach, from the chapter."""
    text = CHAPTER.read_text(encoding="utf-8")
    cells, finest = re.search(r'\{ "Full", (\d+), ([\d.]+)f \}', text).groups()
    rings = int(re.search(r"TERRAIN_RINGS = (\d+);", text).group(1))
    skirt = float(re.search(r"const float SKIRT_DISTANCE = ([\d.]+);", text).group(1))
    return int(cells), float(finest), rings, skirt


def grid(f, x, y, cells, size, stroke, hole=None):
    """A square grid of cells, leaving out the block the ring inside covers (hole: first and last cell index)."""
    for i in range(cells):
        for j in range(cells):
            if hole and hole[0] <= i < hole[1] and hole[0] <= j < hole[1]:
                continue
            f.rect(x + i * size, y + j * size, size, size, "none", stroke, 0.9, opacity=0.5)


def label_on(f, x, y, string, fill, ink, size=15):
    """A label with a patch of its ring's colour behind it, so the grid lines do not run through the words."""
    w, h = measure(string, size, "bold")
    f.rect(x - w / 2 - 6, y - h / 2 - 5, w + 12, h + 10, fill, "none", radius=4)
    f.text(x, y, string, size, "bold", ink, "middle")


def rings_around_the_camera():
    cells, finest, rings, _ = full_preset()
    assert (cells, finest, rings) == (128, 0.5, 12), (cells, finest, rings)
    drawn = 8   # cells a side on the page; the inner ring covers the middle half, as it does at 128

    f = Figure("rings-around-the-camera", 660, 384,
               "The ground's rings seen from above: ring 0 around the camera, ring 1 around it, ring 2 around that. Each is "
               "the same grid, twice the size of the ring inside it.",
               source="36-Terrain-To-The-Horizon.md, section 2 (Each ring twice the size)",
               parameters={"cellsPerSide": cells, "cellsDrawn": drawn, "finestCellMetres": finest})
    outer, x0, y0 = 336, 24, 24
    centre = (x0 + outer / 2, y0 + outer / 2)
    looks = [(TEAL_FILL, TEAL, TEAL), (BLUE_FILL, BLUE, BLUE), (FILL, LINE, GRAY)]   # ring 0, 1, 2
    for level in (2, 1, 0):
        side = outer / 2 ** (2 - level)
        left, top = centre[0] - side / 2, centre[1] - side / 2
        fill, stroke, _ = looks[level]
        f.rect(left, top, side, side, fill, "none")
        grid(f, left, top, drawn, side / drawn, stroke, None if level == 0 else (drawn // 4, 3 * drawn // 4))
        f.rect(left, top, side, side, "none", stroke, 1.8)
    for level in (2, 1):
        side = outer / 2 ** (2 - level)
        fill, _, ink = looks[level]
        label_on(f, centre[0], centre[1] - side / 2 + side / drawn, f"ring {level}", fill, ink)
    label_on(f, centre[0], centre[1] - 22, "ring 0", TEAL_FILL, TEAL)
    f.circle(centre[0], centre[1], 6, INK, WHITE, 2)

    nx = x0 + outer + 36
    f.circle(nx + 6, 120, 6, INK, WHITE, 2)
    f.text(nx + 22, 120, "the camera", 15)
    f.lines(nx, 170, ["the same grid, three times,", "each twice the size"], 15)
    f.lines(nx, 246, ["seen from above; drawn with", f"{drawn} cells a side, where each", f"ring has {cells}"],
            13.5, "italic", GRAY)
    return f


def where_two_rings_meet():
    f = Figure("where-two-rings-meet", 800, 262,
               "From above, the edge where ring L, with fine cells, meets ring L + 1, whose cells are twice as big: every "
               "other vertex of ring L is a vertex of ring L + 1, and the ones between lie halfway along one of its cell "
               "edges.",
               source="36-Terrain-To-The-Horizon.md, section 2 (Each ring on its neighbour's vertices)")
    fine, gx, top = 50, 176, 30
    coarse = 2 * fine
    edge = top + coarse
    for i in range(3):
        f.rect(gx + i * coarse, top, coarse, coarse, BLUE_FILL, BLUE, 1.6)
    for i in range(6):
        for j in range(2):
            f.rect(gx + i * fine, edge + j * fine, fine, fine, TEAL_FILL, TEAL, 1.4)
    f.line([(gx, edge), (gx + 3 * coarse, edge)], BLUE, 2)

    f.text(gx - 20, top + coarse / 2 - 10, "ring L + 1", 15, "bold", BLUE, "end")
    f.text(gx - 20, top + coarse / 2 + 10, "(coarse)", 14, fill=GRAY, anchor="end")
    f.text(gx - 20, edge + fine - 10, "ring L", 15, "bold", TEAL, "end")
    f.text(gx - 20, edge + fine + 10, "(fine)", 14, fill=GRAY, anchor="end")

    def shared(x, y):
        f.circle(x, y, 6, INK, WHITE, 2)

    def between(x, y):
        f.circle(x, y, 6, WHITE, TEAL, 2.4)

    for k in range(7):
        (shared if k % 2 == 0 else between)(gx + k * fine, edge)

    f.text(24, 28, "seen from above", 13.5, "italic", GRAY)   # top left, as in the other figures
    lx = gx + 3 * coarse + 44
    shared(lx + 6, 84)
    f.lines(lx + 24, 84, ["every other vertex of ring L:", "a vertex of ring L + 1 too"], 15)
    between(lx + 6, 166)
    f.lines(lx + 24, 166, ["the ones between: halfway", "along one of ring L + 1’s", "cell edges"], 15)
    return f


def a_crack_between_rings():
    f = Figure("a-crack-between-rings", 800, 240,
               "The border between two rings seen from the side: the coarse ring's edge runs straight from one shared vertex "
               "to the next, the fine ring's vertex between them is at the true height above it, and the gap between the "
               "two is a crack.",
               source="36-Terrain-To-The-Horizon.md, section 5 (Cracks)")
    base, left, right, peak = 172, 190, 430, (310, 86)
    f.text(24, 28, "seen from the side", 13.5, "italic", GRAY)

    f.polygon([(left, base), peak, (right, base)], RED_FILL)
    f.line([(40, base), (548, base)], BLUE, 2.6)
    f.line([(left, base), peak, (right, base)], TEAL, 2.6)
    f.text(310, 150, "the gap: a crack", 14, "bold", RED, "middle")

    f.circle(peak[0], peak[1], 6.5, WHITE, TEAL, 2.4)
    f.text(peak[0], peak[1] - 26, "fine vertex at the true height", 15, anchor="middle")
    f.text(left + 30, 108, "the fine ring’s edge", 14, fill=TEAL, anchor="end")
    for x in (left, right):
        f.circle(x, base, 6.5, INK, WHITE, 2)
        f.text(x, base + 28, "shared vertex", 14, fill=GRAY, anchor="middle")
    f.lines(560, base - 10, ["the coarse ring’s edge,", "straight"], 15, fill=BLUE)
    return f


def the_skirt_from_the_side():
    cells, finest, rings, skirt = full_preset()
    reach = cells / 2 * finest * 2 ** (rings - 1)   # the last ring's half side: 64 of its cells
    assert reach == 65536 and skirt == 150000, (reach, skirt)
    reach_km = int(reach // 1000)   # the chapter's "65 km": 65,536 m, cut, not rounded

    f = Figure("the-skirt-from-the-side", 880, 262,
               "Seen from the side: the sea runs out from under the eye to 65 km, where the rings end. From there the skirt, "
               "one row of long triangles, climbs to a point 150 km out at the eye's height, which is on the horizon, "
               "where the eye's level line of sight meets it.",
               source="36-Terrain-To-The-Horizon.md, section 11 (The skirt)",
               parameters={"ringsReachMetres": reach, "skirtDistanceMetres": skirt,
                           "horizontal": "to scale", "vertical": "not to scale"})
    x0, x1 = 118, 830
    eye_y, sea_y = 92, 196

    def px(metres):
        return x0 + (x1 - x0) * metres / skirt

    ring_end = px(reach)
    f.text(24, 28, "seen from the side; distances to scale, heights not", 13.5, "italic", GRAY)

    f.rect(x0 - 50, sea_y, ring_end - x0 + 50, 12, BLUE_FILL, "none")
    f.line([(x0 - 50, sea_y), (ring_end, sea_y)], BLUE, 2.6)
    f.text(x0 - 62, sea_y + 2, "sea", 15, "bold", BLUE, "end")

    f.line([(x0 + 30, eye_y), (x1, eye_y)], LINE, 1.6, "2 6")
    f.add(f'<path d="M{number(x0 - 24)} {number(eye_y)} Q{number(x0)} {number(eye_y - 25)} {number(x0 + 24)} {number(eye_y)} '
          f'Q{number(x0)} {number(eye_y + 25)} {number(x0 - 24)} {number(eye_y)} Z" fill="{WHITE}" stroke="{BLUE}" '
          f'stroke-width="2" stroke-linejoin="round"/>')
    f.circle(x0, eye_y, 7.5, BLUE)
    f.text(x0 - 36, eye_y, "eye", 15, "bold", BLUE, "end")

    f.line([(ring_end, sea_y), (x1, eye_y)], TEAL, 3)
    f.circle(ring_end, sea_y, 6, INK, WHITE, 2)
    f.circle(x1, eye_y, 6, INK, WHITE, 2)
    f.text(ring_end, sea_y + 32, f"{reach_km} km, where the rings end", 15, anchor="middle")
    f.text(856, eye_y - 44, f"{skirt / 1000:.0f} km out, at the eye’s height", 15, anchor="end")
    f.text(856, eye_y - 24, "(on the horizon)", 14, fill=GRAY, anchor="end")

    # The skirt's label sits below its line, where it climbs.
    lx = 600
    f.lines(lx, 176, ["the skirt: one row", "of long triangles"], 15, fill=TEAL)
    return f


FIGURES = [rings_around_the_camera, where_two_rings_meet, a_crack_between_rings, the_skirt_from_the_side]
