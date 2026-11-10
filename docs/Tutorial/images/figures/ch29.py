"""Chapter 29, The FFT Ocean: authored figures.

@author Gary Yang
@brief Figures for 29-FFT-Ocean.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def one_frame_of_the_ocean():
    f = Figure("one-frame-of-the-ocean", 880, 556,
               "One frame of the ocean. Wind feeds the spectrum pass, which makes h0 only when a setting changes. Time and h0 "
               "feed animate, then FFT, then assemble. Assemble writes the displacement map for the surface vertex shader and "
               "normals plus foam for the surface fragment shader, and feeds the preview pass.",
               source="29-FFT-Ocean.md, Where this is going")
    rows = [56, 158, 260, 376, 500]
    spine_x, spine_w, h = 170, 200, 68
    centre, spine_end = spine_x + spine_w / 2, spine_x + spine_w

    node(f, 24, rows[0], 96, 52, "wind", kind="input")
    node(f, 24, rows[1], 96, 52, "time", kind="input")
    for y, title, note in zip(rows, ["spectrum", "animate", "FFT", "assemble", "preview"],
                              ["section 7", "section 8", "section 5", "section 9", "section 6"]):
        node(f, spine_x, y, spine_w, h, title, note)
    node(f, 428, rows[0], 190, h, "h0", "the starting waves", "data")
    f.text(636, rows[0] - 10, "only when a", 13.5, "italic", GRAY)
    f.text(636, rows[0] + 10, "setting changes", 13.5, "italic", GRAY)

    f.arrow([(120, rows[0]), (spine_x, rows[0])])
    f.arrow([(120, rows[1]), (spine_x, rows[1])])
    f.arrow([(spine_end, rows[0]), (428, rows[0])])
    f.arrow([(523, rows[0] + h / 2), (523, rows[1]), (spine_end, rows[1])])
    # The spine starts at animate: spectrum reaches it only through h0.
    for a, b in zip(rows[1:-1], rows[2:]):
        f.arrow([(centre, a + h / 2), (centre, b - h / 2)])
    f.text(centre + 14, (rows[1] + rows[2]) / 2, "eight spectra, packed into two images", 13.5, fill=GRAY)
    f.text(spine_end + 18, rows[2], "16 dispatches at N = 256: waves → heights", 13.5, fill=GRAY)

    for y, offset, data, shader in [(rows[3] - 44, -12, "displacement map", "surface vertex shader"),
                                    (rows[3] + 44, 12, "normals + foam", "surface fragment shader")]:
        node(f, 428, y, 170, 52, data, kind="data")
        node(f, 630, y, 226, 62, shader, "section 10", "shader")
        f.arrow([(spine_end, rows[3] + offset), (399, rows[3] + offset), (399, y), (428, y)])
        f.arrow([(598, y), (630, y)])
    f.arrow([(spine_end, rows[4]), (428, rows[4])])
    f.text(440, rows[4], "a picture of any of these, in a panel", 15)

    for y, kind, label in [(136, "pass", "compute pass"), (166, "data", "image data"), (196, "shader", "graphics shader")]:
        swatch(f, 668, y, kind, label)
    return f


def wave_energy_by_wavelength():
    gravity, wind = 9.81, 12.0
    scale = wind * wind / gravity

    def energy(wavelength):
        k = 2 * math.pi / wavelength
        return math.exp(-1 / (k * scale) ** 2) / k ** 4

    peak = 2 * math.pi * math.sqrt(2) * scale
    table = {1000: 0.000, 300: 0.005, 200: 0.371, 130: 1.000, 100: 0.788, 70: 0.345, 50: 0.119, 30: 0.019, 10: 0.000}
    worst = max(abs(energy(w) / energy(peak) - printed) for w, printed in table.items())
    assert worst < 5e-4, worst  # The curve must reproduce the chapter's printed table to its 3 places.

    f = Figure("wave-energy-by-wavelength", 880, 404,
               "Wave energy against wavelength along the wind, relative to its peak: near zero at 1000 metres, rising to 1 at "
               "about 130 metres, then falling to near zero by 10 metres.",
               kind="computed plot", source="29-FFT-Ocean.md, section 7 (What a sea's spectrum looks like)",
               parameters={"spectrum": "Phillips, exp(-1/(kL)^2)/k^4 along the wind", "windMetresPerSecond": wind,
                           "gravity": gravity, "peakWavelengthMetres": round(peak, 2), "worstTableDifference": round(worst, 5)})
    left, right, top, bottom = 96, 852, 34, 330
    long_end, short_end = 1300, 7

    def px(wavelength):
        return left + (right - left) * math.log(long_end / wavelength) / math.log(long_end / short_end)

    def py(share):
        return bottom - (bottom - top) * share / 1.2

    for share in (0, 0.25, 0.5, 0.75, 1.0):
        f.line([(left, py(share)), (right, py(share))], LINE if share == 0 else GRID, 1.2 if share == 0 else 1)
        f.text(left - 12, py(share), f"{share:g}", 13.5, fill=GRAY, anchor="end")
    steps = [long_end * (short_end / long_end) ** (i / 320) for i in range(321)]
    curve = [(px(w), py(energy(w) / energy(peak))) for w in steps]
    area = "M" + " L".join(f"{number(x)} {number(y)}" for x, y in curve) + f" L{number(right)} {number(bottom)} L{number(left)} {number(bottom)} Z"
    f.add(f'<path d="{area}" fill="{BLUE_FILL}"/>')
    f.line(curve, BLUE, 2.8)

    offsets = {1000: (0, -14, "middle"), 300: (-8, -13, "end"), 200: (-11, -7, "end"), 100: (12, -5, "start"),
               70: (11, -7, "start"), 50: (10, -10, "start"), 30: (6, -14, "start"), 10: (0, -14, "middle")}
    for wavelength, printed in table.items():
        x, y = px(wavelength), py(energy(wavelength) / energy(peak))
        f.line([(x, bottom), (x, bottom + 6)], LINE, 1.2)
        f.text(x, bottom + 22, str(wavelength), 13.5, fill=GRAY, anchor="middle")
        f.circle(x, y, 5.5, GOLD, WHITE, 1.8)
        if wavelength in offsets:
            dx, dy, anchor = offsets[wavelength]
            f.text(x + dx, y + dy, f"{printed:.3f}", 13.5, anchor=anchor)
    f.text(px(130), py(1.0) - 18, "1.000 at about 8.9 L: 130 m for a 12 m/s wind", 14.5, "bold", anchor="middle")
    f.text(left + 18, 134, "the wind cannot build waves", 14, fill=GRAY)
    f.text(left + 18, 154, "far longer than its own scale", 14, fill=GRAY)
    f.text(640, 134, "shorter waves carry", 14, fill=GRAY)
    f.text(640, 154, "far less energy", 14, fill=GRAY)
    f.text((left + right) / 2, 384, "wavelength in metres", 14, fill=GRAY, anchor="middle")
    f.text(30, (top + bottom) / 2, "P(k) / peak, along the wind", 14, fill=GRAY, anchor="middle", rotate=-90)
    return f


def crests_troughs_and_wavelength():
    f = Figure("crests-troughs-and-wavelength", 880, 290,
               "One wave, h = A cos(k x + φ), seen from the side along k: crests rise A above the mean level, "
               "troughs sink A below it, and a wavelength runs from crest to crest. Seen from above, the crests are "
               "parallel lines across the wave vector k.",
               kind="computed plot", source="29-FFT-Ocean.md, section 1 (What describes a wave)",
               parameters={"profile": "A cos(k x), phase 0"})
    # Side view: two whole wavelengths, crests at x = 0, λ, 2λ.
    wave, amp, mean = 184, 48, 130
    x_crest = 92
    def at(x):  # x in wavelengths
        return (x_crest + x * wave, mean - amp * math.cos(2 * math.pi * x))
    start, end = -0.32, 2.32
    f.line([(at(start)[0] - 6, mean), (at(end)[0] + 6, mean)], LINE, 1.3, "6 5")
    f.text(at(end)[0] + 14, mean, "mean level", 13.5, fill=GRAY)
    curve = [at(start + (end - start) * i / 400) for i in range(401)]
    f.polygon(curve + [(curve[-1][0], mean + amp + 4), (curve[0][0], mean + amp + 4)], BLUE_FILL)
    f.line(curve, BLUE, 2.8)
    for i in range(3):
        x, y = at(i)
        f.text(x, y - 18, "crest", 14, "bold", anchor="middle")
    for i in range(2):
        x, y = at(i + 0.5)
        f.text(x, y + 20, "trough", 14, "bold", anchor="middle")

    # Amplitude, at the last crest; the wavelength, crest to crest under the first trough.
    ax = at(2)[0] + 34
    f.line([(at(2)[0] + 6, at(2)[1]), (ax + 6, at(2)[1])], LINE, 1.1, "3 3")
    f.arrow([(ax, mean - 2), (ax, at(2)[1] + 2)], GRAY, 1.4, 9, both=True)
    f.text(ax + 10, mean - amp / 2, "A", 15, "italic", INK)
    dim = mean + amp + 52
    for i in range(2):
        x, y = at(i)
        f.line([(x, y + 8), (x, dim + 8)], LINE, 1.1, "3 3")
    f.arrow([(at(0)[0] + 2, dim), (at(1)[0] - 2, dim)], GRAY, 1.4, 9, both=True)
    f.rect((at(0)[0] + at(1)[0]) / 2 - 52, dim - 11, 104, 22, WHITE)
    f.text((at(0)[0] + at(1)[0]) / 2, dim, "wavelength", 14, anchor="middle")
    f.text(x_crest - 50, 34, "side view, along k", 13.5, "italic", GRAY)
    f.arrow([(at(1.25)[0], 34), (at(1.95)[0], 34)], INK, 2.2, 13)
    f.text(at(1.25)[0] - 12, 34, "k", 18, "vector", INK, "end")
    f.text(at(1.95)[0] + 12, 34, "the way the wave travels", 13.5, "italic", GRAY)

    # From above: crest lines at right angles to k, one wavelength apart.
    divider = 640
    f.line([(divider, 24), (divider, f.height - 24)], HAIR, 1.4)
    box_x, box_y, side = 676, 56, 172
    f.text(box_x, 34, "from above", 13.5, "italic", GRAY)
    f.rect(box_x, box_y, side, side, FILL, LINE, 1.2, 4)
    angle = 30.0
    d = unit(angle)                      # along k, SVG space
    across = (-d[1], d[0])               # along a crest line
    cx, cy = box_x + side / 2, box_y + side / 2
    spacing = 58
    f.defs.append(f'<clipPath id="from-above"><rect x="{box_x}" y="{box_y}" width="{side}" height="{side}" rx="4"/></clipPath>')
    f.add('<g clip-path="url(#from-above)">')
    for i in range(-3, 4):
        for offset, colour, width, dash in [(0.0, BLUE, 2.6, None), (0.5, LINE, 1.2, "5 5")]:
            o = (i + offset) * spacing
            px, py = cx + d[0] * o, cy + d[1] * o
            f.line([(px - across[0] * 200, py - across[1] * 200), (px + across[0] * 200, py + across[1] * 200)], colour, width, dash)
    f.add("</g>")
    # k through the middle, from one crest line to the next.
    k0 = (cx - d[0] * spacing * 0.9, cy - d[1] * spacing * 0.9)
    k1 = (cx + d[0] * spacing * 0.9, cy + d[1] * spacing * 0.9)
    f.arrow([k0, k1], INK, 2.4, 13)
    f.rect(k1[0] - 2, k1[1] - 30, 20, 22, FILL)
    f.text(k1[0] + 8, k1[1] - 19, "k", 18, "vector", INK, "middle")
    f.text(box_x + side / 2, box_y + side + 22, "crests: lines across k", 13.5, fill=BLUE, anchor="middle")
    f.text(box_x + side / 2, box_y + side + 42, "dashed: troughs", 13.5, "italic", GRAY, "middle")
    return f


def a_gaussian_bell_curve():
    within = [math.erf(n / math.sqrt(2)) for n in (1, 2, 3)]
    # The chapter's "68% within one σ of the mean, 95% within two, and 99.73% within three".
    assert round(100 * within[0]) == 68 and round(100 * within[1]) == 95 and round(100 * within[2], 2) == 99.73, within

    f = Figure("a-gaussian-bell-curve", 760, 352,
               "A bell curve: how often a Gaussian random number of mean 0 and standard deviation 1 takes each value. "
               "Values cluster around 0; 68% fall within one standard deviation and 95% within two.",
               kind="computed plot", source="29-FFT-Ocean.md, section 7 (Random numbers with a bell curve)",
               parameters={"mean": 0, "sigma": 1, "withinOneTwoThree": [round(w, 4) for w in within]})
    left, right, top, bottom = 70, 730, 36, 220
    span = 3.6

    def px(v):
        return left + (right - left) * (v + span) / (2 * span)

    def pdf(v):
        return math.exp(-v * v / 2) / math.sqrt(2 * math.pi)

    def py(density):
        return bottom - (bottom - top) * density / pdf(0) * 0.96

    def band(a, b, colour):
        points = [(px(a + (b - a) * i / 120), py(pdf(a + (b - a) * i / 120))) for i in range(121)]
        f.polygon(points + [(px(b), bottom), (px(a), bottom)], colour)

    band(-2, 2, BLUE_FILL)
    band(-1, 1, "#c4d8ea")
    for v in (-2, -1, 1, 2):
        f.line([(px(v), py(pdf(v))), (px(v), bottom)], WHITE, 1.4)
    curve = [(px(-span + 2 * span * i / 400), py(pdf(-span + 2 * span * i / 400))) for i in range(401)]
    f.line(curve, BLUE, 2.8)
    f.arrow([(left - 8, bottom), (right + 6, bottom)], LINE, 1.4, 10)
    f.line([(left - 8, bottom), (left - 8, top - 6)], LINE, 1.4)
    f.text(left + 4, top - 6, "how often", 14, fill=GRAY)
    for v in range(-3, 4):
        f.line([(px(v), bottom), (px(v), bottom + 6)], LINE, 1.2)
        f.text(px(v), bottom + 20, f"{v}".replace("-", "−"), 13.5, fill=GRAY, anchor="middle")
    f.text(right - 4, bottom - 16, "value", 14, fill=GRAY, anchor="end")
    f.text(right, top - 6, "mean 0, standard deviation σ = 1", 13.5, fill=GRAY, anchor="end")

    for y, a, label in [(bottom + 48, 1, "68% within one σ"), (bottom + 84, 2, "95% within two")]:
        f.line([(px(-a), y - 7), (px(-a), y), (px(a), y), (px(a), y - 7)], BLUE, 1.5)
        f.rect((px(-a) + px(a)) / 2 - measure(label, 14)[0] / 2 - 8, y + 2, measure(label, 14)[0] + 16, 20, WHITE)
        f.text((px(-a) + px(a)) / 2, y + 13, label, 14, "bold", BLUE, "middle")
    return f


# One wave h = A cos(k x), moved sideways by λ D with D = −A sin(k x) (section 8's displacement for one cosine).
CHOP_AK = 0.8   # λ A k at choppiness 1: sharp crests, no fold (a fold needs λ A k > 1)


def moved(x, choppiness):
    """A point at phase x (radians): where the sideways move puts it, and its height, in units of 1/k."""
    return x - choppiness * CHOP_AK * math.sin(x), CHOP_AK * math.cos(x)


def points_moved_toward_the_crests():
    f = Figure("points-moved-toward-the-crests", 880, 258,
               "The same surface points before and after the sideways move. At choppiness 0 they are evenly spaced "
               "on a round cosine; at choppiness 1 each has moved toward the nearest crest, so they bunch at sharp "
               "crests and spread across broad troughs.",
               kind="computed plot", source="29-FFT-Ocean.md, section 8 (Sharp crests: moving the surface sideways)",
               parameters={"lambdaAk": CHOP_AK, "pointsPerWavelength": 8, "displacement": "-A sin(kx)"})
    x0, scale = 162, 158 / (2 * math.pi)      # one wavelength is 158 px
    rows = [(0, 62, "choppiness 0", "evenly spaced"), (1, 172, "choppiness 1", "bunched at the crests")]
    phases = [math.pi * (-1 + i / 4) for i in range(25)]   # from a trough to a trough, 8 per wavelength

    for choppiness, mean, name, note in rows:
        def at(phase):
            mx, h = moved(phase, choppiness)
            return (x0 + (mx + math.pi) * scale, mean - h * scale)
        steps = [-math.pi + 6 * math.pi * i / 600 for i in range(601)]
        if choppiness:
            f.line([(x0 + (s + math.pi) * scale, mean - CHOP_AK * math.cos(s) * scale) for s in steps], LINE, 1.3, "5 5")
        f.line([at(s) for s in steps], BLUE, 2.6)
        for phase in phases:
            f.circle(*at(phase), 4.6, GOLD, WHITE, 1.6)
        f.text(28, mean, name, 15, "bold")
        f.text(x0 + 6 * math.pi * scale + 20, mean, note, 15, fill=INK)
    # Where a few points of the lower row came from: ticks at their even spacing, arrows toward the crest.
    mean = rows[1][1]
    for phase in phases:
        sx = x0 + (phase + math.pi) * scale
        mx, h = moved(phase, 1)
        ex = x0 + (mx + math.pi) * scale
        if abs(ex - sx) > 9:
            y = mean + CHOP_AK * scale + 22
            f.arrow([(sx, y), (ex, y)], TEAL, 1.4, 7)
    f.text(x0 + 6 * math.pi * scale + 20, mean + CHOP_AK * scale + 22, "toward the nearest crest", 13.5, "italic", TEAL)
    f.text(x0 + 6 * math.pi * scale + 20, mean - 24, "dashed: before the move", 13.5, "italic", GRAY)
    return f


def grid_squeezed_at_the_crest():
    columns, rows, cell = 12, 3, 28
    widths = []
    for i in range(columns):
        a = moved(-math.pi + 2 * math.pi * i / columns, 1)[0]
        b = moved(-math.pi + 2 * math.pi * (i + 1) / columns, 1)[0]
        widths.append((b - a) / (2 * math.pi / columns))
    assert min(widths) < 1 < max(widths) and abs(sum(widths) - columns) < 1e-9   # shrinks at the crest, grows in the troughs

    f = Figure("grid-squeezed-at-the-crest", 852, 222,
               "Seen from above, a flat grid of small squares across one wavelength, and the same grid after every corner "
               "moves sideways by λ D: near the crest in the middle the squares shrink, and in the troughs at either side "
               "they grow.",
               kind="computed plot", source="29-FFT-Ocean.md, section 9 (The Jacobian: how squeezed the surface is)",
               parameters={"lambdaAk": CHOP_AK, "columnsPerWavelength": columns})
    top = 52
    height = rows * cell
    width = columns * cell

    def grid(left, xs, fills):
        for i in range(columns):
            f.rect(left + xs[i], top, xs[i + 1] - xs[i], height, fills[i])
        for x in xs:
            f.line([(left + x, top), (left + x, top + height)], BLUE, 1.4)
        for j in range(rows + 1):
            f.line([(left + xs[0], top + j * cell), (left + xs[-1], top + j * cell)], BLUE, 1.4)

    flat = [i * cell for i in range(columns + 1)]
    after = [(moved(-math.pi + 2 * math.pi * i / columns, 1)[0] + math.pi) / (2 * math.pi) * width for i in range(columns + 1)]
    left_a, left_b = 32, 484
    grid(left_a, flat, [FILL] * columns)
    grid(left_b, after, [TEAL_FILL if w < 1 else GOLD_FILL for w in widths])
    f.text(left_a + width / 2, 28, "flat grid", 14, fill=GRAY, anchor="middle")
    f.text(left_b + width / 2, 28, "after the sideways move", 14, fill=GRAY, anchor="middle")
    f.arrow([(left_a + width + 30, top + height / 2), (left_b - 30, top + height / 2)], GRAY, 1.8, 12)

    below = top + height + 24
    for x, anchor in [(0, "start"), (width / 2, "middle"), (width, "end")]:
        label = "crest" if anchor == "middle" else "trough"
        f.text(left_b + x, below, label, 14, "bold", anchor=anchor)
        f.text(left_b + x, below + 22, "squares shrink" if anchor == "middle" else "squares grow", 13.5, "italic",
               TEAL if anchor == "middle" else GOLD_TEXT, anchor)
    f.text(left_a + width / 2, below, "one wavelength, seen from above", 13.5, "italic", GRAY, "middle")
    return f


FIGURES = [one_frame_of_the_ocean, wave_energy_by_wavelength, crests_troughs_and_wavelength, a_gaussian_bell_curve,
           points_moved_toward_the_crests, grid_squeezed_at_the_crest]
