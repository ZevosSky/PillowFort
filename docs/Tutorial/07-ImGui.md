# 07 — ImGui Debug Panels

**Goal:** interactive panels over the triangle, without ImGui taking ownership
of your input.

**ROADMAP:** step 8.

**Module:** `DebugPanels`, namespace `pf::debug_panels`, type
`ImGuiDebugPanels`.

`ImGuiDebugPanels` owns ImGui's lifetime and the panels every demo shares —
frame statistics, and pickers for settings such as the present mode. A panel
that edits one demo's parameters belongs beside those parameters instead
(section 9), which is what lets ROADMAP step 10 add a demo without touching
this module.

**Prerequisites:**
[Chapter 2, section 4](02-Instance-And-Device.md#4-the-window-and-the-surface)
(the `Window` module and its event queue),
[Chapter 3, section 2](03-Swapchain.md#2-choosing-the-format) (the `_SRGB`
swapchain, which section 6 here pays for), Chapter 4's class map and section 2
(frames in flight, which section 3's `ImageCount` must cover),
[Chapter 5, section 3](05-First-Frame.md#3-where-the-loop-lives) (the frame loop
that section 10 extends), and Chapter 6 (the pipeline cache from section 6, and
the triangle the panels draw over).

This is the chapter that makes the project a *workbench* rather than a demo.
Everything after it is easier to debug because you can put state on screen and
change it without recompiling.

**ImGui is an immediate-mode GUI**, which is not how most widget toolkits work.
It keeps no window or button objects for you to create and update. Instead,
every frame, you call a function per widget —
`ImGui::SliderFloat("Amplitude", &value, 0.0f, 4.0f)` — which both draws the
slider this frame and returns whether the user just changed `value`. ImGui
turns the frame's calls into triangles, and its Vulkan backend records them
into your command buffer. So calling `ImGui::Begin` and the widgets again
every frame is the design, not a mistake, and a panel is just a function you
call between the frame's start and its recording.

---

## 1. Check the backend's header first

The ImGui Vulkan backend changes shape between versions. The code below matches
the pin, **v1.92.9b-docking**. **Open
`Vendor/ImGui/backends/imgui_impl_vulkan.h` and read `ImGui_ImplVulkan_InitInfo`
before typing any of this.** It is about 40 lines, plus the
`ImGui_ImplVulkan_PipelineInfo` struct it embeds, just above it. It is the
authoritative version for your pin, and checking takes less time than
debugging a struct mismatch. Where the header's comments and the change log at
the top of `imgui_impl_vulkan.cpp` disagree, the change log is right; section 2
meets one such case.

---

## 2. The descriptor pool — let the backend make it

A shader finds an image through a **descriptor set**, a small object that
points at it; Chapter 8, section 6 builds them. ImGui needs one for every
texture it draws — its font atlas, plus any image you register — and allocates
them from a **descriptor pool**. It wants its own pool, so its allocations
never interact with yours, and **the pinned backend will make that pool
itself**: set `DescriptorPoolSize` in the init info (section 3) and leave
`DescriptorPool` null. The backend creates the pool, sizes it correctly, and
destroys it in its own shutdown.

Do not hand-build the pool from an older tutorial: the classic recipe's pool
holds `COMBINED_IMAGE_SAMPLER` descriptors, which the header's comment still
asks for, but the pinned backend allocates separate `SAMPLED_IMAGE` and
`SAMPLER` descriptors (its change log entry of 2026-04-22), so that pool holds
none of what it allocates. A strict driver then fails inside
`ImGui_ImplVulkan_Init` with `VK_ERROR_OUT_OF_POOL_MEMORY`; a lenient one runs
it, and validation does not check pool sizes.

Sixty-four sets is generous for a font atlas alone, and leaves room for what
you will want later: **showing your own images inside ImGui windows.**
`ImGui_ImplVulkan_AddTexture(view, layout)` returns a `VkDescriptorSet` you can
pass straight to `ImGui::Image()`, where `layout` is the layout the image will
be in *when ImGui draws*, not the one it is in now. Chapter 9 lists it among
what a demo may create for itself.

---

## 3. Initialization

Everything the backend needs arrives in one create-info. `VulkanRenderer`
fills it, because it already holds every handle on the list (section 10):

```cpp
// Source/PillowFort/DebugPanels/ImGuiDebugPanels.h
struct ImGuiDebugPanelsCreateInfo
{
    GLFWwindow*      window              = nullptr;
    VkInstance       instance            = VK_NULL_HANDLE;   // VulkanInstance::Instance()
    VkPhysicalDevice physicalDevice      = VK_NULL_HANDLE;
    VkDevice         device              = VK_NULL_HANDLE;
    uint32_t         graphicsQueueFamily = 0;
    VkQueue          graphicsQueue       = VK_NULL_HANDLE;
    uint32_t         minImageCount       = 2;                // ImGui requires >= 2
    uint32_t         imageCount          = 2;                // VulkanSwapchain::imageCount()
    VkPipelineCache  pipelineCache       = VK_NULL_HANDLE;   // Chapter 06 section 6
    VkFormat         colorFormat         = VK_FORMAT_UNDEFINED;   // the swapchain's
};
```

`ImGuiDebugPanels` itself holds no Vulkan objects: the backend creates, owns,
and destroys everything, including the descriptor pool from section 2. Its
only members are section 5's UI-scale and frame-lifetime state; it borrows no
GPU handles either.
Its functions are tagged with the section that writes them (`setUiScale` is
section 5's too):

```cpp
// Source/PillowFort/DebugPanels/ImGuiDebugPanels.h, inside namespace pf::debug_panels
class ImGuiDebugPanels
{
public:
    ImGuiDebugPanels() = default;
    ImGuiDebugPanels(const ImGuiDebugPanels&) = delete;
    ImGuiDebugPanels& operator=(const ImGuiDebugPanels&) = delete;

    InitializationResult initialize(const ImGuiDebugPanelsCreateInfo& info);   // section 3
    void beginFrame();                                                         // section 5
    void record(VkCommandBuffer commandBuffer);                                // section 5
    void discardFrame();                                                       // section 5
    void drawFrameStatistics(const FrameStatistics& statistics);              // section 7
    bool drawPresentModePicker(std::span<const VkPresentModeKHR> supported,
                               VkPresentModeKHR& current);                     // section 7
    void setUiScale(float scale);
    float uiScale() const { return m_requestedUiScale; }
    void shutdown();                                                           // section 8

private:
    ImGuiStyle m_baseStyle;
    float m_requestedUiScale = 1.0f;
    float m_appliedUiScale = 1.0f;
    bool m_scaleInitialized = false;
    bool m_scaleSliderDragging = false;
    bool m_frameBegun = false;   // NewFrame has not yet reached Render or EndFrame
    ImVec2 m_lastDisplaySize{};
};
```

One panels object owns the ImGui context and backend lifecycle. It stays in
place from `initialize` through `shutdown`; copying those responsibilities
would give two objects control of the same resources. The deleted copy
operations also suppress implicit moves. The default constructor only sets
CPU state; fallible setup still belongs in `initialize`.

The header includes `InitializationResult.h`, `<imgui.h>` (for `ImGuiStyle`
and `ImVec2`), `<vulkan/vulkan.h>`, `<array>`, `<span>`, and `<string>`, and
forward-declares `struct GLFWwindow;`. Section 7's `FrameStatistics` goes above
the class, which takes it by reference. The `.cpp` includes ImGui, both backends,
`Log.h`, `<algorithm>`, `<cmath>`, `<format>`, and
`<vulkan/vk_enum_string_helper.h>`. It also includes `<imgui_internal.h>` for the
pinned version's window-rescale helper; that version-sensitive dependency stays
in this module, not in every demo.

The backend reports its own Vulkan failures through a callback you supply:

```cpp
// File scope, above the namespace block in ImGuiDebugPanels.cpp.
static void checkVulkanResult(VkResult result)
{
    if (result == VK_SUCCESS) { return; }
    Log::error(std::format("ImGui Vulkan backend: {}", string_VkResult(result)).c_str());
}
```

```cpp
// Source/PillowFort/DebugPanels/ImGuiDebugPanels.cpp
InitializationResult ImGuiDebugPanels::initialize(const ImGuiDebugPanelsCreateInfo& info)
{
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();

    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    io.ConfigFlags |= ImGuiConfigFlags_DockingEnable;
    io.IniFilename = nullptr;   // see note below

    ImGui::StyleColorsDark();
    m_baseStyle = ImGui::GetStyle();
    m_appliedUiScale = 1.0f;
    m_scaleSliderDragging = false;
    m_lastDisplaySize = {};
    // The implicit small default is a bitmap font. Use the vector default for crisp live resizing.
    io.Fonts->AddFontDefaultVector();
    if (!m_scaleInitialized)
    {
        setUiScale(ImGui_ImplGlfw_GetContentScaleForWindow(info.window));
    }

    // false: the Window module owns the GLFW callbacks. See section 4.
    if (!ImGui_ImplGlfw_InitForVulkan(info.window, false))
    {
        return InitializationResult::failure("ImGui GLFW backend failed to initialize.");
    }

    const VkFormat colorFormat = info.colorFormat;
    const VkPipelineRenderingCreateInfo renderingInfo{
        .sType                   = VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO,
        .colorAttachmentCount    = 1,
        .pColorAttachmentFormats = &colorFormat,
    };

    ImGui_ImplVulkan_InitInfo vulkanInfo{};
    vulkanInfo.ApiVersion                  = VK_API_VERSION_1_3;
    vulkanInfo.Instance                    = info.instance;
    vulkanInfo.PhysicalDevice              = info.physicalDevice;
    vulkanInfo.Device                      = info.device;
    vulkanInfo.QueueFamily                 = info.graphicsQueueFamily;
    vulkanInfo.Queue                       = info.graphicsQueue;
    vulkanInfo.DescriptorPoolSize          = 64;   // section 2: the backend makes the pool
    vulkanInfo.MinImageCount               = info.minImageCount;
    vulkanInfo.ImageCount                  = info.imageCount;
    vulkanInfo.PipelineCache               = info.pipelineCache;
    vulkanInfo.UseDynamicRendering         = true;
    vulkanInfo.CheckVkResultFn             = &checkVulkanResult;

    // Since 2025-09-26 these live on PipelineInfoMain, not on InitInfo itself.
    vulkanInfo.PipelineInfoMain.MSAASamples                 = VK_SAMPLE_COUNT_1_BIT;
    vulkanInfo.PipelineInfoMain.PipelineRenderingCreateInfo = renderingInfo;

    if (!ImGui_ImplVulkan_Init(&vulkanInfo))
    {
        return InitializationResult::failure("ImGui Vulkan backend failed to initialize.");
    }

    return InitializationResult::success();
}
```

Points that matter:

- **`UseDynamicRendering = true` and a valid
  `PipelineInfoMain.PipelineRenderingCreateInfo`.** Without both, the backend
  has neither a `VkRenderPass` nor a list of attachment formats to build its
  pipeline against, so `ImGui_ImplVulkan_Init` skips the pipeline without a
  word and a later `RenderDrawData` binds a null one. A zero `sType` counts as
  missing (the backend's assert on it is only in
  `ImGui_ImplVulkan_CreateMainPipeline`, which `Init` then never calls), so set
  it. The format must match the attachment you will actually draw into — the
  swapchain's, `m_swapchain.format()`.
- **`ImageCount` sizes the backend's ring of vertex and index buffers**, one
  taken per `RenderDrawData`, so it must be at least Chapter 4's two frames in
  flight, or ImGui rewrites a buffer the GPU may still be reading. The
  swapchain's image count, at least the surface's minimum plus one (Chapter
  3, section 5), is at least two on any surface that allows two. The backend
  asserts that `MinImageCount` is at least 2; beyond that, `MinImageCount`
  only sizes swapchains the backend would make for extra OS windows, which
  this engine does not enable. Neither needs updating when the swapchain is
  recreated.
- **The two config flags.** `NavEnableKeyboard` lets Tab and the arrow keys
  move between widgets, and is why a clicked panel keeps the keyboard
  (section 4). `DockingEnable` lets you drag one panel onto another to make
  tabs; the pin is ImGui's docking branch, ROADMAP's choice, and nothing in
  this chapter docks a panel for you.
- **`io.IniFilename = nullptr` is a starting choice, not a final one.** ImGui
  persists window positions to `imgui.ini` in the working directory by default,
  which pollutes your repo root. Once you have panels you care about arranging,
  point it at a real path beside the executable and *keep* the layout — a
  parameter workbench you have to rearrange every launch does not get used.
- **`CheckVkResultFn`** routes the backend's internal Vulkan errors into
  `ErrorReporting` instead of silence.
- **The startup scale is the OS window content scale, not an extra multiplier.**
  `AddFontDefaultVector()` supplies a vector font for crisp resizing. Store the
  dark style before scaling it, then queue the content scale as the requested
  value through `setUiScale`; section 5 applies it to a fresh copy of that
  style before the next `NewFrame`. The `m_scaleInitialized` guard keeps a
  scale already chosen if `initialize` ever runs again on the same object;
  nothing in this program does that yet.

---

## 4. Input forwarding, and why the roadmap is right

`ImGui_ImplGlfw_InitForVulkan(window, false)` — the `false` means "do not
install GLFW callbacks". ROADMAP requires this, because the `Window`
module owns the callbacks and queues events, and letting ImGui install its own
would either replace the window's callbacks or, because ImGui calls whichever
callback was installed before its own, make delivery depend on which module
happened to initialize first.

The cost is that you forward manually, and the forwarding has a dependency
problem: `Window` must not know `DebugPanels` exists. So `Window` exposes an
optional set of forwarding hooks — plain GLFW callback types, nothing
ImGui-specific — and `SandboxGame`, the only place that knows both modules,
fills them in.

<a id="ch07-input"></a>

### Attempt CH07-input: let ImGui and the window share input without owning each other

Keep the backend's callback installation disabled. Add optional
GLFW-shaped forwarding hooks to `GlfwWindow`, register the window's own
callbacks, and connect the hooks from `SandboxGame` after ImGui initializes.
A key must reach ImGui and the engine event queue once each; typed characters
must reach a text field; missing hooks must be harmless. Include mouse
buttons, cursor position, scroll, cursor enter/leave and window focus. The
window module must compile without an ImGui include. The panels look pale at
this stage for a reason unrelated to input (section 6), so judge the input by
the exit check's tests, not by how the panel looks.

**Acceptance:** Each key reaches ImGui and the engine queue once, text input
works, `GlfwWindow` compiles without an ImGui include, and the window runs
with no forwarding hooks set.

**Transfer:** Leave the optional hooks unset, then reconnect them. Predict which engine events remain unchanged and verify no duplicate delivery or null-hook crash.

<details>
<summary>Hint 1: the dependency belongs in the composition root</summary>

`SandboxGame` knows both modules and can connect them. `GlfwWindow` only needs
function pointers with GLFW's signatures, not a debug-panel object.

</details>

<details>
<summary>Hint 2: distinguish physical keys from text</summary>

Each engine callback first invokes its optional forwarding hook, then queues
the engine event if that event belongs to its queue. Character input is a
separate callback from key presses; forwarding only keys does not deliver
text. Cursor enter/leave and window focus can be forwarded without adding
engine events.

</details>

<details>
<summary>Hint 3: wire all seven callbacks after the context exists</summary>

Use GLFW's callback typedefs in the hook struct and its seven `glfwSet*Callback`
functions during window initialization. Then assign the matching
`ImGui_ImplGlfw_*Callback` functions through `setInputForwarding` in `main`,
after `ImGuiDebugPanels::initialize` succeeds.

</details>

<details>
<summary>Worked solution: forwarding and connecting input</summary>

```cpp
// Source/PillowFort/Window/GlfwWindow.h
// Every member is optional. GLFW's own typedefs, so any GLFW-shaped
// callback fits - ImGui's backend entry points are exactly that shape.
struct InputForwarding
{
    GLFWkeyfun         key            = nullptr;
    GLFWcharfun        character      = nullptr;
    GLFWmousebuttonfun mouseButton    = nullptr;
    GLFWscrollfun      scroll         = nullptr;
    GLFWcursorposfun   cursorPosition = nullptr;
    GLFWcursorenterfun cursorEnter    = nullptr;
    GLFWwindowfocusfun windowFocus    = nullptr;
};

// On GlfwWindow:
//     void setInputForwarding(const InputForwarding& forwarding) { m_forwarding = forwarding; }
```

Each callback forwards first, then queues its own event:

```cpp
// Source/PillowFort/Window/GlfwWindow.cpp
void GlfwWindow::onKey(GLFWwindow* window, int key, int scancode, int action, int mods)
{
    GlfwWindow* owner = self(window);   // glfwGetWindowUserPointer, from Chapter 02 section 4
    if (owner->m_forwarding.key != nullptr) { owner->m_forwarding.key(window, key, scancode, action, mods); }
    owner->queueEvent(Event::key(key, action, mods));
}

void GlfwWindow::onChar(GLFWwindow* window, unsigned int codepoint)
{
    GlfwWindow* owner = self(window);
    if (owner->m_forwarding.character != nullptr) { owner->m_forwarding.character(window, codepoint); }
}

// onMouseButton, onScroll, and onCursorPos follow onKey: forward, then queue.
// onCursorEnter and onWindowFocus follow onChar: forward only.
```

GLFW calls none of them until they are registered: without the seven lines
below, no click reaches ImGui or the queue. Declare all seven where Chapter 2,
section 4's header comment left room, each with its GLFW type's signature, and
register them in `initialize`, in place of its "Chapter 7 registers" comment:

```cpp
// Source/PillowFort/Window/GlfwWindow.cpp, in initialize, after the resize callback.
glfwSetKeyCallback(m_window, &GlfwWindow::onKey);
glfwSetCharCallback(m_window, &GlfwWindow::onChar);
glfwSetMouseButtonCallback(m_window, &GlfwWindow::onMouseButton);
glfwSetScrollCallback(m_window, &GlfwWindow::onScroll);
glfwSetCursorPosCallback(m_window, &GlfwWindow::onCursorPos);
glfwSetCursorEnterCallback(m_window, &GlfwWindow::onCursorEnter);
glfwSetWindowFocusCallback(m_window, &GlfwWindow::onWindowFocus);
```

And `SandboxGame` connects them, **after** `ImGuiDebugPanels::initialize` —
forwarding into ImGui before its context exists crashes on the first mouse
move:

```cpp
// Source/SandboxGame/Main.cpp
window.setInputForwarding({
    .key            = ImGui_ImplGlfw_KeyCallback,
    .character      = ImGui_ImplGlfw_CharCallback,
    .mouseButton    = ImGui_ImplGlfw_MouseButtonCallback,
    .scroll         = ImGui_ImplGlfw_ScrollCallback,
    .cursorPosition = ImGui_ImplGlfw_CursorPosCallback,
    .cursorEnter    = ImGui_ImplGlfw_CursorEnterCallback,
    .windowFocus    = ImGui_ImplGlfw_WindowFocusCallback,
});
```

Forgetting `character` is the classic one: every key works except typing in
a text field, which you notice weeks later.

The complete forwarding is in
[GlfwWindow.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Window/GlfwWindow.cpp);
[ImGuiDebugPanels.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/DebugPanels/ImGuiDebugPanels.cpp)
initializes the backend that receives it.

</details>

### Who gets the input

Every event now goes to ImGui *and* into the window's queue, so the frame loop
decides who acts on it. ImGui answers with two flags on `ImGui::GetIO()`:
`WantCaptureMouse` is true when the cursor is over an ImGui window or dragging
a widget, and `WantCaptureKeyboard` when a text field has focus or, because
section 3 turned on keyboard navigation, whenever an ImGui window has focus:
after a click on a panel, keys stop at the filter until you click the scene.
The loop skips the queued mouse events while the first is set, and
the keyboard events while the second is — section 10 shows the code. Without
that filter, dragging a slider also spins Chapter 10's camera.

These flags are only valid **after `ImGui::NewFrame()`**. Reading them before
gives you last frame's answer, which is usually right and occasionally produces
a one-frame glitch that is maddening to reproduce.

---

## 5. The frame

**Stage boundary:** This chapter builds a small floating Frame panel,
including its scale slider. The finished reference in `Source/` moves the
scale into a pinned toolbar and groups the controls into a sidebar
(`DemoPanel.cpp`). Build this chapter from its own listings as one set, and do
not mix in that later code: the two pair their window calls differently. The
optional
[control-workspace transfer at the end of Chapter 9](09-Demo-Harness.md#control-workspace-transfer)
is for a later return, after several demos exist, not a prerequisite for this
chapter.

### Beginning, recording and discarding a frame

Every ImGui frame has three moments, and each is one function on
`ImGuiDebugPanels`. **`beginFrame`** starts the frame. The backends'
`NewFrame` calls go first: GLFW's hands ImGui this frame's display size, time
step and mouse state, and Vulkan's only checks that section 3 initialized it.
Then `ImGui::NewFrame` opens the frame that widgets are added to, and from
then on section 4's `WantCapture*` flags describe this frame. **`record`**
ends it: `ImGui::Render` closes the frame and turns its widgets into draw
data, which the backend records into your command buffer. **`discardFrame`**
ends a frame that began but will not be recorded, because `drawFrame` skipped
it or failed before recording. Every `NewFrame` must reach either `Render` or
`EndFrame`, or the next `NewFrame` asserts without saying which frame was
dropped. The `m_frameBegun` flag in section 3's class remembers whether a
begun frame still owes one of those two calls.

```cpp
// Source/PillowFort/DebugPanels/ImGuiDebugPanels.cpp
void ImGuiDebugPanels::beginFrame()
{
    ImGui_ImplVulkan_NewFrame();
    ImGui_ImplGlfw_NewFrame();
    ImGui::NewFrame();
    m_frameBegun = true;
}

void ImGuiDebugPanels::record(VkCommandBuffer commandBuffer)
{
    ImGui::Render();
    m_frameBegun = false;
    ImGui_ImplVulkan_RenderDrawData(ImGui::GetDrawData(), commandBuffer);
}

// For a frame that began but will not be recorded - drawFrame skipped or failed.
// Every NewFrame must reach either Render or EndFrame.
void ImGuiDebugPanels::discardFrame()
{
    if (!m_frameBegun) { return; }
    ImGui::EndFrame();
    m_frameBegun = false;
}
```

This `beginFrame` has no UI scale yet; the attempt below adds one. `record`
and `discardFrame` stay as they are.

The frame flag records an obligation, not whether Vulkan submitted anything.
`Render` closes ImGui's frame before its backend records the draw data. If a
later command-buffer end or submit fails, guarded `discardFrame` therefore
does nothing. If recording fails before `Render`, it closes the begun frame
with `EndFrame`. This also makes cleanup safe before the first `NewFrame`.

`ImGui_ImplVulkan_RenderDrawData` **records into an active rendering scope**.
It does not begin one. It can submit work of its own, though: when the font
atlas changes — on the first frame, and whenever a new UI scale (the attempt
below) needs glyphs at a size not drawn before — it records the upload into
its own command buffer, submits that to the queue from section 3, and waits
with `vkQueueWaitIdle` before it returns. That is legal, since your command
buffer is still recording, but it stalls the CPU until the GPU is idle, which
section 7's plot can show as a spike when a new scale is applied. Where the
scope goes:

```cpp
vkCmdBeginRendering(commandBuffer, &renderingInfo);

drawScene(commandBuffer);              // the triangle
m_debugPanels.record(commandBuffer);   // ImGui on top

vkCmdEndRendering(commandBuffer);
```

From Chapter 8 on, the scene moves to an offscreen target and ImGui records
inside the composite pass's rendering scope instead, on top of the fullscreen
triangle. You could also give ImGui its own `vkCmdBeginRendering` with
`LOAD_OP_LOAD`; either works. The constraints are that a rendering scope is
open and that its attachments match what section 3 told the backend: one
color attachment of that format, one sample, no depth.

<a id="ch07-scale-a-live-interface"></a>

### Attempt CH07-scale-a-live-interface: scale a live interface

On a 4K monitor the default panel is hard to read. Enlarging the font alone
leaves small controls; multiplying padding every frame makes the panel grow
forever. A slider that resizes itself during a drag can move underneath the
pointer. Solve those three problems together before opening the answer.

Add a global 75-300% UI scale control. Decide when a requested value may change
the active layout, which measurements use the scale, and what happens to a
panel near the edge when the window becomes smaller.

**Acceptance:** Fonts and controls scale together without cumulative growth.
Repeated requests are stable, mouse dragging does not move the active slider,
keyboard changes apply, and panels remain reachable after a viewport shrink.

**Transfer:** Start at the OS content scale, change it manually, then recreate
the rendering resources. Which state belongs to the user's session and which
state belongs to a particular ImGui context?

**Scaling acceptance:** At 75%, 150% and 300%, the Frame slider remains
reachable after shrinking the window. Return to 100% and verify the original
spacing returns; the same scale request on successive frames must not keep
moving or enlarging windows. While dragging, the slider's geometry stays
fixed; releasing it applies the selected scale. A keyboard step from 100% to
101% must not round back to 100%.

**Scaling transfer:** Move Frame near the lower-right edge, change to 300%,
then shrink the viewport. Predict whether scaling its saved position alone
keeps its title and controls reachable, and verify the clamp. Enter a
non-finite or out-of-range value through `setUiScale`: it must be ignored or
clamped without damaging the next frame.

<details>
<summary>Hint 1: the idea</summary>

Separate a requested value from the value used by the current frame. Keep an
unscaled baseline instead of treating last frame's scaled style as a baseline.

</details>

<details>
<summary>Hint 2: the data and coordinates</summary>

Font size, style dimensions and saved window rectangles all participate.
Viewport dimensions are already physical pixels: do not scale them a second
time. A minimized zero-size viewport is not a useful layout constraint.

</details>

<details>
<summary>Hint 3: a concrete route</summary>

Apply queued changes before `NewFrame`, restore and scale the baseline style,
and move existing windows by the old-to-new ratio. Delay mouse-driven changes
until release, then clamp windows to the usable viewport. Reject nonfinite
requests and clamp the supported range.

</details>

<details>
<summary>Worked solution: queued UI scale</summary>

A scale slider queues a request. Apply it after the backend frame hooks but
before `ImGui::NewFrame()`, never midway through this frame's layout. Mouse
dragging holds the applied scale steady until release; keyboard edits apply
on the next frame. Section 7 supplies the slider and its drag-state update;
the initialization in section 3 supplies the vector font and baseline style.
Together those pieces are the complete implementation, not just the setter.

Three pieces go in `ImGuiDebugPanels.cpp`: `uiPixels`, a file-scope helper
that section 7's panel also uses; a `beginFrame` that replaces
[the scale-free one](#beginning-recording-and-discarding-a-frame) above; and
`setUiScale`, which section 3's
`initialize` already calls. `record` and `discardFrame` are unchanged.

```cpp
// File scope for this chapter. Chapter 09 moves this into shared DemoPanel helpers.
static float uiPixels(float baselinePixels)
{
    return baselinePixels * ImGui::GetStyle().FontScaleMain;
}

void ImGuiDebugPanels::beginFrame()
{
    ImGui_ImplVulkan_NewFrame();
    ImGui_ImplGlfw_NewFrame();
    const bool scaleChanged = m_requestedUiScale != m_appliedUiScale && !m_scaleSliderDragging;
    m_scaleSliderDragging = false;
    if (scaleChanged)
    {
        ImGuiStyle& style = ImGui::GetStyle();
        style = m_baseStyle;
        style.ScaleAllSizes(m_requestedUiScale);
        style.FontScaleMain = m_requestedUiScale;
        ImGui::ScaleWindowsInViewport(static_cast<ImGuiViewportP*>(ImGui::GetMainViewport()),
                                       m_requestedUiScale / m_appliedUiScale);
        m_appliedUiScale = m_requestedUiScale;
    }
    const ImVec2 display = ImGui::GetIO().DisplaySize;
    if (display.x > 0.0f && display.y > 0.0f
        && (scaleChanged || display.x != m_lastDisplaySize.x || display.y != m_lastDisplaySize.y))
    {
        const ImGuiStyle& style = ImGui::GetStyle();
        const float margin = uiPixels(10.0f);
        const ImVec2 maximum{ std::max(style.WindowMinSize.x, display.x - 2.0f * margin),
                               std::max(style.WindowMinSize.y, display.y - 2.0f * margin) };
        for (ImGuiWindow* window : GImGui->Windows)
        {
            if ((window->Flags & ImGuiWindowFlags_ChildWindow) != 0 || window->DockIsActive) { continue; }
            const ImVec2 size{ std::min(window->SizeFull.x, maximum.x),
                                std::min(window->SizeFull.y, maximum.y) };
            ImGui::SetWindowSize(window->Name, size);
            ImGui::SetWindowPos(window->Name, ImVec2{
                std::clamp(window->Pos.x, margin, std::max(margin, display.x - size.x - margin)),
                std::clamp(window->Pos.y, margin, std::max(margin, display.y - size.y - margin)) });
        }
        m_lastDisplaySize = display;
    }
    ImGui::NewFrame();
    m_frameBegun = true;
}

void ImGuiDebugPanels::setUiScale(float scale)
{
    if (!std::isfinite(scale)) { return; }
    m_requestedUiScale = std::clamp(scale, 0.75f, 3.0f);
    m_scaleInitialized = true;
}
```

The style is reset from `m_baseStyle` every time: calling `ScaleAllSizes(2)`
on an already doubled style would quadruple its padding. The dragging flag is
cleared before building the UI and recomputed after the slider, so a collapsed
or omitted Frame panel cannot keep an old drag flag forever. Existing windows are
rescaled once by the ratio between the requested and applied values, then
clamped when scale or viewport size changes, but only when both viewport
dimensions are positive. A minimized zero-sized viewport must not overwrite
saved positions or shrink every window to its minimum. Child and docked windows follow
their parent's layout instead. The private viewport/window access is specific
to the pin checked in section 1.

</details>

---

## 6. The sRGB washout

Promised in Chapter 3, section 2: ImGui's colors are already sRGB bytes, so the
`_SRGB` swapchain encodes them a second time and the panels look pale and
low-contrast. **This is expected, and Chapter 8, section 4 fixes it** by moving the
one encode into a composite pass and switching the swapchain to UNORM, which stores
ImGui's bytes as they are. If only ImGui looks washed out, this is why.

---

## 7. A panel worth having on day one

```cpp
// Source/PillowFort/DebugPanels/ImGuiDebugPanels.h. VulkanRenderer fills the
// GPU half (section 10); SandboxGame adds the timing from its clock.
struct FrameStatistics
{
    float                  cpuMilliseconds = 0.0f;
    std::array<float, 120> history{};               // last two seconds at 60 Hz
    std::string            gpuName;
    VkExtent2D             extent{};
    uint32_t               imageCount      = 0;
    const char*            presentModeName = "";    // string_VkPresentModeKHR
    uint64_t               frameIndex      = 0;
};
```

```cpp
void ImGuiDebugPanels::drawFrameStatistics(const FrameStatistics& statistics)
{
    // Without a position every ImGui window opens at the same spot and hides the
    // others. FirstUseEver lets the user move it afterwards.
    const float margin = uiPixels(10.0f);
    ImGui::SetNextWindowPos(ImVec2(margin, margin), ImGuiCond_FirstUseEver);
    const ImVec2 display = ImGui::GetIO().DisplaySize;
    const ImVec2 minimum = ImGui::GetStyle().WindowMinSize;
    ImGui::SetNextWindowSizeConstraints(ImVec2(0.0f, 0.0f), ImVec2(
        std::max(minimum.x, display.x - 2.0f * margin),
        std::max(minimum.y, display.y - 2.0f * margin)));
    if (ImGui::Begin("Frame", nullptr, ImGuiWindowFlags_AlwaysAutoResize))
    {
        const float fps = statistics.cpuMilliseconds > 0.0f ? 1000.0f / statistics.cpuMilliseconds
                                                            : 0.0f;   // frame 0 has no duration yet
        ImGui::Text("%.3f ms  (%.1f fps)", statistics.cpuMilliseconds, fps);
        int scalePercent = static_cast<int>(std::lround(m_requestedUiScale * 100.0f));
        ImGui::SetNextItemWidth(ImGui::GetFontSize() * 8.0f);
        if (ImGui::SliderInt("UI scale", &scalePercent, 75, 300, "%d%%", ImGuiSliderFlags_AlwaysClamp))
        {
            setUiScale(static_cast<float>(scalePercent) * 0.01f);
        }
        m_scaleSliderDragging = ImGui::IsItemActive() && ImGui::IsMouseDown(ImGuiMouseButton_Left);
        ImGui::PlotLines("##history", statistics.history.data(),
                         static_cast<int>(statistics.history.size()),
                         0, nullptr, 0.0f, 33.0f, ImVec2(0, uiPixels(60.0f)));
        ImGui::Separator();
        ImGui::Text("GPU:       %s", statistics.gpuName.c_str());
        ImGui::Text("Swapchain: %u x %u (%u images)",
                    statistics.extent.width, statistics.extent.height,
                    statistics.imageCount);
        ImGui::Text("Present:   %s", statistics.presentModeName);
        ImGui::Text("Frame:     %llu", statistics.frameIndex);
    }
    ImGui::End();
}
```

`ImGui::Begin` must always be paired with `ImGui::End`, **even when it returns
false**. The `if` guards the contents, not the `End`. This is the most common
ImGui bug there is, and it manifests as an assert deep in ImGui with no
indication of which window is unbalanced.

The frame-time plot earns its space immediately: at 165 Hz a hitch is
invisible in a number and obvious in a graph. The scale slider uses integer 1%
steps and only queues `setUiScale`; section 5 applies keyboard edits next frame
and mouse edits after the drag is released.

This chapter uses a file-local `uiPixels` and a viewport-sized Frame cap, so
it does not depend on a future chapter's files. Chapter 9, section 6 replaces
that local helper and the two placement/size calls with shared `uiPosition`
and `stopNextWindowAtScreenBottom`, whose cap also follows a dragged panel's
top edge. The assembled source includes that later shared-helper version.

### The present-mode picker Chapter 3 promised

Chapter 3's `setPresentMode` has been waiting for a caller. A combo box on the
same panel, listing **only the modes this surface supports**, makes it
impossible to ask for one that is not there:

```cpp
// Source/PillowFort/DebugPanels/ImGuiDebugPanels.cpp, beside drawFrameStatistics.
// Returns true when the user picked a different mode; `current` is updated.
bool ImGuiDebugPanels::drawPresentModePicker(std::span<const VkPresentModeKHR> supported,
                                             VkPresentModeKHR& current)
{
    bool changed = false;
    if (ImGui::Begin("Frame"))   // Begin on an existing name appends to that window
    {
        if (ImGui::BeginCombo("Present mode", string_VkPresentModeKHR(current)))
        {
            for (const VkPresentModeKHR mode : supported)
            {
                if (ImGui::Selectable(string_VkPresentModeKHR(mode), mode == current))
                {
                    changed = mode != current;
                    current = mode;
                }
            }
            ImGui::EndCombo();
        }
    }
    ImGui::End();
    return changed;
}
```

```cpp
// In SandboxGame, after drawFrameStatistics.
VkPresentModeKHR presentMode = renderer.swapchain().presentMode();
if (renderer.debugPanels().drawPresentModePicker(renderer.swapchain().supportedPresentModes(),
                                                 presentMode))
{
    renderer.setPresentMode(presentMode);
}
```

---

## 8. Shutdown

Reverse order, and Vulkan must still be alive:

```cpp
void ImGuiDebugPanels::shutdown()
{
    // Caller has already run vkDeviceWaitIdle. Safe after a partial initialize:
    // each backend is shut down only if it got as far as registering itself.
    if (ImGui::GetCurrentContext() == nullptr) { return; }
    discardFrame();

    const ImGuiIO& io = ImGui::GetIO();
    if (io.BackendRendererUserData != nullptr) { ImGui_ImplVulkan_Shutdown(); }
    if (io.BackendPlatformUserData != nullptr) { ImGui_ImplGlfw_Shutdown(); }
    ImGui::DestroyContext();
}
```

ImGui owns Vulkan objects (its pipeline, font image, buffers) and destroys them
in `ImGui_ImplVulkan_Shutdown`. That requires a live `VkDevice`, which is why
the roadmap shuts the debug panels down before Vulkan. Getting this backwards
produces a crash inside the driver at exit, which reads like a driver bug and
is not.

---

## 9. Toward the shader-parameter workbench

The thing you actually want is a panel whose sliders drive a shader. The wiring
belongs in Chapter 8, but design the ownership now, because getting it wrong
costs a refactor.

The parameters belong to whatever draws with them — the triangle, for now, and
the triangle demo once Chapter 9, section 6 makes it one. Put the struct beside
that code:

```cpp
// Source/PillowFort/VulkanGraphics/ShaderParameters.h
// Moves into the triangle demo's folder in Chapter 09 section 6.
#pragma once

namespace pf::vulkan_graphics {

// Laid out to match the push-constant block in Chapter 08.
struct ShaderParameters
{
    float time            = 0.0f;
    float amplitude       = 1.0f;
    float frequency       = 4.0f;
    float padding0        = 0.0f;
    float baseColor[4]    = { 0.2f, 0.5f, 0.9f, 1.0f };
};

// The panel that edits it. Defined in ShaderParameters.cpp; true if anything changed.
bool drawShaderParameters(ShaderParameters& parameters);

} // namespace pf::vulkan_graphics
```

`padding0` keeps `baseColor` on a 16-byte boundary, which is where the
shader's matching block will put it (Chapter 8, section 8 has the rule).

The panel is a free function beside the struct — not an `ImGuiDebugPanels`
member. It **edits** the struct; it does not know it is a push constant, it
does not touch Vulkan, and it does not own the value. Its definition goes in a
`.cpp`, not the header: Chapter 8 has `VulkanRenderer.h` include this header,
so a function defined here would be defined again in every file that includes
the renderer, and the link fails with `LNK2005`. Keeping the body out also keeps
`<imgui.h>` out of every file that only wants the struct.

```cpp
// Source/PillowFort/VulkanGraphics/ShaderParameters.cpp, inside namespace pf::vulkan_graphics.
// Includes ShaderParameters.h, <imgui.h> and <algorithm>; demo code may.
bool drawShaderParameters(ShaderParameters& parameters)
{
    bool changed = false;
    const float scale = ImGui::GetStyle().FontScaleMain;
    const float margin = 10.0f * scale;
    const ImVec2 display = ImGui::GetIO().DisplaySize;
    const ImVec2 minimum = ImGui::GetStyle().WindowMinSize;
    const float top = std::clamp(260.0f * scale, margin,
        std::max(margin, display.y - ImGui::GetFrameHeight() * 2.0f - margin));
    ImGui::SetNextWindowPos(ImVec2(margin, top), ImGuiCond_FirstUseEver);   // below Frame, if it fits
    ImGui::SetNextWindowSizeConstraints(ImVec2(0.0f, 0.0f), ImVec2(
        std::max(minimum.x, display.x - 2.0f * margin),
        std::max(minimum.y, display.y - top - margin)));
    if (ImGui::Begin("Shader", nullptr, ImGuiWindowFlags_AlwaysAutoResize))
    {
        changed |= ImGui::SliderFloat("Amplitude", &parameters.amplitude, 0.0f, 4.0f);
        changed |= ImGui::SliderFloat("Frequency", &parameters.frequency, 0.1f, 32.0f);
        changed |= ImGui::ColorEdit4("Base color", parameters.baseColor);
    }
    ImGui::End();
    return changed;
}
```

The position and size lines are layout for this stage only, not part of the
parameters: Chapter 9 replaces them with the shared `beginDemoPanel` helper.
`260.0f * scale` puts the panel's top below where Frame usually ends, and the
clamp pulls it up in a short window, leaving room for two rows. The size
constraint stops the panel at the window's bottom edge, so at a large scale its
contents scroll instead of running off screen.

Keeping it out of `ImGuiDebugPanels` is what ROADMAP step 10's exit check turns
on: a second demo, with its own parameters and its own panel, touches only its
own folder (Chapter 9, section 8). Call the function anywhere between
`beginFrame` and `record`.

A slider's drag range is not automatically a hard input limit. The
[pinned ImGui header](https://github.com/ocornut/imgui/blob/b48d1afbe8ee8b238e2961dc363a949dd7304e23/imgui.h#L702)
notes that Ctrl+click text input can exceed it unless
`ImGuiSliderFlags_AlwaysClamp` is supplied. Use that flag for a parameter with
a declared legal range. Validate work counts again where commands or GPU
parameters are built: a future caller may bypass the panel entirely. Chapter
20's Life step count and Chapter 33's bounce/sample counts make those bounds
part of their recording contract. UI editing and data validation are different
responsibilities.

Until the triangle reads the values, they can live in `main`, which owns
everything else too; Chapter 8, section 5 moves them onto the renderer, beside
the draw that pushes them. **This is `Main.cpp`**, which includes
`ShaderParameters.h`. Above the frame loop:

```cpp
vulkan_graphics::ShaderParameters shaderParameters;   // Chapter 08 section 5 moves it onto the renderer
```

and in the loop that [section 10](#10-who-owns-the-panels) writes, after
`drawFrameStatistics`:

```cpp
vulkan_graphics::drawShaderParameters(shaderParameters);   // edits it; nothing reads it until Chapter 08
```

One trap in `baseColor`, which bites in Chapter 8: `ColorEdit4` edits the number
as an sRGB-encoded color, so it must be converted to linear before lighting math
uses it — the last row of Chapter 8, section 4's color-boundary table.

Returning `changed` costs nothing now and is easy to forget later: anything
that builds up a result over many frames — Chapter 33's path tracer is the
example — must start over when a parameter changes, and that boolean is how it
finds out.

---

## 10. Who owns the panels

**`VulkanRenderer` owns `ImGuiDebugPanels`.** It records ImGui into the frame's
command buffer, it holds every handle the create-info needs, and its shutdown
already begins with `vkDeviceWaitIdle`. `SandboxGame` owns the *order* of each
frame, and reaches the panels through the renderer. The renderer grows by:

```cpp
// Added to VulkanRenderer (Chapter 04's class map).
public:
    void beginUiFrame() { m_debugPanels.beginFrame(); }     // before any ImGui:: call
    void setPresentMode(VkPresentModeKHR mode)               // section 7's picker
    {
        m_swapchain.setPresentMode(mode);
        m_framebufferResized = true;                         // recreate, like a resize
    }
    debug_panels::ImGuiDebugPanels& debugPanels() { return m_debugPanels; }
    const VulkanSwapchain&          swapchain() const { return m_swapchain; }
    debug_panels::FrameStatistics   frameStatistics() const; // the GPU half

private:
    debug_panels::ImGuiDebugPanels m_debugPanels;
```

At the start of Chapter 4's `drawFrame`, add one failure exit:

```cpp
    const auto failFrame = [&]()
    {
        m_debugPanels.discardFrame();
        return FrameStatus::Failed;
    };
```

Replace each original `return FrameStatus::Failed` in that function with
`return failFrame()`, including the failure side of the acquire-time
recreation expression. In the `VK_ERROR_OUT_OF_DATE_KHR` branch, call
`m_debugPanels.discardFrame()` before that expression too: a successful
recreation returns `Skipped`, which must close the UI just as a failure does.
Do not add a new discard after ordinary presentation: `record` already called
`Render`. The guard makes a failure after `Render` harmless to ImGui's state.

- **In `initialize`**, last — after the swapchain and pipeline cache exist, since
  the create-info needs both. Fill `ImGuiDebugPanelsCreateInfo` from
  `m_vulkan` (`Instance()`, `PhysicalDevice()`, `Device()`, `GraphicsFamily()`,
  `GraphicsQueue()`), `m_swapchain` (`imageCount()`, `format()`), and
  `m_pipelineCache`, then call `m_debugPanels.initialize(info)`.
- **In `shutdown`**, first — right after `vkDeviceWaitIdle`, before the frame
  resources and the swapchain. `ImGuiDebugPanels::shutdown` is safe after a
  partial initialize (section 8).
- **In `recordFrame`**, `m_debugPanels.record(commandBuffer)` inside the last
  rendering scope of the frame (section 5).
- **In `drawFrame`**, every `Failed` return and the acquire-time `Skipped`
  return close any begun UI frame. The minimized branch of `main` never calls
  `beginUiFrame`, so it needs nothing. A forced skip goes **before**
  `vkAcquireNextImageKHR`: skipping after a successful acquire would leave
  `imageAvailable` signalled with nothing waiting on it. The exit check forces
  this path because some drivers report `OUT_OF_DATE` only from present.
- **`frameStatistics`** fills `gpuName` from `vkGetPhysicalDeviceProperties` on
  `m_vulkan.PhysicalDevice()`, and `extent`, `imageCount`, and
  `presentModeName` (via `string_VkPresentModeKHR(m_swapchain.presentMode())`)
  from the swapchain.

Chapter 5's loop then becomes:

```cpp
// Source/SandboxGame/Main.cpp, inside the frame loop, after the minimized check.
window.pollEvents();
// Polling can deliver a minimize after the check at the top of the loop.
if (window.isMinimized()) { continue; }
renderer.beginUiFrame();                    // ImGui::NewFrame: WantCapture* now valid

const ImGuiIO& io = ImGui::GetIO();
for (const window::Event& event : window.drainEvents())
{
    if (event.kind == window::EventKind::FramebufferResized)
    {
        renderer.notifyFramebufferResized();   // never filtered: ImGui does not own the window size
        continue;
    }
    if (io.WantCaptureMouse && event.isMouse())       { continue; }   // section 4
    if (io.WantCaptureKeyboard && event.isKeyboard()) { continue; }
    // Anything left is the application's - the active demo's, from Chapter 09 on.
}

debug_panels::FrameStatistics statistics = renderer.frameStatistics();
statistics.cpuMilliseconds = frameMilliseconds;
statistics.history         = history;
statistics.frameIndex      = frameCount++;
renderer.debugPanels().drawFrameStatistics(statistics);

// Then Chapter 05's elapsedSeconds, FrameRequest, and drawFrame lines, unchanged.
```

The timing comes from the same `steady_clock` as Chapter 5's elapsed time:

```cpp
// Source/SandboxGame/Main.cpp. Before the loop:
auto                   previousFrame = std::chrono::steady_clock::now();
std::array<float, 120> history{};
uint64_t               frameCount = 0;

// In the loop, right after the minimized check:
const auto  now               = std::chrono::steady_clock::now();
const float frameMilliseconds = std::chrono::duration<float, std::milli>(now - previousFrame).count();
previousFrame = now;
std::rotate(history.begin(), history.begin() + 1, history.end());   // oldest sample drops off the front
history.back() = frameMilliseconds;
```

(`<imgui.h>`, `<imgui_impl_glfw.h>`, `<algorithm>`, and `<array>` join
Main.cpp's includes.) Despite its name, `cpuMilliseconds` is the whole
interval between two passes of the loop as the CPU's clock sees it, including
the fence wait and any vsync wait in present, not the CPU's own work: under
FIFO it reads the refresh interval however light the frame is. The first
frame after restoring from minimized shows a long spike — the time spent
minimized — which is the truth, not a bug.

Recheck minimization immediately after polling: the minimize event may have
arrived after the check at the top of the loop. Continuing there begins no
ImGui frame, so it needs no `discardFrame`. Keep the initial minimized branch's
`waitEvents`, which waits instead of spinning.

Note the order: `beginUiFrame` comes before draining events, so section 4's
`WantCaptureMouse` answers for this frame, and every `ImGui::` call goes
between `beginUiFrame` and `drawFrame`, which records them.

`SandboxGame` now calls `ImGui::` and the GLFW backend's callbacks directly, so
it needs the ImGui and GLFW include directories — Chapter 1's workspace gives
them to `SandboxGame` for exactly this reason.

---

## Exit check

Regenerate (`ImGuiDebugPanels` and `ShaderParameters` are new files), then
build and run:

- [ ] Panels render over the triangle and respond to mouse and keyboard.
- [ ] A "Shader" panel sits below "Frame". Its sliders move and change nothing
      yet: Chapter 8, section 5 connects them to the triangle.
- [ ] Events stop at the filter while ImGui wants them: dragging a slider or
      typing in a field passes nothing on, and clicks outside any panel get
      through. Nothing consumes them until Chapter 10's camera controls, so a
      temporary log line after the filter is how to see it.
- [ ] Typing into a text field works, proving `character` is forwarded. No
      panel here has an `ImGui::InputText`; Ctrl+click a slider to type a
      value into it, or add a temporary `InputText`.
- [ ] Resizing and minimizing with panels open produces no validation errors.
- [ ] Shutdown is clean with panels open.
- [ ] **The skipped-frame path works.** For one run, have `drawFrame` call
      `discardFrame` and return `Skipped` every hundredth frame, before
      `vkAcquireNextImageKHR` (section 10): the panels keep drawing and
      validation stays silent. Move those lines below the acquire and
      validation reports `VUID-vkAcquireNextImageKHR-semaphore-01286`, a
      semaphore still signalled — which is why the skip goes first. Remove
      them.
- [ ] ImGui looks washed out, and you know Chapter 8 is the fix (section 6).

Next: [08 — Resources, Memory, and Descriptors](08-Resources-And-Descriptors.md)
