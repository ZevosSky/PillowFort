"""Chapter 31, Spray: authored figures.

@author Gary Yang
@brief Figures for 31-Spray.md
@copyright (C) Gary 2026
"""
import math
import random

from figure_kit import *

MONO_ADVANCE = 1233 / 2048  # DejaVu Sans Mono's advance per unit of size
ROCK = "#9aa7b4"


def sea_surface(x, still, crest_x, crest_height=18, swell=6, swell_length=150):
    """A schematic water line: a small swell, and one wave crest arriving at crest_x."""
    bump = crest_height * math.exp(-((x - crest_x) / 34) ** 2)
    return still - swell * math.cos(2 * math.pi * x / swell_length) - bump


def draw_foam(f, xs, surface, rng, centre, reach, density=1.0):
    """Flecks of foam lying on the water, thinning out with distance from centre."""
    for x in xs:
        fade = 1 - abs(x - centre) / reach
        if fade <= 0 or rng.random() > fade * density:
            continue
        y = surface(x) + rng.uniform(1, 9)
        w = rng.uniform(5, 11)
        f.add(f'<ellipse cx="{number(x)}" cy="{number(y)}" rx="{number(w / 2)}" ry="2.2" fill="{WHITE}" '
              f'stroke="{LINE}" stroke-width="0.9" opacity="{number(0.35 + 0.65 * fade)}"/>')


def draw_spray(f, rng, base, count, spread, height, lean=-0.35):
    """Droplets in a fan above base, smaller and fewer toward the top."""
    for _ in range(count):
        t = rng.random() ** 0.8
        y = base[1] - t * height
        x = base[0] + (rng.random() - 0.5) * spread * (0.4 + t) + lean * t * height
        r = 1.6 + 2.6 * (1 - t) * rng.random()
        f.circle(x, y, r, BLUE_FILL, BLUE, 1.1)


def leader(f, start, end, label, anchor="start", size=15, font="bold", colour=INK):
    f.line([start, end], GRAY, 1.1)
    dx = 6 if anchor == "start" else (-6 if anchor == "end" else 0)
    dy = 0 if anchor != "middle" else -12
    f.text(end[0] + dx, end[1] + dy, label, size, font, colour, anchor)


def spray_and_foam_at_the_rock():
    f = Figure("spray-and-foam-at-the-rock", 720, 300,
               "Side view of the goal: a rock stands in the sea, a wave runs into it and the water flies up from it as "
               "spray, and foam lies on the water round the rock.",
               source="31-Spray.md, Where this is going")
    rng = random.Random(31)
    still, bottom = 182, 286
    rock_x = 380
    surface = lambda x: sea_surface(x, still, rock_x - 66)
    xs = [20 + 680 * i / 680 for i in range(681)]

    # Water first, then the rock in front of it, its underwater part seen through the water.
    water = [(x, surface(x)) for x in xs]
    f.polygon(water + [(700, bottom), (20, bottom)], BLUE_FILL)
    rock = [(rock_x - 96, bottom), (rock_x - 72, 220), (rock_x - 64, 168), (rock_x - 52, 120), (rock_x - 30, 96),
            (rock_x - 4, 88), (rock_x + 22, 98), (rock_x + 46, 112), (rock_x + 58, 140), (rock_x + 68, 182),
            (rock_x + 84, 236), (rock_x + 104, bottom)]
    f.polygon(rock, ROCK, GRAY, 1.6)
    # The water in front of the rock's foot, so it stands in the sea rather than on it.
    front = [(x, surface(x)) for x in xs if rock_x - 110 <= x <= rock_x + 118]
    f.polygon(front + [(front[-1][0], bottom), (front[0][0], bottom)], BLUE_FILL, opacity=0.72)
    f.line(water, BLUE, 2.4)
    f.line([(20, bottom), (700, bottom)], WHITE, 3)

    draw_foam(f, [x for x in range(30, 690, 7)], surface, rng, rock_x, 230, 1.2)
    draw_spray(f, rng, (rock_x - 58, 150), 46, 70, 112)

    f.text(rock_x, 128, "rock", 15, "bold", WHITE, "middle")
    leader(f, (rock_x - 112, 66), (rock_x - 164, 48), "spray", "end")
    leader(f, (rock_x + 132, surface(rock_x + 132) + 4), (rock_x + 196, 236), "foam", "start")
    f.arrow([(90, 150), (210, 150)], GRAY, 1.6, 10)
    f.text(90, 128, "a wave runs into the rock", 13.5, "italic", GRAY)
    return f


def chip(f, x, y, label, new=False, size=14):
    """A small box inside a step: one of the things it draws or reads."""
    w = measure(label, size, "bold" if new else "regular")[0] + 22
    fill, stroke = (TEAL_FILL, TEAL) if new else (WHITE, LINE)
    f.rect(x, y - 13, w, 26, fill, stroke, 1.2, 6)
    f.text(x + w / 2, y, label, size, "bold" if new else "regular", INK, "middle")
    return x + w


def step(f, x, y, w, h, title, sub="", new=False):
    """One step of the frame: white for Chapter 30's, teal for this chapter's."""
    fill, stroke = (TEAL_FILL, TEAL) if new else (WHITE, LINE)
    f.rect(x, y - h / 2, w, h, fill, stroke, 1.4, 10)
    if sub:
        f.text(x + w / 2, y - 10, title, 15, "bold", anchor="middle")
        f.text(x + w / 2, y + 12, sub, 13, fill=GRAY, anchor="middle")
    else:
        f.text(x + w / 2, y, title, 15, "bold", anchor="middle")


def group(f, x0, y0, x1, y1, name):
    """A dashed outline round the steps one function records, its name on the outline."""
    f.rect(x0, y0, x1 - x0, y1 - y0, "none", TEAL, 1.4, 12, "6 5")
    width = len(name) * 14 * MONO_ADVANCE
    lead = measure("new:", 14, "bold")[0]
    start = x1 - 22 - width - lead - 6
    f.rect(start - 8, y0 - 12, lead + width + 22, 24, WHITE)
    f.text(start, y0, "new:", 14, "bold", TEAL)
    f.text(start + lead + 6, y0, name, 14, "mono-bold", TEAL)


def one_frame_with_spray():
    f = Figure("one-frame-with-spray", 880, 804,
               "One frame with spray: after Chapter 30's steps 1 to 9, the new SeaObjects::RecordSimulation fades "
               "the local foam into scratch, finds the water at the rock to write requests and atomic foam maxima, "
               "resolves the scratch to the sampled local foam, and runs Chapter 21's particle passes with emission "
               "sized by the requests. Step 10 then records the new rock into the sun's shadow cascades, each a "
               "rendering scope of its own, before its scene pass draws the sea, the new rock and the sky, and the "
               "new SeaObjects::RecordSpray draws the spray.",
               source="31-Spray.md, Where this is going")
    x, w = 40, 380
    centre = x + w / 2
    rows = [52, 132, 236, 318, 400, 482, 576, 668, 760]
    h = 54

    step(f, x, rows[0], w, h, "Chapter 30 steps 1-8", "waves, FFT, maps, foam")
    note = f.text(x + w + 24, rows[0] - 10, "maps handed to the vertex shader", 14)
    f.text(note[2] + 5, rows[0] - 10, "(Chapter 30)", 14, fill=GRAY)
    note = f.text(x + w + 24, rows[0] + 12, "and, from this chapter, to compute as well", 14)
    f.text(note[2] + 5, rows[0] + 12, "(section 4)", 14, fill=GRAY)
    step(f, x, rows[1], w, h, "Chapter 30 step 9", "the sky's Update")

    step(f, x, rows[2], w, h, "local foam fades into uint scratch", "section 7", True)
    step(f, x, rows[3], w, h, "impact: the water at the rock", "sections 5-7", True)
    step(f, x, rows[4], w, h, "resolve scratch to sampled local foam", "section 7", True)
    step(f, x, rows[5], w, h, "Chapter 21's begin, emit, simulate, end", "section 6", True)
    f.rect(482, rows[3] - 27, 214, 54, GOLD_FILL, GOLD, 1.4, 10)
    f.text(589, rows[3] - 10, "requests,", 15, "bold", anchor="middle")
    f.text(589, rows[3] + 11, "atomic foam maxima", 15, "bold", anchor="middle")
    f.arrow([(x + w, rows[3]), (482, rows[3])])
    f.arrow([(589, rows[3] + 27), (589, rows[5]), (x + w, rows[5])])
    f.text(603, (rows[4] + rows[5]) / 2 + 2, "emission sized", 13.5, "italic", GRAY)
    f.text(603, (rows[4] + rows[5]) / 2 + 22, "by the requests", 13.5, "italic", GRAY)
    group(f, 24, rows[2] - 54, 736, rows[5] + 42, "SeaObjects::RecordSimulation")

    # Step 10 opens with the shadow cascades, each a rendering scope of its own, so they come before the scene pass.
    step(f, x, rows[6], w, h, "shadow cascades: the rock", "step 10, before the scene pass; section 2", True)

    # Step 10: the scene pass, with the new rock among what it draws.
    sx, sw, sh = x, 560, 78
    f.rect(sx, rows[7] - sh / 2, sw, sh, WHITE, LINE, 1.4, 10)
    f.text(sx + 16, rows[7] - 19, "Chapter 30 step 10: the scene pass", 15, "bold")
    cx = sx + 16
    for label, new in [("the sea", False), ("the rock, section 2", True), ("the sky", False)]:
        cx = chip(f, cx, rows[7] + 15, label, new) + 10

    step(f, x, rows[8], w, h, "the spray", "Chapter 21's second scope, section 6", True)
    lead = measure("new:", 14, "bold")[0]
    f.text(x + w + 24, rows[8], "new:", 14, "bold", TEAL)
    f.text(x + w + 24 + lead + 6, rows[8], "SeaObjects::RecordSpray", 14, "mono-bold", TEAL)

    tops = [rows[0] + h / 2, rows[1] + h / 2, rows[2] + h / 2, rows[3] + h / 2, rows[4] + h / 2, rows[5] + h / 2,
            rows[6] + h / 2, rows[7] + sh / 2]
    bottoms = [rows[1] - h / 2, rows[2] - h / 2, rows[3] - h / 2, rows[4] - h / 2, rows[5] - h / 2, rows[6] - h / 2,
               rows[7] - sh / 2, rows[8] - h / 2]
    for a, b in zip(tops, bottoms):
        f.arrow([(centre, a), (centre, b)])

    for y, kind, label in [(548, "input", "Chapter 30's frame"), (578, "teal", "new in this chapter"), (608, "data", "data")]:
        swatch(f, 640, y, kind, label)
    return f


FIGURES = [spray_and_foam_at_the_rock, one_frame_with_spray]
