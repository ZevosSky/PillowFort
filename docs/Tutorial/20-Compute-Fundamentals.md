# 20 — Compute Fundamentals

**Goal:** run GPU work that is not drawing: compute pipelines, workgroups, storage
images and buffers, shared memory, subgroups, atomics, and the barriers between
dispatches. The exercise is Conway's Game of Life, simulated, counted, and drawn
entirely by compute shaders.

**ROADMAP:** step 21+ — a demo, in `Source/PillowFort/Demos/Life/` with shaders
under `Shaders/Life/`, registered in `SandboxGame` like every demo since Chapter 09.

**Module:** the demo is `pf::demos::life`. Six small free functions join
`VulkanGraphics` (`pf::vulkan_graphics`) in three existing files, and they are
what every later compute chapter uses: `memoryBarrier` and `computeToComputeBarrier`
(`VulkanBarriers`), `createComputePipeline` and `groupCount` (`GraphicsPipeline`),
and `createReadbackBuffer` and `readBuffer` (`VulkanResources`). One include,
`Shaders/Include/Random.glsl`, is shared with later chapters.

**Prerequisites:**

- Chapter 02 section 2 — the two validation-layer settings, and its "One blind
  spot" paragraph: section 5 proves the second setting is live.
- Chapter 04 section 5 — the three questions, `transitionImage`, and the barrier
  cookbook. Every barrier in this chapter is answered the same way, and the
  "Compute" table in Chapter 04's appendix, "Barriers the later chapters add",
  collects this chapter's rows in one place.
- Chapter 06 sections 1, 3, and 8 — the shader glob already compiles
  `.comp.glsl` files, `readSpirv` and `createShaderModule` load them, and
  `GraphicsPipeline.cpp` is where the compute pipeline's function goes.
- Chapter 07 section 9 — a demo's panel is a free function beside its data.
- Chapter 08 sections 3 and 4 (the scene target has `STORAGE_BIT`, and the
  contract for handing it back), 6 (descriptor sets), 7 (VMA's `createBuffer`),
  and 8 (C++/GLSL twins, std430).
- Chapter 09 — the `Demo` interface, `DemoContext`, `RecordContext`,
  `Resize`, and `handBackSceneTarget`.

Chapters 10-19 are not needed: Life has no camera, no meshes, and no depth. The
ocean (29) needs this chapter on top of 01-10, with Chapter 18 section 6 and
Chapter 21 section 3's random numbers. The path tracer (33) builds on this
chapter, Chapter 10's camera, Chapter 16 section 6, and Chapter 21 section 3.

---

## Why compute, and why Life

Everything so far has run in a graphics pipeline. You drew vertices, the vertex
shader ran once for each, the rasterizer decided which pixels they covered, and
the fragment shader ran once per covered pixel. You chose how many vertices to
draw, and the rasterizer chose everything else.

Compute keeps only the shader. You say how many invocations you want, arranged in
a grid you choose, and each one gets its position in that grid and access to
memory. Nothing is rasterized, nothing is blended, and there is no attachment to
write to. Anything that reads "for every element, compute something" fits: a
simulation step, an FFT, culling a list of objects, updating particles, tracing
a ray per pixel.

The exercise is Conway's Life on a 300 x 170 grid that wraps at its edges. A
cell with exactly three live neighbours comes alive, and a live cell with two or
three stays alive. Life was chosen because it is the smallest program that needs
every idea in this chapter:

- **It is exact.** The rules are integers, so a bug is not "slightly off". A
  single glider on an empty grid must keep its population at exactly 5 forever,
  and that is a check you can read back from the GPU.
- **It ping-pongs.** Each generation reads one image and writes another, so it has
  the ocean's FFT structure (29) and the path tracer's frame-to-frame reuse (33).
- **It reads neighbours.** Each cell reads eight others, which is the textbook
  case for shared memory.
- **It counts.** Population, births, and deaths need atomics. Particles (21) and
  grass (25-27) need the same machinery: counters, a reset, and reading them back
  without stalling.
- **It is visible without a graphics pipeline.** A compute pass writes the scene
  image directly, the way the path tracer does.

Compute feeding the vertex stage is covered in text in section 10, and Chapter
21 does it for real.

### What you are actually writing

The demo is one class. Here is its header, which is also the map of the
chapter: every private function names the section that writes it.

```cpp
// Source/PillowFort/Demos/Life/LifeDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"
#include "Life/LifeTypes.h"

#include <vma/vk_mem_alloc.h>

#include <array>
#include <cstdint>

namespace pf::demos::life {

// What the panel edits (section 11). CPU state: it survives Teardown and Setup.
struct LifeSettings
{
    int   stepsPerFrame = 1;       // generations per frame
    bool  paused        = false;
    int   pattern       = 0;       // 0 = random soup, 1 = a single glider
    float density       = 0.3f;    // random soup: the chance that a cell starts alive
    bool  reseed        = true;    // set by the panel, consumed by Record
};

class LifeDemo : public Demo
{
public:
    const char*          Name() const override { return "Life (compute)"; }
    InitializationResult Setup(const DemoContext& context) override;                    // sections 2-9
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override; // section 10
    void                 Update(const FrameInput& input) override;                      // section 11
    void                 Record(const RecordContext& frame) override;                   // section 11
    void                 Teardown() override;                                           // section 12

private:
    InitializationResult CreateCellImages();     // section 4
    InitializationResult CreateBuffers();        // sections 8 and 9
    InitializationResult CreateDescriptors();    // section 4
    InitializationResult CreatePipelines();      // section 2
    void RecordSeed(VkCommandBuffer commandBuffer);                          // section 3
    void RecordStep(VkCommandBuffer commandBuffer, bool countStatistics);    // sections 5-8
    void RecordClearStatistics(VkCommandBuffer commandBuffer);               // section 8
    void RecordReadback(VkCommandBuffer commandBuffer, uint32_t frameIndex); // section 9
    void ReadStatistics(uint32_t frameIndex);                                // section 9
    void RecordDisplay(VkCommandBuffer commandBuffer, const vulkan_graphics::SceneTargets& targets);   // section 10

    // Deliberately not multiples of the 8 x 8 workgroup, so the bounds checks and
    // the wrap-around are exercised on every edge.
    static constexpr uint32_t GRID_WIDTH  = 300;
    static constexpr uint32_t GRID_HEIGHT = 170;
    static constexpr uint32_t GROUP_SIZE  = 8;   // local_size_x and local_size_y in all three shaders

    vulkan_graphics::VulkanContext m_vulkan;                       // Chapter 09's DemoContext, copied
    VkPipelineCache                m_pipelineCache = VK_NULL_HANDLE;

    // Section 4: two cell images, ping-pong. m_current holds the latest generation.
    std::array<VkImage, 2>         m_cellImages{};
    std::array<VmaAllocation, 2>   m_cellAllocations{};
    std::array<VkImageView, 2>     m_cellViews{};
    uint32_t                       m_current = 0;

    // Section 4: m_sets[i] reads image i and writes image 1 - i.
    VkDescriptorSetLayout          m_setLayout      = VK_NULL_HANDLE;
    VkDescriptorPool               m_descriptorPool = VK_NULL_HANDLE;
    std::array<VkDescriptorSet, 2> m_sets{};

    // Section 2.
    VkPipelineLayout               m_pipelineLayout  = VK_NULL_HANDLE;
    VkPipeline                     m_seedPipeline    = VK_NULL_HANDLE;
    VkPipeline                     m_stepPipeline    = VK_NULL_HANDLE;
    VkPipeline                     m_displayPipeline = VK_NULL_HANDLE;

    // Sections 8 and 9.
    vulkan_graphics::AllocatedBuffer m_statistics;
    std::array<vulkan_graphics::AllocatedBuffer, vulkan_graphics::FRAMES_IN_FLIGHT> m_readback;
    std::array<bool, vulkan_graphics::FRAMES_IN_FLIGHT>                              m_readbackPending{};

    // CPU state.
    LifeSettings   m_settings;
    LifeStatistics m_latest{};        // the newest statistics read back
    uint64_t       m_generation = 0;  // steps recorded since the last seed
    uint32_t       m_seed       = 1;  // feeds the random soup; a new one per reseed
};

} // namespace pf::demos::life
```

The settings live in the demo object, not in anything `Setup` creates, so that
switching to another demo and back keeps them (Chapter 09's rule).
`"Life/LifeTypes.h"` resolves through the `Shaders` include directory Chapter 09
added. It holds the structs C++ and GLSL share, and section 3 writes it.

**This is `Setup`.** It reads as a list of steps, in dependency order. Section 7
explains the subgroup check at the top.

```cpp
InitializationResult LifeDemo::Setup(const DemoContext& context)
{
    m_vulkan        = context.vulkan;
    m_pipelineCache = context.pipelineCache;

    const VkPhysicalDeviceSubgroupProperties subgroup = querySubgroupProperties(m_vulkan.physicalDevice);
    if ((subgroup.supportedStages & VK_SHADER_STAGE_COMPUTE_BIT) == 0 ||
        (subgroup.supportedOperations & VK_SUBGROUP_FEATURE_ARITHMETIC_BIT) == 0)
    {
        return InitializationResult::failure("Life needs subgroup arithmetic in compute shaders.");
    }
    Log::info(std::format("Life: subgroup size {}", subgroup.subgroupSize).c_str());

    if (auto result = CreateCellImages(); !result)  { return result; }   // section 4
    if (auto result = CreateBuffers(); !result)     { return result; }   // sections 8 and 9
    if (auto result = CreateDescriptors(); !result) { return result; }   // section 4
    if (auto result = CreatePipelines(); !result)   { return result; }   // section 2

    // The cell images hold nothing yet, so the first Record must seed them, whatever
    // the settings say. Nothing has been copied into a readback buffer either.
    m_current         = 0;
    m_settings.reseed = true;
    m_readbackPending.fill(false);
    return InitializationResult::success();
}
```

The pipelines come last even though section 2 explains them first: a pipeline
layout needs the descriptor set layout that `CreateDescriptors` makes, and that
needs the images and buffers it points at.

### Where everything lands

```text
Source/PillowFort/VulkanGraphics/
  VulkanBarriers.h/.cpp     + memoryBarrier, computeToComputeBarrier        section 5
  GraphicsPipeline.h/.cpp   + createComputePipeline, groupCount             sections 2, 3
  VulkanResources.h/.cpp    + createReadbackBuffer, readBuffer              section 9
Source/PillowFort/Demos/Life/
  LifeDemo.h/.cpp           the demo
Shaders/Include/
  Random.glsl               pcgHash, for every shader that needs randomness section 3
Shaders/Life/
  LifeTypes.h               C++/GLSL twins                                  section 3
  LifeSeed.comp.glsl        writes a starting pattern                       section 3
  LifeStep.comp.glsl        one generation                                  sections 6-8
  LifeDisplay.comp.glsl     cells to scene pixels                           section 10
Source/SandboxGame/Main.cpp + one registration line                         section 12
```

```text
LifeDemo.cpp
  includes
  static querySubgroupProperties(physicalDevice)               section 7
  namespace pf::demos::life {
      using namespace vulkan_graphics;
      static drawLifePanel(settings, statistics, generation)   section 11
      LifeDemo::Setup                                          above
      LifeDemo::CreatePipelines                                section 2
      LifeDemo::CreateCellImages                               section 4
      LifeDemo::CreateBuffers                                  sections 8 and 9
      LifeDemo::CreateDescriptors                              section 4
      LifeDemo::Resize                                         section 10
      LifeDemo::Update                                         section 11
      LifeDemo::RecordSeed                                     section 3
      LifeDemo::RecordStep                                     section 5
      LifeDemo::RecordClearStatistics                          section 8
      LifeDemo::RecordReadback, ReadStatistics                 section 9
      LifeDemo::RecordDisplay                                  section 10
      LifeDemo::Record                                         section 11
      LifeDemo::Teardown                                       section 12
  }
```

`LifeDemo.cpp` includes `LifeDemo.h`, `PillowFort/DebugPanels/DemoPanel.h`,
`PillowFort/ErrorReporting/Log.h`,
`PillowFort/VulkanGraphics/GraphicsPipeline.h`,
`PillowFort/VulkanGraphics/VulkanBarriers.h`, `<imgui.h>`, and `<format>`.
`Demo.h` already brings in `SceneTargets.h` and `VulkanResources.h`.

---

## 1. Where compute runs

Three facts about compute work in Vulkan decide where its commands go.

**It runs on the queue you already have.** Chapter 02 section 5's
`selectQueueFamilies` already required `VK_QUEUE_COMPUTE_BIT` beside graphics and
presentation, for exactly this chapter, so every command below goes into the
frame's one command buffer on the one queue. A separate compute-only queue
("async compute") can overlap compute with rendering, at the price of
queue-family ownership transfers and semaphores between queues. ROADMAP parks
multiple queues, and nothing in the tutorial needs them.

**A dispatch must not be inside a rendering scope.** `vkCmdDispatch` between
`vkCmdBeginRendering` and `vkCmdEndRendering` is a validation error. That is why
Chapter 09's `Record` contract lets a demo record compute *before* it opens the
scene pass, and why Life, which has no scene pass at all, never opens one.

**Compute has its own bind point.** `vkCmdBindPipeline` and
`vkCmdBindDescriptorSets` take a `VkPipelineBindPoint`. A compute pipeline bound
at `VK_PIPELINE_BIND_POINT_COMPUTE` does not disturb the graphics pipeline or the
graphics descriptor sets, and the reverse also holds. A demo can bind its compute
state, dispatch, and then draw without rebinding anything for graphics.

---

## 2. The compute pipeline

**This is `createComputePipeline`.** A compute pipeline is a graphics pipeline
with everything removed but one shader stage. There is no vertex input, no
rasterizer, no blending, and no attachment formats, so the long struct literal of
Chapter 06 section 4 shrinks to a stage and a layout.

That is also why it gets a plain function rather than a desc struct. Chapter 06
section 8 made `GraphicsPipelineDesc` because a graphics pipeline has a dozen
things worth varying, and a compute pipeline has three: the shader, the layout,
and optionally specialization constants. It goes in `GraphicsPipeline.cpp`,
beside `createGraphicsPipeline`, because `createShaderModule` is a file-scope
static there and this is its second caller. If the file name starts to bother
you, rename it to `Pipelines.cpp` later. The declaration sits beside the
graphics one:

```cpp
// Chapter 20 section 2. One shader and a layout are the whole description, so no
// desc struct. VK_NULL_HANDLE, logged, if the shader is missing or creation fails.
VkPipeline createComputePipeline(VkDevice device, VkPipelineCache cache,
                                 const std::filesystem::path& shader,
                                 VkPipelineLayout layout,
                                 const VkSpecializationInfo* specialization = nullptr);
```

```cpp
// Chapter 20 section 2: the compute pipeline is the graphics one with everything
// but the shader stage removed.
VkPipeline createComputePipeline(VkDevice device, VkPipelineCache cache,
                                 const std::filesystem::path& shader,
                                 VkPipelineLayout layout,
                                 const VkSpecializationInfo* specialization)
{
    const std::vector<uint32_t> spirv = readSpirv(shader);   // logs if missing
    if (spirv.empty()) { return VK_NULL_HANDLE; }

    const VkShaderModule module = createShaderModule(device, spirv);

    const VkComputePipelineCreateInfo pipelineInfo{
        .sType  = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
        .stage  = {
            .sType               = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
            .stage               = VK_SHADER_STAGE_COMPUTE_BIT,
            .module              = module,
            .pName               = "main",
            .pSpecializationInfo = specialization,
        },
        .layout = layout,
    };

    VkPipeline pipeline = VK_NULL_HANDLE;
    const VkResult result = vkCreateComputePipelines(device, cache, 1, &pipelineInfo, nullptr, &pipeline);

    vkDestroyShaderModule(device, module, nullptr);   // consumed, as in createGraphicsPipeline

    if (result != VK_SUCCESS)
    {
        Log::error(std::format("vkCreateComputePipelines failed for {}: {}",
                               shader.string(), string_VkResult(result)).c_str());
        return VK_NULL_HANDLE;
    }
    return pipeline;
}
```

The `.stage` member is a whole `VkPipelineShaderStageCreateInfo`, nested by
value, so its designated initializers go inside the outer ones. The pipeline
cache from Chapter 06 section 6 works for compute exactly as for graphics.

**This is `CreatePipelines`.** Life has three compute shaders: seed, step, and
display. They share one pipeline layout, because the layout only describes what
can be bound, and the three shaders bind the same descriptor set and push the
same 16-byte block. Each reads the part of it that it needs. One layout also
means that the descriptor set bound for one dispatch stays valid for the next.
Sets stay bound across pipeline changes as long as the layouts are compatible
(Chapter 08 section 6).

```cpp
InitializationResult LifeDemo::CreatePipelines()
{
    // One layout for all three passes: the one set layout, and 16 bytes of push
    // constants that each shader reads part of.
    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(LifeParameters),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_setLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_vulkan.device, &layoutInfo, nullptr, &m_pipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for Life.");
    }

    m_seedPipeline    = createComputePipeline(m_vulkan.device, m_pipelineCache, "Life/LifeSeed.comp.spv", m_pipelineLayout);
    m_stepPipeline    = createComputePipeline(m_vulkan.device, m_pipelineCache, "Life/LifeStep.comp.spv", m_pipelineLayout);
    m_displayPipeline = createComputePipeline(m_vulkan.device, m_pipelineCache, "Life/LifeDisplay.comp.spv", m_pipelineLayout);
    if (m_seedPipeline == VK_NULL_HANDLE || m_stepPipeline == VK_NULL_HANDLE || m_displayPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating a Life compute pipeline failed.");
    }
    return InitializationResult::success();
}
```

The `.spv` paths are what Chapter 06's glob produces from
`Shaders/Life/LifeSeed.comp.glsl` and the others, so adding the three shaders
needs nothing in `premake5.lua` beyond rerunning `GenerateProjects.bat`. The
display shader pushes no constants, and that is fine: a layout may offer more
than a shader uses, never less.

---

## 3. The execution model, and the first shader

> **Jump:** a graphics pipeline decided how many shader invocations ran: one per
> vertex you drew and one per pixel covered. From here you decide, by sizing a
> grid to your data, and nothing outside the shader knows what an invocation
> means. Keep in mind that the grid you dispatch is almost never exactly the
> size of your data. It rounds up to whole workgroups, so every compute shader
> starts by asking whether its invocation is real.

A compute shader declares its **workgroup** size at the top:

```glsl
layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;
```

A workgroup here is 8 x 8 = 64 **invocations**. The invocations of one workgroup
run together on one part of the GPU, can share fast on-chip `shared` memory, and
can wait for each other with `barrier()` (section 6). `vkCmdDispatch(x, y, z)`
launches an `x * y * z` grid of workgroups. Workgroups run in no particular order,
possibly all at once, possibly one at a time, and **nothing synchronizes one
workgroup with another** inside a dispatch. If one workgroup's result is another's
input, they belong in two dispatches with a barrier between them (section 5).

Each invocation finds out where it is from built-in variables:

| Variable | Meaning |
| --- | --- |
| `gl_NumWorkGroups` | The `x, y, z` passed to `vkCmdDispatch` |
| `gl_WorkGroupID` | Which workgroup this invocation is in |
| `gl_WorkGroupSize` | The `local_size` constants |
| `gl_LocalInvocationID` | Position inside the workgroup, `(0..7, 0..7, 0)` here |
| `gl_LocalInvocationIndex` | The same, flattened: `0..63` |
| `gl_GlobalInvocationID` | `gl_WorkGroupID * gl_WorkGroupSize + gl_LocalInvocationID`: the position in the whole grid |

Most shaders use `gl_GlobalInvocationID` as "my element". Section 6 is where the
local IDs earn their place.

### How big a workgroup

The rules that decide it, with the reasons:

| Rule | Why |
| --- | --- |
| A multiple of the subgroup size | The hardware runs invocations in fixed-width groups: 32 on NVIDIA, 64 or 32 on AMD, 8 to 32 on Intel, 8 on lavapipe (section 7). A *lane* is one invocation's slot in such a group. A workgroup of 48 on a 32-wide GPU fills two groups and leaves 16 lanes idle. |
| 64 or 256 invocations | Enough work per group to *hide memory latency*: while one workgroup waits hundreds of cycles for memory, the core runs another, so more groups resident at once means fewer idle cycles. Small enough that several groups fit on one core at once. |
| At most 128 unless you checked | `maxComputeWorkGroupInvocations` is only **guaranteed** to be 128, and `maxComputeWorkGroupSize` only `(128, 128, 64)`. Every desktop GPU reports 1024, but a size above 128 is a hardware requirement you are adding. |

This tutorial uses 64: `8 x 8` for images, `64` for lists. It is a multiple of
every subgroup size above and within the guarantee. The path tracer (33) uses
`8 x 8` for the same reasons.

The limits worth knowing, all in `VkPhysicalDeviceLimits`:

| Limit | Guaranteed | Typical desktop | lavapipe |
| --- | --- | --- | --- |
| `maxComputeWorkGroupInvocations` | 128 | 1024 | 1024 |
| `maxComputeWorkGroupCount` | 65535 in each dimension | 65535, or far more in x | 65535 |
| `maxComputeSharedMemorySize` | 16 KB | 32 to 64 KB | 32 KB |

The workgroup-count cap is the one that bites later: a 1D dispatch of 64-wide
groups tops out near 4.2 million elements, which a large particle pool can
reach (21). Query, and do not assume.

### Dispatch sizing and the bounds guard

You need enough workgroups to cover the grid, so you divide and round up.
`groupCount` is the rounding, written once, in `GraphicsPipeline.h`, because a
truncating `(count / groupSize)` silently skips the last partial group:

```cpp
// Chapter 20 section 3. Workgroups needed to cover `count` items: rounds up, so
// the last group runs past the end and the shader must check its index.
constexpr uint32_t groupCount(uint32_t count, uint32_t groupSize)
{
    return (count + groupSize - 1) / groupSize;
}
```

(`GraphicsPipeline.h` gains `#include <cstdint>` for `uint32_t`.)

Life's grid is 300 x 170 cells. 300 / 8 is 37.5 and 170 / 8 is 21.25, so the
dispatch is 38 x 22 workgroups, 304 x 176 invocations. The extra 4 columns and
6 rows of invocations do not correspond to cells. Writing from them writes
outside the image. With GPU-assisted validation on you get a message; without it
you get corruption along the right and bottom edges that looks like a wrap-around
bug. Every shader below checks first. The grid size was picked to *not* be a
multiple of 8 so that the check is exercised.

### The twin structs

The seed shader is the first to read push constants, so the header both
languages share comes first. It has Chapter 09's `<Name>Types.h` shape: GLSL
includes it as `"LifeTypes.h"` from beside the shaders, and C++ as
`"Life/LifeTypes.h"`. It includes Chapter 08's `SharedShaderTypes.h` for the
`uint` alias on the C++ side, and its C++ half lives in the demo's namespace.

```c
/* Shaders/Life/LifeTypes.h - Chapter 20's C++/GLSL twins. GLSL includes it as
   "LifeTypes.h", C++ as "Life/LifeTypes.h". */
#ifndef PF_LIFE_TYPES_H
#define PF_LIFE_TYPES_H

#include "SharedShaderTypes.h"   /* the vec4 and uint aliases, on the C++ side */

#ifdef __cplusplus
    namespace pf::demos::life {
    using shared::uint;
#endif

/* Push constants, shared by all three passes; each reads the fields it needs. */
struct LifeParameters
{
    uint  seed;              /* a new value reseeds the random soup */
    uint  pattern;           /* 0 = random soup, 1 = a single glider */
    float density;           /* random soup: the chance that a cell starts alive */
    uint  countStatistics;   /* 1 on the frame's last step, 0 on the others */
};

/* The statistics buffer (std430). Zeroed by vkCmdFillBuffer every frame. */
struct LifeStatistics
{
    uint population;         /* cells alive after the frame's last step */
    uint births;             /* cells that came alive in that step */
    uint deaths;             /* cells that died in it */
    uint padding0;
};

#ifdef __cplusplus
    static_assert(sizeof(LifeParameters) == 16, "LifeParameters layout drifted.");
    static_assert(sizeof(LifeStatistics) == 16, "LifeStatistics layout drifted.");
    }
#endif

#endif
```

Both structs are four 4-byte scalars, which lay out identically in C, std430, and
std140, so the size checks are all they need. Section 8 says what changes when a
struct holds vectors. `LifeStatistics` is explained there too.

### A hash, shared by every shader that needs randomness

The random soup needs a random value per cell, and a GPU has no `rand()`. What it
has is integer arithmetic, and a good **hash** turns any integer into one that
looks random: neighbouring inputs give unrelated outputs. PCG's output function
is the standard choice, a few multiplies and shifts. Particles (21), grass
(25-27), and the path tracer (33) all need it too, so it goes in an include
beside `SharedShaderTypes.h`, not in Life's folder:

```glsl
// Shaders/Include/Random.glsl - hashing and random numbers for any shader.
// An include, not a stage: Chapter 06's glob compiles only .vert, .frag, and
// .comp files, so this is compiled through the shaders that include it.
#ifndef PF_RANDOM_GLSL
#define PF_RANDOM_GLSL

// PCG: a well-mixed 32-bit hash. Every output bit depends on every input bit, so
// neighbouring inputs (cell 7, cell 8) give unrelated outputs.
uint pcgHash(uint value)
{
    uint state = value * 747796405u + 2891336453u;
    uint word  = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
    return (word >> 22u) ^ word;
}

#endif
```

The include guard matters once a shader includes two headers that both include
this one. Chapter 21 adds random floats and directions to the same file.

### The seed shader

**This is `LifeSeed.comp.glsl`**, the simplest shader in the chapter: one
invocation per cell, nothing read, one value written. Its job is the starting
pattern: either a random soup, or one glider near the centre for the exit
check.

```glsl
// Shaders/Life/LifeSeed.comp.glsl
#version 450
#extension GL_GOOGLE_include_directive : require
#include "LifeTypes.h"
#include "Random.glsl"

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 1, r32ui) uniform writeonly uimage2D cellsOut;

layout(push_constant) uniform PushConstants
{
    LifeParameters parameters;
};

void main()
{
    ivec2 cell = ivec2(gl_GlobalInvocationID.xy);
    ivec2 size = imageSize(cellsOut);
    if (cell.x >= size.x || cell.y >= size.y) { return; }   // the dispatch rounds up

    bool alive = false;
    if (parameters.pattern == 0u)
    {
        // One hash per cell from its index and the seed: independent cells, and a
        // different soup for every seed.
        uint index = uint(cell.y) * uint(size.x) + uint(cell.x);
        // Divided by 2^32, the 32-bit hash becomes a float between 0 and 1.
        float chance = float(pcgHash(index ^ pcgHash(parameters.seed))) * (1.0 / 4294967296.0);
        alive = chance < parameters.density;
    }
    else
    {
        // A glider, a little up and left of the centre. It travels down and to the
        // right forever, so on an otherwise empty grid the population stays 5.
        ivec2 offset = cell - size / 2;
        alive = offset == ivec2(1, 0) || offset == ivec2(2, 1)
             || offset == ivec2(0, 2) || offset == ivec2(1, 2) || offset == ivec2(2, 2);
    }
    imageStore(cellsOut, cell, uvec4(alive ? 1u : 0u));
}
```

Things worth noticing:

- **`imageSize` instead of a size in the push constants.** The image knows its
  extent. Asking it keeps one source of truth, so a grid-size change on the C++
  side cannot disagree with the shader.
- **The guard returns early.** That is safe here because nothing later in the
  shader needs every invocation present. Section 6 has a shader where it is not.
- **The hash.** A random value per cell from `pcgHash(index ^ pcgHash(seed))` is
  independent per cell, reproducible for a given seed, and different for each
  seed. Hashing the seed first matters: `index ^ seed` alone would make seed 1's
  soup seed 0's with neighbouring cells swapped. The `sin`-based one-liners from
  shader-toy code produce visible patterns. Chapter 21 explains seeding
  properly, because its particles need fresh random numbers every frame.
- **`uvec4` for `imageStore` on a `uimage2D`.** A store always takes a 4-vector;
  the components the format lacks are dropped.

**This is `RecordSeed`.** Bind, push, dispatch, barrier. Section 4 explains which
set it binds and section 5 explains the barrier, but the shape is the one every
dispatch in this chapter has:

```cpp
void LifeDemo::RecordSeed(VkCommandBuffer commandBuffer)
{
    const LifeParameters parameters{
        .seed    = m_seed++,
        .pattern = static_cast<uint32_t>(m_settings.pattern),
        .density = m_settings.density,
    };
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_seedPipeline);
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                       0, sizeof(parameters), &parameters);

    // The seed shader writes binding 1, so bind the set whose output is the
    // current image: the one that reads the other.
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_pipelineLayout,
                            0, 1, &m_sets[1 - m_current], 0, nullptr);
    vkCmdDispatch(commandBuffer, groupCount(GRID_WIDTH, GROUP_SIZE), groupCount(GRID_HEIGHT, GROUP_SIZE), 1);

    computeToComputeBarrier(commandBuffer);   // the first step reads what this wrote
    m_generation = 0;
}
```

`GROUP_SIZE` in C++ and `local_size_x = 8` in GLSL must agree, and nothing checks
that they do. Section 8's specialization-constant note shows how to make the
shader take its size from C++ when you have several sizes to keep in step.

---

## 4. Storage images

The cells live in images that compute shaders read and write directly with
integer coordinates. These are **storage images**: no sampler, no filtering, no
mipmap selection, just `imageLoad(image, ivec2)` and `imageStore(image, ivec2,
value)`. They differ from the textures of Chapter 08 in four ways.

**The format.** Storage support is per format. The spec guarantees
`STORAGE_IMAGE` support only for a short list. The useful ones are
`R32_UINT`, `R32_SINT`, `R32_SFLOAT`, `R32G32_SFLOAT`, `R32G32B32A32_SFLOAT`,
`R16G16B16A16_SFLOAT`, and `R8G8B8A8_UNORM` (and their `UINT`/`SINT` siblings).
Small formats like `R8_UINT` need the `shaderStorageImageExtendedFormats`
feature, and `_SRGB` formats are never storage formats (Chapter 03 section 5).
Life stores one 32-bit unsigned integer per cell, the number of generations the
cell has been alive, in `R32_UINT`. Four bytes for one bit of state looks
wasteful, but it is on the guaranteed list, it gives the display an age to color
by, and at 51,000 cells it is 200 KB. If a format is not on the list, check
`vkGetPhysicalDeviceFormatProperties` for `STORAGE_IMAGE_BIT` in
`optimalTilingFeatures` before relying on it (Chapter 08 section 3).

**The format qualifier.** The GLSL declaration names the format:
`layout(r32ui) uniform uimage2D`. `imageLoad` needs it unless the device offers
`shaderStorageImageReadWithoutFormat`, and it must match the image view's actual
format. Validation catches a mismatch only when the shader actually executes that
access, so a rarely taken branch can hide one. The image type follows the
format's kind: `uimage2D` for `UINT`, `iimage2D` for `SINT`, and `image2D` for
float and normalized formats. `r32ui` matches `R32_UINT`, `rgba16f` matches
`R16G16B16A16_SFLOAT`, `rg32f` matches `R32G32_SFLOAT`, and `rgba8` matches
`R8G8B8A8_UNORM`.

**`readonly` and `writeonly`.** They compile to real SPIR-V decorations
(`NonWritable`, `NonReadable`), drivers use them, and validation uses them to
catch a store to an input. They are *not* an aliasing promise; that is
`restrict`, a separate qualifier. Declare the access you actually use.

**The layout is `GENERAL`.** A storage image must be in `VK_IMAGE_LAYOUT_GENERAL`
when a shader accesses it. There is no optimal layout for read-write access.
`GENERAL` is deliberately unoptimized, so an image that is only *sampled*
afterwards is better moved to `SHADER_READ_ONLY_OPTIMAL` (Chapter 04's cookbook).
Life's cells are only ever accessed as storage, so they go to `GENERAL` once and
stay there.

**This is `CreateCellImages`.** Two images, because a generation cannot be
computed in place: a cell's new value depends on its neighbours' old values, and
in-place updates would mix old and new depending on which workgroup ran first.

```cpp
InitializationResult LifeDemo::CreateCellImages()
{
    // One 32-bit unsigned integer per cell: how many generations it has been alive.
    // STORAGE is the only usage: imageLoad and imageStore, never sampled or copied.
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R32_UINT,
        .extent        = { GRID_WIDTH, GRID_HEIGHT, 1 },
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

    for (size_t i = 0; i < m_cellImages.size(); ++i)
    {
        if (vmaCreateImage(m_vulkan.allocator, &imageInfo, &allocationInfo,
                           &m_cellImages[i], &m_cellAllocations[i], nullptr) != VK_SUCCESS)
        {
            return InitializationResult::failure("vmaCreateImage failed for a Life cell image.");
        }

        const VkImageViewCreateInfo viewInfo{
            .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
            .image            = m_cellImages[i],
            .viewType         = VK_IMAGE_VIEW_TYPE_2D,
            .format           = imageInfo.format,
            .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
        };
        if (vkCreateImageView(m_vulkan.device, &viewInfo, nullptr, &m_cellViews[i]) != VK_SUCCESS)
        {
            return InitializationResult::failure("vkCreateImageView failed for a Life cell image.");
        }
    }

    // Storage images are used in GENERAL. Move both there once, here; nothing
    // transitions them again, so every later barrier on them is a memory barrier.
    immediateSubmit(m_vulkan, [&](VkCommandBuffer commandBuffer) {
        for (VkImage image : m_cellImages)
        {
            transitionImage(commandBuffer, image,
                            VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                            VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                            VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                            VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
        }
    });
    return InitializationResult::success();
}
```

The one transition answers the three questions of Chapter 04 section 5 like
this:

- **Q1 (execution):** nothing came before, so the source stage is `NONE`. The
  destination is `COMPUTE_SHADER`, the first stage that touches the images.
- **Q2 (memory):** there are no earlier writes to flush, so the source access is
  `NONE`. The destination access is storage read and write, since the first
  shaders to touch the images do both.
- **Q3 (layout):** `UNDEFINED` to `GENERAL`. The contents are garbage until the
  seed pass writes every cell.

"Everything after the barrier" means everything submitted to the queue after
it, in any command buffer (Chapter 04 section 5), so this one also orders every
frame recorded after `immediateSubmit` returns. That is why a barrier in a
one-off upload command buffer is enough for work submitted later.

### Descriptors, and ping-pong without updates

**This is `CreateDescriptors`.** One set layout with four bindings serves all
three shaders. A shader declares only the bindings it uses, and a layout may
have more.

| Binding | Type | Seed | Step | Display |
| --- | --- | --- | --- | --- |
| 0 `cellsIn` | storage image | | reads | reads |
| 1 `cellsOut` | storage image | writes | writes | |
| 2 `statistics` | storage buffer | | atomics | |
| 3 `sceneImage` | storage image | | | writes |

The ping-pong is two prebuilt sets. Set 0 reads image 0 and writes image 1; set
1 reads image 1 and writes image 0. A step binds `m_sets[m_current]`, writes the
other image, and flips `m_current`. No descriptor is updated per dispatch, which
matters because updating a set that an in-flight frame may still be reading is
exactly what Chapter 08 section 6 forbids. Binding 3 is the engine's scene
image. Its view changes when the window does, so `Resize` writes it (section 10),
not this function.

```cpp
InitializationResult LifeDemo::CreateDescriptors()
{
    // Every binding is used only by compute shaders. Binding 3 is the engine's
    // scene image, written in Resize because its view changes with the window.
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding         = 0,   // cellsIn
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding         = 1,   // cellsOut
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding         = 2,   // statistics
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding         = 3,   // sceneImage
          .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
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
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for Life.");
    }

    // Two sets of three storage images and one storage buffer.
    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,  2 * 3 },
        { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 2 * 1 },
    };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 2,
        .poolSizeCount = 2,
        .pPoolSizes    = poolSizes,
    };
    if (vkCreateDescriptorPool(m_vulkan.device, &poolInfo, nullptr, &m_descriptorPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for Life.");
    }

    const std::array<VkDescriptorSetLayout, 2> layouts{ m_setLayout, m_setLayout };
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_descriptorPool,
        .descriptorSetCount = 2,
        .pSetLayouts        = layouts.data(),
    };
    if (vkAllocateDescriptorSets(m_vulkan.device, &allocateInfo, m_sets.data()) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for Life.");
    }

    // Set i reads image i and writes image 1 - i: the ping-pong is two prebuilt
    // sets, never a descriptor update per dispatch.
    for (uint32_t i = 0; i < 2; ++i)
    {
        const VkDescriptorImageInfo cellsIn{
            .imageView   = m_cellViews[i],
            .imageLayout = VK_IMAGE_LAYOUT_GENERAL,
        };
        const VkDescriptorImageInfo cellsOut{
            .imageView   = m_cellViews[1 - i],
            .imageLayout = VK_IMAGE_LAYOUT_GENERAL,
        };
        const VkDescriptorBufferInfo statistics{
            .buffer = m_statistics.buffer,
            .offset = 0,
            .range  = sizeof(LifeStatistics),
        };
        const VkWriteDescriptorSet writes[] = {
            { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
              .dstSet          = m_sets[i],
              .dstBinding      = 0,
              .descriptorCount = 1,
              .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
              .pImageInfo      = &cellsIn },
            { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
              .dstSet          = m_sets[i],
              .dstBinding      = 1,
              .descriptorCount = 1,
              .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
              .pImageInfo      = &cellsOut },
            { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
              .dstSet          = m_sets[i],
              .dstBinding      = 2,
              .descriptorCount = 1,
              .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
              .pBufferInfo     = &statistics },
        };
        vkUpdateDescriptorSets(m_vulkan.device, 3, writes, 0, nullptr);
    }
    return InitializationResult::success();
}
```

Notice what a storage image descriptor does *not* have: a sampler. The
`VkDescriptorImageInfo` carries only the view and the layout the image will be
in when the shader runs. The pool is the demo's own (Chapter 09). The engine's
pool is sized for the composite set alone.

The seed shader writes binding 1, so `RecordSeed` binds `m_sets[1 - m_current]`
to make "binding 1" mean "the current image". Seeding is a step that ignores its
input.

---

## 5. Barriers between dispatches

Two dispatches in one command buffer have **no ordering between them** unless you
add one. The second may start before the first finishes, and even when it starts
later, the first's writes may still be in a cache the second cannot see. This is
the most common compute bug there is. It is also the one most likely to look
fine: on a fast GPU the dispatches usually do run in order, and the bug appears
on someone else's machine, or at a different window size.

### What sync validation can see

> **Jump:** since Chapter 05, "synchronization validation is silent" meant
> something, because a positive control had fired. That control was an
> *attachment* hazard, and attachments are what the layer has always tracked.
> Everything in this chapter is a shader reading and writing through
> descriptors, which the layer follows only through the second setting Chapter
> 02 section 2 turned on. Keep in mind from here that a silent layer proves
> something only about the accesses in the first two rows below.

Chapter 02 section 2's "One blind spot" paragraph explained that second setting,
`syncval_shader_accesses_heuristic`. With it on, the layer reads each bound
pipeline's SPIR-V, works out which bindings each shader reads and which it
writes, and treats every dispatch and draw as accessing those resources. That
is what makes a missing barrier between two dispatches a
`SYNC-HAZARD-READ-AFTER-WRITE` instead of silence. Here is the whole picture, in
one table that the later chapters point back to:

| | What sync validation checks |
| --- | --- |
| **Always** | Attachments (draws, clears, resolves, loads and stores), copies, `vkCmdFillBuffer`, and layout transitions |
| **With the shader-access setting** | Storage buffers, storage images, and sampled images that a dispatch or draw uses, each as a whole resource |
| **Not at all** (layer 1.4.363) | An atomic as a *write*: `atomicAdd` reads and writes, and the layer records only the read. One rendering scope's attachment writes before the next scope loads the same image (Chapter 21). A ping-pong's write-after-write when a read of the same image sits between the writes (Chapter 29 section 5). A read through an array of descriptors (one binding, `descriptorCount` above 1), even at a constant index (Chapter 30 section 4). You will meet the last two in Chapters 29 and 30; they need not make sense yet |

A barrier whose job is in the last row is argued from the three questions, and
the layer cannot confirm it either way. "As a whole resource" can also cut the
other way: two dispatches that write different halves of one buffer look like
they conflict. Nothing in this tutorial does that, but if a hazard appears only
with the setting on, check which bytes each side really touches. And a
`vkconfig` override that lists the setting beats the program's request;
`VK_LAYER_SYNCVAL_SHADER_ACCESSES_HEURISTIC=1`, set for one process, forces it
on, as `VK_LAYER_VALIDATE_SYNC=1` does for sync validation itself.

That is why this chapter's exit check deletes one barrier on purpose. The hazard it
must report is a dispatch reading an image another dispatch wrote, which the
layer can see only through this setting. If it reports nothing, the setting is
off, and every "silent" in this chapter proves nothing.

### The helpers

**This is `memoryBarrier` and `computeToComputeBarrier`, in `VulkanBarriers`.**
Chapter 04's `transitionImage` is an image barrier: three questions about one
image, layout included. Between dispatches whose resources stay in `GENERAL`
there is no layout to change, and often more than one resource is involved: Life's
step writes an image and, on its last step, a buffer. A **global memory
barrier** (`VkMemoryBarrier2`) answers Q1 and Q2 for every resource at once:

```cpp
// Chapter 20 section 5. A global memory barrier: the same three questions as
// transitionImage minus the layout, and no particular image or buffer. Every
// buffer hazard in the tutorial uses this.
void memoryBarrier(VkCommandBuffer commandBuffer,
                   VkPipelineStageFlags2 srcStage,
                   VkAccessFlags2 srcAccess,
                   VkPipelineStageFlags2 dstStage,
                   VkAccessFlags2 dstAccess);

// Chapter 20 section 5. One dispatch's storage writes, before the next dispatch
// reads them or writes over them.
void computeToComputeBarrier(VkCommandBuffer commandBuffer);
```

```cpp
void memoryBarrier(VkCommandBuffer commandBuffer,
                   VkPipelineStageFlags2 srcStage,
                   VkAccessFlags2 srcAccess,
                   VkPipelineStageFlags2 dstStage,
                   VkAccessFlags2 dstAccess)
{
    const VkMemoryBarrier2 barrier{
        .sType         = VK_STRUCTURE_TYPE_MEMORY_BARRIER_2,
        .srcStageMask  = srcStage,
        .srcAccessMask = srcAccess,
        .dstStageMask  = dstStage,
        .dstAccessMask = dstAccess,
    };
    const VkDependencyInfo dependency{
        .sType              = VK_STRUCTURE_TYPE_DEPENDENCY_INFO,
        .memoryBarrierCount = 1,
        .pMemoryBarriers    = &barrier,
    };
    vkCmdPipelineBarrier2(commandBuffer, &dependency);
}

void computeToComputeBarrier(VkCommandBuffer commandBuffer)
{
    // READ and WRITE on the destination: the next dispatch may read what this one
    // wrote, and ping-pong means the one after that overwrites it.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
}
```

Both go in `VulkanBarriers.h` and `VulkanBarriers.cpp`, inside
`pf::vulkan_graphics`, after `transitionImage`. Two choices in them are worth
defending.

**Why a global barrier and never `VkBufferMemoryBarrier2`.** A buffer barrier
names a buffer and a byte range, which looks more precise. Desktop drivers
implement it as a global barrier anyway: caches are not flushed by address range.
The range matters only for a queue-family ownership transfer, which this
tutorial never does. A global barrier is one struct instead of one per buffer,
and it cannot name the wrong buffer. Images still get `transitionImage`
whenever their layout changes, because only an image barrier can change a layout.

**Why `READ | WRITE` on the destination.** Step N+1 reads what step N wrote, which
is a read-after-write and needs `STORAGE_READ`. Step N+2 then *overwrites* that
same image, a write-after-write, and that needs `STORAGE_WRITE`, which the next
barrier's source will not cover on its own. Leaving out the write half is
the classic ping-pong bug: Chapter 29's FFT has the same rule.

The three questions for a barrier between two generations:

- **Q1:** step N's `COMPUTE_SHADER` work must finish before step N+1's
  `COMPUTE_SHADER` work starts.
- **Q2:** step N's `SHADER_STORAGE_WRITE`s are made available and then visible to
  step N+1's `SHADER_STORAGE_READ`s and `SHADER_STORAGE_WRITE`s.
- **Q3:** no layout changes. Both images stay `GENERAL`, which is why this is a
  memory barrier and not an image barrier.

**This is `RecordStep`.** It has the same shape as `RecordSeed`, with the barrier
doing the work this section is about, and then the flip:

```cpp
void LifeDemo::RecordStep(VkCommandBuffer commandBuffer, bool countStatistics)
{
    const LifeParameters parameters{
        .countStatistics = countStatistics ? 1u : 0u,
    };
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_stepPipeline);
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                       0, sizeof(parameters), &parameters);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_pipelineLayout,
                            0, 1, &m_sets[m_current], 0, nullptr);
    vkCmdDispatch(commandBuffer, groupCount(GRID_WIDTH, GROUP_SIZE), groupCount(GRID_HEIGHT, GROUP_SIZE), 1);

    // Section 5: the next step reads what this one wrote, and overwrites what it read.
    computeToComputeBarrier(commandBuffer);

    m_current = 1 - m_current;
    ++m_generation;
}
```

`m_current` flips at record time, not at execution time, and that is correct:
the commands execute in the order recorded, so "the image the next recorded
dispatch reads" is all `m_current` has to mean.

### The return trip

Every per-frame cycle needs both directions (Chapter 04's cookbook notes). The
last thing a frame does with the cells is the display pass reading them. The
next frame's first write to them must wait for that read, which is a
write-after-read: Q1 only, since a read leaves nothing to flush. That is why
`Record` starts with a barrier before it writes anything (section 11).

In this demo the step's own barrier usually covers it already, because a
barrier orders everything before it on the queue, last frame's command buffer
included, against everything after it (Chapter 04 section 5). But while the simulation is paused and you
press **Reseed**, no step runs, the seed is the frame's first write, and only the
return-trip barrier stands between it and last frame's display read. Sync
validation, with the heuristic on, reports exactly that as a
`SYNC-HAZARD-WRITE-AFTER-READ` at submit time if the barrier is removed. Correct
only because of how other code happens to be ordered is the kind of correct that
breaks during the next refactor. Write the barrier.

---

## 6. Shared memory and `barrier()`

> **Jump:** until now every shader invocation has been independent. A vertex
> shader never saw its neighbour's result, and neither did a fragment shader.
> Inside a compute workgroup, invocations can cooperate: they share a small
> on-chip memory and can wait for each other. This needs a second kind of
> barrier, `barrier()` in GLSL, which is a different thing from
> `vkCmdPipelineBarrier2`. Keep the two apart: `barrier()` orders invocations of
> one workgroup inside one dispatch; a pipeline barrier orders whole commands.

A Life step done naively reads nine cells per invocation: itself and eight
neighbours. Every cell is therefore read nine times from the image, once by each
neighbour and once by itself. Each workgroup of 8 x 8 cells needs only a
10 x 10 tile, its own cells plus a one-cell border, which is 100 reads instead
of 576. The cooperative version:

1. All 64 invocations together load the 100-cell tile into `shared` memory.
2. `barrier()`: nobody continues until everybody has finished loading.
3. Each invocation reads its neighbourhood from shared memory, which is fast on-chip
   storage, typically a few cycles away instead of hundreds.

**This is `LifeStep.comp.glsl`**, the first half. The second half, the
statistics, is section 7's and 8's.

```glsl
// Shaders/Life/LifeStep.comp.glsl
#version 450
#extension GL_GOOGLE_include_directive       : require
#extension GL_KHR_shader_subgroup_basic      : require
#extension GL_KHR_shader_subgroup_arithmetic : require
#include "LifeTypes.h"

const int GROUP = 8;            // the workgroup is GROUP x GROUP cells
const int TILE  = GROUP + 2;    // plus a one-cell border all round

layout(local_size_x = GROUP, local_size_y = GROUP, local_size_z = 1) in;

layout(set = 0, binding = 0, r32ui) uniform readonly  uimage2D cellsIn;
layout(set = 0, binding = 1, r32ui) uniform writeonly uimage2D cellsOut;

layout(set = 0, binding = 2, std430) buffer StatisticsBuffer
{
    LifeStatistics statistics;
};

layout(push_constant) uniform PushConstants
{
    LifeParameters parameters;
};

// One entry per cell of the tile: the workgroup's 8 x 8 cells and their neighbours.
shared uint tile[TILE * TILE];

void main()
{
    ivec2 size   = imageSize(cellsIn);
    ivec2 corner = ivec2(gl_WorkGroupID.xy) * GROUP - 1;   // the tile's top-left cell

    // 1. Load the tile together: 64 invocations, 100 entries, so some load twice.
    for (int i = int(gl_LocalInvocationIndex); i < TILE * TILE; i += GROUP * GROUP)
    {
        ivec2 cell = corner + ivec2(i % TILE, i / TILE);
        tile[i] = imageLoad(cellsIn, (cell + size) % size).r;   // the grid wraps around
    }

    // Nobody reads the tile until everybody has finished writing it.
    barrier();

    // 2. Count the eight neighbours from shared memory instead of the image.
    ivec2 local      = ivec2(gl_LocalInvocationID.xy) + 1;   // this cell, inside the tile
    uint  age        = tile[local.y * TILE + local.x];
    uint  neighbours = 0u;
    for (int dy = -1; dy <= 1; ++dy)
    {
        for (int dx = -1; dx <= 1; ++dx)
        {
            if (dx == 0 && dy == 0) { continue; }
            neighbours += tile[(local.y + dy) * TILE + (local.x + dx)] > 0u ? 1u : 0u;
        }
    }

    // Conway's rules: born with exactly 3 neighbours, survives with 2 or 3. The
    // value is how many generations the cell has been alive, for the display.
    bool alive = neighbours == 3u || (age > 0u && neighbours == 2u);
    uint next  = alive ? min(age + 1u, 65535u) : 0u;

    // 3. The bounds check comes only now. Invocations past the edge of the grid
    //    still had to help load the tile and reach barrier(), and they still take
    //    part in subgroupAdd below; they just do not store.
    ivec2 cell   = ivec2(gl_GlobalInvocationID.xy);
    bool  inside = cell.x < size.x && cell.y < size.y;
    if (inside)
    {
        imageStore(cellsOut, cell, uvec4(next));
    }
```

What is load-bearing in it:

- **`gl_LocalInvocationIndex` as a loop start, `GROUP * GROUP` as the stride.**
  This is the general shape of a cooperative load. 64 invocations walk 100 entries
  in strides of 64, so invocations 0-35 load two entries and the rest load one.
  The same loop works for any tile size and any workgroup size.
- **`barrier()` is a control barrier and, for `shared` variables, a memory
  barrier.** In a compute shader it makes every invocation of the workgroup wait
  until all have arrived, and makes their `shared` writes visible to each other.
  It does *not* order image or buffer memory between invocations. That would
  take `memoryBarrierImage()` or `memoryBarrierBuffer()` before it, which Life
  does not need, because the tile is the only thing invocations exchange.
- **No early return before `barrier()`.** This is the rule the seed shader did
  not have to care about. `barrier()` must be reached by every invocation of the
  workgroup, in *uniform control flow*: every invocation of the workgroup takes
  the same path to that line. If the out-of-range invocations of the
  right-hand workgroups returned at the top, the others would wait at
  `barrier()` for invocations that never arrive. The spec calls that undefined,
  and in practice it is a hang or garbage. So the guard moves down and becomes
  a condition on the store.
- **`(cell + size) % size` is the wrap.** The tile reaches one cell past each
  edge of the workgroup, so `cell` ranges from -1 to one past the edge. Adding
  `size` before the `%` keeps the operand non-negative, since GLSL's `%` on
  negative integers is undefined. For an in-range cell at column 299, its right
  neighbour at 300 wraps to 0, which is the torus. Out-of-range invocations read
  wrapped values too, harmlessly, because they never store.
- **The tile stores ages, and neighbour counting tests `> 0`.** One shared array
  serves both purposes: a neighbour counts if it is alive, and the cell's own
  entry is its age.
- **Shared memory budget.** 100 `uint`s is 400 bytes, far under the guaranteed
  16 KB. A larger tile with a wider border, or a `vec4` per entry, can reach the
  limit quickly. Count bytes when you design one.

A naive version, nine `imageLoad`s per invocation and no shared memory, is a
useful first step and a good thing to compare against. The checkpoint below runs
the step, so you can write the naive one first, see the pictures, then switch
to this one and see the same pictures. On a GPU with good caches, the tiled
version's win is modest at this size; it grows with the neighbourhood (a 5 x 5
blur reads 25 values per output) and with how often each value is reused.

---

## Checkpoint — see it run

Nothing has been on screen yet, and nothing in sections 7-9 is needed to watch
Life run: they count the cells and read the counts back. So the display comes
first. Write these now, out of order; each is final as written:

- Section 10's `LifeDisplay.comp.glsl`, `RecordDisplay`, and `Resize`. They use
  nothing from sections 7-9.
- Section 12's `Teardown`, the registration line in `Main.cpp`, and a rerun of
  `GenerateProjects.bat` for the new files. `Teardown` destroys the statistics
  and readback buffers before they exist, which is safe: destroying a null
  buffer does nothing.

And four stand-ins, each replaced by a later section:

- **`LifeStep.comp.glsl` ends after the store**, with the closing brace of
  `main`. Section 7 replaces that brace with the statistics.
- **`Setup` leaves out** the subgroup check at its top (section 7) and the
  `CreateBuffers` line (sections 8 and 9).
- **`CreateDescriptors` writes two descriptors**, not three:
  `vkUpdateDescriptorSets(m_vulkan.device, 2, writes, 0, nullptr)`. The third is
  binding 2's statistics buffer, which does not exist yet. Leaving a binding
  unwritten is legal while no dispatch uses it (section 10 says why), and the
  shortened step shader does not.
- **`Update` is empty** — `void LifeDemo::Update(const FrameInput&) {}` — and
  **`Record` is this**:

```cpp
// Section 6's checkpoint: a first Record, with no statistics. Section 11 writes the final one.
void LifeDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    computeToComputeBarrier(commandBuffer);        // section 5: the return trip
    if (m_settings.reseed)                         // section 3
    {
        RecordSeed(commandBuffer);
        m_settings.reseed = false;
    }
    RecordStep(commandBuffer, false);              // one generation a frame, not counted
    RecordDisplay(commandBuffer, frame.targets);   // section 10, written early
}
```

`Setup` asks for a reseed, so the first frame seeds a random soup. Pick **Life
(compute)** in the demo picker:

- [ ] A soup of orange (young) and blue (old) cells evolves at one generation a
      frame, with no artefacts along any edge.
- [ ] Resizing the window, very wide or very tall, draws the same grid centred,
      with square cells and dark margins.
- [ ] Synchronization validation, with the shader-access setting on, is silent.

Sections 7-9 now grow a demo that runs, and section 11's panel and final
`Record` replace the last two stand-ins.

---

## 7. Subgroups, a first look

The invocations of a workgroup do not run one at a time, and they do not all run
at once. The hardware runs them in fixed-size groups that execute in lockstep,
called **subgroups** in Vulkan, warps on NVIDIA, and waves or wavefronts on AMD.
Their size is the subgroup size:

| Hardware | Subgroup size |
| --- | --- |
| NVIDIA | 32 |
| AMD GCN | 64 |
| AMD RDNA | 32 or 64, chosen by the driver per shader; most drivers report 64 |
| Intel | 8, 16, or 32, chosen by the compiler per shader |
| lavapipe (the Linux CPU driver) | 8 |

The invocations of a subgroup can exchange values directly, without shared memory
and without `barrier()`: sum a value across the subgroup, broadcast one lane's
value, shuffle values between lanes. These are the GLSL `subgroup*` functions.
Vulkan 1.1 made them core, but only the **basic** operations
(`subgroupElect`, `subgroupBarrier`, `gl_SubgroupSize`) are guaranteed, and only
in compute shaders. Everything else, arithmetic included, is reported in
`VkPhysicalDeviceSubgroupProperties::supportedOperations`. Every desktop driver
supports arithmetic, but it is a hardware requirement, so `Setup` checks for it
and reports a missing one rather than failing to create the pipeline.

**This is `querySubgroupProperties`.** It is a file-scope helper, above the
namespace block in `LifeDemo.cpp`, because it needs nothing from the class:

```cpp
// File scope, above the namespace block. Section 7: subgroupAdd needs the
// arithmetic subgroup operations in the compute stage. Every desktop driver
// has them, but the spec guarantees only the basic ones, so ask.
static VkPhysicalDeviceSubgroupProperties querySubgroupProperties(VkPhysicalDevice physicalDevice)
{
    VkPhysicalDeviceSubgroupProperties subgroup{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SUBGROUP_PROPERTIES,
    };
    VkPhysicalDeviceProperties2 properties{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,
        .pNext = &subgroup,
    };
    vkGetPhysicalDeviceProperties2(physicalDevice, &properties);
    subgroup.pNext = nullptr;   // it pointed into this function's stack
    return subgroup;
}
```

It is the properties version of Chapter 02's feature chain:
`vkGetPhysicalDeviceProperties2` fills every struct chained to it. `Setup` logs
the subgroup size, so you can see 8 on lavapipe and 32 or 64 on a GPU.

Life uses one subgroup operation, to count. Every invocation knows whether its
cell is alive, was born, or died. Adding those up across 51,000 cells with one
atomic each would make 51,000 invocations queue up on one memory address.
`subgroupAdd` first sums inside each subgroup. One lane then does the atomic for
all of them, and the queue is 8 times shorter on lavapipe and 32 to 64 times
shorter on a GPU.

**This is `LifeStep.comp.glsl`, the second half.**

```glsl
    // 4. Statistics, on the frame's last step only. A push constant is the same for
    //    every invocation, so this branch is uniform and every lane reaches subgroupAdd.
    if (parameters.countStatistics != 0u)
    {
        uvec3 mine = uvec3(0u);
        if (inside)
        {
            mine.x = next > 0u ? 1u : 0u;                  // alive
            mine.y = (age == 0u && next > 0u) ? 1u : 0u;   // born
            mine.z = (age > 0u && next == 0u) ? 1u : 0u;   // died
        }
        uvec3 total = subgroupAdd(mine);   // every lane gets the subgroup's sum
        if (subgroupElect())               // and exactly one lane writes it
        {
            atomicAdd(statistics.population, total.x);
            atomicAdd(statistics.births,     total.y);
            atomicAdd(statistics.deaths,     total.z);
        }
    }
}
```

Two rules make this correct:

- **Every lane must be active at the `subgroupAdd`.** A subgroup operation
  combines only the lanes that reach it. If out-of-range invocations had skipped
  it, the sum would still be correct here, since they would contribute nothing,
  but `subgroupElect` might then pick a lane that is about to leave, and the
  pattern breaks the moment a branch is not that simple. The safe habit is the
  one above: keep everyone, and pass zeros.
- **`subgroupElect()` is true in exactly one active lane** (the lowest-numbered),
  which makes it the standard way to do something once per subgroup.

Subgroup sizes are why the workgroup size rule in section 3 exists, and they are
the main way compute code silently depends on the hardware. Code that assumes 32
lanes, through hard-coded shuffles or `gl_SubgroupInvocationID < 32`, breaks on
lavapipe's 8 and AMD's 64. Use `gl_SubgroupSize`. Chapter 02 section 7's
`subgroupSizeControl` and `computeFullSubgroups` let a pipeline *require* a size
and full subgroups, which the ocean's fast FFT path wants (29). Nothing here
needs them.

---

## 8. Storage buffers and atomics

A **storage buffer** is the buffer counterpart of a storage image: read-write
memory a shader indexes directly. Its GLSL side is a `buffer` block:

```glsl
layout(set = 0, binding = 2, std430) buffer StatisticsBuffer
{
    LifeStatistics statistics;
};
```

Compared with the uniform buffers of Chapter 08:

| | Uniform buffer | Storage buffer |
| --- | --- | --- |
| Shader access | Read only | Read, write, atomics |
| Guaranteed size per binding | 16 KB (`maxUniformBufferRange`) | 128 MB (`maxStorageBufferRange`) |
| Last member may be an unsized array (`Particle particles[];`) | No | Yes; `particles.length()` is computed from the bound range |
| Default layout | `std140` | `std430` |
| Buffer usage | `UNIFORM_BUFFER_BIT` | `STORAGE_BUFFER_BIT` |
| Typical use | Small per-frame constants every invocation reads | Large arrays, results, counters |

### std430, and the case that bites compute

Storage buffers use std430, with Chapter 08 section 8's rules and its three
habits: no `vec3` in a shared struct (use `vec4`, or pack a scalar in `w`),
`uint` instead of `bool`, and `static_assert` the size and key offsets. The
worst case is worth seeing once, because it is the trap a compute shader that
reads mesh data walks into (Chapter 33 section 6 reads its vertices as floats
for this reason). Chapter 11's `Vertex` is 48 tightly packed bytes:
`vec3 position, vec3 normal, vec2 uv, vec4 tangent` at offsets 0, 12, 24, 32.
The same struct declared in a std430 buffer puts `normal` at 16, `uv` at 32,
`tangent` at 48, and is 64 bytes long. A compute shader reading Chapter 11's
vertex buffer through it reads garbage from the second vertex on. The ways out:
declare the buffer as `float data[]` and index it in floats (12 per vertex),
or enable `scalarBlockLayout` (Chapter 02 section 7) and declare it
`layout(scalar)`, which follows C's rules.

`LifeStatistics` is four `uint`s. It is identical in every layout, and the
`static_assert` in `LifeTypes.h` keeps it that way.

### Atomics

`atomicAdd(statistics.population, n)` adds `n` to a buffer member as one
indivisible read-modify-write, so two invocations adding at once both count. It
returns the value *before* the add, which is what makes atomics more than
counters. `slot = atomicAdd(count, 1)` hands every caller a distinct slot, and
that is how Chapter 21 appends particles to a list. GLSL has `atomicAdd`,
`atomicMin`, `atomicMax`, `atomicAnd`, `atomicOr`, `atomicXor`, `atomicExchange`,
and `atomicCompSwap`, on 32-bit `int` and `uint` members of storage buffers and
`shared` variables. Compute shaders get them without any feature; 64-bit
integers and floats need extensions. On images, atomics need the `R32_UINT` or
`R32_SINT` format.

Atomics are correct regardless of order. They are not free: the hardware
serializes operations on one address. That is section 7's reason to reduce first.

### The statistics buffer

**This is `CreateBuffers`, first half.** The buffer is device-local because only
the GPU touches it. Its three usage bits are its three uses: atomics
(`STORAGE_BUFFER`), the per-frame zeroing below (`TRANSFER_DST`), and the copy
out for the CPU in section 9 (`TRANSFER_SRC`). Forgetting a usage bit is a
validation error at the command that needs it, far from this line.

```cpp
InitializationResult LifeDemo::CreateBuffers()
{
    // Section 8. Device-local: only the GPU touches it. STORAGE for the atomics,
    // TRANSFER_DST for vkCmdFillBuffer, TRANSFER_SRC for the readback copy.
    m_statistics = createBuffer(m_vulkan, sizeof(LifeStatistics),
                                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT
                                    | VK_BUFFER_USAGE_TRANSFER_DST_BIT
                                    | VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                                false);
    if (m_statistics.buffer == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the Life statistics buffer failed.");
    }
```

The descriptor in `CreateDescriptors` binds it with `range =
sizeof(LifeStatistics)`. A storage buffer binding's `offset` must be a multiple of
`minStorageBufferOffsetAlignment`, which may be as large as 256. That matters
when you bind several sub-ranges of one buffer, not here.

### Zeroing the counters every frame

The counters accumulate, so every frame that counts must start them at zero.
`vkCmdFillBuffer(commandBuffer, buffer, offset, size, value)` writes a repeated
32-bit value into a buffer on the GPU, and it is the right tool for a handful of
counters. It is a transfer command: synchronization treats it as a **clear**
(`VK_PIPELINE_STAGE_2_CLEAR_BIT`, access `TRANSFER_WRITE`), and it must be
outside a rendering scope. So it needs a barrier on each side.

**This is `RecordClearStatistics`.** `Record` calls it on every frame that
counts (section 11):

```cpp
void LifeDemo::RecordClearStatistics(VkCommandBuffer commandBuffer)
{
    // The return trip for the buffer: last frame's atomics wrote it and its readback copy read it.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_2_COPY_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);
    vkCmdFillBuffer(commandBuffer, m_statistics.buffer, 0, sizeof(LifeStatistics), 0);
    // The zeros, before this frame's atomics read and write them.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
}
```

The first barrier is the return trip for the buffer. The previous frame's atomics
wrote it and its readback copy read it, and the fill must wait for both:

- **Q1:** `COMPUTE_SHADER` (the atomics) and `COPY` (the readback copy) before
  `CLEAR`.
- **Q2:** the atomics' writes are made available (`SHADER_STORAGE_WRITE`) before
  the fill writes over them (`TRANSFER_WRITE`). That is a write-after-write. The
  copy only read, so it needs Q1 alone, and adds nothing to the access mask.
- **Q3:** none; it is a buffer.

The second orders the fill before this frame's atomics:

- **Q1:** `CLEAR` before `COMPUTE_SHADER`.
- **Q2:** the zeros are made available and visible to storage read and write. An
  atomic is both a read and a write.
- **Q3:** none.

The fill is a write the layer sees and the atomics are reads it sees (section
5's table), so deleting either barrier is reported. On a GPU a missing barrier
here shows as counters that occasionally include last frame's counts, or lose
the start of this frame's.

The alternative to a fill is a one-invocation compute pass that writes the zeros.
It saves nothing here: it needs the same barriers. Chapter 21 resets its
counters inside a compute pass that has to run anyway, which removes the fill
and its barriers entirely. That is the case where the alternative wins.

### A note on specialization constants

`GROUP_SIZE = 8` in C++ and `local_size_x = 8` in GLSL are two copies of one
number. GLSL can take the workgroup size from a specialization constant instead,
with `layout(local_size_x_id = 0, local_size_y_id = 1) in;`, which
`createComputePipeline`'s last parameter then sets at pipeline creation, exactly
like Chapter 08's `encodeSrgb`. Life keeps the literal.

---

## 9. Reading results back without stalling

> **Jump:** until now data has flowed one way, from the CPU to the GPU. The
> population counter is the first value the CPU needs back. The GPU runs a frame
> or two behind the CPU (Chapter 04 section 2), so a value the GPU produces
> "this frame" does not exist yet when the CPU records the next one. Keep in
> mind: a readback is a value from the past, and the only question is how far in
> the past.

The naive readback stalls. Record a copy into host-visible memory, submit, wait
for the fence, read. Waiting for the fence of the frame just submitted means the
CPU idles until the GPU finishes, the GPU idles while the CPU records the next
frame, and frames in flight are gone.

The pattern that does not stall is the one frames in flight already give you.
Keep **one readback buffer per frame in flight**. Each frame copies into its own
slot's buffer. The next time that slot comes round, `drawFrame` has already
waited on its fence before calling `Record`, so the copy is finished and nothing
waits extra. With two frames in flight the value is two frames old. That is the
price, and for a statistic on a panel it costs nothing.

### Memory the CPU reads

Chapter 08's `createBuffer` asks VMA for `HOST_ACCESS_SEQUENTIAL_WRITE`, which
is the right request for memory the CPU *writes*, and VMA may answer with
write-combined memory. Reading from that memory is legal and very slow: every
read can go across the bus uncached. A readback buffer asks for
`HOST_ACCESS_RANDOM`, and VMA then prefers `HOST_CACHED` memory, Chapter 08
section 1's type 2. Cached memory need not be coherent, so after the GPU writes
it the CPU's cache may hold stale lines. `vmaInvalidateAllocation` drops them,
and is a no-op on coherent memory.

**This is `createReadbackBuffer` and `readBuffer`, in `VulkanResources`.** They
are declared after `destroyBuffer` in `VulkanResources.h`:

```cpp
// Chapter 20 section 9. The CPU reads it: a copy destination in memory chosen for
// reading, mapped for its whole life. One per frame in flight.
AllocatedBuffer createReadbackBuffer(VulkanContext& context, VkDeviceSize size);

// Chapter 20 section 9. Only after the fence of the frame that wrote it: makes the
// GPU's writes visible to the CPU's caches, then copies `size` bytes out.
void readBuffer(VulkanContext& context, const AllocatedBuffer& buffer,
                void* destination, VkDeviceSize size);
```

They are defined in `VulkanResources.cpp`, after `destroyBuffer`:

```cpp
AllocatedBuffer createReadbackBuffer(VulkanContext& context, VkDeviceSize size)
{
    const VkBufferCreateInfo bufferInfo{
        .sType       = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
        .size        = size,
        .usage       = VK_BUFFER_USAGE_TRANSFER_DST_BIT,   // filled by vkCmdCopyBuffer
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
    };

    // RANDOM, not createBuffer's SEQUENTIAL_WRITE: the CPU reads this, and VMA then
    // prefers HOST_CACHED memory. Write-combined memory is fine to write and very
    // slow to read.
    const VmaAllocationCreateInfo allocationInfo{
        .flags = VMA_ALLOCATION_CREATE_HOST_ACCESS_RANDOM_BIT | VMA_ALLOCATION_CREATE_MAPPED_BIT,
        .usage = VMA_MEMORY_USAGE_AUTO,
    };

    AllocatedBuffer result{ .size = size };
    VmaAllocationInfo detail{};
    if (vmaCreateBuffer(context.allocator, &bufferInfo, &allocationInfo,
                        &result.buffer, &result.allocation, &detail) != VK_SUCCESS)
    {
        Log::error("vmaCreateBuffer failed for a readback buffer.");
        return {};
    }
    result.mapped = detail.pMappedData;
    return result;
}

void readBuffer(VulkanContext& context, const AllocatedBuffer& buffer,
                void* destination, VkDeviceSize size)
{
    // HOST_CACHED memory need not be HOST_COHERENT. Invalidating is what makes the
    // GPU's writes visible to the CPU there, and it is a no-op where it is coherent.
    vmaInvalidateAllocation(context.allocator, buffer.allocation, 0, size);
    std::memcpy(destination, buffer.mapped, static_cast<size_t>(size));
}
```

**This is `CreateBuffers`, second half.** One readback buffer per frame in
flight:

```cpp
    // Section 9. One per frame in flight, so a copy never lands in a buffer the
    // CPU may be reading.
    for (AllocatedBuffer& readback : m_readback)
    {
        readback = createReadbackBuffer(m_vulkan, sizeof(LifeStatistics));
        if (readback.buffer == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a Life readback buffer failed.");
        }
    }
    return InitializationResult::success();
}
```

### The copy, and the barriers around it

**This is `RecordReadback`.** `Record` calls it after the frame's last step:

```cpp
void LifeDemo::RecordReadback(VkCommandBuffer commandBuffer, uint32_t frameIndex)
{
    // The atomics' writes, before the copy reads the counters.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);
    const VkBufferCopy region{ .size = sizeof(LifeStatistics) };
    vkCmdCopyBuffer(commandBuffer, m_statistics.buffer, m_readback[frameIndex].buffer, 1, &region);
    // The copy's writes, visible to the CPU once this frame's fence has signalled.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    m_readbackPending[frameIndex] = true;
}
```

The first barrier answers the three questions for the copy reading the counters:
`COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` (the atomics) before `COPY` /
`TRANSFER_READ`, buffer, no layout. Its writer is an atomic, so it sits in the
last row of section 5's table: the three questions are its proof, not the layer.

The second is the one people leave out. A fence signal makes the GPU's writes
*available*; making them visible to the CPU is a separate step. It takes a barrier whose destination is `HOST` / `HOST_READ`,
recorded before the submit whose fence the CPU waits on. Most desktop drivers
work without it, which is how it gets forgotten. The Khronos synchronization
examples have it, and it costs nothing.

**This is `ReadStatistics`**, which `Record` calls before anything else:

```cpp
void LifeDemo::ReadStatistics(uint32_t frameIndex)
{
    // This slot's fence has been waited on, so the copy recorded the last time
    // this slot was used has landed. Read it once, then forget it.
    if (m_readbackPending[frameIndex])
    {
        readBuffer(m_vulkan, m_readback[frameIndex], &m_latest, sizeof(m_latest));
        m_readbackPending[frameIndex] = false;
    }
}
```

Three details:

- **It is in `Record`, not `Update`.** Chapter 09 calls `Update` (and ImGui)
  *before* `drawFrame` waits on the slot's fence, and `Record` after. Reading in
  `Update` would race the GPU's copy into that buffer.
- **`m_readbackPending`** remembers whether the slot's buffer holds a copy that
  has not been read. A paused frame does not count and does not copy, and without
  the flag the next visit to that slot would read the counts from two frames
  before. The panel would then flicker between old and new values while paused.
- **How old the numbers are.** Read in frame N's `Record`, they were copied in
  frame N - 2. The panel draws them in frame N + 1's `Update`. At one step per
  frame, the population on the panel is two generations behind the generation
  counter next to it: the lag is exactly `FRAMES_IN_FLIGHT` generations, which
  is the whole design.

---

## 10. Compute to graphics

Life's last pass turns cells into pixels. It writes the engine's scene image, the
`R16G16B16A16_SFLOAT` target from Chapter 08, directly, as a storage image. That
is why Chapter 08 created it with `STORAGE_BIT`, and it is how the path tracer
(33) works too. No graphics pipeline, no rendering scope, and no
`beginScenePass`: Chapter 09's `Record` contract lets a demo produce the scene
image any way it likes, as long as it overwrites every pixel and hands the image
back the way the composite pass expects it.

**This is `LifeDisplay.comp.glsl`.** One invocation per *window pixel*, not per
cell. Each pixel works out which cell it shows:

```glsl
// Shaders/Life/LifeDisplay.comp.glsl
#version 450

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0, r32ui)   uniform readonly  uimage2D cellsIn;
layout(set = 0, binding = 3, rgba16f) uniform writeonly image2D  sceneImage;

void main()
{
    ivec2 pixel  = ivec2(gl_GlobalInvocationID.xy);
    ivec2 target = imageSize(sceneImage);
    if (pixel.x >= target.x || pixel.y >= target.y) { return; }   // no barrier() here: returning is fine

    // Fit the whole grid in the window with square cells, centred. The window's
    // size changes how big a cell is, never how many there are.
    ivec2 grid   = imageSize(cellsIn);
    float scale  = min(float(target.x) / float(grid.x), float(target.y) / float(grid.y));   // pixels per cell
    vec2  margin = 0.5 * (vec2(target) - vec2(grid) * scale);
    vec2  cell   = (vec2(pixel) + 0.5 - margin) / scale;

    // Linear values: the composite pass is the only sRGB encoder.
    vec3 color = vec3(0.0);                                          // outside the grid
    if (all(greaterThanEqual(cell, vec2(0.0))) && all(lessThan(cell, vec2(grid))))
    {
        uint age = imageLoad(cellsIn, ivec2(cell)).r;
        float older = clamp(float(age) / 32.0, 0.0, 1.0);
        color = (age == 0u) ? vec3(0.01)                                       // dead
                            : mix(vec3(1.0, 0.6, 0.1), vec3(0.1, 0.3, 1.0), older);   // newborn to old
    }
    imageStore(sceneImage, pixel, vec4(color, 1.0));
}
```

This is the shader that makes the simulation **resolution-independent**. The
grid is 300 x 170 cells whatever the window is. The window decides only how
many pixels a cell covers (`scale`, the same in x and y so cells stay square) and
how wide the black margins are. Resize the window to anything, including odd
sizes, very tall, or very wide, and the same cells are drawn, centred,
letterboxed. The `rgba16f` qualifier matches the scene target's format, and the
colors are linear (Chapter 08 section 4): the composite pass encodes them.
`ivec2(cell)` truncates toward zero, which equals `floor` here because `cell` is
non-negative inside the grid.

### The barriers on the scene image, both directions

**This is `RecordDisplay`**, the last thing `Record` does.

```cpp
void LifeDemo::RecordDisplay(VkCommandBuffer commandBuffer, const SceneTargets& targets)
{
    // Chapter 08's contract: the image arrives last read by the composite pass,
    // and the display pass overwrites every pixel.
    transitionImage(commandBuffer, targets.colorImage,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_displayPipeline);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_pipelineLayout,
                            0, 1, &m_sets[m_current], 0, nullptr);
    vkCmdDispatch(commandBuffer,
                  groupCount(targets.extent.width, GROUP_SIZE),
                  groupCount(targets.extent.height, GROUP_SIZE), 1);

    // ...and hand it back: GENERAL to SHADER_READ_ONLY_OPTIMAL, visible to the
    // composite's fragment shader.
    handBackSceneTarget(commandBuffer, targets, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
}
```

Into compute, the return trip from last frame's composite (the "Sampled result
handed back to compute" row of Chapter 04's appendix):

- **Q1:** last frame's composite pass sampled this image in its
  `FRAGMENT_SHADER`; this frame's `COMPUTE_SHADER` writes must wait for it.
- **Q2:** that was a read, which leaves nothing to flush, so the source access is
  `NONE`. The destination is `SHADER_STORAGE_WRITE`.
- **Q3:** `UNDEFINED` to `GENERAL`. Storage access needs `GENERAL`, and
  `UNDEFINED` lets the driver discard the old contents, which is correct only
  because the display pass writes every pixel. It is also the right old layout
  on the first frame after the engine recreates the target.

Out to graphics, through Chapter 09's `handBackSceneTarget` (the "Compute
result sampled by a later shader" row of Chapter 04's appendix):

- **Q1:** the display's `COMPUTE_SHADER` work before the composite's
  `FRAGMENT_SHADER`.
- **Q2:** `SHADER_STORAGE_WRITE` made available, and made visible to
  `SHADER_SAMPLED_READ`. These are different accesses even though both are
  shaders: synchronization2 split "shader read" into sampled and storage reads
  so the driver can flush exactly the caches involved.
- **Q3:** `GENERAL` to `SHADER_READ_ONLY_OPTIMAL`, the layout the composite's
  descriptor declares. `GENERAL` would also be legal to sample from, but the
  composite set was written for `SHADER_READ_ONLY_OPTIMAL`, and the read-only
  layout lets the driver compress.

The source half of the hand-back is what this demo did last, so you pass it. The
destination half is the composite pass and never changes, so the helper fixes
it. The display reads the cells written by the frame's last step, and the
barrier at the end of `RecordStep` already ordered that.

### `Resize`: keeping binding 3 pointed at the right image

**This is `Resize`.** The scene image belongs to the engine, which recreates it
whenever the swapchain is recreated. Chapter 09 calls `Resize` after every
`Setup` and after every recreation, behind a `vkDeviceWaitIdle`. That makes it
the one place where binding 3 is written, and the one time it is safe to write
it:

```cpp
InitializationResult LifeDemo::Resize(const SceneTargets& targets)
{
    // Chapter 09 calls this after every Setup and after every swapchain
    // recreation, behind a vkDeviceWaitIdle, so rewriting the sets is safe.
    const VkDescriptorImageInfo sceneImage{
        .imageView   = targets.colorView,
        .imageLayout = VK_IMAGE_LAYOUT_GENERAL,   // the layout the display pass writes it in
    };
    for (VkDescriptorSet set : m_sets)
    {
        const VkWriteDescriptorSet write{
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = set,
            .dstBinding      = 3,
            .descriptorCount = 1,
            .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
            .pImageInfo      = &sceneImage,
        };
        vkUpdateDescriptorSets(m_vulkan.device, 1, &write, 0, nullptr);
    }
    return InitializationResult::success();
}
```

Nothing else in Life depends on the window: the cells, the statistics, and the
pipelines are all independent of it. That is the other half of being
resolution-independent. A window-sized resource would be rebuilt here.

Between `Setup` and the first `Resize`, binding 3 is unwritten. That is legal,
because a descriptor only has to be valid when a dispatch that uses it runs, and
`Resize` always comes before the first `Record`.

### When compute feeds the vertex stage

Life's compute output reaches graphics as an image a fragment shader samples.
The other common route is something the vertex stage reads. Chapter 04's
appendix collects these rows; here are the three the later chapters use:

| Compute wrote... | ...and the draw reads it as | dstStage / dstAccess | Usage it needs |
| --- | --- | --- | --- |
| A storage buffer the vertex shader indexes (`gl_InstanceIndex`) — particles (21), grass (25-27) | a `readonly` storage buffer | `VERTEX_SHADER` / `SHADER_STORAGE_READ` | `STORAGE_BUFFER` |
| Indirect draw or dispatch arguments (21, 26) | the command's parameters | `DRAW_INDIRECT` / `INDIRECT_COMMAND_READ` | `STORAGE_BUFFER \| INDIRECT_BUFFER` |
| An image the vertex shader samples (the ocean's displacement, 29) | a sampled image | `VERTEX_SHADER` / `SHADER_SAMPLED_READ`, layout to `SHADER_READ_ONLY_OPTIMAL` | (image) `STORAGE \| SAMPLED` |

The source is always `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE`. Every row needs
its return trip next frame, from the reading stage with `NONE` back to
`COMPUTE_SHADER`, unless the buffer is duplicated per frame in flight. Two traps:

- Vertex input is not "the vertex shader". Fetching vertex attributes and
  indices are stages of their own (`VERTEX_ATTRIBUTE_INPUT`, `INDEX_INPUT`),
  before `VERTEX_SHADER`, so a barrier to `VERTEX_SHADER` does not cover a
  compute-written vertex or index buffer. The appendix's "Compute wrote a
  vertex buffer" row has the right stage.
- A storage buffer the vertex shader reads must be declared `readonly`.
  Writing storage memory from vertex shaders needs the
  `vertexPipelineStoresAndAtomics` feature, which the tutorial does not enable,
  and validation rejects a vertex-stage storage buffer that lacks the
  `NonWritable` decoration.

And the std430 trap from section 8: a compute shader that writes Chapter 11's
48-byte vertices through a std430 struct writes them at the wrong offsets.

---

## 11. The frame, in order

**This is `Record`**, in place of the checkpoint's. It runs once per frame,
after Chapter 09 waited on this slot's fence, with the frame's command buffer
already begun. Every piece it calls was written in an earlier section, so it
reads as the chapter's outline:

```cpp
void LifeDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    ReadStatistics(frame.frameIndex);                     // section 9: what this slot copied last time

    const int  steps = m_settings.paused ? 0 : m_settings.stepsPerFrame;
    const bool count = steps > 0;

    // Section 5: the return trip. Last frame's display may still be reading the
    // cells; this frame's first dispatch must not write them before it finishes.
    computeToComputeBarrier(commandBuffer);

    if (count) { RecordClearStatistics(commandBuffer); }  // section 8
    if (m_settings.reseed)                                 // section 3
    {
        RecordSeed(commandBuffer);
        m_settings.reseed = false;
    }
    for (int step = 0; step < steps; ++step)
    {
        RecordStep(commandBuffer, step == steps - 1);      // sections 5-8; only the last one counts
    }
    if (count) { RecordReadback(commandBuffer, frame.frameIndex); }   // section 9
    RecordDisplay(commandBuffer, frame.targets);                       // section 10
}
```

Read top to bottom, it is the chapter: read last time's numbers, return-trip
barrier, zero the counters, seed, step, copy the counters out, draw, hand back.
Every write has a barrier before its first reader and before its next writer.
Only the last step counts, because the statistics describe the generation on
screen, and counting every step would mean resetting between steps.

Note what is *not* here. There is no `beginScenePass`, because Life never
rasterizes. Nothing waits on the swapchain either: the frame's submit waits for
`imageAvailable` only at `COLOR_ATTACHMENT_OUTPUT` (Chapter 04 section 4), and
none of these commands run in that stage, so the whole simulation can run
before the swapchain image is even acquired.

### The panel

**This is `Update` and `drawLifePanel`**, which replace the checkpoint's empty
`Update`. The panel follows Chapter 07 section 9: a free function that edits
plain settings and knows nothing about Vulkan. Life has no camera, so Chapter 09
section 6's `beginDemoPanel` opens it under "Frame". `Record` acts on what it
changed. Picking a pattern, moving the density
slider, and the button all request a reseed, because each makes the current
grid stale.

```cpp
// Section 11. Edits the settings and shows the statistics; Record acts on both.
// Inside the namespace because it names the demo's types; static because only
// this file calls it.
static void drawLifePanel(LifeSettings& settings, const LifeStatistics& statistics, uint64_t generation)
{
    if (debug_panels::beginDemoPanel("Life", debug_panels::DemoPanelSlot::BelowFrame))
    {
        ImGui::Text("Generation  %llu", static_cast<unsigned long long>(generation));
        ImGui::Text("Population  %u", statistics.population);
        ImGui::Text("Births      %u", statistics.births);
        ImGui::Text("Deaths      %u", statistics.deaths);
        ImGui::TextDisabled("Counted on the GPU, read back %u frames later.", FRAMES_IN_FLIGHT);

        ImGui::SeparatorText("Simulation");
        ImGui::Checkbox("Paused", &settings.paused);
        ImGui::SliderInt("Steps per frame", &settings.stepsPerFrame, 1, 16);

        ImGui::SeparatorText("Seed");
        settings.reseed |= ImGui::Combo("Pattern", &settings.pattern, "Random soup\0Glider\0");
        settings.reseed |= ImGui::SliderFloat("Density", &settings.density, 0.05f, 0.95f);
        settings.reseed |= ImGui::Button("Reseed");
    }
    ImGui::End();
}
```

```cpp
void LifeDemo::Update(const FrameInput& /*input*/)
{
    drawLifePanel(m_settings, m_latest, m_generation);
}
```

`drawLifePanel` sits inside `pf::demos::life`, after `using namespace
vulkan_graphics;` (which is where `FRAMES_IN_FLIGHT` comes from), as a `static`
function. It names the demo's types, so it cannot be above the namespace block
like `querySubgroupProperties`, and `static` keeps it out of the linker's sight
the same way.

"Steps per frame" is the honest speed control. Frame rate is the display's
business, so a simulation that should run faster runs more steps per frame
rather than more frames.

---

## 12. Teardown, and registering the demo

**This is `Teardown`.** Chapter 09 waited for the device before calling it. Undo
`Setup` in reverse; every handle is reset so that the next `Setup` starts clean,
and the CPU state (`m_settings`) is deliberately left alone.

```cpp
void LifeDemo::Teardown()
{
    // Chapter 09 waited for the device. Reverse order of Setup; Vulkan's destroy
    // calls accept null handles, so a partial Setup is safe too.
    vkDestroyPipeline(m_vulkan.device, m_displayPipeline, nullptr);
    vkDestroyPipeline(m_vulkan.device, m_stepPipeline, nullptr);
    vkDestroyPipeline(m_vulkan.device, m_seedPipeline, nullptr);
    vkDestroyPipelineLayout(m_vulkan.device, m_pipelineLayout, nullptr);
    vkDestroyDescriptorPool(m_vulkan.device, m_descriptorPool, nullptr);   // frees both sets
    vkDestroyDescriptorSetLayout(m_vulkan.device, m_setLayout, nullptr);

    for (AllocatedBuffer& readback : m_readback)
    {
        destroyBuffer(m_vulkan, readback);
    }
    destroyBuffer(m_vulkan, m_statistics);

    for (size_t i = 0; i < m_cellImages.size(); ++i)
    {
        vkDestroyImageView(m_vulkan.device, m_cellViews[i], nullptr);
        vmaDestroyImage(m_vulkan.allocator, m_cellImages[i], m_cellAllocations[i]);   // null image: no-op
    }

    m_displayPipeline = m_stepPipeline = m_seedPipeline = VK_NULL_HANDLE;
    m_pipelineLayout  = VK_NULL_HANDLE;
    m_descriptorPool  = VK_NULL_HANDLE;
    m_setLayout       = VK_NULL_HANDLE;
    m_sets            = {};
    m_cellImages      = {};
    m_cellAllocations = {};
    m_cellViews       = {};
}
```

The VMA calls need no guard: Chapter 09 calls `Teardown` only after `Setup` has
copied the context, so the allocator exists. A leaked allocation shows up as an
assertion in `vmaDestroyAllocator` at shutdown, which makes "switch to Life and
back, then quit" a free leak check.

**Registering it** is Chapter 09's one line in `Source/SandboxGame/Main.cpp`,
plus its include:

```cpp
#include "PillowFort/Demos/Life/LifeDemo.h"
```

```cpp
    demoList.push_back(std::make_unique<demos::life::LifeDemo>());               // Chapter 20
```

It goes after the last demo already in the list, so the picker lists demos in
reading order.

Then rerun `GenerateProjects.bat`. `LifeDemo.cpp` and the three `.comp.glsl`
shaders are new files, and premake's globs see them only on regeneration: the
C++ glob for the first, Chapter 06's shader glob for the rest. The two headers
and `Random.glsl` are compiled through the files that include them.

---

## When it does not work

| Symptom | Likely cause |
| --- | --- |
| Garbage or stripes along the right or bottom edge | A missing bounds check, or a truncating `count / groupSize` instead of `groupCount` |
| Hang, or a device-lost, when a workgroup is partly outside the grid | An early `return` before `barrier()` (section 6) |
| Patterns tear, or differ between runs at the same seed | A missing barrier between steps, or between the last step and the display. With the heuristic on, sync validation says which |
| Validation is silent, but removing a step barrier changes nothing it reports | `syncval_shader_accesses_heuristic` is off: Chapter 02's second layer setting is missing, or an override turned it off (section 5) |
| Image is black, and validation reports a format mismatch | The GLSL format qualifier does not match the view (`r32ui` vs `R32_UINT`, `rgba16f` vs the scene target) |
| Population is far too high, or grows every frame | The counters are not reset (the fill, or its barriers), or every step counts instead of the last |
| Population is 0 while the grid is visibly alive | Reading the readback buffer before its fence, or reading in `Update`; or the `HOST` barrier is missing on a driver that needs it |
| Population flickers while paused | A stale readback slot re-read: the `m_readbackPending` flag is missing |
| Cells are rectangles, or the grid stretches with the window | Separate x and y scales in the display shader |
| Works at one window size, garbage after resizing | Binding 3 still points at the old scene view: it must be rewritten in `Resize` |
| `Setup` fails with "subgroup arithmetic" | The device lacks `VK_SUBGROUP_FEATURE_ARITHMETIC_BIT` in compute. Replace `subgroupAdd` with one `atomicAdd` per invocation |

---

## Exit check

- [ ] Rerun `GenerateProjects.bat`, build, and pick **Life (compute)** in the
      demo picker. The log shows the subgroup size: 8 on lavapipe, 32 or 64 on a
      GPU.
- [ ] A random soup evolves into still lifes (blue, old), blinkers, and the
      occasional glider (orange, young), with no artefacts at any edge.
- [ ] Choose **Glider**. With 16 steps per frame it crosses the grid, wraps at
      every edge, and the population stays exactly **5** forever. Births and
      deaths stay equal.
- [ ] Resolution-independent: resize to an odd size, then very tall, then very
      wide. The same 300 x 170 grid is drawn every time, centred, with square
      cells and black margins, and the simulation continues where it was.
- [ ] Pause, then press **Reseed** several times. Each reseed shows a new soup,
      and the statistics hold still while paused.
- [ ] Synchronization validation, with the shader-access heuristic on, is
      silent through all of the above, and through switching to another demo and
      back. Quitting reports no leaked VMA allocation.
- [ ] **Positive control.** Delete the `computeToComputeBarrier(commandBuffer)`
      call in `RecordStep`. The first frame must report
      `SYNC-HAZARD-READ-AFTER-WRITE` on a `vkCmdDispatch`: one step's or the
      display's storage read of an image the previous dispatch wrote. If it
      reports nothing, the shader-access setting is off (section 5), and every
      "silent" above proves nothing. Put the barrier back.

Next: [21 — GPU Particles](21-GPU-Particles.md)
