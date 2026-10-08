# 18 — Anti-Aliasing

**Goal:** geometric edges are smooth at 4× MSAA, cutout leaves stop
stair-stepping, and the sample count is a setting you can change live — while
everything that reads the scene after it is drawn keeps reading a plain,
single-sample image.

**ROADMAP:** step 19.

**Module:** `Source/PillowFort/VulkanGraphics/`, namespace
`pf::vulkan_graphics` — `VulkanRenderer` (the multisampled targets and the
setting), `SceneTargets.h/.cpp` (the resolves in `beginScenePass`),
`GraphicsPipeline.h/.cpp`, and `SceneRenderer`'s pipelines. Also
`DebugPanels/ImGuiDebugPanels` (a picker), `SandboxGame/Main.cpp` (`--msaa`),
the demos that build their own pipelines, and `Shaders/Scene/Mesh.frag.glsl`
(alpha-to-coverage).

**Prerequisites:**

- Chapter 04 section 5 — the three questions, and the cookbook's
  "Depth attachment, start of frame" row, which this chapter reuses.
- Chapter 06 sections 4 and 8 — the multisample state that has said
  `VK_SAMPLE_COUNT_1_BIT` since the triangle, `GraphicsPipelineDesc`, and the
  deletion-queue question section 8 left open.
- Chapter 08 sections 3, 4, and 6 — images, the scene target and its contract
  with the composite pass, and the rule for re-pointing descriptors.
- Chapter 09 sections 3-5 — `SceneFormats` (whose `samples` field has waited
  for this chapter), `SceneTargets`, `beginScenePass`, and `switchDemo`'s
  Teardown, Setup, Resize sequence.
- Chapter 10 section 9 — the depth image, its barrier, and its `STORE_OP_STORE`.
- Chapter 11 sections 8 and 11 — `GraphicsPipelineDesc`'s field order, and
  `SceneRenderer::CreatePipelines`.
- Chapter 15 section 5 — fragments are shaded in 2x2 quads, which is how
  `fwidth` knows its neighbours' values. Section 8 uses it.
- Chapter 15 section 11 — `discard` and the demote feature, the cutout
  pipelines, and `MeshSpecialization`.
- Chapter 17 — the shadow pass, which this chapter leaves at one sample, and
  its test scene.

---

## What you are actually writing

Multisample anti-aliasing changes what the scene pass draws *into*, and nothing
that comes after it:

```text
 one sample (Chapters 08-17)              N samples (this chapter)
 ───────────────────────────              ───────────────────────────────────────────────
 scene pass draws into:                   scene pass draws into:
   scene target   (1 sample, SFLOAT)        multisampled color (N samples, SFLOAT, transient)
   scene depth    (1 sample, D32)           multisampled depth (N samples, D32, transient)
                                          and at the end of the pass, by the hardware:
                                            color ── resolve: AVERAGE ──▶ scene target
                                            depth ── resolve: MAX or SAMPLE_ZERO ──▶ scene depth
 after the pass, everyone reads:          after the pass, everyone reads:
   scene target, scene depth                scene target, scene depth   (unchanged)
```

The right-hand column's last line is the point of the design. The composite
pass, ImGui, Chapter 20's compute, Chapter 21's particles, Chapter 26's culling,
and Chapter 33's path tracer (which writes the scene target as a storage image
and never rasterizes at all) all go on seeing the same single-sample images
they always did. Only the scene pass knows about samples.

The files, and what each section adds:

```text
VulkanGraphics/VulkanRenderer.h/.cpp   sample counts, depth resolve mode, the multisampled  sections 3, 4, 7
                                       targets, setSampleCount
VulkanGraphics/SceneTargets.h/.cpp     the multisampled handles; resolves in beginScenePass  sections 4, 5
VulkanGraphics/GraphicsPipeline.h/.cpp samples and alphaToCoverage                           section 6
VulkanGraphics/SceneRenderer.cpp       CreatePipelines: the sample count, alpha-to-coverage  sections 6, 8
Demos/Triangle, Gradient, Cubes        .samples in their pipelines                           section 6
DebugPanels/ImGuiDebugPanels.h/.cpp    drawSampleCountPicker                                 section 7
SandboxGame/Main.cpp                   --msaa, and the picker                                sections 3, 7
Shaders/Scene/Mesh.frag.glsl           alpha-to-coverage for cutouts                         section 8
```

### What `VulkanRenderer` gains

```cpp
// Source/PillowFort/VulkanGraphics/VulkanRenderer.h - Chapter 18's additions.
struct RendererSettings
{
    // Chapter 05's preferredGpu and presentMode come first, unchanged.
    uint32_t         sampleCount = 1;   // Chapter 18: MSAA samples per pixel, from --msaa; lowered to what the GPU offers
};

class VulkanRenderer
{
public:
    // Chapter 18 section 7.
    VkSampleCountFlagBits                  sampleCount() const { return m_sampleCount; }
    std::span<const VkSampleCountFlagBits> supportedSampleCounts() const { return m_supportedSampleCounts; }
    void                                   setSampleCount(VkSampleCountFlagBits samples);

private:
    InitializationResult createMultisampleTargets(VkExtent2D extent);   // Chapter 18 section 4
    void                 destroyMultisampleTargets();

    // Chapter 18, beside the scene targets.
    std::vector<VkSampleCountFlagBits> m_supportedSampleCounts;                     // section 3
    VkSampleCountFlagBits              m_sampleCount      = VK_SAMPLE_COUNT_1_BIT;
    VkResolveModeFlagBits              m_depthResolveMode = VK_RESOLVE_MODE_SAMPLE_ZERO_BIT;
    VkImage                            m_multisampleColorImage      = VK_NULL_HANDLE;   // section 4; null at 1x
    VmaAllocation                      m_multisampleColorAllocation = VK_NULL_HANDLE;
    VkImageView                        m_multisampleColorView       = VK_NULL_HANDLE;
    VkImage                            m_multisampleDepthImage      = VK_NULL_HANDLE;
    VmaAllocation                      m_multisampleDepthAllocation = VK_NULL_HANDLE;
    VkImageView                        m_multisampleDepthView       = VK_NULL_HANDLE;
};
```

`VulkanRenderer.h` gains `<span>` and `<vector>`. The order things happen in:

```text
VulkanRenderer::initialize
    the allocator, swapchain, scene depth format       Chapters 05, 08, 10
    query sample counts and depth resolve modes        section 3
    createSceneTarget(extent)                          Chapter 08, 10; ends with createMultisampleTargets
    the rest of initialize, unchanged
VulkanRenderer::destroySceneTarget                     begins with destroyMultisampleTargets
VulkanRenderer::setSampleCount                         section 7: wait, rebuild the multisampled pair, switchDemo
```

> **Jump:** until now, one pixel of an attachment held one value, and the image
> you drew into was the image the next pass read. From here, at more than one
> sample, the attachments hold **N values per pixel**, the fragment shader still
> runs **once** per pixel per triangle, and the image you draw into is **not**
> the one anyone reads: the pass ends by collapsing N samples into one pixel of a
> different image. Keep three images in mind for each of color and depth — what
> the pipeline renders into (multisampled), what the pass resolves into
> (single-sample), and which one each barrier is about.

---

## 1. What aliasing is, and which kind MSAA fixes

A pixel is a square; the rasterizer asks one question per pixel — *does the
triangle cover the pixel's centre?* — and colors the whole square by the
answer. Anything that changes faster than once per pixel gets that one answer
for all of it. The result is **aliasing**, and it comes in four kinds that look
alike and have different cures:

| Kind | Looks like | Cause | Cure |
| --- | --- | --- | --- |
| **Geometric edges** | Staircases along every silhouette, crawling as the camera moves | Coverage is decided at one point per pixel | **MSAA** — this chapter |
| **Sub-pixel geometry** | Thin poles, wires, and distant grass blades breaking into dashes that flicker | The object is thinner than a pixel and misses most pixel centres | MSAA helps (more points to hit); below the sample spacing it fails too |
| **Shading** | Sparkling specular highlights on bumpy, shiny surfaces; noisy normal maps in the distance | The *color* changes faster than once per pixel, inside a triangle | Not MSAA. Sample shading (the aside at the end of section 8) or filtering the shading itself; in practice temporal AA |
| **Texture** | Moiré on a distant checkerboard | A texel pattern finer than the pixels | Mipmaps — Chapter 15 did this already |

Shadow-map aliasing — staircase shadow edges — is a fifth case that belongs to
Chapter 17: it is a shading change across a surface, and PCF is its filter.

MSAA addresses the first row, completely, and the second, partly. That is
exactly the aliasing a scene of USD models with thin parts and cutout leaves
shows most, and the grass chapters (25-27) need it badly: a field of blades is
nothing *but* edges. What MSAA leaves — shading aliasing and blades thinner than
the sample spacing — is section 9's subject, and the reason temporal AA is named
there as the next step.

---

## 2. How MSAA works

**Multisampling** keeps several **samples** per pixel — 4 is the standard — at
fixed positions inside the pixel. For each triangle, the rasterizer tests
*coverage* at every sample position and the *depth test* at every sample. But it
runs the fragment shader **once per pixel** that the triangle touches, and writes
that one color to each sample the triangle covered and that passed depth.

```text
 one pixel, 4 samples          edge of a red triangle            stored samples      resolved pixel
 ┌─────────────┐               ┌─────────────┐                   ┌─────────────┐
 │   ●     ●   │               │ ●╲    ●     │  shader runs once │ R      B    │     average:
 │             │               │    ╲        │  → red; written   │             │     2 red, 2 blue
 │   ●     ●   │               │ ●    ╲  ●   │  to the 2 covered │ R      B    │     = purple
 └─────────────┘               └───────╲─────┘  samples          └─────────────┘
```

At the end, a **resolve** averages each pixel's samples into one value. Along an
edge the pixel gets a mix in proportion to coverage — an anti-aliased edge — at
nearly the cost of no anti-aliasing in *shading*: one shader invocation per pixel
per triangle, as before (a few more along edges, where two triangles each shade
the same pixel).

What it costs is **memory and bandwidth**: a 4× target stores four colors and
four depths per pixel. At 1920 × 1080 with an 8-byte color and 4-byte depth, that
is 100 MB that exists only during the pass. On a desktop GPU this is real
bandwidth, though compression of mostly-uniform pixels hides much of it. On a
tile-based GPU (phones, Apple silicon) the samples live in on-chip tile memory,
are resolved there, and never reach main memory at all — which is what section
4's *transient* usage is for.

What it does **not** do is change what the shader computes. A specular highlight
smaller than a pixel is evaluated once, at one point — MSAA averages one value
with itself.

---

## 3. What the GPU offers

**This is the sample-count query in `VulkanRenderer::initialize`**, two
file-scope helpers, and `--msaa`.

**Sample counts.** Not every count works for every attachment. The device
reports, per kind of attachment, which counts a framebuffer may use:
`framebufferColorSampleCounts` for float and fixed-point color formats — the
scene target's `R16G16B16A16_SFLOAT` is one — and
`framebufferDepthSampleCounts` for depth. The scene pass has both, so the usable
counts are the bits set in **both**. The spec guarantees 1 and 4; desktop GPUs
typically add 2 and 8; Mesa's lavapipe offers exactly 1 and 4.

```cpp
// File scope, above the namespace block in VulkanRenderer.cpp. Chapter 18 section 3: the sample counts
// a scene pass can use - its color AND its depth attachment must support them - ascending, from 1.
static std::vector<VkSampleCountFlagBits> querySampleCounts(const VkPhysicalDeviceLimits& limits)
{
    const VkSampleCountFlags both = limits.framebufferColorSampleCounts & limits.framebufferDepthSampleCounts;
    std::vector<VkSampleCountFlagBits> counts;
    for (uint32_t bit = VK_SAMPLE_COUNT_1_BIT; bit <= VK_SAMPLE_COUNT_64_BIT; bit <<= 1)
    {
        if ((both & bit) != 0) { counts.push_back(static_cast<VkSampleCountFlagBits>(bit)); }
    }
    return counts;
}

// File scope. The largest supported count that is not more than the one asked for. 1 is always there.
static VkSampleCountFlagBits chooseSampleCount(std::span<const VkSampleCountFlagBits> supported, uint32_t requested)
{
    VkSampleCountFlagBits chosen = VK_SAMPLE_COUNT_1_BIT;
    for (const VkSampleCountFlagBits count : supported)
    {
        if (static_cast<uint32_t>(count) <= requested) { chosen = count; }
    }
    if (static_cast<uint32_t>(chosen) != requested)
    {
        Log::warning(std::format("MSAA {}x is not available here; using {}x.",
                                 requested, static_cast<uint32_t>(chosen)).c_str());
    }
    return chosen;
}
```

A `VkSampleCountFlagBits` value *is* its count — `VK_SAMPLE_COUNT_4_BIT` is 4 —
which is what lets the comparison and the cast work. Like the present mode in
Chapter 03, an unavailable request is lowered with a warning, never refused.

**Depth resolve modes.** Averaging is right for color and meaningless for depth:
the average of a near and a far depth is a surface that is not there. So depth
resolves by **choosing** a sample, and Vulkan 1.2 made the choice core:
`VkPhysicalDeviceDepthStencilResolveProperties::supportedDepthResolveModes` says
which of these the device can do:

| Mode | Result | Guaranteed |
| --- | --- | --- |
| `SAMPLE_ZERO` | Sample 0's depth | Yes, always |
| `MIN` | The nearest sample (with `LESS` testing) | No |
| `MAX` | The farthest sample | No |
| `AVERAGE` | The mean of the samples: a depth where no surface is | No; a driver may offer it, and this chapter never wants it |

This tutorial resolves with **`MAX` where it is supported, `SAMPLE_ZERO`
otherwise**. Why the farthest: the readers of the resolved depth want it.
Chapter 26 builds an occlusion-culling pyramid from it, and an occlusion test
must never call something hidden that is visible; at an edge pixel, the farthest
sample is the conservative answer. Chapter 21's soft particles fade against it,
and at edges either choice is fine. Readers must tolerate either mode — on a
device with only `SAMPLE_ZERO` (lavapipe is one) they will get sample 0 — and
the two differ only along geometric edges. AMD, NVIDIA, and Intel desktop
drivers report `MAX`.

The query goes in `initialize`, after the allocator and Chapter 10's choice of
the depth format, and before `createSceneTarget`, which needs both answers. One
`vkGetPhysicalDeviceProperties2` call returns the limits and, through `pNext`,
the resolve properties:

```cpp
    // Chapter 18 section 3: which sample counts this GPU's scene pass can use, and how it resolves depth.
    VkPhysicalDeviceDepthStencilResolveProperties resolveProperties{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DEPTH_STENCIL_RESOLVE_PROPERTIES,
    };
    VkPhysicalDeviceProperties2 deviceProperties{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,
        .pNext = &resolveProperties,
    };
    vkGetPhysicalDeviceProperties2(m_vulkan.PhysicalDevice(), &deviceProperties);
    m_supportedSampleCounts = querySampleCounts(deviceProperties.properties.limits);
    m_sampleCount           = chooseSampleCount(m_supportedSampleCounts, settings.sampleCount);
    m_depthResolveMode      = (resolveProperties.supportedDepthResolveModes & VK_RESOLVE_MODE_MAX_BIT) != 0
                            ? VK_RESOLVE_MODE_MAX_BIT
                            : VK_RESOLVE_MODE_SAMPLE_ZERO_BIT;
    Log::info(std::format("MSAA: {}x; depth resolves by {}.",
                          static_cast<uint32_t>(m_sampleCount),
                          string_VkResolveModeFlagBits(m_depthResolveMode)).c_str());
```

`string_VkResolveModeFlagBits` comes from `vk_enum_string_helper.h`, which
`VulkanRenderer.cpp` already includes for the present mode's name.

**The setting.** `parseSettings` in `Main.cpp` — Chapter 05's, which Chapter 09
made return a `LaunchSettings` holding the renderer's settings and the starting
demo — gains one branch, so `SandboxGame.exe --msaa 4` starts at four samples:

```cpp
        else if (key == "--msaa")
        {
            settings.renderer.sampleCount = static_cast<uint32_t>(std::atoi(argv[i + 1]));   // 1, 2, 4, 8: the renderer checks
        }
```

`Main.cpp` gains `<cstdlib>` for `std::atoi`.

The default stays 1: anti-aliasing is something to turn on and compare against,
and Chapter 05's habit is that startup behaviour does not change under you.

---

## 4. The multisampled targets

**This is `createMultisampleTargets` and `destroyMultisampleTargets`**, and what
`SceneTargets` gains.

Two images, the scene target's color format and Chapter 10's depth format, at
the chosen sample count, sized to the window. They differ from every image so
far in two flags:

- **`samples`** is the count, not `VK_SAMPLE_COUNT_1_BIT`.
- **`VK_IMAGE_USAGE_TRANSIENT_ATTACHMENT_BIT`**: the image is only ever an
  attachment, and its contents are not needed after the pass — only the
  resolved values are. That is the promise that lets a tile-based GPU keep it in
  tile memory and never give it real memory at all.

To collect on that promise, the memory must be **lazily allocated**
(`VK_MEMORY_PROPERTY_LAZILY_ALLOCATED_BIT`): committed only if something actually
spills to it. Tile-based GPUs have such a memory type; desktop GPUs do not, and
lavapipe does not. So it is asked for as *preferred*, not required — VMA uses it
where it exists and falls back to ordinary device memory everywhere else. On a
desktop GPU the transient flag then changes nothing but documentation, which is
fine: the code is right for both kinds of hardware.

```cpp
// File scope, above the namespace block. Chapter 18 section 4: a multisampled attachment that lives
// only for the length of the scene pass.
static VkImageCreateInfo multisampleTargetInfo(VkExtent2D extent, VkFormat format,
                                               VkSampleCountFlagBits samples, VkImageUsageFlags usage)
{
    return VkImageCreateInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = format,
        .extent        = { extent.width, extent.height, 1 },
        .mipLevels     = 1,
        .arrayLayers   = 1,
        .samples       = samples,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = usage | VK_IMAGE_USAGE_TRANSIENT_ATTACHMENT_BIT,   // resolved, never read back
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
}
```

Transient usage allows only attachment usages beside it — no `SAMPLED`, no
`STORAGE`, no `TRANSFER`. That is not a limitation here: nothing samples these
images; everyone samples what they resolve into.

```cpp
// VulkanRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 18).
InitializationResult VulkanRenderer::createMultisampleTargets(VkExtent2D extent)
{
    // At one sample the scene pass draws straight into the scene target and depth: nothing to make.
    if (m_sampleCount == VK_SAMPLE_COUNT_1_BIT) { return InitializationResult::success(); }

    // Lazily allocated memory where the GPU has it (tile-based GPUs keep transient attachments on chip
    // and never back them); "preferred", so desktop GPUs, which have none, get device memory instead.
    const VmaAllocationCreateInfo allocationInfo{
        .flags          = VMA_ALLOCATION_CREATE_DEDICATED_MEMORY_BIT,
        .usage          = VMA_MEMORY_USAGE_AUTO,
        .preferredFlags = VK_MEMORY_PROPERTY_LAZILY_ALLOCATED_BIT,
    };
    const VkImageCreateInfo colorInfo = multisampleTargetInfo(extent, VK_FORMAT_R16G16B16A16_SFLOAT,
                                                              m_sampleCount, VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT);
    const VkImageCreateInfo depthInfo = multisampleTargetInfo(extent, m_sceneDepthFormat, m_sampleCount,
                                                              VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT);
    if (vmaCreateImage(m_context.allocator, &colorInfo, &allocationInfo,
                       &m_multisampleColorImage, &m_multisampleColorAllocation, nullptr) != VK_SUCCESS ||
        vmaCreateImage(m_context.allocator, &depthInfo, &allocationInfo,
                       &m_multisampleDepthImage, &m_multisampleDepthAllocation, nullptr) != VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for a multisampled scene target.");
    }

    VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_multisampleColorImage,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = colorInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
    };
    if (vkCreateImageView(m_device, &viewInfo, nullptr, &m_multisampleColorView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the multisampled color target.");
    }
    viewInfo.image            = m_multisampleDepthImage;
    viewInfo.format           = depthInfo.format;
    viewInfo.subresourceRange = { VK_IMAGE_ASPECT_DEPTH_BIT, 0, 1, 0, 1 };
    if (vkCreateImageView(m_device, &viewInfo, nullptr, &m_multisampleDepthView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the multisampled depth target.");
    }
    return InitializationResult::success();
}

void VulkanRenderer::destroyMultisampleTargets()
{
    vkDestroyImageView(m_device, m_multisampleColorView, nullptr);   // null is a no-op
    vkDestroyImageView(m_device, m_multisampleDepthView, nullptr);
    if (m_context.allocator != VK_NULL_HANDLE)                        // VMA asserts on a null allocator
    {
        vmaDestroyImage(m_context.allocator, m_multisampleColorImage, m_multisampleColorAllocation);
        vmaDestroyImage(m_context.allocator, m_multisampleDepthImage, m_multisampleDepthAllocation);
    }
    m_multisampleColorView       = VK_NULL_HANDLE;
    m_multisampleDepthView       = VK_NULL_HANDLE;
    m_multisampleColorImage      = VK_NULL_HANDLE;
    m_multisampleDepthImage      = VK_NULL_HANDLE;
    m_multisampleColorAllocation = VK_NULL_HANDLE;
    m_multisampleDepthAllocation = VK_NULL_HANDLE;
}
```

They are window-sized, so they follow the window exactly as the scene target
and depth do — by being made in the same place. Chapter 10's `createSceneTarget`
ends with `return InitializationResult::success();`; that line becomes

```cpp
    return createMultisampleTargets(extent);   // Chapter 18: the multisampled pair, at more than one sample
```

and `destroySceneTarget` begins with `destroyMultisampleTargets();`. Since
`recreateSwapchain` already calls those two, **resizing needs no new code**: the
multisampled pair is rebuilt at the new extent, and the demo's `Resize` receives
the new handles.

### What a demo sees of them

**This is `SceneTargets.h`.** Five fields at the end, defaulted so every
designated initializer in Chapters 09-17 still compiles:

```cpp
    // Chapter 18: what the scene pass draws into at more than one sample; null at one. beginScenePass
    // resolves them into colorView and depthView, which are what everything after the pass reads.
    VkImage               multisampleColorImage = VK_NULL_HANDLE;
    VkImageView           multisampleColorView  = VK_NULL_HANDLE;
    VkImage               multisampleDepthImage = VK_NULL_HANDLE;
    VkImageView           multisampleDepthView  = VK_NULL_HANDLE;
    VkResolveModeFlagBits depthResolveMode      = VK_RESOLVE_MODE_NONE;   // MAX where supported, else SAMPLE_ZERO
```

and **`VulkanRenderer::sceneTargets`** fills them, with `SceneFormats::samples` —
the field Chapter 09 reserved — finally set:

```cpp
SceneTargets VulkanRenderer::sceneTargets() const
{
    return SceneTargets{
        .formats               = SceneFormats{ .depth = m_sceneDepthFormat, .samples = m_sampleCount },
        .extent                = m_swapchain.extent(),   // createSceneTarget's extent
        .colorImage            = m_sceneImage,
        .colorView             = m_sceneView,
        .depthImage            = m_sceneDepthImage,      // Chapter 10
        .depthView             = m_sceneDepthView,
        .multisampleColorImage = m_multisampleColorImage,   // Chapter 18
        .multisampleColorView  = m_multisampleColorView,
        .multisampleDepthImage = m_multisampleDepthImage,
        .multisampleDepthView  = m_multisampleDepthView,
        .depthResolveMode      = m_depthResolveMode,
    };
}
```

A demo almost never touches the multisampled handles. They are in
`SceneTargets` because `beginScenePass` takes its whole description of the pass
from there, and because a demo that someday opens its own scope over the same
images (rather than the standard pass) needs them.

---

## 5. Resolving under dynamic rendering

**This is `beginScenePass`, grown** — and the reason the resolve logic exists
exactly once.

### Resolve attachments

Chapter 05 filled in `VkRenderingAttachmentInfo` with `resolveMode =
VK_RESOLVE_MODE_NONE` and moved on. Three fields have waited since then:

- **`resolveMode`** — how samples combine: `AVERAGE` for color, section 3's
  choice for depth.
- **`resolveImageView`** — the single-sample image the result goes into: the
  scene target for color, Chapter 10's depth image for depth.
- **`resolveImageLayout`** — the layout that image is in during the pass:
  `COLOR_ATTACHMENT_OPTIMAL` and `DEPTH_ATTACHMENT_OPTIMAL`.

The resolve happens when the rendering scope ends, by the hardware, at no shader
cost. The multisampled image's own `storeOp` becomes `DONT_CARE`: once resolved,
its samples are not needed, and saying so is what lets a tile-based GPU never
write them out. That is also why they are *transient*.

So at more than one sample, each attachment's `imageView` becomes the
multisampled image, its `resolveImageView` the image it used to be, and its
`storeOp` `DONT_CARE`. Chapter 09's color attachment and Chapter 10's depth
attachment each gain one `if (multisampled)` block that sets those four fields
and the mode; the depth attachment loses its `const` for it. The whole function
is printed after the barriers below, with both blocks in place.

`VkRenderingInfo` does not change: it still names one color attachment and one
depth attachment. A resolve is part of an attachment, not an attachment of its
own — which is one of the ways dynamic rendering is simpler than the render-pass
objects it replaced, where resolve attachments were a separate array that had to
line up with the color array by index.

### Why the scene target stays single-sample

The resolve's destination is **Chapter 08's scene target, unchanged** — one
sample, `R16G16B16A16_SFLOAT`, with `SAMPLED` and `STORAGE` usage. The
alternative — make the scene target itself multisampled and resolve later —
would ripple into everything: the composite shader would need a
`sampler2DMS` and a manual resolve; compute shaders would need multisampled
storage images (an optional feature); the path tracer, which writes the target
from a compute shader and never rasterizes, would have to write N samples per
pixel for no reason. Resolving inside the scene pass keeps the scene target what
it has been since Chapter 08, and so keeps **Chapter 08 section 4's contract
exactly**: the demo receives the target, leaves it in `SHADER_READ_ONLY_OPTIMAL`
with its writes visible to the fragment shader, and `handBackSceneTarget` needs
no new argument.

### Depth: resolved, not kept multisampled

The same reasoning decides depth. Later chapters read the scene's depth after
the pass — Chapter 21's soft particles, Chapter 26's occlusion culling. Keeping
depth multisampled-only would make each of them handle samples (a
`sampler2DMS`, a loop over `gl_NumSamples`, a different shader per sample count).
Resolving gives them one depth per pixel, in the image Chapter 10 created with
`SAMPLED` usage for exactly this. What they get at edges is section 3's choice,
farthest or sample 0.

### The barriers, again with three questions

Four images now take part in the pass, and each needs its start-of-frame barrier.
It helps to ask, for each: *what wrote it last frame, and what writes it now?*

**The scene target** — unchanged, and that is not an accident. At one sample the
pass draws into it; at N the resolve writes it. The spec puts **every**
multisample resolve in the `COLOR_ATTACHMENT_OUTPUT` stage with
`COLOR_ATTACHMENT_WRITE` access, in `COLOR_ATTACHMENT_OPTIMAL` — exactly what
drawing uses. So Chapter 09's barrier (last read by the composite, now written)
and `handBackSceneTarget`'s defaults (last written at `COLOR_ATTACHMENT_OUTPUT`)
are right at any sample count.

**The multisampled color** — written last frame (by draws, then by its
`DONT_CARE` store), written again now:

- Q1: `COLOR_ATTACHMENT_OUTPUT` before `COLOR_ATTACHMENT_OUTPUT`.
- Q2: a write after a write: `COLOR_ATTACHMENT_WRITE` on both sides.
- Q3: `UNDEFINED` to `COLOR_ATTACHMENT_OPTIMAL` — it is cleared.

The resolve also *read* it last frame. The store comes after the resolve's
read, so waiting for last frame's store covers it.

**The multisampled depth** — the same reasoning makes it Chapter 10's barrier
exactly: last written by the depth tests and its store, at the fragment-test
stages; the resolve's read precedes the store. One barrier serves both depth
images that the tests run on; the code picks the image.

**The single-sample depth, at N samples** — the one surprise in this chapter.
It is a *depth* image, but nothing tests depth against it any more: its only
writer is the depth **resolve**, and resolves, depth included, run at
`COLOR_ATTACHMENT_OUTPUT` with `COLOR_ATTACHMENT_WRITE`. So this barrier names
color-attachment stages and accesses for a depth image. Its source also names
the fragment-test stages. Nothing in this chapter needs them: they are for a
pass that reads this image after the scene pass, which Chapter 21 section 5 is
the first to write, and it explains them there.

Here is `beginScenePass` whole, as it now reads — Chapter 09's color barrier,
Chapter 10's depth, and this chapter's additions, each marked:

```cpp
void beginScenePass(VkCommandBuffer commandBuffer, const SceneTargets& targets,
                    const VkClearColorValue* clearColor)
{
    const bool multisampled = targets.formats.samples != VK_SAMPLE_COUNT_1_BIT;   // Chapter 18

    // Chapter 04's "Offscreen target, start of frame" row. The last reader was
    // the previous frame's composite pass, so this is a write after a read:
    // FRAGMENT_SHADER to wait for, nothing to flush.
    transitionImage(commandBuffer, targets.colorImage,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);

    // Chapter 18: the multisampled color, cleared every frame. Last frame's draws and its DONT_CARE store
    // wrote it; the store comes after the resolve's read, so waiting for writes covers that read too.
    if (multisampled)
    {
        transitionImage(commandBuffer, targets.multisampleColorImage,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    }

    // Chapter 10: the depth target, every frame, before the pass that clears it. Chapter 18: the image
    // the depth TESTS use - the single-sample one at one sample, the multisampled one above that. Either
    // way its last writers were last frame's tests and store, and this is Chapter 04's depth row.
    if (targets.depthView != VK_NULL_HANDLE)
    {
        const VkImage testedDepth = multisampled ? targets.multisampleDepthImage : targets.depthImage;
        transitionImage(commandBuffer, testedDepth,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                        VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                        VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                        VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                        VK_IMAGE_ASPECT_DEPTH_BIT);

        // Chapter 18: at more than one sample the single-sample depth is only the resolve's destination,
        // and a resolve - of depth too - writes at COLOR_ATTACHMENT_OUTPUT with COLOR_ATTACHMENT_WRITE.
        // The source also names the fragment tests, for a pass that reads this image after the scene pass
        // and hands it back (Chapter 21 section 5).
        if (multisampled)
        {
            transitionImage(commandBuffer, targets.depthImage,
                            VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                            VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT
                                | VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                            VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                            VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                            VK_IMAGE_ASPECT_DEPTH_BIT);
        }
    }

    VkRenderingAttachmentInfo colorAttachment{
        .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView   = targets.colorView,
        .imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
        .resolveMode = VK_RESOLVE_MODE_NONE,
        .loadOp      = VK_ATTACHMENT_LOAD_OP_DONT_CARE,
        .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
    };
    if (clearColor != nullptr)
    {
        colorAttachment.loadOp           = VK_ATTACHMENT_LOAD_OP_CLEAR;
        colorAttachment.clearValue.color = *clearColor;
    }

    // Chapter 18: at more than one sample, draw into the multisampled image and resolve into the scene
    // target. Only the resolved pixels are kept.
    if (multisampled)
    {
        colorAttachment.imageView          = targets.multisampleColorView;
        colorAttachment.resolveMode        = VK_RESOLVE_MODE_AVERAGE_BIT;
        colorAttachment.resolveImageView   = targets.colorView;
        colorAttachment.resolveImageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        colorAttachment.storeOp            = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    }

    // Cleared to 1.0, the far plane: every fragment that passes LESS is nearer
    // than nothing at all. Stored, not discarded, because later chapters read it
    // after the pass (particles in 21, the grass's occlusion culling in 26).
    VkRenderingAttachmentInfo depthAttachment{
        .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView   = targets.depthView,
        .imageLayout = VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
        .resolveMode = VK_RESOLVE_MODE_NONE,
        .loadOp      = VK_ATTACHMENT_LOAD_OP_CLEAR,
        .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
        .clearValue  = { .depthStencil = { 1.0f, 0 } },
    };

    // Chapter 18: the depth tests run on the multisampled depth; the resolve writes the single-sample one,
    // which is what Chapters 21 and 26 read after the pass.
    if (multisampled)
    {
        depthAttachment.imageView          = targets.multisampleDepthView;
        depthAttachment.resolveMode        = targets.depthResolveMode;
        depthAttachment.resolveImageView   = targets.depthView;
        depthAttachment.resolveImageLayout = VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL;
        depthAttachment.storeOp            = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    }

    const VkRenderingInfo renderingInfo{
        .sType                = VK_STRUCTURE_TYPE_RENDERING_INFO,
        .renderArea           = { { 0, 0 }, targets.extent },
        .layerCount           = 1,
        .viewMask             = 0,
        .colorAttachmentCount = 1,
        .pColorAttachments    = &colorAttachment,
        .pDepthAttachment     = targets.depthView != VK_NULL_HANDLE ? &depthAttachment : nullptr,
        .pStencilAttachment   = nullptr,
    };
    vkCmdBeginRendering(commandBuffer, &renderingInfo);

    // Every pipeline so far declares viewport and scissor dynamic (Chapter 06
    // section 4), and every scene pass so far covers the whole target.
    const VkViewport viewport{ 0.0f, 0.0f,
                               static_cast<float>(targets.extent.width),
                               static_cast<float>(targets.extent.height),
                               0.0f, 1.0f };
    const VkRect2D scissor{ { 0, 0 }, targets.extent };
    vkCmdSetViewport(commandBuffer, 0, 1, &viewport);
    vkCmdSetScissor(commandBuffer, 0, 1, &scissor);
}
```

Two of these are rows in Chapter 04's appendix, "Barriers the later chapters
add": the multisampled color, and the single-sample depth as the resolve
target. The multisampled depth uses the cookbook's depth row as it stands.

Getting the single-sample depth's barrier wrong is easy to do by analogy — copy
Chapter 10's fragment-test row — and synchronization validation catches it:
the exit check makes that mistake on purpose and expects
`SYNC-HAZARD-WRITE-AFTER-WRITE` from `vkCmdEndRendering`, the resolve.

### What the pass leaves behind

`endScenePass` is still `vkCmdEndRendering`. Its comment in `SceneTargets.h`
documents the last writers, which Chapter 09's contract requires and which every
later reader builds its barrier from:

```cpp
// Ends the scope. Leaves the color target in COLOR_ATTACHMENT_OPTIMAL, last written at
// COLOR_ATTACHMENT_OUTPUT with COLOR_ATTACHMENT_WRITE - by draws at one sample, by the resolve at more
// (Chapter 18), which are the same stage and access. Leaves the depth target in DEPTH_ATTACHMENT_OPTIMAL,
// last written at EARLY_ and LATE_FRAGMENT_TESTS with DEPTH_STENCIL_ATTACHMENT_WRITE at one sample
// (Chapter 10), and at COLOR_ATTACHMENT_OUTPUT with COLOR_ATTACHMENT_WRITE by the resolve at more
// (Chapter 18): a reader's barrier names both.
```

---

## 6. Every scene pipeline declares the sample count

**This is `GraphicsPipelineDesc`, `createGraphicsPipeline`, and every pipeline
that draws inside the scene pass.**

A pipeline's `rasterizationSamples` must equal the sample count of the
attachments it draws into. It is baked in at creation — one of the few states
Chapter 06 section 8 listed as never dynamic — so a pipeline built for one
sample cannot draw into a four-sample pass. Validation says so at the first draw.

Two fields join the desc, **at the end**, after `layout` (designated
initializers name fields in order, and nothing written so far names these):

```cpp
    VkSampleCountFlagBits       samples         = VK_SAMPLE_COUNT_1_BIT;   // Chapter 18: the pass's sample count
    bool                        alphaToCoverage = false;                   // Chapter 18 section 8
```

and Chapter 06's multisample state in `createGraphicsPipeline` stops being a
constant:

```cpp
    const VkPipelineMultisampleStateCreateInfo multisample{
        .sType                 = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
        .rasterizationSamples  = desc.samples,
        .alphaToCoverageEnable = desc.alphaToCoverage ? VK_TRUE : VK_FALSE,
    };
```

Which pipelines take the scene's count, and which stay at one:

| Pipeline | Draws into | Samples |
| --- | --- | --- |
| `SceneRenderer`'s mesh pipelines (11, 15) | the scene pass | `m_formats.samples` |
| `TriangleDemo`, `GradientDemo` (09) | the scene pass | `m_context.formats.samples` |
| `CubesDemo` (10) | the scene pass | `m_context.formats.samples` |
| Anything a later demo draws inside `beginScenePass` (the grass) | the scene pass | the formats' `samples` |
| The composite pass (08, 16) | the swapchain image | 1 |
| ImGui (07) | the swapchain image | 1 |
| Chapter 17's shadow casters | the shadow map | 1 |
| Anything drawn after `endScenePass` over the resolved target (21's particles) | the scene target | 1 |

The rule in one sentence: **a pipeline's sample count is its attachments', and
only the standard scene pass's attachments are multisampled.**

For the demos, it is one line each, after `.layout` in the desc their `Setup`
builds:

```cpp
        .samples        = m_context.formats.samples,   // Chapter 18: the scene pass's sample count
```

`SceneFormats::samples` reaches every `Setup` through `DemoContext`, since
Chapter 09 — this is the field's first reader. For `SceneRenderer`, section 8
shows `CreatePipelines` with this and alpha-to-coverage together.

---

## 7. Changing the sample count while running

**This is `setSampleCount`, the picker, and where `main` calls them.**

Changing the sample count replaces two kinds of object: the multisampled images,
which the renderer owns, and **every pipeline that draws in the scene pass**,
which the demos own. The second is the interesting part. The renderer cannot
rebuild a demo's pipelines — it does not know them — and asking every demo to
rebuild its pipelines in `Resize` would mean every demo, now and later, writing
code for a case most of them would never test.

Chapter 09 already has a sequence that builds a demo's pipelines from the
current formats: **`switchDemo`** — wait for the GPU, `Teardown`, `Setup` with a
fresh `DemoContext`, `Resize`. Switching to the demo that is *already* active
rebuilds everything it owns for the new sample count, through the one path every
demo already has to get right. The cost is a re-`Setup`: whatever the demo
uploads, it uploads again. Chapter 09's rule keeps that cheap — `Teardown`
releases GPU objects only, and CPU state survives in the demo object — so the USD
viewer keeps its imported scene, its inspector edits, and its camera, and
re-uploads meshes and textures without re-parsing the file (Chapter 14's
`Setup` imports only while its scene is still empty).

> **Jump:** a *setting* is now applied by tearing the demo down and setting it
> up again. Until now `Setup` ran when you picked a demo, and `Resize` when the
> window changed; from here `Setup` is also how any change to `SceneFormats`
> reaches a demo, and a demo must treat Teardown-then-Setup as routine, not as
> leaving. That is what Chapter 09's "Setup → Teardown → Setup must work" rule
> was for. Keep it in mind when a later chapter adds CPU state to a demo: if it
> must survive a sample-count change, it lives in the demo object, not in
> anything `Teardown` releases.

```cpp
// VulkanRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 18).
void VulkanRenderer::setSampleCount(VkSampleCountFlagBits samples)
{
    if (samples == m_sampleCount) { return; }

    // The multisampled images and every scene pipeline are about to be replaced, and a frame in flight
    // may still be using them. A click in a panel, like a resize: one stall is fine.
    vkDeviceWaitIdle(m_device);
    destroyMultisampleTargets();
    m_sampleCount = samples;
    if (const auto created = createMultisampleTargets(m_swapchain.extent()); !created)
    {
        // Back to one sample, which needs no images of its own, so frames can still be drawn. The
        // picker then shows 1x, and the log says why.
        Log::error(std::format("MSAA {}x: {}", static_cast<uint32_t>(samples), created.message()).c_str());
        destroyMultisampleTargets();
        m_sampleCount = VK_SAMPLE_COUNT_1_BIT;
    }

    // Pipelines are built only in a demo's Setup, from DemoContext::formats (Chapter 09). Setting the
    // active demo up again is the one route that rebuilds all of them, whoever owns them.
    switchDemo(m_demo);
}
```

It returns nothing, like `switchDemo`, and for the same reason: the program
carries on whatever happens. Two things can fail. The multisampled images can
fail to allocate, and then the renderer falls back to one sample, which needs
none, and logs why. Or the demo's re-`Setup` can fail at the new count, and
then `switchDemo` detaches it, exactly as Chapter 09 section 5 does for any
failed switch, and `demoError()` says why in the demo picker. `switchDemo(m_demo)`
passes the pointer by value before `switchDemo` clears `m_demo`, so tearing the
demo down and setting the same one up again needs nothing special.

Only the multisampled pair is rebuilt. The scene target and depth do not depend
on the sample count, so Chapter 08's composite set, which points at the scene
target, does not need rewriting — Chapter 08 section 6's rule for re-pointing a
descriptor never comes up. A demo's own descriptors that point at the targets
are rebuilt by its `Resize`, which `switchDemo` calls.

**The deletion-queue question, answered for this case.** Chapter 06 section 8
said that changing a pipeline at runtime means destroying one an in-flight frame
may still use, which needs a small deletion queue — or a wait. A deletion queue
lets a frame keep running while its old objects age out; it is the right tool
when changes are frequent (shader hot reload, streaming). A sample-count change
happens when someone clicks a combo box. `vkDeviceWaitIdle` costs one frame's
latency at that moment, which nobody can see, and makes the code obviously
correct. The queue stays deferred, as ROADMAP has it.

### The picker

The sample count gets a combo box that lists only what the GPU supports, so an
unsupported count cannot be asked for. It goes in a small window of its own,
"MSAA", to the right of the Frame panel; the comment in the code says why not
inside Frame.

```cpp
// Source/PillowFort/DebugPanels/ImGuiDebugPanels.h, beside drawPresentModePicker (Chapter 18).
    bool drawSampleCountPicker(std::span<const VkSampleCountFlagBits> supported,
                               VkSampleCountFlagBits& current);
```

```cpp
// ImGuiDebugPanels.cpp, beside drawPresentModePicker (Chapter 18). True when the user picked another count.
bool ImGuiDebugPanels::drawSampleCountPicker(std::span<const VkSampleCountFlagBits> supported,
                                             VkSampleCountFlagBits& current)
{
    bool changed = false;

    // A small window of its own, right of "Frame": a row added to "Frame" would push its bottom edge
    // under the panels that Chapters 09, 10, and 20 open at y = 220.
    ImGui::SetNextWindowPos(ImVec2(360.0f, 10.0f), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("MSAA", nullptr, ImGuiWindowFlags_AlwaysAutoResize))
    {
        const std::string label = std::format("{}x", static_cast<uint32_t>(current));
        ImGui::SetNextItemWidth(ImGui::GetFontSize() * 5.0f);   // "64x" and the arrow
        if (ImGui::BeginCombo("Samples per pixel", label.c_str()))
        {
            for (const VkSampleCountFlagBits count : supported)
            {
                const std::string name = std::format("{}x", static_cast<uint32_t>(count));
                if (ImGui::Selectable(name.c_str(), count == current))
                {
                    changed = count != current;
                    current = count;
                }
            }
            ImGui::EndCombo();
        }
    }
    ImGui::End();
    return changed;
}
```

`AlwaysAutoResize` sizes the window to its one row, and the fixed width keeps
the combo from stretching across the screen. `ImGuiDebugPanels.cpp` gains
`<format>` and `<string>` if it does not have them.

### Where `main` calls it

The change re-runs the demo's `Setup`, so it belongs exactly where Chapter 09
put the demo switch: **before `Update`**, so a demo is never torn down after it
has drawn ImGui widgets that this frame will still render. Right after the demo
picker:

```cpp
        // Chapter 18: the scene's sample count. Applying it sets the demo up again, so it happens here, with
        // the demo switch, before Update draws the demo's panels.
        VkSampleCountFlagBits sampleCount = renderer.sampleCount();
        if (renderer.debugPanels().drawSampleCountPicker(renderer.supportedSampleCounts(), sampleCount))
        {
            renderer.setSampleCount(sampleCount);
        }
```

A demo that fails to set up again at the new count lands in the demo picker's
status line, through `renderer.demoError()`, as a failed switch does — because
it *is* one.

---

## 8. Alpha-to-coverage for cutouts

Turn on 4× and look at Chapter 17's leaf fence. The **geometry**'s edges — the
quad's border, which is cut away anyway — would be smooth. The **leaves**' edges
are as jagged as at 1×.

**Why.** A cutout's edge is not a triangle edge; it is a line *inside* the
triangle where the texture's alpha crosses the threshold. MSAA decides coverage
per sample from geometry, and every sample of a pixel inside the quad is covered.
Then the fragment shader runs once and `discard`s or not — for the whole pixel.
So the alpha edge is decided once per pixel: exactly the aliasing MSAA was meant
to remove, reintroduced by the shader.

**Alpha-to-coverage** moves that decision back into coverage. With
`alphaToCoverageEnable` set, the fragment's output alpha becomes a **coverage
mask**: an alpha of 0.5 at 4× keeps two of the four samples, 0.25 keeps one. The
covered samples get the color; the resolve averages them with whatever is behind
— a soft, anti-aliased edge — and the uncovered samples write neither color nor
depth, so what is behind them stays visible and stays in the depth buffer.

**The alpha has to be shaped first.** A texture's alpha changes smoothly over
several texels, so feeding it in raw gives a blurry, semi-transparent band, the
width of a texel when magnified and wider in the distance. What is wanted is an
edge **one pixel wide** at the threshold. `fwidth(opacity)` is how much opacity
changes from this pixel to the next. The GPU knows it because it shades pixels
in 2x2 quads and can subtract a neighbour's value from this one (Chapter 15
section 5). That change per pixel is exactly the scale for a one-pixel edge:

```text
 coverage = (opacity - threshold) / fwidth(opacity) + 0.5        then clamped to [0, 1]
```

A worked example. The threshold is 0.5, and across this part of the leaf the
opacity changes by 0.2 from one pixel to the next, so `fwidth` is 0.2:

```text
 opacity                       0.40     0.45     0.50     0.55     0.60
 (opacity - 0.5) / 0.2         -0.5    -0.25      0.0     0.25      0.5
 + 0.5, clamped: coverage       0.0     0.25      0.5     0.75      1.0
 samples kept, at 4x         0 of 4   1 of 4   2 of 4   3 of 4   4 of 4
```

At the threshold the coverage is 0.5. Half a pixel's worth of change either
side (0.1 of opacity here) takes it to 0 or to 1, so the soft band is one pixel
wide in total. The edge lands where `discard` would have put it, and is a pixel
wide at any distance: far away `fwidth` is larger, and the same division keeps
the band one pixel wide.

### In `Mesh.frag.glsl`

Chapter 15 put the cutout behind specialization constant 1. Alpha-to-coverage
is constant 2 — Chapter 15 reserved it — beside the other two declarations:

```glsl
layout(constant_id = 2) const bool alphaToCoverage = false;   // Chapter 18: cutout edges as coverage
```

Chapter 15's first three lines of `main` — the comment, `opacity`, and the
`discard` — are replaced by:

```glsl
    // Cut out first: nothing below matters for a discarded pixel. Chapter 18: with alpha-to-coverage the
    // edge becomes sample coverage instead, sharpened so it is one pixel wide at any distance.
    float opacity  = materialOpacity(uv);
    float coverage = 1.0;
    if (alphaCutout)
    {
        if (alphaToCoverage)
        {
            coverage = clamp((opacity - material.opacityThreshold) / max(fwidth(opacity), 1e-4) + 0.5, 0.0, 1.0);
        }
        else if (opacity < material.opacityThreshold)
        {
            discard;
        }
    }
```

and the output's alpha, which has been 1.0, carries it:

```glsl
    outColor = vec4(min(color, vec3(64000.0)), coverage);
```

`max(fwidth(opacity), 1e-4)` keeps a perfectly flat opacity (an untextured cutout
material) from dividing by zero. `fwidth` needs the other pixels of the 2x2 quad
(Chapter 15 section 5), which is why it must be computed before any `discard` in
the same branch could remove them; with alpha-to-coverage on there is no discard
at all.

The scene target's alpha channel now holds coverage values instead of 1.0.
Nothing reads it — the composite pass outputs alpha 1.0 (Chapter 08) — so that is
harmless.

### In `CreatePipelines`

Chapter 15's `MeshSpecialization` gains its third member, the map its third
entry, and the desc the two fields from section 6:

```cpp
// In CreatePipelines (Chapter 15, grown in Chapter 18): the three constants the mesh fragment shader declares.
struct MeshSpecialization
{
    uint32_t shadingMode     = 0;          // constant_id 0
    VkBool32 alphaCutout     = VK_FALSE;   // constant_id 1 - a GLSL bool is a 4-byte VkBool32
    VkBool32 alphaToCoverage = VK_FALSE;   // constant_id 2 - Chapter 18
};
const VkSpecializationMapEntry meshEntries[] = {
    { .constantID = 0, .offset = offsetof(MeshSpecialization, shadingMode), .size = sizeof(uint32_t) },
    { .constantID = 1, .offset = offsetof(MeshSpecialization, alphaCutout), .size = sizeof(VkBool32) },
    { .constantID = 2, .offset = offsetof(MeshSpecialization, alphaToCoverage), .size = sizeof(VkBool32) },
};

// Chapter 18: alpha-to-coverage needs samples to cover. At one sample a cutout keeps its discard.
const bool multisampled = m_formats.samples != VK_SAMPLE_COUNT_1_BIT;
```

In the loop over modes and cutout, the values and the desc:

```cpp
        const bool               toCoverage = cutout && multisampled;
        const MeshSpecialization values{
            .shadingMode     = mode,
            .alphaCutout     = cutout ? VK_TRUE : VK_FALSE,
            .alphaToCoverage = toCoverage ? VK_TRUE : VK_FALSE,
        };
        const VkSpecializationInfo specialization{
            .mapEntryCount = 3,
            .pMapEntries   = meshEntries,
            .dataSize      = sizeof(values),
            .pData         = &values,
        };
```

and Chapter 11's mesh desc, with `.fragmentSpecialization = &specialization`
as Chapter 15 left it, gains after `.layout`:

```cpp
            .samples                = m_formats.samples,   // Chapter 18
            .alphaToCoverage        = toCoverage,
```

Pipeline state and shader constant are set together, on the same condition. The
state without the constant would cover with the raw, blurry alpha; the constant
without the state would write a coverage value that nothing turns into a mask and
cut nothing out.

### Its limits

- **N + 1 levels.** At 4× a pixel can be 0, 25, 50, 75, or 100% covered. That
  is plenty for an edge a pixel wide, and nowhere near enough for real
  translucency — it is not blending.
- **The counts are the intent, not the rule.** Vulkan specifies no algorithm
  for turning alpha into a mask, only that the samples kept are meant to be
  proportional to alpha, and it lets the algorithm differ from pixel to pixel.
  A desktop GPU may dither, keeping more samples in one pixel and fewer in the
  next, so this section's counts — 0.25 keeps one of four — hold on average
  rather than in every pixel. The edge is soft either way.
- **At one sample it is a threshold.** With one sample, the coverage mask is the
  sample or nothing, at an implementation-defined alpha — usually 0.5. Rather
  than depend on that, the pipelines above keep `discard` at 1×.
- **The shadow pass still discards.** Chapter 17's shadow map has one sample,
  so its cutout casters keep their `discard`.

### Aside: sample shading

Shading aliasing — a highlight smaller than a pixel — survives MSAA because the
shader runs once per pixel. **Sample shading** runs it per *sample* instead:
`sampleShadingEnable = VK_TRUE` and `minSampleShading = 1.0` in the
multisample state shade every sample separately, so a 4× pass shades four times
as much. It needs the `sampleRateShading` device feature (Vulkan 1.0; enable it
in Chapter 02's `CreateDevice` beside the others). It is the brute-force answer
— supersampling, paid only where triangles are — and the cost is why shipping
renderers prefer to filter the shading itself (for example, widening roughness
where the normal map varies within a pixel) and then use temporal AA. It is not
built here.

---

## 9. What MSAA cannot fix

Load Chapter 17's test scene at 4× and fly back from the pole fence until the
poles are thinner than a pixel. The 3 cm poles and 2 cm wires come and go as
dashes: four samples a pixel is still a grid, and a line narrower than its
spacing slips between the samples. The grass will be thousands of such lines.

The general answer is **temporal anti-aliasing** (TAA): offset the projection by
a different sub-pixel amount every frame (a *jitter*), so successive frames
sample different points, and blend each frame with the history of previous
ones. Over a few frames, every pixel has seen many sample positions — far more
than MSAA's four — at the shading cost of one. It also smooths shading and
specular aliasing, which MSAA cannot touch.

Its price is why it would need a chapter of its own; this tutorial names it and
does not build it. What it costs:

- **Reprojection.** When the camera or an object moves, last frame's pixel is
  somewhere else. TAA needs per-pixel **motion vectors** — an extra render
  target the scene pass writes — to find it.
- **Ghosting and blur.** History that no longer matches (something moved in
  front, or was uncovered) must be rejected, usually by clamping it to the range
  of colors around the current pixel. Getting that wrong smears moving objects or
  softens the whole image.
- **It changes the frame's structure.** A jittered projection, a history image
  per frame in flight, and a resolve pass between the scene and the composite.

TAA is the next step for the grass chapters, and it is on the index's
[list of things named but not built](../VulkanTutorial.md#named-not-built).
MSAA stays useful beside it — many engines run both — and it is what makes
geometric edges correct *within* a frame, which TAA can only approximate over
time.

---

## Exit check

- [ ] Startup logs the sample count and the depth resolve mode, for example
      `MSAA: 4x; depth resolves by VK_RESOLVE_MODE_MAX_BIT` on a desktop
      driver (lavapipe reports only `SAMPLE_ZERO`).
- [ ] Chapter 17's `ShadowTest.usda` at 1× and at 4×, from the starting camera:
      screenshots of the same crop around the pole fence, the wires, and the
      leaf fence. At 4× pole and box silhouettes are smooth and the leaves'
      edges are soft; at 1× both are staircases.
- [ ] At 4×, switching `alphaToCoverage` off in `CreatePipelines` (temporarily:
      `toCoverage = false`) brings the leaves' jagged edges back while the
      geometry stays smooth — the screenshots this check compares. Put it back.
- [ ] Changing the sample count in the MSAA window, repeatedly, while the USD
      viewer runs: the scene keeps its camera and inspector edits, and there
      are no validation messages. The MSAA window sits right of the Frame
      panel, and no other panel covers either of them.
- [ ] Resizing, minimizing, and restoring at 4× are validation-clean, and the
      image is never stretched.
- [ ] `--msaa 3` starts at 2× with a warning (or at 1× where 2 is missing).
- [ ] **The resolve barrier is proven.** Temporarily give the single-sample
      depth's barrier in `beginScenePass` Chapter 10's row — source and
      destination `EARLY_FRAGMENT_TESTS | LATE_FRAGMENT_TESTS` with depth
      accesses — and run at 4×: synchronization validation must report
      `SYNC-HAZARD-WRITE-AFTER-WRITE` at `vkCmdEndRendering` (the resolve).
      Put it back.
- [ ] Chapter 17's shadows still work at 4×: the shadow pass is one sample and
      does not care.

Next: [19 — Instancing and Indirect Draws](19-Instancing-And-Indirect.md)
