"""Chapter 12, The Scene Graph: authored figures.

@author Gary Yang
@brief Figures for 12-Scene-Graph.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def box_around_a_turned_box():
    half = (2.0, 1.0)
    turn = math.radians(45)
    axes = [(math.cos(turn), math.sin(turn)), (-math.sin(turn), math.cos(turn))]  # the matrix's axis columns
    reach = [abs(axes[0][i]) * half[0] + abs(axes[1][i]) * half[1] for i in range(2)]  # transformBounds
    corners = [(sx * half[0] * axes[0][0] + sy * half[1] * axes[1][0], sx * half[0] * axes[0][1] + sy * half[1] * axes[1][1])
               for sx, sy in [(1, 1), (-1, 1), (-1, -1), (1, -1)]]
    # The chapter's numbers: axis columns (0.707, 0.707) and (-0.707, 0.707), a reach of 2.12 on X and Y, a 4.24 box.
    assert [tuple(round(c, 3) for c in a) for a in axes] == [(0.707, 0.707), (-0.707, 0.707)]
    assert round(reach[0], 2) == 2.12 and round(reach[1], 2) == 2.12 and round(2 * reach[0], 2) == 4.24
    # It is the exact box: the turned box's corners touch all four of its sides.
    assert abs(max(c[0] for c in corners) - reach[0]) < 1e-12 and abs(max(c[1] for c in corners) - reach[1]) < 1e-12

    # The key sits 69 px right of the drawing; the card ends as far right of the widest line, the formula under the
    # bar, as the drawing starts from the left edge.
    s, cx, cy = 58, 168, 154
    left = cx - s * reach[0]
    key_x = round(cx + s * reach[0] + 69)
    formula = "reach along X: |0.707|·2 + |−0.707|·1 = 2.12"
    f = Figure("box-around-a-turned-box", round(key_x + measure(formula)[0] + left), 340,
               "A box 4 by 2, turned 45 degrees about Z, inside the axis-aligned box around it, 4.24 square. Its half-axes, "
               "(0.707, 0.707) times 2 and (-0.707, 0.707) times 1, reach 1.41 and 0.71 along X: 2.12 in all.",
               kind="computed plot", source="12-Scene-Graph.md, section 2 (transformBounds)",
               parameters={"halfSize": list(half), "turnDegrees": 45, "reach": round(reach[0], 4)})

    def at(x, y):
        return (cx + s * x, cy - s * y)

    f.rect(cx - s * reach[0], cy - s * reach[1], 2 * s * reach[0], 2 * s * reach[1], BLUE_FILL, BLUE, 1.6, 0, "7 5")
    f.polygon([at(*c) for c in corners], GOLD_FILL, GOLD, 1.6)
    tips = [at(axes[0][0] * half[0], axes[0][1] * half[0]), at(axes[1][0] * half[1], axes[1][1] * half[1])]
    f.line([(tips[0][0], tips[0][1] + 6), (tips[0][0], 296)], LINE, 1.1, "3 4")
    f.line([(cx, cy + 8), (cx, 296)], LINE, 1.1, "3 4")
    f.arrow([at(0, 0), tips[0]], INK, 2.4, 13)
    f.arrow([at(0, 0), tips[1]], TEAL, 2.4, 13)
    f.circle(cx, cy, 4.5, INK, WHITE, 1.4)

    # How far the half-axes reach along X: one segment from each, made positive.
    y = 296
    right = cx + s * reach[0]
    for a, b, color, ink, label in [(cx, tips[0][0], INK, INK, "1.41"), (tips[0][0], right, TEAL, TEAL, "0.71")]:
        f.line([(a, y), (b, y)], color, 2.6)
        f.text((a + b) / 2, y + 18, label, 13.5, "bold", ink, "middle")
    for x in (cx, tips[0][0], right):
        f.line([(x, y - 6), (x, y + 6)], GRAY, 1.3)

    x = key_x
    swatch = [(x + 15 + (sx * 13 * axes[0][0] + sy * 6.5 * axes[1][0]), 54 - (sx * 13 * axes[0][1] + sy * 6.5 * axes[1][1]))
              for sx, sy in [(1, 1), (-1, 1), (-1, -1), (1, -1)]]
    f.polygon(swatch, GOLD_FILL, GOLD, 1.4)  # the same box, small
    f.text(x + 44, 46, "a box of half-size (2, 1), 4 by 2,", 15)
    f.text(x + 44, 66, "turned 45° about Z", 15)
    f.rect(x, 97, 30, 26, BLUE_FILL, BLUE, 1.4, 0, "5 4")
    f.text(x + 44, 102, "the axis-aligned box around it,", 15)
    f.text(x + 44, 122, "4.24 square", 15)
    for y, color, label in [(166, INK, "2 · (0.707, 0.707)"), (196, TEAL, "1 · (−0.707, 0.707)")]:
        f.arrow([(x, y + 8), (x + 28, y - 8)], color, 2.4, 10)
        f.text(x + 44, y, label, 15)
    f.text(x + 44, 224, "its half-axes: the axis columns,", 13.5, "italic", GRAY)
    f.text(x + 44, 242, "scaled by the half-size", 13.5, "italic", GRAY)
    f.text(x, 296, formula, 15)  # the bar's label: the total is its last number
    return f


def shear_from_an_uneven_parent():
    turn = math.radians(45)
    x_axis, y_axis = (math.cos(turn), math.sin(turn)), (-math.sin(turn), math.cos(turn))
    stretched = [(2 * a[0], a[1]) for a in (x_axis, y_axis)]  # the parent's scale of 2 along X

    def apart(a, b):
        return math.degrees(math.acos((a[0] * b[0] + a[1] * b[1]) / (math.hypot(*a) * math.hypot(*b))))

    assert round(apart(x_axis, y_axis)) == 90 and round(apart(*stretched)) == 127  # the chapter's 90 and 127 degrees

    f = Figure("shear-from-an-uneven-parent", 800, 256,
               "On the left, a child's x and y axes turned 45 degrees, 90 degrees apart. On the right, the same axes after the "
               "parent's scale of 2 along X: stretched sideways and 127 degrees apart, no longer perpendicular.",
               kind="computed plot", source="12-Scene-Graph.md, section 5 (transformFromMatrix, shear)",
               parameters={"turnDegrees": 45, "parentScale": [2, 1, 1], "anglesApart": [round(apart(x_axis, y_axis), 2),
                                                                                         round(apart(*stretched), 2)]})
    unit_px = 92

    def axes(ox, oy, pair, colour_fill):
        (ax, ay), (bx, by) = pair
        a, b = (ox + ax * unit_px, oy - ay * unit_px), (ox + bx * unit_px, oy - by * unit_px)
        f.polygon([(ox, oy), a, (a[0] + bx * unit_px, a[1] - by * unit_px), b], colour_fill, "none")
        f.arrow([(ox, oy), a], BLUE, 2.6, 14)
        f.arrow([(ox, oy), b], GOLD, 2.6, 14)
        for (dx, dy), tip, name, ink in [((ax, ay), a, "x", BLUE), ((bx, by), b, "y", GOLD_TEXT)]:
            size = math.hypot(dx, dy)
            f.text(tip[0] + dx / size * 18, tip[1] - dy / size * 18, name, 20, "vector", ink, "middle")
        start, end = (math.degrees(math.atan2(v[1], v[0])) for v in pair)
        f.arc(ox, oy, 34, start, end, TEAL, 1.5)
        f.circle(ox, oy, 4.5, INK, WHITE, 1.4)
        return start, end

    ox, oy = 172, 208
    start, end = axes(ox, oy, (x_axis, y_axis), FILL)
    f.text(ox, oy - 52, "90°", 15, "bold", TEAL, "middle")
    f.text(ox, 32, "the child's axes, turned 45°: 90° apart", 15, fill=GRAY, anchor="middle")

    f.arrow([(332, 138), (392, 138)], LINE, 2, 12)

    ox = 586
    axes(ox, oy, stretched, FILL)
    f.text(ox, oy - 52, "127°", 15, "bold", TEAL, "middle")
    f.text(ox, 32, "after the parent's scale of 2 along X: 127° apart", 15, fill=GRAY, anchor="middle")
    return f


def a_plane_as_four_numbers():
    plane = (1, 0, 0, -2)

    def side(x):
        return plane[0] * x + plane[3]

    assert side(1) == -1 and side(3) == 1 and side(2) == 0  # the chapter's two points, and the wall x = 2

    f = Figure("a-plane-as-four-numbers", 720, 262,
               "The plane (1, 0, 0, -2) is the wall x = 2, facing +X along its normal (1, 0, 0). The point (1, 0, 0) gives "
               "1·1 - 2 = -1, behind it; the point (3, 0, 0) gives 1·3 - 2 = 1, in front of it.",
               kind="computed plot", source="12-Scene-Graph.md, section 9 (A plane as four numbers)",
               parameters={"plane": list(plane)})
    s, x0, axis_y = 140, 80, 152

    def px(x):
        return x0 + s * x

    wall = px(2)
    f.rect(wall, 58, px(3.95) - wall, 150, TEAL_FILL, "none")
    f.rect(px(0.05), 58, wall - px(0.05), 150, FILL, "none")
    f.text((px(0.05) + wall) / 2, 38, "behind (< 0)", 15, "bold", GRAY, "middle")
    f.text((wall + px(3.95)) / 2, 38, "in front (≥ 0)", 15, "bold", TEAL, "middle")

    f.arrow([(px(0.05), axis_y), (px(4.05), axis_y)], LINE, 1.4, 10)
    f.text(px(4.05) + 10, axis_y, "x", 15, "italic", GRAY)

    f.line([(wall, 52), (wall, 214)], INK, 3)
    f.text(wall, 236, "x = 2", 15, "bold", anchor="middle")
    f.arrow([(wall, 82), (wall + 104, 82)], TEAL, 2.6, 14)
    f.text(wall + 116, 82, "normal (1, 0, 0)", 15, fill=TEAL)

    for x in (1, 3):
        value = side(x)
        f.circle(px(x), axis_y, 6, INK, WHITE, 1.8)
        f.text(px(x), axis_y - 24, f"({x}, 0, 0)", 15, anchor="middle")
        sign = "−" if value < 0 else ""
        f.text(px(x), axis_y + 28, f"1·{x} − 2 = {sign}{abs(value)}", 15, anchor="middle")
    return f


FIGURES = [box_around_a_turned_box, shear_from_an_uneven_parent, a_plane_as_four_numbers]
