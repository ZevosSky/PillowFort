"""Chapter 28, Clouds: authored figures.

@author Gary Yang
@brief Figures for 28-Clouds.md
@copyright (C) Gary 2026
"""
import functools
import math
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402  (only its contour routines, for outlines and bands)
import numpy as np                # noqa: E402

from figure_kit import *          # noqa: E402

BOTTOM, TOP = 1500.0, 4000.0      # CloudSettings.h: the cloud layer, metres above y = 0
_MASK = 0xFFFFFFFF


def mix_colour(a, b, t):
    """Blend two #rrggbb colours."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def contour_paths(xs, ys, values, levels, to_px):
    """Filled bands of a field, one SVG path per band, from Matplotlib's contour routine."""
    figure = plt.figure()
    bands = plt.contourf(xs, ys, values, levels=levels)
    out = []
    for path in bands.get_paths():
        d = []
        for (x, y), code in zip(path.vertices, path.codes):
            px, py = to_px(x, y)
            d.append(("M" if code == 1 else "Z" if code == 79 else "L") + ("" if code == 79 else f"{number(px)} {number(py)}"))
        out.append("".join(d))
    plt.close(figure)
    return out


def cloud_outline(f, blobs, base, fill, stroke):
    """A heap of soft round blobs cut flat at its base, as a cumulus is, outlined as one shape.

    Each blob is a steep bump, exp(-(d/r)^4), and the heap is where their sum reaches one half: round bumps
    joined by small fillets. Returns the heap's inside test, for the samples drawn in it."""
    def field(x, y):
        return np.minimum(sum(np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / (r * r)) ** 2) for cx, cy, r in blobs) - 0.5,
                          (base - y) / 40.0)

    def inside(x, y):
        return float(field(np.float64(x), np.float64(y))) >= 0
    x0 = min(cx - r for cx, _, r in blobs) - 8
    x1 = max(cx + r for cx, _, r in blobs) + 8
    y0 = min(cy - r for _, cy, r in blobs) - 8
    xs, ys = np.linspace(x0, x1, 320), np.linspace(y0, base + 4, 220)
    values = field(*np.meshgrid(xs, ys))
    for d in contour_paths(xs, ys, values, [0, values.max() + 1], lambda x, y: (x, y)):
        f.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="1.3" stroke-linejoin="round" fill-rule="evenodd"/>')
    return inside


def number_badge(f, x, y, digit):
    f.circle(x, y, 10, TEAL)
    f.text(x, y, digit, 13, "bold", WHITE, "middle")


def rays_through_the_cloud_layer():
    f = Figure("rays-through-the-cloud-layer", 880, 376,
               "The cloud layer lies between 1500 m and 4000 m. From the eye, one ray leaves through each texel of a cube "
               "face and is marched in steps from where it enters the layer to where it leaves. At each step: how dense is "
               "the cloud here, how much sun gets in, and how much of that leaves toward the eye.",
               source="28-Clouds.md, Where this is going",
               parameters={"bottomMetres": BOTTOM, "topMetres": TOP, "texelsDrawn": 8, "stepsDrawn": 10,
                           "verticalScale": "to scale; the eye drawn near the ground",
                           "markedRay": "the last texel on the sun's side"})
    k, ground = 0.064, 346                  # pixels per metre, vertically; the ground's line
    y_bottom, y_top = ground - BOTTOM * k, ground - TOP * k
    ex, ey = 282, ground - 18               # the eye, near the ground

    # The layer, its two altitudes named at the left.
    for y, label, dy in [(y_top, "4000 m: the top of the cloud layer", -14), (y_bottom, "1500 m: the bottom", 16)]:
        f.line([(24, y), (564, y)], LINE, 1.4, "8 5")
        f.text(24, y + dy, label, 14, fill=GRAY)
    f.hatch(24, 564, ground)
    f.line([(24, ground), (564, ground)], INK, 2)

    # Two heaps with flat bases in the layer; the marked ray crosses the right one.
    left_cloud = [(150, 222, 18), (174, 206, 24), (204, 194, 27), (230, 218, 22), (190, 228, 24)]
    cloud_outline(f, left_cloud, y_bottom - 16, GRID, LINE)
    right_cloud = [(340, 230, 20), (376, 224, 26), (416, 222, 28), (456, 224, 26), (492, 230, 20),
                   (390, 178, 28), (430, 168, 32), (468, 182, 24), (482, 204, 20),
                   (414, 138, 26), (448, 140, 22), (432, 124, 18)]
    in_cloud = cloud_outline(f, right_cloud, y_bottom - 10, GRID, LINE)

    # One ray per texel: 8 drawn of the face's 256, through the texel centres of the face straight up.
    # The marked ray is the last on the sun's side, so the three questions are drawn where no other ray runs.
    texels, near = 8, 34
    centres = [-1 + (2 * i + 1) / texels for i in range(texels)]
    marked = texels - 1
    grey = [((ex, ey), (ex + u * (ey - y_top), y_top)) for i, u in enumerate(centres) if i != marked]
    for segment in grey:
        f.line(list(segment), LINE, 1.1)
    f.line([(ex - near, ey - near), (ex + near, ey - near)], BLUE, 2.4)
    for i in range(texels + 1):
        x = ex - near + 2 * near * i / texels
        f.line([(x, ey - near - 4), (x, ey - near + 4)], BLUE, 1.3)

    u = centres[marked]
    entry = (ex + u * (ey - y_bottom), y_bottom)
    exit_ = (ex + u * (ey - y_top), y_top)
    f.line([(ex, ey), entry], BLUE, 1.6)
    f.line([entry, exit_], BLUE, 2.4)
    steps = 10
    points = [(entry[0] + (exit_[0] - entry[0]) * (j + 0.5) / steps, entry[1] + (exit_[1] - entry[1]) * (j + 0.5) / steps)
              for j in range(steps)]
    inside_points = [p for p in points if in_cloud(*p)]
    for x, y in points:
        f.circle(x, y, 4.2, BLUE if (x, y) in inside_points else WHITE, BLUE, 1.4)
    assert len(inside_points) >= 6 and not in_cloud(*points[0]) and not in_cloud(*points[-1])
    current = points[5]                     # the step the three questions are asked at
    assert in_cloud(*current)

    # Ray coordinates around that step: a runs down the ray toward the eye, s to its right, away from the other rays.
    length = math.hypot(entry[0] - exit_[0], entry[1] - exit_[1])
    along = ((entry[0] - exit_[0]) / length, (entry[1] - exit_[1]) / length)
    right = (along[1], -along[0])            # screen right of a ray running up and to the right

    def at(a, s):
        return (current[0] + along[0] * a + right[0] * s, current[1] + along[1] * a + right[1] * s)

    # The sun, and the three questions at one step.
    sun = (590, 56)
    for i in range(10):
        ray = unit(36 * i)
        f.line([(sun[0] + ray[0] * 17, sun[1] + ray[1] * 17), (sun[0] + ray[0] * 24, sun[1] + ray[1] * 24)], GOLD, 2)
    f.circle(*sun, 12, GOLD_SOFT, GOLD, 1.6)
    f.text(sun[0] - 34, sun[1], "sun", 14, fill=GOLD_TEXT, anchor="end")
    toward = (sun[0] - current[0], sun[1] - current[1])
    reach = math.hypot(*toward)
    toward = (toward[0] / reach, toward[1] / reach)
    gap = 30
    sun_line = (current, (sun[0] - toward[0] * gap, sun[1] - toward[1] * gap))
    f.line(list(sun_line), GOLD, 2, "7 5")
    f.circle(*current, 6.5, BLUE, WHITE, 1.8)

    light = (at(26, 14), at(70, 14))        # what leaves toward the eye: down the ray, beside it
    f.arrow(list(light), BLUE, 2, 10)

    below_sun = (-toward[1], toward[0])     # square to the sun's line, on its lower side (the sun is up and right)
    assert below_sun[1] > 0
    on_sun_line = (current[0] + toward[0] * 98, current[1] + toward[1] * 98)
    badges = {"1": at(0, 24),
              "2": (on_sun_line[0] + below_sun[0] * 16, on_sun_line[1] + below_sun[1] * 16),
              "3": at(44, 34)}
    for digit, (x, y) in badges.items():
        number_badge(f, x, y, digit)

    # Each badge clear of every line and sample, the ones it names included: 3 px between edges. Badge 1 also stands
    # well away from the tail of arrow 3, so it cannot be read as that arrow's label.
    def distance(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
    segments = grey + [((ex, ey), exit_), sun_line, light, ((24, y_top), (564, y_top)), ((24, y_bottom), (564, y_bottom))]
    for digit, (x, y) in badges.items():
        lines = [round(distance((x, y), a, b), 1) for a, b in segments]
        samples = [round(math.hypot(x - px_, y - py_), 1) for px_, py_ in points]
        assert min(lines) >= 10 + 3 + 1.2 and min(samples) >= 10 + 3 + 6.5, (digit, (x, y), lines, samples)
    assert math.hypot(badges["1"][0] - light[0][0], badges["1"][1] - light[0][1]) >= 2 * 10

    f.circle(ex, ey, 5, INK, WHITE, 1.4)
    f.text(ex + 14, ey + 4, "eye", 14, "bold")
    f.text(ex - near - 12, ey - near, "one ray per texel", 14, fill=GRAY, anchor="end")
    f.text(ex - near - 12, ey - near + 19, "of a cube face", 14, fill=GRAY, anchor="end")

    x = 600
    f.text(x, 150, "at each step along a ray:", 15, "bold")
    for y, digit, words in [(184, "1", ["how dense is it here?"]), (216, "2", ["how much sun gets in?"]),
                            (248, "3", ["how much of that leaves", "toward the eye?"])]:
        number_badge(f, x + 10, y, digit)
        f.lines(x + 30, y, words, 15, spacing=20)
    return f


def jittered_first_step():
    rays, rows, steps_up, step = 24, 4, 6, 23.0
    rng = random.Random(28)                 # a fixed stream, so the figure is the same every time it is built
    # One random fraction per texel: the top row's are the rays drawn above it.
    jitter = [[rng.random() for _ in range(rays)] for _ in range(rows)]

    def thickness(i):
        """How far, in steps, the cloud reaches along ray i: a smooth heap across the row of rays."""
        x = (i + 0.5) / rays
        return 0.3 + 4.4 * math.sin(math.pi * x) ** 1.5

    def counted(i, start):
        return sum(1 for s in range(steps_up + 1) if s + start < thickness(i))

    fixed = [[counted(i, 0.0) for i in range(rays)] for _ in range(rows)]
    jittered = [[counted(i, jitter[r][i]) for i in range(rays)] for r in range(rows)]
    assert all(c == math.ceil(thickness(i)) for i, c in enumerate(fixed[0]))      # a staircase: whole steps only
    assert all(abs(jittered[r][i] - fixed[r][i]) <= 1 for r in range(rows) for i in range(rays))
    assert any(len({jittered[r][i] for r in range(rows)}) > 1 for i in range(rays))   # one ray's column varies
    top_count = max(fixed[0])

    f = Figure("jittered-first-step", 880, 372,
               "Rays marched up through the same heap of cloud. When every ray starts at the entry point, neighbouring rays "
               "sample the same slices, and the texels, shaded by how many samples fell inside the cloud, form bands. When "
               "each ray starts a random fraction of a step later, the same texels break up into fine noise.",
               kind="computed plot",
               source="28-Clouds.md, section 3 (Why the first step is random)",
               parameters={"rays": rays, "rows": rows, "seed": 28, "thicknessInSteps": "0.3 + 4.4 sin(pi x)^1.5",
                           "countsFixed": fixed[0], "countsJittered": jittered})
    width, entry_y = 336, 214
    spacing = width / rays
    for x0, starts, counts, title, result in [
            (64, [[0.0] * rays] * rows, fixed, "every ray starts at the entry point", "bands"),
            (488, jitter, jittered, "each ray starts a random fraction of a step later", "fine noise")]:
        f.text(x0 + width / 2, 28, title, 15, "bold", anchor="middle")
        heap = [(x0 + (i + 0.5) * spacing, entry_y - thickness(i) * step) for i in range(rays)]
        f.polygon([(x0, entry_y)] + [(x0, heap[0][1])] + heap + [(x0 + width, heap[-1][1]), (x0 + width, entry_y)], GRID)
        f.line([(x0, heap[0][1])] + heap + [(x0 + width, heap[-1][1])], LINE, 1.3)
        f.line([(x0 - 6, entry_y), (x0 + width + 6, entry_y)], INK, 1.8)
        f.text(x0 - 12, entry_y, "entry", 13.5, "italic", GRAY, "end")
        for i in range(rays):
            x = x0 + (i + 0.5) * spacing
            f.line([(x, entry_y), (x, entry_y - (steps_up + 0.9) * step)], LINE, 0.9)
            for s in range(steps_up + 1):
                height = s + starts[0][i]
                y = entry_y - height * step
                inside = height < thickness(i)
                f.circle(x, y, 3.1, BLUE if inside else WHITE, BLUE if inside else LINE, 1.1)
        # One texel per ray, in four neighbouring rows of the image: how many of its samples fell inside the cloud.
        strip_y = entry_y + 26
        for r in range(rows):
            for i, count in enumerate(counts[r]):
                f.rect(x0 + i * spacing, strip_y + r * spacing, spacing, spacing, mix_colour(FILL, BLUE, count / top_count))
        f.rect(x0, strip_y, width, rows * spacing, "none", INK, 1.3)
        f.text(x0 + width / 2, strip_y + rows * spacing + 24, result, 15, "bold", anchor="middle")

    f.text(64, 352, "each texel: how many of its ray's samples fell inside the cloud; the top row is the rays above",
           13.5, "italic", GRAY)
    return f


# The shape volume's base channel: CloudShapeNoise.comp.glsl's worleyNoise(p, 4, 10u), Random.glsl's hash.
def _pcg_hash(value):
    state = (value * 747796405 + 2891336453) & _MASK
    word = (((state >> ((state >> 28) + 4)) ^ state) * 277803737) & _MASK
    return ((word >> 22) ^ word) & _MASK


def _random_float(state):
    state = _pcg_hash(state)
    return state, (state >> 8) * (1.0 / 16777216.0)


@functools.lru_cache(maxsize=None)
def _feature_point(cell, period, seed):
    """latticeHash and the jittered point of one cube; cells wrap every period, so the noise tiles."""
    wrapped = [(c + period) % period for c in cell]
    state = _pcg_hash(wrapped[0] ^ _pcg_hash(wrapped[1] ^ _pcg_hash(wrapped[2] ^ seed)))
    point = []
    for c in cell:                          # vec3(randomFloat(state), randomFloat(state), randomFloat(state))
        state, offset = _random_float(state)
        point.append(c + offset)
    return tuple(point)


def _worley(q, period, seed):
    """worleyNoise: min(F1, 1) in cell widths at q (in cells), searching the home cube and the 26 around it."""
    home = [math.floor(c) for c in q]
    return min([1.0] + [math.dist(q, _feature_point((home[0] + dx, home[1] + dy, home[2] + dz), period, seed))
                        for dz in (-1, 0, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)])


def worley_distance_and_inverted():
    period, seed = 4, 10                    # CloudShapeNoise.comp.glsl: worleyNoise(p, 4, 10u), the base channel
    z = 0.4125                              # the slice, in cells: q = p * period, so p.z = z / 4
    x0, y0 = 0.0, 0.8                       # the window's corner, in cells; it is 4 by 2 cells
    near, far = 0.125, 0.5                  # how far off the slice a point may lie and still be marked: solid, hollow
    cols, rows, cell = 4, 2, 90

    def f1(x, y):
        return _worley((x0 + x, y0 + y, z), period, seed)

    xs, ys = np.linspace(0, cols, cols * 48 + 1), np.linspace(0, rows, rows * 48 + 1)
    distance = np.array([[f1(x, y) for x in xs] for y in ys])

    # The feature points of the three layers of cubes the slice can see, placed in the window.
    marked = []
    for cx in range(math.floor(x0) - 1, math.floor(x0) + cols + 1):
        for cy in range(math.floor(y0) - 1, math.floor(y0) + rows + 2):
            for cz in range(math.floor(z) - 1, math.floor(z) + 2):
                p = _feature_point((cx, cy, cz), period, seed)
                off = abs(p[2] - z)
                u, v = p[0] - x0, p[1] - y0
                assert _worley(p, period, seed) == 0.0                   # F1 is 0 at each feature point
                if off < far and 0 <= u <= cols and 0 <= v <= rows:
                    marked.append((u, v, off))
    solid = [m for m in marked if m[2] < near]
    assert len(solid) >= 5 and len(marked) > len(solid)
    for u, v, off in solid:                 # in the slice, F1 under a point is its distance off the slice
        assert abs(f1(u, v) - off) < 1e-9 and f1(u, v) < near
    for i, (u, v, _) in enumerate(marked):  # every marker inside the frame, none on another
        assert min(u, v, cols - u, rows - v) * cell >= 10
        assert all(math.hypot(u - a, v - b) * cell >= 11 for a, b, _ in marked[i + 1:])
    assert distance.max() <= 1.0 and distance.min() >= 0.0
    for dx, dy, dz in [(period, 0, 0), (0, period, 0), (0, 0, period)]:    # one period along any axis: it tiles
        assert abs(_worley((1.3, 2.7, z), period, seed) - _worley((1.3 + dx, 2.7 + dy, z + dz), period, seed)) < 1e-12

    f = Figure("worley-distance-and-inverted", 880, 340,
               "A slice through Worley noise four cells across, one point per cube. On the left, F1, the distance to the "
               "nearest point: near 0, dark, where a point lies in or near the slice, lighter toward the seams; on the right, "
               "max(1 - F1, 0), what clouds use: a round, bright blob around each point, fainter for points farther off the "
               "slice, with dark seams between them.",
               kind="computed plot",
               source="28-Clouds.md, section 7 (Worley noise, in three dimensions)",
               parameters={"function": "CloudShapeNoise's worleyNoise(p, 4, 10u) with Random.glsl's pcgHash, in 3D",
                           "slice": f"z = {z} cells (p.z = {z / period})", "windowCells": [x0, y0, x0 + cols, y0 + rows],
                           "solidMarkersWithin": near, "hollowMarkersWithin": far, "bands": 8})
    levels = np.linspace(0, 1, 9)
    shades = [mix_colour(BLUE, FILL, (i + 0.5) / 8) for i in range(8)]   # 0 dark, 1 light: bright blobs, dark seams
    panels = [(36, distance, "F1 (distance to the nearest point)"),
              (484, np.maximum(1 - distance, 0), "max(1 − F1, 0) (what clouds use)")]
    top = 50
    for left, values, title in panels:
        f.text(left + cols * cell / 2, 26, title, 15, "bold", anchor="middle")
        clip = f"worley-panel-{left}"
        f.defs.append(f'<clipPath id="{clip}"><rect x="{left}" y="{top}" width="{cols * cell}" height="{rows * cell}"/></clipPath>')
        paths = contour_paths(xs, ys, values, levels, lambda x, y, left=left: (left + x * cell, top + y * cell))
        body = "".join(f'<path d="{d}" fill="{shade}" fill-rule="evenodd"/>' for d, shade in zip(paths, shades))
        f.add(f'<g clip-path="url(#{clip})">{body}</g>')
        f.rect(left, top, cols * cell, rows * cell, "none", INK, 1.4)
        for u, v, off in marked:
            point_marker(f, left + u * cell, top + v * cell, off < near)

    # The two notes under the panels, and the shared scale.
    note_y = top + rows * cell + 26
    entries = [(True, "a point near the slice"), (False, "a point farther off it")]
    widths = [17 + measure(words, 14)[0] for _, words in entries]
    x = 36 + (cols * cell - sum(widths) - 26) / 2       # the two entries centred under the left panel
    for (solid, words), width in zip(entries, widths):
        point_marker(f, x + 5, note_y, solid)
        f.text(x + 17, note_y, words, 14)
        x += width + 26
    f.text(484 + cols * cell / 2, note_y, "around each point: a blob,", 14, anchor="middle")
    f.text(484 + cols * cell / 2, note_y + 20, "fainter the farther off the slice it lies", 14, anchor="middle")
    scale_y, sx, sw = note_y + 52, 300, 280
    for i, shade in enumerate(shades):
        f.rect(sx + i * sw / 8, scale_y, sw / 8, 16, shade)
    f.rect(sx, scale_y, sw, 16, "none", LINE, 1)
    f.text(sx - 10, scale_y + 8, "0", 14, fill=GRAY, anchor="end")
    f.text(sx + sw + 10, scale_y + 8, "1", 14, fill=GRAY)
    return f


def point_marker(f, x, y, solid):
    """A feature point: solid in or near the slice, a small hollow ring farther off it."""
    if solid:
        f.circle(x, y, 4, WHITE, INK, 1.4)
    else:
        f.circle(x, y, 3, "none", INK, 1.2)


def cumulus_height_profile():
    cumulus = (0.0, 0.10, 0.60, 0.95)       # CloudMarch's CUMULUS

    def smoothstep(a, b, x):
        t = min(max((x - a) / (b - a), 0.0), 1.0)
        return t * t * (3 - 2 * t)

    def profile(h):
        return smoothstep(cumulus[0], cumulus[1], h) * (1.0 - smoothstep(cumulus[2], cumulus[3], h))

    assert profile(0.0) == 0 and profile(0.95) == 0 and profile(1.0) == 0
    assert all(profile(h) == 1 for h in (0.10, 0.35, 0.60))
    assert abs(profile(0.05) - 0.5) < 1e-12 and abs(profile(0.775) - 0.5) < 1e-12
    layer = TOP - BOTTOM                    # the table's metres, for the default 1500-4000 m layer
    assert [round(h * layer) for h in cumulus[1:]] == [250, 1500, 2375]

    f = Figure("cumulus-height-profile", 760, 424,
               "A cumulus's profile, with height in the layer upward and the share of the shape kept across. From 0 to "
               "0.10 it rises, a smoothstep from 0 to 1; from 0.10 to 0.60 the shape is kept whole; from 0.60 to 0.95 it "
               "falls, a smoothstep from 1 back to 0; above 0.95 nothing is kept.",
               kind="computed plot",
               source="28-Clouds.md, section 9 (Step 2, the type, a profile over height)",
               parameters={"heights": list(cumulus), "profile": "smoothstep(a, b, h) * (1 - smoothstep(c, d, h))"})
    left, bottom, wide, tall = 110, 336, 250, 286

    def px(share):
        return left + share * wide

    def py(h):
        return bottom - h * tall

    f.line([(px(0), py(1.0)), (px(1), py(1.0))], GRID, 1)
    f.line([(px(1), py(0)), (px(1), py(1.0))], GRID, 1, "4 4")
    curve = [(px(profile(i / 400)), py(i / 400)) for i in range(401)]
    f.polygon([(px(0), py(0))] + curve + [(px(0), py(1.0))], BLUE_FILL)
    f.line(curve, BLUE, 3)
    f.line([(px(0), py(0)), (px(0), py(1.04))], INK, 1.6)
    f.arrow([(px(0), py(0)), (px(1.12), py(0))], INK, 1.6, 10)
    for h, label in [(0.0, "0.00"), (0.10, "0.10"), (0.60, "0.60"), (0.95, "0.95"), (1.0, "1.00")]:
        f.line([(px(0) - 5, py(h)), (px(0), py(h))], INK, 1.3)
        f.text(px(0) - 10, py(h) + (-5 if h == 1.0 else 4 if h == 0.95 else 0), label, 13.5, fill=GRAY, anchor="end")
    for share in (0, 0.5, 1):
        f.text(px(share), py(0) + 20, f"{share:g}", 13.5, fill=GRAY, anchor="middle")
    f.text(px(0), py(1.0) - 26, "height in the layer", 14, fill=GRAY, anchor="middle")
    f.text(px(0.5), py(0) + 44, "the share of the shape kept: 0 at the axis, 1 at the line", 14, fill=GRAY, anchor="middle")
    f.text(px(0.5), py(0) + 68, "a cumulus: 0, 0.10, 0.60, 0.95", 14, "italic", GRAY, "middle")

    # Each part of the profile, bracketed beside the plot.
    bx = px(1) + 46
    for low, high, name, words in [(0.95, 1.0, "gone:", "nothing above 0.95"),
                                   (0.60, 0.95, "falls:", "a smoothstep from 1 back to 0"),
                                   (0.10, 0.60, "full:", "the shape is kept whole"),
                                   (0.0, 0.10, "rises:", "a smoothstep from 0 to 1")]:
        f.line([(bx - 6, py(low) - 2), (bx, py(low) - 2), (bx, py(high) + 2), (bx - 6, py(high) + 2)], LINE, 1.3)
        y = py((low + high) / 2)
        box = f.text(bx + 14, y, name, 15, "bold", BLUE)
        f.text(box[2] + 7, y, words, 15)
    return f


FIGURES = [rays_through_the_cloud_layer, jittered_first_step, worley_distance_and_inverted, cumulus_height_profile]
