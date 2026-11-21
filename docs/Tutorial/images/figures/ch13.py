"""Chapter 13, Adding a Library: TinyUSDZ: authored figures.

@author Gary Yang
@brief Figures for 13-Adding-TinyUSDZ.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def xform_op_order_from_above():
    turn = 30.0
    move = (1.0, 0.0)  # xformOp:translate's x and z; its y, 0.5, is the height and does not show from above

    def rotate_y(point, degrees):  # world (x, z) under rotateY: x' = x cos + z sin, z' = -x sin + z cos
        c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
        return (point[0] * c + point[1] * s, -point[0] * s + point[1] * c)

    file_order = move                     # T · R: turn about the centre at the origin, then move
    reversed_order = rotate_y(move, turn)  # R · T: move, then swing about the parent's origin
    # The chapter's numbers: (1, 0.5, 0) for the file's order, (0.87, 0.5, -0.5) reversed.
    assert file_order == (1.0, 0.0)
    assert (round(reversed_order[0], 2), round(reversed_order[1], 2)) == (0.87, -0.5)

    f = Figure("xform-op-order-from-above", 840, 352,
               "Two top-down views of a prim, with +Y toward you, the parent's x to the right and -z up. "
               "In the order written above, translate then rotateY (T · R), the prim turns 30 degrees about its own centre "
               "while that centre is at the origin, then moves to (1, 0.5, 0). Reversed (R · T), it moves to (1, 0.5, 0) "
               "first, then swings 30 degrees about the parent's Y axis, on a circle of radius 1 around the parent's "
               "origin, to (0.87, 0.5, -0.5). It ends turned the same way in both.",
               kind="computed plot", source="13-Adding-TinyUSDZ.md, section 9 (Transforms are a list of operations)",
               parameters={"translate": [1, 0.5, 0], "rotateYDegrees": turn,
                           "reversedCentre": [round(reversed_order[0], 4), 0.5, round(reversed_order[1], 4)]})
    s, oy, half = 150, 226, 0.15  # pixels per metre; the origin's row; the marker's half-size in metres

    def page(ox, point):  # world (x, z) to the page: x right, z down (so -z is up)
        return (ox + s * point[0], oy + s * point[1])

    def square(ox, centre, degrees, fill, stroke, dash=None):
        corners = [rotate_y((sx * half, sz * half), degrees) for sx, sz in [(1, 1), (-1, 1), (-1, -1), (1, -1)]]
        points = [page(ox, (centre[0] + cx, centre[1] + cz)) for cx, cz in corners]
        if dash:
            f.line(points, stroke, 1.4, dash, closed=True)
        else:
            f.polygon(points, fill, stroke, 1.6, opacity=0.85)

    def badge(x, y, label):
        f.circle(x, y, 10, WHITE, INK, 1.4)
        f.text(x, y, label, 13, "bold", INK, "middle")

    def axes(ox):
        f.arrow([(ox, oy), (ox + s * 1.5, oy)], LINE, 1.2, 9)
        f.text(ox + s * 1.5 + 9, oy, "x", 15, "italic", GRAY)
        f.arrow([(ox, oy), (ox, oy - s * 0.93)], LINE, 1.2, 9)
        f.text(ox, oy - s * 0.93 - 14, "−z", 15, "italic", GRAY, "middle")

    def caption(ox, order, name):
        f.text(ox - 46, 30, order, 13.5, "mono")
        f.text(ox - 46, 54, name, 15, "bold")

    def steps(ox, first, second):
        badge(ox - 36, 288, "1")
        f.text(ox - 18, 288, first, 15)
        badge(ox - 36, 314, "2")
        f.text(ox - 18, 314, second, 15)

    # The order written above: T · R. The turn happens while the centre is still at the origin.
    ox = 96
    caption(ox, '["xformOp:translate", "xformOp:rotateY"]', "T · R, as written above")
    axes(ox)
    square(ox, (0, 0), 0, None, LINE, "5 4")
    square(ox, (0, 0), turn, GOLD_FILL, GOLD)
    f.arc(ox, oy, 40, 0, turn, TEAL, 1.6)
    f.text(ox + 48, oy - 13, "30°", 13, "bold", TEAL)
    badge(ox - 44, oy - 38, "1")
    square(ox, file_order, turn, GOLD_FILL, GOLD)
    end = page(ox, file_order)
    f.arrow([(ox + 8, oy), end], BLUE, 2.6, 13)
    badge(ox + s * 0.5, oy + 24, "2")
    f.circle(*end, 4, INK, WHITE, 1.3)
    f.text(end[0], oy - 52, "centre (1, 0.5, 0)", 15, "bold", anchor="middle")
    steps(ox, "turn 30° about its own centre", "move by (1, 0.5, 0)")

    # Reversed: R · T. The move happens first, so the turn swings the centre around the parent's origin.
    ox = 516
    caption(ox, '["xformOp:rotateY", "xformOp:translate"]', "R · T, reversed")
    axes(ox)
    square(ox, (0, 0), 0, None, LINE, "5 4")
    square(ox, move, 0, None, LINE, "5 4")
    square(ox, reversed_order, turn, GOLD_FILL, GOLD)
    moved = page(ox, move)
    f.arrow([(ox + 8, oy), moved], BLUE, 2.6, 13)
    badge(ox + s * 0.5, oy + 24, "1")
    f.line([(ox, oy), page(ox, reversed_order)], LINE, 1.2, "3 4")
    f.arc(ox, oy, s, 0, turn - 4, TEAL, 2.4)
    tip = (ox + s * math.cos(math.radians(turn)), oy - s * math.sin(math.radians(turn)))
    back = (ox + s * math.cos(math.radians(turn - 4)), oy - s * math.sin(math.radians(turn - 4)))
    f.arrow([back, tip], TEAL, 2.4, 13)
    f.arc(ox, oy, 40, 0, turn, TEAL, 1.6)
    f.text(ox + 48, oy - 13, "30°", 13, "bold", TEAL)
    badge(ox + (s + 30) * math.cos(math.radians(14)), oy - (s + 30) * math.sin(math.radians(14)), "2")
    f.circle(*page(ox, reversed_order), 4, INK, WHITE, 1.3)
    f.text(page(ox, reversed_order)[0], oy - s * 0.5 - 52, "centre (0.87, 0.5, −0.5)", 15, "bold", anchor="middle")
    steps(ox, "move by (1, 0.5, 0)", "swing 30° about the parent's Y")
    f.text(f.width / 2, 338, "seen from above, +Y toward you; the prim drawn as a small square, its centre dotted",
           13.5, "italic", GRAY, "middle")
    return f


FIGURES = [xform_op_order_from_above]
