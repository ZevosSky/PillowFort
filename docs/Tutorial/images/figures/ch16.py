"""Chapter 16, Lights: authored figures.

@author Gary Yang
@brief Figures for 16-Lights.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


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


def box(f, x, y, w, h, title, notes=(), kind="pass", font="mono-bold"):
    """The kit's node with a code name as its title and up to two note lines, each a list of runs."""
    if not notes:
        node(f, x, y, w, h, title, "", kind, font)
        return
    node(f, x, y, w, h, "", "", kind)
    first = y - 9 * len(notes)
    f.text(x + w / 2, first, title, 15, font, anchor="middle")
    for i, parts in enumerate(notes):
        runs(f, x + w / 2, first + 22 + 18 * i, [(t, fnt, GRAY) for t, fnt in parts], 13, "middle")


def light_route():
    f = Figure("light-route", 880, 524,
               "A light's route through the engine: importLight turns each UsdLux light type into a scene::Light on a "
               "node, and every frame, in the demo's Record, Scene::CollectLights resolves each against its node's world "
               "matrix into LightItems plus the ambient, which SceneRenderer::WriteLights writes into this frame's light "
               "buffer. Mesh.frag.glsl loops over the lights, and Composite.frag.glsl applies exposure and the tone "
               "curve and encodes.",
               source="16-Lights.md, What you are actually writing")
    left, middle, right = (24, 252), (310, 276), (612, 244)   # columns: x and width

    def centre(column):
        return column[0] + column[1] / 2

    row1 = 138
    for x, label in [(99, "USD file"), (331, "UsdImport.cpp (section 3)"), (centre(right), "Scene (section 2)")]:
        f.text(x, 30, label, 14, fill=GRAY, anchor="middle")
    types = ["DistantLight", "SphereLight", "RectLight", "DiskLight", "DomeLight"]
    for i, name in enumerate(types):
        y = row1 + (i - 2) * 38
        node(f, 24, y, 150, 30, name, "", "input", "mono-bold", 14)
        f.line([(174, y), (198, y)])
    f.line([(198, row1 - 76), (198, row1 + 76)])
    f.arrow([(198, row1), (236, row1)])
    box(f, 236, row1, 190, 46, "importLight")
    f.arrow([(426, row1), (right[0], row1)])
    box(f, right[0], row1, right[1], 58, "scene::Light", [[("on a node", "regular")]], "data")
    f.text(centre(right) - 14, row1 + 54, "authored values,", 13.5, "italic", GRAY, "end")
    f.text(centre(right) - 14, row1 + 73, "in the light's own space", 13.5, "italic", GRAY, "end")

    divider = 254
    f.line([(24, divider), (856, divider)], HAIR, 1.4)
    label = [("every frame, in the demo's", "regular", GRAY), ("Record", "mono", GRAY)]
    width = sum(measure(t, 14, fnt)[0] for t, fnt, _ in label) + 14 * 0.36
    f.rect(310 - 10, divider - 12, width + 20, 24, WHITE)
    runs(f, 310, divider, label, 14)

    row2, row3 = 306, 384
    box(f, right[0], row2, right[1], 46, "Scene::CollectLights")
    node(f, middle[0], row2, middle[1], 46, "resolveLight(light, node.world)", "", "pass", "mono-bold", 14)
    box(f, left[0], row2, left[1], 46, "LightItem[] + ambient", kind="data")
    f.arrow([(centre(right), row1 + 29), (centre(right), row2 - 23)])
    f.arrow([(right[0], row2), (middle[0] + middle[1], row2)])
    f.arrow([(middle[0], row2), (left[0] + left[1], row2)])
    f.arrow([(centre(left), row2 + 23), (centre(left), row3 - 23)])
    box(f, left[0], row3, left[1], 46, "SceneRenderer::WriteLights")
    node(f, middle[0], row3, middle[1], 58, "this frame's light buffer", "section 4, set 0 binding 1", "data")
    f.arrow([(left[0] + left[1], row3), (middle[0], row3)])

    divider = 436
    f.line([(24, divider), (856, divider)], HAIR, 1.4)
    row4 = 482
    # Nudged right of the light buffer's centre to leave the legend room, still under the buffer's arrow.
    mesh = (centre(middle) - 134, 292)
    composite = (628, 228)
    box(f, mesh[0], row4, mesh[1], 62, "Mesh.frag.glsl",
        [[("for each light,", "regular"), ("evaluatePreviewSurface;", "mono")], [("plus the ambient (section 5)", "regular")]], "shader")
    box(f, composite[0], row4, composite[1], 62, "Composite.frag.glsl",
        [[("exposure, tone curve, encode", "regular")], [("section 6", "regular")]], "shader")
    f.arrow([(centre(middle), row3 + 29), (centre(middle), row4 - 31)])
    f.arrow([(mesh[0] + mesh[1], row4), (composite[0], row4)])

    # The same legend words as the material's route in Chapter 15, which this figure is introduced against.
    for x, y, kind, text in [(24, 466, "input", "in the USD file"), (178, 466, "pass", "C++ code"),
                             (24, 498, "data", "data"), (178, 498, "shader", "shader")]:
        swatch(f, x, y, kind, text)
    return f


def solid_angle_of_a_ball():
    radius, distance, sphere = 66.0, 500.0, 112.0       # r, d and the unit sphere's radius, in pixels
    half_angle = math.asin(radius / distance)
    exact = 2 * math.pi * (1 - math.cos(half_angle))     # the cap's true solid angle, in units of the unit sphere
    approximate = math.pi * radius ** 2 / distance ** 2   # the chapter's pi r^2 / d^2
    assert abs(exact / approximate - 1) < 0.01            # "about": within 1 % at this size

    f = Figure("solid-angle-of-a-ball", 830, 392,
               "A ball of radius r at distance d sends light through a narrow cone to a shaded point inside a sphere of "
               "radius 1, covering a small patch of that sphere. The patch's area, about pi r squared over d squared, is "
               "the ball's solid angle.",
               kind="computed plot", source="16-Lights.md, section 2 (What intensity measures)",
               parameters={"rOverD": round(radius / distance, 4), "halfAngleDegrees": round(math.degrees(half_angle), 3),
                           "exactOverApproximate": round(exact / approximate, 4)})
    ball, point = (122.0, 160.0), (122.0 + distance, 160.0)
    along = math.sqrt(distance ** 2 - radius ** 2)

    def from_point(degrees, reach):
        u = unit(degrees)
        return (point[0] + u[0] * reach, point[1] + u[1] * reach)

    upper, lower = 180 - math.degrees(half_angle), 180 + math.degrees(half_angle)
    f.polygon([point, from_point(upper, along), from_point(lower, along)], GOLD_FILL)
    f.line([from_point(upper, along), point], GOLD_SOFT, 1.3)
    f.line([from_point(lower, along), point], GOLD_SOFT, 1.3)
    for angle in (180 - math.degrees(half_angle) * 0.45, 180 + math.degrees(half_angle) * 0.45):
        f.arrow([from_point(angle, distance - radius - 34), from_point(angle, sphere + 12)], GOLD, 2.0, 12)

    f.circle(*point, sphere, "none", GRAY, 1.4)
    f.arc(point[0], point[1], sphere, upper, lower, TEAL, 7)
    f.line([point, from_point(-40, sphere)], LINE, 1.3)
    one = from_point(-40, sphere / 2)
    f.text(one[0] + 10, one[1] + 10, "1", 16, "italic", GRAY, "middle")
    f.circle(*point, 6, INK, WHITE, 2)

    f.circle(*ball, radius, GOLD_SOFT, GOLD, 1.8)
    f.line([ball, (ball[0], ball[1] - radius)], GOLD_TEXT, 1.6)
    f.circle(*ball, 3.5, GOLD_TEXT)
    f.text(ball[0] + 13, ball[1] - radius / 2, "r", 18, "italic", GOLD_TEXT, "middle")

    f.text(ball[0], ball[1] - radius - 24, "ball, radius r", 15, anchor="middle")
    f.text(point[0], point[1] - sphere - 22, "shaded point, inside a sphere of radius 1", 15, anchor="middle")
    f.text(ball[0] + 220, ball[1] - 58, "light from the ball", 14, "italic", GOLD_TEXT, "middle")

    y = point[1] + sphere + 30
    f.line([(ball[0], ball[1] + radius + 8), (ball[0], y + 8)], LINE, 1.1, "3 4")
    f.line([(point[0], point[1] + sphere + 6), (point[0], y + 8)], LINE, 1.1, "3 4")
    f.arrow([(ball[0], y), (point[0], y)], LINE, 1.3, 9, both=True)
    f.rect((ball[0] + point[0]) / 2 - 14, y - 12, 28, 24, WHITE)
    f.text((ball[0] + point[0]) / 2, y, "d", 18, "italic", anchor="middle")

    key_x, key_y = 40, y + 44
    f.arc(key_x + 70, key_y + 1, 70, 172, 188, TEAL, 7)
    f.text(key_x + 16, key_y, "the patch of the unit sphere the ball covers. Its area, about π r² / d², is the ball's", 14.5)
    f.text(key_x + 16, key_y + 21, "solid angle: the silhouette's area, π r², shrunk by the distance squared.", 14.5)
    return f


FIGURES = [light_route, solid_angle_of_a_ball]
