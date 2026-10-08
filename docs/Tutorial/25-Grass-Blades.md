# 25 — Grass, Part I: Blades

**Goal:** a 20 × 20 m patch of forty thousand grass blades on rolling ground.
Every blade is a curved, tapered strip that the vertex shader builds from two
`vec4`s and `gl_VertexIndex` — no mesh, no vertex buffer. The blades are lit by
Chapter 16's sun, shadowed by Chapter 17's cascades, and two standing stones
throw shadows across them.

**ROADMAP:** step 21+ — a demo, in `Source/PillowFort/Demos/Grass/` with
shaders under `Shaders/Grass/`.

**Module:** the demo is `pf::demos::grass` (`GrassDemo`). One engine addition
that any later pipeline can use: `GraphicsPipelineDesc` gains a `topology`
field (section 4).

**Prerequisites:**

- Chapter 08 sections 4 (ImGui colors are sRGB; the shaders want linear), 6
  (one uniform buffer per frame in flight), and 8 (C++/GLSL twin structs).
- Chapter 09 — the `Demo` interface (section 2), what `Setup` is handed
  (section 3), and the scene part of the frame: `beginScenePass`,
  `endScenePass`, `handBackSceneTarget` (section 4). Section 7 for registering a
  demo in `Main.cpp`, and section 8 for a demo's C++/GLSL twin header.
- Chapter 10 sections 6 (`rotationFromYawPitch`), 7 (`FrameData`,
  `FrameBlock.glsl`, and `SceneRenderer`'s set 0), 9 (the depth buffer every
  scene pipeline declares), 11 (the fly controller), and 12 (`CameraControls`
  and the "Camera" panel).
- Chapter 11 sections 4 (`makeCube`), 6 (uploading through a staging buffer, and
  the barrier after the copy), 7 (which side is the front), 10 (Lambert's
  diffuse light), and 11 (`AddMesh`, `AddMaterial`); and its `ColorSpace.h`
  (`scene::srgbToLinear`).
- Chapter 12 section 5 — why a demo keeps its camera's `Transform` beside the
  `Camera` instead of inside it, and the cross product, whose argument order
  sections 5 and 7 rely on.
- Chapter 16 sections 2, 4, and 5 — a `LightItem` is plain data, `WriteLights`
  fills set 0's light buffer, and `lightIrradiance` in `Lights.glsl` reads it.
- Chapter 17 sections 6 and 9 — `sunShadow` in `Shadows.glsl`, and
  `RecordShadows`; and its "Shadows" panel.
- Chapter 18 section 6 — every pipeline drawn in the scene pass takes the
  scene's sample count.
- Chapter 19 sections 1 and 2 — instancing with `gl_InstanceIndex`, and a
  storage buffer as per-instance data — and the `PrepareDraws` / `RecordDraws`
  split of sections 5 and 6.
- For section 8: Chapter 23 section 8 — a demo's sky: the member,
  `Initialize`, `Update` before the scene pass, `Draw` after the opaque draws,
  `Shutdown` — and Chapter 24 section 4: every demo that draws meshes calls
  `SetImageBasedLighting`, `Sky::Update` takes the frame index, and
  `skyLightsScene` becomes `FrameData::ambientMode`.

---

## Where this is going

*Ghost of Tsushima* (Sucker Punch, 2020) is remembered for its fields: hills of
pampas grass that move in long waves when the wind comes through, every blade
its own. Eric Wohllaib described how they were made in "Procedural Grass in
*Ghost of Tsushima*" at GDC 2021. These three chapters build toward that grass,
one idea at a time.

What the talk describes, as one picture:

- **Every blade is generated on the GPU, every frame.** The world is cut into
  tiles. A compute shader lays out candidate blades on a jittered grid in each
  tile near the camera, looks up what grows there and how tall, culls against
  the view and the distance, and writes an instance for each blade that
  survives.
- **A blade is a cubic Bézier curve** — four control points — described by a
  handful of numbers: height, width, tilt, bend, and the direction it faces. It
  tapers to a point.
- **Two levels of detail:** 15 vertices near the camera, 7 farther away, and the
  near blade morphs into the far shape before it switches, so nothing pops.
- **Clumps.** Blades belong to Voronoi cells that pull them together and give
  them a shared height, facing, and color, the way real grass grows in tufts.
- **Wind** is a 2D noise field scrolling across the world in the wind's
  direction; each blade samples it and sways on its own phase.
- **The look:** blades seen edge-on are widened in view space so the field never
  goes thin; normals are tilted across each blade so a flat strip shades as if
  rounded; translucency, gloss, and darkening toward the root; distant blades take
  the ground's normal.
- **Shadows** do not come from the blades, which are too many and too thin to
  draw into a shadow map. The terrain, raised to grass height and dithered, is
  drawn into the shadow map instead, and screen-space shadows add the fine
  detail.

### Where each technique comes from

Every technique in these three chapters is one of three kinds. **The game's**
means at least two of the sources listed at the end of this chapter — written
summaries of the talk, and open implementations that say which of their ideas
came from it — agree that *Ghost of Tsushima* does it. **One source** means only
one summary says so. **This tutorial's** means the sources do not describe the
game's method, and what is built here is a common technique chosen to fill the
gap. The chapters state the method either way; this table is the one place
that says which is which.

| Technique | Kind | Where |
| --- | --- | --- |
| Blades on a jittered grid, generated per tile in compute, culled by view and distance | the game's | 25 §2, 26 §2-3 |
| A blade as a cubic Bézier curve, tapering to a point, from height, width, tilt, bend, and facing | the game's | 25 §6 |
| 15 vertices near, 7 far, vertices crowded toward the tip, and a morph before the switch | the game's | 25 §4, 26 §5-6 |
| The blade's height read from the terrain under it | the game's (from a height texture; here a function) | 25 §3 |
| The 32-byte blade record, the 4 m tile, the density falloff, the capacities | this tutorial's | 25 §2, 26 §2, §7 |
| No culling of edge-on blades; widening them in view space instead | the game's | 26 §3, 27 §3 |
| Occlusion culling against last frame's depth | this tutorial's, from GPU-driven renderers | 26 §9 |
| Clumps from Voronoi cells sharing height, facing, and color | the game's | 27 §1 |
| Wind from a scrolling noise field, plus a sway on each blade's own phase | the game's | 27 §2 |
| A minimum width carried as alpha-to-coverage | this tutorial's, the standard thin-geometry technique | 27 §4 |
| Normals tilted across the blade; distant blades taking the ground's normal | the game's | 27 §5-6 |
| Translucency, a highlight, and darkening toward the root | the game's (named); the shading models are this tutorial's | 27 §7 |
| The terrain, raised and dithered, as the grass's shadow caster; screen-space shadows | one source | 27 §8 |
| A ball that pushes blades aside | this tutorial's | 27 §9 |
| Short grass folding one blade into two | the game's (not built) | 27, "Where to go from here" |

### The staircase

That picture is three chapters' work, and each stands on the last:

| Chapter | What it adds | The idea to take from it |
| --- | --- | --- |
| **25 — Blades** (this one) | One blade's geometry: a strip from `gl_VertexIndex`, curved, two-sided, lit, shadowed. Forty thousand of them, placed once by the CPU. | A blade is a function of a few numbers, evaluated in the vertex shader. |
| **26 — GPU Generation** | The field is generated around the camera every frame in compute, culled, split into two LODs, and drawn by two indirect draws. An optional Part 2: occlusion culling against last frame's depth. | The field is a function of *position*, not a list. |
| **27 — The Look** | Clumps, wind, edge-on thickening, rounded normals, light through the blades, the far field, grass shadows, and a ball the blades get out of the way of. | Each trick is a few lines, and each is a toggle you can see. |

This chapter deliberately does the one thing *Ghost of Tsushima* does not: it
places the blades once, on the CPU, in a fixed patch. That is the wrong
architecture for a field — Chapter 26 says why and replaces it — but it keeps
everything else out of the way while the blade itself is the subject. Nothing
here is wasted: the blade's shape, its data, its two pipelines, and its lighting
all carry forward unchanged.

### What you are actually writing

**This is `GrassDemo.h`**, the map of the chapter. Every private function names
the section that writes it; the five functions every demo has start in section 1
and grow.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Grass toward Ghost of Tsushima: blades from the vertex shader (Chapter 25)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Grass/GrassDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/DrawItem.h"
#include "PillowFort/Scene/Transform.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"
#include "PillowFort/VulkanGraphics/ShadowMaps.h"
#include "PillowFort/VulkanGraphics/Sky.h"
#include "Grass/GrassTypes.h"

#include <glm/glm.hpp>

#include <array>
#include <cstdint>
#include <vector>

namespace pf::demos::grass {

// What the panel edits (section 2). CPU state: it survives Teardown and Setup.
struct GrassSettings
{
    glm::vec3 rootColor   { 0.15f, 0.25f, 0.10f };   // sRGB, as the swatches show them
    glm::vec3 tipColor    { 0.54f, 0.65f, 0.27f };
    glm::vec3 groundColor { 0.27f, 0.25f, 0.17f };
    float     terrainAmplitude  = 1.2f;     // metres
    float     terrainWavelength = 40.0f;    // metres
    float     sunElevation      = 35.0f;    // degrees above the horizon
    float     sunAzimuth        = 230.0f;   // degrees, turning from -Z toward +X
    float     sunIntensity      = 3.0f;     // irradiance, in Chapter 16's units
    int       debugView         = 0;        // GRASS_VIEW_*
};

class GrassDemo final : public Demo
{
public:
    GrassDemo();                                                                         // section 1
    const char*          Name() const override { return "Grass"; }
    InitializationResult Setup(const DemoContext& context) override;                    // section 1
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override; // section 1
    void                 Update(const FrameInput& input) override;                      // section 1
    void                 Record(const RecordContext& frame) override;                   // section 1
    void                 Teardown() override;                                           // section 1
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }

private:
    InitializationResult CreateBlades();        // section 2
    InitializationResult CreateDescriptors();   // section 2
    InitializationResult CreatePipelines();     // sections 3 and 4
    void                 CreateStones();        // section 8
    void WriteFrameBuffers(uint32_t frameIndex, const glm::mat4& view, const glm::mat4& projection);   // section 2

    // The patch: PATCH_SIDE x PATCH_SIDE cells of BLADE_SPACING metres, one blade in each.
    static constexpr float    BLADE_SPACING = 0.1f;
    static constexpr uint32_t PATCH_SIDE    = 200;     // 20 m square, 40 000 blades
    // The ground under it: TERRAIN_CELLS x TERRAIN_CELLS quads of TERRAIN_CELL metres.
    static constexpr float    TERRAIN_CELL  = 0.5f;
    static constexpr uint32_t TERRAIN_CELLS = 160;     // 80 m square

    DemoContext                    m_context;
    vulkan_graphics::SceneRenderer m_sceneRenderer;    // set 0: camera, sun, shadows; it also draws the stones
    vulkan_graphics::Sky           m_sky;   // Chapter 23
    bool                           m_skyLightsScene = false;   // Chapter 25 section 8: Chapter 24's switch, this frame

    // Section 2: the blades and the parameters, and the set that holds them.
    vulkan_graphics::AllocatedBuffer m_blades;
    uint32_t                         m_bladeCount = 0;
    std::array<vulkan_graphics::AllocatedBuffer, vulkan_graphics::FRAMES_IN_FLIGHT> m_parameterBuffers;
    VkDescriptorSetLayout            m_grassSetLayout = VK_NULL_HANDLE;
    VkDescriptorPool                 m_descriptorPool = VK_NULL_HANDLE;
    std::array<VkDescriptorSet, vulkan_graphics::FRAMES_IN_FLIGHT> m_grassSets{};

    // Sections 3 and 4: one layout for both pipelines.
    VkPipelineLayout m_pipelineLayout  = VK_NULL_HANDLE;
    VkPipeline       m_terrainPipeline = VK_NULL_HANDLE;
    VkPipeline       m_grassPipeline   = VK_NULL_HANDLE;

    // Section 8: something to cast a shadow on the grass.
    std::vector<scene::DrawItem> m_stones;

    // CPU state.
    GrassSettings                   m_settings;
    vulkan_graphics::ShadowSettings m_shadowSettings;
    scene::Camera                   m_camera;
    scene::Transform                m_cameraTransform;   // the grass has no Scene: its camera's pose is its own
    scene::CameraControls           m_controls;
    float                           m_time      = 0.0f;
    float                           m_deltaTime = 0.0f;
};

} // namespace pf::demos::grass
```

Everything the panel edits lives in `GrassSettings`, and the camera lives in
the demo object, so switching to another demo and back keeps both (Chapter 09
section 2). The demo has no `Scene` — a field of grass is not a node tree — so
it keeps the camera's pose in `m_cameraTransform` beside `m_camera`, the way
Chapter 12 section 5 arranges every camera. `m_sceneRenderer` is there for three
things the grass needs and should not rebuild: set 0 (the camera, the sun, the
shadow map), the shadow pass, and drawing ordinary meshes — the two stones of
section 8.

### Where everything lands

```text
Source/PillowFort/VulkanGraphics/
  GraphicsPipeline.h/.cpp   + topology                                       section 4
Shaders/Grass/
  GrassTypes.h              C++/GLSL twins                                   section 2
  Terrain.glsl              the ground's height and normal, in one place      section 3
  Terrain.vert.glsl         a square of ground from gl_VertexIndex            section 3
  Terrain.frag.glsl         the ground, lit                                   section 3
  Grass.vert.glsl           a blade from gl_VertexIndex                       sections 4-7
  Grass.frag.glsl           its color and its light                           sections 4 and 7
Source/PillowFort/Demos/Grass/
  GrassDemo.h/.cpp          the demo
Source/SandboxGame/Main.cpp + one registration line                           section 1
```

```text
GrassDemo.cpp
  includes
  static sunTravelDirection(elevation, azimuth)          section 2
  namespace pf::demos::grass {
      using namespace vulkan_graphics;
      static drawGrassPanel(settings, bladeCount)         section 2
      GrassDemo::GrassDemo                                section 1
      GrassDemo::Setup                                    section 1
      GrassDemo::CreatePipelines                          sections 3 and 4
      GrassDemo::CreateBlades                             section 2
      GrassDemo::CreateDescriptors                        section 2
      GrassDemo::CreateStones                             section 8
      GrassDemo::Resize                                   section 1
      GrassDemo::Update                                   section 1, grown in 2 and 8
      GrassDemo::WriteFrameBuffers                        section 2
      GrassDemo::Record                                   section 1, grown in 2-5 and 8
      GrassDemo::Teardown                                 section 1, grown in 8
  }
```

`GrassDemo.cpp` includes `GrassDemo.h`, `PillowFort/DebugPanels/DemoPanel.h`,
`PillowFort/Scene/ColorSpace.h`, `PillowFort/Scene/Light.h`,
`PillowFort/Scene/MeshGenerators.h`, `PillowFort/VulkanGraphics/GraphicsPipeline.h`,
`<glm/gtc/matrix_transform.hpp>`, `<imgui.h>`, `<vma/vk_mem_alloc.h>`, `<cmath>`,
`<cstring>`, `<random>`, and `<span>`.

> **Rerun `GenerateProjects.bat`** after creating these files, and again
> whenever a later section adds one. Premake expands both the C++ and the shader
> globs when it generates the projects; a file added afterwards is not built,
> and a shader that is not built fails at `Setup` with a missing `.spv`.

---

## 1. An empty field: the demo's skeleton

Before any grass, the demo needs to exist: a camera you can fly, a sky, and a
scene pass that draws nothing yet. Everything in this section is Chapter 09's
and Chapter 10's pattern, so it goes quickly.

**This is the constructor.** Chapter 09 section 2 says a demo's constructor
holds CPU state only — no device exists yet — so all it does is say where the
camera starts:

```cpp
// CPU state only, no GPU work (Chapter 09): where the camera starts. Walking
// height, a few metres back from the patch, looking slightly down, flying.
GrassDemo::GrassDemo()
{
    m_controls.active              = scene::ControllerKind::Fly;
    m_cameraTransform.translation  = glm::vec3(0.0f, 1.6f, 9.0f);
    m_cameraTransform.rotation     = scene::rotationFromYawPitch({ .yaw = 0.0f, .pitch = glm::radians(-8.0f) });
}
```

The **fly** controller (Chapter 10 section 11) suits grass better than the
default orbit: you want to walk through a field at head height, not circle a
point. The camera starts 1.6 m up — eye height — 9 m back from the patch's
centre, pitched 8° down so the patch fills the lower half of the view.
`rotationFromYawPitch` is Chapter 10 section 6's; the fly controller reads its
angles back out of the rotation every frame, so a pitch set here is kept, not
snapped back to level the first time the mouse moves.

**This is `Setup`, as it starts.** The scene renderer is created first, because
everything later depends on its set 0 layout:

```cpp
InitializationResult GrassDemo::Setup(const DemoContext& context)
{
    m_context = context;   // first, so Teardown works however far this gets

    if (auto result = m_sceneRenderer.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats);
        !result)
    {
        return result;
    }
    return InitializationResult::success();
}
```

`m_context` is assigned before anything can fail, because `Teardown` uses its
device and allocator to destroy whatever `Setup` got as far as making (Chapter
09 section 2: `Teardown` must be safe after a partial `Setup`). Sections 2, 3,
4, and 8 each add a line here.

**This is `Resize`.** The demo owns nothing sized to the window — the depth
buffer is the renderer's, and the aspect ratio is read from the targets every
frame — so there is nothing to do:

```cpp
// Nothing here is sized to the window: Record takes the aspect ratio from the targets.
InitializationResult GrassDemo::Resize(const SceneTargets& /*targets*/)
{
    return InitializationResult::success();
}
```

**This is `Update`, as it starts:** this frame's events to the controllers,
the active controller moves the camera, the time is kept for `FrameData`, and
Chapter 10's "Camera" panel is drawn:

```cpp
void GrassDemo::Update(const FrameInput& input)
{
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    m_controls.Update(input.deltaSeconds, m_cameraTransform);
    m_time      = input.elapsedSeconds;
    m_deltaTime = input.deltaSeconds;

    scene::drawCameraPanel(m_camera, m_controls, m_cameraTransform);
}
```

`Update` runs before the frame's fence wait (Chapter 09 section 9), so it
touches CPU state only. Everything the GPU reads is written in `Record`.

**This is `Record`, as it starts:** clear the scene target to a sky blue and
hand it back.

```cpp
void GrassDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;

    const VkClearColorValue clearColor{ { 0.35f, 0.50f, 0.75f, 1.0f } };   // linear
    beginScenePass(commandBuffer, frame.targets, &clearColor);
    endScenePass(commandBuffer);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

The clear color is **linear**, like every color the scene target holds
(Chapter 08 section 4), so it reaches the screen as a lighter, paler blue.

**This is `Teardown`, as it starts.** It releases what `Setup` made, in reverse:

```cpp
void GrassDemo::Teardown()
{
    m_sceneRenderer.Shutdown();
}
```

Section 8 shows it complete.

**And this is the registration**, in `Source/SandboxGame/Main.cpp`, beside the
other demos (Chapter 09 section 7):

```cpp
#include "PillowFort/Demos/Grass/GrassDemo.h"
```

```cpp
demoList.push_back(std::make_unique<demos::grass::GrassDemo>());          // Chapter 25
```

Run with `--demo Grass`, or pick "Grass" in the "Demos" window. You should see
an empty blue sky and the "Camera" panel, set to Fly. Moving changes nothing
you can see yet, because there is nothing to see.

---

## 2. The grass's own data

The grass needs three things the scene renderer does not provide: the blades
themselves, the numbers the panel edits, and a few values that differ between
draws. Each gets the home its access pattern calls for.

### The twin structs

**This is `Shaders/Grass/GrassTypes.h`**, shared by C++ and GLSL the way Chapter
09 section 8 shares a demo's types: `#include "GrassTypes.h"` from a shader
beside it, `#include "Grass/GrassTypes.h"` from C++ (premake's `Shaders`
include directory, Chapter 09):

```c
/* Shaders/Grass/GrassTypes.h - the grass demo's C++/GLSL twins. GLSL includes it as
   "GrassTypes.h", C++ as "Grass/GrassTypes.h". */
#ifndef PF_GRASS_TYPES_H
#define PF_GRASS_TYPES_H

#include "SharedShaderTypes.h"   /* the vec4 and uint aliases, on the C++ side */

#ifdef __cplusplus
    namespace pf::demos::grass {
    using shared::vec4;
    using shared::uint;
#endif

/* What the fragment shaders draw instead of the lit color (GrassParameters::debugView). */
#define GRASS_VIEW_SHADED   0u
#define GRASS_VIEW_STRIP    1u   /* segments as bands, left edge red, right edge green */
#define GRASS_VIEW_NORMALS  2u   /* the normal the light sees, as a color */

/* One blade. std430, set 1 binding 0, read by the vertex shader with gl_InstanceIndex. */
struct GrassBlade
{
    vec4 rootAndFacing;   /* xz: where it grows, world metres; y: unused, the vertex shader asks the
                             terrain; w: facing, radians about +Y */
    vec4 shape;           /* x height (m), y width at the root (m), z tilt 0..1, w bend 0..1 */
};

/* Everything the panel edits. std140, set 1 binding 1, one buffer per frame in flight. */
struct GrassParameters
{
    vec4 rootColor;       /* linear rgb: the panel's sRGB, converted on the CPU */
    vec4 tipColor;        /* linear rgb */
    vec4 groundColor;     /* linear rgb */
    vec4 terrainShape;    /* x amplitude (m), y wavelength (m), zw unused */
    uint debugView;       /* GRASS_VIEW_* */
    uint padding0;
    uint padding1;
    uint padding2;
};

/* Push constants, vertex stage, shared by both pipelines; each reads what it needs. */
struct GrassPush
{
    vec4 terrainGrid;     /* xy: world xz of the grid's corner, z: cell size (m), w: cells per side */
};

#ifdef __cplusplus
    static_assert(sizeof(GrassBlade) == 32, "GrassBlade layout drifted.");
    static_assert(sizeof(GrassParameters) == 80, "GrassParameters layout drifted.");
    static_assert(offsetof(GrassParameters, debugView) == 64, "GrassParameters alignment drifted.");
    static_assert(sizeof(GrassPush) == 16, "GrassPush layout drifted.");
    }
#endif

#endif
```

Each of the three structs answers a different question.

**`GrassBlade` — what makes one blade different from another.** Five numbers
describe a blade, and they are all the vertex shader needs to build it:

- where it grows (**x**, **z**) and the direction it **faces**;
- its **height** and its **width** at the root, in metres;
- its **tilt**, how far it leans from upright: 0 stands straight, 1 lies flat;
- its **bend**, how much it arches over: 0 is a straight blade, 1 a strong curve.

Section 6 turns these into a curve. Packed into two `vec4`s the struct is
32 bytes, identical in C++ and std430, with no padding to get wrong (Chapter 08
section 8). The root's **y** is deliberately left unused: the vertex shader asks
the terrain how high the ground is (section 5). The CPU does not know the
terrain's shape and never needs to. Chapter 27 adds a third `vec4`.

**`GrassParameters` — what the panel edits.** Colors, the terrain's shape, and
which debug view to draw. It changes when the panel changes, so it is a uniform
buffer rewritten every frame, one per frame in flight (Chapter 08 section 6).
The colors are **linear**: the panel shows sRGB swatches, and the CPU converts
them before they are written (Chapter 08 section 4). The three `padding` words
round the struct to a multiple of 16 bytes so that Chapter 26 can append `vec4`s
after it without breaking std140's alignment rules; the `static_assert`s catch
any drift between the two languages.

**`GrassPush` — what differs between draws in one frame.** Only the ground uses
it in this chapter: where its grid starts and how big a cell is (section 3).
Push constants are the place for values that change between two draws with the
same pipeline layout; Chapter 26 adds a field the blade draws use.

### The blades: a jittered grid, uploaded once

**This is `CreateBlades`.** Forty thousand blades on a 20 × 20 m square, one in
every 10 cm cell, at a random spot inside its cell:

```cpp
InitializationResult GrassDemo::CreateBlades()
{
    // A fixed seed: the same field every run, so screenshots can be compared.
    std::mt19937                          random(1234u);
    std::uniform_real_distribution<float> unit(0.0f, 1.0f);

    std::vector<GrassBlade> blades;
    blades.reserve(PATCH_SIDE * PATCH_SIDE);
    const float start = -0.5f * BLADE_SPACING * static_cast<float>(PATCH_SIDE);
    for (uint32_t z = 0; z < PATCH_SIDE; ++z)
    {
        for (uint32_t x = 0; x < PATCH_SIDE; ++x)
        {
            // One blade somewhere in each cell: a jittered grid, never a clump or a gap.
            const float rootX = start + (static_cast<float>(x) + unit(random)) * BLADE_SPACING;
            const float rootZ = start + (static_cast<float>(z) + unit(random)) * BLADE_SPACING;
            blades.push_back(GrassBlade{
                .rootAndFacing = { rootX, 0.0f, rootZ, unit(random) * 6.2831853f },
                .shape         = { 0.35f + 0.35f * unit(random),     // height, metres
                                   0.035f + 0.02f * unit(random),    // width, metres
                                   0.10f + 0.35f * unit(random),     // tilt
                                   0.10f + 0.40f * unit(random) },   // bend
            });
        }
    }
    m_bladeCount = static_cast<uint32_t>(blades.size());

    // Written once and read by the GPU ever after: device-local, filled through a
    // staging buffer the way Chapter 11 section 6 fills a mesh.
    const VkDeviceSize size    = sizeof(GrassBlade) * blades.size();
    AllocatedBuffer    staging = createBuffer(m_context.vulkan, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, true);
    m_blades = createBuffer(m_context.vulkan, size,
                            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, false);
    if (staging.buffer == VK_NULL_HANDLE || m_blades.buffer == VK_NULL_HANDLE)
    {
        destroyBuffer(m_context.vulkan, staging);
        return InitializationResult::failure("Creating the blade buffer failed.");
    }
    std::memcpy(staging.mapped, blades.data(), static_cast<size_t>(size));
    vmaFlushAllocation(m_context.vulkan.allocator, staging.allocation, 0, VK_WHOLE_SIZE);
    immediateSubmit(m_context.vulkan, [&](VkCommandBuffer commandBuffer) {
        const VkBufferCopy region{ .srcOffset = 0, .dstOffset = 0, .size = size };
        vkCmdCopyBuffer(commandBuffer, staging.buffer, m_blades.buffer, 1, &region);
        // The copy's writes, visible to the vertex shader in every later submission.
        const VkMemoryBarrier2 uploaded{
            .sType         = VK_STRUCTURE_TYPE_MEMORY_BARRIER_2,
            .srcStageMask  = VK_PIPELINE_STAGE_2_COPY_BIT,
            .srcAccessMask = VK_ACCESS_2_TRANSFER_WRITE_BIT,
            .dstStageMask  = VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT,
            .dstAccessMask = VK_ACCESS_2_SHADER_STORAGE_READ_BIT,
        };
        const VkDependencyInfo dependency{
            .sType              = VK_STRUCTURE_TYPE_DEPENDENCY_INFO,
            .memoryBarrierCount = 1,
            .pMemoryBarriers    = &uploaded,
        };
        vkCmdPipelineBarrier2(commandBuffer, &dependency);
    });
    destroyBuffer(m_context.vulkan, staging);   // immediateSubmit waited: the copy is done

    // Rewritten every frame from the panel: one per frame in flight (Chapter 08 section 6).
    for (AllocatedBuffer& parameters : m_parameterBuffers)
    {
        parameters = createBuffer(m_context.vulkan, sizeof(GrassParameters),
                                  VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, true);
        if (parameters.buffer == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a grass parameter buffer failed.");
        }
    }
    return InitializationResult::success();
}
```

Why each choice:

- **A jittered grid, not uniform random positions.** Points scattered uniformly
  at random clump and leave holes — that is what "random" looks like, and it does
  not look like a lawn. One point per cell, jittered inside the cell, gives even
  coverage with no visible pattern. *Ghost of Tsushima* lays its blades out the
  same way; Chapter 27 adds clumps on purpose, with control over where.
- **A fixed seed.** The same field every run, so a screenshot taken before a
  change can be compared with one taken after.
- **The shape ranges** — 35-70 cm tall, 3.5-5.5 cm wide, a little tilt, a little
  bend — are a meadow's, and the panel will not edit them in this chapter. They
  become `shapeMin` and `shapeMax` in Chapter 26.
- **A staging copy with a barrier**: Chapter 11 section 6's mesh upload, with
  the vertex shader instead of vertex input as the reader. Chapter 11 explains
  why the barrier is needed although `immediateSubmit` waits on a fence; note
  that synchronization validation will not report it missing. Chapter 26 replaces
  the upload with blades the GPU generates, so this is its only use here. Its
  cookbook row:

| Transition | srcStage / srcAccess | dstStage / dstAccess | Layout |
| --- | --- | --- | --- |
| Storage buffer upload, ready for the vertex shader | `COPY` / `TRANSFER_WRITE` | `VERTEX_SHADER` / `SHADER_STORAGE_READ` | — (buffers; a `VkMemoryBarrier2`) |

The same function creates the parameter buffers — host-visible, mapped, one per
frame in flight, because the CPU rewrites one every frame while the GPU may
still be reading the other.

### Set 1

The blades and the parameters are the grass's descriptor set. **Set 0 stays the
scene renderer's** (camera, lights, shadows; Chapter 10 section 7), and the
grass takes **set 1**, the slot meshes use for their material (Chapter 15
section 7): the grass is, in effect, its own material, so the numbering keeps
meaning what it means everywhere else.

**This is `CreateDescriptors`:**

```cpp
InitializationResult GrassDemo::CreateDescriptors()
{
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding         = 0,   // the blades
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_VERTEX_BIT },
        { .binding         = 1,   // the parameters
          .descriptorType  = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT },
    };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 2,
        .pBindings    = bindings,
    };
    if (vkCreateDescriptorSetLayout(m_context.vulkan.device, &setLayoutInfo, nullptr, &m_grassSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the grass.");
    }

    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, FRAMES_IN_FLIGHT },
        { VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, FRAMES_IN_FLIGHT },
    };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = FRAMES_IN_FLIGHT,
        .poolSizeCount = 2,
        .pPoolSizes    = poolSizes,
    };
    if (vkCreateDescriptorPool(m_context.vulkan.device, &poolInfo, nullptr, &m_descriptorPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the grass.");
    }

    std::array<VkDescriptorSetLayout, FRAMES_IN_FLIGHT> layouts;
    layouts.fill(m_grassSetLayout);
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_descriptorPool,
        .descriptorSetCount = FRAMES_IN_FLIGHT,
        .pSetLayouts        = layouts.data(),
    };
    if (vkAllocateDescriptorSets(m_context.vulkan.device, &allocateInfo, m_grassSets.data()) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the grass.");
    }

    // Both sets point at the one blade buffer; each at its own frame's parameters.
    for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
    {
        const VkDescriptorBufferInfo bladeInfo{ .buffer = m_blades.buffer, .offset = 0, .range = VK_WHOLE_SIZE };
        const VkDescriptorBufferInfo parameterInfo{
            .buffer = m_parameterBuffers[i].buffer, .offset = 0, .range = sizeof(GrassParameters) };
        const VkWriteDescriptorSet writes[] = {
            { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
              .dstSet          = m_grassSets[i],
              .dstBinding      = 0,
              .descriptorCount = 1,
              .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
              .pBufferInfo     = &bladeInfo },
            { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
              .dstSet          = m_grassSets[i],
              .dstBinding      = 1,
              .descriptorCount = 1,
              .descriptorType  = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
              .pBufferInfo     = &parameterInfo },
        };
        vkUpdateDescriptorSets(m_context.vulkan.device, 2, writes, 0, nullptr);
    }
    return InitializationResult::success();
}
```

Binding 0 is read by the vertex stage only; binding 1 by both stages, because
the fragment shader reads the colors and the debug view. Two sets, one per frame
in flight: both point at the one blade buffer, which never changes after
`Setup`, and each at its own frame's parameter buffer, so writing frame N+1's
parameters cannot change what frame N is still drawing with.

### Writing a frame's data

**This is `WriteFrameBuffers`**, which fills this frame's slot of every buffer
the CPU writes — set 0's frame data and lights, set 1's parameters:

```cpp
// This frame's slot of every buffer the CPU writes: set 0's frame data and lights,
// set 1's parameters. Record calls it after the fence wait (Chapter 09 section 9).
void GrassDemo::WriteFrameBuffers(uint32_t frameIndex, const glm::mat4& view, const glm::mat4& projection)
{
    const glm::vec3 sunTravel = sunTravelDirection(m_settings.sunElevation, m_settings.sunAzimuth);
    const glm::vec3 ambient{ 0.12f, 0.15f, 0.20f };   // a blue sky's fill light, linear

    shared::FrameData frameData{};
    frameData.view           = view;
    frameData.projection     = projection;
    frameData.viewProjection = projection * view;
    frameData.cameraPosition = glm::vec4(m_cameraTransform.translation, 1.0f);
    frameData.time           = m_time;
    frameData.deltaTime      = m_deltaTime;
    m_sceneRenderer.WriteFrameData(frameIndex, frameData);

    // The sun as Chapter 16's light, built by hand: a LightItem is plain data.
    const scene::LightItem sun{
        .type      = scene::LightType::Distant,
        .direction = sunTravel,
        .emission  = glm::vec3(m_settings.sunIntensity),   // a distant light's emission is irradiance
    };
    m_sceneRenderer.WriteLights(frameIndex, std::span(&sun, 1), ambient);

    const GrassParameters parameters{
        .rootColor    = glm::vec4(scene::srgbToLinear(m_settings.rootColor), 1.0f),
        .tipColor     = glm::vec4(scene::srgbToLinear(m_settings.tipColor), 1.0f),
        .groundColor  = glm::vec4(scene::srgbToLinear(m_settings.groundColor), 1.0f),
        .terrainShape = { m_settings.terrainAmplitude, m_settings.terrainWavelength, 0.0f, 0.0f },
        .debugView    = static_cast<uint>(m_settings.debugView),
    };
    std::memcpy(m_parameterBuffers[frameIndex].mapped, &parameters, sizeof(parameters));
    vmaFlushAllocation(m_context.vulkan.allocator, m_parameterBuffers[frameIndex].allocation, 0, VK_WHOLE_SIZE);
}
```

`FrameData` is Chapter 10 section 7's, field by field. The **sun** is a
Chapter 16 `LightItem` built by hand — there is no USD stage to import one from,
and a `LightItem` is plain data (Chapter 16 section 2). A distant light's
`emission` is the irradiance it delivers to a surface facing it, so the panel's
"Intensity" of 3 is three times the light a white surface needs to reach a
pixel value of 1. The ambient term is a dim blue: the sky's light, arriving from
everywhere, in the shadows too.

The sun's direction comes from two angles, which is how the panel will edit it.
**This is `sunTravelDirection`**, at file scope above the namespace block:

```cpp
// File scope, above the namespace block. The direction sunlight travels, from the
// panel's two angles: Chapter 16's convention, the reverse of "toward the sun".
static glm::vec3 sunTravelDirection(float elevationDegrees, float azimuthDegrees)
{
    const float elevation = glm::radians(elevationDegrees);
    const float azimuth   = glm::radians(azimuthDegrees);
    const glm::vec3 towardSun{ std::cos(elevation) * std::sin(azimuth),
                               std::sin(elevation),
                               -std::cos(elevation) * std::cos(azimuth) };
    return -towardSun;
}
```

Elevation is degrees above the horizon; azimuth turns from −Z (straight ahead
of the starting camera) toward +X. Chapter 16 describes a light by the
direction its light **travels** — a UsdLux light shines down its own −Z
axis — so the function builds the direction *toward* the
sun — which is how a person aims one — and returns its opposite. Get this
backwards and the lit side of everything goes dark.

Every write ends with `vmaFlushAllocation`, because VMA's host-writable memory
is not promised to be coherent (Chapter 10 section 7); on memory that is, the
flush does nothing.

### The panel

**This is `drawGrassPanel`**, a static function inside the namespace like
Chapter 21's panel. It edits `GrassSettings` directly; `WriteFrameBuffers` reads
the settings every frame, so nothing needs to be told that a slider moved:

```cpp
// The demo's panel (section 2), below Chapter 10's "Camera" window.
static void drawGrassPanel(GrassSettings& settings, uint32_t bladeCount)
{
    if (debug_panels::beginDemoPanel("Grass", debug_panels::DemoPanelSlot::BelowCamera))
    {
        ImGui::Text("Blades: %u", bladeCount);

        // The count stays in view; each group of controls folds away under its name (Chapter 09
        // section 6). The debug view comes first: nearly every check in Chapters 25-27 starts there.
        if (ImGui::CollapsingHeader("Debug"))
        {
            ImGui::Combo("View", &settings.debugView, "Shaded\0Strip\0Normals\0");
        }

        if (ImGui::CollapsingHeader("Color"))
        {
            ImGui::ColorEdit3("Root", &settings.rootColor.x);
            ImGui::ColorEdit3("Tip", &settings.tipColor.x);
            ImGui::ColorEdit3("Ground", &settings.groundColor.x);
        }

        if (ImGui::CollapsingHeader("Ground"))
        {
            ImGui::SliderFloat("Hill height (m)", &settings.terrainAmplitude, 0.0f, 2.0f);   // the stones reach 2 m down
            ImGui::SliderFloat("Hill spacing (m)", &settings.terrainWavelength, 5.0f, 100.0f);
        }

        if (ImGui::CollapsingHeader("Sun"))
        {
            ImGui::SliderFloat("Elevation", &settings.sunElevation, 1.0f, 90.0f, "%.0f deg");
            ImGui::SliderFloat("Azimuth", &settings.sunAzimuth, 0.0f, 360.0f, "%.0f deg");
            ImGui::SliderFloat("Intensity", &settings.sunIntensity, 0.0f, 10.0f);
        }
    }
    ImGui::End();
}
```

The colors are edited as sRGB, because that is what the swatches show and what
a person picks by eye; `WriteFrameBuffers` converts them with Chapter 11's
`scene::srgbToLinear`. The debug views do not do anything until sections 4 and
7 give the shaders something to show. The window opens below Chapter 10's
"Camera" panel, where the other demos put theirs, and its groups start closed:
click a group's name to open it (Chapter 09 section 6). **Add the call to `Update`**,
after the camera panel:

```cpp
    drawGrassPanel(m_settings, m_bladeCount);
```

**This is `Record`, grown:** the view and projection are computed first, and
the frame's buffers written before anything is recorded that could read them.
Replace the top of section 1's `Record` with:

```cpp
void GrassDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const uint32_t        frameIndex    = frame.frameIndex;

    const VkExtent2D extent    = frame.targets.extent;
    const float     aspect     = static_cast<float>(extent.width) / static_cast<float>(extent.height);
    const glm::mat4 view       = scene::viewMatrix(m_cameraTransform.Matrix());
    const glm::mat4 projection = m_camera.Projection(aspect);
    WriteFrameBuffers(frameIndex, view, projection);
```

`Record` runs after the frame's fence wait (Chapter 09 section 9), which is what
makes it safe to overwrite this frame slot's buffers. The aspect ratio comes
from the targets each frame, so a resize needs nothing from the demo.

Add the two calls to `Setup`, after the scene renderer:

```cpp
    if (auto result = CreateBlades(); !result)      { return result; }   // section 2
    if (auto result = CreateDescriptors(); !result) { return result; }   // section 2
```

The picture has not changed — nothing draws yet — but the run should still be
free of validation messages, which is worth checking now: a wrong descriptor
type or pool size shows up here, not later.

---

## 3. The ground

Grass grows on something, and a flat floor would hide half of what the blades
have to get right: standing upright on a slope, catching light that comes over
a ridge. So the ground comes before the blades, and it gets its shape from one
function.

### One function for the ground's shape

**This is `Shaders/Grass/Terrain.glsl`**, an include (no stage in its name, so
Chapter 06's glob does not compile it on its own):

```glsl
// Shaders/Grass/Terrain.glsl - the ground's shape. Everything that stands on the
// ground includes this file, so the blades and the terrain cannot disagree.
#ifndef PF_GRASS_TERRAIN_GLSL
#define PF_GRASS_TERRAIN_GLSL

// Three sine ridges at unrelated angles: rolling hills with no repeat you can
// spot. The weights add up to 1.75, so the height never leaves [-amplitude, amplitude].
float terrainHeight(vec2 xz, vec4 shape)
{
    vec2  p = xz * (6.2831853 / shape.y);   // shape.y: wavelength, metres
    float h = sin(p.x) * cos(0.8 * p.y)
            + 0.50 * sin(1.7 * p.x + 1.3 * p.y + 1.0)
            + 0.25 * sin(-2.9 * p.x + 3.1 * p.y + 2.0);
    return shape.x * h / 1.75;               // shape.x: amplitude, metres
}

// The slope from four nearby heights (central differences). Across 2e in x the
// ground rises dx, and the upward perpendicular to that slope is (-dx, 2e); the
// same in z gives -dz (Chapter 25 section 3).
vec3 terrainNormal(vec2 xz, vec4 shape)
{
    const float e = 0.05;   // metres; far smaller than any ridge
    float dx = terrainHeight(xz + vec2(e, 0.0), shape) - terrainHeight(xz - vec2(e, 0.0), shape);
    float dz = terrainHeight(xz + vec2(0.0, e), shape) - terrainHeight(xz - vec2(0.0, e), shape);
    return normalize(vec3(-dx, 2.0 * e, -dz));
}

#endif
```

Three sine waves at unrelated angles and frequencies add up to rolling hills
with no repeat the eye can find. `terrainShape.x` is the amplitude — how high
the hills are — and `terrainShape.y` the wavelength, how far apart; both are on
the panel. The weights add up to 1.75, so dividing by it keeps the height
inside `[-amplitude, amplitude]`, which section 8's stones and Chapter 26's
culling both rely on.

The normal comes from the same function, by **central differences**. Ask for
the height a step `e` = 5 cm either side of the point in x: across a run of
`2e` the ground rises by `dx`, so the slope along x is the arrow `(2e, dx)` —
run, then rise. The arrow at right angles to it that points up is `(-dx, 2e)`:
swap the two numbers and negate the first. Their dot product,
`2e·(-dx) + dx·2e`, is 0, which is what "at right angles" means.

```text
   side view: x to the right, y up

               normal (-dx, 2e)
               ↖
                 ↖                     ● height at x + e
                   ↖          ____---  ┐
                     ↖ ____---         │ dx
     height at x - e ●--               ┘
                     └──── 2e ─────────┘
                       slope (2e, dx)
```

The same step in z gives `-dz` in the third slot, and the normal is
`normalize(vec3(-dx, 2e, -dz))`. In numbers: if the ground rises 2 cm across
the 10 cm step in x and is level in z, the normal is
`normalize(-0.02, 0.1, 0)` = `(-0.20, 0.98, 0)`, tipped about 11° from straight
up, away from the rise. On flat ground `dx` and `dz` are 0 and the normal is
straight up. No normal is stored anywhere.

**Why a function, and why in its own file.** Two different shaders need the
ground's height: the terrain's vertex shader, to build the ground, and the
blade's vertex shader, to stand each blade on it (section 5). If they asked two
different sources, every disagreement would be a blade floating or sunk. With
one function in one include, they cannot disagree. *Ghost of Tsushima* reads
the height from the terrain's own height texture, per tile; this
demo has no terrain system, and a function plays the same role — Chapter 26's
compute shader calls it exactly where the game would sample that texture.

### A square of ground from `gl_VertexIndex`

The ground is a grid of quads, and like the blades it is built in the vertex
shader with no vertex buffer — Chapter 11 section 1's idea, a mesh whose
vertices are a formula of their index.

**This is `Shaders/Grass/Terrain.vert.glsl`:**

```glsl
// Shaders/Grass/Terrain.vert.glsl - a square of ground made from gl_VertexIndex.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"
#include "GrassTypes.h"
#include "Terrain.glsl"

layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };
layout(push_constant) uniform GrassPushBlock { GrassPush push; };

layout(location = 0) out vec3 worldPosition;

// Two triangles per cell, counter-clockwise seen from above.
const vec2 corners[6] = vec2[](
    vec2(0.0, 0.0), vec2(0.0, 1.0), vec2(1.0, 0.0),
    vec2(1.0, 0.0), vec2(0.0, 1.0), vec2(1.0, 1.0));

void main()
{
    uint cellsPerSide = uint(push.terrainGrid.w);
    uint cell         = uint(gl_VertexIndex) / 6u;
    vec2 cellXZ       = vec2(cell % cellsPerSide, cell / cellsPerSide);
    vec2 xz           = push.terrainGrid.xy + (cellXZ + corners[gl_VertexIndex % 6]) * push.terrainGrid.z;

    worldPosition = vec3(xz.x, terrainHeight(xz, grass.terrainShape), xz.y);
    gl_Position   = frame.viewProjection * vec4(worldPosition, 1.0);
}
```

Each cell is two triangles, six vertices. Vertex `i` belongs to cell `i / 6`,
which is at column `cell % cellsPerSide` and row `cell / cellsPerSide`, and is
corner `i % 6` of it. The push constant says where the grid starts, how big a
cell is, and how many cells make a side, so the same shader can draw the ground
anywhere — Chapter 26 moves it with the camera. The six corners are listed so
both triangles run **counter-clockwise seen from above**, the winding Chapter 11
section 7 made the front for every mesh: with back-face culling on, the
ground is drawn from above and invisible from below.

Shared corners are computed twice, once for each triangle that uses them, where
an index buffer would compute them once. At six vertices a cell and a few sine
calls a vertex, the waste is not worth an index buffer.

**This is `Shaders/Grass/Terrain.frag.glsl`:**

```glsl
// Shaders/Grass/Terrain.frag.glsl
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"
#include "Lights.glsl"
#include "Shadows.glsl"
#include "GrassTypes.h"
#include "Terrain.glsl"

layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };

layout(location = 0) in  vec3 worldPosition;
layout(location = 0) out vec4 outColor;

const float PI = 3.14159265;

void main()
{
    // Per pixel, from the same function the vertices used: smoother than
    // interpolating a normal per vertex, and nothing to store.
    vec3 normal = terrainNormal(worldPosition.xz, grass.terrainShape);
    vec3 albedo = grass.groundColor.rgb;

    float viewDepth = -(frame.view * vec4(worldPosition, 1.0)).z;   // Chapter 17's cascade choice
    vec3 color = albedo * lightHeader.ambient.rgb;
    if (lightHeader.sunIndex >= 0)
    {
        vec3  L;
        vec3  irradiance = lightIrradiance(lights[lightHeader.sunIndex], worldPosition, L);
        float shadow     = sunShadow(worldPosition, normal, viewDepth);
        color += albedo / PI * irradiance * max(dot(normal, L), 0.0) * shadow;
    }
    outColor = vec4(color * cascadeDebugColor(viewDepth), 1.0);   // white unless "Show cascades" is on
}
```

The lighting is Chapter 11 section 14's Lambert, with Chapter 16's light and
Chapter 17's shadow plugged in: ambient everywhere, plus the sun's irradiance
times the cosine of its angle to the surface, times whether the sun can see the
point. `albedo / π` is the Lambertian BRDF — the `π` is what makes a white
surface reflect exactly the light that reaches it, no more. The normal is
recomputed per pixel from `Terrain.glsl` rather than interpolated from the
vertices: smoother, and nothing to pass between stages.

The view depth is worked out before the sun's block because two things use it:
`sunShadow`, to pick a cascade, and the last line's `cascadeDebugColor`,
Chapter 17 section 13's tint — white unless the "Shadows" panel's "Show
cascades" is on — which the mesh shader applies the same way, so the ground
shows the cascades like everything else.

`sunShadow` reads Chapter 17's shadow map. Until section 8 records a shadow pass
the map's flags say "off" and `sunShadow` returns 1 — Chapter 17 sections 5 and
6 leave the map in a state that is valid to read even if no pass ever runs — so
the ground is lit everywhere for now.

### The pipeline layout, and the ground's pipeline

Both of the grass's pipelines — this one and section 4's — use one layout: set
0 from the scene renderer, set 1 from section 2, and the push constant.

**This is `CreatePipelines`, as it starts:**

```cpp
InitializationResult GrassDemo::CreatePipelines()
{
    // Set 0 is the scene renderer's: camera, lights, shadows. Set 1 is the grass's.
    const std::array<VkDescriptorSetLayout, 2> setLayouts{ m_sceneRenderer.FrameSetLayout(), m_grassSetLayout };
    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT,
        .offset     = 0,
        .size       = sizeof(GrassPush),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = static_cast<uint32_t>(setLayouts.size()),
        .pSetLayouts            = setLayouts.data(),
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_pipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the grass.");
    }

    const GraphicsPipelineDesc terrain{
        .vertexShader   = "Grass/Terrain.vert.spv",
        .fragmentShader = "Grass/Terrain.frag.spv",
        .colorFormats   = { &m_context.formats.color, 1 },
        .depthFormat    = m_context.formats.depth,
        .depthTest      = true,
        .depthWrite     = true,
        .cullMode       = VK_CULL_MODE_BACK_BIT,
        .frontFace      = VK_FRONT_FACE_COUNTER_CLOCKWISE,
        .layout         = m_pipelineLayout,
        .samples        = m_context.formats.samples,
    };
    m_terrainPipeline = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, terrain);
    if (m_terrainPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the terrain pipeline failed.");
    }
    return InitializationResult::success();
}
```

Using `m_sceneRenderer.FrameSetLayout()` for set 0 is what lets
`BindFrameSet` bind the scene renderer's set into this layout (Chapter 10
section 7): two layouts that start with the same set layout are compatible up
to it. The desc is Chapter 11's with Chapter 18's `samples`: the ground is
drawn in the scene pass, so it takes the pass's color and depth formats and
its sample count, and it tests and writes depth like any opaque mesh.

Add it to `Setup`, after the descriptors (it needs `m_grassSetLayout`):

```cpp
    if (auto result = CreatePipelines(); !result)   { return result; }   // sections 3 and 4
```

**Drawing it.** In `Record`, between `beginScenePass` and `endScenePass`:

```cpp
    m_sceneRenderer.BindFrameSet(commandBuffer, m_pipelineLayout, frameIndex);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipelineLayout,
                            1, 1, &m_grassSets[frameIndex], 0, nullptr);

    // The ground: a square of TERRAIN_CELLS quads centred on the patch.
    const float     groundSide = TERRAIN_CELL * static_cast<float>(TERRAIN_CELLS);
    const GrassPush push{ .terrainGrid = { -0.5f * groundSide, -0.5f * groundSide,
                                           TERRAIN_CELL, static_cast<float>(TERRAIN_CELLS) } };
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_terrainPipeline);
    vkCmdDraw(commandBuffer, 6 * TERRAIN_CELLS * TERRAIN_CELLS, 1, 0, 0);
```

Set 0 is bound through the grass's layout — `BindFrameSet` takes the layout to
bind it with — and set 1 after it. The grid is 160 cells of 0.5 m a side, an
80 m square centred on the origin: comfortably bigger than the 20 m patch, so
the patch sits in the middle of open ground. That is 153,600 vertices with no
vertex buffer behind them.

You should see rolling olive-brown hills under the blue sky, lit from behind
your left shoulder — the default sun is 35° up, at an azimuth of 230°, so the
slopes that face you are the bright ones. Drag "Hill height" to 0 and the
ground goes flat; drag "Hill spacing" down and the hills crowd together.

---

## 4. One blade from fifteen vertices

Now the subject of the chapter. A blade is a thin strip that narrows to a point.
*Ghost of Tsushima*'s near blades have **15 vertices**; this
section builds exactly that, standing straight at one spot, and the next three
sections give it a place, a curve, and light.

### The strip

Fifteen vertices make **seven pairs and a tip**. Each pair is the blade's left
and right edge at one height; consecutive pairs make a quad of two triangles;
the last pair and the tip make the final triangle. Numbered:

```text
   14            tip                     vertex i:  segment = i / 2   (0 .. 7)
  12  13                                            side    = i odd ? right : left
  10  11                                            t       = segment / 7, root 0 to tip 1
   8   9
   6   7         each quad between two pairs is two triangles;
   4   5         the strip makes them from the order alone
   2   3
   0   1         root
```

That is exactly what a **triangle strip** draws. In a strip, every vertex after
the first two makes a triangle with the two before it: (0, 1, 2), (1, 2, 3),
(2, 3, 4), and so on up to (12, 13, 14). Fifteen vertices give thirteen
triangles, and each vertex is shaded once. As a triangle *list* the same blade
needs 39 vertices, each pair shaded up to three times.

A strip alternates the order of its triangles' vertices — (0, 1, 2) runs one
way round, (1, 2, 3) the other — and Vulkan compensates by treating every
second triangle as if its first two vertices were swapped, so the whole strip
has the winding of its first triangle. That matters in section 7, where the
fragment shader asks which side of the blade it is looking at.

> **Jump:** every pipeline so far has drawn **triangle lists**, so the topology
> was hard-coded in Chapter 06's `createGraphicsPipeline`. A strip is a
> different way of reading the same vertex stream, and it is a pipeline
> property, so `GraphicsPipelineDesc` grows one more field. Keep in mind that
> a strip is a *primitive topology*, not a mesh format: the vertex shader is
> unchanged in kind — it still turns `gl_VertexIndex` into a position — and
> only the way consecutive vertices are grouped into triangles differs. Each
> **instance** starts a new strip, so the next section's forty thousand blades
> never join into one long ribbon, with no primitive restart needed.

**This is the `GraphicsPipelineDesc` change**, in
`Source/PillowFort/VulkanGraphics/GraphicsPipeline.h`. The field goes **at the
end**, after Chapter 18's two, so every existing designated initializer, which
must name fields in declaration order, still compiles:

```cpp
    VkPrimitiveTopology         topology        = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;   // Chapter 25: strips for grass blades
```

and in `GraphicsPipeline.cpp`, Chapter 06 section 4's input-assembly state
stops hard-coding the list:

```cpp
    const VkPipelineInputAssemblyStateCreateInfo inputAssembly{
        .sType    = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
        .topology = desc.topology,
    };
```

The default keeps every existing pipeline a triangle list.
`primitiveRestartEnable` stays false: restart is for joining several strips in
one *indexed* draw, and here instancing separates them.

### The shader

**This is `Shaders/Grass/Grass.vert.glsl`, as it starts:** one blade, half a
metre tall and 5 cm wide, standing on the ground at the origin.

```glsl
// Shaders/Grass/Grass.vert.glsl - one blade, built from gl_VertexIndex (section 4).
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"
#include "GrassTypes.h"
#include "Terrain.glsl"

layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };

layout(location = 2) out float bladeT;        // 0 at the root, 1 at the tip
layout(location = 3) out float bladeSide;     // -1 on the left edge, +1 on the right

const uint SEGMENTS = 7u;   // 7 pairs of vertices and a tip: 15 vertices

void main()
{
    // Which vertex of the strip this is: a pair per segment, then the tip.
    uint  segment = uint(gl_VertexIndex) / 2u;                // 0 .. SEGMENTS
    float side    = (gl_VertexIndex & 1) == 0 ? -1.0 : 1.0;    // left, right
    float t       = float(segment) / float(SEGMENTS);

    // For now one blade, half a metre tall, standing on the ground at the origin.
    float height    = 0.5;
    float width     = 0.05;
    vec3  root      = vec3(0.0, terrainHeight(vec2(0.0), grass.terrainShape), 0.0);
    float halfWidth = 0.5 * width * (1.0 - t * t);             // full width low down, a point at the tip

    vec3 position = root + vec3(side * halfWidth, t * height, 0.0);
    bladeT        = t;
    bladeSide     = side;
    gl_Position   = frame.viewProjection * vec4(position, 1.0);
}
```

Three lines carry the idea:

- **`segment` and `side`** decode the vertex number into the diagram above:
  integer division by two gives the height step, the lowest bit the edge. The
  tip, vertex 14, comes out as segment 7 on the left edge, and since the width
  there is zero, which edge does not matter.
- **`t`** runs from 0 at the root to 1 at the tip. It is the one coordinate
  everything along the blade is a function of: position now, the curve in
  section 6, color in section 7.
- **`halfWidth`** is `1 - t²`: almost the full width for the lower half of the
  blade, then a fast taper into the point. A linear taper, `1 - t`, makes a
  narrow triangle that reads as a spike rather than a leaf.

The outputs start at location 2 because section 7 adds two more in front of
them (the world position and the normal); numbering them now means nothing has
to move later.

**This is `Shaders/Grass/Grass.frag.glsl`, as it starts**, unlit:

```glsl
// Shaders/Grass/Grass.frag.glsl - unlit for now (section 4); section 7 lights it.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "GrassTypes.h"

layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };

layout(location = 2) in  float bladeT;
layout(location = 3) in  float bladeSide;
layout(location = 0) out vec4  outColor;

void main()
{
    if (grass.debugView == GRASS_VIEW_STRIP)
    {
        float band = fract(bladeT * 7.0 + 0.001) < 0.5 ? 1.0 : 0.6;
        outColor = vec4(band * (bladeSide < 0.0 ? vec3(0.9, 0.1, 0.1) : vec3(0.1, 0.9, 0.1)), 1.0);
        return;
    }
    outColor = vec4(mix(grass.rootColor.rgb, grass.tipColor.rgb, bladeT), 1.0);
}
```

The **Strip** debug view is how you check the vertex decoding without trusting
the shading: each segment is a band, alternating bright and dark, and the left
half of the blade is red, the right half green (`bladeSide` is interpolated
across each triangle, so it changes sign down the middle). Seven bands, red on
the left, green on the right, a point at the top: the strip is right. The
`+ 0.001` keeps a band boundary that lands exactly on a vertex from flickering
between the two colors.

### The pipeline

**In `CreatePipelines`**, the blade's desc goes after the ground's:

```cpp
    const GraphicsPipelineDesc blades{
        .vertexShader   = "Grass/Grass.vert.spv",
        .fragmentShader = "Grass/Grass.frag.spv",
        .colorFormats   = { &m_context.formats.color, 1 },
        .depthFormat    = m_context.formats.depth,
        .depthTest      = true,
        .depthWrite     = true,
        .cullMode       = VK_CULL_MODE_NONE,                       // sections 4 and 7: both faces
        .frontFace      = VK_FRONT_FACE_COUNTER_CLOCKWISE,
        .layout         = m_pipelineLayout,
        .samples        = m_context.formats.samples,
        .topology       = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_STRIP,    // section 4
    };
```

and the creation at the end makes both pipelines and checks both:

```cpp
    m_terrainPipeline = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, terrain);
    m_grassPipeline   = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, blades);
    if (m_terrainPipeline == VK_NULL_HANDLE || m_grassPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating a grass pipeline failed.");
    }
```

Two fields differ from the ground's:

- **`topology`**: the strip.
- **`cullMode = NONE`.** A blade is one sheet with nothing behind it, seen from
  either side as the wind and the camera turn it. With back-face culling, every
  blade whose back faced the camera would vanish — about half of them, at
  random. Section 7 makes the back face *look* right; here it only has to be
  drawn. `frontFace` is still set, because section 7's `gl_FrontFacing` is
  decided by it.

**Drawing one blade.** In `Record`, after the ground:

```cpp
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_grassPipeline);
    vkCmdDraw(commandBuffer, 15, 1, 0, 0);
```

The pipeline layout is the ground's, so the sets and the push constant bound
for the ground are still bound.

Fly forward a few metres (W) until a thin pale-green spike stands on the hill in
front of you; set the panel's View to **Strip** and it becomes seven red and
green bands.

---

## 5. Forty thousand blades

One blade becomes many the way Chapter 19 drew four thousand trees: one draw
with an instance count, and per-instance data in a storage buffer that the
vertex shader indexes with `gl_InstanceIndex`. Here the instance *is* the blade
— there is no mesh behind it at all — and the per-instance data is section 2's
`GrassBlade`.

**This is how `Grass.vert.glsl` grows:** the blade's numbers come from the
buffer, and its own frame from its facing. Three changes to section 4's shader.

The blade buffer is declared beside the parameters, after the includes:

```glsl
layout(set = 1, binding = 0, std430) readonly buffer BladeBlock { GrassBlade blades[]; };
```

`main` starts by reading this instance's blade:

```glsl
    GrassBlade blade = blades[gl_InstanceIndex];
```

and section 4's fixed blade — from `// For now one blade` to the `position`
line — becomes the blade's own frame and its root on the ground:

```glsl
    // The blade's own frame. front is where its face looks; right runs across it.
    float facing = blade.rootAndFacing.w;
    vec3  up     = vec3(0.0, 1.0, 0.0);
    vec3  front  = vec3(sin(facing), 0.0, cos(facing));
    vec3  right  = cross(up, front);                           // across the blade

    float height = blade.shape.x;
    float width  = blade.shape.y;

    vec3 root = vec3(blade.rootAndFacing.x, 0.0, blade.rootAndFacing.z);
    root.y    = terrainHeight(root.xz, grass.terrainShape);

    float halfWidth = 0.5 * width * (1.0 - t * t);             // full width low down, a point at the tip
    vec3  position  = root + up * t * height + right * side * halfWidth;
```

What changed, and why:

- **`blades[gl_InstanceIndex]`.** Every one of an instance's fifteen vertices
  reads the same blade. The buffer is `readonly`, which a storage buffer read by
  a vertex shader must be (Chapter 20 section 10: writing one from the vertex
  stage needs a feature the tutorial does not enable).
- **The blade's own frame.** `facing` is an angle about the vertical. `front`
  is the horizontal direction the blade's face looks toward, and `right =
  up × front` runs across it, so the width is laid along `right` and the height
  along `up`. With a facing of 0, `front` is +Z, and Chapter 12 section 5's
  formula gives `cross((0,1,0), (0,0,1))` = `(1·1 − 0·0, 0·0 − 0·1, 0·0 − 1·0)`
  = `(1, 0, 0)`: `right` is +X, and the blade is section 4's exactly. Random
  facings are what keep a field from looking combed.
- **The root on the ground.** The buffer says where in x and z; the height comes
  from `Terrain.glsl`, the function the ground was built from, so every blade
  stands exactly on the surface you see. Move the "Hill height" slider and the
  blades ride up and down with the ground, because neither has a stored height.

**And in `Record`**, the draw asks for every blade:

```cpp
    // The blades: 15 vertices each, one instance per blade.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_grassPipeline);
    vkCmdDraw(commandBuffer, 15, m_bladeCount, 0, 0);
```

That is 600,000 vertices, and per-blade work — reading the blade, building its
frame, asking the terrain — is repeated by each of a blade's fifteen vertices.
It costs a GPU nothing it would notice at this count. Chapter 26 moves the
per-blade part into a compute pass anyway, where it is done once per blade, and
at a hundred times the blades it starts to matter.

You should see a field of straight, pale-green spikes, darker at the root and
lighter at the tip, covering the hill in front of the camera and ending sharply
at the patch's edges, ten metres either side of the origin. It looks like a
brush, not grass: real blades lean and curve.

## Checkpoint

The field exists: forty thousand blades, each built by the vertex shader from
two `vec4`s, standing on the ground wherever the hills put it, and View
**Strip** shows how each one is decoded. Sections 6-8 give the blades their
shape, their light, and their shadows.

---

## 6. The curve

A real blade is a leaf that leans away from its root and arches over under its
own weight. The shape to give it needs to be smooth, controllable with a few
numbers, and cheap to evaluate at any point along its length — every vertex
asks "where am I at my `t`?". A cubic Bézier curve is all three, and it is what
*Ghost of Tsushima*'s blades are.

> **Jump:** this is the one new piece of mathematics in the chapter.
> A **cubic Bézier curve** is defined by four control points, `P0` to `P3`:
>
> `B(t) = (1-t)³ P0 + 3(1-t)²t P1 + 3(1-t)t² P2 + t³ P3`, for `t` from 0 to 1.
>
> Read it as a **weighted average** of the four points whose weights slide along
> as `t` grows: at `t = 0` all the weight is on `P0`, at `t = 1` all of it on
> `P3`, and in between the middle two pull the curve toward themselves without
> it passing through them. Three properties are all the grass needs. The curve
> **starts at `P0` and ends at `P3`**, so the root stays put and the tip is
> where you say. It **leaves `P0` heading toward `P1` and arrives at `P3` coming
> from `P2`**, so the inner two points set how it bends. And the four weights
> are never negative and always add up to 1, so the curve **never leaves the
> box around its four points** — Chapters 26 and 27 use that to bound a blade
> for culling without evaluating it. Keep in mind that the blade's height is
> now the distance from `P0` to `P3`, not the length along the curve.

### Four points from tilt and bend

The blade's numbers become control points in the vertical plane that contains
its facing. Two directions in that plane describe the shape:

```text
          up
           │      arch (perpendicular to chord, away from the ground)
           │     ╱
       P3 ●    ╱            chord: from the root toward the tip, leaning back by
         ╱  ●P2                    tilt × 90° from upright
        ╱  ●P1              P1, P2: a third and two thirds of the way along the
       ╱ ╱                          chord, pushed out along arch by bend × height / 2
  P0 ●───────────── back    P3: the tip, height along the chord
   (root)
```

- **`chord`** runs from the root toward where the tip will be. `tilt` leans it
  from straight up (`tilt = 0`) toward lying flat along `back` (`tilt = 1`),
  the direction opposite the blade's face.
- **`arch`** is perpendicular to the chord, on the side away from the ground.
- **`P1` and `P2`** sit at a third and two thirds of the way along the chord,
  so with `bend = 0` all four points lie on one line and the "curve" is that
  straight line: a stiff, leaning blade. **`bend`** pushes the middle two out
  along `arch`, by up to half the blade's height, and the blade arches over.

Two checks with numbers. At `tilt = 0`, `lean` is 0, so `chord` = `up` and
`arch` = `−back` = `front`: an upright blade bows toward its face. At
`tilt = 1`, `lean` is 90°, so `chord` = `back` and `arch` = `up`: a blade lying
flat bows toward the sky. In between, the two stay at right angles.

Leaning toward `back` means the blade's face — the side `front` looks out of —
tilts up toward the sky as the blade leans. That is the side that catches the
sun, and the one section 7's normal points out of.

**This is how `Grass.vert.glsl` grows again.** The curve is a function of its
own, before `main`:

```glsl
// The cubic Bezier curve: a weighted average of four points, the weights set by t.
vec3 bezier(vec3 p0, vec3 p1, vec3 p2, vec3 p3, float t)
{
    float s = 1.0 - t;
    return s * s * s * p0 + 3.0 * s * s * t * p1 + 3.0 * s * t * t * p2 + t * t * t * p3;
}
```

In `main`, the frame gains `back`, after `front`:

```glsl
    vec3  back   = -front;
```

the shape gains its other two numbers, after `width`:

```glsl
    float tilt   = blade.shape.z;
    float bend   = blade.shape.w;
```

and the `halfWidth` and `position` lines at the end become the curve: four
control points, the point on the curve at `t`, and the two edges either side of
it.

```glsl
    // Four control points in the plane of up and back. chord runs root to tip;
    // arch is perpendicular to it, on the side away from the ground.
    float lean  = tilt * 1.5707963;                            // 0 upright, 1 lying flat
    vec3  chord = cos(lean) * up + sin(lean) * back;
    vec3  arch  = sin(lean) * up - cos(lean) * back;
    vec3  p0    = root;
    vec3  p1    = root + height * (chord / 3.0       + arch * bend * 0.5);
    vec3  p2    = root + height * (chord * 2.0 / 3.0 + arch * bend * 0.5);
    vec3  p3    = root + height * chord;

    vec3  center    = bezier(p0, p1, p2, p3, t);
    float halfWidth = 0.5 * width * (1.0 - t * t);             // full width low down, a point at the tip

    vec3 position = center + right * side * halfWidth;
```

Each pair of vertices is now placed at the curve's point for its `t` and spread
across `right`, which stays horizontal: the blade is a ribbon swept along the
curve, flat side to the facing. The tip vertex lands exactly on `P3`.

The seven segments are evenly spaced in `t`, which spaces them evenly along the
*parameter*, not where the curve needs them. A blade that bends hard near the
tip shows a visible corner there. *Ghost of Tsushima* moves its vertices toward
the tip, where the bend is, and Chapter 26 does the same once it
needs a 7-vertex blade to look like the 15-vertex one.

Set View to **Strip** and fly close to a blade: the bands now follow an arch,
and the red and green halves stay on their own sides all the way up. Back on
**Shaded**, the field has turned from a brush into grass — blades leaning every
which way, some nearly upright, some arching over — but it is flat: every blade
is the same color at the same height whichever way it faces, because nothing is
lit yet.

---

## 7. Normals, two faces, and light

Light needs a normal, and a blade's normal changes along its length: upright
near the root, the face looks sideways; near an arched-over tip it looks at the
sky. The curve already knows which way it is going at every `t`, and that is
enough to find the normal.

### The tangent, and the normal from it

The **derivative** of the Bézier curve, `B'(t)`, is the direction the curve runs
at `t` — the tangent. Differentiating section 6's formula term by term and
collecting gives a curve of the same family, built from the three *differences*
between consecutive control points:

`B'(t) = 3(1-t)² (P1 - P0) + 6(1-t)t (P2 - P1) + 3t² (P3 - P2)`

Take the algebra on trust; the check that matters is this. At the root it
points from `P0` toward `P1`; at the tip from `P2` toward `P3`:
the "leaves toward `P1`, arrives from `P2`" property of section 6, in numbers.
Its length is the curve's speed, which does not matter here, because it is only
used for a direction.

The blade's surface at `t` contains two directions: along the blade (the
tangent) and across it (`right`). The normal is perpendicular to both,
`normalize(cross(right, tangent))`, and the **order of the two arguments
decides which face it comes out of**. Check it with numbers. With a facing of
0, `right` is `(1, 0, 0)` (section 5), and an upright blade's tangent is `up`,
`(0, 1, 0)`. Chapter 12 section 5's formula gives

`cross((1,0,0), (0,1,0))` = `(0·0 − 0·1, 0·0 − 1·0, 1·1 − 0·0)` = `(0, 0, 1)`

which is `front`: the normal points out of the blade's face. Swap the
arguments, `cross(tangent, right)`, and every term changes sign: `(0, 0, −1)`,
out of the back. As the blade leans back, the tangent tilts toward `back` and
the normal tilts up toward the sky with it.

**This is how `Grass.vert.glsl` is finished for this chapter.** Two outputs for
lighting, the world position and the normal, take locations 0 and 1, the ones
section 4 left free; they go before `bladeT`:

```glsl
layout(location = 0) out vec3  worldPosition;
layout(location = 1) out vec3  worldNormal;   // of the front face; the fragment shader flips it for the back
```

The derivative goes after `bezier`:

```glsl
vec3 bezierDerivative(vec3 p0, vec3 p1, vec3 p2, vec3 p3, float t)
{
    float s = 1.0 - t;
    return 3.0 * s * s * (p1 - p0) + 6.0 * s * t * (p2 - p1) + 3.0 * t * t * (p3 - p2);
}
```

`main` takes the tangent beside the point on the curve, after `center`:

```glsl
    vec3  tangent   = bezierDerivative(p0, p1, p2, p3, t);
```

and its last lines — from `position` to `gl_Position` — write the two new
outputs:

```glsl
    worldPosition = center + right * side * halfWidth;
    worldNormal   = normalize(cross(right, tangent));
    bladeT        = t;
    bladeSide     = side;
    gl_Position   = frame.viewProjection * vec4(worldPosition, 1.0);
```

The whole shader, as this chapter leaves it, is in the Appendix.

### Two faces from one triangle

A blade is one sheet. When the camera looks at its back, the normal computed
above points away from the camera, and lighting with it shades the back as if
it were the far side of a solid object — dark when the sun is in front of the
blade, lit when the sun is behind it, which is the wrong way round for what
the eye sees.

The fix is in the fragment shader: **if the fragment belongs to a back face,
flip the normal**, so the normal always points out of the side being looked at.
`gl_FrontFacing` says which side the rasterizer is drawing. It is decided by the
triangle's winding on screen and the pipeline's `frontFace`, which is why
section 4 kept `COUNTER_CLOCKWISE` although nothing is culled. Look at the
strip's first triangle from the side `front` looks out of — for a facing of 0,
from +Z, so +X is to your right and +Y up:

```text
     2 ●              vertex 0: root, left edge     (side -1)
       │ ↖            vertex 1: root, right edge    (side +1)
       │   ↖          vertex 2: one step up, left edge
       ↓     ↖
     0 ●──→───● 1     0 → 1 → 2 → 0 turns counter-clockwise
```

Seen from the front, 0 → 1 → 2 turns counter-clockwise, so "front facing" means
"looking at the face the normal points out of". The strip's alternate
triangles are flipped by Vulkan to match (section 4), so the whole blade
agrees.

Lighting the back with a flipped normal makes it behave like a second,
independent surface. Real leaves are a little more interesting than that: light
from behind shines *through* them. Chapter 27 adds that.

**This is `Shaders/Grass/Grass.frag.glsl`, complete for this chapter:**

```glsl
// Shaders/Grass/Grass.frag.glsl
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"
#include "Lights.glsl"
#include "Shadows.glsl"
#include "GrassTypes.h"

layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };

layout(location = 0) in  vec3  worldPosition;
layout(location = 1) in  vec3  worldNormal;
layout(location = 2) in  float bladeT;
layout(location = 3) in  float bladeSide;
layout(location = 0) out vec4  outColor;

const float PI = 3.14159265;

void main()
{
    // One triangle, two faces: light the face you are looking at.
    vec3 normal = normalize(worldNormal) * (gl_FrontFacing ? 1.0 : -1.0);

    if (grass.debugView == GRASS_VIEW_STRIP)
    {
        float band = fract(bladeT * 7.0 + 0.001) < 0.5 ? 1.0 : 0.6;
        outColor = vec4(band * (bladeSide < 0.0 ? vec3(0.9, 0.1, 0.1) : vec3(0.1, 0.9, 0.1)), 1.0);
        return;
    }
    if (grass.debugView == GRASS_VIEW_NORMALS)
    {
        outColor = vec4(normal * 0.5 + 0.5, 1.0);
        return;
    }

    vec3 albedo = mix(grass.rootColor.rgb, grass.tipColor.rgb, bladeT);

    float viewDepth = -(frame.view * vec4(worldPosition, 1.0)).z;   // Chapter 17's cascade choice
    vec3 color = albedo * lightHeader.ambient.rgb;
    if (lightHeader.sunIndex >= 0)
    {
        vec3  L;
        vec3  irradiance = lightIrradiance(lights[lightHeader.sunIndex], worldPosition, L);
        float shadow     = sunShadow(worldPosition, normal, viewDepth);
        color += albedo / PI * irradiance * max(dot(normal, L), 0.0) * shadow;
    }
    outColor = vec4(color * cascadeDebugColor(viewDepth), 1.0);   // white unless "Show cascades" is on
}
```

The lighting is the ground's from section 3 — ambient, plus the sun times the
cosine, times the shadow, over `π` — with the blade's normal and color:

- **The color runs from root to tip**, mixed by `t` between two linear colors
  from the panel: dark at the base, where little light reaches in a real field,
  and lighter, yellower at the tip. It is the cheapest thing that makes the
  field read as grass rather than green paper. Chapter 27 adds per-blade and
  per-clump variation and darkens the roots properly.
- **`sunShadow` gets the flipped normal**, the one facing the camera, so
  Chapter 17's normal offset pushes the lookup out of the side that is lit. The
  stones of section 8 are the first thing to cast a shadow onto the blades.
- **The cascade tint** is the ground's: the view depth is computed once, for
  `sunShadow` and for `cascadeDebugColor` on the last line.
- **The Normals view** shows the normal after the flip, as a color: `n * 0.5 +
  0.5`, so a normal along +X is pinkish, +Y light green, +Z light blue. Each blade
  should shade smoothly from root to tip with no seam down its middle and no
  sudden jump at a segment. The colors come out paler than those numbers,
  because the composite pass encodes them as if they were light; Chapter 11
  section 10 converts its debug normals first to show the raw values, and for
  judging smoothness it makes no difference.

The vertex shader's two new outputs are now read, by locations 0 and 1.

Back on **Shaded**, the field has depth: blades facing the sun are bright,
blades turned away are darker, and the arching tips catch more light than the
upright stems. The ground shows between the blades, darker than they are.

---

## 8. Stones, shadows, and teardown

Grass that receives shadows needs something to cast them. This demo does not
draw its blades into the shadow map at all — there are far too many, and they
are thinner than a shadow-map texel — and neither does *Ghost of Tsushima*. How
grass can *seem* to shade itself without that is Chapter 27 section 8. Here, two
standing stones cast shadows across the field, which exercises everything
Chapter 17 built: cascades, filtering, and the blades' normal offset.

**This is `CreateStones`:**

```cpp
void GrassDemo::CreateStones()
{
    // Two standing stones: Chapter 11's cube through the scene renderer, there to
    // throw shadows across the blades. Each runs from 2 m below the lowest the
    // ground can be to 3 m above the origin, so it stands in the ground wherever
    // the hills are - the CPU never needs to know the ground's height.
    const uint32_t material = m_sceneRenderer.AddMaterial(scene::Material{ .name = "Stone", .baseColor = { 0.25f, 0.24f, 0.22f, 1.0f } });
    const uint32_t mesh     = m_sceneRenderer.AddMesh(scene::makeCube(1.0f));
    const glm::vec3 positions[] = { { -3.5f, 0.0f, 3.5f }, { 3.0f, 0.0f, -2.5f } };
    m_stones.clear();
    for (const glm::vec3& position : positions)
    {
        const glm::mat4 world = glm::translate(glm::mat4(1.0f), position + glm::vec3(0.0f, 0.5f, 0.0f))
                              * glm::scale(glm::mat4(1.0f), glm::vec3(0.8f, 5.0f, 0.6f));
        m_stones.push_back(scene::DrawItem{ .world = world, .mesh = mesh, .submesh = 0, .material = material });
    }
}
```

A stone is Chapter 11's cube, scaled into a slab 0.8 m wide, 0.6 m deep, and 5
m tall, drawn by the scene renderer with an ordinary material — the grass's
pipelines have nothing to do with it. Its material is Chapter 15's, every field
but the name and a linear grey left at its default.

The stones go 2.5 m below and above their centre, which is lifted 0.5 m: from
−2.0 m to +3.0 m. The panel's "Hill height" stops at 2 m, so the ground is never
lower than −2 m and a stone always stands in it, wherever the hills are, and
the CPU never needs to know the ground's height. The cost is that most of the
stone is underground; nothing is drawn there that anyone sees.

**This is how `Record` is finished.** The stones are prepared and the shadows
recorded before the scene pass, after `WriteFrameBuffers`:

```cpp
    // Before the scene pass: the stones' draws (Chapter 19), drawn and casting
    // shadows, then the sun's cascades (Chapter 17).
    m_sceneRenderer.PrepareDraws(frameIndex, m_stones, m_stones);
    m_sceneRenderer.RecordShadows(commandBuffer, frameIndex, m_camera, view, aspect,
                                  m_sceneRenderer.SunDirection(frameIndex), m_shadowSettings);
```

and the stones are drawn first inside it, right after `beginScenePass`:

```cpp
    // The stones first: RecordDraws binds its own pipeline and set 0, and ours follow.
    m_sceneRenderer.RecordDraws(commandBuffer, frameIndex);
```

The order follows from what each call needs:

- **`PrepareDraws`** (Chapter 19) batches the stones twice — once as the
  scene's draws, once as the shadow casters — and writes this frame's instance
  data. It runs before anything binds set 0, as Chapter 19 requires.
- **`RecordShadows`** (Chapter 17 section 9) fits the cascades to the camera,
  draws every caster into every cascade, and leaves the shadow map ready for
  the fragment shaders. It needs `SunDirection(frameIndex)`, which
  `WriteLights` set inside `WriteFrameBuffers`, so it comes after that.
- **`RecordDraws`** draws the stones inside the scene pass. It binds its own
  pipeline and its own sets, so it goes **before** the grass binds set 0 and
  set 1 through its own layout. The other way round, the grass's bindings would
  be disturbed and need binding again.

`Record` is listed whole in the Appendix.

**The sky (Chapter 23).** The field gets Chapter 23's sky like every other 3D
demo, with the panel's sun — the one `WriteFrameBuffers` gives the light buffer.
In `Setup`, just before `CreateStones()`:

```cpp
    if (auto result = m_sky.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats); !result)
    {
        return result;   // Chapter 23
    }
```

Right after it, one line from Chapter 24. The stones are drawn with the mesh
pipelines, whose fragment shader names set 0's bindings 10-12, so the demo
points them at the sky's light:

```cpp
    m_sceneRenderer.SetImageBasedLighting(m_sky.Lighting());   // Chapter 24: the stones' shader names set 0's bindings 10-12
```

In `Record`, after `RecordShadows`, before the clear color, with the frame
index Chapter 24 section 4 added:

```cpp
    // Chapter 23: the sky's sun is the panel's, the one WriteFrameBuffers gave the light buffer.
    m_sky.Update(commandBuffer, frameIndex, frame.sky,
                 { .sunDirection  = sunTravelDirection(m_settings.sunElevation, m_settings.sunAzimuth),
                   .sunIrradiance = glm::vec3(m_settings.sunIntensity) });
```

and after the blades, before `endScenePass`:

```cpp
    m_sky.Draw(commandBuffer, view, projection);   // Chapter 23: after the ground, the stones, and the blades
```

With the sky Off, the clear color's blue shows as before.

**The sky's light, on the field too.** Chapter 24's "Light the scene with the
sky" decides each frame where the ambient light comes from, through
`FrameData::ambientMode`. The stones' mesh shader reads it already; the ground
and the blades have shaders of their own, so they read it too, and look up
binding 10, the diffuse cube, by their normal. Each fragment shader declares
the one binding it reads, after its set 1 block:

```glsl
layout(set = 0, binding = 10) uniform samplerCube skyDiffuse;   // Chapter 25 section 8: Chapter 24's sky light, E / pi
```

and its ambient line becomes the switch: in `Terrain.frag.glsl`

```glsl
    // Chapter 25 section 8: Chapter 24's switch - the sky's light around the normal, or Chapter 16's constant.
    vec3 ambient = frame.ambientMode == AMBIENT_SKY ? texture(skyDiffuse, normal).rgb : lightHeader.ambient.rgb;
    vec3 color   = albedo * ambient;
```

and in `Grass.frag.glsl` the same two lines, where section 7 wrote its ambient
line. The mode is the same
for every pixel, so the branch costs one comparison (Chapter 15 section 9). The
demo turns the setting into the mode as Meshes does (Chapter 24 section 4),
but `WriteFrameBuffers` is not handed the frame's settings, so `Record` keeps
the answer in a member beside `m_sky`:

```cpp
    bool                           m_skyLightsScene = false;   // Chapter 25 section 8: Chapter 24's switch, this frame
```

sets it just before it calls `WriteFrameBuffers`:

```cpp
    m_skyLightsScene = vulkan_graphics::skyLightsScene(frame.sky);   // Chapter 25 section 8: for WriteFrameBuffers
```

and `WriteFrameBuffers` writes it after `frameData.deltaTime`:

```cpp
    frameData.ambientMode    = m_skyLightsScene ? AMBIENT_SKY : AMBIENT_FLAT;   // Chapter 25 section 8: the sky's light
```

With the sky on and the box ticked, the field's shade takes the sky's color: the
shaded blades and ground turn a little bluer, and dim with the sky as the sun
sets. Untick it and the shade is the fixed fill light again.

**In `Update`**, Chapter 17's "Shadows" panel goes between the camera's and the
grass's, editing `m_shadowSettings`, which the demo owns like its other CPU
state:

```cpp
    drawShadowPanel(m_shadowSettings);
```

**In `Setup`**, the stones come last:

```cpp
    CreateStones();                                                      // section 8
```

`CreateStones` comes last because it adds a mesh and a material to the scene
renderer, which must already exist, and it cannot fail in a way the demo can
recover from: `AddMesh` uploads and waits.

**This is `Teardown`, complete.** It destroys in the reverse order of creation,
and puts every handle back to null, because Chapter 09 section 2 allows `Setup`
to run again after `Teardown` — a sample-count change does exactly that
(Chapter 18 section 7):

```cpp
void GrassDemo::Teardown()
{
    const VkDevice device = m_context.vulkan.device;
    m_sky.Shutdown();                                              // Chapter 23
    vkDestroyPipeline(device, m_grassPipeline, nullptr);
    vkDestroyPipeline(device, m_terrainPipeline, nullptr);
    vkDestroyPipelineLayout(device, m_pipelineLayout, nullptr);
    vkDestroyDescriptorPool(device, m_descriptorPool, nullptr);   // frees the sets
    vkDestroyDescriptorSetLayout(device, m_grassSetLayout, nullptr);
    m_grassPipeline   = VK_NULL_HANDLE;
    m_terrainPipeline = VK_NULL_HANDLE;
    m_pipelineLayout  = VK_NULL_HANDLE;
    m_descriptorPool  = VK_NULL_HANDLE;
    m_grassSetLayout  = VK_NULL_HANDLE;
    m_grassSets       = {};

    for (AllocatedBuffer& parameters : m_parameterBuffers)
    {
        destroyBuffer(m_context.vulkan, parameters);
    }
    destroyBuffer(m_context.vulkan, m_blades);
    m_bladeCount = 0;

    m_stones.clear();
    m_sceneRenderer.Shutdown();
}
```

Destroying the descriptor pool frees the sets allocated from it, so the sets are
only forgotten. The stones' `DrawItem`s are cleared because they name a mesh and
a material inside the scene renderer that `Shutdown` is about to release;
`Setup` adds them again. `vkDestroy*` and `destroyBuffer` accept null handles,
which is what makes this safe after a `Setup` that failed halfway.

You should now see the finished picture: forty thousand blades on the hill and
two grey slabs standing in the field, the near one to your left. The sun is
behind your left shoulder, so the shadows run away from you and to the right:
the near stone's lies across the grass toward the middle of the view. From eye
height it is easy to miss — you look along the field at a grazing angle, and the
blades in the shadow are a thin band among lit ones — so fly up a few metres (E)
and look down, and both shadows lie clearly across the grass and the ground.
Turn the sun's azimuth and they swing round; lower its elevation and they
stretch. Where a shadow crosses a blade, the blade darkens part of the way up:
the shadow's edge climbs the blade at the angle the sun sets.

---

## If something goes wrong

- **No blades, only the ground.** The draw's instance count is zero (check
  `m_bladeCount` in the panel), the strip topology is missing (a *list* of 15
  vertices is five scattered triangles, and with 40,000 instances the field is
  shards), or `cullMode` is `BACK` and you are looking at backs — try turning the
  camera round.
- **Blades floating above the ground or sunk into it.** The blade's root and the
  ground disagree about the height: both must call `terrainHeight` with the same
  `terrainShape`, from the same `Terrain.glsl`.
- **Every blade the same shade whichever way it faces.** The normal is not
  reaching the fragment shader (check the locations: 0 and 1 in both stages), or
  it is not being flipped for back faces — fly round a blade and watch its back.
- **Blades black on one side and normal on the other.** `frontFace` does not
  match the strip's winding, so the flip happens on the wrong side. It must be
  `COUNTER_CLOCKWISE` for a strip built as in section 4.
- **A validation error about the descriptor type at binding 0 or 1.** The set
  layout, the pool sizes, and the writes in `CreateDescriptors` must agree:
  binding 0 a storage buffer, binding 1 a uniform buffer.
- **Lit side and shadowed side swapped, or no light at all.** The sun's
  direction is the direction its light travels; `sunTravelDirection` returns
  the opposite of "toward the sun". A `LightItem` built with the toward-the-sun
  vector lights everything from below.
- **Colors far too saturated or too dark.** The panel's colors are sRGB and must
  pass through `scene::srgbToLinear` before they are written; the composite
  pass encodes the result once.

---

## Exit check

- [ ] The demo appears as "Grass" in the "Demos" window and starts with
      `--demo Grass`, flying, at eye height, looking at the patch.
- [ ] With "Hill height" at 0, the ground is flat; at 2 m the hills are steep and
      every blade still stands on the surface, none floating, none sunk.
- [ ] View **Strip**: close to any blade, seven bands alternate bright and dark
      from root to tip, red on the left half and green on the right, ending in a
      point.
- [ ] View **Normals**: each blade shades smoothly from root to tip, with no
      seam down its middle; blades seen from behind show the same colors as
      blades seen from the front, facing you.
- [ ] View **Shaded**: blades facing the sun are visibly brighter than blades
      facing away; tips are lighter and yellower than roots.
- [ ] Seen from a few metres up, both stones cast shadows across the grass and
      the ground; the shadows move when the sun's azimuth and elevation change,
      and "Show cascades" in the "Shadows" panel tints the grass and the ground
      by cascade, like the stones.
- [ ] Sky section on **Sun sky**: the sky replaces the clear color, and its
      glow sits where the panel's sun is; turning the sun's azimuth moves the
      glow, the disk, and the stones' shadows together. Untick **Light the
      scene with the sky**: the shaded side of the field loses its blue tint.
- [ ] Chapter 18's sample count can be changed while running, from its "MSAA"
      window: the demo's
      `Teardown` and `Setup` run, the picture comes back the same, with no
      validation messages.
- [ ] Switching to another demo and back keeps the camera, the panel's
      settings, and the shadow settings.
- [ ] No validation messages at any point, with synchronization validation on.

---

## Sources

These are the sources behind the table in "Where each technique comes from";
"the game's" there means at least two of them agree.

- Eric Wohllaib, "Procedural Grass in *Ghost of Tsushima*", GDC 2021 (Sucker
  Punch Productions), GDC Vault.
- Written summaries of the talk: Tiger Abrodi's write-up (tigerabrodi.blog), a
  GitHub gist summarizing the talk, hexaquo.at's notes, and the GDC Vault
  abstract.
- Cain Rademan, *Unity-Grass* (GitHub): an implementation whose README lists the
  techniques it takes "mostly from the Tsushima talk" — Bézier blades, clumps,
  view-space thickening, rounded normals, vertices toward the tip.
- 2Retr0, *GodotGrass* (GitHub): view-space thickening "as suggested in the GoT
  GDC talk", clumps from cellular noise.
- WhiteWhale52, *GhostofTsushimaGrassRendering* (GitHub): tiles generated by
  compute, and the 15- and 7-vertex levels of detail.
- Klemens Jahrmann and Michael Wimmer, "Responsive Real-Time Grass Rendering for
  General 3D Scenes", I3D 2017 — the best-known earlier GPU grass method, built
  on *quadratic* Bézier blades; Chapter 26 contrasts its culling with this one's.

---

## Appendix: complete listings

For reference: the code this chapter changed in more than one place, as the
chapter leaves it. Read the sections for why; use these to check your files.

**`Shaders/Grass/Grass.vert.glsl`:**

```glsl
// Shaders/Grass/Grass.vert.glsl - one blade per instance, built from gl_VertexIndex.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"
#include "GrassTypes.h"
#include "Terrain.glsl"

layout(set = 1, binding = 0, std430) readonly buffer BladeBlock { GrassBlade blades[]; };
layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };

layout(location = 0) out vec3  worldPosition;
layout(location = 1) out vec3  worldNormal;   // of the front face; the fragment shader flips it for the back
layout(location = 2) out float bladeT;        // 0 at the root, 1 at the tip
layout(location = 3) out float bladeSide;     // -1 on the left edge, +1 on the right

const uint SEGMENTS = 7u;   // 7 pairs of vertices and a tip: 15 vertices

// The cubic Bezier curve, and its derivative: the direction the curve runs at t.
vec3 bezier(vec3 p0, vec3 p1, vec3 p2, vec3 p3, float t)
{
    float s = 1.0 - t;
    return s * s * s * p0 + 3.0 * s * s * t * p1 + 3.0 * s * t * t * p2 + t * t * t * p3;
}

vec3 bezierDerivative(vec3 p0, vec3 p1, vec3 p2, vec3 p3, float t)
{
    float s = 1.0 - t;
    return 3.0 * s * s * (p1 - p0) + 6.0 * s * t * (p2 - p1) + 3.0 * t * t * (p3 - p2);
}

void main()
{
    GrassBlade blade = blades[gl_InstanceIndex];

    // Which vertex of the strip this is: a pair per segment, then the tip.
    uint  segment = uint(gl_VertexIndex) / 2u;                // 0 .. SEGMENTS
    float side    = (gl_VertexIndex & 1) == 0 ? -1.0 : 1.0;    // left, right
    float t       = float(segment) / float(SEGMENTS);

    // The blade's own frame. front is where its face looks while it stands
    // upright; it leans the other way, toward back.
    float facing = blade.rootAndFacing.w;
    vec3  up     = vec3(0.0, 1.0, 0.0);
    vec3  front  = vec3(sin(facing), 0.0, cos(facing));
    vec3  back   = -front;
    vec3  right  = cross(up, front);                           // across the blade

    float height = blade.shape.x;
    float width  = blade.shape.y;
    float tilt   = blade.shape.z;
    float bend   = blade.shape.w;

    vec3 root = vec3(blade.rootAndFacing.x, 0.0, blade.rootAndFacing.z);
    root.y    = terrainHeight(root.xz, grass.terrainShape);

    // Four control points in the plane of up and back. chord runs root to tip;
    // arch is perpendicular to it, on the side away from the ground.
    float lean  = tilt * 1.5707963;                            // 0 upright, 1 lying flat
    vec3  chord = cos(lean) * up + sin(lean) * back;
    vec3  arch  = sin(lean) * up - cos(lean) * back;
    vec3  p0    = root;
    vec3  p1    = root + height * (chord / 3.0       + arch * bend * 0.5);
    vec3  p2    = root + height * (chord * 2.0 / 3.0 + arch * bend * 0.5);
    vec3  p3    = root + height * chord;

    vec3  center    = bezier(p0, p1, p2, p3, t);
    vec3  tangent   = bezierDerivative(p0, p1, p2, p3, t);
    float halfWidth = 0.5 * width * (1.0 - t * t);             // full width low down, a point at the tip

    worldPosition = center + right * side * halfWidth;
    worldNormal   = normalize(cross(right, tangent));
    bladeT        = t;
    bladeSide     = side;
    gl_Position   = frame.viewProjection * vec4(worldPosition, 1.0);
}
```

**`GrassDemo::CreatePipelines`:**

```cpp
InitializationResult GrassDemo::CreatePipelines()
{
    // Set 0 is the scene renderer's: camera, lights, shadows. Set 1 is the grass's.
    const std::array<VkDescriptorSetLayout, 2> setLayouts{ m_sceneRenderer.FrameSetLayout(), m_grassSetLayout };
    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT,
        .offset     = 0,
        .size       = sizeof(GrassPush),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = static_cast<uint32_t>(setLayouts.size()),
        .pSetLayouts            = setLayouts.data(),
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_pipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the grass.");
    }

    const GraphicsPipelineDesc terrain{
        .vertexShader   = "Grass/Terrain.vert.spv",
        .fragmentShader = "Grass/Terrain.frag.spv",
        .colorFormats   = { &m_context.formats.color, 1 },
        .depthFormat    = m_context.formats.depth,
        .depthTest      = true,
        .depthWrite     = true,
        .cullMode       = VK_CULL_MODE_BACK_BIT,
        .frontFace      = VK_FRONT_FACE_COUNTER_CLOCKWISE,
        .layout         = m_pipelineLayout,
        .samples        = m_context.formats.samples,
    };
    const GraphicsPipelineDesc blades{
        .vertexShader   = "Grass/Grass.vert.spv",
        .fragmentShader = "Grass/Grass.frag.spv",
        .colorFormats   = { &m_context.formats.color, 1 },
        .depthFormat    = m_context.formats.depth,
        .depthTest      = true,
        .depthWrite     = true,
        .cullMode       = VK_CULL_MODE_NONE,                       // sections 4 and 7: both faces
        .frontFace      = VK_FRONT_FACE_COUNTER_CLOCKWISE,
        .layout         = m_pipelineLayout,
        .samples        = m_context.formats.samples,
        .topology       = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_STRIP,    // section 4
    };
    m_terrainPipeline = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, terrain);
    m_grassPipeline   = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, blades);
    if (m_terrainPipeline == VK_NULL_HANDLE || m_grassPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating a grass pipeline failed.");
    }
    return InitializationResult::success();
}
```

**`GrassDemo::Record`:**

```cpp
void GrassDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const uint32_t        frameIndex    = frame.frameIndex;

    const VkExtent2D extent    = frame.targets.extent;
    const float     aspect     = static_cast<float>(extent.width) / static_cast<float>(extent.height);
    const glm::mat4 view       = scene::viewMatrix(m_cameraTransform.Matrix());
    const glm::mat4 projection = m_camera.Projection(aspect);
    m_skyLightsScene = vulkan_graphics::skyLightsScene(frame.sky);   // Chapter 25 section 8: for WriteFrameBuffers
    WriteFrameBuffers(frameIndex, view, projection);

    // Before the scene pass: the stones' draws (Chapter 19), drawn and casting
    // shadows, then the sun's cascades (Chapter 17).
    m_sceneRenderer.PrepareDraws(frameIndex, m_stones, m_stones);
    m_sceneRenderer.RecordShadows(commandBuffer, frameIndex, m_camera, view, aspect,
                                  m_sceneRenderer.SunDirection(frameIndex), m_shadowSettings);

    // Chapter 23: the sky's sun is the panel's, the one WriteFrameBuffers gave the light buffer.
    m_sky.Update(commandBuffer, frameIndex, frame.sky,
                 { .sunDirection  = sunTravelDirection(m_settings.sunElevation, m_settings.sunAzimuth),
                   .sunIrradiance = glm::vec3(m_settings.sunIntensity) });

    const VkClearColorValue clearColor{ { 0.35f, 0.50f, 0.75f, 1.0f } };   // linear
    beginScenePass(commandBuffer, frame.targets, &clearColor);

    // The stones first: RecordDraws binds its own pipeline and set 0, and ours follow.
    m_sceneRenderer.RecordDraws(commandBuffer, frameIndex);

    m_sceneRenderer.BindFrameSet(commandBuffer, m_pipelineLayout, frameIndex);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipelineLayout,
                            1, 1, &m_grassSets[frameIndex], 0, nullptr);

    // The ground: a square of TERRAIN_CELLS quads centred on the patch.
    const float     groundSide = TERRAIN_CELL * static_cast<float>(TERRAIN_CELLS);
    const GrassPush push{ .terrainGrid = { -0.5f * groundSide, -0.5f * groundSide,
                                           TERRAIN_CELL, static_cast<float>(TERRAIN_CELLS) } };
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_terrainPipeline);
    vkCmdDraw(commandBuffer, 6 * TERRAIN_CELLS * TERRAIN_CELLS, 1, 0, 0);

    // The blades: 15 vertices each, one instance per blade.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_grassPipeline);
    vkCmdDraw(commandBuffer, 15, m_bladeCount, 0, 0);

    m_sky.Draw(commandBuffer, view, projection);   // Chapter 23: after the ground, the stones, and the blades
    endScenePass(commandBuffer);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

Next: [26 — Grass, Part II: GPU Generation](26-Grass-GPU-Generation.md)
