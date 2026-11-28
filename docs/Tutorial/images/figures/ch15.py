"""Chapter 15, Materials and Textures: authored figures.

@author Gary Yang
@brief Figures for 15-Materials-And-Textures.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def shading_directions():
    f = Figure("shading-directions", 880, 300,
               "Four unit vectors leaving a shaded point on a surface: n straight up, l toward the light, v toward the eye, "
               "and h exactly halfway between l and v.",
               source="15-Materials-And-Textures.md, section 9 (Two words for light, and four directions)")
    ox, oy, length = 290, 252, 170

    def tip(vector, reach):
        return (ox + vector[0] * reach, oy + vector[1] * reach)

    l_angle, v_angle = 127.0, 25.0
    l, v, n = unit(l_angle), unit(v_angle), unit(90)
    total = (l[0] + v[0], l[1] + v[1])
    size = math.hypot(*total)
    h = (total[0] / size, total[1] / size)  # normalize(l + v), computed rather than placed
    h_angle = math.degrees(math.atan2(-h[1], h[0]))

    f.hatch(48, 532, oy)
    f.line([(48, oy), (532, oy)], INK, 2.2)
    f.text(544, oy, "surface", 14, fill=GRAY)

    radius = 86
    for start, end in [(v_angle, h_angle), (h_angle, l_angle)]:
        f.arc(ox, oy, radius, start, end, TEAL, 1.3)
        middle = unit((start + end) / 2)
        f.line([tip(middle, radius - 6), tip(middle, radius + 6)], TEAL, 1.3)

    for vector, color, dash in [(n, INK, None), (l, GOLD, None), (v, BLUE, None), (h, TEAL, "9 6")]:
        f.arrow([(ox, oy), tip(vector, length)], color, 2.6, 15, dash)
    label_ink = {"n": INK, "l": GOLD_TEXT, "v": BLUE, "h": TEAL}
    for vector, name, reach, dx in [(n, "n", 190, -10), (l, "l", 188, -12), (v, "v", 190, 4), (h, "h", 190, 10)]:
        px, py = tip(vector, reach)
        f.text(px + dx, py, name, 21, "vector", label_ink[name], "middle")
    f.circle(ox, oy, 6, INK, WHITE, 2)

    sx, sy = tip(l, 232)
    for i in range(10):
        ray = unit(36 * i)
        f.line([(sx + ray[0] * 18, sy + ray[1] * 18), (sx + ray[0] * 26, sy + ray[1] * 26)], GOLD, 2)
    f.circle(sx, sy, 13, GOLD_SOFT, GOLD, 1.6)

    ex, ey = tip(v, 236)
    f.add(f'<path d="M{number(ex - 24)} {number(ey)} Q{number(ex)} {number(ey - 25)} {number(ex + 24)} {number(ey)} '
          f'Q{number(ex)} {number(ey + 25)} {number(ex - 24)} {number(ey)} Z" fill="{WHITE}" stroke="{BLUE}" stroke-width="2" stroke-linejoin="round"/>')
    f.circle(ex, ey, 7.5, BLUE)

    rows = [("n", "the surface normal"), ("l", "toward the light"), ("v", "toward the eye"), ("h", "halfway between l and v:")]
    y = 74
    for name, text in rows:
        f.text(636, y, name, 18, "vector", label_ink[name])
        f.text(662, y, text, 15)
        y += 38
    f.text(662, y - 16, "normalize(l + v)", 15)
    return f


def box(f, x, y, w, h, title, note="", kind="pass", font="mono-bold"):
    """The kit's node, with a code name as its title."""
    node(f, x, y, w, h, title, note, kind, font)


def material_route():
    f = Figure("material-route", 880, 548,
               "A material's route through the engine: the USD file's Material, UsdPreviewSurface and UsdUVTexture are "
               "imported into scene::Material and scene::TextureImage, which UsdViewerDemo::Setup uploads through "
               "SceneRenderer's AddTexture and AddMaterial as a GpuTexture and a MaterialParameters uniform buffer with "
               "set 1. RecordDraws binds set 1 when the material changes, and Mesh.frag.glsl samples it.",
               source="15-Materials-And-Textures.md, What you are actually writing")
    h = 46
    row_a, row_b = 82, 146
    for x, label in [(175, "USD file"), (460, "UsdImport.cpp (sections 2-4)"), (694, "Scene (section 3)")]:
        f.text(x, 32, label, 14, fill=GRAY, anchor="middle")

    box(f, 24, row_a, 96, h, "Material", kind="input")
    box(f, 148, row_a, 178, h, "UsdPreviewSurface", kind="input")
    box(f, 194, row_b, 132, h, "UsdUVTexture", kind="input")
    box(f, 362, row_a, 196, h, "importMaterial")
    box(f, 362, row_b, 196, h, "importTextureImage")
    box(f, 596, row_a, 196, h, "scene::Material", kind="data")
    box(f, 596, row_b, 196, h, "scene::TextureImage", kind="data")
    f.arrow([(120, row_a), (148, row_a)])
    f.arrow([(168, row_a + h / 2), (168, row_b), (194, row_b)])
    for y in (row_a, row_b):
        f.arrow([(326, y), (362, y)])
        f.arrow([(558, y), (596, y)])
    f.text(596, row_b + 44, "plain data: numbers, pixels,", 13.5, "italic", GRAY)
    f.text(596, row_b + 63, "texture indices", 13.5, "italic", GRAY)

    divider = 236
    f.line([(24, divider), (856, divider)], HAIR, 1.4)
    f.text(24, divider + 24, "SceneRenderer (sections 5-7)", 14, fill=GRAY)
    r1, r2, r3 = 300, 366, 428
    setup_y = (r1 + r2) / 2
    box(f, 610, setup_y, 230, 62, "UsdViewerDemo::Setup", "uploads both, in index order")
    for y in (row_a, row_b):
        f.line([(792, y), (818, y)])
    f.arrow([(818, row_a), (818, setup_y - 31)])

    box(f, 382, r1, 150, h, "AddTexture")
    box(f, 382, r2, 150, h, "AddMaterial")
    box(f, 382, r3, 150, h, "RecordDraws")
    f.arrow([(610, setup_y), (571, setup_y), (571, r1), (532, r1)])
    f.arrow([(610, setup_y), (571, setup_y), (571, r2), (532, r2)])
    box(f, 24, r1, 312, 56, "GpuTexture", "mip chain, section 5", "data")
    box(f, 24, r2, 312, 56, "MaterialParameters", "uniform buffer + set 1", "data")
    f.arrow([(382, r1), (336, r1)])
    f.arrow([(382, r2), (336, r2)])
    f.arrow([(382, r3), (342, r3)])
    f.text(332, r3, "binds set 1 when the material changes", 15, anchor="end")

    divider = 466
    f.line([(24, divider), (856, divider)], HAIR, 1.4)
    shader_y = 510
    box(f, 24, shader_y, 530, 60, "Mesh.frag.glsl", "samples set 1 (section 8); a BRDF, normal maps, cutouts (sections 9-11)", "shader")
    f.arrow([(457, r3 + h / 2), (457, shader_y - 30)])

    for x, y, kind, label in [(584, 494, "input", "in the USD file"), (740, 494, "pass", "C++ code"),
                              (584, 526, "data", "data"), (740, 526, "shader", "shader")]:
        swatch(f, x, y, kind, label)
    return f


def pixel_footprint_and_anisotropy():
    texels, panel_texel = 16, 12
    f = Figure("pixel-footprint-and-anisotropy", 800, 418,
               "One screen pixel on a floor seen at a glancing angle covers a strip of texture 16 texels long and 1 texel wide. "
               "The mip level for 16 texels filters a square far wider than the strip, so it blurs across the strip as well as "
               "along it; the level for 1 texel reads one texel, sharp across but aliasing along the strip; anisotropic "
               "filtering spreads filtered samples along the strip's long axis.",
               source="15-Materials-And-Textures.md, section 5 (Anisotropic filtering needs a device feature)",
               parameters={"footprintTexels": [texels, 1]})

    # The pixel and its footprint.
    top_y, size = 70, 22
    f.text(84, 34, "one screen pixel", 14, fill=GRAY, anchor="middle")
    f.rect(84 - size / 2, top_y - size / 2, size, size, BLUE_FILL, BLUE, 1.6, 2)
    f.arrow([(116, top_y), (176, top_y)])
    strip_x, cell = 196, 21
    f.text(strip_x + texels * cell / 2, 34, "its footprint on a receding floor", 14, fill=GRAY, anchor="middle")
    f.rect(strip_x, top_y - cell / 2, texels * cell, cell, GOLD_FILL, GOLD, 1.5, 1)
    for i in range(1, texels):
        f.line([(strip_x + i * cell, top_y - cell / 2), (strip_x + i * cell, top_y + cell / 2)], GOLD_SOFT, 1)
    f.text(strip_x + texels * cell + 20, top_y, "16 texels long, 1 texel wide", 15)

    # Three ways to filter it, each over the same 16 x 16 texels around the strip.
    span = texels * panel_texel
    panels = [36 + i * (span + 76) for i in range(3)]
    panel_top = 124
    centre_y = panel_top + span / 2
    titles = [("the level for 16 texels", "blurry across the strip", "as well as along it"),
              ("the level for 1 texel", "sharp across, but", "aliasing along it"),
              ("anisotropic filtering", "filtered samples spread", "along the long axis")]
    for index, x in enumerate(panels):
        f.rect(x, panel_top, span, span, WHITE, HAIR, 1)
        for i in range(1, texels):
            f.line([(x + i * panel_texel, panel_top), (x + i * panel_texel, panel_top + span)], GRID, 1)
            f.line([(x, panel_top + i * panel_texel), (x + span, panel_top + i * panel_texel)], GRID, 1)
        strip_top = centre_y - panel_texel / 2
        f.rect(x, strip_top, span, panel_texel, GOLD_FILL, GOLD, 1.4, 1)
        if index == 0:
            f.rect(x, panel_top, span, span, TEAL_FILL, TEAL, 1.8, 2, opacity=0.62)
            f.rect(x, strip_top, span, panel_texel, "none", GOLD, 1.4, 1)
            f.circle(x + span / 2, centre_y, 5, TEAL, WHITE, 1.4)
        elif index == 1:
            cx = x + 8 * panel_texel
            f.rect(cx - panel_texel, strip_top, panel_texel, panel_texel, TEAL, TEAL, 1.2, 1)
        else:
            # Probes one texel across that touch, so together they cover the whole strip with no gaps. No count is
            # labelled: the chapter says maxAnisotropy does not promise a number of fetches.
            for i in range(texels):
                f.circle(x + (i + 0.5) * panel_texel, centre_y, panel_texel / 2 - 0.4, TEAL_FILL, TEAL, 1.3)
        title, *notes = titles[index]
        f.text(x + span / 2, panel_top + span + 26, title, 15, "bold", anchor="middle")
        f.lines(x + span / 2, panel_top + span + 50, notes, 13.5, fill=GRAY, anchor="middle", spacing=19)
    return f


def tangent_frame_on_a_quad():
    f = Figure("tangent-frame-on-a-quad", 736, 312,
               "One textured quad seen from the front, with the frame at a point on it: the tangent T points right along the "
               "image, toward +u; the bitangent B points up the image; the normal N points out of the page, toward you.",
               source="15-Materials-And-Textures.md, section 10 (Tangents)")
    left, top, width, height, cell = 40, 74, 320, 180, 20
    f.rect(left, top, width, height, FILL, "none", 1.2, 2)
    for x in range(left + cell, left + width, cell):
        f.line([(x, top), (x, top + height)], GRID, 1)
    for y in range(top + cell, top + height, cell):
        f.line([(left, y), (left + width, y)], GRID, 1)
    f.rect(left, top, width, height, "none", INK, 1.6, 2)   # the border last, so the grid does not cut it
    f.text(left + width / 2, top + height + 26, "one textured quad, seen from the front", 14, "italic", GRAY, "middle")

    ox, oy = left + width / 2, top + height / 2
    f.arrow([(ox + 12, oy), (left + width + 46, oy)], BLUE, 2.6, 15)
    f.arrow([(ox, oy - 12), (ox, top - 40)], TEAL, 2.6, 15)
    f.circle(ox, oy, 10, WHITE, INK, 2.2)
    f.circle(ox, oy, 3.6, INK)
    f.text(left + width + 62, oy, "T", 21, "vector", BLUE, "middle")
    f.text(ox + 20, top - 46, "B", 21, "vector", TEAL, "middle")
    f.text(ox - 22, oy + 22, "N", 21, "vector", INK, "middle")

    rows = [("T", BLUE, "right along the image, +u"), ("B", TEAL, "up the image"), ("N", INK, "out of the page, toward you")]
    y = 118
    for name, colour, text in rows:
        f.text(482, y, name, 18, "vector", colour)
        f.text(510, y, text, 15)
        y += 38
    return f


FIGURES = [material_route, pixel_footprint_and_anisotropy, shading_directions, tangent_frame_on_a_quad]
