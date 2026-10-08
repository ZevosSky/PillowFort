# 28 — Clouds

**Goal:** clouds in the sky of every demo that shows one: a few fair-weather
cumulus, a sky of scattered heaps, or a grey overcast with a break in it. They
are lit by the sun, with the bright silver edge you see when you look toward it.
They drift with the wind and change shape as they go. They are not pictures of
clouds. They are a block of air with a density at every point, and a march
through it adds up how much light reaches your eye. The chapter builds that
from the physics up: how much light gets through a fog, which way a droplet
scatters it, and how to approximate light that has bounced many times. Then it
builds the shape, from noise generated once into 3D images.

**ROADMAP:** step 21+. The clouds are engine code, not a demo: they belong to
Chapter 23's sky, so every demo that shows the sky shows them too.

**Module:** `Source/PillowFort/VulkanGraphics/`, namespace `pf::vulkan_graphics`:
- **New:** `Clouds.h/.cpp` and `CloudSettings.h/.cpp`. The clouds time
  themselves with Chapter 24's `GpuTimestamps` (section 14).
- **Chapter 23's code grows:** `Sky` gains a `Clouds` member, `SkySettings`
  gains `clouds`, and `SkyInputs` gains `cameraPosition` and `time`.
- **Shaders:** `Shaders/Include/CloudTypes.h`, shared by C++ and GLSL, and in
  `Shaders/Clouds/`:
  - `CloudNoise.glsl`;
  - `CloudShapeNoise.comp.glsl`, `CloudDetailNoise.comp.glsl`, and
    `CloudWeather.comp.glsl`, which make the noise;
  - `CloudMarch.comp.glsl`, which marches;
  - `Clouds.frag.glsl`, which draws.

**Math:**
- **Taught here:**
  - density and extinction (section 2);
  - transmittance, and the Beer-Lambert law (2);
  - a march as a sum, and the exact light of one step (3);
  - where a ray meets a horizontal plane (3);
  - the phase function of Henyey and Greenstein (6);
  - Worley noise in three dimensions, noise that tiles, and Perlin-Worley
    (7);
  - what a 3D image and its mips cost in memory (7);
  - a linear remap (9);
  - a mip level from distance, without derivatives (9);
  - light that scattered many times, as octaves (11);
  - a running average, and how far it lags (13).
- **Assumed:** `e^x` and `log2` as buttons on a calculator. Section 2 says in
  words what `e^-x` does.
- **Used from earlier chapters:**
  - radiance and irradiance (Chapter 15 section 9);
  - solid angle, and the sun's irradiance in the scene's units (16 §2);
  - `smoothstep` (16 §5);
  - exposure (16 §6);
  - mip levels and `log2` (15 §5);
  - even directions on a sphere (21 §3);
  - premultiplied alpha (21 §5);
  - Voronoi cells and gradient noise (27 §1-2).

**Prerequisites:**

- Chapter 23, all of it:
  - section 1, `Sky.vert`'s un-projected view direction;
  - section 2, a cube image's six faces and `cubeTexelDirection`;
  - section 3, the cube, and its one view, which is a `samplerCube` to one
    shader and an `imageCube` to another;
  - section 6, the sun's disk, drawn in `Sky::Draw` rather than baked;
  - section 7, `Update` and `Draw`: the barriers around the bake, the promise
    that the cube can be sampled by compute after `Update`, and the draw at
    depth 1.0;
  - section 8, `SkySettings` and its panel;
  - section 10, `DrawInOwnPass`, for Chapter 22's deferred path.
- Chapter 20:
  - sections 2 and 3, `createComputePipeline`, `groupCount`, and the bounds
    guard;
  - section 4, storage images, their format qualifiers, and `GENERAL`;
  - section 5, `memoryBarrier`, and the table of what synchronization
    validation can see;
  - section 10, the return trip from a fragment shader back to compute.
- Chapter 21:
  - section 3, `seedRandom`, `randomFloat`, and directions spread evenly
    over a sphere;
  - section 5, premultiplied alpha;
  - section 8, timing passes with timestamps.
- Chapter 24 section 9, `GpuTimestamps`: Chapter 21 section 8's queries, made
  a class.
- Chapter 27 sections 1 (Voronoi cells, one jittered point per cell) and 2
  (gradient noise, octaves, and noise that slides with the wind). If you
  skipped the grass, read 27 §1's Voronoi Jump box and 27 §2's gradient-noise
  Jump box and worked example; you do not need to build the grass.
- Chapter 15:
  - section 5, mip chains, how a sampler picks a level, and building a chain
    by blitting;
  - section 9, radiance and irradiance.
- Chapter 16:
  - section 2, light units, and a distant light's irradiance;
  - section 5, `smoothstep`;
  - section 6, exposure and the tone curve. Read this chapter's numbers with
    the curve on Raw and 0 stops.
- Chapter 04 section 5, the three questions, and its appendix, which this
  chapter adds rows to.

---

## Where this is going

A cloud is a region of air full of water droplets. It has no surface. Light
enters it, bounces from droplet to droplet, and comes out somewhere else: a
little of it straight toward you, most of it in other directions. What you see
when you look at a cloud is the sum of all the light that a line of sight
through it collects on the way. So that is what the shader computes. For each
direction it walks along the line in steps, asks at each step how dense the
cloud is there and how much sunlight reaches that point, and adds up what comes
toward the eye.

```text
                                         sun
      ______________________________ 4000 m  \    top of the cloud layer
             .--~~~--.        .-~~-.          \
          .-(  dense  )-.    (      )          \   at each step along a ray:
         (    marched    )    '-..-'            \   - how dense is it here?
      ____'-.__________.-'_________ 1500 m       \  - how much sun gets in?
                \   |   /                           - how much of that leaves
                 \  |  /   one ray per texel           toward the eye?
                  \ | /    of a cube face
                   eye
```

When you have finished, a demo with Chapter 23's sky switched on draws a sky
like the ones in this chapter's exit check:

- **"Scattered"**, the default: heaps of cumulus a few hundred metres to a
  couple of kilometres across, with white tops and grey undersides, thinning
  into the haze at the horizon.
- **"Clear"**: a few fair-weather clouds, most of them small.
- **"Overcast"**: a flat grey lid with a break of blue in it.

Turn the sun low and toward the camera, and the clouds in front of it are
darker in their middles and bright at their thin edges: the silver lining. Leave the
program running and they drift downwind and change at their edges.

### Where the clouds are drawn, in one paragraph

Chapter 23's sky is a cube image of radiance, and its draw puts that cube
behind everything at depth 1.0. The clouds are a second cube, smaller,
256 × 256 per face. It holds what the clouds look like from where the camera
stands: the light they send each way, and how much of the sky behind them they
hide. A compute pass marches one face of it per frame. Right after the sky's
own draw, `Clouds::Draw` blends the whole cube over the sky. Section 1 says
why it is a cube and not the screen, and what that choice gives up.

---

## What you are actually writing

One frame, with this chapter's work in it:

```text
 Setup (in Sky::Initialize)                   Record (every frame)
 ─────────────────────────────────────        ───────────────────────────────────────────────────
 Clouds::Initialize                           Sky::Update                             Chapter 23
   timestamps                    section 14     bake the sky's cube, if anything changed
   the cloud cube, 256 x 256 x 6  section 4     Clouds::Update                        sections 5, 13
   the noise, generated once:     section 7       march this frame's face: 256 x 256 rays
     shape volume   128^3                         blend each texel into what it held
     detail volume   32^3                     the shadows, then the scene pass
     weather map    512^2                     Sky::Draw                               Chapter 23
   the draw and the march      sections 4, 5     the sky, behind everything
                                                Clouds::Draw: the cloud cube over it  section 4
```

### The class map

`Clouds` is to the sky what Chapter 17's `ShadowMaps` is to `SceneRenderer`: a
class with its own images and pipelines, owned and driven by the class it
belongs to. A demo never sees it. A demo already owns a `Sky`, and the sky now
owns the clouds.

**This is `Source/PillowFort/VulkanGraphics/Clouds.h`**, whole. Each private
function names the section that writes it.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Volumetric clouds, marched into a cube of their own and drawn over the sky (Chapter 28)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/VulkanGraphics/Clouds.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/VulkanGraphics/CloudSettings.h"
#include "PillowFort/VulkanGraphics/GpuTimestamps.h"
#include "PillowFort/VulkanGraphics/SceneTargets.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include "CloudTypes.h"   // CLOUD_* sizes, CloudMarchParameters
#include "SkyTypes.h"     // Chapter 23: SkyDrawParameters, which the draw pushes

#include <glm/glm.hpp>
#include <vulkan/vulkan.h>
#include <vma/vk_mem_alloc.h>

#include <cstdint>

namespace pf::vulkan_graphics {

// What the clouds need from the sky each frame (section 5).
struct CloudInputs
{
    glm::vec3 sunDirection{ 0.0f, -1.0f, 0.0f };   // the way sunlight travels, unit: SkyInputs'
    glm::vec3 sunIrradiance{ 0.0f };               // SkyInputs'; zero: the clouds are lit by the sky alone
    glm::vec3 cameraPosition{ 0.0f };              // the cube is seen from here
    float     time     = 0.0f;                     // seconds: moves the wind
    float     exposure = 1.0f;                     // the sky's 2^stops, so the clouds match the cube
};

// One image of noise and its mip chain (section 7): sampled through `view`, every level, and written by
// the generation pass through `storageView`, level 0 alone.
struct NoiseImage
{
    VkImage       image       = VK_NULL_HANDLE;
    VmaAllocation allocation  = VK_NULL_HANDLE;
    VkImageView   view        = VK_NULL_HANDLE;
    VkImageView   storageView = VK_NULL_HANDLE;
    VkExtent3D    extent{};
    uint32_t      mipLevels   = 0;
};

// The clouds. Chapter 23's Sky owns one: Initialize and Shutdown with the sky's, Update at the end of the
// sky's Update, and Draw right after the sky's own draw.
class Clouds
{
public:
    // The cloud cube, its sets and pipelines, and the noise, made here once. skyCube and skySampler are
    // the sky's own: the march reads the sky for its ambient light.
    InitializationResult Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                    const SceneFormats& formats, VkImageView skyCube, VkSampler skySampler);
    void Shutdown();   // device idle first; safe after a partial Initialize

    // In Record, before the scene pass, after the sky's bake: marches this frame's faces of the cube.
    void Update(VkCommandBuffer commandBuffer, const CloudSettings& settings, const CloudInputs& inputs);

    // Inside the scene pass, right after the sky: blends the cube over it. `draw` is the value the sky
    // pushed for its own draw: the clouds reuse its vertex shader (Chapter 23).
    void Draw(VkCommandBuffer commandBuffer, const shared::SkyDrawParameters& draw) const;

    // Premultiplied: rgb the light the clouds send each way, a their opacity. For reflections (Chapter 30).
    VkImageView CubeView() const { return m_cubeView; }

private:
    InitializationResult CreateCube();          // section 4
    InitializationResult CreateDescriptors();   // section 4
    InitializationResult CreateNoise();         // section 7
    InitializationResult GenerateNoise();       // section 7
    InitializationResult CreateDrawPipeline();  // section 4
    InitializationResult CreateMarchPipeline(); // section 5
    shared::CloudMarchParameters MarchParameters(const CloudSettings& settings, const CloudInputs& inputs,
                                                 float weight) const;   // section 5

    VulkanContext   m_context;                          // copies of borrowed handles
    VkPipelineCache m_pipelineCache = VK_NULL_HANDLE;   // borrowed
    SceneFormats    m_formats;
    VkImageView     m_skyCube    = VK_NULL_HANDLE;      // borrowed from the sky
    VkSampler       m_skySampler = VK_NULL_HANDLE;      // borrowed: linear, clamped

    // Section 4: the cloud cube.
    VkImage       m_cube           = VK_NULL_HANDLE;
    VmaAllocation m_cubeAllocation = VK_NULL_HANDLE;
    VkImageView   m_cubeView       = VK_NULL_HANDLE;   // CUBE: the march writes it, the draw samples it

    // Section 4: one pool, two sets.
    VkDescriptorPool      m_pool           = VK_NULL_HANDLE;   // frees both sets with it
    VkDescriptorSetLayout m_marchSetLayout = VK_NULL_HANDLE;   // the cube to write, the noise, the sky
    VkDescriptorSetLayout m_drawSetLayout  = VK_NULL_HANDLE;   // the cube
    VkDescriptorSet       m_marchSet       = VK_NULL_HANDLE;
    VkDescriptorSet       m_drawSet        = VK_NULL_HANDLE;
    VkPipelineLayout      m_marchLayout    = VK_NULL_HANDLE;
    VkPipeline            m_marchPipeline  = VK_NULL_HANDLE;
    VkPipelineLayout      m_drawLayout     = VK_NULL_HANDLE;
    VkPipeline            m_drawPipeline   = VK_NULL_HANDLE;

    // Section 7: the noise, and the one sampler all three are read through.
    NoiseImage m_shape;                            // 128^3, with mips
    NoiseImage m_detail;                           // 32^3, with mips
    NoiseImage m_weather;                          // 512^2
    VkSampler  m_noiseSampler = VK_NULL_HANDLE;    // linear between texels and levels, repeating

    // Sections 5 and 13: which faces come next, and when the old texels must not be averaged in.
    bool          m_on         = false;   // the last Update marched, so Draw draws
    uint32_t      m_nextFace   = 0;
    uint32_t      m_updates    = 0;       // counts Updates: seeds the jitter, picks the timestamp slot
    uint32_t      m_freshFaces = 6;       // faces still to be written at weight 1
    CloudSettings m_lastSettings;
    glm::vec3     m_lastSunDirection{ 0.0f };
    float         m_lastExposure = 0.0f;

    // Section 14: four timestamps a frame - the march's start and end, the draw's start and end.
    static constexpr uint32_t TIMESTAMP_COUNT = 4;
    GpuTimestamps m_timestamps;
    uint32_t      m_slot = 0;   // this frame's set of four
    CloudTimings  m_timings;
};

} // namespace pf::vulkan_graphics
```

The `NoiseImage` struct, the sampler, and the three images are section 7's. The
counters near the end are sections 5 and 13's. `CubeView` is public for the
sea chapters, which reflect the clouds (Chapter 30).

### What a person edits

**This is `Source/PillowFort/VulkanGraphics/CloudSettings.h`.** The settings
are plain data, like Chapter 16's `ToneMappingSettings`. They live inside
Chapter 23's `SkySettings`, which `VulkanRenderer` owns and hands to every
demo, so one panel controls the clouds of whichever demo is running: the
"Clouds" part of the Sky header, in the "Tone mapping" window. Each group
names the section that explains it. The `operator==` at the end is how
`Update` notices that a slider moved (section 13).

```cpp
// Part of SkySettings: one for the whole engine, edited under the Sky header of the "Tone mapping" window,
// handed to every demo's sky.
// Each group names the section that explains it.
struct CloudSettings
{
    bool  enabled         = true;

    // Sections 2 and 5: the layer, and how thick the cloud is.
    float bottom          = 1500.0f;   // metres above y = 0
    float top             = 4000.0f;
    float extinction      = 0.02f;     // per metre at density 1: light goes 50 m, on average, before it scatters
    bool  uniformLayer    = false;     // density 1 everywhere in the layer: a test with a known answer

    // Section 6: how a droplet scatters sunlight.
    float forwardG        = 0.8f;      // Henyey-Greenstein g of the forward lobe
    float backwardG       = 0.3f;      // and of the backward lobe, leaning the other way
    float backwardShare   = 0.3f;      // 0..1: the backward lobe's share

    // Sections 8 and 9: what the sky holds.
    float coverage        = 0.5f;      // 0 clear .. 1 overcast
    bool  typeFromWeather = true;      // each place's cloud type from the weather map ...
    float cloudType       = 1.0f;      // ... or this one everywhere: 0 stratus, 0.5 stratocumulus, 1 cumulus
    float billows         = 0.5f;      // how deeply the shape volume's small Worley octaves carve it
    float erosion         = 0.5f;      // how deeply the detail volume eats the edges

    // Section 10: the wind.
    float windSpeed       = 10.0f;     // metres per second
    float windAngle       = 30.0f;     // degrees, turning from -Z toward +X: where the wind blows to

    // Section 11: light that scattered more than once.
    int   octaves         = 6;         // 1 = single scattering only
    float octaveEnergy    = 0.8f;      // each octave's energy, as a share of the one before

    // Section 13: cost.
    int   steps           = 64;        // march steps through the layer
    int   lightSteps      = 6;         // steps toward the sun from each sample
    int   facesPerFrame   = 1;         // of the cube's six
    float newWeight       = 0.25f;     // how much each update counts against what the texel held

    // Section 5: what the cube shows.
    int   debugView       = 0;         // CLOUD_VIEW_*
    float sliceAltitude   = 2000.0f;   // metres, for the density slice

    // Section 13: a change that the old texels must not be averaged with.
    bool operator==(const CloudSettings&) const = default;
};
```

The rest of the header is a struct for what section 14 measures, and the two
panel functions:

```cpp
// What the clouds cost on the GPU, in milliseconds, from timestamps (section 14).
struct CloudTimings
{
    double generateMs = 0.0;   // the noise, once, at Initialize
    double marchMs    = 0.0;   // this frame's faces
    double drawMs     = 0.0;   // blending the cube over the sky
};

// The "Clouds" part of the Sky panel: call between the panel's Begin and End. True if anything changed.
bool drawCloudPanel(CloudSettings& settings);

// Appends the timings to the "Tone mapping" window, under Chapter 23's Sky header. Clouds::Update calls
// it; the window was drawn earlier in this ImGui frame, so Begin finds it and adds to its end.
void drawCloudTimings(const CloudTimings& timings, bool measured);
```

`Clouds.h` holds a `CloudTimings`, so the struct is needed from the start;
`drawCloudTimings` is section 14's. **Type `drawCloudPanel` from Appendix A
now**, into `CloudSettings.cpp`: every test in Part 1 uses it. It is one slider
per field, in groups that open and close, with three buttons at the top that
section 8 explains.

### Where everything lands

```text
Shaders/Include/CloudTypes.h               the images' sizes, the debug views, the march's push constants   section 4
Shaders/Clouds/CloudNoise.glsl             tileable Worley and gradient noise, in 3D                       section 7
Shaders/Clouds/CloudShapeNoise.comp.glsl   fills the 128^3 shape volume                                     section 7
Shaders/Clouds/CloudDetailNoise.comp.glsl  fills the 32^3 detail volume                                     section 7
Shaders/Clouds/CloudWeather.comp.glsl      fills the 512^2 weather map                                      section 8
Shaders/Clouds/CloudMarch.comp.glsl        the march: one face of the cloud cube per dispatch               sections 3, 5, 6, 8-12
Shaders/Clouds/Clouds.frag.glsl            the draw: the cube, blended over the sky                         section 4
VulkanGraphics/CloudSettings.h/.cpp        the settings and their panel                                     every section
VulkanGraphics/Clouds.h/.cpp               the class                                                        sections 4, 5, 7, 13, 14
VulkanGraphics/GpuTimestamps.h/.cpp        timestamp queries, as a class (from Chapter 24)                  section 14
VulkanGraphics/Sky.h/.cpp, SkySettings.*   own the clouds, carry their settings and inputs                  section 4
Demos/{Cubes,Meshes,SceneGraph,Particles,UsdViewer,Grass}   the camera position and the time, for the sky   section 4
```

```text
Clouds.cpp
  includes
  namespace pf::vulkan_graphics {
      static createNoiseImage(context, extent, mipmapped, name, noise)   section 7
      static destroyNoiseImage(context, noise)                          section 7
      static blitMipChain(commandBuffer, noise)                          section 7
      Clouds::Initialize                                                 below
      Clouds::CreateCube                                                 section 4
      Clouds::CreateDescriptors                                          section 4
      Clouds::CreateNoise                                                section 7
      Clouds::GenerateNoise                                              section 7
      Clouds::CreateDrawPipeline                                         section 4
      Clouds::CreateMarchPipeline                                        section 5
      Clouds::MarchParameters                                            section 5
      Clouds::Update                                                     sections 5, 13, 14
      Clouds::Draw                                                       sections 4, 14
      Clouds::Shutdown                                                   section 4
  }
```

`Clouds.cpp` includes `Clouds.h`, `PillowFort/ErrorReporting/Log.h`,
`PillowFort/VulkanGraphics/GraphicsPipeline.h`,
`PillowFort/VulkanGraphics/VulkanBarriers.h`, `<algorithm>`, `<array>`,
`<bit>`, `<cmath>`, and `<format>`. The helpers sit inside the namespace, as `static`,
because they name the namespace's types.

**This is `Initialize`.** It reads as the chapter's order of work. The
timestamps come first so that the noise's generation can be timed. The cube
and its descriptor sets come before the noise, because `CreateNoise` fills in
three bindings of a set that already exists:

```cpp
InitializationResult Clouds::Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                        const SceneFormats& formats, VkImageView skyCube, VkSampler skySampler)
{
    m_context       = context;
    m_pipelineCache = pipelineCache;
    m_formats       = formats;
    m_skyCube       = skyCube;
    m_skySampler    = skySampler;

    // Section 14: first, so that the noise can be timed too.
    if (auto result = m_timestamps.Initialize(m_context, TIMESTAMP_COUNT); !result) { return result; }
    if (auto result = CreateCube(); !result)          { return result; }   // section 4
    if (auto result = CreateDescriptors(); !result)   { return result; }   // section 4
    if (auto result = CreateNoise(); !result)         { return result; }   // section 7
    if (auto result = CreateDrawPipeline(); !result)  { return result; }   // section 4
    if (auto result = CreateMarchPipeline(); !result) { return result; }   // section 5

    // The cube holds nothing yet: every face's first update replaces it.
    m_on         = false;
    m_nextFace   = 0;
    m_updates    = 0;
    m_freshFaces = 6;
    return InitializationResult::success();
}
```

Type it with only the lines whose sections you have reached, because a call to
a function you have not written yet does not link. Section 4's first run needs
the timestamps, `CreateCube`, `CreateDescriptors`, and `CreateDrawPipeline`.
Section 5 adds `CreateMarchPipeline`. Section 7 writes `CreateNoise`, whose
line goes in once section 8 has written the third of its shaders.

The chapter adds eleven files: two `.cpp` files, three headers, five shader
stages, and one shader include. Create each when its section writes it, and
rerun `GenerateProjects.bat` each time. Premake expands the C++ and shader
globs when it generates the projects, so a file added afterwards is not built.

---

# Part 1 — Light through a layer (sections 1-6)

Part 1 builds everything except the clouds' shape. It explains how light
crosses a cloudy layer, builds the cube that holds the result, and writes the
march. Its test subject is the simplest cloud there is: a slab of uniform fog
between two altitudes, everywhere the same. A uniform slab has answers you can
work out on paper, so the code can be checked against numbers before any noise
makes it interesting. Part 2 replaces the slab with real shapes.

## 1. Where the clouds are drawn

There are two ways to put volumetric clouds on the screen.

**On the screen itself.** Every pixel marches its own ray, usually at a quarter
of the screen's width and height or less, and the result is scaled up and
blended over the sky. *Horizon Zero Dawn* does this: it marches one pixel in sixteen
each frame and fills in the rest from earlier frames, moved to where they are
now. That second half is *temporal reprojection*: keep last frame's image, work
out where each of its pixels lands after the camera moved, and reuse it. It is
what makes the method fast, and it is also a project of its own.

**In a cube around the camera.** The clouds are rendered into a cube image
like Chapter 23's sky, a texel per direction, from where the camera stands.
Then they are drawn exactly as the sky is: a full-screen triangle that looks up
each pixel's direction.

This chapter uses the cube. Here is the arithmetic that decides it:

| | Screen, 400 × 250: a quarter of 1600 × 1000 each way | Cube, 256 × 256 per face |
| --- | --- | --- |
| Rays marched in total | 100,000 per frame | 393,216 for the whole cube |
| Rays marched per frame | all of them, every frame | 65,536: one face a frame |
| Grows with | the window, and with what reprojection must undo | nothing: fixed |
| Averaging noise over frames | needs reprojection | free: a texel always looks the same way |
| Who else can use it | nobody | every demo with the sky; the sea's reflections (Chapters 30-31) |

**What the cube gives up**, and when that matters:

- **The eye must stay below the cloud base.** The cube shows the layer from
  underneath. Flying into a cloud, or above one, is screen-space work.
  `Update` keeps the cube's origin below the base, so a camera that climbs
  above it still sees the clouds as if from below.
- **Parallax only every few frames.** The cube is re-rendered from the camera's
  current position, one face per frame, so it catches up within six frames. A
  cloud 3 km away shifts by 0.2° when you walk 10 m, and the cube's faces have
  caught up long before that is visible.
- **The clouds are always behind everything.** They are drawn at depth 1.0,
  like the sky. A mountain tall enough to reach into the cloud base would be
  drawn in front of clouds that should hide its top. Nothing in this tutorial's
  scenes is that tall.
- **The resolution is fixed.** A texel at the centre of a face spans about
  0.45°, which is about 8 pixels on a 1600-pixel-wide view with a 90° field of
  view. Clouds are soft, so this costs less than it sounds, but you can see
  it. `CLOUD_FACE_SIZE` is one number to raise, and section 14 says what that
  costs.

Where to go after this chapter, for clouds you can fly through, is in "Where to
go next" at the end.

## 2. Fog, measured

> **Jump:** until now light travelled through empty space between surfaces, and
> every shader evaluated something *at* a surface: a material, a light, a
> shadow. A cloud has no surface. Light is changed at every point along the way
> through it, a little at a time, and what reaches the eye is a sum over the
> whole path. Keep in mind from here that "how bright is this pixel" becomes
> "add up the light from every point along this pixel's ray, each one dimmed by
> what lies between it and the eye". Sections 2 and 3 build that sum one piece
> at a time.

Three quantities describe a fog, a cloud, or smoke. Each has a short name worth
learning, because papers about clouds use nothing else.

**Density** is how much stuff there is at a point: here, how many water
droplets. In this chapter it is a number from 0 to 1 that the noise of Part 2
produces, so 0 is clear air and 1 the thickest cloud there is.

**Extinction**, written σ (sigma), is the chance that light travelling one more
metre hits a droplet and is knocked out of its straight path. It is measured
per metre. This chapter makes it the density times one number from the panel,
**Extinction**, whose default is 0.02 per metre. At density 1, light travels
1 / 0.02 = 50 m on average before it hits something. That distance, 1/σ, is
the **mean free path**.

**Transmittance**, written *T*, is the fraction of light that crosses a stretch
of fog without being knocked out of its path. It runs from 1, all of it, to 0,
none.

How do the three connect? Picture one metre of uniform fog with σ = 0.02. It
stops 2% of whatever light enters it. The next metre stops 2% of what is left,
not 2% of the original, and so does every metre after it. Each metre takes the
same *share*, not the same *amount*. So the light never runs out after some
distance. It halves, then halves again, at a steady rate, the way a radioactive
sample decays. That is the **Beer-Lambert law**:

$$
T = e^{-\sigma d}
$$

for a distance *d* through fog of extinction σ. The `e` is Euler's number,
2.718..., and `e^-x` is the function that falls in exactly this way: by the
same share for each equal step in *x*.

A worked example: how much light gets through **100 m** of cloud at density 1?
Here σ *d* = 0.02 × 100 = 2, so *T* = e^-2 = **0.135**. About 13% gets
through. Through 35 m, *T* = e^-0.7 = 0.5: half. Through 1 km, *T* = e^-20,
two parts in a billion: a cloud a kilometre thick is a wall.

The product σ*d* has a name of its own, the **optical depth** τ (tau). It
counts how many mean free paths deep you are, and *T* = e^-τ. When the density
changes along the way, as it will in a real cloud, cut the path into pieces
over which it is nearly constant. Each piece has its own τ. The
transmittances multiply, so the optical depths add:

$$
T = e^{-\tau_1} \, e^{-\tau_2} \, e^{-\tau_3} \cdots = e^{-(\tau_1 + \tau_2 + \tau_3 + \cdots)}
$$

That is the whole of the transmittance half of this chapter: add up σ × length
along the path, and take e to minus that.

How dense are real clouds? A rough scale:

| What | σ, per metre | Mean free path |
| --- | --- | --- |
| Clear air, light haze | 0.0001 to 0.001 | 1 to 10 km |
| Thick fog | about 0.04 | 25 m |
| Stratus | 0.02 to 0.05 | 20 to 50 m |
| The core of a cumulus | 0.05 to 0.2 | 5 to 20 m |
| This chapter, at density 1 | 0.02 (the panel's default) | 50 m |

The default is lighter than a real cumulus. Section 3 marches in steps tens of
metres long, and fog much denser than one step deep looks blocky. The slider
goes to 0.2 if you want to see why.

**Where the light goes.** "Knocked out of its path" can mean two things.
*Absorbed*: the light is gone, turned into heat. *Scattered*: it leaves in a
new direction. Soot absorbs, which is why smoke can be black. Water droplets
almost only scatter: a cloud droplet absorbs well under one part in a thousand
of the light it stops. So in a cloud, every bit of light lost from one path
reappears on another. That is why clouds are white, and why this chapter can
use one number, σ, for both. A renderer of smoke would need a second one.

## 3. Marching a ray

Section 2 says how much of the sky *behind* a cloud gets through it. That is
half of what the eye sees. The other half is the light the cloud *sends*: sunlight
and skylight scattered toward the eye by droplets all along the line of sight.
Each droplet's contribution is dimmed by the cloud between it and the eye,
which is section 2's transmittance again.

Here is the sum, in words, for one line of sight. Walk outward from the eye
in steps. At each step, take the light that this slice scatters toward the eye.
Multiply it by the transmittance from the eye to the slice. Add it to a
running total.

$$
L \;=\; \sum_{\text{steps } i} T_i \,\times\, \big(\text{light that step } i \text{ sends toward the eye}\big)
$$

where *T*<sub>*i*</sub> is the transmittance of everything between the eye and
step *i*. *T* only ever shrinks as you walk out, so it is kept as a running
product too. Each step multiplies it by its own transmittance.

> **Jump:** if you have met integrals, this is one: the light gathered along
> the ray, ∫ *T*(s) σ(s) *S*(s) ds, chopped into steps. If you have not, all
> you need is that an integral is a sum of infinitely many thin slices, and a
> march is the same sum with a few dozen thick ones. Thicker slices are
> cheaper and less accurate. The rest of this section is about making thick
> slices accurate.

**What one step sends.** Call *S* the light that the cloud at a point scatters
toward the eye per unit of optical depth: the sunlight and skylight arriving
there, times the share that turns toward the eye. Section 6 works *S* out. The
obvious guess for one step of length Δs is *S* × σΔs: the light per optical
depth, times the step's optical depth. It is right for thin steps and badly
wrong for thick ones. A worked example: march 150 m of uniform cloud with
σ = 0.01 per metre and *S* = 1, in three steps of 50 m. Each step has
σΔs = 0.5.

| Step | *T* so far | Naive: *T* × *S* × σΔs | Exact: *T* × *S* × (1 − e^-σΔs) |
| --- | --- | --- | --- |
| 1 | 1.000 | 0.500 | 0.393 |
| 2 | 0.607 | 0.303 | 0.239 |
| 3 | 0.368 | 0.184 | 0.145 |
| **Sum** | | **0.987** | **0.777** |

Now compare both columns with the real answer. A slab this thick, glowing with
*S* = 1, sends exactly 1 − e^-1.5 = 0.777. The naive sum is 27% too bright.
With a single 200 m step at σΔs = 2 it adds 2.0, twice as much light as the
slab could ever send, while the exact column gives 0.865.

The fix is the column on the right. Inside one step, the light from each part
of the step is dimmed by the part of the step in front of it. Add that up
exactly and the step sends not σΔs × *S* but:

$$
\big(1 - e^{-\sigma \Delta s}\big) \, S
$$

In words: the share of the light that the step itself stops, 1 − e^-σΔs, is
also the share of its own glow that gets out. That holds because a cloud
scatters everything it stops (section 2). For thin steps,
1 − e^-σΔs ≈ σΔs, and the two columns agree. For thick ones, the exact form
can never exceed *S*. Sébastien Hillaire's 2016 course notes introduced this
form for real-time clouds. In code, a step is three lines:

```glsl
        float stepTransmittance = exp(-density * clouds.extinction * stepLength);
        light         += transmittance * (1.0 - stepTransmittance) * scattered;
        transmittance *= stepTransmittance;
```

The first is the step's own transmittance. The second adds the step's light,
dimmed by everything in front of it. The third makes the step part of the "in
front" for the steps behind it.

**Where the ray is inside the layer.** The clouds live between two altitudes,
`bottom` and `top`, 1500 m and 4000 m by default. A ray leaves the eye with a
unit direction **d**, so it climbs **d**.y metres for every metre it travels.
It reaches an altitude *h* after

$$
t = \frac{h - e_y}{d_y}
$$

metres, where *e*<sub>y</sub> is the eye's own height. A worked example: for an
eye near the ground and a ray 30° above the horizon, **d**.y = sin 30° = 0.5.
The ray enters the layer at 1500 / 0.5 = 3 km and leaves it at 8 km. At 7°
above the horizon it enters at 12.3 km. At 3°, it enters at 28.7 km. Rays
near the horizon spend tens of kilometres in the layer, and section 12 decides
how far is far enough.

The march divides the stretch from entry to exit into `steps` equal steps, 64
by default:

```glsl
    // Section 3: where the ray is inside the layer. It climbs direction.y metres per metre travelled,
    // so it reaches an altitude h after (h - eye.y) / direction.y metres.
    float reach = MARCH_REACH;
    float start = (clouds.bottom - eye.y) / direction.y;
    float end   = min((clouds.top - eye.y) / direction.y, reach);
    if (start >= end) { return vec4(0.0); }

    float stepLength = (end - start) / float(clouds.steps);
    float t          = start + stepLength * randomFloat(random);   // section 3: jitter the first step
```

These lines open section 5's `marchClouds`. `reach` caps how far a march goes,
because a ray near the horizon would otherwise cross tens of kilometres of
layer. It is a constant at the top of the march shader, under the push
constants (section 5), and section 12 explains the number:

```glsl
// Section 12: how far a march reaches, in metres, and where the fade into the sky starts, as a fraction
// of that. Clouds further away than MARCH_REACH are not drawn at all; the fade hides the edge.
const float MARCH_REACH = 30000.0;
```

**Why the first step is random.** If every ray took its samples at the same
distances, neighbouring rays would sample the same slices of the cloud, and the
slices would show as contour lines:

```text
  every ray starts at the entry point          each ray starts a random fraction of a step later

  ─────╱╱╱╱───────╱╱╱╱──────╱╱╱╱───   bands   ─────░▒░▓░▒░░▒▓░▒░▒▓▒░▒░▒░▒▓░───   fine noise
```

Moving each ray's first sample by a random fraction of a step, a different
fraction per texel, turns the bands into noise. Noise is easier to get rid of:
the march runs again and again, with a new random fraction each time, and
section 13 averages the results until the noise fades. The random numbers are
Chapter 21's `randomFloat`, seeded from the texel and from a counter of
updates, so each texel and each update draws a different stream.

## 4. The cloud cube, and drawing it

**The numbers, all at once.** **This is `Shaders/Include/CloudTypes.h`**, the
header that both languages share, like Chapter 23's `SkyTypes.h`. It holds the
four images' sizes, the debug views of section 5, and the march's push
constants:

```c
/* Shaders/Include/CloudTypes.h - Chapter 28: the clouds' sizes and push constants, in both languages.
   GLSL and C++ both include it as "CloudTypes.h": Shaders/Include is on both include paths. */
#ifndef PF_CLOUD_TYPES_H
#define PF_CLOUD_TYPES_H

#include "SharedShaderTypes.h"   /* vec2, vec4, uint */

/* Texels along each side of each image (sections 4, 7, and 8). */
#define CLOUD_SHAPE_SIZE   128   /* the shape volume, 128 x 128 x 128 */
#define CLOUD_DETAIL_SIZE  32    /* the detail volume, 32 x 32 x 32 */
#define CLOUD_WEATHER_SIZE 512   /* the weather map, 512 x 512 */
#define CLOUD_FACE_SIZE    256   /* each face of the cloud cube, 256 x 256 */

/* CloudMarchParameters::debugView (section 5). */
#define CLOUD_VIEW_SHADED        0u
#define CLOUD_VIEW_COVERAGE      1u   /* the weather map where each ray meets the cloud base: red cover, green type */
#define CLOUD_VIEW_DENSITY_SLICE 2u   /* the density where each ray crosses sliceAltitude */
#define CLOUD_VIEW_TRANSMITTANCE 3u   /* how much of the sky gets through: white clear, black opaque */

#ifdef __cplusplus
    namespace pf::shared {
#endif

/* The march's push constants (std430): exactly the 128 bytes every device guarantees. */
struct CloudMarchParameters
{
    vec4  toSun;           /*   0  xyz: unit direction TOWARD the sun; w: seconds, which moves the wind */
    vec4  sunIrradiance;   /*  16  rgb: the sun's irradiance times the sky's exposure; w: each octave's energy, 0..1 */
    vec4  origin;          /*  32  xyz: where the cube is seen from, below the cloud base; w: this update's blend weight */
    vec2  wind;            /*  48  wind velocity along world x and z, m/s */
    float sliceAltitude;   /*  56  metres: where CLOUD_VIEW_DENSITY_SLICE cuts the layer */
    uint  uniformLayer;    /*  60  1: density 1 everywhere in the layer, the test of section 5; 0: the noise */
    float bottom;          /*  64  the cloud layer, metres above y = 0 */
    float top;             /*  68 */
    float coverage;        /*  72  0 clear .. 1 overcast */
    float extinction;      /*  76  per metre, at density 1 */
    float billows;         /*  80  how deeply the shape's own Worley octaves carve it, 0..1 */
    float erosion;         /*  84  how deeply the detail volume eats the edges, 0..1 */
    float cloudType;       /*  88  0 stratus .. 1 cumulus; below 0: the weather map's */
    float forwardG;        /*  92  Henyey-Greenstein g of the forward lobe */
    float backwardG;       /*  96  g of the backward lobe, a positive number */
    float backwardShare;   /* 100  0..1: how much of the scattering the backward lobe takes */
    uint  face;            /* 104  which cube face this dispatch marches: 0..5 */
    uint  frame;           /* 108  counts updates; seeds the jitter */
    uint  steps;           /* 112  march steps through the layer */
    uint  lightSteps;      /* 116  steps toward the sun from each sample */
    uint  octaves;         /* 120  multiple-scattering octaves, 1 = single scattering */
    uint  debugView;       /* 124  CLOUD_VIEW_* */
};

#ifdef __cplusplus
    static_assert(sizeof(CloudMarchParameters) == 128, "CloudMarchParameters layout drifted.");
    static_assert(offsetof(CloudMarchParameters, bottom) == 64, "CloudMarchParameters alignment drifted.");
    static_assert(offsetof(CloudMarchParameters, face) == 104, "CloudMarchParameters alignment drifted.");
    }
#endif

#endif
```

The push constants are exactly 128 bytes, the size every device guarantees.
The first 64 bytes are three `vec4`s and a `vec2` with two scalars beside it.
Each `vec4` carries a scalar in its `w` that belongs with it: the time with the
sun's direction, the octave energy with the sun's light, and the blend weight
with the origin. Sixteen four-byte scalars fill the rest. The asserts pin the
two offsets where std430 could have surprised you.

**This is `CreateCube`.** The cloud cube is Chapter 23's cube again, with a
smaller face and different contents. The usual sky cube holds radiance and
nothing else. This one holds **premultiplied color**, Chapter 21 section 5's
idea: rgb is the light the clouds send toward the eye from that direction,
already dimmed by the cloud in front, and alpha is their **opacity**,
1 − *T*. Those two numbers are exactly what section 3's march produces, and
Chapter 21's premultiplied blend puts them over the sky in one fixed-function
step:

$$
\text{result} = \text{cloud}_{rgb} + \text{sky} \times (1 - \text{cloud}_{a})
$$

Its format is `R16G16B16A16_SFLOAT`. It holds light, which is unbounded, so it
has to be a float, and it needs a fourth channel for the opacity.

```cpp
InitializationResult Clouds::CreateCube()
{
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .flags         = VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R16G16B16A16_SFLOAT,
        .extent        = { CLOUD_FACE_SIZE, CLOUD_FACE_SIZE, 1 },
        .mipLevels     = 1,
        .arrayLayers   = 6,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_STORAGE_BIT        // the march writes it, face by face
                       | VK_IMAGE_USAGE_SAMPLED_BIT        // the draw reads it by direction
                       | VK_IMAGE_USAGE_TRANSFER_DST_BIT,  // cleared once, below
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(m_context.allocator, &imageInfo, &allocationInfo, &m_cube, &m_cubeAllocation, nullptr)
        != VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for the cloud cube.");
    }

    // One cube view for both uses, as Chapter 23's: an imageCube to the march, a samplerCube to the draw.
    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_cube,
        .viewType         = VK_IMAGE_VIEW_TYPE_CUBE,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 6 },
    };
    if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &m_cubeView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the cloud cube.");
    }

    // Cleared to "no cloud" - zero light, zero opacity - so a face drawn before its first march shows the
    // sky, and the first march's average starts from numbers rather than whatever the memory held.
    immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, m_cube,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);
        const VkClearColorValue       clear{ { 0.0f, 0.0f, 0.0f, 0.0f } };
        const VkImageSubresourceRange range{ VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 6 };
        vkCmdClearColorImage(commandBuffer, m_cube, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, &clear, 1, &range);
        transitionImage(commandBuffer, m_cube,
                        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_SAMPLED_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_READ_BIT);
    });
    return InitializationResult::success();
}
```

- **One view, two uses**, as in Chapter 23 section 3. The march writes the cube
  as an `imageCube`, one texel at a time with the face as the third
  coordinate, and the draw samples the same view as a `samplerCube`, by
  direction.
- **Cleared, not left undefined.** A new image's memory is whatever was there,
  and on a 16-bit float a bad bit pattern is a NaN. Each face's first march
  replaces what it held (section 5), but the draw samples every face from the
  first frame, and at one face a frame most of them are still waiting. Cleared
  to zero light and zero opacity, a face that has not been marched yet shows
  the plain sky.
- **Readable from the start.** The cube leaves `CreateCube` in
  `SHADER_READ_ONLY_OPTIMAL`, as Chapter 23's does, so any descriptor set that
  names it is valid before the first march and while the clouds are off. The
  sea chapters keep it in a set all the time.

The clear's two barriers answer Chapter 04 section 5's three questions:

- **Before the clear.**
  - Q1: nothing came before, so the source is `NONE`. The clear runs in the
    `CLEAR` stage.
  - Q2: nothing to flush. The clear writes, so the destination is
    `TRANSFER_WRITE`.
  - Q3: `UNDEFINED` to `TRANSFER_DST_OPTIMAL`, the layout a clear needs.
- **After it.**
  - Q1: the clear's `CLEAR` stage before the first readers. Those are the
    draw's fragment shader and the march's compute shader.
  - Q2: the clear's `TRANSFER_WRITE` made available. It is made visible to
    both readers' accesses: the draw's sampled read and the march's storage
    read.
  - Q3: `TRANSFER_DST_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL`, where each frame
    expects to find the cube (section 5).

**This is `CreateDescriptors`.** Two sets come from one small pool, one per
pass:

| Set | Binding | What | Written by |
| --- | --- | --- | --- |
| march | 0 | the cloud cube, a storage image (`imageCube`) | here |
| march | 1, 2, 3 | the shape volume, the detail volume, the weather map | `CreateNoise` (section 7) |
| march | 4 | Chapter 23's sky cube, for the ambient light | here |
| draw | 0 | the cloud cube, sampled by direction | here |

The code is Chapter 20 section 4's pattern: two set layouts, a pool sized for
one storage image and five combined image samplers, two sets, and three writes.
It is in Appendix A. Bindings 1 to 3 stay empty until section 7's `CreateNoise` writes them, which
`Initialize` calls right after this. A descriptor only has to be valid when a
shader that uses it runs (Chapter 20 section 10). The two cubes are sampled
through the sky's own sampler, linear and clamped, so the clouds create none of
their own for them.

**This is `Clouds.frag.glsl`**, the whole draw shader. Chapter 23's
`Sky.vert` already turns each corner of the full-screen triangle into a world
direction, so the clouds reuse it unchanged. Only the fragment shader is new,
and it is one texture lookup:

```glsl
// Shaders/Clouds/Clouds.frag.glsl - Chapter 28 section 4. Drawn right after the sky, with Chapter 23's
// Sky.vert and its push constants: each pixel looks up its own direction in the cloud cube. The cube
// holds premultiplied color, so the pipeline's PremultipliedAlpha blend keeps the sky behind - its sun
// disk included - in proportion to how much light gets through the clouds.
#version 450

layout(location = 0) in  vec3 viewDirection;   // from Sky.vert: world space, not unit length
layout(location = 0) out vec4 outColor;

layout(set = 0, binding = 0) uniform samplerCube cloudCube;

void main()
{
    outColor = texture(cloudCube, normalize(viewDirection));
}
```

**This is `CreateDrawPipeline`.** It is Chapter 23's sky pipeline with two
differences: the fragment shader, and the blend.

```cpp
InitializationResult Clouds::CreateDrawPipeline()
{
    // The sky's push range, exactly: Sky.vert reads the same SkyDrawParameters at the same offset.
    const VkPushConstantRange drawRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
        .offset     = 0,
        .size       = sizeof(shared::SkyDrawParameters),
    };
    const VkPipelineLayoutCreateInfo drawLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_drawSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &drawRange,
    };
    if (vkCreatePipelineLayout(m_context.device, &drawLayoutInfo, nullptr, &m_drawLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the cloud draw.");
    }

    // Chapter 23's sky pipeline, but blended: the cube's premultiplied color over what the sky drew.
    const VkFormat colorFormats[] = { m_formats.color };
    const GraphicsPipelineDesc desc{
        .vertexShader   = "Sky/Sky.vert.spv",
        .fragmentShader = "Clouds/Clouds.frag.spv",
        .colorFormats   = colorFormats,
        .depthFormat    = m_formats.depth,
        .depthTest      = true,
        .depthWrite     = false,
        .depthCompare   = VK_COMPARE_OP_LESS_OR_EQUAL,
        .blend          = BlendMode::PremultipliedAlpha,
        .layout         = m_drawLayout,
        .samples        = m_formats.samples,
    };
    m_drawPipeline = createGraphicsPipeline(m_context.device, m_pipelineCache, desc);
    if (m_drawPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the cloud draw pipeline failed.");
    }
    return InitializationResult::success();
}
```

- **The same push range as the sky's**, 96 bytes for the vertex and fragment
  stages, because `Sky.vert` reads `SkyDrawParameters` from offset 0. The
  draw pushes the very value the sky pushed. Its `clipToWorld` is the matrix
  that un-projects a corner (Chapter 23 section 1).
- **The same depth state:** depth 1.0, `LESS_OR_EQUAL`, no depth writes. The
  clouds land on exactly the pixels the sky did, behind everything drawn.
- **`BlendMode::PremultipliedAlpha`**, Chapter 21's: source × 1 + destination
  × (1 − source alpha). With the cube's contents that is the formula above. The
  sun's disk, which Chapter 23 draws analytically in `Sky::Draw` and never
  bakes, is dimmed by the clouds in front of it like the rest of the sky.
  Behind a thick cloud it disappears, with no change to the sky's shaders.

**This is `Draw`.** It binds, pushes, and draws three vertices:

```cpp
void Clouds::Draw(VkCommandBuffer commandBuffer, const shared::SkyDrawParameters& draw) const
{
    if (!m_on) { return; }

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_drawPipeline);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_drawLayout, 0, 1, &m_drawSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_drawLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(draw), &draw);
    vkCmdDraw(commandBuffer, 3, 1, 0, 0);   // Chapter 08's full-screen triangle, at depth 1.0
}
```

Section 14 puts a timestamp on each side of the draw. `m_on` is set by
`Update`, so switching the clouds off on the panel stops the march and the draw
together.

**`Shutdown`** is the reverse of `Initialize`, with every handle put back to
null so that `Initialize` can run again after a demo switch. Like the sky's, it
first checks that `Initialize` ever ran: with no device there is nothing to
destroy anything with. It is in Appendix A.

### What the sky gains

Four small changes to Chapter 23's code connect the clouds to it.

**`SkySettings` gains the cloud settings**, at the end of the struct, and
`SkySettings.h` includes `CloudSettings.h`:

```cpp
    CloudSettings clouds;           // Chapter 28
```

and `drawSkyPanel`, after its exposure slider, inside the Sky header, draws them
there too:

```cpp
        changed |= drawCloudPanel(settings.clouds);   // Chapter 28
```

**`SkyInputs` gains two fields** at its end. The clouds need to know where the
camera is, because the cube is seen from there, and what time it is, because
the wind moves them:

```cpp
    glm::vec3 cameraPosition{ 0.0f };              // Chapter 28: where the clouds are seen from
    float     time = 0.0f;                         // Chapter 28: seconds, which move the clouds' wind
```

Every demo that updates a sky fills them in. Here is the USD viewer's, just
before its `m_sky.Update`:

```cpp
    skyInputs.cameraPosition = glm::vec3(frameData.cameraPosition);   // Chapter 28: for the clouds
    skyInputs.time           = m_time;
```

and the Meshes demo's, whose sky inputs are written in place:

```cpp
    m_sky.Update(commandBuffer, frame.frameIndex, frame.sky,
                 { .sunDirection   = sun.direction,                          // Chapter 23
                   .sunIrradiance  = sun.emission,
                   .cameraPosition = glm::vec3(frameData.cameraPosition),   // Chapter 28
                   .time           = m_time });
```

The Cubes, Scene graph, Particles, and Grass demos get the same two lines; the
grass passes `m_cameraTransform.translation`, which is what its frame data
holds. A demo that leaves them out still gets clouds, but frozen, and seen from
the world's origin.

**`Sky` owns a `Clouds`**, as a private member at the end of the class, with
`Sky.h` including `Clouds.h`, and passes it on to the sea chapters:

```cpp
    Clouds m_clouds;   // Chapter 28: marched into a cube of their own, drawn over this one
```

```cpp
    VkImageView CloudCubeView() const { return m_clouds.CubeView(); }   // Chapter 28: premultiplied clouds
```

and calls it from its four functions. In `Initialize`, after
`CreatePipelines`, because the clouds read the sky's cube and need its view and
sampler to exist:

```cpp
    // Chapter 28: the clouds, which read this cube for the light of the sky around them.
    if (auto result = m_clouds.Initialize(m_context, m_pipelineCache, m_formats, m_cubeView, m_cubeSampler); !result)
    {
        return result;
    }
```

In `Shutdown`, right after Chapter 23's check that `Initialize` ever ran, and
before anything of the sky's is destroyed, because the clouds' descriptor set
points at the sky's cube:

```cpp
    m_clouds.Shutdown();   // Chapter 28: first, because the clouds' set points at this cube
```

At the very end of `Update`, after the bake-if-changed block. The clouds march
every frame whether or not the sky changed, and they read the cube the bake
may just have written:

```cpp
    // Chapter 28: the clouds march every frame, whether or not the sky changed.
    m_clouds.Update(commandBuffer, settings.clouds, { .sunDirection   = inputs.sunDirection,
                                                      .sunIrradiance  = inputs.sunIrradiance,
                                                      .cameraPosition = inputs.cameraPosition,
                                                      .time           = inputs.time,
                                                      .exposure       = exposure });
```

`exposure` is the sky's `2^stops`, which Chapter 23 bakes into its cube. The
clouds multiply their sunlight by the same number, so that a brighter sky has
brighter clouds.

And at the end of `Draw`, after the sky's own `vkCmdDraw`, passing the push
constants the sky just used:

```cpp
    m_clouds.Draw(commandBuffer, draw);   // Chapter 28: blended over the sky, with the same push constants
```

Chapter 22's deferred path draws the sky with `DrawInOwnPass` (Chapter 23
section 10), which opens a scope of its own and calls `Draw` inside it. So the
clouds follow the sky there too, with no further change.

### A first look: a cube you can recognize

Nothing marches yet, but everything that draws the cube exists. A cube cleared
to a color you would never mistake for a cloud proves the draw, the blend, and
the sky's wiring now, before a march can hide a mistake in any of them.

- **`Update`, for now, is its first line.** Section 5 writes the march below
  it:

  ```cpp
  void Clouds::Update(VkCommandBuffer /*commandBuffer*/, const CloudSettings& settings, const CloudInputs& /*inputs*/)
  {
      m_on = settings.enabled;   // section 5 writes the march below this line
  }
  ```

- **`Initialize`** calls the timestamps, `CreateCube`, `CreateDescriptors`, and
  `CreateDrawPipeline`, and nothing else yet.
- **In `CreateCube`, clear to half-opaque red** instead of to nothing, for this
  run only:

  ```cpp
          const VkClearColorValue       clear{ { 0.5f, 0.0f, 0.0f, 0.5f } };   // for this run only: half-opaque red
  ```

Build, run the USD viewer, open the Sky header of the "Tone mapping" window, and
set **Mode** to "Sun sky". The whole sky turns a pinkish red, and so does the
ground beyond the scene's floor. By the blend formula above, each pixel is now
red 0.5 plus half the sky, and half the sky's green and blue: the red is the
cube's light, and the half is its opacity hiding the sky. Turn toward the sun
and its disk still shows, because half of a disk tens of thousands of times
brighter than the sky is still white. Untick **Clouds** and the plain sky comes
back: `Update` sets `m_on` false, and `Draw` returns at once.

Put the clear back to zero before section 5: a face that has not been marched
yet should show the plain sky ("Cleared, not left undefined", above).

## 5. The march

**This is `Shaders/Clouds/CloudMarch.comp.glsl`**, built over the rest of the
chapter. Appendix B lists it whole. Its head includes the shared header,
Chapter 23's cube helpers, and Chapter 21's random numbers, and declares the
five bindings and the push constants:

```glsl
// Shaders/Clouds/CloudMarch.comp.glsl - Chapter 28. One face of the cloud cube per dispatch: each texel
// marches its direction through the cloud layer, and blends what it finds into what the texel held.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "CloudTypes.h"   // CloudMarchParameters, CLOUD_*
#include "CubeMap.glsl"   // Chapter 23: cubeTexelDirection
#include "Random.glsl"    // Chapter 21: seedRandom, randomFloat

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0, rgba16f) uniform imageCube   cloudCube;    // texel (x, y) of face z; premultiplied
layout(set = 0, binding = 1) uniform sampler3D   shapeVolume;          // section 7
layout(set = 0, binding = 2) uniform sampler3D   detailVolume;         // section 7
layout(set = 0, binding = 3) uniform sampler2D   weatherMap;           // section 8
layout(set = 0, binding = 4) uniform samplerCube skyCube;              // Chapter 23: the sky, for the ambient light

layout(push_constant) uniform MarchBlock
{
    CloudMarchParameters clouds;
};
```

Bindings 1 to 3 are the noise, which nothing reads until Part 2, so they can
stay empty until section 7 writes them (section 4's `CreateDescriptors`).

**One invocation per texel of a face.** `main` works out which face and which
texel it is, turns that into a direction with Chapter 23's
`cubeTexelDirection`, marches, and blends:

```glsl
void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    if (texel.x >= CLOUD_FACE_SIZE || texel.y >= CLOUD_FACE_SIZE) { return; }   // the dispatch rounds up

    uint face      = (clouds.face + gl_GlobalInvocationID.z) % 6u;   // z counts this frame's faces
    vec3 direction = cubeTexelDirection(face, (vec2(texel) + 0.5) / float(CLOUD_FACE_SIZE));

    // Section 3: a different jitter for every texel and every update.
    uint random = seedRandom(uint(texel.y * CLOUD_FACE_SIZE + texel.x) + face * uint(CLOUD_FACE_SIZE * CLOUD_FACE_SIZE),
                             clouds.frame);

    // Below the horizon, and on the -Y face, the eye under the layer sees no cloud.
    vec4 result = vec4(0.0);
    if (direction.y > 0.001)
    {
        result = clouds.debugView == CLOUD_VIEW_SHADED ? marchClouds(direction, random) : debugView(direction, random);
    }

    // Section 5: blend into what the texel held. Weight 1 replaces it - by choosing result, not by mix,
    // whose previous * 0 is NaN when previous is NaN or infinite: such a texel would never recover.
    ivec3 address  = ivec3(texel, int(face));
    vec4  previous = imageLoad(cloudCube, address);
    imageStore(cloudCube, address, clouds.origin.w >= 1.0 ? result : mix(previous, result, clouds.origin.w));
}
```

- **The face comes from z.** `Update` marches one face per frame by default,
  but the panel allows up to six. All of a frame's faces are one dispatch,
  whose z counts them on from `clouds.face`. Separate dispatches would need
  nothing between them, because they write different faces. But
  synchronization validation tracks a storage image as a whole (Chapter 20
  section 5), and would report them as a conflict.
- **Below the horizon there is nothing to march.** The eye is below the cloud
  base, so a ray that does not climb never meets the layer. That covers the
  whole -Y face and the lower half of the side faces. Their texels write
  "no cloud", and they cost almost nothing.
- **The blend weight is `origin.w`.** 1 replaces what the texel held. Anything
  less keeps a share of the old value, which is section 13's running average.
  `mix(previous, result, w)` is `previous × (1 − w) + result × w`. At weight 1
  the shader stores `result` itself instead: `previous × 0` is 0 only when
  `previous` is a number. A NaN or an infinity times 0 is NaN, so with `mix` a
  texel that ever held one would never hold a number again, not even after
  section 13's fresh starts.

**This is `marchClouds`**, section 3's sum, as Part 1 has it. Two of its lines
stand in for later sections, and each says which line replaces it: the
footprint, which section 9 works out, and the last line, which section 12 fades.
The light each step sends is section 6's, so for now it is zero, and the march
measures only how much of the sky gets through:

```glsl
vec4 marchClouds(vec3 direction, inout uint random)
{
    vec3 eye = clouds.origin.xyz;

    // Section 3: where the ray is inside the layer. It climbs direction.y metres per metre travelled,
    // so it reaches an altitude h after (h - eye.y) / direction.y metres.
    float reach = MARCH_REACH;
    float start = (clouds.bottom - eye.y) / direction.y;
    float end   = min((clouds.top - eye.y) / direction.y, reach);
    if (start >= end) { return vec4(0.0); }

    float stepLength = (end - start) / float(clouds.steps);
    float t          = start + stepLength * randomFloat(random);   // section 3: jitter the first step

    vec3  light         = vec3(0.0);
    float transmittance = 1.0;
    for (uint i = 0u; i < clouds.steps; ++i, t += stepLength)
    {
        vec3  p         = eye + direction * t;
        float footprint = 0.0;   // Part 1: section 9 works out how wide this texel is, out here
        float density   = cloudDensity(p, true, footprint);
        if (density <= 0.0) { continue; }

        vec3 scattered = vec3(0.0);   // Part 1: section 6 lights the cloud

        // Section 3: this step's own share of the light, and of the transmittance.
        float stepTransmittance = exp(-density * clouds.extinction * stepLength);
        light         += transmittance * (1.0 - stepTransmittance) * scattered;
        transmittance *= stepTransmittance;
        // Nothing behind this point would show - except the sun's disk, which is tens of thousands of
        // times brighter than the sky: 1% of it is still white. So a ray that stops here is opaque.
        if (transmittance < 0.01)
        {
            transmittance = 0.0;
            break;
        }
    }

    return vec4(light, 1.0 - transmittance);   // Part 1: section 12 fades far clouds here
}
```

- **It returns premultiplied color.** The light gathered, and 1 − *T*. Section
  12's fade will scale both together, which is how a premultiplied color fades.
- **It stops early, and then it is opaque.** Once *T* falls below 1%, the rest
  of the steps would only cost time, so the loop ends and sets *T* to 0. Not
  leaving the last 1% in is deliberate. The sky behind is about 0.3, and 1% of
  that is invisible. But Chapter 23 draws the sun's disk at tens of thousands,
  and 1% of the disk is still white: a sun shining through a cloud it cannot
  get through.
- **A sample with no cloud costs only its density**, two texture reads once
  Part 2 gives the cloud a shape. `continue` skips the lighting, which is where
  the time goes (section 6). In a sky of scattered clouds most samples are clear
  air.

**This is `cloudDensity`, as Part 1 has it.** Above the layer or below it there
is no cloud. Inside it, the **Uniform layer** checkbox returns 1 everywhere:
section 2's slab of fog. Without it there is no cloud at all yet:

```glsl
float cloudDensity(vec3 p, bool withDetail, float footprint)
{
    float height = (p.y - clouds.bottom) / (clouds.top - clouds.bottom);   // 0 at the base, 1 at the top
    if (height <= 0.0 || height >= 1.0) { return 0.0; }
    if (clouds.uniformLayer != 0u)      { return 1.0; }   // section 5: a slab with a known answer
    return 0.0;   // Part 1: no shapes yet. Section 9 replaces this line.
}
```

Section 9 replaces the last line with the shapes. `withDetail` and `footprint`
are explained there and in section 6.

**This is `debugView`, as Part 1 has it**, the panel's **View** list. Each view
writes an opaque color instead of the clouds, unlit, so that what it shows is a
number and not a lighting result. Part 1 has one view, and sections 8 and 9 add
the other two in place of the last line:

```glsl
vec4 debugView(vec3 direction, inout uint random)
{
    vec3 eye = clouds.origin.xyz;
    if (clouds.debugView == CLOUD_VIEW_TRANSMITTANCE)
    {
        return vec4(vec3(1.0 - marchClouds(direction, random).a), 1.0);
    }
    return vec4(0.0, 0.0, 0.0, 1.0);   // Part 1: sections 8 and 9 add their views here
}
```

| View | Shows | Use it in |
| --- | --- | --- |
| Transmittance | *T* along each ray, grey: white is clear sky, black is opaque | below; section 12 |
| Coverage | the weather map where each ray meets the cloud base: red is cloudiness, green is cloud type | section 8 |
| Density slice | the density where each ray crosses the panel's slice altitude, a horizontal cut through the layer | section 9 |

**This is `MarchParameters`**, which turns the settings and the frame's inputs
into the push constants:

```cpp
shared::CloudMarchParameters Clouds::MarchParameters(const CloudSettings& settings, const CloudInputs& inputs,
                                                     float weight) const
{
    // The cube is seen from the camera, but never from inside or above the layer: the march assumes the
    // eye is below the clouds.
    const glm::vec3 origin{ inputs.cameraPosition.x,
                            std::min(inputs.cameraPosition.y, settings.bottom - 1.0f),
                            inputs.cameraPosition.z };
    const float     windAngle = glm::radians(settings.windAngle);   // Chapter 27's convention: from -Z toward +X

    return {
        .toSun         = glm::vec4(-inputs.sunDirection, inputs.time),
        .sunIrradiance = glm::vec4(inputs.sunIrradiance * inputs.exposure, settings.octaveEnergy),
        .origin        = glm::vec4(origin, weight),
        .wind          = glm::vec2(std::sin(windAngle), -std::cos(windAngle)) * settings.windSpeed,
        .sliceAltitude = settings.sliceAltitude,
        .uniformLayer  = settings.uniformLayer ? 1u : 0u,
        .bottom        = settings.bottom,
        .top           = std::max(settings.top, settings.bottom + 1.0f),
        .coverage      = settings.coverage,
        .extinction    = settings.extinction,
        .billows       = settings.billows,
        .erosion       = settings.erosion,
        .cloudType     = settings.typeFromWeather ? -1.0f : settings.cloudType,
        .forwardG      = settings.forwardG,
        .backwardG     = settings.backwardG,
        .backwardShare = settings.backwardShare,
        .face          = m_nextFace,
        .frame         = m_updates,
        .steps         = static_cast<uint32_t>(std::max(settings.steps, 1)),
        .lightSteps    = static_cast<uint32_t>(std::max(settings.lightSteps, 1)),
        .octaves       = static_cast<uint32_t>(std::max(settings.octaves, 1)),
        .debugView     = static_cast<uint32_t>(settings.debugView),
    };
}
```

- **The cube is seen from the camera**, but never from at or above the cloud
  base, as section 1 promised.
- **The sun's direction is turned around.** `SkyInputs` carries the way
  sunlight travels, Chapter 16's convention, and the march wants the way
  toward the sun.
- **The sunlight carries the sky's exposure**, 2^stops, because Chapter 23's
  cube does. The clouds' ambient light is read from that cube (section 6), so
  it already has it.
- **The wind becomes a velocity** in world x and z, from Chapter 27's angle
  convention: degrees from −Z toward +X (section 10).
- **A cloud type below zero means "from the weather map"** (section 8).

**`CreateMarchPipeline`** is Chapter 20's pattern with nothing new in it: a
pipeline layout with the march's set and 128 bytes of push constants, and
`createComputePipeline` with `"Clouds/CloudMarch.comp.spv"`. It is in Appendix
A.

**This is `Update`, as Part 1 has it.** What matters here is the shape:
barrier, march, barrier. The running average and the timing are sections 13
and 14's, and each adds its lines with an anchor:

```cpp
void Clouds::Update(VkCommandBuffer commandBuffer, const CloudSettings& settings, const CloudInputs& inputs)
{
    m_on = settings.enabled;
    if (!m_on) { return; }

    const uint32_t faces  = static_cast<uint32_t>(std::clamp(settings.facesPerFrame, 1, 6));
    const float    weight = 1.0f;   // Part 1: each march replaces what the texel held. Section 13 averages.
    const shared::CloudMarchParameters parameters = MarchParameters(settings, inputs, weight);

    // Section 5. Into the march: last frame's draw sampled the cube in its fragment shader, and the march
    // reads and writes it as storage.
    transitionImage(commandBuffer, m_cube,
                    VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                    VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_marchPipeline);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_marchLayout, 0, 1, &m_marchSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_marchLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(parameters), &parameters);
    // One dispatch for all of this frame's faces: z counts them, on from parameters.face.
    constexpr uint32_t GROUP = 8;   // the shader's local_size_x and _y
    vkCmdDispatch(commandBuffer, groupCount(CLOUD_FACE_SIZE, GROUP), groupCount(CLOUD_FACE_SIZE, GROUP), faces);

    // Out of the march: the draw, later this frame, samples what it wrote.
    transitionImage(commandBuffer, m_cube,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

    m_nextFace   = (m_nextFace + faces) % 6;
    ++m_updates;
}
```

The two barriers around the march, with the three questions:

- **Into the march.** This is the return trip of Chapter 20 section 10, with
  one difference.
  - Q1: last frame's `Clouds::Draw` sampled the cube in its
    `FRAGMENT_SHADER`, and this frame's `COMPUTE_SHADER` writes it, so the
    write waits for the read.
  - Q2: a read leaves nothing to flush, so the source access is `NONE`. The
    destination is a storage **read and** write.
  - Q3: `SHADER_READ_ONLY_OPTIMAL` to `GENERAL`, not `UNDEFINED` to `GENERAL`,
    and this is the difference. The march blends into what each texel held
    (from section 13 on, at a weight below 1), so the old contents must
    survive the transition. `UNDEFINED` would let the
    driver throw them away.
  - The old contents were written by an earlier march. The barrier after that
    march made them available. This barrier's execution dependency chains
    after it, through the fragment shader, and its destination access makes
    them visible to the storage read.
- **Out of the march.**
  - Q1: this `COMPUTE_SHADER` before the draw's `FRAGMENT_SHADER`, later this
    frame. Nothing else reads the cube after the march, so nothing else is
    named. Adding `COMPUTE_SHADER` just in case would make every compute
    dispatch after it in the frame wait for the march to finish.
  - Q2: `SHADER_STORAGE_WRITE` made visible to `SHADER_SAMPLED_READ`.
  - Q3: `GENERAL` to `SHADER_READ_ONLY_OPTIMAL`, the layout the draw's
    descriptor names.

The march also *samples* the sky's cube. That needs nothing here: Chapter 23
section 7's barrier after the bake already names `COMPUTE_SHADER` as a reader,
and from Chapter 23's `Initialize` on the cube is always in
`SHADER_READ_ONLY_OPTIMAL` when no bake is running.

### The test with a known answer

Section 2 worked out *T* on paper, so the program can be checked against it.
Make the layer uniform and thin enough to see through, look straight up, and
read the transmittance:

- In the "Tone mapping" window, open **Sky** and set **Mode** to "Sun sky". Set
  the curve to Raw at 0 stops (Chapter 16 section 6), so the screen shows the
  numbers unchanged.
- Under "Clouds", tick **Uniform layer**, set **Extinction** to 0.0004
  (Ctrl+click a slider to type a value into it), and leave the altitudes at
  1500 to 4000 m. Under "Debug", set **View** to "Transmittance".
- Fly the camera so it looks straight up.

The ray straight up crosses 2500 m of fog, so τ = 0.0004 × 2500 = 1 and
*T* = e^-1 = 0.368. The composite pass encodes 0.368 as the sRGB byte
**163**. Read the pixel at the centre of the screen, by picking it in
RenderDoc's Texture Viewer (Chapter 34 sections 1 and 3) or with any color
picker on a screenshot: it is (163, 163, 163), which a viewer that shows
fractions gives as 163/255 = 0.639. Rays away from the centre cross the layer
at a slant, through more fog, so the picture darkens toward the edges. Set the
extinction to 0.0008 and the centre reads e^-2 = 0.135, the byte 103. If it
does not, the march's step bookkeeping is wrong somewhere, and it is worth
finding now, before any noise hides it.

Back on "Shaded", the sky shows through the slab dimmed, darkest toward the
horizon, where the rays cross the most fog: the slab hides what it should, and
sends no light of its own yet. Section 6 gives it light.

## 6. Sunlight

A uniform slab with nothing but its own transmittance is a grey filter. To
glow, the cloud needs light, and the brightest light in the sky is the sun. At
every sample the march asks two questions about it: how much sunlight reaches
this point, and how much of what arrives turns toward the eye?

### How much sunlight reaches a point

The sunlight reaching a point inside the cloud has crossed the cloud between it
and the sun, so it is the sun's irradiance (Chapter 16 section 2) times another
transmittance. Section 2 knows how to find one: march again, this time from the
sample toward the sun, adding up σ × length. How far toward the sun it looks
is a constant at the top of the shader, beside `MARCH_REACH`:

```glsl
// Section 6: how far toward the sun each sample looks for cloud in the light's way, in metres.
const float LIGHT_MARCH_DISTANCE = 1000.0;
```

**This is `opticalDepthToSun`**, the *light march*:

```glsl
float opticalDepthToSun(vec3 p, float footprint)
{
    float stepLength = LIGHT_MARCH_DISTANCE / float(clouds.lightSteps);
    float depth      = 0.0;
    for (uint i = 0u; i < clouds.lightSteps; ++i)
    {
        vec3 q = p + clouds.toSun.xyz * (stepLength * (float(i) + 0.5));
        depth += cloudDensity(q, false, footprint) * clouds.extinction * stepLength;
    }
    return depth;
}
```

It returns the optical depth τ rather than *T*, because section 11 needs the
optical depth itself. It is short and coarse by design: six steps by default,
spread over 1 km toward the sun. Cloud further away than that still shades the
point, but by then the light has scattered so many times that it hardly
matters which way it came from (section 11). It is also cheap per step, with
`withDetail` false. The edges' fine erosion (section 9) changes what you see
of a cloud's outline, not how much light reaches its middle, so the light march
skips the detail volume's lookup.

The light march is the expensive part of the chapter. It runs at every sample
that has cloud, so a 64-step march with 6 light steps reads the density up to
64 × 7 times per ray. Section 14 measures it.

### How much of it turns toward the eye

A droplet does not scatter evenly in all directions. Droplets much larger than
a wavelength of light, as cloud droplets are (about 10 micrometres, against
half a micrometre), scatter mostly *forward*, close to the way the light was
already going. The function that
says how much goes each way is the **phase function**, written *p*. It depends
on one angle, θ (theta), between the direction the light came in along and the
direction it leaves along. For this shader that is the angle between "toward
the sun" and "toward the eye", seen from the sample.

Two facts define it:

- *p*(θ) is a share **per steradian** (Chapter 16 section 2's solid angle):
  of the light a droplet scatters, how much goes into each small cone of
  directions around θ.
- Added up over the whole sphere of directions, the shares make 1. All the
  scattered light goes somewhere.

The even case, the same in every direction, is therefore 1 over the sphere's
solid angle: *p* = 1 / 4π = **0.0796** per steradian.

**Henyey and Greenstein's** phase function (1941, for dust between the stars)
is the standard way to lean that evenness forward or backward with one number,
*g*, between −1 and 1:

$$
p(\theta) = \frac{1}{4\pi} \cdot \frac{1 - g^2}{\big(1 + g^2 - 2g\cos\theta\big)^{3/2}}
$$

*g* = 0 gives back 1/4π. *g* > 0 leans forward, and *g* < 0 backward. The
closer *g* gets to 1, the narrower and brighter the forward peak. A worked
example, for *g* = 0.8, about a cloud droplet's:

| θ | cos θ | 1 + *g*² − 2*g* cos θ | *p*(θ), per steradian | compared with even |
| --- | --- | --- | --- | --- |
| 0° (looking toward the sun) | 1 | 0.04 | 3.58 | 45 times |
| 90° (the sun to your side) | 0 | 1.64 | 0.0136 | a sixth |
| 180° (the sun behind you) | −1 | 3.24 | 0.0049 | a sixteenth |

The light a droplet sends straight on, past the sun's direction, is 730 times
the light it sends straight back. **That is the silver lining.** Look toward the
sun past the edge of a cloud. The thin edge lets sunlight in and lets it out
again toward you, with the phase function at its peak, so the edge blazes. The
thick middle lets almost no sunlight through, and goes dark. Look away from the
sun, and the same cloud is lit from your side but sends you only the backward
share.

**This is `henyeyGreenstein`**, the formula as written. Its `PI` is the first
constant at the top of the shader:

```glsl
const float PI = 3.14159265359;
```

```glsl
float henyeyGreenstein(float cosAngle, float g)
{
    float denominator = 1.0 + g * g - 2.0 * g * cosAngle;
    return (1.0 - g * g) / (4.0 * PI * denominator * sqrt(denominator));
}
```

**Two lobes.** One forward lobe alone leaves a cloud with the sun behind you
far too dark: 0.0049 per steradian is almost nothing. Real droplets do send
some light backward, and, more importantly, light that bounces many times
inside a cloud comes back out of the side it went in. Section 11 deals with the
second properly. The usual first step is a **second, backward lobe**, mixed in
with a small share. **This is `cloudPhase`**:

```glsl
float cloudPhase(float cosAngle, float sharpness)
{
    return mix(henyeyGreenstein(cosAngle,  clouds.forwardG * sharpness),
               henyeyGreenstein(cosAngle, -clouds.backwardG * sharpness), clouds.backwardShare);
}
```

With the defaults, a forward lobe of *g* = 0.8 and a backward lobe of
*g* = −0.3 taking 30%, here is the arithmetic for both directions:

- **Straight back:** 0.7 × 0.0049 + 0.3 × 0.211 = **0.067**, fourteen times the
  single lobe's.
- **Straight forward:** 0.7 × 3.58 + 0.3 × 0.033 = 2.52, still a strong peak.

The `sharpness` argument is section 11's. For now it is 1. The panel's
**Forward g**, **Backward g**, and **Backward share** are these three numbers.

### Putting them together

**This is `sunLight`, as Part 1 has it**: the light one sample scatters toward
the eye per unit of optical depth. It is the sun's irradiance, times the
transmittance from the sun, times the phase function. Section 11 replaces it
with a loop that adds the light that scattered more than once:

```glsl
vec3 sunLight(float opticalDepth, float cosAngle)
{
    return clouds.sunIrradiance.rgb * exp(-opticalDepth) * cloudPhase(cosAngle, 1.0);   // Part 1: section 11 replaces this
}
```

Its result is a radiance in the scene's units: an irradiance (lux) times a
phase function (per steradian). That is the same unit as the sky and as
every lit surface since Chapter 16, so the clouds, the sky, and the scene all
take the same exposure and tone curve.

### The sky's light

The sun is not the only light. The whole blue dome of the sky shines on the
clouds from above, and that light is what fills a cloud's shaded side with
blue-grey rather than black. Chapter 23's cube holds exactly that sky, so the
march reads it. **This is `skyAmbient`**:

```glsl
vec3 skyAmbient()
{
    vec3 sum = texture(skyCube, vec3(0.0, 1.0, 0.0)).rgb;
    sum += texture(skyCube, normalize(vec3( 1.0, 0.577,  0.0))).rgb;
    sum += texture(skyCube, normalize(vec3(-1.0, 0.577,  0.0))).rgb;
    sum += texture(skyCube, normalize(vec3( 0.0, 0.577,  1.0))).rgb;
    sum += texture(skyCube, normalize(vec3( 0.0, 0.577, -1.0))).rgb;
    return sum / 5.0;
}
```

A droplet lit evenly from every direction of a sky of radiance *L*, scattering
evenly, sends *L* toward the eye: the phase function adds up to 1 over the
sphere (above). So the in-scattered sky light per unit of optical depth is
just the sky's average radiance. Five lookups estimate the average over the
upper half: straight up, and four at 30° above the horizon (`0.577` is
tan 30°). The cube's exposure is already in it.

A point near a cloud's base sees less sky than a point near its top, because
the cloud above blocks it. `marchClouds` scales the ambient term by
`mix(0.3, 1.0, height)`: 30% at the base of the layer, all of it at the top.
That is the crudest stand-in for the sky's own light march, and cheap.

### Into the march

`marchClouds` can now light its steps. Before the loop, after the line that
jitters `t`, add the two things that are the same at every step of a ray, the
angle the phase function needs and the sky's light:

```glsl
    float cosAngle = dot(direction, clouds.toSun.xyz);
    vec3  ambient  = skyAmbient();
```

and in the loop, replace Part 1's `vec3 scattered = vec3(0.0);` with the
sunlight and the sky's light, the second scaled by the height:

```glsl
        // Section 6: the sky lights the top of a cloud more than its base, which the cloud above shades.
        float height    = (p.y - clouds.bottom) / (clouds.top - clouds.bottom);
        vec3  scattered = sunLight(opticalDepthToSun(p, footprint), cosAngle) + ambient * mix(0.3, 1.0, height);
```

The step's share of `scattered` is section 3's: `(1 − e^−σΔs)`, dimmed by the
transmittance in front of it.

## Checkpoint

With **Uniform layer** still ticked, set **View** back to "Shaded" and
**Extinction** to 0.001, put the sun about 25° up (the USD viewer's Sun
sliders), and look a little above the horizon:

- **The test with a known answer** reads 163 straight up in the Transmittance
  view, and 103 at twice the extinction (section 5).
- **Toward the sun, the layer glows.** On Raw the glow clips to a white blot
  around the sun's direction. Switch the curve to ACES and it becomes a broad
  halo, bright in the middle and fading over tens of degrees: the phase
  function's forward peak.
- **Drag "Forward g" to 0.95** and the halo tightens into a bright spot around
  the sun. Drag it to 0 and it spreads into an even brightening of the whole
  layer.
- **Turn away from the sun** and the layer is an even, dull lavender-grey,
  lit by the backward lobe and the sky.
- **Raise the extinction to 0.01** and the layer becomes a dark grey overcast.
  The sun and its disk are gone: the rays toward it stop early and count as
  opaque.

---

# Part 2 — Shape (sections 7-10)

Part 1's slab is a cloud with no shape. Part 2 gives it one, the way *Horizon
Zero Dawn* does (Andrew Schneider's 2015 and 2017 talks). Three images of noise
are made once, at start-up, and the density at a point is assembled from them:

- **a weather map**, seen from above: where clouds may grow and which kind;
- **a shape volume**, 3D: the heaps and billows;
- **a detail volume**, also 3D, much smaller: the ragged edges.

## 7. Noise that tiles, in three dimensions

**Why noise in an image rather than noise in the march?** Section 6's march
reads the density up to 64 × 7 = 448 times per ray. The shape's noise below
costs several hundred hash calls per point: four octaves of Worley noise at 27
cells each, and four of gradient noise at 8 corners each. Computed in the
march, that would be hundreds of thousands of hashes per ray. Read from an image, it is one
filtered lookup. So the noise is computed once, into **3D images**, and the
march samples them like textures.

> **Jump:** a 3D image is a stack of 2D images, one per depth slice, read with
> three coordinates instead of two. Everything Chapter 15 said about 2D
> textures carries over: formats, samplers, mips, linear filtering. Each just
> gains a third direction. A linear filter now blends the eight texels around a
> point instead of four, and a mip level halves the depth as well as the width
> and height. Keep in mind that the third direction is what makes these images
> expensive, which is the next thing to work out.

### What a 3D image costs

A 2D texture of side *n* holds *n*² texels. A 3D one holds *n*³, so doubling
its side multiplies its memory by eight, not four. With four bytes per texel
(`R8G8B8A8_UNORM`):

| Image | Texels | Memory | With mips |
| --- | --- | --- | --- |
| Shape volume, 128³ | 2,097,152 | 8 MiB | 9.1 MiB |
| Detail volume, 32³ | 32,768 | 128 KiB | 146 KiB |
| Weather map, 512² (2D) | 262,144 | 1 MiB | no mips |
| *For comparison:* a 256³ shape volume | 16,777,216 | 64 MiB | 73 MiB |
| *For comparison:* the cloud cube, 256² × 6 at 8 bytes | 393,216 | 3 MiB | — |

**The mip chain of a 3D image costs a seventh more**, against a third for a 2D
image. Each 2D level has a quarter of the texels of the one above, so the chain
adds 1/4 + 1/16 + 1/64 + ... = 1/3. Each 3D level has an *eighth*, so it adds
1/8 + 1/64 + 1/512 + ... = 1/7. That is why the shape volume's 8 MiB becomes
9.1 MiB, not 10.7.

All three images are `R8G8B8A8_UNORM`. Two reasons decide that:

- It is on the short list of formats every device can use as a storage image
  (Chapter 20 section 4), which the generation passes need.
- Every device can also blit it with linear filtering, which the mip chain
  needs (Chapter 15 section 5).

Eight bits per channel is plenty for noise, which nobody looks at directly.
`R8_UNORM` would be a quarter of the size, but it is a storage format only with
the `shaderStorageImageExtendedFormats` feature, and the shape volume uses all
four channels anyway.

### Worley noise, in three dimensions

Chapter 27 section 1 put one jittered point in each square of a grid and
found, for any position, the nearest of them. That made Voronoi cells.
**Worley noise** is the *distance* to that nearest point, written *F*1. In
three dimensions the grid has cubes instead of squares, and the nearest point
is almost always in the position's own cube or one of the 26 around it, so the
search covers 27 cubes instead of 9.

*F*1 is 0 at each point and grows toward the cell walls. Turned upside down,
1 − *F*1, it is a lattice of round, bright blobs with dark seams between them.
That looks like the bulges on the top of a cumulus, which is why clouds use
**inverted Worley noise**. A slice through it, at about 4 cells across:

```text
   F1 (distance to the nearest point)        1 - F1 (inverted: what clouds use)
   ..::--==##==--::....::--==##==--::        ##==--::..::--==##==--::..::--==##
   ::--==##==--::.  .::--==####==--::        ==--::.    .::--==--::.    .::--==
   --==##==--::.  *  .::--==##==--::.        --::.   ##   .::--::.   ##   .::--
   ::--==##==--::.  .::--==####==--::        ==--::.    .::--==--::.    .::--==
   ..::--==##==--::....::--==##==--::        ##==--::..::--==##==--::..::--==##
         * = a point                               ## around each point: a blob
```

### Noise that tiles

The shape volume covers 8 km of the world. The sampler repeats it beyond that
(`REPEAT`), so the noise must repeat too, or a seam runs through the sky every
8 km. Noise repeats when its *lattice* repeats: when the point in cell
`period` is the point in cell 0. So every cell coordinate is wrapped into
0 to `period` − 1 before it is hashed. A worked example, with a period of 4:

| Cell | Wrapped | So its point is the point of cell |
| --- | --- | --- |
| −1 | 3 | 3: the left neighbour of cell 0 is the last cell |
| 0 | 0 | 0 |
| 3 | 3 | 3 |
| 4 | 0 | 0: the right neighbour of cell 3 is the first cell |

The volume holds exactly one period across its width, so its left face
continues its right face exactly. Only the hash is wrapped. A neighbouring
cell's point still sits at its own unwrapped position, `vec3(cell)` plus its
jitter, because the distance is measured in the unwrapped space around the
position.

How many metres of the world one repeat of each image covers is the march's
choice, three constants at the top of the march shader, under `PI`. The
weather map (section 8) is the third:

```glsl
// Section 7: how many metres of the world one repeat of each image covers.
const float SHAPE_SCALE   = 8000.0;
const float DETAIL_SCALE  = 700.0;
const float WEATHER_SCALE = 40000.0;
```

### Gradient noise, in three dimensions

Chapter 27 section 2's gradient noise puts a random unit vector at each corner
of a square, takes each corner's vector dotted with the offset to the
position, and blends the four ramps with the quintic fade curve. In three
dimensions a cube has eight corners, blended along x, then y, then z. The random
unit vectors are Chapter 21 section 3's directions spread evenly over a whole
sphere: cos θ uniform from −1 to 1, and the angle around the axis uniform.

**This is `Shaders/Clouds/CloudNoise.glsl`**, both noises, tileable, as an
include:

```glsl
// Shaders/Clouds/CloudNoise.glsl - Chapter 28. Noise that tiles: Worley noise (the distance
// to the nearest of a set of scattered points) and three-dimensional gradient noise, on a
// lattice that repeats every `period` cells. Include Random.glsl first.
#ifndef PF_CLOUD_NOISE_GLSL
#define PF_CLOUD_NOISE_GLSL

// The random stream of one lattice cell. The cell is wrapped into 0..period-1 first, so
// cell `period` hashes like cell 0: the noise repeats every period cells, and a volume
// holding exactly one period tiles without a seam. The callers' cells are never below -1,
// so adding one period makes them non-negative: GLSL leaves % of a negative number
// undefined. `seed` gives each use its own points.
uint latticeHash(ivec3 cell, int period, uint seed)
{
    uvec3 wrapped = uvec3(cell + period) % uint(period);
    return pcgHash(wrapped.x ^ pcgHash(wrapped.y ^ pcgHash(wrapped.z ^ seed)));
}

// Worley noise: the distance from p to the nearest feature point, one point per cell,
// in cells. p runs 0..1 across one period. The nearest point is almost always in p's
// own cell or one of the 26 around it, so those 27 are searched (Chapter 27 section 1
// searched 9 in two dimensions). A distance over one cell is rare, and is cut to 1.
float worleyNoise(vec3 p, int period, uint seed)
{
    vec3  q       = p * float(period);
    ivec3 home    = ivec3(floor(q));
    float nearest = 1.0;
    for (int dz = -1; dz <= 1; ++dz)
    {
        for (int dy = -1; dy <= 1; ++dy)
        {
            for (int dx = -1; dx <= 1; ++dx)
            {
                ivec3 cell  = home + ivec3(dx, dy, dz);
                uint  state = latticeHash(cell, period, seed);
                vec3  point = vec3(cell) + vec3(randomFloat(state), randomFloat(state), randomFloat(state));
                nearest = min(nearest, distance(q, point));
            }
        }
    }
    return nearest;
}

// A random unit vector for a lattice point: Chapter 21 section 3's sphere burst, with
// cos(theta) uniform over the whole -1..1 and the angle around the axis uniform.
vec3 latticeGradient(ivec3 point, int period, uint seed)
{
    uint  state    = latticeHash(point, period, seed);
    float cosTheta = 2.0 * randomFloat(state) - 1.0;
    float sinTheta = sqrt(max(0.0, 1.0 - cosTheta * cosTheta));
    float phi      = randomFloat(state) * 6.28318530718;
    return vec3(sinTheta * cos(phi), sinTheta * sin(phi), cosTheta);
}

// Chapter 27 section 2's gradient noise, in three dimensions: eight corners instead of
// four, each contributing its gradient dotted with the offset to p, blended with the
// same quintic along x, then y, then z. About -0.6..0.6; zero at every lattice point.
float gradientNoise(vec3 p, int period, uint seed)
{
    vec3  q    = p * float(period);
    ivec3 cell = ivec3(floor(q));
    vec3  f    = q - vec3(cell);
    vec3  u    = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);

    float n000 = dot(latticeGradient(cell + ivec3(0, 0, 0), period, seed), f - vec3(0.0, 0.0, 0.0));
    float n100 = dot(latticeGradient(cell + ivec3(1, 0, 0), period, seed), f - vec3(1.0, 0.0, 0.0));
    float n010 = dot(latticeGradient(cell + ivec3(0, 1, 0), period, seed), f - vec3(0.0, 1.0, 0.0));
    float n110 = dot(latticeGradient(cell + ivec3(1, 1, 0), period, seed), f - vec3(1.0, 1.0, 0.0));
    float n001 = dot(latticeGradient(cell + ivec3(0, 0, 1), period, seed), f - vec3(0.0, 0.0, 1.0));
    float n101 = dot(latticeGradient(cell + ivec3(1, 0, 1), period, seed), f - vec3(1.0, 0.0, 1.0));
    float n011 = dot(latticeGradient(cell + ivec3(0, 1, 1), period, seed), f - vec3(0.0, 1.0, 1.0));
    float n111 = dot(latticeGradient(cell + ivec3(1, 1, 1), period, seed), f - vec3(1.0, 1.0, 1.0));

    float nearZ = mix(mix(n000, n100, u.x), mix(n010, n110, u.x), u.y);
    float farZ  = mix(mix(n001, n101, u.x), mix(n011, n111, u.x), u.y);
    return mix(nearZ, farZ, u.z);
}

// Octaves (Chapter 27 section 2): each one twice the frequency and half the weight of the
// one before, divided by the total weight so the range stays that of one octave or less.
// The period doubles with the frequency, so every octave still tiles.
float gradientFbm(vec3 p, int period, int octaves, uint seed)
{
    float sum    = 0.0;
    float weight = 1.0;
    float total  = 0.0;
    for (int octave = 0; octave < octaves; ++octave)
    {
        sum    += weight * gradientNoise(p, period << octave, seed + uint(octave));
        total  += weight;
        weight *= 0.5;
    }
    return sum / total;
}

#endif
```

`gradientFbm` is Chapter 27's octaves: each octave doubles the frequency and
halves the weight. Here the *period* doubles too, `period << octave`, so every
octave still repeats exactly once across the volume. One octave of 3D gradient
noise mostly stays within about ±0.6. Four octaves, divided by their total
weight, mostly stay within ±0.25, which is why the shaders below scale it by
2 and shift it by 0.5 to fill 0 to 1.

### Perlin-Worley

Inverted Worley noise makes good blobs but a poor sky: each blob is round and
on its own. Gradient noise makes connected, rolling masses, but they are smooth
and have no bulges. Schneider's **Perlin-Worley** noise combines them so that
the result is high wherever *either* one is high:

$$
\text{perlinWorley} = w + p \, (1 - w)
$$

with *w* the inverted Worley value and *p* the gradient noise, both 0 to 1. In
words, start from the Worley blob, and fill the rest of the way up to 1 in
proportion to the gradient noise. Worked:

- Inside a blob, *w* = 0.8 and *p* = 0.5 give 0.8 + 0.5 × 0.2 = **0.9**. The
  blob stays a blob.
- In a seam between blobs, *w* = 0.1 and *p* = 0.5 give 0.1 + 0.5 × 0.9 =
  **0.55**. The gradient noise bridges the seam.

You may see this written `remap(p, 0, 1, w, 1)`, a remap (section 9) of the
gradient noise into the range from *w* to 1. It is the same formula.

**This is `CloudShapeNoise.comp.glsl`.** One invocation per texel of the
128³ volume, 4 × 4 × 4 to a workgroup. That is 64 invocations, Chapter 20's
size, in three dimensions.

```glsl
// Shaders/Clouds/CloudShapeNoise.comp.glsl - Chapter 28 section 7. Fills the 128^3 shape
// volume once, at setup. Every channel holds exactly one period of its noise, so the
// volume tiles in all three directions.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "Random.glsl"
#include "CloudNoise.glsl"

layout(local_size_x = 4, local_size_y = 4, local_size_z = 4) in;

layout(set = 0, binding = 0, rgba8) uniform writeonly image3D shapeVolume;

void main()
{
    ivec3 texel = ivec3(gl_GlobalInvocationID);
    ivec3 size  = imageSize(shapeVolume);
    if (any(greaterThanEqual(texel, size))) { return; }   // the dispatch rounds up

    vec3 p = (vec3(texel) + 0.5) / vec3(size);   // 0..1 across the volume

    // R: Perlin-Worley. Inverted Worley at 4 cells is a lattice of round blobs; gradient
    // noise, stretched from about -0.25..0.25 to 0..1, joins them into a connected mass.
    // worley + perlin * (1 - worley) is high wherever either one is.
    float perlin       = clamp(gradientFbm(p, 4, 4, 0u) * 2.0 + 0.5, 0.0, 1.0);
    float worley       = 1.0 - worleyNoise(p, 4, 10u);
    float perlinWorley = worley + perlin * (1.0 - worley);

    // G, B, A: inverted Worley at 8, 16, and 32 cells - billows two, four, and eight times
    // smaller, which the march erodes the blobs with.
    vec4 value = vec4(perlinWorley,
                      1.0 - worleyNoise(p, 8, 11u),
                      1.0 - worleyNoise(p, 16, 12u),
                      1.0 - worleyNoise(p, 32, 13u));
    imageStore(shapeVolume, texel, value);
}
```

- **R is Perlin-Worley**: 4 Worley cells across the volume, so blobs about
  2 km across in the world, and four octaves of gradient noise starting at 4
  cells.
- **G, B, and A are inverted Worley at 8, 16, and 32 cells**, the same kind of
  bulge two, four, and eight times smaller. Section 9 uses them to carve
  billows into the blobs. The finest has 4 texels per cell, the fewest that
  still look round.
- **Each channel has its own `seed`**, so the 32-cell points are not the
  8-cell points scaled down.

**This is `CloudDetailNoise.comp.glsl`**, the same thing for the small
volume's three channels: inverted Worley at 2, 4, and 8 cells. A is unused,
because `RGB8` is not a storage format every device has.

```glsl
// Shaders/Clouds/CloudDetailNoise.comp.glsl - Chapter 28 section 7. Fills the 32^3 detail
// volume once, at setup: inverted Worley at three frequencies, for eroding the edges.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "Random.glsl"
#include "CloudNoise.glsl"

layout(local_size_x = 4, local_size_y = 4, local_size_z = 4) in;

layout(set = 0, binding = 0, rgba8) uniform writeonly image3D detailVolume;

void main()
{
    ivec3 texel = ivec3(gl_GlobalInvocationID);
    ivec3 size  = imageSize(detailVolume);
    if (any(greaterThanEqual(texel, size))) { return; }

    vec3 p = (vec3(texel) + 0.5) / vec3(size);

    // A is unused: RGBA8 is on the storage formats every device supports, RGB8 is not.
    vec4 value = vec4(1.0 - worleyNoise(p, 2, 20u),
                      1.0 - worleyNoise(p, 4, 21u),
                      1.0 - worleyNoise(p, 8, 22u),
                      1.0);
    imageStore(detailVolume, texel, value);
}
```

### The images, and making them

**This is `createNoiseImage`**, one 3D or 2D noise image with its two views,
at the top of the namespace in `Clouds.cpp`:

```cpp
static InitializationResult createNoiseImage(VulkanContext& context, VkExtent3D extent, bool mipmapped,
                                             const char* name, NoiseImage& noise)
{
    const bool volume = extent.depth > 1;
    noise.extent    = extent;
    noise.mipLevels = mipmapped ? std::bit_width(std::max({ extent.width, extent.height, extent.depth })) : 1;

    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = volume ? VK_IMAGE_TYPE_3D : VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R8G8B8A8_UNORM,
        .extent        = extent,
        .mipLevels     = noise.mipLevels,
        .arrayLayers   = 1,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_STORAGE_BIT         // the generation pass writes level 0
                       | VK_IMAGE_USAGE_SAMPLED_BIT         // the march reads every level
                       | VK_IMAGE_USAGE_TRANSFER_SRC_BIT    // each level is the blit source of the next
                       | VK_IMAGE_USAGE_TRANSFER_DST_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(context.allocator, &imageInfo, &allocationInfo, &noise.image, &noise.allocation, nullptr)
        != VK_SUCCESS)
    {
        return InitializationResult::failure(std::format("vmaCreateImage failed for the cloud {}.", name));
    }

    const VkImageViewType viewType = volume ? VK_IMAGE_VIEW_TYPE_3D : VK_IMAGE_VIEW_TYPE_2D;
    const VkImageViewCreateInfo sampledInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = noise.image,
        .viewType         = viewType,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, noise.mipLevels, 0, 1 },
    };
    VkImageViewCreateInfo storageInfo = sampledInfo;
    storageInfo.subresourceRange.levelCount = 1;   // imageStore reaches only a view's base level
    if (vkCreateImageView(context.device, &sampledInfo, nullptr, &noise.view) != VK_SUCCESS ||
        vkCreateImageView(context.device, &storageInfo, nullptr, &noise.storageView) != VK_SUCCESS)
    {
        return InitializationResult::failure(std::format("vkCreateImageView failed for the cloud {}.", name));
    }
    return InitializationResult::success();
}
```

- **The image type follows the depth.** A depth above 1 makes it a 3D image,
  `VK_IMAGE_TYPE_3D` with a `3D` view. The weather map is a 2D image made by
  the same function.
- **`std::bit_width` of the largest side** is Chapter 15's level count: 8
  levels for 128, from 128³ down to 1³.
- **Two views.** `view` covers every level and is what the march samples.
  `imageStore` can reach only the base level of the view it is given, so
  `storageView` covers level 0 alone, which is what the generation shader
  writes. One view would work, but this way each binding names exactly what it
  touches. The blits fill the other levels.
- **Four usages:** storage for the generation, sampled for the march, and
  transfer source and destination for the blits.

`destroyNoiseImage`, beside it, destroys both views and the image and resets
the struct. It is in Appendix A.

**This is `blitMipChain`**, Chapter 15 section 5's chain in three dimensions:

```cpp
static void blitMipChain(VkCommandBuffer commandBuffer, const NoiseImage& noise)
{
    int32_t width  = static_cast<int32_t>(noise.extent.width);
    int32_t height = static_cast<int32_t>(noise.extent.height);
    int32_t depth  = static_cast<int32_t>(noise.extent.depth);
    for (uint32_t level = 1; level < noise.mipLevels; ++level)
    {
        // The level above was just written - by the generation pass or the last blit - and is read now.
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT,
                      VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT | VK_ACCESS_2_TRANSFER_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);

        const int32_t nextWidth  = std::max(width / 2, 1);
        const int32_t nextHeight = std::max(height / 2, 1);
        const int32_t nextDepth  = std::max(depth / 2, 1);
        const VkImageBlit blit{
            .srcSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, level - 1, 0, 1 },
            .srcOffsets     = { { 0, 0, 0 }, { width, height, depth } },
            .dstSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, level, 0, 1 },
            .dstOffsets     = { { 0, 0, 0 }, { nextWidth, nextHeight, nextDepth } },
        };
        vkCmdBlitImage(commandBuffer, noise.image, VK_IMAGE_LAYOUT_GENERAL, noise.image, VK_IMAGE_LAYOUT_GENERAL,
                       1, &blit, VK_FILTER_LINEAR);
        width  = nextWidth;
        height = nextHeight;
        depth  = nextDepth;
    }
}
```

It differs from Chapter 15's in two ways:

- **Depth halves too.** Each blit's offsets have a third component, and a
  linear blit of a 3D image averages 2 × 2 × 2 texels into one.
- **Every level stays in `GENERAL`.** A blit may read from and write to
  `GENERAL` as well as the two transfer layouts. Leaving the whole image in one
  layout turns Chapter 15's three transitions per level into one global memory
  barrier per level, `memoryBarrier` from Chapter 20 section 5. The three
  questions for it:
  - Q1: the level above was written by the generation's `COMPUTE_SHADER`, or by
    the previous `BLIT`. Both come before this `BLIT`.
  - Q2: its `SHADER_STORAGE_WRITE` or `TRANSFER_WRITE`, made visible to this
    blit's `TRANSFER_READ`.
  - Q3: no layout changes.

**This is `CreateNoise`**: the three images, the one sampler the march reads
all three through, the generation, and the march's three bindings that
`CreateDescriptors` left empty.

```cpp
InitializationResult Clouds::CreateNoise()
{
    if (auto result = createNoiseImage(m_context, { CLOUD_SHAPE_SIZE, CLOUD_SHAPE_SIZE, CLOUD_SHAPE_SIZE }, true,
                                       "shape volume", m_shape); !result)        { return result; }
    if (auto result = createNoiseImage(m_context, { CLOUD_DETAIL_SIZE, CLOUD_DETAIL_SIZE, CLOUD_DETAIL_SIZE }, true,
                                       "detail volume", m_detail); !result)      { return result; }
    if (auto result = createNoiseImage(m_context, { CLOUD_WEATHER_SIZE, CLOUD_WEATHER_SIZE, 1 }, false,
                                       "weather map", m_weather); !result)       { return result; }

    // Linear between texels and between mip levels, and repeating: every image holds whole periods of
    // its noise, so the world can be tiled with it.
    const VkSamplerCreateInfo samplerInfo{
        .sType        = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter    = VK_FILTER_LINEAR,
        .minFilter    = VK_FILTER_LINEAR,
        .mipmapMode   = VK_SAMPLER_MIPMAP_MODE_LINEAR,
        .addressModeU = VK_SAMPLER_ADDRESS_MODE_REPEAT,
        .addressModeV = VK_SAMPLER_ADDRESS_MODE_REPEAT,
        .addressModeW = VK_SAMPLER_ADDRESS_MODE_REPEAT,
        .maxLod       = VK_LOD_CLAMP_NONE,
    };
    if (vkCreateSampler(m_context.device, &samplerInfo, nullptr, &m_noiseSampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the cloud noise.");
    }

    if (auto result = GenerateNoise(); !result) { return result; }

    // The march's bindings 1 to 3, which CreateDescriptors left for here.
    const VkDescriptorImageInfo shape{ .sampler = m_noiseSampler, .imageView = m_shape.view,
                                       .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
    const VkDescriptorImageInfo detail{ .sampler = m_noiseSampler, .imageView = m_detail.view,
                                        .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
    const VkDescriptorImageInfo weather{ .sampler = m_noiseSampler, .imageView = m_weather.view,
                                         .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
    const VkWriteDescriptorSet writes[] = {
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_marchSet, .dstBinding = 1,
          .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &shape },
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_marchSet, .dstBinding = 2,
          .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &detail },
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_marchSet, .dstBinding = 3,
          .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &weather },
    };
    vkUpdateDescriptorSets(m_context.device, 3, writes, 0, nullptr);
    return InitializationResult::success();
}
```

The sampler filters linearly between texels *and* between mip levels, and it
repeats in all three directions. Every image holds whole periods of its noise,
so repeating is what tiles the world with it.

**This is `GenerateNoise`.** The generation runs once, so the function builds
its own set layout, pool, and three pipelines, uses them, and destroys them
before it returns. Its first half is Chapter 20's pattern, once for each
shader, and is in Appendix A. The third shader, the weather map's, is the next
section's: add the `CreateNoise` line to `Initialize` once section 8 has
written it. Three things in it are worth knowing:

- **One set layout serves all three shaders**, a single storage image at
  binding 0. A storage image descriptor does not say whether its image is 2D
  or 3D; the view does.
- **A `release` lambda cleans up on every path**: whatever was created by the
  time something fails, and everything at the end. Destroying a null handle
  does nothing, so it can run at any point.
- **A timer of its own.** `timer` is a `GpuTimestamps` of two (section 14),
  initialized just before the submission. `release` shuts it down with the
  rest.

The second half records the work in one `immediateSubmit` and waits for it:

```cpp
    immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
        timer.Reset(commandBuffer, 0);
        timer.Write(commandBuffer, 0, 0);

        // Every level of every image to GENERAL: the shaders write level 0 there, and blits may read and
        // write GENERAL too, so nothing changes layout again until the end. The first writers are the
        // dispatches (level 0) and the blits (every other level), so both wait for this transition.
        for (const NoiseImage* image : images)
        {
            transitionImage(commandBuffer, image->image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                            VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                            VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT,
                            VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT | VK_ACCESS_2_TRANSFER_WRITE_BIT);
        }

        // One invocation per texel: 4 x 4 x 4 groups for the volumes, 8 x 8 for the map.
        constexpr uint32_t VOLUME_GROUP = 4;
        constexpr uint32_t MAP_GROUP    = 8;
        const uint32_t groups[3][3] = {
            { groupCount(CLOUD_SHAPE_SIZE, VOLUME_GROUP), groupCount(CLOUD_SHAPE_SIZE, VOLUME_GROUP), groupCount(CLOUD_SHAPE_SIZE, VOLUME_GROUP) },
            { groupCount(CLOUD_DETAIL_SIZE, VOLUME_GROUP), groupCount(CLOUD_DETAIL_SIZE, VOLUME_GROUP), groupCount(CLOUD_DETAIL_SIZE, VOLUME_GROUP) },
            { groupCount(CLOUD_WEATHER_SIZE, MAP_GROUP), groupCount(CLOUD_WEATHER_SIZE, MAP_GROUP), 1 },
        };
        for (size_t i = 0; i < 3; ++i)
        {
            vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, pipelines[i]);
            vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, pipelineLayout,
                                    0, 1, &sets[i], 0, nullptr);
            vkCmdDispatch(commandBuffer, groups[i][0], groups[i][1], groups[i][2]);
        }

        blitMipChain(commandBuffer, m_shape);
        blitMipChain(commandBuffer, m_detail);

        // Done: every level, written by a dispatch or a blit, becomes something the march samples.
        for (const NoiseImage* image : images)
        {
            transitionImage(commandBuffer, image->image, VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                            VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT,
                            VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT | VK_ACCESS_2_TRANSFER_WRITE_BIT,
                            VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
        }

        timer.Write(commandBuffer, 0, 1);
    });

    // immediateSubmit waited for its fence, so both timestamps are final.
    if (timer.Read(0))
    {
        m_timings.generateMs = timer.Milliseconds(0, 1);
        Log::info(std::format("Clouds: the noise took {:.1f} ms on the GPU.", m_timings.generateMs).c_str());
    }
    release();
    return InitializationResult::success();
}
```

The three questions for its two image barriers:

- **Before the dispatches**, every level of every image goes from `UNDEFINED`
  to `GENERAL`.
  - Q1: nothing came before.
  - Q2: nothing to flush.
  - Q3: `UNDEFINED`, because every texel is about to be written.

  The destination is the subtle part, and synchronization validation is what
  points it out. Level 0's first writer is a `COMPUTE_SHADER`, but every other
  level's first writer is a `BLIT`. Name only the compute stage, and the
  layout transition is not ordered before the blits. The layer reports a
  `SYNC-HAZARD-WRITE-AFTER-WRITE` on every `vkCmdBlitImage`: the blit writes a
  level that the transition was still writing. Hence `COMPUTE_SHADER | BLIT`
  and `SHADER_STORAGE_WRITE | TRANSFER_WRITE`.
- **After the blits**, `GENERAL` to `SHADER_READ_ONLY_OPTIMAL`.
  - Q1: the dispatches and the blits before the march's `COMPUTE_SHADER`.
  - Q2: both kinds of write, made visible to `SHADER_SAMPLED_READ`.
  - Q3: the read-only layout the march's descriptors name.

This is a one-off submission, so these barriers also order every frame
recorded after it (Chapter 20 section 4).

`timer`'s two timestamps bracket the whole submission, and `immediateSubmit`
has waited for its fence, so they are final as soon as it returns. The log
line, `Clouds: the noise took N ms on the GPU`, appears every time a demo with
a sky is set up. A desktop GPU takes a few milliseconds; section 14 says why
this timer is a `GpuTimestamps` of its own.

## 8. The weather map

From above, a sky of cumulus is not uniform. There are clusters and clear
stretches several kilometres across, and in one place the clouds tower while in
another they stay flat. Schneider's **weather map** holds that: a 2D image laid
over the world, saying for each place how cloudy it is and what kind of cloud
grows there.

**This is `CloudWeather.comp.glsl`**, one invocation per texel of a 512² map
covering 40 km:

```glsl
// Shaders/Clouds/CloudWeather.comp.glsl - Chapter 28 section 8. Fills the 2D weather map
// once, at setup: R is how cloudy each place is, G which type of cloud grows there.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "Random.glsl"
#include "CloudNoise.glsl"

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0, rgba8) uniform writeonly image2D weatherMap;

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    ivec2 size  = imageSize(weatherMap);
    if (any(greaterThanEqual(texel, size))) { return; }

    // One slice through the 3D noise: it tiles in x and y, and z stays fixed.
    vec3 p = vec3((vec2(texel) + 0.5) / vec2(size), 0.5);

    float cloudiness = clamp(gradientFbm(p, 4, 5, 30u) * 2.0 + 0.5, 0.0, 1.0);
    float cloudType  = clamp(gradientFbm(p, 2, 3, 40u) * 2.0 + 0.5, 0.0, 1.0);
    imageStore(weatherMap, texel, vec4(cloudiness, cloudType, 0.0, 1.0));
}
```

It is a slice through section 7's 3D noise at a fixed z. That tiles in x and y
for free and needs no 2D noise of its own.

- **R, cloudiness:** five octaves of gradient noise starting at 4 cells, so
  patches of about 10 km, with structure down to a few hundred metres.
- **G, cloud type:** three octaves starting at 2 cells, so whole regions of the
  map share a type, changing over 20 km.

**Coverage.** The panel's **Coverage**, *c*, from 0 to 1, slides the whole
map's cloudiness up or down. Here is what each place gets:

$$
\text{cover} = \operatorname{clamp}(w + 2c - 1,\; 0,\; 1)
$$

for a weather value *w*. Worked, at a place where the map says *w* = 0.6:

| *c* | cover | What the sky does |
| --- | --- | --- |
| 0 | clamp(−0.4) = 0 | nothing grows anywhere |
| 0.35 ("Clear") | 0.3 | only the cloudiest places hold small clouds |
| 0.5 ("Scattered") | 0.6 | the map as it was made |
| 0.85 ("Overcast") | clamp(1.3) = 1 | everywhere is as cloudy as it gets |

At *c* = 0.5 the map is unchanged. Below that everything sinks, and the
emptier places drop to zero first. Above it everything rises, and the cloudier
places reach 1 first.

**This is `weatherAt`** in the march, which reads the map and applies the
coverage and the type. It reads the map where the wind has carried it to, by
an offset that section 10 explains; the offset is one line, so write it now,
above `weatherAt`:

```glsl
vec3 windOffset()
{
    return vec3(clouds.wind.x, 0.0, clouds.wind.y) * clouds.toSun.w;
}
```

```glsl
vec2 weatherAt(vec3 p)
{
    vec2 weather  = textureLod(weatherMap, (p.xz - windOffset().xz) / WEATHER_SCALE, 0.0).rg;
    float cover   = clamp(weather.r + 2.0 * clouds.coverage - 1.0, 0.0, 1.0);
    float type    = clouds.cloudType < 0.0 ? weather.g : clouds.cloudType;
    return vec2(cover, type);
}
```

The map is read at `p.xz` minus the wind's offset and divided by its 40 km,
`WEATHER_SCALE` from section 7. **Type from weather map** on the panel uses the map's G. Untick it,
and the **Type** slider sets one type everywhere, which reaches the shader as
`cloudType` 0 to 1. A negative `cloudType` means "from the map".

**The three buttons.** "Clear", "Scattered", and "Overcast" are starting points
that set the coverage and the type together, from `drawCloudPanel`
(Appendix A):

| Button | Coverage | Type |
| --- | --- | --- |
| Clear | 0.35 | cumulus everywhere (1.0) |
| Scattered | 0.5 | from the weather map |
| Overcast | 0.85 | mostly stratus (0.3) |

**The Coverage view.** In `debugView`, replace Part 1's last line,
`return vec4(0.0, 0.0, 0.0, 1.0);`, with these. They find where the ray meets
the cloud base, and show the weather there; the last line is the density
slice's, which section 9 replaces:

```glsl
    float altitude = clouds.debugView == CLOUD_VIEW_COVERAGE ? clouds.bottom : clouds.sliceAltitude;
    float t        = (altitude - eye.y) / direction.y;
    if (t > MARCH_REACH) { return vec4(0.0, 0.0, 0.0, 1.0); }
    vec3 p = eye + direction * t;
    if (clouds.debugView == CLOUD_VIEW_COVERAGE) { return vec4(weatherAt(p), 0.0, 1.0); }
    return vec4(0.0, 0.0, 0.0, 1.0);   // section 9 replaces this with the density slice
```

`altitude` is the cloud base for this view and the panel's slice altitude for
section 9's; `t` is section 3's distance to it. Set **View** to "Coverage".
Each ray now shows the map where it meets the cloud base: red for cover, green
for type. Yellow is high in
both, and dark is low in both. Looking up, you see only a few kilometres of the
map, so it is one smooth color. Look toward the horizon instead, where a view
takes in tens of kilometres: the patches appear, squeezed flat by perspective,
with a black band just above the horizon where the base is further away than
the march reaches (section 12). Drag **Coverage** down and the red drains out.

## 9. The density

Everything is now in place to replace the slab. `cloudDensity` builds the
density at a point in four steps, each a line or two. Together they replace
Part 1's last line, `return 0.0;`, in the order they come below:

1. **The shape:** Perlin-Worley blobs, carved by their own smaller billows.
2. **The type:** a profile over height, so each kind of cloud has its own
   thickness.
3. **The coverage:** only as much of the shape as the weather allows.
4. **The edges:** eroded by the detail volume.

One small tool does most of the work.

### Remapping

A **remap** takes a value in one range and moves it, in proportion, to
another. This chapter only ever maps a range [*low*, *high*] onto [0, 1], and
clamps:

$$
\operatorname{remap01}(x, \text{low}, \text{high}) = \operatorname{clamp}\!\left(\frac{x - \text{low}}{\text{high} - \text{low}},\; 0,\; 1\right)
$$

Worked: remap01(0.6, 0.2, 1.0) = (0.6 − 0.2) / 0.8 = **0.5**. A value at
*low* becomes 0, one at *high* becomes 1, and everything below *low* is cut to
0. That cut is what makes remap useful for clouds. Raising *low* eats away
whatever is thin, and stretches what is left back to the full range.

**This is `remap01`**, at the top of the march shader with the other helpers:

```glsl
float remap01(float value, float low, float high)
{
    return clamp((value - low) / (high - low), 0.0, 1.0);
}
```

### Step 1 — the shape

The shape volume's G, B, and A are three octaves of inverted Worley noise. Add
them with weights 0.625, 0.25, and 0.125, which sum to 1, and you get one
**billows** value. It is near 1 at the centre of a small bulge and lower in the
creases between bulges. The shape is the Perlin-Worley channel, remapped with
*low* raised where the billows are low:

```glsl
    vec3  shapePosition = p - windOffset();
    float shapeLod      = log2(max(footprint / SHAPE_TEXEL, 1.0));
    vec4  shape         = textureLod(shapeVolume, shapePosition / SHAPE_SCALE, shapeLod);
    float billows       = shape.g * 0.625 + shape.b * 0.25 + shape.a * 0.125;
    float density       = remap01(shape.r, (1.0 - billows) * clouds.billows, 1.0);
```

Worked, with the panel's **Billows** at 0.5 and a Perlin-Worley value of 0.7:

- At the centre of a bulge, billows 0.8, *low* = (1 − 0.8) × 0.5 = 0.1, and
  the shape is (0.7 − 0.1) / 0.9 = **0.67**.
- In a crease, billows 0.2, *low* = 0.4, and the shape is (0.7 − 0.4) / 0.6 =
  **0.5**.

So the creases are thinner, and once coverage cuts the thin parts away (step
3), the surface breaks into bulges: the cauliflower look of a cumulus.
**Billows** at 0 turns it off.

`shapeLod` is the mip level to read, which the end of this section explains.

### Step 2 — the type, a profile over height

A stratus is a flat sheet a few hundred metres thick. A cumulus rises from a
flat base into a tower that can fill the layer. Schneider describes each type by
how its density changes from the base of the layer to the top, and blends
between types by the weather map's G. Here each type is four heights, as
fractions of the layer from 0 at the base to 1 at the top. The density rises
from 0 to full between the first two and falls back to 0 between the last two.

For the default layer, 1500 to 4000 m, that is:

| Type | Four heights, as fractions | Full between | Gone above | In words |
| --- | --- | --- | --- | --- |
| Stratus | 0, 0.05, 0.10, 0.25 | 125 and 250 m | 625 m | a flat sheet a few hundred metres thick |
| Stratocumulus | 0, 0.10, 0.30, 0.50 | 250 and 750 m | 1250 m | a lumpy layer about a kilometre deep |
| Cumulus | 0, 0.10, 0.60, 0.95 | 250 and 1500 m | 2375 m | a tower that fills most of the layer |

(The heights in metres are above the base.) One profile, drawn with height
upward:

```text
   height in the layer
   1.00 ┤
   0.95 ┤╮                    gone: nothing above 0.95
        │ ╲                   falls: a smoothstep from 1 back to 0
   0.60 ┤  │
        │  │                  full: the shape is kept whole
   0.10 ┤  │
        │ ╱                   rises: a smoothstep from 0 to 1
   0.00 ┼╯─┴─────────▶ the share of the shape kept: 0 at the axis, 1 at the line
          a cumulus: 0, 0.10, 0.60, 0.95
```

**This is `heightProfile`**, with the three types as constants:

```glsl
const vec4 STRATUS       = vec4(0.0, 0.05, 0.10, 0.25);
const vec4 STRATOCUMULUS = vec4(0.0, 0.10, 0.30, 0.50);
const vec4 CUMULUS       = vec4(0.0, 0.10, 0.60, 0.95);

float heightProfile(float height, float cloudType)
{
    vec4 type = cloudType < 0.5 ? mix(STRATUS, STRATOCUMULUS, cloudType * 2.0)
                                : mix(STRATOCUMULUS, CUMULUS, cloudType * 2.0 - 1.0);
    return smoothstep(type.x, type.y, height) * (1.0 - smoothstep(type.z, type.w, height));
}
```

- **Between types, the four heights blend.** A type of 0.25, halfway from
  stratus to stratocumulus, gets the heights halfway between theirs, so
  types change smoothly across the weather map.
- **The edges are `smoothstep`** (Chapter 16 section 5), not straight ramps,
  so the base of a cloud is flat-ish and soft rather than a hard cut.
- **The numbers are fractions of the layer**, so changing the panel's altitude
  range stretches every type with it. A 2.5 km layer gives a stratus about
  500 m thick and a cumulus about 2 km tall.

### Step 3 — the coverage

Section 8 gave each place a cover from 0 to 1. The shape, times its profile,
is also 0 to 1. Schneider applies the cover with a remap whose *low* is
1 − cover, and then multiplies by cover so that thin coverage also gives thin
cloud. Written out, those two operations simplify to one subtraction:

$$
\text{density} = \max(\text{shape} + \text{cover} - 1,\; 0)
$$

Worked, at a point where the shape (times its profile) is 0.8:

| cover | density | |
| --- | --- | --- |
| 1.0 | 0.8 | all of the shape, as dense as it gets |
| 0.6 | 0.4 | the shape, thinned |
| 0.3 | 0.1 | only the densest cores, and those thin |
| 0.15 | 0 | nothing: 0.8 + 0.15 − 1 is below zero |

Low coverage keeps only the places where the shape is near 1, the middles of
the blobs. That is why a clear sky's clouds are small and round, not large and
faint. In the code, after `weatherAt` reads the map, it is two lines: the
profile and the subtraction.

```glsl
    vec2 weather = weatherAt(p);
    density *= heightProfile(height, weather.y);
    density  = max(density + weather.x - 1.0, 0.0);
    if (!withDetail || density <= 0.0) { return density; }
```

The last line returns early for the light march (section 6), which skips the
edges. It also returns early wherever there is no cloud at all, which is most
of the sky, before the detail volume's lookup costs anything.

### Step 4 — the edges

The shape volume's smallest bulge is 250 m across. Real cloud edges are ragged
at a few tens of metres. The **detail volume** carries that: 32³ texels
repeating every 700 m, about 22 m per texel. It erodes the edges with the same
remap trick, raising *low* where its own Worley sum is low:

```glsl
    // The edges, eaten by small Worley noise that drifts a little faster than the shape, so the edges
    // churn while the clouds hold together (section 10). Its own mip level: its texels are smaller.
    float detailLod = log2(max(footprint / DETAIL_TEXEL, 1.0));
    vec3  detail    = textureLod(detailVolume, (p - 1.5 * windOffset()) / DETAIL_SCALE, detailLod).rgb;
    float wisps     = detail.r * 0.625 + detail.g * 0.25 + detail.b * 0.125;
    return remap01(density, (1.0 - wisps) * clouds.erosion, 1.0);
```

The remap only bites where the density is already near *low*. With **Erosion**
at 0.5 the largest *low* is 0.5, and a density of 0.3 at a point where the wisps
are 0.4 has *low* = 0.3. It is eaten entirely. The same density where the wisps
are 0.9 has *low* = 0.05 and becomes (0.3 − 0.05) / 0.95 = 0.26: nearly
untouched. Thick middles survive and thin edges fray, which is what the detail
is for.

### The whole function

The four steps' lines, in order, after Part 1's opening three, are the whole of
`cloudDensity`; Appendix B lists it in place. The shape and the weather divide
by section 7's `SHAPE_SCALE` and `WEATHER_SCALE`, the detail by `DETAIL_SCALE`.

### Which mip level: a footprint, worked out by hand

Far clouds are sampled sparsely: one cube texel sees a wide patch of sky, but
reads the noise at only one point per step. That is the shimmering problem of
Chapter 15 section 5, and mips are the answer again. A fragment shader would
pick the level from its 2 × 2 quad's derivatives. A compute shader has no
quads, so it works the level out itself, from the **footprint**: how wide one
cube texel is at the distance being sampled.

A texel at the centre of a face spans about 2 / `CLOUD_FACE_SIZE` radians: the
face is 2 units wide, seen from 1 unit away, and a small angle in radians is
close to width ÷ distance. So one texel is 2/256 ≈ 0.0078 rad ≈ 0.45°, the
number section 1 quoted. At a distance *t* that angle covers *t* × 2/256
metres. The level is log2 of how many of a volume's texels fit in that width,
and never below 0:

$$
\text{lod} = \log_2 \max\!\left(\frac{t \times \text{TEXEL\_ANGLE}}{\text{texel size in metres}},\; 1\right)
$$

```glsl
const float TEXEL_ANGLE   = 2.0 / float(CLOUD_FACE_SIZE);
const float SHAPE_TEXEL   = SHAPE_SCALE / float(CLOUD_SHAPE_SIZE);
const float DETAIL_TEXEL  = DETAIL_SCALE / float(CLOUD_DETAIL_SIZE);
```

Worked. A shape texel is 8000 / 128 = 62.5 m, and a detail texel
700 / 32 = 21.9 m:

| Distance *t* | Footprint | Shape level | Detail level |
| --- | --- | --- | --- |
| 2 km (overhead) | 16 m | 0 | 0 |
| 10 km | 78 m | 0.32 | 1.8 |
| 30 km | 234 m | 1.9 | 3.4 |

The march computes the footprint once per step, and each volume turns it into
its own level. In `marchClouds`, replace Part 1's footprint line with:

```glsl
        float footprint = t * TEXEL_ANGLE;   // section 9: how wide this texel is, out here
```

The light march passes the same footprint on, so the samples toward the sun
read the same level as the sample they light. Overhead, both volumes read their
sharpest level. Toward the horizon the detail fades first, which is what
distance should do.

**The Density slice view** shows the result without lighting. In `debugView`,
replace section 8's last line with:

```glsl
    return vec4(vec3(cloudDensity(p, true, t * TEXEL_ANGLE)), 1.0);
```

Set **View** to "Density slice" and the **Slice altitude** to 2000 m, and look
up. Each ray shows the density where it crosses that altitude: grey clumps on
black, a horizontal cut through the layer. Untick **Type from weather map**, set the
**Type** to 1, cumulus, and raise the slice to 3200 m: the clumps thin out and
shrink, because 3200 m is 0.68 of the layer, past where a cumulus starts to
fall. With the type from the map, this part of the sky is a mixture that has
nothing left at 3200 m at all.

## 10. Wind

Chapter 27 section 2 moved its gusts across the field by sampling the noise at
`position - velocity × time`: the pattern slides downwind, and every point
sees what has arrived at it. The clouds do the same, with the wind's angle in
Chapter 27's convention, degrees from −Z toward +X. `windOffset`, which section
8 had you write above `weatherAt`, is that offset: the wind's velocity times
the time, along the ground.

`MarchParameters` turns the panel's **Wind** speed and **Blows toward** angle
into the velocity `clouds.wind`, and the time arrives in `toSun.w`. Look back
at `cloudDensity` for where the offset is used:

- **The shape and the weather move together**, both offset by `windOffset()`.
  A cloud keeps its shape and its place in the weather pattern, and the whole
  sky drifts downwind as one.
- **The detail moves 1.5 times as fast.** Its offset is `1.5 * windOffset()`,
  so the small noise slides through each cloud while the cloud holds together,
  and the edges churn and change as they go. Real cloud edges do: they
  evaporate on one side and grow on another faster than the cloud itself
  moves.

At the default 10 m/s a cloud 3 km away crosses about a degree of sky every 5
seconds. That is slow enough that the time-slicing of section 13 cannot be
seen, and fast enough that the sky is visibly alive after a few seconds of
watching.

## Checkpoint

Untick **Uniform layer**, set **Extinction** back to 0.02 and **View** to
"Shaded":

- **"Scattered"** fills the sky with heaps of cumulus a few hundred metres to a
  couple of kilometres across, with grey bases and brighter tops. Fewer, larger
  shapes overhead; many, flattened by perspective, toward the horizon.
- **"Clear"** leaves a few separate clouds with wide blue between them, most
  of them small: only the densest cores of the shape pass the coverage.
- **"Overcast"** closes the sky into a flat grey lid, with a break of blue
  here and there where the weather map dips.
- **The Coverage and Density slice views** show the map and the cut described
  in sections 8 and 9.
- **Leave it running** for half a minute: the clouds drift downwind, and their
  edges change as they go.

---

# Part 3 — Light, finished (sections 11-12)

Part 2's clouds have the right shapes and the wrong brightness. With the sun
behind you they are a dull blue-grey, nothing like the white heaps of a summer
afternoon. Part 3 finds the missing light, and then decides what happens at the
horizon.

## 11. Light that scattered more than once

**What is missing.** Section 6 counted *single scattering*: sunlight that
reaches a point directly, dimmed by the cloud on the way, and scatters once,
toward the eye. Inside a real cloud that is a tiny share of the light. A
photon that enters a cumulus scatters tens or hundreds of times before it
leaves, because the cloud absorbs almost nothing (section 2), so every
scattering only redirects it. Light that has bounced that often has forgotten
where the sun is. It leaves in every direction, much of it back out of the
side it came in through, and that is the white you see on a cloud with the sun
behind you. A thick white cloud reflects roughly as much light as fresh snow:
around 0.8 × *E* / π for a sun of irradiance *E*, Chapter 15 section 9's
Lambertian reflection with an albedo of 0.8. The USD viewer's sun delivers π
times the panel's **Sun color**, (0.90, 0.85, 0.80). A color's *luminance* is
how bright the eye finds it, as one number: 0.2126 R + 0.7152 G + 0.0722 B,
weighted toward green because the eye is most sensitive there. For the sun
color that is 0.86. So at Raw and 0 stops, a white cloud there should reach a
luminance of about 0.8 × 0.86 = **0.68**.

Single scattering alone, which is all Parts 1 and 2 have, falls far short of
that: with the sun behind you, Part 2's clouds are a fraction as bright as
snow.

Simulating every bounce is a path tracer's job (Chapter 33), far too slow
here. The approximation real-time renderers use comes from Magnus Wrenninge's
work on the clouds of *Oz: The Great and Powerful* (2013), which Hillaire's
2016 notes brought to games. It adds a few more copies of single scattering,
called **octaves**, each one standing for light that has scattered more times
than the one before. Three things change from one octave to the next:

| Factor | Each octave | Because light that has scattered more |
| --- | --- | --- |
| energy, *a* | × *a* (the panel's **Octave energy**, 0.8) | has less of the sun's light left in it |
| reach, *b* | × 0.5 on the optical depth | has found its way deeper into the cloud |
| sharpness, *c* | × 0.5 on both lobes' *g* | is less sure which way the sun was |

So octave *i* adds

$$
a^i \; e^{-b^i \tau} \; p_{c^i g}(\theta)
$$

to section 6's single scattering, which is octave 0. Here τ is the optical depth
to the sun, and the phase function's *g* values are scaled by *c*<sup>*i*</sup>.

A worked example shows why this matters. Take a point inside a cloud with an
optical depth of **τ = 8** toward the sun: 400 m of cloud at σ = 0.02. Leave
out the phase function, so only the transmittance part is compared:

| Octave *i* | energy *a*<sup>*i*</sup> | reach: e^−(0.5<sup>*i*</sup> × 8) | product |
| --- | --- | --- | --- |
| 0 (single scattering) | 1 | e^−8 = 0.00034 | 0.00034 |
| 1 | 0.8 | e^−4 = 0.018 | 0.015 |
| 2 | 0.64 | e^−2 = 0.135 | 0.087 |
| 3 | 0.51 | e^−1 = 0.37 | 0.19 |
| 4 | 0.41 | e^−0.5 = 0.61 | 0.25 |
| 5 | 0.33 | e^−0.25 = 0.78 | 0.26 |
| **Sum** | | | **0.80** |

Single scattering brings in 0.00034 of the sun. Six octaves bring in 0.80,
over two thousand times as much, and nearly all of it from the late octaves,
the ones that reach deep. That is the bright inside of a cumulus. Near the
cloud's surface, where τ is small, the extra octaves add much less, so the
edges toward the sun keep section 6's sharp forward peak. With the sharpness
halving each time, the later octaves are nearly even in all directions, which
is what light that has bounced many times should be.

**This is `sunLight`, whole.** It replaces section 6's one line with the loop,
one pass per octave:

```glsl
vec3 sunLight(float opticalDepth, float cosAngle)
{
    float sum       = 0.0;
    float energy    = 1.0;
    float reach     = 1.0;
    float sharpness = 1.0;
    for (uint octave = 0u; octave < clouds.octaves; ++octave)
    {
        sum       += energy * exp(-reach * opticalDepth) * cloudPhase(cosAngle, sharpness);
        energy    *= clouds.sunIrradiance.w;
        reach     *= 0.5;
        sharpness *= 0.5;
    }
    return clouds.sunIrradiance.rgb * sum;
}
```

**The honest part: the energy factor.** Wrenninge keeps *a* ≤ *b*, so that no
octave can add light that was never there. With *b* = 0.5 that means
*a* ≤ 0.5. Try it: set **Octaves** to 3 and **Octave energy** to 0.5, with
the sun behind you, and the clouds stay dull, blue-grey heaps, barely brighter
than Part 2's. With so few octaves, and a light march only a kilometre long,
the deep octaves that carry most of the light are starved. This chapter's
defaults are 6 octaves at **a = 0.8**, which breaks the guarantee and was
chosen by eye. The same clouds then look like cumulus, though still short of
the 0.68 a white surface would reach. Section 2 said a cloud absorbs almost
nothing. A model that brings back too little light is the larger error here,
so the defaults lean the other way.

Turn **Octave energy** down and watch the clouds grey. **Octaves** at 1 is
section 6's single scattering exactly.

## 12. The horizon

Rays near the horizon meet the cloud layer kilometres away and cross it at a
shallow slant (section 3's worked example):

| Above the horizon | Meets the base at | Crosses the layer for |
| --- | --- | --- |
| 30° | 3 km | 5 km |
| 7° | 12.3 km | 20 km |
| 3° | 28.7 km | 48 km |
| 1° | 86 km | 143 km |

Marching all of that would be pointless and expensive:

- Sixty-four steps over 143 km are steps of more than 2 km, which see no clouds
  at all, only noise.
- Real air between you and a cloud 50 km away hides it in its own haze. That
  haze is Chapter 23's pale horizon.
- The real Earth curves away, and at that distance the cloud base is below the
  horizon anyway.

So the march stops at **30 km**, section 3's `MARCH_REACH`, and a cloud fades
out before it gets there. Where the fade starts is a fraction of the reach, a
constant to add under `MARCH_REACH`:

```glsl
const float FADE_START  = 0.4;
```

`marchClouds` already ends the march at whichever comes first, the top of the
layer or `MARCH_REACH`. Now it fades by where the ray *entered* the layer:
fully there up to 12 km, gone by 30 km, with Chapter 16 section 5's
`smoothstep` between.

The same line keeps the clouds' light inside a half float. Straight toward the
sun the forward lobe is 3.58 per steradian at the default *g*, and 62 at 0.95,
so a bright sun at a high exposure can pass 65504. The cube would then hold
infinity, which section 13's running average keeps, and the draw would show a
dark hole around the sun. So the clouds' own light, `light` divided by the
opacity, stops at the 60000 Chapter 23 section 6 holds the disk to. Clamped
per unit of opacity rather than as a sum, a thin cloud drawn over the disk
blends two values of at most 60000, and stays below the limit as well.

Replace Part 1's last line of `marchClouds`,
`return vec4(light, 1.0 - transmittance);`, with:

```glsl
    // Section 12: far clouds fade into the sky in front of them. And the clouds' own light, light
    // divided by the opacity, stops at the 60000 Chapter 23 holds the sun's disk to: past the largest
    // half float, 65504, the cube would hold infinity. Clamped per unit of opacity, not as a sum, so a
    // thin cloud drawn over the disk stays below 65504 too.
    float fade = 1.0 - smoothstep(FADE_START * reach, reach, start);
    return vec4(min(light, vec3(60000.0 * (1.0 - transmittance))), 1.0 - transmittance) * fade;
```

Multiplying a premultiplied color by `fade` fades it correctly: its light
and its opacity shrink together, so a cloud at half fade covers half as much of
the sky and adds half as much of its own light. In degrees, clouds are whole
down to about 7° above the horizon and gone by about 3°. The band below is
Chapter 23's haze, as it is in reality on a clear day.

**What this leaves out.** The real cloud layer is a shell around a round
planet, not a flat plane. Over a flat layer, rays near the horizon meet it
much further away than they would a curved one, and at 1° the difference is
already large. *Horizon Zero Dawn* marches a spherical shell, which brings far
clouds down to the horizon properly. It costs one ray-sphere intersection
instead of a ray-plane one, the quadratic formula. Chapter 33's path tracer
intersects spheres the same way, so that chapter is the place to learn it
before trying it here. The fade hides the difference.

## Checkpoint

The panel at its defaults, "Scattered":

- **Sun behind you**, about 25° up: white-grey heaps with soft grey undersides.
  Set **Octaves** to 3 and **Octave energy** to 0.5 and they go blue-grey and
  dull, as in section 11. Put them back.
- **Sun in front**, low: the clouds near it have bright rims and darker
  middles, and the sky around the sun glows through the gaps.
- **Sun high**, 60°, looking up: soft white clouds with little shading. Light
  from above reaches everything you can see.
- **Toward the horizon:** the clouds flatten into bands by perspective and
  fade into the haze a few degrees above it.

---

# Part 4 — Cost (sections 13-14)

The clouds now look right. Part 4 is about what they cost and how that cost is
spread out. Section 13 covers the one-face-a-frame schedule and the running
average that hides the march's noise. Section 14 measures it all, with Chapter
24's `GpuTimestamps`.

## 13. Time slicing and the running average

### One face a frame

`Update` marches **Faces per frame** faces, one by default, and moves
`m_nextFace` on by that many. The six faces take turns, so each is
re-marched every six frames:

| Faces per frame | A face is refreshed every | At 60 frames a second |
| --- | --- | --- |
| 1 | 6 frames | 0.1 s |
| 2 | 3 frames | 0.05 s |
| 6 | every frame | 0.017 s |

Clouds a few kilometres away move a fraction of a degree in a tenth of a
second, so on a real GPU one face per frame is invisible and costs a sixth of
marching them all. The frames are not equal, though: the one that marches +Y
costs the most, and the one that marches −Y almost nothing (section 5), so the
frame time rises and falls in a six-frame rhythm.

The faces are refreshed at different times, so their edges can disagree for a
moment about where a moving cloud is. At 10 m/s and 3 km, a refresh of 0.1 s
moves a cloud by 1 m, a twentieth of a 23 m texel (section 9). On a slow
device that takes 80 ms a frame, a refresh takes half a second and moves it
5 m, still only a fifth of a texel. You would need a gale and a very slow
machine to see a seam.

### The running average

Each update blends its fresh, jittered march into what the texel held
(section 5's last line):

$$
\text{new value} = \text{old value} \times (1 - w) + \text{this update} \times w
$$

with *w* the panel's **New sample weight**, 0.25 by default. This is an
**exponential moving average**. Unroll it and the newest update counts *w*,
the one before *w*(1 − *w*), the one before that *w*(1 − *w*)², and so on. Old
updates fade away, but never all at once. Two numbers describe what it does.

**How much it smooths.** Each update's jitter is noise. Noise is measured by
its *variance*, the average of its squared size, and the size you see is the
square root of that. Take the next number on trust: the average's noise has
*w* / (2 − *w*) times one update's variance, 0.25 / 1.75 = 1/7. That is what
averaging 7 updates gives, so the noise's size falls by the square root, to
√(1/7) = 0.38 of one update's. You can see this directly. Set **Steps** to 8, so each step is
long and the jitter is loud, and **New sample weight** to 1: the clouds' edges
dissolve into blocky grain, a different value in every cube texel. Set the
weight back to 0.25, and within a few refreshes the grain melts into a soft
texture. At the default 64 steps the jitter is too small to see either way.
The average is what lets you turn the step count down (section 14) without the
grain showing.

**How far it lags.** An average remembers the past, and the past is where the
cloud *was*. At *w* = 0.25 the updates count 0.25, 0.19, 0.14, 0.11, and so
on, at ages 0, 1, 2, 3 updates, and their weighted average age, the average's
centre of mass, is (1 − *w*) / *w* = 3 updates in the past. Each update of a
face is one refresh apart, so the lag in time is

$$
\text{lag} = \frac{1 - w}{w} \times \text{refresh time}
$$

and a cloud moving at the wind speed *v* is drawn about *v* × lag behind where
it is. That is **ghosting**: the trailing edge of a moving cloud smears over
where the cloud has just been.

**Choosing the weight against the wind.** Ghosting cannot be seen while it is
smaller than one texel of the cube. A texel at distance *D* is *D* × 2/256
metres wide (section 9), so the rule is:

$$
\frac{1 - w}{w} \times \text{refresh time} \times v \;<\; D \times \frac{2}{256}
$$

Worked, for a cloud 3 km away (*D* × 2/256 = 23 m):

| Machine | Refresh time | Wind | Lag at *w* = 0.25 | Smallest *w* that stays under a texel |
| --- | --- | --- | --- | --- |
| a GPU at 60 fps | 0.1 s | 10 m/s | 0.3 s: 3 m, an eighth of a texel | 0.04 |
| a GPU at 60 fps | 0.1 s | 40 m/s | 0.3 s: 12 m, half a texel | 0.15 |
| a slow device, 80 ms a frame | 0.5 s | 10 m/s | 1.5 s: 15 m, 0.6 texel | 0.18 |
| a slow device, 80 ms a frame | 0.5 s | 40 m/s | 1.5 s: 60 m, 2.6 texels | 0.46 |

The default, 0.25, keeps ghosting below a texel everywhere except in a gale on
a slow machine. Put honestly: on the slow device, with the wind at 40 m/s, the
trailing edges are about two and a half texels softer than with *w* = 1. That
is hard to see, because a texel is already soft, and the exit check does not
ask you to.
A smaller weight smooths more and lags more. Lower it only when the wind is
light and the frame rate high.

**Starting again.** The average must not blend the clouds the panel just
changed with the clouds it changed them from. So any change of a setting, of the
sun's direction, or of the exposure makes the next six faces fresh: `Update`
marches them at weight 1, replacing what they held. Three changes to section
5's `Update` do it. Above the line `const uint32_t faces = ...`, add the test
for a change:

```cpp
    // Section 13: a texel keeps a running average of its updates. Anything that changes how the clouds
    // look - a slider, the sun, or the exposure - makes the old values wrong, and the next six faces
    // start afresh.
    if (!(settings == m_lastSettings) || inputs.sunDirection != m_lastSunDirection ||
        inputs.exposure != m_lastExposure)
    {
        m_freshFaces       = 6;
        m_lastSettings     = settings;
        m_lastSunDirection = inputs.sunDirection;
        m_lastExposure     = inputs.exposure;
    }
```

replace Part 1's `const float weight = 1.0f;` with the weight the panel sets,
except while faces are fresh:

```cpp
    const float    weight = m_freshFaces > 0 ? 1.0f : settings.newWeight;
```

and after `m_nextFace = ...` at the end, count the fresh faces down:

```cpp
    m_freshFaces = m_freshFaces > faces ? m_freshFaces - faces : 0;
```

`CloudSettings::operator==`, defaulted in its header, compares every field.
The wind is the one change that does *not* restart the average. The clouds
move, and their settings stay the same. That motion is exactly the case the
lag arithmetic above covers.

## 14. Timing it

### `GpuTimestamps`, from Chapter 24

Chapter 24 section 9 made Chapter 21 section 8's timestamp queries a class,
`GpuTimestamps`, when the sky's light became their third user. The clouds use
it twice, and its rules hold here as there: a frame reads only its own slot,
after that slot's fence; every difference is masked by the valid bits; and a
timestamp bounds the work recorded before it, nothing more.

### How the clouds use it

`Clouds` owns a `GpuTimestamps` of four: the march's start and end in
`Update`, and the draw's start and end in `Draw`. `Update` decides which frame
slot to use. The clouds already count their updates, to seed section 3's
jitter, and there is at most one a frame, so the count picks the slot as well
as the frame index `Sky::Update` is handed would (Chapter 24 section 4): the
slot used two updates ago belongs to a frame at least two frames back, whose
fence has been waited. At the top of `Update`, after `if (!m_on) { return; }`, add:

```cpp
    // Section 14. The clouds count their own updates, which advance once a frame like the engine's frame
    // index: the slot used FRAMES_IN_FLIGHT updates ago belongs to a frame whose fence has been waited.
    m_slot = m_updates % FRAMES_IN_FLIGHT;
    if (m_timestamps.Read(m_slot))
    {
        m_timings.marchMs = m_timestamps.Milliseconds(0, 1);
        m_timings.drawMs  = m_timestamps.Milliseconds(2, 3);
    }
    drawCloudTimings(m_timings, m_timestamps.Available());
    m_timestamps.Reset(commandBuffer, m_slot);
    m_timestamps.Write(commandBuffer, m_slot, 0);
```

Then timestamp 1 goes after the march's second barrier, just before
`m_nextFace = ...` at the end of `Update`:

```cpp
    m_timestamps.Write(commandBuffer, m_slot, 1);
```

and timestamps 2 and 3 around section 4's draw: in `Draw`, put the first before
`vkCmdBindPipeline` and the second after `vkCmdDraw`:

```cpp
    m_timestamps.Write(commandBuffer, m_slot, 2);
```

```cpp
    m_timestamps.Write(commandBuffer, m_slot, 3);
```

The noise, made once in `Initialize`, has a timer of its own: the
`GpuTimestamps` of two in `GenerateNoise` (section 7). It resets, writes before
the work and after it, and reads as soon as `immediateSubmit` returns, at the
end of section 7's listing.

Why not borrow the frames' four instead? `Read` fetches all of a pool's
timestamps at once, and a timestamp that was never written is never ready.
Write two of four and `Read` returns false every time, and the noise's time
silently never appears. A timer of exactly the size you write avoids that.

**This is `drawCloudTimings`**, which `CloudSettings.h` declared at the start
(the front matter), the last function in `CloudSettings.cpp`. `Update` calls
it each frame. That is ImGui in the middle of
recording, which no earlier chapter does. It is allowed, because ImGui's frame
is open from `beginUiFrame` until the renderer's `record` calls
`ImGui::Render`, after the demo's `Record`. `ImGui::Begin("Tone mapping")`
finds the window Main drew earlier this frame, Chapter 23's Sky header
included, and adds a line to its end, below the header. The timings live inside
the demo's sky, and the panel lives in the engine, so this is the one place
both are known:

```cpp
void drawCloudTimings(const CloudTimings& timings, bool measured)
{
    if (ImGui::Begin("Tone mapping"))
    {
        if (measured)
        {
            // Two short lines, so the window stays clear of the demo picker.
            ImGui::Text("Clouds: noise %.2f ms, once", timings.generateMs);
            ImGui::Text("march %.2f ms, draw %.2f ms a frame", timings.marchMs, timings.drawMs);
        }
        else
        {
            ImGui::TextDisabled("Clouds: this device has no timestamps.");
        }
    }
    ImGui::End();
}
```

### What the numbers say

Here is one machine, a software Vulkan device that runs this kind of work
hundreds of times slower than a desktop GPU, at the defaults: 256 × 256 faces,
64 steps, 6 light steps, 6 octaves, "Scattered":

| Pass | Time |
| --- | --- |
| The noise, once, in `Initialize` | 300 to 1000 ms |
| March, the +Y face (every ray climbs) | about 90 ms |
| March, a side face (half the rays climb) | 45 to 60 ms |
| March, the -Y face (no ray climbs) | about 1 ms |
| Draw | 0.1 to 0.4 ms |
| A whole frame of the USD viewer, median: clouds off / on / 6 faces a frame | 26 / 77 / 290 ms |

What those numbers say about any GPU is only their proportions:

- **The march is everything.** The draw is a single texture lookup per pixel.
- **The cost is in the cloudy samples.** A face's march costs about rays ×
  cloudy samples per ray × (1 + light steps) density lookups. That is why the
  +Y face, all of whose rays meet clouds, costs the most. It is also why
  "Scattered" is the expensive sky: its rays cross long stretches of thin
  cloud. "Clear" has few cloudy samples, and "Overcast" has many but stops
  each ray as soon as it is opaque (section 5). On the +Y face here, Clear
  took 45 ms, Overcast 42 ms, and Scattered 96 ms.
- **The knobs, roughly in order of what they save:**
  - **Faces per frame** is linear: 6 costs six times 1.
  - **Light steps** multiplies the lookups at every cloudy sample: going from
    6 to 3 took the +Y face from 96 to 58 ms here, and the side faces down by
    about a fifth.
  - **Steps** saves less than you would expect: 32 instead of 64 took the +Y
    face from 96 to 80 ms. A ray stops when it is opaque, whatever the step
    count, and every ray pays for its setup and its five sky lookups. The
    running average (section 13) hides the grain of fewer steps.
  - **`CLOUD_FACE_SIZE`** is quadratic: 512 is four times 256, 128 a quarter.
  - **Octaves** are arithmetic only, with no lookups, and cheap.

A desktop GPU runs this kind of work hundreds of times faster than that
device, so expect the march of one face to take well under a millisecond. Whether it
does, and whether 512 × 512 faces fit a budget, is what only a real GPU can say.

## Checkpoint

- The "Tone mapping" window shows a "Clouds:" line under the Sky header, with
  three numbers: the noise once, and the march and draw of the current frame.
  The march number jumps around as the faces take turns: highest for +Y, near
  zero for −Y.
- **Faces per frame** at 6 multiplies the march time by about six. **Light
  steps** at 3 brings it down, most of all on the +Y face.
- **Steps** at 8 with **New sample weight** at 1 shows the grain, and 0.25
  hides it within a few refreshes.

---

## If something goes wrong

| Symptom | Likely cause |
| --- | --- |
| No clouds at all | The sky is Off, or **Clouds** is unticked; or the demo never calls `Sky::Update` and `Sky::Draw`. Check the "Clouds:" timings line: if it is missing, `Update` is not running |
| Black or speckled patches that never go away | A NaN or an infinity in the cloud cube, kept by a blend that `mix`es at weight 1 instead of storing `result`: `previous × 0` is NaN for either (section 5). A cube not cleared at creation is one source (section 4) |
| The sun shines through a cloud too thick to see through | The march stops early but leaves its last 1% of transmittance in (section 5) |
| A straight line or a seam across the sky, repeating every few kilometres | The noise does not tile: a cell coordinate not wrapped before hashing, or an octave whose period does not double with its frequency (section 7) |
| Rings or contour bands inside clouds | The first step is not jittered, or every update uses the same jitter (section 3) |
| Grain that never settles | **New sample weight** at 1, or fresh faces forced every frame because something in the settings changes every frame (section 13) |
| Moving clouds smear on their trailing side | **New sample weight** too low for the wind and the frame rate (section 13's table) |
| With the sun behind you, the clouds are dull grey-blue | **Octaves** at 1, or **Octave energy** at 0.5 or below (section 11) |
| Clouds near the horizon shimmer as they drift | The mip levels are not chosen from the footprint, or the noise images have no mip chain (sections 7, 9) |
| `SYNC-HAZARD-WRITE-AFTER-WRITE` on `vkCmdBlitImage` at start-up | The first transition of the noise images names only the compute stage; the blits write levels 1 and up (section 7) |
| `SYNC-HAZARD-READ-AFTER-WRITE` on `vkCmdDraw` | The barrier after the march does not reach the draw's `FRAGMENT_SHADER` (section 5; it is the exit check's positive control) |
| The clouds stand still, or do not follow the camera | The demo leaves `SkyInputs::time` or `cameraPosition` at zero |
| A tall object is drawn in front of clouds that should hide it | Expected: the clouds are at depth 1.0, behind everything (section 1) |

## Exit check

Run each in a demo that shows a sky: the USD viewer with `Basics.usda`, whose
sun is the panel's, or the grass. Open the Sky header of the "Tone mapping"
window and set **Mode** to "Sun sky".

- [ ] Rerun `GenerateProjects.bat` and build. Each time a demo with a sky is
      set up, the log shows a line `Clouds: the noise took N ms on the GPU`,
      with your own number for N.
- [ ] **The test with a known answer** (section 5): uniform layer, extinction
      0.0004, Transmittance view, Raw at 0 stops, looking straight up. The
      centre of the screen reads (163, 163, 163), picked in RenderDoc's
      Texture Viewer (Chapter 34 section 3) or with a color picker. At
      extinction 0.0008 it reads (103, 103, 103).
- [ ] **"Scattered"**, the default: heaps of cumulus with grey bases, thinning
      into the haze a few degrees above the horizon. **"Clear"**: a few separate
      clouds, most of them small, with wide blue between. **"Overcast"**: a grey
      lid with breaks of blue.
- [ ] **Sun low and in front of you** (the USD viewer's **Elevation** at about
      12°, and turn to face it): clouds near the sun are bright at their edges,
      and the sun's disk shows only through the gaps. Behind a thick cloud it
      is gone.
- [ ] **Sun behind you**, about 25° up: white-grey clouds. **Octaves** 3 with
      **Octave energy** 0.5 turns them dull blue-grey (section 11).
- [ ] **Sun high**, 60°: looking up, soft clouds lit almost evenly.
- [ ] Leave it running: within half a minute the clouds have drifted downwind,
      and their edges have changed shape on the way.
- [ ] In the USD viewer, switch between Forward and Deferred (Chapter 22): the
      clouds are the same on both paths. Set MSAA to 4x: the same again.
- [ ] The "Clouds:" line in the "Tone mapping" window shows the noise's time
      once and the march's time per frame, changing as the faces take turns:
      highest for +Y, near zero for −Y. **Faces per frame** at 6 multiplies the
      march by about six.
- [ ] Synchronization validation is silent through all of the above, through
      switching to other demos and back, and through switching the sky and the
      clouds off and on. Quitting reports no leaked VMA allocation.
- [ ] **Positive control.** In `Clouds::Update`, change the barrier after the
      march so that its destination stage is `VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT`
      instead of `VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT`. Every frame with
      clouds reports `SYNC-HAZARD-READ-AFTER-WRITE` on `vkCmdDraw`: the
      draw's fragment shader samples the cube before the transition that
      handed it over is ordered with it. Put the stage back.

The barriers this chapter adds are collected, with the rest, in Chapter 04's
appendix, "Barriers the later chapters add".

## Where to go next

- **Clouds you can fly through.** March on the screen instead of into a cube:
  a ray per pixel from the camera, at a quarter of the resolution or less,
  stopped at the scene's depth so that mountains can sit inside clouds. To
  afford that, *Horizon Zero Dawn* marches one pixel in sixteen each frame and
  fills in the rest by **temporal reprojection**: last frame's result, moved to
  where each of its pixels lands now that the camera has moved, kept where it
  still fits and thrown away where it does not. Most of this chapter carries
  over unchanged: the density, the lighting, and the step's integral. What is
  new is the reprojection, the rejection of history that no longer fits, and
  an upscale that respects edges.
- **A round planet.** March a spherical shell instead of a flat slab. The cloud
  base then curves down to the horizon properly, and the fade of section 12 can
  move much further out.
- **Shadows on the ground.** Render the clouds' transmittance toward the sun
  into a 2D map over the scene, and multiply the sun's light by it. The ground
  then darkens under the clouds, and the scene darkens under an overcast,
  which today it does not: only the sky knows about the clouds.
- **Curl noise.** Schneider's 2017 talk swirls the detail volume's sample
  positions with a 2D curl-noise texture, which turns round billows into wisps
  near the cloud base.
- **The "powder" term.** The same 2015 talk darkens a cloud's sunlit face at
  its very edge, where light has not yet had room to scatter back out. This
  chapter's octaves (section 11) get most of that on their own, so it is left
  out; it is one more factor in `sunLight` if you want it.
- **The sea's reflections** (Chapters 30 and 31) read `Sky::CloudCubeView`
  beside the sky's cube: sky × (1 − cloud.a) + cloud.rgb, as `Clouds::Draw`
  does.

## Sources

- Andrew Schneider and Nathan Vos, "The Real-time Volumetric Cloudscapes of
  *Horizon: Zero Dawn*", SIGGRAPH 2015, Advances in Real-Time Rendering. The
  weather map, Perlin-Worley shape noise, the height profiles per cloud type,
  coverage applied by remap, erosion by detail noise, the light march, and the
  powder term. Also Schneider's chapter "Real-Time Volumetric Cloudscapes" in
  *GPU Pro 7* (2016).
- Andrew Schneider, "Nubis: Authoring Real-Time Volumetric Cloudscapes with the
  Decima Engine", SIGGRAPH 2017, Advances in Real-Time Rendering. Curl noise,
  and reprojection for screen-space clouds.
- Sébastien Hillaire, "Physically Based Sky, Atmosphere and Cloud Rendering in
  Frostbite", SIGGRAPH 2016, Physically Based Shading in Theory and Practice.
  The energy-conserving integral of one step (section 3), and multiple
  scattering by octaves for real time (section 11). Also Hillaire's
  open-source *TileableVolumeNoise*, whose Perlin-Worley combination section 7
  follows.
- Magnus Wrenninge, Christopher Kulla, and Viktor Lundqvist, "Oz: The Great and
  Volumetric", SIGGRAPH 2013 Talks. The octave approximation of multiple
  scattering and its *a* ≤ *b* condition.
- L. G. Henyey and J. L. Greenstein, "Diffuse radiation in the Galaxy",
  *The Astrophysical Journal* 93, 1941. The phase function of section 6.
- Steven Worley, "A Cellular Texture Basis Function", SIGGRAPH 1996. Worley
  noise.
- Ken Perlin, "Improving Noise", SIGGRAPH 2002. Gradient noise with the quintic
  fade curve, as Chapter 27 section 2 uses it.

## Appendix A — Code to type in, not explained in the text

These are parts of the chapter's code that repeat patterns earlier chapters
taught. The sections point here when you need each one; type them in then.

**`drawCloudPanel`**, the first function in `CloudSettings.cpp`, after the
file's includes (`CloudSettings.h` and `<imgui.h>`) and inside the namespace.
Part 1 needs it (the front matter):

```cpp
bool drawCloudPanel(CloudSettings& settings)
{
    bool changed = false;
    ImGui::SeparatorText("Clouds");
    changed |= ImGui::Checkbox("Clouds", &settings.enabled);

    // Section 8: three starting points; every slider below still moves from there.
    if (ImGui::Button("Clear"))
    {
        settings.coverage = 0.35f; settings.typeFromWeather = false; settings.cloudType = 1.0f; changed = true;
    }
    ImGui::SameLine();
    if (ImGui::Button("Scattered"))
    {
        settings.coverage = 0.5f; settings.typeFromWeather = true; changed = true;
    }
    ImGui::SameLine();
    if (ImGui::Button("Overcast"))
    {
        settings.coverage = 0.85f; settings.typeFromWeather = false; settings.cloudType = 0.3f; changed = true;
    }
    changed |= ImGui::SliderFloat("Coverage", &settings.coverage, 0.0f, 1.0f);
    changed |= ImGui::Checkbox("Type from weather map", &settings.typeFromWeather);
    if (!settings.typeFromWeather)
    {
        changed |= ImGui::SliderFloat("Type", &settings.cloudType, 0.0f, 1.0f, "%.2f (0 stratus, 1 cumulus)");
    }
    changed |= ImGui::DragFloatRange2("Altitude (m)", &settings.bottom, &settings.top, 10.0f, 200.0f, 10000.0f,
                                      "%.0f", "%.0f", ImGuiSliderFlags_AlwaysClamp);
    changed |= ImGui::SliderFloat("Extinction (/m)", &settings.extinction, 0.0001f, 0.2f, "%.4f",
                                  ImGuiSliderFlags_Logarithmic);
    changed |= ImGui::Checkbox("Uniform layer", &settings.uniformLayer);

    if (ImGui::TreeNode("Shape and wind"))
    {
        changed |= ImGui::SliderFloat("Billows", &settings.billows, 0.0f, 1.0f);
        changed |= ImGui::SliderFloat("Erosion", &settings.erosion, 0.0f, 1.0f);
        changed |= ImGui::SliderFloat("Wind (m/s)", &settings.windSpeed, 0.0f, 60.0f);
        changed |= ImGui::SliderFloat("Blows toward", &settings.windAngle, 0.0f, 360.0f, "%.0f deg");
        ImGui::TreePop();
    }
    if (ImGui::TreeNode("Light"))
    {
        changed |= ImGui::SliderFloat("Forward g", &settings.forwardG, 0.0f, 0.95f);
        changed |= ImGui::SliderFloat("Backward g", &settings.backwardG, 0.0f, 0.95f);
        changed |= ImGui::SliderFloat("Backward share", &settings.backwardShare, 0.0f, 1.0f);
        changed |= ImGui::SliderInt("Octaves", &settings.octaves, 1, 8);
        changed |= ImGui::SliderFloat("Octave energy", &settings.octaveEnergy, 0.0f, 0.95f);
        ImGui::TreePop();
    }
    if (ImGui::TreeNode("Cost"))
    {
        changed |= ImGui::SliderInt("Steps", &settings.steps, 8, 256);
        changed |= ImGui::SliderInt("Light steps", &settings.lightSteps, 1, 16);
        changed |= ImGui::SliderInt("Faces per frame", &settings.facesPerFrame, 1, 6);
        changed |= ImGui::SliderFloat("New sample weight", &settings.newWeight, 0.05f, 1.0f);
        ImGui::TreePop();
    }
    if (ImGui::TreeNode("Debug"))
    {
        changed |= ImGui::Combo("View", &settings.debugView, "Shaded\0Coverage\0Density slice\0Transmittance\0");
        changed |= ImGui::SliderFloat("Slice altitude (m)", &settings.sliceAltitude, 0.0f, 10000.0f, "%.0f");
        ImGui::TreePop();
    }
    return changed;
}
```

**`destroyNoiseImage`**, in `Clouds.cpp` after `createNoiseImage`:

```cpp
static void destroyNoiseImage(VulkanContext& context, NoiseImage& noise)
{
    vkDestroyImageView(context.device, noise.storageView, nullptr);
    vkDestroyImageView(context.device, noise.view, nullptr);
    vmaDestroyImage(context.allocator, noise.image, noise.allocation);   // null image: no-op
    noise = {};
}
```

**`CreateDescriptors`** (section 4):

```cpp
InitializationResult Clouds::CreateDescriptors()
{
    const auto sampled = [](uint32_t binding, VkShaderStageFlags stages) {
        return VkDescriptorSetLayoutBinding{ .binding = binding, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                                             .descriptorCount = 1, .stageFlags = stages };
    };
    const VkDescriptorSetLayoutBinding marchBindings[] = {
        { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .descriptorCount = 1,
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        sampled(1, VK_SHADER_STAGE_COMPUTE_BIT),   // the shape volume
        sampled(2, VK_SHADER_STAGE_COMPUTE_BIT),   // the detail volume
        sampled(3, VK_SHADER_STAGE_COMPUTE_BIT),   // the weather map
        sampled(4, VK_SHADER_STAGE_COMPUTE_BIT),   // the sky
    };
    const VkDescriptorSetLayoutBinding drawBinding = sampled(0, VK_SHADER_STAGE_FRAGMENT_BIT);

    VkDescriptorSetLayoutCreateInfo layoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 5,
        .pBindings    = marchBindings,
    };
    if (vkCreateDescriptorSetLayout(m_context.device, &layoutInfo, nullptr, &m_marchSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the cloud march.");
    }
    layoutInfo.bindingCount = 1;
    layoutInfo.pBindings    = &drawBinding;
    if (vkCreateDescriptorSetLayout(m_context.device, &layoutInfo, nullptr, &m_drawSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the cloud draw.");
    }

    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,          1 },
        { VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 4 + 1 },
    };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 2,
        .poolSizeCount = 2,
        .pPoolSizes    = poolSizes,
    };
    if (vkCreateDescriptorPool(m_context.device, &poolInfo, nullptr, &m_pool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the clouds.");
    }

    const VkDescriptorSetLayout layouts[] = { m_marchSetLayout, m_drawSetLayout };
    VkDescriptorSet             sets[2]{};
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_pool,
        .descriptorSetCount = 2,
        .pSetLayouts        = layouts,
    };
    if (vkAllocateDescriptorSets(m_context.device, &allocateInfo, sets) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the clouds.");
    }
    m_marchSet = sets[0];
    m_drawSet  = sets[1];

    // The march writes the faces in GENERAL; the draw and the march read in SHADER_READ_ONLY_OPTIMAL,
    // the layouts the barriers in Update put each image in.
    const VkDescriptorImageInfo faces{ .imageView = m_cubeView, .imageLayout = VK_IMAGE_LAYOUT_GENERAL };
    const VkDescriptorImageInfo sky{ .sampler = m_skySampler, .imageView = m_skyCube,
                                     .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
    const VkDescriptorImageInfo cube{ .sampler = m_skySampler, .imageView = m_cubeView,
                                      .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
    const VkWriteDescriptorSet writes[] = {
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_marchSet, .dstBinding = 0,
          .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .pImageInfo = &faces },
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_marchSet, .dstBinding = 4,
          .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &sky },
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_drawSet, .dstBinding = 0,
          .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &cube },
    };
    vkUpdateDescriptorSets(m_context.device, 3, writes, 0, nullptr);
    return InitializationResult::success();
}
```

**`CreateMarchPipeline`** (section 5), Chapter 20's pattern: one set, 128 bytes
of push constants, and `createComputePipeline`:

```cpp
InitializationResult Clouds::CreateMarchPipeline()
{
    const VkPushConstantRange marchRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(shared::CloudMarchParameters),
    };
    const VkPipelineLayoutCreateInfo marchLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_marchSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &marchRange,
    };
    if (vkCreatePipelineLayout(m_context.device, &marchLayoutInfo, nullptr, &m_marchLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the cloud march.");
    }
    m_marchPipeline = createComputePipeline(m_context.device, m_pipelineCache, "Clouds/CloudMarch.comp.spv", m_marchLayout);
    if (m_marchPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the cloud march pipeline failed.");
    }
    return InitializationResult::success();
}
```

**The first half of `GenerateNoise`** (section 7), up to the `immediateSubmit`
that section 7 shows:

```cpp
InitializationResult Clouds::GenerateNoise()
{
    // One layout for all three generation shaders: a single storage image at binding 0, whatever its
    // dimensions - a descriptor does not say whether its image is 2D or 3D, the view does.
    const VkDescriptorSetLayoutBinding binding{ .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
                                                .descriptorCount = 1, .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 1,
        .pBindings    = &binding,
    };
    const VkDescriptorPoolSize poolSize{ VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, 3 };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 3,
        .poolSizeCount = 1,
        .pPoolSizes    = &poolSize,
    };
    VkDescriptorSetLayout setLayout      = VK_NULL_HANDLE;
    VkDescriptorPool      pool           = VK_NULL_HANDLE;
    VkPipelineLayout      pipelineLayout = VK_NULL_HANDLE;
    std::array<VkPipeline, 3>      pipelines{};
    std::array<VkDescriptorSet, 3> sets{};
    GpuTimestamps                  timer;   // section 14: two timestamps, around the whole generation

    const auto release = [&] {
        for (VkPipeline pipeline : pipelines) { vkDestroyPipeline(m_context.device, pipeline, nullptr); }
        vkDestroyPipelineLayout(m_context.device, pipelineLayout, nullptr);
        vkDestroyDescriptorPool(m_context.device, pool, nullptr);
        vkDestroyDescriptorSetLayout(m_context.device, setLayout, nullptr);
        timer.Shutdown();
    };

    if (vkCreateDescriptorSetLayout(m_context.device, &setLayoutInfo, nullptr, &setLayout) != VK_SUCCESS ||
        vkCreateDescriptorPool(m_context.device, &poolInfo, nullptr, &pool) != VK_SUCCESS)
    {
        release();
        return InitializationResult::failure("Creating the cloud noise's descriptors failed.");
    }
    const std::array<VkDescriptorSetLayout, 3> setLayouts{ setLayout, setLayout, setLayout };
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = pool,
        .descriptorSetCount = 3,
        .pSetLayouts        = setLayouts.data(),
    };
    const VkPipelineLayoutCreateInfo pipelineLayoutInfo{
        .sType          = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount = 1,
        .pSetLayouts    = &setLayout,
    };
    if (vkAllocateDescriptorSets(m_context.device, &allocateInfo, sets.data()) != VK_SUCCESS ||
        vkCreatePipelineLayout(m_context.device, &pipelineLayoutInfo, nullptr, &pipelineLayout) != VK_SUCCESS)
    {
        release();
        return InitializationResult::failure("Creating the cloud noise's pipeline layout failed.");
    }

    const std::array<const NoiseImage*, 3> images{ &m_shape, &m_detail, &m_weather };
    const char* const shaders[] = { "Clouds/CloudShapeNoise.comp.spv", "Clouds/CloudDetailNoise.comp.spv",
                                    "Clouds/CloudWeather.comp.spv" };
    for (size_t i = 0; i < 3; ++i)
    {
        const VkDescriptorImageInfo target{ .imageView = images[i]->storageView, .imageLayout = VK_IMAGE_LAYOUT_GENERAL };
        const VkWriteDescriptorSet  write{
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = sets[i],
            .dstBinding      = 0,
            .descriptorCount = 1,
            .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
            .pImageInfo      = &target,
        };
        vkUpdateDescriptorSets(m_context.device, 1, &write, 0, nullptr);
        pipelines[i] = createComputePipeline(m_context.device, m_pipelineCache, shaders[i], pipelineLayout);
        if (pipelines[i] == VK_NULL_HANDLE)
        {
            release();
            return InitializationResult::failure("Creating a cloud noise pipeline failed.");
        }
    }
    if (auto result = timer.Initialize(m_context, 2); !result)
    {
        release();
        return result;
    }

```

**`Shutdown`** (section 4):

```cpp
void Clouds::Shutdown()
{
    // Device idle first. Initialize never ran: no device to destroy anything with. Otherwise null handles
    // are no-ops, so a partial Initialize is safe; the pool frees both sets.
    const VkDevice device = m_context.device;
    if (device == VK_NULL_HANDLE) { return; }
    vkDestroyPipeline(device, m_drawPipeline, nullptr);
    vkDestroyPipelineLayout(device, m_drawLayout, nullptr);
    vkDestroyPipeline(device, m_marchPipeline, nullptr);
    vkDestroyPipelineLayout(device, m_marchLayout, nullptr);
    vkDestroySampler(device, m_noiseSampler, nullptr);
    if (m_context.allocator != VK_NULL_HANDLE)   // VMA asserts on a null allocator: Initialize never ran
    {
        destroyNoiseImage(m_context, m_weather);
        destroyNoiseImage(m_context, m_detail);
        destroyNoiseImage(m_context, m_shape);
        vmaDestroyImage(m_context.allocator, m_cube, m_cubeAllocation);
    }
    vkDestroyDescriptorPool(device, m_pool, nullptr);
    vkDestroyDescriptorSetLayout(device, m_drawSetLayout, nullptr);
    vkDestroyDescriptorSetLayout(device, m_marchSetLayout, nullptr);
    vkDestroyImageView(device, m_cubeView, nullptr);
    m_timestamps.Shutdown();

    m_drawPipeline    = m_marchPipeline  = VK_NULL_HANDLE;
    m_drawLayout      = m_marchLayout    = VK_NULL_HANDLE;
    m_noiseSampler    = VK_NULL_HANDLE;
    m_pool            = VK_NULL_HANDLE;
    m_drawSetLayout   = m_marchSetLayout = VK_NULL_HANDLE;
    m_marchSet        = m_drawSet        = VK_NULL_HANDLE;
    m_cubeView        = VK_NULL_HANDLE;
    m_cube            = VK_NULL_HANDLE;
    m_cubeAllocation  = VK_NULL_HANDLE;
    m_on              = false;
}
```

## Appendix B — `CloudMarch.comp.glsl`, whole

The march shader as the chapter leaves it, for reference:

```glsl
// Shaders/Clouds/CloudMarch.comp.glsl - Chapter 28. One face of the cloud cube per dispatch: each texel
// marches its direction through the cloud layer, and blends what it finds into what the texel held.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "CloudTypes.h"   // CloudMarchParameters, CLOUD_*
#include "CubeMap.glsl"   // Chapter 23: cubeTexelDirection
#include "Random.glsl"    // Chapter 21: seedRandom, randomFloat

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0, rgba16f) uniform imageCube   cloudCube;    // texel (x, y) of face z; premultiplied
layout(set = 0, binding = 1) uniform sampler3D   shapeVolume;          // section 7
layout(set = 0, binding = 2) uniform sampler3D   detailVolume;         // section 7
layout(set = 0, binding = 3) uniform sampler2D   weatherMap;           // section 8
layout(set = 0, binding = 4) uniform samplerCube skyCube;              // Chapter 23: the sky, for the ambient light

layout(push_constant) uniform MarchBlock
{
    CloudMarchParameters clouds;
};

const float PI = 3.14159265359;

// Section 7: how many metres of the world one repeat of each image covers.
const float SHAPE_SCALE   = 8000.0;
const float DETAIL_SCALE  = 700.0;
const float WEATHER_SCALE = 40000.0;

// Section 9: the angle one texel of a cube face spans at its centre, in radians: a face is 2 units wide
// seen from 1 unit away, split into CLOUD_FACE_SIZE texels. And each volume's texel, in metres.
const float TEXEL_ANGLE   = 2.0 / float(CLOUD_FACE_SIZE);
const float SHAPE_TEXEL   = SHAPE_SCALE / float(CLOUD_SHAPE_SIZE);
const float DETAIL_TEXEL  = DETAIL_SCALE / float(CLOUD_DETAIL_SIZE);

// Section 6: how far toward the sun each sample looks for cloud in the light's way, in metres.
const float LIGHT_MARCH_DISTANCE = 1000.0;

// Section 12: how far a march reaches, in metres, and where the fade into the sky starts, as a fraction
// of that. Clouds further away than MARCH_REACH are not drawn at all; the fade hides the edge.
const float MARCH_REACH = 30000.0;
const float FADE_START  = 0.4;

// Section 9: a linear map from [low, high] to [0, 1], clamped. remap(0.6, 0.2, 1.0) = 0.5.
float remap01(float value, float low, float high)
{
    return clamp((value - low) / (high - low), 0.0, 1.0);
}

// Section 9: each cloud type is four heights, as fractions of the layer: where its density starts to
// rise, where it is full, where it starts to fall, and where it is gone.
const vec4 STRATUS       = vec4(0.0, 0.05, 0.10, 0.25);
const vec4 STRATOCUMULUS = vec4(0.0, 0.10, 0.30, 0.50);
const vec4 CUMULUS       = vec4(0.0, 0.10, 0.60, 0.95);

float heightProfile(float height, float cloudType)
{
    vec4 type = cloudType < 0.5 ? mix(STRATUS, STRATOCUMULUS, cloudType * 2.0)
                                : mix(STRATOCUMULUS, CUMULUS, cloudType * 2.0 - 1.0);
    return smoothstep(type.x, type.y, height) * (1.0 - smoothstep(type.z, type.w, height));
}

// Section 10: where the wind has carried the clouds to by now. The world is fixed; the noise slides
// downwind, so sampling at p minus the distance travelled finds what has arrived at p.
vec3 windOffset()
{
    return vec3(clouds.wind.x, 0.0, clouds.wind.y) * clouds.toSun.w;
}

// Section 8: the weather map where p stands. r: how cloudy, after the panel's coverage; g: the cloud type.
vec2 weatherAt(vec3 p)
{
    vec2 weather  = textureLod(weatherMap, (p.xz - windOffset().xz) / WEATHER_SCALE, 0.0).rg;
    float cover   = clamp(weather.r + 2.0 * clouds.coverage - 1.0, 0.0, 1.0);
    float type    = clouds.cloudType < 0.0 ? weather.g : clouds.cloudType;
    return vec2(cover, type);
}

// Section 5, grown by section 9: how much cloud there is at p, 0 to 1. `withDetail` is false for the
// light march, which does not need the edges' fine detail (section 6). `footprint` is how wide, in
// metres, the cube texel this sample belongs to is at p's distance; it picks the mip levels (section 9).
float cloudDensity(vec3 p, bool withDetail, float footprint)
{
    float height = (p.y - clouds.bottom) / (clouds.top - clouds.bottom);   // 0 at the base, 1 at the top
    if (height <= 0.0 || height >= 1.0) { return 0.0; }
    if (clouds.uniformLayer != 0u)      { return 1.0; }   // section 5: a slab with a known answer

    // Section 9. The shape: Perlin-Worley blobs, carved by their own smaller Worley billows.
    vec3  shapePosition = p - windOffset();
    float shapeLod      = log2(max(footprint / SHAPE_TEXEL, 1.0));
    vec4  shape         = textureLod(shapeVolume, shapePosition / SHAPE_SCALE, shapeLod);
    float billows       = shape.g * 0.625 + shape.b * 0.25 + shape.a * 0.125;
    float density       = remap01(shape.r, (1.0 - billows) * clouds.billows, 1.0);

    // Tall where the type is tall, then only what coverage lets through.
    vec2 weather = weatherAt(p);
    density *= heightProfile(height, weather.y);
    density  = max(density + weather.x - 1.0, 0.0);
    if (!withDetail || density <= 0.0) { return density; }

    // The edges, eaten by small Worley noise that drifts a little faster than the shape, so the edges
    // churn while the clouds hold together (section 10). Its own mip level: its texels are smaller.
    float detailLod = log2(max(footprint / DETAIL_TEXEL, 1.0));
    vec3  detail    = textureLod(detailVolume, (p - 1.5 * windOffset()) / DETAIL_SCALE, detailLod).rgb;
    float wisps     = detail.r * 0.625 + detail.g * 0.25 + detail.b * 0.125;
    return remap01(density, (1.0 - wisps) * clouds.erosion, 1.0);
}

// Section 6: Henyey and Greenstein's phase function: of the light a particle scatters, the share per
// steradian that goes off at an angle whose cosine is cosAngle. g > 0 leans forward, g < 0 backward,
// g = 0 is even in every direction: 1 / 4 pi.
float henyeyGreenstein(float cosAngle, float g)
{
    float denominator = 1.0 + g * g - 2.0 * g * cosAngle;
    return (1.0 - g * g) / (4.0 * PI * denominator * sqrt(denominator));
}

// Section 6: a forward lobe and a smaller backward one. `sharpness` (section 11) scales both g's down
// for light that has scattered many times and forgotten where it came from.
float cloudPhase(float cosAngle, float sharpness)
{
    return mix(henyeyGreenstein(cosAngle,  clouds.forwardG * sharpness),
               henyeyGreenstein(cosAngle, -clouds.backwardG * sharpness), clouds.backwardShare);
}

// Section 6: how much cloud lies between p and the sun, as optical depth (extinction times distance).
float opticalDepthToSun(vec3 p, float footprint)
{
    float stepLength = LIGHT_MARCH_DISTANCE / float(clouds.lightSteps);
    float depth      = 0.0;
    for (uint i = 0u; i < clouds.lightSteps; ++i)
    {
        vec3 q = p + clouds.toSun.xyz * (stepLength * (float(i) + 0.5));
        depth += cloudDensity(q, false, footprint) * clouds.extinction * stepLength;
    }
    return depth;
}

// Sections 6 and 11: the sunlight one sample scatters toward the eye. Octave 0 is section 6's single
// scattering; each later octave stands for light that scattered again: with less energy (the panel's
// octave energy, 0.8 by default), reaching twice as deep, and half as sure of its direction.
vec3 sunLight(float opticalDepth, float cosAngle)
{
    float sum       = 0.0;
    float energy    = 1.0;
    float reach     = 1.0;
    float sharpness = 1.0;
    for (uint octave = 0u; octave < clouds.octaves; ++octave)
    {
        sum       += energy * exp(-reach * opticalDepth) * cloudPhase(cosAngle, sharpness);
        energy    *= clouds.sunIrradiance.w;
        reach     *= 0.5;
        sharpness *= 0.5;
    }
    return clouds.sunIrradiance.rgb * sum;
}

// Section 6: the sky's light, averaged over its upper half from five directions - straight up and
// four at 30 degrees above the horizon. Chapter 23's cube already holds the exposure.
vec3 skyAmbient()
{
    vec3 sum = texture(skyCube, vec3(0.0, 1.0, 0.0)).rgb;
    sum += texture(skyCube, normalize(vec3( 1.0, 0.577,  0.0))).rgb;
    sum += texture(skyCube, normalize(vec3(-1.0, 0.577,  0.0))).rgb;
    sum += texture(skyCube, normalize(vec3( 0.0, 0.577,  1.0))).rgb;
    sum += texture(skyCube, normalize(vec3( 0.0, 0.577, -1.0))).rgb;
    return sum / 5.0;
}

// Sections 3, 5, 6, 9, 11, and 12: one ray through the layer, as premultiplied color (Chapter 21 section
// 5): rgb is the light that reaches the eye from the clouds; a is their opacity, 1 - transmittance.
vec4 marchClouds(vec3 direction, inout uint random)
{
    vec3 eye = clouds.origin.xyz;

    // Section 3: where the ray is inside the layer. It climbs direction.y metres per metre travelled,
    // so it reaches an altitude h after (h - eye.y) / direction.y metres.
    float reach = MARCH_REACH;
    float start = (clouds.bottom - eye.y) / direction.y;
    float end   = min((clouds.top - eye.y) / direction.y, reach);
    if (start >= end) { return vec4(0.0); }

    float stepLength = (end - start) / float(clouds.steps);
    float t          = start + stepLength * randomFloat(random);   // section 3: jitter the first step

    float cosAngle = dot(direction, clouds.toSun.xyz);
    vec3  ambient  = skyAmbient();

    vec3  light         = vec3(0.0);
    float transmittance = 1.0;
    for (uint i = 0u; i < clouds.steps; ++i, t += stepLength)
    {
        vec3  p         = eye + direction * t;
        float footprint = t * TEXEL_ANGLE;   // section 9: how wide this texel is, out here
        float density   = cloudDensity(p, true, footprint);
        if (density <= 0.0) { continue; }

        // Section 6: the sky lights the top of a cloud more than its base, which the cloud above shades.
        float height    = (p.y - clouds.bottom) / (clouds.top - clouds.bottom);
        vec3  scattered = sunLight(opticalDepthToSun(p, footprint), cosAngle) + ambient * mix(0.3, 1.0, height);

        // Section 3: this step's own share of the light, and of the transmittance.
        float stepTransmittance = exp(-density * clouds.extinction * stepLength);
        light         += transmittance * (1.0 - stepTransmittance) * scattered;
        transmittance *= stepTransmittance;
        // Nothing behind this point would show - except the sun's disk, which is tens of thousands of
        // times brighter than the sky: 1% of it is still white. So a ray that stops here is opaque.
        if (transmittance < 0.01)
        {
            transmittance = 0.0;
            break;
        }
    }

    // Section 12: far clouds fade into the sky in front of them. And the clouds' own light, light
    // divided by the opacity, stops at the 60000 Chapter 23 holds the sun's disk to: past the largest
    // half float, 65504, the cube would hold infinity. Clamped per unit of opacity, not as a sum, so a
    // thin cloud drawn over the disk stays below 65504 too.
    float fade = 1.0 - smoothstep(FADE_START * reach, reach, start);
    return vec4(min(light, vec3(60000.0 * (1.0 - transmittance))), 1.0 - transmittance) * fade;
}

// Section 5: the debug views, unlit and opaque, so the sky behind does not show through.
vec4 debugView(vec3 direction, inout uint random)
{
    vec3 eye = clouds.origin.xyz;
    if (clouds.debugView == CLOUD_VIEW_TRANSMITTANCE)
    {
        return vec4(vec3(1.0 - marchClouds(direction, random).a), 1.0);
    }
    float altitude = clouds.debugView == CLOUD_VIEW_COVERAGE ? clouds.bottom : clouds.sliceAltitude;
    float t        = (altitude - eye.y) / direction.y;
    if (t > MARCH_REACH) { return vec4(0.0, 0.0, 0.0, 1.0); }
    vec3 p = eye + direction * t;
    if (clouds.debugView == CLOUD_VIEW_COVERAGE) { return vec4(weatherAt(p), 0.0, 1.0); }
    return vec4(vec3(cloudDensity(p, true, t * TEXEL_ANGLE)), 1.0);
}

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    if (texel.x >= CLOUD_FACE_SIZE || texel.y >= CLOUD_FACE_SIZE) { return; }   // the dispatch rounds up

    uint face      = (clouds.face + gl_GlobalInvocationID.z) % 6u;   // z counts this frame's faces
    vec3 direction = cubeTexelDirection(face, (vec2(texel) + 0.5) / float(CLOUD_FACE_SIZE));

    // Section 3: a different jitter for every texel and every update.
    uint random = seedRandom(uint(texel.y * CLOUD_FACE_SIZE + texel.x) + face * uint(CLOUD_FACE_SIZE * CLOUD_FACE_SIZE),
                             clouds.frame);

    // Below the horizon, and on the -Y face, the eye under the layer sees no cloud.
    vec4 result = vec4(0.0);
    if (direction.y > 0.001)
    {
        result = clouds.debugView == CLOUD_VIEW_SHADED ? marchClouds(direction, random) : debugView(direction, random);
    }

    // Section 5: blend into what the texel held. Weight 1 replaces it - by choosing result, not by mix,
    // whose previous * 0 is NaN when previous is NaN or infinite: such a texel would never recover.
    ivec3 address  = ivec3(texel, int(face));
    vec4  previous = imageLoad(cloudCube, address);
    imageStore(cloudCube, address, clouds.origin.w >= 1.0 ? result : mix(previous, result, clouds.origin.w));
}
```

Next: [29 — The FFT Ocean](29-FFT-Ocean.md)
