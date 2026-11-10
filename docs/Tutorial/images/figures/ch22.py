"""Chapter 22, Deferred Shading: authored figures.

@author Gary Yang
@brief Figures for 22-Deferred-Shading.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def card(f, x, y, w, h, title, notes=(), kind="plain"):
    """A pass with its title and, under it, what it does, left-aligned; y is the top."""
    fill, stroke = {"plain": (FILL, LINE), "pass": (BLUE_FILL, BLUE)}[kind]
    f.rect(x, y, w, h, fill, stroke, 1.4, 10)
    if notes:
        top = y + (h - 26 - 19 * len(notes)) / 2  # the block of title and notes, centred in the box
        f.text(x + 16, top + 13, title, 15, "bold")
        f.lines(x + 16, top + 35, notes, 14, spacing=19)
    else:
        f.text(x + 16, y + h / 2, title, 15, "bold")


def forward_and_deferred_frames():
    f = Figure("forward-and-deferred-frames", 880, 470,
               "The frame forward and deferred, side by side: both start with the shadow pass and end with the second "
               "scope's blended things and the hand-back to the composite. Between them, forward's one scene pass runs "
               "the material and every light per fragment, while deferred's G-buffer pass writes the material and a "
               "compute lighting pass adds, per pixel, the lights near its tile.",
               source="22-Deferred-Shading.md, What you are actually writing")
    columns = [(24, "forward (Chapters 11-21)"), (472, "deferred (this chapter)")]
    w, gap = 384, 24
    for x, heading in columns:
        f.text(x, 30, heading, 15, "bold")
        f.line([(x, 46), (x + w, 46)], LINE, 1.2)

    # Row tops and heights; the forward scene pass spans the deferred G-buffer and lighting rows.
    y_shadow, h_shadow = 62, 40
    y_gbuffer, h_gbuffer = y_shadow + h_shadow + gap, 100
    y_light, h_light = y_gbuffer + h_gbuffer + gap, 82
    y_scope, h_scope = y_light + h_light + gap, 62
    y_hand, h_hand = y_scope + h_scope + gap, 40
    f.height = y_hand + h_hand + 24

    left, right = columns[0][0], columns[1][0]
    for x in (left, right):
        card(f, x, y_shadow, w, h_shadow, "shadow pass")
        card(f, x, y_hand, w, h_hand, "hand back to the composite (Chapter 08)")
    card(f, left, y_gbuffer, w, y_light + h_light - y_gbuffer, "scene pass",
         ["per fragment, the material and then every light;", "writes color, depth"], "pass")
    card(f, right, y_gbuffer, w, h_gbuffer, "G-buffer pass",
         ["per fragment, the material only; writes the", "G-buffer, the depth, and the light that needs",
          "no light list (ambient, emission)"], "pass")
    card(f, right, y_light, w, h_light, "lighting pass, compute",
         ["per pixel, the lights near its tile, added to", "what the G-buffer pass wrote"], "pass")
    card(f, left, y_scope, w, h_scope, "second scope", ["blended things (section 10)"])
    card(f, right, y_scope, w, h_scope, "second scope", ["the same blended things, unchanged"])

    centre = w / 2
    for x, stops in [(left, [(y_shadow, h_shadow), (y_gbuffer, y_light + h_light - y_gbuffer), (y_scope, h_scope), (y_hand, h_hand)]),
                     (right, [(y_shadow, h_shadow), (y_gbuffer, h_gbuffer), (y_light, h_light), (y_scope, h_scope), (y_hand, h_hand)])]:
        for (top_a, h_a), (top_b, _) in zip(stops, stops[1:]):
            f.arrow([(x + centre, top_a + h_a + 1), (x + centre, top_b - 1)], GRAY, 1.6, 10)
    return f


def octahedral_normal_square():
    def encode(n):
        """encodeOctahedral, with signNotZero, as the chapter's GLSL writes it."""
        total = abs(n[0]) + abs(n[1]) + abs(n[2])
        p = (n[0] / total, n[1] / total)
        if n[2] >= 0:
            return p
        sign = [1.0 if c >= 0 else -1.0 for c in p]
        return ((1 - abs(p[1])) * sign[0], (1 - abs(p[0])) * sign[1])

    def decode(e):
        n = [e[0], e[1], 1 - abs(e[0]) - abs(e[1])]
        if n[2] < 0:
            sign = [1.0 if c >= 0 else -1.0 for c in n[:2]]
            n[0], n[1] = (1 - abs(e[1])) * sign[0], (1 - abs(e[0])) * sign[1]
        length = math.sqrt(sum(c * c for c in n))
        return [c / length for c in n]

    above, below = (0.6, 0.0, 0.8), (0.6, 0.0, -0.8)
    e_above, e_below = encode(above), encode(below)
    # The chapter's worked numbers: (0.4286, 0), and (1, 0.5714) for the mirror below the equator.
    assert (round(e_above[0], 4), round(e_above[1], 4)) == (0.4286, 0.0)
    assert (round(e_below[0], 4), round(e_below[1], 4)) == (1.0, 0.5714)
    assert all(abs(a - b) < 1e-12 for a, b in zip(decode(e_above), above))
    assert all(abs(a - b) < 1e-12 for a, b in zip(decode(e_below), below))
    # The fold is a mirror across the edge x + y = 1: the midpoint lies on it, and the step is along (1, 1).
    assert abs((e_above[0] + e_below[0]) / 2 + (e_above[1] + e_below[1]) / 2 - 1) < 1e-12
    assert abs((e_below[0] - e_above[0]) - (e_below[1] - e_above[1])) < 1e-12

    f = Figure("octahedral-normal-square", 860, 384,
               "The square from -1 to 1 that holds an octahedral normal: the diamond |x| + |y| <= 1 inside it is the "
               "upper half of the sphere, +z at its centre, and the four corner triangles are the lower half folded out, "
               "-z at the corners. The normal (0.6, 0, 0.8) lands at (0.4286, 0), and its mirror (0.6, 0, -0.8) folds "
               "out to (1, 0.5714).",
               kind="computed plot", source="22-Deferred-Shading.md, section 3 (A normal in two numbers)",
               parameters={"examples": {"(0.6, 0, 0.8)": [round(c, 4) for c in e_above],
                                        "(0.6, 0, -0.8)": [round(c, 4) for c in e_below]}})
    x0, y0, S = 92, 38, 300
    cx, cy = x0 + S / 2, y0 + S / 2

    def at(ex, ey):
        return (x0 + (ex + 1) / 2 * S, y0 + (1 - ey) / 2 * S)

    diamond = [at(0, 1), at(1, 0), at(0, -1), at(-1, 0)]
    f.rect(x0, y0, S, S, GOLD_FILL, "none")
    f.polygon(diamond, BLUE_FILL, BLUE, 1.6)
    f.line([at(-1, 0), at(1, 0)], LINE, 1, "4 4")
    f.line([at(0, -1), at(0, 1)], LINE, 1, "4 4")
    f.rect(x0, y0, S, S, "none", INK, 1.6)

    for sx in (-1, 1):
        for sy in (-1, 1):
            f.circle(*at(sx, sy), 4.5, GOLD, WHITE, 1.4)
            lx, ly = at(sx * 0.82, sy * 0.86)
            f.text(lx, ly, "−z", 15, "bold", GOLD_TEXT, "middle")
            gx, gy = at(sx * 0.66, sy * 0.66)  # deep in the corner triangle, clear of the diamond's edge
            f.text(gx, gy, "lower", 13.5, "italic", GOLD_TEXT, "middle")
    f.circle(cx, cy, 4.5, BLUE, WHITE, 1.4)
    f.text(cx - 10, cy - 14, "+z", 15, "bold", BLUE, "end")
    # The label sits on the dashed x = 0 axis, so the axis stops for it.
    label_w, label_h = measure("upper half", 13.5, "italic")
    f.rect(cx - label_w / 2 - 5, cy - 58 - label_h / 2 - 4, label_w + 10, label_h + 8, BLUE_FILL)
    f.text(cx, cy - 58, "upper half", 13.5, "italic", BLUE, "middle")

    # The worked pair: the same p, kept in the diamond above the equator, folded out across the edge below it.
    pa, pb = at(*e_above), at(*e_below)
    f.arrow([pa, pb], TEAL, 1.6, 10, "5 4")
    f.circle(*pa, 5.5, TEAL, WHITE, 1.6)
    f.circle(*pb, 5.5, WHITE, TEAL, 2.2)
    f.text(pa[0], pa[1] + 20, "(0.4286, 0)", 13.5, fill=TEAL, anchor="middle")
    f.text(pb[0] + 12, pb[1], "(1, 0.5714)", 13.5, fill=TEAL)

    for (ex, ey), anchor, dx in [((-1, 1), "end", -10), ((1, 1), "start", 10), ((-1, -1), "end", -10), ((1, -1), "start", 10)]:
        x, y = at(ex, ey)
        f.text(x + dx, y, f"({'−1' if ex < 0 else '1'}, {'−1' if ey < 0 else '1'})", 13.5, fill=GRAY, anchor=anchor)

    key = 526
    f.rect(key, 52, 30, 20, BLUE_FILL, BLUE, 1.3, 3)
    f.lines(key + 42, 62, ["inside the diamond |x| + |y| ≤ 1:", "the upper half (z ≥ 0), +z at the centre,",
                           "the equator on the diamond's edges"], 14, spacing=19)
    f.rect(key, 142, 30, 20, GOLD_FILL, GOLD, 1.3, 3)
    f.lines(key + 42, 152, ["the four corner triangles: the lower", "half (z < 0), each quarter folded out",
                            "across the edge it touches; −z at the", "four corners"], 14, spacing=19)
    f.circle(key + 15, 262, 5.5, TEAL, WHITE, 1.6)
    f.text(key + 42, 262, "(0.6, 0, 0.8) → (0.4286, 0)", 14)
    f.circle(key + 15, 292, 5.5, WHITE, TEAL, 2.2)
    f.text(key + 42, 292, "(0.6, 0, −0.8) → (1, 0.5714):", 14)
    f.text(key + 42, 311, "the same p, folded out", 14)
    return f


def what_a_tile_can_light():
    f = Figure("what-a-tile-can-light", 800, 290,
               "Seen from the side, the tile's pixels look out from the eye between two of its four side planes. Inside "
               "those planes, between the nearest and the farthest surface the tile shows, is what the tile can light.",
               source="22-Deferred-Shading.md, section 8 (What a tile sees)")
    eye_x, eye_y = 64, 138
    label_y = eye_y + 128
    end_x, near_x, far_x = 640, 352, 548
    spread = math.tan(math.radians(10))

    def edge(x, side):
        return eye_y + side * (x - eye_x) * spread

    region = [(near_x, edge(near_x, -1)), (far_x, edge(far_x, -1)), (far_x, edge(far_x, 1)), (near_x, edge(near_x, 1))]
    f.polygon(region, TEAL_FILL, TEAL, 1.6)
    f.lines((near_x + far_x) / 2, eye_y - 10, ["what the tile", "can light"], 15, "bold", TEAL, "middle", 20)

    for x, label in [(near_x, "nearest surface"), (far_x, "farthest surface")]:
        f.line([(x, edge(x, -1) - 22), (x, edge(x, 1) + 22)], INK, 1.6, "6 4")
        f.text(x, label_y, label, 14, fill=INK, anchor="middle")
    for side, label in [(-1, "one side plane"), (1, "the opposite one")]:
        f.line([(eye_x, eye_y), (end_x, edge(end_x, side))], BLUE, 2.2)
        f.text(end_x + 12, edge(end_x, side), label, 14, fill=BLUE)
    f.circle(eye_x, eye_y, 6.5, INK, WHITE, 1.6)
    f.text(eye_x - 2, eye_y + 24, "eye", 15, "bold", anchor="middle")
    f.text(24, label_y, "seen from the side", 13.5, "italic", GRAY)  # the view, as an aside, not a title
    return f


FIGURES = [forward_and_deferred_frames, octahedral_normal_square, what_a_tile_can_light]
