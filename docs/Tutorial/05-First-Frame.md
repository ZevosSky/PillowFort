# 05 — The First Frame

**Goal:** a window filled with a color you chose, that survives everything you
can do to the window.

**ROADMAP:** step 6.

**Module:** `VulkanGraphics`, namespace `pf::vulkan_graphics`, plus
`SandboxGame/Main.cpp`.

**Prerequisites:** Chapters 2–4 — `VulkanRenderer::initialize`
([Chapter 4, section 2](04-Commands-And-Synchronization.md#2-frames-in-flight)),
`drawFrame`
([Chapter 4, section 4](04-Commands-And-Synchronization.md#4-the-frame-in-order))
and `shutdown`
([Chapter 4, section 6](04-Commands-And-Synchronization.md#6-shutdown)),
`transitionImage` and the first and last rows of the barrier cookbook
([Chapter 4, section 5](04-Commands-And-Synchronization.md#5-barriers-and-the-three-questions-they-answer)),
`VulkanSwapchain::recreate` and its zero-size case
([Chapter 3, section 7](03-Swapchain.md#7-recreation)), and the `Window` module
([Chapter 2, section 4](02-Instance-And-Device.md#4-the-window-and-the-surface)).

This chapter is short because Chapters 2 through 4 supplied the setup and
frame-lifetime machinery. This first visible result brings those pieces together.
It is also the first chapter whose program runs, so its exit check sends you
back to the runtime checks Chapters 2–4 deferred until something could run.

---

## 1. Recording the frame

**This is `VulkanRenderer::recordFrame`**, the private function Chapter 4's
`drawFrame` calls between resetting the pool and submitting. Its two
`transitionImage` calls are why `VulkanRenderer.cpp` now includes
`VulkanBarriers.h`.

With dynamic rendering (core in 1.3) there is no `VkRenderPass` and no
`VkFramebuffer`, the two objects older Vulkan code creates ahead of time to
describe its attachments
([what changed](../VulkanTutorial.md#what-changed-since-the-tutorials-you-probably-remember)).
You name the attachments inline instead, at record time, in the
`VkRenderingInfo` that `vkCmdBeginRendering` takes.

<a id="ch05-clear-frame"></a>

### Attempt CH05-clear-frame: turn an acquired image into a presented clear

Write `recordFrame` using Chapter 4's barrier helper. Begin and end the
command buffer; clear the acquired image over the entire current swapchain
extent, preserve the clear for presentation, and leave it in the presentation
layout. There are no draws or depth attachments yet. For each transition,
write down the previous access, next access and required layout before you
choose the masks. At the exit check the requested color must fill the window,
survive resize and restoration, and pass the synchronization positive control.

**Acceptance:** The requested clear fills the current extent, survives resize/minimize/restore, and the synchronization positive control passes.

**Transfer:** Change the clear color and restore from a differently sized minimized window. Predict which image/extent is used, then check for stale borders or an old color.

<details>
<summary>Hint 1: the clear is attachment work</summary>

Dynamic rendering can clear an attachment without a draw. Its load operation
performs the clear, and its store operation keeps the result. The acquired
image must first be usable as a color attachment.

</details>

<details>
<summary>Hint 2: put one rendering scope between two transitions</summary>

Record begin, transition to attachment, begin rendering with a clear, end
rendering, transition to present, then end the command buffer. The old
contents can be discarded because the clear overwrites every pixel.

</details>

<details>
<summary>Hint 3: connect the first transition to the acquire wait</summary>

Use `COLOR_ATTACHMENT_OUTPUT` as both stages of the first transition, source
access `NONE`, destination access `COLOR_ATTACHMENT_WRITE`. The rendering
attachment uses `LOAD_OP_CLEAR` and `STORE_OP_STORE`; its image view is the
one for `imageIndex`, and the render area covers the swapchain's current
extent. The final transition has a color-write source and a `NONE`
destination.

</details>

<details>
<summary>Worked solution: recording the clear frame</summary>

```cpp
// Source/PillowFort/VulkanGraphics/VulkanRenderer.cpp
InitializationResult VulkanRenderer::recordFrame(VkCommandBuffer commandBuffer,
                                                  uint32_t imageIndex,
                                                  const FrameRequest& request)
{
    const VkCommandBufferBeginInfo beginInfo{
        .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
    };
    if (vkBeginCommandBuffer(commandBuffer, &beginInfo) != VK_SUCCESS)
    {
        return InitializationResult::failure("Beginning the frame command buffer failed.");
    }

    // The swapchain image arrives in an unknown layout. We overwrite all of it,
    // so UNDEFINED is correct and lets the driver skip preserving contents.
    // The source stage is the stage drawFrame waited imageAvailable at - that is
    // what orders this transition after the acquire. Chapter 04 section 5.
    transitionImage(commandBuffer, m_swapchain.image(imageIndex),
                    VK_IMAGE_LAYOUT_UNDEFINED,
                    VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);

    const VkRenderingAttachmentInfo colorAttachment{
        .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView   = m_swapchain.imageView(imageIndex),
        .imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
        .resolveMode = VK_RESOLVE_MODE_NONE,
        .loadOp      = VK_ATTACHMENT_LOAD_OP_CLEAR,
        .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
        .clearValue  = { .color = { { request.clearColor[0], request.clearColor[1],
                                      request.clearColor[2], request.clearColor[3] } } },
    };

    const VkRenderingInfo renderingInfo{
        .sType                = VK_STRUCTURE_TYPE_RENDERING_INFO,
        .renderArea           = { { 0, 0 }, m_swapchain.extent() },
        .layerCount           = 1,
        .viewMask             = 0,
        .colorAttachmentCount = 1,
        .pColorAttachments    = &colorAttachment,
        .pDepthAttachment     = nullptr,
        .pStencilAttachment   = nullptr,
    };

    vkCmdBeginRendering(commandBuffer, &renderingInfo);
    // Chapter 06 puts the triangle here. Chapter 07 puts ImGui after it.
    vkCmdEndRendering(commandBuffer);

    transitionImage(commandBuffer, m_swapchain.image(imageIndex),
                    VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                    VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE);

    if (vkEndCommandBuffer(commandBuffer) != VK_SUCCESS)
    {
        return InitializationResult::failure("Ending the frame command buffer failed.");
    }
    return InitializationResult::success();
}
```

The complete frame owner is
[VulkanRenderer.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/VulkanRenderer.cpp).
Its later demo hook delegates the scene clear and draw to
[TriangleDemo.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Triangle/TriangleDemo.cpp).

</details>

### What is worth noticing

**Recording can fail before submission.** Beginning or ending the command
buffer returns a result; the `vkCmd*` calls between them return `void`.
Chapter 4's caller checks this result before resetting the slot's fence or
submitting. A failed recording ends the run through `FrameStatus::Failed`;
the next iteration must not reuse its acquired image or acquire semaphore.

**`ONE_TIME_SUBMIT_BIT` matches how the buffer is used.** Each recording is
submitted once, then `drawFrame` resets the pool and records it again, which
is exactly the promise the flag makes; the driver need not prepare the
recording for a second submission.

**`loadOp` and `storeOp` are performance decisions, not bookkeeping.**
Tile-based GPUs (most phones and tablets) render the image a small tile at a
time in on-chip memory, and these two ops decide whether each tile is first
read in from main memory and afterwards written back. Desktop GPUs feel them
too: a clear can often be done as a fast clear of compression metadata rather
than a write of every pixel, and `DONT_CARE` lets the driver skip reading the
old contents.

| Op | Meaning | Use |
| --- | --- | --- |
| `LOAD_OP_CLEAR` | Fill with `clearValue` | Every pixel must start from one known value, including any your draws do not cover. |
| `LOAD_OP_DONT_CARE` | Contents undefined | You will write every pixel yourself, e.g. a fullscreen pass; no previous contents need preserving. |
| `LOAD_OP_LOAD` | Preserve existing | You are compositing onto previous contents; the implementation must retain them. |
| `STORE_OP_STORE` | Keep the result | Anything you will present or sample. |
| `STORE_OP_DONT_CARE` | Discard | Depth buffers you do not read after the pass. |

A depth attachment whose contents no later pass reads, including a later
depth test with `LOAD_OP_LOAD`, can use
`LOAD_OP_CLEAR` and `STORE_OP_DONT_CARE`. This lets the implementation avoid
preserving depth that nobody consumes; the actual saving depends on the
device and pass. Chapter 21, section 5 adds a sixth op,
`STORE_OP_NONE`, for an attachment a scope only reads and leaves as it found
it.

**The clear is a load op, not a clear command.** Chapter 3, section 5 requests
`TRANSFER_DST_BIT` when the surface offers it, which would allow
`vkCmdClearColorImage` instead. That command needs the image in
`TRANSFER_DST_OPTIMAL` (or `GENERAL`), so it adds a layout and a transfer-stage
barrier before the image can become an attachment, and it cannot run at all on
a surface that does not offer the flag. The load op clears inside the
rendering scope the triangle will draw into, with no extra layout or barrier.

**`vkCmdBeginRendering` can be called more than once per frame.** Each call is
an independent render "pass" over whatever attachments you name. Chapter 8
uses this: an offscreen scene pass, then a swapchain pass. There is no subpass
machinery involved, and so nothing orders one scope after another for you:
when a later scope reads what an earlier one wrote, a barrier goes between
them (Chapter 8, section 4).

**The clear color is in linear space.** The `_SRGB` swapchain Chapter 3 starts
with encodes on write, so `{0.2, 0.2, 0.2, 1.0}` is stored as byte 124 and
displays as a mid-grey (Chapter 3, section 2). That stays true after
Chapter 8 moves the encode into the composite pass: the clear color clears a
linear image, and the composite encodes it the same way. Chapter 16's exposure
and tone curve act on it too, and at their defaults (0 stops, Raw) change
nothing.

---

## 2. What `main` hands the renderer

The roadmap has no graphics abstraction layer: demos call Vulkan directly
(step 10). But `main` has no reason to, and the request it passes each frame is
plain data. Keep it in a header that does not include `vulkan.h`. That does not
hide Vulkan from `main`, which includes `VulkanRenderer.h` and names present
modes in section 3's `parseSettings`; it keeps Vulkan types out of what crosses
from `main` to the renderer every frame. This replaces Chapter 4's empty
placeholder in the same file, so nothing needs regenerating:

```cpp
// Source/PillowFort/VulkanGraphics/FrameRequest.h
namespace pf::vulkan_graphics {

struct FrameRequest
{
    float clearColor[4] = { 0.05f, 0.05f, 0.08f, 1.0f };
};

} // namespace pf::vulkan_graphics
```

`FrameStatus`, the other half of the conversation, was defined beside
`VulkanRenderer` in Chapter 4.

Resist adding to `FrameRequest`. The pressure to grow it into a scene
description starts the moment you have a triangle, and ROADMAP step 10 has a
better home for all of that: each demo records its own commands. This struct
stays the handful of values `main` itself owns.

---

## 3. Where the loop lives

`SandboxGame` owns the only `main()` and wires the pieces together.
`Main.cpp` includes `PillowFort/Window/GlfwWindow.h`,
`PillowFort/VulkanGraphics/VulkanRenderer.h`, `PillowFort/ErrorReporting/Log.h`,
`<chrono>`, `<cmath>`, `<format>`, and `<string_view>`, then says
`using namespace pf;` — which is why the code below can write `window::` and
`vulkan_graphics::`. The loop itself is ROADMAP step 2's — a
`std::chrono::steady_clock` frame loop that drains the `Window` module's event
queue once per frame — with the renderer plugged in.

First, two settings come from the command line, so trying the other GPU or
another present mode needs no rebuild:

```cpp
// Source/SandboxGame/Main.cpp, file scope.
//   SandboxGame.exe --gpu RTX --present mailbox
static vulkan_graphics::RendererSettings parseSettings(int argc, char** argv)
{
    vulkan_graphics::RendererSettings settings;
    for (int i = 1; i + 1 < argc; i += 2)
    {
        const std::string_view key   = argv[i];
        const std::string_view value = argv[i + 1];

        if (key == "--gpu")
        {
            settings.preferredGpu = value;
        }
        else if (key == "--present")
        {
            if      (value == "fifo")         { settings.presentMode = VK_PRESENT_MODE_FIFO_KHR; }
            else if (value == "fifo-relaxed") { settings.presentMode = VK_PRESENT_MODE_FIFO_RELAXED_KHR; }
            else if (value == "mailbox")      { settings.presentMode = VK_PRESENT_MODE_MAILBOX_KHR; }
            else if (value == "immediate")    { settings.presentMode = VK_PRESENT_MODE_IMMEDIATE_KHR; }
            else { Log::warning(std::format("Unknown --present \"{}\"; using fifo.", value).c_str()); }
        }
        else
        {
            Log::warning(std::format("Unknown option \"{}\"; ignored.", key).c_str());
        }
    }
    return settings;
}
```

To pass them when launching from Visual Studio, put them in `premake5.lua` —
`debugargs { "--gpu", "RTX" }` in `project "SandboxGame"` — rather than on the
project's Debugging page, which saves into an untracked
`SandboxGame.vcxproj.user` under `Build/` that a later generation can
overwrite.

Then `main` itself:

```cpp
// Source/SandboxGame/Main.cpp
int main(int argc, char** argv)
{
    window::GlfwWindow window;
    if (const auto result = window.initialize({ 1280, 720, "PillowFort Sandbox" }); !result)
    {
        Log::error(std::format("Window: {}", result.message()).c_str());
        return 1;
    }

    vulkan_graphics::VulkanRenderer renderer;
    if (const auto result = renderer.initialize(window.handle(), parseSettings(argc, argv)); !result)
    {
        Log::error(std::format("Vulkan: {}", result.message()).c_str());
        renderer.shutdown();   // destroys whatever initialize got as far as creating
        window.shutdown();
        return 1;
    }

    const auto startTime = std::chrono::steady_clock::now();
    int exitCode = 0;

    while (!window.shouldClose())
    {
        // Minimized: nothing to draw into, so sleep until something happens.
        // This is ROADMAP step 2's "wait instead of spinning", and it lives here,
        // beside the shouldClose check, so closing from the taskbar still exits.
        if (window.isMinimized())
        {
            window.waitEvents();
            continue;
        }

        window.pollEvents();

        // The queue is drained once per frame, per the roadmap.
        for (const window::Event& event : window.drainEvents())
        {
            if (event.kind == window::EventKind::FramebufferResized)
            {
                renderer.notifyFramebufferResized();
            }
        }

        const float elapsedSeconds = std::chrono::duration<float>(
            std::chrono::steady_clock::now() - startTime).count();

        vulkan_graphics::FrameRequest request;
        request.clearColor[0] = 0.5f + 0.5f * std::sin(elapsedSeconds);

        if (renderer.drawFrame(request) == vulkan_graphics::FrameStatus::Failed)
        {
            Log::error("Rendering failed. Shutting down.");
            exitCode = 1;
            break;
        }
    }

    renderer.shutdown();     // begins with vkDeviceWaitIdle
    window.shutdown();
    return exitCode;
}
```

`Skipped` needs no handling here: it means "nothing was drawn this time", and the
next iteration tries again. Chapter 4's acquire-time skip leaves the slot's
fence signalled and its acquire semaphore unused. That is different from a
failure after a successful acquire: `Failed` stops this loop, even if no GPU
work was submitted (Chapter 4, section 4).

The two shutdowns run in the order Chapter 2, section 8 gives, renderer before
window: the renderer's surface was made from the window's handle. That is the
teardown order ROADMAP step 6 asks you to verify.

Animating the clear color from elapsed time is worth the three lines: a static
color cannot distinguish "presenting correctly at 165 fps" from "presented once
and hung".

---

## 4. Stressing it

This is the milestone the roadmap gates on, so actually run the list:

| Action | What it exercises | What failure looks like |
| --- | --- | --- |
| Drag a window edge, release, repeat twenty times | Recreation on each release (Windows freezes the loop during the drag itself; Chapter 2, section 4) | Validation spam, or a hang from the fence-reset bug in Chapter 4 |
| Maximize and restore repeatedly | Large extent jumps | Stale image views |
| Minimize, wait, restore | Zero-extent handling | A busy-wait pinning one core, or a zero-extent swapchain error from validation |
| Minimize, then close from the taskbar | The minimized wait still reaching `shouldClose` | The process never exits |
| Drag between monitors at different scaling | Extent re-query | Stretched or blurry output from cached capabilities |
| Alt-tab away and back | Surface loss on some drivers | `VK_ERROR_SURFACE_LOST_KHR` |
| Close immediately after a resize | Shutdown right after recreation | Destroying in-use objects |
| Switch present mode at runtime (once Chapter 7 has the picker) | Recreation outside the resize path | A hang or validation error from anything sized at startup |
| The same, with the image count forced to change | `renderFinished` resizing | Indexing past the end of `renderFinished` if you sized it from `FRAMES_IN_FLIGHT`, or only once from the first swapchain |

The last two rows wait for Chapter 7's present-mode picker; come back to them
then. The last row also needs help to mean anything. Whether a present-mode
switch changes the image count is up to the driver, so force it: temporarily
make Chapter 3's `minImageCount + 1` into `+ 2` whenever the requested mode is
not FIFO. Every switch between FIFO and another mode then changes the count,
which is exactly the case Chapter 4's per-image semaphores exist for. Read the
count in the swapchain log line after each switch: if the surface's
`maxImageCount` clamps both requests to the same number, the count has not
changed and the row has not been tested.

---

## Exit check

This chapter adds no files, so build without regenerating, then run Debug with
validation on:

- [ ] The window's color swings smoothly between a dark blue-grey and a
      pinkish red, one full cycle about every six seconds (section 3's `sin`
      of the elapsed time drives the red channel). The dark end is not black:
      green and blue stay at linear 0.05 and 0.08, which the `_SRGB`
      swapchain stores as bytes 63 and 80 (section 1), so a screenshot reads
      about (0, 63, 80) at one end and (255, 63, 80) at the other.
- [ ] The runtime checks Chapters 2, 3, and 4 left for a running program
      pass: every item under their "After Chapter 5" headings, among them the
      GPU and swapchain log lines, the leaked-device, missing-layer and
      API-version tests, the frame-slot log, and the `--gpu` and `--present`
      options.
- [ ] **Synchronization validation is proven on.** Temporarily change the
      end-of-frame barrier's source access from
      `VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT` to `VK_ACCESS_2_NONE`. The
      rendering's writes are then never made available before the transition
      to `PRESENT_SRC_KHR`. A layout transition rewrites the image, so it
      counts as a write, and sync validation must report
      `SYNC-HAZARD-WRITE-AFTER-WRITE` on the first frame — the ID in the
      brackets Chapter 2's callback prints
      ([Chapter 34, section 5](34-Debugging.md#5-reading-validation-messages)
      reads such a message field by field). If it reports nothing, it is
      off — check for a `vkconfig` override (Chapter 1, section 5) before
      trusting any "no validation errors" result below. Put the barrier back
      afterwards.
- [ ] Every row of the stress table passes with zero validation errors, except
      the two present-mode rows, which wait for Chapter 7.
- [ ] A minimized window uses no measurable CPU: Task Manager shows about 0%
      for `SandboxGame.exe`. A spinning loop shows one logical processor's
      share instead (100% divided by their count).

Next: [06 — Shaders and Pipelines](06-Shaders-And-Pipelines.md)
