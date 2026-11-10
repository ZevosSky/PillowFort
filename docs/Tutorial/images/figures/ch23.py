"""Chapter 23, The Sky: authored figures.

@author Gary Yang
@brief Figures for 23-The-Sky.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *

# Section 2's table, which CubeMap.glsl's arrays copy: per layer, the face, its centre, right and down.
CUBE_FACES = {
    0: ("+X", (1, 0, 0), (0, 0, -1), (0, -1, 0)),
    1: ("−X", (-1, 0, 0), (0, 0, 1), (0, -1, 0)),
    2: ("+Y", (0, 1, 0), (1, 0, 0), (0, 0, 1)),
    3: ("−Y", (0, -1, 0), (1, 0, 0), (0, 0, -1)),
    4: ("+Z", (0, 0, 1), (1, 0, 0), (0, -1, 0)),
    5: ("−Z", (0, 0, -1), (-1, 0, 0), (0, -1, 0)),
}
AXIS_NAMES = {(1, 0, 0): "+X", (-1, 0, 0): "−X", (0, 1, 0): "+Y", (0, -1, 0): "−Y", (0, 0, 1): "+Z", (0, 0, -1): "−Z"}


def add(a, b, k=1):
    return tuple(x + k * y for x, y in zip(a, b))


def cube_map_faces_unfolded():
    # The cross: column and row of each layer, as the chapter unfolds the cube.
    cross = {2: (1, 0), 1: (0, 1), 4: (1, 1), 0: (2, 1), 5: (3, 1), 3: (1, 2)}
    # The unfolding is a real one for faces stored as seen from outside: wherever two faces touch in the cross,
    # the edge they share is the same edge of the cube.
    for a, (ca, ra) in cross.items():
        for b, (cb, rb) in cross.items():
            _, centre_a, right_a, down_a = CUBE_FACES[a]
            _, centre_b, right_b, down_b = CUBE_FACES[b]
            if (cb, rb) == (ca + 1, ra):
                assert add(centre_a, right_a) == add(centre_b, right_b, -1), (a, b)
            if (cb, rb) == (ca, ra + 1):
                assert add(centre_a, down_a) == add(centre_b, down_b, -1), (a, b)
    # The worked example: (0.2, 0.5, -0.8) lands on -Z at 0.375 across and about 0.19 down.
    d = (0.2, 0.5, -0.8)
    _, centre, right, down = CUBE_FACES[5]
    across = sum(x * y for x, y in zip(d, right)) / 0.8
    downward = sum(x * y for x, y in zip(d, down)) / 0.8
    assert abs(across + 0.25) < 1e-12 and abs(downward + 0.625) < 1e-12 and (round((across + 1) / 2, 3), round((downward + 1) / 2, 2)) == (0.375, 0.19)

    F = 132
    x0, y0 = 24, 24
    f = Figure("cube-map-faces-unfolded", x0 + 4 * F + 24, y0 + 3 * F + 24,
               "The cube map unfolded flat, each face as its image is stored: +Y (layer 2) above +Z, the row -X (1), +Z "
               "(4), +X (0), -Z (5), and -Y (3) below +Z. Arrows on each face give its right and down: +Y right +X and "
               "down +Z, -Y right +X and down -Z, and the four in the row all down -Y, with right +Z, +X, -Z and -X in "
               "turn.",
               source="23-The-Sky.md, section 2 (Cube maps: six faces, one direction)")
    for layer, (column, row) in cross.items():
        name, _, right, down = CUBE_FACES[layer]
        x, y = x0 + column * F, y0 + row * F
        f.rect(x, y, F, F, FILL, LINE, 1.4)
        f.text(x + F / 2 + 8, y + F / 2 + 6, name, 24, "bold", anchor="middle")
        f.text(x + F / 2 + 8, y + F / 2 + 32, f"layer {layer}", 13.5, fill=GRAY, anchor="middle")
        ox, oy = x + 16, y + 16
        f.arrow([(ox, oy), (ox + 50, oy)], BLUE, 2.2, 10)
        f.text(ox + 58, oy, AXIS_NAMES[right], 14, "bold", BLUE)
        f.arrow([(ox, oy), (ox, oy + 50)], TEAL, 2.2, 10)
        f.text(ox, oy + 66, AXIS_NAMES[down], 14, "bold", TEAL, "middle")
        f.circle(ox, oy, 3.2, INK)
    # The key, beside +Y and well clear of the row of faces below it.
    kx, ky, pitch = x0 + 2 * F + 22, y0 + 14, 36
    f.arrow([(kx, ky), (kx + 34, ky)], BLUE, 2.2, 10)
    f.text(kx + 46, ky, "right: the column grows, u", 14)
    f.arrow([(kx + 8, ky + pitch - 14), (kx + 8, ky + pitch + 14)], TEAL, 2.2, 10)
    f.text(kx + 46, ky + pitch, "down: the row grows, v", 14)
    f.circle(kx + 8, ky + 2 * pitch, 3.2, INK)
    f.text(kx + 46, ky + 2 * pitch, "u = 0, v = 0", 14)
    assert ky + 2 * pitch + 30 <= y0 + F  # at least 30 px between the key's last row and the faces' row
    return f


def lat_long_image_layout():
    def uv(d):
        """latLongUv: OpenEXR's convention, which UsdLux's DomeLight uses."""
        length = math.sqrt(sum(c * c for c in d))
        x, y, z = (c / length for c in d)
        return 0.5 - math.atan2(x, z) / (2 * math.pi), 0.5 - math.asin(y) / math.pi

    columns = [(0.0, "−Z", "+180°"), (0.25, "+X", "+90°"), (0.5, "+Z", "0°"), (0.75, "−X", "−90°"), (1.0, "−Z", "−180°")]
    for u, name, _ in columns:
        direction = {"+X": (1, 0, 0), "−X": (-1, 0, 0), "+Z": (0, 0, 1), "−Z": (0, 0, -1)}[name]
        got = uv(direction)
        assert abs(got[1] - 0.5) < 1e-12 and (abs(got[0] - u) < 1e-12 or (name == "−Z" and u in (0.0, 1.0) and got[0] in (0.0, 1.0)))
    assert abs(uv((0, 1, 0))[1]) < 1e-12 and abs(uv((0, -1, 0))[1] - 1) < 1e-12
    worked = uv((1, 1, 0))
    assert all(abs(c - 0.25) < 1e-12 for c in worked)            # u = v = 0.25
    assert (round(worked[0] * 2048), round(worked[1] * 1024)) == (512, 256)

    f = Figure("lat-long-image-layout", 860, 360,
               "A latitude-longitude image twice as wide as tall: u runs 0 to 1 across, where the horizon faces -Z, +X, "
               "+Z, -X and -Z again at longitudes +180, +90, 0, -90 and -180 degrees, and v runs from 0 straight up (+Y) "
               "through 0.5 at the horizon to 1 straight down (-Y). The direction (1, 1, 0) / sqrt 2 lands at u = v = "
               "0.25.",
               kind="computed plot", source="23-The-Sky.md, section 4 (From an environment image)",
               parameters={"workedDirection": "(1, 1, 0)/sqrt(2)", "workedUv": [round(c, 4) for c in worked]})
    x0, y0, W, H = 148, 58, 480, 240

    def at(u, v):
        return (x0 + u * W, y0 + v * H)

    f.rect(x0, y0, W, H, FILL, "none")
    for u, _, _ in columns[1:-1]:
        # The gridline stops for the direction's name above the horizon; the dot covers the rest of the gap.
        horizon = at(u, 0.5)[1]
        f.line([at(u, 0), (at(u, 0)[0], horizon - 30)], LINE, 1.1)
        f.line([(at(u, 0)[0], horizon), at(u, 1)], LINE, 1.1)
    f.line([at(0, 0.5), at(1, 0.5)], INK, 1.4, "6 4")
    f.rect(x0, y0, W, H, "none", INK, 1.6)

    f.text(24, y0 - 22, "u", 14, "italic", GRAY)
    f.text(24, y0 + H + 22, "longitude", 14, "italic", GRAY)
    for u, name, longitude in columns:
        x, y = at(u, 0.5)
        f.line([(x, y0 - 6), (x, y0)], INK, 1.3)
        f.line([(x, y0 + H), (x, y0 + H + 6)], INK, 1.3)
        f.text(x, y0 - 22, f"{u:g}", 14, fill=GRAY, anchor="middle")
        f.text(x, y0 + H + 22, longitude, 14, fill=GRAY, anchor="middle")
        f.circle(x, y, 5, BLUE, WHITE, 1.5)
        anchor, dx = {0.0: ("start", 8), 1.0: ("end", -8)}.get(u, ("middle", 0))
        f.text(x + dx, y - 18, name, 16, "bold", BLUE, anchor)

    for v, lat in [(0, "+90°"), (0.5, "0°"), (1, "−90°")]:
        f.text(x0 - 10, at(0, v)[1], lat, 14, fill=GRAY, anchor="end")
    f.text(x0 - 62, y0 + H / 2, "latitude", 14, "italic", GRAY, "middle", rotate=-90)

    for v, place in [(0, "straight up (+Y)"), (0.5, "the horizon"), (1, "straight down (−Y)")]:
        y = at(1, v)[1]
        f.text(x0 + W + 18, y, f"v = {v:g}", 14, fill=GRAY)
        f.text(x0 + W + 82, y, place, 14)

    px, py = at(*worked)
    f.circle(px, py, 5.5, TEAL, WHITE, 1.6)
    f.text(px + 12, py - 4, "(1, 1, 0) / √2", 14, "bold", TEAL)
    f.text(px + 12, py + 16, "u = v = 0.25", 13.5, fill=TEAL)
    return f


FIGURES = [cube_map_faces_unfolded, lat_long_image_layout]
