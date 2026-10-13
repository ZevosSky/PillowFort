# 36 — Terrain to the Horizon

**Goal:** ground all the way to the horizon. Twelve rings of one grid around the
camera, each twice as coarse as the one inside it, drawn in one instanced draw:
first over noise, so they work with no file at all, then over a 33 km map with
an island about 21 km across inside it, read from a 16-bit heightmap an erosion
script makes, with noise for the detail near the camera. Past the coast a flat
sea reflects the sky; haze fades the far ground into it; a skirt carries the
last ring out to the horizon; and the camera stands on the ground, from a copy
of the same height on the CPU.

**ROADMAP:** step 21+ — the `Horizon` demo grows. A class of its own, `Terrain`,
in `Source/PillowFort/Demos/Horizon/`; its shaders under `Shaders/Horizon/`;
the heightmap and the script that makes it in `Assets/Terrain/`.

**Module:** `pf::demos::horizon` (`Terrain`, owned by `HorizonDemo`). One
function goes outside the demo, `usd_import::ImportGrayImage16`, because the
importer is the only code that includes a TinyUSDZ header (the index's module
table), and TinyUSDZ's image loader is what decodes a 16-bit PNG.

**Math:** taught where it is first used, and listed in the index's [The math,
chapter by chapter](../VulkanTutorial.md#the-math-chapter-by-chapter): rings
that double, and why twelve of them cost twelve times one (section 2); how many
cells a wave needs to be drawn, and the rule that fades detail out by distance
(section 3); where a point of the world lies on the map, and a bilinear sample,
each worked by hand (section 9).

**Prerequisites:**

- Builds on Chapter 35, built and running: this chapter grows its plates, its
  `VIEWPOINT`, `KeepCameraInBounds` and `Record`, and relies on its reversed
  depth with `GREATER` and the clear to 0 (section 6) and on the sky drawn
  first, `SUN_TRAVEL` and the 1,400 m ceiling (section 7).
- Chapter 25 section 3 (the grass's ground: a grid made from `gl_VertexIndex`
  with no vertex buffer, and its normal from central differences); Chapter 26
  section 2 (the ground snapped to whole cells as it follows the camera);
  Chapter 27 sections 2 (gradient noise, `Noise.glsl`) and 9 (a copy of the
  ground's height on the CPU, for the ball); Chapter 20 sections 3 (`pcgHash` in
  `Random.glsl`) and 4 (`createDescriptorSets`).
- Chapter 16 section 5 (`smoothstep`: 0, an S-curve, then 1); Chapter 19
  sections 1 and 2 (one draw, many instances, and `gl_InstanceIndex`).
- Chapter 08 sections 2 (`immediateSubmit`) and 5 (push constants); Chapter
  15 sections 4 (decoding images through TinyUSDZ, and what it does to a
  16-bit one) and 5 (a mip chain made by blits, and its barriers); Chapter 04
  section 5 (the three questions a barrier answers); Chapter 13 sections 5 (who
  may include TinyUSDZ) and 6 (`Assets/` beside the executable).
- Chapter 24 sections 1 and 4 (set 0 binding 10, the sky's light as E / π, and
  `ambientMode`) and 6 (binding 11, the sky blurred a level per roughness:
  level 0 is the sky itself); Chapter 23 section 8 (one sky setting for the
  whole engine, `SkyMode::Off` by default).
- Chapter 11 section 14 (`FrameData`'s sun and ambient light, and `sunColor`
  as what a white surface facing the sun reflects); Chapter 15 section 9 (why
  that is the sun's irradiance divided by π).
- Chapter 28 sections 2 (light lost by the same share every metre, an
  exponential) and 9 (a mip level the shader names itself, as a `log2`).
- Chapter 29 section 10 (Schlick's Fresnel); Chapter 30 sections 9 (the skirt)
  and 10 (the sun's glint, scaled to add up to its irradiance, and haze that
  fades toward the sky at the horizon).
- Chapter 09 sections 2 (`Setup` and `Teardown`) and 6 (`beginDemoPanel`);
  Chapter 10 section 10 (which input reaches the demo while ImGui has the
  keyboard); Chapter 18 section 6 (every scene pipeline declares the pass's
  sample count); Chapter 02 section 3 (validation messages and their IDs).

---

## Where this is going

Chapter 35 built a camera that sees 200 km and a depth buffer that can tell
near from far at every distance, and drew nothing but test plates with it. This
chapter puts the ground in, the biggest thing in the far view: from 1,000 m up,
the land you can see reaches tens of kilometres, and Chapter 35's "Layers by
distance" worked out why drawing it all at near detail is out of the question.
Its answer was rings around the camera, each twice as coarse as the one inside
it, all of them one draw; *The Witcher 3* drew its terrain the same way
(Gollent, in Sources). The chapter is in three parts:

- **Part 1, "Rings"** (sections 1-6): one grid, made by the vertex shader;
  twelve rings of it, each twice the size of the one inside; height from
  noise, octaves of it from 8 km waves down to 2 m ones (section 3), and the
  rule that fades each one out before the big cells far away would shimmer;
  normals and light; the cracks where two rings meet; and a copy of the height
  on the CPU, which the camera stands on. Nothing in it needs a file. It ends
  with rolling hills of noise to the horizon.
- **Part 2, "An island"** (sections 7-10): a script that rains on noise
  mountains until valleys form and writes them as a heightmap, 4,096 texels on
  a side at 8 m each; that heightmap on the GPU with every mip level, laid under
  the world so that the sea is within the camera's reach, each ring reading the
  level that suits its cells, and the noise kept for the detail 8 m texels
  cannot hold; and the sea, which is the terrain itself, drawn flat
  at 0 wherever the ground is lower and shaded as water. It ends with the
  island in its sea, the sea reaching the last ring 65 km out.
- **Part 3, "To the horizon"** (section 11): haze, which fades the far ground
  into the sky and makes distance read as distance; and a skirt that carries
  the last ring's edge out to the horizon, so the world has no edge.

### What you are actually writing

**This is `Terrain.h`**, the map of the chapter. The terrain is a class of its
own, as the sky is, because Chapters 37 to 42 stand things on it: they will ask
it for the ground's height. Every private function names the section that
writes it:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 36: the ground to the horizon, as rings of one grid over a 16-bit heightmap
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/Terrain.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"
#include "PillowFort/VulkanGraphics/SceneTargets.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include <glm/glm.hpp>
#include <vulkan/vulkan.h>
#include <vma/vk_mem_alloc.h>

#include <array>
#include <cstdint>
#include <vector>

namespace pf::demos::horizon {

// Section 2: every ring is a grid of `cells` x `cells`, and ring 0's cells are `finestCell` metres across. Two
// presets, both reaching 65 km: the full one, and a lighter one for lavapipe, which is a CPU.
struct TerrainPreset
{
    const char* name;
    uint32_t    cells;
    float       finestCell;   // metres
};
inline constexpr std::array<TerrainPreset, 2> TERRAIN_PRESETS{ {
    { "Full", 128, 0.5f },
    { "Low (lavapipe)", 64, 1.0f },
} };
inline constexpr uint32_t TERRAIN_RINGS = 12;   // section 2

// What the panel changes. The demo keeps it, so it survives Teardown.
struct TerrainSettings
{
    uint32_t preset       = 0;          // section 2: an index into TERRAIN_PRESETS
    bool     showCells    = false;      // section 1: the cell edges as lines
    bool     showRings    = false;      // section 2: a color per ring
    bool     freezeRings  = false;      // section 2: the rings stay put while the camera flies on
    float    hazeDistance = 20000.0f;   // section 11: metres
};

// The ground. A demo owns one, as it owns a Sky: Initialize in Setup, Shutdown in Teardown, Record inside
// the scene pass.
class Terrain
{
public:
    // Section 1: the pipeline. Section 8: the heightmap, from the file to an image with every mip level, and
    // section 9: the set that points the shaders at it.
    InitializationResult Initialize(const vulkan_graphics::VulkanContext& context, VkPipelineCache pipelineCache,
                                    const vulkan_graphics::SceneFormats& formats,
                                    VkDescriptorSetLayout frameSetLayout);
    void Shutdown();   // the host has idled the device (Chapter 09 section 9); safe after a partial Initialize

    // Inside the scene pass, after the clear to depth 0: every ring in one draw, centred on `ringCenter`.
    void Record(VkCommandBuffer commandBuffer, const vulkan_graphics::SceneRenderer& sceneRenderer,
                uint32_t frameIndex, const TerrainSettings& settings, glm::vec2 ringCenter, bool skyOn) const;

    // Section 6: the ground's height at xz, for rings centred on `ringCenter`: the shaders' noise, copied to
    // the CPU, and from section 9 the CPU's copy of the heightmap's top level. The camera stands on it.
    float HeightAt(glm::vec2 xz, glm::vec2 ringCenter, const TerrainSettings& settings) const;

    // Section 8: the heightmap's side in texels; 0 when it could not be loaded and the noise stands in.
    uint32_t HeightmapSize() const { return m_hasHeightmap ? m_heightmapSize : 0; }

private:
    InitializationResult CreatePipeline(VkDescriptorSetLayout frameSetLayout);   // sections 1, 5, 9
    void                 LoadHeightmap();                                        // section 8
    InitializationResult UploadHeightmap();                                      // section 8
    InitializationResult CreateHeightmapSet();                                   // section 9
    float                MapHeight(glm::vec2 xz) const;                          // section 9

    vulkan_graphics::VulkanContext m_context;                          // copies of borrowed handles
    VkPipelineCache                m_pipelineCache = VK_NULL_HANDLE;   // borrowed
    vulkan_graphics::SceneFormats  m_formats;

    // Section 1: the rings' pipeline. Section 9: its layout gains set 1, the heightmap.
    VkPipelineLayout m_layout   = VK_NULL_HANDLE;
    VkPipeline       m_pipeline = VK_NULL_HANDLE;

    // Section 8: the heightmap's top level on the CPU, kept for HeightAt, and the image on the GPU.
    std::vector<uint16_t> m_heights;
    uint32_t              m_heightmapSize = 0;       // texels per side
    bool                  m_hasHeightmap  = false;   // false: a one-texel stand-in, and the noise alone
    VkImage               m_heightmap           = VK_NULL_HANDLE;
    VmaAllocation         m_heightmapAllocation = VK_NULL_HANDLE;
    VkImageView           m_heightmapView       = VK_NULL_HANDLE;
    VkSampler             m_heightmapSampler    = VK_NULL_HANDLE;

    // Section 9: set 1, which points the vertex shader at the heightmap.
    VkDescriptorSetLayout m_setLayout = VK_NULL_HANDLE;
    VkDescriptorPool      m_pool      = VK_NULL_HANDLE;
    VkDescriptorSet       m_set       = VK_NULL_HANDLE;
};

} // namespace pf::demos::horizon
```

`TerrainSettings` is what the panel changes. The demo keeps it, with the
camera, so a switch to another demo and back finds every setting as it was;
the `Terrain` itself is GPU objects, made in `Setup` and gone after `Teardown`.
Write the whole header now: a function that is declared and never called needs
no body, so the file builds at every step, and each section fills in what it
names.

`HorizonDemo.h` gains an include, a panel function, the terrain, and the
settings it is drawn with. The include goes with the others, the function with
the other private ones, `m_terrain` under `m_sky`, and the CPU state at the end
of the class:

```cpp
// With the includes:
#include "PillowFort/Demos/Horizon/Terrain.h"

// With the private functions, after DrawDepthReadout:
    void                 DrawTerrainControls();                                // Chapter 36: sections 1, 2, 6, 8, 11

// Under m_sky:
    Terrain                        m_terrain;         // Chapter 36: the ground, to the horizon

// At the end of the class, after m_time:
    // Chapter 36: the terrain's settings, where its rings are centred, and whether the plates show.
    TerrainSettings m_terrainSettings;
    bool            m_presetChosen = false;   // section 2: Setup picks the preset once, by the device
    glm::vec2       m_ringCenter{ 0.0f };     // section 2: the camera's x and z, unless the rings are frozen
    bool            m_showPlates = false;     // section 1: they stand in the ground now, so off at first
```

### Where everything lands

```text
Source/PillowFort/Demos/Horizon/
  Terrain.h                the class, above
  Terrain.cpp              top to bottom:
      the banner, the path line, the includes                section 1, grown in 8
      transitionLevels                                       file scope (section 8)
      pcgHash, latticeGradient, gradientNoise,               file scope (section 6)
        cellSizeAt, noiseOctaves
      namespace pf::demos::horizon {
          using namespace vulkan_graphics;                   section 1
          the heightmap's constants, FALLBACK_SKY            sections 8 and 10
          Initialize, Shutdown, CreatePipeline               section 1, grown in 5 and 9
          LoadHeightmap, UploadHeightmap                     section 8
          CreateHeightmapSet                                 section 9
          Record                                             section 1, grown in 2, 5, 9-11
          MapHeight, HeightAt                                sections 9 and 6
      }
  HorizonDemo.h, .cpp      Chapter 35's, grown: the terrain in Setup, Teardown,
                           Update and Record, its panel group, the light in
                           FrameData, and the camera on the ground
Shaders/Horizon/
  HorizonTypes.h           TerrainDraw, the terrain's push constants        section 1
                           MAP_ORIGIN, the map under the world              section 9
  Terrain.vert.glsl        the rings, the height, the seals, the skirt      sections 1-5, 10, 11
  Terrain.frag.glsl        the ground's colour, light, water, haze          sections 1, 2, 4, 10, 11
  TerrainHeight.glsl       the height function, an include                  sections 3 and 9
Source/PillowFort/UsdImport/UsdImport.h, .cpp
  ImportGrayImage16                                                         section 8
Assets/Terrain/
  make_island.py           the erosion script                               section 7
  Island/Island.png        what it writes: 4,096 x 4,096, 16 bits            section 7
```

Section 1 shows the top of `Terrain.cpp`, and each section after it says where
its code goes in this order.

---

# Part 1 — Rings (sections 1-6)

Part 1 needs no file: noise alone makes hills, so that every step can be seen.

Every run in this chapter is with the engine's sky on, unless it says
otherwise: **Sun sky**, with the Sky header closed again (Chapter 35 section 7).
With the sky off, the background is the demo's pale clear colour, and from
section 4 the ground is lit by a constant ambient light instead of the sky's.

## 1. One grid, from the vertex shader

**This is `TerrainDraw`, the top of `Terrain.cpp`, `Initialize`, `Shutdown`,
`CreatePipeline`, a first `Record`, the two shaders, and the terrain in
`HorizonDemo`.**

### The grid needs no vertex buffer

The grid is Chapter 25 section 3's ground: no vertex buffer, two triangles of
six vertices per cell, and a vertex shader that works out from
`gl_VertexIndex` alone which cell and which of its corners it is drawing. Here
it has 128 cells on a side (section 2's preset decides), each half a metre
across: a square 64 m on a side, 98,304 vertices.

The grid follows the camera. Its corner is half a grid short of the camera in
x and in z, **snapped down to a whole number of cells**, as Chapter 26 section
2's grass ground is: then every vertex sits at a whole number of cells from the
origin, the same points of the world whichever way the camera moves, and the
grid jumps a cell at a time instead of sliding, which would make anything on
it swim. Section 2 changes the snap to two cells, and says why.

### The push constants

The shaders need to know where the camera is, how big a cell is, and how many
cells a side has; later sections add the heightmap's size and the sky's colour.
That is a few numbers that change every frame, so they are push constants
(Chapter 08 section 5), in a C++/GLSL twin as the flat pipeline's are (Chapter
35 section 3). Write the whole struct now, with the fields later sections use,
so its layout never changes under a shader written earlier. In
`HorizonTypes.h`, the `uint` alias joins `vec4` at the top, and the comment on
the include says so:

```c
#include "SharedShaderTypes.h"   /* the vec4 and uint aliases, on the C++ side */

#ifdef __cplusplus
    namespace pf::demos::horizon {
    using shared::vec4;
    using shared::uint;
```

and below `FlatDraw`, still inside the namespace that `#ifdef __cplusplus`
opens at the top, the terrain's flags and its push constants:

```c
/* Chapter 36: what the terrain's shaders draw besides the ground itself, bits of TerrainDraw::flags. */
#define TERRAIN_SHOW_CELLS 1u   /* section 1: every cell's edges, as dark lines */
#define TERRAIN_SHOW_RINGS 2u   /* section 2: a color per ring */
#define TERRAIN_HEIGHTMAP  4u   /* section 9: the heightmap is loaded; without it, section 3's noise alone */
#define TERRAIN_SKY        8u   /* section 10: the engine's sky is on, so the water and the haze can read it */

/* Chapter 36: the terrain's push constants, read by both of its shaders. */
struct TerrainDraw
{
    vec4 rings;       /*  0  x, z: the point the rings are centred on (m); y: ring 0's cell (m); w: cells per side */
    uint ringCount;   /* 16  section 2 */
    uint flags;       /* 20  TERRAIN_* */
    uint padding0;    /* 24  keeps the next vec4 on 16 bytes */
    uint padding1;    /* 28 */
    vec4 heightmap;   /* 32  section 9. x: the map's side (m); y: the height stored as 0 (m); z: the range (m) */
    vec4 sky;         /* 48  section 10. rgb: the sky's color when it is off, linear; w: section 11's haze distance (m) */
};
```

`flags` carries the panel's debug views, and two facts the shaders cannot
know: whether a heightmap was loaded, and whether the sky is on. The
`static_assert` block at the end of the file, which also closes the namespace,
gets two checks for the new struct, beside `FlatDraw`'s:

```c
    static_assert(sizeof(TerrainDraw) == 64, "TerrainDraw layout drifted.");
    static_assert(offsetof(TerrainDraw, heightmap) == 32, "TerrainDraw alignment drifted.");
```

64 bytes is half of the 128 every device must give push constants.

### `Terrain.cpp`

The file begins as every file here does. The includes are the ones this
section needs; section 8 adds the rest. `Horizon/HorizonTypes.h` starts at
`Horizon/` because `Shaders/` is on the include path (Chapter 09 section 8):

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 36: the ground to the horizon, as rings of one grid over a 16-bit heightmap
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/Terrain.cpp
#include "PillowFort/Demos/Horizon/Terrain.h"

#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"

#include "Horizon/HorizonTypes.h"   // TerrainDraw, shared with the terrain's shaders

namespace pf::demos::horizon {

using namespace vulkan_graphics;
```

`Initialize` keeps copies of the handles it is given, as the `Sky` does, then
builds what the terrain draws with. For now that is only the pipeline;
sections 8 and 9 add their steps above it:

```cpp
InitializationResult Terrain::Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                         const SceneFormats& formats, VkDescriptorSetLayout frameSetLayout)
{
    m_context       = context;
    m_pipelineCache = pipelineCache;
    m_formats       = formats;

    return CreatePipeline(frameSetLayout);                                      // section 1
}
```

`Shutdown` is written whole now, ahead of the steps it undoes, as Chapter 35
section 1 wrote `Teardown`: destroying a null handle does nothing, so it is
safe after any `Initialize`, partial or not yet grown. It does not wait for
the GPU: the host does that before it calls `Teardown` (Chapter 09 section 9),
so nothing is in use by the time `Shutdown` runs. It ends by resetting the
object, so a second `Initialize` after a switch back to the demo starts from
nothing:

```cpp
void Terrain::Shutdown()
{
    const VkDevice device = m_context.device;
    if (device == VK_NULL_HANDLE)
    {
        return;   // Initialize never ran
    }
    vkDestroyPipeline(device, m_pipeline, nullptr);                // section 1
    vkDestroyPipelineLayout(device, m_layout, nullptr);
    vkDestroyDescriptorPool(device, m_pool, nullptr);              // section 9: frees the set with it
    vkDestroyDescriptorSetLayout(device, m_setLayout, nullptr);
    vkDestroySampler(device, m_heightmapSampler, nullptr);         // section 8
    vkDestroyImageView(device, m_heightmapView, nullptr);
    vmaDestroyImage(m_context.allocator, m_heightmap, m_heightmapAllocation);
    *this = Terrain{};
}
```

### The pipeline

`CreatePipeline` is the flat pipeline's shape (Chapter 35 section 3) without
the vertex input: no bindings and no attributes, since the shader makes its own
positions. Its layout is set 0, the scene renderer's camera and light, which the
caller passes in, and the push constants, which both shaders read. It compares
with `GREATER`, because this demo's depth is reversed, culls back faces, since
the ground is only ever seen from above (section 5 gives that up, for a reason),
and declares the pass's sample count (Chapter 18 section 6):

```cpp
// Section 1: no vertex buffer, as Chapter 25's ground: the vertex shader makes every position from its
// indices. Set 0 is the scene renderer's; section 9 adds set 1, the heightmap. Both shaders read the push
// constants.
InitializationResult Terrain::CreatePipeline(VkDescriptorSetLayout frameSetLayout)
{
    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
        .offset     = 0,
        .size       = sizeof(TerrainDraw),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &frameSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.device, &layoutInfo, nullptr, &m_layout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the terrain.");
    }

    const GraphicsPipelineDesc desc{
        .vertexShader   = "Horizon/Terrain.vert.spv",
        .fragmentShader = "Horizon/Terrain.frag.spv",
        .colorFormats   = { &m_formats.color, 1 },
        .depthFormat    = m_formats.depth,
        .depthTest      = true,
        .depthWrite     = true,
        .depthCompare   = VK_COMPARE_OP_GREATER,   // Chapter 35 section 6: this demo's depth is reversed
        .cullMode       = VK_CULL_MODE_BACK_BIT,   // the ground is seen from above
        .frontFace      = VK_FRONT_FACE_COUNTER_CLOCKWISE,
        .layout         = m_layout,
        .samples        = m_formats.samples,
    };
    m_pipeline = createGraphicsPipeline(m_context.device, m_pipelineCache, desc);
    if (m_pipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the terrain pipeline failed.");
    }
    return InitializationResult::success();
}
```

### Recording it

`Record` runs inside the scene pass. It fills the push constants, binds the
pipeline and set 0, and draws six vertices per cell. `ringCenter` is where the
grid is centred, which is the camera's x and z (section 2 adds a way to hold it
still); `skyOn` sets a flag section 10's shaders read. The preset is the first
of `TERRAIN_PRESETS`, the full one, until section 2 picks:

```cpp
void Terrain::Record(VkCommandBuffer commandBuffer, const SceneRenderer& sceneRenderer, uint32_t frameIndex,
                     const TerrainSettings& settings, glm::vec2 ringCenter, bool skyOn) const
{
    const TerrainPreset& preset = TERRAIN_PRESETS[settings.preset];
    uint32_t flags = 0;
    if (settings.showCells) { flags |= TERRAIN_SHOW_CELLS; }    // section 1
    if (skyOn)              { flags |= TERRAIN_SKY; }           // section 10 reads it

    const TerrainDraw draw{
        .rings     = { ringCenter.x, preset.finestCell, ringCenter.y, static_cast<float>(preset.cells) },
        .ringCount = 1,                                                                 // section 2: 12
        .flags     = flags,
    };
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipeline);
    sceneRenderer.BindFrameSet(commandBuffer, m_layout, frameIndex);
    vkCmdPushConstants(commandBuffer, m_layout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0,
                       sizeof(draw), &draw);

    // Six vertices per cell, one instance: section 2 makes it twelve.
    vkCmdDraw(commandBuffer, 6 * preset.cells * preset.cells, 1, 0, 0);
}
```

### The shaders

The vertex shader is the grass ground's: the cell and its corner from the
index, the grid's corner from the camera, and the vertex at a whole number of
cells from the origin. It is flat for now, at height 0. The `out` variables
have the location numbers the finished shader gives them, so they do not move
as the shader grows: 0 and 3 now, and the gaps are for the ones that arrive
later, 1 the normal (section 4), 2 the height before the sea (section 10) and
4 the ring (section 2). `cellPosition` counts in cells from the grid's corner,
so it is a whole number at every vertex, and the fragment shader uses that to
draw the cell edges:

```glsl
// Shaders/Horizon/Terrain.vert.glsl - Chapter 36: the ground, as rings of one grid around the camera. Every
// position comes from gl_VertexIndex alone; from section 2, gl_InstanceIndex says which ring.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"   // set 0 binding 0: frame.viewProjection, frame.cameraPosition
#include "HorizonTypes.h"    // TerrainDraw

layout(push_constant) uniform TerrainBlock
{
    TerrainDraw terrain;
};

layout(location = 0) out vec3  worldPosition;   // as drawn: section 10 flattens the sea to 0
layout(location = 3) out vec2  cellPosition;    // in the ring's own cells: whole numbers at the vertices

// Two triangles per cell, counter-clockwise seen from above (Chapter 25's grass ground).
const ivec2 CORNERS[6] = ivec2[](ivec2(0, 0), ivec2(0, 1), ivec2(1, 0), ivec2(1, 0), ivec2(0, 1), ivec2(1, 1));

void main()
{
    // Section 1: which cell of the grid, and which of its corners.
    int   cells  = int(terrain.rings.w);
    int   quad   = gl_VertexIndex / 6;
    ivec2 square = ivec2(quad % cells, quad / cells);      // the cell, counted from the corner
    ivec2 vertex = square + CORNERS[gl_VertexIndex % 6];   // the vertex, counted from the corner

    // Section 1: the grid's corner, half a grid short of the camera, snapped down to a whole number of
    // cells as Chapter 26's ground is, so the grid stays put under the camera until it has moved a cell.
    float cell   = terrain.rings.y;
    ivec2 corner = ivec2(floor(terrain.rings.xz / cell)) - cells / 2;

    ivec2 lattice = corner + vertex;   // the vertex, in this ring's cells from the origin
    vec2  xz      = vec2(lattice) * cell;

    worldPosition = vec3(xz.x, 0.0, xz.y);   // flat, for now: section 3 raises it
    cellPosition  = vec2(vertex);
    gl_Position   = frame.viewProjection * vec4(worldPosition, 1.0);
}
```

The fragment shader gives the ground one green for now, and draws the cell
edges when the panel asks. `fwidth` is how much `cellPosition` changes from
one pixel to the next, so dividing the distance to the nearest edge by it
gives that distance in pixels: a line about one pixel wide, whether a cell is
three pixels across or three hundred:

```glsl
// Shaders/Horizon/Terrain.frag.glsl - Chapter 36: the ground lit by the sun and the sky, the sea wherever the
// ground is below 0, and haze toward the horizon. Linear values.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"   // frame.cameraPosition, and section 4's sun and ambient light
#include "HorizonTypes.h"    // TerrainDraw

layout(push_constant) uniform TerrainBlock
{
    TerrainDraw terrain;
};

layout(location = 0) in vec3  worldPosition;
layout(location = 3) in vec2  cellPosition;

layout(location = 0) out vec4 outColor;

void main()
{
    vec3 color = vec3(0.10, 0.18, 0.06);   // section 4 lights it; for now, one green

    // Section 1: dark lines along every cell edge, about a pixel wide whatever the cell's size on screen:
    // fwidth is how far cellPosition changes across one pixel.
    if ((terrain.flags & TERRAIN_SHOW_CELLS) != 0u)
    {
        vec2  toEdge = abs(fract(cellPosition + 0.5) - 0.5) / max(fwidth(cellPosition), vec2(1e-6));
        float line   = 1.0 - clamp(min(toEdge.x, toEdge.y), 0.0, 1.0);
        color *= 1.0 - 0.75 * line;
    }
    outColor = vec4(color, 1.0);
}
```

### In the demo

`Setup` initializes the terrain after the flat pipeline and before the sky,
which Chapter 35 section 7 put last, handing it the scene renderer's set 0
layout:

```cpp
    // Chapter 36 section 1: the ground.
    if (auto result = m_terrain.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats,
                                           m_sceneRenderer.FrameSetLayout());
        !result)
    {
        return result;
    }
```

`Teardown` undoes `Setup` in reverse, so the terrain is shut down just after
the sky and before the flat pipeline:

```cpp
    m_terrain.Shutdown();                                                        // Chapter 36 section 1
```

In `Record`, the terrain is drawn right after the clear to depth 0, so it is
tested against the far plane like the plates, and before them. The first
version centres it on the camera; section 2 replaces the argument:

```cpp
    // Chapter 36 section 1: the ground, after the clear to 0, and before the plates.
    m_terrain.Record(commandBuffer, m_sceneRenderer, frame.frameIndex, m_terrainSettings,
                     { m_cameraTransform.translation.x, m_cameraTransform.translation.z },
                     frame.sky.mode != SkyMode::Off);
```

**The plates.** Chapter 35's plates hang in the air at the viewpoint's
height, 100 m up; once the ground has hills, section 3 on, the near ones
stand in them. They stay, for anyone who wants Chapter 35's depth check
again, but are drawn only when the panel asks. `PrepareDraws` still sorts all
eight every frame, as Chapter 35 wrote it. Handing it none would draw nothing
too, but the scene renderer would then copy an empty list of draw commands
with `memcpy` from a null pointer, which C++ does not allow even for zero
bytes. So what changes is the drawing: in `Record`, Chapter 35's bind,
`BindFrameSet` and `RecordBatches` for the plates go inside an `if`:

```cpp
    // Chapter 35 section 3: the plates, through Chapter 19's batches, with this demo's pipeline. Chapter 36
    // section 1: only while the panel shows them, since they would stand in the ground.
    if (m_showPlates)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_flatPipeline);
        m_sceneRenderer.BindFrameSet(commandBuffer, m_flatLayout, frame.frameIndex);
        m_sceneRenderer.RecordBatches(commandBuffer, frame.frameIndex, DrawList::Scene,
                                      [&](VkCommandBuffer cb, const DrawRun& run) {
            vkCmdSetCullMode(cb, run.doubleSided ? VK_CULL_MODE_NONE : VK_CULL_MODE_BACK_BIT);
            const FlatDraw draw{ .baseColor = m_materialColors[run.material] };
            vkCmdPushConstants(cb, m_flatLayout, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(draw), &draw);
        });
    }
```

**The panel** gains a Terrain group at its top. The Depth readout moves to the
bottom and shows only while the plates do, since it describes them.
`DrawPanel` becomes:

```cpp
void HorizonDemo::DrawPanel()
{
    // Horizon draws no Camera window (section 1), so its panel takes that window's place, under Frame.
    if (debug_panels::beginDemoPanel("Horizon", debug_panels::DemoPanelSlot::BelowFrame))
    {
        DrawTerrainControls();   // Chapter 36 section 1
        DrawCameraControls();    // Chapter 35 sections 1, 4
        if (m_showPlates)        // Chapter 36 section 1: the plates' readout, while they show
        {
            DrawDepthReadout();  // Chapter 35 section 6
        }
    }
    ImGui::End();
}
```

At 1280 x 720 the panel, its Terrain and Camera groups, is about 310 pixels
tall, and about 420 with the plates' readout shown: inside the 490 pixels
Chapter 35 section 1 gave it.

The group starts with the two checkboxes this section needs; sections 2, 6, 8
and 11 add to its end. It goes above `Record`:

```cpp
// Chapter 36 section 1: the terrain's group, at the top of the panel.
void HorizonDemo::DrawTerrainControls()
{
    ImGui::SeparatorText("Terrain");
    ImGui::Checkbox("Show cell edges", &m_terrainSettings.showCells);
    ImGui::SameLine();
    ImGui::Checkbox("Show the plates", &m_showPlates);
}
```

The terrain adds files: rerun `GenerateProjects.bat`, build, and run with
`--demo Horizon`. This first run only checks that the grid is there. Below the
horizon is the sky's plain ground, as before: the grid is under the camera,
100 m down, out of view. Click once on the scene, hold the right mouse button,
and drag down to look straight down: a green square, 64 m across, with the
sky's ground around it. Turn on **Show cell edges** and it is a mesh of fine
squares. Fly with WASD: the square follows the camera, a cell at a time.

## 2. Twelve rings

**This is the rings in the vertex shader, the ring colours, `Record`'s twelve
instances, the presets, and the rings held still.**

### Each ring twice the size

One grid of half-metre cells that reached 65 km in every direction would be
262,144 cells on a side, nearly 70 billion cells (Chapter 35's "Layers by
distance" is why that cannot be). The way out is rings: at twice the distance a
cell twice the size looks the same size, so a band of the same grid with cells
twice as big reaches twice as far for the same cost. The ground is the same
grid many times over, nested around the camera, each copy twice the size of the
one inside it:

```text
  Seen from above (not to scale): the same grid, three times, each twice the size.

  +-----------------------------------+
  |               ring 2              |
  |     +-----------------------+     |
  |     |         ring 1        |     |
  |     |     +-----------+     |     |
  |     |     |  ring 0   |     |     |
  |     |     |     o     |     |     |    o  the camera
  |     |     |           |     |     |
  |     |     +-----------+     |     |
  |     |                       |     |
  |     +-----------------------+     |
  |                                   |
  +-----------------------------------+
```

Ring *L* is the same 128 x 128 grid with cells of

$$
s_L = s_0 \cdot 2^L
$$

where $s_0$ is ring 0's cell. A ring reaches half its side from its centre,
64 cells, so ring *L* reaches $64\,s_L$. A worked example: with $s_0$ = 0.5 m,
ring 11's cells are $0.5 \cdot 2^{11}$ = 1,024 m, and it reaches
64 x 1,024 m = 65,536 m: 65 km. Twelve rings, 0 to 11, cost twelve times one
grid, 1.2 million vertices, for a view 2,048 times as wide. The vertex shader
makes every vertex from its index alone, so the twelve are one draw with
twelve instances (Chapter 19 section 1), and `gl_InstanceIndex` says which ring
a vertex is in.

### Each ring on its neighbour's vertices

Where ring *L* ends, ring *L* + 1 carries on, and the two must meet: every
vertex on ring *L*'s outer edge has to lie on ring *L* + 1's grid, or the
edges of the two rings run past each other. Ring *L* + 1's vertices are at
whole numbers of *its* cells, which are two of ring *L*'s; so ring *L*'s corner
must be at an **even** number of its own cells. That is why the snap is to two
cells. Then ring *L*'s whole outer edge lies on ring *L* + 1's vertex lines:
every other vertex of ring *L* is a vertex of ring *L* + 1, and the ones between
lie halfway along one of its cell edges (section 5 comes back to those).

```text
  The edge where ring L (fine) meets ring L + 1 (coarse), from above:

  ring L + 1   +-----------+-----------+-----------+
               |           |           |           |
               |           |           |           |
  ring L       +-----+-----+-----+-----+-----+-----+
               |     |     |     |     |     |     |
               +-----+-----+-----+-----+-----+-----+
```

Ring *L*'s cell and corner are two small functions, above `main` in
`Terrain.vert.glsl`. A cell is ring 0's doubled *L* times: 0.5 m times a power
of two, which a float holds exactly, so every vertex position below is exact
too, and a vertex two rings share is the same float in both. The doubling is a
shift, `1u << level`, rather than `exp2`: GLSL lets `exp2` be a few units in
the last place off, even for a whole number, and one ring's cell a hair off
would move all of its vertices off the next ring's:

```glsl
// Section 2: ring L's cell, in metres: ring 0's, doubled L times. A power of two times 0.5 or 1, so every
// position below, a whole number of cells, is exact in a float, and a vertex two rings share is the same
// float in both. The doubling is a shift: exp2 is allowed to be a little off, and would break that.
float ringCell(uint level)
{
    return terrain.rings.y * float(1u << level);
}

// Section 2: ring L's corner (its smallest x and z), in its own cells from the origin. Half a ring short of
// the centre, snapped down to an even number of cells: a vertex of ring L + 1, whose cells are twice as big.
ivec2 ringCorner(uint level)
{
    vec2 snapped = floor(terrain.rings.xz / (2.0 * ringCell(level)));
    return 2 * ivec2(snapped) - int(terrain.rings.w) / 2;
}
```

### The middle of each ring

Every ring is a whole 128 x 128 grid, but its middle is where the ring inside
it lies. Drawn twice, the same ground would fight in the depth buffer, and it
would cost a quarter more for nothing. So in every ring but ring 0, the cells
the ring inside covers **collapse**: all six of their vertices go to the same
point, and a triangle with no area draws no pixels. The inner ring is 128 of its
own cells across, which is 64 of this ring's, and its corner is at an even
number of its cells, which is a whole number of this ring's; so the covered
cells are exactly a 64 x 64 block, and no cell is half covered.

> **Jump:** two kinds of coordinates are in play from here, and they must not
> mix. `vertex` and `square` count cells **of this ring**, from **its corner**;
> `ringCorner` counts cells of a ring from **the origin**. The inner ring's
> corner, `ringCorner(ring - 1)`, is in the inner ring's cells, half the size:
> halving it puts it in this ring's cells, and subtracting this ring's corner
> puts it in the same frame as `square`. Every comparison below is between
> numbers in that one frame. A worked example, with the camera at x = 1,234.5:
> ring 0's corner is 2 x floor(1,234.5 / 1) - 64 = 2,404 of its half-metre
> cells, and ring 1's is 2 x floor(1,234.5 / 2) - 64 = 1,170 of its metre
> cells. Halved, ring 0's corner is 1,202 metre cells; less ring 1's corner,
> that is 32. The inner block starts at square 32 and covers 32 to 95, the
> middle 64 of ring 1's 128.

`main` changes in its middle. This block **replaces** section 1's `cell` and
`corner` lines and the comment above them, and it ends above the `lattice`
line: the instance now says which ring this is, and the collapse follows.
`ring` is also an output, for the debug colours. It is `flat`: a flat output
is not blended across the triangle, which takes one vertex's value, and every
vertex of a triangle has the same ring anyway:

```glsl
    // Section 2: the instance is the ring.
    ring         = uint(gl_InstanceIndex);
    float cell   = ringCell(ring);
    ivec2 corner = ringCorner(ring);

    // Section 2: the cells the ring inside covers, a block cells/2 across, are collapsed: all six of their
    // vertices go to one point, and a triangle with no area draws nothing.
    if (ring > 0u)
    {
        ivec2 inner = ringCorner(ring - 1u) / 2 - corner;   // the inner ring's corner, in this ring's cells
        if (all(greaterThanEqual(square, inner)) && all(lessThan(square, inner + cells / 2)))
        {
            vertex = square;
        }
    }
```

And the output, beside `cellPosition`:

```glsl
layout(location = 4) flat out uint ring;        // section 2: which ring, for the ring colors
```

### Seeing the rings

A debug view colours each ring, six colours that repeat. In the fragment
shader, the input beside `cellPosition`, a table of colours above `main`, and
the tint at the end of `main`, before the cell edges:

```glsl
layout(location = 4) flat in uint ring;
```

```glsl
// Section 2: one color per ring, repeating every six.
const vec3 RING_COLORS[6] = vec3[](vec3(1.0, 0.25, 0.25), vec3(1.0, 0.8, 0.2), vec3(0.3, 1.0, 0.3),
                                   vec3(0.2, 0.9, 1.0), vec3(0.35, 0.4, 1.0), vec3(1.0, 0.35, 1.0));
```

```glsl
    // Section 2: the debug view, a color per ring.
    if ((terrain.flags & TERRAIN_SHOW_RINGS) != 0u)
    {
        color = mix(color, RING_COLORS[ring % 6u] * 0.5, 0.6);
    }
```

### Twelve instances

In `Record`, the rings flag joins the cells flag, `ringCount` becomes
`TERRAIN_RINGS` (nothing reads it until section 11's skirt, which has to know
which ring is the last), and the draw has twelve instances:

```cpp
// Under the cells flag:
    if (settings.showRings) { flags |= TERRAIN_SHOW_RINGS; }    // section 2

// In the push constants, in place of 1:
        .ringCount = TERRAIN_RINGS,                                                     // section 2

// The draw, in place of section 1's:
    // Section 2: six vertices per cell, a ring per instance, every ring in one draw.
    vkCmdDraw(commandBuffer, 6 * preset.cells * preset.cells, TERRAIN_RINGS, 0, 0);
```

### What it costs, and a preset for lavapipe

1.2 million vertices is a modest job for a GPU's vertex stage; Chapter 24
section 9's GPU timers, which Chapter 37 brings to this demo, measure it on
yours. No ring is culled. Every ring surrounds the camera, so every ring is
partly in view and Chapter 12 section 9's test, one per object, would keep all
twelve; the triangles behind the camera are dropped by clipping, after the
vertex shader has run. Culling parts of a ring, or the ground hills hide
(Chapter 26 section 9's depth pyramid), is for when the timers ask for it.

On lavapipe, Mesa's Vulkan driver that runs on the CPU, the full rings take
about half a second a frame, too slow to fly. So `Terrain.h` has two presets. **Full** is 128 cells a
side with half-metre cells; **Low** is 64 cells a side with 1 m cells, a quarter
of the vertices, reaching just as far: ring 11 is 32 x 2,048 m = 65,536 m
again. A device whose type is `VK_PHYSICAL_DEVICE_TYPE_CPU` starts on Low, any
other on Full, the first time `Setup` runs; after that the panel's choice
stands. A GPU never meets the Low preset unless you pick it. In `Setup`, before
the terrain's `Initialize`:

```cpp
    // Chapter 36 section 2: lavapipe, which is a CPU, starts on the light preset, a GPU on the full one;
    // only the first time, so the panel's choice survives switching demos.
    if (!m_presetChosen)
    {
        VkPhysicalDeviceProperties device{};
        vkGetPhysicalDeviceProperties(m_context.vulkan.physicalDevice, &device);
        m_terrainSettings.preset = device.deviceType == VK_PHYSICAL_DEVICE_TYPE_CPU ? 1u : 0u;
        m_presetChosen           = true;
    }
```

### Holding the rings still

The rings follow the camera, so from the camera they always look the same:
nested around you, wherever you go. To see them as they are, they can be held
still while the camera flies off and looks back. `m_ringCenter` is where they
are centred; `Update` moves it to the camera every frame unless the panel
froze it, right after `KeepCameraInBounds`:

```cpp
    if (!m_terrainSettings.freezeRings)   // Chapter 36 section 2: the rings follow the camera, unless frozen
    {
        m_ringCenter = { m_cameraTransform.translation.x, m_cameraTransform.translation.z };
    }
```

and `Record` hands it to the terrain, in place of the camera's position:

```cpp
    m_terrain.Record(commandBuffer, m_sceneRenderer, frame.frameIndex, m_terrainSettings, m_ringCenter,
                     frame.sky.mode != SkyMode::Off);
```

Frozen rings keep their detail where they were, too: section 3 fades detail by
the distance from the rings' centre, not from the camera, so a camera flown
away from them is over the coarse ground they draw there, and section 6's copy
of the height follows them.

The panel gets the two checkboxes and the presets, at the end of
`DrawTerrainControls`:

```cpp
    // Section 2: the rings, and the two presets.
    ImGui::Checkbox("Show rings", &m_terrainSettings.showRings);
    ImGui::SameLine();
    ImGui::Checkbox("Freeze rings", &m_terrainSettings.freezeRings);
    if (ImGui::BeginCombo("Preset", TERRAIN_PRESETS[m_terrainSettings.preset].name))
    {
        for (uint32_t preset = 0; preset < TERRAIN_PRESETS.size(); ++preset)
        {
            if (ImGui::Selectable(TERRAIN_PRESETS[preset].name, preset == m_terrainSettings.preset))
            {
                m_terrainSettings.preset = preset;
            }
        }
        ImGui::EndCombo();
    }
```

Run it. The flat green now reaches the horizon. Turn on **Show rings**: bands
of colour, one ring each. The two nearest are about as tall on the screen as
each other, and from there each is half as tall as the one before it,
crowding toward the horizon: a ring twice as far away takes up half the angle
below it.

To see the rings as they are, hold them still and fly away from them. Turn on
**Freeze rings**, click on the scene, hold Shift and D until the panel's
Position shows x near 500 (about two and a half seconds at 200 m/s), then
Shift and E until the Position stops at y = 1,400, the ceiling, and look
straight down: hold the right mouse button and drag down until the view stops
turning. The rings are nested squares, each twice the size of the one inside
it, centred half a kilometre to your left, where the camera was when you froze
them. Turn **Freeze rings** off and they jump to be centred under you.

## 3. Height, and the rule for detail

**This is `TerrainHeight.glsl` and the height in `main`.**

### Octaves of noise

Chapter 27 section 2's gradient noise is a smooth random function: random
slopes at the corners of a unit lattice, blended across each square, in about
[-0.7, 0.7]. One wave of it is a gentle bump; mountains take several, each
half as long and half as tall as the one before: **octaves**. Here the first
is 8,192 m long and the thirteenth 2 m. Each octave is the noise times 0.05 of
its wavelength, so it stands at most 0.05 x 0.7 = 0.035 of its wavelength, about
a thirtieth, above or below the middle. A worked example: the 8,192 m octave
reaches ±287 m; the next ±143 m; all thirteen together are bounded by twice
the first, ±573 m.

At a lattice point the noise is exactly 0. Each corner adds its slope times
the offset from that corner to the point, and at a lattice point the only
corner with any weight is the one there, whose offset is zero. The origin is a
lattice point of every octave, so the ground there is at 0 m, 100 m below
where the camera starts.

Two changes from Chapter 27's noise. The slope at a lattice point comes from a
table of eight directions, the axes and the diagonals, picked by the same
`pcgHash` (Chapter 20 section 3) of the point: Chapter 27 took the cosine and
sine of a hashed angle, and the CPU's `cos` and the GPU's differ in their last
bits, where a table reads the same numbers on both, which section 6 needs. And
the octaves fade out with distance, which is the rest of this section.

### How many cells a wave needs

The rings draw the height only at their vertices, and draw straight lines
between them. A wave with many vertices along each wavelength comes out as the
wave. With fewer, what is drawn depends on where the vertices happen to fall:
two per wavelength can land on the crests, or on the slopes halfway down, or
on the zero crossings, which draws nothing at all. With fewer than two, the
vertices trace a different, longer wave that is not in the ground at all; this
is *aliasing*. And the vertices do not stay on one spot of the wave: as section
2's rings move, ground passes from one ring to the next, and is drawn by a
different set of vertices.

So each octave should be drawn only where the cells are small enough for it.
How big are the cells at a distance *d* from the rings' centre? Measure *d*
along x or z, whichever is further, because the rings are squares. Ring *L*'s
cells begin where the ring inside it ends. That ring is *N* of its own cells
across, *N*/2 of ring *L*'s, so it reaches *N*/4 of them, 32 $s_L$, either side
of its centre; but its corner snaps down to a whole number of ring *L*'s cells,
which can bring its edge up to one of them nearer the centre. So ring *L*
starts at least $(N/4 - 1)\,s_L$ = 31 $s_L$ out, and a point at distance *d* in
ring *L* has $s_L \le d / 31$. At distance *d* the cells are at most

$$
c(d) = \max\!\left(s_0,\ \frac{d}{N/4 - 1}\right)
$$

with *N* = 128 cells a side, *N*/4 - 1 = 31, and never smaller than ring 0's.
A worked example: at 1 km, $c$ = 1,000 / 31 = 32.3 m.

**The rule.** An octave of wavelength $\lambda$ is drawn at full strength while
it spans four or more of those cells, and fades out by the time it spans two:

$$
\text{strength} = \text{smoothstep}\bigl(2c(d),\ 4c(d),\ \lambda\bigr)
$$

`smoothstep` is Chapter 16 section 5's: 0 below its first edge, 1 above its
second, and between them $3s^2 - 2s^3$, where *s* is how far from the first
edge to the second the value has come. At 1 km, $2c$ = 64.5 m and $4c$ =
129 m. The 128 m octave has come 63.5 of the 64.5 m between them, *s* =
0.984, and is at smoothstep(64.5, 129, 128) = 0.999: all but full. The 64 m
one, below 64.5 m, is gone, and the octaves between fade. At the camera, where
the cells are half a metre, all thirteen octaves are there, down to the 2 m
one.

> **Jump:** the rule ties detail to the distance from the rings' centre. Keep
> three facts together. Every vertex sits at a whole number of its ring's cells
> from the origin, so while the rings stay put no vertex moves across the
> ground; only the bands where one ring hands ground to the next change their
> vertices. The strength depends only on the distance, never on which ring
> draws a point, so on both sides of such a band every octave still drawn spans
> at least two of the coarse cells, and a vertex two rings share has the same
> height in both. And because it is the distance from the centre, far ground
> changes its shape a little as the camera moves: an octave out there is part
> of the way through its fade, and a few hundred metres of flight change how
> much of it is drawn. Section 2's **Freeze rings** holds that still. In
> numbers, at 100 m the cells are at most 3.2 m, so an octave is at full
> strength from 13 m long and gone below 6.5 m; at 10 km they are 323 m, with
> full strength from 1,290 m and gone below 645 m (1 km is the worked example
> above).

Why four and two? Stricter, eight and four, keeps more cells to every wave and
halves the detail everywhere: mountains a few kilometres off turn to rounded
lumps. Looser, two and one, lets the coarse rings draw waves they
cannot hold, and the far ridges crawl as you fly. Four and two is the least
detail that does not alias; the fade between them is what keeps a wave from
appearing or vanishing at once.

### `TerrainHeight.glsl`

The height is a function that several shaders will want (Chapter 40 places
trees with it), so it lives in an include of its own, as `Noise.glsl` does for
the grass. It reads `terrain`, the push constants, so a shader includes it
after declaring that block:

```glsl
// Shaders/Horizon/TerrainHeight.glsl - Chapter 36: the ground's height at any point, as the rings draw it.
// An include: Terrain.vert.glsl includes it after its TerrainDraw block, named `terrain`, which it reads.
// Terrain.cpp keeps a copy on the CPU (Terrain::HeightAt); change one and you must change the other.
#ifndef PF_HORIZON_TERRAIN_HEIGHT_GLSL
#define PF_HORIZON_TERRAIN_HEIGHT_GLSL

#include "Random.glsl"   // pcgHash

// Section 3: the gradient at each lattice point, one of eight: the four axes and the four diagonals. A table,
// where Chapter 27's noise took the cosine and sine of a hashed angle, so that the CPU's copy finds exactly
// the same numbers.
const vec2 GRADIENTS[8] = vec2[](
    vec2(1.0, 0.0), vec2(-1.0, 0.0), vec2(0.0, 1.0), vec2(0.0, -1.0),
    vec2(0.70710678, 0.70710678), vec2(-0.70710678, 0.70710678),
    vec2(0.70710678, -0.70710678), vec2(-0.70710678, -0.70710678));

vec2 latticeGradient(ivec2 point)
{
    return GRADIENTS[pcgHash(uint(point.x) ^ pcgHash(uint(point.y))) & 7u];
}

// Section 3: Chapter 27's gradient noise, in about [-0.7, 0.7], with the table's gradients.
float gradientNoise(vec2 p)
{
    ivec2 cell = ivec2(floor(p));
    vec2  f    = fract(p);
    vec2  u    = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);

    float a = dot(latticeGradient(cell + ivec2(0, 0)), f - vec2(0.0, 0.0));
    float b = dot(latticeGradient(cell + ivec2(1, 0)), f - vec2(1.0, 0.0));
    float c = dot(latticeGradient(cell + ivec2(0, 1)), f - vec2(0.0, 1.0));
    float d = dot(latticeGradient(cell + ivec2(1, 1)), f - vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

// Section 3: the size of the largest cell the rings draw at xz. A point at distance d from the rings' centre,
// along x or z, whichever is further, lies in a ring whose cells are at most d / (N/4 - 1) across, and never
// finer than ring 0's.
float cellSizeAt(vec2 xz)
{
    vec2  offset = abs(xz - terrain.rings.xz);
    float reach  = max(offset.x, offset.y);   // not `distance`, which would shadow GLSL's built-in distance()
    return max(terrain.rings.y, reach / (terrain.rings.w / 4.0 - 1.0));
}

// Section 3: octaves of noise, from `wavelength` down, each half as long and half as tall as the one before;
// an octave stands about a thirtieth of its wavelength above or below. An octave is drawn at full strength
// while it spans four or more cells, and fades out by the time it spans two, the fewest that can draw a
// wave at all. The octaves get shorter, so once one has gone, every later one has too.
float noiseOctaves(vec2 xz, float wavelength, int octaves)
{
    float cell   = cellSizeAt(xz);
    float height = 0.0;
    for (int octave = 0; octave < octaves; ++octave)
    {
        float strength = smoothstep(2.0 * cell, 4.0 * cell, wavelength);
        if (strength <= 0.0)
        {
            break;
        }
        height    += strength * 0.05 * wavelength * gradientNoise(xz / wavelength);
        wavelength *= 0.5;
    }
    return height;
}

// The ground's height at xz: thirteen octaves, 8,192 m down to 2 m.
float terrainHeight(vec2 xz)
{
    return noiseOctaves(xz, 8192.0, 13);
}

#endif
```

This is the tutorial's second grid from `gl_VertexIndex`, its second gradient
noise and its third `terrainHeight` (Chapter 25 section 3's sums sines and takes
`(xz, shape)`; Chapter 27 section 9's CPU copy takes `(xz, amplitude,
wavelength)`; this one takes `(xz)` alone). They are copies on purpose, each
shaped for its own demo, and the index lists them as a module not yet
extracted. Section 10's water and section 11's haze copy Chapters 29 and 30's
the same way.

In `Terrain.vert.glsl`, the include goes under the push-constant block:

```glsl
#include "TerrainHeight.glsl"   // section 3: terrainHeight, which reads `terrain`
```

and `main` changes in two places. The height of each vertex goes below `xz`:

```glsl
    float height  = terrainHeight(xz);
```

and the line near the end that sets `worldPosition`, which section 1 left at
height 0, is **replaced**, so that the vertex is drawn at that height:

```glsl
    worldPosition = vec3(xz.x, height, xz.y);
```

Leave the two lines apart. Every later section that adjusts the height or
the position puts its lines **between** them, below `float height` and above
`worldPosition`. That line is what gets drawn, so a change to the height made
below it changes a variable nothing draws, and no error says so. The
Checkpoint at the end lists `main`'s lines in their finished order.

Run it: one flat green to the horizon, its hills hard to see without light.
Turn on **Show cell edges** and **Show rings**: the grid lies over rolling
hills, each ring's cells twice the size of the last. Look closely along the
borders between rings and you may find specks of the background showing
through; section 5 is about them.

## 4. Normals and light

**This is the normal in the vertex shader, the light in the fragment shader,
and the sun in `FrameData`.**

The hills are one flat green; light shows their shape. A surface's normal comes
from its slope, by Chapter 25 section 3's central differences: the height a
step either side in x and in z. The step is a cell, the cell section 3's rule
gives at that point, `cellSizeAt`, rather than the ring's own: the rule's cell
changes smoothly with distance, so two rings meeting at a border compute their
normals with the same step there, and the shading has no seam where the
geometry has none. It is computed per vertex and blended across the triangle;
the fragment shader has no height function to call. In `main`, below the
height and above section 3's `worldPosition` line:

```glsl
    // Section 4: the slope from four heights a cell apart (Chapter 25 section 3's central differences),
    // with the cell section 3's rule gives here, so neighbouring rings agree along their border.
    float apart = cellSizeAt(xz);
    float dx    = terrainHeight(xz + vec2(apart, 0.0)) - terrainHeight(xz - vec2(apart, 0.0));
    float dz    = terrainHeight(xz + vec2(0.0, apart)) - terrainHeight(xz - vec2(0.0, apart));
    vertexNormal = normalize(vec3(-dx, 2.0 * apart, -dz));
```

with its output beside `worldPosition`:

```glsl
layout(location = 1) out vec3  vertexNormal;    // section 4
```

**The light** is Chapter 11 section 14's, through `FrameData`: the flat
pipeline never needed a sun, so Chapter 35's `Record` never wrote one. The sun
is the one the sky is baked from, `SUN_TRAVEL`, and `sunColor` is what a white
surface facing it reflects, its irradiance E over π (Chapter 15 section 9).
Chapter 35 handed the sky π x (0.90, 0.85, 0.80) as the sun's irradiance, so
`sunColor` is (0.90, 0.85, 0.80) itself. The ambient light is the sky's, from
set 0 binding 10, when the sky is on and lights the scene (Chapter 24 section
4), and a constant pale blue otherwise. The constants go under `SUN_TRAVEL`:

```cpp
// Chapter 36 section 4: the same sun's color, as FrameData wants it: E / pi, so a white surface facing it
// reflects this (Chapter 11). And the ambient light with the sky off, a pale blue.
constexpr glm::vec3 SUN_COLOR{ 0.90f, 0.85f, 0.80f };
constexpr glm::vec3 FLAT_AMBIENT{ 0.20f, 0.25f, 0.32f };
```

and `Record` writes them into `FrameData`, under `frameData.time`.
`skyLightsScene` is the rule every demo applies, Chapter 24 section 4's, from
`SkySettings.h`: the sky lights the scene when it is asked to and there is a
sky:

```cpp
    // Chapter 36 section 4: the light the terrain is shaded with: the sky's sun, and the sky as ambient light
    // when it is on and lights the scene (Chapter 24), else a constant.
    frameData.sunDirection   = glm::vec4(SUN_TRAVEL, 0.0f);
    frameData.sunColor       = glm::vec4(SUN_COLOR, 0.0f);
    frameData.ambientColor   = glm::vec4(FLAT_AMBIENT, 0.0f);
    frameData.ambientMode    = skyLightsScene(frame.sky) ? AMBIENT_SKY : AMBIENT_FLAT;
```

**What the ground is made of** depends on its height and its slope: sand by the
sea, grass, bare rock where it is steep, snow on the highest tops. The normal's
y, `up`, is the cosine of the slope: 1 on the flat, 0.7 at 45 degrees. Rock
comes in as `up` falls from 0.75 to 0.6, which is `1.0 - smoothstep(0.6, 0.75, up)`:
`smoothstep` wants its first edge below its second, and GLSL leaves the other
order undefined. These are linear albedos, a fraction of the light each surface
reflects. In the fragment shader, the sky's light is one binding, declared
under the push-constant block, and the normal is one more input, under
`worldPosition`'s; the two functions go above `main`:

```glsl
layout(set = 0, binding = 10) uniform samplerCube skyDiffuse;    // section 4: Chapter 24's light, E / pi
layout(location = 1) in vec3  vertexNormal;
```

```glsl
// Section 4: what the ground is made of, from its height and how steep it is (`up` is the normal's y: 1 on
// the flat, 0 on a cliff). Linear albedos: sand by the sea, grass, rock on the steep, snow on the tops.
vec3 groundAlbedo(float height, float up)
{
    const vec3 SAND  = vec3(0.45, 0.40, 0.28);
    const vec3 GRASS = vec3(0.08, 0.15, 0.04);
    const vec3 ROCK  = vec3(0.22, 0.19, 0.15);
    const vec3 SNOW  = vec3(0.80, 0.82, 0.85);
    vec3 albedo = mix(SAND, GRASS, smoothstep(2.0, 6.0, height));
    albedo      = mix(albedo, ROCK, (1.0 - smoothstep(0.6, 0.75, up)) * smoothstep(1.0, 4.0, height));
    return mix(albedo, SNOW, smoothstep(820.0, 900.0, height) * smoothstep(0.75, 0.85, up));
}
```

`frame.sunDirection` is the way sunlight travels (Chapter 11 section 14), so
the way toward the sun is its negation, and the sun's share is the cosine
between that and the normal:

```glsl
// Section 4: Chapter 11's light, for a matte surface facing N: the sun, whose sunColor is already E / pi, and
// the light from everywhere else, which is Chapter 24's sky when it lights the scene.
vec3 lightAt(vec3 N)
{
    vec3 ambient = frame.ambientMode == AMBIENT_SKY ? texture(skyDiffuse, N).rgb : frame.ambientColor.rgb;
    return frame.sunColor.rgb * max(dot(N, -frame.sunDirection.xyz), 0.0) + ambient;
}
```

`main`'s one green line becomes the ground lit, in three lines:

```glsl
    // Section 4: the ground, lit.
    vec3 N     = normalize(vertexNormal);
    vec3 color = groundAlbedo(worldPosition.y, N.y) * lightAt(N);
```

Run it: the ground is lit now, a little brighter where it faces the sun and
darker where it turns away. It is green above a few metres and pale below 2 m,
where the noise dips under 0, as it does to your left: that is the sand, which
the sky's blue light turns nearly grey. The hills are not gentle, a few hundred
metres from valley floor to top within a kilometre of the start, and still no
slope passes 28 degrees. Climb with Shift and E, held until the panel's
Position reads 1,400, the ceiling, and look a little down: green ground and
winding bands of pale lowland, the ground the noise leaves below 0, which
section 10's sea will flood. No slope of this noise is steep enough for rock,
nor any top high enough for snow; the island's are, from section 9. The specks
along the ring borders are section 5's cracks.

## 5. Cracks between rings

**This is the averaging on each ring's outer edge, the seals and their
vertices in `Record`'s draw, and the pipeline's culling.**

### Cracks

Look along the borders between rings with **Show cell edges** on. Every other
vertex on a ring's outer edge is not a vertex of the ring outside it (section
2's picture): the coarse ring's edge runs straight from one of its vertices to
the next, and the fine ring's vertex between them is at the ground's true
height, above or below that straight line. Between the two there is a sliver
of nothing, a **crack**, and whatever is behind it shows through.

```text
  The border, seen from the side: the coarse edge is straight, the fine vertex is not on it.

         fine vertex at the true height
                    *
                  /   \            the gap: a crack
  coarse ---------*-----*--------- the coarse ring's edge, straight
             shared vertex   shared vertex
```

The fix is to move each of those vertices onto the straight line: its height
becomes the average of its two neighbours along the edge, which are shared with
the coarse ring and have the same heights in both. The vertex is then exactly
on the coarse edge, and the crack closes. In `main`, below `float height` and
above section 4's normal, so that it comes before the `worldPosition` line that
draws the height (section 3):

```glsl
    // Section 5: on the outer edge, every other vertex has no partner in the ring outside, whose edge runs
    // straight from one of its vertices to the next. Moved onto that straight line, it closes the crack.
    bool onZEdge = vertex.x == 0 || vertex.x == cells;   // on an edge that runs along z: x is first or last
    bool onXEdge = vertex.y == 0 || vertex.y == cells;   // on an edge that runs along x: z is first or last
    if (onXEdge && (lattice.x & 1) != 0)
    {
        height = 0.5 * (terrainHeight(xz - vec2(cell, 0.0)) + terrainHeight(xz + vec2(cell, 0.0)));
    }
    else if (onZEdge && (lattice.y & 1) != 0)
    {
        height = 0.5 * (terrainHeight(xz - vec2(0.0, cell)) + terrainHeight(xz + vec2(0.0, cell)));
    }
```

A vertex is on an edge that runs along x when its z is the grid's first or
last, `onXEdge`; along that edge, the vertices between the coarse ring's are
the ones whose x, in this ring's cells from the origin, is odd. `& 1` reads the
lowest bit, which works for negative numbers too. The corners lie on both kinds
of edge, but their x and z are both even, so neither branch moves them.

### Pinholes

With the fix, the coarse edge and the fine one are the same line, exactly, in
real numbers. The GPU does not draw with real numbers: it rounds every vertex
to a grid of sub-pixel positions before it fills triangles, and the fine
ring's in-between vertex, rounded, can land a hair off the coarse ring's edge.
Its rounding opens a sliver too thin to see, except where it happens to cover
the centre of a pixel: then that one pixel is left undrawn, a **pinhole**, and
which pixels they are changes as the camera moves.
From the start view, with the averaging alone, one pixel of the 456,000 below
the horizon was left open.

Rounding cannot open a gap between two triangles that **share an edge**:
Vulkan requires that a pixel centre lying exactly on an edge two triangles
share be covered by exactly one of them (Direct3D's *top-left rule* is one
way to choose which). So the gap gets triangles of its own: for each pair of
cells along a ring's outer edge, the triangle from one shared vertex, through
the vertex between, to the next. It shares its two short edges with the fine
ring's triangles and its long one with the coarse ring's, and in real numbers
it has no area at all; but whatever rounding does to it, it fills exactly the
sliver rounding made. These are **seals**.

They come after the grid's vertices, three for each pair of cells on the outer
edge. A side has *N*/2 pairs and a ring four sides, so `Record` draws 3 x 2*N*
= 6*N* more. Its draw becomes:

```cpp
    // Section 2: six vertices per cell, a ring per instance, every ring in one draw. Section 5: and three more
    // for each pair of cells along the outer edge, the seals.
    vkCmdDraw(commandBuffer, 6 * preset.cells * preset.cells + 6 * preset.cells, TERRAIN_RINGS, 0, 0);
```

and in `main`, directly below the `vertex` line and above section 2's `ring`
lines, an index past the grid's is a seal's: which pair of edge cells it seals,
on which side, and which of the three vertices, in the order shared, between,
shared. Which way round that makes the triangle does not matter; the next part
sees to that:

```glsl
    // Section 5: after the grid's vertices, the seals along the outer edge: for each pair of edge cells, the
    // triangle from one shared vertex through the odd one to the next, which has no area. It is drawn once,
    // and the pipeline does not cull, so which way round it ends up facing does not matter.
    int seal = gl_VertexIndex - 6 * cells * cells;
    if (seal >= 0)
    {
        int pair  = seal / 3;                              // 0 to 2 * cells - 1: cells / 2 pairs on each side
        int side  = pair / (cells / 2);                    // 0: z = 0, 1: x = cells, 2: z = cells, 3: x = 0
        int along = 2 * (pair % (cells / 2)) + seal % 3;   // the pair's shared vertex, the odd one, the next shared
        vertex = side == 0 ? ivec2(along, 0) : side == 1 ? ivec2(cells, along)
               : side == 2 ? ivec2(along, cells) : ivec2(0, along);
    }
```

Everything below `main`'s seal block treats a seal's vertex as any other vertex
on the edge: the shared ones get their height, the one between gets the
average. The collapse test, which reads `square`, never matches a seal: its
index is past the grid's, so its `square.y` is at least `cells`, and the
collapsed block ends above that row. The seals cost 768 vertices a ring at
the full preset, under 1% more.

### No culling

One more change, and it is a line in the pipeline. A triangle with no area has
no front and no back: which way round a seal faces is up to the last bits of
its three positions, and a pipeline that culls back faces drops every seal
that comes out facing away, and with it the pixel it was there to fill. Two
ways round that. The seals could be a draw of their own, with culling set to
none for it alone, as Chapter 35 section 3's flat pipeline sets its cull mode
per run. Or the ground could stop culling at all, which is one line, and what
this chapter does. In `CreatePipeline`, section 1's `cullMode` becomes:

```cpp
        .cullMode       = VK_CULL_MODE_NONE,       // section 5: a seal has no front or back
```

Nothing else in the picture changes. The ground is a height field seen from
above, so a triangle that faces away from the camera, the far side of a hill,
always has ground in front of it, and the depth test throws its pixels away as
it throws away anything hidden. What culling did was spare the rasterizer those
triangles, and that is the price.

Culling comes after the vertex shader, so the 1.2 million vertex shader runs of
section 2 are the same either way. What changes is what the rasterizer is
handed: the triangles that face away, few from the viewpoint, where the island
lies open below you, and many from the ground, where every hill hides the
next. On lavapipe, which rasterizes on the CPU, a frame from the ground takes
measurably longer without culling, and from the viewpoint the difference is
lost in the variation. Chapter 37's GPU timers will say what it is on yours.
The Exit check puts culling back, to show what it was doing.

### Seeing them

To see the cracks for yourself, change the clear colour in `HorizonDemo::Record`
to magenta, `{ 1.0f, 0.0f, 1.0f, 1.0f }`, and leave the sky **Off**: the clear
colour then shows wherever nothing was drawn. Take a full-size screenshot from
the start view and count the magenta pixels below the horizon. Counting by
eye gets it wrong, since one pixel is about one in a million of the picture.
This script counts them (it needs Pillow: `pip install pillow`). Give it the
screenshot and the row the horizon is on, where the magenta above the ground
ends: 360 in a 1280 x 720 window. It counts from three rows below, so that the
horizon's own line is not counted:

```python
# count_magenta.py: python count_magenta.py screenshot.png <the horizon's row>
import sys
from PIL import Image   # pip install pillow

image = Image.open(sys.argv[1]).convert("RGB")
first_row = int(sys.argv[2]) + 3   # three rows below the horizon, so its own line is not counted
found = []
for y in range(first_row, image.height):
    for x in range(image.width):
        r, g, b = image.getpixel((x, y))
        if r > 200 and g < 60 and b > 200:   # magenta: a lot of red and blue, little green
            found.append((x, y))
print(len(found), "magenta pixels below row", first_row, found[:10])
```

Take out both fixes, the averaging `if`/`else` and the seals' `+ 6 * preset.cells`
in `Record`: about 150 magenta pixels (155 here; the count changes a little
with the frame), along the ring borders, more of them far off, where the rings
are coarse. Put back the averaging alone: one pixel is left, a pinhole. Put back
the seals as well: none, zero. The seals alone leave none here either: without
the averaging, each seal is a real triangle standing in its crack, a sliver of
ground that belongs to neither ring, and it fills the crack. The averaging is
what makes the two rings' edges one line, so that the seals only ever fill what
rounding opens. Put the colour back.

Over the island, from section 9 on, the count depends on the ground in view,
and with neither fix runs from about ten pixels to hundreds. With both, none,
and the Exit check asks for none, in the finished demo, from its two views.

## 6. Standing on it: the CPU's copy

**This is the noise on the CPU, `HeightAt`, the camera kept above the ground,
and the ground in the panel.**

Fly into a hill and you are inside it, looking at the ground from underneath.
At 200 m/s that takes a moment's inattention. The camera should stand on the
ground, and the GPU's heights are on the GPU; the CPU needs its own.

It is the same function, copied. Chapter 27 section 9 kept a CPU copy of
Chapter 25's sine hills for the ball; this copy is longer, but every line maps
to one in `TerrainHeight.glsl`. `pcgHash` is plain 32-bit arithmetic, which
wraps the same way in C++'s `uint32_t` as in GLSL's `uint`; the gradients are
the same table; and `glm` has `floor`, `dot`, `mix`, `max` and `smoothstep`
with GLSL's definitions. Two things are passed in that the shader reads from
its push constants: `cellSizeAt` takes the rings' centre, ring 0's cell and
the cells per side, and `noiseOctaves` takes the cell `cellSizeAt` found. The
five functions go at file scope, above the `namespace` line, after
`transitionLevels` once section 8 writes it:

```cpp
// File scope, above the namespace block. Section 6: TerrainHeight.glsl's noise, on the CPU, line for line.
// Change one and you must change the other.
static uint32_t pcgHash(uint32_t value)   // Random.glsl's
{
    const uint32_t state = value * 747796405u + 2891336453u;
    const uint32_t word  = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
    return (word >> 22u) ^ word;
}

static glm::vec2 latticeGradient(glm::ivec2 point)
{
    static constexpr glm::vec2 GRADIENTS[8] = {
        { 1.0f, 0.0f }, { -1.0f, 0.0f }, { 0.0f, 1.0f }, { 0.0f, -1.0f },
        { 0.70710678f, 0.70710678f }, { -0.70710678f, 0.70710678f },
        { 0.70710678f, -0.70710678f }, { -0.70710678f, -0.70710678f },
    };
    return GRADIENTS[pcgHash(static_cast<uint32_t>(point.x) ^ pcgHash(static_cast<uint32_t>(point.y))) & 7u];
}

static float gradientNoise(glm::vec2 p)
{
    const glm::ivec2 cell = glm::ivec2(glm::floor(p));
    const glm::vec2  f    = p - glm::floor(p);
    const glm::vec2  u    = f * f * f * (f * (f * 6.0f - 15.0f) + 10.0f);

    const float a = glm::dot(latticeGradient(cell + glm::ivec2(0, 0)), f - glm::vec2(0.0f, 0.0f));
    const float b = glm::dot(latticeGradient(cell + glm::ivec2(1, 0)), f - glm::vec2(1.0f, 0.0f));
    const float c = glm::dot(latticeGradient(cell + glm::ivec2(0, 1)), f - glm::vec2(0.0f, 1.0f));
    const float d = glm::dot(latticeGradient(cell + glm::ivec2(1, 1)), f - glm::vec2(1.0f, 1.0f));
    return glm::mix(glm::mix(a, b, u.x), glm::mix(c, d, u.x), u.y);
}

// The shader's cellSizeAt, with what it reads from the push constants passed in: the largest cell the rings
// draw at xz, when they are centred on ringCenter.
static float cellSizeAt(glm::vec2 xz, glm::vec2 ringCenter, float finestCell, float cells)
{
    const glm::vec2 offset = glm::abs(xz - ringCenter);
    const float     reach  = glm::max(offset.x, offset.y);
    return glm::max(finestCell, reach / (cells / 4.0f - 1.0f));
}

// The shader's noiseOctaves, with the cell passed in: cellSizeAt's, at xz.
static float noiseOctaves(glm::vec2 xz, float cell, float wavelength, int octaves)
{
    float height = 0.0f;
    for (int octave = 0; octave < octaves; ++octave)
    {
        const float strength = glm::smoothstep(2.0f * cell, 4.0f * cell, wavelength);
        if (strength <= 0.0f)
        {
            break;
        }
        height     += strength * 0.05f * wavelength * gradientNoise(xz / wavelength);
        wavelength *= 0.5f;
    }
    return height;
}
```

`HeightAt` is `terrainHeight` for rings centred on `ringCenter`: the cell, and
so every octave's strength, as the shader finds them at that point. Under the
camera, with the rings centred on it, that is ring 0's half-metre cell and all
thirteen octaves; under a camera flown away from frozen rings, it is the
coarser cell they draw there, with the short octaves faded as they are on
screen. It goes at the end of the file, inside the namespace; section 9 adds
the heightmap to it:

```cpp
// Section 6: terrainHeight on the CPU, for rings centred on ringCenter: the octaves fade by the same cell as
// in the shader. Section 9 adds the heightmap.
float Terrain::HeightAt(glm::vec2 xz, glm::vec2 ringCenter, const TerrainSettings& settings) const
{
    const TerrainPreset& preset = TERRAIN_PRESETS[settings.preset];
    const float          cell   = cellSizeAt(xz, ringCenter, preset.finestCell, static_cast<float>(preset.cells));
    return noiseOctaves(xz, cell, 8192.0f, 13);
}
```

The CPU and GPU now compute the same numbers, in the same order, in 32-bit
floats; they can still differ in the last bit or two, where a compiler fuses a
multiply and an add, which is far less than a millimetre.

**The camera** stays 1.5 m above the ground. At 200 m/s and 60 frames a
second, the camera moves 3.3 m a frame, and `KeepCameraInBounds` runs every
frame after the controller has moved it, so it never ends a frame below. The
constant goes under `FLAT_AMBIENT`:

```cpp
// Chapter 36 section 6: how far above the ground the camera stays.
constexpr float GROUND_CLEARANCE = 1.5f;   // metres
```

and `KeepCameraInBounds` gains its last lines, after the ceiling. The rings are
centred on the camera unless they are frozen, and then on `m_ringCenter`; when
they are not frozen, `m_ringCenter` is still last frame's here, because
`Update` moves it after this function, so the camera's own position stands in.
The ground is never taken as lower than 0, which from section 10 on is the sea:

```cpp
    // Chapter 36 section 6: and above the ground, or the sea, by GROUND_CLEARANCE: the ground as the rings
    // draw it, centred on the camera, or where they were frozen.
    const glm::vec2 here   = { position.x, position.z };
    const glm::vec2 center = m_terrainSettings.freezeRings ? m_ringCenter : here;
    const float     ground = std::max(m_terrain.HeightAt(here, center, m_terrainSettings), 0.0f);
    position.y = std::max(position.y, ground + GROUND_CLEARANCE);
```

The panel shows the ground under the camera, at the end of
`DrawTerrainControls`, where `m_ringCenter` is this frame's:

```cpp
    // Section 6: the ground under the camera, from the CPU's copy of its height.
    const glm::vec3& position = m_cameraTransform.translation;
    const float      ground   = m_terrain.HeightAt({ position.x, position.z }, m_ringCenter, m_terrainSettings);
    ImGui::Text("Ground  %.1f m, camera %.1f m above", ground, position.y - std::max(ground, 0.0f));
```

## Checkpoint

Rerun `GenerateProjects.bat` if you have not since section 1, build, and run
with `--demo Horizon`. Rolling hills of noise, lit by the sun, reach the
horizon in every direction; at the start the panel reads **Ground 0.0 m,
camera 100.0 m above**. **Show rings** colours the rings; **Show cell edges**
shows the grid on the hills, finer near you. Click on the scene and dive with
Shift and Q: the camera stops with the panel reading 1.5 m above the ground.
Fly on with Shift and W: the camera rides up over the hills and never goes in;
where the ground falls away, it flies on level. Turn on **Freeze rings**, and
click on the scene again, because ImGui keeps the keyboard after a click on the
panel (Chapter 10 section 10); fly a kilometre off with Shift and W and dive
again: the camera stops on the ground the frozen rings draw there. (Over the
heightmap it does not quite, as section 9 says; Chapter 37 section 4 makes it
exact.)

---

# Part 2 — An island (sections 7-10)

Noise makes hills, but not the valleys, ridges and coast that water carves:
Part 2 swaps its long octaves for an eroded heightmap, and floods everything
below 0.

## 7. A heightmap, made by erosion

**This is `Assets/Terrain/make_island.py` and what it writes.**

> **Jump:** this section leaves the engine for a while: no C++ and no shaders,
> a Python script that makes the data the next three sections draw. Keep in
> mind only what it hands over: a square image of 16-bit heights, how many
> metres its side stands for, and which heights its 0 and its 65,535 mean.
> Section 8 picks up those three numbers.

A heightmap is an image whose texels are heights. Two choices decide most of
it. **Sixteen bits per texel**, not eight: 8 bits give 256 levels, which over
the island's 1,200 m of range is a step of 4.7 m, and every slope would come
out as terraces; 16 bits give 65,536 levels, steps of 1.8 cm. And **its size**:
4,096 texels a side at 8 m each is 32,768 m, a 33 km map with an island about
21 km across inside it and sea round it, in 32 MB, 43 MB with its mip levels
(section 8). Near the camera, 8 m texels are coarse, which is what section 9's
noise octaves are for.

The heightmap is made by a script, as `make_sky_test.py` made Chapter 23's test
sky: plain Python 3 and its standard library, and what it writes is committed.
Both are on the `start` branch, the script at `Assets/Terrain/make_island.py` and
the PNG in `Assets/Terrain/Island/`, so there is nothing to type here; the
appendix at the end of this chapter says what the file holds and prints its
erosion. It works in four steps:

1. **The shape**, on a coarser grid of 1,024 x 1,024 cells of 32 m: a coastline
   about 10.5 km from the centre, bent in and out by noise, and mountains
   wherever a sum of noise octaves is high, rising toward the middle. This is
   Part 1's terrain with an edge.
2. **Erosion.** Raindrops, a million of them, one at a time. Each starts
   somewhere at random and runs downhill a cell at a step. How much soil it can
   carry grows with how steeply it is falling, how fast it goes, and how much
   water it has left; carrying less than that, it picks soil up, and carrying
   more, it drops some. Where drops gather, they cut valleys, and the valleys
   join, because a valley gathers more drops. A drop that reaches the sea ends
   there, and the sea takes its soil away.
3. **Detail.** The grid is enlarged four times, to 8 m texels, with a smooth
   curve through the coarse heights (Catmull-Rom's, which passes through every
   sample), and small noise is added on land for what the 32 m grid could not
   hold.
4. **The file.** Heights from -200 m to 1,000 m are written as 0 to 65,535, in
   a 16-bit grayscale PNG, with the range in its text notes.

The numbers it was run with are the constants at its top; change them and run
it again for another island:

```python
# The numbers the committed Island.png was made with. Change them and run again for another island.
SIZE          = 4096       # texels per side of the PNG
TEXEL         = 8.0        # metres per texel: the map is SIZE * TEXEL = 32,768 m across
WORK          = 1024       # cells per side of the grid steps 1 and 2 work on: 32 m each
SEED          = 36
ISLAND_RADIUS = 10500.0    # metres from the centre to the coast, on average
PEAK          = 950.0      # metres: the highest point after erosion, under the clouds' 1,500 m
SEA_FLOOR     = -160.0     # metres: the sea floor far from the coast
DROPLETS      = 1000000    # raindrops on erosion's finest grid (step 2), about one per cell; a quarter, and a
                           # sixteenth, of that on the grids 2 and 4 times coarser
HEIGHT_MIN    = -200.0     # metres stored as 0
HEIGHT_MAX    = 1000.0     # metres stored as 65535: steps of 1,200 / 65,535 = 1.8 cm
```

The drop is the heart of it, `erode` in the appendix, from Hans Theobald
Beyer's description (Sources). Heights are divided by the cell's size first,
so a slope is a plain number, the same on any grid. Inertia keeps a little of
the drop's direction, so it runs on across flat ground instead of stopping;
the soil comes from, and goes to, the four cells around the drop, by how close
it is to each. A drop runs at most 64 steps, which on 32 m cells is 2 km:
enough for gullies, too short for the long valleys between mountains. So
`erode_coarse_to_fine` runs the drops first on the grid shrunk four times,
where 64 steps reach 8 km, then twice, then on the 32 m grid itself, each pass
adding what it changed to the full grid.

Running it is optional, because the island it makes is on `start`. To make one,
run `python make_island.py` from `Assets/Terrain/`. It takes about two minutes
on a desktop CPU and up to 2.7 GiB of memory, overwrites `Island/Island.png`
(and, with Chapter 38's additions, the material maps beside it; `git restore`
puts the committed files back), and prints a line saying what it wrote:

```text
size 4096 x 4096 at 8 m (32,768 m), seed 36, work grid 1024, 1000000 droplets; heights -166.0 to 954.4 m, stored -200 to 1000 m
```

That is the committed run's line. Another Python or C library makes a similar
island, not this one: since Python 3.12 `sum()` adds floats with a correction,
and `**` asks the C library's `pow()`, whose last bit differs between Windows
and Linux, and the raindrops grow those last-bit differences into a different
island. So the committed `Island.png` is the reference. Every number in this
chapter and the next ones is measured on it; the script is there to show how it
was made, and to make islands of your own.

The highest point is 954 m, under the clouds' 1,500 m base and the camera's
1,400 m ceiling (Chapter 35 section 7); section 9 puts it where the camera can
reach it. `python make_island.py --quick` writes a small preview instead,
`Island/IslandQuick.png`, in seconds, and leaves `Island.png` alone. Open
`Island/Island.png` in any image viewer: a grey island in a near-black sea,
whiter where it is higher, its ridges branching out from the middle. Section 8
loads that file.

**Where it is kept.** `Island.png` is 17.5 MB, so it is committed in Git LFS,
which keeps large files outside the repository's history: the whole folder
`Assets/Terrain/Island/` is marked for LFS in `.gitattributes`, by folder and
never by extension, so a small PNG anywhere else stays an ordinary file. `start`
has the line already; in a tree of your own it goes at the end of
`.gitattributes`, with any other LFS folders:

```text
Assets/Terrain/Island/** filter=lfs diff=lfs merge=lfs -text
```

The script stays in plain git beside it. A clone made without LFS gets a small
text file where the PNG should be; section 8's loader says so and the demo
carries on with Part 1's noise.

**A heightmap of your own.** Terrain tools such as Gaea and World Machine export
heightmaps as 16-bit grayscale PNGs. Three numbers in `Terrain.cpp` (section 8)
say what the file means: `MAP_SIZE`, its side in metres, which is its texels
times the metres per texel you designed it at; and `HEIGHT_MIN` and
`HEIGHT_MAX`, the heights the tool wrote as 0 and as 65,535. Set them, put the
file in `Assets/Terrain/Island/`, and set `HEIGHTMAP_FILE`. A fourth number,
`MAP_ORIGIN` in `HorizonTypes.h` (section 9), says which point of the map lies
under the world's origin: set it so that the ground within 5 km of the origin is
the ground you want the camera to see. The map must be square. Its edge should
be below sea level, because past the edge the sampler clamps to the edge texels
(section 8), out to the horizon; and keep its peaks under the 1,400 m ceiling,
or the camera cannot reach them, and under the 1,500 m cloud base.

## 8. The heightmap on the GPU

**This is `ImportGrayImage16`, the top of `Terrain.cpp` grown,
`transitionLevels`, the heightmap's constants, `LoadHeightmap`,
`UploadHeightmap`, and their steps in `Initialize`.**

> **Jump:** this section holds several things at once, none of them new on its
> own: a file decoded through the importer (Chapter 15 section 4), with its 16
> bits kept whole instead of cut to 8; a file that may be missing, or an LFS
> pointer in the PNG's place; a mip chain made by blits (Chapter 15 section 5);
> and the barriers around it (Chapter 04 section 5). Keep in mind where it
> ends: an `R16_UNORM` image with every level, ready for a vertex shader to
> sample, and the top level kept on the CPU. Nothing reads either until
> section 9.

### Decoding it

The engine already decodes PNGs: Chapter 15's importer hands the file to
TinyUSDZ's image loader, which uses the `stb_image` library inside it. Two
things stop this chapter from simply calling what is there. The importer cuts
16-bit images to 8 bits (Chapter 15 section 4), which here would turn every
slope into 4.7 m terraces. And `stb_image` itself cannot be called from
outside: TinyUSDZ compiles it with `STB_IMAGE_STATIC`, which makes every
`stbi_` function private to TinyUSDZ's own file. TinyUSDZ's loader does decode
16 bits, though: it calls `stbi_load_16` whenever a file has 16-bit samples, and
says so in the image it returns.

The importer is the only code allowed to include a TinyUSDZ header (Chapter 13
section 5), so the new function goes there, beside `ImportUsdFile`. In
`UsdImport.h`, the image it fills and the function, after `ImportUsdFile`, and
`<cstdint>` and `<vector>` join its includes:

```cpp
// Chapter 36: a grayscale image of 16 bits per texel, such as a heightmap.
struct GrayImage16
{
    uint32_t              width  = 0;
    uint32_t              height = 0;
    std::vector<uint16_t> texels;   // row by row from the top: width * height of them
};

// Chapter 36: decodes a 16-bit grayscale PNG with the stb_image inside TinyUSDZ, as Chapter 15's textures
// are. Fails, leaving `image` empty, when the file is missing, does not decode, or is not 16 bits.
InitializationResult ImportGrayImage16(const std::filesystem::path& file, GrayImage16& image);
```

In `UsdImport.cpp`, at the end of the namespace, it uses the file's own
`toUtf8` (Chapter 13 section 13). For a 4,096 x 4,096 map, `stb_image`'s four
16-bit channels are 128 MB, and TinyUSDZ copies them into the image it
returns, so the program's memory rises by about 190 MB for a moment; the
function keeps one channel, 32 MB:

```cpp
// Chapter 36. TinyUSDZ asks stb_image for four channels whatever the file holds, so a gray texel comes back
// as gray, gray, gray, and opaque: the first of each four is the one to keep.
InitializationResult ImportGrayImage16(const std::filesystem::path& file, GrayImage16& image)
{
    image = {};
    std::ifstream stream(file, std::ios::binary);
    const std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(stream)), std::istreambuf_iterator<char>());
    if (bytes.empty())
    {
        return InitializationResult::failure(std::format("{} not found.", toUtf8(file)));
    }
    auto decoded = tinyusdz::image::LoadImageFromMemory(bytes.data(), bytes.size(), toUtf8(file.filename()));
    if (!decoded)
    {
        return InitializationResult::failure(std::format("{} could not be decoded: {}", toUtf8(file.filename()),
                                                         decoded.error()));
    }
    const tinyusdz::Image& source = decoded.value().image;
    if (source.format != tinyusdz::Image::PixelFormat::UInt || source.bpp != 16 || source.channels < 1)
    {
        return InitializationResult::failure(std::format("{} is not a 16-bit image.", toUtf8(file.filename())));
    }

    image.width  = static_cast<uint32_t>(source.width);
    image.height = static_cast<uint32_t>(source.height);
    image.texels.resize(size_t(image.width) * image.height);
    const uint16_t* wide     = reinterpret_cast<const uint16_t*>(source.data.data());   // native byte order
    const size_t    channels = static_cast<size_t>(source.channels);
    for (size_t i = 0; i < image.texels.size(); ++i)
    {
        image.texels[i] = wide[i * channels];
    }
    return InitializationResult::success();
}
```

### Loading it

The file's name and what its numbers mean are constants at the top of the
namespace in `Terrain.cpp`, below `using namespace vulkan_graphics;`. They are
the script's: a map 32,768 m across, with 0 meaning -200 m and 65,535 meaning
1,000 m:

```cpp
// Section 8: the heightmap Assets/Terrain/make_island.py writes, and what its numbers mean: the map's side in
// metres and the heights stored as 0 and as 65,535. For another map, change these to its own; section 9's
// MAP_ORIGIN says which point of the map the world's origin lies over.
constexpr const char* HEIGHTMAP_FILE = "Island.png";   // in Assets/Terrain/Island/, beside the executable
constexpr float       MAP_SIZE       = 32768.0f;       // metres: 4,096 texels of 8 m
constexpr float       HEIGHT_MIN     = -200.0f;        // metres, stored as 0
constexpr float       HEIGHT_MAX     = 1000.0f;        // metres, stored as 65,535
```

`Terrain.cpp`'s includes grow by what this section and the next use:

```cpp
#include "PillowFort/ErrorReporting/Log.h"
#include "PillowFort/UsdImport/UsdImport.h"
#include "PillowFort/VulkanGraphics/ExecutableFiles.h"
#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"

#include "Horizon/HorizonTypes.h"   // TerrainDraw, shared with the terrain's shaders

#include <algorithm>
#include <bit>
#include <cstring>
#include <filesystem>
#include <format>
#include <utility>
```

`LoadHeightmap` reads the file from beside the executable, where the build
copies `Assets/` (Chapter 13 section 6). A missing file, one that does not
decode, an LFS pointer in its place, or a map that is not square, is reported
as a warning, not an error: the demo is still worth running. In that case the
terrain keeps a one-texel stand-in, because set 1 (section 9) must point at an
image either way, and `m_hasHeightmap` stays false, which section 9 turns into
"draw Part 1's noise". The heights are kept on the CPU, for section 9's copy
of the height. `Setup` runs it every time the demo is entered, and decoding
17.5 MB of PNG takes a few seconds in a Debug build, so a switch away and back
pays it again:

```cpp
// Section 8: the file, decoded by the importer, which is the engine's only door to TinyUSDZ and its
// stb_image. Anything wrong is reported, not fatal: a one-texel stand-in keeps set 1 valid, and the
// shaders fall back to section 3's noise.
void Terrain::LoadHeightmap()
{
    const std::filesystem::path file = executableDirectory() / "Assets" / "Terrain" / "Island" / HEIGHTMAP_FILE;
    usd_import::GrayImage16 image;
    if (auto result = usd_import::ImportGrayImage16(file, image); !result)
    {
        Log::warning(std::format("No heightmap: {} The terrain is noise alone.", result.message()).c_str());
    }
    else if (image.width != image.height)
    {
        Log::warning(std::format("The heightmap is {} x {}, not square; the terrain is noise alone.",
                                 image.width, image.height).c_str());
    }
    else
    {
        m_heights       = std::move(image.texels);
        m_heightmapSize = image.width;
        m_hasHeightmap  = true;
        Log::info(std::format("Heightmap: {} x {} texels of {} m.", m_heightmapSize, m_heightmapSize,
                              MAP_SIZE / static_cast<float>(m_heightmapSize)).c_str());
        return;
    }
    m_heights       = { 0 };
    m_heightmapSize = 1;
    m_hasHeightmap  = false;
}
```

### The image, and its mip levels

On the GPU the heightmap is an `R16_UNORM` image: one channel of 16 bits, read
by the shader as a number from 0 to 1, with Chapter 15 section 5's mip chain
(every texel the average of the 2 x 2 above it: four texels of 1,000, 1,200,
1,400 and 1,600 m become one of 1,300 m). Each level is the same island with
half the detail, which is what section 9's coarse rings read; averaging lowers
the sharpest peaks a little in the far levels, where they are a few pixels
across anyway.

Chapter 15 made the levels with `vkCmdBlitImage`, and the same works here,
with one difference: Vulkan requires every device to sample, filter and blit
Chapter 15's `R8G8B8A8` formats, and not `R16_UNORM`. Lavapipe does all three;
on a device that does not, the program, which asks
(`vkGetPhysicalDeviceFormatProperties`), fails `Setup` with a message rather
than draw garbage. Making the levels on the CPU would avoid the question, at
the cost of the CPU's time in every `Setup`; it is not built here.

Each barrier answers Chapter 04 section 5's three questions, as the comments
say. A barrier over a range of levels is `GpuTexture.cpp`'s `transitionMipLevel`
with a count; it goes at file scope, above the noise functions, as its comment
says:

```cpp
// File scope, above the namespace block. Section 8: Chapter 04's transitionImage for a range of mip levels,
// the way GpuTexture.cpp's transitionMipLevel does it for one.
static void transitionLevels(VkCommandBuffer commandBuffer, VkImage image, uint32_t firstLevel, uint32_t levels,
                             VkImageLayout oldLayout, VkImageLayout newLayout,
                             VkPipelineStageFlags2 srcStage, VkAccessFlags2 srcAccess,
                             VkPipelineStageFlags2 dstStage, VkAccessFlags2 dstAccess)
{
    const VkImageMemoryBarrier2 barrier{
        .sType               = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2,
        .srcStageMask        = srcStage,
        .srcAccessMask       = srcAccess,
        .dstStageMask        = dstStage,
        .dstAccessMask       = dstAccess,
        .oldLayout           = oldLayout,
        .newLayout           = newLayout,
        .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .image               = image,
        .subresourceRange    = { VK_IMAGE_ASPECT_COLOR_BIT, firstLevel, levels, 0, 1 },
    };
    const VkDependencyInfo dependency{
        .sType                   = VK_STRUCTURE_TYPE_DEPENDENCY_INFO,
        .imageMemoryBarrierCount = 1,
        .pImageMemoryBarriers    = &barrier,
    };
    vkCmdPipelineBarrier2(commandBuffer, &dependency);
}
```

```cpp
// Section 8: an R16_UNORM image with every mip level, made on the GPU as Chapter 15's textures are: the top
// level copied in, each level below blitted, at half the size, from the one above.
InitializationResult Terrain::UploadHeightmap()
{
    // R16_UNORM is not one of the formats every Vulkan device must sample, filter, and blit, so ask.
    const VkFormat format = VK_FORMAT_R16_UNORM;
    VkFormatProperties properties{};
    vkGetPhysicalDeviceFormatProperties(m_context.physicalDevice, format, &properties);
    const VkFormatFeatureFlags needed = VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT | VK_FORMAT_FEATURE_SAMPLED_IMAGE_FILTER_LINEAR_BIT
                                      | VK_FORMAT_FEATURE_BLIT_SRC_BIT | VK_FORMAT_FEATURE_BLIT_DST_BIT
                                      | VK_FORMAT_FEATURE_TRANSFER_DST_BIT;
    if ((properties.optimalTilingFeatures & needed) != needed)
    {
        return InitializationResult::failure("This GPU cannot sample, filter, and blit R16_UNORM images.");
    }

    const uint32_t levels = std::bit_width(m_heightmapSize);   // 4,096 down to 1: 13 levels
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = format,
        .extent        = { m_heightmapSize, m_heightmapSize, 1 },
        .mipLevels     = levels,
        .arrayLayers   = 1,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(m_context.allocator, &imageInfo, &allocationInfo, &m_heightmap, &m_heightmapAllocation,
                       nullptr) != VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for the heightmap.");
    }

    const VkDeviceSize size    = m_heights.size() * sizeof(uint16_t);
    AllocatedBuffer    staging = createBuffer(m_context, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, true);
    std::memcpy(staging.mapped, m_heights.data(), static_cast<size_t>(size));
    vmaFlushAllocation(m_context.allocator, staging.allocation, 0, VK_WHOLE_SIZE);   // no-op if coherent

    immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
        // (1) What is written: every level, by the copy or a blit. Who reads it next: nothing yet; the
        //     image is new, so there is nothing to wait for. The layout: from nothing to TRANSFER_DST.
        transitionLevels(commandBuffer, m_heightmap, 0, levels,
                         VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                         VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                         VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);

        const VkBufferImageCopy region{
            .imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 },
            .imageExtent      = { m_heightmapSize, m_heightmapSize, 1 },
        };
        vkCmdCopyBufferToImage(commandBuffer, staging.buffer, m_heightmap, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                               1, &region);

        int32_t side = static_cast<int32_t>(m_heightmapSize);
        for (uint32_t level = 1; level < levels; ++level)
        {
            // (2) What was written: the level above, by the copy or the blit before. Who reads it next: this
            //     blit. The layout: TRANSFER_DST to TRANSFER_SRC.
            transitionLevels(commandBuffer, m_heightmap, level - 1, 1,
                             VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                             VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                             VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);

            // Each texel of the level below is the average of the 2 x 2 above it: a linear filter, exactly
            // halfway between them.
            const int32_t half = std::max(side / 2, 1);
            const VkImageBlit blit{
                .srcSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, level - 1, 0, 1 },
                .srcOffsets     = { { 0, 0, 0 }, { side, side, 1 } },
                .dstSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, level, 0, 1 },
                .dstOffsets     = { { 0, 0, 0 }, { half, half, 1 } },
            };
            vkCmdBlitImage(commandBuffer, m_heightmap, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                           m_heightmap, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &blit, VK_FILTER_LINEAR);
            side = half;
        }

        // (3) What was written: the last level, by the last blit (or, for a one-texel map, by the copy); the
        //     levels above it were read by blits, which wrote nothing to them. Who reads it next: the
        //     terrain's VERTEX shader, sampling, in a later submission. The layouts: every level to
        //     SHADER_READ_ONLY.
        if (levels > 1)
        {
            transitionLevels(commandBuffer, m_heightmap, 0, levels - 1,
                             VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                             VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_NONE,
                             VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
        }
        transitionLevels(commandBuffer, m_heightmap, levels - 1, 1,
                         VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                         VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                         VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    });
    destroyBuffer(m_context, staging);

    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_heightmap,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, levels, 0, 1 },
    };
    if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &m_heightmapView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the heightmap.");
    }

    // Linear within a level and between levels; past the edge, the edge texel, which is sea floor. The shader
    // names its level itself.
    const VkSamplerCreateInfo samplerInfo{
        .sType        = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter    = VK_FILTER_LINEAR,
        .minFilter    = VK_FILTER_LINEAR,
        .mipmapMode   = VK_SAMPLER_MIPMAP_MODE_LINEAR,
        .addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .maxLod       = VK_LOD_CLAMP_NONE,
    };
    if (vkCreateSampler(m_context.device, &samplerInfo, nullptr, &m_heightmapSampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the heightmap.");
    }
    return InitializationResult::success();
}
```

Barrier (3) names the **vertex** shader, not the fragment shader of Chapter 15's
textures, because the rings read the heightmap where they place their vertices.
It is two calls, as its comment says: the levels above the last were only read,
by a blit, so they need an execution dependency, `VK_ACCESS_2_NONE`, before
their layout changes.

`Initialize` gains the two steps, above section 1's `return`:

```cpp
    LoadHeightmap();                                                            // section 8
    if (auto result = UploadHeightmap(); !result)    { return result; }         // section 8
```

and the panel says what was loaded, at the end of `DrawTerrainControls`:

```cpp
    // Section 8: what was loaded.
    const uint32_t size = m_terrain.HeightmapSize();
    if (size > 0) { ImGui::Text("Heightmap  %u x %u", size, size); }
    else          { ImGui::TextUnformatted("Heightmap  none: noise alone"); }
```

Run it: the log has a line `Heightmap: 4096 x 4096 texels of 8 m.`, and the
panel reads **Heightmap 4096 x 4096**. The terrain has not changed: nothing
reads the image yet.

**What sync validation can check here.** Take `VK_ACCESS_2_TRANSFER_WRITE_BIT`
out of barrier (2)'s first half and validation reports a
`SYNC-HAZARD-WRITE-AFTER-WRITE` at the barrier, the Exit check's positive
control. Set barrier (3)'s second half to `VK_PIPELINE_STAGE_2_NONE` and
`VK_ACCESS_2_NONE` and it stays silent, because the reader is a later
submission, after `immediateSubmit`'s fence wait, which sync validation does
not look across: that half rests on the three questions alone.

## 9. Sampling it

**This is set 1, `MAP_ORIGIN`, `mapHeight` and the new `terrainHeight`, the
heightmap in `Record`, `MapHeight` and `HeightAt` on the CPU, and a new
viewpoint.**

### Set 1

The vertex shader reads the heightmap through set 1, which the terrain owns:
one binding, a combined image sampler, written once, because the heightmap
never changes after `Setup`. Chapter 20 section 4's `createDescriptorSets` makes
the layout, a pool counted from it (one combined image sampler, one set) and the
set, and the function writes the binding. `CreateHeightmapSet` goes after
`UploadHeightmap`:

```cpp
// Section 9: set 1, one binding, written once: the heightmap never changes after Setup.
InitializationResult Terrain::CreateHeightmapSet()
{
    const VkDescriptorSetLayoutBinding binding{
        .binding         = 0,
        .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
        .descriptorCount = 1,
        .stageFlags      = VK_SHADER_STAGE_VERTEX_BIT,
    };
    if (!createDescriptorSets(m_context, { &binding, 1 }, m_setLayout, m_pool, { &m_set, 1 }))
    {
        return InitializationResult::failure("Creating the terrain's descriptor set failed.");
    }

    const VkDescriptorImageInfo imageInfo{
        .sampler     = m_heightmapSampler,
        .imageView   = m_heightmapView,
        .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
    };
    const VkWriteDescriptorSet write{
        .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
        .dstSet          = m_set,
        .dstBinding      = 0,
        .descriptorCount = 1,
        .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
        .pImageInfo      = &imageInfo,
    };
    vkUpdateDescriptorSets(m_context.device, 1, &write, 0, nullptr);
    return InitializationResult::success();
}
```

> Chapter 38 renames `CreateHeightmapSet` to `CreateIslandSet`, grows set 1 to
> four bindings visible to the vertex, fragment and compute stages, and widens
> `UploadHeightmap`'s barrier (3) to those stages; a tree past Chapter 38 has
> those versions.

`Initialize` runs it after the upload and before the pipeline, whose layout
needs it:

```cpp
    if (auto result = CreateHeightmapSet(); !result) { return result; }         // section 9
```

and `CreatePipeline`'s layout takes both sets. A new first line, above
`pushRange`, names them:

```cpp
    const std::array<VkDescriptorSetLayout, 2> setLayouts{ frameSetLayout, m_setLayout };
```

and in `layoutInfo`, the count and the pointer, which named set 0 alone,
become

```cpp
        .setLayoutCount         = static_cast<uint32_t>(setLayouts.size()),
        .pSetLayouts            = setLayouts.data(),
```

`Record` binds set 1 after set 0, raises the flag when a heightmap was loaded,
and fills in the push constants' `heightmap`: its side in metres, the height
stored as 0, and the range. Three lines, each in its place in the `Record` you
have from sections 1, 2 and 5:

```cpp
// After the line that raises TERRAIN_SHOW_RINGS:
    if (m_hasHeightmap)     { flags |= TERRAIN_HEIGHTMAP; }     // section 9

// In `draw`, after `.flags     = flags,`:
        .heightmap = { MAP_SIZE, HEIGHT_MIN, HEIGHT_MAX - HEIGHT_MIN, 0.0f },           // section 9

// After the call to `BindFrameSet`:
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_layout, 1, 1, &m_set, 0, nullptr);
```

### Where the world lies over the map

> **Jump:** until now the map and the world have not met. Keep one rule in
> mind: a point of the world, `xz`, is at `xz + MAP_ORIGIN` on the map, in
> metres from the map's middle.

The shader has to say which texel lies under each point of the world. The
obvious answer, the map's middle under the world's origin, is the wrong one
here: the camera may not go further than 5 km from the origin (Chapter 35
section 4), and from the map's middle the nearest sea is 8.75 km away.
Everything the camera could reach would be land, and the sea of section 10
something to look at and never to visit. So the map is moved under the world.
**`MAP_ORIGIN`** is the point of the map, in metres from its middle, that lies
under the origin. The map's columns run along +x and its rows along +z, so in
an image viewer, north up, +x is to the right and +z down. A point of the world
is at `xz + MAP_ORIGIN` on the map, and its texture coordinate is that over the
map's side, plus a half, because the middle is 0.5:

$$
\mathbf{uv} = \frac{xz + \text{MAP\_ORIGIN}}{32{,}768\ \text{m}} + \frac{1}{2}
$$

A worked example, with `MAP_ORIGIN` = (7,300, 400): the origin itself is at
uv = (7,300 / 32,768 + 0.5, 400 / 32,768 + 0.5) = (0.723, 0.512), over seven
tenths of the way across the map and just over half of the way down.

Where on the map? The sea is within 5 km of any point 7.5 km or more from the
island's middle, but the high ground is a mass of ridges in the middle and the
east, and some points on the rim have none of it in reach. So the point was
chosen by measuring, inside the 5 km circle round each candidate, how far the
nearest sea is, how much of the circle is water, and how high the ground gets.
(7,300, 400) is 7.3 km east of the map's middle and 400 m south of it (the
middle is at world (-7,300, -400), off to the camera's left), and on the map's
own 8 m texels it puts the ground under the origin at 122 m, the nearest sea
2.6 km away, 114 degrees to the right of the way the camera starts facing, and
the highest ground on the map, 954 m, inside the circle too, 2.55 km away, 66
degrees to the left.

Both languages need the point, the shader's `mapHeight` and the CPU's
`MapHeight`, so it is written once, in the header they both include, as a
macro: GLSL and C++ spell a constant differently, and a macro is the same text
in both. Its `vec2` is the built-in in GLSL and `glm::vec2` in C++, which the
aliases at the top of the header gain, under `uint`:

```c
    using shared::uint;
    using shared::vec2;
```

and the macro goes below `TerrainDraw`, above the `static_assert`s:

```c
/* Chapter 36 section 9: which point of the heightmap lies under the world origin, in metres from the map's
   middle: +x along the image's columns, +z down its rows. A macro, because GLSL and C++ spell a constant
   differently; `vec2` is glm::vec2 in C++ (the using above). */
#define MAP_ORIGIN vec2(7300.0f, 400.0f)
```

### Which level

> **Jump:** Chapter 15's sampler chose a texture's mip level itself, from how
> fast the texture coordinate changes between neighbouring pixels. A vertex
> shader has no neighbouring pixels, so this shader names the level, with
> `textureLod`, as Chapter 28 section 9's march did; section 3's rule supplies
> the number.

Section 3's rule decides the level. A mip level holds nothing shorter than two
of its texels, so a level whose texels are two of the cells there holds
nothing shorter than four cells: that level is the one at full strength. As the
distance grows, the sampler blends toward the next level down, until its finest
detail would span only two cells and it has gone, exactly as an octave fades.
The level is the `log2` of how many top-level texels fit in that width, as
Chapter 28 section 9 worked its levels out:

$$
\text{level} = \log_2 \frac{2\,c(d)}{t}
$$

with *t* the top level's texel, 8 m, and never below 0. A worked example: at
1 km, $c$ = 32 m, so the level is $\log_2(64/8)$ = 3, whose texels are 64 m.
Near the camera, $2c$ is 1 m, smaller than a texel, and the top level is read,
blended smoothly between its texels by the sampler: the noise's last three
octaves, 8, 4 and 2 m, carry on below it, as section 3's rule allows them.

The texture coordinate is the one just worked out, from `xz + MAP_ORIGIN`. In
`TerrainHeight.glsl`, the binding goes under the include of `Random.glsl`, and
`mapHeight` above `terrainHeight`, which then uses it:

```glsl
// Section 9: the heightmap. R16_UNORM, every mip level, clamped at its edges.
layout(set = 1, binding = 0) uniform sampler2D heightmap;
```

```glsl
// Section 9: the heightmap at xz, from the mip level whose texels are two cells across. A level holds nothing
// shorter than two of its texels, so that is the noise's rule again: four cells to its shortest wavelength,
// fading to two as the sampler blends toward the next level down. The world origin lies over the map point
// MAP_ORIGIN, measured from the map's middle, so xz is at xz + MAP_ORIGIN on the map; past the map's edge the
// sampler clamps to the edge texels, which are sea floor.
float mapHeight(vec2 xz)
{
    float texel = terrain.heightmap.x / float(textureSize(heightmap, 0).x);
    float level = log2(max(2.0 * cellSizeAt(xz) / texel, 1.0));
    vec2  uv    = (xz + MAP_ORIGIN) / terrain.heightmap.x + 0.5;
    float value = textureLod(heightmap, uv, level).r;
    return terrain.heightmap.y + value * terrain.heightmap.z;
}
```

```glsl
// The ground's height at xz. Section 3: thirteen octaves, 8,192 m down to 2 m. Section 9: the heightmap for
// everything its texels can hold, and the last three octaves, 8, 4, and 2 m, for the detail they cannot;
// section 3's octaves alone when there is no heightmap.
float terrainHeight(vec2 xz)
{
    if ((terrain.flags & TERRAIN_HEIGHTMAP) == 0u)
    {
        return noiseOctaves(xz, 8192.0, 13);
    }
    return mapHeight(xz) + noiseOctaves(xz, 8.0, 3);
}
```

### On the CPU

The CPU's copy reads the level the camera stands on, the top one, with the same
bilinear blend the sampler makes. A texel's centre is half a texel in from its
edge, so a point's position in texels is its texture coordinate times the size,
less a half; the four texels around it are blended by how far it is across. A
worked example: on a 4-texel map 32 m across, a point over the map's middle is
at texture coordinate 0.5, position 0.5 x 4 - 0.5 = 1.5 in texels, so halfway
between texels 1 and 2. In two dimensions the blend runs along x in two rows,
then between the rows along z. Take texels (1, 1) = 100 m, (2, 1) = 200 m, (1,
2) = 300 m and (2, 2) = 400 m, and a point at texel position (1.5, 1.25): the
two rows give 150 and 350 m, and a quarter of the way from the first to the
second is mix(150, 350, 0.25) = 200 m. The texture coordinate it starts from is
the shader's, `MAP_ORIGIN` included: one macro feeds both, so the two cannot
drift apart. `MapHeight` goes above `HeightAt`:

```cpp
// Section 9: the shader's mapHeight at level 0, the level under the camera: a bilinear sample of the same
// 16-bit values, with the texel centres where the GPU puts them, half a texel in from each edge.
float Terrain::MapHeight(glm::vec2 xz) const
{
    const int       last  = static_cast<int>(m_heightmapSize) - 1;
    const glm::vec2 texel = ((xz + MAP_ORIGIN) / MAP_SIZE + 0.5f) * static_cast<float>(m_heightmapSize) - 0.5f;
    const glm::vec2 base  = glm::floor(texel);
    const glm::vec2 f     = texel - base;
    auto value = [&](int x, int z) {
        x = std::clamp(x, 0, last);   // CLAMP_TO_EDGE
        z = std::clamp(z, 0, last);
        return static_cast<float>(m_heights[static_cast<size_t>(z) * m_heightmapSize + static_cast<size_t>(x)]) / 65535.0f;
    };
    const int   x = static_cast<int>(base.x);
    const int   z = static_cast<int>(base.y);
    const float v = glm::mix(glm::mix(value(x, z), value(x + 1, z), f.x),
                             glm::mix(value(x, z + 1), value(x + 1, z + 1), f.x), f.y);
    return HEIGHT_MIN + v * (HEIGHT_MAX - HEIGHT_MIN);
}
```

The GPU's sampler does the same sum, but with its blend weights rounded to as
many bits as the device reports in `VkPhysicalDeviceLimits::subTexelPrecisionBits`:
at least 4, and 8 on lavapipe. With 4 bits a weight can be a sixteenth off.
Where the ground rises a metre for every metre across, neighbouring 8 m texels
differ by 8 m, so the GPU and the CPU can disagree by up to 0.5 m there, and by
3 cm with 8 bits. That is inside the camera's 1.5 m; only a slope three times
as steep, at 4 bits, would use it all. `HeightAt` gains the heightmap, as
`terrainHeight` did:

```cpp
// Section 6: terrainHeight on the CPU, for rings centred on ringCenter: the octaves fade by the same cell as
// in the shader. Section 9 adds the heightmap's top level, which is what the rings read near their centre.
float Terrain::HeightAt(glm::vec2 xz, glm::vec2 ringCenter, const TerrainSettings& settings) const
{
    const TerrainPreset& preset = TERRAIN_PRESETS[settings.preset];
    const float          cell   = cellSizeAt(xz, ringCenter, preset.finestCell, static_cast<float>(preset.cells));
    if (!m_hasHeightmap)
    {
        return noiseOctaves(xz, cell, 8192.0f, 13);
    }
    return MapHeight(xz) + noiseOctaves(xz, cell, 8.0f, 3);
}
```

The CPU keeps the top level only, which is what the rings read where their
cells are fine, and under the camera they always are, unless the rings are
frozen and the camera has flown away from them. Then the ground it flies over
is drawn from a coarser level, which the CPU does not have, between vertices
tens of metres apart: a kilometre from frozen rings it can be tens of metres
from `HeightAt` in a steep valley, and the camera can sink into it. **Freeze
rings** is for looking at the rings from above, not for flying low.

### A new viewpoint

Chapter 35's viewpoint is 100 m above the origin, where the island's ground is
at 122 m: the camera would start under it, and the clamp would lift it to
1.5 m above the grass, looking at the next hill. The viewpoint moves up to
1,000 m, above the highest ground, and looks 10 degrees down at the island.
`VIEWPOINT` changes, and a pitch joins it:

```cpp
constexpr glm::vec3 VIEWPOINT{ 0.0f, 1000.0f, 0.0f };   // Chapter 36 section 9: above the island's highest ground
constexpr float     VIEW_PITCH = glm::radians(-10.0f);  // Chapter 36 section 9: looking a little down, at it
```

Both the constructor and `ReturnToViewpoint` turn the camera by it, through
Chapter 10 section 6's `rotationFromYawPitch`. In the constructor, after the
translation:

```cpp
    m_cameraTransform.rotation    = scene::rotationFromYawPitch({ .yaw = 0.0f, .pitch = VIEW_PITCH });   // Chapter 36 section 9
```

and `ReturnToViewpoint` is replaced whole, its comment above it too:

```cpp
// Where the camera starts: Chapter 35 section 2 stands the plates in front of it, and Chapter 36 section 9
// raises it above the island and tips it down.
void HorizonDemo::ReturnToViewpoint()
{
    m_cameraTransform.translation = VIEWPOINT;
    m_cameraTransform.rotation    = scene::rotationFromYawPitch({ .yaw = 0.0f, .pitch = VIEW_PITCH });
}
```

The plates are placed from the viewpoint, so they rise 900 m with it, and
their distances from the camera are unchanged, which keeps Chapter 35's
readout true.

**Flying from here.** The fly controller moves along where the camera looks
(Chapter 10 section 11). With the view 10 degrees down, Shift and W goes forward
and down, about a metre for every six forward, and S goes backward and up; Q and
E still go straight down and up. Mouse-look turns 0.003 radians for every pixel
of drag (Chapter 35 section 1), so about 385 pixels is 66 degrees and about 665
is 114.

Run it: the island, from above its eastern side. The green land rolls away
ahead, cut by valleys, and at the right edge it ends in a grey plain: below
sea level the ground carries on down to the sea floor, pale as sand, and
section 10 floods it. The panel reads **Ground 121.8 m, camera 878.2 m above**.
The highest ground on the map, 954 m, is 66 degrees to your left and about
2.5 km off: hold the right mouse button and drag left about 385 pixels to see
it. It looks lower from here, because the rings are coarse that far out; it
reaches its full 954 m only as you approach.

## 10. The sea

**This is the sea level in the vertex shader, the water in the fragment
shader, and the sky they reflect.**

> **Jump:** four things meet in this section's few lines: the height before
> the sea flattens it, `groundHeight`, blended across each triangle; Chapter
> 29 section 10's Fresnel; Chapter 30 section 10's glint; and the sky's cube,
> read in a reflected direction. Keep them apart by what each answers:
> `groundHeight`, whether a pixel is water and how deep; Fresnel, how much of
> it is mirror; the cube and the glint, what the mirror shows.

### Flat water from the same rings

The sea needs no geometry of its own. Wherever the ground is below 0, the
vertex shader puts the vertex at 0 instead; the rings are then flat over the
sea, and still the same grid, with no edge to join. The fragment shader has to
know which pixels are water, so the vertex shader also hands it the height
*before* flattening, `groundHeight`, which the rasterizer blends across the
triangle like any other output. Where it is below 0, the pixel is water, and
its depth is how far below. A coastline then falls where the blended height
crosses 0, inside a triangle rather than along its edges, so it follows the
ground more closely than the triangles do. It is not quite level: in a
triangle across the coast, the water's vertex is drawn at 0 and the land's at
its height, so the water's edge lies a little up the slope, within that one
cell. Near the camera that is centimetres; far out, the cells are large and
the haze of section 11 is over it. The vertex shader's outputs gain
`groundHeight`, under `vertexNormal`'s:

```glsl
layout(location = 2) out float groundHeight;    // section 10: the ground's height before the sea flattened it
```

and `main` flattens the sea after the normal, above the `worldPosition` line
(section 3):

```glsl
    // Section 10: ground below sea level is drawn at sea level, as water; the fragment shader tells which is
    // which from the height before flattening.
    groundHeight = height;
    float drawn  = max(height, 0.0);
```

Then that `worldPosition` line, which section 3 had you leave where it stands, is
changed to draw the vertex at `drawn`, not at `height`:

```glsl
    worldPosition = vec3(xz.x, drawn, xz.y);
```

Forget this and nothing fails: the ground stays under the sea, and only its
colour says where the water is.

### What water looks like

Calm water is a mirror for the sky, more of a mirror the more grazing the
view: Schlick's Fresnel, from 2% looking straight down to all of it at the
horizon (Chapter 29 section 10). It shows the sun as a glint, Chapter 30
section 10's lobe, scaled so it adds up to the sun's irradiance. Under the
mirror is the water's own colour, light that went in and came back: nearly
black where it is deep, and where it is shallow, the sand below, which is
`groundAlbedo`'s at the waterline. The sand fades by `exp(-depth / 3)`, the
same share of it lost for every metre of water, as light in Chapter 28 section
2's fog: 37% of it is left under 3 m, 5% under 9 m.

The sky it mirrors is the engine's, when it is on: set 0 binding 11, the
specular cube Chapter 24 filters a level per roughness, whose level 0 is the
sky itself, without the sun's disk. A reflection that points below the horizon
is lifted to it, as Chapter 30 section 10's sea does: on open water it would
find more water, about as bright as the horizon. With the sky off, the cube was
never baked and holds nothing worth reading, so the water reflects the demo's
clear colour instead; the push constants carry it, and `skyOn` raises the flag
that says which. The colour is a constant above `Initialize`:

```cpp
// Section 10: what the sky is with the engine's sky off: the demo's clear color (Chapter 35 section 1), so
// the haze fades far ground into the background.
constexpr glm::vec3 FALLBACK_SKY{ 0.45f, 0.60f, 0.80f };
```

and `Record` puts it in `.sky`, under `.heightmap`, with a 0 where section 11
puts the haze:

```cpp
        .sky       = glm::vec4(FALLBACK_SKY, 0.0f),                                     // section 10; w: section 11
```

In the fragment shader, the sky's cube is binding 11, under binding 10; the new
input goes under `vertexNormal`'s; `PI` and the glint's power go under
`outColor`'s declaration; and the two functions go above `main`:

```glsl
layout(set = 0, binding = 11) uniform samplerCube skySpecular;   // section 10: level 0 is the sky itself
layout(location = 2) in float groundHeight;
const float PI          = 3.14159265;
const float GLINT_POWER = 800.0;   // section 10: how tight the sun's glint is (Chapter 29's)
```

```glsl
// Section 10: the sky in a direction, lifted to the horizon if it points below it (on the open sea, that is
// more sea, about as bright as the horizon). With the engine's sky off, the demo's clear color.
vec3 skyColor(vec3 direction)
{
    if ((terrain.flags & TERRAIN_SKY) == 0u)
    {
        return terrain.sky.rgb;
    }
    direction = normalize(vec3(direction.x, max(direction.y, 0.0), direction.z));
    return textureLod(skySpecular, direction, 0.0).rgb;
}
```

```glsl
// Section 10: water `depth` metres deep, seen along V (unit, toward the eye): the sky mirrored with Schlick's
// Fresnel, and the sun's glint (Chapter 30 section 10's lobe), over the water's body, which shows the sand
// below where it is shallow.
vec3 waterColor(float depth, vec3 V)
{
    const vec3 N    = vec3(0.0, 1.0, 0.0);
    const vec3 DEEP = vec3(0.01, 0.04, 0.06);   // linear: what deep water gives back
    vec3  towardSun = -frame.sunDirection.xyz;
    vec3  R         = reflect(-V, N);
    float facing    = clamp(V.y, 0.0, 1.0);
    float fresnel   = 0.02 + 0.98 * pow(1.0 - facing, 5.0);
    float lobe      = (GLINT_POWER + 1.0) / (2.0 * PI) * pow(max(dot(R, towardSun), 0.0), GLINT_POWER);
    vec3  mirror    = skyColor(R) + PI * frame.sunColor.rgb * lobe;   // the sun's irradiance, E

    vec3 light = lightAt(N);
    vec3 sand  = groundAlbedo(0.0, 1.0);                       // the sea floor at the waterline
    vec3 body  = mix(DEEP, sand, exp(-depth / 3.0)) * light;   // the floor fades out over a few metres
    return mix(body, mirror, fresnel);
}
```

`main`'s start is rewritten: it replaces section 4's three lines (the comment,
`N` and `color`) with the direction to the eye, which the water needs, and a
choice of water or ground. The ground's albedo now takes `groundHeight`, which
is the same as the position's height on land. The debug views below stay as
they were:

```glsl
    vec3  toEye = frame.cameraPosition.xyz - worldPosition;
    float range = length(toEye);
    vec3  V     = toEye / range;

    // Section 4: the ground, lit. Section 10: or water, where the ground is below sea level.
    vec3 color;
    if (groundHeight < 0.0)
    {
        color = waterColor(-groundHeight, V);
    }
    else
    {
        vec3 N = normalize(vertexNormal);
        color  = groundAlbedo(groundHeight, N.y) * lightAt(N);
    }
```

## Checkpoint

Run with `--demo Horizon`. The island lies below, and the sea all round it,
out to where the rings end. The nearest coast is 2.6 km away, 114 degrees to
the right: hold the right mouse button and drag right about 665 pixels, in
two drags, and the shore is ahead and below, a pale line of sand. Hold Shift
and W, which goes forward and a little down: at 200 m/s the coast passes under
you after about 13 seconds, when the panel's **From the origin** reads about
2,600 m. Let go after 5 to 8 seconds, with it between 1,000 and 1,600 m, to
see the coast from above: the sand, the shallows where it fades into the
water, and the sea beyond, dark and mirroring the sky. Fly on out over the sea,
then climb to the ceiling with Shift and E and look out. Turn the sky off in
the Tone mapping window: the water mirrors the pale clear colour instead.
Above the far sea, where the rings end, the sky's plain ground shows between
the sea and the horizon, a band about 13 pixels thick at the ceiling: Part 3
deals with it.

---

# Part 3 — To the horizon (section 11)

Far mountains are as sharp and as dark as near ones, and past the last ring the
sky's ground shows under the horizon: two small additions fix both.

## 11. Haze and the skirt

**This is the haze in the fragment shader, its distance in the push constants
and its slider, and the skirt at the end of the vertex shader.**

### Haze

Air is not quite clear: over a long way, whatever is far off fades toward the
colour of the sky behind it. The sea of Chapters 29 and 30 fades the same way,
and the rule is Chapter 28 section 2's: the same share of a surface's own light
is lost for every metre, so the share left after *r* metres is $e^{-r/h}$,
where *h*, the **haze distance**, is the 1/σ of that section. A worked example,
with *h* = 20 km: a mountain 5 km away keeps $e^{-0.25}$ = 78% of its own
colour, one 20 km away 37%, and the last ring, 65 km out, 4%. The sea's haze
distance was 900 m, for a view that ended at 5 km; this view reaches 65 km, so
it is tens of kilometres.

The colour it fades to is the sky's straight behind the surface, as Chapter 30
section 10's sea fades: `skyColor` in the direction from the eye, which
section 10 wrote for the water, lifted to the horizon when it points below it.
So far ground fades into the sky exactly where it meets it, and the seams the
rings could leave far off, where the detail fades, are under the haze. With
the sky off, the haze fades to the clear colour, which is the background then.
One caution: the sky's light cube holds the sky alone, not Chapter 28's clouds,
so a far ridge under a cloud fades to blue sky.

In `main`, after the ground or the water, and before the debug views, so that
the ring colours and the cell lines stay unhazed and can be told apart all the
way to the horizon:

```glsl
    // Section 11: haze. Far ground fades into the sky behind it: the fraction left after `range` metres
    // is exp(-range / hazeDistance), as Chapter 30's sea fades (its section 10), at tens of kilometres. The
    // debug views below come after it, so their colors reach the horizon unhazed.
    color = mix(color, skyColor(-V), 1.0 - exp(-range / terrain.sky.w));
```

The haze distance is the panel's, in `TerrainSettings`, and goes in the `w` of
the push constants' `.sky`, in `Record`, in place of section 10's 0:

```cpp
        .sky       = glm::vec4(FALLBACK_SKY, settings.hazeDistance),                    // sections 10, 11
```

and its slider, at the end of `DrawTerrainControls`, on a logarithmic scale
from 2 km to 100 km, since the useful values span fifty times:

```cpp
    // Section 11: how far the air lets you see.
    ImGui::SliderFloat("Haze (m)", &m_terrainSettings.hazeDistance, 2000.0f, 100000.0f, "%.0f",
                       ImGuiSliderFlags_Logarithmic);
```

Run it: the far ground goes paler and bluer into the sky. Turn toward the
highest ground (drag left about 385 pixels) and drag the **Haze** slider to its
left end, 2 km: the summit, about 2.5 km off, is a faint shape, and everything
past it is gone. Up at 100 km, the far land stands out as hard as the near,
which is what makes it look near.

### The skirt

The rings end 65 km out. Look toward the horizon from 1,400 m and there is a
thin band between the end of the sea and the horizon line: the sky's plain
ground, below the horizon (Chapter 23 section 6). The rings' edge is below the
horizon by the angle whose tangent is the camera's height over 65 km, about
1.2 degrees: with the camera's 60-degree field of view, about 13 pixels at 720
lines and 27 at 1440.

Chapter 30 section 9 closed the same gap at the edge of its sea with a
**skirt**, and this one is the same, further out: the last ring's outer
vertices go out to 150 km, inside the 200 km far plane, and up to the camera's
height. A point at the eye's height lies on the horizon whatever its distance,
so the last row of triangles reaches from the end of the rings to the horizon,
from any height:

```text
  Seen from the side (not to scale):

  eye  o . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . *  150 km out, at the eye's height
                                                     _ _ _ - - - '        (on the horizon)
  sea  ==================================== * - - - '                     the skirt: one row of long triangles
                                         65 km, where the rings end
```

The vertices are pulled straight away from the rings' centre, so the skirt's
edge is a circle round the camera, not a square. Its normal points up, and its
`groundHeight` is the height of the point it was moved from, 65 km out and past
the map's edge, which is sea floor: it is shaded as water, and is all haze by
then, the colour of the sky at the horizon. The distance is a constant above
`ringCell`:

```glsl
// Section 11: how far out the skirt pulls the last ring's outer edge, in metres: past the 65 km the rings
// reach, inside the 200 km far plane.
const float SKIRT_DISTANCE = 150000.0;
```

and the skirt goes after section 10's `drawn`, above the `worldPosition` line:
only the last ring's outer edge, `onXEdge` and `onZEdge` from section 5:

```glsl
    // Section 11: the skirt. The last ring's outer edge goes out to SKIRT_DISTANCE and up to the camera's
    // height, which from any height is on the horizon: no edge to the world, and none of the sky's ground
    // below it (Chapter 30 section 9's skirt, further out).
    if (ring == terrain.ringCount - 1u && (onXEdge || onZEdge))
    {
        xz           = terrain.rings.xz + normalize(xz - terrain.rings.xz) * SKIRT_DISTANCE;
        drawn        = frame.cameraPosition.y;
        vertexNormal = vec3(0.0, 1.0, 0.0);
    }
```

Run it, fly out over the sea as section 10's checkpoint did, climb to the
ceiling and look out to sea: the water meets the sky at the horizon, with
nothing between.

## Checkpoint

This is the finished chapter; the Exit check below walks through it. The frame
is Chapter 35 section 7's, with these lines changed or added:

```text
 FrameData: the camera, and the sun and ambient light (section 4)      WriteFrameData
     the terrain: twelve rings, one draw, GREATER (sections 1-5, 9-11) Terrain::Record
     the plates, if the panel shows them (section 1): flat, GREATER    RecordBatches
```

And the vertex shader's `main`, top to bottom, with the section that wrote each
part. The order is the point: a line that lands below the `worldPosition` line
changes a variable nothing draws:

```text
 which cell, which corner of it                              section 1
 the seals' vertices                                         section 5
 the ring, its cell and corner; the collapse                 section 2
 lattice, xz, and float height                               sections 1, 3
 the odd vertices on the outer edge, averaged                section 5
 the normal, from four heights a cell apart                  section 4
 groundHeight, and drawn: the sea at sea level               section 10
 the last ring's outer edge pulled out: the skirt            section 11
 worldPosition (from drawn), cellPosition, gl_Position       sections 1, 3, 10
```

---

## If something goes wrong

| Symptom | Cause |
| --- | --- |
| The rings flicker in their middles, two colours fighting | The collapse is missing or wrong: the inner ring's cells are drawn twice (section 2) |
| Dark or magenta specks along the borders between rings | The cracks: the outer edge's odd vertices are not on the coarse ring's edge (section 5), or the averaging was written below the `worldPosition` line and changes nothing that is drawn (section 3) |
| A stray pixel of the background now and then, in a different place as you fly | The pinholes: the seals are missing, `Record` does not draw their `6 * preset.cells` vertices, or the pipeline still culls back faces and drops a seal that faces away (section 5) |
| The far ridges crawl and sparkle as you fly | The octaves or the heightmap's level are sharper than section 3's rule allows: check the 2 and 4 in `noiseOctaves`, and the 2 in `mapHeight` |
| Shading seams along ring borders | The normal's step is the ring's cell instead of `cellSizeAt` (section 4) |
| Everything is pitch black, or one flat green | `FrameData`'s sun and ambient light were not written (section 4) |
| You can fly into the hills | `KeepCameraInBounds` lost section 6's lines, or `HeightAt` and `terrainHeight` disagree: the CPU's copy must match the shader line for line, `MAP_ORIGIN` included (section 9) |
| Land in every direction within 5 km, and the sea out of reach | `MAP_ORIGIN` is still (0, 0), or `mapHeight` and `MapHeight` do not both add it (section 9) |
| "No heightmap" in the log, and the terrain is noise | The file is missing from `Assets/Terrain/Island/` beside the executable, or it is a Git LFS pointer: `git lfs pull`, then build so `Assets/` is copied again (section 8) |
| `Setup` fails: "This GPU cannot sample, filter, and blit R16_UNORM images" | The device lacks an optional format feature (section 8). Making the mip levels on the CPU is the way round it, at the cost section 8 gives; it is not built here |
| Terraces 4.7 m tall on every slope | The heightmap was cut to 8 bits on the way: it must be read through `ImportGrayImage16`, into `R16_UNORM` (section 8) |
| The island is the wrong size, or too tall, or sunk | `MAP_SIZE`, `HEIGHT_MIN` or `HEIGHT_MAX` do not match the file (section 7) |
| The ground is under the water, and only its colour says where the sea is | `worldPosition` still draws `height`: it must draw `drawn` (section 10) |
| A band of brown under the horizon, far out | The skirt is missing (section 11) |
| The far mountains are as dark as the near ones | The haze is missing, or its distance is far too long (section 11) |

## Exit check

Run the finished demo, with the sky on unless a line says otherwise. The rings,
the coast and the sea, the haze and the skirt were checked where they were
built, and the hygiene every exit check assumes is [the index's
conventions](../VulkanTutorial.md#conventions-every-chapter-uses). This list is
what those runs did not check.

- [ ] **No cracks.** Set the clear colour in `HorizonDemo::Record` to magenta,
      `{ 1.0f, 0.0f, 1.0f, 1.0f }`, build, and run with the sky **Off**. Take
      a full-size screenshot toward the coast (**Back to the viewpoint**, then
      a drag right of about 665 pixels, in two drags) and another toward the
      summit (**Back to the viewpoint**, then a drag left of about 385 pixels).
      Count the magenta pixels below the horizon in each with section 5's
      script, giving it the horizon's row (250 in a 1280 x 720 window, in both):
      zero, in both.
- [ ] **The control for the culling.** In `CreatePipeline`, put
      `VK_CULL_MODE_BACK_BIT` back, leave the clear colour magenta, build, and
      count again from the same two views. On lavapipe about ten pixels come
      back toward the coast, and one or none toward the summit. Another GPU may
      leave others, or none; the point is that with culling on, zero is no
      longer certain. Put `VK_CULL_MODE_NONE` and the colour back.
- [ ] **The ground, over the island.** From **Back to the viewpoint**, turn
      toward the highest summit and fly into it with Shift and W, diving with
      Q: the camera stops 1.5 m above the ground, as the panel says, and rides
      over it. Part 1's checkpoint did this over the noise; here the CPU's copy
      of the heightmap is what stops it.
- [ ] **No heightmap.** Rename `Island.png` beside the executable and run: the
      log has a warning beginning "No heightmap", the panel reads **Heightmap
      none: noise alone**, and the demo runs with Part 1's hills, a sea in
      their valleys. Name it back.
- [ ] **The positive control.** In `UploadHeightmap`, in barrier (2), change
      `VK_ACCESS_2_TRANSFER_WRITE_BIT` in the first half to `VK_ACCESS_2_NONE`,
      build, and run a few frames. Validation reports
      `SYNC-HAZARD-WRITE-AFTER-WRITE` at `vkCmdPipelineBarrier2`: "performs image
      layout transition on the VkImage ..., which was previously written by
      vkCmdCopyBufferToImage", and again for each blit. Put it back.

---

## Where to go from here

Chapter 37 stands objects on this ground; they ask `Terrain::HeightAt` where it
is.

What this chapter did not build, and when it becomes worth building:

- **Tiles and streaming**, when the authored world outgrows memory (Chapter 35's
  list says what it takes). This heightmap is 32 MB, 43 MB with its levels; 8 m
  texels over 33 km are coarse, and near the camera the noise makes up the
  difference. The same world at 1 m over 100 km would be 20 GB: tiles, loaded
  around the camera as it moves, each into its place in the rings' image, as
  *The Witcher 3* streams them into its clipmap's levels (Gollent).
- **A morph band**, if a ring's hand-over shows as a pop on a real display:
  near a ring's outer edge, each vertex blends toward where the coarse ring
  would put it, so nothing changes at the switch (Losasso and Hoppe; Asirvatham
  and Hoppe).
- **Culling again**, if Chapter 37's timers show the rasterizer paying for the
  triangles that face away (section 5 gave culling up so that the seals could
  be drawn once). Make the terrain pipeline's cull mode dynamic, as Chapter 35
  section 3's flat pipeline does, and draw twice: the grid, with
  `vkCmdSetCullMode(VK_CULL_MODE_BACK_BIT)` before it, and then the seals,
  `6 * cells` vertices starting at vertex `6 * cells * cells`, with
  `VK_CULL_MODE_NONE`.
- **Indexed rings**, if the ring pass is too slow on a slower GPU. Each vertex
  here is computed six times, once per triangle that uses it; an index buffer,
  the same for every ring, lets the GPU reuse a vertex it has just computed,
  up to six times fewer vertex shader runs, less what its cache of recent
  vertices misses. Chapter 37's GPU timers say whether it is needed.
- **Earth's curvature**, when the horizon looks too flat from a peak. The
  ground drops below a flat plane by $d^2 / 2R$, about 70 m at 30 km: one line
  in the vertex shader, and the skirt's height with it.
- **Swapping in an authored export**: section 7 says which three numbers to
  change.

---

## Sources

- Frank Losasso and Hugues Hoppe, *Geometry Clipmaps: Terrain Rendering Using
  Nested Regular Grids*, SIGGRAPH 2004. The nested rings, each twice the size,
  following the viewer, and the band at each ring's edge that blends toward
  the coarser ring.
- Arul Asirvatham and Hugues Hoppe, *Terrain Rendering Using GPU-Based
  Geometry Clipmaps*, GPU Gems 2, chapter 2, 2005. The same rings, with the
  work moved to the GPU.
- Marcin Gollent, *Landscape Creation and Rendering in REDengine 3*, GDC 2014.
  *The Witcher 3*'s terrain as a geometry clipmap, with tiles streamed into its
  levels.
- Hans Theobald Beyer, *Implementation of a method for hydraulic erosion*,
  bachelor's thesis, Technische Universität München, 2015. The raindrop
  erosion in `make_island.py`.
- Christophe Schlick, *An Inexpensive BRDF Model for Physically-based
  Rendering*, 1994 (Chapter 29's source): the Fresnel term.
- The Vulkan specification, "Required Format Support": which formats every
  device must sample, filter and blit, and that `R16_UNORM` is not among them;
  and `VkPhysicalDeviceLimits::subTexelPrecisionBits`, whose minimum is 4.

---

## Appendix — `make_island.py`

Reference for section 7: the script that writes the heightmap. It is on the
`start` branch at `Assets/Terrain/make_island.py` (489 lines, plain Python 3
with the standard library only), beside the PNG it writes. The file there is the
finished one: Chapter 38 grows it (the raindrops' footprints, and step 2b, the
material map, written beside the island), and the island it makes is the same,
byte for byte. To make an island again, run `python make_island.py` from
`Assets/Terrain/`; section 7 says what a run costs and why it makes a similar
island, not the committed one. What it makes:

| File | Made by | What it is |
| --- | --- | --- |
| `Island/Island.png` | `python make_island.py` | the heightmap: 4,096 x 4,096 texels of 16 bits at 8 m, heights -200 to 1,000 m stored as 0 to 65,535 with the range in the file's text chunks; 17.5 MB, in Git LFS; the reference |
| `Island/IslandQuick.png` | `--quick` | a 1,024 x 1,024 preview of 32 m texels, from a sixteenth of the raindrops, with 256 x 256 material maps beside it, also named `*Quick.png`; seconds |
| `Island/IslandMaterials0.png`, `IslandMaterials1.png` | the same run, from Chapter 38 | the material map: six weights of what the ground is made of, three to a file; Chapter 38 section 1 |

And what the file holds, in its order:

| Step | Functions | What they do |
| --- | --- | --- |
| 1 | `catmull_rom`, `enlarge_line`, `enlarge`, `value_noise` | Catmull-Rom's smooth curve through every sample, used to make value noise from a coarse random lattice and, in step 3, to enlarge a grid |
| 1 | `smoothstep`, `make_shape` | the 1,024 x 1,024 grid of 32 m: a coastline bent by noise, and mountains where a sum of noise octaves is high, taller toward the middle |
| 2 | `erode` | one raindrop at a time; below |
| 2 | `soften`, `shrink`, `erode_coarse_to_fine` | a 3 x 3 blur; a grid made smaller; the drops run first on a grid four times coarser, then two, then the grid itself, each pass adding what it changed |
| 2b | `box_blur`, `slope_grid`, `make_materials`, `write_png_rgb`, `sha256` | Chapter 38's material map, and a fingerprint of each file written; Chapter 38's appendix |
| 3, 4 | `png_chunk`, `write_png`, `main` | the highest point scaled to `PEAK`; the grid enlarged four times with detail noise added on land; heights stored as 0 to 65,535 in a 16-bit grayscale PNG |

`erode` is the part section 7 teaches. It is the file's, as this chapter needs
it; the file also has a few lines marked `# Chapter 38` that record where each
drop stepped and dropped soil. They draw nothing from the random generator and
change none of the heights:

```python
# Raindrops, one at a time (Hans Theobald Beyer, "Implementation of a method for hydraulic erosion", 2015).
# Each starts somewhere at random with a little water and no soil, and steps one cell at a time downhill,
# keeping some of its direction (inertia). How much soil it can carry grows with how steeply it is falling,
# how fast it moves, and how much water it has left. Carrying less than that, it picks soil up; carrying
# more, or going uphill, it drops some. The soil comes from, and goes to, the four cells around it.
def erode(heights, work, droplets, rng):
    cell = SIZE * TEXEL / work   # metres per cell of this grid
    w = work
    h = array.array("d", (v / cell for row in heights for v in row))   # heights in cells: slopes are plain numbers
    INERTIA, CAPACITY, MIN_SLOPE = 0.1, 4.0, 0.01
    DEPOSIT, ERODE, EVAPORATE, GRAVITY, STEPS = 0.02, 0.15, 0.02, 4.0, 64
    sqrt = math.sqrt
    random01 = rng.random
    for _ in range(droplets):
        x = 1.0 + random01() * (w - 3)
        y = 1.0 + random01() * (w - 3)
        dx = dy = 0.0
        speed, water, soil = 1.0, 1.0, 0.0
        for _ in range(STEPS):
            ix, iy = int(x), int(y)
            fx, fy = x - ix, y - iy
            i = iy * w + ix
            h00, h10, h01, h11 = h[i], h[i + 1], h[i + w], h[i + w + 1]
            gx = (h10 - h00) * (1.0 - fy) + (h11 - h01) * fy
            gy = (h01 - h00) * (1.0 - fx) + (h11 - h10) * fx
            here = h00 + (h10 - h00) * fx + (h01 - h00) * fy + (h00 - h10 - h01 + h11) * fx * fy
            dx = dx * INERTIA - gx * (1.0 - INERTIA)
            dy = dy * INERTIA - gy * (1.0 - INERTIA)
            length = sqrt(dx * dx + dy * dy)
            if length < 1e-9:
                break
            dx /= length
            dy /= length
            x += dx
            y += dy
            if x < 1.0 or y < 1.0 or x >= w - 2 or y >= w - 2:
                break
            jx, jy = int(x), int(y)
            gx2, gy2 = x - jx, y - jy
            k = jy * w + jx
            a, b, c, d = h[k], h[k + 1], h[k + w], h[k + w + 1]
            there = a + (b - a) * gx2 + (c - a) * gy2 + (a - b - c + d) * gx2 * gy2
            if there < 0.0:
                break   # into the sea, which carries its soil away: the coast keeps its shape
            drop = there - here   # negative going downhill
            capacity = max(-drop, MIN_SLOPE) * speed * water * CAPACITY
            if soil > capacity or drop > 0.0:
                amount = min(drop, soil) if drop > 0.0 else (soil - capacity) * DEPOSIT
                soil -= amount
            else:
                amount = -min((capacity - soil) * ERODE, -drop)
                soil -= amount
            # amount > 0 deposits, < 0 erodes; shared by the four cells the drop was among.
            h[i] += amount * (1.0 - fx) * (1.0 - fy)
            h[i + 1] += amount * fx * (1.0 - fy)
            h[i + w] += amount * (1.0 - fx) * fy
            h[i + w + 1] += amount * fx * fy
            speed = sqrt(max(speed * speed - drop * GRAVITY, 0.0))
            water *= 1.0 - EVAPORATE
    return [[h[j * w + i] * cell for i in range(w)] for j in range(w)]
```

Next: [37 — Objects at a Distance](37-Objects-At-A-Distance.md)
