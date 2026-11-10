"""Chapter 06, Shaders and Pipelines: authored figures.

@author Gary Yang
@brief Figures for 06-Shaders-And-Pipelines.md
@copyright (C) Gary 2026
"""
from matplotlib.textpath import text_to_path

from figure_kit import *


def advance(string, size, font):
    """How far a line of text moves the pen, trailing spaces included (measure() gives ink only)."""
    prop = FONTS[font].copy()
    prop.set_size(size)
    return text_to_path.get_text_width_height_descent(string, prop, False)[0]


def spans(f, x, y, string, size=14, fill=INK, code_fill=INK):
    """One line in which `backticked` parts are set in mono, as code identifiers are."""
    for i, part in enumerate(string.split("`")):
        if part:
            font = "mono" if i % 2 else "regular"
            f.text(x, y, part, size, font, code_fill if i % 2 else fill)
            x += advance(part, size, font)


def triangle_in_clip_space():
    f = Figure("triangle-in-clip-space", 640, 430,
               "The window as x and y from minus one to plus one, with y growing downward. The triangle's top corner is "
               "at (0, -0.5) in red, its lower left at (-0.5, 0.5) in blue and its lower right at (0.5, 0.5) in green, "
               "with the colors blending across it.",
               source="06-Shaders-And-Pipelines.md, section 2 (The triangle shaders)")
    cx, cy, s = 285, 226, 170

    def at(x, y):
        return (cx + s * x, cy + s * y)

    f.rect(cx - s, cy - s, 2 * s, 2 * s, FILL, LINE, 1.3, 3)
    f.line([at(-1, 0), at(1, 0)], LINE, 1, "5 6")
    f.line([at(0, -1), at(0, 1)], LINE, 1, "5 6")
    for x, label in [(-1, "x = −1"), (0, "x = 0"), (1, "x = +1")]:
        px, py = at(x, -1)
        f.line([(px, py), (px, py - 7)], LINE, 1.3)
        f.text(px, py - 22, label, 14, fill=GRAY, anchor="middle")
    for y, label in [(-1, "y = −1"), (0, "y = 0"), (1, "y = +1")]:
        px, py = at(-1, y)
        f.line([(px, py), (px - 7, py)], LINE, 1.3)
        f.text(px - 14, py, label, 14, fill=GRAY, anchor="end")

    top, right, left = at(0, -0.5), at(0.5, 0.5), at(-0.5, 0.5)
    corners = [("gt", top, (right, left), 0), ("gr", right, (left, top), 1), ("gl", left, (top, right), 2)]
    layers = []
    points = " ".join(f"{number(x)},{number(y)}" for x, y in (top, right, left))
    for name, corner, (a, b), channel in corners:
        # A barycentric weight is linear, so each corner is one gradient on its own channel. Screen then
        # sums the channels exactly. The stops apply the sRGB encode the swapchain would apply.
        ex, ey = b[0] - a[0], b[1] - a[1]
        t = ((corner[0] - a[0]) * ex + (corner[1] - a[1]) * ey) / (ex * ex + ey * ey)
        foot = (a[0] + t * ex, a[1] + t * ey)
        stops = []
        for i in range(17):
            value = i / 16
            rgb = [0, 0, 0]
            rgb[channel] = round(encode_srgb(value) * 255)
            stops.append(f'<stop offset="{number(value)}" stop-color="rgb({rgb[0]},{rgb[1]},{rgb[2]})"/>')
        f.defs.append(f'<linearGradient id="{name}" gradientUnits="userSpaceOnUse" x1="{number(foot[0])}" y1="{number(foot[1])}" '
                      f'x2="{number(corner[0])}" y2="{number(corner[1])}">{"".join(stops)}</linearGradient>')
        layers.append(f'<polygon points="{points}" fill="url(#{name})" style="mix-blend-mode:screen"/>')
    f.add(f'<g style="isolation:isolate"><polygon points="{points}" fill="#000000"/>{"".join(layers)}</g>')
    ox, oy = at(0, 0)
    f.line([(ox - 6, oy), (ox + 6, oy)], WHITE, 1.6)
    f.line([(ox, oy - 6), (ox, oy + 6)], WHITE, 1.6)

    f.circle(*top, 6.5, "#e23a30", WHITE, 2)
    f.circle(*left, 6.5, "#2a55d8", WHITE, 2)
    f.circle(*right, 6.5, "#1f9d3f", WHITE, 2)
    f.text(top[0] + 16, top[1], "(0, −0.5)  red", 15)
    f.text(left[0], left[1] + 24, "(−0.5, 0.5)", 15, anchor="middle")
    f.text(left[0], left[1] + 44, "blue", 15, anchor="middle")
    f.text(right[0], right[1] + 24, "(0.5, 0.5)", 15, anchor="middle")
    f.text(right[0], right[1] + 44, "green", 15, anchor="middle")

    arrow_x = cx + s + 36
    f.arrow([(arrow_x, top[1]), (arrow_x, right[1])], GOLD, 2.4, 14)
    f.text(arrow_x + 16, cy - 11, "+y points", 15, "bold", GOLD_TEXT)
    f.text(arrow_x + 16, cy + 11, "down", 15, "bold", GOLD_TEXT)
    return f


def pipeline_state_in_draw_order():
    f = Figure("pipeline-state-in-draw-order", 880, 570,
               "The path a draw takes, top to bottom, with the create-info field that configures each step: vkCmdDraw of "
               "3 vertices, then vertex input and input assembly, the vertex shader, viewport and scissor, rasterization "
               "and multisample, the fragment shader, depth test and color blend, and finally the color attachment.",
               source="06-Shaders-And-Pipelines.md, section 4 (The graphics pipeline)")
    groups = [
        ("input", [("vkCmdDraw(3 vertices)", None, None)]),
        ("plain", [("vertex input", "pVertexInputState", "where vertices come from: nothing yet (Chapter 11)"),
                   ("input assembly", "pInputAssemblyState", "every three vertices make a triangle")]),
        ("teal", [("VERTEX SHADER", "pStages[0]", "once per vertex: writes `gl_Position`")]),
        ("plain", [("viewport, scissor", "pViewportState", "clip space to pixels; set each frame"),
                   ("rasterization", "pRasterizationState", "culling, front face; finds the covered pixels"),
                   ("multisample", "pMultisampleState", "one sample per pixel until Chapter 18")]),
        ("teal", [("FRAGMENT SHADER", "pStages[1]", "once per fragment: writes `outColor`")]),
        ("plain", [("depth test", "pDepthStencilState", "before or after the shader; none until Chapter 10"),
                   ("color blend", "pColorBlendState", "off: the fragment replaces the pixel")]),
        ("input", [("color attachment", "VkPipelineRenderingCreateInfo", "only its format, here")]),
    ]
    left, width, field_x, note_x = 24, 192, 234, 486
    row, pad, gap = 28, 5, 24
    centre = left + width / 2
    y = 24
    for index, (kind, rows) in enumerate(groups):
        height = len(rows) * row + 2 * pad
        fill, stroke = {"input": (WHITE, LINE), "plain": (FILL, LINE), "teal": (TEAL_FILL, TEAL)}[kind]
        f.rect(left, y, width, height, fill, stroke, 1.4, 9)
        for i, (stage, field, note) in enumerate(rows):
            middle = y + pad + row * (i + 0.5)
            if i:
                f.line([(left + 10, y + pad + row * i), (left + width - 10, y + pad + row * i)], HAIR, 1)
            if field is None:
                f.text(centre, middle, stage, 13.5, "mono", anchor="middle")
                continue
            f.text(left + 13, middle, stage, 15, "bold" if kind == "teal" else "regular",
                   TEAL if kind == "teal" else INK)
            f.text(field_x, middle, field, 13.5, "mono", GRAY)
            spans(f, note_x, middle, note, 14)
        y += height
        if index < len(groups) - 1:
            f.arrow([(centre, y + 2), (centre, y + gap - 2)], GRAY, 1.6, 9)
            y += gap
    assert y + 24 == f.height, y + 24

    swatch(f, 600, 34, "teal", "a shader stage")
    swatch(f, 600, 62, "shader", "fixed-function state")
    return f


FIGURES = [triangle_in_clip_space, pipeline_state_in_draw_order]
