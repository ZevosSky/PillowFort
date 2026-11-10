# 09 — The Demo Harness

**Goal:** the triangle runs as the first of several demos, picked from an ImGui
panel, and a new demo is one folder, one class, and one line in `main`.

**ROADMAP:** step 10.

**Module:** `Demos`, namespace `pf::demos` — the interface — with each demo in
its own folder and nested namespace (`Source/PillowFort/Demos/Triangle/`,
`pf::demos::triangle`). Smaller changes to `VulkanGraphics`
(`pf::vulkan_graphics`), `DebugPanels` (`pf::debug_panels`),
`SandboxGame/Main.cpp`, and `premake5.lua`.

**Prerequisites:** Chapter 8, built and running. It also uses, from earlier:

- [Chapter 5, section 2](05-First-Frame.md#2-what-main-hands-the-renderer)
  (`FrameRequest`) and [section 3](05-First-Frame.md#3-where-the-loop-lives)
  (the frame loop in `main`, `parseSettings`).
- Chapter 6, sections [1](06-Shaders-And-Pipelines.md#1-the-shader-build),
  [2](06-Shaders-And-Pipelines.md#2-the-triangle-shaders),
  [7](06-Shaders-And-Pipelines.md#7-drawing), and
  [8](06-Shaders-And-Pipelines.md#8-when-the-second-pipeline-arrives) (the
  shader glob and executable-relative paths, the fullscreen vertex shader, where
  the triangle's pipeline lives, and `GraphicsPipelineDesc` with
  `createGraphicsPipeline`).
- Chapter 7, sections
  [4](07-ImGui.md#4-input-forwarding-and-why-the-roadmap-is-right),
  [7](07-ImGui.md#7-a-panel-worth-having-on-day-one),
  [9](07-ImGui.md#9-toward-the-shader-parameter-workbench), and
  [10](07-ImGui.md#10-who-owns-the-panels) (the `WantCapture*` filter, placing a
  window with `SetNextWindowPos` and `ImGuiCond_FirstUseEver`,
  `ShaderParameters` and why its panel is a free function, and the renderer
  owning the panels, with the frame loop's order).

<a id="ui-stage-boundary"></a>

This chapter's listings and exit checks build floating windows (Frame, Shader
and a Demos picker at the top right), and its `beginDemoPanel` opens a native
ImGui window that `ImGui::End` closes. Later in the reference, these windows
become sections of one shared workspace with a different closing call;
details below.

<details>
<summary>Later stages change this chapter's code</summary>

The assembled reference uses a pinned demo combo and a global scale control
with fixed Scene / Render / Stats categories, an optional later redesign
taught in this chapter's closing
[control-workspace transfer](#control-workspace-transfer). Do not mix the two.
The reference's `beginPanel`, `beginDemoPanel` and `appendPanel` open sections
of one shared workspace and are always closed with `debug_panels::endPanel`,
even when their category is hidden and nothing was opened; `ImGui::End` there
would close a window the call never began.

</details>

This chapter adds almost no Vulkan. It moves code you already have to where it
belongs, so that every chapter after it can say "a demo" and mean one folder.
The new ideas are about ownership and timing — who creates what, who calls
whom, and when — and those are worth slowing down for, because every later
demo depends on getting them right once.

### What changes, and where

```text
Source/PillowFort/
  Demos/                                new module
    Demo.h                              section 2: the interface and what it is handed
    Triangle/
      TriangleDemo.h, .cpp              section 6: new
      ShaderParameters.h, .cpp          section 6: moved here from VulkanGraphics/
    Gradient/
      GradientDemo.h, .cpp              section 8: new, the second demo
  VulkanGraphics/
    SceneTargets.h, .cpp                sections 3-4: new
    VulkanResources.h                   section 3: gains FRAMES_IN_FLIGHT
    FrameRequest.h                      section 7: clearColor changes meaning
    VulkanRenderer.h, .cpp              section 5: loses the triangle, gains the active demo
  DebugPanels/
    DemoPanel.h, .cpp                   section 6: new, where every demo's panel opens
    ImGuiDebugPanels.h, .cpp            section 7: gains drawDemoPicker
Source/SandboxGame/Main.cpp             section 7: the demo list, --demo, the loop; section 8: one line
Shaders/Gradient/                       section 8: new
premake5.lua                            section 8: "Shaders" joins the include path
```

Files are added, moved, and deleted here, so **rerun `GenerateProjects.bat`**
once you have them on disk. Every new file starts with the house banner
(`@author`, `@brief`, `@copyright`) that Chapter 2, section 0 showed; the
listings from here on leave it out. `VulkanGraphics/ShaderParameters.h` and
`.cpp` are deleted, not left beside their copies: in their old namespace they
would still compile, as a second `ShaderParameters` that nothing uses and that
the next person to change the triangle's sliders edits by mistake.

---

## 1. Why a harness, and where the line falls

ROADMAP's third goal is *make a new demo cheap: one folder, one class, one line
to register it.* Right now a demo is the opposite. The triangle is spread
across `VulkanRenderer` (its pipeline layout, its pipeline, its parameters, the
draw in `recordFrame`), `VulkanGraphics/ShaderParameters.*` (its panel), and
`main` (the animated clear color and the line that sets `parameters.time`). A
second demo would have to edit all of them, and a third would have to work
around the second.

The harness draws one line through the frame and puts each piece on a side of
it. The line is the one Chapter 8, section 4 already drew in `recordFrame`, with
the comments `The scene's part` and `The engine's part`:

| The engine — `VulkanRenderer`, `ImGuiDebugPanels` | A demo — `Demos/<Name>/` |
| --- | --- |
| Instance, device, swapchain, frames in flight, submit and present | Its pipelines and pipeline layouts |
| The window-sized targets: the scene color image now, the depth buffer from Chapter 10, the multisampled images from Chapter 18 | Its own buffers, images, descriptor pools, and samplers |
| The composite pass and ImGui, into the swapchain image | Everything recorded in the scene's part of the frame |
| The pipeline cache, the immediate-submit pool and fence, the allocator | Its parameters and the ImGui panel that edits them |
| The panels every demo shares: frame statistics, present mode, the demo picker | Reacting to input that ImGui did not take |

Ownership of the window-sized targets follows the index's "Who owns what in a
frame": the engine creates and rebuilds them and tells the demo when they
change; the demo decides what to put in them. Section 4 says why the *scene
part* belongs to the demo even though the images do not.

So, out of `VulkanRenderer` and into `Demos/Triangle/`: `createTrianglePipeline`,
`m_pipelineLayout`, `m_pipeline`, `m_triangleParameters` and its accessor, the
triangle's draw, and `ShaderParameters.*`. Out of `main`: the animated clear
color and the per-frame parameter lines. Everything else stays.

---

## 2. The `Demo` interface

**This is `Source/PillowFort/Demos/Demo.h`.** ROADMAP step 10 lists the five
functions a demo has — setup, update, record, resize, teardown — and the class
is those five, a name, and one optional CPU-only hook, `Deactivate`, which the
end of this section explains. Here is the whole header first, because its
three small structs are the subject of section 3 (and, for `FrameInput`,
section 7) and the class is the subject of this one:

```cpp
// Source/PillowFort/Demos/Demo.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/VulkanGraphics/SceneTargets.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"
#include "PillowFort/Window/GlfwWindow.h"

#include <vulkan/vulkan.h>

#include <cstdint>
#include <span>

namespace pf::demos {

// Handed to Setup. Borrowed handles, valid until Teardown returns; a demo keeps
// a copy, because its other functions need them too.
struct DemoContext
{
    vulkan_graphics::VulkanContext vulkan;                          // Chapter 08: device, queue, allocator, ...
    VkPipelineCache                pipelineCache = VK_NULL_HANDLE;  // Chapter 06 section 6
    vulkan_graphics::SceneFormats  formats;                         // what scene pipelines declare
};

// Handed to Update once per frame, between ImGui::NewFrame and drawFrame.
struct FrameInput
{
    float                          deltaSeconds   = 0.0f;   // since the last frame, at most 0.1
    float                          elapsedSeconds = 0.0f;   // since startup
    std::span<const window::Event> events;                  // what ImGui did not capture
};

// Handed to Record once per frame, after this frame slot's fence wait.
struct RecordContext
{
    VkCommandBuffer               commandBuffer = VK_NULL_HANDLE;   // begun; record into it, nothing else
    uint32_t                      frameIndex    = 0;                // which per-frame copy is free
    vulkan_graphics::SceneTargets targets;
};

class Demo
{
public:
    Demo() = default;
    Demo(const Demo&) = delete;
    Demo& operator=(const Demo&) = delete;

    virtual ~Demo() = default;   // SandboxGame deletes demos through this type

    virtual const char*          Name() const = 0;                                          // section 2
    virtual InitializationResult Setup(const DemoContext& context) = 0;                     // section 2
    virtual InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) = 0;  // section 2
    virtual void                 Update(const FrameInput& input) = 0;                       // section 7
    virtual InitializationResult Record(const RecordContext& frame) = 0;                    // section 4
    virtual void                 Teardown() = 0;                                            // section 2
    virtual void                 Deactivate() {} // CPU-only input release before detach or resource rebuild
};

} // namespace pf::demos
```

**Why a class with virtual functions.** The renderer has to call code it was
compiled without knowing — the gradient in section 8, the ocean in Chapter 29.
That is what a virtual function is for, and it is one of the few places in this
project where runtime polymorphism earns its keep. Five functions that share
state (the pipelines `Setup` makes are the ones `Record` binds and `Teardown`
destroys) are a class, not five callbacks. The destructor is virtual because
`main` owns the demos as `std::unique_ptr<Demo>` and deletes them through the
base type; without it, that delete is undefined behaviour, and in practice the
derived destructor never runs.

The base forbids copying, which also keeps derived resource-owning demos from
being implicitly moved. The registry can move its `unique_ptr` while the demo
it points to stays at the same address. Borrowed `DemoContext` and
`RecordContext` remain copyable. Keep a derived demo's existing CPU constructor;
these declarations do not require a second default constructor there.

Every lifecycle function is pure, including `Resize`, which the triangle leaves
empty.
Reading a demo's header then tells you its whole lifecycle, and a demo that
needs `Resize` cannot forget it by inheriting a default that does nothing.

The functions, in the order they are called:

- **`Name`** — the label in the picker (section 7), and the prefix on the
  demo's error messages.
- **`Setup`** — creates everything that does not depend on the window's size:
  pipeline layouts, pipelines, descriptor pools, buffers whose size is the
  demo's own choice. It is fallible and returns `InitializationResult`, the
  convention from Chapter 2, section 0. **The constructor does nothing that
  can fail and touches no GPU object**: a demo is constructed in `main` before
  anyone knows whether it will ever be shown.
- **`Resize`** — creates or rebuilds whatever depends on the scene targets:
  images sized to the window (Chapter 33's accumulation image), and descriptors
  or ImGui textures that point at the targets' views. The engine rebuilds its own
  targets and then tells the demo, which rebuilds its own, so `recreateSwapchain`
  never has to know a demo's images (that is why ROADMAP step 10 lists `resize`).
  The harness calls it **right after every successful `Setup`** and again after
  every swapchain recreation, even a present-mode switch that left the extent
  unchanged (Chapter 7, section 7): the handles changed, so `Resize` rebuilds
  without comparing. It runs after the device wait inside
  `VulkanSwapchain::recreate`, so a `Resize` that destroys the demo's old
  window-sized images is safe, and it is fallible like `Setup` (section 5 says
  what a failure does).
- **`Update`** — once per frame, before anything is recorded: CPU-side state,
  input, and the demo's ImGui panel. Section 7.
- **`Record`** — once per frame, into the frame's command buffer: the scene's
  part of the frame. Return success only after recording its complete part;
  a required upload or recording failure returns a failure to the renderer.
  Section 4.
- **`Teardown`** — destroys everything `Setup` and `Resize` created.

`Deactivate` is the one function with a default, and it is CPU-only: the
harness calls it just before every `Teardown`. It exists because the demo
object outlives its GPU resources (`main` keeps it for the whole run), and so
does any input state it holds. Nothing in this chapter overrides it. From
Chapter 10, camera demos use it to forget held keys, held buttons and queued
mouse motion; without that, a key released while another demo is active never
reaches the camera, which is still moving when you switch back to it. It must
not call `Update`, which draws UI and may touch resources that a failed `Setup`
never created.

Two rules about `Teardown` make switching work, and both are easy to break
without noticing:

- **It must be safe after a `Setup` that failed partway.** The harness calls it
  whenever `Setup` or any `Resize` fails, to free whatever got created.
  This is the same rule as `VulkanRenderer::shutdown` after a partial
  `initialize`: Vulkan's destroy functions accept a null handle, so destroying
  everything unconditionally is correct. (VMA's destroy functions are the
  exception, Chapter 8, section 4, but a demo is only set up while the
  allocator exists.) `Setup`'s first line copies the context, so `Teardown`
  always has a device to pass.
- **It must leave the demo able to `Setup` again.** A demo is set up every time
  you switch to it and torn down every time you switch away, many times in one
  run. Resetting each handle to `VK_NULL_HANDLE` after destroying it is what
  makes the second `Setup` start clean. CPU-side state — slider values,
  colors — is deliberately *not* reset, so switching away and back keeps what
  you had dialled in.

> **Jump:** Until now you could read a frame top to bottom: `main`'s loop
> called the renderer, and `recordFrame` said in order what went into the
> command buffer. From here on the renderer calls into code it does not know,
> at moments it chooses. Keep in mind that a demo's functions run in an order
> the *harness* guarantees, not one you can see at a call site — Setup, then
> Resize, then Update and Record once per frame, with Resize again whenever the
> targets change, and Teardown last. Section 9 is that order as a table; keep it
> open while writing your first demo.

---

## 3. What a demo is handed

A demo needs Vulkan handles, but the roadmap rules out the usual shortcuts:
no singletons, no service locators, nothing global a demo could reach for. So
everything a demo uses arrives as an argument, in one of four small structs,
each handed over at the moment it becomes valid: `DemoContext` to `Setup`,
`SceneTargets` to `Resize`, `FrameInput` to `Update` (section 7), and
`RecordContext` to `Record`.

### `DemoContext`, for `Setup`

- **`vulkan`** is Chapter 8's `VulkanContext` — device, physical device,
  graphics queue, the immediate-submit pool and fence, and the allocator. It
  is everything `createBuffer`, `uploadToBuffer`, and `immediateSubmit` need,
  which is why Chapter 8 made those free functions over this struct rather
  than renderer members. It is passed **by value**: it is six handles that
  never change after `VulkanRenderer::initialize`, so a copy is still a borrow.
  And those functions take `VulkanContext&`, non-const, so the demo's own copy
  is exactly what it needs to pass them.
- **`pipelineCache`** is Chapter 6's. Every demo builds its pipelines through
  the same cache, so the one file `shutdown` saves covers every demo you have
  visited, and switching back to a demo finds its pipelines already compiled
  in the cache.
- **`formats`** says what a pipeline drawing in the scene pass must declare.

### `SceneFormats` and `SceneTargets`

**This is the first half of `Source/PillowFort/VulkanGraphics/SceneTargets.h`.**
The engine's window-sized images have two kinds of facts about them, which
change at different times, so they are two structs:

```cpp
// Source/PillowFort/VulkanGraphics/SceneTargets.h
#pragma once

#include <vulkan/vulkan.h>

namespace pf::vulkan_graphics {

// What a pipeline drawing inside the standard scene pass must declare. Fixed
// between a demo's Setup and its Teardown: a Resize changes the extent and the
// handles, never these.
struct SceneFormats
{
    VkFormat              color   = VK_FORMAT_R16G16B16A16_SFLOAT;   // Chapter 08's scene target
    VkFormat              depth   = VK_FORMAT_UNDEFINED;             // Chapter 10's depth buffer
    VkSampleCountFlagBits samples = VK_SAMPLE_COUNT_1_BIT;           // Chapter 18's MSAA
};

// Borrowed, not owned: VulkanRenderer creates these images and rebuilds them on
// every swapchain recreation. Valid until the demo's next Resize.
struct SceneTargets
{
    SceneFormats formats;
    VkExtent2D   extent{};
    VkImage      colorImage = VK_NULL_HANDLE;   // what the composite pass samples
    VkImageView  colorView  = VK_NULL_HANDLE;
};
```

**Formats go to `Setup`; handles go to `Resize` and `Record`.** A pipeline
bakes in its attachment formats (Chapter 6, section 4), so a demo needs them
before it can build one, and they stay the same for as long as the pipeline
does. The image handles and the extent change on every recreation, so a demo
must never keep them past the next `Resize` — which is also why `Record` is
handed them fresh every frame rather than trusting a copy.

**Why `depth` exists before anything uses it.** Chapter 10 gives the standard
scene pass a depth attachment, and dynamic rendering requires every pipeline
drawn in that pass to declare the same depth format. Both demos in this chapter
pass `context.formats.depth` to `GraphicsPipelineDesc::depthFormat` —
`UNDEFINED` today — so they keep working unchanged when Chapter 10 sets it.
`samples` waits for Chapter 18's MSAA the same way; nothing reads it until
then.

The color format is the literal that `sceneTargetInfo`, the file-scope helper
in `VulkanRenderer.cpp`, used in Chapter 8. Now that it has a name, that
function uses the name, fully qualified because the helper sits above the
namespace block:

```cpp
        .format      = pf::vulkan_graphics::SceneFormats{}.color,   // R16G16B16A16_SFLOAT; Chapter 09 named it
```

### `FRAMES_IN_FLIGHT`

Chapter 4 put `FRAMES_IN_FLIGHT` in `VulkanRenderer.h`, where only the
renderer needed it. Demos need it now — Chapter 8, section 6's rule is one copy
of anything written per frame, and a demo sizes those arrays with it — and a
demo should not include the renderer to get a constant. **This is
`VulkanResources.h`**, beside `VulkanContext`; delete the line from
`VulkanRenderer.h`, which already includes this file:

```cpp
namespace pf::vulkan_graphics {

// Chapter 04's constant, moved here from VulkanRenderer.h in Chapter 09 so that
// demos can size their per-frame copies without including the renderer.
static constexpr uint32_t FRAMES_IN_FLIGHT = 2;
```

### `RecordContext`, for `Record`

The command buffer, the scene targets, and `frameIndex` — which of the
`FRAMES_IN_FLIGHT` slots this frame is using. `Record` is called from
`recordFrame`, which runs after `drawFrame` has waited on that slot's fence, so
**`Record` is the first point in the frame where the slot's per-frame buffers
are free to write**, and where a buffer the GPU wrote for that slot
`FRAMES_IN_FLIGHT` frames ago is safe to read back (Chapter 20, section 9 adds
the step that makes those writes visible to the CPU). `Update` runs before the
fence wait, so it must not touch per-frame GPU memory at all; section 9 has the
order.

### What a demo makes for itself

Anything not in those structs. In particular:

- **Descriptor pools.** The renderer's pool from Chapter 8 is sized for the
  composite set and nothing else. A shared pool would have to be sized for
  every demo at once, which is exactly the cross-demo coupling the harness is
  removing, so each demo creates a pool sized for its own sets in `Setup` and
  destroys it in `Teardown` — which frees every set allocated from it.
- **Samplers**, with the filtering and addressing its textures want.
- **ImGui textures** (`ImGui_ImplVulkan_AddTexture`, Chapter 7, section 2),
  removed again in `Teardown` — or in `Resize`, for one showing a target that
  was just rebuilt. Section 5 makes sure ImGui still exists when `Teardown`
  runs.

> **Jump:** a demo now has four lifetimes to keep apart, and each struct
> belongs to one. The demo *object* lives for the whole run (`main` owns it).
> What `Setup` creates lives until `Teardown` — possibly many times per run.
> What `Resize` is handed lives until the next `Resize`. And `frameIndex`
> names one slot of a per-frame copy for one frame. Most bugs in a new demo are
> something used outside the lifetime it came with: a target's view kept past
> the next `Resize`, or a per-frame buffer written in `Update`, before its
> slot's fence has been waited on.

---

## 4. The scene part: Chapter 8's contract, now across a boundary

The contract between the two halves of the frame is Chapter 8, section 4's (and
the index's "Who owns what in a frame"), and the demo now signs it: it receives the
scene target in `SHADER_READ_ONLY_OPTIMAL` (or `UNDEFINED` on the first frame
after it was created), writes every pixel, and hands the target back in
`SHADER_READ_ONLY_OPTIMAL` with its writes visible to the composite pass's
fragment shader. Everything in between is its business: compute dispatches,
shadow passes, a rasterized pass, more drawing after that pass.

**Why the demo owns the whole scene part, not just the draws inside it.** The
obvious alternative is for the renderer to open the scene's rendering scope —
transition, clear, `vkCmdBeginRendering` — and call the demo inside it. That
breaks the moment a demo is not a single rasterized pass. Chapter 33's path
tracer writes every pixel of the scene image from a compute shader and never
rasterizes at all; an engine-opened scope would clear its work. So the demo
gets the command buffer and the targets and records what it likes, and the
engine's only demand is the contract.

The cost is that every rasterizing demo would write the same forty lines: the
start-of-frame barrier, the attachment, the rendering info, viewport and
scissor, the end, and the hand-back barrier. Those forty lines already have two
users before any second demo exists — the triangle, and the renderer itself,
which must still fill the scene target when no demo is active (section 5) — so
they become three engine functions.

**This is the second half of `SceneTargets.h`**, and `SceneTargets.cpp`:

```cpp
// Opens the standard scene pass: the color target from UNDEFINED to
// COLOR_ATTACHMENT_OPTIMAL, a rendering scope over it, and a viewport and
// scissor covering it. clearColor null means LOAD_OP_DONT_CARE, for a demo that
// writes every pixel itself.
void beginScenePass(VkCommandBuffer commandBuffer, const SceneTargets& targets,
                    const VkClearColorValue* clearColor);

// Ends the scope. Leaves the color target in COLOR_ATTACHMENT_OPTIMAL, last
// written at COLOR_ATTACHMENT_OUTPUT with COLOR_ATTACHMENT_WRITE.
void endScenePass(VkCommandBuffer commandBuffer);

// Chapter 08's contract: hands the color target to the composite pass in
// SHADER_READ_ONLY_OPTIMAL. The defaults describe what endScenePass leaves; a
// demo that wrote the target some other way says how.
void handBackSceneTarget(VkCommandBuffer commandBuffer, const SceneTargets& targets,
                         VkImageLayout         currentLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                         VkPipelineStageFlags2 lastStage     = VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                         VkAccessFlags2        lastAccess    = VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);

} // namespace pf::vulkan_graphics
```

Three functions rather than a begin/end pair, because the end of the
rendering scope and the end of the scene part are different moments. A demo
that draws something after the main pass — Chapter 21's particles, blended
over the scene with the depth buffer read-only — opens its own scope between
`endScenePass` and `handBackSceneTarget`. That is why `endScenePass` documents
the state it leaves: the next barrier is the demo's to write, and its source
half is that last writer. It is one line today, and it is still worth having:
every rasterizing demo then reads begin, draw, end, hand back, and when Chapter
10 adds a depth attachment, the state `endScenePass` leaves the depth buffer in
is documented in one place.

The clear color is a pointer so that "no clear" is expressible: a demo whose
fullscreen pass writes every pixel passes `nullptr` and gets
`LOAD_OP_DONT_CARE`, Chapter 5, section 1's cheapest case.

```cpp
// Source/PillowFort/VulkanGraphics/SceneTargets.cpp
#include "PillowFort/VulkanGraphics/SceneTargets.h"

#include "PillowFort/VulkanGraphics/VulkanBarriers.h"

namespace pf::vulkan_graphics {

void beginScenePass(VkCommandBuffer commandBuffer, const SceneTargets& targets,
                    const VkClearColorValue* clearColor)
{
    // Chapter 04's "Offscreen target, start of frame" row. The last reader was
    // the previous frame's composite pass, so this is a write after a read:
    // FRAGMENT_SHADER to wait for, nothing to flush.
    transitionImage(commandBuffer, targets.colorImage,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);

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

    const VkRenderingInfo renderingInfo{
        .sType                = VK_STRUCTURE_TYPE_RENDERING_INFO,
        .renderArea           = { { 0, 0 }, targets.extent },
        .layerCount           = 1,
        .viewMask             = 0,
        .colorAttachmentCount = 1,
        .pColorAttachments    = &colorAttachment,
        .pDepthAttachment     = nullptr,
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

void endScenePass(VkCommandBuffer commandBuffer)
{
    vkCmdEndRendering(commandBuffer);
}

// The default arguments live on the declaration only.
void handBackSceneTarget(VkCommandBuffer commandBuffer, const SceneTargets& targets,
                         VkImageLayout currentLayout,
                         VkPipelineStageFlags2 lastStage, VkAccessFlags2 lastAccess)
{
    // The source half is whatever the demo did last; the destination half is
    // the composite pass, and never changes.
    transitionImage(commandBuffer, targets.colorImage,
                    currentLayout, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    lastStage, lastAccess,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
}

} // namespace pf::vulkan_graphics
```

Both barriers are Chapter 8's, moved, and both are rows of Chapter 4's
cookbook: "Offscreen target, start of frame" for `beginScenePass`, and "Offscreen
target, drawn and about to be composited" for `handBackSceneTarget`'s defaults.

`handBackSceneTarget` splits its barrier along the contract: the destination
half is the engine's and fixed, the source half describes what the demo did
last and is a parameter. The defaults are what `endScenePass` leaves, so a
rasterizing demo passes nothing. A compute demo that wrote the target as a
storage image passes `VK_IMAGE_LAYOUT_GENERAL`,
`VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT`, and
`VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT` — Chapter 4's "Compute result sampled
by a later shader" row. Such a demo writes its own *first* barrier too, and
whatever its destination half, the source half stays
`FRAGMENT_SHADER` / `NONE`: the previous user of the image is still last
frame's composite pass, whoever writes it now.

The rest of the contract, which `Record` keeps whether or not it uses the
helpers:

- Record into `frame.commandBuffer` only. Never begin, end, or submit it,
  never touch the swapchain, and leave no rendering scope open.
- Rely on no state the engine set, and expect the engine to rely on none the
  demo set: the composite pass sets its own viewport, scissor, pipeline, and
  descriptor set afterwards.
- Compute recorded at the top of `Record` is not held behind the swapchain
  acquire; the demo's color writes are, even though they go to the offscreen
  target. That can reduce overlap even when the final frame still meets the
  display interval. Chapter 4, section 5 ("Barriers next to semaphores") says
  why the wait covers the whole stage and describes a second submit that can
  separate those waits. Keep this one-submit teaching path until queue/timing
  evidence justifies the additional submission and synchronization work.

> **Jump:** in Chapter 8 the two scene-target barriers sat a few lines apart
> in `recordFrame`, next to the composite pass that depends on them. Now the
> barriers are in demo code and the composite is in the renderer, and nothing
> in C++'s type system connects them — a demo that forgets
> `handBackSceneTarget` compiles. Validation is what checks the contract: core
> validation reports a skipped hand-back as a layout mismatch at the
> composite's draw, and synchronization validation reports access masks that
> do not describe the demo's last writes. Keep in mind that whoever records
> the scene part owns *both* ends of the target's trip through the frame, and
> run every new demo with validation on before believing its picture.

---

## 5. The renderer's side

**This is `VulkanRenderer`, again.** Its class map (Chapter 4's, as grown by
6, 7, and 8) changes in both directions.

It **loses**, with every line that used them in `initialize`, `recordFrame`,
and `shutdown`: `createTrianglePipeline()`, `m_pipelineLayout`, `m_pipeline`,
`m_triangleParameters`, `triangleParameters()`, the `ShaderParameters.h`
include, and the `FRAMES_IN_FLIGHT` constant (section 3). `m_pipelineCache`
stays — it was never the triangle's.

It **gains** a borrowed pointer to the active demo, a string holding why the
last demo was detached, and the functions around them:

```cpp
namespace pf::demos { class Demo; }   // Chapter 09; the renderer only holds a pointer

    // Chapter 09 section 5. Waits for the GPU, tears the current demo down, and
    // sets `demo` up; nullptr leaves none. A demo that fails is detached, here or
    // in a later Resize, and demoError() says why.
    void               switchDemo(demos::Demo* demo);
    demos::Demo*       demo() const      { return m_demo; }
    const std::string& demoError() const { return m_demoError; }   // empty unless a demo failed

    SceneTargets         sceneTargets() const;          // Chapter 09 section 5: what a demo sees of them
    void                 detachDemo(demos::Demo* demo, const InitializationResult& failure);   // section 5

    demos::Demo* m_demo = nullptr;                        // Chapter 09: borrowed; SandboxGame owns every demo
    std::string  m_demoError;                             // Chapter 09: why the last demo was detached
```

The forward declaration goes above the `pf::vulkan_graphics` namespace block,
since `Demo` lives in another namespace; the three functions are public,
beside Chapter 7's; `sceneTargets` and `detachDemo` are private, beside
`createSceneTarget`; the members go after `m_debugPanels`. The header includes
`SceneTargets.h` in place of `ShaderParameters.h`. Only `VulkanRenderer.cpp`,
which calls the demo, includes `Demos/Demo.h` — the header needs the name, not
the class — and it gains `<format>` for `detachDemo`'s message.

`m_demo` is a raw pointer because it is a borrow: `main` owns every demo for
the whole run (section 7), and the renderer only needs to know which one is
active. `nullptr` means none — at startup before the first switch, and after a
demo has failed.

### `sceneTargets`

What a demo sees of Chapter 8's members, assembled on demand so it can never
be stale:

```cpp
SceneTargets VulkanRenderer::sceneTargets() const
{
    return SceneTargets{
        .formats    = SceneFormats{},
        .extent     = m_swapchain.extent(),   // createSceneTarget's extent
        .colorImage = m_sceneImage,
        .colorView  = m_sceneView,
    };
}
```

### `switchDemo`

The one place a demo is set up or torn down while the program runs. A demo's
GPU objects cannot be destroyed while a submitted frame still uses them;
Chapter 6, section 8 gave waiting as the simple answer to a rare change.
`Setup` and `Resize` can each fail, and `Teardown` must release a partial setup.

Keep the demo object's lifetime separate from its activation. The registered
object and its CPU settings survive this sequence; `Teardown` releases its
GPU state. The renderer publishes an active pointer only at the last step:

![Switching demos: request a demo, wait for previous GPU use, deactivate and tear down the old demo, set up the candidate, resize it, and only then publish the active pointer. A failure in Setup or Resize tears the candidate down, retains the error and leaves no active demo.](images/demo-switch-sequence.svg)

For ordinary setup/resize errors, the no-active-demo state must still draw
the renderer's clear and picker. That is the recovery path being tested.
Device loss is a separate fatal rendering failure, not a promise that the
picker can recover a lost device.

<a id="ch09-demo-switch"></a>

#### Attempt CH09-demo-switch: keep a failed demo from stopping the workbench

Implement the switch before opening the answer. Wait before releasing the
old demo, set up the requested demo with the current formats, and call its
first `Resize` before it can record a frame. A null request leaves no demo
active. An initialization failure must release the attempted demo's partial
GPU state, preserve a useful error for the picker, and leave the renderer able
to clear its target and accept another choice. CPU settings remain in the
demo object across a teardown and setup. Test both a successful switch and a
demo whose `Setup` returns failure after creating one resource; the latter
must leave nothing behind (validation names any object still alive at
`vkDestroyDevice`, and `vmaDestroyAllocator` asserts on a leaked allocation)
and let you choose the triangle again.

**Acceptance:** A successful demo receives setup and initial resize before recording; a partial setup failure releases its allocation, shows its error and permits another selection.

**Transfer:** Make Setup succeed but the first Resize fail. Predict active-demo state and cleanup, then verify the picker can still select the triangle.

<details>
<summary>Hint 1: separate the requested object from the active one</summary>

Do not mark a demo active until both setup and its first resize succeed.
Keeping a pointer to the requested object lets you clean up a partial setup
without allowing `Record` to run on it.

</details>

<details>
<summary>Hint 2: give both failure sites the same cleanup path</summary>

The initial `Resize` and a later resize can fail too. Use one helper that
tears down the attempted demo and retains its name and failure message.
Clear the old status when a new attempt starts.

</details>

<details>
<summary>Hint 3: use the current target formats and handles</summary>

Build `DemoContext` from `m_context`, `m_pipelineCache` and
`sceneTargets().formats`. Call `Resize(sceneTargets())` after `Setup`; assign
`m_demo` only after both return success. Chapter 8's `requireSafeDeviceIdle`
must run, and succeed, before the old demo's GPU objects are torn down.

</details>

<details>
<summary>Worked solution: switching and detaching demos</summary>

```cpp
void VulkanRenderer::switchDemo(demos::Demo* demo)
{
    // In-flight frames may still be using the old demo's pipelines and buffers.
    // A user-driven switch accepts a device-idle stall to keep teardown explicit.
    const VkResult idle = requireSafeDeviceIdle(m_device, "switching demos");

    if (m_demo != nullptr)
    {
        m_demo->Deactivate();
        m_demo->Teardown();
        m_demo = nullptr;
    }
    m_demoError.clear();
    if (idle == VK_ERROR_DEVICE_LOST)
    {
        m_demoError = "Device lost while switching demos; no new demo was initialized.";
        Log::error(m_demoError.c_str());
        return;
    }
    if (demo == nullptr) { return; }

    const demos::DemoContext context{
        .vulkan        = m_context,
        .pipelineCache = m_pipelineCache,
        .formats       = sceneTargets().formats,
    };

    // Resize right after Setup, so window-sized things are created in one place.
    if (auto result = demo->Setup(context); !result)
    {
        detachDemo(demo, result);
        return;
    }
    if (auto result = demo->Resize(sceneTargets()); !result)
    {
        detachDemo(demo, result);
        return;
    }
    m_demo = demo;
}

// A demo that failed in Setup or Resize. Teardown frees whatever it got as far
// as creating - it is safe after a partial Setup - and the reason is kept for
// the picker. The renderer carries on without a demo.
void VulkanRenderer::detachDemo(demos::Demo* demo, const InitializationResult& failure)
{
    demo->Deactivate();
    demo->Teardown();
    m_demoError = std::format("{}: {}", demo->Name(), failure.message());
    Log::error(m_demoError.c_str());
}
```

**Why `vkDeviceWaitIdle` is acceptable here.** With two frames in flight, the
GPU may still be executing command buffers that bind the old demo's pipelines
and read its buffers. Destroying them now is a use-after-free on the GPU, which
validation reports and a driver may not survive. The alternatives are waiting
on both frames' fences, or a
deletion queue that retires the old demo's objects after their last submitted
uses complete (Chapter 6, section 8). That machinery stays deferred until hot
reload needs it. A demo switch is rare, and this renderer accepts the wait.
The new demo's `Setup` also compiles pipelines and uploads resources; deferring
destruction would not remove that work. `VulkanSwapchain::recreate` makes the
same trade. `requireSafeDeviceIdle` also checks that the wait
finished: if GPU completion is unknown, it ends the process before anything is
destroyed. On device loss it lets the teardown run, and `switchDemo` then sets
`demoError` and returns without starting another `Setup`; the next `drawFrame`
fails through the existing frame-status path.

**What a failure does.** A demo can fail in
two places: in the `Setup` and first `Resize` that `switchDemo` runs, and in
any later `Resize`, which `recreateSwapchain` runs from inside `drawFrame`. A
return value from `switchDemo` would reach `main` in the first case and nobody
in the second, so both go through `detachDemo` instead. It runs the demo's
`Teardown`, which frees whatever got created, keeps the reason in
`m_demoError`, and leaves **no** demo active — not the previous one, because
restoring it would mean setting it up again, which can fail too. With no demo,
the renderer clears the scene target itself (below), the picker shows the
message (section 7), and you pick something else: a broken demo does not take
the workbench down with it. `m_demoError` is cleared at the start of every
switch, so the message always belongs to the latest attempt.

The complete switching and resize lifecycle is
[VulkanRenderer.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/VulkanRenderer.cpp).

</details>

### `recordFrame`

The scene's part of Chapter 8's `recordFrame` — from the first scene-target
barrier through the second — becomes this:

```cpp
    // ---- The scene's part: the active demo's, or a plain clear without one. ----
    // Either way the scene target ends in SHADER_READ_ONLY_OPTIMAL, written,
    // which is all the engine's part below relies on (Chapter 08 section 4).
    const SceneTargets targets = sceneTargets();
    if (m_demo != nullptr)
    {
        const auto recorded = m_demo->Record({
            .commandBuffer = commandBuffer,
            .frameIndex    = m_frameIndex,   // drawFrame waited on this slot's fence
            .targets       = targets,
        });
        if (!recorded) { return recorded; }
    }
    else
    {
        const VkClearColorValue clearColor{ { request.clearColor[0], request.clearColor[1],
                                              request.clearColor[2], request.clearColor[3] } };
        beginScenePass(commandBuffer, targets, &clearColor);
        endScenePass(commandBuffer);
        handBackSceneTarget(commandBuffer, targets);
    }
```

Without a demo, the composite pass still samples the scene target, so
something must keep the contract: the renderer clears it, through the same
helpers a demo uses. That is the second user section 4 counted, and the new
meaning of `FrameRequest::clearColor` (section 7). `m_frameIndex` has not been
advanced yet at this point — `drawFrame` does that after present — so it names
the slot whose fence was just waited on. A failed demo result returns before
the composite samples the target. Chapter 4 then returns `Failed` without
resetting the fence or submitting; Chapter 7's guarded discard closes a UI
frame that has not reached `Render`. This is terminal for the run, unlike a
`Setup` or `Resize` failure during a safe demo switch. The engine's part below
is unchanged from Chapter 8, including its checked command-buffer end and
success result; its `viewport` and `scissor` locals stay with it.

### `recreateSwapchain`

Chapter 8 ended it with `writeCompositeSet()`. The demo is told last, after
every engine target it might refer to has been rebuilt:

```cpp
    writeCompositeSet();                                  // section 6, one binding

    // Chapter 09: the engine's targets are rebuilt; now the demo rebuilds what
    // it owns that depends on them. Still after vkDeviceWaitIdle. A demo that
    // cannot is detached, and the frame goes on without it.
    if (m_demo != nullptr)
    {
        if (const auto resized = m_demo->Resize(sceneTargets()); !resized)
        {
            detachDemo(m_demo, resized);
            m_demo = nullptr;
        }
    }
    return RecreateResult::Recreated;
}
```

A failure here is handled according to who failed. The engine's own
`createSceneTarget` failing leaves the composite pass nothing to sample, so the
frame fails and the program shuts down; a demo's `Resize` failing leaves the
engine's targets fine, so only the demo is detached, here, before anything
else is recorded, because with its window-sized images missing its next
`Record` would use destroyed handles.

### `shutdown`

The demo goes first, right after the wait — before the debug panels, which
were first until now:

```cpp
void VulkanRenderer::shutdown()
{
    if (m_device != VK_NULL_HANDLE)
    {
        (void)requireSafeDeviceIdle(m_device, "shutting down the renderer");

        // Chapter 09: the demo first. It may hold ImGui textures, which need the
        // backend alive, and VMA allocations, which vmaDestroyAllocator checks for.
        if (m_demo != nullptr)
        {
            m_demo->Deactivate();
            m_demo->Teardown();
            m_demo = nullptr;
        }

        m_debugPanels.shutdown();   // Chapter 07 section 10: right after the demo
```

Both reasons in the comment are real. `ImGui_ImplVulkan_RemoveTexture` needs
the backend that `m_debugPanels.shutdown` destroys, and with the demo torn down
before `vmaDestroyAllocator` (the last call, Chapter 8's class map), the
allocator's assertion is a leak check on every demo for free: a demo that
forgets a `destroyBuffer` stops the Debug build at exit. Remove the triangle's
`vkDestroyPipeline` and `vkDestroyPipelineLayout` lines further down; its
`Teardown` does that now.

In `initialize`, the `createTrianglePipeline()` call goes; nothing replaces it,
because no demo exists yet when the renderer initializes. `main` makes the
first switch (section 7).

---

## 6. The triangle becomes a demo

**This is `Source/PillowFort/Demos/Triangle/`.** Chapter 7, section 9 said
`ShaderParameters` would move into the triangle demo's folder at this step, and
designed it to make that move a file copy: the struct and its panel never knew
they were on the renderer. Move both files, and change their namespace:

```cpp
// Source/PillowFort/Demos/Triangle/ShaderParameters.h
// Moved here from VulkanGraphics/ by Chapter 09: the triangle's, not the engine's.
#pragma once

namespace pf::demos::triangle {
```

`ShaderParameters.cpp` changes its include to
`"PillowFort/Demos/Triangle/ShaderParameters.h"` and its namespace to match.
The struct is unchanged, and so is `drawShaderParameters` except for its
placement: everything from the `scale` local through `ImGui::Begin`, which the
end of this section replaces with a helper every demo's panel uses.

**Why a namespace per demo.** `ShaderParameters` and `drawShaderParameters` are
good names for the triangle's parameters, and they will be good names for the
next demo's too. Two demos each defining `pf::demos::ShaderParameters` is a
one-definition-rule violation, and two `drawShaderParameters(ShaderParameters&)`
with different structs link into one library as the same symbol — `LNK2005` if
you are lucky, the wrong panel if you are not. A nested namespace per demo,
named after its folder in lower case, makes every name inside a demo private to
it without anyone having to coordinate.

The class itself is the other half of what leaves the renderer. Its members
are the renderer's old triangle members under new names, plus Chapter 5's
clear color, which was always really the triangle's background:

```cpp
// Source/PillowFort/Demos/Triangle/TriangleDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Demos/Triangle/ShaderParameters.h"

namespace pf::demos::triangle {

class TriangleDemo final : public Demo
{
public:
    const char*          Name() const override { return "Triangle"; }
    InitializationResult Setup(const DemoContext& context) override;
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override;
    void                 Update(const FrameInput& input) override;
    InitializationResult Record(const RecordContext& frame) override;
    void                 Teardown() override;

private:
    DemoContext      m_context;                           // borrowed, from Setup
    VkPipelineLayout m_pipelineLayout = VK_NULL_HANDLE;   // was VulkanRenderer's
    VkPipeline       m_pipeline       = VK_NULL_HANDLE;   // was VulkanRenderer's
    ShaderParameters m_parameters;                        // was m_triangleParameters
    VkClearColorValue m_clearColor{ { 0.05f, 0.05f, 0.08f, 1.0f } };   // was FrameRequest's
};

} // namespace pf::demos::triangle
```

`final` says nothing derives from it, which lets the compiler call its
functions directly when it can see the type, and says to a reader that this is
a leaf.

`Setup` is `createTrianglePipeline` with the renderer's members replaced by the
context's. `Update` is the three lines `main` used to run for the triangle,
plus the clear color. `Record` is the triangle's part of Chapter 8's
`recordFrame`, with the helpers from section 4 in place of the barriers and
the scope:

```cpp
// Source/PillowFort/Demos/Triangle/TriangleDemo.cpp
#include "PillowFort/Demos/Triangle/TriangleDemo.h"

#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"

#include <cmath>
#include <cstddef>

namespace pf::demos::triangle {

// Chapter 06 sections 4, 5, and 8 with Chapter 08 section 5's push constant
// range - VulkanRenderer::createTrianglePipeline, moved.
InitializationResult TriangleDemo::Setup(const DemoContext& context)
{
    m_context = context;   // first, so Teardown works however far this gets

    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
        .offset     = 0,
        .size       = sizeof(ShaderParameters),
    };
    static_assert(sizeof(ShaderParameters) <= 128, "Push constant budget exceeded.");

    // Chapter 08 section 8: GLSL starts the vec4 baseColor on a 16-byte boundary,
    // and padding0 is what puts the C++ member there too.
    static_assert(offsetof(ShaderParameters, baseColor) == 16, "ShaderParameters no longer matches its GLSL block.");

    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 0,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    VkPipelineLayout createdPipelineLayout = VK_NULL_HANDLE;
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &createdPipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the triangle.");
    }
    m_pipelineLayout = createdPipelineLayout;

    const vulkan_graphics::GraphicsPipelineDesc triangle{
        .vertexShader   = "Triangle/Triangle.vert.spv",
        .fragmentShader = "Triangle/Triangle.frag.spv",
        .colorFormats   = { &m_context.formats.color, 1 },
        .depthFormat    = m_context.formats.depth,   // none yet; matches the pass when Chapter 10 adds one
        .layout         = m_pipelineLayout,
    };
    m_pipeline = vulkan_graphics::createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache,
                                                         triangle);
    if (m_pipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the triangle pipeline failed.");
    }
    return InitializationResult::success();
}

// The triangle owns nothing sized to the window.
InitializationResult TriangleDemo::Resize(const vulkan_graphics::SceneTargets& /*targets*/)
{
    return InitializationResult::success();
}

void TriangleDemo::Update(const FrameInput& input)
{
    drawShaderParameters(m_parameters);   // the panel from Chapter 07 section 9
    m_parameters.time = input.elapsedSeconds;

    // Chapter 05's animated clear color, now the triangle's own background.
    m_clearColor.float32[0] = 0.5f + 0.5f * std::sin(input.elapsedSeconds);
}

InitializationResult TriangleDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;

    vulkan_graphics::beginScenePass(commandBuffer, frame.targets, &m_clearColor);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipeline);
    vkCmdPushConstants(commandBuffer, m_pipelineLayout,
                       VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(ShaderParameters), &m_parameters);
    vkCmdDraw(commandBuffer, 3, 1, 0, 0);   // 3 vertices, 1 instance

    vulkan_graphics::endScenePass(commandBuffer);
    vulkan_graphics::handBackSceneTarget(commandBuffer, frame.targets);
    return InitializationResult::success();
}

// Safe after a partial Setup: destroying a null handle is a no-op. Leaves the
// demo as Setup found it, so switching back to it sets it up again.
void TriangleDemo::Teardown()
{
    vkDestroyPipeline(m_context.vulkan.device, m_pipeline, nullptr);
    vkDestroyPipelineLayout(m_context.vulkan.device, m_pipelineLayout, nullptr);
    m_pipeline       = VK_NULL_HANDLE;
    m_pipelineLayout = VK_NULL_HANDLE;
}

} // namespace pf::demos::triangle
```

Three details:

- **`.colorFormats` points at `m_context`.** `GraphicsPipelineDesc` holds a
  `std::span`, which does not own what it points at; Chapter 8 pointed it at a
  local that lived until the call returned. A member lives at least that long.
- **`elapsedSeconds` is the same clock as before.** Chapter 5 computed it from
  `startTime` in `main`, and `main` still does (section 7), so `time` and the
  clear color animate exactly as they did — which is what the exit check
  compares.
- **The shaders do not move.** They have lived in `Shaders/Triangle/` since
  Chapter 6, which is already the per-demo shader folder the index asks for,
  and Chapter 6, section 1's glob mirrors them to
  `Shaders/Triangle/*.spv` beside the executable. The paths in the desc are
  the ones the renderer used.

### Where a demo's panel goes: `beginDemoPanel`

Every demo has a panel, and they all open in one place: the left column, under
"Frame" at y = 260 or, from Chapter 10 on, under the "Camera" panel a 3D demo
adds, at y = 510. Those are *baseline* distances, the pixels they measure at
Chapter 7's 100% UI scale: `uiPixels` multiplies them by the current scale,
and `uiPosition` clamps the starting position to the available viewport. In a
1280 × 720 window at 100%, the below-camera slot leaves 200 pixels before the
bottom margin. That is room for a few controls, such as the triangle's three,
but Chapter 25's grass panel has more than sixty rows, and a panel that sizes
itself to its contents grows off the bottom edge from that starting position.
Stop it at the edge, so what does not fit scrolls inside it rather than
becoming unreachable.

That is one function, which every demo's main panel calls instead of
`SetNextWindowPos` and `Begin`. It goes in `DebugPanels`, beside the demo
picker: the left column is the engine's layout rather than any one demo's, and
`DebugPanels` depends on nothing a demo owns, so demos and engine alike can call
it. **This is `Source/PillowFort/DebugPanels/DemoPanel.h`:**

```cpp
// Source/PillowFort/DebugPanels/DemoPanel.h
#pragma once

#include <imgui.h>

namespace pf::debug_panels {

// Where a demo's main panel opens: the left column, under the engine's windows.
enum class DemoPanelSlot
{
    BelowFrame,    // under Chapter 07's "Frame": a demo without a camera
    BelowCamera,   // under Chapter 10's "Camera": a demo with one
};

float uiPixels(float baselinePixels);
ImVec2 uiPosition(float baselineX, float baselineY);
ImVec2 clampUiPosition(ImVec2 position);

// ImGui::Begin for a demo's main panel. Opens it at its slot the first time, fits it to
// its contents, and stops it at the bottom of the screen; what does not fit scrolls.
// Returns what Begin returns. Call ImGui::End afterwards either way, as after Begin.
bool beginDemoPanel(const char* name, DemoPanelSlot slot);

// The height limit on its own, for a demo's other windows, which open elsewhere. Call it
// just before their ImGui::Begin.
void stopNextWindowAtScreenBottom();

} // namespace pf::debug_panels
```

**And `DemoPanel.cpp`:**

```cpp
// Source/PillowFort/DebugPanels/DemoPanel.cpp
#include "PillowFort/DebugPanels/DemoPanel.h"

#include <imgui.h>

#include <algorithm>
#include <cfloat>

// File scope, above the namespace block. ImGui calls this while it sizes the window,
// once the window has its position: the window may be as tall as the room between its
// top edge and the bottom of the screen, less the 10-pixel margin, and no taller.
// (ImGui still keeps the title bar, however little room there is.)
static void stopAtScreenBottom(ImGuiSizeCallbackData* data)
{
    const float margin = pf::debug_panels::uiPixels(10.0f);
    const float room = std::max(ImGui::GetStyle().WindowMinSize.y,
        ImGui::GetIO().DisplaySize.y - margin - data->Pos.y);
    data->DesiredSize.x = std::min(data->DesiredSize.x,
        std::max(ImGui::GetStyle().WindowMinSize.x, ImGui::GetIO().DisplaySize.x - margin - data->Pos.x));
    data->DesiredSize.y = std::min(data->DesiredSize.y, room);
}

namespace pf::debug_panels {

float uiPixels(float baselinePixels)
{
    return baselinePixels * ImGui::GetStyle().FontScaleMain;
}

ImVec2 clampUiPosition(ImVec2 position)
{
    const ImVec2 display = ImGui::GetIO().DisplaySize;
    const float margin = uiPixels(10.0f);
    ImVec2 minimum = ImGui::GetStyle().WindowMinSize;
    minimum.y = std::max(minimum.y, ImGui::GetFrameHeight() * 2.0f + ImGui::GetStyle().WindowPadding.y * 2.0f);
    position.x = std::clamp(position.x, margin, std::max(margin, display.x - minimum.x - margin));
    position.y = std::clamp(position.y, margin, std::max(margin, display.y - minimum.y - margin));
    return position;
}

ImVec2 uiPosition(float baselineX, float baselineY)
{
    ImVec2 position = clampUiPosition(ImVec2(uiPixels(baselineX), uiPixels(baselineY)));
    const float margin = uiPixels(10.0f);
    // Leave room for a normal tool panel when a scaled column no longer fits.
    const float reserve = std::min(uiPixels(360.0f), ImGui::GetIO().DisplaySize.x - 2.0f * margin);
    position.x = std::min(position.x, std::max(margin, ImGui::GetIO().DisplaySize.x - reserve - margin));
    return position;
}

void stopNextWindowAtScreenBottom()
{
    // No fixed limits: the callback caps the height every frame from where the window is
    // now, so a window dragged higher has room to grow.
    ImGui::SetNextWindowSizeConstraints(ImVec2(0.0f, 0.0f), ImVec2(FLT_MAX, FLT_MAX), stopAtScreenBottom);
}

bool beginDemoPanel(const char* name, DemoPanelSlot slot)
{
    // The left column on first use, with room for Frame's global scale control.
    const float top = slot == DemoPanelSlot::BelowFrame ? 260.0f : 510.0f;
    ImGui::SetNextWindowPos(uiPosition(10.0f, top), ImGuiCond_FirstUseEver);
    stopNextWindowAtScreenBottom();
    return ImGui::Begin(name, nullptr, ImGuiWindowFlags_AlwaysAutoResize);   // fits its contents, up to the cap
}

} // namespace pf::debug_panels
```

- **The limit is a function, not a number.** `SetNextWindowSizeConstraints`
  takes a smallest and a largest size, and optionally a function that ImGui
  calls while it sizes the window, handing it the window's position (`Pos`) and
  the size it is about to take (`DesiredSize`), which the function may lower.
  A fixed largest size worked out from y = 510 would stay 200 pixels wherever
  the panel was dragged; measured from `Pos` every frame, the limit follows the
  panel when it is dragged, and the program's window when that is resized.

The three helpers each do one thing: `uiPixels` scales a baseline distance,
`clampUiPosition` keeps a position on screen with room for a minimum-size
window, and `uiPosition` does both for a panel's first placement. When the
window is narrow for the scale, `uiPosition` also moves the starting point
left until a panel 360 baseline pixels wide still fits, rather than only
keeping its title bar on screen. The callback caps width as well as height,
and never below ImGui's minimum window size.

Now remove Chapter 7's file-local `uiPixels`, include
`"PillowFort/DebugPanels/DemoPanel.h"` in `ImGuiDebugPanels.cpp`, and in
`drawFrameStatistics` replace the locals `margin`, `display` and `minimum` and
the `SetNextWindowPos` and `SetNextWindowSizeConstraints` calls with:

```cpp
    ImGui::SetNextWindowPos(uiPosition(10.0f, 10.0f), ImGuiCond_FirstUseEver);
    stopNextWindowAtScreenBottom();
```

The triangle's panel is the first demo caller. `ShaderParameters.cpp` includes
`"PillowFort/DebugPanels/DemoPanel.h"` in place of `<algorithm>`, which only
the placement used, and in `drawShaderParameters` the seven placement
statements after `bool changed = false;` (from `scale` through
`SetNextWindowSizeConstraints`) and the `ImGui::Begin` go, so it begins:

```cpp
bool drawShaderParameters(ShaderParameters& parameters)
{
    bool changed = false;
    if (debug_panels::beginDemoPanel("Shader", debug_panels::DemoPanelSlot::BelowFrame))
    {
```

The `ImGui::End()` after the `if` stays where it was: this chapter's
`beginDemoPanel` is a `Begin`, and needs its `End` whether it returned true or
not. Every later demo's early-stage panel begins the same way. In the
assembled reference, close it with `debug_panels::endPanel()` instead, as
[the note under this chapter's prerequisites](#ui-stage-boundary) explains
(open the note).

A long panel has one more habit, and Chapter 21's particles are the first to
use it: its statistics stay in view, and each group of controls goes under
`if (ImGui::CollapsingHeader("Name"))` instead of a `SeparatorText` label. The
header is a bar with the group's name, closed until it is clicked, and it
returns true while open, so a closed group costs one row.

These floating panels are enough for the next few chapters. When many demos'
panels crowd the left column, the optional
[control-workspace transfer at the end of this chapter](#control-workspace-transfer)
asks how to grow them into one workspace; come back to it after several more
demos.

---

## 7. `SandboxGame`: the list, the picker, and the loop

ROADMAP says `SandboxGame` "owns the only `main()` and constructs everything
explicitly. No singletons, service locators, static registration, or generated
entry points." For demos, that means the list of demos is a variable in
`main`.

### Registration is one line

**This is `Source/SandboxGame/Main.cpp`,** after `setInputForwarding` and
before the loop:

```cpp
    // Chapter 09: every demo, in the order the picker lists them. Adding a demo
    // is one line here, plus its #include. SandboxGame owns them all; the
    // renderer borrows the active one.
    std::vector<std::unique_ptr<demos::Demo>> demoList;
    demoList.push_back(std::make_unique<demos::triangle::TriangleDemo>());

    std::vector<const char*> demoNames;
    for (const std::unique_ptr<demos::Demo>& demo : demoList) { demoNames.push_back(demo->Name()); }

    // A demo that fails is reported, not fatal: the renderer detaches it, shows
    // its own clear color, and keeps the reason, which the picker displays.
    size_t selectedDemo = findDemo(demoNames, settings.demo);
    renderer.switchDemo(demoList[selectedDemo].get());
```

The list has one demo for now; section 8 adds the second with one more line.
Constructors perform no fallible GPU setup (section 2); only the selected
demo's `Setup` acquires those resources. CPU member construction can still
allocate or prepare scene data. Keep expensive CPU preparation in `Setup` too
if startup measurements justify deferring it. `main` includes each demo's header — for now
`"PillowFort/Demos/Triangle/TriangleDemo.h"` — plus `<memory>`, `<span>`,
`<string>`, and `<vector>`; `<cmath>` goes, since `main` no longer animates
anything.

**Why not let each demo register itself** with a static object whose
constructor adds it to a global list. Beyond being the static registration the
roadmap rules out, it does not work here: demos live in the
`PillowFortEngine` static library, and a linker pulls an object file out of a
static library only when something references a symbol in it. A demo's file
that only registers itself is referenced by nothing, so it is silently left
out, the registration never runs, and the demo is missing with no error. The
explicit line in `main` is the reference that links it.

### Starting on a demo: `--demo`

Clicking through the picker after every launch gets old, and a scripted run
cannot click. Chapter 5's command line grows one option. A demo is not a
renderer setting, so `parseSettings` now returns a struct holding both:

```cpp
// Everything the command line chooses: Chapter 05's renderer settings, and
// from Chapter 09 the demo to start on.
struct LaunchSettings
{
    vulkan_graphics::RendererSettings renderer;
    std::string                       demo;   // part of a demo's Name(); empty = the first one
};
```

In Chapter 5's `parseSettings`, the return type and the local become
`LaunchSettings`, the two existing branches write `settings.renderer.preferredGpu`
and `settings.renderer.presentMode`, and one branch joins them before the final
`else`:

```cpp
        else if (key == "--demo")
        {
            settings.demo = value;
        }
```

`main` now parses first (`const LaunchSettings settings = parseSettings(argc, argv);`
as its first line) and passes `settings.renderer` to `renderer.initialize`. The
name is matched by part, case-sensitively, as `--gpu` matches a device:

```cpp
// File scope. The first demo whose name contains `part`, so `--demo Grad` is
// enough; the first demo when `part` is empty or matches nothing.
static size_t findDemo(std::span<const char* const> names, std::string_view part)
{
    if (part.empty()) { return 0; }
    for (size_t i = 0; i < names.size(); ++i)
    {
        if (std::string_view(names[i]).find(part) != std::string_view::npos) { return i; }
    }
    Log::warning(std::format("No demo matches --demo \"{}\"; starting the first.", part).c_str());
    return 0;
}
```

### The picker

**This is `ImGuiDebugPanels`.** Chapter 7 put the panels every demo shares
here, and a list of all the demos is the most shared panel there is. It takes
names, not demos, so `DebugPanels` stays independent of `Demos` — the same
reason `drawPresentModePicker` takes a span of present modes rather than the
swapchain:

```cpp
    bool drawDemoPicker(std::span<const char* const> names, size_t& current,
                        const std::string& status);                            // Chapter 09 section 7
```

```cpp
// Chapter 09 section 7. Returns true when the user picked a different demo;
// `current` is updated. `status` is shown under the list when not empty.
bool ImGuiDebugPanels::drawDemoPicker(std::span<const char* const> names, size_t& current,
                                      const std::string& status)
{
    bool changed = false;

    // Pinned to the top-right corner, clear of "Frame" and of a demo's panel.
    // ImGuiCond_Always rather than FirstUseEver, so it follows the corner when
    // the window shrinks instead of being left outside it. Fixed width; the
    // height follows the list and the status line, with scrolling on smaller viewports.
    const ImGuiIO& io = ImGui::GetIO();
    const float margin = uiPixels(10.0f);
    const float width = std::min(uiPixels(240.0f), std::max(1.0f, io.DisplaySize.x - 2.0f * margin));
    ImGui::SetNextWindowPos(ImVec2(io.DisplaySize.x - margin, margin), ImGuiCond_Always,
                            ImVec2(1.0f, 0.0f));
    ImGui::SetNextWindowSizeConstraints(ImVec2(width, 0.0f),
        ImVec2(width, std::max(ImGui::GetStyle().WindowMinSize.y, io.DisplaySize.y - 2.0f * margin)));
    if (ImGui::Begin("Demos", nullptr, ImGuiWindowFlags_AlwaysAutoResize))
    {
        for (size_t i = 0; i < names.size(); ++i)
        {
            if (ImGui::Selectable(names[i], i == current) && i != current)
            {
                current = i;
                changed = true;
            }
        }
        if (!status.empty())
        {
            ImGui::Separator();
            ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 0.45f, 0.45f, 1.0f));
            ImGui::TextWrapped("%s", status.c_str());
            ImGui::PopStyleColor();
        }
    }
    ImGui::End();
    return changed;
}
```

The picker's width and margin are baseline UI distances; its viewport cap lets
a long list scroll when enlarged or when the window shrinks. `main` passes
`renderer.demoError()` as the status, and a detached demo stays selected in the
list — the honest answer to "what did I pick?" — so to retry one that failed,
pick another and come back: a click on the item already selected is not a
change (`i != current`), and runs no `Setup`.

### The loop

Four changes to Chapter 7, section 10's loop, in the order they appear in it.
**This is the frame loop in `main`.**
Keep Chapter 7's minimization recheck after `pollEvents` and before
`beginUiFrame`; switching demos does not change that frame-lifetime rule.

First, the event filter keeps what it lets through instead of discarding it.
Declare `demoEvents` beside `io`, and `push_back` in place of the comment that
ended the loop body ("Anything left is the application's"):

```cpp
        const ImGuiIO&             io = ImGui::GetIO();
        std::vector<window::Event> demoEvents;
```

```cpp
            if (io.WantCaptureKeyboard && event.isKeyboard()) { continue; }
            demoEvents.push_back(event);
```

Second, after the present-mode picker, the demo picker, where a switch happens.
The reason it comes before `Update` is below:

```cpp
        // Chapter 09: switch before Update, so a demo is never torn down after
        // it has drawn ImGui widgets that this frame will still render.
        if (renderer.debugPanels().drawDemoPicker(demoNames, selectedDemo, renderer.demoError()))
        {
            renderer.switchDemo(demoList[selectedDemo].get());
        }
```

Third, after Chapter 5's `elapsedSeconds` lines, the active demo is updated. Chapter
8, section 5's triangle lines (`triangleParameters()`, `drawShaderParameters`, and
the `time` they set) leave `main`, with its `ShaderParameters.h` include: the
triangle's `Update` does both now (section 6).

```cpp
        if (demos::Demo* demo = renderer.demo(); demo != nullptr)
        {
            demo->Update({
                .deltaSeconds   = std::min(frameMilliseconds / 1000.0f, 0.1f),   // no leap after a stall
                .elapsedSeconds = elapsedSeconds,
                .events         = demoEvents,
            });
        }
```

Fourth, Chapter 5's two `FrameRequest` lines, with the animated clear color that
moved into the triangle, become a default request:

```cpp
        // Its clear color is what the scene shows while no demo is active.
        const vulkan_graphics::FrameRequest request{};
```

The filter is Chapter 7, section 4's, unchanged; what passes it is now kept in
`demoEvents` for the demo. Chapter 10, section 10 refines it once, for a camera
that tracks held keys. Window resizes still go straight to the renderer and never reach `events`;
the demo hears about them as `Resize`, after the targets exist.

**`Update` gets the input in `FrameInput`.** `events` is a span over this
frame's `demoEvents`, valid only during the call, which is the only time a
demo needs it — a controller turns events into its own state then.
`deltaSeconds` is clamped to a tenth of a second. The first frame after the
window is restored, or after Windows' modal resize loop (Chapter 2, section 4)
held the loop for a second, measures that whole stall; a demo that integrates
motion — a camera's velocity, Chapter 21's particles — would jump by all of it
at once. `elapsedSeconds` is the wall clock since startup, unclamped, for
anything that animates by absolute time, as the triangle does. The frame
statistics still get the true frame time.

**The switch happens before `Update`.** Between `beginUiFrame` and `drawFrame`,
every ImGui call is recorded into this frame's draw lists, and rendered in
`drawFrame`. If the active demo's `Update` drew a panel showing one of its own
textures and the picker then tore that demo down, the frame would render a
draw list pointing at a destroyed descriptor set. Drawing the picker first
means the outgoing demo has drawn nothing this frame. The switch itself is
safe mid-UI-frame: `switchDemo` waits for the GPU, and nothing it does touches
ImGui's frame.

**`FrameRequest` now means "no demo".** Chapter 5's animated clear color moved
into the triangle, so `main` passes a default `FrameRequest`, whose
`clearColor` is what the renderer clears the scene target to when no demo is
active — a dark blue-grey that says "nothing is drawing" rather than "broken".
Chapter 5, section 2 asked this struct to stay the handful of values `main`
itself owns, and that is what it still is. Its header says so now:

```cpp
// Source/PillowFort/VulkanGraphics/FrameRequest.h
#pragma once

namespace pf::vulkan_graphics {

struct FrameRequest
{
    // From Chapter 09, what the scene target shows while no demo is active.
    // Each demo clears to its own color.
    float clearColor[4] = { 0.05f, 0.05f, 0.08f, 1.0f };
};

} // namespace pf::vulkan_graphics
```

After the loop, `renderer.shutdown()` tears the active demo down first
(section 5). The demo objects themselves are destroyed when `demoList` goes out
of scope at the end of `main`, after Vulkan is gone — harmless, because their
destructors do nothing either.

---

## Checkpoint

Everything the triangle had has moved, and nothing new has been added, so
build and run now: a mistake in the move shows here, on a picture you know,
before a second demo is involved. You should see:

- **the triangle exactly as at the end of Chapter 8**: the same bands, the
  same animated background, and the "Shader" panel under "Frame", whose sliders
  still change it;
- **a "Demos" panel in the top-right corner** listing Triangle alone, selected;
- **validation silent**, through resizing the window and through closing it,
  and no assertion from `vmaDestroyAllocator` at exit: the triangle's
  `Teardown` freed what its `Setup` made.

---

## 8. The second demo

ROADMAP's exit check for this step: *adding a second demo touches only its own
folder plus one registration line.* The index makes "its own folder" two
folders — `Source/PillowFort/Demos/<Name>/` and `Shaders/<Name>/` — and the
second demo exists to prove the claim. It is deliberately tiny: a fullscreen
gradient between two colors you pick, so that everything in it is plumbing.

### One engine change first

A demo's push-constant block has a C++ side and a GLSL side, and Chapter 8,
section 8 showed the cure for keeping two copies in sync: one header both
languages include. A demo's own types belong in its own shader folder, as
`Shaders/<Name>/<Name>Types.h`, not in `Shaders/Include/SharedShaderTypes.h` —
which is for what more than one demo uses, and editing it would put a shared
file in every demo's diff. GLSL finds the header by relative name, from the
shader beside it. C++ needs `Shaders/` itself on the include path, so it can
say `"Gradient/GradientTypes.h"`. **This is the common `includedirs` in
`premake5.lua`:**

```lua
        "Source",
        "Shaders",                       -- a demo's own <Name>/<Name>Types.h (Chapter 09 section 8)
        "Shaders/Include",               -- SharedShaderTypes.h, shared with GLSL (Chapter 08 section 8)
```

This is a change to the engine, made once, before the second demo — so that the
second demo, and every one after it, needs no edit outside its folders.
Chapter 6, section 1's shader glob already compiles any
`Shaders/<Name>/*.frag.glsl` it finds and mirrors it beside the executable; a
`Types.h` is not a stage, so the glob leaves it alone. Regenerate.

### The gradient's files

The shared struct follows `SharedShaderTypes.h`'s shape, and includes it for
the `vec4` alias rather than defining another one. On the C++ side it lives in
the demo's namespace, for the same reason as section 6's:

```c
/* Shaders/Gradient/GradientTypes.h - the gradient's push constants, in both languages. */
#ifndef PF_GRADIENT_TYPES_H
#define PF_GRADIENT_TYPES_H

#include "SharedShaderTypes.h"   /* the vec4 alias on the C++ side */

#ifdef __cplusplus
    namespace pf::demos::gradient {
    using shared::vec4;
#endif

struct GradientParameters
{
    vec4 topColor;      /* sRGB, as ImGui's swatch shows it; the shader decodes */
    vec4 bottomColor;
};

#ifdef __cplusplus
    static_assert(sizeof(GradientParameters) == 32, "GradientParameters layout drifted.");
    }
#endif

#endif
```

The shader draws with Chapter 6, section 2's fullscreen vertex shader, which
hands it `uv`. Both colors come from ImGui swatches, so they are sRGB and are
decoded before blending — Chapter 8, section 4's color-boundary table, and the
reason the blend happens in linear light:

```glsl
// Shaders/Gradient/Gradient.frag.glsl - drawn with Fullscreen/Fullscreen.vert.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "Color.glsl"           // Shaders/Include: srgbToLinear (Chapter 08 section 5)
#include "GradientTypes.h"      // beside this file

layout(location = 0) in  vec2 uv;
layout(location = 0) out vec4 outColor;

layout(push_constant) uniform GradientBlock
{
    GradientParameters parameters;
};

void main()
{
    // Both colors came from ImGui swatches: decode, then blend in linear light.
    vec3 top    = srgbToLinear(parameters.topColor.rgb);
    vec3 bottom = srgbToLinear(parameters.bottomColor.rgb);
    outColor    = vec4(mix(top, bottom, uv.y), 1.0);   // uv.y is 0 at the top: Vulkan's Y points down
}
```

The two includes resolve differently. `"GradientTypes.h"` is found beside the
shader, the way a quoted include always looks first. `"Color.glsl"` is found
through the `-I` for `Shaders/Include` that Chapter 6's `configureShaderBuilds`
passes to every `glslc` call — it is the triangle's decode from Chapter 8,
section 5, shared rather than copied, so the gradient needs nothing outside its
own folder to get it.

The class has the triangle's shape. Its panel is a file-scope function in its
`.cpp`, since nothing else needs it, and its `Resize` keeps the extent it was
handed so the panel can show that the hook ran:

```cpp
// Source/PillowFort/Demos/Gradient/GradientDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"

#include "Gradient/GradientTypes.h"   // Shaders/Gradient/, shared with the shader

#include <cstdint>

namespace pf::demos::gradient {

class GradientDemo final : public Demo
{
public:
    const char*          Name() const override { return "Gradient"; }
    InitializationResult Setup(const DemoContext& context) override;
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override;
    void                 Update(const FrameInput& input) override;
    InitializationResult Record(const RecordContext& frame) override;
    void                 Teardown() override;

private:
    DemoContext        m_context;
    VkPipelineLayout   m_pipelineLayout = VK_NULL_HANDLE;
    VkPipeline         m_pipeline       = VK_NULL_HANDLE;
    GradientParameters m_parameters{
        .topColor    = { 0.10f, 0.20f, 0.45f, 1.0f },
        .bottomColor = { 0.95f, 0.60f, 0.30f, 1.0f },
    };
    VkExtent2D         m_extent{};          // from the last Resize, shown on the panel
    uint32_t           m_resizeCount = 0;
};

} // namespace pf::demos::gradient
```

**This is `GradientDemo.cpp`.** It opens with the includes and the panel,
above the namespace block:

```cpp
// Source/PillowFort/Demos/Gradient/GradientDemo.cpp
#include "PillowFort/Demos/Gradient/GradientDemo.h"

#include "PillowFort/DebugPanels/DemoPanel.h"
#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"

#include <imgui.h>

// File scope, above the namespace block. The gradient's panel; nothing else
// needs it, so it is not even in the header.
static void drawGradientPanel(pf::demos::gradient::GradientParameters& parameters,
                              VkExtent2D extent, uint32_t resizeCount)
{
    if (pf::debug_panels::beginDemoPanel("Gradient", pf::debug_panels::DemoPanelSlot::BelowFrame))
    {
        ImGui::ColorEdit3("Top", &parameters.topColor.x);
        ImGui::ColorEdit3("Bottom", &parameters.bottomColor.x);
        ImGui::Text("Resize calls: %u (last %u x %u)", resizeCount, extent.width, extent.height);
    }
    ImGui::End();
}
```

`&parameters.topColor.x` hands `ColorEdit3` the address of the first of three
contiguous floats — `glm::vec4` stores `x, y, z, w` in order. The fourth,
alpha, is left at 1 and never edited.

**`Setup` is the triangle's `Setup` with three changes**, inside
`namespace pf::demos::gradient`, and the names changed from triangle to
gradient:

- **The push-constant range is fragment-only**:
  `.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT` and
  `.size = sizeof(GradientParameters)`. Only the fragment shader reads the
  block; `stageFlags` must cover every stage that does (Chapter 8, section 5),
  and need cover no more. `Record`'s `vkCmdPushConstants` says the same.
- **The vertex shader is `"Fullscreen/Fullscreen.vert.spv"`**, Chapter 6,
  section 2's, shared, and the fragment shader `"Gradient/Gradient.frag.spv"`.
- **The two `static_assert`s go**: `GradientTypes.h` asserts its own layout.

The rest of the class:

```cpp
// Nothing here is sized to the window either; the gradient only remembers what
// it was told, so the panel can show that the hook ran.
InitializationResult GradientDemo::Resize(const vulkan_graphics::SceneTargets& targets)
{
    m_extent = targets.extent;
    ++m_resizeCount;
    return InitializationResult::success();
}

void GradientDemo::Update(const FrameInput& /*input*/)
{
    drawGradientPanel(m_parameters, m_extent, m_resizeCount);
}

InitializationResult GradientDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;

    // nullptr: no clear. The fullscreen triangle writes every pixel (Chapter 05's
    // LOAD_OP_DONT_CARE case).
    vulkan_graphics::beginScenePass(commandBuffer, frame.targets, nullptr);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipeline);
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(GradientParameters), &m_parameters);
    vkCmdDraw(commandBuffer, 3, 1, 0, 0);

    vulkan_graphics::endScenePass(commandBuffer);
    vulkan_graphics::handBackSceneTarget(commandBuffer, frame.targets);
    return InitializationResult::success();
}
```

**`Resize` does something visible.** The gradient owns nothing sized to the
window, so this is only bookkeeping, but it makes the exit check's "resizing
calls the active demo's resize" something you can read off the panel. The
count is CPU state, so it survives switching away and back; expect it to count
every switch to the gradient as well as every recreation.

**`Teardown` is the triangle's, word for word**: destroy the pipeline and its
layout, and reset both handles. The file ends with the namespace's closing
brace. The Appendix prints the whole file, as the smallest complete demo there
is — a template for the next one.

Then the registration, in `main`: one line after the triangle's,

```cpp
    demoList.push_back(std::make_unique<demos::gradient::GradientDemo>());
```

and `#include "PillowFort/Demos/Gradient/GradientDemo.h"` beside the
triangle's include. Regenerate, build, and the gradient is in the picker.

What changed on disk to add it, after the one-time `premake5.lua` line above:
`Source/PillowFort/Demos/Gradient/` and `Shaders/Gradient/`, both new, and two
lines of `Main.cpp`. Nothing in `VulkanGraphics`, `DebugPanels`, or the
triangle. That is the exit check, and it is worth confirming with
`git status` rather than by memory.

---

## 9. What runs when

The whole harness on one page — the table to keep open while writing a demo.

| When | Order |
| --- | --- |
| Startup | `renderer.initialize` (no demo) → `main` constructs every demo → `switchDemo(first or --demo)` |
| `switchDemo(demo)` | `requireSafeDeviceIdle` → old `Teardown` → new `Setup(context)` → new `Resize(targets)` → active (a failure at either step: `detachDemo`, section 5) |
| Every frame, in `main` | `pollEvents` → skip if now minimized → `beginUiFrame` → drain and filter events → frame statistics and present-mode picker → demo picker (a switch happens here) → active `Update(input)` → `drawFrame` |
| Inside `drawFrame` | fence wait for this slot → acquire → active `Record(frame)`, or the engine's clear → composite and ImGui → submit → present → `recreateSwapchain` if needed |
| `recreateSwapchain` | `VulkanSwapchain::recreate` (`requireSafeDeviceIdle`) → engine rebuilds its targets → composite set rewritten → active `Resize(targets)` (a failure detaches the demo, section 5) |
| Shutdown | `requireSafeDeviceIdle` → active `Teardown` → ImGui shutdown → engine objects → `vmaDestroyAllocator` (asserts on a demo's leak) |

One rule follows from the table that it does not show: **destroying anything
mid-run that an in-flight frame may still use** — replacing a mesh from a panel
button, say, needs a checked `requireSafeDeviceIdle` first. `switchDemo`, and
the swapchain recreation that precedes every later `Resize`, already provide
one; anywhere else, the demo must call it itself.

---

## If something goes wrong

| Symptom | Likely cause |
| --- | --- |
| `ShaderParameters`: undeclared identifier, in `VulkanRenderer.cpp` | A line of the triangle's left behind in `initialize`, `recordFrame`, or `shutdown` (section 5) |
| `VUID-vkCmdDraw-imageLayout-00344` at the composite's draw: the scene image is `COLOR_ATTACHMENT_OPTIMAL`, the descriptor says `SHADER_READ_ONLY_OPTIMAL` | The demo's `Record` skipped `handBackSceneTarget` |
| A layout error or `SYNC-HAZARD-WRITE-AFTER-WRITE` at the hand-back barrier | Its source half does not describe what the demo did last — a compute demo passing the defaults, which say `COLOR_ATTACHMENT_OPTIMAL` |
| Validation: depth attachment format mismatch, after Chapter 10 | A demo's pipeline does not pass `context.formats.depth` |
| Validation about destroyed pipelines or buffers in use, when switching | Something destroyed outside `Teardown`, or a switch path that skipped `requireSafeDeviceIdle` |
| Validation reports an invalid `VkPipeline` in `vkDestroyPipeline` when a demo you visited before fails its next `Setup` | `Teardown` destroyed a handle without resetting it to `VK_NULL_HANDLE`; when the next `Setup` failed before replacing it, `Teardown` destroyed it again |

---

## Exit check

- [ ] The Demos panel lists Triangle and Gradient. Switching back and forth
      twenty times is validation-clean. The Shader panel is shown only with
      the triangle, the Gradient panel only with the gradient.
- [ ] Drag the Shader panel by its title bar to the bottom of the window: once
      its rows reach the bottom edge it gets shorter and shows a scrollbar,
      instead of running off. Drag it back up and it grows to fit its rows.
- [ ] With the gradient active, resizing the window increases its panel's
      resize count and shows the new extent; so does changing the present mode,
      with the extent unchanged.
- [ ] **The contract is checked, not assumed.** Temporarily change
      `handBackSceneTarget`'s default `lastAccess`, on its declaration in
      `SceneTargets.h`, to `VK_ACCESS_2_NONE`. The
      scene's color writes are then never made available before the hand-back
      transition, and sync validation must report
      `SYNC-HAZARD-WRITE-AFTER-WRITE` on the first frame. Put it back.
- [ ] A demo whose `Setup` fails — temporarily point the gradient at a shader
      that does not exist — leaves the window running with the dark blue-grey
      clear color and the error under the picker, and switching to the triangle
      still works.
- [ ] A demo whose `Resize` fails is detached the same way. Temporarily make
      the gradient's `Resize` begin with
      `if (targets.extent.width < 1000) { return InitializationResult::failure("Narrower than 1000 pixels."); }`,
      then narrow the window with the gradient active: the program keeps
      running, with the dark blue-grey clear color and the message under the
      picker, validation stays clean, and the triangle can still be picked.
      Widening the window again does not bring the gradient back; picking
      another demo and then the gradient does.
- [ ] `SandboxGame --demo Grad` starts on the gradient.
- [ ] Closing with either demo active is validation-clean, and
      `vmaDestroyAllocator` does not assert.
- [ ] Adding the gradient changed only `Source/PillowFort/Demos/Gradient/`,
      `Shaders/Gradient/`, and two lines of `Main.cpp` — checked with
      `git status`.

---

<a id="control-workspace-transfer"></a>

## Optional transfer: grow the tools, not the tab bar

**Return here after several more demos.** This chapter's panels are
intentionally small: Frame, the Demos picker and one floating panel per demo.
By Horizon, frame timing, rendering options, scene settings and
camera controls all need a home. Before reading the reference implementation,
sketch how you would find those controls at 4K with Chapter 7's UI scale at
300%, and after shrinking the window to 1100 x 650 at 200%. Then cycle
through thirteen demos. Should that action leave thirteen more tabs behind?

**Problem:** Keep demo selection and global scale reachable while a long scene
panel scrolls. Give rendering settings and measurements predictable locations.
Keep a useful scene viewport; do not solve crowding by silently reducing the
user's chosen scale or hiding controls behind an ever-growing overflow strip.

**Acceptance:** The same three navigation choices remain after every demo
switch. Each category keeps its own vertical scroll position. The final scene
control is reachable, and scrolling it does not move the demo selector. At a
very small viewport and 300%, the controls may be a drawer rather than a
simultaneous view of everything, but its close action and the scale popup must
remain reachable. A user who explicitly chooses floating windows may still
move and dock them; resizing must not create automatic dock tabs.

<details>
<summary>Hint 1: separate navigation from panel count</summary>

The number of rendering modules is not a useful number of top-level navigation
choices. Classify controls by the task: change the scene, change rendering,
inspect measurements. Registering a new module need not add a navigation item.

</details>

<details>
<summary>Hint 2: own the scroll boundary centrally</summary>

One fixed header and one scrolling child per category are enough. A scene
module should submit a section to that child, not choose another screen-space
window position. Decide what to do with old `SetNextWindowPos` metadata when
the next `Begin` is now a shared sidebar rather than that module's window.

</details>

<details>
<summary>Complete solution: the reference control workspace</summary>

The grown reference uses a top toolbar containing the demo combo, the 75-300%
scale control and the controls toggle. Below it, one bounded sidebar has fixed
**Scene / Render / Stats** navigation. Scene contains only the current demo's
sections; Render contains presentation, antialiasing, tone mapping and shadows;
Stats contains timings, resource counters and debug previews. Sections are
collapsible headings inside the selected category, not individual dock tabs.

[`DemoPanel.h`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/DebugPanels/DemoPanel.h) declares the
shared boundary. A module submits a section and always balances it, including
when its category is inactive:

```cpp
if (pf::debug_panels::beginPanel("Simulation", 0,
    pf::debug_panels::PanelGroup::Scene))
{
    pf::debug_panels::sliderFloat("Speed", &speed, 0.0f, 4.0f);
}
pf::debug_panels::endPanel();
```

In this assembled-reference API, `beginPanel`, `beginDemoPanel` and
`appendPanel` are paired with `endPanel`, not `ImGui::End`. The wrapper may
have begun a scrolling child or no native window at all. Section 6's
`beginDemoPanel` is the original native-window helper, and every listing that
calls it, in this chapter and the later ones, closes it with `ImGui::End`; do
not combine one version's beginning with the other's ending.

The complete
[`DemoPanel.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/DebugPanels/DemoPanel.cpp) implements
the fixed sidebar, independent scrolling children, wrapped labels and
deliberate floating mode. It clears stale next-window metadata before beginning
the shared sidebar. The toolbar is submitted before sections; its demo and
scale popups remain above it. The sidebar is at most 360 logical pixels wide
and, where there is enough room, at most 45% of the physical viewport. At tiny
sizes the header condenses to two rows and offers a scale popup; chosen scale
is never silently changed.

**Layout > Floating windows** is an explicit customization choice, not a
resize fallback. **Sidebar** returns to fixed navigation; returning to floating
mode restores the saved native layout. **Reset layout** restores the visible
Scene sidebar and clears that saved arrangement. This keeps user docking
available without making automatic docking the default experience.
The tiny header uses shorter **Floating** and **Reset** menu labels. Recompute
its current height before clamping floating windows: a one-row header becoming
two rows must not cover an existing title bar. A failed demo is also a toolbar
state, not merely text inside Scene: **Failed: demo name**, or the tiny
**Error** button, exposes the full error even while Stats is selected or tools
are hidden. Reporting a persistent error must not repeatedly change the user's
selected category.

[`UiScaleTests.cpp`](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/UiScaleTests.cpp) exercises the
production ImGui core with mocked platform/GPU backends. Its queued mouse and
keyboard events test category selection, demo selection, drawer access, precise
scale changes, tiny popup access, wrapped checkbox labels and disabled controls,
each category's retained scroll, floating-layout roundtrips and pinned error
details. Its layout oracle rejects an
injected automatic dock node, so "everything is contained in one tab strip"
cannot accidentally count as success. Native screenshots remain necessary for
font readability, backend behavior and scene/UI balance.

</details>

---

## Appendix: a minimal demo, whole

Reference: section 8's `GradientDemo.cpp` in one piece. Every demo in the
chapters after this one has these five functions in this shape; start a new
one by copying the gradient's folders and renaming.

```cpp
// Source/PillowFort/Demos/Gradient/GradientDemo.cpp
#include "PillowFort/Demos/Gradient/GradientDemo.h"

#include "PillowFort/DebugPanels/DemoPanel.h"
#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"

#include <imgui.h>

// File scope, above the namespace block. The gradient's panel; nothing else
// needs it, so it is not even in the header.
static void drawGradientPanel(pf::demos::gradient::GradientParameters& parameters,
                              VkExtent2D extent, uint32_t resizeCount)
{
    if (pf::debug_panels::beginDemoPanel("Gradient", pf::debug_panels::DemoPanelSlot::BelowFrame))
    {
        ImGui::ColorEdit3("Top", &parameters.topColor.x);
        ImGui::ColorEdit3("Bottom", &parameters.bottomColor.x);
        ImGui::Text("Resize calls: %u (last %u x %u)", resizeCount, extent.width, extent.height);
    }
    ImGui::End();
}

namespace pf::demos::gradient {

InitializationResult GradientDemo::Setup(const DemoContext& context)
{
    m_context = context;   // first, so Teardown works however far this gets

    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT,   // only the fragment shader reads it
        .offset     = 0,
        .size       = sizeof(GradientParameters),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 0,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    VkPipelineLayout createdPipelineLayout = VK_NULL_HANDLE;
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &createdPipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the gradient.");
    }
    m_pipelineLayout = createdPipelineLayout;

    const vulkan_graphics::GraphicsPipelineDesc gradient{
        .vertexShader   = "Fullscreen/Fullscreen.vert.spv",   // Chapter 06 section 2's, shared
        .fragmentShader = "Gradient/Gradient.frag.spv",
        .colorFormats   = { &m_context.formats.color, 1 },
        .depthFormat    = m_context.formats.depth,
        .layout         = m_pipelineLayout,
    };
    m_pipeline = vulkan_graphics::createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache,
                                                         gradient);
    if (m_pipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the gradient pipeline failed.");
    }
    return InitializationResult::success();
}

// Nothing here is sized to the window either; the gradient only remembers what
// it was told, so the panel can show that the hook ran.
InitializationResult GradientDemo::Resize(const vulkan_graphics::SceneTargets& targets)
{
    m_extent = targets.extent;
    ++m_resizeCount;
    return InitializationResult::success();
}

void GradientDemo::Update(const FrameInput& /*input*/)
{
    drawGradientPanel(m_parameters, m_extent, m_resizeCount);
}

InitializationResult GradientDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;

    // nullptr: no clear. The fullscreen triangle writes every pixel (Chapter 05's
    // LOAD_OP_DONT_CARE case).
    vulkan_graphics::beginScenePass(commandBuffer, frame.targets, nullptr);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipeline);
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(GradientParameters), &m_parameters);
    vkCmdDraw(commandBuffer, 3, 1, 0, 0);

    vulkan_graphics::endScenePass(commandBuffer);
    vulkan_graphics::handBackSceneTarget(commandBuffer, frame.targets);
    return InitializationResult::success();
}

void GradientDemo::Teardown()
{
    vkDestroyPipeline(m_context.vulkan.device, m_pipeline, nullptr);
    vkDestroyPipelineLayout(m_context.vulkan.device, m_pipelineLayout, nullptr);
    m_pipeline       = VK_NULL_HANDLE;
    m_pipelineLayout = VK_NULL_HANDLE;
}

} // namespace pf::demos::gradient
```

---

Next: [10 — Cameras and Depth](10-Cameras-And-Depth.md)
