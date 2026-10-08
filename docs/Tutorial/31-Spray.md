# 31 — Spray

**Goal:** something in Chapter 30's sea for the waves to hit. A rock stands in
it, and where a wave runs into the rock the water flies up as spray, Chapter
21's particles, with the GPU deciding where and how many. Foam stays behind on
the water around the rock and fades. Chapter 32 floats a boat in the same sea,
through the same door this chapter builds.

**ROADMAP:** step 21+ — Chapter 30's demo, grown, in `Source/PillowFort/Demos/Sea/`
with shaders under `Shaders/Sea/` and a prop in `Assets/Scenes/`.

**Module:** still `pf::demos::sea`. Everything new lives in one class,
`SeaObjects`, which `SeaDemo` owns and calls from a handful of places, and in
`SprayParticles`, Chapter 21's particle system copied for its second user.
`SeaDemo.cpp` changes in eleven places (the table "Where `SeaDemo` changes"
lists them), `SeaDemo.h` in two, the surface's fragment shader in three. The
engine does not change.

**Math:** taught where it is first used — finding a point by guessing and
correcting (section 3); a speed as the change over one frame (section 5);
rounding a fraction at random so the average comes out right (section 6). It
assumes Chapter 21 section 3's random numbers and its drag as an exponential,
Chapter 20 section 8's `atomicAdd`, and Chapter 30 section 8's exponential fade.

**Prerequisites:**

- Chapter 30, all of it, built and running. Above all: section 3 (a cascade is
  Chapter 29's ocean), 4 (the surface: where a point of the flat sea reads each
  cascade's displacement, the surface's set, and the sun as an irradiance in
  the sky's units, which lights the rock and the spray here), 8 (Record's steps
  1 and 8, the return trips and hand-overs, and the foam's old layout), 9 (the
  sky's three calls, which this chapter's calls sit beside), and 10 (the
  glint's sun, in the same units).
- Chapter 29 sections 8 and 9: the choppy displacement moves the water
  sideways, and the displacement map says where each point of the flat sea
  goes, not what is above a place. Section 3 here starts from that.
- Chapter 21 sections 1 to 5: the pool, the dead and alive lists, the counters
  and indirect arguments, the five passes and their barriers, and drawing the
  particles in a second rendering scope. Section 6 copies all of it. Section 3
  too: `seedRandom` and `randomFloat`, semi-implicit Euler, and drag as an
  exponential; and section 7, the counters read back for the panel.
- Chapter 20 sections 5 (`computeToComputeBarrier`), 8 (atomics, and
  `atomicAdd` handing out places in a list), and 9 (reading results back without
  stalling).
- Chapter 14 section 7 (`ImportUsdFile`) and Chapter 12 section 6 (the flat draw
  list), for loading the rock; Chapter 11 sections 5 to 7 and 14 (vertex
  attributes, `uploadMesh`, which side is the front, one light).
- Chapter 09 section 6: the height limit a panel takes so that it stops at the
  bottom of the window.
- Chapter 04 section 5: the three questions every barrier answers.

---

## Where this is going

```text
                      .  '  .
                  ' .  spray  . '
                .   '  .  '  .   '
           ~~~~~~/^^^^^^^^^^\~~~~~~~~
        ~~~~ ::::|   rock   |:::: ~~~~~
      ~~~~~~ ::::\__________/:::: ~~~~~~~~
    ~~~~~~~~~~~ :::: foam :::: ~~~~~~~~~~~~~~
```

The sea of Chapter 30 is a set of images on the GPU, made fresh every frame.
Everything in this chapter and the next is a question put to those images:
*where is the water here, and how fast is it moving?* The rock asks at 96
points round its waterline, and where the answer is "coming at me fast", it
asks for spray. Chapter 32's boat asks the same question under its hull, and
the answers push it up. So after a rock to look at, the chapter's job is a door
into the sea that a compute shader can use, and the rest goes through it.

One frame, end to end. Chapter 30's frame is unchanged up to the surface; this
chapter adds the boxes marked *new*:

```text
 Chapter 30 steps 1-8: waves, FFT, maps, foam; maps handed to the vertex shader       (Chapter 30)
                 and, from this chapter, to compute as well (section 4)
 Chapter 30 step 9: the sky's Update
      |
  [ local foam fades, sec. 7 ]                                        new: SeaObjects::RecordSimulation
      |
  [ impact: the water at the rock, sec. 5-7 ] -> requests, foam
      |
  [ Chapter 21's begin, emit, simulate, end, sec. 6 ] <- emission sized by the requests
      |
 Chapter 30 step 10: the scene pass: the sea, [ the rock, sec. 2 ], the sky
      |
  [ the spray, Chapter 21's second scope, sec. 6 ]                    new: SeaObjects::RecordSpray
```

The chapter is in three parts:

- **Part 1, "A rock in the sea"** (sections 1-2): a class for everything new,
  and a rock drawn in the sea. It ends with the rock in the sea and the waves
  washing up and down its sides.
- **Part 2, "Spray"** (sections 3-6): the water's height at any point, the one
  set every new pass reads the sea through, how fast the water comes at the
  rock, and spray particles that the GPU asks for itself. It ends with waves
  breaking on the rock.
- **Part 3, "Foam that stays"** (sections 7-8): foam in a map of its own, and
  the frame in order. It ends with a ring of foam round the rock.

### Two decisions about the code

**A class of its own.** Chapter 30's `SeaDemo.cpp` is over a thousand lines
already. Everything this chapter adds reads the sea the same way — through the
displacement maps, after the hand-over — and nothing in Chapter 30 reads
anything this chapter makes except one foam map. So it goes in its own class,
`SeaObjects`, with one door in (the maps) and one out (the foam map), and
`SeaDemo` calls it at a few points of its frame. Chapter 32's boat moves into
the same class: it reads the sea through the same door.

**Chapter 21's particles, copied.** The spray needs Chapter 21's whole system:
the pool, the lists, the counters, the five passes, the billboards. The sea is
its second user. The house rule is to write a pattern twice before automating
it, so `SprayParticles` is a copy, narrowed to what spray needs, and it runs
three of Chapter 21's five compute shaders and both of its drawing shaders
exactly as they are. A third user should move it into `VulkanGraphics` as a
`GpuParticles` that takes its emit and simulate shaders as parameters; that is
named again in section 8.

### Where `SeaDemo` changes

Chapter 30's demo is touched in eleven places, each small. They are spread
over the chapter, so here they are in one list to tick off:

| Where in `SeaDemo` | What changes | Section |
| --- | --- | --- |
| `SeaDemo.h` | the include of `SeaObjects.h`, and the member `m_objects` | 1 |
| `Setup` | `m_objects.Initialize`, before `CreateSurface` | 1 |
| `Teardown` | `m_objects.Shutdown`, before the sky's | 1 |
| `RecordSurface` | `m_objects.RecordDraw`, after the water | 2 |
| `Record`, step 8 | the displacement's hand-over names `COMPUTE_SHADER` too | 4 |
| `Record`, step 1 | the displacement's return trip waits for `COMPUTE_SHADER` too | 4 |
| `Record`, at the top | `m_objects.ReadResults`, beside the timestamps | 6 |
| `Record`, after the sky's `Update` | `m_objects.RecordSimulation` | 6 |
| `Record`, after `RecordSurface` | `m_objects.RecordSpray` | 6 |
| `Update` | `m_objects.Update`, the panel | 6 |
| `CreateSurface` | one more binding, 11, and its image: the local foam | 7 |

### What you are actually writing

**This is `SeaObjects.h`**, the class map. Every private function names the
section that writes it:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapters 31 and 32: a rock and a boat in Chapter 30's sea, the spray they throw, the foam they leave
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Sea/SeaObjects.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Demos/Sea/SprayParticles.h"
#include "PillowFort/VulkanGraphics/GpuMesh.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"
#include "Particles/ParticleTypes.h"
#include "Sea/SeaTypes.h"
#include "Sea/SprayTypes.h"

#include <glm/glm.hpp>
#include <vma/vk_mem_alloc.h>

#include <array>
#include <cstdint>
#include <filesystem>
#include <span>
#include <vector>

namespace pf::demos::sea {

// What the "Rock and boat" panel edits. CPU state: it survives Shutdown and Initialize.
// Colors are sRGB, as the swatches show them.
struct SeaObjectSettings
{
    float sprayThreshold = 1.0f;     // section 5: m/s the water must come at an object faster than
    float sprayRate      = 150.0f;   // section 6: particles a second, per point, per m/s past the threshold
    float sprayLaunch    = 10.0f;    // section 6: launch speed, m/s, per m/s past the threshold
    float sprayDrag      = 0.6f;     // section 6: per second
    float spraySize      = 0.25f;    // section 6: metres across at birth; three times that at the end
    float sprayOpacity   = 0.6f;     // section 6
    glm::vec3 sprayColor { 0.95f, 0.97f, 1.0f };
    float foamStamp      = 0.4f;     // section 7: foam left per m/s past the threshold
    float foamFade       = 8.0f;     // section 7: seconds for the local foam to fade to 37%
};

// One part of a prop, ready to draw: which uploaded mesh, which of its submeshes, where, and in
// what color (section 2).
struct PropPart
{
    uint32_t  mesh    = 0;            // index into SeaObjects::m_meshes
    uint32_t  submesh = 0;
    glm::mat4 model{ 1.0f };          // inside the prop: the rock's includes where the rock stands
    glm::vec3 color{ 0.8f };          // linear, the material's base color
};

// Section 1. Everything Chapters 31 and 32 put in the sea, as one piece SeaDemo owns and calls at a few
// points of its frame. All of it reads the sea through one door: the cascades' displacement maps,
// in SHADER_READ_ONLY_OPTIMAL whenever RecordSimulation and RecordDraw run.
class SeaObjects
{
public:
    InitializationResult Initialize(const DemoContext& context, const vulkan_graphics::SceneRenderer& sceneRenderer,
                                    std::span<const VkImageView, SEA_CASCADE_COUNT> displacementMaps);   // section 1
    void Shutdown();   // device idle first; safe after a partial Initialize, or none. Keeps the settings.

    // Section 7: the foam map the surface's fragment shader reads, always in GENERAL, and the sampler
    // that reads it: clamped, with a border of no foam.
    VkImageView LocalFoamView() const    { return m_localFoamView; }
    VkSampler   LocalFoamSampler() const { return m_localFoamSampler; }

    // In SeaDemo::Update: the panel.
    void Update();

    // In SeaDemo::Record, in this order. ReadResults first, after the frame's fence wait.
    void ReadResults(uint32_t frameIndex);                                   // section 6
    void RecordSimulation(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                          const SeaParameters& sea);                         // sections 5-7: before the scene pass
    void RecordDraw(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                    const SeaParameters& sea) const;                         // section 2: inside it
    void RecordSpray(VkCommandBuffer commandBuffer, const RecordContext& frame,
                     const SeaParameters& sea) const;                        // section 6: after it

private:
    InitializationResult LoadProp(const std::filesystem::path& file, const glm::mat4& placement);   // section 2
    InitializationResult CreateBuffersAndImages();                                                         // section 4
    InitializationResult CreateProbeSet(std::span<const VkImageView, SEA_CASCADE_COUNT> displacementMaps);   // section 4
    InitializationResult CreatePipelines();                                         // section 2, grown in 4, 5, 7
    SprayParameters      PackSpray(const SeaParameters& sea) const;                 // section 5

    DemoContext                           m_context;
    const vulkan_graphics::SceneRenderer* m_sceneRenderer = nullptr;   // SeaDemo's: set 0, the camera

    // Section 2: the rock, as Chapter 14 imports it.
    std::vector<vulkan_graphics::GpuMesh> m_meshes;
    std::vector<PropPart>                 m_parts;

    // Section 4: what the passes that read the sea keep from frame to frame.
    vulkan_graphics::AllocatedBuffer m_probes;      // vec4 per sample point: last frame's water there (section 5)
    vulkan_graphics::AllocatedBuffer m_requests;    // the request count, then SprayRequest[SPRAY_REQUEST_CAPACITY] (section 6)
    VkImage                          m_localFoamImage      = VK_NULL_HANDLE;   // rgba16f, r used (section 7)
    VmaAllocation                    m_localFoamAllocation = VK_NULL_HANDLE;
    VkImageView                      m_localFoamView       = VK_NULL_HANDLE;
    VkSampler                        m_localFoamSampler    = VK_NULL_HANDLE;   // clamped, a border of no foam
    VkSampler                        m_repeatSampler       = VK_NULL_HANDLE;   // Chapter 30's, for the cascades' maps
    std::array<vulkan_graphics::AllocatedBuffer, vulkan_graphics::FRAMES_IN_FLIGHT> m_readback;   // section 6
    std::array<bool, vulkan_graphics::FRAMES_IN_FLIGHT>                       m_readbackPending{};

    VkDescriptorSetLayout m_probeSetLayout = VK_NULL_HANDLE;   // section 4
    VkDescriptorPool      m_probePool      = VK_NULL_HANDLE;
    VkDescriptorSet       m_probeSet       = VK_NULL_HANDLE;
    VkPipelineLayout      m_probeLayout    = VK_NULL_HANDLE;
    VkPipeline            m_impactPipeline = VK_NULL_HANDLE;   // sections 5-7
    VkPipeline            m_fadePipeline   = VK_NULL_HANDLE;   // section 7
    VkPipelineLayout      m_propLayout     = VK_NULL_HANDLE;   // section 2
    VkPipeline            m_propPipeline   = VK_NULL_HANDLE;

    SprayParticles m_spray;   // section 6: Chapter 21's system, fed by the impact pass

    // CPU state.
    SeaObjectSettings           m_settings;
    particles::ParticleCounters m_counters{};            // section 6: for the panel, a frame or two old
    bool                        m_reset       = true;    // forget the probes, clear the foam and the spray
    uint32_t                    m_frameNumber = 0;       // seeds the impact pass's random numbers
};

} // namespace pf::demos::sea
```

`SeaObjectSettings` is what its panel edits. `PropPart` is one piece of a
prop, ready to draw. The members come in groups: the props (section 2), the
buffers and images the passes keep from frame to frame (sections 4-7), the set
and the pipelines, Chapter 21's particles, and the CPU's own state, including
its copy of what the GPU reports back.

**This is how `SeaObjects.cpp` is laid out**:

```text
SeaObjects.cpp
  includes                                               Appendix A
  static scenesDirectory                                 file scope: Chapter 14's place for the props
  namespace pf::demos::sea {
      using namespace vulkan_graphics;
      ObjectReadback                                     section 4
      Initialize                                         section 1, grown in 4 and 6
      LoadProp                                           section 2
      CreateBuffersAndImages, CreateProbeSet             section 4
      CreatePipelines                                    section 2; rows in 4, 5, 7
      Update                                             sections 6, 7
      ReadResults, PackSpray                             sections 6, 5
      RecordSimulation                                   sections 6, 7
      RecordDraw, RecordSpray                            sections 2, 6
      Shutdown                                           section 1
  }
```

### Where everything lands

```text
Assets/Scenes/
  make_sea_props.py         writes the props (Appendix B): the rock, and Chapter 32's boat     section 2
  Rock.usda, Boat.usda      what it wrote
Shaders/Sea/
  SprayTypes.h              C++/GLSL twins: the rock, the samples, the spray            sections 2-7
  SeaWater.glsl             where the water is, for any compute shader                  section 3
  SeaProp.vert/.frag.glsl   the rock                                                    section 2
  SprayImpact.comp.glsl     the water against the rock                                  sections 5-7
  SprayRequests.glsl        the list of particles asked for                             section 6
  SprayBegin.comp.glsl      Chapter 21's begin, sized by the requests                   section 6
  SprayEmit.comp.glsl       Chapter 21's emit, from the requests                        section 6
  SeaLocalFoam.comp.glsl    the local foam fades                                        section 7
  SeaSurface.frag.glsl      + the local foam                                            section 7
Shaders/Particles/          Chapter 21's, used as they are:
  ParticleReset.comp.glsl, ParticleSimulate.comp.glsl, ParticleEnd.comp.glsl,
  Particle.vert.glsl, Particle.frag.glsl, ParticleBuffers.glsl, ParticleTypes.h
Source/PillowFort/Demos/Sea/
  SeaObjects.h/.cpp         the rock, the spray, the local foam                         sections 1-7
  SprayParticles.h/.cpp     Chapter 21's particle system, copied                        section 6
  SeaDemo.h/.cpp            + the calls into SeaObjects                                 sections 1, 2, 4, 6, 7
```

---

# Part 1 — A rock in the sea (sections 1-2)

Part 1 builds the class that holds everything new and the first thing in the
sea: a rock, drawn with the camera's set and nothing else. Nothing in it reads
the sea yet; Part 2 opens the door.

## 1. A class for what is in the sea

`SeaObjects` is the class map at the top of the chapter. Part 1 writes its
setup, its draw, and its teardown; Part 2 adds its passes. One thing in the map
belongs to a later section: `m_spray`, whose class section 6 writes. Until
section 6, leave out the `#include` of `SprayParticles.h` and the `m_spray`
member; everything else in the map can be typed now. The map names the types of
`SprayTypes.h`, which section 2 writes, so the class compiles at the end of
Part 1, not before.

**This is `SeaObjects::Initialize`, as Part 1 has it**: the rock, then its
pipeline, each a step of its own so that each can fail with its own message:

```cpp
InitializationResult SeaObjects::Initialize(const DemoContext& context, const SceneRenderer& sceneRenderer,
                                            std::span<const VkImageView, SEA_CASCADE_COUNT> /*displacementMaps*/)
{
    m_context       = context;   // first, so Shutdown works however far this gets
    m_sceneRenderer = &sceneRenderer;

    // Section 2: the rock where SprayTypes.h says it stands.
    const glm::mat4 rockPlacement = glm::translate(glm::mat4(1.0f), glm::vec3(SPRAY_ROCK_X, SPRAY_ROCK_Y, SPRAY_ROCK_Z));
    if (auto result = LoadProp(scenesDirectory() / "Rock.usda", rockPlacement); !result) { return result; }

    if (auto result = CreatePipelines(); !result) { return result; }   // section 2

    m_reset = true;   // the probes, the foam, and the particles all start from nothing
    m_readbackPending.fill(false);
    return InitializationResult::success();
}
```

`m_context` first, as in every demo's `Setup`, so that `Shutdown` can run
however far this got. The displacement maps are the class's one door in, and
nothing reads them until section 4; until then the parameter's name is
commented out, so that the compiler does not warn that it is unused. Section 4
puts the name back and adds two steps before `CreatePipelines`. `m_reset` asks
the first frame of Part 2's passes to start from nothing: the GPU's buffers hold
whatever was in memory until a pass writes them.

**This is `SeaObjects::Shutdown`.** It destroys everything the class will own
by the end of the chapter, in reverse order. Handles that were never made are
null, and destroying a null handle does nothing, so it is right after a partial
`Initialize` and right in every part of the chapter. Only when `Initialize` never
ran at all is there no device to destroy anything with:

```cpp
void SeaObjects::Shutdown()
{
    // SeaDemo's Teardown waited for the device. Reverse order of Initialize; null handles are
    // no-ops. The settings are kept.
    const VkDevice device = m_context.vulkan.device;
    if (device == VK_NULL_HANDLE)
    {
        return;   // Initialize never ran
    }
    VkPipeline* pipelines[] = { &m_propPipeline, &m_fadePipeline, &m_impactPipeline };
    for (VkPipeline* pipeline : pipelines)
    {
        vkDestroyPipeline(device, *pipeline, nullptr);
        *pipeline = VK_NULL_HANDLE;
    }
    vkDestroyPipelineLayout(device, m_propLayout, nullptr);
    vkDestroyPipelineLayout(device, m_probeLayout, nullptr);
    vkDestroyDescriptorPool(device, m_probePool, nullptr);
    vkDestroyDescriptorSetLayout(device, m_probeSetLayout, nullptr);

    vkDestroySampler(device, m_localFoamSampler, nullptr);
    vkDestroySampler(device, m_repeatSampler, nullptr);
    vkDestroyImageView(device, m_localFoamView, nullptr);
    vmaDestroyImage(m_context.vulkan.allocator, m_localFoamImage, m_localFoamAllocation);
    for (AllocatedBuffer& readback : m_readback)
    {
        destroyBuffer(m_context.vulkan, readback);
    }
    destroyBuffer(m_context.vulkan, m_requests);
    destroyBuffer(m_context.vulkan, m_probes);
    for (GpuMesh& mesh : m_meshes)
    {
        destroyMesh(m_context.vulkan, mesh);
    }
    m_meshes.clear();
    m_parts.clear();

    m_propLayout       = m_probeLayout = VK_NULL_HANDLE;
    m_probePool        = VK_NULL_HANDLE;
    m_probeSetLayout   = VK_NULL_HANDLE;
    m_probeSet         = VK_NULL_HANDLE;
    m_localFoamSampler = m_repeatSampler = VK_NULL_HANDLE;
    m_localFoamView       = VK_NULL_HANDLE;
    m_localFoamImage      = VK_NULL_HANDLE;
    m_localFoamAllocation = VK_NULL_HANDLE;
}
```

### Where `SeaDemo` calls it

`SeaDemo` owns one. In `SeaDemo.h`, the include goes with the others,

```cpp
#include "PillowFort/Demos/Sea/SeaObjects.h"
```

and the member after `m_sky`:

```cpp
    // Chapters 31 and 32: a rock and a boat, the spray they throw, and the foam they leave.
    SeaObjects m_objects;
```

In `SeaDemo::Setup`, it is initialized after the sky and before
`CreateSurface`: the surface's set will name a foam map that `SeaObjects` makes
(section 7). It is handed the three displacement maps' views, the one door in:

```cpp
    // Chapter 31: before the surface too, whose set names the local foam map.
    const std::array<VkImageView, SEA_CASCADE_COUNT> displacementMaps{
        m_cascades[0].displacement.view, m_cascades[1].displacement.view, m_cascades[2].displacement.view };
    if (auto result = m_objects.Initialize(m_context, m_sceneRenderer, displacementMaps); !result) { return result; }
```

`m_sceneRenderer` is passed by reference and kept as a pointer: the props and
the spray draw with the camera's set 0, which belongs to the scene renderer.
`SeaDemo` outlives `SeaObjects` (it owns it), so the pointer never dangles.

In `SeaDemo::Teardown`, it goes just before the sky's `Shutdown`:

```cpp
    m_objects.Shutdown();   // Chapter 31
```

## 2. A rock

### The prop

The rock is a USD file, `Assets/Scenes/Rock.usda`: a sphere of radius 7 m cut
into 24 rings of 48 facets, each point pushed in or out by two smooth waves
over the sphere, so its outline is lumpy but has nothing hanging over the
water. It has no normals of its own, so Chapter 14's importer gives every
facet its own, which suits a rock. A short Python script,
`Assets/Scenes/make_sea_props.py`, writes it, and Chapter 32's boat beside it;
Appendix B has the script, and you run it once.

The rock stands with its middle 3 m under the mean sea level, at
`(0, −3, −70)`: 70 m in front of where Chapter 29's camera starts. Where a sphere
of radius 7 m meets a plane 3 m above its middle is a circle of radius
`√(7² − 3²) = 6.32` m, `SPRAY_ROCK_WATERLINE`. The lumps move the real
waterline in and out by up to a metre around that circle, which section 5 has
to live with.

### The twin structs

Everything the CPU and the shaders of this chapter must agree on is in one
header, read by both languages, like Chapter 30's `SeaTypes.h`. The rock's
numbers and `PropParameters`, the props' push constant, are this section's.
The rest is explained where it is used — the sample points in section 5, the
request list in section 6, the foam map in section 7 — but the class map
already names it, so type the whole header now and read it through once for the
shape.

**This is `Shaders/Sea/SprayTypes.h`**:

```cpp
/* Shaders/Sea/SprayTypes.h - the C++/GLSL twins of Chapters 31 and 32: the rock, the boat, and the
   spray they throw. GLSL includes it as "SprayTypes.h", C++ as "Sea/SprayTypes.h". */
#ifndef PF_SPRAY_TYPES_H
#define PF_SPRAY_TYPES_H

#include "SharedShaderTypes.h"   /* the vec4, mat4, and uint aliases, on the C++ side */

/* Section 2. The rock: where its middle is, and the radius of the circle where it meets the mean
   sea level. Rock.usda is a sphere of radius 7 m with its middle 3 m under the water. */
#define SPRAY_ROCK_X            0.0f
#define SPRAY_ROCK_Y           -3.0f
#define SPRAY_ROCK_Z          -70.0f
#define SPRAY_ROCK_WATERLINE    6.3f

/* Section 5. Where the sea is sampled for spray: points around the rock's waterline. One
   invocation each. */
#define SPRAY_ROCK_SAMPLES     96u
#define SPRAY_SAMPLE_COUNT     SPRAY_ROCK_SAMPLES
#define SPRAY_GROUP_SIZE       64

/* Section 6. The most new particles one frame can ask for. */
#define SPRAY_REQUEST_CAPACITY 4096u

/* Section 7. The local foam map: a square of sea, centred on the rock, that does not repeat. */
#define SPRAY_FOAM_SIZE      256.0f    /* metres along each side */
#define SPRAY_FOAM_TEXELS    512u      /* texels along each side: half a metre each */

#ifdef __cplusplus
    namespace pf::demos::sea {
    using shared::vec4;
    using shared::mat4;
    using shared::uint;
#endif

/* Section 6. One new particle the impact pass asks for (std430, 32 bytes). */
struct SprayRequest
{
    vec4 positionAndLifetime;   /*  0: xyz metres; w seconds it lives */
    vec4 velocity;              /* 16: xyz metres per second; w unused */
};

/* Push constants for the passes that read the sea: the impact pass (section 5), the local foam's
   fade (section 7), and the boat (Chapter 32). Each reads the fields it needs. */
struct SprayParameters
{
    vec4  patchSizes;           /*   0: xyz each cascade's patch size, as SeaParameters has them */
    vec4  weights;              /*  16: xyz the cascades in use */
    vec4  boatStart;            /*  32: xyz where the boat starts; w its heading, radians */
    float deltaTime;            /*  48: ocean seconds this step covers */
    float throttle;             /*  52: -1 full astern .. 1 full ahead */
    float rudder;               /*  56: -1 hard to port (left) .. 1 hard to starboard (right) */
    float sprayThreshold;       /*  60: m/s of water rising against an object before it sprays */
    float sprayRate;            /*  64: particles per second, per sample, per m/s over the threshold */
    float sprayLaunch;          /*  68: launch speed, m/s, per m/s over the threshold */
    float foamStamp;            /*  72: foam added per m/s over the threshold */
    float foamFade;             /*  76: seconds for the local foam to fade to 37% */
    uint  frameNumber;          /*  80: seeds the random numbers */
    uint  flags;                /*  84: SPRAY_FLAG_* */
    uint  padding0;             /*  88 */
    uint  padding1;             /*  92 */
};

/* SprayParameters::flags */
#define SPRAY_FLAG_RESET 1u     /* forget last frame's samples and foam */

/* Push constants for drawing the rock and the boat (section 2). */
struct PropParameters
{
    mat4 model;                 /*  0: the part's own placement, inside its prop */
    vec4 color;                 /* 64: rgb linear base color; w: 1 for the boat, whose placement is the GPU's */
    vec4 sunDirection;          /* 80: xyz the way sunlight travels */
    vec4 sunIrradiance;         /* 96: rgb, the scene's units */
};

#ifdef __cplusplus
    static_assert(sizeof(SprayRequest) == 32, "SprayRequest layout drifted.");
    static_assert(sizeof(SprayParameters) == 96, "SprayParameters layout drifted.");
    static_assert(offsetof(SprayParameters, deltaTime) == 48, "SprayParameters alignment drifted.");
    static_assert(sizeof(PropParameters) == 112, "PropParameters layout drifted.");
    }
#endif

#endif
```

`SprayParameters` is the push constant every pass that reads the sea shares,
96 bytes; each pass reads the fields it needs. Three of its fields, `boatStart`,
`throttle`, and `rudder`, are Chapter 32's boat. They are in the struct from the
start because C++ and every shader that includes the header share its layout,
and a field added in the middle later would move every offset after it; until
Chapter 32 nothing sets them, and they stay 0. `PropParameters`' `color.w` waits
for the boat in the same way: the rock always pushes 0 there.

### Loading it

Chapter 14 imports a USD file into a scene graph. The rock does not need a
scene graph: it needs its meshes on the GPU, where each part sits, and each
part's color. So `LoadProp` imports the file into a `Scene` of its own, asks it
for Chapter 12's flat draw list, uploads every mesh with Chapter 11's
`uploadMesh`, keeps one `PropPart` per draw item, and lets the scene go.

**This is `LoadProp`**:

```cpp
InitializationResult SeaObjects::LoadProp(const std::filesystem::path& file, const glm::mat4& placement)
{
    // Chapter 14's importer into a scene of its own, used once and dropped: the prop needs its
    // meshes, where each part sits, and each part's color, and nothing else.
    scene::Scene scene;
    if (auto result = usd_import::ImportUsdFile(file, scene); !result) { return result; }
    scene.UpdateWorldTransforms();
    std::vector<scene::DrawItem> draws;
    scene.CollectDraws(draws, nullptr);

    const uint32_t firstMesh = static_cast<uint32_t>(m_meshes.size());
    for (uint32_t mesh = 0; mesh < scene.MeshCount(); ++mesh)
    {
        m_meshes.push_back(uploadMesh(m_context.vulkan, scene.GetMesh(mesh).data));
        if (m_meshes.back().vertexBuffer.buffer == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Uploading a sea prop's mesh failed.");
        }
    }
    for (const scene::DrawItem& draw : draws)
    {
        m_parts.push_back(PropPart{
            .mesh    = firstMesh + draw.mesh,
            .submesh = draw.submesh,
            .model   = placement * draw.world,
            .color   = glm::vec3(scene.GetMaterial(draw.material).baseColor),
        });
    }
    return InitializationResult::success();
}
```

`placement` puts the whole prop in the world: for the rock, a translation to
where `SprayTypes.h` says it stands, multiplied in front of each part's own
matrix from the file. `firstMesh` turns the scene's mesh indices, which start at
0 for every file, into indices into `m_meshes`, which holds every prop's.

### Drawing it

The shaders are Chapter 11's mesh shaders cut down to what a rock needs:
Lambert in the sun's units (Chapter 30 sections 4 and 10), so the rock is lit
by the same sun as the water and brightens with "Sun strength", and never
quite black, a quarter of its color standing in for the sky's light.

**This is `Shaders/Sea/SeaProp.vert.glsl`**:

```glsl
// Shaders/Sea/SeaProp.vert.glsl - the rock (section 2), placed by its push constant.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "FrameBlock.glsl"      // set 0: frame.viewProjection
#include "SprayTypes.h"

layout(location = 0) in vec3 inPosition;   // Chapter 11's vertex: all four are declared, two are used
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUv;
layout(location = 3) in vec4 inTangent;

layout(push_constant) uniform PushConstants
{
    PropParameters prop;
};

layout(location = 0) out vec3 worldNormal;

void main()
{
    mat4 model  = prop.model;
    worldNormal = mat3(model) * inNormal;   // rotations and moves only, no scale: Chapter 11 section 13 not needed
    gl_Position = frame.viewProjection * model * vec4(inPosition, 1.0);
}
```

It is Chapter 11's vertex shader with one push constant for the part's place,
and set 0's camera. All four of Chapter 11's attributes are declared although
two are used, so that the pipeline's vertex input, which describes all four,
matches the shader.

**This is `Shaders/Sea/SeaProp.frag.glsl`**:

```glsl
// Shaders/Sea/SeaProp.frag.glsl - the rock and the boat, lit by the sea's sun (section 2; Chapter 32).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SprayTypes.h"

layout(push_constant) uniform PushConstants
{
    PropParameters prop;
};

layout(location = 0) in  vec3 worldNormal;
layout(location = 0) out vec4 outColor;

void main()
{
    // Lambert (Chapter 11 section 14) in the sun's units, never quite dark: a quarter for the sky.
    float lit   = max(dot(normalize(worldNormal), -prop.sunDirection.xyz), 0.0);
    vec3  color = prop.color.rgb * prop.sunIrradiance.rgb / 3.14159265 * (0.25 + 0.75 * lit);
    outColor = vec4(color, 1.0);
}
```

**This is `CreatePipelines`, as Part 1 has it**: the props' pipeline layout and
pipeline. Part 2 adds the compute passes' layout and pipelines in front of it.

```cpp
InitializationResult SeaObjects::CreatePipelines()
{
    // Section 2: the rock. Set 0 the camera.
    const VkDescriptorSetLayout frameSetLayout = m_sceneRenderer->FrameSetLayout();
    const VkPushConstantRange   propRange{ VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0,
                                           sizeof(PropParameters) };
    const VkPipelineLayoutCreateInfo propLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &frameSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &propRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &propLayoutInfo, nullptr, &m_propLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the sea's props.");
    }
    // Chapter 11's mesh pipeline: its vertex, counter-clockwise front faces, backs culled, in the
    // scene pass at the scene's sample count.
    const GraphicsPipelineDesc desc{
        .vertexShader     = "Sea/SeaProp.vert.spv",
        .fragmentShader   = "Sea/SeaProp.frag.spv",
        .vertexBindings   = meshVertexBindings(),
        .vertexAttributes = meshVertexAttributes(),
        .colorFormats     = { &m_context.formats.color, 1 },
        .depthFormat      = m_context.formats.depth,
        .depthTest        = true,
        .depthWrite       = true,
        .depthCompare     = VK_COMPARE_OP_LESS,
        .cullMode         = VK_CULL_MODE_BACK_BIT,
        .frontFace        = VK_FRONT_FACE_COUNTER_CLOCKWISE,
        .layout           = m_propLayout,
        .samples          = m_context.formats.samples,
    };
    m_propPipeline = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, desc);
    if (m_propPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the sea's prop pipeline failed.");
    }
    return InitializationResult::success();
}
```

The props' pipeline layout has the camera's set at 0, as every scene pipeline
does, and nothing else: a rock needs to know where the camera is and where it
stands itself, and the push constant says the second. The pipeline is Chapter
11's: its vertex format, counter-clockwise front faces with backs culled, depth
tested and written, in the scene pass at the scene's sample count (Chapter 18).

**This is `RecordDraw`**: one indexed draw per part, inside the scene pass.

```cpp
void SeaObjects::RecordDraw(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SeaParameters& sea) const
{
    // Section 2: inside the scene pass, with the camera's set.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_propPipeline);
    m_sceneRenderer->BindFrameSet(commandBuffer, m_propLayout, frameIndex);

    for (const PropPart& part : m_parts)
    {
        const GpuMesh&        mesh    = m_meshes[part.mesh];
        const scene::Submesh& submesh = mesh.submeshes[part.submesh];
        const PropParameters  prop{
            .model         = part.model,
            .color         = glm::vec4(part.color, 0.0f),
            .sunDirection  = sea.sunDirection,
            .sunIrradiance = sea.sunIrradiance,
        };
        vkCmdPushConstants(commandBuffer, m_propLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                           0, sizeof(prop), &prop);
        const VkDeviceSize offset = 0;
        vkCmdBindVertexBuffers(commandBuffer, 0, 1, &mesh.vertexBuffer.buffer, &offset);
        vkCmdBindIndexBuffer(commandBuffer, mesh.indexBuffer.buffer, 0, VK_INDEX_TYPE_UINT32);
        vkCmdDrawIndexed(commandBuffer, submesh.indexCount, 1, submesh.firstIndex, 0, 0);
    }
}
```

`SeaDemo::RecordSurface` calls it inside the scene pass, after the water and
before the sky, so that the sky lands only where neither the water nor the
rock did:

```cpp
    // Chapters 31 and 32: the rock and the boat.
    m_objects.RecordDraw(commandBuffer, frame.frameIndex, parameters);
```

## Checkpoint

Rerun `GenerateProjects.bat` (the new `.cpp` file must be in the project),
build, run `make_sea_props.py` once if you have not, and run with
`--demo Sea`. You can now see:

- **the rock, 70 m ahead**, dark and faceted, lit from the sun's side;
- **the waves on it.** Watch its waterline: the water climbs and falls on its
  sides as each wave passes, a metre or more for the swell's waves. The
  water passes straight through where the rock is — nothing yet tells the sea
  the rock is there, and nothing in this chapter will; section 8 says what
  would;
- the sky, the clouds, and Chapter 30's panels, all as before.

---

# Part 2 — Spray (sections 3-6)

A wave that reaches a rock has nowhere to go. It climbs the rock's face and
runs into it, and when it does that fast enough it breaks into spray. Part 2
first finds where the water is at any point (section 3) and gives every new
compute pass one set to read the sea through (section 4). Then it measures how
fast the water comes at the rock at 96 points round its waterline (section 5),
and asks Chapter 21's particle system for spray wherever that is fast
(section 6).

## 3. Where the water is

### The question the maps do not answer

Chapter 29 section 9 made the displacement map: the texel for a point `g` of
the flat sea holds `D(g)`, how far the waves move that point — sideways in x
and z, and up in y. The vertex shader asks the map exactly the question it
answers: *where does this point of the flat sea go?* It takes a grid point and
moves it.

The rock, and Chapter 32's boat, ask a different question: *how high is the
water above this place?* The water above a place `p` is whichever point of the
flat sea landed there, the `g` with

$$
g + D_{xz}(g) = p
$$

and its height is `D_y(g)`. Reading the map at `p` itself gives the height of
the point that *started* at `p`, which has moved somewhere else. With
Chapter 30's choppy waves that is not a small error: a crest is pushed
sideways toward its own middle, which is what makes it sharp (Chapter 29
section 8), and reading at `p` puts every crest in the wrong place by up to the
waves' amplitude.

### Guessing and correcting

There is no formula that turns `D` around, but there is a way to find `g` by
guessing. Guess that the point above `p` started at `p`. Look up where that
guess really goes: it lands `D_xz(g)` away from where it started, and so misses
`p` by that much. Move the guess back by the miss and look again:

$$
g_{n+1} = p - D_{xz}(g_n)
$$

Each step the miss shrinks, because the displacement changes slowly from one
place to the next. If it changes by at most a fraction *f* per metre, the miss
is multiplied by about *f* each step. For a wave of amplitude *A*, wave number
*k*, and choppiness λ, that fraction is at most λ*Ak*: the number that, in
Chapter 29 section 9, folds a crest over when it passes 1. Below 1, every step
shrinks the miss.

A worked example, with one wave 60 m long (*k* = 2π / 60 = 0.105 rad/m), 1 m
high, at choppiness 1, which moves the point that starts at `g` by
`−sin(k g)` sideways and lifts it by `cos(k g)`. The water above `p = 10` m:

| Step | Guess `g` | Lands at | Miss | Height there |
| --- | --- | --- | --- | --- |
| 0 | 10.000 | 9.134 | −0.866 | 0.500 |
| 1 | 10.866 | 9.958 | −0.042 | 0.420 |
| 2 | 10.908 | 9.998 | −0.002 | 0.416 |
| 3 | 10.910 | 10.000 | −0.0001 | 0.415 |

Reading the map at `p` would have said 0.50 m. The water is really 0.415 m
high there, and three steps find it to a tenth of a millimetre. A real sea is
many waves at once, each with its own steepness, and the miss shrinks a little
slower, but three steps are still far closer than the sea's surface is drawn:
the surface's grid has a vertex every two metres.

### `SeaWater.glsl`

The guess-and-correct loop is wanted by this chapter's impact pass and by
Chapter 32's boat, so it lives in an include. It reads the cascades'
displacement maps exactly as Chapter 30's vertex shader does — each at its own
scale, `grid / L` plus half a texel (Chapter 30 section 4), weighted by the
panel's Solo — and adds them up. `textureLod` with level 0, because a compute
shader has no neighbouring pixels to pick a mip level from; the maps have one
level anyway.

**This is `Shaders/Sea/SeaWater.glsl`**:

```glsl
// Shaders/Sea/SeaWater.glsl - where the water is, for a compute pass that needs to know (Chapter 31
// section 3). An include, not a stage. It names the three displacement maps at set 0, bindings 0-2,
// which is where the sea's probe set puts them.
#ifndef PF_SEA_WATER_GLSL
#define PF_SEA_WATER_GLSL

layout(set = 0, binding = 0) uniform sampler2D displacementMap0;
layout(set = 0, binding = 1) uniform sampler2D displacementMap1;
layout(set = 0, binding = 2) uniform sampler2D displacementMap2;

// How far the sea moves the point of the flat sea at `grid`: the vertex shader's sum of the
// cascades (Chapter 30 section 4). textureLod, because a compute shader has no derivatives.
vec3 seaDisplacement(vec2 grid, vec4 patchSizes, vec4 weights)
{
    vec3 sum = vec3(0.0);
    sum += weights.x * textureLod(displacementMap0, grid / patchSizes.x + 0.5 / vec2(textureSize(displacementMap0, 0)), 0.0).xyz;
    sum += weights.y * textureLod(displacementMap1, grid / patchSizes.y + 0.5 / vec2(textureSize(displacementMap1, 0)), 0.0).xyz;
    sum += weights.z * textureLod(displacementMap2, grid / patchSizes.z + 0.5 / vec2(textureSize(displacementMap2, 0)), 0.0).xyz;
    return sum;
}

// What the sea did to the water that is now above the world point `position`: its displacement,
// whose y is the water's height there. The maps say where each point of the flat sea goes, not what
// lies above a place, so: guess the point that ends up here, see where it really goes, and move the
// guess back by the miss. Each step shrinks the miss by about lambda A k.
vec3 seaDisplacementAbove(vec2 position, vec4 patchSizes, vec4 weights)
{
    vec2 grid = position;
    for (int step = 0; step < 3; ++step)
    {
        grid = position - seaDisplacement(grid, patchSizes, weights).xz;
    }
    return seaDisplacement(grid, patchSizes, weights);
}

// The water's height above the world point `position`.
float seaHeight(vec2 position, vec4 patchSizes, vec4 weights)
{
    return seaDisplacementAbove(position, patchSizes, weights).y;
}

#endif
```

The include names three bindings, 0 to 2 of set 0. A shader that includes it
must be given a set with the three maps there; section 4 builds that set.
`seaDisplacementAbove` returns the whole displacement, not just the height,
because section 5 needs the sideways part too: how fast the water is moving.
`seaHeight`, the height alone, is what Chapter 32's boat asks for.

## 4. The probe set, and one more reader of the maps

### What the passes keep from frame to frame

The passes in this chapter remember things between frames: what each sample
point saw last frame (section 5), the list of particles asked for (section 6),
a map of foam (section 7). Each is written by one frame and read by the next,
so each lives as long as the demo, on the GPU.

The CPU reads one of these back every frame, the spray's counters (section 6),
so each readback buffer holds this, at the top of `SeaObjects.cpp` inside the
namespace. It is a struct of one member because Chapter 32 adds a second, the
boat's state, to the same copy:

```cpp
// Section 4: what one readback buffer holds: the spray's counters, for the panel (section 6).
struct ObjectReadback
{
    particles::ParticleCounters counters;
};
```

**This is `CreateBuffersAndImages`**:

```cpp
InitializationResult SeaObjects::CreateBuffersAndImages()
{
    // Two buffers the GPU keeps from frame to frame: what each sample point saw last frame
    // (section 5), and the list of particles asked for, with its count in front (section 6).
    m_probes   = createBuffer(m_context.vulkan, sizeof(glm::vec4) * SPRAY_SAMPLE_COUNT,
                              VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, false);
    m_requests = createBuffer(m_context.vulkan, 4 * sizeof(uint32_t) + sizeof(SprayRequest) * SPRAY_REQUEST_CAPACITY,
                              VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, false);
    if (m_probes.buffer == VK_NULL_HANDLE || m_requests.buffer == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the sea objects' buffers failed.");
    }

    // Section 6: Chapter 20 section 9's readback, one per frame in flight.
    for (AllocatedBuffer& readback : m_readback)
    {
        readback = createReadbackBuffer(m_context.vulkan, sizeof(ObjectReadback));
        if (readback.buffer == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a sea objects readback buffer failed.");
        }
    }

    // Section 7: the local foam map, in Chapter 30's foam format for the same reasons: rgba16f is
    // both a storage image and filterable everywhere.
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R16G16B16A16_SFLOAT,
        .extent        = { SPRAY_FOAM_TEXELS, SPRAY_FOAM_TEXELS, 1 },
        .mipLevels     = 1,
        .arrayLayers   = 1,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(m_context.vulkan.allocator, &imageInfo, &allocationInfo,
                       &m_localFoamImage, &m_localFoamAllocation, nullptr) != VK_SUCCESS)
    {
        return InitializationResult::failure("Creating the local foam map failed.");
    }
    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_localFoamImage,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
    };
    if (vkCreateImageView(m_context.vulkan.device, &viewInfo, nullptr, &m_localFoamView) != VK_SUCCESS)
    {
        return InitializationResult::failure("Creating the local foam map's view failed.");
    }

    // Two samplers, both linear. The cascades' maps repeat, as Chapter 30's sampler does (section 4);
    // the local foam does not, and past its edge reads the border: transparent black, no foam (section 7).
    VkSamplerCreateInfo samplerInfo{
        .sType        = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter    = VK_FILTER_LINEAR,
        .minFilter    = VK_FILTER_LINEAR,
        .mipmapMode   = VK_SAMPLER_MIPMAP_MODE_NEAREST,
        .addressModeU = VK_SAMPLER_ADDRESS_MODE_REPEAT,
        .addressModeV = VK_SAMPLER_ADDRESS_MODE_REPEAT,
        .addressModeW = VK_SAMPLER_ADDRESS_MODE_REPEAT,
    };
    if (vkCreateSampler(m_context.vulkan.device, &samplerInfo, nullptr, &m_repeatSampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the sea objects.");
    }
    samplerInfo.addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
    samplerInfo.addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
    samplerInfo.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
    samplerInfo.borderColor  = VK_BORDER_COLOR_FLOAT_TRANSPARENT_BLACK;
    if (vkCreateSampler(m_context.vulkan.device, &samplerInfo, nullptr, &m_localFoamSampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the local foam.");
    }

    // Two things before the first frame. The request count starts at zero; after that, the spray's
    // begin pass zeroes it every frame (section 6). The local foam goes to GENERAL and stays there
    // (section 7).
    immediateSubmit(m_context.vulkan, [&](VkCommandBuffer commandBuffer) {
        vkCmdFillBuffer(commandBuffer, m_requests.buffer, 0, 4 * sizeof(uint32_t), 0);
        memoryBarrier(commandBuffer, VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                      VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
        transitionImage(commandBuffer, m_localFoamImage,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    });
    return InitializationResult::success();
}
```

The two buffers are device-local storage buffers (Chapter 20 section 8). The
request list has one more use: it is cleared by `vkCmdFillBuffer` before the
first frame, so it is a transfer destination. The readback buffers are Chapter
20 section 9's, one per frame in flight. The foam map and its samplers are
section 7's; the repeating sampler is Chapter 30's, made again here because
`SeaObjects` takes the maps' views and nothing else of `SeaDemo`'s. The one-time
commands at the end are explained where they matter: the fill in section 6, the
foam's layout in section 7.

### One set for every reader of the sea

Every pass this chapter adds reads the displacement maps, and most of them read
or write the buffers above. They all use one descriptor set, the **probe set**,
named for what the passes do with it: probe the sea at a few points.

| Binding | What | Type | Who uses it |
| --- | --- | --- | --- |
| 0-2 | the cascades' displacement maps | combined image sampler | `SeaWater.glsl`, in every pass |
| 3 | the probes: last frame's water at each sample point | storage buffer | the impact pass (section 5) |
| 5 | the request list | storage buffer | the impact pass, which fills it, and the spray's begin and emit (section 6) |
| 6 | the local foam map | storage image | the impact pass and the fade (section 7) |

Binding 4 is missing on purpose. The request list is at 5 because the spray's
own set (section 6) is Chapter 21's five bindings plus the list, so the list is
5 there, and one include, `SprayRequests.glsl`, declares it for both sets.
Chapter 32 puts the boat's state in the gap. Bindings need not be numbered
without gaps; a set's layout lists the ones it has.

The three maps are three bindings, not an array of three, for Chapter 30
section 4's reason: synchronization validation follows a shader's reads through
single bindings, and the barriers on these maps are worth checking.

**This is `CreateProbeSet`**:

```cpp
InitializationResult SeaObjects::CreateProbeSet(std::span<const VkImageView, SEA_CASCADE_COUNT> displacementMaps)
{
    // One set for every pass that reads the sea:
    //   0-2  the cascades' displacement maps     sampled, as the surface's vertex shader reads them
    //   3    the probes                          section 5
    //   5    the request list                    section 6, at 5 because the spray's own set has it there
    //   6    the local foam map                  section 7
    // Binding 4 waits for Chapter 32's boat.
    const VkShaderStageFlags compute = VK_SHADER_STAGE_COMPUTE_BIT;
    const VkDescriptorSetLayoutBinding bindings[] = {
        { 0, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, compute, nullptr },
        { 1, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, compute, nullptr },
        { 2, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, compute, nullptr },
        { 3, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,         1, compute, nullptr },
        { 5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,         1, compute, nullptr },
        { 6, VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,          1, compute, nullptr },
    };
    const VkDescriptorSetLayoutCreateInfo layoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = static_cast<uint32_t>(std::size(bindings)),
        .pBindings    = bindings,
    };
    if (vkCreateDescriptorSetLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_probeSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the sea objects.");
    }

    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, SEA_CASCADE_COUNT },
        { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,         2 },
        { VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,          1 },
    };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 1,
        .poolSizeCount = static_cast<uint32_t>(std::size(poolSizes)),
        .pPoolSizes    = poolSizes,
    };
    if (vkCreateDescriptorPool(m_context.vulkan.device, &poolInfo, nullptr, &m_probePool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the sea objects.");
    }
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_probePool,
        .descriptorSetCount = 1,
        .pSetLayouts        = &m_probeSetLayout,
    };
    if (vkAllocateDescriptorSets(m_context.vulkan.device, &allocateInfo, &m_probeSet) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the sea objects.");
    }

    // The maps in the layout SeaDemo's hand-over leaves them in; the foam in GENERAL, always.
    std::array<VkDescriptorImageInfo, SEA_CASCADE_COUNT + 1> images{};
    for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
    {
        images[c] = { m_repeatSampler, displacementMaps[c], VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
    }
    images[SEA_CASCADE_COUNT] = { VK_NULL_HANDLE, m_localFoamView, VK_IMAGE_LAYOUT_GENERAL };
    const VkDescriptorBufferInfo probes{ m_probes.buffer, 0, VK_WHOLE_SIZE };
    const VkDescriptorBufferInfo requests{ m_requests.buffer, 0, VK_WHOLE_SIZE };
    std::array<VkWriteDescriptorSet, std::size(bindings)> writes{};
    for (uint32_t i = 0; i < writes.size(); ++i)
    {
        const uint32_t binding = bindings[i].binding;   // 4 is missing, so not i
        writes[i] = VkWriteDescriptorSet{
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = m_probeSet,
            .dstBinding      = binding,
            .descriptorCount = 1,
            .descriptorType  = bindings[i].descriptorType,
        };
        if (binding < 3)       { writes[i].pImageInfo  = &images[binding]; }             // the maps
        else if (binding == 3) { writes[i].pBufferInfo = &probes; }
        else if (binding == 5) { writes[i].pBufferInfo = &requests; }
        else                   { writes[i].pImageInfo  = &images[SEA_CASCADE_COUNT]; }   // the foam
    }
    vkUpdateDescriptorSets(m_context.vulkan.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
    return InitializationResult::success();
}
```

The maps are named in `SHADER_READ_ONLY_OPTIMAL`, the layout Chapter 30's
hand-over leaves them in after step 8; the foam map in `GENERAL`, the only
layout it is ever in. Because 4 is missing, a binding's number is not its place
in the `bindings` table, so the loop reads the number from the table.

`Initialize` gains the two steps, before `CreatePipelines`; put the name of the
`displacementMaps` parameter back too:

```cpp
    if (auto result = CreateBuffersAndImages(); !result)         { return result; }   // section 4
    if (auto result = CreateProbeSet(displacementMaps); !result) { return result; }   // section 4
    if (auto result = CreatePipelines(); !result)                { return result; }   // sections 2 and 4
```

The passes that read the sea will share one pipeline layout: the probe set and
a `SprayParameters`. It goes at the top of `CreatePipelines`, before the props'
layout, because sections 5 and 7 add pipelines that use it right after it:

```cpp
    // Section 4: the passes that read the sea share a layout, the probe set and a SprayParameters.
    const VkPushConstantRange probeRange{ VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(SprayParameters) };
    const VkPipelineLayoutCreateInfo probeLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_probeSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &probeRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &probeLayoutInfo, nullptr, &m_probeLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the sea objects.");
    }
```

### The maps get a new reader

Until now, only the surface's vertex shader read the displacement maps, and
Chapter 30's barriers say so. Step 8 hands each map from the compute pass that
wrote it to `VERTEX_SHADER`; step 1, next frame, takes it back from
`VERTEX_SHADER`. This chapter's passes are compute dispatches that run after
step 8 and sample the same maps. Both barriers change by one stage. With
Chapter 04 section 5's three questions:

- **Step 8, the hand-over.** Q1: the assemble pass's `COMPUTE_SHADER` writes
  must finish before the reads, which now happen in `VERTEX_SHADER` *and* in
  this chapter's `COMPUTE_SHADER`. Q2: those writes must be visible to sampled
  reads in both stages; the access, `SHADER_SAMPLED_READ`, is the same for both.
  Q3: unchanged, `GENERAL` to `SHADER_READ_ONLY_OPTIMAL`.

  In `SeaDemo::Record`, step 8, the displacement's destination becomes:

```cpp
        transitionImage(commandBuffer, cascade.displacement.image,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
```

- **Step 1, the return trip.** Q1: next frame's assemble pass rewrites the maps,
  so it must wait for every reader of this frame's maps: the vertex shader and
  now the compute passes too. Q2: the readers only read, so the source access
  stays `NONE`. Q3: unchanged.

  In step 1, the displacement's source becomes:

```cpp
        transitionImage(commandBuffer, cascade.displacement.image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
```

Step 1 begins with a `computeToComputeBarrier`, and it is tempting to think it
already covers the compute readers. It does not reach the layout transition.
Every barrier has two halves: the stages it **waits for**, which must finish
first, and the stages it **holds back**, which may not start until they have.
Two barriers chain — the second waits for what the first waited for — only
through a stage that is in the first one's held-back half and in the second
one's waited-for half:

```text
 computeToComputeBarrier   waits for: COMPUTE            holds back: COMPUTE ──┐
                                                                               │  a chain needs a stage in both;
 the transition            waits for: VERTEX | COMPUTE  ◄──────────────────────┘  VERTEX alone shares none
```

With `VERTEX_SHADER` alone in its first half, the transition shares nothing with
the barrier before it, and the layout change, and the assemble pass after it,
could start while last frame's compute passes still read the maps. So the
transition names `COMPUTE_SHADER` itself. Chapter 21 section 5 draws the same
kind of chain for its second rendering scope. The exit check has the control
for the hand-over: take `COMPUTE_SHADER` out of step 8's destination, and
synchronization validation reports the impact pass's reads of all three maps.

## 5. How fast the water comes at the rock

### Where to ask

The rock asks at 96 points on a circle round its middle, at the radius where
the mean sea meets it, `SPRAY_ROCK_WATERLINE`. 96 points on a circle 40 m round
are one every 41 cm, close enough that a wave hitting the rock is seen at
several points at once. The circle is the rock's average waterline; its lumps
put the real face up to a metre inside or outside it. Spray that starts inside
the rock is hidden by the rock for the moment it takes to come out, which looks
like water bursting off the face, so the circle is good enough. Each point also
has a direction, **out**: away from the rock's middle, along the ground.

### Two ways the water comes at the rock

Water reaches the face of a rock in two ways, and spray comes from both:

- **It climbs it.** The water's surface at the face rises. Measure how deep the
  point at the mean waterline is under the water, its **submersion**
  `s = h − y`, where `h` is the water's height above the point and `y` the
  point's own height (0, for the rock). A rising sea makes `s` grow.
- **It runs into it.** Under a wave, the water moves sideways as well as up and
  down, forward under a crest and back under a trough: the sideways part of
  Chapter 29 section 8's choppy displacement. Where it moves toward the rock, it
  is stopped by the face, and its speed has to go somewhere.

Both are speeds, and neither is in the maps. The maps hold where the water *is*
this frame, not how fast it moves. A speed is a change divided by the time it
took: the probe buffer keeps, for every point, what the last frame saw there,
and this frame's value minus last frame's, divided by the frame's time, is the
speed.

$$
\text{rise} = \frac{s_\text{now} - s_\text{last}}{\Delta t}
\qquad
\text{flow} = \frac{D_{xz,\text{now}} - D_{xz,\text{last}}}{\Delta t}
$$

`D_xz` is the sideways displacement of the water above the point, which
`seaDisplacementAbove` returns with the height. Only the part of the flow
toward the rock counts: `inward = −flow · out`. The two add up to the speed at
which the water comes at the rock:

$$
\text{impact} = \max(\text{rise}, 0) + \max(\text{inward}, 0)
$$

A worked example. At 60 frames a second, Δ*t* = 1/60 s. A point's submersion
goes from 0.100 m to 0.125 m in one frame: `rise = 0.025 × 60 = 1.5` m/s. The
water above it moved 0.010 m toward the rock in the same frame: `inward = 0.6`
m/s. The impact is 2.1 m/s. A water surface falling away, or flowing out from
the rock, adds nothing: that is what `max(…, 0)` says.

The impact is clamped at 20 m/s. Where Chapter 29 section 9's Jacobian folds a
crest over, the guess-and-correct of section 3 can jump from one side of the
fold to the other between frames, and the difference over one frame is then
huge without meaning anything.

**The threshold.** A gentle sea rises and falls against a rock without throwing
spray. Only the part of the impact above a threshold, "Threshold" in the panel,
1 m/s by default, counts, and the rest of the chapter calls it the
**strength**: `strength = impact − threshold`. Above, in the example, the
strength is 1.1 m/s. A strength at or below 0 throws nothing; section 6 turns a
positive one into particles and section 7 into foam.

### The impact pass

One invocation per sample point, in groups of 64. **This is
`Shaders/Sea/SprayImpact.comp.glsl`, as section 5 has it**:

```glsl
// Shaders/Sea/SprayImpact.comp.glsl - one invocation per point where the sea meets the rock: how
// fast the water comes at it, and where that is fast, spray to ask for and foam to leave
// (sections 5-7).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SprayTypes.h"
#include "SeaWater.glsl"   // set 0, bindings 0-2: the sea's displacement maps

layout(local_size_x = SPRAY_GROUP_SIZE) in;

// Per point, what the last frame saw: x how deep under the water the point was, yz the water's
// horizontal displacement there.
layout(set = 0, binding = 3, std430) buffer ProbeBuffer { vec4 probes[]; };

layout(push_constant) uniform PushConstants
{
    SprayParameters spray;
};

void main()
{
    uint id = gl_GlobalInvocationID.x;
    if (id >= SPRAY_SAMPLE_COUNT) { return; }

    // 1. Where the point is, which way is out from the object, and how fast the object moves there.
    vec3 point;
    vec3 outward;
    vec3 objectVelocity = vec3(0.0);
    if (id < SPRAY_ROCK_SAMPLES)
    {
        // Round the rock's waterline, at the mean sea level.
        float angle = 2.0 * 3.14159265 * float(id) / float(SPRAY_ROCK_SAMPLES);
        outward = vec3(cos(angle), 0.0, sin(angle));
        point   = vec3(SPRAY_ROCK_X, 0.0, SPRAY_ROCK_Z) + SPRAY_ROCK_WATERLINE * outward;
    }

    // 2. Section 5: how fast the water comes at the object. It climbs it: the point's depth under the
    //    water grows, whether the water rises or a bow drives down into a wave. And it runs into it:
    //    the water's own horizontal speed toward the object. Both are this frame against last frame's,
    //    which is this point's slot.
    vec3  water      = seaDisplacementAbove(point.xz, spray.patchSizes, spray.weights);
    float submersion = water.y - point.y;
    bool  reset      = (spray.flags & SPRAY_FLAG_RESET) != 0u || spray.deltaTime <= 0.0;
    vec4  previous   = reset ? vec4(submersion, water.xz, 0.0) : probes[id];
    probes[id]       = vec4(submersion, water.xz, 0.0);
    float time       = max(spray.deltaTime, 1e-4);
    float rise       = (submersion - previous.x) / time;
    vec2  flow       = (water.xz - previous.yz) / time;
    float inward     = -dot(flow, outward.xz);
    float impact     = min(max(rise, 0.0) + max(inward, 0.0), 20.0);   // m/s; a fold can spike it

    // 3. Only near the waterline does anything happen, and only the part of the impact past the
    //    threshold counts: the strength, which throws spray (section 6) and leaves foam (section 7).
    if (abs(submersion) > 1.0) { return; }
    float strength = impact - spray.sprayThreshold;
```

Sections 6 and 7 add the rest of `main`. Step 1 is written for any object at
the water's edge, though the rock is the only one so far: the `if` is always
true while every point is the rock's, and `objectVelocity` stays 0, because a
rock does not move. Chapter 32 puts sample points round a boat after these 96,
with an `else` that places them and gives them the hull's velocity.

The probe buffer, binding 3, holds one `vec4` per point: x the submersion, y
and z the water's sideways displacement, as this frame found them for next
frame to compare with. When there is no last frame to compare with — the first
frame, after "Start again", or a paused sea whose Δ*t* is 0 — the point compares
with itself, and every speed is 0.

Step 3 is a short cut with a reason: a point more than a metre above or below
the water is not at the water's edge, so whatever the water does there throws
nothing. For the rock this happens in a trough of the swell, when the waterline
drops below the circle of points. Its last line is the strength, for the steps
that sections 6 and 7 add after it.

### What the pass is pushed

**This is `PackSpray`.** It copies the sea's patch sizes, weights, and frame
time out of Chapter 30's `SeaParameters`, so the impact pass reads exactly the
sea the surface draws, and adds the panel's settings:

```cpp
SprayParameters SeaObjects::PackSpray(const SeaParameters& sea) const
{
    return SprayParameters{
        .patchSizes     = sea.patchSizes,
        .weights        = sea.weights,
        .deltaTime      = sea.deltaTime,
        .sprayThreshold = m_settings.sprayThreshold,
        .sprayRate      = m_settings.sprayRate,
        .sprayLaunch    = m_settings.sprayLaunch,
        .foamStamp      = m_settings.foamStamp,
        .foamFade       = m_settings.foamFade,
        .frameNumber    = m_frameNumber,
        .flags          = (m_reset ? SPRAY_FLAG_RESET : 0u),
    };
}
```

`m_frameNumber` counts frames, for the random numbers of section 6. The fields
it leaves out, the boat's, are 0.

The pass's pipeline goes in `CreatePipelines`, after the probe layout: a table
of passes, one row so far, which section 7 grows by one:

```cpp
    const struct { VkPipeline* pipeline; const char* shader; } passes[] = {
        { &m_impactPipeline, "Sea/SprayImpact.comp.spv" },     // section 5
    };
    for (const auto& pass : passes)
    {
        *pass.pipeline = createComputePipeline(m_context.vulkan.device, m_context.pipelineCache, pass.shader, m_probeLayout);
        if (*pass.pipeline == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a sea objects compute pipeline failed.");
        }
    }
```

## 6. Spray the GPU asks for

### Who decides

In Chapter 21 the CPU decided how many particles to make each frame, from a
rate and the frame's time, and pushed the number. Here the number depends on
where the waves hit the rock, which only the GPU knows this frame. The CPU could
find out by reading the impact pass's results back, a frame or two later
(Chapter 20 section 9), and spray would lag the waves that threw it by that
much. So the GPU decides: the impact pass writes a **request** for every
particle it wants, and Chapter 21's begin pass, instead of reading a count the
CPU pushed, reads how many requests there are. The CPU never learns the number
until the panel's readback, and never needs it.

### How many, from a strength

The number of particles a point asks for is a rate times its strength times the
frame's time: 150 particles a second for each metre per second past the
threshold, by default. That is rarely a whole number. The point with strength
1.3 at 60 frames a second wants `150 × 1.3 / 60 = 3.25` particles this frame.

Rounding down would lose the quarter every frame, and a weak hit, wanting 0.4
a frame, would never spray at all. Rounding to the nearest would give that weak
hit nothing and a slightly stronger one, 0.6, a whole particle every frame,
two thirds too many. Instead, **round at random**: take the 3, and add one more
with a probability equal to the fraction left over, 0.25. Over many frames the
average is

$$
3 + 0.25 \times 1 + 0.75 \times 0 = 3.25
$$

exactly what was wanted, and the 0.4 hit sprays on two frames in five.

### Asking

**These are steps 5 and 6** of the impact pass's `main`, after step 3; section
7 puts a step 4 between them. Add the two includes they need beside the others
at the top of the file,

```glsl
#include "SprayRequests.glsl"   // set 0, binding 5: the requests, section 6
#include "Random.glsl"
```

and then:

```glsl
    // 5. Section 6: only past the threshold does the water throw spray. How many particles: the rate
    //    times the strength times the step. The fraction left over becomes one more particle as often
    //    as it is large, so the average comes out right.
    if (strength <= 0.0) { return; }
    uint  random = seedRandom(id, spray.frameNumber);
    float wanted = spray.sprayRate * strength * spray.deltaTime;
    uint  count  = uint(wanted) + (randomFloat(random) < fract(wanted) ? 1u : 0u);

    // 6. Ask for them, if there is room. atomicAdd hands out places as Chapter 21's lists
    //    do; past the capacity a request is dropped, never written out of bounds.
    uint first = atomicAdd(requestCount, count);
    for (uint i = 0u; i < count && first + i < SPRAY_REQUEST_CAPACITY; ++i)
    {
        // Up and out from the object, fanned by a random nudge, faster the harder the water hits.
        vec3  nudge     = vec3(randomFloat(random), randomFloat(random), randomFloat(random)) * 2.0 - 1.0;
        vec3  direction = normalize(outward * 0.4 + vec3(0.0, 1.0, 0.0) + 0.4 * nudge);
        float speed     = spray.sprayLaunch * strength * (0.6 + 0.8 * randomFloat(random));
        vec3  start     = vec3(point.x, water.y, point.z) + outward * (0.3 * randomFloat(random));
        float lifetime  = 1.0 + randomFloat(random);
        requests[first + i] = SprayRequest(vec4(start, lifetime), vec4(direction * speed + 0.5 * objectVelocity, 0.0));
    }
}
```

`seedRandom` and `randomFloat` are Chapter 21's: a different stream of random
numbers for each point and each frame.

Placing requests in a shared list is Chapter 20 section 8's `atomicAdd`: each
invocation adds how many it wants to the list's count, and gets back the count
before its add, which is where its own requests start. Two invocations asking
at once get places that do not overlap. The count can run past
`SPRAY_REQUEST_CAPACITY`, 4096; the loop stops at the capacity, so a request
past it is dropped, never written out of bounds.

Each request is a particle as the emit pass will make it. It starts on the
water's surface at the point, up to 30 cm out from the face. It flies up and
out — `out × 0.4 + up`, so mostly up, as water deflected by a wall is — fanned
by a random nudge, at a speed of "Launch", 10 m/s, per metre per second of
strength, give or take 40%. The strength-1.3 hit throws its spray at 8 to 18
m/s, up to about 10 m before drag and gravity turn it. It lives one to two
seconds. Half the object's own velocity is added, which for the rock is
nothing; Chapter 32's boat throws its spray forward with it.

**This is `Shaders/Sea/SprayRequests.glsl`**, the list, declared once for the
three shaders that use it:

```glsl
// Shaders/Sea/SprayRequests.glsl - the list of new particles the impact pass asks for (Chapter 31
// section 6). An include: the probe set and the spray's particle set both name it at binding 5 of
// set 0, so the impact pass that fills it and the passes that read it declare it once, here.
#ifndef PF_SPRAY_REQUESTS_GLSL
#define PF_SPRAY_REQUESTS_GLSL

#include "SprayTypes.h"

layout(set = 0, binding = 5, std430) buffer RequestBuffer
{
    uint         requestCount;   // appended to with atomicAdd; may run past the capacity
    uint         padding0;
    uint         padding1;
    uint         padding2;
    SprayRequest requests[];     // SPRAY_REQUEST_CAPACITY of them
};

#endif
```

The count is first, with three words of padding, so that the requests after
it start 16 bytes in, as a `vec4` must in std430.

### Chapter 21's particles, a second time

**This is `SprayParticles.h`**:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 31: Chapter 21's GPU particles, copied and narrowed to spray thrown by the sea
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Sea/SprayParticles.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"
#include "Particles/ParticleTypes.h"   // Chapter 21's structs, used as they are
#include "Sea/SprayTypes.h"

#include <cstdint>

namespace pf::demos::sea {

// Section 6. Chapter 21's particle system, its second user: the same pool, lists, counters, and
// indirect arguments, the same reset, simulate, and end passes and the same billboards, with a begin
// and an emit of its own. Its emitter is a list of requests that the impact pass fills on the GPU.
// A third user should move this into VulkanGraphics as a GpuParticles that takes its emit and
// simulate shaders as parameters.
class SprayParticles
{
public:
    // Spray never needs Chapter 21's million: a few thousand a second, living a second or two.
    static constexpr uint32_t CAPACITY = 1u << 16;

    // `requests` is the list the impact pass fills: the request count, then SprayRequest[SPRAY_REQUEST_CAPACITY].
    // It is the caller's; the begin and emit passes read it, and begin zeroes its count.
    InitializationResult Initialize(const vulkan_graphics::VulkanContext& vulkan, VkPipelineCache pipelineCache,
                                    const vulkan_graphics::SceneFormats& formats, VkDescriptorSetLayout frameSetLayout,
                                    VkBuffer requests);
    void Shutdown();   // device idle first; safe after a partial Initialize, or none

    VkBuffer CounterBuffer() const { return m_counters.buffer; }   // for a readback copy

    // Before the scene pass: begin, emit, simulate, and end, each with Chapter 21's barrier after it.
    // `reset` frees every particle first. The caller's earlier barrier covers last frame's readers.
    void RecordSimulation(VkCommandBuffer commandBuffer, float deltaTime, float drag, bool reset);

    // After the scene pass: Chapter 21's second rendering scope, blended over what the scene drew.
    void RecordDraw(VkCommandBuffer commandBuffer, const RecordContext& frame,
                    const vulkan_graphics::SceneRenderer& sceneRenderer,
                    const particles::ParticleAppearance& appearance) const;

private:
    vulkan_graphics::VulkanContext m_vulkan;
    VkPipelineCache                m_pipelineCache = VK_NULL_HANDLE;
    vulkan_graphics::SceneFormats  m_formats;

    vulkan_graphics::AllocatedBuffer m_particles;    // Particle[CAPACITY]
    vulkan_graphics::AllocatedBuffer m_deadList;     // uint[CAPACITY]
    vulkan_graphics::AllocatedBuffer m_aliveLists;   // uint[2 * CAPACITY]
    vulkan_graphics::AllocatedBuffer m_counters;     // ParticleCounters
    vulkan_graphics::AllocatedBuffer m_indirect;     // ParticleIndirect

    VkDescriptorSetLayout m_setLayout      = VK_NULL_HANDLE;   // Chapter 21's five bindings, and the requests at 5
    VkDescriptorPool      m_descriptorPool = VK_NULL_HANDLE;
    VkDescriptorSet       m_set            = VK_NULL_HANDLE;

    VkPipelineLayout m_computeLayout    = VK_NULL_HANDLE;
    VkPipeline       m_resetPipeline    = VK_NULL_HANDLE;   // Chapter 21's
    VkPipeline       m_beginPipeline    = VK_NULL_HANDLE;
    VkPipeline       m_emitPipeline     = VK_NULL_HANDLE;
    VkPipeline       m_simulatePipeline = VK_NULL_HANDLE;
    VkPipeline       m_endPipeline      = VK_NULL_HANDLE;   // Chapter 21's
    VkPipelineLayout m_drawLayout       = VK_NULL_HANDLE;
    VkPipeline       m_drawPipeline     = VK_NULL_HANDLE;   // Chapter 21's billboards, premultiplied

    uint32_t m_currentList = 0;   // the alive list holding the live particles
};

} // namespace pf::demos::sea
```

It is Chapter 21's system with the demo taken out of it: the five buffers of
its section 1, one copy each, the set, the compute passes and their barriers of
its sections 3 and 4, and the billboards of its section 5. What changes is small:

- **The pool is 65,536 particles**, not a million. Spray is a few thousand a
  second, living a second or two.
- **Binding 5 is the request list.** It belongs to `SeaObjects` (the impact pass
  writes it through the probe set), and `SprayParticles` is handed it.
- **Three of the five passes are Chapter 21's shader files, as they are**:
  reset, simulate, and end. Simulate's ground is put 1 km below the sea, so it
  never bounces anything: spray falls back into the water, where the water's
  depth test hides it, and dies of age.
- **Begin and emit are new**, and short.

Its `Initialize` creates the five buffers, the set with the request list at
binding 5, Chapter 21's compute layout and five pipelines, and Chapter 21's
billboard pipeline. `RecordDraw` is Chapter 21 section 5's second rendering
scope, handed the scene renderer and the appearance rather than owning them.
`Shutdown` is Chapter 21 section 9's teardown without the ground's pipeline and
layout, the query pool, the readback, and the scene renderer, with one draw
pipeline rather than two, behind a return when there is no device. You can
start both from the particles demo rather than retype them. Chapter 21's
structs live in its namespace, so the file takes the five it uses with a
`using particles::` line each; the branch `reference-latest` has the whole
file.
Here are the three places `Initialize` differs from Chapter 21's code. The
buffers, without Chapter 21's second copy for the CPU's emitter:

```cpp
    // Chapter 21 section 1's buffers, one copy each.
    const struct
    {
        AllocatedBuffer*   buffer;
        VkDeviceSize       size;
        VkBufferUsageFlags usage;
    } buffers[] = {
        { &m_particles,  sizeof(Particle) * CAPACITY,     VK_BUFFER_USAGE_STORAGE_BUFFER_BIT },
        { &m_deadList,   sizeof(uint32_t) * CAPACITY,     VK_BUFFER_USAGE_STORAGE_BUFFER_BIT },
        { &m_aliveLists, sizeof(uint32_t) * CAPACITY * 2, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT },
        { &m_counters,   sizeof(ParticleCounters),
          VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT },
        { &m_indirect,   sizeof(ParticleIndirect),
          VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT },
    };
```

The set's six buffers, the request list last (so Chapter 21's limit check asks
for six, not five):

```cpp
    const VkBuffer named[] = { m_particles.buffer, m_deadList.buffer, m_aliveLists.buffer, m_counters.buffer,
                               m_indirect.buffer, requests };
```

and the passes:

```cpp
    const struct { VkPipeline* pipeline; const char* shader; } passes[] = {
        { &m_resetPipeline,    "Particles/ParticleReset.comp.spv" },   // Chapter 21's
        { &m_beginPipeline,    "Sea/SprayBegin.comp.spv" },
        { &m_emitPipeline,     "Sea/SprayEmit.comp.spv" },
        { &m_simulatePipeline, "Particles/ParticleSimulate.comp.spv" },   // Chapter 21's
        { &m_endPipeline,      "Particles/ParticleEnd.comp.spv" },     // Chapter 21's
    };
```

**This is `SprayParticles::RecordSimulation`**: Chapter 21 section 4's steps 2
to 6, one after another, with Chapter 21's barriers between them:

```cpp
void SprayParticles::RecordSimulation(VkCommandBuffer commandBuffer, float deltaTime, float drag, bool reset)
{
    // Chapter 21's push constants, with the fields spray uses. No emitter: the requests are it. The
    // ground is far below the sea, so Chapter 21's simulate never bounces anything; spray falls back
    // into the water, where the sea's depth hides it, and dies of age.
    const uint32_t current = m_currentList;
    const ParticleSimulation simulation{
        .gravity      = glm::vec4(0.0f, -9.81f, 0.0f, drag),
        .deltaTime    = deltaTime,
        .groundHeight = -1000.0f,
        .currentList  = current,
        .maxParticles = CAPACITY,
    };
    vkCmdPushConstants(commandBuffer, m_computeLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(simulation), &simulation);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_computeLayout, 0, 1, &m_set, 0, nullptr);

    // Chapter 21's reset, when asked: every slot free.
    if (reset)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_resetPipeline);
        vkCmdDispatch(commandBuffer, groupCount(CAPACITY, PARTICLE_GROUP_SIZE), 1, 1);
        computeToComputeBarrier(commandBuffer);
    }

    // Begin: the requests' count becomes the emission. Its writes are read as indirect arguments and
    // by the shaders after it: Chapter 21's barrier, unchanged.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_beginPipeline);
    vkCmdDispatch(commandBuffer, 1, 1, 1);
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT
                      | VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    // Emit and simulate, sized by the GPU.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_emitPipeline);
    vkCmdDispatchIndirect(commandBuffer, m_indirect.buffer, offsetof(ParticleIndirect, emit));
    computeToComputeBarrier(commandBuffer);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_simulatePipeline);
    vkCmdDispatchIndirect(commandBuffer, m_indirect.buffer, offsetof(ParticleIndirect, simulate));
    computeToComputeBarrier(commandBuffer);

    // End: the draw's arguments, read by the draw, its vertex shader, and a copy of the counters.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_endPipeline);
    vkCmdDispatch(commandBuffer, 1, 1, 1);
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT
                      | VK_PIPELINE_STAGE_2_COPY_BIT,
                  VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_READ_BIT
                      | VK_ACCESS_2_TRANSFER_READ_BIT);

    m_currentList = 1 - current;   // the survivors are in the other list now
}
```

Chapter 21's step 1, the return trip at the top of the frame, is not here:
`SeaObjects` makes one barrier at the top of its own frame that covers every
buffer it and the spray own (the end of this section shows it). Its readback of
the counters is `SeaObjects`' too.

**This is `Shaders/Sea/SprayBegin.comp.glsl`.** Chapter 21's begin made
`min(emitRequest, deadCount)` particles; this one makes as many as were
requested, capped by the list's capacity and by the dead list, and then sets
the request count back to 0, ready for next frame's impact pass:

```glsl
// Shaders/Sea/SprayBegin.comp.glsl - Chapter 21's begin pass, with the count of new particles read
// from the impact pass's requests instead of pushed by the CPU (section 6).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "../Particles/ParticleBuffers.glsl"   // Chapter 21's set 0, bindings 0-4, and its push constants
#include "SprayRequests.glsl"                  // set 0, binding 5

layout(local_size_x = 1) in;

void main()
{
    uint current = simulation.currentList;
    uint next    = 1u - current;

    // As many as were asked for, as fit in the list, and as the dead list can supply. Then the
    // request count starts again from zero for next frame's impact pass.
    uint emitCount = min(min(requestCount, SPRAY_REQUEST_CAPACITY), counters.deadCount);
    counters.emitCount = emitCount;
    requestCount       = 0u;

    // The rest is Chapter 21's.
    counters.aliveCount[next] = 0u;
    uint simulateCount = counters.aliveCount[current] + emitCount;
    indirect.emit     = DispatchIndirectCommand((emitCount     + PARTICLE_GROUP_SIZE - 1) / PARTICLE_GROUP_SIZE, 1u, 1u);
    indirect.simulate = DispatchIndirectCommand((simulateCount + PARTICLE_GROUP_SIZE - 1) / PARTICLE_GROUP_SIZE, 1u, 1u);
}
```

Zeroing the count here, in a pass that runs anyway, costs no extra command and
no extra barrier, as Chapter 21's begin did for the next alive list. The count
starts at 0 because `CreateBuffersAndImages` filled the list's first 16 bytes
with zeros, followed by a barrier from that fill (`CLEAR`) to the compute passes,
before the first frame.

**This is `Shaders/Sea/SprayEmit.comp.glsl`.** Chapter 21's emit, with the
particle's start taken from its request instead of an emitter and a cone:
request *i* becomes new particle *i*.

```glsl
// Shaders/Sea/SprayEmit.comp.glsl - Chapter 21's emit pass: one invocation per new particle, each
// started from its request rather than from an emitter (section 6).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "../Particles/ParticleBuffers.glsl"   // Chapter 21's set 0, bindings 0-4, and its push constants
#include "SprayRequests.glsl"                  // set 0, binding 5

layout(local_size_x = PARTICLE_GROUP_SIZE) in;

void main()
{
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.emitCount) { return; }   // the dispatch rounds up

    // Chapter 21's pop: begin made emitCount <= deadCount, so a free slot exists.
    uint deadSlot = atomicAdd(counters.deadCount, uint(-1)) - 1u;
    uint index    = deadList[deadSlot];

    // Request id becomes particle index: where, how fast, and how long, as the impact pass decided.
    SprayRequest request = requests[id];
    particles[index] = Particle(vec4(request.positionAndLifetime.xyz, 0.0),
                                vec4(request.velocity.xyz, request.positionAndLifetime.w));

    // Chapter 21's append to the current alive list.
    uint aliveSlot = atomicAdd(counters.aliveCount[simulation.currentList], 1u);
    aliveLists[simulation.currentList * simulation.maxParticles + aliveSlot] = index;
}
```

### Wiring it in

In `SeaObjects::Initialize`, after `CreatePipelines`, the spray is initialized
with the scene renderer's set 0 layout, for the billboards, and the request
list:

```cpp
    // Section 6: Chapter 21's particles, fed by the request list.
    if (auto result = m_spray.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats,
                                         sceneRenderer.FrameSetLayout(), m_requests.buffer);
        !result)
    {
        return result;
    }
```

In `SeaObjects::Shutdown`, first:

```cpp
    m_spray.Shutdown();
```

Now put back the `#include` of `SprayParticles.h` and the `m_spray` member that
section 1 left out of the header.

**This is `RecordSpray`.** The spray is lit as Chapter 30's foam is, white in
the sun's units, so it dims and brightens with the sun; it starts at "Opacity"
and fades to a third of it, and grows to three times its size as it spreads:

```cpp
void SeaObjects::RecordSpray(VkCommandBuffer commandBuffer, const RecordContext& frame, const SeaParameters& sea) const
{
    // Section 6: Chapter 21's billboards, white in the sun's units, as the foam is (Chapter 30 section 8).
    const glm::vec3 color = scene::srgbToLinear(m_settings.sprayColor) * glm::vec3(sea.sunIrradiance) / 3.14159265f;
    const particles::ParticleAppearance appearance{
        .startColor = glm::vec4(color, m_settings.sprayOpacity),
        .endColor   = glm::vec4(color, 0.3f * m_settings.sprayOpacity),
        .startSize  = m_settings.spraySize,
        .endSize    = 3.0f * m_settings.spraySize,
    };
    m_spray.RecordDraw(commandBuffer, frame, *m_sceneRenderer, appearance);
}
```

Chapter 21 draws its particles in a second rendering scope after the scene
pass, single-sampled, blended over the resolved color and depth-tested against
the resolved depth (Chapter 21 section 5). So `SeaDemo::Record` calls it right
after `RecordSurface`, which ends the scene pass, and before the timestamp
after the surface:

```cpp
    m_objects.RecordSpray(commandBuffer, frame, PackSurface());   // Chapter 31: over the finished scene
```

### The counters, for the panel

The panel shows how many particles are alive. That is Chapter 21 section 7's
readback of the counters: copied to this frame's readback buffer at the end of
`RecordSimulation`, read on the CPU when this frame's slot comes round again,
after its fence. Section 4's `ObjectReadback` is what each readback buffer
holds.

**This is `ReadResults`**:

```cpp
void SeaObjects::ReadResults(uint32_t frameIndex)
{
    // Chapter 20 section 9: this slot's fence has been waited on, so its copy is complete.
    if (m_readbackPending[frameIndex])
    {
        ObjectReadback latest{};
        readBuffer(m_context.vulkan, m_readback[frameIndex], &latest, sizeof(latest));
        m_counters = latest.counters;
        m_readbackPending[frameIndex] = false;
    }
}
```

`SeaDemo::Record` calls it at the top of the frame, beside reading its own
timestamps, which follow the same rule:

```cpp
    m_objects.ReadResults(frame.frameIndex);   // Chapter 31: what this slot copied out last time
```

Alive is the pool's size minus the dead list's count: every slot is either on
the dead list or holds a live particle.

### The frame, as section 6 has it

Everything the spray needs is in place, and `RecordSimulation` puts it in order.
**This is `SeaObjects::RecordSimulation`, as section 6 has it**:

```cpp
void SeaObjects::RecordSimulation(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SeaParameters& sea)
{
    const SprayParameters spray = PackSpray(sea);

    // 1. Return trips. Last frame's compute passes wrote every buffer here; its draw read the spray,
    //    and its copy read the counters out. Chapter 21's barrier, for all of them at once.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT
                      | VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_probeLayout, 0, 1, &m_probeSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_probeLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(spray), &spray);

    // 4. Section 5: where the water comes at the rock fast, spray is asked for. The spray's begin
    //    pass reads the requests next.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_impactPipeline);
    vkCmdDispatch(commandBuffer, groupCount(SPRAY_SAMPLE_COUNT, SPRAY_GROUP_SIZE), 1, 1);
    computeToComputeBarrier(commandBuffer);

    // 5. Section 6: Chapter 21's frame, its emission sized by the requests.
    m_spray.RecordSimulation(commandBuffer, sea.deltaTime, m_settings.sprayDrag, m_reset);

    // 7. Section 6: Chapter 20 section 9's readback, the spray's counters for the panel.
    const VkBufferCopy counterRegion{ .srcOffset = 0, .dstOffset = offsetof(ObjectReadback, counters),
                                      .size = sizeof(particles::ParticleCounters) };
    vkCmdCopyBuffer(commandBuffer, m_spray.CounterBuffer(), m_readback[frameIndex].buffer, 1, &counterRegion);
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    m_readbackPending[frameIndex] = true;

    m_reset = false;
    ++m_frameNumber;
}
```

Step by step:

1. **Return trips.** One global memory barrier covers every buffer: Chapter
   21's return trip, whose source names every stage that touched them last
   frame — the compute passes that wrote them, the draw that read the spray's
   indirect arguments and particles, and the copy that read the counters.
4. **The impact pass**, then a barrier: the spray's begin pass reads the request
   count and the emit pass the requests. The exit check's control removes this
   one.
5. **The spray**: Chapter 21's frame, sized by the requests.
7. **The readback**: Chapter 21's end barrier already made the counters
   visible to the copy, and the copy's own barrier makes its result visible to
   the CPU after the fence.

The numbers have gaps. Section 7 fills steps 2 and 6, the local foam's fade and
its hand-over, and Chapter 32 fills step 3, the boat. The steps are numbered as
the finished function numbers them, so nothing is renumbered when they arrive.

`SeaDemo::Record` calls `RecordSimulation` after the sky's `Update` and before
the timestamp that closes Chapter 30's "maps": the maps have been handed over by
then, and the scene pass after it draws what the passes decided.

```cpp
    // Chapters 31 and 32: the rock and the boat ask the sea where it is; the boat moves, the spray with it.
    m_objects.RecordSimulation(commandBuffer, frame.frameIndex, PackSurface());
```

Chapter 30's panel's "maps" time now includes this chapter's compute passes.

### The panel

**This is `SeaObjects::Update`, as section 6 has it**: a window with the
spray's settings and the particle count. It is named "Rock and boat" for what
it holds once Chapter 32 has put the boat in it, and the boat's settings will
make it taller than the room below it at 720 pixels, so it takes Chapter 09
section 6's height limit from the start, from
`PillowFort/DebugPanels/DemoPanel.h`:

```cpp
void SeaObjects::Update()
{
    ImGui::SetNextWindowPos(ImVec2(360.0f, 275.0f), ImGuiCond_FirstUseEver);   // under "Sea preview"
    ImGui::SetNextWindowCollapsed(true, ImGuiCond_FirstUseEver);              // a title bar until clicked
    debug_panels::stopNextWindowAtScreenBottom();                              // open, taller than the room left
    if (ImGui::Begin("Rock and boat"))
    {
        if (ImGui::Button("Start again"))
        {
            m_reset = true;
        }

        ImGui::SeparatorText("Spray (sections 5 and 6)");
        ImGui::SliderFloat("Threshold (m/s)", &m_settings.sprayThreshold, 0.0f, 5.0f);
        ImGui::SliderFloat("Rate", &m_settings.sprayRate, 0.0f, 1000.0f, "%.0f");
        ImGui::SliderFloat("Launch", &m_settings.sprayLaunch, 0.0f, 20.0f);
        ImGui::SliderFloat("Drag", &m_settings.sprayDrag, 0.0f, 4.0f);
        ImGui::SliderFloat("Size (m)", &m_settings.spraySize, 0.05f, 1.0f);
        ImGui::SliderFloat("Opacity", &m_settings.sprayOpacity, 0.0f, 1.0f);
        ImGui::ColorEdit3("Spray", &m_settings.sprayColor.x);
        ImGui::Text("%u particles alive", SprayParticles::CAPACITY - m_counters.deadCount);
        ImGui::Text("%u new this frame", m_counters.emitCount);
    }
    ImGui::End();
}
```

"Start again" sets `m_reset`, which the next frame packs into the flags: the
probes compare with themselves, and the spray's reset pass frees every
particle. `SeaDemo::Update` calls it after the camera's controls:

```cpp
    m_objects.Update();   // Chapter 31: its panel
```

## Checkpoint

Rerun `GenerateProjects.bat`, build, and run with `--demo Sea`. Fly to the far
side of the rock from the camera's start, the side the wind's waves come from:
to about `(−6, 4, −100)`, looking back toward the start. Open "Rock and boat".
You can now see:

- **waves breaking on the rock.** As a crest reaches the face, white spray
  bursts up and out along the part of the rock it hits, several metres high,
  and falls back; between crests, nothing. The swell's bigger waves throw more;
- the panel's particle count rising into the thousands as a wave hits and
  falling back as the spray dies. "Threshold" at 0.5 m/s makes the rock spray
  at every wave; at 3 m/s, almost never. "Launch" at 4 halves the spray's
  height.

The water where the waves hit stays as it was: the foam they leave is Part 3's.

---

# Part 3 — Foam that stays (sections 7-8)

Part 3 keeps a record of where the waves hit: foam in a map of its own, faded
over seconds and drawn on the water (section 7). Then it reads the whole frame
in order (section 8).

## 7. Foam that does not repeat

### Why Chapter 30's foam maps cannot hold it

Where the waves hit the rock, the water should stay white for a while, as it
does behind a breaking crest. Chapter 30 already has foam that lingers: each
cascade's foam map, faded and topped up every frame. But those maps **repeat**.
Each covers one patch, 250 m, 37 m, or 7 m, and the sampler's `REPEAT` lays it
over the whole sea. Foam stamped into cascade 0's map at the rock would appear
at the rock, and also 250 m to its left, 250 m behind it, and in every other
patch of the sea.

So the rock's foam gets a map of its own that does not repeat: **the local foam
map**, a square of sea 256 m across centred on the rock, 512 texels a side, half
a metre per texel. It is `rgba16f`, like Chapter 30's foam, and only its red
channel is used; 512 × 512 texels of 8 bytes are 2 MB. Outside the square, the
surface reads no foam, because its sampler clamps to a border of transparent
black. Chapter 32's boat leaves its wake in the same map, and so leaves none
outside it; section 8 says what would carry a wake further.

### Stamping and fading

Each frame the map does two things. A **fade** pass multiplies every texel by
`exp(−Δt / τ)`, Chapter 30 section 8's fade, with τ the panel's "Local foam
fade", 8 s: after 8 s a patch of foam is at 37%, after 24 s at 5%. Then the
impact pass **stamps** fresh foam at every point where the water hit: "Foam per
m/s" times the strength, into a small disc of texels round the point. A stamp
keeps the larger of what is there and what it brings, so a second stamp on the
same patch tops it up instead of piling past white.

**This is `Shaders/Sea/SeaLocalFoam.comp.glsl`**, the fade:

```glsl
// Shaders/Sea/SeaLocalFoam.comp.glsl - the local foam map's fade, before this frame's foam is added
// (section 7): Chapter 30's fade, with no Jacobian, because this map's foam comes from the rock and
// the boat.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SprayTypes.h"

layout(local_size_x = 8, local_size_y = 8) in;

layout(set = 0, binding = 6, rgba16f) uniform image2D localFoam;   // r: foam. Read, then written

layout(push_constant) uniform PushConstants
{
    SprayParameters spray;
};

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    if (any(greaterThanEqual(texel, imageSize(localFoam)))) { return; }

    // After a reset the image holds garbage: start from nothing.
    float foam = 0.0;
    if ((spray.flags & SPRAY_FLAG_RESET) == 0u)
    {
        foam = imageLoad(localFoam, texel).r * exp(-spray.deltaTime / spray.foamFade);
    }
    imageStore(localFoam, texel, vec4(foam));
}
```

After a reset the map holds whatever memory held, so the fade writes 0 instead
of reading it.

The stamp is a function above `main` in the impact pass, with the map at binding
6:

```glsl
layout(set = 0, binding = 6, rgba16f) uniform image2D localFoam;   // section 7: r, the foam
```

```glsl
// Section 7: adds foam in a small disc around a point, into the map that does not repeat.
// Neighbouring invocations may stamp the same texel at once; one write then wins, which for foam
// is harmless.
void stampFoam(vec2 position, float amount)
{
    vec2  origin  = vec2(SPRAY_ROCK_X, SPRAY_ROCK_Z) - 0.5 * SPRAY_FOAM_SIZE;
    vec2  centre  = (position - origin) / SPRAY_FOAM_SIZE * float(SPRAY_FOAM_TEXELS);
    ivec2 size    = imageSize(localFoam);
    for (int y = -2; y <= 2; ++y)
    {
        for (int x = -2; x <= 2; ++x)
        {
            ivec2 texel = ivec2(floor(centre)) + ivec2(x, y);
            if (any(lessThan(texel, ivec2(0))) || any(greaterThanEqual(texel, size))) { continue; }
            float falloff = max(1.0 - length(vec2(texel) + 0.5 - centre) / 2.5, 0.0);
            float old     = imageLoad(localFoam, texel).r;
            imageStore(localFoam, texel, vec4(max(old, min(amount * falloff, 1.0))));
        }
    }
}
```

The disc is five texels across, 2.5 m, with its foam falling off from the
middle. Two points 41 cm apart stamp overlapping discs, sometimes in the same
dispatch. When two invocations read and write the same texel at once, one
write is lost: the texel ends up with one of the two stamps instead of the
larger. For foam that is harmless — the next frame stamps again — and it saves
the atomics an exact answer would need.

**This is step 4** of the impact pass's `main`, between step 3 and section 6's
step 5. It uses the strength that step 3 ends with:

```glsl
    // 4. Section 7: foam where the water hits hard, more the harder it hits.
    float foam     = spray.foamStamp * strength;
    if (foam > 0.0)
    {
        stampFoam(point.xz, foam);
    }
```

### One layout, always

Chapter 30's foam maps change layout twice a frame: `GENERAL` for the compute
pass that writes them, `SHADER_READ_ONLY_OPTIMAL` for the fragment shader that
samples them. That cost Chapter 30 section 8 a trap: the return trip's old
layout must not be `UNDEFINED`, or the driver may throw the foam away.

The local foam map never leaves `GENERAL`. A storage image must be in `GENERAL`
to be written, and a sampled image may be in `GENERAL` too, so the writers and
the reader can all use it there. Its barriers are then about time and caches
only — the old and new layouts are the same, and there is no layout to get
wrong. `CreateBuffersAndImages` moves it to `GENERAL` once, before the first
frame, and every barrier after that leaves it there. On some GPUs, sampling an
image in `GENERAL` is a little slower than in `SHADER_READ_ONLY_OPTIMAL`,
because the driver must keep it in a form both kinds of access understand; for
one 2 MB map read once per pixel of water, that does not matter. Chapter 30's
maps keep their two layouts because they are Chapter 29's, used as they are.

The map's two barriers are in `RecordSimulation`, below. With the three
questions:

- **The return trip, at the top of the frame.** Q1: last frame's surface
  sampled the map in `FRAGMENT_SHADER`; this frame's fade reads and writes it in
  `COMPUTE_SHADER`. Q2: a read leaves nothing to make available, so the source
  access is `NONE`; the destination is a storage read and write. Q3: `GENERAL`
  to `GENERAL`.
- **The hand-over, after the impact pass.** Q1: the impact pass's
  `COMPUTE_SHADER` writes before the surface's `FRAGMENT_SHADER`. Q2:
  `SHADER_STORAGE_WRITE` made visible to `SHADER_SAMPLED_READ`. Q3: `GENERAL` to
  `GENERAL`.

### The surface reads it

The surface's set gains one binding, 11, after Chapter 30's ten. In
`SeaDemo::CreateSurface` the array grows by one:

```cpp
    // Set 1: one binding per cascade and map. Displacement at 0-2 for the vertex shader; normals at
    // 3-5, foam at 6-8 (section 8), the sky's cube at 9 (section 9), its clouds' at 10 (section 10),
    // and Chapter 31's local foam at 11 for the fragment shader.
    std::array<VkDescriptorSetLayoutBinding, 3 * SEA_CASCADE_COUNT + 3> bindings{};
```

and the new binding's image comes after the clouds' cube, with `SeaObjects`'
clamping sampler and in `GENERAL`:

```cpp
    infos[3 * SEA_CASCADE_COUNT + 2] = { m_objects.LocalFoamSampler(), m_objects.LocalFoamView(),
                                         VK_IMAGE_LAYOUT_GENERAL };   // Chapter 31: always in GENERAL
```

Binding 11 is a fragment-shader binding, like every binding from 3 on, so the
loop that fills in the layout's bindings needs no change.

In `SeaSurface.frag.glsl`, include the twins for where the map lies,

```glsl
#include "SprayTypes.h"   // Chapter 31: where the local foam map lies
```

declare the binding after the clouds' cube,

```glsl
layout(set = 1, binding = 11) uniform sampler2D localFoamMap;   // Chapter 31 section 7: the rock's and the boat's
```

and add its foam to the cascades', after `float foam = 1.0 - clear;`, by
Chapter 30's own rule for adding foam: a point is clear only if every map leaves
it clear.

```glsl
    // Chapter 31 section 7: the foam the rock and the boat leave, from a map of its own that covers
    // one square of sea and does not repeat. Outside the square, the sampler's border is no foam.
    vec2  localUv = (worldPosition.xz - vec2(SPRAY_ROCK_X, SPRAY_ROCK_Z)) / SPRAY_FOAM_SIZE + 0.5;
    float local   = texture(localFoamMap, localUv).r;
    foam = 1.0 - (1.0 - foam) * (1.0 - local);
```

The map is read at `worldPosition`, where the water is drawn, not at
`gridPosition`, where it started: the impact pass stamped the foam where the
water was.

### The frame, as Chapter 31 leaves it

`RecordSimulation` gains three things, all for the local foam. In step 1,
after the memory barrier, comes the foam's return trip, the first of its two
barriers above:

```cpp
    transitionImage(commandBuffer, m_localFoamImage,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                    VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
```

Step 2, the fade, after `vkCmdPushConstants` and before step 4. One invocation
per texel, in 8 × 8 groups, then a barrier, because the impact pass stamps into
the faded map:

```cpp
    // 2. Section 7: last frame's local foam fades.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_fadePipeline);
    vkCmdDispatch(commandBuffer, groupCount(SPRAY_FOAM_TEXELS, 8), groupCount(SPRAY_FOAM_TEXELS, 8), 1);
    computeToComputeBarrier(commandBuffer);   // the impact pass stamps into the faded map
```

And step 6, after the spray's `RecordSimulation`, the hand-over to the surface,
the second barrier:

```cpp
    // 6. Hand-overs. The local foam to the surface's fragment shader, still in GENERAL (section 7).
    transitionImage(commandBuffer, m_localFoamImage,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
```

Appendix A prints `RecordSimulation` whole, as this chapter leaves it. Only step
3 is still missing: it is Chapter 32's boat, which runs beside the fade and
shares its barrier.

The fade's pipeline is the table's second row, after the impact pass's:

```cpp
        { &m_fadePipeline,   "Sea/SeaLocalFoam.comp.spv" },    // section 7
```

The panel gains the foam's two settings, after the spray's:

```cpp
        ImGui::SeparatorText("Foam (section 7)");
        ImGui::SliderFloat("Foam per m/s", &m_settings.foamStamp, 0.0f, 2.0f);
        ImGui::SliderFloat("Local foam fade (s)", &m_settings.foamFade, 0.5f, 30.0f, "%.1f", ImGuiSliderFlags_Logarithmic);
```

"Start again" now clears the foam as well: with the reset flag set, the fade
writes 0 instead of reading what the map held.

## 8. The frame, and where to go from here

### The frame, in order

`SeaDemo::Record`, as it is now, with this chapter's additions:

```text
 top            Chapter 30's timestamps read; SeaObjects::ReadResults               section 6
 1-8            Chapter 30: return trips (displacement from VERTEX | COMPUTE),       section 4
                waves, FFT, maps, foam, hand-overs (displacement to VERTEX | COMPUTE)
 9              the sky's Update                                                     (Chapter 30)
 Chapter 31     SeaObjects::RecordSimulation:
                  1 return trips   2 local foam fades   barrier                     section 7
                  4 impact: probes, requests, foam stamps   barrier                  sections 5-7
                  5 Chapter 21's begin, emit, simulate, end                          section 6
                  6 hand-over: the local foam   7 readback                           sections 6, 7
 10             the scene pass: the sea (+ local foam), the rock, the sky            sections 2, 7
 Chapter 31     SeaObjects::RecordSpray: Chapter 21's second scope                   section 6
                the scene target back to the engine
```

### What it costs

The new compute passes are small next to Chapter 30's FFTs: the impact pass is
96 invocations, each reading the three maps four times (section 3's three
guesses and the answer); the fade touches
262,144 texels once; the spray's passes are Chapter 21's, at a few thousand
particles. Chapter 30's panel times them inside "maps", and the spray's draw
inside "surface". Set "Rate" to 0 to see what the spray adds on your GPU.

### Where to go from here

- **The water does not know the rock is there.** Waves pass through it and
  carry on behind it as if it were not there. A real rock reflects waves and
  shelters the water behind it. That takes a simulation of the water itself
  near the rock, a small grid of heights and velocities stepped every frame by
  the shallow-water equations, added on top of the FFT sea; a whole chapter of
  its own.
- **Spray that lands as foam.** Particles that hit the water could stamp foam
  where they fall, from the simulate pass.
- **A third particle system.** A third user of Chapter 21's system — rain on the
  sea, smoke from the boat — is the time to move `SprayParticles` into
  `VulkanGraphics` as `GpuParticles`, with the emit and simulate shaders as
  parameters, and to switch Chapter 21 and this chapter over to it.
- **Something that moves.** A rock never moves; a boat does, and reads the sea
  for a different reason: to float. Chapter 32 puts one in this sea, through the
  same probe set, and lets its bow throw this chapter's spray.

## Checkpoint

Rerun `GenerateProjects.bat`, build, and run with `--demo Sea`. From the same
place, about `(−6, 4, −100)` looking back toward the start, you can now see:

- **foam at the waterline**, a pale ring round the rock where the waves hit,
  which fades over seconds when they stop;
- "Foam per m/s" at 0: no new foam, and the ring fades away over the "Local
  foam fade" time; at 2, a whiter ring;
- the spray as before.

---

## When it does not work

| Symptom | Cause |
| --- | --- |
| `Initialize` fails with a file not found | The rock is read from `Assets/Scenes/` beside the executable (Chapter 13's post-build copy). Run `make_sea_props.py` in `Assets/Scenes/` and build again, so the copy picks up `Rock.usda` |
| No spray at all | Read the panel's particle count while a wave hits the rock: 0 means no requests. Lower "Threshold" to 0.5: if spray appears, the sea is calmer than the threshold; raise the wind or the swell instead. If it does not, check that `RecordSimulation` runs after step 8's hand-over: before it, the maps are still being written and the impact pass reads a sea that is not there yet, and synchronization validation reports it |
| Spray everywhere, all the time, from the whole circle at once | The probes compare with garbage: the first frame must be a reset, so check that `m_reset` starts true and that the impact pass reads `SPRAY_FLAG_RESET` |
| Foam at the rock appears 250 m away too | The impact pass is stamping into one of Chapter 30's foam maps instead of the local one: binding 6 of the probe set must be `m_localFoamView` |
| Spray, but no foam at the rock | The surface does not add binding 11's foam, or step 4 of the impact pass is missing. Foam a little off to one side of where the waves hit means the surface reads the map at `gridPosition`; it must read at `worldPosition`, where the impact pass stamped (section 7) |
| Foam that never fades | The fade does not run before the impact pass, or its push constant's `foamFade` is 0 |

## Exit check

- [ ] Run with `--demo Sea` and the sky on. From the rock's windward side (about
      `(−6, 4, −100)`, looking back toward the start) watch for a minute: spray
      bursts up from the rock as crests reach it, a few metres high, and nothing
      between crests; a ring of foam lingers at its foot.
- [ ] Set "Threshold" to 0 and watch the particle count: thousands, and spray
      from all round the rock. Set it to 5: none.
- [ ] "Start again": the foam and the spray are gone at once, and come back with
      the next waves.
- [ ] The same at 4x MSAA, after resizing the window, and after switching to
      Ocean and back. Synchronization validation, with the shader-access setting
      on (Chapter 20 section 5), is silent through all of it.
- [ ] **The positive controls.** Each one weakens a barrier this chapter added
      and must be reported by synchronization validation, with the shader-access
      setting on; without it all four are silent and prove nothing. Build each
      change on its own, run a few frames, read the messages, and put the barrier
      back.
  - **The maps handed to the impact pass.** In `SeaDemo::Record` step 8, take
    `VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT` out of the displacement's
    destination. Expect `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDispatch`, for
    set 0, bindings 0, 1, and 2: the impact pass sampling the maps before the
    assemble pass's writes are visible to it.
  - **The faded foam handed to the impact pass.** In `RecordSimulation`, delete
    the `computeToComputeBarrier` after step 2. Expect
    `SYNC-HAZARD-WRITE-AFTER-WRITE` at the impact pass's `vkCmdDispatch`, binding
    6: the stamp writing the map the fade just wrote.
  - **The requests handed to the spray.** Delete the `computeToComputeBarrier`
    after step 4. Expect `SYNC-HAZARD-WRITE-AFTER-WRITE` at the spray's begin
    pass, binding 5: begin zeroing the request count while the impact pass's
    writes to the list may still be in flight.
  - **The local foam handed to the surface.** In step 6, change the local foam's
    destination stage from `FRAGMENT_SHADER` to `COMPUTE_SHADER`. Expect
    `SYNC-HAZARD-READ-AFTER-WRITE` at the surface's `vkCmdDraw`, set 1,
    binding 11.

---

## Sources

- Jerry Tessendorf, *Simulating Ocean Water*, 2001: the choppy displacement,
  which is why section 3 has to look for the water above a place.
- Chapter 21 of this tutorial, for the particle system, and Chapter 20 section 9,
  for reading results back.

## Appendix A — `SeaObjects.cpp`: its head, and the functions that grew in pieces

Reference: the file's includes, and the three functions that sections 1-7 built
a piece at a time, as this chapter leaves them; Chapter 32 adds the boat to all
three. Every other function is printed whole in its section, except `Update`
and `Shutdown`, noted below.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapters 31 and 32: a rock and a boat in Chapter 30's sea, the spray they throw, the foam they leave
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Sea/SeaObjects.cpp
#include "PillowFort/Demos/Sea/SeaObjects.h"

#include "PillowFort/DebugPanels/DemoPanel.h"
#include "PillowFort/Scene/ColorSpace.h"
#include "PillowFort/Scene/Scene.h"
#include "PillowFort/UsdImport/UsdImport.h"
#include "PillowFort/VulkanGraphics/ExecutableFiles.h"
#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"
#include "PillowFort/VulkanGraphics/VulkanBarriers.h"

#include <glm/gtc/matrix_transform.hpp>
#include <imgui.h>

#include <algorithm>
#include <cstddef>

// File scope, above the namespace block. Chapter 14's place for scenes: beside the executable.
static std::filesystem::path scenesDirectory()
{
    return pf::vulkan_graphics::executableDirectory() / "Assets" / "Scenes";
}

namespace pf::demos::sea {

using namespace vulkan_graphics;
```

```cpp
InitializationResult SeaObjects::Initialize(const DemoContext& context, const SceneRenderer& sceneRenderer,
                                            std::span<const VkImageView, SEA_CASCADE_COUNT> displacementMaps)
{
    m_context       = context;   // first, so Shutdown works however far this gets
    m_sceneRenderer = &sceneRenderer;

    // Section 2: the rock where SprayTypes.h says it stands.
    const glm::mat4 rockPlacement = glm::translate(glm::mat4(1.0f), glm::vec3(SPRAY_ROCK_X, SPRAY_ROCK_Y, SPRAY_ROCK_Z));
    if (auto result = LoadProp(scenesDirectory() / "Rock.usda", rockPlacement); !result) { return result; }

    if (auto result = CreateBuffersAndImages(); !result)         { return result; }   // section 4
    if (auto result = CreateProbeSet(displacementMaps); !result) { return result; }   // section 4
    if (auto result = CreatePipelines(); !result)                { return result; }   // sections 2 and 4

    // Section 6: Chapter 21's particles, fed by the request list.
    if (auto result = m_spray.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats,
                                         sceneRenderer.FrameSetLayout(), m_requests.buffer);
        !result)
    {
        return result;
    }

    m_reset = true;   // the probes, the foam, and the particles all start from nothing
    m_readbackPending.fill(false);
    return InitializationResult::success();
}
```

```cpp
InitializationResult SeaObjects::CreatePipelines()
{
    // Section 4: the passes that read the sea share a layout, the probe set and a SprayParameters.
    const VkPushConstantRange probeRange{ VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(SprayParameters) };
    const VkPipelineLayoutCreateInfo probeLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_probeSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &probeRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &probeLayoutInfo, nullptr, &m_probeLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the sea objects.");
    }
    const struct { VkPipeline* pipeline; const char* shader; } passes[] = {
        { &m_impactPipeline, "Sea/SprayImpact.comp.spv" },     // section 5
        { &m_fadePipeline,   "Sea/SeaLocalFoam.comp.spv" },    // section 7
    };
    for (const auto& pass : passes)
    {
        *pass.pipeline = createComputePipeline(m_context.vulkan.device, m_context.pipelineCache, pass.shader, m_probeLayout);
        if (*pass.pipeline == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a sea objects compute pipeline failed.");
        }
    }

    // Section 2: the rock. Set 0 the camera.
    const VkDescriptorSetLayout frameSetLayout = m_sceneRenderer->FrameSetLayout();
    const VkPushConstantRange   propRange{ VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0,
                                           sizeof(PropParameters) };
    const VkPipelineLayoutCreateInfo propLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &frameSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &propRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &propLayoutInfo, nullptr, &m_propLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the sea's props.");
    }
    // Chapter 11's mesh pipeline: its vertex, counter-clockwise front faces, backs culled, in the
    // scene pass at the scene's sample count.
    const GraphicsPipelineDesc desc{
        .vertexShader     = "Sea/SeaProp.vert.spv",
        .fragmentShader   = "Sea/SeaProp.frag.spv",
        .vertexBindings   = meshVertexBindings(),
        .vertexAttributes = meshVertexAttributes(),
        .colorFormats     = { &m_context.formats.color, 1 },
        .depthFormat      = m_context.formats.depth,
        .depthTest        = true,
        .depthWrite       = true,
        .depthCompare     = VK_COMPARE_OP_LESS,
        .cullMode         = VK_CULL_MODE_BACK_BIT,
        .frontFace        = VK_FRONT_FACE_COUNTER_CLOCKWISE,
        .layout           = m_propLayout,
        .samples          = m_context.formats.samples,
    };
    m_propPipeline = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, desc);
    if (m_propPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the sea's prop pipeline failed.");
    }
    return InitializationResult::success();
}
```

`Update` is section 6's, printed whole there; section 7 adds the foam's three
lines after the spray's.

```cpp
void SeaObjects::RecordSimulation(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SeaParameters& sea)
{
    const SprayParameters spray = PackSpray(sea);

    // 1. Return trips. Last frame's compute passes wrote every buffer here; its draw read the spray,
    //    and its copy read the counters out. Chapter 21's barrier, for all of them at once. The local
    //    foam stays in GENERAL; last frame's surface sampled it.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT
                      | VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    transitionImage(commandBuffer, m_localFoamImage,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                    VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_probeLayout, 0, 1, &m_probeSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_probeLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(spray), &spray);

    // 2. Section 7: last frame's local foam fades.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_fadePipeline);
    vkCmdDispatch(commandBuffer, groupCount(SPRAY_FOAM_TEXELS, 8), groupCount(SPRAY_FOAM_TEXELS, 8), 1);
    computeToComputeBarrier(commandBuffer);   // the impact pass stamps into the faded map

    // 4. Section 5: where the water comes at the rock fast, spray is asked for and foam
    //    left. The spray's begin pass reads the requests next.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_impactPipeline);
    vkCmdDispatch(commandBuffer, groupCount(SPRAY_SAMPLE_COUNT, SPRAY_GROUP_SIZE), 1, 1);
    computeToComputeBarrier(commandBuffer);

    // 5. Section 6: Chapter 21's frame, its emission sized by the requests.
    m_spray.RecordSimulation(commandBuffer, sea.deltaTime, m_settings.sprayDrag, m_reset);

    // 6. Hand-overs. The local foam to the surface's fragment shader, still in GENERAL (section 7).
    transitionImage(commandBuffer, m_localFoamImage,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

    // 7. Section 6: Chapter 20 section 9's readback, the spray's counters for the panel.
    const VkBufferCopy counterRegion{ .srcOffset = 0, .dstOffset = offsetof(ObjectReadback, counters),
                                      .size = sizeof(particles::ParticleCounters) };
    vkCmdCopyBuffer(commandBuffer, m_spray.CounterBuffer(), m_readback[frameIndex].buffer, 1, &counterRegion);
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    m_readbackPending[frameIndex] = true;

    m_reset = false;
    ++m_frameNumber;
}
```

`Shutdown` is section 1's, printed whole there; section 6 puts
`m_spray.Shutdown();` first.

## Appendix B — `make_sea_props.py`

Run it once, from `Assets/Scenes/`, with Python 3; it uses nothing outside the
standard library, and what it writes, `Rock.usda` and `Boat.usda`, is committed
beside it. The boat is Chapter 32's; writing both props from one script keeps
their helpers in one place.

```python
# Assets/Scenes/make_sea_props.py
# Writes the sea's two props: Boat.usda, a 6 m open boat with a cabin (Chapter 32), and Rock.usda, a
# lumpy rock 14 m across (Chapter 31). Run once, from Assets/Scenes/:
#     python make_sea_props.py
# Plain Python 3, standard library only. Not part of the build: what it writes is committed.
# Both are Y-up and in metres. No normals are authored, so the importer gives every face its own
# (Chapter 14), which suits a boat made of flat panels and a rock made of facets.

import math


def material(root, name, color, roughness):
    return f"""
        def Material "{name}"
        {{
            token outputs:surface.connect = </{root}/Materials/{name}/Surface.outputs:surface>

            def Shader "Surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = {color}
                float inputs:roughness = {roughness}
                token outputs:surface
            }}
        }}"""


def mesh(root, name, points, faces, materialName):
    counts = ", ".join(str(len(face)) for face in faces)
    indices = ", ".join(str(i) for face in faces for i in face)
    pointText = ", ".join(f"({x:.4f}, {y:.4f}, {z:.4f})" for x, y, z in points)
    return f"""
    def Mesh "{name}" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {{
        uniform token subdivisionScheme = "none"
        int[] faceVertexCounts = [{counts}]
        int[] faceVertexIndices = [{indices}]
        point3f[] points = [{pointText}]
        rel material:binding = </{root}/Materials/{materialName}>
    }}"""


def write(fileName, root, materials, meshes):
    with open(fileName, "w") as f:
        f.write(f'#usda 1.0\n(\n    defaultPrim = "{root}"\n    metersPerUnit = 1\n    upAxis = "Y"\n)\n\n')
        f.write(f'def Xform "{root}"\n{{\n    def Scope "Materials"\n    {{')
        f.write("".join(materials))
        f.write("\n    }\n")
        f.write("".join(meshes))
        f.write("\n}\n")


# The boat. Its origin is its centre of mass, low in the hull: the keel is 0.25 m below it and the deck
# 0.85 m above. The bow points along -Z, the way a camera looks. The hull is the deck's outline joined
# to a narrower, flat bottom: seven side panels, the deck, and the bottom. Every face is listed
# counter-clockwise seen from outside.
deck = [(-1.2, 3.0), (1.2, 3.0), (1.2, 0.0), (1.0, -1.8), (0.0, -3.2), (-1.0, -1.8), (-1.2, 0.0)]
bottom = [(x * 0.7, z if z > -3.0 else -2.4) for x, z in deck]
hullPoints = [(x, 0.85, z) for x, z in deck] + [(x, -0.25, z) for x, z in bottom]
n = len(deck)
sides = [[i, n + i, n + (i + 1) % n, (i + 1) % n] for i in range(n)]
deckFace = [[i for i in range(n)]]                 # the outline runs counter-clockwise seen from above
bottomFace = [[n + i for i in range(n)][::-1]]     # so the bottom, seen from below, is the reverse

# The cabin: a box on the deck, toward the stern.
def box(x0, x1, y0, y1, z0, z1):
    p = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
    faces = [[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2], [3, 2, 6, 7], [4, 5, 1, 0]]
    return p, faces

cabinPoints, cabinFaces = box(-0.7, 0.7, 0.85, 1.85, -0.4, 1.6)

write("Boat.usda", "Boat",
      [material("Boat", "Hull", "(0.80, 0.80, 0.78)", 0.4),
       material("Boat", "Deck", "(0.45, 0.30, 0.18)", 0.8),
       material("Boat", "Cabin", "(0.55, 0.62, 0.70)", 0.5)],
      [mesh("Boat", "Hull", hullPoints, sides + bottomFace, "Hull"),
       mesh("Boat", "Deck", hullPoints, deckFace, "Deck"),
       mesh("Boat", "Cabin", cabinPoints, cabinFaces, "Cabin")])


# The rock: a sphere of radius 7 m cut into 24 rings of 48 facets, each point pushed in or out by a few
# smooth waves over the sphere, so the outline is irregular but has no overhangs worth speaking of.
rings, segments, radius = 24, 48, 7.0
rockPoints = [(0.0, radius * 0.95, 0.0)]                       # the top
for ring in range(1, rings):
    polar = math.pi * ring / rings                               # 0 at the top, pi at the bottom
    for segment in range(segments):
        around = 2.0 * math.pi * segment / segments
        lump = 1.0 + 0.12 * math.sin(3.0 * around + 1.3) * math.sin(2.0 * polar) \
                   + 0.06 * math.sin(7.0 * around) * math.sin(5.0 * polar + 0.7)
        r = radius * lump
        rockPoints.append((r * math.sin(polar) * math.cos(around), r * math.cos(polar),
                           -r * math.sin(polar) * math.sin(around)))
rockPoints.append((0.0, -radius, 0.0))                           # the bottom
last = len(rockPoints) - 1
rockFaces = []
for segment in range(segments):                                  # the cap round the top
    rockFaces.append([0, 1 + segment, 1 + (segment + 1) % segments])
for ring in range(rings - 2):                                    # quads between rings
    for segment in range(segments):
        a = 1 + ring * segments + segment
        b = 1 + ring * segments + (segment + 1) % segments
        rockFaces.append([a, a + segments, b + segments, b])
for segment in range(segments):                                  # the cap round the bottom
    a = 1 + (rings - 2) * segments
    rockFaces.append([last, a + (segment + 1) % segments, a + segment])

write("Rock.usda", "Rock",
      [material("Rock", "Stone", "(0.28, 0.26, 0.24)", 0.9)],
      [mesh("Rock", "Rock", rockPoints, rockFaces, "Stone")])
```

## Appendix C — `SprayImpact.comp.glsl`, as this chapter leaves it

```glsl
// Shaders/Sea/SprayImpact.comp.glsl - one invocation per point where the sea meets the rock: how
// fast the water comes at it, and where that is fast, spray to ask for and foam to leave
// (sections 5-7).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SprayTypes.h"
#include "SeaWater.glsl"   // set 0, bindings 0-2: the sea's displacement maps
#include "SprayRequests.glsl"   // set 0, binding 5: the requests, section 6
#include "Random.glsl"

layout(local_size_x = SPRAY_GROUP_SIZE) in;

// Per point, what the last frame saw: x how deep under the water the point was, yz the water's
// horizontal displacement there.
layout(set = 0, binding = 3, std430) buffer ProbeBuffer { vec4 probes[]; };
layout(set = 0, binding = 6, rgba16f) uniform image2D localFoam;   // section 7: r, the foam

layout(push_constant) uniform PushConstants
{
    SprayParameters spray;
};

// Section 7: adds foam in a small disc around a point, into the map that does not repeat.
// Neighbouring invocations may stamp the same texel at once; one write then wins, which for foam
// is harmless.
void stampFoam(vec2 position, float amount)
{
    vec2  origin  = vec2(SPRAY_ROCK_X, SPRAY_ROCK_Z) - 0.5 * SPRAY_FOAM_SIZE;
    vec2  centre  = (position - origin) / SPRAY_FOAM_SIZE * float(SPRAY_FOAM_TEXELS);
    ivec2 size    = imageSize(localFoam);
    for (int y = -2; y <= 2; ++y)
    {
        for (int x = -2; x <= 2; ++x)
        {
            ivec2 texel = ivec2(floor(centre)) + ivec2(x, y);
            if (any(lessThan(texel, ivec2(0))) || any(greaterThanEqual(texel, size))) { continue; }
            float falloff = max(1.0 - length(vec2(texel) + 0.5 - centre) / 2.5, 0.0);
            float old     = imageLoad(localFoam, texel).r;
            imageStore(localFoam, texel, vec4(max(old, min(amount * falloff, 1.0))));
        }
    }
}

void main()
{
    uint id = gl_GlobalInvocationID.x;
    if (id >= SPRAY_SAMPLE_COUNT) { return; }

    // 1. Where the point is, which way is out from the object, and how fast the object moves there.
    vec3 point;
    vec3 outward;
    vec3 objectVelocity = vec3(0.0);
    if (id < SPRAY_ROCK_SAMPLES)
    {
        // Round the rock's waterline, at the mean sea level.
        float angle = 2.0 * 3.14159265 * float(id) / float(SPRAY_ROCK_SAMPLES);
        outward = vec3(cos(angle), 0.0, sin(angle));
        point   = vec3(SPRAY_ROCK_X, 0.0, SPRAY_ROCK_Z) + SPRAY_ROCK_WATERLINE * outward;
    }

    // 2. Section 5: how fast the water comes at the object. It climbs it: the point's depth under the
    //    water grows, whether the water rises or a bow drives down into a wave. And it runs into it:
    //    the water's own horizontal speed toward the object. Both are this frame against last frame's,
    //    which is this point's slot.
    vec3  water      = seaDisplacementAbove(point.xz, spray.patchSizes, spray.weights);
    float submersion = water.y - point.y;
    bool  reset      = (spray.flags & SPRAY_FLAG_RESET) != 0u || spray.deltaTime <= 0.0;
    vec4  previous   = reset ? vec4(submersion, water.xz, 0.0) : probes[id];
    probes[id]       = vec4(submersion, water.xz, 0.0);
    float time       = max(spray.deltaTime, 1e-4);
    float rise       = (submersion - previous.x) / time;
    vec2  flow       = (water.xz - previous.yz) / time;
    float inward     = -dot(flow, outward.xz);
    float impact     = min(max(rise, 0.0) + max(inward, 0.0), 20.0);   // m/s; a fold can spike it

    // 3. Only near the waterline does anything happen, and only the part of the impact past the
    //    threshold counts: the strength, which throws spray (section 6) and leaves foam (section 7).
    if (abs(submersion) > 1.0) { return; }
    float strength = impact - spray.sprayThreshold;

    // 4. Section 7: foam where the water hits hard, more the harder it hits.
    float foam     = spray.foamStamp * strength;
    if (foam > 0.0)
    {
        stampFoam(point.xz, foam);
    }

    // 5. Section 6: only past the threshold does the water throw spray. How many particles: the rate
    //    times the strength times the step. The fraction left over becomes one more particle as often
    //    as it is large, so the average comes out right.
    if (strength <= 0.0) { return; }
    uint  random = seedRandom(id, spray.frameNumber);
    float wanted = spray.sprayRate * strength * spray.deltaTime;
    uint  count  = uint(wanted) + (randomFloat(random) < fract(wanted) ? 1u : 0u);

    // 6. Ask for them, if there is room. atomicAdd hands out places as Chapter 21's lists
    //    do; past the capacity a request is dropped, never written out of bounds.
    uint first = atomicAdd(requestCount, count);
    for (uint i = 0u; i < count && first + i < SPRAY_REQUEST_CAPACITY; ++i)
    {
        // Up and out from the object, fanned by a random nudge, faster the harder the water hits.
        vec3  nudge     = vec3(randomFloat(random), randomFloat(random), randomFloat(random)) * 2.0 - 1.0;
        vec3  direction = normalize(outward * 0.4 + vec3(0.0, 1.0, 0.0) + 0.4 * nudge);
        float speed     = spray.sprayLaunch * strength * (0.6 + 0.8 * randomFloat(random));
        vec3  start     = vec3(point.x, water.y, point.z) + outward * (0.3 * randomFloat(random));
        float lifetime  = 1.0 + randomFloat(random);
        requests[first + i] = SprayRequest(vec4(start, lifetime), vec4(direction * speed + 0.5 * objectVelocity, 0.0));
    }
}
```

Next: [32 — A Boat](32-A-Boat.md)
