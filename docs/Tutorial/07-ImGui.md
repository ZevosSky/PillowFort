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

**Prerequisites:** Chapter 02 section 4 (the `Window` module and its event
queue), Chapter 03 section 2 (the `_SRGB` swapchain, which section 6 here
pays for), Chapter 04's class map, and Chapter 06 (the pipeline cache from
section 6, and the triangle the panels draw over).

This is the chapter that makes the project a *workbench* rather than a demo.
Everything after it is easier to debug because you can put state on screen and
change it without recompiling.

**ImGui is an immediate-mode GUI**, which is not how most widget toolkits work.
It keeps no window or button objects for you to create and update. Instead,
every frame, you call a function per widget —
`ImGui::SliderFloat("Amplitude", &value, 0.0f, 4.0f)` — which both draws the
slider this frame and returns whether the user just changed `value`. ImGui turns the frame's calls into
triangles, and its Vulkan backend records them into your command buffer. So
calling `ImGui::Begin` and the widgets again every frame is the design, not a
mistake, and a panel is just a function you call between the frame's start and
its recording.

---

## 1. Check the backend's header first

The ImGui Vulkan backend changes shape between versions. The code below matches
the pin, **v1.92.9b-docking**. **Open
`Vendor/ImGui/backends/imgui_impl_vulkan.h` and read `ImGui_ImplVulkan_InitInfo`
before typing any of this.** It is 30 lines, it is the authoritative version
for your pin, and checking takes less time than debugging a struct mismatch.
Where the header's comments and the change log at the top of
`imgui_impl_vulkan.cpp` disagree, the change log is right.

---

## 2. The descriptor pool — let the backend make it

A shader finds an image through a **descriptor set**, a small object that
points at it; Chapter 08 section 6 builds them. ImGui needs one for every
texture it draws — its font atlas, plus any image you register — and allocates
them from a **descriptor pool**. It wants its own pool, so its allocations
never interact with yours, and **the pinned backend will make that pool
itself**: set `DescriptorPoolSize` in the init info (section 3) and leave
`DescriptorPool` null. The backend creates the pool, sizes it correctly, and
destroys it in its own shutdown.

Do not hand-build the pool from an older tutorial: the pinned backend uses a
different kind of descriptor than the classic recipe, so that pool holds none of
what the backend allocates. A driver that counts pool sizes strictly fails the
backend's first allocation inside `ImGui_ImplVulkan_Init`, which section 3's
`checkVulkanResult` logs as `VK_ERROR_OUT_OF_POOL_MEMORY`; one that lets a pool
overfill runs it anyway, and the validation layer does not check pool sizes, so
a hand-built pool that works on one GPU can still fail on the next.

Sixty-four sets is generous for a font atlas alone, and leaves room for what
you will want later: **showing your own images inside ImGui windows.**
`ImGui_ImplVulkan_AddTexture(view, layout)` returns a `VkDescriptorSet` you can
pass straight to `ImGui::Image()`, where `layout` is the layout the image will
be in *when ImGui draws*, not the one it is in now. Chapter 09 lists it among
what a demo may create for itself.

---

## 3. Initialization

Everything the backend needs arrives in one create-info. `VulkanRenderer`
fills it, because it holds everything the backend needs (section 10):

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
and destroys everything, including the descriptor pool from section 2. So the
class is only its functions, each tagged with the section that writes it:

```cpp
// Source/PillowFort/DebugPanels/ImGuiDebugPanels.h, inside namespace pf::debug_panels
class ImGuiDebugPanels
{
public:
    InitializationResult initialize(const ImGuiDebugPanelsCreateInfo& info);   // section 3
    void beginFrame();                                                         // section 5
    void record(VkCommandBuffer commandBuffer);                                // section 5
    void discardFrame();                                                       // section 5
    void drawFrameStatistics(const FrameStatistics& statistics);              // section 7
    bool drawPresentModePicker(std::span<const VkPresentModeKHR> supported,
                               VkPresentModeKHR& current);                     // section 7
    void shutdown();                                                           // section 8
};
```

The header includes `InitializationResult.h`, `<vulkan/vulkan.h>`, `<array>`,
`<span>`, and `<string>`, and forward-declares `struct GLFWwindow;`. The `.cpp`
includes ImGui, both backends, `Log.h`, `<format>`, and
`<vulkan/vk_enum_string_helper.h>`.

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

    // In this pin these live on PipelineInfoMain, not on InitInfo itself.
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
  tries to build its pipeline against a `VkRenderPass` you do not have. The
  format must match the attachment you will actually draw into — the
  swapchain's, `m_swapchain.format()`. The backend asserts on the `sType`, so
  set it.
- **`MSAASamples` and `PipelineRenderingCreateInfo` live on
  `PipelineInfoMain`**, not on `InitInfo` itself, in this pin. Older pins had
  them directly on `InitInfo`; this is the struct mismatch section 1 warns
  about, and the most likely thing here to be stale.
- **`io.IniFilename = nullptr` is a starting choice, not a final one.** ImGui
  persists window positions to `imgui.ini` in the working directory by default,
  which pollutes your repo root. Once you have panels you care about arranging,
  point it at a real path beside the executable and *keep* the layout — a
  parameter workbench you have to rearrange every launch does not get used.
- **`CheckVkResultFn`** routes the backend's internal Vulkan errors into
  `ErrorReporting` instead of silence.

---

## 4. Input forwarding, and why the roadmap is right

`ImGui_ImplGlfw_InitForVulkan(window, false)` — the `false` means "do not
install GLFW callbacks". ROADMAP requires this, because the `Window`
module owns the callbacks and queues events, and letting ImGui install its own
would either overwrite yours or chain unpredictably.

The cost is that you forward manually, and the forwarding has a dependency
problem: `Window` must not know `DebugPanels` exists. So `Window` exposes an
optional set of forwarding hooks — plain GLFW callback types, nothing
ImGui-specific — and `SandboxGame`, the only place that knows both modules,
fills them in.

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

### Who gets the input

Every event now goes to ImGui *and* into the window's queue, so the frame loop
decides who acts on it. ImGui answers with two flags on `ImGui::GetIO()`:
`WantCaptureMouse` is true when the cursor is over an ImGui window or dragging
a widget, and `WantCaptureKeyboard` when a text field or keyboard navigation
has focus. The loop skips the queued mouse events while the first is set, and
the keyboard events while the second is — section 10 shows the code. Without
that filter, dragging a slider also spins Chapter 10's camera.

These flags are only valid **after `ImGui::NewFrame()`**. Reading them before
gives you last frame's answer, which is usually right and occasionally produces
a one-frame glitch that is maddening to reproduce.

---

## 5. The frame

```cpp
void ImGuiDebugPanels::beginFrame()
{
    ImGui_ImplVulkan_NewFrame();
    ImGui_ImplGlfw_NewFrame();
    ImGui::NewFrame();
}

void ImGuiDebugPanels::record(VkCommandBuffer commandBuffer)
{
    ImGui::Render();
    ImGui_ImplVulkan_RenderDrawData(ImGui::GetDrawData(), commandBuffer);
}

// For a frame that began but will not be recorded - drawFrame returned Skipped.
// ImGui asserts in NewFrame if the previous frame never reached Render or
// EndFrame, and the assert message does not say which frame was dropped.
void ImGuiDebugPanels::discardFrame()
{
    ImGui::EndFrame();
}
```

`ImGui_ImplVulkan_RenderDrawData` **records into an active rendering scope**.
It does not begin one. So:

```cpp
vkCmdBeginRendering(commandBuffer, &renderingInfo);

drawScene(commandBuffer);              // the triangle
m_debugPanels.record(commandBuffer);   // ImGui on top

vkCmdEndRendering(commandBuffer);
```

From Chapter 08 on, the scene moves to an offscreen target and ImGui records
inside the composite pass's rendering scope instead, on top of the fullscreen
triangle. You could also give ImGui its own `vkCmdBeginRendering` with
`LOAD_OP_LOAD`; either works, and the constraint is only that a rendering scope
is open.

---

## 6. The sRGB washout

Promised in Chapter 03 section 2, and it happens the first time you run this:
ImGui's colors are already sRGB bytes, the `_SRGB` swapchain encodes them a
second time, and the panels look pale and low-contrast. **This is expected, and
Chapter 08 fixes it** by moving the one encode into a composite pass and
switching the swapchain to UNORM, which stores ImGui's bytes as they are.

If your triangle looks right and only ImGui looks washed out, this is why. It
is not a bug in your barrier code.

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
    ImGui::SetNextWindowPos(ImVec2(10.0f, 10.0f), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("Frame"))
    {
        const float fps = statistics.cpuMilliseconds > 0.0f ? 1000.0f / statistics.cpuMilliseconds
                                                            : 0.0f;   // frame 0 has no duration yet
        ImGui::Text("%.3f ms  (%.1f fps)", statistics.cpuMilliseconds, fps);
        ImGui::PlotLines("##history", statistics.history.data(),
                         static_cast<int>(statistics.history.size()),
                         0, nullptr, 0.0f, 33.0f, ImVec2(0, 60));
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
invisible in a number and obvious in a graph.

### The present-mode picker Chapter 03 promised

Chapter 03's `setPresentMode` has been waiting for a caller. A combo box on the
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

The list differs a lot between GPUs, which is the point of building it from the
query: Chapter 03 section 3 has an integrated GPU with no `MAILBOX` beside a
discrete one with all four.

---

## 8. Shutdown

Reverse order, and Vulkan must still be alive:

```cpp
void ImGuiDebugPanels::shutdown()
{
    // Caller has already run vkDeviceWaitIdle. Safe after a partial initialize:
    // each backend is shut down only if it got as far as registering itself.
    if (ImGui::GetCurrentContext() == nullptr) { return; }

    const ImGuiIO& io = ImGui::GetIO();
    if (io.BackendRendererUserData != nullptr) { ImGui_ImplVulkan_Shutdown(); }
    if (io.BackendPlatformUserData != nullptr) { ImGui_ImplGlfw_Shutdown(); }
    ImGui::DestroyContext();
}
```

ImGui owns Vulkan objects (its pipeline, font image, buffers) and destroys them
in `ImGui_ImplVulkan_Shutdown`. That requires a live `VkDevice`, which is why
the roadmap puts debug panels down before Vulkan. Getting this backwards
produces a crash inside the driver at exit, which reads like a driver bug and
is not.

---

## 9. Toward the shader-parameter workbench

The thing you actually want is a panel whose sliders drive a shader. The wiring
belongs in Chapter 08, but design the ownership now, because getting it wrong
costs a refactor.

The parameters belong to whatever draws with them — the triangle, for now, and
the triangle demo once Chapter 09 section 6 makes it one. Put the struct beside
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
shader's matching block will put it (Chapter 08 section 8 has the rule).

The panel is a free function beside the struct — not an `ImGuiDebugPanels`
member. It **edits** the struct; it does not know it is a push constant, it
does not touch Vulkan, and it does not own the value. Its definition goes in a
`.cpp`, not the header: Chapter 08 has `VulkanRenderer.h` include this header,
so a function defined here would be defined again in every file that includes
the renderer, and the link fails with `LNK2005`. Keeping the body out also keeps
`<imgui.h>` out of every file that only wants the struct.

```cpp
// Source/PillowFort/VulkanGraphics/ShaderParameters.cpp, inside namespace pf::vulkan_graphics.
// Includes ShaderParameters.h and <imgui.h>; demo code may.
bool drawShaderParameters(ShaderParameters& parameters)
{
    bool changed = false;
    ImGui::SetNextWindowPos(ImVec2(10.0f, 220.0f), ImGuiCond_FirstUseEver);   // below "Frame"
    if (ImGui::Begin("Shader"))
    {
        changed |= ImGui::SliderFloat("Amplitude", &parameters.amplitude, 0.0f, 4.0f);
        changed |= ImGui::SliderFloat("Frequency", &parameters.frequency, 0.1f, 32.0f);
        changed |= ImGui::ColorEdit4("Base color", parameters.baseColor);
    }
    ImGui::End();
    return changed;
}
```

Keeping it out of `ImGuiDebugPanels` is what ROADMAP step 10's exit check turns
on: a second demo, with its own parameters and its own panel, touches only its
own folder (Chapter 09 section 8). Call the function anywhere between
`beginFrame` and `record`.

Until the triangle reads the values, they can live in `main`, which owns
everything else too; Chapter 08 section 5 moves them onto the renderer, beside
the draw that pushes them. **This is `Main.cpp`**, which includes
`ShaderParameters.h`. Above the frame loop:

```cpp
vulkan_graphics::ShaderParameters shaderParameters;   // Chapter 08 section 5 moves it onto the renderer
```

and in the loop, after `drawFrameStatistics`:

```cpp
vulkan_graphics::drawShaderParameters(shaderParameters);   // edits it; nothing reads it until Chapter 08
```

One trap in `baseColor`, which bites in Chapter 08: `ColorEdit4` edits the
number, and the swatch shows that number as ImGui draws it. Once the swapchain
is UNORM, that means **the swatch treats the value as sRGB-encoded**, while your
shader treats it as linear — the triangle comes out lighter than the swatch.
Convert picked colors to linear before lighting math uses them. Chapter 08
section 4's color-boundary table has the rule for every source of color.

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
- **In `drawFrame`**, the `Skipped` return — acquire reporting
  `OUT_OF_DATE` — calls `m_debugPanels.discardFrame()` first. The minimized
  branch of `main` never calls `beginUiFrame`, so it needs nothing. That return
  is rare: some drivers report `OUT_OF_DATE` only from present, never from
  acquire, so it may never run on your machine, and the exit check forces it.
  A forced skip goes **before** `vkAcquireNextImageKHR`: skipping after a
  successful acquire would leave `imageAvailable` signalled with nothing
  waiting on it.
- **`frameStatistics`** fills `gpuName` from `vkGetPhysicalDeviceProperties` on
  `m_vulkan.PhysicalDevice()`, and `extent`, `imageCount`, and
  `presentModeName` (via `string_VkPresentModeKHR(m_swapchain.presentMode())`)
  from the swapchain.

Chapter 05's loop then becomes:

```cpp
// Source/SandboxGame/Main.cpp, inside the frame loop, after the minimized check.
window.pollEvents();
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

if (renderer.drawFrame(request) == vulkan_graphics::FrameStatus::Failed) { break; }
```

The timing comes from the same `steady_clock` as Chapter 05's elapsed time:

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

(`<algorithm>` and `<array>` join Main.cpp's includes.) The first frame after
restoring from minimized shows a long spike — the time spent minimized — which
is the truth, not a bug.

Note the order: `beginUiFrame` before draining events, so section 4's
`WantCaptureMouse` answers for this frame, and every `ImGui::` call between it
and `drawFrame`, which records them.

Chapter 09 section 7 keeps what survives this filter and hands it to the active
demo, and Chapter 10 section 10 changes the filter in one way: a key or
mouse-button *release* is never dropped. With the filter above, a camera that
saw W pressed in the scene never hears it released over a panel, and keeps
flying; that section explains why letting every release through is always safe.

`SandboxGame` now calls `ImGui::` and the GLFW backend's callbacks directly, so
it needs the ImGui and GLFW include directories — Chapter 01's workspace gives
them to `SandboxGame` for exactly this reason.

---

## Exit check

- [ ] Panels render over the triangle and respond to mouse and keyboard.
- [ ] A "Shader" panel sits below "Frame". Its sliders move and change nothing
      yet: Chapter 08 section 5 connects them to the triangle.
- [ ] Events stop at the filter while ImGui wants them: dragging a slider or
      typing in a field passes nothing on, and clicks outside any panel get
      through. Nothing consumes them until Chapter 10's camera controls, so a
      temporary log line after the filter is how to see it.
- [ ] Typing into `ImGui::InputText` works, proving `character` is forwarded.
- [ ] Resizing and minimizing with panels open produces no validation errors.
- [ ] Shutdown is clean with panels open.
- [ ] **The skipped-frame path works.** For one run, have `drawFrame` call
      `discardFrame` and return `Skipped` every hundredth frame, before
      `vkAcquireNextImageKHR` (section 10): the panels keep drawing and
      validation stays silent. Move those lines below the acquire and
      validation reports `VUID-vkAcquireNextImageKHR-semaphore-01286`, a
      semaphore still signalled — which is why the skip goes first. Remove
      them.
- [ ] ImGui looks washed out, and you know Chapter 08 is the fix (section 6).

Next: [08 — Resources, Memory, and Descriptors](08-Resources-And-Descriptors.md)
