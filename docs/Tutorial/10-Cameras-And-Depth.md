# 10 — Cameras and Depth

**Goal:** orbit around a field of cubes, with near cubes hiding far ones; then
fly through it with mouse and keyboard, tuned from an ImGui panel.

**ROADMAP:** step 11.

**Module:** a new module, `Scene` (`Source/PillowFort/Scene/`, namespace
`pf::scene`), for the camera, its transform, and the controllers that move it —
plain C++ and GLM, no Vulkan. `VulkanGraphics` (`pf::vulkan_graphics`) gains the
per-frame buffer (`SceneRenderer`) and the depth target. The test subject is a
demo, `Source/PillowFort/Demos/Cubes/` (`pf::demos::cubes`). Small additions to
`Window`, `Demos/Demo.h`, and `SandboxGame/Main.cpp`.

**Prerequisites:**

- Math: 2D and 3D vectors as arrows, sine, cosine, `atan2`, and a dot product.
  Section 1 teaches matrices from scratch; nothing else is assumed.
- Chapter 04 section 5: the three questions every barrier answers,
  `transitionImage` and its `aspect` argument, and the cookbook's "Depth
  attachment, start of frame" row.
- Chapter 05 section 1: load and store ops.
- Chapter 06 section 2 (Vulkan's clip space: Y down, depth `[0, 1]`, and
  `GLM_FORCE_DEPTH_ZERO_TO_ONE` in `premake5.lua`), section 4
  (`pDepthStencilState`, and the viewport-flip alternative), and section 8
  (`GraphicsPipelineDesc`'s depth fields, `createGraphicsPipeline`).
- Chapter 07 section 4 (the `WantCapture*` filter) and section 9 (a panel is a
  free function beside the data it edits).
- Chapter 08 section 2 (host-visible buffers, kept mapped), section 4
  (`createSceneTarget` and `destroySceneTarget`, and the resize path that calls
  them), section 5 ("When 128 bytes is not enough"), section 6 (descriptor
  sets, and one copy per frame in flight), section 7 (VMA's `createBuffer`), and
  section 8 (`SharedShaderTypes.h` and the `std140` rules).
- Chapter 09, all of it: the `Demo` interface and what it is handed, the scene
  pass helpers in `SceneTargets.h`, the event filter in `main` (section 7), and
  the "What runs when" table (section 9).

Every chapter so far drew in two dimensions, with positions written straight
into clip space. This one adds the third, and with it three things that arrive
together because none is useful alone: a camera to look from, a buffer that
carries the camera to every shader, and a depth buffer so that what is in front
stays in front.

The chapter is in two parts. **Part 1** (sections 1-9) is the math and the
plumbing — spaces, matrices, the projection, the camera's transform, the
per-frame buffer — then a field of cubes you can orbit around, drawn first
without a depth buffer so you can see what goes wrong, then with one.
**Part 2** (sections 10-12) lets you fly through it: cursor capture, held keys,
a fly controller, and a panel to switch between the two.

### What changes, and where

```text
Source/PillowFort/
  Scene/                                new module, pf::scene - no Vulkan in it
    Transform.h, .cpp                   sections 3 and 6
    Camera.h, .cpp                      sections 2 and 4
    OrbitController.h, .cpp             section 6; section 12: three more members
    FlyController.h, .cpp               section 11
    CameraControls.h, .cpp              section 12: both controllers, and the Camera panel
  VulkanGraphics/
    SceneRenderer.h, .cpp               section 7: new - set 0 and the per-frame buffers
    SceneTargets.h, .cpp                section 9: depth joins the targets and the scene pass
    VulkanRenderer.h, .cpp              section 9: owns the depth image
  Window/GlfwWindow.h, .cpp             section 10: setCursorCaptured
  Demos/Demo.h                          section 10: WantsCursorCaptured
  Demos/Cubes/CubesDemo.h, .cpp         section 8: the demo; section 12: both controllers
Source/SandboxGame/Main.cpp             section 8: one line; section 10: the filter and the cursor
Shaders/Include/SharedShaderTypes.h     section 7: FrameData
Shaders/Include/FrameBlock.glsl         section 7: new include
Shaders/Cubes/                          section 8: Cube.vert.glsl, Cube.frag.glsl, CubesTypes.h
```

The new folders are matched by `premake5.lua`'s existing globs, so nothing
changes there — but files were added, so **rerun `GenerateProjects.bat`**.

---

# Part 1 — Seeing in 3D (sections 1-9)

## 1. Four spaces, and the one you already know

Chapter 06's triangle wrote its corners directly in **clip space** — the space
the vertex shader's `gl_Position` is in — and Chapter 06 section 2 described
it: X to the right, **Y down**, and depth from 0 at the near plane to 1 at the
far plane. A 3D scene needs three more spaces in front of that one, and a matrix
to get from each to the next:

```text
 local (object) space   a cube's corners, around its own centre
        │  model matrix: where this object is            (section 3; per draw)
        ▼
 world space            right-handed, +Y up, metres - one space for the whole scene
        │  view matrix: where the camera is              (section 4; per frame)
        ▼
 view space             the camera at the origin, looking down -Z, +Y up
        │  projection matrix: the lens                   (section 2; per frame)
        ▼
 clip space             Vulkan's: x right, y DOWN, depth 0..1 after the divide
        │  divide by w, then the viewport                (the GPU does both)
        ▼
 framebuffer            pixels
```

The conventions are the index's ("Cameras, geometry, and scenes"), fixed once
for every chapter from here on: world space is right-handed with +Y up and one
unit per metre; view space is what `glm::lookAt` builds, the camera looking
down its own −Z. Only the last arrow is the GPU's. Everything above it is a
`glm::mat4` this chapter computes on the CPU, and the vertex shader applies
them in one line:

```glsl
gl_Position = frame.viewProjection * model * vec4(localPosition, 1.0);
```

`viewProjection` is the projection times the view, multiplied once per frame
on the CPU rather than once per vertex on the GPU. The order of the factors
matters, and the next passage says why.

> **Jump:** Until now every position in the tutorial was in one space, the one
> the GPU wants. From here on a vector means nothing without its space: a
> normal in local space is not a normal in world space, and a "distance" from a
> depth buffer is not metres. When something renders wrong in a 3D chapter, the
> first question is which space each vector in the failing line is in. The
> diagram above is the answer key. Before building any arrow, the next passage
> says what a matrix does to a point; then the chapter builds the arrows one at
> a time, starting with the last.

### What a matrix does to a point

Everything in this chapter rests on one idea, so it gets a worked example.

A `glm::mat4` is sixteen numbers in four columns of four. Multiplying it by a
point `(x, y, z, w)` is easiest to read column by column:

```text
M · (x, y, z, w)  =  x · column0  +  y · column1  +  z · column2  +  w · column3
```

`x` copies of the first column, plus `y` of the second, and so on. Take an
object that is turned 90° about +Y — counter-clockwise seen from above — and
then moved 5 m along +X. Its matrix is:

```text
          column0   column1   column2   column3
   x   [     0         0         1         5     ]
   y   [     0         1         0         0     ]
   z   [    -1         0         0         0     ]
   w   [     0         0         0         1     ]
```

Read each column as an answer:

- **Column 0, `(0, 0, -1)`**: where the object's own +X axis points in the
  world. A quarter turn about +Y swings +X round to −Z.
- **Column 1, `(0, 1, 0)`**: where its +Y points — unchanged, since it turned
  about Y.
- **Column 2, `(1, 0, 0)`**: where its +Z points — swung round to +X.
- **Column 3, `(5, 0, 0)`**: where its origin lands.

So a transform matrix is a list: where the object's three axes point, and
where its origin is. Now the fourth coordinate, `w`:

- **A point** one metre along the object's +X is `(1, 0, 0, 1)`. It gives
  `1 · column0 + 1 · column3 = (0, 0, -1, 0) + (5, 0, 0, 1) = (5, 0, -1, 1)`:
  turned to −Z, then moved 5 m along X.
- **A direction** — "the object's +X", say, or a surface normal — is
  `(1, 0, 0, 0)`. It gives `1 · column0 = (0, 0, -1, 0)`: turned, but not
  moved, because `w = 0` skips column 3.

That is the fourth coordinate's first job: positions carry `w = 1` and pick
up the translation; directions carry `w = 0` and only turn. (Section 2 gives it
a second job, the perspective divide.) The
`vec4(localPosition, 1.0)` in the shader line above is a position. GLM indexes
a matrix `m[column][row]`, so `m[3]` is column 3: `glm::vec3(m[3])` reads where
the origin went.

**Matrices apply right to left.** `A * B * p` means `A * (B * p)`: the matrix
next to the point acts first. Call the quarter turn `R` and the move `T`. The
matrix above is `T * R`: `R` turns the point to `(0, 0, -1)`, then `T` moves it
to `(5, 0, -1)`. `R * T` is a different object: `T` first moves the point to
`(6, 0, 0)`, then `R` swings it round the *world* origin to `(0, 0, -6)`. So
in `viewProjection * model * position` the model matrix acts first, then the
view, then the projection — the diagram's order, top to bottom.

Keep three facts; every later section uses them:

1. A matrix's columns are where the axes point; column 3 is where the origin
   lands.
2. `w = 1` is a point and moves; `w = 0` is a direction and only turns.
3. `A * B * p` applies `B` first.

---

## 2. The projection, built by hand

**This is `Camera::Projection`**, in `Source/PillowFort/Scene/Camera.cpp`. GLM
writes the matrix for us, but it is worth knowing what each of its five
non-zero entries does, because every depth, culling, and precision question in
later chapters comes back to them.

A perspective camera sees a pyramid with its tip at the eye. A point straight
ahead at distance `d` in front of the camera — view-space `z = -d` — appears
smaller the further away it is, so its screen position is its `x` and `y`
*divided by* `d`. A matrix cannot divide, which is why clip space has a fourth
coordinate: the matrix puts `d` into `w`, and the GPU divides `x`, `y`, and `z`
by `w` after the vertex shader.

Here the matrix is read by rows rather than columns, because each row makes
one output: an output coordinate is its row multiplied term by term with
`(x, y, z, 1)` and summed. That is section 1's rule seen from the other side.
Written out, with `t = tan(fovY / 2)` and `a = width / height`:

```text
              column 0     column 1    column 2         column 3
row 0  x:  [  1/(a·t)        0            0                0          ]
row 1  y:  [    0         -1/t            0                0          ]
row 2  z:  [    0            0         f/(n-f)        -f·n/(f-n)      ]
row 3  w:  [    0            0           -1                0          ]
```

GLM indexes `[column][row]`, so `[2][3]` below is column 2, row 3: "the `z`
input, into the `w` output".

- **`[0][0]` and `[1][1]`** scale `x` and `y` so that the edges of the field of
  view land on ±1 after the divide: a point at the top edge of the view has
  `y = d·t`, and `d·t · (1/t) / d = 1`. `x` also divides by the aspect ratio,
  so a square in the world stays square on a wide window.
- **`[2][3] = -1`** is the divide. Row 3 is `(0, 0, -1, 0)`, so
  `w = -z`: the distance in front of the camera.
- **`[2][2]` and `[3][2]`** decide depth. Row 2 gives
  `z_clip = f/(n-f) · (-d) - f·n/(f-n) = f·(d-n)/(f-n)`, and dividing by
  `w = d` gives depth `f/(f-n) · (1 - n/d)`: exactly 0 at `d = n` and exactly 1
  at `d = f`. That is Vulkan's `[0, 1]`, and it is what
  `GLM_FORCE_DEPTH_ZERO_TO_ONE` asks GLM for (premake defines it for every
  file; Chapter 06 section 2 explains why there and only there). Without it GLM
  writes OpenGL's `[-1, 1]`, Vulkan clips everything that lands below 0, and
  geometry close to the camera vanishes as if the near plane had moved out to
  about twice its distance.
- **The minus sign on `[1][1]`** is the only thing here that is Vulkan's and
  not GLM's. GLM, like OpenGL, puts +Y up in clip space; Vulkan puts it down
  (Chapter 06 section 2). Negating `[1][1]` flips the image the right way up.

**Flip exactly once, here.** Chapter 06 section 4 named the other way to fix
the Y direction — a viewport with a negative height — and said the flip would
happen here instead, once. Nothing else in the engine flips Y, not the
viewport, not a shader. Flipping twice gives an upside-down image; flipping in
the viewport *and* forgetting it in the winding rules gives inside-out meshes,
which is Chapter 11's subject. The projection is the place, because it is the
one matrix every camera's image passes through.

So `Projection` is GLM's matrix with one entry negated:

```cpp
glm::mat4 Camera::Projection(float aspect) const
{
    // Right-handed, depth [0, 1]: premake defines GLM_FORCE_DEPTH_ZERO_TO_ONE for
    // every file, so this is glm::perspectiveRH_ZO.
    glm::mat4 projection = glm::perspective(verticalFov, aspect, nearPlane, farPlane);

    // GLM writes OpenGL's +Y up. Vulkan's clip space has +Y down. This is the one
    // place in the engine that flips Y - section 2.
    projection[1][1] = -projection[1][1];
    return projection;
}
```

The aspect ratio is an argument rather than a member because it belongs to the
image being drawn, not to the camera: it changes when the window is resized,
and the same camera can draw into targets of different shapes. Section 8 passes
the scene target's extent every frame.

### A point, worked through

Take a 90° field of view, so `t = tan 45° = 1`; a square window, `a = 1`; and
`n = 1`, `f = 2`. The view-space point `(0.5, 1, -2)` — half a metre right, a
metre up, two metres ahead:

```text
x_clip = 1 · 0.5                 =  0.5
y_clip = -1 · 1                  = -1
z_clip = 2/(1-2) · (-2) - 2·1/1  =  4 - 2 = 2
w_clip = -(-2)                   =  2

after the divide by w:  (0.25, -0.5, 1.0)
```

A quarter of the way from the centre to the right edge, halfway from the
centre to the top edge (Y down, so up is negative), and depth 1, because the
point sits on the far plane. A point
straight ahead at `d = 1.5`, halfway between the planes, gets
`z_clip = 3 - 2 = 1` and `w = 1.5`: depth **0.67**, not 0.5. Depth is not
spread evenly over distance, which is the next subsection's subject.

### How much precision depth has, and where

Depth is `f/(f-n) · (1 - n/d)`, not `d`: it follows `1/d`. With the defaults
this chapter uses, `n = 0.1` and `f = 500`:

| Distance `d` | Depth |
| --- | --- |
| 0.1 m (the near plane) | 0 |
| 0.2 m | 0.5 |
| 1 m | 0.9 |
| 10 m | 0.99 |
| 100 m | 0.999 |
| 500 m (the far plane) | 1 |

Half of all depth values are spent on the first 10 centimetres in front of the
lens, and from 10 m out to 500 m almost the whole view shares the last 1%.
`D32_SFLOAT` (section 9) still tells apart surfaces about 6 mm apart at 100 m,
and 15 cm apart at 500 m: plenty for these scenes. Run out of precision and
distant surfaces flicker through each other, "z-fighting".

The lever you control is `n`: precision at every distance scales with it.
**Make the near plane as far out as the scene allows.** 0.1 m is a good default
for walking around a room-sized scene; 0.01 m costs a factor of ten everywhere.
Even then you will not see z-fighting in this chapter's cube field: at its far
edge, about 55 m away, a 1 cm near plane still resolves about 2 cm, and no two
surfaces there are that close. That margin is what the table is for. What the
near plane does that you *can* see is cut away whatever is nearer than it;
Part 2's Camera panel has a Near slider to try it.

### The repository's older camera builds the same matrix

`VulkanGraphics/Camera/Camera.cpp`, a camera that came with the repository
from Gary Herron's course code, builds this matrix by hand. Its `ry` is `t`,
`rx = ry * aspect`, and `front` and `back` are `n` and `f`:

```cpp
P[0][0] = 1.0/rx;                          // 1/(a·t)
P[1][1] = -1.0/ry;                         // -1/t: Vulkan's Y down
P[2][2] = -back/(back-front);              // f/(n-f)
P[3][2] = -(front*back)/(back-front);      // -f·n/(f-n)
P[2][3] = -1;                              // w = -z
```

It starts from `glm::mat4 P;`, which is a trap worth knowing: unless
`GLM_FORCE_CTOR_INIT` is defined (premake does not), GLM leaves a
default-constructed matrix uninitialized, so the other ten entries are
whatever was on the stack. Building a matrix by hand, start from
`glm::mat4 P(0.0f)` and write its constants as floats (`1.0f / rx`). `1.0` is a
`double`, so the first two lines above each store a `double` in a `float`,
which MSVC reports as `C4244` at `/W4`.

### Aside: reverse-Z

Most modern engines swap the depth range — near at 1, far at 0, cleared to 0,
compared with `GREATER` — because floats are densest near 0, which then
offsets the `1/d` squeeze and makes precision roughly even with distance. The
tutorial does not: these scenes do not need it, and it would change the
projection, the clear value, the compare op, and every later reader of depth.

---

## 3. Where a thing is: `Transform`

**This is `Source/PillowFort/Scene/Transform.h` and `.cpp`.** Before a camera
can have a position, something has to hold one. A `Transform` is a translation,
a rotation, and a scale, kept apart:

```cpp
// Source/PillowFort/Scene/Transform.h
#pragma once

#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>

namespace pf::scene {

struct Transform
{
    glm::vec3 translation{ 0.0f };
    glm::quat rotation = glm::identity<glm::quat>();   // unit length, or it is not a rotation
    glm::vec3 scale{ 1.0f };

    glm::mat4 Matrix() const;    // translate * rotate * scale: scale first, translate last

    // The rotated axes. A camera looks down its -Z, so Forward is where it looks.
    glm::vec3 Forward() const { return rotation * glm::vec3(0.0f, 0.0f, -1.0f); }
    glm::vec3 Right() const   { return rotation * glm::vec3(1.0f, 0.0f, 0.0f); }
    glm::vec3 Up() const      { return rotation * glm::vec3(0.0f, 1.0f, 0.0f); }
};
```

```cpp
} // namespace pf::scene
```

(Section 6 adds two functions between the struct and the closing brace.)

**Why three parts, and not a `glm::mat4`.** A matrix is what the GPU wants, and
`Matrix()` produces one on demand. But nearly everything that *changes* a
transform wants the parts: a controller turns the camera without moving it, an
inspector edits the scale (Chapter 12), an importer reads them from a file
(Chapter 14). Taking a matrix apart again to do any of that is lossy work.
Keeping the parts and building the matrix when needed also means rounding
errors cannot accumulate: a matrix multiplied by small rotations every frame
slowly stops being a rotation, while a quaternion that drifts is put right by
normalizing four numbers — and the controllers below rebuild it from two angles
every time they turn the camera.

**Why a quaternion, and not three angles.** Angles are how people think about
orientation, and Chapter 12's inspector shows them. They are a poor way to
*store* it: three Euler angles have orientations where two of the axes line up
and a degree of freedom disappears (gimbal lock), there are twelve conventions
for which axis turns first, and two orientations that look alike can have very
different angles. A unit quaternion has none of those problems, composes with
`*`, and turns into a matrix with `glm::mat4_cast`. The cost is that its four
numbers are not readable — which is why the controllers in section 6 work in
yaw and pitch and convert.

> **Using a quaternion without its math.** Treat `glm::quat` as a box holding
> one orientation; you never read or write its four numbers.
> `glm::angleAxis(angle, axis)` builds one: a turn of `angle` radians about the
> unit vector `axis`. `q * v` turns the vector `v` by it. `q1 * q2` is the
> orientation that turns by `q2` first, then by `q1` — right to left, like
> matrices. `glm::mat4_cast(q)` gives the same turn as a matrix, and
> `glm::normalize(q)` repairs the drift that many small multiplications cause.

`glm::identity<glm::quat>()` is the orientation that turns nothing.

**`Matrix()`** composes the three in the one order that makes sense —
scale, then rotate, then translate:

```cpp
glm::mat4 Transform::Matrix() const
{
    // Read right to left: a point is scaled, then rotated, then moved.
    return glm::translate(glm::mat4(1.0f), translation)
         * glm::mat4_cast(rotation)
         * glm::scale(glm::mat4(1.0f), scale);
}
```

Read right to left, as section 1 showed: the scale acts first, then the
rotation, then the translation. Scaling after rotating would stretch the object
along the *world's* axes instead of its own, and rotating after translating
would swing it around the world origin — section 1's `R * T`.
`glm::translate` and `glm::scale` come from `<glm/gtc/matrix_transform.hpp>`.

`Forward`, `Right`, and `Up` are the transform's own axes in its parent's space
— for a camera in this chapter, in world space. They are section 1's columns
without the scale: `Right` is column 0's direction, `Up` column 1's, and
`Forward` minus column 2's, because a camera looks down its −Z. The controllers
move along these.

---

## 4. Where the camera is: the view matrix

**This is `Source/PillowFort/Scene/Camera.h`, and the rest of `Camera.cpp`.**

A camera is two things: a lens and a position. The lens is section 2's
projection, and its three numbers are the camera's data. The position is a
`Transform`, which in this chapter the camera owns:

```cpp
// Source/PillowFort/Scene/Camera.h
#pragma once

#include "PillowFort/Scene/Transform.h"

#include <glm/glm.hpp>

namespace pf::scene {

struct Camera
{
    float     verticalFov = glm::radians(60.0f);   // the whole vertical angle, in radians
    float     nearPlane   = 0.1f;                  // metres; must be > 0
    float     farPlane    = 500.0f;                // metres
    Transform transform;                           // where it is. Chapter 12 moves this onto a node.

    // View space to Vulkan's clip space: Y down, depth [0, 1]. aspect is width / height.
    glm::mat4 Projection(float aspect) const;
};

// World space to view space, from the camera's world matrix. Uses only its
// rigid part - position and orientation - so a scaled camera, or one under a
// scaled parent (Chapter 14's imports), still has a view measured in metres.
glm::mat4 viewMatrix(const glm::mat4& cameraWorld);

} // namespace pf::scene
```

`verticalFov` is the whole vertical angle, in radians like every angle in GLM;
Part 2's Camera panel shows degrees. The horizontal angle follows from the
aspect ratio, which is why the vertical one is the one stored: resizing a wide
window then shows more to the sides rather than less at the top.

**The view matrix is the inverse of the camera's world transform.** The
*inverse* of a matrix is the one that undoes it: `inverse(M) * M * p = p` for
every point. The camera's transform takes a point from the camera's own space —
where the camera sits at the origin looking down −Z — to the world. The view
matrix has to do the opposite: take a world point and say where it is
*relative to the camera*. So `view = inverse(cameraWorld)`.

A worked case. A camera at `(0, 0, 5)`, not turned, has a world matrix that
only moves things by `(0, 0, 5)`. Its view matrix moves the whole world by
`(0, 0, -5)`: the world origin lands at view-space `(0, 0, -5)`, five metres in
front of the lens, which looks down −Z. Moving the camera to the right is the
same as moving the world to the left.

`glm::lookAt(eye, center, up)` builds exactly that inverse, from a description
instead of a matrix: it puts the eye at the origin and turns `center - eye` onto
−Z. And section 1 says where to find the description in the camera's world
matrix: its eye is column 3, its forward direction is minus column 2, and its
up is column 1. So `lookAt` on those *is* the inverse:

```cpp
glm::mat4 viewMatrix(const glm::mat4& cameraWorld)
{
    // The camera's position and axes, read straight out of its world matrix:
    // column 3 is where it is, column 2 its +Z (it looks down -Z), column 1 its +Y.
    const glm::vec3 eye     = glm::vec3(cameraWorld[3]);
    const glm::vec3 forward = -glm::normalize(glm::vec3(cameraWorld[2]));
    const glm::vec3 up      = glm::normalize(glm::vec3(cameraWorld[1]));

    // lookAt builds the inverse of a rigid transform from exactly these, and
    // re-orthonormalizes them on the way, so no scale or shear gets through.
    return glm::lookAt(eye, eye + forward, up);
}
```

To *re-orthonormalize* is to make the three directions unit length and at
right angles to each other again.

Why not `glm::inverse(cameraWorld)`? With no scale it gives the same matrix, but
a camera's world matrix can carry scale it did not ask for — from Chapter 14 a
camera can sit under a parent that a file scaled by 100, and inverting that
would make view space centimetres. `lookAt` uses only the normalized
directions, so scale never reaches view space.

> Chapter 12 moves the camera's `Transform` onto a node in the scene graph, and
> the camera keeps only the lens. Its view becomes `viewMatrix(node.world)`,
> which is why the function takes a matrix rather than a `Camera`.

---

## 5. Input a camera can use

A camera does not move itself; a controller turns input into motion, and
section 6 writes the first one. Everything it needs already arrives through
Chapter 09's `FrameInput::events` — the window's queue, after the ImGui filter
(Chapter 07 section 4, Chapter 09 section 7):

- **Mouse buttons**, as `MouseButton` events with `GLFW_PRESS` or
  `GLFW_RELEASE`, and **the wheel**, as `Scroll` events whose `y` is the number
  of notches (fractions, on a touchpad).
- **How far the mouse moved**: the difference between two consecutive
  `CursorPosition` events.

Part 2's fly controller needs two things more — keys held across frames, and a
cursor that hides and stops at no edge — and section 10 adds them.

---

## 6. Turning a camera: yaw, pitch, and the orbit controller

A **controller** turns input into motion. The tutorial has two, because they
answer different questions: an **orbit** controller for looking *at* something
from all sides, written here, and a **fly** controller for moving *through* a
scene, in Part 2. They are separate classes rather than modes of the camera, so
a camera can be driven by either, by an animation, or by an inspector
(Chapter 12) without knowing which.

**A controller holds input, never the pose.** The camera's `Transform` is the
one place its position and orientation live. Each frame a controller reads the
transform, applies whatever input arrived, and writes the transform back. It
keeps no yaw or pitch of its own between frames. If it did, anything else that
turned the camera — Chapter 12's inspector, a camera imported from a file, the
other controller — would be undone the next time the controller wrote its
stale copy back.

### Yaw and pitch

Both controllers turn the camera the same way: **yaw** about the world's up
axis, **pitch** about the camera's own sideways axis, and no **roll** — the
horizon stays level. That is a natural pair of angles, and the quaternion has to
be converted to and from it. **This is the rest of `Transform.h`**, between the
struct and the end of the namespace:

```cpp
// An orientation with no roll, as two angles: yaw about world +Y, then pitch
// about the turned X axis. Both camera controllers think in these (section 6).
struct YawPitch
{
    float yaw   = 0.0f;   // radians; 0 looks down -Z, positive turns left
    float pitch = 0.0f;   // radians; positive looks up
};

// Controllers clamp pitch just short of straight up or down: at exactly 90
// degrees "forward" and "up" are the same line, and yaw stops meaning anything.
inline constexpr float MAX_PITCH = glm::radians(89.0f);

YawPitch  yawPitchOf(const glm::quat& rotation);              // any roll is discarded
glm::quat rotationFromYawPitch(const YawPitch& angles);
```

**and of `Transform.cpp`**, which also gains `<algorithm>` and `<cmath>`:

```cpp
YawPitch yawPitchOf(const glm::quat& rotation)
{
    // Where -Z ends up says everything a no-roll orientation needs: its
    // horizontal heading is the yaw, its height the sine of the pitch.
    const glm::vec3 forward = rotation * glm::vec3(0.0f, 0.0f, -1.0f);
    return YawPitch{
        .yaw   = std::atan2(-forward.x, -forward.z),
        .pitch = std::asin(std::clamp(forward.y, -1.0f, 1.0f)),
    };
}
```

```cpp
glm::quat rotationFromYawPitch(const YawPitch& angles)
{
    // Yaw about the WORLD up, applied last; pitch about the camera's own X,
    // applied first. The other order would tilt the yaw axis with the pitch.
    return glm::angleAxis(angles.yaw,   glm::vec3(0.0f, 1.0f, 0.0f))
         * glm::angleAxis(angles.pitch, glm::vec3(1.0f, 0.0f, 0.0f));
}
```

`rotationFromYawPitch` builds the orientation: pitch the camera's −Z up or down
about X first, then turn the result about world Y. Multiplying in the other
order would pitch about a *world* X that the yaw had already turned away from,
and the horizon would tilt.

`yawPitchOf` reads the angles back out of any rotation by looking at where it
sends −Z. With no roll, the forward vector is
`(-cos(pitch)·sin(yaw), sin(pitch), -cos(pitch)·cos(yaw))`, so the pitch is the
arcsine of its height and the yaw is the angle of its horizontal part. A
rotation *with* roll comes back without it, which is what a level-horizon
controller wants.

```text
 Seen from above (+Y towards you)            Seen from the side

              -Z   yaw 0                             +Y
               ▲                                      ▲       forward
    yaw +90°   │                                      │      ╱
  -X ◀─────────●─────────▶ +X                         │     ╱
               │                                      │    ╱  pitch
               │                                      │   ╱
              +Z                                      ●──────────────▶
                                                        the yaw direction
```

Yaw is measured from −Z, turning left (towards −X) as it grows. Pitch is the
angle above the horizontal: forward climbs `sin(pitch)` and keeps
`cos(pitch)` of its length along the ground, which is where the `cos(pitch)`
factors in the formula come from.

The **pitch clamp** is there because of that arcsine. Looking straight up,
forward is `(0, 1, 0)`, its horizontal part is zero, and `atan2(0, 0)` has no
meaningful answer: the yaw would be lost and the view would snap. Stopping a
degree short keeps the horizontal part non-zero.

### The orbit controller

**This is `Source/PillowFort/Scene/OrbitController.h` and `.cpp`.** The camera
sits on a sphere around a target and always looks at it; dragging with the left
mouse button moves it around the sphere, and scrolling changes the sphere's
radius. It is the controller for inspecting one thing — a mesh in Chapter 11, an
imported model in Chapter 14.

```cpp
// Source/PillowFort/Scene/OrbitController.h
#pragma once

#include "PillowFort/Scene/Transform.h"
#include "PillowFort/Window/GlfwWindow.h"

namespace pf::scene {

// The camera sits on a sphere around `target` and always looks at it. Drag with
// the left mouse button to move around the sphere, scroll to change its radius.
class OrbitController
{
public:
    glm::vec3 target{ 0.0f };
    float     distance          = 10.0f;   // metres from the target
    float     minDistance       = 0.5f;
    float     maxDistance       = 200.0f;
    float     rotateSensitivity = 0.005f;  // radians per pixel of drag
    float     zoomStep          = 0.1f;    // fraction of the distance per scroll notch

    void HandleEvent(const window::Event& event);
    bool Update(float deltaSeconds, Transform& transform);   // true if it moved the transform

private:
    bool   m_dragging   = false;
    bool   m_haveCursor = false;
    double m_cursorX    = 0.0;
    double m_cursorY    = 0.0;
    float  m_pendingYaw   = 0.0f;
    float  m_pendingPitch = 0.0f;
    float  m_pendingZoom  = 0.0f;   // scroll notches; positive zooms in
};

} // namespace pf::scene
```

`HandleEvent` records what arrived; `Update`, once per frame, turns it into a
pose. Section 12 adds three small members for when two controllers share a
camera. `OrbitController.cpp` includes `OrbitController.h`, `<algorithm>` for
`std::clamp`, and `<cmath>` for `std::pow`.

```cpp
void OrbitController::HandleEvent(const window::Event& event)
{
    if (event.kind == window::EventKind::MouseButton && event.code == GLFW_MOUSE_BUTTON_LEFT)
    {
        m_dragging   = event.action == GLFW_PRESS;
        m_haveCursor = false;
    }
    else if (event.kind == window::EventKind::CursorPosition && m_dragging)
    {
        if (m_haveCursor)
        {
            m_pendingYaw   -= static_cast<float>(event.x - m_cursorX) * rotateSensitivity;
            m_pendingPitch -= static_cast<float>(event.y - m_cursorY) * rotateSensitivity;
        }
        m_cursorX    = event.x;
        m_cursorY    = event.y;
        m_haveCursor = true;
    }
    else if (event.kind == window::EventKind::Scroll)
    {
        m_pendingZoom += static_cast<float>(event.y);   // a wheel notch is 1.0; touchpads send fractions
    }
}
```

```cpp
bool OrbitController::Update(float /*deltaSeconds*/, Transform& transform)
{
    if (m_pendingYaw == 0.0f && m_pendingPitch == 0.0f && m_pendingZoom == 0.0f)
    {
        return false;   // leave the pose alone, so an edit made elsewhere survives
    }

    YawPitch angles = yawPitchOf(transform.rotation);
    angles.yaw  += m_pendingYaw;
    angles.pitch = std::clamp(angles.pitch + m_pendingPitch, -MAX_PITCH, MAX_PITCH);

    // Each notch scales the distance by the same factor, so zooming feels the
    // same at 1 metre and at 100.
    distance = std::clamp(distance * std::pow(1.0f - zoomStep, m_pendingZoom), minDistance, maxDistance);

    // Looking at the target from `distance` away means standing behind it along
    // the camera's own +Z, which is backwards from where it looks.
    transform.rotation    = rotationFromYawPitch(angles);
    transform.translation = target - transform.Forward() * distance;

    m_pendingYaw   = 0.0f;
    m_pendingPitch = 0.0f;
    m_pendingZoom  = 0.0f;
    return true;
}
```

**Where the camera ends up** follows from "looks at the target from
`distance` away": the camera is behind the target along its own line of sight,
so its position is `target - Forward() * distance`. The orientation comes first,
then the position follows from it — which is why the controller stores no
position at all.

**Zoom is multiplicative.** Each scroll notch multiplies the distance by 0.9.
Subtracting a fixed amount instead would crawl at 100 m and overshoot the
target at 1 m. Scroll offsets are fractional on touchpads, so the exponent is a
float.

**Nothing moves without input.** `Update` returns early when nothing is pending.
If it always rewrote the position, the camera could never be placed anywhere
except on the orbit sphere — not by the inspector, not by switching from the fly
controller.

---

## 7. The per-frame buffer

A camera produces three matrices and a position, and every shader that draws
the scene needs them. Chapter 08 section 5 already said where they go: at 64
bytes per matrix they overflow the 128-byte push-constant budget, so they go in
a **uniform buffer**, one per frame in flight, persistently mapped, bound
through a descriptor set (Chapter 08 section 6). From this chapter on that set
has a fixed number and a fixed meaning — the index's descriptor-set table:

| Set | Bound | Contents |
| --- | --- | --- |
| 0 | once per frame | binding 0: the frame uniform buffer, `FrameData`. Later chapters add bindings 1-4 (lights, instances, shadows) and 10-12 (the sky's light) |
| 1 | per material | from Chapter 15 |
| push constants | per draw | the model matrix, from Chapter 11 |

### One layout, two languages

**This is `Shaders/Include/SharedShaderTypes.h`**, which Chapter 08 section 8
created so that a struct read by both C++ and GLSL is written once. Its C++
prelude gains one alias,

```c
using mat4 = glm::mat4;   /* Chapter 10: column-major, 64 bytes, as GLSL's mat4 */
```
after `using vec4`, and its first struct, in place of the two comment lines
Chapter 08 left for it. The closing brace of `namespace pf::shared`, which
Chapter 08 left in a block of its own, moves into the new struct's asserts —
as it will for every struct after it — so `FrameData` is inside the namespace:

```c
/* Chapter 10: everything that is the same for every draw in a frame. Set 0,
   binding 0, std140. Append-only: a later chapter adds fields at the END and
   updates the asserts, so no shader written earlier reads the wrong offset. */
struct FrameData
{
    mat4  view;             /*   0  world -> view */
    mat4  projection;       /*  64  view -> clip: Vulkan's, Y down, depth [0, 1] */
    mat4  viewProjection;   /* 128  projection * view, multiplied once here, not per vertex */
    vec4  cameraPosition;   /* 192  xyz world-space eye; w = 1 */
    float time;             /* 208  seconds since startup */
    float deltaTime;        /* 212  seconds since the previous frame */
    float padding0;         /* 216  keeps the size a multiple of 16 */
    float padding1;         /* 220 */
};

#ifdef __cplusplus
    static_assert(sizeof(FrameData) == 224, "FrameData layout drifted.");
    static_assert(offsetof(FrameData, cameraPosition) == 192, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, time) == 208, "FrameData alignment drifted.");
    }
#endif
```

The layout is `std140`, the rules Chapter 08 section 8 tabulated for uniform
buffers, and it is chosen so that C++ and `std140` agree without any trickery:

- A `mat4` is four `vec4` columns in both languages, 64 bytes, 16-aligned.
- `cameraPosition` is a `vec4`, not a `vec3`, by Chapter 08's first habit —
  `w` is set to 1 and never read.
- The four floats at the end fill one 16-byte row exactly, and the padding
  makes the size a multiple of 16, which is what an array of them or a
  following member would need.

The `static_assert`s are Chapter 08's third habit: a field added in the wrong
place fails the build instead of quietly giving every shader the wrong numbers.

**The struct only grows at the end.** Chapter 11 appends the light, and later
chapters may append more; nothing is ever inserted or reordered. Every shader
written against an earlier version then still reads the right offsets — it
simply does not know about the fields after its own.

The GLSL side wraps the struct in a uniform block. That wrapping is the same in
every shader that reads set 0, so it is an include too. **This is
`Shaders/Include/FrameBlock.glsl`:**

```glsl
// Shaders/Include/FrameBlock.glsl - set 0, binding 0, as SceneRenderer lays it out (Chapter 10).
// An include, not a shader: no .vert/.frag/.comp in the name, so Chapter 06's glob skips it.
// The including shader says #extension GL_GOOGLE_include_directive : require first.
#include "SharedShaderTypes.h"

layout(std140, set = 0, binding = 0) uniform FrameBlock
{
    FrameData frame;   // frame.viewProjection, frame.cameraPosition, ...
};
```

Like `Color.glsl`, it is never compiled on its own, and every shader finds it
through the `-I Shaders/Include` Chapter 06's glob passes (Chapter 09 section 8
has how includes resolve). A block with an instance name (`frame`) keeps its
members out of the shader's global namespace, so a shader can still have its
own variable called `time`.

### Who owns it: `SceneRenderer`

The buffer, its descriptor set layout, a pool, and the sets need an owner.
Not the renderer: it owns the frame loop and the window-sized images, and a
demo with no camera — the triangle, the gradient, Chapter 20's compute exercise
— has no use for a camera buffer. The data is the *scene's*: which camera,
which light, which objects. So it belongs to a class that knows how to draw a
scene, which a demo that draws one owns.

> **Jump:** `SceneRenderer` starts here with one job — set 0 — and grows a lot.
> Chapter 11 gives it meshes, materials, the mesh pipelines, and a function that
> records a list of draws; Chapters 15-19 add material descriptor sets, a light
> buffer, shadow maps, a sample count, and per-instance data. Keep in mind what
> it is *for* rather than what it holds today: it is the reusable half of every
> demo that draws a 3D scene. A demo owns one, sets it up in `Setup`, and tears
> it down in `Teardown`. A demo with pipelines of its own — this chapter's cubes,
> Chapter 25's grass — still uses it for set 0, by putting
> `FrameSetLayout()` in its own pipeline layout.

**This is `Source/PillowFort/VulkanGraphics/SceneRenderer.h`:**

```cpp
// Source/PillowFort/VulkanGraphics/SceneRenderer.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/VulkanGraphics/SceneTargets.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include "SharedShaderTypes.h"   // FrameData, shared with GLSL (Chapter 08 section 8)

#include <vulkan/vulkan.h>

#include <array>

namespace pf::vulkan_graphics {

// The reusable half of every demo that draws a 3D scene. A demo owns one,
// initializes it in Setup and shuts it down in Teardown. In this chapter it
// owns set 0 - the data every draw in a frame shares; Chapter 11 gives it meshes
// and pipelines, and Chapters 15-19 grow it further.
class SceneRenderer
{
public:
    // Copies the context's handles and the formats; owns nothing it was given.
    InitializationResult Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                    const SceneFormats& formats);
    // Device idle first (Teardown runs after a wait). Safe after a partial Initialize.
    void Shutdown();

    // Set 0's shape, for a pipeline layout - this class's own pipelines, or a
    // demo's (the cubes below, the grass in Chapter 25).
    VkDescriptorSetLayout FrameSetLayout() const { return m_frameSetLayout; }

    // In Record only: after the fence wait, the GPU is done with this slot's buffer.
    void WriteFrameData(uint32_t frameIndex, const shared::FrameData& data);
    void BindFrameSet(VkCommandBuffer commandBuffer, VkPipelineLayout layout, uint32_t frameIndex) const;

private:
    InitializationResult CreateFrameResources();   // set 0: layout, pool, buffers, sets
    void                 DestroyFrameResources();

    VulkanContext   m_context;                         // copies of borrowed handles
    VkPipelineCache m_pipelineCache = VK_NULL_HANDLE;  // borrowed
    SceneFormats    m_formats;

    // Set 0: one uniform buffer and one set per frame in flight.
    VkDescriptorSetLayout                         m_frameSetLayout = VK_NULL_HANDLE;
    VkDescriptorPool                              m_framePool      = VK_NULL_HANDLE;   // frees the sets with it
    std::array<AllocatedBuffer, FRAMES_IN_FLIGHT> m_frameBuffers;                      // persistently mapped
    std::array<VkDescriptorSet, FRAMES_IN_FLIGHT> m_frameSets{};
};

} // namespace pf::vulkan_graphics
```

It copies the `VulkanContext` the demo was handed, as every demo does
(Chapter 09 section 3): a handful of handles, all borrowed. The formats are kept
for Chapter 11's pipelines.

**This is `SceneRenderer.cpp`.** `Initialize` is the list of steps — one, for
now, and Chapter 11 adds a second:

```cpp
InitializationResult SceneRenderer::Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                               const SceneFormats& formats)
{
    m_context       = context;
    m_pipelineCache = pipelineCache;
    m_formats       = formats;

    if (auto result = CreateFrameResources(); !result) { return result; }
    return InitializationResult::success();
}
```

`CreateFrameResources` is Chapter 08 section 6 made concrete: a layout, a pool
sized for exactly what is allocated from it, one set per frame in flight, and
one buffer per set.

```cpp
InitializationResult SceneRenderer::CreateFrameResources()
{
    // The shape of set 0. Both stages read it: the vertex shader for the
    // matrices, the fragment shader for the camera position and, from Chapter
    // 11, the light. Later chapters append bindings 1-4 and 10-12 to this array.
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding         = 0,
          .descriptorType  = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT },
    };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = static_cast<uint32_t>(std::size(bindings)),
        .pBindings    = bindings,
    };
    if (vkCreateDescriptorSetLayout(m_context.device, &setLayoutInfo, nullptr, &m_frameSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for set 0.");
    }

    // Exactly what the sets below take: one set per frame in flight, each taking one
    // descriptor of every binding in the layout above, written or not. A pool of our
    // own, so no other owner's sizing matters.
    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, FRAMES_IN_FLIGHT },
    };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = FRAMES_IN_FLIGHT,
        .poolSizeCount = static_cast<uint32_t>(std::size(poolSizes)),
        .pPoolSizes    = poolSizes,
    };
    if (vkCreateDescriptorPool(m_context.device, &poolInfo, nullptr, &m_framePool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for set 0.");
    }

    std::array<VkDescriptorSetLayout, FRAMES_IN_FLIGHT> layouts;
    layouts.fill(m_frameSetLayout);
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_framePool,
        .descriptorSetCount = FRAMES_IN_FLIGHT,
        .pSetLayouts        = layouts.data(),
    };
    if (vkAllocateDescriptorSets(m_context.device, &allocateInfo, m_frameSets.data()) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for set 0.");
    }

    for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
    {
        // Host-visible and mapped for its whole life (Chapter 08 section 2):
        // written every frame, read once, small.
        m_frameBuffers[i] = createBuffer(m_context, sizeof(shared::FrameData),
                                         VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, true);
        if (m_frameBuffers[i].buffer == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a FrameData buffer failed.");
        }

        // Written once: the set always points at the same buffer. What changes
        // every frame is the buffer's contents, not the set.
        const VkDescriptorBufferInfo bufferInfo{
            .buffer = m_frameBuffers[i].buffer,
            .offset = 0,
            .range  = sizeof(shared::FrameData),
        };
        const VkWriteDescriptorSet write{
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = m_frameSets[i],
            .dstBinding      = 0,
            .descriptorCount = 1,
            .descriptorType  = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
            .pBufferInfo     = &bufferInfo,
        };
        vkUpdateDescriptorSets(m_context.device, 1, &write, 0, nullptr);
    }
    return InitializationResult::success();
}
```

**A pool of its own**, and not the renderer's: Chapter 09 section 3's rule is
that each demo creates and destroys its own pools, sized for its own sets, and
`SceneRenderer` belongs to a demo. When a later chapter adds a binding to
`bindings`, it adds the matching entry to `poolSizes` beside it, times
`FRAMES_IN_FLIGHT`: a pool is counted by layout, and every set allocated from
it takes one descriptor of each binding in its layout, written or not. A count
that is short does not always fail — some drivers let a pool overfill — so it
can run on one GPU and fail on another (Chapter 24 section 3).

**Each set is written once**, at creation: it always points at the same buffer,
and only the buffer's contents change per frame.

**Writing the data** happens every frame, into this frame's buffer only:

```cpp
void SceneRenderer::WriteFrameData(uint32_t frameIndex, const shared::FrameData& data)
{
    AllocatedBuffer& buffer = m_frameBuffers[frameIndex];
    std::memcpy(buffer.mapped, &data, sizeof(data));

    // VMA may have picked memory that is not HOST_COHERENT; then the write must
    // be flushed before the GPU can see it. On coherent memory this does nothing.
    vmaFlushAllocation(m_context.allocator, buffer.allocation, 0, VK_WHOLE_SIZE);
}
```

**When to call it is the important part: in `Record`, never in `Update`.**
Chapter 09 section 9 orders the frame: `Update` runs before `drawFrame`, and
`Record` runs inside it, after `drawFrame` has waited on this frame slot's fence.
Before that wait, the GPU may still be reading `m_frameBuffers[frameIndex]` for
the frame that last used this slot, two frames ago; writing it then changes a
frame that is already being drawn. After the wait, that frame is finished.
(This is the reason there are two buffers: with one, the CPU could never write
while the GPU was drawing.)

**No barrier is needed** between the CPU's write and the shaders' reads:
submitting a command buffer makes every host write before it visible to it,
and `vmaFlushAllocation` covers memory that is not `HOST_COHERENT` (Chapter 08
section 7).

**Binding** is one call, with the pipeline layout of whatever is about to draw:

```cpp
void SceneRenderer::BindFrameSet(VkCommandBuffer commandBuffer, VkPipelineLayout layout,
                                 uint32_t frameIndex) const
{
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, layout,
                            0, 1, &m_frameSets[frameIndex], 0, nullptr);
}
```

And **shutdown**, safe after a partial `Initialize` because every destroy accepts
a null handle — and after none at all, which is the early return:

```cpp
void SceneRenderer::Shutdown()
{
    // Initialize never ran: there is no device to destroy anything with.
    if (m_context.device == VK_NULL_HANDLE) { return; }
    DestroyFrameResources();
}
```

```cpp
void SceneRenderer::DestroyFrameResources()
{
    vkDestroyDescriptorPool(m_context.device, m_framePool, nullptr);   // frees the sets too
    vkDestroyDescriptorSetLayout(m_context.device, m_frameSetLayout, nullptr);
    for (AllocatedBuffer& buffer : m_frameBuffers)
    {
        destroyBuffer(m_context, buffer);   // a null buffer is a no-op
    }
    m_framePool      = VK_NULL_HANDLE;
    m_frameSetLayout = VK_NULL_HANDLE;
    m_frameSets      = {};
}
```

The `.cpp` includes `SceneRenderer.h` and `<cstring>` for `std::memcpy`; the
header includes `SceneTargets.h`, `VulkanResources.h`, and
`"SharedShaderTypes.h"` for the types it holds.

---

## 8. The cube field

**This is the Cubes demo**: `Source/PillowFort/Demos/Cubes/` and
`Shaders/Cubes/`, one folder each, the way Chapter 09 lays out every demo. A
grid of boxes of different heights, each slowly turning, is the cheapest scene
in which depth visibly matters: from a low angle every box hides part of the
one behind it.

It is drawn first **without a depth buffer**, on purpose. The scene pass still
has only Chapter 09's color attachment; section 9 gives it depth. Running the
field before that is the quickest way to see what a depth buffer is for.

**There are no vertex buffers yet**, deliberately. The cube's 36 vertices come
from `gl_VertexIndex`, the way Chapter 06's triangle did, so this chapter's new
things — camera, frame buffer, depth — are the only new things on the screen.
Chapter 11 is the jump to real meshes.

### The push constant

Each cube's model matrix and color go in a push constant: 80 bytes, well inside
the 128-byte budget, and exactly what Chapter 08 section 5 said push constants
are for — small, per draw. Its C++ and GLSL twins share a header,
`Shaders/<Name>/<Name>Types.h`, the way Chapter 09 section 8 lays out a demo's
own types. **This is `Shaders/Cubes/CubesTypes.h`:**

```c
/* Shaders/Cubes/CubesTypes.h - one cube's push constants, in both languages. */
#ifndef PF_CUBES_TYPES_H
#define PF_CUBES_TYPES_H

#include "SharedShaderTypes.h"   /* the mat4 and vec4 aliases on the C++ side */

#ifdef __cplusplus
    namespace pf::demos::cubes {
    using shared::mat4;
    using shared::vec4;
#endif

struct CubeDraw
{
    mat4 model;   /*  0  this cube's local -> world */
    vec4 color;   /* 64  linear rgb; a unused */
};

#ifdef __cplusplus
    static_assert(sizeof(CubeDraw) == 80, "CubeDraw layout drifted.");
    }
#endif

#endif
```

### The shaders

**This is `Shaders/Cubes/Cube.vert.glsl`.** A cube has six faces of two
triangles, 36 vertices. Rather than list 36 positions, the shader describes each
face by its normal and two axes across it, and builds the corners:

```glsl
// Shaders/Cubes/Cube.vert.glsl - a unit cube from gl_VertexIndex alone: draw 36 vertices.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"   // set 0: frame.viewProjection
#include "CubesTypes.h"      // CubeDraw

layout(push_constant) uniform CubeBlock
{
    CubeDraw cube;
};

layout(location = 0) out vec3 faceColor;

// One face per row: its outward normal, and two axes across it with
// cross(u, v) == normal, so walking the corners -u-v, +u-v, +u+v, -u+v goes
// counter-clockwise seen from outside. Chapter 11 says why that matters.
const vec3 faceNormal[6] = vec3[](vec3( 1, 0, 0), vec3(-1, 0, 0), vec3(0,  1, 0),
                                  vec3( 0,-1, 0), vec3( 0, 0, 1), vec3(0,  0,-1));
const vec3 faceU[6]      = vec3[](vec3( 0, 0,-1), vec3( 0, 0, 1), vec3(1,  0, 0),
                                  vec3( 1, 0, 0), vec3( 1, 0, 0), vec3(-1, 0, 0));
const vec3 faceV[6]      = vec3[](vec3( 0, 1, 0), vec3( 0, 1, 0), vec3(0,  0,-1),
                                  vec3( 0, 0, 1), vec3( 0, 1, 0), vec3(0,  1, 0));

// Two triangles per face, as corner signs along (u, v): (0,1,2) and (0,2,3).
const vec2 corner[6] = vec2[](vec2(-1,-1), vec2( 1,-1), vec2( 1, 1),
                              vec2(-1,-1), vec2( 1, 1), vec2(-1, 1));

// Not lighting - Chapter 11 has the light. A fixed brightness per face, so the
// faces of one cube can be told apart and its edges read clearly.
const float faceShade[6] = float[](0.80, 0.55, 1.00, 0.35, 0.90, 0.65);

void main()
{
    int  face = gl_VertexIndex / 6;
    vec2 c    = corner[gl_VertexIndex % 6];

    // Half a unit out along the normal, and half a unit across in each direction.
    vec3 localPosition = 0.5 * (faceNormal[face] + c.x * faceU[face] + c.y * faceV[face]);

    gl_Position = frame.viewProjection * cube.model * vec4(localPosition, 1.0);
    faceColor   = cube.color.rgb * faceShade[face];
}
```

Three things to notice:

- **The corner order is counter-clockwise seen from outside**, because each
  face's `u × v` — written `cross(u, v)` in the comment — equals its outward
  normal. Nothing in this chapter culls, so it does not matter yet; Chapter 11
  turns culling on and explains why this order is the one that survives it.
- **`faceShade` is not lighting.** It is a fixed brightness per face, so the
  three visible faces of a box differ and its silhouette reads as a box. Chapter
  11 replaces it with a light.
- The shader includes `FrameBlock.glsl` for set 0 and `CubesTypes.h` for the
  push constant; Chapter 09 section 8 has how each resolves.

> **Normals and the cross product.** A *normal* is the unit-length arrow
> pointing straight out of the front of a surface. `cross(a, b)` is an arrow
> perpendicular to both `a` and `b`, and its direction follows the right-hand
> rule: point your right hand's fingers along `a`, curl them towards `b`, and
> your thumb points along `cross(a, b)`. So `cross(+X, +Y) = +Z`, and swapping
> the arguments flips it: `cross(+Y, +X) = −Z`. For a triangle `a, b, c`,
> `cross(b − a, c − a)` points out of the side from which `a → b → c` runs
> counter-clockwise. That is why a face whose `cross(u, v)` is its outward
> normal has corners that run counter-clockwise seen from outside.

**This is `Shaders/Cubes/Cube.frag.glsl`:**

```glsl
// Shaders/Cubes/Cube.frag.glsl
#version 450

layout(location = 0) in  vec3 faceColor;
layout(location = 0) out vec4 outColor;

void main()
{
    outColor = vec4(faceColor, 1.0);   // linear; the composite pass encodes (Chapter 08)
}
```

### The demo

**This is `Source/PillowFort/Demos/Cubes/CubesDemo.h`**, as Part 1 leaves it.
Its camera is driven by section 6's orbit controller; Part 2 swaps that for
both controllers and a panel (section 12).

```cpp
// Source/PillowFort/Demos/Cubes/CubesDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/OrbitController.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"

#include <array>

namespace pf::demos::cubes {

class CubesDemo final : public Demo
{
public:
    CubesDemo();   // CPU only: puts the camera somewhere useful

    const char*          Name() const override { return "Cubes"; }
    InitializationResult Setup(const DemoContext& context) override;
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override;
    void                 Update(const FrameInput& input) override;
    void                 Record(const RecordContext& frame) override;
    void                 Teardown() override;

private:
    // GPU objects: created in Setup, released in Teardown.
    DemoContext                    m_context;
    vulkan_graphics::SceneRenderer m_sceneRenderer;                 // set 0 and FrameData
    VkPipelineLayout               m_pipelineLayout = VK_NULL_HANDLE;
    std::array<VkPipeline, 2>      m_pipelines{};                   // [depth test off, on]

    // CPU state: survives Teardown, so switching back finds everything as it was.
    scene::Camera          m_camera;
    scene::OrbitController m_orbit;
    int                    m_gridSize  = 15;     // cubes along each side
    float                  m_spacing   = 3.0f;   // metres between cube centres
    bool                   m_depthTest = true;
    float                  m_time      = 0.0f;
    float                  m_deltaTime = 0.0f;
};

} // namespace pf::demos::cubes
```

The members split the way Chapter 09 section 2 asks: GPU objects that `Setup`
creates and `Teardown` releases, and CPU state that survives `Teardown`, so
switching to the gradient and back finds the camera where you left it. Two
pipelines, because the panel can switch the depth test off — once section 9
has given the pass a depth buffer, the clearest way to see what it does, and
this chapter's positive control.

**This is `CubesDemo.cpp`.** It includes `PillowFort/DebugPanels/DemoPanel.h`,
`PillowFort/Scene/Transform.h`, `GraphicsPipeline.h`, `"Cubes/CubesTypes.h"`
(through the `Shaders` include directory Chapter 09 added), `<imgui.h>`, and
`<cmath>`. The **constructor**
places the camera — CPU work only, per Chapter 09:

```cpp
CubesDemo::CubesDemo()
{
    // Orbiting the middle of the field, from above and to one side. Placing the
    // camera exactly where the orbit controller would put it means the first
    // drag continues smoothly from here.
    m_orbit.target   = glm::vec3(0.0f);
    m_orbit.distance = 35.0f;
    m_camera.transform.rotation    = scene::rotationFromYawPitch({ .yaw   = glm::radians(30.0f),
                                                                   .pitch = glm::radians(-25.0f) });
    m_camera.transform.translation = m_orbit.target - m_camera.transform.Forward() * m_orbit.distance;
}
```

The camera is put exactly where the orbit controller would put it, on its sphere
looking at the target, so the first drag continues from the starting view
rather than snapping to the controller's idea of it.

**`Setup`** creates the scene renderer, a pipeline layout with set 0 and the
push-constant range, and the two pipelines:

```cpp
InitializationResult CubesDemo::Setup(const DemoContext& context)
{
    m_context = context;   // first, so Teardown works however far this gets

    if (auto result = m_sceneRenderer.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats);
        !result)
    {
        return result;
    }

    // Set 0 is the scene renderer's frame data; the push constant is one cube.
    const VkDescriptorSetLayout setLayout = m_sceneRenderer.FrameSetLayout();
    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT,
        .offset     = 0,
        .size       = sizeof(CubeDraw),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &setLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_pipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the cubes.");
    }

    // Two pipelines that differ only in the depth test, so the panel can show
    // what the depth buffer is for. Both declare the depth format: the pass has
    // a depth attachment either way, and the formats must match.
    for (int depthTest = 0; depthTest < 2; ++depthTest)
    {
        const vulkan_graphics::GraphicsPipelineDesc desc{
            .vertexShader   = "Cubes/Cube.vert.spv",
            .fragmentShader = "Cubes/Cube.frag.spv",
            .colorFormats   = { &m_context.formats.color, 1 },
            .depthFormat    = m_context.formats.depth,
            .depthTest      = depthTest == 1,
            .depthWrite     = depthTest == 1,
            .depthCompare   = VK_COMPARE_OP_LESS,
            .layout         = m_pipelineLayout,
        };
        m_pipelines[depthTest] = vulkan_graphics::createGraphicsPipeline(m_context.vulkan.device,
                                                                         m_context.pipelineCache, desc);
        if (m_pipelines[depthTest] == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a cube pipeline failed.");
        }
    }
    return InitializationResult::success();
}
```

The pipeline layout's set 0 is `m_sceneRenderer.FrameSetLayout()` — the cube
pipelines are the demo's, but the frame data is the scene renderer's, and using
its layout is what makes `BindFrameSet` compatible with them. Both pipelines
declare `formats.depth` and say whether to test depth, and today neither
tests anything: `formats.depth` is still `UNDEFINED` (Chapter 09 section 3),
so the pass has no depth attachment, `createGraphicsPipeline` leaves the depth
state out (Chapter 06 section 8), and the two pipelines are the same. They ask
now for what section 9 provides, so that nothing in the demo changes when it
arrives — the promise Chapter 09's triangle and gradient made too. From then
on the pass has a depth attachment either way, and a pipeline drawn in it must
declare its format whether it tests depth or not.

```cpp
// The depth target is the renderer's; nothing here is sized to the window.
InitializationResult CubesDemo::Resize(const vulkan_graphics::SceneTargets& /*targets*/)
{
    return InitializationResult::success();
}
```

**`Update`** feeds this frame's events to the orbit controller, lets it move
the camera, and draws the demo's panel:

```cpp
void CubesDemo::Update(const FrameInput& input)
{
    // Input first: Record draws whatever the transform says afterwards.
    for (const window::Event& event : input.events)
    {
        m_orbit.HandleEvent(event);
    }
    m_orbit.Update(input.deltaSeconds, m_camera.transform);

    if (debug_panels::beginDemoPanel("Cubes", debug_panels::DemoPanelSlot::BelowCamera))
    {
        ImGui::SliderInt("Grid size", &m_gridSize, 1, 40);
        ImGui::Checkbox("Depth test", &m_depthTest);
    }
    ImGui::End();

    m_time      = input.elapsedSeconds;
    m_deltaTime = input.deltaSeconds;
}
```

`BelowCamera` opens the panel below where Part 2's Camera panel will go
(Chapter 09 section 6). Time is only
*stored* here: `Update` runs before the fence wait and must not touch
per-frame GPU memory (Chapter 09 section 9), so the frame data is written in
`Record`.

**`Record`** is where the camera becomes a buffer, and the cubes become draws:

```cpp
void CubesDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const VkExtent2D      extent        = frame.targets.extent;

    // This frame's camera, written now: after the fence wait, into this slot's
    // buffer. The aspect ratio comes from the target, so a resize just works.
    const float aspect = static_cast<float>(extent.width) / static_cast<float>(extent.height);
    shared::FrameData frameData{};
    frameData.view           = scene::viewMatrix(m_camera.transform.Matrix());
    frameData.projection     = m_camera.Projection(aspect);
    frameData.viewProjection = frameData.projection * frameData.view;
    frameData.cameraPosition = glm::vec4(m_camera.transform.translation, 1.0f);
    frameData.time           = m_time;
    frameData.deltaTime      = m_deltaTime;
    m_sceneRenderer.WriteFrameData(frame.frameIndex, frameData);

    const VkClearColorValue clearColor{ { 0.02f, 0.02f, 0.03f, 1.0f } };
    vulkan_graphics::beginScenePass(commandBuffer, frame.targets, &clearColor);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipelines[m_depthTest ? 1 : 0]);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_pipelineLayout, frame.frameIndex);

    // Rows from the back (-Z) to the front (+Z): back to front from the starting
    // camera, front to back from the other side, where "Depth test" off shows
    // it most.
    const float half = 0.5f * static_cast<float>(m_gridSize - 1);
    for (int z = 0; z < m_gridSize; ++z)
    {
        for (int x = 0; x < m_gridSize; ++x)
        {
            const float fx = static_cast<float>(x) - half;
            const float fz = static_cast<float>(z) - half;

            // A different height and a slow spin per cube, so the field has
            // something to hide behind and visibly runs.
            const float height = 1.0f + 2.0f * (0.5f + 0.5f * std::sin(fx * 1.7f + fz * 2.3f));
            const float spin   = 0.4f * m_time + 0.7f * (fx - fz);

            // Section 3's Transform: stretched to its height, turned, then moved
            // into the grid, lifted by half its height so it stands on the ground.
            const scene::Transform placement{
                .translation = glm::vec3(fx * m_spacing, 0.5f * height, fz * m_spacing),
                .rotation    = glm::angleAxis(spin, glm::vec3(0.0f, 1.0f, 0.0f)),
                .scale       = glm::vec3(1.0f, height, 1.0f),
            };

            const float u = m_gridSize > 1 ? static_cast<float>(x) / static_cast<float>(m_gridSize - 1) : 0.5f;
            const float v = m_gridSize > 1 ? static_cast<float>(z) / static_cast<float>(m_gridSize - 1) : 0.5f;
            const CubeDraw draw{
                .model = placement.Matrix(),
                .color = glm::vec4(0.05f + 0.9f * u, 0.2f, 0.05f + 0.9f * v, 1.0f),   // linear
            };
            vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT,
                               0, sizeof(CubeDraw), &draw);
            vkCmdDraw(commandBuffer, 36, 1, 0, 0);   // 6 faces x 2 triangles x 3 vertices
        }
    }

    vulkan_graphics::endScenePass(commandBuffer);
    vulkan_graphics::handBackSceneTarget(commandBuffer, frame.targets);
}
```

In order:

1. **The frame data**, into this slot's buffer. `view` from section 4,
   `projection` from section 2 with the aspect of the target being drawn — so
   resizing the window never distorts the image — and their product.
2. **The scene pass**, through Chapter 09's helper. Section 9 makes it clear a
   depth buffer and record its barrier too, with no change here: nothing in
   the demo mentions depth except its pipelines.
3. **Pipeline, then set 0**, once. `vkCmdBindDescriptorSets` needs a layout
   compatible with the pipeline's, and binding the set after the pipeline keeps
   the pairing obvious.
4. **One draw per cube**: its model matrix and color by push constant, then 36
   vertices. The model matrix is section 3's `Transform`, so there is one way to
   build one: the unit cube is stretched to its height, turned, and moved into
   the grid, lifted by half its height so its base sits on the ground.
5. **End the pass and hand the scene target back**, Chapter 09's contract.

**`Teardown`** releases GPU objects only:

```cpp
// Safe after a partial Setup. GPU objects only: the camera stays where it is.
void CubesDemo::Teardown()
{
    for (VkPipeline& pipeline : m_pipelines)
    {
        vkDestroyPipeline(m_context.vulkan.device, pipeline, nullptr);
        pipeline = VK_NULL_HANDLE;
    }
    vkDestroyPipelineLayout(m_context.vulkan.device, m_pipelineLayout, nullptr);
    m_pipelineLayout = VK_NULL_HANDLE;
    m_sceneRenderer.Shutdown();
}
```

### Registering it

**This is `Source/SandboxGame/Main.cpp`**, the one line Chapter 09 section 7
promised per demo, after the gradient's,

```cpp
demoList.push_back(std::make_unique<demos::cubes::CubesDemo>());        // Chapter 10
```

and its include, `#include "PillowFort/Demos/Cubes/CubesDemo.h"`, beside the
other demos'. `SandboxGame --demo Cubes` starts on it.

## Checkpoint

Run `SandboxGame --demo Cubes`. You should see:

- a grid of turning boxes of different heights, from above and to one side;
- the view turning around the middle of the field as you drag with the left
  mouse button, and zooming as you scroll, never passing straight overhead;
- the image keeping its proportions as you resize the window;
- **what is still wrong.** Every box looks hollow, or inside out: parts of its
  far faces are drawn over its near ones. A box's six faces are drawn in the
  same order whichever way it faces you, nothing removes the back ones yet
  (Chapter 11 does), and without a depth buffer the last triangle drawn at a
  pixel wins. Orbit half way round and it is worse: the rows are now drawn
  front to back, so whole cubes at the back of the field paint over the ones in
  front. The "Depth test" checkbox changes nothing yet. Section 9 fixes all of
  it.

---

## 9. The depth buffer

**Why it is needed.** Section 8's checkpoint showed it: without one, the last
thing drawn wins. Between cubes, the field is drawn row by row from the back to
the front, which is the right order from the starting camera and backwards from
the other side, where the back row is now nearest and is painted over by cubes
behind it. Within one cube there is no right order at all: its faces are drawn
in the same order from every side. Sorting draws far-to-near ("the painter's
algorithm") fixes the first only for objects that do not overlap themselves,
never the second, and sorting every frame costs CPU time that scales with the
scene. A depth buffer fixes both, per pixel. A **fragment** is one triangle's
claim on one pixel — a pixel can receive several, one from each triangle that
covers it — and each fragment's depth is compared with the nearest one drawn so
far at that pixel, and only a nearer one is written.

### Whose it is

The depth buffer is sized to the window, like the scene color target, and
every chapter from here to the ocean draws 3D into it. So it is the
**renderer's**, created and destroyed beside the scene target in Chapter 08
section 4's `createSceneTarget` and `destroySceneTarget`. Both resize paths
already go through those two functions, so the depth buffer follows the window
with no new code — and Chapter 09's `Resize` already hands each demo the new
handles. A demo never creates one.

### The format

**This is `VulkanRenderer.cpp`, above the namespace block.** The scene's depth
is `D32_SFLOAT`, 32-bit float depth, with section 2's precision. Later chapters
also *read* the depth buffer in shaders (Chapter 21's particles fade where they
touch geometry, Chapter 26's grass culls against it), so the format must be
both a depth attachment and sampleable. Every desktop GPU supports both, but
the spec does not promise it, so the renderer checks once and reports a GPU
that cannot, rather than assuming:

```cpp
// File scope, above the namespace block. Chapter 10: can this GPU render depth
// into `format` and sample it in a shader afterwards?
static bool supportsSampledDepth(VkPhysicalDevice physicalDevice, VkFormat format)
{
    const VkFormatFeatureFlags needed = VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT
                                      | VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT;
    VkFormatProperties properties{};
    vkGetPhysicalDeviceFormatProperties(physicalDevice, format, &properties);
    return (properties.optimalTilingFeatures & needed) == needed;
}
```

The check runs in `initialize`, right before the targets are first created. A
failure is an `InitializationResult` like any other — unsupported hardware is
reported, not asserted — and the program stops with the message:

```cpp
// Chapter 10: before the targets. Every desktop GPU passes; one that does not is reported.
if (!supportsSampledDepth(m_vulkan.PhysicalDevice(), m_sceneDepthFormat))
{
    return InitializationResult::failure("This GPU cannot render D32_SFLOAT depth and sample it afterwards.");
}
if (auto result = createSceneTarget(m_swapchain.extent()); !result) { return result; }
```

The format is a member rather than a constant written at every use because
pipelines are built against it (below) and Chapter 18 builds multisampled
images in it; it is fixed for the whole run, never changed on resize.

### The image and its view

The create-info is Chapter 08 section 3's `sceneTargetInfo` with a depth format
and depth usage, beside it above the namespace block:

```cpp
// File scope, above the namespace block. Chapter 10's depth target: the scene
// target's twin, sized to the window like it, with a depth format and usage.
static VkImageCreateInfo sceneDepthInfo(VkExtent2D extent, VkFormat format)
{
    return VkImageCreateInfo{
        .sType       = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType   = VK_IMAGE_TYPE_2D,
        .format      = format,
        .extent      = { extent.width, extent.height, 1 },
        .mipLevels   = 1,
        .arrayLayers = 1,
        .samples     = VK_SAMPLE_COUNT_1_BIT,
        .tiling      = VK_IMAGE_TILING_OPTIMAL,
        .usage       = VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT   // the depth test reads and writes it
                     | VK_IMAGE_USAGE_SAMPLED_BIT,                   // later chapters read it in shaders
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
}
```

`DEPTH_STENCIL_ATTACHMENT` is what the depth test needs. `SAMPLED` is for the
later readers; it is part of the create-info from the start because adding a
usage later means a different image, and a usage nobody uses yet costs
nothing measurable. (A shader can read a depth image with a sampler only after a
barrier to a read-only layout, which is the reader's job — see "Who reads it
later", below.)

The four members go with Chapter 08's scene-target members in
`VulkanRenderer.h`, in creation order:

```cpp
VkFormat              m_sceneDepthFormat     = VK_FORMAT_D32_SFLOAT;  // Chapter 10: checked in initialize
VkImage               m_sceneDepthImage      = VK_NULL_HANDLE;        // beside the scene target
VmaAllocation         m_sceneDepthAllocation = VK_NULL_HANDLE;
VkImageView           m_sceneDepthView       = VK_NULL_HANDLE;
```

and `createSceneTarget` gains its second half — the same two steps as the color
target, image then view:

```cpp
// Chapter 10: the depth target, the same way. Created here, so every path that
// rebuilds the color target - startup and recreateSwapchain - rebuilds it too.
const VkImageCreateInfo depthInfo = sceneDepthInfo(extent, m_sceneDepthFormat);
if (vmaCreateImage(m_context.allocator, &depthInfo, &allocationInfo,
                   &m_sceneDepthImage, &m_sceneDepthAllocation, nullptr) != VK_SUCCESS)
{
    return InitializationResult::failure("vmaCreateImage failed for the scene depth target.");
}

// A depth view names the DEPTH aspect; COLOR here is a validation error.
const VkImageViewCreateInfo depthViewInfo{
    .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
    .image            = m_sceneDepthImage,
    .viewType         = VK_IMAGE_VIEW_TYPE_2D,
    .format           = m_sceneDepthFormat,
    .subresourceRange = { VK_IMAGE_ASPECT_DEPTH_BIT, 0, 1, 0, 1 },
};
if (vkCreateImageView(m_device, &depthViewInfo, nullptr, &m_sceneDepthView) != VK_SUCCESS)
{
    return InitializationResult::failure("vkCreateImageView failed for the scene depth target.");
}
return InitializationResult::success();
```

It reuses the color target's `allocationInfo` — a dedicated VMA allocation, for
the same reason: large, and recreated on every resize. The view's aspect is
`DEPTH`; a depth image viewed with the `COLOR` aspect is a validation error.

`destroySceneTarget` destroys both, in three places beside the color target's
own lines:

```cpp
// destroySceneTarget, Chapter 10's lines. Beside the color view's destroy:
vkDestroyImageView(m_device, m_sceneDepthView, nullptr);

// Inside the allocator check, beside the color image's:
vmaDestroyImage(m_context.allocator, m_sceneDepthImage, m_sceneDepthAllocation);

// And with the other resets at the end:
m_sceneDepthView       = VK_NULL_HANDLE;
m_sceneDepthImage      = VK_NULL_HANDLE;
m_sceneDepthAllocation = VK_NULL_HANDLE;
```

### What a demo sees of it

Chapter 09 section 3 gave demos a borrowed view of the renderer's targets,
`SceneTargets`, and reserved `SceneFormats::depth` for this chapter. **This is
`Source/PillowFort/VulkanGraphics/SceneTargets.h`**: the struct gains two
handles, with null defaults so every existing designated initializer still
compiles,

```cpp
VkImage      depthImage = VK_NULL_HANDLE;   // Chapter 10: single-sample, also SAMPLED for later readers
VkImageView  depthView  = VK_NULL_HANDLE;
```

and **`VulkanRenderer::sceneTargets`** fills them, and the depth format. Its
`.formats` line changes, and two lines join the end of the initializer:

```cpp
        .formats    = SceneFormats{ .depth = m_sceneDepthFormat },   // Chapter 10: depth is on
```

```cpp
        .depthImage = m_sceneDepthImage,   // Chapter 10
        .depthView  = m_sceneDepthView,
```

`switchDemo` builds the `DemoContext`'s formats from `sceneTargets()`, so from
here on every demo's `Setup` sees `formats.depth == D32_SFLOAT`. Chapter 09's
triangle and gradient, and section 8's cubes, already pass
`context.formats.depth` to their pipelines' `depthFormat`, as Chapter 09
section 10 promised, so they keep working without a change — and they must:
dynamic rendering requires a pipeline's depth format to match the pass it draws
in, whether the pipeline tests depth or not.

### The pipeline side

A pipeline that draws with depth needs two things, and Chapter 06 section 8's
`GraphicsPipelineDesc` already has both. `depthFormat` goes into
`VkPipelineRenderingCreateInfo::depthAttachmentFormat`, the way the color formats
do. And the three depth fields become a
`VkPipelineDepthStencilStateCreateInfo`, which `createGraphicsPipeline` builds
and passes whenever `depthFormat` is set:

```cpp
const VkPipelineDepthStencilStateCreateInfo depthStencil{
    .sType            = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO,
    .depthTestEnable  = desc.depthTest  ? VK_TRUE : VK_FALSE,
    .depthWriteEnable = desc.depthWrite ? VK_TRUE : VK_FALSE,
    .depthCompareOp   = desc.depthCompare,
};
```

The three are separate on purpose:

- **`depthTestEnable`** — compare each fragment against the buffer and discard
  the ones that fail.
- **`depthWriteEnable`** — write the depth of fragments that pass. An opaque
  object both tests and writes. A transparent one (Chapter 21's particles)
  tests but does not write, so it is hidden behind walls but does not hide what
  is behind *it*.
- **`depthCompareOp = LESS`** — "passes" means "nearer than what is there".
  With the buffer cleared to 1.0, the far plane, anything in the view is
  nearer.

Nothing in `createGraphicsPipeline` changes in this chapter. What changes is
section 8's two cube pipelines: with a depth format to build against, one now
tests and writes depth and the other does not, which is what the "Depth test"
checkbox switches between.

### The pass

**This is `beginScenePass`**, in `SceneTargets.cpp`, the helper Chapter 09
section 4 wrote for the color target. It grows in two places, both only when
the targets have a depth view.

First, **the barrier**, before anything else touches the depth image — after
the color target's barrier, before the attachments:

```cpp
// Chapter 10: the depth target, every frame, before the pass that clears it.
// Chapter 04's "Depth attachment, start of frame" row. One depth image serves
// both frames in flight, so the last frame's depth writes must finish before
// this frame's clear - a write after a write, so both sides name the writes.
// UNDEFINED: the clear replaces whatever was there.
if (targets.depthView != VK_NULL_HANDLE)
{
    transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
}
```

Chapter 04 section 5's three questions, answered:

- **Q1, execution — what must finish, and what must wait?** One depth image is
  shared by both frames in flight (it is one of the renderer's targets, not a
  per-frame copy). The previous frame's depth tests and writes may still be
  running when this frame starts, so this frame's clear and tests must wait for
  them. Depth is read and written in two stages — `EARLY_FRAGMENT_TESTS` before
  the fragment shader and `LATE_FRAGMENT_TESTS` after it — so both sides name
  both.
- **Q2, memory — whose writes must be flushed, whose caches invalidated?** The
  previous frame wrote depth, so its `DEPTH_STENCIL_ATTACHMENT_WRITE` is made
  available. This frame's clear writes and its tests read, so both
  `DEPTH_STENCIL_ATTACHMENT_READ` and `_WRITE` are made visible. This is a
  write-after-write hazard, which is why — unlike the color target's
  write-after-read barrier above it — the source access is not `NONE`.
- **Q3, layout — from what, to what?** From `UNDEFINED`, because the clear is
  about to replace every value and the old contents do not matter, to
  `DEPTH_ATTACHMENT_OPTIMAL`. The last argument, `VK_IMAGE_ASPECT_DEPTH_BIT`, is
  the one Chapter 04 gave `transitionImage` for exactly this.

That is Chapter 04's cookbook row "Depth attachment, start of frame", word for
word.

Second, **the attachment**, beside the color attachment, and the rendering
info's `pDepthAttachment`:

```cpp
// Cleared to 1.0, the far plane: every fragment that passes LESS is nearer
// than nothing at all. Stored, not discarded, because later chapters read it
// after the pass (particles in 21, the grass's occlusion culling in 26).
const VkRenderingAttachmentInfo depthAttachment{
    .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
    .imageView   = targets.depthView,
    .imageLayout = VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
    .resolveMode = VK_RESOLVE_MODE_NONE,
    .loadOp      = VK_ATTACHMENT_LOAD_OP_CLEAR,
    .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
    .clearValue  = { .depthStencil = { 1.0f, 0 } },
};
```

The rendering info's `pDepthAttachment`, which Chapter 09 left `nullptr`, now
points at it whenever the targets have a depth view:

```cpp
    .pDepthAttachment     = targets.depthView != VK_NULL_HANDLE ? &depthAttachment : nullptr,
```

**Why `STORE_OP_STORE`**, when Chapter 05 section 1 said a depth buffer nobody
reads afterwards should use `DONT_CARE`? Because somebody will read it. Chapter
21's particles and Chapter 26's culling read the scene's depth after the pass
(and Chapter 18 resolves multisampled depth into this image), and a `DONT_CARE`
store would hand them garbage on hardware that discards it (tile-based GPUs
genuinely do). On a desktop GPU the
difference is small; it is chosen once here so no later chapter has to change
the engine's pass.

`endScenePass` does not change — it is still `vkCmdEndRendering` — but its
comment in `SceneTargets.h` now says what it leaves behind, because Chapter 09's
contract is that the helpers document their last writer:

```cpp
// Ends the scope. Leaves the color target in COLOR_ATTACHMENT_OPTIMAL, last
// written at COLOR_ATTACHMENT_OUTPUT with COLOR_ATTACHMENT_WRITE, and the depth
// target in DEPTH_ATTACHMENT_OPTIMAL, last written at EARLY_ and
// LATE_FRAGMENT_TESTS with DEPTH_STENCIL_ATTACHMENT_WRITE (Chapter 10).
```

### Who reads it later

After `endScenePass` the depth image is in `DEPTH_ATTACHMENT_OPTIMAL`, last
written by the fragment tests. A later chapter that samples it (21, 26) adds its
own barrier to a read-only layout after the pass, and **owns the return trip**:
after its read, a barrier back to `DEPTH_ATTACHMENT_OPTIMAL`, from its read
stage with `NONE` access to the fragment-test stages. That chains into this
section's barrier on the next frame, so `beginScenePass` never changes for a
new reader — Chapter 04's "every per-frame cycle needs both directions",
applied by whoever adds the reader.

### Resizing

Nothing to do. The depth image is created and destroyed by the same two
functions as the scene target, `recreateSwapchain` already calls them, and the
demo's `Resize` receives the new handles. The cube demo's `Resize` is empty: it
owns nothing sized to the window.

## Checkpoint

Build and run the Cubes demo again. Nothing in it changed, and now:

- every box is solid: its near faces in front, its far faces hidden;
- near cubes hide far ones from every side — orbit all the way round to check;
- with "Depth test" unticked, section 8's picture comes back: hollow boxes,
  and from the far side, far cubes painting over near ones. Tick it again;
- validation stays silent through resizing and closing, with the depth
  barrier in every frame.

---

# Part 2 — Flying the camera (sections 10-12)

The orbit controller looks *at* one point. To move *through* a scene you want
a fly controller — W, A, S, D, and mouse-look. That takes two things the window
does not give yet (section 10), the controller itself (section 11), and a way
to switch between the two controllers (section 12).

## 10. What the window must add

ROADMAP step 2, the window, has no chapter of its own; Chapter 02 section 4
wrote down the `GlfwWindow` every later chapter uses, and this section is where
its next additions are written down. Section 5 listed what a camera gets from
the window already. Flying needs two things more.

### Every release reaches the demo

A fly controller keeps its own set of held keys from press and release events
(section 11). That works only if every release reaches it — and Chapter 07's
filter can drop one. Hold W in the scene — the press passes the filter — then
let the cursor drift over a panel, or click into a text field, and release W.
`WantCapture*` is now true, the release is dropped, the camera never hears it,
and it flies forward forever. A release can never do harm by getting through:
a release whose press ImGui took tells the demo "not held", which it already
believed. So releases are never filtered, and everything else is filtered
exactly as before.

**This is `main`'s event filter** (Chapter 09 section 7). The two
`WantCapture` lines move inside a test:

```cpp
            // A release is never filtered: if the press reached the demo, the
            // release must too, or the key stays held forever. The kind test is
            // needed because GLFW_RELEASE is 0, which is also the action of
            // every scroll and cursor event.
            const bool isRelease = event.action == GLFW_RELEASE &&
                                   (event.kind == window::EventKind::Key ||
                                    event.kind == window::EventKind::MouseButton);
            if (!isRelease)
            {
                if (io.WantCaptureMouse && event.isMouse())       { continue; }   // Chapter 07 section 4
                if (io.WantCaptureKeyboard && event.isKeyboard()) { continue; }
            }
```

The test needs the `kind` check: GLFW's `GLFW_RELEASE` is `0`, and `0` is also
the `action` of every scroll and cursor event, which carry no action at all.
GLFW itself sends a release for every held key when the window loses focus, so
alt-tabbing away with W held does not leave the camera flying either.

### The cursor, captured

For mouse-look, the cursor has to disappear and stop at no edge: dragging to
turn around would otherwise end when the pointer reaches the side of the
window. GLFW does this with
`glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_DISABLED)`: the cursor is
hidden and held in place, and `CursorPosition` events keep coming as an
unbounded *virtual* position, so differences between them still work.

GLFW calls stay inside the `Window` module, so the addition is a method on
`GlfwWindow`, in Chapter 02's lower-case style:

```cpp
// Chapter 10: hide the cursor and stop it at no edge, for mouse-look.
// Cursor positions keep arriving, as an unbounded virtual position.
void setCursorCaptured(bool captured);
```

It goes in the public section after `setInputForwarding`, with a private member
beside `m_forwarding`:

```cpp
bool               m_cursorCaptured = false;   // Chapter 10
```

The function goes in `GlfwWindow.cpp`, before `drainEvents`:

```cpp
void GlfwWindow::setCursorCaptured(bool captured)
{
    // Called every frame; only a change reaches GLFW, which moves the real
    // cursor when it switches modes.
    if (captured == m_cursorCaptured) { return; }
    glfwSetInputMode(m_window, GLFW_CURSOR, captured ? GLFW_CURSOR_DISABLED : GLFW_CURSOR_NORMAL);
    m_cursorCaptured = captured;
}
```

It is called every frame (below), so it remembers the last state and only calls
GLFW on a change; switching modes moves the real cursor, and doing that sixty
times a second is not free on every platform.

**Who decides.** Chapter 09 decided that a demo never receives the window. So
the demo *says* whether it wants the cursor, and `main`, which owns the window,
applies it. **This is `Source/PillowFort/Demos/Demo.h`**, gaining one function
at the end of the class:

```cpp
// Chapter 10: true while the demo wants the mouse to itself - hidden and
// unbounded, for mouse-look. Main applies it after Update. Not pure, so
// demos without a camera need not say anything.
virtual bool WantsCursorCaptured() const { return false; }
```

It is the interface's only function with a body. Every other demo — the
triangle, the gradient — has no camera, and a default of "no" means none of
them changes. **And in `main`'s loop**, right after the active demo's `Update`
(Chapter 09 section 7), so the answer reflects this frame's input:

```cpp
// Chapter 10: mouse-look hides the cursor and frees it from the window's
// edges for as long as the demo asks - and gives it back the moment it
// stops asking, or when there is no demo at all.
window.setCursorCaptured(renderer.demo() != nullptr && renderer.demo()->WantsCursorCaptured());
```

Asking every frame, rather than having the demo request a capture once, is what
makes the cursor come back in every case — the button released, the controller
switched, the demo switched away, or no demo at all. The capture is a function
of the current state, never a state of its own that something could forget to
undo.

---

## 11. The fly controller

**This is `Source/PillowFort/Scene/FlyController.h` and `.cpp`.** W, A, S, and D
move forward, left, back, and right; Q and E move down and up; Shift goes four
times faster. Holding the right mouse button turns the camera with the mouse —
the convention of most 3D editors, which keeps the left button free for
clicking panels and for the orbit controller's drag.

```cpp
// Source/PillowFort/Scene/FlyController.h
#pragma once

#include "PillowFort/Scene/Transform.h"
#include "PillowFort/Window/GlfwWindow.h"   // window::Event, and GLFW's key codes

#include <cstdint>

namespace pf::scene {

// W/S forward and back, A/D left and right, Q/E down and up, Shift to go
// faster; hold the right mouse button to look around. Holds input state only:
// the pose lives in the Transform that Update is handed.
class FlyController
{
public:
    float moveSpeed       = 5.0f;     // metres per second
    float lookSensitivity = 0.003f;   // radians per pixel of mouse movement
    float boostMultiplier = 4.0f;     // while Shift is held

    void HandleEvent(const window::Event& event);
    bool Update(float deltaSeconds, Transform& transform);   // true if it moved the transform
    bool WantsCursorCaptured() const { return m_looking; }
    void ReleaseAll();                                       // forget everything held

private:
    enum HeldKey : uint32_t
    {
        MoveForward = 1u << 0, MoveBack = 1u << 1, MoveLeft = 1u << 2, MoveRight = 1u << 3,
        MoveDown    = 1u << 4, MoveUp   = 1u << 5, Boost    = 1u << 6,
    };

    uint32_t m_held       = 0;       // HeldKey bits, from press and release events
    bool     m_looking    = false;   // right button down
    bool     m_haveCursor = false;   // a cursor position seen since the button went down
    double   m_cursorX    = 0.0;
    double   m_cursorY    = 0.0;
    float    m_pendingYaw   = 0.0f;  // radians, collected from events until the next Update
    float    m_pendingPitch = 0.0f;
};

} // namespace pf::scene
```

The `window::Event` it consumes uses GLFW's key and button codes, so the header
includes `GlfwWindow.h`. That makes `Scene` depend on `Window` for one struct and
some constants, which is acceptable: the controllers *are* the code that turns
window input into camera motion. No GLFW function is called outside `Window`.
`FlyController.cpp` includes `FlyController.h` and `<algorithm>` for
`std::clamp`.

The work is split across two functions, because input and time arrive
separately. `HandleEvent` is called once per event and only records what
happened: which keys are now held, and how far the mouse moved while looking.
`Update` is called once per frame with the frame's duration, and turns that
state into motion.

```cpp
void FlyController::HandleEvent(const window::Event& event)
{
    if (event.kind == window::EventKind::Key)
    {
        uint32_t bit = 0;
        switch (event.code)
        {
        case GLFW_KEY_W:            bit = MoveForward; break;
        case GLFW_KEY_S:            bit = MoveBack;    break;
        case GLFW_KEY_A:            bit = MoveLeft;    break;
        case GLFW_KEY_D:            bit = MoveRight;   break;
        case GLFW_KEY_Q:            bit = MoveDown;    break;
        case GLFW_KEY_E:            bit = MoveUp;      break;
        case GLFW_KEY_LEFT_SHIFT:
        case GLFW_KEY_RIGHT_SHIFT:  bit = Boost;       break;
        default:                    return;
        }
        // REPEAT changes nothing: the key was already held.
        if (event.action == GLFW_PRESS)   { m_held |= bit; }
        if (event.action == GLFW_RELEASE) { m_held &= ~bit; }
    }
    else if (event.kind == window::EventKind::MouseButton && event.code == GLFW_MOUSE_BUTTON_RIGHT)
    {
        m_looking    = event.action == GLFW_PRESS;
        m_haveCursor = false;   // the next position is the reference, not a movement
    }
    else if (event.kind == window::EventKind::CursorPosition && m_looking)
    {
        if (m_haveCursor)
        {
            // Screen Y grows downward, so moving the mouse down looks down.
            m_pendingYaw   -= static_cast<float>(event.x - m_cursorX) * lookSensitivity;
            m_pendingPitch -= static_cast<float>(event.y - m_cursorY) * lookSensitivity;
        }
        m_cursorX    = event.x;
        m_cursorY    = event.y;
        m_haveCursor = true;
    }
}
```

Held keys are bits, set on press and cleared on release; `GLFW_REPEAT`, which
GLFW sends while a key stays down, changes nothing. The mouse delta is collected
in `m_pendingYaw` and `m_pendingPitch` — several cursor events can arrive in one
frame — and the **first** cursor position after the button goes down is only a
reference, never a movement. Without that, the first event would measure the
distance from wherever the cursor was when the last drag ended, and the view
would jump. (Positions over an ImGui panel never reach the controller either —
Chapter 07's filter drops them — so the last position it saw can be stale
for another reason too.) Moving the mouse right turns right, which is a
*decreasing* yaw, because a positive rotation about +Y turns −Z towards −X, to
the left.

```cpp
bool FlyController::Update(float deltaSeconds, Transform& transform)
{
    bool changed = false;

    // Look. The angles come from the transform every time, not from a copy kept
    // here, so anything else that turns the camera is respected.
    if (m_pendingYaw != 0.0f || m_pendingPitch != 0.0f)
    {
        YawPitch angles = yawPitchOf(transform.rotation);
        angles.yaw  += m_pendingYaw;
        angles.pitch = std::clamp(angles.pitch + m_pendingPitch, -MAX_PITCH, MAX_PITCH);
        transform.rotation = rotationFromYawPitch(angles);
        m_pendingYaw   = 0.0f;
        m_pendingPitch = 0.0f;
        changed = true;
    }

    // Move: along where the camera looks, and along world up for Q and E.
    glm::vec3 direction{ 0.0f };
    if (m_held & MoveForward) { direction += transform.Forward(); }
    if (m_held & MoveBack)    { direction -= transform.Forward(); }
    if (m_held & MoveRight)   { direction += transform.Right(); }
    if (m_held & MoveLeft)    { direction -= transform.Right(); }
    if (m_held & MoveUp)      { direction += glm::vec3(0.0f, 1.0f, 0.0f); }
    if (m_held & MoveDown)    { direction -= glm::vec3(0.0f, 1.0f, 0.0f); }

    if (glm::dot(direction, direction) > 0.0f)
    {
        // Normalized, so a diagonal is not faster than straight ahead; scaled by
        // the frame's duration, so speed does not depend on the frame rate.
        const float speed = moveSpeed * ((m_held & Boost) ? boostMultiplier : 1.0f);
        transform.translation += glm::normalize(direction) * speed * deltaSeconds;
        changed = true;
    }
    return changed;
}
```

Two details are what make this feel right:

- **The direction is normalized before it is scaled.** W and D together would
  otherwise move at √2 times the speed.
- **The distance is speed times `deltaSeconds`.** A controller that moved a
  fixed step per frame would fly twice as fast at 120 fps as at 60. Chapter 09
  clamps `deltaSeconds` to 0.1 s, so the frame after a stall (a minimized
  window, Windows' modal resize loop) does not teleport the camera.

Forward follows the view, pitch included — looking up and pressing W climbs —
while Q and E move along the world's up, not the camera's. That is "flying";
a walking controller would flatten forward onto the ground plane instead.

```cpp
void FlyController::ReleaseAll()
{
    m_held         = 0;
    m_looking      = false;
    m_haveCursor   = false;
    m_pendingYaw   = 0.0f;
    m_pendingPitch = 0.0f;
}
```

`ReleaseAll` is for switching controllers: the one being switched away from
must not keep a key it will never hear released.

---

## 12. Both controllers, and their panel

**This is `Source/PillowFort/Scene/CameraControls.h` and `.cpp`.** Every demo
with a camera from here on — these cubes, Chapter 11's meshes, Chapter 12's
scene graph, and the rest — wants both controllers, one active at a time, and a
panel to pick between them. So the pair gets one home in `Scene`, rather than a
copy in each demo's folder.

### What the orbit controller needs for it

Two controllers sharing one camera need two things from each — whether it
wants the cursor captured, and a way to forget everything held when it is
switched away from — and one more from the orbit: a way to start from wherever
the fly controller left the camera. The fly controller has its two already
(section 11). **This is `OrbitController.h`**, three lines after `Update`:

```cpp
    bool WantsCursorCaptured() const { return false; }       // the cursor stays visible while dragging
    void ReleaseAll();

    // Put the target `distance` in front of the camera, so that switching to
    // orbiting does not move the view.
    void Retarget(const Transform& camera);
```

The cursor stays visible while orbiting: the drag is short, and a visible
pointer that stops at the window's edge is what people expect from a
turntable. **And `OrbitController.cpp`:**

```cpp
void OrbitController::ReleaseAll()
{
    m_dragging     = false;
    m_haveCursor   = false;
    m_pendingYaw   = 0.0f;
    m_pendingPitch = 0.0f;
    m_pendingZoom  = 0.0f;
}
```

```cpp
void OrbitController::Retarget(const Transform& camera)
{
    target = camera.translation + camera.Forward() * distance;
}
```

`Retarget` is what makes switching from flying to orbiting seamless: instead
of snapping the camera back to the old target, the orbit adopts a target
straight ahead of wherever the camera already is, at the distance it had.

### The pair

**This is `CameraControls.h`:**

```cpp
// Source/PillowFort/Scene/CameraControls.h
#pragma once

#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/FlyController.h"
#include "PillowFort/Scene/OrbitController.h"

namespace pf::scene {

enum class ControllerKind { Fly, Orbit };

// What every camera-driving demo owns. Only the active controller sees input.
struct CameraControls
{
    ControllerKind  active = ControllerKind::Orbit;
    FlyController   fly;
    OrbitController orbit;

    void HandleEvent(const window::Event& event);
    bool Update(float deltaSeconds, Transform& transform);
    bool WantsCursorCaptured() const;

    // Switch controllers without a jump: the old one forgets what was held, and
    // an orbit starts around a point in front of where the camera already looks.
    void Select(ControllerKind kind, const Transform& current);
};

// One ImGui window, "Camera". Edits the projection and the controllers, and
// shows where the camera is. True if anything changed.
bool drawCameraPanel(Camera& camera, CameraControls& controls, const Transform& cameraTransform);

} // namespace pf::scene
```

```cpp
void CameraControls::HandleEvent(const window::Event& event)
{
    if (active == ControllerKind::Fly) { fly.HandleEvent(event); }
    else                               { orbit.HandleEvent(event); }
}
```

```cpp
bool CameraControls::Update(float deltaSeconds, Transform& transform)
{
    return active == ControllerKind::Fly ? fly.Update(deltaSeconds, transform)
                                         : orbit.Update(deltaSeconds, transform);
}
```

```cpp
bool CameraControls::WantsCursorCaptured() const
{
    return active == ControllerKind::Fly && fly.WantsCursorCaptured();
}
```

```cpp
void CameraControls::Select(ControllerKind kind, const Transform& current)
{
    if (kind == active) { return; }
    fly.ReleaseAll();
    orbit.ReleaseAll();
    if (kind == ControllerKind::Orbit) { orbit.Retarget(current); }
    active = kind;
}
```

The panel is a free function beside the data it edits, for Chapter 07 section
9's reasons: it does not know who owns the camera, and the demo decides where
to call it. Its `.cpp` includes `<imgui.h>` and `<algorithm>`; the header does
not, so code that only wants the controllers does not pull in ImGui.

```cpp
bool drawCameraPanel(Camera& camera, CameraControls& controls, const Transform& cameraTransform)
{
    bool changed = false;
    ImGui::SetNextWindowPos(ImVec2(10.0f, 220.0f), ImGuiCond_FirstUseEver);   // below "Frame"
    if (ImGui::Begin("Camera"))
    {
        // Degrees in the UI, radians in the struct.
        float fovDegrees = glm::degrees(camera.verticalFov);
        if (ImGui::SliderFloat("Vertical FOV", &fovDegrees, 20.0f, 120.0f, "%.0f deg"))
        {
            camera.verticalFov = glm::radians(fovDegrees);
            changed = true;
        }
        // Logarithmic: the interesting values of both span orders of magnitude.
        changed |= ImGui::SliderFloat("Near", &camera.nearPlane, 0.01f, 10.0f, "%.3f m",
                                      ImGuiSliderFlags_Logarithmic);
        changed |= ImGui::SliderFloat("Far", &camera.farPlane, 10.0f, 5000.0f, "%.0f m",
                                      ImGuiSliderFlags_Logarithmic);
        camera.farPlane = std::max(camera.farPlane, camera.nearPlane * 2.0f);   // keep near < far

        ImGui::Separator();
        int kind = controls.active == ControllerKind::Fly ? 0 : 1;
        const bool flyPicked   = ImGui::RadioButton("Fly", &kind, 0);
        ImGui::SameLine();
        const bool orbitPicked = ImGui::RadioButton("Orbit", &kind, 1);
        if (flyPicked || orbitPicked)
        {
            controls.Select(kind == 0 ? ControllerKind::Fly : ControllerKind::Orbit, cameraTransform);
            changed = true;
        }

        if (controls.active == ControllerKind::Fly)
        {
            ImGui::TextUnformatted("WASD move, Q/E down/up, Shift faster");
            ImGui::TextUnformatted("Hold the right mouse button to look");
            changed |= ImGui::SliderFloat("Speed", &controls.fly.moveSpeed, 0.5f, 50.0f, "%.1f m/s",
                                          ImGuiSliderFlags_Logarithmic);
        }
        else
        {
            ImGui::TextUnformatted("Drag with left mouse to orbit, scroll to zoom");
            const glm::vec3& target = controls.orbit.target;
            ImGui::Text("Target:    %.2f, %.2f, %.2f", target.x, target.y, target.z);
            ImGui::Text("Distance:  %.2f m", controls.orbit.distance);
        }

        const glm::vec3& position = cameraTransform.translation;
        ImGui::Text("Position:  %.2f, %.2f, %.2f", position.x, position.y, position.z);
    }
    ImGui::End();
    return changed;
}
```

The near and far sliders are logarithmic because their useful values span
orders of magnitude — and section 2 showed that the near plane is the one that
decides depth precision. The far plane is kept above the near plane, because
`n = f` divides by zero in the projection.

### The cubes, with both

`CubesDemo` swaps section 8's orbit controller for the pair. In
`CubesDemo.h`, `#include "PillowFort/Scene/CameraControls.h"` replaces the
`OrbitController.h` include, the member becomes

```cpp
    scene::CameraControls m_controls;
```

in place of `m_orbit`, and the class says when it wants the cursor, after
`Teardown`:

```cpp
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }
```

In the **constructor**, every `m_orbit` becomes `m_controls.orbit`, and one
line comes first, saying which controller starts active:

```cpp
    m_controls.active          = scene::ControllerKind::Orbit;
```

**`Update`** feeds the pair instead of the orbit alone, then draws the Camera
panel above the Cubes panel:

```cpp
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    m_controls.Update(input.deltaSeconds, m_camera.transform);
    scene::drawCameraPanel(m_camera, m_controls, m_camera.transform);
```

## Checkpoint

You can now also:

- select Fly in the Camera panel and move with W, A, S, D, Q, and E, faster
  with Shift;
- hold the right mouse button to hide the cursor and look around, and get the
  cursor back where it was on release;
- switch back to Orbit without the view jumping;
- scroll in until the nearest cubes are a few metres away, then drag the Near
  slider up towards 10 m: cubes nearer than the near plane are cut away, and
  one that straddles it is sliced open, showing the inside of its far faces
  (nothing culls them yet; Chapter 11 does). Drag it back to 0.1 m.

---

## If something goes wrong

| Symptom | Likely cause |
| --- | --- |
| Nothing visible, no validation errors | The camera is inside or behind everything: check the Position line in the Camera panel. Or the projection lacks the `[1][1]` negation *and* culling is on (not yet, Chapter 11) |
| The image is upside down | Y is flipped twice (the projection and a negative viewport height) or not at all |
| Near geometry vanishes as if the near plane were far out | `GLM_FORCE_DEPTH_ZERO_TO_ONE` is not defined for this file: GLM wrote `[-1, 1]` depth |
| "This GPU cannot render D32_SFLOAT depth and sample it afterwards." at startup | The GPU lacks the depth format every desktop GPU has (section 9); try the other GPU with `--gpu` |
| Validation: the pipeline's depth attachment format does not match the rendering's | A pipeline built without `depthFormat = context.formats.depth` drawing in a pass that now has depth |
| Validation: image view aspect / format mismatch on the depth view | The view was created with `VK_IMAGE_ASPECT_COLOR_BIT` |
| `SYNC-HAZARD-WRITE-AFTER-WRITE` on the depth image | The depth barrier's source access is `NONE`, or the barrier is missing |
| Boxes look hollow, and far cubes are drawn over near ones from one side | The depth test is off — the Cubes panel's checkbox — or the pipeline has `depthTest` but not `depthWrite`, or the pass has no depth at all: `sceneTargets` does not fill `formats.depth` and the depth view (section 9) |
| Distant surfaces flicker through each other | Depth precision: the near plane is too close (section 2) |
| A cube is stretched along the world's Y as it turns, instead of its own | Scale applied after rotation: the model matrix must be `T * R * S` (section 3) |
| The view snaps when the right button is pressed | The first cursor position after the press was used as a movement instead of a reference |
| The camera keeps moving after a key is released while a panel has focus | Section 10's release rule is missing from the event filter |
| The cursor stays hidden after looking around | `setCursorCaptured` is not called every frame, or not after `Update` |
| Movement is faster at a higher frame rate | Speed not multiplied by `deltaSeconds` |
| The camera jumps when switching from fly to orbit | `Select` did not `Retarget` |

---

## Exit check

- [ ] The Cubes demo shows a grid of turning boxes from above and to one side,
      and the Camera panel shows its position.
- [ ] **Orbit**: dragging with the left mouse button turns the view around the
      middle of the field; scrolling zooms in and out; the camera never passes
      straight overhead (the pitch clamp).
- [ ] **Fly**: after selecting Fly, W/A/S/D/Q/E move the camera, Shift moves it
      faster, and holding the right mouse button hides the cursor and turns the
      view; releasing it brings the cursor back where it was. Switching back to
      Orbit does not move the view.
- [ ] Hold W, click a panel's title bar while still holding it — ImGui now
      wants the keyboard — and release W: the camera stops (section 10's
      release rule).
- [ ] **Near cubes hide far ones from every side.** Orbit half way around the
      field and they still do.
- [ ] **The depth test is proven to be what does it.** Untick "Depth test":
      every box turns hollow, its far faces drawn over its near ones, and from
      the other side of the field far cubes paint over near ones — section
      8's picture. Tick it again.
- [ ] Resizing, maximizing, and minimizing produce no validation errors, and
      the image is never stretched (the aspect ratio follows the window).
- [ ] Validation, with synchronization validation proven on by Chapter 05's
      positive control, is silent for the whole run. As a positive control for
      the new barrier, temporarily change the depth barrier's source access in
      `beginScenePass` to `VK_ACCESS_2_NONE`: sync validation must report
      `SYNC-HAZARD-WRITE-AFTER-WRITE` on the depth image. Put it back.
- [ ] Switching from Cubes to the triangle and back twenty times is
      validation-clean, and the camera is where you left it.

Next: [11 — Meshes](11-Meshes.md)
