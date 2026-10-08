# 03 — The Swapchain

**Goal:** a swapchain that is correct on the first frame and survives resize,
minimize, restore, and monitor changes.

**ROADMAP:** step 4.

**Module:** `VulkanGraphics`, namespace `pf::vulkan_graphics`.

**Prerequisites:** Chapter 02 — the `VulkanInstance` accessors, section 4's
window and surface, and section 5's `rejectionReason`, which guarantees at
least one surface format and present mode. Like Chapter 02, this chapter
builds but does not run until Chapter 05's frame loop calls it.

---

## What a swapchain actually is

A ring of images owned by the presentation engine (the compositor, usually
DWM on Windows), plus the rules for borrowing one, drawing into it, and giving
it back. You never allocate its images and you never free them.

The contract per frame is:

1. **Acquire** — ask for the index of an image you may draw into. This is
   asynchronous: the function returns an index immediately, but the image is
   not safe to write until a semaphore signals.
2. **Render** — record commands targeting that image.
3. **Present** — hand it back, waiting on a semaphore that says rendering
   finished.

The acquire/present pair is why binary semaphores exist and why Chapter 04 has
a whole section on getting them right.

### What you are actually writing

`VulkanSwapchain` owns the swapchain and everything sized from it. It borrows
the device and surface from Chapter 02's `VulkanInstance` and the window from
the `Window` module, and destroys none of them.

```cpp
// Source/PillowFort/VulkanGraphics/VulkanSwapchain.h
enum class RecreateResult
{
    Recreated,   // a new swapchain is ready
    Minimized,   // zero-sized window; nothing was touched, try again later
    Failed,      // unrecoverable; the swapchain is gone
};

class VulkanSwapchain
{
public:
    InitializationResult initialize(const VulkanInstance& vulkan, GLFWwindow* window,
                                    VkPresentModeKHR requestedPresentMode);
    RecreateResult recreate();                                  // section 7
    void shutdown();                                            // section 8

    // Chapter 07's picker. Takes effect at the next recreate(); falls back to
    // FIFO if this surface does not offer it (section 3).
    void setPresentMode(VkPresentModeKHR requested) { m_requestedPresentMode = requested; }

    VkSwapchainKHR handle() const                  { return m_swapchain; }
    VkFormat       format() const                  { return m_format; }
    VkExtent2D     extent() const                  { return m_extent; }
    uint32_t       imageCount() const              { return static_cast<uint32_t>(m_images.size()); }
    VkImage        image(uint32_t index) const     { return m_images[index]; }
    VkImageView    imageView(uint32_t index) const { return m_imageViews[index]; }
    VkSemaphore    renderFinished(uint32_t imageIndex) const;   // Chapter 04

    VkPresentModeKHR                   presentMode() const           { return m_presentMode; }
    std::span<const VkPresentModeKHR> supportedPresentModes() const { return m_supportedPresentModes; }

private:
    InitializationResult createSwapchain(VkSwapchainKHR oldSwapchain);   // sections 1-6
    InitializationResult createImageViews();                             // section 6
    void destroyImageViews();                                            // section 6
    void createRenderFinishedSemaphores();                               // Chapter 04
    void destroyRenderFinishedSemaphores();                              // Chapter 04

    // Borrowed.
    VkPhysicalDevice m_physicalDevice = VK_NULL_HANDLE;
    VkDevice         m_device         = VK_NULL_HANDLE;
    VkSurfaceKHR     m_surface        = VK_NULL_HANDLE;
    GLFWwindow*      m_window         = nullptr;

    // Owned, and rebuilt by every recreate().
    VkSwapchainKHR           m_swapchain = VK_NULL_HANDLE;
    VkFormat                 m_format    = VK_FORMAT_UNDEFINED;
    VkExtent2D               m_extent{};
    std::vector<VkImage>     m_images;           // the swapchain's; never destroyed by us
    std::vector<VkImageView> m_imageViews;
    std::vector<VkSemaphore> m_renderFinished;   // one per image, Chapter 04

    VkPresentModeKHR              m_presentMode          = VK_PRESENT_MODE_FIFO_KHR;   // what we got
    VkPresentModeKHR              m_requestedPresentMode = VK_PRESENT_MODE_FIFO_KHR;   // what was asked for
    std::vector<VkPresentModeKHR> m_supportedPresentModes;   // re-queried by every createSwapchain
};
```

`initialize` is the three create steps in order:

```cpp
InitializationResult VulkanSwapchain::initialize(const VulkanInstance& vulkan, GLFWwindow* window,
                                                 VkPresentModeKHR requestedPresentMode)
{
    m_physicalDevice       = vulkan.PhysicalDevice();
    m_device               = vulkan.Device();
    m_surface              = vulkan.Surface();
    m_window               = window;
    m_requestedPresentMode = requestedPresentMode;

    if (auto result = createSwapchain(VK_NULL_HANDLE); !result) { return result; }
    if (auto result = createImageViews(); !result)              { return result; }
    createRenderFinishedSemaphores();   // Chapter 04 section 3

    return InitializationResult::success();
}
```

### Where everything lands in the .cpp

The three `choose*` functions in sections 2-4 are the swapchain's whole
configuration layer, and they are **file-scope statics, not members**: each one
is a pure function of data `createSwapchain` has just queried, and none of them
needs the class.

```text
VulkanSwapchain.cpp
  includes (VulkanSwapchain.h, VulkanInstance.h, Log.h, <GLFW/glfw3.h>,
            <vulkan/vk_enum_string_helper.h>, <algorithm>, <format>, <vector>)
  static chooseSurfaceFormat(formats)                     section 2
  static choosePresentMode(modes, requested)              section 3
  static chooseExtent(capabilities, window)               section 4
  namespace pf::vulkan_graphics {
      VulkanSwapchain::initialize(vulkan, window, mode)   above
      VulkanSwapchain::createSwapchain(oldSwapchain)      sections 1-6
      VulkanSwapchain::createImageViews()                 section 6
      VulkanSwapchain::destroyImageViews()                section 6
      VulkanSwapchain::recreate()                         section 7
      VulkanSwapchain::shutdown()                         section 8
      VulkanSwapchain::createRenderFinishedSemaphores()   Chapter 04
      VulkanSwapchain::destroyRenderFinishedSemaphores()  Chapter 04
      VulkanSwapchain::renderFinished(imageIndex)         Chapter 04
  }
```

The header needs `InitializationResult.h`, `<vulkan/vulkan.h>`, `<span>`, `<vector>`,
`struct GLFWwindow;`, and a forward declaration of `class VulkanInstance;`
inside the namespace — the `.cpp` includes the real one.

---

## 1. Querying what the surface supports

**This is `createSwapchain`, part 1.** Sections 1 through 6 are one function,
top to bottom. Three queries, all using the enumerate-twice pattern:

```cpp
InitializationResult VulkanSwapchain::createSwapchain(VkSwapchainKHR oldSwapchain)
{
    VkSurfaceCapabilitiesKHR capabilities{};
    vkGetPhysicalDeviceSurfaceCapabilitiesKHR(m_physicalDevice, m_surface, &capabilities);

    uint32_t formatCount = 0;
    vkGetPhysicalDeviceSurfaceFormatsKHR(m_physicalDevice, m_surface, &formatCount, nullptr);
    std::vector<VkSurfaceFormatKHR> formats(formatCount);
    vkGetPhysicalDeviceSurfaceFormatsKHR(m_physicalDevice, m_surface, &formatCount, formats.data());

    uint32_t presentModeCount = 0;
    vkGetPhysicalDeviceSurfacePresentModesKHR(m_physicalDevice, m_surface, &presentModeCount, nullptr);
    std::vector<VkPresentModeKHR> presentModes(presentModeCount);
    vkGetPhysicalDeviceSurfacePresentModesKHR(m_physicalDevice, m_surface, &presentModeCount,
                                              presentModes.data());

    const VkSurfaceFormatKHR surfaceFormat = chooseSurfaceFormat(formats);                 // section 2
    const VkPresentModeKHR   presentMode   = choosePresentMode(presentModes,
                                                               m_requestedPresentMode); // section 3
    const VkExtent2D         extent        = chooseExtent(capabilities, m_window);      // section 4

    // >>> Section 5 continues this function here: image count and usage. <<<
}
```

**Re-query capabilities on every recreation.** `currentExtent` changes when the
window moves between monitors with different DPI, and caching it at startup is
a bug that only appears on multi-monitor machines. Because the queries live in
`createSwapchain`, which `recreate()` calls, you get this for free — which is
the reason to put them here rather than in `initialize`.

---

## 2. Choosing the format

**File scope, above the namespace block.**

```cpp
// File scope, above the namespace block.
static VkSurfaceFormatKHR chooseSurfaceFormat(const std::vector<VkSurfaceFormatKHR>& formats)
{
    // Chapter 08 changes this one constant to VK_FORMAT_B8G8R8A8_UNORM. See below.
    constexpr VkFormat preferred = VK_FORMAT_B8G8R8A8_SRGB;

    for (const VkSurfaceFormatKHR& format : formats)
    {
        if (format.format     == preferred &&
            format.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR)
        {
            return format;
        }
    }

    // Second choice: any format the display will interpret as sRGB. An HDR
    // surface also lists formats in other color spaces (HDR10, scRGB), and
    // landing on one of those by accident changes what every byte means.
    for (const VkSurfaceFormatKHR& format : formats)
    {
        if (format.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) { return format; }
    }
    return formats[0];   // non-empty: Chapter 02's rejectionReason checked
}
```

### What sRGB is, and the decision it forces

An 8-bit color channel has 256 values. Spread evenly over the amount of light,
too few would land in the darks, where eyes notice small steps, and too many in
the brights, where they do not. So 8-bit images and displays store color on the
**sRGB** curve, roughly `stored = light^(1/2.2)`, which spends more of the 256
values on dark shades:

| Stored byte | As 0-1 | Light it means (linear) |
| --- | --- | --- |
| 0 | 0.0 | 0.0 |
| 64 | 0.25 | 0.05 |
| 128 | 0.5 | 0.22 |
| 188 | 0.74 | 0.5 |
| 255 | 1.0 | 1.0 |

Half the byte values, 0 to 128, cover the darkest fifth of the light.

The trap is arithmetic. Light adds, so anything that mixes light — averaging,
blending, lighting — has to act on the *linear* amounts. Take a pixel on the
edge of a white triangle over black, half covered. Half the light is linear
0.5, which is stored as byte 188. Averaging the stored bytes instead,
`(0 + 255) / 2 = 128`, gives a pixel with 22% of the light, and the edge comes
out visibly too dark. Hence the rule for the whole tutorial: **compute in
linear, and encode to sRGB once, at the end.**

Picking an `_SRGB` format makes the hardware do that encode on every write:
the fragment shader writes linear values and the image stores sRGB bytes.
Chapter 05 comes back to it: a clear color of linear 0.2 is stored as byte 124
and looks mid-grey, not dark.

The cost is one gotcha you will hit in Chapter 07: **ImGui's colors are already
sRGB bytes**, so an `_SRGB` attachment encodes them a second time and the panels
look pale. **Start with `_SRGB` now anyway**: the hardware encode is exactly
right for the triangle. Chapter 08 moves the encode into a pass of its own and
changes `preferred` above to `VK_FORMAT_B8G8R8A8_UNORM`, and nothing else in
this chapter moves. The index's
[Color, across the whole tutorial](../VulkanTutorial.md#color-across-the-whole-tutorial)
lays out the whole plan, chapter by chapter, and why the alternatives lose.

---

## 3. Choosing the present mode

Only `VK_PRESENT_MODE_FIFO_KHR` is guaranteed to exist. It is a true vsync
queue: presents wait for vblank (the moment the display starts a new refresh),
nothing tears (shows the top of one frame and the bottom of the next), and the
queue never drops frames.

| Mode | Behavior | Use it when |
| --- | --- | --- |
| `FIFO` | Queue, waits for vblank. Always available. | Default. Correct for the foundation. |
| `FIFO_RELAXED` | FIFO, but tears if you missed vblank. | You would rather tear than stutter. |
| `MAILBOX` | Queue of one, newest wins, no tearing, no wait. | Interactive tuning. Costs an extra image. |
| `IMMEDIATE` | No sync at all. Tears. | Measuring raw frame time only. |

Everything but FIFO is optional, and support genuinely varies: an integrated
GPU may offer `IMMEDIATE`, `FIFO`, and `FIFO_RELAXED` but no `MAILBOX`, while a
discrete GPU typically offers all four — on one machine with both, it was
exactly that. Code that assumes `MAILBOX` exists works on only one of them.

ROADMAP specifies FIFO, which is right for the foundation. But once you
have ImGui sliders driving shader parameters, FIFO's queued frames add latency
you feel on every drag. And a frame that misses a vblank waits for the next
one, so a workload hovering around the refresh interval — a path tracer taking
18 ms at 60 Hz — presents on an uneven 16.7/33.3 ms rhythm that reads as judder.

So make the mode a setting rather than a constant. The request comes from
outside — Chapter 05's command line sets the starting mode, Chapter 07's picker
changes it at runtime — and the swapchain honours it when the surface can:

```cpp
// File scope, above the namespace block.
static VkPresentModeKHR choosePresentMode(const std::vector<VkPresentModeKHR>& modes,
                                          VkPresentModeKHR requested)
{
    for (const VkPresentModeKHR mode : modes)
    {
        if (mode == requested) { return mode; }
    }

    // Not silently something else: say so, and take the one mode that exists
    // everywhere.
    Log::warning(std::format("Present mode {} is not supported here; using FIFO.",
                             string_VkPresentModeKHR(requested)).c_str());
    return VK_PRESENT_MODE_FIFO_KHR;
}
```

It falls back to FIFO, not to the "nearest" mode, on purpose. Substituting
`IMMEDIATE` for a missing `MAILBOX` would trade latency for tearing, and that
is a choice for the person looking at the screen. The warning, the startup log
line, and Chapter 07's panel all show what you actually got.

`setPresentMode` only records the request; the renderer then asks for a
recreation the same way a resize does. That makes a mode switch a good test of
the recreation path you are about to write.

---

## 4. Choosing the extent

The trap that produces a correct-looking window with a stretched image:

```cpp
// File scope, above the namespace block.
static VkExtent2D chooseExtent(const VkSurfaceCapabilitiesKHR& capabilities,
                               GLFWwindow* window)
{
    // A driver that pins the extent reports the value directly.
    if (capabilities.currentExtent.width != UINT32_MAX)
    {
        return capabilities.currentExtent;
    }

    // Otherwise we choose, in PIXELS, not screen coordinates.
    int width = 0;
    int height = 0;
    glfwGetFramebufferSize(window, &width, &height);

    return VkExtent2D{
        .width  = std::clamp(static_cast<uint32_t>(width),
                             capabilities.minImageExtent.width,
                             capabilities.maxImageExtent.width),
        .height = std::clamp(static_cast<uint32_t>(height),
                             capabilities.minImageExtent.height,
                             capabilities.maxImageExtent.height),
    };
}
```

Two things:

- `currentExtent.width == UINT32_MAX` is the sentinel for "you decide". Windows
  drivers usually pin the extent, so you may never exercise the other branch
  locally. Write it correctly anyway.
- **`glfwGetFramebufferSize`, never `glfwGetWindowSize`.** On a 150% scaled
  display these differ, and using window size gives you a swapchain smaller
  than the window, which the compositor stretches. It looks like a mysterious
  blur.

---

## 5. Image count and usage

**This is `createSwapchain`, part 2**, continuing after the three `choose*`
calls.

```cpp
uint32_t imageCount = capabilities.minImageCount + 1;
if (capabilities.maxImageCount > 0 && imageCount > capabilities.maxImageCount)
{
    imageCount = capabilities.maxImageCount;
}
```

`minImageCount + 1` gives the driver one spare so you are not stalled waiting
for the image currently on screen. `maxImageCount == 0` means unlimited.

**This is a request, not a guarantee.** `vkGetSwapchainImagesKHR` may return
more. Always size your per-image arrays from what that call returns, never from
`imageCount`. This matters in Chapter 04, where you allocate one semaphore per
swapchain image.

### The usage flags, which decide what you can do later

```cpp
VkImageUsageFlags usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;   // always supported
if ((capabilities.supportedUsageFlags & VK_IMAGE_USAGE_TRANSFER_DST_BIT) != 0)
{
    usage |= VK_IMAGE_USAGE_TRANSFER_DST_BIT;
}
```

`COLOR_ATTACHMENT_BIT` is always supported and is what dynamic rendering needs.

`TRANSFER_DST_BIT` allows `vkCmdBlitImage` or `vkCmdCopyImage` *into* the
swapchain image. Nothing in this tutorial copies into the swapchain — from
Chapter 08 on, a composite pass draws into it — so it is a convenience for
debugging, requested only when the surface offers it.

**What not to request:** `VK_IMAGE_USAGE_STORAGE_BIT`, so a compute shader
could write the swapchain image directly. Support depends on the format, and
`_SRGB` formats are never storage formats. Compute results go to an offscreen
image of their own, which Chapter 08's composite pass draws to the screen.

---

## 6. Creating the swapchain

**This is `createSwapchain`, part 3 — the end of it.**

```cpp
const VkSwapchainCreateInfoKHR swapchainInfo{
    .sType            = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
    .surface          = m_surface,
    .minImageCount    = imageCount,
    .imageFormat      = surfaceFormat.format,
    .imageColorSpace  = surfaceFormat.colorSpace,
    .imageExtent      = extent,
    .imageArrayLayers = 1,
    .imageUsage       = usage,
    .imageSharingMode = VK_SHARING_MODE_EXCLUSIVE,
    .preTransform     = capabilities.currentTransform,
    .compositeAlpha   = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
    .presentMode      = presentMode,
    .clipped          = VK_TRUE,
    .oldSwapchain     = oldSwapchain,     // VK_NULL_HANDLE on first creation
};

VkSwapchainKHR newSwapchain = VK_NULL_HANDLE;
const VkResult result = vkCreateSwapchainKHR(m_device, &swapchainInfo, nullptr, &newSwapchain);
if (result != VK_SUCCESS)
{
    return InitializationResult::failure(
        std::format("vkCreateSwapchainKHR failed: {}", string_VkResult(result)));
}

// Only now, on success, does the new swapchain become the current one.
m_swapchain             = newSwapchain;
m_format                = surfaceFormat.format;
m_extent                = extent;
m_presentMode           = presentMode;
m_supportedPresentModes = presentModes;

uint32_t actualImageCount = 0;
vkGetSwapchainImagesKHR(m_device, m_swapchain, &actualImageCount, nullptr);
m_images.resize(actualImageCount);
vkGetSwapchainImagesKHR(m_device, m_swapchain, &actualImageCount, m_images.data());

Log::info(std::format("Swapchain: {}x{}, {} images, {}, {}, {}", extent.width, extent.height,
                      actualImageCount, string_VkFormat(m_format),
                      string_VkColorSpaceKHR(surfaceFormat.colorSpace),
                      string_VkPresentModeKHR(presentMode)).c_str());
return InitializationResult::success();
}
```

That log line is this chapter's first exit check, and it is worth keeping: when
a resize goes wrong, the before-and-after swapchain lines are the first thing to
read.

The fields worth understanding rather than copying:

- **`imageSharingMode`** — `EXCLUSIVE` means one queue family owns each image,
  which is correct given one universal queue and is also the faster option.
  `CONCURRENT` is only needed if graphics and present are different families,
  which is rare on desktop.
- **`preTransform`** — pass through `currentTransform`. Only mobile actually
  rotates here; passing anything else on desktop means the compositor does an
  extra blit.
- **`clipped = VK_TRUE`** — the driver may skip shading pixels hidden by
  another window. Only set `VK_FALSE` if you read back the presented image.
- **`oldSwapchain`** — lets the driver recycle memory during recreation and,
  more usefully, keeps the old swapchain presentable while the new one is
  built. You still must destroy the old handle yourself afterwards; passing it
  here does not transfer ownership.

Then a view for each image — **this is `createImageViews`**, with its
counterpart beside it:

```cpp
InitializationResult VulkanSwapchain::createImageViews()
{
    m_imageViews.resize(m_images.size(), VK_NULL_HANDLE);
    for (size_t i = 0; i < m_images.size(); ++i)
    {
        const VkImageViewCreateInfo viewInfo{
            .sType    = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
            .image    = m_images[i],
            .viewType = VK_IMAGE_VIEW_TYPE_2D,
            .format   = m_format,
            .subresourceRange = {
                .aspectMask     = VK_IMAGE_ASPECT_COLOR_BIT,
                .baseMipLevel   = 0,
                .levelCount     = 1,
                .baseArrayLayer = 0,
                .layerCount     = 1,
            },
        };
        const VkResult result = vkCreateImageView(m_device, &viewInfo, nullptr, &m_imageViews[i]);
        if (result != VK_SUCCESS)
        {
            return InitializationResult::failure(
                std::format("vkCreateImageView failed: {}", string_VkResult(result)));
        }
    }
    return InitializationResult::success();
}

void VulkanSwapchain::destroyImageViews()
{
    for (VkImageView view : m_imageViews)
    {
        if (view != VK_NULL_HANDLE) { vkDestroyImageView(m_device, view, nullptr); }
    }
    m_imageViews.clear();
}
```

The images belong to the swapchain and must not be destroyed. The **views are
yours** and must be destroyed on every recreation. The null check in
`destroyImageViews` is for the case where `createImageViews` failed halfway.

---

## 7. Recreation

Recreation is triggered from three places, and missing any one produces a bug
that only appears sometimes. The first two are in the renderer's `drawFrame`,
which Chapter 04 section 4 writes out in full; they reach `recreate()` through
`recreateSwapchain`, the renderer's one-line wrapper around it, which gives
Chapter 08 a single place to rebuild everything else sized from the window.

1. **`VK_ERROR_OUT_OF_DATE_KHR` from acquire.** The surface changed and the
   swapchain is unusable. You must recreate and skip the frame. Crucially, on
   this path the acquire semaphore was *not* signalled, so you must not submit
   anything that waits on it.
2. **`VK_ERROR_OUT_OF_DATE_KHR` or `VK_SUBOPTIMAL_KHR` from present.**
   `SUBOPTIMAL` means it still worked but no longer matches the surface —
   handle it after presenting, not by skipping.
3. **The GLFW framebuffer-size callback.** Some drivers never report
   out-of-date on resize, so without this you get a stretched image on those
   machines. The `Window` module owns the callback and queues the event; the
   renderer reads a flag, and clears it only once a recreation succeeds, so a
   resize that arrives while minimized is retried when the window has a size.

### `recreate()`, and handling zero size

```cpp
RecreateResult VulkanSwapchain::recreate()
{
    vkDeviceWaitIdle(m_device);

    // Minimized. A zero-sized swapchain is invalid, so there is nothing to
    // build - and nothing is torn down either, so the old swapchain stays
    // valid until there is something to replace it with.
    //
    // Ask the surface, through the same chooseExtent createSwapchain is about
    // to call, rather than glfwGetFramebufferSize: on Windows a minimized
    // surface reports a 0x0 currentExtent, and the two sources can briefly
    // disagree around a minimize. Asking immediately before creating keeps
    // them from disagreeing about the one value that matters.
    VkSurfaceCapabilitiesKHR capabilities{};
    vkGetPhysicalDeviceSurfaceCapabilitiesKHR(m_physicalDevice, m_surface, &capabilities);
    const VkExtent2D extent = chooseExtent(capabilities, m_window);
    if (extent.width == 0 || extent.height == 0) { return RecreateResult::Minimized; }

    destroyImageViews();
    destroyRenderFinishedSemaphores();          // count is about to change

    const VkSwapchainKHR oldSwapchain = m_swapchain;
    const InitializationResult result = createSwapchain(oldSwapchain);
    vkDestroySwapchainKHR(m_device, oldSwapchain, nullptr);
    if (!result)
    {
        m_swapchain = VK_NULL_HANDLE;           // createSwapchain left it pointing at the old one
        Log::error(result.message());
        return RecreateResult::Failed;
    }

    if (const auto viewResult = createImageViews(); !viewResult)
    {
        Log::error(viewResult.message());
        return RecreateResult::Failed;
    }
    createRenderFinishedSemaphores();           // resized from the NEW image count
    return RecreateResult::Recreated;
}
```

**Everything sized from the image count gets rebuilt here, not just the views.**
The per-image `renderFinished` semaphores from
[Chapter 04](04-Commands-And-Synchronization.md) are the other one, and they are
easy to forget because a resize usually returns the same image count — so the
stale vector keeps working until the day it does not. The count can change,
since the driver may return more images than you asked for, but nothing
guarantees a given change does — so Chapter 05's stress table forces one
deliberately rather than hoping.

**`recreate()` does not wait while minimized; it reports it.** The waiting —
`glfwWaitEvents` until the window has a size again — belongs in the frame loop
(Chapter 05 section 3), not here. The difference matters: a wait loop inside
`recreate()` never looks at `glfwWindowShouldClose`, so closing the app from
the taskbar while it is minimized hangs it forever. In the frame loop, the same
wait sits right beside the close check. Either way `glfwWaitEvents` sleeps until
an event arrives, which is the difference between an idle minimized app and one
pinning a core — ROADMAP's "wait instead of spinning" check.

`vkDeviceWaitIdle` before destroying is the blunt instrument. It is correct and
it costs a pipeline flush during an operation the user perceives as a resize,
which is fine. Finer-grained recreation using per-frame fences is a later
optimization with real correctness risk; do not start there.

---

## 8. Shutdown

**This is `shutdown`.** It runs before `VulkanInstance::Shutdown`, because the
swapchain is created from the device and the surface that function destroys.

```cpp
void VulkanSwapchain::shutdown()
{
    // The caller has already run vkDeviceWaitIdle.
    destroyRenderFinishedSemaphores();
    destroyImageViews();
    if (m_swapchain != VK_NULL_HANDLE)
    {
        vkDestroySwapchainKHR(m_device, m_swapchain, nullptr);
        m_swapchain = VK_NULL_HANDLE;
    }
    m_images.clear();
}
```

---

## Exit check

**Now:** regenerate (two new files), then build with no errors or warnings.

**After Chapter 05**, which runs the swapchain for the first time:

- [ ] Startup logs the chosen format, color space, present mode, extent, and
      actual image count.
- [ ] Dragging the window edge produces no validation errors. (On Windows the
      recreation happens when you release — see Chapter 02 section 4.)
- [ ] Minimizing drops CPU usage to near zero, restoring resumes cleanly, and
      closing from the taskbar while minimized exits.
- [ ] Dragging between monitors with different scaling produces a correctly
      sized, unstretched image.
- [ ] Starting with `--present immediate` (Chapter 05) uses it; asking for a
      mode the surface lacks logs the warning and runs on FIFO.
- [ ] Switching present mode at runtime recreates without error. (Once
      Chapter 07 has the picker.)

Next: [04 — Commands and Synchronization](04-Commands-And-Synchronization.md)
