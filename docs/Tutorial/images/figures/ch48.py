"""Chapter 48, Grass in the Coastal Pipeline: authored figures.

@author Gary Yang
@brief Figures for 48-Grass-In-The-Coastal-Pipeline.md
@copyright (C) Gary 2026
"""
from pathlib import Path
import math
import re

from figure_kit import *

CHAPTER = Path(__file__).resolve().parents[2] / "48-Grass-In-The-Coastal-Pipeline.md"


def chapter_text():
    return " ".join(CHAPTER.read_text(encoding="utf-8").split())   # one line, so wrapped sentences match


def floor_div(value, divisor):
    """grassSourceFloorDiv, as the chapter prints it."""
    return value // divisor if value >= 0 else -1 - (-(value + 1)) // divisor


def remainder(value, divisor):
    """grassSourceRemainder, as the chapter prints it."""
    return value % divisor if value >= 0 else divisor - 1 - (-(value + 1)) % divisor


def quarter_turn(x, z, side):
    """The chapter's positive quarter-turn: (x, z) to (z, side - 1 - x)."""
    return z, side - 1 - x


def nested_source_and_negative_cells():
    text = chapter_text()
    assert "Compose nine actual 16-blade clumps into one patch, and sixteen patches into one parent" in text
    assert "maps `(x,z)` to `(z,side-1-x)`" in text
    examples = re.search(r"world cell `(-?\d+)` belongs to parent `(-?\d+)`, local cell `(\d+)`; cell `(-?\d+)` "
                         r"belongs to parent `(-?\d+)`, local cell `(\d+)`; cell `(-?\d+)` belongs to parent "
                         r"`(-?\d+)`, local cell `(\d+)`", text).groups()
    examples = [tuple(int(v) for v in examples[i:i + 3]) for i in (0, 3, 6)]
    parent_side, patch_side = 12, 3
    for cell, parent, local in examples:
        assert (floor_div(cell, parent_side), remainder(cell, parent_side)) == (parent, local), (cell, parent, local)
        assert parent * parent_side + local == cell
    assert examples == [(-1, -1, 11), (-12, -1, 0), (-13, -2, 11)], examples
    assert int(-1 / parent_side) == 0   # what truncation would say for cell -1

    f = Figure("nested-grass-source", 880, 560,
               "Above left, one parent: 12 by 12 fine clump cells in 16 patches of 3 by 3, one patch shaded. Above "
               "right, that patch's nine clumps as authored and after one positive quarter-turn, which moves the clump "
               "at (x, z) to (z, 2 - x). Below, world cells -13 to 0 along one axis with the parent and local cell "
               "that floor division gives each: cell -13 is parent -2, local 11; cells -12 to -1 are parent -1, local "
               "0 to 11; cell 0 is parent 0, local 0.",
               kind="computed plot", source="48-Grass-In-The-Coastal-Pipeline.md, section 7 (Author A Source You Can "
                                            "Aggregate)",
               parameters={"parentCells": parent_side, "patchCells": patch_side, "bladesPerClump": 16,
                           "examples": [list(e) for e in examples]})

    # One parent, its patches outlined, one patch shaded.
    cell, gx, gy = 17, 40, 60
    side = parent_side * cell
    shaded = (2, 1)   # patch column, patch row: an example, not a particular parent's layout
    f.text(24, 28, "one parent, seen from above", 13.5, "italic", GRAY)
    px, pz = gx + shaded[0] * patch_side * cell, gy + shaded[1] * patch_side * cell
    f.rect(px, pz, patch_side * cell, patch_side * cell, TEAL_FILL, "none")
    for i in range(parent_side + 1):
        f.line([(gx + i * cell, gy), (gx + i * cell, gy + side)], LINE, 0.8)
        f.line([(gx, gy + i * cell), (gx + side, gy + i * cell)], LINE, 0.8)
    for i in range(0, parent_side + 1, patch_side):
        f.line([(gx + i * cell, gy), (gx + i * cell, gy + side)], INK, 1.8)
        f.line([(gx, gy + i * cell), (gx + side, gy + i * cell)], INK, 1.8)
    f.rect(px, pz, patch_side * cell, patch_side * cell, "none", TEAL, 2.4)
    f.arrow([(gx, gy + side + 18), (gx + 46, gy + side + 18)], GRAY, 1.5, 8)
    f.text(gx + 52, gy + side + 18, "x", 14, "italic", GRAY)
    f.arrow([(gx - 18, gy), (gx - 18, gy + 46)], GRAY, 1.5, 8)
    f.text(gx - 18, gy + 60, "z", 14, "italic", GRAY, "middle")

    nx = gx + side + 26
    f.lines(nx, gy + 22, ["a parent: 12 × 12 fine cells,", "16 patches of 3 × 3"], 15, spacing=21)
    f.lines(nx, gy + 82, ["a patch: 9 clumps"], 15, fill=TEAL)
    f.lines(nx, gy + 120, ["a clump: 16 blades"], 15)
    f.lines(nx, gy + 164, ["at Horizon’s density a patch", "is 2 m wide and a parent 8 m"], 13.5, "italic", GRAY,
            spacing=19)

    # The shaded patch, as authored and after a quarter-turn; each clump keeps its number.
    small, ax, ay = 34, 520, 78
    turned_x = ax + patch_side * small + 96

    def patch(x0, y0, at):
        f.rect(x0, y0, patch_side * small, patch_side * small, TEAL_FILL, TEAL, 2)
        for z in range(patch_side):
            for x in range(patch_side):
                child = at[(x, z)]
                f.rect(x0 + x * small, y0 + z * small, small, small, GOLD_FILL if child == 0 else "none", LINE, 1)
                f.text(x0 + (x + 0.5) * small, y0 + (z + 0.5) * small, str(child), 15, "bold",
                       GOLD_TEXT if child == 0 else INK, "middle")

    authored = {(x, z): x + patch_side * z for z in range(patch_side) for x in range(patch_side)}
    turned = {quarter_turn(x, z, patch_side): child for (x, z), child in authored.items()}
    assert turned[(0, 2)] == 0 and turned[(0, 0)] == 2   # the first clump goes to (0, 2), clump 2 to (0, 0)
    patch(ax, ay, authored)
    patch(turned_x, ay, turned)
    f.text(ax + patch_side * small / 2, ay - 22, "the shaded patch", 15, "bold", TEAL, "middle")
    f.text(turned_x + patch_side * small / 2, ay - 22, "after a quarter-turn", 15, "bold", anchor="middle")
    f.arrow([(ax + patch_side * small + 14, ay + 1.5 * small), (turned_x - 14, ay + 1.5 * small)], TEAL, 2)
    f.text((ax + turned_x + patch_side * small) / 2, ay + patch_side * small + 26, "(x, z) → (z, 2 − x)", 15,
           "mono", anchor="middle")
    f.lines(ax - 6, ay + patch_side * small + 62,
            ["The lookup undoes it: find the parent and", "undo its turn, then the patch and its turn,",
             "and only then pick the clump."], 13.5, "italic", GRAY, spacing=19)

    # World cells -13 to 0 along x, with floor division's parent and local cell.
    top = 340
    f.line([(24, top - 26), (856, top - 26)], HAIR, 1.2)
    f.text(24, top, "world cells along x, and what floor division by 12 makes of them", 13.5, "italic", GRAY)
    cells = list(range(-13, 1))
    w, x0, row = 52, 112, top + 50
    f.text(x0 - 14, row, "cell", 14, "bold", anchor="end")
    f.text(x0 - 14, row + 40, "local", 14, "bold", GOLD_TEXT, "end")
    examples_cells = {e[0] for e in examples} | {0}
    for i, c in enumerate(cells):
        x = x0 + i * w
        named = c in examples_cells
        f.rect(x + 2, row - 16, w - 4, 32, TEAL_FILL if named else FILL, TEAL if named else LINE, 1.3, 5)
        f.text(x + w / 2, row, str(c).replace("-", "−"), 15, "bold", TEAL if named else INK, "middle")
        f.text(x + w / 2, row + 40, str(remainder(c, parent_side)), 15, "bold", GOLD_TEXT, "middle")
    brace_y = row + 72

    def brace(first, last, label, open_left=False, open_right=False):
        left = x0 + cells.index(first) * w + 4
        right = x0 + (cells.index(last) + 1) * w - 4
        f.line([(left, brace_y - 7), (left, brace_y), (right, brace_y), (right, brace_y - 7)], BLUE, 1.6)
        if open_left:
            f.line([(left - 34, brace_y), (left, brace_y)], BLUE, 1.6, "4 4")
        if open_right:
            f.line([(right, brace_y), (right + 34, brace_y)], BLUE, 1.6, "4 4")
        f.text((left + right) / 2, brace_y + 20, label, 14, "bold", BLUE, "middle")

    brace(-13, -13, "parent −2", open_left=True)
    brace(-12, -1, "parent −1: −12 + local")
    brace(0, 0, "parent 0", open_right=True)
    f.text(24, brace_y + 54, "Truncation toward zero would put cell −1 in parent 0, at local cell −1, outside 0 to 11.",
           13.5, "italic", GRAY)
    f.height = round(brace_y + 78)
    return f


def rounded_blade_face_and_edge():
    text = chapter_text()
    assert "Write the unfiltered rounded normal as `R = normalize(F + E)`" in text
    assert "Its physical normal is `normalize(-F + E)`, not `-R`" in text
    edge = 0.6   # an example rounding: |E| = 0.6 |F|, so R leans 31 degrees toward the edge
    lean = math.degrees(math.atan(edge))

    f = Figure("rounded-blade-face-and-edge", 880, 360,
               "A blade's cross-section, twice. Left, the eye on the captured side: the face normal F, the edge offset "
               "E along the blade's width, and the rounded normal R = normalize(F + E) leaning toward the edge. Right, "
               "the eye on the other side: the physical normal is normalize(-F + E), which is R reflected across the "
               "blade's plane, with the same lean toward the edge; -R would also reverse the rounding.",
               kind="computed plot", source="48-Grass-In-The-Coastal-Pipeline.md, section 10 (Attempt "
                                            "CH48-capture-facing)",
               parameters={"edgeOverFace": edge, "leanDegrees": round(lean, 1)})
    length = 92

    def vector(p, d, name, color, dash=None, size=17):
        tip = (p[0] + d[0] * length, p[1] + d[1] * length)
        f.arrow([p, tip], color, 2.2, 12, dash)
        return tip

    def blade(cx, cy, below=False):
        """The cross-section: a thin blade, its shading normals fanning out toward both edges."""
        f.add(f'<path d="M{number(cx - 150)} {number(cy)} Q{number(cx)} {number(cy - 7)} {number(cx + 150)} {number(cy)} '
              f'Q{number(cx)} {number(cy + 7)} {number(cx - 150)} {number(cy)} Z" fill="{GREEN}" opacity="0.25" '
              f'stroke="{GREEN}" stroke-width="1.6"/>')
        for k in (-2, -1, 0, 1, 2):
            a = math.radians(k * 14)
            x = cx + k * 52
            s = 1 if below else -1   # the side the eye sees: down the page when it is below the blade
            f.line([(x, cy + 4 * s), (x + math.sin(a) * 24, cy + s * (4 + math.cos(a) * 24))], GREEN, 1.2)

    def side(cx, eye_above):
        cy = 196
        blade(cx, cy, not eye_above)
        p = (cx + 64, cy - 4 if eye_above else cy + 4)
        up = -1 if eye_above else 1   # SVG y grows downward
        e = (edge, 0)
        if eye_above:
            f_tip = vector(p, (0, -1), "F", BLUE)
            e_tip = vector(p, e, "E", GOLD)
            norm = math.hypot(1, edge)
            r = (edge / norm, -1 / norm)
            f.line([f_tip, (f_tip[0] + edge * length, f_tip[1])], LINE, 1.2, "4 4")
            f.line([e_tip, (e_tip[0], e_tip[1] - length)], LINE, 1.2, "4 4")
            r_tip = vector(p, r, "R", TEAL)
            f.text(f_tip[0] - 14, f_tip[1] + 6, "F", 18, "vector", BLUE, "end")
            f.text(e_tip[0] + 6, e_tip[1] + 20, "E", 18, "vector", GOLD_TEXT)
            f.text(r_tip[0] + 10, r_tip[1] - 4, "R", 18, "vector", TEAL)
            eye = (cx - 110, 64)
        else:
            norm = math.hypot(1, edge)
            r_up = (edge / norm, -1 / norm)
            # R as captured, faint, and its mirror image across the blade's plane.
            r_tip = (p[0] + r_up[0] * length, p[1] + r_up[1] * length)
            f.line([p, r_tip], TEAL, 1.6, "3 4")
            f.text(r_tip[0] + 10, r_tip[1] - 4, "R", 18, "vector", LINE)
            f.line([(cx - 160, p[1]), (cx + 170, p[1])], LINE, 1.1, "6 5")
            f_tip = vector(p, (0, 1), "−F", BLUE)
            e_tip = vector(p, (edge, 0), "E", GOLD)
            m_tip = vector(p, (edge / norm, 1 / norm), "", TEAL)
            n_tip = vector(p, (-edge / norm, 1 / norm), "", RED, "6 4")
            f.text(f_tip[0] - 12, f_tip[1] + 4, "−F", 18, "vector", BLUE, "end")
            f.text(e_tip[0] + 6, e_tip[1] - 16, "E", 18, "vector", GOLD_TEXT)
            f.text(m_tip[0] + 8, m_tip[1] + 4, "normalize(−F + E)", 13, "mono", TEAL)
            f.text(n_tip[0] - 10, n_tip[1] + 6, "−R", 18, "vector", RED, "end")
            eye = (cx - 110, 328)
        # The eye, and the ray toward it.
        f.add(f'<path d="M{number(eye[0] - 16)} {number(eye[1])} Q{number(eye[0])} {number(eye[1] - 11)} '
              f'{number(eye[0] + 16)} {number(eye[1])} Q{number(eye[0])} {number(eye[1] + 11)} {number(eye[0] - 16)} '
              f'{number(eye[1])} Z" fill="{WHITE}" stroke="{BLUE}" stroke-width="1.8"/>')
        f.circle(eye[0], eye[1], 4.5, BLUE)
        f.line([(eye[0] + 18 * (p[0] - eye[0]) / math.hypot(p[0] - eye[0], p[1] - eye[1]),
                 eye[1] + 18 * (p[1] - eye[1]) / math.hypot(p[0] - eye[0], p[1] - eye[1])), p], LINE, 1.2, "2 5")
        f.text(eye[0] - 24, eye[1], "eye", 14, "bold", BLUE, "end")

    left, right = 230, 610
    f.text(24, 28, "a blade cut across its width; green: its rounded shading normals", 13.5, "italic", GRAY)
    side(left, True)
    side(right, False)
    f.lines(left - 190, 268, ["dot(F, ray) > 0: keep", "R = normalize(F + E)"], 14, "mono", spacing=20)
    f.lines(470, 56, ["dot(F, ray) < 0: reflect R", "across the blade’s plane:", "R − 2 (R·F) F"], 14, "mono",
            spacing=20)
    f.lines(470, 132, ["−R would turn the", "rounding round too"], 13.5, "italic", RED, spacing=19)
    f.line([(445, 50), (445, 340)], HAIR, 1.2)
    return f


FIGURES = [nested_source_and_negative_cells, rounded_blade_face_and_edge]
