# 26 — Grass, Part II: GPU Generation

**Goal:** an endless field, generated around the camera every frame. A compute
pass lays out candidate blades in 4 m tiles near the camera, culls them against
the view, thins them with distance, and appends the survivors into two levels
of detail — 15 vertices near, 7 far — that morph into each other so the switch
cannot be seen. Two indirect draws whose blade counts the CPU never learns draw
them. A panel shows the counts and what each pass costs. Optionally, in Part 2
(section 9), blades hidden behind last frame's depth are culled too.

**ROADMAP:** step 21+ — the same demo, `Source/PillowFort/Demos/Grass/`, shaders
under `Shaders/Grass/`.

**Module:** `pf::demos::grass`. `GrassDemo` loses Chapter 25's CPU-placed patch
and gains a compute pipeline of three passes. Nothing outside the demo's two
folders changes.

**Prerequisites:**

- Chapter 25, all of it: this chapter rebuilds its demo around the same blade.
- Chapter 21 sections 2 to 4 — counters, appending with atomics, the
  single-invocation Begin and End passes, the indirect command structs in
  `SharedShaderTypes.h`, and the return-trip barrier — and section 7, reading
  counts back without stalling. The grass uses the same machinery for a
  different job.
- Chapter 24 section 9 — `GpuTimestamps`, Chapter 21 section 8's timestamp
  queries as a class, which section 8 uses to time the grass.
- Chapter 04 section 5 — the three questions every barrier answers. Each of
  this chapter's barriers is argued with them.
- Chapter 20 sections 3 (dispatch sizing and `groupCount`), 5
  (`computeToComputeBarrier`, `memoryBarrier`, and what synchronization
  validation can see), 8 (atomics), and 10 (compute feeding the vertex stage).
- Chapter 19 sections 6 and 7 — indirect draws, and the
  `drawIndirectFirstInstance` feature it enabled.
- Chapter 12 section 9 — `Frustum`, `frustumFromViewProjection`, and
  `intersects`.
- For Part 2 only: Chapter 10 sections 1 and 2 (clip space, `w`, and the
  divide that gives normalized device coordinates) and 9 (the depth image, and
  who owns a later reader's return trip); Chapter 15 section 5 (mip levels and
  `log2`); and Chapter 18 sections 4 and 5 (at 2× and up the depth image is a
  resolve target, `MAX` or `SAMPLE_ZERO`).

---

# Part 1 — A field generated on the GPU (sections 1-8)

Sections 1 to 8 replace Chapter 25's list of blades with a field computed
every frame, culled, split into two levels of detail, and measured. Part 1
ends with the whole field on screen and its budget on the panel. Part 2 is
optional: nothing later depends on it.

## 1. A field is a function of position

Chapter 25's patch is twenty metres across and holds forty thousand blades.
Make it reach fifty metres in every direction from the camera at the same
spacing and it needs about eight hundred thousand; make the camera able to walk
anywhere and the list has no end. Uploading them all is not the problem — they
are 32 bytes each. The problem is that almost none of them are worth drawing in
any one frame: most are behind the camera, many are too far away to be more
than a speck, and the vertex shader would still run fifteen times for every one.

*Ghost of Tsushima* does not keep a list. Every frame, for the tiles of world
near the camera, a compute shader **decides from scratch** where the blades are,
what they look like, and whether they are visible, and writes out only the ones
that are. Nothing about a blade is stored between frames.

> **Jump:** Chapter 25's blades were *data*: made once, on the CPU, and read
> every frame. From here they are a *function*: given a point on the ground, the
> generation pass computes the blade that grows there, every frame, and throws
> it away after drawing. The idea to hold on to is that **the same point must
> produce the same blade every time**, whichever frame, tile list, or GPU thread
> computes it — otherwise the field would boil as the camera moves. So
> everything random about a blade is derived from the integer coordinates of its
> cell in the world, never from a frame number, a thread index, or the order the
> tiles were listed in. Hold on, too, to what this costs: the CPU no longer knows
> how many blades there are. The GPU counts them, writes its own draw commands,
> and the CPU hears the numbers two frames later, for the panel only.

What changes in the demo:

- **`CreateBlades` goes**, with `m_bladeCount` and `<random>`. The blade buffer
  is now written by compute every frame, so it needs no staging copy and no
  upload barrier — only the barriers between the compute passes and the draws
  that read their results (section 4).
- **The blade's root height is computed once**, by the generation pass, and
  stored in the `y` Chapter 25 left unused. The vertex shader stops asking the
  terrain fifteen times per blade.
- **The ground follows the camera**, because the field does.
- **Two draws instead of one**, one per level of detail, both indirect.

### What you are actually writing

**This is `GrassDemo.h`**, the map of Part 1. Part 2 adds to it; what it adds
is listed there.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Grass toward Ghost of Tsushima: generated, culled, and LODed on the GPU (Chapter 26)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Grass/GrassDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Bounds.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/DrawItem.h"
#include "PillowFort/Scene/Transform.h"
#include "PillowFort/VulkanGraphics/GpuTimestamps.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"
#include "PillowFort/VulkanGraphics/ShadowMaps.h"
#include "PillowFort/VulkanGraphics/Sky.h"
#include "Grass/GrassTypes.h"

#include <glm/glm.hpp>

#include <array>
#include <cstdint>
#include <vector>

namespace pf::demos::grass {

// What the panel edits (Chapter 25 section 2, grown here). CPU state: it survives Teardown and Setup.
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
    // Chapter 26
    int       bladesPerSide     = 40;       // per tile side: 40 in 4 m is a blade every 10 cm
    float     lodDistance       = 12.0f;    // metres
    float     morphBand         = 4.0f;     // metres
    float     densityStart      = 10.0f;    // metres
    float     maxDistance       = 50.0f;    // metres
    float     farDensity        = 0.15f;    // the fraction of candidates that grow at maxDistance
    float     fadeBand          = 0.08f;    // how far below its cut a blade starts to shrink
    glm::vec4 shapeMin { 0.35f, 0.035f, 0.10f, 0.10f };   // height (m), width (m), tilt, bend:
    glm::vec4 shapeMax { 0.70f, 0.055f, 0.45f, 0.50f };   // Chapter 25's ranges
    bool      freezeCulling     = false;    // keep culling from where the camera was
};

// What the GPU reported for a frame FRAMES_IN_FLIGHT frames ago (section 8).
struct GrassStatistics
{
    uint32_t tiles        = 0;
    uint32_t candidates   = 0;
    uint32_t lodCount[2]  = {};   // what the counters reached, which may exceed the capacity
    double   generateMs   = 0.0;
    double   lod0Ms       = 0.0;
    double   lod1Ms       = 0.0;
};

class GrassDemo final : public Demo
{
public:
    GrassDemo();                                                                         // section 1
    const char*          Name() const override { return "Grass"; }
    InitializationResult Setup(const DemoContext& context) override;
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override;
    void                 Update(const FrameInput& input) override;
    void                 Record(const RecordContext& frame) override;
    void                 Teardown() override;
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }

private:
    InitializationResult CreateBuffers();       // section 3, replacing Chapter 25's CreateBlades
    InitializationResult CreateDescriptors();   // section 3
    InitializationResult CreatePipelines();     // section 4
    void                 CreateStones();        // Chapter 25 section 8
    uint32_t CollectTiles(uint32_t frameIndex, const scene::Frustum& cullFrustum, glm::vec3 cullPosition);   // section 2
    void WriteFrameBuffers(uint32_t frameIndex, const glm::mat4& view, const glm::mat4& projection,
                           const scene::Frustum& cullFrustum, glm::vec3 cullPosition);                       // sections 2-7
    void RecordGeneration(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t tileCount);         // section 4
    void ReadStatistics(uint32_t frameIndex);                                                                // section 8

    // A blade every few centimetres, in square tiles; every candidate one invocation.
    static constexpr float    TILE_SIZE     = 4.0f;       // metres
    static constexpr uint32_t MAX_TILES     = 4096;       // a 256 m square; far more than maxDistance reaches
    static constexpr uint32_t LOD0_CAPACITY = 200000;
    static constexpr uint32_t LOD1_CAPACITY = 600000;
    static constexpr uint32_t TIMESTAMP_COUNT      = 5;   // per frame in flight (section 8)
    // The ground follows the camera: TERRAIN_CELLS x TERRAIN_CELLS quads of TERRAIN_CELL metres.
    static constexpr float    TERRAIN_CELL  = 0.5f;
    static constexpr uint32_t TERRAIN_CELLS = 260;        // 130 m square

    DemoContext                    m_context;
    vulkan_graphics::SceneRenderer m_sceneRenderer;
    vulkan_graphics::Sky           m_sky;   // Chapter 23
    bool                           m_skyLightsScene = false;   // Chapter 25 section 8: Chapter 24's switch, this frame

    // Section 3: one set for the compute passes and the draws alike.
    vulkan_graphics::AllocatedBuffer m_blades;     // LOD 0's region, then LOD 1's; written by compute
    vulkan_graphics::AllocatedBuffer m_counters;   // GrassCounters
    vulkan_graphics::AllocatedBuffer m_commands;   // two DrawIndirectCommands
    std::array<vulkan_graphics::AllocatedBuffer, vulkan_graphics::FRAMES_IN_FLIGHT> m_parameterBuffers;
    std::array<vulkan_graphics::AllocatedBuffer, vulkan_graphics::FRAMES_IN_FLIGHT> m_tileBuffers;
    VkDescriptorSetLayout            m_grassSetLayout = VK_NULL_HANDLE;
    VkDescriptorPool                 m_descriptorPool = VK_NULL_HANDLE;
    std::array<VkDescriptorSet, vulkan_graphics::FRAMES_IN_FLIGHT> m_grassSets{};

    // Section 4: one layout for every pipeline.
    VkPipelineLayout m_pipelineLayout     = VK_NULL_HANDLE;
    VkPipeline       m_terrainPipeline    = VK_NULL_HANDLE;
    VkPipeline       m_grassPipeline      = VK_NULL_HANDLE;
    VkPipeline       m_beginPipeline      = VK_NULL_HANDLE;
    VkPipeline       m_generatePipeline   = VK_NULL_HANDLE;
    VkPipeline       m_endPipeline        = VK_NULL_HANDLE;

    // Section 8: what each frame cost and produced, read back FRAMES_IN_FLIGHT frames later.
    std::array<vulkan_graphics::AllocatedBuffer, vulkan_graphics::FRAMES_IN_FLIGHT> m_readback;
    std::array<uint32_t, vulkan_graphics::FRAMES_IN_FLIGHT> m_tileCounts{};
    std::array<uint32_t, vulkan_graphics::FRAMES_IN_FLIGHT> m_candidateCounts{};
    std::array<bool, vulkan_graphics::FRAMES_IN_FLIGHT>     m_readbackPending{};
    vulkan_graphics::GpuTimestamps   m_timestamps;   // Chapter 24's class, TIMESTAMP_COUNT a frame
    GrassStatistics                  m_statistics;

    // Chapter 25 section 8.
    std::vector<scene::DrawItem> m_stones;

    // CPU state.
    GrassSettings                   m_settings;
    vulkan_graphics::ShadowSettings m_shadowSettings;
    scene::Camera                   m_camera;
    scene::Transform                m_cameraTransform;   // the grass has no Scene: its camera's pose is its own
    scene::CameraControls           m_controls;
    glm::mat4                       m_frozenViewProjection{ 1.0f };   // section 2: the culling camera,
    glm::vec3                       m_frozenPosition{ 0.0f };         // while freezeCulling is on
    float                           m_time      = 0.0f;
    float                           m_deltaTime = 0.0f;
};

} // namespace pf::demos::grass
```

`GrassSettings` grows the generation's numbers — how dense, how far, where the
levels of detail switch — and `GrassStatistics` is what the GPU reports back.
The new private functions follow the frame: `CollectTiles` picks the tiles on
the CPU, `WriteFrameBuffers` writes them and the parameters, `RecordGeneration`
records the compute, and `ReadStatistics` reads two-frame-old results.

### Where everything lands

```text
Shaders/Grass/
  GrassTypes.h              + GrassTile, GrassCounters; GrassParameters and
                              GrassPush grow                                  sections 2-5
  GrassCompute.glsl         set 1 as the compute passes see it                section 3
  GrassGenerate.comp.glsl   place, thin, cull, and append every candidate      section 3
  GrassBegin.comp.glsl      the counts start at zero                          section 4
  GrassEnd.comp.glsl        the counts become two draws                       section 4
  BladeShape.glsl           Chapter 25's curve, moved out of Grass.vert.glsl  section 5
  Grass.vert.glsl           either level of detail, and the morph             sections 5 and 6
  Grass.frag.glsl           two more debug views                              section 5
  GrassDepthReduce.comp.glsl  one level of the depth pyramid                  section 9 (Part 2)
Source/PillowFort/Demos/Grass/
  GrassDemo.h/.cpp          the demo, rebuilt
```

```text
GrassDemo.cpp
  includes
  static sunTravelDirection(elevation, azimuth)          Chapter 25
  namespace pf::demos::grass {
      using namespace vulkan_graphics;
      static drawGrassPanel(settings, statistics, caps)   section 2
      GrassDemo::GrassDemo                                Chapter 25
      GrassDemo::Setup                                    section 3
      GrassDemo::CreatePipelines                          section 4
      GrassDemo::CreateBuffers                            section 3
      GrassDemo::CreateDescriptors                        section 3
      GrassDemo::CreateStones                             Chapter 25
      GrassDemo::Resize                                   Chapter 25 (Part 2 fills it)
      GrassDemo::Update                                   section 2
      GrassDemo::CollectTiles                             section 2
      GrassDemo::WriteFrameBuffers                        sections 2-7
      GrassDemo::RecordGeneration                         section 4
      GrassDemo::ReadStatistics                           section 8
      GrassDemo::Record                                   sections 2, 4, 5, and 8
      GrassDemo::Teardown                                 section 8
      (Part 2 adds four functions; section 9 lists them)
  }
```

`GrassDemo.cpp` now includes `PillowFort/VulkanGraphics/VulkanBarriers.h` (for
Chapter 20's `memoryBarrier` and `computeToComputeBarrier`, and Chapter 04's
`transitionImage` in Part 2), `<algorithm>`, and `<cstddef>`, and no longer
needs `<random>`.

> **Rerun `GenerateProjects.bat`** after adding the new shaders: the shader
> glob, like the C++ one, is expanded when the projects are generated.

From here to the end of section 4 the demo is being rebuilt, and the grass is
back on screen at the end of section 4 — the near part of it — and whole at the
end of section 5. Build after each section anyway: the compiler and the
validation layer catch most mistakes where they are made.

---

## 2. Tiles around the camera

The generation pass needs to know *where* to generate. Asking every blade in
the world "are you visible?" is out of the question, so the world is cut into
**tiles** — squares of ground, 4 m on a side here — and the CPU decides which
tiles are worth generating; the GPU then decides blade by blade within them.
*Ghost of Tsushima* generates per tile in compute. The 4 m is this tutorial's
choice: big enough that a few hundred tiles cover the view, small enough that a
tile's box hugs the hills.

A tile is two integers, its column and row in a grid that covers the whole
world. **This is the new struct in `GrassTypes.h`:**

```c
/* Chapter 26: one visible tile, written by the CPU each frame. std430, set 1 binding 2. */
struct GrassTile
{
    int  x;               /* the tile covers [x, x + 1) * tileSize in world x */
    int  z;               /* and [z, z + 1) * tileSize in world z */
    uint padding0;
    uint padding1;
};
```

Two integers would do; the padding makes the struct 16 bytes so that its std430
array stride is the same in C++ and GLSL without thinking about it.

### Which tiles

**This is `CollectTiles`**, which fills this frame's tile buffer with every tile
that is near enough and inside the view:

```cpp
// Every tile near enough and inside the culling frustum, written into this
// frame's tile buffer. Returns how many.
uint32_t GrassDemo::CollectTiles(uint32_t frameIndex, const scene::Frustum& cullFrustum, glm::vec3 cullPosition)
{
    // Every blade of a tile fits in this box: its roots are inside the square, and
    // nothing of a blade is further from its root than its height plus its width -
    // the radius the generation pass culls each blade's sphere with (section 3). So:
    // the square grown by that much, from the lowest the ground can be to the highest.
    const float bladeReach = m_settings.shapeMax.x + m_settings.shapeMax.y;
    const float low        = -m_settings.terrainAmplitude - bladeReach;
    const float high       =  m_settings.terrainAmplitude + bladeReach;
    const float reach      = m_settings.maxDistance;
    const int   firstX = static_cast<int>(std::floor((cullPosition.x - reach) / TILE_SIZE));
    const int   lastX  = static_cast<int>(std::floor((cullPosition.x + reach) / TILE_SIZE));
    const int   firstZ = static_cast<int>(std::floor((cullPosition.z - reach) / TILE_SIZE));
    const int   lastZ  = static_cast<int>(std::floor((cullPosition.z + reach) / TILE_SIZE));

    GrassTile* tiles = static_cast<GrassTile*>(m_tileBuffers[frameIndex].mapped);
    uint32_t   count = 0;
    for (int z = firstZ; z <= lastZ && count < MAX_TILES; ++z)
    {
        for (int x = firstX; x <= lastX && count < MAX_TILES; ++x)
        {
            const glm::vec2 squareMin{ static_cast<float>(x) * TILE_SIZE, static_cast<float>(z) * TILE_SIZE };
            const glm::vec2 squareMax = squareMin + TILE_SIZE;
            const scene::Aabb box{
                .min = { squareMin.x - bladeReach, low,  squareMin.y - bladeReach },
                .max = { squareMax.x + bladeReach, high, squareMax.y + bladeReach },
            };
            // The square's nearest point to the camera, on the ground plane: no root
            // in this tile is nearer than that.
            const glm::vec2 camera{ cullPosition.x, cullPosition.z };
            const glm::vec2 nearest = glm::clamp(camera, squareMin, squareMax);
            if (glm::distance(nearest, camera) > reach || !scene::intersects(cullFrustum, box))
            {
                continue;
            }
            tiles[count++] = GrassTile{ .x = x, .z = z };
        }
    }
    vmaFlushAllocation(m_context.vulkan.allocator, m_tileBuffers[frameIndex].allocation, 0, VK_WHOLE_SIZE);
    return count;
}
```

Two tests, both conservative — a tile is dropped only if no blade it could
hold could be seen:

- **Distance.** A tile is kept if the nearest point of its square is within
  `maxDistance` of the camera, measured on the ground. The square, not the box:
  section 7 thins blades by the distance to their *roots*, and every root lies
  inside the square.
- **The frustum**, Chapter 12 section 9's test of a box against six planes. The
  box must contain everything any blade of the tile could become. Vertically
  that is the lowest the ground can be to the highest — the terrain's amplitude
  either way, which is why Chapter 25 kept the height inside it — plus the
  tallest blade. Sideways it is the square **grown by the same reach**, because a
  blade rooted at the edge of its tile leans out over the next one. The reach
  is the radius section 3 culls each blade's sphere with, so the two tests
  agree about what a blade can occupy.

`MAX_TILES` is a fixed capacity for the tile buffer: 4096 tiles is a 256 m
square, more than the panel's furthest `maxDistance` can reach. The loop stops
adding tiles if it is ever reached rather than writing past the buffer.

The tile buffer is **host-visible, one per frame in flight**, written by the CPU
every frame and read by the generation pass: the same arrangement as the
parameter buffers, for the same reason, and like them it needs a flush but no
barrier (Chapter 10 section 7). Section 3 creates it.

### The culling camera

The tiles, and the blades in section 3, are culled against a **culling camera**,
which is normally the real one. The panel can freeze it: the culling camera
stays where it was while the real camera flies away, and you can see from
outside exactly which tiles and blades were generated — the field becomes a
wedge with the frozen camera at its point. It is the single most useful debug
view in this chapter.

**This is the top of `Record`**, which picks the culling camera, collects the
tiles, and writes the frame's buffers:

```cpp
void GrassDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const uint32_t        frameIndex    = frame.frameIndex;

    const VkExtent2D extent    = frame.targets.extent;
    const float     aspect     = static_cast<float>(extent.width) / static_cast<float>(extent.height);
    const glm::mat4 view       = scene::viewMatrix(m_cameraTransform.Matrix());
    const glm::mat4 projection = m_camera.Projection(aspect);

    // The culling camera is the real one, unless the panel froze it where it was.
    if (!m_settings.freezeCulling)
    {
        m_frozenViewProjection = projection * view;
        m_frozenPosition       = m_cameraTransform.translation;
    }
    const scene::Frustum cullFrustum = scene::frustumFromViewProjection(m_frozenViewProjection);

    const uint32_t tileCount = CollectTiles(frameIndex, cullFrustum, m_frozenPosition);
    m_skyLightsScene = vulkan_graphics::skyLightsScene(frame.sky);   // Chapter 25 section 8: for WriteFrameBuffers
    WriteFrameBuffers(frameIndex, view, projection, cullFrustum, m_frozenPosition);
```

`frustumFromViewProjection` takes the combined matrix and returns six planes in
world space (Chapter 12 section 9), the same planes the GPU will test blades
against, so the CPU's and the GPU's culling agree.

### The panel, grown

Everything this chapter adds is on the panel, so it comes first.
**`drawGrassPanel`** takes the statistics and the two capacities, shows a
"Budget" at the top, gains two debug views and a "Generation" group, and keeps
Chapter 25's "Color", "Ground", and "Sun" groups after them as they were. Its
first half, for this chapter:

```cpp
static void drawGrassPanel(GrassSettings& settings, const GrassStatistics& statistics,
                           uint32_t capacity0, uint32_t capacity1)
{
    if (debug_panels::beginDemoPanel("Grass", debug_panels::DemoPanelSlot::BelowCamera))
    {
        ImGui::SeparatorText("Budget");
        ImGui::Text("Tiles %u, candidates %u", statistics.tiles, statistics.candidates);
        ImGui::Text("LOD 0 %u / %u, LOD 1 %u / %u",
                    statistics.lodCount[0], capacity0, statistics.lodCount[1], capacity1);
        if (statistics.lodCount[0] > capacity0 || statistics.lodCount[1] > capacity1)
        {
            ImGui::TextColored(ImVec4(1.0f, 0.4f, 0.3f, 1.0f), "Over capacity: blades are being dropped");
        }
        ImGui::Text("Generate %.3f ms, LOD 0 %.3f ms, LOD 1 %.3f ms",
                    statistics.generateMs, statistics.lod0Ms, statistics.lod1Ms);

        // The budget stays in view; each group of controls folds away under its name (Chapter 09
        // section 6). The debug view comes first: nearly every check in Chapters 25-27 starts there.
        if (ImGui::CollapsingHeader("Debug"))
        {
            ImGui::Combo("View", &settings.debugView, "Shaded\0Strip\0Normals\0LOD\0Tiles\0");
        }

        if (ImGui::CollapsingHeader("Generation"))
        {
            // To 256, past both capacities at the default distances (section 8's "Raise"). Clamped even when
            // typed: Generate is bladesPerSide * bladesPerSide / 64 workgroups wide; Vulkan guarantees 65535.
            ImGui::SliderInt("Blades per tile side", &settings.bladesPerSide, 4, 256, "%d", ImGuiSliderFlags_AlwaysClamp);
            ImGui::DragFloatRange2("Height (m)", &settings.shapeMin.x, &settings.shapeMax.x, 0.01f, 0.05f, 2.0f);
            ImGui::SliderFloat("LOD distance (m)", &settings.lodDistance, 2.0f, 60.0f);
            ImGui::SliderFloat("Morph band (m)", &settings.morphBand, 0.0f, 10.0f);
            ImGui::SliderFloat("Thinning starts (m)", &settings.densityStart, 0.0f, 60.0f);
            ImGui::SliderFloat("Grass ends (m)", &settings.maxDistance, 5.0f, 120.0f);
            ImGui::SliderFloat("Density at the end", &settings.farDensity, 0.0f, 1.0f);
            ImGui::SliderFloat("Fade band", &settings.fadeBand, 0.001f, 0.5f);
            ImGui::Checkbox("Freeze culling", &settings.freezeCulling);
        }
```

The "Budget" lines read `GrassStatistics`, which section 8 fills from what the
GPU reports; until then they show zeros. The "Generation" sliders are sections
3 to 7's, and "Freeze culling" is the culling camera above. **In `Update`**, the
call becomes:

```cpp
    drawGrassPanel(m_settings, m_statistics, LOD0_CAPACITY, LOD1_CAPACITY);
```

### The ground follows

An endless field needs endless ground, and the cheapest way to get it is to
draw Chapter 25's grid wherever the camera is. **In `Record`, the ground's push
constant becomes:**

```cpp
    // The ground follows the culling camera, snapped to whole cells so it does not swim.
    const float groundSide = TERRAIN_CELL * static_cast<float>(TERRAIN_CELLS);
    const float cornerX    = std::floor(m_frozenPosition.x / TERRAIN_CELL) * TERRAIN_CELL - 0.5f * groundSide;
    const float cornerZ    = std::floor(m_frozenPosition.z / TERRAIN_CELL) * TERRAIN_CELL - 0.5f * groundSide;
    GrassPush push{ .terrainGrid = { cornerX, cornerZ, TERRAIN_CELL, static_cast<float>(TERRAIN_CELLS) } };
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_terrainPipeline);
    vkCmdDraw(commandBuffer, 6 * TERRAIN_CELLS * TERRAIN_CELLS, 1, 0, 0);
```

and `TERRAIN_CELLS` grows to 260, a 130 m square, enough to reach past
`maxDistance` in every direction. The corner is **snapped to whole cells**: the
grid's vertices then always sit at the same world positions, and only which
cells are drawn changes as the camera moves. A grid that moved continuously with
the camera would sample the hills at shifting points, and the ground would
visibly swim. It follows the *culling* camera, so a frozen view keeps its ground
too.

---

## 3. The generation pass

Now the GPU side. One compute pass looks at every candidate position in every
listed tile and decides whether a blade grows there, and what it looks like.

### The data, grown

**This is what `GrassTypes.h` gains.** `GrassBlade` itself does not change, but
its root's `y` is now filled: the generation pass asks the terrain once per
blade and stores the answer. Two debug views, LOD and tiles, used from section
5, follow Chapter 25's three:

```c
#define GRASS_VIEW_LOD      3u   /* Chapter 26: LOD 0 green, morphing yellow, LOD 1 blue */
#define GRASS_VIEW_TILES    4u   /* Chapter 26: a color per tile */
```

**`GrassParameters` grows by everything the compute passes need**, after
Chapter 25's `padding2`: the culling camera's six planes and position (sections
2-3); the range of shapes, which was hard-coded in Chapter 25's `CreateBlades`
(section 3); the tile size and how many candidates a tile side has; the two
capacities and the LOD distance (sections 4 and 5); the morph band (section 6);
and the thinning (section 7).

```c
    /* Chapter 26: generation, culling, and LOD. */
    vec4  frustumPlanes[6]; /* the culling camera's planes: xyz inward unit normal, w distance */
    vec4  cullPosition;     /* xyz: the culling camera's position; w unused */
    vec4  shapeMin;         /* the smallest height, width, tilt, and bend a blade is given */
    vec4  shapeMax;         /* and the largest */
    float tileSize;         /* metres */
    uint  bladesPerSide;    /* candidates per tile: bladesPerSide * bladesPerSide */
    uint  capacity0;        /* blades LOD 0's region holds; LOD 1's region starts here */
    uint  capacity1;        /* blades LOD 1's region holds */
    float lodDistance;      /* metres: LOD 0 nearer than this, LOD 1 beyond */
    float morphBand;        /* metres: LOD 0 turns into LOD 1's shape over this last stretch */
    float densityStart;     /* metres: every candidate grows nearer than this */
    float maxDistance;      /* metres: none grows beyond this */
    float farDensity;       /* the fraction of candidates still growing at maxDistance */
    float fadeBand;         /* how far below its cut a blade's size starts shrinking, 0..1 */
    uint  padding3;
    uint  padding4;
```

Planes are `vec4`s, so the array has std140's 16-byte stride in both languages.
The two padding words at the end keep the struct a multiple of 16 bytes.

**`GrassCounters`**, after `GrassTile`, is what the generation pass counts with
atomics: how many blades went into each level of detail.

```c
/* Chapter 26: what the generation pass counts. std430, set 1 binding 3. */
struct GrassCounters
{
    uint lodCount[2];     /* blades appended to each LOD's region; may run past its capacity */
    uint padding0;
    uint padding1;
};
```

**`GrassPush` grows a segment count** after `terrainGrid`, which tells the
vertex shader which level of detail it is drawing (section 5), and three
padding words that keep it a multiple of 16 bytes:

```c
    uint segmentCount;    /* Chapter 26: 7 for LOD 0, 3 for LOD 1 */
    uint padding0;
    uint padding1;
    uint padding2;
```

And the size checks, which replace Chapter 25's: `GrassParameters` is now 272
bytes with two more offsets pinned, `GrassPush` 32, and the two new structs are
checked too.

```c
    static_assert(sizeof(GrassParameters) == 272, "GrassParameters layout drifted.");
    static_assert(offsetof(GrassParameters, debugView) == 64, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, frustumPlanes) == 80, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, tileSize) == 224, "GrassParameters alignment drifted.");
    static_assert(sizeof(GrassTile) == 16, "GrassTile layout drifted.");
    static_assert(sizeof(GrassCounters) == 16, "GrassCounters layout drifted.");
    static_assert(sizeof(GrassPush) == 32, "GrassPush layout drifted.");
```

The whole file is in the Appendix.

### Buffers and set 1, grown

Chapter 25's set 1 had the blades and the parameters. The compute passes need
three more bindings: the tile list, the counters, and the two draw commands the
End pass writes. One set layout serves the draws and the compute passes both;
each binding lists the stages that read it.

**This is `CreateBuffers`, replacing `CreateBlades`:**

```cpp
InitializationResult GrassDemo::CreateBuffers()
{
    VulkanContext& vulkan = m_context.vulkan;

    // Written by compute and read by the draws: the GPU's alone, so device-local.
    m_blades   = createBuffer(vulkan, sizeof(GrassBlade) * (LOD0_CAPACITY + LOD1_CAPACITY),
                              VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, false);
    m_counters = createBuffer(vulkan, sizeof(GrassCounters),
                              VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT, false);
    m_commands = createBuffer(vulkan, 2 * sizeof(shared::DrawIndirectCommand),
                              VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT, false);
    if (m_blades.buffer == VK_NULL_HANDLE || m_counters.buffer == VK_NULL_HANDLE || m_commands.buffer == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the grass buffers failed.");
    }

    // Written by the CPU every frame, or read by it: one of each per frame in flight.
    for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
    {
        m_parameterBuffers[i] = createBuffer(vulkan, sizeof(GrassParameters), VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, true);
        m_tileBuffers[i]      = createBuffer(vulkan, sizeof(GrassTile) * MAX_TILES, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, true);
        m_readback[i]         = createReadbackBuffer(vulkan, sizeof(GrassCounters));
        if (m_parameterBuffers[i].buffer == VK_NULL_HANDLE || m_tileBuffers[i].buffer == VK_NULL_HANDLE ||
            m_readback[i].buffer == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a per-frame grass buffer failed.");
        }
    }
    return InitializationResult::success();
}
```

- **The blades, the counters, and the commands are the GPU's alone**, so they are
  device-local, and there is **one of each** shared by both frames in flight.
  Chapter 21 section 1 weighed the alternative — a copy per frame in flight — and
  chose one copy and a barrier at the top of each frame; the grass makes the same
  choice for the same reason, more strongly: the blade buffer is the biggest
  allocation in the demo, `(200,000 + 600,000) × 32` bytes, about 25 MB.
- **Usage bits say how each is used**: the counters are also copied out for the
  panel (`TRANSFER_SRC`, section 8), and the commands are read by
  `vkCmdDrawIndirect` (`INDIRECT_BUFFER`).
- **The parameters, the tiles, and the readback buffers are per frame in flight**:
  the CPU writes the first two, or reads the third, while the GPU may still be
  using the other frame's.

**This is `CreateDescriptors`:**

```cpp
InitializationResult GrassDemo::CreateDescriptors()
{
    const VkShaderStageFlags drawAndCompute = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_COMPUTE_BIT;
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1,   // blades
          .stageFlags = drawAndCompute },
        { .binding = 1, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, .descriptorCount = 1,   // parameters
          .stageFlags = drawAndCompute | VK_SHADER_STAGE_FRAGMENT_BIT },
        { .binding = 2, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1,   // tiles
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding = 3, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1,   // counters
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding = 4, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1,   // draw commands
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
    };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 5,
        .pBindings    = bindings,
    };
    if (vkCreateDescriptorSetLayout(m_context.vulkan.device, &setLayoutInfo, nullptr, &m_grassSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the grass.");
    }

    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 4 * FRAMES_IN_FLIGHT },
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

    // Bindings 1 and 2 are per frame in flight; 0, 3, and 4 are shared by both sets.
    for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
    {
        const VkDescriptorBufferInfo infos[] = {
            { .buffer = m_blades.buffer,              .offset = 0, .range = VK_WHOLE_SIZE },
            { .buffer = m_parameterBuffers[i].buffer, .offset = 0, .range = sizeof(GrassParameters) },
            { .buffer = m_tileBuffers[i].buffer,      .offset = 0, .range = VK_WHOLE_SIZE },
            { .buffer = m_counters.buffer,            .offset = 0, .range = VK_WHOLE_SIZE },
            { .buffer = m_commands.buffer,            .offset = 0, .range = VK_WHOLE_SIZE },
        };
        std::array<VkWriteDescriptorSet, 5> writes{};
        for (uint32_t binding = 0; binding < 5; ++binding)
        {
            writes[binding] = VkWriteDescriptorSet{
                .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                .dstSet          = m_grassSets[i],
                .dstBinding      = binding,
                .descriptorCount = 1,
                .descriptorType  = bindings[binding].descriptorType,
                .pBufferInfo     = &infos[binding],
            };
        }
        vkUpdateDescriptorSets(m_context.vulkan.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
    }
    return InitializationResult::success();
}
```

The two sets differ only in bindings 1 and 2, the per-frame buffers. Writing all
five bindings in one loop works because the array of buffer infos is in binding
order.

**In `Setup`**, `CreateBlades` becomes `CreateBuffers`:

```cpp
    if (auto result = CreateBuffers(); !result)     { return result; }   // section 3
```

### Set 1, as the compute passes see it

The vertex shader declares the blades `readonly`; the generation pass only
writes them. GLSL lets each shader declare a binding with the access it needs,
and the three compute passes share one include. **This is
`Shaders/Grass/GrassCompute.glsl`:**

```glsl
// Shaders/Grass/GrassCompute.glsl - set 1 as the three compute passes see it (Chapter 26).
// The graphics shaders declare the same bindings, with the access they need.
#ifndef PF_GRASS_COMPUTE_GLSL
#define PF_GRASS_COMPUTE_GLSL

layout(set = 1, binding = 0, std430) writeonly buffer BladeBlock   { GrassBlade blades[]; };
layout(set = 1, binding = 1)                   uniform GrassBlock   { GrassParameters grass; };
layout(set = 1, binding = 2, std430) readonly  buffer TileBlock    { GrassTile tiles[]; };
layout(set = 1, binding = 3, std430)           buffer CounterBlock { GrassCounters counters; };
layout(set = 1, binding = 4, std430) writeonly buffer CommandBlock { DrawIndirectCommand commands[2]; };

#endif
```

`DrawIndirectCommand` is Chapter 21's mirror of `VkDrawIndirectCommand`, from
`SharedShaderTypes.h`. `readonly` and `writeonly` are promises the compiler can
use; the counters are read and written, so they are neither.

### The pass

**This is `Shaders/Grass/GrassGenerate.comp.glsl`**, the whole pass. It reads
top to bottom as the life of one candidate blade, and the walkthrough after it
follows the same order. Two of its blocks are explained later, where they
belong: the thinning under `// Thinning` in section 7, and the append at the
end in section 4. Type the whole file now; those sections point back to it.

```glsl
// Shaders/Grass/GrassGenerate.comp.glsl - place, cull, and append every candidate blade (Chapter 26).
#version 450
#extension GL_GOOGLE_include_directive : require

#include "Random.glsl"
#include "GrassTypes.h"
#include "GrassCompute.glsl"
#include "Terrain.glsl"

layout(local_size_x = 64) in;

// A sphere is outside when it is wholly behind any one of the six planes.
bool sphereInFrustum(vec3 center, float radius)
{
    for (int i = 0; i < 6; ++i)
    {
        vec4 plane = grass.frustumPlanes[i];
        if (dot(plane.xyz, center) + plane.w < -radius) { return false; }
    }
    return true;
}

void main()
{
    // x: which candidate in the tile; y: which tile.
    uint perSide   = grass.bladesPerSide;
    uint candidate = gl_GlobalInvocationID.x;
    if (candidate >= perSide * perSide) { return; }
    GrassTile tile = tiles[gl_WorkGroupID.y];

    // The cell's WORLD coordinates name the blade, so the same blade grows in the
    // same place whichever tile list, frame, or invocation produced it.
    ivec2 cell  = ivec2(tile.x, tile.z) * int(perSide) + ivec2(candidate % perSide, candidate / perSide);
    uint  state = pcgHash(uint(cell.x) ^ pcgHash(uint(cell.y)));

    float spacing = grass.tileSize / float(perSide);
    vec2  xz      = (vec2(cell) + vec2(randomFloat(state), randomFloat(state))) * spacing;
    vec3  root    = vec3(xz.x, terrainHeight(xz, grass.terrainShape), xz.y);

    // Thinning: each blade draws its own cut once, and grows while the density
    // where it stands is above it. Just above the cut it shrinks instead of popping.
    float distanceToCamera = distance(root, grass.cullPosition.xyz);
    float along   = clamp((distanceToCamera - grass.densityStart) / (grass.maxDistance - grass.densityStart), 0.0, 1.0);
    float density = distanceToCamera > grass.maxDistance ? 0.0 : mix(1.0, grass.farDensity, along);
    float cut     = randomFloat(state);
    if (cut >= density) { return; }
    float grow    = clamp((density - cut) / grass.fadeBand, 0.0, 1.0);

    vec4 shape = mix(grass.shapeMin, grass.shapeMax,
                     vec4(randomFloat(state), randomFloat(state), randomFloat(state), randomFloat(state)));
    shape.xy *= grow;

    // Every point of the blade is within its height of the root, and its edges
    // within half its width more.
    if (!sphereInFrustum(root, shape.x + shape.y)) { return; }

    GrassBlade blade;
    blade.rootAndFacing = vec4(root, randomFloat(state) * 6.2831853);
    blade.shape         = shape;

    // Append to the LOD's region. Check-and-skip: the count may run past the
    // capacity, the write may not (Chapter 21).
    uint lod      = distanceToCamera < grass.lodDistance ? 0u : 1u;
    uint capacity = lod == 0u ? grass.capacity0 : grass.capacity1;
    uint slot     = atomicAdd(counters.lodCount[lod], 1u);
    if (slot < capacity)
    {
        blades[(lod == 0u ? 0u : grass.capacity0) + slot] = blade;
    }
}
```

**Which candidate.** The dispatch is two-dimensional: `y` is the tile, one row
of workgroups per tile, and `x` covers the tile's `bladesPerSide²` candidates in
workgroups of 64 — a multiple of every common subgroup size (Chapter 20
section 3). The last workgroup of a row runs past the candidates, so the bounds
check comes first. Every invocation of a workgroup shares one tile, so
`tiles[...]` is one read the whole group agrees on.

**A name from the world.** `cell` is the candidate's integer position in a grid
that covers the world: the tile's position times candidates per side, plus the
candidate's place in the tile. The random stream is seeded from that cell and
nothing else — the same shape as Chapter 21's `seedRandom`, with `y` in the
frame's place — so a blade is the same blade in every frame, from whichever
tile list and thread produced it. This is the Jump of section 1, in two lines.
Change `bladesPerSide` and every cell is renamed, so the field rearranges: that
is expected.

**Where it grows.** A random point in its cell, as in Chapter 25, and the
ground's height there, from the same `Terrain.glsl` the ground is drawn with.

**Whether it grows.** The thinning with distance, section 7's subject: past
`densityStart`, fewer and fewer candidates grow, and a blade near its cut shrinks
rather than vanishing. Until section 7, read it as "some far candidates return
early". It also works out `distanceToCamera`, which section 4 uses too.

**What it looks like.** Four random numbers pick a height, width, tilt, and bend
between `shapeMin` and `shapeMax`: Chapter 25's ranges, now on the panel.

**Whether it can be seen.** A sphere around the root, tested against the
culling camera's six planes. Its radius has to contain the whole blade: every
control point of the curve is within the blade's height of the root (`P3` is
exactly that far, `P1` and `P2` less), the curve never leaves its control
points' box (Chapter 25 section 6), and the edges are half a width further out.
So `height + width` is safely enough. Testing four points, or the curve's box,
would cull a few more blades at a few more instructions; a sphere is one dot
product per plane.

**Where it goes.** Section 4, next.

What the pass does **not** do is cull blades seen edge-on. Jahrmann and
Wimmer's grass (I3D 2017) drops blades whose face is nearly parallel to the view
direction, on the grounds that they cover almost no pixels; at a grazing angle
across a field that is most of them, and the field visibly thins. *Ghost of
Tsushima* keeps them and widens them in view space instead, which is Chapter 27
section 3.

### Writing the parameters

**`WriteFrameBuffers` takes the culling camera** — its frustum and position —
as two more parameters, here and in the header:

```cpp
void GrassDemo::WriteFrameBuffers(uint32_t frameIndex, const glm::mat4& view, const glm::mat4& projection,
                                  const scene::Frustum& cullFrustum, glm::vec3 cullPosition)
```

The parameters' designated initializer gains the new fields after `.debugView`,
in the struct's order:

```cpp
        .cullPosition  = glm::vec4(cullPosition, 0.0f),
        .shapeMin      = m_settings.shapeMin,
        .shapeMax      = m_settings.shapeMax,
        .tileSize      = TILE_SIZE,
        .bladesPerSide = static_cast<uint>(m_settings.bladesPerSide),
        .capacity0     = LOD0_CAPACITY,
        .capacity1     = LOD1_CAPACITY,
        .lodDistance   = m_settings.lodDistance,
        .morphBand     = std::max(m_settings.morphBand, 0.001f),
        .densityStart  = std::min(m_settings.densityStart, m_settings.maxDistance - 0.01f),
        .maxDistance   = m_settings.maxDistance,
        .farDensity    = m_settings.farDensity,
        .fadeBand      = m_settings.fadeBand,
```

and the planes are copied in after it, before the `memcpy`:

```cpp
    std::copy(cullFrustum.planes.begin(), cullFrustum.planes.end(), parameters.frustumPlanes);
```

The frustum's planes are copied into the fixed-size array with `std::copy`,
since a designated initializer cannot fill an array member from a
`std::array`. `densityStart` is kept just below `maxDistance`, because section
7's thinning divides by their difference, and `morphBand` at least a millimetre,
because section 6's `smoothstep` is undefined when its two edges meet, as they
would with the slider at 0.

---

## 4. Appending survivors, and the barriers around it

Thousands of invocations each decide, independently, that their blade survives,
and each needs a slot in the blade buffer that no other invocation takes. This
is Chapter 21's **append**: an atomic counter hands out slots. It is the last
block of the pass in section 3, under `// Append to the LOD's region`, and its
heart is one line, `uint slot = atomicAdd(counters.lodCount[lod], 1u);`.

`atomicAdd` returns the value *before* the add, so each invocation gets a
different slot, and the counter ends at the number of survivors. The blades end
up packed from slot 0 with no gaps, in no particular order — which does not
matter, because the draw only needs them packed.

**Unlike particles, this list can overflow.** Chapter 21's particles never
outnumber their pool, so they never check. The grass has a fixed capacity per
level of detail and no upper bound on how many candidates survive: a steep
hillside facing the camera, or a slider pushed to the right, can exceed it. So
the append has **two halves**:

- **Check, and skip.** The counter is always incremented — so it records how
  many blades *wanted* a slot, which the panel shows — but the blade is written
  only `if (slot < capacity)`. Writing past the end of the region
  would overwrite the other level's blades, or memory past the buffer.
- **Clamp.** The End pass draws `min(count, capacity)` blades, not `count`.

Blades beyond the capacity are simply not drawn. Which ones is up to the order
the GPU happened to run the invocations in, so an overflowing field flickers in
patches. The panel turns red when that happens (section 8), and the fix is a
bigger capacity or a lower density, not a smarter append.

Which region a blade goes to, LOD 0 or LOD 1, is section 5's subject; here it is
enough that there are two counters and two regions.

### Begin and End

The counters must start at zero every frame, and the draws need commands built
from where they finish. Each is a pass of one invocation, Chapter 21 section 3's
pattern. **This is `Shaders/Grass/GrassBegin.comp.glsl`:**

```glsl
// Shaders/Grass/GrassBegin.comp.glsl - one invocation: this frame's counts start at zero.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "GrassTypes.h"
#include "GrassCompute.glsl"

layout(local_size_x = 1) in;

void main()
{
    counters.lodCount[0] = 0u;
    counters.lodCount[1] = 0u;
}
```

**And `Shaders/Grass/GrassEnd.comp.glsl`:**

```glsl
// Shaders/Grass/GrassEnd.comp.glsl - one invocation: the counts become this frame's two draws.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "GrassTypes.h"
#include "GrassCompute.glsl"

layout(local_size_x = 1) in;

void main()
{
    // The counters may have run past capacity (the panel shows it); the draws may not.
    commands[0] = DrawIndirectCommand(15u, min(counters.lodCount[0], grass.capacity0), 0u, 0u);
    commands[1] = DrawIndirectCommand(7u,  min(counters.lodCount[1], grass.capacity1), 0u, grass.capacity0);
}
```

The End pass writes two `VkDrawIndirectCommand`s: 15 vertices for every LOD 0
blade, starting at instance 0; 7 vertices for every LOD 1 blade, starting at
instance `capacity0`. Section 5 explains the second one's `firstInstance`. A
single invocation is wasteful in the abstract and irrelevant in practice: it is
a few instructions, and the alternative — having the last generation workgroup
write the commands — needs a second atomic to find out which workgroup is last.

### The pipelines

**In `CreatePipelines`**, the layout and the two graphics descs are Chapter
25's. The three compute pipelines are created with the same layout, after the
graphics ones, and the check covers all five — the end of the function becomes:

```cpp
    const VkDevice        device = m_context.vulkan.device;
    const VkPipelineCache cache  = m_context.pipelineCache;
    m_terrainPipeline  = createGraphicsPipeline(device, cache, terrain);
    m_grassPipeline    = createGraphicsPipeline(device, cache, blades);
    m_beginPipeline    = createComputePipeline(device, cache, "Grass/GrassBegin.comp.spv", m_pipelineLayout);
    m_generatePipeline = createComputePipeline(device, cache, "Grass/GrassGenerate.comp.spv", m_pipelineLayout);
    m_endPipeline      = createComputePipeline(device, cache, "Grass/GrassEnd.comp.spv", m_pipelineLayout);
    if (m_terrainPipeline == VK_NULL_HANDLE || m_grassPipeline == VK_NULL_HANDLE ||
        m_beginPipeline == VK_NULL_HANDLE || m_generatePipeline == VK_NULL_HANDLE || m_endPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating a grass pipeline failed.");
    }
```

`createComputePipeline` is Chapter 20 section 2's.

One layout for five pipelines works because the compute passes and the draws
agree on set 1, and set 0 and the push constant are simply unused by the
compute shaders. A compute pipeline's layout may contain bindings and ranges its
shader never touches.

### Recording the compute

**This is `RecordGeneration`**, as it stands until section 8 adds two
timestamps:

```cpp
void GrassDemo::RecordGeneration(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t tileCount)
{
    // The return trip: last frame's draws, copy, and compute passes are done with
    // these buffers before this frame's compute passes write them again.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT |
                  VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_pipelineLayout,
                            1, 1, &m_grassSets[frameIndex], 0, nullptr);

    // Begin: the counters start at zero.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_beginPipeline);
    vkCmdDispatch(commandBuffer, 1, 1, 1);
    computeToComputeBarrier(commandBuffer);

    // Generate: one invocation per candidate, one row of workgroups per tile.
    if (tileCount > 0)
    {
        const uint32_t candidates = static_cast<uint32_t>(m_settings.bladesPerSide * m_settings.bladesPerSide);
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_generatePipeline);
        vkCmdDispatch(commandBuffer, groupCount(candidates, 64), tileCount, 1);
    }
    computeToComputeBarrier(commandBuffer);

    // End: the counts become the two draws.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_endPipeline);
    vkCmdDispatch(commandBuffer, 1, 1, 1);

    // Forward: the draws read the commands and the blades, the copy reads the counters.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_2_COPY_BIT,
                  VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_TRANSFER_READ_BIT);

    // Chapter 20 section 9: the counts, copied for the CPU to read FRAMES_IN_FLIGHT frames from now.
    const VkBufferCopy region{ .srcOffset = 0, .dstOffset = 0, .size = sizeof(GrassCounters) };
    vkCmdCopyBuffer(commandBuffer, m_counters.buffer, m_readback[frameIndex].buffer, 1, &region);
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
}
```

Five barriers, each answering Chapter 04 section 5's three questions. Chapter
20 section 5 explains why a compute pass needs a barrier after it at all, and
Chapter 21 section 4 the same chain of passes for particles; what follows is
what is particular to the grass.

**1. The return trip**, at the top. Last frame's draws read the commands
(`DRAW_INDIRECT`) and the blades (`VERTEX_SHADER`), its copy read the counters
(`COPY`), and its compute passes wrote all three. Nothing else orders this
frame's compute after any of that: the submission waits for the swapchain image
only at `COLOR_ATTACHMENT_OUTPUT`, so compute at the top of a frame can start
while the last frame is still drawing.

- **Q1:** all four of those stages finish before this frame's `COMPUTE_SHADER`
  work starts.
- **Q2:** last frame's compute writes are made available and visible to this
  frame's storage reads and writes. The reads need nothing flushed.
- **Q3:** buffers; no layouts.

It is Chapter 21's return trip, stage for stage.

**2. Begin → Generate.** Generate's atomics read and write the counters Begin
zeroed: a write, then a read-modify-write. `computeToComputeBarrier` (Chapter
20 section 5): **Q1** compute before compute; **Q2** `SHADER_STORAGE_WRITE`
made visible to `SHADER_STORAGE_READ | SHADER_STORAGE_WRITE`; **Q3** none.

**3. Generate → End.** End reads the counters Generate incremented, and the
same helper orders it. The layer cannot check this one (Chapter 20 section 5's
table); the three questions are the proof: without it End may read a count
that is still climbing.

**4. Forward: compute → the draws and the copy.** The two draws read the
commands at `DRAW_INDIRECT` and the blades at `VERTEX_SHADER`; the copy reads
the counters at `COPY`.

- **Q1:** compute finishes before indirect-argument fetch, vertex shading, and
  the copy start.
- **Q2:** `SHADER_STORAGE_WRITE` made visible to `INDIRECT_COMMAND_READ`,
  `SHADER_STORAGE_READ`, and `TRANSFER_READ`.
- **Q3:** buffers; no layouts.

Chapter 20 section 10's table has the first two rows; the copy adds a third
destination. Indirect-argument fetch is its own stage, `DRAW_INDIRECT`, before
the vertex shader, and its own access, `INDIRECT_COMMAND_READ`: a barrier to
`VERTEX_SHADER` alone would leave the draw reading a stale instance count.

**5. Copy → host.** The counters are copied into this frame slot's readback
buffer, which the CPU reads `FRAMES_IN_FLIGHT` frames later (section 8). The
barrier makes the copy's writes available to the host (`HOST` /
`HOST_READ`); the fence the CPU waits on before reading does the rest, exactly
as in Chapter 20 section 9.

**Seeing them fire.** Run with synchronization validation and the
shader-access setting on (Chapter 02 turns both on), and delete one barrier at
a time:

| Delete | What validation reports |
| --- | --- |
| 4, forward | `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDrawIndirect`, for the commands and the blades |
| 2, Begin → Generate | `SYNC-HAZARD-READ-AFTER-WRITE` at the Generate dispatch: Begin's plain store of the counters, then Generate's atomics, which the layer records as reads |
| 3, Generate → End | nothing — the writer is an atomic, which the layer cannot see as a write |
| 2 and 3 together | `SYNC-HAZARD-READ-AFTER-WRITE` at the Generate and End dispatches |
| 1, return trip | `SYNC-HAZARD-WRITE-AFTER-READ` at the submission: this frame's compute writes what last frame's indirect draw and counter copy read. If you did Part 2, only the copy is reported; section 9 says why |

Put each one back. The silent row is the one to remember: a clean run does not
prove that a barrier after an atomic is there.

### The first picture

`Record` now runs the compute before the scene pass — compute cannot run inside
a rendering scope (Chapter 20 section 1) — and draws the first region with
Chapter 25's pipeline. **After `WriteFrameBuffers`:**

```cpp
    // Compute first, outside any rendering scope (Chapter 20 section 1).
    RecordGeneration(commandBuffer, frameIndex, tileCount);
```

**And the blades' draw becomes**, for now:

```cpp
    // For now LOD 0's region only, with Chapter 25's shaders; section 5 draws LOD 1.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_grassPipeline);
    vkCmdDrawIndirect(commandBuffer, m_commands.buffer, 0, 1, sizeof(shared::DrawIndirectCommand));
```

Chapter 25's vertex shader still works unchanged: the blade struct is the same
size, it reads `blades[gl_InstanceIndex]`, and it still asks the terrain for the
root's height, which gives the same answer the compute pass stored.

You should see the field again — but only the nearest twelve metres of it: LOD
0's region. Fly in any direction: the grass comes with you, generated anew
every frame, and the blades at a given spot are always the same blades. Freeze
culling and fly up and out: a wedge of grass stands on bare ground, twelve
metres long and about as wide as the culling camera's view, its point cut off a
couple of metres in front of the camera, where the bottom of the view meets the
ground.

---

## 5. Two levels of detail

A blade fifty metres away covers a few pixels. Fifteen vertices to draw it are
wasted, and there are many more far blades than near ones. *Ghost of Tsushima*
draws near blades with **15 vertices** and far ones with **7**: the same curve,
sampled more coarsely.

### One buffer, two regions, two draws

The generation pass already sorts blades by distance (section 4's append):
nearer than `lodDistance`, into LOD 0; beyond, into LOD 1. Both levels live in
**one buffer**, LOD 0 in the first `capacity0` slots and LOD 1 in the
`capacity1` after them:

```text
 blades:  [ 0 ............ capacity0 ) [ capacity0 ................ capacity0 + capacity1 )
            LOD 0, 15 vertices each       LOD 1, 7 vertices each
 draw 0:    firstInstance 0               draw 1: firstInstance capacity0
```

The End pass writes two draws, and each says where its region starts with
`firstInstance`. **`gl_InstanceIndex` includes `firstInstance`** — it runs from
`firstInstance` to `firstInstance + instanceCount - 1` — so the vertex shader
reads `blades[gl_InstanceIndex]` without knowing which region it is in, or that
there are regions. A nonzero `firstInstance` written into an indirect command
needs the `drawIndirectFirstInstance` feature, which Chapter 19 section 6
enabled; without it the second draw would read LOD 0's blades on some GPUs and
work on others, and the core validation layer cannot tell you, because it never
reads the buffer.

The capacities, 200,000 and 600,000, are generous for the panel's default
density: in the default view about 12,000 blades land in LOD 0 and 90,000 in
LOD 1. Section 8's panel shows the real numbers.

### One pipeline, told the level

The two draws differ only in how many vertices make a blade, so they share a
pipeline, and a push constant says which level is being drawn: `segmentCount`,
7 or 3, set between the draws. The alternative, two pipelines with a
specialization constant, would save a branch per vertex; the branch is on a
value every invocation of a draw agrees on, which GPUs handle at almost no cost.

### Vertices where the curve bends

With seven segments spaced evenly in `t`, Chapter 25's blades already showed a
corner near the tip, where a bent blade turns fastest. With *three* segments it
would be a polyline. *Ghost of Tsushima* moves its vertices toward the tip.
Here the spacing is

`t(i) = 1 - (1 - i/7)²`

for vertex pair `i`: the steps shrink from 0.27 at the root to 0.02 at the tip,
which puts them where the curve changes direction.

The low level must also be **nested** in the high one, for section 6's sake:
its four vertex pairs are pairs 0, 2, 4, and 7 of the high level, at exactly the
same `t`. That is the `LOW_TO_HIGH` table. The low level's segments then run
between points that lie on the high level's blade, which is what lets the high
level fold itself onto the low one. In numbers, the high level's eight pairs sit
at

`t` = 0, 0.27, 0.49, 0.67, 0.82, 0.92, 0.98, 1

and the low level keeps the first, third, fifth, and last: 0, 0.49, 0.82, 1.
Its steps, 0.49, 0.33, and 0.18, crowd toward the tip the same way, with fewer
of them.

### The blade's shape, shared

Both levels evaluate the curve at arbitrary `t`, and section 6 evaluates it at
two more points per vertex, so the curve moves out of the vertex shader into an
include. **This is `Shaders/Grass/BladeShape.glsl`:**

```glsl
// Shaders/Grass/BladeShape.glsl - Chapter 25's curve, moved out of Grass.vert.glsl by
// Chapter 26 so that the vertex shader can evaluate it at any t, for either LOD.
#ifndef PF_GRASS_BLADE_SHAPE_GLSL
#define PF_GRASS_BLADE_SHAPE_GLSL

struct BladeCurve
{
    vec3  p0, p1, p2, p3;   // the four control points
    vec3  right;            // across the blade
    float width;            // at the root, metres
};

// Chapter 25's control points, unchanged. The root's height now comes with the
// blade: the generation pass asked the terrain once, instead of every vertex.
BladeCurve bladeCurve(GrassBlade blade)
{
    float facing = blade.rootAndFacing.w;
    vec3  up     = vec3(0.0, 1.0, 0.0);
    vec3  front  = vec3(sin(facing), 0.0, cos(facing));
    vec3  back   = -front;

    float height = blade.shape.x;
    float tilt   = blade.shape.z;
    float bend   = blade.shape.w;

    float lean  = tilt * 1.5707963;
    vec3  chord = cos(lean) * up + sin(lean) * back;
    vec3  arch  = sin(lean) * up - cos(lean) * back;

    BladeCurve curve;
    curve.p0    = blade.rootAndFacing.xyz;
    curve.p1    = curve.p0 + height * (chord / 3.0       + arch * bend * 0.5);
    curve.p2    = curve.p0 + height * (chord * 2.0 / 3.0 + arch * bend * 0.5);
    curve.p3    = curve.p0 + height * chord;
    curve.right = cross(up, front);
    curve.width = blade.shape.y;
    return curve;
}

vec3 bezier(BladeCurve curve, float t)
{
    float s = 1.0 - t;
    return s * s * s * curve.p0 + 3.0 * s * s * t * curve.p1 + 3.0 * s * t * t * curve.p2 + t * t * t * curve.p3;
}

vec3 bezierDerivative(BladeCurve curve, float t)
{
    float s = 1.0 - t;
    return 3.0 * s * s * (curve.p1 - curve.p0) + 6.0 * s * t * (curve.p2 - curve.p1) + 3.0 * t * t * (curve.p3 - curve.p2);
}

// One edge of the blade at t: side -1 is the left edge, +1 the right.
vec3 bladeEdge(BladeCurve curve, float t, float side)
{
    float halfWidth = 0.5 * curve.width * (1.0 - t * t);
    return bezier(curve, t) + curve.right * side * halfWidth;
}

vec3 bladeNormal(BladeCurve curve, float t)
{
    return normalize(cross(curve.right, bezierDerivative(curve, t)));
}

// LOD 0 has 7 segments (15 vertices), LOD 1 has 3 (7 vertices), and LOD 1's
// vertices are LOD 0's vertices number 0, 2, 4, and 7. Nested, so LOD 0 can
// fold itself flat onto LOD 1's shape.
const uint HIGH_SEGMENTS  = 7u;
const uint LOW_SEGMENTS   = 3u;
const uint LOW_TO_HIGH[4] = uint[](0u, 2u, 4u, 7u);

// Where LOD 0's vertex pair number i sits along the curve: crowded toward the
// tip, where the curve bends, and sparse at the straight root.
float segmentT(uint highSegment)
{
    float s = float(highSegment) / float(HIGH_SEGMENTS);
    return 1.0 - (1.0 - s) * (1.0 - s);
}

#endif
```

`bladeCurve` is Chapter 25's control points, gathered into a struct with the
two things every evaluation needs beside them, `right` and the width. The root
comes from the blade, height included. `bladeEdge` is a point on one edge;
`bladeNormal` is Chapter 25 section 7's normal. Nothing about the shape has
changed — set `segmentT` back to `i / 7` and LOD 0 is Chapter 25's blade exactly.

**This is `Grass.vert.glsl`, for this section:**

```glsl
// Shaders/Grass/Grass.vert.glsl - Chapter 26's version: either LOD (section 5).
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"
#include "Random.glsl"
#include "GrassTypes.h"
#include "BladeShape.glsl"

layout(set = 1, binding = 0, std430) readonly buffer BladeBlock { GrassBlade blades[]; };
layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };
layout(push_constant) uniform GrassPushBlock { GrassPush push; };

layout(location = 0) out vec3  worldPosition;
layout(location = 1) out vec3  worldNormal;
layout(location = 2) out float bladeT;
layout(location = 3) out float bladeSide;
layout(location = 4) out vec3  debugColor;   // what the LOD and tile views show

void main()
{
    // gl_InstanceIndex includes the draw's firstInstance: LOD 1's draw starts at
    // capacity0, so it reads LOD 1's region without knowing it has one.
    GrassBlade blade = blades[gl_InstanceIndex];
    BladeCurve curve = bladeCurve(blade);

    uint  segment     = uint(gl_VertexIndex) / 2u;           // 0 .. push.segmentCount
    float side        = (gl_VertexIndex & 1) == 0 ? -1.0 : 1.0;
    bool  lowLod      = push.segmentCount == LOW_SEGMENTS;
    uint  highSegment = lowLod ? LOW_TO_HIGH[segment] : segment;
    float t           = segmentT(highSegment);

    vec3 position = bladeEdge(curve, t, side);
    vec3 normal   = bladeNormal(curve, t);

    if (grass.debugView == GRASS_VIEW_TILES)
    {
        ivec2 tile = ivec2(floor(blade.rootAndFacing.xz / grass.tileSize));
        uint  hash = pcgHash(uint(tile.x) ^ pcgHash(uint(tile.y)));
        debugColor = vec3(hash & 255u, (hash >> 8) & 255u, (hash >> 16) & 255u) / 255.0;
    }
    else
    {
        debugColor = lowLod ? vec3(0.1, 0.3, 0.9) : vec3(0.1, 0.8, 0.1);
    }

    worldPosition = position;
    worldNormal   = normal;
    bladeT        = t;
    bladeSide     = side;
    gl_Position   = frame.viewProjection * vec4(position, 1.0);
}
```

`highSegment` is the vertex pair's number in the *high* level: the pair itself
for LOD 0, the `LOW_TO_HIGH` entry for LOD 1. From there both levels compute
`t`, the position, and the normal the same way. The debug color is decided here,
where the level and the tile are known, and passed down: the tile color is a hash
of the tile's coordinates, the same hash for every blade in it.

**In `Grass.frag.glsl`**, the two debug views need one input, after
`bladeSide`:

```glsl
layout(location = 4) in  vec3  debugColor;
```

and one test, right after `albedo` is worked out:

```glsl
    if (grass.debugView == GRASS_VIEW_LOD || grass.debugView == GRASS_VIEW_TILES)
    {
        albedo = debugColor * (0.35 + 0.65 * bladeT);   // still lit, so the shapes stay readable
    }
```

The LOD and tile colors replace the blade's color but keep the lighting, so the
shapes stay readable under the tint.

### The two draws

**In `Record`, the blades' draw becomes two:**

```cpp
    // The two LODs: the same pipeline, two commands the End pass wrote.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_grassPipeline);
    push.segmentCount = 7;
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
    vkCmdDrawIndirect(commandBuffer, m_commands.buffer, 0, 1, sizeof(shared::DrawIndirectCommand));

    push.segmentCount = 3;
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
    vkCmdDrawIndirect(commandBuffer, m_commands.buffer, sizeof(shared::DrawIndirectCommand), 1,
                      sizeof(shared::DrawIndirectCommand));
```

The push constant is pushed again before each draw, with the whole struct: the
ground's grid stays in it, unused by the blades. The second draw starts
`sizeof(DrawIndirectCommand)` bytes into the command buffer, where the End pass
put LOD 1's command.

The whole field is back, out to fifty metres in every direction you look. Set
View to **LOD**: green near, blue far, and a sharp line between them twelve
metres out. Walk forward slowly and watch that line: blades crossing it change
shape in one frame, visibly — tips jump, curves straighten. Section 6 removes
that.

---

## 6. Hiding the switch

A 7-vertex blade is not the 15-vertex blade with fewer vertices: its three
straight segments cut the corners of the curve. At the switch the shape jumps,
and across a field of moving blades that jump reads as a band of shimmer that
travels with the camera.

> **Jump:** the fix is to change the high level *before* the switch, so that at
> the switch distance it has already become the low level's shape. This is a
> **geomorph**: a mesh whose vertices slide, as a function of distance, from
> where its detailed shape puts them to where its coarse shape would. The part
> to keep in mind is *which* coarse shape: not "the curve with fewer points", but
> the low level's actual **polyline** — straight lines between the four nested
> vertex pairs. Every high-level vertex has a place on that polyline (it lies
> between two of the low level's vertices along `t`), and morphing moves it
> there in a straight line. At the switch distance the 15-vertex blade is
> exactly the 7-vertex polyline, drawn with more vertices than it needs, and
> swapping one for the other changes nothing on screen. Holding on to "nested
> levels" from section 5 is what makes this possible.

The picture, for one edge of a blade. Along `t` the levels are nested:

```text
   high level:  0      1      2     3     4    5   6  7      ● every pair
                ●------●------◉-----●-----◉----●---●--◉      ◉ the pairs both levels share
   low level:   ◉-------------◉-----------◉-----------◉
                0             2           4           7
```

and side-on, between two shared pairs, the curve bulges where the low level
draws a straight line. Pair 3 slides from one onto the other as the blade nears
the switch:

```text
        morph = 0                         morph = 1

             ● 3
         .--' '--.
   2 ◉--'         '--◉ 4            2 ◉-------●-------◉ 4
                                              3
   pair 3 on the curve              pair 3 on the straight segment, at the
                                    same fraction of the way from 2 to 4
```

*Ghost of Tsushima*'s high level morphs toward the low level's shape before the
switch. **This is the morph**, added to `Grass.vert.glsl` after the position and
normal are computed:

```glsl
    // LOD 0 near the switch distance slides its vertices onto LOD 1's straight
    // segments; at the switch the two are the same shape and nothing pops.
    float morph = 0.0;
    if (!lowLod)
    {
        float distanceToCamera = distance(blade.rootAndFacing.xyz, grass.cullPosition.xyz);
        morph = smoothstep(grass.lodDistance - grass.morphBand, grass.lodDistance, distanceToCamera);

        uint  low = highSegment < LOW_TO_HIGH[1] ? 0u : (highSegment < LOW_TO_HIGH[2] ? 1u : 2u);
        float ta  = segmentT(LOW_TO_HIGH[low]);
        float tb  = segmentT(LOW_TO_HIGH[low + 1u]);
        float f   = (t - ta) / (tb - ta);
        vec3  onLowLod   = mix(bladeEdge(curve, ta, side), bladeEdge(curve, tb, side), f);
        vec3  lowLodNormal = normalize(mix(bladeNormal(curve, ta), bladeNormal(curve, tb), f));
        position = mix(position, onLowLod, morph);
        normal   = normalize(mix(normal, lowLodNormal, morph));
    }
```

and the LOD view's color shows how far along the morph is, yellow at the end:

```glsl
        debugColor = lowLod ? vec3(0.1, 0.3, 0.9) : mix(vec3(0.1, 0.8, 0.1), vec3(0.9, 0.8, 0.1), morph);
```

Step by step:

- **`morph`** is 0 nearer than `lodDistance - morphBand` and 1 at `lodDistance`,
  with a smooth ramp between: the 15-vertex curve becomes the polyline over the
  last `morphBand` metres before the switch. The ramp is
  **`smoothstep(a, b, x)`** (Chapter 16 section 5): 0 below `a`, 1 above `b`,
  and between them an S-shaped curve. With `s = (x - a) / (b - a)` it is
  `3s² - 2s³`, which leaves 0 and arrives at 1 flat, so the morph eases in and out instead of starting with
  a jolt. With the defaults, a 12 m switch and a 4 m band, a root 8 m away gets
  0, 10 m gets 0.5, 11 m gets 0.84, and 12 m gets 1. The distance is the root's
  distance from the *culling* camera — the same distance the generation pass
  used to choose the level, so the morph ends exactly where the switch is.
- **`low`** is which of the low level's three segments this vertex lies on;
  `ta` and `tb` are that segment's ends, and `f` how far between them this
  vertex is in `t`.
- **`onLowLod`** is the point on the straight segment between the low level's
  two vertices at `ta` and `tb`, at the same fraction. Both ends are *on the
  curve*, so the polyline is evaluated exactly where the low level will draw it.
- **The normal morphs too**, to the normal the low level will interpolate along
  that segment; otherwise the shading would jump at the switch even with the
  shape matched.

Only LOD 0 morphs; LOD 1 is already the polyline.

Measured on one machine, the morph cuts what changes on screen when blades
cross the switch to about a thirtieth of what it was; what is left is MSAA
sampling the edges of segments that moved by a fraction of a pixel.

Walk forward again with View on **LOD**: the green band turns yellow before it
turns blue, and on **Shaded** the line where blades change is gone. Set "Morph
band" to 0 to see what it was hiding.

---

## 7. Thinning with distance

LOD 1 makes far blades cheaper; it does not make them fewer, and there are a
great many of them: the area of a ring of ground grows with its distance, so
most candidates are far away. The ring between 40 and 50 m is
π(50² − 40²) = 900π m², nine times the 100π m² of the whole disc within 10 m.
Far blades also matter least: at fifty metres a blade is a pixel wide, and ten
of them in a pixel look much like three. So the
field thins with distance — every candidate grows near the camera, fewer and
fewer further out, none past `maxDistance`.

The falloff here is this tutorial's, and the panel exposes every number in it.
It is the block under `// Thinning` in section 3's listing of
`GrassGenerate.comp.glsl`, plus the line `shape.xy *= grow;` after the shape is
picked. Read it against these three steps:

- **The density** is 1 out to `densityStart`, falls in a straight line to
  `farDensity` at `maxDistance`, and is 0 beyond: the fraction of candidates
  that grow at that distance.
- **Each candidate draws its own `cut`**, a random number from its cell's stream,
  and grows while the density where it stands is above it. The cut is the
  blade's own, the same every frame, so as the camera walks away a blade
  disappears at one fixed distance and comes back at the same distance: the
  field thins in a stable order, not by flickering.
- **Just above its cut, a blade shrinks instead of vanishing.** `grow` is 1
  while the density is more than `fadeBand` above the cut, and falls to 0 as it
  reaches it; height and width are multiplied by it. A blade that would have
  popped out of existence at one distance instead dwindles to nothing over a
  short stretch.

Thinning removes blades but not the ground's coverage, so at the far edge bare
ground starts to show through. Chapter 27 section 6 has the ground take on the
grass's color as the blades thin, which is what makes a sparse far field read as
dense.

`densityStart` must stay below `maxDistance`, since their difference is
divided by; `WriteFrameBuffers` keeps it a centimetre short.

Move "Thinning starts" toward the camera and the field gets visibly sparser
in the distance; drag "Density at the end" to 1 and the field is full right up
to its edge, which then stands out as a sharp line; drag "Fade band" toward 0
and blades start to pop as you walk.

---

## 8. Budgets you can see

The CPU no longer knows how much grass there is, or what it costs. Both can be
asked of the GPU, and both answers come back a frame or two late, which is fine
for a panel.

### Counts

`RecordGeneration` already copies the counters into this frame slot's readback
buffer (section 4). They are read when this frame slot comes round again,
`FRAMES_IN_FLIGHT` frames later, right after its fence has been waited — by
then the GPU is done with them, and reading costs no stall. Chapter 20 section 9
explains the arrangement; Chapter 21 section 7 uses it for particles.

### Time

Five timestamps a frame bracket three regions: the compute passes, the LOD 0
draw, and the LOD 1 draw. This is the fourth pass in the tutorial to time
itself, so it uses Chapter 24 section 9's `GpuTimestamps` rather than a fourth
copy of Chapter 21's code: the header's `m_timestamps` is one, of
`TIMESTAMP_COUNT` (5) timestamps a frame. The class keeps Chapter 21's rules —
a pool per frame in flight, reset before use, read after the fence, every
difference masked to the valid bits — and does nothing at all on a device
without timestamps. `Setup` initializes it after `CreatePipelines`:

```cpp
    if (auto result = m_timestamps.Initialize(m_context.vulkan, TIMESTAMP_COUNT); !result)
    {
        return result;   // Chapter 26 section 8: Chapter 24's GpuTimestamps
    }
```

The first timestamp is the first line of `RecordGeneration`:

```cpp
    m_timestamps.Write(commandBuffer, frameIndex, 0);
```

the second goes right after the End dispatch, before the forward barrier:

```cpp
    m_timestamps.Write(commandBuffer, frameIndex, 1);
```

and the other three in `Record`: `2` right after the ground's `vkCmdDraw`, `3`
after LOD 0's `vkCmdDrawIndirect`, and `4` after LOD 1's. Before any of them,
outside any rendering scope, `Record` resets this frame's pool, just before it
calls `RecordGeneration`:

```cpp
    m_timestamps.Reset(commandBuffer, frameIndex);
```

So each difference is the time from one point to the next: the compute passes
(0 to 1), LOD 0 (2 to 3), and LOD 1 (3 to 4). A timestamp is written when
everything recorded before it has finished, so these are bounds on the work
between them, not exact costs, and on a GPU that overlaps draws they can even
read zero. They are good enough to say which pass is the expensive one, which
is what a budget needs.

**This is `ReadStatistics`**, which `Record` calls first:

```cpp
// What this slot's previous frame produced and cost. Record calls it first: the
// fence for this slot has been waited, so both are final, and nothing stalls.
void GrassDemo::ReadStatistics(uint32_t frameIndex)
{
    if (!m_readbackPending[frameIndex]) { return; }
    m_readbackPending[frameIndex] = false;

    GrassCounters counters{};
    readBuffer(m_context.vulkan, m_readback[frameIndex], &counters, sizeof(counters));

    m_statistics.tiles       = m_tileCounts[frameIndex];
    m_statistics.candidates  = m_candidateCounts[frameIndex];
    m_statistics.lodCount[0] = counters.lodCount[0];
    m_statistics.lodCount[1] = counters.lodCount[1];
    if (m_timestamps.Read(frameIndex))   // false on a device without timestamps: the last numbers stand
    {
        m_statistics.generateMs = m_timestamps.Milliseconds(0, 1);
        m_statistics.lod0Ms     = m_timestamps.Milliseconds(2, 3);
        m_statistics.lod1Ms     = m_timestamps.Milliseconds(3, 4);
    }
}
```

`Milliseconds` masks and converts, as Chapter 21 did by hand. `m_readbackPending`
keeps the first frames — before anything was recorded into a slot — from
reading garbage.

### The frame, complete

`Record` is now complete for this chapter, and the Appendix lists it whole. In
order: last results in; the culling camera, the tiles, and the parameters;
the compute, before any rendering scope; Chapter 17's shadow pass and Chapter
19's draws prepared; then the scene pass — stones, ground, LOD 0, LOD 1. This
frame's timestamps are reset before the first one, outside any rendering scope,
as the `vkCmdResetQueryPool` inside `GpuTimestamps::Reset` requires.

**At the end of `Setup`** the readback flags are cleared, because no slot holds
results yet:

```cpp
    // Nothing has been copied into a readback buffer, or timed, yet.
    m_readbackPending.fill(false);
```

**`Teardown`** destroys everything this chapter creates, in the reverse order
of creation, and puts each handle back to null: Chapter 25 section 8's pattern,
now with `m_timestamps.Shutdown()`, the three compute pipelines, and the new
buffers. The Appendix lists it.

### What the numbers say

The default view generates about 160 tiles — 260,000 candidates — and draws
about 12,000 LOD 0 and 90,000 LOD 1 blades. The timings are for saying which
pass dominates. On one machine it was the draws, by far, and LOD 1 more than
LOD 0, because it has seven times the blades for half the vertices each; check
the proportions on yours, where the generation pass should cost a small
fraction of a millisecond. Things to try with the panel open:

- **Raise "Blades per tile side"** until a capacity turns red. The counts keep
  climbing past the capacity; the draws stop at it.
- **Pull "Grass ends" in** and watch the candidates, the LOD 1 count, and the LOD
  1 time fall together.
- **Freeze culling and turn round**: the counts stay what they were, because the
  culling camera did not move, and the draws still cost their vertex work while
  nothing they draw is in view — the clearest demonstration that it is the
  culling that saves the time.

## Checkpoint

Part 1 is complete. Run with `--demo Grass` and you can now see and check:

- an endless field that comes with you as you fly, the same blades at the same
  spots whenever you return;
- with "Freeze culling" on, the wedge of tiles and blades the frozen camera
  generated, thinning toward its far edge;
- View **Tiles**: 4 m squares, each its own color; View **LOD**: green near,
  yellow across the morph band, blue far, and no line of popping blades as you
  walk forward;
- the panel's counts and timings updating, and the capacity warning when
  "Blades per tile side" is pushed high;
- no validation messages.

If you stop here, Chapter 27 works as it is: skip to it.

---

# Part 2 — Optional: occlusion culling (section 9)

Part 2 culls blades that last frame's depth says were hidden. It is the largest
jump in the three grass chapters, nothing later depends on it, and Chapter 27
works with or without it. Skip it the first time through if you like; where
Chapter 27 meets its code, it says what to leave out.

## 9. Occlusion culling against last frame's depth

Stand in a field at eye height and look across it. The frustum is full of
blades, and most of them are hidden — behind the blades in front, behind the
next hill. Every one of them is generated, appended, and drawn, and its pixels
lose the depth test. With the eye half a metre above the ground, more than half
of LOD 1 is like that.

**Occlusion culling** asks, for each blade, whether something already drawn
covers it. The technique here is **hierarchical-Z** culling, from GPU-driven
renderers: Haar and Aaltonen's "GPU-Driven Rendering Pipelines" (SIGGRAPH 2015)
and Wihlidal's "Optimizing the Graphics Pipeline with Compute" (GDC 2016).

> **Jump:** three ideas at once, each new.
>
> **A pyramid of farthest depths.** Reduce the depth image by halves, each texel
> keeping the *farthest* depth of the four below it. Then a rectangle of any size
> on screen can be tested with four reads: at the level where it spans two
> texels, those four texels' farthest depth is the farthest depth *anything*
> drawn in that rectangle had. If the blade's nearest point is farther still, it
> was behind all of it.
>
> **Last frame's depth, with last frame's camera.** This frame's depth does not
> exist yet when this frame's blades are generated. Last frame's does, so the
> test asks "*was* this blade hidden?": project it with last frame's matrices,
> compare with last frame's depth. While the camera moves smoothly that is almost
> always the same answer; where it is not, a blade can appear one frame late.
>
> **Borrowing the renderer's depth image.** The depth buffer belongs to the scene
> pass (Chapter 10). The grass reads it after the pass, as a sampled image, and
> must hand it back as a depth attachment before the next frame's pass — the
> return trip Chapter 10 section 9 assigns to every later reader.

The pyramid, small enough to work by hand. Depth is 0 near and 1 far (Chapter
10 section 9), so "farthest" is the largest:

```text
   depth image, 4 × 4           level 0, 2 × 2        level 1, 1 × 1

   0.2  0.3 │ 0.9  0.9           0.6 │ 0.9               0.9
   0.6  0.4 │ 0.8  0.7          ─────┼─────
   ─────────┼─────────           0.5 │ 0.8
   0.5  0.5 │ 0.3  0.8
   0.5  0.4 │ 0.2  0.1          each texel: the largest of the four below it
```

A blade whose nearest depth is 0.7 and which covers only the top-left quarter
of the screen reads level 0's 0.6: nothing drawn there was farther than 0.6, so
all of it was in front of the blade, and the blade is culled. If it covers the
whole screen it reads level 1's 0.9, and 0.7 is not farther than that, so
something drawn there may have been behind it: the blade is kept.

### What changes

The pyramid is window-sized, so it is the first thing the grass owns that
`Resize` must rebuild. Everything else is additions. **In `GrassTypes.h`**, the
parameters grow, after `padding4`:

```c
    /* Chapter 26 section 9 (optional): occlusion against last frame's depth. Zero without it. */
    mat4  occlusionViewProjection;  /* last frame's viewProjection: the one its depth was drawn with */
    vec4  occlusionPyramid;         /* xy: level 0's size in texels, z: its level count, w: 1 to test */
```

the counters' two padding words become a count and one padding word:

```c
    uint occluded;        /* section 9: candidates the depth pyramid hid */
    uint padding0;
```

and the size check becomes 352 bytes, with one more offset pinned:

```c
    static_assert(sizeof(GrassParameters) == 352, "GrassParameters layout drifted.");
    static_assert(offsetof(GrassParameters, occlusionViewProjection) == 272, "GrassParameters alignment drifted.");
```

`GrassCompute.glsl` gains the pyramid at binding 5:

```glsl
layout(set = 1, binding = 5)                   uniform sampler2D    depthPyramid;   // section 9
```

and `GrassBegin.comp.glsl` zeroes the new count:

```glsl
    counters.occluded    = 0u;
```

**In `GrassDemo.h`**, a setting, a statistic, four functions, a constant, and
the pyramid's objects:

```cpp
    bool      occlusionCulling  = true;     // section 9 (optional)
```

```cpp
    uint32_t occluded     = 0;    // section 9
```

```cpp
    InitializationResult CreateOcclusionObjects();                                     // section 9 (optional)
    InitializationResult CreatePyramid(const vulkan_graphics::SceneTargets& targets);  // section 9, from Resize
    void                 DestroyPyramid();                                             // section 9
    void RecordDepthPyramid(VkCommandBuffer commandBuffer, const vulkan_graphics::SceneTargets& targets);   // section 9
```

```cpp
    static constexpr uint32_t MAX_PYRAMID_LEVELS   = 16;  // section 9: enough for a 65536-pixel-wide window
```

```cpp
    // Section 9 (optional): last frame's depth as a pyramid of farthest depths.
    VkImage                      m_pyramid           = VK_NULL_HANDLE;
    VmaAllocation                m_pyramidAllocation = VK_NULL_HANDLE;
    VkImageView                  m_pyramidView       = VK_NULL_HANDLE;   // every level: what the generation pass samples
    std::vector<VkImageView>     m_pyramidLevelViews;                    // one per level: what the reduce pass writes
    VkExtent2D                   m_pyramidExtent{};
    uint32_t                     m_pyramidLevels     = 0;
    bool                         m_pyramidValid      = false;            // holds a finished frame's depth
    glm::mat4                    m_previousViewProjection{ 1.0f };       // the camera that depth was drawn from
    VkSampler                    m_nearestSampler    = VK_NULL_HANDLE;
    VkDescriptorSetLayout        m_reduceSetLayout   = VK_NULL_HANDLE;
    VkDescriptorPool             m_reducePool        = VK_NULL_HANDLE;
    std::vector<VkDescriptorSet> m_reduceSets;                           // one per level
    VkPipelineLayout             m_reduceLayout      = VK_NULL_HANDLE;
    VkPipeline                   m_reducePipeline    = VK_NULL_HANDLE;
```

### The pyramid

Level 0 is half the depth image's size, rounded up, so each of its texels
covers a 2 × 2 block of depth; every level after that is the usual mip chain,
each half the one before, **rounded down**, down to 1 × 1. Rounding down means
an odd-sized level has a last column or row that no 2 × 2 block below reaches,
so the last texel of each row and column takes whatever is left over, three
texels instead of two. Nothing is skipped, and the pyramid stays conservative.

Its format is `R32_SFLOAT`, one depth per texel, and it lives in `GENERAL`
layout for its whole life: the reduce pass writes it as a storage image and
reads the level above as a sampled one, and the generation pass samples it, all
of which `GENERAL` allows. Keeping one layout means no layout transitions, only
memory barriers.

**This is `Shaders/Grass/GrassDepthReduce.comp.glsl`:**

```glsl
// Shaders/Grass/GrassDepthReduce.comp.glsl - one level of the depth pyramid (Chapter 26 section 9).
// Each texel keeps the FARTHEST depth of the 2x2 block above it: anything behind
// that is behind everything the block saw.
#version 450

layout(local_size_x = 8, local_size_y = 8) in;

layout(set = 0, binding = 0) uniform sampler2D source;                 // the level above, or the depth image
layout(set = 0, binding = 1, r32f) uniform writeonly image2D target;   // this level

void main()
{
    ivec2 texel      = ivec2(gl_GlobalInvocationID.xy);
    ivec2 targetSize = imageSize(target);
    if (any(greaterThanEqual(texel, targetSize))) { return; }

    // A mip level is half the one above, rounded DOWN, so an odd source has a
    // column or row no 2x2 block reaches. The last texel of each row and column
    // takes whatever is left, and nothing is skipped.
    ivec2 sourceSize = textureSize(source, 0);
    ivec2 first      = texel * 2;
    ivec2 last       = min(mix(first + 1, sourceSize - 1, equal(texel, targetSize - 1)), sourceSize - 1);

    float farthest = 0.0;
    for (int y = first.y; y <= last.y; ++y)
    {
        for (int x = first.x; x <= last.x; ++x)
        {
            farthest = max(farthest, texelFetch(source, ivec2(x, y), 0).r);
        }
    }
    imageStore(target, texel, vec4(farthest));
}
```

One invocation per texel of the level being written, 8 × 8 per workgroup. It
reads its block from the level above (or, for level 0, from the depth image)
with `texelFetch`, which ignores filtering and takes integer coordinates, and
keeps the **largest** depth: in Chapter 10's depth range, 0 is near and 1 far, so
the largest is the farthest. It has its own set layout — one source, one target
— which is set 0 of its own pipeline layout, unrelated to the grass's.

**This is `CreateOcclusionObjects`**, called from `Setup`: everything the
pyramid needs whatever the window's size.

```cpp
// Section 9: what the depth pyramid needs whatever the window's size - a sampler,
// and the reduce pass's set layout, pool, pipeline layout, and pipeline.
InitializationResult GrassDemo::CreateOcclusionObjects()
{
    const VkDevice device = m_context.vulkan.device;

    // texelFetch ignores filtering, but a combined image sampler needs one.
    const VkSamplerCreateInfo samplerInfo{
        .sType        = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter    = VK_FILTER_NEAREST,
        .minFilter    = VK_FILTER_NEAREST,
        .mipmapMode   = VK_SAMPLER_MIPMAP_MODE_NEAREST,
        .addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .maxLod       = VK_LOD_CLAMP_NONE,
    };
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1,   // source
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .descriptorCount = 1,           // target
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
    };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 2,
        .pBindings    = bindings,
    };
    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, MAX_PYRAMID_LEVELS },
        { VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, MAX_PYRAMID_LEVELS },
    };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = MAX_PYRAMID_LEVELS,
        .poolSizeCount = 2,
        .pPoolSizes    = poolSizes,
    };
    if (vkCreateSampler(device, &samplerInfo, nullptr, &m_nearestSampler) != VK_SUCCESS ||
        vkCreateDescriptorSetLayout(device, &setLayoutInfo, nullptr, &m_reduceSetLayout) != VK_SUCCESS ||
        vkCreateDescriptorPool(device, &poolInfo, nullptr, &m_reducePool) != VK_SUCCESS)
    {
        return InitializationResult::failure("Creating the depth pyramid's sampler or descriptors failed.");
    }

    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType          = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount = 1,
        .pSetLayouts    = &m_reduceSetLayout,
    };
    if (vkCreatePipelineLayout(device, &layoutInfo, nullptr, &m_reduceLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the depth pyramid.");
    }
    m_reducePipeline = createComputePipeline(device, m_context.pipelineCache, "Grass/GrassDepthReduce.comp.spv",
                                             m_reduceLayout);
    if (m_reducePipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the depth pyramid pipeline failed.");
    }
    return InitializationResult::success();
}
```

The sampler is nearest-neighbour with no LOD clamp: `texelFetch` ignores the
filter, but a combined image sampler must have a sampler. The pool holds one set
per level, up to 16 levels, a 65,536-pixel-wide window's worth.

**In `Setup`**, after the timestamps:

```cpp
    if (auto result = CreateOcclusionObjects(); !result) { return result; }   // section 9 (optional)
```

**This is `CreatePyramid`**, the window-sized part:

```cpp
// Section 9: the pyramid, sized from the window - level 0 is half the depth image,
// rounded up, and every level after is Vulkan's usual half, rounded down.
InitializationResult GrassDemo::CreatePyramid(const SceneTargets& targets)
{
    VulkanContext& vulkan = m_context.vulkan;
    m_pyramidExtent = { std::max(1u, (targets.extent.width + 1) / 2), std::max(1u, (targets.extent.height + 1) / 2) };
    m_pyramidLevels = static_cast<uint32_t>(std::floor(std::log2(static_cast<float>(
                          std::max(m_pyramidExtent.width, m_pyramidExtent.height))))) + 1;
    m_pyramidLevels = std::min(m_pyramidLevels, MAX_PYRAMID_LEVELS);

    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R32_SFLOAT,
        .extent        = { m_pyramidExtent.width, m_pyramidExtent.height, 1 },
        .mipLevels     = m_pyramidLevels,
        .arrayLayers   = 1,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(vulkan.allocator, &imageInfo, &allocationInfo, &m_pyramid, &m_pyramidAllocation, nullptr) != VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for the depth pyramid.");
    }

    // One view of every level for the generation pass, and one per level for the reduce pass.
    VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_pyramid,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = VK_FORMAT_R32_SFLOAT,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, m_pyramidLevels, 0, 1 },
    };
    if (vkCreateImageView(vulkan.device, &viewInfo, nullptr, &m_pyramidView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the depth pyramid.");
    }
    m_pyramidLevelViews.assign(m_pyramidLevels, VK_NULL_HANDLE);
    for (uint32_t level = 0; level < m_pyramidLevels; ++level)
    {
        viewInfo.subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, level, 1, 0, 1 };
        if (vkCreateImageView(vulkan.device, &viewInfo, nullptr, &m_pyramidLevelViews[level]) != VK_SUCCESS)
        {
            return InitializationResult::failure("vkCreateImageView failed for a depth pyramid level.");
        }
    }

    // GENERAL from the start and for good: storage writes and sampled reads both
    // work in it, and the generation pass's descriptor names it.
    immediateSubmit(vulkan, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, m_pyramid, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    });

    // The reduce pass's sets: level 0 reads the depth image, every other level the one above.
    vkResetDescriptorPool(vulkan.device, m_reducePool, 0);
    std::vector<VkDescriptorSetLayout> layouts(m_pyramidLevels, m_reduceSetLayout);
    m_reduceSets.assign(m_pyramidLevels, VK_NULL_HANDLE);
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_reducePool,
        .descriptorSetCount = m_pyramidLevels,
        .pSetLayouts        = layouts.data(),
    };
    if (vkAllocateDescriptorSets(vulkan.device, &allocateInfo, m_reduceSets.data()) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the depth pyramid.");
    }
    for (uint32_t level = 0; level < m_pyramidLevels; ++level)
    {
        const VkDescriptorImageInfo source{
            .sampler     = m_nearestSampler,
            .imageView   = level == 0 ? targets.depthView : m_pyramidLevelViews[level - 1],
            .imageLayout = level == 0 ? VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL : VK_IMAGE_LAYOUT_GENERAL,
        };
        const VkDescriptorImageInfo target{ .imageView = m_pyramidLevelViews[level], .imageLayout = VK_IMAGE_LAYOUT_GENERAL };
        const VkWriteDescriptorSet writes[] = {
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_reduceSets[level], .dstBinding = 0,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &source },
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_reduceSets[level], .dstBinding = 1,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .pImageInfo = &target },
        };
        vkUpdateDescriptorSets(vulkan.device, 2, writes, 0, nullptr);
    }

    // And the generation pass's binding 5, in both frames' sets.
    const VkDescriptorImageInfo pyramidInfo{
        .sampler = m_nearestSampler, .imageView = m_pyramidView, .imageLayout = VK_IMAGE_LAYOUT_GENERAL };
    for (VkDescriptorSet set : m_grassSets)
    {
        const VkWriteDescriptorSet write{
            .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = set, .dstBinding = 5,
            .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &pyramidInfo };
        vkUpdateDescriptorSets(vulkan.device, 1, &write, 0, nullptr);
    }

    m_pyramidValid = false;   // nothing reduced into it yet
    return InitializationResult::success();
}
```

- **The level count** is Vulkan's mip rule for the level-0 size,
  `floor(log2(largest side)) + 1`; one more level than that is invalid, and the
  validation layer says so (`VUID-VkImageCreateInfo-mipLevels-00958`).
- **Two kinds of view**: one of every level, which the generation pass samples at
  whatever level it chooses, and one per level, which the reduce pass writes and
  the next level reads.
- **The layout goes to `GENERAL` once**, in a one-off submission. Its three
  questions: **Q1** nothing before it (a new image), compute after it; **Q2**
  nothing to make available, and the storage writes that follow must see the new
  layout; **Q3** `UNDEFINED` to `GENERAL`. The next frame's work is later in
  submission order on the same queue, so the barrier's second half reaches it.
- **The reduce sets**: level 0 reads the depth image, in the
  `SHADER_READ_ONLY_OPTIMAL` layout `RecordDepthPyramid` puts it in; every other
  level reads the one above, in `GENERAL`.
- **Binding 5 of both grass sets** is pointed at the whole pyramid. Until a
  pyramid exists that binding is unwritten, which is legal as long as nothing
  that uses it runs: `Resize` runs after every `Setup`, before the first frame
  (Chapter 09 section 2), so it always has.
- **`m_pyramidValid` is cleared**: a new pyramid holds nothing yet, and the
  generation pass must not cull against it until a frame has filled it.

**This is `DestroyPyramid`:**

```cpp
void GrassDemo::DestroyPyramid()
{
    for (VkImageView view : m_pyramidLevelViews)
    {
        vkDestroyImageView(m_context.vulkan.device, view, nullptr);
    }
    m_pyramidLevelViews.clear();
    vkDestroyImageView(m_context.vulkan.device, m_pyramidView, nullptr);
    if (m_pyramid != VK_NULL_HANDLE)
    {
        vmaDestroyImage(m_context.vulkan.allocator, m_pyramid, m_pyramidAllocation);
    }
    m_pyramidView       = VK_NULL_HANDLE;
    m_pyramid           = VK_NULL_HANDLE;
    m_pyramidAllocation = VK_NULL_HANDLE;
    m_pyramidValid      = false;
}
```

**And `Resize` finally has work to do:**

```cpp
// The depth pyramid is the one window-sized thing the grass owns (section 9).
// Resize runs after a vkDeviceWaitIdle, so the old one can go at once.
InitializationResult GrassDemo::Resize(const SceneTargets& targets)
{
    DestroyPyramid();
    return CreatePyramid(targets);
}
```

The renderer waits for the device to be idle before it calls `Resize`, so the
old pyramid, its views, and the sets that name them can be destroyed at once.

**In `CreateDescriptors`**, set 1 gets binding 5, and the pool one combined image
sampler per set:

```cpp
        { .binding = 5, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1,   // section 9
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
```

with `.bindingCount = 6`, and in the pool sizes, with `.poolSizeCount = 3`:

```cpp
        { VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, FRAMES_IN_FLIGHT },   // section 9
```

### Building it every frame

**This is `RecordDepthPyramid`**, recorded after the scene pass:

```cpp
// Section 9: after the scene pass, the depth it left reduced level by level.
void GrassDemo::RecordDepthPyramid(VkCommandBuffer commandBuffer, const SceneTargets& targets)
{
    // Depth: attachment to sampled. Its last writer is the depth test at 1x and the
    // resolve at 2x and up (Chapter 18), so the source is both stages.
    transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT |
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);

    // The pyramid: this frame's generation pass sampled it, and now it is rewritten.
    // A write after a read: wait for the reads, nothing to flush.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_reducePipeline);
    for (uint32_t level = 0; level < m_pyramidLevels; ++level)
    {
        const uint32_t width  = std::max(1u, m_pyramidExtent.width >> level);
        const uint32_t height = std::max(1u, m_pyramidExtent.height >> level);
        vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_reduceLayout,
                                0, 1, &m_reduceSets[level], 0, nullptr);
        vkCmdDispatch(commandBuffer, groupCount(width, 8), groupCount(height, 8), 1);

        // This level's writes, before the next level samples them - and, after the
        // last, before next frame's generation pass does.
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    }

    // The return trip: depth back to an attachment once the reads are done. It
    // chains into beginScenePass's own depth barrier next frame (Chapter 21 section 5).
    transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
}
```

Four barriers, and each answers the three questions:

**1. The depth image, attachment to sampled.**

- **Q1:** its last writer must finish before the reduce pass reads it. At 1×
  that is the depth test, in `EARLY_FRAGMENT_TESTS` and `LATE_FRAGMENT_TESTS`.
  At 2× and up the depth image is the **resolve target** (Chapter 18 section
  5), and every multisample resolve — depth too — runs in
  `COLOR_ATTACHMENT_OUTPUT` with `COLOR_ATTACHMENT_WRITE` access. The source is
  the union of both, so one barrier is right at every sample count.
- **Q2:** those writes made visible to `COMPUTE_SHADER` / `SHADER_SAMPLED_READ`.
- **Q3:** `DEPTH_ATTACHMENT_OPTIMAL`, where `endScenePass` leaves it, to
  `SHADER_READ_ONLY_OPTIMAL`, with the **depth** aspect. The contents matter, so
  the old layout is the real one, not `UNDEFINED`.

At 2× and up the resolved depth is the farthest sample when the driver offers
`MAX` and the first sample otherwise (Chapter 18); some drivers offer only
`SAMPLE_ZERO`. With `SAMPLE_ZERO` a pixel on an object's edge can carry the near
object's depth although part of the pixel saw past it, so the pyramid can be a
little too near along silhouettes, and a blade visible only through such a
sub-pixel gap may be culled. Chapter 18 accepted that for every reader of the
resolved depth.

**2. The pyramid, read before it is rewritten.** This frame's generation pass
sampled the pyramid; the reduce pass is about to overwrite it — a write after a
read. **Q1:** the reads finish first; **Q2:** nothing was written, so nothing to
make available — `NONE` on the source side — and the reduce's storage writes are
the destination; **Q3:** none, the layout stays `GENERAL`. Deleting it is
silent; the aside at the end of this section says why, and why it stays.

**3. Level to level**, after every dispatch. **Q1:** this level's writes finish
before the next level's dispatch, which reads them; **Q2:** `SHADER_STORAGE_WRITE`
made visible to `SHADER_SAMPLED_READ`; **Q3:** none. After the last level, the
same barrier makes the whole pyramid visible to the next frame's generation
pass, which comes later in submission order. Delete it and validation reports
`SYNC-HAZARD-READ-AFTER-WRITE` at the next level's dispatch.

**4. The depth image's return trip.** **Q1:** the reduce's reads finish before the
next frame's depth test; **Q2:** nothing to flush (reads), and the depth test's
read and write are the destination; **Q3:** `SHADER_READ_ONLY_OPTIMAL` back to
`DEPTH_ATTACHMENT_OPTIMAL`. Its destination stages are the fragment tests,
which next frame's `beginScenePass` barrier has in its source at every sample
count, so the two chain (Chapter 21 section 5 follows this chain from one frame
to the next): the depth image is never written
while the reduce may still be reading it. Deleting it is silent too; see the
aside.

One edit here does fire, and it is the one that proves the union source: drop
`COLOR_ATTACHMENT_OUTPUT` and `COLOR_ATTACHMENT_WRITE` from barrier 1's source
and run at 4×. Validation reports `SYNC-HAZARD-WRITE-AFTER-WRITE` at barrier 1:
its layout transition against the resolve's write at the end of the scene pass.
At 1× the same edit is silent, because the depth test is then the last writer.

**In `Record`**, after `handBackSceneTarget`:

```cpp
    // Section 9: this frame's depth, reduced for the next frame's generation pass.
    RecordDepthPyramid(commandBuffer, frame.targets);
    m_previousViewProjection = projection * view;
    m_pyramidValid           = true;
```

The view-projection is remembered with the depth it was drawn with.

### The test

**This is `occluded`**, in `GrassGenerate.comp.glsl` after `sphereInFrustum`:

```glsl
// Section 9 (optional): is a sphere hidden behind last frame's depth? Project its
// bounding box with last frame's camera, find the pyramid level where that
// rectangle spans at most 2x2 texels, and compare its nearest depth with the
// farthest those texels saw.
bool occluded(vec3 center, float radius)
{
    if (grass.occlusionPyramid.w == 0.0) { return false; }

    vec2  low     = vec2(1.0);
    vec2  high    = vec2(0.0);
    float nearest = 1.0;
    for (int corner = 0; corner < 8; ++corner)
    {
        vec3 offset = vec3((corner & 1) != 0 ? radius : -radius,
                           (corner & 2) != 0 ? radius : -radius,
                           (corner & 4) != 0 ? radius : -radius);
        vec4 clip = grass.occlusionViewProjection * vec4(center + offset, 1.0);
        if (clip.w <= 0.0) { return false; }   // reaches behind last frame's camera: keep it
        vec3 ndc = clip.xyz / clip.w;
        low      = min(low, ndc.xy * 0.5 + 0.5);
        high     = max(high, ndc.xy * 0.5 + 0.5);
        nearest  = min(nearest, ndc.z);
    }
    // Partly off last frame's screen: no depth there to hide behind.
    if (any(lessThan(low, vec2(0.0))) || any(greaterThan(high, vec2(1.0)))) { return false; }

    // In level 0's texels, then shifted down to the level where the rectangle is
    // at most one texel wide. A level's last texel holds the remainder, so clamp.
    // (The level's size is Vulkan's mip rule, computed rather than asked with
    // textureSize: cheaper, and a level that differs between invocations is a corner
    // some drivers get wrong.)
    vec2  span  = (high - low) * grass.occlusionPyramid.xy;
    int   level = int(min(ceil(log2(max(max(span.x, span.y), 1.0))), grass.occlusionPyramid.z - 1.0));
    ivec2 size  = max(ivec2(grass.occlusionPyramid.xy) >> level, ivec2(1));
    ivec2 a     = min(ivec2(low * grass.occlusionPyramid.xy) >> level, size - 1);
    ivec2 b     = min(ivec2(high * grass.occlusionPyramid.xy) >> level, size - 1);

    float farthest = max(max(texelFetch(depthPyramid, a, level).r, texelFetch(depthPyramid, ivec2(b.x, a.y), level).r),
                         max(texelFetch(depthPyramid, ivec2(a.x, b.y), level).r, texelFetch(depthPyramid, b, level).r));
    return nearest > farthest;
}
```

- **The blade's box, projected with last frame's camera.** The eight corners of
  the box around the culling sphere go through `occlusionViewProjection`, the
  way Chapter 10 sections 1 and 2 project any point: to clip space, then divided
  by `w` into normalized device coordinates, −1 to 1 across the screen, which
  `ndc.xy * 0.5 + 0.5` turns into 0 to 1 across the pyramid. If any corner is
  behind last frame's camera (`w ≤ 0`), the divide is meaningless and the blade
  is kept. The rectangle the corners cover is the area to test, and the
  smallest projected depth is the blade's nearest point.
- **Off last frame's screen means kept.** There is no depth there to be hidden
  behind. This is what makes turning the camera safe: newly visible ground was
  not in last frame's view, so nothing in it is culled.
- **The level** is the one where the rectangle spans at most two texels each way:
  `ceil(log2(span))` levels down from level 0, where span is the rectangle's
  size in level-0 texels. Each level halves the texels (Chapter 15 section 5's
  mip arithmetic), so at level `L` one texel covers `2^L` of level 0's. A
  rectangle 13 texels wide: `log2(13)` ≈ 3.7, rounded up to level 4, where a
  texel covers 16 — so the 13 fall within at most two texels, depending on where
  they start. Four `texelFetch`es at the rectangle's corners then cover it.
- **The level's size is computed, not asked.** A level is level 0 halved and
  floored `level` times, at least 1. `textureSize(depthPyramid, level)` would say
  the same, but the arithmetic is cheaper, and a `textureSize` whose level
  differs between neighbouring invocations is a corner some drivers get wrong:
  a blade that clamps its coordinates to the wrong level's size can be culled
  while visible.
- **Hidden** means its nearest point is farther than the farthest depth in its
  rectangle: everything drawn there was in front of all of it.

**In `main`**, after the frustum test:

```glsl
    if (occluded(root, shape.x + shape.y))
    {
        atomicAdd(counters.occluded, 1u);
        return;
    }
```

The count is for the panel only.

**In `WriteFrameBuffers`**, the parameters gain last frame's camera and the
pyramid's shape:

```cpp
        // Section 9: last frame's camera, and whether its pyramid may be trusted.
        .occlusionViewProjection = m_previousViewProjection,
        .occlusionPyramid        = { static_cast<float>(m_pyramidExtent.width), static_cast<float>(m_pyramidExtent.height),
                                     static_cast<float>(m_pyramidLevels),
                                     m_pyramidValid && m_settings.occlusionCulling && !m_settings.freezeCulling ? 1.0f : 0.0f },
```

The test is switched off (`w = 0`) until a pyramid has been filled, when the
panel turns it off, and while culling is frozen: a frozen culling camera's view
is not last frame's view, so last frame's depth says nothing about it.

**The panel** gains the count, at the end of the budget's lines:

```cpp
        ImGui::Text("Occluded %u", statistics.occluded);   // section 9
```

and a checkbox, in the "Generation" group after "Freeze culling":

```cpp
            ImGui::Checkbox("Occlusion culling", &settings.occlusionCulling);   // section 9
```

**`ReadStatistics`** copies it:

```cpp
    m_statistics.occluded    = counters.occluded;
```

**And `Teardown`** releases it all, first:

```cpp
    DestroyPyramid();                                              // section 9
    vkDestroyPipeline(device, m_reducePipeline, nullptr);
    vkDestroyPipelineLayout(device, m_reduceLayout, nullptr);
    vkDestroyDescriptorPool(device, m_reducePool, nullptr);
    vkDestroyDescriptorSetLayout(device, m_reduceSetLayout, nullptr);
    vkDestroySampler(device, m_nearestSampler, nullptr);
    m_reducePipeline  = VK_NULL_HANDLE;
    m_reduceLayout    = VK_NULL_HANDLE;
    m_reducePool      = VK_NULL_HANDLE;
    m_reduceSetLayout = VK_NULL_HANDLE;
    m_nearestSampler  = VK_NULL_HANDLE;
```

### What it buys

Toggle "Occlusion culling" with the panel open and the image must not change:
culling that changes the picture is a bug. It does not, at 1× or 4×, and the
counts move: on one machine, in the default view about 8% of LOD 1 is culled,
and with the eye half a metre above the ground about 58%. The steeper
the view across the field, the more there is to cull.

"Must not change" means that no blade goes missing, not that every sample stays
the same. Section 4's append hands out slots in the order the atomics happen to
run, and on most GPUs that order varies from frame to frame, as workgroups
finish in a different order (Chapter 21 section 5 met the same thing with alpha
particles). Where two blades cross at exactly the same depth, the depth test
(`VK_COMPARE_OP_LESS`) keeps the one drawn first, so a few isolated samples
along such crossings can differ between any two frames, culling or no culling.
Before comparing on against off, capture two frames with nothing toggled to see
that baseline. A driver that runs the atomics in the same order every frame,
such as Mesa's lavapipe on the CPU, shows none.

What it costs is the reduce pass — a few dispatches over a half-resolution image
— and eight projections and four fetches per candidate that survives the
frustum. Whether that wins depends on how expensive drawing a blade is
compared with testing one, which is a question for real hardware.

The one-frame lag has a visible failure, and it is worth knowing what it looks
like: when the camera moves sideways past a hill, ground that the hill hid last
frame comes into view, and its blades were culled against last frame's depth —
for one frame, that ground is bare. In a field the effect is a flicker at the
edge of a hill when the camera moves fast. GPU-driven renderers fix it with a
second pass: draw what passed, build a pyramid from *this* frame's depth, re-test
what failed, draw what passes now (Haar and Aaltonen, Wihlidal). That is the
natural next step, and not built here.

### Why validation is quiet here

Three deletions in this section go unreported, and none of them is permission
to delete. Each is covered by a chain of other barriers that happens to exist
in this frame.

- **Barrier 2, the pyramid's write after read.** Section 4's forward barrier
  orders the generation pass before the draws' vertex shading, and barrier 1
  here has the fragment tests — and so every graphics stage before them, vertex
  shading included — as its source. Through that chain the generation's reads
  of the pyramid are already ordered before the reduce. The explicit barrier
  says what the reduce depends on in one place, and keeps it true if the order
  of the frame ever changes.
- **Section 4's return trip**, deleted with Part 2 built, is reported only for
  the counter copy, for the same reason: barrier 1's source covers last frame's
  indirect fetch and vertex shading, and its destination is compute. The copy
  is a transfer, outside that chain, so the return trip is still the only
  thing that orders it.
- **Barrier 4, the depth image's return trip.** `beginScenePass` transitions
  the depth image from `UNDEFINED`, so the layout it was left in is never
  checked; and section 4's return trip (source `COMPUTE_SHADER`) and forward
  barrier (to `VERTEX_SHADER`) sit between the reduce and the next frame's
  depth writes, with `beginScenePass`'s depth barrier, whose source includes
  vertex shading, after them. Remove the grass's compute from a frame and that
  chain is gone. Chapter 10 section 9 makes every later reader of the depth
  image responsible for its return trip, so it stays.

The two controls that do fire — a missing level-to-level barrier, and
barrier 1 without its resolve stages at 4× — are the ones to run.

## Checkpoint

Part 2 is complete. You can now see and check:

- the panel's "Occluded" count rising as you lower the camera into the field
  and look across it;
- toggling "Occlusion culling" changes that count and nothing in the picture:
  hold the camera still, toggle, and watch any patch of grass. For a strict
  check, capture both in RenderDoc (Chapter 34 sections 1 and 3) and compare
  their final images; on a GPU a few isolated samples where blades cross
  differ even between two captures with nothing toggled (section 9's "What it
  buys");
- resizing the window rebuilds the pyramid without a validation message;
- deleting a level-to-level barrier reports `SYNC-HAZARD-READ-AFTER-WRITE`.

---

## If something goes wrong

- **No grass at all, and no validation messages.** The draws' instance counts are
  zero. Check the panel's counts: if they are zero too, no tile was collected
  (is the culling frustum built from `projection * view`, in that order?) or the
  generation dispatch has no work (`tileCount` 0, or `bladesPerSide` 0). If the
  counts are right but nothing draws, the End pass or the forward barrier is
  missing.
- **Only the near grass, or the far grass drawn with the near blades' data.** The
  second draw's `firstInstance` is not `capacity0`, or the
  `drawIndirectFirstInstance` feature is not enabled (Chapter 19 section 6) — the
  core validation layer cannot see that one.
- **The field boils as the camera moves.** Something random is seeded from the
  frame, the thread, or the tile list instead of the world cell.
- **Blades flicker in patches.** A capacity is exceeded (the panel turns red), or
  the forward barrier is missing and a draw reads blades still being written.
- **A band of shimmer that follows you at the LOD distance.** The morph is off,
  or the levels are not nested: LOD 1's vertices must be LOD 0's pairs 0, 2, 4,
  and 7, at the same `t`.
- **Grass vanishes at the edges of the screen when turning.** The tile box or the
  blade sphere is too small for what a blade can reach, so a blade leaning into
  view from outside the frustum was culled.
- **With Part 2: holes in the grass that do not move with the camera.** The
  occlusion test is not conservative. Compare the image with occlusion on and
  off: a blade missing with it on is the bug, while a few isolated samples
  where blades cross can differ on a GPU anyway (section 9's "What it buys").
  Check the level size (computed, not `textureSize`), the remainder texels of
  odd levels, and that the test is off until the pyramid has been filled.
- **With Part 2: `VUID-VkImageCreateInfo-mipLevels-00958`.** One mip level too
  many: the count is `floor(log2(largest side)) + 1`.

---

## Exit check

- [ ] The field reaches `maxDistance` in every direction you look and moves with
      you; a blade at a given spot is the same blade every time you return to it.
- [ ] **Freeze culling**, then fly out: a wedge of grass, the culling camera's
      view out to `maxDistance`, stands on the ground, thinning toward its far
      edge; nothing behind the frozen camera.
- [ ] View **Tiles**: 4 m squares of color, the same color for a tile whenever it
      comes back into view.
- [ ] View **LOD**: green near, yellow over the morph band, blue far. Walking
      forward slowly on **Shaded**, no band of blades changing shape follows
      you at the LOD distance; with "Morph band" at 0, one does — the tips
      jump as each blade crosses it.
- [ ] The panel's counts and timings update; raising "Blades per tile side" far
      enough turns the capacity warning on (at the default view, LOD 0 holds
      about 40,000 blades at 80 and passes its 200,000 near 180), and the count
      keeps rising past the capacity while the drawn blades stop at it.
- [ ] No validation messages with synchronization validation and the
      shader-access setting on. Deleting the forward barrier reports
      `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDrawIndirect`; put it back.
- [ ] If you did Part 2: with the camera still, toggling "Occlusion culling"
      changes the "Occluded" count and nothing you can see, at 1× and at 4×
      (RenderDoc captures of both, Chapter 34 sections 1 and 3, differ only
      where two captures with nothing toggled also can: at isolated samples
      where blades cross, section 9's "What it buys");
      deleting a level barrier reports `SYNC-HAZARD-READ-AFTER-WRITE`; at 4×,
      dropping `COLOR_ATTACHMENT_OUTPUT` from barrier 1's source reports
      `SYNC-HAZARD-WRITE-AFTER-WRITE`; resizing the window rebuilds the pyramid
      with no validation messages.
- [ ] Changing the sample count and switching demos and back still work, with no
      validation messages.

---

## Sources

- Eric Wohllaib, "Procedural Grass in *Ghost of Tsushima*", GDC 2021, and the
  summaries and implementations listed in Chapter 25. Its table, "Where each
  technique comes from", says which of this chapter's techniques are the game's
  and which are this tutorial's.
- Ulrich Haar and Sebastian Aaltonen, "GPU-Driven Rendering Pipelines",
  SIGGRAPH 2015 Advances in Real-Time Rendering — compute culling, compaction,
  indirect draws, and hierarchical-Z occlusion with last frame's depth.
- Graham Wihlidal, "Optimizing the Graphics Pipeline with Compute", GDC 2016 —
  culling in compute, the depth pyramid, and the two-pass fix for disocclusion.
- Klemens Jahrmann and Michael Wimmer, "Responsive Real-Time Grass Rendering for
  General 3D Scenes", I3D 2017 — orientation, frustum, and distance culling of
  blades in compute (orientation culling contrasted in section 3).
- Mithzzx, *Project-GrassFlow* (GitHub) — an open implementation with per-LOD
  append buffers and Hi-Z culling of grass, used to cross-check the structure.
- The Vulkan specification, "Image Mip Level Sizing" (the floor rule) and
  "Multisample Resolve Operations" (resolves run in the color-attachment-output
  stage).

---

## Appendix: complete listings

For reference: Part 1's code where this chapter changed it in more than one
place. Part 2's additions are all in section 9.

**`Shaders/Grass/GrassTypes.h`:**

```c
/* Shaders/Grass/GrassTypes.h - the grass demo's C++/GLSL twins. GLSL includes it as
   "GrassTypes.h", C++ as "Grass/GrassTypes.h". */
#ifndef PF_GRASS_TYPES_H
#define PF_GRASS_TYPES_H

#include "SharedShaderTypes.h"   /* the vec4 and uint aliases, on the C++ side */

#ifdef __cplusplus
    namespace pf::demos::grass {
    using shared::mat4;
    using shared::vec4;
    using shared::uint;
#endif

/* What the fragment shaders draw instead of the lit color (GrassParameters::debugView). */
#define GRASS_VIEW_SHADED   0u
#define GRASS_VIEW_STRIP    1u   /* segments as bands, left edge red, right edge green */
#define GRASS_VIEW_NORMALS  2u   /* the normal the light sees, as a color */
#define GRASS_VIEW_LOD      3u   /* Chapter 26: LOD 0 green, morphing yellow, LOD 1 blue */
#define GRASS_VIEW_TILES    4u   /* Chapter 26: a color per tile */

/* One blade. std430, set 1 binding 0, read by the vertex shader with gl_InstanceIndex. */
struct GrassBlade
{
    vec4 rootAndFacing;   /* xyz: the root on the ground, world metres (Chapter 26: the generation
                             pass fills y); w: facing, radians about +Y */
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
    /* Chapter 26: generation, culling, and LOD. */
    vec4  frustumPlanes[6]; /* the culling camera's planes: xyz inward unit normal, w distance */
    vec4  cullPosition;     /* xyz: the culling camera's position; w unused */
    vec4  shapeMin;         /* the smallest height, width, tilt, and bend a blade is given */
    vec4  shapeMax;         /* and the largest */
    float tileSize;         /* metres */
    uint  bladesPerSide;    /* candidates per tile: bladesPerSide * bladesPerSide */
    uint  capacity0;        /* blades LOD 0's region holds; LOD 1's region starts here */
    uint  capacity1;        /* blades LOD 1's region holds */
    float lodDistance;      /* metres: LOD 0 nearer than this, LOD 1 beyond */
    float morphBand;        /* metres: LOD 0 turns into LOD 1's shape over this last stretch */
    float densityStart;     /* metres: every candidate grows nearer than this */
    float maxDistance;      /* metres: none grows beyond this */
    float farDensity;       /* the fraction of candidates still growing at maxDistance */
    float fadeBand;         /* how far below its cut a blade's size starts shrinking, 0..1 */
    uint  padding3;
    uint  padding4;
};

/* Chapter 26: one visible tile, written by the CPU each frame. std430, set 1 binding 2. */
struct GrassTile
{
    int  x;               /* the tile covers [x, x + 1) * tileSize in world x */
    int  z;               /* and [z, z + 1) * tileSize in world z */
    uint padding0;
    uint padding1;
};

/* Chapter 26: what the generation pass counts. std430, set 1 binding 3. */
struct GrassCounters
{
    uint lodCount[2];     /* blades appended to each LOD's region; may run past its capacity */
    uint padding0;
    uint padding1;
};

/* Push constants, vertex stage, shared by both pipelines; each reads what it needs. */
struct GrassPush
{
    vec4 terrainGrid;     /* xy: world xz of the grid's corner, z: cell size (m), w: cells per side */
    uint segmentCount;    /* Chapter 26: 7 for LOD 0, 3 for LOD 1 */
    uint padding0;
    uint padding1;
    uint padding2;
};

#ifdef __cplusplus
    static_assert(sizeof(GrassBlade) == 32, "GrassBlade layout drifted.");
    static_assert(sizeof(GrassParameters) == 272, "GrassParameters layout drifted.");
    static_assert(offsetof(GrassParameters, debugView) == 64, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, frustumPlanes) == 80, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, tileSize) == 224, "GrassParameters alignment drifted.");
    static_assert(sizeof(GrassTile) == 16, "GrassTile layout drifted.");
    static_assert(sizeof(GrassCounters) == 16, "GrassCounters layout drifted.");
    static_assert(sizeof(GrassPush) == 32, "GrassPush layout drifted.");
    }
#endif

#endif
```

**`GrassDemo::RecordGeneration`:**

```cpp
void GrassDemo::RecordGeneration(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t tileCount)
{
    m_timestamps.Write(commandBuffer, frameIndex, 0);

    // The return trip: last frame's draws, copy, and compute passes are done with
    // these buffers before this frame's compute passes write them again.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT |
                  VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_pipelineLayout,
                            1, 1, &m_grassSets[frameIndex], 0, nullptr);

    // Begin: the counters start at zero.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_beginPipeline);
    vkCmdDispatch(commandBuffer, 1, 1, 1);
    computeToComputeBarrier(commandBuffer);

    // Generate: one invocation per candidate, one row of workgroups per tile.
    if (tileCount > 0)
    {
        const uint32_t candidates = static_cast<uint32_t>(m_settings.bladesPerSide * m_settings.bladesPerSide);
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_generatePipeline);
        vkCmdDispatch(commandBuffer, groupCount(candidates, 64), tileCount, 1);
    }
    computeToComputeBarrier(commandBuffer);

    // End: the counts become the two draws.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_endPipeline);
    vkCmdDispatch(commandBuffer, 1, 1, 1);
    m_timestamps.Write(commandBuffer, frameIndex, 1);

    // Forward: the draws read the commands and the blades, the copy reads the counters.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_2_COPY_BIT,
                  VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_TRANSFER_READ_BIT);

    // Chapter 20 section 9: the counts, copied for the CPU to read FRAMES_IN_FLIGHT frames from now.
    const VkBufferCopy region{ .srcOffset = 0, .dstOffset = 0, .size = sizeof(GrassCounters) };
    vkCmdCopyBuffer(commandBuffer, m_counters.buffer, m_readback[frameIndex].buffer, 1, &region);
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
}
```

**`GrassDemo::Record`:**

```cpp
void GrassDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const uint32_t        frameIndex    = frame.frameIndex;

    ReadStatistics(frameIndex);

    const VkExtent2D extent    = frame.targets.extent;
    const float     aspect     = static_cast<float>(extent.width) / static_cast<float>(extent.height);
    const glm::mat4 view       = scene::viewMatrix(m_cameraTransform.Matrix());
    const glm::mat4 projection = m_camera.Projection(aspect);

    // The culling camera is the real one, unless the panel froze it where it was.
    if (!m_settings.freezeCulling)
    {
        m_frozenViewProjection = projection * view;
        m_frozenPosition       = m_cameraTransform.translation;
    }
    const scene::Frustum cullFrustum = scene::frustumFromViewProjection(m_frozenViewProjection);

    const uint32_t tileCount = CollectTiles(frameIndex, cullFrustum, m_frozenPosition);
    m_skyLightsScene = vulkan_graphics::skyLightsScene(frame.sky);   // Chapter 25 section 8: for WriteFrameBuffers
    WriteFrameBuffers(frameIndex, view, projection, cullFrustum, m_frozenPosition);

    // Compute first, outside any rendering scope (Chapter 20 section 1).
    m_timestamps.Reset(commandBuffer, frameIndex);
    RecordGeneration(commandBuffer, frameIndex, tileCount);
    m_tileCounts[frameIndex]      = tileCount;
    m_candidateCounts[frameIndex] = tileCount * static_cast<uint32_t>(m_settings.bladesPerSide * m_settings.bladesPerSide);
    m_readbackPending[frameIndex] = true;

    m_sceneRenderer.PrepareDraws(frameIndex, m_stones, m_stones);
    m_sceneRenderer.RecordShadows(commandBuffer, frameIndex, m_camera, view, aspect,
                                  m_sceneRenderer.SunDirection(frameIndex), m_shadowSettings);

    // Chapter 23: the sky's sun is the panel's, the one WriteFrameBuffers gave the light buffer.
    m_sky.Update(commandBuffer, frameIndex, frame.sky,
                 { .sunDirection  = sunTravelDirection(m_settings.sunElevation, m_settings.sunAzimuth),
                   .sunIrradiance = glm::vec3(m_settings.sunIntensity) });

    const VkClearColorValue clearColor{ { 0.35f, 0.50f, 0.75f, 1.0f } };   // linear
    beginScenePass(commandBuffer, frame.targets, &clearColor);

    m_sceneRenderer.RecordDraws(commandBuffer, frameIndex);

    m_sceneRenderer.BindFrameSet(commandBuffer, m_pipelineLayout, frameIndex);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipelineLayout,
                            1, 1, &m_grassSets[frameIndex], 0, nullptr);

    // The ground follows the culling camera, snapped to whole cells so it does not swim.
    const float groundSide = TERRAIN_CELL * static_cast<float>(TERRAIN_CELLS);
    const float cornerX    = std::floor(m_frozenPosition.x / TERRAIN_CELL) * TERRAIN_CELL - 0.5f * groundSide;
    const float cornerZ    = std::floor(m_frozenPosition.z / TERRAIN_CELL) * TERRAIN_CELL - 0.5f * groundSide;
    GrassPush push{ .terrainGrid = { cornerX, cornerZ, TERRAIN_CELL, static_cast<float>(TERRAIN_CELLS) } };
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_terrainPipeline);
    vkCmdDraw(commandBuffer, 6 * TERRAIN_CELLS * TERRAIN_CELLS, 1, 0, 0);
    m_timestamps.Write(commandBuffer, frameIndex, 2);

    // The two LODs: the same pipeline, two commands the End pass wrote.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_grassPipeline);
    push.segmentCount = 7;
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
    vkCmdDrawIndirect(commandBuffer, m_commands.buffer, 0, 1, sizeof(shared::DrawIndirectCommand));
    m_timestamps.Write(commandBuffer, frameIndex, 3);

    push.segmentCount = 3;
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
    vkCmdDrawIndirect(commandBuffer, m_commands.buffer, sizeof(shared::DrawIndirectCommand), 1,
                      sizeof(shared::DrawIndirectCommand));
    m_timestamps.Write(commandBuffer, frameIndex, 4);

    m_sky.Draw(commandBuffer, view, projection);   // Chapter 23: after the ground, the stones, and the blades
    endScenePass(commandBuffer);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

**`GrassDemo::Teardown`:**

```cpp
void GrassDemo::Teardown()
{
    const VkDevice device = m_context.vulkan.device;
    m_sky.Shutdown();                                              // Chapter 23
    m_timestamps.Shutdown();
    vkDestroyPipeline(device, m_endPipeline, nullptr);
    vkDestroyPipeline(device, m_generatePipeline, nullptr);
    vkDestroyPipeline(device, m_beginPipeline, nullptr);
    vkDestroyPipeline(device, m_grassPipeline, nullptr);
    vkDestroyPipeline(device, m_terrainPipeline, nullptr);
    vkDestroyPipelineLayout(device, m_pipelineLayout, nullptr);
    vkDestroyDescriptorPool(device, m_descriptorPool, nullptr);   // frees the sets
    vkDestroyDescriptorSetLayout(device, m_grassSetLayout, nullptr);
    m_endPipeline      = VK_NULL_HANDLE;
    m_generatePipeline = VK_NULL_HANDLE;
    m_beginPipeline    = VK_NULL_HANDLE;
    m_grassPipeline    = VK_NULL_HANDLE;
    m_terrainPipeline  = VK_NULL_HANDLE;
    m_pipelineLayout   = VK_NULL_HANDLE;
    m_descriptorPool   = VK_NULL_HANDLE;
    m_grassSetLayout   = VK_NULL_HANDLE;
    m_grassSets        = {};

    for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
    {
        destroyBuffer(m_context.vulkan, m_readback[i]);
        destroyBuffer(m_context.vulkan, m_tileBuffers[i]);
        destroyBuffer(m_context.vulkan, m_parameterBuffers[i]);
    }
    destroyBuffer(m_context.vulkan, m_commands);
    destroyBuffer(m_context.vulkan, m_counters);
    destroyBuffer(m_context.vulkan, m_blades);

    m_stones.clear();
    m_sceneRenderer.Shutdown();
}
```

Next: [27 — Grass, Part III: The Look](27-Grass-Look.md)
