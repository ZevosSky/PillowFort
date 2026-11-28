"""Chapter 32, A Boat: authored figures.

@author Gary Yang
@brief Figures for 32-A-Boat.md
@copyright (C) Gary 2026
"""
import math
import random

from figure_kit import *

MONO_ADVANCE = 1233 / 2048  # DejaVu Sans Mono's advance per unit of size
ROCK = "#9aa7b4"


def draw_foam(f, xs, surface, rng, start, end, density=1.0):
    """Flecks of foam lying on the water between start and end, thinning out toward end."""
    for x in xs:
        fade = 1 - (x - start) / (end - start)
        if not 0 < fade <= 1 or rng.random() > fade * density:
            continue
        y = surface(x) + rng.uniform(1, 8)
        w = rng.uniform(5, 11)
        f.add(f'<ellipse cx="{number(x)}" cy="{number(y)}" rx="{number(w / 2)}" ry="2.2" fill="{WHITE}" '
              f'stroke="{LINE}" stroke-width="0.9" opacity="{number(0.25 + 0.75 * fade)}"/>')


def draw_spray(f, rng, base, count, spread, height, lean):
    """Droplets in a fan above base, smaller toward the top; lean tips the fan sideways."""
    for _ in range(count):
        t = rng.random() ** 0.8
        y = base[1] - t * height
        x = base[0] + (rng.random() - 0.5) * spread * (0.4 + t) + lean * t * height
        f.circle(x, y, 1.6 + 2.4 * (1 - t) * rng.random(), BLUE_FILL, BLUE, 1.1)


def the_boat_and_the_rock():
    f = Figure("the-boat-and-the-rock", 860, 312,
               "Side view of the goal: the rock from Chapter 31 with its spray, and to its right the boat, which pitches, "
               "rolls and heaves on the waves and is driven by the arrow keys. Spray flies at its bow when it drops into "
               "a wave, and a wake of foam fades behind it.",
               source="32-A-Boat.md, Where this is going")
    rng = random.Random(32)
    still, bottom = 206, 298
    rock_x, boat_x = 170, 520

    def surface(x):
        crest = 15 * math.exp(-((x - (boat_x - 78)) / 30) ** 2) + 12 * math.exp(-((x - (rock_x - 62)) / 32) ** 2)
        return still - 6 * math.cos(2 * math.pi * (x - 40) / 170) - crest

    xs = [20 + 820 * i / 820 for i in range(821)]
    water = [(x, surface(x)) for x in xs]
    f.polygon(water + [(840, bottom), (20, bottom)], BLUE_FILL)

    # The rock, as in Chapter 31.
    rock = [(rock_x - 88, bottom), (rock_x - 66, 240), (rock_x - 58, 192), (rock_x - 46, 146), (rock_x - 26, 122),
            (rock_x - 2, 114), (rock_x + 22, 124), (rock_x + 42, 138), (rock_x + 54, 166), (rock_x + 62, 204),
            (rock_x + 78, 252), (rock_x + 96, bottom)]
    f.polygon(rock, ROCK, GRAY, 1.6)
    front = [(x, surface(x)) for x in xs if rock_x - 100 <= x <= rock_x + 110]
    f.polygon(front + [(front[-1][0], bottom), (front[0][0], bottom)], BLUE_FILL, opacity=0.72)

    # The boat: bow to the left, pitched bow-down into the wave ahead of it, a little under the water.
    pitch = math.radians(-7)
    cx, cy = boat_x, surface(boat_x) - 9
    size = 1.25

    def place(px, py):
        px, py = px * size, py * size
        return (cx + px * math.cos(pitch) - py * math.sin(pitch), cy + px * math.sin(pitch) + py * math.cos(pitch))

    hull = [place(*p) for p in [(-70, -12), (58, -12), (62, 2), (50, 14), (-38, 14), (-58, 4)]]
    cabin = [place(*p) for p in [(-6, -12), (-6, -34), (30, -34), (30, -12)]]
    f.polygon(cabin, FILL, INK, 1.5)
    f.polygon(hull, WHITE, INK, 1.6)
    # The water in front of the hull's bottom, which sits a little under it.
    front = [(x, surface(x)) for x in xs if boat_x - 96 <= x <= boat_x + 86]
    f.polygon(front + [(front[-1][0], bottom), (front[0][0], bottom)], BLUE_FILL, opacity=0.72)
    f.line(water, BLUE, 2.4)
    f.line([(20, bottom), (840, bottom)], WHITE, 3)

    draw_foam(f, list(range(rock_x - 150, rock_x + 170, 7)), surface, rng, rock_x - 150, rock_x + 260, 0.8)
    draw_foam(f, list(range(boat_x + 58, 834, 6)), surface, rng, boat_x + 50, 840, 1.3)
    draw_spray(f, rng, (rock_x - 52, 176), 40, 64, 104, -0.3)
    bow = place(-70, -10)
    draw_spray(f, rng, (bow[0] - 6, bow[1] + 4), 22, 30, 52, -0.55)

    f.text(rock_x, 154, "rock", 15, "bold", WHITE, "middle")
    top = place(12, -34)
    label_x = top[0] + 22
    f.line([(top[0] + 4, top[1] - 6), (label_x - 6, 84)], GRAY, 1.1)
    f.text(label_x, 66, "the boat:", 15, "bold")
    widest = f.text(label_x, 88, "pitches, rolls, and heaves on the waves;", 14)
    f.text(label_x, 108, "arrow keys drive it", 14)
    assert widest[2] <= f.width - 28, widest   # the same margin as the water's right end, and then some
    f.line([(bow[0] - 22, bow[1] - 44), (bow[0] - 50, 118)], GRAY, 1.1)
    f.text(bow[0] - 56, 98, "spray at the bow when it", 14, anchor="end")
    f.text(bow[0] - 56, 118, "drops into a wave", 14, anchor="end")
    wake_x = boat_x + 150
    f.line([(wake_x, surface(wake_x) + 6), (wake_x + 30, 262)], GRAY, 1.1)
    f.text(wake_x + 36, 262, "a wake of foam", 14)
    f.text(wake_x + 36, 282, "fading behind it", 14)
    return f


def chip(f, x, y, label, new=False, size=14):
    """A small box inside a step: one of the things it draws or reads."""
    w = measure(label, size, "bold" if new else "regular")[0] + 22
    fill, stroke = (TEAL_FILL, TEAL) if new else (WHITE, LINE)
    f.rect(x, y - 13, w, 26, fill, stroke, 1.2, 6)
    f.text(x + w / 2, y, label, size, "bold" if new else "regular", INK, "middle")
    return x + w


def step(f, x, y, w, h, title, sub="", new=False, size=15):
    """One step of the frame: white for Chapters 30 and 31's, teal for this chapter's."""
    fill, stroke = (TEAL_FILL, TEAL) if new else (WHITE, LINE)
    f.rect(x, y - h / 2, w, h, fill, stroke, 1.4, 10)
    if sub:
        f.text(x + w / 2, y - 10, title, size, "bold", anchor="middle")
        f.text(x + w / 2, y + 12, sub, 13, fill=GRAY, anchor="middle")
    else:
        f.text(x + w / 2, y, title, size, "bold", anchor="middle")


def one_frame_with_the_boat():
    f = Figure("one-frame-with-the-boat", 880, 840,
               "Chapter 31's frame with this chapter's additions: in SeaObjects::RecordSimulation the boat now moves "
               "beside the foam fade, and the impact pass reads the water at the hull as well as at the rock, "
               "writing requests and atomic foam and wake maxima. Step 10's shadow cascades take the boat beside the "
               "rock, and its scene pass draws the boat among the sea, the rock and the sky, before the spray.",
               source="32-A-Boat.md, Where this is going")
    x, w = 40, 460
    centre = x + w / 2
    rows = [52, 132, 236, 330, 424, 506, 606, 706, 796]
    h = 54

    step(f, x, rows[0], w, h, "Chapter 30 steps 1-8", "waves, FFT, maps, foam")
    note = f.text(x + w + 24, rows[0] - 10, "hand-overs to", 14)
    f.text(note[2] + 6, rows[0] - 10, "VERTEX | COMPUTE", 14, "mono")
    f.text(x + w + 24, rows[0] + 12, "(Chapter 31 section 4)", 14, fill=GRAY)
    step(f, x, rows[1], w, h, "Chapter 30 step 9", "the sky's Update")

    half = (w - 16) / 2
    step(f, x, rows[2], half, h, "foam fades into scratch", size=14)
    step(f, x + half + 16, rows[2], half, h, "the boat moves", "sections 1-3", True)

    ih = 70
    f.rect(x, rows[3] - ih / 2, w, ih, WHITE, LINE, 1.4, 10)
    f.text(x + 16, rows[3] - 17, "impact", 15, "bold")
    cx = chip(f, x + 16, rows[3] + 14, "the rock") + 10
    chip(f, cx, rows[3] + 14, "the hull, section 3", True)
    step(f, x, rows[4], w, h, "resolve scratch to sampled local foam")
    step(f, x, rows[5], w, h, "Chapter 21's begin, emit, simulate, end")

    dx, dw = 548, 188
    f.rect(dx, rows[3] - 27, dw, 54, GOLD_FILL, GOLD, 1.4, 10)
    f.text(dx + dw / 2, rows[3] - 10, "requests, atomic", 15, "bold", anchor="middle")
    f.text(dx + dw / 2, rows[3] + 11, "foam/wake maxima", 15, "bold", anchor="middle")
    f.arrow([(x + w, rows[3]), (dx, rows[3])])
    f.arrow([(dx + dw / 2, rows[3] + 27), (dx + dw / 2, rows[5]), (x + w, rows[5])])

    name = "SeaObjects::RecordSimulation"
    top, bottom = rows[2] - 50, rows[5] + 42
    width = len(name) * 14 * MONO_ADVANCE
    f.rect(24, top, 736, bottom - top, "none", LINE, 1.4, 12, "6 5")
    f.rect(744 - width - 8, top - 12, width + 16, 24, WHITE)
    f.text(744 - width, top, name, 14, "mono-bold", GRAY)

    sx, sw, sh = x, 620, 78
    # Step 10 opens with Chapter 31's shadow cascades, now with the boat in them, before the scene pass.
    f.rect(sx, rows[6] - sh / 2, sw, sh, WHITE, LINE, 1.4, 10)
    f.text(sx + 16, rows[6] - 19, "Chapter 31: the shadow cascades, before the scene pass", 15, "bold")
    cx = sx + 16
    for label, new in [("the rock", False), ("the boat, section 2", True)]:
        cx = chip(f, cx, rows[6] + 15, label, new) + 10
    f.rect(sx, rows[7] - sh / 2, sw, sh, WHITE, LINE, 1.4, 10)
    f.text(sx + 16, rows[7] - 19, "Chapter 30 step 10: the scene pass", 15, "bold")
    cx = sx + 16
    for label, new in [("the sea", False), ("the rock", False), ("the boat, section 2", True), ("the sky", False)]:
        cx = chip(f, cx, rows[7] + 15, label, new) + 10
    step(f, x, rows[8], w, h, "the spray")

    # Arrows: one into each of the two parallel steps, and both on into the impact pass.
    fork = rows[2] - h / 2 - 20
    left_c, right_c = x + half / 2, x + half + 16 + half / 2
    f.line([(centre, rows[1] + h / 2), (centre, fork), (left_c, fork)])
    f.line([(centre, fork), (right_c, fork)])
    f.arrow([(left_c, fork), (left_c, rows[2] - h / 2)])
    f.arrow([(right_c, fork), (right_c, rows[2] - h / 2)])
    f.arrow([(left_c, rows[2] + h / 2), (left_c, rows[3] - ih / 2)])
    f.arrow([(right_c, rows[2] + h / 2), (right_c, rows[3] - ih / 2)])
    for a, b in [(rows[0] + h / 2, rows[1] - h / 2), (rows[3] + ih / 2, rows[4] - h / 2), (rows[4] + h / 2, rows[5] - h / 2),
                 (rows[5] + h / 2, rows[6] - sh / 2), (rows[6] + sh / 2, rows[7] - sh / 2),
                 (rows[7] + sh / 2, rows[8] - h / 2)]:
        f.arrow([(centre, a), (centre, b)])

    for y, kind, label in [(rows[7] - 30, "input", "Chapters 30 and 31"), (rows[7], "teal", "new in this chapter"),
                           (rows[7] + 30, "data", "data")]:
        swatch(f, 680, y, kind, label)
    return f


FIGURES = [the_boat_and_the_rock, one_frame_with_the_boat]
