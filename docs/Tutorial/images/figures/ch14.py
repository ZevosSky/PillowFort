"""Chapter 14, Importing USD Scenes: authored figures.

@author Gary Yang
@brief Figures for 14-Importing-USD-Scenes.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def runs(f, x, y, parts, size=15, anchor="start"):
    """One line made of (text, font, colour) runs, such as prose with a code name in it."""
    widths = [measure(text, size, font)[0] for text, font, _ in parts]
    gap = size * 0.3
    total = sum(widths) + gap * (len(parts) - 1)
    left = {"start": x, "middle": x - total / 2, "end": x - total}[anchor]
    for (text, font, colour), width in zip(parts, widths):
        f.text(left, y, text, size, font, colour)
        left += width + gap
    return left - gap


def dimension(f, a, b, tick=7, colour=LINE):
    """A dimension line between two points, with an arrowhead and a short tick at each end."""
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    nx, ny = -(b[1] - a[1]) / length, (b[0] - a[0]) / length
    f.arrow([a, b], colour, 1.3, 9, both=True)
    for px, py in (a, b):
        f.line([(px - nx * tick, py - ny * tick), (px + nx * tick, py + ny * tick)], colour, 1.3)


def right_angle(f, corner, toward_a, toward_b, size=12, colour=TEAL):
    """The small square that marks a right angle at corner, between the directions to a and to b."""
    def step(toward):
        dx, dy = toward[0] - corner[0], toward[1] - corner[1]
        length = math.hypot(dx, dy)
        return dx / length * size, dy / length * size
    (ax, ay), (bx, by) = step(toward_a), step(toward_b)
    cx, cy = corner
    f.line([(cx + ax, cy + ay), (cx + ax + bx, cy + ay + by), (cx + bx, cy + by)], colour, 1.3)


def lens_and_film_triangle():
    focal_length, vertical_aperture = 35.0, 24.0   # the chapter's example: a 35 mm lens over a 24 mm film
    theta = math.degrees(math.atan((vertical_aperture / 2) / focal_length))
    vertical_fov = 2 * math.degrees(math.atan(vertical_aperture / (2 * focal_length)))
    assert abs(vertical_fov - 2 * theta) < 1e-9   # the section's two formulas agree

    f = Figure("lens-and-film-triangle", 820, 392,
               "A camera seen from the side: the lens, the middle of the film and the film's top edge make a right "
               "triangle, with focalLength as the side along the axis (the near side) and half the verticalAperture as "
               "the far side. The angle theta at the lens is half the vertical field of view, the same angle at which "
               "light from the scene crosses at the lens.",
               kind="computed plot", source="14-Importing-USD-Scenes.md, section 6 (Cameras)",
               parameters={"focalLength": focal_length, "verticalAperture": vertical_aperture,
                           "thetaDegrees": round(theta, 2), "drawnAt": "10 px per millimetre"})
    scale = 10.0
    lens_x, axis_y = 226.0, 196.0
    film_x = lens_x + focal_length * scale
    half = vertical_aperture / 2 * scale
    top, bottom = (film_x, axis_y - half), (film_x, axis_y + half)
    slope = half / (film_x - lens_x)

    # The scene side: the same ray, continued back through the lens, and the axis beyond it.
    back = 196.0
    scene_point = (lens_x - back, axis_y + back * slope)
    f.line([(lens_x - back - 6, axis_y), (lens_x, axis_y)], LINE, 1.3, "6 6")
    f.arrow([scene_point, (lens_x - 18, axis_y + 18 * slope)], GOLD, 2.0, 12, "7 6")
    f.arc(lens_x, axis_y, 70, 180, 180 + theta, TEAL, 1.4)
    f.text(lens_x - 92, axis_y + 15, "θ", 18, "italic", TEAL, "middle")
    f.text(lens_x - back + 2, axis_y + back * slope + 24, "light from the scene", 14, "italic", GRAY)

    # The right triangle: lens, middle of the film, top edge of the film.
    f.polygon([(lens_x, axis_y), (film_x, axis_y), top], TEAL_FILL)
    f.line([(lens_x, axis_y), (film_x, axis_y)], INK, 1.8)
    f.arrow([(lens_x, axis_y), top], GOLD, 2.4, 13)
    right_angle(f, (film_x, axis_y), (lens_x, axis_y), top, 13)
    f.arc(lens_x, axis_y, 110, 0, theta, TEAL, 1.4)
    f.text(lens_x + 128, axis_y - 20, "θ", 18, "italic", TEAL, "middle")

    # The lens and the film.
    lens_half = 52
    f.add(f'<path d="M{number(lens_x)} {number(axis_y - lens_half)} Q{number(lens_x + 15)} {number(axis_y)} '
          f'{number(lens_x)} {number(axis_y + lens_half)} Q{number(lens_x - 15)} {number(axis_y)} {number(lens_x)} '
          f'{number(axis_y - lens_half)} Z" fill="{BLUE_FILL}" stroke="{BLUE}" stroke-width="1.6" opacity="0.9"/>')
    f.circle(lens_x, axis_y, 4.5, INK, WHITE, 1.6)
    f.text(lens_x, axis_y - lens_half - 18, "lens", 15, "bold", anchor="middle")
    f.rect(film_x - 4, top[1], 8, 2 * half, GOLD_FILL, GOLD, 1.4, 2)
    f.text(film_x, top[1] - 20, "film", 15, "bold", anchor="middle")

    # The two sides the tangent is made of.
    dimension(f, (film_x + 34, axis_y), (film_x + 34, top[1]))
    f.line([(film_x + 6, axis_y), (film_x + 42, axis_y)], LINE, 1.1, "3 4")
    runs(f, film_x + 52, axis_y - half / 2 - 11, [("half the", "regular", INK)], 15)
    runs(f, film_x + 52, axis_y - half / 2 + 11, [("verticalAperture", "mono", INK)], 15)
    dimension(f, (lens_x, bottom[1] + 36), (film_x, bottom[1] + 36))
    f.line([(lens_x, axis_y + lens_half + 8), (lens_x, bottom[1] + 44)], LINE, 1.1, "3 4")
    f.line([(film_x, bottom[1] + 6), (film_x, bottom[1] + 44)], LINE, 1.1, "3 4")
    f.text((lens_x + film_x) / 2, bottom[1] + 58, "focalLength", 15, "mono", anchor="middle")
    return f


def framing_a_bounding_sphere():
    theta = 30.0                          # half of the default 60-degree vertical field of view
    radius = 112.0                        # r, in pixels
    distance = radius / math.sin(math.radians(theta))
    assert abs(distance - 2 * radius) < 1e-9   # the chapter: d = r / sin 30 degrees = 2r

    f = Figure("framing-a-bounding-sphere", 830, 340,
               "A camera framing a sphere of radius r around the scene's bounds: the view's edge touches the sphere at a "
               "right angle to the radius, so the camera, the sphere's centre and the touching point make a right "
               "triangle. sin theta = r / d, so at theta = 30 degrees, d = 2r.",
               kind="computed plot", source="14-Importing-USD-Scenes.md, section 9 (Loading a file, on the CPU only)",
               parameters={"thetaDegrees": theta, "radiusPixels": radius, "distancePixels": distance})
    camera_x, axis_y = 128.0, 160.0
    centre = (camera_x + distance, axis_y)
    along = distance * math.cos(math.radians(theta))
    touch = (camera_x + along * math.cos(math.radians(theta)), axis_y - along * math.sin(math.radians(theta)))
    assert abs(math.hypot(touch[0] - centre[0], touch[1] - centre[1]) - radius) < 1e-9

    # The scene's box and the sphere around it: the box's corners sit on the sphere.
    corner = math.radians(31.0)
    half_w, half_h = radius * math.cos(corner), radius * math.sin(corner)
    f.circle(*centre, radius, BLUE_FILL, BLUE, 1.6)
    f.rect(centre[0] - half_w, axis_y - half_h, 2 * half_w, 2 * half_h, FILL, LINE, 1.2, 2, "5 4")
    f.text(centre[0] + 4, axis_y + half_h - 16, "the bounds", 13.5, fill=GRAY, anchor="middle")

    # The view: its top edge grazes the sphere, its bottom edge (dashed) is the mirror image. Both stop a little
    # past their touching points, so the lower one ends clear of the centre's extension line below the sphere.
    reach = along * 1.15
    edge = (math.cos(math.radians(theta)), -math.sin(math.radians(theta)))
    f.line([(camera_x, axis_y), (camera_x + edge[0] * reach, axis_y + edge[1] * reach)], INK, 2.0)
    f.line([(camera_x, axis_y), (camera_x + edge[0] * reach, axis_y - edge[1] * reach)], LINE, 1.4, "7 6")
    f.line([(camera_x, axis_y), centre], GRAY, 1.4, "6 5")
    f.arc(camera_x, axis_y, 62, 0, theta, TEAL, 1.5)
    f.text(camera_x + 80, axis_y - 20, "θ", 18, "italic", TEAL, "middle")

    # The right triangle's short side: the radius to the touching point.
    f.line([centre, touch], TEAL, 2.4)
    right_angle(f, touch, centre, (camera_x, axis_y), 12)
    f.circle(*touch, 5, TEAL, WHITE, 1.6)
    f.circle(*centre, 5, INK, WHITE, 1.6)
    label = (centre[0] + (touch[0] - centre[0]) * 0.74, centre[1] + (touch[1] - centre[1]) * 0.74)
    f.text(label[0] + 16, label[1] + 2, "r", 18, "italic", TEAL, "middle")
    f.text(touch[0] - 14, touch[1] - 22, "touching point", 14, fill=GRAY, anchor="end")
    f.text(centre[0] + 12, axis_y + 2, "centre", 14, fill=GRAY)

    # The camera: a body and a lens hood, with the view's apex at the hood's front.
    f.rect(camera_x - 48, axis_y - 14, 32, 28, BLUE, BLUE, 1.2, 4)
    f.polygon([(camera_x - 17, axis_y - 7), (camera_x, axis_y - 13), (camera_x, axis_y + 13), (camera_x - 17, axis_y + 7)], BLUE, BLUE)
    f.text(camera_x - 30, axis_y + 34, "camera", 14, fill=GRAY, anchor="middle")

    y = axis_y + radius + 30
    f.line([(camera_x, axis_y + 46), (camera_x, y + 8)], LINE, 1.1, "3 4")
    f.line([(centre[0], axis_y + radius + 6), (centre[0], y + 8)], LINE, 1.1, "3 4")   # from below the sphere
    dimension(f, (camera_x, y), (centre[0], y))
    f.rect((camera_x + centre[0]) / 2 - 14, y - 12, 28, 24, WHITE)
    f.text((camera_x + centre[0]) / 2, y, "d", 18, "italic", anchor="middle")

    x = 560
    f.text(x, axis_y - 24, "sin θ = r / d,  so  d = r / sin θ", 16)
    f.text(x, axis_y + 8, "with θ = 30°:  d = r / sin 30° = 2r", 14.5, fill=GRAY)
    return f


FIGURES = [lens_and_film_triangle, framing_a_bounding_sphere]
