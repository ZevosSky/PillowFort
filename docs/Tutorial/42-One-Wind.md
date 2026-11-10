# 42 — One Wind

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

**Goal:** one wind for the whole island. One owner holds where the wind
blows, how fast, and how hard and how wide its gusts are. Once a frame it
writes them into the per-frame block the island's shaders already read, and
the coast's grass, the one thing on the island that already moves in the
wind, follows it (section 1). Then the wind turns without its gusts jumping
(section 2). The planned Chapter 53, Rolling Wind, builds on this owner: it
makes the gusts roll across the island, and bends the trees, the understory
and the far forest to them, with their shadows and the clouds above.

*Ghost of Tsushima* works this way: a gust that flattens the grass in front
of you reaches the tree behind it a moment later. Bill Rockenbeck's
[GDC 2021 talk](https://www.gdcvault.com/play/1027350/Blowing-from-the-West-Simulating)
describes it, and [Chapter 52](52-Wind-Fields-And-Vorticles.md) took its local
sources from the same talk. Our island has no such wind yet. Chapter 27's
grass has a wind of its own, Chapter 28's clouds another, Chapter 30's sea a
third, and everything Chapters 37–40 planted stands still.

**Read after:** [Chapter 41](41-Grass-On-The-Island.md). Chapter 43 does not
need this chapter: the world wind starts as the coast's sea wind, so nothing
Chapter 43 measures changes.

**ROADMAP:** step 21+ — the `Horizon` demo grows.

**Module:** `pf::vulkan_graphics` gains `WorldWind`, a CPU-only owner beside
`CloudSettings`, and `FrameData` grows by two `vec4`s. The Grass and Horizon
demos each own one wind. `GrassSettings` keeps only how the blades respond to
it: gust lean and sway.

**Math:** section 1 turns an angle into a direction on the ground,
(sin a, −cos a), as Chapter 27, section 2 does. Section 2 sums a position from
each frame's travel, finds the chord between two directions, and takes the
short way round between two angles, in (−180, 180].

**Prerequisites:**

- [Chapter 41](41-Grass-On-The-Island.md), built and running: `CoastalArea`
  ([section 1](41-Grass-On-The-Island.md#1-one-frame-several-systems)), whose
  constructor, `Prepare` and `DrawControls` are in
  [CoastalArea.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/CoastalArea.cpp).
- [Chapter 27, section 2](27-Grass-Look.md#2-wind): the gust field and its
  blows-toward convention, `gustStrength`, the blade's lean along the wind,
  and the Wind view.
- [Chapter 26, section 3](26-Grass-GPU-Generation.md#3-the-generation-pass):
  `GrassParameters`, the uniform block the grass's compute passes read.
- [Chapter 28, section 10](28-Clouds.md#10-wind) (the clouds' wind) and
  [Chapter 28, section 13](28-Clouds.md#13-time-slicing-and-the-running-average)
  (a change of `CloudSettings` restarts the running average);
  [Chapter 30, section 5](30-A-Rougher-Sea.md#5-jonswap-a-spectrum-fitted-to-real-seas)
  (the sea's wind speed, measured 10 m above the water).
- [Chapter 10, section 7](10-Cameras-And-Depth.md#7-the-per-frame-buffer) (the
  per-frame buffer, written after the slot's fence wait) and
  [Chapter 8, section 8](08-Resources-And-Descriptors.md#8-one-layout-two-languages)
  (one header for C++ and GLSL, held together by `static_assert`s).
- [Chapter 9, section 9](09-Demo-Harness.md#9-what-runs-when) (`Update`, then
  `Record`, every frame) and
  [Chapter 9's optional transfer](09-Demo-Harness.md#control-workspace-transfer)
  (the `debug_panels::sliderFloat`, `checkbox` and `combo` wrappers).
- [Chapter 37, section 3](37-Objects-At-A-Distance.md#3-villages-and-landmarks):
  `LANDMARKS`, which section 2's **Guide toward** turns the wind toward.
- For section 1's checkpoint: atomic appends
  ([Chapter 21, section 5](21-GPU-Particles.md#5-drawing-the-particles);
  [Chapter 26, section 9](26-Grass-GPU-Generation.md#9-occlusion-culling-against-last-frames-depth)),
  the deferred path's 1x MSAA
  ([Chapter 22, section 9](22-Deferred-Shading.md#9-msaa-and-why-the-deferred-path-stays-at-one-sample))
  and `--capture-output`
  ([Chapter 49, section 2](49-Bloom-And-Color-Grading.md#2-capture-the-pixels-you-actually-display)).
- Mentioned but not required:
  - [Chapter 51](51-Atmosphere-And-Aerial-Perspective.md), whose `atmosphere`
    field section 1's offsets assume (section 1 says what to do without it);
  - [Chapter 50, section 4](50-Screen-Space-Ambient-Occlusion.md#4-filter-without-smearing-a-foreground-edge),
    whose `--ao` option section 1's checkpoint uses;
  - [Chapter 52, section 1](52-Wind-Fields-And-Vorticles.md#1-two-kinds-of-particle-two-owners):
    section 1 counts its `WindSources`, and section 2's pause works as its
    **Paused** does;
  - [Chapter 43, section 3](43-Waves-To-The-Shore.md#3-the-same-water-at-different-frame-rates),
    whose coastal **Paused** is why section 2's checkbox is called
    **Wind paused**;
  - [Chapter 47, section 4](47-Grass-Representation-Handover.md#4-animate-derived-data),
    whose `grassClumpLean`, the assembled reference's blade and clump lean,
    section 2 names.

## Where the code goes

| File | What sections 1 and 2 do there |
| --- | --- |
| [WorldWind.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/WorldWind.h), [WorldWind.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/WorldWind.cpp) | New: the owner, its settings and its state, and its panel; section 2: the summed offset, the turn rate, the pause and `blowsTowardDegrees` |
| [SharedShaderTypes.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Include/SharedShaderTypes.h) | `FrameData` appends `windDirection` and `windGust` |
| [FrameData.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/FrameData.h) | `applyWorldWind`, its last function |
| [GrassField.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Grass/GrassField.h), [GrassField.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Grass/GrassField.cpp) | `GrassSettings` gives up the wind, `GrassFrame` gains it, `PackParameters` copies it and treats a calm wind as no gusts; section 2: the offset goes with it |
| [GrassGenerateKernel.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassGenerateKernel.glsl), [GrassTypes.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassTypes.h) | Section 2: `gustStrength` reads the owner's offset from `windDirection.zw` |
| [GrassDemo.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Grass/GrassDemo.h), [GrassDemo.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Grass/GrassDemo.cpp) | The Grass demo's owner, its Wind group, `SetWind` and `SetWindToward` |
| [HorizonDemo.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/HorizonDemo.h), [HorizonDemo.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/HorizonDemo.cpp) | Horizon's owner, its Wind group, who reads it, and `SetWindToward`; section 2: **Guide toward** and `SetWindGuide` |
| [CoastalArea.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/CoastalArea.h), [CoastalArea.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/CoastalArea.cpp) | Reads the published wind; its own copy and its slider go |
| [Main.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/SandboxGame/Main.cpp) | Harness: `--wind-turn-at` and `--wind-turn-to`, a turn at a set frame; section 2: `--wind-guide` |
| [premake5.lua](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/premake5.lua) | The `TutorialWorldWindTests` project; section 2: `TutorialWorldWindTurnTests` |
| [WorldWindTests.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/WorldWindTests.cpp), [RendererConvergenceTests.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/RendererConvergenceTests.cpp) | The owner on the CPU; the frame block's size check moves to 448 |
| [WorldWindTurnTests.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/WorldWindTurnTests.cpp) | Section 2: the summed offset, the turn and the pause on the CPU, in a file of their own so that section 1's checks build without them |

`WorldWind.cpp` is a new file, so run `GenerateProjects.bat` again before you
build ([Chapter 1, section 3](01-Environment-And-Build.md#3-the-corrected-workspace)).
The acceptance tests are optional projects, which
`GenerateProjects.bat --tutorial-tests` generates; each checkpoint prints its
project.

## 1. Four winds in one frame

Start Horizon at the **Coast** viewpoint with the sky and its clouds on, and
watch for a minute:

```powershell
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe `
    --demo Horizon --horizon-view Coast --sky sun --clouds 1 --msaa 4
```

The coastal grass leans toward −X, and its gusts roll that way at 5.5 m/s.
To see them as blue lulls and pink gusts, set **Grass view** to Wind under
**Coastal area**. The sea's waves run toward −X too. The clouds drift toward
−Z and a little toward +X, at 10 m/s. The trees on the hills, the bushes and
ferns under them, and the far forest do not move at all.

**Keep this build before you change anything.** Section 1's checkpoint
compares every demo's frame with it. Copy its output folder somewhere outside
`Build/`. The executable finds its shaders and assets beside itself
([Chapter 6, section 1](06-Shaders-And-Pipelines.md#1-the-shader-build)), so
the copy runs on its own:

```powershell
Copy-Item -Recurse .\Build\Artifacts\Release\SandboxGame ..\SandboxGame-before-42
```

Nothing here is broken: each system does what its own chapter taught. There
are simply four winds, and nothing asks them to agree. Before you replace
them, count the right thing. A **reader** takes a wind: the blade shader, the
cloud march, the spectrum. An **owner** stores one: a settings struct, or code
that copies a value into one. Every owner is a place where a direction or a
speed can come out different from the others.

> **Jump:** from here on, a wind is one piece of state with many readers, not
> a setting each system keeps. The owner holds the wind itself. How each
> reader responds to it stays with the reader: the grass's lean and sway now,
> and in Chapter 53 a tree's bend and a leaf's flutter.

<a id="ch42-one-owner"></a>

### Attempt CH42-one-owner: one owner, published once

List every wind in Horizon: who stores it, in what units, and who reads it.
Then design the one structure they all read, give it one owner per demo, and
publish it once a frame. Predict first: which of the winds you listed can
follow the new owner now, and which cannot simply follow a wind that may
change every frame?

**Acceptance:** each of the Grass and Horizon demos owns one wind, constructed
by the demo like everything else it owns, with no global and no singleton.
Handing the owner a value that is not finite, a speed outside 0–60 m/s, a
strength outside 0–1 or a gust size under 0.5 m is refused, and the old wind
stays, settings and published state alike. A calm wind reaches the grass as no
gusts, never as a division by zero. The asserts hold at 448 bytes, with the
wind at offsets 416 and 432. With the wind at its defaults, every demo draws
the same frame as before at a fixed clock, except where atomics already make
the old build's runs differ (the checkpoint says how to judge those).

**Transfer:** `ShadowDepth.vert.glsl`, a vertex shader on set 0, could read
the wind by including `FrameBlock.glsl`, without a change to any layout.
`GrassGenerate.comp.glsl` binds that same set 0, yet it cannot. What would you
change so that it could read `FrameData` in place of its copy, and what else
would you have to check before changing it?

<details>
<summary>Hint 1: where the copies hide</summary>

A shader that reads a value owns nothing; code that copies one does. Look for
the copies. `CoastalArea`'s constructor is one: what does it copy into the
coastal grass's settings, when does it run, and does the field it writes mean
the same thing as the value it reads?

</details>

<details>
<summary>Hint 2: what the owner holds</summary>

Separate the wind (direction, mean speed, gust strength, gust size) from each
reader's response (lean, sway). Use the units the sea and the clouds already
use: degrees the wind blows toward, metres per second. Check a whole new
setting before storing any of it, so that a refused one changes nothing.
Append to `FrameData`; never insert.

</details>

<details>
<summary>Hint 3: where each piece goes</summary>

Put `WorldWind` beside `CloudSettings` in `VulkanGraphics`, and
`applyWorldWind` at the end of `FrameData.h`. Each demo's `Update` hands the
panel's settings to the owner and advances it; `Record` writes it into
`FrameData`. The grass's generation pass is compute and reads its own uniform
block, `GrassParameters`. `CoastalArea::Prepare` is already handed Horizon's
`FrameData`, so it reads the wind from there and owns none.

</details>

<details>
<summary>Worked solution: the owner, its fields and its readers</summary>

**The count.** Five owners, four of them in Horizon's frame:

| Owner | What it stores | Units | From |
| --- | --- | --- | --- |
| `GrassSettings` | `windAngle`, `windSpeed`, `windStrength`, `gustScale` | degrees toward; m/s the gusts travel; 0–1; metres across a gust | Chapter 27, section 2 |
| `CoastalArea`'s constructor | copies the sea's `windAzimuth` and `windSpeed` into its own `GrassSettings`, once | degrees toward; m/s | Chapter 41's `CoastalArea.cpp` |
| `CloudSettings` | `windAngle`, `windSpeed` | degrees toward; m/s | Chapter 28, section 10 |
| `SeaSettings` | `windAzimuth`, `windSpeed`, and the swell's own direction | degrees toward; m/s at 10 m above the water | Chapter 30, section 5 |
| `WindSources`, if you took Chapter 52 | local sources only; no wind of the world | m/s | Chapter 52, section 1 |

The `CoastalArea` row is worse than a second copy. It copies once, so a sea
wind changed later never reaches the grass. And it puts the sea's
`windSpeed`, the mean wind 10 m above the water, into the grass's
`windSpeed`, how fast the gusts travel: two quantities that share a unit.
This chapter joins them on purpose: **the gusts travel downwind at the mean
wind speed**. Real gusts move at about that speed, and the choice keeps the
coast's grass as it is, since its gusts already travel at the sea's 5.5 m/s.

**Answer to the prediction.** Only the grass can follow the owner now, in the
Grass demo and on the coast. The sea and the clouds keep their own winds, and
Horizon's panel says so: the sea's wind rebuilds its spectrum, and the
clouds' wind restarts their running average, so as they stand, neither can
follow a wind that changes every frame.

**What the owner holds.** The direction, the speed, and the gusts' strength
and size describe the air. How far a gust leans a blade, and how a blade
sways, are how the grass responds to it; a tree will respond with a different
lean and a slower sway. So the owner keeps four numbers, in units stated
once:

| What | Unit | Convention |
| --- | --- | --- |
| Direction | degrees it **blows toward**, turning from −Z toward +X | the unit vector (sin a, −cos a) in world x and z: Chapter 27, section 2's, which the clouds and the sea already use |
| Mean speed | metres per second | the sea's own: the wind 10 m above the ground |
| Gust strength | 0 to 1 | how much of a full gust the strongest place gets |
| Gust size | metres | across one gust |

**Where to publish it.** The shaders that draw the island's colour already
include `FrameBlock.glsl`: `FrameData` at set 0, binding 0, written once a
frame after the slot's fence wait. A wind there costs nothing to bind and
reaches all of them, but not the grass's generation pass, which is compute.
That pass binds the same set 0 for the shadow data at binding 3, yet in
`SceneRenderer`'s set 0
([Chapter 11, section 11](11-Meshes.md#11-scenerenderer-draws-meshes))
binding 0 names only the vertex and fragment stages. The pass already reads a
wind from its own uniform block, `GrassParameters`, so it gets a copy there,
filled from the same state, and the set every demo shares stays as it is.

The fields go at the end of `FrameData`, so no older shader reads a moved
offset. A value-initialized frame (`makeFrameData` builds one) has them at
zero, and zero is calm, so a demo that never mentions the wind draws as it
did. Calm has one trap: its gust size is 0, and every gust field divides by
the gust size. So the contract has a rule for readers: **a gust size below
`WorldWind::MIN_GUST_SIZE`, half a metre, means calm, and a reader that sees
one uses no gusts instead of dividing by it.** `Configure` refuses such a
size, so only a wind nobody configured, all zero, has one.

**This is `WorldWind.h`.** The settings are what a panel edits. The state is
what a frame publishes, laid out like `FrameData`'s two new vectors, so that
publishing it is two copies. `Configure` returns an `InitializationResult`,
because a refused change must leave the wind as it was. The class holds no
GPU object, so it needs no `Initialize` or `Shutdown`, and a demo holds it by
value, as it holds its camera.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  One wind for a whole demo: its settings, its owner and its panel (Chapter 42)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/VulkanGraphics/WorldWind.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"

#include <glm/glm.hpp>

namespace pf::vulkan_graphics {

// Chapter 42 section 1: the wind, in the units every reader shares. How a reader responds to it (a
// blade's lean, its sway) belongs to the reader, not to the wind. Zero speed and strength are calm.
struct WorldWindSettings
{
    float towardDegrees = 0.0f;    // where it blows to, turning from -Z toward +X (Chapter 27 section 2)
    float speed         = 0.0f;    // mean speed, metres per second
    float strength      = 0.0f;    // 0..1: how hard the gusts are
    float gustSize      = 15.0f;   // metres across one gust
};

// What one frame publishes: FrameData's windDirection and windGust, field for field. All zero is calm,
// and a reader treats a gust size below WorldWind::MIN_GUST_SIZE as calm instead of dividing by it.
struct WorldWindState
{
    glm::vec4 direction{ 0.0f };   // xy: the unit vector it blows along, world xz; zw: the gust offset, metres
    glm::vec4 gust{ 0.0f };        // x strength, y gust size in metres, z mean speed in m/s; w unused
};

// One per demo, constructed by the demo like everything else it owns. CPU only: it holds no GPU object.
class WorldWind
{
public:
    static constexpr float MAX_SPEED     = 60.0f;   // metres per second, past any storm the demos draw
    static constexpr float MIN_GUST_SIZE = 0.5f;    // metres; the slider starts at 2, and a size near 0 overflows the noise

    InitializationResult     Configure(const WorldWindSettings& settings);   // a bad value keeps the old wind
    void                     Advance(float deltaSeconds);                     // once a frame, from Update
    const WorldWindSettings& Settings() const { return m_settings; }
    const WorldWindState&    State() const { return m_state; }

private:
    void Publish();

    WorldWindSettings m_settings;
    WorldWindState    m_state;
    double            m_seconds = 0.0;   // how long the wind has blown
};

// The wind's four sliders, the same in every demo that owns a WorldWind. True if one changed.
bool drawWorldWindPanel(WorldWindSettings& settings);

} // namespace pf::vulkan_graphics
```

**This is `WorldWind.cpp`.** `Configure` checks every value before it keeps
any, because a NaN would spread to every blade. The gust size is a divisor,
so it must be at least `MIN_GUST_SIZE`, a quarter of the slider's smallest: a
typed `1e-38` would overflow a position to infinity, and the noise would turn
that into NaN. `Advance` ignores a frame time that is negative or not finite.
`Publish` turns the angle into a direction with Chapter 27's float operations
(`glm::radians`, `std::sin`, `-std::cos`), so the grass gets the same bits as
before. The gust offset is Chapter 27's formula for now: velocity times how
long the wind has blown, in a `double`. Nothing reads it yet; section 2 moves
the grass onto it, and shows why the formula has to change.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  One wind for a whole demo: its settings, its owner and its panel (Chapter 42)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/VulkanGraphics/WorldWind.cpp
#include "PillowFort/VulkanGraphics/WorldWind.h"

#include "PillowFort/DebugPanels/DemoPanel.h"

#include <cmath>
#include <format>

namespace pf::vulkan_graphics {

InitializationResult WorldWind::Configure(const WorldWindSettings& settings)
{
    // Every value finite, and each in the range its readers can use: the gust size is a divisor.
    const bool finite = std::isfinite(settings.towardDegrees) && std::isfinite(settings.speed) &&
                        std::isfinite(settings.strength) && std::isfinite(settings.gustSize);
    if (!finite || settings.speed < 0.0f || settings.speed > MAX_SPEED || settings.strength < 0.0f ||
        settings.strength > 1.0f || settings.gustSize < MIN_GUST_SIZE)
    {
        return InitializationResult::failure(std::format("World wind unchanged: values must be finite, speed 0-{} m/s, strength 0-1, gust size at least {} m.", MAX_SPEED, MIN_GUST_SIZE));
    }
    m_settings = settings;
    Publish();
    return InitializationResult::success();
}

void WorldWind::Advance(float deltaSeconds)
{
    if (!std::isfinite(deltaSeconds) || deltaSeconds < 0.0f) { return; }   // a bad frame time changes nothing
    m_seconds += deltaSeconds;
    Publish();
}

// The gusts move as Chapter 27's grass already moves them: the offset is the wind's velocity times
// how long it has blown.
void WorldWind::Publish()
{
    const float     toward = glm::radians(m_settings.towardDegrees);
    const glm::vec2 along{ std::sin(toward), -std::cos(toward) };
    const glm::vec2 offset = glm::vec2(glm::dvec2(along) * (static_cast<double>(m_settings.speed) * m_seconds));
    m_state.direction = glm::vec4(along, offset);
    m_state.gust      = glm::vec4(m_settings.strength, m_settings.gustSize, m_settings.speed, 0.0f);
}

// No slider clamps a typed value: Configure turns a bad one away, and the demo puts the old one back.
bool drawWorldWindPanel(WorldWindSettings& settings)
{
    bool changed = false;
    changed |= debug_panels::sliderFloat("Blows toward", &settings.towardDegrees, -180.0f, 180.0f, "%.0f deg");
    changed |= debug_panels::sliderFloat("Mean speed (m/s)", &settings.speed, 0.0f, 30.0f);
    changed |= debug_panels::sliderFloat("Gust strength", &settings.strength, 0.0f, 1.0f);
    changed |= debug_panels::sliderFloat("Gust size (m)", &settings.gustSize, 2.0f, 60.0f);
    return changed;
}

} // namespace pf::vulkan_graphics
```

Chapter 27 clamped its strength and gust-size sliders
(`ImGuiSliderFlags_AlwaysClamp`), because nothing stood between a typed value
and the shader. Now the owner does: a typed strength above 1, or a gust size
under half a metre, is refused, and the demo puts the last good value back.

**This is `FrameData`'s end**, in `Shaders/Include/SharedShaderTypes.h`. Two
`vec4`s, so std140 needs no padding, appended after Chapter 51's `atmosphere`,
and three asserts changed or added:

```cpp
    vec4  atmosphere;       /* 400: enabled, solar exposure, aerial max metres, observer altitude metres */
    /* Chapter 42: the world wind, written once a frame by the demo's one owner. All zero is calm. */
    vec4  windDirection;    /* 416  xy: unit vector the wind blows along, world xz; zw: gust offset, metres */
    vec4  windGust;         /* 432  x strength 0..1, y gust size metres, z mean speed m/s; w unused */
};

#ifdef __cplusplus
    static_assert(sizeof(FrameData) == 448, "FrameData layout drifted.");
```

```cpp
    static_assert(offsetof(FrameData, atmosphere) == 400, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, windDirection) == 416, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, windGust) == 432, "FrameData alignment drifted.");
#endif
```

Without Chapter 51, your block ends at `padding10`, at 400 bytes, and you have
no `applyAtmosphereSettings`. Type Chapter 51's `atmosphere` line and its
`offsetof` assert from the listings above first. Nothing of yours reads that
field, but it makes your offsets match these and the acceptance tests':
`WorldWindTests.cpp`'s two `static_assert`s check 448, 416 and 432, and
`RendererConvergenceTests.cpp` checks 448. Leave out the
`applyAtmosphereSettings` line in the two listings below that write the frame.
[The engine you built](../VulkanTutorial.md#framedata-whole) shows the whole
block.

Move the size check in `Tests/TutorialHarness/RendererConvergenceTests.cpp`
to 448, and check while you are there that a frame nobody gives a wind is
calm. If your tree has no such file, because you ran Renderer convergence's
checks from a reference checkout, copy the
[reference's](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/RendererConvergenceTests.cpp)
unchanged to that path instead: it already holds both checks below.

```cpp
            check(sizeof(frame) == 448 && frame.haze == glm::vec4(0.0f) && frame.hazeSky == 0,
                  "FAIL: shared haze ABI or disabled defaults");
            // Chapter 42 section 1: only applyWorldWind writes a wind; a frame nobody gives one is calm.
            check(frame.windDirection == glm::vec4(0.0f) && frame.windGust == glm::vec4(0.0f),
                  "FAIL: shared wind calm defaults");
```

**This is `applyWorldWind`**, the last function in `FrameData.h`, with
`#include "PillowFort/VulkanGraphics/WorldWind.h"` among the header's includes
(after `SkySettings.h`'s, if you took Chapter 51):

```cpp
// Chapter 42 section 1: the demo's one wind, the same for every reader of set 0, binding 0.
inline void applyWorldWind(shared::FrameData& frame, const WorldWindState& wind)
{
    frame.windDirection = wind.direction;
    frame.windGust      = wind.gust;
}
```

**The grass gives up its wind.** In `GrassField.h`, `GrassSettings` loses
`windAngle`, `windSpeed`, `windStrength` and `gustScale`. One comment line
takes their place; the three lines after them, how a blade responds, stay.
`GrassFrame`, what a host hands the field each frame, gains the host's wind.
`GrassField.h` includes `"PillowFort/VulkanGraphics/WorldWind.h"` beside
`SceneRenderer.h`.

```cpp
    // Chapter 27 section 2: how a blade responds to the wind. The wind itself is the demo's WorldWind (Chapter 42 section 1).
    float     gustLean          = 0.35f;    // how far a full gust leans a blade, in blade heights
```

```cpp
    float time = 0.0f;
    bool occlusionEnabled = false;
    vulkan_graphics::WorldWindState wind;   // Chapter 42 section 1: the host's one wind, as it publishes it
};
```

`PackParameters` reads the published wind, so it follows the rule for calm.
Its `windAngle` line at the top goes, and in its place it asks whether the
frame has gusts at all. A `GrassFrame` built without `.wind`, or filled before
the owner's first `Configure`, is calm, all zero:

```cpp
GrassParameters GrassField::PackParameters(const GrassSettings& settings, const GrassFrame& frame) const
{
    // Chapter 42 section 1: gustStrength divides by the gust size, and calm (all zero) has none.
    const bool gusts = frame.wind.gust.y >= WorldWind::MIN_GUST_SIZE;
```

Then it copies the wind into `GrassParameters`, whose layout stays. Calm
hands the shader no strength and a size it can divide by, so `gustStrength`
returns 0 everywhere; a real wind passes through bit for bit. The offset
stays out of `windDirection.zw` for now, because nothing in the grass reads
it yet:

```cpp
        // Chapter 42 section 1: the compute pass cannot read FrameData, so the wind comes in a copy.
        .windDirection   = { frame.wind.direction.x, frame.wind.direction.y, 0.0f, 0.0f },
        .interactor      = settings.interactor ? glm::vec4(frame.interactorPosition, settings.interactorRadius) : glm::vec4(0.0f),
        .windSpeed       = frame.wind.gust.z,
        .windStrength    = gusts ? frame.wind.gust.x : 0.0f,
        .gustScale       = gusts ? frame.wind.gust.y : WorldWind::MIN_GUST_SIZE,   // calm: no gusts, and nothing divides by 0
```

**The Grass demo owns its wind.** Its defaults are Chapter 27's, so the field
looks as it did. The panel edits `m_windSettings`; the owner keeps the last
good copy. In `GrassDemo.h`, below `m_settings`:

```cpp
    // Chapter 42 section 1: the demo's one wind, at Chapter 27's defaults. The panel edits the settings;
    // Update hands them to the owner, which keeps the last good ones.
    vulkan_graphics::WorldWindSettings m_windSettings{ .towardDegrees = 20.0f, .speed = 3.0f,
                                                       .strength = 0.6f, .gustSize = 15.0f };
    vulkan_graphics::WorldWind         m_wind;
```

`SetWind`, among the demo's public setters, wrote the `windStrength` that
`GrassSettings` no longer has; `--grass-wind` calls it. It now sets the world
wind's gust strength, which `Update` hands to the owner like a panel value:

```cpp
    void SetWind(float strength) { m_windSettings.strength = strength; }   // Chapter 42 section 1: the world wind's gust strength
```

`drawGrassPanel` takes the wind's settings after the grass's:

```cpp
static void drawGrassPanel(GrassSettings& settings, WorldWindSettings& wind, const GrassStatistics& statistics,
                           uint32_t capacity0, uint32_t capacity1)
```

and its Wind group becomes the wind's four sliders, then the blades' three:

```cpp
        if (ImGui::CollapsingHeader("Wind"))
        {
            drawWorldWindPanel(wind);   // Chapter 42 section 1: the wind; below it, how the blades respond
            pf::debug_panels::sliderFloat("Gust lean", &settings.gustLean, 0.0f, 1.0f, "%.3f", ImGuiSliderFlags_AlwaysClamp);
            pf::debug_panels::sliderFloat("Sway (Hz)", &settings.swayFrequency, 0.0f, 3.0f);
            pf::debug_panels::sliderFloat("Sway amount", &settings.swayAmount, 0.0f, 0.3f, "%.3f", ImGuiSliderFlags_AlwaysClamp);
        }
```

`Update` ends by handing the panel's wind to the owner and moving it on a
frame. A refused value puts the owner's settings back into the panel's copy,
and the log says why:

```cpp
    drawGrassPanel(m_settings, m_windSettings, m_field.Statistics(), LOD0_CAPACITY, LOD1_CAPACITY);

    // Chapter 42 section 1: the owner takes the panel's wind only if it is valid, then moves on a frame.
    if (auto result = m_wind.Configure(m_windSettings); !result)
    {
        Log::warning(result.message());
        m_windSettings = m_wind.Settings();
    }
    m_wind.Advance(input.deltaSeconds);
}
```

`WriteFrameBuffers` publishes the wind into `FrameData` just before
`m_sceneRenderer.WriteFrameData`, and hands the same state to the grass, as
the last field of its `GrassFrame`:

```cpp
    vulkan_graphics::applyAtmosphereSettings(frameData, sky);
    vulkan_graphics::applyWorldWind(frameData, m_wind.State());   // Chapter 42 section 1
    if (auto result = m_sceneRenderer.WriteFrameData(frameIndex, frameData); !result) { return result; }
```

```cpp
        .time = m_time,
        .occlusionEnabled = m_settings.occlusionCulling && !m_settings.freezeCulling,
        .wind = m_wind.State(),
    };
```

**Horizon owns its wind, and the coast reads it.** Horizon's wind starts as
the coast's: the direction and speed from `CoastalArea::DefaultSeaSettings()`,
and the strength and gust size `GrassSettings` held. In `HorizonDemo.h`,
below `m_deltaTime`, with `#include "PillowFort/VulkanGraphics/WorldWind.h"`
after `Sky.h`'s include:

```cpp
    // Chapter 42 section 1: the demo's one wind, seeded with the coast's sea wind (toward -90 degrees at
    // 5.5 m/s) so that the coast looks as it did. The panel edits the settings; Update hands them to the
    // owner. The clouds' own wind is kept as Record last saw it, for the panel.
    vulkan_graphics::WorldWindSettings m_windSettings{ .towardDegrees = CoastalArea::DefaultSeaSettings().windAzimuth,
                                                       .speed = CoastalArea::DefaultSeaSettings().windSpeed,
                                                       .strength = 0.6f, .gustSize = 15.0f };
    vulkan_graphics::WorldWind         m_wind;
    glm::vec2                          m_cloudWind{ 0.0f };   // degrees toward, m/s
```

and, after `DrawPlantControls`'s declaration:

```cpp
    void                 DrawWindControls();                                   // Chapter 42: section 1
```

`HorizonDemo::Update` ends as the Grass demo's does:

```cpp
    // Chapter 42 section 1: the owner takes the panel's wind only if it is valid, then moves on a frame.
    if (auto result = m_wind.Configure(m_windSettings); !result)
    {
        Log::warning(result.message());
        m_windSettings = m_wind.Settings();
    }
    m_wind.Advance(input.deltaSeconds);
}
```

`Record` writes the wind into the one `FrameData` it already builds, after the
`hazeSky` line and just before `m_sceneRenderer.WriteFrameData`, and notes the
clouds' wind for the panel:

```cpp
    vulkan_graphics::applyAtmosphereSettings(frameData, frame.sky);
    vulkan_graphics::applyWorldWind(frameData, m_wind.State());   // Chapter 42 section 1: once, for every reader
    m_cloudWind = { frame.sky.clouds.windAngle, frame.sky.clouds.windSpeed };
```

The Wind group goes after the plants' controls in `DrawPanel`
(`DrawWindControls();      // Chapter 42 section 1`, below
`DrawPlantControls();`). Below the four sliders it says who reads the wind:
two of the island's winds are still not this one, and a panel that hid that
would send you looking for a bug:

```cpp
// Chapter 42 section 1: the demo's one wind, and who reads it. So far only the coast's grass does.
void HorizonDemo::DrawWindControls()
{
    if (!ImGui::CollapsingHeader("Wind")) { return; }
    vulkan_graphics::drawWorldWindPanel(m_windSettings);
    const glm::vec2 sea = m_coastal.SeaWind();
    ImGui::SeparatorText("Who reads it");
    ImGui::TextWrapped("Coastal grass: this wind");
    ImGui::TextWrapped("Sea: its spectrum's own, toward %.0f deg at %.1f m/s", sea.x, sea.y);
    ImGui::TextWrapped("Clouds: their own, toward %.0f deg at %.1f m/s", m_cloudWind.x, m_cloudWind.y);
    ImGui::TextWrapped("Trees, understory, far forest: nothing yet");
}
```

**`CoastalArea` owns no wind.** Delete the two constructor lines that set
`m_grassSettings.windAngle` and `m_grassSettings.windSpeed` from
`DefaultSeaSettings()`, and the **Wind strength** slider in `DrawControls`;
the Wind group does its job now. `Prepare`, handed Horizon's `FrameData`,
takes the wind from there, as the last field of the coastal grass's frame:

```cpp
            .time = data.time,
            .occlusionEnabled = false,
            .wind = { data.windDirection, data.windGust },   // Chapter 42 section 1: Horizon's wind, as published
        };
```

and `CoastalArea.h` lets the panel read the sea's wind, after `SetSeaEnabled`:

```cpp
    // Chapter 42 section 1: the sea keeps its spectrum's wind, degrees toward and m/s, for Horizon's panel.
    glm::vec2 SeaWind() const { return { m_sea.Settings().windAzimuth, m_sea.Settings().windSpeed }; }
```

**Why the frame does not change.** No shader reads `windDirection` or
`windGust` yet, and the grass is handed the same direction, speed, strength
and size, computed by the same float operations. `TutorialWorldWindTests`
checks that bit for bit.

**Answer to the transfer.** Add `VK_SHADER_STAGE_COMPUTE_BIT` to binding 0's
`stageFlags` in `SceneRenderer::CreateFrameResources`, and include
`FrameBlock.glsl` in the generation kernel. Check two things first. Every
demo that draws with `SceneRenderer` shares that layout, but a stage flag only
allows a read, so nothing else changes. And the block must be written before
the pass reads it. It is: the host writes it after the fence wait, before the
frame is submitted, and a submission sees the host writes made before it.

</details>

### A turn at a set frame

Section 2 starts by turning the wind at an exact frame, which a hand cannot
do. Two harness options do it: at the frame `--wind-turn-at` names, they set
**Blows toward** to `--wind-turn-to`, as a drag would. Add them now, so that
the build you keep at the end of this section has them. `GrassDemo.h` (after
`SetWind`) and `HorizonDemo.h` (after `RequestImpostorRebake`) gain the same
public setter:

```cpp
    void SetWindToward(float degrees) { m_windSettings.towardDegrees = degrees; }   // Chapter 42 section 1: --wind-turn-at
```

In `Main.cpp`, `LaunchSettings` gains three fields at its end:

```cpp
    int                               windTurnAt = 0;        // Chapter 42: a frame number, 0 is never
    float                             windTurnTo = 0.0f;     // degrees the wind blows toward from that frame
    bool                              windValuesValid = true;
```

`parseSettings` gains a branch just before the `--far-forest` one
(Chapter 40's):

```cpp
        else if (key == "--wind-turn-at" || key == "--wind-turn-to")
        {
            const auto [end, error] = key == "--wind-turn-at"
                ? std::from_chars(value.data(), value.data() + value.size(), settings.windTurnAt)
                : std::from_chars(value.data(), value.data() + value.size(), settings.windTurnTo);
            settings.windValuesValid &= error == std::errc{} && end == value.data() + value.size();
        }
```

`main` refuses a bad value after parsing, after its check of the grass
options:

```cpp
    if (!settings.windValuesValid || settings.windTurnAt < 0 || !std::isfinite(settings.windTurnTo)
        || settings.windTurnTo < -360.0f || settings.windTurnTo > 360.0f)
    {
        Log::error("--wind-turn-at must be a frame number (0: never); --wind-turn-to is degrees, -360 to 360.");
        return 1;
    }
```

and the frame loop turns the wind in a hook of its own. It goes just after
the `--resize-at` hook, with the loop's other frame-numbered hooks, which all
follow Chapter 7's `frameCount++`:

```cpp
        if (settings.windTurnAt > 0 && frameCount == static_cast<uint64_t>(settings.windTurnAt))
        {
            grassDemo.SetWindToward(settings.windTurnTo);     // Chapter 42: a scripted turn of the world wind,
            horizonDemo.SetWindToward(settings.windTurnTo);   // to compare the frames across it
        }
```

[SandboxGame's command line](../VulkanTutorial.md#sandboxgames-command-line)
lists both options.

### Checkpoint

Build, then run Horizon at **Coast** with the sky and clouds on, and open
**Wind** in the Horizon panel. It reads −90 deg, 5.5 m/s, 0.6 and 15 m.
**Who reads it** lists the coastal grass on this wind, the sea (toward −90 deg
at 5.5 m/s) and the clouds (toward 30 deg at 10.0 m/s) on their own, and the
trees, understory and far forest on nothing yet:

![Horizon's panel at the Coast viewpoint with the Wind group open: Blows toward -90 deg, Mean speed 5.500, Gust strength 0.600 and Gust size 15.000, and under Who reads it four lines: Coastal grass: this wind; Sea: its spectrum's own, toward -90 deg at 5.5 m/s; Clouds: their own, toward 30 deg at 10.0 m/s; Trees, understory, far forest: nothing yet.](images/42-wind-group.png)

The frame itself must not change. Capture it at a fixed clock with the copy
of the old build and with the new one. `--fixed-dt` steps the clock by
exactly that much each frame, `--frames` stops after 120, and
`--capture-output` saves what the last frame wrote, before the UI:

```powershell
& ..\SandboxGame-before-42\SandboxGame.exe `
    --demo Horizon --horizon-view Coast --sky sun --clouds 1 --msaa 4 `
    --width 1600 --height 900 --fixed-dt 0.016666667 --frames 120 --capture-output coast-before.bmp
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe `
    --demo Horizon --horizon-view Coast --sky sun --clouds 1 --msaa 4 `
    --width 1600 --height 900 --fixed-dt 0.016666667 --frames 120 --capture-output coast-after.bmp
Get-FileHash coast-before.bmp, coast-after.bmp
```

The Coast frame holds the coastal grass, judged as below if the hashes
differ; on the reference RTX 5090 they matched. Every other demo that
includes `FrameBlock.glsl` must match exactly, apart from the ones that draw
in atomic order, below: Cubes (with and without `--sky sun`), Meshes, Scene
graph, Ocean, and the USD viewer on both its paths. The deferred path's
compute lighting pass reads the block through a layout of its own. It draws
deferred only at 1x MSAA, so give it
`--demo "USD viewer" --render-path deferred --msaa 1`, and check that the log
does not say it draws forward. If you took Chapter 50, add `--ao 1`, whose
two compute passes read the block too.

Three things vary from run to run: the Particles demo, the Sea's spray, and
the grass, in the Grass demo and in Horizon. Each is drawn in the order the
GPU's atomics hand out slots (Chapter 21, section 5; Chapter 26, section 9),
so two runs of the *old* build already differ. Capture each three or more
times with each build, and compare each new capture with the nearest old one.
For the grass, use the Grass demo's Wind view, which shows the gust field
itself:

```powershell
foreach ($n in 1..3)
{
    & ..\SandboxGame-before-42\SandboxGame.exe --demo Grass --grass-debug-view wind --msaa 4 `
        --width 1600 --height 900 --fixed-dt 0.016666667 --frames 120 --capture-output "grass-before-$n.bmp"
    & ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe --demo Grass --grass-debug-view wind --msaa 4 `
        --width 1600 --height 900 --fixed-dt 0.016666667 --frames 120 --capture-output "grass-after-$n.bmp"
}
```

`--demo Particles` and `--demo Sea`, without `--grass-debug-view`, work the
same way. `Tests\TutorialHarness\ImageArtifacts.ps1` holds a small image
comparison. It is supplied, not typed: if your tree lacks it, copy the
[reference's](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/ImageArtifacts.ps1) unchanged to
that path. `ChangedPixels` counts the pixels that differ, and the last
argument, 1, compares every pixel:

```powershell
. .\Tests\TutorialHarness\ImageArtifacts.ps1
[TutorialImageDiff]::Compare("$PWD\grass-before-1.bmp", "$PWD\grass-after-1.bmp", 1).ChangedPixels
```

The new captures should be as close to the old ones as the old ones are to
each other: a few pixels for the grass, hundreds to tens of thousands for
Particles and the spray. A moved offset or a broken gust field changes a large
part of the frame. On one RTX 5090 at these settings, eight old runs of the
Grass demo were 0–2 pixels apart in either view. The new runs were 0–2 pixels
from the nearest old one in the Wind view, and 0–3 in the shaded view
(`REFERENCE.md` keeps the full readings).

The Grass demo's **Wind** now shows the four wind sliders, then
**Gust lean**, **Sway (Hz)** and **Sway amount**. Drag **Blows toward** in
Horizon: the coastal grass turns its lean at once, and its whole pattern of
gusts jumps somewhere new in the same frame. Section 2 fixes that jump.

The first acceptance test's source,
[`WorldWindTests.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/WorldWindTests.cpp), is
supplied too: if your tree lacks it, copy it unchanged to
`Tests/TutorialHarness/WorldWindTests.cpp`. It checks only this section's
owner, so it builds before section 2. Add its project to `premake5.lua`,
inside the `if _OPTIONS["tutorial-tests"] then` block (the
[scene-documents reference](SceneDocumentsReference.md#register-only-completed-fixture-sources)
adds the option and the block, if your file has neither).

```lua
    project "TutorialWorldWindTests"
        kind "ConsoleApp"
        apply_common_cpp_settings()
        files { "Tests/TutorialHarness/WorldWindTests.cpp" }
        includedirs { "Vendor/GLFW/include" }   -- GrassField.h reaches GlfwWindow.h through Demo.h
        links { "PillowFortEngine", "GLFW", "ImGui", "TinyUSDZ" }
```

If your tree already had `RendererConvergenceTests.cpp`, it has the
`TutorialRendererConvergenceTests` project too, from
[Renderer convergence](RendererConvergence.md). If you copied the file above,
add the reference's project after this one. It links no engine library, so it
compiles [Chapter 12](12-Scene-Graph.md)'s `Bounds.cpp` beside the test, for
the box and frustum functions the test and `Visibility.h` call:

```lua
    project "TutorialRendererConvergenceTests"
        kind "ConsoleApp"
        apply_common_cpp_settings()
        files { "Tests/TutorialHarness/RendererConvergenceTests.cpp", "Source/PillowFort/Scene/Bounds.cpp" }
```

Generate them, build them, and run each from the repository root, in
PowerShell. Neither opens a window, and a test that finds a broken contract
says which and exits with a nonzero code:

```powershell
.\GenerateProjects.bat --tutorial-tests
if ($LASTEXITCODE -ne 0) { throw 'Project generation failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:TutorialWorldWindTests,TutorialRendererConvergenceTests
if ($LASTEXITCODE -ne 0) { throw 'The acceptance test build failed.' }
foreach ($target in 'TutorialWorldWindTests', 'TutorialRendererConvergenceTests')
{
    & ".\Build\Artifacts\Debug\$target\$target.exe"
    if ($LASTEXITCODE -ne 0) { throw "$target failed." }
}
```

`TutorialWorldWindTests` prints one `PASS` line with its count of checks. It
checks:

- the calm wind's zeros;
- the blows-toward convention at 0, 90, −90 and 180 degrees, and the
  direction bit for bit against Chapter 27's;
- that every refused setting keeps the old wind (a gust size just under half
  a metre among them);
- the offset and the frame-time guard;
- the copies into `FrameData` and `GrassParameters`;
- that a calm frame reaches the grass as no gusts, with a gust size it can
  divide by.

`TutorialRendererConvergenceTests` passes with its size check at 448.

**Keep this build too.** Section 2's checkpoint runs it beside the next one:

```powershell
Copy-Item -Recurse .\Build\Artifacts\Release\SandboxGame ..\SandboxGame-section1
```

## 2. A wind that turns without jumping

Start the Grass demo in its Wind view and leave it running for two minutes:

```powershell
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe `
    --demo Grass --grass-debug-view wind --msaa 4
```

Then open **Wind** in the Grass panel and drag **Blows toward** from 20 to 110
degrees. While you drag, the field scrambles: every blue lull and pink gust
is replaced by another, and the blades swing round with the slider. Let go,
and the field drifts on as a pattern you have never seen. Now turn it early,
with section 1's scripted turn at frame 60, about a second in at 60 frames a
second:

```powershell
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe `
    --demo Grass --grass-debug-view wind --msaa 4 --wind-turn-at 60 --wind-turn-to 110
```

This time the blotches shift a little and keep their shapes; only the blades
swing. The longer the program has run, the further a turn throws the gusts.

**Why it jumps.** Chapter 27's `gustStrength` samples its noise at
`xz - drift`, with `drift = windDirection * windSpeed * time`: the pattern has
travelled along the current direction, at the current speed, for the whole
run. Turn the direction from d₁ to d₂ at time t, and every point on the ground
reads the noise (d₁ − d₂)·v·t away from where it read it a frame before. Both
directions are unit vectors, so |d₁ − d₂| is the chord between them,
2 sin(Δθ/2), and the pattern jumps

  2 · v · t · sin(Δθ / 2).

After 120 s at the Grass demo's 3 m/s, a 90-degree turn moves the pattern
2 × 3 × 120 × sin 45° = 509 m, more than thirty 15 m gusts: what you see
afterwards is unrelated to what you saw before. One second in, the same turn
moves it 4.2 m, under a third of a gust, so the blotches kept their shapes. A
drag only spreads the jump out: two minutes in, one degree a frame still
moves the pattern 6 m every frame.

> **Jump:** "velocity times time" is a position only while the velocity never
> changes, and a wind that turns is a velocity that changes. Keep two things
> apart from here on: *where* the gusts are, and *where they are going now*,
> the direction and speed the owner publishes this frame.

<a id="ch42-a-turn-is-not-a-jump"></a>

### Attempt CH42-a-turn-is-not-a-jump: a turn is not a jump

Make the gust pattern turn without a jump: after any turn, at any time, one
frame may move the pattern no further than the wind carries it in that frame.
Add a pause too, which holds the gusts where they are, so you can study one
pattern and see which motion is the wind's and which is the grass's own sway.
Predict first: once the gusts no longer jump, and with nothing else changed,
what do the blades do across the turn in the Wind view, and in **Shaded**?

**Acceptance:** over any run of frames, however the wind turns, speeds up or
slows down, one frame moves the published offset by no more than the mean
speed times the frame time, up to the spacing of the float it is published as.
A paused wind publishes the same bits frame after frame. In the Wind view,
after two minutes, a turn leaves the blotches where they are, and they drift
on along the new heading.

**Transfer:** Chapter 28, section 10's clouds read `windOffset()`, which is
velocity times time too. How far does the sky jump when their 10 m/s wind is
turned 90 degrees after ten minutes? Why could you not fix it by keeping the
clouds' offset in `CloudSettings`, whose `operator==` is how the clouds notice
that a slider moved (Chapter 28, section 13)?

<details>
<summary>Hint 1: two frames, two directions</summary>

Write where the gusts are after two frames that blew in different directions:
p₀ + d₁·v·dt + d₂·v·dt. Where does the time since the start appear in that
sum, and what in it changes when the direction does?

</details>

<details>
<summary>Hint 2: who keeps the sum</summary>

The owner already runs once a frame, and it already publishes a slot for the
gust offset: `WorldWindState::direction.zw`, which section 1 filled with
velocity times time. Keep the running total in the owner, in a `double`, add
the frame's travel in `Advance`, and publish it as a float. The grass's copy,
`GrassParameters::windDirection`, has a `zw` it never used; hand it the whole
vector.

</details>

<details>
<summary>Hint 3: the shader, and the pause</summary>

In `gustStrength`, `drift` is now just `grass.windDirection.zw`. A pause is a
frame in which the wind's clock does not move: advance by zero.

</details>

<details>
<summary>Worked solution: the offset, summed by the owner</summary>

**The owner keeps the sum.** In `WorldWind.h`, the private member that
counted the seconds goes. In its place the owner keeps the gust offset itself,
in a `double`:

```cpp
    glm::dvec2        m_offset{ 0.0 };
```

and the settings gain the pause, after `gustSize`:

```cpp
    bool  paused        = false;   // section 2: the wind's clock stands still: no drift, no turn
```

**This is `Advance`**, in `WorldWind.cpp`, in place of section 1's. It adds
this frame's travel (the direction that blew during the frame, times the
speed, times the frame's time) to the running total. A paused wind advances
by zero, as Chapter 52's **Paused** does if you took that chapter: its time
stands still, so it neither drifts nor, after the next attempt, turns.

```cpp
void WorldWind::Advance(float deltaSeconds)
{
    if (!std::isfinite(deltaSeconds) || deltaSeconds < 0.0f) { return; }   // a bad frame time changes nothing
    const float seconds = m_settings.paused ? 0.0f : deltaSeconds;          // paused: the wind's clock stands still

    // Section 2: carry the gusts by this frame's travel, along the direction that blew during it. The offset
    // is the sum of every frame's travel, so a turn bends the gusts' path instead of swinging all of it.
    const glm::dvec2 along{ m_state.direction.x, m_state.direction.y };
    m_offset += along * (static_cast<double>(m_settings.speed) * seconds);
    Publish();
}
```

`Publish` no longer works out an offset from a clock. The two lines that
computed it become one, and the comment above `Publish`, which described
them, goes:

```cpp
    m_state.direction = glm::vec4(along, glm::vec2(m_offset));
```

**Why a `double`.** Summed in a float, every frame's 5 cm of travel would be
rounded to the float's spacing, and the error would grow every frame. Summed
in a `double` and rounded once, when it is published, the error is half a
float's spacing and never grows: about 1 mm near 20 km and 4 mm near 100 km,
nothing against 15 m gusts. The spacing reaches a metre only past 8,000 km,
more than two weeks of a 5.5 m/s wind.

**The grass reads it.** `PackParameters` hands the whole vector on, in place
of section 1's comment and its line that kept only `xy`:

```cpp
        // Chapter 42 section 1: the compute pass cannot read FrameData, so the wind comes in a copy; from
        // section 2 its zw carries the owner's gust offset.
        .windDirection   = frame.wind.direction,
```

`GrassTypes.h` says what the slot now holds:

```cpp
    vec4  windDirection;    /* xy: unit vector the wind blows along, in world xz; zw: gust offset, metres (Chapter 42) */
```

and `gustStrength`, in `GrassGenerateKernel.glsl`, reads it in place of
velocity times time. Chapter 27 named the offset `drift`, and the name stays:

```glsl
// Chapter 27 section 2: gust strength where a blade stands, 0 calm to 1 a full gust. Two
// octaves of noise, the whole field carried downwind by the world wind's offset (Chapter 42 section 2).
float gustStrength(vec2 xz)
{
    vec2  drift = grass.windDirection.zw;   // Chapter 42 section 2: every frame's travel, summed by the owner
```

The rest of the function is unchanged. `GrassParameters::windSpeed` keeps its
place, so the block's layout does not move, but nothing in the grass reads it
any more. `CoastalArea::Prepare` already hands the coastal grass Horizon's
published state whole, so the coast needs no change of its own.

**The panel.** The pause is a checkbox among the wind's controls, after the
four sliders in `drawWorldWindPanel`. It is not called **Paused**, because
Horizon's coastal panel has a **Paused** of its own (Chapter 43's clock), and
two widgets with one label in one window are one widget to ImGui:

```cpp
    changed |= debug_panels::checkbox("Wind paused", &settings.paused);                                   // section 2
```

and the comment above the declaration in `WorldWind.h` stops counting
sliders:

```cpp
// The wind's controls, the same in every demo that owns a WorldWind. True if one changed.
```

**The two clocks.** The owner's clock starts at the demo's first `Update` and
adds up the frame times it is handed. Chapter 27's `time` counts from the
program's start. When nothing turns, that is now the only difference between
the old picture and the new. Started from the command line at a fixed clock,
both count the same frames, so the frame after two minutes matches section
1's to float rounding (the checkpoint measures it).

**Answer to the prediction.** In the Wind view the blotches now hold their
place, and in both views the blades still swing round in one frame. The next
attempt finds why.

**Answer to the transfer.** The clouds jump 2 × 10 × 600 × sin 45° = 8.49 km,
most of a sky. Their fix is the same sum, but it cannot live in
`CloudSettings`: an offset that changes every frame would make the settings
differ from last frame's every frame, and the clouds would restart their
running average every frame. A running total belongs beside the settings, in
the thing that advances them, as `m_offset` sits beside `m_settings` here.

</details>

<a id="ch42-a-lean-that-turns-smoothly"></a>

### Attempt CH42-a-lean-that-turns-smoothly: a lean that turns smoothly

With the first fix in, turn the wind again, in **Shaded**: the gusts hold, but
every blade still swings a quarter turn in one frame. Find why, then make the
wind itself turn, at a rate you choose, the short way round.

**Acceptance:** each frame turns the published direction by no more than the
turn rate times the frame time. The wind lands exactly, bit for bit, on the
direction it was given, after ceil(Δθ / (rate × dt)) frames. From 170 to −170
degrees it turns 20 degrees through 180, not 340 through 0. A half turn goes
the positive way, with the angle growing from −Z toward +X. The first wind a
demo configures blows where it is set, without turning from 0 first. A turn
rate under a degree a second, or an angle past a full turn either way (beyond
−360 to 360 degrees), is refused, and the old wind stays; the worked solution
says why.

**Transfer:** What turn rate keeps the tip of a 0.7 m blade, leaning 0.35
blade heights in a full gust, under 1 cm of travel a frame at 60 frames a
second?

<details>
<summary>Hint 1: who else reads the direction</summary>

The gust is not the only reader of the direction. Look at what
`GrassVertexKernel.glsl` hands `grassClumpLean`, and at what the clump
impostors hand it in `GrassClumpRuntime.glsl`.

</details>

<details>
<summary>Hint 2: two directions</summary>

Keep two angles in the owner: where the settings say the wind should blow, and
where it blows now. `Advance` moves the second toward the first by at most
`turnRate × dt` degrees, and `Publish` publishes the second.

</details>

<details>
<summary>Hint 3: the short way round</summary>

The difference of two angles is only defined up to whole turns. Bring it into
(−180, 180] with `fmod` and one correction, so that 170 to −170 is +20, not
−340. A difference of exactly 180 stays +180, which is the tie rule. When what
is left is no more than one frame's step, land on the wanted angle itself, so
that the published direction ends bit for bit where the settings put it.

</details>

<details>
<summary>Worked solution: the wind turns at a rate</summary>

**Why the blades still snap.** `applyWind`'s lean in Chapter 27, and
`grassClumpLean` in the shared kernels since, push the blade along
`grass.windDirection.xy`. The gust moved by a sum; the direction did not.
The wind has to turn, and every reader then turns with it.

**The settings gain a rate**, between `gustSize` and `paused`. Thirty degrees
a second turns a quarter of the compass in three seconds:

```cpp
    float turnRate      = 30.0f;   // section 2: degrees a second the wind turns toward towardDegrees
```

and the owner a slowest rate, after `MIN_GUST_SIZE` (`Configure`, below, says
why):

```cpp
    static constexpr float MIN_TURN_RATE = 1.0f;    // section 2: degrees a second, the slider's low end; a slower step can round away
```

**The owner keeps where it blows now.** The private part of `WorldWind`
becomes, whole:

```cpp
private:
    void Publish();

    WorldWindSettings m_settings;
    WorldWindState    m_state;
    // Section 2: where the wind blows now, turning toward m_settings.towardDegrees, and how far it has
    // carried the gusts: the sum of every frame's travel, in double, published as a float.
    float             m_towardDegrees = 0.0f;
    glm::dvec2        m_offset{ 0.0 };
    bool              m_configured = false;   // the first Configure sets the direction without a turn
};
```

`m_configured` is for the first wind. A demo's first `Update` hands the owner
its starting settings. Eased in from 0, every demo would open with the wind
swinging round from −Z, and Horizon's coast, blowing toward −90, would start a
quarter turn wrong.

**This is the short way round**, in `WorldWind.cpp`, above the namespace
block:

```cpp
// File scope, above the namespace block. Chapter 42 section 2: the short way round from one blows-toward
// angle to another, in (-180, 180]. Half a turn is a tie, and it goes the positive way, from -Z toward +X.
static float shortestTurnDegrees(float fromDegrees, float toDegrees)
{
    float turn = std::fmod(toDegrees - fromDegrees, 360.0f);   // (-360, 360)
    if (turn > 180.0f) { turn -= 360.0f; }
    else if (turn <= -180.0f) { turn += 360.0f; }
    return turn;
}
```

**This is `Configure`**, whole, in place of section 1's. It refuses two more
kinds of value, for one reason: the wind now steps toward its angle a little
each frame (half a degree at the default 30 degrees a second and 60 frames a
second), and a step smaller than half the gap between two floats rounds away.

- The angle must lie between −360 and 360 degrees. Past 2²³, about
  8.4 million, floats are a whole degree apart: a wind sitting on a typed
  10,000,000 degrees and asked for 0 would add its half degree, round back,
  and never move again.
- The turn rate must be at least `MIN_TURN_RATE`, a degree a second, the
  slider's low end. Near 360 degrees floats are about 0.00003 apart, so a
  much slower step can round away at a high frame rate; one degree a second
  still moves at over 30,000 frames a second.

The slider stops at ±180, and **Guide toward** (below) gives angles in
(−180, 180]. But Ctrl+click can type any number, so the owner refuses the
rest, and the demo puts the last good value back. The first wind it accepts
blows where it is set:

```cpp
InitializationResult WorldWind::Configure(const WorldWindSettings& settings)
{
    // Every value finite, and each in the range its readers can use: the gust size is a divisor, and section
    // 2's turn steps the angle, so the angle stays within a full turn either way and the rate is not so slow
    // that a frame's step rounds away.
    const bool finite = std::isfinite(settings.towardDegrees) && std::isfinite(settings.speed) &&
                        std::isfinite(settings.strength) && std::isfinite(settings.gustSize) &&
                        std::isfinite(settings.turnRate);
    if (!finite || std::abs(settings.towardDegrees) > 360.0f || settings.speed < 0.0f || settings.speed > MAX_SPEED ||
        settings.strength < 0.0f || settings.strength > 1.0f || settings.gustSize < MIN_GUST_SIZE ||
        settings.turnRate < MIN_TURN_RATE)
    {
        return InitializationResult::failure(std::format("World wind unchanged: values must be finite, direction -360 to 360 degrees, speed 0-{} m/s, strength 0-1, gust size at least {} m, turn rate at least {} deg/s.", MAX_SPEED, MIN_GUST_SIZE, MIN_TURN_RATE));
    }
    m_settings = settings;
    if (!m_configured)   // section 2: the first wind blows where it is set; a later one is turned toward
    {
        m_towardDegrees = settings.towardDegrees;
        m_configured    = true;
    }
    Publish();
    return InitializationResult::success();
}
```

**`Advance` turns the wind** after it has carried the gusts. Between the
`m_offset` line and `Publish();`:

```cpp
    // Then turn toward the wanted direction, the short way round, by at most turnRate degrees a second.
    const float turn = shortestTurnDegrees(m_towardDegrees, m_settings.towardDegrees);
    const float step = m_settings.turnRate * seconds;
    m_towardDegrees  = std::abs(turn) <= step ? m_settings.towardDegrees : m_towardDegrees + std::copysign(step, turn);
```

This frame's gusts travel along the direction published last frame. The
turned direction is published at once, so the blades lean along it in this
frame, and the gusts follow it from the next. Paused, `step` is 0, so the
wind does not turn either. Landing on `m_settings.towardDegrees` itself, not
on a sum of steps, puts the published direction bit for bit where Chapter
27's formula would, so a finished turn leans the blades exactly as if the
wind had always blown there. The gusts keep the bent path they travelled.

**This is `Publish`**, whole, in place of section 1's. It publishes where the
wind blows now:

```cpp
// Where the wind blows now, the same float operations as Chapter 27's PackParameters, and how far it has
// carried the gusts.
void WorldWind::Publish()
{
    const float     toward = glm::radians(m_towardDegrees);
    const glm::vec2 along{ std::sin(toward), -std::cos(toward) };
    m_state.direction = glm::vec4(along, glm::vec2(m_offset));
    m_state.gust      = glm::vec4(m_settings.strength, m_settings.gustSize, m_settings.speed, 0.0f);
}
```

**The panel** gets the rate, before the pause:

```cpp
    changed |= debug_panels::sliderFloat("Turn rate (deg/s)", &settings.turnRate, 1.0f, 180.0f, "%.0f");   // section 2
```

**Answer to the transfer.** A full-gust lean puts the tip 0.35 × 0.7 =
0.245 m out from the root, and a turn of Δθ radians moves it 0.245·Δθ, so 1 cm
a frame allows 0.041 rad, 2.3 degrees, a frame: 140 degrees a second. The
default 30 moves the tip 2 mm a frame.

</details>

### Guide toward

*Ghost of Tsushima* points the way without a marker on the screen: its
Guiding Wind turns until it blows toward where you are going. With a wind
that turns at a rate, that is one more control. While a landmark is chosen in
Horizon's **Guide toward**, the demo hands the owner, every frame, the
direction from the camera to it. The owner turns the wind there at its turn
rate, and the coastal grass follows.

The direction from the camera to a landmark is a vector on the ground; the
owner wants an angle. **This is `blowsTowardDegrees`**, the inverse of
(sin a, −cos a), declared in `WorldWind.h` after `drawWorldWindPanel`:

```cpp
// Section 2: the blows-toward angle of a direction on the ground, in (-180, 180]: the inverse of
// (sin a, -cos a). The direction need not be a unit vector, but it must not be zero.
float blowsTowardDegrees(glm::vec2 along);
```

and defined at the end of `WorldWind.cpp`'s namespace block.
`atan2(x, −z)` undoes (sin a, −cos a) whatever the vector's length. It
answers from −180 to 180, and −180 and 180 are the same direction, so −180 is
reported as 180. Then each direction has one number, in the same (−180, 180]
that `shortestTurnDegrees` works in:

```cpp
// Section 2: atan2 answers in [-180, 180], and -180 is the same direction as 180.
float blowsTowardDegrees(glm::vec2 along)
{
    const float degrees = glm::degrees(std::atan2(along.x, -along.y));
    return degrees <= -180.0f ? 180.0f : degrees;
}
```

In `HorizonDemo.h`, below `m_cloudWind`, the demo remembers the choice:

```cpp
    int                                m_windGuide = 0;       // section 2: 0 nothing, else 1 + a LANDMARKS index
```

In `DrawWindControls`, after `drawWorldWindPanel`, the combo lists the
landmarks in `LANDMARKS`' order (Chapter 37, section 3):

```cpp
    // Section 2: Ghost of Tsushima's Guiding Wind. While a landmark is chosen, Update sets Blows toward.
    debug_panels::combo("Guide toward", &m_windGuide, "Nothing\0Lighthouse\0Tower\0Keep\0");   // LANDMARKS' order
```

and in `HorizonDemo::Update`, before the owner is handed the settings, the
guide writes where the wind should blow. Within a metre of the landmark there
is no direction to blow in, so the wind keeps the one it had:

```cpp
    // Chapter 42 section 2: a guided wind wants to blow from the camera toward the landmark, wherever the
    // camera goes; the owner turns it there at its turn rate. Closer than a metre there is no direction.
    if (m_windGuide > 0)
    {
        const glm::vec2 toLandmark = LANDMARKS[m_windGuide - 1].position -
                                     glm::vec2(m_cameraTransform.translation.x, m_cameraTransform.translation.z);
        if (glm::length(toLandmark) > 1.0f) { m_windSettings.towardDegrees = vulkan_graphics::blowsTowardDegrees(toLandmark); }
    }
```

While a guide is chosen, **Blows toward** follows it, and a drag on the slider
is undone the next frame; choose **Nothing** to steer by hand again.

For a scripted run, `--wind-guide` chooses the landmark at the
`--wind-turn-at` frame. `HorizonDemo.h` gains a setter after `SetWindToward`:

```cpp
    void SetWindGuide(int guide) { m_windGuide = guide; }   // Chapter 42 section 2: --wind-guide; 0 nothing, else 1 + a LANDMARKS index
```

In `Main.cpp`, `LaunchSettings` gains a field after `windValuesValid`:

```cpp
    int                               windGuide = 0;         // Chapter 42 section 2: Horizon's guide from that frame; -1 an unknown name
```

`parseSettings` gains a branch after the wind-turn one:

```cpp
        else if (key == "--wind-guide")
        {
            constexpr std::array<std::string_view, 4> guides{ "none", "lighthouse", "tower", "keep" };   // LANDMARKS' order
            const auto found = std::find(guides.begin(), guides.end(), value);
            settings.windGuide = found != guides.end() ? static_cast<int>(found - guides.begin()) : -1;   // -1: refused below
        }
```

`main` gains a check after the wind-turn check:

```cpp
    if (settings.windGuide < 0 || (settings.windGuide > 0 && settings.windTurnAt == 0))
    {
        Log::error("--wind-guide is none, lighthouse, tower or keep, and needs --wind-turn-at.");
        return 1;
    }
```

and the frame hook gains one call, after its two `SetWindToward` calls:

```cpp
            horizonDemo.SetWindGuide(settings.windGuide);     // section 2: or toward a landmark (0: no guide)
```

### Checkpoint

Build, then run the Grass demo in its Wind view, as at the start of this
section. **Wind** now shows **Turn rate (deg/s)**, 30, and **Wind paused**
after **Gust size**. After two minutes, drag **Blows toward** from 20 to 110:

- the blotches stay where they are, and over about three seconds the
  direction they move bends round to the new heading;
- in **Shaded**, the blades' lean swings round over the same three seconds
  instead of snapping;
- **Wind paused** stops the blotches and the turn where they are. The blades,
  and the clump impostors, go on swaying: their sway is the grass's own
  response, on the grass's own clock. A **Mean speed** of 0 also stops the
  blotches, but the wind still turns and the grass still sways.

In Horizon at **Coast dunes**, with **Grass view** set to Wind under
**Coastal area**, choose **Lighthouse** in **Guide toward**. **Blows toward**
reads about 15 deg at once, the lighthouse's direction from there, and the
grass's gusts and lean turn to it over three and a half seconds.

**Measure the turn.** Turn the wind at frame 7200, two minutes in, and save
the frames around it: `--sequence` writes each frame from `--sequence-first`
to `--sequence-last`, which may not pass `--frames`, as a BMP in a folder. Run
this build with the turn, section 1's copy with the same turn, and this build
without it, for a baseline. `@run` hands the array's items to the program:

```powershell
$last = 7215   # 7400 for the whole turn
$run = '--demo', 'Grass', '--grass-debug-view', 'wind', '--msaa', '4', '--width', '1600', '--height', '900',
       '--fixed-dt', '0.016666667', '--frames', $last, '--sequence-first', '7190', '--sequence-last', $last
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe @run --wind-turn-at 7200 --wind-turn-to 110 --sequence turn
& ..\SandboxGame-section1\SandboxGame.exe @run --wind-turn-at 7200 --wind-turn-to 110 --sequence turn-section1
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe @run --sequence still
```

Then compare each frame with the one before it. `MeanAbsoluteChannelDelta` is
the mean change of a colour channel, out of 255:

```powershell
. .\Tests\TutorialHarness\ImageArtifacts.ps1
function Show-Changes($folder, $first, $last)
{
    foreach ($frame in ($first + 1)..$last)
    {
        $before = Join-Path $PWD ('{0}\frame-{1:D6}.bmp' -f $folder, ($frame - 1))
        $after  = Join-Path $PWD ('{0}\frame-{1:D6}.bmp' -f $folder, $frame)
        '{0}: {1:N3}' -f $frame, [TutorialImageDiff]::Compare($before, $after, 1).MeanAbsoluteChannelDelta
    }
}
Show-Changes turn 7190 $last
Show-Changes turn-section1 7190 $last
Show-Changes still 7190 $last
```

A jump stands out from the frames beside it. In section 1's run, frame 7200
reads dozens of times its neighbours, and the frames after it show another
field. In this build's run no frame reads more than about one and a half
times the median of the six frames around it. For **Shaded**, put `'shaded'`
in place of `'wind'` and run the three again. One RTX 5090 at these settings
read, at frame 7200:

| Frame 7200 | This build | Section 1's build | No turn |
| --- | --- | --- | --- |
| Wind view | 0.45 | 12.1 | 0.32 |
| **Shaded** | 1.48 | 17.0 | 0.96 |

Without the turn, the Wind view read 0.31 to 0.49 over these frames, as the
blades sway and the gusts drift. After the turn, this build's worst frame
read 1.08 times the median of its neighbours (1.20 in **Shaded**). Your GPU's
numbers will differ a little; `REFERENCE.md` keeps the full readings.

For the whole three-second turn, set `$last = 7400`, run the two lines that
set `$run` again so that they pick up the new `$last`, and repeat the turned
and unturned runs and their comparisons. The turned run rises unevenly to
about twice the unturned one (at most 1.96 times in the Wind view). From
frame 7380, after the turn, it stays near 1.8 to 1.9 times (1.5 to 1.7 in
**Shaded**). That is the new heading, not a jump: the camera looks along −Z,
so at 20 degrees the gusts drift away from it, and at 110 degrees across the
view, which changes more pixels a frame. Still no frame stands out.

Horizon's coastal grass shows the same, turned from −90 to 0 at frame 600:

```powershell
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe `
    --demo Horizon --horizon-view "Coast dunes" --grass-debug-view wind --msaa 4 --width 1600 --height 900 `
    --fixed-dt 0.016666667 --wind-turn-at 600 --wind-turn-to 0 `
    --frames 615 --sequence-first 590 --sequence-last 615 --sequence dunes
Show-Changes dunes 590 615
```

On the RTX 5090 the turn frame read 0.096, close to the 0.073 to 0.082 of the
frames before it; section 1's build read 2.90 there.

Without a turn, the two builds should agree, up to the two clocks. Count the
pixels that differ in frame 7200 of a plain run:

```powershell
$plain = '--demo', 'Grass', '--grass-debug-view', 'wind', '--msaa', '4', '--width', '1600', '--height', '900',
         '--fixed-dt', '0.016666667', '--frames', '7200', '--capture-output'
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe @plain plain-section2.bmp
& ..\SandboxGame-section1\SandboxGame.exe @plain plain-section1.bmp
[TutorialImageDiff]::Compare("$PWD\plain-section1.bmp", "$PWD\plain-section2.bmp", 1).ChangedPixels
```

On the RTX 5090, 38 or 39 pixels of 1.44 million differ, where two runs of one
build differ in 0 to 2. The two clocks' sums differ in a float's last bit,
which moves a few blade edges across a sample.

Section 1's build above and this section's below, frames 7199 and 7200 from
left to right:

![Four frames of the Grass demo's Wind view after two minutes, the wind turned from 20 to 110 degrees at frame 7200. Top, section 1's build: frames 7199 and 7200 show two different patterns of blue lulls and pink gusts. Bottom, this section's build: frames 7199 and 7200 show the same pattern.](images/42-turn-without-jump.jpg)

Section 2's checks are a third test, `TutorialWorldWindTurnTests`, in a file
of their own so that section 1's still builds for a reader who has not
reached this section. Its source,
[`WorldWindTurnTests.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/WorldWindTurnTests.cpp),
is supplied like section 1's: copy it unchanged to
`Tests/TutorialHarness/WorldWindTurnTests.cpp` if your tree lacks it. Its
project goes after `TutorialWorldWindTests`' in `premake5.lua`:

```lua
    project "TutorialWorldWindTurnTests"   -- Chapter 42 section 2, apart so section 1's checks build without it
        kind "ConsoleApp"
        apply_common_cpp_settings()
        files { "Tests/TutorialHarness/WorldWindTurnTests.cpp" }
        includedirs { "Vendor/GLFW/include" }
        links { "PillowFortEngine", "GLFW", "ImGui", "TinyUSDZ" }
```

The project is new, so generate again, then build and run all three; section
1's two still pass:

```powershell
.\GenerateProjects.bat --tutorial-tests
if ($LASTEXITCODE -ne 0) { throw 'Project generation failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:TutorialWorldWindTests,TutorialWorldWindTurnTests,TutorialRendererConvergenceTests
if ($LASTEXITCODE -ne 0) { throw 'The acceptance test build failed.' }
foreach ($target in 'TutorialWorldWindTests', 'TutorialWorldWindTurnTests', 'TutorialRendererConvergenceTests')
{
    & ".\Build\Artifacts\Debug\$target\$target.exe"
    if ($LASTEXITCODE -ne 0) { throw "$target failed." }
}
```

`TutorialWorldWindTurnTests` prints one `PASS` line with its count of checks.
It checks that:

- a turn rate that is not finite or is under a degree a second, or an angle
  past a full turn either way (10,000,000 degrees among them), is refused,
  and the old wind stays;
- the offset reaches `GrassParameters` bit for bit;
- over 10,000 random frames 20 km out, where floats are coarse, with the wind
  turned, sped up, slowed and paused at random, no frame moves the offset or
  turns the direction further than it may;
- velocity times time breaks that bound: worked out from the formula alone,
  with no owner, a sudden 90-degree turn after two minutes at 3 m/s jumps
  509 m; and an eased turn, worked out on the owner's own directions, still
  moves the field over fifty times the bound in a frame;
- turns land exactly, including 170 to −170, 350 to −350 and both half turns;
- a pause, or a bad frame time, in the middle of a turn changes nothing;
- the offset 100 km out is within one float spacing, 8 mm, of the owner's
  `double`;
- `blowsTowardDegrees` undoes (sin a, −cos a), at unit length and at 2.5 km.

This section's first attempt, CH42-a-turn-is-not-a-jump, has a prepared CPU
pair, `ch42-integrated-drift`
([how to use one](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md)). Its
Starter's `Advance` puts velocity times time back (the direction now times the
distance so far), and it fails one of the oracle's checks: the gusts' travel
through a turn. The Starter is the current reference with that one line
changed, so it already holds the second attempt's answer: open it after both
attempts.

Next: [43 — Waves to the Shore](43-Waves-To-The-Shore.md).
