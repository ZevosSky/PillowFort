# 04 — Commands and Synchronization

**Goal:** understand frames in flight well enough that the compute and
rendering chapters from 20 on are about algorithms rather than about
debugging hazards.

**ROADMAP:** step 5.

**Module:** `VulkanGraphics`, namespace `pf::vulkan_graphics`.

**Prerequisites:** Chapter 02 (`VulkanInstance` and its accessors) and Chapter
03 (`VulkanSwapchain`, and section 7's three recreation triggers, which
`drawFrame` here calls). Like them, this chapter builds but does not run until
Chapter 05.

This is the chapter to read slowly. Synchronization is the only part of Vulkan
where a wrong program runs correctly on your machine for weeks and then
corrupts on someone else's. The barrier cookbook at the end of section 5 covers
Chapters 05-10; the rows the later chapters add are in this chapter's appendix,
for when they send you there.

---

## What you are actually writing

Chapters 02 and 03 built things that exist once. This chapter builds the thing
that runs every frame, and it needs an owner: **`VulkanRenderer`**. It holds the
`VulkanInstance` and `VulkanSwapchain`, owns the per-frame resources, and its
`drawFrame` is section 4. Section 3's semaphores are the exception — they
belong to `VulkanSwapchain`, for reasons that section explains.

```cpp
// Source/PillowFort/VulkanGraphics/VulkanRenderer.h
// This class grows: Chapter 05 adds recordFrame, Chapter 06 a pipeline,
// Chapter 07 the debug panels.

static constexpr uint32_t FRAMES_IN_FLIGHT = 2;

enum class FrameStatus
{
    Presented,   // drew and presented
    Skipped,     // swapchain was recreated or the window is minimized; try again next frame
    Failed,      // unrecoverable
};

// What main chooses at startup (Chapter 05 parses it from the command line).
struct RendererSettings
{
    std::string      preferredGpu;                                 // part of a device name; empty = automatic
    VkPresentModeKHR presentMode = VK_PRESENT_MODE_FIFO_KHR;       // FIFO if the surface lacks it
};

struct FrameResources                                  // section 2
{
    VkCommandPool   commandPool    = VK_NULL_HANDLE;
    VkCommandBuffer commandBuffer  = VK_NULL_HANDLE;
    VkFence         inFlightFence  = VK_NULL_HANDLE;   // GPU finished this frame's work
    VkSemaphore     imageAvailable = VK_NULL_HANDLE;   // acquire completed
};

class VulkanRenderer
{
public:
    VulkanRenderer() = default;
    VulkanRenderer(const VulkanRenderer&) = delete;
    VulkanRenderer& operator=(const VulkanRenderer&) = delete;

    InitializationResult initialize(GLFWwindow* window, const RendererSettings& settings);   // section 2
    FrameStatus drawFrame(const FrameRequest& request);      // section 4
    void notifyFramebufferResized() { m_framebufferResized = true; }
    void shutdown();                                         // section 6

private:
    InitializationResult createFrameResources(FrameResources& frame);    // sections 1-2
    RecreateResult recreateSwapchain();                                   // section 4
    InitializationResult recordFrame(VkCommandBuffer commandBuffer, uint32_t imageIndex,
                                     const FrameRequest& request);        // Chapter 05

    VulkanInstance  m_vulkan;                            // Chapter 02
    VulkanSwapchain m_swapchain;                         // Chapter 03

    // Borrowed from m_vulkan, cached because every function here uses them.
    VkDevice m_device        = VK_NULL_HANDLE;
    VkQueue  m_graphicsQueue = VK_NULL_HANDLE;

    std::array<FrameResources, FRAMES_IN_FLIGHT> m_frames;
    uint32_t m_frameIndex         = 0;
    bool     m_framebufferResized = false;
};
```

`FrameRequest` is Chapter 05's — a struct holding the clear color. Until you get
there it can be an empty `struct FrameRequest {};` in
`Source/PillowFort/VulkanGraphics/FrameRequest.h`, inside the same namespace.

The header sits inside `namespace pf::vulkan_graphics` and includes
`FrameRequest.h`, `VulkanInstance.h`, `VulkanSwapchain.h`, `<array>`, and
`<string>`. It holds the other two classes by value, so a forward declaration
will not do here.

This class owns the frame pools, fences and acquire semaphores. Copying their
handle values would create two owners that both destroy the same objects, so
copy construction and assignment are deleted. The explicit default
constructor keeps ordinary construction available; borrowed handles in a
context or view remain copyable.

---

## 1. Command pools and command buffers

**This is `createFrameResources`, first half.** A `VkCommandPool` is an
allocator for command buffers, and it is **not thread-safe**. One pool per
thread that records, per frame in flight.

```cpp
InitializationResult VulkanRenderer::createFrameResources(FrameResources& frame)
{
    const VkCommandPoolCreateInfo poolInfo{
        .sType            = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        .flags            = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT,
        .queueFamilyIndex = m_vulkan.GraphicsFamily(),
    };
    VkCommandPool commandPool = VK_NULL_HANDLE;
    if (vkCreateCommandPool(m_device, &poolInfo, nullptr, &commandPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateCommandPool failed.");
    }
    frame.commandPool = commandPool;

    const VkCommandBufferAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool        = frame.commandPool,
        .level              = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
        .commandBufferCount = 1,
    };
    if (vkAllocateCommandBuffers(m_device, &allocateInfo, &frame.commandBuffer) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateCommandBuffers failed.");
    }

    // >>> Section 2 continues this function here: the fence and the semaphore. <<<
}
```

**Reset the pool, not the buffer.** Two ways to recycle:

| Approach | Flags | Behavior |
| --- | --- | --- |
| `vkResetCommandPool` | `TRANSIENT_BIT` | Resets every buffer in the pool at once and can return memory to the pool wholesale. Faster. |
| `vkResetCommandBuffer` | `RESET_COMMAND_BUFFER_BIT` | Per-buffer reset. Forces the driver into a per-buffer allocation strategy, which is slower for *every* buffer in the pool. |

With one pool per frame in flight, `vkResetCommandPool(device, frame.commandPool, 0)`
once the slot's fence wait has passed is both simpler and faster. Do not set
`RESET_COMMAND_BUFFER_BIT` — it is a pessimization you pay for even if you
never call the function.

`TRANSIENT_BIT` tells the driver these buffers are short-lived, which is
accurate: you re-record every one, every frame. It is only a hint; the table
pairs it with the pool reset because both suit this pattern, but
`vkResetCommandPool` itself needs no creation flag.

**Recording a command buffer while the GPU is still executing it is undefined
behavior.** That single sentence is what frames in flight exist to prevent.

---

## 2. Frames in flight

Without any overlap, your frame looks like this, and both processors are idle
half the time:

```text
CPU:  [record][wait...............][record][wait..............]
GPU:  [.......][execute][present..][.......][execute][present.]
```

With two frames in flight, the CPU records frame N+1 while the GPU executes
frame N. You need two of everything the CPU touches while the GPU is busy —
which is the `FrameResources` struct and the `m_frames` array in the class
above.

Two is the right number. Three trades latency for throughput and is worth
measuring later; one defeats the purpose.

**This is `createFrameResources`, second half.** Create the fence **already
signalled**, so frame 0 does not deadlock waiting for work that never happened:

```cpp
const VkFenceCreateInfo fenceInfo{
    .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
    .flags = VK_FENCE_CREATE_SIGNALED_BIT,
};
VkFence inFlightFence = VK_NULL_HANDLE;
if (vkCreateFence(m_device, &fenceInfo, nullptr, &inFlightFence) != VK_SUCCESS)
{
    return InitializationResult::failure("vkCreateFence failed.");
}
frame.inFlightFence = inFlightFence;

const VkSemaphoreCreateInfo semaphoreInfo{
    .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO,
};
VkSemaphore imageAvailable = VK_NULL_HANDLE;
if (vkCreateSemaphore(m_device, &semaphoreInfo, nullptr, &imageAvailable) != VK_SUCCESS)
{
    return InitializationResult::failure("vkCreateSemaphore failed.");
}
frame.imageAvailable = imageAvailable;

return InitializationResult::success();
}
```

A scalar `vkCreate*` writes into a local handle, and only `VK_SUCCESS` publishes
it to the owning member. On failure, the
[general error-output rule](https://docs.vulkan.org/spec/latest/chapters/fundamentals.html#fundamentals-errorcodes)
leaves that output undefined; initializing the member to null beforehand is
not enough. The successful prefix stays owned for `shutdown` to release.
[`vkAllocateCommandBuffers`](https://docs.vulkan.org/refpages/latest/refpages/source/vkAllocateCommandBuffers.html)
is an explicit exception: it frees a failed allocation's prefix and returns
null entries, so its direct write to `frame.commandBuffer` above is safe.

`imageAvailable` is per frame in flight, and that is correct: the only thing
that waits on it is this frame's own submit, and by the next visit to this
slot the fence wait at the top of `drawFrame` has seen that submit complete,
so the semaphore is unsignalled and free to reuse. Its partner,
`renderFinished`, is waited on by the presentation engine, which no fence of
ours tracks; that one is *not* per frame, and it is the next section.

**This is `initialize`.** It brings up its three parts in dependency order: the
instance, the swapchain built from it, then each slot's frame resources:

```cpp
InitializationResult VulkanRenderer::initialize(GLFWwindow* window, const RendererSettings& settings)
{
    // Chapter 01's premake defines this in Debug only.
#ifdef PF_VULKAN_VALIDATION
    constexpr bool enableValidation = true;
#else
    constexpr bool enableValidation = false;
#endif

    if (auto result = m_vulkan.Initialize(window, enableValidation, settings.preferredGpu); !result)
    {
        return result;
    }

    // Cached before anything else can fail, so shutdown() sees the device.
    m_device        = m_vulkan.Device();
    m_graphicsQueue = m_vulkan.GraphicsQueue();

    if (auto result = m_swapchain.initialize(m_vulkan, window, settings.presentMode); !result)
    {
        return result;
    }

    for (FrameResources& frame : m_frames)
    {
        if (auto result = createFrameResources(frame); !result) { return result; }
    }
    return InitializationResult::success();
}
```

As with `VulkanInstance`, a failed `initialize` is still followed by
`shutdown()`, which section 6 makes safe.

---

## 3. The semaphore trap

Here is the mistake that is in a great many Vulkan tutorials, including older
versions of the canonical one, and that you will reproduce from memory if you
are not warned.

The obvious design is one `renderFinished` semaphore per *frame in flight*,
alongside the fence and the `imageAvailable` semaphore. It runs fine. It is
also invalid, and the validation layer will eventually say so.

> **Jump:** from here on, hold two counters apart. The **frame slot**,
> `m_frameIndex`, is yours: it runs 0, 1, 0, 1, and picks which
> `FrameResources` — command pool, fence, `imageAvailable` — this frame uses.
> The **image index** comes back from `vkAcquireNextImageKHR` every frame: it
> runs from 0 to the swapchain's image count minus one, in whatever order the
> driver likes, and picks the swapchain image, its view, and (after this
> section) its `renderFinished` semaphore. With more images than slots, which
> is the usual case, the two never stay in step. The bug below is a resource
> that follows the wrong counter.

**Why it breaks.** Take 2 frames in flight and 3 swapchain images:

| Frame | Slot | Image | Signals | Waited by |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | `renderFinished[0]` | present of image 0 |
| 1 | 1 | 1 | `renderFinished[1]` | present of image 1 |
| 2 | 0 | 2 | `renderFinished[0]` again | present of image 2 |

Before frame 2 submits, it waits on `inFlightFence[0]`. That fence guarantees
frame 0's **rendering** finished — it says nothing about whether the
**presentation engine** has consumed `renderFinished[0]` yet. If it has not,
you are signalling an already-signalled binary semaphore, which is undefined
behavior.

**The fix: one `renderFinished` semaphore per swapchain image.**

Because they are sized by the image count and must die with the swapchain,
`VulkanSwapchain` owns them — right beside the image views, created and
destroyed at the same points: `initialize` and `recreate` create both,
`recreate` and `shutdown` destroy both. It is the only class that already knows
the real count.

```cpp
// Source/PillowFort/VulkanGraphics/VulkanSwapchain.cpp
// Sized from vkGetSwapchainImagesKHR, NOT from FRAMES_IN_FLIGHT,
// and NOT from the minImageCount you requested.
InitializationResult VulkanSwapchain::createRenderFinishedSemaphores()
{
    const VkSemaphoreCreateInfo semaphoreInfo{
        .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO,
    };

    m_renderFinished.assign(m_images.size(), VK_NULL_HANDLE);   // actual image count, not frame count
    for (VkSemaphore& semaphore : m_renderFinished)
    {
        VkSemaphore created = VK_NULL_HANDLE;
        const VkResult result = vkCreateSemaphore(m_device, &semaphoreInfo, nullptr, &created);
        if (result != VK_SUCCESS)
        {
            destroyRenderFinishedSemaphores();   // release the successful prefix; discard failed output
            return InitializationResult::failure(
                std::format("Creating a swapchain render-finished semaphore failed: {}", string_VkResult(result)));
        }
        semaphore = created;
    }
    return InitializationResult::success();
}

void VulkanSwapchain::destroyRenderFinishedSemaphores()
{
    for (VkSemaphore semaphore : m_renderFinished)
    {
        if (semaphore != VK_NULL_HANDLE) { vkDestroySemaphore(m_device, semaphore, nullptr); }
    }
    m_renderFinished.clear();
}

// The renderer reaches them the same way it reaches images and views.
VkSemaphore VulkanSwapchain::renderFinished(uint32_t imageIndex) const
{
    return m_renderFinished[imageIndex];
}
```

`recreate()` in [Chapter 03](03-Swapchain.md) calls these alongside
`destroyImageViews()` and `createImageViews()`. Forgetting that half is this
section's second bug: the count changes, the vector does not, and you index
past the end of it. Chapter 05's stress table has a row for
exactly this.

The returned image index alone is not the completion signal. This frame's
submit waits on that acquire's `imageAvailable` semaphore before its attachment
work. Completing that wait guarantees the previous presentation using image
`i` has completed, including its wait on `renderFinished[i]`. This frame can
then signal that image's semaphore again, ordered after the acquire wait.
That is the reuse proof in Khronos's
[Swapchain Semaphore Reuse guide](https://docs.vulkan.org/guide/latest/swapchain_semaphore_reuse.html#_discussion_of_solution).

> Timeline semaphores solve this class of problem generally, and are core in
> Vulkan 1.2. They cannot be used for present, which still requires binary
> semaphores, so you would end up with both. ROADMAP parks them deliberately;
> Chapter 29 notes where they would start to pay off.

---

## 4. The frame, in order

**This is `drawFrame`**, whole. `m_swapchain` is the `VulkanSwapchain` object
from Chapter 03, so the raw handle is `m_swapchain.handle()`. Submit and
present both go to `m_graphicsQueue`, because Chapter 02 chose one family
that does graphics and presentation.

<a id="ch04-frame-order"></a>

**Attempt CH04-frame-order: make early exits safe.** Sketch the frame as a
sequence, then implement it before opening the answer. The previous use of
this frame slot must finish before you reuse its command pool; submission
must wait for the acquired image and signal that image's `renderFinished`
semaphore. If acquire says `OUT_OF_DATE`, return through recreation without
leaving an unsignalled fence that no submission will signal. Treat
`SUBOPTIMAL` as a usable image and other acquire failures as failures. Trace
two visits to the same slot, with an out-of-date acquire on the first: the
second visit must be able to pass its fence wait. Chapter 05 provides the
runtime resize check once `recordFrame` exists.

**Acceptance:** Both visits to the slot complete even when the first acquire is OUT_OF_DATE; pool reuse waits for prior work, and a usable image reaches submission/presentation.

**Transfer:** Replace OUT_OF_DATE with SUBOPTIMAL in the trace. Predict whether work is submitted and which fence will signal before checking the changed path.

<details>
<summary>Hint 1: a reset fence needs a future signal</summary>

Waiting on the slot's old fence is safe at the start. Resetting it is a
promise that this attempt will submit work which signals it. An acquire
failure can invalidate that promise.

</details>

<details>
<summary>Hint 2: separate acquiring an image from committing a submission</summary>

Wait, acquire, and handle unusable results first. Reset the pool and record
while the fence is still signalled. Only successful recording may reset the
fence and proceed to submission. Advance the frame slot after the submitted
frame, not after an acquire that produced no usable image.

</details>

<details>
<summary>Hint 3: use the two different indices for their two jobs</summary>

`m_frameIndex` selects the command pool, acquire semaphore and fence.
`imageIndex` selects `m_swapchain.renderFinished(imageIndex)`. The acquire
wait is at `COLOR_ATTACHMENT_OUTPUT` and the `renderFinished` signal at
`ALL_COMMANDS`; section 5 explains both, and how the image's first barrier
must match that wait.

</details>

<details>
<summary>Worked solution: the frame and its early exits</summary>

```cpp
FrameStatus VulkanRenderer::drawFrame(const FrameRequest& request)
{
    FrameResources& frame = m_frames[m_frameIndex];

    // 1. Wait until this slot's previous work finished, so its command buffer is reusable.
    if (vkWaitForFences(m_device, 1, &frame.inFlightFence, VK_TRUE, UINT64_MAX) != VK_SUCCESS)
    {
        return FrameStatus::Failed;
    }

    // 2. Ask for an image. Returns immediately; the semaphore signals when it is safe.
    uint32_t imageIndex = 0;
    const VkResult acquireResult = vkAcquireNextImageKHR(
        m_device, m_swapchain.handle(), UINT64_MAX, frame.imageAvailable, VK_NULL_HANDLE, &imageIndex);

    if (acquireResult == VK_ERROR_OUT_OF_DATE_KHR)
    {
        // Fence NOT reset, nothing submitted, semaphore not signalled.
        return recreateSwapchain() == RecreateResult::Failed ? FrameStatus::Failed
                                                             : FrameStatus::Skipped;
    }
    // SUBOPTIMAL still gave us a usable image, so keep going and handle it after
    // present. Anything else - DEVICE_LOST, SURFACE_LOST_KHR - left imageIndex
    // untouched, and submitting against it is how a driver error becomes a crash.
    if (acquireResult != VK_SUCCESS && acquireResult != VK_SUBOPTIMAL_KHR)
    {
        return FrameStatus::Failed;
    }

    // 3. Recycle and record while this slot's fence is still signalled.
    if (vkResetCommandPool(m_device, frame.commandPool, 0) != VK_SUCCESS)
    {
        return FrameStatus::Failed;
    }
    if (auto recorded = recordFrame(frame.commandBuffer, imageIndex, request); !recorded)
    {
        // Nothing from this attempt was submitted. Failed is terminal: main
        // stops; it must not retry with this acquired image/semaphore.
        return FrameStatus::Failed;
    }

    // 4. Recording succeeded. Only now consume the fence's signalled state.
    if (vkResetFences(m_device, 1, &frame.inFlightFence) != VK_SUCCESS)
    {
        return FrameStatus::Failed;
    }

    // 5. Submit.
    const VkSemaphoreSubmitInfo waitInfo{
        .sType     = VK_STRUCTURE_TYPE_SEMAPHORE_SUBMIT_INFO,
        .semaphore = frame.imageAvailable,
        .value     = 0,                                          // ignored for binary semaphores
        .stageMask = VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
    };

    const VkSemaphoreSubmitInfo signalInfo{
        .sType     = VK_STRUCTURE_TYPE_SEMAPHORE_SUBMIT_INFO,
        .semaphore = m_swapchain.renderFinished(imageIndex),
        .value     = 0,
        .stageMask = VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT,
    };

    const VkCommandBufferSubmitInfo commandInfo{
        .sType         = VK_STRUCTURE_TYPE_COMMAND_BUFFER_SUBMIT_INFO,
        .commandBuffer = frame.commandBuffer,
    };

    const VkSubmitInfo2 submitInfo{
        .sType                    = VK_STRUCTURE_TYPE_SUBMIT_INFO_2,
        .waitSemaphoreInfoCount   = 1,
        .pWaitSemaphoreInfos      = &waitInfo,
        .commandBufferInfoCount   = 1,
        .pCommandBufferInfos      = &commandInfo,
        .signalSemaphoreInfoCount = 1,
        .pSignalSemaphoreInfos    = &signalInfo,
    };

    if (vkQueueSubmit2(m_graphicsQueue, 1, &submitInfo, frame.inFlightFence) != VK_SUCCESS)
    {
        return FrameStatus::Failed;
    }

    // 6. Present. pWaitSemaphores and pSwapchains take addresses, so both handles need names.
    const VkSemaphore    renderFinishedSemaphore = m_swapchain.renderFinished(imageIndex);
    const VkSwapchainKHR swapchain               = m_swapchain.handle();
    const VkPresentInfoKHR presentInfo{
        .sType              = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
        .waitSemaphoreCount = 1,
        .pWaitSemaphores    = &renderFinishedSemaphore,
        .swapchainCount     = 1,
        .pSwapchains        = &swapchain,
        .pImageIndices      = &imageIndex,
    };
    const VkResult presentResult = vkQueuePresentKHR(m_graphicsQueue, &presentInfo);

    // Advance before any early return below: this slot's work is submitted.
    m_frameIndex = (m_frameIndex + 1) % FRAMES_IN_FLIGHT;

    // 7. Recreate if present or the window asked for it. Chapter 03 section 7.
    if (presentResult == VK_ERROR_OUT_OF_DATE_KHR ||
        presentResult == VK_SUBOPTIMAL_KHR        ||
        m_framebufferResized)
    {
        const RecreateResult recreated = recreateSwapchain();
        if (recreated == RecreateResult::Failed)    { return FrameStatus::Failed; }
        if (recreated == RecreateResult::Recreated) { m_framebufferResized = false; }
    }
    else if (presentResult != VK_SUCCESS)
    {
        return FrameStatus::Failed;
    }

    return FrameStatus::Presented;
}
```

Both recreation paths go through one private function. Today it only forwards;
it exists so that everything else sized from the window — Chapter 08's
offscreen target, the demos' accumulation images — is rebuilt in exactly one
place, rather than at two call sites that will drift apart:

```cpp
RecreateResult VulkanRenderer::recreateSwapchain()
{
    return m_swapchain.recreate();   // Chapter 08 section 4 grows this
}
```

The complete frame owner, with the later scene and demo work added, is
[VulkanRenderer.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/VulkanRenderer.cpp).
It keeps the same result-bearing recording boundary. Chapter 05 implements
the checked command-buffer begin and end; Chapter 09 carries a demo's result
through it.

</details>

**Reset the fence after successful recording.** An `OUT_OF_DATE` acquire is a
retryable skip: no image was acquired and the fence remains signalled. A pool
reset or recording failure after a usable acquire is terminal. The acquire
semaphore may now be signalled without a submission waiting on it, so merely
leaving the fence signalled does not make a retry valid. Chapter 05's main loop
stops on `Failed`. A submit failure is terminal too; the fence was reset, but
there may be no work to signal it. Shutdown must not start another frame wait.
The two `stageMask` values in step 5 are explained under "Barriers next to
semaphores" in section 5.

---

## 5. Barriers, and the three questions they answer

`VkImageMemoryBarrier2` has six fields that people copy without understanding.
They answer three separate questions, and separating them makes barriers
mechanical instead of mysterious.

```cpp
VkImageMemoryBarrier2 barrier{
    .sType         = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2,

    .srcStageMask  = ...,   // Q1: what must finish first?
    .srcAccessMask = ...,   // Q2: whose writes must be flushed (made available)?

    .dstStageMask  = ...,   // Q1: what must wait?
    .dstAccessMask = ...,   // Q2: whose caches must be invalidated (made visible)?

    .oldLayout     = ...,   // Q3: what is the memory arranged for now?
    .newLayout     = ...,   // Q3: what should it be arranged for next?

    .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
    .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
    .image               = image,
    .subresourceRange    = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
};

const VkDependencyInfo dependency{
    .sType                   = VK_STRUCTURE_TYPE_DEPENDENCY_INFO,
    .imageMemoryBarrierCount = 1,
    .pImageMemoryBarriers    = &barrier,
};
vkCmdPipelineBarrier2(commandBuffer, &dependency);
```

(The `...` are the blanks the three questions fill in; the helper at the end of
this section is this block with parameters in them.)

Q1 is asked in **pipeline stages**. The first pipeline arrives in Chapter 06,
but Chapter 05's barriers already name stages, so here is the list now. A draw
passes through these stages, top to bottom, and a stage mask names one or more
of them, as `VK_PIPELINE_STAGE_2_<name>_BIT`:

```text
 TOP_OF_PIPE               a marker: before any work
 DRAW_INDIRECT             reads indirect draw arguments                (Chapter 19)
 VERTEX_ATTRIBUTE_INPUT,
 INDEX_INPUT               read vertex and index buffers                (Chapter 11)
 VERTEX_SHADER             runs once per vertex                         (Chapter 06)
 EARLY_FRAGMENT_TESTS      depth test before shading                    (Chapter 10)
 FRAGMENT_SHADER           runs once per pixel a triangle covers        (Chapter 06)
 LATE_FRAGMENT_TESTS       depth test after shading                     (Chapter 10)
 COLOR_ATTACHMENT_OUTPUT   writes and blends color; also a color
                           attachment's load and store                  (Chapter 05)
 BOTTOM_OF_PIPE            a marker: after all work

 Work that is not a draw has a stage of its own:
 COPY, BLIT, CLEAR         transfer commands                            (Chapter 08)
 COMPUTE_SHADER            a dispatch                                   (Chapter 20)
 HOST                      the CPU reading or writing mapped memory     (Chapter 20)
 ALL_COMMANDS              every stage at once
 NONE                      no stage: nothing to wait for, or nothing that waits
```

**Q1 — execution.** "Every command before this barrier must finish its
`srcStageMask` stages before any command after it may start its `dstStageMask`
stages." Nothing about memory yet, just ordering — and "before" reaches
further back than this command buffer, which the subsection after Q3 shows.

**Q2 — memory.** Even with correct ordering, the writer's results may sit in a
cache the reader cannot see. `srcAccessMask` makes writes *available* (flushed
out); `dstAccessMask` makes them *visible* (invalidated in). Both halves are
required. Getting Q1 right and Q2 wrong is the classic "works on NVIDIA, breaks
on AMD" bug, because cache behavior differs. The reverse case — a write after a
read — needs only Q1: reads leave nothing to flush, so `srcAccessMask` is
`NONE` and the execution dependency does the work.

**Q3 — layout.** Images are stored in an opaque, usage-optimized arrangement.
Transitioning may physically rewrite memory. `VK_IMAGE_LAYOUT_UNDEFINED` as
`oldLayout` means "I do not care about the existing contents" and lets the
driver skip that work — always use it when you are about to overwrite the whole
image, as you do with the swapchain image every frame.

### What "before" and "after" cover

"Before" means everything submitted to this queue ahead of the barrier, not
only the commands above it in the same command buffer: earlier command buffers,
earlier submits, and last frame's work, which may still be running. "After"
likewise means everything that comes later on the queue. The specification
calls the two halves the barrier's *first* and *second synchronization
scope*; the stage and access masks narrow each one down to the stages and
accesses that matter.

A stage named in a source mask also covers every earlier stage of the same
pipeline (and one in a destination mask every later stage), for waiting though
not for memory: `COLOR_ATTACHMENT_OUTPUT` covers the vertex shader, the
fragment shader and the fragment tests that a draw passes through first, but a
write is made available only when its own stage and access are named. A
dispatch and a draw are different pipelines, so a compute stage and a graphics
stage never cover each other.

```text
 the queue, in submission order ──────────────────────────────────────────────────▶

│ frame N-1's command buffer          │ frame N's command buffer                  │
│ pass A writes X   pass B reads X    │ BARRIER   pass A writes X again   ...     │
└───────────── before the barrier ────────────┘└─────── after the barrier ────────┘
```

(Chapter 08's offscreen image is the first real case: the scene pass writes it,
and the composite pass reads it.)

That is why one barrier at the top of frame N protects last frame's read from
this frame's write, although they sit in different command buffers and
different submits — and frame N-1 may well still be running on the GPU when
frame N is submitted. The fence wait at the top of `drawFrame` does not cover
it: that fence belongs to this slot, which last ran frame N-2, and it holds
back only the CPU. The barrier is what orders the GPU, and its source stage is
the stage that did the reading. The cookbook below calls these barriers
**return trips**, and every chapter from 08 on has some.

### Barriers next to semaphores

A semaphore wait and a barrier form one chain **only if the barrier's
`srcStageMask` includes the stage the semaphore was waited at.** This is the
rule behind the first barrier of every frame:

```text
 acquire ─signals─▶ imageAvailable ─waited at COLOR_ATTACHMENT_OUTPUT─┐
                                                                      ▼
 first barrier, srcStageMask = COLOR_ATTACHMENT_OUTPUT ─▶ layout transition ─▶ draw
```

The submit in section 4 waits on `imageAvailable` at `COLOR_ATTACHMENT_OUTPUT`,
not `TOP_OF_PIPE`: vertex shading for the frame can begin before the image is
available, because nothing writes color until that stage, and waiting at
`TOP_OF_PIPE` would serialize the whole pipeline behind the presentation
engine. So the barrier that moves the swapchain image out of `UNDEFINED` names
the same stage as its source, and the layout transition is ordered after the
acquire. With `srcStageMask = NONE` the arrow down is missing: the transition
is ordered after *nothing*, can run while the presentation engine is still
reading the image, and synchronization validation reports it.

The wait holds back every `COLOR_ATTACHMENT_OUTPUT` operation in the submit,
not only those on the swapchain image. From Chapter 08 on, the scene pass draws
into an offscreen target in the same submit, so its color writes wait for the
acquire too. Engines that want that overlap split the frame into two submits
and let only the second, the pass that draws into the swapchain image, wait on
`imageAvailable`. This tutorial keeps one submit per frame.

The present side is not symmetric, and that is what makes it easy to get the
acquire side wrong by analogy. A semaphore *signal* covers every earlier command
that falls in its `stageMask`; with `ALL_COMMANDS` that includes the transition
to `PRESENT_SRC_KHR`. So the end-of-frame barrier can use a `NONE` destination.

The general form:

- `VK_PIPELINE_STAGE_2_NONE` / `VK_ACCESS_2_NONE` on the **destination** side
  when a later semaphore signal covers it, and on the **source** side only when
  the resource genuinely has no earlier use — a freshly created image.
- `VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT` on both sides, with
  `VK_ACCESS_2_MEMORY_WRITE_BIT` as the source access and
  `VK_ACCESS_2_MEMORY_READ_BIT | VK_ACCESS_2_MEMORY_WRITE_BIT` as the
  destination, when you are not sure. It is correct and slow; the broad stage
  alone is not enough while the access masks are still too narrow. Use it to
  get working, then tighten. Synchronization validation will not complain
  about being too strict.

### Barrier cookbook

The barriers Chapters 05-10 use. Each is the three questions answered for one
case; the appendix at the end of this chapter collects the rows the later
chapters add.

| Transition | srcStage / srcAccess | dstStage / dstAccess | Layout |
| --- | --- | --- | --- |
| Begin frame: swapchain image ready to draw | `COLOR_ATTACHMENT_OUTPUT` / `NONE` | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `UNDEFINED` to `COLOR_ATTACHMENT_OPTIMAL` |
| End frame: ready to present | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `NONE` / `NONE` | `COLOR_ATTACHMENT_OPTIMAL` to `PRESENT_SRC_KHR` |
| Staging upload into a new texture | `NONE` / `NONE` | `COPY` / `TRANSFER_WRITE` | `UNDEFINED` to `TRANSFER_DST_OPTIMAL` |
| Texture ready to sample | `COPY` / `TRANSFER_WRITE` | `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ` | `TRANSFER_DST_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Offscreen target, start of frame | `FRAGMENT_SHADER` / `NONE` | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `UNDEFINED` to `COLOR_ATTACHMENT_OPTIMAL` |
| Offscreen target, drawn and about to be composited | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ` | `COLOR_ATTACHMENT_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Depth attachment, start of frame | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS` / `DEPTH_STENCIL_ATTACHMENT_WRITE` | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS` / `DEPTH_STENCIL_ATTACHMENT_READ \| DEPTH_STENCIL_ATTACHMENT_WRITE` | `UNDEFINED` to `DEPTH_ATTACHMENT_OPTIMAL` |

Notes on that table:

- **Every per-frame cycle needs both directions.** An image written by one pass
  and read by another every frame needs the forward barrier and the one back —
  "Offscreen target, start of frame" is the return trip of the composite row.
  The first frame works without the return trip, which is exactly why it gets
  forgotten. Use `UNDEFINED` as the old layout when the next pass overwrites
  every texel.
- The source stage of a return trip is whichever stage last read the image —
  `FRAGMENT_SHADER` for the composite pass.
- The depth row's source is last frame's depth writes: one depth image is
  shared by both frames in flight, so this is a write-after-write, and it needs
  the write access on both sides. It names both test stages because a depth
  attachment's load (the clear) runs in `EARLY_FRAGMENT_TESTS` and its store
  in `LATE_FRAGMENT_TESTS`. Pass `VK_IMAGE_ASPECT_DEPTH_BIT` as
  `transitionImage`'s last argument.
- Synchronization2 split the old `VK_ACCESS_SHADER_READ_BIT` into
  `SHADER_SAMPLED_READ` and `SHADER_STORAGE_READ`, and
  `VK_ACCESS_SHADER_WRITE_BIT` into `SHADER_STORAGE_WRITE`. Use the specific
  ones; they let the driver flush less.

### A helper you will use everywhere

Write this once. The finished reference calls it more than 80 times.

```cpp
// Source/PillowFort/VulkanGraphics/VulkanBarriers.h, inside namespace pf::vulkan_graphics
void transitionImage(VkCommandBuffer commandBuffer,
                     VkImage image,
                     VkImageLayout oldLayout,
                     VkImageLayout newLayout,
                     VkPipelineStageFlags2 srcStage,
                     VkAccessFlags2 srcAccess,
                     VkPipelineStageFlags2 dstStage,
                     VkAccessFlags2 dstAccess,
                     VkImageAspectFlags aspect = VK_IMAGE_ASPECT_COLOR_BIT);
```

```cpp
// Source/PillowFort/VulkanGraphics/VulkanBarriers.cpp, inside namespace pf::vulkan_graphics
// The default argument lives on the declaration only.
void transitionImage(VkCommandBuffer commandBuffer,
                     VkImage image,
                     VkImageLayout oldLayout,
                     VkImageLayout newLayout,
                     VkPipelineStageFlags2 srcStage,
                     VkAccessFlags2 srcAccess,
                     VkPipelineStageFlags2 dstStage,
                     VkAccessFlags2 dstAccess,
                     VkImageAspectFlags aspect)
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
        .subresourceRange    = { aspect, 0, VK_REMAINING_MIP_LEVELS, 0, VK_REMAINING_ARRAY_LAYERS },
    };

    const VkDependencyInfo dependency{
        .sType                   = VK_STRUCTURE_TYPE_DEPENDENCY_INFO,
        .imageMemoryBarrierCount = 1,
        .pImageMemoryBarriers    = &barrier,
    };
    vkCmdPipelineBarrier2(commandBuffer, &dependency);
}
```

Unlike the block at the top of this section, the helper covers every mip level
and array layer (`VK_REMAINING_MIP_LEVELS`, `VK_REMAINING_ARRAY_LAYERS`), which
is what a whole-image transition wants. A barrier on one level (Chapter 15) or
a range of levels (Chapter 36) is written by hand.

Resist the temptation to write the "smart" version that infers stages from
layouts. It cannot even cover the cookbook: "Begin frame" and "Offscreen
target, start of frame" have the same two layouts and different source stages,
because the source depends on what came before (the acquire's wait for one,
last frame's composite for the other), and a layout does not record that. For
compute, where `GENERAL` says nothing about the stage, it silently produces
over-broad barriers, and there the whole point is precision.

---

## 6. Shutdown

**This is `shutdown`.** One wait, then everything in reverse order of creation.
Destroying a `VK_NULL_HANDLE` is a valid no-op, which is what makes this safe
after a partial `initialize`.

```cpp
void VulkanRenderer::shutdown()
{
    if (m_device != VK_NULL_HANDLE)
    {
        vkDeviceWaitIdle(m_device);

        for (FrameResources& frame : m_frames)
        {
            vkDestroySemaphore(m_device, frame.imageAvailable, nullptr);
            vkDestroyFence(m_device, frame.inFlightFence, nullptr);
            vkDestroyCommandPool(m_device, frame.commandPool, nullptr);   // frees its buffers too
            frame = {};
        }
        m_swapchain.shutdown();
    }
    m_vulkan.Shutdown();
    m_device        = VK_NULL_HANDLE;
    m_graphicsQueue = VK_NULL_HANDLE;
}
```

This is the Chapter 04 lifecycle. It ignores what `vkDeviceWaitIdle` returns;
Chapter 08 section 2 adds the checked `requireSafeDeviceIdle` helper, and
Chapter 09 uses it here before tearing down a demo or any frame resources. If
the wait fails with anything but `VK_ERROR_DEVICE_LOST`, the GPU may still be
using these objects, so the complete reference stops rather than destroy them.

This wait covers submitted rendering work. Unextended Vulkan has a separate
presentation-lifetime limitation: `vkDeviceWaitIdle` is not a formal proof
that the presentation engine has released every swapchain resource. This
tutorial uses the common idle-at-shutdown approach; a stronger presentation
completion contract needs presentation fences, such as those described in
the guide's
[swapchain-maintenance section](https://docs.vulkan.org/guide/latest/swapchain_semaphore_reuse.html#_vk_ext_swapchain_maintenance1_extension).
The per-image semaphore reuse proof during rendering does not remove that
shutdown limitation.

---

## Exit check

**Now:** regenerate (`VulkanRenderer`, `VulkanBarriers` and `FrameRequest.h`
are new files), then build with no errors or warnings. `recordFrame` is
declared but has no body until Chapter 05; the engine library builds anyway,
because the program does not use the renderer until then.

**After Chapter 05**, which calls `drawFrame` every frame:

- [ ] Two frames in flight, verified by logging the frame slot index.
- [ ] `renderFinished` semaphores are sized from `vkGetSwapchainImagesKHR`.
- [ ] Validation is silent for a 10-minute session, once Chapter 05's positive
      control has proven synchronization validation on (the
      [conventions](../VulkanTutorial.md#conventions-every-chapter-uses)).
- [ ] Resizing repeatedly never hangs. (If it hangs, check the fence reset
      ordering in steps 3-4 of `drawFrame`.)
- [ ] Shutdown after `vkDeviceWaitIdle` destroys everything without complaint.

Next: [05 — The First Frame](05-First-Frame.md)

---

## Appendix: barriers the later chapters add

Reference; skip it on a first reading. These rows come from Chapters 11 to 33.
Each is explained in the chapter its first column names, by section 5's three
questions or, where an earlier row already answers them, by what differs, so
come back to them when you get there. They are collected here so that one table
answers "what barrier goes between X and Y" for those chapters; the far-view
chapters from 36 on state their barriers in place.

### Geometry and textures

| Transition | srcStage / srcAccess | dstStage / dstAccess | Layout |
| --- | --- | --- | --- |
| Mesh upload, ready for vertex input (11; also 19's grown geometry buffers) | `COPY` / `TRANSFER_WRITE` | `VERTEX_ATTRIBUTE_INPUT \| INDEX_INPUT` / `VERTEX_ATTRIBUTE_READ \| INDEX_READ` | — (buffers: a `VkMemoryBarrier2`) |
| Storage buffer uploaded, read by a vertex shader (25's blades) | `COPY` / `TRANSFER_WRITE` | `VERTEX_SHADER` / `SHADER_STORAGE_READ` | — (buffer) |
| Buffer grown by a copy: earlier uploads, read by the copy (19) | `COPY` / `TRANSFER_WRITE` | `COPY` / `TRANSFER_READ` | — (buffers) |
| Mip chain, before the copy and the blits (15; every level) | `NONE` / `NONE` | `COPY \| BLIT` / `TRANSFER_WRITE` | `UNDEFINED` to `TRANSFER_DST_OPTIMAL` |
| Mip level written, about to be blitted from (15; one level) | `COPY \| BLIT` / `TRANSFER_WRITE` | `BLIT` / `TRANSFER_READ` | `TRANSFER_DST_OPTIMAL` to `TRANSFER_SRC_OPTIMAL` |
| Mip level blitted from, ready to sample (15; one level) | `BLIT` / `NONE` | `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ` | `TRANSFER_SRC_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Last mip level written, ready to sample (15; one level) | `COPY \| BLIT` / `TRANSFER_WRITE` | `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ` | `TRANSFER_DST_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL` |

### Shadows and multisampling

| Transition | srcStage / srcAccess | dstStage / dstAccess | Layout |
| --- | --- | --- | --- |
| Shadow map, start of the shadow pass; last frame sampled it (17, 22) | `FRAGMENT_SHADER \| COMPUTE_SHADER` / `NONE` | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS` / `DEPTH_STENCIL_ATTACHMENT_READ \| DEPTH_STENCIL_ATTACHMENT_WRITE` | `UNDEFINED` to `DEPTH_ATTACHMENT_OPTIMAL`, all layers |
| Shadow map drawn, about to be sampled (17, 22) | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS` / `DEPTH_STENCIL_ATTACHMENT_WRITE` | `FRAGMENT_SHADER \| COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `DEPTH_ATTACHMENT_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL`, all layers |
| Multisampled color, start of frame (18) | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `UNDEFINED` to `COLOR_ATTACHMENT_OPTIMAL` |
| Single-sample depth as the resolve target, start of frame (18) | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS \| COLOR_ATTACHMENT_OUTPUT` / `DEPTH_STENCIL_ATTACHMENT_WRITE \| COLOR_ATTACHMENT_WRITE` | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `UNDEFINED` to `DEPTH_ATTACHMENT_OPTIMAL` |

### Compute

| Transition | srcStage / srcAccess | dstStage / dstAccess | Layout |
| --- | --- | --- | --- |
| Storage image ping-pong between dispatches (20; 29's FFT) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `COMPUTE_SHADER` / `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | `GENERAL` to `GENERAL` |
| Compute result sampled by a later shader (20; 29) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `VERTEX_SHADER` or `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ` | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Sampled result handed back to compute, next frame (20; 29) | `VERTEX_SHADER` or `FRAGMENT_SHADER` / `NONE` | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `SHADER_READ_ONLY_OPTIMAL` (or `UNDEFINED`) to `GENERAL` |
| Accumulation image, frame to frame (33) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `COMPUTE_SHADER` / `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | `GENERAL` to `GENERAL` |
| Storage image created for compute (20; 26's depth pyramid needs only `SHADER_STORAGE_WRITE`) | `NONE` / `NONE` | `COMPUTE_SHADER` / `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | `UNDEFINED` to `GENERAL` |
| Counters: last frame's atomics and readback copy, before `vkCmdFillBuffer` (20) | `COMPUTE_SHADER \| COPY` / `SHADER_STORAGE_WRITE` | `CLEAR` / `TRANSFER_WRITE` | — (buffer) |
| Counters zeroed by `vkCmdFillBuffer`, then used by compute (20) | `CLEAR` / `TRANSFER_WRITE` | `COMPUTE_SHADER` / `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | — (buffer) |
| Compute-written counters copied for readback (20, 21) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `COPY` / `TRANSFER_READ` | — (buffer) |
| Readback copy visible to the CPU, before the fence (20, 21) | `COPY` / `TRANSFER_WRITE` | `HOST` / `HOST_READ` | — (buffer) |
| Compute wrote arguments for later dispatches (21's begin pass) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `DRAW_INDIRECT \| COMPUTE_SHADER` / `INDIRECT_COMMAND_READ \| SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | — (buffer) |
| Compute wrote draw arguments and what the vertex shader reads (19, 21, 26; drop `COPY` / `TRANSFER_READ` when nothing is read back) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `DRAW_INDIRECT \| VERTEX_SHADER \| COPY` / `INDIRECT_COMMAND_READ \| SHADER_STORAGE_READ \| TRANSFER_READ` | — (buffers) |
| ...and its return trip, at the top of next frame's compute (21, 26) | `DRAW_INDIRECT \| VERTEX_SHADER \| COPY \| COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `COMPUTE_SHADER` / `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | — (buffers) |
| Compute wrote a vertex buffer (20; described, not built) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `VERTEX_ATTRIBUTE_INPUT` / `VERTEX_ATTRIBUTE_READ` | — (buffer with `STORAGE_BUFFER \| VERTEX_BUFFER` usage) |
| Scene color from the scene pass into a second, blended scope (21; 23's `DrawInOwnPass`) | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_READ \| COLOR_ATTACHMENT_WRITE` | `COLOR_ATTACHMENT_OPTIMAL`, unchanged |
| Scene depth after the scene pass, to a read-only depth test (21; soft particles add `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ`) | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS \| COLOR_ATTACHMENT_OUTPUT` / `DEPTH_STENCIL_ATTACHMENT_WRITE \| COLOR_ATTACHMENT_WRITE` | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS` / `DEPTH_STENCIL_ATTACHMENT_READ` | `DEPTH_ATTACHMENT_OPTIMAL` to `DEPTH_READ_ONLY_OPTIMAL` |
| ...its return trip after that scope (21; soft particles add `FRAGMENT_SHADER` to the source) | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS` / `NONE` | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS` / `DEPTH_STENCIL_ATTACHMENT_READ \| DEPTH_STENCIL_ATTACHMENT_WRITE` | `DEPTH_READ_ONLY_OPTIMAL` to `DEPTH_ATTACHMENT_OPTIMAL` |
| Scene depth sampled by compute (26's depth pyramid; 22, where at one sample only the depth tests) | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS \| COLOR_ATTACHMENT_OUTPUT` / `DEPTH_STENCIL_ATTACHMENT_WRITE \| COLOR_ATTACHMENT_WRITE` | `COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `DEPTH_ATTACHMENT_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL` |
| ...its return trip before the next scene pass (22, 26) | `COMPUTE_SHADER` / `NONE` | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS` / `DEPTH_STENCIL_ATTACHMENT_READ \| DEPTH_STENCIL_ATTACHMENT_WRITE` | `SHADER_READ_ONLY_OPTIMAL` to `DEPTH_ATTACHMENT_OPTIMAL` |
| Pyramid level written, sampled by the next level and next frame's generation (26) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | — (`GENERAL` throughout: a `VkMemoryBarrier2`) |
| Pyramid rewritten after this frame's generation pass sampled it (26) | `COMPUTE_SHADER` / `NONE` | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | — (`GENERAL` throughout: a `VkMemoryBarrier2`) |
| Buffers uploaded, read by an acceleration-structure build and by compute (33) | `COPY` / `TRANSFER_WRITE` | `ACCELERATION_STRUCTURE_BUILD \| COMPUTE_SHADER` / `SHADER_READ` | — (buffers) |
| Acceleration structure built, read by the next build or a ray query (33) | `ACCELERATION_STRUCTURE_BUILD` / `ACCELERATION_STRUCTURE_WRITE` | `ACCELERATION_STRUCTURE_BUILD \| COMPUTE_SHADER` / `ACCELERATION_STRUCTURE_READ` | — (a `VkMemoryBarrier2`) |
| Sky cube created, readable before any bake: later chapters' sets name it while the sky is off (23) | `NONE` / `NONE` | `FRAGMENT_SHADER \| COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `UNDEFINED` to `SHADER_READ_ONLY_OPTIMAL`, all six layers |
| Sky light cube created, readable before any filter: set 0 names it in every demo that draws meshes (24) | `NONE` / `NONE` | `FRAGMENT_SHADER \| COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `UNDEFINED` to `SHADER_READ_ONLY_OPTIMAL`, every level and layer |
| Sky cube, before the bake; a draw, perhaps last frame's, sampled it (23) | `FRAGMENT_SHADER \| COMPUTE_SHADER` / `NONE` | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `UNDEFINED` to `GENERAL`, all six layers |
| Sky cube baked, about to be sampled (23) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `FRAGMENT_SHADER \| COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Sky light cubes and source chain, before a filter; last frame's draws and the last filter sampled them (24; the `FRAGMENT_SHADER` source is also covered by a chain through the sky's own pre-bake barrier) | `FRAGMENT_SHADER \| COMPUTE_SHADER` / `NONE` | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `UNDEFINED` to `GENERAL` |
| Source chain downsampled, about to be summed by compute (24) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Sky light cubes filtered, about to be sampled (24) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `FRAGMENT_SHADER \| COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Lookup table, computed once in `immediateSubmit`: before, then after (24) | `NONE` / `NONE`; then `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE`; then `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ` | `UNDEFINED` to `GENERAL`; then to `SHADER_READ_ONLY_OPTIMAL` |
| Image uploaded by `uploadToImage`, then sampled by compute: a second barrier (23's environment image) | `COPY` / `TRANSFER_WRITE` | `COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `SHADER_READ_ONLY_OPTIMAL`, unchanged |
| Scene depth tested but not written in a second scope (23's `DrawInOwnPass`) | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS \| COLOR_ATTACHMENT_OUTPUT` / `DEPTH_STENCIL_ATTACHMENT_WRITE \| COLOR_ATTACHMENT_WRITE` | `EARLY_FRAGMENT_TESTS \| LATE_FRAGMENT_TESTS` / `DEPTH_STENCIL_ATTACHMENT_READ` | `DEPTH_ATTACHMENT_OPTIMAL`, unchanged: no return trip |
| Cloud cube created, before its one-time clear (28) | `NONE` / `NONE` | `CLEAR` / `TRANSFER_WRITE` | `UNDEFINED` to `TRANSFER_DST_OPTIMAL`, all six layers |
| ...cleared, readable before the first march: later chapters' sets name it while the clouds are off (28) | `CLEAR` / `TRANSFER_WRITE` | `FRAGMENT_SHADER \| COMPUTE_SHADER` / `SHADER_SAMPLED_READ \| SHADER_STORAGE_READ` | `TRANSFER_DST_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL`, all six layers |
| Noise images before generation: level 0 written by dispatches, every other level by blits (28) | `NONE` / `NONE` | `COMPUTE_SHADER \| BLIT` / `SHADER_STORAGE_WRITE \| TRANSFER_WRITE` | `UNDEFINED` to `GENERAL`, every level |
| Noise level written by a dispatch or a blit, blitted from next (28) | `COMPUTE_SHADER \| BLIT` / `SHADER_STORAGE_WRITE \| TRANSFER_WRITE` | `BLIT` / `TRANSFER_READ` | — (`GENERAL` throughout: a `VkMemoryBarrier2`) |
| Noise images finished, sampled by the march (28) | `COMPUTE_SHADER \| BLIT` / `SHADER_STORAGE_WRITE \| TRANSFER_WRITE` | `COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL`, every level |
| Cloud cube into the march, contents kept; last frame's draw sampled it (28) | `FRAGMENT_SHADER` / `NONE` | `COMPUTE_SHADER` / `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | `SHADER_READ_ONLY_OPTIMAL` to `GENERAL` (not from `UNDEFINED`: the running average needs the old texels) |
| Cloud cube marched, sampled by the draw (28) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ` | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Foam map kept across frames, written by compute, sampled by fragment: its return trip (30) | `FRAGMENT_SHADER` / `NONE` | `COMPUTE_SHADER` / `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | `SHADER_READ_ONLY_OPTIMAL` to `GENERAL` (`UNDEFINED` only on the first frame or after a reset) |
| Compute result sampled by the vertex shader and by later compute (31's displacement maps) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `VERTEX_SHADER \| COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` |
| ...its return trip (31) | `VERTEX_SHADER \| COMPUTE_SHADER` / `NONE` | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `UNDEFINED` to `GENERAL` |
| Storage image written by compute, sampled by fragment, `GENERAL` throughout (31's local foam) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ` | `GENERAL` to `GENERAL` |
| ...its return trip (31) | `FRAGMENT_SHADER` / `NONE` | `COMPUTE_SHADER` / `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | `GENERAL` to `GENERAL` |
| Storage buffer written by compute, read by a vertex shader and a readback copy (32's boat) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `VERTEX_SHADER \| COPY` / `SHADER_STORAGE_READ \| TRANSFER_READ` | — (buffer) |

### Deferred shading

| Transition | srcStage / srcAccess | dstStage / dstAccess | Layout |
| --- | --- | --- | --- |
| G-buffer, start of the G-buffer pass; last frame's lighting pass sampled it (22) | `COMPUTE_SHADER` / `NONE` | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `UNDEFINED` to `COLOR_ATTACHMENT_OPTIMAL` |
| G-buffer drawn, about to be sampled by compute (22) | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `COMPUTE_SHADER` / `SHADER_SAMPLED_READ` | `COLOR_ATTACHMENT_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Scene target drawn, then read and rewritten by compute (22) | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_WRITE` | `COMPUTE_SHADER` / `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE` | `COLOR_ATTACHMENT_OPTIMAL` to `GENERAL` |
| Scene target written by compute, an attachment again for later scopes (22) | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `COLOR_ATTACHMENT_OUTPUT` / `COLOR_ATTACHMENT_READ \| COLOR_ATTACHMENT_WRITE` | `GENERAL` to `COLOR_ATTACHMENT_OPTIMAL` |

### Notes on these rows

- A barrier on one mip level narrows `subresourceRange` to that level. While
  its chain is built, an image is in several layouts at once (Chapter 15
  section 5).
- Every compute-table row whose source is the scene pass's depth, and Chapter
  18's resolve-target row, has the same three-part source. At 1x the scene
  pass's depth test was the last writer; at Nx the resolve was, and every
  multisample resolve, depth included, runs in `COLOR_ATTACHMENT_OUTPUT` with
  color-attachment access.
  The union covers both, and a reader's return trip chains in either way
  (Chapter 21 section 5 draws the chain). The multisampled depth image itself
  uses Chapter 10's depth row unchanged.
- Pass `VK_IMAGE_ASPECT_DEPTH_BIT` for every depth row.
- `GENERAL` is the only layout valid for storage images, and it is deliberately
  unoptimized. If a compute result is only ever *sampled* afterwards,
  transition it to `SHADER_READ_ONLY_OPTIMAL` and let the driver compress it.
- The source stage of a compute return trip is the stage that last read the
  image: `FRAGMENT_SHADER` for a display pass, `VERTEX_SHADER` for the ocean's
  displacement map.
- Synchronization validation cannot check some of these: Chapter 20 section 5
  lists what it sees and what it does not. Argue those barriers from the three
  questions.
