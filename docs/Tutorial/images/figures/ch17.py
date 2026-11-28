"""Chapter 17, Shadows: authored figures.

@author Gary Yang
@brief Figures for 17-Shadows.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def runs(f, x, y, parts, size=15, anchor="start"):
    """One line made of (text, font, colour) runs, such as prose with a code name in it."""
    widths = [measure(text, size, font)[0] for text, font, _ in parts]
    gap = size * 0.36
    total = sum(widths) + gap * (len(parts) - 1)
    left = {"start": x, "middle": x - total / 2, "end": x - total}[anchor]
    for (text, font, colour), width in zip(parts, widths):
        f.text(left, y, text, size, font, colour)
        left += width + gap
    return left - gap


def box(f, x, y, w, h, title, notes=(), kind="pass", font="mono-bold"):
    """The kit's node with a title and up to two note lines, each a list of (text, font) runs."""
    if not notes:
        node(f, x, y, w, h, title, "", kind, font)
        return
    node(f, x, y, w, h, "", "", kind)
    first = y - 9 * len(notes)
    f.text(x + w / 2, first, title, 15, font, anchor="middle")
    for i, parts in enumerate(notes):
        runs(f, x + w / 2, first + 22 + 18 * i, [(t, fnt, GRAY) for t, fnt in parts], 13, "middle")


def barrier_bar(f, x, y, w, before, after):
    """A barrier between two steps: a teal band naming what it orders before and after."""
    f.rect(x, y - 13, w, 26, TEAL_FILL, TEAL, 1.3, 13)
    runs(f, x + w / 2, y, [("barrier:", "bold", TEAL), (before, "regular", INK), ("→", "regular", TEAL),
                           (after, "regular", INK)], 13.5, "middle")


def a_frame_with_a_shadow_pass():
    f = Figure("a-frame-with-a-shadow-pass", 880, 582,
               "The demo's Record with shadows: after the host writes, ShadowMaps::Record fits each cascade into "
               "ShadowData and, between two barriers, draws a depth-only pass from the sun into one layer of the shadow "
               "map per cascade. In the scene pass, Mesh.frag.glsl samples the map at set 0 binding 4 and dims only the "
               "sun's light.",
               source="17-Shadows.md, What you are actually writing")
    runs(f, 40, 30, [("demo", "regular", GRAY), ("Record", "mono", GRAY), ("(Chapter 09)", "regular", GRAY)], 14)
    f.rect(24, 46, 832, 516, FILL, LINE, 1.3, 12)

    main_x, main_w = 48, 404
    data_x, data_w = 560, 256
    centre = main_x + main_w / 2

    r1 = 86
    box(f, main_x, r1, main_w, 40, "WriteFrameData, WriteLights")
    f.text(data_x, r1, "host writes, as in Chapter 16", 13.5, "italic", GRAY)

    # RecordShadows: the sun's pass, which leaves the shadow map ready to sample.
    top, bottom = 124, 366
    f.rect(main_x, top, 832 - main_x, bottom - top, WHITE, LINE, 1.3, 10)
    runs(f, main_x + 16, top + 22, [("RecordShadows", "mono-bold", INK), ("→", "regular", GRAY),
                                    ("ShadowMaps::Record", "mono-bold", INK)], 15)
    inner_x, inner_w = main_x + 16, main_w - 16
    inner_centre = inner_x + inner_w / 2
    ra, rb, rc, rd = 190, 240, 290, 340
    box(f, inner_x, ra, inner_w, 46, "fit each cascade to the camera", [[("on the CPU", "regular")]], font="bold")
    box(f, inner_x, rc, inner_w, 46, "for each cascade: a depth-only pass",
        [[("from the sun, into one layer of the map", "regular")]], font="bold")
    barrier_bar(f, inner_x, rb, inner_w, "last frame's sampling", "depth writes")
    barrier_bar(f, inner_x, rd, inner_w, "depth writes", "fragment-shader sampling")

    box(f, data_x, ra, data_w, 46, "ShadowData", [[("set 0 binding 3", "regular")]], "data")
    f.arrow([(inner_x + inner_w, ra), (data_x, ra)])

    # The shadow map: one image, one layer per cascade, drawn as a short stack.
    layer_w, layer_h, step = 132, 40, 7
    map_x = data_x
    for i in range(3, -1, -1):
        f.rect(map_x + i * step, rc - layer_h / 2 - i * step + 4, layer_w, layer_h, GOLD_FILL, GOLD, 1.3, 6)
    f.text(map_x + layer_w / 2, rc + 4, "shadow map", 15, "bold", anchor="middle")
    f.text(map_x + layer_w + 3 * step + 14, rc - 8, "one layer", 13, fill=GRAY)
    f.text(map_x + layer_w + 3 * step + 14, rc + 10, "per cascade", 13, fill=GRAY)
    f.arrow([(inner_x + inner_w, rc), (map_x, rc)])

    # The scene pass, which samples it.
    r3, r3b, r4 = 406, 468, 530
    box(f, main_x, r3, main_w, 40, "beginScenePass")
    draws_x = main_x + 40
    box(f, draws_x, r3b, main_w - 40, 46, "RecordDraws", [[("Mesh.frag.glsl", "mono"), ("samples the map", "regular")]])
    box(f, main_x, r4, main_w, 40, "endScenePass, handBackSceneTarget")
    map_centre = map_x + layer_w / 2
    f.arrow([(map_centre, rc + layer_h / 2 + 4), (map_centre, r3b), (main_x + main_w, r3b)], GOLD, 1.8)
    f.text(map_centre + 12, (rc + r3b) / 2 + 8, "set 0 binding 4", 13.5, fill=GOLD_TEXT)
    f.text(main_x + main_w + 20, r3b + 22, "dims only the sun's light where", 13.5, "italic", GRAY)
    f.text(main_x + main_w + 20, r3b + 40, "the map says something is in the way", 13.5, "italic", GRAY)

    # The order, top to bottom.
    f.arrow([(centre, r1 + 20), (centre, top)], GRAY, 1.5, 9)
    f.arrow([(inner_centre, ra + 23), (inner_centre, rb - 13)], GRAY, 1.5, 9)
    f.arrow([(inner_centre, rb + 13), (inner_centre, rc - 23)], GRAY, 1.5, 9)
    f.arrow([(inner_centre, rc + 23), (inner_centre, rd - 13)], GRAY, 1.5, 9)
    f.arrow([(centre, bottom), (centre, r3 - 20)], GRAY, 1.5, 9)
    draws_centre = draws_x + (main_w - 40) / 2
    f.arrow([(draws_centre, r3 + 20), (draws_centre, r3b - 23)], GRAY, 1.5, 9)
    f.arrow([(draws_centre, r3b + 23), (draws_centre, r4 - 20)], GRAY, 1.5, 9)
    return f


def crosses(box, segments, pad=0):
    """Whether any straight segment ((x, y), (x, y)) passes through a text box (x0, y0, x1, y1), grown by pad. The
    driver checks text against text and the card; this checks it against the drawing's lines."""
    x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    for (ax, ay), (bx, by) in segments:
        # Liang-Barsky: clip the segment's parameter range [0, 1] against the box's four sides.
        dx, dy, low, high = bx - ax, by - ay, 0.0, 1.0
        for p, q in [(-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)]:
            if p == 0:
                if q < 0:
                    break
            elif p < 0:
                low = max(low, q / p)
            else:
                high = min(high, q / p)
            if low > high:
                break
        else:
            return True
    return False


def sun(f, x, y, r=13):
    """The sun glyph Chapter 15's shading figure uses."""
    for i in range(10):
        ray = unit(36 * i)
        f.line([(x + ray[0] * (r + 5), y + ray[1] * (r + 5)), (x + ray[0] * (r + 13), y + ray[1] * (r + 13))], GOLD, 2)
    f.circle(x, y, r, GOLD_SOFT, GOLD, 1.6)


def light_box_around_the_view_slice():
    # The chapter's defaults: maxDistance 120 m, casterReach 200 m, the test scene's camera (a 60 degree vertical lens,
    # 3 m up, tipped down 8 degrees). The low sun and the tower are this figure's choice: section 2's "tower behind you,
    # between you and a low sun".
    max_distance, caster_reach, half_fov = 120.0, 200.0, math.radians(30.0)
    eye_height, tilt, elevation = 3.0, math.radians(-8.0), math.radians(15.0)
    tower_x, tower_height, tower_width = -100.0, 40.0, 8.0

    # World: x forward along the ground, y up, the camera at (0, eye_height). Light space: x along the sunlight, which
    # travels forward and down at `elevation`; y across it. Everything is drawn in light space, camera at the origin.
    d = (math.cos(elevation), -math.sin(elevation))
    n = (math.sin(elevation), math.cos(elevation))

    def light(wx, wy):
        rx, ry = wx, wy - eye_height
        return (rx * d[0] + ry * d[1], rx * n[0] + ry * n[1])

    def view(depth, across):   # a point of the camera's vertical section, in world space
        axis, side = (math.cos(tilt), math.sin(tilt)), (-math.sin(tilt), math.cos(tilt))
        return (axis[0] * depth + side[0] * across, eye_height + axis[1] * depth + side[1] * across)

    reach = max_distance * math.tan(half_fov)
    corners = [light(*view(0.0, 0.0)), light(*view(max_distance, reach)), light(*view(max_distance, -reach))]
    low_x, high_x = min(c[0] for c in corners), max(c[0] for c in corners)
    low_y, high_y = min(c[1] for c in corners), max(c[1] for c in corners)
    near = low_x - caster_reach
    assert low_x == corners[0][0]   # with the sun behind it, the camera is the slice's point nearest the sun

    # The tower's top casts along the light onto the ground inside the slice, in front of the camera.
    shadow_world = tower_x + tower_height / math.tan(elevation)
    top, shadow = light(tower_x, tower_height), light(shadow_world, 0.0)
    # The shadow tip relative to the camera is (shadow_world, -eye_height): its depth along the view axis, and its
    # offset across it, which the lens keeps within depth * tan(fov / 2).
    ahead = shadow_world * math.cos(tilt) - eye_height * math.sin(tilt)
    across = -shadow_world * math.sin(tilt) - eye_height * math.cos(tilt)
    assert abs(shadow[1] - top[1]) < 1e-9 and 0 < ahead < max_distance and abs(across) < ahead * math.tan(half_fov)
    assert near < top[0] < low_x    # the tower is outside the slice but inside the pulled-back box

    f = Figure("light-box-around-the-view-slice", 880, 464,
               "Light space seen from the side, the sunlight running left to right: the light's box is tight around the "
               "slice of the view across the light, and its near plane is pulled back towards the sun by casterReach. So"
               " a tower outside the slice, nearer the sun, still shades the ground inside it.",
               source="17-Shadows.md, section 2 (The light's camera: fitted to what you can see)",
               parameters={"maxDistanceMetres": max_distance, "casterReachMetres": caster_reach, "verticalFovDegrees": 60,
                           "cameraHeightMetres": eye_height, "cameraTiltDegrees": -8, "sunElevationDegrees": 15,
                           "towerMetres": {"behindCamera": -tower_x, "height": tower_height},
                           "shadowTipMetresAhead": round(shadow_world, 1)})
    scale = 636 / (high_x - near)
    left, top_px = 60, 118

    def px(p):
        return (left + (p[0] - near) * scale, top_px + (high_y - p[1]) * scale)

    box_left, box_top = px((near, high_y))
    box_right, box_bottom = px((high_x, low_y))
    tight_left = px((low_x, 0))[0]

    def ground_at(x_px):   # where the ground line crosses a given x on the page
        a, b = px(light(-300.0, 0.0)), px(light(200.0, 0.0))
        t = (x_px - a[0]) / (b[0] - a[0])
        return (x_px, a[1] + (b[1] - a[1]) * t)

    f.rect(box_left, box_top, box_right - box_left, box_bottom - box_top, TEAL_FILL, "none", opacity=0.45)
    f.polygon([px(c) for c in corners], BLUE_FILL, BLUE, 1.6)

    # The ground, tilted in light space because the sun is low, with the drafting hatch on its far side.
    a, b = ground_at(box_left), ground_at(box_right)   # the ground leaves the box through its bottom, on the left
    ga = ground_at(max(box_left, a[0] + (b[0] - a[0]) * (box_bottom - a[1]) / (b[1] - a[1])))
    gb = ground_at(box_right)
    length = math.hypot(gb[0] - ga[0], gb[1] - ga[1])
    ux, uy = (gb[0] - ga[0]) / length, (gb[1] - ga[1]) / length
    hatch = []
    s = 24.0
    while s < length - 10:
        x, y = ga[0] + ux * s, ga[1] + uy * s
        stroke = [(x + 6, y + 2), (x - 4, y + 14)]
        # The ground stops at the box: a stroke that would cross its bottom is cut short there.
        t = min(1.0, (box_bottom - 3 - stroke[0][1]) / (stroke[1][1] - stroke[0][1]))
        stroke[1] = (stroke[0][0] + (stroke[1][0] - stroke[0][0]) * t, stroke[0][1] + (stroke[1][1] - stroke[0][1]) * t)
        if t > 0.35 and stroke[1][0] > box_left + 3:
            f.line(stroke, LINE, 1.1)
            hatch.append(stroke)
        s += 17
    f.line([ga, gb], INK, 2)

    # The tight box's near side, dashed, and the box the fit makes.
    f.line([(tight_left, box_top), (tight_left, box_bottom)], BLUE, 1.5, "6 5")
    f.rect(box_left, box_top, box_right - box_left, box_bottom - box_top, "none", TEAL, 2)

    # The tower, standing square to the ground, and the sunlight that grazes its top.
    half = tower_width / 2
    outline = [px(light(tower_x - half, 0.0)), px(light(tower_x - half, tower_height)),
               px(light(tower_x + half, tower_height)), px(light(tower_x + half, 0.0))]
    f.polygon(outline, HAIR, GRAY, 1.4)
    tip, hit = px(top), px(shadow)
    f.line([(box_left + 2, tip[1]), hit], GOLD, 1.8, "7 5")
    f.circle(hit[0], hit[1], 5, INK, WHITE, 1.6)

    # The camera at the slice's apex.
    cam = px(corners[0])
    f.circle(cam[0], cam[1], 6, BLUE, WHITE, 1.8)

    # Sunlight, left to right, above everything.
    sun(f, 52, 58)
    for x0 in (92, 312, 532):
        f.arrow([(x0, 58), (x0 + 184, 58)], GOLD, 2, 12)
    f.text(856, 30, "light space, seen from the side", 14, "italic", GRAY, "end")

    # Labels inside the box are placed by computation and checked against every line they could sit on: the slice's
    # edges, the ground and its hatch, the box, the dashed line and the sunlight's ray.
    upper, lower = px(corners[1]), px(corners[2])
    slice_edges = [(cam, upper), (upper, lower), (lower, cam)]
    box_edges = [((box_left, box_top), (box_right, box_top)), ((box_right, box_top), (box_right, box_bottom)),
                 ((box_right, box_bottom), (box_left, box_bottom)), ((box_left, box_bottom), (box_left, box_top))]
    lines_drawn = slice_edges + box_edges + [(ga, gb), ((tight_left, box_top), (tight_left, box_bottom)),
                                             ((box_left + 2, tip[1]), hit)] + [tuple(s) for s in hatch]

    widths = {}   # measuring outlines text, which is slow, and the searches below try thousands of places

    def text_box(x, y, string, font="regular", anchor="middle", pad=4):
        if (string, font) not in widths:
            widths[(string, font)] = measure(string, 13.5, font)[0]
        w = widths[(string, font)]
        x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
        return (x0 - pad, y - 8 - pad, x0 + w + pad, y + 5 + pad)

    def in_slice(box):
        def side(p, a, b):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        points = [(box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])]
        triangle = [(cam, upper, lower), (upper, lower, cam), (lower, cam, upper)]   # each edge and the corner facing it
        return all(side(p, a, b) * side(c, a, b) > 0 for p in points for a, b, c in triangle)

    def overlaps(a, b):
        return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])

    # The slice's name goes in its upper wedge, between its edges and above the ground, as high as it fits.
    names = ["slice of", "the view"]

    def upper_edge_x(y):
        return cam[0] + (upper[0] - cam[0]) * (cam[1] - y) / (cam[1] - upper[1])

    def far_edge_x(y):
        return upper[0] + (lower[0] - upper[0]) * (y - upper[1]) / (lower[1] - upper[1])

    def name_boxes(y):
        return [text_box((upper_edge_x(y + 18 * i - 9) + far_edge_x(y + 18 * i - 9)) / 2, y + 18 * i, name, "bold")
                for i, name in enumerate(names)]
    label_y = next(y for y in range(int(box_top) + 20, int(cam[1]))
                   if all(in_slice(b) and not crosses(b, lines_drawn) for b in name_boxes(y)))
    taken = name_boxes(label_y)
    for i, name in enumerate(names):
        middle = (taken[i][0] + taken[i][2]) / 2
        f.text(middle, label_y + 18 * i, name, 13.5, "bold", BLUE, "middle")

    # The shadow's label: wholly inside the slice, clear of every line, as near the shadow as it goes, with a leader.
    shadow_words = ["its shadow,", "inside the slice"]
    best = None
    for y in range(int(box_top) + 12, int(box_bottom) - 30, 2):
        for x in range(int(cam[0]), int(box_right), 2):
            boxes = [text_box(x, y + 18 * i, word) for i, word in enumerate(shadow_words)]
            if any(not in_slice(b) or crosses(b, lines_drawn) or any(overlaps(b, t) for t in taken) for b in boxes):
                continue
            below = boxes[0][1] > hit[1]
            anchor = (x, boxes[0][1] + 2) if below else (x, boxes[-1][3] - 2)
            reach = math.hypot(anchor[0] - hit[0], anchor[1] - hit[1])
            if reach > 22 and (best is None or reach < best[0]):
                best = (reach, x, y, anchor)
    _, label_x, label_y, anchor = best
    reach = math.hypot(anchor[0] - hit[0], anchor[1] - hit[1])
    ux, uy = (anchor[0] - hit[0]) / reach, (anchor[1] - hit[1]) / reach
    f.line([(hit[0] + ux * 8, hit[1] + uy * 8), anchor], INK, 1.1)
    drawn = f.lines(label_x, label_y, shadow_words, 13.5, anchor="middle", spacing=18)
    assert all(in_slice(b) and not crosses(b, lines_drawn, 3) for b in drawn)

    # The rest sit where the drawing leaves room; each is checked against the lines, the tower's outline included.
    tower_edges = list(zip(outline, outline[1:] + outline[:1]))
    ground_x = ga[0] + 40
    ground_y = ground_at(ground_x + measure("ground", 13.5)[0])[1] - 16   # the ground rises to the right
    placed = [f.text(ground_x, ground_y, "ground", 13.5, fill=GRAY),
              f.text(tip[0], outline[1][1] - 18, "a tower outside the slice", 13.5, anchor="middle"),
              # The dashed line: where the box's near side would be without casterReach.
              f.text(tight_left - 10, box_top + 22, "near plane without casterReach", 13.5, fill=BLUE, anchor="end")]
    assert not any(crosses(b, lines_drawn + tower_edges, 3) for b in placed)
    y_dim = box_top - 18
    f.arrow([(tight_left, y_dim), (box_left, y_dim)], TEAL, 1.6, 10)
    f.line([(tight_left, y_dim - 6), (tight_left, y_dim + 6)], TEAL, 1.4)
    f.text((box_left + tight_left) / 2, y_dim - 14, "casterReach, towards the sun", 13.5, "bold", TEAL, "middle")
    f.text(box_left, box_bottom + 20, "near plane", 13.5, fill=TEAL)
    f.lines(tight_left, box_bottom + 20, ["camera: the slice's point", "nearest the sun"], 13.5, fill=BLUE,
            anchor="middle", spacing=18)
    f.text(box_right, box_bottom + 20, "far plane", 13.5, fill=TEAL, anchor="end")
    x_dim = box_right + 18
    f.arrow([(x_dim, box_top), (x_dim, box_bottom)], TEAL, 1.6, 10, both=True)
    f.lines(x_dim + 12, (box_top + box_bottom) / 2 - 18, ["tight around", "the slice,", "across the light"], 13.5,
            "bold", TEAL, spacing=18)
    return f


def shadow_acne_from_flat_steps():
    # Seen as the shadow map sees it: the sunlight straight down the page, one column per shadow-map texel. The map keeps
    # one depth per texel, the surface's depth at the texel's centre, so its steps are flat; a surface tilted away from
    # the sun leaves every step's far half behind the stored value.
    texels, cell, tilt = 6, 72.0, math.radians(22.0)
    left, top = 40.0, 122.0
    slope = math.tan(tilt)

    def surface(x):
        return top + (x - left) * slope

    f = Figure("shadow-acne-from-flat-steps", 880, 384,
               "A surface tilted away from the sun, drawn with the sunlight running straight down the page and one "
               "column per shadow-map texel, and the one flat depth the map stores per texel, the surface's depth at the"
               " texel's centre. In every texel the surface's far half tests behind the stored value and shadows itself.",
               source="17-Shadows.md, section 7 (Shadow acne, peter-panning, and bias)",
               parameters={"texels": texels, "surfaceTiltDegrees": 22})
    right = left + texels * cell
    bottom = surface(right) + 30

    # Sunlight, straight down the page.
    f.text(left, 30, "sunlight", 14, fill=GOLD_TEXT)
    for i in range(texels):
        x = left + (i + 0.5) * cell
        f.arrow([(x, 46), (x, 84)], GOLD, 2, 11)

    # The texels: columns, and a bracket naming one.
    for i in range(texels + 1):
        x = left + i * cell
        f.line([(x, 100), (x, bottom)], GRID, 1.2)
    f.line([(left, 100), (right, 100)], LINE, 1.2)
    f.line([(left, bottom), (right, bottom)], LINE, 1.2)
    f.line([(left, bottom - 6), (left, bottom + 6), (left + cell, bottom + 6), (left + cell, bottom - 6)], GRAY, 1.4)

    # The self-shadowed wedge in each texel, between the stored step and the surface below it.
    for i in range(texels):
        centre = left + (i + 0.5) * cell
        stored = surface(centre)
        far = left + (i + 1) * cell
        f.polygon([(centre, stored), (far, stored), (far, surface(far))], RED, opacity=0.16)

    # The surface: each texel's near half lit, its far half self-shadowed.
    for i in range(texels):
        a, centre, b = left + i * cell, left + (i + 0.5) * cell, left + (i + 1) * cell
        f.line([(a, surface(a)), (centre, surface(centre))], INK, 3)
        f.line([(centre, surface(centre)), (b, surface(b))], RED, 3.4)
    # The stored depth: one flat step per texel, at the surface's depth at the texel's centre.
    for i in range(texels):
        a, centre, b = left + i * cell, left + (i + 0.5) * cell, left + (i + 1) * cell
        f.line([(a + 3, surface(centre)), (b - 3, surface(centre))], GOLD, 2.6)
        f.circle(centre, surface(centre), 4, GOLD, WHITE, 1.4)

    # Labels on the drawing.
    f.text(left, bottom + 24, "one shadow-map texel", 13.5, fill=GRAY)
    f.arrow([(right + 12, top + 10), (right + 12, bottom - 16)], LINE, 1.4, 10)
    f.lines(right + 24, (top + bottom) / 2 - 10, ["farther", "from the sun"], 13.5, fill=GRAY, spacing=18)

    # The key, in the chapter's words.
    kx, y = 646, 150
    rows = [(GOLD, 2.6, "stored depth per texel:", "flat steps, the surface's depth", "at the texel's centre"),
            (INK, 3, "surface, nearer the sun", "than the stored value: lit", None),
            (RED, 3.4, "surface on the far half of the", "step: tests \"behind\" the stored", "value, self-shadowed")]
    for colour, width, *texts in rows:
        f.line([(kx - 40, y), (kx - 10, y)], colour, width)
        lines = [t for t in texts if t]
        f.lines(kx, y, lines, 13.5, spacing=18)
        y += 18 * len(lines) + 24
    return f


def smallest_sphere_around_a_slice():
    def sphere(n, far, k2):
        """fitStable's sphere: its centre's depth on the view axis and its radius, for a slice between n and far."""
        centre = min(0.5 * (n + far) * (1 + k2), far)
        far_sq = (far - centre) ** 2 + far * far * k2
        near_sq = (centre - n) ** 2 + n * n * k2
        return centre, math.sqrt(max(far_sq, near_sq)), far_sq, near_sq

    # The test scene's lens, which the chapter works through: 60 degrees vertical, 16:9, a 14-34 m slice, 2048 texels.
    tan_y = math.tan(math.radians(30.0))
    lens_k2 = tan_y ** 2 * (1 + (16 / 9) ** 2)
    lens = (14.0, 34.0, lens_k2)
    z_lens, r_lens, _, _ = sphere(*lens)
    assert abs(lens_k2 - 1.39) < 0.005                      # "k² ≈ 1.39"
    assert z_lens == lens[1] and abs(r_lens - 40.04) < 0.005  # on its far plane, "radius about 40.04 m", f·k
    assert abs(2 * r_lens / 2048 * 100 - 3.91) < 0.005      # "2r / 2048 ≈ 3.91 cm"
    # The formula's other branch needs a narrow lens and a long slice, (n + f)(1 + k²) / 2 < f: a 30 degree vertical lens
    # in 16:9 and a 4-20 m slice.
    narrow_k2 = math.tan(math.radians(15.0)) ** 2 * (1 + (16 / 9) ** 2)
    narrow = (4.0, 20.0, narrow_k2)
    z_narrow, r_narrow, far_sq, near_sq = sphere(*narrow)
    assert z_narrow < narrow[1] and abs(far_sq - near_sq) < 1e-9   # inside the slice, near and far corners equally far
    # The drawing is a cut through the view axis and one corner, where a corner at depth d is d·k from the axis, so a
    # lens opens wider here than its vertical angle: 2·atan(k) from corner to corner, "57°" and "99°" in the text.
    narrow_across = 2 * math.degrees(math.atan(math.sqrt(narrow_k2)))
    lens_across = 2 * math.degrees(math.atan(math.sqrt(lens_k2)))
    assert round(narrow_across) == 57 and round(lens_across) == 99

    f = Figure("smallest-sphere-around-a-slice", 880, 452,
               "Two frustum slices cut lengthwise through the view axis and one corner, each inside the smallest "
               "circle around its corners, centred on the view axis. With a narrow 30 degree lens in 16:9, 57 degrees "
               "from corner to corner, and a long 4 to 20 m slice, the centre lies inside the slice and every corner is "
               "on the circle. With the test scene's 60 degree lens in 16:9, 99 degrees from corner to corner, and a "
               "14 to 34 m slice, the centre stops on the far plane and the radius is about 40.04 m.",
               kind="computed plot", source="17-Shadows.md, section 12 (Shimmering, and holding the shadow still)",
               parameters={"testLens": {"verticalFovDegrees": 60, "aspect": "16:9", "near": lens[0], "far": lens[1],
                                        "k2": round(lens_k2, 4), "centre": round(z_lens, 3), "radius": round(r_lens, 3)},
                           "narrowLens": {"verticalFovDegrees": 30, "aspect": "16:9", "near": narrow[0],
                                          "far": narrow[1], "k2": round(narrow_k2, 4), "centre": round(z_narrow, 3),
                                          "radius": round(r_narrow, 3)}})
    diameter, axis_y = 252.0, 208.0
    circles, segments = [], []   # every circle and straight line drawn, so no label may sit on one

    def clear_of_circles(box, pad=3):
        x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
        for cx, cy, r in circles:
            nearest = math.hypot(max(x0 - cx, 0, cx - x1), max(y0 - cy, 0, cy - y1))
            farthest = max(math.hypot(x - cx, y - cy) for x in (x0, x1) for y in (y0, y1))
            if nearest < r < farthest:
                return False
        return True

    def panel(n, far, k2, centre_depth, radius, circle_left, captions, labels):
        k = math.sqrt(k2)
        scale = diameter / (2 * radius)
        camera_x = circle_left + (0 - (centre_depth - radius)) * scale

        def at(depth, across):
            return (camera_x + depth * scale, axis_y - across * scale)
        cx, cy = at(centre_depth, 0)
        f.circle(cx, cy, radius * scale, TEAL_FILL, TEAL, 1.8)
        circles.append((cx, cy, radius * scale))
        # The frustum's edges, faint, then the slice the sphere has to hold.
        right_x = cx + radius * scale + 18
        f.line([at(0, 0), at(far, far * k)], LINE, 1.2, "5 4")
        f.line([at(0, 0), at(far, -far * k)], LINE, 1.2, "5 4")
        outline = [at(n, n * k), at(far, far * k), at(far, -far * k), at(n, -n * k)]
        f.polygon(outline, BLUE_FILL, BLUE, 1.6)
        f.line([(at(0, 0)[0] - 14, axis_y), (right_x, axis_y)], GRAY, 1.3, "8 5")
        segments.extend([(at(0, 0), at(far, far * k)), (at(0, 0), at(far, -far * k)),
                         ((at(0, 0)[0] - 14, axis_y), (right_x, axis_y))] + list(zip(outline, outline[1:] + outline[:1])))
        for depth, across in [(n, n * k), (n, -n * k), (far, far * k), (far, -far * k)]:
            f.circle(*at(depth, across), 5, BLUE, WHITE, 1.6)
        for dx, dy in [(-6, -6), (-6, 6)]:
            f.line([(cx + dx, cy + dy), (cx - dx, cy - dy)], INK, 2.4)
        # The camera, looking right along the axis.
        cam = at(0, 0)
        f.rect(cam[0] - 30, cam[1] - 9, 20, 18, BLUE, BLUE, 1, 3)
        f.polygon([(cam[0] - 11, cam[1]), (cam[0], cam[1] - 8), (cam[0], cam[1] + 8)], BLUE, BLUE, 1)
        assert all(clear_of_circles(box) and not crosses(box, segments, 3) for box in labels(at, cx, cy))
        middle = circle_left + diameter / 2
        f.lines(middle, axis_y + diameter / 2 + 34, captions, 13.5, anchor="middle", spacing=19)

    def narrow_labels(at, cx, cy):
        n, far, k = narrow[0], narrow[1], math.sqrt(narrow[2])
        top_near, top_far = at(n, n * k), at(far, far * k)
        return [f.text(top_near[0] - 10, top_near[1] - 10, "near", 13.5, fill=BLUE, anchor="end"),
                f.text(top_far[0] + 10, top_far[1] - 14, "far corner", 13.5, fill=BLUE),
                f.text(cx - 10, cy - 16, "centre", 13.5, "bold", anchor="end")]

    def lens_labels(at, cx, cy):
        n, far, k = lens[0], lens[1], math.sqrt(lens[2])
        top_near, top_far = at(n, n * k), at(far, far * k)
        # The radius, drawn out to the circle at 35 degrees, and its length just outside the circle.
        edge = (cx + diameter / 2 * math.cos(math.radians(35)), cy - diameter / 2 * math.sin(math.radians(35)))
        f.line([(cx, cy), edge], TEAL, 1.6)
        segments.append(((cx, cy), edge))
        return [f.text(top_near[0] - 10, top_near[1] - 10, "near", 13.5, fill=BLUE, anchor="end"),
                f.text(top_far[0] + 12, top_far[1] - 10, "far corner", 13.5, fill=BLUE),
                f.text(cx + 10, cy + 20, "centre", 13.5, "bold"),
                f.text(edge[0] + 12, edge[1] - 4, "radius ≈ 40.04 m", 13.5, "bold", TEAL)]

    panel(*narrow, z_narrow, r_narrow, 84,
          ["a narrow 30° lens in 16:9, 57° from corner to", "corner, and a long 4–20 m slice: the centre lies",
           "inside the slice, every corner on the sphere"], narrow_labels)
    panel(*lens, z_lens, r_lens, 474,
          ["the test scene's 60° lens in 16:9, 99° from", "corner to corner, and a 14–34 m slice:",
           "the centre stops on the far plane"],
          lens_labels)
    f.text(440, 30, "a cut through the view axis and one corner: the smallest circle around the corners is the"
           " sphere, centre ✕", 14, "italic", GRAY, "middle")
    return f


FIGURES = [a_frame_with_a_shadow_pass, light_box_around_the_view_slice, shadow_acne_from_flat_steps, smallest_sphere_around_a_slice]
