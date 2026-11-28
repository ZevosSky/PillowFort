"""Chapter 18, Anti-Aliasing: authored figures.

@author Gary Yang
@brief Figures for 18-Anti-Aliasing.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def what_the_scene_pass_draws_into():
    f = Figure("what-the-scene-pass-draws-into", 880, 420,
               "With one sample the scene pass draws straight into the scene target and scene depth; with N samples it "
               "draws into a transient multisampled color and depth, which the hardware resolves at the end of the pass,"
               " color by AVERAGE and depth by MAX or SAMPLE_ZERO, into the same scene target and scene depth. After the"
               " pass everyone reads those two images, unchanged.",
               source="18-Anti-Aliasing.md, What you are actually writing")
    # The left column's boxes hold their notes with room to spare (the widest, "1 sample, SFLOAT", is about 115 px).
    left = [(24, 142), (178, 142)]
    right = [(348, 240), (608, 248)]
    divider = (left[1][0] + left[1][1] + right[0][0]) / 2
    left_middle, right_middle = (24 + left[1][0] + left[1][1]) / 2, (right[0][0] + 856) / 2
    assert measure("1 sample, SFLOAT", 13)[0] + 24 < left[0][1]
    f.line([(divider, 20), (divider, 400)], HAIR, 1.4)
    f.text(left_middle, 30, "one sample (Chapters 08-17)", 15, "bold", anchor="middle")
    f.text(right_middle, 30, "N samples (this chapter)", 15, "bold", anchor="middle")

    pass_y, multi_y, single_y, h = 84, 188, 318, 58

    def centre(column):
        return column[0] + column[1] / 2

    # One sample: the pass draws into the images everyone reads.
    node(f, left_middle - 100, pass_y, 200, 46, "scene pass")
    for column, title in zip(left, ["scene target", "scene depth"]):
        f.arrow([(centre(column), pass_y + 23), (centre(column), single_y - h / 2)])
    f.text(left_middle, (pass_y + single_y) / 2 - 20, "draws into", 13.5, "italic", GRAY, "middle")
    node(f, left[0][0], single_y, left[0][1], h, "scene target", "1 sample, SFLOAT", "data")
    node(f, left[1][0], single_y, left[1][1], h, "scene depth", "1 sample, D32", "data")

    # N samples: the pass draws into the multisampled pair, which the hardware resolves at the end of the pass.
    node(f, right_middle - 100, pass_y, 200, 46, "scene pass")
    for column in right:
        f.arrow([(right_middle + (centre(column) - right_middle) * 0.32, pass_y + 23), (centre(column), multi_y - h / 2)])
    f.text(right_middle, pass_y + 52, "draws into", 13.5, "italic", GRAY, "middle")
    node(f, right[0][0], multi_y, right[0][1], h, "multisampled color", "N samples, SFLOAT, transient", "data")
    node(f, right[1][0], multi_y, right[1][1], h, "multisampled depth", "N samples, D32, transient", "data")
    band = (multi_y + single_y) / 2
    resolve_ends = []
    for column, mode in zip(right, ["AVERAGE", "MAX or SAMPLE_ZERO"]):
        x = column[0] + 56
        f.arrow([(x, multi_y + h / 2), (x, single_y - h / 2)], TEAL, 2.2, 12)
        boxes = f.lines(x + 14, band - 9, ["resolve:", mode], 13.5, "bold", TEAL, spacing=19)
        resolve_ends.append((max(b[2] for b in boxes), x))
    # The note sits centred between the color resolve's label and the depth resolve's arrow.
    f.lines((resolve_ends[0][0] + resolve_ends[1][1]) / 2, band - 9, ["at the end of the pass,", "by the hardware"], 13.5,
            "italic", GRAY, "middle", 19)
    node(f, right[0][0], single_y, right[0][1], h, "scene target", "1 sample, SFLOAT", "data")
    node(f, right[1][0], single_y, right[1][1], h, "scene depth", "1 sample, D32", "data")

    # After the pass: the same two images in both columns.
    rule = single_y + h / 2 + 18
    for a, b, words in [(left[0][0], left[1][0] + left[1][1], "after the pass, everyone reads these"),
                        (right[0][0], right[1][0] + right[1][1], "after the pass, everyone reads these, unchanged")]:
        f.line([(a, rule - 7), (a, rule), (b, rule), (b, rule - 7)], TEAL, 1.6)
        f.text((a + b) / 2, rule + 20, words, 13.5, "bold", TEAL, "middle")
    return f


def four_samples_in_one_pixel():
    def decode(hex_colour):
        """sRGB-encoded #rrggbb to linear, the inverse of the kit's encode_srgb."""
        channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]

    # The resolve averages linear values (the scene target is SFLOAT); the composite encodes the result once.
    red, blue = decode(RED), decode(BLUE)
    average = [(r + b) / 2 for r, b in zip(red, blue)]
    purple = "#" + "".join(f"{round(encode_srgb(c) * 255):02x}" for c in average)

    f = Figure("four-samples-in-one-pixel", 880, 286,
               "One pixel with 4 samples on a square: a red triangle's edge covers the 2 left samples, the shader runs "
               "once and its red is written to those 2 while the other 2 keep their blue, and the resolve averages 2 red"
               " and 2 blue into one purple pixel.",
               source="18-Anti-Aliasing.md, section 2 (How MSAA works)",
               parameters={"samplePositions": "a square, as the chapter draws them for clarity",
                           "resolvedColour": purple, "averagedIn": "linear"})
    size, top = 128, 62
    xs = [28 + i * (size + 104) for i in range(4)]
    samples = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
    covered = [True, False, True, False]

    def edge_x(v):   # the triangle's edge across the pixel, as a fraction of its width at height v
        return 0.30 + 0.30 * v

    for x, title in zip(xs, ["one pixel, 4 samples", "edge of a red triangle", "stored samples", "resolved pixel"]):
        f.text(x + size / 2, 34, title, 14, fill=GRAY, anchor="middle")
    for a, b in zip(xs, xs[1:]):
        f.arrow([(a + size + 18, top + size / 2), (b - 18, top + size / 2)], GRAY, 1.7, 11)

    # 1. The pixel and its 4 sample positions.
    f.rect(xs[0], top, size, size, FILL, LINE, 1.6, 3)
    for u, v in samples:
        f.circle(xs[0] + u * size, top + v * size, 7, INK)

    # 2. A red triangle's edge crosses it; the samples left of the edge are covered.
    x = xs[1]
    f.polygon([(x + edge_x(0) * size, top), (x + size, top), (x + size, top + size), (x + edge_x(1) * size, top + size)],
              BLUE, opacity=0.85)
    f.polygon([(x, top), (x + edge_x(0) * size, top), (x + edge_x(1) * size, top + size), (x, top + size)], RED,
              opacity=0.85)
    f.line([(x + edge_x(0) * size, top), (x + edge_x(1) * size, top + size)], INK, 1.6)
    f.rect(x, top, size, size, "none", LINE, 1.6, 3)
    for (u, v), inside in zip(samples, covered):
        assert (u < edge_x(v)) == inside
        f.circle(x + u * size, top + v * size, 7, WHITE if inside else INK, INK if inside else WHITE, 2)

    # 3. What each sample holds now.
    x = xs[2]
    f.rect(x, top, size, size, FILL, LINE, 1.6, 3)
    for (u, v), inside in zip(samples, covered):
        f.circle(x + u * size, top + v * size, 15, RED if inside else BLUE)
        f.text(x + u * size, top + v * size, "R" if inside else "B", 15, "bold", WHITE, "middle")

    # 4. The resolve's average.
    f.rect(xs[3], top, size, size, purple, LINE, 1.6, 3)

    notes = [(xs[1], ["covers the 2 left samples;", "the other 2 keep their blue"]),
             (xs[2], ["shader runs once → red;", "written to the 2 covered", "samples"]),
             (xs[3], ["average: 2 red, 2 blue", "= purple"])]
    for x, lines in notes:
        f.lines(x + size / 2, top + size + 30, lines, 13.5, anchor="middle", spacing=19)
    return f


FIGURES = [what_the_scene_pass_draws_into, four_samples_in_one_pixel]
