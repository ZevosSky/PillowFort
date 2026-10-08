# 21 — GPU Particles

**Goal:** a fountain of tens of thousands of particles that are born, move,
bounce, and die entirely on the GPU, drawn with one indirect draw whose
instance count the CPU never sets. Its panel shows the live count, read back
without stalling, and what each pass costs on the GPU.

**ROADMAP:** step 21+ — a demo, in `Source/PillowFort/Demos/Particles/` with
shaders under `Shaders/Particles/`.

**Module:** the demo is `pf::demos::particles`. Three small engine additions
other chapters use: `BlendMode::PremultipliedAlpha` in `GraphicsPipeline`
(section 5), GLSL mirrors of Vulkan's indirect command structs in
`Shaders/Include/SharedShaderTypes.h` (section 2), and random numbers in
`Shaders/Include/Random.glsl` (section 3).

**Prerequisites:**

- Chapter 20, all of it, and especially section 3 (dispatch sizing), 5 (barriers
  between dispatches, and the table of what sync validation can see), 8
  (storage buffers, std430, atomics), and 9 (reading results back without
  stalling).
- Chapter 04 section 5 — the three questions, and that a barrier orders
  everything before it on the queue, last frame's command buffer included,
  against everything after it. Every return trip here depends on that.
- Chapter 19 sections 6 and 7 — the indirect draw, written by the CPU, and what
  changes when the GPU writes it. This chapter is that change.
- Chapter 10 sections 6 and 12 (the camera controls), 7 (`FrameData` and
  `SceneRenderer`'s set 0), and 9 (the depth target, what `endScenePass` leaves
  it in, and who owns a later reader's return trip).
- Chapter 09 section 4 — the scene part of the frame belongs to the demo, and a
  demo may open its own rendering scope between `endScenePass` and
  `handBackSceneTarget`.
- Chapter 18 — pipelines drawn inside the scene pass take the scene's sample
  count; after the pass, the scene's color and depth are single-sample
  (resolved). Section 5 here finishes the story of section 5 there: why the
  single-sample depth's barrier names the fragment-test stages.
- Chapter 06 section 8 (`GraphicsPipelineDesc` and `BlendMode`), and Chapter 08
  section 4 (colors from ImGui are sRGB).

Chapter 16's tone curve is worth having on: additive particles stack well past
1.0, and the raw mode clips them to white.

---

## The problem particles pose

A particle system is many small things, each born somewhere, moving under a few
forces, fading, and dying. A CPU system keeps them in an array, updates them in a
loop, and uploads their positions every frame. That is fine for a few thousand
particles. At a hundred thousand the upload alone is megabytes per frame, and
the loop costs milliseconds of CPU for work that is trivially parallel.

On the GPU the state never leaves video memory and the update is a compute
dispatch, so the numbers stop mattering. What does get hard is the one thing
the CPU did for free: **knowing how many there are.** Particles are born and
die every frame. On the CPU, death is an `erase` and birth a `push_back`. On the
GPU thousands of invocations run at once, none knows what the others are doing,
and the CPU learns what happened only after the frame is over.

The standard answer, used in most engines since AMD's "Compute-based GPU
particle systems" talk (GDC 2014), has four parts, and this chapter builds each
one:

- **A fixed pool** of particle slots, allocated once (section 1).
- **A dead list**, a stack of free slot numbers. Emitting pops one; dying pushes
  one back. **Two alive lists**, so that each frame the survivors are packed into
  the other list with no gaps. Atomic counters keep all three consistent while
  thousands of invocations edit them at once (sections 2 and 3).
- **Indirect dispatches and an indirect draw**: the GPU writes the size of its
  own work, so the CPU never has to know the count (sections 2 and 4).
- **A delayed readback** of the counters for the panel, Chapter 20's pattern
  (section 7).

One frame, in order:

```text
 Begin (1 invocation)      emit count = min(asked, free); dispatch sizes for emit and simulate
   │ barrier
 Emit (indirect)           pop a free slot, start a particle, append it to alive[current]
   │ barrier
 Simulate (indirect)       age, move, bounce; dead -> dead list, alive -> alive[next]
   │ barrier
 End (1 invocation)        draw arguments: 6 vertices x alive[next] instances
   │ barrier
 copy the counters out     for the panel, two frames from now
 scene pass                the ground, with depth
 particle pass             one vkCmdDrawIndirect, blended, depth read-only
```

### What you are actually writing

**This is `ParticlesDemo.h`**, the map of the chapter. Every private function
names the section that writes it.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 21: GPU particles - emitted, simulated, and counted in compute, drawn indirectly
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Particles/ParticlesDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/Transform.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"
#include "Particles/ParticleTypes.h"

#include <array>
#include <cstdint>

namespace pf::demos::particles {

// What the panel edits (section 7). CPU state: it survives Teardown and Setup.
// Colors are sRGB here, as the swatches show them; Record converts them.
struct ParticleSettings
{
    float emitRate          = 4000.0f;  // particles per second
    float speed             = 7.0f;     // metres per second
    float speedVariation    = 0.2f;     // +- fraction
    float spreadDegrees     = 15.0f;    // the cone's half-angle
    float lifetime          = 3.0f;     // seconds, the average
    float lifetimeVariation = 0.3f;     // +- fraction
    float gravity           = 9.81f;    // metres per second squared, downwards
    float drag              = 0.3f;     // per second
    float restitution       = 0.4f;     // vertical speed kept in a bounce
    float friction          = 0.3f;     // horizontal speed lost in a bounce
    float startColor[4]     = { 1.0f, 0.75f, 0.35f, 1.0f };
    float endColor[4]       = { 0.9f, 0.2f, 0.05f, 0.0f };
    float startSize         = 0.12f;    // metres
    float endSize           = 0.04f;
    int   blend             = 0;        // 0 additive, 1 premultiplied alpha
    int   maxParticles      = 65536;    // how much of the pool is in use
    bool  paused            = false;
};

// GPU milliseconds per pass, from timestamp queries (section 8).
struct ParticleTimings
{
    float emit     = 0.0f;   // begin + emit
    float simulate = 0.0f;
    float end      = 0.0f;   // end + the counter readback copy
    float ground   = 0.0f;   // the scene pass
    float draw     = 0.0f;   // the particles
};

class ParticlesDemo : public Demo
{
public:
    ParticlesDemo();   // CPU only: puts the camera somewhere useful

    const char*          Name() const override { return "Particles"; }
    InitializationResult Setup(const DemoContext& context) override;                    // sections 1-8
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override; // nothing to do
    void                 Update(const FrameInput& input) override;                      // section 7
    void                 Record(const RecordContext& frame) override;                   // section 6
    void                 Teardown() override;                                           // section 9
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }

private:
    InitializationResult CreateBuffers();            // section 1
    InitializationResult CreateDescriptors();        // section 1
    InitializationResult CreateComputePipelines();   // section 4
    InitializationResult CreateDrawPipelines();      // section 5
    InitializationResult CreateTimestamps();         // section 8
    void RecordCompute(VkCommandBuffer commandBuffer, uint32_t frameIndex);              // section 4
    void RecordParticles(VkCommandBuffer commandBuffer, const RecordContext& frame);     // section 5
    void ReadResults(uint32_t frameIndex);                                               // sections 7 and 8
    void WriteTimestamp(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t which);

    // The pool's size. The panel's "Max particles" uses part of it, so changing
    // that needs no new buffers - only a reset (section 3).
    static constexpr uint32_t PARTICLE_CAPACITY = 1u << 20;
    static constexpr uint32_t TIMESTAMP_COUNT   = 6;   // per frame in flight (section 8)

    vulkan_graphics::VulkanContext m_vulkan;            // Chapter 09's DemoContext, copied
    VkPipelineCache                m_pipelineCache = VK_NULL_HANDLE;
    vulkan_graphics::SceneFormats  m_formats;
    vulkan_graphics::SceneRenderer m_sceneRenderer;     // Chapter 10: set 0, the camera

    // Section 1: one of each, shared by both frames in flight.
    vulkan_graphics::AllocatedBuffer m_particles;       // Particle[PARTICLE_CAPACITY]
    vulkan_graphics::AllocatedBuffer m_deadList;        // uint[PARTICLE_CAPACITY]
    vulkan_graphics::AllocatedBuffer m_aliveLists;      // uint[2 * PARTICLE_CAPACITY]
    vulkan_graphics::AllocatedBuffer m_counters;        // ParticleCounters
    vulkan_graphics::AllocatedBuffer m_indirect;        // ParticleIndirect
    std::array<vulkan_graphics::AllocatedBuffer, vulkan_graphics::FRAMES_IN_FLIGHT> m_readback;
    std::array<bool, vulkan_graphics::FRAMES_IN_FLIGHT>                              m_readbackPending{};
    std::array<uint32_t, vulkan_graphics::FRAMES_IN_FLIGHT>                          m_readbackList{};

    VkDescriptorSetLayout m_setLayout      = VK_NULL_HANDLE;   // set 0 for compute, set 1 for drawing
    VkDescriptorPool      m_descriptorPool = VK_NULL_HANDLE;
    VkDescriptorSet       m_set            = VK_NULL_HANDLE;

    // Section 4.
    VkPipelineLayout m_computeLayout    = VK_NULL_HANDLE;
    VkPipeline       m_resetPipeline    = VK_NULL_HANDLE;
    VkPipeline       m_beginPipeline    = VK_NULL_HANDLE;
    VkPipeline       m_emitPipeline     = VK_NULL_HANDLE;
    VkPipeline       m_simulatePipeline = VK_NULL_HANDLE;
    VkPipeline       m_endPipeline      = VK_NULL_HANDLE;

    // Section 5.
    VkPipelineLayout          m_groundLayout   = VK_NULL_HANDLE;
    VkPipeline                m_groundPipeline = VK_NULL_HANDLE;
    VkPipelineLayout          m_drawLayout     = VK_NULL_HANDLE;
    std::array<VkPipeline, 2> m_drawPipelines{};            // [additive, premultiplied alpha]

    // Section 8.
    VkQueryPool                                          m_queryPool       = VK_NULL_HANDLE;
    double                                               m_timestampPeriod = 0.0;   // nanoseconds per tick
    uint64_t                                             m_timestampMask   = 0;
    std::array<bool, vulkan_graphics::FRAMES_IN_FLIGHT>  m_timestampsPending{};

    // CPU state: survives Teardown, so switching back finds everything as it was.
    ParticleSettings      m_settings;
    scene::Camera         m_camera;
    scene::Transform      m_cameraTransform;
    scene::CameraControls m_controls;
    float                 m_time            = 0.0f;
    float                 m_deltaTime       = 0.0f;
    float                 m_emitCarry       = 0.0f;   // the fraction of a particle not yet emitted
    uint32_t              m_frameNumber     = 0;      // seeds the GPU's random numbers
    uint32_t              m_currentList     = 0;      // the alive list holding the live particles
    bool                  m_resetRequested  = true;
    ParticleCounters      m_latest{};                 // read back, FRAMES_IN_FLIGHT frames old
    uint32_t              m_latestList      = 0;      // which of its alive counts was drawn
    ParticleTimings       m_timings;
};

} // namespace pf::demos::particles
```

Everything the panel edits lives in `ParticleSettings`, and the camera lives in
the demo object, so switching to another demo and back keeps both (Chapter
09). `m_cameraTransform` is the camera's pose, kept apart from `scene::Camera`
the way Chapter 12 arranges it, so this code does not change when the camera
becomes a node.

**This is `Setup`**, in dependency order:

```cpp
InitializationResult ParticlesDemo::Setup(const DemoContext& context)
{
    m_vulkan        = context.vulkan;
    m_pipelineCache = context.pipelineCache;
    m_formats       = context.formats;

    if (auto result = m_sceneRenderer.Initialize(m_vulkan, m_pipelineCache, m_formats); !result)
    {
        return result;
    }
    if (auto result = CreateBuffers(); !result)          { return result; }   // section 1
    if (auto result = CreateDescriptors(); !result)      { return result; }   // section 1
    if (auto result = CreateComputePipelines(); !result) { return result; }   // section 4
    if (auto result = CreateDrawPipelines(); !result)    { return result; }   // section 5
    if (auto result = CreateTimestamps(); !result)       { return result; }   // section 8

    // The buffers hold garbage: the first Record resets the pool before anything
    // reads it. Nothing has been read back or timed yet.
    m_resetRequested = true;
    m_readbackPending.fill(false);
    m_timestampsPending.fill(false);
    return InitializationResult::success();
}
```

`SceneRenderer` comes first because two pipeline layouts need its set 0 layout
(section 5). There is no `Resize` work: the demo owns nothing sized to the window.

### Where everything lands

```text
Source/PillowFort/VulkanGraphics/
  GraphicsPipeline.h/.cpp   + BlendMode::PremultipliedAlpha                     section 5
Shaders/Include/
  SharedShaderTypes.h       + DispatchIndirectCommand, DrawIndirectCommand,
                              DrawIndexedIndirectCommand                        section 2
  Random.glsl               + seedRandom, randomFloat                           section 3
Source/PillowFort/Demos/Particles/
  ParticlesDemo.h/.cpp      the demo
Shaders/Particles/
  ParticleTypes.h           C++/GLSL twins                                      sections 1 and 2
  ParticleBuffers.glsl      the compute passes' view of the buffers             section 3
  ParticleReset.comp.glsl   every slot free                                     section 3
  ParticleBegin.comp.glsl   this frame's counts and dispatch sizes              section 3
  ParticleEmit.comp.glsl    new particles                                       section 3
  ParticleSimulate.comp.glsl  age, move, bounce, sort into the lists            section 3
  ParticleEnd.comp.glsl     the draw's arguments                                section 3
  Particle.vert.glsl        camera-facing quads                                 section 5
  Particle.frag.glsl        soft round dots, premultiplied                      section 5
  Ground.vert.glsl, Ground.frag.glsl   the floor they bounce on                 section 5
Source/SandboxGame/Main.cpp + one registration line                             section 9
```

```text
ParticlesDemo.cpp
  includes
  static_asserts on the indirect command mirrors                 section 2
  static srgbToLinear(value)                                     section 5
  static timestampValidBits(physicalDevice)                      section 8
  namespace pf::demos::particles {
      using namespace vulkan_graphics;
      static drawParticlePanel(...)                              section 7
      ParticlesDemo::ParticlesDemo                               section 7
      ParticlesDemo::Setup                                       above
      ParticlesDemo::CreateBuffers, CreateDescriptors            section 1
      ParticlesDemo::CreateComputePipelines                      section 4
      ParticlesDemo::CreateDrawPipelines                         section 5
      ParticlesDemo::CreateTimestamps                            section 8
      ParticlesDemo::Resize                                      (nothing)
      ParticlesDemo::Update                                      section 7
      ParticlesDemo::WriteTimestamp                              section 8
      ParticlesDemo::ReadResults                                 sections 7 and 8
      ParticlesDemo::RecordCompute                               section 4
      ParticlesDemo::RecordParticles                             section 5
      ParticlesDemo::Record                                      section 6
      ParticlesDemo::Teardown                                    section 9
  }
```

`ParticlesDemo.cpp` includes `ParticlesDemo.h`,
`PillowFort/DebugPanels/DemoPanel.h`,
`PillowFort/VulkanGraphics/GraphicsPipeline.h`,
`PillowFort/VulkanGraphics/VulkanBarriers.h`, `<imgui.h>`, `<algorithm>`,
`<cmath>`, `<cstddef>`, and `<vector>`.

---

## 1. The pool

**One particle is 32 bytes.** Position, age, velocity, lifetime: two `vec3`s and
two scalars. Chapter 08's first habit says no `vec3` in a shared struct, and
Chapter 20 section 8 showed why. Here the scalars ride in the `w` components, so
the struct is two `vec4`s, identical in C++ and std430, and an array of them has
no padding at all:

```c
/* One particle (std430, 32 bytes). Two vec4s, with the scalars packed in w. */
struct Particle
{
    vec4 positionAndAge;        /*  0: xyz metres, w seconds since it was emitted */
    vec4 velocityAndLifetime;   /* 16: xyz metres per second, w seconds it lives */
};
```

It is the first struct of **`ParticleTypes.h`**, the demo's C++/GLSL twins in
Chapter 09's `<Name>Types.h` shape. Section 2 shows the header whole.

Size and color are not stored. They follow from age and lifetime by a curve
(section 5), so storing them would cost bandwidth twice a frame for nothing.
What *is* per particle and not derivable, such as a random variation in size,
comes from hashing the particle's slot number, which stays the same for its
whole life.

### Capacity, and why there is one copy of everything

**This is `CreateBuffers`.** The pool is sized once, to `PARTICLE_CAPACITY`
(2^20, about a million), and the panel's "Max particles" uses the first part of
it. Changing the limit then needs no new buffers, only a reset (section 3). At 32
bytes a particle plus 12 bytes of list entries, the capacity costs 44 MB, far
under the guaranteed 128 MB storage-buffer range.

```cpp
InitializationResult ParticlesDemo::CreateBuffers()
{
    // Device-local, one of each: only the GPU touches them, and particles live
    // from frame to frame, so one copy carries the state forward.
    const struct
    {
        AllocatedBuffer*   buffer;
        VkDeviceSize       size;
        VkBufferUsageFlags usage;
    } buffers[] = {
        { &m_particles,  sizeof(Particle) * PARTICLE_CAPACITY, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT },
        { &m_deadList,   sizeof(uint32_t) * PARTICLE_CAPACITY, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT },
        { &m_aliveLists, sizeof(uint32_t) * PARTICLE_CAPACITY * 2, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT },
        { &m_counters,   sizeof(ParticleCounters),
          VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT },    // copied out for the panel
        { &m_indirect,   sizeof(ParticleIndirect),
          VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT }, // compute writes, commands read
    };
    for (const auto& entry : buffers)
    {
        *entry.buffer = createBuffer(m_vulkan, entry.size, entry.usage, false);
        if (entry.buffer->buffer == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a particle buffer failed.");
        }
    }

    // Chapter 20 section 9's readback, one per frame in flight.
    for (AllocatedBuffer& readback : m_readback)
    {
        readback = createReadbackBuffer(m_vulkan, sizeof(ParticleCounters));
        if (readback.buffer == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a particle readback buffer failed.");
        }
    }
    return InitializationResult::success();
}
```

Two decisions in it need saying, and the first reverses a rule.

> **Jump:** Chapter 08's rule was one copy per frame in flight of anything the
> CPU writes every frame, so the CPU never writes a copy the GPU is still
> reading. These buffers get **one copy each**. Nothing here is written by the
> CPU, and particle state *persists*: frame N's simulate reads what frame N-1's
> wrote, so two copies would each go stale. The price of one copy is a barrier
> at the top of every frame, the return trip that keeps frame N's compute from
> overwriting what frame N-1's draw is still reading (section 4). Keep the test
> in mind, because the grass chapters apply it to every buffer they make:
> written by the CPU every frame, one copy per frame in flight; written by the
> GPU and carried from frame to frame, one copy and a return trip. Here only the
> readback buffers, which the CPU reads, are per frame in flight.

**Device-local, with the usage bits the uses need.** Every buffer is
`STORAGE_BUFFER`. The counters add `TRANSFER_SRC` because they are copied out for
the panel. The indirect-argument buffer adds `INDIRECT_BUFFER`, which is what lets
`vkCmdDispatchIndirect` and `vkCmdDrawIndirect` read it. Chapter 19's
CPU-written indirect buffer had `INDIRECT_BUFFER` and was host-visible; this one
is written by a shader, so it needs `STORAGE_BUFFER` too, and it is
device-local because the CPU never touches it.

### One set, bound twice

**This is `CreateDescriptors`.** The compute passes use all five buffers, one
more than the four storage buffers per shader stage that Vulkan guarantees, so
the function first asks the device for five. The vertex shader reads two of
them, the particles and the alive lists. Rather than two sets pointing at the
same buffers, there is one set whose layout makes those two bindings visible to
both stages. The compute pipelines bind it as set 0, and the drawing pipeline as
set 1, after `SceneRenderer`'s set 0.

```cpp
InitializationResult ParticlesDemo::CreateDescriptors()
{
    // The compute passes see all five buffers, and Vulkan guarantees only four storage
    // buffers per shader stage. Every desktop GPU has far more; ask rather than assume.
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(m_vulkan.physicalDevice, &properties);
    if (properties.limits.maxPerStageDescriptorStorageBuffers < 5)
    {
        return InitializationResult::failure("The particles need five storage buffers per shader stage.");
    }

    // One set, bound twice: at set 0 for the compute passes, and at set 1 for the
    // vertex shader, which reads the particles and the alive lists.
    const VkShaderStageFlags computeAndVertex = VK_SHADER_STAGE_COMPUTE_BIT | VK_SHADER_STAGE_VERTEX_BIT;
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,   // particles
          .descriptorCount = 1, .stageFlags = computeAndVertex },
        { .binding = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,   // dead list
          .descriptorCount = 1, .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding = 2, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,   // alive lists
          .descriptorCount = 1, .stageFlags = computeAndVertex },
        { .binding = 3, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,   // counters
          .descriptorCount = 1, .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding = 4, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,   // indirect arguments
          .descriptorCount = 1, .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
    };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = static_cast<uint32_t>(std::size(bindings)),
        .pBindings    = bindings,
    };
    if (vkCreateDescriptorSetLayout(m_vulkan.device, &setLayoutInfo, nullptr, &m_setLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the particles.");
    }

    const VkDescriptorPoolSize poolSize{ VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, static_cast<uint32_t>(std::size(bindings)) };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 1,
        .poolSizeCount = 1,
        .pPoolSizes    = &poolSize,
    };
    if (vkCreateDescriptorPool(m_vulkan.device, &poolInfo, nullptr, &m_descriptorPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the particles.");
    }

    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_descriptorPool,
        .descriptorSetCount = 1,
        .pSetLayouts        = &m_setLayout,
    };
    if (vkAllocateDescriptorSets(m_vulkan.device, &allocateInfo, &m_set) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the particles.");
    }

    // Binding i is buffers[i], whole. Written once: the buffers never change.
    const AllocatedBuffer* buffers[] = { &m_particles, &m_deadList, &m_aliveLists, &m_counters, &m_indirect };
    std::array<VkDescriptorBufferInfo, std::size(buffers)> infos{};
    std::array<VkWriteDescriptorSet, std::size(buffers)>   writes{};
    for (uint32_t i = 0; i < std::size(buffers); ++i)
    {
        infos[i] = VkDescriptorBufferInfo{ .buffer = buffers[i]->buffer, .offset = 0, .range = VK_WHOLE_SIZE };
        writes[i] = VkWriteDescriptorSet{
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = m_set,
            .dstBinding      = i,
            .descriptorCount = 1,
            .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
            .pBufferInfo     = &infos[i],
        };
    }
    vkUpdateDescriptorSets(m_vulkan.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
    return InitializationResult::success();
}
```

A descriptor set may be bound at different set numbers in different pipeline
layouts. All that matters is that each layout's slot holds this set layout.
`VK_WHOLE_SIZE` binds each buffer whole, which also makes the GLSL runtime arrays'
`length()` meaningful, though nothing here needs it.

---

## 2. Lists, counters, and the GPU deciding the count

> **Jump:** until now the CPU always knew how much work it was asking for: a grid
> size, a vertex count, a number of instances. From here the GPU decides. The
> number of particles alive this frame exists only in a GPU buffer, the dispatch
> that simulates them and the draw that shows them are sized from that buffer,
> and the CPU learns the number two frames later, if it asks. Keep in mind that
> any CPU-side number on the panel is a report about the past, never an input.

### The dead list: a stack of free slots

At the start every slot is free, and the dead list holds all their numbers,
`0..max-1`, with `deadCount = max`. To emit, an invocation **pops**:

```glsl
uint deadSlot = atomicAdd(counters.deadCount, uint(-1)) - 1u;
uint index    = deadList[deadSlot];
```

`atomicAdd` returns the value *before* the add, and adding `uint(-1)` subtracts
one in unsigned arithmetic. So every invocation gets a different old count, and
each takes the entry just below it. A thousand invocations popping at once get a
thousand different slots, in no particular order, and the count comes out
right. To die, an invocation **pushes**: `deadList[atomicAdd(counters.deadCount, 1u)] = index`.

Popping is safe only if there is something to pop. If two invocations popped
the last free slot, the count would go below zero and wrap to four billion. So
nobody emits blind: a single-invocation pass first sets `emitCount =
min(asked, deadCount)`, and exactly that many emit.

### The alive lists: compaction by appending

The simulate pass needs the live particles packed from 0, so that invocation `i`
can find the `i`-th one, and the draw needs the same thing for instance `i`.
Slots die in the middle of the pool, so the pool itself is never packed. A list
of live slot numbers is, if it is rebuilt every frame: simulate reads
`alive[current]`, and every survivor **appends** itself to `alive[next]` with
the same atomic trick, upwards. The new list holds exactly the survivors, with
no gaps. This is stream compaction, done as a side effect of the update.

The two lists swap roles every frame, which is why there are two. The new
particles of a frame are appended to `alive[current]` before simulate reads it,
so they are simulated, and drawn, in the frame they are born.

**The invariant.** After every frame, every slot is either on the dead list or on
`alive[next]`, so `alive + dead = max`. The panel shows both numbers; if they
ever stop adding up, a barrier is missing or a count was used before it was
final. The same invariant is why particles cannot overflow a list: each list
holds `max` entries, and there are never more than `max` particles. (The grass
chapters append into lists that *can* fill up, and they check before writing;
particles need not.)

### The counters and the indirect arguments

These are the rest of **`ParticleTypes.h`**, now whole:

```c
/* Shaders/Particles/ParticleTypes.h - Chapter 21's C++/GLSL twins. GLSL includes
   it as "ParticleTypes.h", C++ as "Particles/ParticleTypes.h". */
#ifndef PF_PARTICLE_TYPES_H
#define PF_PARTICLE_TYPES_H

#include "SharedShaderTypes.h"   /* vec4, uint, and the indirect command structs */

/* The 64-wide passes' local_size_x, and the C++ side's groupCount divisor: one
   number for both languages. */
#define PARTICLE_GROUP_SIZE 64

#ifdef __cplusplus
    namespace pf::demos::particles {
    using shared::vec4;
    using shared::uint;
    using shared::DispatchIndirectCommand;
    using shared::DrawIndirectCommand;
#endif

/* One particle (std430, 32 bytes). Two vec4s, with the scalars packed in w. */
struct Particle
{
    vec4 positionAndAge;        /*  0: xyz metres, w seconds since it was emitted */
    vec4 velocityAndLifetime;   /* 16: xyz metres per second, w seconds it lives */
};

/* The bookkeeping (std430). Changed by atomics, read back for the panel. */
struct ParticleCounters
{
    uint aliveCount[2];         /*  0: particles in alive list 0 and alive list 1 */
    uint deadCount;             /*  8: free slots on the dead list */
    uint emitCount;             /* 12: this frame's emissions, clamped to deadCount */
};

/* The indirect arguments (std430), written only by the begin and end passes. */
struct ParticleIndirect
{
    DispatchIndirectCommand emit;       /*  0: vkCmdDispatchIndirect, the emit pass */
    DispatchIndirectCommand simulate;   /* 12: vkCmdDispatchIndirect, the simulate pass */
    DrawIndirectCommand     draw;       /* 24: vkCmdDrawIndirect, the particles */
};

/* Push constants for every compute pass; each reads what it needs. */
struct ParticleSimulation
{
    vec4  emitterPosition;      /*  0: xyz metres; w unused */
    vec4  gravity;              /* 16: xyz metres per second squared; w = drag, per second */
    float deltaTime;            /* 32: seconds this step covers */
    float speed;                /* 36: metres per second at emission */
    float speedVariation;       /* 40: +- this fraction of speed */
    float spreadAngle;          /* 44: radians, the cone's half-angle around +Y */
    float lifetime;             /* 48: seconds, the average */
    float lifetimeVariation;    /* 52: +- this fraction of lifetime */
    float groundHeight;         /* 56: metres; the plane particles bounce on */
    float restitution;          /* 60: fraction of the vertical speed kept in a bounce */
    float friction;             /* 64: fraction of the horizontal speed lost in a bounce */
    uint  emitRequest;          /* 68: particles the CPU asks for this frame */
    uint  frameNumber;          /* 72: seeds this frame's random numbers */
    uint  currentList;          /* 76: 0 or 1, the alive list emit appends to and simulate reads */
    uint  maxParticles;         /* 80: the pool size in use; also each alive list's length */
    uint  padding0;
    uint  padding1;
    uint  padding2;
};

/* Push constants for drawing the particles. Colors are LINEAR. */
struct ParticleAppearance
{
    vec4  startColor;           /*  0: rgb at birth, a = opacity */
    vec4  endColor;             /* 16: rgb and opacity at the end of its life */
    float startSize;            /* 32: metres across, at birth */
    float endSize;              /* 36: metres across, at the end */
    uint  aliveList;            /* 40: which alive list to draw */
    uint  maxParticles;         /* 44: where alive list 1 starts */
};

/* Push constants for the ground the particles bounce on. */
struct GroundParameters
{
    float height;               /* 0: metres, the same as ParticleSimulation::groundHeight */
    float halfSize;             /* 4: metres from the centre to each edge */
    float padding0;
    float padding1;
};

#ifdef __cplusplus
    static_assert(sizeof(Particle) == 32, "Particle layout drifted.");
    static_assert(sizeof(ParticleCounters) == 16, "ParticleCounters layout drifted.");
    static_assert(offsetof(ParticleIndirect, simulate) == 12, "ParticleIndirect layout drifted.");
    static_assert(offsetof(ParticleIndirect, draw) == 24, "ParticleIndirect layout drifted.");
    static_assert(sizeof(ParticleIndirect) == 40, "ParticleIndirect layout drifted.");
    static_assert(sizeof(ParticleSimulation) == 96, "ParticleSimulation layout drifted.");
    static_assert(offsetof(ParticleSimulation, deltaTime) == 32, "ParticleSimulation layout drifted.");
    static_assert(sizeof(ParticleAppearance) == 48, "ParticleAppearance layout drifted.");
    static_assert(sizeof(GroundParameters) == 16, "GroundParameters layout drifted.");
    }
#endif

#endif
```

`PARTICLE_GROUP_SIZE` is a `#define` in the shared header so that the shaders'
`local_size_x` and C++'s `groupCount` divisor are one number, the improvement
Chapter 20 section 8's note on specialization constants pointed at.

**`ParticleCounters`** is the bookkeeping the atomics change. **`ParticleIndirect`**
holds three commands the GPU writes for itself: the emit dispatch's size, the
simulate dispatch's size, and the particle draw. They live in separate buffers on
purpose. The counters are hammered by atomics in the middle passes; the indirect
arguments are written only by the two single-invocation passes at either end.
Keeping them apart keeps every hazard on the indirect buffer to exactly two
barriers, and keeps the barriers easy to read (section 4).

The two push-constant blocks, `ParticleSimulation` for every compute pass and
`ParticleAppearance` for the draw, are 96 and 48 bytes, inside the 128-byte
budget. Each pass reads the fields it needs, as in Chapter 20.

### Commands a shader can write

`vkCmdDispatchIndirect` reads a `VkDispatchIndirectCommand`, three `uint32_t`s, at
an offset in a buffer. `vkCmdDrawIndirect` reads a `VkDrawIndirectCommand`: vertex
count, instance count, first vertex, first instance. For a shader to write them,
GLSL needs structs with the same fields in the same order. Particles and the
grass chapters both need them, so they go in **`SharedShaderTypes.h`**, after
the last struct and inside `pf::shared`:

```c
/* Chapter 21: Vulkan's indirect command structs, field for field, so a compute
   shader can write them. A demo's .cpp checks them against Vulkan's own with
   static_assert; this header does not include vulkan.h. */
struct DispatchIndirectCommand      /* VkDispatchIndirectCommand */
{
    uint x;
    uint y;
    uint z;
};

struct DrawIndirectCommand          /* VkDrawIndirectCommand */
{
    uint vertexCount;
    uint instanceCount;
    uint firstVertex;
    uint firstInstance;
};

struct DrawIndexedIndirectCommand   /* VkDrawIndexedIndirectCommand */
{
    uint indexCount;
    uint instanceCount;
    uint firstIndex;
    int  vertexOffset;
    uint firstInstance;
};

#ifdef __cplusplus
    static_assert(sizeof(DispatchIndirectCommand) == 12, "DispatchIndirectCommand layout drifted.");
    static_assert(sizeof(DrawIndirectCommand) == 16, "DrawIndirectCommand layout drifted.");
    static_assert(sizeof(DrawIndexedIndirectCommand) == 20, "DrawIndexedIndirectCommand layout drifted.");
    }
#endif
```

The namespace's closing brace moves down from `FrameData`'s asserts to here, so
the new structs are inside it. All of their members are 4-byte scalars, so std430
and C agree, and offsets into the buffer are multiples of 4, as the indirect
commands require. The header deliberately does not include `vulkan.h`, so the
check against Vulkan's own structs is in the demo, at the top of
`ParticlesDemo.cpp`:

```cpp
// File scope, above the namespace block. Section 2: the GLSL mirrors in
// SharedShaderTypes.h must match Vulkan's own structs, field for field.
static_assert(sizeof(pf::shared::DispatchIndirectCommand) == sizeof(VkDispatchIndirectCommand));
static_assert(sizeof(pf::shared::DrawIndirectCommand) == sizeof(VkDrawIndirectCommand));
static_assert(offsetof(pf::shared::DrawIndirectCommand, instanceCount) == offsetof(VkDrawIndirectCommand, instanceCount));
static_assert(sizeof(pf::shared::DrawIndexedIndirectCommand) == sizeof(VkDrawIndexedIndirectCommand));
```

A mirror that drifted from Vulkan's layout would make the GPU dispatch or draw a
garbage count, the kind of bug that hangs a machine rather than reporting
anything. The asserts make it a compile error.

**What changed from Chapter 19.** There, the CPU wrote `VkDrawIndexedIndirectCommand`s
into a host-visible buffer, one per frame in flight, in `PrepareDraws` (called
from `Record`), and needed no barrier, because host writes before
`vkQueueSubmit2` are visible to the submitted work. Only C++ touched those
commands, so Vulkan's own struct was all it needed; the mirrors above are the
first a shader sees. Here the producer is a compute shader, and Chapter 19
section 7 already named what follows from that:

| | Chapter 19 (CPU writes) | Here (GPU writes) |
| --- | --- | --- |
| Memory | host-visible, mapped | device-local |
| Usage | `INDIRECT_BUFFER` | `STORAGE_BUFFER \| INDIRECT_BUFFER` |
| Copies | one per frame in flight | one, plus a return-trip barrier |
| Barrier before the draw | none: the submit covers host writes | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` to `DRAW_INDIRECT \| VERTEX_SHADER` / `INDIRECT_COMMAND_READ \| SHADER_STORAGE_READ`, Chapter 19 section 7's row (section 4 adds the counters' copy) |
| Features | `multiDrawIndirect` and friends, for many draws | none: one draw, `firstInstance` 0 |

`DRAW_INDIRECT` is the stage in which *both* `vkCmdDrawIndirect` and
`vkCmdDispatchIndirect` read their arguments, and `INDIRECT_COMMAND_READ` is that
read. It is not a shader access, which is why a barrier that only names
`COMPUTE_SHADER` does not cover it.

---

## 3. The passes

The five compute shaders share one view of the buffers. An include holds it, so
that the bindings are written once. **This is `ParticleBuffers.glsl`**, with no
stage suffix, so Chapter 06's glob compiles it only through the shaders that
include it:

```glsl
// Shaders/Particles/ParticleBuffers.glsl - the particle set, as every compute pass
// sees it. An include, not a stage: Chapter 06's glob skips it.
#include "ParticleTypes.h"

layout(set = 0, binding = 0, std430) buffer ParticleBuffer   { Particle particles[]; };
layout(set = 0, binding = 1, std430) buffer DeadListBuffer   { uint deadList[]; };
layout(set = 0, binding = 2, std430) buffer AliveListBuffer  { uint aliveLists[]; };   // two lists, maxParticles apart
layout(set = 0, binding = 3, std430) buffer CounterBuffer    { ParticleCounters counters; };
layout(set = 0, binding = 4, std430) buffer IndirectBuffer   { ParticleIndirect indirect; };

layout(push_constant) uniform PushConstants
{
    ParticleSimulation simulation;
};
```

### Reset

**This is `ParticleReset.comp.glsl`.** It runs once after `Setup`, and again
whenever the panel's "Reset" or "Max particles" asks. Every slot goes on the dead
list and both alive lists are emptied.

```glsl
// Shaders/Particles/ParticleReset.comp.glsl - every slot free, nothing alive.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "ParticleBuffers.glsl"

layout(local_size_x = PARTICLE_GROUP_SIZE) in;

void main()
{
    uint id = gl_GlobalInvocationID.x;
    if (id == 0u)
    {
        counters.aliveCount[0] = 0u;
        counters.aliveCount[1] = 0u;
        counters.deadCount     = simulation.maxParticles;
        counters.emitCount     = 0u;
    }
    if (id >= simulation.maxParticles) { return; }

    // The dead list is a stack of free slot numbers. Its order does not matter.
    deadList[id] = id;
}
```

Chapter 20 zeroed its counters with `vkCmdFillBuffer`, and that cannot do this:
a fill writes one repeated value, and the dead list needs the numbers `0` to
`max - 1`. A compute pass can write anything. Invocation 0 writes the counters
*before* its own bounds check, and that is correct as long as `max` is at least
1, which the panel guarantees: its slider passes `ImGuiSliderFlags_AlwaysClamp`
(section 7), so even a value typed with Ctrl+click stays between 1024 and
`PARTICLE_CAPACITY`. Without the flag a typed 0 dispatches no workgroups, so
nothing resets the counters, and a typed 2000000 writes past the end of the dead
list. Changing "Max particles" must reset, because a
smaller limit would strand slots above it on the alive lists, and a larger one
would leave slots that are on no list at all.

### Begin

**This is `ParticleBegin.comp.glsl`.** One invocation, `vkCmdDispatch(1, 1, 1)`:
nothing here is parallel, it only has to happen on the GPU, because the numbers
it reads exist only there.

```glsl
// Shaders/Particles/ParticleBegin.comp.glsl - one invocation: this frame's counts
// and the indirect arguments for emit and simulate.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "ParticleBuffers.glsl"

layout(local_size_x = 1) in;

void main()
{
    uint current = simulation.currentList;
    uint next    = 1u - current;

    // Emit only what the dead list can supply, so every pop in the emit pass succeeds.
    uint emitCount = min(simulation.emitRequest, counters.deadCount);
    counters.emitCount = emitCount;

    // The list simulate fills this frame starts empty. Resetting it here, in a pass
    // that runs anyway, costs no extra command and no extra barrier.
    counters.aliveCount[next] = 0u;

    // Emit runs once per new particle; simulate once per particle alive after emit.
    uint simulateCount = counters.aliveCount[current] + emitCount;
    indirect.emit     = DispatchIndirectCommand((emitCount     + PARTICLE_GROUP_SIZE - 1) / PARTICLE_GROUP_SIZE, 1u, 1u);
    indirect.simulate = DispatchIndirectCommand((simulateCount + PARTICLE_GROUP_SIZE - 1) / PARTICLE_GROUP_SIZE, 1u, 1u);
}
```

Three jobs, each a reason the CPU could not do it:

- **Clamp the emission** to what the dead list can supply, so every pop in the
  emit pass succeeds.
- **Reset the count simulate will append to**, in a pass that runs anyway: no
  command and no barrier, where Chapter 20's fill needed one of each and two
  barriers.
- **Size the two dispatches.** Simulate must run once per particle alive after
  emission, which is the old count plus the clamped emission. Both are known
  here, before emit runs, because every emission is guaranteed to succeed. That
  guarantee is what saves a second single-invocation pass between emit and
  simulate.

The workgroup counts are rounded up the way Chapter 20's `groupCount` does it,
and the shaders check their index for the same reason. A dispatch with a group
count of 0 is legal and does nothing, which is what happens when nothing is
emitted.

### Random numbers, and seeding them

Emission needs random directions, speeds, and lifetimes, a fresh set for every
new particle in every frame. Chapter 20 put `pcgHash` in
`Shaders/Include/Random.glsl`. **This is the rest of `Random.glsl`**, appended
before its closing `#endif`:

```glsl
// Chapter 21: a stream of random numbers, one per invocation. The caller keeps
// the state in a local uint and passes it to every call, which advances it.

// A state that differs per item AND per frame.
uint seedRandom(uint index, uint frame)
{
    return pcgHash(index ^ pcgHash(frame));
}

// Uniform in [0, 1). The top 24 bits, because a float holds 24: dividing all 32
// would round the largest values up to exactly 1.0.
float randomFloat(inout uint state)
{
    state = pcgHash(state);
    return float(state >> 8u) * (1.0 / 16777216.0);
}
```

The state is a `uint` the caller keeps in a local variable and passes to every
call. That is a random-number *stream*: each call hashes the state into the next
one. What matters is where each stream starts:

- **Seeded from the frame alone**, every new particle in a frame would get the
  same numbers and leave along the same path, in clumps.
- **Seeded from the invocation alone**, the `k`-th new particle of every frame
  would repeat the `k`-th of the frame before, and the fountain would show a
  fixed set of trajectories, visibly.
- **Seeded from both**, through `seedRandom(index, frame)`, every new particle of
  every frame starts a different stream. Hashing the frame before combining it
  keeps "item 7 of frame 2" from equalling "item 2 of frame 7".

`randomFloat` keeps 24 bits, for the reason in its comment: with all 32, "in
`[0, 1)`" would be false about once in sixteen million calls, which is often at
a hundred thousand particles a second. Chapter 20's seed shader divided a whole
hash by 2^32, which was harmless there (a density comparison does not care about
an occasional 1.0). From here on, `randomFloat` is the way to get a float.

### Emit

**This is `ParticleEmit.comp.glsl`.** One invocation per new particle.

```glsl
// Shaders/Particles/ParticleEmit.comp.glsl - one invocation per new particle.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "ParticleBuffers.glsl"
#include "Random.glsl"

layout(local_size_x = PARTICLE_GROUP_SIZE) in;

// Uniform over the cap of the unit sphere within halfAngle of +Y (section 3): the
// cap's height, which is the cosine of the angle from +Y, is uniform between
// cos(halfAngle) and 1, and the angle around +Y is uniform.
vec3 randomInCone(inout uint state, float halfAngle)
{
    float cosTheta = mix(1.0, cos(halfAngle), randomFloat(state));
    float sinTheta = sqrt(max(0.0, 1.0 - cosTheta * cosTheta));
    float phi      = randomFloat(state) * 6.28318530718;
    return vec3(sinTheta * cos(phi), cosTheta, sinTheta * sin(phi));
}

void main()
{
    uint id = gl_GlobalInvocationID.x;
    if (id >= counters.emitCount) { return; }   // the dispatch rounds up

    // Pop a free slot. The begin pass made emitCount <= deadCount, so one exists.
    // atomicAdd returns the value before the add: subtracting 1 makes this
    // invocation's slot the old top of the stack.
    uint deadSlot = atomicAdd(counters.deadCount, uint(-1)) - 1u;
    uint index    = deadList[deadSlot];

    // A different stream per new particle and per frame. A fountain: every particle
    // starts at the emitter and leaves upwards, within the spread angle of +Y.
    uint random    = seedRandom(id, simulation.frameNumber);
    vec3 position  = simulation.emitterPosition.xyz;
    vec3 direction = randomInCone(random, simulation.spreadAngle);

    float speed    = simulation.speed    * (1.0 + simulation.speedVariation    * (randomFloat(random) * 2.0 - 1.0));
    float lifetime = simulation.lifetime * (1.0 + simulation.lifetimeVariation * (randomFloat(random) * 2.0 - 1.0));
    particles[index] = Particle(vec4(position, 0.0), vec4(direction * speed, lifetime));

    // Append to the current alive list: the same atomic trick, upwards.
    uint aliveSlot = atomicAdd(counters.aliveCount[simulation.currentList], 1u);
    aliveLists[simulation.currentList * simulation.maxParticles + aliveSlot] = index;
}
```

**Directions spread evenly over a cone.** `randomInCone` picks a direction in
two steps: how far to tilt it away from +Y (the angle `theta`), and which way
round to tilt it (`phi`). Every way round is as likely as any other, so `phi` is
uniform from 0 to 360 degrees. The tilt is the trap: an angle drawn uniformly
does *not* spread the directions evenly.

The sphere has a property, found by Archimedes, that says what to draw instead.
Cut a sphere into slices of equal thickness along one axis, and every slice has
the same surface area, whether it is a small ring near the pole or a wide band
near the equator:

```text
  +Y      (one quarter of the sphere, side on; spin it round +Y)
   *-._
   |    '-.            slice 1: close to the axis, so a short ring,
 --|-------'.-------            but the surface leans over: a long arc
   |          \        slice 2
 --|-----------\----
   |            |      slice 3: far from the axis, so a long ring,
 --|------------|---            but the surface is steep: a short arc
```

Near the pole the ring is short but the surface is nearly flat, so a slice takes
a long arc of it; near the equator the ring is long but the surface is steep,
so the arc is short. The two cancel exactly: on a unit sphere a slice of
thickness `h` has area `2 pi h`. The height along +Y of a direction tilted by
`theta` is `cos(theta)`. So drawing `cos(theta)` uniformly, between
`cos(halfAngle)` and 1, gives every equal-area slice the same share of the
particles, which is an even spread. That is the first line of `randomInCone`.

A worked example shows what the uniform angle would have done instead. Cut a
30-degree cone into three bands of 10 degrees each. A uniform angle gives each
band a third of the particles, but the bands' areas on the unit sphere are very
different:

```text
 band, degrees from +Y    area, 2 pi (cos start - cos end)    share of particles    share / area
 0 to 10                  0.095                               one third             3.5
 10 to 20                 0.283                               one third             1.2
 20 to 30                 0.463                               one third             0.7
```

Five times as many particles per unit area near the axis as at the rim: a
fountain with a bright core and a thin edge. With `cos(theta)` drawn uniformly,
each band gets a share in proportion to its area, and the density is the same
everywhere.

Other emitter shapes change only where a particle starts and which way it goes.
A sphere burst draws `cos(theta)` uniformly over the whole -1 to 1 and starts
each particle on the sphere's surface; a ring starts them on a circle around
the emitter. Both are a good exercise: one more push-constant field to choose
the shape, and a branch here.

The **variations** are symmetric, `1 ± v`, so the average speed and lifetime are
exactly the slider values. Section 7's equilibrium check depends on the average
lifetime being known.

### Simulate

**This is `ParticleSimulate.comp.glsl`.** One invocation per live particle,
new ones included.

```glsl
// Shaders/Particles/ParticleSimulate.comp.glsl - one invocation per live particle:
// age it, move it, and file it on the next alive list or back on the dead list.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "ParticleBuffers.glsl"

layout(local_size_x = PARTICLE_GROUP_SIZE) in;

void main()
{
    uint id      = gl_GlobalInvocationID.x;
    uint current = simulation.currentList;
    if (id >= counters.aliveCount[current]) { return; }

    uint     index    = aliveLists[current * simulation.maxParticles + id];
    Particle particle = particles[index];
    float    dt       = simulation.deltaTime;

    // 1. Dead: give the slot back, and do not carry it to the next list.
    float age      = particle.positionAndAge.w + dt;
    float lifetime = particle.velocityAndLifetime.w;
    if (age >= lifetime)
    {
        uint deadSlot = atomicAdd(counters.deadCount, 1u);   // push
        deadList[deadSlot] = index;
        return;
    }

    // 2. Move: gravity, then drag, then position (semi-implicit Euler).
    vec3 velocity = particle.velocityAndLifetime.xyz;
    vec3 position = particle.positionAndAge.xyz;
    velocity += simulation.gravity.xyz * dt;
    velocity *= exp(-simulation.gravity.w * dt);   // exact decay for linear drag, stable at any dt
    position += velocity * dt;

    // 3. The ground: put it back on the plane, and bounce what was moving into it.
    if (position.y < simulation.groundHeight && velocity.y < 0.0)
    {
        position.y   = simulation.groundHeight;
        velocity.y   = -velocity.y * simulation.restitution;
        velocity.xz *= 1.0 - simulation.friction;
    }
    particles[index] = Particle(vec4(position, age), vec4(velocity, lifetime));

    // 4. Survived: append to the other list. This is the compaction - the next
    //    list holds only live particles, packed from 0, in no particular order.
    uint next      = 1u - current;
    uint aliveSlot = atomicAdd(counters.aliveCount[next], 1u);
    aliveLists[next * simulation.maxParticles + aliveSlot] = index;
}
```

What each step is doing:

- **Death first**, before any work is spent moving a particle that is about to
  vanish. A particle dies in the first frame its age reaches its lifetime, so on
  average it lives half a frame less than its lifetime. Section 7's check
  accounts for that.
- **Euler integration** is `position += velocity * dt`: assume the velocity
  holds still for the whole step. *Explicit* Euler moves by the old velocity and
  then updates it; **semi-implicit Euler**, used here, updates the velocity first
  and moves by the *new* one. It is one line different and much better behaved
  for bouncing, because the velocity a particle leaves the ground with is the
  one it moves by.
- **Drag** removes the same *fraction* of the speed every instant. Compounding
  that continuously, like continuously compounded interest run backwards, is
  what `exp` computes: over one step the velocity is multiplied by
  `exp(-k dt)`, which is the exact solution of `dv/dt = -k v`. The obvious
  `1 - k dt` is the same for small steps: at the default drag of 0.3 per second
  and 60 frames a second both are 0.995. But it goes negative when `k dt > 1`,
  so a long frame would make particles reverse. The exponential never does, at
  any frame time.
- **The ground** is the plane `y = groundHeight`. A particle that crossed it
  while moving down is put back on it, its vertical speed reflected and scaled
  by the restitution, and its horizontal speed reduced by the friction. A
  particle at rest jitters by a fraction of a millimetre each frame as gravity
  pulls it in and the plane pushes it back, which is invisible. A real
  collider would test the path rather than the end point, and that is where to
  go for walls and fast particles.
- **The append** at the end is the compaction from section 2. The order of the
  next list depends on which invocation's atomic ran first, which varies from
  frame to frame. Section 5 comes back to that.

### End

**This is `ParticleEnd.comp.glsl`.** One invocation turns the survivors' count
into the draw:

```glsl
// Shaders/Particles/ParticleEnd.comp.glsl - one invocation: the draw's arguments.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "ParticleBuffers.glsl"

layout(local_size_x = 1) in;

void main()
{
    // Six vertices make one camera-facing quad; one instance per live particle.
    uint next = 1u - simulation.currentList;
    indirect.draw = DrawIndirectCommand(6u, counters.aliveCount[next], 0u, 0u);
}
```

Six vertices draw one quad as two triangles, and `instanceCount` copies it once
per live particle. Why not let simulate increment `indirect.draw.instanceCount`
directly and skip this pass? It could, but then the indirect buffer would be
modified by atomics in the middle of the frame. As section 4 shows, keeping its
writers to the two single-invocation passes is what keeps its barriers simple.

---

## 4. Recording the compute

**This is `CreateComputePipelines`**, Chapter 20's shape: one layout, one
push-constant block, a pipeline per pass.

```cpp
InitializationResult ParticlesDemo::CreateComputePipelines()
{
    // Chapter 20's shape: one layout for every compute pass, one push-constant block.
    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(ParticleSimulation),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_setLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_vulkan.device, &layoutInfo, nullptr, &m_computeLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the particle passes.");
    }

    const struct { VkPipeline* pipeline; const char* shader; } passes[] = {
        { &m_resetPipeline,    "Particles/ParticleReset.comp.spv" },
        { &m_beginPipeline,    "Particles/ParticleBegin.comp.spv" },
        { &m_emitPipeline,     "Particles/ParticleEmit.comp.spv" },
        { &m_simulatePipeline, "Particles/ParticleSimulate.comp.spv" },
        { &m_endPipeline,      "Particles/ParticleEnd.comp.spv" },
    };
    for (const auto& pass : passes)
    {
        *pass.pipeline = createComputePipeline(m_vulkan.device, m_pipelineCache, pass.shader, m_computeLayout);
        if (*pass.pipeline == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a particle compute pipeline failed.");
        }
    }
    return InitializationResult::success();
}
```

**This is `RecordCompute`.** It is long because every pass is followed by its
barrier, and each barrier is worth reading, so here it is in five pieces.

First, this frame's numbers. The emission is the rate times the time step, with
the fractional particle carried to the next frame, so that 4000 a second at
60 Hz averages 66.67 rather than truncating to 66 every frame:

```cpp
void ParticlesDemo::RecordCompute(VkCommandBuffer commandBuffer, uint32_t frameIndex)
{
    // This frame's emission: the rate times the time step, carrying the fraction
    // over so that 4000 per second at 60 Hz averages 66.67, not 66.
    const float wanted  = m_settings.emitRate * m_deltaTime + m_emitCarry;
    const float whole   = std::floor(wanted);
    const float request = std::min(whole, static_cast<float>(m_settings.maxParticles));
    m_emitCarry         = wanted - whole;

    const uint32_t current = m_currentList;
    const float    spread  = glm::radians(m_settings.spreadDegrees);
    const ParticleSimulation simulation{
        .emitterPosition   = glm::vec4(0.0f, 0.05f, 0.0f, 0.0f),
        .gravity           = glm::vec4(0.0f, -m_settings.gravity, 0.0f, m_settings.drag),
        .deltaTime         = m_deltaTime,
        .speed             = m_settings.speed,
        .speedVariation    = m_settings.speedVariation,
        .spreadAngle       = spread,
        .lifetime          = m_settings.lifetime,
        .lifetimeVariation = m_settings.lifetimeVariation,
        .groundHeight      = 0.0f,
        .restitution       = m_settings.restitution,
        .friction          = m_settings.friction,
        .emitRequest       = static_cast<uint32_t>(request),
        .frameNumber       = m_frameNumber++,
        .currentList       = current,
        .maxParticles      = static_cast<uint32_t>(m_settings.maxParticles),
    };
    vkCmdPushConstants(commandBuffer, m_computeLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                       0, sizeof(simulation), &simulation);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_computeLayout,
                            0, 1, &m_set, 0, nullptr);
```

The push constants and the set are bound once for all five passes. Both stay
bound across `vkCmdBindPipeline` calls, because every compute pipeline here has
the same layout.

### The return trip

```cpp
    // 1. The return trip. Last frame's draw read the indirect arguments and the
    //    particles, its readback copy read the counters, and its compute passes
    //    wrote all of it. This frame's compute writes them again.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT
                      | VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
```

The previous frame left four kinds of access on these buffers. Its compute passes
wrote everything. Its draw read the indirect arguments (`DRAW_INDIRECT`) and its
vertex shader read the particles and an alive list (`VERTEX_SHADER`). Its readback
copy read the counters (`COPY`). Nothing on the queue orders this frame's first
dispatch after any of them. The submit waits on the swapchain image only at
`COLOR_ATTACHMENT_OUTPUT`, so compute at the top of a frame may start while the
last frame is still drawing.

- **Q1:** all four of those stages must finish before this frame's
  `COMPUTE_SHADER` work starts.
- **Q2:** the earlier compute *writes* are made available
  (`SHADER_STORAGE_WRITE`) and visible to this frame's storage reads and writes:
  begin reads the counters simulate wrote. The draw's and the copy's reads need
  nothing flushed, since they wrote nothing.
- **Q3:** buffers, no layouts.

This is the cost of keeping one copy of the state, and it is one barrier.

### Reset and begin

```cpp
    // 2. Reset, when asked: every slot free, both alive lists empty.
    if (m_resetRequested)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_resetPipeline);
        vkCmdDispatch(commandBuffer, groupCount(simulation.maxParticles, PARTICLE_GROUP_SIZE), 1, 1);
        computeToComputeBarrier(commandBuffer);
        m_resetRequested = false;
        m_emitCarry      = 0.0f;
    }

    // 3. Begin: one invocation writes this frame's counts and dispatch sizes.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_beginPipeline);
    vkCmdDispatch(commandBuffer, 1, 1, 1);

    // Its writes are read two ways: as indirect arguments by the dispatches, and
    // as storage by their shaders.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT
                      | VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
```

The reset is followed by Chapter 20's `computeToComputeBarrier`, because begin
reads the counters it wrote. The barrier after begin is the new one:

- **Q1:** begin's `COMPUTE_SHADER` work before the next commands'
  `DRAW_INDIRECT` stage (where `vkCmdDispatchIndirect` reads the arguments) and
  `COMPUTE_SHADER` stage (where emit and simulate run).
- **Q2:** begin's storage writes made visible to *two kinds* of read: the
  argument fetch (`INDIRECT_COMMAND_READ`) and the shaders' storage reads and
  writes of the counters. Leaving out `INDIRECT_COMMAND_READ` is the classic
  mistake here, and it is the one that makes a GPU dispatch with last frame's
  count.
- **Q3:** none.

A barrier orders everything after it, not only the next command (Chapter 04
section 5), so this one also covers simulate's argument fetch two dispatches
later.

### Emit and simulate

```cpp
    // 4. Emit, sized by the GPU.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_emitPipeline);
    vkCmdDispatchIndirect(commandBuffer, m_indirect.buffer, offsetof(ParticleIndirect, emit));
    computeToComputeBarrier(commandBuffer);
    WriteTimestamp(commandBuffer, frameIndex, 1);

    // 5. Simulate, sized by the GPU: everything alive, new particles included.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_simulatePipeline);
    vkCmdDispatchIndirect(commandBuffer, m_indirect.buffer, offsetof(ParticleIndirect, simulate));
    computeToComputeBarrier(commandBuffer);
    WriteTimestamp(commandBuffer, frameIndex, 2);
```

`vkCmdDispatchIndirect` takes the buffer and the byte offset of a
`VkDispatchIndirectCommand` in it. `offsetof` on the twin struct gives it, and
section 2's asserts guarantee the layout. Between the two, and after simulate,
Chapter 20's `computeToComputeBarrier`: simulate reads the particles and the
list emit wrote, and end reads the count simulate wrote. The timestamps are
section 8's.

### End, and the counters out

```cpp
    // 6. End: one invocation turns the survivors' count into the draw's instance count.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_endPipeline);
    vkCmdDispatch(commandBuffer, 1, 1, 1);

    // Read three ways: the draw's arguments, the vertex shader's particles and
    // alive list, and the copy of the counters below.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT
                      | VK_PIPELINE_STAGE_2_COPY_BIT,
                  VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_READ_BIT
                      | VK_ACCESS_2_TRANSFER_READ_BIT);

    // 7. Chapter 20 section 9: the counters, out to this slot's readback buffer.
    const VkBufferCopy region{ .size = sizeof(ParticleCounters) };
    vkCmdCopyBuffer(commandBuffer, m_counters.buffer, m_readback[frameIndex].buffer, 1, &region);
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    m_readbackPending[frameIndex] = true;
    m_readbackList[frameIndex]    = 1 - current;   // the list simulate filled

    // The survivors are in the other list now; next frame starts from it.
    m_currentList = 1 - current;
}
```

The barrier after end has three readers:

- **Q1:** end's `COMPUTE_SHADER` work before the draw's argument fetch
  (`DRAW_INDIRECT`), its vertex shader (`VERTEX_SHADER`), and the copy (`COPY`).
- **Q2:** compute's storage writes made visible to `INDIRECT_COMMAND_READ` (the
  draw's arguments), `SHADER_STORAGE_READ` (the vertex shader reading the
  particles and the alive list), and `TRANSFER_READ` (the copy reading the
  counters).
- **Q3:** none.

It covers simulate's writes as well as end's, because a barrier orders
everything before it in the stages it names, not only the last dispatch. The copy and its
`HOST` barrier are Chapter 20 section 9's, unchanged. The one thing to remember
for the readback is *which* alive list was drawn, because the counters hold both:
`m_readbackList` keeps it per slot.

### What validation can check here

The barrier between simulate and end makes simulate's `atomicAdd` on
`aliveCount[next]` visible to end's plain read of it. Its writer is an atomic,
so the layer cannot check it (Chapter 20 section 5's table); the three
questions are its proof. What the layer does catch, and what this chapter's
exit check uses as its positive control: delete the barrier after end, and
`vkCmdDrawIndirect` reports `SYNC-HAZARD-READ-AFTER-WRITE`, both for the
argument fetch and for the vertex shader's reads.

Those five pieces, in order, are the whole of `RecordCompute`; nothing sits
between them but blank lines.

---

## Stopping point

The compute half is complete: the pool and its lists (sections 1 and 2), the
five passes (section 3), and `RecordCompute`, which runs them with a barrier
after each and leaves the draw's arguments in the indirect buffer. Every frame
the GPU now sizes its own work and the CPU never learns the count. Nothing
draws yet, so there is nothing to see: section 5 draws the particles, and the
checkpoint after section 6 runs them.

---

## 5. Drawing the particles

### A quad per particle, with no vertex buffer

Each particle is a square facing the camera, a **billboard**. The vertex shader
builds it from two built-in numbers: `gl_InstanceIndex` says which particle, and
`gl_VertexIndex` (0-5) says which corner of which triangle. Chapter 19 already
indexed a storage buffer with `gl_InstanceIndex`. The new part is that the
instance goes through the alive list first: instance `i` draws whichever slot is
`i`-th in the list simulate just filled.

**This is `Particle.vert.glsl`:**

```glsl
// Shaders/Particles/Particle.vert.glsl - a camera-facing quad per particle, from
// gl_VertexIndex and gl_InstanceIndex alone: no vertex buffer.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "FrameBlock.glsl"      // set 0: frame.view, frame.projection
#include "ParticleTypes.h"
#include "Random.glsl"

// Set 1: the compute passes' set, bound a second time. readonly is required: the
// vertex stage may not write storage buffers without vertexPipelineStoresAndAtomics.
layout(set = 1, binding = 0, std430) readonly buffer ParticleBuffer  { Particle particles[]; };
layout(set = 1, binding = 2, std430) readonly buffer AliveListBuffer { uint aliveLists[]; };

layout(push_constant) uniform PushConstants
{
    ParticleAppearance appearance;
};

layout(location = 0) out vec2 corner;   // -1..1 across the quad
layout(location = 1) out vec4 color;    // linear rgb, a = opacity

// Two triangles: (0, 1, 2) and (0, 2, 3) of the corners -x-y, +x-y, +x+y, -x+y.
const vec2 corners[6] = vec2[](vec2(-1.0, -1.0), vec2( 1.0, -1.0), vec2( 1.0,  1.0),
                               vec2(-1.0, -1.0), vec2( 1.0,  1.0), vec2(-1.0,  1.0));

void main()
{
    // Instance i draws the i-th live particle: the alive list maps it to its slot.
    uint     index    = aliveLists[appearance.aliveList * appearance.maxParticles + uint(gl_InstanceIndex)];
    Particle particle = particles[index];

    // How far through its life, 0 to 1. Size and color follow straight lines in
    // it; opacity fades in quickly and out slowly, so nothing pops.
    float life = clamp(particle.positionAndAge.w / particle.velocityAndLifetime.w, 0.0, 1.0);
    float fade = smoothstep(0.0, 0.05, life) * (1.0 - smoothstep(0.6, 1.0, life));

    // A fixed per-slot variation in size, so a cloud does not look stamped out.
    uint  random = pcgHash(index);
    float size   = mix(appearance.startSize, appearance.endSize, life)
                 * (0.75 + 0.5 * float(random >> 8u) * (1.0 / 16777216.0));

    // The centre into view space, where the camera's right is always +X and its up
    // +Y. Offsetting there makes a square that faces the screen; then project it.
    corner = corners[gl_VertexIndex];
    vec4 centre = frame.view * vec4(particle.positionAndAge.xyz, 1.0);
    centre.xy  += corner * (0.5 * size);
    gl_Position = frame.projection * centre;

    color   = mix(appearance.startColor, appearance.endColor, life);
    color.a *= fade;
}
```

- **`readonly` is required here, not decoration.** Writing storage memory from a
  vertex shader needs the `vertexPipelineStoresAndAtomics` feature, which the
  tutorial does not enable, and validation rejects a vertex-stage storage buffer
  without the `NonWritable` decoration that `readonly` produces.
- **Camera-facing corners, built in view space.** The view matrix moves the
  world so that the camera sits at the origin looking down -Z (Chapter 10
  sections 1 and 4). In that space the camera's right is always +X and its up
  is always +Y, so adding the corner to the centre's `x` and `y` makes a square
  that faces the screen whatever the camera does. The projection then takes it
  the rest of the way, which is the second half of what `viewProjection` does.
  Chapter 10's `FrameData` already carries `view` and `projection`, so this
  costs nothing new.
- **Curves over the lifetime.** `life` runs from 0 to 1. Size and color are
  straight lines in it, between the panel's start and end values. Opacity fades
  in over the first 5% and out over the last 40%, so a particle neither pops in
  nor vanishes.
- **Variation by slot.** `pcgHash(index)` gives each slot a fixed size factor.
  It is keyed by the slot, not the instance, because the instance order changes
  every frame (section 3), and a particle that changed size every frame would
  flicker.

**This is `Particle.frag.glsl`:**

```glsl
// Shaders/Particles/Particle.frag.glsl - a soft round dot, premultiplied.
#version 450

layout(location = 0) in  vec2 corner;
layout(location = 1) in  vec4 color;
layout(location = 0) out vec4 outColor;

void main()
{
    // 1 at the centre, 0 at the circle's edge and beyond: the quad's corners are
    // fully transparent, so no discard is needed.
    float falloff = max(1.0 - dot(corner, corner), 0.0);
    float alpha   = color.a * falloff * falloff;

    // Premultiplied: color already multiplied by its own alpha. The additive
    // pipeline (ONE, ONE) and the premultiplied one (ONE, ONE_MINUS_SRC_ALPHA)
    // both want exactly this.
    outColor = vec4(color.rgb * alpha, alpha);
}
```

The falloff turns the square into a soft round dot that reaches zero at the
circle's edge, so the quad's corners are fully transparent and no `discard` is
needed. That matters because `discard` makes a pipeline need Chapter 15's
`shaderDemoteToHelperInvocation`, and blending with zero alpha costs less than
branching. The output is **premultiplied**: color already multiplied by its own
alpha. The next subsection says why that one output suits both blend modes.

### Blending: additive or premultiplied, and why not plain alpha

Every blend mode is `result = source * srcFactor + destination * dstFactor`.
Three are worth knowing for particles:

| Mode | Factors (color) | Result | Order matters? |
| --- | --- | --- | --- |
| Alpha ("over") | `SRC_ALPHA`, `ONE_MINUS_SRC_ALPHA` | `c * a + d * (1 - a)` | Yes |
| Additive | `ONE`, `ONE` | `c * a + d` (the shader multiplied by `a`) | No |
| Premultiplied alpha | `ONE`, `ONE_MINUS_SRC_ALPHA` | `c * a + d * (1 - a)` | Yes |

**Additive** adds light. Addition does not care about order, so ten thousand
overlapping particles look the same whichever is drawn first, and no sorting is
needed. It can only brighten, which is right for fire, sparks, and glowing
things and wrong for smoke. The scene target is `R16G16B16A16_SFLOAT`, so the
sums go above 1.0 instead of clipping in the target. Chapter 16's tone curve then
compresses them; in raw mode the composite clamps them to white.

**Alpha** covers what is behind. "Over" is not commutative: A over B is not B
over A. For the result to be right, overlapping particles must be drawn back to
front, which means sorting them by distance from the camera every frame. On
the GPU that is a sort pass (bitonic or radix, several dispatches) between
simulate and draw. And the order the alive list gives you is not just
unsorted. It is the order the atomics ran in, which is roughly oldest first and
newest last, since emit appends the new particles after last frame's survivors.
On most GPUs it also varies from frame to frame, as workgroups finish in a
different order, so unsorted alpha particles pop as overlaps resolve
differently.

**Premultiplied alpha** is "over" with the multiplication moved into the shader.
What it buys here is that one mode spans both behaviours: a pixel with alpha 1
covers like "over", and a pixel with color but alpha 0 adds like additive. A
single pipeline can then draw smoke and sparks together.

**What this chapter does instead of sorting:** additive by default, which needs
no order, and premultiplied alpha on the panel to show the problem. With small,
soft, short-lived dots the errors are hard to see. Make both sizes 0.6 m and the
end color an opaque blue, and they are obvious: the young orange particles,
drawn last, cover the older blue ones that are nearer the camera. The fixes are
a GPU sort of the alive list by view depth, or order-independent transparency
(weighted blended OIT, McGuire and Bavoil, 2013). Both are separate projects, and
neither is built here.

**This is `createGraphicsPipeline`'s blend state**, in `GraphicsPipeline.cpp`,
which gains the premultiplied case. The enum gains it first, in
`GraphicsPipeline.h`:

```cpp
// Chapter 21 adds PremultipliedAlpha: the shader has already multiplied its color
// by its alpha, so the source factor is ONE.
enum class BlendMode { Opaque, Alpha, Additive, PremultipliedAlpha };
```

Chapter 06 section 8 left the blend state to the body of `createGraphicsPipeline`,
where two blending modes fit a pair of ternaries on `desc.blend == BlendMode::Alpha`.
A third does not, so the whole `if (desc.blend != BlendMode::Opaque)` block becomes
a `switch`, whatever shape yours had:

```cpp
    // result = source * srcFactor + destination * dstFactor, for color and alpha.
    if (desc.blend != BlendMode::Opaque)
    {
        blendAttachment.blendEnable         = VK_TRUE;
        blendAttachment.colorBlendOp        = VK_BLEND_OP_ADD;
        blendAttachment.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
        blendAttachment.dstAlphaBlendFactor = VK_BLEND_FACTOR_ZERO;
        blendAttachment.alphaBlendOp        = VK_BLEND_OP_ADD;
        switch (desc.blend)
        {
        case BlendMode::Alpha:                // color * a + destination * (1 - a)
            blendAttachment.srcColorBlendFactor = VK_BLEND_FACTOR_SRC_ALPHA;
            blendAttachment.dstColorBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
            break;
        case BlendMode::Additive:             // color + destination
            blendAttachment.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
            blendAttachment.dstColorBlendFactor = VK_BLEND_FACTOR_ONE;
            break;
        case BlendMode::PremultipliedAlpha:   // (color * a) + destination * (1 - a)
            blendAttachment.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
            blendAttachment.dstColorBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
            blendAttachment.dstAlphaBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
            break;
        case BlendMode::Opaque:
            break;
        }
    }
```

The alpha channel's own factors do not matter for the scene target, which the
composite pass reads only as RGB. For premultiplied alpha they are set the way
"over" needs anyway, so the mode is right for a target that does use alpha.

### Depth: test on, write off

The particle pipeline tests depth and does not write it.

- **Test on**, so that opaque geometry hides particles behind it. Orbit below the
  ground and the fountain disappears behind it.
- **Write off**, because a particle that wrote depth would hide whatever is drawn
  after it behind its *whole quad*, transparent corners included. Without sorting,
  "after" changes every frame, so the result is square holes that flicker. An
  additive particle should not hide anything anyway: light passing through light
  does not block it.

Write off also makes the depth buffer read-only for the whole particle pass,
which the next subsection uses.

### A second rendering scope, after the scene pass

> **Jump:** every demo so far drew its whole scene in one rendering scope:
> `beginScenePass`, draws, `endScenePass`, hand back. Particles draw after the
> scene pass, in a scope of their own, with the scene's depth bound read-only.
> Chapter 09 left room for exactly this, and Chapter 10 section 9 said what the
> scene pass leaves behind for it. Keep in mind that the targets now cross from
> one scope to the next inside your `Record`, so the barriers between the scopes
> are yours, and so is the depth buffer's way back.

Why not draw the particles inside the scene pass, after the ground? Three
reasons, and the first is the deciding one:

- **Cost.** At 4x MSAA (Chapter 18) everything in the scene pass is drawn into
  multisampled targets. Blending ten thousand overlapping quads at four samples
  per pixel is four times the blending work, for soft dots whose edges have
  nothing to antialias. After the pass, the scene has been resolved, and
  particles blend into the single-sample target once per pixel.
- **The depth they test against** is then the resolved single-sample depth, the
  image Chapter 10 created with `SAMPLED` usage. That is also what soft
  particles (section 10) need to read.
- **Order.** Transparent things go after all opaque ones. A separate scope makes
  that structural rather than a rule about where in a function a draw sits.

So the particle pipeline is single-sample whatever `formats.samples` says,
while the ground, which draws inside the scene pass, takes the scene's sample
count.

**This is `CreateDrawPipelines`.** The ground is a large quad generated from
`gl_VertexIndex` like the particles, with a grid drawn in its fragment shader so
that bounces have something to land on. Its layout is set 0 and a small push
constant. The particles' layout is set 0, the particle set at 1, and the
appearance push constant.

```cpp
InitializationResult ParticlesDemo::CreateDrawPipelines()
{
    // The ground: set 0 for the camera, and its height and size as push constants.
    // It draws inside the scene pass, so it takes the scene's formats and sample count.
    const VkDescriptorSetLayout frameSetLayout = m_sceneRenderer.FrameSetLayout();
    const VkPushConstantRange groundRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT,
        .offset     = 0,
        .size       = sizeof(GroundParameters),
    };
    const VkPipelineLayoutCreateInfo groundLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &frameSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &groundRange,
    };
    if (vkCreatePipelineLayout(m_vulkan.device, &groundLayoutInfo, nullptr, &m_groundLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the ground.");
    }
    const GraphicsPipelineDesc ground{
        .vertexShader   = "Particles/Ground.vert.spv",
        .fragmentShader = "Particles/Ground.frag.spv",
        .colorFormats   = { &m_formats.color, 1 },
        .depthFormat    = m_formats.depth,
        .depthTest      = true,
        .depthWrite     = true,
        .depthCompare   = VK_COMPARE_OP_LESS,
        .layout         = m_groundLayout,
        .samples        = m_formats.samples,
    };
    m_groundPipeline = createGraphicsPipeline(m_vulkan.device, m_pipelineCache, ground);
    if (m_groundPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the ground pipeline failed.");
    }

    // The particles: set 0 the camera, set 1 the particle set, and the look as
    // push constants. Drawn after the scene pass, single-sample.
    const VkDescriptorSetLayout drawSetLayouts[] = { frameSetLayout, m_setLayout };
    const VkPushConstantRange drawRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT,
        .offset     = 0,
        .size       = sizeof(ParticleAppearance),
    };
    const VkPipelineLayoutCreateInfo drawLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 2,
        .pSetLayouts            = drawSetLayouts,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &drawRange,
    };
    if (vkCreatePipelineLayout(m_vulkan.device, &drawLayoutInfo, nullptr, &m_drawLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the particles.");
    }

    const BlendMode blends[] = { BlendMode::Additive, BlendMode::PremultipliedAlpha };
    for (size_t i = 0; i < m_drawPipelines.size(); ++i)
    {
        // Depth test on, depth write off: hidden by the ground, never hiding each other.
        const GraphicsPipelineDesc particles{
            .vertexShader   = "Particles/Particle.vert.spv",
            .fragmentShader = "Particles/Particle.frag.spv",
            .colorFormats   = { &m_formats.color, 1 },
            .depthFormat    = m_formats.depth,
            .depthTest      = true,
            .depthWrite     = false,
            .depthCompare   = VK_COMPARE_OP_LESS,
            .blend          = blends[i],
            .layout         = m_drawLayout,
        };
        m_drawPipelines[i] = createGraphicsPipeline(m_vulkan.device, m_pipelineCache, particles);
        if (m_drawPipelines[i] == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a particle pipeline failed.");
        }
    }
    return InitializationResult::success();
}
```

**These are the ground's shaders.** They need no explanation beyond the
comments, and their `GroundParameters` push constant is in `ParticleTypes.h`:

```glsl
// Shaders/Particles/Ground.vert.glsl - the plane the particles bounce on: one quad
// from gl_VertexIndex.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "FrameBlock.glsl"      // set 0: frame.viewProjection
#include "ParticleTypes.h"

layout(push_constant) uniform PushConstants
{
    GroundParameters ground;
};

layout(location = 0) out vec2 groundPosition;   // world x and z, metres

const vec2 corners[6] = vec2[](vec2(-1.0, -1.0), vec2( 1.0, -1.0), vec2( 1.0,  1.0),
                               vec2(-1.0, -1.0), vec2( 1.0,  1.0), vec2(-1.0,  1.0));

void main()
{
    groundPosition = corners[gl_VertexIndex] * ground.halfSize;
    gl_Position    = frame.viewProjection * vec4(groundPosition.x, ground.height, groundPosition.y, 1.0);
}
```

```glsl
// Shaders/Particles/Ground.frag.glsl - a dark floor with a line every metre.
#version 450

layout(location = 0) in  vec2 groundPosition;
layout(location = 0) out vec4 outColor;

void main()
{
    // Distance to the nearest grid line, in pixels: fwidth turns metres into
    // screen pixels, so the lines stay one pixel wide at any distance.
    vec2  toLine = abs(fract(groundPosition - 0.5) - 0.5) / fwidth(groundPosition);
    float line   = 1.0 - clamp(min(toLine.x, toLine.y), 0.0, 1.0);
    outColor = vec4(mix(vec3(0.03), vec3(0.15), line), 1.0);   // linear
}
```

**This is `RecordParticles`**, the second rendering scope. It starts where `endScenePass`
left the targets (Chapter 10 section 9): color in `COLOR_ATTACHMENT_OPTIMAL`,
depth in `DEPTH_ATTACHMENT_OPTIMAL`.

```cpp
void ParticlesDemo::RecordParticles(VkCommandBuffer commandBuffer, const RecordContext& frame)
{
    const SceneTargets& targets = frame.targets;

    // The scene pass left color in COLOR_ATTACHMENT_OPTIMAL and depth in
    // DEPTH_ATTACHMENT_OPTIMAL (Chapter 10). Blending reads and writes the color;
    // the depth test only reads the depth, so it moves to the read-only layout.
    transitionImage(commandBuffer, targets.colorImage,
                    VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_COLOR_ATTACHMENT_READ_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    // Last written by the depth test at 1x, by the resolve at Nx (Chapter 18):
    // the source names both.
    transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT
                        | VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);

    // Load what the scene drew and blend over it. The depth is loaded and never
    // stored: STORE_OP_NONE says this pass leaves it exactly as it found it.
    const VkRenderingAttachmentInfo colorAttachment{
        .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView   = targets.colorView,
        .imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
        .resolveMode = VK_RESOLVE_MODE_NONE,
        .loadOp      = VK_ATTACHMENT_LOAD_OP_LOAD,
        .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
    };
    const VkRenderingAttachmentInfo depthAttachment{
        .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView   = targets.depthView,
        .imageLayout = VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL,
        .resolveMode = VK_RESOLVE_MODE_NONE,
        .loadOp      = VK_ATTACHMENT_LOAD_OP_LOAD,
        .storeOp     = VK_ATTACHMENT_STORE_OP_NONE,
    };
    const VkRenderingInfo renderingInfo{
        .sType                = VK_STRUCTURE_TYPE_RENDERING_INFO,
        .renderArea           = { { 0, 0 }, targets.extent },
        .layerCount           = 1,
        .colorAttachmentCount = 1,
        .pColorAttachments    = &colorAttachment,
        .pDepthAttachment     = &depthAttachment,
    };
    vkCmdBeginRendering(commandBuffer, &renderingInfo);

    const VkViewport viewport{ 0.0f, 0.0f,
                               static_cast<float>(targets.extent.width),
                               static_cast<float>(targets.extent.height),
                               0.0f, 1.0f };
    const VkRect2D scissor{ { 0, 0 }, targets.extent };
    vkCmdSetViewport(commandBuffer, 0, 1, &viewport);
    vkCmdSetScissor(commandBuffer, 0, 1, &scissor);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_drawPipelines[m_settings.blend == 0 ? 0 : 1]);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_drawLayout, frame.frameIndex);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_drawLayout,
                            1, 1, &m_set, 0, nullptr);

    // ImGui's swatches are sRGB; the shader wants linear. Alpha is linear already.
    const float* start = m_settings.startColor;
    const float* end   = m_settings.endColor;
    const ParticleAppearance appearance{
        .startColor   = glm::vec4(srgbToLinear(start[0]), srgbToLinear(start[1]), srgbToLinear(start[2]), start[3]),
        .endColor     = glm::vec4(srgbToLinear(end[0]), srgbToLinear(end[1]), srgbToLinear(end[2]), end[3]),
        .startSize    = m_settings.startSize,
        .endSize      = m_settings.endSize,
        .aliveList    = m_currentList,   // RecordCompute flipped it to the list simulate filled
        .maxParticles = static_cast<uint32_t>(m_settings.maxParticles),
    };
    vkCmdPushConstants(commandBuffer, m_drawLayout, VK_SHADER_STAGE_VERTEX_BIT,
                       0, sizeof(appearance), &appearance);

    // One draw; the GPU wrote how many instances it has.
    vkCmdDrawIndirect(commandBuffer, m_indirect.buffer, offsetof(ParticleIndirect, draw), 1,
                      sizeof(VkDrawIndirectCommand));

    vkCmdEndRendering(commandBuffer);

    // The depth's return trip (Chapter 10 section 9): back to the layout the next
    // frame's scene pass expects, after this pass's depth tests have read it.
    transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
}
```

**The colors are sRGB in the settings and linear on the GPU.** Section 7's
panel edits them with `ColorEdit4`, which shows a number as an sRGB swatch, so
`RecordParticles` converts the RGB before pushing it and leaves alpha alone
(Chapter 08 section 4). This is the same conversion as `scene::srgbToLinear` in
Chapter 11 section 14's `ColorSpace.h`; this demo keeps its own copy, as a
file-scope function in its `.cpp`:

```cpp
// File scope, above the namespace block. Section 5: the swatches are sRGB, the
// shaders want linear (Chapter 08 section 4). Alpha is not encoded.
static float srgbToLinear(float value)
{
    return value <= 0.04045f ? value / 12.92f : std::pow((value + 0.055f) / 1.055f, 2.4f);
}
```

Without it, a picked orange comes out noticeably lighter and less saturated
than its swatch.

The two barriers into the scope, through the three questions:

| | Color target | Depth target |
| --- | --- | --- |
| Q1, what finishes / what waits | the scene pass's color writes (`COLOR_ATTACHMENT_OUTPUT`) / blending (`COLOR_ATTACHMENT_OUTPUT`) | the scene pass's depth writes (`EARLY_` and `LATE_FRAGMENT_TESTS`), or at Nx the resolve (`COLOR_ATTACHMENT_OUTPUT`) / the particles' depth tests |
| Q2, flush / invalidate | `COLOR_ATTACHMENT_WRITE` / `COLOR_ATTACHMENT_READ \| WRITE`: blending reads what is there and writes the result | `DEPTH_STENCIL_ATTACHMENT_WRITE \| COLOR_ATTACHMENT_WRITE` / `DEPTH_STENCIL_ATTACHMENT_READ` |
| Q3, layout | unchanged: `COLOR_ATTACHMENT_OPTIMAL` | `DEPTH_ATTACHMENT_OPTIMAL` to `DEPTH_READ_ONLY_OPTIMAL` |

Notes on them:

- **The color barrier has no layout change**, and it is still needed. Nothing
  orders one rendering scope's (`vkCmdBeginRendering` to `vkCmdEndRendering`)
  attachment writes before the next scope's loads. The layer cannot check this
  one (Chapter 20 section 5's table); the three questions are its proof, and
  Chapter 09 section 4 said the barrier after `endScenePass` is the demo's to
  write.
- **The depth source names both possible writers**, the ones `endScenePass`'s
  comment documents (Chapter 18 section 5): the depth tests at 1x, the resolve
  at Nx.
- **`DEPTH_READ_ONLY_OPTIMAL`** tells the driver nothing in this scope writes
  depth, which the pipeline's `depthWrite = false` already guarantees. It is also
  the layout that lets a shader *sample* the depth while it is bound as the
  depth attachment, which section 10 needs.
- **`STORE_OP_NONE`** (core in 1.3) on the depth attachment: this scope leaves the
  depth exactly as it found it. `STORE_OP_STORE` would count as a write, which a
  read-only layout cannot have.

**The return trip** after the scope is Chapter 10 section 9's rule: a later reader
of the depth hands it back in `DEPTH_ATTACHMENT_OPTIMAL`, with its own read stages
as the source, so the next frame's scene pass finds it as `endScenePass`
documented. A write after a read needs only the execution dependency, so the
source access is `NONE`.

This hand-back is the first half of a chain, and Chapter 18 section 5 wrote the
second half. Follow the single-sample depth image from one frame to the next at
4x:

```text
 frame N     scene pass       the depth tests run on the MULTISAMPLED depth; at the
                              end, the resolve writes this image (COLOR_ATTACHMENT_OUTPUT)
             RecordParticles  barrier in; the particles' depth tests read this image;
                              hand-back: layout back to DEPTH_ATTACHMENT_OPTIMAL,
                                dst = EARLY_|LATE_FRAGMENT_TESTS ──────┐
                                                                       │ chains into
 frame N+1   beginScenePass   Chapter 18's barrier, before the resolve writes it again,
                                src = EARLY_|LATE_FRAGMENT_TESTS ◀─────┘
                                    | COLOR_ATTACHMENT_OUTPUT
```

Two barriers on the same queue are ordered one after the other only when they
*chain*: the second one's source stages take in the first one's destination
stages. The hand-back ends at the fragment tests, and next frame's
`beginScenePass` barrier names the fragment tests in its source, so its layout
change comes after the hand-back's. The resolve that barrier waits for writes
at `COLOR_ATTACHMENT_OUTPUT`, a stage that already takes in the fragment tests
before it (Chapter 04 section 5); Chapter 18 names the fragment tests anyway
because that makes the chain readable in the code: this barrier's destination
is that barrier's source. At 1x there is nothing to add: the scene pass's depth
barrier is Chapter 10's, whose source is the fragment tests.

---

## 6. The frame

**This is `Record`.**

```cpp
void ParticlesDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const uint32_t        frameIndex    = frame.frameIndex;

    // 1. What this slot copied and timed last time.
    ReadResults(frameIndex);

    // 2. The camera, into this slot's frame buffer (Chapter 10 section 7).
    const VkExtent2D extent = frame.targets.extent;
    const float      aspect = static_cast<float>(extent.width) / static_cast<float>(extent.height);
    shared::FrameData frameData{};
    frameData.view           = scene::viewMatrix(m_cameraTransform.Matrix());
    frameData.projection     = m_camera.Projection(aspect);
    frameData.viewProjection = frameData.projection * frameData.view;
    frameData.cameraPosition = glm::vec4(m_cameraTransform.translation, 1.0f);
    frameData.time           = m_time;
    frameData.deltaTime      = m_deltaTime;
    m_sceneRenderer.WriteFrameData(frameIndex, frameData);

    if (m_queryPool != VK_NULL_HANDLE)
    {
        vkCmdResetQueryPool(commandBuffer, m_queryPool, frameIndex * TIMESTAMP_COUNT, TIMESTAMP_COUNT);
    }
    WriteTimestamp(commandBuffer, frameIndex, 0);

    // 3. Sections 3 and 4: emit, simulate, and the draw's arguments, all on the GPU.
    RecordCompute(commandBuffer, frameIndex);
    WriteTimestamp(commandBuffer, frameIndex, 3);

    // 4. The opaque scene: the ground, in the standard scene pass.
    const VkClearColorValue clearColor{ { 0.01f, 0.012f, 0.02f, 1.0f } };
    beginScenePass(commandBuffer, frame.targets, &clearColor);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_groundPipeline);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_groundLayout, frameIndex);
    const GroundParameters ground{ .height = 0.0f, .halfSize = 20.0f };
    vkCmdPushConstants(commandBuffer, m_groundLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(ground), &ground);
    vkCmdDraw(commandBuffer, 6, 1, 0, 0);
    endScenePass(commandBuffer);
    WriteTimestamp(commandBuffer, frameIndex, 4);

    // 5. Section 5: the particles, blended over it, then the scene goes back to the engine.
    RecordParticles(commandBuffer, frame);
    WriteTimestamp(commandBuffer, frameIndex, 5);
    m_timestampsPending[frameIndex] = m_queryPool != VK_NULL_HANDLE;

    handBackSceneTarget(commandBuffer, frame.targets);
}
```

Read top to bottom, it is the chapter. Read last time's results, write the
camera, run the compute, draw the opaque scene in the standard pass, draw the
particles in their own scope, hand the target back. Compute runs before
`beginScenePass` because a dispatch may not be inside a rendering scope (Chapter
20 section 1). Because the submit waits on the swapchain image only at
`COLOR_ATTACHMENT_OUTPUT`, all of it can start before the image is acquired.

The camera block is Chapter 10's `CubesDemo`, with the pose kept in
`m_cameraTransform`. `FrameData`'s remaining fields stay zero; this demo draws
nothing lit.

**Paused** freezes time rather than skipping the passes: `Update` sets the time
step to zero, so nothing is emitted, nothing ages, and nothing moves, while
every pass still runs. The draw, the readback, and the timings then work the
same paused as running. With nothing changing they are cheap anyway, and there
is no second path through `Record` to get wrong.

---

## Checkpoint — the fountain

`Record` is written. What stands between it and the exit check is the panel and
its numbers (section 7), the timings (section 8), and `Teardown` (section 9).
None of that is needed to see the fountain, so borrow three pieces now, each
final as written:

- Section 9's `Teardown` and the registration line, then rerun
  `GenerateProjects.bat` for the new files.
- Section 7's constructor, which puts the camera where it can see the fountain.
- Section 8's `WriteTimestamp`. It does nothing while there is no query pool,
  and until section 8 there is none.

And three stand-ins, each replaced by its section:

- **`CreateTimestamps`** returns `InitializationResult::success()` and creates
  nothing, so `m_queryPool` stays null and `Record` skips the reset.
- **`ReadResults`** is empty: no counts or timings come back yet.
- **`Update`** moves the camera and keeps the time, without the particle panel:

```cpp
// Section 6's checkpoint: the camera and the time step. Section 7 adds the particle panel and pausing.
void ParticlesDemo::Update(const FrameInput& input)
{
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    m_controls.Update(input.deltaSeconds, m_cameraTransform);
    scene::drawCameraPanel(m_camera, m_controls, m_cameraTransform);

    m_time      = input.elapsedSeconds;
    m_deltaTime = input.deltaSeconds;
}
```

Pick **Particles** in the demo picker, with validation on:

- [ ] A fountain of orange dots rises from the centre of the grid, falls,
      bounces, and fades, at the settings' defaults: 4000 a second, each living
      about 3 seconds.
- [ ] Orbiting the camera below the ground hides the fountain behind the floor.
- [ ] Synchronization validation, with the shader-access setting on, is silent,
      through resizing too.

Section 7 puts the numbers beside it, and replaces the last two stand-ins.

---

## 7. The panel, and the numbers that come back

**This is `Update`**, in place of the checkpoint's. Camera input and Chapter
10's camera panel first, then the particle panel, then this frame's time step:

```cpp
void ParticlesDemo::Update(const FrameInput& input)
{
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    m_controls.Update(input.deltaSeconds, m_cameraTransform);
    scene::drawCameraPanel(m_camera, m_controls, m_cameraTransform);

    m_resetRequested |= drawParticlePanel(m_settings, m_latest, m_latestList, m_timings,
                                          m_queryPool != VK_NULL_HANDLE);

    m_time      = input.elapsedSeconds;
    m_deltaTime = m_settings.paused ? 0.0f : input.deltaSeconds;   // paused: time stands still
}
```

The **camera starts** orbiting the fountain from a little above, set in the
constructor the way Chapter 10's cubes do it:

```cpp
ParticlesDemo::ParticlesDemo()
{
    // Orbiting the fountain from a little above, far enough to see it land.
    m_controls.active         = scene::ControllerKind::Orbit;
    m_controls.orbit.target   = glm::vec3(0.0f, 1.5f, 0.0f);
    m_controls.orbit.distance = 14.0f;
    m_cameraTransform.rotation    = scene::rotationFromYawPitch({ .yaw   = glm::radians(20.0f),
                                                                  .pitch = glm::radians(-15.0f) });
    m_cameraTransform.translation = m_controls.orbit.target
                                  - m_cameraTransform.Forward() * m_controls.orbit.distance;
}
```

**This is `drawParticlePanel`**, a free function in the demo's namespace, as in
Chapter 20. It returns true when the pool must be reset. Its four groups of
controls are more than its place under "Camera" shows at once, so it folds
them, as Chapter 09 section 6 describes: the counts stay in view, and each group
is a collapsing header, closed until you click it.

```cpp
// Section 7. Edits the settings and shows what came back from the GPU. True when
// the pool must be reset.
static bool drawParticlePanel(ParticleSettings& settings, const ParticleCounters& counters,
                              uint32_t drawnList, const ParticleTimings& timings, bool timed)
{
    bool reset = false;
    if (debug_panels::beginDemoPanel("Particles", debug_panels::DemoPanelSlot::BelowCamera))
    {
        // Little's law: at equilibrium, alive = rate x average lifetime.
        const float expected = std::min(settings.emitRate * settings.lifetime,
                                        static_cast<float>(settings.maxParticles));
        ImGui::Text("Alive     %u  (expected about %.0f)", counters.aliveCount[drawnList], expected);
        ImGui::Text("Free      %u", counters.deadCount);
        ImGui::Text("Emitted   %u this frame", counters.emitCount);
        ImGui::TextDisabled("Read back %u frames late, without waiting.", FRAMES_IN_FLIGHT);
        if (timed)
        {
            ImGui::Text("GPU ms    emit %.3f  simulate %.3f  end %.3f", timings.emit, timings.simulate, timings.end);
            ImGui::Text("          ground %.3f  particles %.3f", timings.ground, timings.draw);
        }

        // The counts stay in view; each group of controls folds away under its name (Chapter 09 section 6).
        if (ImGui::CollapsingHeader("Emitter"))
        {
            ImGui::SliderFloat("Rate (per s)", &settings.emitRate, 0.0f, 100000.0f, "%.0f", ImGuiSliderFlags_Logarithmic);
            ImGui::SliderFloat("Speed (m/s)", &settings.speed, 0.0f, 30.0f);
            ImGui::SliderFloat("Speed variation", &settings.speedVariation, 0.0f, 1.0f);
            ImGui::SliderFloat("Spread (deg)", &settings.spreadDegrees, 0.0f, 90.0f);
            ImGui::SliderFloat("Lifetime (s)", &settings.lifetime, 0.1f, 10.0f);
            ImGui::SliderFloat("Lifetime variation", &settings.lifetimeVariation, 0.0f, 1.0f);
        }

        if (ImGui::CollapsingHeader("Forces"))
        {
            ImGui::SliderFloat("Gravity (m/s2)", &settings.gravity, -5.0f, 20.0f);
            ImGui::SliderFloat("Drag (per s)", &settings.drag, 0.0f, 5.0f);
            ImGui::SliderFloat("Restitution", &settings.restitution, 0.0f, 1.0f);
            ImGui::SliderFloat("Friction", &settings.friction, 0.0f, 1.0f);
        }

        if (ImGui::CollapsingHeader("Look"))
        {
            ImGui::ColorEdit4("Start color", settings.startColor);
            ImGui::ColorEdit4("End color", settings.endColor);
            ImGui::SliderFloat("Start size (m)", &settings.startSize, 0.005f, 1.0f, "%.3f", ImGuiSliderFlags_Logarithmic);
            ImGui::SliderFloat("End size (m)", &settings.endSize, 0.005f, 1.0f, "%.3f", ImGuiSliderFlags_Logarithmic);
            ImGui::Combo("Blending", &settings.blend, "Additive\0Premultiplied alpha\0");
        }

        if (ImGui::CollapsingHeader("Pool"))
        {
            // AlwaysClamp: the shaders index every pool buffer with this, so even a value typed with
            // Ctrl+click must stay within PARTICLE_CAPACITY, and at least 1 for the reset (section 3).
            reset |= ImGui::SliderInt("Max particles", &settings.maxParticles, 1024, 1 << 20, "%d",
                                      ImGuiSliderFlags_Logarithmic | ImGuiSliderFlags_AlwaysClamp);
            ImGui::Checkbox("Paused", &settings.paused);
            reset |= ImGui::Button("Reset");
        }
    }
    ImGui::End();
    return reset;
}
```

**The colors are sRGB in the panel and linear on the GPU**, which is why
`RecordParticles` passed them through `srgbToLinear` (section 5).

### Reading the counters back

**This is `ReadResults`**, at the start of `Record`. Its first half is Chapter 20
section 9's readback, unchanged except for remembering which alive list was
drawn. Section 8 explains the second half.

```cpp
void ParticlesDemo::ReadResults(uint32_t frameIndex)
{
    // Chapter 20 section 9: this slot's fence has been waited on, so what it
    // copied and timed the last time it ran is complete. Neither call waits.
    if (m_readbackPending[frameIndex])
    {
        readBuffer(m_vulkan, m_readback[frameIndex], &m_latest, sizeof(m_latest));
        m_latestList                  = m_readbackList[frameIndex];
        m_readbackPending[frameIndex] = false;
    }

    if (m_timestampsPending[frameIndex])
    {
        uint64_t ticks[TIMESTAMP_COUNT]{};
        if (vkGetQueryPoolResults(m_vulkan.device, m_queryPool, frameIndex * TIMESTAMP_COUNT, TIMESTAMP_COUNT,
                                  sizeof(ticks), ticks, sizeof(uint64_t), VK_QUERY_RESULT_64_BIT) == VK_SUCCESS)
        {
            // Unsigned subtraction, then the mask: correct across one wrap-around.
            const auto milliseconds = [&](uint32_t from, uint32_t to) {
                return static_cast<float>(static_cast<double>((ticks[to] - ticks[from]) & m_timestampMask)
                                          * m_timestampPeriod * 1e-6);
            };
            m_timings = ParticleTimings{
                .emit     = milliseconds(0, 1),
                .simulate = milliseconds(1, 2),
                .end      = milliseconds(2, 3),
                .ground   = milliseconds(3, 4),
                .draw     = milliseconds(4, 5),
            };
        }
        m_timestampsPending[frameIndex] = false;
    }
}
```

### What the numbers should say

The panel's "expected" is **Little's law**: in a steady state, the number of things
in a system equals the rate they arrive times how long each stays. At 4000 a
second and an average lifetime of 3 seconds, about 12,000 particles are alive
once the first ones have had time to die. Two corrections, both small:

- A particle dies in the first frame its age reaches its lifetime, which is on
  average half a frame early, so the count is `rate x (lifetime - dt/2)`. At
  20 ms frames that is 11,960.
- The readback is two frames old, which does not matter once the count is steady.

If the count settles far from that, something is wrong: particles dying early,
or emission being lost. If "Alive" plus "Free" is not "Max particles", a count
was read before it was final. Set "Max particles" below rate x lifetime and the
alive count pins at the maximum, "Free" drops to around zero, and "Emitted"
falls to however many died that frame. The pool is full, and begin's clamp is
doing its job.

---

## 8. What each pass costs

CPU frame time does not say what the GPU spent. To answer "is it the
simulation or the drawing?", the GPU has to report its own clock, and
**timestamp queries** are how it does. This section is where the tutorial
teaches them: Chapter 22 copies this code for the USD viewer, and Chapter 24
section 9 makes it the `GpuTimestamps` class.

### What a timestamp measures

A **query pool** is an array of slots the GPU can write results into. In a
timestamp pool, each slot holds a 64-bit count of the GPU's clock ticks.
`vkCmdWriteTimestamp2(commandBuffer, stage, pool, query)` records a command
that writes the clock into slot `query`, and `stage` says *when*: once every
command recorded before it has finished that stage. With `ALL_COMMANDS`, that
is once everything before it has finished.

So a timestamp does not mark an instant in one pass; it marks the point where
the GPU had finished everything before it. The difference between two of them
**bounds** the work recorded between them. It brackets a region and says
nothing about the instructions inside, and if two passes overlap, because no
barrier separates them, a difference can include part of the neighbour's work.
Particles has a barrier between every pass, so its passes run one after another
and each difference is one pass.

The other stage you will see in examples is `TOP_OF_PIPE`: a start marker there
is written as soon as the GPU reaches it, without waiting for earlier work. That
suits one region timed on its own, at the price that whatever earlier work was
still running is counted too. For a chain of regions, one stage for every
marker keeps every difference meaning the same thing, so this demo uses
`ALL_COMMANDS` throughout.

### From ticks to milliseconds

A tick is not a fixed time. `VkPhysicalDeviceLimits::timestampPeriod` is the
number of nanoseconds per tick on this GPU. With a period of 10 ns, a
difference of 120,000 ticks is 1,200,000 ns, which is 1.2 ms.

The counter is also not always 64 bits wide. Each queue family reports
`timestampValidBits`: between 36 and 64, or 0 for a family that cannot write
timestamps at all. The bits above that are zero, and the counter wraps to 0
when it overflows. Subtracting as unsigned 64-bit integers and then masking to
the valid bits gives the right difference even across a wrap. A toy 8-bit
counter shows how: the region starts at 250 and ends at 4, after the counter
passed 255. In 64-bit unsigned arithmetic `4 - 250` is 2^64 - 246, a huge
number, but its low 8 bits, `& 0xFF`, are 10, which is the true count: 5 ticks
up to 255, 1 to wrap to 0, and 4 more. The same holds at 36 bits for any region
shorter than one full wrap, which at 36 bits is over a minute even at 1 ns a
tick.

The bits are per queue family, and the demo does not know which family the
renderer chose, only that it can draw. Taking the fewest among the families
that can draw is safe: masking to fewer bits than the counter really has still
gives the right difference, as long as the region is shorter than that shorter
wrap.

### One block of queries per frame in flight

The pool holds `TIMESTAMP_COUNT` queries for each frame in flight. Frame slot
`i` owns the block that starts at its **base query**, `i * TIMESTAMP_COUNT`, and
the reset, the writes, and the read all count from there. Two rules decide
where those three go:

- **A query must be reset before it is written again**, with
  `vkCmdResetQueryPool`, and that command may not be inside a rendering scope.
  `Record` resets the slot's block at the top, before any pass.
- **Results are read only from a frame that has finished.** `ReadResults` reads
  the slot's block at the start of its next use, after `drawFrame` has waited
  on its fence, so `vkGetQueryPoolResults` finds the values ready and never
  waits. Asking for the current frame's results with `VK_QUERY_RESULT_WAIT_BIT`
  would stall the CPU until the GPU caught up, and destroy the overlap you were
  trying to measure. `VK_QUERY_RESULT_64_BIT` asks for 64-bit values.

### The code

**This is `timestampValidBits`**, at file scope above the namespace block:

```cpp
// File scope, above the namespace block. Section 8: the fewest valid timestamp bits of any
// queue family that can draw - one of them is the family recording the frame.
static uint32_t timestampValidBits(VkPhysicalDevice physicalDevice)
{
    uint32_t familyCount = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(physicalDevice, &familyCount, nullptr);
    std::vector<VkQueueFamilyProperties> families(familyCount);
    vkGetPhysicalDeviceQueueFamilyProperties(physicalDevice, &familyCount, families.data());

    uint32_t bits = 64;
    for (const VkQueueFamilyProperties& family : families)
    {
        if ((family.queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0)
        {
            bits = std::min(bits, family.timestampValidBits);
        }
    }
    return bits;
}
```

**This is `CreateTimestamps`.** A family with 0 valid bits has no timestamps;
the demo then runs without timings rather than refusing to start:

```cpp
InitializationResult ParticlesDemo::CreateTimestamps()
{
    // The period turns ticks into nanoseconds, and the valid bits give the mask.
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(m_vulkan.physicalDevice, &properties);
    m_timestampPeriod = static_cast<double>(properties.limits.timestampPeriod);

    const uint32_t validBits = timestampValidBits(m_vulkan.physicalDevice);
    if (validBits == 0)
    {
        return InitializationResult::success();   // no timestamps here: the panel just omits the timings
    }
    m_timestampMask = validBits >= 64 ? ~0ull : (1ull << validBits) - 1ull;

    const VkQueryPoolCreateInfo queryPoolInfo{
        .sType      = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO,
        .queryType  = VK_QUERY_TYPE_TIMESTAMP,
        .queryCount = TIMESTAMP_COUNT * FRAMES_IN_FLIGHT,
    };
    if (vkCreateQueryPool(m_vulkan.device, &queryPoolInfo, nullptr, &m_queryPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateQueryPool failed for the particle timings.");
    }
    return InitializationResult::success();
}
```

The mask is the valid bits set to 1: with 36 valid bits, `(1 << 36) - 1`. At 64
the shift would overflow, so all ones is written directly.

**This is `WriteTimestamp`**, which writes timestamp `which` of this slot's
block:

```cpp
void ParticlesDemo::WriteTimestamp(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t which)
{
    if (m_queryPool == VK_NULL_HANDLE) { return; }
    // ALL_COMMANDS: written once everything recorded before it has finished.
    vkCmdWriteTimestamp2(commandBuffer, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, m_queryPool,
                         frameIndex * TIMESTAMP_COUNT + which);
}
```

The six go at the start of `Record` (0), after emit (1), after simulate (2), after
end and the copy (3), after the scene pass (4), and after the particle pass (5),
so the five differences are the panel's five numbers. `Record` (section 6) resets
the block before timestamp 0, and `ReadResults` (section 7) turns the block into
milliseconds: the unsigned difference, the mask, then the period.

### What the numbers show

The absolute numbers depend on the GPU and the window, and so does the shape at
the defaults. With enough particles to keep a GPU busy, emit, simulate, and end
together cost a fraction of drawing the particles, and drawing them costs what
it does because of overdraw: every particle covers dozens of pixels and blends
each one. With few, a fast GPU has so little to do in a compute pass that the
fixed cost of its dispatches and barriers can be most of what the pass measures.
Before optimizing a pass, measure which pass it is.

---

## 9. Teardown, and registering the demo

**This is `Teardown`:**

```cpp
void ParticlesDemo::Teardown()
{
    // Chapter 09 waited for the device. Null handles are no-ops, so a partial
    // Setup is safe; the CPU state - settings and camera - is kept.
    vkDestroyQueryPool(m_vulkan.device, m_queryPool, nullptr);
    for (VkPipeline& pipeline : m_drawPipelines)
    {
        vkDestroyPipeline(m_vulkan.device, pipeline, nullptr);
        pipeline = VK_NULL_HANDLE;
    }
    VkPipeline* pipelines[] = { &m_groundPipeline, &m_resetPipeline, &m_beginPipeline,
                                &m_emitPipeline, &m_simulatePipeline, &m_endPipeline };
    for (VkPipeline* pipeline : pipelines)
    {
        vkDestroyPipeline(m_vulkan.device, *pipeline, nullptr);
        *pipeline = VK_NULL_HANDLE;
    }
    vkDestroyPipelineLayout(m_vulkan.device, m_drawLayout, nullptr);
    vkDestroyPipelineLayout(m_vulkan.device, m_groundLayout, nullptr);
    vkDestroyPipelineLayout(m_vulkan.device, m_computeLayout, nullptr);
    vkDestroyDescriptorPool(m_vulkan.device, m_descriptorPool, nullptr);   // frees the set
    vkDestroyDescriptorSetLayout(m_vulkan.device, m_setLayout, nullptr);

    for (AllocatedBuffer& readback : m_readback)
    {
        destroyBuffer(m_vulkan, readback);
    }
    AllocatedBuffer* buffers[] = { &m_indirect, &m_counters, &m_aliveLists, &m_deadList, &m_particles };
    for (AllocatedBuffer* buffer : buffers)
    {
        destroyBuffer(m_vulkan, *buffer);
    }
    m_sceneRenderer.Shutdown();

    m_queryPool      = VK_NULL_HANDLE;
    m_drawLayout     = m_groundLayout = m_computeLayout = VK_NULL_HANDLE;
    m_descriptorPool = VK_NULL_HANDLE;
    m_setLayout      = VK_NULL_HANDLE;
    m_set            = VK_NULL_HANDLE;
}
```

The settings and the camera survive; every handle goes back to `VK_NULL_HANDLE`,
so the next `Setup` starts clean. `SceneRenderer::Shutdown` releases set 0.

**Registering** is Chapter 09's one line in `Source/SandboxGame/Main.cpp`, plus
its include:

```cpp
#include "PillowFort/Demos/Particles/ParticlesDemo.h"
```

```cpp
    demoList.push_back(std::make_unique<demos::particles::ParticlesDemo>());
```

Then rerun `GenerateProjects.bat`: `ParticlesDemo.cpp` and nine shaders are new.

---

## 10. Exercise: soft particles

Look closely where the particles sit on the ground. Each quad cuts into the floor
along a straight, hard line, because the depth test is all or nothing per pixel.
**Soft particles** fade a particle out as it gets close to what is behind it, so
the line disappears. The idea is one comparison in the fragment shader:

```text
fade = clamp((distance to the scene behind this pixel - distance to this particle) / softDistance, 0, 1)
```

It needs the scene's depth *sampled*, not just tested. Chapter 10 already made
the two choices that allow it: the depth image has `SAMPLED` usage, and the
scene pass stores it (`STORE_OP_STORE`) rather than discarding it. Section 5
already moved it to `DEPTH_READ_ONLY_OPTIMAL`, the layout that allows sampling
an image that is also bound as the depth attachment. The rest is left to you.

**The fragment shader** reads the depth at its own pixel, turns both depths into
distances, and fades. It gains a binding, a helper, and a block before the
output:

```glsl
// Particle.frag.glsl, soft particles. Set 0 (FrameBlock.glsl) supplies frame.projection.
layout(set = 1, binding = 5) uniform sampler2D sceneDepth;   // the scene's depth, read-only

// Distance in front of the camera, in metres, from a [0, 1] depth value: the
// projection's depth row run backwards (Chapter 10 section 2).
float viewDistance(float depth)
{
    return frame.projection[3][2] / (depth + frame.projection[2][2]);
}

    // In main, after alpha is computed: fade out where the quad is about to cut
    // into the scene, instead of a hard line along the intersection.
    if (appearance.softDistance > 0.0)
    {
        float scene = viewDistance(texelFetch(sceneDepth, ivec2(gl_FragCoord.xy), 0).r);
        float self  = viewDistance(gl_FragCoord.z);
        alpha *= clamp((scene - self) / appearance.softDistance, 0.0, 1.0);
    }
```

A depth value is not a distance: perspective packs most of `[0, 1]` close to the
camera. `viewDistance` runs Chapter 10's projection backwards. Depth is
`(P[2][2] * z + P[3][2]) / -z` for a view-space `z`, so the distance `-z` is
`P[3][2] / (depth + P[2][2])`, using the same `frame.projection` the vertex
shader projected with. `texelFetch` reads one texel with no filtering, which is
what depth needs, and its integer coordinates are `gl_FragCoord.xy`, because the
particle pass covers the same pixels as the depth image.

**What else changes**, each a small step you have done before:

- `ParticleAppearance` gains `softDistance` and padding to 64 bytes. The
  fragment shader now reads the push constants, so the range's stages and the
  `vkCmdPushConstants` call both become `VERTEX | FRAGMENT`, and the fragment
  shader includes `FrameBlock.glsl` and `ParticleTypes.h` and declares the push
  block as the vertex shader does.
- Binding 5 of the particle set: a combined image sampler for the fragment
  stage, with a nearest-filtering sampler created beside the set. The
  descriptor pool gains a second size, so `poolSizeCount` becomes 2:
  `{ VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1 }`, and the storage buffers'
  count becomes a plain 5, because `std::size(bindings)` now counts the sampler
  too. A pool is counted type by type, by each set's layout: as section 1 wrote
  it, it holds six storage buffers and no sampler, which some drivers allocate
  from anyway and others fail with `VK_ERROR_OUT_OF_POOL_MEMORY`. Validation
  says nothing. The depth view changes with the window, so the binding
  is written in `Resize`, the one place Chapter 09 guarantees comes after a
  wait, with the layout `DEPTH_READ_ONLY_OPTIMAL`.
- **The barriers** gain the new reader. Into the scope, the depth transition's
  destination adds `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ`: without it the
  layout transition is not made visible to the shader's read, and sync
  validation reports `SYNC-HAZARD-READ-AFTER-WRITE` at the draw. That is your
  positive control. The return trip's source can add `FRAGMENT_SHADER` too; it
  is already implied, since `LATE_FRAGMENT_TESTS` comes after the fragment
  shader, but naming it says what the barrier is for.

To see it, make the particles large (half a metre) and bring the camera down
near the floor. Without the fade, every dot resting on the ground ends in a hard
horizontal edge; with `softDistance` at 0.25 m, the edges are gone and the dots
melt into the floor. On a multisampled scene (Chapter 18) the sampled depth is
the resolved one, so along the edges of geometry the fade is a pixel off, which
soft dots hide completely.

---

## When it does not work

| Symptom | Likely cause |
| --- | --- |
| Nothing draws; the panel says thousands are alive | The draw reads the wrong alive list: `aliveList` must be the list simulate *filled* (`m_currentList` after the flip) |
| Nothing draws, and "Alive" is 0 | Begin's dispatch sizes or end's draw arguments are not reaching the commands: check the barrier after begin includes `DRAW_INDIRECT` / `INDIRECT_COMMAND_READ`, and that the indirect buffer has `INDIRECT_BUFFER` usage |
| "Alive" + "Free" is not "Max particles" | A count read before it was final, a missing barrier between two passes, or a reset that did not run after "Max particles" changed |
| Particles leave in clumps, or along the same paths every frame | The random stream is seeded from the frame alone, or from the invocation alone (section 3) |
| A hang or a device-lost when emitting | Popping more than the dead list holds: the emit pass must stop at `counters.emitCount`, which begin clamped |
| Particles flicker in size or color | Variation keyed by `gl_InstanceIndex`, which changes order every frame, instead of by the slot |
| Square dark or missing patches inside the cloud | Depth write left on for the particles |
| The fountain shows through the ground from below | Depth test off for the particles, or the particle scope bound no depth attachment |
| Colors lighter than their swatches | The sRGB-to-linear conversion is missing |
| Validation: storage buffer in the vertex stage must be NonWritable | `readonly` missing in `Particle.vert.glsl` |
| Validation: pipeline sample count does not match | The particle pipeline was built with the scene's sample count; it draws after the resolve, at 1x |
| The fountain stops after a long hitch and restarts in a burst | The frame time is clamped (Chapter 09) and the emission follows it; this is correct |

---

## Exit check

- [ ] Rerun `GenerateProjects.bat`, build, and pick **Particles** in the demo
      picker. A fountain of orange dots rises, falls onto the grid, bounces, and
      fades.
- [ ] At the defaults (4000 a second, 3 s lifetime), "Alive" climbs for about four
      seconds and then holds near 12,000, within about a percent, and stays
      there. "Alive" plus "Free" equals "Max particles" every frame.
- [ ] **Max particles** 4096: "Alive" pins at the limit, "Free" drops to near
      zero, the fountain thins, and nothing corrupts. Raise it again and the pool
      resets and refills.
- [ ] Spread, gravity (try negative), drag, restitution, and friction all
      visibly do what they say. Paused freezes everything, with the counts and
      timings still live.
- [ ] Drag the orbit camera below the ground: the ground hides the fountain.
      Only the dots resting on the floor still show a little. Their quads
      straddle the plane, so their lower halves are genuinely below it.
- [ ] Switch to **Premultiplied alpha**, set both sizes to 0.6 m and the end
      color to an opaque blue. The orange core of young particles draws over
      blue ones in front of it, the order problem section 5 describes. With
      **Additive**, the same particles sum toward white instead, whatever the
      order. Switch back.
- [ ] The panel shows GPU milliseconds for emit, simulate, end, the ground, and the
      particles.
- [ ] Synchronization validation, with Chapter 02's shader-access setting on, is
      silent through all of the above, through resizing, and through switching to
      another demo and back. Quitting reports no leaked VMA allocation.
- [ ] **Positive control.** Delete the `memoryBarrier` after the end pass in
      `RecordCompute`. The first frame must report
      `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDrawIndirect`, for the indirect
      buffer written by `vkCmdDispatch` and for the vertex shader's reads. If it
      reports nothing, the shader-access setting is off (Chapter 20 section 5).
      Put the barrier back.
- [ ] On a real GPU: raise "Max particles", "Lifetime", and the rate to the
      top of their sliders, for about a million alive (100,000 a second for
      10 s). Watch which pass grows. Expect the draw, not the simulation.

---

## Where to go from here

The fountain has one emitter, a point that throws particles into a cone, and
its color runs in a straight line from start to end. A particle system in a
game has many emitters of different shapes, bursts as well as steady rates,
and colors that follow a curve. This tutorial does not build any of that. What
follows is how it would fit the passes you have, if you want to build it
yourself.

**What stays.** Simulate, end, the draw, and every barrier in this chapter are
untouched by everything below. Emitters change two things only: who decides how
many particles start this frame, and where each one starts. Everything from the
emit pass's last line onwards is the same system.

**Many emitters, counted on the GPU.** Today the CPU works out one number,
`emitRequest`, and begin clamps it. With several emitters, move what describes
an emitter into a storage buffer, one struct each:
- its shape and its transform;
- its rate, and the fraction of a particle it carried over from last frame (the
  `m_emitCarry` of section 4, kept on the GPU now);
- a burst count, spent once and then zeroed;
- its speed and lifetime ranges;
- which row of the color ramp it uses (below).

Keeping the carried fraction in that buffer, rather than on the CPU, means a
GPU pass can change an emitter's rate without a round trip. Two passes then
change:
- **Begin** runs one invocation per emitter instead of one in total. Each
  works out its own count. A running total turns the counts into a table of
  where each emitter's particles start: emitter k starts where emitters 0 to
  k − 1 end. With a few dozen emitters, one workgroup builds that table. The
  clamp to the dead list's count stays, on the total.
- **Emit** still runs once per new particle. Each invocation finds its emitter
  by searching the table for the last start at or below its own index (a
  binary search, since the table is sorted by construction), then samples that
  emitter's shape.

**Or requests, as the sea does.** Chapter 31 section 6 takes another route.
Any pass appends a request (where a particle starts, its velocity, its
lifetime) to a buffer with `atomicAdd`, begin reads the request count instead
of a pushed number, and emit copies one request per invocation. That separates
who decides from who emits:
- the CPU's emitters become one more small pass that writes requests;
- an impact (Chapter 31) writes requests;
- a particle dying can write one too, from the simulate pass, which is how
  "sub-emitters" (sparks that leave smoke) work. They are emitted next frame.

The price is a request's worth of memory and one extra write and read per new
particle. The emitter table computes the same values inside emit instead.

**Shapes.** A shape is a function from a few random numbers to a starting
point, and sometimes a direction:
- a sphere's surface is section 3's `randomInCone` with a half-angle of π;
- a box is three uniform numbers;
- a disc of radius R takes R√u for the distance from its centre, because the
  area within a radius grows as its square, so a plain uniform u would crowd
  the middle.

A mesh's surface takes two steps. First pick a triangle in proportion to its
area, from a running total of the triangles' areas (built once, on the CPU)
and a binary search. Then pick a point inside the triangle, with barycentric
weights (1 − √u, √u(1 − v), √u·v) for two uniform numbers u and v. If simulate
or the draw need anything per emitter, each particle needs its emitter's
index. Both `w` components of `Particle` are taken, so that means a third
`vec4` or a packed field.

**Color over life as a ramp.** `Particle.vert` mixes `startColor` and
`endColor` by how far through its life a particle is. That is a ramp with two
keys. Fire that starts white, turns orange, and ends as dark smoke needs more
keys, but keeps the same shape: a list of (life, color) keys, where the shader
finds the two keys around `life` and mixes between them. There are two ways to
hand the ramp to the shader:
- **A few keys in the push constants.** Today the appearance block uses 48 of
  the 128 bytes every device guarantees. Replacing the two colors with four
  color keys and one `vec4` of their positions still fits. Beyond that, the
  keys go in a uniform buffer, one per frame in flight. Either way they are
  picked in ImGui, so they are sRGB and need section 5's `srgbToLinear`.
- **An image, for many keys or a painted gradient.** Use 256 × 1 texels per
  ramp, one row per emitter, sampled with linear filtering and `CLAMP_TO_EDGE`
  at (life, row). Upload it with Chapter 08's `uploadToImage`. Use an `_SRGB`
  format if the pixels are sRGB, so the sampler decodes them before it
  filters. If a panel edits the ramp live, frames still in flight may be
  reading the image the upload overwrites. Wait for the device to go idle
  before the upload (an edit is rare), or keep one image per frame in flight.

Size over life is the same idea in one channel. The ramp's alpha is a natural
home for it, or for opacity.

Next: [22 — Deferred Shading](22-Deferred-Shading.md)
