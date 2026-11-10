# Renderer convergence

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

**Goal:** get the engine ready for a second representation of every tree.
After Chapter 39 the understory keeps its own copy of the plants' meshes,
every shadow cascade draws one caster list, and a frame whose required upload
fails is still submitted. Three steps change that, one contract at a time:
`SceneRenderer` becomes the one owner of mesh geometry; each shadow cascade
gets its own visibility list over the same instances, and the camera's depth
convention is stated once; and a failed recording stops before the fence
reset and the submit. A short supplied section moves the distance haze into
the engine's shaders. A fourth, optional step gives Chapters 29 and 30's FFT
simulations one resource owner.

**Read after** [Chapter 39's plant exit check](39-Plants.md#exit-check). Steps
1–3 are required before Chapter 40; step 4 is optional and needs Chapters 29
and 30. This page is Chapter 39's handoff to Chapter 40, on a page of its own
so that the chapters whose engine it changes can point at it; its attempts
keep their `CH39-` names.

**ROADMAP:** step 21+ — the engine under the `Horizon` demo converges.

**Module:** `pf::vulkan_graphics` (`SceneRenderer`, `ShadowMaps`,
`SceneTargets` and `VulkanRenderer` change; `Visibility.h` and
`DepthConvention.h` are new, and step 4 adds `OceanFft`) and `pf::demos`
(`Demo.h` and every demo's `Record`; `Understory` borrows the renderer's
geometry). Nothing here adds a plant, a seed or a placement.

**Math:** a box against a plane by its centre and its reach, and a cascade's
near distance moved back by the blend fraction (step 2); a depth mapping and
its inverse with near and far swapped (step 2); the haze's exponential fade
(the haze section); the passes of a power-of-two FFT and which copy holds the
result (step 4).

**Prerequisites:**

- Chapter 39, built and running, with its exit check passed: sections
  [9](39-Plants.md#9-planted-by-the-gpu) and
  [10](39-Plants.md#10-drawn-from-the-counts)'s understory (its own copy of the
  plants' meshes, `CopyMeshes` and `Draw`, which step 1 replaces, and its
  checked `RecordCompute`), and section
  [3](39-Plants.md#3-cutting-them-out)'s leaf pipelines, which keep `GREATER`
  through step 2.
- Step 1:
  [Chapter 8, section 2](08-Resources-And-Descriptors.md#2-a-buffer-end-to-end)
  (staging and `immediateSubmit`);
  [Chapter 11, section 6](11-Meshes.md#6-getting-a-mesh-onto-the-gpu) (a mesh's
  upload); Chapter 19, sections
  [4](19-Instancing-And-Indirect.md#4-one-vertex-buffer-for-every-mesh) and
  [6](19-Instancing-And-Indirect.md#6-indirect-draws) (`MeshRange`, indirect
  commands and `firstInstance`).
- Step 2: [Chapter 12, section 10](12-Scene-Graph.md#10-culling-on-the-cpu) (a
  box against the frustum's planes);
  [Chapter 17, section 11](17-Shadows.md#11-cascaded-shadow-maps) (cascades and
  their blend bands);
  [Chapter 18, section 3](18-Anti-Aliasing.md#3-what-the-gpu-offers) (the
  resolve modes the GPU offers);
  [Chapter 22, section 6](22-Deferred-Shading.md#6-the-lighting-pass)
  (`EnableDeferred`), if your route has the deferred path;
  [Chapter 35, section 6](35-Seeing-Far.md#6-reversed-depth-in-the-frame)
  (reversed depth).
- The haze: Chapter 36, sections [10](36-Terrain-To-The-Horizon.md#10-the-sea)
  and [11](36-Terrain-To-The-Horizon.md#11-haze-and-the-skirt), and
  [Chapter 37, section 2](37-Objects-At-A-Distance.md#2-a-scene-of-the-demos-own)
  (`skyColor` and `hazed` in `HorizonShading.glsl`);
  [Chapter 24, section 6](24-Image-Based-Lighting.md#6-the-specular-cube-a-level-per-roughness)
  (set 0's binding 11, the sky's specular cube); the index's
  [`FrameData`, whole](../VulkanTutorial.md#framedata-whole) and its append-only
  rule.
- Step 3: Chapter 4, sections
  [2](04-Commands-And-Synchronization.md#2-frames-in-flight) and
  [4](04-Commands-And-Synchronization.md#4-the-frame-in-order) (frames in flight
  and their fences);
  [Chapter 8, section 2](08-Resources-And-Descriptors.md#2-a-buffer-end-to-end)
  (checked uploads); Chapter 9, sections
  [2](09-Demo-Harness.md#2-the-demo-interface) and
  [5](09-Demo-Harness.md#5-the-renderers-side) (the demo's side and the
  renderer's).
- Step 4, optional: Chapters 29 and 30; Chapter 20, sections
  [2](20-Compute-Fundamentals.md#2-the-compute-pipeline)
  (`createComputePipeline`) and [4](20-Compute-Fundamentals.md#4-storage-images)
  (`createDescriptorSets`).

> **Jump:** until now the Horizon chapters changed their own demo and added
> only small pieces outside it: the two image imports in `UsdImport`
> (Chapter 36, section 8, and Chapter 38, section 2) and a few read-only
> accessors on `SceneRenderer` (Chapter 39, section 3). Here the engine's own
> contracts change, and every demo's `Record` with them: who owns geometry,
> what a shadow cascade draws, what depth means, and whether a frame can
> fail. Hold one question per step: what did the old code assume, and which
> caller relied on it? Each step has its own CPU program; run it before the
> next step starts. Step 2's program also reads the haze fields, so run it at
> the end of the haze section that follows step 2.

### Where everything lands

```text
Source/PillowFort/VulkanGraphics/
  SceneRenderer.h, .cpp     ranges others borrow; lists per view;
                            checked uploads                              steps 1-3
  Visibility.h              the visibility tests, new                    step 2
  DepthConvention.h         the depth policy, new, supplied whole        step 2
  SceneTargets.h, .cpp      supplied whole                               step 2
  ShadowMaps.h, .cpp        supplied header; the fit and caster volumes  step 2
  VulkanRenderer.h, .cpp    the resolve modes; a frame that can fail     steps 2, 3
  OceanFft.h, .cpp          the shared FFT, new (optional)               step 4
Source/PillowFort/Demos/
  Demo.h, every demo        Record reports failure                       step 3
  Horizon/Understory.h, .cpp  borrows the renderer's geometry            step 1
  Horizon/HorizonDemo.cpp   the depth convention; writes the haze        steps 2, 3; haze
  Ocean/OceanDemo.cpp, Sea/SeaSurface.cpp   use OceanFft (optional)      step 4
Shaders/Include/
  SharedShaderTypes.h       FrameData's haze fields, appended            haze
  DistanceHaze.glsl         the shared haze, new                         haze
Shaders/Horizon/
  HorizonShading.glsl       skyColor and hazed call it                   haze
Shaders/Scene/
  Mesh.frag.glsl            the haze, after the lights                   haze
```

Steps 2 and 4 and the haze section add files: regenerate
(`GenerateProjects.bat`), then build. Each step names the functions it
replaces and where its new ones go.

---

## Renderer convergence checkpoint

Chapter 39's plants now run. Keep that result before changing ownership.
Chapter 39, section 9 deliberately gave `Understory` its own geometry buffers
so the first compute-to-draw lesson was local. Chapter 40 will add yet another
representation of a tree. Copying geometry again, or reusing one visibility
list for every view, would make that next lesson harder to reason about.

This is a later **integration handoff**, not an extra plant-generation
algorithm. Work through the first three steps in order; run their CPU checks
between edits. They preserve the existing assets, seeds, placements and leaf
math. Between steps 2 and 3, a short supplied section moves the distance haze
into the engine; it has no attempt. The fourth step is a separate
consolidation for readers who have also completed Chapters 29 and 30.

| Step | Smallest change | Observable checkpoint |
| --- | --- | --- |
| [1. Geometry ownership](#convergence-geometry) | Borrow numeric draw ranges from `SceneRenderer`; bind its current buffers | A forced growth failure preserves old geometry; successful growth changes handles but preserves old ranges |
| [2. Visibility and depth](#convergence-visibility-depth) | Filter each light cascade independently; choose a complete camera-depth policy | Off-camera casters survive, sparse retained instances keep their IDs, and both depth policies round-trip |
| [3. Fallible frames](#convergence-fallible-frames) | Propagate a required upload error to the submission owner | A failed recording neither resets the slot fence nor submits a partial command buffer |
| [4. Shared FFT resources](#convergence-shared-fft) (optional) | One resource owner and stage scheduler, independent simulation fields | Every supported power-of-two plan ends in copy zero; invalid configuration is rejected |

**Source checkpoints.** The [CPU checkpoint guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md)
provides editable, content-identified source exports alongside the full-repository
CPU targets named below. These are exercises on the current assembled
CPU/reference implementation, not historical source immediately after Chapter
39. The older immutable `renderer-convergence` pair in the
[stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md) remains a separate
visibility exercise: its starter keeps every caster and must fail only
`FAIL: cascade rejection`; its frame-order invariant must pass in both
variants. That pair does not supply four reconstructed historical starters.
CPU checks here exercise production code with Vulkan calls replaced where
necessary; they open no graphics window. A native run, rendered shadow
comparison and timing measurement are separate checks, not implied by a CPU
pass or by exporting a source tree.

<a id="convergence-geometry"></a>

### Step 1 — One geometry owner

**Prerequisites and files.** Reuse Chapter 11's mesh upload, Chapter 19's
`MeshRange`, indexed indirect command and `firstInstance`, and Chapter 8's
staging buffer and `immediateSubmit`. Change
[`SceneRenderer.h/.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/SceneRenderer.h)
and [`Understory.h/.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/Understory.cpp).
The renderer owns vertices and indices; `Understory` still owns its generated
instance records, indirect-command template, parameter buffers and compute
pipeline. Its lifetime must end before the renderer's.

<a id="ch39-convergence-geometry-owner"></a>

### Attempt CH39-convergence-geometry-owner: borrow ranges that survive growth

Remove the second copy of plant vertices and indices made by Chapter 39,
section 9. Register each mesh once with `SceneRenderer`, then let the
understory draw its submeshes through that same allocation. Work out which
values a consumer may keep when another mesh makes the renderer grow its
buffers.

**Acceptance:** Understory no longer allocates or destroys geometry buffers.
A missing mesh range reports failure. A failed growth copy leaves the old
buffers and registered range usable and publishes no new mesh index. A
successful growth uses new buffer handles while all earlier `firstIndex` and
`vertexOffset` values retain their meaning.

**Transfer:** Append a rock after preparing the plant commands. Explain why
caching the old `VkBuffer` is wrong, and why retaining a pointer into the
renderer's growing `std::vector<MeshRange>` is wrong even when numeric ranges
remain stable.

<details>
<summary>Hint 1: the idea</summary>

Share the storage, not the foliage shader. A draw needs numbers describing a
mesh and the buffers that currently contain those numbers' geometry. Those
have different lifetimes.

</details>

<details>
<summary>Hint 2: the data and lifetime</summary>

Copy `firstIndex`, `vertexOffset` and submesh ranges into commands. Resolve a
range only while constructing those commands; a later `AddMesh` can
reallocate the range vector. Bind current buffers when recording. Before
replacing buffers, finish their GPU users and copy the old bytes into
candidate allocations.

</details>

<details>
<summary>Hint 3: a concrete route</summary>

Expose `GeometryRange(mesh)` and `BindGeometry(commandBuffer)`. Grow both
buffers without publishing either until allocation and copying succeed.
`AddMesh` keeps its output index invalid until its own append succeeds.
`Understory::BuildMeshCommands` copies registered submesh offsets and material
indices; `Draw` binds geometry through the renderer, then binds its instance
buffer at binding 1.

</details>

<details>
<summary>Worked solution: a range is borrowed briefly, its numbers are copied</summary>

In `SceneRenderer.h`, retain Chapter 19's numeric range and add its local
bounds; the cascade step will transform that bound with each instance:

```cpp
struct MeshRange
{
    int32_t                     vertexOffset = 0;   // added to every index of the mesh
    uint32_t                    firstIndex   = 0;   // its first index in the shared index buffer
    std::vector<scene::Submesh> submeshes;          // index ranges relative to firstIndex
    bool                        doubleSided  = false;
    scene::Aabb                 bounds;
};
```

Inside the existing public section, add these accessors. They do not transfer
ownership or promise that the returned pointer survives another registration:

```cpp
const MeshRange* GeometryRange(uint32_t mesh) const
{
    return mesh < m_meshRanges.size() ? &m_meshRanges[mesh] : nullptr;
}
void BindGeometry(VkCommandBuffer commandBuffer) const;
```

The complete replacement growth and mesh-publication functions are below, in
`SceneRenderer.cpp`, inside `pf::vulkan_graphics`. Existing `createGeometryBuffer`
creates transfer-source/destination geometry buffers; existing `immediateSubmit`
returns a checked result only after its copy has completed. Keep those Chapter
8/11 helpers. The file-scope helper must permit copying geometry both into
and out of a buffer. Replace a transfer-destination-only helper with:

```cpp
static pf::vulkan_graphics::AllocatedBuffer createGeometryBuffer(pf::vulkan_graphics::VulkanContext& context,
                                                                 VkDeviceSize size, VkBufferUsageFlags usage)
{
    return pf::vulkan_graphics::createBuffer(context, size,
                                             usage | VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                                             false);
}
```

Declare `GrowGeometry(uint32_t vertexCount, uint32_t indexCount)` privately as
returning `InitializationResult`. The 64-bit capacity calculations avoid
overflow before clamping to Vulkan's draw-index limits.

```cpp
InitializationResult SceneRenderer::GrowGeometry(uint32_t vertexCount, uint32_t indexCount)
{
    if (vertexCount <= m_vertexCapacity && indexCount <= m_indexCapacity) { return InitializationResult::success(); }

    // A frame in flight may be drawing from the old buffers: they cannot be replaced under it.
    const VkResult idle = vkDeviceWaitIdle(m_context.device);
    if (idle != VK_SUCCESS)
    {
        return InitializationResult::failure(std::format("vkDeviceWaitIdle before growing geometry failed: {}.", string_VkResult(idle)));
    }

    const uint32_t vertexCapacity = static_cast<uint32_t>(std::min<uint64_t>(INT32_MAX,
        std::max({ uint64_t(vertexCount), uint64_t(m_vertexCapacity) * 2, uint64_t(65536) })));
    const uint32_t indexCapacity = static_cast<uint32_t>(std::min<uint64_t>(UINT32_MAX,
        std::max({ uint64_t(indexCount), uint64_t(m_indexCapacity) * 2, uint64_t(196608) })));
    AllocatedBuffer vertices = createGeometryBuffer(m_context, vertexCapacity * sizeof(scene::Vertex),
                                                    VK_BUFFER_USAGE_VERTEX_BUFFER_BIT);
    AllocatedBuffer indices  = createGeometryBuffer(m_context, indexCapacity * sizeof(uint32_t),
                                                    VK_BUFFER_USAGE_INDEX_BUFFER_BIT);
    if (vertices.buffer == VK_NULL_HANDLE || indices.buffer == VK_NULL_HANDLE)
    {
        destroyBuffer(m_context, vertices);
        destroyBuffer(m_context, indices);
        return InitializationResult::failure("Could not grow the shared geometry buffers.");
    }

    if (m_vertexCount > 0)   // what was uploaded already moves into the new buffers
    {
        const InitializationResult copied = immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
            // Every earlier upload's writes, before this copy reads them.
            memoryBarrier(commandBuffer, VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                          VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);
            const VkBufferCopy vertexCopy{ .size = m_vertexCount * sizeof(scene::Vertex) };
            const VkBufferCopy indexCopy{ .size = m_indexCount * sizeof(uint32_t) };
            vkCmdCopyBuffer(commandBuffer, m_vertices.buffer, vertices.buffer, 1, &vertexCopy);
            vkCmdCopyBuffer(commandBuffer, m_indices.buffer, indices.buffer, 1, &indexCopy);
            // This copy's writes, before vertex input reads the new buffers: Chapter 11's upload row.
            memoryBarrier(commandBuffer, VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                          VK_PIPELINE_STAGE_2_VERTEX_ATTRIBUTE_INPUT_BIT | VK_PIPELINE_STAGE_2_INDEX_INPUT_BIT,
                          VK_ACCESS_2_VERTEX_ATTRIBUTE_READ_BIT | VK_ACCESS_2_INDEX_READ_BIT);
        });
        if (!copied)
        {
            destroyBuffer(m_context, vertices);
            destroyBuffer(m_context, indices);
            return copied;
        }
    }
    destroyBuffer(m_context, m_vertices);
    destroyBuffer(m_context, m_indices);
    m_vertices       = vertices;
    m_indices        = indices;
    m_vertexCapacity = vertexCapacity;
    m_indexCapacity  = indexCapacity;
    return InitializationResult::success();
}

InitializationResult SceneRenderer::AddMesh(const scene::MeshData& mesh, uint32_t& index)
{
    index = UINT32_MAX;
    if (mesh.vertices.empty() || mesh.indices.empty() ||
        uint64_t(m_vertexCount) + mesh.vertices.size() > INT32_MAX ||
        uint64_t(m_indexCount) + mesh.indices.size() > UINT32_MAX)
    {
        return InitializationResult::failure("AddMesh: empty mesh or shared geometry exceeds the 32-bit draw limits.");
    }
    const uint32_t vertexCount = static_cast<uint32_t>(mesh.vertices.size());
    const uint32_t indexCount  = static_cast<uint32_t>(mesh.indices.size());
    MeshRange range{
        .vertexOffset = static_cast<int32_t>(m_vertexCount),
        .firstIndex   = m_indexCount,
        .submeshes    = mesh.submeshes,
        .doubleSided  = mesh.doubleSided,
        .bounds       = scene::computeBounds(mesh),
    };

    const VkDeviceSize vertexBytes = vertexCount * sizeof(scene::Vertex);
    const VkDeviceSize indexBytes  = indexCount * sizeof(uint32_t);
    AllocatedBuffer staging = createBuffer(m_context, vertexBytes + indexBytes,
                                           VK_BUFFER_USAGE_TRANSFER_SRC_BIT, true);
    if (staging.buffer == VK_NULL_HANDLE || staging.mapped == nullptr)
    {
        destroyBuffer(m_context, staging);
        return InitializationResult::failure("AddMesh: creating the staging buffer failed.");
    }
    {
        auto* bytes = static_cast<std::byte*>(staging.mapped);
        std::memcpy(bytes, mesh.vertices.data(), static_cast<size_t>(vertexBytes));
        std::memcpy(bytes + vertexBytes, mesh.indices.data(), static_cast<size_t>(indexBytes));
        const VkResult flushed = vmaFlushAllocation(m_context.allocator, staging.allocation, 0, VK_WHOLE_SIZE);
        if (flushed != VK_SUCCESS)
        {
            destroyBuffer(m_context, staging);
            return InitializationResult::failure(std::format("AddMesh: staging flush failed: {}.", string_VkResult(flushed)));
        }
        if (auto grown = GrowGeometry(m_vertexCount + vertexCount, m_indexCount + indexCount); !grown)
        {
            destroyBuffer(m_context, staging);
            return grown;
        }

        const InitializationResult copied = immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
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
            memoryBarrier(commandBuffer, VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                          VK_PIPELINE_STAGE_2_VERTEX_ATTRIBUTE_INPUT_BIT | VK_PIPELINE_STAGE_2_INDEX_INPUT_BIT,
                          VK_ACCESS_2_VERTEX_ATTRIBUTE_READ_BIT | VK_ACCESS_2_INDEX_READ_BIT);
        });
        destroyBuffer(m_context, staging);
        if (!copied) { return copied; }
        m_vertexCount += vertexCount;
        m_indexCount  += indexCount;
    }
    m_meshRanges.push_back(std::move(range));
    index = static_cast<uint32_t>(m_meshRanges.size() - 1);
    return InitializationResult::success();
}
```

There are two commitments. `GrowGeometry` replaces storage after copying all
previously registered geometry; `AddMesh` publishes the new logical range only
after appending its bytes. If growth succeeds but the following append fails,
the storage may already be larger, but earlier meshes are still valid and the
new mesh index/counts are not published. This is not a promise that every
failed append restores the old buffer handles.

`BindGeometry` is the only new binding function. Put it in `SceneRenderer.cpp`:

```cpp
void SceneRenderer::BindGeometry(VkCommandBuffer commandBuffer) const
{
    const VkDeviceSize zero = 0;
    vkCmdBindVertexBuffers(commandBuffer, 0, 1, &m_vertices.buffer, &zero);
    vkCmdBindIndexBuffer(commandBuffer, m_indices.buffer, 0, VK_INDEX_TYPE_UINT32);
}
```

`Understory.h` now forward-declares `pf::vulkan_graphics::SceneRenderer` and holds
`const vulkan_graphics::SceneRenderer* m_renderer = nullptr;`
instead of its private geometry allocations. Its `Initialize` takes a
`const SceneRenderer& renderer`, stores `m_renderer = &renderer`, and calls
`BuildMeshCommands(props)` before `CreateBuffers` and `CreatePass`. In
`HorizonDemo::Setup`, pass `m_sceneRenderer` to that initializer after
`RegisterProps` has registered the meshes. Keep the declaration and definition
of `Initialize` in agreement. Remove `m_vertexData`, `m_indexData`, `m_vertices` and `m_indices` from
`Understory.h`. Remove their two `destroyBuffer` calls, the two CPU-vector
swaps, and the `m_vertices`/`m_indices` default assignments from understory
teardown. Add `m_renderer = nullptr;` beside the borrowed pipeline-cache
reset; the remaining explicit resets still apply. Include `SceneRenderer.h` in `Understory.cpp` so its member calls
see the definition. Generated instance/command buffers remain owned there.
Use this replacement `CreateBuffers`; it no longer allocates or uploads
geometry:

```cpp
InitializationResult Understory::CreateBuffers()
{
    const VkDeviceSize instanceBytes = 2 * UNDERSTORY_KINDS * UNDERSTORY_MAX_CELLS * UNDERSTORY_MAX_CELLS * sizeof(PlantInstance);
    m_instances = createBuffer(m_context, instanceBytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, false);
    m_commands  = createBuffer(m_context, sizeof(UnderstoryCommands),
                               VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT
                               | VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT, false);
    bool ok = m_instances.buffer != VK_NULL_HANDLE && m_commands.buffer != VK_NULL_HANDLE;
    for (uint32_t frame = 0; frame < FRAMES_IN_FLIGHT; ++frame)
    {
        m_params[frame]   = createBuffer(m_context, sizeof(UnderstoryParams), VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, true);
        m_readback[frame] = createReadbackBuffer(m_context, sizeof(UnderstoryCommands));
        ok = ok && m_params[frame].buffer != VK_NULL_HANDLE && m_params[frame].mapped != nullptr
             && m_readback[frame].buffer != VK_NULL_HANDLE && m_readback[frame].mapped != nullptr;
    }
    if (!ok)
    {
        return InitializationResult::failure("Creating the understory's buffers failed.");
    }
    return InitializationResult::success();
}
```

Replace `CopyMeshes` with the following `BuildMeshCommands` declaration and
definition; the rest of Chapter 39, section 9's compute layout is unchanged:

```cpp
InitializationResult Understory::BuildMeshCommands(const Props& props)
{
    const scene::Scene& world = props.World();
    uint32_t command = 0;
    for (uint32_t kind = 0; kind < UNDERSTORY_KINDS; ++kind)
    {
        std::array<uint32_t, 3> meshes{};
        if (!props.PlantMeshes(UNDERSTORY_PLANTS[kind], meshes))
        {
            return InitializationResult::failure(std::format("{} was not loaded.", UNDERSTORY_PLANTS[kind]));
        }
        const uint32_t parts = static_cast<uint32_t>(world.GetMesh(meshes[0]).data.submeshes.size());
        if (world.GetMesh(meshes[1]).data.submeshes.size() != parts || command + 2 * parts > UNDERSTORY_COMMANDS)
        {
            return InitializationResult::failure(std::format("{}'s levels do not match.", UNDERSTORY_PLANTS[kind]));
        }

        // The sphere round LOD0, as Chapter 37 section 5 measures it: its radius, and its middle's height.
        const scene::Aabb& box = world.GetMesh(meshes[0]).bounds;
        m_kinds[kind] = glm::vec4(0.5f * glm::length(box.max - box.min), 0.5f * (box.min.y + box.max.y),
                                  static_cast<float>(command), static_cast<float>(parts));

        for (uint32_t level = 0; level < 2; ++level)
        {
            const scene::MeshData& data        = world.GetMesh(meshes[level]).data;
            const MeshRange* range = m_renderer->GeometryRange(meshes[level]);
            if (range == nullptr || range->submeshes.size() != data.submeshes.size())
            {
                return InitializationResult::failure("The understory's geometry was not registered with the renderer.");
            }
            for (const scene::Submesh& submesh : range->submeshes)
            {
                m_template.commands[command] = {
                    .indexCount    = submesh.indexCount,
                    .instanceCount = 0,
                    .firstIndex    = range->firstIndex + submesh.firstIndex,
                    .vertexOffset  = range->vertexOffset,
                    .firstInstance = (2 * kind + level) * UNDERSTORY_MAX_CELLS * UNDERSTORY_MAX_CELLS,
                };
                m_materials[command] = submesh.materialIndex;   // the scene's, which RegisterProps kept
                ++command;
            }
        }
    }
    if (command != UNDERSTORY_COMMANDS)
    {
        return InitializationResult::failure("The understory's plants do not have the parts it expects.");
    }
    return InitializationResult::success();
}
```

The local `range` pointer is used and discarded in the loop. Each command
copies its values. The first plant's first submesh starts at
`range->firstIndex + submesh.firstIndex`, while its vertex offset is the mesh's
registered `vertexOffset`. `firstInstance` still selects the region filled by
that kind and LOD's compute pass; sharing geometry does not change it.

Replace Chapter 39, section 10's `Draw` with this complete function:

```cpp
void Understory::Draw(VkCommandBuffer commandBuffer, const std::function<void(VkCommandBuffer, uint32_t)>& bindRun) const
{
    m_renderer->BindGeometry(commandBuffer);
    const VkDeviceSize zero = 0;
    vkCmdBindVertexBuffers(commandBuffer, 1, 1, &m_instances.buffer, &zero);
    for (uint32_t command = 0; command < UNDERSTORY_COMMANDS; ++command)
    {
        bindRun(commandBuffer, m_materials[command]);
        vkCmdDrawIndexedIndirect(commandBuffer, m_commands.buffer, command * sizeof(DrawIndexedIndirectCommand), 1,
                                 sizeof(DrawIndexedIndirectCommand));
    }
}
```

**Run the ownership check.** The production fixture is
[`MirrorBatchTests.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/MirrorBatchTests.cpp), target
`TutorialMirrorBatchTests`. It registers a cube, forces the next growth copy
to fail, checks no new range/index is published and the original two buffers
remain live, then retries successfully and records the actual bound handles.
Its assertion `shared geometry ranges or current-buffer binding changed during growth`
catches both stale bindings and changed old offsets. Caching the original
vertex buffer is a useful deliberate failure; undo that edit before moving on.
This mock proves ownership/publication behavior, not how a leaf looks on a GPU.
The full-repository build and run commands are in
[Run the four CPU contracts](#run-the-four-cpu-contracts), after step 4.

</details>

**Optional, after this step:** [Foliage batches](FoliageBatches.md) traces
two plant sizes through the commands `BuildMeshCommands` now makes, and asks
which costs grow when a field gains plants. It is a companion lesson, not a
step: Chapter 40 does not need it.

<a id="convergence-visibility-depth"></a>

### Step 2 — One instance identity, several visibility lists

**Prerequisites and files.** Use Chapter 12's world AABB and frustum-plane
test, Chapter 17's fitted cascades and blend band, Chapter 19's instanced runs,
and Chapter 35's reversed depth. Add
[`Visibility.h`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/Visibility.h) and
[`DepthConvention.h`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/DepthConvention.h);
change `SceneRenderer` and the existing depth consumers. Include `Visibility.h`
in `SceneRenderer.cpp`. It includes `Bounds.h`, `<algorithm>`, `<cmath>`,
`<span>` and `<vector>`; the functions below live in `pf::vulkan_graphics`.

**Supplied support boundary, before attempting the selection algorithm.**
Chapter 17's final source does not yet have the new cascade-volume API, caster
switch, checked shadow recording result or camera-depth parameter. Install
this bounded support first; none is an API you were expected to guess. Work
from the supplied current reference files linked below, keeping the existing
plant shaders and assets. This is an explicit integration upgrade, not a claim
that these files already existed on the historical Chapter 17/39 boundary.

| Supplied unit | Exact replacement/copy boundary | What remains your task |
| --- | --- | --- |
| [`DepthConvention.h`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/DepthConvention.h) | Copy the complete header, including Vulkan/GLM includes and `pf::vulkan_graphics` namespace | Explain and check the matching projection/clear/compare policy in the worked answer |
| [`SceneTargets.h/.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/SceneTargets.h) | Copy both complete support files as a matched pair; keep the default conventional-depth overload and its implementation | Pass the correct convention at Horizon's camera pass; the later `ScenePassOptions` continuation overload is supplied support, unused by this plant checkpoint |
| [`ShadowMaps.h`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/ShadowMaps.h) | Replace the complete header; it supplies the settings, volume struct, method declarations, stored matrices and callback contract shown below | Implement the changed fit and volume-export methods in the worked answer |
| [`ShadowMaps.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/ShadowMaps.cpp) | Retain/copy the file includes and file-scope helpers from `cascadeSplits` through `fitStable`; inside the namespace copy the complete definitions of `Initialize`, `DataBufferInfo`, `MapImageInfo`, `CreatePipelines`, `DestroyPipelines`, `Shutdown`, `Record` and `drawShadowPanel` | Replace the old `FitCascades` and add `FitCasterVolumes` with the complete implementations below; `Record` supplies the checked upload and standard-Z rendering loop, not the selection algorithm |

Forward the resolve capabilities into the supplied `SceneTargets` too. Include
`DepthConvention.h` in `VulkanRenderer.cpp`. Beside `m_depthResolveMode` in
`VulkanRenderer.h`, add:

```cpp
VkResolveModeFlags m_supportedDepthResolveModes = VK_RESOLVE_MODE_SAMPLE_ZERO_BIT;
```

In Chapter 18, section 3's MSAA query inside `VulkanRenderer::initialize`, keep
the property query and sample-count selection. Replace its assignment of
`m_depthResolveMode` with these two assignments:

```cpp
m_supportedDepthResolveModes = resolveProperties.supportedDepthResolveModes;
m_depthResolveMode = conservativeDepthResolve(m_supportedDepthResolveModes, DepthConvention::Conventional);
```

At the end of the designated `SceneTargets` initializer in
`VulkanRenderer::sceneTargets()`, keep the existing mode and append the supported
mask, in this order:

```cpp
        .depthResolveMode      = m_depthResolveMode,
        .supportedDepthResolveModes = m_supportedDepthResolveModes,
```

The renderer retains the device's complete mask, while each pass chooses the
mode appropriate to its depth convention. Without this forwarding, the
default mask would force `SAMPLE_ZERO` even when the device supports `MIN` for
conservative reversed-depth resolves.

The shadow file's support depends only on the existing error, resource, mesh,
pipeline, barrier and panel helpers plus the new depth/visibility headers. It
does not require Chapter 40's impostors, the grass continuation or an FFT.
`Record`'s exact copy boundary starts at
`InitializationResult ShadowMaps::Record(...)` and ends immediately before
`bool drawShadowPanel(...)`; replace Chapter 17's earlier body rather than
keeping a second definition beside it. The header and definition still return
`InitializationResult`. `drawShadowPanel` includes a **Cull casters** checkbox
for the full-list comparison control. A failed required shadow-data flush
returns before any cascade draws; step 3 propagates that result to submission.

These are the new header contracts supplied by `ShadowMaps.h`, shown here so
the use sites below are explicit. Add `cullCasters` to the existing settings;
`m_data` remains Chapter 17's `shared::ShadowData`, not a second matrix cache:

```cpp
// In ShadowSettings:
bool cullCasters = true;

// Namespace scope, after ShadowCasterCallback:
struct ShadowCasterVolumes
{
    std::array<scene::Frustum, SHADOW_CASCADE_COUNT> frusta{};
    uint32_t count = 0;
};

// In ShadowMaps public:
ShadowCasterVolumes FitCasterVolumes(const scene::Camera& camera, const glm::mat4& view,
                                     float aspect, std::optional<glm::vec3> sunDirection,
                                     const ShadowSettings& settings);
const glm::mat4& CascadeViewProjection(uint32_t cascade) const
{
    return m_data.cascadeViewProjection[cascade];
}
InitializationResult Record(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                            VkDescriptorSet frameSet, const scene::Camera& camera,
                            const glm::mat4& view, float aspect,
                            std::optional<glm::vec3> sunDirection,
                            const ShadowSettings& settings,
                            const ShadowCasterCallback& drawCasters,
                            const ShadowCasterCallback& extraCasters);
```

The returned matrices are valid during their cascade's recording callback;
`FitCasterVolumes` instead returns copied CPU frusta for earlier collection.
Neither accessor transfers ownership. Add the following complete public
wrapper to `SceneRenderer.h`, together with the result-returning declaration
whose implementation this exercise changes:

```cpp
ShadowCasterVolumes PrepareShadowVolumes(const scene::Camera& camera, const glm::mat4& view,
                                         float aspect, std::optional<glm::vec3> sunDirection,
                                         const ShadowSettings& settings)
{
    return m_shadows.FitCasterVolumes(camera, view, aspect, sunDirection, settings);
}
InitializationResult RecordShadows(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                                   const scene::Camera& camera, const glm::mat4& view, float aspect,
                                   std::optional<glm::vec3> sunDirection, const ShadowSettings& settings,
                                   const ShadowCasterCallback& extraCasters = {});
```

Also include `DepthConvention.h` in `SceneRenderer.h`, replace its public
initializer declaration with the following, and add the private field:

```cpp
// Public declaration; the default keeps existing demo calls conventional:
InitializationResult Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                const SceneFormats& formats,
                                DepthConvention depth = DepthConvention::Conventional);
DepthConvention Depth() const { return m_depth; }

// Private field:
DepthConvention m_depth = DepthConvention::Conventional;
```

In `SceneRenderer.cpp`, replace the initializer with this complete definition.
The default belongs only on the header declaration, not the definition:

```cpp
InitializationResult SceneRenderer::Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                               const SceneFormats& formats, DepthConvention depth)
{
    m_context       = context;
    m_pipelineCache = pipelineCache;
    m_formats       = formats;
    m_depth         = depth;

    if (auto result = m_shadows.Initialize(m_context); !result) { return result; }
    if (auto result = CreateFrameResources(); !result)    { return result; }
    if (auto result = CreateMaterialResources(); !result) { return result; }
    if (auto result = CreatePipelines(); !result)         { return result; }
    return InitializationResult::success();
}
```

Change `CreatePipelines`' mesh description from a literal comparison to
`.depthCompare = depthCompareOp(m_depth)`. If your route includes Chapter
22's deferred renderer, keep its conventional-depth implementation and add
the supplied leading `EnableDeferred` guard: when `m_depth` is reversed, log
that it draws forward and return success before allocating deferred resources.
Do not add a deferred feature on a route where it does not yet exist.

In Horizon's `Setup`, pass the reversed convention explicitly:

```cpp
if (auto result = m_sceneRenderer.Initialize(m_context.vulkan, m_context.pipelineCache,
                                             m_context.formats, DepthConvention::Reversed); !result)
{
    return result;
}
```

Horizon's `Projection` returns
`depthProjection(m_camera.verticalFov, aspect, m_camera.nearPlane,
m_camera.farPlane, DepthConvention::Reversed)`; call the supplied
`beginScenePass(commandBuffer, frame.targets, &clearColor,
DepthConvention::Reversed)` instead of a local clear-depth override. Its
custom flat/leaf camera pipelines remain `GREATER`. `SceneTargets.cpp` now
uses `depthClearValue(depth)` and `conservativeDepthResolve` where appropriate;
the shadow pipeline and its rendering attachment explicitly use
`DepthConvention::Conventional`. This installs a complete convention instead
of just changing the newly shared renderer's compare operation.

<a id="ch39-convergence-cascade-visibility"></a>

### Attempt CH39-convergence-cascade-visibility: preserve identity across independent views

Give each shadow cascade its own retained command list. An instance invisible
to the camera may cast a visible shadow. Do not renumber instance records when
you remove a caster, and do not treat unknown bounds as proof of invisibility.
Then state the camera-depth convention as one contract rather than an
independent clear value and comparison in every pipeline.

**Acceptance:** A known outside box is rejected; intersecting, missing and
nonfinite bounds remain conservative. An off-camera box can survive the light
volume. Selecting instances 2, 4 and 5 produces spans `(2, 1)` and `(4, 2)`
without changing their mesh ranges. Conventional and reversed camera depths
project/reconstruct consistently; shadow maps continue to use conventional
depth.

**Transfer:** Put a tall tree outside the camera view but inside one light
cascade. Predict which camera/cascade lists contain it. A different cascade
may reject it without either list changing that tree's instance identity.

<details>
<summary>Hint 1: the idea</summary>

The camera's question is whether a surface is visible. The shadow pass asks
whether a surface can block light reaching its receivers. These are different
volumes. Retaining an unnecessary caster costs work; dropping a possible
caster changes the picture.

</details>

<details>
<summary>Hint 2: the data and coordinates</summary>

For each plane and world-space AABB, use the box's centre and half extents;
reject only when even its furthest reach lies outside. Keep a bounds array
parallel to the shared instance array. A sparse retained set needs several
indirect commands, not one command with a reduced count over the old interval.

</details>

<details>
<summary>Hint 3: a concrete route</summary>

`conservativeCasterVisible` validates metadata before calling `intersects`.
`appendVisibleCasterCommands` flushes a span on each rejected instance and at
the end. Fit/filter against the same `CascadeViewProjection` that the shadow
pass actually renders. Let a `DepthConvention` select the camera's projection,
clear, compare and reconstruction together; do not pass the camera convention
into the shadow-map pipeline.

</details>

<details>
<summary>Worked solution: reject conservatively, keep contiguous spans</summary>

Chapter 12's plane test has a useful numerical interpretation. If a plane is
`(n, d)`, box centre is `c`, and half extent is `e`, its centre distance is
`dot(n, c) + d` and reach is `dot(abs(n), e)`. Only a sum below zero proves the
whole box is outside. With plane `x <= 6`, a box centred at `x = 6.1` with
half extent `0.2` crosses the boundary and stays. A box at `x = 100` does not.
This calculation assumes usable metadata, so the conservative wrapper checks
it before delegating to `scene::intersects`.

These are the complete selection functions in `Visibility.h`:

```cpp
// Unknown bounds stay visible. A light frustum already includes its receiver slice's caster reach.
inline bool conservativeCasterVisible(const scene::Frustum& lightFrustum, const scene::Aabb& worldBounds)
{
    for (int axis = 0; axis < 3; ++axis)
    {
        if (!std::isfinite(worldBounds.min[axis]) || !std::isfinite(worldBounds.max[axis]) ||
            worldBounds.min[axis] > worldBounds.max[axis])
        {
            return true;
        }
    }
    for (const glm::vec4& plane : lightFrustum.planes)
    {
        for (int axis = 0; axis < 4; ++axis)
        {
            if (!std::isfinite(plane[axis])) { return true; }
        }
    }
    return scene::intersects(lightFrustum, worldBounds);
}

// Keep contiguous instance spans without moving the shared instance records or changing their IDs.
inline uint32_t appendVisibleCasterCommands(const VkDrawIndexedIndirectCommand& source,
                                            std::span<const scene::Aabb> instanceBounds,
                                            const scene::Frustum& lightFrustum,
                                            std::vector<VkDrawIndexedIndirectCommand>& output)
{
    uint32_t visible = 0;
    VkDrawIndexedIndirectCommand span = source;
    span.instanceCount = 0;
    for (uint32_t i = 0; i < source.instanceCount; ++i)
    {
        const uint32_t instance = source.firstInstance + i;
        const bool keep = instance >= instanceBounds.size() ||
                          conservativeCasterVisible(lightFrustum, instanceBounds[instance]);
        if (keep)
        {
            if (span.instanceCount == 0) { span.firstInstance = instance; }
            ++span.instanceCount;
            ++visible;
        }
        else if (span.instanceCount != 0)
        {
            output.push_back(span);
            span.instanceCount = 0;
        }
    }
    if (span.instanceCount != 0) { output.push_back(span); }
    return visible;
}
```

Walk the original interval `[2, 7)` for the example in the problem. Keep 2,
reject 3: emit `(firstInstance=2, instanceCount=1)`. Keep 4 and 5, reject 6:
emit `(4, 2)`. Both commands retain `indexCount`, `firstIndex` and
`vertexOffset` from `source`; the shader still reads records 2, 4 and 5.
Compacting the records themselves would require updating every other view
that references those records, which this algorithm avoids.

`PrepareDraws` writes the world bound for each uploaded caster beside its
matrix. Build it from `scene::transformBounds(meshRange.bounds,
item.world)` in the same sorted order; do not leave the bounds in input order
while the instance array is sorted. Preserve mirrored transform batching:
opposite handedness remains a separate `DrawRun` with its appropriate front
face. Culling must not merge runs with different material or facing state.

A cascade that starts exactly at the previous split would lose the receiver
band where Chapter 17 blends between maps. Fit its near receiver distance
with the same blend fraction used by shading. `Visibility.h` supplies:

```cpp
inline float cascadeReceiverNear(uint32_t cascade, float cameraNear,
                                  std::span<const float> splits, float blendFraction)
{
    if (cascade == 0 || cascade > splits.size()) { return cameraNear; }
    const float previousNear = cascade == 1 ? 0.0f : splits[cascade - 2];
    const float previousFar = splits[cascade - 1];
    return std::max(cameraNear, previousFar - (previousFar - previousNear) *
                    std::clamp(blendFraction, 0.0f, 1.0f));
}
```

With splits 10 and 40 metres and blend fraction 0.1, cascade 1 starts at 9 m,
not 10 m. A receiver at 9.5 m belongs to its blend band. A naive fit using
`sliceNear = i == 0 ? camera.nearPlane : splits[i - 1]` fits that receiver only
in the earlier map; Chapter 17's current answer already includes the overlap.
A selector using the naive fit can therefore remove a
caster from the next map exactly where the fragment shader blends it in.

Replace **the whole existing** `ShadowMaps::FitCascades` definition with the
following and add the complete `FitCasterVolumes` immediately after it.
Keep Chapter 17's file-scope `cascadeSplits`, `fitTight`, `fitStable`,
`CascadeFit` and `lightUp` support helpers unchanged. The one changed input
to either stable or tight fitting is the receiver's expanded `sliceNear`;
the chosen fit still includes `settings.casterReach` towards the sun:

```cpp
void ShadowMaps::FitCascades(const scene::Camera& camera, const glm::mat4& view, float aspect,
                             const glm::vec3& sunDirection, const ShadowSettings& settings)
{
    const uint32_t  count         = static_cast<uint32_t>(std::clamp(settings.cascadeCount, 1, SHADOW_CASCADE_COUNT));
    const glm::mat4 cameraToWorld = glm::inverse(view);
    const float     tanHalfFovY   = std::tan(camera.verticalFov * 0.5f);
    const float     farDistance   = std::min(settings.maxDistance, camera.farPlane);
    const std::array<float, SHADOW_CASCADE_COUNT> splits =
        cascadeSplits(count, camera.nearPlane, farDistance, settings.splitLambda);

    for (uint32_t i = 0; i < count; ++i)
    {
        const float      sliceNear = cascadeReceiverNear(i, camera.nearPlane, splits, settings.blendFraction);
        const CascadeFit fit       = settings.stabilize
            ? fitStable(cameraToWorld, tanHalfFovY, aspect, sliceNear, splits[i], sunDirection,
                        m_resolution, settings.casterReach)
            : fitTight(cameraToWorld, tanHalfFovY, aspect, sliceNear, splits[i], sunDirection,
                       m_resolution, settings.casterReach);
        m_data.cascadeViewProjection[i] = fit.viewProjection;
        m_data.cascadeSplits[i]         = splits[i];
        m_data.cascadeTexelSize[i]      = fit.texelSize;
    }
    m_data.cascadeCount = count;
    m_data.sunDirection = glm::vec4(sunDirection, 0.0f);
    m_data.maxDistance  = farDistance;
}

ShadowCasterVolumes ShadowMaps::FitCasterVolumes(const scene::Camera& camera, const glm::mat4& view, float aspect,
                                                  std::optional<glm::vec3> sunDirection, const ShadowSettings& settings)
{
    ShadowCasterVolumes volumes;
    if (!settings.enabled || !sunDirection.has_value()) { return volumes; }
    FitCascades(camera, view, aspect, glm::normalize(*sunDirection), settings);
    volumes.count = m_data.cascadeCount;
    for (uint32_t cascade = 0; cascade < volumes.count; ++cascade)
    {
        volumes.frusta[cascade] = scene::frustumFromViewProjection(m_data.cascadeViewProjection[cascade]);
    }
    return volumes;
}
```

This centralizes both collection and rendering on one fit. When shadows are
disabled or there is no sun, the copied `ShadowCasterVolumes` has count zero;
it does not accidentally expose the previous frame's cascades. When active,
its frusta come from exactly the `m_data` matrices returned by the callback
accessor. Fit twice with the same inputs and both results agree; do not use a
camera-only fit for collection and a caster-expanded fit for drawing.

The supplied `ShadowMaps::Record` calls that same method before publishing its
per-frame data. Its complete CPU preparation block is reproduced here so the
call path into the new fit is visible; it is inside `Record`, after checking
the frame slot's mapped buffer and before the first image transition:

```cpp
    // ---- CPU: this frame's ShadowData. The fence for frameIndex has been waited on. ----
    const bool active = settings.enabled && sunDirection.has_value();
    if (active)
    {
        FitCascades(camera, view, aspect, glm::normalize(*sunDirection), settings);
    }
    m_data.normalOffset  = settings.normalOffset;
    m_data.mapResolution = m_resolution;
    m_data.filterRadius  = std::clamp(settings.filterRadius, 0, 3);
    m_data.blendFraction = settings.blendFraction;
    m_data.flags         = (active ? SHADOW_FLAG_ENABLED : 0u)
                         | (active && settings.showCascades ? SHADOW_FLAG_SHOW_CASCADES : 0u);
    std::memcpy(m_dataBuffers[frameIndex].mapped, &m_data, sizeof(m_data));
    const VkResult flushed = vmaFlushAllocation(m_context.allocator, m_dataBuffers[frameIndex].allocation, 0, VK_WHOLE_SIZE);
    if (flushed != VK_SUCCESS)
    {
        return InitializationResult::failure(std::format("Flushing shadow data failed: {}.", string_VkResult(flushed)));
    }

    // No sun: the map stays in SHADER_READ_ONLY_OPTIMAL from the last frame, and flags tell the shader not
    // to read it.
    if (!active) { return InitializationResult::success(); }
```

The supplied remainder of `Record` opens each conventional-depth cascade,
binds its per-frame shadow set, then calls `drawCasters(commandBuffer,
cascade)` and `extraCasters` when present. That first callback is the
`SceneRenderer::RecordShadows` selector below; while it runs,
`CascadeViewProjection(cascade)` reads the very matrix just fitted and
uploaded. A failed required matrix flush returns before either callback.
Keep the copied rendering loop, barriers and attachment lifetime support;
the changed fitting/selection algorithm is completely shown here.

On the current plant route, collection still passes the ordinary full caster
list to `PrepareDraws`; it does not need a new specialized collector. A
later representation can optionally call `PrepareShadowVolumes` before
`PrepareDraws` to collect its own candidates, using the same `m_shadowCamera`,
`frameData.view`, `aspect`, sun and `m_shadowSettings` later passed to
`RecordShadows`. Chapter 40 will supply that representation; do not add
`m_impostors` to complete this lesson. The camera frustum remains unsuitable
as the light's caster volume: the shared fit above includes receiver overlap
and the sunward caster reach.

For assembly, replace the private per-slot declaration in `SceneRenderer.h`
with the following. `ShadowDrawStatistics`, immediately above the renderer
class, holds the candidate count and per-cascade retained instance/command
counts. They describe work, not new object identities:

```cpp
struct ShadowDrawStatistics
{
    uint32_t candidates = 0;
    std::array<uint32_t, SHADOW_CASCADE_COUNT> visible{};
    std::array<uint32_t, SHADOW_CASCADE_COUNT> commands{};
};
```

The renderer's private per-slot declarations are:

```cpp
    struct FrameDraws
    {
        AllocatedBuffer                                     instances;   // set 0 binding 2
        AllocatedBuffer                                     indirect;    // VkDrawIndexedIndirectCommand[capacity]
        uint32_t                                            capacity = 0;   // instances (and commands)
        std::vector<VkDrawIndexedIndirectCommand>           commands;    // the CPU's copy
        std::array<std::vector<DrawRun>, DRAW_LIST_COUNT>   runs;
        std::vector<scene::Aabb>                            bounds;
        AllocatedBuffer                                     shadowIndirect;
        uint32_t                                            shadowCapacity = 0;
        uint32_t                                            uploadedInstances = 0;
        uint64_t                                            uploadedShadowCommands = 0;
        std::vector<VkDrawIndexedIndirectCommand>           shadowCommands;
        std::vector<DrawRun>                                 shadowRuns;
    };
    std::array<FrameDraws, FRAMES_IN_FLIGHT>     m_frameDraws;
    std::array<DrawStatistics, FRAMES_IN_FLIGHT> m_statistics{};
    std::array<ShadowDrawStatistics, FRAMES_IN_FLIGHT> m_shadowStatistics{};
```

`DestroyFrameResources` must destroy each slot's `shadowIndirect` alongside
its instance/indirect buffers; reset its capacities and clear its scratch
vectors. `PrepareDraws` resizes `frame.bounds` to the total scene-plus-caster
record capacity, writes a caster bound at the same `instance` index as that
caster's matrix, and clears per-frame upload/statistics state before building
lists. Empty/default bounds remain conservative. `EnsureShadowCapacity`
allocates space for
`SHADOW_CASCADE_COUNT * capacity` indirect commands after the slot fence wait;
it returns false on allocation failure and leaves the complete, already
prepared caster list available. Declare it privately with return type `bool`.
The complete allocator is:

```cpp
bool SceneRenderer::EnsureShadowCapacity(uint32_t frameIndex, uint32_t commands)
{
    FrameDraws& frame = m_frameDraws[frameIndex];
    if (commands <= frame.shadowCapacity) { return true; }
    const uint32_t capacity = static_cast<uint32_t>(std::min<uint64_t>(
        std::max({ uint64_t(commands), uint64_t(frame.shadowCapacity) * 2, uint64_t(1024) }), UINT32_MAX));
    AllocatedBuffer buffer = createBuffer(m_context,
        VkDeviceSize(capacity) * SHADOW_CASCADE_COUNT * sizeof(VkDrawIndexedIndirectCommand),
        VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT, true);
    if (buffer.buffer == VK_NULL_HANDLE || buffer.mapped == nullptr)
    {
        destroyBuffer(m_context, buffer);
        Log::warning("Could not grow cascade commands; drawing the complete caster list this frame.");
        return false;
    }
    destroyBuffer(m_context, frame.shadowIndirect);
    frame.shadowIndirect = buffer;
    frame.shadowCapacity = capacity;
    return true;
}
```

Split Chapter 19's `RecordBatches` into a range-taking private helper and the
public list-taking wrapper below. Declare the private helper with the same
signature; the implementation is complete for all four existing draw modes:

```cpp
void SceneRenderer::RecordPreparedBatches(VkCommandBuffer commandBuffer,
                                          std::span<const VkDrawIndexedIndirectCommand> commands,
                                          std::span<const DrawRun> runs, VkBuffer indirect, VkDeviceSize offset,
                                          const std::function<void(VkCommandBuffer, const DrawRun&)>& bindRun) const
{
    if (runs.empty()) { return; }

    // Every mesh is in these two buffers (section 4): bound once, for every command.
    BindGeometry(commandBuffer);

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
                const VkDrawIndexedIndirectCommand& command = commands[c];
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
                const VkDrawIndexedIndirectCommand& command = commands[c];
                vkCmdDrawIndexed(commandBuffer, command.indexCount, command.instanceCount, command.firstIndex,
                                 command.vertexOffset, command.firstInstance);
            }
            break;
        case DrawMode::Indirect:
            for (uint32_t c = run.firstCommand; c < end; ++c)
            {
                vkCmdDrawIndexedIndirect(commandBuffer, indirect, offset + VkDeviceSize(c) * stride, 1, stride);
            }
            break;
        case DrawMode::MultiDraw:
            vkCmdDrawIndexedIndirect(commandBuffer, indirect, offset + VkDeviceSize(run.firstCommand) * stride,
                                     run.commandCount, stride);
            break;
        }
    }
}

void SceneRenderer::RecordBatches(VkCommandBuffer commandBuffer, uint32_t frameIndex, DrawList list,
                                  const std::function<void(VkCommandBuffer, const DrawRun&)>& bindRun) const
{
    const FrameDraws& frame = m_frameDraws[frameIndex];
    RecordPreparedBatches(commandBuffer, frame.commands, frame.runs[static_cast<uint32_t>(list)],
                          frame.indirect.buffer, 0, bindRun);
}
```

The complete changed shadow recording function follows; the material-binding
callback is Chapter 17's existing policy:

```cpp
InitializationResult SceneRenderer::RecordShadows(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                                  const scene::Camera& camera, const glm::mat4& view, float aspect,
                                  std::optional<glm::vec3> sunDirection, const ShadowSettings& settings,
                                  const ShadowCasterCallback& extraCasters)
{
    if (frameIndex >= FRAMES_IN_FLIGHT) { return InitializationResult::failure("Recording shadows with an invalid frame slot."); }
    FrameDraws& frame = m_frameDraws[frameIndex];
    ShadowDrawStatistics& statistics = m_shadowStatistics[frameIndex];
    statistics = {};
    frame.uploadedShadowCommands = 0;
    const std::vector<DrawRun>& sourceRuns = frame.runs[static_cast<uint32_t>(DrawList::ShadowCasters)];
    for (const DrawRun& run : sourceRuns)
    {
        for (uint32_t c = run.firstCommand; c < run.firstCommand + run.commandCount; ++c)
        {
            statistics.candidates += frame.commands[c].instanceCount;
        }
    }
    // No descriptor is changed here. The current frame slot's fence protects this indirect buffer.
    const bool compact = settings.cullCasters && settings.enabled && sunDirection.has_value() &&
                         EnsureShadowCapacity(frameIndex, statistics.candidates);
    // Called once per cascade, inside its rendering scope, with set 0 already bound.
    const ShadowCasterCallback drawCasters = [&](VkCommandBuffer cb, uint32_t cascade) {
        const shared::ShadowDrawData push{ .cascade = cascade, .padding0 = 0, .padding1 = 0, .padding2 = 0 };
        const auto bindRun = [&](VkCommandBuffer runCb, const DrawRun& run) {
            const GpuMaterial&     material = m_gpuMaterials[run.material];
            const VkPipelineLayout layout   = m_shadows.CasterLayout(material.cutout);
            vkCmdBindPipeline(runCb, VK_PIPELINE_BIND_POINT_GRAPHICS, m_shadows.CasterPipeline(material.cutout));
            vkCmdSetFrontFace(runCb, FrontFace(run));
            vkCmdSetCullMode(runCb, VK_CULL_MODE_NONE);   // Chapter 17's two-sided shadow policy
            if (material.cutout)   // its fragment shader reads the material: set 1
            {
                vkCmdBindDescriptorSets(runCb, VK_PIPELINE_BIND_POINT_GRAPHICS, layout, 1, 1, &material.set, 0, nullptr);
            }
            vkCmdPushConstants(runCb, layout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
        };
        const auto drawCompleteList = [&] {
            statistics.commands[cascade] = 0;
            statistics.visible[cascade] = statistics.candidates;
            for (const DrawRun& run : sourceRuns) { statistics.commands[cascade] += run.commandCount; }
            RecordBatches(cb, frameIndex, DrawList::ShadowCasters, bindRun);
        };
        if (!compact)
        {
            drawCompleteList();
            return;
        }

        const scene::Frustum lightFrustum = scene::frustumFromViewProjection(m_shadows.CascadeViewProjection(cascade));
        frame.shadowCommands.clear();
        frame.shadowRuns.clear();
        for (const DrawRun& sourceRun : sourceRuns)
        {
            DrawRun selected = sourceRun;
            selected.firstCommand = static_cast<uint32_t>(frame.shadowCommands.size());
            for (uint32_t c = sourceRun.firstCommand; c < sourceRun.firstCommand + sourceRun.commandCount; ++c)
            {
                statistics.visible[cascade] += appendVisibleCasterCommands(frame.commands[c], frame.bounds,
                                                                            lightFrustum, frame.shadowCommands);
            }
            selected.commandCount = static_cast<uint32_t>(frame.shadowCommands.size()) - selected.firstCommand;
            if (selected.commandCount != 0) { frame.shadowRuns.push_back(selected); }
        }
        statistics.commands[cascade] = static_cast<uint32_t>(frame.shadowCommands.size());
        if (frame.shadowCommands.empty()) { return; }
        const VkDeviceSize offset = VkDeviceSize(cascade) * frame.shadowCapacity * sizeof(VkDrawIndexedIndirectCommand);
        std::memcpy(static_cast<std::byte*>(frame.shadowIndirect.mapped) + offset, frame.shadowCommands.data(),
                    frame.shadowCommands.size() * sizeof(VkDrawIndexedIndirectCommand));
        const VkResult flushed = vmaFlushAllocation(m_context.allocator, frame.shadowIndirect.allocation, offset,
                                                    frame.shadowCommands.size() * sizeof(VkDrawIndexedIndirectCommand));
        if (flushed != VK_SUCCESS)
        {
            Log::warning(std::format("Flushing cascade commands failed ({}); drawing the complete caster list.",
                                     string_VkResult(flushed)).c_str());
            drawCompleteList();
            return;
        }
        frame.uploadedShadowCommands += statistics.commands[cascade];
        RecordPreparedBatches(cb, frame.shadowCommands, frame.shadowRuns, frame.shadowIndirect.buffer, offset, bindRun);
    };
    return m_shadows.Record(commandBuffer, frameIndex, m_frameSets[frameIndex], camera, view, aspect,
                     sunDirection, settings, drawCasters, extraCasters);
}
```

`RecordPreparedBatches` accepts command/run spans, an indirect buffer and a
byte offset; it binds the shared geometry, applies each run's callback, and
issues the same Chapter 19 draw mode over those ranges. Each cascade occupies
its own buffer region, so a later CPU copy cannot replace an earlier
cascade's recorded indirect commands. Failure of this optional compaction
upload draws the complete **current** caster list instead. Step 3 distinguishes
that valid fallback from a failed required instance or shadow-matrix upload.

Depth is the other half of the view contract. The complete policy helpers go
in `DepthConvention.h`, including Vulkan and GLM's
`<glm/ext/matrix_clip_space.hpp>`:

```cpp
enum class DepthConvention { Conventional, Reversed };

constexpr float depthClearValue(DepthConvention convention)
{
    return convention == DepthConvention::Reversed ? 0.0f : 1.0f;
}

constexpr VkCompareOp depthCompareOp(DepthConvention convention)
{
    return convention == DepthConvention::Reversed ? VK_COMPARE_OP_GREATER : VK_COMPARE_OP_LESS;
}

constexpr VkResolveModeFlagBits conservativeDepthResolve(VkResolveModeFlags supported, DepthConvention convention)
{
    const auto farthest = convention == DepthConvention::Reversed ? VK_RESOLVE_MODE_MIN_BIT : VK_RESOLVE_MODE_MAX_BIT;
    return (supported & farthest) != 0 ? farthest : VK_RESOLVE_MODE_SAMPLE_ZERO_BIT;
}

inline glm::mat4 depthProjection(float verticalFov, float aspect, float nearPlane, float farPlane,
                                 DepthConvention convention)
{
    glm::mat4 projection = convention == DepthConvention::Reversed
        ? glm::perspectiveRH_ZO(verticalFov, aspect, farPlane, nearPlane)
        : glm::perspectiveRH_ZO(verticalFov, aspect, nearPlane, farPlane);
    projection[1][1] *= -1.0f;
    return projection;
}

// Positive view distance for a finite perspective projection with Vulkan's [0, 1] depth.
inline float viewDistanceFromDepth(float depth, float nearPlane, float farPlane, DepthConvention convention)
{
    const float denominator = convention == DepthConvention::Reversed
        ? nearPlane + depth * (farPlane - nearPlane)
        : farPlane - depth * (farPlane - nearPlane);
    return nearPlane * farPlane / denominator;
}
```

For finite near/far planes, swapping the arguments to `perspectiveRH_ZO`
reverses the mapping. The projection still flips Y for Vulkan. Conventional
near/far map to 0/1 and clear to 1 with `LESS`; reversed near/far map to 1/0
and clear to 0 with `GREATER`. Depth reconstruction must invert the same
mapping. At an MSAA edge, choosing the farthest covered depth means `MAX`
conventionally but `MIN` when reversed; unsupported modes explicitly fall
back to `SAMPLE_ZERO`.

Pass `DepthConvention::Reversed` to Horizon's `SceneRenderer::Initialize`;
other demos keep its conventional default. Use the same convention in
`beginScenePass`, the frame projection and custom camera pipelines. The
mesh pipeline calls `depthCompareOp(m_depth)`. The shadow-map pipeline keeps
`LESS`, clear 1 and its conventional light projection. The present deferred
renderer reports an explicit forward fallback for reversed depth rather
than silently applying conventional reconstruction to it.

**Run checkpoint `ch39-visibility-depth`.** The CPU checkpoint guide supplies
an isolated source export. Its source is
[`RendererConvergenceTests.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/RendererConvergenceTests.cpp),
export target `TutorialConvergence` (the full-repository target is
`TutorialRendererConvergenceTests`). The shorter export name keeps MSBuild's
generated tracking paths within Windows' path limit in nested folders. It checks the numeric examples
above, invalid metadata, sparse span identity, blend overlap, mirrored bounds,
near/far ordering, inverse projection and depth reconstruction. Returning
`true` unconditionally from `conservativeCasterVisible` must fail
`FAIL: cascade rejection`. Using camera visibility must fail
`FAIL: off-camera caster removed by camera visibility`. The production
integration/fallback assertions also live in `TutorialMirrorBatchTests`.
Passing these tests establishes selection/depth contracts, not a visual
judgment of rendered shadows. Keep stationary near/far/low-sun comparisons
as a separate native exit check when a graphics run is appropriate.

</details>

<a id="shared-distance-haze"></a>

### Shared distance haze (supplied, no attempt)

Horizon's own shaders already fade a surface into the sky behind it. Chapter
36, section 11 wrote that haze, and Chapter 37, section 2 moved it into
`HorizonShading.glsl` as `skyColor` and `hazed`, with the distance in each
pass's push constants. From Chapter 41 on, the engine's shaders draw into the
same far view (the grass blades, and the sea's surface on the coast), and a
surface left unhazed there would stand out against hazed ground. So the
haze becomes engine code: one include, and one setting in the frame block,
which the demo writes once a frame. None of it is new mathematics, so this
section supplies it whole and asks nothing of you but to type it.

The frame block grows by 32 bytes at its end, by the append-only rule of the
index's [`FrameData`, whole](../VulkanTutorial.md#framedata-whole): `haze`, a
fallback colour and the distance in metres, and `hazeSky`, whether to read
the sky behind the surface, then padding to the next multiple of 16. Every
offset before them stays where it was. In `Shaders/Include/SharedShaderTypes.h`,
after `padding7`:

```cpp
    /* Renderer convergence: shared distance haze, off for every earlier caller by default. */
    vec4  haze;             /* 368  fallback linear RGB; w metres, <= 0 disables haze */
    uint  hazeSky;          /* 384  nonzero: use the sky environment behind the surface */
    uint  padding8;         /* 388 */
    uint  padding9;         /* 392 */
    uint  padding10;        /* 396 */
```

and two checks beside the others, with the `sizeof` check raised to 400:

```cpp
    static_assert(offsetof(FrameData, haze) == 368, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, hazeSky) == 384, "FrameData alignment drifted.");
```

`makeFrameData` value-initializes the block, so `haze.w` is 0 and the haze
is off in every demo that does not write it. Chapter 51 later appends
`atmosphere` after `padding10`, which makes the block 416 bytes, and Chapter 42
appends the world wind after that, 448.

The include is Chapter 37's two functions, with the cube passed in, because
each shader that includes it declares its own binding, and with two changes.
A distance of 0 or less returns the colour untouched, which is what "off"
means; in Chapter 37 it made every surface all sky. And a direction pointing
straight down has nothing left once it is lifted to the horizon, so it reads
the sky toward −Z instead of normalizing a zero vector. The fade itself is
unchanged: the share of the sky's colour is 1 − exp(−range / w), 63 % at
range w and 95 % at 3w. The new file, `Shaders/Include/DistanceHaze.glsl`:

```glsl
#ifndef PF_DISTANCE_HAZE_GLSL
#define PF_DISTANCE_HAZE_GLSL
#include "AtmosphereSampling.glsl"

vec3 distanceHazeSky(samplerCube environment, vec3 direction, bool skyOn, vec3 fallback)
{
    if (!skyOn) { return fallback; }
    vec3 horizon = vec3(direction.x, max(direction.y, 0.0), direction.z);
    float lengthSquared = dot(horizon, horizon);
    horizon = lengthSquared > 1e-8 ? horizon * inversesqrt(lengthSquared) : vec3(0.0, 0.0, -1.0);
    return textureLod(environment, horizon, 0.0).rgb;
}

vec3 distanceHaze(vec3 color, vec3 directionAway, float range, vec4 haze, bool skyOn, samplerCube environment)
{
    if (atmosphereEnabled()) { return applyAtmosphere(color,directionAway,range); }
    if (haze.w <= 0.0) { return color; }
    vec3 background = distanceHazeSky(environment, directionAway, skyOn, haze.rgb);
    return mix(color, background, 1.0 - exp(-range / haze.w));
}

#endif
```

Two of its lines are Chapter 51's: the `AtmosphereSampling.glsl` include,
and the first line of `distanceHaze`, which hands the whole job to the
physical atmosphere when that is on. Leave both out until then.

`HorizonShading.glsl` keeps its two names, so no Horizon shader changes; their
bodies now call the include, which goes after `Shadows.glsl`:

```glsl
#include "DistanceHaze.glsl"
```

```glsl
// Chapter 36 section 10: the sky in a direction, lifted to the horizon if it points below it (on the open
// sea, that is more sea, about as bright as the horizon). With the engine's sky off, `fallback`: the demo's
// clear color.
vec3 skyColor(vec3 direction, bool skyOn, vec3 fallback)
{
    return distanceHazeSky(skySpecular, direction, skyOn, fallback);
}

// Chapter 36 section 11: haze. A surface `range` metres away along -V (V is unit, toward the eye) fades into
// the sky behind it: the fraction left is exp(-range / hazeDistance). `sky` is TerrainDraw::sky: rgb the
// fallback, w the haze distance.
vec3 hazed(vec3 color, vec3 V, float range, bool skyOn, vec4 sky)
{
    return distanceHaze(color, -V, range, sky, skyOn, skySpecular);
}
```

The engine's mesh shader, `Shaders/Scene/Mesh.frag.glsl`, includes it after
`ImageBasedLighting.glsl`, whose `skySpecular` is set 0's binding 11 (Chapter
24, section 6); level 0 of that cube is the sky itself:

```glsl
#include "ImageBasedLighting.glsl"   // Chapter 24: set 0 bindings 10-12, evaluateAmbientLight
#include "DistanceHaze.glsl"
```

and fades the lit colour last, before the debug views replace it:

```glsl
    color *= cascadeDebugColor(viewDepth);   // Chapter 17: white unless "Show cascades" is on
    color = distanceHaze(color, -V, length(frame.cameraPosition.xyz - worldPosition),
                         frame.haze, frame.hazeSky != 0u, skySpecular);
```

Horizon is the one demo that writes it. In `HorizonDemo::Record`, after
`ambientMode` and before `WriteFrameData`, the same colour and distance its
terrain pushes (Chapter 36, section 11), so the engine's surfaces and
Horizon's own fade alike:

```cpp
    frameData.haze           = glm::vec4(FALLBACK_SKY, m_terrainSettings.hazeDistance);
    frameData.hazeSky        = frame.sky.mode != SkyMode::Off ? 1u : 0u;
```

The complete reference makes the same call in three more places: the
deferred lighting pass (`DeferredLighting.comp.glsl`, after its lights,
reading the cube at its own set's binding 11, since that set keeps set 0's
numbers, Chapter 22, section 6), Chapter 41's grass blades
(`GrassFragmentKernel.glsl`) and the sea's surface
(`SeaSurfaceFragment.glsl`). None is needed for Chapter 40: Horizon draws
forward under reversed depth (step 2), its grass and sea arrive in Chapter
41, and no other demo writes a distance. Add each when your route reaches
it.

**Check.** Step 2's program, `TutorialRendererConvergenceTests`, builds a
frame with `makeFrameData` and fails with
`FAIL: shared haze ABI or disabled defaults` unless `haze` and `hazeSky` are
zero and `FrameData` has the size its layout gives. Because it reads these two
fields, the full-repository target compiles in your own tree only once this
section is typed; run it here, not at the end of step 2. (The exported
`TutorialConvergence` checkpoint already has the fields.) Later chapters keep
appending to the block, so a chapter that adds a field moves that size check
with it: the check guards the layout, it is not a constant.

<a id="convergence-fallible-frames"></a>

### Step 3 — A failed recording must not become a submitted frame

**Prerequisites and files.** Return to Chapter 4's fence lifecycle, Chapter
8's checked uploads and Chapter 9's demo/renderer boundary. Change
[`Demo.h`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Demo.h), each demo override,
[`VulkanRenderer.h/.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/VulkanRenderer.cpp)
and required upload callers such as `SceneRenderer::PrepareDraws`. This
change has a source-wide signature effect, so compile every demo override
present on your route, including Horizon. You do not need to introduce demos
from later chapters merely to update their signatures. No new graphics
abstraction or retry system is required.

<a id="ch39-convergence-fallible-frame"></a>

### Attempt CH39-convergence-fallible-frame: stop at the submission boundary

Suppose an instance buffer is mapped, the CPU has copied this frame's data,
and flushing the allocation fails. Return a diagnostic all the way to the
frame owner. Ensure that the partially recorded frame cannot draw last
frame's instances, submit commands or leave the slot fence reset with no
submission that can signal it.

**Acceptance:** Allocation and flush failures remain failures. Required
preparation publishes no draw records on failure. A demo recording failure
reaches `drawFrame`, closes the ImGui frame, clears capture readiness and
returns `FrameStatus::Failed` without fence reset, submit or present.
Success follows `wait → acquire → pool reset → begin → demo → UI → end →
fence reset → submit → present`.

**Transfer:** Decide whether a failed cascade-command optimization and a
failed shadow-matrix upload have the same policy. Name the complete current
frame data that makes a fallback valid; a stale buffer from yesterday's
successful frame does not qualify.

<details>
<summary>Hint 1: the idea</summary>

A helper returning failure is useful only if its caller changes the
submission decision. Recording command bytes and submitting GPU work are
different commitments. Keep the fence signaled while recording may fail.

</details>

<details>
<summary>Hint 2: the state and lifetime</summary>

At preparation entry, clear published counts/runs. Host-visible does not mean
host-coherent: check `vmaFlushAllocation`. A completed required upload is the
point where counts become valid. After acquiring a swapchain image, an
aborted frame also has WSI/semaphore state; silently retrying needs more
recovery logic than returning false from a draw helper.

</details>

<details>
<summary>Hint 3: a concrete route</summary>

Keep Chapters 4–10's result-bearing `Demo::Record`, frame boundary and
Chapter 39, section 9's checked understory writer. Audit each intermediate
caller added by convergence. Reset the fence only after successful recording
and immediately before submission. Failure after acquisition is terminal in this application;
ordinary frame retry would need an explicit WSI recovery policy.

</details>

<details>
<summary>Worked solution: make publication and submission explicit</summary>

Keep the existing `InitializationResult` error carrier for per-frame errors.
The `Demo.h` declaration introduced in Chapter 9 remains:

```cpp
virtual InitializationResult Record(const RecordContext& frame) = 0;
```

Audit every override's header/definition. Successful paths return
`InitializationResult::success()` only after all required work is recorded;
required writers such as `WriteFrameData`, `WriteLights`, `PrepareDraws`,
`RecordShadows` and Chapter 39, section 9's `Understory::RecordCompute`
already return checked results; preserve those checks through convergence.
For example, this is Horizon's exact draw-list call after collecting camera
items and the independently collected casters:

```cpp
if (auto result = m_sceneRenderer.PrepareDraws(frame.frameIndex, m_draws, m_casters); !result) { return result; }
```

Do not merely add a success return at the end while leaving a failed helper
ignored in the middle. Preserve intentional complete alternatives, such as
the USD viewer's clear-only frame when no scene is loaded.

`PrepareDraws` clears `commands`, `bounds`, all runs and published counts on
entry, checks slot/capacity/mapping before writing, and constructs this frame's
instances and commands as in Chapter 19. Preserve its checked flush tail
when adding the bounds and visibility data. `instance` is the number of records actually written;
publication (`uploadedInstances`) follows both successful flushes:

```cpp
if (instance != 0)
{
    const VkResult instancesFlushed = vmaFlushAllocation(m_context.allocator, frame.instances.allocation, 0, VK_WHOLE_SIZE);
    const VkResult commandsFlushed = instancesFlushed == VK_SUCCESS
        ? vmaFlushAllocation(m_context.allocator, frame.indirect.allocation, 0, VK_WHOLE_SIZE) : instancesFlushed;
    if (commandsFlushed != VK_SUCCESS)
    {
        frame.commands.clear();
        for (auto& runs : frame.runs) { runs.clear(); }
        return InitializationResult::failure(std::format("Flushing scene instance/command records failed: {}.", string_VkResult(commandsFlushed)));
    }
}
frame.uploadedInstances = instance;
```

The per-frame camera/light, shadow-matrix and understory writers present on
this route use the same checked-write rule. Their allocation and flush
failures are required errors. Chapters 25–27 already apply it to
the grass parameter/tile writers. The assembled reference additionally
checks the later impostor writers; those are not a prerequisite to construct
the current Chapter 39 checkpoint. By contrast, step 2's failed compacted
indirect upload can use the already uploaded full **current** list; it logs
the failed optimization and succeeds through that complete alternative.
On the path-tracer route, Chapter 33's TLAS setup upload follows the checked
rule too and releases its temporary buffer on failure; it is absent on the
shorter forest route. These are concrete audited paths, not a universal
Vulkan recovery claim.

Preserve Chapter 5's `InitializationResult` return from the private
`VulkanRenderer::recordFrame`, including checked `vkBeginCommandBuffer` and
`vkEndCommandBuffer`. Its demo call still propagates the result before the
composite and ImGui recording:

```cpp
if (m_demo != nullptr)
{
    const auto recorded = m_demo->Record({
        .commandBuffer = commandBuffer,
        .frameIndex    = m_frameIndex,
        .targets       = targets,
        .sky           = m_skySettings,
    });
    if (!recorded) { return recorded; }
}
```

Keep Chapter 9's existing no-demo clear in the `else` branch. On successful
end-recording return success. On begin/end failure return a descriptive
failure instead of continuing. A return from a demo can leave a rendering
scope open, so the failed command buffer is discarded, not submitted or
continued with an engine composite.

In `drawFrame`, preserve the existing guarded UI cleanup and capture
invalidation on every failure. This lambda belongs before any early return:

```cpp
const auto failFrame = [&](const char* message)
{
    Log::error(message);
    m_debugPanels.discardFrame();
    m_sceneCaptureReady = false;
    m_uiCaptureReady = false;
    return FrameStatus::Failed;
};
```

Keep the slot-fence wait and image acquisition before command recording.
Preserve the late fence reset in the complete critical section below.
It belongs **after successful acquisition**, before Chapter 4's unchanged
submit-info construction. The CPU timing lines in production may surround
`recordFrame`; they do not alter the order.

```cpp
if (vkResetCommandPool(m_device, frame.commandPool, 0) != VK_SUCCESS)
{
    return failFrame("Resetting the frame command pool failed.");
}
const auto recorded = recordFrame(frame.commandBuffer, imageIndex, request);
if (!recorded)
{
    (void)vkResetCommandPool(m_device, frame.commandPool, 0);
    return failFrame(recorded.message());
}
if (vkResetFences(m_device, 1, &frame.inFlightFence) != VK_SUCCESS)
{
    return failFrame("Resetting the frame fence failed.");
}
```

Then check `vkQueueSubmit2` before publishing capture readiness or advancing
submission accounting. A submission failure after fence reset is fatal too;
never enter another slot wait as though work had been submitted. Presentation
errors happen after a real submission and must preserve that accounting.
Acquire-out-of-date still closes the UI and recreates/skips without consuming
the fence. Main stops on `FrameStatus::Failed`; shutdown performs the existing
idle/teardown sequence. A retry policy would additionally need to recover the
acquired image, semaphore and any CPU simulation history changed during
recording. This lesson deliberately supplies no such retry claim.

**Run the frame-order check.**
[`FrameRecordingTests.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/FrameRecordingTests.cpp),
target `TutorialFrameRecordingTests`, compiles the actual renderer recording
path with controlled Vulkan/WSI calls and real ImGui core. Its ten failure
cases include wait, acquire, command-pool reset, begin, demo, end, fence reset,
present and recreate failures. The success case checks the exact ordered
trace in the acceptance statement. Moving fence reset before `recordFrame`
must fail `failed recording consumed the signaled frame fence`. Removing
`if (!recorded) { return recorded; }` must fail the partial-submission check.
The required-writer coverage is in `TutorialMirrorBatchTests`: failing the
first or second mapped flush must leave no published scene/indirect records,
and a failed required shadow-data upload must emit no caster draws. Normal
coherent-memory hardware is not a negative test for a flush failure. No part
of this mocked checkpoint certifies native acquired-image teardown; the
separate `TutorialFrameFailureGpuTests` target exercises that boundary when
an attended graphics run is appropriate. Full-repository commands follow
step 4.

</details>

<a id="convergence-shared-fft"></a>

### Step 4 (optional) — Shared FFT resources, independent simulations

**Prerequisites and files.** This step requires Chapters 29 and 30, especially
the packed inverse FFT, four borrowed ping-pong images per field, compute
barriers, the FFT push constants and the assemble pass. If you reached plants
through the scene/terrain route without implementing those lessons, continue
to Chapter 40 after step 3 and return here later. This step adds no ocean
physics and is not a forest dependency.

Add [`OceanFft.h/.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/OceanFft.h) in
`VulkanGraphics`. Call it from `OceanDemo.cpp` and `SeaSurface.cpp`, which keep
their own spectrum/animation/foam/images. Regenerate after adding the two
source files. Keep Chapter 29's `Shaders/Ocean/FftStage.comp.glsl` and
`FftParameters`; changing resource ownership must not change its transform.

<a id="ch39-convergence-shared-fft"></a>

### Attempt CH39-convergence-shared-fft: share a mechanism without merging state

Ocean runs one FFT field. Sea runs independent cascade fields using the same
shader. Extract the descriptor/pipeline lifetime and row/column dispatch
schedule into one owner. Predict which ping-pong copy contains the final
output and where a barrier belongs when several fields run through a stage.

**Acceptance:** A side of 8 produces six stages, directions `0,0,0,1,1,1`,
stage numbers `0,1,2,0,1,2`, sources `0,1,0,1,0,1` and final output copy 0.
Every supported power of two agrees. Invalid sizes, missing fields, null or
aliased image handles and missing device handles are rejected. Teardown
releases FFT descriptors/pipeline before a simulation destroys borrowed
images; spectrum and foam state remain in their simulations.

**Transfer:** Add another independent field with the same side length. Name
which descriptors grow and which physical parameters must remain outside
`OceanFft`. Explain why one shared mutable ocean simulation would violate
the ownership boundary.

<details>
<summary>Hint 1: the idea</summary>

The repeated mechanism is a resource lifetime and dispatch plan. Physical
state is an input owned elsewhere. Borrowing an image does not make the FFT
responsible for creating, resizing or destroying that image.

</details>

<details>
<summary>Hint 2: the data and schedule</summary>

For side `2^k`, execute `k` stages in each of two directions: `2k` passes is
always even. Source alternates every pass, including across the direction
boundary. Dispatch every independent field for one stage, then insert a
shared read/write barrier before any field's next stage.

</details>

<details>
<summary>Hint 3: a concrete route</summary>

Prepare two descriptor sets per field: A/B source copy 0 to copy 1, and copy 1
to copy 0. Bind the selected set using `2 * field + source`. Validate distinct
images across all fields before creating resources. After `Record`, restore
the simulation's own descriptor set and push constants before its assemble
pass, because FFT recording binds a different layout.

</details>

<details>
<summary>Worked solution: a stage-major owner with borrowed image pairs</summary>

For `N = 8`, `k = log2(N) = 3`. The three row passes move `0→1`, `1→0`,
`0→1`; the three column passes continue `1→0`, `0→1`, `1→0`. Resetting source
to zero at the direction boundary would read the wrong row result whenever
`k` is odd. Derive source from the whole plan's pass number instead.

The following is the complete header, after the project file banner. The
borrowed-image contract states format, shape, layout and lifetime; raw Vulkan
handles alone do not encode all of these properties. `Initialize` checks the
side/device limits and nonnull/distinct handles it can inspect; the caller
must still supply the promised image format, extent and layout.

```cpp
#pragma once

#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include <array>
#include <bit>
#include <cstdint>
#include <span>
#include <vector>

namespace pf::vulkan_graphics {

inline bool validOceanFftSize(uint32_t side)
{
    return side >= 2 && side <= 16384 && std::has_single_bit(side);
}

struct OceanFftStage
{
    uint32_t stage;
    uint32_t direction;
    uint32_t source;
};

inline std::vector<OceanFftStage> oceanFftPlan(uint32_t side)
{
    std::vector<OceanFftStage> plan;
    if (!validOceanFftSize(side)) { return plan; }
    const uint32_t stages = std::bit_width(side) - 1;
    for (uint32_t direction = 0; direction < 2; ++direction)
    {
        for (uint32_t stage = 0; stage < stages; ++stage)
        {
            plan.push_back({ stage, direction, static_cast<uint32_t>(plan.size()) & 1u });
        }
    }
    return plan;
}

struct OceanFftField
{
    // Four distinct RGBA32F storage images, square `side`, in GENERAL. The caller
    // owns their images/views and keeps them alive until Shutdown after device idle.
    const std::array<AllocatedImage, 2>* a = nullptr;
    const std::array<AllocatedImage, 2>* b = nullptr;
};

class OceanFft
{
public:
    OceanFft() = default;
    OceanFft(const OceanFft&) = delete;
    OceanFft& operator=(const OceanFft&) = delete;

    InitializationResult Initialize(const VulkanContext& context, VkPipelineCache cache, uint32_t side,
                                    std::span<const OceanFftField> fields);
    // Input in copy 0 must already be compute-visible. Output returns to copy 0,
    // compute-visible. Fields run independently within a stage, followed by one
    // shared read/write barrier before the next stage and final consumer.
    void Record(VkCommandBuffer commandBuffer) const;
    void Shutdown();
    bool Ready() const { return m_pipeline != VK_NULL_HANDLE; }

private:
    VulkanContext m_context;
    VkDescriptorSetLayout m_setLayout = VK_NULL_HANDLE;
    VkDescriptorPool m_pool = VK_NULL_HANDLE;
    VkPipelineLayout m_layout = VK_NULL_HANDLE;
    VkPipeline m_pipeline = VK_NULL_HANDLE;
    std::vector<VkDescriptorSet> m_sets;
    std::vector<OceanFftStage> m_plan;
    uint32_t m_groups = 0;
};

} // namespace pf::vulkan_graphics
```

The complete implementation follows. Descriptor creation and pipeline creation
reuse Chapter 20's checked helpers; the shader and its butterfly mathematics
are Chapter 29's supplied mechanism. This extraction changes the owner and
schedule, not those helpers or the shader. A failed partial initialization is
safe to pass to `Shutdown`, as required by the demo teardown contract.

```cpp
#include "PillowFort/VulkanGraphics/OceanFft.h"

#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"
#include "PillowFort/VulkanGraphics/VulkanBarriers.h"
#include "Ocean/OceanTypes.h"

#include <algorithm>
#include <cassert>

namespace pf::vulkan_graphics {

InitializationResult OceanFft::Initialize(const VulkanContext& context, VkPipelineCache cache, uint32_t side,
                                          std::span<const OceanFftField> fields)
{
    if (m_context.device != VK_NULL_HANDLE || !validOceanFftSize(side) || fields.empty() || fields.size() > 32
        || context.device == VK_NULL_HANDLE || context.physicalDevice == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Invalid FFT configuration: use 1-32 fields, a power-of-two side from 2 to 16384, and a live device.");
    }
    std::vector<VkImage> images;
    for (const OceanFftField& field : fields)
    {
        if (field.a == nullptr || field.b == nullptr)
        {
            return InitializationResult::failure("An FFT field must borrow two ping-pong image pairs.");
        }
        for (const auto* pair : { field.a, field.b })
        {
            for (const AllocatedImage& image : *pair)
            {
                if (image.image == VK_NULL_HANDLE || image.view == VK_NULL_HANDLE
                    || std::find(images.begin(), images.end(), image.image) != images.end())
                {
                    return InitializationResult::failure("FFT fields must borrow distinct non-null storage images, including across cascades.");
                }
                images.push_back(image.image);
            }
        }
    }
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(context.physicalDevice, &properties);
    if (side > properties.limits.maxImageDimension2D || properties.limits.maxPerStageDescriptorStorageImages < 4)
    {
        return InitializationResult::failure("The device does not support the FFT's storage-image size or bindings.");
    }
    m_context = context;
    m_plan = oceanFftPlan(side);
    m_groups = groupCount(side, OCEAN_GROUP_SIZE);
    const std::array<VkDescriptorSetLayoutBinding, 4> bindings{ {
        { 0, VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr },
        { 1, VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr },
        { 2, VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr },
        { 3, VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr },
    } };
    m_sets.resize(fields.size() * 2);
    if (!createDescriptorSets(m_context, bindings, m_setLayout, m_pool, m_sets))
    {
        return InitializationResult::failure("Creating shared FFT descriptor resources failed.");
    }
    for (uint32_t field = 0; field < fields.size(); ++field)
    {
        for (uint32_t source = 0; source < 2; ++source)
        {
            const std::array<VkDescriptorImageInfo, 4> dispatchImages{ {
                { VK_NULL_HANDLE, (*fields[field].a)[source].view, VK_IMAGE_LAYOUT_GENERAL },
                { VK_NULL_HANDLE, (*fields[field].b)[source].view, VK_IMAGE_LAYOUT_GENERAL },
                { VK_NULL_HANDLE, (*fields[field].a)[1 - source].view, VK_IMAGE_LAYOUT_GENERAL },
                { VK_NULL_HANDLE, (*fields[field].b)[1 - source].view, VK_IMAGE_LAYOUT_GENERAL },
            } };
            std::array<VkWriteDescriptorSet, 4> writes{};
            for (uint32_t binding = 0; binding < 4; ++binding)
            {
                writes[binding] = {
                    .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                    .dstSet = m_sets[2 * field + source],
                    .dstBinding = binding,
                    .descriptorCount = 1,
                    .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
                    .pImageInfo = &dispatchImages[binding],
                };
            }
            vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
        }
    }
    const VkPushConstantRange push{ VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(demos::ocean::FftParameters) };
    const VkPipelineLayoutCreateInfo layout{
        .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount = 1,
        .pSetLayouts = &m_setLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges = &push,
    };
    VkPipelineLayout pipelineLayout = VK_NULL_HANDLE;
    if (vkCreatePipelineLayout(m_context.device, &layout, nullptr, &pipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("Creating the shared FFT pipeline layout failed.");
    }
    m_layout = pipelineLayout;
    m_pipeline = createComputePipeline(m_context.device, cache, "Ocean/FftStage.comp.spv", m_layout);
    return Ready() ? InitializationResult::success() : InitializationResult::failure("Creating the shared FFT pipeline failed.");
}

void OceanFft::Record(VkCommandBuffer commandBuffer) const
{
    assert(Ready() && commandBuffer != VK_NULL_HANDLE);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_pipeline);
    for (const OceanFftStage& stage : m_plan)
    {
        const demos::ocean::FftParameters constants{ stage.stage, stage.direction };
        vkCmdPushConstants(commandBuffer, m_layout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(constants), &constants);
        for (size_t field = 0; field < m_sets.size() / 2; ++field)
        {
            const VkDescriptorSet set = m_sets[2 * field + stage.source];
            vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_layout, 0, 1, &set, 0, nullptr);
            vkCmdDispatch(commandBuffer, m_groups, m_groups, 1);
        }
        computeToComputeBarrier(commandBuffer);
    }
}

void OceanFft::Shutdown()
{
    if (m_context.device == VK_NULL_HANDLE) { return; }
    vkDestroyPipeline(m_context.device, m_pipeline, nullptr);
    vkDestroyPipelineLayout(m_context.device, m_layout, nullptr);
    vkDestroyDescriptorPool(m_context.device, m_pool, nullptr);
    vkDestroyDescriptorSetLayout(m_context.device, m_setLayout, nullptr);
    m_context = {};
    m_setLayout = VK_NULL_HANDLE;
    m_pool = VK_NULL_HANDLE;
    m_layout = VK_NULL_HANDLE;
    m_pipeline = VK_NULL_HANDLE;
    std::vector<VkDescriptorSet>{}.swap(m_sets);   // release the old allocation, not only its elements
    std::vector<OceanFftStage>{}.swap(m_plan);
    m_groups = 0;
}

} // namespace pf::vulkan_graphics
```

During `OceanDemo::Setup`, after `CreateImages`, initialize one field:

```cpp
const OceanFftField field{ &m_spectrumA, &m_spectrumB };
if (auto result = m_fft.Initialize(m_context.vulkan, m_context.pipelineCache,
                                  FFT_SIZE, { &field, 1 }); !result)
{
    return result;
}
```

`SeaSurface::Initialize` builds `std::array<OceanFftField, SEA_CASCADE_COUNT>`
from each cascade's image pairs and passes the array to the same initializer.
Remove the duplicate FFT descriptor/pipeline ownership from both consumers;
keep their other compute resources. After their animate pass, make its writes
compute-visible, call `m_fft.Record(commandBuffer)`, then restore the
simulation's own set and push constants before assemble. Ocean's complete
changed handoff is:

```cpp
computeToComputeBarrier(commandBuffer);
m_fft.Record(commandBuffer);
vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_oceanLayout,
                        0, 1, &m_oceanSet, 0, nullptr);
vkCmdPushConstants(commandBuffer, m_oceanLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                   0, sizeof(parameters), &parameters);
vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_assemblePipeline);
vkCmdDispatch(commandBuffer, groups, groups, 1);
computeToComputeBarrier(commandBuffer);
```

The owner ends each FFT stage with a compute barrier, including the final one,
so output copy 0 is visible to assemble. Independent fields do not require a
barrier between their dispatches within the same stage: they borrow distinct
images. Teardown, after device idle, calls `m_fft.Shutdown()` before destroying
any spectrum images. The owner's destroy functions release only resources it
created; the four images per field remain the simulation's responsibility.

**Run the FFT check.**
[`OceanFftTests.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/OceanFftTests.cpp), target
`TutorialOceanFftTests`, checks the production plan for every supported power
of two and rejects invalid initialization without launching Vulkan. Resetting
source to `stage & 1` must fail its ping-pong assertion for odd stage counts.
The CPU plan check does not execute the FFT shader, test real descriptor
allocation or measure the dispatch barrier on a GPU. Chapter 29's test wave
and Chapter 30's independent-cascade visual/numerical exits remain the native
integration checks. Keep the ownership extraction separate from changes to
spectrum normalization, foam, or water appearance.

</details>

### Run the four CPU contracts

The four targets are the checks the steps above name. They are optional
projects: generate them, build them, and run each from the repository root,
in PowerShell. No command here launches a graphics window, and a program that
finds a broken contract says which and exits with a nonzero code:

```powershell
.\GenerateProjects.bat --tutorial-tests
if ($LASTEXITCODE -ne 0) { throw 'Project generation failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:TutorialMirrorBatchTests,TutorialRendererConvergenceTests,TutorialFrameRecordingTests,TutorialOceanFftTests
if ($LASTEXITCODE -ne 0) { throw 'The CPU contract build failed.' }
foreach ($target in 'TutorialMirrorBatchTests', 'TutorialRendererConvergenceTests', 'TutorialFrameRecordingTests', 'TutorialOceanFftTests')
{
    & ".\Build\Artifacts\Debug\$target\$target.exe"
    if ($LASTEXITCODE -ne 0) { throw "$target failed." }
}
```

The build is the guide's usual one with a target list, one worker as
[Building with Premake](../Premake.md) explains. The memory guards the
reference's own runs used are a convenience for a busy machine, not part of
the check; [Working a prepared exercise](ReferenceSolutions.md#working-a-prepared-exercise)
explains them with the runner's other flags.

**Optional: the visibility and depth checkpoint on its own.** The
checkpoint runner snapshots the actual source into a separate editable tree,
generates its own project, and builds and runs the production CPU oracle for
step 2. It is a complete reference checkpoint, without a declared starter
omission. The runner needs PowerShell 7, and its Generate, Build and Check
phases carry the memory and busy-machine guards that
[Working a prepared exercise](ReferenceSolutions.md#working-a-prepared-exercise)
explains. A refused phase says why; run it again once the machine is free:

```powershell
$runner = '.\Tests\TutorialHarness\Checkpoints\Invoke-SourceCheckpoint.ps1'
& $runner -Checkpoint ch39-visibility-depth -Action Prepare
& $runner -Checkpoint ch39-visibility-depth -Action Generate
& $runner -Checkpoint ch39-visibility-depth -Action Build
& $runner -Checkpoint ch39-visibility-depth -Action Check
```

The [CPU checkpoint guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md)
explains content identities, protected acceptance oracles, sealing/export and
working on a new destination without overwriting your previous edit. This
export covers the selection/depth algorithm, not the whole Horizon renderer.

Regenerate whenever files are added, removed or renamed. A clean compile
checks signatures and headers; the fault-controlled programs check CPU
publication and call ordering. Neither replaces the original plant visual
exits, nor establishes that every historical chapter boundary was
independently built. The complete application must also compile after the
source-wide `Demo::Record` signature change; keep that separate from these
bounded CPU contracts and any later attended graphics run.

**Handoff to Chapter 40.** Save a checkpoint after the first three convergence
steps. A tree's meshes now have one owner; its camera and shadow representations
can have separate lists without changing identity; and a failed required
preparation cannot become a submitted partial frame. Chapter 40 can build on
those three contracts. The optional FFT extraction serves the ocean route
independently. Preserve [Chapter 39's plant exit checks](39-Plants.md#exit-check);
none is replaced by passing a CPU test or by accepting a newer assembled
reference. Tighter caster volumes than these per-cascade lists can come
later: measure the conservative light volumes before reducing their reach,
because the camera frustum is not a safe substitute for the light's caster
volume.

Next: [40 - Forests to the Horizon](40-Forests-To-The-Horizon.md)
