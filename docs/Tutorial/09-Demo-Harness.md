# 09 — The Demo Harness

**Goal:** the triangle runs as the first of several demos, picked from an ImGui
panel, and a new demo is one folder, one class, and one line in `main`.

**ROADMAP:** step 10.

**Module:** `Demos`, namespace `pf::demos` — the interface — with each demo in
its own folder and nested namespace (`Source/PillowFort/Demos/Triangle/`,
`pf::demos::triangle`). Smaller changes to `VulkanGraphics`
(`pf::vulkan_graphics`), `DebugPanels` (`pf::debug_panels`),
`SandboxGame/Main.cpp`, and `premake5.lua`.

**Prerequisites:**

- Chapter 05 section 2 (`FrameRequest`) and section 3 (the frame loop in
  `main`, `parseSettings`).
- Chapter 06 section 1 (the shader glob, executable-relative paths), section 2
  (the fullscreen vertex shader), section 7 (where the triangle's pipeline
  lives), and section 8 (`GraphicsPipelineDesc`, `createGraphicsPipeline`).
- Chapter 07 section 4 (the `WantCapture*` filter), section 7 (placing a
  window with `SetNextWindowPos` and `ImGuiCond_FirstUseEver`), section 9
  (`ShaderParameters` and why its panel is a free function), and section 10
  (the renderer owns the panels; the frame loop's order).
- Chapter 08's opening: the class map (the renderer's members and their
  shutdown order) and "Where the free functions live" (`VulkanContext`).
  Section 4 (the scene target, the contract between the scene's part of the
  frame and the engine's, and "Following the window", which promises demos a
  hook for window-sized images of their own), section 5 (the push-constant
  path, and `Color.glsl`, the shared include with `srgbToLinear`), section 6
  (descriptor pools), section 7 (the allocator `VulkanContext` gains), and
  section 8 (`SharedShaderTypes.h`).

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
(`@author`, `@brief`, `@copyright`) that Chapter 02 section 0 showed; the
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
it. The line is the one Chapter 08 section 4 already drew in `recordFrame`, with
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
is those five and a name. Here is the whole header first, because its three
small structs are the subject of section 3 and the class is the subject of
this one:

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
    virtual ~Demo() = default;   // SandboxGame deletes demos through this type

    virtual const char*          Name() const = 0;                                          // section 2
    virtual InitializationResult Setup(const DemoContext& context) = 0;                     // section 2
    virtual InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) = 0;  // section 2
    virtual void                 Update(const FrameInput& input) = 0;                       // section 7
    virtual void                 Record(const RecordContext& frame) = 0;                    // section 4
    virtual void                 Teardown() = 0;                                            // section 2
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
base type; without it, the derived destructor never runs.

Every function is pure, including `Resize`, which the triangle leaves empty.
Reading a demo's header then tells you its whole lifecycle, and a demo that
needs `Resize` cannot forget it by inheriting a default that does nothing.

The functions, in the order they are called:

- **`Name`** — the label in the picker (section 7), and the prefix on the
  demo's error messages.
- **`Setup`** — creates everything that does not depend on the window's size:
  pipeline layouts, pipelines, descriptor pools, buffers whose size is the
  demo's own choice. It is fallible and returns `InitializationResult`, the
  convention from Chapter 02 section 0. **The constructor does nothing that
  can fail and touches no GPU object**: a demo is constructed in `main` before
  anyone knows whether it will ever be shown.
- **`Resize`** — creates or rebuilds whatever depends on the scene targets:
  images sized to the window (Chapter 33's accumulation image), and
  descriptors or ImGui textures that point at the targets' views. The engine
  rebuilds its own targets and then tells the demo, which rebuilds its own: a
  `recreateSwapchain` that knew each demo's images would break the "touches
  only its own folder" rule, which is why ROADMAP step 10 lists `resize`. The
  harness calls it **right after every successful `Setup`**, and again after
  every swapchain recreation, so size-dependent work has exactly one home.
  Being told "the targets changed" is more accurate than "the window was
  resized": a present-mode switch (Chapter 07 section 7) recreates the
  swapchain and the scene target at the same extent. The handles changed even
  when the size did not, so `Resize` rebuilds without comparing. It runs after
  the `vkDeviceWaitIdle` inside `VulkanSwapchain::recreate`, so destroying the
  old images there is safe. It is fallible for the same reason `Setup` is — an
  image can fail to allocate — and section 5 says what a failure does.
- **`Update`** — once per frame, before anything is recorded: CPU-side state,
  input, and the demo's ImGui panel. Section 7.
- **`Record`** — once per frame, into the frame's command buffer: the scene's
  part of the frame. Section 4.
- **`Teardown`** — destroys everything `Setup` and `Resize` created.

Two rules about `Teardown` make switching work, and both are easy to break
without noticing:

- **It must be safe after a `Setup` that failed partway.** The harness calls it
  whenever `Setup` or any `Resize` fails, to free whatever got created.
  This is the same rule as `VulkanRenderer::shutdown` after a partial
  `initialize`: Vulkan's destroy functions accept a null handle, so destroying
  everything unconditionally is correct. (VMA's are not null-safe in their
  first argument — Chapter 08 section 4 — but a demo is only set up while the
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
each handed over at the moment it becomes valid.

### `DemoContext`, for `Setup`

- **`vulkan`** is Chapter 08's `VulkanContext` — device, physical device,
  graphics queue, the immediate-submit pool and fence, and the allocator. It
  is everything `createBuffer`, `uploadToBuffer`, and `immediateSubmit` need,
  which is why Chapter 08 made those free functions over this struct rather
  than renderer members. It is passed **by value**: it is six handles that
  never change after `VulkanRenderer::initialize`, so a copy is still a borrow.
  And those functions take `VulkanContext&`, non-const, so the demo's own copy
  is exactly what it needs to pass them.
- **`pipelineCache`** is Chapter 06's. Every demo builds its pipelines through
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
bakes in its attachment formats (Chapter 06 section 4), so a demo needs them
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

The color format is the one `sceneTargetInfo` used in Chapter 08. Now that it
has a name, that function uses the name:

```cpp
        .format      = pf::vulkan_graphics::SceneFormats{}.color,   // R16G16B16A16_SFLOAT; Chapter 09 named it
```

### `FRAMES_IN_FLIGHT`

Chapter 04 put `FRAMES_IN_FLIGHT` in `VulkanRenderer.h`, where only the
renderer needed it. Demos need it now — Chapter 08 section 6's rule is one copy
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
`FRAMES_IN_FLIGHT` frames ago is safe to read back. `Update` runs before the
fence wait, so it must not touch per-frame GPU memory at all; section 9 has the
order.

### What a demo makes for itself

Anything not in those structs. In particular:

- **Descriptor pools.** The renderer's pool from Chapter 08 is sized for the
  composite set and nothing else. A shared pool would have to be sized for
  every demo at once, which is exactly the cross-demo coupling the harness is
  removing, so each demo creates a pool sized for its own sets in `Setup` and
  destroys it in `Teardown` — which frees every set allocated from it.
- **Samplers**, with the filtering and addressing its textures want.
- **ImGui textures** (`ImGui_ImplVulkan_AddTexture`, Chapter 07 section 2),
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

## 4. The scene part: Chapter 08's contract, now across a boundary

Chapter 08 section 4 ended with a contract between the two halves of the
frame. Restated, because the demo now signs it:

- The demo receives the scene color target in `SHADER_READ_ONLY_OPTIMAL` — or
  `UNDEFINED` on the first frame after it was created — and must hand it back
  in `SHADER_READ_ONLY_OPTIMAL`, with its writes made visible to the composite
  pass's fragment shader.
- It must write every pixel. Its first transition uses `UNDEFINED` as the old
  layout, which tells the driver the contents may be discarded.
- Everything in between is its business: compute dispatches, shadow passes, a
  rasterized pass, more drawing after that pass.

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
`LOAD_OP_DONT_CARE`, Chapter 05 section 1's cheapest case.

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

Both barriers are Chapter 08's, moved, and both are rows of Chapter 04's
cookbook. Through Chapter 04 section 5's three questions:

| | `beginScenePass` | `handBackSceneTarget` (defaults) |
| --- | --- | --- |
| Q1, what must finish first / what waits | Last frame's composite (`FRAGMENT_SHADER`) / this frame's color writes (`COLOR_ATTACHMENT_OUTPUT`) | This frame's color writes / the composite's sampling (`FRAGMENT_SHADER`) |
| Q2, flush / invalidate | Nothing: the earlier access was a read. / `COLOR_ATTACHMENT_WRITE` | `COLOR_ATTACHMENT_WRITE` / `SHADER_SAMPLED_READ` |
| Q3, layout | `UNDEFINED` (contents discarded) to `COLOR_ATTACHMENT_OPTIMAL` | `COLOR_ATTACHMENT_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL` |

`handBackSceneTarget` splits its barrier along the contract: the destination
half is the engine's and fixed, the source half describes what the demo did
last and is a parameter. The defaults are what `endScenePass` leaves, so a
rasterizing demo passes nothing. A compute demo that wrote the target as a
storage image passes `VK_IMAGE_LAYOUT_GENERAL`,
`VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT`, and
`VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT` — Chapter 04's "Compute result sampled
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
  acquire; the demo's color writes are, which is harmless at these frame
  times (Chapter 04 section 5 has why a wait applies to a whole stage).

> **Jump:** in Chapter 08 the two scene-target barriers sat a few lines apart
> in `recordFrame`, next to the composite pass that depends on them. Now the
> barriers are in demo code and the composite is in the renderer, and nothing
> in C++'s type system connects them — a demo that forgets
> `handBackSceneTarget` compiles. Synchronization validation is what checks the
> contract. Keep in mind that whoever records the scene part owns *both* ends
> of the target's trip through the frame, and run every new demo with
> validation on before believing its picture.

---

## 5. The renderer's side

**This is `VulkanRenderer`, again.** Its class map (Chapter 04's, as grown by
06, 07, and 08) changes in both directions.

It **loses**, with every line that used them in `initialize`, `recordFrame`,
and `shutdown`: `createTrianglePipeline()`, `m_pipelineLayout`, `m_pipeline`,
`m_triangleParameters`, `triangleParameters()`, the `ShaderParameters.h`
include, and the `FRAMES_IN_FLIGHT` constant (section 3). `m_pipelineCache`
stays — it was never the triangle's.

It **gains** a borrowed pointer to the active demo, the reason the last one
was dropped, and the functions around them:

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
beside Chapter 07's; `sceneTargets` and `detachDemo` are private, beside
`createSceneTarget`; the members go after `m_debugPanels`. The header includes
`SceneTargets.h` in place of `ShaderParameters.h`. Only `VulkanRenderer.cpp`,
which calls the demo, includes `Demos/Demo.h` — the header needs the name, not
the class.

`m_demo` is a raw pointer because it is a borrow: `main` owns every demo for
the whole run (section 7), and the renderer only needs to know which one is
active. `nullptr` means none — at startup before the first switch, and after a
demo has failed.

### `sceneTargets`

What a demo sees of Chapter 08's members, assembled on demand so it can never
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

The one place a demo is set up or torn down while the program runs:

```cpp
void VulkanRenderer::switchDemo(demos::Demo* demo)
{
    // In-flight frames may still be using the old demo's pipelines and buffers.
    // A switch is rare and user-driven; a stall here costs nothing anyone sees.
    vkDeviceWaitIdle(m_device);

    if (m_demo != nullptr)
    {
        m_demo->Teardown();
        m_demo = nullptr;
    }
    m_demoError.clear();
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
    demo->Teardown();
    m_demoError = std::format("{}: {}", demo->Name(), failure.message());
    Log::error(m_demoError.c_str());
}
```

**Why `vkDeviceWaitIdle` is acceptable here.** With two frames in flight, the
GPU may still be executing command buffers that bind the old demo's pipelines
and read its buffers. Destroying them now is a use-after-free on the GPU, which
validation reports and a driver may not survive. The alternatives are waiting
on both frames' fences, which is the same stall spelled differently, or a
deletion queue that holds the old demo's objects for `FRAMES_IN_FLIGHT` frames
— the machinery Chapter 06 section 8 deferred until hot reload needs it. A
switch is something a person clicks, perhaps a few times a minute; a stall of
one or two frames is invisible next to the pipeline compiles and uploads the
new demo's `Setup` is about to do. `VulkanSwapchain::recreate` makes the same
trade for the same reason.

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

### `recordFrame`

The scene's part of Chapter 08's `recordFrame` — from the first scene-target
barrier through the second — becomes this:

```cpp
    // ---- The scene's part: the active demo's, or a plain clear without one. ----
    // Either way the scene target ends in SHADER_READ_ONLY_OPTIMAL, written,
    // which is all the engine's part below relies on (Chapter 08 section 4).
    const SceneTargets targets = sceneTargets();
    if (m_demo != nullptr)
    {
        m_demo->Record({
            .commandBuffer = commandBuffer,
            .frameIndex    = m_frameIndex,   // drawFrame waited on this slot's fence
            .targets       = targets,
        });
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
the slot whose fence was just waited on. The engine's part below is unchanged
from Chapter 08, and its `viewport` and `scissor` locals stay with it.

### `recreateSwapchain`

Chapter 08 ended it with `writeCompositeSet()`. The demo is told last, after
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

The two failures this function can meet are treated differently, and the
difference is the point. If the engine's own `createSceneTarget` fails, there
is nothing for the composite pass to sample, so the frame fails and the program
shuts down. If a demo's `Resize` fails, the engine's targets are fine, so only
the demo goes. It must not stay attached with its window-sized images missing —
its next `Record` would use destroyed handles — which is why the detach happens
here, still after `vkDeviceWaitIdle`, before anything else is recorded.

### `shutdown`

The demo goes first, right after the wait — before the debug panels, which
were first until now:

```cpp
void VulkanRenderer::shutdown()
{
    if (m_device != VK_NULL_HANDLE)
    {
        vkDeviceWaitIdle(m_device);

        // Chapter 09: the demo first. It may hold ImGui textures, which need the
        // backend alive, and VMA allocations, which vmaDestroyAllocator checks for.
        if (m_demo != nullptr)
        {
            m_demo->Teardown();
            m_demo = nullptr;
        }

        m_debugPanels.shutdown();   // Chapter 07 section 10: right after the demo
```

Both reasons in the comment are real. `ImGui_ImplVulkan_RemoveTexture` needs
the backend that `m_debugPanels.shutdown` destroys. And Chapter 08's class map
("What `VulkanRenderer` gains") made `vmaDestroyAllocator` the last call for a reason: it asserts if any
allocation is still alive. With the demo torn down before it, that assertion
is now a leak check on every demo for free — a demo that forgets a
`destroyBuffer` stops the Debug build at exit. Remove the triangle's
`vkDestroyPipeline` and `vkDestroyPipelineLayout` lines further down; its
`Teardown` does that now.

In `initialize`, the `createTrianglePipeline()` call goes; nothing replaces it,
because no demo exists yet when the renderer initializes. `main` makes the
first switch (section 7).

---

## 6. The triangle becomes a demo

**This is `Source/PillowFort/Demos/Triangle/`.** Chapter 07 section 9 said
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
The struct is unchanged, and so is `drawShaderParameters` except for its first
two lines, which the end of this section replaces with a helper every demo's
panel uses.

**Why a namespace per demo.** `ShaderParameters` and `drawShaderParameters` are
good names for the triangle's parameters, and they will be good names for the
next demo's too. Two demos each defining `pf::demos::ShaderParameters` is a
one-definition-rule violation, and two `drawShaderParameters(ShaderParameters&)`
with different structs link into one library as the same symbol — `LNK2005` if
you are lucky, the wrong panel if you are not. A nested namespace per demo,
named after its folder in lower case, makes every name inside a demo private to
it without anyone having to coordinate.

The class itself is the other half of what leaves the renderer. Its members
are the renderer's old triangle members under new names, plus Chapter 05's
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
    void                 Record(const RecordContext& frame) override;
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
plus the clear color. `Record` is the triangle's part of Chapter 08's
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
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_pipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the triangle.");
    }

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

void TriangleDemo::Record(const RecordContext& frame)
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
  `std::span`, which does not own what it points at; Chapter 08 pointed it at a
  local that lived until the call returned. A member lives at least that long.
- **`elapsedSeconds` is the same clock as before.** Chapter 05 computed it from
  `startTime` in `main`, and `main` still does (section 7), so `time` and the
  clear color animate exactly as they did — which is what the exit check
  compares.
- **The shaders do not move.** They have lived in `Shaders/Triangle/` since
  Chapter 06, which is already the per-demo shader folder the index asks for,
  and Chapter 06 section 1's glob mirrors them to
  `Shaders/Triangle/*.spv` beside the executable. The paths in the desc are
  the ones the renderer used.

### Where a demo's panel goes: `beginDemoPanel`

Every demo has a panel, and they all open in one place: the left column, under
"Frame" at y = 220, or, from Chapter 10 on, under the "Camera" panel a 3D demo
adds, at y = 470. In a 1280 × 720 window that leaves a 3D demo's panel 240
pixels, about nine rows. The triangle's three sliders fit; Chapter 25's grass
panel has more than sixty rows.

A panel that sizes itself to its contents grows until it is as tall as the
program's window, wherever it starts, rather than until it reaches the bottom
edge. A tall panel opened 470 pixels down therefore runs off the bottom, and
scrolling cannot help: scrolled to the end, its last rows sit at the bottom of
the panel, which is below the edge, so they can never be seen. The cure is to
stop the panel at the bottom edge, so that it ends in view and what does not
fit scrolls inside it.

That is one function, which every demo's main panel calls instead of
`SetNextWindowPos` and `Begin`. It goes in `DebugPanels`, beside the demo
picker: the left column is the engine's layout rather than any one demo's, and
`DebugPanels` depends on nothing a demo owns, so demos and engine alike can call
it. **This is `Source/PillowFort/DebugPanels/DemoPanel.h`:**

```cpp
// Source/PillowFort/DebugPanels/DemoPanel.h
#pragma once

namespace pf::debug_panels {

// Where a demo's main panel opens: the left column, under the engine's windows.
enum class DemoPanelSlot
{
    BelowFrame,    // under Chapter 07's "Frame": a demo without a camera
    BelowCamera,   // under Chapter 10's "Camera": a demo with one
};

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
    const float room    = ImGui::GetIO().DisplaySize.y - 10.0f - data->Pos.y;
    data->DesiredSize.y = std::min(data->DesiredSize.y, room);
}

namespace pf::debug_panels {

void stopNextWindowAtScreenBottom()
{
    // No fixed limits: the callback caps the height every frame from where the window is
    // now, so a window dragged higher has room to grow.
    ImGui::SetNextWindowSizeConstraints(ImVec2(0.0f, 0.0f), ImVec2(FLT_MAX, FLT_MAX), stopAtScreenBottom);
}

bool beginDemoPanel(const char* name, DemoPanelSlot slot)
{
    // The left column on first use: "Frame" from y = 10, "Camera" from 220, a 3D demo's panel from 470.
    const float top = slot == DemoPanelSlot::BelowFrame ? 220.0f : 470.0f;
    ImGui::SetNextWindowPos(ImVec2(10.0f, top), ImGuiCond_FirstUseEver);
    stopNextWindowAtScreenBottom();
    return ImGui::Begin(name, nullptr, ImGuiWindowFlags_AlwaysAutoResize);   // fits its contents, up to the cap
}

} // namespace pf::debug_panels
```

- **The limit is a function, not a number.** `SetNextWindowSizeConstraints`
  takes a smallest and a largest size, and optionally a function that ImGui
  calls while it sizes the window, handing it the window's position (`Pos`) and
  the size it is about to take (`DesiredSize`), which the function may lower.
  A fixed largest size worked out from y = 470 would stay 240 pixels wherever
  the panel was dragged; measured from `Pos` every frame, the limit follows the
  panel when it is dragged, and the program's window when that is resized.
- **`AlwaysAutoResize`** fits the panel to its contents every frame, up to the
  limit: a short panel stays short, and the scrollbar appears only when the
  contents outgrow the room.
- **`ImGuiCond_FirstUseEver`**, as for "Frame" in Chapter 07: the slot is where
  the panel starts, and the user may move it.
- **`stopNextWindowAtScreenBottom`** is the limit on its own, for a demo's
  second window, which opens somewhere else. Chapter 29's ocean preview is the
  first.

The triangle's panel is the first caller. `ShaderParameters.cpp` includes
`"PillowFort/DebugPanels/DemoPanel.h"`, and `drawShaderParameters` begins:

```cpp
bool drawShaderParameters(ShaderParameters& parameters)
{
    bool changed = false;
    if (debug_panels::beginDemoPanel("Shader", debug_panels::DemoPanelSlot::BelowFrame))
    {
```

The `ImGui::End()` after the `if` stays where it was: like `Begin`,
`beginDemoPanel` needs its `End` whether it returned true or not. Every later
demo's panel begins the same way.

A long panel has one more habit, and Chapter 21's particles are the first to
use it: its statistics stay in view, and each group of controls goes under
`if (ImGui::CollapsingHeader("Name"))` instead of a `SeparatorText` label. The
header is a bar with the group's name, closed until it is clicked, and it
returns true while open, so a closed group costs one row.

---

## 7. `SandboxGame`: the list, the picker, and the loop

ROADMAP says `SandboxGame` "owns the only `main()` and constructs everything
explicitly. No singletons, service locators, static registration." For demos,
that means the list of demos is a variable in `main`.

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
Constructing every demo up front costs nothing, because constructors do
nothing (section 2): an unvisited demo is a few bytes of default member
values. `main` includes each demo's header — for now
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
cannot click. Chapter 05's command line grows one option. A demo is not a
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

In Chapter 05's `parseSettings`, the return type and the local become
`LaunchSettings`, the two existing branches write `settings.renderer.preferredGpu`
and `settings.renderer.presentMode`, and one branch joins them before the final
`else`:

```cpp
        else if (key == "--demo")
        {
            settings.demo = value;
        }
```

`main` now parses first — `const LaunchSettings settings = parseSettings(argc, argv);`
as its first line — and passes `settings.renderer` to `renderer.initialize`.
The name is matched the way `--gpu` matches a device, by part, so
`--demo Tri` is enough for the triangle (and, after section 8, `--demo Grad`
for the gradient):

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

To start Visual Studio's debugger on a demo, it goes where Chapter 05 put the
other options: `debugargs { "--demo", "Gradient" }` in `premake5.lua`'s
`SandboxGame` project.

### The picker

**This is `ImGuiDebugPanels`.** Chapter 07 put the panels every demo shares
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
    // height follows the list and the status line.
    const ImGuiIO& io = ImGui::GetIO();
    ImGui::SetNextWindowPos(ImVec2(io.DisplaySize.x - 10.0f, 10.0f), ImGuiCond_Always,
                            ImVec2(1.0f, 0.0f));
    ImGui::SetNextWindowSizeConstraints(ImVec2(240.0f, 0.0f), ImVec2(240.0f, FLT_MAX));
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

`FLT_MAX` needs `<cfloat>` in `ImGuiDebugPanels.cpp`. `main` passes
`renderer.demoError()` as the status, and a detached demo stays selected in the
list — the honest answer to "what did I pick?" — so to retry one that failed,
pick another and come back.

### The loop

Three changes to Chapter 07 section 10's loop: the event filter keeps what it
lets through instead of discarding it, a switch can happen, and the active demo
is updated. **This is
the frame loop in `main`,** from `window.pollEvents()` to `drawFrame`, with
Chapter 07's statistics and present-mode lines left as they were:

```cpp
        window.pollEvents();
        renderer.beginUiFrame();                    // ImGui::NewFrame: WantCapture* now valid

        // The queue is drained once per frame, per the roadmap. What survives
        // the filter is the active demo's (Chapter 09 section 7).
        const ImGuiIO&             io = ImGui::GetIO();
        std::vector<window::Event> demoEvents;
        for (const window::Event& event : window.drainEvents())
        {
            if (event.kind == window::EventKind::FramebufferResized)
            {
                renderer.notifyFramebufferResized();   // never filtered: ImGui does not own the window size
                continue;
            }

            if (io.WantCaptureMouse && event.isMouse())       { continue; }   // Chapter 07 section 4
            if (io.WantCaptureKeyboard && event.isKeyboard()) { continue; }
            demoEvents.push_back(event);
        }

        debug_panels::FrameStatistics statistics = renderer.frameStatistics();
        statistics.cpuMilliseconds = frameMilliseconds;
        statistics.history         = history;
        statistics.frameIndex      = frameCount++;
        renderer.debugPanels().drawFrameStatistics(statistics);

        // After drawFrameStatistics.
        VkPresentModeKHR presentMode = renderer.swapchain().presentMode();
        if (renderer.debugPanels().drawPresentModePicker(renderer.swapchain().supportedPresentModes(),
                                                         presentMode))
        {
            renderer.setPresentMode(presentMode);
        }

        // Chapter 09: switch before Update, so a demo is never torn down after
        // it has drawn ImGui widgets that this frame will still render.
        if (renderer.debugPanels().drawDemoPicker(demoNames, selectedDemo, renderer.demoError()))
        {
            renderer.switchDemo(demoList[selectedDemo].get());
        }

        const float elapsedSeconds = std::chrono::duration<float>(
            std::chrono::steady_clock::now() - startTime).count();

        if (demos::Demo* demo = renderer.demo(); demo != nullptr)
        {
            demo->Update({
                .deltaSeconds   = std::min(frameMilliseconds / 1000.0f, 0.1f),   // no leap after a stall
                .elapsedSeconds = elapsedSeconds,
                .events         = demoEvents,
            });
        }

        // Its clear color is what the scene shows while no demo is active.
        const vulkan_graphics::FrameRequest request{};

        if (renderer.drawFrame(request) == vulkan_graphics::FrameStatus::Failed)
        {
            Log::error("Rendering failed. Shutting down.");
            break;
        }
```

The filter is Chapter 07 section 4's, unchanged; what passes it is now kept in
`demoEvents` for the demo. Chapter 10 section 10 refines it once, for a camera
that tracks held keys. Window resizes still go straight to the renderer and never reach `events`;
the demo hears about them as `Resize`, after the targets exist.

**`Update` gets the input in `FrameInput`.** `events` is a span over this
frame's `demoEvents`, valid only during the call, which is the only time a
demo needs it — a controller turns events into its own state then.
`deltaSeconds` is clamped to a tenth of a second. The first frame after the
window is restored, or after Windows' modal resize loop (Chapter 02 section 4)
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

**`FrameRequest` now means "no demo".** Chapter 05's animated clear color moved
into the triangle, so `main` passes a default `FrameRequest`, whose
`clearColor` is what the renderer clears the scene target to when no demo is
active — a dark blue-grey that says "nothing is drawing" rather than "broken".
Chapter 05 section 2 asked this struct to stay the handful of values `main`
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

- **the triangle exactly as at the end of Chapter 08**: the same bands, the
  same animated background, and the "Shader" panel under "Frame", whose sliders
  still change it;
- **a "Demos" panel in the top-right corner** listing Triangle alone, selected;
- **validation silent**, through resizing the window and through closing it,
  and no assertion from `vmaDestroyAllocator` at exit: the triangle's
  `Teardown` freed what its `Setup` made.

If the scene is dark blue-grey with a message under the picker, the triangle
failed in `Setup` and was detached (section 5); the message says why.

---

## 8. The second demo

ROADMAP's exit check for this step: *adding a second demo touches only its own
folder plus one registration line.* The index makes "its own folder" two
folders — `Source/PillowFort/Demos/<Name>/` and `Shaders/<Name>/` — and the
second demo exists to prove the claim. It is deliberately tiny: a fullscreen
gradient between two colors you pick, so that everything in it is plumbing.

### One engine change first

A demo's push-constant block has a C++ side and a GLSL side, and Chapter 08
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
Chapter 06 section 1's shader glob already compiles any
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

The shader draws with Chapter 06 section 2's fullscreen vertex shader, which
hands it `uv`. Both colors come from ImGui swatches, so they are sRGB and are
decoded before blending — Chapter 08 section 4's color-boundary table, and the
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
through the `-I` for `Shaders/Include` that Chapter 06's `shaderCommands`
passes to every `glslc` call — it is the triangle's decode from Chapter 08
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
    void                 Record(const RecordContext& frame) override;
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
  block; `stageFlags` must cover every stage that does (Chapter 08 section 5),
  and need cover no more. `Record`'s `vkCmdPushConstants` says the same.
- **The vertex shader is `"Fullscreen/Fullscreen.vert.spv"`**, Chapter 06
  section 2's, shared, and the fragment shader `"Gradient/Gradient.frag.spv"`.
- **The two `static_assert`s go**: `GradientTypes.h` asserts its own layout.

The pipeline still passes `m_context.formats.depth`, as every scene pipeline
must from Chapter 10 on. The rest of the class:

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

void GradientDemo::Record(const RecordContext& frame)
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
| `switchDemo(demo)` | `vkDeviceWaitIdle` → old `Teardown` → new `Setup(context)` → new `Resize(targets)` → active. If `Setup` or `Resize` fails: `detachDemo` — new `Teardown`, no active demo, the reason in `demoError()` |
| Every frame, in `main` | `pollEvents` → `beginUiFrame` → drain and filter events → frame statistics and present-mode picker → demo picker (a switch happens here) → active `Update(input)` → `drawFrame` |
| Inside `drawFrame` | fence wait for this slot → acquire → active `Record(frame)`, or the engine's clear → composite and ImGui → submit → present → `recreateSwapchain` if needed |
| `recreateSwapchain` | `VulkanSwapchain::recreate` (`vkDeviceWaitIdle`) → engine rebuilds its targets → composite set rewritten → active `Resize(targets)`. A failed `Resize` detaches the demo and the frame goes on |
| Shutdown | `vkDeviceWaitIdle` → active `Teardown` → ImGui shutdown → engine objects → `vmaDestroyAllocator` (asserts on a demo's leak) |

And the rules that follow from it:

- **`Update` is before the fence wait.** CPU state and ImGui only; no per-frame
  GPU writes, no commands.
- **`Record` is after the fence wait.** The first moment `frameIndex`'s
  per-frame buffers may be written or read back.
- **`Resize` is after a `vkDeviceWaitIdle`,** so the old size-dependent objects
  may be destroyed on the spot.
- **Destroying anything mid-run that an in-flight frame may still use** —
  replacing a mesh from a panel button, say — needs a `vkDeviceWaitIdle` first.
  `switchDemo` and `Resize` already provide one; anywhere else, the demo does.

---

## 10. How later chapters plug in

Nothing here needs building now. The next chapter is the first to use what
this one left open:

- **Depth (Chapter 10).** The depth buffer is window-sized, so it is the
  engine's, beside the scene target. `SceneFormats::depth` becomes
  `D32_SFLOAT`, `SceneTargets` gains the depth image and view, and
  `beginScenePass` grows the depth attachment and Chapter 04's depth row.
  Both demos here keep working unchanged, because their pipelines already
  declare `context.formats.depth`.

Every later chapter plugs in the same way: what is sized to the window is the
engine's, everything else is the demo's, and section 4's contract is where the
two meet.

---

## If something goes wrong

| Symptom | Likely cause |
| --- | --- |
| `ShaderParameters`: undeclared identifier, in `VulkanRenderer.cpp` | A line of the triangle's left behind in `initialize`, `recordFrame`, or `shutdown` (section 5) |
| A new demo's files are not compiled, or `LNK2019` for its functions | `GenerateProjects.bat` not rerun after adding them |
| `VUID-vkCmdDraw-imageLayout-00344` at the composite's draw: the scene image is `COLOR_ATTACHMENT_OPTIMAL`, the descriptor says `SHADER_READ_ONLY_OPTIMAL` | The demo's `Record` skipped `handBackSceneTarget` |
| A layout error or `SYNC-HAZARD-WRITE-AFTER-WRITE` at the hand-back barrier | Its source half does not describe what the demo did last — a compute demo passing the defaults, which say `COLOR_ATTACHMENT_OPTIMAL` |
| Validation: depth attachment format mismatch, after Chapter 10 | A demo's pipeline does not pass `context.formats.depth` |
| Validation about destroyed pipelines or buffers in use, when switching | Something destroyed outside `Teardown`, or a switch path that skipped `vkDeviceWaitIdle` |
| Assertion in `vmaDestroyAllocator` at exit | A demo's `Teardown` misses a `destroyBuffer` or `vmaDestroyImage` |
| Validation reports an invalid `VkPipeline` in `vkDestroyPipeline`, switching away from a demo the second time | `Teardown` destroyed a handle without resetting it to `VK_NULL_HANDLE`; when the next `Setup` failed before replacing it, `Teardown` destroyed it again |
| The scene is dark blue-grey and the picker shows a message | The selected demo failed in `Setup` or `Resize` and was detached; the message says why |
| A demo's panel runs off the bottom of the window, and its last rows cannot be reached | The panel calls `SetNextWindowPos` and `ImGui::Begin` itself instead of `beginDemoPanel` (section 6) |

---

## Exit check

- [ ] The triangle runs as a registered demo and looks exactly as it did in
      Chapter 08: same bands, same animated background, same Shader panel.
- [ ] The Demos panel lists Triangle and Gradient. Switching back and forth
      twenty times is validation-clean, with synchronization validation proven
      on by Chapter 05's positive control. The Shader panel is shown only with
      the triangle, the Gradient panel only with the gradient.
- [ ] Drag the Shader panel by its title bar to the bottom of the window: once
      its rows reach the bottom edge it gets shorter and shows a scrollbar,
      instead of running off. Drag it back up and it grows to fit its rows.
- [ ] With the gradient active, resizing the window increases its panel's
      resize count and shows the new extent; so does changing the present mode,
      with the extent unchanged.
- [ ] **The contract is checked, not assumed.** Temporarily change
      `handBackSceneTarget`'s default `lastAccess` to `VK_ACCESS_2_NONE`. The
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
      Widening the window again does not bring the gradient back; picking it
      again does.
- [ ] `SandboxGame --demo Grad` starts on the gradient.
- [ ] Closing with either demo active is validation-clean, and
      `vmaDestroyAllocator` does not assert.
- [ ] Adding the gradient changed only `Source/PillowFort/Demos/Gradient/`,
      `Shaders/Gradient/`, and two lines of `Main.cpp` — checked with
      `git status`.

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
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_pipelineLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the gradient.");
    }

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

void GradientDemo::Record(const RecordContext& frame)
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
