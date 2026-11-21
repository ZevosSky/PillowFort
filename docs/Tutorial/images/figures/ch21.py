"""Chapter 21, GPU Particles: authored figures.

@author Gary Yang
@brief Figures for 21-GPU-Particles.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *

MONO_ADVANCE = 1233 / 2048  # DejaVu Sans Mono's advance per unit of size, for text that continues in another font


def barrier_pill(f, x, y, label="barrier"):
    """The teal barrier mark the queue figure uses, small, centred on (x, y)."""
    w = measure(label, 13.5, "bold")[0] + 22
    f.rect(x - w / 2, y - 11, w, 22, TEAL, TEAL, 1.2, 11)
    f.text(x, y, label, 13.5, "bold", WHITE, "middle")


def one_frame_of_the_particles():
    f = Figure("one-frame-of-the-particles", 800, 592,
               "One frame of the particles: begin, emit, simulate and end run in compute with a barrier after each, "
               "begin sizing the emit and simulate dispatches and end writing the draw's arguments. Then the counters "
               "are copied out, the scene pass draws the ground, and the particle pass draws with one indirect draw.",
               source="21-GPU-Particles.md, The problem particles pose")
    box_x, box_w, h = 128, 220, 46
    centre, note_x = box_x + box_w / 2, 378
    rows = [46, 130, 214, 298, 382, 442, 502]
    passes = [("Begin", "1 invocation", ["emit count = min(asked, free);", "dispatch sizes for emit and simulate"]),
              ("Emit", "indirect", ["pop a free slot, start a particle,", "append it to alive[current]"]),
              ("Simulate", "indirect", ["age, move, bounce;", "dead → dead list, alive → alive[next]"]),
              ("End", "1 invocation", ["draw arguments: 6 vertices × alive[next] instances"])]
    for y, (title, note, lines) in zip(rows, passes):
        node(f, box_x, y, box_w, h, title, note, "pass")
        f.lines(note_x, y - (len(lines) - 1) * 10, lines, 15, spacing=20)
    for y, title in zip(rows[4:], ["copy the counters out", "scene pass", "particle pass"]):
        node(f, box_x, y, box_w, 40, title, kind="plain")
    f.text(note_x, rows[4], "for the panel, two frames from now", 15)
    f.text(note_x, rows[5], "the ground, with depth", 15)
    call = f.text(note_x, rows[6], "one ", 15)
    code = f.text(call[2] + 4, rows[6], "vkCmdDrawIndirect", 14, "mono")
    f.text(code[2] + 3, rows[6], ", blended, depth read-only", 15)

    # The order: a barrier after each compute pass, then the copy and the two drawing passes.
    for a, b in zip(rows[:4], rows[1:5]):
        bottom = b - (20 if b == rows[4] else h / 2)
        f.arrow([(centre, a + h / 2), (centre, bottom)], GRAY, 1.6, 10)
        barrier_pill(f, centre, (a + h / 2 + bottom) / 2 - 2)
    for a, b in zip(rows[4:], rows[5:]):
        f.arrow([(centre, a + 20), (centre, b - 20)], GRAY, 1.6, 10)

    # What the GPU writes for its own later commands: begin sizes emit and simulate, end sizes the draw.
    rail = 100
    for top, targets, words in [(rows[0], [rows[1], rows[2]], ["dispatch", "sizes"]),
                                (rows[3], [rows[6]], ["draw", "arguments"])]:
        f.line([(box_x, top), (rail, top), (rail, targets[-1])], GOLD, 1.6, "6 4")
        for y in targets:
            f.arrow([(rail, y), (box_x, y)], GOLD, 1.6, 10, "6 4")
        middle = (top + targets[0]) / 2 if len(targets) > 1 else (top + targets[-1]) / 2
        f.lines(rail - 10, middle - 9, words, 13.5, "italic", GOLD_TEXT, "end", spacing=18)

    # The key, as the ocean's frame has one: what the two box fills mean.
    key_y = rows[-1] + 20 + 38  # a wider gap than between the boxes, so the key does not read as one more step
    swatch(f, box_x, key_y, "pass", "compute pass")
    swatch(f, box_x + 40 + measure("compute pass", 13.5)[0] + 36, key_y, "shader", "copy and drawing")
    return f


def equal_slices_of_a_sphere():
    slices = 3
    bounds = [1 - i / slices for i in range(slices + 1)]           # heights along +Y: 1, 2/3, 1/3, 0
    arcs = [math.acos(b) - math.acos(a) for a, b in zip(bounds, bounds[1:])]
    rings = [math.sqrt(1 - ((a + b) / 2) ** 2) for a, b in zip(bounds, bounds[1:])]

    def area(top, bottom, steps=4000):
        """The slice's surface area, summed as rings: 2 pi r along the arc."""
        a0, a1 = math.acos(top), math.acos(bottom)
        da = (a1 - a0) / steps
        return sum(2 * math.pi * math.sin(a0 + (i + 0.5) * da) * da for i in range(steps))

    # Archimedes: every slice of equal thickness h has area 2 pi h, near the pole or at the equator.
    for a, b in zip(bounds, bounds[1:]):
        assert abs(area(a, b) - 2 * math.pi * (a - b)) < 1e-6
    assert arcs[0] > arcs[1] > arcs[2] and rings[0] < rings[1] < rings[2]
    # The chapter's table after the figure: 10-degree bands of a 30-degree cone, area 2 pi (cos start - cos end).
    bands = [2 * math.pi * (math.cos(math.radians(s)) - math.cos(math.radians(s + 10))) for s in (0, 10, 20)]
    assert [round(b, 3) for b in bands] == [0.095, 0.283, 0.463]
    assert [round((1 / 3) / b, 1) for b in bands] == [3.5, 1.2, 0.7]

    f = Figure("equal-slices-of-a-sphere", 760, 330,
               "One quarter of a unit sphere, side on, cut into three slices of equal thickness h along +Y. Slice 1, "
               "near the axis, is a short ring with a long arc; slice 3, far from the axis, is a long ring with a short "
               "arc.",
               kind="computed plot", source="21-GPU-Particles.md, section 3 (Emit: directions spread evenly over a cone)",
               parameters={"slices": slices, "arcLengths": [round(a, 4) for a in arcs],
                           "ringRadiiAtMidHeight": [round(r, 4) for r in rings], "areaEach": round(2 * math.pi / slices, 4)})
    R, cx, cy = 228, 92, 300
    colors = [(GOLD, GOLD_TEXT), (BLUE, BLUE), (TEAL, TEAL)]

    def at(x, y):
        return (cx + R * x, cy - R * y)

    # The quarter disc, faint, and the three slices' boundaries.
    disc = [at(math.sin(t), math.cos(t)) for t in [i * math.pi / 2 / 90 for i in range(91)]]
    f.polygon([at(0, 0)] + disc, FILL)
    for b in bounds:
        y = at(0, b)[1]
        reach = math.sqrt(max(0.0, 1 - b * b))
        if b < 1:
            f.line([(cx - 12, y), (cx + R + 36, y)], LINE, 1.1, "5 4")
    f.line([at(0, 0), at(0, 0)], LINE)
    f.arrow([(cx, cy + 12), (cx, cy - R - 34)], INK, 1.8, 11)
    f.text(cx + 12, cy - R - 32, "+Y", 15, "bold")
    f.text(cx + 44, cy - R - 32, "one quarter of the sphere, side on; spin it round +Y", 13.5, "italic", GRAY)

    for i, (a, b) in enumerate(zip(bounds, bounds[1:])):
        stroke, ink = colors[i]
        t0, t1 = math.acos(a), math.acos(b)
        arc = [at(math.sin(t), math.cos(t)) for t in [t0 + (t1 - t0) * k / 60 for k in range(61)]]
        f.line(arc, stroke, 4.2)
        mid = (a + b) / 2
        r = math.sqrt(1 - mid * mid)
        f.line([at(0, mid), at(r, mid)], stroke, 1.4, "2 3")
        f.circle(*at(r, mid), 3.4, stroke)
        if i == slices - 1:
            f.text(cx + 14, at(0, mid)[1] - 13, "distance from the axis", 13.5, "italic", GRAY)
        # The thickness, the same for every slice.
        ya, yb = at(0, a)[1], at(0, b)[1]
        f.arrow([(56, ya + 3), (56, yb - 3)], GRAY, 1.2, 7, both=True)
        f.text(40, (ya + yb) / 2, "h", 15, "italic", GRAY, "middle")

    label_x = cx + R + 56
    lines = [("slice 1", [": close to the axis, so a short ring,", "but the surface leans over: a long arc"]),
             ("slice 2", []),
             ("slice 3", [": far from the axis, so a long ring,", "but the surface is steep: a short arc"])]
    for i, (name, rest) in enumerate(lines):
        mid = (bounds[i] + bounds[i + 1]) / 2
        y = at(0, mid)[1] - (10 if rest else 0)
        head = f.text(label_x, y, name, 15, "bold", colors[i][1])
        if rest:
            f.text(head[2] + 1, y, rest[0], 15)
            f.text(label_x + 56, y + 20, rest[1], 15)
    return f


def depth_hand_back_chain():
    f = Figure("depth-hand-back-chain", 816, 330,
               "The single-sample depth image from frame N to frame N+1 at 4x: the scene pass's resolve writes it, "
               "RecordParticles' depth tests read it, and its hand-back barrier's destination is the early and late "
               "fragment tests. That chains into frame N+1's beginScenePass barrier, whose source names the same "
               "fragment-test stages and COLOR_ATTACHMENT_OUTPUT.",
               source="21-GPU-Particles.md, section 5 (A second rendering scope, after the scene pass)")
    stage = "EARLY_|LATE_FRAGMENT_TESTS"
    name_x, name_w, note_x, pitch = 128, 172, 324, 21
    mono = 14 * MONO_ADVANCE

    def mixed(x, y, parts):
        """One line of sans and mono pieces, each (text, font, colour); a space between pieces unless the text
        already starts or ends with one, or the next piece is closing punctuation."""
        space = 4.77  # DejaVu Sans at 15 px
        for i, (text, font, ink) in enumerate(parts):
            is_mono = font.startswith("mono")
            box = f.text(x, y, text, 14 if is_mono else 15, font, ink)
            if is_mono:
                x += len(text) * mono  # trailing spaces included
            else:
                x = box[2] + space * (len(text) - len(text.rstrip(" ")))
            following = parts[i + 1][0] if i + 1 < len(parts) else ""
            if following and following[0] not in " ).,;" and not text.endswith((" ", "(")):
                x += space
        return x

    def chip(x, y, lines):
        """A barrier's stage mask, as the code writes it; y is the first line's middle."""
        w = 22 + max(len("".join(t for t, _, _ in line)) for line in lines) * mono
        h = 12 + pitch * len(lines)
        f.rect(x, y - 16, w, h, TEAL_FILL, TEAL, 1.4, 8)
        for i, line in enumerate(lines):
            mixed(x + 11, y + i * pitch, line)
        return x + w, y - 16 + h

    # Frame N: the scene pass, then the particles' scope and its hand-back. Frame N+1: Chapter 18's barrier.
    y1 = 46
    mixed(note_x, y1, [("the depth tests run on the", "regular", INK), ("multisampled", "bold", INK), ("depth; at the", "regular", INK)])
    mixed(note_x, y1 + pitch, [("end, the resolve writes this image (", "regular", INK),
                               ("COLOR_ATTACHMENT_OUTPUT", "mono", INK), (")", "regular", INK)])
    node(f, name_x, y1 + pitch / 2, name_w, 54, "scene pass", kind="pass")

    y2 = y1 + 2 * pitch + 38
    mixed(note_x, y2, [("barrier in; the particles' depth tests read this image;", "regular", INK)])
    mixed(note_x, y2 + pitch, [("hand-back: layout back to", "regular", INK), ("DEPTH_ATTACHMENT_OPTIMAL", "mono", INK),
                               (",", "regular", INK)])
    dst_y = y2 + 2 * pitch + 8
    right_a, bottom_a = chip(note_x, dst_y, [[("dst = ", "mono", GRAY), (stage, "mono-bold", TEAL)]])
    node(f, name_x, (y2 - 16 + bottom_a) / 2, name_w, bottom_a - y2 + 16, "RecordParticles", kind="pass",
         title_font="mono-bold", size=14)

    y3 = bottom_a + 52
    rail = right_a + 50
    mixed(note_x, y3, [("Chapter 18's barrier, before the resolve", "regular", INK)])
    mixed(note_x, y3 + pitch, [("writes it again,", "regular", INK)])
    src_y = y3 + 2 * pitch + 8
    right_b, bottom_b = chip(note_x, src_y, [[("src = ", "mono", GRAY), (stage, "mono-bold", TEAL)],
                                             [("    | COLOR_ATTACHMENT_OUTPUT", "mono", INK)]])
    node(f, name_x, (y3 - 16 + bottom_b) / 2, name_w, bottom_b - y3 + 16, "beginScenePass", kind="pass",
         title_font="mono-bold", size=14)
    f.height = round(bottom_b + 24)

    f.arrow([(right_a, dst_y), (rail, dst_y), (rail, src_y), (right_b, src_y)], TEAL, 2.2, 13)
    divider = (bottom_a + y3 - 16) / 2
    f.line([(24, divider), (f.width - 24, divider)], HAIR, 1.4, "6 5")
    f.text(rail + 14, divider + 22, "chains into", 15, "italic", TEAL)
    f.text(24, (y1 + bottom_a) / 2, "frame N", 15, "bold")
    f.text(24, (y3 - 16 + bottom_b) / 2, "frame N+1", 15, "bold")
    return f


FIGURES = [one_frame_of_the_particles, equal_slices_of_a_sphere, depth_hand_back_chain]
