# 33 — Path Tracing

**Goal:** a path tracer that converges while you watch. A compute shader follows
random paths of light through a small scene — a floor, a red, a white, and a
green sphere, and a glowing sphere above them — and the demo averages the paths
over many frames, so a grainy picture settles into a clean one, with soft
shadows from an area light and color bleeding that no earlier chapter draws.
Route A finds what each ray hits by formula and runs on any GPU. Route B finds
it among triangle meshes with the GPU's ray queries, and the picture must not
change.

**ROADMAP:** step 21+ — a demo, in `Source/PillowFort/Demos/PathTracer/` with
shaders under `Shaders/PathTrace/`, registered in `SandboxGame` like every demo
since Chapter 09.

**Module:** the demo is `pf::demos::path_tracer` (`PathTracerDemo`). Route B
adds a second class beside it, `MeshScene`, and three small engine changes:
optional ray-query extensions in `VulkanInstance::CreateDevice`, buffer device
addresses in VMA, and a `rayQuery` flag in `VulkanContext` (section 6).

**Math:** Monte Carlo integration — estimating a sum by averaging random
samples — and the probability density that goes with it, taught in sections 0
and 4 with worked numbers. Assumed: vectors, the dot product as a cosine
(Chapter 11 section 14), and what a matrix and its inverse do (Chapter 10
sections 1, 2, and 4).

**Prerequisites:**

- Chapter 09 — the `Demo` interface, and `Resize`, which the engine calls after
  `Setup` and after every swapchain recreation (section 2); `DemoContext` and
  `RecordContext` (section 3); `handBackSceneTarget` (section 4); registering a
  demo in `Main.cpp` (section 7).
- Chapter 10 sections 1 and 2 (the four spaces, Vulkan's Y-down clip space, the
  projection and its divide by `w`), 4 (the inverse of a matrix, `viewMatrix`),
  6 (the orbit controller), and 12 (`CameraControls` and the "Camera" panel,
  both of which report whether anything moved).
- Chapter 11 section 14 — the dot product as the cosine in Lambert's law.
- Chapter 15 section 9, reading only: "Two words for light" (radiance,
  irradiance, and what a BRDF is) and "(a) Lambert" (why a matte surface's BRDF
  is albedo / π). Nothing else from Chapter 15 is used.
- Chapter 16 section 6 — exposure and the tone curve, which section 5 uses.
- Chapter 20 sections 2 (`createComputePipeline`), 3 (workgroups, `groupCount`,
  the bounds check, and `pcgHash` in `Random.glsl`), 4 (storage images,
  `GENERAL`, and Life's one-time transition into it), 5
  (`computeToComputeBarrier` and the return trip), and 10 (a compute shader
  that writes the scene target, its barriers in both directions, and a `Resize`
  that rewrites a descriptor).
- Chapter 21 section 3: "Random numbers, and seeding them" (`seedRandom` and
  `randomFloat` in `Random.glsl` — if you skipped Chapter 21, add that block to
  `Random.glsl` now; it needs only `pcgHash`), and "Directions spread evenly
  over a cone" (Archimedes' equal slices), which section 4 uses for a whole
  sphere.
- Route B (section 6) also uses Chapter 02 section 6 (`CreateDevice` and its
  chain of feature structs), Chapter 08 sections 2 (`uploadToBuffer`, which
  leaves the barrier to its caller) and 9 (buffer device addresses), Chapter 11
  sections 2, 4, and 13 (the 48-byte `Vertex`, `makeUvSphere` and `makePlane`,
  and the normal matrix), and Chapter 19 section 4 (several meshes in one
  vertex buffer and one index buffer). Loading extension functions from the
  device with `vkGetDeviceProcAddr` is new here, and section 6 explains it
  where it is used.

Nothing else from Chapters 12-32 is needed. If you built image-based lighting
(Chapter 24), section 0 will look familiar, and it says where; it does not
depend on it.

---

## 0. Path tracing in one page

Every renderer so far has lit a point from its lights and — since Chapter 24 —
from the sky in every direction, added up ahead of time into cubes; the sea of
Chapters 30-32 reflects that sky and its clouds. What none of them does is light
that bounced off another surface first: the floor never lights the underside of
the sphere above it, and a red wall never tints the white one beside it. A path
tracer follows light through every bounce, and the answer is the whole picture:
shadows with soft edges from a light that has a size, light bounced off the
floor onto the underside of a sphere, and the red sphere tinting the white one
beside it. This section is the idea; sections 1-5 build it.

### What a pixel should show

A pixel records the light arriving along one line of sight. Follow that line
back from the eye to the first surface it meets. The light leaving that point
toward the eye has two parts: what the surface **emits** itself (here, only the
glowing sphere), and what it **reflects** — and a surface reflects light
arriving from *every* direction above it, not only from the light:

```text
              sky         light
                \    |    /
   red sphere -- \   |   /         light arrives from every direction above the point,
                  \  |  /          and some of each is reflected toward the eye
     eye  <--------  P
   ──────────────────────────────  floor
```

Each of those arriving directions is itself a line of sight. It ends on some
other surface — the light, the sky, the red sphere, the floor further along —
whose outgoing light is made in exactly the same way. In words, this is the
**rendering equation** (Kajiya, 1986), the one piece of physics this chapter
uses:

> light leaving a point toward the eye = the light it emits + the sum, over
> every direction above it, of the light arriving from that direction × the
> BRDF × cos θ

(Strictly it is an integral: each direction counts in proportion to the tiny
patch of sky it covers. "Sum" is the right picture.)

If you built Chapter 24, you have computed this sum once already. Section 1
there added up the light arriving on a surface from every direction of a sky,
each weighted by its cosine, and stored the answer in a cube, for the one case
where every direction ends on the sky. A path tracer does it for every surface,
where a direction may end on another surface whose light is the same sum again;
and instead of adding up every direction, it samples a few.

The BRDF and the cos θ are Chapter 15 section 9's: the BRDF says what fraction
of the light arriving from one direction leaves toward another, and cos θ (the
dot product of the normal with the arriving direction, Chapter 11 section 14)
says how much a slanted beam is spread out. Every surface here is matte, so its
BRDF is Chapter 15's first one, albedo / π, the same for every pair of
directions.

Two things make that hard to compute directly. The sum is over infinitely many
directions, and each term needs the same sum again at another surface, and so
on. A path tracer does not try. It picks *one* direction at random at each
surface, follows it, and repeats, so that one pixel sample is one random **path**
from the eye to a light or to the sky. Then it averages many paths. That only
works because of one idea, and it is worth seeing with numbers first.

### Monte Carlo, with darts

Draw a square 2 m on a side, and inside it a circle of radius 1 m. Throw darts
that land anywhere in the square with equal chance. The circle covers π/4 of the
square's area (π × 1² against 2 × 2), so the fraction of darts that land inside
it is close to π/4, and the square's area, 4, times that fraction is close to
π. Running exactly that, three times at each size:

| Darts | Three estimates of π | Typical error |
| --- | --- | --- |
| 100 | 2.80, 3.44, 3.08 | 0.16 |
| 10,000 | 3.140, 3.152, 3.146 | 0.016 |
| 1,000,000 | 3.1414, 3.1433, 3.1436 | 0.0016 |

Three things in that table are the whole of what this chapter needs from
probability:

- **Every estimate is right on average**, even with 100 darts: the errors go
  both ways and do not lean. An estimate with that property is called
  **unbiased**. A path tracer that is unbiased converges to the correct picture;
  one that is not converges, just as smoothly, to a wrong one.
- **The noise shrinks with the square root of the count.** A hundred times the
  darts gives ten times the accuracy; four times the darts halves the noise. So
  the first few hundred samples of a pixel do most of the visible work, and the
  thousands after them only polish.
- **Nothing about the circle mattered** except being able to ask of one random
  point "is it inside?". The same averaging estimates any sum or area you can
  sample: here, the sum over all directions above a point, and over all the
  directions after those.

This is **Monte Carlo integration**: to add up something continuous, sample it
at random places, average, and multiply by the size of what you sampled — the
square's area here. A pixel's value is such a sum, so one random path is one
dart, and the picture is the average of many.

### What the demo does with that

Every frame, each pixel traces a few new paths and adds their light to a running
total it keeps between frames. The screen shows the total divided by the number
of paths. In the first frame each pixel has one path and the picture is mostly
noise; after a few hundred it is clean; after a few thousand you cannot see it
change. That is **progressive** rendering, and sections 1-5 are its parts: the
image that keeps the total (1), the random numbers (2), the rays and the scene,
with a first picture that shows what each ray hits (3), the path itself (4),
and the display and what restarts the sum (5).

> **Jump:** until now every frame was drawn from scratch, shown, and thrown
> away. From here the picture is a running average built across frames, and
> nothing on screen is "this frame": it is the mean of every sample since the
> average last started. Keep in mind the rule that follows, because the whole
> demo is shaped by it: anything that changes what a new sample would be — the
> camera, the scene, the bounce limit, the window's size — makes every sample so
> far wrong, and the average must start again. Anything that changes only how
> the average is *shown* — exposure, the tone curve — must not restart it.

---

## Pick a route

There are three ways to find what a ray hits in Vulkan. They are a sequence
more than a choice.

| Route | Needs | Scene | Start here? |
| --- | --- | --- | --- |
| **A. Compute, by formula** | No extensions | Spheres and a plane | **Yes** |
| **B. Compute + ray query** | `VK_KHR_acceleration_structure`, `VK_KHR_ray_query`, buffer device addresses | Triangle meshes | After A converges |
| **C. Ray tracing pipelines** | B's, plus `VK_KHR_ray_tracing_pipeline` | Triangle meshes | Only with a reason (section 7) |

Everything that makes path tracing hard — the random numbers, the sampling, the
accumulation, convergence — is in route A, which is sections 1-5. Route B
(section 6) changes one shader function, the one that finds the nearest hit,
and the demo keeps both so you can switch between them and compare. Ray queries
inside a compute shader are what most current renderers use; route C's ray
tracing pipelines add little for a scene like this and cost a great deal of
setup, and section 7 says why to leave them.

---

## What you are actually writing

The demo is one class. **This is `PathTracerDemo.h`**, the map of the chapter:
every function names the section that writes it. Route B (section 6) adds one
member, a `MeshScene`, and the lines that use it; `m_meshesPipeline` and the
`route` setting are here from the start so that route A's code needs no
changing when it arrives.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  A progressive path tracer in a compute shader (Chapter 33)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/PathTracer/PathTracerDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/Transform.h"
#include "PathTrace/PathTraceTypes.h"

#include <vma/vk_mem_alloc.h>

#include <cstdint>

namespace pf::demos::path_tracer {

// What the panel edits (section 5). CPU state: it survives Teardown and Setup.
struct PathTracerSettings
{
    int samplesPerFrame = 1;   // paths per pixel per frame
    int maxBounces      = 8;   // surfaces one path may hit
    int route           = 0;   // 0 = route A, spheres by formula; 1 = route B, triangles by ray query
};

class PathTracerDemo final : public Demo
{
public:
    PathTracerDemo();   // CPU only: puts the camera where it frames the scene

    const char*          Name() const override { return "Path Tracer"; }
    InitializationResult Setup(const DemoContext& context) override;                    // below
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override; // section 1
    void                 Update(const FrameInput& input) override;                      // section 5
    void                 Record(const RecordContext& frame) override;                   // section 3
    void                 Teardown() override;                                           // section 3
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }

private:
    InitializationResult CreateDescriptors();                          // section 1
    InitializationResult CreateAccumulationImage(VkExtent2D extent);   // section 1
    void                 DestroyAccumulationImage();                   // section 1
    InitializationResult CreatePipelines();                            // section 3

    static constexpr uint32_t GROUP_SIZE = 8;   // local_size_x and local_size_y in PathTrace.glsl

    // GPU objects: created in Setup and Resize, released in Teardown.
    vulkan_graphics::VulkanContext m_vulkan;                       // Chapter 09's DemoContext, copied
    VkPipelineCache                m_pipelineCache = VK_NULL_HANDLE;

    // Section 1: the running sum, the window's size, rebuilt by every Resize.
    VkImage       m_accumulationImage      = VK_NULL_HANDLE;
    VmaAllocation m_accumulationAllocation = VK_NULL_HANDLE;
    VkImageView   m_accumulationView       = VK_NULL_HANDLE;

    // Section 1: set 0 - the accumulation image and the scene target.
    VkDescriptorSetLayout m_setLayout      = VK_NULL_HANDLE;
    VkDescriptorPool      m_descriptorPool = VK_NULL_HANDLE;
    VkDescriptorSet       m_set            = VK_NULL_HANDLE;

    // Section 3: one layout, a pipeline per route.
    VkPipelineLayout m_pipelineLayout  = VK_NULL_HANDLE;
    VkPipeline       m_spheresPipeline = VK_NULL_HANDLE;   // route A
    VkPipeline       m_meshesPipeline  = VK_NULL_HANDLE;   // route B (section 6); null until then

    // CPU state: survives Teardown, so switching back finds everything as it was.
    scene::Camera         m_camera;
    scene::Transform      m_cameraTransform;
    scene::CameraControls m_controls;
    PathTracerSettings    m_settings;
    bool                  m_resetAccumulation  = true;   // set by Resize and Update, acted on by Record
    uint32_t              m_accumulatedFrames  = 0;      // frames in the sum since it last started
    uint32_t              m_accumulatedSamples = 0;      // samples per pixel in it, for the panel
    uint32_t              m_frameSeed          = 0;      // counts every frame recorded; never reset
    float                 m_restartSeconds     = 0.0f;   // when the sum last started, for the panel
};

} // namespace pf::demos::path_tracer
```

The camera is Chapter 10's: a lens, a `Transform` beside it, and the two
controllers with their panel. Its constructor places it the way the Cubes demo
did, exactly where the orbit controller would, so the first drag continues
smoothly — orbiting the white sphere from 8 m away, a little above it:

```cpp
PathTracerDemo::PathTracerDemo()
{
    // Orbiting the white sphere from in front and a little above. Placing the camera
    // exactly where the orbit controller would put it means the first drag continues
    // smoothly from here (Chapter 10's Cubes demo does the same).
    m_controls.active         = scene::ControllerKind::Orbit;
    m_controls.orbit.target   = glm::vec3(0.0f, 1.0f, 0.0f);
    m_controls.orbit.distance = 8.0f;
    m_cameraTransform.rotation    = scene::rotationFromYawPitch({ .yaw   = glm::radians(180.0f),
                                                                  .pitch = glm::radians(-8.0f) });
    m_cameraTransform.translation = m_controls.orbit.target
                                  - m_cameraTransform.Forward() * m_controls.orbit.distance;
}
```

A yaw of 180° looks down +Z, so the camera stands at about `(0, 2.1, -7.9)`
looking at the spheres, and world +X is on the *left* of the picture: the red
sphere, at x = −2.1, appears on the right.

**This is `Setup`.** Two steps, in dependency order: the pipeline layout needs
the descriptor set layout. The accumulation image is the window's size, so it
belongs to `Resize`, which the engine always calls straight after `Setup`.

```cpp
InitializationResult PathTracerDemo::Setup(const DemoContext& context)
{
    m_vulkan        = context.vulkan;
    m_pipelineCache = context.pipelineCache;

    if (auto result = CreateDescriptors(); !result) { return result; }   // section 1
    if (auto result = CreatePipelines(); !result) { return result; }     // section 3

    // The accumulation image depends on the window's size, so Resize - which always
    // comes straight after Setup - makes it.
    return InitializationResult::success();
}
```

### Where everything lands

```text
Source/PillowFort/Demos/PathTracer/
  PathTracerDemo.h/.cpp     the demo                                       sections 1-5
  MeshScene.h/.cpp          route B's meshes and acceleration structures   section 6
Shaders/PathTrace/
  PathTraceTypes.h          C++/GLSL twins: the push constants             section 1
  PathTrace.glsl            the tracer: everything except the scene        sections 2-4
  Spheres.comp.glsl         route A: the scene, hit by formula             section 3
  Meshes.comp.glsl          route B: the scene, hit by ray query           section 6
Source/SandboxGame/Main.cpp + one registration line                        section 3
Source/PillowFort/VulkanGraphics/
  VulkanInstance.h/.cpp, VulkanResources.h, VulkanRenderer.cpp             section 6 (route B)
```

```text
PathTracerDemo.cpp
  includes
  namespace pf::demos::path_tracer {
      using namespace vulkan_graphics;
      static drawPathTracerPanel(settings, routeBReady, samples, seconds)   section 5
      PathTracerDemo::PathTracerDemo                                         above
      PathTracerDemo::Setup                                                  above
      PathTracerDemo::CreateDescriptors                                      section 1
      PathTracerDemo::CreateAccumulationImage                                section 1
      PathTracerDemo::DestroyAccumulationImage                               section 1
      PathTracerDemo::Resize                                                 section 1
      PathTracerDemo::CreatePipelines                                        section 3
      PathTracerDemo::Update                                                 sections 3, 5
      PathTracerDemo::Record                                                 section 3
      PathTracerDemo::Teardown                                               section 3
  }
```

`PathTracerDemo.cpp` includes `PathTracerDemo.h`,
`PillowFort/DebugPanels/DemoPanel.h`,
`PillowFort/VulkanGraphics/GraphicsPipeline.h`,
`PillowFort/VulkanGraphics/VulkanBarriers.h`, `<imgui.h>`, and `<vector>`.
`"PathTrace/PathTraceTypes.h"` resolves through the `Shaders` include directory
Chapter 09 added, as Life's `"Life/LifeTypes.h"` does. Rerun
`GenerateProjects.bat` once the new files are on disk.

---

## 1. The accumulation image

**This is the running total.** Each pixel needs two numbers kept between frames:
the sum of the light every path so far brought back, and how many paths that
was. Two images are involved:

| Image | Format | Owner | Holds |
| --- | --- | --- | --- |
| Accumulation | `R32G32B32A32_SFLOAT` | the demo | `rgb` = the summed light, `a` = the number of samples |
| Scene target | `R16G16B16A16_SFLOAT` | the engine (Chapter 08) | the average, `rgb / a`, written every frame |

The demo writes the average straight into the engine's scene target, as a
storage image, the way Life's display pass did (Chapter 20 section 10), and the
composite pass takes it from there. The average is still linear light: tone
mapping happens once, in the composite (section 5), which is what lets exposure
change without touching the sum.

**Why 32-bit floats.** A half float keeps 11 significant bits, so the bigger the
number, the coarser the steps it can hold. Take a pixel whose average is 0.5,
after 4096 samples: its sum is 2048. Half float can hold 2048 and 2050 but
nothing between, so adding the next sample, 0.5, gives 2048.5, which rounds back
to 2048. That sample is lost, and so is every sample below 1 from then on: the
pixel stops converging, and darker pixels stop first. A 32-bit float's steps at
2048 are 0.00024 apart. This is the one image in the tutorial where the format
is not a choice.

**This is `CreateAccumulationImage`.** It is Life's `CreateCellImages` (Chapter
20 section 4) for one image of another format: a storage image, created, viewed,
and moved to `GENERAL` once with `immediateSubmit`, where it stays.

```cpp
InitializationResult PathTracerDemo::CreateAccumulationImage(VkExtent2D extent)
{
    // Four 32-bit floats per pixel: rgb is the sum of every sample's light, a is how
    // many samples that is. STORAGE only: the shader loads and stores it, nothing samples it.
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R32G32B32A32_SFLOAT,
        .extent        = { extent.width, extent.height, 1 },
        .mipLevels     = 1,
        .arrayLayers   = 1,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_STORAGE_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{
        .usage = VMA_MEMORY_USAGE_AUTO,
    };
    if (vmaCreateImage(m_vulkan.allocator, &imageInfo, &allocationInfo,
                       &m_accumulationImage, &m_accumulationAllocation, nullptr) != VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for the accumulation image.");
    }

    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_accumulationImage,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
    };
    if (vkCreateImageView(m_vulkan.device, &viewInfo, nullptr, &m_accumulationView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the accumulation image.");
    }

    // Into GENERAL once, here, as Chapter 20 did with Life's cells. It stays there, so
    // every barrier on it from now on is a memory barrier.
    immediateSubmit(m_vulkan, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, m_accumulationImage,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    });
    return InitializationResult::success();
}

void PathTracerDemo::DestroyAccumulationImage()
{
    vkDestroyImageView(m_vulkan.device, m_accumulationView, nullptr);                       // null: no-op
    vmaDestroyImage(m_vulkan.allocator, m_accumulationImage, m_accumulationAllocation);   // null: no-op
    m_accumulationView       = VK_NULL_HANDLE;
    m_accumulationImage      = VK_NULL_HANDLE;
    m_accumulationAllocation = VK_NULL_HANDLE;
}
```

Its contents start as garbage, and the first frame never reads them: the shader
ignores what the image holds whenever the sum is starting again (section 4's
`main`).

**This is `CreateDescriptors`.** One set, two storage images. One set is enough
for both frames in flight because neither image changes between frames — they
change only in `Resize`, which runs behind a `vkDeviceWaitIdle`.

```cpp
InitializationResult PathTracerDemo::CreateDescriptors()
{
    // Set 0: two storage images, both used only by the compute shader.
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding         = 0,   // accumulationImage
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding         = 1,   // outputImage: the engine's scene target
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT },
    };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 2,
        .pBindings    = bindings,
    };
    if (vkCreateDescriptorSetLayout(m_vulkan.device, &setLayoutInfo, nullptr, &m_setLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the path tracer.");
    }

    // One set: both images change only in Resize, behind a vkDeviceWaitIdle, so the
    // frames in flight can share it.
    const VkDescriptorPoolSize poolSize{ VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, 2 };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 1,
        .poolSizeCount = 1,
        .pPoolSizes    = &poolSize,
    };
    if (vkCreateDescriptorPool(m_vulkan.device, &poolInfo, nullptr, &m_descriptorPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the path tracer.");
    }

    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_descriptorPool,
        .descriptorSetCount = 1,
        .pSetLayouts        = &m_setLayout,
    };
    if (vkAllocateDescriptorSets(m_vulkan.device, &allocateInfo, &m_set) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the path tracer.");
    }
    return InitializationResult::success();   // Resize writes both bindings
}
```

**This is `Resize`.** The accumulation image is the demo's own and the window's
size, so it is rebuilt here — the job Chapter 09 section 2 gave `Resize` — and
both bindings are pointed at this size's images. Its old samples belong to
pixels that no longer exist, so the sum starts again.

```cpp
InitializationResult PathTracerDemo::Resize(const SceneTargets& targets)
{
    // Chapter 09 calls this after Setup and after every swapchain recreation, behind a
    // vkDeviceWaitIdle: nothing still uses the old image, and its samples belong to
    // pixels that no longer exist.
    DestroyAccumulationImage();
    if (auto result = CreateAccumulationImage(targets.extent); !result) { return result; }

    // Point set 0 at this size's two images, both in GENERAL while the shader runs.
    const VkDescriptorImageInfo accumulation{
        .imageView   = m_accumulationView,
        .imageLayout = VK_IMAGE_LAYOUT_GENERAL,
    };
    const VkDescriptorImageInfo output{
        .imageView   = targets.colorView,
        .imageLayout = VK_IMAGE_LAYOUT_GENERAL,
    };
    const VkWriteDescriptorSet writes[] = {
        { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
          .dstSet          = m_set,
          .dstBinding      = 0,
          .descriptorCount = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
          .pImageInfo      = &accumulation },
        { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
          .dstSet          = m_set,
          .dstBinding      = 1,
          .descriptorCount = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
          .pImageInfo      = &output },
    };
    vkUpdateDescriptorSets(m_vulkan.device, 2, writes, 0, nullptr);

    m_resetAccumulation = true;
    return InitializationResult::success();
}
```

### Starting the sum again

`m_resetAccumulation` is the Jump box's rule in one boolean. `Resize` sets it,
and so does `Update` (section 5) whenever the camera moves or a setting that
changes the picture changes. `Record` acts on it first thing, in its step 1
(section 3 prints it), and tells the shader through the push constants: the
frames summed so far, which it sets back to 0. The shader then adds to the
image when `accumulatedFrames` is above 0 and overwrites it when it is 0. That
`if` is the whole progressive design. Chapter 07 section 9 had every panel
return whether it changed something, and this is the demo that boolean was
for.

### The push constants

**This is `Shaders/PathTrace/PathTraceTypes.h`**, a C++/GLSL twin like Life's
(Chapter 08 section 8), with what the shader needs each frame. 96 bytes, within
the 128 Vulkan guarantees for push constants:

```c
/* Shaders/PathTrace/PathTraceTypes.h - Chapter 33's C++/GLSL twins. GLSL includes it as
   "PathTraceTypes.h", C++ as "PathTrace/PathTraceTypes.h". */
#ifndef PF_PATH_TRACE_TYPES_H
#define PF_PATH_TRACE_TYPES_H

#include "SharedShaderTypes.h"   /* the mat4, vec4, and uint aliases, on the C++ side */

#ifdef __cplusplus
    namespace pf::demos::path_tracer {
    using shared::mat4;
    using shared::vec4;
    using shared::uint;
#endif

/* The push constants: everything the tracer needs that can change from frame to frame. */
struct PathTraceParameters
{
    mat4 inverseViewProjection;   /*  0  clip space back to world space (section 3) */
    vec4 cameraPosition;          /* 64  xyz world-space eye; w unused */
    uint accumulatedFrames;       /* 80  frames already summed; 0 = start the sum again (section 1) */
    uint frameSeed;               /* 84  different every frame, never reset: seeds the random numbers */
    uint samplesPerFrame;         /* 88  paths per pixel in this frame */
    uint maxBounces;              /* 92  surfaces one path may hit */
};

#ifdef __cplusplus
    static_assert(sizeof(PathTraceParameters) == 96, "PathTraceParameters layout drifted.");
    static_assert(offsetof(PathTraceParameters, accumulatedFrames) == 80, "PathTraceParameters alignment drifted.");
    }
#endif

#endif
```

### The barrier between frames

The accumulation image is the one resource this demo keeps from one frame to
the next, so it is the one that needs a barrier between frames. Frame N's
dispatch writes it; frame N+1's dispatch reads it and writes it again. Work in
two submissions is no more ordered than two dispatches in one command buffer
(Chapter 20 section 5): only a barrier orders them, and a barrier reaches back
across submissions on the same queue. So `Record` puts one before its dispatch,
and Chapter 04's three questions answer it:

- **Q1 (execution):** last frame's `COMPUTE_SHADER` work finishes before this
  frame's `COMPUTE_SHADER` work starts.
- **Q2 (memory):** last frame's `SHADER_STORAGE_WRITE`s are made visible to this
  frame's `SHADER_STORAGE_READ`s and `SHADER_STORAGE_WRITE`s — both, because the
  shader reads the sum and then overwrites it.
- **Q3 (layout):** none. The image stays in `GENERAL`, so a memory barrier is
  enough.

That is exactly Chapter 20's `computeToComputeBarrier`, so `Record` calls it:

```cpp
    // 3. Section 1: last frame's dispatch wrote the accumulation image; this one reads it
    //    and writes it again.
    computeToComputeBarrier(commandBuffer);
```

It is the row "Accumulation image, frame to frame" in Chapter 04's appendix of
barriers. The exit check removes it on purpose and expects synchronization
validation to say so. The hazard is a shader's access through a descriptor, so
the layer sees it only through the setting Chapter 02 section 2 turned on
(Chapter 20 section 5 explains it); a quiet layer proves nothing until that
control has fired.

---

## 2. Randomness

Every path needs fresh random numbers, and a GPU has no `rand()`. Chapter 21
section 3 built what this chapter needs: `seedRandom(index, frame)` starts a
stream from two numbers, and `randomFloat(state)` returns the next number in
`[0, 1)` and advances the stream. The tracer keeps one stream per pixel, in a
local `uint` it passes to everything that draws from it, and seeds it once, in
`main`:

```glsl
    // Section 2: a different stream for every pixel in every frame.
    uint rng = seedRandom(uint(pixel.y * size.x + pixel.x), parameters.frameSeed);
```

**Seed from the pixel and the frame together**, for the reason Chapter 21 gave
for particles. Seeded from the pixel alone, every frame repeats the last one's
paths exactly, and the average never changes: the image stays noisy forever,
which looks like broken accumulation rather than a broken seed.

**The frame number here never resets.** `frameSeed` counts every frame the
demo has recorded, while `accumulatedFrames` goes back to 0 whenever the sum
starts again. Seeding from the second would give the first frame after every
camera move the same random numbers, so while you orbit, the noise would hold
still on the screen like dirt on a window instead of shimmering.

Better sequences than a hash — Sobol, blue noise — reach the same quality in
noticeably fewer samples. They are section 8's first entry; get the picture
right first.

---

## 3. A ray for every pixel, and what it hits

### Where the shader code goes

**This is `Shaders/PathTrace/PathTrace.glsl`**, the tracer, which both routes
share. Route A's `Spheres.comp.glsl` and route B's `Meshes.comp.glsl` each
include it and then define one function, `intersectScene`, which returns the
nearest surface along a ray. The tracer calls that function and knows nothing
else about the scene, which is why route B changes nothing but it. GLSL, like
C, needs a function declared before it is called, so the head of the file
declares it and each route defines it afterwards:

```glsl
// Shaders/PathTrace/PathTrace.glsl - the path tracer, shared by both routes (Chapter 33).
// An include, not a stage: Spheres.comp.glsl (route A) and Meshes.comp.glsl (route B)
// include it, then define intersectScene, the one function that differs between them.

#include "Random.glsl"       // pcgHash (Chapter 20); seedRandom and randomFloat (Chapter 21)
#include "PathTraceTypes.h"  // PathTraceParameters, shared with C++

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0, rgba32f) uniform image2D accumulationImage;       // the demo's: sum and count
layout(set = 0, binding = 1, rgba16f) uniform writeonly image2D outputImage;   // the engine's scene target

layout(push_constant) uniform PathTraceBlock
{
    PathTraceParameters parameters;
};

struct Material
{
    vec3 albedo;     // the fraction of arriving light the surface reflects, per channel
    vec3 emission;   // light the surface gives off itself (linear, like every color here)
};

struct Hit
{
    bool     valid;      // false: the ray left the scene
    float    distance;   // along the ray from its origin
    vec3     position;
    vec3     normal;     // unit length, pointing out of the surface
    Material material;
};

// Each route defines this after including this file: the nearest surface along a ray
// whose direction is unit length.
Hit intersectScene(vec3 origin, vec3 direction);
```

The rest of `PathTrace.glsl` follows in this order: `cameraRayDirection` and
`environmentRadiance` (this section), then `randomPointOnSphere`,
`sampleCosineHemisphere`, `maxComponent`, `tracePath`, and `main` (section 4).
Chapter 06's glob compiles only `Name.stage.glsl` files, so `PathTrace.glsl`,
like `Random.glsl`, is compiled only through the files that include it.

### From a pixel to a ray

Rasterizing ran the camera forwards: Chapter 10 took a point in the world
through the view matrix, then the projection, then divided by `w`, and got a
place on the screen. A ray tracer needs the opposite question: *which points in
the world lie under this pixel?* So it runs the same chain backwards.

```text
 pixel (x, y) ──► NDC: x and y from -1 to 1          (y = -1 is the TOP: Vulkan's Y-down)
        │
        │  pick depth 1, the far plane, and w = 1
        ▼
 inverse(projection × view) × (ndc.x, ndc.y, 1, 1)   = the far point, but scaled by 1/w
        │
        │  divide by w: Chapter 10 section 2's divide, run backwards
        ▼
 a world point on the far plane ──► the ray: from the camera, towards that point
```

The inverse of a matrix undoes it (Chapter 10 section 4), so
`inverse(projection × view)` takes a clip-space point back into world space.
What it cannot undo by itself is the divide by `w` that the GPU did after the
projection; a point that came back with `w = 0.002` is its world position
divided by 500. Dividing by the `w` that comes out restores it.

Worked, with the default camera (at `(0, 2.11, -7.92)`, 1280 × 720, a 500 m far
plane): the centre pixel has NDC `(0, 0)`. Multiplied by the inverse,
`(0, 0, 1, 1)` comes back as `(0, -0.135, 0.974, 0.002)`. Its `w` is 0.002,
which is 1/500, so dividing by it gives the world point `(0, -67.5, 487.2)`:
500 m from the camera along its view direction, `(0, -0.139, 0.990)`, which is
the 8° downward tilt the constructor gave it. The top-left pixel, NDC
`(-1, -1)`, comes back as the direction `(0.66, 0.28, 0.69)`: up, because
running Chapter 10's flipped projection backwards flips y back, and towards +X,
which is the picture's left. No flip is needed anywhere else.

The C++ side builds the matrix once a frame, in `Record`'s step 2 at the end of
this section: `glm::inverse(m_camera.Projection(aspect) * view)`, pushed as
`inverseViewProjection`. The shader side is the diagram:

```glsl
// Section 3: the direction of the ray through a point of the image. ndc is (-1, -1) at the
// top-left corner and (1, 1) at the bottom-right: Vulkan's clip space (Chapter 10 section 1).
vec3 cameraRayDirection(vec2 ndc)
{
    // The point on the far plane (depth 1) under ndc, taken back into the world. The inverse
    // undoes the projection and the view but not the divide by w, so divide here.
    vec4 farPoint = parameters.inverseViewProjection * vec4(ndc, 1.0, 1.0);
    return normalize(farPoint.xyz / farPoint.w - parameters.cameraPosition.xyz);
}
```

### The scene

**This is `Shaders/PathTrace/Spheres.comp.glsl`**, route A's whole scene: a
floor, three spheres of radius 1 standing on it, and a fourth above them that
glows. The red and the green are what make color bleeding visible on the white
sphere and the floor between them.

```glsl
// Shaders/PathTrace/Spheres.comp.glsl - route A: a floor and four spheres, hit by formula.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "PathTrace.glsl"   // the tracer: everything except the scene

struct Sphere
{
    vec3     center;
    float    radius;
    Material material;
};

// The scene: a grey floor, a red and a green sphere either side of a white one, and
// a light. The red and green are what make color bleeding visible on the white
// sphere and the floor.
const Material floorMaterial = Material(vec3(0.75), vec3(0.0));

const Sphere spheres[4] = Sphere[](
    Sphere(vec3(-2.1, 1.0, 0.0), 1.0, Material(vec3(0.75, 0.15, 0.15), vec3(0.0))),
    Sphere(vec3( 0.0, 1.0, 0.0), 1.0, Material(vec3(0.75), vec3(0.0))),
    Sphere(vec3( 2.1, 1.0, 0.0), 1.0, Material(vec3(0.15, 0.75, 0.15), vec3(0.0))),
    Sphere(vec3( 0.0, 5.0, 2.0), 1.0, Material(vec3(0.0), vec3(12.0)))
);
```

The light's emission, 12, is radiance in the same linear units as everything
else; it is far above 1 because the light is small and far from most of what it
lights. Section 5's tone curve is what brings it back into range.

**Where a ray meets a sphere.** A ray is every point `origin + t × direction`
for `t > 0`, with `direction` of length 1, and a sphere is every point at
distance `radius` from its centre. A hit is a `t` that is both. Put
`offset = origin − center`; then "at distance `radius`" is
`|offset + t × direction|² = radius²`, and multiplying out (using `direction ·
direction = 1`) gives a quadratic in `t`:

$$
t^2 + 2bt + c = 0, \qquad b = \text{offset} \cdot \text{direction}, \qquad c = \text{offset} \cdot \text{offset} - \text{radius}^2
$$

whose two roots are `t = −b ± √(b² − c)`: where the ray goes in and where it
comes out. When `b² − c` is negative the line misses the sphere. Worked, for a
ray from `(0, 1, −8)` straight along +Z at the white sphere: `offset = (0, 0,
−8)`, `b = −8`, `c = 64 − 1 = 63`, `b² − c = 1`, so `t = 8 − 1 = 7` (in, at
z = −1) or `8 + 1 = 9` (out, at z = 1). The nearer positive root is the hit.

```glsl
// Distance along a unit-length direction to the nearest hit in front of the
// origin, or -1.0 for a miss. Points at distance t are origin + t * direction;
// putting that into |p - center|^2 = radius^2 gives t^2 + 2bt + c = 0, with b and c below.
float intersectSphere(Sphere sphere, vec3 origin, vec3 direction)
{
    vec3  offset       = origin - sphere.center;
    float b            = dot(offset, direction);
    float c            = dot(offset, offset) - sphere.radius * sphere.radius;
    float discriminant = b * b - c;
    if (discriminant < 0.0) { return -1.0; }   // the line misses the sphere

    float root = sqrt(discriminant);
    float t    = -b - root;             // the near side
    if (t <= 0.0) { t = -b + root; }    // origin inside the sphere: take the far side
    return t > 0.0 ? t : -1.0;          // both behind the origin: a miss
}
```

**This is `intersectScene`**: test everything, keep the nearest. The floor is
the plane y = 0, which a ray heading down reaches at `t = −origin.y /
direction.y`; its normal is straight up everywhere. A sphere's normal at a point
is the direction from its centre to that point.

```glsl
Hit intersectScene(vec3 origin, vec3 direction)
{
    Hit hit;
    hit.valid    = false;
    hit.distance = 1e30;

    // The floor: the plane y = 0, hit only by rays heading down onto it.
    if (direction.y < 0.0)
    {
        float t = -origin.y / direction.y;
        if (t > 0.0)
        {
            hit.valid    = true;
            hit.distance = t;
            hit.position = origin + direction * t;
            hit.normal   = vec3(0.0, 1.0, 0.0);
            hit.material = floorMaterial;
        }
    }

    // The spheres: keep whichever hit is nearest.
    for (int i = 0; i < spheres.length(); ++i)
    {
        float t = intersectSphere(spheres[i], origin, direction);
        if (t > 0.0 && t < hit.distance)
        {
            hit.valid    = true;
            hit.distance = t;
            hit.position = origin + direction * t;
            hit.normal   = normalize(hit.position - spheres[i].center);
            hit.material = spheres[i].material;
        }
    }
    return hit;
}
```

The floor is an exact plane rather than the old trick of a huge sphere, because
near the surface of a sphere of radius `R` the test above subtracts two numbers
close to `R²`, and in 32-bit floats that loses the answer long before `R`
reaches the thousands.

A ray that hits nothing has left the scene, and sees the sky. **This is
`environmentRadiance`**, in `PathTrace.glsl` because both routes share the sky.
It is deliberately dim, so that the glowing sphere is what lights the scene:

```glsl
// Section 3: the sky, dim and a little bluer overhead, so the light sphere is what
// lights the scene.
vec3 environmentRadiance(vec3 direction)
{
    float up = 0.5 * (direction.y + 1.0);   // 0 straight down, 1 straight up
    return mix(vec3(0.05), vec3(0.10, 0.14, 0.20), up);
}
```

The engine's sky setting (Chapter 23) does not reach this demo: the demo writes
every pixel of the scene target itself, sky included, and its sky is this
function. Replacing it with a lookup in the engine's sky cube would light the
scene as Chapter 24 lights it, now with every bounce: a good exercise once route
A converges.

### A first picture: what each ray hits

Everything so far can be checked before any randomness is involved: the rays
from section 3's un-projection, and the surfaces `intersectScene` finds. Noise
would hide a mistake in either. So, for now, `main` traces one ray through the
centre of each pixel and writes the normal of the first surface it hits, as a
color: a normal's components run from −1 to 1, and `normal * 0.5 + 0.5` squeezes
them into 0 to 1. **This is the temporary `main`**, at the end of
`PathTrace.glsl`; section 4 replaces it:

```glsl
// Section 3, for now: the first surface under the centre of each pixel, its normal shown as a
// color. Section 4's main replaces this one.
void main()
{
    ivec2 pixel = ivec2(gl_GlobalInvocationID.xy);
    ivec2 size  = imageSize(accumulationImage);
    if (pixel.x >= size.x || pixel.y >= size.y) { return; }

    vec2 ndc   = (vec2(pixel) + 0.5) / vec2(size) * 2.0 - 1.0;
    Hit  hit   = intersectScene(parameters.cameraPosition.xyz, cameraRayDirection(ndc));
    vec3 color = hit.valid ? hit.normal * 0.5 + 0.5 : vec3(0.0);   // -1..1 squeezed into 0..1
    imageStore(outputImage, pixel, vec4(color, 1.0));
}
```

To run it, the demo needs its pipeline, its frame, and its teardown. None of
them changes when section 4's tracer replaces this `main`, so they are written
here, once.

### The pipelines

**This is `CreatePipelines`.** One pipeline layout — set 0 and the push
constants — and one compute pipeline per route. Route A's is here; route B adds
its own, and its set 1, in section 6. The layout's set list is a vector for that
reason: section 6 appends to it.

```cpp
InitializationResult PathTracerDemo::CreatePipelines()
{
    // Set 0 for both routes; route B's set 1 joins it when there is one (section 6).
    std::vector<VkDescriptorSetLayout> setLayouts{ m_setLayout };

    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(PathTraceParameters),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = static_cast<uint32_t>(setLayouts.size()),
        .pSetLayouts            = setLayouts.data(),
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_vulkan.device, &layoutInfo, nullptr, &m_pipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the path tracer.");
    }

    m_spheresPipeline = createComputePipeline(m_vulkan.device, m_pipelineCache,
                                              "PathTrace/Spheres.comp.spv", m_pipelineLayout);
    if (m_spheresPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the path tracer's route A pipeline failed.");
    }
    return InitializationResult::success();
}
```

### The scene target, both directions

These are Chapter 20 section 10's two barriers on the scene target, unchanged,
with the path tracer as the writer: before the dispatch, from last frame's
composite read (`FRAGMENT_SHADER`, `NONE`) to this frame's
`SHADER_STORAGE_WRITE` in `GENERAL`, from `UNDEFINED` because every pixel is
rewritten; after it, `handBackSceneTarget` from `GENERAL` and
`COMPUTE_SHADER`/`SHADER_STORAGE_WRITE`. They are steps 4 and 6 of `Record`.

### `Record`

**This is `Record`**, in order. Step 1 is section 1's reset, step 2 section 3's
camera, step 3 section 1's barrier between frames.

```cpp
void PathTracerDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const VkExtent2D      extent        = frame.targets.extent;

    // 1. Section 1: start the sum again if anything made it wrong.
    if (m_resetAccumulation)
    {
        m_accumulatedFrames  = 0;
        m_accumulatedSamples = 0;
        m_resetAccumulation  = false;
    }

    // 2. Section 3: the camera, as the matrix that takes a pixel back into the world.
    const float     aspect = static_cast<float>(extent.width) / static_cast<float>(extent.height);
    const glm::mat4 view   = scene::viewMatrix(m_cameraTransform.Matrix());
    const PathTraceParameters parameters{
        .inverseViewProjection = glm::inverse(m_camera.Projection(aspect) * view),
        .cameraPosition        = glm::vec4(m_cameraTransform.translation, 1.0f),
        .accumulatedFrames     = m_accumulatedFrames,
        .frameSeed             = m_frameSeed++,
        .samplesPerFrame       = static_cast<uint32_t>(m_settings.samplesPerFrame),
        .maxBounces            = static_cast<uint32_t>(m_settings.maxBounces),
    };

    // 3. Section 1: last frame's dispatch wrote the accumulation image; this one reads it
    //    and writes it again.
    computeToComputeBarrier(commandBuffer);

    // 4. Section 3: the scene target, from last frame's composite read to this frame's writes.
    transitionImage(commandBuffer, frame.targets.colorImage,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    // 5. Section 3: one invocation per pixel, with the route the panel picked.
    const bool meshes = m_settings.route == 1 && m_meshesPipeline != VK_NULL_HANDLE;
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, meshes ? m_meshesPipeline : m_spheresPipeline);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_pipelineLayout,
                            0, 1, &m_set, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                       0, sizeof(parameters), &parameters);
    vkCmdDispatch(commandBuffer, groupCount(extent.width, GROUP_SIZE), groupCount(extent.height, GROUP_SIZE), 1);

    ++m_accumulatedFrames;
    m_accumulatedSamples += parameters.samplesPerFrame;

    // 6. Section 3: hand the scene target to the composite pass, which tone-maps it.
    handBackSceneTarget(commandBuffer, frame.targets, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
}
```

`m_meshesPipeline` is null until section 6, so `meshes` is false and route A
always runs. The aspect ratio comes from the target each frame, so a resize
needs nothing here: `Resize` has already restarted the sum.

### Teardown, and registering the demo

**This is `Teardown`**: reverse order of `Setup` and `Resize`, every destroy
safe on a null handle. The camera and the settings are CPU state and stay.

```cpp
void PathTracerDemo::Teardown()
{
    // Chapter 09 waited for the device. Reverse order of Setup and Resize; Vulkan's
    // destroy calls accept null handles, so a partial Setup is safe too.
    vkDestroyPipeline(m_vulkan.device, m_meshesPipeline, nullptr);
    vkDestroyPipeline(m_vulkan.device, m_spheresPipeline, nullptr);
    vkDestroyPipelineLayout(m_vulkan.device, m_pipelineLayout, nullptr);
    vkDestroyDescriptorPool(m_vulkan.device, m_descriptorPool, nullptr);   // frees the set
    vkDestroyDescriptorSetLayout(m_vulkan.device, m_setLayout, nullptr);
    DestroyAccumulationImage();

    m_meshesPipeline  = VK_NULL_HANDLE;
    m_spheresPipeline = VK_NULL_HANDLE;
    m_pipelineLayout  = VK_NULL_HANDLE;
    m_descriptorPool  = VK_NULL_HANDLE;
    m_setLayout       = VK_NULL_HANDLE;
    m_set             = VK_NULL_HANDLE;
}
```

And in `Main.cpp`, an include beside the other demos' and one line at the end of
the list (Chapter 09 section 7):

```cpp
#include "PillowFort/Demos/PathTracer/PathTracerDemo.h"
```

```cpp
    demoList.push_back(std::make_unique<demos::path_tracer::PathTracerDemo>());   // Chapter 33
```

### `Update`, for now

The camera must move, so that you can check the rays from more than one place.
Section 5's `Update` adds the panel and the rule for restarting the sum; until
then it is only the camera's controls and panel:

```cpp
void PathTracerDemo::Update(const FrameInput& input)
{
    // Section 3, for now: only the camera. Section 5's Update adds the panel and the restart rule.
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    m_controls.Update(input.deltaSeconds, m_cameraTransform);
    scene::drawCameraPanel(m_camera, m_controls, m_cameraTransform);
}
```

## Checkpoint

Rerun `GenerateProjects.bat`, build, and run with `--demo Path`. You can now
see the scene in false color, one color per direction a surface faces:

- **the floor**, flat light green everywhere: its normal is straight up,
  `(0, 1, 0)`, which shows as `(0.5, 1, 0.5)`;
- **four spheres**, each yellow where it faces the camera (−Z, `(0.5, 0.5, 0)`),
  green toward the top, magenta underneath, pink on the side facing +X (the
  picture's left) and teal on the other; the light sphere hangs above them;
- **black** wherever a ray hits nothing;
- **the spheres in their order**: the one at x = −2.1, red in section 5's
  picture, is on the right, because the camera looks down +Z. Orbit, and the
  spheres turn while their colors stay fixed to the world's directions: a
  surface facing +X is pink from wherever you look at it.

A sphere that comes out flat, a floor that is not one color, or a picture upside
down points at `intersectSphere`, the floor's normal, or the un-projection,
while the picture is still simple enough to read.

---

## 4. The tracer

Section 0's recipe was "at each surface, pick one direction at random and
follow it". Two questions are still open: *which* random direction, and what to
do with the answer so that the average comes out right. Both have one-line
answers once one more idea is in place.

### Choosing directions, and the pdf

Not all directions above a surface matter equally. The cos θ in the rendering
equation means light arriving straight down along the normal counts fully and
light arriving at a grazing angle counts almost nothing. A path that wastes its
one direction near the horizon brings back little. So the tracer picks
directions **more often near the normal**, in proportion to cos θ. Here is how
uneven that is, as the fraction of picked directions within an angle of the
normal:

| Within | 30° | 45° | 60° |
| --- | --- | --- | --- |
| Picked in proportion to cos θ | 25% | 50% | 75% |
| Picked evenly over the hemisphere | 13% | 29% | 50% |

A rule for how likely each direction is to be picked is a **probability
density**, or **pdf**. With infinitely many directions, any single one has no
chance at all of being picked exactly; a density says instead how thickly the
picks crowd around each direction, per unit of the hemisphere's area, the way a
population density is people per square kilometre. "In proportion to cos θ" is
the pdf `cos θ / π` (the π makes the whole hemisphere add up to exactly 1, for
the same reason π appears in Lambert's BRDF). In numbers: 0.32 along the normal,
0.16 at 60° from it, 0 at the horizon. An even spread is 0.16 everywhere.

The rule that goes with a pdf: **divide each sample by the pdf of the
direction you picked.** It is the darts' "multiply by the size of what you
sampled", generalized. Picked evenly, every direction above a surface has pdf
1/(2π) — the hemisphere's area is 2π, Chapter 21's `2πh` with `h = 1` — so
dividing by it multiplies by 2π, just as the darts multiplied by the square's
area. Picked unevenly, a direction picked twice as often as an even spread would
pick it is divided by a pdf twice as large, so it counts half as much; otherwise
the directions near the normal would be counted twice over and the average would
come out too bright. In darts terms: throw twice as many darts at the left half
of the square, and each left-half dart must count as half a dart. Choosing the
pdf to favor what matters is called **importance sampling**. If you built
Chapter 24, you have met it without the randomness: section 7's lookup table
placed its directions in rings that each hold an equal share of GGX's lobe, so
they crowd where the lobe is strong, and then counted each one equally. Here the
directions crowd where the cosine is large, and dividing by the pdf does the
counting.

So one path's estimate of the reflected light, from one direction, is

$$
\frac{\text{BRDF} \times L_{\text{in}} \times \cos\theta}{\text{pdf}}
= \frac{(\text{albedo} / \pi) \times L_{\text{in}} \times \cos\theta}{\cos\theta / \pi}
= \text{albedo} \times L_{\text{in}}
$$

The cosine and both πs cancel. With directions picked in proportion to cos θ,
a matte surface simply multiplies whatever light the next direction brings back
by its albedo. That is why the tracer below has no cosine and no π in it, and
why adding a cosine "because the rendering equation has one" is the classic bug:
it counts the cosine twice and gives a picture that looks plausible and is too
dark.

**How to pick in proportion to cos θ.** A neat geometric fact does it: take a
sphere of radius 1 resting on the surface at the hit point, so its centre is at
`hit + normal`. Pick a point uniformly on that sphere's surface, and the
direction from the hit point to it is distributed exactly as cos θ / π: the
25%, 50%, and 75% in the table above are what it produces. In code, that is
`normal + a random point on the unit sphere`, normalized.

A random point on the unit sphere comes from Chapter 21's cone trick with the
cone opened all the way: the height `z` is uniform in `[−1, 1]`, and so is the
angle around it (Archimedes showed that equal slices of height cut equal areas
from a sphere). Both functions go in `PathTrace.glsl` after
`environmentRadiance`:

```glsl
// Section 4: uniform on the unit sphere - Chapter 21's cone trick with the cone opened all
// the way: the height z is uniform in [-1, 1], and so is the angle around it.
vec3 randomPointOnSphere(inout uint rng)
{
    float z   = randomFloat(rng) * 2.0 - 1.0;
    float phi = randomFloat(rng) * 6.28318530718;
    float r   = sqrt(max(0.0, 1.0 - z * z));
    return vec3(r * cos(phi), r * sin(phi), z);
}

// Section 4: a direction around `normal` with pdf cos(theta) / pi - more often near the
// normal, never below the surface. A point on a unit sphere resting on the surface, seen
// from where the sphere touches it, lies in exactly that distribution.
vec3 sampleCosineHemisphere(vec3 normal, inout uint rng)
{
    vec3 direction = normal + randomPointOnSphere(rng);
    // Vanishingly rare, but a zero vector normalizes to NaN, and one NaN
    // sample poisons that pixel's accumulation for good.
    return dot(direction, direction) > 1e-8 ? normalize(direction) : normal;
}

float maxComponent(vec3 v) { return max(v.x, max(v.y, v.z)); }
```

### Throughput: what is left of the light

A path bounces several times before it reaches a light, and each bounce
multiplies by an albedo. A path that goes eye → white floor (0.75) → red sphere
(0.75, 0.15, 0.15) → light (12) brings back `0.75 × (0.75, 0.15, 0.15) × 12 =
(6.75, 1.35, 1.35)`: reddish light on the floor, which is color bleeding. The
tracer keeps that running product in a variable called **throughput** — "how
much of whatever this path finds next will reach the eye" — starting at 1 and
multiplied by each surface's albedo. Whatever light the path meets, emitted or
from the sky, is added to the result times the throughput so far.

### Russian roulette, in two numbers

After a few bounces most paths carry very little: four bounces off 0.75 surfaces
leave a throughput of 0.32, and off the red sphere's green channel, 0.15, far
less. Tracing them further costs as much as tracing bright ones. Stopping them
at a fixed bounce would be biased — it would drop real light — but stopping
them *at random*, and making the survivors brighter to compensate, is not:

- A path has throughput 0.1. Give it a survival chance of 0.1.
- 9 paths in 10 stop and add nothing more. 1 in 10 carries on, with its
  throughput divided by 0.1, so it is back to 1.
- On average the further light is `0.1 × (1 × L) + 0.9 × 0 = 0.1 × L` —
  exactly what all ten paths would have added at throughput 0.1. Unbiased, at a
  tenth of the cost.

That is **Russian roulette**. The tracer uses the throughput's largest channel
as the survival chance, so dim paths are culled and bright ones almost never,
clamps it to at least 0.05 so no survivor is multiplied by more than 20, and
waits until the fourth surface, because the first bounces are the ones the
picture depends on most and cutting them adds the most noise.

### `tracePath` and `main`

**This is `tracePath`**: section 0's recipe, with the pieces above.

```glsl
// Section 4: one path from the camera. Returns the light it carries back to the eye.
vec3 tracePath(vec3 origin, vec3 direction, inout uint rng)
{
    vec3 radiance   = vec3(0.0);   // light gathered so far, as it arrives at the eye
    vec3 throughput = vec3(1.0);   // how much of what the path finds next reaches the eye

    for (uint bounce = 0u; bounce < parameters.maxBounces; ++bounce)
    {
        Hit hit = intersectScene(origin, direction);
        if (!hit.valid)
        {
            radiance += throughput * environmentRadiance(direction);
            break;
        }

        radiance += throughput * hit.material.emission;

        // The next direction, picked with pdf cos/pi: the cosine and the 1/pi of the
        // Lambertian BRDF cancel against it, and the albedo is all that is left.
        direction   = sampleCosineHemisphere(hit.normal, rng);
        throughput *= hit.material.albedo;

        // Russian roulette, from the fourth surface on: stop dim paths at random, and
        // make the survivors brighter by exactly what the stopped ones would have added.
        if (bounce >= 3u)
        {
            float survival = clamp(maxComponent(throughput), 0.05, 1.0);
            if (randomFloat(rng) >= survival) { break; }
            throughput /= survival;
        }

        // Off the surface, or the next ray can hit the point it starts from.
        origin = hit.position + hit.normal * 1e-4;
    }
    return radiance;
}
```

**This is `main`**, in place of section 3's temporary one: one invocation per
pixel, as Chapter 20's display pass was. It traces `samplesPerFrame` paths, each
through a random point inside the pixel, adds their light to the sum, and writes
the average:

```glsl
void main()
{
    ivec2 pixel = ivec2(gl_GlobalInvocationID.xy);
    ivec2 size  = imageSize(accumulationImage);
    if (pixel.x >= size.x || pixel.y >= size.y) { return; }

    // Section 2: a different stream for every pixel in every frame.
    uint rng = seedRandom(uint(pixel.y * size.x + pixel.x), parameters.frameSeed);

    vec3 sum = vec3(0.0);
    // Not `sample`: that is a reserved word in GLSL.
    for (uint sampleIndex = 0u; sampleIndex < parameters.samplesPerFrame; ++sampleIndex)
    {
        // A random point inside the pixel, not its centre: averaging them is the antialiasing.
        vec2 jitter = vec2(randomFloat(rng), randomFloat(rng));
        vec2 ndc    = (vec2(pixel) + jitter) / vec2(size) * 2.0 - 1.0;
        sum += tracePath(parameters.cameraPosition.xyz, cameraRayDirection(ndc), rng);
    }

    // Section 1: add to what earlier frames left, unless the sum is starting again.
    vec4 previous    = parameters.accumulatedFrames == 0u ? vec4(0.0) : imageLoad(accumulationImage, pixel);
    vec4 accumulated = previous + vec4(sum, float(parameters.samplesPerFrame));
    imageStore(accumulationImage, pixel, accumulated);

    // The average, still linear: the composite pass tone-maps and encodes it (section 5).
    imageStore(outputImage, pixel, vec4(accumulated.rgb / accumulated.a, 1.0));
}
```

Four details carry weight:

- **The origin offset, `1e-4`.** A hit position computed in floating point lands
  a hair above or below the true surface. Below, the next ray starts inside the
  surface and hits it again at once, and the picture comes out dark and grainy —
  "shadow acne". Moving the origin a tenth of a millimetre along the normal is
  enough at this scene's scale; a scene measured in kilometres needs the offset
  to grow with the distance from the origin.
- **No cosine in the loop.** The cancellation above already counted it.
- **Roulette from the fourth surface, not the first.** Starting it at bounce 0
  adds noise to exactly the paths that matter most.
- **The jitter is the antialiasing.** Each sample goes through a different
  random point of its pixel, so edges average out over the frames with no MSAA
  and no extra pass.

---

## 5. Displaying it, and what restarts the sum

### Tone mapping is the engine's

There is no new display pass and no new shader. A path tracer's light goes far
above 1.0 — the glowing sphere is 12 — and Chapter 08's composite pass would
clamp it, throwing every highlight away. Chapter 16 section 6 already grew that
pass an exposure control, in stops, and a choice of tone curve, applied to the
scene target just before the sRGB encode, with a "Tone mapping" panel to drive
them. The path tracer uses it as every other demo does: its only job is to
leave the scene target in `SHADER_READ_ONLY_OPTIMAL`.

If you came here from Chapter 20 without doing 11-19, do Chapter 16 section 6
now. It touches only the composite shader, the composite pipeline layout's
push-constant range, `ToneMapping.h` and its panel, and one line in `main`, and
it needs nothing else from Chapter 16. Its defaults, 0 stops and the raw curve,
are Chapter 08's clamp exactly, so nothing earlier changes.

For the path tracer, pick the ACES curve and leave the exposure at 0 stops;
lower the exposure if the floor under the light washes out.

**Exposure does not restart the sum, and must not.** It changes how the
composite reads the scene target, after the average is taken, so the samples
summed so far stay right. The demo never even sees it: the tone-mapping
settings belong to the renderer, not to the demo, which makes the mistake —
resetting on an exposure change — impossible here. It is an easy one to make
in a renderer where they live together, and it makes the tracer feel broken.

### `Update`, the panel, and what restarts the sum

**This is the panel**, a free function beside the demo (Chapter 07 section 9),
above `PathTracerDemo`'s functions in the file. It shows the progress and edits
the settings, and returns true when a change makes the summed samples wrong:

```cpp
// Section 5. Edits the settings and shows the progress. Inside the namespace because it
// names the demo's types; static because only this file calls it. True when a change
// makes the samples summed so far wrong.
static bool drawPathTracerPanel(PathTracerSettings& settings, bool routeBReady,
                                uint32_t samplesPerPixel, float seconds)
{
    bool restart = false;
    if (debug_panels::beginDemoPanel("Path tracer", debug_panels::DemoPanelSlot::BelowCamera))
    {
        ImGui::Text("Samples per pixel  %u", samplesPerPixel);
        ImGui::Text("Seconds            %.1f", seconds);
        ImGui::Text("Samples per second %.1f", seconds > 0.0f ? static_cast<float>(samplesPerPixel) / seconds : 0.0f);

        // Not a restart: the accumulation image counts samples, so frames with different
        // numbers of them average correctly. Clamped even when typed (Ctrl+click): 0 right
        // after a restart divides 0 by 0, and a large or negative count (the shader's is
        // unsigned) outlasts Windows' GPU watchdog, TDR (Chapter 34 section 6).
        ImGui::SliderInt("Samples per frame", &settings.samplesPerFrame, 1, 16, "%d", ImGuiSliderFlags_AlwaysClamp);

        // A different bounce limit is a different picture.
        restart |= ImGui::SliderInt("Max bounces", &settings.maxBounces, 1, 16);
        if (routeBReady)
        {
            restart |= ImGui::Combo("Route", &settings.route, "A: spheres, by formula\0B: triangles, by ray query\0");
        }
        restart |= ImGui::Button("Restart");
    }
    ImGui::End();
    return restart;
}
```

**This is `Update`**, in place of section 3's camera-only one. Input first, then
the panels, as in every camera demo; the
camera controllers and the camera panel report whether they moved anything
(Chapter 10 section 12), and that, or the path tracer's panel, restarts the sum.
It also notes when the sum restarted, so the panel can show seconds and samples
per second since then:

```cpp
void PathTracerDemo::Update(const FrameInput& input)
{
    // Input first, then the panels. Anything that moves the camera or changes what a
    // sample means starts the sum again.
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    bool restart = m_controls.Update(input.deltaSeconds, m_cameraTransform);
    restart |= scene::drawCameraPanel(m_camera, m_controls, m_cameraTransform);
    restart |= drawPathTracerPanel(m_settings, m_meshesPipeline != VK_NULL_HANDLE, m_accumulatedSamples,
                                   input.elapsedSeconds - m_restartSeconds);

    if (restart)
    {
        m_resetAccumulation = true;
    }
    if (m_resetAccumulation)   // from here or from Resize
    {
        m_restartSeconds = input.elapsedSeconds;
    }
}
```

The whole rule, as a table:

| Change | Restarts the sum? | Why |
| --- | --- | --- |
| Camera moved, by mouse or panel; field of view | Yes | Every pixel looks somewhere else |
| Window resized | Yes (`Resize`) | The pixels themselves are new |
| Max bounces, route, the Restart button | Yes | A different estimate, or asked for |
| Samples per frame | No | The image counts samples, not frames |
| Exposure, tone curve | No | They act on the average, after it is taken |
| Another demo and back | Yes (`Resize` after `Setup`) | The accumulation image was released |

## Checkpoint

Run with `--demo Path`. The first frame is one path per pixel and mostly noise:
the spheres are recognizable, and the floor is a scatter of bright specks where
a path happened to reach the light. It settles as the samples add up:

| Samples per pixel | What it looks like |
| --- | --- |
| 1-2 | The spheres' shapes; the floor a dense field of white specks |
| 16 | Specks thinning; the shadows under the spheres just visible |
| 64 | Soft shadows under each sphere; fine grain everywhere |
| 256 | Grain only up close; a green tint on the white sphere's side toward the green one, and on the floor between them |
| 1000 | Clean at a glance; more samples change nothing you can see |

The red sphere is on the right because the camera looks down +Z (the class
map's note). Orbit the camera and the picture goes back to noise and starts
settling again; drag the exposure slider and it does not. That is route A,
complete.

---

## 6. Route B: ray query over triangle meshes

Spheres stop being enough the moment you want a real model. Route B lets the
GPU find the nearest hit among triangles, and it keeps everything else:
`intersectScene` is the only shader function that changes, and the scene is
section 3's, rebuilt from Chapter 11's meshes so you can switch routes and see
that the picture holds. Its pieces:

```text
Shaders/PathTrace/Meshes.comp.glsl            new: intersectScene by ray query
Shaders/PathTrace/PathTraceTypes.h            + MeshInstance
Source/PillowFort/Demos/PathTracer/
  MeshScene.h/.cpp                            new: the meshes and their acceleration structures
  PathTracerDemo.h/.cpp                       + a MeshScene member, and the lines that use it
Source/PillowFort/VulkanGraphics/
  VulkanInstance.h/.cpp                       + supportsRayQuery; CreateDevice enables it when it can
  VulkanResources.h                           + VulkanContext::rayQuery
  VulkanRenderer.cpp                          + VMA's device-address flag; fills rayQuery
```

> **Jump:** two ideas arrive together, and neither has been used before. **Device
> addresses** (Chapter 08 section 9 described them): a buffer can be handed to
> the GPU as a raw 64-bit pointer instead of through a descriptor, and an
> acceleration structure's build reads every one of its inputs that way. And
> **a two-level acceleration structure**: each mesh's triangles are sorted once
> into a search tree, the bottom level, and the scene is a second, small tree of
> *instances* — a mesh and where it stands — the top level. Keep in mind that a
> ray query searches the top level, which leads it into the bottom levels, and
> that the shader never sees either tree: it is told only "triangle 37 of
> instance 2, at this distance, at this point on the triangle".

### Why a tree, and why two levels

Route A tests every object for every ray. That is fine for five objects and
hopeless for a model: the sphere mesh alone has 3,968 triangles, and a scene
can have millions. An **acceleration structure** is a tree of boxes. Each box
encloses part of the geometry, and a ray that misses a box skips everything
inside it, so a ray visits a handful of boxes and a few triangles instead of
every triangle. You never build the tree yourself: you describe the geometry,
give the driver memory, and ask it to build, on the GPU.

It comes in two levels because objects repeat and move:

```text
 TLAS (top level): five instances                 BLAS (bottom level): one per mesh
 ┌─────────────────────────────────────┐          ┌──────────────────────────────┐
 │ floor  -> floor BLAS,  at (0, 0, 0)    │ ───────► │ floor: 2 triangles           │
 │ red    -> sphere BLAS, at (-2.1, 1, 0) │ ──┐      └──────────────────────────────┘
 │ white  -> sphere BLAS, at (0, 1, 0)    │ ──┼────► ┌──────────────────────────────┐
 │ green  -> sphere BLAS, at (2.1, 1, 0)  │ ──┤      │ sphere: 3,968 triangles,     │
 │ light  -> sphere BLAS, at (0, 5, 2)    │ ──┘      │ in boxes within boxes        │
 └─────────────────────────────────────┘          └──────────────────────────────┘
```

A **bottom-level** structure (BLAS) holds one mesh's triangles, in the mesh's
own space. A **top-level** structure (TLAS) holds instances: each points at a
BLAS and says where it stands, with the top three rows of a model matrix. Four
of the five instances here share one sphere BLAS, so its triangles are stored
once; and moving an object means rebuilding only the small top level.

### Enabling it

Ray queries need three device extensions and two features, and not every GPU
has them, so the engine asks for them only where they exist and says so in
`VulkanContext`. Every other demo runs either way.

**This is `supportsRayQuery`**, in `VulkanInstance.cpp` after
`hasRequiredFeatures`. It is the same query `hasRequiredFeatures` makes, with
the ray-query feature structs in the chain:

```cpp
// File scope, above the namespace block. Chapter 33, route B: the three extensions
// and two features a ray query needs. Optional: a GPU without them runs everything else.
static bool supportsRayQuery(VkPhysicalDevice device)
{
    if (!hasDeviceExtension(device, VK_KHR_ACCELERATION_STRUCTURE_EXTENSION_NAME) ||
        !hasDeviceExtension(device, VK_KHR_RAY_QUERY_EXTENSION_NAME) ||
        !hasDeviceExtension(device, VK_KHR_DEFERRED_HOST_OPERATIONS_EXTENSION_NAME))
    {
        return false;
    }

    VkPhysicalDeviceRayQueryFeaturesKHR rayQuery{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_RAY_QUERY_FEATURES_KHR,
    };
    VkPhysicalDeviceAccelerationStructureFeaturesKHR accelerationStructure{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ACCELERATION_STRUCTURE_FEATURES_KHR,
        .pNext = &rayQuery,
    };
    VkPhysicalDeviceFeatures2 features{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
        .pNext = &accelerationStructure,
    };
    vkGetPhysicalDeviceFeatures2(device, &features);
    return accelerationStructure.accelerationStructure == VK_TRUE && rayQuery.rayQuery == VK_TRUE;
}
```

`VK_KHR_deferred_host_operations` is never used here, but
`VK_KHR_acceleration_structure` requires it to be enabled beside it.

**In `CreateDevice`**, everything from the extension list to `enabledFeatures`
changes. The list becomes a vector so the three extensions can join it; the two
feature structs are chained after `enable13` only when the GPU has them; and a
`VkPhysicalDeviceVulkan12Features` turns on buffer device addresses, which
Vulkan 1.3 requires every GPU to have, so it needs no check:

```cpp
    // Chapter 33, route B: the ray query extensions and features, only on a GPU that
    // has them, so that one without them still runs every other demo.
    m_rayQueryEnabled = supportsRayQuery(m_physicalDevice);
    std::vector<const char*> deviceExtensions = { VK_KHR_SWAPCHAIN_EXTENSION_NAME };
    if (m_rayQueryEnabled)
    {
        deviceExtensions.push_back(VK_KHR_ACCELERATION_STRUCTURE_EXTENSION_NAME);
        deviceExtensions.push_back(VK_KHR_RAY_QUERY_EXTENSION_NAME);
        deviceExtensions.push_back(VK_KHR_DEFERRED_HOST_OPERATIONS_EXTENSION_NAME);   // acceleration_structure needs it
    }
    VkPhysicalDeviceRayQueryFeaturesKHR enableRayQuery{
        .sType    = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_RAY_QUERY_FEATURES_KHR,
        .rayQuery = VK_TRUE,
    };
    VkPhysicalDeviceAccelerationStructureFeaturesKHR enableAccelerationStructure{
        .sType                 = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ACCELERATION_STRUCTURE_FEATURES_KHR,
        .pNext                 = &enableRayQuery,
        .accelerationStructure = VK_TRUE,
    };

    VkPhysicalDeviceVulkan13Features enable13{
        .sType                          = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES,
        .pNext                          = m_rayQueryEnabled ? &enableAccelerationStructure : nullptr,   // Chapter 33
        .shaderDemoteToHelperInvocation = VK_TRUE,   // GLSL discard (Chapter 15 section 11)
        .synchronization2               = VK_TRUE,
        .dynamicRendering               = VK_TRUE,
    };

    // Chapter 33: buffer device addresses (Chapter 08 section 9). Acceleration structures read
    // every input through them, and every Vulkan 1.3 GPU has them.
    VkPhysicalDeviceVulkan12Features enable12{
        .sType               = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES,
        .pNext               = &enable13,
        .bufferDeviceAddress = VK_TRUE,
    };

    VkPhysicalDeviceFeatures2 enabledFeatures{
        .sType    = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
        .pNext    = &enable12,
```

The rest of `enabledFeatures` is unchanged. In `deviceInfo`, the two extension
lines follow the vector, and after `vkGetDeviceQueue` one line reports what was
enabled:

```cpp
        .enabledExtensionCount   = static_cast<uint32_t>(deviceExtensions.size()),
        .ppEnabledExtensionNames = deviceExtensions.data(),
```

```cpp
    Log::info(m_rayQueryEnabled ? "Ray queries: enabled." : "Ray queries: not on this GPU.");   // Chapter 33
```

`VulkanInstance.h` gains the member and its accessor, beside the others:

```cpp
    bool             RayQueryEnabled() const { return m_rayQueryEnabled; }   // Chapter 33, route B
```

```cpp
    // Chapter 33: the ray query extensions are on - the GPU had them all.
    bool                     m_rayQueryEnabled = false;
```

`VulkanContext` (in `VulkanResources.h`) gains a last field, so that a demo can
ask without seeing `VulkanInstance`:

```cpp
    bool             rayQuery       = false;            // Chapter 33: ray queries are enabled
```

And in `VulkanRenderer::initialize`, the allocator is told that buffers may ask
for device addresses — the third of Chapter 08 section 9's three agreements —
and the context is filled in:

```cpp
        .flags            = VMA_ALLOCATOR_CREATE_BUFFER_DEVICE_ADDRESS_BIT,   // Chapter 33
```

```cpp
    m_context.rayQuery       = m_vulkan.RayQueryEnabled();   // Chapter 33
```

The first line is the first field of `allocatorInfo`; the second goes after
`m_context.graphicsQueue`. On a GPU that has ray queries, the log now says
`Ray queries: enabled.`

### What you are writing: `MeshScene`

Route B's scene is a class of its own beside the demo, because nothing in it
belongs to route A. **This is `MeshScene.h`**, its map:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Route B's scene: triangle meshes in acceleration structures, for ray queries (Chapter 33)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/PathTracer/MeshScene.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include <vulkan/vulkan.h>

#include <array>
#include <cstdint>

namespace pf::demos::path_tracer {

// Section 3's floor and spheres as triangle meshes: the two meshes in one vertex and one
// index buffer, a bottom-level acceleration structure for each, and a top-level one
// holding the five instances. Plus set 1, which hands all of it to Meshes.comp.glsl.
class MeshScene
{
public:
    // Only on a device with ray queries (VulkanContext::rayQuery). Destroy releases
    // whatever a failed Create got as far as making.
    InitializationResult Create(const vulkan_graphics::VulkanContext& context);
    void                 Destroy();

    VkDescriptorSetLayout SetLayout() const { return m_setLayout; }   // null until Create
    void Bind(VkCommandBuffer commandBuffer, VkPipelineLayout layout) const;   // as set 1

private:
    // An acceleration structure lives in a buffer, like an image lives in memory.
    struct AccelerationStructure
    {
        VkAccelerationStructureKHR       handle = VK_NULL_HANDLE;
        vulkan_graphics::AllocatedBuffer buffer;
        VkDeviceAddress                  address = 0;   // what a TLAS instance points at
    };

    // One mesh's place in the shared buffers: Chapter 19 section 4's idea.
    struct MeshRange
    {
        uint32_t firstIndex   = 0;
        uint32_t indexCount   = 0;
        uint32_t vertexOffset = 0;
        uint32_t vertexCount  = 0;
    };

    InitializationResult LoadFunctions();
    InitializationResult CreateGeometry();
    InitializationResult BuildBottomLevel(const MeshRange& mesh, AccelerationStructure& result);
    InitializationResult BuildTopLevel();
    InitializationResult Build(VkAccelerationStructureBuildGeometryInfoKHR& buildInfo,
                               uint32_t primitiveCount, AccelerationStructure& result);
    InitializationResult CreateDescriptors();

    vulkan_graphics::VulkanContext m_vulkan;

    // The five acceleration-structure entry points: extension functions, which the
    // Vulkan loader does not export, so they come from vkGetDeviceProcAddr.
    PFN_vkCreateAccelerationStructureKHR           m_createAccelerationStructure  = nullptr;
    PFN_vkDestroyAccelerationStructureKHR          m_destroyAccelerationStructure = nullptr;
    PFN_vkGetAccelerationStructureBuildSizesKHR    m_getBuildSizes                = nullptr;
    PFN_vkCmdBuildAccelerationStructuresKHR        m_cmdBuildAccelerationStructures = nullptr;
    PFN_vkGetAccelerationStructureDeviceAddressKHR m_getAccelerationStructureAddress = nullptr;
    VkDeviceSize                                   m_scratchAlignment = 0;

    // The geometry, and what each instance is made of.
    vulkan_graphics::AllocatedBuffer m_vertexBuffer;     // every mesh's scene::Vertex
    vulkan_graphics::AllocatedBuffer m_indexBuffer;      // every mesh's indices, each counting from 0
    vulkan_graphics::AllocatedBuffer m_instanceBuffer;   // a MeshInstance per TLAS instance
    std::array<MeshRange, 2>         m_meshes{};         // [sphere, floor]

    std::array<AccelerationStructure, 2> m_bottomLevels{};   // one per mesh
    AccelerationStructure                m_topLevel;

    // Set 1.
    VkDescriptorSetLayout m_setLayout      = VK_NULL_HANDLE;
    VkDescriptorPool      m_descriptorPool = VK_NULL_HANDLE;
    VkDescriptorSet       m_set            = VK_NULL_HANDLE;
};

} // namespace pf::demos::path_tracer
```

**This is `Create`**, in order: the entry points, the geometry, a BLAS per
mesh, the TLAS over them, and set 1.

```cpp
InitializationResult MeshScene::Create(const VulkanContext& context)
{
    m_vulkan           = context;
    m_scratchAlignment = queryScratchAlignment(m_vulkan.physicalDevice);

    if (auto result = LoadFunctions(); !result)  { return result; }
    if (auto result = CreateGeometry(); !result) { return result; }
    for (size_t i = 0; i < m_meshes.size(); ++i)
    {
        if (auto result = BuildBottomLevel(m_meshes[i], m_bottomLevels[i]); !result) { return result; }
    }
    if (auto result = BuildTopLevel(); !result)     { return result; }   // after the BLASes it points at
    if (auto result = CreateDescriptors(); !result) { return result; }
    return InitializationResult::success();
}
```

```text
MeshScene.cpp
  includes: MeshScene.h, PillowFort/Scene/MeshGenerators.h, PillowFort/VulkanGraphics/VulkanBarriers.h,
            "PathTrace/PathTraceTypes.h", <glm/glm.hpp>, <cstring>, <vector>
  struct SceneObject, static sceneObjects[]        the scene, below
  static bufferAddress(device, buffer)             below
  static queryScratchAlignment(physicalDevice)     "Building one"
  namespace pf::demos::path_tracer {
      using namespace vulkan_graphics;
      MeshScene::Create, LoadFunctions, CreateGeometry, BuildBottomLevel, BuildTopLevel,
      Build, CreateDescriptors, Bind, Destroy
  }
```

### Five entry points

**This is `LoadFunctions`.** The acceleration-structure functions belong to an
extension, and the Vulkan loader exports only core functions, so calling
`vkCreateAccelerationStructureKHR` directly compiles and then fails to link
(`LNK2019`). Instead, each is looked up by name at run time. They are
device-level functions, whose first parameter is the device or a command
buffer, so the lookup is `vkGetDeviceProcAddr` on the device that enabled the
extension: it returns that device's own entry point, which skips the loader's
dispatch on every call. What comes back is a generic `PFN_vkVoidFunction`, cast
to the function's own `PFN_` type, and the check after the five turns a missing
one into a failure instead of a crash. Five is few enough to write out; Volk,
the loader library in the SDK, does this for every function, and is worth
adopting if you go on to route C, which has many more.

```cpp
InitializationResult MeshScene::LoadFunctions()
{
    // Device-level functions of an enabled extension: looked up by name on the device.
    m_createAccelerationStructure = reinterpret_cast<PFN_vkCreateAccelerationStructureKHR>(
        vkGetDeviceProcAddr(m_vulkan.device, "vkCreateAccelerationStructureKHR"));
    m_destroyAccelerationStructure = reinterpret_cast<PFN_vkDestroyAccelerationStructureKHR>(
        vkGetDeviceProcAddr(m_vulkan.device, "vkDestroyAccelerationStructureKHR"));
    m_getBuildSizes = reinterpret_cast<PFN_vkGetAccelerationStructureBuildSizesKHR>(
        vkGetDeviceProcAddr(m_vulkan.device, "vkGetAccelerationStructureBuildSizesKHR"));
    m_cmdBuildAccelerationStructures = reinterpret_cast<PFN_vkCmdBuildAccelerationStructuresKHR>(
        vkGetDeviceProcAddr(m_vulkan.device, "vkCmdBuildAccelerationStructuresKHR"));
    m_getAccelerationStructureAddress = reinterpret_cast<PFN_vkGetAccelerationStructureDeviceAddressKHR>(
        vkGetDeviceProcAddr(m_vulkan.device, "vkGetAccelerationStructureDeviceAddressKHR"));

    if (m_createAccelerationStructure == nullptr || m_destroyAccelerationStructure == nullptr ||
        m_getBuildSizes == nullptr || m_cmdBuildAccelerationStructures == nullptr ||
        m_getAccelerationStructureAddress == nullptr)
    {
        return InitializationResult::failure("An acceleration structure entry point is missing.");
    }
    return InitializationResult::success();
}
```

### The meshes, in one vertex buffer and one index buffer

The scene is section 3's, as instances of two meshes. **This is the scene
table**, at file scope in `MeshScene.cpp`; its numbers are `Spheres.comp.glsl`'s:

```cpp
// File scope, above the namespace block. Section 3's scene as instances of two meshes:
// which mesh, where, and what it is made of. The numbers are Spheres.comp.glsl's.
struct SceneObject
{
    uint32_t  mesh;       // 0 = the sphere, 1 = the floor
    glm::vec3 position;
    glm::vec3 albedo;
    glm::vec3 emission;
};

static const SceneObject sceneObjects[] = {
    { 1, {  0.0f, 0.0f, 0.0f }, { 0.75f, 0.75f, 0.75f }, {  0.0f,  0.0f,  0.0f } },   // the floor
    { 0, { -2.1f, 1.0f, 0.0f }, { 0.75f, 0.15f, 0.15f }, {  0.0f,  0.0f,  0.0f } },   // red
    { 0, {  0.0f, 1.0f, 0.0f }, { 0.75f, 0.75f, 0.75f }, {  0.0f,  0.0f,  0.0f } },   // white
    { 0, {  2.1f, 1.0f, 0.0f }, { 0.15f, 0.75f, 0.15f }, {  0.0f,  0.0f,  0.0f } },   // green
    { 0, {  0.0f, 5.0f, 2.0f }, {  0.0f,  0.0f,  0.0f }, { 12.0f, 12.0f, 12.0f } },   // the light
};

// File scope, above the namespace block. A buffer's GPU address (Chapter 08 section 9).
static VkDeviceAddress bufferAddress(VkDevice device, VkBuffer buffer)
{
    const VkBufferDeviceAddressInfo addressInfo{
        .sType  = VK_STRUCTURE_TYPE_BUFFER_DEVICE_ADDRESS_INFO,
        .buffer = buffer,
    };
    return vkGetBufferDeviceAddress(device, &addressInfo);
}
```

The shader, given a hit, will need the triangle's vertex normals and the
instance's material. Two choices keep that simple. **Both meshes share one
vertex buffer and one index buffer**, Chapter 19 section 4's arrangement: each
mesh's indices still count from 0, and its `vertexOffset` says where its
vertices start, exactly as `vkCmdDrawIndexed` adds it. And **each instance gets
a `MeshInstance`** — its material and its mesh's place in those buffers — in a
third buffer indexed by the instance's position in the TLAS. **This is
`MeshInstance`**, added to `PathTraceTypes.h` after `PathTraceParameters`, with
its asserts beside the others:

```c
/* Route B (section 6): one instance in the top-level acceleration structure. std430,
   set 1 binding 3, indexed by the instance's position in the TLAS. */
struct MeshInstance
{
    vec4 albedo;         /*  0  rgb linear; a unused */
    vec4 emission;       /* 16  rgb linear; a unused */
    uint firstIndex;     /* 32  where this mesh's indices start in the shared index buffer */
    uint vertexOffset;   /* 36  added to each of its indices, as vkCmdDrawIndexed adds vertexOffset */
    uint padding0;       /* 40  keeps the size a multiple of 16 */
    uint padding1;       /* 44 */
};
```

```c
    static_assert(sizeof(MeshInstance) == 48, "MeshInstance layout drifted.");
    static_assert(offsetof(MeshInstance, firstIndex) == 32, "MeshInstance alignment drifted.");
```

With one buffer of each, the shader reaches every triangle through three plain
storage buffers. Had each mesh kept its own buffers, it would need a buffer per
mesh, and the way to reach those is Chapter 08 section 9's `buffer_reference`.

**This is `CreateGeometry`.** It generates the two meshes, appends them into the
shared arrays, fills in the instances, and uploads all three with Chapter 08's
`uploadToBuffer`. The vertex and index buffers carry four usages — read by the
builds, by address, by the shader, and written by a copy — and the instance
buffer two:

```cpp
InitializationResult MeshScene::CreateGeometry()
{
    // Chapter 11's meshes from a formula: a sphere of radius 1, fine enough that its
    // outline looks round, and a floor 1 km square. Both go into one vertex buffer and
    // one index buffer. Each mesh's indices still count from 0; its vertexOffset says
    // where its vertices start.
    const scene::MeshData meshData[] = {
        scene::makeUvSphere(1.0f, 64, 32),
        scene::makePlane(1000.0f, 1000.0f, 1),
    };
    std::vector<scene::Vertex> vertices;
    std::vector<uint32_t>      indices;
    for (size_t i = 0; i < m_meshes.size(); ++i)
    {
        m_meshes[i] = {
            .firstIndex   = static_cast<uint32_t>(indices.size()),
            .indexCount   = static_cast<uint32_t>(meshData[i].indices.size()),
            .vertexOffset = static_cast<uint32_t>(vertices.size()),
            .vertexCount  = static_cast<uint32_t>(meshData[i].vertices.size()),
        };
        vertices.insert(vertices.end(), meshData[i].vertices.begin(), meshData[i].vertices.end());
        indices.insert(indices.end(), meshData[i].indices.begin(), meshData[i].indices.end());
    }

    // What the shader needs to know about each instance: its material, and where its
    // mesh is in the shared buffers.
    std::vector<MeshInstance> instances;
    for (const SceneObject& object : sceneObjects)
    {
        const MeshRange& mesh = m_meshes[object.mesh];
        instances.push_back({
            .albedo       = glm::vec4(object.albedo, 0.0f),
            .emission     = glm::vec4(object.emission, 0.0f),
            .firstIndex   = mesh.firstIndex,
            .vertexOffset = mesh.vertexOffset,
        });
    }

    // The builds read the vertices and indices by device address; the shader reads all
    // three as storage buffers; a copy fills them.
    const VkBufferUsageFlags geometryUsage = VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_BUILD_INPUT_READ_ONLY_BIT_KHR
                                           | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT
                                           | VK_BUFFER_USAGE_STORAGE_BUFFER_BIT
                                           | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    const VkDeviceSize vertexBytes   = vertices.size() * sizeof(scene::Vertex);
    const VkDeviceSize indexBytes    = indices.size() * sizeof(uint32_t);
    const VkDeviceSize instanceBytes = instances.size() * sizeof(MeshInstance);
    m_vertexBuffer   = createBuffer(m_vulkan, vertexBytes, geometryUsage, false);
    m_indexBuffer    = createBuffer(m_vulkan, indexBytes, geometryUsage, false);
    m_instanceBuffer = createBuffer(m_vulkan, instanceBytes,
                                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, false);
    if (m_vertexBuffer.buffer == VK_NULL_HANDLE || m_indexBuffer.buffer == VK_NULL_HANDLE ||
        m_instanceBuffer.buffer == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the path tracer's mesh buffers failed.");
    }

    uploadToBuffer(m_vulkan, m_vertexBuffer, vertices.data(), vertexBytes);   // Chapter 08 section 2
    uploadToBuffer(m_vulkan, m_indexBuffer, indices.data(), indexBytes);
    uploadToBuffer(m_vulkan, m_instanceBuffer, instances.data(), instanceBytes);

    // uploadToBuffer leaves the barrier to its caller. One barrier after all three copies
    // covers them, because its first scope reaches back over everything submitted before
    // it on this queue. The builds read with SHADER_READ; so does the tracer.
    immediateSubmit(m_vulkan, [](VkCommandBuffer commandBuffer) {
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                      VK_ACCESS_2_SHADER_READ_BIT);
    });
    return InitializationResult::success();
}
```

The barrier's destination is the access the specification names for each
reader: an acceleration-structure build reads its vertex, index, and instance
inputs as `SHADER_READ` in the `ACCELERATION_STRUCTURE_BUILD` stage, and the
tracer reads the storage buffers in `COMPUTE_SHADER`.

### Building one, in six steps

A BLAS and a TLAS are built the same way; only step 1, the description, differs.
The steps:

1. **Describe the geometry**: a `VkAccelerationStructureGeometryKHR` — for a
   BLAS the triangles (where the positions are, their stride, the indices), for
   the TLAS the instances.
2. **Ask for sizes**: `vkGetAccelerationStructureBuildSizesKHR` says how much
   memory the structure needs, and how much **scratch** memory the build needs
   while it works.
3. **Allocate the structure's buffer**, with
   `ACCELERATION_STRUCTURE_STORAGE` usage.
4. **Create the structure** over that buffer — like an image view, it is a
   handle onto memory you own.
5. **Allocate the scratch buffer**, aligned as the device requires.
6. **Build**, on the GPU, with `vkCmdBuildAccelerationStructuresKHR`, then a
   barrier so later readers see the result.

**This is `Build`**, steps 2-6, shared by both levels. Two of its details are
where acceleration structures most often go wrong:

- **Scratch alignment.** The scratch address must be a multiple of
  `minAccelerationStructureScratchOffsetAlignment` — commonly 128 or 256 bytes
  on desktop GPUs — and an ordinary buffer's alignment does not
  promise that. Get it wrong and you get a lost device or a structure that rays
  pass through, with no useful message. `Build` allocates that much extra and
  rounds the address up.
- **The barrier after the build.** The TLAS build reads every BLAS, and the
  tracer's ray queries read the TLAS. Without
  `ACCELERATION_STRUCTURE_BUILD`/`WRITE` to `ACCELERATION_STRUCTURE_BUILD |
  COMPUTE_SHADER`/`ACCELERATION_STRUCTURE_READ` after each build, the next one
  may read a half-built tree.

```cpp
// File scope, above the namespace block. The build's scratch memory must start at a
// multiple of this, which a buffer's ordinary alignment does not promise.
static VkDeviceSize queryScratchAlignment(VkPhysicalDevice physicalDevice)
{
    VkPhysicalDeviceAccelerationStructurePropertiesKHR accelerationStructure{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ACCELERATION_STRUCTURE_PROPERTIES_KHR,
    };
    VkPhysicalDeviceProperties2 properties{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,
        .pNext = &accelerationStructure,
    };
    vkGetPhysicalDeviceProperties2(physicalDevice, &properties);
    return accelerationStructure.minAccelerationStructureScratchOffsetAlignment;
}
```

```cpp
InitializationResult MeshScene::Build(VkAccelerationStructureBuildGeometryInfoKHR& buildInfo,
                                      uint32_t primitiveCount, AccelerationStructure& result)
{
    // Step 2: how much memory the structure and its build need. The driver answers from
    // the description alone, before any memory exists.
    VkAccelerationStructureBuildSizesInfoKHR sizes{
        .sType = VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_SIZES_INFO_KHR,
    };
    m_getBuildSizes(m_vulkan.device, VK_ACCELERATION_STRUCTURE_BUILD_TYPE_DEVICE_KHR,
                    &buildInfo, &primitiveCount, &sizes);

    // Steps 3 and 4: a buffer to hold it, and the structure, created over that buffer.
    result.buffer = createBuffer(m_vulkan, sizes.accelerationStructureSize,
                                 VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_STORAGE_BIT_KHR
                                     | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
                                 false);
    if (result.buffer.buffer == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating an acceleration structure's buffer failed.");
    }
    const VkAccelerationStructureCreateInfoKHR createInfo{
        .sType  = VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_CREATE_INFO_KHR,
        .buffer = result.buffer.buffer,
        .size   = sizes.accelerationStructureSize,
        .type   = buildInfo.type,
    };
    if (m_createAccelerationStructure(m_vulkan.device, &createInfo, nullptr, &result.handle) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateAccelerationStructureKHR failed.");
    }

    // Step 5: scratch, working memory for the build alone. Its address must be a multiple
    // of m_scratchAlignment, so allocate that much extra and round the address up.
    AllocatedBuffer scratch = createBuffer(m_vulkan, sizes.buildScratchSize + m_scratchAlignment,
                                           VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
                                           false);
    if (scratch.buffer == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating an acceleration structure's scratch buffer failed.");
    }
    const VkDeviceAddress scratchAddress = bufferAddress(m_vulkan.device, scratch.buffer);
    buildInfo.dstAccelerationStructure  = result.handle;
    buildInfo.scratchData.deviceAddress = (scratchAddress + m_scratchAlignment - 1) / m_scratchAlignment
                                        * m_scratchAlignment;

    // Step 6: build it on the GPU, and wait.
    const VkAccelerationStructureBuildRangeInfoKHR  range{ .primitiveCount = primitiveCount };
    const VkAccelerationStructureBuildRangeInfoKHR* ranges = &range;   // one geometry, one range
    immediateSubmit(m_vulkan, [&](VkCommandBuffer commandBuffer) {
        m_cmdBuildAccelerationStructures(commandBuffer, 1, &buildInfo, &ranges);

        // The build's writes, before whatever reads the structure next: the TLAS build
        // reads each BLAS, and the tracer's ray queries read the TLAS.
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR,
                      VK_ACCESS_2_ACCELERATION_STRUCTURE_WRITE_BIT_KHR,
                      VK_PIPELINE_STAGE_2_ACCELERATION_STRUCTURE_BUILD_BIT_KHR | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                      VK_ACCESS_2_ACCELERATION_STRUCTURE_READ_BIT_KHR);
    });
    destroyBuffer(m_vulkan, scratch);   // immediateSubmit waited: the build is finished

    // What a TLAS instance stores to point at this structure.
    const VkAccelerationStructureDeviceAddressInfoKHR addressInfo{
        .sType                 = VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_DEVICE_ADDRESS_INFO_KHR,
        .accelerationStructure = result.handle,
    };
    result.address = m_getAccelerationStructureAddress(m_vulkan.device, &addressInfo);
    return InitializationResult::success();
}
```

**This is `BuildBottomLevel`**, step 1 for one mesh. The positions are the
first 12 bytes of each 48-byte `scene::Vertex`, so the description gives their
format and the vertex's full size as the stride, and the build skips the
normal, uv, and tangent between them. Both addresses start at the mesh's own
part of the shared buffers, which is what makes its 0-based indices find its
vertices:

```cpp
InitializationResult MeshScene::BuildBottomLevel(const MeshRange& mesh, AccelerationStructure& result)
{
    // Step 1: what to build from. A position is the first 12 bytes of each 48-byte
    // scene::Vertex, and the stride skips the rest. Both addresses start at this mesh's
    // part of the shared buffers, so its indices, counting from 0, find its vertices.
    const VkDeviceAddress vertexAddress = bufferAddress(m_vulkan.device, m_vertexBuffer.buffer)
                                        + mesh.vertexOffset * sizeof(scene::Vertex);
    const VkDeviceAddress indexAddress  = bufferAddress(m_vulkan.device, m_indexBuffer.buffer)
                                        + mesh.firstIndex * sizeof(uint32_t);
    const VkAccelerationStructureGeometryKHR geometry{
        .sType        = VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_KHR,
        .geometryType = VK_GEOMETRY_TYPE_TRIANGLES_KHR,
        .geometry     = { .triangles = {
            .sType        = VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_TRIANGLES_DATA_KHR,
            .vertexFormat = VK_FORMAT_R32G32B32_SFLOAT,
            .vertexData   = { .deviceAddress = vertexAddress },
            .vertexStride = sizeof(scene::Vertex),
            .maxVertex    = mesh.vertexCount - 1,
            .indexType    = VK_INDEX_TYPE_UINT32,
            .indexData    = { .deviceAddress = indexAddress },
        } },
        .flags        = VK_GEOMETRY_OPAQUE_BIT_KHR,   // nothing for an any-hit test to do: the fast path
    };
    VkAccelerationStructureBuildGeometryInfoKHR buildInfo{
        .sType         = VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_GEOMETRY_INFO_KHR,
        .type          = VK_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL_KHR,
        .flags         = VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR,   // built once, traced always
        .mode          = VK_BUILD_ACCELERATION_STRUCTURE_MODE_BUILD_KHR,
        .geometryCount = 1,
        .pGeometries   = &geometry,
    };
    return Build(buildInfo, mesh.indexCount / 3, result);   // steps 2-6; a primitive is a triangle
}
```

`PREFER_FAST_TRACE` asks the driver to spend longer building a better tree,
which is right for geometry built once and traced every frame; geometry rebuilt
every frame would ask for `PREFER_FAST_BUILD`, and getting the two backwards can
cost two or three times the tracing time.

**This is `BuildTopLevel`**, step 1 for the scene. Each instance is a
`VkAccelerationStructureInstanceKHR`: a BLAS's address and a transform, written
as three rows of four — the top three rows of a model matrix, rows not columns.
These objects only move, so the left 3 × 3 is the identity and the last column
is the position. The build reads the instances once, by address, so a buffer
the CPU fills is enough, and it is freed as soon as the build has run:

```cpp
InitializationResult MeshScene::BuildTopLevel()
{
    // Step 1, top level: one instance per scene object - a BLAS, and where to put it. The
    // transform is the top three rows of a model matrix, row by row; these objects only move.
    std::vector<VkAccelerationStructureInstanceKHR> instances;
    for (const SceneObject& object : sceneObjects)
    {
        instances.push_back({
            .transform = { .matrix = { { 1.0f, 0.0f, 0.0f, object.position.x },
                                       { 0.0f, 1.0f, 0.0f, object.position.y },
                                       { 0.0f, 0.0f, 1.0f, object.position.z } } },
            .instanceCustomIndex                    = 0,      // unused: the shader asks for the instance's place in this list
            .mask                                   = 0xFF,   // visible to every ray (rayQueryInitializeEXT's 0xFF)
            .instanceShaderBindingTableRecordOffset = 0,      // route C's; a ray query ignores it
            .flags                                  = 0,
            .accelerationStructureReference         = m_bottomLevels[object.mesh].address,
        });
    }

    // The build reads the instances once, by address, so a buffer the CPU writes is enough.
    const VkDeviceSize bytes = instances.size() * sizeof(VkAccelerationStructureInstanceKHR);
    AllocatedBuffer instanceBuffer = createBuffer(m_vulkan, bytes,
                                                  VK_BUFFER_USAGE_ACCELERATION_STRUCTURE_BUILD_INPUT_READ_ONLY_BIT_KHR
                                                      | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT,
                                                  true);
    if (instanceBuffer.buffer == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the TLAS instance buffer failed.");
    }
    std::memcpy(instanceBuffer.mapped, instances.data(), static_cast<size_t>(bytes));
    vmaFlushAllocation(m_vulkan.allocator, instanceBuffer.allocation, 0, VK_WHOLE_SIZE);   // no-op when coherent

    const VkAccelerationStructureGeometryKHR geometry{
        .sType        = VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_KHR,
        .geometryType = VK_GEOMETRY_TYPE_INSTANCES_KHR,
        .geometry     = { .instances = {
            .sType           = VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_GEOMETRY_INSTANCES_DATA_KHR,
            .arrayOfPointers = VK_FALSE,   // the instances themselves, side by side
            .data            = { .deviceAddress = bufferAddress(m_vulkan.device, instanceBuffer.buffer) },
        } },
        .flags        = VK_GEOMETRY_OPAQUE_BIT_KHR,
    };
    VkAccelerationStructureBuildGeometryInfoKHR buildInfo{
        .sType         = VK_STRUCTURE_TYPE_ACCELERATION_STRUCTURE_BUILD_GEOMETRY_INFO_KHR,
        .type          = VK_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL_KHR,
        .flags         = VK_BUILD_ACCELERATION_STRUCTURE_PREFER_FAST_TRACE_BIT_KHR,
        .mode          = VK_BUILD_ACCELERATION_STRUCTURE_MODE_BUILD_KHR,
        .geometryCount = 1,
        .pGeometries   = &geometry,
    };
    const InitializationResult result = Build(buildInfo, static_cast<uint32_t>(instances.size()), m_topLevel);
    destroyBuffer(m_vulkan, instanceBuffer);   // Build waited: the TLAS holds its own copy now
    return result;
}
```

The instance struct uses C bit-fields — `instanceCustomIndex` and `mask` share
one 32-bit word, 24 bits and 8 — which is why every field is named rather than
listed.

### Set 1

**This is `CreateDescriptors`**: set 1, as `Meshes.comp.glsl` declares it —
the TLAS and three storage buffers, all for the compute stage:

| Binding | Type | Holds |
| --- | --- | --- |
| 0 `topLevel` | `ACCELERATION_STRUCTURE_KHR` | the TLAS |
| 1 `vertexData` | `STORAGE_BUFFER` | `m_vertexBuffer` |
| 2 `indices` | `STORAGE_BUFFER` | `m_indexBuffer` |
| 3 `instances` | `STORAGE_BUFFER` | `m_instanceBuffer` |

The layout, the pool, and the allocation are Chapter 20's pattern, written out in
full in the appendix. Two things are new. Set 1 gets **its own pool**, because
an acceleration-structure descriptor is only valid on a device with the
extension, and route A's pool must not mention it. And an acceleration structure
has no image or buffer info to point at, so it is written through a struct of
its own, chained into the write's `pNext`:

```cpp
    // An acceleration structure has no image or buffer info of its own: it is written
    // through this struct, chained into the write's pNext.
    const VkWriteDescriptorSetAccelerationStructureKHR topLevel{
        .sType                      = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET_ACCELERATION_STRUCTURE_KHR,
        .accelerationStructureCount = 1,
        .pAccelerationStructures    = &m_topLevel.handle,
    };
```

```cpp
        { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
          .pNext           = &topLevel,
          .dstSet          = m_set,
          .dstBinding      = 0,
          .descriptorCount = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR },
```

`Bind` puts the set at number 1, and `Destroy` releases everything in reverse
and resets the object, so the next `Setup` can `Create` it again; both are in
the appendix too. A `MeshScene` that was never created holds no device, and
`Destroy` returns at once, which is what lets the demo call it unconditionally.

### In the shader

**This is `Shaders/PathTrace/Meshes.comp.glsl`.** It includes the same tracer
and defines `intersectScene` with a ray query. `GL_EXT_ray_query` is rejected
under `#version 450`, so this file is `#version 460`; nothing in
`PathTrace.glsl` minds.

A ray query is a small loop. `rayQueryInitializeEXT` starts a search of the
TLAS along the ray, between a nearest and a furthest distance. Each call to
`rayQueryProceedEXT` advances the search and stops to ask the shader about any
candidate it cannot decide alone — a triangle that might be transparent, for
example. Every triangle here is opaque, so the loop body is empty and the
hardware decides everything, which is the fast path. When it finishes, the
query holds the **committed** hit, the nearest one (the `true` argument in each
`rayQueryGet...` call asks about it). The shader learns which instance, which
triangle of its mesh, the distance, and the hit's **barycentrics**: two numbers
`(u, v)` that say where on the triangle it is, as weights of its three corners,
`(1 − u − v, u, v)`. The normal at the hit is the corners' normals blended by
those weights — the same blend the rasterizer gave every varying in Chapter 11.

```glsl
// Shaders/PathTrace/Meshes.comp.glsl - route B: the same scene as triangle meshes, found by a ray query.
#version 460                                   // 450 will not accept GL_EXT_ray_query
#extension GL_GOOGLE_include_directive : require
#extension GL_EXT_ray_query            : require
#include "PathTrace.glsl"   // the tracer: everything except the scene

// Set 1: the top-level acceleration structure, and what it takes to shade a hit.
layout(set = 1, binding = 0) uniform accelerationStructureEXT topLevel;
layout(set = 1, binding = 1, std430) readonly buffer VertexBuffer   { float vertexData[]; };   // scene::Vertex, 12 floats each
layout(set = 1, binding = 2, std430) readonly buffer IndexBuffer    { uint indices[]; };
layout(set = 1, binding = 3, std430) readonly buffer InstanceBuffer { MeshInstance instances[]; };

// scene::Vertex is 48 bytes: position, normal, uv, tangent. Read as floats, its normal is
// floats 3 to 5 of the 12.
vec3 vertexNormal(uint vertex)
{
    uint first = vertex * 12u + 3u;
    return vec3(vertexData[first], vertexData[first + 1u], vertexData[first + 2u]);
}

Hit intersectScene(vec3 origin, vec3 direction)
{
    // The nearest opaque triangle between 0 and 10 km along the ray.
    rayQueryEXT rayQuery;
    rayQueryInitializeEXT(rayQuery, topLevel, gl_RayFlagsOpaqueEXT, 0xFFu,
                          origin, 0.0, direction, 10000.0);
    while (rayQueryProceedEXT(rayQuery)) { }   // empty: opaque triangles only, so the hardware decides

    Hit hit;
    hit.valid = rayQueryGetIntersectionTypeEXT(rayQuery, true) == gl_RayQueryCommittedIntersectionTriangleEXT;
    if (!hit.valid) { return hit; }

    // Which instance, which of its triangles, and where on the triangle.
    MeshInstance instance    = instances[rayQueryGetIntersectionInstanceIdEXT(rayQuery, true)];
    uint         triangle    = uint(rayQueryGetIntersectionPrimitiveIndexEXT(rayQuery, true));
    vec2         barycentric = rayQueryGetIntersectionBarycentricsEXT(rayQuery, true);

    // The triangle's three vertices, found the way vkCmdDrawIndexed finds them.
    uint first = instance.firstIndex + triangle * 3u;
    vec3 n0 = vertexNormal(indices[first]      + instance.vertexOffset);
    vec3 n1 = vertexNormal(indices[first + 1u] + instance.vertexOffset);
    vec3 n2 = vertexNormal(indices[first + 2u] + instance.vertexOffset);

    // Blended by the barycentrics: (1 - u - v) of vertex 0, u of vertex 1, v of vertex 2.
    vec3 localNormal = n0 * (1.0 - barycentric.x - barycentric.y) + n1 * barycentric.x + n2 * barycentric.y;

    // Into world space with the normal matrix, transpose(inverse(model)) (Chapter 11 section 13).
    // The query hands back inverse(model) as worldToObject, and a vector on the left of a
    // matrix multiplies by its transpose.
    mat3 worldToObject = mat3(rayQueryGetIntersectionWorldToObjectEXT(rayQuery, true));
    hit.normal = normalize(localNormal * worldToObject);

    hit.distance = rayQueryGetIntersectionTEXT(rayQuery, true);
    hit.position = origin + direction * hit.distance;
    hit.material = Material(instance.albedo.rgb, instance.emission.rgb);
    return hit;
}
```

Three things here are easy to get wrong:

- **The vertex buffer is read as floats.** In a std430 block a `vec3` is aligned
  to 16 bytes, so a GLSL struct of `vec3 position; vec3 normal; ...` would put
  the normal at byte 16, not the 12 where C++ wrote it (Chapter 08 section 8's
  trap). Twelve floats per vertex, read by index, cannot drift.
- **The normal needs the normal matrix**, for the reason Chapter 11 section 13
  gave: under a non-uniform scale, the model matrix tilts normals the wrong way.
  The query hands back `inverse(model)`, and `localNormal * worldToObject`, with
  the vector on the left, multiplies by its transpose (Chapter 14 section 3's
  row vectors), which is the normal matrix with no `transpose` call. These
  instances only move, so here it changes nothing, but the line is right for any
  instance you add.
- **The instance is found by its place in the TLAS's list**
  (`rayQueryGetIntersectionInstanceIdEXT`), which is also its place in the
  `MeshInstance` buffer, because both were filled from `sceneObjects` in order.

The tessellated spheres are the only real difference from route A. Their hit
points lie on flat facets slightly inside the true sphere, and their normals are
blended, so the outline is very slightly polygonal up close. At 64 segments and
32 rings that is invisible from the default camera.

### Wiring it into the demo

Five additions to `PathTracerDemo`, none of which changes a line of route A.
The header includes `MeshScene.h` and gains the member, after the pipelines:

```cpp
#include "PillowFort/Demos/PathTracer/MeshScene.h"
```

```cpp
    // Section 6: route B's meshes and acceleration structures.
    MeshScene m_meshScene;
```

`Setup` creates it between the descriptors and the pipelines, because the
pipeline layout needs its set layout:

```cpp
    // Section 6: route B, when the GPU has ray queries. Before the pipelines, whose
    // layout needs its set layout.
    if (m_vulkan.rayQuery)
    {
        if (auto result = m_meshScene.Create(m_vulkan); !result) { return result; }
    }
```

`CreatePipelines` adds set 1 to the layout, after the `setLayouts` vector is
made, and route B's pipeline before its `return`:

```cpp
    if (m_meshScene.SetLayout() != VK_NULL_HANDLE)
    {
        setLayouts.push_back(m_meshScene.SetLayout());
    }
```

```cpp
    // Section 6: route B's pipeline, only where its shader can run.
    if (m_meshScene.SetLayout() != VK_NULL_HANDLE)
    {
        m_meshesPipeline = createComputePipeline(m_vulkan.device, m_pipelineCache,
                                                 "PathTrace/Meshes.comp.spv", m_pipelineLayout);
        if (m_meshesPipeline == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating the path tracer's route B pipeline failed.");
        }
    }
```

One pipeline layout serves both pipelines. Route A's shader declares only set
0, which a layout with two sets still matches; route A's dispatch binds only set
0, which is all its pipeline uses. `Record` binds set 1 for route B, right after
set 0:

```cpp
    if (meshes)
    {
        m_meshScene.Bind(commandBuffer, m_pipelineLayout);   // section 6: set 1
    }
```

And `Teardown` destroys it after the pipeline layout:

```cpp
    m_meshScene.Destroy();                                                 // section 6
```

Now `m_meshesPipeline` exists, the panel shows the **Route** combo, and
choosing B restarts the sum and traces the meshes.

### Beyond two meshes

The same structure traces a whole USD scene from Chapter 14. Each `GpuMesh`
becomes a BLAS — its buffers need this section's usage flags, which is the
reason Chapter 11 section 6 said a later chapter would add usage bits — each
draw item becomes a TLAS instance with its world matrix's top three rows, and
the `MeshInstance` buffer carries each item's material. With many meshes in
separate buffers, the instance holds their device addresses and the shader
reads them through `buffer_reference` (Chapter 08 section 9) instead of the
three shared buffers here. Materials with textures need texture coordinates
fetched the way the normal is, and Chapter 15's whole material model — at which
point the BRDF is no longer Lambert's, and section 8's first row applies.

## Checkpoint

Rerun `GenerateProjects.bat` (`MeshScene.cpp` and `Meshes.comp.glsl` are new),
build, and run with `--demo Path`. On a GPU with ray queries the log says they
are enabled, and the panel gains the "Route" combo. Pick "B: triangles, by ray
query": the sum restarts and settles to route A's picture, sphere for sphere and
shadow for shadow. Up close, the spheres' outlines are faintly polygonal, the
facets of Chapter 11's sphere.

---

## 7. Route C, and why to skip it

Ray tracing pipelines replace the compute shader with five kinds of shader —
ray generation, miss, closest-hit, any-hit, and intersection — launched by
`vkCmdTraceRaysKHR`, and the hardware calls the right hit shader for whatever
each ray hits. Their real advantage is scheduling: with many materials, rays
that hit the same material are shaded together, which a single compute shader
cannot arrange.

The cost is the **shader binding table**: a buffer of shader-group handles whose
layout follows three alignment values from
`VkPhysicalDeviceRayTracingPipelinePropertiesKHR` — the size of a handle, the
stride between handles, and the alignment of each region's start. Get any of
them wrong and the wrong shader runs, or none, often with no validation message.
It is the least forgiving object in the API.

Route B gives you the same hardware traversal with none of that. Come back to
route C when a scene has many materials with very different shading, and then
consider Volk for its long list of entry points.

---

## 8. Making it fast

Once it is right, in rough order of payoff:

| Change | Effect |
| --- | --- |
| Next event estimation: at each bounce, also send a ray straight at a light | Enormous for small, bright lights like this one, which random bounces rarely find — most of the floor's noise |
| Low-discrepancy samples (Sobol, blue noise) instead of a hash | The same quality in noticeably fewer samples |
| Render at lower resolution while the camera moves | Interactive while moving, unchanged once still |
| A glossy BRDF, such as Chapter 15's GGX, sampled by its own pdf | Not speed but the next feature: every BRDF that is not Lambert's needs its own way of picking directions and its own pdf to divide by, exactly as section 4 did for the cosine |
| Wavefront path tracing: one dispatch per bounce, live paths compacted | A big win at high bounce counts; a large restructuring |
| `subgroupAny` to leave loops early (Chapter 20 section 7) | Cheap; helps when whole subgroups finish together |

The path tracer does not read Chapter 15's BRDF switch in `FrameData`, for the
reason in the fourth row: it has no `FrameData`, and its surfaces are matte by
construction, because its directions are picked for Lambert's BRDF and no other.

Do not start with any of these. A correct path tracer that takes a minute to
converge is worth more than a fast wrong one, and route A's converged picture is
how you will check every optimization afterwards.

---

## 9. Debugging

**Watch the counter.** The panel shows samples per pixel. If the picture stops
improving while the count climbs, the random numbers repeat (section 2). If it
never improves, the sum is restarting every frame — something in `Update`
reports a change every frame — or the barrier between frames is missing.

**Clamp fireflies while debugging.** A single sample of a million, from a bad
pdf or a division by nearly zero, dominates a pixel's average for thousands of
frames and looks like broken accumulation. Clamping each sample's light hides
it, and is biased, so make it a checkbox, never a fix.

**Print from the shader.** `debugPrintfEXT` works in compute shaders. Turn on
the layer's Debug Printf for one run by setting two environment variables for
that process: `VK_LAYER_PRINTF_ENABLE=1`, and `VK_LAYER_PRINTF_TO_STDOUT=1`,
which sends the output to the console. Without the second it arrives as an
Information-level validation message, which Chapter 02's callback, set for
warnings and errors, never shows. `vkconfig` can switch both on for a session
instead, as Chapter 01 section 5 describes — leave synchronization validation
out of the override, and clear the override when you are done. Then add
`#extension GL_EXT_debug_printf : require` before the first `#include` of
`PathTrace.glsl`, so both routes have it, and print from `tracePath`, after the
miss check:

```glsl
        // The first surface the centre pixel's paths hit.
        if (gl_GlobalInvocationID.xy == uvec2(640, 360) && bounce == 0u)
        {
            debugPrintfEXT("t=%f  normal=(%f,%f,%f)\n", hit.distance, hit.normal.x, hit.normal.y, hit.normal.z);
        }
```

With the default camera at 1280 × 720 this prints lines like
`t=7.000036  normal=(-0.004868,0.133022,-0.991101)`: the white sphere, 7 m
away, as section 3's worked example said. Gate on one pixel, or a single frame
prints a million lines. This is the one way to read intermediate values inside
a path, and it turns a whole class of guessing into reading.

**Show what a path sees.** Section 3's checkpoint was the first of these. Write
the first hit's normal (`normal * 0.5 + 0.5`), its albedo, its distance, or the
number of bounces a path took, instead of the light, behind a combo box. Almost
every "the picture is wrong" question is answered at once by one of them.

---

## If something goes wrong

| What you see | Likely cause |
| --- | --- |
| The image never gets cleaner | `frameSeed` is not changing, or the seed ignores it: every frame repeats the same paths (section 2) |
| It gets cleaner, then stops improving | The accumulation image is not 32-bit float (section 1) |
| The picture restarts every frame | Something in `Update` returns "changed" every frame; or `Resize` is being called every frame |
| Noise that holds still on screen while you orbit | Seeded from `accumulatedFrames`, which restarts with the camera, instead of `frameSeed` |
| Plausible but too dark | An extra `cos θ` in `tracePath`: the pdf already cancelled it (section 4) |
| Dark, grainy speckle everywhere | No origin offset, or too small for the scene's scale: shadow acne (section 4) |
| Upside down | The projection's Y flip is missing, or something flips a second time (section 3) |
| A pixel goes black or white and never recovers | A NaN or infinity reached the sum: a zero-length vector normalized, or a division by a zero pdf |
| Bright specks that take ages to fade | Expected without next event estimation: paths that happen to hit the small light (section 8) |
| Red and green on the wrong sides | They are not: the camera looks down +Z, so +X is on the left (the note under the constructor, in "What you are actually writing") |
| Route B: everything is missed, or it hangs | The scratch address is not aligned, or a barrier between builds is missing (section 6) |
| Route B: no Route combo | The GPU lacks ray queries; the log says `Ray queries: not on this GPU.` |
| Route B: lighting is subtly wrong on the spheres | Reading the vertex as GLSL `vec3`s in std430 puts the normal at the wrong offset (section 6) |

Color bleeding — red and green light on the white sphere and on the floor
between them — is the strongest single sign that the light transport is right.
Nothing in the shader mentions it; it appears because paths bounce.

---

## Exit check

- [ ] The demo appears as "Path Tracer" in the "Demos" window and starts with
      `--demo Path`. The log says whether ray queries are enabled.
- [ ] The panel's "Samples per pixel" climbs by one per frame. At 1 sample the
      floor is a field of specks; by about 250 the shadows under the spheres are
      soft, with only fine grain; by 1000 the picture no longer visibly changes.
- [ ] At 1000 samples, the white sphere's side facing the green sphere is
      visibly greener than its side facing the red one, and the floor between
      each pair is tinted the same way: light that bounced off a colored sphere.
- [ ] Dragging the "Exposure (stops)" slider brightens and darkens the picture,
      and "Samples per pixel" keeps climbing without a pause.
- [ ] Dragging in the window to orbit sends "Samples per pixel" back to 1 and
      the picture back to noise; it settles again once you stop.
- [ ] "Max bounces" at 1 gives only light seen directly — the light sphere, the
      sky, and black surfaces; at 2 the surfaces lit directly by the light
      appear; raising it further brightens the shadows a little at a time and
      then stops changing.
- [ ] Resizing the window restarts the sum, with no validation messages.
- [ ] **Positive control:** delete the `computeToComputeBarrier` call in
      `Record` and run with synchronization validation on. Within a few frames
      the layer reports `SYNC-HAZARD-WRITE-AFTER-WRITE` from `vkQueueSubmit2`,
      for "descriptor binding 0 ... from descriptor set 0": the accumulation
      image, written by this frame's dispatch and by last frame's, in two
      submissions with nothing between them. Put the call back.
- [ ] If you did route B: choosing "B: triangles, by ray query" restarts the sum
      and converges to the same picture as route A, sphere for sphere and
      shadow for shadow.
- [ ] No validation messages at any point, with synchronization validation on.

---

## Sources

- James T. Kajiya, "The Rendering Equation", SIGGRAPH 1986 — the equation in
  section 0, and the path tracing algorithm.
- Matt Pharr, Wenzel Jakob, and Greg Humphreys, *Physically Based Rendering*,
  4th edition (pbr-book.org) — Monte Carlo integration, importance sampling,
  Russian roulette, and cosine-weighted hemisphere sampling.
- Peter Shirley, *Ray Tracing in One Weekend* series — the unit-sphere
  construction of cosine-weighted directions used in section 4.
- The Vulkan specification, `VK_KHR_acceleration_structure` and
  `VK_KHR_ray_query`, and the GLSL extension `GL_EXT_ray_query` — the build
  steps, the access types for build inputs, and the query functions in section 6.

---

## Appendix — `MeshScene`'s set 1, `Bind`, and `Destroy`

Reference: section 6's last three functions in full, in `MeshScene.cpp` after
`Build`.

```cpp
InitializationResult MeshScene::CreateDescriptors()
{
    // Set 1, exactly as Meshes.comp.glsl declares it.
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding         = 0,   // topLevel
          .descriptorType  = VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding         = 1,   // vertexData
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding         = 2,   // indices
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding         = 3,   // instances
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT },
    };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 4,
        .pBindings    = bindings,
    };
    if (vkCreateDescriptorSetLayout(m_vulkan.device, &setLayoutInfo, nullptr, &m_setLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the mesh scene.");
    }

    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR, 1 },
        { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,             3 },
    };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 1,
        .poolSizeCount = 2,
        .pPoolSizes    = poolSizes,
    };
    if (vkCreateDescriptorPool(m_vulkan.device, &poolInfo, nullptr, &m_descriptorPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the mesh scene.");
    }
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_descriptorPool,
        .descriptorSetCount = 1,
        .pSetLayouts        = &m_setLayout,
    };
    if (vkAllocateDescriptorSets(m_vulkan.device, &allocateInfo, &m_set) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the mesh scene.");
    }

    // An acceleration structure has no image or buffer info of its own: it is written
    // through this struct, chained into the write's pNext.
    const VkWriteDescriptorSetAccelerationStructureKHR topLevel{
        .sType                      = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET_ACCELERATION_STRUCTURE_KHR,
        .accelerationStructureCount = 1,
        .pAccelerationStructures    = &m_topLevel.handle,
    };
    const VkDescriptorBufferInfo vertices{ .buffer = m_vertexBuffer.buffer, .offset = 0, .range = VK_WHOLE_SIZE };
    const VkDescriptorBufferInfo indices{ .buffer = m_indexBuffer.buffer, .offset = 0, .range = VK_WHOLE_SIZE };
    const VkDescriptorBufferInfo instances{ .buffer = m_instanceBuffer.buffer, .offset = 0, .range = VK_WHOLE_SIZE };
    const VkWriteDescriptorSet writes[] = {
        { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
          .pNext           = &topLevel,
          .dstSet          = m_set,
          .dstBinding      = 0,
          .descriptorCount = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR },
        { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
          .dstSet          = m_set,
          .dstBinding      = 1,
          .descriptorCount = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
          .pBufferInfo     = &vertices },
        { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
          .dstSet          = m_set,
          .dstBinding      = 2,
          .descriptorCount = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
          .pBufferInfo     = &indices },
        { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
          .dstSet          = m_set,
          .dstBinding      = 3,
          .descriptorCount = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
          .pBufferInfo     = &instances },
    };
    vkUpdateDescriptorSets(m_vulkan.device, 4, writes, 0, nullptr);
    return InitializationResult::success();
}
```

```cpp
void MeshScene::Bind(VkCommandBuffer commandBuffer, VkPipelineLayout layout) const
{
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 1, 1, &m_set, 0, nullptr);
}

void MeshScene::Destroy()
{
    if (m_vulkan.device == VK_NULL_HANDLE) { return; }   // never created: nothing to release

    // The caller waited for the device. Reverse order of Create.
    vkDestroyDescriptorPool(m_vulkan.device, m_descriptorPool, nullptr);   // frees the set
    vkDestroyDescriptorSetLayout(m_vulkan.device, m_setLayout, nullptr);
    if (m_destroyAccelerationStructure != nullptr)
    {
        m_destroyAccelerationStructure(m_vulkan.device, m_topLevel.handle, nullptr);   // null: no-op
        for (AccelerationStructure& bottom : m_bottomLevels)
        {
            m_destroyAccelerationStructure(m_vulkan.device, bottom.handle, nullptr);
        }
    }
    destroyBuffer(m_vulkan, m_topLevel.buffer);   // after the structure that lives in it
    for (AccelerationStructure& bottom : m_bottomLevels)
    {
        destroyBuffer(m_vulkan, bottom.buffer);
    }
    destroyBuffer(m_vulkan, m_instanceBuffer);
    destroyBuffer(m_vulkan, m_indexBuffer);
    destroyBuffer(m_vulkan, m_vertexBuffer);

    *this = MeshScene{};   // back to "never created", so Create can run again
}
```

Next: the index's closing page, [The engine you built](../VulkanTutorial.md#appendix-the-engine-you-built); then [34 — Debugging and Profiling](34-Debugging.md), a toolbox to keep at hand.
