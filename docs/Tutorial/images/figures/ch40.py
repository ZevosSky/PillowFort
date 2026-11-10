"""Chapter 40, Forests to the Horizon: authored figures.

@author Gary Yang
@brief Figures for 40-Forests-To-The-Horizon.md
@copyright (C) Gary 2026
"""
from pathlib import Path
import math
import re

from figure_kit import *

CHAPTER = Path(__file__).resolve().parents[2] / "40-Forests-To-The-Horizon.md"


def chapter_numbers():
    """The bake grid and the handover distances, as the chapter states them."""
    text = " ".join(CHAPTER.read_text(encoding="utf-8").split())   # one line, so wrapped sentences match
    elevations = [int(v) for v in re.findall(r"-?\d+", re.search(r"The elevations are ([-\d, and]+) degrees", text).group(1))]
    assert "from eight azimuths and seven elevations" in text
    enter, exit_ = map(float, re.search(r"The enter distance is (\d+) m and the exit distance is (\d+) m", text).groups())
    pool = float(re.search(r"which reaches at least (\d+) m from the camera", text).group(1))
    reach = float(re.search(r"out to its (\d+) m `TREE_REACH`", text).group(1))
    near, far = map(int, re.search(r"85 degree row are about (\d+) degrees apart, on the 10 degree row about (\d+)",
                                   text).groups())
    return elevations, 8, enter, exit_, pool, reach, near, far


def neighbour_angle(elevation, azimuth_step):
    """The angle between two baked directions on one row, azimuth_step apart: the great circle, not the row."""
    e, a = math.radians(elevation), math.radians(azimuth_step)
    return math.degrees(math.acos(math.sin(e) ** 2 + math.cos(e) ** 2 * math.cos(a)))


def impostor_views_and_handover():
    elevations, azimuths, enter, exit_, pool, reach, near, far = chapter_numbers()
    assert elevations == [-65, -40, -15, 10, 35, 60, 85], elevations
    assert (enter, exit_, pool, reach) == (490, 560, 592, 600)
    step = 360 / azimuths
    spacing = {e: neighbour_angle(e, step) for e in elevations}
    assert round(spacing[85]) == near == 4 and round(spacing[10]) == far == 44, spacing

    f = Figure("impostor-views-and-handover", 880, 600,
               "Above, the 56 baked directions of one species, 8 azimuths 45 degrees apart on each of 7 elevation rows "
               "from -65 to 85 degrees, drawn at their true spacing on the sphere: neighbours on the 85 degree row are "
               "about 4 degrees apart, on the 10 degree row about 44. Below, the handover by distance: a mesh tree "
               "stays a mesh until 560 m, an impostor becomes a mesh only inside 490 m, between the two a tree keeps "
               "last frame's owner, and the near pool reaches at least 592 m in every direction, inside its 600 m "
               "TREE_REACH.",
               kind="computed plot", source="40-Forests-To-The-Horizon.md, sections 1 and 2",
               parameters={"azimuths": azimuths, "elevations": elevations, "meshEnterMetres": enter,
                           "meshExitMetres": exit_, "poolReachMetres": pool, "treeReachMetres": reach,
                           "neighbourDegrees": {str(e): round(spacing[e], 1) for e in elevations}})

    # The sphere, unrolled so that each row keeps its true length: a row at elevation e is cos(e) as long as
    # the equator, and its eight views are spread evenly along it (a sinusoidal map).
    cx, cy, half_w, half_h = 300, 214, 250, 128
    f.text(24, 28, "the baked directions, seen as the sphere they sample; each row drawn at its true length", 13.5,
           "italic", GRAY)

    def at(azimuth, elevation):
        return cx + azimuth / 180 * half_w * math.cos(math.radians(elevation)), cy - elevation / 90 * half_h

    rim = [at(-180, e) for e in range(-90, 91, 3)] + [at(180, e) for e in range(90, -91, -3)]
    f.polygon(rim, FILL, LINE, 1.2)
    for e in elevations:
        f.line([at(-180, e), at(180, e)], HAIR, 1.2)
    for k in range(azimuths):
        for e in elevations:
            x, y = at(-180 + k * step, e)
            f.circle(x, y, 4, GOLD_SOFT, GOLD, 1.3)
    # Azimuth wraps: past the last view on a row comes the first one again.
    wx, wy = at(180, 10)
    f.circle(wx, wy, 4, WHITE, GOLD, 1.3)
    f.text(wx - 10, wy + 18, "the first view again", 13, "italic", GRAY, "end")

    label_x = cx + half_w + 36
    head_y = cy - 85 / 90 * half_h - 30
    f.text(label_x + 34, head_y, "row", 13.5, "bold", GRAY, "end")
    f.text(label_x + 50, head_y, "its neighbours are", 13.5, "bold", GRAY)
    for e in elevations:
        y = cy - e / 90 * half_h
        f.text(label_x + 34, y, f"{e}°", 15, "bold", anchor="end")
        f.text(label_x + 50, y, f"about {round(spacing[e])}° apart", 15, fill=GOLD_TEXT if e in (85, 10) else INK)
    f.text(24, cy + half_h + 26, "8 views on every row, 45° apart in azimuth; beyond −65° and 85° the row clamps",
           13.5, "italic", GRAY)

    # The handover along the distance from the camera to the tree's framing centre, from 400 m out.
    top = cy + half_h + 104
    f.line([(24, top - 50), (856, top - 50)], HAIR, 1.2)
    f.text(24, top - 24, "each bar: where a tree keeps that owner; each arrow: where it changes", 13.5, "italic", GRAY)
    x0, x1, d0, d1 = 150, 850, 400.0, 630.0

    def dx(metres):
        return x0 + (x1 - x0) * (metres - d0) / (d1 - d0)

    mesh_y, impostor_y, axis_y = top + 34, top + 92, top + 140
    f.rect(dx(enter), mesh_y - 22, dx(exit_) - dx(enter), impostor_y - mesh_y + 44, TEAL_FILL, "none", radius=4)
    f.text((dx(enter) + dx(exit_)) / 2, top + 2, "keeps last frame’s owner", 13.5, "bold", TEAL, "middle")

    f.text(x0 - 22, mesh_y, "mesh", 15, "bold", BLUE, "end")
    f.text(x0 - 22, impostor_y, "impostor", 15, "bold", GOLD_TEXT, "end")
    f.rect(x0, mesh_y - 7, dx(exit_) - x0, 14, BLUE_FILL, BLUE, 1.4, 4)
    f.rect(dx(enter), impostor_y - 7, x1 - dx(enter), 14, GOLD_FILL, GOLD, 1.4, 4)
    f.arrow([(dx(exit_), mesh_y + 8), (dx(exit_), impostor_y - 9)], BLUE, 1.8)
    f.text(dx(exit_) + 10, (mesh_y + impostor_y) / 2, "past 560 m: impostor", 14, fill=BLUE)
    f.arrow([(dx(enter), impostor_y - 8), (dx(enter), mesh_y + 9)], GOLD, 1.8)
    f.text(dx(enter) - 10, (mesh_y + impostor_y) / 2, "inside 490 m: mesh", 14, fill=GOLD_TEXT, anchor="end")

    # The axis, broken at its start: everything nearer than 400 m is a mesh's.
    f.line([(x0 + 10, axis_y), (x1, axis_y)], INK, 1.6)
    f.line([(x0 - 4, axis_y + 6), (x0 + 2, axis_y - 6)], INK, 1.6)
    f.line([(x0 + 4, axis_y + 6), (x0 + 10, axis_y - 6)], INK, 1.6)
    for metres in (enter, exit_):
        f.line([(dx(metres), axis_y - 6), (dx(metres), axis_y + 6)], INK, 1.6)
        f.text(dx(metres), axis_y + 20, f"{metres:.0f} m", 14, "bold", anchor="middle")
    for metres, below in ((pool, True), (reach, False)):
        f.line([(dx(metres), axis_y - 6), (dx(metres), axis_y + 6)], TEAL, 1.6)
    f.text(dx(reach), axis_y - 18, "600", 13, fill=TEAL, anchor="middle")

    f.text((x0 + x1) / 2, axis_y + 44, "distance from the camera to the tree’s framing centre", 13.5, "italic", GRAY,
           "middle")
    pool_y = axis_y + 82
    f.rect(x0, pool_y - 6, dx(pool) - x0, 12, TEAL_FILL, TEAL, 1.3, 4)
    f.line([(dx(pool), axis_y + 6), (dx(pool), pool_y - 6)], TEAL, 1.2, "3 3")
    f.text(dx(pool), axis_y + 20, "592 m", 14, "bold", TEAL, "middle")
    f.text(x0 - 22, pool_y, "near pool", 15, "bold", TEAL, "end")
    f.text(x0 + 12, pool_y + 22, "reaches at least 592 m from the camera in every direction, inside its 600 m TREE_REACH", 13.5, "italic", GRAY)
    f.height = round(pool_y + 46)
    return f


FIGURES = [impostor_views_and_handover]
