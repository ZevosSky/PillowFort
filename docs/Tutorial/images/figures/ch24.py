"""Chapter 24, Image-Based Lighting: authored figures.

@author Gary Yang
@brief Figures for 24-Image-Based-Lighting.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def half_disc(f, cx, cy, r, upper, fill, stroke, opacity=None):
    """The upper or lower half of a circle, closed along its diameter."""
    sweep = 1 if upper else 0
    extra = f' opacity="{number(opacity)}"' if opacity is not None else ""
    f.add(f'<path d="M{number(cx - r)} {number(cy)} A{number(r)} {number(r)} 0 0 {sweep} {number(cx + r)} {number(cy)} Z" '
          f'fill="{fill}" stroke="{stroke}" stroke-width="1.6" stroke-linejoin="round"{extra}/>')


def sky_with_a_sunset_patch():
    sky, ground, sunset, patch = (0.10, 0.20, 0.40), (0.04, 0.03, 0.02), (3.0, 1.2, 0.3), 0.2
    elevation = 5.0

    # The chapter's table, from section 1's sum over this sky: each surface's light divided by pi.
    def received(sun_cosine, sky_share, ground_share):
        return tuple(sky_share * s + ground_share * g + (b - s) * patch * sun_cosine / math.pi
                     for s, g, b in zip(sky, ground, sunset))
    floor = received(math.cos(math.radians(90 - elevation)), 1.0, 0.0)
    toward = received(math.cos(math.radians(elevation)), 0.5, 0.5)
    away = received(0.0, 0.5, 0.5)
    average = tuple(0.5 * s + 0.5 * g + (b - s) * patch / (4 * math.pi) for s, g, b in zip(sky, ground, sunset))
    for value, printed in [(floor, (0.12, 0.21, 0.40)), (toward, (0.25, 0.18, 0.20)), (away, (0.07, 0.12, 0.21)),
                           (average, (0.12, 0.13, 0.21))]:
        assert all(abs(v - p) <= 0.0051 for v, p in zip(value, printed)), (value, printed)

    f = Figure("sky-with-a-sunset-patch", 700, 322,
               "A simple sky seen from the side: blue sky above the horizon, (0.10, 0.20, 0.40); dark ground below, "
               "(0.04, 0.03, 0.02); and a sunset, a patch of 0.2 steradians just above the horizon toward +X, "
               "(3.0, 1.2, 0.3).",
               source="24-Image-Based-Lighting.md, section 1 (Why one ambient color is wrong)",
               parameters={"sky": sky, "ground": ground, "sunset": sunset, "sunsetSteradians": patch,
                           "sunsetElevationDegrees": elevation})
    cx, cy, r = 260, 166, 132
    half_disc(f, cx, cy, r, True, BLUE_FILL, BLUE)
    half_disc(f, cx, cy, r, False, GRAY, "none", 0.22)
    half_disc(f, cx, cy, r, False, "none", GRAY)
    f.line([(24, cy), (cx - r, cy)], INK, 2)
    f.line([(cx + r, cy), (676, cy)], INK, 2)
    f.text(28, cy - 16, "horizon", 14, fill=GRAY)

    f.text(cx, cy - 78, "blue sky above", 15, "bold", anchor="middle")
    f.text(cx, cy - 56, "(0.10, 0.20, 0.40)", 15, anchor="middle")
    f.text(cx, cy + 56, "dark ground below", 15, "bold", anchor="middle")
    f.text(cx, cy + 78, "(0.04, 0.03, 0.02)", 15, anchor="middle")

    # The sunset: a patch of sky just above the horizon, centred on section 1's 5 degrees.
    sector = [(cx + rr * math.cos(math.radians(t)), cy - rr * math.sin(math.radians(t)))
              for rr, ts in [(r - 7, range(1, 10)), (r + 7, range(9, 0, -1))] for t in ts]
    f.polygon(sector, GOLD_SOFT, GOLD, 1.6)
    f.arrow([(cx, cy), (cx + r - 26, cy)], INK, 1.8, 11)
    f.circle(cx, cy, 4.5, INK, WHITE, 1.6)
    f.text(cx + r - 40, cy + 18, "+X", 14, "bold", anchor="middle")
    tip = (cx + r * math.cos(math.radians(elevation)) + 8, cy - r * math.sin(math.radians(elevation)) - 4)
    f.line([tip, (436, 104)], GOLD, 1.3)
    f.text(444, 74, "sunset", 15, "bold", GOLD_TEXT)
    f.lines(444, 98, ["a patch of 0.2 sr, just above", "the horizon toward +X,", "(3.0, 1.2, 0.3)"], 15, spacing=22)
    return f


def solid_angle_of_a_cube_texel():
    # Section 2's numbers, which the drawing's formula must reproduce.
    area = (2 / 16) ** 2
    assert round(area, 4) == 0.0156
    assert round(area / 1.0 ** 3, 4) == 0.0156 and round(area / (1 + 2 * (1 / 16) ** 2) ** 1.5, 4) == 0.0154
    corner = 1 + 2 * 0.9375 ** 2
    assert round(corner, 2) == 2.76 and round(corner ** 1.5, 2) == 4.58 and round(area / corner ** 1.5, 4) == 0.0034
    whole = sum(area / (1 + (-1 + (i + 0.5) / 8) ** 2 + (-1 + (j + 0.5) / 8) ** 2) ** 1.5
                for i in range(16) for j in range(16)) * 6
    assert round(whole, 3) == 12.578, whole

    texels, u = 4, 0.75                      # a coarse face, so one texel is big enough to see; the texel at u = 0.75
    d = math.sqrt(1 + u * u)
    a = math.atan(u)
    assert abs(math.cos(a) - 1 / d) < 1e-12  # cos(a) = 1 / d

    f = Figure("solid-angle-of-a-cube-texel", 668, 388,
               "A cube face seen edge-on, 1 unit from the centre. The line of sight to a texel on it is d long and meets the "
               "face at the angle a from straight on, so seen from the centre the texel looks its area times cos a big; d is "
               "the square root of 1 + u squared + v squared, and cos a is 1 / d.",
               kind="computed plot",
               source="24-Image-Based-Lighting.md, section 2 (Adding up a sky, texel by texel)",
               parameters={"texelsAcrossTheDrawnFace": texels, "texelCentreU": u, "angleDegrees": round(math.degrees(a), 2)})
    scale = 150
    cx, cy = 72, 204
    face_x = cx + scale

    def on_face(position):
        return (face_x, cy - position * scale)

    low, high = u - 1 / texels, u + 1 / texels
    centre = on_face(u)
    f.polygon([(cx, cy), on_face(high), on_face(low)], GOLD_FILL)
    f.line([(cx, cy), on_face(high)], GOLD_SOFT, 1.3)
    f.line([(cx, cy), on_face(low)], GOLD_SOFT, 1.3)

    f.line([(cx, cy), (face_x, cy)], LINE, 1.4, "5 5")
    f.text((cx + face_x) / 2, cy + 16, "1", 16, "italic", GRAY, "middle")
    f.line([on_face(-1), on_face(1)], INK, 2.2)
    for k in range(2 * texels + 1):
        x, y = on_face(-1 + 2 * k / (2 * texels))
        if k % 2 == 0:
            f.line([(x - 6, y), (x + 6, y)], INK, 1.6)
    f.rect(face_x - 3, on_face(high)[1], 6, on_face(low)[1] - on_face(high)[1], GOLD, "none")

    f.line([(cx, cy), centre], BLUE, 2.2)
    sight = ((centre[0] - cx) / (d * scale), (centre[1] - cy) / (d * scale))
    middle = ((cx + centre[0]) / 2, (cy + centre[1]) / 2)
    f.rect(middle[0] - 11, middle[1] - 12, 22, 24, WHITE, "none", radius=4)
    f.text(middle[0], middle[1], "d", 18, "italic", BLUE, "middle")
    f.arc(cx, cy, 52, 0, math.degrees(a), TEAL, 1.4)
    f.text(cx + 66 * math.cos(a / 2), cy - 66 * math.sin(a / 2), "a", 17, "italic", TEAL, "middle")

    # What the centre sees: the texel across the line of sight, (2/M) cos(a) on this cross-section.
    across = (-sight[1], sight[0])
    half = 0.5 * (2 / texels) * scale * math.cos(a)
    f.line([(centre[0] - across[0] * half, centre[1] - across[1] * half),
            (centre[0] + across[0] * half, centre[1] + across[1] * half)], TEAL, 4)
    f.circle(cx, cy, 5.5, INK, WHITE, 2)
    f.text(cx, cy + 22, "centre", 14, fill=GRAY, anchor="middle")

    for position, label in [(1, "u = 1"), (0, "u = 0"), (-1, "u = −1")]:
        x, y = on_face(position)
        f.text(x + 14, y, label, 13.5, fill=GRAY)
    f.text(face_x + 14, cy + 80, "face, 1 unit", 14, fill=GRAY)
    f.text(face_x + 14, cy + 99, "from the centre", 14, fill=GRAY)

    x = 300
    f.line([(face_x + 9, on_face(u + 0.08)[1]), (x - 10, 64)], GOLD, 1.2)
    f.lines(x, 64, ["texel, area (2/M)², tilted by the angle a"], 15)
    f.line([(face_x + 26, centre[1] + 17), (x - 10, 116)], TEAL, 1.2)
    f.lines(x, 116, ["seen from the centre it looks (2/M)² cos(a)", "big, and it is d away"], 15, spacing=21)
    f.text(x, 236, "d = √(1 + u² + v²),  cos(a) = 1 / d", 15, "bold")
    return f


def downsample_lookups_on_shared_corners():
    taps, cells, cell = 2, 4, 52
    # Section 3's placement: lookup i lands (i + 0.5) / taps of the way across the small texel, in sky texels.
    corners = [(i + 0.5) / taps * cells for i in range(taps)]
    assert corners == [1.0, 3.0]             # every lookup sits on a corner four sky texels share

    f = Figure("downsample-lookups-on-shared-corners", 720, 310,
               "One texel of the small copy covers 4 by 4 sky texels; with taps = 2 it makes four lookups, each on the corner "
               "four sky texels share. Linear filtering returns those four texels' average, and the four lookups together "
               "average all sixteen.",
               source="24-Image-Based-Lighting.md, section 3 (The class, its images, and a smaller sky)",
               parameters={"taps": taps, "skyTexelsAcross": cells, "lookupsAt": corners})
    left, top = 40, 56
    span = cells * cell
    for j in range(cells):
        for i in range(cells):
            group = (i // 2 + j // 2) % 2
            f.rect(left + i * cell, top + j * cell, cell, cell, TEAL_FILL if group == 0 else WHITE, "none")
    for k in range(1, cells):
        f.line([(left + k * cell, top), (left + k * cell, top + span)], LINE, 1.1)
        f.line([(left, top + k * cell), (left + span, top + k * cell)], LINE, 1.1)
    f.rect(left, top, span, span, "none", INK, 2.6, 2)

    def lookup(x, y):
        f.circle(x, y, 11, WHITE, TEAL, 2)
        f.line([(x - 5.5, y - 5.5), (x + 5.5, y + 5.5)], TEAL, 2.4)
        f.line([(x - 5.5, y + 5.5), (x + 5.5, y - 5.5)], TEAL, 2.4)

    for gy in corners:
        for gx in corners:
            lookup(left + gx * cell, top + gy * cell)
    f.text(left, 30, "one texel of the small copy", 14, fill=GRAY)
    f.text(left + span / 2, top + span + 24, "4 × 4 sky texels, taps = 2", 14, fill=GRAY, anchor="middle")

    x = 320
    lookup(x + 10, 110)
    f.text(x + 34, 110, "a lookup on the corner four sky texels share.", 15)
    f.text(x + 34, 134, "Linear filtering returns their average;", 15)
    f.text(x + 34, 158, "the four lookups together average all sixteen.", 15)
    f.rect(x, 206, 20, 20, TEAL_FILL, LINE, 1.1, 2)
    f.text(x + 34, 216, "the 2 × 2 sky texels one lookup averages", 15)
    return f


def rough_reflection_streak_and_blob():
    f = Figure("rough-reflection-streak-and-blob", 720, 300,
               "A light reflected in a rough floor, seen at a low angle. The real reflection is a tall streak, long toward the "
               "viewer and narrow across; the split sum's reflection is a round blob around r.",
               source="24-Image-Based-Lighting.md, section 5 (What a rough surface reflects: the split sum)")
    width, height, top = 300, 214, 22
    horizon = top + 74

    def panel(left, streak, caption):
        f.rect(left, top, width, height, WHITE, "none")
        f.rect(left, horizon, width, top + height - horizon, FILL, "none")
        vanish = (left + width / 2, horizon)
        bottom = top + height
        for k in range(-6, 7):
            reach = k * 64
            t = min(1.0, (width / 2) / abs(reach)) if k else 1.0
            f.line([vanish, (vanish[0] + reach * t, horizon + (bottom - horizon) * t)], GRID, 1)
        f.line([(left, horizon), (left + width, horizon)], INK, 1.6)
        f.rect(left, top, width, height, "none", LINE, 1.2, 8)
        light = (left + width / 2, horizon - 40)
        f.circle(*light, 11, GOLD_SOFT, GOLD, 1.6)
        mirror = (light[0], horizon + 40)
        if streak:
            f.add(f'<ellipse cx="{number(mirror[0])}" cy="{number(mirror[1] + 30)}" rx="13" ry="62" fill="{GOLD_FILL}" '
                  f'stroke="{GOLD_SOFT}" stroke-width="1.2"/>')
            f.add(f'<ellipse cx="{number(mirror[0])}" cy="{number(mirror[1] + 26)}" rx="6" ry="45" fill="{GOLD_SOFT}"/>')
        else:
            f.circle(mirror[0], mirror[1], 30, GOLD_FILL, GOLD_SOFT, 1.2)
            f.circle(mirror[0], mirror[1], 15, GOLD_SOFT)
        # The mirror direction r in both panels, so the two reflections compare at the same point; its label sits
        # the same 14 px outside each reflection's outer edge.
        f.circle(mirror[0], mirror[1], 3.5, INK)
        f.text(mirror[0] + (13 if streak else 30) + 14, mirror[1], "r", 19, "vector", INK, "middle")
        widths = [measure(text, 15, font)[0] for text, font in caption]
        x = left + width / 2 - (sum(widths) + 7 * (len(caption) - 1)) / 2
        for (text, font), w in zip(caption, widths):
            f.text(x, top + height + 24, text, 15, font)
            x += w + 7
        return light

    light = panel(28, True, [("the real reflection: a tall streak", "bold")])
    panel(392, False, [("the split sum's: a round blob around", "bold"), ("r", "vector")])
    f.text(light[0] - 20, light[1], "light", 14, fill=GRAY, anchor="end")
    f.text(40, horizon - 12, "horizon", 13.5, fill=GRAY)
    f.text(40, top + height - 14, "rough floor", 13.5, fill=GRAY)
    return f


FIGURES = [sky_with_a_sunset_patch, solid_angle_of_a_cube_texel, downsample_lookups_on_shared_corners,
           rough_reflection_streak_and_blob]
