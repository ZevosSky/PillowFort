"""Chapter 08, Resources, Memory, and Descriptors: authored figures.

@author Gary Yang
@brief Figures for 08-Resources-And-Descriptors.md
@copyright (C) Gary 2026
"""
from matplotlib.textpath import text_to_path

from figure_kit import *


def advance(string, size, font):
    """How far a line of text moves the pen, trailing spaces included (measure() gives ink only)."""
    prop = FONTS[font].copy()
    prop.set_size(size)
    return text_to_path.get_text_width_height_descent(string, prop, False)[0]


def spans(f, x, y, string, size=14, fill=INK, code_fill=INK, anchor="start"):
    """One line in which `backticked` parts are set in mono, as code identifiers are."""
    parts = [(part, "mono" if i % 2 else "regular") for i, part in enumerate(string.split("`")) if part]
    if anchor == "middle":
        x -= sum(advance(part, size, font) for part, font in parts) / 2
    for part, font in parts:
        f.text(x, y, part, size, font, code_fill if font == "mono" else fill)
        x += advance(part, size, font)


def color_encodings_in_the_frame():
    f = Figure("color-encodings-in-the-frame", 880, 272,
               "Linear sources feed the scene shaders, which write linear values to the R16G16B16A16_SFLOAT scene target. "
               "The composite pass clamps and encodes linear to sRGB into the B8G8R8A8_UNORM swapchain, which ImGui's "
               "already-sRGB colors also reach directly, and the swapchain goes to the display.",
               source="08-Resources-And-Descriptors.md, section 4 (Linear and sRGB)")
    top, low = 64, 214

    def box(x, w, y, title, note="", kind="plain", note_font="regular"):
        fill, stroke = {"plain": (FILL, LINE), "input": (WHITE, LINE), "data": (GOLD_FILL, GOLD)}[kind]
        h = 60 if note else 48
        f.rect(x, y - h / 2, w, h, fill, stroke, 1.4, 10)
        if note:
            f.text(x + w / 2, y - 11, title, 15, "bold", anchor="middle")
            f.text(x + w / 2, y + 12, note, 13.5, note_font, GRAY, "middle")
        else:
            f.text(x + w / 2, y, title, 15, "bold", anchor="middle")

    def link(a, b, y, label):
        f.arrow([(a, y), (b, y)])
        f.text((a + b) / 2, y - 14, label, 13.5, "italic", GRAY, "middle")

    box(24, 116, top, "sources", kind="input")
    box(234, 156, top, "scene shaders")
    box(484, 228, top, "scene target", "R16G16B16A16_SFLOAT", "data", "mono")
    link(140, 234, top, "linear")
    link(390, 484, top, "linear")

    box(24, 190, low, "ImGui", "(already sRGB)")
    box(484, 228, low, "swapchain", "B8G8R8A8_UNORM", "data", "mono")
    box(770, 86, low, "display", kind="input")
    link(214, 484, low, "sRGB")
    link(712, 770, low, "sRGB")

    x = 598
    f.arrow([(x, top + 30), (x, low - 30)], TEAL, 2.4, 14)
    f.text(x + 16, (top + low) / 2 - 11, "composite:", 15, "bold", TEAL)
    f.text(x + 16, (top + low) / 2 + 11, "clamp, linear → sRGB", 15, "bold", TEAL)
    return f


def push_constant_offsets_without_padding():
    # Offsets worked out from each language's rule rather than typed in: C++ puts a float on any 4-byte
    # boundary; a push-constant block (std430) starts a vec4 on a multiple of 16.
    members = [("time", 4, 4), ("amplitude", 4, 4), ("frequency", 4, 4), ("baseColor", 16, 16)]

    def place(rows, vec4_alignment):
        offset, offsets = 0, {}
        for name, size, alignment in rows:
            step = vec4_alignment if alignment == 16 else 4
            offset = -(-offset // step) * step
            offsets[name] = offset
            offset += size
        return offsets, offset

    cpp, cpp_end = place(members, 4)
    glsl, glsl_end = place(members, 16)
    assert (cpp["baseColor"], cpp_end, glsl["baseColor"], glsl_end) == (12, 28, 16, 32)  # the chapter's table
    padded = members[:3] + [("padding0", 4, 4)] + members[3:]
    assert place(padded, 4)[0]["baseColor"] == place(padded, 16)[0]["baseColor"] == 16  # "the two agree"

    f = Figure("push-constant-offsets-without-padding", 720, 352,
               "Byte offsets 0 to 32, with padding0 removed from both sides. C++ puts time, amplitude and frequency at 0, 4 "
               "and 8 and baseColor's red, green, blue and alpha at 12 to 24, ending at 28 bytes pushed. GLSL puts the same "
               "first three members there, leaves a gap at 12 because a vec4 starts on a multiple of 16, and reads "
               "baseColor.r, g, b and a at 16 to 28.",
               kind="computed plot", source="08-Resources-And-Descriptors.md, section 8 (Where the bytes go)",
               parameters={"cppBaseColorOffset": cpp["baseColor"], "cppBytesPushed": cpp_end,
                           "glslBaseColorOffset": glsl["baseColor"], "glslBlockEnd": glsl_end})
    top, row = 62, 32

    def y_of(offset):
        return top + offset / 4 * row

    columns = {"C++": (102, 222), "GLSL": (348, 222)}
    f.text(78, 34, "offset", 13.5, fill=GRAY, anchor="end")
    for title, (x, w) in columns.items():
        lead = f"{title}, without "   # the member's name in mono, as code identifiers are everywhere else
        start = x + w / 2 - (advance(lead, 15, "bold") + advance("padding0", 15, "mono-bold")) / 2
        f.text(start, 34, lead, 15, "bold")
        f.text(start + advance(lead, 15, "bold"), 34, "padding0", 15, "mono-bold")
    for offset in range(0, glsl_end + 1, 4):
        f.text(78, y_of(offset), str(offset), 13.5, fill=GRAY, anchor="end")
        f.line([(84, y_of(offset)), (92, y_of(offset))], LINE, 1.2)

    def cell(column, offset, label, fill, stroke, dash=None, ink=INK):
        x, w = columns[column]
        f.rect(x, y_of(offset), w, row, fill, stroke, 1.3, 0, dash)
        spans(f, x + w / 2, y_of(offset) + row / 2, label, 14, ink, ink, "middle")

    channels = ["red", "green", "blue", "alpha"]
    for name in ("time", "amplitude", "frequency"):
        cell("C++", cpp[name], f"`{name}`", BLUE_FILL, BLUE)
        cell("GLSL", glsl[name], f"`{name}`", GOLD_FILL, GOLD)
    for i, channel in enumerate(channels):
        cell("C++", cpp["baseColor"] + 4 * i, f"`baseColor[{i}]`  ({channel})", BLUE_FILL, BLUE)
        cell("GLSL", glsl["baseColor"] + 4 * i, f"`baseColor.{'rgba'[i]}`", GOLD_FILL, GOLD)

    # The gap: the bytes GLSL skips so that the vec4 starts on a multiple of 16.
    x, w = columns["GLSL"]
    gap_top = y_of(glsl["frequency"] + 4)
    f.rect(x, gap_top, w, row, WHITE, LINE, 1.3, 0, "5 4")
    for i in range(12):
        sx = x + 8 + i * 18
        if abs(sx + 5 - (x + w / 2)) > 30:  # keep the word clear of the strokes
            f.line([(sx + 10, gap_top + 5), (sx, gap_top + row - 5)], LINE, 1.1)
    f.text(x + w / 2, gap_top + row / 2, "gap", 14, "italic", GRAY, "middle")
    f.text(x + w + 16, gap_top + row / 2 - 9, "a vec4 starts on", 13.5, fill=GRAY)
    f.text(x + w + 16, gap_top + row / 2 + 9, "a multiple of 16", 13.5, fill=GRAY)

    # Where C++ stops: the shader's alpha lies past it.
    x, w = columns["C++"]
    f.text(x + w / 2, y_of(cpp_end) + row / 2, f"end: {cpp_end} bytes pushed", 13.5, "italic", RED, "middle")
    f.line([(x - 6, y_of(cpp_end)), (columns["GLSL"][0] + columns["GLSL"][1] + 6, y_of(cpp_end))], RED, 1.6, "6 4")
    return f


FIGURES = [color_encodings_in_the_frame, push_constant_offsets_without_padding]
