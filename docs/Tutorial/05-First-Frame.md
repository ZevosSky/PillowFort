# 05 — The First Frame

**Goal:** a window filled with a color you chose, that survives everything you
can do to the window.

**ROADMAP:** step 6.

**Module:** `VulkanGraphics`, namespace `pf::vulkan_graphics`, plus
`SandboxGame/Main.cpp`.

**Prerequisites:** Chapters 02-04 — `VulkanRenderer::initialize` and
`drawFrame` (04 section 4), `transitionImage` and the first and last rows of the
barrier cookbook (04 section 5), and the `Window` module (02 section 4).

This chapter is short, because Chapters 02 through 04 did the work. That is the
correct shape for Vulkan: the first pixel is expensive and the second is free.
It is also the first chapter that runs, so its exit check sends you back to the
runtime checks Chapters 02-04 left for now.

---

## 1. Recording the frame

**This is `VulkanRenderer::recordFrame`**, the private function Chapter 04's
`drawFrame` calls between resetting the pool and submitting.

With dynamic rendering there is no render pass and no framebuffer. You describe
the attachments inline, at record time.

```cpp
// Source/PillowFort/VulkanGraphics/VulkanRenderer.cpp
void VulkanRenderer::recordFrame(VkCommandBuffer commandBuffer,
                                 uint32_t imageIndex,
                                 const FrameRequest& request)
{
    const VkCommandBufferBeginInfo beginInfo{
        .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
    };
    vkBeginCommandBuffer(commandBuffer, &beginInfo);

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

    vkEndCommandBuffer(commandBuffer);
}
```

### What is worth noticing

**`loadOp` and `storeOp` are performance decisions, not bookkeeping.** On
tile-based hardware they control whether the tile memory is populated from and
written back to main memory, and even on desktop they are real:

| Op | Meaning | Use |
| --- | --- | --- |
| `LOAD_OP_CLEAR` | Fill with `clearValue` | You are overwriting everything. |
| `LOAD_OP_DONT_CARE` | Contents undefined | You will write every pixel yourself, e.g. a fullscreen pass. Cheapest. |
| `LOAD_OP_LOAD` | Preserve existing | You are compositing onto previous contents. Most expensive. |
| `STORE_OP_STORE` | Keep the result | Anything you will present or sample. |
| `STORE_OP_DONT_CARE` | Discard | Depth buffers you do not read after the pass. |

A depth attachment you never sample afterwards should use
`LOAD_OP_CLEAR` and `STORE_OP_DONT_CARE`. That is free performance you get by
being honest with the driver.

**`vkCmdBeginRendering` can be called more than once per frame.** Each call is
an independent render "pass" over whatever attachments you name. Chapter 08
uses this: an offscreen scene pass, then a swapchain pass. There is no subpass
machinery involved.

**The clear color is in linear space.** With the `_SRGB` swapchain format
Chapter 03 starts with, the hardware encodes on write. So `{0.2, 0.2, 0.2, 1.0}`
is stored as byte 124 and displays as a mid-grey, not the dark grey the number
suggests — Chapter 03 section 2's table. This surprises people once. It stays true after Chapter 08 moves the encode into a shader: the
clear color then clears a linear image, and the composite pass encodes it the
same way.

---

## 2. What `main` hands the renderer

The roadmap has no graphics abstraction layer: demos call Vulkan directly
(step 10). But `main` has no reason to, and the request it passes each frame is
plain data. Keep it in a header that does not include `vulkan.h`:

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
`VulkanRenderer` in Chapter 04.

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
`debugargs { "--gpu", "RTX" }` in `project "SandboxGame"` — rather than the
project's Debugging page, which the next generation erases.

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
            break;
        }
    }

    renderer.shutdown();     // begins with vkDeviceWaitIdle
    window.shutdown();
    return 0;
}
```

`isMinimized` is `glfwGetFramebufferSize` reporting zero in either dimension,
and `waitEvents` is `glfwWaitEvents`. `Skipped` needs no handling here: it means
"nothing was drawn this time", and the next iteration simply tries again.

Animating the clear color from elapsed time is worth the three lines: a static
color cannot distinguish "presenting correctly at 165 fps" from "presented once
and hung".

---

## 4. Stressing it

This is the milestone the roadmap gates on, so actually run the list:

| Action | What it exercises | What failure looks like |
| --- | --- | --- |
| Drag a window edge, release, repeat twenty times | Recreation on each release (Windows freezes the loop during the drag itself; Chapter 02 section 4) | Validation spam, or a hang from the fence-reset bug in Chapter 04 |
| Maximize and restore repeatedly | Large extent jumps | Stale image views |
| Minimize, wait, restore | Zero-extent handling | Busy-wait at 100% CPU, or a zero-extent swapchain error from validation |
| Minimize, then close from the taskbar | The minimized wait still reaching `shouldClose` | The process never exits |
| Drag between monitors at different scaling | Extent re-query | Stretched or blurry output from cached capabilities |
| Alt-tab away and back | Surface loss on some drivers | `VK_ERROR_SURFACE_LOST_KHR` |
| Close immediately after a resize | Shutdown right after recreation | Destroying in-use objects |
| Switch present mode at runtime (once Chapter 07 has the picker) | Recreation outside the resize path | A hang or validation error from anything sized at startup |
| The same, with the image count forced to change | `renderFinished` resizing | Indexing past the end of `renderFinished` if you sized from `FRAMES_IN_FLIGHT` |

The last row needs help to mean anything. Whether a present-mode switch changes
the image count is up to the driver, so force it: temporarily make Chapter 03's
`minImageCount + 1` into `+ 2` whenever the requested mode is not FIFO. Every
switch then changes the count, which is exactly the case Chapter 04's
per-image semaphores exist for.

---

## Exit check

- [ ] The window shows a smoothly animating color.
- [ ] The runtime checks Chapters 02, 03, and 04 left for a running program
      pass: the GPU and swapchain log lines, the leaked-device and
      missing-layer tests, the frame-slot log, and the `--gpu` and `--present`
      options.
- [ ] **Synchronization validation is proven on.** Temporarily change the
      end-of-frame barrier's source access from
      `VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT` to `VK_ACCESS_2_NONE`. The
      rendering's writes are then never made available before the transition
      to `PRESENT_SRC_KHR`, and sync validation must report
      `SYNC-HAZARD-WRITE-AFTER-WRITE` on the first frame — the ID in the
      brackets Chapter 02's callback prints. If it reports
      nothing, it is off — check for a `vkconfig` override (Chapter 01 section
      5) before trusting any "no validation errors" result below. Put the
      barrier back afterwards.
- [ ] Every row of the stress table passes with zero validation errors.
- [ ] A minimized window uses no measurable CPU.
- [ ] `SandboxGame/Main.cpp` includes no Vulkan header directly. (A courtesy,
      not a rule: demo code in step 10 calls Vulkan freely.)

Next: [06 — Shaders and Pipelines](06-Shaders-And-Pipelines.md)
