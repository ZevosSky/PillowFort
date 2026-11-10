"""Chapter 26, Grass: GPU Generation: authored figures.

@author Gary Yang
@brief Figures for 26-Grass-GPU-Generation.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *

# GrassField.h: the blade buffer's two regions.
LOD0_CAPACITY, LOD1_CAPACITY = 200000, 600000
# BladeShape.glsl: LOD 0 has 7 segments, LOD 1 has 3, nested at LOD 0's pairs 0, 2, 4 and 7.
HIGH_SEGMENTS, LOW_TO_HIGH = 7, (0, 2, 4, 7)


def segment_t(pair):
    """BladeShape.glsl's segmentT: t(i) = 1 - (1 - i/7)^2, steps that shrink toward the tip."""
    s = pair / HIGH_SEGMENTS
    return 1.0 - (1.0 - s) * (1.0 - s)


def lod_regions_in_one_blade_buffer():
    f = Figure("lod-regions-in-one-blade-buffer", 880, 238,
               "The blade buffer holds both levels: LOD 0, 15 vertices each, in slots 0 up to capacity0, and LOD 1, 7 "
               "vertices each, in slots capacity0 up to capacity0 + capacity1. Draw 0 starts at firstInstance 0 and draw 1 "
               "at firstInstance capacity0.",
               source="26-Grass-GPU-Generation.md, section 5 (One buffer, two regions, two draws)",
               parameters={"capacity0": LOD0_CAPACITY, "capacity1": LOD1_CAPACITY, "widthsToScale": True})
    left, right = 104, 856
    split = left + (right - left) * LOD0_CAPACITY / (LOD0_CAPACITY + LOD1_CAPACITY)
    top, height = 62, 58
    middle = top + height / 2

    f.text(24, middle, "blades", 15, "bold")
    for x, label, anchor in [(left, "0", "middle"), (split, "capacity0", "middle"),
                             (right, "capacity0 + capacity1", "end")]:
        f.line([(x, top - 16), (x, top)], LINE, 1.2)
        f.text(x + (6 if anchor == "end" else 0), top - 28, label, 14, "mono", GRAY, anchor)
    for a, b, name, note in [(left, split, "LOD 0", "15 vertices each"), (split, right, "LOD 1", "7 vertices each")]:
        f.rect(a, top, b - a, height, GOLD_FILL, GOLD, 1.4, 6)
        f.text((a + b) / 2, middle - 10, name, 15, "bold", anchor="middle")
        f.text((a + b) / 2, middle + 12, note, 13.5, fill=GRAY, anchor="middle")

    # Each draw names where its region starts; gl_InstanceIndex counts on from there.
    row = 162
    for x, name, value in [(left, "draw 0", "firstInstance 0"), (split, "draw 1", "firstInstance capacity0")]:
        f.arrow([(x, row + 22), (x, top + height + 4)], BLUE, 2, 12)
        f.text(x + 12, row, name, 15, "bold", BLUE)
        f.text(x + 12, row + 22, value, 14, "mono", INK)
    f.text(right, 222, "widths to scale: capacity0 200,000, capacity1 600,000", 13.5, "italic", GRAY, "end")
    return f


def nested_blade_levels_along_t():
    ts = [segment_t(i) for i in range(HIGH_SEGMENTS + 1)]
    printed = [0, 0.27, 0.49, 0.67, 0.82, 0.92, 0.98, 1]           # section 5's eight pairs
    assert [round(t, 2) for t in ts] == printed
    assert round(ts[1] - ts[0], 2) == 0.27 and round(ts[7] - ts[6], 2) == 0.02
    low = [ts[i] for i in LOW_TO_HIGH]
    assert [round(t, 2) for t in low] == [0, 0.49, 0.82, 1]
    assert [round(b - a, 2) for a, b in zip(low, low[1:])] == [0.49, 0.33, 0.18]

    f = Figure("nested-blade-levels-along-t", 880, 284,
               "One edge of a blade along t, from the root at 0 to the tip at 1. The high level has eight vertex pairs, "
               "0 to 7, whose steps shrink toward the tip; the low level has four, at the high level's pairs 0, 2, 4 and 7, "
               "the pairs both levels share.",
               kind="computed plot",
               source="26-Grass-GPU-Generation.md, section 6 (Hiding the switch)",
               parameters={"t": [round(t, 4) for t in ts], "lowToHigh": list(LOW_TO_HIGH)})
    x0, x1 = 140, 836
    high_y, low_y = 92, 162

    def px(t):
        return x0 + (x1 - x0) * t

    def dot(x, y, is_shared):
        if is_shared:
            f.circle(x, y, 6.5, WHITE, TEAL, 2.2)
            f.circle(x, y, 2.8, TEAL)
        else:
            f.circle(x, y, 4.8, INK, WHITE, 1.3)

    # The legend, on its own row above the drawing.
    dot(440, 30, False)
    f.text(454, 30, "every pair", 14)
    dot(578, 30, True)
    f.text(594, 30, "the pairs both levels share", 14)

    shared = set(LOW_TO_HIGH)
    for y, name in [(high_y, "high level"), (low_y, "low level")]:
        f.text(24, y, name, 15, "bold")
    f.line([(px(0), high_y), (px(1), high_y)], INK, 2)
    f.line([(px(low[0]), low_y), (px(low[-1]), low_y)], INK, 2)
    for i in LOW_TO_HIGH:
        f.line([(px(ts[i]), high_y + 9), (px(ts[i]), low_y - 9)], TEAL, 1.3, "4 4")

    # Pairs 6 and 7 sit 0.02 apart; their numbers lean away from each other.
    nudge = {6: (-3, "end"), 7: (3, "start")}
    for i, t in enumerate(ts):
        dot(px(t), high_y, i in shared)
        dx, anchor = nudge.get(i, (0, "middle"))
        f.text(px(t) + dx, high_y - 22, str(i), 14, "bold", TEAL if i in shared else INK, anchor)
    for i in LOW_TO_HIGH:
        dot(px(ts[i]), low_y, True)
        f.text(px(ts[i]), low_y + 23, str(i), 14, "bold", TEAL, "middle")

    # A t ruler under both, so 0.49 and 0.82 can be read off.
    ruler = 222
    f.line([(px(0), ruler), (px(1), ruler)], LINE, 1.2)
    for t in (0, 0.25, 0.5, 0.75, 1):
        f.line([(px(t), ruler - 5), (px(t), ruler + 5)], LINE, 1.2)
        f.text(px(t), ruler + 20, f"{t:g}", 13.5, fill=GRAY, anchor="middle")
    f.text(px(0) - 16, ruler, "t", 15, "italic", GRAY, "end")
    f.text(px(0), ruler + 41, "root", 13.5, "italic", GRAY, "middle")
    f.text(px(1), ruler + 41, "tip", 13.5, "italic", GRAY, "middle")
    return f


def pair_three_slides_onto_the_low_level():
    tilt, bend = 0.3, 0.5   # Chapter 25's figure's blade, inside the meadow's ranges (tilt 0.10-0.45, bend 0.10-0.50)
    lean = tilt * math.pi / 2
    chord = (math.sin(lean), math.cos(lean))          # (back, up), as BladeShape.glsl builds them
    arch = (-math.cos(lean), math.sin(lean))
    controls = [(0.0, 0.0),
                tuple(c / 3 + a * bend * 0.5 for c, a in zip(chord, arch)),
                tuple(c * 2 / 3 + a * bend * 0.5 for c, a in zip(chord, arch)),
                chord]

    def bezier(t):
        s = 1 - t
        weights = (s * s * s, 3 * s * s * t, 3 * s * t * t, t * t * t)
        return tuple(sum(w * p[k] for w, p in zip(weights, controls)) for k in range(2))

    ta, tb, t3 = segment_t(2), segment_t(4), segment_t(3)
    fraction = (t3 - ta) / (tb - ta)                   # the morph's f = (t - ta) / (tb - ta)
    assert abs(fraction - 9 / 16) < 1e-12
    a, b, on_curve = bezier(ta), bezier(tb), bezier(t3)
    on_segment = tuple(p + (q - p) * fraction for p, q in zip(a, b))

    # Turn the piece so 2 -> 4 runs left to right, and scale it to the panel.
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    span = 340

    def place(point, ox, oy):
        dx, dy = point[0] - a[0], point[1] - a[1]
        u = (dx * math.cos(angle) + dy * math.sin(angle)) / length
        v = (-dx * math.sin(angle) + dy * math.cos(angle)) / length
        return (ox + u * span, oy - v * span)

    assert place(on_curve, 0, 0)[1] < 0       # the curve bows the same way in both panels: up, as drawn
    f = Figure("pair-three-slides-onto-the-low-level", 880, 222,
               "Side-on, one edge of the blade between the shared pairs 2 and 4. At morph = 0, pair 3 sits on the curve, "
               "which bulges away from the straight segment. At morph = 1 it sits on the straight segment from 2 to 4, at "
               "the same fraction of the way from 2 to 4.",
               kind="computed plot",
               source="26-Grass-GPU-Generation.md, section 6 (Hiding the switch)",
               parameters={"tilt": tilt, "bend": bend, "t": [round(ta, 4), round(t3, 4), round(tb, 4)],
                           "fraction": "9/16", "drawnSpanPixels": span})
    left_x, right_x, base_y = 52, 482, 108
    for ox, title in [(left_x, "morph = 0"), (right_x, "morph = 1")]:
        f.text(ox + span / 2, 32, title, 15, "bold", anchor="middle")
    curve = [bezier(ta + (tb - ta) * k / 60) for k in range(61)]

    # morph = 0: the curve carries pair 3; the straight segment is only a guide.
    f.line([place(a, left_x, base_y), place(b, left_x, base_y)], LINE, 1.3, "5 5")
    f.line([place(p, left_x, base_y) for p in curve], GREEN, 3)
    # morph = 1: the straight segment carries pair 3; the curve it left is the guide, with pair 3's old place.
    f.line([place(p, right_x, base_y) for p in curve], LINE, 1.3, "5 5")
    f.line([place(a, right_x, base_y), place(b, right_x, base_y)], GREEN, 3)
    f.circle(*place(on_curve, right_x, base_y), 5.5, WHITE, LINE, 1.4)

    for ox, three, label_dy in [(left_x, place(on_curve, left_x, base_y), -20),
                                (right_x, place(on_segment, right_x, base_y), 22)]:
        for point, label in [(a, "2"), (b, "4")]:
            x, y = place(point, ox, base_y)
            f.circle(x, y, 7, WHITE, TEAL, 2.2)
            f.circle(x, y, 3.2, TEAL)
            f.text(x + (-16 if label == "2" else 16), y, label, 15, "bold", TEAL, "end" if label == "2" else "start")
        f.circle(*three, 6, INK, WHITE, 1.6)
        f.text(three[0], three[1] + label_dy, "3", 15, "bold", anchor="middle")

    f.text(left_x + span / 2, 168, "pair 3 on the curve", 15, anchor="middle")
    f.lines(right_x + span / 2, 168, ["pair 3 on the straight segment, at the", "same fraction of the way from 2 to 4"],
            15, anchor="middle", spacing=21)
    return f


def depth_pyramid_by_hand():
    depth = [[0.2, 0.3, 0.9, 0.9],
             [0.6, 0.4, 0.8, 0.7],
             [0.5, 0.5, 0.3, 0.8],
             [0.5, 0.4, 0.2, 0.1]]

    def reduce(image):
        n = len(image) // 2
        return [[max(image[2 * r + i][2 * c + j] for i in (0, 1) for j in (0, 1)) for c in range(n)] for r in range(n)]

    level0 = reduce(depth)
    level1 = reduce(level0)
    assert level0 == [[0.6, 0.9], [0.5, 0.8]] and level1 == [[0.9]]   # the chapter's worked pyramid

    f = Figure("depth-pyramid-by-hand", 760, 298,
               "A 4 by 4 depth image reduced to level 0, 2 by 2, and level 1, 1 by 1. Each texel keeps the largest, "
               "farthest, of the four below it: level 0 holds 0.6, 0.9, 0.5 and 0.8, and level 1 holds 0.9.",
               kind="computed plot",
               source="26-Grass-GPU-Generation.md, section 9 (Occlusion culling against last frame's depth)",
               parameters={"depth": depth, "level0": level0, "level1": level1})
    cell, top = 52, 62
    grids = [(32, depth, "depth image, 4 × 4"), (370, level0, "level 0, 2 × 2"), (612, level1, "level 1, 1 × 1")]

    def kept(image, r, c):
        """True for a texel the level above keeps: the largest of its 2 x 2 block (every one, on a tie)."""
        br, bc = r // 2 * 2, c // 2 * 2
        return image[r][c] == max(image[br + i][bc + j] for i in (0, 1) for j in (0, 1))

    for x, image, title in grids:
        n = len(image)
        y = top + (4 - n) * cell / 2
        f.text(x + n * cell / 2, y - 20, title, 14, fill=GRAY, anchor="middle")
        for r in range(n):
            for c in range(n):
                keep = n > 1 and kept(image, r, c)
                f.rect(x + c * cell, y + r * cell, cell, cell, TEAL_FILL if keep else WHITE, LINE, 1)
                f.text(x + (c + 0.5) * cell, y + (r + 0.5) * cell, f"{image[r][c]:g}", 15,
                       "bold" if keep or n == 1 else "regular", TEAL if keep else INK, "middle")
        if n > 1:
            mid = n * cell / 2
            f.line([(x + mid, y), (x + mid, y + n * cell)], INK, 2.2)
            f.line([(x, y + mid), (x + n * cell, y + mid)], INK, 2.2)
        f.rect(x, y, n * cell, n * cell, "none", INK, 2.2)

    centre = top + 2 * cell
    f.arrow([(32 + 4 * cell + 22, centre), (370 - 22, centre)], GRAY, 1.8, 11)
    f.arrow([(370 + 2 * cell + 22, centre), (612 - 22, centre)], GRAY, 1.8, 11)
    f.text(340, 240, "each texel: the largest of the four below it", 14)
    f.rect(340, 259, 22, 18, TEAL_FILL, LINE, 1)
    f.text(372, 268, "the largest of its four: what the level above keeps", 14, fill=GRAY)
    return f


FIGURES = [lod_regions_in_one_blade_buffer, nested_blade_levels_along_t, pair_three_slides_onto_the_low_level,
           depth_pyramid_by_hand]
