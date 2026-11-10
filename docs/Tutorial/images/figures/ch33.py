"""Chapter 33, Path Tracing: authored figures.

@author Gary Yang
@brief Figures for 33-Path-Tracing.md
@copyright (C) Gary 2026
"""
from pathlib import Path
import math
import re

from figure_kit import *

CHAPTER = Path(__file__).resolve().parents[2] / "33-Path-Tracing.md"
RED_FILL = "#f6dcd6"


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


def glowing_sphere(f, x, y, r=21):
    """The scene's light: a sphere like the others, in gold, with a halo. The chapter's scene has no sun."""
    f.circle(x, y, r + 11, GOLD_FILL)
    f.circle(x, y, r + 5, "none", GOLD_SOFT, 1.4)
    f.circle(x, y, r, GOLD_SOFT, GOLD, 1.8)


def eye(f, x, y, color=BLUE):
    """The eye glyph Chapter 15's shading figure uses."""
    f.add(f'<path d="M{number(x - 24)} {number(y)} Q{number(x)} {number(y - 25)} {number(x + 24)} {number(y)} '
          f'Q{number(x)} {number(y + 25)} {number(x - 24)} {number(y)} Z" fill="{WHITE}" stroke="{color}" '
          f'stroke-width="2" stroke-linejoin="round"/>')
    f.circle(x, y, 7.5, color)


def light_arriving_at_a_point():
    f = Figure("light-arriving-at-a-point", 880, 298,
               "A point P on the floor. Light arrives at it from every direction above it, from the sky, the light and "
               "the red sphere among them, and some of each is reflected toward the eye.",
               source="33-Path-Tracing.md, section 0 (What a pixel should show)")
    px, py = 318, 250

    def at(angle, reach):
        u = unit(angle)
        return (px + u[0] * reach, py + u[1] * reach)

    f.hatch(60, 566, py)
    f.line([(60, py), (566, py)], INK, 2.2)
    f.text(578, py, "floor", 14, fill=GRAY)

    # Every direction above the point: a fan of faint arrivals inside a dashed half circle.
    f.arc(px, py, 150, 0, 90, LINE, 1.2, "4 5")
    f.arc(px, py, 150, 90, 180, LINE, 1.2, "4 5")
    named = {"light": 54, "sky": 108, "red sphere": 144}
    for angle in range(18, 163, 18):
        if all(abs(angle - a) > 9 for a in named.values()):
            f.arrow([at(angle, 146), at(angle, 46)], LINE, 1.2, 8)

    # The named arrivals, each from its source, and the reflection toward the eye.
    tip = 24   # where the named arrivals stop short of P, leaving room for its label
    f.arrow([at(named["light"], 172), at(named["light"], tip)], GOLD, 2.4, 13)
    sx, sy = at(named["light"], 206)
    glowing_sphere(f, sx, sy)
    f.text(sx + 42, sy, "light", 15, "bold", GOLD_TEXT)

    f.arrow([at(named["sky"], 196), at(named["sky"], tip)], BLUE, 2.4, 13)
    kx, ky = at(named["sky"], 214)
    f.text(kx, ky, "sky", 15, "bold", BLUE, "middle")

    f.arrow([at(named["red sphere"], 178), at(named["red sphere"], tip)], RED, 2.4, 13)
    rx, ry = at(named["red sphere"], 206)
    f.circle(rx, ry, 21, RED_FILL, RED, 1.8)
    f.text(rx - 30, ry, "red sphere", 15, "bold", RED, "end")

    eye_angle = 174
    f.arrow([at(eye_angle, 16), at(eye_angle, 196)], TEAL, 2.8, 14)
    ex, ey = at(eye_angle, 222)
    eye(f, ex, ey)
    f.text(ex, ey - 30, "eye", 15, "bold", BLUE, "middle")

    f.circle(px, py, 6, INK, WHITE, 2)
    f.text(px + 22, py - 14, "P", 16, "bold")

    nx = 588   # the note's left edge: it ends about 31 px from the card's right edge, as "red sphere" starts on the left
    f.lines(nx, 112, ["light arrives from every direction", "above the point, and some of each"], 15)
    runs(f, nx, 112 + 2 * 15 * 1.35, [("is reflected ", "regular", INK), ("toward the eye", "bold", TEAL)])
    return f


def from_a_pixel_to_a_ray():
    f = Figure("from-a-pixel-to-a-ray", 880, 356,
               "From a pixel to a ray: the pixel becomes NDC from -1 to 1, with y = -1 at the top. With depth 1 and w = 1, "
               "inverse(projection × view) takes it back to the far point scaled by 1/w; dividing by w gives a world point "
               "on the far plane, and the ray runs from the camera towards it.",
               source="33-Path-Tracing.md, section 3 (From a pixel to a ray)")
    spine = 290
    rows = [52, 176, 300]
    h = 52

    node(f, 24, rows[0], 120, h, "pixel (x, y)", kind="input")
    ndc_x, ndc_w = 172, 236
    node(f, ndc_x, rows[0], ndc_w, h + 8, "NDC", "x and y from −1 to 1", "plain")
    f.arrow([(144, rows[0]), (ndc_x, rows[0])])

    # The NDC square: which corner is which, as cameraRayDirection's comment states it.
    sq_x, sq_y, sq = 494, 28, 64   # top level with the NDC box; small enough that "(1, 1)" stays clear of the note below
    f.rect(sq_x, sq_y, sq, sq, FILL, LINE, 1.3, 2)
    f.circle(sq_x, sq_y, 5, BLUE, WHITE, 1.6)
    f.circle(sq_x + sq, sq_y + sq, 5, BLUE, WHITE, 1.6)
    f.text(sq_x - 12, sq_y + 8, "(−1, −1)", 13.5, anchor="end")
    f.text(sq_x + sq + 12, sq_y + sq - 6, "(1, 1)", 13.5)
    f.text(sq_x + sq + 12, sq_y + 8, "y = −1 is the TOP:", 14, "bold", GOLD_TEXT)
    f.text(sq_x + sq + 12, sq_y + 28, "Vulkan’s Y-down", 14, fill=GOLD_TEXT)
    f.arrow([(sq_x + sq / 2, sq_y + 14), (sq_x + sq / 2, sq_y + sq - 10)], GOLD, 1.8, 10)
    f.line([(ndc_x + ndc_w, rows[0]), (sq_x - 6, rows[0])], LINE, 1.2, "4 4")

    code = "inverse(projection × view) × (ndc.x, ndc.y, 1, 1)"
    code_w = measure(code, 15, "mono-bold")[0] + 44
    node(f, spine - code_w / 2, rows[1], code_w, h + 8, code, "= the far point, but scaled by 1/w", "plain", "mono-bold")

    world_title = "a world point on the far plane"
    world_w = measure(world_title, 15, "bold")[0] + 44
    node(f, spine - world_w / 2, rows[2], world_w, h, world_title, kind="plain")
    ray_x = spine + world_w / 2 + 48
    node(f, ray_x, rows[2], 856 - ray_x, h + 8, "the ray", "from the camera, towards that point", "teal")
    f.arrow([(spine + world_w / 2, rows[2]), (ray_x, rows[2])])

    for (top, bottom), note in zip([(rows[0], rows[1]), (rows[1], rows[2])],
                                   ["pick depth 1, the far plane, and w = 1",
                                    "divide by w: Chapter 10 section 2’s divide, run backwards"]):
        upper = top + (h + 8) / 2
        lower = bottom - (h + 8) / 2 if bottom != rows[2] else bottom - h / 2
        f.arrow([(spine, upper), (spine, lower)])
        f.text(spine + 16, (upper + lower) / 2, note, 14, "italic", GRAY)
    return f


def scene_instances():
    """Read the chapter's sceneObjects table, so the figure's positions are the code's."""
    text = CHAPTER.read_text(encoding="utf-8")
    block = text.split("static const SceneObject sceneObjects[] = {", 1)[1].split("};", 1)[0]
    rows = re.findall(r"\{\s*(\d),\s*\{\s*([-\d.]+)f,\s*([-\d.]+)f,\s*([-\d.]+)f\s*\}.*?//\s*(?:the )?(\w+)", block)
    return [(int(mesh), tuple(float(v) for v in (x, y, z)), name) for mesh, x, y, z, name in rows]


def coordinate(value):
    return f"{value:g}".replace("-", "−")


def two_level_acceleration_structure():
    instances = scene_instances()
    assert [name for _, _, name in instances] == ["floor", "red", "white", "green", "light"], instances
    text = CHAPTER.read_text(encoding="utf-8")
    segments, rings = map(int, re.search(r"makeUvSphere\(1\.0f, (\d+), (\d+)\)", text).groups())
    sphere_triangles = segments * (rings - 1) * 2   # makeUvSphere drops one triangle per cell at each pole
    plane_cells = int(re.search(r"makePlane\(1000\.0f, 1000\.0f, (\d+)\)", text).group(1))
    floor_triangles = 2 * plane_cells * plane_cells
    assert sphere_triangles == 3968 and floor_triangles == 2, (sphere_triangles, floor_triangles)

    f = Figure("two-level-acceleration-structure", 880, 326,
               "The top-level structure holds five instances: the floor points at the floor BLAS, at (0, 0, 0), and the red, "
               "white, green and light spheres all point at one sphere BLAS, at their own positions. The floor BLAS holds 2 "
               "triangles; the sphere BLAS holds 3,968, in boxes within boxes.",
               source="33-Path-Tracing.md, section 6 (Why a tree, and why two levels)",
               parameters={"instances": [[name, list(position)] for _, position, name in instances],
                           "sphereTriangles": sphere_triangles, "floorTriangles": floor_triangles})
    left, right = 24, 452
    f.text(left, 28, "TLAS (top level): five instances", 15, "bold")
    f.rect(left, 46, right - left, 262, FILL, LINE, 1.3, 10)
    swatches = {"floor": (FILL, LINE), "red": (RED_FILL, RED), "white": (WHITE, LINE), "green": ("#d9ecd9", GREEN),
                "light": (GOLD_SOFT, GOLD)}
    row_ys = [80 + 48 * i for i in range(5)]
    for (mesh, position, name), y in zip(instances, row_ys):
        f.rect(left + 14, y - 18, right - left - 28, 36, WHITE, LINE, 1.2, 7)
        fill, stroke = swatches[name]
        f.circle(left + 34, y, 8, fill, stroke, 1.5)
        target = "floor BLAS," if mesh == 1 else "sphere BLAS,"
        where = "at (" + ", ".join(coordinate(v) for v in position) + ")"
        f.text(left + 52, y, name, 15, "bold")
        f.text(left + 116, y, "→ " + target, 15)
        f.text(left + 254, y, where, 15)

    blas_x, blas_r = 566, 856
    f.text(blas_x, 28, "BLAS (bottom level): one per mesh", 15, "bold")
    node(f, blas_x, row_ys[0], blas_r - blas_x, 40, "", kind="data")
    runs(f, blas_x + 18, row_ys[0], [("floor:", "bold", INK), (f"{floor_triangles} triangles", "regular", INK)])
    f.arrow([(right, row_ys[0]), (blas_x, row_ys[0])], INK, 1.8)

    top, bottom = row_ys[1] - 22, row_ys[4] + 22
    f.rect(blas_x, top, blas_r - blas_x, bottom - top, GOLD_FILL, GOLD, 1.4, 10)
    runs(f, blas_x + 18, top + 24, [("sphere:", "bold", INK), (f"{sphere_triangles:,} triangles,", "regular", INK)])
    f.text(blas_x + 18, top + 46, "in boxes within boxes", 15)
    # A sketch of the tree: a box holding two boxes, each holding two, each holding a few triangles.
    bx, by, bw, bh = blas_x + 22, top + 68, blas_r - blas_x - 44, bottom - top - 84
    f.rect(bx, by, bw, bh, WHITE, TEAL, 1.5, 4)
    for i in range(2):
        cx = bx + 8 + i * (bw - 8) / 2
        cw = (bw - 24) / 2
        f.rect(cx, by + 8, cw, bh - 16, TEAL_FILL, TEAL, 1.3, 3)
        for j in range(2):
            gx = cx + 6 + j * (cw - 6) / 2
            gw = (cw - 18) / 2
            f.rect(gx, by + 16, gw, bh - 32, WHITE, TEAL, 1.1, 2)
            # Two small triangles sharing an edge, a scrap of the mesh in the smallest box.
            mx, my, t = gx + gw / 2, by + bh / 2, 9
            f.polygon([(mx - t - 3, my + t), (mx - 3, my - t), (mx + t - 3, my + t)], GOLD_SOFT, GOLD, 1.1)
            f.polygon([(mx - 3, my - t), (mx + t + 3 + 3, my - t), (mx + t - 3, my + t)], GOLD_FILL, GOLD, 1.1)

    trunk = 506
    for y in row_ys[1:]:
        f.line([(right, y), (trunk, y)], INK, 1.8)
    f.line([(trunk, row_ys[1]), (trunk, row_ys[4])], INK, 1.8)
    middle = (row_ys[1] + row_ys[4]) / 2
    f.arrow([(trunk, middle), (blas_x, middle)], INK, 1.8)
    return f


FIGURES = [light_arriving_at_a_point, from_a_pixel_to_a_ray, two_level_acceleration_structure]
