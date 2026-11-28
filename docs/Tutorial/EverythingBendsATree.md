# 56 — Everything Bends, page 2: a tree bends from its foot

**Chapter 56's pages:** [1. Section 1 — One front for the whole island](56-Everything-Bends.md) · **2. Section 2 — A tree bends from its foot** · [3. Part 2 — Every part attached, every view the same](EverythingBendsAttached.md) · [4. Parts 3 and 4 — Once a frame, and the clouds aloft](EverythingBendsOnceAFrame.md).

Section 1 made the fronts a fact of the island's world wind, so that a front crossing the coastal grass reaches the
trees behind it ([section 1](56-Everything-Bends.md#1-a-front-is-a-fact-of-the-island)); the trees, the ferns and the shadows do not move yet.
Your tree holds section 1's code, its checkpoint passed and the supplied test at stage 1. Keep
`..\SandboxGame-before-56`, the build you copied before section 1: sections 2, 5 and 7 run it again. The prerequisites
are the chapter's, listed in its [header](56-Everything-Bends.md).

## 2. A tree bends from its foot

A front now reaches every stage that reads the frame. This section makes a tree answer it: the whole tree leans from its
foot on a spring of its own, every vertex bent by one function that the shaders and a CPU test both compile. Its
branches and leaves ride along rigidly until section 3 gives them motion of their own.

A question that leads to the Jump below: a front reaches the foot of a 12 m oak. If every vertex of the oak moved
downwind by the same distance, what would its roots do? If each moved by a distance that grows with its height, what
would happen to the trunk's length?

<details>
<summary>Hint and answer</summary>

Follow two points, the foot and the crown's top, and measure the distance between them before and after. In the first
rule the roots slide along the ground with the rest of the tree. In the second the foot stays, but the top moves
sideways at the same height, so it ends further from the foot: the trunk stretches.

</details>

> **Jump:** a bend is not a rotation, and not a slide. It is a shear pinned at the root, so the foot stays where it
> stands, followed by a pull-back that puts every point at its old distance from the foot, so the crown swings on an arc
> and no point moves toward or away from the foot.
> [Chapter 47, section 4](47-Grass-Representation-Handover.md#4-animate-derived-data) did the grass's with
> `grassClumpUnlean`; here the shear grows as the square of the height up the plant, so the trunk curves.

<a id="ch56-tree-bends"></a>

### Attempt CH56-tree-bends: a tree that leans from its foot

Predict first: a clump of grass rings at 0.8 Hz. Would an oak ring faster or slower? And what happens if its period
matches the time between two fronts, about 3 s at 5.5 m/s? Start from the spring of
[Chapter 53, section 3](53-Rolling-Wind.md#3-a-push-and-its-swing-back); the answer opens the worked solution. Then
the GPU's side: would you bend in `Leaf.vert` behind a test of the run's numbers, or in a second pipeline? What does
each cost a calm draw, and how would you show the calm picture unchanged? That answer is the solution's paragraph
**A second pipeline, from the same body**.

**Acceptance:** a shared header, `PlantWindSource.h`, compiled as C++ and GLSL as `GrassWindSource.h` is, works out a
plant's lean from the fronts at its foot through the plant's own spring, and bends a vertex by it with its roots still
and its distance to the foot kept. Every tree near the camera leans on the same fronts as the grass in front of it, and
with **Plants in the wind** off every plant draws with Chapter 39's shaders and Forest floor's frame equals the kept
build's.

**Transfer:** Chapter 39's leaf plates draw with the oak's and the pine's leaf materials. Once the second pipeline is
chosen per material, what do the plates do, and how can they stay rigid with no flag on any draw?

<details>
<summary>Hint 1: one answer per plant</summary>

Everything about the trunk's answer is the same for every vertex of one plant: its foot, its height, the fronts there,
its spring. Write it as a function of those, and let the bend take a vertex and that answer.

</details>

<details>
<summary>Hint 2: what may differ from plant to plant</summary>

Neighbouring trees should not sway as one, so each needs its own gain and frequency, from something that never changes
while the tree stands. Chapter 39's understory compacts its instances every frame, so a slot is no such thing.

</details>

<details>
<summary>Hint 3: where it goes</summary>

The functions go in a new header, `PlantWindSource.h`, beside `GrassWindSource.h`, with `PlantWind.glsl` handing them
`frame`'s blocks. The answer's numbers go in `FrameData` after the fronts, packed from Horizon's rows; a material's own
in `FlatDraw`'s padding, pushed for each run from a table in `SceneRenderer`; and the bend in a second vertex shader
that shares `Leaf.vert`'s body.

</details>

<details>
<summary>Worked solution: one function from the foot, a second pipeline per material</summary>

**Answer to the first prediction.** Slower: a tall trunk is a soft spring under a heavy crown. The chapter takes 0.5 Hz
and a damping ratio of 0.3. A period close to the time between fronts would ring in step with them, each front adding to
the last swing. At 0.5 Hz the period is 2 s, against fronts 3.1 s apart on average (17 m at 5.5 m/s). The jitter, 0.45,
spreads the gaps from about 0.3 to 5.9 s, so some fronts do arrive 2 s apart, but a damping of 0.3 takes a swing down to
about a seventh in one period, and even a push repeated at the spring's own rate for ever would build the swing to only
about 1.75 times its steady size. So each front is a push and a release. A smaller plant answers faster: its frequency
is multiplied by `clamp(sqrt(12 m / h), 1, 4)`. Each plant's gain and frequency spread come from a hash of where its
foot stands, never of an instance slot.

**One header for the bend.** `PlantWindSource.h` follows `GrassWindSource.h`
([Chapter 53, section 2](53-Rolling-Wind.md#2-a-steady-wind-and-a-blade-that-stays-whole)): a C++ branch that opens
`pf::plant_wind` and brings in the names GLSL has built in, and macros for the words the two languages disagree on:
`PF_PLANT_FUNCTION`, `PF_PLANT_OUT` for an out parameter, and `PF_PLANT_CONST`, `constexpr` in C++ so a `static_assert`
can read it. Every function takes the frame's blocks and the camera as arguments, so a vertex stage and the test each
call it with what they have. Four things are worth reading before the listing:

- **The fronts' frame is the grass kernel's, copied.** `plantFrontAnswer` puts the foot into the fronts' frame with the
  kernel's lines, section 1's correction included, then calls Chapter 53's `frontResponse` for the gusts and the
  ripples, so a tree feels the same fronts as a clump at its foot. The same lines, copied: no C++ compiles the kernel,
  so nothing can compare the two copies, and the supplied test compares this header with a copy of its own.
- **The trunk's lean**, `plantTrunkLean`, is a fraction of the plant's height: a steady part from Chapter 53's drag
  curve, with its knee at 9 m/s, plus the gust span times the front answer. Each plant's gain (0.7 to 1.3) and its
  frequency's spread (±15 %) come from a hash of its foot.
- **The soft stop is written without `pow`.** With q = lean / 0.3 it is lean / ⁴√(1 + q⁴), q⁴ taken as q² · q². GLSL
  leaves `pow` undefined for a negative base, and an underdamped trunk rings back past upright, so the lean goes
  negative after a push. Chapter 53's `softLimit` takes the same fourth root, as two square roots.
- **The bend.** `bendPlant` moves a point downwind by tip · s², s being how far up the plant it is (0 at the foot, 1 at
  the height), then scales it about the foot back to its old distance: the Jump's shear and pull-back. `bendNormal`
  turns the normal to match, worked out below the list.

**The normal, worked once.** Tangents along a surface move with the bend's derivative, the matrix of how the moved
point changes as the rest point moves, so a normal moves by that matrix's inverse transpose: the argument of
[Chapter 11, section 13](11-Meshes.md#13-how-normals-move-the-normal-matrix), with the derivative in place of the model
matrix. Take the shear alone, in the plane of the wind, with (along, up) as the axes. It moves a point along by
tip · (y / h)², so its derivative is [[1, k], [0, 1]], where k = 2 · tip · s / h is the shear's slope at that height.
Its inverse is [[1, −k], [0, 1]] (multiply the two to check), and the transpose of that is [[1, 0], [−k, 1]]: a normal
(a, u) becomes (a, u − k · a). That is `bendNormal`'s one line, and it is exact for the shear. For a 12 m tree whose
tip moves 1 m, a normal facing downwind halfway up (s = 0.5) tilts by k ≈ 0.083, about 4.8 degrees. What `bendNormal`
leaves out is the pull-back's own turn, and that is not small: it is first order in the lean, as the shear's term is.
On the trunk's axis it would turn a normal facing up by tip · s / h downwind, half the shear's slope, and the code
leaves such a normal as it was: near the crown (s = 0.9) that is about 2.6 degrees off at a lean of 0.05 of the
height, and about 15 at the 0.3 stop. Above the plant's height, where s is held at 1, the true slope is 0 and the code
still tilts. So a leaf card facing the sky keeps its rest normal as the tree leans. The chapter keeps this normal, and
nothing measures its error.

**How far out the motion counts.** [Chapter 37, section 5](37-Objects-At-A-Distance.md#5-height-on-screen) gives a
length L at distance d a size on screen of L · H / (2 d tan(θ / 2)) pixels, H the window's height in pixels and θ the
vertical field of view, so one pixel there is 2 d tan(θ / 2) / H long. At 450 m, at 1080p with Horizon's 60 degree lens,
that is 2 × 450 × tan 30° / 1080 ≈ 0.48 m. At Horizon's default wind (5.5 m/s, strength 0.6) an oak's lean rises from
its steady part to a full gust's by 0.30 × (drag(5.5 × 1.6) − drag(5.5)) ≈ 0.065 of its height, drag being
`plantDragBend` below, which at the tip of a 12.13 m oak is about 0.8 m: one to two pixels at 450 m by the plant's gain,
before the spring's overshoot. So the pixel does not end the motion; the hand-over does. Chapter 40 hands the far forest
to impostors at 490 m, where a tree becomes a picture that never bends, so the trunk fades out from 400 to 450 m, giving
up a pixel or two of swing so nothing pops at the hand-over, and past 460 m, `PLANT_CUT`, nothing is worked out at all.
The fade is per plant, from the camera to the foot, so every vertex of one plant agrees. This section adds five files,
so `GenerateProjects.bat` runs again before the build, at the checkpoint. In `Shaders/Include/`, create
`PlantWindSource.h`:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 56 section 2: a plant's trunk answer to the world wind's fronts and the root-pinned bend it drives, one
///         text for GLSL and for the CPU test
/// @copyright (C) Gary 2026
///========================================================
// Every function takes the frame's blocks and the camera as arguments, so a vertex stage, a compute stage and the test all
// call it with what they have (PlantWind.glsl passes `frame`'s). The front answer is Chapter 53's frontResponse, included
// unchanged; the lines that put a plant's foot into the fronts' frame are the grass kernel's, copied by hand (no C++ compiles
// the kernel, so nothing can compare the two copies: the test checks this header against its own hand copy).
#ifndef PF_PLANT_WIND_SOURCE_H
#define PF_PLANT_WIND_SOURCE_H

#include "../Grass/GrassWindSource.h"   // frontResponse, hash01, pcgHash and the front constants, Chapter 53's
#include "SharedShaderTypes.h"          // FrameData's blocks: WindFronts, PlantWind

#ifdef __cplusplus
#include <algorithm>
#include <cmath>
#include <glm/common.hpp>
#include <glm/exponential.hpp>
#include <glm/geometric.hpp>
#include <glm/glm.hpp>
namespace pf::plant_wind
{
using namespace pf::demos::grass;
using shared::PlantWind;
using shared::WindFronts;
using shared::uint;
using glm::clamp;
using glm::distance;
using glm::dot;
using glm::floatBitsToUint;
using glm::length;
using glm::max;
using glm::min;
using glm::normalize;
using glm::smoothstep;
using glm::vec2;
using glm::vec3;
using glm::vec4;
using std::abs;
using std::sqrt;
#define PF_PLANT_FUNCTION inline
#define PF_PLANT_OUT float&
#define PF_PLANT_CONST inline constexpr float   // constexpr in C++, so a static_assert can read it
#else
#define PF_PLANT_FUNCTION
#define PF_PLANT_OUT out float
#define PF_PLANT_CONST const float
#endif

// Where a plant stops answering, by its distance from the camera (metres, camera to foot): the trunk's motion fades out
// between these two, and past PLANT_CUT nothing is evaluated at all. The fade ends at 450 m because the far forest's
// hand-over to impostors (Chapter 40, TREE_MESH_ENTER) is at 490 m, where a tree becomes a picture that never bends. All
// three sit below it, and the build asserts it (HorizonDemo.cpp). Section 3 adds the branch's and the flutter's nearer ends.
PF_PLANT_CONST PLANT_TRUNK_FADE_START = 400.0f;
PF_PLANT_CONST PLANT_TRUNK_FADE_END   = 450.0f;
PF_PLANT_CONST PLANT_CUT              = 460.0f;

PF_PLANT_CONST PLANT_KNEE       = 9.0f;    // m/s: Chapter 53's drag knee, for a tree
PF_PLANT_CONST PLANT_LEAN_LIMIT = 0.3f;    // the soft stop on the lean, as a fraction of the height

// Chapter 53's saturating drag, as a function of a plant's wind speed: 0..1.
PF_PLANT_FUNCTION float plantDragBend(float windSpeed)
{
    const float pressure = (windSpeed / PLANT_KNEE) * (windSpeed / PLANT_KNEE);
    return pressure / (1.0f + pressure);
}

// The trunk's share of the wind at a distance: 1 near the camera, 0 past PLANT_TRUNK_FADE_END.
PF_PLANT_FUNCTION float plantTrunkFade(float distanceToFoot)
{
    return 1.0f - smoothstep(PLANT_TRUNK_FADE_START, PLANT_TRUNK_FADE_END, distanceToFoot);
}

// The gust layer's answer (and rippleWeight times the ripple layer's) at a plant's foot: the fronts' frame first, as the
// grass kernel builds it (along the wind, across it, the fronts' own travel taken off, the front speed floored), then
// frontResponse for each layer. 0 when the wind is calm or the gust size is 0.
PF_PLANT_FUNCTION float plantFrontAnswer(vec2 foot, float naturalFrequency, float dampingRatio, vec4 windDirection,
                                         vec4 windGust, WindFronts fronts, float rippleWeight)
{
    const float speed = windGust.z;
    if (windGust.y < 0.5f || speed <= 0.0f)
    {
        return 0.0f;
    }
    const vec2  along      = vec2(windDirection.x, windDirection.y);
    const vec2  across     = vec2(-along.y, along.x);
    const vec2  frontFrame = foot - fronts.frontSpeed * (vec2(windDirection.z, windDirection.w) + vec2(fronts.travelCorrectionX, fronts.travelCorrectionY));
    const float alongWind  = dot(frontFrame, along);
    const float acrossWind = dot(frontFrame, across);
    const float frontMetresPerSecond = max(fronts.frontSpeed * speed, MIN_FRONT_SPEED);
    const float zeta = clamp(dampingRatio, MIN_DAMPING, MAX_DAMPING);
    const float gust = frontResponse(alongWind, acrossWind, naturalFrequency, zeta, frontMetresPerSecond, 0.0f,
                                     max(fronts.gustSpacing, MIN_FRONT_METRES), fronts.gustJitter,
                                     max(fronts.gustCrestLength, MIN_FRONT_METRES), fronts.gustCrestBend, fronts.gustOccupancy,
                                     fronts.gustLengthMin, max(fronts.gustLengthMax, fronts.gustLengthMin),
                                     0.0f, fronts.frontSizeFloor, GUST_SALT).x;
    const float ripple = frontResponse(alongWind, acrossWind, naturalFrequency, zeta, frontMetresPerSecond, 0.0f,
                                       max(fronts.rippleSpacing, MIN_FRONT_METRES), fronts.rippleJitter,
                                       RIPPLE_CREST_LENGTH, RIPPLE_CREST_BEND, fronts.rippleOccupancy, RIPPLE_LENGTH_MIN,
                                       RIPPLE_LENGTH_MAX, fronts.rippleBaseline, fronts.frontSizeFloor, RIPPLE_SALT).x;
    return gust + rippleWeight * ripple;
}

// The trunk's whole answer as a fraction of the plant's height: the fade times the soft-stopped lean. 0 for a rigid plant
// (no height), a calm wind, all four amounts at 0, or a plant past the trunk's fade. The plant's own gain, spread and
// frequency come from a hash of where it stands, never of an instance slot, which changes with the draw order.
PF_PLANT_FUNCTION float plantTrunkLean(vec3 foot, float height, vec3 camera, vec4 windDirection, vec4 windGust,
                                       WindFronts fronts, PlantWind plant)
{
    const float speed   = windGust.z;
    const float amounts = abs(plant.steadyLean) + abs(plant.gustLean) + abs(plant.branchMetres) + abs(plant.flutterMetres);
    if (height <= 0.0f || amounts == 0.0f || windGust.y < 0.5f || speed <= 0.0f)
    {
        return 0.0f;
    }
    const float fade = plantTrunkFade(distance(foot, camera));
    if (fade <= 0.0f)
    {
        return 0.0f;
    }
    const uint  seed  = pcgHash(floatBitsToUint(foot.x) * 747796405u ^ pcgHash(floatBitsToUint(foot.z) + 17u));
    const float gain  = mix(0.7f, 1.3f, float(seed >> 8u) * (1.0f / 16777216.0f));
    const float apart = float(pcgHash(seed + 1u) >> 8u) * (1.0f / 16777216.0f);
    // A small plant answers faster: the natural frequency rises as the square root of the height falls, to four times.
    const float naturalFrequency = 6.2831853f * plant.trunkFrequency * (1.0f + 0.15f * (2.0f * apart - 1.0f))
                                 * clamp(sqrt(12.0f / height), 1.0f, 4.0f);
    const float answer = plantFrontAnswer(vec2(foot.x, foot.z), naturalFrequency, plant.trunkDamping, windDirection, windGust,
                                          fronts, plant.rippleWeight);
    const float strength = windGust.x;
    const float steady   = plant.steadyLean * plantDragBend(speed);
    const float gustSpan = plant.gustLean * (plantDragBend(speed * (1.0f + strength)) - plantDragBend(speed));
    float       lean     = steady + gustSpan * gain * answer;
    // The soft stop: nearly the lean itself below the limit, none further past it. Written without pow, whose base GLSL
    // leaves undefined when negative, and an underdamped trunk rings back past upright: q^4 is q2 * q2.
    const float q  = lean / PLANT_LEAN_LIMIT;
    const float q2 = q * q;
    lean = lean / sqrt(sqrt(1.0f + q2 * q2));
    return fade * lean;
}

// A root-pinned shear: the point moves along the wind by tipMetres * s^2 (s: how far up the plant it is, 0..1), then is
// pulled back to its old distance from the foot: each point keeps its distance to the foot, not the curve's length, so a
// crown swings on an arc and does not stretch. The foot (s = 0) stays.
PF_PLANT_FUNCTION vec3 bendPlant(vec3 world, vec3 foot, float height, vec2 along, float tipMetres, PF_PLANT_OUT s)
{
    s = clamp((world.y - foot.y) / height, 0.0f, 1.0f);
    const vec3 moved  = world + vec3(along.x, 0.0f, along.y) * (tipMetres * s * s);
    const vec3 before = world - foot;
    const vec3 after  = moved - foot;
    return foot + after * (length(before) / max(length(after), 1.0e-4f));
}

// The normal of the sheared plant: the shear's slope is 2 * tip * s / height, and a normal tilts against it. This is the
// shear's exact inverse transpose; the pull-back's turn is left out, and it is first order in the lean, not small. Where s is
// clamped the true slope is 0; the code keeps it.
PF_PLANT_FUNCTION vec3 bendNormal(vec3 normal, vec2 along, float height, float tipMetres, float s)
{
    normal.y -= 2.0f * tipMetres / height * s * dot(along, vec2(normal.x, normal.z));
    return normalize(normal);
}

#undef PF_PLANT_FUNCTION
#undef PF_PLANT_OUT
#undef PF_PLANT_CONST
#ifdef __cplusplus
}
#endif
#endif
```

The shaders call it through a small wrapper that hands it what `frame` holds and returns the point unchanged for a rigid
plant, a calm wind or a plant past the cut. In `Shaders/Include/`, create `PlantWind.glsl`:

```glsl
// Shaders/Include/PlantWind.glsl - Chapter 56 section 2: a plant bends on the world wind's fronts, from its foot.
// An include, not a stage. The including shader says #extension GL_GOOGLE_include_directive : require, then
// #include "FrameBlock.glsl" (for `frame`) first. PlantWindSource.h holds the functions over arguments, so the test runs
// the same text; this file only hands them what `frame` holds.
#ifndef PF_PLANT_WIND_GLSL
#define PF_PLANT_WIND_GLSL

#include "PlantWindSource.h"

// A vertex of a plant standing at `foot`, `height` metres tall in the world (its plant-space height times its own scale),
// answering the wind with `bend` (0..1) of the lean. Returns the moved point and corrects `normal`. A plant that stands
// still (no height or bend), a wind that is calm, a plant with no amounts and one past PLANT_CUT all return `world`.
vec3 plantWind(vec3 world, inout vec3 normal, vec3 foot, float height, float bend)
{
    PlantWind plant   = frame.plantWind;
    float     amounts = abs(plant.steadyLean) + abs(plant.gustLean) + abs(plant.branchMetres) + abs(plant.flutterMetres);
    if (height <= 0.0 || bend <= 0.0 || amounts == 0.0 || frame.windGust.y < 0.5 || frame.windGust.z <= 0.0)
    {
        return world;
    }
    if (distance(foot, frame.cameraPosition.xyz) >= PLANT_CUT)   // a per-plant value
    {
        return world;
    }
    vec2  along     = frame.windDirection.xy;
    float tipMetres = height * bend * plantTrunkLean(foot, height, frame.cameraPosition.xyz, frame.windDirection,
                                                     frame.windGust, frame.windFronts, plant);
    float s;
    vec3  moved = bendPlant(world, foot, height, along, tipMetres, s);
    normal      = bendNormal(normal, along, height, tipMetres, s);
    return moved;
}

#endif
```

**The plants' block, as rows.** How a plant answers is the same for every plant in a frame, so it goes in `FrameData`
too: seven floats and a spare, 32 bytes, appended at 512. All zero is rigid, so every demo that never fills it draws its
plants still. In `SharedShaderTypes.h`, below the `};` that closes `WindFronts`, add, with a blank line on each side:

```cpp
/* Chapter 56 section 2: how the plants answer the fronts: the response of every plant in a frame, the same for all of them
   (a tree's own numbers come from where it stands). All zero is rigid. std140: eight floats, 32 bytes. */
struct PlantWind
{
    float trunkFrequency;   /*   0  Hz: the trunk's own spring, before each plant's spread */
    float trunkDamping;     /*   4  the trunk's damping ratio */
    float steadyLean;       /*   8  fraction of its height at full drag (half of it at the 9 m/s knee) */
    float gustLean;         /*  12  fraction of its height per unit of drag rise, before the plant's gain and the spring's overshoot; the soft stop caps the lean at 0.3 */
    float rippleWeight;     /*  16  how much of the ripple layer the trunk answers, against the gust layer's 1 */
    float branchMetres;     /*  20  section 3: how far a crown's outer branches sway, metres */
    float flutterMetres;    /*  24  section 3: how far a leaf card's tip shivers, metres */
    float spare;            /*  28  free */
};
```

Below `FrameData`'s `windFronts` member add the first listing; replace
`static_assert(sizeof(FrameData) == 512, "FrameData layout drifted.");` with the second; and below the `windFronts`
offset assert add `static_assert(offsetof(FrameData, plantWind) == 512, "FrameData alignment drifted.");`, indented as
its neighbours:

```cpp
    /* Chapter 56 section 2: how the plants answer them. All zero is rigid. */
    PlantWind  plantWind;   /* 512  32 bytes */
```

```cpp
    static_assert(sizeof(PlantWind) == 32, "PlantWind layout drifted.");
    static_assert(offsetof(PlantWind, rippleWeight) == 16 && offsetof(PlantWind, spare) == 28, "PlantWind alignment drifted.");
    static_assert(sizeof(FrameData) == 544, "FrameData layout drifted.");
```

Your two tests hold `FrameData`'s size again. In `WorldWindTests.cpp`, replace the line that starts
`static_assert(sizeof(shared::FrameData) == 512` with the first; in `RendererConvergenceTests.cpp`, replace the two
lines of the `check` that starts `check(sizeof(frame) == 512` with the second:

```cpp
static_assert(sizeof(shared::FrameData) == 544, "FrameData must be 544 bytes from Chapter 56 section 2.");
```

```cpp
            check(sizeof(frame) == 544 && frame.haze == glm::vec4(0.0f) && frame.hazeSky == 0,
                  "FAIL: FrameData is 544 bytes (haze, wind, fronts and the plants' block) and its haze is off by default");
```

Horizon owns the numbers, as rows of the same kind as the fronts', with `shared::PlantWind` as the block. The defaults
are the chapter's tuning: a trunk at 0.5 Hz and damping 0.3, a steady lean of 0.04 of the height at full drag, and a
gust lean of 0.30 of it per unit of drag rise, the whole lean softly stopped at 0.3 of the height. The branch and
flutter rows are section 3's, here so the block has all its numbers. In `HorizonDemo.h`, add
`#include "PillowFort/DebugPanels/SettingRows.h"` below `#include "PillowFort/Demos/Horizon/CoastalArea.h"`, and below
`LOW_COARSE_CASTERS` and its blank line, add, with a blank line below it:

```cpp
// Chapter 56 section 2: how the plants answer the world wind, as rows: the settings, and the PlantWind block each is packed
// into. The first five are the trunk's; the last two are section 3's, here so the block has all its numbers.
struct PlantWindSettings
{
    float trunkFrequency = 0.5f;    // Hz: an oak's own spring, slower than a clump of grass's 0.8
    float trunkDamping   = 0.3f;    // underdamped: each front is a push and a release
    float steadyLean     = 0.04f;   // fraction of its height at full drag (half of it at the 9 m/s knee)
    float gustLean       = 0.30f;   // fraction of its height per unit of drag rise, before gain and overshoot; the soft stop caps the lean at 0.3
    float rippleWeight   = 0.3f;    // how much of the ripple layer the trunk answers
    float branchMetres   = 0.15f;   // section 3
    float flutterMetres  = 0.03f;   // section 3
};

enum PlantWindGroup : int
{
    PLANT_WIND_RESPONSE
};

using PlantWindSetting = debug_panels::SettingRow<PlantWindSettings, shared::PlantWind, PlantWindGroup>;

// Designated, as the fronts' rows are. A typed value stays inside its range: a damping of 1 has no ringing to compute.
#define PF_PLANT_WIND_ROW(M, MIN, MAX, DECIMALS, LABEL) \
    { .name = #M, .member = &PlantWindSettings::M, .field = &shared::PlantWind::M, .range = { MIN, MAX }, .decimals = DECIMALS, \
      .label = LABEL, .group = PLANT_WIND_RESPONSE, .flags = debug_panels::SETTING_HOLDS }
inline constexpr auto PLANT_WIND_ROWS = std::to_array<PlantWindSetting>({
    PF_PLANT_WIND_ROW(trunkFrequency, 0.05f, 3.0f, 2, "Tree frequency (Hz)"),
    PF_PLANT_WIND_ROW(trunkDamping, 0.02f, 0.95f, 2, "Damping"),
    PF_PLANT_WIND_ROW(steadyLean, 0.0f, 0.5f, 3, "Steady lean"),
    PF_PLANT_WIND_ROW(gustLean, 0.0f, 1.0f, 3, "Gust lean"),
    PF_PLANT_WIND_ROW(rippleWeight, 0.0f, 2.0f, 2, "Ripple weight"),
    PF_PLANT_WIND_ROW(branchMetres, 0.0f, 1.0f, 3, "Branch sway (m)"),
    PF_PLANT_WIND_ROW(flutterMetres, 0.0f, 0.2f, 3, "Flutter (m)"),
});
static_assert(PLANT_WIND_ROWS.size() == 7, "one row per plant response setting");
static_assert(debug_panels::settingRowsValid(PLANT_WIND_ROWS));
#undef PF_PLANT_WIND_ROW
```

**Plants in the wind** is a switch: off, the block stays 0 and every plant draws with Chapter 39's shaders. Directly
below `m_windGuide`, with no blank line, add the first listing; below `SetWindFront`'s closing brace, the second, which
`--plant-wind` calls, with no blank line above or below it:

```cpp
    // Chapter 56 section 2: "Plants in the wind". Off, every plant run draws with Chapter 39's shaders and the block is zero.
    bool                               m_plantWindOn = true;
    PlantWindSettings                  m_plantWindSettings;
```

```cpp
    void SetPlantWind(bool enabled) { m_plantWindOn = enabled; }   // Chapter 56 section 2: --plant-wind 0|1
```

In `HorizonDemo.cpp`'s `Record`, pack the rows below the `applyWorldWind` line, only while the switch is on:

```cpp
    // Chapter 56 section 2: how the plants answer it; with the switch off every amount is 0, which is rigid.
    if (m_plantWindOn) { debug_panels::packSettingRows(PLANT_WIND_ROWS, m_plantWindSettings, frameData.plantWind, true); }
```

and in `DrawWindControls`, replace the line `ImGui::TextWrapped("Trees, understory, far forest: nothing yet");` with:

```cpp
    ImGui::TextWrapped("Trees: the same fronts (Plants in the wind); understory, far forest: nothing yet");
    // Chapter 56 section 2: how the plants answer it. Off, every plant draws with Chapter 39's shaders and the block is 0.
    if (ImGui::TreeNode("Plants in the wind"))
    {
        debug_panels::checkbox("Plants in the wind", &m_plantWindOn);
        debug_panels::drawSettingRows(PLANT_WIND_ROWS, PLANT_WIND_RESPONSE, m_plantWindSettings);
        ImGui::TreePop();
    }
```

**What differs from plant to plant.** Three numbers belong to a plant's material, not to the frame: its height in plant
space, the share of the lean it takes, and section 3's flutter. They ride in `FlatDraw`'s three padding words, which the
leaf pipelines already push for every run, so `InstanceData` keeps its 112 bytes in every demo. The words stay `uint`,
carrying a float's bits, so the shaders that read `FlatDraw` and know nothing of wind compile as before. In
`HorizonTypes.h`, replace the three lines from `uint padding0;` to `uint padding2;` with:

```cpp
    uint windHeightBits;    /* 36  Chapter 56 section 2: the run's plant height in plant space, metres, as float bits (read with
                                  uintBitsToFloat); 0 is rigid. Only the wind pipelines' vertex stage reads it. These three
                                  words stay uint, as ShadowDrawData's do, so no base shader's code changes (Release byte
                                  for byte; Debug once its names are stripped) */
    uint windBendBits;      /* 40  the share of the lean this material takes, 0..1, as float bits */
    uint windFlutterBits;   /* 44  section 3: 1 for a leaf card, 0 for bark, as float bits; nothing reads it yet */
```

`SceneRenderer` holds one table, by material, that the demo fills once; zero, the default, is rigid, so no other demo
changes. In `SceneRenderer.h`, below `MaterialCount()`, add the first listing; below `m_gpuMaterials` and one blank
line, the second, with one blank line between it and `ShadowMaps m_shadows` below. In `SceneRenderer.cpp`'s `Shutdown`,
below `m_materials.clear();`, add the third:

```cpp
    // Chapter 56 section 2: how a material's parts answer the world wind: x its height in plant space (metres), y the share of
    // the lean it takes (0..1), z its leaf cards' flutter (0 or 1; section 3 reads it). The demo that draws bending plants
    // fills it once and pushes a run's numbers when it binds the run. Zero, the default, is rigid, so no other demo changes.
    void SetMaterialWind(uint32_t material, glm::vec3 wind)
    {
        if (m_materialWind.size() <= material) { m_materialWind.resize(material + 1, glm::vec3(0.0f)); }
        m_materialWind[material] = wind;
    }
    glm::vec3 MaterialWind(uint32_t material) const { return material < m_materialWind.size() ? m_materialWind[material] : glm::vec3(0.0f); }
```

```cpp
    std::vector<glm::vec3>         m_materialWind;               // Chapter 56 section 2: SetMaterialWind's, by material
```

```cpp
    m_materialWind.clear();       // Chapter 56 section 2: the demo registers the wind table again after Initialize
```

**One height per species.** Section 5's shadows read a plant's height whichever material a vertex has, so a species'
bark and leaves must share one. The heights come from the scene's meshes: a mismatch is a data error, so `Setup` fails
and names the species, as a missing file is reported. The species' height is LOD0's, and LOD1's must agree within
0.01 m. The LOD2 stand-in is a smaller shape by design (the function's comment gives the oak's numbers), so it is not
measured: its materials take the species' height, and its shadow will lean with the tree. The rule is a free function
over plain data, so the supplied test runs the same text. In `Source/PillowFort/Demos/Horizon/`, create
`PlantWindTable.h`:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 56 section 2: the rule that gives every material of a species one plant height, as a free function over
///         plain data, so Horizon's Setup and the supplied test run the same text
/// @copyright (C) Gary 2026
///========================================================
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <format>
#include <functional>
#include <map>
#include <string>

namespace pf::demos::horizon
{
/// What speciesWindHeight decided: one height for the species, and every material that takes it; or the reason it failed.
struct SpeciesWindHeight
{
    bool                        ok     = false;
    float                       height = 0.0f;   // metres in plant space; 0 when the species has no real material
    std::map<uint32_t, float>   materials;       // every material that takes it, with that height, by material index
    std::string                 error;           // set when ok is false
};

/// A species' materials must share one height, because the shadows and the lean pass read it as the plant's whichever
/// material a vertex has. `lod0` and `lod1` are the real levels: for each material they use, the tallest mesh that uses it
/// (in plant space, metres). The first material's height is the species'; any other more than 0.01 m from it is a data
/// error, and the failure names the two materials. `standIn` is the LOD2 stand-in's materials with their own meshes' heights:
/// it is a smaller shape by design (the oak's is 10.83 m against 12.13 m), so it is never measured, and each of its materials
/// that no real level uses takes the species' height, so its shadow leans with the tree.
inline SpeciesWindHeight speciesWindHeight(const std::string& species, const std::map<uint32_t, float>& lod0,
                                           const std::map<uint32_t, float>& lod1, const std::map<uint32_t, float>& standIn,
                                           const std::function<std::string(uint32_t)>& materialName)
{
    std::map<uint32_t, float> heights;
    for (const std::map<uint32_t, float>* level : { &lod0, &lod1 })
    {
        for (const auto& [material, height] : *level)
        {
            float& merged = heights[material];
            merged        = std::max(merged, height);
        }
    }
    SpeciesWindHeight result;
    const float       first = heights.empty() ? 0.0f : heights.begin()->second;
    for (const auto& [material, height] : heights)
    {
        if (std::abs(height - first) > 0.01f)
        {
            result.error = std::format(
                "{}'s materials do not share one height in plant space ({} is {:.3f} m, {} is {:.3f} m); the wind bends a plant by one height.",
                species, materialName(heights.begin()->first), first, materialName(material), height);
            return result;
        }
    }
    for (const auto& entry : standIn)
    {
        heights.try_emplace(entry.first, first);   // its own height, entry.second, is never read
    }
    result.ok     = true;
    result.height = first;
    for (const auto& entry : heights)
    {
        result.materials[entry.first] = first;
    }
    return result;
}

/// How much of its lean a plant material takes, at most 1: a gain above 1 would lean a crown past the bound section 4 derives,
/// and no plant takes more than the whole.
inline constexpr float PLANT_BEND_GAIN = 1.0f;
}   // namespace pf::demos::horizon
```

The bend gain is at most 1: section 4's bound assumes it. `RegisterPlantWind` measures each species' two real levels and
fills the table; a `static_assert` above it keeps the trunk's fade and the cut below the handover. In `HorizonDemo.cpp`,
add three includes: the first listing below `#include "PillowFort/Demos/Horizon/HorizonDemo.h"`, the second below
`#include "Horizon/HorizonTypes.h"   // FlatDraw, shared with Flat.frag.glsl`, and `#include <map>` below
`#include <limits>`:

```cpp
#include "PillowFort/Demos/Horizon/PlantWindTable.h"   // Chapter 56 section 2: speciesWindHeight
```

```cpp
#include "PlantWindSource.h"          // Chapter 56 section 2: PLANT_CUT, the wind's distance rules
```

Below `RegisterProps`' closing brace, add, with a blank line on each side:

```cpp
// Chapter 56 section 2: the trunk's fade and the cut end below the handover to impostors, where a tree is a picture that never
// bends (Chapter 40's 490 m): a plant that would bend is always a mesh.
static_assert(plant_wind::PLANT_TRUNK_FADE_END < plant_wind::PLANT_CUT && plant_wind::PLANT_CUT < TREE_MESH_ENTER,
              "the wind's fade and cut must end before the handover to impostors");

// Chapter 56 section 2: the wind table. For each species, the height in plant space of every material its two real levels
// (LOD0 and LOD1) use (the tallest mesh that uses it): a species' bark and leaf must share one height, because section 5's
// shadows and the lean pass read it as the plant's, whichever material a vertex has. The heights come from the scene's
// meshes, so a mismatch is a data error: Setup fails and says which species. The LOD2 stand-in is a smaller shape by design
// (the oak's is 10.83 m against 12.13 m), so it is not measured: its materials take the species' height, and its shadow leans
// with the tree. Flutter is 0 until section 3.
InitializationResult HorizonDemo::RegisterPlantWind()
{
    if (!m_props.PlantsLoaded())
    {
        return InitializationResult::success();
    }
    static_assert(PLANT_BEND_GAIN <= 1.0f, "a bend gain above 1 leans past section 4's bound");
    const scene::Scene& world = m_props.World();
    for (const char* species : { "OakTree", "PineTree", "Fern", "Flower", "Bush" })
    {
        std::array<uint32_t, 3> meshes{};
        if (!m_props.PlantMeshes(species, meshes))
        {
            continue;
        }
        // By scene material: the tallest mesh of the level that uses it.
        const auto heightsOf = [&](uint32_t mesh) {
            std::map<uint32_t, float> byMaterial;
            const scene::Mesh&        source = world.GetMesh(mesh);
            for (const scene::Submesh& submesh : source.data.submeshes)
            {
                float& height = byMaterial[submesh.materialIndex];
                height        = std::max(height, source.bounds.max.y);
            }
            return byMaterial;
        };
        const SpeciesWindHeight table = speciesWindHeight(
            species, heightsOf(meshes[0]), heightsOf(meshes[1]), heightsOf(meshes[2]),
            [&](uint32_t material) { return world.GetMaterial(material).name; });
        if (!table.ok)
        {
            return InitializationResult::failure(table.error);
        }
        for (const auto& entry : table.materials)
        {
            const uint32_t material = entry.first;
            m_sceneRenderer.SetMaterialWind(material, glm::vec3(table.height, PLANT_BEND_GAIN, 0.0f));
            Log::info(std::format("Horizon wind: {} height {:.2f} m (plant space).", world.GetMaterial(material).name, table.height).c_str());
        }
    }
    return InitializationResult::success();
}
```

In `Setup`, below the line that calls `RegisterProps()`, add:

```cpp
    if (auto result = RegisterPlantWind(); !result) { return result; }   // Chapter 56 section 2
```

**A second pipeline, from the same body.** The second prediction, answered. The bend could be a runtime `if` inside
`Leaf.vert`. Then every calm draw would carry the wind's code, and the calm picture could be shown equal to Chapter 39's
only by capture, GPU by GPU. So the bend lives in a second vertex shader, a twin, and a material that has wind draws
with it while the switch is on; the calm shaders then compile to the code Chapter 39's text gives, and a calm draw pays
nothing for the twin, since `BindLeafRun` binds a pipeline for every run already. The twin is not a copy: `Leaf.vert`'s
body moves to `LeafBody.glsl`, which both files include, and `LeafWind.vert` defines `PF_PLANT_WIND` first. With the
define off, the preprocessor leaves exactly Chapter 39's text.

That claim was measured, by the reference; you need not repeat it. Growing `FrameData` changes the frame block's
declaration in every shader that includes it, with the same function bodies. With that held fixed (each commit's
`SharedShaderTypes.h` on both sides), the reference compiled every stage file of the base at the base and at each
section's commit, in both flag sets, debug information stripped: 266 compiled the same and 4 differed, the two grass
generation shaders in both sets, which take section 1's kernel line.

The twin's vertex stage reads `FlatDraw`'s first 48 bytes, so the leaf layout's push range must reach the vertex stage,
and every `vkCmdPushConstants` names the same stages. The base pipelines are built against that layout too: they are
new pipelines with Chapter 39's shaders, which do not read the vertex stage's range. In `Shaders/Horizon/`, create
`LeafBody.glsl`:

```glsl
// Shaders/Horizon/LeafBody.glsl - Chapter 39 section 3: Flat.vert.glsl, with the texture coordinates the
// leaf cards are cut out by, and where the plant stands, for its tint.
// Chapter 56 section 2: the body of both Leaf.vert.glsl and LeafWind.vert.glsl. The includer's #version, extension and (for the
// wind twin) `#define PF_PLANT_WIND` come first; with the define off, the preprocessor leaves exactly Chapter 39's text.

#include "FrameBlock.glsl"   // set 0 binding 0: frame.viewProjection

#ifdef PF_PLANT_WIND
#include "HorizonTypes.h"    // FlatDraw: its wind words are the run's
#include "PlantWind.glsl"

// The leaf layout's push range reaches this stage (vertex | fragment); only FlatDraw's first 48 bytes are read here.
layout(push_constant) uniform WindPush { FlatDraw draw; };
#endif

// Chapter 11's 48-byte Vertex: position, normal and uv; its tangent, at offset 32, no plant shader reads.
layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUv;

layout(location = 0) out vec3 worldPosition;
layout(location = 1) out vec3 worldNormal;
layout(location = 2) out vec2 uv;
layout(location = 3) flat out vec2 plantBase;   // the plant's own origin, x and z: the same for all of it
layout(location = 4) flat out uint coverageVertex; // stable provoking vertex, not a draw-order instance ID

// Set 0 binding 2: every instance PrepareDraws wrote this frame (Chapter 19 section 3).
layout(std430, set = 0, binding = 2) readonly buffer InstanceBuffer { InstanceData instances[]; };

void main()
{
    InstanceData instance = instances[gl_InstanceIndex];
    vec4 world    = instance.model * vec4(inPosition, 1.0);
#ifdef PF_PLANT_WIND
    vec3 normal = instance.normalMatrix * inNormal;
    // The plant's height in plant space times its own scale, from the run's push; 0 is rigid.
    world.xyz = plantWind(world.xyz, normal, instance.model[3].xyz, uintBitsToFloat(draw.windHeightBits) * length(instance.model[1].xyz),
                          uintBitsToFloat(draw.windBendBits));
#endif
    worldPosition = world.xyz;
#ifdef PF_PLANT_WIND
    worldNormal   = normal;
#else
    worldNormal   = instance.normalMatrix * inNormal;
#endif
    uv            = inUv;
    plantBase     = instance.model[3].xz;
    coverageVertex = uint(gl_VertexIndex);
    gl_Position   = frame.viewProjection * world;
}
```

Replace the whole of `Leaf.vert.glsl` with the first listing, and create `LeafWind.vert.glsl` beside it with the second:

```glsl
// Shaders/Horizon/Leaf.vert.glsl - Chapter 39 section 3: the leaf pipelines' vertex stage. Chapter 56 section 2 moved its
// body to LeafBody.glsl, which LeafWind.vert.glsl includes with the wind on; this file is the body with it off.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "LeafBody.glsl"
```

```glsl
// Shaders/Horizon/LeafWind.vert.glsl - Chapter 56 section 2: Leaf.vert.glsl's body with the plant bent on the world wind's
// fronts. A run whose material has wind draws with this while "Plants in the wind" is on; every other run, and every run
// with it off, draws with Leaf.vert.glsl, which is Chapter 39's text.
#version 450
#extension GL_GOOGLE_include_directive : require
#define PF_PLANT_WIND
#include "LeafBody.glsl"
```

The pipeline table gains a first index, `[wind][understory][mode]`: four more pipelines here, the tree rows' four modes.
Section 4 adds the understory's four and section 5 two shadow pipelines, ten in all. In `HorizonDemo.h`, replace the
line `std::array<std::array<VkPipeline, 4>, 2> m_leafPipelines{};` with:

```cpp
    // [wind][understory][mode]: Chapter 56 section 2 adds the first index, the wind twins of the tree pipelines (the
    // understory's twins are section 4's, so [1][1] stays empty here).
    std::array<std::array<std::array<VkPipeline, 4>, 2>, 2> m_leafPipelines{};
```

In `HorizonDemo.cpp`'s `CreateLeafPipelines`, replace the `pushRange` line with the first listing below. Then replace
the loop, from `for (uint32_t understory = 0; understory < 2; ++understory)` to its closing brace, with the second: the
same body one level deeper, the twin's file chosen by `wind`, and the understory's twins left for section 4:

```cpp
    // Chapter 56 section 2: the range reaches the vertex stage too, for the wind twins' FlatDraw wind words.
    const VkPushConstantRange pushRange{ .stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, .offset = 0,
                                         .size = sizeof(LeafPush) };
```

```cpp
    for (uint32_t wind = 0; wind < 2; ++wind)   // Chapter 56 section 2: every leaf pipeline exists twice, base and wind
    {
        for (uint32_t understory = 0; understory < 2; ++understory)
        {
            if (wind != 0 && understory != 0) { continue; }   // section 4 adds the understory's wind twins
            for (uint32_t mode = 0; mode < 4; ++mode)   // 0 opaque, 1 hardware cutout, 2 overdraw, 3 explicit cutout
            {
                const Constants            values{ mode == 1 || mode == 3 ? VK_TRUE : VK_FALSE, mode == 2 ? VK_TRUE : VK_FALSE,
                                                    static_cast<uint32_t>(m_context.formats.samples) };
                const VkSpecializationInfo specialization{
                    .mapEntryCount = static_cast<uint32_t>(entries.size()),
                    .pMapEntries   = entries.data(),
                    .dataSize      = sizeof(values),
                    .pData         = &values,
                };
                const GraphicsPipelineDesc desc{
                    .vertexShader           = understory ? "Horizon/Understory.vert.spv"
                                            : wind ? "Horizon/LeafWind.vert.spv" : "Horizon/Leaf.vert.spv",
                    .fragmentShader         = mode != 3 ? "Horizon/LeafHardware.frag.spv"
                        : m_context.formats.samples == VK_SAMPLE_COUNT_64_BIT
                            ? "Horizon/Leaf64.frag.spv" : "Horizon/Leaf.frag.spv",
                    .vertexBindings         = { bindings.data(), understory ? 2u : 1u },
                    .vertexAttributes       = { attributes.data(), understory ? 5u : 3u },
                    .colorFormats           = { &m_context.formats.color, 1 },
                    .depthFormat            = m_context.formats.depth,
                    .depthTest              = true,
                    .depthWrite             = mode != 2,   // section 7: counting hides nothing behind it
                    .depthCompare           = VK_COMPARE_OP_GREATER,   // Chapter 35 section 6: reversed, as every pipeline here
                    .frontFace              = VK_FRONT_FACE_COUNTER_CLOCKWISE,
                    .dynamicStates          = dynamicStates,
                    .blend                  = mode == 2 ? BlendMode::Additive : BlendMode::Opaque,
                    .fragmentSpecialization = &specialization,
                    .layout                 = m_leafLayout,
                    .samples                = m_context.formats.samples,
                    .alphaToCoverage        = mode == 1 && multisampled,
                };
                m_leafPipelines[wind][understory][mode] = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, desc);
                if (m_leafPipelines[wind][understory][mode] == VK_NULL_HANDLE)
                {
                    return InitializationResult::failure("Creating the leaf pipelines failed.");
                }
            }
        }
    }
```

`Teardown` walks one level more. Replace its loop over `m_leafPipelines`, from the `for` to its closing brace, with:

```cpp
    for (const auto& rows : m_leafPipelines)                                     // Chapter 39 section 3
    {
        for (const std::array<VkPipeline, 4>& pipelines : rows)
        {
            for (VkPipeline pipeline : pipelines)
            {
                vkDestroyPipeline(m_context.vulkan.device, pipeline, nullptr);
            }
        }
    }
```

**The twin per frame and per material.** `BindLeafRun` takes the switch and picks the twin when it is on and the
material's height and bend are not zero; every other run draws with the base pipeline, Chapter 39's shaders, and
pushes zeros, which it does not read. Nothing marks a plant as bending: a plant past the cut returns early inside the
shader, so `DrawItem`, the sort key, the runs and `Props.cpp` do not change. In `HorizonDemo.h`, replace the lines from
`BindLeafRun`'s declaration down to `CreateLeafPlates`' with these four; the last is new:

```cpp
    void                 BindLeafRun(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t material,
                                     bool understory, bool skyOn, bool wind);   // Chapter 39: sections 3, 5-7; Chapter 56 section 2: wind
    InitializationResult CreateLeafPlates();                                   // Chapter 39: section 6
    InitializationResult RegisterPlantWind();                                  // Chapter 56 section 2: the materials' wind table
```

In `HorizonDemo.cpp`, replace `BindLeafRun`'s first lines, from its signature down to `vkCmdBindPipeline`, with the
first listing, and the lines from `.flags     = flags },` down to `vkCmdPushConstants` with the second:

```cpp
void HorizonDemo::BindLeafRun(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t material, bool understory,
                              bool skyOn, bool windOn)
{
    // Chapter 56 section 2: the wind twin is chosen per frame and per material: the switch is on and the material's wind is
    // not zero. Every other run draws with Chapter 39's shaders and pushes zeros, which it ignores.
    const glm::vec3 windNumbers = windOn && !understory ? m_sceneRenderer.MaterialWind(material) : glm::vec3(0.0f);
    const bool      wind        = windNumbers.x > 0.0f && windNumbers.y > 0.0f;
    const LeafMaterial& leaf = m_leafMaterials[material];
    const bool explicitCoverage = m_context.formats.samples != VK_SAMPLE_COUNT_1_BIT
        && m_plantSettings.alphaToCoverage && m_plantSettings.mipFix && m_plantSettings.decorrelateCoarse;
    const uint32_t mode = m_plantSettings.overdraw ? 2u : leaf.cutout ? (explicitCoverage ? 3u : 1u) : 0u;
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_leafPipelines[wind ? 1 : 0][understory ? 1 : 0][mode]);
```

```cpp
                  .flags     = flags,
                  .windHeightBits  = std::bit_cast<uint32_t>(wind ? windNumbers.x : 0.0f),
                  .windBendBits    = std::bit_cast<uint32_t>(wind ? windNumbers.y : 0.0f),
                  .windFlutterBits = std::bit_cast<uint32_t>(wind ? windNumbers.z : 0.0f) },
        .leaf = { .mipScale = { leaf.mipScale[0], leaf.mipScale[1], leaf.mipScale[2] } },
    };
    vkCmdPushConstants(commandBuffer, m_leafLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(push), &push);
```

The trees' runs in `Record` pass the switch, and the understory's pass `false` until section 4. The two calls become:

```cpp
            BindLeafRun(cb, frame.frameIndex, run.material, false, skyOn, m_plantWindOn);
```

```cpp
            BindLeafRun(cb, frame.frameIndex, material, true, skyOn, false);   // section 4 gives the understory its twin
```

**The leaf plates stay rigid.** [Chapter 39, section 6](39-Plants.md#6-leaves-that-thin-out)'s plates use the oak's and
the pine's leaf materials, which now have wind, so they would bend. Their rows take copies of those two materials, as
the ash's row has its own; a copy has nothing in the table, so the per-material choice draws it with the base pipeline.
In `CreateLeafPlates`, replace the comment line that starts `// Each row's material: the ash's, and the trees' leaves`
with the first listing, and directly below the closing brace of the `if` that logs
"No leaf plates: the trees' leaves are not loaded." and returns, with no blank line, add the second:

```cpp
    // Each row's material: the ash's, and the trees' leaves, found by name in the props' scene. Chapter 56 section 2: the
    // plates stay rigid, so the oak's and the pine's rows take their own copies of those two materials, as the ash's row has
    // its own: a copy has no wind in the table, so the per-material choice draws it with Chapter 39's shaders.
```

```cpp
    for (size_t row = 1; row < LEAF_ROWS.size(); ++row)
    {
        const scene::Material& tree     = world.GetMaterial(materials[row]);
        const uint32_t         treePicture = tree.opacityTexture.image;
        uint32_t               copy     = 0;
        if (auto result = m_sceneRenderer.AddMaterial(tree, copy); !result) { return result; }
        DescribeMaterial(copy, tree, treePicture != scene::NO_TEXTURE ? &world.GetTexture(treePicture) : nullptr, true);
        materials[row] = copy;
    }
```

**The flag.** `--plant-wind 0` starts Horizon with the switch off; any value but 0 or 1 stops the program. In
`Main.cpp`, add the first listing below `farForest` in `LaunchSettings`, the second below the `--far-forest` parse, the
third below the block that checks `--wind-fronts`, and the fourth below `horizonDemo.SetFarForestEnabled`:

```cpp
    int                               plantWind = 1;         // Chapter 56 section 2: --plant-wind 0|1; -1 a bad value
```

```cpp
        else if (key == "--plant-wind") { settings.plantWind = value == "0" ? 0 : value == "1" ? 1 : -1; }   // refused below
```

```cpp
    if (settings.plantWind < 0)
    {
        Log::error("--plant-wind must be 0 or 1.");
        return 1;
    }
```

```cpp
    horizonDemo.SetPlantWind(settings.plantWind == 1);   // Chapter 56 section 2: Plants in the wind, on at first
```

**`PlantWindTests.cpp`.** Stage 2 calls `plantTrunkLean`, `bendPlant` and `speciesWindHeight`. Replace the line that
starts `#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 2   // raised in each section of Chapter 56
```

**Answer to the transfer.** They would bend, since their materials now have wind. Their rows take copies of the two
materials, which have nothing in the wind table, so the per-material choice draws them with the base pipeline, as
`CreateLeafPlates` above does.

</details>

### Checkpoint

Add the section's bookmark: inside the oaks at 4 m, with grass and ferns in front and their shadows on the ground. In
`HorizonDemo.cpp`, replace the line `constexpr std::array<View, 1> WIND_VIEWS{ {` and the "Wind edge" line below it
with:

```cpp
// Section 2 adds "Wind wood": inside the oaks at 4 m, grass and ferns before them, their shadows on the ground.
constexpr std::array<View, 2> WIND_VIEWS{ {
    { "Wind edge", { 808.0f, -60.0f }, 2.5f, 180.0f, -2.0f },
    { "Wind wood", { -380.0f, 700.0f }, 4.0f, -35.0f, -3.0f },
```

Five files are new: generate again, then build and run the tests with section 1's checkpoint commands. The supplied test
ends `PASS: plant wind, stage 2 (47 checks)`. Stage 2 checks the bend: the roots do not move and every point keeps its
distance to the foot within 1e-5; each fade ends before the cut and the cut before 490 m; a tree and a clump of grass at
one foot get the same answer, the header against the test's own copy of the kernel's front frame, with no correction
and with a turned wind's; `plantTrunkLean` is 0 when calm, for a rigid plant and past the fade, never past the soft stop
for a raw lean far above 0.3 or for a negative one, and odd in the lean; and `speciesWindHeight` takes LOD0's height for
the stand-in and fails when LOD1's is 1 m off. The reference saw each check fail under a planted control. Then look:

```powershell
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4
```

- The grass rolls and the oaks behind it sway on the same rhythm: a front that crosses the grass reaches the trees. Each
  crown swings on an arc with its roots still; on the reference RTX 5090, in the command's default 1280 × 720 window,
  the crowns at Wind edge swung by 11 to 14 pixels. The branches and leaves move as one with the trunk, which section 3
  changes.

- `--horizon-view "Wind wood"` stands among the oaks, with the grass and the trees in front of you.
- Open **Wind**, then **Plants in the wind**, and untick its checkbox: the trees stand still and the grass rolls on. The
  log at start-up lists each species' material with its height, from `RegisterPlantWind`: the oak's materials at
  12.13 m and the pine's at 14.04 m, in plant space.

**Calm is the old picture.** With the switch off, Forest floor and Coast should equal the kept build's frames, byte for
byte. The kept build does not know `--plant-wind`; it warns that the option is unknown and ignores it, and its plants
stand still anyway:

```powershell
& ..\SandboxGame-before-56\SandboxGame.exe `
    --demo Horizon --horizon-view "Forest floor" --plant-wind 0 --sky off --msaa 4 `
    --width 1600 --height 900 --fixed-dt 0.016666667 --frames 120 --capture-output floor-before-56.bmp
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe `
    --demo Horizon --horizon-view "Forest floor" --plant-wind 0 --sky off --msaa 4 `
    --width 1600 --height 900 --fixed-dt 0.016666667 --frames 120 --capture-output floor-56-2.bmp
Get-FileHash floor-before-56.bmp, floor-56-2.bmp
```

On the reference RTX 5090 the two were equal, and so were the two captures at Coast with the same flags. The reference
recorded it with the finished chapter's code, not at this section's own state. That is what the switch promises,
measured; the chapter claims nothing about the switch on with no wind. Forest floor draws Chapter 39's understory and
Coast the coastal grass, both in the order the GPU's atomics hand out slots; if yours differ, judge them as Chapter 42,
section 1 judges the grass. The bend is not free: every vertex of a near tree works out its plant's answer, which is
the same for all of them.

Next in this chapter: [Part 2 — Every part attached, every view the same](EverythingBendsAttached.md), sections 3 to 5.
