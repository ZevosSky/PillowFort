# 08 — Resources, Memory, and Descriptors

**Goal:** get arbitrary data from C++ into a shader, and get a shader's output
back onto the screen. Every later demo is built on this chapter.

**ROADMAP:** step 9.

**Module:** `VulkanGraphics`, namespace `pf::vulkan_graphics`.

**Prerequisites:**

- Chapter 03 section 2, "What sRGB is, and the decision it forces": the sRGB
  curve, why math on light happens on linear values, and why the swapchain has
  been `_SRGB` until now.
- Chapter 04 section 5: the three questions every barrier answers,
  `transitionImage`, and the cookbook's two "Offscreen target" rows.
- Chapter 05 section 1: `recordFrame`, its rendering scope, and its load op.
- Chapter 06 section 1 (the shader glob, and the `-I` for `Shaders/Include`),
  section 2 (the fullscreen vertex shader), and section 8
  (`GraphicsPipelineDesc` and `createGraphicsPipeline`).
- Chapter 07 section 9: `ShaderParameters` and the panel that edits it.

This is the chapter to slow down on. Every chapter after it assumes all of it.

### What `VulkanRenderer` gains

This chapter adds more to the renderer than any other, and every addition needs
a matching line in `shutdown` or Chapter 02's "no leaked objects" check stops
passing. Here is all of it first, each line tagged with the section that
explains it, so you can see where each section's code lands:

```cpp
// Added to VulkanRenderer (Chapter 04's class map).
public:
    // Until Chapter 09 gives the triangle, and these, a demo of their own.
    ShaderParameters& triangleParameters() { return m_triangleParameters; }   // section 5

private:
    InitializationResult createSceneTarget(VkExtent2D extent);   // section 4
    void                 destroySceneTarget();                   // section 4
    InitializationResult createCompositeObjects();               // section 6: set layout, pool, set, layout, pipeline
    void                 writeCompositeSet();                    // section 6, one binding

VulkanContext         m_context;                      // sections 2 and 7: borrowed handles, the allocator
VkSampler             m_linearClampSampler = VK_NULL_HANDLE;   // section 3
VkImage               m_sceneImage      = VK_NULL_HANDLE;      // section 4
VmaAllocation         m_sceneAllocation = VK_NULL_HANDLE;
VkImageView           m_sceneView       = VK_NULL_HANDLE;
VkDescriptorSetLayout m_compositeSetLayout = VK_NULL_HANDLE;   // section 6
VkDescriptorPool      m_descriptorPool     = VK_NULL_HANDLE;   // section 6, frees its sets with it
VkDescriptorSet       m_compositeSet       = VK_NULL_HANDLE;
VkPipelineLayout      m_compositeLayout    = VK_NULL_HANDLE;
VkPipeline            m_compositePipeline  = VK_NULL_HANDLE;
ShaderParameters      m_triangleParameters;           // section 5
```

**`initialize`** creates them in that order, after the swapchain and before the
debug panels:

1. `vmaCreateAllocator`, right after the device (section 7).
2. The rest of `m_context`, the immediate pool and fence, and the sampler
   (sections 2 and 3).
3. `createSceneTarget(m_swapchain.extent())` (section 4).
4. `createCompositeObjects()` (section 6), beside Chapter 06's
   `createTrianglePipeline()` — whose layout gains section 5's push-constant
   range, and whose `colorFormat` becomes the scene format (section 4).

**`shutdown`**, after `vkDeviceWaitIdle` and the debug panels and before the
frame resources and swapchain, is the reverse: pipelines, then pipeline
layouts, then `vkDestroyDescriptorPool` (which frees every set allocated from
it), then set layouts, then `destroySceneTarget()`, the sampler,
`immediateFence`, and `immediatePool`, and **last**
`vmaDestroyAllocator(m_context.allocator)`. That last call checks that every
VMA allocation is gone — a second leak check for free — and it checks with
`assert`, so a leak is a modal assertion dialog in Debug rather than a log
line. Guard both `destroySceneTarget()` and `vmaDestroyAllocator` with
`if (m_context.allocator != VK_NULL_HANDLE)`: every Vulkan destroy call here
is safe on a null handle after a partial `initialize`, but VMA asserts on a
null allocator.

### Where the free functions live

Sections 1 and 2 are free functions, not members: every demo will create
buffers, and none of them should need the renderer to do it. They take a small
struct of borrowed handles instead.

```cpp
// Source/PillowFort/VulkanGraphics/VulkanResources.h, inside namespace pf::vulkan_graphics
// Borrowed, not owned. VulkanRenderer fills it after initialize(): the first
// three from VulkanInstance, the last two created for immediateSubmit alone.
struct VulkanContext
{
    VkDevice         device         = VK_NULL_HANDLE;
    VkPhysicalDevice physicalDevice = VK_NULL_HANDLE;
    VkQueue          graphicsQueue  = VK_NULL_HANDLE;
    VkCommandPool    immediatePool  = VK_NULL_HANDLE;   // no flags; buffers are freed, not reset
    VkFence          immediateFence = VK_NULL_HANDLE;   // created unsignalled
    // Section 7 adds: VmaAllocator allocator = VK_NULL_HANDLE;
};
```

```text
VulkanResources.cpp
  includes
  static findMemoryType(physicalDevice, typeBits, required)    section 1
  namespace pf::vulkan_graphics {
      createBuffer(...)      declared in VulkanResources.h     section 2
      destroyBuffer(...)                                        section 2
      immediateSubmit(...)                                      section 2
      uploadToBuffer(...)                                       section 2
      uploadToImage(...)                                        section 3
  }
```

`VulkanResources.h` includes `<vulkan/vulkan.h>`, `<functional>` for
`immediateSubmit`'s `std::function`, and from section 7 `<vma/vk_mem_alloc.h>`.
`VulkanResources.cpp` includes `VulkanResources.h`, `Log.h`, `VulkanBarriers.h`
(`uploadToImage`'s `transitionImage`), and `<cstring>` for `std::memcpy`.

Section 7 replaces the allocation inside `createBuffer` with VMA, and the
signatures change with it — an allocator has to come from somewhere, and a
`VkDeviceMemory` is no longer what you hold. Sections 1 and 2 still do it by
hand first: knowing what VMA does for you is the point of seeing it done once.

### Reading order and typing order

The sections run in the order the ideas build on each other: memory by hand
(1-2), images (3), the frame (4), push constants (5), descriptors (6), VMA (7),
and the byte layout that ties C++ to GLSL (8). Typed in that order, the chapter
would have you write `createBuffer` twice and run nothing until the end. So
read sections 1 and 2 closely, but do not type their `findMemoryType`,
`AllocatedBuffer`, `createBuffer`, or `destroyBuffer`: section 7 replaces all
four, and its versions are the ones you keep. Then type:

1. **Section 7**: `VmaImplementation.cpp`, the allocator at the top of
   `initialize`, and VMA's `AllocatedBuffer`, `createBuffer`, and
   `destroyBuffer`.
2. **Section 2's** `immediateSubmit` as shown, and `uploadToBuffer` in the form
   section 7 ends with.
3. **Section 3**: `sceneTargetInfo`; the context's pool, fence, and sampler; and
   `uploadToImage`, with section 7's three changes.
4. **Section 4, then section 6.** Build and run: the checkpoint after section 6
   says what you should see.
5. **Section 5**, which connects the sliders, then **section 8**, which proves
   that the struct they travel in matches its shader.

Section 9 is for Chapter 33's path tracer; skim it.

---

## 1. Memory: heaps, types, and the one function you need

Vulkan exposes memory as **heaps** (physical pools with a size) and **types**
(a heap index plus property flags). A typical discrete GPU reports something
like:

| Type | Heap | Properties | What it is |
| --- | --- | --- | --- |
| 0 | 0 (VRAM, 12 GB) | `DEVICE_LOCAL` | Fast GPU memory. Not CPU-addressable. |
| 1 | 1 (RAM, 32 GB) | `HOST_VISIBLE \| HOST_COHERENT` | Staging. CPU writes, GPU reads over PCIe. |
| 2 | 1 (RAM) | `HOST_VISIBLE \| HOST_COHERENT \| HOST_CACHED` | Readback. Fast for the CPU to *read*. |
| 3 | 0 (VRAM, 256 MB) | `DEVICE_LOCAL \| HOST_VISIBLE \| HOST_COHERENT` | The BAR window. |

Type 3 is worth knowing about. Classically it was a 256 MB window; with
Resizable BAR enabled it can cover all of VRAM. It lets the CPU write straight
into device-local memory with no staging copy, which is exactly right for
**per-frame uniform data** — small, written every frame, read once. Prefer it
for uniform buffers, fall back to type 1 if it is absent or full.

Integrated GPUs vary. Some report a single heap where everything is
device-local and host visible; others, AMD's among them, report a
device-local heap carved out of system memory (its size a firmware setting)
beside an ordinary host heap, with the same kinds of type as the table above.
Your allocator must not assume either shape.

```cpp
// File scope, above the namespace block. Only createBuffer calls it.
static uint32_t findMemoryType(VkPhysicalDevice physicalDevice,
                               uint32_t typeBits,
                               VkMemoryPropertyFlags required)
{
    VkPhysicalDeviceMemoryProperties properties{};
    vkGetPhysicalDeviceMemoryProperties(physicalDevice, &properties);

    for (uint32_t i = 0; i < properties.memoryTypeCount; ++i)
    {
        const bool typeAllowed = (typeBits & (1u << i)) != 0;
        const bool hasProperties =
            (properties.memoryTypes[i].propertyFlags & required) == required;

        if (typeAllowed && hasProperties) { return i; }
    }
    return UINT32_MAX;
}
```

`typeBits` comes from `VkMemoryRequirements::memoryTypeBits` — a bitmask of
which types are legal for *this specific resource*. You must respect it; the
same buffer size with different usage flags can have different legal types.

---

## 2. A buffer, end to end

```cpp
struct AllocatedBuffer
{
    VkBuffer       buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkDeviceSize   size   = 0;
};

AllocatedBuffer createBuffer(VkDevice device,
                             VkPhysicalDevice physicalDevice,
                             VkDeviceSize size,
                             VkBufferUsageFlags usage,
                             VkMemoryPropertyFlags memoryProperties)
{
    AllocatedBuffer result{ .size = size };

    const VkBufferCreateInfo bufferInfo{
        .sType       = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
        .size        = size,
        .usage       = usage,
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
    };
    vkCreateBuffer(device, &bufferInfo, nullptr, &result.buffer);

    VkMemoryRequirements requirements{};
    vkGetBufferMemoryRequirements(device, result.buffer, &requirements);

    const uint32_t memoryType = findMemoryType(physicalDevice,
                                               requirements.memoryTypeBits,
                                               memoryProperties);
    if (memoryType == UINT32_MAX)
    {
        // No memory type satisfies this combination on this device - report it,
        // do not assert. Feeding UINT32_MAX to vkAllocateMemory gets you a
        // validation error pointing at the allocation, not at the reason.
        Log::error("No memory type supports the requested buffer properties.");
        vkDestroyBuffer(device, result.buffer, nullptr);
        return {};
    }

    const VkMemoryAllocateInfo allocateInfo{
        .sType           = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
        .allocationSize  = requirements.size,     // NOT the size you asked for
        .memoryTypeIndex = memoryType,
    };
    vkAllocateMemory(device, &allocateInfo, nullptr, &result.memory);
    vkBindBufferMemory(device, result.buffer, result.memory, 0);

    return result;
}

void destroyBuffer(VkDevice device, AllocatedBuffer& buffer)
{
    vkDestroyBuffer(device, buffer.buffer, nullptr);   // null handles are a valid no-op
    vkFreeMemory(device, buffer.memory, nullptr);
    buffer = {};
}
```

The caller checks `result.buffer != VK_NULL_HANDLE`. That is the whole error
channel here, and it is deliberately thin — section 7 replaces this function
with VMA, which does the same search with a much better fallback policy. The
point of writing it once is knowing what VMA is doing for you, not shipping it.

Three separate objects and three steps: **create the handle, allocate memory,
bind them together.** They are decoupled precisely so one allocation can back
many resources — which is what a real allocator does, and what you are about to
stop doing by hand.

Note `requirements.size`, not `size`. Alignment padding means the driver may
need more than you asked for. Using your own number produces corruption at
buffer boundaries that looks like a shader bug.

### Uploading through a staging buffer

Device-local memory is not mappable, so getting data there is a two-step.
Nothing in this chapter calls `uploadToBuffer`: its first caller is Chapter 33's
path tracer, and Chapter 11 writes a mesh upload of its own on the same
pattern. It is here because it is what `immediateSubmit` is for, and the exit
check runs it once.

```cpp
void uploadToBuffer(VulkanContext& context, AllocatedBuffer& destination,
                    const void* data, VkDeviceSize size)
{
    AllocatedBuffer staging = createBuffer(
        context.device, context.physicalDevice, size,
        VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);

    void* mapped = nullptr;
    vkMapMemory(context.device, staging.memory, 0, size, 0, &mapped);
    std::memcpy(mapped, data, static_cast<size_t>(size));
    vkUnmapMemory(context.device, staging.memory);

    immediateSubmit(context, [&](VkCommandBuffer commandBuffer) {
        const VkBufferCopy region{ .size = size };
        vkCmdCopyBuffer(commandBuffer, staging.buffer, destination.buffer, 1, &region);
    });

    destroyBuffer(context.device, staging);
}
```

`uploadToBuffer` records no barrier after its copy, because only the caller
knows what reads the buffer next: before that first read, the caller records a
barrier from `COPY` / `TRANSFER_WRITE` to the reading stage — Chapter 11's mesh
upload records its own for vertex and index input.

`HOST_COHERENT` means writes are visible to the GPU without explicit flushing.
Without it you must call `vkFlushMappedMemoryRanges`, and the ranges must be
aligned to `nonCoherentAtomSize`. Take coherent memory; the performance
difference is not worth the class of bug.

**Keep long-lived buffers mapped.** `vkMapMemory` is not cheap and there is no
requirement to unmap. For per-frame uniform buffers, map once at creation and
keep the pointer for the object's lifetime.

### `immediateSubmit`

You need one-shot GPU work in a dozen places — uploads, layout transitions,
acceleration structure builds. Write it once:

```cpp
void immediateSubmit(VulkanContext& context,
                     std::function<void(VkCommandBuffer)> record)
{
    const VkCommandBufferAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool        = context.immediatePool,
        .level              = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
        .commandBufferCount = 1,
    };
    VkCommandBuffer commandBuffer = VK_NULL_HANDLE;
    vkAllocateCommandBuffers(context.device, &allocateInfo, &commandBuffer);

    const VkCommandBufferBeginInfo beginInfo{
        .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
    };
    vkBeginCommandBuffer(commandBuffer, &beginInfo);
    record(commandBuffer);
    vkEndCommandBuffer(commandBuffer);

    const VkCommandBufferSubmitInfo commandInfo{
        .sType         = VK_STRUCTURE_TYPE_COMMAND_BUFFER_SUBMIT_INFO,
        .commandBuffer = commandBuffer,
    };
    const VkSubmitInfo2 submitInfo{
        .sType                  = VK_STRUCTURE_TYPE_SUBMIT_INFO_2,
        .commandBufferInfoCount = 1,
        .pCommandBufferInfos    = &commandInfo,
    };

    vkResetFences(context.device, 1, &context.immediateFence);
    vkQueueSubmit2(context.graphicsQueue, 1, &submitInfo, context.immediateFence);
    vkWaitForFences(context.device, 1, &context.immediateFence, VK_TRUE, UINT64_MAX);

    // Give the buffer back. vkResetCommandPool would recycle it for re-recording
    // but would NOT free it, so allocating a fresh one per call and only
    // resetting leaks one command buffer per upload - slowly, and invisibly.
    vkFreeCommandBuffers(context.device, context.immediatePool, 1, &commandBuffer);
}
```

It stalls, which is fine for load-time work and unacceptable per frame. Use a
dedicated pool and fence so it never touches the per-frame ones — the last two
members of `VulkanContext`, created in `initialize` beside section 3's sampler.
The blocks here show `uploadToBuffer` first because it motivates
`immediateSubmit`; in the file `immediateSubmit` comes first, as the layout at
the top of the chapter shows.

---

## 3. Images, and the offscreen HDR target

Images add a format, an extent, mip levels, array layers, tiling, and a layout.
The one you need first is the render target that Chapters 03 and 07 kept
promising:

```cpp
// File scope, above the namespace block in VulkanRenderer.cpp. Section 4's
// createSceneTarget calls it at the window's extent.
static VkImageCreateInfo sceneTargetInfo(VkExtent2D extent)
{
    return VkImageCreateInfo{
        .sType       = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType   = VK_IMAGE_TYPE_2D,
        .format      = VK_FORMAT_R16G16B16A16_SFLOAT,
        .extent      = { extent.width, extent.height, 1 },
        .mipLevels   = 1,
        .arrayLayers = 1,
        .samples     = VK_SAMPLE_COUNT_1_BIT,
        .tiling      = VK_IMAGE_TILING_OPTIMAL,
        .usage       = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT   // draw into it
                     | VK_IMAGE_USAGE_SAMPLED_BIT            // the composite pass reads it
                     | VK_IMAGE_USAGE_STORAGE_BIT            // compute writes it (Ch. 20/33)
                     | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,      // or blit it directly
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
}
```

On format choice:

| Format | Bytes/px | Use |
| --- | --- | --- |
| `R16G16B16A16_SFLOAT` | 8 | The scene target. HDR, high dynamic range: values above 1.0 are allowed, and Chapter 16 compresses them for the screen. Half float is plenty for that. |
| `R32G32B32A32_SFLOAT` | 16 | Path tracer accumulation (Chapter 33). Summing thousands of samples in half float loses the low-order bits, and the image stops converging. |
| `B8G8R8A8_UNORM` | 4 | The swapchain image, from section 4 on. |

`initialLayout` must be `UNDEFINED` or `PREINITIALIZED`, and `PREINITIALIZED`
only applies to linear tiling. Always start `UNDEFINED` and transition.

**Check `STORAGE_BIT` support before requesting it.**
`vkGetPhysicalDeviceFormatProperties` tells you whether a format supports
`STORAGE_IMAGE_BIT` in `optimalTilingFeatures`. `R16G16B16A16_SFLOAT` is widely
supported for storage; some formats are not, and the failure is at image
creation, far from the shader that motivated it.

### Samplers

A sampler says *how* a shader reads an image. It is an object of its own, not
part of any image, so one sampler serves every image that wants the same
reading. Its fields:

- **`magFilter` and `minFilter`** — how texels are blended when the image is
  drawn larger (`mag`) or smaller (`min`) than it is. `LINEAR` blends the
  nearest four texels; `NEAREST` takes one, which looks blocky up close.
- **`mipmapMode` and `maxLod`** — mip levels are pre-shrunk copies of an
  image, which Chapter 15 makes. `VK_LOD_CLAMP_NONE` lets the sampler use
  every level the image has; an image with one level has nothing else to pick.
- **The three address modes**, one per texture axis — what a coordinate
  outside 0..1 reads. `REPEAT` wraps around, for a texture that tiles, like a
  floor. `CLAMP_TO_EDGE` repeats the border texel: right for the composite
  pass's full-screen read (section 4), where wrapping would bleed the left
  edge of the image into the right.

You need very few. The renderer has exactly one, linear-clamp, and later
chapters make their own for their textures. It is created once, together with
section 2's immediate pool and fence and the rest of the context. **This is
`VulkanRenderer::initialize`**, after the swapchain — step 2 of the list at the
top of the chapter:

```cpp
m_context.device         = m_device;
m_context.physicalDevice = m_vulkan.PhysicalDevice();
m_context.graphicsQueue  = m_graphicsQueue;

const VkCommandPoolCreateInfo immediatePoolInfo{
    .sType            = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
    .queueFamilyIndex = m_vulkan.GraphicsFamily(),
};
const VkFenceCreateInfo immediateFenceInfo{
    .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,   // unsignalled: immediateSubmit resets it anyway
};
const VkSamplerCreateInfo linearClampInfo{
    .sType        = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
    .magFilter    = VK_FILTER_LINEAR,
    .minFilter    = VK_FILTER_LINEAR,
    .mipmapMode   = VK_SAMPLER_MIPMAP_MODE_LINEAR,
    .addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
    .addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
    .addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
    .maxLod       = VK_LOD_CLAMP_NONE,
};
if (vkCreateCommandPool(m_device, &immediatePoolInfo, nullptr, &m_context.immediatePool) != VK_SUCCESS ||
    vkCreateFence(m_device, &immediateFenceInfo, nullptr, &m_context.immediateFence) != VK_SUCCESS ||
    vkCreateSampler(m_device, &linearClampInfo, nullptr, &m_linearClampSampler) != VK_SUCCESS)
{
    return InitializationResult::failure("Creating the immediate pool, fence, or sampler failed.");
}
```

The immediate pool has no flags: `immediateSubmit` frees its one command
buffer after every use rather than resetting it.

### Uploading pixels into an image

Same staging idea as `uploadToBuffer`, plus the two layout transitions from
Chapter 04's cookbook on either side of the copy — the image cannot be written
by a copy in `UNDEFINED`, and cannot be sampled in `TRANSFER_DST_OPTIMAL`. Like
`uploadToBuffer`, it is written now and first called later, by Chapter 23's
sky:

```cpp
void uploadToImage(VulkanContext& context, VkImage image, VkExtent2D extent,
                   const void* pixels, VkDeviceSize size)
{
    AllocatedBuffer staging = createBuffer(
        context.device, context.physicalDevice, size,
        VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);

    void* mapped = nullptr;
    vkMapMemory(context.device, staging.memory, 0, size, 0, &mapped);
    std::memcpy(mapped, pixels, static_cast<size_t>(size));
    vkUnmapMemory(context.device, staging.memory);

    immediateSubmit(context, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);

        const VkBufferImageCopy region{
            .imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 },
            .imageExtent      = { extent.width, extent.height, 1 },
        };
        vkCmdCopyBufferToImage(commandBuffer, staging.buffer, image,
                               VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &region);

        transitionImage(commandBuffer, image,
                        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    });

    destroyBuffer(context.device, staging);
}
```

The image needs `TRANSFER_DST_BIT | SAMPLED_BIT` usage, and a format that
matches what the pixels *are*: `R8G8B8A8_SRGB` for a color image, `UNORM` for
data — section 4's color-boundary table says why. A zeroed `bufferRowLength`
and `bufferImageHeight` mean "tightly packed", which is what `memcpy` of a plain
pixel array gives you. The final barrier's `FRAGMENT_SHADER` is for a texture a
fragment shader samples; a vertex-shader heightmap wants `VERTEX_SHADER` there.

---

## 4. Getting the offscreen image to the screen

Chapters 03 and 07 both deferred to this section. The frame becomes two passes:
draw the scene into the offscreen image from section 3, then draw one fullscreen
triangle into the swapchain image that samples it and does the sRGB encode —
with ImGui in the same rendering scope, on top.

### The switch Chapter 03 promised

In `chooseSurfaceFormat`, change `preferred` to `VK_FORMAT_B8G8R8A8_UNORM`.
From here on the composite shader encodes, the hardware does not, and ImGui's
colors reach the screen as they were authored. `ImGuiDebugPanelsCreateInfo::colorFormat`
is still `m_swapchain.format()`, which is now UNORM. The triangle pipeline's
`colorFormat` becomes `VK_FORMAT_R16G16B16A16_SFLOAT`, because it now draws
into the offscreen image, and `FrameRequest::clearColor` now clears that image.

### Linear and sRGB

Chapter 03 section 2 explained the curve and the rule: compute in linear, and
encode to sRGB once, at the end. Until now the `_SRGB` swapchain did that one
encode in hardware. From here the engine does it, so the rule becomes part of
the frame's design.

> **Jump:** from here on a color is a number with one of two meanings, linear
> or sRGB-encoded, and nothing in the type says which. Keep in mind that math
> on light happens on linear numbers, that the screen wants encoded ones, and
> that exactly one place in the frame converts the first into the second. When
> a color looks washed out or too dark, ask which of the two a number was, and
> whether something converted it twice or not at all.

Every color in the frame is in one of the two encodings, and each arrow below
is the one place a conversion happens:

```text
 sources ──linear──▶ scene shaders ──linear──▶ R16G16B16A16_SFLOAT scene target
                                                         │
                                           composite: clamp, linear → sRGB
                                                         ▼
 ImGui (already sRGB) ─────────────────────────▶ B8G8R8A8_UNORM swapchain ──▶ display
```

- **Scene math is linear**, and the HDR target stores it linear, with room above
  1.0 for Chapter 16's tone mapping to compress.
- **The composite pass is the only encoder.** The UNORM swapchain stores bytes
  as given, and the display interprets them as sRGB.
- **ImGui bypasses the scene entirely.** Its colors are authored as sRGB bytes,
  its blending is designed to happen on those bytes, and a UNORM target leaves
  both alone — which is the whole reason for the switch.

That leaves the inputs. Every color entering the scene has to arrive linear,
and not every source hands you linear:

| Source | Arrives as | What to do |
| --- | --- | --- |
| Clear color, vertex colors, constants in code | Whatever you wrote | Write linear values: the linear value that displays as sRGB 50% grey is `0.214`, not `0.5` |
| Color textures the scene samples — albedo, photos | sRGB bytes | Create the image as `R8G8B8A8_SRGB`; sampling decodes to linear for free |
| An image shown only through `ImGui::Image` | sRGB bytes | `UNORM` — ImGui works in sRGB bytes end to end, so decoding would darken it |
| Data textures — normals, heights, masks | Raw numbers | `UNORM` or `SFLOAT`; decoding them would corrupt the data |
| A color picked in ImGui (`ColorEdit`) | sRGB, as the swatch shows it | Convert RGB with the inverse curve before use — on the CPU, or `srgbToLinear` in the shader. Alpha is already linear; leave it |

The last row is the easy one to miss: the triangle's `baseColor` from Chapter 07
comes out lighter than its swatch until you convert it (section 5).

### The composite shader

**This is `Shaders/Composite/Composite.frag.glsl`.** It pairs with Chapter 06
section 2's fullscreen vertex shader, which hands it `uv`:

```glsl
// Shaders/Composite/Composite.frag.glsl
#version 450

layout(location = 0) in  vec2 uv;
layout(location = 0) out vec4 outColor;

layout(set = 0, binding = 0) uniform sampler2D sceneImage;

// False only when the surface offered no UNORM format and the swapchain fell
// back to an _SRGB one, whose hardware encode then does the job (the aside below).
layout(constant_id = 0) const bool encodeSrgb = true;

// The exact sRGB curve: Chapter 03's pow(linear, 1/2.2) shape, with a short
// straight segment near 0 so the slope stays finite. Plain pow is off in the darks.
vec3 linearToSrgb(vec3 linear)
{
    vec3 low  = linear * 12.92;
    vec3 high = 1.055 * pow(linear, vec3(1.0 / 2.4)) - 0.055;
    return mix(high, low, lessThanEqual(linear, vec3(0.0031308)));
}

void main()
{
    // No tone mapping yet: clamp and encode, which is what the _SRGB swapchain
    // did for you before. Chapter 16 adds exposure and a tone curve.
    vec3 color = clamp(texture(sceneImage, uv).rgb, 0.0, 1.0);
    outColor   = vec4(encodeSrgb ? linearToSrgb(color) : color, 1.0);
}
```

`mix(a, b, t)` is GLSL's blend of two values: `a + (b − a) × t`, so `t = 0`
gives `a`, `t = 1` gives `b`, and `t = 0.25` a quarter of the way from one to
the other. Given a vector of booleans for `t`, as here, it picks instead, per
component: `b` where the comparison is true, `a` where it is false. That is how
the curve uses its straight segment below 0.0031308 and the power curve above
it, with no `if`.

Because it clamps and encodes the way the hardware did, **the triangle should
look indistinguishable from Chapter 06** — not bit-identical, since the spec
lets the hardware curve differ by a small tolerance, but no difference you can
see. That makes a good check that the new plumbing is right before anything new
is drawn with it.

`sceneImage` is the shader's one input from outside: a single combined image
sampler, bound to the offscreen image's view with section 3's linear-clamp
sampler. Section 6 builds the descriptor set that provides it, and the
pipeline that runs this shader.

### The frame, in `recordFrame`

```cpp
// ---- The scene's part: the triangle today, a demo's Record from Chapter 09. ----
// Into the offscreen image. Its previous reader was last frame's composite
// pass, so this is Chapter 04's "Offscreen target, start of frame" row.
transitionImage(commandBuffer, m_sceneImage,
                VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);

// vkCmdBeginRendering over m_sceneView, LOAD_OP_CLEAR; the triangle; vkCmdEndRendering.

transitionImage(commandBuffer, m_sceneImage,
                VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

// ---- The engine's part: composite and ImGui, into the swapchain image. ----
// The same acquire barrier as Chapter 05.
transitionImage(commandBuffer, m_swapchain.image(imageIndex),
                VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_NONE,
                VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);

// vkCmdBeginRendering over the swapchain view, LOAD_OP_DONT_CARE - the fullscreen
// triangle writes every pixel. Bind the composite pipeline and its set,
// vkCmdDraw(commandBuffer, 3, 1, 0, 0), then m_debugPanels.record(commandBuffer),
// then vkCmdEndRendering.

transitionImage(commandBuffer, m_swapchain.image(imageIndex),
                VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
                VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE);
```

The two rendering scopes are Chapter 05's `recordFrame` twice over, with a
different view and load op each time; they are left as comments so the barriers
— the part that is new — stay readable. Section 6 shows the three calls that
bind and draw the composite.

**The contract between the two halves**, which every later chapter relies on.
Whatever draws the scene receives the scene target in
`SHADER_READ_ONLY_OPTIMAL` — or `UNDEFINED` on the first frame after it is
created — and must hand it back in `SHADER_READ_ONLY_OPTIMAL`, with its writes
made visible to the fragment shader. Everything in between is the scene's
business: the triangle goes through `COLOR_ATTACHMENT_OPTIMAL`, the path
tracer through `GENERAL`. The engine records only the swapchain side. Using
`UNDEFINED` as the scene's first old layout is always correct here, since every
scene rewrites every pixel.

### Following the window

**The offscreen image is sized to the window, so it has to follow the window.**
This is what Chapter 04's `recreateSwapchain` wrapper was for:

```cpp
RecreateResult VulkanRenderer::recreateSwapchain()
{
    const RecreateResult result = m_swapchain.recreate();
    if (result != RecreateResult::Recreated) { return result; }

    // recreate() already ran vkDeviceWaitIdle, so nothing still reads the old
    // image, and rewriting the composite set is safe.
    destroySceneTarget();                                 // view, image, memory
    if (const auto created = createSceneTarget(m_swapchain.extent()); !created)
    {
        Log::error(created.message());
        return RecreateResult::Failed;
    }
    writeCompositeSet();                                  // section 6, one binding
    return RecreateResult::Recreated;
}
```

`createSceneTarget` and `destroySceneTarget` are the scene image, its memory,
and its view. They allocate through VMA, which section 7 introduces — the one
allocation in this chapter written that way from the start, because a
window-sized image recreated on every resize is exactly what a hand-rolled
allocator does badly. The typing order at the top of the chapter has you
create the allocator first.

```cpp
InitializationResult VulkanRenderer::createSceneTarget(VkExtent2D extent)
{
    const VkImageCreateInfo imageInfo = sceneTargetInfo(extent);   // section 3
    const VmaAllocationCreateInfo allocationInfo{
        .flags = VMA_ALLOCATION_CREATE_DEDICATED_MEMORY_BIT,   // big and short-lived: its own block
        .usage = VMA_MEMORY_USAGE_AUTO,
    };
    if (vmaCreateImage(m_context.allocator, &imageInfo, &allocationInfo,
                       &m_sceneImage, &m_sceneAllocation, nullptr) != VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for the scene target.");
    }

    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_sceneImage,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
    };
    if (vkCreateImageView(m_device, &viewInfo, nullptr, &m_sceneView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the scene target.");
    }
    return InitializationResult::success();
}

void VulkanRenderer::destroySceneTarget()
{
    vkDestroyImageView(m_device, m_sceneView, nullptr);   // null is a no-op

    // vmaDestroyImage returns early for a null image too - but only after
    // asserting that the allocator exists, and a partial initialize can leave
    // it null. Unlike Vulkan's destroy functions, VMA's are not null-safe in
    // their first argument.
    if (m_context.allocator != VK_NULL_HANDLE)
    {
        vmaDestroyImage(m_context.allocator, m_sceneImage, m_sceneAllocation);
    }
    m_sceneView       = VK_NULL_HANDLE;
    m_sceneImage      = VK_NULL_HANDLE;
    m_sceneAllocation = VK_NULL_HANDLE;
}
```

`initialize` calls `createSceneTarget` once too. Anything else sized to the
window follows the same path — Chapter 10's depth buffer is created and
destroyed inside these two functions — and Chapter 09 gives demos a hook for
their own.

This is also where your second graphics pipeline appears — the composite one —
which makes it the moment Chapter 06 section 8 describes.

### Aside: a surface with no UNORM format

On the rare surface without `B8G8R8A8_UNORM`, `chooseSurfaceFormat` falls back
to another format in the sRGB color space, and that fallback is an `_SRGB`
format. An encoding shader in front of it would encode twice — the Chapter 07
washout, now on everything. On Windows desktop drivers this does not happen,
but it costs little to handle, and it is the place to meet a tool later
chapters use.

A **specialization constant** is a shader constant whose value is supplied
when the pipeline is built. The driver compiles the shader with that value
fixed and deletes the branch not taken, so one shader source gives several
pipelines. `encodeSrgb` in the composite shader is one: `layout(constant_id = 0)`
names it, and `true` is its value when the pipeline supplies none. The
pipeline is built for one swapchain format anyway, so the decision is made
once, there, from this test:

```cpp
// File scope, above the namespace block. The _SRGB formats a desktop surface offers.
static bool isSrgbFormat(VkFormat format)
{
    return format == VK_FORMAT_B8G8R8A8_SRGB
        || format == VK_FORMAT_R8G8B8A8_SRGB
        || format == VK_FORMAT_A8B8G8R8_SRGB_PACK32;
}
```

Section 6 passes the value when it builds the composite pipeline. On that
fallback ImGui still washes out, because the hardware encodes its bytes too;
the scene, at least, is right, and the renderer logs a warning.

---

## 5. Push constants: the ImGui slider path

For the parameter workbench you want, push constants are the right mechanism.
They are inline in the command buffer, need no descriptor set, no allocation,
and no synchronization — you re-record every frame anyway.

The limit is small. `maxPushConstantsSize` is guaranteed to be at least
**128 bytes** and is exactly 128 on a lot of hardware. Treat 128 as the budget.

```cpp
// Layout
const VkPushConstantRange pushRange{
    .stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
    .offset     = 0,
    .size       = sizeof(ShaderParameters),
};
static_assert(sizeof(ShaderParameters) <= 128, "Push constant budget exceeded.");

const VkPipelineLayoutCreateInfo layoutInfo{
    .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
    .setLayoutCount         = 0,
    .pushConstantRangeCount = 1,
    .pPushConstantRanges    = &pushRange,
};

// Per frame, inside the rendering scope
vkCmdPushConstants(commandBuffer, m_pipelineLayout,
                   VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                   0, sizeof(ShaderParameters), &parameters);
```

```glsl
layout(push_constant) uniform ShaderParametersBlock
{
    float time;
    float amplitude;
    float frequency;
    float padding0;
    vec4  baseColor;
} parameters;
```

**`stageFlags` must match between the range and `vkCmdPushConstants`**, and
must cover every stage that reads the block. A mismatch is a validation error
with a clear message, which is one of the friendlier failure modes in Vulkan.

The triangle's fragment shader has to read the block for any of this to show,
and `baseColor` needs the decode section 4's table asks for.

The decode is not the triangle's. Every shader that takes a color from an ImGui
panel needs the same function — Chapter 09's second demo is the next — and
two copies of a color curve drift apart one constant at a time. So it goes in a
shared include from its first use. Chapter 06 section 1 planned for this:
`shaderCommands` passes `-I` for `Shaders/Include` to every `glslc` call, and
its glob compiles only files named for a stage, so a `Color.glsl` there is
compiled only as part of the shaders that include it:

```glsl
// Shaders/Include/Color.glsl - color-space helpers any shader may include.
#ifndef PF_COLOR_GLSL
#define PF_COLOR_GLSL

// sRGB-encoded to linear: the exact curve, inverse of the composite pass's
// linearToSrgb (Chapter 08 section 4). For colors picked in ImGui, which are
// sRGB as the swatch shows them. Alpha is linear already; pass only rgb.
//
// Only the decode is shared. The encode stays in Composite.frag.glsl, the one
// shader that may use it: a second encoder anywhere else is the double-encode
// bug Chapter 08 section 4 exists to prevent.
vec3 srgbToLinear(vec3 srgb)
{
    vec3 low  = srgb / 12.92;
    vec3 high = pow((srgb + 0.055) / 1.055, vec3(2.4));
    return mix(high, low, lessThanEqual(srgb, vec3(0.04045)));
}

#endif
```

The encode stays out of the shared file on purpose, as its comment says: one
`#include` away from every scene shader is exactly where a second encoder must
never be. The include guard is the C preprocessor's, which `glslc` runs: a
shader that ends up including the file twice, once directly and once through
another header, gets one definition.

The triangle's fragment shader includes it. `glslc` understands `#include` on
its own; the extension line makes the shader say so explicitly, and it is what
`glslangValidator` requires:

```glsl
// Shaders/Triangle/Triangle.frag.glsl, grown from Chapter 06.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "Color.glsl"   // srgbToLinear; Shaders/Include is on glslc's include path

layout(location = 0) in  vec3 fragmentColor;
layout(location = 0) out vec4 outColor;

layout(push_constant) uniform ShaderParametersBlock
{
    float time;
    float amplitude;
    float frequency;
    float padding0;
    vec4  baseColor;
} parameters;

void main()
{
    // baseColor came from an ImGui swatch, so it is sRGB: decode it once, here.
    vec3 base = srgbToLinear(parameters.baseColor.rgb);

    // Moving bands, so every slider visibly does something. At full amplitude
    // the band peaks are exactly baseColor.
    float band = 0.5 + 0.5 * sin(gl_FragCoord.x / 64.0 * parameters.frequency + parameters.time);
    outColor   = vec4(mix(fragmentColor, base, band * parameters.amplitude / 4.0), 1.0);
}
```

The parameters live on the renderer until Chapter 09 section 6 moves them,
with the triangle, into its demo — `ShaderParameters m_triangleParameters` and a public
`ShaderParameters& triangleParameters()` returning it. `main` reaches them
between `beginUiFrame` and `drawFrame` (Chapter 07 section 10), in place of
Chapter 07's local `shaderParameters`:

```cpp
// Source/SandboxGame/Main.cpp, in the frame loop.
vulkan_graphics::ShaderParameters& parameters = renderer.triangleParameters();
drawShaderParameters(parameters);          // ImGui edits the struct (Chapter 07)
parameters.time = elapsedSeconds;
// ...and recordFrame pushes it with vkCmdPushConstants before the triangle's draw.
```

That is the workbench. Everything else is more parameters.

### When 128 bytes is not enough

A camera alone is a `mat4` view-projection (64 bytes) plus position and a few
scalars, and you are already near the limit. At that point:

- Put the camera in a **uniform buffer**, one per frame in flight, mapped
  persistently, host-visible-device-local if available — read through a
  descriptor set (section 6). Chapter 10 section 7 builds exactly this.
- Keep push constants for the small, per-draw things: an object index, a
  material ID, the frame counter.

That split — a UBO for per-frame data, push constants for per-draw data — is
what most engines converge on.

---

## 6. Descriptor sets

Push constants carry a few bytes of numbers. A shader that reads an image or a
whole buffer needs a **descriptor**: a small record naming the resource — for
an image, also the sampler and the layout to read it in. Descriptors are
grouped into **sets**, and four objects are involved. The relationship is the
part people find confusing:

- **`VkDescriptorSetLayout`** — the *shape*. "Binding 0 is a combined image
  sampler visible to the fragment shader." Created once, matches your GLSL.
- **`VkDescriptorPool`** — memory the sets are carved from.
- **`VkDescriptorSet`** — an instance of a layout, holding actual handles.
- **`vkUpdateDescriptorSets`** — writes handles into a set.

This chapter has one user: section 4's composite shader, which already declared
what it needs.

```glsl
layout(set = 0, binding = 0) uniform sampler2D sceneImage;
```

### The composite set: layout, pool, set

**This is `createCompositeObjects`**, in `VulkanRenderer.cpp`, which
`initialize` calls after `createSceneTarget`. It builds everything the
composite pass draws with — the set, then the pipeline. First the set's shape,
which must match that GLSL line exactly, and a pool sized for exactly what is
allocated from it:

```cpp
// Chapter 08 sections 4 and 6: one combined image sampler set, and the composite pipeline.
InitializationResult VulkanRenderer::createCompositeObjects()
{
    const VkDescriptorSetLayoutBinding binding{
        .binding         = 0,
        .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
        .descriptorCount = 1,
        .stageFlags      = VK_SHADER_STAGE_FRAGMENT_BIT,
    };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 1,
        .pBindings    = &binding,
    };
    const VkDescriptorPoolSize poolSize{ VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1 };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 1,
        .poolSizeCount = 1,
        .pPoolSizes    = &poolSize,
    };
    if (vkCreateDescriptorSetLayout(m_device, &setLayoutInfo, nullptr, &m_compositeSetLayout) != VK_SUCCESS ||
        vkCreateDescriptorPool(m_device, &poolInfo, nullptr, &m_descriptorPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("Creating the composite descriptor set layout or pool failed.");
    }

    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_descriptorPool,
        .descriptorSetCount = 1,
        .pSetLayouts        = &m_compositeSetLayout,
    };
    if (vkAllocateDescriptorSets(m_device, &allocateInfo, &m_compositeSet) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the composite set.");
    }
    writeCompositeSet();
```

(The function continues below with the pipeline.)

- **The binding** is `sampler2D`'s Vulkan name, a **combined image sampler**:
  an image view and a sampler in one descriptor. Its `binding` is GLSL's
  `binding`; its `stageFlags` say only the fragment shader reads it. The `set`
  number is not in the layout at all — it comes from where the layout sits in
  the pipeline layout, below.
- **The pool** says how many sets may be allocated from it (`maxSets`) and how
  many descriptors of each type they may hold in total. A pool is counted by
  layout: every set allocated from it takes one descriptor of each binding in
  its layout, times that binding's `descriptorCount`, whether the set ever
  writes that binding or not. This one holds one set of one combined image
  sampler. Asking a pool for more than it holds is always a sizing mistake,
  but not always reported: Vulkan lets `vkAllocateDescriptorSets` fail with
  `VK_ERROR_OUT_OF_POOL_MEMORY` or find room anyway, and the validation
  layer's default checks say nothing, because an overfull pool is a runtime
  error, not a misuse of the API. Chapter 24 section 3 meets the trap, a set
  that never writes one of its bindings; sized one sampler short, its pool ran
  on NVIDIA and lavapipe and failed only on AMD. So count a pool from its
  layouts: a clean run on one GPU proves nothing. Destroying the pool frees
  every set allocated from it, which is why `shutdown` never frees the set
  itself. Chapter 09 has each demo create a pool of its own, sized for its own
  sets.
- **The set** is allocated with the layout it is an instance of. It holds no
  handles yet; `writeCompositeSet` puts them in.

**This is `writeCompositeSet`**, the one write the set needs:

```cpp
void VulkanRenderer::writeCompositeSet()
{
    const VkDescriptorImageInfo imageInfo{
        .sampler     = m_linearClampSampler,
        .imageView   = m_sceneView,
        .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
    };
    const VkWriteDescriptorSet write{
        .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
        .dstSet          = m_compositeSet,
        .dstBinding      = 0,
        .descriptorCount = 1,
        .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
        .pImageInfo      = &imageInfo,
    };
    vkUpdateDescriptorSets(m_device, 1, &write, 0, nullptr);
}
```

`imageLayout` is the layout the image will be in *when the shader reads it* —
`SHADER_READ_ONLY_OPTIMAL`, which section 4's contract guarantees — not the
layout it is in now. It is a function of its own because the view changes:
`recreateSwapchain` rebuilds the scene target and then calls it again
(section 4).

### The composite pipeline

The rest of `createCompositeObjects`. A **pipeline layout** lists the set
layouts a pipeline uses, by set number — element 0 of `pSetLayouts` is set 0 —
plus any push-constant ranges, of which the composite has none yet (Chapter 16
adds one). Then the specialization constant from section 4's aside, and the
pipeline itself, through Chapter 06 section 8's `GraphicsPipelineDesc`:

```cpp
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_compositeSetLayout,
    };
    if (vkCreatePipelineLayout(m_device, &layoutInfo, nullptr, &m_compositeLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the composite pass.");
    }

    // A GLSL bool specialization constant is a VkBool32 on the C++ side - four
    // bytes, not sizeof(bool).
    const VkBool32 encodeSrgb = isSrgbFormat(m_swapchain.format()) ? VK_FALSE : VK_TRUE;
    const VkSpecializationMapEntry encodeEntry{
        .constantID = 0,
        .offset     = 0,
        .size       = sizeof(VkBool32),
    };
    const VkSpecializationInfo specialization{
        .mapEntryCount = 1,
        .pMapEntries   = &encodeEntry,
        .dataSize      = sizeof(VkBool32),
        .pData         = &encodeSrgb,
    };
    if (encodeSrgb == VK_FALSE)
    {
        Log::warning("The swapchain fell back to an _SRGB format; ImGui will look washed out.");
    }

    const VkFormat swapchainFormat = m_swapchain.format();
    const GraphicsPipelineDesc composite{
        .vertexShader           = "Fullscreen/Fullscreen.vert.spv",
        .fragmentShader         = "Composite/Composite.frag.spv",
        .colorFormats           = { &swapchainFormat, 1 },
        .fragmentSpecialization = &specialization,
        .layout                 = m_compositeLayout,
    };
    m_compositePipeline = createGraphicsPipeline(m_device, m_pipelineCache, composite);
    if (m_compositePipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the composite pipeline failed.");
    }
    return InitializationResult::success();
}
```

- **The specialization info** is a byte blob and a map: entry 0 says "constant
  0 is the four bytes at offset 0", and `pData` points at them.
  `createGraphicsPipeline` hands it to the fragment stage.
- **`swapchainFormat` is a named local** because `colorFormats` is a span, which
  points at its data rather than copying it; the local lives until the call
  returns.
- **No depth, no blending, no vertex input**: the fullscreen triangle makes its
  own corners, and every pixel is written once. The desc's defaults say so.

### The rule that prevents a whole class of bugs

**Never update a descriptor set, or write a buffer, the GPU might still be
reading.** With two frames in flight, the GPU may still be drawing the previous
frame while the CPU records the next. So anything whose *contents* change every
frame — a camera's matrices, say — needs `FRAMES_IN_FLIGHT` copies, and each
copy is written only after the fence for its frame slot has been waited on.
Chapter 10 section 7 builds exactly that: one uniform buffer and one set per
frame in flight, each set written once at creation, and only the buffers'
contents changing per frame.

A set that never changes — a texture loaded once — needs one copy. A set that
must be *re-pointed* while running, like the composite set after a resize, is
rewritten only after a `vkDeviceWaitIdle`, which `recreateSwapchain` has
already done. The alternative is `VK_DESCRIPTOR_BINDING_UPDATE_AFTER_BIND_BIT`
from descriptor indexing, which relaxes the rule. It is a good tool and a bad
starting point.

### Binding

In `recordFrame`'s second rendering scope (section 4), the composite pass is
three calls:

```cpp
vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_compositePipeline);
vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_compositeLayout,
                        0, 1, &m_compositeSet, 0, nullptr);
vkCmdDraw(commandBuffer, 3, 1, 0, 0);
```

The `0, 1` are the first set number and the count: one set, bound as set 0.
Binding needs a pipeline layout compatible with the pipeline's, which is why it
names `m_compositeLayout`. Sets stay bound across pipeline binds as long as the
layouts are compatible, which makes an organization by frequency worth adopting
even at this scale:

| Set | Frequency | Contents |
| --- | --- | --- |
| 0 | Per frame | Camera, time, global parameters |
| 1 | Per pass | Render-target inputs, shadow maps |
| 2 | Per material | Textures |
| 3 | Per draw | Rarely used; push constants usually win |

This tutorial uses two of those: from Chapter 10 on, set 0 is per frame and
set 1 is per material, with push constants per draw. Nothing here needs a
per-pass set yet, and a set number with nothing bound still needs a layout, so
it is left out rather than reserved. The [index](../VulkanTutorial.md) has the
whole plan in one table. (The composite pass is the engine's own and binds its
one set as set 0; it never shares a pipeline layout with the scene.)

---

## Checkpoint

If you typed in the order at the top of the chapter, build and run now. You
should see:

- **the triangle exactly as Chapter 06 drew it**, though it is now drawn into
  the offscreen image and reaches the screen through the composite pass. If it
  looks lighter or darker than before, something encodes twice or not at all;
- **the panels darker and crisper than in Chapter 07**: ImGui's colors are no
  longer encoded a second time;
- **resizing that follows the window**: drag the window small and large, and
  the triangle is never stretched or cropped, with validation silent.

The "Shader" panel's sliders move and change nothing yet. Section 5 connects
them.

---

## 7. Switch to VMA now

Sections 1 and 2 allocated memory by hand. That was the point — you know what
heaps, memory types, and `memoryTypeBits` mean, and none of it is mysterious.

Keep going and you will write a suballocator, because a scene imported in
Chapter 14 holds hundreds of buffers and images, and `maxMemoryAllocationCount`
is as low as 4096 on some drivers. That is not a Vulkan learning goal.

It is already installed. The implementation goes in exactly one translation
unit, and under premake's `warnings "Extra"` it emits dozens of warnings that
are VMA's, not yours — so silence them for that one include:

```cpp
// Source/PillowFort/VulkanGraphics/VmaImplementation.cpp - the only file that defines it.
#pragma warning(push, 0)
#define VMA_IMPLEMENTATION
#include <vma/vk_mem_alloc.h>
#pragma warning(pop)
```

Everything else includes `<vma/vk_mem_alloc.h>` plainly — including
`VulkanRenderer.h` and `VulkanResources.h`, whose members use VMA's types. The
allocator is created right after the device and goes in the context, so the
free functions can reach it:

```cpp
// In VulkanRenderer::initialize, right after m_vulkan.Initialize.
const VmaAllocatorCreateInfo allocatorInfo{
    .physicalDevice   = m_vulkan.PhysicalDevice(),
    .device           = m_device,
    .instance         = m_vulkan.Instance(),
    .vulkanApiVersion = VK_API_VERSION_1_3,
};
if (vmaCreateAllocator(&allocatorInfo, &m_context.allocator) != VK_SUCCESS)   // VulkanContext's new field
{
    return InitializationResult::failure("vmaCreateAllocator failed.");
}
```

The buffer functions from section 2 then change shape. The memory-type search
disappears into VMA, and a host-visible buffer comes back already mapped:

```cpp
// VulkanResources.h, replacing section 2's AllocatedBuffer and createBuffer.
struct AllocatedBuffer
{
    VkBuffer      buffer     = VK_NULL_HANDLE;
    VmaAllocation allocation = VK_NULL_HANDLE;
    void*         mapped     = nullptr;   // non-null when the CPU writes it
    VkDeviceSize  size       = 0;
};

// hostVisible: the CPU writes it - staging, per-frame uniforms. Otherwise device-local.
AllocatedBuffer createBuffer(VulkanContext& context, VkDeviceSize size,
                             VkBufferUsageFlags usage, bool hostVisible);
void            destroyBuffer(VulkanContext& context, AllocatedBuffer& buffer);
```

```cpp
// VulkanResources.cpp. findMemoryType is no longer needed; delete it.
AllocatedBuffer createBuffer(VulkanContext& context, VkDeviceSize size,
                             VkBufferUsageFlags usage, bool hostVisible)
{
    const VkBufferCreateInfo bufferInfo{
        .sType       = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
        .size        = size,
        .usage       = usage,
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
    };

    const VmaAllocationCreateFlags hostFlags = VMA_ALLOCATION_CREATE_HOST_ACCESS_SEQUENTIAL_WRITE_BIT
                                             | VMA_ALLOCATION_CREATE_MAPPED_BIT;
    const VmaAllocationCreateInfo allocationInfo{
        .flags = hostVisible ? hostFlags : VmaAllocationCreateFlags{ 0 },
        .usage = VMA_MEMORY_USAGE_AUTO,
    };

    AllocatedBuffer result{ .size = size };
    VmaAllocationInfo detail{};
    if (vmaCreateBuffer(context.allocator, &bufferInfo, &allocationInfo,
                        &result.buffer, &result.allocation, &detail) != VK_SUCCESS)
    {
        Log::error("vmaCreateBuffer failed.");
        return {};
    }
    result.mapped = detail.pMappedData;
    return result;
}

void destroyBuffer(VulkanContext& context, AllocatedBuffer& buffer)
{
    // A null buffer is a no-op; a null allocator asserts. Buffers only exist
    // after the allocator does, so this cannot see one.
    vmaDestroyBuffer(context.allocator, buffer.buffer, buffer.allocation);
    buffer = {};
}
```

`uploadToBuffer` and `uploadToImage` change the same three ways: create the
staging buffer with `createBuffer(context, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, true)`;
`std::memcpy` into `staging.mapped` in place of the `vkMapMemory` /
`vkUnmapMemory` pair; and follow the copy with
`vmaFlushAllocation(context.allocator, staging.allocation, 0, VK_WHOLE_SIZE)`.
The flush is the price of letting VMA choose the memory type:
`HOST_ACCESS_SEQUENTIAL_WRITE` asks for host-visible memory, not coherent
memory, so section 2's "take coherent memory" is no longer a guarantee — and on
a coherent type VMA skips the call, so it costs nothing where it is not needed.
Every `destroyBuffer(context.device, ...)` becomes `destroyBuffer(context, ...)`.
Here is `uploadToBuffer` as you keep it; `uploadToImage` changes the same lines:

```cpp
void uploadToBuffer(VulkanContext& context, AllocatedBuffer& destination,
                    const void* data, VkDeviceSize size)
{
    AllocatedBuffer staging = createBuffer(context, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, true);

    std::memcpy(staging.mapped, data, static_cast<size_t>(size));
    vmaFlushAllocation(context.allocator, staging.allocation, 0, VK_WHOLE_SIZE);   // no-op when coherent

    immediateSubmit(context, [&](VkCommandBuffer commandBuffer) {
        const VkBufferCopy region{ .size = size };
        vkCmdCopyBuffer(commandBuffer, staging.buffer, destination.buffer, 1, &region);
    });

    destroyBuffer(context, staging);
}
```

`VMA_MEMORY_USAGE_AUTO` plus the access-pattern flag picks the best available
type, including the device-local host-visible BAR memory from section 1, with
a correct fallback everywhere. That heuristic alone is worth the dependency.

---

## 8. One layout, two languages

You already have a struct written twice: `ShaderParameters` in C++ (Chapter 07
section 9) and the `ShaderParametersBlock` push-constant block in GLSL
(section 5). Nothing checks that the two agree, and a silent mismatch produces
garbage that looks like a math error. This section is how to keep them in
agreement, and how to make the compiler prove it.

### Where the bytes go

The two languages place members by different rules. C++ puts a `float` on any
4-byte boundary. GLSL, in a push-constant block, starts a `vec4` only on a
multiple of 16. `ShaderParameters` has its `padding0` for exactly that reason.
Take it out of both sides and compare where each language puts each member:

```text
 offset   C++, without padding0      GLSL, without padding0
    0     time                       time
    4     amplitude                  amplitude
    8     frequency                  frequency
   12     baseColor[0]  (red)        -- gap: a vec4 starts on a multiple of 16 --
   16     baseColor[1]  (green)      baseColor.r
   20     baseColor[2]  (blue)       baseColor.g
   24     baseColor[3]  (alpha)      baseColor.b
   28     (end: 28 bytes pushed)     baseColor.a
```

C++ writes the color at 12; the shader reads it from 16. Red is lost, green is
read as red, and alpha is whatever lies past the 28 bytes C++ pushed. With
`padding0` in both, C++ also puts `baseColor` at 16, and the two agree.

### The alignment rules you must respect

The rule that bit there is one row of a short table. Which rules apply depends
on the kind of block:

| Layout | Where | Rule |
| --- | --- | --- |
| `std140` | Uniform buffers | `vec3` and `vec4` align to **16**, and so does every element of an array: a `float[4]` takes 64 bytes. Wasteful and full of surprises. |
| `std430` | Storage buffers, push constants | Scalars and `vec2` align naturally, but `vec3` and `vec4` still align to 16. What changes from `std140` is that arrays and structs are no longer rounded up to 16, so a `float[]` has a 4-byte stride. |
| `scalar` | Anything, needs `scalarBlockLayout` | Exactly C rules. `#extension GL_EXT_scalar_block_layout : require` |

Three habits that eliminate the problem:

1. **Never put a `vec3` in a shared struct.** Use `vec4` and ignore `w`, or
   pack a scalar into it. A `vec3` followed by a `float` occupies 16 bytes in
   `std140` and 16 in C++ — but a `vec3` followed by a `vec3` does not match,
   and you will not notice until the second one is wrong.
2. **Enable `scalarBlockLayout`** (Chapter 02's table) and use
   `layout(scalar)`. It makes GLSL follow C rules and most of the class of bug
   disappears. This tutorial keeps to habits 1 and 3 instead, so that every
   block reads the same under any GLSL settings; `scalar` is there when you
   want it.
3. **`static_assert` the size and key offsets.** Free, and it fails at compile
   time instead of rendering wrong.

### Make the compiler check it

The third habit, for the twin you already have, is one line. **This is
`createTrianglePipeline`**, beside section 5's budget check:

```cpp
// Chapter 08 section 8: GLSL starts the vec4 baseColor on a 16-byte boundary,
// and padding0 is what puts the C++ member there too.
static_assert(offsetof(ShaderParameters, baseColor) == 16, "ShaderParameters no longer matches its GLSL block.");
```

`offsetof` needs `<cstddef>`. Delete `padding0` from the C++ struct and the
build stops on this line, rather than the triangle's bands turning the wrong
color. Chapter 09 moves the line with the rest of the triangle.

### One definition both languages read

A `static_assert` checks two copies; it does not remove one. The cure is a
header both compilers read. `glslc` runs the C preprocessor, a `struct` is
written almost the same way in both languages, and the differences — C++ needs
GLM's types and a namespace — fit behind `#ifdef __cplusplus`. **This is
`Shaders/Include/SharedShaderTypes.h`**, as this chapter leaves it:

```c
/* Shaders/Include/SharedShaderTypes.h */
#ifndef PF_SHARED_SHADER_TYPES_H
#define PF_SHARED_SHADER_TYPES_H

#ifdef __cplusplus
    #include <cstddef>   /* offsetof, for the static_asserts below */
    #include <cstdint>
    #include <glm/glm.hpp>
    namespace pf::shared {
    using vec2 = glm::vec2;
    using vec4 = glm::vec4;
    using uint = std::uint32_t;
#endif

/* Each shared struct goes here, with its static_asserts after it. */
/* Chapter 10 writes the first. */

#ifdef __cplusplus
    }   /* namespace pf::shared */
#endif

#endif
```

The C++ prelude gives GLSL's type names to GLM's types, so a struct written
with `vec4` and `uint` compiles in both languages; C++ code then names it
`shared::` and the struct's name. The `static_assert`s sit inside
`#ifdef __cplusplus` because GLSL has none.

The file holds no struct yet, and the triangle keeps its hand-written pair: its
C++ side carries the default values the panel starts from, which a GLSL struct
cannot. The first structs written this way arrive in the next two chapters.
Chapter 09's gradient keeps its push constants in a header in its own folder
that includes this one for the `vec4` alias, and Chapter 10's `FrameData`,
which every scene shader reads, is the first struct that lives here.

From GLSL:

```glsl
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SharedShaderTypes.h"
```

The GLSL side works exactly as section 5's `Color.glsl` does: the extension
line, and Chapter 06's `-I` for `Shaders/Include`, so the include resolves from
any shader's folder. A `.h` there is not picked up by that chapter's glob,
which only compiles `.vert`, `.frag`, and `.comp` files. What is new is the C++
side, which `Color.glsl` never had: `#include "SharedShaderTypes.h"` needs the
same directory on the compiler's include path, so add `"Shaders/Include"` to
the common `includedirs` in `premake5.lua`, beside `"Source"`.

Generating this header from a schema is the plausible end state, and ROADMAP
parks it until there is a real consumer. Write it by hand for the first two
structs, then decide — that is Guardrail 2, write a pattern twice before
automating it.

---

## 9. Buffer device address, for later

Nothing before Chapter 33's path tracer uses this; skim it now, and come back
then. Enable `Vulkan12Features::bufferDeviceAddress` and a buffer has a plain
64-bit GPU pointer, which `vkGetBufferDeviceAddress` returns (Chapter 33
section 6 writes the call). A shader receives it as a number and reads through
it as a typed reference:

```glsl
#extension GL_EXT_buffer_reference    : require
#extension GL_EXT_scalar_block_layout : require   // for the `scalar` qualifier below

layout(buffer_reference, scalar) buffer VertexBuffer { Vertex vertices[]; };

layout(push_constant) uniform PushConstants {
    VertexBuffer vertices;   // a 64-bit address, in 8 push constant bytes
} pc;
```

No descriptor set, no binding, no update. For a path tracer that needs to reach
arbitrary meshes and materials from a single shader, this is far simpler than
descriptor indexing — and acceleration structures require the feature anyway.

Enabling the feature is not the whole switch. Three more places must agree, and
missing any one is reported at `vkBindBufferMemory` or `vkGetBufferDeviceAddress`,
not at the line you forgot:

- the buffer's usage includes `VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT`;
- its memory was allocated with `VkMemoryAllocateFlagsInfo` carrying
  `VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT` in `pNext`;
- with VMA, which does that allocation for you, the allocator was created with
  `VMA_ALLOCATOR_CREATE_BUFFER_DEVICE_ADDRESS_BIT`.

---

## Exit check

- [ ] Each ImGui slider changes what the triangle looks like, through a push
      constant, with no recompile.
- [ ] The scene renders to an offscreen `R16G16B16A16_SFLOAT` target and reaches
      a `B8G8R8A8_UNORM` swapchain through the composite pass — and the
      triangle looks as it did in Chapter 06.
- [ ] With Amplitude at its maximum, the band peaks on the triangle match the
      `baseColor` swatch. (Delete the `srgbToLinear` call to see them come out
      lighter than the swatch — the mistake section 4 warns about.)
- [ ] ImGui draws into the swapchain image after the composite and is no longer
      washed out.
- [ ] Resizing recreates the offscreen target; the image is never stretched or
      cropped.
- [ ] Closing is validation-clean, and `vmaDestroyAllocator` does not assert:
      every VMA allocation was freed.
- [ ] **The upload path runs.** Nothing calls `uploadToBuffer` yet, so for one
      run add this to `initialize`, after `createCompositeObjects`, and delete
      it again afterwards:

      ```cpp
      {
          const uint32_t  words[16]{};
          AllocatedBuffer target = createBuffer(m_context, sizeof(words), VK_BUFFER_USAGE_TRANSFER_DST_BIT, false);
          uploadToBuffer(m_context, target, words, sizeof(words));
          destroyBuffer(m_context, target);
      }
      ```

      Validation stays clean. Comment out the `destroyBuffer` line and closing
      stops on VMA's assertion that some allocations were not freed: the leak
      check works.
- [ ] **The layout check works.** Delete `padding0` from the C++
      `ShaderParameters`: the build stops at section 8's `static_assert`. Put it
      back.

Next: [09 — The Demo Harness](09-Demo-Harness.md)
