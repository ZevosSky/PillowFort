"""Chapter 25, Grass Blades: authored figures.

@author Gary Yang
@brief Figures for 25-Grass-Blades.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *

SEGMENTS = 7          # Grass.vert.glsl: 7 pairs of vertices and a tip, 15 vertices
HEIGHT, WIDTH = 0.5, 0.05


def half_width(t):
    """Grass.vert.glsl's taper: full width low down, a point at the tip."""
    return 0.5 * WIDTH * (1.0 - t * t)


def strip_vertex(i):
    """Section 4's decode of gl_VertexIndex: (side, t), side -1 on the left edge and +1 on the right."""
    segment = i // 2
    side = -1.0 if i % 2 == 0 else 1.0
    return side, segment / SEGMENTS


def runs(f, x, y, parts, size=15):
    """One line made of (text, font, colour) runs."""
    for text, font, colour in parts:
        box = f.text(x, y, text, size, font, colour)
        x = box[2] + size * 0.4
    return x


def central_difference_normal():
    e, run, rise = 0.05, 0.10, 0.02          # section 3's worked numbers: a 2 cm rise across the 10 cm step
    assert abs(run - 2 * e) < 1e-12
    length = math.hypot(-rise, run)
    normal = (-rise / length, run / length)
    assert (round(normal[0], 2), round(normal[1], 2)) == (-0.20, 0.98)
    assert round(math.degrees(math.atan2(-normal[0], normal[1]))) == 11
    assert abs(run * -rise + rise * run) < 1e-15   # (2e, dx) . (-dx, 2e) = 0

    f = Figure("central-difference-normal", 700, 330,
               "Side view, x to the right and y up: the ground's height a step e either side of x. Across a run of 2e it "
               "rises dx, so the slope is the arrow (2e, dx), and the normal (-dx, 2e) stands at right angles to it, "
               "pointing up and away from the rise.",
               kind="computed plot",
               source="25-Grass-Blades.md, section 3 (The ground)",
               parameters={"e": e, "dx": rise, "normal": [round(normal[0], 3), round(normal[1], 3)]})
    scale, slope, curl = 3000.0, rise / run, 8.0
    ox, oy = 330.0, 214.0

    def ground(t):
        """Straight between the two samples, curving over a crest beyond them, so the slope there is exact."""
        bend = max(0.0, abs(t) - e)
        return slope * t - curl * bend * bend

    def at(t):
        return (ox + t * scale, oy - ground(t) * scale)

    profile = [at(-0.085 + 0.181 * k / 160) for k in range(161)]
    f.polygon(profile + [(profile[-1][0], 312), (profile[0][0], 312)], FILL)
    f.line(profile, INK, 2.2)

    left, right = at(-e), at(e)
    # The run and the rise, dimensioned below and beside the slope.
    below, beside = left[1] + 18, right[0] + 18
    f.line([(left[0], left[1] + 6), (left[0], below + 6)], LINE, 1.1, "3 3")
    f.line([(right[0], right[1] + 6), (right[0], below + 6)], LINE, 1.1, "3 3")
    f.arrow([(left[0], below), (right[0], below)], GRAY, 1.3, 9, both=True)
    f.rect((left[0] + right[0]) / 2 - 18, below - 11, 36, 22, FILL)
    f.text((left[0] + right[0]) / 2, below, "2e", 15, "italic", INK, "middle")
    f.line([(right[0] + 6, right[1]), (beside + 6, right[1])], LINE, 1.1, "3 3")
    f.line([(right[0] + 6, left[1]), (beside + 6, left[1])], LINE, 1.1, "3 3")
    f.arrow([(beside, right[1]), (beside, left[1])], GRAY, 1.3, 9, both=True)
    f.text(beside + 12, (left[1] + right[1]) / 2, "dx", 15, "italic", INK)
    f.text((left[0] + right[0]) / 2, below + 28, "slope (2e, dx)", 15, "bold", BLUE, "middle")

    f.arrow([left, (right[0] - 9, right[1] + 9 * slope)], BLUE, 3, 14)
    base = at(0)
    along = (1 / math.hypot(1, slope), -slope / math.hypot(1, slope))
    up = (normal[0], -normal[1])
    mark = 12
    f.line([(base[0] + along[0] * mark, base[1] + along[1] * mark),
            (base[0] + (along[0] + up[0]) * mark, base[1] + (along[1] + up[1]) * mark),
            (base[0] + up[0] * mark, base[1] + up[1] * mark)], TEAL, 1.3)
    reach = 148
    tip = (base[0] + up[0] * reach, base[1] + up[1] * reach)
    f.arrow([base, tip], TEAL, 3, 15)
    f.circle(*base, 5, INK, WHITE, 1.6)
    f.text(tip[0], tip[1] - 18, "normal (−dx, 2e)", 15, "bold", TEAL, "middle")

    for point, label, dx, dy, anchor in [(left, "height at x − e", -12, -20, "end"), (right, "height at x + e", 10, -24, "start")]:
        f.circle(*point, 6, GOLD, WHITE, 1.8)
        f.text(point[0] + dx, point[1] + dy, label, 15, anchor=anchor)

    gx, gy = 590, 104
    f.arrow([(gx, gy), (gx + 46, gy)], GRAY, 1.6, 10)
    f.arrow([(gx, gy), (gx, gy - 46)], GRAY, 1.6, 10)
    f.text(gx + 54, gy, "x", 15, "italic", GRAY)
    f.text(gx, gy - 58, "y", 15, "italic", GRAY, "middle")
    f.text(gx + 8, gy + 22, "side view", 13.5, "italic", GRAY)
    return f


def blade_strip_vertex_order():
    count = 2 * SEGMENTS + 1
    assert count == 15 and count - 2 == 13           # fifteen vertices, thirteen triangles
    assert strip_vertex(14) == (-1.0, 1.0) and half_width(1.0) == 0.0   # the tip: segment 7, left, zero width

    f = Figure("blade-strip-vertex-order", 760, 394,
               "The blade strip's fifteen vertices, numbered: even numbers up the left edge, odd up the right, from 0 and 1 "
               "at the root to 14 alone at the tip. Each triangle is a vertex and the two before it, so each quad between "
               "two pairs is two triangles.",
               source="25-Grass-Blades.md, section 4 (One blade from fifteen vertices)",
               parameters={"segments": SEGMENTS, "halfWidth": "0.5 * width * (1 - t*t)", "drawnWidthOverHeight": 0.42})
    cx, root_y, tall, wide = 196, 352, 308, 64   # wide: half the root's width in pixels, drawn wider than the blade

    def place(i):
        side, t = strip_vertex(i)
        return (cx + side * wide * half_width(t) / half_width(0.0), root_y - t * tall)

    points = [place(i) for i in range(count)]
    for k in range(count - 2):
        f.polygon([points[k], points[k + 1], points[k + 2]], BLUE_FILL if k % 2 == 0 else TEAL_FILL)
    for k in range(count - 2):
        f.line([points[k], points[k + 1], points[k + 2]], BLUE, 1.4, closed=True)
    for i, (x, y) in enumerate(points):
        f.circle(x, y, 4.5, INK, WHITE, 1.4)
        side, _ = strip_vertex(i)
        if i == count - 1:
            f.text(x, y - 20, str(i), 15, "bold", anchor="middle")
        else:
            f.text(x + side * 14, y, str(i), 15, "bold", anchor="end" if side < 0 else "start")
    f.text(cx + 30, points[-1][1] - 2, "tip", 14, fill=GRAY)
    f.text(cx + wide + 44, root_y, "root", 14, fill=GRAY)

    x = 360
    f.text(x, 60, "vertex i:", 15, "bold")
    runs(f, x, 88, [("segment = i / 2", "mono", INK), ("(0 .. 7)", "regular", GRAY)])
    runs(f, x, 114, [("side    = i odd ? right : left", "mono", INK)])
    runs(f, x, 140, [("t       = segment / 7,", "mono", INK), ("root 0 to tip 1", "regular", GRAY)])
    f.rect(x, 194, 22, 16, BLUE_FILL, BLUE, 1.2, 2)
    f.rect(x + 26, 194, 22, 16, TEAL_FILL, BLUE, 1.2, 2)
    f.text(x + 62, 202, "each quad between two pairs is two", 15)
    f.text(x + 62, 226, "triangles; the strip makes them from", 15)
    f.text(x + 62, 250, "the order alone", 15)
    f.text(x, 352, "drawn wider than the blade, to show the triangles", 13.5, "italic", GRAY)
    return f


def blade_control_points():
    tilt, bend = 0.3, 0.5                    # inside the meadow's ranges: tilt 0.10-0.45, bend 0.10-0.50
    lean = tilt * math.pi / 2
    # Section 6, in (back, up) coordinates.
    chord = (math.sin(lean), math.cos(lean))
    arch = (-math.cos(lean), math.sin(lean))
    assert abs(chord[0] * arch[0] + chord[1] * arch[1]) < 1e-12 and arch[1] > 0   # at right angles, away from the ground
    controls = [(0.0, 0.0),
                tuple(c / 3 + a * bend * 0.5 for c, a in zip(chord, arch)),
                tuple(c * 2 / 3 + a * bend * 0.5 for c, a in zip(chord, arch)),
                chord]

    def bezier(t):
        s = 1 - t
        weights = (s * s * s, 3 * s * s * t, 3 * s * t * t, t * t * t)
        return tuple(sum(w * p[k] for w, p in zip(weights, controls)) for k in range(2))

    for t in (0.0, 0.2, 0.5, 0.8, 1.0):      # the chapter's reduced form: P0 + height (chord t + 1.5 bend arch t (1 - t))
        reduced = tuple(c * t + 1.5 * bend * a * t * (1 - t) for c, a in zip(chord, arch))
        assert all(abs(p - q) < 1e-12 for p, q in zip(bezier(t), reduced))

    f = Figure("blade-control-points", 880, 404,
               "A blade's four control points in the vertical plane of up and back. The chord runs from the root, P0, to the "
               "tip, P3, leaning back from upright by tilt times 90 degrees; arch is perpendicular to it, away from the "
               "ground. P1 and P2 sit a third and two thirds of the way along the chord, pushed out along arch by bend times "
               "height over 2, and the curve bows toward them.",
               kind="computed plot",
               source="25-Grass-Blades.md, section 6 (The curve)",
               parameters={"tilt": tilt, "bend": bend, "leanDegrees": round(math.degrees(lean), 2)})
    rx, ry, height = 196, 352, 262

    def screen(point):
        return (rx + point[0] * height, ry - point[1] * height)

    f.hatch(56, 372, ry)
    f.line([(56, ry), (372, ry)], INK, 2)
    f.arrow([(rx, ry), (rx, ry - 300)], GRAY, 1.6, 11)
    f.text(rx, ry - 314, "up", 14, fill=GRAY, anchor="middle")
    f.arrow([(rx, ry), (rx + 206, ry)], GRAY, 1.6, 11)
    f.text(rx + 214, ry, "back", 14, fill=GRAY)

    p0, p1, p2, p3 = (screen(p) for p in controls)
    turn = 64
    f.arc(rx, ry, turn, 90 - math.degrees(lean), 90, BLUE, 1.4)
    # The wedge between up and the chord is too narrow for the label, so it sits outside, low, with a leader that
    # crosses the chord well below the arc's end and meets the arc at its middle.
    on_arc = (rx + turn * math.sin(lean * 0.5), ry - turn * math.cos(lean * 0.5))
    label = (rx + 34, ry - 22)
    f.line([(label[0] - 4, label[1] - 4), on_arc], BLUE, 1)
    f.text(*label, "tilt × 90°", 14, fill=BLUE)
    f.line([p0, p1, p2, p3], LINE, 1.2, "4 4")
    f.line([p0, p3], BLUE, 2, "8 6")
    on_chord = [screen(tuple(c * k / 3 for c in chord)) for k in (1, 2)]
    for start, end in zip(on_chord, (p1, p2)):
        mark = 9
        a = (arch[0], -arch[1])
        c = (chord[0], -chord[1])
        f.line([(start[0] + c[0] * mark, start[1] + c[1] * mark),
                (start[0] + (c[0] + a[0]) * mark, start[1] + (c[1] + a[1]) * mark),
                (start[0] + a[0] * mark, start[1] + a[1] * mark)], TEAL, 1.2)
        f.arrow([start, (end[0] - a[0] * 7, end[1] - a[1] * 7)], TEAL, 2, 10)
        f.circle(*start, 3, BLUE)
    f.line([screen(bezier(k / 80)) for k in range(81)], GREEN, 3.2)
    for point in (p1, p2):
        f.circle(*point, 6, WHITE, TEAL, 2)
    for point in (p0, p3):
        f.circle(*point, 6, INK, WHITE, 1.8)

    middle = screen(tuple(c * 0.5 for c in chord))
    f.text(middle[0] + 16, middle[1] + 8, "chord", 15, "bold", BLUE)
    # arch between its two arrows, halfway from the chord to the curve, clear of the up axis.
    bow = screen(bezier(0.5))
    f.text((middle[0] + bow[0]) / 2 + 3, (middle[1] + bow[1]) / 2, "arch", 15, "bold", TEAL, "middle")
    f.text(p1[0] - 14, p1[1], "P1", 15, "bold", anchor="end")
    f.text(p2[0], p2[1] - 20, "P2", 15, "bold", anchor="middle")   # above its point: the up axis runs just left of it
    f.text(p3[0] + 14, p3[1], "P3", 15, "bold")
    f.text(p3[0] + 14, p3[1] + 20, "(tip)", 14, fill=GRAY)
    box = f.text(p0[0] - 66, p0[1] - 16, "P0", 15, "bold", anchor="end")
    f.text(box[2] + 6, p0[1] - 16, "(root)", 14, fill=GRAY)

    x, name = 440, 92
    rows = [(BLUE, "chord", ["from the root toward the tip, leaning back", "by tilt × 90° from upright"]),
            (TEAL, "arch", ["perpendicular to chord, away from the", "ground"]),
            (INK, "P1, P2", ["a third and two thirds of the way along", "the chord, pushed out along arch by",
                             "bend × height / 2"]),
            (INK, "P3", ["the tip, height along the chord"])]
    y = 58
    for colour, label, text in rows:
        f.text(x, y, label, 15, "bold", colour)
        f.lines(x + name, y, text, 15, spacing=21)
        y += 21 * len(text) + 20
    return f


def first_blade_triangle_winding():
    points = {i: (strip_vertex(i)[0] * half_width(strip_vertex(i)[1]), strip_vertex(i)[1] * HEIGHT) for i in range(3)}
    (x0, y0), (x1, y1), (x2, y2) = points[0], points[1], points[2]
    signed = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    assert signed > 0                        # with +X right and +Y up, 0 -> 1 -> 2 turns counter-clockwise

    f = Figure("first-blade-triangle-winding", 720, 296,
               "The strip's first triangle seen from +Z, with +X to the right and +Y up: vertex 0 at the root's left edge, "
               "vertex 1 at the root's right edge, vertex 2 one step up on the left edge. Going 0, 1, 2 and back to 0 turns "
               "counter-clockwise, and the normal points out of the page, toward you.",
               kind="computed plot",
               source="25-Grass-Blades.md, section 7 (Normals, two faces, and light)",
               parameters={"vertices": {str(i): [round(p[0], 4), round(p[1], 4)] for i, p in points.items()}})
    scale, ox, oy = 2600, 150, 242
    at = {i: (ox + p[0] * scale, oy - p[1] * scale) for i, p in points.items()}
    corners = [at[0], at[1], at[2]]
    f.polygon(corners, BLUE_FILL, BLUE, 1.6)
    for i in range(3):
        a, b = corners[i], corners[(i + 1) % 3]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        f.arrow([(mid[0] - ux * 14, mid[1] - uy * 14), (mid[0] + ux * 6, mid[1] + uy * 6)], BLUE, 2.2, 13)
    # The turning sign sits at the incentre, the point furthest from all three edges and their arrows. It runs
    # counter-clockwise from 120 degrees round to 60, and its head leaves the arc along the tangent there, pointing
    # up and to the left, so the head is never built from a chord shorter than itself.
    sides = [math.hypot(corners[(i + 2) % 3][0] - corners[(i + 1) % 3][0], corners[(i + 2) % 3][1] - corners[(i + 1) % 3][1])
             for i in range(3)]
    centre = tuple(sum(s * c[k] for s, c in zip(sides, corners)) / sum(sides) for k in range(2))
    radius, start, end, lead = 22, 138, 420, 12
    turn = [(centre[0] + radius * math.cos(math.radians(s)), centre[1] - radius * math.sin(math.radians(s)))
            for s in range(start, end + 1, 6)]
    tangent = (-math.sin(math.radians(end)), -math.cos(math.radians(end)))     # counter-clockwise, in screen y-down
    turn.append((turn[-1][0] + tangent[0] * lead, turn[-1][1] + tangent[1] * lead))
    f.arrow(turn, TEAL, 1.8, 9)
    for i, (x, y) in at.items():
        f.circle(x, y, 5.5, INK, WHITE, 1.6)
    f.text(at[0][0] - 14, at[0][1] + 4, "0", 16, "bold", anchor="end")
    f.text(at[1][0] + 14, at[1][1] + 4, "1", 16, "bold")
    f.text(at[2][0] - 14, at[2][1], "2", 16, "bold", anchor="end")

    gx, gy = 280, 160
    f.arrow([(gx, gy), (gx + 44, gy)], GRAY, 1.6, 10)
    f.arrow([(gx, gy), (gx, gy - 44)], GRAY, 1.6, 10)
    f.text(gx + 52, gy, "+X", 14, fill=GRAY)
    f.text(gx, gy - 56, "+Y", 14, fill=GRAY, anchor="middle")
    f.circle(gx, gy, 8, WHITE, GRAY, 1.6)
    f.circle(gx, gy, 2.8, GRAY)
    f.text(gx - 14, gy + 22, "seen from +Z", 13.5, "italic", GRAY)

    x = 372
    rows = [("vertex 0:", "root, left edge", "(side −1)"), ("vertex 1:", "root, right edge", "(side +1)"),
            ("vertex 2:", "one step up, left edge", "")]
    for k, (name, where, side) in enumerate(rows):
        y = 64 + 26 * k
        runs(f, x, y, [(name, "bold", INK), (where, "regular", INK)] + ([(side, "regular", GRAY)] if side else []))
    f.text(x, 164, "0 → 1 → 2 → 0 turns counter-clockwise", 15, "bold", TEAL)
    f.circle(x + 8, 222, 8, WHITE, INK, 1.8)
    f.circle(x + 8, 222, 2.8, INK)
    f.text(x + 26, 222, "the normal: out of the page, toward you", 15)
    return f


FIGURES = [central_difference_normal, blade_strip_vertex_order, blade_control_points, first_blade_triangle_winding]
