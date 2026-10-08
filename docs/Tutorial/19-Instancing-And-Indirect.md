# 19 — Instancing and Indirect Draws

**Goal:** a forest of four thousand trees, imported from a USD `PointInstancer`,
drawn with a handful of draw calls — each one drawing every visible tree of one
kind, its parameters read by the GPU from a buffer — with the counts on a panel,
read back from that buffer.

**ROADMAP:** step 20.

**Module:**

- `Source/PillowFort/VulkanGraphics/`, `pf::vulkan_graphics` — `SceneRenderer`
  draws in batches: a per-instance buffer at set 0 binding 2, one shared vertex
  and index buffer for every mesh, and an indirect command buffer. Chapter 17's
  shadow casters are batched the same way.
- `Source/PillowFort/UsdImport/UsdImport.cpp`, `pf::usd_import` — `instanceable`
  prims and `PointInstancer`s, with meshes shared between instances.

Shaders: `Shaders/Scene/Mesh.vert.glsl` and Chapter 17's
`Shaders/Shadows/ShadowDepth.vert.glsl` read the per-instance buffer.

**Prerequisites:**

- Chapter 02 sections 5-7 — the feature chain, which gains two indirect-draw
  features.
- Chapter 04 section 5 — barriers, for the shared buffers' uploads and for
  section 7's look ahead, and that a barrier orders everything submitted before
  it on the queue, not only its own command buffer.
- Chapter 08 sections 2, 6, and 8 — `createBuffer`, `immediateSubmit`, the
  per-frame-copies rule, and `std430`.
- Chapter 09 — `Record` runs after the frame's fence wait, which is what makes
  the per-frame buffers safe to rewrite and to replace.
- Chapter 11 — `SceneRenderer::AddMesh`, `GpuMesh`, `DrawData`, the vertex
  input, and `RecordDraws`, all of which this chapter changes.
- Chapter 12 — `DrawItem`, `Scene::CollectDraws` and its per-node frustum
  culling.
- Chapter 14 — `importPrim`, `asXformable`, the mesh import path (`addMesh`), and
  the fact that TinyUSDZ's loader does not compose references (Chapter 13).
- Chapter 15 section 7 — `GpuMaterial` and set 1, bound per material.
- Chapter 17 section 9 — `RecordShadows` and its caster callback.

---

## What you are actually writing

Chapter 11 drew a mesh with one `vkCmdDrawIndexed` and its model matrix in a
push constant; Chapter 12 turned the scene into a list of such draws, one per
visible submesh. That list is the input here, unchanged. What changes is
everything between the list and the GPU:

```text
 Scene::CollectDraws ──▶ DrawItem[]  (Chapter 12: one per visible submesh, culled per node)
 ──────────────────────────────────────────────── SceneRenderer, in the demo's Record ─────
 PrepareDraws (sections 3-6), on the CPU:
   sort the items so that equal (mesh, submesh, material) sit together
   every item's matrices ──▶ the instance buffer, set 0 binding 2, in sorted order
   every run of equal items ──▶ ONE VkDrawIndexedIndirectCommand: instanceCount = its length
   every run of commands with the same material ──▶ one DrawRun
 RecordDraws / RecordBatches (section 6), into the command buffer:
   bind the shared vertex and index buffers once (section 4)
   per DrawRun: bind its pipeline and material, then ONE vkCmdDrawIndexedIndirect
 ──────────────────────────────────────────────────────────────────────────────────────────
 Mesh.vert.glsl: instances[gl_InstanceIndex].model
```

The files, and what each section changes:

```text
VulkanInstance.cpp                    two features, queried and enabled            section 6
Shaders/Include/SharedShaderTypes.h   InstanceData; ShadowDrawData shrinks         sections 3, 8
VulkanGraphics/SceneRenderer.h/.cpp   binding 2, the shared geometry buffers,      sections 3-6, 8
                                      PrepareDraws, RecordBatches, RecordDraws,
                                      RecordShadows
Shaders/Scene/Mesh.vert.glsl          the instance buffer replaces DrawData        section 3
Shaders/Shadows/ShadowDepth.vert.glsl the same, for Chapter 17's casters           section 8
UsdImport/UsdImport.cpp               class prims skipped, a mesh cache,           sections 9-10
                                      instanceable prims, importPointInstancer
Demos/UsdViewer/UsdViewerDemo.cpp     the "Instancing" panel; PrepareDraws         sections 6, 8
Assets/Scenes/make_forest.py          writes Forest.usda                           section 11, Appendix A
```

### What `SceneRenderer` becomes

```cpp
// Source/PillowFort/VulkanGraphics/SceneRenderer.h - Chapter 19's additions and replacements.

// How RecordBatches issues the same commands. Every mode draws the same image; they differ
// in how many calls it takes (section 6).
enum class DrawMode : uint32_t
{
    OnePerItem     = 0,   // a vkCmdDrawIndexed per DrawItem: Chapter 11's way, for comparison
    Instanced      = 1,   // a vkCmdDrawIndexed per command, instanceCount > 1
    Indirect       = 2,   // a vkCmdDrawIndexedIndirect per command
    MultiDraw      = 3,   // a vkCmdDrawIndexedIndirect per run: drawCount > 1 (multiDrawIndirect)
};

// The two lists PrepareDraws batches: the camera's, and Chapter 17's unculled shadow casters.
enum class DrawList : uint32_t { Scene = 0, ShadowCasters = 1 };
inline constexpr uint32_t DRAW_LIST_COUNT = 2;

// Where one mesh sits in the shared geometry buffers (section 4).
struct MeshRange
{
    int32_t                     vertexOffset = 0;   // added to every index of the mesh
    uint32_t                    firstIndex   = 0;   // its first index in the shared index buffer
    std::vector<scene::Submesh> submeshes;          // index ranges relative to firstIndex
    bool                        doubleSided  = false;
};

// Consecutive commands that share everything bound around them: one material (so one
// pipeline and one set 1), one cull mode. A multi-draw draws a whole run in one call.
struct DrawRun
{
    uint32_t firstCommand = 0;
    uint32_t commandCount = 0;
    uint32_t material     = 0;
    bool     doubleSided  = false;
};

// What PrepareDraws did with the Scene list, for the panel (section 6).
struct DrawStatistics
{
    uint32_t items           = 0;   // DrawItems in
    uint32_t commands        = 0;   // indirect commands (batches) out
    uint32_t runs            = 0;
    uint32_t drawCalls       = 0;   // vkCmdDraw* calls RecordDraws makes in the current mode
    uint32_t largestInstance = 0;   // the largest instanceCount
};

class SceneRenderer
{
public:
    // ...Chapters 10-17, except as below...

    // Chapter 19: replaces Chapter 11's RecordDraws(commandBuffer, frameIndex, draws).
    // In Record, after the fence wait and BEFORE anything that binds set 0. Sorts and batches
    // both lists and writes this frame slot's instance and indirect buffers.
    void PrepareDraws(uint32_t frameIndex, std::span<const scene::DrawItem> sceneDraws,
                      std::span<const scene::DrawItem> shadowCasters = {});
    // Inside the scene pass: the Scene list, with the mesh pipelines.
    void RecordDraws(VkCommandBuffer commandBuffer, uint32_t frameIndex) const;
    // Binds the shared geometry, then for each run calls `bindRun` (which binds whatever the
    // run needs) and issues its draws in the current DrawMode.
    void RecordBatches(VkCommandBuffer commandBuffer, uint32_t frameIndex, DrawList list,
                       const std::function<void(VkCommandBuffer, const DrawRun&)>& bindRun) const;

    void     SetDrawMode(DrawMode mode) { m_drawMode = mode; }
    DrawMode GetDrawMode() const { return m_drawMode; }
    const DrawStatistics& Statistics(uint32_t frameIndex) const { return m_statistics[frameIndex]; }
    // The Scene list's commands, read from the buffer the GPU reads them from.
    std::span<const VkDrawIndexedIndirectCommand> IndirectCommands(uint32_t frameIndex) const;

    // Chapter 17's RecordShadows loses its `casters` parameter (section 8):
    void RecordShadows(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                       const scene::Camera& camera, const glm::mat4& view, float aspect,
                       std::optional<glm::vec3> sunDirection, const ShadowSettings& settings,
                       const ShadowCasterCallback& extraCasters = {});

private:
    bool GrowGeometry(uint32_t vertexCount, uint32_t indexCount);        // section 4
    bool EnsureFrameCapacity(uint32_t frameIndex, uint32_t instances);   // section 3

    // Section 4: every mesh in two buffers. Replaces Chapter 11's std::vector<GpuMesh> m_meshes.
    AllocatedBuffer        m_vertices;
    AllocatedBuffer        m_indices;
    uint32_t               m_vertexCount    = 0;
    uint32_t               m_vertexCapacity = 0;
    uint32_t               m_indexCount     = 0;
    uint32_t               m_indexCapacity  = 0;
    std::vector<MeshRange> m_meshRanges;

    // Sections 3, 5, and 6: one set per frame in flight.
    struct FrameDraws
    {
        AllocatedBuffer                                     instances;   // set 0 binding 2
        AllocatedBuffer                                     indirect;    // VkDrawIndexedIndirectCommand[capacity]
        uint32_t                                            capacity = 0;   // instances (and commands)
        std::vector<VkDrawIndexedIndirectCommand>           commands;    // the CPU's copy
        std::array<std::vector<DrawRun>, DRAW_LIST_COUNT>   runs;
    };
    std::array<FrameDraws, FRAMES_IN_FLIGHT>     m_frameDraws;
    std::array<DrawStatistics, FRAMES_IN_FLIGHT> m_statistics{};
    std::vector<uint32_t>                        m_order;   // PrepareDraws' scratch, reused
    DrawMode                                     m_drawMode = DrawMode::MultiDraw;
};
```

`SceneRenderer.h` gains `<functional>`; `SceneRenderer.cpp` gains `<tuple>`.

> **Jump:** so far one call drew one thing, and everything the shader knew about
> that thing came with the call — Chapter 11's push constant. From here a call
> draws **many** things, and the shader learns which one it is drawing from a
> number Vulkan hands it, `gl_InstanceIndex`, which it uses to look itself up in
> a buffer. Hold onto that indirection: an instance is *an index into an array*,
> and the array is written separately from the draw. Every GPU-driven technique
> in the chapters after this one — particles, grass — is that indirection with
> the array written by a compute shader instead of the CPU.

---

## 1. One call, many instances

Every draw call costs CPU time before the GPU sees it: the driver validates
state, translates the call into the GPU's own command format, and writes it
into the command buffer. A few microseconds each — nothing for the dozens of
draws in Chapter 15's test scenes, and the whole frame for the eight thousand
draws a forest of four thousand two-part trees needs. On top of that, every
draw re-binds whatever changed, and the shadow pass from Chapter 17 does it all
again, once per cascade.

Most of those draws are the same draw. Every pine trunk is the same mesh with
the same material; only its model matrix differs. **Instancing** says that
once: one call, `instanceCount` copies. Vulkan runs the vertex shader for every
vertex of every instance, and tells it which instance it is working on in
`gl_InstanceIndex`.

Three things to work out, and this chapter takes them in order:

- Where does each instance's matrix come from, if not from the call?
  (Sections 2 and 3.)
- Which draws can become one instanced draw, and how does the renderer find
  them in an arbitrary list? (Sections 4 and 5.)
- If the calls are now few and uniform, can their parameters live in a buffer
  instead of in the command stream — where a compute shader could write them?
  (Section 6.)

---

## 2. Two ways to feed per-instance data

**Instance-rate vertex attributes.** A vertex buffer binding can be declared
with `VK_VERTEX_INPUT_RATE_INSTANCE`: its attributes then advance once per
instance instead of once per vertex. Bind a buffer of matrices as a second
vertex buffer, describe a `mat4` as four `vec4` attributes (a vertex attribute
is at most four components), and the vertex shader receives its instance's
matrix as ordinary inputs. `firstInstance` offsets where in that buffer the
instances start. It is the classic method and it is fast.

**A storage buffer indexed by `gl_InstanceIndex`.** Write the per-instance data
into a storage buffer, and have the vertex shader read
`instances[gl_InstanceIndex]`.

This tutorial uses the storage buffer, for reasons that matter more as the
chapters go on:

- **Compute writes it.** Chapter 21's particles and Chapters 26 and 27's grass
  generate their instances in compute shaders. A storage buffer is what compute
  writes; the draw then reads the same buffer with no format conversion, no
  vertex input state to keep in sync, and no second copy.
- **Any layout.** A storage buffer holds whatever struct you declare — matrices,
  indices, colors, a material number — read with `std430` rules (Chapter 08
  section 8). Vertex attributes are limited to vertex formats and to four
  components each, so a `mat4` is four attributes and a `mat3` with padding is
  three more.
- **Indirection.** An entry can point at another: an instance can carry the
  index of its material or of a bone palette. Attributes cannot be indexed.
- **The pipeline does not change.** The vertex input state describes the
  mesh's vertices only, as in Chapter 11; one pipeline serves instanced and
  non-instanced draws.

The cost is a storage-buffer load per vertex, which every desktop GPU caches
well. Mobile GPUs that fetch vertex attributes with fixed-function hardware
are the case where instance-rate attributes still win.

**`gl_InstanceIndex` in Vulkan includes `firstInstance`.** A draw with
`firstInstance = 100` and `instanceCount = 3` runs its vertices with
`gl_InstanceIndex` 100, 101, and 102. That is the difference from OpenGL's
`gl_InstanceID`, which started at 0, and it is what makes the scheme work: one
buffer holds every instance of every draw in the frame, and each draw's
`firstInstance` says where its own instances start.

---

## 3. The instance buffer

One entry per drawn instance: the model matrix and the normal matrix — exactly
what Chapter 11's `DrawData` push constant carried per draw, minus the color
Chapter 15 retired. The normal matrix stays precomputed on the CPU: inverting
a matrix per vertex, per instance, would cost more than storing 48 bytes.

```c
/* Shaders/Include/SharedShaderTypes.h - Chapter 19. One drawn instance: set 0 binding 2,
   std430, indexed by gl_InstanceIndex. */
struct InstanceData
{
    mat4 model;          /*  0  local -> world */
    mat3 normalMatrix;   /* 64  transpose(inverse(mat3(model))); std430: three 16-byte columns */
};                       /* 112 */

#ifdef __cplusplus
    static_assert(sizeof(InstanceData) == 112, "InstanceData layout drifted.");
    static_assert(offsetof(InstanceData, normalMatrix) == 64, "InstanceData alignment drifted.");
    }
#endif
```

It goes at the end of the header, after the last struct's asserts, and the
closing brace of `namespace pf::shared` moves below it — Chapter 11's
pattern.

`mat3` is Chapter 11's alias for `glm::mat3x4` on the C++ side, for the reason
Chapter 11 gave: `std430` stores each of a `mat3`'s three columns in 16 bytes.

### Set 0, binding 2

It is CPU-written every frame, so it follows the light buffer's pattern from
Chapter 16: one host-visible buffer per frame in flight, persistently mapped,
written in `Record` after the fence wait. The binding joins
`CreateFrameResources`' array:

```cpp
// SceneRenderer.cpp, CreateFrameResources (Chapter 19): binding 2 joins the set 0 layout's array.
{ .binding         = 2,
  .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
  .descriptorCount = 1,
  .stageFlags      = VK_SHADER_STAGE_VERTEX_BIT },
```

and the pool's storage-buffer line, Chapter 16's, doubles:

```cpp
// The set 0 pool's sizes (Chapter 19): one storage buffer per frame for the lights, one for the instances.
{ VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 2 * FRAMES_IN_FLIGHT },
```

Each frame's buffers are created by the same function that grows them, called
once per slot at the end of `CreateFrameResources` — a descriptor the shader
reads must point at a buffer before the first draw:

```cpp
// At the end of CreateFrameResources (Chapter 19): every slot starts with room for 1024 instances.
for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
{
    if (!EnsureFrameCapacity(i, 1))
    {
        return InitializationResult::failure("Creating the instance and indirect buffers failed.");
    }
}
```

`DestroyFrameResources` destroys them, after Chapter 16's light buffers:

```cpp
// DestroyFrameResources (Chapter 19): each slot's instance and indirect buffers.
for (FrameDraws& frame : m_frameDraws)
{
    destroyBuffer(m_context, frame.instances);
    destroyBuffer(m_context, frame.indirect);
    frame.capacity = 0;
}
```

### Growing it

How many instances a frame has depends on the scene and the camera, so the
buffer must grow. **Replacing a per-frame buffer is safe at exactly one point:
after that slot's fence wait**, in `Record` — the frame that last used this
slot has finished, so nothing on the GPU reads its buffer, and only this slot's
descriptor set points at it. The same reasoning lets the descriptor be
rewritten right there: Chapter 08 section 6's rule forbids updating a set the
GPU might be reading, and this one it cannot be. One more condition, which is
why `PrepareDraws` must come first in `Record`: **nothing recorded yet in this
frame may have bound the set**, since updating a bound set invalidates the
command buffer that bound it.

The indirect buffer of section 6 lives beside it, sized from the same count —
there are never more commands than instances — so it grows here too:

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 19).
bool SceneRenderer::EnsureFrameCapacity(uint32_t frameIndex, uint32_t instances)
{
    FrameDraws& frame = m_frameDraws[frameIndex];
    if (instances <= frame.capacity) { return true; }

    // This slot's fence was waited, so the GPU no longer reads its buffers: replace them.
    uint32_t capacity = std::max(frame.capacity * 2, 1024u);
    while (capacity < instances) { capacity *= 2; }
    destroyBuffer(m_context, frame.instances);
    destroyBuffer(m_context, frame.indirect);
    frame.capacity = 0;

    frame.instances = createBuffer(m_context, capacity * sizeof(shared::InstanceData),
                                   VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, true);
    frame.indirect  = createBuffer(m_context, capacity * sizeof(VkDrawIndexedIndirectCommand),
                                   VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT, true);
    if (frame.instances.buffer == VK_NULL_HANDLE || frame.indirect.buffer == VK_NULL_HANDLE)
    {
        Log::error(std::format("Could not make room for {} instances.", instances).c_str());
        return false;
    }
    frame.capacity = capacity;

    // Only this slot's set points at the buffer, and nothing has bound it yet this frame.
    const VkDescriptorBufferInfo instanceInfo{
        .buffer = frame.instances.buffer,
        .offset = 0,
        .range  = VK_WHOLE_SIZE,
    };
    const VkWriteDescriptorSet write{
        .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
        .dstSet          = m_frameSets[frameIndex],
        .dstBinding      = 2,
        .descriptorCount = 1,
        .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
        .pBufferInfo     = &instanceInfo,
    };
    vkUpdateDescriptorSets(m_context.device, 1, &write, 0, nullptr);
    return true;
}
```

`VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT` is the usage section 6's draws require of
any buffer they read commands from; without it they are a validation error.

### The vertex shader

`Mesh.vert.glsl` reads its matrices from the instance buffer instead of the push
constant. The buffer is `readonly`: a vertex shader may write a storage buffer
only with the `vertexPipelineStoresAndAtomics` feature, which nothing here
enables or needs, and validation rejects a writable one.

```glsl
// Shaders/Scene/Mesh.vert.glsl - Chapter 19: the matrices per instance, not per draw.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"

layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUv;
layout(location = 3) in vec4 inTangent;

layout(location = 0) out vec3 worldPosition;
layout(location = 1) out vec3 worldNormal;
layout(location = 2) out vec2 uv;
layout(location = 3) out vec4 worldTangent;

// Set 0 binding 2: every instance drawn this frame, in PrepareDraws' order.
layout(std430, set = 0, binding = 2) readonly buffer InstanceBuffer { InstanceData instances[]; };

void main()
{
    // gl_InstanceIndex starts at the draw's firstInstance: it indexes the whole buffer directly.
    InstanceData instance = instances[gl_InstanceIndex];

    vec4 world    = instance.model * vec4(inPosition, 1.0);
    worldPosition = world.xyz;
    worldNormal   = instance.normalMatrix * inNormal;
    uv            = inUv;

    // Chapter 15's tangent, unchanged but for where the matrix comes from.
    mat3  linear = mat3(instance.model);
    float mirror = determinant(linear) < 0.0 ? -1.0 : 1.0;
    worldTangent = vec4(linear * inTangent.xyz, inTangent.w * mirror);

    gl_Position = frame.viewProjection * world;
}
```

Nothing reads `DrawData` any more, so `m_meshLayout` loses its push-constant
range. In `CreatePipelines`, Chapter 11's `drawRange` goes, and Chapter 15's
layout becomes:

```cpp
    // CreatePipelines (Chapter 19): sets 0 and 1, and no push constants - the matrices are
    // per instance now.
    const VkDescriptorSetLayout setLayouts[] = { m_frameSetLayout, m_materialSetLayout };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType          = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount = 2,
        .pSetLayouts    = setLayouts,
    };
```

`DrawData` stays in `SharedShaderTypes.h` — removing a struct is not
appending, and nothing is harmed by it — but no shader declares it.

---

## 4. One vertex buffer for every mesh

Chapter 11 gave every mesh its own vertex and index buffer. That is the
natural first design, and it is what stops section 6's best tool from working:
**a single multi-draw call draws every command with the same bound buffers.**
Commands for two different meshes need two different vertex buffers, so they
need two calls. With a buffer per mesh, a forest of two tree kinds made of four
meshes takes at least four calls however clever the rest is.

The fix is to put every mesh into **one** vertex buffer and **one** index
buffer, each mesh at its own offset, and to say the offsets in the draw instead
of in the binding. Indexed draws already have both slots:

- `firstIndex` — where in the index buffer this draw's indices start;
- `vertexOffset` — a number added to every index before it fetches a vertex.

So a mesh's indices are stored exactly as `MeshData` has them, counting from 0,
and the draw adds the mesh's place in the shared vertex buffer. Nothing is
rewritten during upload.

> **Jump:** a mesh stops being a pair of buffers and becomes a **range** inside
> buffers that belong to the renderer. Keep in mind what that moves: every
> draw now carries the mesh's offsets, the buffers are bound once for the whole
> pass, and adding a mesh can mean *moving* every mesh before it into a bigger
> buffer. In exchange, what used to be a mesh switch is free, and the GPU can
> draw any mix of meshes from one command list — which is exactly what the
> GPU-driven chapters need.

The two buffers are device-local and grow by doubling. Growing copies the
old contents into the new buffers on the GPU — they are device-local, so the
CPU cannot read them back — and that copy needs two barriers:

- **before it**: the earlier uploads wrote the old buffers with copies, and this
  copy *reads* them. Each upload ended with a barrier that made its writes
  visible to vertex input, not to transfer reads — `COPY`/`TRANSFER_WRITE` to
  `COPY`/`TRANSFER_READ`. "Everything before the barrier" means everything
  submitted earlier to the same queue, in any command buffer (Chapter 04
  section 5), which is why one barrier here covers every upload ever made.
- **after it**: the copy wrote the new buffers, and vertex input reads them —
  Chapter 11's upload barrier, `COPY`/`TRANSFER_WRITE` to
  `VERTEX_ATTRIBUTE_INPUT | INDEX_INPUT` / `VERTEX_ATTRIBUTE_READ | INDEX_READ`.

Both are memory barriers — no image, no layout — so one small helper writes
them:

```cpp
// SceneRenderer.cpp - file scope, above the namespace block (Chapter 19). The writes of every copy
// recorded before it, visible to `dstStage`'s `dstAccess`.
static void afterCopies(VkCommandBuffer commandBuffer, VkPipelineStageFlags2 dstStage, VkAccessFlags2 dstAccess)
{
    const VkMemoryBarrier2 barrier{
        .sType         = VK_STRUCTURE_TYPE_MEMORY_BARRIER_2,
        .srcStageMask  = VK_PIPELINE_STAGE_2_COPY_BIT,
        .srcAccessMask = VK_ACCESS_2_TRANSFER_WRITE_BIT,
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

// File scope, above the namespace block. A shared geometry buffer: device-local, written by
// uploads, and read by the copy when it grows.
static pf::vulkan_graphics::AllocatedBuffer createGeometryBuffer(pf::vulkan_graphics::VulkanContext& context,
                                                                 VkDeviceSize size, VkBufferUsageFlags usage)
{
    return pf::vulkan_graphics::createBuffer(context, size,
                                             usage | VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                                             false);
}
```

Growing has one more hazard: a frame in flight may be drawing from the old
buffers right now. Growth is rare — a scene's meshes are added in the demo's
`Setup`, which runs after a `vkDeviceWaitIdle` — so the function simply waits
for the device itself, which makes it safe wherever it is called.

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 19).
bool SceneRenderer::GrowGeometry(uint32_t vertexCount, uint32_t indexCount)
{
    if (vertexCount <= m_vertexCapacity && indexCount <= m_indexCapacity) { return true; }

    // A frame in flight may be drawing from the old buffers: they cannot be replaced under it.
    vkDeviceWaitIdle(m_context.device);

    const uint32_t vertexCapacity = std::max({ vertexCount, m_vertexCapacity * 2, 65536u });
    const uint32_t indexCapacity  = std::max({ indexCount, m_indexCapacity * 2, 196608u });
    AllocatedBuffer vertices = createGeometryBuffer(m_context, vertexCapacity * sizeof(scene::Vertex),
                                                    VK_BUFFER_USAGE_VERTEX_BUFFER_BIT);
    AllocatedBuffer indices  = createGeometryBuffer(m_context, indexCapacity * sizeof(uint32_t),
                                                    VK_BUFFER_USAGE_INDEX_BUFFER_BIT);
    if (vertices.buffer == VK_NULL_HANDLE || indices.buffer == VK_NULL_HANDLE)
    {
        destroyBuffer(m_context, vertices);
        destroyBuffer(m_context, indices);
        Log::error("Could not grow the shared geometry buffers.");
        return false;
    }

    if (m_vertexCount > 0)   // what was uploaded already moves into the new buffers
    {
        immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
            afterCopies(commandBuffer, VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);
            const VkBufferCopy vertexCopy{ .size = m_vertexCount * sizeof(scene::Vertex) };
            const VkBufferCopy indexCopy{ .size = m_indexCount * sizeof(uint32_t) };
            vkCmdCopyBuffer(commandBuffer, m_vertices.buffer, vertices.buffer, 1, &vertexCopy);
            vkCmdCopyBuffer(commandBuffer, m_indices.buffer, indices.buffer, 1, &indexCopy);
            afterCopies(commandBuffer, VK_PIPELINE_STAGE_2_VERTEX_ATTRIBUTE_INPUT_BIT | VK_PIPELINE_STAGE_2_INDEX_INPUT_BIT,
                        VK_ACCESS_2_VERTEX_ATTRIBUTE_READ_BIT | VK_ACCESS_2_INDEX_READ_BIT);
        });
    }
    destroyBuffer(m_context, m_vertices);
    destroyBuffer(m_context, m_indices);
    m_vertices       = vertices;
    m_indices        = indices;
    m_vertexCapacity = vertexCapacity;
    m_indexCapacity  = indexCapacity;
    return true;
}
```

**This is `AddMesh`**, rewritten. It uploads through one staging buffer, as
Chapter 11's `uploadMesh` did, but into the shared buffers' tails at the
current counts, and records the mesh's range. `uploadMesh` and `GpuMesh` stay
in `GpuMesh.h` for anything else that wants a mesh of its own; `SceneRenderer`
no longer uses them.

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 19). Replaces Chapter 11's
// AddMesh. Returns the mesh's index, which DrawItem::mesh refers to.
uint32_t SceneRenderer::AddMesh(const scene::MeshData& mesh)
{
    const uint32_t vertexCount = static_cast<uint32_t>(mesh.vertices.size());
    const uint32_t indexCount  = static_cast<uint32_t>(mesh.indices.size());
    MeshRange range{
        .vertexOffset = static_cast<int32_t>(m_vertexCount),
        .firstIndex   = m_indexCount,
        .submeshes    = mesh.submeshes,
        .doubleSided  = mesh.doubleSided,
    };

    if (vertexCount > 0 && indexCount > 0 && GrowGeometry(m_vertexCount + vertexCount, m_indexCount + indexCount))
    {
        const VkDeviceSize vertexBytes = vertexCount * sizeof(scene::Vertex);
        const VkDeviceSize indexBytes  = indexCount * sizeof(uint32_t);
        AllocatedBuffer staging = createBuffer(m_context, vertexBytes + indexBytes,
                                               VK_BUFFER_USAGE_TRANSFER_SRC_BIT, true);
        auto* bytes = static_cast<std::byte*>(staging.mapped);
        std::memcpy(bytes, mesh.vertices.data(), static_cast<size_t>(vertexBytes));
        std::memcpy(bytes + vertexBytes, mesh.indices.data(), static_cast<size_t>(indexBytes));
        vmaFlushAllocation(m_context.allocator, staging.allocation, 0, VK_WHOLE_SIZE);

        immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
            const VkBufferCopy vertexCopy{
                .srcOffset = 0,
                .dstOffset = m_vertexCount * sizeof(scene::Vertex),
                .size      = vertexBytes,
            };
            const VkBufferCopy indexCopy{
                .srcOffset = vertexBytes,
                .dstOffset = m_indexCount * sizeof(uint32_t),
                .size      = indexBytes,
            };
            vkCmdCopyBuffer(commandBuffer, staging.buffer, m_vertices.buffer, 1, &vertexCopy);
            vkCmdCopyBuffer(commandBuffer, staging.buffer, m_indices.buffer, 1, &indexCopy);
            afterCopies(commandBuffer, VK_PIPELINE_STAGE_2_VERTEX_ATTRIBUTE_INPUT_BIT | VK_PIPELINE_STAGE_2_INDEX_INPUT_BIT,
                        VK_ACCESS_2_VERTEX_ATTRIBUTE_READ_BIT | VK_ACCESS_2_INDEX_READ_BIT);
        });
        destroyBuffer(m_context, staging);
        m_vertexCount += vertexCount;
        m_indexCount  += indexCount;
    }
    else
    {
        range.submeshes.clear();   // nothing uploaded: nothing to draw
    }

    m_meshRanges.push_back(std::move(range));
    return static_cast<uint32_t>(m_meshRanges.size() - 1);
}
```

A mesh that failed to upload keeps its index, with no submeshes, so that
`DrawItem` indices still mean the same thing on both sides. `PrepareDraws`
leaves out items whose submesh it does not have.

`Shutdown` releases them in place of Chapter 11's loop over `m_meshes`, and
`MeshCount()` counts ranges:

```cpp
    // Shutdown (Chapter 19), replacing Chapter 11's loop over m_meshes and its clear().
    destroyBuffer(m_context, m_vertices);
    destroyBuffer(m_context, m_indices);
    m_meshRanges.clear();
    m_vertexCount = m_vertexCapacity = m_indexCount = m_indexCapacity = 0;
```

```cpp
// SceneRenderer.h (Chapter 19): replaces Chapter 11's MeshCount.
std::size_t MeshCount() const     { return m_meshRanges.size(); }
```

---

## 5. Batching the draw list

**This is `PrepareDraws`, first half.** The input is any list of `DrawItem`s,
in any order. The output is three things: the instance buffer's contents, one
indirect command per group of items that can be one instanced draw, and the
runs that can be one multi-draw.

**Sorting does the finding.** Two items can share an instanced draw when they
have the same mesh, submesh, and material: same indices, same textures, only
the matrix differs. Sort the items so that equal ones are adjacent, and every
group is a contiguous run of the sorted list — so its instances are contiguous
in the instance buffer, and one `firstInstance` plus one `instanceCount`
describe it. The sort key orders the coarser things first, so that runs of
commands that can share a *call* are adjacent too:

```text
 (cutout?, doubleSided?, material, mesh, submesh)
  └─ pipeline ─┘ └ cull ┘ └ set 1 ┘ └ the command ┘
```

Items with the same material are adjacent, so section 6 binds each material
once; items with the same mesh and submesh within a material are adjacent, so
they become one command.

The list is sorted through a vector of indices, not by moving the items: a
`DrawItem` is a 64-byte matrix plus three numbers, and moving thousands of them
costs more than sorting their indices. `std::sort` is fine here — the order
within one group does not matter, because every instance in it draws the same
way.

```cpp
// SceneRenderer.cpp - file scope, above the namespace block (Chapter 19). Chapter 11's normal
// matrix, in the std430 shape InstanceData stores it in.
static glm::mat3x4 normalMatrix(const glm::mat4& model)
{
    return glm::mat3x4(glm::transpose(glm::inverse(glm::mat3(model))));
}
```

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 19).
void SceneRenderer::PrepareDraws(uint32_t frameIndex, std::span<const scene::DrawItem> sceneDraws,
                                 std::span<const scene::DrawItem> shadowCasters)
{
    FrameDraws& frame = m_frameDraws[frameIndex];
    frame.commands.clear();
    for (std::vector<DrawRun>& runs : frame.runs) { runs.clear(); }
    m_statistics[frameIndex] = {};

    const uint32_t total = static_cast<uint32_t>(sceneDraws.size() + shadowCasters.size());
    if (!EnsureFrameCapacity(frameIndex, total)) { return; }   // draws nothing this frame, and says why

    auto* instances = static_cast<shared::InstanceData*>(frame.instances.mapped);
    uint32_t instance = 0;   // the next free slot in the instance buffer, across both lists

    const std::span<const scene::DrawItem> lists[DRAW_LIST_COUNT] = { sceneDraws, shadowCasters };
    for (uint32_t list = 0; list < DRAW_LIST_COUNT; ++list)
    {
        const std::span<const scene::DrawItem> draws = lists[list];
        std::vector<DrawRun>& runs = frame.runs[list];

        // The items there is something to draw for - Chapter 15's RecordDraws skipped a mesh that
        // failed to upload and a material without a set 1 - then sorted so that items which can
        // share a command, then a run, are adjacent.
        m_order.clear();
        for (uint32_t i = 0; i < static_cast<uint32_t>(draws.size()); ++i)
        {
            const scene::DrawItem& item = draws[i];
            if (item.mesh < m_meshRanges.size() && item.submesh < m_meshRanges[item.mesh].submeshes.size() &&
                item.material < m_gpuMaterials.size() && m_gpuMaterials[item.material].set != VK_NULL_HANDLE)
            {
                m_order.push_back(i);
            }
        }
        auto key = [&](uint32_t i) {
            const scene::DrawItem& item = draws[i];
            return std::tuple(m_gpuMaterials[item.material].cutout, m_meshRanges[item.mesh].doubleSided,
                              item.material, item.mesh, item.submesh);
        };
        std::sort(m_order.begin(), m_order.end(), [&](uint32_t a, uint32_t b) { return key(a) < key(b); });

        // >>> The second half, below, walks m_order and writes instances, commands, and runs. <<<
    }

    // >>> And the end of the function writes the commands into the indirect buffer. <<<
}
```

**This is `PrepareDraws`, second half** — the walk over the sorted indices,
inside the `list` loop where the first half left the marker. Each item writes
its matrices to the next instance slot. An item equal to the previous one adds
an instance to the previous command; otherwise it starts a new command whose
`firstInstance` is its own slot. A new command with the previous one's material
and cull mode joins the previous run; otherwise it starts a run.

```cpp
        // PrepareDraws, inside the list loop (Chapter 19): instances, commands, runs.
        const scene::DrawItem* previous = nullptr;
        for (const uint32_t index : m_order)
        {
            const scene::DrawItem& item = draws[index];
            const MeshRange& mesh = m_meshRanges[item.mesh];

            instances[instance] = shared::InstanceData{ .model = item.world, .normalMatrix = normalMatrix(item.world) };

            const bool sameCommand = previous != nullptr && previous->mesh == item.mesh &&
                                     previous->submesh == item.submesh && previous->material == item.material;
            if (sameCommand)
            {
                frame.commands.back().instanceCount += 1;   // one more copy of the same thing
            }
            else
            {
                const scene::Submesh& submesh = mesh.submeshes[item.submesh];
                frame.commands.push_back(VkDrawIndexedIndirectCommand{
                    .indexCount    = submesh.indexCount,
                    .instanceCount = 1,
                    .firstIndex    = mesh.firstIndex + submesh.firstIndex,
                    .vertexOffset  = mesh.vertexOffset,
                    .firstInstance = instance,
                });

                const bool sameRun = previous != nullptr && previous->material == item.material &&
                                     m_meshRanges[previous->mesh].doubleSided == mesh.doubleSided;
                if (sameRun)
                {
                    runs.back().commandCount += 1;
                }
                else
                {
                    runs.push_back(DrawRun{
                        .firstCommand = static_cast<uint32_t>(frame.commands.size() - 1),
                        .commandCount = 1,
                        .material     = item.material,
                        .doubleSided  = mesh.doubleSided,
                    });
                }
            }
            previous = &item;
            ++instance;
        }
```

A run never spans the two lists, because `previous` starts over for each list;
the shadow casters' commands follow the scene's in the same `commands` vector,
and their runs point into it.

Notice what the sort did *not* need to know: nothing about USD, prototypes, or
instancers. Any two draws of the same mesh with the same material — a
hand-placed pair of chairs, a `PointInstancer`'s four thousand trees — become
one command. Sections 9 and 10 only have to make sure that instances in the
file share a mesh index in the scene.

---

## 6. Indirect draws

### The command, in a buffer

`vkCmdDrawIndexed(commandBuffer, indexCount, instanceCount, firstIndex,
vertexOffset, firstInstance)` takes its five numbers from the command stream,
which the CPU writes. `vkCmdDrawIndexedIndirect` takes the same five numbers
from **a buffer**, which anything can write — the CPU now, a compute shader in
Chapter 21. Vulkan defines the layout, and C++ has it as a struct:

```cpp
// vulkan_core.h - Vulkan's own, shown for reference. 20 bytes, tightly packed.
typedef struct VkDrawIndexedIndirectCommand {
    uint32_t    indexCount;
    uint32_t    instanceCount;
    uint32_t    firstIndex;
    int32_t     vertexOffset;
    uint32_t    firstInstance;
} VkDrawIndexedIndirectCommand;

// The non-indexed draw's equivalent, read by vkCmdDrawIndirect. 16 bytes. Chapter 21's
// particles use it: no index buffer, vertices generated from gl_VertexIndex.
typedef struct VkDrawIndirectCommand {
    uint32_t    vertexCount;
    uint32_t    instanceCount;
    uint32_t    firstVertex;
    uint32_t    firstInstance;
} VkDrawIndirectCommand;
```

**This is the end of `PrepareDraws`**: the commands go into this frame slot's
indirect buffer, and the statistics are filled in for the panel. The buffer is
host-visible and per frame in flight, exactly like the instance buffer — the
CPU writes it every frame, and no barrier is needed for the same reason: host
writes made before `vkQueueSubmit2` are visible to the submitted work.

```cpp
    // The end of PrepareDraws (Chapter 19): the commands, into this frame slot's indirect buffer.
    std::memcpy(frame.indirect.mapped, frame.commands.data(),
                frame.commands.size() * sizeof(VkDrawIndexedIndirectCommand));
    vmaFlushAllocation(m_context.allocator, frame.instances.allocation, 0, VK_WHOLE_SIZE);
    vmaFlushAllocation(m_context.allocator, frame.indirect.allocation, 0, VK_WHOLE_SIZE);

    // What the Scene list became, for the panel.
    DrawStatistics& statistics = m_statistics[frameIndex];
    const std::vector<DrawRun>& sceneRuns = frame.runs[static_cast<uint32_t>(DrawList::Scene)];
    statistics.items    = static_cast<uint32_t>(sceneDraws.size());
    statistics.runs     = static_cast<uint32_t>(sceneRuns.size());
    statistics.commands = 0;
    for (const DrawRun& run : sceneRuns)
    {
        statistics.commands += run.commandCount;
        for (uint32_t c = run.firstCommand; c < run.firstCommand + run.commandCount; ++c)
        {
            statistics.largestInstance = std::max(statistics.largestInstance, frame.commands[c].instanceCount);
        }
    }
    statistics.drawCalls = m_drawMode == DrawMode::OnePerItem ? statistics.items
                         : m_drawMode == DrawMode::MultiDraw  ? statistics.runs
                                                              : statistics.commands;
```

### Two device features

Indirect drawing itself is core Vulkan 1.0 and needs nothing. Two refinements
of it do, and this chapter uses both:

- **`multiDrawIndirect`** (Vulkan 1.0, `VkPhysicalDeviceFeatures`): a
  `drawCount` greater than 1 — one call that walks several consecutive commands
  in the buffer. Without it, `drawCount` must be 0 or 1.
- **`drawIndirectFirstInstance`** (Vulkan 1.0): a nonzero `firstInstance` *in an
  indirect command*. Without it, every command's `firstInstance` must be 0 —
  which would defeat section 2's whole scheme. **The core validation layer
  cannot catch this one:** the value is in a buffer the layer does not read when
  you record the draw. Only GPU-assisted validation, which instruments the
  draw (the layer adds checking code to your shaders and reads its results
  back; it is slower, so it is off unless you ask for it), reports it
  (`VUID-VkDrawIndexedIndirectCommand-firstInstance-00554`). A
  missing feature here would "work" on a GPU that ignores the rule and draw
  wrong instances on one that does not.

Both are universal on desktop GPUs, so they are requirements, checked and
enabled the way Chapter 15's `samplerAnisotropy` was. Chapter 02's
`hasRequiredFeatures` check grows:

```cpp
// Chapter 02 section 5, hasRequiredFeatures - the return statement, grown again (Chapter 19):
return features13.dynamicRendering == VK_TRUE
    && features13.synchronization2 == VK_TRUE
    && features.features.samplerAnisotropy == VK_TRUE
    && features.features.multiDrawIndirect == VK_TRUE
    && features.features.drawIndirectFirstInstance == VK_TRUE;
```

and its `rejectionReason` message says so:

```cpp
    if (!hasRequiredFeatures(device))                                 { return "no dynamicRendering, synchronization2, samplerAnisotropy, or the indirect-draw features"; }
```

`CreateDevice` enables them. Both are Vulkan 1.0 features, so they join Chapter
15's `samplerAnisotropy` in `enabledFeatures.features` — designated initializers
in `VkPhysicalDeviceFeatures`' declaration order, which puts them first:

```cpp
// Chapter 02 section 6, CreateDevice (Chapter 19): two more 1.0 features beside samplerAnisotropy.
VkPhysicalDeviceFeatures2 enabledFeatures{
    .sType    = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
    .pNext    = &enable13,
    .features = {
        .multiDrawIndirect         = VK_TRUE,
        .drawIndirectFirstInstance = VK_TRUE,
        .samplerAnisotropy         = VK_TRUE,
    },
};
```

The chain itself does not change: `enable13` keeps everything Chapters 02 and 15
put in it.

### Recording: four ways to issue the same commands

**This is `RecordBatches`.** It binds the shared geometry once — every command
carries its own offsets into it — and then, per run, lets the caller bind the
run's pipeline and sets, and issues the run's commands. *How* it issues them is
the draw mode, and the four modes are this chapter in miniature, from Chapter
11's way to the GPU-driven one:

- **One per item** — every instance its own `vkCmdDrawIndexed`, with
  `instanceCount` 1 and its own `firstInstance`. The same instance buffer, so the
  same image; as many calls as Chapter 11 made.
- **Instanced** — one `vkCmdDrawIndexed` per command, `instanceCount` copies.
  The numbers still come from the CPU's command stream.
- **Indirect** — the same calls, but `vkCmdDrawIndexedIndirect` with `drawCount`
  1: each call's five numbers are read by the GPU from the buffer.
- **Multi-draw** — one `vkCmdDrawIndexedIndirect` per run, `drawCount` = the
  run's length: the GPU walks that many consecutive commands, `stride` bytes
  apart, all sharing what was bound for the run. This is where section 4's
  shared buffers pay: a run is "everything with this material", whatever meshes
  it contains.

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 19).
void SceneRenderer::RecordBatches(VkCommandBuffer commandBuffer, uint32_t frameIndex, DrawList list,
                                  const std::function<void(VkCommandBuffer, const DrawRun&)>& bindRun) const
{
    const FrameDraws& frame = m_frameDraws[frameIndex];
    const std::vector<DrawRun>& runs = frame.runs[static_cast<uint32_t>(list)];
    if (runs.empty()) { return; }

    // Every mesh is in these two buffers (section 4): bound once, for every command.
    const VkDeviceSize zero = 0;
    vkCmdBindVertexBuffers(commandBuffer, 0, 1, &m_vertices.buffer, &zero);
    vkCmdBindIndexBuffer(commandBuffer, m_indices.buffer, 0, VK_INDEX_TYPE_UINT32);

    constexpr uint32_t stride = sizeof(VkDrawIndexedIndirectCommand);
    for (const DrawRun& run : runs)
    {
        bindRun(commandBuffer, run);
        const uint32_t end = run.firstCommand + run.commandCount;
        switch (m_drawMode)
        {
        case DrawMode::OnePerItem:
            for (uint32_t c = run.firstCommand; c < end; ++c)
            {
                const VkDrawIndexedIndirectCommand& command = frame.commands[c];
                for (uint32_t i = 0; i < command.instanceCount; ++i)
                {
                    vkCmdDrawIndexed(commandBuffer, command.indexCount, 1, command.firstIndex,
                                     command.vertexOffset, command.firstInstance + i);
                }
            }
            break;
        case DrawMode::Instanced:
            for (uint32_t c = run.firstCommand; c < end; ++c)
            {
                const VkDrawIndexedIndirectCommand& command = frame.commands[c];
                vkCmdDrawIndexed(commandBuffer, command.indexCount, command.instanceCount, command.firstIndex,
                                 command.vertexOffset, command.firstInstance);
            }
            break;
        case DrawMode::Indirect:
            for (uint32_t c = run.firstCommand; c < end; ++c)
            {
                vkCmdDrawIndexedIndirect(commandBuffer, frame.indirect.buffer, c * stride, 1, stride);
            }
            break;
        case DrawMode::MultiDraw:
            vkCmdDrawIndexedIndirect(commandBuffer, frame.indirect.buffer, run.firstCommand * stride,
                                     run.commandCount, stride);
            break;
        }
    }
}
```

Every offset handed to an indirect draw must be a multiple of 4, and the stride
at least the command's size and a multiple of 4. `VkDrawIndexedIndirectCommand`
is 20 bytes of 4-byte fields, so commands packed back to back satisfy both.

**This is `RecordDraws`**, rewritten around `RecordBatches`. What used to be
per draw is now per run: the pipeline (opaque or cutout, Chapter 15), the cull
mode (Chapter 11's dynamic state), and set 1. Set 0 — which now includes the
instance buffer — and the front face are bound once.

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 19). Replaces Chapter 11's.
void SceneRenderer::RecordDraws(VkCommandBuffer commandBuffer, uint32_t frameIndex) const
{
    BindFrameSet(commandBuffer, m_meshLayout, frameIndex);
    vkCmdSetFrontFace(commandBuffer, m_frontFaceFlipped ? VK_FRONT_FACE_CLOCKWISE
                                                        : VK_FRONT_FACE_COUNTER_CLOCKWISE);
    const uint32_t shading = static_cast<uint32_t>(m_shading);

    RecordBatches(commandBuffer, frameIndex, DrawList::Scene, [&](VkCommandBuffer cb, const DrawRun& run) {
        const GpuMaterial& material = m_gpuMaterials[run.material];
        vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, m_meshPipelines[shading][material.cutout ? 1 : 0]);
        vkCmdSetCullMode(cb, run.doubleSided ? VK_CULL_MODE_NONE : VK_CULL_MODE_BACK_BIT);
        vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, m_meshLayout, 1, 1, &material.set, 0, nullptr);
    });
}
```

Binding the pipeline every run, even when two runs share one, is deliberate
simplicity: a run is a material, and a scene has tens of them, not thousands.

**And `IndirectCommands`**, which the panel uses to show what the GPU reads —
the Scene list's commands come first in the buffer:

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 19).
std::span<const VkDrawIndexedIndirectCommand> SceneRenderer::IndirectCommands(uint32_t frameIndex) const
{
    const FrameDraws& frame = m_frameDraws[frameIndex];
    if (frame.indirect.mapped == nullptr) { return {}; }
    return { static_cast<const VkDrawIndexedIndirectCommand*>(frame.indirect.mapped),
             m_statistics[frameIndex].commands };
}
```

Reading back from this memory is slow — it is allocated for the CPU to write
sequentially, which on many GPUs means uncached, write-combined memory — so the
panel reads a handful of commands, not all of them. And it reads them while the
GPU may be reading the same bytes for an in-flight frame, which is harmless:
two readers never race.

### The panel

The draw mode is a setting worth switching live, and the statistics are worth
seeing, so the viewer gets a small "Instancing" window now; section 8's
checkpoint is where it first has something to show. `Update` runs before the
fence wait and has no `frameIndex` of its own, so the demo remembers the slot it
last recorded, and the panel shows that frame's statistics and its first
commands, read back from the indirect buffer:

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp - file scope, above the namespace block (Chapter 19). The
// "Instancing" panel.
static void drawInstancingPanel(pf::vulkan_graphics::SceneRenderer& renderer, uint32_t frameIndex)
{
    namespace vulkan_graphics = pf::vulkan_graphics;
    ImGui::SetNextWindowPos(ImVec2(360.0f, 200.0f), ImGuiCond_FirstUseEver);   // under "Shadows"
    ImGui::SetNextWindowCollapsed(true, ImGuiCond_FirstUseEver);              // a title bar until you open it
    if (ImGui::Begin("Instancing", nullptr, ImGuiWindowFlags_AlwaysAutoResize))
    {
        int mode = static_cast<int>(renderer.GetDrawMode());
        if (ImGui::Combo("Draw mode", &mode,
                         "One per item\0Instanced\0Indirect\0Multi-draw indirect\0"))
        {
            renderer.SetDrawMode(static_cast<vulkan_graphics::DrawMode>(mode));
        }

        const vulkan_graphics::DrawStatistics& statistics = renderer.Statistics(frameIndex);
        ImGui::Text("Draw items:      %u", statistics.items);
        ImGui::Text("Commands:        %u", statistics.commands);
        ImGui::Text("Runs:            %u", statistics.runs);
        ImGui::Text("Draw calls:      %u", statistics.drawCalls);
        ImGui::Text("Largest batch:   %u instances", statistics.largestInstance);

        // Read back from the indirect buffer itself: what the GPU will read.
        const auto commands = renderer.IndirectCommands(frameIndex);
        if (ImGui::BeginTable("commands", 5, ImGuiTableFlags_Borders))
        {
            for (const char* heading : { "indexCount", "instanceCount", "firstIndex", "vertexOffset", "firstInstance" })
            {
                ImGui::TableSetupColumn(heading);
            }
            ImGui::TableHeadersRow();
            for (size_t c = 0; c < std::min<size_t>(commands.size(), 8); ++c)
            {
                ImGui::TableNextRow();
                ImGui::TableNextColumn(); ImGui::Text("%u", commands[c].indexCount);
                ImGui::TableNextColumn(); ImGui::Text("%u", commands[c].instanceCount);
                ImGui::TableNextColumn(); ImGui::Text("%u", commands[c].firstIndex);
                ImGui::TableNextColumn(); ImGui::Text("%d", commands[c].vertexOffset);
                ImGui::TableNextColumn(); ImGui::Text("%u", commands[c].firstInstance);
            }
            ImGui::EndTable();
        }
    }
    ImGui::End();
}
```

Like Chapter 17's "Shadows", the window opens as a title bar; click the title to open it.

```cpp
// Demos/UsdViewer/UsdViewerDemo.h, private (Chapter 19).
uint32_t m_lastFrameIndex = 0;   // the frame slot Record last prepared draws for
```

```cpp
// UsdViewerDemo::Update, after the scene panels (Chapter 19).
drawInstancingPanel(m_sceneRenderer, m_lastFrameIndex);
```

`Record` sets `m_lastFrameIndex` beside its `PrepareDraws` call, which section
8 adds to the demo. The statistics are the frame that slot last prepared: a
frame or two old, which for a panel is now.

---

## 7. When the GPU writes the commands

Everything above, the CPU writes. The point of indirect draws is that it does
not have to. In Chapter 21 a compute shader simulates particles and writes the
draw's `instanceCount` — how many are alive — without the CPU ever knowing the
number; in Chapter 26 a compute shader culls grass blades and writes both the
instances and the counts. The draw call is recorded once, with an offset into a
buffer whose contents do not exist yet when it is recorded. That is what makes
it GPU-driven: the decision about *what* to draw moves to the GPU, and the CPU
records the same few calls every frame.

**`vkCmdDrawIndexedIndirectCount`** is the same idea one level up: a multi-draw
that reads *how many* commands to draw from a buffer too. A compute pass that
culls whole objects compacts the surviving commands to the front of the buffer
and writes how many there are; the draw reads that number, and the CPU records
one call with `maxDrawCount` as the upper bound. It needs Vulkan 1.2's
`drawIndirectCount` feature, which this tutorial does not enable: nothing here
culls whole objects on the GPU, and a count the CPU writes is one it already
knows. It is the next step when something does.

Two things change when a shader is the writer, and both are barriers:

- **The read happens in its own pipeline stage.** The GPU fetches indirect
  commands and counts in `VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT`, with
  `VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT` — before the vertex shader, before
  vertex input. A compute shader's writes must be made visible *there*, and to
  the vertex shader that reads the instances; Chapter 21 section 4 builds this
  barrier with the three questions. Getting the destination stage wrong —
  `VERTEX_SHADER` alone — is the classic bug: the instance data is ready but
  the command that says how many instances to draw is read too early, and the
  draw uses last frame's count.
- **The buffer goes device-local and stops being per frame.** A buffer the GPU
  writes and reads needs no CPU copy per frame in flight; it needs the barrier
  above and its return trip, from this frame's indirect read back to next
  frame's compute write. Chapter 21 builds exactly that.

The buffer usage then gains `VK_BUFFER_USAGE_STORAGE_BUFFER_BIT` beside
`INDIRECT_BUFFER_BIT`, since compute writes it as a storage buffer and the draw
reads it as an indirect one.

---

## 8. The shadow casters, batched too

Chapter 17 draws every shadow caster into every cascade — four times the scene
pass's draws, through a callback that loops over the casters one by one. With a
forest that is thirty thousand draws, and it is the same problem with the same
answer. `PrepareDraws` already batched the casters into their own runs (its
second list), into the same instance buffer, so the callback becomes a
`RecordBatches` call.

The caster vertex shader reads the instance buffer, like the mesh one:

```glsl
// Shaders/Shadows/ShadowDepth.vert.glsl - Chapter 19: the model matrix per instance.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SharedShaderTypes.h"

layout(location = 0) in  vec3 position;   // scene::Vertex, Chapter 11's vertex input
layout(location = 2) in  vec2 uv;
layout(location = 0) out vec2 outUv;      // read only by ShadowCutout.frag

layout(std140, set = 0, binding = 3) uniform ShadowBlock { ShadowData shadowData; };
layout(std430, set = 0, binding = 2) readonly buffer InstanceBuffer { InstanceData instances[]; };
layout(push_constant) uniform ShadowDrawBlock { ShadowDrawData draw; };

void main()
{
    gl_Position = shadowData.cascadeViewProjection[draw.cascade]
                * instances[gl_InstanceIndex].model * vec4(position, 1.0);
    outUv       = uv;
}
```

so the push constant shrinks to the cascade number — 16 bytes, padded. Chapter
17's struct and its assert are replaced where they stand:

```c
/* Shaders/Include/SharedShaderTypes.h - Chapter 19 replaces Chapter 17's ShadowDrawData: the
   model matrix moved to the instance buffer. GLSL: ShadowDrawBlock. */
struct ShadowDrawData
{
    uint cascade;                       /*  0  which cascadeViewProjection to draw with */
    uint padding0;
    uint padding1;
    uint padding2;
};

#ifdef __cplusplus
    static_assert(sizeof(ShadowDrawData) == 16, "ShadowDrawData layout drifted.");
#endif
```

The caster pipelines' push range is `sizeof(shared::ShadowDrawData)`, so it
follows on its own.

`RecordShadows` loses its `casters` parameter — `PrepareDraws` took them — and
its callback pushes the cascade per run, after binding the run's caster
pipeline, as Chapter 17's did per draw:

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 19). Replaces Chapter 17's.
void SceneRenderer::RecordShadows(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                                  const scene::Camera& camera, const glm::mat4& view, float aspect,
                                  std::optional<glm::vec3> sunDirection, const ShadowSettings& settings,
                                  const ShadowCasterCallback& extraCasters)
{
    // Called once per cascade, inside its rendering scope, with set 0 already bound.
    const ShadowCasterCallback drawCasters = [&](VkCommandBuffer cb, uint32_t cascade) {
        const shared::ShadowDrawData push{ .cascade = cascade, .padding0 = 0, .padding1 = 0, .padding2 = 0 };
        RecordBatches(cb, frameIndex, DrawList::ShadowCasters, [&](VkCommandBuffer runCb, const DrawRun& run) {
            const GpuMaterial&     material = m_gpuMaterials[run.material];
            const VkPipelineLayout layout   = m_shadows.CasterLayout(material.cutout);
            vkCmdBindPipeline(runCb, VK_PIPELINE_BIND_POINT_GRAPHICS, m_shadows.CasterPipeline(material.cutout));
            if (material.cutout)   // its fragment shader reads the material: set 1
            {
                vkCmdBindDescriptorSets(runCb, VK_PIPELINE_BIND_POINT_GRAPHICS, layout, 1, 1, &material.set, 0, nullptr);
            }
            vkCmdPushConstants(runCb, layout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
        });
    };
    m_shadows.Record(commandBuffer, frameIndex, m_frameSets[frameIndex], camera, view, aspect,
                     sunDirection, settings, drawCasters, extraCasters);
}
```

The caster pipelines bake `CULL_MODE_NONE` (Chapter 17 section 4), so the run's
cull mode is not set here. A caster run being "one material" is finer than the
shadow pass needs — every opaque material uses the same caster pipeline and no
set 1 — but sharing `PrepareDraws` with the scene list keeps one batching rule,
and the number of materials is small.

### The demos call it

Everything `SceneRenderer` needs is now in place, and the demos switch to it.
`UsdViewerDemo::Record` gathers both lists and hands them over before anything
binds set 0 — that is, before Chapter 17's shadow pass — and then remembers the
slot for section 6's panel:

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, Record (Chapter 19): Chapter 17's shadow lines, after
// WriteLights, become these. Both lists go to PrepareDraws; RecordShadows no longer takes one.
m_scene.CollectDraws(m_shadowCasters, nullptr);
m_sceneRenderer.PrepareDraws(frame.frameIndex, m_draws, m_shadowCasters);
m_sceneRenderer.RecordShadows(commandBuffer, frame.frameIndex, camera, frameData.view, aspect,
                              m_sceneRenderer.SunDirection(frame.frameIndex), m_shadowSettings);
m_lastFrameIndex = frame.frameIndex;   // the slot the panel's statistics come from
```

and inside the scene pass, `RecordDraws` takes no list:

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, between beginScenePass and endScenePass (Chapter 19).
m_sceneRenderer.RecordDraws(commandBuffer, frame.frameIndex);
```

`m_draws` is the camera-culled list Chapter 12's `CollectDraws` already fills
each frame. Chapters 11 and 12's demos have one list and no shadow pass, so
theirs is the same change with one argument:

```cpp
// Demos/Meshes/MeshesDemo.cpp and Demos/SceneGraph/SceneGraphDemo.cpp, Record (Chapter 19): after
// Chapter 16's WriteLights, before beginScenePass.
m_sceneRenderer.PrepareDraws(frame.frameIndex, m_draws);
```

```cpp
// ...and between beginScenePass and endScenePass, in place of Chapter 11's call.
m_sceneRenderer.RecordDraws(commandBuffer, frame.frameIndex);
```

---

## Checkpoint — the same image, fewer calls

Sections 3-8 changed *how* the scene is drawn and nothing about *what* is drawn,
so the test is that the picture stays put while the numbers move. Build, open
Chapter 17's `ShadowTest.usda` in the USD viewer with validation on, and click
the "Instancing" window's title to open it.

- [ ] The image is the one Chapter 17 drew, shadows included.
- [ ] The panel shows 106 draw items and 106 commands. Every pillar and box in
      that file is a mesh of its own, so no two items can share a command, and
      the largest batch is 1 instance. But the 106 commands fall into **4
      runs**, one per material, so in **Multi-draw indirect** the whole scene
      is **4 draw calls**.
- [ ] Switching through the four modes changes "Draw calls" — 106, 106, 106,
      4 — and not one pixel of the scene. The shadows stay in every mode: the
      casters go through the same batches (section 8).
- [ ] The command table shows the commands as the GPU reads them: each
      `firstInstance` one past the last, each `vertexOffset` where its mesh
      starts in the shared vertex buffer (section 4).
- [ ] Validation, synchronization validation included, is silent in every mode.

What is still missing is `instanceCount` above 1: nothing in this file says two
of its meshes are the same mesh. Sections 9 and 10 teach the importer to read
USD's two ways of saying so, and section 11 builds a forest that says it four
thousand times.

---

## 9. USD instancing, part one: `instanceable` prims

USD has two instancing mechanisms, and both have to end in the same place:
**several nodes whose meshes are the same mesh index**, so that section 5's
sort puts their draws together.

The first is **scene-graph instancing**. A prim marked `instanceable = true`
that references another prim says "my contents are exactly that prim's
contents, and I promise not to override anything inside" — so every such prim
referencing the same thing can share one copy. Blender writes it when you tick
*Instancing* on export: every collection instance becomes

```usda
def Xform "Rock_0" (
    instanceable = true
    prepend references = </root/prototypes/Rock>
)
{
    double3 xformOp:translate = (4, 0, 0)
    uniform token[] xformOpOrder = ["xformOp:translate"]
}
```

with the shared contents under a `class "prototypes"` prim. A **class** is a
template: it is in the file to be referenced, and it is never drawn by itself.

> **Jump:** Chapter 14's loader reads a USD file without *composing* it
> (Chapter 13): a reference is a note that says "my contents are over there",
> and nothing follows it. That was fine until now because nothing in the test
> files referenced anything. Here the importer follows one kind of reference
> itself — an **internal** one, to a prim in the same file, which is what
> Blender writes — and takes the referenced prim's children as the instance's
> children. Keep in mind what it does not do: merge the referenced prim's own
> attributes with the instance's (the instance's transform is used, the
> prototype root's ignored), follow references to other files, or handle
> variants, payloads, and inherits. That is what a composition engine is for,
> and TinyUSDZ's own (`CompositeAllArcs`) drops `PointInstancer`s at this pin,
> which section 10 needs.

Three changes to `UsdImport.cpp`, in the order `importPrim` meets them.

**Skip classes.** TinyUSDZ v0.9.4's `Prim::specifier()` reports `Invalid` for
every prim read from a `.usda` file, so the specifier is read from the schema
struct, which stores it correctly. A class with a type (`class Xform`) is an
`Xform`; Blender's typeless `class "prototypes"` is a `Model`:

```cpp
// UsdImport.cpp - file scope, above the namespace block (Chapter 19). Whether the prim is a
// `class` - a template, drawn only through what references it.
static bool isClassPrim(const tinyusdz::Prim& prim)
{
    if (const auto* xform = prim.as<tinyusdz::Xform>()) { return xform->spec == tinyusdz::Specifier::Class; }
    if (const auto* model = prim.as<tinyusdz::Model>()) { return model->spec == tinyusdz::Specifier::Class; }
    if (const auto* scope = prim.as<tinyusdz::Scope>()) { return scope->spec == tinyusdz::Specifier::Class; }
    return false;
}
```

```cpp
// importPrim, right after Chapter 14's inactive / Material / Shader / GeomSubset test (Chapter 19).
if (isClassPrim(prim)) { return; }   // and everything under it
```

**Share meshes.** Every instance of `Rock` reaches the same prototype prims —
`/root/prototypes/Rock/Body` — through a different instance node. A cache keyed
by the mesh prim's path turns the second and later visits into a reuse of the
first's mesh index instead of a second copy of the geometry. Chapter 14 fixes a
mirrored instance's winding by reversing its triangles, so mirroring is part of
the key: a mirrored and an unmirrored instance cannot share.

```cpp
// UsdImport.cpp - Chapter 15's ImportContext gains one more cache (Chapter 19):
std::map<std::pair<std::string, bool>, uint32_t> meshes = {};   // (mesh prim path, mirrored) -> scene mesh
```

```cpp
    // ImportUsdFile, where Chapter 14 builds the context (Chapter 19): the new member is named too.
    ImportContext context{
        .scene         = scene,
        .stage         = stage,
        .directory     = file.parent_path(),
        .metersPerUnit = metersPerUnit,
        .skipped       = {},
        .materials     = {},   // Chapter 15
        .textures      = {},   // Chapter 15
        .meshes        = {},   // Chapter 19
    };
```

In `importPrim`'s geometry dispatch, the cache is consulted first, and filled
after:

```cpp
    // importPrim, the start of Chapter 14's dispatch (Chapter 19): a mesh prim reached before -
    // through another instance of the same prototype - is shared, not rebuilt.
    const auto meshKey = std::make_pair(path, mirrored);
    if (const auto shared = context.meshes.find(meshKey); shared != context.meshes.end())
    {
        context.scene.SetMesh(node, shared->second);
    }
    else if (const auto* mesh = prim.as<tinyusdz::GeomMesh>())
```

```cpp
    // importPrim, right after the dispatch's last branch (Chapter 19): remember what was built.
    if (context.scene.GetNode(node).mesh != pf::scene::NO_COMPONENT)
    {
        context.meshes.try_emplace(meshKey, context.scene.GetNode(node).mesh);
    }
```

The first line replaces Chapter 14's `if (const auto* mesh = ...)` with an
`else if`; every other branch is unchanged. A shared mesh keeps the material
its first import resolved — the binding on the prototype's own prims, which is
where Blender writes it.

**Follow the reference.** An instanceable prim arrives from the loader with no
children; its contents are the referenced prim's:

```cpp
// UsdImport.cpp - file scope, above the namespace block (Chapter 19). The prim an instanceable
// prim's internal reference points at, or nullptr. External files are not followed.
static const tinyusdz::Prim* instancePrototype(const ImportContext& context, const tinyusdz::Prim& prim,
                                               const std::string& path)
{
    const tinyusdz::PrimMeta& metas = prim.metas();
    if (!metas.has_instanceable() || !metas.get_instanceable() || !metas.references) { return nullptr; }

    for (const auto& [qualifier, references] : metas.references.value())
    {
        for (const tinyusdz::Reference& reference : references)
        {
            if (!reference.asset_path.GetAssetPath().empty())
            {
                Log::warning(std::format("{}: references another file ({}); not followed.",
                                         path, reference.asset_path.GetAssetPath()).c_str());
                continue;
            }
            if (const auto target = context.stage.GetPrimAtPath(reference.prim_path)) { return target.value(); }
        }
    }
    return nullptr;
}
```

```cpp
    // importPrim, just before Chapter 14's loop over prim.children() (Chapter 19): an instance's
    // contents are its prototype's children, under the instance's own node.
    if (const tinyusdz::Prim* prototype = instancePrototype(context, prim, path))
    {
        for (const tinyusdz::Prim& child : prototype->children())
        {
            importPrim(context, child, node, usdWorld);
        }
    }
```

A non-instanceable prim with a reference still arrives empty, as Chapter 14
says; following every reference is composition, and the line above follows
only the ones that promise to be identical copies.

---

## 10. USD instancing, part two: the `PointInstancer`

Scene-graph instancing costs a prim per instance in the file. For forests,
crowds of rocks, and scattered debris — thousands to millions of copies — USD
has a prim that stores instances as **arrays**:

| Attribute | Type | Per instance |
| --- | --- | --- |
| `prototypes` | relationship | The prototype prims, by index |
| `protoIndices` | `int[]` | Which prototype |
| `positions` | `point3f[]` | Translation |
| `orientations` | `quath[]` | Rotation, as a quaternion of **half floats** (16-bit floats; real part first) |
| `scales` | `float3[]` | Scale |
| `ids` | `int64[]` | A stable id; the instance's index when not authored |
| `invisibleIds` | `int64[]` | Ids to hide |
| `inactiveIds` | `int64[]` | Ids to remove entirely |

`orientations` are half floats to halve their size — a forest of a million
trees spends 8 MB on rotations instead of 16 — and TinyUSDZ's `half_to_float`
widens them. USD composes each instance's transform as **scale, then rotate,
then translate**, applied after the prototype prim's own transform and before
the instancer's — in matrix terms, `instancerWorld × T × R × S ×
prototypeLocal`, which is exactly what a node with a `Transform` of (T, R, S),
parented under the instancer and holding the prototype's nodes, computes.

So the importer makes **one node per instance**, under the instancer's node,
and imports the prototype prim beneath it — through the mesh cache of
section 9, so every instance of a prototype shares its meshes. The prototypes
themselves usually live under the instancer (`Trees/Prototypes/Pine`), and USD
draws them only through the instancer; so the instancer's branch imports its
own children only that way, never as ordinary children.

Is a node per instance too many? For thousands, no: a node is a transform, a
name, and a few indices; Chapter 12's dirty flags mean an unmoving forest costs
nothing to update; and the inspector can select and move any single tree,
which is worth having. For millions, the instances would stay arrays — an
instancer component whose expansion happens in `CollectDraws`, or on the GPU —
and that is the grass chapters' territory.

`importPointInstancer` imports each prototype through `importPrim`, and
`importPrim`'s dispatch calls `importPointInstancer` — the two call each other,
so `importPrim` is declared above both. The declaration and the function go
just above `importPrim`'s definition:

```cpp
// UsdImport.cpp - file scope, above importPointInstancer (Chapter 19): Chapter 14's importPrim,
// declared, so the two functions that call each other can both be defined.
static void importPrim(ImportContext& context, const tinyusdz::Prim& prim, pf::scene::NodeIndex parent,
                       const glm::dmat4& parentUsdWorld);
```

```cpp
// UsdImport.cpp - file scope, above the namespace block (Chapter 19). A UsdGeomPointInstancer:
// one node per instance under `node`, holding its prototype's nodes - whose meshes the mesh
// cache shares between instances.
static void importPointInstancer(ImportContext& context, const tinyusdz::GeomPointInstancer& instancer,
                                 pf::scene::NodeIndex node, const glm::dmat4& usdWorld, const std::string& path)
{
    std::vector<const tinyusdz::Prim*> prototypes;
    if (instancer.prototypes)
    {
        const tinyusdz::Relationship& relationship = instancer.prototypes.value();
        const std::vector<tinyusdz::Path> targets = relationship.is_path()
            ? std::vector<tinyusdz::Path>{ relationship.targetPath } : relationship.targetPathVector;
        for (const tinyusdz::Path& target : targets)
        {
            const auto prim = context.stage.GetPrimAtPath(target);
            prototypes.push_back(prim ? prim.value() : nullptr);
        }
    }

    // Every per-instance array, at the default time; an unauthored one stays empty.
    std::vector<int32_t>                   protoIndices;
    std::vector<tinyusdz::value::point3f>  positions;
    std::vector<tinyusdz::value::quath>    orientations;
    std::vector<tinyusdz::value::float3>   scales;
    std::vector<int64_t>                   ids;
    std::vector<int64_t>                   invisibleIds;
    std::vector<int64_t>                   inactiveIds;
    auto read = [](const auto& attribute, auto& values) {
        if (const auto value = attribute.get_value()) { value.value().get_default(&values); }
    };
    read(instancer.protoIndices, protoIndices);
    read(instancer.positions, positions);
    read(instancer.orientations, orientations);
    read(instancer.scales, scales);
    read(instancer.ids, ids);
    read(instancer.invisibleIds, invisibleIds);
    if (const auto inactive = instancer.inactiveIds.get_value()) { inactiveIds = inactive.value(); }

    const std::set<int64_t> invisible(invisibleIds.begin(), invisibleIds.end());
    const std::set<int64_t> inactive(inactiveIds.begin(), inactiveIds.end());
    uint32_t badIndices = 0;
    for (size_t i = 0; i < protoIndices.size(); ++i)
    {
        const int64_t id = i < ids.size() ? ids[i] : static_cast<int64_t>(i);
        if (inactive.contains(id)) { continue; }

        const int32_t prototype = protoIndices[i];
        if (prototype < 0 || static_cast<size_t>(prototype) >= prototypes.size() || prototypes[prototype] == nullptr)
        {
            ++badIndices;
            continue;
        }

        pf::scene::Transform local;
        if (i < positions.size())
        {
            local.translation = glm::vec3(positions[i].x, positions[i].y, positions[i].z);
        }
        if (i < orientations.size())
        {
            const tinyusdz::value::quath& q = orientations[i];
            local.rotation = glm::normalize(glm::quat(tinyusdz::value::half_to_float(q.real),
                                                      tinyusdz::value::half_to_float(q.imag[0]),
                                                      tinyusdz::value::half_to_float(q.imag[1]),
                                                      tinyusdz::value::half_to_float(q.imag[2])));
        }
        if (i < scales.size())
        {
            local.scale = glm::vec3(scales[i][0], scales[i][1], scales[i][2]);
        }

        const pf::scene::NodeIndex instance =
            context.scene.AddNode(std::format("Instance{}", id), node, local);
        if (invisible.contains(id)) { context.scene.SetVisible(instance, false); }
        importPrim(context, *prototypes[prototype], instance, usdWorld * glm::dmat4(local.Matrix()));
    }
    if (badIndices > 0)
    {
        Log::warning(std::format("{}: {} instances name no usable prototype; skipped.", path, badIndices).c_str());
    }
}
```

`glm::quat`'s constructor takes `(w, x, y, z)` — the real part first, as USD
stores it. `UsdImport.cpp` gains `<set>`.

The instancer joins `asXformable` — it has a transform, like any `Gprim` — and
gets a branch in the dispatch that **returns** instead of falling through to
the children loop, replacing Chapter 14's "skipped" warning for it:

```cpp
// UsdImport.cpp, in asXformable (Chapter 19):
if (const auto* instancer = prim.as<tinyusdz::GeomPointInstancer>()) { return instancer; }
```

```cpp
    // importPrim's dispatch (Chapter 19), beside the camera and light branches.
    else if (const auto* instancer = prim.as<tinyusdz::GeomPointInstancer>())
    {
        importPointInstancer(context, *instancer, node, usdWorld, path);
        return;   // its children are its prototypes: imported only through its instances
    }
```

Two things this importer does not do, both worth naming. **A prototype that
is mirrored by an instance's negative scale** gets its own mesh copy through the
mirrored cache key — correct, at the cost of sharing. And
**`velocities`/`accelerations`** — motion blur data — are ignored.

---

## 11. The forest

### The test scene

`Assets/Scenes/Forest.usda` is four thousand trees on a jittered grid, in two
kinds, each with its own random turn and size; a few hidden through
`invisibleIds`; six rocks placed as `instanceable` references to a class
prototype; and a ground. The trees are boxes, so that the triangle count stays
small and what is measured is draw calls — a box trunk under a box crown, which
is enough to see. Four thousand array entries are not hand-written, so a script
writes the file: `Assets/Scenes/make_forest.py`, printed in Appendix A. Like
Chapter 15's, it runs once and its output is committed.

What to expect from it: 4096 trees minus the 43 hidden is 4053, each two
boxes, so 8106 tree `DrawItem`s when the whole forest is in view, plus the
ground and twelve rock boxes. Four meshes for the trees (each prototype's trunk
and crown), two for the rocks, one ground: seven commands. Four materials, all
opaque and single-sided: **four multi-draw calls for the entire scene**. And
the scene list's largest `instanceCount` is around two thousand — one
prototype's trunks.

**Culling is already per instance.** Every tree is a node with its own bounds,
so Chapter 12's `CollectDraws` drops the trees outside the view before
batching ever sees them, and the `instanceCount`s shrink as you turn away.
That is CPU culling of instances — correct, and at four thousand trees about
as fast as it needs to be. At grass scale it moves to a compute shader, which
writes the instance buffer and the counts itself: Chapter 26.

---

## Exit check

Run `UsdViewerDemo` on `Forest.usda`, with validation and synchronization
validation on.

- [ ] **Thousands of instances, few calls.** With the whole forest in view, the
      panel shows about 8100 draw items, 7 commands, 4 runs, and **4 draw
      calls** in multi-draw mode; the largest batch is about 2000 instances.
      The command table shows those numbers as they sit in the indirect
      buffer.
- [ ] **Every mode draws the same image.** Switching through all four modes
      changes the draw-call count — about 8100, 7, 7, 4 — and not one pixel.
      On a GPU, "One per item" is visibly slower.
- [ ] **Instances are culled.** Turning the camera away from most of the
      forest drops the items and the `instanceCount`s in the table, but not
      the number of draw calls.
- [ ] **The file's instancing is honored.** Every 97th tree is missing (the
      `invisibleIds`); the six rocks stand in a ring around the centre, and no
      rock stands at the origin (the class prototype is not drawn). Making a
      hidden tree visible in the hierarchy brings it back, and moving any one
      tree in the inspector moves only that tree.
- [ ] **Shadows still work** (Chapter 17): the trees cast them, from the batched
      caster draws, in every draw mode.
- [ ] **The feature is real.** Temporarily set `drawIndirectFirstInstance` to
      `VK_FALSE` in `CreateDevice` and run with GPU-assisted validation
      (`VK_LAYER_GPUAV_ENABLE=1`, or vkconfig's GPU-AV): it reports
      `VUID-VkDrawIndexedIndirectCommand-firstInstance-00554`. With core
      validation only, it says nothing — section 6's warning.
- [ ] Chapters 15 and 16's scenes look as they did.

Next: [20 — Compute Fundamentals](20-Compute-Fundamentals.md)

---

## Appendix A — `make_forest.py`

Reference: the script that writes `Forest.usda` (section 11). It is plain
Python 3 with the standard library only, runs once from `Assets/Scenes/`, and
is not part of the build.

```python
# Assets/Scenes/make_forest.py
# Writes Forest.usda: a PointInstancer of trees and a few instanceable rocks. Run once,
# from Assets/Scenes/:
#     python make_forest.py [trees per side]
# Plain Python 3, standard library only. Not part of the build: commit what it writes.
import math, random, sys

SIDE = int(sys.argv[1]) if len(sys.argv) > 1 else 64      # 64 x 64 = 4096 trees
SPACING = 2.0
random.seed(19)

positions, orientations, scales, proto = [], [], [], []
for z in range(SIDE):
    for x in range(SIDE):
        px = (x - SIDE / 2) * SPACING + random.uniform(-0.6, 0.6)
        pz = (z - SIDE / 2) * SPACING + random.uniform(-0.6, 0.6)
        positions.append(f"({px:.3f}, 0, {pz:.3f})")
        # A random turn about +Y, as a quaternion (real, i, j, k) - written as half floats.
        angle = random.uniform(0.0, 2.0 * math.pi)
        orientations.append(f"({math.cos(angle / 2):.4f}, 0, {math.sin(angle / 2):.4f}, 0)")
        s = random.uniform(0.7, 1.3)
        scales.append(f"({s:.3f}, {s * random.uniform(0.8, 1.4):.3f}, {s:.3f})")
        proto.append(str(random.randint(0, 1)))
# Every 97th tree is hidden through invisibleIds - ids default to the instance's index.
invisible = [str(i) for i in range(0, SIDE * SIDE, 97)]

def material(name, color, roughness):
    return f"""
        def Material "{name}"
        {{
            token outputs:surface.connect = </Forest/Materials/{name}/Surface.outputs:surface>

            def Shader "Surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = {color}
                float inputs:roughness = {roughness}
                token outputs:surface
            }}
        }}"""

def cube(name, size, scale, translate, mat):
    return f"""
                def Cube "{name}" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {{
                    double size = {size}
                    float3 xformOp:scale = {scale}
                    double3 xformOp:translate = {translate}
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </Forest/Materials/{mat}>
                }}"""

rocks = []
for i in range(6):
    angle = i / 6 * 2 * math.pi
    rocks.append(f"""
    def Xform "Rock{i}" (
        instanceable = true
        prepend references = </Forest/Library/Rock>
    )
    {{
        double3 xformOp:translate = ({8 * math.cos(angle):.3f}, 0, {8 * math.sin(angle):.3f})
        float3 xformOp:rotateXYZ = (0, {math.degrees(angle):.1f}, 0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }}""")

with open("Forest.usda", "w") as f:
    f.write(f"""#usda 1.0
(
    defaultPrim = "Forest"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "Forest"
{{
    def Scope "Materials"
    {{{material("Bark", "(0.30, 0.18, 0.09)", 0.9)}{material("Leaves", "(0.10, 0.35, 0.08)", 0.7)}{material("Stone", "(0.45, 0.45, 0.42)", 0.8)}{material("Ground", "(0.25, 0.22, 0.18)", 1.0)}
    }}

    # Templates: a class is never drawn by itself, only through what references it.
    class Xform "Library"
    {{
        def Xform "Rock"
        {{{cube("Body", 1, "(1.2, 0.6, 0.9)", "(0, 0.3, 0)", "Stone")}{cube("Top", 1, "(0.6, 0.4, 0.5)", "(0.2, 0.75, 0)", "Stone")}
        }}
    }}

    def Mesh "Ground" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {{
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-80, 0, 80), (80, 0, 80), (80, 0, -80), (-80, 0, -80)]
        uniform token subdivisionScheme = "none"
        rel material:binding = </Forest/Materials/Ground>
    }}

    # High above the forest's near edge: the whole forest in view.
    def Camera "Camera"
    {{
        float focalLength = 24
        float verticalAperture = 24
        float2 clippingRange = (0.1, 500)
        double3 xformOp:translate = (0, 60, 110)
        float xformOp:rotateX = -30
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateX"]
    }}
{"".join(rocks)}

    def PointInstancer "Trees"
    {{
        rel prototypes = [</Forest/Trees/Prototypes/Pine>, </Forest/Trees/Prototypes/Oak>]
        int[] protoIndices = [{", ".join(proto)}]
        point3f[] positions = [{", ".join(positions)}]
        quath[] orientations = [{", ".join(orientations)}]
        float3[] scales = [{", ".join(scales)}]
        int64[] invisibleIds = [{", ".join(invisible)}]

        # Under the instancer: drawn only through its instances.
        def Scope "Prototypes"
        {{
            def Xform "Pine"
            {{{cube("Trunk", 1, "(0.25, 1.2, 0.25)", "(0, 0.6, 0)", "Bark")}{cube("Crown", 1, "(1.2, 1.6, 1.2)", "(0, 2.0, 0)", "Leaves")}
            }}
            def Xform "Oak"
            {{{cube("Trunk", 1, "(0.3, 1.0, 0.3)", "(0, 0.5, 0)", "Bark")}{cube("Crown", 1, "(1.8, 1.0, 1.8)", "(0, 1.5, 0)", "Leaves")}
            }}
        }}
    }}
}}
""")
```
